---
name: product-support-investigator-codex
description: Codex adapter for the Community Product Support Investigator workflow.
---

# Codex Adapter

Use the repository root `SKILL.md` as the canonical Product Support Investigator Community contract. Apply `docs/INVESTIGATION_METHOD.md` for the vendor-neutral investigation method.

Use available local tools, connectors, files, and user-provided evidence; do not assume a vendor integration. Preserve Observed/Inferred/Unknown separation, evidence discipline, successful-vs-failing comparison, basic hypothesis assessment, customer-safe communication, ownership recommendation, and the read-only default.

During active troubleshooting, incorporate each meaningful command or tool result as new evidence. Reassess what is known, what remains unknown, and which relevant safe check would help validate the current hypothesis or failure stage. Avoid generic command dumps.

For optional telemetry, follow the repository root `references/evidence-providers.md` contract. Discover tools exposed by the host, inspect their read-only capabilities, and query only to answer a specific investigation question. For Grafana, load `references/grafana.md`; an existing read-only MCP tool or the optional `scripts/grafana_evidence.py` CLI can acquire evidence. No integration is required. Never put credentials in tool arguments or model context.
