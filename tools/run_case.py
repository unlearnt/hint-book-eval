"""
Execute one test case against the target LLM and save the result to memory/runs/.

Usage:
  python tools/run_case.py --case <id> --prompt <vN> --target <assessment|generation> [--run-id <uuid>] [--model <id>] [--provider <name>]
"""
import argparse, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *

def build_messages(prompt, case, target):
    if target == "generation":
        user_text = fill_template(prompt["user_prefix"], doc_type=case.get("doc_type",""))
        return [{"role":"user","content":user_text}]

    # Assessment: load hint page + images
    hp        = load_hint_page(case["hint_page_id"])
    checklist = build_checklist(hp)
    images    = [img_to_data_url(ROOT / p) for p in case.get("image_paths",[])]
    n         = len(images)
    labels    = ", ".join(f"{i}={'front' if i==0 else 'back' if i==1 else f'img{i}'}" for i in range(n))
    bbox_inst = (
        f"REGION ANNOTATION: For NO or WARN answers include bbox [x1,y1,x2,y2] (0–1) and imgIdx N ({labels}). "
        "For YES/UNVERIFIABLE/CONTEXT omit bbox and imgIdx."
    )
    guidance = ""
    if case.get("guidance_path"):
        gp = ROOT / case["guidance_path"]
        if gp.exists(): guidance = f"\nEXPERT FORENSIC GUIDANCE:\n{gp.read_text()}"

    user_text = fill_template(
        prompt["user_prefix"],
        doc_type=hp["title"], guidance=guidance,
        bbox_instructions=bbox_inst, checklist=checklist
    )
    content = [{"type":"text","text":user_text}]
    content += [{"type":"image_url","image_url":{"url":u}} for u in images]
    return [{"role":"user","content":content}]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case",     required=True)
    ap.add_argument("--prompt",   required=True)
    ap.add_argument("--target",   required=True, choices=["assessment","generation"])
    ap.add_argument("--run-id",   default=None)
    ap.add_argument("--model",    default=None)
    ap.add_argument("--provider", default=None)
    args = ap.parse_args()

    run_id   = args.run_id or new_run_id()
    model    = args.model    or MODELS["runner"]["model"]
    provider = args.provider or MODELS["runner"]["provider"]

    try:
        case   = find_case(args.case, args.target)
        prompt = load_prompt(args.target, args.prompt)
    except FileNotFoundError as e:
        err(e); return

    if not case.get("enabled", True):
        out({"status":"skipped","reason":"case disabled","run_id":run_id}); return

    raw, parsed, latency, usage, error = "", None, 0, {}, None
    try:
        msgs = build_messages(prompt, case, args.target)
        t0 = time.monotonic()
        raw, usage = call_llm(msgs, model=model, provider=provider,
                              system=prompt["system_prompt"], temperature=0.1, max_tokens=8192)
        latency = int((time.monotonic() - t0) * 1000)
        try: parsed = extract_json(raw)
        except Exception: pass
    except Exception as e:
        error = str(e)

    run = {"run_id":run_id,"timestamp":now_ts(),"case_id":args.case,
           "prompt_version":args.prompt,"model":model,"provider":provider,
           "raw_output":raw,"parsed_output":parsed,
           "latency_ms":latency,"usage":usage,"error":error}
    save_run(run)
    out({"status":"error" if error else "success","run_id":run_id,
         "latency_ms":latency,"preview":raw[:300],"error":error})

if __name__ == "__main__":
    main()
