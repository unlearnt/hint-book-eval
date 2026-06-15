"""
Version and save a pre-generated prompt to prompts/{target}/vN.md — no LLM is called.
Used by the native prompt-improver agent after producing a new prompt directly as Claude.

Usage:
  python tools/save_prompt.py \
    --parent vN --target TARGET --notes 'summary' \
    --content-file /path/to/prompt_body.md
    # The content file must contain the full prompt body (system + user prefix sections).
    # save_prompt.py wraps it in the YAML front matter and writes the versioned file.
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parent",       required=True)
    ap.add_argument("--target",       required=True, choices=["assessment","generation"])
    ap.add_argument("--notes",        default="")
    ap.add_argument("--content-file", required=True, help="file with the full prompt body")
    args = ap.parse_args()

    body = Path(args.content_file).read_text()

    existing = list_versions(PROMPTS, args.target)
    version  = next_version(existing)
    notes    = args.notes[:120].replace('"', "'")

    path = PROMPTS / args.target / f"{version}.md"
    path.write_text(
        f'---\nversion: {version}\nparent: {args.parent}\ntarget: {args.target}\n'
        f'created_at: "{now_ts()[:10]}"\naggregate_score: null\nnotes: "{notes}"\n---\n\n'
        + body
    )
    out({"new_version": version, "path": str(path)})

if __name__ == "__main__":
    main()
