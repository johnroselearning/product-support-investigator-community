"""Read-only stdio MCP server. Run: python -m skill_adapter.server."""
from copy import deepcopy
from hashlib import sha256
import sys
from typing import Any

import yaml
from mcp.server import MCPServer
from mcp.server.extension import Extension, MethodBinding
from mcp.server.mcpserver.resources import TextResource
from mcp.shared.exceptions import MCPError
from mcp_types import RequestParams, ToolAnnotations

from observability.audit import audit_event
from observability.logging import configure_logging, get_logger

from .bundle import BASE_URI, SKILL_URI, read_bundle

EXTENSION_ID = "io.modelcontextprotocol/skills"
VERSIONS = frozenset({"2026-07-28"})
log = get_logger("mcp_server")


class ListParams(RequestParams):
    cursor: str | None = None


class GetParams(RequestParams):
    uri: str


class Skills(Extension):
    """SEP-2640 binding using the SDK's public extension API."""
    identifier = EXTENSION_ID

    def __init__(self, entry: dict):
        self.entry = entry

    def methods(self):
        return (
            MethodBinding("skills/list", ListParams, self.list, VERSIONS),
            MethodBinding("skills/get", GetParams, self.get, VERSIONS),
        )

    async def list(self, ctx, params):
        log.info("skill discovery requested", extra={"component": "mcp_server", "operation": "skills_list", "status": "success"})
        if params.cursor is not None:
            raise MCPError(-32602, "Invalid cursor")
        return {"resultType": "complete", "skills": [deepcopy(self.entry)],
                "ttlMs": 0, "cacheScope": "public"}

    async def get(self, ctx, params):
        log.info("skill retrieval requested", extra={"component": "mcp_server", "operation": "skills_get", "status": "success"})
        if params.uri != SKILL_URI:
            raise MCPError(-32602, "Unknown skill URI")
        return {"resultType": "complete", "skill": deepcopy(self.entry),
                "ttlMs": 0, "cacheScope": "public"}


def create_server() -> MCPServer:
    # Snapshot once: reads and manifests remain consistent until process restart.
    bundle = read_bundle()
    texts = {name: data.decode("utf-8") for name, data in bundle.items()}
    frontmatter = yaml.safe_load(texts["SKILL.md"].split("---\n", 2)[1])
    if frontmatter.get("name") != "product-support-investigator" or not frontmatter.get("description"):
        raise ValueError("Invalid canonical skill frontmatter")
    entry = {
        "uri": SKILL_URI, "frontmatter": frontmatter,
        "resources": [{"uri": BASE_URI + name, "digest": "sha256:" + sha256(data).hexdigest(),
                       "size": len(data)} for name, data in bundle.items()],
    }
    async def exact_resource_uri(ctx, call_next):
        # Check raw input before SDK URI parsing can normalize dot segments.
        if ctx.method == "resources/read":
            uri = (ctx.params or {}).get("uri")
            if not isinstance(uri, str) or uri not in {BASE_URI + name for name in bundle}:
                raise MCPError(-32602, "Unknown or unauthorized skill resource")
        return await call_next(ctx)

    server = MCPServer(
        "product-support-investigator-skills", version="0.1.0",
        instructions=(f"Read-only skill distribution. Discover with skills/list and skills/get "
                      f"when negotiated, or fallback tools list_skills/get_skill. "
                      f"Instructions: {SKILL_URI}. Supporting files use resources/read. "
                      "Retrieval does not activate a skill or execute bundled code."),
        extensions=[Skills(entry)], middleware=[exact_resource_uri],
    )
    for name, text in texts.items():
        server.add_resource(TextResource(uri=BASE_URI + name, name=name, text=text,
                            mime_type="text/x-python" if name.endswith(".py") else "text/markdown"))

    annotations = ToolAnnotations(read_only_hint=True, destructive_hint=False,
                                  idempotent_hint=True, open_world_hint=False)

    @server.tool(annotations=annotations)
    def list_skills() -> dict[str, Any]:
        """Fallback tool (not skills/list): list skill metadata and complete file manifests."""
        return {"skills": [deepcopy(entry)]}

    @server.tool(annotations=annotations)
    def get_skill(uri: str = SKILL_URI) -> dict[str, Any]:
        """Fallback tool (not skills/get): retrieve metadata, instructions, and every included file.

        Only the exact listed SKILL.md URI is accepted. Code files are inert text.
        """
        if uri != SKILL_URI:
            raise MCPError(-32602, "Unknown skill URI")
        return {"skill": deepcopy(entry),
                "files": [{"uri": BASE_URI + name, "text": text} for name, text in texts.items()]}

    return server


def main():
    # stdout is reserved for MCP JSON-RPC frames when using stdio transport.
    configure_logging(stream=sys.stderr)
    audit_event("configuration_changed", operation="server_started", status="success")
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
