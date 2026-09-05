#!/usr/bin/env python3
from pathlib import Path
import re, sys, json

root = Path(__file__).resolve().parents[1]
skill = root / "SKILL.md"
required = [
    root / "references" / "investigation-methodology.md",
    root / "references" / "api-error-investigation.md",
    root / "references" / "authentication-investigation.md",
    root / "references" / "webhook-investigation.md",
    root / "references" / "escalation-framework.md",
    root / "agents" / "openai.yaml",
    root / "tests" / "cases.json",
]

errors = []
if not skill.exists():
    errors.append("SKILL.md missing")
else:
    text = skill.read_text()
    if not text.startswith("---\n"):
        errors.append("SKILL.md frontmatter missing")
    if "name: product-support-investigator" not in text:
        errors.append("skill name mismatch")
    if "description:" not in text:
        errors.append("description missing")
    if len(text.splitlines()) > 500:
        errors.append("SKILL.md exceeds 500 lines")

for path in required:
    if not path.exists():
        errors.append(f"Missing: {path.relative_to(root)}")

try:
    cases = json.loads((root / "tests" / "cases.json").read_text())
    if len(cases) < 10:
        errors.append("Expected at least 10 evaluation cases")
except Exception as e:
    errors.append(f"Invalid tests/cases.json: {e}")

if errors:
    print("INVALID")
    for e in errors:
        print("-", e)
    sys.exit(1)

print("VALID")
print("Skill:", root.name)
print("SKILL.md lines:", len(skill.read_text().splitlines()))
print("Evaluation cases:", len(cases))
