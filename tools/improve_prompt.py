"""
Generate the next prompt version from grader feedback and save to prompts/{target}/vN.md.

Usage:
  python tools/improve_prompt.py --current <vN> --target <assessment|generation> --failing-runs <id1> [id2 ...]
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *

_SYSTEM = """\
You are an expert prompt engineer for document forensics AI systems.

You receive a prompt and grader feedback from failing runs. Produce a targeted improved version.

Rules:
- Minimal edits: change only what the feedback identifies as wrong.
- Keep {doc_type}, {guidance}, {bbox_instructions}, {checklist} placeholders exactly.
- Do NOT change the JSON output schema at the end of the user_prefix.
- Explain each change in change_summary.

Return ONLY valid JSON:
{"system_prompt":"...","user_prefix":"...","change_summary":["bullet 1","bullet 2"]}
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--current",       required=True)
    ap.add_argument("--target",        required=True, choices=["assessment","generation"])
    ap.add_argument("--failing-runs",  nargs="+", default=[])
    args = ap.parse_args()

    prompt = load_prompt(args.target, args.current)

    # Collect improvement_notes from failing runs
    feedback = []
    for run_id in args.failing_runs[:8]:
        for r in all_runs(with_grade=True):
            if r["run_id"] == run_id:
                g = r.get("grade", {})
                feedback.append(
                    f"run={run_id[:8]} case={r['case_id']} score={g.get('aggregate_score',0):.1f}\n"
                    f"  feedback: {g.get('improvement_notes','—')}"
                )
                break
    feedback_text = "\n\n".join(feedback) or "(none)"

    user_text = (
        f"CURRENT SYSTEM PROMPT:\n{prompt['system_prompt']}\n\n"
        f"CURRENT USER PREFIX:\n{prompt['user_prefix']}\n\n"
        f"GRADER FEEDBACK:\n{feedback_text}\n\n"
        "Return the improved prompt as JSON."
    )
    content, _ = call_llm(
        [{"role":"user","content":user_text}],
        model=MODELS["prompt_improver"]["model"],
        provider=MODELS["prompt_improver"]["provider"],
        system=_SYSTEM, temperature=0.3, max_tokens=8192
    )
    data    = extract_json(content)
    summary = data.get("change_summary", [])

    existing = list_versions(PROMPTS, args.target)
    version  = next_version(existing)
    notes    = "; ".join(summary)[:120]

    path = PROMPTS / args.target / f"{version}.md"
    path.write_text(
        f"---\nversion: {version}\nparent: {args.current}\ntarget: {args.target}\n"
        f'created_at: "{now_ts()[:10]}"\naggregate_score: null\nnotes: "{notes}"\n---\n\n'
        f"## System Prompt\n\n{data['system_prompt']}\n\n---\n\n"
        f"## User Prefix Template\n\n"
        "> Placeholders: `{doc_type}` `{guidance}` `{bbox_instructions}` `{checklist}`\n\n"
        f"```\n{data['user_prefix']}\n```\n"
    )
    out({"new_version":version,"change_summary":summary,"path":str(path)})

if __name__ == "__main__":
    main()
