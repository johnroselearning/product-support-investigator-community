# Grafana provider

Read [the common contract](evidence-providers.md) first. The optional adapter in `providers/grafana.py` supports Grafana instances exposing the datasource UID proxy API, Loki streams, and Prometheus-compatible range-query matrices. Other datasource plugins are unsupported, not failures of the investigated application. There is no dashboard, alert, datasource, user, organization, or configuration write capability.

## Local request example (synthetic)

```json
{
  "evidence_id": "E7",
  "purpose": "Which backend recorded the reported failing request?",
  "operation": "logs",
  "datasource_uid": "replace-with-discovered-uid",
  "scope": {
    "service": "checkout",
    "environment": "production",
    "start_time": "2026-09-23T10:31:00Z",
    "end_time": "2026-09-23T10:33:00Z",
    "labels": {"service": "checkout", "environment": "production"}
  },
  "identifiers": {"request_id": "req-81273"}
}
```

Label names and values are installation-specific: confirm them from authorized configuration or existing evidence. The adapter builds escaped exact-label LogQL selectors, followed by a literal line filter for the strongest identifier (request, correlation, trace). Without an identifier it uses supplied endpoint/error text. Filters are substring matches; verify the actual identifier field before attributing the log. It does not silently expand a search. A request ID stored only in structured metadata may require an available MCP tool with an appropriate selector; absence from a line search is not evidence of absence.

For metrics use `operation: metrics`, a discovered Prometheus UID, the same time scope, a supplied `query` (PromQL), and optional `step_seconds` (default 30). PromQL must explicitly enforce the relevant scope. Metric names, units, labels, and aggregation semantics must come from real evidence/documentation. The adapter does not generate PromQL or infer causes.

For `health` or `datasources`, supply an evidence ID and purpose, optionally `datasource_type: loki|prometheus` or a known `datasource_uid`. Health checks `/api/health` and datasource metadata. Metadata only advertises capability: it does not prove query permission or datasource availability. Discovery returns at most 20 supported datasource summaries, never credentials, datasource URLs, or configuration. A known UID avoids the list call; type filtering is local because the list endpoint has no type filter.

## Limits and failures

HTTPS only, bearer token from environment, no redirects, 10-second socket timeout, no automatic retries, maximum 1 MiB HTTP body, maximum one-hour query window, 100 observations, 2,000 characters per text field, 20 labels per observation, at most 1,001 evaluation steps per metric series. The HTTP timeout is a socket timeout, not a guaranteed total wall-clock deadline. Narrow queries and enforce server-side query budgets for production use. Returned timestamps retain their source units; Loki nanoseconds remain strings to avoid precision loss.

Oversized wire bodies are discarded with `response_too_large`, rather than parsed partially. Smaller bodies are normalized and clipped with explicit limitations. Bound hits may hide matches; never treat clipped results as complete. Redaction is best effort and precedes text truncation. Raw errors and response bodies are not echoed. Provider failures yield no application observations.

## API references

The adapter uses fixed GET paths only:

- Grafana `/api/health`, `/api/datasources`, `/api/datasources/uid/:uid` and `/api/datasources/proxy/uid/:uid/*`: [Grafana HTTP API](https://grafana.com/docs/grafana/latest/developer-resources/api-reference/http-api/) and [route definitions](https://github.com/grafana/grafana/blob/main/pkg/api/api.go).
- Loki `/loki/api/v1/query_range`: [Loki HTTP API](https://grafana.com/docs/loki/latest/reference/loki-http-api/).
- Prometheus `/api/v1/query_range`: [Prometheus HTTP API](https://prometheus.io/docs/prometheus/latest/querying/api/).

Grafana versions, datasource plugins, and hosted deployments differ. Verify proxy support and least-privilege datasource read/query permissions for the target installation. No live endpoint compatibility is claimed by the mocked tests.
