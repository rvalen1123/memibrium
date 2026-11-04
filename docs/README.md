# docs/ — index

Last confirmed against: 6f10406 (2026-11-02)

The root [README](../README.md) is the short entry point. The files here hold the full text that used to live in it (relocated verbatim in the MED-242 docs pass), plus the evaluation records under `eval/`. Status values: `current` (describes `main` as it is) · `historical` (kept for the record; some content is known to be out of date and says so) · `archived` (in `archive/`).

<!-- index:start -->

## Repository-level documents

| File | Answers | Status |
|---|---|---|
| [`../README.md`](../README.md) | What Memibrium is, how to run it, the API at a glance, open caveats (MED-234; legacy Azure config under MED-233), where the docs are. | current |
| [`../AGENTS.md`](../AGENTS.md) | How a coding agent should work in this repo: repo map, exact commands, behaviour-changing conventions (CT lifecycle, additive migrations, idempotency key rules, embedding dimension), Always / Ask first / Never boundaries, done-gate. | current |
| [`../CLAUDE.md`](../CLAUDE.md) | `@AGENTS.md` — Claude Code reads the same instructions. | current |
| [`../DISTRIBUTION.md`](../DISTRIBUTION.md) | The skill-over-MCP distribution pattern, every install path (Claude Code, Copilot CLI, Cursor, any MCP client), plugin layout, MemSkill comparison. | current |
| [`../SECURITY.md`](../SECURITY.md) | Security policy. Still the GitHub template text (version table and reporting instructions are placeholders). | current |
| [`../LICENSE.md`](../LICENSE.md) | Business Source License 1.1 (change date 2030-03-23 → Apache 2.0) with the patent notice. | current |
| [`../plugins/memibrium/skills/crystallization-memory/SKILL.md`](../plugins/memibrium/skills/crystallization-memory/SKILL.md) | The governance skill agents load: 8 rules, tool quick-reference, anti-patterns, interaction examples. | current |
| [`../skills/crystallization-memory/SKILL.md`](../skills/crystallization-memory/SKILL.md) | Redirect stub saying the skill moved to `plugins/memibrium/`. Kept because the Dockerfile copies `skills/` and external installs may still point here. | historical |

## docs/

| File | Answers | Status |
|---|---|---|
| [`architecture.md`](architecture.md) | How the skill and MCP server layer, tiering = lifecycle state, what each component adds, the lifecycle flow (IngestAgent → ConsolidateAgent → QueryAgent), the CT distinction, design decisions, patent ↔ code map, repository layout. | current |
| [`api.md`](api.md) | Counts (27 routes, 18 manifest tools) and the tool → route map, the MCP endpoint `POST /mcp` (protocol versions, served, withheld and path-gated tools, argument validation), every route with one line each, GET-vs-POST filter behaviour on the list routes, the optional PDF dependency, the ingestion pipeline and 30-category taxonomy, idempotent retain semantics and the startup migration, example prompts. No per-route field tables; the `GET /mcp/tools` manifest has the input schemas. | current |
| [`operations.md`](operations.md) | The two supported run paths (local Python with `.env` exported; the RuVector compose stack: automatic model pull, `OLLAMA_MODELS` and `MEMIBRIUM_BIND` overrides, loopback-only ports, the 1536→768 upgrade note), which variables each LLM client reads (fixed `ollama` key), the full environment-variable list with defaults (incl. `CT_RANKER_*`), the CI test commands and a local pgvector container for the DB tests, network exposure, and a short "Legacy: Azure (subscription closed, not maintained)" section. | current |
| [`benchmarks.md`](benchmarks.md) | The April-2026 LOCOMO benchmark narrative: reconstructed baseline, the corrupted-database correction, the superseded failure-mode table, and the two practical takeaways. The numbers are as of April 2026 and flagged inline; later evidence is in `eval/`. | historical |
| [`roadmap.md`](roadmap.md) | Phase roadmap (what shipped, what is planned) and the April-2026 competitive landscape table. | current |
| [`eval/README.md`](eval/README.md) | Index of all 122 evaluation records grouped by study (LongMemEval, LoCoMo, phase_b_artifacts), newest first. | current |
| [`archive/README.md`](archive/README.md) | Archive policy and the log of what was moved there and why. | current |

<!-- index:end -->

## Keeping this index honest

- When you add a file under `docs/`, add a row here. When you add a record under `docs/eval/`, add a row to `eval/README.md` instead.
- Update the `Last confirmed against` line (short SHA of `origin/main`, date) whenever you re-verify the rows against the code.
- A file whose contents are known to be stale but still worth reading gets `historical`, not deletion. Only a file that a newer file or the code explicitly replaces, or an exact duplicate, moves to `archive/` (see `archive/README.md`).
