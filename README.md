# HintBook Eval Pipeline

Agentic prompt evaluation and optimization for the [HintBook](../hintbook-app) document forensics app. Runs entirely inside Claude Code — no external API keys required.

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

This runs three lean agents in sequence — generate → grade → improve — until the hint page's citation quality passes the threshold. Each version and its score are logged automatically.

---

## How it works

The pipeline has two independent flows:

### Flow 1 — Hint page generation (`/generate-hints`)

Produces a forensic hint page for a specific document type. Runs three single-purpose agents back to back, each doing one job and exiting:

```
/generate-hints "California Driver License Gen 3 Real ID"
```

```
[v1]  hintbook-generator-agent     →  generates hint page with citations
      hintbook-generator-grader-agent  →  grades every hint against its citation
      score=72.5  failed=12

[v2]  hintbook-generator-improver-agent  →  fixes root cause in prompt
      hintbook-generator-agent     →  regenerates with improved prompt
      hintbook-generator-grader-agent  →  re-grades
      score=84.0  ✓ threshold met  →  saved to hints/ca_dl.json
```

Every version is saved (`hints/ca_dl-v1.json`, `hints/ca_dl-v2.json`). Scores are logged to `memory/hint-scores.json`. The version that passes is promoted to `hints/ca_dl.json`.

### Flow 2 — Assessment prompt optimization (`/run-loop`)

Once you have hint pages and real document images, optimize the assessment prompt:

```
/run-loop --native
```

```
iteration 1:  sample cases → run assessment → grade output → score=68.2
              → improve prompts/assessment/v1.md → v2
iteration 2:  score=79.1
              → improve → v3
iteration 3:  score=83.5  ✓ threshold met
```

### Human review (`/review`)

After runs accumulate, annotate grader mistakes and optionally upgrade the rubric:

```
/review assessment --native
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

Generate a hint page for a document type. Runs the three hint-generation agents in sequence, improving the prompt between rounds until quality passes the threshold.

| Argument | Default | Description |
|---|---|---|
| `doc_type` | required | Document description (e.g. `"Florida Driver License"`) |
| `--id` | derived | Override the snake_case hint ID |
| `--threshold N` | `80` | Quality score (0–100) needed to stop |
| `--max-revisions N` | `3` | Max prompt improvement rounds |

Each round: generate → grade → if score < threshold, improve prompt → next round. Versions increment (`v1`, `v2`, …), scores are logged, and the passing version is promoted to `hints/{id}.json`.

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
│   ├── hintbook-generator-agent.md          #   generate hint page with citations
│   ├── hintbook-generator-grader-agent.md   #   grade every hint against its citation
│   ├── hintbook-generator-improver-agent.md #   improve generation prompt from feedback
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
│       └── v2.md                  #   citation-aware generation prompt (current)
│
├── rubrics/
│   ├── assessment/v1.md           #   4-criterion assessment rubric (100 pts)
│   └── generation/
│       ├── v1.md                  #   structural rubric (superseded)
│       └── v2.md                  #   citation-quality rubric (current)
│
├── hints/
│   ├── ca_dl.json                 #   California DL — canonical (promoted version)
│   ├── ca_dl-v1.json              #   California DL — version history
│   └── ca_dl-v2.json              #   ...
│
├── cases/
│   └── assessment/                #   assessment cases (require document images)
│
├── memory/
│   ├── runs/                      #   assessment run + grade files (gitignored)
│   ├── scores.json                #   assessment score history per case
│   ├── hint-scores.json           #   hint generation score history per version
│   └── golden-set.json            #   human-verified anchor cases for rubric validation
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
# → produces hints/ca_dl.json

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
| New assessment case | `/add-case assessment` |
| New prompt target | Add `prompts/{target}/v1.md`, `rubrics/{target}/v1.md`, `cases/{target}/` |
| Change quality threshold | Pass `--threshold N` to `/generate-hints` or edit `>= 80` in `run-loop.md` |
| Change case sampling | Edit the 20/40/40 weights in `tools/sample.py` |
