"""
Save a hint evaluation report to memory/hint-evals/{hint_id}-{timestamp}.json.

Usage:
  python tools/save_hint_eval.py --hint-id <id> --eval-file /tmp/eval.json
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *

HINT_EVALS = MEMORY / "hint-evals"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hint-id",   required=True)
    ap.add_argument("--eval-file", required=True)
    args = ap.parse_args()

    raw = Path(args.eval_file).read_text()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        err(f"Invalid JSON: {e}"); return

    HINT_EVALS.mkdir(parents=True, exist_ok=True)
    ts   = now_ts().replace(":", "-").replace(".", "-")[:19]
    dest = HINT_EVALS / f"{args.hint_id}-{ts}.json"
    dest.write_text(json.dumps(data, indent=2))

    out({
        "saved":         str(dest),
        "hint_id":       args.hint_id,
        "quality_score": data.get("quality_score"),
        "total_hints":   data.get("total_hints"),
        "accurate":      data.get("accurate"),
        "failed_count":  data.get("failed_count", 0),
    })

if __name__ == "__main__":
    main()
