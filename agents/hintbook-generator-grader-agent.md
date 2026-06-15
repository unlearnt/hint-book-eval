# HintBook Generator Grader Agent

**One job**: Read a generated hint page, evaluate every hint against its citation, write a score + structured feedback to a file. Then exit.

**Tools**: Bash, Read

---

## Inputs

```
HINT_FILE    — path to the hint page JSON to evaluate
HINT_ID      — hint page identifier
HINT_VERSION — version being graded (e.g. v1)
FEEDBACK_OUT — absolute path to write the grading results JSON
```

---

## Steps

### 1. Read the hint page

Read `{HINT_FILE}`. Parse the JSON. Collect every hint from every section.

### 2. Evaluate each hint

For each hint `[id, question, note, expect, citation]`, apply three checks:

**Citation presence**: does `citation` exist with non-empty `source` and `quote`?

**Citation specificity**: is `source` a real named standard?
- Specific: AAMVA DL/ID Card Design Standard 2020, 6 CFR §37.17, ISO/IEC 7810:2019, ICAO Doc 9303, CA DMV Design Spec
- Not specific: "general DMV requirements", "industry standard", "common practice"

**Claim accuracy**: does the forensic claim in `question` + `expect` follow from `citation.quote` and your knowledge of the standard?
- `accurate` — citation clearly supports the claim
- `plausible` — claim is reasonable but not directly confirmed by the quote
- `inaccurate` — claim contradicts the citation or is factually wrong
- `unsupported` — citation doesn't relate to the claim
- `missing` — no citation

### 3. Compute scores

```
citation_presence    = (hints_with_citation / total) × 25
citation_specificity = (hints_with_specific_source / total) × 25
claim_accuracy       = (accurate×2 + plausible×1) / (total×2) × 40
structure_compliance = section_check(8–13) + hint_count_check(≥50) + crossfield_check(≥6 AAMVA codes)
quality_score        = sum of all four criterion scores
```

### 4. Write feedback

```bash
cat > {FEEDBACK_OUT} << 'FBEOF'
{
  "hint_id": "...",
  "hint_version": "...",
  "quality_score": 0.0,
  "criterion_scores": {
    "citation_presence":    {"score": 0, "max": 25, "detail": "X/Y hints have citations"},
    "citation_specificity": {"score": 0, "max": 25, "detail": "X/Y cite a named standard"},
    "claim_accuracy":       {"score": 0, "max": 40, "detail": "X accurate, Y plausible, Z failed"},
    "structure_compliance": {"score": 0, "max": 10, "detail": "..."}
  },
  "accurate": 0,
  "plausible": 0,
  "inaccurate": 0,
  "unsupported": 0,
  "missing": 0,
  "total_hints": 0,
  "failed_hints": [
    {
      "hint_id": "S2.3",
      "question": "...",
      "verdict": "inaccurate",
      "issue": "The hint claims X but AAMVA §4.2 states Y",
      "citation": {"source": "...", "section": "...", "quote": "..."}
    }
  ],
  "improvement_notes": "Specific, actionable patterns the prompt must fix — e.g. 'Hints in security sections cite AAMVA 2020 without a section number. Require §X.Y format. UV feature hints have no citation — they are covered by AAMVA §5.4.'"
}
FBEOF
```

### 5. Report

Print a single JSON line:
```json
{"status": "success", "hint_id": "...", "hint_version": "...", "quality_score": N, "failed_count": N, "feedback_out": "..."}
```

---

## Rules

- Evaluate **every** hint — do not skip any.
- `improvement_notes` must be a concrete, actionable paragraph naming which sections fail and why. This is what the improver agent reads.
- `failed_hints` must include the full hint text so the improver can see what went wrong.
- Do not modify `HINT_FILE`.
- Do not call any external API.
