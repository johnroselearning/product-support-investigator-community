"""Review-only synthetic handovers. No raw customer material is accepted/copied."""
import re
from uuid import uuid4

from .contracts import ContractError
from .regressions import proposed_regression

# Fixed safe descriptions make the default draft conservative. Detailed free text
# requires a separate human editorial review outside this API.
_FINDINGS = {
    "wrong_repository": ("PSI repository selection needs review",
        "Select only a repository mapped to the work item's workflow and target.",
        "Configure distinct synthetic customer and PSI repositories; request a customer code check.",
        "A wrong selection can leave the customer investigation incomplete."),
    "unnecessary_grafana_call": ("PSI capability selection needs review",
        "Query Grafana only for a declared evidence need with known scope and inputs.",
        "Ask a general question or a repository-only question using synthetic context.",
        "Unnecessary queries can add latency and consume evidence budgets."),
    "lost_followup_context": ("PSI follow-up context needs review",
        "Retain established scope from earlier conversation turns.",
        "Supply a synthetic service in one turn, then request a check of the same service.",
        "Lost context can cause repeated clarification or incomplete checks."),
    "invalid_forge_response": ("PSI Forge response contract needs review",
        "Return the existing bounded Jira action envelope or a sanitized error envelope.",
        "Exercise the Forge response validator with a synthetic malformed envelope.",
        "An invalid envelope can prevent Rovo from using retrieved evidence."),
    "unsafe_evidence_disclosure": ("PSI maintenance draft privacy needs review",
        "Exclude customer logs, private code, tokens, personal data and sensitive URLs.",
        "Supply synthetic sensitive strings; prepare a review-only maintenance draft.",
        "Unsafe drafts could disclose sensitive evidence if manually shared."),
    "tool_failure": ("PSI evidence retrieval failure needs review",
        "Report provider failures as limitations and keep customer causation unknown.",
        "Use a synthetic provider that raises a timeout during a bounded read.",
        "Missing evidence can limit diagnosis; customer impact remains unverified."),
    "feature_request": ("PSI scoped capability improvement proposal",
        "New capabilities preserve workflow separation, known resource mappings and read-only defaults.",
        "Exercise separate synthetic customer and PSI capability roles before proposing an extension.",
        "Potential benefit and implementation scope require human review."),
}


def _observations(state, defect_type):
    observations = []
    for index, event in enumerate(state.events):
        status, capability = event.get("status"), event.get("capability")
        if event.get("phase") == "call" and status == "execution_failure":
            if defect_type == "tool_failure":
                observations.append({"reference": f"event:{index}", "fact": "A PSI provider call failed; no application cause was established."})
        if defect_type == "wrong_repository" and status in ("cross_scope_denied", "authorization_denial") and capability in (
                "read_repository_file", "list_commits", "read_repository_issue", "read_pull_request", "compare_revisions"):
            observations.append({"reference": f"event:{index}", "fact": "A repository access attempt was blocked by scope checks."})
        if defect_type == "unnecessary_grafana_call" and status == "irrelevant_capability" and capability in ("search_logs", "query_metrics"):
            observations.append({"reference": f"event:{index}", "fact": "A telemetry query was blocked as irrelevant to the declared evidence need."})
    return observations


def prepare_draft(state, defect_type, *, requested=False):
    """Return a separate linked maintenance artifact, never a GitHub mutation.

    Missing connectors alone do not establish a PSI defect. A caller may explicitly
    request an unverified draft; observable failures support only the facts stated.
    """
    if defect_type not in _FINDINGS or type(requested) is not bool:
        raise ContractError("invalid_maintenance_request")
    observed = _observations(state, defect_type)
    if not requested and not observed:
        raise ContractError("maintenance_handover_not_supported")
    parent = state.parent_investigation_id if state.workflow == "psi_maintenance" else (state.parent_investigation_id or state.run_id)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", state.run_id) or (
            parent is not None and not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", parent)):
        raise ContractError("opaque_investigation_id_required")
    title, expected, reproduction, impact = _FINDINGS[defect_type]
    work_item_id = state.work_item_id if state.workflow == "psi_maintenance" else uuid4().hex
    draft = {
        "status": "draft_review_required", "workflow": "psi_maintenance",
        "work_item_id": work_item_id,
        "parent_investigation_id": parent, "investigation_id": state.run_id,
        "defect_type": defect_type, "title": title, "expected_behavior": expected,
        "actual_behavior": "Observed PSI execution limitation; see sanitized facts." if observed else
                           "Reported PSI behavior; reproduction and cause are unverified.",
        "reproduction_steps": [reproduction, "Use only local synthetic fixtures; record the result for review."],
        "evidence": {"observed": observed,
                     "inferred": ["This behavior may warrant a PSI regression; human review is required."],
                     "unknown": ["Whether this reproduces in the user's host.", "PSI defect root cause and customer application cause."]},
        "impact": impact, "proposed_test": proposed_regression(defect_type, work_item_id=work_item_id),
        "acceptance_criteria": [expected, "The allowlisted regression passes using synthetic inputs.",
                                "The draft contains no customer evidence and requires review before manual filing."],
        "review_note": "Review accuracy, sanitization and intended repository visibility before manually filing.",
    }
    from .state import State
    maintenance = State(run_id=work_item_id, work_item_id=work_item_id,
        parent_investigation_id=parent, trace_id=state.trace_id, correlation_id=state.correlation_id,
        workflow="psi_maintenance", target_system="psi", telemetry_target_system="psi", evidence_scope="psi_maintenance")
    maintenance.event("maintenance_draft_prepared", status="success", reason="requested" if requested else "execution_evidence")
    maintenance.event("regression_selected", status="success", test_id=draft["proposed_test"]["test_id"], reason="proposed_only")
    state.events.extend(maintenance.events)
    return draft
