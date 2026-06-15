"""
Record a hint page version score to memory/hint-scores.json.

Usage:
  python tools/record_hint_score.py \
    --hint-id ca_dl \
    --hint-version v1 \
    --prompt-version v2 \
    --score 72.5 \
    --accurate 35 --plausible 5 --inaccurate 3 --unsupported 2 --missing 5 \
    --total 50
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *

HINT_SCORES = MEMORY / "hint-scores.json"

def load_hint_scores():
    if not HINT_SCORES.exists(): return {}
    return json.loads(HINT_SCORES.read_text())

def save_hint_scores(data):
    HINT_SCORES.write_text(json.dumps(data, indent=2))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hint-id",       required=True)
    ap.add_argument("--hint-version",  required=True)
    ap.add_argument("--prompt-version",required=True)
    ap.add_argument("--score",         required=True, type=float)
    ap.add_argument("--accurate",      type=int, default=0)
    ap.add_argument("--plausible",     type=int, default=0)
    ap.add_argument("--inaccurate",    type=int, default=0)
    ap.add_argument("--unsupported",   type=int, default=0)
    ap.add_argument("--missing",       type=int, default=0)
    ap.add_argument("--total",         type=int, default=0)
    args = ap.parse_args()

    data = load_hint_scores()
    data.setdefault(args.hint_id, [])

    entry = {
        "hint_version":   args.hint_version,
        "prompt_version": args.prompt_version,
        "score":          round(args.score, 2),
        "accurate":       args.accurate,
        "plausible":      args.plausible,
        "inaccurate":     args.inaccurate,
        "unsupported":    args.unsupported,
        "missing":        args.missing,
        "total_hints":    args.total,
        "timestamp":      now_ts(),
    }
    # replace existing entry for same hint_version if re-run
    data[args.hint_id] = [e for e in data[args.hint_id] if e["hint_version"] != args.hint_version]
    data[args.hint_id].append(entry)
    data[args.hint_id].sort(key=lambda e: int(e["hint_version"][1:]))
    save_hint_scores(data)

    out({"recorded": True, "hint_id": args.hint_id, "hint_version": args.hint_version,
         "score": args.score})

if __name__ == "__main__":
    main()
