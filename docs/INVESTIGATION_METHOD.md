# Investigation Method — Community Edition

Use the workflow in the root `SKILL.md` as the canonical Community methodology.

The Community investigation method is deliberately evidence-first and understandable:

1. establish the user's goal;
2. validate the reported symptom when possible;
3. identify the stage where expected behavior diverges;
4. separate Observed, Inferred, and Unknown information;
5. gather the most relevant available evidence;
6. compare successful and failing behavior;
7. build a timeline and review recent changes when relevant;
8. form a small set of plausible hypotheses;
9. compare supporting and contradicting evidence;
10. assess the deepest cause supported by current evidence;
11. recommend safe next checks, workaround, ownership, escalation, and customer communication as appropriate.

## Epistemic Separation

- **Observed:** directly supported by a source or reproduction.
- **Inferred:** an explanation derived from observed evidence.
- **Unknown:** not available or not yet established.

Never turn temporal proximity, a matching symptom, an exception name, a nearby ticket, or a similar historical incident into causation without current evidence.

## Layered Investigation

Map complex workflows into useful stages rather than treating the entire system as one opaque failure.

Examples:

```text
API: DNS -> TLS -> authentication -> authorization -> application -> dependency -> response
CLI: install -> runtime -> authentication -> configuration -> remote request -> processing -> result
UI: load -> authentication -> API -> backend -> response -> rendering
```

Use successful evidence to avoid repeatedly checking stages that already appear healthy. Keep Unknown stages explicit.

## Evidence Boundaries

For important evidence, state what was observed and avoid claiming more than the evidence establishes.

Examples:

- successful DNS resolution does not prove application processing;
- successful authentication does not prove authorization;
- a successful API call does not prove a later upload or background operation succeeded;
- a stack-trace frame shows where an error surfaced but does not automatically establish the underlying cause;
- similar tickets can suggest a hypothesis but do not prove a shared incident.

## Successful vs Failing Paths

A useful Community technique is to compare a failing workflow with a related successful workflow.

```text
Successful -> A -> B -> C -> success
Failing    -> A -> B -> C -> D -> failure
```

Inspect meaningful differences while remaining open to alternative explanations. Shared components become less suspicious when equivalent successful behavior exercises them, unless other evidence shows why the successful case differs.

## Hypothesis Discipline

When root cause is not directly established, keep a small set of plausible hypotheses. For each, summarize:

- evidence for;
- evidence against or missing;
- confidence: High, Medium, or Low;
- a useful validation step when needed.

Challenge obvious assumptions and avoid preserving a hypothesis simply because it was proposed first.

Do not create false numerical precision from sparse evidence.

## Authoritative Guidance

Use official documentation, compatibility matrices, release notes, known-issue pages, and official repositories when they materially help explain expected behavior, supported versions, dependencies, or known regressions.

Documentation is evidence about expected behavior. It is not direct proof of the user's root cause. Compare it with the current environment and runtime evidence.

Prefer primary/authoritative sources over community sources when both are available.

## Cause and Impact

Distinguish:

- customer symptom;
- immediate technical failure;
- underlying evidence-supported cause;
- contributing factors.

Do not infer severity from an error code or the word "blocked" alone. Use demonstrated customer/business impact, affected scope, environment, duration/frequency, security/data risk, and workaround availability.

## Safe Next Actions

Recommend checks that are relevant to the current failure stage and evidence. Avoid generic command dumps. Suggested commands should be read-only and scoped unless the user explicitly authorizes a change.

When evidence remains insufficient, say what is missing and state: **Insufficient evidence to determine the root cause.**


## New Evidence and Stopping

Incorporate new command results into the current assessment. Explain what they support, contradict, or leave unknown; revise confidence when appropriate. A useful validation check should distinguish plausible explanations. Stop when the cause is established, the requested scope is met, evidence is unavailable, checks become repetitive, or further action needs another owner or authorization. Report the remaining gap and exact next evidence.
