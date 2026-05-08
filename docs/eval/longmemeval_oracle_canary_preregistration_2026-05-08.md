# LongMemEval oracle canary preregistration — 2026-05-08

Scope: preregistration scaffold for moving Memibrium product telemetry toward LongMemEval. This document does not authorize a benchmark launch, full LongMemEval run, DB/Docker/runtime mutation, model deployment, or changes to LOCOMO comparability claims.

## Rationale

LongMemEval is the preferred next primary product benchmark because its categories map directly to Memibrium's memory-product claims:

- `single-session-user`, `single-session-assistant`, `single-session-preference`: session memory behavior.
- `multi-session`: long-range cross-session memory.
- `temporal-reasoning`: time-sensitive recall.
- `knowledge-update`: stale-vs-current fact handling, closest to CT lifecycle / delta-decay claims.
- Abstention rows (`question_id` ending in `_abs`): knowing when not to answer.

LOCOMO remains useful as continuity evidence for prior Memibrium work, but current LOCOMO answer-side canaries are internal diagnostics, not quote-worthy benchmark claims.

## Historical LOCOMO judge caveat

Prior Memibrium LOCOMO diagnostics in this branch used the Sector 7 Azure/Foundry chat stack with `gpt-4.1-mini` as answer/judge/query-expansion model unless a specific artifact says otherwise.

Implication:

- Those LOCOMO results are internally comparable within the Memibrium diagnostic history.
- They are not directly comparable to published/default GPT-4o-class LongMemEval numbers.
- They should not be read as a continuous score series with the LongMemEval results below once LongMemEval switches to GPT-4o judging.

## Dataset selection

Use the cleaned HuggingFace dataset, not the original 2024 LongMemEval files or older Drive mirrors:

```bash
mkdir -p data/
cd data/
wget https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_oracle.json
wget https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_s_cleaned.json
wget https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_m_cleaned.json
```

Pinned cleaned dataset revision and file identities for this preregistration:

- HuggingFace dataset: `xiaowu0162/longmemeval-cleaned`.
- HuggingFace revision: `98d7416c24c778c2fee6e6f3006e7a073259d48f`.
- `longmemeval_oracle.json`: 15,388,478 bytes, SHA256 `821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c`.
- `longmemeval_s_cleaned.json`: 277,383,467 bytes, SHA256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`.
- `longmemeval_m_cleaned.json`: 2,737,100,077 bytes, HuggingFace LFS SHA256 `9d79e5524794a2e6900a3aa9cb7d9152c5a3e8319c9a87c25494ba1eacee495f`.

The local first download of `_m` timed out at 1,445,072,896 bytes and is not a valid local file hash. The `_m` identity above is from the HuggingFace tree/LFS metadata at the pinned revision. This preregistration still does not authorize `_m` execution.

## Upstream LongMemEval repo

Upstream source is pinned before runner infrastructure:

- Upstream URL: `https://github.com/xiaowu0162/LongMemEval`.
- Default branch: `main`.
- Upstream HEAD inspected for this preregistration: `982fbd7045c9977e9119b5424cab0d7790d19413`.
- Judge script path: `src/evaluation/evaluate_qa.py`.
- Judge script SHA256: `ecce9c4c79dc89d99534ac17b383a5cbb5b9f0c69ee98adaf0684742e3d95251`.
- `requirements-lite.txt` SHA256: `d9d66e3c70fa859855f0fb47f3b3ee39b881d599e27f9b10ba725c7796a9d14b`.

Before any scored run, still record the local fork URL/commit if Memibrium carries a patched evaluator. If the evaluator is adapted for Azure AI Foundry, keep the upstream prompt text unchanged and document the adapter diff separately.

Install the lite environment only unless explicitly reproducing upstream retrieval/generation baselines:

```bash
conda create -n longmemeval-lite python=3.9
conda activate longmemeval-lite
pip install -r requirements-lite.txt
```

## Judge stack pin

LongMemEval judge for the first Memibrium product canary is pinned as:

- Provider/project: Azure AI Foundry, Sector 7 project `proj-default`.
- Project URL: `https://sector-7.services.ai.azure.com/api/projects/proj-default`.
- Inference base URL: `https://sector-7.services.ai.azure.com/models`.
- Judge model name/deployment: `gpt-4o`.
- Judge model version: `2024-11-20`.
- Temperature: `0`.
- Judge prompt: verbatim from upstream `src/evaluation/evaluate_qa.py` at `982fbd7045c9977e9119b5424cab0d7790d19413`; preserve task-specific prompts from `get_anscheck_prompt()`.

Upstream's current `model_zoo` maps `gpt-4o` to `gpt-4o-2024-08-06`. Memibrium's first comparable LongMemEval judge intentionally uses Azure AI Foundry `gpt-4o` version `2024-11-20` instead. Treat this as an explicit Memibrium judge-stack pin, not an upstream-default reproduction.

Recommended scoring env shape for the LongMemEval judge process:

```bash
export AZURE_CHAT_ENDPOINT="https://sector-7.services.ai.azure.com/models"
export JUDGE_MODEL="gpt-4o"
# Use the current Sector 7 project key from Azure AI Foundry; do not paste keys into artifacts.
export AZURE_CHAT_API_KEY="<redacted>"
```

Do not overwrite historical LOCOMO docs to imply those runs used GPT-4o. If a transition run intentionally rejudges LOCOMO or LongMemEval with a different judge, preregister it as a separate judge-variance experiment.

## First canary scope

Start with `longmemeval_oracle.json`, not `_s` or `_m`.

Reason: oracle mode includes the evidence sessions, so retrieval is solved. This isolates answer-side behavior, analogous to the LOCOMO frozen-final-context canaries where gold-hit stayed flat and the signal was generation-side.

The first LongMemEval canary is limited to a hash-stratified 25-row oracle slice. It is not a full LongMemEval score and is not externally quote-worthy.

## Slice construction

Predeclared deterministic slice:

- Seed: `memibrium-longmemeval-oracle-canary-2026-05-08-v1`.
- Source: `longmemeval_oracle.json` from `xiaowu0162/longmemeval-cleaned` revision `98d7416c24c778c2fee6e6f3006e7a073259d48f`.
- Unit: LongMemEval question row keyed by `question_id`.
- Selection artifact: `docs/eval/results/longmemeval_oracle_canary_25_selection_20260508.json`.
- Hash rule: `sha256(seed + ':' + question_id + ':' + question)`.
- Quotas: 4 rows per `question_type`; for question types with abstention rows, reserve one slot for the lowest-hash `_abs` row and fill the other 3 slots with the lowest-hash non-abstention rows; add 1 extra lowest-hash not-yet-selected `knowledge-update` row as product-telemetry oversample.
- Counts: 25 rows total; `knowledge-update` 5, `multi-session` 4, `single-session-assistant` 4, `single-session-preference` 4, `single-session-user` 4, `temporal-reasoning` 4; abstention rows 4.

Selected `question_id` list:

| # | question_id | question_type | abstention |
|---:|---|---|---|
| 1 | `0ddfec37_abs` | `knowledge-update` | yes |
| 2 | `a1eacc2a` | `knowledge-update` | no |
| 3 | `852ce960` | `knowledge-update` | no |
| 4 | `eace081b` | `knowledge-update` | no |
| 5 | `09ba9854_abs` | `multi-session` | yes |
| 6 | `b3c15d39` | `multi-session` | no |
| 7 | `3c1045c8` | `multi-session` | no |
| 8 | `gpt4_731e37d7` | `multi-session` | no |
| 9 | `dc439ea3` | `single-session-assistant` | no |
| 10 | `58470ed2` | `single-session-assistant` | no |
| 11 | `71a3fd6b` | `single-session-assistant` | no |
| 12 | `fca762bc` | `single-session-assistant` | no |
| 13 | `35a27287` | `single-session-preference` | no |
| 14 | `06878be2` | `single-session-preference` | no |
| 15 | `a89d7624` | `single-session-preference` | no |
| 16 | `d6233ab6` | `single-session-preference` | no |
| 17 | `29f2956b_abs` | `single-session-user` | yes |
| 18 | `3f1e9474` | `single-session-user` | no |
| 19 | `af8d2e46` | `single-session-user` | no |
| 20 | `6f9b354f` | `single-session-user` | no |
| 21 | `gpt4_fe651585_abs` | `temporal-reasoning` | yes |
| 22 | `0db4c65d` | `temporal-reasoning` | no |
| 23 | `b9cfe692` | `temporal-reasoning` | no |
| 24 | `gpt4_68e94288` | `temporal-reasoning` | no |
| 25 | `45dc21b6` | `knowledge-update` | no |

No answer generation or judging may occur until this selection artifact is committed.

## Candidate under test

Carry forward the locked answer-side candidate without post-LOCOMO retuning:

- answer-shape directive scoped to LongMemEval categories analogous to LOCOMO `multi-hop,temporal`, especially `multi-session` and `temporal-reasoning`;
- multimodal metadata projection only if the LongMemEval row contains comparable metadata fields; otherwise record it as a no-op rather than inventing metadata;
- no subject guard;
- preserve baseline/treatment evidence identity in oracle mode.

## Output format

LongMemEval evaluation expects JSONL predictions shaped as:

```json
{"question_id": "...", "hypothesis": "..."}
```

For Memibrium artifacts, also preserve per-row metadata outside the upstream scoring file:

- `question_id`;
- category/type;
- oracle evidence/session IDs or evidence hashes;
- baseline answer;
- treatment answer;
- judge score/details;
- answer model identity;
- judge model identity/version;
- prompt hashes;
- any abstention/knowledge-update flags.

## Initial interpretation rules

- Oracle canary movement is answer-side evidence only; it does not prove retrieval quality.
- Do not compare LongMemEval oracle scores directly to LOCOMO 199Q/cumulative scores.
- Expect lower absolute scores than LOCOMO because LongMemEval is harder.
- Do not externally communicate the first LongMemEval number until it is calibrated against published baselines and the judge stack is clearly disclosed.
- Treat `knowledge-update` and abstention behavior as first-class product telemetry, not secondary category detail.

## Promotion gates before `_s` or `_m`

Before moving from oracle to `longmemeval_s_cleaned.json` or `longmemeval_m_cleaned.json`, require a separate preregistration that includes:

- dataset hashes and upstream commit;
- exact judge model/version/prompt;
- answer model and retrieval/runtime substrate;
- DB/Docker/runtime mutation approval if Memibrium ingest is required;
- cleanup plan;
- thresholds for overall, `knowledge-update`, abstention, and temporal regressions;
- cost estimate and rate-limit plan.

## Standing guardrails

- No full LOCOMO 199Q/cumulative run without explicit approval.
- No full LongMemEval `_s` or `_m` run without explicit approval.
- No DB/Docker/runtime mutation without explicit approval.
- No direct `/mcp/tools` curl retry without permission.
- Do not touch or commit `docs/reference/` unless explicitly asked.
- Redact secrets/tokens/API keys/env credentials from logs and artifacts.
