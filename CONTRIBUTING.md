# Contributing

Thank you for contributing to Product Support Investigator.

## Use pull requests

Do not make routine changes directly on `main`. Create a short-lived branch, make the change there, and open a pull request.

Before requesting review:

1. keep the change focused;
2. do not commit credentials, tokens, private keys, `.env` files, customer data, or production exports;
3. run the repository validation and relevant Forge lint/tests;
4. document security or permission changes explicitly;
5. keep integrations least-privilege and read-only unless mutation is an intentional, reviewed requirement.

## Agent and integration safety

Changes to agent instructions or integrations should preserve these properties:

- evidence is distinguished from inference;
- external/customer content is treated as untrusted input, not as privileged instructions;
- Jira/Atlassian permissions use the narrowest practical scopes;
- data returned to an agent is bounded to what the investigation needs;
- write/delete/mutation behavior is not introduced silently;
- credentials and secrets are supplied through supported secret/configuration mechanisms, never source code;
- failures should not expose credentials or unnecessary sensitive response bodies.

## Validation

Run the skill validator from the repository root:

```bash
python3 scripts/validate_skill.py
```

For the Forge adapter, install dependencies in `forge-app/` and run the available lint command before deployment.

## Security reports

Do not report vulnerabilities or leaked credentials in a public issue. Follow `SECURITY.md`.
