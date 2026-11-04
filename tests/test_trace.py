import asyncio
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from observability.trace import request_trace, current_trace
from observability.trace.schema import PHASES
from observability.trace.store import TraceStore
from observability.trace.evaluator import evaluate
from observability.tool_calls import logged_tool_call
from observability.config import ObservabilityConfig
from observability.logging import configure_logging

class TraceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = TraceStore(Path(self.tmp.name) / 'trace.db')
        self.stream = io.StringIO()
        configure_logging(stream=self.stream)

    def request(self, kind='incident_investigation', **kw):
        return request_trace(kind, store=self.store, **kw)

    def test_decisions_and_ids(self):
        with self.request(correlation_id='corr-external') as r:
            self.assertTrue(r.trace.skill_applied)
            self.assertEqual(r.trace.correlation_id, 'corr-external')
        first = r.trace.trace_id
        for kind in ('general_question', 'documentation', 'how_to', 'unrelated_coding'):
            with self.request(kind) as r:
                self.assertFalse(r.trace.skill_applied)
            self.assertEqual(r.trace.final_status, 'skipped')
            self.assertNotEqual(first, r.trace.trace_id)
        events = [json.loads(x) for x in self.stream.getvalue().splitlines()]
        self.assertEqual(events[0]['event_type'], 'skill_decision_started')
        self.assertTrue(all(k in events[0] for k in ('timestamp', 'level', 'service', 'trace_id', 'correlation_id', 'investigation_id', 'message')))

    def test_async_context_and_tool(self):
        @logged_tool_call('test')
        async def call():
            await asyncio.sleep(0)
            return [current_trace().trace.correlation_id]
        async def worker(cid):
            with self.request(correlation_id=cid) as r:
                result = await call()
                self.assertEqual(r.trace.tools_called[0]['correlation_id'], cid)
                return result[0]
        async def run():
            return await asyncio.gather(worker('a'), worker('b'))
        self.assertEqual(asyncio.run(run()), ['a', 'b'])
        self.assertIsNone(current_trace())

    def test_tool_success_failure_skip_no_raw(self):
        @logged_tool_call('grafana_mcp', 'query')
        def call(fail=False, **kwargs):
            if fail:
                raise RuntimeError('password=secret private raw response')
            return ['raw response']
        with self.request() as r:
            call(password='secret', body='private evidence')
            with self.assertRaises(RuntimeError): call(True)
            r.skip('github', 'No code-change signal')
        t = self.store.get(r.trace.trace_id)
        self.assertEqual([x['status'] for x in t['tools_called']], ['success', 'failed'])
        self.assertEqual(t['tools_called'][0]['result_count'], 1)
        self.assertEqual(t['tools_skipped'][0]['reason'], 'No code-change signal')
        self.assertNotIn('private evidence', json.dumps(t))
        self.assertNotIn('raw response', json.dumps(t))
        self.assertNotIn('secret', json.dumps(t))
        self.assertFalse(ObservabilityConfig().log_raw_evidence)

    def test_phases_evidence_compliance(self):
        with self.request() as r:
            self.assertFalse(evaluate(r.trace)['passed'])
            for phase in PHASES[2:]:
                with r.phase(phase, 'Explicit synthetic test completion'): pass
            for kind in ('observed', 'inferred', 'unknown'):
                r.evidence(source='fixture', locator='E1', evidence_type=kind, safe_summary='Safe fixture summary')
            r.consider('fixture', 'Fixture evidence available')
            r.hypothesis('H1', 'supported', ['E1'], 'Fixture test supports hypothesis')
            r.trace.final_confidence = 'High'
            for check in ('avoid_unsupported_claims', 'disclose_missing_evidence'):
                r.event('response_check', check_id=check, passed=True)
            self.assertTrue(evaluate(r.trace)['passed'])
        self.assertEqual(r.trace.final_status, 'completed')
        self.assertEqual(self.store.get(r.trace.trace_id)['timestamp'], r.trace.timestamp)

    def test_failed_phase_and_exception(self):
        with self.assertRaises(ValueError):
            with self.request() as r:
                with r.phase('retrieve_evidence', 'Lookup'): raise ValueError('secret')
        self.assertEqual(r.trace.phases[6].status, 'failed')
        self.assertEqual(r.trace.final_status, 'failed')
        self.assertIsNone(current_trace())

    def test_writes(self):
        with self.request() as r:
            self.assertTrue(r.trace.read_only_mode)
            with self.assertRaises(PermissionError):
                with r.write('Jira comment requested', authorized=True): self.fail('write ran')
            self.assertEqual(r.trace.writes_attempted, 1)
            self.assertEqual(r.trace.writes_blocked, 1)
            r.trace.read_only_mode = False
            with r.write('Explicit test authorization', authorized=True): pass
            self.assertEqual(r.trace.writes_completed, 1)
        self.assertIn('write_attempted', self.stream.getvalue())

    def test_redaction_storage_and_cli(self):
        with self.request() as r:
            r.complete_phase('collect_issue_context', 'user@example.com +1 (555) 123-4567 password=hidden Authorization: Basic abcdef')
        stored = self.store.get(r.trace.trace_id)
        for secret in ('user@example.com', '123-4567', 'hidden', 'abcdef'):
            self.assertNotIn(secret, json.dumps(stored))
        for cmd in (['inspect', r.trace.trace_id], ['export', r.trace.trace_id, '--format', 'json'], ['list']):
            output = subprocess.check_output([sys.executable, '-m', 'observability.trace', '--db', str(self.store.path), *cmd], text=True)
            self.assertIn(r.trace.trace_id, output)
        self.assertEqual(len(self.store.list()), 1)

if __name__ == '__main__': unittest.main()

class ContractTests(unittest.TestCase):
    def test_forge_contract_matches_python_and_skill(self):
        from hashlib import sha256
        from observability.trace.evaluator import CHECKLIST
        contract = json.loads(Path('forge-app/src/trace-contract.json').read_text())
        self.assertEqual(contract['checks'], CHECKLIST)
        self.assertEqual(contract['skill_version'], 'sha256:' + sha256(Path('SKILL.md').read_bytes()).hexdigest())

    def test_cookie_and_configuration_redaction(self):
        from observability.redaction import redact
        self.assertNotIn('secondsecret', redact('Cookie: sid=firstsecret; session=secondsecret'))
        stream = io.StringIO()
        configure_logging(ObservabilityConfig(redact_sensitive_data=False, log_raw_evidence=True), stream=stream)
        from observability.logging import get_logger
        get_logger('test').info('client_secret=hidden me@example.com')
        self.assertNotIn('hidden', stream.getvalue())
        self.assertNotIn('me@example.com', stream.getvalue())
