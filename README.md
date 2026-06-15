# HintBook Eval Pipeline

Agentic prompt evaluation and optimization for the [HintBook](../hintbook-app) document forensics app. Runs entirely inside Claude Code — no external API keys required.

This repo is **source-only**. Hint pages, assessment cases, and memory files are gitignored — every user starts fresh and generates their own data.

---

## Quick start

```bash
pip install -e .
cd hintbook-eval-pipeline-cc
claude
```

Then in the Claude Code session, generate your first hint page:

```
/generate-hints "California Driver License Gen 3 Real ID"
```

This runs three lean agents in sequence — generate → grade → improve — until the hint page passes the quality threshold. Each version and its score are logged locally.

---

## How it works

The pipeline has two independent flows:

### Flow 1 — Hint page generation (`/generate-hints`)

Produces a forensic hint page for a specific document type. Hints are image-checkable only — every check must be answerable from a scanned or photographed front/back image. Physical checks (card thickness, tilt effects, UV features, laser perforation) are excluded.

Three single-purpose agents run back to back, each doing one job and exiting:

```
/generate-hints "California Driver License Gen 3 Real ID"
```

```
[v1]  hintbook-generator-agent
        → searches AAMVA, CFR, DMV pages, ICAO/ISO online
        → generates hint page citing text actually fetched
      hintbook-generator-grader-agent
        → independently fetches each cited source
        → cross-checks every claim against the live page
        score=72.5  inaccurate=4  → below threshold, continuing

[v2]  hintbook-generator-improver-agent  →  fixes root cause in prompt
      hintbook-generator-agent           →  regenerates with improved prompt
      hintbook-generator-grader-agent    →  re-grades
        score=84.0  inaccurate=0  ✓  →  promoted to hints/ca_dl.json
```

Promotion requires **both**: score ≥ threshold **and** zero inaccurate hints. A version that passes the score but still has inaccurate citations keeps improving.

Every version is saved locally (`hints/ca_dl-v1.json`, `hints/ca_dl-v2.json`). Scores are logged to `memory/hint-scores.json`. Neither is committed to git.

### Flow 2 — Assessment prompt optimization (`/run-loop`)

Once you have hint pages and real document images, optimize the assessment prompt:

```
/run-loop --native
```

```
iteration 1:  sample cases → run assessment → grade output → score=68.2
              → improve prompts/assessment/v1.md → v2
iteration 2:  score=79.1  → improve → v3
iteration 3:  score=83.5  ✓ threshold met
```

### Human review (`/review`)

After runs accumulate, annotate grader mistakes and optionally upgrade the rubric:

```
/review --native
```

---

## Modes

### Native — no API keys needed (recommended)

All agents run inside Claude Code itself — no external calls, no keys required.

`/generate-hints` always runs natively. For `/run-loop` and `/review`, pass `--native`:

```
/run-loop --native
/review --native
```

### API — evaluate external models

Without `--native`, each role calls a configurable LLM provider. Useful for evaluating a non-Claude model (e.g. Llama on DeepInfra) as the runner.

```bash
cp .env.example .env
# fill in ANTHROPIC_API_KEY, DEEPINFRA_API_KEY
```

Default model assignments:

| Role | Model | Provider |
|---|---|---|
| Runner | `anthropic/claude-sonnet-4-6` | DeepInfra |
| Grader | `claude-sonnet-4-6` | Anthropic |
| Prompt-Improver | `claude-sonnet-4-6` | Anthropic |
| Grader-Improver | `claude-opus-4-7` | Anthropic |
| Grade-Grader | `claude-sonnet-4-6` | Anthropic |

Override in `.env`:
```env
RUNNER_MODEL=anthropic/meta-llama/Llama-3.3-70B-Instruct
RUNNER_PROVIDER=deepinfra
```

---

## Slash commands

### `/generate-hints <doc_type> [options]`

Generate a hint page for a document type. Searches authoritative sources online, generates hints with real citations, grades every claim against the fetched source, and improves the prompt if needed.

| Argument | Default | Description |
|---|---|---|
| `doc_type` | required | Document description (e.g. `"Florida Driver License"`) |
| `--id` | derived | Override the snake_case hint ID |
| `--threshold N` | `80` | Quality score (0–100) needed to stop |
| `--max-revisions N` | `3` | Max prompt improvement rounds |

Promotion requires score ≥ threshold **and** zero inaccurate hints. If both conditions aren't met, the loop continues improving.

### `/run-loop [options]`

Autonomous assessment prompt-improvement loop.

| Argument | Default | Description |
|---|---|---|
| `--native` | off | Run everything inside Claude Code |
| `--batch N` | `5` | Cases per iteration |
| `--patience N` | `3` | Stop after N rounds without improvement |
| `--max-tries N` | `10` | Hard cap on total iterations |
| `--dry-run` | — | Print steps without running any model |

### `/review [options]`

Human-review session for grader outputs, with optional rubric upgrade.

| Argument | Default | Description |
|---|---|---|
| `--n N` | `10` | Recent graded runs to show |
| `--native` | off | Use native grader for unscored runs |

For each run: shows output + grader scores → mark Correct / Incorrect / Partial / Skip → optionally add to golden set. If ≥ 3 incorrect: Grade-Grader diagnosis → Grader-Improver → golden-set validation gate → promote new rubric.

### `/status`

Print pipeline state: prompt version table, rubric versions, per-case score history, hint-scores log, golden set size, and health warnings.

### `/add-case`

Wizard to add an assessment case. Asks for a case ID, the hint page ID to use (must already exist in `hints/`), image paths, and a ground-truth verdict. The case is saved with `"enabled": false` — open the file and flip it to `true` once you've verified the image paths.

---

## Directory layout

```
.
├── .claude/commands/
│   ├── generate-hints.md          #   /generate-hints
│   ├── run-loop.md                #   /run-loop
│   ├── review.md                  #   /review
│   ├── status.md                  #   /status
│   └── add-case.md                #   /add-case
│
├── agents/
│   │   # Hint generation (3 single-purpose agents)
│   ├── hintbook-generator-agent.md          #   search web → generate hint page with real citations
│   ├── hintbook-generator-grader-agent.md   #   fetch cited sources → verify every claim online
│   ├── hintbook-generator-improver-agent.md #   improve generation prompt from grader feedback
│   │
│   │   # Assessment loop — native mode
│   ├── runner-native.md           #   run assessment case as Claude
│   ├── grader-native.md           #   grade assessment output as Claude
│   ├── prompt-improver-native.md  #   improve assessment prompt as Claude
│   │
│   │   # Assessment loop — API mode
│   ├── runner.md
│   ├── grader.md
│   ├── prompt-improver.md
│   │
│   │   # Grader improvement (human-gated)
│   ├── grade-grader.md            #   audit grader quality, write diagnosis
│   └── grader-improver.md         #   propose and validate new rubric
│
├── tools/
│   ├── common.py                  #   shared utilities — LLM calls, file I/O, versioning
│   │
│   │   # Hint generation tools
│   ├── save_hint_version.py       #   save hints/{id}-{vN}.json; --promote writes canonical
│   ├── record_hint_score.py       #   append version score to memory/hint-scores.json
│   │
│   │   # Assessment loop — API-mode tools (call external LLMs)
│   ├── run_case.py
│   ├── grade.py
│   ├── improve_prompt.py
│   ├── improve_grader.py
│   │
│   │   # Assessment loop — native tools (file I/O only, no LLM)
│   ├── build_messages.py          #   format a case into the task Claude should perform
│   ├── save_run.py                #   persist a pre-generated run output
│   ├── save_grade.py              #   persist a pre-generated grade + update scores
│   ├── save_prompt.py             #   version and save a pre-generated prompt file
│   │
│   └── sample.py                  #   sample cases (20% never-tested, 40% worst, 40% random)
│
├── prompts/
│   ├── assessment/v1.md           #   initial assessment prompt
│   └── generation/
│       ├── v1.md                  #   initial generation prompt
│       ├── v2.md                  #   citation-aware generation prompt
│       └── v3.md                  #   image-checkable hints only (current)
│
├── rubrics/
│   ├── assessment/v1.md           #   4-criterion assessment rubric (100 pts)
│   └── generation/
│       ├── v1.md                  #   structural rubric (superseded)
│       ├── v2.md                  #   citation-quality rubric (superseded)
│       └── v3.md                  #   adds image_checkability criterion (current)
│
├── hints/                         #   gitignored — generated locally per user
├── cases/assessment/              #   gitignored — user-specific cases with local image paths
│
├── memory/                        #   gitignored — all runtime logs and run files
│
├── .env.example
├── .gitignore
└── pyproject.toml
```

---

## Typical workflow

```
# 1. Generate and refine a hint page (no images needed)
/generate-hints "California Driver License Gen 3 Real ID"
# → produces hints/ca_dl.json locally (gitignored)

# 2. Repeat for other document types
/generate-hints "Florida Driver License"
/generate-hints "US Passport Book 2021"

# 3. Place your document images somewhere under the project root
#    e.g. data/images/ca_dl_front.jpg, data/images/ca_dl_back.jpg

# 4. Add an assessment case linking an image to a hint page
/add-case
# The wizard asks for:
#   - case_id          e.g. ca-dl-genuine-001
#   - hint_page_id     e.g. ca_dl  (matches hints/ca_dl.json)
#   - image_paths      e.g. data/images/ca_dl_front.jpg
#   - ground_truth     genuine / forged + expected verdict
# Then open cases/assessment/{case_id}.json and set "enabled": true

# 5. Optimize the assessment prompt against your cases
/run-loop --native

# 6. Review grader quality and seed the golden set
/review --native --n 10

# 7. Check overall pipeline state
/status
```

---

## Extending

| What | How |
|---|---|
| New document type | `/generate-hints "<doc_type>"` |
| New assessment case | `/add-case` |
| Change quality threshold | Pass `--threshold N` to `/generate-hints` |
| Change case sampling | Edit the 20/40/40 weights in `tools/sample.py` |
