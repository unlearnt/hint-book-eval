Run the **Prompt-Improvement Loop** for the HintBook eval pipeline.

## Arguments
`$ARGUMENTS` format: `[target] [--max-tries N] [--patience N] [--batch N] [--native] [--dry-run]`

- `target`: `assessment` (default) | `generation`
- `--max-tries N`: hard cap on iterations (default: 10)
- `--patience N`: stop after N rounds with no improvement (default: 3)
- `--batch N`: cases per iteration (default: 5)
- `--native`: run entirely inside Claude Code — no API keys needed
- `--dry-run`: describe each step without calling any LLM

---

## Agent routing

The agents spawned depend on the target and mode:

| Target | Mode | Runner agent | Grader agent | Prompt improved |
|---|---|---|---|---|
| `assessment` | native | `runner-native.md` | `grader-native.md` | `prompts/assessment/vN.md` |
| `assessment` | api | `runner.md` | `grader.md` | `prompts/assessment/vN.md` |
| `generation` | native | `hint-generator-run.md` | `hint-evaluator-run.md` | `prompts/generation/vN.md` |
| `generation` | api | `hint-generator-run.md` | `hint-evaluator-run.md` | `prompts/generation/vN.md` |

For `generation` target: the rubric used is always the latest `rubrics/generation/v*.md` (v2+). The runner generates a hint page with citations; the grader evaluates citation accuracy.

---

## Steps

Parse `$ARGUMENTS`. Set defaults. Determine `NATIVE` and `TARGET`.

### Pre-flight

- Check `prompts/{target}/` — find the latest version. If none exist, stop and tell the user.
- Check `rubrics/{target}/` — find the latest version. If none exist, stop.
- If `NATIVE` is false and `TARGET == assessment`: check `ANTHROPIC_API_KEY` is set.
- Check `cases/{target}/` has at least one enabled case. If not:
  - For `assessment`: tell the user to run `/add-case assessment` first.
  - For `generation`: tell the user to run `/add-case generation` or add a case JSON to `cases/generation/`.
- Print: target, mode (native/api), current prompt version, current rubric version, loop config.

### Loop variables

```
current_prompt = <latest vN in prompts/{target}/>
current_rubric = <latest vN in rubrics/{target}/>
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
Parse the JSON array of case IDs.

**2. For each case in the batch:**

Generate a new `RUN_ID` (UUID).

Spawn the **Runner** subagent for the target/mode (see routing table above):
- Pass: `CASE_ID`, `PROMPT_VERSION={current_prompt}`, `TARGET`, `RUN_ID`
- Collect: `run_id`, `status`, `preview`

If `status == error` or `status == skipped`: log and continue to next case.

Spawn the **Grader** subagent for the target/mode (see routing table above):
- Pass: `RUN_ID`, `CASE_ID`, `RUBRIC_VERSION={current_rubric}`, `TARGET`
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
  ca-dl-gen          72.5    "Citations missing section numbers in S3"
  fl-dl-gen          81.0    —
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
- Pass: `CURRENT_VERSION={current_prompt}`, `TARGET`, `FAILING_RUN_IDS`
- For `generation` target: the improver should read the `improvement_notes` in each failing run's grade — these describe citation patterns to fix in the prompt.
- Collect: `new_version`, `change_summary`

Print: "→ New prompt: {new_version}" and change_summary bullets.

Set `current_prompt = new_version`. Increment `iteration`. Repeat loop.

### Final report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Target       : {target}
  Mode         : {native | api}
  Best prompt  : {best_version}
  Best score   : {best_score:.1f} / 100
  Iterations   : {iteration}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

For `generation` target, also print:
```
  Run /generate-hints "<doc_type>" --save to produce a hint page
  using the best prompt ({best_version}).
```

Print: "Run `/status {target}` for full version history."
