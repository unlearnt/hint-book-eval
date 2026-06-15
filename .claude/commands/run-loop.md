Run the **Assessment Prompt-Improvement Loop** for the HintBook eval pipeline.

## Arguments
`$ARGUMENTS` format: `[--max-tries N] [--patience N] [--batch N] [--native] [--dry-run]`

- `--max-tries N`: hard cap on iterations (default: 10)
- `--patience N`: stop after N rounds with no improvement (default: 3)
- `--batch N`: cases per iteration (default: 5)
- `--native`: run entirely inside Claude Code — no API keys needed
- `--dry-run`: describe each step without calling any LLM

---

## Agent routing

| Mode | Runner agent | Grader agent | Prompt improved |
|---|---|---|---|
| native | `runner-native.md` | `grader-native.md` | `prompts/assessment/vN.md` |
| api | `runner.md` | `grader.md` | `prompts/assessment/vN.md` |

---

## Steps

Parse `$ARGUMENTS`. Set defaults. Determine `NATIVE`.

### Pre-flight

- Check `prompts/assessment/` — find the latest version. If none exist, stop and tell the user.
- Check `rubrics/assessment/` — find the latest version. If none exist, stop.
- If `NATIVE` is false: check `ANTHROPIC_API_KEY` is set.
- Check `cases/assessment/` has at least one enabled case. If not, tell the user to run `/add-case` first.
- Print: mode (native/api), current prompt version, current rubric version, loop config.

### Loop variables

```
current_prompt = <latest vN in prompts/assessment/>
current_rubric = <latest vN in rubrics/assessment/>
best_score     = -1
best_version   = current_prompt
no_improve     = 0
iteration      = 0
```

### Iteration (repeat until stopping condition)

**1. Sample cases**
```bash
python tools/sample.py --target assessment --n {batch}
```
Parse the JSON array of case IDs.

**2. For each case in the batch:**

Generate a new `RUN_ID` (UUID).

Spawn the **Runner** subagent:
- Pass: `CASE_ID`, `PROMPT_VERSION={current_prompt}`, `TARGET=assessment`, `RUN_ID`
- Collect: `run_id`, `status`, `preview`

If `status == error` or `status == skipped`: log and continue to next case.

Spawn the **Grader** subagent:
- Pass: `RUN_ID`, `CASE_ID`, `RUBRIC_VERSION={current_rubric}`, `TARGET=assessment`
- Collect: `aggregate_score`, `improvement_notes`

Record: `(case_id, run_id, aggregate_score, improvement_notes)`

**3. Aggregate**

```
agg_score = mean of aggregate_scores collected this iteration
```

Print a table:
```
Iteration {N} — prompt {current_prompt} — rubric {current_rubric}
  case               score   notes
  ─────────────────────────────────────────────────────
  ca_dl_001          72.5    "Missed UV fluorescence check"
  ca_dl_002          81.0    —
  ...
  ─────────────────────────────────────────────────────
  Average            76.8
```

Update tracking:
- If `agg_score > best_score`: `best_score = agg_score`, `best_version = current_prompt`, `no_improve = 0`
- Else: `no_improve += 1`

**4. Check stopping conditions**

- `no_improve >= patience` → "No improvement for {N} rounds. Stopping."
- `iteration >= max_tries` → "Max tries reached."
- All scores ≥ 80 → "All cases passed threshold."

→ Any of the above: go to **Final report**.

**5. Improve the prompt**

Collect failing runs (score < 80, up to 6 run IDs).

Spawn a **Prompt-Improver** subagent:
- If `NATIVE` is true: read `agents/prompt-improver-native.md`
- If `NATIVE` is false: read `agents/prompt-improver.md`
- Pass: `CURRENT_VERSION={current_prompt}`, `TARGET=assessment`, `FAILING_RUN_IDS`
- Collect: `new_version`, `change_summary`

Print: "→ New prompt: {new_version}" and change_summary bullets.

Set `current_prompt = new_version`. Increment `iteration`. Repeat loop.

### Final report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Mode         : {native | api}
  Best prompt  : {best_version}
  Best score   : {best_score:.1f} / 100
  Iterations   : {iteration}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Print: "Run `/status` for full version history."
