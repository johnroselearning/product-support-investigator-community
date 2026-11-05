# PSI payload architecture and observation boundaries

Inspected 5 November 2026, against the existing working tree, including the
uncommitted optimization work. This document describes observable construction
boundaries. It does not describe hidden Codex, Claude, or Rovo model requests.

## Distribution and host-owned context

| Boundary | Construction / serialization | Observable locally | Outside this repository's control |
|---|---|---|---|
| Canonical skill | Root `SKILL.md`; `skill_adapter/bundle.py:read_bundle` snapshots a fixed public allowlist | Exact file bytes and hashes | Whether a host selects, injects, truncates, or repeats the skill |
| Portable copies | `scripts/sync_skill.py:outputs` copies the public bundle into `skills/product-support-investigator`; `codex/SKILL.md`, `claude/CLAUDE.md`, `atlassian/AGENT.md` provide host entry guidance | Source/generated instructions | Host system instructions, history packing, tool registry, request framing, actual usage |
| MCP distribution | `skill_adapter/server.py:create_server`, resources/read, skills/list/get, fallback list_skills/get_skill; default get_skill includes files | Public resource/tool response and manifest structure | How a host incorporates responses into subsequent model requests; retrieval itself is not a model call |
| Conditional references | Portable hosts follow `SKILL.md`; harness `context.py:selected_references/load_context` extracts selected headings with source hashes | Harness excerpts and static public files | Portable-host reference choices and any hidden prompt cache |
| Forge agent instructions | `scripts/sync_skill.py:outputs` joins `atlassian/compliance-gate.txt` and `atlassian/rovo-adapter.txt`; generates `forge-app/prompts/investigator.md` | Exact generated prompt bytes | Atlassian's system instructions, skill loading, action schemas, history, critic/final-response construction, model and billing |
| Forge registered skill | Generated `forge-app/skills/product-support-investigation/SKILL.md` and Markdown references; action protocol appended; manifest examples declare source | Bundled public skill and registration examples | Rovo skill selection, invocation, serialization, cache behavior |

Public file inventory counts measure available source material. They are **not**
per-request input counts. The generated Forge prompt retains the compliance gate;
this work does not regenerate it, change configuration, or deploy Forge.

## Harness context construction

All semantic objects pass through `investigation_harness/engine.py:Harness.model`.
That method deep-copies and applies the existing `safe` redactors, adds the
response contract, enforces destination/budget checks, then invokes the adapter.
The optional profiler observes a separate copy **after** those checks and
**before** adapter invocation. It does not add fields to model-visible objects.
Existing state reservations are byte-based safety budgets, not measured tokens.

| Actual stage name | Payload construction | What it represents |
|---|---|---|
| `understand` | `Harness.run`: request messages/artifacts/scope, `routing.json`, supplied evidence, UNDERSTANDING response contract | Request understanding, workflow planning; includes prior user messages supplied in this request |
| `skill_selection` | `process_work_item` chooses the skill from the validated route; emits an event | Deterministic step; **no separate model input** |
| `choose` | `investigate`: `State.view()`, relevant `Registry.catalog`, conditional `method` excerpts, service leads, choice response contract | Capability selection and investigation loop decision |
| `propose` | `investigate`: `State.view()`, selected capability and `Registry.contract`, proposal response contract | Bounded evidence-acquisition planning; not the tool execution itself |
| `evidence_acquisition` | `recover_scope`/`execute` perform readiness checks, call bound providers, validate/normalize results, `add_evidence` updates state | Tool execution; **no standalone model call**. Its outputs enter later `choose`/`propose`/`report` requests |
| `investigation` | Encompasses `choose` and `propose`, plus tool execution | Conceptual phase, not an additional request; no double counting |
| `report` | `report`: `State.view()`, conditional `method`, REPORT response contract | Initial final-response draft |
| `critic` | `report`: goal/understanding, complete bounded evidence ledger, conclusion, FINDINGS response contract | Conditional review |
| `revise` | `report`: `State.view()`, conclusion, findings, REPORT response contract | Conditional final-response revision |
| Finalization | `reports.py:finalize_report` removes unsupported claims, retains ledger/gaps, marks root cause Unknown | Deterministic post-processing; **no model call** |

`State.view()` serializes understanding, selected skill, workflow and work-item
scope/provenance, evidence, hypotheses, questions, assumptions, actions, critic
findings, budgets and consumption. `Registry.catalog()` serializes capability
descriptions, alternatives, availability, roles, workflows, and resource scopes.
`Registry.contract()` serializes bound input/output schemas and execution metadata.
These are intermediate Python dictionaries, not provider HTTP request bodies.

### Evidence and conversation serialization

* `engine.py:add_evidence` stores bounded records with excerpt, locator, source,
  scope, timestamp, trust, freshness and contradictions. `State.view()` and critic
  inputs present those records repeatedly. Reports retain the complete ledger.
  Profiling attributes excerpt/body content to a provider when the structured
  source is known; record identity, scope and provenance remain `evidence_ledger`.
* Grafana: `providers/grafana.py` creates bounded envelopes, `providers/evidence.py`
  sanitizes them; `grafana_worker.py` serializes the envelope over stdout.
  `investigation_harness/grafana.py:bind_grafana` uses a scoped child process and
  converts observations into harness records. These provider calls acquire data;
  they are not model calls. Only later adapter inputs count as model-bound context.
* GitHub: the harness registry defines repository/commit/issue/PR capabilities and
  their schemas. Fixtures serialize synthetic excerpts; trusted host bindings
  supply real results. There is no native live GitHub client or GitHub model
  request in this repository. `references/github.md` is guidance, not retrieved
  repository evidence. Forge's Jira action does not acquire GitHub data.
* Jira: `forge-app/src/index.js` calls Jira via Forge `asUser()`;
  `jira-evidence.js:collectJiraEvidence` constructs a redacted, bounded response
  with issue fields, optional comment/changelog pages, linked/candidate issues,
  locators, pagination and limitations. `response.js` validates the action result.
  Rovo consumes that object externally. A returned action object is not a visible
  Rovo model request. Harness Jira fixtures are synthetic records from fetch_issue.
* Conversation: the harness accepts at most 20 message strings in a request.
  `understand` sees that array; later inputs contain structured understanding
  and state, not an automatically appended transcript. Action history, critic
  findings, scope and evidence live in state. Portable-host conversation packing
  is hidden. The profiler additionally accepts raw assistant/user/tool history
  when a host explicitly supplies an authorized local request capture.
* Mixed workflows create child states with separate work-item scope and IDs.
  Profiling preserves safe internal investigation/work-item/parent/trace IDs;
  it does not merge evidence or alter customer/maintenance isolation.

## What is a model call?

`semantic.py:CallbackAdapter` delegates to a host callback. The callback may add
system prompts, tool declarations, history or provider-specific framing. Capturing
its input establishes a `harness_intermediate` boundary, not a full model request
or a confirmed provider submission. `Decision.input_tokens/output_tokens` are
optional adapter-reported usage; they are retained separately from estimates.

`FixtureAdapter` and benchmark `Meter` execute scripted choices.
`ConservativeCritic` performs deterministic checks. Harness `state.model_calls`
counts adapter/critic invocations for budgeting and includes these simulations;
the profiler does not equate that counter with observed model calls.
`ModelCritic` delegates through an adapter; only a host provider-boundary capture
can establish the complete request and submitted-call status.

An explicitly supplied `provider_request` capture with `submitted: true` may
count as an observed model call. `synthetic_provider_request`, scripted adapters,
deterministic critics and static source files contribute zero. Actual usage must
come from a response's usage object, or separately labelled adapter-reported
counts. A request alone cannot establish its usage or cache hits.

## Instrumentation scope

The new hooks cover every `Harness.model` path, including mixed work items and
conditional revisions. The benchmark and harness CLI expose explicit opt-in flags.
All persisted profiles contain only metrics, keyed hashes and allowlisted metadata.
Standalone provider-style JSON/JSONL can be profiled offline; the profiler itself
has no provider client or external transmission code.

MCP/Forge live return paths are intentionally not given production payload logging.
Their static instructions and sanitized synthetic response representations can be
profiled locally. Native host requests, live evidence distribution, production
latency, billing, cache discounts, and semantic investigation quality remain
unobserved. See [PAYLOAD_PROFILING.md](PAYLOAD_PROFILING.md) for capture formats,
measurement definitions, results and limitations.
