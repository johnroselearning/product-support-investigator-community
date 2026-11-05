#!/usr/bin/env python3
"""Offline A/B/C capture. Scripted decisions are not model accuracy measurements.

Capture each stage before changing its sources. Counts use ceil(characters/4),
not provider billing or token reservations. No network calls or customer data.
"""
import argparse
import asyncio
from collections import Counter
from dataclasses import replace
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from investigation_harness.engine import Harness
from investigation_harness.evaluate import DATA, grade
from investigation_harness.fixtures import fixture_registry, policy, scenario
from investigation_harness.semantic import ConservativeCritic
from investigation_harness.registry import Registry
from investigation_harness.state import State
from observability.logging import configure_logging


def estimate(value):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, allow_nan=False)
    return math.ceil(len(text) / 4)


class Meter:
    def __init__(self, adapter):
        self.adapter = adapter
        self.destination = adapter.destination
        self.simulated = True
        self.inputs = self.outputs = 0
        self.references = Counter()

    async def invoke(self, method, *args):
        payload = args[1] if method == "decide" else args[0]
        self.inputs += estimate(payload)
        self.references.update((payload.get("method") or {}).keys())
        result = await getattr(self.adapter, method)(*args)
        self.outputs += estimate(result.value)
        return result

    async def decide(self, *args):
        return await self.invoke("decide", *args)

    async def review(self, *args):
        return await self.invoke("review", *args)


def extra_case(name):
    if name in ("http500", "missing_correlation"):
        request, adapter = scenario("checkout")
        request["messages"] = ["Investigate HTTP 500 from POST /checkout in production at 09:05 UTC; " +
                               ("request req-123." if name == "http500" else "no correlation ID is available.")]
        adapter.understanding["summary"] = request["messages"][0]
        adapter.understanding["work_items"][0]["evidence_needs"] = ["search_logs"]
    elif name == "github_only":
        request, adapter = scenario("repository")
        adapter.understanding["route"] = "investigate_external"
        adapter.understanding["goals"] = ["diagnose"]
        adapter.understanding["work_items"][0]["requested_action"] = "diagnose"
        adapter.understanding["work_items"][0]["evidence_needs"] = ["read_repository_file"]
    elif name == "maintenance":
        request, adapter = scenario("repository")
        adapter.understanding["decision"] = "psi_maintenance"
        item = adapter.understanding["work_items"][0]
        item.update(workflow="psi_maintenance", evidence_scope="psi_maintenance")
    else:
        request, adapter = scenario("explain")
        adapter.understanding.update(decision="needs_clarification", route="clarify",
                                     ambiguities=["Which system should be investigated?"])
    registry, config = fixture_registry("repository"), policy()
    if name == "maintenance":
        registry.bind(replace(registry.bindings["read_repository_file"], roles=frozenset({"psi_github"}),
                              permitted_workflows=frozenset({"psi_maintenance"})))
        config = replace(config, resource_scopes=tuple(replace(s, role="psi_github") for s in config.resource_scopes
                                                      if s.role == "customer_github"))
    return request, adapter, registry, config


async def capture(label, repeats, profiler=None):
    cases = json.loads(DATA.read_text())["cases"]
    rows = []
    configure_logging(stream=io.StringIO())
    extras = ["github_only", "maintenance", "unclear", "http500", "missing_correlation"]
    for name in [c["id"] for c in cases] + extras:
        elapsed = []
        for repeat in range(repeats):
            if name in extras:
                request, adapter, registry, config = extra_case(name)
            else:
                case = next(c for c in cases if c["id"] == name)
                request, adapter = scenario(name)
                request = case["request"]
                registry, config = fixture_registry(name), policy()
            meter, critic = Meter(adapter), Meter(ConservativeCritic())
            started = time.perf_counter()
            # Profile the first repeat only: timing repeats must not inflate the
            # scenario corpus or manufacture perfectly shared prefixes.
            class ScenarioObserver:
                def observe(self, stage, payload, **metadata):
                    return profiler.observe(stage, payload, **{**metadata, "scenario": name,
                        "synthetic": True, "comparison_group": label,
                        "kind": "deterministic_critic" if stage == "critic" else metadata["kind"]})

                def attach_usage(self, *args, **kwargs):
                    return profiler.attach_usage(*args, **kwargs)

            state = await Harness(meter, registry, config, critic=critic,
                profiler=ScenarioObserver() if profiler is not None and repeat == 0 else None).run(request)
            elapsed.append((time.perf_counter() - started) * 1000)
        executed = [a["capability"] for a in state.actions if "attempt" in a]
        if name not in extras:
            checks = grade(state, case["expected"])
            unnecessary = max(0, state.calls - case["expected"]["max_calls"])
        else:
            checks = {"routing": state.workflow == {"github_only": "customer_investigation", "http500": "customer_investigation", "missing_correlation": "customer_investigation", "maintenance": "psi_maintenance",
                                                    "unclear": "needs_clarification"}[name],
                      "tool_choice": executed == ([] if name == "unclear" else ["search_logs"] if name in ("http500", "missing_correlation") else ["read_repository_file"]),
                      "readiness": state.termination not in ("invalid_contract", "execution_failure", "budget_exhausted"),
                      "evidence_support": len(state.evidence) == (0 if name == "unclear" else 1)}
            unnecessary = max(0, state.calls - (0 if name == "unclear" else 1))
        rows.append({"id": name, "input_tokens_estimate": meter.inputs + critic.inputs,
                     "output_tokens_estimate": meter.outputs + critic.outputs,
                     "total_tokens_estimate": meter.inputs + critic.inputs + meter.outputs + critic.outputs,
                     "reference_presentations": dict(meter.references), "tool_calls": state.calls,
                     "unnecessary_tool_calls_against_fixture_budget": unnecessary,
                     "model_calls_including_deterministic_critic": state.model_calls,
                     "termination": state.termination, "checks": checks,
                     "local_latency_ms_median": round(statistics.median(elapsed), 3),
                     "provider_usage": "unavailable; scripted decisions"})
    inventory = []
    for path in sorted({ROOT / "SKILL.md", ROOT / "forge-app/prompts/investigator.md", *ROOT.glob("references/*.md")}):
        data = path.read_bytes()
        inventory.append({"path": str(path.relative_to(ROOT)), "lines": len(data.splitlines()),
                          "tokens_estimate": estimate(data.decode()), "sha256": hashlib.sha256(data).hexdigest()})
    if label == "A":
        baseline = json.loads((ROOT / "docs/optimization/baseline-inventory.json").read_text())
        inventory = [{"path": r["path"], "lines": r["lines"], "tokens_estimate": r["estimated_tokens"], "sha256": r["sha256"]}
                     for r in baseline if r["path"] in ("SKILL.md", "forge-app/prompts/investigator.md") or r["path"].startswith("references/")]
    return {"label": label, "mode": "offline-scripted-simulation", "token_method": "ceil(unicode_characters/4) per message",
            "repeats": repeats, "network_calls": 0, "inventory": inventory, "cases": rows,
            "totals": {key: sum(row[key] for row in rows) for key in
                       ("input_tokens_estimate", "output_tokens_estimate", "total_tokens_estimate", "tool_calls",
                        "unnecessary_tool_calls_against_fixture_budget")}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True, choices=("A", "B", "C"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--profile-output", type=Path, help="Opt-in sanitized payload profile; separate from historical benchmark results")
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    if args.profile_output and args.profile_output.resolve() == args.output.resolve():
        parser.error("Benchmark and profiling outputs must use separate paths")
    profiler = None
    if args.profile_output:
        from scripts.profile_payloads import PayloadProfiler
        profiler = PayloadProfiler(enabled=True)
    if args.label in ("A", "B"):
        # Reproduce the pre-optimization harness loading/catalog behavior using
        # today's compact core. Only context presentation changes; policy, tool
        # execution, evidence and evaluation contracts are shared with C.
        source_root = ROOT / "docs/optimization/baseline" if args.label == "A" else ROOT
        if args.label == "A":
            original = json.loads((ROOT / "docs/optimization/baseline-inventory.json").read_text())
            for name in ("SKILL.md", "references/evidence-providers.md"):
                digest = hashlib.sha256((source_root / name).read_bytes()).hexdigest()
                if digest != next(r["sha256"] for r in original if r["path"] == name):
                    parser.error("Baseline source digest mismatch: " + name)
        def legacy_context(state):
            if not state.selected_skill:
                return None
            sections = {"SKILL.md": ("Investigation Principles", "Evidence Model", "Root Cause Assessment"),
                        "references/evidence-providers.md": ("Trust and privacy",)}
            result = {}
            for name, headings in sections.items():
                text = (source_root / name).read_text()
                result[name] = {"sha256": hashlib.sha256(text.encode()).hexdigest(),
                               "sections": {h: text.split("## " + h + "\n", 1)[1].split("\n## ", 1)[0] for h in headings}}
            return result
        original_catalog, original_view = Registry.catalog, State.view
        def catalog(self, state=None, policy=None, **kwargs):
            return original_catalog(self, state, policy, relevant_only=False)
        def view(self):
            result = original_view(self)
            result.pop("categories", None)
            return result
        with patch("investigation_harness.engine.load_context", legacy_context), patch.object(Registry, "catalog", catalog), patch.object(State, "view", view):
            result = asyncio.run(capture(args.label, args.repeats, profiler))
    else:
        result = asyncio.run(capture(args.label, args.repeats, profiler))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    if profiler is not None:
        from scripts.profile_payloads import write_report
        profile = profiler.report()
        profile["benchmark"] = {"label": args.label, "mode": result["mode"],
            "profiled_repeats": 1, "timing_repeats": args.repeats, "network_calls": 0,
            "case_checks_passed": sum(all(row["checks"].values()) for row in result["cases"]),
            "cases": len(result["cases"]), "source_inventory": result["inventory"]}
        write_report(args.profile_output, profile)
    print(json.dumps(result["totals"]))
    return 0 if all(all(r["checks"].values()) for r in result["cases"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
