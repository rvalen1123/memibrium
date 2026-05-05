# LOCOMO hybrid-active canonical substrate baseline comparison — 2026-05-01

Repo: `/home/zaddy/src/Memibrium`
Branch: `query-expansion`
Run HEAD: `8d471fa`
Run class: no-intervention observational substrate baseline; not Phase C.

## Verdict

Canonical hybrid-active baseline completed and artifacts preserved.

Phase C gate status after this run: baseline artifacts are preserved and cleanup verifies `0`; once this file and artifacts are committed, Phase C is unblocked for evidence-based intervention selection.

## Score summary

- Overall 5-category score: `14.82%`
- Protocol 4-category score: `19.41%`
- Total questions: `199`
- Avg query latency: `2478 ms`
- Query expansion fallback: `0/199 (0.0)`

## Category scores

| Category | Score | Count |
|---|---:|---:|
| cat-adversarial | 0.0 | 47 |
| cat-multi-hop | 30.77 | 13 |
| cat-single-hop | 26.56 | 32 |
| cat-temporal | 39.19 | 37 |
| cat-unanswerable | 3.57 | 70 |

## Retrieval/context diagnostics

- Mean `n_memories`: `4.5327`
- `n_memories == 15` saturation: `22/199 (11.06%)`
- Distribution: `2:57, 3:110, 11:1, 12:3, 13:3, 14:3, 15:22`

Recovered stale-live-path floor for comparison:

- 5-category score: `66.08%`
- Query expansion fallback: `0/199`
- Mean `n_memories`: `13.1608`
- `n=15` saturation: `31.16%`

Interpretation: this run is the first comparable canonical-substrate hybrid-active measurement, not a Phase C intervention. It should be compared as legacy-recall fallback floor -> actual hybrid retrieval on the same canonical answer/judge/embedding substrate.

## Locked condition evidence

Condition from result JSON:

```json
{
  "cleaned": false,
  "normalize_dates": false,
  "query_expansion": true,
  "context_rerank": false,
  "append_context_expansion": false,
  "gated_append_context_expansion": false,
  "no_expansion_arm_b": false,
  "legacy_context_assembly": false
}
```

Prelaunch checks all passed: `True`.

Server/benchmark substrate excerpts from prelaunch artifact:

```text
AZURE_CHAT_DEPLOYMENT=gpt-4.1-mini
AZURE_CHAT_ENDPOINT=https://sector-7.services.ai.azure.com
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-small
AZURE_EMBEDDING_ENDPOINT=https://sector-7.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini
AZURE_OPENAI_ENDPOINT=https://sector-7.openai.azure.com/
USE_RUVECTOR=true
```

Benchmark env:

```json
{
  "AZURE_CHAT_ENDPOINT": "https://sector-7.services.ai.azure.com/models",
  "AZURE_CHAT_DEPLOYMENT": "gpt-4.1-mini",
  "AZURE_OPENAI_DEPLOYMENT": "gpt-4.1-mini",
  "ANSWER_MODEL": "gpt-4.1-mini",
  "JUDGE_MODEL": "gpt-4.1-mini",
  "CHAT_MODEL": "gpt-4.1-mini",
  "AZURE_EMBEDDING_ENDPOINT": "https://sector-7.openai.azure.com/",
  "AZURE_EMBEDDING_DEPLOYMENT": "text-embedding-3-small",
  "USE_QUERY_EXPANSION": "1",
  "USE_CONTEXT_RERANK": "",
  "USE_APPEND_CONTEXT_EXPANSION": "",
  "USE_GATED_APPEND_CONTEXT_EXPANSION": "",
  "USE_LEGACY_CONTEXT_ASSEMBLY": ""
}
```

Embedding probe:

```json
{"ollama":{"success":true,"latency_ms":0.03,"dimensions":1536,"endpoint":"http://ollama:11434/v1","model":"nomic-embed-text","sample_prefix":[0.01641845703125,-0.0225677490234375,0.0226287841796875]},"azure":{"success":true,"latency_ms":618.98,"dimensions":1536,"endpoint":"https://sector-7.openai.azure.com/","deployment":"text-embedding-3-small","sample_embedding_prefix":[0.01641845703125,-0.0225677490234375,0.0226287841796875]},"recommendation":"keep_ollama"}
```

Hybrid source check:

```text
contains_literal_vector_cast False
contains_dynamic_vtype_cast True
```

Source hashes:

```text
5efefae8f05b45974dab6a379403e1a94d00a60e2bfb76b403d4ebe4a7e360d5  server.py
a35fe1624ff17bc19190a8ee5959a767b690cb44303907fbfb7f5373fb771fce  hybrid_retrieval.py
5efefae8f05b45974dab6a379403e1a94d00a60e2bfb76b403d4ebe4a7e360d5  /app/server.py
a35fe1624ff17bc19190a8ee5959a767b690cb44303907fbfb7f5373fb771fce  /app/hybrid_retrieval.py
```

## Post-run evidence before cleanup

- Health: `{"status":"ok","engine":"memibrium"}`
- LOCOMO rows before cleanup: `49`
- Fresh logs contain `text-embedding-3-small`: `True`
- Fresh logs contain `gpt-4.1-mini`: `False` in the post-run 20-minute server tail; canonical chat identity is instead captured in prelaunch server env and benchmark env above, and the benchmark log/preflight succeeded using `gpt-4.1-mini`.
- Fresh logs absent hybrid fallback strings: `True`

## Artifacts

- Result JSON: `docs/eval/results/locomo_conv26_hybrid_active_substrate_baseline_2026-05-01.json`
  - sha256: `d44b9288a633bfdb04061f44bb5d37b8240342e5550e2df5f1c2bc2f38187637`
- Run log: `docs/eval/results/locomo_conv26_hybrid_active_substrate_baseline_2026-05-01.log`
  - sha256: `c8d6535f4b83d368e2a08b9df56bd397f1ba664a966d7fb4bbe8ce672b1c393e`
- Prelaunch evidence: `docs/eval/results/locomo_hybrid_active_substrate_baseline_prelaunch_2026-05-01.json`
  - sha256: `bcffc4eb53e5321168e848db6276f0471ef03d2e605acfe99937c2ab152ce931`

## Cleanup status

Cleanup completed after artifact preservation.

Cleanup command deleted:

- contradictions linked to LOCOMO memories: `1`
- temporal expressions linked to LOCOMO memories: `66`
- memory snapshots linked to LOCOMO memories: `0`
- memory edges linked to LOCOMO memories: `417`
- LOCOMO memories: `49`

Post-cleanup verification:

```text
locomo_remaining = 0
```

Phase C intervention selection may proceed only from this committed baseline and the audit evidence, not from the stale legacy-recall floor alone.
