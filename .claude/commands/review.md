Run an interactive **human-review session** for recent grader outputs, then optionally trigger the Grader-Improvement Loop.

## Arguments
`$ARGUMENTS` format: `[target] [--n N] [--native]`

- `target`: `assessment` (default) | `generation`
- `--n N`: number of recent graded runs to review (default: 10)
- `--native`: use the native grader (no API key needed) when re-grading runs during review

---

## Steps

Parse `$ARGUMENTS`. Set `NATIVE` = true if `--native` was passed.

### 1. Fetch recent graded runs
```bash
python tools/sample.py --target {target} --status
```
Then list the N most recently graded runs from `memory/runs/` (sort by timestamp descending, pick those with a `grade` field).

For each run file read: `run_id`, `case_id`, `prompt_version`, `raw_output`, `grade.aggregate_score`, `grade.criterion_scores`, `grade.overall_feedback`, `grade.improvement_notes`.

### 2. Review each run — interactively

For each run, display:
```
─── [{i}/{N}] case={case_id}  run={run_id[:8]}  score={aggregate_score:.1f}/100 ───

Model output (first 500 chars):
  {raw_output[:500]}...

Grader scores:
  verdict_accuracy : {score} / {weight}  — {reasoning}
  check_accuracy   : ...
  ...

Overall feedback   : {overall_feedback}
Improvement notes  : {improvement_notes}
```

Ask the user:
1. `"Correct / Incorrect / Partial / Skip? [s]"` — wait for input
2. If Incorrect or Partial: `"What's wrong? (one line)"` — wait for note
3. If Incorrect or Partial: `"Enter corrected aggregate score (0–100):"` — wait for number
4. `"Add to golden set? [Y/n]"` — if Y, write entry to `memory/golden-set.json`

Accumulate an `annotations` list:
```json
{
  "run_id": "...",
  "case_id": "...",
  "verdict": "correct|incorrect|partial",
  "note": "...",
  "correct_aggregate": N
}
```

### 3. Save annotations
Write to `memory/annotations-{timestamp}.json`.
Print: "Saved {N} annotation(s) → memory/annotations-{timestamp}.json"

### 4. Offer to run the Grader-Improvement Loop
If there are ≥ 3 `incorrect` annotations:

Ask: `"Run Grader-Improvement Loop now? [Y/n]"`

If yes:
- Generate a timestamp: `DIAG_OUT=memory/diagnosis-{timestamp}.json`

Spawn a **Grade-Grader** subagent (read `agents/grade-grader.md` as its system prompt):
- Pass: `TARGET`, `ANNOTATIONS_FILE=memory/annotations-{timestamp}.json`, `DIAGNOSIS_OUT={DIAG_OUT}`
- Wait for it to write the diagnosis and report back.

If `promote_recommended == true`:
  Spawn a **Grader-Improver** subagent (read `agents/grader-improver.md` as its system prompt):
  - Pass: `CURRENT_RUBRIC_VERSION=<latest vN>`, `TARGET`, `DIAGNOSIS_FILE={DIAG_OUT}`, `NATIVE={NATIVE}`
  - Wait for it to report back.
  - Print whether the rubric was promoted and the new version if so.

Print: "Run `/status {target}` to see the updated rubric."

---

## Native mode note

With `--native`, if runs in the review set have no `grade` field (they were run natively but not yet graded), you may grade them during review:

Spawn a **Grader (native)** subagent — read `agents/grader-native.md` as its system prompt:
- Pass: `RUN_ID`, `CASE_ID`, `RUBRIC_VERSION=<latest vN>`, `TARGET`
- Then display the returned scores in the review UI above.
