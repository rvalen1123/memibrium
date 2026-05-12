# LOCOMO Failure-Mode Classification Rubric

Used for eyeball-corrected failure-mode analysis on temporal (condition 4) failures.

## Categories

### A. Relative-Date Failure
**Criteria:** The source text contains evidence that answers the question, but the evidence includes an unresolved relative date expression (yesterday, last week, next month, etc.) that the model failed to resolve.

**Examples:**
- GT: "When did X happen?" → "August 14, 2023"
- Source: "I went to X yesterday" on August 15, 2023
- Model answered incorrectly or "I don't know"
- Normalization would convert "yesterday" → "August 14, 2023" in the memory text

**Boundary cases:**
- If the relative date resolves to a range (e.g., "last week" = week of Aug 7–13) and GT is a specific date within that range → A
- If the relative date resolves outside the GT range → C (gold-label error)

### B. True Retrieval Miss
**Criteria:** The source text contains explicit, unambiguous evidence that directly answers the question (no relative dates, no inference needed), but the model still answered incorrectly or "I don't know."

**Examples:**
- GT: "When did X happen?" → "August 14, 2023"
- Source: "I went to X on August 14, 2023" (explicit date)
- Model answered incorrectly or "I don't know"
- Retrieval failed to surface the evidence, or surfaced it but model ignored it

**Boundary cases:**
- If evidence requires inference across multiple sessions → D (composition)
- If evidence is implicit/indirect → A (relative-date) or C (gold-label)

### C. Gold-Label Error
**Criteria:** The ground-truth answer has no supporting evidence in the source text, or directly contradicts the source text.

**Examples:**
- GT says "X happened in 2021" but source text shows X introduced in 2023
- GT asks about event Y but no mention of Y exists in any session
- GT specifies a date that is impossible given the conversation chronology

**Boundary cases:**
- If evidence exists but is ambiguous/implicit → not C
- If GT is slightly off (e.g., "January 2022" vs. "January 21, 2022") → judgment call; if the month/year match, usually A (relative-date resolution issue)

### D. Composition Failure
**Criteria:** Answering the question requires combining evidence from multiple sessions or multiple facts, and the model retrieved some but not all necessary pieces.

**Examples:**
- GT: "How many times did X travel to Y?" → requires counting mentions across sessions
- Model retrieves some mentions but misses others
- Model answers with partial information

**Boundary cases:**
- If model retrieved all pieces but reasoned incorrectly → B (retrieval worked, reasoning failed)
- If question requires single-session inference → not D

## Classification Process

1. Read the question and GT answer
2. Search all sessions for keywords from the question/GT
3. Read the relevant session(s) in full context
4. Determine if evidence exists and what form it takes
5. Classify according to the criteria above
6. When uncertain, default to the more conservative category (A over B, C over B)

## Known Limitations

- Small samples (N=20) can produce materially different rates than larger samples (N=50)
- Use 95% CI for proportions: ±22% at N=20, ±14% at N=50, ±10% at N=100
- Classifier rubric consistency matters — document any adjustments
