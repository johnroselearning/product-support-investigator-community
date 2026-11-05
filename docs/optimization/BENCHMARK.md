# Optimization benchmark

All token figures below are **estimates**, not tokenizer/provider usage. They use
ceil(Unicode characters / 4), per serialized message. No tokenizer is available in
the existing environments; none was added. No production/customer calls or paid
model evaluations were performed.

## Core and packaging size

| Artifact | A: original | C: optimized | Estimated reduction |
| --- | ---: | ---: | ---: |
| Canonical SKILL.md | ~5,140 tokens / 328 lines | ~1,496 tokens / 64 lines | 70.89% |
| Always-loaded Forge agent prompt | ~15,910 tokens | ~2,025 tokens | 87.27% |

The Rovo prompt comparison excludes separately activated skill content. Rovo may
load the core and selected references in addition to the short prompt; total live
context is unmeasured. Smaller prompt files alone are not proof of billing savings.

## A/B/C harness comparison

A uses the original core/provider sections and legacy unfiltered capability catalog.
B uses the compact core with legacy loading/catalog behavior. C adds conditional
provider/maintenance context and filters the catalog to declared evidence needs and
fallback paths. All use the same synthetic tools, scripted semantic decisions,
limits, deterministic guards and graders. No extra classifier/reviewer LLM is used.

A's first 39 cases were captured before implementation. The replay implementation
with archived original core/provider inputs reproduces their **exact aggregate
input/output estimates and tool counts** (510,770 / 14,680 / 33), then adds the same
two explicit HTTP 500/missing-ID cases used by B/C. Original input hashes are checked
against `baseline-inventory.json`. This is a replay of the audited execution path,
not three live deployed implementations.

Each stage has **41 cases**, including the existing 36-case evaluation corpus.
Latency uses three local fixture runs per case. Scripted adapters do not make LLM
calls; counters include the existing deterministic critic for contract compatibility.

| Metric | A | B | C |
| --- | ---: | ---: | ---: |
| Estimated input tokens | 539,652 | 516,582 | 454,278 |
| Estimated output tokens | 15,485 | 15,485 | 15,485 |
| Estimated total tokens | 555,137 | 532,067 | 469,763 |
| Synthetic tool calls | 35 | 35 | 35 |
| Calls above fixture allowance (proxy) | 0 | 0 | 0 |
| Cases passing all applicable structural checks | 41 | 41 | 41 |
| Cases with context references loaded | 32 | 32 | 38 |
| Unique file loads across work items | 64 | 64 | 68 |
| Reference presentations in model payloads | 194 | 194 | 209 |
| Sum of per-case median local execution, ms | 1162.6 | 1141.8 | 971.6 |

Estimated input context falls **15.82%** A→C;
estimated total tokens fall **15.38%**.
Output estimates and tool counts are unchanged, because decisions are scripted.
The original harness was already bounded: no tool-call reduction is claimed for it.

C presents more reference context in some direct reads/maintenance work items to
preserve relevant privacy and scope guidance. Thus loading frequency is not lower
on every dimension; smaller sections/catalogs produce the measured context change.
No provider cache behavior is assumed. The local timing totals are sums of medians,
not end-to-end provider latency; they are sensitive to scheduling/logging and cannot
establish production speedup.

“Calls above fixture allowance” is only an efficiency proxy; zero does not prove
that every semantically unnecessary call was detected. Tool-selection and evidence
checks are structural fixture checks, not measured language-model accuracy.

## Coverage and evidence quality

| Requested scenario | Cases |
| --- | --- |
| Ordinary questions | explain, rewrite |
| HTTP 500 | http500, jira |
| Missing correlation ID | missing_correlation, checkout, sparse |
| Grafana-only | checkout, metrics |
| GitHub-only | github_only, repository |
| Combined Grafana/GitHub | mixed, conflict |
| Unavailable tools | missing_tool, unavailable, failure, tool_fallback |
| PSI maintenance | maintenance; existing workflow unit tests cover mixed/drafts/scope |
| Prompt injection | injection; cross_tenant and sensitive exercise other boundaries |
| Insufficient evidence | empty, partial, stale, sparse, conflict |
| Follow-up | multiturn; existing workflow and Forge support-reference tests |
| Essential ambiguity | unclear, environment, tenant |

All **36/36 original cases** still pass routing, skill selection, clarification,
tool choice, readiness, evidence support, security and efficiency. All **41/41**
benchmark cases pass their applicable checks. Evidence checks validate retained IDs,
source-statement support, scope and conservative Unknown root cause, not semantic
entailment. No structural regressions were observed; model accuracy regressions
remain **unmeasured**. Hypothesis/report validation, sensitive-data handling,
customer/maintenance isolation and injection regressions remain active.

## Jira acquisition experiment

`benchmark-jira.json` is a separate synthetic reconstruction of the audited old
four-GET acquisition path versus the current pure collector. It is not execution
of an old deployment. Full-size payload shapes differ, so compare coverage too.

| Profile | Synthetic calls | Response token estimate | Comments / history returned |
| --- | ---: | ---: | ---: |
| Legacy reconstruction | 4 | ~6,443 | 100 / 100 |
| C issue only | 1 | ~277 | 0 / 0 |
| C explicit first pages | 4 | ~1,844 | 20 / 20 |
| C original page limits | 4 | ~7,586 | 100 / 100 |

Default acquisition uses one GET instead of the audited four-call default. Asking
for all original-size pages still makes four calls and can produce a **larger**
payload because provenance/coverage metadata is retained. Requesting less evidence
saves context only when that evidence is irrelevant or can be fetched later.
Skipped/partial evidence never supports absence; subsequent pages may increase
call counts. No semantic completeness or production latency gain is claimed here.

## Validation and reproducibility

- `python3 scripts/validate_skill.py`: PASS; valid YAML and synchronized artifacts.
- `.venv-mcp/bin/python -m unittest discover -s tests -p 'test_*.py'`: PASS, **105 tests**.
  This includes real modern/legacy MCP SDK subprocess round trips.
- `python3 -m investigation_harness.evaluate --split all`: PASS, 36/36 in all dimensions.
- `node --test forge-app/src/trace.test.mjs forge-app/src/response.test.mjs forge-app/src/jira-evidence.test.mjs`:
  PASS, three test files, including optional retrieval, pagination, bounds, redaction,
  deduplication, changed statements, evidence locators and existing trace contracts.
- Skill Creator `quick_validate.py`: PASS for portable and Forge skill directories.
- `python3 scripts/package_plugin.py`: PASS, local archive only.

System Python lacks the declared MCP SDK. The existing `.venv-mcp` environment
contains it. Baseline subprocess tests timed out inside sandbox process isolation;
all seven MCP tests pass outside that isolation. No dependency was installed.
No active Forge manifest/site was present; Forge lint/deploy and live Codex/Claude/
Rovo activation are unverified. See ARCHITECTURE.md for platform-specific limits.

Reproduce fixture estimates from this checkout:

```bash
python3 scripts/benchmark_optimization.py --label A --output /tmp/psi-A.json
python3 scripts/benchmark_optimization.py --label B --output /tmp/psi-B.json
python3 scripts/benchmark_optimization.py --label C --output /tmp/psi-C.json
node scripts/benchmark_jira.mjs /tmp/psi-jira.json
```

The JSON captures contain per-case estimates, tool counts, reference presentation
frequency, checks, termination and local median latency. Provider usage is explicitly
unavailable. Archived baseline text is inert test input and excluded from skill
packaging. Future changes to execution/fixture semantics require a new benchmark
version; do not relabel them as this historical baseline.

## Remaining risks and next steps

Validate real-host playbook selection and source entailment with synthetic data and
provider usage instrumentation before claiming model accuracy, billing or production
latency gains. Confirm Rovo Preview loading and optional action inputs using the
intended Forge CLI/site. Legacy full-bundle consumers still pay for the full bundle.
Declared evidence needs may miss a newly relevant capability until host replanning;
the runtime continues to fail closed. Best-effort redaction cannot recognize every
secret, and clipped records require authorized follow-up retrieval. No publication,
deployment or installation change was made.
