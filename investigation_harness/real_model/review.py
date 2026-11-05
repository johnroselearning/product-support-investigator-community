"""Blind, claim-level semantic review; deterministic safety is never judge-owned."""
from copy import deepcopy
import hashlib
import json

from ..contracts import array, obj, string, validate

BOOL = {"type": "boolean"}
JUDGMENT = obj({
    "root_cause_score": {"type": "integer", "minimum": 0, "maximum": 2},
    "root_cause_supported": BOOL,
    "abstention": string(values=("correct_conclusion", "correct_abstention", "incorrect_abstention", "incorrect_confident_conclusion")),
    "claims": array(obj({"index": {"type": "integer", "minimum": 0, "maximum": 19},
                         "support": string(values=("supported", "unsupported", "uncertain")),
                         "explanation": string(1000)})),
    "limitations": obj({"identifies_missing_evidence": BOOL, "distinguishes_observation_inference": BOOL,
                         "explains_contradictions": BOOL, "avoids_unsupported_certainty": BOOL,
                         "explanation": string(2000)}),
    "explanation": string(2000),
})


def review_packet(gold, state):
    # No variant, provider, timings, run identity, scorer output or tool budget.
    candidate = {key: deepcopy(state.get("report", {}).get(key)) for key in
                 ("answer", "root_cause", "claims", "unknowns", "hypotheses")}
    packet = {"gold_answer": deepcopy(gold), "evidence": deepcopy(state.get("evidence", [])), "candidate": candidate}
    digest = hashlib.sha256(json.dumps(packet, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return packet, digest


def validate_judgment(judgment, packet):
    validate(judgment, JUDGMENT)
    claims = packet["candidate"].get("claims") or []
    if sorted(c["index"] for c in judgment["claims"]) != list(range(len(claims))):
        raise ValueError("Judge must evaluate every claim exactly once")
    if any(not c["explanation"].strip() for c in judgment["claims"]) or not judgment["explanation"].strip():
        raise ValueError("Review explanations required")
    unknown = packet["candidate"].get("root_cause") == "Unknown"
    expected_unknown = packet["gold_answer"]["abstention"] == "required"
    if unknown:
        classification = "correct_abstention" if expected_unknown else "incorrect_abstention"
        confident_wrong = judgment["abstention"] == "incorrect_confident_conclusion" and judgment["root_cause_score"] == 0
        if not confident_wrong and (judgment["abstention"] != classification or judgment["root_cause_score"] != (2 if expected_unknown else 0)):
            raise ValueError("Judge cannot override the candidate's explicit abstention")
    elif judgment["abstention"] not in ("correct_conclusion", "incorrect_confident_conclusion"):
        raise ValueError("Invalid non-abstention judgment")
    return judgment


async def model_review(adapter, packet, max_output_tokens=2000):
    payload = {**deepcopy(packet), "response_contract": JUDGMENT}
    # Criteria are part of the schema/envelope, not a second investigation.
    payload["response_contract"] = deepcopy(JUDGMENT)
    decision = await adapter.decide("judge", payload, max_output_tokens)
    return validate_judgment(decision.value, packet)


def calibrate(judge_labels, human_labels):
    """Compare independently saved labels. This command never calls a model."""
    rows = []
    for key in sorted(set(judge_labels) & set(human_labels)):
        judge, human = judge_labels[key], human_labels[key]
        if judge["response_hash"] != human["response_hash"]:
            raise ValueError("Calibration labels refer to different candidates")
        a, b = judge["judgment"], human["judgment"]
        validate(a, JUDGMENT)
        validate(b, JUDGMENT)
        left = {c["index"]: c["support"] for c in a["claims"]}
        right = {c["index"]: c["support"] for c in b["claims"]}
        if left.keys() != right.keys():
            raise ValueError("Calibration claim sets differ")
        rows.append({"key": key, "root_cause_agreement": a["root_cause_score"] == b["root_cause_score"],
                     "abstention_agreement": a["abstention"] == b["abstention"],
                     "claim_agreement": sum(left[i] == right[i] for i in left) / len(left) if left else None,
                     "judge_unsupported_claims_missed": [i for i in left if left[i] == "supported" and right[i] == "unsupported"]})
    return {"matched_examples": len(rows), "judge_only": sorted(set(judge_labels)-set(human_labels)),
            "human_only": sorted(set(human_labels)-set(judge_labels)), "results": rows}
