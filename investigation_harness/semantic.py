"""Replaceable semantic decisions. No keyword router and no implicit network calls."""
from dataclasses import dataclass
from typing import Awaitable, Callable, Protocol


@dataclass
class Decision:
    value: dict
    input_tokens: int | None = None
    output_tokens: int | None = None


class SemanticAdapter(Protocol):
    simulated: bool
    destination: str

    async def decide(self, stage: str, payload: dict, max_output_tokens: int) -> Decision:
        """Stages: understand, choose, propose, report, revise. Return structured data.

        Host implementation must honor output limits, cancellation and destination
        policy. Credentials belong in its runtime closure, never in payloads.
        """
        ...


class CallbackAdapter:
    """Bridge a host's existing structured-output model without adding an SDK."""
    simulated = False

    def __init__(self, callback: Callable[..., Awaitable[Decision]], *, destination: str):
        self.callback = callback
        self.destination = destination

    async def decide(self, stage, payload, max_output_tokens):
        return await self.callback(stage, payload, max_output_tokens)


class Critic(Protocol):
    async def review(self, payload: dict, max_output_tokens: int) -> Decision:
        ...


class ModelCritic:
    def __init__(self, adapter):
        self.adapter = adapter
        self.destination = adapter.destination

    async def review(self, payload, max_output_tokens):
        return await self.adapter.decide("critic", payload, max_output_tokens)


class ConservativeCritic:
    """Deterministic baseline, explicitly not independent semantic verification."""
    destination = "local"

    async def review(self, payload, max_output_tokens):
        report = payload["conclusion"]
        conflicts = [e["id"] for e in payload["evidence"] if e.get("contradicts")]
        return Decision({
            "unsupported_claims": ["Strong claims require causal or attribution evidence"]
                if any(c["kind"] in ("causal", "blame", "deployed", "absence") for c in report["claims"]) else [],
            "contradictions": ["Retain conflicting evidence: " + ", ".join(conflicts)] if conflicts else [],
            "alternatives": ["Consider earlier failures and non-release explanations"]
                if any(c["kind"] == "causal" for c in report["claims"]) else [],
            "needed_evidence": report["unknowns"][:5],
        })
