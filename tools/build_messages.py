"""
Format a test case into messages for native (Claude Code) execution.
Outputs JSON with system_prompt, user_message, and image_paths — no LLM is called.

Usage:
  python tools/build_messages.py --case <id> --prompt <vN> --target <assessment|generation> [--run-id <uuid>]
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case",   required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--target", required=True, choices=["assessment","generation"])
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args()

    run_id = args.run_id or str(uuid.uuid4())

    try:
        case   = find_case(args.case, args.target)
        prompt = load_prompt(args.target, args.prompt)
    except FileNotFoundError as e:
        err(str(e)); return

    if not case.get("enabled", True):
        out({"status": "skipped", "reason": "case disabled", "run_id": run_id}); return

    image_paths = []

    if args.target == "generation":
        user_message = fill_template(prompt["user_prefix"], doc_type=case.get("doc_type", ""))

    else:  # assessment
        hp        = load_hint_page(case["hint_page_id"])
        checklist = build_checklist(hp)
        raw_paths = case.get("image_paths", [])
        image_paths = [str((ROOT / p).resolve()) for p in raw_paths]
        n      = len(raw_paths)
        labels = ", ".join(
            f"{i}={'front' if i==0 else 'back' if i==1 else f'img{i}'}"
            for i in range(n)
        )
        bbox_inst = (
            f"REGION ANNOTATION: For NO or WARN answers include bbox [x1,y1,x2,y2] (0–1) "
            f"and imgIdx N ({labels}). For YES/UNVERIFIABLE/CONTEXT omit bbox and imgIdx."
        ) if n > 0 else ""
        guidance = ""
        if case.get("guidance_path"):
            gp = ROOT / case["guidance_path"]
            if gp.exists():
                guidance = f"\nEXPERT FORENSIC GUIDANCE:\n{gp.read_text()}"
        user_message = fill_template(
            prompt["user_prefix"],
            doc_type=hp["title"], guidance=guidance,
            bbox_instructions=bbox_inst, checklist=checklist
        )

    out({
        "run_id":        run_id,
        "system_prompt": prompt["system_prompt"],
        "user_message":  user_message,
        "image_paths":   image_paths,
        "metadata": {
            "case_id":        args.case,
            "target":         args.target,
            "prompt_version": args.prompt,
            "doc_type":       case.get("doc_type") or case.get("hint_page_id"),
        },
    })

if __name__ == "__main__":
    main()
