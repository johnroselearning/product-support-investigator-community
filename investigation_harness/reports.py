"""Deterministic report checks; critic approval is never evidence or permission."""
import re

from .contracts import REPORT, validate


def needs_critic(report, state):
    return bool(report["unknowns"] or state.questions or
                any(e.get("contradicts") or e.get("stale") for e in state.evidence) or
                any(h["contradictions"] for h in report["hypotheses"]) or
                any(a.get("status") in ("partial", "empty") for a in state.actions) or
                any(state.scope.conflict(key) for key in state.scope.candidates) or
                any(c["consequential"] or c["kind"] in ("causal", "blame", "deployed", "absence")
                    for c in report["claims"]))


def check_report(report, state):
    validate(report, REPORT)
    by_id = {e["id"]: e for e in state.evidence}
    problems = []
    for index, claim in enumerate(report["claims"]):
        refs = claim["refs"]
        if not refs or any(ref not in by_id for ref in refs):
            problems.append((index, "unsupported_reference"))
            continue
        if claim["kind"] == "observed":
            if not claim["text"] or not any(claim["text"] in by_id[ref]["excerpt"] for ref in refs):
                problems.append((index, "unsupported_observation"))
        elif claim["kind"] == "inferred":
            # Additional conservative guard, not a semantic truth evaluator.
            if re.search(r"\b(caused|root cause|confirmed|responsible|blame|deployed|no failures?)\b", claim["text"], re.I):
                problems.append((index, "strong_inference"))
        else:
            # v1 has no machine-verifiable causal proof/attribution contract.
            problems.append((index, "unverified_strong_claim"))
    for hypothesis in report["hypotheses"]:
        if not hypothesis["support"] or any(ref not in by_id for ref in hypothesis["support"] + hypothesis["contradictions"]):
            problems.append((-1, "unsupported_hypothesis"))
    return problems


def finalize_report(report, state):
    problems = check_report(report, state)
    invalid = {index for index, _ in problems}
    report["claims"] = [c for i, c in enumerate(report["claims"]) if i not in invalid]
    if -1 in invalid:
        report["hypotheses"] = []
    investigation = state.selected_skill is not None
    if state.understanding.get("context") == "hypothetical":
        report["answer"] = "Hypothetical discussion: " + report["answer"]
    elif investigation or state.understanding.get("route") == "direct_retrieval":
        # No unsupported factual prose may bypass the claim contract via a summary.
        report["answer"] = "Evidence gathered; source statements remain unverified."
        if investigation:
            report["answer"] += " Insufficient evidence to determine the root cause."
    gaps = list(dict.fromkeys(report["unknowns"] + state.questions))
    if any(e.get("stale") for e in state.evidence):
        gaps.append("Some evidence is stale; current state remains unverified.")
    if any(e.get("contradicts") for e in state.evidence):
        gaps.append("Conflicting evidence remains; consider both observations.")
    for action in state.actions:
        if action.get("status") == "empty":
            gaps.append("Empty query results do not prove that no failure occurred.")
        elif action.get("status") == "partial":
            gaps.append("Results are partial; coverage is incomplete.")
    if problems:
        gaps.append("Unsupported claims were removed by deterministic report checks.")
    report["unknowns"] = list(dict.fromkeys(gaps))
    report["adequate"] = report["adequate"] and not gaps and not problems
    report["checks"] = [reason for _, reason in problems]
    report["root_cause"] = "Unknown" if investigation else "not_applicable"
    # The complete bounded ledger preserves contradictions even if omitted in prose.
    report["evidence"] = state.evidence
    return report
