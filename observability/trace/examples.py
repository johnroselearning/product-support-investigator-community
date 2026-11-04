"""Synthetic fixtures, never claims about a real incident. Run as a module."""
import json
from pathlib import Path
from observability.logging import configure_logging
from observability.tool_calls import logged_tool_call
from . import request_trace
from .schema import PHASES

@logged_tool_call('grafana_mcp', 'query', reason='Synthetic service and incident window available')
def fixture_query(fail=False):
    if fail:
        raise TimeoutError('Synthetic timeout')
    return ['fixture-E1']

def generate(output=None):
    traces = {}
    with request_trace('incident_investigation') as r:
        with r.phase('collect_issue_context', 'Synthetic expected and actual behavior recorded'): pass
        with r.phase('identify_service', 'Synthetic checkout service identified'): pass
        with r.phase('identify_time_window', 'Synthetic incident window identified'): pass
        with r.phase('select_tools', 'Select fixture telemetry for service and time window'):
            r.consider('grafana_mcp', 'Synthetic service and incident window available')
            r.skip('github', 'No deployment or code-change signal')
        with r.phase('retrieve_evidence', 'Synthetic query returned one fixture'): fixture_query()
        with r.phase('classify_evidence', 'Classified fixture evidence'):
            r.evidence(source='fixture', locator='E1', evidence_type='observed', safe_summary='Synthetic timeout reproduced in fixture', confidence='High')
            r.evidence(source='fixture', locator='E2', evidence_type='unknown', safe_summary='Production impact not assessed', confidence=None)
        with r.phase('test_hypotheses', 'Synthetic hypothesis tested'):
            r.hypothesis('H1', 'supported', ['E1'], 'Fixture check reproduced timeout')
        with r.phase('produce_findings', 'Synthetic findings prepared'): pass
        with r.phase('calculate_confidence', 'Confidence based on fixture reproduction'):
            r.trace.final_confidence = 'High'
        with r.phase('validate_final_response', 'Synthetic findings checked against fixture evidence'):
            r.event('response_check', check_id='avoid_unsupported_claims', passed=True)
            r.event('response_check', check_id='disclose_missing_evidence', passed=True)
    traces['successful-investigation'] = r.store.get(r.trace.trace_id)
    with request_trace('general_question') as r: pass
    traces['skipped-skill'] = r.store.get(r.trace.trace_id)
    try:
        with request_trace('incident_investigation') as r:
            with r.phase('retrieve_evidence', 'Synthetic Grafana call'): fixture_query(True)
    except TimeoutError:
        pass
    traces['failed-grafana'] = r.store.get(r.trace.trace_id)
    if output:
        path = Path(output); path.mkdir(parents=True, exist_ok=True)
        for name, trace in traces.items():
            (path / (name + '.json')).write_text(json.dumps(trace, indent=2) + '\n')
    return traces

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--output')
    args = parser.parse_args()
    configure_logging()
    generate(args.output)
