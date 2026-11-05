# PSI context and retrieval architecture

The canonical skill is a compact entrypoint. It retains activation, request
classification, diagnosis, tool selection, trust/permissions, evidence and output
requirements. The 28-section report menu and detailed procedures are conditional
references. This follows the [Agent Skills specification](https://agentskills.io/specification):
frontmatter for discovery, core instructions on activation, supporting resources
only when needed. All core references are direct; reference files do not require
another reference to be loaded.

## Request and execution boundaries

| Category | Existing decision | Execution |
| --- | --- | --- |
| QUESTION | general_question | Direct answer; no evidence tool discovery or investigation |
| INVESTIGATION | customer_investigation | Supplied evidence or useful scoped reads; missing fields do not change intent |
| MAINTENANCE | psi_maintenance | PSI code/telemetry; sanitized review-only handover |
| UNCLEAR | needs_clarification | One essential clarification; no executable work item |
| Both investigation and maintenance | mixed | Separate work items, ledgers, resource mappings and allowed actions |

`request_categories` maps the existing structured host understanding deterministically.
It does not guess intent from keywords and adds no classifier call. The existing
single `understand` semantic stage and JSON contracts remain intact. Questions
cannot open a tool loop even if a planner requests one. Partial investigations
continue with available evidence; unresolved tenant/authorization boundaries still
fail closed.

`context.py` selects trusted local sections from validated work-item fields.
Questions/essential clarifications load no investigation context. Supplied-only
analysis skips the provider contract. External acquisition receives trust and
retrieval rules. Maintenance additionally receives workflow isolation/handover
rules. Each selected file is read once per work item and identified by SHA-256.
Relevant method excerpts are still sent on each stateless choose/report call;
this change does not claim provider caching or remove instructions from later calls.

The portable host selects symptom playbooks (HTTP, auth, webhook, complex
methodology) from the core. The harness deliberately retains its bounded excerpt
model; it does not automatically interpret free text to select those playbooks.
Their end-to-end selection needs real-host evaluation.

## Conditional acquisition

The harness presents only declared evidence capabilities and their existing
acquisition alternatives. Unavailable capabilities remain identifiable for honest
fallback. This reduces catalog context; it does not grant access or skip readiness.
Every actual call still checks schema, relevance, capability availability,
permissions, user/tenant/workflow/resource intersections, scope provenance, query
bounds, result limits, time/cost budgets and destination policy. Unknown customer
resources never fall back to a known PSI repository.

Jira, GitHub and Grafana remain optional. Select them for a diagnostic question,
known authorized scope and expected evidence value, never because connected.
The native portable host's calls are not intercepted by the optional harness.

The existing Forge Jira action defaults to issue context. Optional `sections`
selects comments, changelog and/or related candidates. `limit` defaults to 20,
maximum 100; related candidates stay capped at 10. `startAt` and returned
`nextStartAt` support comments/history pagination. Input validation precedes reads;
GET routes, `asUser()` and caller permissions are unchanged. Related search page
tokens are reported but later candidate pages require authorized Jira access outside
this action. The first issue retrieval is repeated for a subsequent action page;
there is no new cross-request cache or continuity claim.

Responses redact common secrets and email addresses before bounding large fields,
retain locators/timestamps/exact relevant errors, deduplicate identical facts and
preserve changed/contradictory statements. Omitted sections have unknown totals,
skipped/coverage markers, and cannot support absence claims. Large field excerpts
are explicitly clipped with source locators. Full originals stay at authorized
Jira sources, not a new raw-log store. More pages can cost more calls than the old
single 100-record page. Relevance, rather than indiscriminate omission, must guide
what the host requests.

## Evidence and security

The harness's full bounded ledger, evidence IDs, source locators, provenance,
contradictions, redaction, response contracts, deterministic report support checks,
retry/no-progress limits and evaluation contracts remain. Tool text cannot choose
references, executable commands, permissions or scope. Provider failures never
become customer application causation. Conditional critics remain conditional;
the default critic is deterministic and no unconditional LLM review was added.

Core safety applies even if references cannot load. The Atlassian compliance gate
is byte-identical and remains first in the generated agent prompt. Portable
instructions are guidance, not an access-control mechanism. Redaction is best
effort and cannot recognize every secret/PII format, including split rich-text
fragments; review before sharing remains necessary.

## Platform compatibility

| Surface | Packaging and verified checks | Remaining boundary |
| --- | --- | --- |
| Codex | Portable generated skill, direct relative references, YAML validation, isolated bundle closure, real MCP SDK resource round trips | Native activation/reference choice and host caching not exercised |
| Claude | Same portable directory plus existing repository adapter; no new runtime dependency for the skill | Claude Desktop/Code installation and activation not exercised |
| Forge/Rovo | Generated canonical core under the existing skill key/source directory, Markdown references bundled there, short agent prompt, existing Jira action | No live site/Forge deployment or skill-selection measurement; no Python helpers, GitHub or Grafana action |

Atlassian's current [Rovo skill documentation](https://developer.atlassian.com/platform/forge/manifest-reference/modules/rovo-skill/)
describes bundled supporting files, runtime skill selection and Preview limitations
including unsupported executable skill sources. We package Markdown only for Rovo;
local Python helpers remain in the portable bundle. Explicit invocation/caching
semantics are not assumed to match Codex/Claude. The short agent prompt retains an
essential fallback if skill loading fails and preserves exact returned support
references in success/failure responses.

The [Rovo action schema](https://developer.atlassian.com/platform/forge/manifest-reference/modules/rovo-action/)
supports the optional string/integer inputs used here. Existing production app ID,
runtime, module/action/function keys, required inputs, scopes and GET execution
identity are preserved. Only optional action inputs were added to the two manifest
templates. There is no active `forge-app/manifest.yml` in this checkout; no
installation configuration, permission, site or deployment was changed. Forge lint
and live packaging validation remain unverified until an authorized environment
with an active manifest is available. No publishing/deployment was performed.

MCP native discovery still returns metadata/file manifests. Prefer `resources/read`
for individual files. Legacy clients can use `get_skill(include_files=false)` then
selective reads. The original true default/full-bundle contract is retained; those
calls still return all files and do not gain progressive-loading savings.

## Files changed by this optimization

The checkout was dirty before work. This list describes this task's edits, not all
files shown by `git diff`.

- Canonical instructions: `SKILL.md`, `references/reporting.md`,
  `references/investigation-methodology.md`, `references/evidence-providers.md`,
  `references/github.md`, `references/grafana.md`.
- Harness: `investigation_harness/context.py`, `engine.py`, `registry.py`,
  `state.py`, `workflows.py` (other harness files retain pre-existing user edits).
- Distribution: `skill_adapter/bundle.py`, `skill_adapter/server.py`,
  `scripts/sync_skill.py`, `scripts/validate_skill.py`, `atlassian/rovo-adapter.txt`.
- Forge: `forge-app/src/index.js`, `jira-evidence.js`, `jira-evidence.test.mjs`,
  `forge-app/manifest.example.yml`, `forge-app/manifest.yml.example`, `forge-app/README.md`.
- Generated artifacts: changed portable core/reference copies under
  `skills/product-support-investigator/`; Forge core plus Markdown references and
  COMMUNITY under `forge-app/skills/product-support-investigation/`;
  `forge-app/prompts/investigator.md`, `forge-app/src/trace-contract.json`,
  `docs/OUTPUT_FORMAT.md`, local upload archive in `dist/`.
- Validation: `tests/test_optimization.py`, `tests/test_mcp_skills.py`,
  `.github/workflows/skill-validation.yml`, `scripts/benchmark_optimization.py`,
  `scripts/benchmark_jira.mjs`.
- Documentation/evidence: `docs/MCP_SKILLS.md`, this directory's baseline,
  architecture, benchmark report, JSON inventories/captures and two immutable
  pre-change instruction inputs under `baseline/`. Baseline copies are not
  published in the portable bundle or loaded during normal investigation.

## Next validation

Run real-host, synthetic-data trials for ordinary questions, diagnosis, maintenance,
follow-ups, injection and incomplete evidence in Codex/Claude/Rovo. Collect provider
usage, actual reference reads, tool decisions and wall latency with permission.
Review evidence entailment independently; structural fixture checks cannot establish
semantic accuracy. Validate the template inputs and skill-reference selection with
the intended Forge CLI/site before any separately authorized release.
