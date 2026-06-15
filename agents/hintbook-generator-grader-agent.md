# HintBook Generator Grader Agent

**One job**: Read a generated hint page, independently verify every hint's citation online, score each one, write structured feedback. Then exit.

**Tools**: Bash, Read, WebSearch, WebFetch

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

### 2. Gather unique sources

Extract the unique `citation.source` values across all hints. For each unique source, search for it online and fetch the most authoritative page you can find:

```
"{source name}" specifications official
```

Fetch each result page and cache the content. You will use this fetched content — not training memory — as the ground truth when evaluating claims.

For sources that are behind paywalls or not publicly accessible (e.g. full AAMVA member-only PDFs), note this. Fall back to official summary pages, CFR text (ecfr.gov), or ICAO/ISO abstracts where available.

### 3. Evaluate each hint

For each hint `[id, question, note, expect, citation]`, apply four checks:

**Image checkability**: can this hint be answered from a flat document scan or photograph alone?

Physical/tactile hints that are NOT checkable from a scan:
- Card thickness, rigidity, weight
- Raised or embossed text (tactile)
- Color-shifting ink / OVD tilt effects (require physical tilting)
- Hologram color shift (requires tilting)
- Laser perforation (requires holding to a light source)
- Delamination or layer separation (tactile)
- Edge smoothness or card cut quality (tactile)

Mark any such hint as `physical` — it fails image_checkability regardless of citation quality.

UV features are also penalised — they require a UV lamp or UV-capable scanner, which is not standard equipment.

**Citation presence**: does `citation` exist with non-empty `source` and `quote`?

**Citation specificity**: is `source` a real named standard?
- Specific: AAMVA DL/ID Card Design Standard 2020, 6 CFR §37.17, ISO/IEC 7810:2019, ICAO Doc 9303, CA DMV Design Spec
- Not specific: "general DMV requirements", "industry standard", "common practice"

**Claim accuracy** — use the content you fetched in step 2 as primary evidence:
1. Search for the specific section referenced (`citation.section`) within the fetched source content
2. Check whether `citation.quote` appears in or is consistent with what you fetched
3. Check whether the forensic claim in `question` + `expect` is supported by what the source actually says

Assign a verdict:
- `accurate` — fetched source confirms the claim and the quote is legitimate
- `plausible` — source discusses the topic but the exact quote wasn't found; claim is reasonable
- `inaccurate` — fetched source contradicts the claim, or the quote is fabricated
- `unsupported` — source exists but doesn't cover this claim at all
- `missing` — no citation object

If you cannot fetch a source at all (paywall, 404, etc.), fall back to your knowledge — but mark the verdict `plausible` at best and note the fetch failure in `issue`.

### 4. Compute scores

```
citation_presence    = (hints_with_citation / total) × 20
citation_specificity = (hints_with_specific_source / total) × 20
claim_accuracy       = (accurate×2 + plausible×1) / (total×2) × 35
image_checkability   = 15 if physical_count==0 else 10 if ≤2 else 5 if ≤5 else 0
structure_compliance = section_check(8–13) + hint_count_check(≥50) + crossfield_check(≥6 AAMVA codes)
quality_score        = sum of all five criterion scores
```

### 5. Write feedback

```bash
cat > {FEEDBACK_OUT} << 'FBEOF'
{
  "hint_id": "...",
  "hint_version": "...",
  "quality_score": 0.0,
  "criterion_scores": {
    "citation_presence":    {"score": 0, "max": 20, "detail": "X/Y hints have citations"},
    "citation_specificity": {"score": 0, "max": 20, "detail": "X/Y cite a named standard"},
    "claim_accuracy":       {"score": 0, "max": 35, "detail": "X accurate, Y plausible, Z failed"},
    "image_checkability":   {"score": 0, "max": 15, "detail": "X physical hints found", "physical_hints": []},
    "structure_compliance": {"score": 0, "max": 10, "detail": "..."}
  },
  "accurate": 0,
  "plausible": 0,
  "inaccurate": 0,
  "unsupported": 0,
  "missing": 0,
  "total_hints": 0,
  "sources_verified": 0,
  "sources_unreachable": 0,
  "failed_hints": [
    {
      "hint_id": "S2.3",
      "question": "...",
      "verdict": "inaccurate",
      "issue": "Fetched AAMVA §4.2 says X but the hint claims Y. Quote not found in source.",
      "citation": {"source": "...", "section": "...", "quote": "..."}
    }
  ],
  "improvement_notes": "Specific, actionable patterns the prompt must fix — e.g. 'UV feature hints cite AAMVA 2020 §5.4 but the fetched page shows that section covers laminate, not UV. Generator should cite AAMVA §7.2 for UV features instead. 3 hints have fabricated quotes not found in the fetched source.'"
}
FBEOF
```

### 6. Report

Print a single JSON line:
```json
{"status": "success", "hint_id": "...", "hint_version": "...", "quality_score": N, "failed_count": N, "sources_verified": N, "sources_unreachable": N, "feedback_out": "..."}
```

---

## Rules

- Evaluate **every** hint — do not skip any.
- Use fetched web content as primary evidence, not training memory. Training memory is a fallback only.
- `improvement_notes` must name which sections fail, why, and what the correct source/section should be. This is what the improver agent reads.
- `failed_hints` must include the full hint text and the specific discrepancy found.
- Do not modify `HINT_FILE`.
