# LOCOMO Phase B.5 hybrid-active root-cause addendum — 2026-05-01

Scope: read-only/diagnostic only. No benchmark launch. No runtime mutation. No container rebuild/restart. No DB write. Commands used: Docker inspect/log/env reads, HTTP dashboard/health reads, source inspection, and `BEGIN READ ONLY` DB probes.

## Headline

Hybrid-active is false in the currently running server because the live container is running an older `hybrid_retrieval.py` that hard-codes `$1::vector` in semantic search, while the DB has only the `ruvector` type.

This is not a DB substrate failure. It is not primarily a search_path failure. It is not evidence that the server is pointed at the wrong DB. It is a stale server-image/source mismatch.

## Evidence

### DB/probe target

Read-only DB probe was run directly in `memibrium-ruvector-db` against `memory` as user `memory`.

- `current_database()`: `memory`
- `current_user`: `memory`
- `current_schema()`: `public`
- `search_path`: `"$user", public`
- `pg_type` contains `ruvector` in `public`
- `pg_type` does not contain `vector`
- `pg_extension`: `ruvector` version `0.3.0`
- `memories.embedding`: `USER-DEFINED:ruvector`
- `(embedding <=> embedding)` succeeds in a read-only transaction

### Live server env

Live `memibrium-server` env points at the same Docker DB target:

- `DB_HOST=ruvector-db`
- `DB_PORT=5432`
- `DB_NAME=memory`
- `DB_USER=memory`
- `USE_RUVECTOR=true`

Secret-like values were redacted in terminal output. The DB target is consistent with the probe target.

### Live server/image age

- Server container image ID: `sha256:3fe64e84a34850fdf40318f8af5b4638d23e14640c3edf1e21f9c998ff024c84`
- Repo tag: `memibrium-memibrium:latest`
- Image created: `2026-04-24T03:13:55.798256015Z`
- Container created: `2026-04-30T22:56:12.927377452Z`
- Container started: `2026-04-30T22:56:14.714755967Z`

The running image predates the current host source state and likely predates the current hybrid retrieval fix.

### Source mismatch: host vs container

Host hashes:

- `server.py`: `5efefae8f05b45974dab6a379403e1a94d00a60e2bfb76b403d4ebe4a7e360d5`
- `hybrid_retrieval.py`: `a35fe1624ff17bc19190a8ee5959a767b690cb44303907fbfb7f5373fb771fce`

Container hashes:

- `/app/server.py`: `df37cef5af863ba29e81077434635cae1da66e7f9b19c5b070baade0cd69822d`
- `/app/hybrid_retrieval.py`: `75cc4e079f48b288e655811c3f764daf574a9e0016c3be4f4469cf7bd8aa2bd3`

Host current `hybrid_retrieval.py` semantic query:

```python
1 - (embedding <=> $1::{self.vtype}) AS cosine_score
ORDER BY embedding <=> $1::{self.vtype}
```

Container `/app/hybrid_retrieval.py` semantic query:

```python
1 - (embedding <=> $1::vector) AS cosine_score
ORDER BY embedding <=> $1::vector
```

Live logs match the stale container source:

```text
Hybrid retrieval failed: type "vector" does not exist, falling back to legacy recall
```

### Dashboard caveat

`/mcp/dashboard` reports architecture `vector_extension: ruvector` and feature `hybrid_retrieval`, but this is only config/feature-surface evidence. It does not prove semantic hybrid search is executing. The hard-coded `$1::vector` in the live container causes runtime fallback despite the dashboard reporting ruvector.

## Hypothesis ranking

1. **Confirmed root cause: stale live container source/image hard-codes `$1::vector` in `/app/hybrid_retrieval.py`.**
2. Wrong DB/schema/search_path: unlikely. Env and probe targets align; `ruvector` is in `public` and visible under the active search_path.
3. Pre-install pooled connections: unlikely as primary root cause. The error text is produced by a query that names `vector`; a pool refresh would not make a nonexistent `vector` type exist in a DB that only has `ruvector`.
4. ORM/driver naming `vector`: confirmed at source-query level, not ORM. The container source itself names `$1::vector`.

## Methodological implication

All prior LOCOMO artifact-history scores produced by this live server path should be treated as **legacy-recall fallback scores**, not measured hybrid-retrieval scores, unless a specific run independently proves hybrid-active binary status.

That includes the recovered 66.08% `text-embedding-3-small` conv-26 run in the current investigation history. It is a useful floor/baseline, but not evidence of hybrid-retrieval performance.

Future Phase D interpretation must separate:

- substrate/image fix effects: legacy fallback -> actual hybrid path;
- Phase C intervention effects: any precision/evidence-selection change after hybrid-active is true.

Do not attribute a post-fix score jump to a Phase C intervention unless there is a fresh no-intervention hybrid-active baseline.

## Required unblock before Phase C

Minimum safe sequence before choosing/testing a Phase C intervention:

1. Make a small surgical code/image fix or rebuild/restart so live `/app/hybrid_retrieval.py` uses `$1::{self.vtype}` or equivalent ruvector-safe casting.
2. Add/keep a unit test that fails if semantic search hard-codes `::vector` when `vtype='ruvector'`.
3. Rebuild/restart only in an explicitly authorized mutation window.
4. Re-run binary hybrid-active probe.
5. Run a no-intervention hybrid-active LOCOMO baseline only if explicitly authorized; otherwise Phase C comparisons will remain confounded by legacy->hybrid substrate change.

## Judge-leniency gap note

The frozen judge-leniency probe is categories 1–4 only because the upstream Penfield AP baseline excludes category 5/adversarial. Future leniency measurements from `judge_leniency_probe_40q_2026-05-01.json` must be labeled **category-1-through-4 judge leniency**, not category-5 leniency.

If audit-corrected category-5 assets later support a defensible intentionally-wrong cat-5 probe, add it as a secondary Phase E metric with its own hash and scoring basis. Do not mix it into the pinned AP-baseline probe without changing the artifact version.

## License/source preservation

The local pinned audit copy now includes upstream license notices:

- `locomo_audit_9493fb4b4af4256ed17a18e8fd0b3cfdeec29539/LICENSE`
- `locomo_audit_9493fb4b4af4256ed17a18e8fd0b3cfdeec29539/THIRD-PARTY-NOTICES.md`

License/provenance to preserve in future writeups:

- `dial481/locomo-audit` / Penfield Labs correction and AP-baseline assets, pinned at commit `9493fb4b4af4256ed17a18e8fd0b3cfdeec29539`.
- LoCoMo dataset: Maharana, Lee, Tuber, and Bansal / SNAP Research, CC BY-NC 4.0.
- EverMemOS prompt asset notice where applicable, Apache 2.0, as recorded in upstream `THIRD-PARTY-NOTICES.md`.

## Phase B.5 status

- Root cause diagnosis: complete.
- Runtime mutation: none.
- Benchmark launch: none.
- Phase C: still blocked until live hybrid-active binary probe flips to true and a no-intervention hybrid-active baseline policy is decided.
