"""Local regression selection only. No issue text is an execution input."""
from copy import deepcopy
import re

from .contracts import ContractError, obj, string, validate

_CASES = (
    ("routing-scope-v1", "wrong_repository", "wrong_repository", "test_cross_scope_repository_and_datasource_are_blocked"),
    ("capability-selection-v1", "unnecessary_grafana_call", "unnecessary_grafana", "test_irrelevant_grafana_call_is_blocked"),
    ("followup-context-v1", "lost_followup_context", "multiturn", "test_followup_context_is_retained"),
    ("forge-contract-v1", "invalid_forge_response", "forge_response", "test_invalid_forge_response_contract"),
    ("redaction-v1", "unsafe_evidence_disclosure", "sensitive_draft", "test_drafts_never_copy_customer_content"),
    ("provider-failure-v1", "tool_failure", "timeout", "test_provider_failure_is_not_customer_causation"),
    ("workflow-contract-v1", "feature_request", "scoped_capabilities", "test_customer_and_psi_roles_use_separate_resources"),
)


def catalog():
    return [{"test_id": test_id, "applicable_defect_types": [defect],
             "inputs": obj({"case_id": string(values=[case])}),
             "execution_environment": "local_synthetic",
             "required_permissions": ["human_regression_approval"], "timeout_seconds": 30,
             "local_check": "forge-app/src/response.test.mjs" if test_id == "forge-contract-v1" else "tests/test_workflows.py:WorkflowTests." + check,
             "result_format": obj({"test_id": string(values=[test_id]),
                                   "outcome": string(values=("succeeded", "failed", "blocked", "unknown")),
                                   "duration_ms": {"type": "number", "minimum": 0},
                                   "validation": string(values=("local_synthetic",))})}
            for test_id, defect, case, check in _CASES]


def select_regression(defect_type, test_id, inputs, *, approved=False, work_item_id=None):
    """Approval is supplied by trusted host/UI code, never inferred from an issue."""
    if type(approved) is not bool:
        raise ContractError("invalid_regression_approval")
    if work_item_id is not None and (not isinstance(work_item_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", work_item_id)):
        raise ContractError("opaque_work_item_id_required")
    entry = next((e for e in catalog() if e["test_id"] == test_id and
                  defect_type in e["applicable_defect_types"]), None)
    if entry is None:
        raise ContractError("test_not_allowlisted_for_defect")
    validate(inputs, entry["inputs"])
    return {"test_id": test_id, "defect_type": defect_type, "work_item_id": work_item_id, "validated_inputs": deepcopy(inputs),
            "approval": "approved" if approved else "proposed", "execution": "not_run",
            "execution_environment": entry["execution_environment"],
            "required_permissions": entry["required_permissions"],
            "timeout_seconds": entry["timeout_seconds"], "result_format": entry["result_format"]}


def proposed_regression(defect_type, *, work_item_id=None):
    entry = next((e for e in catalog() if defect_type in e["applicable_defect_types"]), None)
    if entry is None:
        raise ContractError("unknown_defect_type")
    case = entry["inputs"]["properties"]["case_id"]["enum"][0]
    return select_regression(defect_type, entry["test_id"], {"case_id": case}, work_item_id=work_item_id)
