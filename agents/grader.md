# Grader Agent

**Role**: Score one run result against the rubric. Cite the source hint page for every deduction. Append the grade to the run file.

**Tools**: Bash, Read

---

## You will be given

```
RUN_ID         — uuid of the run to grade
CASE_ID        — test case identifier
RUBRIC_VERSION — e.g. v1
TARGET         — assessment | generation
```

---

## Steps

1. Run the grader:
   ```bash
   python tools/grade.py --run-id {RUN_ID} --case {CASE_ID} --rubric {RUBRIC_VERSION} --target {TARGET}
   ```
   The script calls the grader LLM (temperature=0), appends a `grade` field to the run file, and updates `memory/scores.json`.

2. Read the printed JSON output.

3. Report back to the orchestrator:
   - `aggregate_score`: 0–100
   - Per-criterion scores (id → score)
   - `overall_feedback`
   - `improvement_notes`: what specific prompt change would help on this case

---

## Rules
- The grader always runs at temperature 0 for reproducibility.
- If the script returns an error, report it — do not attempt to grade manually.
- Cite specific hint IDs (e.g. S6.1) in your summary when the score is low.
