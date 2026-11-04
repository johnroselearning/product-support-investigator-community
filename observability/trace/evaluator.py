"""Conservative execution checks, not a semantic truth or reasoning evaluator."""
# Derived from SKILL.md: Investigation Principles, Workflow, Hypotheses,
# Output Contract, and Final Quality Gate. Explicit attestations are adapter-owned.
CHECKLIST = {
    'classify_request': 'classify_request',
    'decide_skill_usage': 'decide_skill_usage',
    'collect_issue_context': 'collect_issue_context',
    'select_tools_conditionally': 'select_tools',
    'use_read_only_default': None,
    'separate_observed_inferred_unknown': 'classify_evidence',
    'test_hypotheses': 'test_hypotheses',
    'avoid_unsupported_claims': 'validate_final_response',
    'record_confidence': 'calculate_confidence',
    'disclose_missing_evidence': 'validate_final_response',
}

def evaluate(trace):
    t = trace.as_dict() if hasattr(trace, 'as_dict') else trace
    phases = {p['phase_id']: p for p in t['phases']}
    checks = []
    for key, phase in CHECKLIST.items():
        applicable = t['skill_applied'] or key in ('classify_request', 'decide_skill_usage', 'use_read_only_default')
        ok = phases[phase]['status'] == 'passed' if phase else t['writes_completed'] == 0 or (not t['read_only_mode'] and t['user_authorization_present'])
        if key == 'record_confidence':
            ok = ok and t['final_confidence'] is not None
        if key == 'test_hypotheses':
            ok = ok and any(h.get('status') in ('supported', 'rejected', 'inconclusive') and h.get('evidence_references') for h in t['hypotheses'])
        if key == 'separate_observed_inferred_unknown':
            ok = ok and bool(t['evidence_summary'])
        if key == 'select_tools_conditionally':
            ok = ok and bool(t['tools_considered']) and all(x.get('reason') for x in t['tools_considered'])
        if key in ('avoid_unsupported_claims', 'disclose_missing_evidence'):
            ok = ok and any(e['event_type'] == 'response_check' and e.get('check_id') == key and e.get('passed') is True for e in t['events'])
        status = ('passed' if ok else 'failed') if applicable else 'skipped'
        checks.append({'id': key, 'status': status, 'evidence': 'Recorded execution satisfies check' if ok else ('Not applicable to skipped skill' if not applicable else 'Required completion evidence missing')})
    return {'passed': all(c['status'] != 'failed' for c in checks), 'checks': checks}
