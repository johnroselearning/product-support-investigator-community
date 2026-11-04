# Harness verification record

Date: 4 November 2026. Harness version: **0.1.0**. Dataset version: **1.0**.

The implementation and local verification are complete. Semantic classification and evidence conclusions in the offline demo are explicitly scripted simulations. **No real-model quality scores, live integration success, token savings, or bias-free behavior are claimed.**

## Verification performed

| Check | Result |
| --- | --- |
| Deterministic contract/security tests (`test_harness_contracts.py`) | 19 passed |
| Fixture integration tests (`test_harness_integration.py`) | 12 passed |
| Mocked Grafana bridge tests (`test_harness_grafana.py`) | 3 passed; no network |
| Versioned offline evaluation | 36 cases passed all eight separate dimensions |
| Local representative demo (`python3 -m investigation_harness --all`) | Completed six simulated scenarios |
| Existing Grafana, observability, and trace Python tests | 29 passed |
| Existing skill/generated-file validation | Passed; generated files unchanged |
| Existing Forge trace test | Passed (`node --test forge-app/src/trace.test.mjs`) |
| Full Python discovery using `.venv-mcp` | 70 tests: 67 passed, 3 existing MCP protocol tests timed out during `initialize`; see below |
| Whitespace validation (`git diff --check`) | Passed |

The standard system Python cannot import the repository's MCP package. Harness-only tests run without that dependency. The existing `.venv-mcp` environment was used for full repository validation.

The three failing existing tests are:

- `test_mcp_skills.ProtocolTests.test_invalid_requests_over_wire`
- `test_mcp_skills.ProtocolTests.test_legacy_client_fallback`
- `test_mcp_skills.ProtocolTests.test_native_discovery_and_complete_retrieval`

They report `MCPError: Request 'initialize' timed out`. The legacy-client failure was reproduced by running only that test, without importing the new harness. This delivery does not modify the existing MCP server or the user's tracing changes. The full suite is therefore **not green** in this environment; the MCP handshake failure remains unresolved. The new tests and unaffected regression checks pass independently.

## Offline dataset and results

[Cases and independent expectations](../tests/harness/cases.v1.json) contain synthetic conversation/artifact snapshots and acceptable outcomes. Fifteen cases are development cases; twenty-one are held-out cases. The fixture script does not read expected decisions. The evaluator passes only request/state/contracts to the semantic adapter; expected answers, case IDs, split labels, and grader feedback do not enter model inputs. Multiple valid capability paths are accepted where appropriate.

[Machine-readable results](../tests/harness/evaluation-report.v1.json) record per-case checks, termination, call counts, and accurately labeled token accounting.

| Dimension | Fixture cases passing |
| --- | --- |
| Routing (including mixed goals) | 36 / 36 |
| Skill selection | 36 / 36 |
| Clarification necessity | 36 / 36 |
| Tool choice | 36 / 36 |
| Readiness | 36 / 36 |
| Evidence support contracts | 36 / 36 |
| Security checks | 36 / 36 |
| Efficiency bounds | 36 / 36 |

These are runtime regression results. Neither the overall counts nor the held-out split demonstrate real-model generalization. The evidence-support dimension checks references, exact observed excerpts, allowed claim types, and minimum retained evidence. It does not establish semantic entailment. Token usage is unavailable for fixtures; reservations are explicitly estimated. No savings baseline was measured.

Coverage includes explanation, rewriting, direct retrieval, actual and hypothetical incidents, supplied stack traces, mixed and multi-turn requests, Jira-first context acquisition, missing service discovery, sparse informal requests, unresolved tenant/environment scope, retrieved conflicts, missing/unavailable tools, alternative-tool fallback, empty/partial/stale results, misleading release suggestions, unsupported team blame, prompt injection, redaction, cross-tenant attempts, repeated calls, and pagination.

## Residual gaps

- A real structured-output model adapter must be supplied by the host; no production credentials were used or requested.
- Live Grafana is opt-in and tested with mocked process/provider responses only. GitHub/Jira bindings in this runtime are fixtures; existing Forge/Jira behavior is unchanged.
- Conditional critic and deterministic checks cannot prove causal correctness. V1 keeps root cause Unknown and removes unverified strong claims.
- Native Codex, Claude, and Rovo calls remain outside this runtime's enforcement boundary. Hosts must integrate tool interception, authenticated grants, model routing, and egress controls explicitly.
- Redaction and semantic resistance to prompt injection or bias remain imperfect. Human review is needed before external sharing or consequential decisions.
- The existing MCP initialization timeout needs separate investigation before claiming a fully passing repository suite.

See [architecture, limits, and local/live-adapter instructions](INVESTIGATION_HARNESS.md). No deployment, publishing, commit push, production mutation, or public service exposure was performed.
