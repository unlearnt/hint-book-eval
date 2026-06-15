Run the **Prompt-Improvement Loop** for the HintBook eval pipeline.

## Arguments
`$ARGUMENTS` format: `[target] [--max-tries N] [--patience N] [--batch N] [--native] [--dry-run]`

- `target`: `assessment` (default) | `generation`
- `--max-tries N`: hard cap on iterations (default: 10)
- `--patience N`: stop after N rounds with no improvement (default: 3)
- `--batch N`: cases per iteration (default: 5)
- `--native`: run entirely inside Claude Code — no API keys needed (uses `agents/*-native.md`)
- `--dry-run`: describe each step without calling any LLM

---

## Steps

Parse `$ARGUMENTS`. Set defaults. Determine `NATIVE` = true if `--native` was passed.

### Pre-flight
- Check that `prompts/{target}/v1.md` exists. If not, tell the user to add an initial prompt and stop.
- Check that `rubrics/{target}/v1.md` exists. Same.
- If `NATIVE` is **false**: check that `ANTHROPIC_API_KEY` is set in the environment (read `.env` if present). Warn if missing.
- Find the latest prompt version in `prompts/{target}/` and rubric version in `rubrics/{target}/`.
- Print: current prompt, rubric, mode (`native` or `api`), and loop config.

### Loop variables
```
current_prompt = <latest vN>
current_rubric = <latest vN>
best_score     = -1
best_version   = current_prompt
no_improve     = 0
iteration      = 0
```

### Iteration (repeat until stopping condition)

**1. Sample cases**
```bash
python tools/sample.py --target {target} --n {batch}
```
Prints a JSON array of case IDs. Parse it.

**2. For each case in the batch:**

Generate a new `RUN_ID` (UUID).

If `NATIVE` is **true**:

  Spawn a **Runner (native)** subagent — read `agents/runner-native.md` as its system prompt:
  - Pass: `CASE_ID`, `PROMPT_VERSION={current_prompt}`, `TARGET`, `RUN_ID`
  - Collect: `run_id`, `status`, `preview`

If `NATIVE` is **false**:

  Spawn a **Runner** subagent — read `agents/runner.md` as its system prompt:
  - Pass: `CASE_ID`, `PROMPT_VERSION={current_prompt}`, `TARGET`, `RUN_ID`
  - Collect: `run_id`, `status`

If `status == error` or `status == skipped`: log it, continue to next case.

If `NATIVE` is **true**:

  Spawn a **Grader (native)** subagent — read `agents/grader-native.md` as its system prompt:
  - Pass: `RUN_ID`, `CASE_ID`, `RUBRIC_VERSION={current_rubric}`, `TARGET`
  - Collect: `aggregate_score`, `improvement_notes`

If `NATIVE` is **false**:

  Spawn a **Grader** subagent — read `agents/grader.md` as its system prompt:
  - Pass: `RUN_ID`, `CASE_ID`, `RUBRIC_VERSION={current_rubric}`, `TARGET`
  - Collect: `aggregate_score`, `improvement_notes`

Record: `(case_id, run_id, aggregate_score, improvement_notes)`

**3. Aggregate**
```
agg_score = mean(scores collected this iteration)
```
Print a table: case | score | improvement_notes

Update tracking:
- If `agg_score > best_score`: update `best_score`, `best_version=current_prompt`, reset `no_improve=0`
- Else: `no_improve += 1`

**4. Check stopping conditions** (check in order)
- `no_improve >= patience` → print "No improvement for N rounds. Stopping."
- `iteration >= max_tries` → print "Max tries reached."
- All scores ≥ 80 → print "All cases passed threshold."
→ In any of these cases: go to **Final report**

**5. Improve the prompt**
Collect failing run IDs (score < 80, up to 6).

If `NATIVE` is **true**:

  Spawn a **Prompt-Improver (native)** subagent — read `agents/prompt-improver-native.md` as its system prompt:
  - Pass: `CURRENT_VERSION={current_prompt}`, `TARGET`, `FAILING_RUN_IDS`
  - Collect: `new_version`, `change_summary`

If `NATIVE` is **false**:

  Spawn a **Prompt-Improver** subagent — read `agents/prompt-improver.md` as its system prompt:
  - Pass: `CURRENT_VERSION={current_prompt}`, `TARGET`, `FAILING_RUN_IDS`
  - Collect: `new_version`, `change_summary`

Print: "→ New prompt: {new_version}" + change_summary bullets.
Set `current_prompt = new_version`. Increment `iteration`. Repeat loop.

### Final report
```
Mode            : {native | api}
Best prompt     : {best_version}
Best score      : {best_score:.1f}
Iterations      : {iteration}
```
Print: "Run `/status {target}` for full version history."
