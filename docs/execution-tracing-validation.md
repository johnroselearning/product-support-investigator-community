# Execution tracing implementation validation

Implementation is locally tested; authenticated Grafana verification remains pending.

## Architecture and schema

See [architecture and interface](execution-tracing.md) and the complete typed
[schema](../observability/trace/schema.py). There was no central investigation
orchestrator: the application boundaries are skill distribution over MCP, the Grafana
HTTP provider, and the Forge Jira action. Root SKILL.md and generated platform
instructions remain the investigation methodology. Unobserved host phases are not_run.

## Examples (synthetic fixtures)

| Example | Skill applied | Final status | Confidence |
|---|---|---|---|
| [successful-investigation](../examples/traces/successful-investigation.json) | True | completed | High |
| [skipped-skill](../examples/traces/skipped-skill.json) | False | skipped | None |
| [failed-grafana](../examples/traces/failed-grafana.json) | True | failed | None |

Each linked JSON contains every schema field, phase, compliance result, event,
tool outcome, evidence summary and hypothesis status. These are explicitly synthetic,
not production incident results. The failed case records TimeoutError without its
message or raw evidence.

## Checks performed

- Full Python suite: **36 tests passed**, including real MCP subprocess clients.
- Forge instrumentation: **2 Node tests passed**.
- `python3 scripts/validate_skill.py`: **VALID**, generated files synchronized,
  314 canonical skill lines and 16 behavioral evaluation cases.
- `git diff --check`: passed.
- Default Docker stack: application, Loki and Promtail running with final code.
- Live Loki query for `{service="product-support-investigator"} | json |
  event_type="skill_decision_completed"`: success, one stream and one event at
  initial validation. This is an actual startup trace whose skill decision is skipped.
- Existing `grafana-local` detected on HTTPS port 3000 and connected to the Compose
  network. Bundled Grafana is now opt-in; the stopped duplicate container from the
  first startup attempt was removed. Existing Grafana data was not replaced.

## Failures and verification limits

- Sandboxed MCP integration tests timed out during initialization. The complete
  suite passed outside that sandbox (4.98 seconds on final run).
- Initial Docker startup failed mounting the host Docker containers directory;
  removed that unused mount because the collector reads through Docker's API.
- Initial Grafana startup hit an occupied port; reused existing Grafana instead.
- Existing collector discovered unrelated containers and produced old-log rejection
  errors. Added a keep filter selecting only the PSI application service.
- Existing Grafana serves HTTPS with a local certificate and rejects admin/admin
  with HTTP 401. The in-app browser rejects the certificate. Authenticated datasource
  configuration and Grafana query verification await user sign-in; **not verified**.
- Real Jira/Rovo deployment and a credentialed live Grafana evidence retrieval were
  not performed. Forge tests cover the trace boundary locally. No mutation scopes
  or production writes were introduced.
- The checked-in behavioral evaluation scenarios are validated structurally, not
  executed against a hosted model. No claim is made about hidden host reasoning.
- Node reports an existing package module-type warning; tests still pass. The
  Forge package's module configuration was preserved.

## Files created or modified by this implementation

- [`.dockerignore`](../.dockerignore)
- [`.gitignore`](../.gitignore)
- [`README.md`](../README.md)
- [`docker-compose.yml`](../docker-compose.yml)
- [`docs/execution-tracing.md`](../docs/execution-tracing.md)
- [`examples/traces/failed-grafana.json`](../examples/traces/failed-grafana.json)
- [`examples/traces/skipped-skill.json`](../examples/traces/skipped-skill.json)
- [`examples/traces/successful-investigation.json`](../examples/traces/successful-investigation.json)
- [`forge-app/src/index.js`](../forge-app/src/index.js)
- [`forge-app/src/trace-contract.json`](../forge-app/src/trace-contract.json)
- [`forge-app/src/trace.js`](../forge-app/src/trace.js)
- [`forge-app/src/trace.test.mjs`](../forge-app/src/trace.test.mjs)
- [`observability/context.py`](../observability/context.py)
- [`observability/logging.py`](../observability/logging.py)
- [`observability/redaction.py`](../observability/redaction.py)
- [`observability/tool_calls.py`](../observability/tool_calls.py)
- [`observability/trace/__init__.py`](../observability/trace/__init__.py)
- [`observability/trace/__main__.py`](../observability/trace/__main__.py)
- [`observability/trace/evaluator.py`](../observability/trace/evaluator.py)
- [`observability/trace/examples.py`](../observability/trace/examples.py)
- [`observability/trace/provider.py`](../observability/trace/provider.py)
- [`observability/trace/schema.py`](../observability/trace/schema.py)
- [`observability/trace/store.py`](../observability/trace/store.py)
- [`ops/promtail/config.yml`](../ops/promtail/config.yml)
- [`providers/grafana.py`](../providers/grafana.py)
- [`scripts/sync_skill.py`](../scripts/sync_skill.py)
- [`skill_adapter/server.py`](../skill_adapter/server.py)
- [`skills/product-support-investigator/providers/grafana.py`](../skills/product-support-investigator/providers/grafana.py)
- [`tests/test_trace.py`](../tests/test_trace.py)
- [`docs/execution-tracing-validation.md`](execution-tracing-validation.md) (this report)

Pre-existing changes to both example Forge manifests, the manifest backup,
`gepa_demo.py`, and root `package-lock.json` were preserved.
