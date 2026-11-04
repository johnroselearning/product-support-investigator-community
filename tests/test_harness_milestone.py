"""Deterministic milestone checks; all providers and decisions are synthetic."""
import unittest
from investigation_harness.engine import Harness
from investigation_harness.fixtures import fixture_registry, policy, scenario
from investigation_harness.service_map import ServiceMap


class ServiceMappingTests(unittest.IsolatedAsyncioTestCase):
    async def test_mapping_is_only_a_bounded_lead_and_events_are_content_free(self):
        mapping = ServiceMap([{"service": "checkout", "aliases": ["cart"], "routes": ["/pay"],
                               "components": ["api"], "environments": ["production"],
                               "datasources": ["private"], "telemetry_labels": {"service": "checkout"},
                               "dependencies": ["payments"], "owners": ["team"]}])
        self.assertEqual(mapping.leads("cart")[0]["service"], "checkout")
        self.assertEqual(mapping.leads(None), [])
        request, model = scenario("checkout")
        state = await Harness(model, fixture_registry("checkout"), policy(), service_map=mapping).run(request, parent_investigation_id="parent123")
        choice = next(payload for stage, payload in model.payloads if stage == "choose")
        self.assertEqual(choice["service_leads"][0]["datasources"], ["private"])
        self.assertTrue(all(a.get("inputs", {}).get("datasource") != "private" for a in state.actions))
        done = next(e for e in state.events if e["phase"] == "call" and e["status"] != "started")
        self.assertIn("duration_ms", done)
        self.assertIn("retry_count", done)
        self.assertEqual(done["parent_investigation_id"], "parent123")
        self.assertIn("evidence_refs", next(e for e in state.events if e["phase"] == "evidence_update"))
        self.assertNotIn("private", str(state.events))

    def test_bad_mapping_is_rejected(self):
        for entry in ({"service": "x", "token": "secret"}, {"service": "x", "aliases": "bad"}):
            with self.assertRaises(ValueError):
                ServiceMap([entry])
