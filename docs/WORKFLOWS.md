# Scoped PSI workflows and maintenance regressions

The portable [workflow reference](../references/workflows.md) describes customer
investigation, PSI maintenance and incident/defect/mixed examples. This executable
foundation extends the existing harness, registry, policy and trace schema; it
adds no MCP server, credential store or external execution service.

## Request understanding and linked work items

The `understand` response now requires `decision`: `general_question`,
`customer_investigation`, `psi_maintenance`, `mixed` or `needs_clarification`.
Existing `goals` describe intent; `route` controls answer/retrieval/investigation/
clarification. Each `work_items` entry separately contains `workflow`,
`target_system`, `evidence_scope`, `requested_action`, `evidence_needs`,
provenance-bearing `scope`, `evidence_refs` and `defect_type`. Host model adapters
must use this updated response contract. Fixtures are simulations, not a language
classifier or proof of intent accuracy.

A general-question decision forces a direct answer with zero evidence calls.
Mixed requests require exactly one customer and one PSI item. Assign mixed scope
per item; a global ambiguous scope fails closed. Extracted scope must cite a source
containing its value. Only that item's selected and correctly tagged artifacts
enter its ledger. Untagged legacy artifacts default to `customer_application`;
PSI artifacts require `psi_maintenance` or `psi_execution`. The classifier sees
the supplied request; subsequent planning, proposals, reports and critics see
only their work item's evidence and scope.

A single workflow still returns `State`. Mixed requests return two isolated states
in `work_items` and separate reports, with no combined evidence ledger. Each item
has a distinct `run_id`/`work_item_id`; its `parent_investigation_id` points to the
mixed request. Children share trace/correlation IDs. An active recorder's existing
investigation/trace/correlation IDs are reused. A host-provided parent can link a
follow-up; the conversation must still be supplied in `messages`. No persistent
conversation memory is added. Mixed items run sequentially under shared elapsed,
tool-call, model-call, token-reservation and cost budgets.

## Trusted capability and resource mapping

Registry entries describe provider, availability, operation, access mode, roles
and permitted workflows. `Policy.resource_scopes` maps exact roles and targets to
operations, repositories, datasources and selectors. These mappings further
restrict global operator and authenticated user grants. They never fill missing
repository/datasource inputs or authorize mutations.

```python
from investigation_harness.registry import ResourceScope

customer_code = ResourceScope(
    "customer-code", "customer_github", "ams",
    frozenset({"read_repository_file", "list_commits", "read_repository_issue", "read_pull_request"}),
    repositories=frozenset({"example/ams"}),
)
psi_logs = ResourceScope(
    "psi-telemetry", "psi_grafana", "psi", frozenset({"search_logs"}),
    datasources=frozenset({"operator-supplied-uid"}),
    selectors=(("tenant", "operator-tenant"), ("environment", "production"),
               ("service", "product-support-investigator")),
)
# Pass these in Policy(resource_scopes=(customer_code, psi_logs), ...).
# Bind the discovered host tool's actual callable and input/output translation:
# Binding(..., roles=frozenset({"customer_github"}),
#         permitted_workflows=frozenset({"customer_investigation"})).
```

These are placeholders, not live datasource IDs or repositories. Four roles are
supported: `customer_github`, `customer_grafana`, `psi_github`, `psi_grafana`.
A shared binding may explicitly permit both matching roles/workflows. The
intersection is rechecked before every call/retry. Grafana mappings require an
explicit service selector, including when roles share a datasource. Returned
resources, selectors and evidence domains are checked again.

Readiness also checks the declared evidence need, availability, actual input
schema, adequate provenance-bearing scope, limits, global/user grants and read-only
destination. Natural-language relevance still depends on the model; the harness
deterministically checks its declared evidence need. Missing connectors retain
supplied evidence and allow other checks. Unknown mappings never fall back to
the PSI repository or enumerate arbitrary resources. User-supplied evidence can
still be analyzed without a connector or known mapping; it grants no tool access.

## Review-only handover and regression selection

`maintenance.prepare_draft(state, defect_type, requested=True)` returns a separate
linked draft. Without a request it requires matching observable PSI behavior, such
as a provider failure or blocked repository attempt. Missing connectors alone
are insufficient. Customer tool failures do not automatically create drafts.
A PSI work item requesting `draft_issue` or `propose_tests` can prepare one after
analysis. No GitHub write exists in this workflow.

Drafts contain expected/actual behavior, synthetic reproduction, classified
evidence, opaque IDs, impact, a proposed allowlisted test and acceptance criteria.
Free-text evidence is deliberately excluded; unsupported behavior stays reported
and unverified. Fixed descriptions cover the initial defect catalog and a scoped
capability feature proposal. Detailed editorial text requires human review.

`regressions.catalog()` describes test ID, defect type, exact input schema, local
check, environment, required permission, timeout and result format.

```python
from investigation_harness.regressions import select_regression
selection = select_regression(
    "wrong_repository", "routing-scope-v1", {"case_id": "wrong_repository"},
    work_item_id="opaque-maintenance-id", approved=True,
)
assert selection["execution"] == "not_run"
```

Approval comes from trusted host/UI confirmation, never issue text or a model.
Unknown IDs, mismatched defects and extra inputs (commands, URLs or workflow
parameters) fail validation. Selection exposes no callable, shell or workflow
dispatch. There is no external test executor or result ingestion API. Run the
fixed local checks below and report actual results separately. The Forge entry
maps to its Node response contract test. No browser framework is needed.

## Runtime and telemetry boundaries

Trace schema **1.1** additively extends `observability/trace/schema.py`. Harness
events use the existing logger, or an active recorder's store. Without an active
recorder there is no automatic SQLite persistence. Logging remains host-configured.
Events retain legacy harness fields and add `event_type`, `workflow`,
`work_item_id`, `parent_investigation_id`, `target_system`, `capability`, `operation`,
`resource_scope_id`, `outcome`, `error_type`, `duration_ms` where observable, and
trace/correlation/investigation IDs. Every event is `psi_execution` telemetry,
including customer-workflow events; none proves customer application cause.

Outcomes are `succeeded`, `failed`, `skipped`, `blocked`, `unavailable`, `unknown`.
Starts and unobserved completion are unknown. A successful empty/partial read
describes execution, not evidence completeness. Missing events prove neither
success nor a skip. Provider errors retain safe categories, not exception text.
IDs remain JSON fields; Loki labels remain service/environment/level. No prompts,
customer evidence, credentials or code enter these events.

The existing dashboard adds investigation activity, PSI execution health and
maintenance/regression proposal views. [Grafana guidance](GRAFANA.md#psi-execution-views)
queries actual fields; regression runs/metrics are not invented. No live Grafana
instance is modified or provisioned by this implementation.

Portable instructions do not enforce access; native host calls bypass the harness.
Trusted host code must bind its MCP tools and authenticated grants. The existing
bounded Grafana HTTP bridge is retained, opt-in, with explicit roles and the same
policy checks. No live GitHub adapter is bundled. Forge/Rovo retains the Jira-only
`asUser()` action and scopes, adds a response contract check and execution metadata,
and records GitHub/Grafana as unavailable. It does not run Python mixed workflows,
expose GitHub/Grafana actions, or persist Rovo follow-up context. Its reasoning
completion remains unknown.

## Local verification and deferred operations

```bash
python3 scripts/sync_skill.py
python3 scripts/validate_skill.py
.venv-mcp/bin/python -m unittest discover -s tests -p 'test_*.py'
python3 -m investigation_harness.evaluate --split all
node --test forge-app/src/trace.test.mjs forge-app/src/response.test.mjs
python3 scripts/package_plugin.py
git diff --check
```

Normal tests use synthetic evidence and mock connectors. MCP protocol tests need
working subprocess stdio and the installed SDK; sandbox initialization timeouts
must be distinguished from functional failures. No real-model accuracy or live
integration was measured. Deferred: authenticated host bindings, external tests
and result ingestion, live dashboards, Forge deployment/installation, GitHub
filing/comments/workflows, push/publish, automatic patching/merging/deployment and
issue closure.
