# Privacy Policy — Product Support Investigator

_Last updated: 10 September 2026_

Product Support Investigator is an evidence-first, read-only investigation app for Jira Cloud and Atlassian Rovo.

## Data the app accesses

When a user asks the app to investigate a Jira issue, the app may access Jira data the user is already permitted to view, including:

- issue key, summary, description, status, priority, issue type, project, labels, components, versions, environment, and timestamps;
- reporter and assignee information available through Jira;
- issue comments and changelog entries;
- linked issues; and
- a bounded set of recently updated issues from the same Jira project as possible correlation candidates.

## How data is used

The app uses this information only to perform the investigation requested by the user and to distinguish observed evidence, hypotheses, and missing information.

The Forge action accesses Jira through the current user's authorization context (`asUser()`), so Jira permissions continue to determine which issues and data the user can access.

## Storage and external transfer

The Community Edition Forge app does not configure a developer-controlled remote backend, external API, or external data store. It does not intentionally send Jira data to Datadog, Zendesk, GitHub, or another third-party service.

The app runs on Atlassian Forge and returns investigation evidence to the Atlassian Rovo agent. Processing performed by Jira, Forge, and Rovo is governed by the applicable Atlassian terms, privacy documentation, and customer configuration.

The app does not intentionally persist Jira issue data in an application-owned database or storage layer.

## Data retention

Because the app does not intentionally persist Jira issue data in an application-owned store, it does not maintain a separate developer-controlled retention period for Jira issue data. Atlassian products and services may retain data according to the customer's configuration and Atlassian's applicable policies.

## Permissions

The app is designed for least-privilege, read-only investigation. Its Forge manifest requests:

- `read:jira-work`
- `read:chat:rovo`

The app does not request Jira write scopes for creating or modifying issues, comments, workflows, or other Jira content.

## Security

Security reports should be submitted privately through GitHub Private Vulnerability Reporting when available. Do not include credentials, customer data, or exploit details in public issues.

See [SECURITY.md](SECURITY.md) for vulnerability-reporting guidance.

## User requests and questions

For general product or privacy questions, use the public repository's issue tracker without posting confidential Jira data, credentials, or personal information.

If a privacy request concerns information retained by Jira, Forge, or Rovo rather than by this app, the request may need to be handled through the relevant Atlassian site administrator or Atlassian privacy process.

## Changes to this policy

This policy may be updated when the app's data access, storage, integrations, or distribution model changes. Material changes should be reflected in the repository and Marketplace listing before or when the corresponding app change is released.
