// The existing Jira action's success contract. No GitHub/Grafana action is added.
export function validateInvestigationResponse(result) {
  const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
  if (!object(result) || result.evidenceVersion !== '2' || result.readOnly !== true ||
      result.source !== 'Jira Cloud REST API via Forge asUser()' ||
      !object(result.issue) || !/^[A-Za-z][A-Za-z0-9_]+-\d+$/.test(result.issue.key) ||
      !object(result.issue.fields) || !object(result.comments) || !Array.isArray(result.comments.items) ||
      result.comments.items.length > 100 || !object(result.changelog) || !Array.isArray(result.changelog.items) ||
      result.changelog.items.length > 100 || !Array.isArray(result.linkedIssues) ||
      !object(result.recentProjectIssues) || !Array.isArray(result.recentProjectIssues.items) ||
      result.recentProjectIssues.items.length > 10) {
    throw new TypeError('Invalid Jira investigation response contract');
  }
  return result;
}
