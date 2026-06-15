"""
Sample a batch of test cases for a loop iteration.
40% random · 40% worst-scored · 20% never-tested.

Usage:
  python tools/sample.py --target <assessment|generation> --n 5
  python tools/sample.py --target assessment --status   # print score history table
"""
import argparse, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, choices=["assessment","generation"])
    ap.add_argument("--n",      type=int, default=5)
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--seed",   type=int, default=None)
    args = ap.parse_args()

    scores = load_scores().get(args.target, {})

    if args.status:
        rows = [
            {"case_id":cid,"runs":len(s),"best":round(max(s),1),"avg":round(sum(s)/len(s),1)}
            for cid, s in sorted(scores.items()) if s
        ]
        out(rows); return

    cases  = list_cases(args.target)
    if not cases:
        out([]); return

    rng           = random.Random(args.seed)
    never_tested  = [c for c in cases if c["case_id"] not in scores]
    tested        = [c for c in cases if c["case_id"] in scores]
    poorly_scored = sorted(tested, key=lambda c: sum(scores[c["case_id"]])/len(scores[c["case_id"]]))

    n_never = round(args.n * 0.20)
    n_poor  = round(args.n * 0.40)
    n_rand  = args.n - n_never - n_poor

    selected = []
    selected += rng.sample(never_tested, min(n_never, len(never_tested)))
    selected += poorly_scored[:n_poor]
    remaining = [c for c in cases if c not in selected]
    selected += rng.sample(remaining, min(n_rand, len(remaining)))

    # backfill if buckets came up short
    if len(selected) < args.n:
        pool = [c for c in cases if c not in selected]
        selected += rng.sample(pool, min(args.n - len(selected), len(pool)))

    out([c["case_id"] for c in selected[:args.n]])

if __name__ == "__main__":
    main()
