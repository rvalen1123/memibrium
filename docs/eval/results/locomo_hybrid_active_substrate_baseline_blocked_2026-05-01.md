# LOCOMO hybrid-active substrate baseline blocked — 2026-05-01

Repo: `/home/zaddy/src/Memibrium`
Branch: `query-expansion`
Commit checked: `b27565f`
Depends on:
- `docs/eval/locomo_hybrid_rebuild_restart_probe_preregistration_2026-05-01.md`
- `docs/eval/locomo_hybrid_active_substrate_baseline_preregistration_2026-05-01.md`
- `docs/eval/results/locomo_hybrid_rebuild_restart_probe_result_2026-05-01.md`

## Verdict

Baseline launch: `blocked`
Benchmark launched: `false`
Reason: post-mutation server is hybrid-active, but the separately preregistered comparable substrate baseline gate is not satisfied.

## Gate checks

Hybrid-active gate:

- `/health` OK.
- `USE_RUVECTOR=true` in live server.
- Live `/app/hybrid_retrieval.py` does not contain hard-coded `$1::vector`.
- Live `/app/hybrid_retrieval.py` contains dynamic `$1::{self.vtype}` casting.
- Fresh logs do not show `Hybrid retrieval failed` or `type "vector" does not exist` in the checked tail.
- LOCOMO contamination count is `0`.

Comparable substrate gate:

- Required by preregistration: recovered-floor substrate using `text-embedding-3-small` embeddings and `gpt-4.1-mini` answer/judge/query-expansion stack.
- Observed live server after rebuild: `AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-large-1` and `AZURE_CHAT_DEPLOYMENT=grok-4-20-non-reasoning-1`.
- `/mcp/test_embeddings` reports Azure deployment `text-embedding-3-large-1` with `3072` dimensions, not `text-embedding-3-small` with `1536` dimensions.
- Fresh logs show calls to `/openai/deployments/text-embedding-3-large-1/embeddings`.

This state proves the stale `::vector` blocker is fixed, but it is not launch-ready for the comparable no-intervention substrate baseline defined on 2026-05-01.

## Evidence captured immediately before stop

### Git state

```text
query-expansion
b27565f
```

### Health

```text
{"status":"ok","engine":"memibrium"}
```

### Relevant server env

```text
AZURE_CHAT_DEPLOYMENT=grok-4-20-non-reasoning-1
AZURE_CHAT_ENDPOINT=https://sector-7.services.ai.azure.com
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-large-1
AZURE_EMBEDDING_ENDPOINT=https://sector-7.services.ai.azure.com
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini
AZURE_OPENAI_ENDPOINT=https://sector-7.openai.azure.com/
CHAT_MODEL=gemma4:e4b
EMBEDDING_BASE_URL=http://ollama:11434/v1
EMBEDDING_MODEL=nomic-embed-text
RUVECTOR_GNN=true
USE_RUVECTOR=true
```

### LOCOMO contamination count

```text
0
```

### Live source probe

```text
contains_literal_vector_cast False
contains_dynamic_vtype_cast True
```

### `/mcp/test_embeddings`

```json
{"ollama":{"success":true,"latency_ms":0.05,"dimensions":1536,"endpoint":"http://ollama:11434/v1","model":"nomic-embed-text","sample_prefix":[-0.01177978515625,0.003444671630859375,-0.0010690689086914062]},"azure":{"success":true,"latency_ms":753.55,"dimensions":3072,"endpoint":"https://sector-7.services.ai.azure.com","deployment":"text-embedding-3-large-1","sample_embedding_prefix":[-0.00977325439453125,0.0028553009033203125,-0.0008869171142578125]},"recommendation":"keep_ollama"}
```

### Fresh relevant log tail

```text
2026-05-01 14:25:51,729 [INFO] ChatClient: Azure Foundry (https://sector-7.services.ai.azure.com, model=grok-4-20-non-reasoning-1)
2026-05-01 14:25:51,779 [INFO] Vector extension: ruvector
2026-05-01 14:25:55,107 [INFO] HTTP Request: POST https://sector-7.services.ai.azure.com/openai/deployments/text-embedding-3-large-1/embeddings?api-version=2024-06-01 "HTTP/1.1 200 OK"
INFO:     172.21.0.1:37558 - "POST /mcp/recall HTTP/1.1" 200 OK
2026-05-01 14:28:29,692 [INFO] HTTP Request: POST https://sector-7.services.ai.azure.com/openai/deployments/text-embedding-3-large-1/embeddings?api-version=2024-06-01 "HTTP/1.1 200 OK"
2026-05-01 14:28:30,549 [INFO] HTTP Request: POST https://sector-7.services.ai.azure.com/openai/deployments/text-embedding-3-large-1/embeddings?api-version=2024-06-01 "HTTP/1.1 200 OK"
INFO:     172.21.0.1:55200 - "POST /mcp/test_embeddings HTTP/1.1" 200 OK
2026-05-01 14:28:31,079 [INFO] HTTP Request: POST https://sector-7.services.ai.azure.com/openai/deployments/text-embedding-3-large-1/embeddings?api-version=2024-06-01 "HTTP/1.1 200 OK"
INFO:     172.21.0.1:60152 - "POST /mcp/recall HTTP/1.1" 200 OK
2026-05-01 14:35:18,115 [INFO] HTTP Request: POST https://sector-7.services.ai.azure.com/openai/deployments/text-embedding-3-large-1/embeddings?api-version=2024-06-01 "HTTP/1.1 200 OK"
INFO:     172.21.0.1:47880 - "POST /mcp/test_embeddings HTTP/1.1" 200 OK
```

## Decision

Stopped before LOCOMO launch. This follows the pre-registered stop rule: if recovered-floor substrate identity is not verified, stop and document. No LOCOMO benchmark, DB cleanup, or Phase C intervention was launched from this state.

## Next unblock options

1. Pre-register and execute a separate env-alignment mutation that restores the recovered-floor server substrate (`text-embedding-3-small`, `gpt-4.1-mini`) while preserving the now-fixed hybrid source, then rerun the substrate-baseline pre-launch gate.
2. Or pre-register a different observational baseline explicitly using the current `text-embedding-3-large-1` / `grok-4-20-non-reasoning-1` substrate, with a clear statement that it is not comparable to the recovered 66.08% floor.

Phase C remains blocked until a valid substrate baseline is completed and committed.
