// Offline synthetic comparison of the audited legacy path and the current reader.
// Legacy is a simulation of the original four GET calls, not a deployed run.
import { writeFileSync } from 'node:fs';
import { collectJiraEvidence } from '../forge-app/src/jira-evidence.js';

const issue = {id: '1', key: 'SUP-123', fields: {summary: 'HTTP 500 from checkout',
  description: 'req-123 timed out', project: {key: 'SUP'}, issuelinks: []}};
const comments = Array.from({length: 100}, (_, i) => ({id: String(i), created: '2026-11-05T09:00:00Z',
  body: `Observation ${i}: req-123 TimeoutError; validate against request telemetry.`}));
const changes = Array.from({length: 100}, (_, i) => ({id: String(i), created: '2026-11-05T09:00:00Z',
  items: [{field: 'status', fromString: 'Open', toString: 'Investigating'}]}));
const candidates = Array.from({length: 10}, (_, i) => ({id: String(i), key: `SUP-${200 + i}`, fields: {summary: `Candidate ${i}`}}));

async function run(payload) {
  let calls = 0;
  const result = await collectJiraEvidence('SUP-123', payload, async (operation, args) => {
    calls++;
    if (operation === 'get_issue') return issue;
    if (operation === 'get_comments') return {total: comments.length, comments: comments.slice(args.startAt, args.startAt + args.limit)};
    if (operation === 'get_changelog') return {total: changes.length, values: changes.slice(args.startAt, args.startAt + args.limit)};
    return {isLast: true, issues: candidates.slice(0, args.limit)};
  });
  return {tool_calls: calls, response_tokens_estimate: Math.ceil(JSON.stringify(result).length / 4),
    returned_comments: result.comments.items.length, returned_changes: result.changelog.items.length};
}

const legacy = {issue, comments: {total: 100, items: comments}, changelog: {total: 100, items: changes},
  recentProjectIssues: {items: candidates}, linkedIssues: []};
const output = {mode: 'offline-synthetic-simulation', token_method: 'ceil(JSON Unicode characters/4)',
  live_calls: 0, latency: 'not measured',
  A_legacy_acquisition_model: {tool_calls: 4, response_tokens_estimate: Math.ceil(JSON.stringify(legacy).length / 4), returned_comments: 100, returned_changes: 100},
  C_issue_only: await run({}), C_explicit_first_pages: await run({sections: 'comments,changelog,related'}),
  C_explicit_original_limits: await run({sections: 'comments,changelog,related', limit: 100}),
  limitations: ['Legacy response is a reconstruction, not execution of the old adapter.',
    'Payload shapes differ; figures illustrate synthetic context budgets, not billing savings.',
    'Issue-only and first-page modes intentionally cover less evidence; sources/coverage remain explicit.',
    'Further pages can increase call counts. No semantic completion or production speed claim.']};
if (process.argv[2]) writeFileSync(process.argv[2], JSON.stringify(output, null, 2) + '\n');
else console.log(JSON.stringify(output, null, 2));
