# HintBook Eval Pipeline

Agentic prompt evaluation and optimization for the [HintBook](../hintbook-app) document forensics app. Runs entirely inside Claude Code — no external API keys required.

---

## Quick start

```bash
pip install -e .
cd hintbook-eval-pipeline-cc
claude
```

Then in the Claude Code session:

```
/run-loop generation --native
```

That's it. The pipeline samples generation test cases, generates hint pages as Claude, evaluates every hint's citation accuracy as Claude, and writes an improved prompt when scores fall below threshold — all without any API keys.

Once the generation prompt converges, produce a production hint page:

```
/generate-hints "California Driver License Gen 3 Real ID" --save
```

---

## How it works

Three commands, two loops:

| Command | What it does |
|---|---|
| `/run-loop generation` | Optimize the **hint generation prompt** — generates hint pages across doc types, grades every hint's citation accuracy, improves `prompts/generation/vN.md` until convergence |
| `/run-loop assessment` | Optimize the **assessment prompt** — runs against document images, grades output against the rubric, improves `prompts/assessment/vN.md` |
| `/generate-hints` | **Production** — use the best generation prompt to produce a specific hint page with citations, evaluate it, and save to `hints/` |
| `/review` | **Human-gated grader improvement** — annotate grader mistakes, propose a new rubric, validate against golden set |

**Generation loop** (citation-based): sample doc types → generate hint page with citations → evaluate every hint against its citation → if avg quality < 80, improve generation prompt → repeat.

**Assessment loop** (rubric-based): sample image cases → run assessment → grade output → if avg < 80, improve assessment prompt → repeat.

Once `/run-loop generation` converges, run `/generate-hints <doc_type> --save` to produce production-ready hint pages using the optimized prompt. Assessment cases then use those saved hint pages.

---

## Modes

### Native (default recommendation) — no API keys

Pass `--native` and all inference runs inside Claude Code itself. The spawned subagents **are** Claude — no external calls, no keys.

```
/run-loop generation --native
/run-loop assessment --native
/review generation --native
```

Internally, `--native` routes to a different set of agent files (`agents/*-native.md`) that do the work themselves, and thin persistence tools (`save_run.py`, `save_grade.py`, `save_prompt.py`) that only handle file I/O.

### API — evaluate external models

Without `--native`, each role calls a configurable LLM provider. Useful when you want to evaluate a non-Claude model (e.g. Llama on DeepInfra) as the runner while Claude grades it.

```bash
cp .env.example .env
# fill in ANTHROPIC_API_KEY, DEEPINFRA_API_KEY
```

```
/run-loop generation
```

Default model assignments:

| Role | Model | Provider |
|---|---|---|
| Runner | `anthropic/claude-sonnet-4-6` | DeepInfra |
| Grader | `claude-sonnet-4-6` | Anthropic |
| Prompt-Improver | `claude-sonnet-4-6` | Anthropic |
| Grader-Improver | `claude-opus-4-7` | Anthropic |
| Grade-Grader | `claude-sonnet-4-6` | Anthropic |

Override any role in `.env`:

```env
RUNNER_MODEL=anthropic/meta-llama/Llama-3.3-70B-Instruct
RUNNER_PROVIDER=deepinfra
IMPROVER_MODEL=claude-opus-4-8
```

---

## Slash commands

### `/run-loop [target] [options]`

Autonomous prompt-improvement loop.

| Argument | Default | Description |
|---|---|---|
| `target` | `assessment` | `assessment` or `generation` |
| `--native` | off | Run everything inside Claude Code |
| `--batch N` | `5` | Cases per iteration |
| `--patience N` | `3` | Stop after N rounds without improvement |
| `--max-tries N` | `10` | Hard cap on total iterations |
| `--dry-run` | — | Print steps without running any model |

### `/review [target] [options]`

Human-review session for grader outputs, with optional grader upgrade.

| Argument | Default | Description |
|---|---|---|
| `target` | `assessment` | `assessment` or `generation` |
| `--n N` | `10` | Recent graded runs to show |
| `--native` | off | Use native grader for any unscored runs |

For each run: shows model output + grader scores → you mark Correct / Incorrect / Partial / Skip → optionally add to golden set. If ≥ 3 incorrect: offers to run the Grader-Improvement Loop (Grade-Grader diagnosis → Grader-Improver → golden-set validation gate → promote).

### `/status [target]`

Print pipeline state: prompt version table (with best score marked ◀), rubric version table, per-case score history, golden set size, and health warnings.

### `/add-case [target]`

Wizard to add a test case. Generation cases need only a document type string. Assessment cases need image paths, a hint page ID, and a ground-truth verdict. Cases start disabled — set `"enabled": true` in the file when ready.

---

## Directory layout

```
.
├── .claude/commands/              # Slash commands (loaded by Claude Code)
│   ├── run-loop.md                #   /run-loop
│   ├── review.md                  #   /review
│   ├── status.md                  #   /status
│   └── add-case.md                #   /add-case
│
├── agents/                        # Subagent system-prompt definitions
│   ├── runner.md                  #   API mode runner
│   ├── runner-native.md           #   Native mode runner (generates output as Claude)
│   ├── grader.md                  #   API mode grader
│   ├── grader-native.md           #   Native mode grader (scores as Claude)
│   ├── prompt-improver.md         #   API mode prompt-improver
│   ├── prompt-improver-native.md  #   Native mode prompt-improver (writes prompt as Claude)
│   ├── grade-grader.md            #   Audits grader quality, writes diagnosis JSON
│   └── grader-improver.md         #   Proposes and validates new rubric versions
│
├── tools/
│   ├── common.py                  #   Shared utilities — LLM calls, file I/O, versioning
│   │
│   │   # API-mode tools (call external LLMs)
│   ├── run_case.py                #   Run one case via API
│   ├── grade.py                   #   Grade a stored run via API
│   ├── improve_prompt.py          #   Generate next prompt version via API
│   ├── improve_grader.py          #   Generate + validate next rubric via API
│   │
│   │   # Native-mode tools (file I/O only, no LLM)
│   ├── build_messages.py          #   Format a case into the prompt Claude should follow
│   ├── save_run.py                #   Persist a pre-generated run output
│   ├── save_grade.py              #   Persist a pre-generated grade + update scores
│   ├── save_prompt.py             #   Version and save a pre-generated prompt file
│   │
│   └── sample.py                  #   Sample cases for an iteration (20/40/40 strategy)
│
├── prompts/
│   ├── assessment/v1.md           #   Initial assessment prompt
│   └── generation/v1.md           #   Initial generation prompt
│
├── rubrics/
│   ├── assessment/v1.md           #   4-criterion assessment rubric (100 pts)
│   └── generation/v1.md           #   4-criterion generation rubric (100 pts)
│
├── hints/
│   └── ca_dl.json                 #   California DL hint page (14 sections, 56 checks)
│
├── cases/
│   ├── assessment/                #   Assessment cases (require document images)
│   └── generation/                #   6 generation cases — ready to run, no images needed
│
├── memory/
│   ├── runs/                      #   Run + grade JSON files (gitignored)
│   ├── scores.json                #   Score history per case
│   └── golden-set.json            #   Human-verified anchor cases for rubric validation
│
├── .env.example
├── .gitignore
└── pyproject.toml
```

---

## Included test cases

Six **generation** cases ship enabled and ready to run — no images required:

| Case ID | Document |
|---|---|
| `ca-dl-gen` | California Driver License (Gen 3, Real ID) |
| `fl-dl-gen` | Florida Driver License |
| `tx-dl-gen` | Texas Driver License |
| `ny-dl-gen` | New York Driver License |
| `us-passport-gen` | US Passport Book (2021) |
| `us-passport-card-gen` | US Passport Card |

**Assessment** cases need real document images. Add them with `/add-case assessment`.

---

## Extending

| What | How |
|---|---|
| New document type | `/add-case generation` — enter a doc_type description |
| New hint page | Create `hints/{id}.json` (follow `hints/ca_dl.json` schema), reference via `hint_page_id` in assessment cases |
| New prompt target | Add `prompts/{target}/v1.md`, `rubrics/{target}/v1.md`, `cases/{target}/` — tools are target-agnostic |
| Change pass threshold | Edit the `>= 80` value in `.claude/commands/run-loop.md` |
| Change case sampling | Edit the 20/40/40 weights in `tools/sample.py` |
