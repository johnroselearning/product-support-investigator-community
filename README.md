# Product Support Investigator — Community Edition

Free and open-source, evidence-first AI investigation skill for technical customer and product issues.

The Community Edition helps support engineers conduct solid, vendor-independent investigations using the evidence available. It does **not** require Datadog, Zendesk, Jira, GitHub, Grafana, logs, or any other specific integration.

It can help investigate API failures, application errors, authentication problems, webhooks, integrations, payments, data mismatches, performance issues, regressions, deployments, and technical escalations while clearly separating observed facts, inference, and unknowns.

See [`COMMUNITY.md`](COMMUNITY.md) for the Community Edition scope and feature boundary, [`CHANGELOG.md`](CHANGELOG.md) for release history, and [`LICENSE`](LICENSE) for licensing.

For the Jira/Rovo distribution, see [`PRIVACY.md`](PRIVACY.md), [`DATA_HANDLING.md`](DATA_HANDLING.md), [`SECURITY.md`](SECURITY.md), [`TERMS.md`](TERMS.md), and the [`MARKETPLACE.md`](MARKETPLACE.md) submission guide.

The root [`SKILL.md`](SKILL.md) is the canonical investigation methodology used by all platform adapters.

For Codex and Claude installation commands, packaging, and distribution guidance, see [Publish and install](docs/PUBLISHING.md).

## Install in Claude Code

Product Support Investigator is distributed through the public GitHub-hosted `support-investigator` community marketplace.

Add the marketplace and install the plugin:

```bash
claude plugin marketplace add johnroselearning/product-support-investigator-community
claude plugin install product-support-investigator@support-investigator
```

The marketplace manifest has passed `claude plugin validate . --strict`, GitHub marketplace discovery has been verified, and the plugin installation path has been verified. Runtime investigation behavior has not yet been independently tested with an active Claude subscription.

Advanced commercial capabilities may be offered separately. Community Edition remains independently useful.

## Choose how you want to use it

There are three common ways to use this project:

1. **Use the skill in Codex / ChatGPT or Claude** — easiest if you want an AI investigator while working with files, code, logs, or support evidence.
2. **Use the Atlassian Rovo agent in Jira** — easiest for Jira users after the Forge app has been installed on their Atlassian site.
3. **Deploy your own Forge/Rovo copy** — for developers or teams that want to install Product Support Investigator in their own Jira site.

You do not need to use all three.

---

# 1. Use Product Support Investigator in Codex / ChatGPT

The repository contains a plugin manifest and reusable skills for Codex-compatible environments.

If your ChatGPT or Codex workspace already has Product Support Investigator installed as a plugin, you do not need to clone this repository. Open the plugin/skill and ask it to investigate your issue.

Example request:

```text
Use Product Support Investigator to investigate this issue.

Error: POST /api/v1/checkout/process returns HTTP 500
Environment: production
Approximate time: 14:32 UTC
Request ID: abc-123

I do not have application logs. Investigate with the information available and tell me what evidence I should collect next.
```

The investigator should continue with partial evidence instead of requiring a specific monitoring or ticketing tool.

## Local repository setup for developers

Set `COMMUNITY_REPOSITORY_URL` to the clone URL of the published Community repository. The public default branch is `main`. Then run:

```bash
git clone "$COMMUNITY_REPOSITORY_URL" product-support-investigator
cd product-support-investigator
```

If you already cloned it earlier:

```bash
cd product-support-investigator
git checkout main
git pull origin main
```

For a published release, prefer the corresponding release tag when you need a reproducible version.

The important files are:

- `SKILL.md` — canonical investigation methodology
- `COMMUNITY.md` — Community Edition scope and feature boundary
- `CHANGELOG.md` — release history
- `skills/product-support-investigator/SKILL.md` — portable skill entry point
- `skills/atlassian-forge/SKILL.md` — Atlassian/Forge-specific guidance
- `codex/` — Codex adapter
- `claude/` — Claude adapter
- `references/` — issue-specific investigation playbooks
- `examples/` — example investigations

> Local plugin installation commands can vary by the Codex/ChatGPT surface and workspace configuration. If the plugin is published in your workspace or Plugin Directory, prefer installing it through the product UI rather than relying on a machine-specific binary path.

---

# 2. Use Product Support Investigator in Jira / Atlassian Rovo

This repository **does include a Forge/Rovo app** under [`forge-app/`](forge-app/README.md).

A normal Jira user does not need to run Forge commands. The Atlassian site administrator installs the app once. After installation, users can open Rovo and use the **Product Support Investigator** agent.

Example:

```text
Investigate SUP-1428.

Use the Jira issue, comments, changelog, linked issues, and any other available evidence.
Do not assume a root cause if the evidence is insufficient.
```

The Jira adapter is intentionally read-only. It can collect bounded Jira evidence but should not modify issues, deploy code, roll back production, or contact customers without explicit human authorization.

If your organization gives you an Atlassian installation link, open the link, choose the Jira site, review the requested permissions, and install the app. No terminal commands are required for normal users.

---

# 3. Deploy your own Jira / Rovo copy

This section is for the person setting up the app for a Jira site.

## What you need first

You need:

- a computer with Git installed;
- Node.js installed;
- an Atlassian account that can use Forge;
- access to an Atlassian Jira Cloud site;
- permission to install apps on that site.

Check Git and Node.js:

```bash
git --version
node --version
npm --version
```

If those commands print version numbers, continue.

## Step 1 — Download the project

Set `COMMUNITY_REPOSITORY_URL` to the published Community repository clone URL, then run:

```bash
git clone "$COMMUNITY_REPOSITORY_URL" product-support-investigator
cd product-support-investigator/forge-app
```

If you already have the repository:

```bash
cd product-support-investigator
git checkout main
git pull origin main
cd forge-app
```

For a published release, prefer the corresponding release tag when you need a reproducible version.

## Step 2 — Install the Atlassian Forge CLI

Run:

```bash
npm install -g @forge/cli@latest
forge --version
forge login
```

`forge login` opens the Atlassian authentication flow. Sign in with the Atlassian account that should own or manage the Forge app.

## Step 3 — Prepare the Forge manifest

This repository provides a reusable manifest template.

From the `forge-app` directory run:

```bash
cp manifest.yml.example manifest.yml
```

You should now have:

```text
forge-app/manifest.yml
```

Do **not** manually replace `REPLACE_WITH_FORGE_APP_ID` before registration. The next command registers this source tree and writes the new Atlassian App ID into `manifest.yml`.

## Step 4 — Register your Forge app

Run this once:

```bash
forge register product-support-investigator
```

If Forge asks you to choose a Developer Space, select the Developer Space you want to own this app.

If your organization gave you a specific Developer Space ID, you can instead use:

```bash
forge register product-support-investigator --developer-space-id YOUR_DEVELOPER_SPACE_ID
```

Replace only:

```text
YOUR_DEVELOPER_SPACE_ID
```

with the real Developer Space ID.

> Do not repeatedly run `forge register` for the same setup. Registering again creates or associates a different app identity and can disconnect the source tree from the previous Forge environments and stored configuration.

## Step 5 — Install project dependencies

Still inside `forge-app`, run:

```bash
npm install
```

## Step 6 — Validate the app

Run:

```bash
forge lint
```

If `forge lint` succeeds, continue.

If `forge lint` times out but deployment later succeeds, do not automatically assume the source code is invalid. Capture the verbose output with:

```bash
forge lint --verbose
```

and investigate the lint-specific failure path separately.

## Step 7 — Deploy to the development environment

Run:

```bash
forge deploy --environment development
```

## Step 8 — Install it on your Jira site

Use this command:

```bash
forge install --environment development --site YOUR-SITE.atlassian.net --product Jira
```

Example:

```bash
forge install --environment development --site example-company.atlassian.net --product Jira
```

Replace only:

```text
YOUR-SITE
```

with the first part of your Atlassian site address.

For example, if your Jira URL is:

```text
https://example-company.atlassian.net
```

use:

```bash
forge install --environment development --site example-company.atlassian.net --product Jira
```

If the app is already installed and you changed permissions or modules, run:

```bash
forge install --upgrade --environment development --site YOUR-SITE.atlassian.net --product Jira
```

## Step 9 — Open Rovo and test the agent

Open your Jira site and open Rovo.

Look for:

```text
Product Support Investigator
```

Then try:

```text
Investigate SUP-1428.
```

or:

```text
Investigate this Jira issue. Separate observed facts, inference, and unknowns. Compare successful and failing paths before deciding the likely cause.
```

The agent can retrieve Jira evidence such as issue fields, comments, changelog, linked issues, and bounded recent same-project candidates through the included read-only Forge action.

---

# Deploy to production

Development installation should be tested first.

When you are satisfied with the development version, deploy the same app to Forge production:

```bash
cd product-support-investigator/forge-app
forge deploy --environment production
```

If you also want to install the production environment on your own Jira site, run:

```bash
forge install --environment production --site YOUR-SITE.atlassian.net --product Jira
```

If a production installation already exists and needs permission/module upgrades:

```bash
forge install --upgrade --environment production --site YOUR-SITE.atlassian.net --product Jira
```

---

# Share the Rovo agent with another Jira customer

For private/beta distribution, deploy a tested production build first:

```bash
cd product-support-investigator/forge-app
forge deploy --environment production
```

Then use the Atlassian Developer Console:

1. Open the Product Support Investigator app.
2. Open **Distribution**.
3. Open **Distribution controls**.
4. Enable **Sharing**.
5. Complete the requested app details.
6. Select Jira as the Atlassian product.
7. Copy the generated installation link.
8. Send that link to the customer's Jira administrator.

The customer administrator installs the app using the link. Normal users do not need the source code or Forge CLI.

For more detail see [`forge-app/PRIVATE_DISTRIBUTION.md`](forge-app/PRIVATE_DISTRIBUTION.md).

---

# What the Jira integration can read

The current Forge/Rovo action is read-only and uses the current Jira user's permissions.

It can return bounded evidence including:

- Jira issue fields;
- comments;
- changelog entries;
- linked Jira issues;
- recently updated same-project issues as investigation candidates.

Recently updated issues are **not automatically treated as related incidents**. The investigator must establish evidence linking them before using them to support a hypothesis.

The example manifest currently requests:

```yaml
permissions:
  scopes:
    - read:jira-work
    - read:chat:rovo
```

Datadog and Zendesk remain optional. Their absence must not prevent the investigation.

---

# Common troubleshooting commands

Check Forge CLI version:

```bash
forge --version
```

Check whether you are in the correct directory:

```bash
pwd
ls
```

You should see files such as:

```text
manifest.yml
package.json
src
prompts
```

Validate with detailed output:

```bash
forge lint --verbose
```

Deploy with detailed output:

```bash
forge deploy --environment development --verbose
```

See current app installations:

```bash
forge install list
```

If you previously configured a Forge CLI proxy and no longer need it:

```bash
forge settings delete proxy
```

Do not delete proxy settings unless you know that your environment does not require them.

---

# Repository structure

```text
product-support-investigator/
├── SKILL.md                              # canonical investigation methodology
├── COMMUNITY.md                          # Community Edition scope and boundary
├── CHANGELOG.md                          # release history
├── PRIVACY.md                            # Jira/Rovo privacy policy
├── DATA_HANDLING.md                      # current Forge data-flow disclosure
├── SECURITY.md                           # security and vulnerability reporting
├── TERMS.md                              # distributed app terms
├── MARKETPLACE.md                        # Atlassian Marketplace submission guide
├── LICENSE                               # MIT license
├── skills/
│   ├── product-support-investigator/     # portable skill entry point
│   └── atlassian-forge/                  # Forge/Jira guidance
├── codex/                                # Codex adapter
├── claude/                               # Claude adapter
├── atlassian/                            # Atlassian adapter instructions
├── forge-app/                            # working Forge/Rovo application
│   ├── manifest.yml.example
│   ├── package.json
│   ├── prompts/
│   └── src/
├── references/                           # investigation playbooks
├── examples/                             # example investigations
├── docs/                                 # extension/publishing documentation
└── tests/                                # evaluation material
```

---

# Investigation philosophy

The core behavior across every platform is:

```text
Investigate with what you have
        ↓
Discover what available tools can provide
        ↓
Ask only for information that actually blocks progress
        ↓
Compare successful and failing paths
        ↓
Gather and correlate evidence
        ↓
Generate competing hypotheses
        ↓
Try to disprove the leading hypothesis
        ↓
Re-rank using new and negative evidence
        ↓
Confirm the deepest supported cause — or say it is still unknown
```

A missing Datadog account, Zendesk connection, Jira integration, or log file must not make the investigator unusable.

If the available evidence cannot distinguish the cause, it should say:

> **Insufficient evidence to determine the root cause.**

---

# Community / commercial boundary

Community Edition provides the public evidence-first investigation foundation described in [`COMMUNITY.md`](COMMUNITY.md). It is intended to remain independently useful for individual support engineers and teams.

Community is independently useful and requires no commercial service. Contributions should preserve the scope in `COMMUNITY.md`.

---

# Further documentation

- [`COMMUNITY.md`](COMMUNITY.md) — Community Edition scope and feature boundary
- [`CHANGELOG.md`](CHANGELOG.md) — release history
- [`SKILL.md`](SKILL.md) — canonical investigation methodology
- [`PRIVACY.md`](PRIVACY.md) — Jira/Rovo privacy policy
- [`DATA_HANDLING.md`](DATA_HANDLING.md) — Forge data handling and data flow
- [`SECURITY.md`](SECURITY.md) — security policy
- [`TERMS.md`](TERMS.md) — terms for the distributed app
- [`MARKETPLACE.md`](MARKETPLACE.md) — Marketplace listing and review checklist
- [`forge-app/README.md`](forge-app/README.md) — Forge/Rovo developer details
- [`forge-app/PRIVATE_DISTRIBUTION.md`](forge-app/PRIVATE_DISTRIBUTION.md) — private customer distribution
- [`docs/CONNECTORS.md`](docs/CONNECTORS.md) — optional connector model
- [`docs/EXTENDING.md`](docs/EXTENDING.md) — adding future platforms/connectors
- [`docs/INVESTIGATION_METHOD.md`](docs/INVESTIGATION_METHOD.md) — investigation approach
- [`docs/OUTPUT_FORMAT.md`](docs/OUTPUT_FORMAT.md) — report format
- [`docs/PUBLISHING.md`](docs/PUBLISHING.md) — publishing guidance

Forge and Rovo change over time, so check Atlassian's current Forge documentation when deploying or changing permissions.
