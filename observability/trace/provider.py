"""Instrument provider execution without claiming downstream reasoning occurred."""
from functools import wraps
from . import current_trace, request_trace

def traced_provider(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if current_trace():
            return function(*args, **kwargs)
        with request_trace('support_investigation') as recorder:
            recorder.consider('grafana_mcp', 'Explicit bounded Grafana provider request')
            recorder.complete_phase('select_tools', 'Caller selected Grafana evidence provider')
            from .schema import now
            next(p for p in recorder.trace.phases if p.phase_id == 'retrieve_evidence').started_at = now()
            result = function(*args, **kwargs)
            status = result.get('retrieval_status', 'unknown')
            recorder.complete_phase('retrieve_evidence', 'Provider retrieval status: ' + status,
                                    status='passed' if status in ('success', 'empty') else 'failed')
            if not recorder.trace.tools_called:
                recorder.skip('grafana_mcp', 'Provider validation or configuration prevented a remote call')
            if status not in ('success', 'empty'):
                recorder.trace.errors.append({'error_type': 'EvidenceAccessLimitation', 'status': status})
            return result
    return wrapper
