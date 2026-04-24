# Prereg Calibration Record

| Date | Intervention | Metric | Predicted | Range | Actual | In range? |
|---|---|---|---|---|---|---|
| 2026-04-23 | Date normalization | temporal | 70.9% | 68.4–73.6 | 70.87% | yes |
| 2026-04-24 | Query expansion | 4-cat overall | 79% | 78–80 | 77.48% | no, -0.52pp |

## Calibration notes
- Hit ratio: 1/2
- Pattern: 1 below-range miss; 1 dead-center hit
- Watch for: systematic optimism if a third miss lands below
- Watch for: canary→full-run extrapolation reliability
  - query-expansion miss came largely from open-domain not generalizing from conv-26

## Lessons accumulated
- Aggregate directional predictions are more stable than per-category extrapolations
- Single-conversation canaries are unreliable for high-weight category extrapolation
- Pre-pinned interpretation tables prevent post-hoc rationalization
