"""
Shared foundation for all eval-pipeline tools.
Every tool does: from common import *
"""
import base64
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT      = Path(__file__).parent.parent
TOOLS     = ROOT / "tools"
AGENTS    = ROOT / "agents"
PROMPTS   = ROOT / "prompts"
RUBRICS   = ROOT / "rubrics"
HINTS     = ROOT / "hints"
CASES     = ROOT / "cases"
MEMORY    = ROOT / "memory"
RUNS      = MEMORY / "runs"
SCORES    = MEMORY / "scores.json"
GOLDEN    = MEMORY / "golden-set.json"

load_dotenv(ROOT / ".env")
RUNS.mkdir(parents=True, exist_ok=True)

# ── Model defaults ─────────────────────────────────────────────────────────────
MODELS = {
    "runner":           {"model": os.getenv("RUNNER_MODEL",   "anthropic/claude-sonnet-4-6"), "provider": os.getenv("RUNNER_PROVIDER",   "deepinfra")},
    "grader":           {"model": os.getenv("GRADER_MODEL",   "claude-sonnet-4-6"),           "provider": os.getenv("GRADER_PROVIDER",   "anthropic")},
    "prompt_improver":  {"model": os.getenv("IMPROVER_MODEL", "claude-sonnet-4-6"),           "provider": os.getenv("IMPROVER_PROVIDER", "anthropic")},
    "grader_improver":  {"model": os.getenv("GRADER_IMPROVER_MODEL", "claude-opus-4-7"),      "provider": os.getenv("GRADER_IMPROVER_PROVIDER", "anthropic")},
    "grade_grader":     {"model": os.getenv("GRADE_GRADER_MODEL", "claude-sonnet-4-6"),       "provider": os.getenv("GRADE_GRADER_PROVIDER", "anthropic")},
}

# ── LLM API ───────────────────────────────────────────────────────────────────
_PROVIDER_CFG = {
    "deepinfra":  {"base": "https://api.deepinfra.com/v1/openai", "key": "DEEPINFRA_API_KEY"},
    "openrouter": {"base": "https://openrouter.ai/api/v1",        "key": "OPENROUTER_API_KEY"},
}

def call_llm(messages, *, model, provider, system=None, temperature=0.1, max_tokens=8192):
    """Dispatch to Anthropic or OpenAI-compat. Returns (content, usage_dict)."""
    if provider == "anthropic":
        return _call_anthropic(messages, model=model, system=system,
                               temperature=temperature, max_tokens=max_tokens)
    return _call_openai(messages, model=model, provider=provider,
                        system=system, temperature=temperature, max_tokens=max_tokens)

def _call_anthropic(messages, *, model, system, temperature, max_tokens):
    import anthropic as _ant
    client = _ant.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    kwargs = dict(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
    if system:
        kwargs["system"] = system
    r = client.messages.create(**kwargs)
    return r.content[0].text, {"input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens}

def _call_openai(messages, *, model, provider, system, temperature, max_tokens):
    import httpx
    cfg = _PROVIDER_CFG[provider]
    key = os.environ.get(cfg["key"], "")
    if not key:
        raise ValueError(f"Missing env var: {cfg['key']}")
    hdrs = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if provider == "openrouter":
        hdrs |= {"HTTP-Referer": "https://github.com/hintbook-eval", "X-Title": "HintBook Eval"}
    msgs = ([{"role": "system", "content": system}] if system else []) + list(messages)
    with httpx.Client(timeout=180) as c:
        r = c.post(f"{cfg['base']}/chat/completions", headers=hdrs,
                   json={"model": model, "messages": msgs, "temperature": temperature, "max_tokens": max_tokens})
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"] or "", data.get("usage", {})

def extract_json(text):
    """Extract first JSON object from text (tolerant of markdown fences)."""
    s, e = text.find("{"), text.rfind("}")
    if s == -1: raise ValueError("No JSON object in response")
    raw = re.sub(r",(\s*[}\]])", r"\1", text[s:e+1])
    return json.loads(raw)

# ── Image utilities ────────────────────────────────────────────────────────────
def img_to_data_url(path, max_px=1024, quality=92):
    """Load image, resize to max_px longest side, return data URL string."""
    from PIL import Image
    img = Image.open(path).convert("RGB")
    w, h = img.size
    if max(w, h) > max_px:
        r = max_px / max(w, h)
        img = img.resize((int(w*r), int(h*r)), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, "JPEG", quality=quality)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/jpeg;base64,{b64}"

# ── Prompt / rubric markdown loader ───────────────────────────────────────────
def _parse_md(path):
    """Parse YAML front matter + markdown body. Returns (meta, body)."""
    text = Path(path).read_text()
    if not text.startswith("---"):
        return {}, text
    end  = text.index("---", 3)
    meta = {}
    for line in text[3:end].splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            v = v.strip().strip('"').strip("'")
            meta[k.strip()] = None if v == "null" else v
    return meta, text[end+3:].strip()

def _section(body, heading):
    """Extract text under a ## heading."""
    m = re.search(rf"##\s+{re.escape(heading)}\s*\n(.*?)(?=\n##\s|\Z)", body, re.DOTALL)
    return m.group(1).strip() if m else ""

def _fence_content(text):
    """Return content inside first ``` block, or text stripped of blockquotes."""
    m = re.search(r"```[^\n]*\n(.*?)```", text, re.DOTALL)
    if m: return m.group(1).strip()
    return "\n".join(l for l in text.splitlines() if not l.startswith(">")).strip()

def load_prompt(target, version):
    """Load prompts/{target}/{version}.md → {version, system_prompt, user_prefix, ...}."""
    meta, body = _parse_md(PROMPTS / target / f"{version}.md")
    return {**meta,
            "system_prompt": _section(body, "System Prompt"),
            "user_prefix":   _fence_content(_section(body, "User Prefix Template"))}

def load_rubric(target, version):
    """Load rubrics/{target}/{version}.md → {version, grader_system_prompt, criteria [...]}."""
    meta, body = _parse_md(RUBRICS / target / f"{version}.md")
    grader_sys = _section(body, "Grader System Prompt")
    # Parse criterion sections: ### crit_id — N pts
    criteria = []
    for m in re.finditer(r"###\s+(\w+)\s+—\s+(\d+)\s+pts\s*\n(.*?)(?=\n###\s|\Z)", body, re.DOTALL):
        crit_id, weight, content = m.group(1), int(m.group(2)), m.group(3).strip()
        desc_m = re.search(r"\*\*What it measures:\*\*\s*(.*?)(?=\n\n|\Z)", content, re.DOTALL)
        criteria.append({
            "id":            crit_id,
            "weight":        weight,
            "description":   desc_m.group(1).strip() if desc_m else "",
            "grading_guide": content,
        })
    return {**meta, "grader_system_prompt": grader_sys, "criteria": criteria}

def list_versions(base_dir, target, ext=".md"):
    """Return sorted list of vN versions in base_dir/target/."""
    d = Path(base_dir) / target
    if not d.exists(): return []
    return sorted([p.stem for p in d.glob(f"v*{ext}") if p.stem[1:].isdigit()],
                  key=lambda v: int(v[1:]))

def next_version(existing):
    if not existing: return "v1"
    return f"v{max(int(v[1:]) for v in existing) + 1}"

# ── Hint page loader ──────────────────────────────────────────────────────────
def load_hint_page(hint_page_id):
    return json.loads((HINTS / f"{hint_page_id}.json").read_text())

def build_checklist(hint_page):
    lines = []
    for sec in hint_page["sections"]:
        lines.append(f"[{sec['id']}] {sec['title']}")
        for h in sec["hints"]:
            note = f" [{h[2]}]" if len(h) > 2 and h[2] else ""
            lines.append(f"  {h[0]}: {h[1]}{note}")
        lines.append("")
    return "\n".join(lines).strip()

# ── Case loader ───────────────────────────────────────────────────────────────
def find_case(case_id, target):
    for p in (CASES / target).glob("*.json"):
        data = json.loads(p.read_text())
        items = data if isinstance(data, list) else [data]
        for item in items:
            if item.get("id") == case_id or item.get("case_id") == case_id:
                return item
    raise FileNotFoundError(f"Case '{case_id}' not found in cases/{target}/")

def list_cases(target):
    cases = []
    for p in (CASES / target).glob("*.json"):
        data = json.loads(p.read_text())
        items = data if isinstance(data, list) else [data]
        cases.extend(i for i in items if i.get("enabled", True))
    return cases

# ── Run result I/O ────────────────────────────────────────────────────────────
def new_run_id(): return str(uuid.uuid4())
def now_ts():    return datetime.now(timezone.utc).isoformat()

def save_run(run: dict):
    d = RUNS / run["case_id"]
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{run['run_id']}.json").write_text(json.dumps(run, indent=2))

def load_run(case_id, run_id):
    return json.loads((RUNS / case_id / f"{run_id}.json").read_text())

def all_runs(with_grade=False):
    results = []
    if not RUNS.exists(): return results
    for case_dir in RUNS.iterdir():
        if not case_dir.is_dir(): continue
        for p in sorted(case_dir.glob("*.json"), reverse=True):
            try:
                r = json.loads(p.read_text())
                if with_grade and "grade" not in r: continue
                results.append(r)
            except Exception: pass
    return sorted(results, key=lambda r: r.get("timestamp",""), reverse=True)

# ── Score history ─────────────────────────────────────────────────────────────
def load_scores():
    if not SCORES.exists(): return {}
    return json.loads(SCORES.read_text())

def save_scores(data):
    SCORES.write_text(json.dumps(data, indent=2))

def record_score(target, case_id, score):
    data = load_scores()
    data.setdefault(target, {}).setdefault(case_id, []).append(score)
    save_scores(data)

# ── Golden set ────────────────────────────────────────────────────────────────
def load_golden():
    if not GOLDEN.exists(): return []
    return json.loads(GOLDEN.read_text())

def save_golden(cases):
    GOLDEN.write_text(json.dumps(cases, indent=2))

def add_golden(entry: dict):
    cases = load_golden()
    cases = [c for c in cases if c.get("run_id") != entry["run_id"]]
    cases.append(entry)
    save_golden(cases)

# ── Hint page formatting (for grader context) ─────────────────────────────────
def format_hint_page(hint_page):
    lines = [f"HINT PAGE: {hint_page['title']}"]
    for sec in hint_page["sections"]:
        lines.append(f"\n[{sec['id']}] {sec['title']}")
        for h in sec["hints"]:
            note   = f" [{h[2]}]" if len(h) > 2 and h[2] else ""
            expect = f"  (expect: {h[3]})" if len(h) > 3 else ""
            lines.append(f"  {h[0]}: {h[1]}{note}{expect}")
    return "\n".join(lines)

def format_criteria(criteria):
    return "\n".join(
        f"• [{c['id']}] max {c['weight']} pts\n  {c['description']}"
        for c in criteria
    )

def fill_template(template, **kwargs):
    """Safe placeholder substitution. Only replaces {known_key}; leaves other {braces} alone."""
    for k, v in kwargs.items():
        template = template.replace("{" + k + "}", v)
    return template

# ── Quick print helpers ───────────────────────────────────────────────────────
def out(data):
    """Print data as JSON to stdout (consumed by agent)."""
    print(json.dumps(data, indent=2, default=str))

def err(msg):
    print(json.dumps({"error": str(msg)}), file=sys.stderr)
    sys.exit(1)
