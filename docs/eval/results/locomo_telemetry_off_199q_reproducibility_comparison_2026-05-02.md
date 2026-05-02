# LOCOMO telemetry-off 199Q reproducibility attempt — 2026-05-02

## Verdict

`repro_blocked_scope_mismatch_aborted`

Preflight passed, but the benchmark launch was aborted after detecting a command/scope mismatch before a valid 199Q artifact could be produced.

Phase C remains blocked.

## What happened

The Step 5i preregistration locked a telemetry-off reproducibility run intended to evaluate exactly the canonical conv-26 199-question slice. The preflight gates passed and the launch began with telemetry disabled.

The benchmark log then showed:

```text
Conversations to process: 10
Total questions: 1986 (1986 evaluated, skipping cats set())
[1/10] Conv conv-26: Caroline & Melanie
```

This means the current `--max-convs 26` command semantics were not a conv-26-only selector in this runtime. They selected all 10 dataset conversations, while the first conversation happened to be `conv-26`. That violates the preregistered expected evaluated question count of `199` and would not produce a comparable 199Q artifact.

The process was killed after the log reached 60/199 questions within the first conversation. No `/tmp/locomo_results_query_expansion_raw.json` result artifact was produced.

## Preserved evidence

- Prelaunch artifact: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_telemetry_off_199q_reproducibility_prelaunch_2026-05-02.json`
- Partial aborted log: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_telemetry_off_199q_reproducibility_partial_aborted_2026-05-02.log`
- Labels: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_telemetry_off_199q_reproducibility_labels_2026-05-02.json`
- Cleanup proof: `/home/zaddy/src/Memibrium/docs/eval/results/locomo_telemetry_off_199q_reproducibility_cleanup_2026-05-02.json`

Partial log SHA256: `66fe9a85dd3c657ab87dc39432b5d5010d20000acbeebda4e51657b6956f2bfc`

## Hygiene and cleanup

The aborted run had already ingested LOCOMO rows. Mandatory cleanup was executed immediately after abort.

Final post-cleanup verification:

```text
locomo_count|0
temporal_expressions|0
memory_snapshots|0
user_feedback|0
contradictions|0
memory_edges|0
```

Health after cleanup:

```text
{"status":"ok","engine":"memibrium"}
```

## Interpretation

This attempt is not a low-context reproduction, not a high-context reproduction, and not a third-regime observation. It is a blocked execution caused by launch-scope mismatch.

Do not compare the partial running score, partial context shape, or partial log against `f2466c9` or `91fede6`. The run did not complete and did not satisfy the preregistered 199Q scope.

## Next valid step

Preregister a corrected conv-26-only launch protocol. The corrected protocol must prove before launch that it will evaluate exactly the intended 199 questions and must not rely on `--max-convs 26` as if it were a sample-id selector.

Potential correction paths to preregister:

1. Build a temporary input JSON containing only the `sample_id == "conv-26"` conversation, without mutating source code.
2. Add or use an existing explicit sample-id selector only under a separate preregistered source/mutation window.
3. If using dataset ordering, preflight must prove the selected slice length and expected question count from the exact input file before launch.

Do not resume from the partial output. Do not proceed to Phase C.
