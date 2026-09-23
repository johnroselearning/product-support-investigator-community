# Publishing Community

## Codex and Claude distribution

Repository: https://github.com/johnroselearning/product-support-investigator-community

The plugin is named `product-support-investigator`; its repository marketplace is named `support-investigator`. Both platform manifests are already included. A GitHub install and a public directory listing are separate distribution routes. Validation does not establish that either directory has approved this plugin.

### Install from GitHub

In Claude Code, run:

```text
/plugin marketplace add johnroselearning/product-support-investigator-community
/plugin install product-support-investigator@support-investigator
```

For a Codex CLI that supports `codex plugin`, run:

```bash
codex plugin marketplace add https://github.com/johnroselearning/product-support-investigator-community.git
codex plugin install product-support-investigator@support-investigator
```

Check `codex plugin --help` first. The installed Snap CLI checked during preparation did not support these subcommands. Use a current compatible Codex installation or the app's plugin import flow. Start a new task after installation and ask it to use Product Support Investigator with one of the bundled examples.

The marketplace installs the whole plugin. Do not distribute just the thin `skills/product-support-investigator/SKILL.md` entry point: it depends on the root methodology and supporting files.

### Build an upload archive

From the repository root:

```bash
python3 scripts/validate_skill.py
claude plugin validate .claude-plugin/plugin.json
claude plugin validate .
python3 scripts/package_plugin.py
```

The archive is written to `dist/product-support-investigator-0.1.0.zip` (the filename follows the Codex manifest version). It includes both plugin manifests, both skills, the canonical methodology, references, examples, license, Community scope, and optional Grafana Python provider/CLI. Forge deployment files and local settings are excluded. Test the archive's skills in a clean session before submitting; manifest validation alone does not test investigation quality.

### Submit to OpenAI's public directory

Open the [plugin submission portal](https://platform.openai.com/plugins), create a **Skills only** submission, and upload the archive. Complete the listing and testing fields, resolve scan findings, and submit for review. Publication requires the portal's approval process.

Publisher-owned materials still needed: verified developer identity, logo, website/support/privacy/terms URLs, country availability, and policy attestations. Prepare five positive and three negative test cases with expected outcomes. Existing examples and `tests/cases.json` provide source material; do not describe unevaluated cases as passing.

Sources: [OpenAI submission requirements](https://developers.openai.com/plugins/deploy/submission) and [Claude plugin archive import](https://developers.openai.com/plugins/guides/submit-claude-plugin).

### Submit to Claude's public community marketplace

Use the [Claude Console submission form](https://platform.claude.com/plugins/submit) with this repository and the plugin at its root. Team/Enterprise administrators can also use the [organization submission form](https://claude.ai/admin-settings/directory/submissions/plugins/new). Complete the form's publisher details and submit for review.

Approved third-party submissions go to `claude-community`. Anthropic's `claude-plugins-official` catalog is separately curated; the form does not guarantee placement there. See [Claude's submission documentation](https://code.claude.com/docs/en/plugins#submit-your-plugin-to-the-community-marketplace).

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
