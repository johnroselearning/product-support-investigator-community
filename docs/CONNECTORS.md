# Connectors

Connectors are optional evidence providers. Current adapters include Jira/Rovo and the repository's Forge starter; Zendesk and Datadog remain optional. The workflow also supports future providers such as Grafana, Splunk, Elastic, CloudWatch, Azure Monitor, New Relic, Dynatrace, Sentry, GitHub, GitLab, PagerDuty, ServiceNow, Slack, Microsoft Teams, OpenTelemetry, Prometheus, Kubernetes, AWS, Azure, and GCP.

Each connector should return source identifiers, timestamps, observed content, reliability, truncation/availability limits, and read-only behavior where possible. Adding a connector must not change the investigation method or report contract.
