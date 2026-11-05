"""Conditional, non-recursive context from validated structured work items.

No keyword/LLM intent classifier. Retrieved text never selects references.
Portable hosts choose symptom playbooks directly from SKILL.md as needed.
"""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def selected_references(state):
    if state.workflow in ("general_question", "needs_clarification"):
        return {}
    sections = {}
    if state.selected_skill:
        sections["SKILL.md"] = ("Investigation Principles", "Evidence Model", "Root Cause Assessment")
    if state.workflow == "psi_maintenance":
        sections["references/workflows.md"] = ("Optional scoped capabilities", "Evidence and maintenance handover")
    if (state.understanding.get("external_evidence_allowed") and state.evidence_needs
            and state.understanding.get("route") != "investigate_supplied"):
        sections["references/evidence-providers.md"] = ("Trust and privacy", "Retrieval efficiency")
    return sections


def load_context(state):
    result = {}
    for name, headings in selected_references(state).items():
        text = (ROOT / name).read_text()
        excerpts = {}
        for heading in headings:
            marker = "## " + heading + "\n"
            if marker not in text:
                raise ValueError(f"Missing context section: {name}: {heading}")
            excerpts[heading] = text.split(marker, 1)[1].split("\n## ", 1)[0]
        result[name] = {"sha256": hashlib.sha256(text.encode()).hexdigest(), "sections": excerpts}
    return result or None
