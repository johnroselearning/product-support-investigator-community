"""Explicit public skill bundle shared by packaging and MCP; no code execution."""
from pathlib import Path
import re

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
    "references/reporting.md", "references/workflows.md", "references/github.md",
    "references/evidence-providers.md", "references/grafana.md",
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


def reference_errors(bundle: dict[str, bytes], *, markdown_only=False) -> list[str]:
    """Check local instruction paths in an isolated install, without host files.

    Backtick paths follow the skill's root-relative convention; Markdown links
    resolve beside their document. Rovo carries Markdown only, not Python helpers.
    """
    errors = []
    for name, data in bundle.items():
        if not name.endswith(".md"):
            continue
        text = data.decode("utf-8")
        paths = re.findall(r'`((?:references|scripts|providers)/[^`]+\.(?:md|py)|COMMUNITY\.md)`', text)
        links = re.findall(r'\]\(([^)]+)\)', text)
        for target, relative in [(p, False) for p in paths] + [(p, True) for p in links]:
            if "://" in target or target.startswith("#"):
                continue
            target = target.split("#", 1)[0]
            if markdown_only and not target.endswith(".md"):
                continue
            path = Path(name).parent / target if relative else Path(target)
            # References in these bundles have no traversal or absolute paths.
            if path.is_absolute() or ".." in path.parts or path.as_posix() not in bundle:
                errors.append(f"{name}: unresolved reference {target}")
    return errors
