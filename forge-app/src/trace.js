// Adapter-owned facts only: never serialize payloads, response bodies or errors.
import { AsyncLocalStorage } from 'node:async_hooks';
import { randomUUID } from 'node:crypto';
import contract from './trace-contract.json' with { type: 'json' };
const context = new AsyncLocalStorage();
const phases = ['classify_request', 'decide_skill_usage', 'collect_issue_context', 'identify_service', 'identify_time_window', 'select_tools', 'retrieve_evidence', 'classify_evidence', 'test_hypotheses', 'produce_findings', 'calculate_confidence', 'validate_final_response'];

// Only classify signals actually available to the caller; absent host telemetry is not a model stop.
export function terminalReason({ completed, validationFailed, timedOut, toolError, exception, modelEndedEarly, noEvidence, toolNotConfigured } = {}) {
  if (timedOut) return ['timeout', 'The adapter observed a timeout.'];
  if (validationFailed) return ['validation_failed', 'The request failed input validation.'];
  if (toolError) return ['tool_error', 'A required Jira call failed.'];
  if (exception) return ['exception', 'The adapter action raised an exception.'];
  if (completed) return ['completed', 'The investigation completed.'];
  if (modelEndedEarly) return ['model_ended_early', 'The host reported an early model stop.'];
  if (noEvidence) return ['no_evidence', 'Jira returned no issue fields.'];
  if (toolNotConfigured) return ['tool_not_configured', 'A required tool is not configured.'];
  return ['no_evidence', 'The adapter returned Jira context; host investigation and completion evidence are not observable.'];
}
export function emit(event_type, fields = {}) {
  const trace = context.getStore();
  try {
    if (!fields.trace) trace?.events.push({timestamp: new Date().toISOString(), event_type, ...structuredClone(fields)});
    console.log(JSON.stringify({timestamp: new Date().toISOString(), level: fields.status === 'failed' ? 'ERROR' : 'INFO', service: 'product-support-investigator', environment: trace?.environment || 'unknown', event: event_type, event_type, action: 'investigate-jira-issue', investigation_id: trace?.investigation_id, invocation_id: trace?.invocation_id, outcome: fields.status || 'started', error_code: fields.error_code ?? null, ...fields}));
  } catch { /* Diagnostics must never change the action result. */ }
}
export async function traceAction(action, metadata = {}) {
  const trace = {schema_version: '1.0', investigation_id: metadata.investigation_id || `PSI-${randomUUID()}`, invocation_id: metadata.invocation_id || null, environment: metadata.environment || 'unknown', timestamp: new Date().toISOString(), request_type: 'incident_investigation', request_summary_safe: 'Jira investigation action invoked', skill_id: 'product-support-investigator', skill_version: contract.skill_version, skill_applied: null, skill_decision_reason: 'Host skill execution is not observable', skill_observability: 'Host loading and execution of SKILL.md and instructions are not observable', skill_loaded: null, skill_bytes: contract.skill_bytes, instructions_loaded: null, instructions_bytes: contract.instructions_bytes, prompt_hash: contract.prompt_hash, phases: phases.map(phase_id => ({phase_id, status: 'not_run', started_at: null, completed_at: null, output_summary: null, evidence_count: 0, duration_ms: null, finish_reason: null, input_tokens: null, output_tokens: null, not_run_reason: null})), instruction_checks: [], tools_considered: [], tools_called: [], tools_skipped: [], evidence_summary: [], hypotheses: [], read_only_mode: true, writes_attempted: 0, writes_completed: 0, writes_blocked: 0, write_reason: null, user_authorization_present: false, final_status: 'incomplete', final_confidence: null, errors: [], duration_ms: null, events: []};
  return context.run(trace, async () => {
    const start = Date.now();
    emit('action_started');
    emit('skill_decision_started');
    emit('skill_decision_completed', {skill_id: trace.skill_id, skill_version: trace.skill_version, applied: null, skill_observability: trace.skill_observability, skill_loaded: null, skill_bytes: trace.skill_bytes, instructions_loaded: null, instructions_bytes: trace.instructions_bytes, prompt_hash: trace.prompt_hash});
    complete('classify_request', 'passed', 'Jira investigation action invoked', 1);
    complete('decide_skill_usage', 'no_output', 'Host skill decision is not observable', 0);
    let signals = {};
    try {
      const result = await action();
      const fields = result?.issue?.fields;
      const count = fields && typeof fields === 'object' ? Object.keys(fields).length : 0;
      const comments = Array.isArray(result?.comments?.items) ? result.comments.items.length : 0;
      const changes = Array.isArray(result?.changelog?.items) ? result.changelog.items.length : 0;
      const summary = `fetched ${count ? 1 : 0} issue with fields, ${comments} comments, ${changes} changelog entries`;
      complete('collect_issue_context', count ? 'passed' : 'no_output', summary, count ? 1 : 0);
      complete('retrieve_evidence', count || comments || changes ? 'passed' : 'no_output', summary, (count ? 1 : 0) + comments + changes);
      complete('select_tools', 'passed', 'Selected Jira; Grafana and GitHub are unavailable in this adapter', 1);
      skipTool('grafana_mcp', 'Not configured in this Forge adapter');
      skipTool('github', 'No code-change selection implemented in this adapter');
      signals.noEvidence = !count && !comments && !changes;
      return result;
    } catch (error) {
      signals = {validationFailed: metadata.issueKeyValid === false, timedOut: error?.name === 'TimeoutError' || error?.code === 'ETIMEDOUT', toolError: trace.required_tool_failed, exception: true};
      trace.errors.push({error_type: 'ActionError'});
      trace.final_status = 'failed';
      throw error;
    } finally {
      trace.duration_ms = Date.now() - start;
      [trace.stop_reason, trace.stop_detail] = terminalReason(signals);
      for (const phase of trace.phases.filter(p => p.status === 'not_run')) {
        phase.not_run_reason = trace.final_status === 'failed' ? `Earlier phase stopped: ${trace.stop_reason}` : `Not reached by adapter: ${trace.stop_reason}; host execution is not observable`;
      }
      trace.instruction_checks = Object.entries(contract.checks).map(([id, phase]) => {
        const observed = phase ? trace.phases.find(p => p.phase_id === phase) : null;
        const passed = id === 'use_read_only_default' || (['classify_request', 'decide_skill_usage', 'collect_issue_context', 'select_tools_conditionally'].includes(id) && observed?.status === 'passed');
        const expected = phase ? `Evidence for ${phase.replaceAll('_', ' ')}` : 'Read-only operation';
        return {id, status: passed ? 'passed' : 'failed', evidence: passed ? (observed?.output_summary || 'Read-only operation recorded') : `Required completion evidence missing: ${expected}`, expected_evidence: expected, observed_evidence: observed ? (observed.output_summary || observed.not_run_reason) : 'Read-only operation recorded'};
      });
      emit('request_completed', {status: trace.final_status, outcome: trace.final_status === 'failed' ? 'failed' : 'success', error_code: trace.final_status === 'failed' ? 'INVESTIGATION_FAILED' : null, stop_reason: trace.stop_reason, stop_detail: trace.stop_detail, finish_reason: null, input_tokens: null, output_tokens: null, duration_ms: trace.duration_ms, trace});
    }
  });
}
function complete(id, status, output_summary, evidence_count) {
  const phase = context.getStore().phases.find(p => p.phase_id === id);
  const now = new Date().toISOString();
  const start = ['collect_issue_context', 'retrieve_evidence'].includes(id) ? context.getStore().jira_started_at : null;
  Object.assign(phase, {status, started_at: start == null ? now : new Date(start).toISOString(), completed_at: now, duration_ms: start == null ? null : Date.now() - start, output_summary, evidence_count});
  emit('phase_completed', {...phase});
}
function skipTool(tool, reason) {
  const trace = context.getStore();
  trace.tools_considered.push({tool, reason}); trace.tools_skipped.push({tool, reason});
  emit('tool_call_skipped', {tool, reason, status: 'skipped'});
}
export async function traceJiraCall(call, args = {}) {
  const trace = context.getStore();
  const start = Date.now();
  if (trace && trace.jira_started_at == null) trace.jira_started_at = start;
  const safe = {operation: args.operation || 'GET', fields: args.fields || [], expand: args.expand || []};
  const metadata = {call_id: randomUUID(), tool: 'jira', server: 'forge_asUser', operation: safe.operation, status: 'started', safe_argument_summary: safe, reason: 'Retrieve bounded Jira context'};
  trace?.tools_considered.push({tool: 'jira', reason: metadata.reason});
  trace?.tools_called.push(metadata);
  emit('tool_call_started', metadata);
  try {
    const result = await call();
    const array = Array.isArray(result) ? result : [result?.comments, result?.values, result?.issues].find(Array.isArray);
    Object.assign(metadata, {status: 'success', duration_ms: Date.now()-start, result_count: array ? array.length : result && typeof result === 'object' ? 1 : 0, result_shape: Array.isArray(result) ? 'array' : result === null ? 'null' : typeof result});
    emit('tool_call_completed', metadata);
    return result;
  } catch (error) {
    Object.assign(metadata, {status: 'failed', duration_ms: Date.now()-start, result_count: 0, error_type: 'JiraRequestError', error_code: Number.isInteger(error.status) ? error.status : null});
    if (trace && !args.optional) trace.required_tool_failed = true;
    trace?.errors.push({error_type: metadata.error_type, error_code: metadata.error_code});
    emit('tool_call_completed', metadata);
    throw error;
  }
}
