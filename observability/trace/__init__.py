"""Explicit execution recording API shared by local platform adapters."""
from contextlib import contextmanager
from contextvars import ContextVar
from hashlib import sha256
from pathlib import Path
from time import monotonic
from observability.context import get_context, investigation_context
from observability.logging import get_logger
from observability.redaction import redact_mapping, redact
from .schema import Trace, Evidence, now
from .evaluator import evaluate
from .store import TraceStore

_current = ContextVar('psi_trace', default=None)
def current_trace():
    return _current.get()

class Recorder:
    def __init__(self, request_type, *, store=None, correlation_id=None, investigation_id=None):
        self.trace = Trace(request_type=request_type)
        context = get_context()
        self.trace.correlation_id = correlation_id or (context.correlation_id if context else self.trace.correlation_id)
        self.trace.investigation_id = investigation_id or (context.investigation_id if context and context.investigation_id else self.trace.investigation_id)
        skill = Path(__file__).resolve().parents[2] / 'SKILL.md'
        if skill.exists():
            self.trace.skill_version = 'sha256:' + sha256(skill.read_bytes()).hexdigest()
        self.store = store or TraceStore()
        self.started = monotonic()

    def event(self, event_type, **metadata):
        event = redact_mapping(dict(timestamp=now(), event_type=event_type, **metadata), max_depth=20)
        self.trace.events.append(event)
        get_logger('trace').info(event_type, extra={**event, 'trace_id': self.trace.trace_id, 'correlation_id': self.trace.correlation_id, 'investigation_id': self.trace.investigation_id})
        self.store.save(self.trace)

    def complete_phase(self, phase_id, summary, *, status='passed', evidence_references=(), error=None):
        if status not in ('passed', 'failed', 'skipped', 'not_run'):
            raise ValueError('Invalid phase status')
        phase = next(p for p in self.trace.phases if p.phase_id == phase_id)
        phase.started_at = phase.started_at or now()
        phase.completed_at = now() if status != 'not_run' else None
        phase.status, phase.safe_summary = status, redact(summary)[:500]
        phase.evidence_references, phase.error = list(evidence_references), redact(error)[:100] if error else None
        self.event('phase_completed', phase_id=phase_id, status=status)

    @contextmanager
    def phase(self, phase_id, summary):
        next(p for p in self.trace.phases if p.phase_id == phase_id).started_at = now()
        self.event('phase_started', phase_id=phase_id)
        try:
            yield
        except BaseException as error:
            self.complete_phase(phase_id, 'Execution failed', status='failed', error=type(error).__name__)
            raise
        else:
            self.complete_phase(phase_id, summary)

    def consider(self, tool, reason):
        item = redact_mapping({'tool': tool, 'reason': reason})
        self.trace.tools_considered.append(item)
        self.event('tool_considered', **item)

    def skip(self, tool, reason):
        self.consider(tool, reason)
        item = redact_mapping({'tool': tool, 'reason': reason})
        self.trace.tools_skipped.append(item)
        self.event('tool_call_skipped', **item, status='skipped')

    def evidence(self, **values):
        self.trace.evidence_summary.append(Evidence(**redact_mapping(values)))
        self.event('evidence_classified', evidence_type=values['evidence_type'])

    def hypothesis(self, hypothesis_id, status, evidence_references, safe_summary):
        if status not in ('untested', 'supported', 'rejected', 'inconclusive'):
            raise ValueError('Invalid hypothesis status')
        self.trace.hypotheses.append(redact_mapping(dict(hypothesis_id=hypothesis_id, status=status, evidence_references=evidence_references, safe_summary=safe_summary)))
        self.event('hypothesis_tested', hypothesis_id=hypothesis_id, status=status)

    @contextmanager
    def write(self, reason, *, authorized=False):
        t = self.trace
        t.writes_attempted += 1
        t.write_reason = redact(reason)
        t.user_authorization_present = authorized
        self.event('write_attempted', log_type='audit', reason=reason)
        if t.read_only_mode or not authorized:
            t.writes_blocked += 1
            self.event('write_blocked', log_type='audit', status='blocked')
            raise PermissionError('Write requires explicit authorization and read-only mode disabled')
        try:
            yield
        except BaseException:
            self.event('write_failed', log_type='audit', status='failed')
            raise
        else:
            t.writes_completed += 1
            self.event('write_completed', log_type='audit', status='success')

@contextmanager
def request_trace(request_type, **options):
    recorder = Recorder(request_type, **options)
    token = _current.set(recorder)
    t = recorder.trace
    with investigation_context(correlation_id=t.correlation_id, investigation_id=t.investigation_id, request_type=request_type, trace_id=t.trace_id):
        try:
            recorder.event('skill_decision_started')
            t.skill_applied = request_type in ('incident_investigation', 'support_investigation')
            t.skill_decision_reason = 'Evidence-based support investigation requested' if t.skill_applied else 'Request does not diagnose a product or service problem'
            t.request_summary_safe = request_type
            recorder.complete_phase('classify_request', 'Classified by adapter request boundary')
            recorder.complete_phase('decide_skill_usage', t.skill_decision_reason)
            recorder.event('skill_decision_completed', skill_id=t.skill_id, applied=t.skill_applied, request_type=request_type, reason=t.skill_decision_reason, confidence=t.decision_confidence)
            if not t.skill_applied:
                for phase in t.phases[2:]:
                    recorder.complete_phase(phase.phase_id, 'Skill not applicable', status='skipped')
            yield recorder
        except BaseException as error:
            t.errors.append({'error_type': type(error).__name__})
            t.final_status = 'failed'
            raise
        finally:
            t.instruction_checks = evaluate(t)['checks']
            if any(p.status == 'failed' for p in t.phases):
                t.final_status = 'failed'
            if t.final_status != 'failed':
                t.final_status = 'skipped' if not t.skill_applied else ('completed' if evaluate(t)['passed'] and all(p.status in ('passed', 'skipped') for p in t.phases) else 'incomplete')
            t.duration_ms = round((monotonic() - recorder.started)*1000, 2)
            try:
                recorder.event('request_completed', status=t.final_status)
            finally:
                _current.reset(token)
