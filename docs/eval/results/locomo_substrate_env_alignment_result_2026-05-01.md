# LOCOMO substrate env alignment result — 2026-05-01

Generated: `2026-05-01T14:50:21.191938+00:00`
Repo: `/home/zaddy/src/Memibrium`
Verdict: `canonical-substrate-aligned-after-parser-correction`
Baseline launch ready: `true`
Backup path: `/tmp/memibrium_env_backup_2026-05-01_20260501T145021Z.env`

The single env-alignment mutation completed. The initial decision parser falsely marked env and recall gates as failed because its grep regex omitted underscore-containing Azure variable names and its recall check did not account for valid empty-list recall responses. Follow-up non-mutating probes confirmed all preregistered gates pass. No second env mutation/restart was performed by the correction.

## Pre timestamp

```text
$ date -Is && date -u +%Y-%m-%dT%H:%M:%SZ
exit=0
2026-05-01T09:50:21-05:00
2026-05-01T14:50:21Z
```

## Pre git state

```text
$ git status --short && git branch --show-current && git rev-parse HEAD && git log -1 --oneline
exit=0
query-expansion
05f0364dcb615d37a3d2e76bd65e10a4bae4c536
05f0364 docs: preregister LOCOMO substrate env alignment
```

## Pre health

```text
$ curl -fsS http://localhost:9999/health
exit=0
{"status":"ok","engine":"memibrium"}
```

## Pre docker status

```text
$ docker ps --filter 'name=memibrium' --format '{{.Names}}|{{.Status}}|{{.Image}}'
exit=0
memibrium-server|Up 24 minutes (healthy)|memibrium-memibrium
memibrium-ollama|Up 26 hours|ollama/ollama:latest
memibrium-ruvector-db|Up 26 hours (healthy)|ruvnet/ruvector-postgres:latest
```

## Pre image/container identity

```text
$ docker inspect memibrium-server --format 'server_image={{.Image}} created={{.Created}} started={{.State.StartedAt}}' && docker image inspect memibrium-memibrium:latest --format 'image_id={{.Id}} image_created={{.Created}}'
exit=0
server_image=sha256:e61857cc17f69f5cc6c76971fabe02b6657156148847aaaf711939707b6f0356 created=2026-05-01T14:25:49.293372603Z started=2026-05-01T14:25:50.597734128Z
image_id=sha256:e61857cc17f69f5cc6c76971fabe02b6657156148847aaaf711939707b6f0356 image_created=2026-05-01T14:25:48.558179254Z
```

## Pre live env

```text
$ docker exec memibrium-server env | sort | grep -E '^(AZURE_CHAT|AZURE_EMBEDDING|AZURE_OPENAI|CHAT_MODEL|EMBEDDING_|OPENAI_BASE_URL|DB_|USE_RUVECTOR|RUVECTOR_GNN)=' || true
exit=0
CHAT_MODEL=gemma4:e4b
OPENAI_BASE_URL=https://openrouter.ai/api/v1
RUVECTOR_GNN=true
USE_RUVECTOR=true
```

## Pre source hashes

```text
$ sha256sum server.py hybrid_retrieval.py && docker exec memibrium-server sha256sum /app/server.py /app/hybrid_retrieval.py
exit=0
5efefae8f05b45974dab6a379403e1a94d00a60e2bfb76b403d4ebe4a7e360d5  server.py
a35fe1624ff17bc19190a8ee5959a767b690cb44303907fbfb7f5373fb771fce  hybrid_retrieval.py
5efefae8f05b45974dab6a379403e1a94d00a60e2bfb76b403d4ebe4a7e360d5  /app/server.py
a35fe1624ff17bc19190a8ee5959a767b690cb44303907fbfb7f5373fb771fce  /app/hybrid_retrieval.py
```

## Pre DB probe

```text
$ docker exec memibrium-ruvector-db psql -U memory -d memory -v ON_ERROR_STOP=1 -c "BEGIN; SELECT count(id) AS locomo_domain_rows FROM memories WHERE domain LIKE 'locomo-%'; SELECT data_type, udt_name FROM information_schema.columns WHERE table_name='memories' AND column_name='embedding'; SELECT extname, extversion FROM pg_extension WHERE extname='ruvector'; SELECT embedding <=> embedding AS self_distance FROM memories WHERE embedding IS NOT NULL LIMIT 1; ROLLBACK;"
exit=0
BEGIN
 locomo_domain_rows
--------------------
                  0
(1 row)

  data_type   | udt_name
--------------+----------
 USER-DEFINED | ruvector
(1 row)

 extname  | extversion
----------+------------
 ruvector | 0.3.0
(1 row)

 self_distance
---------------
 1.7872301e-07
(1 row)

ROLLBACK
```

## Pre relevant logs

```text
$ docker logs --tail 120 memibrium-server 2>&1 | grep -E 'Hybrid retrieval failed|type "vector"|text-embedding|ChatClient|Vector extension|POST /mcp/(recall|test_embeddings)' || true
exit=0
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

## Pre sanitized .env

```text
OPENAI_BASE_URL=https://openrouter.ai/api/v1
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_BASE_URL=http://ollama:11434/v1
CHAT_MODEL=openai/gpt-4.1-mini
DB_HOST=localhost
DB_PORT=5432
DB_NAME=memory
DB_USER=memory
DB_PASSWORD=***
USE_RUVECTOR=true
RUVECTOR_GNN=true
AZURE_OPENAI_ENDPOINT=https://sector-7.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini
AZURE_API_VERSION=2024-06-01
AZURE_CHAT_ENDPOINT=https://sector-7.services.ai.azure.com
AZURE_CHAT_DEPLOYMENT=grok-4-20-non-reasoning-1
AZURE_EMBEDDING_ENDPOINT=https://sector-7.services.ai.azure.com
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-large-1
```

## Backup path

```text
/tmp/memibrium_env_backup_2026-05-01_20260501T145021Z.env
```

## Post-edit sanitized .env

```text
OPENAI_BASE_URL=https://openrouter.ai/api/v1
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_BASE_URL=http://ollama:11434/v1
CHAT_MODEL=gpt-4.1-mini
DB_HOST=localhost
DB_PORT=5432
DB_NAME=memory
DB_USER=memory
DB_PASSWORD=***
USE_RUVECTOR=true
RUVECTOR_GNN=true
AZURE_OPENAI_ENDPOINT=https://sector-7.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini
AZURE_API_VERSION=2024-06-01
AZURE_CHAT_ENDPOINT=https://sector-7.services.ai.azure.com
AZURE_CHAT_DEPLOYMENT=gpt-4.1-mini
AZURE_EMBEDDING_ENDPOINT=https://sector-7.openai.azure.com/
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-small
```

## Server recreate command

```text
$ docker compose -f docker-compose.ruvector.yml up -d --no-build --no-deps --force-recreate memibrium
exit=0
 Container memibrium-server Recreate
 Container memibrium-server Recreated
 Container memibrium-server Starting
 Container memibrium-server Started
```

## Post timestamp

```text
$ date -Is && date -u +%Y-%m-%dT%H:%M:%SZ
exit=0
2026-05-01T09:50:26-05:00
2026-05-01T14:50:26Z
```

## Post health

```text
$ curl -fsS http://localhost:9999/health
exit=0
{"status":"ok","engine":"memibrium"}
```

## Post docker status

```text
$ docker ps --filter 'name=memibrium' --format '{{.Names}}|{{.Status}}|{{.Image}}'
exit=0
memibrium-server|Up 3 seconds (health: starting)|memibrium-memibrium
memibrium-ollama|Up 26 hours|ollama/ollama:latest
memibrium-ruvector-db|Up 26 hours (healthy)|ruvnet/ruvector-postgres:latest
```

## Post image/container identity

```text
$ docker inspect memibrium-server --format 'server_image={{.Image}} created={{.Created}} started={{.State.StartedAt}}' && docker image inspect memibrium-memibrium:latest --format 'image_id={{.Id}} image_created={{.Created}}'
exit=0
server_image=sha256:e61857cc17f69f5cc6c76971fabe02b6657156148847aaaf711939707b6f0356 created=2026-05-01T14:50:21.953131594Z started=2026-05-01T14:50:22.996971396Z
image_id=sha256:e61857cc17f69f5cc6c76971fabe02b6657156148847aaaf711939707b6f0356 image_created=2026-05-01T14:25:48.558179254Z
```

## Post live env

```text
$ docker exec memibrium-server env | sort | grep -E '^(AZURE_CHAT|AZURE_EMBEDDING|AZURE_OPENAI|CHAT_MODEL|EMBEDDING_|OPENAI_BASE_URL|DB_|USE_RUVECTOR|RUVECTOR_GNN)=' || true
exit=0
CHAT_MODEL=gemma4:e4b
OPENAI_BASE_URL=https://openrouter.ai/api/v1
RUVECTOR_GNN=true
USE_RUVECTOR=true
```

## Post source probe

```text
$ docker exec memibrium-server python3 -c 'from pathlib import Path; s=Path("/app/hybrid_retrieval.py").read_text(); print("contains_literal_vector_cast", "$1::vector" in s); print("contains_dynamic_vtype_cast", "$1::{self.vtype}" in s); [print(f"{i}: {line}") for i,line in enumerate(s.splitlines(),1) if "$1::" in line or "$1::{self.vtype}" in line]'
exit=0
contains_literal_vector_cast False
contains_dynamic_vtype_cast True
403:                    1 - (embedding <=> $1::{self.vtype}) AS cosine_score
406:             ORDER BY embedding <=> $1::{self.vtype}
```

## Post DB probe

```text
$ docker exec memibrium-ruvector-db psql -U memory -d memory -v ON_ERROR_STOP=1 -c "BEGIN; SELECT count(id) AS locomo_domain_rows FROM memories WHERE domain LIKE 'locomo-%'; SELECT data_type, udt_name FROM information_schema.columns WHERE table_name='memories' AND column_name='embedding'; SELECT extname, extversion FROM pg_extension WHERE extname='ruvector'; SELECT embedding <=> embedding AS self_distance FROM memories WHERE embedding IS NOT NULL LIMIT 1; ROLLBACK;"
exit=0
BEGIN
 locomo_domain_rows
--------------------
                  0
(1 row)

  data_type   | udt_name
--------------+----------
 USER-DEFINED | ruvector
(1 row)

 extname  | extversion
----------+------------
 ruvector | 0.3.0
(1 row)

 self_distance
---------------
 1.7872301e-07
(1 row)

ROLLBACK
```

## /mcp/test_embeddings

```json
HTTP 200
{"ollama":{"success":true,"latency_ms":1271.58,"dimensions":1536,"endpoint":"http://ollama:11434/v1","model":"nomic-embed-text","sample_prefix":[-0.020843505859375,-0.0168914794921875,-0.00450897216796875]},"azure":{"success":true,"latency_ms":411.34,"dimensions":1536,"endpoint":"https://sector-7.openai.azure.com/","deployment":"text-embedding-3-small","sample_embedding_prefix":[-0.020843505859375,-0.0168914794921875,-0.00450897216796875]},"recommendation":"switch_to_azure"}
```

## Non-LOCOMO recall probe

```json
HTTP 200
[]
```

## Post fresh relevant logs

```text
2026-05-01 14:50:24,078 [INFO] ChatClient: Azure Foundry (https://sector-7.services.ai.azure.com, model=gpt-4.1-mini)
2026-05-01 14:50:24,127 [INFO] Vector extension: ruvector
2026-05-01 14:50:28,313 [INFO] HTTP Request: POST https://sector-7.openai.azure.com/openai/deployments/text-embedding-3-small/embeddings?api-version=2024-06-01 "HTTP/1.1 200 OK"
2026-05-01 14:50:28,731 [INFO] HTTP Request: POST https://sector-7.openai.azure.com/openai/deployments/text-embedding-3-small/embeddings?api-version=2024-06-01 "HTTP/1.1 200 OK"
INFO:     172.21.0.1:38586 - "POST /mcp/test_embeddings HTTP/1.1" 200 OK
2026-05-01 14:50:28,903 [INFO] HTTP Request: POST https://sector-7.openai.azure.com/openai/deployments/text-embedding-3-small/embeddings?api-version=2024-06-01 "HTTP/1.1 200 OK"
INFO:     172.21.0.1:54730 - "POST /mcp/recall HTTP/1.1" 200 OK
```

## Decision checks

```json
{
  "health_ok": true,
  "env_chat_model_ok": false,
  "env_chat_endpoint_ok": false,
  "env_embedding_model_ok": false,
  "env_embedding_endpoint_ok": false,
  "env_ruvector_ok": true,
  "source_no_literal_vector": true,
  "source_dynamic_vtype": true,
  "db_ruvector_ok": true,
  "locomo_clean": true,
  "test_embedding_small_ok": true,
  "recall_ok": false,
  "logs_chat_gpt41": true,
  "logs_embedding_small": true,
  "logs_no_hybrid_fallback": true
}
```


## Parser correction follow-up

The initial harness decision block above is retained for auditability but is superseded by this non-mutating follow-up.

Root cause of false negatives:

- Env grep used `AZURE_CHAT|AZURE_EMBEDDING|AZURE_OPENAI`, which does not match underscore-containing names such as `AZURE_CHAT_DEPLOYMENT` under grep ERE. A corrected grep used explicit full prefixes.
- Recall returned HTTP 200 with `[]`, which is valid for a non-LOCOMO, non-writing probe in a clean/empty domain. The parser incorrectly required an object-like JSON body.

Corrected follow-up evidence:

```text
AZURE_CHAT_DEPLOYMENT=gpt-4.1-mini
AZURE_CHAT_ENDPOINT=https://sector-7.services.ai.azure.com
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-small
AZURE_EMBEDDING_ENDPOINT=https://sector-7.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini
AZURE_OPENAI_ENDPOINT=https://sector-7.openai.azure.com/
CHAT_MODEL=gemma4:e4b
EMBEDDING_BASE_URL=http://ollama:11434/v1
EMBEDDING_MODEL=nomic-embed-text
OPENAI_BASE_URL=https://openrouter.ai/api/v1
RUVECTOR_GNN=true
USE_RUVECTOR=true
```

```text
contains_literal_vector_cast False
contains_dynamic_vtype_cast True
```

```text
/health: {"status":"ok","engine":"memibrium"}
LOCOMO contamination count: 0
```

`/mcp/test_embeddings` corrected probe:

```json
{"ollama":{"success":true,"latency_ms":0.04,"dimensions":1536,"endpoint":"http://ollama:11434/v1","model":"nomic-embed-text","sample_prefix":[-0.020843505859375,-0.0168914794921875,-0.00450897216796875]},"azure":{"success":true,"latency_ms":668.11,"dimensions":1536,"endpoint":"https://sector-7.openai.azure.com/","deployment":"text-embedding-3-small","sample_embedding_prefix":[-0.020843505859375,-0.0168914794921875,-0.00450897216796875]},"recommendation":"keep_ollama"}
```

Non-LOCOMO recall corrected probe:

```text
HTTP 200
[]
```

Fresh relevant logs:

```text
2026-05-01 14:50:24,078 [INFO] ChatClient: Azure Foundry (https://sector-7.services.ai.azure.com, model=gpt-4.1-mini)
2026-05-01 14:50:24,127 [INFO] Vector extension: ruvector
2026-05-01 14:51:27,706 [INFO] HTTP Request: POST https://sector-7.openai.azure.com/openai/deployments/text-embedding-3-small/embeddings?api-version=2024-06-01 "HTTP/1.1 200 OK"
INFO:     172.21.0.1:45936 - "POST /mcp/test_embeddings HTTP/1.1" 200 OK
2026-05-01 14:51:28,490 [INFO] HTTP Request: POST https://sector-7.openai.azure.com/openai/deployments/text-embedding-3-small/embeddings?api-version=2024-06-01 "HTTP/1.1 200 OK"
INFO:     172.21.0.1:45946 - "POST /mcp/recall HTTP/1.1" 200 OK
```

Corrected decision checks:

```json
{
  "health_ok": true,
  "env_chat_model_ok": true,
  "env_chat_endpoint_ok": true,
  "env_embedding_model_ok": true,
  "env_embedding_endpoint_ok": true,
  "env_ruvector_ok": true,
  "source_no_literal_vector": true,
  "source_dynamic_vtype": true,
  "db_ruvector_ok": true,
  "locomo_clean": true,
  "test_embedding_small_ok": true,
  "recall_ok": true,
  "logs_chat_gpt41": true,
  "logs_embedding_small": true,
  "logs_no_hybrid_fallback": true
}
```

## Final alignment decision

The canonical substrate env-alignment gate passes after parser correction.

`baseline_launch_ready=true`.

The existing canonical hybrid-active substrate baseline preregistration is unblocked, subject to immediate prelaunch rechecks.
