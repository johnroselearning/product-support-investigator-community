# Optional Grafana integration

The skill works without Grafana. Architecture:

```text
User → investigator → investigation question → evidence-provider contract
                                             → Grafana adapter → Loki / Prometheus
                                             → future providers
```

See [the common contract](../references/evidence-providers.md), [Grafana requests and limits](../references/grafana.md), and [the synthetic investigation example](../examples/grafana-checkout.md).

## Local runtime

Python 3.10+ and the standard library are sufficient. Configure `GRAFANA_URL` (HTTPS base URL, including a deployment subpath if needed) and `GRAFANA_TOKEN` using a trusted launcher or secret manager. Use a service account restricted to the necessary datasource metadata/read/query permissions. Do not put values in prompts, repository files, shell command history, Jira issues, or tool arguments. Never print the environment to diagnose setup.

Save only the non-secret request as JSON, then run from the repository/package root:

```bash
python3 scripts/grafana_evidence.py < request.json
```

Without configuration the CLI emits a `not_configured` evidence envelope. HTTP errors become access limitations; the investigator continues from user evidence or another provider. The CLI returns JSON even for provider failures: inspect `retrieval_status`, not the process exit code.

An existing read-only Grafana MCP integration can be used instead. No MCP server is automatically installed, registered, or required. Verify its permissions and enforce equivalent normalization/redaction/output bounds in its trusted backend. Never invoke mutation tools just because the MCP exposes them.

## Atlassian boundary

This release does not connect the deployed Forge app to Grafana. It preserves the current Jira action and manifest, and adds the common investigation behavior to the self-contained Rovo prompt. A future secure backend must enforce tenant/user authorization, datasource allowlists, limits, secret storage, and egress before exposing a telemetry action. Do not pass credentials through a Rovo action payload. See the platform contract above.

## Verification

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/validate_skill.py
python3 scripts/package_plugin.py
```

Tests use synthetic responses and no real credentials/network. They check acquisition and normalization; the behavior cases in `tests/cases.json` separately evaluate investigator reasoning. Live Grafana/MCP/Forge smoke tests require an authorized installation and are not part of offline validation.
