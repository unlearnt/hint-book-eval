Generate a forensic hint page for a document type with per-hint citations, then evaluate every hint against its citation. Optionally save the result to `hints/`.

## Arguments
`$ARGUMENTS` format: `<doc_type> [--id <hint_id>] [--save] [--threshold N] [--max-revisions N]`

- `doc_type`: description of the document (e.g. `"California Driver License Gen 3"`)
- `--id`: override the hint page ID (default: derived from doc_type)
- `--save`: save to `hints/` when quality meets threshold
- `--threshold N`: minimum quality score to auto-save (default: 80)
- `--max-revisions N`: max revision rounds if score is below threshold (default: 2)

---

## Steps

Parse `$ARGUMENTS`. Set defaults.

### 1. Generate the hint page

Choose a `HINT_ID` from `--id` if provided, otherwise derive from `doc_type` (snake_case).
Set `OUT_FILE=/tmp/hints_{HINT_ID}.json`.
Set `EVAL_OUT=/tmp/eval_{HINT_ID}.json`.

Spawn a **Hint-Generator** subagent (read `agents/hint-generator.md` as its system prompt):
- Pass: `DOC_TYPE`, `HINT_ID`, `OUT_FILE`
- Collect: `total_hints`, `cited_hints`, `out_file`

Print:
```
Generated: {total_hints} hints, {cited_hints} with citations
```

### 2. Evaluate the hint page

Spawn a **Hint-Evaluator** subagent (read `agents/hint-evaluator.md` as its system prompt):
- Pass: `HINT_FILE={OUT_FILE}`, `EVAL_OUT`
- Collect: `quality_score`, `accurate`, `plausible`, `inaccurate`, `unsupported`, `missing`, `failed_count`, `summary`

### 3. Display results

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Hint Page: {HINT_ID}
  Quality score: {quality_score:.1f} / 100
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓ Accurate   : {accurate}
  ~ Plausible  : {plausible}
  ✗ Inaccurate : {inaccurate}
  ? Unsupported: {unsupported}
  ∅ Missing    : {missing}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  {summary}
```

If `failed_count > 0`, list the failed hints:
```
Failed hints:
  [S2.3] <question>
         Verdict: inaccurate
         Issue: <issue>
         Citation: <source> §<section> — "<quote>"
```

### 4. Revision loop (if score < threshold)

If `quality_score < threshold` AND `revision < max_revisions`:

Print: `"Score {quality_score:.1f} is below threshold {threshold}. Revising... (attempt {revision+1}/{max_revisions})"`

Spawn a **Hint-Generator** subagent again:
- Pass: `DOC_TYPE`, `HINT_ID`, `OUT_FILE`
- Also pass the `failed_hints` list from the evaluation as `REVISION_NOTES` so the generator can fix them
- The generator should re-generate only the failed hints and merge them into the existing output

Re-run the evaluator (Step 2). Increment `revision`. Repeat until threshold is met or max-revisions reached.

### 5. Save decision

If `quality_score >= threshold` AND `--save` was passed:
```bash
python tools/save_hints.py --hint-file {OUT_FILE}
python tools/save_hint_eval.py --hint-id {HINT_ID} --eval-file {EVAL_OUT}
```
Print: `"✓ Saved to hints/{HINT_ID}.json"`

If `quality_score >= threshold` AND `--save` was NOT passed:
Ask: `"Save hint page to hints/{HINT_ID}.json? [Y/n]"`
If Y: run the save commands above.

If `quality_score < threshold` after all revisions:
Ask: `"Quality score {quality_score:.1f} is below threshold {threshold}. Save anyway? [y/N]"`
If Y: run the save commands with a warning.

### 6. Cleanup

```bash
rm -f {OUT_FILE} {EVAL_OUT}
```

Print final status:
```
Done. Run /status to see all hint pages, or /run-loop assessment --native to evaluate documents against this hint page.
```
