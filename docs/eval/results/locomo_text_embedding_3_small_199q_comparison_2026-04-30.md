# LOCOMO text-embedding-3-small reproduction comparison — 2026-04-30

## Verdict

**Partial reproduction per locked preregistered rules.**

The strict verdict is partial, not strong. However, the diagnostic signal is stronger than the label alone: forcing Azure `text-embedding-3-small` largely recovered the 04-24 retrieval shape and score, supporting embedding substrate drift as the dominant cause of the regression.

## Result summary

| Metric | 04-24 reference | 04-30 bfeb90f boundary fail | This run (`text-embedding-3-small`) |
|---|---:|---:|---:|
| Score | 68.09% | 61.81% | 66.08% |
| Query-expansion fallback | 0/199 | 0/199 | 0/199 |
| Mean `n_memories` | 11.65 | 14.70 | 13.16 |
| `n_memories=15` saturation | 31/199 = 15.6% | 170/199 = 85.4% | 62/199 = 31.16% |

Saturation trajectory: **15.6% → 85.4% → 31.16%**.

This run reduced cap saturation by **54.24pp** versus the failed bfeb90f boundary reproduction and moved most of the way back toward the 04-24 reference shape.

## Locked decision rules

### Strong reproduction checks

| Criterion | Strong threshold | Result | Pass? | Distance from strong |
|---|---:|---:|---:|---:|
| Score | 66.09-70.09% | 66.08% | no | 0.01pp below lower bound |
| Fallback | <=2/199 | 0/199 | yes | — |
| Mean `n_memories` | 10.15-13.15 | 13.16 | no | 0.01 above upper bound |
| `n=15` saturation | 5.6-25.6% | 31.16% | no | 5.56pp above upper bound |

Two strong criteria missed by approximately 0.01 at displayed precision; saturation is the only strong miss with a meaningful margin.

### Partial reproduction checks

All partial checks passed:

- Score inside 63.09-73.09%: 66.08%
- Fallback <=5/199: 0/199
- Mean `n_memories` <=13.20: 13.16
- `n=15` saturation <=55.4%: 31.16%
- Per-question `n_memories` present for all 199 questions
- Effective embedding stack matched `text-embedding-3-small` with 1536-dim output

No failed-reproduction trigger fired.

## `n_memories` distribution

This run histogram:

```text
0: 2
10: 4
11: 25
12: 39
13: 32
14: 35
15: 62
```

Compared with the failed bfeb90f boundary run (`170/199` at cap), this is a qualitatively different retrieval shape: centered around 12-13 with a tail at the cap, not a degenerate cap-saturated distribution. This mechanistically supports the embedding-substrate hypothesis.

## Effective embedding stack

- Provider/client: `AzureOpenAI`
- Endpoint: `https://sector-7.openai.azure.com/`
- Deployment: `text-embedding-3-small`
- Dimensions argument: `1536`
- Observed output dimension: `1536`

## Caveats

1. At exact `bfeb90f`, `server.py` does not appear to read `ENABLE_BACKGROUND_SCORING`, `ENABLE_CONTRADICTION_DETECTION`, or `ENABLE_HIERARCHY_PROCESSING`. These were false in container env, but not functionally honored by that code.
2. Logs showed repeated background-path 404s to `https://sector-7.services.ai.azure.com/models/models/chat/completions`, indicating duplicated `/models` endpoint construction outside the main benchmark path.
3. Logs showed `Hybrid retrieval failed: type "vector" does not exist, falling back to legacy recall`; the benchmark therefore reflects the graceful legacy fallback path under the current ruvector schema.

These caveats do not negate the embedding result, but they show the historical substrate was not fully reproduced by changing only the embedding deployment.

## Metadata

- Repo HEAD: `6bf9fc9f4e328b5f18124afe297a7b147937c1dd`
- Run worktree HEAD: `bfeb90fc0465fdc24203d216c97cd1bc7226c0a4`
- Server image SHA: `sha256:3fe64e84a34850fdf40318f8af5b4638d23e14640c3edf1e21f9c998ff024c84`
- DB image SHA: `sha256:d9f86747f3af63c354bc40b1cc4368575fcdbf16ad7582cb82ef20f0d8907dac`
- Ollama image SHA: `sha256:d3d553bdfbcc7f55dd5ddf42c4cbe3a927aa9bb1802710d35e94656ca5aea02b`
- Python/packages: Python 3.11.15; openai 2.32.0; httpx 0.28.1; asyncpg 0.31.0; pydantic 2.13.1; starlette 0.52.1; uvicorn 0.44.0
- DB extensions: plpgsql 1.0; ruvector 0.3.0
- Embedding column: `ruvector(1536)`

Source hashes:

- `/tmp/locomo10_cleaned.json`: `1b304c7c3d98ff9cef5efd02100a4dfa93fc9ee3babaceca752df9f9aa90b42d`
- `/tmp/locomo/data/locomo10.json`: `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`
- bfeb90f benchmark script: `3fe3b7bdd597bbbe17e9ee1bc819496e448442cd6535edcf348f8bf7f7d78a10`
- bfeb90f `server.py`: `df37cef5af863ba29e81077434635cae1da66e7f9b19c5b070baade0cd69822d`
- conv-26 question list: `07717c689e2e5a228b63d46f3b712a92185a8fa32aed524c4f3e7f9714ba556f`

Post-ingest / pre-cleanup counts:

- `memories`: 68 total, including 49 `locomo-%`
- `entities`: 3108
- `entity_relationships`: 231385
- `temporal_expressions`: 49
- `memory_snapshots`: 0

Cleanup:

- Deleted 49 `locomo-%` memories and 49 linked temporal expressions.
- Verified post-cleanup `locomo-%` memory count: 0.

## Interpretation

Per locked protocol, this is a partial reproduction. Substantively, it is strong evidence that embedding substrate drift was the dominant regression cause. The score recovered from 61.81% to 66.08%, fallback stayed at 0/199, and the retrieval-count distribution shifted from cap-saturated to near-reference shape.

The remaining gap (score 2.01pp below reference; saturation ~15.6pp above reference) likely reflects residual substrate differences such as image/dependency/ruvector behavior, model snapshot drift, endpoint differences, or non-determinism in the 04-24 reference.
