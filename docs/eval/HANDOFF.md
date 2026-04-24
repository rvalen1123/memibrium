# NEXT SESSION: Failure-mode analysis on temporal failures

## BASELINE
- Temporal: 61.4% (n=321) on healthy DB
- Overall: 62.0% J-Score
- Commit hash (substrate): 3cc1c221c6e51f39d68eafd068bd2faceb782f3b
- Data: docs/eval/locomo_results.json
- Full log: docs/eval/baseline_run.log

## FAILURE POOL EXTRACTION
From `docs/eval/locomo_results.json`:
```python
import json
with open('docs/eval/locomo_results.json') as f:
    results = json.load(f)
temporal_failures = [r for r in results['results_log'] if r['cat'] == 'cat-temporal' and r['score'] == 0]
# N = 124 failures
```

## PENDING PRE-WORK (15 min)
- Per-conversation spread check on temporal
- Pin commit hash in results metadata
- Optional: tighten classifier rubric to require evidence quotes

## ANALYSIS
- Sample N=50 from 124 temporal failures (expand to 75 if distribution diverges from old)
- Same 4-bucket rubric: retrieval-missing, relative-date, composition, gold-label
- Log seed, document method

## AFTER ANALYSIS
- Re-derive prediction with new breakdown, explicit fix-rate math
- Then run normalization

## DO NOT
- Run normalization until failure-mode analysis + re-derived prediction complete

## NOTE ON LOCKED PLAN
Protocol at docs/eval/locked_plan.md is partially stale now:
- Step 3's expected range (~45-50%) is obsolete given 61.4% reality
- Read this handoff first, not the locked plan
- The plan's rubric, sampling method, and fix-rate framework are still valid
