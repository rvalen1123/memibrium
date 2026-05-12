# LOCOMO hybrid rebuild/restart/probe result — 2026-05-01

Generated: `2026-05-01T14:25:55.150432+00:00`
Repo: `/home/zaddy/src/Memibrium`
Verdict: `hybrid-active-positive-after-source-grep-correction`
Hybrid active: `true`

This result executes `docs/eval/locomo_hybrid_rebuild_restart_probe_preregistration_2026-05-01.md`.

## Notes

The single rebuild/restart completed. The initial source-grep capture in the harness returned empty output because the heredoc was not passed into `docker exec`; a follow-up non-mutating `python3 -c` source inspection corrected that artifact. No second rebuild/restart was performed. Runtime evidence after correction supports `hybrid_active=true`. Phase C remains blocked until the separate substrate baseline gate is handled.

## Pre-mutation timestamp

```text
2026-05-01T09:25:47-05:00
```

## Pre-mutation git state

```text
query-expansion
d1224c47afb6918aab2bf1f547af7d77fa6c1330
d1224c4 docs: preregister LOCOMO hybrid substrate baseline
```

## Pre-mutation health

```text
{"status":"ok","engine":"memibrium"}
```

## Pre-mutation docker status

```text
memibrium-server|Up 15 hours (healthy)|memibrium-memibrium
memibrium-ollama|Up 26 hours|ollama/ollama:latest
memibrium-ruvector-db|Up 26 hours (healthy)|ruvnet/ruvector-postgres:latest
```

## Pre-mutation image/container identity

```text
server_image=sha256:3fe64e84a34850fdf40318f8af5b4638d23e14640c3edf1e21f9c998ff024c84 created=2026-04-30T22:56:12.927377452Z started=2026-04-30T22:56:14.714755967Z
image_created=2026-04-24T03:13:55.798256015Z repo_tags=["memibrium-memibrium:latest"]
```

## Pre-mutation redacted env

```text
AZURE_CHAT_API_KEY=<redacted>
AZURE_CHAT_DEPLOYMENT=gpt-4.1-mini
AZURE_CHAT_ENDPOINT=https://sector-7.services.ai.azure.com/models
AZURE_EMBEDDING_API_KEY=<redacted>
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-small
AZURE_EMBEDDING_ENDPOINT=https://sector-7.openai.azure.com/
AZURE_OPENAI_API_KEY=<redacted>
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini
AZURE_OPENAI_ENDPOINT=
CHAT_MODEL=gpt-4.1-mini
DB_HOST=ruvector-db
DB_NAME=memory
DB_PASSWORD=<redacted>
DB_PORT=5432
DB_USER=memory
EMBEDDING_BASE_URL=http://ollama:11434/v1
EMBEDDING_MODEL=nomic-embed-text
OPENAI_BASE_URL=
RUVECTOR_GNN=true
USE_RUVECTOR=true
```

## Pre-mutation source hashes

```text
5efefae8f05b45974dab6a379403e1a94d00a60e2bfb76b403d4ebe4a7e360d5  server.py
a35fe1624ff17bc19190a8ee5959a767b690cb44303907fbfb7f5373fb771fce  hybrid_retrieval.py
df37cef5af863ba29e81077434635cae1da66e7f9b19c5b070baade0cd69822d  /app/server.py
75cc4e079f48b288e655811c3f764daf574a9e0016c3be4f4469cf7bd8aa2bd3  /app/hybrid_retrieval.py
```

## Pre-mutation DB read-only probe

```text
BEGIN
 database | user_name | schema |   search_path
----------+-----------+--------+-----------------
 memory   | memory    | public | "$user", public
(1 row)

 typname  | namespace
----------+-----------
 ruvector | public
(1 row)

 extname  | extversion
----------+------------
 ruvector | 0.3.0
(1 row)

  data_type   | udt_name
--------------+----------
 USER-DEFINED | ruvector
(1 row)

 non_null_embeddings
---------------------
                  19
(1 row)

 locomo_domain_rows
--------------------
                  0
(1 row)

 self_distance
---------------
 1.7872301e-07
(1 row)

ROLLBACK
```

## Pre-mutation recent logs

```text
INFO:     127.0.0.1:45986 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:57600 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:45466 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:56024 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:50620 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:47032 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:42356 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:54040 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:42940 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:47578 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:55308 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:57228 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:42592 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:33882 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:40128 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:46858 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:37748 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:59844 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:57044 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:52774 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:37988 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:41756 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:45310 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:54072 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:33150 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:48960 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:38728 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:58296 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:57588 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:59806 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:52360 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:33976 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:53588 - "GET /health HTTP/1.1" 200 OK
2026-05-01 12:55:22,127 [INFO] Consolidation complete: {'decayed': 0, 'shed': 0, 'crystallized': 0, 'total': 0, 'contradictions_resolved': 0}
INFO:     127.0.0.1:35406 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:35432 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:58156 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:54422 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:37996 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:53676 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:49646 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:59548 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:60688 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:60218 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:52718 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:35172 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:59380 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:33382 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:55214 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:50866 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:52512 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:59572 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:51792 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:60592 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:41194 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:57114 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:57656 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:45960 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:56566 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:46120 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:41952 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:57936 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:57332 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:56160 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:42096 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:40174 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:50802 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:57798 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:48312 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:56022 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:38948 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:58678 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:57772 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:60168 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:44376 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:54554 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:53150 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:38436 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:52096 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:42992 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:60416 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:51290 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:43802 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:54922 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:49586 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:55430 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:45410 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:43446 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:58014 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:40222 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:34578 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:38134 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:58974 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:51418 - "GET /health HTTP/1.1" 200 OK
2026-05-01 13:25:18,455 [INFO] Consolidation complete: {'decayed': 0, 'shed': 0, 'crystallized': 0, 'total': 0, 'contradictions_resolved': 0}
INFO:     127.0.0.1:33546 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:55796 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:51436 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:48036 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:40268 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:35426 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:45280 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:39486 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:57030 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:40914 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:51180 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:58828 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:33800 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:52306 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:35370 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:60894 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:39264 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:51630 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:39340 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:46972 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:44304 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:56102 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:47524 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:45752 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:38388 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:38988 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:52610 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:57728 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:37106 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:33912 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:42046 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:48428 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:44550 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:41766 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:56654 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:41550 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:35146 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:59452 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:42850 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:38776 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:53938 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:44144 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:34296 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:44776 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:42470 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:39960 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:44234 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:51520 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:47924 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:33534 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:40362 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:38156 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:38254 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:49104 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:49598 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:56682 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:52268 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:59310 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:39902 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:59580 - "GET /health HTTP/1.1" 200 OK
2026-05-01 13:55:14,729 [INFO] Consolidation complete: {'decayed': 0, 'shed': 0, 'crystallized': 0, 'total': 0, 'contradictions_resolved': 0}
INFO:     127.0.0.1:51688 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:40280 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:39984 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:38710 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:58010 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:54004 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:39808 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:50280 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:39384 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:46950 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:40204 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:54106 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:48332 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:38588 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:51978 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:50754 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:60070 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:39846 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:41612 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:37342 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:57772 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:36194 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:60198 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:46474 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:35482 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:51456 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:48482 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:58160 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:51152 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:44870 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:46686 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:43436 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:50394 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:36206 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:59948 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:52512 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:51398 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:40836 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:55326 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:59128 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:42366 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:55106 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:56348 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:37446 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:53766 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:49176 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:37558 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:60074 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:50052 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:48812 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:34224 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:47740 - "GET /health HTTP/1.1" 200 OK
INFO:     172.21.0.1:34968 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:53230 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:57546 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:59668 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:42688 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:59346 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:44558 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:58914 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:48642 - "GET /health HTTP/1.1" 200 OK
2026-05-01 14:25:10,728 [INFO] Consolidation complete: {'decayed': 0, 'shed': 0, 'crystallized': 0, 'total': 0, 'contradictions_resolved': 0}
INFO:     127.0.0.1:40286 - "GET /health HTTP/1.1" 200 OK
INFO:     172.21.0.1:53376 - "GET /health HTTP/1.1" 200 OK
```

## Mutation command

```text
 Image memibrium-memibrium Building
#1 [internal] load local bake definitions
#1 reading from stdin 518B done
#1 DONE 0.0s

#2 [internal] load build definition from Dockerfile
#2 transferring dockerfile: 697B done
#2 DONE 0.0s

#3 [internal] load metadata for docker.io/library/python:3.11-slim
#3 DONE 0.0s

#4 [internal] load .dockerignore
#4 transferring context: 182B done
#4 DONE 0.0s

#5 [internal] load build context
#5 transferring context: 114.39kB done
#5 DONE 0.0s

#6 [ 1/11] FROM docker.io/library/python:3.11-slim@sha256:233de06753d30d120b1a3ce359d8d3be8bda78524cd8f520c99883bfe33964cf
#6 resolve docker.io/library/python:3.11-slim@sha256:233de06753d30d120b1a3ce359d8d3be8bda78524cd8f520c99883bfe33964cf 0.0s done
#6 DONE 0.0s

#7 [ 2/11] WORKDIR /app
#7 CACHED

#8 [ 3/11] RUN apt-get update &&     apt-get install -y --no-install-recommends libpq-dev &&     rm -rf /var/lib/apt/lists/*
#8 CACHED

#9 [ 4/11] COPY requirements.txt .
#9 CACHED

#10 [ 5/11] RUN pip install --no-cache-dir -r requirements.txt
#10 CACHED

#11 [ 6/11] COPY server.py .
#11 DONE 0.0s

#12 [ 7/11] COPY ingest_engine.py .
#12 DONE 0.0s

#13 [ 8/11] COPY knowledge_taxonomy.py .
#13 DONE 0.0s

#14 [ 9/11] COPY hybrid_retrieval.py .
#14 DONE 0.0s

#15 [10/11] COPY memory_hierarchy.py .
#15 DONE 0.0s

#16 [11/11] COPY skills/ ./skills/
#16 DONE 0.0s

#17 exporting to image
#17 exporting layers
#17 exporting layers 0.2s done
#17 exporting manifest sha256:690e09e654e234b738b41e1179e09acc5ab6d2d01a1cbba7791bd7569334b8fb 0.0s done
#17 exporting config sha256:4ad33aef5d724586282f645ee50b6222c2a8d4e27617ae4e43eac3b973a58086 0.0s done
#17 exporting attestation manifest sha256:0a4ce62963e7d2cd9dfb0d48f427df011cd9857807b02ce6f1b8517a8789bda1 0.0s done
#17 exporting manifest list sha256:e61857cc17f69f5cc6c76971fabe02b6657156148847aaaf711939707b6f0356 0.0s done
#17 naming to docker.io/library/memibrium-memibrium:latest done
#17 unpacking to docker.io/library/memibrium-memibrium:latest 0.1s done
#17 DONE 0.4s

#18 resolving provenance for metadata file
#18 DONE 0.0s
 Image memibrium-memibrium Built
 Container memibrium-ruvector-db Running
 Container memibrium-ollama Running
 Container memibrium-server Recreate
 Container memibrium-server Recreated
 Container memibrium-server Starting
 Container memibrium-server Started
```

## Post-restart health polling

```text
poll 1 exit=56
curl: (56) Recv failure: Connection reset by peer

poll 2 exit=0
{"status":"ok","engine":"memibrium"}
```

## Post-restart docker status

```text
memibrium-server|Up 2 seconds (health: starting)|memibrium-memibrium
memibrium-ollama|Up 26 hours|ollama/ollama:latest
memibrium-ruvector-db|Up 26 hours (healthy)|ruvnet/ruvector-postgres:latest
```

## Post-restart image/container identity

```text
server_image=sha256:e61857cc17f69f5cc6c76971fabe02b6657156148847aaaf711939707b6f0356 created=2026-05-01T14:25:49.293372603Z started=2026-05-01T14:25:50.597734128Z
image_created=2026-05-01T14:25:48.558179254Z repo_tags=["memibrium-memibrium:latest"]
```

## Post-restart redacted env

```text
AZURE_CHAT_API_KEY=<redacted>
AZURE_CHAT_DEPLOYMENT=grok-4-20-non-reasoning-1
AZURE_CHAT_ENDPOINT=https://sector-7.services.ai.azure.com
AZURE_EMBEDDING_API_KEY=<redacted>
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-large-1
AZURE_EMBEDDING_ENDPOINT=https://sector-7.services.ai.azure.com
AZURE_OPENAI_API_KEY=<redacted>
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini
AZURE_OPENAI_ENDPOINT=https://sector-7.openai.azure.com/
CHAT_MODEL=gemma4:e4b
DB_HOST=ruvector-db
DB_NAME=memory
DB_PASSWORD=<redacted>
DB_PORT=5432
DB_USER=memory
EMBEDDING_BASE_URL=http://ollama:11434/v1
EMBEDDING_MODEL=nomic-embed-text
OPENAI_BASE_URL=https://openrouter.ai/api/v1
RUVECTOR_GNN=true
USE_RUVECTOR=true
```

## Post-restart source hashes

```text
5efefae8f05b45974dab6a379403e1a94d00a60e2bfb76b403d4ebe4a7e360d5  server.py
a35fe1624ff17bc19190a8ee5959a767b690cb44303907fbfb7f5373fb771fce  hybrid_retrieval.py
5efefae8f05b45974dab6a379403e1a94d00a60e2bfb76b403d4ebe4a7e360d5  /app/server.py
a35fe1624ff17bc19190a8ee5959a767b690cb44303907fbfb7f5373fb771fce  /app/hybrid_retrieval.py
```

## Post-restart source grep

Initial harness output was empty because the heredoc body was not passed into `docker exec`. Corrected with a non-mutating `python3 -c` source inspection after the same single rebuild/restart:

```text
contains_literal_vector_cast False
contains_dynamic_vtype_cast True
403:                    1 - (embedding <=> $1::{self.vtype}) AS cosine_score
406:             ORDER BY embedding <=> $1::{self.vtype}
```

## Post-restart DB read-only probe

```text
BEGIN
 database | user_name | schema |   search_path
----------+-----------+--------+-----------------
 memory   | memory    | public | "$user", public
(1 row)

 typname  | namespace
----------+-----------
 ruvector | public
(1 row)

 extname  | extversion
----------+------------
 ruvector | 0.3.0
(1 row)

  data_type   | udt_name
--------------+----------
 USER-DEFINED | ruvector
(1 row)

 non_null_embeddings
---------------------
                  19
(1 row)

 locomo_domain_rows
--------------------
                  0
(1 row)

 self_distance
---------------
 1.7872301e-07
(1 row)

ROLLBACK
```

## Logs before positive probe

```text
2026-05-01 14:25:51,729 [INFO] ChatClient: Azure Foundry (https://sector-7.services.ai.azure.com, model=grok-4-20-non-reasoning-1)
INFO:     Started server process [1]
INFO:     Waiting for application startup.
2026-05-01 14:25:51,779 [INFO] Vector extension: ruvector
2026-05-01 14:25:51,788 [INFO] RuVector HNSW index with GNN re-ranking enabled
2026-05-01 14:25:51,793 [INFO] Schema initialized: memories, snapshots, entities, feedback, contradictions, edges
2026-05-01 14:25:51,794 [INFO] LEANN not installed — cold tier stays in pgvector/ruvector (pip install leann to enable)
2026-05-01 14:25:51,794 [INFO] Advanced modules initialized: hybrid retrieval + memory hierarchy
2026-05-01 14:25:51,794 [INFO] Memibrium started — hot: ruvector (GNN + SONA), cold: pgvector, fully sovereign
2026-05-01 14:25:51,795 [INFO] ConsolidateAgent started (interval=30min)
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:9999 (Press CTRL+C to quit)
2026-05-01 14:25:51,810 [INFO] Consolidation complete: {'decayed': 0, 'shed': 0, 'crystallized': 0, 'total': 0, 'contradictions_resolved': 0}
INFO:     172.21.0.1:37550 - "GET /health HTTP/1.1" 200 OK
```

## Positive recall probe response

```text
[]
```

## Logs after positive probe

```text
2026-05-01 14:25:51,729 [INFO] ChatClient: Azure Foundry (https://sector-7.services.ai.azure.com, model=grok-4-20-non-reasoning-1)
INFO:     Started server process [1]
INFO:     Waiting for application startup.
2026-05-01 14:25:51,779 [INFO] Vector extension: ruvector
2026-05-01 14:25:51,788 [INFO] RuVector HNSW index with GNN re-ranking enabled
2026-05-01 14:25:51,793 [INFO] Schema initialized: memories, snapshots, entities, feedback, contradictions, edges
2026-05-01 14:25:51,794 [INFO] LEANN not installed — cold tier stays in pgvector/ruvector (pip install leann to enable)
2026-05-01 14:25:51,794 [INFO] Advanced modules initialized: hybrid retrieval + memory hierarchy
2026-05-01 14:25:51,794 [INFO] Memibrium started — hot: ruvector (GNN + SONA), cold: pgvector, fully sovereign
2026-05-01 14:25:51,795 [INFO] ConsolidateAgent started (interval=30min)
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:9999 (Press CTRL+C to quit)
2026-05-01 14:25:51,810 [INFO] Consolidation complete: {'decayed': 0, 'shed': 0, 'crystallized': 0, 'total': 0, 'contradictions_resolved': 0}
INFO:     172.21.0.1:37550 - "GET /health HTTP/1.1" 200 OK
2026-05-01 14:25:55,107 [INFO] HTTP Request: POST https://sector-7.services.ai.azure.com/openai/deployments/text-embedding-3-large-1/embeddings?api-version=2024-06-01 "HTTP/1.1 200 OK"
INFO:     172.21.0.1:37558 - "POST /mcp/recall HTTP/1.1" 200 OK
```

## Decision criteria

```json
{
  "health_ok": true,
  "source_ok_no_hardcoded_vector_dynamic_vtype_present": true,
  "env_USE_RUVECTOR_true": true,
  "db_ruvector_self_distance_ok": true,
  "probe_valid_response": true,
  "fresh_logs_no_hybrid_or_vector_fallback": true,
  "note": "source_ok corrected by non-mutating python -c inspection after initial heredoc capture bug"
}
```

## Substrate drift noted before baseline

The rebuild/restart picked up current compose/.env values that differ from the recovered 66.08% floor environment:

- Pre-mutation container env showed `AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-small` and `AZURE_CHAT_DEPLOYMENT=gpt-4.1-mini`.
- Post-restart container env showed `AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-large-1` and `AZURE_CHAT_DEPLOYMENT=grok-4-20-non-reasoning-1`.
- Fresh recall/test-embedding logs call `/openai/deployments/text-embedding-3-large-1/embeddings`.

This does not invalidate the hybrid-active proof, but it is a pre-launch comparability issue for the separately preregistered substrate baseline.

## Raw command index

### date

Command: `date -Is`
Exit: `0`

```text
2026-05-01T09:25:47-05:00
```

### git state

Command: `git branch --show-current && git rev-parse HEAD && git status --short && git log -1 --oneline`
Exit: `0`

```text
query-expansion
d1224c47afb6918aab2bf1f547af7d77fa6c1330
d1224c4 docs: preregister LOCOMO hybrid substrate baseline
```

### pre health

Command: `curl -fsS http://localhost:9999/health`
Exit: `0`

```text
{"status":"ok","engine":"memibrium"}
```

### pre docker ps

Command: `docker ps --format '{{.Names}}|{{.Status}}|{{.Image}}' | grep -E 'memibrium|ruvector|ollama' || true`
Exit: `0`

```text
memibrium-server|Up 15 hours (healthy)|memibrium-memibrium
memibrium-ollama|Up 26 hours|ollama/ollama:latest
memibrium-ruvector-db|Up 26 hours (healthy)|ruvnet/ruvector-postgres:latest
```

### pre container inspect

Command: `docker inspect memibrium-server --format 'server_image={{.Image}} created={{.Created}} started={{.State.StartedAt}}'`
Exit: `0`

```text
server_image=sha256:3fe64e84a34850fdf40318f8af5b4638d23e14640c3edf1e21f9c998ff024c84 created=2026-04-30T22:56:12.927377452Z started=2026-04-30T22:56:14.714755967Z
```

### pre image id

Command: `docker inspect memibrium-server --format '{{.Image}}'`
Exit: `0`

```text
sha256:3fe64e84a34850fdf40318f8af5b4638d23e14640c3edf1e21f9c998ff024c84
```

### pre image inspect

Command: `docker image inspect sha256:3fe64e84a34850fdf40318f8af5b4638d23e14640c3edf1e21f9c998ff024c84 --format 'image_created={{.Created}} repo_tags={{json .RepoTags}}'`
Exit: `0`

```text
image_created=2026-04-24T03:13:55.798256015Z repo_tags=["memibrium-memibrium:latest"]
```

### pre redacted env

Command: `docker exec memibrium-server env | sort | grep -E '^(DATABASE_URL|DB_|POSTGRES|PG|USE_RUVECTOR|RUVECTOR|VECTOR|EMBEDDING|AZURE_EMBEDDING|AZURE_CHAT|AZURE_OPENAI|OPENAI_BASE_URL|CHAT_MODEL)' || true`
Exit: `0`

```text
AZURE_CHAT_API_KEY=<redacted>
AZURE_CHAT_DEPLOYMENT=gpt-4.1-mini
AZURE_CHAT_ENDPOINT=https://sector-7.services.ai.azure.com/models
AZURE_EMBEDDING_API_KEY=<redacted>
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-small
AZURE_EMBEDDING_ENDPOINT=https://sector-7.openai.azure.com/
AZURE_OPENAI_API_KEY=<redacted>
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini
AZURE_OPENAI_ENDPOINT=
CHAT_MODEL=gpt-4.1-mini
DB_HOST=ruvector-db
DB_NAME=memory
DB_PASSWORD=<redacted>
DB_PORT=5432
DB_USER=memory
EMBEDDING_BASE_URL=http://ollama:11434/v1
EMBEDDING_MODEL=nomic-embed-text
OPENAI_BASE_URL=
RUVECTOR_GNN=true
USE_RUVECTOR=true
```

### pre host hashes

Command: `sha256sum server.py hybrid_retrieval.py`
Exit: `0`

```text
5efefae8f05b45974dab6a379403e1a94d00a60e2bfb76b403d4ebe4a7e360d5  server.py
a35fe1624ff17bc19190a8ee5959a767b690cb44303907fbfb7f5373fb771fce  hybrid_retrieval.py
```

### pre container hashes

Command: `docker exec memibrium-server sha256sum /app/server.py /app/hybrid_retrieval.py`
Exit: `0`

```text
df37cef5af863ba29e81077434635cae1da66e7f9b19c5b070baade0cd69822d  /app/server.py
75cc4e079f48b288e655811c3f764daf574a9e0016c3be4f4469cf7bd8aa2bd3  /app/hybrid_retrieval.py
```

### pre db probe

Command: `docker exec -i memibrium-ruvector-db psql -U memory -d memory -v ON_ERROR_STOP=1 <<'SQL'
BEGIN READ ONLY;
SELECT current_database() AS database, current_user AS user_name, current_schema() AS schema, current_setting('search_path') AS search_path;
SELECT typname, typnamespace::regnamespace::text AS namespace FROM pg_type WHERE typname IN ('vector','ruvector') ORDER BY typname;
SELECT extname, extversion FROM pg_extension WHERE extname IN ('vector','ruvector') ORDER BY extname;
SELECT data_type, udt_name FROM information_schema.columns WHERE table_name='memories' AND column_name='embedding';
SELECT count(id) AS non_null_embeddings FROM memories WHERE embedding IS NOT NULL;
SELECT count(id) AS locomo_domain_rows FROM memories WHERE domain LIKE 'locomo-%';
SELECT (embedding <=> embedding) AS self_distance FROM memories WHERE embedding IS NOT NULL LIMIT 1;
ROLLBACK;
SQL`
Exit: `0`

```text
BEGIN
 database | user_name | schema |   search_path
----------+-----------+--------+-----------------
 memory   | memory    | public | "$user", public
(1 row)

 typname  | namespace
----------+-----------
 ruvector | public
(1 row)

 extname  | extversion
----------+------------
 ruvector | 0.3.0
(1 row)

  data_type   | udt_name
--------------+----------
 USER-DEFINED | ruvector
(1 row)

 non_null_embeddings
---------------------
                  19
(1 row)

 locomo_domain_rows
--------------------
                  0
(1 row)

 self_distance
---------------
 1.7872301e-07
(1 row)

ROLLBACK
```

### docker logs tail 220

Command: `docker logs --tail 220 memibrium-server 2>&1`
Exit: `0`

```text
2026-05-01 14:25:51,729 [INFO] ChatClient: Azure Foundry (https://sector-7.services.ai.azure.com, model=grok-4-20-non-reasoning-1)
INFO:     Started server process [1]
INFO:     Waiting for application startup.
2026-05-01 14:25:51,779 [INFO] Vector extension: ruvector
2026-05-01 14:25:51,788 [INFO] RuVector HNSW index with GNN re-ranking enabled
2026-05-01 14:25:51,793 [INFO] Schema initialized: memories, snapshots, entities, feedback, contradictions, edges
2026-05-01 14:25:51,794 [INFO] LEANN not installed — cold tier stays in pgvector/ruvector (pip install leann to enable)
2026-05-01 14:25:51,794 [INFO] Advanced modules initialized: hybrid retrieval + memory hierarchy
2026-05-01 14:25:51,794 [INFO] Memibrium started — hot: ruvector (GNN + SONA), cold: pgvector, fully sovereign
2026-05-01 14:25:51,795 [INFO] ConsolidateAgent started (interval=30min)
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:9999 (Press CTRL+C to quit)
2026-05-01 14:25:51,810 [INFO] Consolidation complete: {'decayed': 0, 'shed': 0, 'crystallized': 0, 'total': 0, 'contradictions_resolved': 0}
INFO:     172.21.0.1:37550 - "GET /health HTTP/1.1" 200 OK
2026-05-01 14:25:55,107 [INFO] HTTP Request: POST https://sector-7.services.ai.azure.com/openai/deployments/text-embedding-3-large-1/embeddings?api-version=2024-06-01 "HTTP/1.1 200 OK"
INFO:     172.21.0.1:37558 - "POST /mcp/recall HTTP/1.1" 200 OK
```

### single rebuild restart

Command: `docker compose -f docker-compose.ruvector.yml up -d --build memibrium`
Exit: `0`

```text
 Image memibrium-memibrium Building
#1 [internal] load local bake definitions
#1 reading from stdin 518B done
#1 DONE 0.0s

#2 [internal] load build definition from Dockerfile
#2 transferring dockerfile: 697B done
#2 DONE 0.0s

#3 [internal] load metadata for docker.io/library/python:3.11-slim
#3 DONE 0.0s

#4 [internal] load .dockerignore
#4 transferring context: 182B done
#4 DONE 0.0s

#5 [internal] load build context
#5 transferring context: 114.39kB done
#5 DONE 0.0s

#6 [ 1/11] FROM docker.io/library/python:3.11-slim@sha256:233de06753d30d120b1a3ce359d8d3be8bda78524cd8f520c99883bfe33964cf
#6 resolve docker.io/library/python:3.11-slim@sha256:233de06753d30d120b1a3ce359d8d3be8bda78524cd8f520c99883bfe33964cf 0.0s done
#6 DONE 0.0s

#7 [ 2/11] WORKDIR /app
#7 CACHED

#8 [ 3/11] RUN apt-get update &&     apt-get install -y --no-install-recommends libpq-dev &&     rm -rf /var/lib/apt/lists/*
#8 CACHED

#9 [ 4/11] COPY requirements.txt .
#9 CACHED

#10 [ 5/11] RUN pip install --no-cache-dir -r requirements.txt
#10 CACHED

#11 [ 6/11] COPY server.py .
#11 DONE 0.0s

#12 [ 7/11] COPY ingest_engine.py .
#12 DONE 0.0s

#13 [ 8/11] COPY knowledge_taxonomy.py .
#13 DONE 0.0s

#14 [ 9/11] COPY hybrid_retrieval.py .
#14 DONE 0.0s

#15 [10/11] COPY memory_hierarchy.py .
#15 DONE 0.0s

#16 [11/11] COPY skills/ ./skills/
#16 DONE 0.0s

#17 exporting to image
#17 exporting layers
#17 exporting layers 0.2s done
#17 exporting manifest sha256:690e09e654e234b738b41e1179e09acc5ab6d2d01a1cbba7791bd7569334b8fb 0.0s done
#17 exporting config sha256:4ad33aef5d724586282f645ee50b6222c2a8d4e27617ae4e43eac3b973a58086 0.0s done
#17 exporting attestation manifest sha256:0a4ce62963e7d2cd9dfb0d48f427df011cd9857807b02ce6f1b8517a8789bda1 0.0s done
#17 exporting manifest list sha256:e61857cc17f69f5cc6c76971fabe02b6657156148847aaaf711939707b6f0356 0.0s done
#17 naming to docker.io/library/memibrium-memibrium:latest done
#17 unpacking to docker.io/library/memibrium-memibrium:latest 0.1s done
#17 DONE 0.4s

#18 resolving provenance for metadata file
#18 DONE 0.0s
 Image memibrium-memibrium Built
 Container memibrium-ruvector-db Running
 Container memibrium-ollama Running
 Container memibrium-server Recreate
 Container memibrium-server Recreated
 Container memibrium-server Starting
 Container memibrium-server Started
```

### post health poll 1

Command: `curl -fsS http://localhost:9999/health`
Exit: `56`

```text
curl: (56) Recv failure: Connection reset by peer
```

### post health poll 2

Command: `curl -fsS http://localhost:9999/health`
Exit: `0`

```text
{"status":"ok","engine":"memibrium"}
```

### post docker ps

Command: `docker ps --format '{{.Names}}|{{.Status}}|{{.Image}}' | grep -E 'memibrium|ruvector|ollama' || true`
Exit: `0`

```text
memibrium-server|Up 2 seconds (health: starting)|memibrium-memibrium
memibrium-ollama|Up 26 hours|ollama/ollama:latest
memibrium-ruvector-db|Up 26 hours (healthy)|ruvnet/ruvector-postgres:latest
```

### post container inspect

Command: `docker inspect memibrium-server --format 'server_image={{.Image}} created={{.Created}} started={{.State.StartedAt}}'`
Exit: `0`

```text
server_image=sha256:e61857cc17f69f5cc6c76971fabe02b6657156148847aaaf711939707b6f0356 created=2026-05-01T14:25:49.293372603Z started=2026-05-01T14:25:50.597734128Z
```

### post image id

Command: `docker inspect memibrium-server --format '{{.Image}}'`
Exit: `0`

```text
sha256:e61857cc17f69f5cc6c76971fabe02b6657156148847aaaf711939707b6f0356
```

### post image inspect

Command: `docker image inspect sha256:e61857cc17f69f5cc6c76971fabe02b6657156148847aaaf711939707b6f0356 --format 'image_created={{.Created}} repo_tags={{json .RepoTags}}'`
Exit: `0`

```text
image_created=2026-05-01T14:25:48.558179254Z repo_tags=["memibrium-memibrium:latest"]
```

### post redacted env

Command: `docker exec memibrium-server env | sort | grep -E '^(DATABASE_URL|DB_|POSTGRES|PG|USE_RUVECTOR|RUVECTOR|VECTOR|EMBEDDING|AZURE_EMBEDDING|AZURE_CHAT|AZURE_OPENAI|OPENAI_BASE_URL|CHAT_MODEL)' || true`
Exit: `0`

```text
AZURE_CHAT_API_KEY=<redacted>
AZURE_CHAT_DEPLOYMENT=grok-4-20-non-reasoning-1
AZURE_CHAT_ENDPOINT=https://sector-7.services.ai.azure.com
AZURE_EMBEDDING_API_KEY=<redacted>
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-large-1
AZURE_EMBEDDING_ENDPOINT=https://sector-7.services.ai.azure.com
AZURE_OPENAI_API_KEY=<redacted>
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini
AZURE_OPENAI_ENDPOINT=https://sector-7.openai.azure.com/
CHAT_MODEL=gemma4:e4b
DB_HOST=ruvector-db
DB_NAME=memory
DB_PASSWORD=<redacted>
DB_PORT=5432
DB_USER=memory
EMBEDDING_BASE_URL=http://ollama:11434/v1
EMBEDDING_MODEL=nomic-embed-text
OPENAI_BASE_URL=https://openrouter.ai/api/v1
RUVECTOR_GNN=true
USE_RUVECTOR=true
```

### post host hashes

Command: `sha256sum server.py hybrid_retrieval.py`
Exit: `0`

```text
5efefae8f05b45974dab6a379403e1a94d00a60e2bfb76b403d4ebe4a7e360d5  server.py
a35fe1624ff17bc19190a8ee5959a767b690cb44303907fbfb7f5373fb771fce  hybrid_retrieval.py
```

### post container hashes

Command: `docker exec memibrium-server sha256sum /app/server.py /app/hybrid_retrieval.py`
Exit: `0`

```text
5efefae8f05b45974dab6a379403e1a94d00a60e2bfb76b403d4ebe4a7e360d5  /app/server.py
a35fe1624ff17bc19190a8ee5959a767b690cb44303907fbfb7f5373fb771fce  /app/hybrid_retrieval.py
```

### post source grep

Command: `docker exec memibrium-server python3 - <<'PY'
from pathlib import Path
p=Path('/app/hybrid_retrieval.py')
s=p.read_text()
print('contains_$1_vector=', '$1::vector' in s)
print('contains_dynamic_vtype=', '$1::{self.vtype}' in s)
for i,line in enumerate(s.splitlines(),1):
    if '$1::' in line or '$1::{self.vtype}' in line or '<=> $1' in line:
        print(f'{i}: {line}')
PY`
Exit: `0`

```text

```

### post db probe

Command: `docker exec -i memibrium-ruvector-db psql -U memory -d memory -v ON_ERROR_STOP=1 <<'SQL'
BEGIN READ ONLY;
SELECT current_database() AS database, current_user AS user_name, current_schema() AS schema, current_setting('search_path') AS search_path;
SELECT typname, typnamespace::regnamespace::text AS namespace FROM pg_type WHERE typname IN ('vector','ruvector') ORDER BY typname;
SELECT extname, extversion FROM pg_extension WHERE extname IN ('vector','ruvector') ORDER BY extname;
SELECT data_type, udt_name FROM information_schema.columns WHERE table_name='memories' AND column_name='embedding';
SELECT count(id) AS non_null_embeddings FROM memories WHERE embedding IS NOT NULL;
SELECT count(id) AS locomo_domain_rows FROM memories WHERE domain LIKE 'locomo-%';
SELECT (embedding <=> embedding) AS self_distance FROM memories WHERE embedding IS NOT NULL LIMIT 1;
ROLLBACK;
SQL`
Exit: `0`

```text
BEGIN
 database | user_name | schema |   search_path
----------+-----------+--------+-----------------
 memory   | memory    | public | "$user", public
(1 row)

 typname  | namespace
----------+-----------
 ruvector | public
(1 row)

 extname  | extversion
----------+------------
 ruvector | 0.3.0
(1 row)

  data_type   | udt_name
--------------+----------
 USER-DEFINED | ruvector
(1 row)

 non_null_embeddings
---------------------
                  19
(1 row)

 locomo_domain_rows
--------------------
                  0
(1 row)

 self_distance
---------------
 1.7872301e-07
(1 row)

ROLLBACK
```

### positive recall probe

Command: `curl -fsS -X POST http://localhost:9999/mcp/recall -H 'Content-Type: application/json' -d '{"query":"hybrid active ruvector smoke probe", "top_k":1, "domain":"__hybrid_active_probe_no_rows__"}'`
Exit: `0`

```text
[]
```


## Corrected non-mutating source inspection command

Command run after the harness source-grep capture bug, with no rebuild/restart and no DB mutation:

```text
docker exec memibrium-server python3 -c 'from pathlib import Path
s=Path("/app/hybrid_retrieval.py").read_text()
print("contains_literal_vector_cast", "$1::vector" in s)
print("contains_dynamic_vtype_cast", "$1::{self.vtype}" in s)
for i,line in enumerate(s.splitlines(),1):
    if "$1::" in line or "$1::{self.vtype}" in line or "<=> $1" in line:
        print(f"{i}: {line}")'

contains_literal_vector_cast False
contains_dynamic_vtype_cast True
403:                    1 - (embedding <=> $1::{self.vtype}) AS cosine_score
406:             ORDER BY embedding <=> $1::{self.vtype}
```
