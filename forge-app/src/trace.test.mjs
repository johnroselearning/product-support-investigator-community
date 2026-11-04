import test from 'node:test';
import assert from 'node:assert/strict';
import { traceAction, traceJiraCall } from './trace.js';

test('Forge captures bounded calls without payloads, errors or invented reasoning', async () => {
  const events = [];
  const original = console.log;
  console.log = value => events.push(JSON.parse(value));
  try {
    const result = await traceAction(async () => {
      const data = await traceJiraCall(async () => ({body: 'private description'}));
      try { await traceJiraCall(async () => { const e = new Error('password=secret'); e.status = 403; throw e; }); } catch {}
      return data;
    });
    assert.equal(result.body, 'private description');
    const trace = events.at(-1).trace;
    assert.equal(trace.read_only_mode, true);
    assert.equal(trace.final_status, 'incomplete');
    assert.equal(trace.tools_called[1].error_code, 403);
    assert.equal(trace.phases.find(p => p.phase_id === 'test_hypotheses').status, 'not_run');
    assert.equal(trace.instruction_checks.find(p => p.id === 'test_hypotheses').status, 'failed');
    assert(!JSON.stringify(events).includes('private description'));
    assert(!JSON.stringify(events).includes('password=secret'));
    assert(events.every(e => e.investigation_id === trace.investigation_id));
  } finally { console.log = original; }
});
test('Forge records action failures', async () => {
  const events = []; const original = console.log;
  console.log = value => events.push(JSON.parse(value));
  try {
    await assert.rejects(traceAction(async () => { throw new Error('private'); }));
    assert.equal(events.at(-1).trace.final_status, 'failed');
  } finally { console.log = original; }
});

test('terminal reasons cover each observable signal', async () => {
  const { terminalReason } = await import('./trace.js');
  for (const [signal, expected] of Object.entries({completed: 'completed', noEvidence: 'no_evidence', toolNotConfigured: 'tool_not_configured', toolError: 'tool_error', modelEndedEarly: 'model_ended_early', validationFailed: 'validation_failed', timedOut: 'timeout', exception: 'exception'})) {
    assert.equal(terminalReason({[signal]: true})[0], expected);
  }
});

test('empty Jira fields and unconfigured tools are explained without leaking JWTs', async () => {
  const lines = []; const original = console.log;
  console.log = value => lines.push(value);
  const jwt = 'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJwcml2YXRlIn0.c2lnbmF0dXJl';
  try {
    await traceAction(async () => {
      const issue = await traceJiraCall(async () => ({fields: {}, contextToken: jwt}), {operation: 'get_issue', issueKey: 'SUP-12', fields: ['summary']});
      await traceJiraCall(async () => ({comments: []}), {operation: 'get_comments', issueKey: 'SUP-12'});
      await traceJiraCall(async () => ({values: []}), {operation: 'get_changelog', issueKey: 'SUP-12'});
      return {issue, comments: {items: []}, changelog: {items: []}};
    });
    assert(lines.every(line => !/eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/.test(line)));
    const events = lines.map(JSON.parse); const end = events.at(-1); const trace = end.trace;
    assert.equal(end.status, 'incomplete'); assert.equal(end.stop_reason, 'no_evidence');
    assert.equal(trace.phases.find(p => p.phase_id === 'collect_issue_context').status, 'no_output');
    assert.deepEqual(trace.tools_skipped.map(t => t.tool), ['grafana_mcp', 'github']);
    assert(trace.phases.filter(p => p.status === 'not_run').every(p => p.not_run_reason));
    assert(trace.instruction_checks.filter(c => c.status === 'failed').every(c => c.expected_evidence && c.observed_evidence));
    const starts = events.filter(e => e.event_type === 'tool_call_started');
    const ends = events.filter(e => e.event_type === 'tool_call_completed');
    assert.deepEqual(starts.map(e => e.call_id), ends.map(e => e.call_id));
    assert.equal(ends[1].result_count, 0);
    assert(!lines.join('\n').includes(jwt));
  } finally { console.log = original; }
});

test('failure events classify validation, Jira failure, timeout and exception', async () => {
  for (const [kind, expected] of [['validation', 'validation_failed'], ['jira', 'tool_error'], ['timeout', 'timeout'], ['exception', 'exception']]) {
    const events = []; const original = console.log; console.log = line => events.push(JSON.parse(line));
    try {
      await assert.rejects(traceAction(async () => {
        if (kind === 'jira') return traceJiraCall(async () => { throw new Error('private'); });
        const error = new Error('private'); if (kind === 'timeout') error.name = 'TimeoutError'; throw error;
      }, {issueKeyValid: kind !== 'validation'}));
      assert.equal(events.at(-1).stop_reason, expected);
      assert.equal(events.at(-1).status, 'failed');
    } finally { console.log = original; }
  }
});


test('references are random and handled failures preserve a new reference', async () => {
  const { investigateJiraIssue } = await import('./index.js');
  const original = console.log; console.log = () => {};
  try {
    const a = await investigateJiraIssue({ issueKey: 'bad', support_reference: 'PSI-invalid' });
    const b = await investigateJiraIssue({ issueKey: 'bad', support_reference: a.support_reference });
    assert.match(a.support_reference, /^PSI-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    assert.notEqual(a.support_reference, b.support_reference);
    assert.equal(a.error.code, 'INVESTIGATION_FAILED');
    assert.match(b.continuity, /new investigation/);
  } finally { console.log = original; }
});

test('logging failure never masks a result or error', async () => {
  const original = console.log; console.log = () => { throw new Error('logger failed'); };
  try {
    assert.equal((await traceAction(async () => ({answer: 42}))).answer, 42);
    await assert.rejects(traceAction(async () => { throw new Error('original'); }), /original/);
  } finally { console.log = original; }
});
