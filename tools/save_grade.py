"""
Persist a pre-computed grade to the run file and update scores.json — no LLM is called.
Used by the native grader agent after scoring a run directly as Claude.

Usage:
  python tools/save_grade.py \
    --run-id UUID --case ID --rubric vN --target TARGET \
    --grade-file /path/to/grade.json   # preferred
    # OR
    --grade '{"criterion_scores":{...},...}'
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id",    required=True)
    ap.add_argument("--case",      required=True)
    ap.add_argument("--rubric",    required=True)
    ap.add_argument("--target",    required=True, choices=["assessment","generation"])
    ap.add_argument("--grade",     default=None, help="inline JSON string")
    ap.add_argument("--grade-file",default=None, help="path to file containing the JSON")
    args = ap.parse_args()

    if args.grade_file:
        raw_grade = Path(args.grade_file).read_text()
    elif args.grade:
        raw_grade = args.grade
    else:
        err("provide --grade or --grade-file"); return

    try:
        run    = load_run(args.case, args.run_id)
        rubric = load_rubric(args.target, args.rubric)
    except FileNotFoundError as e:
        err(str(e)); return

    try:
        data = extract_json(raw_grade)
    except Exception as e:
        err(f"invalid grade JSON: {e}"); return

    scores       = data["criterion_scores"]
    total_weight = sum(c["weight"] for c in rubric["criteria"])
    agg          = sum(v["score"] for v in scores.values()) / total_weight * 100

    grade = {
        "rubric_version":    args.rubric,
        "aggregate_score":   round(agg, 2),
        "criterion_scores":  scores,
        "overall_feedback":  data.get("overall_feedback", ""),
        "improvement_notes": data.get("improvement_notes", ""),
    }
    run["grade"] = grade
    save_run(run)
    record_score(args.target, args.case, agg)

    out({"aggregate_score": agg, "criterion_scores": scores,
         "overall_feedback": grade["overall_feedback"],
         "improvement_notes": grade["improvement_notes"]})

if __name__ == "__main__":
    main()
