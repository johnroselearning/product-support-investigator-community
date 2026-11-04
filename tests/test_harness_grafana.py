"""Mocked subprocess bridge tests; no Grafana account, network, or live claims."""
import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch

from investigation_harness.fixtures import FULL_SCOPE
from investigation_harness.grafana import bind_grafana
from investigation_harness.registry import Registry


class Stdin:
    def __init__(self):
        self.data = b""

    def write(self, data):
        self.data += data

    async def drain(self):
        pass

    def close(self):
        pass


class Process:
    def __init__(self, result=None):
        self.stdin = Stdin()
        self.stdout = asyncio.StreamReader()
        if result is not None:
            self.stdout.feed_data(json.dumps(result).encode())
            self.stdout.feed_eof()
        self.returncode = None
        self.killed = False

    async def wait(self):
        self.returncode = 0

    def kill(self):
        self.killed = True


class GrafanaBridgeTests(unittest.IsolatedAsyncioTestCase):
    def registry(self):
        registry = Registry()
        bind_grafana(registry, url="https://grafana.invalid", token="synthetic-runtime-secret",
                     datasources={"loki-checkout": "loki", "prom-checkout": "prometheus"},
                     metrics=["http_errors_total"],
                     label_names={"tenant": "tenant_id", "environment": "env", "service": "service"})
        return registry

    def response(self, metric=False):
        observation = {"timestamp": "1793783100000000000", "timestamp_unit": "unix_nanoseconds",
                       "labels": {"tenant_id": "acme", "env": "production", "service": "checkout"},
                       "message": "request req-123 timed out"}
        if metric:
            observation.pop("message")
            observation.update(value="12", timestamp=1793783100, timestamp_unit="unix_seconds")
        return {"retrieval_status": "success", "observations": [observation], "limitations": []}

    async def test_fixed_loki_request_and_minimal_secret_environment(self):
        process = Process(self.response())
        with patch("investigation_harness.grafana.asyncio.create_subprocess_exec", new=AsyncMock(return_value=process)) as launch:
            result = await self.registry().bindings["search_logs"].handler({**FULL_SCOPE, "limit": 20}, 1)
        request = json.loads(process.stdin.data)
        self.assertEqual(request["scope"]["labels"], {"tenant_id": "acme", "env": "production", "service": "checkout"})
        self.assertNotIn("synthetic-runtime-secret", json.dumps([request, result]))
        self.assertEqual(launch.call_args.kwargs["env"]["GRAFANA_TOKEN"], "synthetic-runtime-secret")
        self.assertNotIn("HOME", launch.call_args.kwargs["env"])
        self.assertEqual(result["records"][0]["scope"]["tenant"], "acme")
        self.assertEqual(result["status"], "success")

    async def test_metric_scope_type_and_template(self):
        process = Process(self.response(metric=True))
        with patch("investigation_harness.grafana.asyncio.create_subprocess_exec", new=AsyncMock(return_value=process)):
            await self.registry().bindings["query_metrics"].handler(
                {**FULL_SCOPE, "datasource": "prom-checkout", "metric": "http_errors_total", "limit": 10}, 1)
        self.assertEqual(json.loads(process.stdin.data)["query"],
                         'http_errors_total{env="production",service="checkout",tenant_id="acme"}')
        for datasource, metric in (("loki-checkout", "http_errors_total"), ("prom-checkout", "unapproved_metric")):
            with self.assertRaises(ValueError):
                await self.registry().bindings["query_metrics"].handler(
                    {**FULL_SCOPE, "datasource": datasource, "metric": metric, "limit": 10}, 1)

    async def test_cross_scope_result_and_process_cancellation(self):
        response = self.response()
        response["observations"][0]["labels"]["tenant_id"] = "globex"
        with patch("investigation_harness.grafana.asyncio.create_subprocess_exec", new=AsyncMock(return_value=Process(response))):
            with self.assertRaises(ValueError):
                await self.registry().bindings["search_logs"].handler({**FULL_SCOPE, "limit": 20}, 1)
        process = Process()
        with patch("investigation_harness.grafana.asyncio.create_subprocess_exec", new=AsyncMock(return_value=process)):
            with self.assertRaises(TimeoutError):
                await self.registry().bindings["search_logs"].handler({**FULL_SCOPE, "limit": 20}, 0.01)
        self.assertTrue(process.killed)
        self.assertIsNotNone(process.returncode)
