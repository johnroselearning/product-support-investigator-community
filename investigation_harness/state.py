"""Bounded state, value provenance, safe events, and runtime-owned configuration."""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from observability.redaction import redact as redact_pii
from providers.evidence import redact as redact_secrets
from . import VERSION


def safe(value, secrets=()):
    # Reuse both existing redactors: signed URLs plus common PII. No raw event bodies.
    if isinstance(value, str):
        return redact_pii(redact_secrets(value, secrets), secrets)
    if isinstance(value, dict):
        from providers.evidence import SENSITIVE
        return {safe(str(k), secrets): "[REDACTED]" if SENSITIVE.search(str(k)) and k not in
                {"input_tokens", "output_tokens", "reserved_tokens", "reserved_token_estimate", "model_tokens", "output_tokens"}
                else safe(v, secrets)
                for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe(v, secrets) for v in value]
    return value


def utcnow():
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Limits:
    tool_calls: int = 6
    retries: int = 1
    seconds: float = 30
    call_seconds: float = 5
    model_calls: int = 12
    model_tokens: int = 240000  # Conservative byte-based reservations, not claimed usage.
    output_tokens: int = 2000
    critic_revisions: int = 1
    results: int = 20
    window_seconds: int = 3600
    response_bytes: int = 65536
    input_bytes: int = 16000
    evidence_records: int = 60
    cost_units: int = 20  # Operator-defined units, not dollars.

    def __post_init__(self):
        import math
        for name, value in asdict(self).items():
            if (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0
                    or (name not in ("seconds", "call_seconds") and type(value) is not int)):
                raise ValueError(f"Invalid limit: {name}")


@dataclass(frozen=True)
class Policy:
    """Only the trusted host constructs this; never hydrate it from model/tool content."""
    tenants: frozenset[str] = frozenset()
    environments: frozenset[str] = frozenset()
    repositories: frozenset[str] = frozenset()
    datasources: frozenset[str] = frozenset()
    projects: frozenset[str] = frozenset()
    capabilities: frozenset[str] = frozenset()
    destinations: frozenset[str] = frozenset({"local"})
    # Host-authenticated user limits; intersect with tenant policy, never replace it.
    user_scope: tuple[tuple[str, str], ...] = ()
    user_capabilities: frozenset[str] = frozenset()
    defaults: tuple[tuple[str, str], ...] = ()  # Only bounded time defaults accepted.
    model_destination: str = "local"


@dataclass
class Scope:
    candidates: dict = field(default_factory=dict)

    def add(self, key, value, source, locator):
        entry = {"value": value, "source": source, "locator": locator}
        candidates = self.candidates.setdefault(key, [])
        if entry not in candidates:
            candidates.append(entry)

    def get(self, key):
        values = {c["value"] for c in self.candidates.get(key, [])}
        return next(iter(values)) if len(values) == 1 else None

    def conflict(self, key):
        return len({c["value"] for c in self.candidates.get(key, [])}) > 1

    def inferred_only(self, key):
        return bool(self.candidates.get(key)) and all(c["source"] == "inferred" for c in self.candidates[key])


@dataclass
class State:
    run_id: str = field(default_factory=lambda: uuid4().hex)
    understanding: dict = field(default_factory=dict)
    selected_skill: str | None = None
    scope: Scope = field(default_factory=Scope)
    evidence: list = field(default_factory=list)
    hypotheses: list = field(default_factory=list)
    questions: list = field(default_factory=list)
    assumptions: list = field(default_factory=list)
    actions: list = field(default_factory=list)
    events: list = field(default_factory=list)
    usage: list = field(default_factory=list)
    critic_findings: list = field(default_factory=list)
    report: dict = field(default_factory=dict)
    budgets: dict = field(default_factory=dict)
    elapsed_seconds: float = 0
    termination: str | None = None
    calls: int = 0
    model_calls: int = 0
    reserved_tokens: int = 0
    cost: int = 0

    def event(self, phase, **fields):
        # Callers may emit only fixed enums, booleans, counts, and internal IDs.
        allowed = {"status", "route", "skill", "count", "checks", "reason", "simulated", "capability", "tool", "provider"}
        if fields.keys() - allowed:
            raise ValueError("Unsafe event field")
        self.events.append({"run_id": self.run_id, "version": VERSION, "phase": phase,
                            "timestamp": utcnow(), **safe(fields)})

    def view(self):
        return {"goal": self.understanding, "skill": self.selected_skill,
                "scope": self.scope.candidates, "evidence": self.evidence,
                "hypotheses": self.hypotheses,
                "questions": self.questions, "assumptions": self.assumptions,
                "actions": self.actions, "critic_findings": self.critic_findings,
                "budget_limits": self.budgets,
                "consumed": {"tool_calls": self.calls, "model_calls": self.model_calls,
                             "reserved_tokens": self.reserved_tokens, "cost_units": self.cost}}

    def export(self):
        return safe(asdict(self))
