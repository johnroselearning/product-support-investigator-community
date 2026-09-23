# Claude Adapter

Apply the repository root `SKILL.md` as the canonical, vendor-neutral Product Support Investigator Community workflow. Also apply `docs/INVESTIGATION_METHOD.md`.

Claude-specific tool and permission handling belongs here; preserve the Community evidence model, Observed/Inferred/Unknown separation, successful-vs-failing comparison, basic hypothesis assessment, customer-safe communication, escalation logic, and read-only default.

During active troubleshooting, treat each meaningful command or tool result as new evidence. Reassess what it supports or weakens before recommending another relevant safe check. Avoid generic command dumps and do not require a particular monitoring or ticketing integration.

For optional telemetry, follow the repository root `references/evidence-providers.md` contract. Discover tools exposed by the host, inspect their read-only capabilities, and query only to answer a specific investigation question. For Grafana, load `references/grafana.md`; an existing read-only MCP tool or the optional `scripts/grafana_evidence.py` CLI can acquire evidence. No integration is required. Never put credentials in tool arguments or model context.
