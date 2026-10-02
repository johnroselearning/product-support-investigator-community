# Atlassian Rovo Adapter Source

The self-contained deployed prompt is generated at `../../forge-app/prompts/investigator.md` by `../../scripts/sync_skill.py` from the canonical root `SKILL.md`, its supporting Markdown files, `../compliance-gate.txt`, and `../rovo-adapter.txt`.

The compliance gate precedes all investigation instructions. The platform adapter supplies Jira action selection and permissions. Do not maintain a separate investigation methodology here.
