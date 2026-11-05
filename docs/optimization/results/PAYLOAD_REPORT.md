# PSI payload profiling report — Phases 1–4

5 November 2026. Offline synthetic captures from the existing A/B/C benchmark; no live provider requests, customer data, deployments, or production configuration changes.

## Findings

Current construction C produced **427,731 estimated input tokens** across **299 observable invocations** in 41 scenarios: 234 scripted adapter decisions and 65 deterministic critic checks. **Observed model calls: 0. Actual provider usage: unavailable.** All 41 cases passed in A, B and C. No capture limits were reached.

Tool/response schemas are the largest measured component, followed by routing/state context. These are the next subjects to inspect after review. The short synthetic evidence excerpts do not establish production evidence weights or justify evidence compaction.

## Component breakdown

Aggregate C inputs, not a single request. Character percentages partition the locally serialized inputs. Token estimates round per component/input; they need not add exactly to the whole-input estimate.

| Component | Estimated tokens | Percentage | Optimization opportunity |
|---|---:|---:|---|
| Core skill | 47,821 | 11.18% | Measure repeated excerpt placement; retain all safety constraints. |
| Provider guidance | 46,325 | 10.81% | Inspect presentation frequency and stable placement after review. |
| Tool schemas | 123,553 | 28.87% | Highest measured target: inspect repeated response and bound input/output contracts. |
| Evidence | 2,176 | 0.49% | Only short synthetic excerpts measured; collect safe production-like sizes before proposing changes. |
| Capability catalog | 30,013 | 7.01% | Inspect repeated schema/metadata presentation without changing discovery or selection. |
| History | 11,312 | 2.63% | Measure bounded action/critic history growth in longer authorized captures. |
| Ledger | 19,098 | 4.44% | Retain provenance, contradictions, scope, identity and limitations. |
| Other | 148,137 | 34.57% | Routing/state context is the second largest individual component; distinguish fixed instructions from dynamic state first. |

The grouped Other row includes routing context, critic context, reference guidance, user requests and serialization overhead. Full component detail remains in the JSON profile.

Top five individual components:

1. `tool_schemas`: 123,553 estimated tokens (28.871%).
2. `routing_context`: 104,571 estimated tokens (24.433%).
3. `core_skill`: 47,821 estimated tokens (11.177%).
4. `provider_guidance`: 46,325 estimated tokens (10.814%).
5. `other`: 33,373 estimated tokens (7.780%).

## Execution stages

| Repository stage | Observed inputs | Total estimate | Mean estimate | Maximum estimate | Duplicate indicator | Shared prefix | Observed model calls |
|---|---:|---:|---:|---:|---:|---:|---:|
| `understand` | 41 | 67,203 | 1,639.10 | 1,892 | 0.965% | 0.381% | 0 |
| `skill_selection` | 0 | 0 | 0.00 | 0 | 0.000% | unavailable | 0 |
| `choose` | 77 | 154,844 | 2,010.96 | 2,776 | 3.720% | 0.348% | 0 |
| `propose` | 43 | 70,948 | 1,649.95 | 1,910 | 9.688% | 0.424% | 0 |
| `evidence_acquisition` | 0 | 0 | 0.00 | 0 | 0.000% | unavailable | 0 |
| `investigation` | 0 | 0 | 0.00 | 0 | 0.000% | unavailable | 0 |
| `critic` | 65 | 29,547 | 454.57 | 752 | 5.589% | 1.046% | 0 |
| `report` | 41 | 69,826 | 1,703.07 | 2,225 | 2.328% | 0.411% | 0 |
| `revise` | 32 | 35,363 | 1,105.09 | 1,556 | 7.171% | 0.634% | 0 |

`understand` is request understanding. Skill selection is deterministic. `choose` is capability selection; `propose` plans evidence acquisition. Together they perform the investigation loop. Tool execution has no separate model input; its results appear in later stage payloads. `report` and `revise` generate the final response; `critic` is conditional and deterministic in this benchmark. Zero rows prevent double counting these conceptual phases. Per-stage component breakdowns are in each JSON stage entry.

## Heaviest scenarios and payloads

| Scenario | Total input estimate | Invocations | Largest input estimate |
|---|---:|---:|---:|
| `mixed` | 22,354 | 12 | 2,776 |
| `conflict` | 16,935 | 10 | 2,511 |
| `injection` | 16,088 | 10 | 2,392 |
| `jira` | 15,826 | 10 | 2,366 |
| `tool_fallback` | 15,797 | 10 | 2,419 |

These are fixed fixture scenario IDs, not claims about production traffic. `mixed` is the fixture involving explanation and release-causality questions; it should not be confused with the separate mixed-workflow isolation contract. The largest single input is `mixed` / `choose`, 2,776 estimated tokens. No scenario ranking was inferred from elapsed time.

## Repeated content and stable versus dynamic input

| Identical block source | Normalized characters | Occurrences | Repeated characters after first |
|---|---:|---:|---:|
| Core skill selected headings | 1,971 | 97 | 189,216 |
| Provider trust/privacy and retrieval guidance | 1,697 | 109 | 183,276 |
| UNDERSTANDING response contract | 3,383 | 41 | 135,320 |
| Fixed routing registry | 2,825 | 41 | 113,000 |
| Bound search_logs input/output contract | 3,656 | 27 | 95,056 |

Across the corpus, repeated core/reference/provider guidance accounts for 376,994 normalized characters (~94,249 tokens), and repeated evidence/ledger blocks for 37,008 characters (~9,252 tokens). These are recurrence indicators across independent scenarios, not removable tokens or production savings.

The within-input duplicate indicator is 4.464% (maximum of normalized-line and identical-block ratios per input). The bounded near-duplicate scan found 145 similar section pairs in 2,403 comparisons; the JSON retains the first 50 pairs. Similarity does not imply equivalent evidence or instructions.

Literal comparable prefixes total 7,664 characters across C inputs (0.448%). Dynamic suffixes total 1,702,807 characters. Each stage/boundary group shares only 19–28 initial characters. Variable request/goal/state content occurs before static method/schema sections in the local dictionaries. Repetition later in a request therefore does not imply a long initial prefix. Provider wrapping could change these results; no reordering was performed.

No actual cache-read, cache-write, hit-rate, or cache discount was observed. Shared prefixes alone establish none of those facts. Provider-specific usage parsing is covered by tests and documented separately.

## A/B/C and standalone source measurements

| Reconstruction | Local compact input estimate | Scripted decisions | Deterministic critic checks | Checks passed | Observed model calls |
|---|---:|---:|---:|---:|---:|
| A | 507,576 | 234 | 65 | 41/41 | 0 |
| B | 484,507 | 234 | 65 | 41/41 | 0 |
| C | 427,731 | 234 | 65 | 41/41 | 0 |

A uses the existing baseline reconstruction; B uses the existing legacy loading/catalog comparison with the compact core; C uses current conditional construction. These are reconstructed synthetic variants, not production deployments. Differences describe input presentation only. The historical benchmark uses default JSON spaces, yielding C = 454,278 estimated input tokens; the profiler uses compact JSON, yielding C = 427,731. Both apply ceil(characters/4). These distinct serializations must not be reported as an additional optimization.

The standalone public-source inventory counts the full canonical skill at 1,496 estimated tokens and generated Forge agent prompt at 2,025. These are static files, not additional observed execution inputs. The separate three-case synthetic provider-shape profile exercises labelled sections, OpenAI-style input/tools, Anthropic-style tool results, mixed history and Unicode; all actual usage fields remain unavailable.

## Estimates, usage and classification availability

| Measurement | Availability |
|---|---|
| Character estimates, components, stages, duplicates, literal prefixes | Available for all 299 C inputs; no skipped inputs |
| Model-specific tokenizer | Not enabled in benchmark; optional installed/cached tiktoken path tested with missing-dependency and cache-miss fallbacks |
| Complete actual provider input serialization | Unavailable for Codex, Claude, Rovo and host callbacks |
| Actual input/output and cache usage | Unavailable; 0 provider-response or adapter-reported usage records in the benchmark |
| Unclassified character percentage | 0.000% for structured C fixtures; confidence/method details retained per payload |
| Investigation semantic accuracy, live coverage, latency and billing savings | Not measured |

Zero unknown content in this fixed structured corpus demonstrates field attribution, not semantic correctness or complete classification of arbitrary customer payloads. The standalone fixtures and tests exercise regex fallback, unknown labels and confidence reporting. Known Other/serialization content is counted separately from unclassified text.

## Recommendations for review

1. Review schema presentation first: tool/response contracts account for 28.871% of C input characters. The UNDERSTANDING contract alone repeats 41 times. Determine which fields the actual host already supplies before considering presentation changes; preserve validation and readiness contracts.
2. Inspect the 24.433% routing/state share. Separate stable routing rules from dynamic understanding, scope, provenance and work-item identity. Review the necessity of repetition with real host requests before changing any field.
3. Measure cache eligibility at a real provider boundary. Core/provider guidance repeats substantially while literal prefixes are short. Review stable placement experiments only after provider framing and real usage fields are available; retain all safety instructions.
4. Collect authorized metadata-only sizes for longer Jira histories, repository excerpts, Grafana pages and multi-turn cases. Tiny synthetic evidence here cannot support evidence-compaction priorities.
5. Add human-reviewed semantic quality evaluation before claiming quality-preserving reductions. Scripted routing/security passes alone cannot establish semantic equivalence.

No evidence compaction, model tiering, schema reduction, prompt reduction or prefix reordering was implemented. These are review targets for the next phase, not approved optimizations.

## Validation

| Check | Result |
|---|---|
| New profiler tests | 28 passed |
| Full Python suite | 133 passed using the existing .venv-mcp runtime outside the sandbox |
| Existing PSI evaluator | 36/36 in every dimension: routing, skill selection, clarification, tool choice, readiness, evidence support, security, efficiency |
| A/B/C benchmarks with capture | 41/41 each; 35 synthetic tool calls; zero unnecessary fixture tool calls |
| Skill validation / generated artifact consistency | PASS |
| Forge trace, response and Jira evidence Node files | 3/3 passed |
| Local package validation | PASS; generated a local ignored archive only |

The sandboxed full suite initially passed 129 tests with three MCP stdio initialization timeouts. A targeted unsandboxed rerun passed all seven MCP tests, and the complete unsandboxed suite passed all 133 tests. No MCP source or security controls were modified to obtain that result.

Tests cover JSON/JSONL parsing, labels and fallback, unknown classification, empty inputs, provider messages/mixed blocks/tool schemas, Unicode, exact/near duplication, prefixes/group isolation, usage/cache semantics, metadata-only redaction, file permissions, opt-in behavior, capture limits, missing tokenizer/cache assets, immutable adapter inputs, observer failure isolation, real callback usage labelling, and benchmark repeat handling. Existing regression tests cover provenance, customer/maintenance isolation, injection resistance, unknown root cause and routing/tool selection.

## Artifacts and reproduction

* [payload-profile-A.json](payload-profile-A.json), [B](payload-profile-B.json), [C](payload-profile-C.json): full metadata-only corpus profiles, including each input and component/stage/scenario aggregates.
* [public-source-inventory.json](public-source-inventory.json): standalone public instruction/reference sizes; zero model calls.
* [synthetic-provider-shapes.json](synthetic-provider-shapes.json): three sanitized provider-format fixtures.
* [validation.json](validation.json): validation summary without raw subprocess logs.

Run the benchmark command from [PAYLOAD_PROFILING.md](../PAYLOAD_PROFILING.md) once for each label, using fresh output paths. HMAC fingerprints and internal IDs change across runs by design; character metrics can also vary slightly with dynamic fixture timestamps/IDs. Public source inventory uses labelled source_artifact captures of SKILL.md, the generated Forge prompt and references/*.md. Nothing in the existing historical result files was rewritten.

## Known limitations

Local intermediate payloads exclude host system prompts, complete tool registries, history packing, transport framing, non-text token costs, hidden retries and model-specific billing. Repetition uses deterministic surface similarity and size bounds, not semantic equivalence. Exact/near analyses can miss cross-component copies and paraphrases. All benchmark grouping is within one variant/stage/boundary/provider/model and includes independent synthetic scenarios. No observed cache hits or production distributions exist. Profiling adds CPU/memory overhead and can influence tight wall-clock budgets when enabled; it does not justify latency claims. Disabled profiling adds no capture or tokenizer work. Raw source content is held only in bounded memory and is never included in profiler outputs.
