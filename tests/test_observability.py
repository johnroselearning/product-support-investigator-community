import asyncio
import io
import json
import logging
import unittest

from observability.context import InvestigationContext, investigation_context
from observability.logging import configure_logging, get_logger
from observability.redaction import redact, redact_mapping
from observability.tool_calls import logged_tool_call


class RedactionTests(unittest.TestCase):
    def test_redacts_secrets_tokens_pii_and_private_keys(self):
        value = ('Authorization: Bearer abc123 Cookie: sid=secret '
                 'api_key=key123 password="pw" me@example.com +1 (555) 123-4567 '
                 'eyJhbGciOiJIUzI1NiJ9.abc.def '
                 '-----BEGIN PRIVATE KEY-----private-----END PRIVATE KEY-----')
        clean = redact(value)
        for secret in ('abc123', 'secret', 'key123', 'pw', 'me@example.com', 'eyJhbGciOiJIUzI1NiJ9.abc.def', 'private'):
            self.assertNotIn(secret, clean)
        self.assertIn('[REDACTED_EMAIL]', clean)
        self.assertIn('[REDACTED_TOKEN]', clean)

    def test_redacts_sensitive_mapping_values(self):
        clean = redact_mapping({'password': 'hidden', 'nested': {'email': 'a@example.com'}, 'ok': 'visible'})
        self.assertEqual(clean['password'], '[REDACTED_SECRET]')
        self.assertEqual(clean['nested']['email'], '[REDACTED_EMAIL]')
        self.assertEqual(clean['ok'], 'visible')


class LoggingTests(unittest.TestCase):
    def test_json_log_contains_context_and_is_redacted_before_write(self):
        stream = io.StringIO()
        configure_logging(stream=stream)
        with investigation_context(InvestigationContext.create(investigation_id='inv-1')):
            get_logger('test').info('contact me@example.com', extra={'component': 'test', 'operation': 'check', 'status': 'success', 'token': 'never serialized'})
        event = json.loads(stream.getvalue())
        self.assertEqual(event['investigation_id'], 'inv-1')
        self.assertTrue(event['correlation_id'].startswith('corr-'))
        self.assertNotIn('me@example.com', stream.getvalue())
        self.assertNotIn('token', event)

    def test_context_isolated_across_async_tasks(self):
        async def read(value):
            with investigation_context(correlation_id=value):
                await asyncio.sleep(0)
                from observability.context import get_context
                return get_context().correlation_id
        async def both():
            return await asyncio.gather(read('a'), read('b'))
        self.assertEqual(asyncio.run(both()), ['a', 'b'])

    def test_tool_wrapper_logs_completion(self):
        stream = io.StringIO(); configure_logging(stream=stream)
        @logged_tool_call('test-tool', 'lookup')
        def lookup():
            return ['one', 'two']
        self.assertEqual(lookup(), ['one', 'two'])
        events = [json.loads(line) for line in stream.getvalue().splitlines()]
        self.assertEqual([event['status'] for event in events], ['started', 'success'])
        self.assertEqual(events[-1]['result_count'], 2)


if __name__ == '__main__':
    unittest.main()
