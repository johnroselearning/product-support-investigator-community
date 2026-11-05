"""EXP-001 quality/reliability and EXP-002 actual usage/latency baseline.

Default: offline dataset validation. --execute AND an explicit config are required
before importing a provider transport, reading credentials, or submitting requests.
"""
import argparse
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import time

from ..contracts import RESULT, validate
from ..engine import Harness
from ..semantic import ConservativeCritic
from ..state import Limits, utcnow
from .dataset import DATA, dataset_digest, load_cases, load_gold, synthetic_environment
from .providers import ModelConfig, ProviderAdapter, load_transport
from .review import calibrate, model_review, review_packet, validate_judgment
from .reporting import render_report
from .scoring import grade, summarize

STAGES = ("understand", "choose", "propose", "tool_execution", "report", "critic", "revise", "total")


def latency_record():
    return {stage: {"seconds": 0.0, "calls": 0, "model_requests": 0, "deterministic_checks": 0} for stage in STAGES}


class MeasuredHarness(Harness):
    """Evaluation-only observer; production Harness and decision contracts unchanged."""
    def __init__(self, *args, **kwargs):
        if kwargs.get("profiler") is not None:
            raise ValueError("Disable payload profiling for latency evaluation")
        super().__init__(*args, **kwargs)
        self.latency = latency_record()

    async def model(self, stage, payload, schema=None, *, critic=False):
        started = time.perf_counter()
        before = len(self.adapter.requests)
        decisions_before = len(self.adapter.decisions)
        deterministic = critic and isinstance(self.critic, ConservativeCritic)
        valid = False
        try:
            value = await super().model(stage, payload, schema, critic=critic)
            valid = True
            return value
        finally:
            for decision in self.adapter.decisions[decisions_before:]:
                decision["contract_valid"] = valid
            row = self.latency[stage]
            row["seconds"] += time.perf_counter() - started
            row["calls"] += 1
            row["model_requests"] += len(self.adapter.requests) - before
            row["deterministic_checks"] += int(deterministic)

    async def execute(self, name, inputs):
        started = time.perf_counter()
        try:
            return await super().execute(name, inputs)
        finally:
            self.latency["tool_execution"]["seconds"] += time.perf_counter() - started
            self.latency["tool_execution"]["calls"] += 1

    async def run(self, *args, **kwargs):
        started = time.perf_counter()
        try:
            return await super().run(*args, **kwargs)
        finally:
            self.latency["total"]["seconds"] = time.perf_counter() - started
            self.latency["total"]["calls"] = 1
            for row in self.latency.values():
                row["seconds"] = round(row["seconds"], 6)


def read_config(path):
    data = json.loads(Path(path).read_text())
    if not isinstance(data, dict) or data.keys() - {"candidate", "judge", "limits"} or "candidate" not in data:
        raise ValueError("Config requires candidate, optional judge and limits")
    candidate = ModelConfig(**data["candidate"])
    judge = ModelConfig(**data["judge"]) if data.get("judge") else None
    if judge and (candidate.provider, candidate.model) == (judge.provider, judge.model):
        raise ValueError("Use a separately configured independent judge model")
    limits = data.get("limits", {})
    allowed = {"seconds", "call_seconds", "output_tokens", "model_calls", "model_tokens"}
    if not isinstance(limits, dict) or limits.keys() - allowed:
        raise ValueError("Unsupported evaluation limit")
    base_limits = {"seconds": 900, "call_seconds": 60, "model_calls": 20,
                   "model_tokens": 1_000_000, "output_tokens": 2000, "retries": 0, **limits}
    Limits(**base_limits)
    return candidate, judge, base_limits


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    temporary.chmod(0o600)
    temporary.replace(path)


def write_report(path, result):
    path = Path(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(render_report(result))


async def dry_run(directory=DATA, config=None):
    cases = load_cases(directory)
    if config:
        read_config(config)  # No transport imports, credential lookups or model access.
    validations = []
    for case in cases:
        gold = load_gold(case["id"], directory)
        registry, _, audit = synthetic_environment(case)
        # Validate the declared tool outputs without inventing semantic decisions.
        for name, spec in case["tools"].items():
            inputs = {k: v for k, v in case["request"]["scope"].items()
                      if k in registry.bindings[name].input_schema["properties"]}
            extras = {"retrieve_trace": {"trace_id": "trace-102"},
                      "read_repository_file": {"path": "checkout.py", "revision": "abc123"},
                      "query_metrics": {"metric": "http_errors_total"}}
            inputs.update(extras.get(name, {}), limit=20)
            validate(inputs, registry.bindings[name].input_schema)
            first = await registry.bindings[name].handler(inputs, 1)
            second = await registry.bindings[name].handler(inputs, 1)
            validate(first, RESULT)
            if first != second or first != spec["response"]:
                raise ValueError("Nondeterministic fixture")
        locators = {r["locator"] for s in case["tools"].values() for r in s["response"]["records"]}
        locators.update(r["locator"] for r in case["request"]["artifacts"])
        if set(gold["expected_evidence"]) - locators or set(gold["required_tools"]) - case["tools"].keys():
            raise ValueError("Gold references unavailable synthetic evidence or tools")
        validations.append({"case_id": case["id"], "category": case["category"],
                            "contracts_valid": True, "fixture_responses_deterministic": True,
                            "planned_repeats": 5, "max_tool_calls": case["max_tool_calls"]})
    return {"mode": "offline-validation", "dataset_sha256": dataset_digest(directory),
            "case_count": len(cases), "planned_investigations": len(cases) * 5,
            "real_model_executions": 0, "real_model_requests": 0, "judge_requests": 0,
            "structural_validation": validations, "real_model_results": None, "human_reviewed_results": None,
            "unmeasured": ["semantic_quality", "root_cause_accuracy", "abstention_correctness",
                           "claim_support", "repeated_model_reliability", "provider_usage", "provider_latency"],
            "profiling_enabled": False, "monetary_cost": None}


async def evaluate(config_path, output, *, allow_model_requests=False, directory=DATA, transport_factory=None):
    if not allow_model_requests:
        raise ValueError("Explicit --execute opt-in required")
    candidate, judge_config, limit_config = read_config(config_path)
    await dry_run(directory, config_path)  # Fail before any provider import/request.
    cases = load_cases(directory)
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("Use a new empty output directory to preserve existing runs")
    output.mkdir(parents=True, exist_ok=True)
    factory = transport_factory or load_transport
    for config in (candidate, judge_config):
        if config and config.api_key_env and not os.environ.get(config.api_key_env):
            raise ValueError("Configured model credential is unavailable")
    rows = []
    result = {"mode": "real-model-with-synthetic-tools", "generated_at": utcnow(),
              "dataset_sha256": dataset_digest(directory), "candidate_configuration": candidate.public(),
              "judge_configuration": judge_config.public() if judge_config else None, "repeats": 5,
              "limits_configuration": limit_config,
              "profiling_enabled": False, "production_integrations": False,
              "real_model_executions": 0, "real_model_requests": 0,
              "results": rows, "summary": None,
              "limitations": ["Synthetic cases are public and do not establish production generalization.",
                  "Production report finalization forces investigation root causes to Unknown; raw attempts are retained separately.",
                  "Unknown usage fields remain null; no estimates or monetary costs are substituted.",
                  "Provider transport factories are trusted code and must not access gold files.",
                  "Deterministic injection checks cover explicit probes, not every possible semantic instruction-following behavior."]}
    # Persist planned runs before work; interruption cannot silently erase missing runs.
    plan = [{"key": f'{c["id"]}:{repeat}', "case_id": c["id"], "repeat": repeat, "status": "not_started"}
            for c in cases for repeat in range(1, 6)]
    write_json(output / "plan.json", plan)
    result.update(planned_runs=len(plan), remaining_runs=len(plan), summary=summarize([]))
    write_json(output / "results.json", result)
    for entry in plan:
        entry["status"] = "in_progress"
        write_json(output / "plan.json", plan)
        case = next(c for c in cases if c["id"] == entry["case_id"])
        key = entry["key"]
        row = {**entry, "expected_abstention": load_gold(case["id"], directory)["abstention"],
               "requests": [], "judge_requests": [], "decisions": [], "tool_audit": [],
               "latency": latency_record(), "judgment": None, "review_source": None, "review_error": None,
               "judge_decisions": [], "review_history": []}
        adapter = None
        try:
            # Fresh transport, adapter, registry, policy, harness and State per run.
            run_config = deepcopy(candidate)
            adapter = ProviderAdapter(run_config, factory(run_config), allow_model_requests=True)
            registry, policy, audit = synthetic_environment(case, adapter.destination)
            harness = MeasuredHarness(adapter, registry, policy, limits=Limits(tool_calls=case["max_tool_calls"], **limit_config))
            state = await harness.run(deepcopy(case["request"]))
            row.update(state=state.export(), latency=harness.latency, tool_audit=audit,
                       requests=adapter.requests, decisions=adapter.decisions, status=state.termination)
        except Exception:
            # Never serialize private provider/factory exceptions.
            row.update(state={"termination": "execution_failure", "report": {}, "workflow": "unknown"}, status="execution_failure")
            if adapter:
                row.update(requests=adapter.requests, decisions=adapter.decisions)
        gold = load_gold(case["id"], directory)
        packet, digest = review_packet(gold, row["state"])
        row["response_hash"] = digest
        write_json(output / "review" / (key.replace(":", "-") + ".json"),
                   {"key": key, "response_hash": digest, "packet": packet})
        if judge_config and row["state"].get("termination") not in ("execution_failure", "invalid_contract", "budget_exhausted"):
            judge = None
            try:
                review_config = deepcopy(judge_config)
                judge = ProviderAdapter(review_config, factory(review_config), allow_model_requests=True)
                row["judgment"] = await asyncio.wait_for(model_review(judge, packet, limit_config["output_tokens"]),
                    timeout=judge_config.timeout_seconds * (judge_config.retries + 1) + 1)
                row["review_source"] = "independent_model"
            except Exception:
                row["review_error"] = "judge_failed_or_invalid_contract"
            finally:
                row["judge_requests"] = judge.requests if judge else []
                row["judge_decisions"] = judge.decisions if judge else []
        row["score"] = grade(case, gold, row["state"], row["decisions"], row["tool_audit"], row["judgment"])
        rows.append(row)
        write_json(output / "runs" / (key.replace(":", "-") + ".json"), row)
        entry["status"] = row["status"]
        write_json(output / "plan.json", plan)
        result["real_model_executions"] = sum(any(q["submission_confirmed"] is True for q in r["requests"]) for r in rows)
        result["real_model_requests"] = sum(q["submission_confirmed"] is True for r in rows for q in r["requests"])
        result["provider_boundary_attempts"] = sum(len(r["requests"]) for r in rows)
        result["summary"] = summarize(rows)
        result["planned_runs"] = len(plan)
        result["remaining_runs"] = sum(p["status"] == "not_started" for p in plan)
        write_json(output / "results.json", result)
        write_json(output / "judge-labels.json", {r["key"]: {"response_hash": r["response_hash"], "judgment": r["judgment"]}
                   for r in rows if r.get("review_source") == "independent_model"})
        write_report(output / "report.md", result)
    return result


def apply_human_reviews(result, labels, directory=DATA):
    if result.get("dataset_sha256") != dataset_digest(directory):
        raise ValueError("Dataset changed; review must use the original dataset")
    cases = {c["id"]: c for c in load_cases(directory)}
    rows = result["results"]
    if set(labels) - {r["key"] for r in rows}:
        raise ValueError("Unknown review run identity")
    for row in rows:
        if row["key"] not in labels:
            continue
        label = labels[row["key"]]
        gold = load_gold(row["case_id"], directory)
        packet, digest = review_packet(gold, row["state"])
        if label["response_hash"] != digest or row["response_hash"] != digest:
            raise ValueError("Review does not match the saved candidate")
        judgment = validate_judgment(label["judgment"], packet)
        if row.get("judgment"):
            row.setdefault("review_history", []).append({"source": row["review_source"], "judgment": deepcopy(row["judgment"])})
        row["judgment"] = judgment
        row["review_source"] = "human"
        row["score"] = grade(cases[row["case_id"]], gold, row["state"], row["decisions"], row["tool_audit"], row["judgment"])
    result["summary"] = summarize(rows)
    return result


def paired_comparison(baseline, variant):
    if baseline["dataset_sha256"] != variant["dataset_sha256"] or baseline["repeats"] != variant["repeats"]:
        raise ValueError("Paired comparisons require the same dataset and repeat count")
    left = {r["key"]: r for r in baseline["results"]}
    right = {r["key"]: r for r in variant["results"]}
    if left.keys() != right.keys():
        raise ValueError("Missing paired run; incomplete results cannot be hidden")
    return {"paired_runs": len(left), "quality_precedes_efficiency": True, "pairs": [
        {"key": key, "baseline_pass": left[key]["score"]["pass"], "variant_pass": right[key]["score"]["pass"],
         "quality_delta": (right[key]["score"]["quality_score"]-left[key]["score"]["quality_score"])
             if left[key]["score"]["quality_score"] is not None and right[key]["score"]["quality_score"] is not None else None,
         "baseline_safety": left[key]["score"]["safety_violations"], "variant_safety": right[key]["score"]["safety_violations"],
         "baseline_usage": left[key]["requests"], "variant_usage": right[key]["requests"]} for key in sorted(left)]}


async def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--review-results", type=Path)
    mode.add_argument("--calibrate-judge", type=Path, help="Saved judge labels; comparison is offline")
    mode.add_argument("--compare", type=Path, help="Baseline results.json for paired comparison")
    parser.add_argument("--variant", type=Path)
    parser.add_argument("--human-labels", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="Directory for execution; JSON file otherwise")
    args = parser.parse_args(argv)
    try:
        if args.execute:
            if not args.config:
                raise ValueError("Execution requires explicit provider/model configuration")
            result = await evaluate(args.config, args.output, allow_model_requests=True)
            print(json.dumps({k: result[k] for k in ("mode", "real_model_executions", "real_model_requests", "summary")}, indent=2))
            return 0 if result["summary"]["baseline_ready_for_comparison"] else 1
        if args.review_results:
            if not args.human_labels:
                raise ValueError("Human labels are required")
            result = apply_human_reviews(json.loads(args.review_results.read_text()), json.loads(args.human_labels.read_text()))
        elif args.calibrate_judge:
            if not args.human_labels:
                raise ValueError("Human calibration labels are required")
            result = calibrate(json.loads(args.calibrate_judge.read_text()), json.loads(args.human_labels.read_text()))
        elif args.compare:
            if not args.variant:
                raise ValueError("Variant results required")
            result = paired_comparison(json.loads(args.compare.read_text()), json.loads(args.variant.read_text()))
        else:
            result = await dry_run(config=args.config)
        write_json(args.output, result)
        if args.review_results:
            write_report(args.output.with_suffix(".md"), result)
        print(json.dumps(result.get("summary", result), indent=2))
        return 0
    except (ValueError, TypeError, KeyError, OSError):
        parser.error("Evaluation configuration, dataset or review is invalid; no private exception details retained")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
