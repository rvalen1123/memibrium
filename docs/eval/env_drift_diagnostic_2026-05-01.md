# LOCOMO env drift diagnostic — 2026-05-01

Repo: `/home/zaddy/src/Memibrium`
Branch: `query-expansion`
Current checked commit before this document: `25b0328`
Mode: read-only diagnostic; no runtime/container/DB mutation; no benchmark launch.

## Purpose

Document why the live post-rebuild substrate differs from the canonical LOCOMO comparison substrate.

The current live server is hybrid-active, but the substrate baseline was blocked because the server advertises:

- `AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-large-1`
- `AZURE_CHAT_DEPLOYMENT=grok-4-20-non-reasoning-1`

The canonical comparable baseline requires:

- `AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-small`
- `AZURE_CHAT_DEPLOYMENT=gpt-4.1-mini`

## Read-only checks performed

### Git state

```text
query-expansion
25b0328
```

Working tree was clean before this diagnostic document was created.

### Current local `.env`

`.env` is ignored by git:

```text
.gitignore:15:.env	.env
```

File metadata:

```text
.env mtime=2026-04-23 03:19:27.930031773 -0500 size=1115
.env.example mtime=2026-04-13 10:59:07.562472947 -0500 size=1463
```

Sanitized relevant `.env` contents:

```text
OPENAI_BASE_URL=https://openrouter.ai/api/v1
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_BASE_URL=http://ollama:11434/v1
CHAT_MODEL=openai/gpt-4.1-mini
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

Interpretation: the immediate source of the post-rebuild drift is the ignored local `.env`. The rebuild/restart in the mutation window made the running container pick up those values.

### Compose behavior

`docker-compose.ruvector.yml` passes Azure chat/embedding values through from `.env`:

```text
AZURE_EMBEDDING_ENDPOINT: ${AZURE_EMBEDDING_ENDPOINT:-}
AZURE_EMBEDDING_DEPLOYMENT: ${AZURE_EMBEDDING_DEPLOYMENT:-}
AZURE_EMBEDDING_API_KEY: ${AZURE_EMBEDDING_API_KEY:-${AZURE_OPENAI_API_KEY:-}}
AZURE_CHAT_ENDPOINT: ${AZURE_CHAT_ENDPOINT:-}
AZURE_CHAT_DEPLOYMENT: ${AZURE_CHAT_DEPLOYMENT:-}
AZURE_CHAT_API_KEY: ${AZURE_CHAT_API_KEY:-${AZURE_OPENAI_API_KEY:-}}
CHAT_MODEL: gemma4:e4b
```

`CHAT_MODEL` from `.env` does not override the server container because compose hard-codes `CHAT_MODEL: gemma4:e4b`; however, `ChatClient` chooses Azure chat whenever `AZURE_CHAT_ENDPOINT` and `AZURE_CHAT_API_KEY` are set, and then uses `AZURE_CHAT_DEPLOYMENT`. Therefore the effective server chat model is `grok-4-20-non-reasoning-1`, not `CHAT_MODEL`.

`EmbedClient` chooses Azure embeddings whenever `AZURE_EMBEDDING_ENDPOINT` and `AZURE_EMBEDDING_API_KEY` are set, and then uses `AZURE_EMBEDDING_DEPLOYMENT`. Therefore the effective server embedding deployment is `text-embedding-3-large-1`, not local `EMBEDDING_MODEL=nomic-embed-text`.

### Current live server env

Read-only container env check:

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
USE_RUVECTOR=true
```

This matches `.env` plus compose precedence.

### Existing archaeology context

Prior read-only archaeology already recorded the same current drift before the hybrid-active mutation:

- `docs/eval/locomo_runtime_config_archaeology_2026-04-30.md` lines 118-130 recorded current server env with `AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-large-1` and `AZURE_CHAT_DEPLOYMENT=grok-4-20-non-reasoning-1`.
- The same document recorded `.env` metadata and noted `.env` is untracked, so exact historical values cannot be recovered from git alone.
- `docs/eval/locomo_environment_substrate_archaeology_2026-04-30.md` ranked embedding substrate drift as the highest-probability culprit.

### Git history signal

Tracked source history outside result artifacts shows:

```text
STRING=grok-4-20-non-reasoning-1
b27565f 2026-05-01 docs: record LOCOMO hybrid mutation result
48d4e18 2026-04-30 docs: record LOCOMO runtime config archaeology

STRING=text-embedding-3-large-1
b27565f 2026-05-01 docs: record LOCOMO hybrid mutation result
6bf9fc9 2026-04-30 docs: preregister LOCOMO text embedding small reproduction
48d4e18 2026-04-30 docs: record LOCOMO runtime config archaeology
5535a58 2026-04-30 docs: archaeology report substrate drift n_memories regression
```

No tracked compose/source default was found that sets Grok or `text-embedding-3-large-1`; these values are environment/runtime facts, not tracked default-code facts.

## Findings

1. The current live substrate drift is explained by ignored local `.env` values consumed by compose at container recreation time.
2. Compose passes `AZURE_CHAT_*` and `AZURE_EMBEDDING_*` through to the server container; these take precedence in server code over `CHAT_MODEL` and `EMBEDDING_MODEL`.
3. The drift predates the 2026-05-01 hybrid-active rebuild: it was already documented in 2026-04-30 archaeology.
4. The exact origin of the ignored `.env` change is not recoverable from git because `.env` is intentionally untracked. File mtime/ctime points to 2026-04-23, but that does not prove the values active during any specific benchmark run.
5. The current default in the local runtime should not be treated as the canonical LOCOMO comparison substrate.

## Methodological implication

The post-rebuild live server is suitable for proving that hybrid retrieval can be active, but not suitable for the comparable canonical substrate baseline without env alignment.

Running LOCOMO now would couple at least three changes:

1. legacy recall fallback -> hybrid retrieval;
2. `text-embedding-3-small` -> `text-embedding-3-large-1`;
3. `gpt-4.1-mini` -> `grok-4-20-non-reasoning-1`.

That would violate the coupled-change attribution discipline used throughout the LOCOMO investigation.

## Recommended next action

Proceed with Option 1:

1. Pre-register a separate atomic env-alignment mutation.
2. Change only the local runtime env needed to restore canonical server substrate.
3. Restart/recreate only the server container.
4. Re-probe hybrid-active status plus canonical embedding/chat identity.
5. If and only if the gate passes, run the existing canonical hybrid-active substrate baseline preregistration.
