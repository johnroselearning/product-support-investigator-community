# Optimization baseline

Captured 2026-11-05 from the **pre-existing dirty working tree**, not Git HEAD.
No existing edits were reset. `baseline-inventory.json` records SHA-256 digests,
exact line/byte/character counts, and estimates for every audited Markdown entry,
reference, adapter, generated skill, documentation file, routing configuration,
and unchanged optional Python helper resource.

## Counting and loading assumptions

`tiktoken` and `transformers` are unavailable in both system Python and the existing
`.venv-mcp` environment. No tokenizer dependency was installed. All token counts
here use **ceil(Unicode characters / 4)**; these are estimates, not model tokenization
or provider usage. Lines, bytes, characters and hashes are exact. Frontmatter is
included. Copies are counted individually and must not be interpreted as all
loaded together by a portable host.

The root SKILL.md has **328 lines, 20,606 bytes, 20,560 characters and ~5,140 tokens**.
Codex/Claude normally discover metadata, then load the core on activation and
references only on demand; actual host caching is not observable here. The old
harness loads three core sections plus provider trust guidance, repeatedly included
in choose/report payloads. The Forge prompt generator unconditionally concatenates
the core and **all bundled Markdown references plus COMMUNITY.md**; the separate
Rovo skill is also registered, so duplicate platform context is possible.

## Audit findings

- Symptom validation, layered decomposition, evidence acquisition, sparse evidence,
  workflow steps, fallback and final quality gate repeat the same instructions.
- Injection, credentials, read-only permissions and provider failure boundaries
  recur in core, provider references, GitHub/workflow guides and Forge instructions.
  Essential safety belongs in core; specialized details remain conditional.
- A 28-section output menu consumes core space even for a one-check investigation.
- General questions, customer investigations and PSI maintenance already have
  structured routing and deterministic isolation. Preserve the existing contracts;
  expose the requested four categories without adding another model call.
- Root/generated portable copies are intentional packaging artifacts. Independent
  Forge skill prose duplicates methodology and can drift from the canonical core.
- Every Forge issue investigation reads up to 100 comments and 100 changelog
  entries, then searches 10 recent project issues regardless of diagnostic value.
  Fields include full status/user/version objects and rich-text bodies.
- GitHub/Grafana integrations already use bounded contracts and runtime checks.
  The harness still presents all 11 conceptual capabilities on every choose step,
  even when the validated work item needs only one. Known UIDs do not need repeated
  datasource discovery; no connected service should be called merely for presence.
- Deduplication, pagination, response-size limits, scoped access, redaction and
  conditional critics already exist. Preserve these checks and full bounded
  evidence; optimize what is sent to the model without weakening the ledger.
- No live integrations, model billing data or production latency are available.
  Baseline benchmark A is a scripted offline capture, not semantic quality proof.

## Tests before implementation

- `python3 scripts/validate_skill.py`: PASS, generated files current, 16 legacy cases.
- `python3 -m unittest discover -s tests -p 'test_*.py'`: 89 tests, one import error
  because system Python lacks the declared MCP SDK. Use the existing environment.
- `.venv-mcp/bin/python -m unittest discover -s tests -p 'test_*.py'`: 95 tests,
  92 passed and 3 subprocess protocol initialization timeouts inside sandbox isolation.
  Later runs outside isolation pass; this is recorded separately in BENCHMARK.md.
- `python3 -m investigation_harness.evaluate --split all`: all **36/36** cases pass
  all eight dimensions (fixture simulation).
- `node --test forge-app/src/trace.test.mjs forge-app/src/response.test.mjs`: PASS,
  two test files. Installed Node executes these as file-level tests.

## File inventory

Token estimates use the same method throughout. See JSON for characters and hashes.

| File | Lines | Bytes | Estimated tokens |
| --- | ---: | ---: | ---: |
| `CHANGELOG.md` | 34 | 1459 | ~365 |
| `COMMUNITY.md` | 37 | 1807 | ~452 |
| `CONTRIBUTING.md` | 45 | 2028 | ~507 |
| `DATA_HANDLING.md` | 77 | 4447 | ~1112 |
| `MARKETPLACE.md` | 148 | 7484 | ~1870 |
| `PRIVACY.md` | 58 | 3260 | ~815 |
| `README.md` | 561 | 18990 | ~4686 |
| `SECURITY.md` | 29 | 1702 | ~425 |
| `SKILL.md` | 328 | 20606 | ~5140 |
| `TERMS.md` | 53 | 3409 | ~852 |
| `atlassian/AGENT.md` | 3 | 360 | ~90 |
| `atlassian/compliance-gate.txt` | 28 | 4839 | ~1209 |
| `atlassian/prompts/investigator.md` | 5 | 469 | ~118 |
| `atlassian/rovo-adapter.txt` | 11 | 2053 | ~514 |
| `claude/CLAUDE.md` | 5 | 409 | ~103 |
| `codex/SKILL.md` | 10 | 587 | ~147 |
| `docs/CONNECTORS.md` | 9 | 1361 | ~341 |
| `docs/EXTENDING.md` | 7 | 980 | ~245 |
| `docs/GITHUB.md` | 20 | 3715 | ~929 |
| `docs/GRAFANA.md` | 80 | 4804 | ~1198 |
| `docs/HARNESS_EVALUATION.md` | 62 | 5240 | ~1310 |
| `docs/INVESTIGATION_HARNESS.md` | 186 | 17904 | ~4470 |
| `docs/INVESTIGATION_METHOD.md` | 105 | 4843 | ~1211 |
| `docs/MCP_SKILLS.md` | 83 | 7722 | ~1931 |
| `docs/OBSERVABILITY.md` | 27 | 1622 | ~406 |
| `docs/OUTPUT_FORMAT.md` | 36 | 1005 | ~252 |
| `docs/PUBLISHING.md` | 82 | 6908 | ~1727 |
| `docs/WORKFLOWS.md` | 164 | 9252 | ~2313 |
| `docs/execution-tracing-validation.md` | 97 | 5694 | ~1423 |
| `docs/execution-tracing.md` | 210 | 11969 | ~2993 |
| `forge-app/prompts/investigator.md` | 1062 | 63700 | ~15910 |
| `forge-app/skills/product-support-investigation/SKILL.md` | 78 | 5979 | ~1495 |
| `investigation_harness/routing.json` | 25 | 2934 | ~734 |
| `providers/__init__.py` | 1 | 76 | ~19 |
| `providers/evidence.py` | 80 | 3391 | ~848 |
| `providers/grafana.py` | 242 | 13337 | ~3335 |
| `references/api-error-investigation.md` | 124 | 5740 | ~1435 |
| `references/authentication-investigation.md` | 68 | 1749 | ~438 |
| `references/escalation-framework.md` | 49 | 1573 | ~394 |
| `references/evidence-providers.md` | 42 | 5261 | ~1315 |
| `references/github.md` | 24 | 3798 | ~950 |
| `references/grafana.md` | 44 | 4229 | ~1058 |
| `references/investigation-methodology.md` | 128 | 5328 | ~1332 |
| `references/webhook-investigation.md` | 70 | 1755 | ~439 |
| `references/workflows.md` | 80 | 4764 | ~1190 |
| `scripts/grafana_evidence.py` | 20 | 540 | ~135 |
| `skills/atlassian-forge/SKILL.md` | 84 | 6903 | ~1725 |
| `skills/product-support-investigator/COMMUNITY.md` | 37 | 1807 | ~452 |
| `skills/product-support-investigator/SKILL.md` | 328 | 20606 | ~5140 |
| `skills/product-support-investigator/providers/__init__.py` | 1 | 76 | ~19 |
| `skills/product-support-investigator/providers/evidence.py` | 80 | 3391 | ~848 |
| `skills/product-support-investigator/providers/grafana.py` | 242 | 13337 | ~3335 |
| `skills/product-support-investigator/references/api-error-investigation.md` | 124 | 5740 | ~1435 |
| `skills/product-support-investigator/references/authentication-investigation.md` | 68 | 1749 | ~438 |
| `skills/product-support-investigator/references/escalation-framework.md` | 49 | 1573 | ~394 |
| `skills/product-support-investigator/references/evidence-providers.md` | 42 | 5261 | ~1315 |
| `skills/product-support-investigator/references/github.md` | 24 | 3798 | ~950 |
| `skills/product-support-investigator/references/grafana.md` | 44 | 4229 | ~1058 |
| `skills/product-support-investigator/references/investigation-methodology.md` | 128 | 5328 | ~1332 |
| `skills/product-support-investigator/references/webhook-investigation.md` | 70 | 1755 | ~439 |
| `skills/product-support-investigator/references/workflows.md` | 80 | 4764 | ~1190 |
| `skills/product-support-investigator/scripts/grafana_evidence.py` | 20 | 540 | ~135 |

Inventory total across 62 physical files: 6,158 lines, 361,939 bytes, ~90,386 estimated tokens. This includes generated duplicates and is not a per-request loading cost.
