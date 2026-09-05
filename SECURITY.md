# Security Policy

## Reporting a vulnerability

Please do not disclose suspected vulnerabilities, credentials, tokens, customer data, or exploit details in a public issue or discussion.

If GitHub private vulnerability reporting is enabled for this repository, use **Security → Advisories → Report a vulnerability**. If that option is unavailable, open a minimal public issue asking the maintainer for a private contact channel, without including sensitive technical details.

When reporting privately, include:

- the affected component or file;
- the impact you believe is possible;
- reproduction steps or a proof of concept, if safe to share;
- any relevant version, commit, or environment information;
- suggested remediation, if known.

## Sensitive data

Never commit or include real API keys, access tokens, passwords, private keys, session cookies, `.env` contents, production customer data, Jira exports containing confidential information, Datadog credentials, Zendesk credentials, Atlassian credentials, or other secrets.

If a secret is accidentally committed, treat it as compromised. Revoke or rotate it immediately. Removing it in a later commit is not sufficient because it may remain in Git history and caches.

## Scope

This repository contains agent instructions and a starter Atlassian Forge/Rovo adapter. Reports involving prompt injection, unintended data disclosure, excessive Jira data access, authorization bypass, credential exposure, unsafe mutation of Jira data, dependency compromise, or CI/CD compromise are especially relevant.

## Supported versions

Until formal releases are published, only the current default branch is actively maintained for security fixes.
