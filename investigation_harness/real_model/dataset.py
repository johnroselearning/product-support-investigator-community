"""Synthetic cases and gold are loaded separately; only requests enter the model."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from ..contracts import RECORD, RESULT, SCOPE, array, obj, string, validate
from ..fixtures import policy as fixture_policy
from ..registry import (Binding, CAPABILITIES, GITHUB_OPERATIONS, Registry, input_contract)

DATA = Path(__file__).resolve().parents[2] / "tests/evaluation/real_model"
REQUEST = obj({"messages": array(string(4000)), "artifacts": array(RECORD), "scope": SCOPE})
CATEGORIES = {"determinable": 3, "unknown": 3, "prompt_injection": 2,
              "conflicting_evidence": 1, "tenant_isolation": 1}


def load_cases(directory=DATA):
    cases = [json.loads(path.read_text()) for path in sorted((Path(directory) / "cases").glob("*.json"))]
    if len(cases) != 10 or len({c["id"] for c in cases}) != 10:
        raise ValueError("Expected ten unique evaluation cases")
    from collections import Counter
    if Counter(c["category"] for c in cases) != CATEGORIES:
        raise ValueError("Dataset category distribution changed")
    known = {c.name for c in CAPABILITIES}
    for case in cases:
        if set(case) != {"id", "category", "difficulty", "request", "tools", "max_tool_calls"}:
            raise ValueError("Invalid public case fields")
        validate(case["id"], {"type": "string", "pattern": r"RM-[0-9]{3}", "maxLength": 6})
        if case["difficulty"] not in ("easy", "medium", "hard"):
            raise ValueError("Invalid difficulty")
        validate(case["request"], REQUEST)
        if not case["request"]["messages"] or not case["request"]["scope"].get("tenant"):
            raise ValueError("Case requires a user request and explicit tenant")
        if not isinstance(case["tools"], dict) or case["tools"].keys() - known:
            raise ValueError("Only existing read-only capabilities are supported")
        if type(case["max_tool_calls"]) is not int or not 0 <= case["max_tool_calls"] <= 6:
            raise ValueError("Invalid tool budget")
        for spec in case["tools"].values():
            if set(spec) != {"available", "response"} or type(spec["available"]) is not bool:
                raise ValueError("Invalid tool fixture")
            validate(spec["response"], RESULT)
    return cases


def load_gold(case_id, directory=DATA):
    gold = json.loads((Path(directory) / "gold" / (case_id + ".json")).read_text())
    required = {"id", "root_cause", "partial_root_causes", "expected_evidence", "required_tools",
                "forbidden_tools", "abstention", "security_canaries", "injection_markers",
                "injection_actions", "injection_scope", "missing_evidence", "contradiction", "limitations", "rationale"}
    if set(gold) != required or gold["id"] != case_id or gold["abstention"] not in ("required", "incorrect"):
        raise ValueError("Invalid gold answer")
    for name in ("partial_root_causes", "expected_evidence", "required_tools", "forbidden_tools",
                 "security_canaries", "injection_markers", "injection_actions", "missing_evidence", "limitations"):
        if not isinstance(gold[name], list) or any(not isinstance(s, str) or not s for s in gold[name]):
            raise ValueError("Invalid gold list")
    validate(gold["injection_scope"], SCOPE)
    if (not isinstance(gold["root_cause"], str) or not gold["root_cause"] or
            (gold["root_cause"] == "Unknown") != (gold["abstention"] == "required")):
        raise ValueError("Gold root cause and abstention disagree")
    return gold


def dataset_digest(directory=DATA):
    digest = hashlib.sha256()
    for path in sorted(Path(directory).glob("*/*.json")):
        digest.update(str(path.relative_to(directory)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def synthetic_environment(case, destination="local"):
    """No host connector discovery. The entire execution registry is local fixtures."""
    # Fixed fixture timestamps are historical observations, not live freshness claims.
    registry = Registry(tuple(replace(c, freshness_seconds=0) for c in CAPABILITIES))
    audit = []
    scope = case["request"]["scope"]
    for name, spec in case["tools"].items():
        async def handle(inputs, timeout, name=name, spec=deepcopy(spec)):
            unauthorized = any(k in inputs and inputs[k] != v for k, v in scope.items())
            audit.append({"capability": name, "inputs": deepcopy(inputs),
                          "authorized": not unauthorized, "effects": "read", "destination": "local"})
            if unauthorized:
                raise ValueError("Synthetic scope boundary denied")
            return deepcopy(spec["response"])
        roles = frozenset() if name == "fetch_issue" else frozenset({
            "customer_github" if name in GITHUB_OPERATIONS else "customer_grafana"})
        registry.bind(Binding(name, "synthetic", "evaluation.fixture." + name, input_contract(name),
                              handle, available=lambda spec=spec: spec["available"],
                              output_schema=RESULT, roles=roles))
    base = fixture_policy()
    capabilities = frozenset(case["tools"])
    config = replace(base, capabilities=capabilities, user_capabilities=capabilities,
                     model_destination=destination, destinations=frozenset({"local", destination}))
    return registry, config, audit
