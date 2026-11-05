# Offline payload profiling, Phases 1–4

The profiler measures locally observable input construction, repetition and stage
distribution. It does not optimize investigation behavior or add model calls.
Architecture and visibility limits are in [PAYLOAD_ARCHITECTURE.md](PAYLOAD_ARCHITECTURE.md).
Measured findings are in [results/PAYLOAD_REPORT.md](results/PAYLOAD_REPORT.md).

## Run without installing dependencies

From the repository root, using the existing Python runtime:

```bash
python3 scripts/profile_payloads.py tests/fixtures/payloads.jsonl \
  --output /tmp/psi-synthetic-profile.json

python3 -m investigation_harness --scenario jira \
  --profile-payloads /tmp/psi-harness-profile.json

python3 scripts/benchmark_optimization.py --label C --repeats 1 \
  --output /tmp/psi-benchmark-profile-run-C.json \
  --profile-output /tmp/psi-payload-C.json
```

The normal harness and benchmark do not instantiate a profiler or write profiles.
The standalone CLI is itself an explicit profiling request. Output is a local
file, atomically written with mode 0600. Do not use customer directories that
automatically synchronize to external services. The profiler never transmits data.
Use distinct input/output paths; benchmark/profile paths must also differ.

`--label A` reuses the existing baseline context reconstruction and source digest
checks; B reuses the existing pre-conditional-loading comparison; C uses current
construction. These remain offline scripted comparisons. Only the first timing
repeat is profiled, avoiding artificially repeated identical benchmark inputs.
Historical `docs/optimization/benchmark-{A,B,C}.json` files are not overwritten.

## Input formats

JSON accepts a request object, a list of capture envelopes, `{"captures":[...]}`,
or a raw message array. JSONL accepts one capture/request per nonblank line.
`--format json` or `--format jsonl` disables auto-detection.

An envelope distinguishes capture metadata from request content:

```json
{
  "stage": "choose",
  "kind": "synthetic_provider_request",
  "synthetic": true,
  "scenario": "synthetic_demo",
  "comparison_group": "same_host_model_and_task_family",
  "provider": "openai",
  "payload": {
    "sections": [
      {"component": "core_skill", "content": "Public instructions"},
      {"component": "jira_evidence", "content": "Synthetic issue excerpt"},
      {"component": "user_request", "content": "Investigate the demo"}
    ]
  }
}
```

`sections` may instead be an ordered object mapping component names to content.
`label` is an alias for `component` within sections. Section labels are capture
metadata; the contents are concatenated in their original order. Labelled section
captures are an approximation unless the host also supplies the complete request.
Do not include both the same content in sections and again in messages.

Raw structures support OpenAI messages, instructions/input, function_call_output,
Anthropic system/messages/tool_result blocks, tools/functions, tool responses,
assistant history and evidence arrays. Mixed text/image objects are retained in
the local serialized size. **Image/audio/video model token costs cannot be derived
from character counts.** System/developer text uses fallback classification when
no component label exists. Earlier user turns and assistant content are history;
the final user turn is user_request. Embedded explicit component/content blocks
take precedence. Structured source/provider fields identify supported evidence;
keywords alone do not establish evidence provenance.

Supported components: `core_skill`, `reference_guidance`, `provider_guidance`,
`tool_schemas`, `capability_catalog`, `jira_evidence`, `grafana_evidence`,
`github_evidence`, `evidence_ledger`, `conversation_history`, `routing_context`,
`critic_context`, `user_request`, `other`.

Harness field/file/role attribution has confidence 1.0 for the serialization
mapping, not semantic truth. Regex fallback has confidence 0.55; unknown content
and unrecognized explicit labels have confidence 0.0. Reports include each
payload's character-weighted confidence, classification-method sizes, and unknown
percentage. JSON punctuation/keys and recognized protocol metadata are known
`other`; `other` is therefore not synonymous with unclassified. Percentages use
characters, avoiding independently rounded section-token percentages.

## Counting and observed usage

Three measurements remain distinct:

1. `input_tokens_estimate`: ceil(Unicode characters / 4) over the entire local
   serialization, or concatenated labelled contents. Raw objects use compact JSON
   with original insertion order and Unicode preserved. This differs from the
   historical benchmark's default JSON spacing. Components aggregate character
   sizes and round per payload/component; their token sums can exceed the single
   whole-input estimate slightly. They partition characters exactly.
2. Optional `--model MODEL`: uses an **already installed** `tiktoken` and existing
   cached encoding assets. No package or model assets are installed/downloaded.
   An absent dependency, unknown model, or cache miss reports `unavailable` and
   preserves character estimates. `serialized_request_token_estimate` counts the
   local serialization; `section_content_token_estimates` counts each content
   piece separately. Neither is an exact provider chat-framing or multimodal count.
3. `usage`: allowlisted numeric usage fields from an optional envelope `response`,
   or explicitly labelled `adapter_reported` Decision counts. Response bodies and
   usage objects are excluded from input size. Usage is never inferred from
   reservations, output caps, estimates, or invocation counts. Synthetic captures
   cannot contribute observed usage, even if they contain a usage-shaped object.

To profile an actual authorized host request, supply `kind: "provider_request"`,
`synthetic: false`, and `submitted: true` only after the host really submitted it.
The standalone tool trusts that declaration; it cannot verify network activity.
Supply `response: {"usage": {...}}` from that same provider response. A harness
callback observation remains intermediate and contributes zero confirmed provider
calls even if adapter-reported counts are present.

OpenAI Responses input/output tokens and cached input details, OpenAI Chat
prompt/completion tokens and cached prompt details, and Anthropic input/output,
cache-read and cache-creation fields are supported. Anthropic's input field counts
uncached input; cache reads/writes remain separate. OpenAI cached tokens are a
subset of its input field. Aggregation groups by provider, metadata source and
semantics, without adding cache fields to input or applying discounts. Missing
values remain null, including unknown cache-hit indicators. Streaming fragments
must be consolidated by the host before profiling; the tool does not infer or
deduplicate incremental usage. Tests use synthetic metadata to verify parsing;
published benchmark results contain no actual provider usage.

## Duplication and prefix analysis

Exact matching normalizes whitespace per line without changing case or meaning.
It detects identical section blocks of at least 32 normalized characters and
repeated lines of at least 16 characters. JSON string leaves are decoded for line
matching. Within-request duplicate percentage is the larger of duplicate-block
and duplicate-line character ratios; the two overlap and are **not added**.
This is a bounded indicator, not an exact removable-token count. Across-request
repetition counts each repeated block occurrence after the first. Largest sources
are identified by component, keyed content hash, size and occurrence count.
Corpus-wide normalized-line matches are reported separately from identical blocks;
their character totals overlap and must not be added.
Repeated instructions specifically mean core, reference and provider guidance;
dynamic routing/state is not counted as instruction text. Repeated evidence
includes evidence content and ledger metadata. These corpus repetition measures
include repeated synthetic instructions across independent cases, not only a
single investigation; they are not savings estimates.

Near matching uses deterministic local weighted Jaccard similarity over 5-token
shingles: same component, length ratio >=0.8, similarity >=0.85. There are no
embeddings or LLM calls. At most 512 unique candidates and 10,000 comparisons
are considered; long sections exceeding 16,000 characters are excluded. Reports
expose limits/comparisons; only the first 50 matches and 20 exact repeated sources
are retained. Candidate count, candidate-cap coverage and oversized-section
exclusions are also reported. Short text, semantic paraphrases, cross-component duplication and
content outside these bounds may be missed.

Stable prefixes are literal common character prefixes of local inputs grouped by
comparison group, stage, boundary kind, provider and model identity. No sorting,
reordering, ID removal, or whitespace normalization manufactures a prefix.
Groups need at least two inputs; singletons report null. Reports include prefix
characters/token estimate, dynamic size and weighted shared-prefix percentage.
**This is not provider cache eligibility or a cache hit.** Provider cache-read,
cache-write and cache-hit metadata remains a separate measurement. No universal
cache discount or production saving is assumed.

## Stages and capture integration

Stage keys use repository names: understand, choose, propose, critic, report,
revise. Reports also include zero-valued skill_selection, evidence_acquisition and
investigation entries because these conceptual phases have no separate model
payload in the harness. `propose` plans evidence acquisition; choose/propose
perform the investigation loop. Skill selection, tool execution and finalization
are deterministic. Every stage includes whole-input total/mean/max estimates,
component distribution, duplicates, prefix coverage and observed model-call count.
Scripted adapter invocations and deterministic critics have separate counts.

For a trusted Python embedding, pass `PayloadProfiler(enabled=True)` as
`Harness(..., profiler=observer)`, then explicitly call `observer.write(local_path)`.
The hook supplies safe internal IDs, takes a separate payload copy, and catches
observer errors without retaining exception text. It cannot mutate the adapter
input or affect policy decisions. Profiling costs CPU/memory and can affect
wall-clock timing; do not interpret profiled latency as production latency or
performance-neutral execution under tight wall-clock budgets.

## Data handling and limits

Artifacts deliberately omit **all** content, including redacted text. Redacting
only known secret patterns cannot reliably sanitize customer logs, private source
or Jira free text, so there is no raw-content capture mode. Size analysis happens
in bounded process memory; unmodified contents are not written, printed, logged,
or transmitted. Exact/near-match fingerprints and arbitrary identifiers use
ephemeral per-profiler keyed HMAC-SHA256; the key is not persisted, preventing
cross-run hash linkage and dictionary recovery from a published digest. Safe
UUID/hex internal trace/investigation IDs may be preserved; other IDs are hashed.
Only trusted synthetic scenario slugs are preserved. Classification labels,
stage/boundary/provider names and usage metadata are allowlisted. Parser failures
emit fixed diagnostics without source text or exception bodies.
The benchmark also retains its existing public source inventory paths and SHA256
digests; that fixed repository inventory contains no customer content.

Use synthetic fixtures whenever possible. For production-like diagnostics, run
the profiler in the trusted host process, persist only its metadata report, and
do not first write an unsanitized provider request to disk. The standalone tool
does not clean up or protect raw input files created by another system. Existing
harness redaction and evidence-provenance controls remain intact.

Defaults: 512 Ki Unicode characters per input, 16 Mi characters retained overall,
2,000 inputs, 2,048 decomposition pieces per input, and a 32 MiB input-file read
limit. Oversized records are skipped in full and counted in `skipped`; there are
no misleading partial-input estimates. CLI flags expose these bounds, plus near
comparison/text bounds (`--help`). JSON syntax is parsed within the file bound;
deeply nested invalid input fails with a fixed diagnostic. Exhausted limits mean
the profile is incomplete. Disabled profiling writes nothing.

## Verification and next phase

Run the profiler tests, full PSI regression suite, validator, evaluator and Forge
Node tests using the existing runtimes. See the result report for commands and
observed outcomes. No dependencies, production configuration, prompts, routing,
tool behavior, provenance rules, or security instructions are changed here.

Review the measurements before considering schema presentation, stable-prefix
placement or other reductions. Evidence compaction, model tiering and further
prompt reduction are outside this implementation. Offline scripted pass counts
do not measure semantic investigation accuracy, live coverage, actual latency,
billing, or savings.
