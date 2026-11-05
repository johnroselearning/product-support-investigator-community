# Investigation reporting

Load for a full report, customer update, or engineering handoff; sparse investigations use the core response.


Adapt output depth to the problem. Do not include empty sections only to satisfy a template.

For sparse evidence, default to an interactive response: brief symptom assessment, essential context questions, one accessible next check, what to capture, and how its result narrows the next step. Keep evidence classification accurate without forcing a full ledger, severity discussion, or generic hypothesis list into the opening response. Use the fuller summary below when evidence exists or a report/escalation is requested.

For Standard investigations, use relevant sections from:

1. Executive Summary
2. Goal and Failure Stage
3. Issue Validation Status
4. Incident Classification
5. Business Impact
6. Technical Signals
7. Timeline / Last Known Success / Onset
8. Observed Facts
9. AI Inferences
10. Unknowns
11. Evidence
12. Correlations
13. Layer / Sequence Validation
14. Successful Control Paths / Differential Signals
15. Blast Radius
16. Similar Incidents / Known Issues
17. Recent Changes / Version Compatibility
18. Hypotheses
19. Root Cause Assessment
20. Risk Assessment
21. Investigation Checklist / Next Useful Check
22. Missing Evidence
23. Suggested Command or Search
24. Workaround
25. Customer Communication
26. Ownership Recommendation
27. Engineering Escalation
28. Confidence

Suggested commands must be read-only, scoped, safe, and must never request credentials or secrets.



Customer-facing updates should be accurate, concise, and safe. Include what is known, what remains under investigation, impact/workaround when supported, and the next meaningful action or update criterion.

Do not expose secrets, private links, signed URLs, unnecessary personal information, internal stack traces, or sensitive architecture details.



Distinguish customer/product failure, platform/service failure, integration failure, deployment/release failure, developer-tooling failure, local-environment failure, and observability/reporting failure.

Assess severity from demonstrated impact rather than the technical error alone. Consider production status, affected users/customers, business impact, data/security risk, duration/frequency, and workaround availability.

If impact is not established, mark severity as Unknown or Provisional.

