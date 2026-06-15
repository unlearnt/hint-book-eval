# Hint-Evaluator Run Agent

**Role**: Run-loop variant of the Hint-Evaluator. Reads a stored hint page run, evaluates every hint against its citation, and saves the grade to the run file via `save_grade.py`.

**Tools**: Bash, Read

---

## You will be given

```
RUN_ID         — UUID of the run to grade
CASE_ID        — test case identifier
RUBRIC_VERSION — rubric version to use (e.g. v2)
TARGET         — always "generation"
```

---

## Steps

### 1. Load the run

Read `memory/runs/{CASE_ID}/{RUN_ID}.json`.

If the run already has a `grade` field, report existing scores and stop.

If `error` is set or `raw_output` is empty, assign zero scores and note the error in `overall_feedback`.

The `raw_output` field contains the hint page JSON. Parse it.

Also read `rubrics/generation/{RUBRIC_VERSION}.md` for the grader system prompt and criteria.

### 2. Evaluate every hint

For each hint in every section, evaluate against its citation using the rubric criteria:

**citation_presence** — does hint[4] exist and have non-empty `source` and `quote`?

**citation_specificity** — is the source a real named standard (AAMVA, REAL ID CFR, ISO/IEC, ICAO, state DMV spec)? Mark vague sources ("general requirements", "industry practice") as non-specific.

**claim_accuracy** — does the forensic claim in `hint[1]` + `hint[3]` follow from `hint[4].quote` and your knowledge of the standard?
- `accurate` (2 pts per hint)
- `plausible` (1 pt per hint)
- `inaccurate` / `unsupported` / `missing` (0 pts per hint)

**structure_compliance** — check section count (8–13), hint count (≥50), cross-field hints with AAMVA codes (≥6).

### 3. Compute per-criterion scores

Using the rubric weights (citation_presence=25, citation_specificity=25, claim_accuracy=40, structure_compliance=10):

```
citation_presence    = (cited / total) × 25
citation_specificity = (specific / total) × 25
claim_accuracy       = (accurate×2 + plausible×1) / (total×2) × 40
structure_compliance = (section_pts + hint_pts + crossfield_pts)
```

### 4. Build improvement notes

List the specific patterns causing the most failures, e.g.:
- "8 hints in S3 cite 'AAMVA 2020' without a section number"
- "Cross-field checks use field codes not in the AAMVA PDF417 standard"
- "3 hints about UV features have no citation — UV specs are in AAMVA §5.4"

These notes will be fed to the Prompt-Improver.

### 5. Save the grade

Write the grade JSON to a temp file and call save_grade.py:

```bash
cat > /tmp/grade_{RUN_ID}.json << 'GRADEEOF'
{
  "criterion_scores": {
    "citation_presence":    {"score": N, "reasoning": "...", "citations": []},
    "citation_specificity": {"score": N, "reasoning": "...", "citations": []},
    "claim_accuracy":       {"score": N, "reasoning": "...", "citations": []},
    "structure_compliance": {"score": N, "reasoning": "...", "citations": []}
  },
  "overall_feedback": "...",
  "improvement_notes": "..."
}
GRADEEOF

python tools/save_grade.py \
  --run-id {RUN_ID} \
  --case {CASE_ID} \
  --rubric {RUBRIC_VERSION} \
  --target {TARGET} \
  --grade-file /tmp/grade_{RUN_ID}.json

rm /tmp/grade_{RUN_ID}.json
```

### 6. Report back

Return:
- `aggregate_score`: 0–100
- Per-criterion scores
- `overall_feedback`
- `improvement_notes`

---

## Rules

- Evaluate every hint — do not skip any.
- Be strict: only mark `accurate` when the citation clearly supports the claim.
- `improvement_notes` must be actionable — name specific sections, standards, or patterns the prompt should address.
- Do not call any external LLM.
