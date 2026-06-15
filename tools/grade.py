"""
Grade a stored run result and append the grade to memory/runs/{case_id}/{run_id}.json.
Also updates memory/scores.json.

Usage:
  python tools/grade.py --run-id <uuid> --case <id> --rubric <vN> --target <assessment|generation>
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *

_GRADE_SCHEMA = (
    '{"criterion_scores":{'
    '"<crit_id>":{"score":N,"reasoning":"...","citations":["hint S6.1"]}}'
    ',"overall_feedback":"...","improvement_notes":"..."}'
)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id",  required=True)
    ap.add_argument("--case",    required=True)
    ap.add_argument("--rubric",  required=True)
    ap.add_argument("--target",  required=True, choices=["assessment","generation"])
    args = ap.parse_args()

    try:
        run    = load_run(args.case, args.run_id)
        rubric = load_rubric(args.target, args.rubric)
    except FileNotFoundError as e:
        err(e); return

    total_weight = sum(c["weight"] for c in rubric["criteria"])

    # Build hint page context (assessment only)
    hint_block = ""
    try:
        case = find_case(args.case, args.target)
        gt   = case.get("ground_truth", {})
        if args.target == "assessment" and case.get("hint_page_id"):
            hp         = load_hint_page(case["hint_page_id"])
            hint_block = f"\n\n{format_hint_page(hp)}"
    except Exception:
        case, gt = {}, {}

    user_text = (
        f"RUBRIC CRITERIA (total {total_weight} pts):\n{format_criteria(rubric['criteria'])}"
        f"{hint_block}\n\n"
        f"GROUND TRUTH:\n"
        f"- label: {gt.get('label','unknown')}\n"
        f"- expected verdict: {gt.get('verdict','?')}\n"
        f"- check_overrides: {json.dumps(gt.get('check_overrides',{}))}\n\n"
        f"MODEL OUTPUT:\n{run['raw_output']}\n\n"
        f"Return ONLY valid JSON:\n{_GRADE_SCHEMA}"
    )

    content, _ = call_llm(
        [{"role":"user","content":user_text}],
        model=MODELS["grader"]["model"],
        provider=MODELS["grader"]["provider"],
        system=rubric["grader_system_prompt"],
        temperature=0.0, max_tokens=4096
    )
    data   = extract_json(content)
    scores = data["criterion_scores"]   # dict: crit_id -> {score, reasoning, citations}
    agg    = sum(v["score"] for v in scores.values()) / total_weight * 100

    grade = {
        "rubric_version":    args.rubric,
        "aggregate_score":   round(agg, 2),
        "criterion_scores":  scores,
        "overall_feedback":  data.get("overall_feedback",""),
        "improvement_notes": data.get("improvement_notes",""),
    }
    run["grade"] = grade
    save_run(run)
    record_score(args.target, args.case, agg)

    out({"aggregate_score":agg, "criterion_scores":scores,
         "overall_feedback":grade["overall_feedback"],
         "improvement_notes":grade["improvement_notes"]})

if __name__ == "__main__":
    main()
