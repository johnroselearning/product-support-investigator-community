# Local request-understanding and investigation harness

Version 0.1.0 adds an optional Python runtime under `investigation_harness/`. It uses the existing evidence method and redactors. It does not change the Forge action, existing MCP distribution server, native host permissions, or the user's tracing implementation. No framework, database, model SDK, or additional agent is required.

## Run locally

From the repository root with Python 3.10+:

```bash
python3 -m investigation_harness --all
python3 -m investigation_harness --scenario jira --events
python3 -m investigation_harness --scenario sparse
python3 -m investigation_harness --scenario conflict
python3 -m unittest discover -s tests -p 'test_harness*.py' -v
python3 -m investigation_harness.evaluate --split dev
python3 -m investigation_harness.evaluate --split heldout
```

Every demonstration is labeled **SIMULATED**. Requests, Jira/GitHub/Grafana responses, and semantic decisions are synthetic. The fixture adapter selects a declared scenario by ID; it does not classify language. Unknown scenarios fail instead of silently falling back to a keyword router. No credentials, network access, public services, or production changes are needed.

The whole repository test suite also needs the existing MCP dependencies:

```bash
.venv-mcp/bin/python -m unittest discover -s tests -p 'test_*.py'
.venv-mcp/bin/python scripts/validate_skill.py
node --test forge-app/src/trace.test.mjs
```

If that environment is absent, create a local virtual environment and install `requirements-mcp.txt` using the project's existing setup. The harness alone uses the standard library and repository modules.

## Architecture and contracts

`routing.json` supplies applicability guidance **before** the full skill is loaded. `SemanticAdapter` separates interpretation from policy. `understand` receives the conversation, supplied artifacts, and routing metadata, then returns independent goals (including mixed requests), actual/hypothetical/unclear context, route, evidence references, scope candidates, constraints, interpreted authorized actions, and decision-relevant ambiguities. Its structured restrictions may narrow host permissions; they cannot grant access.

The five routes are direct answer, direct retrieval, supplied-evidence investigation, external-evidence investigation, and essential clarification. Missing fields and tool availability do not decide skill applicability. No keyword classifier, confidence cutoff, or vendor preference is used.

The single loop runs:

```text
understand → select skill → choose capability → load its actual contract
     → propose → resolve scope → check → execute → update evidence
     → choose again or report → conditional critic → report checks
```

Components:

| Module | Responsibility |
| --- | --- |
| `contracts.py` | Strict, intentionally small JSON Schema subset; unsupported keywords and extra fields fail closed |
| `semantic.py` | Async semantic/model and critic interfaces, host callback bridge, deterministic critic baseline |
| `registry.py` | Evidence need, coverage, freshness, preconditions, alternatives, exact tool binding and I/O contracts |
| `policy.py` | Independent readiness checks, trusted permissions, scope, time/query/result/cost bounds |
| `engine.py` | One bounded loop, acquisition, provenance, deduplication, safe partial results |
| `reports.py` | Evidence references, quote support, conservative strong-claim rejection, mandatory coverage gaps |
| `state.py` | Compact state, run IDs, versions, usage, redaction, content-free event summaries |
| `fixtures.py` | Explicit simulated semantic decisions and synthetic providers |
| `service_map.py` | Optional bounded, operator-supplied service leads; never grants access |
| `grafana.py` | Optional constrained bridge to the existing real HTTP provider |
| `evaluate.py` | Independent grading across eight dimensions; never passes expected answers to adapters |

Registry capabilities include fetch issue, discover service, search logs, query metrics, retrieve trace, read repository file, deployment metadata, revision comparison, and list commits. Names are conceptual capabilities, **not invented MCP methods**. Fixture bindings are explicitly named `fixture.<provider>.<operation>`. A host must bind a discovered real tool and its actual schema, scope translation, destination, and callable. Read-only tool annotations alone never authorize execution.

Each readiness result records capability existence, current availability, schema validity, adequate context, authorization, and limits. A malformed schema prevents interpretation of unsafe fields; later checks are `not_checked`. Missing input, ambiguous scope, unavailable capability/tool, authorization denial, execution failure, empty, and partial results remain distinct.

The state retains every conflicting candidate with `user_provided`, `retrieved`, `configured`, or `inferred` provenance and its source locator. Uncorroborated model-extracted user fields fail validation. Inferred boundaries cannot authorize calls. Resolution prefers conversation/artifacts, then an independently ready declared retrieval alternative, then configured bounded time defaults, then one focused clarification. Defaults never select a tenant, environment, repository, or datasource. Scope recovery cannot erase conflicts. A named issue can fill in service and time; a missing service can permit tenant/environment-scoped discovery.

Provider content is untrusted. Structured resolution hints need a matching returned evidence record; they cannot mutate policy. Returned security scope must match the request and operator/user allowlists. The ledger preserves source locators, source timestamps, Observed classification, limitations, staleness, and contradiction annotations. An observed entry means “this source reports this,” not verified application truth. Reports distinguish observed claims, inferred claims, hypotheses with support/contradictions, and unknowns. A recent commit, repository file, or empty log query never establishes deployment, causation, or absence of failure.

## Host model adapter

There was no reusable model adapter in this repository. `CallbackAdapter` is the integration seam; this release does not add a provider SDK or silently send evidence to a model service. Implement an async callback:

```python
from investigation_harness.semantic import CallbackAdapter, Decision

async def decide(stage, payload, max_output_tokens):
    # Use your host's approved structured-output client here. Credentials stay
    # in its runtime configuration. Honor cancellation and max_output_tokens.
    # payload['response_contract'] contains the expected JSON contract.
    value, usage = await approved_host_model(stage, payload, max_output_tokens)
    return Decision(value, usage.input_tokens, usage.output_tokens)

adapter = CallbackAdapter(decide, destination="your-approved-model-destination")
```

The illustrative `approved_host_model` is supplied by the host; it is not a bundled or discovered tool. Stages are `understand`, `choose`, `propose`, `report`, and bounded `revise`; `ModelCritic(adapter)` also supports `critic`. `choose` sees capability summaries, then `propose` sees only the selected binding's schema. Selected canonical skill sections carry source paths and digests. Provider credentials, expected evaluation answers, and raw exception messages never enter these payloads.

Call `await Harness(adapter, registry, trusted_policy).run(request)` with a new harness per concurrent run. Requests contain `messages` (conversation text strings), `artifacts` (bounded evidence records), and explicit `scope`. The tests and versioned dataset contain complete examples. The operator constructs frozen `Policy` and `Limits` instances. Tenant grants and host-authenticated user grants must both permit a capability; `user_scope` further restricts dimensions. Semantic `authorized_actions` is descriptive, not an access grant. Hosts must independently enforce any user restriction whose interpretation is consequential.

To evaluate a real adapter **with synthetic tools only**, provide a trusted no-argument Python factory returning a non-simulated adapter:

```bash
python3 -m investigation_harness.evaluate --adapter my_host_adapter:create --split heldout --output /tmp/real-model-eval.json
```

This explicit option permits the configured model destination and may incur its provider charges. The factory receives no case IDs, expected decisions, split labels, or grader feedback. Keep credentials in its runtime configuration and independently review actual model results. No real-model evaluation has been run for this delivery.

## Optional service mappings

Construct a `ServiceMap` in trusted host code and pass it as `Harness(..., service_map=...)`. For example:

```python
from investigation_harness.service_map import ServiceMap
service_map = ServiceMap([{
    "service": "checkout", "aliases": ["cart"], "routes": ["/pay"],
    "components": ["api"], "environments": ["production"],
    "datasources": ["approved-loki-uid"],
    "telemetry_labels": {"service": "checkout"},
    "dependencies": ["payments"], "owners": ["checkout-team"],
}])
```

A known service, alias, route, or component in the established service scope matches exact entries; at most ten entries are presented to the model as leads. An unknown scope never enumerates the catalog. Mapping entries neither fill trusted scope nor authorize calls, prove causation, or replace discovery. Scope must still be established independently and pass host policy. Configurations are copied and bounded to 100 entries; keep credentials out of them.

## Optional live Grafana binding

Live execution is opt-in host code. The demo never turns live when it finds environment variables. The repository's existing `GrafanaProvider` is the only supported real provider bridge. GitHub and Jira examples remain fixtures; native Forge/Jira access is unchanged and not invoked by this Python harness.

```python
import os
from investigation_harness.grafana import bind_grafana
from investigation_harness.registry import Registry
from investigation_harness.state import Policy

registry = Registry()
url = "https://grafana.your-approved-domain.example"
bind_grafana(
    registry,
    url=url,
    token=os.environ["GRAFANA_TOKEN"],
    datasources={"approved-loki-uid": "loki", "approved-prom-uid": "prometheus"},
    label_names={"tenant": "tenant_id", "environment": "environment", "service": "service"},
    metrics=["http_errors_total"],
)
policy = Policy(
    tenants=frozenset({"your-tenant"}), environments=frozenset({"production"}),
    datasources=frozenset({"approved-loki-uid", "approved-prom-uid"}),
    capabilities=frozenset({"search_logs", "query_metrics"}),
    user_capabilities=frozenset({"search_logs", "query_metrics"}),
    user_scope=(("tenant", "your-tenant"),),
    destinations=frozenset({"local", url}),
)
```

Replace sample values only from trusted operator configuration. The actual datasource must enforce the configured tenant/environment/service labels and least-privilege service-account access. Grafana is not assumed to store application logs: an approved Loki UID is required for logs, and Prometheus for metrics. The existing provider verifies datasource type before querying. The bridge supports exact fixed metric names plus mandatory scope selectors; no arbitrary PromQL, URLs, queries, or cursors. Returned labels are checked again. The bridge records sanitized provider failure categories in limitations; timeout and transport failure are combined by the underlying provider as unavailable. Zero matches remain inconclusive. The existing provider reads at most 100 observations / 1 MiB on the wire; this bridge applies tighter model-visible limits and marks incomplete coverage. No live service discovery is exposed.

Each live call runs the existing synchronous provider in a child process with only its required environment, fixed GET paths, redirect rejection, and bounded output. Harness cancellation kills and reaps the child. Tokens stay outside prompts and events. Pass additional known sensitive values in `Harness(..., secrets=(... ,))` for explicit redaction if needed. Enforce network egress and endpoint/DNS trust at the host as well. The bridge has only mocked verification here; no production credentials or live calls were used.

## Budgets, critic, and reporting

`Limits` bounds tool calls, per-action retries, elapsed time, per-call timeout, model calls, model token reservations, output size, evidence records, results, query windows, operator-defined cost units, and critic revisions. Identical executed calls are suppressed; only a timed-out attempt is eligible for a bounded retry. Other failures are not presumed transient. Pagination accepts only a cursor returned for the same capability/query. Repeated evidence is deduplicated without dropping new contradiction annotations; a full ledger stops with a partial report instead of silently evicting evidence.

Model adapters must honor cancellation and output limits. The harness bounds returned JSON to four bytes per requested output token and conservatively reserves UTF-8 input bytes plus that entire output byte cap as token-equivalent units. This is a labeled estimate, **not measured token usage or savings**. Provider input/output counts are retained separately when available; absent counts remain null. Cost units are configurable operator units, not monetary billing guarantees. Network adapters and host model clients are trusted code: cooperative cancellation alone cannot contain an arbitrary blocking callback or an adapter that secretly makes extra calls.

Conflicts, significant gaps, consequential claims, and strong causal/attribution claims trigger a replaceable critic. It receives the goal, bounded evidence with references, and proposed conclusion, and returns unsupported claims, contradictions, alternatives, and needed evidence. The default deterministic critic is a conservative baseline, not a model. Revision cycles are bounded. Critic findings cannot execute tools, grant permissions, or establish truth.

Deterministic report checks validate references and exact observed excerpts, reject unverified strong causal/blame/deployment/absence claims, and preserve empty/partial/stale/conflicting coverage gaps. Investigation summary prose is rendered conservatively so a free-text summary cannot bypass claim checks. V1 deliberately keeps root cause **Unknown**: it does not have a machine-verifiable causal-proof contract. Inference and hypothesis entailment still require semantic/human review; citations alone are not proof. These reports are internal investigation artifacts, not automatically approved customer communications.

Default events contain run ID, optional host-supplied parent investigation ID, component version, timestamps, route/skill, readiness enums, actual tool binding identifiers, call duration, result and retry counts, evidence IDs, budget usage, critic finding counts, and termination. They contain no prompts, retrieved excerpts, arguments, or private chain-of-thought. Events are held in memory; only `--events` prints them. Reports contain bounded, redacted excerpts. The existing tracing system is neither replaced nor represented as enforcing this harness; the existing Grafana provider may still emit its existing local tracing metadata.

## Platform and security boundaries

| Surface | Enforced here | Requires host/adapter support | Still instructional outside the harness |
| --- | --- | --- | --- |
| Python harness | Registered read path, schema/scope/user/destination checks, budgets, redaction, evidence/report checks | Trusted policy, correct tool schema/normalization, model and network client behavior, egress isolation | Semantic truth, causal inference, customer-safe editorial review |
| Codex / Claude | Only calls explicitly routed through `Harness` | Tool discovery/schema binding, authenticated user grants, native call interception, model adapter | Existing skill instructions do not intercept native tools |
| Jira Rovo / Forge | Existing Forge action retains its own issue validation, `asUser()` authorization and bounded retrieval | A separate authenticated bridge or Forge implementation of these checks | Python harness is not installed inside Rovo and cannot police Rovo/native actions |

No mutation or outbound data-sharing capability is supported. Tool descriptions, issues, logs, code comments, and model/critic responses cannot authorize access. Permission scope and allowed destinations come only from trusted host construction. Prompt injection can still distort a model's interpretation or suggested text; executable boundaries limit its actions but do not make reasoning immune. Redaction is best effort and may miss unusual secrets, personal data, and sensitive source locators. The system is neither breach-proof nor demonstrated unbiased. Fixture neutrality, informal-language, causal-suggestion, and team-blame cases are regression checks, not a fairness study.

See [the evaluation record](HARNESS_EVALUATION.md) for the exact verification scope and remaining gaps.

Future hosts can supply a parent investigation ID to `run` and persist the returned events through their own telemetry pipeline. Alert triggers and reviewed improvement proposals remain host extension points; no scheduler, autonomous publishing, or improvement workflow is implemented.
