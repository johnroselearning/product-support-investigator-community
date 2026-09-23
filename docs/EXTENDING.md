# Extending to New Agents

Implementations for Codex, Claude, Atlassian Rovo, Hermes, OpenHands, Cursor, Windsurf, and other agents should treat the root `SKILL.md` as the canonical, vendor-neutral contract. Only the integration layer should vary: prompt loading, tool schemas, authentication, permissions, and result serialization.

Adapters must preserve evidence IDs, observed/inferred/unknown separation, confidence labels, hypothesis ranking, customer-safe output, read-only defaults, and engineering escalation quality. Add platform-specific instructions only when the platform has a real capability or constraint to document.

Evidence providers implement [the common acquisition contract](../references/evidence-providers.md). Keep authentication/transport/query normalization in providers and inference, ledger significance, and next checks in the investigator. Forge telemetry requires a separately authorized backend; do not reuse Jira access as Grafana authorization.
