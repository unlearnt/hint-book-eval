"""
Generate the next rubric version from Grade-Grader diagnosis and validate against golden set.
Saves to rubrics/{target}/vN.md only if golden-set accuracy >= threshold.

Usage:
  python tools/improve_grader.py --current <vN> --target <assessment|generation> --diagnosis <path.json> [--min-accuracy 0.80]
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *

_SYSTEM = """\
You are an expert at designing AI grader rubrics for document forensics evaluations.

Given the current rubric and a diagnosis of its failures, produce an improved version.

Constraints:
- Criterion IDs must not change (score history references them).
- Weights must still sum to 100.
- You may reword descriptions, adjust weights, or expand grading guides.

Return ONLY valid JSON:
{
  "grader_system_prompt": "...",
  "criteria": [{"id":"...","weight":N,"description":"...","grading_guide":"..."}],
  "change_summary": ["bullet 1"]
}
"""

def _grade_run(raw_output, rubric, case_gt):
    """Run the grader LLM on a single output. Returns aggregate_score."""
    total = sum(c["weight"] for c in rubric["criteria"])
    user_text = (
        f"RUBRIC:\n{format_criteria(rubric['criteria'])}\n\n"
        f"GROUND TRUTH: {json.dumps(case_gt)}\n\n"
        f"OUTPUT:\n{raw_output}\n\n"
        'Return JSON: {"criterion_scores":{"<id>":{"score":N,"reasoning":""}}, "overall_feedback":"","improvement_notes":""}'
    )
    try:
        content, _ = call_llm(
            [{"role":"user","content":user_text}],
            model=MODELS["grader"]["model"], provider=MODELS["grader"]["provider"],
            system=rubric["grader_system_prompt"], temperature=0.0, max_tokens=4096
        )
        data = extract_json(content)
        return sum(v["score"] for v in data["criterion_scores"].values()) / total * 100
    except Exception:
        return None

def _golden_accuracy(rubric, tolerance=10.0):
    golden = load_golden()
    if not golden: return 1.0
    hits = 0
    for gc in golden:
        predicted = _grade_run(gc["raw_output"], rubric, {})
        if predicted is not None and abs(predicted - gc["correct_aggregate"]) <= tolerance:
            hits += 1
    return hits / len(golden)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--current",       required=True)
    ap.add_argument("--target",        required=True, choices=["assessment","generation"])
    ap.add_argument("--diagnosis",     required=True)
    ap.add_argument("--min-accuracy",  type=float, default=0.80)
    args = ap.parse_args()

    rubric    = load_rubric(args.target, args.current)
    diagnosis = json.loads(Path(args.diagnosis).read_text())

    # Format diagnosis for the LLM
    issues = "\n".join(
        f"- [{d.get('type')}] {d.get('criterion_id','n/a')}: {d.get('description')} "
        f"→ fix: {d.get('fix_suggestion')}"
        for d in diagnosis.get("diagnosis", [])
    )
    golden_sample = "\n".join(
        f"- case={g['case_id']}: correct={g['correct_aggregate']:.1f}"
        for g in load_golden()[:8]
    ) or "(empty)"

    user_text = (
        f"CURRENT GRADER SYSTEM PROMPT:\n{rubric['grader_system_prompt']}\n\n"
        f"CURRENT CRITERIA:\n{format_criteria(rubric['criteria'])}\n\n"
        f"DIAGNOSIS:\n{issues}\n\n"
        f"GOLDEN SET SAMPLE:\n{golden_sample}\n\n"
        "Return the improved rubric as JSON."
    )
    content, _ = call_llm(
        [{"role":"user","content":user_text}],
        model=MODELS["grader_improver"]["model"], provider=MODELS["grader_improver"]["provider"],
        system=_SYSTEM, temperature=0.2, max_tokens=8192
    )
    data    = extract_json(content)
    summary = data.get("change_summary", [])

    # Build candidate rubric dict for validation
    candidate = {
        "grader_system_prompt": data["grader_system_prompt"],
        "criteria":             data["criteria"],
    }

    # Validate against golden set
    current_acc   = _golden_accuracy(rubric)
    candidate_acc = _golden_accuracy(candidate)

    if candidate_acc < args.min_accuracy or candidate_acc < current_acc:
        out({"promoted":False,"candidate_accuracy":candidate_acc,
             "current_accuracy":current_acc,"reason":"Did not beat threshold or current accuracy"})
        return

    # Promote
    existing = list_versions(RUBRICS, args.target)
    version  = next_version(existing)
    notes    = "; ".join(summary)[:120]

    # Write markdown rubric
    crit_md = ""
    for c in data["criteria"]:
        crit_md += f"\n### {c['id']} — {c['weight']} pts\n\n**What it measures:** {c['description']}\n\n{c['grading_guide']}\n"

    path = RUBRICS / args.target / f"{version}.md"
    path.write_text(
        f"---\nversion: {version}\nparent: {args.current}\ntarget: {args.target}\n"
        f'created_at: "{now_ts()[:10]}"\ngolden_set_accuracy: {candidate_acc:.4f}\n'
        f'notes: "{notes}"\n---\n\n'
        f"## Grader System Prompt\n\n{data['grader_system_prompt']}\n\n"
        f"---\n\n## Criteria\n{crit_md}"
    )
    out({"promoted":True,"new_version":version,"change_summary":summary,
         "current_accuracy":current_acc,"candidate_accuracy":candidate_acc})

if __name__ == "__main__":
    main()
