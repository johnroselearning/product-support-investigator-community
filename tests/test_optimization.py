"""Behavioral regressions for conditional context; existing security tests stay intact."""
from pathlib import Path
import re
import unittest
import yaml

from investigation_harness.context import load_context, selected_references
from investigation_harness.engine import Harness
from investigation_harness.fixtures import fixture_registry, policy, scenario
from investigation_harness.registry import Registry
from investigation_harness.state import State
from investigation_harness.workflows import request_categories
from skill_adapter.bundle import FILES, read_bundle

ROOT = Path(__file__).resolve().parents[1]


class ContextTests(unittest.TestCase):
    def test_forge_templates_keep_identity_permissions_and_action_contract(self):
        for name in ("manifest.example.yml", "manifest.yml.example"):
            manifest = yaml.safe_load((ROOT / "forge-app" / name).read_text())
            self.assertEqual(manifest["permissions"], {"scopes": ["read:jira-work", "read:chat:rovo"]})
            self.assertEqual(manifest["app"]["runtime"]["name"], "nodejs24.x")
            self.assertEqual(manifest["app"]["id"], "ari:cloud:ecosystem::app/" + (
                "481a6bda-bcba-497d-a072-a0447026d83f" if name == "manifest.example.yml" else "REPLACE_WITH_FORGE_APP_ID"))
            action = manifest["modules"]["action"][0]
            self.assertEqual((action["key"], action["actionVerb"], action["function"]),
                             ("investigate-jira-issue", "GET", "investigateJiraIssue"))
            self.assertTrue(action["inputs"]["issueKey"]["required"])
            for key in ("sections", "limit", "startAt"):
                self.assertFalse(action["inputs"][key]["required"])

    def test_categories_preserve_mixed_and_partial_investigation(self):
        self.assertEqual(request_categories("general_question"), ("QUESTION",))
        self.assertEqual(request_categories("customer_investigation"), ("INVESTIGATION",))
        self.assertEqual(request_categories("psi_maintenance"), ("MAINTENANCE",))
        self.assertEqual(request_categories("needs_clarification"), ("UNCLEAR",))
        self.assertEqual(request_categories("mixed"), ("INVESTIGATION", "MAINTENANCE"))

    def test_questions_and_unclear_requests_have_no_context_load(self):
        for workflow in ("general_question", "needs_clarification"):
            state = State(workflow=workflow, selected_skill="product-support-investigator")
            self.assertIsNone(load_context(state))

    def test_external_provider_context_is_conditional_and_source_addressable(self):
        state = State(selected_skill="product-support-investigator")
        state.understanding = {"external_evidence_allowed": False, "route": "investigate_supplied"}
        state.evidence_needs = ["search_logs"]
        self.assertEqual(set(selected_references(state)), {"SKILL.md"})
        state.understanding.update(external_evidence_allowed=True, route="investigate_external")
        result = load_context(state)
        self.assertIn("references/evidence-providers.md", result)
        self.assertTrue(all(len(item["sha256"]) == 64 for item in result.values()))
        self.assertNotIn("references/github.md", result)
        state.workflow = "psi_maintenance"
        self.assertIn("references/workflows.md", load_context(state))

    def test_reference_closure_is_direct_and_bundle_copies_are_identical(self):
        bundle = read_bundle()
        linked = re.findall(r'\]\((references/[^)]+)\)', bundle["SKILL.md"].decode())
        self.assertEqual(set(linked), {p for p in FILES if p.startswith("references/")})
        for name, data in bundle.items():
            if name.startswith("references/"):
                self.assertFalse(re.findall(r'\]\((?!https?://|#)[^)]+\.md\)', data.decode()))
                self.assertEqual((ROOT / "forge-app/skills/product-support-investigation" / name).read_bytes(), data)
        prompt = (ROOT / "forge-app/prompts/investigator.md").read_text()
        self.assertNotIn("Supporting file:", prompt)
        self.assertFalse(list((ROOT / "forge-app/skills/product-support-investigation").rglob("*.py")))


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_catalog_filters_irrelevant_connections_and_retains_fallbacks(self):
        request, adapter = scenario("checkout")
        state = await Harness(adapter, fixture_registry("checkout"), policy()).run(request)
        first = next(p for stage, p in adapter.payloads if stage == "choose")
        names = {c["capability"] for c in first["capabilities"]}
        self.assertEqual(names, {"search_logs", "fetch_issue", "discover_service"})
        self.assertNotIn("read_repository_file", names)
        self.assertEqual(first["state"]["categories"], ["INVESTIGATION"])
        self.assertEqual(state.calls, 1)

    async def test_missing_correlation_id_does_not_block_bounded_logs(self):
        request, adapter = scenario("checkout")
        self.assertNotIn("request_id", request["scope"])
        state = await Harness(adapter, fixture_registry("checkout"), policy()).run(request)
        self.assertEqual(state.calls, 1)
        self.assertNotEqual(state.termination, "clarification_essential")

    async def test_followup_reuses_scope_and_report_keeps_complete_bounded_ledger(self):
        request, adapter = scenario("multiturn")
        state = await Harness(adapter, fixture_registry("multiturn"), policy()).run(request)
        self.assertEqual(state.calls, 1)
        self.assertEqual(state.scope.get("service"), "checkout")
        self.assertEqual(state.report["evidence"], state.evidence)
        for claim in state.report["claims"]:
            self.assertTrue(all(ref in {e["id"] for e in state.evidence} for ref in claim["refs"]))

    async def test_ordinary_question_does_not_discover_connected_tools(self):
        request, adapter = scenario("explain")
        registry = Registry()
        def forbidden(*args, **kwargs):
            self.fail("Question tried to discover tools")
        registry.catalog = forbidden
        state = await Harness(adapter, registry, policy()).run(request)
        self.assertEqual(state.calls, 0)
        self.assertEqual(state.critic_findings, [])
        self.assertIsNone(state.selected_skill)

    async def test_injection_and_insufficient_evidence_never_become_causation(self):
        for case in ("injection", "empty", "partial", "blame", "sparse", "missing_tool"):
            request, adapter = scenario(case)
            state = await Harness(adapter, fixture_registry(case), policy()).run(request)
            self.assertEqual(state.report["root_cause"], "Unknown")
            self.assertTrue(all(c["kind"] in ("observed", "inferred") for c in state.report["claims"]))
            self.assertTrue(all(a.get("inputs", {}).get("tenant") == "acme" for a in state.actions if "attempt" in a))


if __name__ == "__main__":
    unittest.main()
