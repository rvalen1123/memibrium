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

Before any launch, record:

- downloaded file paths;
- byte sizes;
- SHA256 hashes;
- HuggingFace revision or resolved commit, if available.

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

Predeclare a deterministic slice before scoring:

- Seed: `memibrium-longmemeval-oracle-canary-2026-05-08-v1`.
- Source: `longmemeval_oracle.json` from the cleaned HuggingFace dataset.
- Unit: LongMemEval question row keyed by `question_id`.
- Stratification: across available LongMemEval question/category labels, with explicit inclusion of `knowledge-update` and abstention (`question_id` ending in `_abs`) if present.
- Ranking rule: within each stratum, rank rows by `sha256(seed + ':' + question_id + ':' + question)` and take the predeclared quota.
- If a category has fewer rows than quota, document the shortfall and redistribute by the same hash ranking rule before scoring.

The exact selected `question_id` list must be committed before any answer generation or judging.

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
