"""Opt-in live bridge to the existing Grafana provider; fixed scoped queries only."""
import asyncio
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

from .contracts import RESULT
from .registry import Binding, input_contract


def bind_grafana(registry, *, url, token, datasources, metrics=(), label_names=None):
    """Trusted host configuration. Never call using model/tool-supplied configuration.

    datasources maps exact authorized UIDs to 'loki' or 'prometheus'. label_names
    maps tenant/environment/service to the actual enforced datasource labels.
    Policy must separately authorize the destination, user and scope.
    """
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment):
        raise ValueError("A trusted HTTPS Grafana URL is required")
    labels = dict(label_names or {})
    if set(labels) != {"tenant", "environment", "service"} or any(
            not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", v) for v in labels.values()) or len(set(labels.values())) != 3:
        raise ValueError("Explicit distinct tenant, environment, and service label mappings required")
    if any(v not in ("loki", "prometheus") for v in datasources.values()):
        raise ValueError("Unsupported datasource")
    if any(not re.fullmatch(r"[A-Za-z_:][A-Za-z0-9_:]*", m) for m in metrics):
        raise ValueError("Only fixed metric names supported")
    # Snapshot operator configuration; subsequent caller mutations cannot broaden it.
    datasources, metrics = dict(datasources), frozenset(metrics)

    for name, operation, datasource_type in (("search_logs", "logs", "loki"), ("query_metrics", "metrics", "prometheus")):
        async def handle(inputs, timeout, operation=operation, datasource_type=datasource_type):
            if datasources.get(inputs["datasource"]) != datasource_type:
                raise ValueError("Datasource not approved for this capability")
            selected = {labels[k]: inputs[k] for k in labels}
            request = {"evidence_id": "bounded-read", "purpose": "Inspect scoped incident evidence", "operation": operation,
                       "datasource_uid": inputs["datasource"], "scope": {
                           "start_time": inputs["start"], "end_time": inputs["end"], "labels": selected},
                       "identifiers": {"request_id": inputs["request_id"]} if inputs.get("request_id") else {}}
            if operation == "metrics":
                if inputs["metric"] not in metrics:
                    raise ValueError("Metric not approved")
                request["query"] = inputs["metric"] + "{" + ",".join(k + "=" + json.dumps(v) for k, v in sorted(selected.items())) + "}"
                request["step_seconds"] = 30
            # The existing synchronous urllib adapter runs in a cancellable child.
            # Minimal environment excludes unrelated credentials and observability egress.
            env = {"PATH": os.defpath, "GRAFANA_URL": url, "GRAFANA_TOKEN": token,
                   "PSI_LOG_LEVEL": "CRITICAL", "PSI_ENABLE_AUDIT_LOG": "false"}
            proc = await asyncio.create_subprocess_exec(sys.executable, "-m", "investigation_harness.grafana_worker",
                                                       stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                                                       stderr=asyncio.subprocess.DEVNULL, env=env,
                                                       cwd=str(Path(__file__).resolve().parents[1]))
            try:
                proc.stdin.write(json.dumps(request).encode())
                await proc.stdin.drain()
                proc.stdin.close()
                raw = await asyncio.wait_for(proc.stdout.read(262145), timeout)
                # read() may return before EOF; bounded accumulation is essential.
                while len(raw) <= 262144:
                    more = await proc.stdout.read(262145 - len(raw))
                    if not more:
                        break
                    raw += more
                if len(raw) > 262144:
                    raise ValueError("Provider output bound exceeded")
                await proc.wait()
                if proc.returncode:
                    raise ValueError("Provider process failed")
                result = json.loads(raw)
            finally:
                if proc.returncode is None:
                    proc.kill()
                    await proc.wait()
            status = result["retrieval_status"]
            rows = []
            scope = {k: inputs[k] for k in ("tenant", "environment", "service", "datasource", "start", "end")}
            for i, observation in enumerate(result["observations"][:inputs["limit"]]):
                if any(observation.get("labels", {}).get(label) != value for label, value in selected.items()):
                    raise ValueError("Provider returned out-of-scope labels")
                from datetime import datetime, timezone
                value = float(observation["timestamp"])
                if observation["timestamp_unit"] == "unix_nanoseconds":
                    value /= 1e9
                rows.append({"locator": f"grafana:{inputs['datasource']}:{observation['timestamp']}:{i}",
                             "excerpt": observation.get("message", "Metric sample: " + observation.get("value", "")),
                             "kind": operation, "scope": scope,
                             "timestamp": datetime.fromtimestamp(value, timezone.utc).isoformat()})
            normalized = {"success": "success", "empty": "empty"}.get(status, "unavailable")
            if rows and (len(result["observations"]) >= inputs["limit"] or any(
                    "truncat" in s.lower() or "bound" in s.lower() or "warning" in s.lower() for s in result["limitations"])):
                normalized = "partial"
            return {"status": normalized, "records": rows, "resolved": {}, "next_cursor": "",
                    "limitations": ["Grafana retrieval status: " + (status if status in {"success", "empty", "authentication_failed", "permission_denied", "query_error", "invalid_request", "invalid_response", "rate_limited", "unavailable", "not_configured", "response_too_large"} else "other_failure") + "; ingestion, source coverage and causal relevance are unverified."]}

        schema = input_contract(name)
        # The existing adapter does not support cursors; no invented pagination.
        schema["properties"].pop("cursor")
        registry.bind(Binding(name, "grafana", "providers.grafana.GrafanaProvider.retrieve:" + operation,
                              schema, handle, available=lambda: bool(url and token), output_schema=RESULT,
                              destination=url.rstrip("/")))
