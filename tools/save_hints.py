"""
Validate and save a generated hint page to hints/{id}.json.

Validates:
  - Valid JSON with required fields (id, title, sections)
  - All hints are 5-element arrays with a citation object
  - No duplicate hint IDs

Usage:
  python tools/save_hints.py --hint-file /tmp/hint_page.json [--force]
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *

def validate_hint_page(data):
    errors = []
    warnings = []

    for field in ("id", "title", "sections"):
        if field not in data:
            errors.append(f"Missing required field: '{field}'")

    if errors:
        return errors, warnings

    all_hint_ids = []
    total = 0
    cited = 0
    missing_citation = []

    for sec in data.get("sections", []):
        sec_id = sec.get("id", "?")
        for hint in sec.get("hints", []):
            total += 1
            if not isinstance(hint, list) or len(hint) < 4:
                errors.append(f"Hint in {sec_id} is not a valid array: {hint}")
                continue
            hint_id = hint[0]
            all_hint_ids.append(hint_id)
            if len(hint) >= 5 and isinstance(hint[4], dict):
                c = hint[4]
                if c.get("source") and c.get("quote"):
                    cited += 1
                else:
                    missing_citation.append(hint_id)
                    warnings.append(f"{hint_id}: citation is incomplete (missing source or quote)")
            else:
                missing_citation.append(hint_id)
                warnings.append(f"{hint_id}: no citation")

    # Check for duplicate IDs
    seen = set()
    for hid in all_hint_ids:
        if hid in seen:
            errors.append(f"Duplicate hint ID: {hid}")
        seen.add(hid)

    n_sec = len(data.get("sections", []))
    if n_sec < 8:
        warnings.append(f"Only {n_sec} sections (minimum 8 recommended)")
    if total < 50:
        warnings.append(f"Only {total} hints (minimum 50 recommended)")
    if missing_citation:
        pct = len(missing_citation) / total * 100 if total else 0
        warnings.append(f"{len(missing_citation)}/{total} hints ({pct:.0f}%) are missing citations")

    return errors, warnings

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hint-file", required=True, help="path to hint page JSON")
    ap.add_argument("--force",     action="store_true", help="overwrite existing file")
    args = ap.parse_args()

    raw = Path(args.hint_file).read_text()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        err(f"Invalid JSON: {e}"); return

    errors, warnings = validate_hint_page(data)
    if errors:
        err({"validation_errors": errors, "warnings": warnings}); return

    hint_id = data["id"]
    dest = HINTS / f"{hint_id}.json"

    if dest.exists() and not args.force:
        err(f"{dest} already exists. Use --force to overwrite."); return

    dest.write_text(json.dumps(data, indent=2))

    total  = sum(len(s.get("hints", [])) for s in data.get("sections", []))
    cited  = sum(
        1 for s in data.get("sections", [])
        for h in s.get("hints", [])
        if len(h) >= 5 and isinstance(h[4], dict) and h[4].get("source")
    )
    out({
        "saved":    str(dest),
        "hint_id":  hint_id,
        "sections": len(data.get("sections", [])),
        "hints":    total,
        "cited":    cited,
        "warnings": warnings,
    })

if __name__ == "__main__":
    main()
