Generate a forensic hint page with citations, grade it, and fix issues until quality passes the threshold. Two types of fixes run depending on what the grader finds:

- **Patcher** — fixes specific `inaccurate` / `unsupported` hints in-place. Fast: only the failing hints are touched.
- **Improver** — rewrites the generation prompt when the overall score is low. Triggers a full regeneration.

Each agent does one job and exits to keep context lean.

## Arguments
`$ARGUMENTS` format: `<doc_type> [--id <hint_id>] [--threshold N] [--max-revisions N]`

- `doc_type`: document description (e.g. `"California Driver License Gen 3 Real ID"`)
- `--id`: override the snake_case hint ID (default: derived from doc_type)
- `--threshold N`: quality score needed to stop (default: 80)
- `--max-revisions N`: max fix rounds total (default: 5)

---

## Setup

Derive `HINT_ID` from `--id` or from `doc_type` (lowercase, spaces → underscores, strip punctuation).

Find the latest generation prompt: list `prompts/generation/v*.md` and take the highest version number. Call it `CURRENT_PROMPT`.

Determine the starting hint version by checking which `hints/{HINT_ID}-v*.json` files already exist. Start at `v1` if none exist. Call it `HINT_VERSION`.

Set:
```
REVISION         = 0
BEST_SCORE       = 0
BEST_INACCURATE  = 999
BEST_HINT_VERSION = null
NEEDS_GENERATION = true    ← true on first run and after each prompt improvement
```

---

## Loop: repeat until promoted or REVISION >= max-revisions

### Step 1 — Generate (only when NEEDS_GENERATION is true)

If `NEEDS_GENERATION` is false, skip to Step 2 using the existing `hints/{HINT_ID}-{HINT_VERSION}.json`.

Set temp files:
```
GEN_OUT  = /tmp/hint_{HINT_ID}_{HINT_VERSION}.json
FEED_OUT = /tmp/feedback_{HINT_ID}_{HINT_VERSION}.json
```

Spawn **HintBook Generator Agent** (`agents/hintbook-generator-agent.md`):
```
PROMPT_VERSION = {CURRENT_PROMPT}
DOC_TYPE       = {doc_type}
HINT_ID        = {HINT_ID}
HINT_VERSION   = {HINT_VERSION}
OUT_FILE       = {GEN_OUT}
```
Wait for: `{status, total_hints, cited_hints}`

If `status != success`: print error and stop.

Save the versioned hint page:
```bash
python tools/save_hint_version.py \
  --hint-file {GEN_OUT} \
  --hint-id {HINT_ID} \
  --hint-version {HINT_VERSION}
```

Set `NEEDS_GENERATION = false`.

---

### Step 2 — Grade

```
GEN_OUT  = /tmp/hint_{HINT_ID}_{HINT_VERSION}.json     (if generated this round)
           OR hints/{HINT_ID}-{HINT_VERSION}.json       (if patched this round)
FEED_OUT = /tmp/feedback_{HINT_ID}_{HINT_VERSION}.json
```

Spawn **HintBook Generator Grader Agent** (`agents/hintbook-generator-grader-agent.md`):
```
HINT_FILE    = {GEN_OUT or hints/{HINT_ID}-{HINT_VERSION}.json}
HINT_ID      = {HINT_ID}
HINT_VERSION = {HINT_VERSION}
FEEDBACK_OUT = {FEED_OUT}
```
Wait for: `{quality_score, inaccurate, failed_count, ...all verdict counts}`

Record the score:
```bash
python tools/record_hint_score.py \
  --hint-id {HINT_ID} \
  --hint-version {HINT_VERSION} \
  --prompt-version {CURRENT_PROMPT} \
  --score {quality_score} \
  --accurate {accurate} --plausible {plausible} \
  --inaccurate {inaccurate} --unsupported {unsupported} --missing {missing} \
  --total {total_hints}
```

Print progress:
```
[{HINT_VERSION}] score={quality_score:.1f}  inaccurate={inaccurate}  prompt={CURRENT_PROMPT}
```

Update best:
```
if quality_score > BEST_SCORE or (quality_score == BEST_SCORE and inaccurate < BEST_INACCURATE):
    BEST_SCORE        = quality_score
    BEST_INACCURATE   = inaccurate
    BEST_HINT_VERSION = HINT_VERSION
```

---

### Step 3 — Check promotion

If `quality_score >= threshold` AND `inaccurate == 0`:
```bash
python tools/save_hint_version.py \
  --hint-file hints/{HINT_ID}-{HINT_VERSION}.json \
  --hint-id {HINT_ID} \
  --hint-version {HINT_VERSION} \
  --promote
```
Print:
```
✓ score={quality_score:.1f} ≥ {threshold}, inaccurate=0
✓ Promoted hints/{HINT_ID}-{HINT_VERSION}.json → hints/{HINT_ID}.json
```
Go to **Final report**.

If `REVISION >= max-revisions`: go to **Max revisions reached**.

---

### Step 4 — Fix

**Branch A — Factual errors present (`inaccurate > 0`)**

Use the patcher. It fixes only the failing hints without regenerating the whole page.

```
PATCH_OUT = /tmp/hint_{HINT_ID}_patch.json
```

Spawn **HintBook Generator Patcher Agent** (`agents/hintbook-generator-patcher-agent.md`):
```
HINT_FILE     = hints/{HINT_ID}-{HINT_VERSION}.json
FEEDBACK_FILE = {FEED_OUT}
HINT_ID       = {HINT_ID}
HINT_VERSION  = {HINT_VERSION}
OUT_FILE      = {PATCH_OUT}
```
Wait for: `{status, patched_count, dropped_count, patched_hints}`

Print:
```
→ Patcher fixed {patched_count} hint(s), dropped {dropped_count}: {patched_hints}
```

Increment `HINT_VERSION` to next number (e.g. v2 → v3).

Save the patched page as the new version:
```bash
python tools/save_hint_version.py \
  --hint-file {PATCH_OUT} \
  --hint-id {HINT_ID} \
  --hint-version {HINT_VERSION}
```

Set `NEEDS_GENERATION = false` (patched page is the input for the next grade).
Clean up: `rm {PATCH_OUT} {FEED_OUT}`
`REVISION += 1`. Repeat loop from Step 2.

---

**Branch B — No factual errors, score below threshold (`inaccurate == 0`, `score < threshold`)**

Use the improver. It fixes the generation prompt; next iteration does a full regeneration.

Spawn **HintBook Generator Improver Agent** (`agents/hintbook-generator-improver-agent.md`):
```
CURRENT_PROMPT_VERSION = {CURRENT_PROMPT}
FEEDBACK_FILE          = {FEED_OUT}
```
Wait for: `{new_prompt_version, root_cause, change_summary}`

Print:
```
→ Prompt improved: {CURRENT_PROMPT} → {new_prompt_version}
  Root cause: {root_cause}
  Change: {change_summary}
```

Update:
```
CURRENT_PROMPT   = new_prompt_version
HINT_VERSION     = v{N+1}   (increment)
NEEDS_GENERATION = true      ← triggers full regeneration next round
REVISION        += 1
```

Clean up: `rm {FEED_OUT}`
Repeat loop from Step 1.

---

## Max revisions reached

Print:
```
Max revisions reached ({REVISION}). Best: {BEST_HINT_VERSION} score={BEST_SCORE:.1f} inaccurate={BEST_INACCURATE}
```
If `BEST_INACCURATE > 0`:
```
⚠ Best version still has inaccurate hints. Review hints/{HINT_ID}-{BEST_HINT_VERSION}.json before promoting.
```
Ask: `"Promote hints/{HINT_ID}-{BEST_HINT_VERSION}.json as canonical? [Y/n]"`
If Y: run `save_hint_version.py --promote` on the best version.

---

## Final report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HintBook: {HINT_ID}    Doc: {doc_type}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Version  Action    Prompt  Score  Inaccurate
  ──────────────────────────────────────────────
  v1       generate  v3      72.5   4
  v2       patch     v3      84.0   0          ← promoted
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Print: `"Run /status to see all hint pages and score history."`
