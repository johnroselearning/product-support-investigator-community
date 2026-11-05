import test from 'node:test';
import assert from 'node:assert/strict';
import { validateInvestigationResponse } from './response.js';

const valid = () => ({evidenceVersion: '2', readOnly: true, source: 'Jira Cloud REST API via Forge asUser()',
  issue: {key: 'SUP-123', fields: {}}, comments: {items: []}, changelog: {items: []},
  linkedIssues: [], recentProjectIssues: {items: []}});

test('Jira action contract rejects malformed and unbounded results', () => {
  const result = valid();
  assert.equal(validateInvestigationResponse(result), result);
  for (const change of [{readOnly: false}, {issue: null}, {comments: {items: Array(101).fill({})}},
                        {recentProjectIssues: {items: Array(11).fill({})}}, {evidenceVersion: 'invented'}]) {
    assert.throws(() => validateInvestigationResponse({...valid(), ...change}), /response contract/);
  }
  for (const result of [null, [], {error: {code: 'PRIVATE'}}]) {
    assert.throws(() => validateInvestigationResponse(result), /response contract/);
  }
});
