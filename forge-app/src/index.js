import api, { route } from '@forge/api';

const MAX_COMMENTS = 100;
const MAX_CHANGELOG_ENTRIES = 100;
const MAX_RECENT_PROJECT_ISSUES = 10;

const ISSUE_FIELDS = [
  'summary',
  'description',
  'status',
  'priority',
  'issuetype',
  'project',
  'labels',
  'components',
  'versions',
  'fixVersions',
  'environment',
  'created',
  'updated',
  'reporter',
  'assignee',
  'issuelinks',
  'parent',
].join(',');

function getIssueKey(payload) {
  return (
    payload?.issueKey ||
    payload?.context?.jira?.issueKey ||
    payload?.context?.issueKey
  );
}

function assertIssueKey(issueKey) {
  if (!issueKey || !/^[A-Za-z][A-Za-z0-9_]+-\d+$/.test(issueKey)) {
    throw new Error('A valid Jira issue key is required, for example SUP-1428.');
  }
}

async function requestJson(path) {
  const response = await api.asUser().requestJira(path, {
    headers: { Accept: 'application/json' },
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(`Jira API request failed with HTTP ${response.status}.`);
    error.status = response.status;
    error.details = body;
    throw error;
  }

  return body;
}

function compactComment(comment) {
  return {
    id: comment.id,
    author: comment.author?.displayName || comment.author?.accountId || 'Unknown',
    created: comment.created,
    updated: comment.updated,
    body: comment.body,
  };
}

function compactChange(change) {
  return {
    id: change.id,
    created: change.created,
    author: change.author?.displayName || change.author?.accountId || 'Unknown',
    items: change.items,
  };
}

function compactIssue(issue) {
  return {
    id: issue.id,
    key: issue.key,
    summary: issue.fields?.summary,
    status: issue.fields?.status,
    priority: issue.fields?.priority,
    issueType: issue.fields?.issuetype,
    updated: issue.fields?.updated,
  };
}

export async function investigateJiraIssue(payload) {
  const issueKey = getIssueKey(payload);
  assertIssueKey(issueKey);

  const issue = await requestJson(
    route`/rest/api/3/issue/${issueKey}?fields=${ISSUE_FIELDS}`,
  );

  const [comments, changelog] = await Promise.all([
    requestJson(
      route`/rest/api/3/issue/${issueKey}/comment?startAt=0&maxResults=${MAX_COMMENTS}`,
    ),
    requestJson(
      route`/rest/api/3/issue/${issueKey}/changelog?startAt=0&maxResults=${MAX_CHANGELOG_ENTRIES}`,
    ),
  ]);

  const linkedIssues = (issue.fields?.issuelinks || []).map((link) => ({
    id: link.id,
    type: link.type?.name,
    direction: link.outwardIssue ? 'outward' : 'inward',
    issueKey: link.outwardIssue?.key || link.inwardIssue?.key,
    summary:
      link.outwardIssue?.fields?.summary || link.inwardIssue?.fields?.summary,
    status:
      link.outwardIssue?.fields?.status || link.inwardIssue?.fields?.status,
  }));

  const projectKey = issue.fields?.project?.key;
  let recentProjectIssues = {
    total: 0,
    items: [],
    unavailable: false,
    limitation:
      'These are recent issues from the same project and are only investigation candidates; recency does not establish relatedness.',
  };

  if (projectKey) {
    const jql = `project = "${projectKey}" AND issuekey != "${issueKey}" ORDER BY updated DESC`;

    const result = await requestJson(
      route`/rest/api/3/search/jql?jql=${jql}&maxResults=${MAX_RECENT_PROJECT_ISSUES}&fields=summary,status,priority,updated,issuetype`,
    ).catch((error) => ({
      unavailable: true,
      reason: error.message,
      total: 0,
      issues: [],
    }));

    recentProjectIssues = {
      total: result.total || 0,
      items: (result.issues || []).map(compactIssue),
      unavailable: result.unavailable || false,
      limitation: result.unavailable
        ? result.reason
        : 'These are recent issues from the same project and are only investigation candidates; recency does not establish relatedness.',
    };
  }

  return {
    evidenceVersion: '2',
    readOnly: true,
    source: 'Jira Cloud REST API via Forge asUser()',
    issue: {
      id: issue.id,
      key: issue.key,
      fields: issue.fields,
    },
    comments: {
      total: comments.total || 0,
      truncated: (comments.total || 0) > MAX_COMMENTS,
      items: (comments.comments || []).map(compactComment),
    },
    changelog: {
      total: changelog.total || 0,
      truncated: (changelog.total || 0) > MAX_CHANGELOG_ENTRIES,
      items: (changelog.values || []).map(compactChange),
    },
    linkedIssues,
    recentProjectIssues,
    optionalSources: {
      datadog: 'not configured',
      zendesk: 'not configured',
    },
    evidenceGuidance: {
      recentProjectIssues:
        'Do not treat these issues as related evidence until a shared identifier, symptom, error signature, component, version, timestamp pattern, or other meaningful correlation is established.',
      rootCause:
        'Do not infer causation from timing or similarity alone. Challenge the leading hypothesis before concluding.',
    },
  };
}
