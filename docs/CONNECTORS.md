# Connectors

Connectors are optional evidence providers, separate from investigation reasoning. The [versioned evidence contract](../references/evidence-providers.md) extends the existing E1/E2 ledger without changing Jira evidenceVersion 2. It applies to Codex, Claude, and future secure Forge telemetry actions.

Available: Jira/Rovo via the existing Forge action; optional [Grafana HTTP adapter](GRAFANA.md) for bounded health/discovery, Loki logs, and Prometheus metrics. Grafana is not wired into Forge. Existing read-only MCP tools may supply the same contract after trusted normalization.

Future providers can implement the same contract for Datadog, Sentry, GitHub, CloudWatch, Azure Monitor, Kubernetes, OpenTelemetry, Elasticsearch, or Splunk without changing the investigation workflow. No source is required. Provider errors remain access limitations, never application evidence.
