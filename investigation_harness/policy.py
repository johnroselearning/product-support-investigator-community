"""Execution checks independent of semantic decisions, descriptions and critic approval."""
from datetime import datetime
from pathlib import PurePosixPath

from .contracts import ContractError, SCOPE_FIELDS, validate


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timezone required")
    return parsed


def prepare(action, state, registry, policy, limits, *, use_defaults=True):
    """Resolve known scope, then safe defaults. Never default a security boundary."""
    inputs = dict(action.get("inputs", {}))
    binding = registry.bindings.get(action.get("capability"))
    if not binding:
        return inputs
    properties = binding.input_schema["properties"]
    for key in SCOPE_FIELDS:
        if key in properties and key not in inputs and state.scope.get(key) is not None:
            inputs[key] = state.scope.get(key)
    for key, value in policy.defaults if use_defaults else ():
        if key not in ("start", "end"):
            raise ValueError("Only time defaults permitted")
        if key in properties and key not in inputs and not state.scope.candidates.get(key):
            inputs[key] = value
            state.scope.add(key, value, "configured", "host:bounded-default")
            assumption = f"Configured {key}: {value}"
            if assumption not in state.assumptions:
                state.assumptions.append(assumption)
    if "limit" in properties and "limit" not in inputs:
        inputs["limit"] = min(limits.results, binding.max_results)
    return inputs


def readiness(action, inputs, state, registry, policy, limits, remaining):
    checks = {key: "not_checked" for key in ("capability", "availability", "schema", "context", "authorization", "limits")}
    name = action.get("capability")
    capability = registry.capabilities.get(name)
    binding = registry.bindings.get(name)
    checks["capability"] = "passed" if capability else "unavailable_capability"
    checks["availability"] = "passed" if binding and binding.available() else "unavailable_tool"
    if not capability or not binding:
        return checks
    try:
        validate(inputs, binding.input_schema)
        checks["schema"] = "passed"
    except ContractError as error:
        checks["schema"] = "missing_input" if "missing_input" in str(error) else "invalid_input"
        if checks["schema"] == "invalid_input":
            return checks  # Do not interpret malformed/unhashable fields as scope.
    missing = [key for key in capability.required_context if not inputs.get(key)]
    ambiguous = [key for key in capability.required_context if state.scope.conflict(key)]
    # Explicit action fields do not erase conflicting or inferred boundaries.
    for key in ("tenant", "environment", "repository", "datasource", "issue", "service", "start", "end"):
        if key in inputs and (state.scope.inferred_only(key) or not state.scope.candidates.get(key)):
            ambiguous.append(key)
    checks["context"] = "ambiguous_scope" if ambiguous else "missing_input" if missing else "passed"
    granted = name in policy.capabilities and name in policy.user_capabilities
    granted = granted and name not in state.understanding.get("forbidden_capabilities", [])
    granted = granted and state.understanding.get("external_evidence_allowed", True)
    granted = granted and binding.effects == "read" and binding.destination in policy.destinations
    scopes = {"tenant": policy.tenants, "environment": policy.environments,
              "repository": policy.repositories, "datasource": policy.datasources}
    for key, allowed in scopes.items():
        if key in inputs:
            granted = granted and inputs[key] in allowed
    for key, value in policy.user_scope:
        if key in inputs:
            granted = granted and inputs[key] == value
    for key in SCOPE_FIELDS:
        if key in inputs and state.scope.get(key) is not None:
            granted = granted and inputs[key] == state.scope.get(key)
    if "issue" in inputs:
        import re
        granted = granted and bool(re.fullmatch(r"[A-Z][A-Z0-9_]*-\d+", inputs["issue"]))
        granted = granted and inputs["issue"].split("-")[0] in policy.projects
    if "path" in inputs:
        path = PurePosixPath(inputs["path"])
        granted = granted and not path.is_absolute() and ".." not in path.parts
    checks["authorization"] = "passed" if granted else "authorization_denial"
    bounded = (state.calls < limits.tool_calls and state.cost + binding.cost_units <= limits.cost_units
               and remaining > binding.minimum_timeout and remaining > 0
               and 0 < inputs.get("limit", 0) <= min(limits.results, binding.max_results))
    if "start" in inputs or "end" in inputs:
        try:
            bounded = bounded and 0 < (timestamp(inputs["end"]) - timestamp(inputs["start"])).total_seconds() <= limits.window_seconds
        except (ValueError, KeyError, TypeError):
            bounded = False
    # A cursor is usable only if an identical prior query returned it.
    if inputs.get("cursor"):
        wanted = {k: v for k, v in inputs.items() if k != "cursor"}
        bounded = bounded and any(a.get("capability") == name and a.get("next_cursor") == inputs["cursor"]
                                  and {k: v for k, v in a.get("inputs", {}).items() if k != "cursor"} == wanted
                                  for a in state.actions)
    checks["limits"] = "passed" if bounded else "limit_exceeded"
    return checks


def failure_reason(checks):
    # Permissions and ambiguity outrank missing fields; retain all independent checks.
    for reason in ("authorization_denial", "ambiguous_scope", "unavailable_capability", "unavailable_tool",
                   "invalid_input", "missing_input", "limit_exceeded"):
        if reason in checks.values():
            return reason
    return None
