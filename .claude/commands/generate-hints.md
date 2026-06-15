Generate a forensic hint page with citations, grade it, and improve the prompt if needed — repeating until quality passes the threshold. Each step runs as a separate agent to keep context lean.

## Arguments
`$ARGUMENTS` format: `<doc_type> [--id <hint_id>] [--threshold N] [--max-revisions N]`

- `doc_type`: document description (e.g. `"California Driver License Gen 3 Real ID"`)
- `--id`: override the snake_case hint ID (default: derived from doc_type)
- `--threshold N`: quality score needed to stop (default: 80)
- `--max-revisions N`: max prompt improvement rounds (default: 3)

---

## Setup

Derive `HINT_ID` from `--id` or from `doc_type` (lowercase, spaces → underscores, strip punctuation).

Find the latest prompt version:
```bash
python tools/sample.py --target generation --status
```
Or simply list `prompts/generation/v*.md` and take the highest version number. Call it `CURRENT_PROMPT`.

Determine the next hint version by checking which `hints/{HINT_ID}-v*.json` files already exist. Start at `v1` if none exist. Call it `HINT_VERSION`.

Set:
```
REVISION = 0
BEST_SCORE = 0
BEST_HINT_VERSION = null
```

---

## Loop: repeat until score ≥ threshold or revision > max-revisions

### Step 1 — Generate

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

---

### Step 2 — Grade

Spawn **HintBook Generator Grader Agent** (`agents/hintbook-generator-grader-agent.md`):
```
HINT_FILE    = {GEN_OUT}
HINT_ID      = {HINT_ID}
HINT_VERSION = {HINT_VERSION}
FEEDBACK_OUT = {FEED_OUT}
```
Wait for: `{quality_score, failed_count}`

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
[{HINT_VERSION}] score={quality_score:.1f}  prompt={CURRENT_PROMPT}  failed={failed_count}
```

Update best:
```
if quality_score > BEST_SCORE:
    BEST_SCORE = quality_score
    BEST_HINT_VERSION = HINT_VERSION
```

Clean up temp files: `rm {GEN_OUT} {FEED_OUT}` (keep the saved `hints/{HINT_ID}-{HINT_VERSION}.json`)

---

### Step 3 — Check threshold

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
✓ Quality threshold met ({quality_score:.1f} ≥ {threshold}, 0 inaccurate)
✓ Promoted hints/{HINT_ID}-{HINT_VERSION}.json → hints/{HINT_ID}.json
```
Go to **Final report**.

If `quality_score >= threshold` AND `inaccurate > 0`:
Print:
```
⚠ Score {quality_score:.1f} ≥ {threshold} but {inaccurate} inaccurate hint(s) remain — continuing.
```
Do NOT promote. Continue to Step 4 (improve).

If `REVISION >= max-revisions`:
Print:
```
Max revisions reached. Best version: {BEST_HINT_VERSION} ({BEST_SCORE:.1f})
```
If the best version has `inaccurate > 0`, warn:
```
⚠ Best version still has inaccurate hints. Review hints/{HINT_ID}-{BEST_HINT_VERSION}.json before promoting.
```
Ask: `"Promote hints/{HINT_ID}-{BEST_HINT_VERSION}.json as canonical? [Y/n]"`
If Y: run save_hint_version.py with `--promote` on the best version.
Go to **Final report**.

---

### Step 4 — Improve

Spawn **HintBook Generator Improver Agent** (`agents/hintbook-generator-improver-agent.md`):
```
CURRENT_PROMPT_VERSION = {CURRENT_PROMPT}
FEEDBACK_FILE          = hints/{HINT_ID}-{HINT_VERSION}-feedback.json
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
CURRENT_PROMPT = new_prompt_version
HINT_VERSION   = v{N+1}   (increment)
REVISION      += 1
```

Repeat loop.

---

## Final report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HintBook: {HINT_ID}    Doc: {doc_type}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Version   Prompt   Score
  ────────────────────────
  v1        v2       72.5
  v2        v3       81.0   ← promoted
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Print: `"Run /status to see all hint pages and score history."`
