"""Real official SDK clients over subprocess stdio, plus bundle boundary checks."""
import asyncio
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from typing import Any, Literal
from pydantic import Field
import yaml

from mcp import Client
from mcp.client import advertise
from mcp.client.stdio import StdioServerParameters
from mcp.shared.exceptions import MCPError
from mcp_types import CacheableResult, Request

from skill_adapter.bundle import BASE_URI, FILES, ROOT, SKILL_URI, read_bundle
from skill_adapter.server import EXTENSION_ID, create_server


class ListResult(CacheableResult):
    result_type: Literal["complete"] = Field(alias="resultType")
    skills: list[dict]


class GetResult(CacheableResult):
    result_type: Literal["complete"] = Field(alias="resultType")
    skill: dict


def client(mode="auto"):
    return Client(StdioServerParameters(command=sys.executable,
                  args=[str(ROOT/"scripts/serve_skills.py")], cwd=tempfile.gettempdir()), mode=mode,
                  read_timeout_seconds=10, extensions=[advertise(EXTENSION_ID, {})], cache=None)


async def request(c, method, params, result):
    return await c.session.send_request(Request[dict[str, Any], str](method=method, params=params), result)


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_native_discovery_and_complete_retrieval(self):
        async with client() as c:
            self.assertEqual(c.protocol_version, "2026-07-28")
            self.assertIn(EXTENSION_ID, c.server_capabilities.extensions)
            self.assertIsNotNone(c.server_capabilities.resources)
            listed = await request(c, "skills/list", {}, ListResult)
            self.assertEqual(listed.result_type, "complete")
            self.assertEqual(listed.ttl_ms, 0)
            self.assertEqual(listed.cache_scope, "public")
            self.assertEqual(len(listed.skills), 1)
            entry = listed.skills[0]
            got = await request(c, "skills/get", {"uri": SKILL_URI}, GetResult)
            self.assertEqual(got.skill, entry)
            self.assertEqual(entry["uri"], SKILL_URI)
            self.assertEqual(entry["frontmatter"]["name"], "product-support-investigator")
            bundle = read_bundle()
            self.assertEqual(entry["frontmatter"], yaml.safe_load(bundle["SKILL.md"].decode().split("---\n", 2)[1]))
            self.assertEqual({r["uri"] for r in entry["resources"]}, {BASE_URI+n for n in FILES})
            resources = await c.list_resources()
            self.assertEqual({str(r.uri) for r in resources.resources}, {BASE_URI+n for n in FILES})
            for resource in entry["resources"]:
                read = await c.read_resource(resource["uri"])
                data = read.contents[0].text.encode("utf-8")
                name = resource["uri"].removeprefix(BASE_URI)
                self.assertEqual(data, bundle[name])
                self.assertEqual(len(data), resource["size"])
                self.assertEqual("sha256:"+hashlib.sha256(data).hexdigest(), resource["digest"])
            # Every included helper has been retrieved as inert text, not imported.
            tools = await c.list_tools()
            self.assertEqual({t.name for t in tools.tools}, {"list_skills", "get_skill"})
            fallback = await c.call_tool("get_skill", {"uri": SKILL_URI})
            self.assertEqual(fallback.structured_content["skill"], entry)
            self.assertEqual({f["uri"]: f["text"].encode() for f in fallback.structured_content["files"]},
                             {BASE_URI+n: data for n, data in bundle.items()})

    async def test_invalid_requests_over_wire(self):
        async with client() as c:
            for uri in ("skill://unknown/SKILL.md", BASE_URI+"references/grafana.md", "product-support-investigator"):
                with self.subTest(skill_uri=uri), self.assertRaises(MCPError) as err:
                    await request(c, "skills/get", {"uri": uri}, GetResult)
                self.assertEqual(err.exception.code, -32602)
                with self.assertRaises(MCPError) as err:
                    await c.call_tool("get_skill", {"uri": uri})
                self.assertEqual(err.exception.code, -32602)
            with self.assertRaises(MCPError) as err:
                await request(c, "skills/list", {"cursor": "invalid"}, ListResult)
            self.assertEqual(err.exception.code, -32602)
            for path in ("missing.md", "../SKILL.md", "references/../SKILL.md", "%2e%2e/SKILL.md",
                         "references/%2e%2e/SKILL.md", "references\\..\\SKILL.md",
                         "references//grafana.md", ".git/config", ".env", "README.md", "SKILL.md?x=1", "SKILL.md#x"):
                with self.subTest(path=path), self.assertRaises(MCPError) as err:
                    # Raw Request avoids client-side URL normalization of malicious input.
                    await request(c, "resources/read", {"uri": BASE_URI+path}, CacheableResult)
                self.assertEqual(err.exception.code, -32602)
            with self.assertRaises(MCPError) as err:
                await request(c, "resources/read", {"uri": "file:///etc/passwd"}, CacheableResult)
            self.assertEqual(err.exception.code, -32602)

    async def test_legacy_client_fallback(self):
        async with client("legacy") as c:
            self.assertNotEqual(c.protocol_version, "2026-07-28")
            listed = await c.call_tool("list_skills", {})
            self.assertEqual(listed.structured_content["skills"][0]["uri"], SKILL_URI)
            got = await c.call_tool("get_skill", {"uri": SKILL_URI})
            files = got.structured_content["files"]
            self.assertEqual(next(f["text"] for f in files if f["uri"] == SKILL_URI),
                             (ROOT/"SKILL.md").read_text())
            self.assertEqual((await c.read_resource(SKILL_URI)).contents[0].text,
                             (ROOT/"SKILL.md").read_text())
            with self.assertRaises(MCPError) as err:
                await request(c, "skills/list", {}, ListResult)
            self.assertEqual(err.exception.code, -32601)


class BundleTests(unittest.TestCase):
    def test_portable_package_and_reference_closure(self):
        subprocess.run([sys.executable, "scripts/sync_skill.py", "--check"], cwd=ROOT, check=True)
        with tempfile.TemporaryDirectory() as directory:
            isolated = Path(directory)/"product-support-investigator"
            shutil.copytree(ROOT/"skills/product-support-investigator", isolated)
            self.assertEqual(read_bundle(isolated), read_bundle())
            # Markdown links resolve beside the reference; canonical backtick paths
            # name files relative to the skill root. Ignore external URLs.
            for name, data in read_bundle(isolated).items():
                if not name.endswith(".md"):
                    continue
                text = data.decode()
                for target in re.findall(r'`((?:references|scripts|providers)/[^`]+\.(?:md|py)|COMMUNITY\.md)`', text):
                    self.assertIn(target, FILES)
                for target in re.findall(r'\]\(([^)]+)\)', text):
                    if "://" not in target and not target.startswith("#"):
                        self.assertTrue((isolated/Path(name).parent/target).is_file(), target)

    def test_missing_file_and_symlink_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/"skill"
            shutil.copytree(ROOT/"skills/product-support-investigator", root)
            missing = root/"references/grafana.md"
            missing.unlink()
            with self.assertRaisesRegex(ValueError, "Missing"):
                read_bundle(root)
            missing.symlink_to(ROOT/"README.md")
            with self.assertRaisesRegex(ValueError, "Symlink"):
                read_bundle(root)
            missing.unlink()
            shutil.rmtree(root/"references")
            (root/"references").symlink_to(ROOT/"references", target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "Symlink"):
                read_bundle(root)

    def test_helper_retrieval_cannot_execute_code(self):
        # Deliberately invalid Python would fail if it were compiled/imported.
        bundle = read_bundle()
        bundle["scripts/grafana_evidence.py"] = b"raise RuntimeError('must not execute')\ninvalid python!"
        provider_before = sys.modules.get("providers.grafana")
        with patch("skill_adapter.server.read_bundle", return_value=bundle):
            server = create_server()
            read = asyncio.run(server.read_resource(BASE_URI+"scripts/grafana_evidence.py"))
            self.assertEqual(list(read)[0].content.encode(), bundle["scripts/grafana_evidence.py"])
        self.assertIs(sys.modules.get("providers.grafana"), provider_before)

    def test_atlassian_gate_preserved_and_generated(self):
        gate = (ROOT/"atlassian/compliance-gate.txt").read_bytes()
        deployed = (ROOT/"forge-app/prompts/investigator.md").read_bytes()
        self.assertTrue(deployed.startswith(gate))
        self.assertEqual(hashlib.sha256(gate).hexdigest(),
                         "ed08048512b2d6bc8d92e0f122d32845268d303e960bc29b7d58de0a89e82037")


if __name__ == "__main__":
    unittest.main()
