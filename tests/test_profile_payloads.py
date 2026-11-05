"""Profiler contracts, privacy, offline operation, and observer isolation."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from scripts.profile_payloads import (CaptureLimits, LocalTokenizer, PayloadProfiler,
    parse_records, profile_records, sections_for, serialized, usage_metadata)
from investigation_harness.engine import Harness
from investigation_harness.fixtures import fixture_registry, policy, scenario
from investigation_harness.semantic import CallbackAdapter, Decision
from observability.logging import configure_logging

ROOT = Path(__file__).resolve().parents[1]


def profile(payload, **metadata):
    observer = PayloadProfiler(enabled=True)
    observer.observe("understand", payload, **metadata)
    return observer.report()


class ParsingTests(unittest.TestCase):
    def test_json_object_array_and_capture_envelope(self):
        self.assertEqual(parse_records('{"input":"hello"}'), [{"input": "hello"}])
        self.assertEqual(parse_records('[{"payload":"one"},{"payload":"two"}]'),
                         [{"payload": "one"}, {"payload": "two"}])
        self.assertEqual(parse_records('{"captures":[{"payload":"one"}]}'), [{"payload": "one"}])

    def test_message_array_is_one_request(self):
        records = parse_records('[{"role":"system","content":"Rules"},{"role":"user","content":"Hi"}]')
        self.assertEqual(len(records), 1)
        self.assertIn("messages", records[0])

    def test_jsonl_and_blank_lines(self):
        text = '\n{"payload":"one"}\n\n{"payload":"two"}\n'
        self.assertEqual(len(parse_records(text, "jsonl")), 2)
        self.assertEqual(parse_records(text), parse_records(text, "jsonl"))
        self.assertEqual(parse_records(" \n"), [])

    def test_malformed_json_never_outputs_payload(self):
        with self.assertRaises(ValueError):
            parse_records('{"secret":', "json")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            path.write_text('{"password":"private-test-canary", BROKEN')
            result = subprocess.run([sys.executable, str(ROOT / "scripts/profile_payloads.py"), str(path),
                                     "--output", str(Path(directory) / "output.json")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("private-test-canary", result.stderr + result.stdout)
            self.assertFalse((Path(directory) / "output.json").exists())

    def test_empty_payloads(self):
        for empty in ("", None, {}, [], {"sections": []}):
            report = profile(empty)
            self.assertEqual(report["totals"]["total_input_tokens_estimate"], 0)
            self.assertEqual(report["totals"]["unknown_percentage"], 0)

    def test_explicit_labels_override_keywords(self):
        report = profile({"sections": [{"component": "user_request", "content": "Grafana Jira GitHub"},
                                       {"label": "core_skill", "content": "Instructions"}]})
        components = report["totals"]["components"]
        self.assertEqual(components["user_request"]["characters"], 19)
        self.assertIn("core_skill", components)
        self.assertEqual(report["totals"]["unknown_percentage"], 0)

    def test_fallback_and_unknown_confidence(self):
        pieces = sections_for({"opaque": "Grafana logs", "unmapped": "xyzzy blorb"})
        self.assertTrue(any(p["component"] == "grafana_evidence" and p["confidence"] == .55 for p in pieces))
        report = profile({"sections": [{"component": "invented", "content": "private"}], "opaque": "xyzzy"})
        self.assertGreater(report["totals"]["unknown_percentage"], 0)
        self.assertLess(report["payloads"][0]["classification"]["weighted_confidence"], 1)

    def test_mixed_content_and_tools_keep_explicit_labels(self):
        payload = {"system": "## Investigation Principles", "tools": [{"name": "fetch_issue", "input_schema": {"type": "object"}}],
            "messages": [{"role": "user", "content": "earlier context"},
                         {"role": "assistant", "content": "previous answer"},
                         {"role": "user", "content": [{"type": "text", "text": "Investigate"},
                            {"component": "jira_evidence", "content": "issue body"},
                            {"type": "image", "source": {"type": "base64", "data": "synthetic"}}]},
                         {"role": "tool", "provider": "github", "content": "source excerpt"}]}
        pieces = sections_for(payload)
        self.assertEqual("".join(p["text"] for p in pieces), serialized(payload))
        components = profile(payload)["totals"]["components"]
        for component in ("core_skill", "tool_schemas", "conversation_history", "user_request", "jira_evidence", "github_evidence"):
            self.assertIn(component, components)

    def test_responses_and_anthropic_tool_blocks(self):
        payload = {"instructions": "Rules", "input": [{"type": "message", "role": "user", "content": "why"},
            {"type": "function_call_output", "call_id": "call-1", "output": "Grafana log excerpt"}]}
        self.assertIn("grafana_evidence", profile(payload)["totals"]["components"])
        anthropic = {"messages": [{"role": "user", "content": [{"type": "tool_result", "tool_use_id": "one", "content": "Jira issue key SUP-1"}]}]}
        self.assertIn("jira_evidence", profile(anthropic)["totals"]["components"])

    def test_harness_components_provenance_and_complete_serialization(self):
        payload = {"state": {"goal": {"summary": "investigate"}, "evidence": [
            {"id": "E1", "source": "search_logs", "excerpt": "log text", "scope": {"tenant": "test"}},
            {"id": "E2", "source": "fetch_issue", "excerpt": "issue text"}], "actions": []},
            "method": {"SKILL.md": {"sections": {"Evidence Model": "instructions"}},
                       "references/evidence-providers.md": {"sections": {"Trust and privacy": "rules"}}},
            "capabilities": [{"name": "fetch_issue"}], "response_contract": {"type": "object"}}
        pieces = sections_for(payload)
        self.assertEqual("".join(p["text"] for p in pieces), serialized(payload))
        components = profile(payload)["totals"]["components"]
        for component in ("core_skill", "provider_guidance", "tool_schemas", "capability_catalog", "grafana_evidence", "jira_evidence", "evidence_ledger"):
            self.assertIn(component, components)

    def test_unicode_is_character_not_byte_estimate(self):
        report = profile({"sections": {"user_request": "你好🙂é"}})
        self.assertEqual(report["totals"]["characters"], 4)
        self.assertEqual(report["totals"]["total_input_tokens_estimate"], 1)


class AnalysisTests(unittest.TestCase):
    def test_duplicate_blocks_and_normalized_lines(self):
        line = "Do not infer causation from timing alone."
        report = profile({"sections": [{"component": "core_skill", "content": line + "\n" + line},
                                       {"component": "core_skill", "content": "  " + line + "\n" + line}]})
        duplicate = report["payloads"][0]["duplicates"]
        self.assertGreater(duplicate["identical_blocks_characters"], 0)
        self.assertGreater(duplicate["normalized_lines_characters"], 0)
        self.assertLessEqual(duplicate["duplicate_percentage"], 100)
        self.assertGreater(report["repetition"]["repeated_instruction_characters"], 0)

    def test_near_duplicate_and_repeat_evidence(self):
        common = "Preserve the source, scope, timestamp, limitations, and identifiers for every observation. "
        profiler = PayloadProfiler(enabled=True)
        for suffix in ("Request one.", "Request two."):
            profiler.observe("choose", {"sections": {"core_skill": common * 4 + suffix,
                "grafana_evidence": "Repeated synthetic log excerpt with request req-123."}})
        report = profiler.report()
        self.assertGreater(report["repetition"]["near_matches_found"], 0)
        self.assertGreater(report["repetition"]["repeated_evidence_characters"], 0)

    def test_stable_prefix_dynamic_size_and_singletons(self):
        profiler = PayloadProfiler(enabled=True)
        for text in ("same prefix: abc", "same prefix: xyz"):
            profiler.observe("choose", {"sections": {"core_skill": text}}, comparison_group="same")
        profiler.observe("choose", "different", comparison_group="different")
        profiler.observe("critic", "same prefix: abc", comparison_group="same")
        report = profiler.report()
        rows = report["payloads"]
        self.assertEqual(rows[0]["stable_prefix_characters"], len("same prefix: "))
        self.assertEqual(rows[0]["dynamic_characters"], 3)
        self.assertIsNone(rows[2]["stable_prefix_percentage"])
        self.assertIsNone(rows[3]["stable_prefix_percentage"])
        self.assertEqual(report["totals"]["observed_model_calls"], 0)

    def test_exact_lines_across_different_blocks_and_hashes_are_ephemeral(self):
        profiler = PayloadProfiler(enabled=True)
        line = "Retain source scope and limitations."
        for suffix in ("unique first suffix", "different second suffix"):
            profiler.observe("report", {"sections": {"core_skill": line + "\n" + suffix}})
        report = profiler.report()
        repeated = report["repetition"]["largest_normalized_lines"]
        self.assertEqual(repeated[0]["characters"], len(line))
        self.assertEqual(repeated[0]["payloads"], 2)
        self.assertNotEqual(profiler.digest(line), PayloadProfiler(enabled=True).digest(line))

    def test_different_provider_and_model_are_not_compared(self):
        profiler = PayloadProfiler(enabled=True)
        for provider, model in (("openai", "a"), ("anthropic", "a"), ("openai", "b")):
            profiler.observe("understand", "identical", provider=provider, model=model)
        self.assertTrue(all(g["stable_prefix_percentage"] is None for g in profiler.report()["payloads"]))

    def test_stage_aggregation_and_observed_call_count(self):
        profiler = PayloadProfiler(enabled=True)
        profiler.observe("request_understanding", {"sections": {"user_request": "12345678"}}, kind="provider_request", submitted=True)
        profiler.observe("request_understanding", {"sections": {"user_request": "1234"}}, kind="scripted_adapter")
        report = profiler.report()
        stage = report["stages"]["understand"]
        self.assertEqual((stage["total_input_tokens_estimate"], stage["mean_input_tokens_estimate"], stage["maximum_input_tokens_estimate"]), (3, 1.5, 2))
        self.assertEqual(stage["observed_model_calls"], 1)
        self.assertEqual(report["stages"]["skill_selection"]["payloads"], 0)

    def test_capture_limits_and_skips(self):
        profiler = PayloadProfiler(enabled=True, limits=CaptureLimits(max_payload_characters=100, max_records=1))
        self.assertIsNone(profiler.observe("understand", "x" * 101))
        profiler.observe("understand", "valid")
        profiler.observe("understand", "second")
        self.assertEqual(profiler.report()["skipped"], {"character_limit": 1, "record_limit": 1})
        with self.assertRaises(ValueError):
            CaptureLimits(max_records=0)


class UsageAndPrivacyTests(unittest.TestCase):
    def test_openai_responses_chat_and_partial_usage(self):
        for usage in ({"input_tokens": 200, "output_tokens": 10, "input_tokens_details": {"cached_tokens": 128}},
                      {"prompt_tokens": 200, "completion_tokens": 10, "prompt_tokens_details": {"cached_tokens": 128}}):
            parsed = usage_metadata({"usage": usage}, "openai")
            self.assertEqual(parsed["actual_input_tokens"], 200)
            self.assertEqual(parsed["cache_read_tokens"], 128)
            self.assertTrue(parsed["cache_hit_indicator"])
            self.assertIsNone(parsed["cache_write_tokens"])
        self.assertIsNone(usage_metadata({"usage": {"input_tokens": -1, "output_tokens": True}}))
        self.assertIsNone(usage_metadata({"usage": {"input_tokens_details": {"secret": "do-not-retain"}}}))
        partial = usage_metadata({"usage": {"output_tokens": 3}})
        self.assertIsNone(partial["actual_input_tokens"])

    def test_anthropic_semantics_and_cache_writes(self):
        parsed = usage_metadata({"message": {"usage": {"input_tokens": 50, "output_tokens": 8,
            "cache_read_input_tokens": 100, "cache_creation_input_tokens": 60,
            "cache_creation": {"ephemeral_5m_input_tokens": 60}}}}, "anthropic")
        self.assertEqual(parsed["actual_input_tokens"], 50)
        self.assertEqual(parsed["cache_read_tokens"], 100)
        self.assertEqual(parsed["cache_write_tokens"], 60)
        self.assertIn("uncached", parsed["input_semantics"])

    def test_usage_is_not_included_in_request_and_synthetic_never_actual(self):
        profiler = PayloadProfiler(enabled=True)
        records = [{"payload": {"input": "Hi"}, "kind": "provider_request", "provider": "openai", "submitted": True,
                    "response": {"usage": {"input_tokens": 42}}},
                   {"payload": {"input": "Hi"}, "kind": "synthetic_provider_request", "synthetic": True,
                    "response": {"usage": {"input_tokens": 999}}}]
        report = profile_records(records, profiler)
        self.assertEqual(report["totals"]["observed_model_calls"], 1)
        self.assertEqual(report["totals"]["usage_available_records"], 1)
        self.assertEqual(report["payloads"][0]["characters"], len('{"input":"Hi"}'))

    def test_redaction_by_omission_allowlists_and_local_permissions(self):
        canaries = ["private-customer-log-canary", "private-source-code-canary", "credential-header-canary", "sensitive-jira-canary"]
        profiler = PayloadProfiler(enabled=True)
        capture = profiler.observe("private-stage-canary", {"Authorization": "Bearer " + canaries[2],
            "sections": {"jira_evidence": canaries[3], "github_evidence": canaries[1], "grafana_evidence": canaries[0]}},
            scenario="private-scenario-canary", metadata={"correlation_id": "private-customer-identifier", "Authorization": canaries[2],
            "trace_id": "trace-1234567890abcdef1234567890abcdef"})
        profiler.attach_usage(capture, {"usage": {"input_tokens": 12, "credential": canaries[2],
                                                   "input_tokens_details": {"secret": canaries[2]}}})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            profiler.write(path)
            text = path.read_text()
            for canary in canaries + ["private-stage-canary", "private-scenario-canary", "private-customer-identifier"]:
                self.assertNotIn(canary, text)
            self.assertIn("trace-1234567890abcdef1234567890abcdef", text)
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)

    def test_default_capture_is_disabled_and_does_not_write(self):
        profiler = PayloadProfiler()
        self.assertIsNone(profiler.observe("understand", "secret"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "not-created.json"
            profiler.write(path)
            self.assertFalse(path.exists())

    def test_missing_optional_dependency_and_offline_asset_miss(self):
        with patch.dict(sys.modules, {"tiktoken": None}):
            tokenizer = LocalTokenizer("model")
            self.assertEqual(tokenizer.status, "unavailable")
            self.assertIsNone(tokenizer.count("hello"))
        package = types.ModuleType("tiktoken")
        loader = types.ModuleType("tiktoken.load")
        loader.read_file = lambda path: self.fail("Tokenizer attempted external IO")
        package.load = loader
        package.encoding_for_model = lambda model: loader.read_file("https://should-not-be-read.invalid")
        with patch.dict(sys.modules, {"tiktoken": package, "tiktoken.load": loader}):
            self.assertEqual(LocalTokenizer("model").status, "unavailable")

    def test_optional_tokenizer_section_and_request_counts_are_separate(self):
        profiler = PayloadProfiler(enabled=True)
        profiler.tokenizer.encoding = types.SimpleNamespace(encode=lambda text, **kw: list(text))
        profiler.tokenizer.status = "available"
        profiler.observe("understand", {"input": "hello"})
        row = profiler.report()["payloads"][0]
        self.assertEqual(row["serialized_request_token_estimate"], len('{"input":"hello"}'))
        self.assertEqual(row["section_content_token_estimates"]["user_request"], len('"hello"'))


class HarnessCaptureTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        configure_logging(stream=io.StringIO())

    async def test_observer_does_not_mutate_adapter_payload_or_outcomes(self):
        class MutatingObserver:
            def observe(self, stage, payload, **kwargs):
                payload.clear()
                raise RuntimeError("private-observer-error")
        for observer in (None, PayloadProfiler(), PayloadProfiler(enabled=True), MutatingObserver()):
            request, adapter = scenario("injection")
            state = await Harness(adapter, fixture_registry("injection"), policy(), profiler=observer).run(request)
            self.assertEqual(state.understanding["route"], "investigate_external")
            self.assertEqual(state.report["root_cause"], "Unknown")
            self.assertEqual(state.calls, 2)
            self.assertTrue(adapter.payloads[0][1]["request"])
            if isinstance(observer, PayloadProfiler) and observer.enabled:
                report = observer.report()
                self.assertEqual(report["totals"]["payloads"], state.model_calls)
                self.assertEqual(report["totals"]["observed_model_calls"], 0)
                self.assertEqual(report["stages"]["critic"]["boundary_counts"], {"deterministic_critic": 2})

    async def test_callback_boundary_is_intermediate_with_adapter_reported_usage(self):
        request, fixture = scenario("explain")
        async def callback(stage, payload, max_output_tokens):
            decision = await fixture.decide(stage, payload, max_output_tokens)
            return Decision(decision.value, 123, 10)
        observer = PayloadProfiler(enabled=True)
        await Harness(CallbackAdapter(callback, destination="local"), fixture_registry("explain"), policy(), profiler=observer).run(request)
        report = observer.report()
        self.assertEqual(report["totals"]["observed_model_calls"], 0)
        self.assertEqual(report["totals"]["usage_available_records"], 2)
        self.assertTrue(all(row["kind"] == "harness_intermediate" and row["usage"]["source"] == "adapter_reported" for row in report["payloads"]))

    async def test_benchmark_opt_in_profile_does_not_count_timing_repeats(self):
        from scripts.benchmark_optimization import capture
        from investigation_harness.evaluate import DATA
        observer = PayloadProfiler(enabled=True)
        # A single case is sufficient to exercise the real benchmark integration.
        with patch("scripts.benchmark_optimization.DATA") as data:
            dataset = json.loads(DATA.read_text())
            data.read_text.return_value = json.dumps({"cases": [dataset["cases"][0]]})
            result = await capture("C", 2, observer)
        report = observer.report()
        expected = sum(row["model_calls_including_deterministic_critic"] for row in result["cases"])
        self.assertEqual(report["totals"]["payloads"], expected)
        self.assertTrue(all(row["synthetic"] for row in report["payloads"]))
        self.assertTrue(all(all(row["checks"].values()) for row in result["cases"]))


if __name__ == "__main__":
    unittest.main()
