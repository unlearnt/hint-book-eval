"""
Persist a pre-computed run result to memory/runs/ — no LLM is called.
Used by the native runner agent after generating output directly as Claude.

Usage:
  python tools/save_run.py \
    --run-id UUID --case ID --prompt vN --target TARGET \
    --output-file /path/to/output.json   # preferred (avoids shell quoting)
    # OR
    --output '{"sections":[...]}'        # inline JSON
    [--latency-ms N]
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id",      required=True)
    ap.add_argument("--case",        required=True)
    ap.add_argument("--prompt",      required=True)
    ap.add_argument("--target",      required=True, choices=["assessment","generation"])
    ap.add_argument("--output",      default=None, help="inline JSON string")
    ap.add_argument("--output-file", default=None, help="path to file containing the JSON")
    ap.add_argument("--latency-ms",  type=int, default=0)
    args = ap.parse_args()

    if args.output_file:
        raw = Path(args.output_file).read_text()
    elif args.output:
        raw = args.output
    else:
        err("provide --output or --output-file"); return

    try:
        parsed = extract_json(raw)
    except Exception:
        parsed = None

    run = {
        "run_id":         args.run_id,
        "timestamp":      now_ts(),
        "case_id":        args.case,
        "prompt_version": args.prompt,
        "model":          "claude-code-native",
        "provider":       "claude-code",
        "raw_output":     raw,
        "parsed_output":  parsed,
        "latency_ms":     args.latency_ms,
        "usage":          {},
        "error":          None,
    }
    save_run(run)
    out({"status": "success", "run_id": args.run_id,
         "latency_ms": args.latency_ms, "preview": raw[:300]})

if __name__ == "__main__":
    main()
