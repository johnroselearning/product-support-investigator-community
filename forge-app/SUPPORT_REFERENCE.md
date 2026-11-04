# Support references in the Jira action

Each action execution starts a new investigation and returns an opaque `PSI-<UUID>` as `support_reference` and as the diagnostic `investigation_id`. The reference is generated even for handled errors. Forge's `getAppContext()` supplies the separate `invocation_id` and environment when available. No Rovo conversation or request ID is inferred. The action reads Jira as the caller; it does not use a reference as authorization.

**Continuity is not implemented.** A supplied previous reference is never attached to an investigation or used to retrieve results, regardless of its format, installation or caller. The action explicitly reports a new investigation. This fail-closed behavior avoids cross-installation access and accidental merges, but does not meet the desired follow-up continuity. There is no mapping to retain. The existing manifest has no storage scope; Forge app storage requires `storage:app`. A future change needs an authorized scope change and installation upgrade, a minimal reference-to-issue and owner/authorization mapping with a defined expiry and cleanup policy, validation of UUID format, installation/environment, and current caller authorization (including Jira `asUser` access), and tests of each boundary. A reference alone must never grant access.

## Report and lookup

Copy the support reference from the response and share it with support; do not include conversation content, credentials or tokens. Rovo rendering is model-mediated, so the instructions cannot guarantee the reference appears. If it is missing, retrying starts another investigation. Where available, Rovo's **Debug response → Request ID** is an additional native fallback for Atlassian support; it is not automatically mapped to these logs.

In Grafana Explore, select Loki, choose the appropriate time range and Forge environment, and replace the example values below. The existing `forge-to-loki.sh` forwarder sends streams with `app`, `environment`, and `forge_environment` labels; IDs remain in the JSON line. Examples use that forwarder's labels, not the separate Docker Promtail stream:

```logql
{app="product-support-investigator", environment="forge", forge_environment="development"} | json | investigation_id="PSI-00000000-0000-4000-8000-000000000000"
{app="product-support-investigator", environment="forge", forge_environment="development"} | json | investigation_id="PSI-00000000-0000-4000-8000-000000000000" | outcome="failed"
{app="product-support-investigator", environment="forge", forge_environment="development"} | json | investigation_id="PSI-00000000-0000-4000-8000-000000000000" | invocation_id="replace-with-observed-invocation-id"
```

These follow [Loki's documented JSON and field filtering syntax](https://grafana.com/docs/loki/latest/query/log_queries/); they have not been run against live Forge logs. Only events actually ingested and still retained in the selected time range are searchable. A chat turn that does not invoke the backend produces no backend event. An investigation ID groups action diagnostics, an invocation ID identifies a Forge execution, a trace/correlation ID belongs to an instrumented distributed trace or correlation mechanism, a Rovo Request ID belongs to Rovo's debugging surface, and a Jira issue key identifies an issue. None implies an automatic mapping to another.

The forwarder polls `forge logs`; it is a development convenience, not a durable ingestion service. It accepts only single-line JSON events from this app; CLI formatting, polling limits, restarts, overlapping windows, failed pushes and retention can cause missing or duplicate events. It uses push time for Loki timestamps. Validate the actual CLI output and ingestion in the target environment. The repository Docker Promtail configuration scrapes only its Docker service, not Forge. Loki is not host-exposed in the default Compose file; provide a suitably secured local endpoint or port mapping for the forwarder. External setup remains: authenticated Forge CLI, a running Loki/Grafana datasource, reachable Loki push endpoint, access controls, retention, and an operational ingestion process. The sample local Loki has `auth_enabled: false` and must not be exposed publicly.

## Development checks (not performed by this change)

From `forge-app`, configure your own app ID in `manifest.yml` using the example, authenticate the Forge CLI, run `npm ci`, then `forge lint`. After authorized development deployment, run `forge deploy --environment development` and, for a new development installation, `forge install --environment development --site <site>.atlassian.net --product Jira`. For an existing installation use the documented upgrade command only if needed. No deployment or installation was performed here.

1. Investigate an accessible issue and check the exact reference in the response, action result, Forge logs and Loki.
2. Ask a follow-up with that reference: confirm the action reports a new investigation and returns a different reference, including on another issue. Check another installation cannot attach it.
3. Invoke with an invalid issue key or inaccessible issue; confirm a handled error includes a new reference and no private error data in logs.
4. Ask a question that invokes no action. Confirm there is no backend event for that turn; do not expect a new reference.

Rovo output, live Forge context, authorization behavior, CLI formatting, ingestion and the LogQL examples require live environment validation. A future Jira UI control could provide a persistent Copy support reference button; no panel is included here.
