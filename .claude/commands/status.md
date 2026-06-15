Show a summary of the HintBook eval pipeline state.

## Arguments
`$ARGUMENTS` format: `[target]`

- `target`: `assessment` | `generation` | (omit to show both)

---

## Steps

For each target in scope:

### Prompt version table
List all `prompts/{target}/v*.md` files. For each, read the YAML front matter to get `version`, `parent`, `aggregate_score`, `notes`, `created_at`.

Display as a table:
```
Prompt Versions — assessment
Version  Parent  Score   Created      Notes
───────────────────────────────────────────────────────
v1       —         —     2026-06-15   Initial version
v2       v1       72.4   2026-06-16   Clarified bbox instruction
v3 ◀    v2       81.0   2026-06-16   Added specificity rule  ← current best
```
(◀ marks the highest-scoring version)

### Rubric version table
List all `rubrics/{target}/v*.md`. Read `version`, `golden_set_accuracy`, `notes`, `created_at`.

```
Rubric Versions — assessment
Version  Golden-set acc  Notes
──────────────────────────────────────────────────
v1 ◀         —           Initial rubric
```

### Case score history
```bash
python tools/sample.py --target {target} --status
```
Display the JSON as a table: case_id | runs | best | avg

### Golden set + memory summary
- Count entries in `memory/golden-set.json`. Print: "Golden-set: N case(s)"
- Count files in `memory/runs/` recursively. Print: "Total runs stored: N"
- If any annotation files exist in `memory/`: print their names and entry counts.

### Health flags
- Any prompt version with `aggregate_score: null` that has been tested? → "⚠ {vN} has no score yet"
- Golden set empty? → "⚠ Golden set is empty — run /review to seed it"
- Latest rubric has never been validated? → "⚠ rubric {vN} has no golden-set accuracy"
