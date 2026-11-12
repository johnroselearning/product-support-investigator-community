# Technical Support Engineer — Phase 1 dataset foundation

This directory provides **reproducible preparation code**, not a redistributed training corpus. Raw data, normalized records and splits are intentionally ignored by Git.

## Sources and permissions

See `sources.json` for the machine-readable source registry. Initial sources:

- `tasksource/it-support-tickets` — 2,229 real, anonymized tickets, seven categories, CC BY 4.0; **preserve the publisher's test split**.
- `tasksource/help-desk-tickets` — real helpdesk reporter messages (357 text-bearing issues in the default configuration), CC BY 4.0; **do not confuse issue_type with the seven ticket categories**.
- `bitext/Bitext-customer-support-llm-chatbot-training-dataset` — 26,872 synthetic conversational examples, CDLA-Sharing 1.0; **opt-in only**, pending legal review of share-alike obligations and intended distribution.

No commercial-use authorization is implied by this registry. Verify upstream terms and revision before commercial training or redistribution. Record attribution and license obligations.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r datasets/requirements.txt
python -m unittest discover -s datasets/tests -v
python datasets/prepare.py --output datasets/generated
# Only after reviewing Bitext's license:
python datasets/prepare.py --output datasets/generated --include-bitext
```

The script downloads data at runtime from Hugging Face. It emits `master/*.jsonl`, `sft/*.jsonl`, `quarantine.jsonl`, and `manifest.json` under the output directory. Do not commit these files until privacy, licensing and redistribution reviews are complete.

## Canonical master record

`case_id`, `source_id`, `source_revision`, `source_split`, `source_row`, `license`, `task_type`, `language`, `ticket`, `labels`, `evidence`, `hypotheses`, `actions`, `root_cause`, `resolution`, `quality`.

For public ticket data, evidence, actions, root cause and resolution remain empty or `unknown` unless explicitly supported. **Never infer a verified resolution from a category label.**

SFT records contain `messages` with system, user and assistant roles and preserve `case_id` and `source_id` for auditing. Classification labels are kept as source labels, not silently converted to severity or priority.

## Quality and evaluation boundaries

- Publisher-provided test partitions are reserved for testing. All other records receive deterministic train/validation/test assignment by normalized-content fingerprint.
- Exact duplicates are removed across splits. This does **not** guarantee semantic or incident-level isolation; audit near-duplicates before reporting model performance.
- Simple PII detection quarantines suspicious records. It is **not** a guarantee of anonymization. A human privacy review is required before training.
- A validation report counts accepted, duplicates, quarantined and per-source/per-split records.
- Conversational customer-service answers are **not** ground truth for technical root-cause investigation. Phase 2 must supply verified investigation trajectories.

## Source citations

- https://huggingface.co/datasets/tasksource/it-support-tickets
- https://huggingface.co/datasets/tasksource/help-desk-tickets
- https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset
