# Data Handling — Product Support Investigator

_Last reviewed: 10 September 2026_

This document describes the Community Edition Forge/Rovo app as currently implemented. Update it whenever the manifest, Jira fields, storage, remotes, analytics, or integrations change.

## Architecture summary

1. A Jira/Rovo user requests an investigation and supplies or provides context for a Jira issue key.
2. The Forge action validates the issue key.
3. The action calls Jira Cloud REST APIs using `api.asUser()`.
4. Jira applies the requesting user's permissions.
5. The action returns bounded Jira evidence to the Rovo agent for investigation.
6. The Community Edition does not configure an application-owned external backend or persistent database.

## Jira information accessed

The current implementation may retrieve:

- issue summary and description;
- status, priority, issue type, project, labels, and components;
- affected/version fields and environment;
- created/updated timestamps;
- reporter and assignee information exposed by Jira;
- issue links and parent information;
- up to 100 comments;
- up to 100 changelog entries; and
- up to 10 recently updated issues from the same project as investigation candidates.

The app marks comment/changelog results as truncated when the Jira result count exceeds the configured bounds.

## Purpose of same-project issue retrieval

Recently updated issues from the same project are candidates only. The app explicitly warns the agent not to treat recency as proof of relatedness. A shared identifier, symptom, error signature, component, version, timestamp pattern, or other meaningful correlation should be established before using another issue as supporting evidence.

## Permissions and authorization

Current Forge scopes:

- `read:jira-work`
- `read:chat:rovo`

Jira REST requests use `api.asUser()`. The app therefore operates within the requesting user's Jira authorization context rather than using an app-level identity to broaden issue visibility.

## Write access

The Community Edition action is declared with the `GET` action verb and performs Jira read requests. It does not create, edit, transition, comment on, or delete Jira issues.

## Storage

The current Community Edition does not intentionally store retrieved Jira issue data in Forge Storage or in a developer-controlled database.

## External egress

The current Community Edition manifest does not configure developer-controlled remotes or external egress for Jira evidence. Datadog and Zendesk are represented only as unconfigured optional sources in the returned evidence structure; the app does not contact those services.

## Credentials

The app does not ask users to provide Jira passwords or API tokens to the Rovo agent. Jira access is handled through Atlassian Forge authorization.

Do not submit secrets, API keys, access tokens, passwords, private keys, session cookies, or other credentials in Jira content for the purpose of using this app.

## AI processing

The retrieved evidence is supplied to the Atlassian Rovo agent as part of the requested investigation. Rovo/Atlassian processing is governed by the applicable Atlassian product terms, privacy documentation, customer settings, and AI-related controls.

## Data deletion

The app does not currently maintain a developer-controlled persistent store of Jira issue evidence. Therefore there is no separate application database record to delete. Data retained by Jira, Forge, Rovo, or other Atlassian services must be managed through the applicable Atlassian product/site controls.

## Future integrations

If a future version adds Datadog, Zendesk, GitHub, an MCP service, RAG/vector storage, analytics, a remote backend, or another external integration, this document and the Privacy Policy must be reviewed before release. New scopes, data flows, subprocessors, retention behavior, and external egress must be disclosed accurately.

## Optional local Grafana adapter (separate from Forge)

The opt-in Python adapter sends scoped read-only queries to a runtime-configured Grafana endpoint using a runtime bearer token. It returns bounded, best-effort redacted telemetry on stdout and does not persist responses. Logs and labels can still contain customer PII or unidentified secrets; review before sharing. Host tools may retain output under their own policies. This adapter does not change Forge storage or egress. See [Grafana setup](docs/GRAFANA.md).
