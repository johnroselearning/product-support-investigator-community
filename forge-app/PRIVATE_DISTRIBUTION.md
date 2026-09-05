# Private Distribution — Product Support Investigator for Atlassian Rovo

This guide explains how to release Product Support Investigator to selected Jira/Rovo customers without publishing it on Atlassian Marketplace.

## Who this is for

There are two roles:

- **App owner/developer** — builds, tests, deploys, and enables sharing.
- **Customer Jira/site administrator** — receives an installation link and installs the app on their own Atlassian site.

End users do not need the GitHub repository, Forge CLI, Node.js, or the source code.

## Distribution model

```text
Product Support Investigator source
              |
              v
     Forge production deployment
              |
              v
 Atlassian Developer Console Sharing
              |
              v
      Installation link
              |
              v
       Customer site admin
              |
              v
     Customer Atlassian site
              |
              v
             Rovo
              |
              v
  Product Support Investigator
```

Each customer installs the Forge app into their own Atlassian site. The Jira action runs using Forge and the current user's Jira permissions. Installing the app on Customer A's site does not give Customer B access to Customer A's Jira data.

## Part A — App owner release checklist

### 1. Test development first

Before sharing the app, validate the development installation with representative Jira issues.

Check the current installation:

```bash
forge install list
```

Test at least:

- issue retrieval
- comments
- changelog/timeline evidence
- linked issues
- related-issue candidates
- missing-data behavior
- insufficient-evidence behavior
- user permission boundaries

The agent must remain read-only and must not claim a root cause without sufficient evidence.

### 2. Validate the app

From `forge-app/`:

```bash
npm install
forge lint
```

Resolve lint errors before releasing. Review warnings rather than automatically ignoring them.

### 3. Deploy to production

When the tested version is ready:

```bash
forge deploy --environment production
```

Development and production are separate Forge environments. A successful development deployment does not automatically publish or update production.

### 4. Enable Sharing

Open the Atlassian Developer Console and select **Product Support Investigator**.

Go to **Distribution** and edit **Distribution controls**. Select **Sharing**, complete the requested app information, select Jira as the installation product, and save the configuration.

Atlassian then provides an installation link for the production app.

Do not publish API tokens, Forge credentials, customer credentials, or other secrets in the repository or installation documentation.

### 5. Send the installation link

Send the generated link only to the Jira/site administrator for the customer that is evaluating the app.

Suggested message:

> Product Support Investigator is a read-only Rovo agent for evidence-first investigation of Jira support incidents. Please open the installation link as an Atlassian site administrator, select the Jira site where you want to evaluate it, review the requested permissions, and approve the installation. After installation, open Rovo and select Product Support Investigator from the available agents.

## Part B — Customer self-service installation

### Requirements

The customer needs:

- an Atlassian Cloud site with Jira
- Rovo available/enabled for the intended users
- a Jira/site administrator who can approve the app installation
- users with permission to view the Jira issues they want the agent to investigate

The customer does **not** need:

- this GitHub repository
- Forge CLI
- Node.js
- the Product Support Investigator source code
- access to the developer's Atlassian site

### Installation

1. Open the private installation link supplied by the Product Support Investigator developer.
2. Sign in to Atlassian if prompted.
3. Choose the intended Atlassian/Jira site.
4. Review the app permissions.
5. Approve/install the app.
6. Open Jira and Rovo Chat.
7. Browse/select **Product Support Investigator**.
8. Open a Jira issue the user is allowed to read.
9. Ask the agent to investigate the issue.

Example requests:

```text
Investigate the current Jira issue.
```

```text
What evidence supports the likely root cause of SUP-1428?
```

```text
What information is missing before we can determine the root cause?
```

## Permissions and data boundaries

The current Jira integration is read-only. It requests Jira/Rovo read scopes and calls Jira through Forge `api.asUser()`.

This means the current user's Jira permissions continue to matter. If a user cannot view an issue because of Jira project or issue-security permissions, the agent should not be treated as a mechanism for bypassing that restriction.

Datadog and Zendesk are optional and are not required for the Jira-only version.

## Updating beta customers

When a new version is ready:

```bash
forge deploy --environment production
```

If the update changes permissions or otherwise requires an installation upgrade, follow the Forge CLI/Developer Console instructions for upgrading installations and customer consent. Do not assume every deployment can be applied silently.

## Removing the app

A customer administrator can uninstall the app from their Atlassian site. The app owner can inspect installations with Forge/Developer Console as permitted by Atlassian's current tooling.

## Private sharing vs Marketplace

Private/direct sharing and Marketplace publication are different stages.

**Private sharing** is suitable for controlled beta testing and selected customers. Customers install using the installation link supplied by the developer.

**Marketplace publication** is the later path for public discovery, commercial listing, broader installation, and Marketplace-specific security/privacy/support/licensing requirements.

Recommended progression:

```text
Development test
      -> production deployment
      -> private sharing
      -> beta customers
      -> feedback/security hardening
      -> Marketplace readiness
      -> Marketplace submission
```

## Troubleshooting

### Agent is not visible

Confirm:

1. The app is installed on the same Atlassian site the user has open.
2. Rovo is available for that site/user.
3. The user is looking in Rovo's agent browser/selector.
4. The installed app version is current.
5. The Rovo agent module is present in the deployed manifest.

### Agent cannot read an issue

Check the user's Jira permissions and issue-security configuration first. The Jira action uses the current user's access rather than intentionally bypassing Jira permissions.

### Forge deployment works but installation does not

Check the target environment, requested scopes, app installation status, and current Forge CLI error output. Development, staging, and production are separate environments.

## Official Atlassian references

- Forge distribution and sharing: https://developer.atlassian.com/platform/forge/distribute-your-apps/
- Forge deployment: https://developer.atlassian.com/platform/forge/cli-reference/deploy/
- Forge environments and versions: https://developer.atlassian.com/platform/forge/environments-and-versions/
- Rovo agent module: https://developer.atlassian.com/platform/forge/manifest-reference/modules/rovo-agent/
- Rovo action module: https://developer.atlassian.com/platform/forge/manifest-reference/modules/rovo-action/
