#!/usr/bin/env python3
"""Build a skills-only upload archive from an explicit public-file allowlist."""
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
version = json.loads((ROOT / '.codex-plugin/plugin.json').read_text())['version']
output = ROOT / 'dist' / f'product-support-investigator-{version}.zip'
files = [ROOT / name for name in (
    '.codex-plugin/plugin.json', '.claude-plugin/plugin.json',
    'SKILL.md', 'LICENSE', 'COMMUNITY.md', 'CHANGELOG.md',
)]
for directory in ('skills', 'references', 'examples'):
    files.extend(p for p in (ROOT / directory).rglob('*')
                 if p.is_file() and p.suffix in ('.md', '.yaml'))
output.parent.mkdir(exist_ok=True)
with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
    for path in sorted(files):
        if path.is_symlink():
            raise ValueError(f'Refusing symlink: {path}')
        archive.write(path, path.relative_to(ROOT))
with ZipFile(output) as archive:
    assert archive.testzip() is None
print(output)
print(f'{len(files)} files; skills, methodology, references, and examples included')
