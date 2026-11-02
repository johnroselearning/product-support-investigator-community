# Local MCP skill adapter

The root `SKILL.md` is the authoritative Product Support Investigator methodology. The stdio adapter reads it directly, exposes its included supporting files, and provides discovery metadata. It does not investigate, route requests, contact evidence providers, execute bundled scripts, or offer a hosted service.

## Install and start

Requires Python 3.10+ with venv/pip. Tested locally with Python 3.14.4 and official SDK `mcp 2.2.0`; CI uses Python 3.12. The skill itself still needs no Python runtime unless using this adapter or the optional Grafana helper. Forge keeps its Node.js 24 runtime and existing dependencies.

```bash
git clone https://github.com/johnroselearning/product-support-investigator-community.git
cd product-support-investigator-community
# For this implementation before merge, use codex/mcp-skill-adapter when available.
python3 -m venv .venv-mcp
.venv-mcp/bin/python -m pip install -r requirements-mcp.txt
python3 scripts/validate_skill.py
.venv-mcp/bin/python scripts/serve_skills.py
```

The last command waits for MCP messages on stdin; stdout is reserved for protocol traffic. Usually the client launches this process, so do not separately start it. On Windows, use `.venv-mcp\Scripts\python.exe` in place of `.venv-mcp/bin/python`.

For a host that accepts `mcpServers` JSON, merge this entry into its MCP configuration and restart/reconnect. Replace `/absolute/path` with your checkout location. The launcher works from any working directory; no environment variables, credentials, or network listener are required.

```json
{
  "mcpServers": {
    "product-support-investigator": {
      "command": "/absolute/path/product-support-investigator-community/.venv-mcp/bin/python",
      "args": ["/absolute/path/product-support-investigator-community/scripts/serve_skills.py"]
    }
  }
}
```

If a host uses another configuration format, set the same command and argument in its local stdio MCP server settings. This is a transport configuration example, not a claim that every agent supports native skill activation.

## Discovery and retrieval

| Client support | Discovery | Retrieval |
| --- | --- | --- |
| MCP `2026-07-28` Skills extension | `server/discover` advertises `io.modelcontextprotocol/skills`; then `skills/list` / `skills/get` | `resources/read` for each manifest URI |
| Generic tools-capable MCP client, including legacy handshake clients | Custom `list_skills` tool | Custom `get_skill` tool returns the entry and all files as inert text |
| Generic resources-capable MCP client | `resources/list` | `resources/read` |

The skill identifier is the full URI `skill://product-support-investigator/SKILL.md`, not its name alone. Native `skills/get` accepts `{"uri": "skill://product-support-investigator/SKILL.md"}`. The fallback `get_skill` tool accepts the same argument or defaults to this skill. Both discovery paths supply verbatim frontmatter and a complete file manifest with byte sizes and SHA-256 digests. Supporting files are relative to the skill directory and readable under `skill://product-support-investigator/`.

Custom fallback tools are **not standard protocol methods**. They do not activate a skill. Hosts must decide how to present and use retrieved instructions, verify files, and apply their approval policies. The optional directory-read method is not implemented or advertised. Native methods are gated to the verified `2026-07-28` protocol revision; legacy connections use tools/resources. No list-change notifications or hot reload are promised; restart to load edits.

## Specification and SDK decision

Checked on 2026-10-03 against the official [stable Skills extension](https://github.com/modelcontextprotocol/ext-skills/blob/main/specification/stable/skills.mdx) and [official Python SDK](https://github.com/modelcontextprotocol/python-sdk). The stable extension requires the newer protocol and discovery negotiation, so advertising it through an older initialization-only implementation would not suffice.

The installed `mcp 2.2.0` SDK has public `Extension` / `MethodBinding` hooks and supports modern discovery, but no built-in Skills helper. This adapter supplies the extension binding through that API. Dependencies are pinned in `requirements-mcp.txt`. The implementation uses the official SDK for protocol framing, negotiation, standard resources, and fallback tools rather than hand-writing JSON-RPC.

## Included files and boundaries

`skill_adapter/bundle.py` defines the explicit 13-file bundle: canonical `SKILL.md`, `COMMUNITY.md`, seven references, the optional Grafana script, and three provider source files. All supporting local paths required by these instructions are included. Documentation, other skills, Forge source, Git internals, environment files, and unrelated repository files are not exposed.

The adapter fails startup if an included file is missing, nonregular, or symlinked (including a symlinked parent inside the bundle). It reads an immutable snapshot at startup so file contents match the advertised digests even if the checkout changes later. It checks raw resource URIs against exact allowed strings before SDK URL normalization: dot segments, encoded paths, query strings, fragments, and unknown files are rejected with Invalid params (`-32602`). Unknown skill URIs also return `-32602`. The single-page catalog rejects cursors. Scripts are returned as plain text; retrieval never imports or executes them.

Read access to the checkout and a trusted local Python/dependency installation are required. The snapshot is public skill content, not support incident data. No credentials or external provider access are configured by serving it. Clients should retain the originating server identity along with skill URIs and verify returned bytes against the manifest.

## Canonical packaging

```bash
python3 scripts/sync_skill.py
python3 scripts/sync_skill.py --check
python3 scripts/package_plugin.py
```

The generator copies the explicit bundle into `skills/product-support-investigator/` for isolated Codex/Claude installation, and composes the self-contained Forge prompt from canonical instructions plus separate Atlassian gate/platform sources. These committed outputs are generated artifacts, not separately maintained methodology. Skill validation, packaging, and CI check drift. MCP reads the canonical sources, not those generated copies.

## Verify with a real client

```bash
.venv-mcp/bin/python -m unittest discover -s tests -p test_mcp_skills.py -v
.venv-mcp/bin/python -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/validate_skill.py
python3 scripts/package_plugin.py
```

The protocol tests launch the adapter from outside the checkout as a real stdio subprocess using the official SDK `Client` and `StdioServerParameters`. They verify modern discovery and legacy initialization, retrieve every file through resources and the fallback tool, compare instructions byte-for-byte with the root source, and verify manifest hashes/sizes. They exercise unknown skill URIs, missing and unauthorized resources, traversal/encoding attempts, missing bundle files, symlinks, portable reference closure, inert script retrieval, and preservation of the Atlassian gate.

This verifies the MCP delivery protocol. End-to-end native skill activation in **Codex, Claude Desktop/Code, ChatGPT, or Rovo has not been tested**. Rovo continues to use its generated Forge prompt and existing action; it does not consume this MCP server. Plugin installation and the larger generated Rovo prompt still require a clean named-client/Forge validation session before release. No merge, publication, installation on an Atlassian site, or deployment is part of this change.
