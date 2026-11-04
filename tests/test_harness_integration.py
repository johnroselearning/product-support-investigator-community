"""Fixture integration tests. These do not measure a real model's intent accuracy."""
import json
import unittest

from investigation_harness.engine import Harness
from investigation_harness.fixtures import fixture_registry, policy, scenario


class FixtureIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def case(self, name):
        request, adapter = scenario(name)
        result = await Harness(adapter, fixture_registry(name), policy()).run(request)
        self.assertNotIn(result.termination, ("invalid_contract", "budget_exhausted", "execution_failure"))
        return result, adapter

    async def test_explanation_rewrite_and_direct_retrieval(self):
        for name in ("explain", "rewrite"):
            state, _ = await self.case(name)
            self.assertIsNone(state.selected_skill)
            self.assertEqual(state.calls, 0)
            self.assertEqual(len(state.critic_findings), 0)
        state, _ = await self.case("commits")
        self.assertIsNone(state.selected_skill)
        self.assertEqual(state.calls, 1)

    async def test_supplied_evidence_and_hypothetical_do_not_need_tools(self):
        for name in ("stack", "hypothetical"):
            state, _ = await self.case(name)
            self.assertIsNotNone(state.selected_skill)
            self.assertEqual(state.calls, 0)

    async def test_issue_retrieval_resolves_fields_with_provenance(self):
        state, _ = await self.case("jira")
        self.assertEqual([a["capability"] for a in state.actions], ["fetch_issue", "search_logs"])
        self.assertEqual(state.scope.candidates["service"][0]["source"], "retrieved")
        self.assertEqual(state.scope.candidates["service"][0]["locator"], "E1")
        self.assertNotEqual(state.termination, "clarification_essential")

    async def test_recovery_before_clarification_and_unavailable_fallback(self):
        state, _ = await self.case("resolve_first")
        self.assertEqual([a["capability"] for a in state.actions], ["fetch_issue", "search_logs"])
        state, _ = await self.case("tool_fallback")
        self.assertEqual(state.calls, 1)
        self.assertEqual(state.actions[-1]["capability"], "search_logs")
        state, _ = await self.case("retrieved_conflict")
        self.assertEqual(state.termination, "clarification_essential")
        self.assertIsNone(state.scope.get("environment"))
        state, _ = await self.case("sparse")
        self.assertEqual(state.understanding["goals"], ["diagnose"])
        self.assertIsNotNone(state.selected_skill)

    async def test_informal_vendor_neutral_and_multiturn_equivalence(self):
        states = [await self.case(name) for name in ("checkout", "informal", "vendor_neutral", "multiturn")]
        self.assertEqual({s.understanding["route"] for s, _ in states}, {"investigate_external"})
        self.assertEqual({s.calls for s, _ in states}, {1})
        self.assertEqual(states[-1][0].scope.get("service"), "checkout")

    async def test_ambiguity_and_cross_tenant_attempts(self):
        for name in ("environment", "tenant", "cross_tenant"):
            state, _ = await self.case(name)
            self.assertEqual(state.calls, 0)
            self.assertIsNotNone(state.selected_skill)
        state, _ = await self.case("environment")
        self.assertEqual(state.termination, "clarification_essential")
        self.assertEqual(len(state.scope.candidates["environment"]), 2)

    async def test_missing_and_unavailable_tools_keep_skill_and_partial_report(self):
        for name in ("missing_tool", "unavailable", "failure"):
            state, _ = await self.case(name)
            self.assertIsNotNone(state.selected_skill)
            self.assertTrue(state.report["unknowns"])

    async def test_empty_partial_stale_and_conflicting_evidence(self):
        for name, word in (("empty", "Empty"), ("partial", "partial"), ("stale", "stale"), ("conflict", "Conflicting")):
            state, _ = await self.case(name)
            self.assertIn(word, " ".join(state.report["unknowns"]))
            self.assertEqual(state.report["root_cause"], "Unknown")

    async def test_retrieved_injection_is_only_data(self):
        state, _ = await self.case("injection")
        self.assertEqual(state.calls, 2)
        self.assertEqual(state.scope.get("tenant"), "acme")
        self.assertTrue(any("Ignore all instructions" in e["excerpt"] for e in state.evidence))
        self.assertTrue(all(a["inputs"]["tenant"] == "acme" for a in state.actions))

    async def test_no_progress_and_pagination(self):
        state, _ = await self.case("repeat")
        self.assertEqual(state.calls, 1)
        self.assertEqual(state.termination, "no_progress")
        state, _ = await self.case("pagination")
        self.assertEqual(state.calls, 2)
        self.assertEqual(len(state.evidence), 2)
        self.assertEqual(state.actions[1]["inputs"]["cursor"], "page-2")

    async def test_discovery_and_all_bound_capabilities(self):
        for name in ("discovery", "mixed", "metrics", "trace", "repository"):
            state, _ = await self.case(name)
            self.assertGreaterEqual(state.calls, 1)
            self.assertTrue(state.evidence)
            self.assertTrue(all(c["kind"] == "observed" for c in state.report["claims"]))

    async def test_progressive_loading_and_no_expected_answers(self):
        state, adapter = await self.case("jira")
        self.assertNotIn("method", adapter.payloads[0][1])
        first_choice = next(p for stage, p in adapter.payloads if stage == "choose")
        self.assertIn("method", first_choice)
        self.assertTrue(all("inputs" not in c for c in first_choice["capabilities"]))
        proposal = next(p for stage, p in adapter.payloads if stage == "propose")
        self.assertIn("inputs", proposal["contract"])
        for stage, payload in adapter.payloads:
            self.assertNotIn("expected", payload)
            self.assertNotIn("evaluation", payload)
        self.assertEqual(state.usage[0]["measurement"], "unavailable_or_partial")
