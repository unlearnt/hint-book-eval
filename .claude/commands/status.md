Show a summary of the HintBook eval pipeline state.

---

## Steps

### Assessment prompt version table
List all `prompts/assessment/v*.md` files. For each, read the YAML front matter to get `version`, `parent`, `aggregate_score`, `notes`, `created_at`.

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

### Assessment rubric version table
List all `rubrics/assessment/v*.md`. Read `version`, `golden_set_accuracy`, `notes`, `created_at`.

```
Rubric Versions — assessment
Version  Golden-set acc  Notes
──────────────────────────────────────────────────
v1 ◀         —           Initial rubric
```

### Generation prompt version table
List all `prompts/generation/v*.md` files with same format as above.

### Hint pages
List all `hints/*.json` (canonical, non-versioned). For each print: `hint_id`, section count, hint count, citation coverage %.

Also show versioned files: `hints/*-v*.json` grouped by hint_id.

Print hint score history from `memory/hint-scores.json`:
```
Hint Scores
hint_id   version  prompt   score   accurate  failed  timestamp
────────────────────────────────────────────────────────────────
ca_dl     v1       v2       72.5    35        12      2026-06-15
ca_dl     v2       v3       84.0    47         3      2026-06-15  ← canonical
```

### Assessment case score history
```bash
python tools/sample.py --target assessment --status
```
Display the JSON as a table: case_id | runs | best | avg

### Golden set + memory summary
- Count entries in `memory/golden-set.json`. Print: "Golden-set: N case(s)"
- Count files in `memory/runs/` recursively. Print: "Total runs stored: N"

### Health flags
- Any prompt version with `aggregate_score: null` that has been tested? → "⚠ {vN} has no score yet"
- Golden set empty? → "⚠ Golden set is empty — run /review to seed it"
- Latest rubric has never been validated? → "⚠ rubric {vN} has no golden-set accuracy"
- Any hint page with citation coverage < 90%? → "⚠ {hint_id}: only {N}% hints cited"
