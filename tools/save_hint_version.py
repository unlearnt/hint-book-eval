"""
Validate and save a versioned hint page to hints/{hint_id}-{version}.json.
Optionally promote it to hints/{hint_id}.json (the canonical version).

Usage:
  python tools/save_hint_version.py \
    --hint-file /tmp/ca_dl.json \
    --hint-id ca_dl \
    --hint-version v2 \
    [--promote]        # also write hints/ca_dl.json
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *

def validate(data):
    errors, warnings = [], []
    for field in ("id", "title", "sections"):
        if field not in data:
            errors.append(f"Missing field: '{field}'")
    if errors: return errors, warnings

    total, cited = 0, 0
    seen_ids = set()
    for sec in data.get("sections", []):
        for h in sec.get("hints", []):
            total += 1
            if not isinstance(h, list) or len(h) < 4:
                errors.append(f"Invalid hint tuple: {h}"); continue
            hid = h[0]
            if hid in seen_ids: errors.append(f"Duplicate hint ID: {hid}")
            seen_ids.add(hid)
            if len(h) >= 5 and isinstance(h[4], dict) and h[4].get("source"):
                cited += 1
            else:
                warnings.append(f"{hid}: missing citation")

    n_sec = len(data.get("sections", []))
    if n_sec < 8:   warnings.append(f"Only {n_sec} sections (min 8 recommended)")
    if total < 50:  warnings.append(f"Only {total} hints (min 50 recommended)")
    pct_cited = cited / total * 100 if total else 0
    if pct_cited < 90:
        warnings.append(f"{total - cited}/{total} hints missing citations ({100-pct_cited:.0f}%)")

    return errors, warnings

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hint-file",    required=True)
    ap.add_argument("--hint-id",      required=True)
    ap.add_argument("--hint-version", required=True)
    ap.add_argument("--promote",      action="store_true",
                    help="also write hints/{hint_id}.json as the canonical version")
    args = ap.parse_args()

    raw = Path(args.hint_file).read_text()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        err(f"Invalid JSON: {e}"); return

    errors, warnings = validate(data)
    if errors:
        err({"validation_errors": errors, "warnings": warnings}); return

    versioned = HINTS / f"{args.hint_id}-{args.hint_version}.json"
    versioned.write_text(json.dumps(data, indent=2))

    promoted = None
    if args.promote:
        canonical = HINTS / f"{args.hint_id}.json"
        canonical.write_text(json.dumps(data, indent=2))
        promoted = str(canonical)

    total = sum(len(s.get("hints", [])) for s in data.get("sections", []))
    cited = sum(
        1 for s in data.get("sections", [])
        for h in s.get("hints", [])
        if len(h) >= 5 and isinstance(h[4], dict) and h[4].get("source")
    )
    out({
        "saved":        str(versioned),
        "promoted":     promoted,
        "hint_id":      args.hint_id,
        "hint_version": args.hint_version,
        "sections":     len(data.get("sections", [])),
        "hints":        total,
        "cited":        cited,
        "warnings":     warnings,
    })

if __name__ == "__main__":
    main()
