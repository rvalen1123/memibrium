# LOCOMO Phase B artifact manifest — 2026-05-01

Scope: Phase B only. No LOCOMO benchmark was launched. No runtime/container/DB mutation was performed. Runtime checks were read-only HTTP, Docker log/status, and `BEGIN READ ONLY` DB probes. File mutations were limited to local artifact scaffolding under `docs/eval/phase_b_artifacts/` plus the helper script `scripts/phase_b_extract_probe_subset.py`.

## Repo state at start

- Repo: `/home/zaddy/src/Memibrium`
- Branch: `query-expansion`
- HEAD: `a611a218379928090499fbbbed4ee652ae171aa4`
- Plan opened: `/home/zaddy/src/Memibrium/.hermes/plans/2026-05-01_031922-locomo-top-tier-final-push.md`

## Hybrid-active verification

Binary result: **NOT ACTIVE in the currently running server**.

Evidence:

1. Health/container status:
   - `curl http://localhost:9999/health` returned `{"status":"ok","engine":"memibrium"}`.
   - `memibrium-server` was healthy; `memibrium-ruvector-db` was healthy.
2. DB ruvector read-only probe:
   - `pg_extension`: `ruvector` installed.
   - `memories.embedding`: `USER-DEFINED:ruvector`.
   - rows with non-null embeddings: `19`.
   - self-distance operator probe: `(embedding <=> embedding)` succeeded with `1.7872301e-07` inside `BEGIN READ ONLY` / `ROLLBACK`.
3. Running server log evidence after read-only recall probe:
   - recent logs contain `Hybrid retrieval failed: type "vector" does not exist, falling back to legacy recall` at `2026-05-01 08:39:19` and `2026-05-01 08:47:50`.
   - no `type "ruvector" does not exist` hits.
4. Code inspection:
   - `server.py` initializes `HybridRetriever(store.pool, store.vtype, embedder)` and tries `hybrid_retriever.search(...)`, then falls back to `query_agent.recall(...)` on exception.
   - `hybrid_retrieval.py` semantic query casts `$1::{self.vtype}`. The live failure proves the running server's effective `self.vtype` is still `vector` while DB type is `ruvector`.

Implication:

- Phase C/D must not proceed until the running server's effective vector type is `ruvector` and a binary hybrid-active probe passes.
- The current `fallback 0/199` benchmark metadata is insufficient as hybrid-active evidence.

## Pinned LOCOMO audit dependency

Upstream:

- Repo: `https://github.com/dial481/locomo-audit.git`
- Pinned commit: `9493fb4b4af4256ed17a18e8fd0b3cfdeec29539`
- Local temporary checkout used for pinning: `/tmp/locomo-audit-pin-9493fb4b4af4256ed17a18e8fd0b3cfdeec29539`

Pinned local artifact directory:

- `/home/zaddy/src/Memibrium/docs/eval/phase_b_artifacts/locomo_audit_9493fb4b4af4256ed17a18e8fd0b3cfdeec29539/`

Copied/pinned artifact hashes:

| SHA256 | Local artifact |
|---|---|
| `7345d1c23c5a182be7ccc35b184b405a136134f2e28323e41c6698322902737b` | `locomo_audit_9493fb4b4af4256ed17a18e8fd0b3cfdeec29539/answer_key.json` |
| `080338f63c229d36b2a177cf4c0720a47aedff830f8202c908c40412d76f5feb` | `locomo_audit_9493fb4b4af4256ed17a18e8fd0b3cfdeec29539/ap_v1_specific_wrong_probe.json` |
| `a83882eda3ff02fd04dace6edddd0ceed533a245fedb3069ffde02a9503c4e3a` | `locomo_audit_9493fb4b4af4256ed17a18e8fd0b3cfdeec29539/ap_v1_specific_wrong_scored_reference.json` |
| `3118fcc86f683d32e0b7294f65345ff8d612e74bd8d5da9af82627d12b82810a` | `locomo_audit_9493fb4b4af4256ed17a18e8fd0b3cfdeec29539/ap_v2_vague_topical_probe.json` |
| `3c32acbdcf667967a4e1f9f541b06566ae5e7361dc92f79f9043af7d068adc6b` | `locomo_audit_9493fb4b4af4256ed17a18e8fd0b3cfdeec29539/ap_v2_vague_topical_scored_reference.json` |
| `f298ef46263fada20688a1d672be37d4f488c6da3b19343eea55ae5c1b5fe55e` | `locomo_audit_9493fb4b4af4256ed17a18e8fd0b3cfdeec29539/errors.json` |

Upstream-only hashes also captured during pinning:

| SHA256 | Upstream artifact |
|---|---|
| `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4` | `data/locomo10.json` |
| `8d5bac4e8215cdb8d8568c97732c001ff823cbb0072f6e1783cc11183687805d` | `ap-baseline/score_ap.py` |
| `9f4654ea40d4e4701dc8248bc8f8ad34d635c819d63564fb1be58e03ab7ab64e` | `ap-baseline/AUDIT_REPORT.md` |
| `58174dbfda41534f49b86451a54257366d35e4ae7a0cffce1af04044a1d47821` | `results-audit/STATISTICAL_VALIDITY.md` |
| `3f980656ba6845f789ccc0f40fa822580c31be7c19f14b3888f28fbc57873e1a` | `methodology/discrepancies.md` |

Audit asset counts:

- `data/locomo10.json`: 10 conversations.
- `errors.json`: 156 audited correction/error records.
- `answer_key.json`: 1,540 category 1–4 Q+A pairs.
- AP baseline v1/v2 unscored result files: 1,540 generated intentionally wrong answers each.
- AP baseline scored references: v1 accuracy `0.10606060606060606`; v2 accuracy `0.6281385281385282`; categories present `1,2,3,4` only.

## Category-5/adversarial scoring basis decision

Pre-declared decision for future Phase D/E artifacts: **report both original and corrected/audit-aware scores when both can be computed**.

Rationale:

- Penfield's AP baseline and answer key are categories 1–4 only.
- Penfield's statistical validity notes state category 5/adversarial is excluded from published evaluations because most category-5 rows lack a ground-truth `answer` and contain only `adversarial_answer`.
- Therefore category-5/adversarial must never be collapsed into one ambiguous headline score.

Required future artifact fields:

- `score_original_locomo`
- `score_audit_corrected_or_audit_aware`
- `category5_scoring_basis`: one of `original`, `corrected`, `both`, `excluded_not_comparable`
- `audit_dependency_commit`
- `audit_asset_sha256`

## Judge-leniency probe scaffolding

Penfield Labs did publish a stable intentionally-wrong probe source in `ap-baseline/` at the pinned commit. Rather than inventing a new probe set, Phase B froze a deterministic 40-item subset for cheap repeated leniency checks.

Frozen subset:

- Path: `/home/zaddy/src/Memibrium/docs/eval/phase_b_artifacts/judge_leniency_probe_40q_2026-05-01.json`
- SHA256: `a2eacf982300cd4639c1fcf095d4fcc6c10afe2571c430d50639fbaa99ff0d6a`
- Items: 40
- Categories: 10 each from categories `1`, `2`, `3`, `4`
- Strategies: 20 `specific_wrong_v1`, 20 `vague_topical_v2`
- Category 5: not included because the upstream AP baseline excludes category 5.
- Selection method: deterministic first 5 items per category per strategy by conversation/question order.

Helper script:

- Path: `/home/zaddy/src/Memibrium/scripts/phase_b_extract_probe_subset.py`
- Purpose: regenerate the exact deterministic subset from pinned AP baseline files.
- It does not call judges, launch benchmarks, or touch runtime state.

## Phase B stop/go status

- Hybrid-active prerequisite: **FAILED** for the currently running server.
- Audit dependency pinning: complete.
- Judge-leniency probe scaffolding: complete.
- Benchmark launch authorization: not requested and not used.

Next safe action:

- Fix or restart/reconfigure only after explicit authorization so the running server uses `ruvector`, then rerun a binary hybrid-active probe. Do not start Phase C or any benchmark until that passes.
