# PSI evaluation baseline results

Recorded 5 November 2026. EXP-001 / EXP-002 infrastructure is implemented and
validated offline. **Real-model investigations: 0. Real-model requests: 0.**
No provider/model execution configuration was selected or authorized for this
implementation. No paid model requests, production connector calls, deployment,
publication or automatic commits were performed.

## Structural simulation results

| Check | Result |
| --- | --- |
| Existing PSI structural evaluator | 36/36 cases pass all eight applicable dimensions |
| Existing expanded synthetic benchmark | 41/41 cases pass applicable checks |
| Existing payload profile | 427,731 estimated input tokens across 299 synthetic invocations |
| Synthetic invocation breakdown | 234 scripted adapter invocations, 65 deterministic critics |
| Confirmed real-model requests in that profile | 0 |
| New dataset validation | 10/10 case contracts, gold references and deterministic responses valid |
| Planned future repetitions | 5 per case, 50 investigations total |
| New offline evaluation tests | 30 pass; model transports and usage counts are mocks |
| Complete Python regression suite | 163 pass (133 existing + 30 new) |
| Payload profiler regression suite | 28 pass, included in the complete suite |
| Forge Node validation | All 3 requested test files pass |
| Skill synchronization / validation | Pass |
| Portable and Forge skill quick validation | Both pass |
| Local package generation / archive validation | Pass, 44 allowlisted files |

The standalone structural evaluator contains 36 cases; the expanded benchmark
adds five, giving the previously reported 41. Neither evaluates real-model
investigation accuracy. Payload estimates reproduce the existing profiling
baseline and remain separate from actual usage. The benchmark's older whole-message
estimator reports 454,278 estimated input tokens; its serialization differs from
the profiler's component-wise method. Neither figure is provider accounting.

The first sandboxed Python run completed 160 tests with three MCP stdio
initialization errors. The seven existing MCP tests passed outside the sandbox.
After final additions, the entire suite passed outside the sandbox: 163 tests,
zero failures/errors. No MCP production code was changed to work around the
execution environment.

[offline-validation.json](offline-validation.json) records the new dataset checks
and the explicit zero-model/unmeasured status. Test-generated 50-run mock reports
exist only in temporary test directories and are not real-model baseline data.

## Real-model results

| Measurement | Result |
| --- | --- |
| Candidate provider / model | Unconfigured for execution |
| Temperature / generation configuration | No executed configuration |
| Real-model investigations / repetitions completed | 0 / 0 |
| Candidate / independent judge model requests | 0 / 0 |
| Root-cause correctness and accuracy | Unmeasured |
| Correct / incorrect abstention | Unmeasured |
| Confident-wrong rate | Unmeasured |
| Semantic claim-support accuracy | Unmeasured |
| Real-model tool-selection accuracy / consistency | Unmeasured |
| Real-model safety violations | Unmeasured; zero real-model trials |
| Mean full quality / pass rate / all-five-pass rate | Unmeasured |
| Actual input / output tokens | Unavailable |
| Cache-read / cache-write tokens | Unavailable |
| Understand / Choose / Propose latency | Unmeasured |
| Synthetic tool execution / Report latency with a real candidate | Unmeasured |
| Critic / Revise latency in real-model investigations | Unmeasured |
| Total real-model investigation duration | Unmeasured |
| Production latency | Unmeasured |
| Monetary cost | Not calculated |

Local test timings are not substituted for provider or production latency. The
runner measures future investigation timings with payload profiling disabled.
Its default critic is deterministic, not an independent model request.

## Human-reviewed results

Human-reviewed real-model runs: **0**. Judge calibration examples supplied by
humans: **0**. Human/judge agreement and judge false acceptance are unmeasured.
Passing tests of the review schema does not count as human semantic validation.

## Unmeasured dimensions and acceptance

All real-model quality, reliability, usage and latency dimensions above remain
unmeasured. Semantic support is never automatically passed when no judge or human
review is available. The infrastructure is ready for an explicitly configured,
authorized execution; a semantic/performance baseline has **not** been established.
Acceptance gates for real-model safety and quality cannot pass with zero trials.

The production report guard always finalizes investigation root causes as
`Unknown`. It will therefore expose incorrect abstentions on the three
determinable cases. This is a known architectural limit, not a measured accuracy
result. Raw model attempts are retained separately, including claims removed by
the guard. No workflow optimization or causal-report contract change was made.

The ten public synthetic cases do not measure real customer distributions,
production connector behavior, all injection strategies or model generalization.
Fixed fixture timestamps disable freshness only in the evaluation registry.
Gold separation protects the model interface, not arbitrary trusted Python
factory code. A custom transport must not read gold or fabricate provider usage.
In-flight cancellation may leave usage unavailable; planned and incomplete runs
remain visible in the saved plan and run artifacts.

## Reproduction

Run from the repository root using the existing environment; no new dependencies
are needed:

```bash
.venv-mcp/bin/python -m investigation_harness.real_model --dry-run \
  --config docs/evaluation/config.example.json \
  --output /tmp/psi-evaluation-validation.json
.venv-mcp/bin/python -m unittest discover -s tests -p 'test_*.py'
.venv-mcp/bin/python -m investigation_harness.evaluate --split all \
  --output /tmp/psi-structural-evaluation.json
.venv-mcp/bin/python -m unittest discover -s tests -p 'test_profile_payloads.py'
.venv-mcp/bin/python scripts/benchmark_optimization.py --label C --repeats 1 \
  --output /tmp/psi-synthetic-benchmark.json \
  --profile-output /tmp/psi-synthetic-payload-profile.json
node --test forge-app/src/trace.test.mjs forge-app/src/response.test.mjs forge-app/src/jira-evidence.test.mjs
.venv-mcp/bin/python scripts/validate_skill.py
.venv-mcp/bin/python scripts/package_plugin.py
```

If the local sandbox prevents MCP stdio initialization, run the existing test
suite in an environment that permits local subprocess stdio. Packaging produces
only the existing ignored local archive; no upload occurs.

See [REAL_MODEL_EVALUATION.md](REAL_MODEL_EVALUATION.md) for explicit provider/model
configuration, optional judge, human review, calibration and paired comparisons.
Actual execution requires a separate, explicit authorization to use the provider.
