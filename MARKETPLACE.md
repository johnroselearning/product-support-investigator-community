# Atlassian Marketplace Submission — Product Support Investigator

This document is the working source of truth for preparing the Community Edition Jira/Rovo app for public Atlassian Marketplace distribution.

## Proposed listing

**App name:** Product Support Investigator

**Tagline:** Evidence-first AI investigation for Jira support and product incidents.

**Short description:** Investigate Jira incidents with a read-only Rovo agent that separates evidence, hypotheses, unknowns, and next investigation steps.

**Supported Atlassian product:** Jira Cloud

**Deployment:** Atlassian Forge

**Primary use cases:** technical support, product support, incident investigation, escalation analysis, evidence collection, and root-cause investigation.

## Long description

Product Support Investigator helps support and engineering teams investigate technical Jira issues without jumping directly from symptoms to an assumed root cause.

The Rovo agent gathers bounded evidence available to the requesting Jira user, including the issue, comments, changelog, linked issues, and a small set of same-project investigation candidates. It then applies the project's evidence-first investigation methodology to distinguish observed facts from hypotheses and unknowns.

The Community Edition is intentionally read-only. It does not modify Jira issues, comments, workflows, deployments, or production systems. Jira REST access runs through the current user's Forge authorization context, so Jira permissions continue to control issue visibility.

No Datadog, Zendesk, GitHub, or external monitoring integration is required. The Community Edition can work from Jira evidence alone and identify what additional evidence should be collected when Jira does not contain enough information to establish a cause.

## Key features

- Evidence-first investigation rather than premature root-cause claims.
- Rovo agent available in Jira after site installation.
- Reads issue details, comments, changelog, linked issues, and bounded same-project candidates.
- Clearly identifies missing evidence and investigation limitations.
- Uses Jira access in the requesting user's authorization context.
- Read-only Jira action; no issue mutation.
- No required Datadog, Zendesk, GitHub, or external backend.
- Open Community Edition methodology and source code.

## Suggested customer-facing trust statement

> Product Support Investigator reads Jira evidence in the requesting user's permission context. The Community Edition does not modify Jira issues and does not configure a developer-controlled external backend for Jira evidence.

Keep this statement synchronized with the implementation. Do not use it if future releases add write actions, app-level access that changes the authorization model, or external data transfer without updating the wording.

## Requested scopes and justification

### `read:jira-work`

Required to retrieve Jira issue evidence used in an investigation, including issue fields, comments, changelog, linked issues, and bounded project issue candidates.

### `read:chat:rovo`

Required for the Rovo agent experience.

No Jira write scope is requested by the current Community Edition manifest.

## Data handling references

- Privacy Policy: [`PRIVACY.md`](PRIVACY.md)
- Data handling: [`DATA_HANDLING.md`](DATA_HANDLING.md)
- Security policy: [`SECURITY.md`](SECURITY.md)
- Terms of Use: [`TERMS.md`](TERMS.md)
- Open-source license: [`LICENSE`](LICENSE)

For the Marketplace form, use public HTTPS URLs to the corresponding files on the repository's default branch after this submission-readiness change is merged.

## Support information

**Public support channel:** GitHub Issues in this repository for non-confidential problems and feature requests.

**Security reports:** GitHub Private Vulnerability Reporting when enabled, as described in `SECURITY.md`.

Before Marketplace submission, provide a monitored support email and security contact email in the Marketplace/vendor profile if Atlassian requires dedicated email fields. Do not publish an address here unless it is intended to be a long-term public support address.

## Listing assets to prepare manually

Repository changes cannot create final Marketplace screenshots from the live Atlassian UI. Capture current screenshots from the production-installed app, with test/synthetic Jira data only.

Recommended assets:

1. Rovo agent discovery/profile showing Product Support Investigator.
2. Investigation request for a synthetic Jira issue.
3. Investigation result showing evidence, hypothesis/unknown separation, and next steps.
4. Jira issue context demonstrating that the app reads evidence without modifying the issue.
5. Optional short demo video using synthetic data.

Do not include customer names, real production incidents, credentials, private URLs, email addresses, access tokens, or confidential logs in Marketplace media.

## Release notes — proposed first Marketplace release

### 0.1.0 — Initial Community Edition Marketplace release

- Adds Product Support Investigator as an Atlassian Rovo agent for Jira Cloud.
- Adds read-only Jira evidence collection through Forge.
- Retrieves issue details, comments, changelog, linked issues, and bounded same-project candidates.
- Uses evidence-first investigation guidance and explicitly separates correlation from causation.
- Requires no external monitoring or ticketing integration.

## Pre-submission technical checks

Run from `forge-app/` against the exact commit intended for release:

```bash
npm ci
forge lint
npm audit --omit=dev --audit-level=high
forge deploy --environment production
```

Confirm the production installation works on a Jira Cloud site and test the Rovo agent with synthetic issues covering:

- a normal issue with comments;
- an issue with changelog entries;
- linked issues;
- an issue with insufficient evidence;
- an invalid/nonexistent issue key;
- a Jira issue the requesting user cannot access; and
- a project with same-project candidate issues.

## Marketplace review consistency checklist

Before submitting, compare the production Forge manifest and source against these documents. Confirm:

- scopes are still limited to the documented read scopes;
- the action remains read-only;
- Jira calls still use the documented authorization context;
- no external remote/egress has been added without disclosure;
- no application-owned persistence has been added without disclosure;
- privacy and data-handling documents describe every accessed data category accurately;
- dependency audit contains no unresolved high/critical vulnerabilities relevant to the production app;
- screenshots contain only synthetic/test data;
- listing claims match actual behavior; and
- support/security contacts are monitored.

## Do not claim yet

Do not claim Atlassian Marketplace approval, Atlassian endorsement, a security certification, data residency guarantees, compliance certifications, or a formal SLA unless those have actually been obtained and apply to this app.

## After Marketplace acceptance

After the public listing is approved:

1. add the Marketplace listing URL to the root README;
2. tag the exact source version corresponding to the approved release;
3. update `CHANGELOG.md` with the Marketplace release;
4. keep privacy/data-handling documents synchronized with every scope, integration, storage, or authorization change; and
5. test production installation/upgrade behavior before each Marketplace release.
