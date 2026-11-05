"""Validate structured request understanding and isolate work-item evidence.

The host model interprets language. These checks constrain its executable plan;
they do not claim to verify semantic intent or make retrieved text trustworthy.
"""
from copy import deepcopy

from .contracts import ContractError


def request_categories(decision):
    """Map validated intent; missing diagnostic fields do not mean UNCLEAR."""
    return {"general_question": ("QUESTION",),
            "customer_investigation": ("INVESTIGATION",),
            "psi_maintenance": ("MAINTENANCE",),
            "mixed": ("INVESTIGATION", "MAINTENANCE"),
            "needs_clarification": ("UNCLEAR",)}[decision]


def validate_plan(understanding):
    decision, items = understanding["decision"], understanding["work_items"]
    expected = {"general_question": [], "needs_clarification": [],
                "customer_investigation": ["customer_investigation"],
                "psi_maintenance": ["psi_maintenance"],
                "mixed": ["customer_investigation", "psi_maintenance"]}[decision]
    if sorted(i["workflow"] for i in items) != sorted(expected):
        raise ContractError("workflow_plan_mismatch")
    for item in items:
        customer = item["workflow"] == "customer_investigation"
        if item["evidence_scope"] != ("customer_application" if customer else "psi_maintenance"):
            raise ContractError("workflow_evidence_scope_mismatch")
        if customer and item["requested_action"] not in ("diagnose", "retrieve"):
            raise ContractError("customer_maintenance_action")
    # The general-question decision can never open a tool loop.
    if decision == "general_question":
        understanding["route"] = "direct_answer"
    elif decision == "needs_clarification":
        understanding["route"] = "clarify"
    elif understanding["route"] in ("direct_answer", "clarify"):
        raise ContractError("workflow_route_mismatch")


def activate(state, item, request, understanding, supplied, policy, *, mixed=False):
    state.workflow = item["workflow"]
    state.target_system = item["target_system"]
    state.telemetry_target_system = state.target_system if any(
        s.target_system == state.target_system for s in policy.resource_scopes) else "unknown"
    state.evidence_scope = item["evidence_scope"]
    state.requested_action = item["requested_action"]
    state.evidence_needs = list(item["evidence_needs"])
    if mixed and (request["scope"] or understanding["scope"]):
        raise ContractError("mixed_scope_must_be_per_work_item")
    refs = item["evidence_refs"]
    by_id = {e["id"]: e for e in supplied}
    permitted = {state.evidence_scope}
    if state.workflow == "psi_maintenance":
        permitted.add("psi_execution")
    if any(ref not in by_id or by_id[ref]["evidence_scope"] not in permitted for ref in refs):
        raise ContractError("cross_work_item_evidence")
    state.evidence = [deepcopy(by_id[ref]) for ref in dict.fromkeys(refs)]
    state.understanding = {
        **{key: deepcopy(understanding[key]) for key in
           ("goals", "context", "route", "forbidden_capabilities", "external_evidence_allowed")},
        "decision": state.workflow, "work_items": [deepcopy(item)],
        "summary": "Scoped " + state.workflow + " work item", "constraints": ["Read only"],
        "authorized_actions": ["read"], "ambiguities": [], "evidence_refs": list(refs),
        "scope": deepcopy(item["scope"] + ([] if mixed else understanding["scope"])),
    }
    if state.requested_action == "retrieve":
        state.understanding["route"] = "direct_retrieval"
    for key, value in (() if mixed else request["scope"].items()):
        state.scope.add(key, value, "user_provided", "request:scope")
    sources = {f"message:{i}": text for i, text in enumerate(request["messages"])}
    sources.update({e["supplied_at"]: e["excerpt"] for e in state.evidence if "supplied_at" in e})
    for candidate in state.understanding["scope"]:
        locator = candidate["locator"]
        if candidate["source"] == "user_provided" and (
                locator not in sources or candidate["value"] not in sources[locator]):
            raise ContractError("unsupported_scope_provenance")
        state.scope.add(candidate["field"], candidate["value"], candidate["source"], locator)
    state.event("work_item_started", status="started")
