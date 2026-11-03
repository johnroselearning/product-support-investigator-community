# Observability

The repository provides a reusable `observability` package for structured JSON events, async-safe investigation context, redaction, tool-call timing, and audit events. It does not change the read-only investigation boundary.

## Configuration

The safe defaults are:

```text
PSI_LOG_LEVEL=INFO
PSI_LOG_FORMAT=json
PSI_LOG_DESTINATION=stdout
PSI_ENVIRONMENT=local
PSI_REDACT_SENSITIVE_DATA=true
PSI_ENABLE_AUDIT_LOG=true
PSI_LOG_RAW_EVIDENCE=false
```

Use `PSI_LOG_DESTINATION=file` with `PSI_LOG_FILE=/path/events.jsonl`, or set `PSI_LOKI_URL` and include `loki` in the destination. Multiple destinations are comma-separated. Loki is best-effort and never required for the application to start.

`PSI_LOG_RAW_EVIDENCE=true` emits a startup warning. It never disables secret redaction; complete Jira descriptions, comments, Grafana payloads, GitHub files, credentials, and tokens are not logged by default.

Wrap an investigation in `investigation_context(...)` to automatically attach a generated or caller-provided `correlation_id` and optional `investigation_id` to every event in the async task. Use `logged_tool_call(tool, operation)` for MCP/provider calls. Use `audit_event(...)` for security-relevant lifecycle events; audit records carry `log_type=audit`.

## Local Grafana

Run `docker compose up --build`, then open Grafana at <http://localhost:3000> with `admin` / `admin`. The Loki datasource and the Product Support Investigator dashboard are provisioned automatically. Promtail forwards Docker JSON logs to Loki and only uses low-cardinality labels: `service`, `environment`, and `level`.
