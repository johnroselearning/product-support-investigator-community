# Publishing Community

## Codex and Claude distribution

Repository: `johnroselearning/product-support-investigator-community`

The plugin is named `product-support-investigator`; its repository marketplace is named `support-investigator`. The repository contains the Claude marketplace and plugin manifests together with the canonical methodology and platform adapters.

### Claude Code: install from the GitHub-hosted community marketplace

The supported community distribution path for this repository is its public GitHub-hosted Claude Code marketplace.

Add the marketplace:

```bash
claude plugin marketplace add johnroselearning/product-support-investigator-community
```

Install Product Support Investigator:

```bash
claude plugin install product-support-investigator@support-investigator
```

During v0.1.0 release preparation, the marketplace was successfully discovered as `support-investigator`, the plugin was recognized as `product-support-investigator@support-investigator`, and the package passed:

```bash
claude plugin validate . --strict
```

These checks validate the manifest/distribution path. They do **not** establish runtime investigation quality. Runtime behavior has not yet been independently tested with an active Claude subscription.

The marketplace installs the whole repository-root plugin. Do not distribute only the thin `skills/product-support-investigator/SKILL.md` entry point because it depends on the canonical root methodology and supporting files.

For current marketplace hosting and distribution rules, use Anthropic's Claude Code plugin marketplace documentation.

### Codex / ChatGPT

The repository also contains Codex-oriented packaging and a portable skill entry point. Codex/ChatGPT installation varies by supported product surface and workspace configuration. Prefer the current product UI or supported plugin/skill installation flow rather than documenting unverified CLI commands.

### Build an upload archive

From the repository root:

```bash
python3 scripts/validate_skill.py
claude plugin validate . --strict
python3 scripts/package_plugin.py
```

The archive is written to `dist/product-support-investigator-0.1.0.zip` (the filename follows the plugin version). It includes the plugin manifests, skills, canonical methodology, references, examples, license, and Community scope. Forge deployment files and local settings are excluded.

Manifest validation does not test investigation quality. Test the packaged skill in a clean supported runtime before making runtime-quality claims.

### Suggested listing copy

- Name: Product Support Investigator — Community Edition
- Category: Productivity
- Short description: Evidence-first investigation of technical customer and product issues.
- Description: Investigate API failures, authentication issues, webhooks, integrations, performance problems, and regressions using available evidence. Separate facts from inference, compare successful and failing paths, rank competing hypotheses, and identify the next useful check. No specific monitoring or ticketing integration is required. Includes Atlassian Forge guidance; deploying the separate Forge/Rovo app is optional.
- Starter prompt: Investigate this HTTP 500 using the evidence below. Separate observed facts, inferences, and unknowns, then rank likely causes and identify the next discriminating check.

## Source and Forge releases

The root `SKILL.md` is authoritative. Package entry points and the self-contained Forge prompt must preserve the Community workflow and report contract. Run `python3 scripts/validate_skill.py` and review all examples before release.

Publish the reviewed source into a new repository whose default branch is `main`. Configure its clone URL in installation instructions; do not use another edition's repository URL. The Claude marketplace uses a relative source so it resolves to this Community package.

For a source-only release, copy the reviewed files without `.git`, dependencies, credentials, or generated output, then initialize a new repository. Review and approve the final content before publishing. No publication is implied by validation.

For Forge/Rovo, copy `manifest.yml.example` to the ignored `manifest.yml`, register your own app identity, install dependencies, and run Forge lint. Review scopes and module schema against current official Atlassian documentation before explicitly deploying and installing. This repository does not claim deployment or installation.
