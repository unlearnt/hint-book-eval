Add a new assessment case to the pipeline.

---

## Steps

### Gather information interactively

Ask the user for:

1. `case_id` — a short kebab-case identifier (e.g. `ca-dl-genuine-001`)
2. `description` — one sentence describing what this case tests
3. `tags` — comma-separated tags (e.g. `ca_dl, genuine, gen3`)
4. `hint_page_id` — which hint page to use (list available files in `hints/` for reference)
5. `image_paths` — one or two image paths relative to project root (front, back)
   - Remind the user to place images under `data/images/`
6. `guidance_path` — path to an expert guidance .txt file, or skip
7. `ground_truth.label` — `genuine` or `forged`
8. `ground_truth.verdict` — expected verdict: `APPEARS_LEGITIMATE | SUSPICIOUS | HIGHLY_SUSPICIOUS | CANNOT_DETERMINE`
9. `ground_truth.check_overrides` — (optional) JSON dict of check_id → expected_answer for known-altered checks

### Confirm and write

Show the assembled JSON and ask: `"Save this case? [Y/n]"`

If yes: write to `cases/assessment/{case_id}.json` and print:
```
✓ Case saved: cases/assessment/{case_id}.json
  Open the file and set "enabled": true once you've verified the image paths.
  Then run: /run-loop --native
```

The case is saved with `"enabled": false` by default — the user must explicitly enable it after verifying the image paths work.
