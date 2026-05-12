# LOCKED PLAN: Memibrium LOCOMO Benchmark — Date Normalization Intervention

## Definition of done

Session is complete when ALL FOUR artifacts exist:
1. Fully-cleaned dataset on disk (`/tmp/locomo10_fully_cleaned.json`)
2. Two benchmark numbers: clean baseline AND clean+normalization
3. Measured fix-rate (computed via pre-pinned formula)
4. One-paragraph entry in skill or README documenting both numbers and fix-rate

Numbers without documentation = INCOMPLETE session. Do not shortcut step 4.

## Step 1: Diagnose and clear database (15 min)

**Use surgical delete, not truncate:**
```bash
docker stop memibrium-server
docker exec -i memibrium-ruvector-db psql -U memory -d memory -c "DELETE FROM memories WHERE domain LIKE 'locomo-%';"
docker start memibrium-server
```

**Verify empty state via SQL, not dashboard:**
```bash
docker exec -i memibrium-ruvector-db psql -U memory -d memory -c "SELECT count(*) FROM memories;"
```
Must return 0 before proceeding.

## Step 2: Full label cleanup on 107 retrieval-missing failures (2 hours max)

- Use rubric in `/tmp/failure_mode_rubric.md`
- Classify all 107 retrieval-missing-bucket failures
- Remove confirmed gold-label errors from eval dataset
- Save as `/tmp/locomo10_fully_cleaned.json`
- **Stop criterion:** All 107 classified OR 2 hours elapsed
- **Out of scope:** Do NOT expand to other buckets or all 200 failures

## Step 3: Re-establish clean baseline WITHOUT normalization (~45 min)

- Run condition 4 on fully-cleaned data
- Command: `cd /tmp && python locomo_bench.py --data /tmp/locomo10_fully_cleaned.json`
- Expected: ~45–50% (higher than 37.7% due to removed label noise)
- Save result as `/tmp/locomo_results_baseline.json`

## HARD CHECKPOINT: Re-clear memories before step 4

**MANDATORY:** Before proceeding to step 4, verify database is empty:
```bash
docker exec -i memibrium-ruvector-db psql -U memory -d memory -c "SELECT count(*) FROM memories;"
```
If count > 0, re-run the delete from step 1. Do NOT skip this.

## Step 4: Run with normalization (~45 min)

- Clear memories again (see checkpoint above)
- Run with `--normalize-dates`
- Command: `cd /tmp && python locomo_bench.py --data /tmp/locomo10_fully_cleaned.json --normalize-dates`
- Save result as `/tmp/locomo_results_normalized.json`

## Step 5: Compute measured fix-rate and document

**Formula (pre-pinned):**
```
measured_fix_rate = (normalization_score − baseline_score) / 33.6
```

Where 33.6 = absolute pp of relative-date failures (54% of 62.3% failure rate).

**Contingency for small delta:**
If baseline-to-normalization delta is <3 percentage points, also run a per-question correctness diff:
```bash
cd /tmp && python3 -c "
import json
with open('locomo_results_baseline.json') as f: b = json.load(f)
with open('locomo_results_normalized.json') as f: n = json.load(f)
# Extract per-question correctness and diff
"
```
This converts a potentially uninterpretable headline into actionable per-question signal.

**Documentation target:** One paragraph in skill or README with:
- Clean baseline score
- Normalization score
- Measured fix-rate
- Comparison to assumed 40%
- If delta <3 pp: note that per-question diff was run

## Pre-registered prediction

- Predicted condition-4 on cleaned data with normalization: **45–55%**
- Assumed fix-rate: **40%**
- Post-run: compare measured fix-rate to assumed 40%

## Files to have open

- `/tmp/benchmark_prediction.md` — prediction and formula
- `/tmp/failure_mode_rubric.md` — classification rubric
- `/tmp/locomo_bench.py` — benchmark script
