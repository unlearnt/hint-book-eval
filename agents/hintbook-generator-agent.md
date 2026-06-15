# HintBook Generator Agent

**One job**: Research the document type online, then generate a forensic hint page with per-hint citations backed by real sources. Write it to a file. Then exit.

**Tools**: Bash, Read, WebSearch, WebFetch

---

## Inputs

```
PROMPT_VERSION  — which generation prompt to use (e.g. v2)
DOC_TYPE        — document description (e.g. "California Driver License Gen 3")
HINT_ID         — snake_case ID for the hint page (e.g. ca_dl)
HINT_VERSION    — version being generated (e.g. v1, v2)
OUT_FILE        — absolute path to write the hint page JSON
```

---

## Steps

### 1. Load the prompt

Read `prompts/generation/{PROMPT_VERSION}.md`.

Extract the `## System Prompt` section — these are your generation instructions.
Extract the content inside the ` ``` ` block under `## User Prefix Template` — this is your task template.
Fill `{doc_type}` with `DOC_TYPE`.

### 2. Research authoritative sources

Before generating any hints, search for real, citable sources for this document type. Run targeted searches and fetch the most relevant pages. Focus on:

- AAMVA DL/ID Card Design Standard (current edition)
- State-specific DMV technical specifications or public documentation
- REAL ID Act implementing regulations (6 CFR Part 37)
- ICAO Doc 9303 (for travel documents)
- ISO/IEC 7810, 7816 (card physical standards)

Example searches to run (adapt to the specific `DOC_TYPE`):
```
"{state} driver license security features specifications site:dmv.{state}.gov OR site:aamva.org"
"AAMVA DL/ID card design standard 2020 section security features"
"REAL ID 6 CFR 37 driver license security markings"
```

For each promising search result, fetch the page and extract:
- The source name (official document title + year)
- The relevant section or table reference
- Verbatim or near-verbatim text that supports a forensic claim

Build a `SOURCES` list you will draw from when writing citations. Every citation in the hint page must trace back to something found in this research step. Do not invent quotes — use text you actually fetched.

If a search returns no usable content for a particular feature (e.g. UV patterns are not publicly documented), note it — hints for those features must be marked `plausible` in the citation and the quote should honestly reflect what the source says, not fabricate specifics.

### 3. Generate the hint page

You are the generation model. Follow the system prompt exactly. Produce a complete hint page JSON, drawing citations exclusively from the `SOURCES` you researched in step 2.

**Every hint must be a 5-element array:**
```
[id, question, note_or_null, expect, citation]
```

Where `citation` is:
```json
{"source": "full standard name", "section": "§4.3.2 or Table 3", "quote": "verbatim or near-verbatim text from the source"}
```

- `quote` must be text you actually found — not paraphrased from memory.
- If no fetchable source exists for a hint, include the citation with `"quote": ""` and note in `note` that the claim is based on general AAMVA compliance requirements.
- No hint may be missing its `citation` object entirely.

**Before writing each hint, ask: can this be answered from a flat image scan?**

Do NOT write hints for:
- Card thickness, rigidity, or weight
- Raised/embossed/tactile text features
- Color-shifting ink or OVD tilt effects
- Hologram color shift when tilted
- Laser perforation (requires holding to a light source)
- Delamination or edge smoothness (tactile)
- Anything requiring bending, flexing, or physically manipulating the card

UV features are allowed — they require a UV scanner, not physical manipulation. Frame them as "under UV light".

Write the output:
```bash
cat > {OUT_FILE} << 'HINTEOF'
{YOUR COMPLETE HINT PAGE JSON — valid JSON only, no fences}
HINTEOF
```

### 4. Report

Print a single JSON line:
```json
{"status": "success", "hint_id": "...", "hint_version": "...", "total_hints": N, "cited_hints": N, "sources_found": N, "out_file": "..."}
```

---

## Rules

- Write ONLY the hint page JSON to `OUT_FILE` — no markdown, no explanation.
- Every hint needs a citation object. No exceptions.
- Citations must reference sources you actually fetched — not recalled from training data alone.
- Do not save to `hints/` yourself — the orchestrator handles that.
