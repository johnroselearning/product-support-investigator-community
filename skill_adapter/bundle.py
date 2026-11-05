"""Explicit public skill bundle shared by packaging and MCP; no code execution."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "product-support-investigator"
BASE_URI = f"skill://{NAME}/"
SKILL_URI = BASE_URI + "SKILL.md"
# Paths are relative to the skill root, never supplied by a client.
FILES = (
    "SKILL.md", "COMMUNITY.md",
    "references/investigation-methodology.md",
    "references/api-error-investigation.md",
    "references/authentication-investigation.md",
    "references/webhook-investigation.md",
    "references/escalation-framework.md",
    "references/evidence-providers.md", "references/grafana.md", "references/github.md",
    "references/workflows.md",
    "references/reporting.md",
    "scripts/grafana_evidence.py",
    "providers/__init__.py", "providers/evidence.py", "providers/grafana.py",
)


def read_bundle(root: Path = ROOT) -> dict[str, bytes]:
    """Fail closed on missing/nonregular files or symlinked bundle components."""
    root = root.resolve(strict=True)
    result = {}
    for name in FILES:
        path = root
        for part in Path(name).parts:
            path = path / part
            if path.is_symlink():
                raise ValueError(f"Symlink in skill bundle: {name}")
        if not path.is_file() or not path.resolve().is_relative_to(root):
            raise ValueError(f"Missing or invalid skill file: {name}")
        result[name] = path.read_bytes()
    return result
