# Publishing Community

The root `SKILL.md` is authoritative. Package entry points and the self-contained Forge prompt must preserve the Community workflow and report contract. Run `python3 scripts/validate_skill.py` and review all examples before release.

Publish the reviewed source into a new repository whose default branch is `main`. Configure its clone URL in installation instructions; do not use another edition's repository URL. The Claude marketplace uses a relative source so it resolves to this Community package.

For a source-only release, copy the reviewed files without `.git`, dependencies, credentials, or generated output, then initialize a new repository. Review and approve the final content before publishing. No publication is implied by validation.

For Forge/Rovo, copy `manifest.yml.example` to the ignored `manifest.yml`, register your own app identity, install dependencies, and run Forge lint. Review scopes and module schema against current official Atlassian documentation before explicitly deploying and installing. This repository does not claim deployment or installation.
