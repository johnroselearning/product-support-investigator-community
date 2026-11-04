"""Small, strict JSON contract validator. Unsupported schema keywords fail closed."""
import json
import math
import re


class ContractError(ValueError):
    pass


def validate(value, schema, path="$"):
    supported = {"type", "properties", "required", "additionalProperties", "items", "enum",
                 "minLength", "maxLength", "pattern", "minimum", "maximum", "maxItems"}
    if set(schema) - supported:
        raise ContractError("unsupported_schema")
    types = {"object": dict, "array": list, "string": str, "integer": int,
             "number": (int, float), "boolean": bool, "null": type(None)}
    kind = schema["type"]
    if not isinstance(value, types[kind]) or (kind in ("integer", "number") and isinstance(value, bool)):
        raise ContractError(f"{path}:type")
    if "enum" in schema and value not in schema["enum"]:
        raise ContractError(f"{path}:enum")
    if kind == "object":
        if set(schema.get("required", [])) - value.keys():
            raise ContractError(f"{path}:missing_input")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties", False) is not False:
            raise ContractError("unsupported_schema")
        if value.keys() - properties.keys():
            raise ContractError(f"{path}:unknown_field")
        for key, item in value.items():
            validate(item, properties[key], f"{path}.{key}")
    elif kind == "array":
        if len(value) > schema.get("maxItems", 100):
            raise ContractError(f"{path}:size")
        for item in value:
            validate(item, schema["items"], path + "[]")
    elif kind == "string":
        if not schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", 2000):
            raise ContractError(f"{path}:size")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value):
            raise ContractError(f"{path}:pattern")
    elif kind in ("number", "integer"):
        if not math.isfinite(value) or not schema.get("minimum", -math.inf) <= value <= schema.get("maximum", math.inf):
            raise ContractError(f"{path}:range")


def obj(properties, required=None):
    return {"type": "object", "properties": properties,
            "required": list(properties) if required is None else required, "additionalProperties": False}


def string(maximum=2000, values=None):
    result = {"type": "string", "maxLength": maximum}
    if values is not None:
        result["enum"] = list(values)
    return result


def array(items, maximum=20):
    return {"type": "array", "items": items, "maxItems": maximum}


IDENTIFIER = {"type": "string", "minLength": 1, "maxLength": 128,
              "pattern": r"[A-Za-z0-9_./:@+-]+"}
SCOPE_FIELDS = ("issue", "service", "environment", "tenant", "repository", "datasource", "start", "end")
SCOPE = obj({key: IDENTIFIER for key in SCOPE_FIELDS}, [])
GOALS = ("explain", "summarize", "rewrite", "retrieve", "diagnose", "discuss", "change")
ROUTES = ("direct_answer", "direct_retrieval", "investigate_supplied", "investigate_external", "clarify")
UNDERSTANDING = obj({
    "goals": array(string(values=GOALS), 7), "context": string(values=("actual", "hypothetical", "unclear")),
    "route": string(values=ROUTES), "summary": string(500),
    "scope": array(obj({"field": string(values=SCOPE_FIELDS), "value": IDENTIFIER,
                         "source": string(values=("user_provided", "inferred")), "locator": string(100)})),
    "constraints": array(string(300)), "authorized_actions": array(string(80)),
    "forbidden_capabilities": array(string(80)), "external_evidence_allowed": {"type": "boolean"},
    "ambiguities": array(string(300)), "evidence_refs": array(string(40)),
})
CLAIM = obj({"kind": string(values=("observed", "inferred", "causal", "blame", "deployed", "absence")),
             "text": string(), "refs": array(string(40)), "consequential": {"type": "boolean"}})
REPORT = obj({"answer": string(4000), "claims": array(CLAIM), "unknowns": array(string(300)),
              "hypotheses": array(obj({"statement": string(300), "support": array(string(40)),
                                       "contradictions": array(string(40))})),
              "adequate": {"type": "boolean"}})
FINDINGS = obj({"unsupported_claims": array(string(300)), "contradictions": array(string(300)),
                "alternatives": array(string(300)), "needed_evidence": array(string(300))})
RECORD = obj({"locator": string(300), "excerpt": string(2000), "kind": string(80),
              "scope": SCOPE, "timestamp": string(50), "contradicts": array(string(300))},
             ["locator", "excerpt", "kind", "scope", "timestamp"])
RESULT = obj({"status": string(values=("success", "empty", "partial", "unavailable", "execution_failure")),
              "records": array(RECORD, 100), "resolved": SCOPE, "next_cursor": string(128),
              "limitations": array(string(300))})


def json_size(value):
    return len(json.dumps(value, ensure_ascii=False, allow_nan=False).encode())
