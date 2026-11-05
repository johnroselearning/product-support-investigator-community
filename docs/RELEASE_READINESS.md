# PSI release readiness for controlled development testing

Reviewed 5 November 2026 (Asia/Kolkata). **Documentation and review only; no deployment, installation, publication, commit, or investigation-behavior change is authorized by this document.**

## Decision

The working tree is suitable for continued local synthetic testing. Hold a new Forge development deployment until the manifest drift, test-data boundary, monitoring acceptance, and recoverable source checkpoint below have been reviewed. Production promotion is outside this review.

The causal-report design below is a proposal for approval, not an implemented feature. Approving that design and approving a later development deployment are separate decisions.

## Reviewed state and preservation

- Branch: `perf/skill-context-optimization`.
- HEAD: `1578d747260712761f819804d2ba89faa550c004` (`feat: PSI support reference implemented`).
- At the initial snapshot: 46 modified tracked files, 94 individual untracked files, and no staged changes. Directory entries in `git status --short` abbreviate the untracked files.
- The ignored `forge-app/manifest.yml` exists and was inspected separately. It is not covered by ordinary Git status or skill synchronization.
- Existing file contents were hashed before review, including the local manifest. They must remain unchanged by this documentation work. Git index entries changed independently during the review; this review does not stage, unstage, reset, or restore them.
- This review adds only `docs/RELEASE_READINESS.md`, `docs/DEVELOPMENT_TEST_PLAN.md`, and `docs/KNOWN_LIMITATIONS.md`. No synchronization write, dependency installation, package publication, or production configuration edit was performed.

The appendix inventories the pre-existing changed files. A branch name or HEAD alone cannot reproduce this dirty working tree; preserve the untracked sources and ignored manifest before any later deployment.

## Why final reports force Unknown

The behavior originated in commit `94b0d68` (`feat: Implemented the v1 harness`), rather than in the current optimization changes. `git blame investigation_harness/reports.py` attributes the whole current finalizer to that commit. The code comment and [harness documentation](INVESTIGATION_HARNESS.md) give the rationale: v1 has no machine-verifiable causal-proof or attribution contract. A critic's approval is neither evidence nor permission.

There are three independent barriers:

1. `investigation_harness/contracts.py::REPORT` accepts only `answer`, `claims`, `unknowns`, `hypotheses`, and `adequate`. A model-supplied `root_cause` field fails the strict additional-properties check.
2. `reports.py::check_report` requires every claim to cite existing ledger IDs. An observed claim must be a nonempty literal excerpt from at least one cited record. Every `causal`, `blame`, `deployed`, and `absence` claim is rejected as `unverified_strong_claim`, even if its references exist. Inferences containing the guarded terms are rejected as `strong_inference`. Unsupported hypothesis references invalidate the hypothesis collection.
3. `reports.py::finalize_report` removes rejected claims, replaces actual investigation/direct-retrieval answer prose with a conservative statement so summaries cannot bypass the claim checks, retains coverage gaps, and unconditionally sets `root_cause = "Unknown"` when `state.selected_skill is not None`. Other routes receive `not_applicable`. Hypothetical answer prose is prefixed instead of replaced, but an investigation's root field still becomes Unknown.

`needs_critic` triggers on consequential claims, gaps, stale/conflicting evidence, partial/empty results, and conflicting scope. `engine.py::report` permits bounded review/revision and still runs deterministic finalization afterward. The default `ConservativeCritic` explicitly does not perform independent semantic verification.

This is a conservative abstention policy, not a determination that every collected dataset lacks a cause. The real-model evaluation's three determinable cases necessarily expose incorrect abstention in the finalized root field. Raw model attempts are saved separately and cannot substitute for accepted final reports. The older fixture grader also treats only Unknown/not_applicable as security-passing; it must be revised carefully if a new report contract is approved.

### Present protections and remaining limits

| Condition | Current treatment |
| --- | --- |
| Missing/unknown citation ID | Drop the claim: `unsupported_reference` |
| Observation absent from cited excerpts | Drop it: `unsupported_observation` |
| Causal/blame/deployment/absence claim | Drop it regardless of citation existence |
| Guarded strong language in an inference | Drop it: `strong_inference` |
| Hypothesis missing support or containing unknown references | Remove hypotheses; record `unsupported_hypothesis` |
| Empty/partial read, stale evidence, declared contradiction | Retain the ledger and add explicit gaps; `adequate` becomes false |
| Invalid model schema or exhausted execution budget | Engine returns a limited report through the same finalizer |
| Critic approves a statement | No permission or causal-proof grant; final checks still apply |

Reference existence, literal quoting, and a short keyword guard do **not** establish entailment. A quoted Jira assertion can remain an observed source statement without becoming an established cause. Synonyms can evade the inference regex, and hypothesis statement meaning is not verified. These are limitations to test, not grounds for deleting the existing guard. Source text remains untrusted. An Unknown root field alone does not certify that every other sentence is safe or accurate.

## Proposed causal-report design — approval required

Supported conclusions can be retained safely only with a new, explicit acceptance boundary. Simply retaining the model's root string, relaxing the regex, or trusting a critic would remove the original protection without replacing it.

### Versioned candidate and acceptance contract

1. Introduce an opt-in report contract v2 in a later change. Keep v1 and its Unknown behavior as the default. A trusted host configuration enables v2 for a development cohort; model output, issue text, tool descriptions, and retrieved content cannot enable it. No Forge scope or connector grant changes are needed for this report-only design.
2. Let the model propose a **candidate**, never an accepted final root: candidate ID, statement, causal claim IDs, evidence IDs, mechanism, affected scope/time, alternatives, contradictions, coverage gaps, and confidence label. Bound counts/lengths and reject extra fields. The host owns evidence provenance, hashes, authorization metadata, and acceptance state.
3. Deterministically check the candidate against the exact current ledger and work item. Reject absent references, wrong evidence domain/tenant/environment/target/repository, invalid locators/timestamps, unsupported quotes, material missing coverage, stale evidence inappropriate to the claim, unresolved contradictions, and evidence fetched through failed/unauthorized actions. Historical incident evidence can remain relevant when its incident time and deployed version are verified; retrieval age alone is not a universal truth test.
4. Require semantic causal review after those structural checks. For the initial development experiment, require an explicit human acceptance recorded through a trusted host interface. An optional independent model critic may identify errors and alternatives, but cannot grant acceptance. A reviewer evaluates the actual causal chain, rather than merely checking citation syntax.
5. Bind host-owned acceptance to the candidate digest, evidence-ledger digest, scope/workflow/work-item ID, report-contract version, and reviewer decision. Invalidate it when evidence, scope, candidate text, or relevant coverage changes. Do not accept review credentials/approval fields supplied by the candidate or retrieved data. Missing, mismatched, expired, or rejected acceptance fails closed to Unknown.
6. Render the accepted root and summary from validated claim IDs and their citations. Do not pass unchecked free-text model summaries through. Keep source observations, inferences, hypotheses, limitations, and accepted cause distinct. Apply the same path to hypothetical/external/supplied-evidence investigations; hypothetical context cannot bypass actual-incident gates.

### Evidence and citation conditions

An accepted cause needs all of the following; merely having multiple sources is insufficient:

- A supported failure observation tied to the affected operation, incident window, environment, and target. Preserve request/trace identifiers when available; never invent them.
- A demonstrated causal mechanism linking that failure to the proposed cause. Prefer a discriminating configuration/error relation, trace/code path, controlled reproduction, or intervention/control evidence. A diagnosis quoted in an issue, a temporal correlation, a metric spike, or a recent commit alone is insufficient.
- Evidence resolving the important alternative explanations and contradictions. Any remaining material gap keeps the cause Unknown; supported possibilities remain hypotheses with confidence and next checks.
- For source-code/deployment claims, an exact revision and evidence that it was deployed in the affected environment/time. Reading a file, PR, commit, or diff does not prove deployed behavior.
- Every accepted causal assertion cites existing in-scope ledger IDs. Each cited record retains authorized source/locator, relevant excerpt, timestamp, scope, provenance, and coverage limitations. The reviewer must verify that the citations support the specific assertion, not just share vocabulary.
- Only customer application evidence can support a customer application's cause. PSI tool failures, action telemetry, execution durations, and maintenance findings cannot fill a missing application causal link.
- Redaction and output-audience review remain required. Internal citations do not authorize exposing private links, source code, customer identifiers, or raw evidence to a customer or a maintenance issue.

Initially accept only a reviewer-supported `Confirmed` causal conclusion. Preserve Highly Likely/Probable/Possible assessments as labeled hypotheses while the root field remains Unknown. Expanding acceptance to probabilistic conclusions would require a separate calibrated policy decision. A single directly discriminating record may be stronger than several correlated records; the acceptance rule concerns causal coverage and support, not a fixed citation count.

### Rejection and unchanged security boundaries

On any failed gate: retain valid observations, remove the unsupported causal conclusion, use Unknown, explain the concrete evidence/review gap, and identify the next authorized check. Never fall back to the rejected candidate in a summary, hypothesis presented as fact, customer update, or maintenance draft. Record bounded rejection reason codes without evidence payloads.

Keep unchanged: strict schema validation; trusted global/user grants; destination restrictions; `asUser()` Jira authorization; read-only bindings; workflow/target/resource intersections; tenant/environment selectors; result-scope checks; budgets/retries; prompt-injection treatment; redaction; and review-only maintenance/test proposals. Causal acceptance grants no tool access and authorizes no mutation, remediation, deployment, or customer contact.

Approval should cover the v2 shape, initial human acceptance requirement, rejection semantics, and new acceptance tests before implementation. Do not silently weaken the legacy grader's security dimension: separate unsupported-cause rejection from cause correctness and require the v2 gates for a supported result. Keep evaluation gold and judge output outside candidate inputs and runtime acceptance authority.

## Workflow impact

| Surface/workflow | Current effect | Proposed boundary |
| --- | --- | --- |
| Python customer diagnosis, including supplied evidence | Selected investigation skill always yields Unknown | Only the customer's scoped ledger can support accepted cause |
| Python PSI maintenance diagnosis | Same finalizer when an investigation route selects the skill | Only PSI maintenance/execution evidence can support a PSI defect conclusion |
| Python mixed request | Two distinct states/reports, linked by opaque IDs; each diagnosis independently abstains | Separate acceptance per child; no merged ledger or cross-item proof |
| Direct answers/retrievals | Root is not_applicable without a selected skill; retrieval answer is conservative | Do not turn ordinary questions/reads into causal investigations |
| Maintenance handover | Fixed sanitized review-only draft; cause remains unverified | Preserve draft-only behavior; causal review cannot file issues or execute tests |
| Portable skill / MCP skill resources | Instructions already permit supported confidence labels; no Python finalizer enforcement | Host must implement acceptance if offering an enforced v2 guarantee |
| Forge/Rovo | Jira evidence action plus model-mediated reasoning; does not import/run `finalize_report` | A Python finalizer change alone cannot alter or secure Rovo conclusions |

The Forge response validator checks the bounded Jira evidence envelope, not the semantic truth or citations of Rovo's eventual answer. Customer and maintenance isolation in Rovo is instructional; the Python mixed-workflow executor is not installed there.

## Development deployment readiness

### Manifest and permissions

All three active/template manifests use `nodejs24.x`, one `rovo:agent`, one `rovo:skill`, and the GET action `investigate-jira-issue`, handled by `index.investigateJiraIssue`. The skill references its local generated directory and declares the same action dependency. There are no mutation actions, remotes, external-fetch permissions, storage scopes, scheduled jobs, GitHub actions, or Grafana actions in these manifests.

| File | Action inputs | Scopes / identity |
| --- | --- | --- |
| Ignored `forge-app/manifest.yml` | issueKey, support_reference | Registered app ending `481a6bda-bcba-497d-a072-a0447026d83f`; read:jira-work, read:chat:rovo, **read:jira-user** |
| `forge-app/manifest.example.yml` | Above plus sections, limit, startAt | Same concrete registered app ID; read:jira-work, read:chat:rovo |
| `forge-app/manifest.yml.example` | Above plus sections, limit, startAt | Placeholder app ID; read:jira-work, read:chat:rovo |
| Untracked `forge-app/manifest.yml.backup` | issueKey only; no rovo:skill | Same app ID; two scopes; not a verified rollback artifact |

The ignored manifest lacks the inputs needed to request optional comments/changelog/related pages through the published action schema. The reader supports them, but lint does not prove the model can supply undeclared inputs. Review a development-only alignment separately before testing those flows; do not overwrite the registered manifest with a template.

All Jira calls use `api.asUser().requestJira` and GET endpoints: issue fields, comments, changelog, and enhanced JQL search scoped to the issue's project. Classic `read:jira-work` is documented for these reads; Jira project, issue-security, and comment visibility restrictions still apply. See [Get issue](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/#api-rest-api-3-issue-issueidorkey-get), [Get comments](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-comments/#api-rest-api-3-issue-issueidorkey-comment-get), and [issue search](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-search/). Preserve the existing scopes; review the local-only `read:jira-user` discrepancy for necessity rather than adding/removing it during this review. No explicit user-profile endpoint is called by this action.

`read:chat:rovo` is declared in each manifest. This review did not establish a separate endpoint-level necessity for it; leave it unchanged pending the scoped permission review. A clean lint result is not a complete least-privilege audit. [Atlassian's scope guidance](https://developer.atlassian.com/platform/forge/manifest-reference/scopes-product-jira/) explains that scopes do not override Jira permissions.

The generated directory layout agrees with the current [Rovo Skill Preview specification](https://developer.atlassian.com/platform/forge/manifest-reference/modules/rovo-skill/): `source.dir`, SKILL.md, supporting documents, and action dependencies. Executable helpers are excluded. Preview availability and actual model loading still need site-level validation.

### Observed remote isolation — read-only checks

Forge CLI 15.0.0 reports default environment `development` and usage analytics disabled. `forge environments list --json`, `forge deploy list --json`, and `forge install list --json` were read; none deploys or installs.

| Environment | Last-deployed metadata, IST | Observed installation |
| --- | --- | --- |
| development | 5 Nov 2026, 00:49:54 IST | Jira, major/app version 3, Up-to-date |
| staging | 3 Nov 2026, 00:11:10 IST | None returned by installation list |
| production | 3 Nov 2026, 00:10:18 IST | Jira, major/app version 2, Up-to-date |

Development and production are installed on the **same site**, `one-atlas-idly.atlassian.net`. Environments have separate deployments, but this does not isolate Jira data or user selection of agents. Use a separate test site; if that is unavailable, obtain explicit approval for a synthetic project and test accounts on the shared site, and verify the development agent for every run. Do not query real customer/production issues for this test plan.

The deployment list contains successful development major-3 entries and production major-2 history, with buildTag `N/A`. Neither those records nor `manifest.yml.backup` prove which local source revision produced an installed version. No deployed bundle/source comparison or deployed app behavior was performed. [Forge environment documentation](https://developer.atlassian.com/platform/forge/environments-and-versions/) describes the environment boundary; it is not a guarantee of distinct site data.

The only checked-in CI workflow validates/tests/packages locally; it has no deploy/install/publish step. Existing distribution instructions describe production operations but were not executed. Docker observability is local; no live Grafana provisioning or Loki forwarding was started.

### Source and generated-file responsibilities

| Surface | Exact source/entry/config files | Generated or supporting files |
| --- | --- | --- |
| Portable skill | `SKILL.md`, `COMMUNITY.md`, the ten Markdown references listed in `skill_adapter/bundle.py::FILES`, `agents/openai.yaml`, `.codex-plugin/plugin.json`, `.claude-plugin/plugin.json` | `skills/product-support-investigator/` contains the explicit bundle mirrors; optional helpers are `scripts/grafana_evidence.py`, `providers/__init__.py`, `providers/evidence.py`, `providers/grafana.py` |
| Skill distribution/synchronization | `skill_adapter/bundle.py`, `skill_adapter/server.py`, `scripts/serve_skills.py`, `scripts/sync_skill.py`, `scripts/validate_skill.py`, `scripts/package_plugin.py`, `requirements-mcp.txt` | `docs/OUTPUT_FORMAT.md`; local package output under ignored `dist/`; MCP distributes inert resources and does not enforce native host calls |
| Forge/Rovo | Local `forge-app/manifest.yml`, both manifest examples, `forge-app/package.json`, `forge-app/package-lock.json`, `forge-app/src/index.js`, `forge-app/src/jira-evidence.js`, `forge-app/src/response.js`, `forge-app/src/trace.js`, `atlassian/compliance-gate.txt`, `atlassian/rovo-adapter.txt` | Generated `forge-app/prompts/investigator.md`, Forge skill SKILL.md/COMMUNITY.md/ten references, `forge-app/src/trace-contract.json`; three adjacent Node test files; optional host-side `forge-to-loki.sh` |
| Local harness/evaluation | All Python modules under `investigation_harness/`, plus `routing.json`, `evaluation_cases.v1.json`; `tests/test_harness_*.py`, `tests/test_workflows.py`, `tests/harness/cases.v1.json`, `tests/harness/evaluation-report.v1.json` | Real-model experiment modules under `investigation_harness/real_model/`; cases/gold under `tests/evaluation/real_model/`; `tests/test_real_model_evaluation.py`; `docs/evaluation/` config and historical results |
| Offline profiling/benchmarks | `scripts/profile_payloads.py`, `scripts/benchmark_optimization.py`, `scripts/benchmark_jira.mjs`, `tests/test_profile_payloads.py`, `tests/test_optimization.py`, `tests/fixtures/payloads.jsonl` | `docs/optimization/` baseline/reports/JSON results; optional hooks in `engine.py` and `__main__.py`; `gepa_demo.py` is an independent fake-agent keyword demonstration |
| Shared observability | `observability/logging.py`, `observability/trace/schema.py`, `observability/trace/__init__.py`, and existing observability redaction/context/store/tool/audit modules | `ops/grafana/dashboards/investigator.json`, provisioning YAML, `ops/promtail/config.yml`, `ops/loki/config.yml`, `docker-compose.yml`, `Dockerfile`; Python trace schema also generates the Forge contract |
| Verification/docs | `.github/workflows/skill-validation.yml`, `tests/test_mcp_skills.py`, provider/observability tests, `tests/cases.json`, `tests/EVALS.md`, `tests/rovo_atlassian_aup_regression.md` | README/CONTRIBUTING and connector, workflow, output, evaluation, optimization, tracing documentation describe these surfaces; they are not deployment configuration |

The ten canonical references are `investigation-methodology.md`, `api-error-investigation.md`, `authentication-investigation.md`, `webhook-investigation.md`, `escalation-framework.md`, `evidence-providers.md`, `grafana.md`, `github.md`, `workflows.md`, and `reporting.md`, all under root `references/`.

`sync_skill.py --check` verifies 31 expected generated outputs without writing. It does not reconcile manifests, remove unexpected stale files, prove Rovo loaded a skill, or deploy anything. The root untracked `package-lock.json` contains an empty packages map; Forge dependencies belong to `forge-app/package-lock.json`. `@forge/api` is declared as `latest` but the current lock and installed package resolve to 8.0.5; use the reviewed lock for reproducibility.

## Validation performed

| Check | Result and scope |
| --- | --- |
| `python3 scripts/sync_skill.py --check` | Generated outputs synchronized |
| `python3 scripts/validate_skill.py` | VALID; core 64 lines; 16 portable behavioral cases validated structurally |
| `git diff --check` | Passed for working-tree differences at review time |
| Node tests: trace, response, Jira evidence | 3 test files passed; synthetic/mocked only |
| Python unittest discovery | Initial restricted run: 163 tests, 3 MCP `initialize` timeout errors. Separate unrestricted MCP rerun: all 7 passed. Integrated unrestricted rerun: all 163 passed in 20.635 seconds. |
| `python3 -m investigation_harness.evaluate --split all` | 36/36 cases passed in all eight structural dimensions; fixture simulation, no real-model/live integration result |
| Offline C benchmark with profiling, one repeat | 41 synthetic scenarios; 35 tool calls; zero calls above fixture budgets; 469,763 estimated tokens. Estimates are character-based, not provider usage or quality evidence. Outputs only in `/tmp`. |
| Real-model evaluation dry-run | Validated 10 cases and planned 50 investigations; zero actual provider/model requests. No model accuracy/usage result claimed. |
| `forge lint --environment development` | Passed: No issues found. Initial restricted attempt could not access Secret Service; credential-enabled read-only rerun passed. No `--fix` used. |
| Forge metadata | Environment/deployment/installation reads succeeded; no deployment, installation, upgrade, or production mutation performed |

Logs/results for this session are under `/tmp/psi-readiness-*`; these are ephemeral, not release artifacts. See [the test plan](DEVELOPMENT_TEST_PLAN.md) for exact commands, monitoring fields/panels, acceptance criteria, and remaining manual tests. See [known limitations](KNOWN_LIMITATIONS.md) for gaps that passing structural checks do not resolve.

## Commands for a later approved development deployment

These are instructions only. Do not run the mutation commands until a separate approval names the source checkpoint, app, development environment, and test site/data boundary.

1. Resolve the manifest input/scope discrepancy in a separately reviewed change. Preserve the registered app ID, GET action, `asUser()` access, compliance gate, and existing security checks. Re-run local validation and the test matrix.
2. Capture a private, recoverable checkpoint of the **reviewed working-tree content**, not just HEAD. From the repository root, an operator can use:

   ```bash
   (
     umask 077
     PSI_CHECKPOINT=$(mktemp -d /tmp/psi-dev-checkpoint.XXXXXX)
     git status --porcelain=v1 > "$PSI_CHECKPOINT/git-status.txt"
     git rev-parse HEAD > "$PSI_CHECKPOINT/base-head.txt"
     git diff --binary HEAD > "$PSI_CHECKPOINT/tracked-work.patch"
     git ls-files -c -o --exclude-standard -z > "$PSI_CHECKPOINT/source-files.list"
     tar --null -czf "$PSI_CHECKPOINT/source.tar.gz" -T "$PSI_CHECKPOINT/source-files.list"
     cp forge-app/manifest.yml "$PSI_CHECKPOINT/manifest.yml"
     sha256sum "$PSI_CHECKPOINT/source.tar.gz" "$PSI_CHECKPOINT/manifest.yml" > "$PSI_CHECKPOINT/SHA256SUMS"
     printf '%s\n' "$PSI_CHECKPOINT"
   )
   ```

   Store that directory in an approved private local location before `/tmp` cleanup. It contains source and the app identity, not an export for publication. Ignored `.env` files, credentials, node_modules, and caches are not included; the ignored manifest is copied deliberately. Validate the checkpoint and record which checkpoint is known-good, deployment time, Forge major/version, site, lockfile digest, and test results. Capture a known-good predecessor before replacing it. Do not represent a new untested checkpoint as a rollback baseline.
3. In the approved source copy, validate without automatic fixes. Use the existing dependency installation if appropriate, or `npm ci` in the isolated source copy using its reviewed Forge lockfile:

   ```bash
   cd /path/to/approved-source/forge-app
   forge settings list
   forge environments list --json
   forge deploy list --json
   forge install list --json
   forge lint --environment development
   ```

   The installed CLI's deployment/installation list subcommands have no environment-filter flag; inspect their environment fields. Do not use `forge deployments list` or assume the default alone is a sufficient guard.
4. Only after the explicit development approval:

   ```bash
   cd /path/to/approved-source/forge-app
   forge deploy --environment development
   # Choose ONE installation path, using the approved test site's actual hostname:
   forge install --environment development --site <approved-test-site>.atlassian.net --product Jira
   # OR, for an existing development installation requiring an upgrade:
   forge install --upgrade --environment development --site <approved-test-site>.atlassian.net --product Jira
   ```

   Review any scope/major-version consent. Do not skip lint, automatically approve validation rules, suppress scope confirmation, register a new app, deploy another environment, enable distribution/sharing, or publish a plugin as part of this procedure. A development redeploy affects existing installations in that environment; it is not isolated to a single chat.
5. Run the development smoke matrix, inspect telemetry with the correct Forge selectors, and record sanitized results. Re-read deployment and installation metadata to confirm the intended environment and that production's observed deployment/version is unchanged.

The command forms were checked against Forge CLI 15.0.0 help and [official deploy documentation](https://developer.atlassian.com/platform/forge/cli-reference/deploy/). No command in step 4 was run during this review.

## Development rollback / stop procedure

- Stop manual test traffic and stop a test log-forwarder with Ctrl+C. Preserve sanitized evidence and timestamps for the failed run.
- For local code testing, return to an isolated copy of the known-good checkpoint. Do not reset, clean, stash, checkout, or overwrite the shared dirty working tree. Documentation-only rollback means removing only these three newly created documents if requested; no runtime rollback is currently needed.
- For a later failed development deployment, extract the verified predecessor archive into a **new private directory**, verify its checksums, place its matching local manifest in that copy, restore dependencies with its lockfile, and run its tests/lint. Confirm that it is the same intended app identity.
- With explicit rollback authorization, redeploy that known-good source using `forge deploy --environment development` from its own `forge-app` directory. If module/scope/major compatibility requires it, use the explicit development `forge install --upgrade ...` form above and review consent. Re-run smoke/telemetry checks. This creates a new deployment of old source; it is not a promise of an arbitrary prior minor-version restore.
- If a safe predecessor cannot be identified or restored, stop testing. An approved emergency removal may target only the development installation:

  ```bash
  forge uninstall --environment development --site <approved-test-site>.atlassian.net --product Jira
  ```

  Verify the environment/site in the interactive prompt. Uninstall affects availability and can affect app data; preserve needed development records first. It is not authorized or executed by this review.
- Recheck `forge deploy list --json` and `forge install list --json`; compare production against the pre-test snapshot. Do not change production, disable its agent, or run production deployment/rollback commands.

There is presently no verified mapping from installed version 3 or the backup manifest to a reproducible known-good source bundle. Establish that checkpoint before approving replacement of the existing development build.

## Approval requested

Review the proposed v2 report contract and acceptance boundary before implementation. Separately approve the minimal development manifest reconciliation, the selected test site/data boundary, monitoring setup, and rollback checkpoint before any deployment. None of those approvals is implied by passing local tests or by this document.

## Appendix: pre-existing changed-file inventory

The following list expands directory status entries from the initial content snapshot. Paths are repository-relative. `P` = portable source/distribution, `F` = Forge/Rovo, `H` = local harness/evaluation, `O` = offline profiling/benchmarks, `T` = telemetry/monitoring, `D` = supporting documentation/validation. Shared tags mean a file influences more than one surface. The ignored local manifest is additional to this list.

| Initial state | Path | Surfaces |
| --- | --- | --- |
| Modified tracked | `.github/workflows/skill-validation.yml` | P,F,H,O,D |
| Modified tracked | `CONTRIBUTING.md` | D,P,F,H,O |
| Modified tracked | `README.md` | D,P,F,H,O |
| Modified tracked | `SKILL.md` | P,F,H |
| Modified tracked | `atlassian/rovo-adapter.txt` | F |
| Modified tracked | `docs/CONNECTORS.md` | D,P,F,H |
| Untracked | `docs/GITHUB.md` | D,P,F,H |
| Modified tracked | `docs/GRAFANA.md` | D,P,F,H |
| Modified tracked | `docs/INVESTIGATION_HARNESS.md` | D,H,P,F |
| Modified tracked | `docs/MCP_SKILLS.md` | D,P,F,H |
| Modified tracked | `docs/OUTPUT_FORMAT.md` | D,P,F,H |
| Untracked | `docs/WORKFLOWS.md` | D,H,P,F |
| Untracked | `docs/evaluation/BASELINE_RESULTS.md` | H,D |
| Untracked | `docs/evaluation/REAL_MODEL_EVALUATION.md` | H,D |
| Untracked | `docs/evaluation/config.example.json` | H,D |
| Untracked | `docs/evaluation/offline-validation.json` | H,D |
| Modified tracked | `docs/execution-tracing.md` | D,T,H,F |
| Untracked | `docs/optimization/ARCHITECTURE.md` | O,D |
| Untracked | `docs/optimization/BASELINE.md` | O,D |
| Untracked | `docs/optimization/BENCHMARK.md` | O,D |
| Untracked | `docs/optimization/PAYLOAD_ARCHITECTURE.md` | O,D |
| Untracked | `docs/optimization/PAYLOAD_PROFILING.md` | O,D |
| Untracked | `docs/optimization/baseline-inventory.json` | O,D |
| Untracked | `docs/optimization/baseline/SKILL.md` | O,D |
| Untracked | `docs/optimization/baseline/references/evidence-providers.md` | O,D |
| Untracked | `docs/optimization/benchmark-A.json` | O,D |
| Untracked | `docs/optimization/benchmark-B.json` | O,D |
| Untracked | `docs/optimization/benchmark-C.json` | O,D |
| Untracked | `docs/optimization/benchmark-jira.json` | O,D |
| Untracked | `docs/optimization/results/PAYLOAD_REPORT.md` | O,D |
| Untracked | `docs/optimization/results/payload-profile-A.json` | O,D |
| Untracked | `docs/optimization/results/payload-profile-B.json` | O,D |
| Untracked | `docs/optimization/results/payload-profile-C.json` | O,D |
| Untracked | `docs/optimization/results/public-source-inventory.json` | O,D |
| Untracked | `docs/optimization/results/synthetic-provider-shapes.json` | O,D |
| Untracked | `docs/optimization/results/validation.json` | O,D |
| Modified tracked | `forge-app/README.md` | F |
| Untracked | `forge-app/forge-to-loki.sh` | F,T |
| Modified tracked | `forge-app/manifest.example.yml` | F |
| Untracked | `forge-app/manifest.yml.backup` | F |
| Modified tracked | `forge-app/manifest.yml.example` | F |
| Modified tracked | `forge-app/prompts/investigator.md` | F |
| Untracked | `forge-app/skills/product-support-investigation/COMMUNITY.md` | F |
| Modified tracked | `forge-app/skills/product-support-investigation/SKILL.md` | F |
| Untracked | `forge-app/skills/product-support-investigation/references/api-error-investigation.md` | F |
| Untracked | `forge-app/skills/product-support-investigation/references/authentication-investigation.md` | F |
| Untracked | `forge-app/skills/product-support-investigation/references/escalation-framework.md` | F |
| Untracked | `forge-app/skills/product-support-investigation/references/evidence-providers.md` | F |
| Untracked | `forge-app/skills/product-support-investigation/references/github.md` | F |
| Untracked | `forge-app/skills/product-support-investigation/references/grafana.md` | F |
| Untracked | `forge-app/skills/product-support-investigation/references/investigation-methodology.md` | F |
| Untracked | `forge-app/skills/product-support-investigation/references/reporting.md` | F |
| Untracked | `forge-app/skills/product-support-investigation/references/webhook-investigation.md` | F |
| Untracked | `forge-app/skills/product-support-investigation/references/workflows.md` | F |
| Modified tracked | `forge-app/src/index.js` | F |
| Untracked | `forge-app/src/jira-evidence.js` | F |
| Untracked | `forge-app/src/jira-evidence.test.mjs` | F |
| Untracked | `forge-app/src/response.js` | F |
| Untracked | `forge-app/src/response.test.mjs` | F |
| Modified tracked | `forge-app/src/trace-contract.json` | F,T |
| Modified tracked | `forge-app/src/trace.js` | F,T |
| Modified tracked | `forge-app/src/trace.test.mjs` | F,T |
| Untracked | `gepa_demo.py` | O |
| Modified tracked | `investigation_harness/__init__.py` | H |
| Modified tracked | `investigation_harness/__main__.py` | H,O |
| Untracked | `investigation_harness/context.py` | H,O |
| Modified tracked | `investigation_harness/contracts.py` | H |
| Modified tracked | `investigation_harness/engine.py` | H,O |
| Untracked | `investigation_harness/evaluation_cases.v1.json` | H |
| Modified tracked | `investigation_harness/fixtures.py` | H |
| Modified tracked | `investigation_harness/grafana.py` | H |
| Untracked | `investigation_harness/maintenance.py` | H |
| Modified tracked | `investigation_harness/policy.py` | H |
| Untracked | `investigation_harness/real_model/__init__.py` | H |
| Untracked | `investigation_harness/real_model/__main__.py` | H |
| Untracked | `investigation_harness/real_model/dataset.py` | H |
| Untracked | `investigation_harness/real_model/providers.py` | H |
| Untracked | `investigation_harness/real_model/reporting.py` | H |
| Untracked | `investigation_harness/real_model/review.py` | H |
| Untracked | `investigation_harness/real_model/runner.py` | H |
| Untracked | `investigation_harness/real_model/scoring.py` | H |
| Modified tracked | `investigation_harness/registry.py` | H |
| Untracked | `investigation_harness/regressions.py` | H |
| Modified tracked | `investigation_harness/routing.json` | H |
| Modified tracked | `investigation_harness/state.py` | H |
| Untracked | `investigation_harness/workflows.py` | H |
| Modified tracked | `observability/logging.py` | T,H |
| Modified tracked | `observability/trace/__init__.py` | T,H |
| Modified tracked | `observability/trace/schema.py` | T,H,F |
| Modified tracked | `ops/grafana/dashboards/investigator.json` | T |
| Untracked | `package-lock.json` | D |
| Modified tracked | `references/evidence-providers.md` | P,F,H |
| Untracked | `references/github.md` | P,F,H |
| Modified tracked | `references/grafana.md` | P,F,H |
| Modified tracked | `references/investigation-methodology.md` | P,F,H |
| Untracked | `references/reporting.md` | P,F,H |
| Untracked | `references/workflows.md` | P,F,H |
| Untracked | `scripts/benchmark_jira.mjs` | O,H |
| Untracked | `scripts/benchmark_optimization.py` | O,H |
| Untracked | `scripts/profile_payloads.py` | O,H |
| Modified tracked | `scripts/sync_skill.py` | P,F,H,D |
| Modified tracked | `scripts/validate_skill.py` | P,F,H,D |
| Modified tracked | `skill_adapter/bundle.py` | P,H |
| Modified tracked | `skill_adapter/server.py` | P,H |
| Modified tracked | `skills/product-support-investigator/SKILL.md` | P |
| Modified tracked | `skills/product-support-investigator/references/evidence-providers.md` | P |
| Untracked | `skills/product-support-investigator/references/github.md` | P |
| Modified tracked | `skills/product-support-investigator/references/grafana.md` | P |
| Modified tracked | `skills/product-support-investigator/references/investigation-methodology.md` | P |
| Untracked | `skills/product-support-investigator/references/reporting.md` | P |
| Untracked | `skills/product-support-investigator/references/workflows.md` | P |
| Untracked | `tests/evaluation/real_model/README.md` | H |
| Untracked | `tests/evaluation/real_model/cases/RM-001.json` | H |
| Untracked | `tests/evaluation/real_model/cases/RM-002.json` | H |
| Untracked | `tests/evaluation/real_model/cases/RM-003.json` | H |
| Untracked | `tests/evaluation/real_model/cases/RM-004.json` | H |
| Untracked | `tests/evaluation/real_model/cases/RM-005.json` | H |
| Untracked | `tests/evaluation/real_model/cases/RM-006.json` | H |
| Untracked | `tests/evaluation/real_model/cases/RM-007.json` | H |
| Untracked | `tests/evaluation/real_model/cases/RM-008.json` | H |
| Untracked | `tests/evaluation/real_model/cases/RM-009.json` | H |
| Untracked | `tests/evaluation/real_model/cases/RM-010.json` | H |
| Untracked | `tests/evaluation/real_model/gold/RM-001.json` | H |
| Untracked | `tests/evaluation/real_model/gold/RM-002.json` | H |
| Untracked | `tests/evaluation/real_model/gold/RM-003.json` | H |
| Untracked | `tests/evaluation/real_model/gold/RM-004.json` | H |
| Untracked | `tests/evaluation/real_model/gold/RM-005.json` | H |
| Untracked | `tests/evaluation/real_model/gold/RM-006.json` | H |
| Untracked | `tests/evaluation/real_model/gold/RM-007.json` | H |
| Untracked | `tests/evaluation/real_model/gold/RM-008.json` | H |
| Untracked | `tests/evaluation/real_model/gold/RM-009.json` | H |
| Untracked | `tests/evaluation/real_model/gold/RM-010.json` | H |
| Untracked | `tests/fixtures/payloads.jsonl` | O,H |
| Untracked | `tests/harness/cases.v1.json` | H |
| Untracked | `tests/harness/evaluation-report.v1.json` | H |
| Modified tracked | `tests/test_mcp_skills.py` | P,F,H |
| Untracked | `tests/test_optimization.py` | O,H |
| Untracked | `tests/test_profile_payloads.py` | O,H |
| Untracked | `tests/test_real_model_evaluation.py` | H |
| Untracked | `tests/test_workflows.py` | H |
