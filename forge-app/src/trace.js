// Adapter-owned facts only. No payloads, paths, response bodies or exception text.
import { AsyncLocalStorage } from 'node:async_hooks';
import { randomUUID } from 'node:crypto';
import contract from './trace-contract.json' with { type: 'json' };
const context = new AsyncLocalStorage();
const phases = ['classify_request', 'decide_skill_usage', 'collect_issue_context', 'identify_service', 'identify_time_window', 'select_tools', 'retrieve_evidence', 'classify_evidence', 'test_hypotheses', 'produce_findings', 'calculate_confidence', 'validate_final_response'];
export function emit(event_type, fields = {}) {
  const trace = context.getStore();
  if (!fields.trace) trace?.events.push({timestamp: new Date().toISOString(), event_type, ...fields});
  console.log(JSON.stringify({timestamp: new Date().toISOString(), level: 'INFO', service: 'product-support-investigator', environment: 'forge', event_type, message: event_type, trace_id: trace?.trace_id, correlation_id: trace?.correlation_id, investigation_id: trace?.investigation_id, ...fields}));
}
export async function traceAction(action) {
  const trace = {schema_version: '1.0', trace_id: `trace-${randomUUID()}`, correlation_id: `corr-${randomUUID()}`, investigation_id: `inv-${randomUUID()}`, timestamp: new Date().toISOString(), request_type: 'incident_investigation', request_summary_safe: 'Jira investigation action invoked', skill_id: 'product-support-investigator', skill_version: contract.skill_version, skill_applied: true, skill_decision_reason: 'Explicit Jira investigation action invoked; host skill execution is not observable', phases: phases.map(phase_id => ({phase_id, status: 'not_run', started_at: null, completed_at: null, safe_summary: '', evidence_references: [], error: null})), instruction_checks: [], tools_considered: [], tools_called: [], tools_skipped: [], evidence_summary: [], hypotheses: [], read_only_mode: true, writes_attempted: 0, writes_completed: 0, writes_blocked: 0, write_reason: null, user_authorization_present: false, final_status: 'incomplete', final_confidence: null, errors: [], duration_ms: null, events: []};
  return context.run(trace, async () => {
    const start = Date.now();
    emit('skill_decision_started');
    emit('skill_decision_completed', {skill_id: trace.skill_id, applied: true, request_type: trace.request_type, reason: trace.skill_decision_reason});
    complete('classify_request'); complete('decide_skill_usage');
    try {
      const result = await action();
      complete('collect_issue_context'); complete('retrieve_evidence'); complete('select_tools');
      skipTool('grafana_mcp', 'Not configured in this Forge adapter');
      skipTool('github', 'No code-change selection implemented in this adapter');
      return result;
    } catch (error) {
      trace.errors.push({error_type: 'ActionError'});
      trace.final_status = 'failed';
      throw error;
    } finally {
      trace.duration_ms = Date.now() - start;
      trace.instruction_checks = Object.entries(contract.checks).map(([id, phase]) => {
        const passed = id === 'use_read_only_default' || (['classify_request', 'decide_skill_usage', 'collect_issue_context', 'select_tools_conditionally'].includes(id) && trace.phases.find(p => p.phase_id === phase)?.status === 'passed');
        return {id, status: passed ? 'passed' : 'failed', evidence: passed ? 'Adapter completion recorded' : 'Required completion evidence missing'};
      });
      // No host reasoning phases are inferred from returning Jira data.
      emit('request_completed', {status: trace.final_status, trace});
    }
  });
}
function complete(id) {
  const phase = context.getStore().phases.find(p => p.phase_id === id);
  Object.assign(phase, {status: 'passed', started_at: new Date().toISOString(), completed_at: new Date().toISOString(), safe_summary: 'Adapter operation completed'});
  emit('phase_completed', {phase_id: id, status: 'passed'});
}
function skipTool(tool, reason) {
  const trace = context.getStore();
  trace.tools_considered.push({tool, reason}); trace.tools_skipped.push({tool, reason});
  emit('tool_call_skipped', {tool, reason, status: 'skipped'});
}
export async function traceJiraCall(call) {
  const trace = context.getStore();
  const start = Date.now();
  const metadata = {tool: 'jira', server: 'forge_asUser', operation: 'GET', status: 'started', safe_argument_summary: 'Arguments omitted', reason: 'Issue key available; retrieve bounded issue context', correlation_id: trace?.correlation_id, investigation_id: trace?.investigation_id};
  trace?.tools_considered.push({tool: 'jira', reason: metadata.reason});
  trace?.tools_called.push(metadata);
  emit('tool_call_started', metadata);
  try {
    const result = await call();
    Object.assign(metadata, {status: 'success', duration_ms: Date.now()-start, result_count: null});
    emit('tool_call_completed', metadata);
    return result;
  } catch (error) {
    Object.assign(metadata, {status: 'failed', duration_ms: Date.now()-start, error_type: 'JiraRequestError', error_code: Number.isInteger(error.status) ? error.status : null});
    trace?.errors.push({error_type: metadata.error_type, error_code: metadata.error_code});
    emit('tool_call_failed', metadata);
    throw error;
  }
}
