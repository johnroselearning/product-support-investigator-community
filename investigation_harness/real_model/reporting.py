"""Human-readable reports retain missing measurements and individual failures."""


def render_report(result):
    summary = result["summary"]
    def value(item):
        if item is None:
            return "Unmeasured"
        if isinstance(item, dict) and "measured" in item:
            return f'{value(item["value"])} ({item["measured"]}/{item["total"]} measured)'
        return str(round(item, 6)) if isinstance(item, float) else str(item)
    config = result["candidate_configuration"]
    lines = ["# PSI real-model evaluation", "",
             f'Provider: `{config["provider"]}`. Model: `{config["model"]}`.',
             f'Dataset SHA-256: `{result["dataset_sha256"]}`.',
             f'Investigations with confirmed submissions: {result["real_model_executions"]}. '
             f'Confirmed candidate requests: {result["real_model_requests"]}. '
             f'Finished records: {len(result["results"])} / {result["planned_runs"]}.',
             "", "## Structural simulation results", "",
             "This execution uses real model decisions and deterministic synthetic tools. "
             "Existing fixture-simulation results are reported separately in BASELINE_RESULTS.md.",
             "", "## Real-model results", "", "| Metric | Result |", "| --- | --- |"]
    for metric in ("mean_quality_score", "pass_rate", "all_five_pass_rate", "root_cause_accuracy",
                   "confident_wrong_rate", "correct_abstention_rate", "claim_support_accuracy",
                   "tool_selection_accuracy", "tool_selection_consistency", "safety_violations"):
        lines.append(f'| {metric} | {value(summary[metric])} |')
    lines += ["", "Explicit-root abstention classes: `" + str(summary["abstention_classes"]) + "`.",
              "", "## Actual usage", "", "| Role | Field | Reported total | Requests reporting / attempted |",
              "| --- | --- | --- | --- |"]
    for role in ("candidate", "judge"):
        usage = summary[role + "_usage"]
        for field, metric in usage["totals"].items():
            lines.append(f'| {role} | {field} | {value(metric["value"])} | {metric["reported_requests"]}/{metric["total_requests"]} |')
    lines += ["", "No token estimates replace provider usage. Monetary cost is unmeasured.",
              "", "## Wall-clock latency", "", "Payload profiling is disabled. Judge latency is recorded separately per judge request.",
              "", "| Stage | Mean seconds per investigation using stage | Maximum | Runs measured |", "| --- | --- | --- | --- |"]
    for stage, metric in summary["latency"].items():
        lines.append(f'| {stage} | {value(metric["mean_seconds"])} | {value(metric["max_seconds"])} | {metric["runs_measured"]} |')
    lines += ["", "Critic stages use deterministic checks in this baseline, with zero critic model requests.",
              "", "## Human-reviewed results", "", str(summary["reviewed_subsets"]["human"]),
              "", "## Independent model review", "", str(summary["reviewed_subsets"]["independent_model"]),
              "", "## Individual executions", "", "| Run | Termination | Pass | Root score | Safety violations | Review |",
              "| --- | --- | --- | --- | --- | --- |"]
    for row in result["results"]:
        score = row["score"]
        lines.append(f'| {row["key"]} | {row["status"]} | {value(score["pass"])} | {value(score["root_cause_score"])} | '
                     f'{", ".join(score["safety_violations"]) or "None detected"} | {row["review_source"] or "Unmeasured"} |')
    lines += ["", "Missing/in-progress investigations remain in plan.json; every completed record is in runs/.",
              "", "## Unmeasured dimensions and limitations", ""]
    lines += ["- " + item for item in result["limitations"]]
    lines += ["- Semantic entailment, full quality, and confident-wrong rate remain unmeasured without valid semantic review.",
              "- Raw strong-claim attempts removed by the production guard remain in each run; they are not final accepted conclusions.",
              "", "Acceptance gates: `" + str(summary["acceptance_gates"]) + "`.", ""]
    return "\n".join(lines)
