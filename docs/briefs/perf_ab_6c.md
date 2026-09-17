# Perf A/B for 6c — round-15 look vs 6c look, same session (Sonnet, mechanical)

Purpose: QA 17 §7 item 7 records the +3 ms frame-time gate as failing at stations 1 and 2 on a cold pass taken on a
different day from round 15. This A/B measures the cost of the 6c foliage look against the round-15 look in ONE session,
back to back, so the number is attributable. You measure and report. You change nothing else.

## Preconditions (check, do not assume)
- `pgrep -fl "MacOS/Blender|headless"` prints nothing. `export/out/bake_queue/status.json` says `"state": "idle"`.
- Work in the main checkout `/Users/dk/Projects/3d render blender 3rd attempt building` on `main`. Do NOT commit, do not
  create a branch, do not edit any tracked file except the report named below. Never run Blender. Never set
  `PFA_DEV_SHARE_GPU` or `PFA_ALLOW_GPU`.
- Run once before the passes, exactly as `web/tools/gate4.sh` does:
  `export PFA_MAIN_ROOT="/Users/dk/Projects/3d render blender 3rd attempt building"; cd web && npm run build; cd ..`
  (`web/node_modules` exists; if `npm run build` fails, stop and report.)

## The three passes, in this order, back to back, nothing else running
Base query (the Gate 4 perf settings, from gate4.sh):
`--query manifest=/assets/gate3/manifest.json --query t=0 --query billboards=0 --query treeboards=0 --query lighting=baked --query post=all --query probe=1 --query impostors=1 --query water=1`

Round-15 look = the base query PLUS (lead's decision, docs/status.md 2026-09-17 addendum):
`--query leafnormal=0 --query leaftrn=0 --query leafsoft=0 --query treemesh=inf --query imp2k=0 --query impmod=0 --query crownint=0 --query cardint=0 --query foliagebias=0 --query walkupmesh=0 --query impint=0 --query cardenv=1 --query shrubenv=1 --query shrublod=0`

6c look = the base query only (the bare delivery defaults).

| pass | tag | look |
|---|---|---|
| A | perfab_r15look | round-15 look |
| B | perfab_6c | 6c look |
| C | perfab_r15look2 | round-15 look again (drift control) |

Each pass is ONE blocking command (fill in TAG and the look's query list):
```
scripts/chrome_run.sh 1500 -- node web/tools/screenshot.mjs \
  --stations 1-6 --size 2560x1440 --frames 120 --warmup 24 --shots 0 --timeout 420000 \
  <query list> \
  --out "renders/web/${TAG}_perf1440.png" --json "renders/web/${TAG}_perf_shot.json" \
  --perf "renders/web/${TAG}_perf.json"
```
Wait for each to exit before starting the next. If a pass fails, retry it once; if it fails again, stop and report the error text.

## Report: `docs/perf_ab_6c.md` (new file; the only file you write besides the renders/web outputs)
1. A table, one row per station 1-6, columns: A median frame_ms, B, C, mean(A,C), B − mean(A,C), A − C (drift), B gpu_cost_ms,
   B draw_calls, B triangles, A draw_calls, A triangles. Read `stations[*].frame_ms.median`, `gpu_cost_ms`, `draw_calls`,
   `triangles` from the three JSONs. Also the resident memory (`stations[0].resident` or `info_memory`, whichever holds MB) per pass.
2. For context, the same medians from `renders/web/round15_perf.json` and `renders/web/round16c_cold_perf.json` (both already on disk).
3. One paragraph of facts only: per station, does the 6c look cost more than +3.0 ms over the round-15 look measured in the same
   session? Is the A−C drift smaller than the B−mean(A,C) delta (i.e. is the delta attributable)? Note the GL renderer string and
   the machine's throttling if any pass's `frame_ms.max` is wildly above p95. No recommendations.
4. Confirm at the end: `pgrep -fl "headless"` empty, no files changed other than the three JSON pairs and the report (`git status --porcelain`).
