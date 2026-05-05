# LOCOMO query-expansion fallback diagnosis — conv-26 199Q

Date: 2026-04-30
Branch/commit inspected: `query-expansion` at `5f79cf3821b983d35757bebb30f5e45c3cf58084`
Artifact inspected: `docs/eval/results/locomo_conv26_query_expansion_199q_2026-04-29.json`
Mode: read-only diagnosis; no code changes.

## Question

Why did query expansion fall back on `57/199` LOCOMO conv-26 questions (`28.64%`)?

Candidate causes considered:

1. Query expansion produces no usable expansions.
2. Retrieval returns empty / low-confidence and triggers fallback.
3. Fallback decision logic has a bug or overly conservative threshold.

Follow-up questions added after first-pass diagnosis:

4. Why do fallback rows score higher than non-fallback rows?
5. Are some apparent successful expansions silently corrupted by wrong-shaped JSON?

## Key finding

The recorded fallback counter is the `expand_query.fail_count`, incremented only when `expand_query()` catches an exception while generating/parsing expansions.

It is not a retrieval-confidence fallback and it is not triggered by low/empty recall.

Code path inspected in `benchmark_scripts/locomo_bench_v2.py`:

- `expand_query(question)` calls `llm_call(...)`, then `json.loads(resp.strip())`.
- On any exception, it increments `expand_query.fail_count` and returns `[question]`.
- `run_benchmark()` saves `expand_query.fail_count` as `expand_query_fallback_count`.

Therefore the 28.64% fallback means: the expansion LLM call or strict JSON parsing failed on 57 questions, so those questions used the original query only.

## Artifact observations

The artifact does not preserve per-question fallback flags. However, for the non-append baseline, fallback can be reconstructed from `n_memories`:

- successful expansion normally runs original + up to 3 reformulations and can fill the answer context to 15 memories;
- expansion fallback runs only the original query and is capped by `RECALL_TOP_K=10`.

Proxy `n_memories <= 10` exactly matches the aggregate fallback count:

- aggregate `expand_query_fallback_count`: `57`
- rows with `n_memories <= 10`: `57`

This proxy should not be reused for append/gated artifacts, because append modes can have >10 memories even when expansion falls back.

## Fallback paradox

Fallback rows are not lower-performing rows in this artifact. They score higher than rows where expansion apparently succeeded:

- fallback proxy (`n_memories <= 10`): `30.0/57` = `52.63%`
- non-fallback rows (`n_memories > 10`): `64.5/142` = `45.42%`
- headline gap: fallback is `+7.21pp`

This changes the interpretation. If fallback is acting like an original-query-only arm, then making expansion succeed more often is not automatically an accuracy fix. It may lower absolute accuracy if expansion is adding retrieval noise.

### Per-category check

Per-category fallback-vs-non-fallback accuracy:

| Category | Fallback | Non-fallback | Delta |
|---|---:|---:|---:|
| adversarial | `4.0/15` = `26.7%` | `2.5/32` = `7.8%` | `+18.9pp` |
| multi-hop | `2.0/2` = `100.0%` | `6.0/11` = `54.5%` | `+45.5pp` |
| single-hop | `4.5/11` = `40.9%` | `9.5/21` = `45.2%` | `-4.3pp` |
| temporal | `2.0/3` = `66.7%` | `20.5/34` = `60.3%` | `+6.4pp` |
| unanswerable | `17.5/26` = `67.3%` | `26.0/44` = `59.1%` | `+8.2pp` |

Category mix alone does not explain the paradox. Applying non-fallback category rates to the fallback category distribution would predict only `24.41/57` = `42.83%`, below both observed fallback accuracy and observed non-fallback accuracy. Conversely, applying fallback category rates to the non-fallback mix would predict `80.41/142` = `56.62%`.

Caveats:

- Some fallback category cells are tiny (`multi-hop n=2`, `temporal n=3`), so the large within-category deltas are unstable.
- This is still observational, not a causal same-question no-expansion vs expansion ablation.
- There may be within-category selection effects: questions that trigger answer/apology behavior may be easier original-query cases or easier abstention/adversarial cases.

Current interpretation: the paradox is real enough to block a simple "fix prompt-following, then expect accuracy to rise" plan. Query expansion may be net-harming some LOCOMO slices, especially by adding noisy context. The next measurement should explicitly compare original-query-only vs expansion, or pre-register a conditional/restricted expansion hypothesis rather than treating expansion success rate as automatically beneficial.

## Fallback distribution

Fallback proxy (`n_memories <= 10`):

- n = 57
- score = `30.0/57` = `52.63%`
- score distribution: 29 full, 2 partial, 26 zero
- latency avg/p50/p95: `2024ms / 1707ms / 2842ms`

Non-fallback rows:

- n = 142
- score = `64.5/142` = `45.42%`
- score distribution: 56 full, 17 partial, 69 zero
- latency avg/p50/p95: `3791ms / 2624ms / 11954ms`

Fallback share by category:

| Category | Fallback / total | Rate |
|---|---:|---:|
| adversarial | 15 / 47 | 31.9% |
| multi-hop | 2 / 13 | 15.4% |
| single-hop | 11 / 32 | 34.4% |
| temporal | 3 / 37 | 8.1% |
| unanswerable | 26 / 70 | 37.1% |

## Live raw-output probes

The live probes reran only the query-expansion LLM prompt; they did not call retrieval, answer, judge, or mutate DB state.

Using the current prompt:

> Generate 3 diverse reformulations of the question focused on different aspects (entities, time, relationships). Return a JSON array of 3 strings only.

First probe:

- first 20 reconstructed fallback questions: 18/20 produced non-JSON answer/helpfulness prose, not a JSON array
- first 10 reconstructed non-fallback questions: 0/10 failed JSON parsing

Representative bad outputs:

- Q: `What career path has Caroline decided to persue?`
  - Raw: `I'm sorry, but I don't have any information about a person named Caroline or her career decisions...`
- Q: `What do Melanie's kids like?`
  - Raw: `I'm sorry, but I don't have any information about Melanie's kids or their preferences...`
- Q: `Would Melanie be considered an ally to the transgender community?`
  - Raw answer/prose about likely public figure Melanie Martinez, not a rewrite JSON array.

Representative good output:

- Q: `When did Caroline go to the LGBTQ support group?`
  - Raw: valid JSON array of rewrite strings.

### Successful-row shape probe

A second live read-only probe reran the same expansion prompt across all 142 reconstructed non-fallback rows (`n_memories > 10`) and classified raw output shapes.

Result:

- valid list of strings: `137/142` (`96.48%`)
- JSON parse error / answer prose: `4/142` (`2.82%`)
- LLM transport/runtime error after retries: `1/142` (`0.70%`)
- parsed-but-wrong-shaped JSON objects/strings/lists with non-strings: `0/142`

By category:

| Category | Valid list | JSON error | LLM error |
|---|---:|---:|---:|
| adversarial | 31 | 0 | 1 |
| multi-hop | 10 | 1 | 0 |
| single-hop | 20 | 1 | 0 |
| temporal | 34 | 0 | 0 |
| unanswerable | 42 | 2 | 0 |

Representative non-fallback rows that now produced answer/prose rather than JSON:

- multi-hop, score 0.0: `Would Melanie be considered a member of the LGBTQ community?`
- single-hop, score 0.0: `How many children does Melanie have?`
- unanswerable, score 1.0: `How does Melanie prioritize self-care?`
- unanswerable, score 0.0: `What kind of painting did Caroline share with Melanie on October 13, 2023?`

Interpretation:

- The suspected hidden parser-shape corruption was not observed in this live sample: no dict outputs, bare JSON strings, non-string list elements, or empty lists appeared among the 142 non-fallback rows.
- The true instability rate is still slightly higher than the artifact's `57/199`, because fresh calls on previously successful rows produced `4` parse failures plus `1` LLM error. That is likely model nondeterminism / endpoint instability, not silent wrong-shape acceptance in the saved artifact.
- Parser validation remains unconditionally correct, but the urgent hidden-corruption concern is lower priority than the fallback paradox and same-question expansion harm question.

Raw probe output was saved outside the repo at `/tmp/locomo_success_expansion_shape_probe_2026-04-30.json` to avoid committing volatile LLM-response artifacts.

## Root-cause hypothesis

Primary root cause of the recorded fallback count: the query-expansion prompt is too weakly framed as a transformation-only task, so the chat model sometimes treats the user question as an ordinary QA request. When it lacks context, it returns apology/helpfulness prose; for public-name-like prompts, it may answer from world knowledge. `expand_query()` then strict-parses `resp.strip()` as JSON and falls back.

This points to candidate cause #1: query expansion produces no usable expansions because the LLM output is not valid JSON / not an array.

It does not support candidate cause #2. Retrieval is not involved in incrementing `expand_query_fallback_count`.

It does not support candidate cause #3 as originally phrased. There is no retrieval threshold decision causing the count. There is, however, a strict parser/contract fragility: `json.loads(resp.strip())` treats Markdown fences, intro text, objects, and answer-prose as hard failures. The code also under-validates parsed output shape.

## Additional code-level observations

`expand_query()` accepts some invalid shapes silently:

- JSON object `{"queries": [...]}` would iterate dict keys and return `['question', 'queries']` without incrementing fallback.
- JSON string `"a"` would return `['question', 'a']` without incrementing fallback.

The successful-row raw probe did not observe this in 142 live calls, but the parser should still validate `isinstance(paraphrases, list)` and string contents explicitly before accepting the output.

The result artifact lacks per-question expansion diagnostics, so future runs cannot directly inspect raw expansion outputs or per-row fallback flags. Current per-row inference from `n_memories` works only for this baseline artifact.

## Revised recommended next step

Do not implement a prompt-following fix yet if the goal is LOCOMO accuracy. The fallback paradox has to be resolved first.

Recommended ordering:

1. Pre-register and run an original-query-only vs query-expansion comparison on the same conv-26 slice, or build a paired replay audit if an original-query-only artifact already exists for the same substrate/model.
2. Keep parser validation as an independent code-hygiene fix: explicitly require a non-empty `list[str]`; reject dicts, bare strings, non-string elements, and empty lists; keep fail-open behavior and count fallbacks.
3. Add diagnosis-grade instrumentation around query expansion before any new full measurement:
   - per-question `query_expansion_fallback: bool`
   - `query_expansion_error_type`
   - `query_expansion_raw_preview` or a redacted/truncated preview when parsing fails
   - `query_expansion_count`
   - optionally the accepted expansion strings in a debug artifact
4. Only after the expansion-vs-original harm question is answered should the prompt be strengthened or expansion policy changed.

Decision boundary for the fix:

- If expansion hurts net or within key categories, disable it or restrict it conditionally, e.g. only when original-query recall confidence is low.
- If expansion is neutral and fallback is mostly selection bias, fix parser/prompt for hygiene but pre-register a small or possibly negative accuracy delta.
- If expansion helps when it works on a same-question comparison, proceed with the original instrument-and-fix plan.

Any LOCOMO accuracy run after changing expansion behavior should be pre-registered, because it changes the retrieval condition. A read-only diagnostic phase did not need pre-registration; a fix-impact measurement does.
