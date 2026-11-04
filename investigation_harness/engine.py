"""One bounded investigation loop. All executions pass the same policy checks."""
import asyncio
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

from .contracts import (ContractError, FINDINGS, RECORD, REPORT, RESULT, SCOPE,
                        UNDERSTANDING, json_size, obj, string, validate)
from .policy import failure_reason, prepare, readiness, timestamp
from .reports import finalize_report, needs_critic
from .semantic import ConservativeCritic
from .state import Limits, State, safe, utcnow
from .service_map import ServiceMap

ROOT = Path(__file__).resolve().parents[1]
ROUTING = json.loads((Path(__file__).with_name("routing.json")).read_text())


class BudgetExhausted(Exception):
    pass


class Harness:
    def __init__(self, adapter, registry, policy, *, limits=None, critic=None, secrets=(), clock=time.monotonic, service_map=None):
        self.adapter, self.registry, self.policy = adapter, registry, policy
        self.limits, self.critic = limits or Limits(), critic or ConservativeCritic()
        self.secrets, self.clock = tuple(secrets), clock
        self.service_map = service_map or ServiceMap()

    async def run(self, request, *, parent_investigation_id=None):
        # A new runner is used per run. Configuration and policy never enter mutable state.
        if parent_investigation_id is not None:
            validate(parent_investigation_id, string(64))
            if not parent_investigation_id.isalnum():
                raise ValueError("Invalid parent investigation ID")
        self.state = State(parent_investigation_id=parent_investigation_id)
        self.started = self.clock()
        self.seen = set()
        self.references = None
        state = self.state
        state.budgets = asdict(self.limits)
        try:
            if json_size(request) > self.limits.input_bytes:
                raise ContractError("request_too_large")
            validate(request, obj({"messages": {"type": "array", "items": string(4000), "maxItems": 20},
                                   "artifacts": {"type": "array", "items": RECORD, "maxItems": 20},
                                   "scope": SCOPE}))
            request = safe(request, self.secrets)
            for key, value in request["scope"].items():
                state.scope.add(key, value, "user_provided", "request:scope")
            for i, artifact in enumerate(request["artifacts"]):
                # Caller-supplied facts are untrusted evidence, never access grants.
                self.add_evidence(artifact, "supplied", 0, source_locator=f"artifact:{i}")
            understanding = await self.model("understand", {"request": request, "routing": ROUTING,
                                                           "evidence": state.evidence}, UNDERSTANDING)
            if not understanding["goals"]:
                raise ContractError("empty_goals")
            state.understanding = understanding
            for item in understanding["scope"]:
                locator = item["locator"]
                if item["source"] == "user_provided":
                    sources = {f"message:{i}": text for i, text in enumerate(request["messages"])}
                    sources.update({f"artifact:{i}": a["excerpt"] for i, a in enumerate(request["artifacts"])})
                    if locator not in sources or item["value"] not in sources[locator]:
                        raise ContractError("unsupported_scope_provenance")
                state.scope.add(item["field"], item["value"], item["source"], locator)
            if any(ref not in {e["id"] for e in state.evidence} for ref in understanding["evidence_refs"]):
                raise ContractError("unsupported_evidence_reference")
            route = understanding["route"]
            state.selected_skill = ROUTING["skill"] if route.startswith("investigate_") else None
            state.event("routing", route=route, simulated=self.adapter.simulated)
            state.event("skill_selection", skill=state.selected_skill, status="selected" if state.selected_skill else "skipped")
            if state.selected_skill:
                # Load selected sections, with source locators and digests. Keep the
                # full skill on disk; do not resend all playbooks at every step.
                sections = {"SKILL.md": ("Investigation Principles", "Evidence Model", "Root Cause Assessment"),
                            "references/evidence-providers.md": ("Trust and privacy",)}
                self.references = {}
                for name, headings in sections.items():
                    text = (ROOT / name).read_text()
                    excerpts = [text.split("## " + heading + "\n", 1)[1].split("\n## ", 1)[0] for heading in headings]
                    self.references[name] = {"sha256": hashlib.sha256(text.encode()).hexdigest(),
                                             "sections": dict(zip(headings, excerpts))}
            if route == "clarify":
                state.questions.extend(understanding["ambiguities"][:1] or ["Which issue or environment should this request address?"])
                state.termination = "clarification_essential"
            elif route == "direct_answer":
                state.termination = "direct_answer"
            else:
                await self.investigate()
            await self.report()
        except BudgetExhausted:
            state.termination = "budget_exhausted"
            self.partial("Execution or model budget exhausted; retained evidence is incomplete.")
        except (ContractError, ValueError, TypeError, KeyError):
            state.termination = "invalid_contract"
            self.partial("A decision or input failed its contract; no further actions were executed.")
        except Exception:
            # Provider/model exception details may contain secrets or private payloads.
            state.termination = "execution_failure"
            self.partial("A component failed; its private exception content was not retained.")
        state.elapsed_seconds = round(max(0, self.clock() - self.started), 6)
        state.event("termination", reason=state.termination, count=state.calls,
                    duration_ms=round(state.elapsed_seconds * 1000), model_calls=state.model_calls,
                    cost_units=state.cost, reserved_tokens=state.reserved_tokens)
        return state

    def remaining(self):
        return self.limits.seconds - (self.clock() - self.started)

    async def model(self, stage, payload, schema=None, *, critic=False):
        state, limits = self.state, self.limits
        destination = getattr(self.critic, "destination", None) if critic else self.adapter.destination
        if destination != self.policy.model_destination and destination != "local":
            raise ContractError("model_destination_denied")
        if destination not in self.policy.destinations:
            raise ContractError("model_transfer_denied")
        payload = safe(deepcopy(payload), self.secrets)
        if schema:
            payload["response_contract"] = schema
        # One UTF-8 byte per token is a deliberately conservative reservation. Actual
        # provider counts, if returned, are recorded separately and never invented.
        reservation = json_size(payload) + limits.output_tokens * 4
        if (self.remaining() <= 0 or state.model_calls >= limits.model_calls or
                state.reserved_tokens + reservation > limits.model_tokens):
            raise BudgetExhausted()
        state.model_calls += 1
        state.reserved_tokens += reservation
        call = self.critic.review(payload, limits.output_tokens) if critic else self.adapter.decide(stage, payload, limits.output_tokens)
        try:
            decision = await asyncio.wait_for(call, timeout=min(self.remaining(), limits.call_seconds))
        except TimeoutError:
            raise BudgetExhausted() from None
        if self.remaining() <= 0:
            raise BudgetExhausted()
        if json_size(decision.value) > limits.output_tokens * 4:
            raise ContractError("model_output_too_large")
        counts = (decision.input_tokens, decision.output_tokens)
        if any(v is not None and (type(v) is not int or v < 0) for v in counts):
            raise ContractError("invalid_usage")
        state.usage.append({"stage": stage, "input_tokens": counts[0], "output_tokens": counts[1],
                            "measurement": "provider" if all(v is not None for v in counts) else "unavailable_or_partial",
                            "reserved_token_estimate": reservation, "estimate_method": "utf8_input_bytes_plus_output_byte_cap"})
        if (counts[0] or 0) + (counts[1] or 0) > reservation or (counts[1] or 0) > limits.output_tokens:
            raise BudgetExhausted()
        if schema:
            validate(decision.value, schema)
        return safe(decision.value, self.secrets)

    async def investigate(self):
        state = self.state
        while state.termination is None:
            choice = await self.model("choose", {"state": state.view(), "capabilities": self.registry.catalog(),
                                                "method": self.references,
                                                "service_leads": self.service_map.leads(state.scope.get("service"))},
                                      obj({"kind": string(values=("action", "report", "clarify")),
                                           "capability": string(80), "question": string(300),
                                           "hypotheses": REPORT["properties"]["hypotheses"]},
                                          ["kind", "capability", "question"]))
            if "hypotheses" in choice:
                known = {e["id"] for e in state.evidence}
                if any(not h["support"] or any(ref not in known for ref in h["support"] + h["contradictions"])
                       for h in choice["hypotheses"]):
                    raise ContractError("unsupported_hypothesis_reference")
                state.hypotheses = choice["hypotheses"]
            if choice["kind"] == "report":
                state.termination = ("no_authorized_useful_action" if state.actions and not any(
                    a["status"] in ("success", "partial", "empty") for a in state.actions) else "evidence_adequate")
                break
            if choice["kind"] == "clarify":
                state.questions.append(choice["question"] or "Which scope should the next check use?")
                state.termination = "clarification_essential"
                break
            name = choice["capability"]
            contract = self.registry.contract(name)
            if not contract:
                reason = "unavailable_tool" if name in self.registry.capabilities else "unavailable_capability"
                state.actions.append({"capability": name, "status": reason})
                state.event("readiness", status=reason)
                state.questions.append("The selected evidence capability has no available binding.")
                continue
            # Once loaded, the binding's real schema is visible to the semantic adapter.
            # Missing scope may be omitted here and resolved from retrieved context below.
            inputs_schema = {**contract["inputs"], "required": []}
            action = await self.model("propose", {"state": state.view(), "capability": name, "contract": contract},
                                      obj({"capability": string(80, [name]), "inputs": inputs_schema, "purpose": string(300)}))
            inputs = prepare(action, state, self.registry, self.policy, self.limits, use_defaults=False)
            checks = readiness(action, inputs, state, self.registry, self.policy, self.limits, self.remaining())
            reason = failure_reason(checks)
            state.event("readiness", status=reason or "ready", checks=checks)
            if reason:
                if reason in ("ambiguous_scope", "missing_input") and await self.recover_scope(name):
                    # Retry the original proposal after authorized retrieval. Every
                    # field is resolved and every policy check runs again.
                    inputs = prepare(action, state, self.registry, self.policy, self.limits, use_defaults=False)
                    checks = readiness(action, inputs, state, self.registry, self.policy, self.limits, self.remaining())
                    reason = failure_reason(checks)
                    state.event("readiness", status=reason or "ready", checks=checks)
            if reason == "missing_input":
                inputs = prepare(action, state, self.registry, self.policy, self.limits)
                checks = readiness(action, inputs, state, self.registry, self.policy, self.limits, self.remaining())
                reason = failure_reason(checks)
                state.event("readiness", status=reason or "ready", checks=checks)
            if reason:
                state.actions.append({"capability": name, "inputs": safe(inputs), "status": reason, "checks": checks})
                if reason in ("ambiguous_scope", "missing_input"):
                    # The semantic planner has already had conversation, issue retrieval
                    # and discovery alternatives available; ask one focused question.
                    field = next((k for k in contract["inputs"]["required"]
                                  if state.scope.conflict(k) or not inputs.get(k) or state.scope.inferred_only(k)), "scope")
                    state.questions.append(f"Which {field} should the next evidence check use?")
                    state.termination = "clarification_essential"
                else:
                    state.questions.append("The next evidence action was blocked: " + reason)
                    if reason == "limit_exceeded":
                        state.termination = "budget_exhausted"
                if state.termination:
                    break
                continue
            fingerprint = hashlib.sha256(json.dumps([name, inputs], sort_keys=True).encode()).hexdigest()
            if fingerprint in self.seen:
                state.termination = "no_progress"
                state.questions.append("Repeated evidence action suppressed; use a different discriminating check.")
                break
            self.seen.add(fingerprint)
            await self.execute(name, inputs)

    async def recover_scope(self, name):
        """Try declared, authorized discovery alternatives before asking for scope.

        No broad query is synthesized. Each alternative has to be independently
        ready with current scope; conflicting tenants can never trigger discovery.
        """
        state = self.state
        for alternative in self.registry.capabilities[name].alternatives:
            if any(a["capability"] == alternative for a in state.actions):
                continue
            action = {"capability": alternative, "inputs": {}, "purpose": "Resolve missing context"}
            inputs = prepare(action, state, self.registry, self.policy, self.limits, use_defaults=False)
            checks = readiness(action, inputs, state, self.registry, self.policy, self.limits, self.remaining())
            if failure_reason(checks):
                continue
            state.event("readiness", status="ready", checks=checks)
            before = deepcopy(state.scope.candidates)
            await self.execute(alternative, inputs)
            # An unavailable alternative does not suppress the original action's
            # focused clarification or erase evidence already collected.
            state.termination = None
            if before != state.scope.candidates:
                return True
        return False

    async def execute(self, name, inputs):
        state, limits = self.state, self.limits
        binding = self.registry.bindings[name]
        for attempt in range(limits.retries + 1):
            checks = readiness({"capability": name}, inputs, state, self.registry, self.policy, limits, self.remaining())
            if failure_reason(checks):
                raise BudgetExhausted()
            call_started = self.clock()
            state.calls += 1
            state.cost += binding.cost_units
            state.event("call", status="started", count=state.calls, capability=name, tool=binding.tool, provider=binding.provider)
            transient_timeout = False
            try:
                result = await asyncio.wait_for(binding.handler(deepcopy(inputs), min(self.remaining(), limits.call_seconds)),
                                                timeout=min(self.remaining(), limits.call_seconds))
                if self.remaining() <= 0:
                    raise BudgetExhausted()
                if json_size(result) > limits.response_bytes:
                    raise ContractError("result_too_large")
                validate(result, binding.output_schema or RESULT)
                # Always normalize to the shared contract, even for a custom binding.
                validate(result, RESULT)
                if len(result["records"]) > inputs["limit"]:
                    raise ContractError("result_limit")
                if result["status"] in ("empty", "unavailable", "execution_failure") and result["records"]:
                    raise ContractError("invalid_result_status")
                # Never ingest returned cross-scope data or authorize new tenants.
                for record in result["records"]:
                    for key in ("tenant", "environment", "repository", "datasource"):
                        if key in inputs and record["scope"].get(key) != inputs[key]:
                            raise ContractError("cross_scope_result")
                    allowed_scope = {"tenant": self.policy.tenants, "environment": self.policy.environments,
                                     "repository": self.policy.repositories, "datasource": self.policy.datasources}
                    if any(key in record["scope"] and record["scope"][key] not in allowed
                           for key, allowed in allowed_scope.items()):
                        raise ContractError("unauthorized_result_scope")
                    if any(key in record["scope"] and record["scope"][key] != value
                           for key, value in self.policy.user_scope):
                        raise ContractError("unauthorized_user_result_scope")
                if result["status"] == "success" and not result["records"]:
                    result["status"] = "empty"
            except BudgetExhausted:
                raise
            except Exception as error:
                transient_timeout = isinstance(error, TimeoutError)
                result = {"status": "execution_failure", "records": [], "resolved": {}, "next_cursor": "",
                          "limitations": ["Provider failure or invalid result; not application evidence."]}
            state.actions.append({"capability": name, "tool": binding.tool, "provider": binding.provider,
                                  "inputs": safe(inputs), "status": result["status"],
                                  "next_cursor": result["next_cursor"], "attempt": attempt + 1})
            state.event("call", status=result["status"], count=state.calls, capability=name,
                        tool=binding.tool, provider=binding.provider, retry_count=attempt,
                        duration_ms=round(max(0, self.clock() - call_started) * 1000),
                        result_count=len(result["records"]))
            if transient_timeout and attempt < limits.retries:
                continue
            before = len(state.evidence)
            for record in result["records"]:
                self.add_evidence(record, name, self.registry.capabilities[name].freshness_seconds)
            # Structured hints must be backed by returned evidence. Their provenance
            # stays retrieved, and conflicts are retained. They never change policy.
            for key, value in result["resolved"].items():
                match = next((e for e in state.evidence[before:] if e["scope"].get(key) == value), None)
                if match:
                    state.scope.add(key, value, "retrieved", match["id"])
            state.event("evidence_update", count=len(state.evidence) - before, status=result["status"],
                        evidence_refs=[e["id"] for e in state.evidence[before:]])
            state.questions.extend(safe(result["limitations"], self.secrets))
            if result["records"] and len(state.evidence) == before:
                state.termination = "no_progress"
            return

    def add_evidence(self, record, source, freshness, source_locator=None):
        state = self.state
        validate(record, RECORD)
        record = safe(deepcopy(record), self.secrets)
        if source_locator:
            record["supplied_at"] = source_locator
        identity = (record["locator"], record["excerpt"], json.dumps(record["scope"], sort_keys=True))
        for existing in state.evidence:
            if (existing["locator"], existing["excerpt"], json.dumps(existing["scope"], sort_keys=True)) == identity:
                existing["contradicts"] = list(dict.fromkeys(existing.get("contradicts", []) + record.get("contradicts", [])))
                return
        if len(state.evidence) >= self.limits.evidence_records:
            raise BudgetExhausted()
        stale = False
        try:
            stale = freshness > 0 and abs((datetime.now(timezone.utc) - timestamp(record["timestamp"])).total_seconds()) > freshness
        except (ValueError, TypeError):
            stale = True
        state.evidence.append({**record, "id": f"E{len(state.evidence) + 1}", "source": source,
                               "classification": "observed", "trust": "untrusted_data", "stale": stale})

    async def report(self):
        state = self.state
        report = await self.model("report", {"state": state.view(), "method": self.references}, REPORT)
        if needs_critic(report, state):
            for revision in range(self.limits.critic_revisions + 1):
                findings = await self.model("critic", {"goal": state.understanding, "evidence": state.evidence,
                                                        "conclusion": report}, FINDINGS, critic=True)
                state.critic_findings.append(findings)
                state.event("critic_findings", count=sum(len(v) for v in findings.values()))
                if not any(findings.values()) or revision == self.limits.critic_revisions:
                    break
                report = await self.model("revise", {"state": state.view(), "conclusion": report, "findings": findings}, REPORT)
        state.report = finalize_report(report, state)
        state.hypotheses = state.report["hypotheses"]
        if state.termination == "evidence_adequate" and not state.report["adequate"]:
            state.termination = "limited_analysis"

    def partial(self, gap):
        state = self.state
        state.questions.append(gap)
        state.report = finalize_report({"answer": "Limited analysis.", "claims": [], "unknowns": [],
                                        "hypotheses": [], "adequate": False}, state)
