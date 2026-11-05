#!/usr/bin/env python3
"""Offline input-payload profiling. Artifacts contain metrics, never payload text.

No SDK, network access, or tokenizer is required. See PAYLOAD_PROFILING.md for
the input format, measurement semantics, privacy boundary, and capture limits.
"""
import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import re
import tempfile
from unittest.mock import patch

COMPONENTS = (
    "core_skill", "reference_guidance", "provider_guidance", "tool_schemas",
    "capability_catalog", "jira_evidence", "grafana_evidence", "github_evidence",
    "evidence_ledger", "conversation_history", "routing_context", "critic_context",
    "user_request", "other",
)
STAGES = ("understand", "skill_selection", "choose", "propose", "evidence_acquisition",
          "investigation", "critic", "report", "revise", "other")
KINDS = ("harness_intermediate", "scripted_adapter", "deterministic_critic",
         "provider_request", "synthetic_provider_request", "source_artifact")
ALIASES = {"request_understanding": "understand", "capability_selection": "choose",
           "critic_validation": "critic", "final_response": "report"}
EVIDENCE = {"jira_evidence", "grafana_evidence", "github_evidence", "evidence_ledger"}
INSTRUCTIONS = {"core_skill", "reference_guidance", "provider_guidance"}
PROVIDERS = {"openai", "anthropic", "adapter", "unknown"}


def serialized(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def estimate(text):
    return math.ceil(len(text) / 4)


def percent(part, whole):
    return round(100 * part / whole, 3) if whole else 0.0


def normalized(text):
    return "\n".join(" ".join(line.split()) for line in text.splitlines() if line.strip())


def text_lines(value):
    if isinstance(value, str):
        yield from value.splitlines()
    elif isinstance(value, dict):
        for item in value.values():
            yield from text_lines(item)
    elif isinstance(value, list):
        for item in value:
            yield from text_lines(item)


def shingles(text):
    tokens = re.findall(r"\w+|[^\w\s]", text)
    return Counter(tuple(tokens[n:n+5]) for n in range(max(1, len(tokens)-4)))


def classify(text):
    """Conservative fallback; a keyword is evidence of a topic, not provenance."""
    patterns = (
        ("core_skill", r"(?i)(?:name:\s*product-support-investigator|## Investigation Principles)"),
        ("provider_guidance", r"(?i)(?:provider guidance|retrieval efficiency|trust and privacy)"),
        ("reference_guidance", r"(?i)(?:references/[\w-]+\.md|investigation methodology)"),
        ("grafana_evidence", r"(?i)\b(?:grafana|loki|prometheus)\b"),
        ("github_evidence", r"(?i)\b(?:github|pull request|commit sha)\b"),
        ("jira_evidence", r"(?i)\b(?:jira|issue key)\b"),
    )
    for component, pattern in patterns:
        if re.search(pattern, text):
            return component, 0.55, "regex_fallback"
    return "other", 0.0, "unknown"


def evidence_component(record):
    provider = record.get("provider", record.get("source", ""))
    if provider in {"jira", "fetch_issue"}:
        return "jira_evidence"
    if provider in {"grafana", "search_logs", "query_metrics", "retrieve_trace", "deployment_metadata", "discover_service"}:
        return "grafana_evidence"
    if provider in {"github", "read_repository_file", "compare_revisions", "list_commits",
                    "read_repository_issue", "read_pull_request"}:
        return "github_evidence"
    return "evidence_ledger"


def sections_for(payload):
    """Partition canonical JSON without dropping keys or double-counting content.

    Labelled sections use their contents in order (labels are capture metadata).
    Everything else includes JSON punctuation/keys, assigned to `other` unless
    inside a known component. This is a local serialization, not provider wire
    framing. Non-text modality costs cannot be inferred from JSON characters.
    """
    pieces = []

    def emit(text, component="other", confidence=1.0, method="serialization"):
        if text:
            pieces.append({"text": text, "component": component,
                           "confidence": confidence, "classification": method})

    def block(value, component, confidence=1.0, method="structured"):
        emit(serialized(value), component, confidence, method)

    def message_content(value, default, confidence=1.0, method="role"):
        if isinstance(value, list):
            emit("[")
            for n, item in enumerate(value):
                if n:
                    emit(",")
                if isinstance(item, dict) and ("component" in item or item.get("type") == "tool_result"):
                    if item.get("type") == "tool_result" and "component" not in item:
                        block(item, *classify(serialized(item)))
                    else:
                        walk(item)
                else:
                    block(item, default, confidence, method)
            emit("]")
        else:
            if isinstance(value, dict) and "component" in value and "content" in value:
                walk(value)
            else:
                block(value, default, confidence, method)

    def walk(value, context=None, *, evidence=False, message_role=None):
        if context is not None:
            block(value, *context)
            return
        if isinstance(value, dict):
            if "component" in value and "content" in value:
                component = value["component"]
                known = isinstance(component, str) and component in COMPONENTS
                block(value, component if known else "other", 1.0 if known else 0.0,
                      "explicit" if known else "unknown_label")
                return
            record_component = evidence_component(value) if evidence else None
            role = value.get("role", message_role)
            emit("{", "evidence_ledger" if evidence else "other")
            for index, (key, item) in enumerate(value.items()):
                emit(("," if index else "") + serialized(key) + ":", "evidence_ledger" if evidence else "other")
                if evidence:
                    block(item, record_component if key in {"excerpt", "body", "observations", "content", "message"} else "evidence_ledger")
                elif key in {"tools", "functions", "response_contract", "response_format", "contract"}:
                    block(item, "tool_schemas")
                elif key in {"capabilities", "capability_catalog"}:
                    block(item, "capability_catalog")
                elif key == "method" and isinstance(item, dict):
                    emit("{")
                    for n, (name, content) in enumerate(item.items()):
                        emit(("," if n else "") + serialized(name) + ":")
                        component = "core_skill" if name == "SKILL.md" else "provider_guidance" if name in {
                            "references/evidence-providers.md", "references/grafana.md", "references/github.md"} else "reference_guidance"
                        block(content, component)
                    emit("}")
                elif key in {"evidence", "artifacts", "records"} and isinstance(item, list):
                    emit("[", "evidence_ledger")
                    for n, record in enumerate(item):
                        if n:
                            emit(",", "evidence_ledger")
                        walk(record, evidence=True)
                    emit("]", "evidence_ledger")
                elif key in {"routing", "scope", "goal", "skill", "categories", "workflow", "target_system",
                             "work_item_id", "evidence_scope", "requested_action", "service_leads", "capability"}:
                    block(item, "routing_context")
                elif key in {"conclusion", "findings", "critic_findings"}:
                    block(item, "critic_context")
                elif key in {"actions", "questions", "assumptions", "hypotheses", "history"}:
                    block(item, "conversation_history")
                elif key in {"messages", "input"} and isinstance(item, list):
                    emit("[")
                    user_positions = [n for n, msg in enumerate(item) if isinstance(msg, str) or
                                      isinstance(msg, dict) and msg.get("role") == "user"]
                    for n, msg in enumerate(item):
                        if n:
                            emit(",")
                        last_user = bool(user_positions) and n == user_positions[-1]
                        if isinstance(msg, str):
                            block(msg, "user_request" if last_user else "conversation_history")
                        else:
                            walk(msg, message_role="user" if last_user else "history" if
                                 isinstance(msg, dict) and msg.get("role") == "user" else None)
                    emit("]")
                elif key in {"system", "instructions"}:
                    component, confidence, method = classify(item if isinstance(item, str) else serialized(item))
                    message_content(item, component, confidence, method)
                elif key == "input" and isinstance(item, str):
                    block(item, "user_request")
                elif key in {"content", "output"} and role in {"assistant", "history"}:
                    message_content(item, "conversation_history")
                elif key == "content" and role == "user":
                    # Preserve explicit labels on mixed text/image blocks.
                    message_content(item, "conversation_history" if message_role == "history" else "user_request")
                elif key in {"content", "output"} and (role in {"tool", "function"} or
                        value.get("type") == "function_call_output"):
                    component = evidence_component(value)
                    if component == "evidence_ledger":
                        block(item, *classify(item if isinstance(item, str) else serialized(item)))
                    else:
                        block(item, component)
                elif key == "content" and role in {"system", "developer"}:
                    message_content(item, *classify(item if isinstance(item, str) else serialized(item)))
                elif key in {"role", "type", "name", "model", "max_tokens", "max_output_tokens", "stream"}:
                    block(item, "other", 1.0, "protocol_metadata")
                else:
                    walk(item)
            emit("}", "evidence_ledger" if evidence else "other")
        elif isinstance(value, list):
            emit("[")
            for n, item in enumerate(value):
                if n:
                    emit(",")
                walk(item)
            emit("]")
        elif isinstance(value, str):
            block(value, *classify(value))
        else:
            block(value, "other", 1.0, "scalar")

    if isinstance(payload, dict) and "sections" in payload:
        labelled = payload["sections"]
        if isinstance(labelled, dict):
            labelled = [{"component": key, "content": value} for key, value in labelled.items()]
        if not isinstance(labelled, list):
            raise ValueError("sections must be an object or array")
        for section in labelled:
            if not isinstance(section, dict) or "content" not in section:
                raise ValueError("Each section needs content")
            component = section.get("component", section.get("label"))
            known = isinstance(component, str) and component in COMPONENTS
            content = section["content"]
            emit(content if isinstance(content, str) else serialized(content), component if known else "other",
                 1.0 if known else 0.0, "explicit" if known else "unknown_label")
        # Provider fields outside sections still belong to the request.
        remaining = {k: v for k, v in payload.items() if k != "sections"}
        if remaining:
            walk(remaining)
    elif payload not in (None, "", {}, []):
        walk(payload)
    return pieces


def usage_metadata(response, provider="unknown", *, adapter_reported=False):
    """Only allowlisted numeric fields escape; preserve provider usage semantics."""
    if not isinstance(response, dict):
        return None
    usage = response.get("usage")
    if not isinstance(usage, dict):
        # Anthropic streaming message_start; message_delta can be supplied separately.
        message = response.get("message", {})
        usage = message.get("usage") if isinstance(message, dict) else None
    if not isinstance(usage, dict):
        return None
    provider = provider if provider in PROVIDERS else "unknown"
    if adapter_reported and provider == "unknown":
        provider = "adapter"
    if provider == "unknown":
        if any(k in usage for k in ("cache_read_input_tokens", "cache_creation_input_tokens")):
            provider = "anthropic"
        elif "prompt_tokens" in usage or "input_tokens_details" in usage:
            provider = "openai"
    def count(key):
        number = usage.get(key)
        return number if type(number) is int and number >= 0 else None
    raw = {key: count(key) for key in ("input_tokens", "output_tokens", "prompt_tokens", "completion_tokens",
           "total_tokens", "cache_read_input_tokens", "cache_creation_input_tokens") if count(key) is not None}
    for key in ("input_tokens_details", "prompt_tokens_details", "cache_creation"):
        details = usage.get(key)
        if isinstance(details, dict):
            allowed = ("cached_tokens", "ephemeral_5m_input_tokens", "ephemeral_1h_input_tokens")
            clean_details = {k: v for k, v in details.items() if k in allowed and type(v) is int and v >= 0}
            if clean_details:
                raw[key] = clean_details
    if not raw:
        return None
    actual_input = count("prompt_tokens") if "prompt_tokens" in usage else count("input_tokens")
    actual_output = count("completion_tokens") if "completion_tokens" in usage else count("output_tokens")
    cached = count("cache_read_input_tokens")
    if cached is None:
        details = raw.get("input_tokens_details", raw.get("prompt_tokens_details", {}))
        cached = details.get("cached_tokens")
    return {"source": "adapter_reported" if adapter_reported else "provider_response",
            "provider": provider, "raw_usage": raw, "actual_input_tokens": actual_input,
            "actual_output_tokens": actual_output, "cache_read_tokens": cached,
            "cache_write_tokens": count("cache_creation_input_tokens"),
            "cache_hit_indicator": cached > 0 if cached is not None else None,
            "input_semantics": "uncached input; cache reads/writes are separate" if provider == "anthropic" else
                "provider input field; cached tokens are a subset for OpenAI" if provider == "openai" else
                "provider/adapter semantics unspecified; do not combine across providers"}


class LocalTokenizer:
    """Optional tiktoken, using existing cache assets only; never download assets."""
    def __init__(self, model=None):
        self.encoding = None
        self.status = "disabled" if not model else "unavailable"
        if model:
            try:
                import tiktoken
                import tiktoken.load
                # Cache hits are read by read_file_cached before read_file. Prevent
                # a cache miss from opening a URL (or arbitrary local model path).
                with patch.object(tiktoken.load, "read_file", side_effect=RuntimeError("Offline tokenizer cache miss")):
                    self.encoding = tiktoken.encoding_for_model(model)
                self.status = "available"
            except (ImportError, KeyError, ValueError, RuntimeError, OSError):
                self.status = "unavailable"

    def count(self, text):
        return len(self.encoding.encode(text, disallowed_special=())) if self.encoding else None


@dataclass(frozen=True)
class CaptureLimits:
    max_payload_characters: int = 524288
    max_total_characters: int = 16777216
    max_records: int = 2000
    max_sections: int = 2048
    max_near_pairs: int = 10000
    max_near_characters: int = 16000

    def __post_init__(self):
        if any(type(v) is not int or v < 1 for v in vars(self).values()):
            raise ValueError("Capture limits must be positive integers")


class PayloadProfiler:
    """Bounded in-memory observer. Writing is explicit and always metadata-only."""
    def __init__(self, *, enabled=False, model=None, limits=None):
        self.enabled = enabled
        self.limits = limits or CaptureLimits()
        self.tokenizer = LocalTokenizer(model) if enabled else LocalTokenizer()
        self.records = []
        self.skipped = Counter()
        self.characters = 0
        self._key = os.urandom(32)

    def digest(self, value):
        return hmac.new(self._key, value.encode("utf-8"), hashlib.sha256).hexdigest()

    def identifier(self, value, *, synthetic=False):
        if not isinstance(value, str):
            return None
        if re.fullmatch(r"(?:trace-|corr-|inv-|PSI-)?[a-fA-F0-9-]{16,64}", value):
            return value
        if synthetic and re.fullmatch(r"[A-Za-z0-9_-]{1,80}", value):
            return value
        return "hmac:" + self.digest(value)

    def observe(self, stage, payload, *, kind="harness_intermediate", scenario=None,
                comparison_group="default", provider="unknown", model=None, metadata=None,
                synthetic=False, submitted=False, response=None):
        if not self.enabled:
            return None
        if len(self.records) >= self.limits.max_records:
            self.skipped["record_limit"] += 1
            return None
        size = len(payload) if isinstance(payload, str) else len(serialized(payload))
        if size > self.limits.max_payload_characters or self.characters + size > self.limits.max_total_characters:
            self.skipped["character_limit"] += 1
            return None
        pieces = sections_for(payload)
        if len(pieces) > self.limits.max_sections:
            self.skipped["section_limit"] += 1
            return None
        text = "".join(p["text"] for p in pieces)
        stage = ALIASES.get(stage, stage)
        stage = stage if stage in STAGES else "other"
        kind = kind if kind in KINDS else "harness_intermediate"
        provider = provider if provider in PROVIDERS else "unknown"
        # Stage, boundary, provider and model must match for prefix comparisons.
        group = self.digest(serialized([comparison_group, stage, kind, provider, model]))
        row = {"stage": stage, "kind": kind, "scenario": self.identifier(scenario, synthetic=synthetic),
               "comparison_group_hash": group, "provider": provider,
               "model_hash": self.digest(model) if isinstance(model, str) else None,
               "synthetic": synthetic, "observed_model_calls": int(kind == "provider_request" and submitted and not synthetic),
               "metadata": {key: self.identifier(value) for key, value in (metadata or {}).items()
                            if key in {"trace_id", "correlation_id", "investigation_id", "parent_investigation_id", "work_item_id"}},
               "usage": usage_metadata(response, provider), "_text": text, "_pieces": pieces}
        self.records.append(row)
        self.characters += size
        return len(self.records) - 1

    def attach_usage(self, record, response, *, adapter_reported=False):
        if record is not None and 0 <= record < len(self.records):
            row = self.records[record]
            # Simulated counts never become actual usage, even if supplied.
            if not row["synthetic"] and row["kind"] not in {"scripted_adapter", "deterministic_critic", "synthetic_provider_request"}:
                row["usage"] = usage_metadata(response, row["provider"], adapter_reported=adapter_reported)

    def report(self):
        groups = defaultdict(list)
        for row in self.records:
            groups[row["comparison_group_hash"]].append(row)
        prefixes = {}
        prefix_rows = []
        for group, rows in groups.items():
            shared = os.path.commonprefix([r["_text"] for r in rows]) if len(rows) >= 2 else ""
            # commonprefix is literal character order, without normalization/reordering.
            prefixes[group] = len(shared) if len(rows) >= 2 else None
            total = sum(len(r["_text"]) for r in rows)
            prefix_rows.append({"comparison_group_hash": group, "stage": rows[0]["stage"],
                "kind": rows[0]["kind"], "payloads": len(rows), "comparable": len(rows) >= 2,
                "stable_prefix_characters": len(shared) if len(rows) >= 2 else None,
                "stable_prefix_tokens_estimate": estimate(shared) if len(rows) >= 2 else None,
                "dynamic_characters_total": total - len(shared) * len(rows) if len(rows) >= 2 else None,
                "shared_prefix_percentage": percent(len(shared) * len(rows), total) if len(rows) >= 2 else None})
        measured = []
        all_blocks = defaultdict(list)
        all_lines = defaultdict(list)
        near_candidates = {}
        for index, row in enumerate(self.records):
            chars, confidence = Counter(), Counter()
            blocks, lines = Counter(), Counter()
            for piece in row["_pieces"]:
                text, component = piece["text"], piece["component"]
                chars[component] += len(text)
                confidence[piece["classification"]] += len(text)
                clean = normalized(text)
                if len(clean) >= 32:
                    blocks[clean] += 1
                    all_blocks[clean].append((index, component))
                    # Bound retained candidates and text; exact matches are handled separately.
                    if len(clean) <= self.limits.max_near_characters and len(near_candidates) < 512:
                        near_candidates.setdefault((component, clean), index)
                # Decode JSON strings to retain original line boundaries.
                try:
                    value = json.loads(text)
                except (ValueError, TypeError):
                    value = text
                for line in text_lines(value):
                    line = " ".join(line.split())
                    if len(line) >= 16:
                        lines[line] += 1
                        all_lines[line].append((index, component))
            size = len(row["_text"])
            block_chars = sum(len(k) * (n - 1) for k, n in blocks.items())
            line_chars = sum(len(k) * (n - 1) for k, n in lines.items())
            unknown = confidence["unknown"] + confidence["unknown_label"]
            prefix = prefixes[row["comparison_group_hash"]]
            item = {key: value for key, value in row.items() if not key.startswith("_")}
            item.update({"id": index, "characters": size, "content_hmac": self.digest(row["_text"]),
                "input_tokens_estimate": estimate(row["_text"]),
                "serialized_request_token_estimate": self.tokenizer.count(row["_text"]),
                "components": {c: {"characters": n, "tokens_estimate": math.ceil(n / 4),
                                    "percentage": percent(n, size)} for c, n in sorted(chars.items())},
                "classification": {"characters_by_method": dict(confidence),
                    "weighted_confidence": round(sum(len(p["text"]) * p["confidence"] for p in row["_pieces"]) / size, 4) if size else 1.0,
                    "unknown_characters": unknown, "unknown_percentage": percent(unknown, size)},
                "section_content_token_estimates": {c: sum(self.tokenizer.count(p["text"]) or 0 for p in row["_pieces"] if p["component"] == c)
                                                    for c in chars} if self.tokenizer.encoding else None,
                "duplicates": {"identical_blocks_characters": block_chars, "normalized_lines_characters": line_chars,
                    "duplicate_percentage": percent(max(block_chars, line_chars), size)},
                "stable_prefix_characters": prefix,
                "dynamic_characters": size - prefix if prefix is not None else None,
                "stable_prefix_percentage": percent(prefix, size) if prefix is not None else None})
            # Synthetic input cannot contribute observed usage even when an envelope includes it.
            if row["synthetic"] or row["kind"] in {"scripted_adapter", "deterministic_critic", "synthetic_provider_request", "source_artifact"}:
                item["usage"] = None
            measured.append(item)
        def repeated_sources(sources):
            repeated = []
            for content, occurrences in sources.items():
                if len(occurrences) > 1:
                    repeated.append({"content_hmac": self.digest(content), "characters": len(content),
                        "occurrences": len(occurrences), "payloads": len({i for i, _ in occurrences}),
                        "components": sorted({c for _, c in occurrences}),
                        "repeated_characters": len(content) * (len(occurrences) - 1)})
            return sorted(repeated, key=lambda r: r["repeated_characters"], reverse=True)
        repeated = repeated_sources(all_blocks)
        repeated_lines = repeated_sources(all_lines)
        near, comparisons = [], 0
        candidates = list(near_candidates)
        candidate_shingles = {content: shingles(content) for _, content in candidates}
        eligible_candidates = sum(len({c for _, c in occurrences}) for content, occurrences in all_blocks.items()
                                  if len(content) <= self.limits.max_near_characters)
        possible_pairs = sum(1 for i, (c, a) in enumerate(candidates) for d, b in candidates[i+1:]
                             if c == d and a != b and min(len(a), len(b)) / max(len(a), len(b)) >= .8)
        for i, (component, left) in enumerate(candidates):
            for other, right in candidates[i+1:]:
                if comparisons >= self.limits.max_near_pairs:
                    break
                if component != other or left == right or min(len(left), len(right)) / max(len(left), len(right)) < .8:
                    continue
                comparisons += 1
                left_set, right_set = candidate_shingles[left], candidate_shingles[right]
                ratio = sum((left_set & right_set).values()) / sum((left_set | right_set).values()) if left_set or right_set else 0.0
                if ratio >= .85:
                    near.append({"component": component, "left_hmac": self.digest(left), "right_hmac": self.digest(right),
                                 "similarity": round(ratio, 4), "left_characters": len(left), "right_characters": len(right)})
        by_stage = {stage: aggregate([r for r in measured if r["stage"] == stage]) for stage in STAGES}
        by_scenario = defaultdict(list)
        for row in measured:
            by_scenario[row["scenario"]].append(row)
        scenarios = [{"scenario": name, **aggregate(rows)} for name, rows in by_scenario.items()]
        scenarios.sort(key=lambda r: r["total_input_tokens_estimate"], reverse=True)
        repeated_instructions = sum(r["repeated_characters"] for r in repeated if set(r["components"]) <= INSTRUCTIONS)
        repeated_evidence = sum(r["repeated_characters"] for r in repeated if set(r["components"]) <= EVIDENCE)
        return {"schema_version": "1", "measurement": "offline_payload_profile",
            "methods": {"character_estimate": "ceil(unicode_characters/4); canonical compact JSON, or labelled section contents",
                "tokenizer": self.tokenizer.status,
                "tokenizer_counts": "section content estimates and serialized-request estimates; exclude provider framing and non-text modality costs",
                "duplicates": "normalized blocks >=32 chars and lines >=16 chars; percentage is max of the two within each payload, not their sum",
                "near_duplicates": "same-component weighted 5-token shingle Jaccard >=0.85; length ratio >=0.8; bounded unique candidates",
                "prefix": "literal local serialization prefix among same group/stage/boundary/provider/model; singleton unknown",
                "privacy": "no raw payloads/customer keys/paths/errors; per-process keyed HMACs; safe internal IDs only",
                "usage": "provider response or adapter-reported fields only; never inferred from estimates/reservations",
                "caching": "shared prefix does not establish cache eligibility, hits, pricing, or discounts"},
            "limits": vars(self.limits), "skipped": dict(self.skipped),
            "totals": aggregate(measured), "stages": by_stage,
            "scenarios": scenarios, "largest_payloads": sorted(measured, key=lambda r: r["characters"], reverse=True)[:10],
            "prefix_groups": prefix_rows,
            "repetition": {"repeated_instruction_characters": repeated_instructions,
                "repeated_instruction_tokens_estimate": math.ceil(repeated_instructions / 4),
                "repeated_evidence_characters": repeated_evidence,
                "repeated_evidence_tokens_estimate": math.ceil(repeated_evidence / 4),
                "largest_identical_blocks": repeated[:20], "largest_normalized_lines": repeated_lines[:20],
                "repeated_line_characters": sum(r["repeated_characters"] for r in repeated_lines),
                "near_duplicate_sections": near[:50],
                "near_matches_found": len(near), "near_comparisons": comparisons,
                "near_comparison_limit_reached": comparisons < possible_pairs,
                "near_candidates_considered": len(candidates),
                "near_candidate_limit_reached": eligible_candidates > len(candidates),
                "near_oversize_unique_sections": sum(len({c for _, c in occurrences}) for content, occurrences in all_blocks.items()
                                                     if len(content) > self.limits.max_near_characters),
                "near_candidate_limit": 512}, "payloads": measured}

    def write(self, path):
        if self.enabled:
            write_report(path, self.report())


def aggregate(rows):
    total_chars = sum(r["characters"] for r in rows)
    components = Counter()
    for row in rows:
        components.update({c: v["characters"] for c, v in row["components"].items()})
    counts = [r["input_tokens_estimate"] for r in rows]
    comparable = [r for r in rows if r["stable_prefix_characters"] is not None]
    usage_groups = defaultdict(list)
    for row in rows:
        usage = row.get("usage")
        if usage:
            usage_groups[(usage["provider"], usage["source"], usage["input_semantics"])].append(usage)
    observed = []
    for (provider, source, semantics), usages in usage_groups.items():
        fields = ("actual_input_tokens", "actual_output_tokens", "cache_read_tokens", "cache_write_tokens")
        observed.append({"provider": provider, "source": source, "input_semantics": semantics, "records": len(usages),
            **{field: sum(u[field] for u in usages if u[field] is not None) if any(u[field] is not None for u in usages) else None for field in fields},
            "cache_hit_records": sum(u["cache_hit_indicator"] is True for u in usages)})
    return {"payloads": len(rows), "observed_model_calls": sum(r["observed_model_calls"] for r in rows),
        "boundary_counts": dict(Counter(r["kind"] for r in rows)), "characters": total_chars,
        "total_input_tokens_estimate": sum(counts), "mean_input_tokens_estimate": round(sum(counts) / len(counts), 3) if counts else 0,
        "maximum_input_tokens_estimate": max(counts, default=0),
        "components": {c: {"characters": n, "tokens_estimate": sum(r["components"].get(c, {}).get("tokens_estimate", 0) for r in rows),
                            "percentage": percent(n, total_chars)} for c, n in components.most_common()},
        "duplicate_percentage": percent(sum(max(r["duplicates"]["identical_blocks_characters"], r["duplicates"]["normalized_lines_characters"]) for r in rows), total_chars),
        "stable_prefix_percentage": percent(sum(r["stable_prefix_characters"] for r in comparable), sum(r["characters"] for r in comparable)) if comparable else None,
        "prefix_comparable_payloads": len(comparable),
        "unknown_percentage": percent(sum(r["classification"]["unknown_characters"] for r in rows), total_chars),
        "usage_available_records": sum(r.get("usage") is not None for r in rows), "observed_usage_by_provider": observed}


def write_report(path, report):
    """Local filesystem only; atomic replacement, owner-only file permissions."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".psi-profile-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, allow_nan=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def parse_records(text, input_format="auto"):
    if not text.strip():
        return []
    if input_format not in {"auto", "json", "jsonl"}:
        raise ValueError("Unknown input format")
    if input_format == "jsonl":
        records = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            if input_format == "json":
                raise
            return parse_records(text, "jsonl")
        if isinstance(value, dict) and isinstance(value.get("captures"), list):
            records = value["captures"]
        elif isinstance(value, list):
            records = [{"messages": value}] if value and all(isinstance(v, dict) and "role" in v for v in value) else value
        else:
            records = [value]
    return records


def profile_records(records, profiler):
    for record in records:
        envelope = isinstance(record, dict) and "payload" in record
        metadata = record if envelope else {}
        payload = record["payload"] if envelope else record
        if not envelope and isinstance(payload, dict):
            # A response is optional capture metadata, never request input.
            payload = {k: v for k, v in payload.items() if k not in {"response", "usage"}}
        profiler.observe(metadata.get("stage", "other"), payload,
            kind=metadata.get("kind", "harness_intermediate"), scenario=metadata.get("scenario"),
            comparison_group=metadata.get("comparison_group", "default"), provider=metadata.get("provider", "unknown"),
            model=metadata.get("model", payload.get("model") if isinstance(payload, dict) else None),
            metadata=metadata.get("metadata"), synthetic=metadata.get("synthetic") is True,
            submitted=metadata.get("submitted") is True,
            response=metadata.get("response") if envelope else record if isinstance(record, dict) else None)
    return profiler.report()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--format", choices=("auto", "json", "jsonl"), default="auto")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", help="Optional installed tiktoken model; existing cached assets only")
    parser.add_argument("--max-file-bytes", type=int, default=33554432)
    for name, default in vars(CaptureLimits()).items():
        parser.add_argument("--" + name.replace("_", "-"), type=int, default=default)
    args = parser.parse_args(argv)
    try:
        if args.max_file_bytes < 1:
            raise ValueError("Invalid input bound")
        if args.input.resolve() == args.output.resolve():
            raise ValueError("Input and output paths must differ")
        # Bounded read even if the file changes after stat().
        with args.input.open("rb") as stream:
            raw = stream.read(args.max_file_bytes + 1)
        if len(raw) > args.max_file_bytes:
            raise ValueError("Input file exceeds capture limit")
        limits = CaptureLimits(**{name: getattr(args, name) for name in vars(CaptureLimits())})
        profiler = PayloadProfiler(enabled=True, model=args.model, limits=limits)
        report = profile_records(parse_records(raw.decode("utf-8"), args.format), profiler)
        write_report(args.output, report)
    except (ValueError, TypeError, OSError, RecursionError):
        # Never echo parser errors, source lines, paths, or provider exceptions.
        parser.exit(2, "Cannot profile input: invalid JSON/shape, unreadable file, or capture limit. No payload text was written.\n")
    print(serialized({"payloads": report["totals"]["payloads"], "skipped": report["skipped"],
                      "estimated_input_tokens": report["totals"]["total_input_tokens_estimate"],
                      "usage_available_records": report["totals"]["usage_available_records"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
