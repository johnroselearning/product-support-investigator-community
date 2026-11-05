// Pure bounded acquisition; the injected reader owns Forge asUser() and routes.
export const ISSUE_FIELDS = ['summary', 'description', 'status', 'priority', 'issuetype',
  'project', 'labels', 'components', 'versions', 'fixVersions', 'environment',
  'created', 'updated', 'reporter', 'assignee', 'issuelinks', 'parent'].join(',');

export function retrievalOptions(payload) {
  const sections = payload.sections === undefined || payload.sections === '' ? [] :
    typeof payload.sections === 'string' ? payload.sections.split(',').map(s => s.trim()) : [null];
  if (sections.some(s => !['comments', 'changelog', 'related'].includes(s))) throw new TypeError('Invalid evidence sections');
  const limit = payload.limit ?? 20;
  const startAt = payload.startAt ?? 0;
  if (!Number.isInteger(limit) || limit < 1 || limit > 100 ||
      !Number.isInteger(startAt) || startAt < 0 || startAt > 100000) throw new TypeError('Invalid evidence page');
  return {sections: new Set(sections), limit, startAt};
}

// Redact before clipping. Raw records remain available only at the authorized
// Jira source, never in telemetry. This is best effort, not a DLP guarantee.
export function redact(value) {
  if (typeof value === 'string') return value
    .replace(/https?:\/\/[^\s<>"']*[?&](?:sig|signature|token|key|X-Amz-Signature|X-Amz-Credential|se|sp|sv)=[^\s<>"']*/gi, '[REDACTED_URL]')
    .replace(/\b(?:Bearer\s+|Basic\s+)[A-Za-z0-9+/_=.\-]+/gi, '[REDACTED_AUTH]')
    .replace(/\b(?:password|secret|token|api[_-]?key|cookie|authorization)\s*[:=]\s*[^\s,;]+/gi, '[REDACTED_SECRET]')
    .replace(/\beyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b/g, '[REDACTED_JWT]')
    .replace(/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, '[REDACTED_EMAIL]');
  if (Array.isArray(value)) return value.map(redact);
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([key, item]) =>
    [key, /^(?:password|secret|token|cookie|authorization|emailAddress)$/i.test(key) ? '[REDACTED]' : redact(item)]));
  return value;
}

function bounded(value, locator, limitations) {
  const safe = redact(value);
  if (JSON.stringify(safe ?? null).length <= 4000) return safe;
  limitations.push(`Excerpt clipped at ${locator}; retrieve the original through authorized Jira access.`);
  return {excerpt: JSON.stringify(safe).slice(0, 4000), truncated: true, locator};
}

function page(raw, key, compact, startAt, limit, locator, limitations) {
  const values = raw[key] || [];
  if (!Array.isArray(values) || values.length > limit) throw new TypeError('Invalid evidence page');
  const total = Number.isInteger(raw.total) ? raw.total : null;
  const hasMore = total === null ? raw.isLast !== true && values.length >= limit : startAt + values.length < total;
  return {total, startAt, maxResults: limit, truncated: startAt > 0 || hasMore,
    nextStartAt: hasMore ? startAt + values.length : null,
    items: deduplicate(values.map(item => compact(item, limitations))), locator,
    limitations: total === null ? ['Source did not report a total; coverage remains uncertain.'] : []};
}

function deduplicate(items) {
  const seen = new Set();
  return items.filter(item => {
    const key = JSON.stringify(item);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export async function collectJiraEvidence(issueKey, payload, read) {
  const {sections, limit, startAt} = retrievalOptions(payload);
  const limitations = [];
  const issue = await read('get_issue', {issueKey, fields: ISSUE_FIELDS});
  if (typeof issue.key !== 'string' || issue.key.toUpperCase() !== issueKey.toUpperCase()) throw new TypeError('Cross-issue result');
  const skipped = section => ({total: null, items: [], skipped: true, truncated: true,
    limitation: `${section} not requested; no absence inference is supported.`});
  let comments = skipped('Comments'), changelog = skipped('Changelog'), recentProjectIssues = skipped('Related candidates');
  const jobs = [];
  if (sections.has('comments')) jobs.push((async () => {
    const raw = await read('get_comments', {issueKey, startAt, limit});
    comments = page(raw, 'comments', comment => ({id: comment.id, created: comment.created, updated: comment.updated,
      author: redact(comment.author?.displayName || comment.author?.accountId || 'Unknown'),
      body: bounded(comment.body, `jira:${issueKey}/comment/${comment.id}`, limitations)}), startAt, limit, `jira:${issueKey}/comments`, limitations);
  })());
  if (sections.has('changelog')) jobs.push((async () => {
    const raw = await read('get_changelog', {issueKey, startAt, limit});
    changelog = page(raw, 'values', change => ({id: change.id, created: change.created,
      author: redact(change.author?.displayName || change.author?.accountId || 'Unknown'),
      items: bounded(change.items, `jira:${issueKey}/changelog/${change.id}`, limitations)}), startAt, limit, `jira:${issueKey}/changelog`, limitations);
  })());
  if (sections.has('related') && issue.fields?.project?.key) jobs.push((async () => {
    const projectKey = issue.fields.project.key;
    if (!/^[A-Za-z][A-Za-z0-9_]*$/.test(projectKey)) throw new TypeError('Invalid project scope');
    const raw = await read('search_project_issues', {issueKey, projectKey, limit: Math.min(limit, 10)}).catch(() => ({unavailable: true, issues: []}));
    if (!Array.isArray(raw.issues) || raw.issues.length > Math.min(limit, 10)) throw new TypeError('Invalid candidate page');
    recentProjectIssues = {total: raw.total ?? null, unavailable: !!raw.unavailable,
      items: (raw.issues || []).map(item => ({id: item.id, key: item.key, summary: redact(item.fields?.summary),
        status: item.fields?.status?.name, priority: item.fields?.priority?.name,
        issueType: item.fields?.issuetype?.name, updated: item.fields?.updated})),
      nextPageToken: raw.nextPageToken || null, truncated: raw.isLast !== true,
      limitation: raw.unavailable ? 'Optional candidate search unavailable; not application evidence.' :
        'Recent project issues are candidates only; recency does not establish relatedness.'};
  })());
  await Promise.all(jobs);
  const links = issue.fields?.issuelinks || [];
  if (links.length > 100) limitations.push(`Linked issues clipped; retrieve jira:${issueKey}/field/issuelinks for full coverage.`);
  const linkedIssues = deduplicate(links.slice(0, 100).map(link => ({id: link.id, type: link.type?.name,
    direction: link.outwardIssue ? 'outward' : 'inward', issueKey: link.outwardIssue?.key || link.inwardIssue?.key,
    summary: redact(link.outwardIssue?.fields?.summary || link.inwardIssue?.fields?.summary),
    status: link.outwardIssue?.fields?.status?.name || link.inwardIssue?.fields?.status?.name})));
  const fields = Object.fromEntries(Object.entries(issue.fields || {}).map(([key, value]) =>
    [key, bounded(value, `jira:${issueKey}/field/${key}`, limitations)]));
  if ('issuelinks' in fields) fields.issuelinks = {returnedAs: 'linkedIssues', locator: `jira:${issueKey}/field/issuelinks`};
  return {evidenceVersion: '2', readOnly: true, source: 'Jira Cloud REST API via Forge asUser()',
    issue: {id: issue.id, key: issue.key, fields}, comments, changelog, linkedIssues, recentProjectIssues,
    optionalSources: {datadog: 'not configured', zendesk: 'not configured'}, limitations,
    evidenceGuidance: {recentProjectIssues: 'Require a shared identifier, symptom, error, component or version before correlation.',
      rootCause: 'Timing and similarity do not establish causation. Challenge consequential conclusions.'}};
}
