# Investigation Methodology

## Goal

Turn a customer-reported symptom into an evidence-backed technical assessment without overclaiming.

## Evidence ladder

Prefer, when applicable:
1. Exact request/transaction evidence
2. Distributed trace
3. Application log tied to the same request
4. Error event/stack trace
5. Dependency/database call tied to the same trace
6. Metrics showing pattern/impact
7. Deployment/configuration/feature-flag history
8. Code change / known bug
9. Historical incidents or support cases
10. Documentation
11. Human assumption

This is guidance, not an absolute ranking.

## Search strategy

Search narrowly first:
1. exact request/correlation ID
2. exact transaction/resource ID
3. exact timestamp ± 2–5 minutes
4. exact error or exception
5. endpoint + account
6. version + endpoint
7. broader time range / similar cases

After each search, record:
- what changed in the investigation;
- what hypothesis gained or lost support;
- what the next discriminating check is.

Avoid repeated searches that do not change the evidence state.

## Progressive decomposition

Divide the relevant workflow into stages, such as user action -> client -> request/network -> authentication -> application -> dependency/persistence -> response. Adapt this sequence to the system.

Find the earliest evidence-supported boundary between working and failing behavior; an unknown stage is not proof of success. Investigate that boundary before expanding broadly.

Choose checks by surface and access:
- Web: inspect the relevant network request or console signal.
- Mobile: distinguish a local app crash from transport failure or a backend error; start with the action, app version, visible error, and timestamp. Use device logs only when available and appropriate.
- API: inspect the exact request and response.
- CLI: inspect the command and error output; use scoped verbose output only when supported and safe.
- Desktop: inspect the failing action and application diagnostics when available.
- Backend: correlate request IDs or timestamps with logs/traces.
- Integration/webhook: separate sender, transport, receiver, processing, and acknowledgement.

These are starting points, not mandatory checks.

## Hypothesis discipline

For every leading hypothesis list:
- supporting evidence;
- contradictory evidence;
- missing validation;
- falsification test.

Example:

Hypothesis: deployment regression\
Support: failures begin 90 seconds after release; matching stack trace references changed code.\
Against: one similar failure occurred before release.\
Missing: comparison across versions.\
Falsification: if old-version instances fail at the same rate, deployment causation weakens.

## Confidence rubric

High: strong independent evidence with limited contradiction.
Medium: meaningful support with an important validation gap.
Low: weak, sparse, or conflicting evidence.
Explain the confidence label; do not invent numerical precision.

## Correlation checklist

Correlate using:
- request/correlation ID;
- exact or near-identical timestamps;
- same account/resource;
- same endpoint/action;
- same exception/error fingerprint;
- same application version;
- same deployment/config event;
- same dependency or region;
- repeated pattern across customers.

Do not call a temporal relationship causal without additional support.

## Sparse-evidence mode

If only a symptom is known:
1. preserve the reported symptom without treating the user's explanation as a cause;
2. identify the goal, observed surface, and relevant failure stage as far as evidence allows;
3. inspect connected read-only evidence sources when useful before asking the user to retrieve the same information;
4. otherwise choose the smallest safe, executable collection check suited to the user's access;
5. explain where to look, what to do, what result to capture, and what outcomes would distinguish;
6. ask essential context questions when needed; do not force a diagnostic action when a question is the better next move;
7. continue from the result when it becomes available.

Do not reduce this mode to missing fields or generic low-confidence hypotheses. Request IDs, timestamps, endpoint/action, and environment are useful; explain how to obtain them when practical. Avoid full diagnostic dumps and redact secrets and personal data.

## Conflict handling

If sources disagree:
1. expose the disagreement;
2. identify likely reasons such as ingestion delay, timezone mismatch, sampling, clock skew, retries, or stale metadata;
3. prefer the source closest to the actual transaction;
4. lower confidence until reconciled.

## Stop conditions

Stop investigating when:
- root cause is adequately confirmed;
- the next action requires a different owner/access level;
- remaining searches are repetitive and non-discriminating;
- the user requested a bounded analysis;
- the next useful action requires access, authorization, or capability unavailable to both investigator and user;
- no further safe discriminating check can be identified.

Return the current evidence state rather than filling gaps with guesses, and include the next executable evidence-gathering action whenever one exists. Waiting for a user's check result pauses execution, not the investigation; state the continuation branch and resume from the returned evidence.

## Successful-Path Comparison


Compare failing behavior with a related successful operation whenever possible. Change or compare one meaningful variable at a time; for telemetry windows, keep selectors and query resolution constant.

Examples:

- one API endpoint fails while another succeeds;
- one customer fails while others succeed;
- one environment fails while another succeeds;
- authentication succeeds but a later operation fails;
- an older version works while a newer version fails;
- one CLI command succeeds while another command fails.

Ask which components are shared and which meaningful differences exist between the successful and failing paths. Do not blame a shared dependency without evidence explaining why the successful path was unaffected.


## Onset, Changes, Compatibility, and Known Issues


When relevant, determine whether the workflow worked before and what changed near the onset of the issue.

Useful sources include deployment history, configuration changes, dependency/runtime changes, feature flags, package versions, release notes, audit history, previous tickets, and telemetry.

For persistent or version-related errors, check authoritative product documentation, compatibility guidance, release notes, known issues, and official repositories when available.

Official documentation describes expected or supported behavior; it does not by itself prove the root cause in the user's environment. Correlate it with current evidence.

Distinguish a supported workaround from a root-cause fix.


## Goal, Failure Stage, and Issue Validation


Before diagnosing a cause, establish:

1. **Goal** — what the user is trying to accomplish.
2. **Failure stage** — where the expected workflow stops or diverges.
3. **Issue validation** — whether current evidence supports the reported failure.

A useful high-level path may look like:

```text
Goal -> prerequisite -> authentication -> configuration -> request -> processing -> result
```

Adapt the path to the system. For example, an API investigation may consider DNS, TLS, authentication, authorization, request validation, application behavior, dependencies, and the response. A CLI investigation may consider installation, runtime, authentication, project configuration, remote request, processing, and result retrieval.

Do not assume the user's explanation of the issue is already the root cause. If the failure cannot currently be confirmed, label it appropriately as unverified, intermittent, historical, resolved, or Unknown based on evidence.
