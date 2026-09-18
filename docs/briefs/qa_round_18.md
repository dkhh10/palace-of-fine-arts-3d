# QA round 18 — Gate 5, the web deployment (brief from the lead, drafted 2026-09-18; the lead fills the staging URL and the capture tag before dispatch). Opus 5 xhigh. Fresh agent.
Read: CLAUDE.md "Phase 6" (6b definition of done and the gate checks: name sweep on the export set, six-station full-resolution tile review before scoring),
docs/qa_round_17.md (the 6c close: scores 3.78 / 3.25 / 2.63 / 2.88 / 2.94 / 2.83, the residual list in §7 — nothing there is expected to change in 6b; anything that does is
a finding), docs/briefs/phase6b_plan.md (item 5: what this round measures), docs/decisions.md from "2026-09-18 · 6b" to the end, docs/briefs/phase6b_export_report.md (tier
bytes, oversize list, the mobile estimate), web/README.md "Phase 6b" on main, docs/delivery.md Phase 6c section (the delivery numbers of record).
Inputs (the lead names them in the latest docs/status.md entry): the staging URL `<URL>`; the "gate5" capture taken against it by web/tools/gate5.sh (stations 1-6 at
1920x1080, `renders/web/gate5_cam0N.png`, the network log `renders/web/gate5_net.json` with bytes before the first frame, time to first frame and per-tier arrival, the
1440p perf pass `renders/web/gate5_perf.json` on the desktop tier, and the mobile-tier capture `renders/web/gate5m_cam0N.png` at 1170x2532 with `?tier=mobile`); the
user's own Safari hero screenshot and the iPhone 16 Pro 30 s walk recording under `renders/web/user/` if they exist (score them as evidence, do not wait for them).
Method: (1) Parity with round16c: the same probe (scripts/qa_r17_probe.py extended to qa_r18_*) on gate5_cam0N vs renders/web/round16c_cam0N.png — luma ratio and MAE
per station; the streamed build after tier 2 must be the 6c build (luma 1.00 +- 0.01, MAE within the resampling noise QA 17 measured for the bare URL); any box that moves
> 3 % is a finding with the tier that owns it. (2) The six-station tile review at 100 % on gate5_cam0N (defects new since round16c only: missing groups, low-res textures
that never sharpened, lightmaps unbound, hot-swap seams, wrong tier order). (3) Payload: bytes before the first frame <= 50 MB (the definition of done), time to first
frame, each tier's arrival time and total, from gate5_net.json; every file served <= 25 MiB and the cache headers on `assets/*`. (4) Desktop perf: 1440p medians within
+3 ms of docs/perf_ab_6c.md pass B (29.7 / 30.4 / 33.5 / 22.0 / 29.8 / 32.3 ms) and resident within 2 % of 1 931 MB — streaming must cost nothing once resident.
(5) Mobile tier: the six captures scored on the rubric against the same references (expect lower; the floor is "loads and walks": no missing building parts, foliage
present as impostors, water present), resident estimate vs the 700 MB target from the export report, the user's iPhone recording (walks, no crash, frame rate readable
from the HUD if shown). (6) Name sweep restated on the gate5 manifests (both tiers). (7) Safari on macOS: the user's screenshot vs gate5_cam01 (Chrome) — any
Safari-only defect is a finding with owner viewer.
Verdict: 6b DONE (payload <= 50 MB before the first frame; desktop parity with round16c at all six stations; mobile loads and walks on the iPhone 16 Pro; no new tile
defect; perf and memory unchanged) or ONE FIX ROUND with the list by owner (export tiers / viewer streaming / deploy). 6b stops at deployment plus one clean round.
Write docs/qa_round_18.md (< 120 lines), renders/web/gate5_gate.png (960 px composite, desktop and mobile rows), append docs/quality_checklist.md; commit only those +
scripts/qa_r18_*.py on main, attribution line at the end of the commit message. Do NOT run Chrome or Blender; the captures are the lead's inputs.
Report < 20 lines: the verdict, payload numbers, per-station parity and scores (desktop, mobile), tile findings, perf and memory, Safari/iPhone evidence, commit id.
