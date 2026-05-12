# LOCOMO `bb9ba5b^` Boundary-Test Comparison (2026-04-30)

## Verdict

**FAILED REPRODUCTION**

Threshold driver: score outside ±5pp (61.81% vs 68.09%, delta -6.28pp)

## Locked reference

- Reference artifact: `docs/eval/results/locomo_conv26_query_expansion_2026-04-24.json`
- Reference score: `68.09%`
- Reference fallback: `0/199`
- Reference latency: `8026ms` (observational only)

## Boundary run

- Boundary under test: `bb9ba5b^`
- Run HEAD: `bfeb90fc0465fdc24203d216c97cd1bc7226c0a4`
- `git rev-parse bb9ba5b^`: `bfeb90fc0465fdc24203d216c97cd1bc7226c0a4`
- Worktree: `/home/zaddy/src/Memibrium-worktrees/locomo-bb9ba5b-parent-2026-04-30`
- Command: `python3 benchmark_scripts/locomo_bench_v2.py --cleaned --normalize-dates --max-convs 1`
- Query expansion: `USE_QUERY_EXPANSION=1` (bfeb90f has no `--query-expansion` CLI flag)

## Result summary

- Score: `61.81%`
- Delta vs reference: `-6.28pp`
- Query-expansion fallback: `0/199`
- Avg query latency: `4229ms` (observational only)
- Total questions: `199`

## Category scores

- `cat-temporal`: `87.84%`
- `cat-multi-hop`: `34.62%`
- `cat-single-hop`: `70.31%`
- `cat-unanswerable`: `75.71%`
- `cat-5`: `22.34%`


## Locked decision rules

- Strong: score within ±2pp of `68.09` and fallback `<=2/199`
- Partial: score within ±5pp of `68.09` and fallback `<=5/199`
- Failed: score outside ±5pp or fallback `>5/199`

## Interpretation

This is a failed reproduction under the locked rules because the score is outside the ±5pp gate while fallback remained at zero.

Because `bb9ba5b^` resolves to `bfeb90f`, this run used the same commit that produced the 04-24 reference artifact. Therefore, failure does not support attributing the gap solely to post-`bfeb90f` Memibrium code drift. It points to environment, DB substrate, dependency versions, benchmark data state, or provider-side drift as necessary next suspects.

## Inference-stack identity

- Endpoint: `https://sector-7.services.ai.azure.com/models`
- Answer model: `gpt-4.1-mini`
- Judge model: `gpt-4.1-mini`
- Query-expansion model: `gpt-4.1-mini`
- Azure chat deployment: `gpt-4.1-mini`
- Azure OpenAI deployment: `gpt-4.1-mini`
- CHAT_MODEL: `gpt-4.1-mini`
- OPENAI_BASE_URL: `<unset>`
- AZURE_OPENAI_ENDPOINT: `<unset>`
- Temperature: `0`

## Paired overlap vs reference

- Common questions: `199`
- Reference-only: `0`
- Current-only: `0`
- Rescued vs reference: `14`
- Harmed vs reference: `23`
- Unchanged correct: `93`
- Unchanged wrong: `35`
- Same partial: `22`
- Partial changed: `12`

## LOCOMO cleanup

- Pre-run LOCOMO count: `0`
- Post-run LOCOMO count before cleanup: `49`
- Post-cleanup LOCOMO count: `0`.
