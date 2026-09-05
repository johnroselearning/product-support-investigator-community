# Atlassian Forge / Rovo adapter

This directory packages Product Support Investigator for Atlassian Forge and Rovo without changing the platform-independent `SKILL.md` used by Codex/Claude.

The first version is deliberately small and safe:

- Rovo Agent: **Product Support Investigator**
- Read-only Jira evidence collection through Forge `asUser()`
- Issue fields, comments, changelog, linked issues, and recent same-project investigation candidates
- Evidence-first investigation prompt derived from the core skill
- Datadog and Zendesk remain optional and are not required for the agent to work
- No Jira mutation, production change, rollback, or remediation action

## Architecture

```text
Rovo / Jira user
      |
      v
Product Support Investigator (Rovo Agent)
      |
      v
investigate-jira-issue (Rovo Action)
      |
      v
Forge function -> Jira Cloud REST API asUser()
      |
      v
bounded evidence -> investigation reasoning -> report

Optional future evidence adapters:
Datadog / Zendesk / GitHub / Grafana / other systems
```

The root `SKILL.md` remains the source methodology. Platform adapters should preserve its evidence model, hypothesis testing, confidence rules, read-only default, and tool-independent fallback.

## 1. Register this existing Forge app

Install the latest Forge CLI and authenticate:

```bash
npm install -g @forge/cli@latest
forge login
```

This repository already contains a Forge source tree. Do **not** run `forge create` inside it. From `forge-app/`, create the local manifest and register this source tree once:

```bash
cp manifest.yml.example manifest.yml
forge register product-support-investigator
```

`forge register` writes the Atlassian App ID into `manifest.yml` and creates development, staging, and production environments.

> Important: do not run `forge register` repeatedly for the same installation unless you intentionally want a new Atlassian App ID. Registering again creates a separate app identity.

The local `manifest.yml` represents your registered app. Keep `manifest.yml.example` as the reusable template for other developers.

## 2. Install dependencies and validate

From `forge-app/`:

```bash
npm install
forge lint
```

The example manifest uses the current Forge Node runtime:

```yaml
app:
  runtime:
    name: nodejs24.x
```

The Forge function lives at `src/index.js`, so the manifest handler is intentionally:

```yaml
handler: index.investigateJiraIssue
```

Do not prefix the handler with `src/`; Forge already resolves function handlers relative to the `src` directory.

## 3. Deploy to development

```bash
forge deploy --environment development
forge install --environment development --site <your-site>.atlassian.net --product Jira
```

If the installation already exists and permissions/modules changed:

```bash
forge install --upgrade --environment development --site <your-site>.atlassian.net --product Jira
```

Then open Rovo and invoke **Product Support Investigator**. Ask it to investigate an issue such as `SUP-1428`, or invoke it from Jira context when available.

## 4. Share with another Atlassian customer

Community users may copy the source and register their own app. For a hosted evaluation, share a tested production installation. For direct/private distribution, deploy a tested version to Forge production and enable **Sharing** in Atlassian Developer Console.

```bash
forge deploy --environment production
```

Then in Atlassian Developer Console:

1. Open **Product Support Investigator**.
2. Open **Distribution**.
3. Under **Distribution controls**, choose **Edit**.
4. Select **Sharing**.
5. Fill in the requested app details and save.
6. Select **Jira** as the Atlassian app for installation.
7. Copy the generated installation link.

Send that link to the customer's Jira/site administrator. They choose their Atlassian site, review the requested permissions, and install the app. After installation, Product Support Investigator is available through Rovo on that customer's site, subject to Rovo availability and each user's Jira permissions.

This direct installation-link distribution is intended for internal use and pre-Marketplace testing. It is not a public Marketplace listing.

See [`PRIVATE_DISTRIBUTION.md`](PRIVATE_DISTRIBUTION.md) for the customer-facing installation and release workflow.

## What the Jira action returns

The action uses the current user's Jira permissions and returns bounded evidence:

- selected issue fields
- up to 100 comments
- up to 100 changelog entries
- Jira issue links
- up to 10 recently updated issues from the same project as investigation candidates

Recent project issues are **not** asserted to be related. The agent must establish a meaningful correlation before using them as supporting evidence.

The response explicitly marks Datadog and Zendesk as `not configured`. Their absence must not stop the investigation.

## Permissions

The example manifest currently requests:

```yaml
permissions:
  scopes:
    - read:jira-work
    - read:chat:rovo
```

The Jira calls use `api.asUser()`, so Jira Browse Projects and issue-security permissions still constrain what evidence can be read.

Before production or Marketplace publication, run `forge lint`, review the scopes produced/required by the current Forge CLI, and verify the current Atlassian Rovo/Forge requirements.

## Datadog and Zendesk later

Do not make these mandatory dependencies. Add them as separate authenticated evidence actions so the Rovo agent can use them when configured and continue with Jira/user-provided evidence when they are absent.

Recommended future actions:

```text
query-datadog-evidence   (optional)
query-zendesk-evidence   (optional)
```

Each adapter should return source metadata, timestamps/identifiers, truncation/availability information, and raw evidence needed for correlation. It should not independently declare a root cause.

## Production roadmap

1. Validate this Jira-only Rovo agent in a development Atlassian site.
2. Add tests/fixtures for Jira evidence normalization.
3. Deploy a tested build to production and enable direct Sharing for beta customers.
4. Add an optional Jira issue panel only if it improves the workflow; keep the Rovo agent usable without it.
5. Add Datadog as an optional evidence adapter.
6. Add Zendesk as an optional evidence adapter.
7. Add Marketplace privacy, security, support, licensing, and listing material only after the core investigation behavior is validated.

## Atlassian documentation

Forge and Rovo schemas evolve, so verify the current Atlassian documentation when deploying:

- Forge getting started: https://developer.atlassian.com/platform/forge/getting-started/
- Forge deployment: https://developer.atlassian.com/platform/forge/cli-reference/deploy/
- Forge distribution/sharing: https://developer.atlassian.com/platform/forge/distribute-your-apps/
- Rovo agent module: https://developer.atlassian.com/platform/forge/manifest-reference/modules/rovo-agent/
- Rovo action module: https://developer.atlassian.com/platform/forge/manifest-reference/modules/rovo-action/
- Jira scopes: https://developer.atlassian.com/platform/forge/manifest-reference/scopes-product-jira/
