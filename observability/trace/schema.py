"""Adapter-neutral v1 execution record. No prompts, payloads or model reasoning."""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

PHASES = ('classify_request', 'decide_skill_usage', 'collect_issue_context', 'identify_service',
          'identify_time_window', 'select_tools', 'retrieve_evidence', 'classify_evidence',
          'test_hypotheses', 'produce_findings', 'calculate_confidence', 'validate_final_response')
Status = Literal['passed', 'failed', 'skipped', 'not_run']
def now():
    return datetime.now(timezone.utc).isoformat()
def identifier(prefix):
    return f'{prefix}-{uuid4().hex}'

@dataclass
class Phase:
    phase_id: str
    status: Status = 'not_run'
    started_at: str | None = None
    completed_at: str | None = None
    safe_summary: str = ''
    evidence_references: list[str] = field(default_factory=list)
    error: str | None = None

@dataclass
class Evidence:
    source: str
    locator: str
    evidence_type: Literal['observed', 'inferred', 'unknown']
    safe_summary: str
    confidence: str | float | None = None
    timestamp: str | None = None

    def __post_init__(self):
        if self.evidence_type not in ('observed', 'inferred', 'unknown'):
            raise ValueError('Invalid evidence type')

@dataclass
class Trace:
    schema_version: str = '1.0'
    trace_id: str = field(default_factory=lambda: identifier('trace'))
    correlation_id: str = field(default_factory=lambda: identifier('corr'))
    investigation_id: str = field(default_factory=lambda: identifier('inv'))
    timestamp: str = field(default_factory=now)
    request_type: str = 'unknown'
    request_summary_safe: str = ''
    skill_id: str = 'product-support-investigator'
    skill_version: str = 'unknown'
    skill_applied: bool = False
    skill_decision_reason: str = ''
    decision_confidence: float | None = None
    phases: list[Phase] = field(default_factory=lambda: [Phase(p) for p in PHASES])
    instruction_checks: list[dict] = field(default_factory=list)
    tools_considered: list[dict] = field(default_factory=list)
    tools_called: list[dict] = field(default_factory=list)
    tools_skipped: list[dict] = field(default_factory=list)
    evidence_summary: list[Evidence] = field(default_factory=list)
    hypotheses: list[dict] = field(default_factory=list)
    read_only_mode: bool = True
    writes_attempted: int = 0
    writes_completed: int = 0
    writes_blocked: int = 0
    write_reason: str | None = None
    user_authorization_present: bool = False
    final_status: str = 'incomplete'
    final_confidence: str | float | None = None
    errors: list[dict] = field(default_factory=list)
    duration_ms: float | None = None
    events: list[dict] = field(default_factory=list)

    def as_dict(self):
        return asdict(self)
