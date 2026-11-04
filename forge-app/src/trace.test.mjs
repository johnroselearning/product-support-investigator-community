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
    assert(events.every(e => e.trace_id === trace.trace_id));
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
