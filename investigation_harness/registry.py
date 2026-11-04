"""Conceptual capabilities bound explicitly to trusted local adapter contracts."""
from dataclasses import dataclass
from typing import Awaitable, Callable

from .contracts import IDENTIFIER, RESULT, obj, string


@dataclass(frozen=True)
class Capability:
    name: str
    evidence: str
    coverage: str
    required_context: tuple[str, ...]
    alternatives: tuple[str, ...] = ()
    freshness_seconds: int = 3600


CAPABILITIES = (
    Capability("fetch_issue", "Issue description and scope", "A single issue; reports are unverified", ("tenant", "issue")),
    Capability("discover_service", "Service identifiers", "Tenant/environment service inventory", ("tenant", "environment"), ("fetch_issue",)),
    Capability("search_logs", "Matching log excerpts", "One configured log datasource; empty is inconclusive", ("tenant", "environment", "service", "datasource", "start", "end"), ("fetch_issue", "discover_service")),
    Capability("query_metrics", "Metric samples", "Configured metric only; correlation is not causation", ("tenant", "environment", "service", "datasource", "start", "end"), ("discover_service",)),
    Capability("retrieve_trace", "Trace spans", "One trace in a tenant and environment", ("tenant", "environment")),
    Capability("read_repository_file", "Source at an exact revision", "Source is not proof of deployed code", ("tenant", "repository")),
    Capability("deployment_metadata", "Deployment revision and time", "Configured environment's deployment record", ("tenant", "environment", "service", "repository")),
    Capability("compare_revisions", "Relevant revision difference", "Diff alone does not establish causation", ("tenant", "repository")),
    Capability("list_commits", "Recent repository commits", "Recency does not establish relevance or deployment", ("tenant", "repository")),
)


@dataclass(frozen=True)
class Binding:
    capability: str
    provider: str
    tool: str  # Exact local Python operation or discovered host tool; never guessed MCP names.
    input_schema: dict
    handler: Callable[[dict, float], Awaitable[dict]]
    available: Callable[[], bool] = lambda: True
    output_schema: dict | None = None
    effects: str = "read"
    destination: str = "local"
    cost_units: int = 1
    max_results: int = 20
    minimum_timeout: float = 0


class Registry:
    def __init__(self, capabilities=CAPABILITIES):
        self.capabilities = {c.name: c for c in capabilities}
        self.bindings = {}

    def bind(self, binding):
        if binding.capability not in self.capabilities:
            raise ValueError("Unknown capability")
        self.bindings[binding.capability] = binding

    def catalog(self):
        # Schemas and skill content are loaded only after a need is selected.
        return [{"capability": c.name, "evidence": c.evidence, "coverage": c.coverage,
                 "preconditions": list(c.required_context), "alternatives": list(c.alternatives),
                 "bound": c.name in self.bindings,
                 "available": bool(c.name in self.bindings and self.bindings[c.name].available())} for c in self.capabilities.values()]

    def contract(self, capability):
        binding = self.bindings.get(capability)
        if binding is None:
            return None
        return {"provider": binding.provider, "tool": binding.tool,
                "inputs": binding.input_schema, "outputs": binding.output_schema or RESULT,
                "effects": binding.effects, "destination": binding.destination,
                "max_results": binding.max_results,
                "freshness_seconds": self.capabilities[capability].freshness_seconds}


def input_contract(capability):
    """Actual contract of the fixture operations and the constrained Grafana bridge."""
    c = next(c for c in CAPABILITIES if c.name == capability)
    props = {key: IDENTIFIER for key in c.required_context}
    extras = {
        "retrieve_trace": {"trace_id": IDENTIFIER},
        "read_repository_file": {"path": IDENTIFIER, "revision": IDENTIFIER},
        "compare_revisions": {"base": IDENTIFIER, "head": IDENTIFIER},
        "query_metrics": {"metric": IDENTIFIER},
    }.get(capability, {})
    props.update(extras)
    required = list(props)
    props.update({"limit": {"type": "integer", "minimum": 1, "maximum": 100},
                  "cursor": string(128)})
    if capability == "search_logs":
        props["request_id"] = IDENTIFIER
    return obj(props, required + ["limit"])
