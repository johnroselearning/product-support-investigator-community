# Investigation reporting

Load for a full report or extended customer update. Short updates and sparse investigations use the core response; engineering handoffs use `references/escalation-framework.md`.

Adapt output depth to the problem. Do not include empty sections only to satisfy a template.

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

Choose sections for the evidence and requested audience. Mark useful but unresolved fields Unknown; omit irrelevant sections. The core rules for evidence, read-only commands, confidentiality, and demonstrated-impact severity apply to every report.

For an engineering handoff, use the extended template in `references/escalation-framework.md`. For customer communication, include what is known, what remains under investigation, supported impact/workaround, and the next meaningful action or update criterion. Keep internal technical detail in the handoff.
