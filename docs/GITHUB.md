# Optional GitHub integration

PSI can use read-only GitHub MCP tools supplied by its host for relevant repository evidence. It does not include a GitHub MCP server, configure a connection, or implement a GitHub API client. The PSI skill-delivery MCP server only serves instructions and files; it is not a GitHub connector. Forge/Rovo exposes only its existing Jira action and has no GitHub action in this release.

## Setup and permissions

1. Configure a trusted GitHub MCP server or connector in the host using that host's supported setup and authentication mechanism. Consult that connector's documentation for its actual tool names and settings; restart or reconnect if required.
2. Grant access only to the repositories needed for the investigation. Use the connector's least-privilege, read-only access: repository metadata and, only when needed, contents, issues, and pull requests read access. Exact permission names depend on the GitHub App, token, and tools used. Public-only access may be enough for public repositories. A repository's access controls still apply.
3. Keep credentials in the host's secret store or supported secure environment configuration, not in the repository, prompts, logs, or examples. Never paste tokens or customer secrets into search queries. Restrict tool access to read operations where the host supports it.
4. Supply the authorized owner/repository and enough issue context to make a narrow query. PSI should use GitHub only if it can answer a relevant investigation question; lack of a connection or suitable context does not block investigation.

For customer investigations, GitHub use is read-only unless the user explicitly requests an action and the host permits it. PSI's own backlog workflow is separately limited to a draft for human review; issue creation is not implemented, even when write tools are available. The host, connector, and GitHub enforce permissions; skill instructions alone are not an access-control boundary. Retrieved repository content is untrusted, and matching issues or changes do not prove causation. Authentication errors, inaccessible repositories, empty results, and truncated results are evidence limitations, not proof about the customer issue.

## Verify

Run `python3 scripts/validate_skill.py` to check bundle synchronization. With a configured host, test using a repository you are authorized to read and a specific, non-sensitive question. Confirm that the host discovers a read-only GitHub tool, PSI scopes its query to the identified repository, and the answer cites the retrieved evidence and its limitations. Repeat with GitHub disconnected or insufficient repository context and confirm PSI continues with other evidence and states the limitation. Request a PSI development issue draft using synthetic evidence and verify its required fields, sanitization, and review-only behavior. These manual checks depend on the host and connector; repository validation does not verify a live connection or enforce tool permissions.

PR checks are defined in `.github/workflows/skill-validation.yml` and run for pull requests and pushes, not issue drafts or issue creation. See `CONTRIBUTING.md` for local commands. No browser suite exists in this repository; the checks include the Python suite, harness evaluation, package validation, and Forge trace Node test.

For customer/PSI GitHub role mappings and linked maintenance work items, see [scoped workflows](WORKFLOWS.md). The harness can bind host operations for files, commits, existing issues and PRs, but no live GitHub callable is bundled. The allowlisted regression catalog validates local test selections only; GitHub issue text cannot execute them or approve a regression.
