# QA round 18b — Gate 5 fix-round verification, the closing 6b round (brief from the lead, 2026-09-18). Opus 5 xhigh. Fresh agent. Do NOT run Chrome or Blender.
Read: docs/qa_round_18.md (your predecessor: ONE FIX ROUND — the blocker was the seven `groups/m_*.glb` unpublished, so `?tier=mobile` drew 49 calls / 548 tris;
finding 2 the loading-bar denominator; everything desktop PASSED), docs/briefs/qa_round_18.md (method), docs/decisions.md from "2026-09-18 · Gate 5 frame time" to the
end (the frame-time decision: the tiered plan is inside +3 ms same-session; the URL-vs-baseline gap is drift, no re-measure), docs/status.md from "QA 18 (9fbece9)" to the
end (the fix round: export 04fa387 names 149 mobile-only rows in the desktop plan with tier "mobile"; viewer cc316e3 publishes the union of both plans with verify_publish,
redirects mobile textures by name — mobile resident 1 453 -> 500 MB, total 61.5 MB — and fixes the tier denominators), the deploy log renders/logs/6b_deploy_3.log.
Inputs: the same staging URL; the "gate5b" capture (`renders/web/gate5b_cam0[1-6].png`, `gate5b_net.json`, `gate5b_perf.json`, `gate5bm_cam0[1-6].png`, `gate5bm_net.json`,
sidecars) taken against the redeployed site; the round-18 captures for the desktop comparison. CLAUDE.md 6b rule: 6b stops at deployment plus one clean QA round — this
is that round; the fix round is spent.
Method (scripts/qa_r18_*.py re-used, extended to qa_r18b_* only where needed): (1) MOBILE, the point of this round: the six `gate5bm` captures on the rubric against the
same references, with the full-resolution tile review (3 x 2 per station) — the building, ornament, ground, shrubs (LOD2), impostor trees and water must all be present;
name every defect (missing group, low-res map that is the mobile look vs a real hole, alpha, banding, lightmap bleed from the `-si 0.5` decimation the export warned of);
mobile resident from the sidecar vs the 700 MB target; mobile bytes before the first frame from gate5bm_net.json (the 50 MB definition of done applies to the desktop
first look; report the mobile figure with its unit); 0 page errors, 0 404s. (2) DESKTOP regression check only: gate5b vs gate5 per station (luma, MAE) — expected
identical assets, so any move > 1/255 is a finding; bytes before the first frame on the URL (must stay <= 50 000 000); perf medians vs gate5cold with the drift caveat;
resident. (3) The loading-bar fix: gate5b_net.json / gate5bm_net.json per-tier loaded vs declared within 5 % at tier 0 on both variants. (4) verify_publish's claim
(1 051 paths, 0 missing) re-checked by curl on a sample of 20 paths from each manifest incl. all seven m_* groups (HTTP 200, content-type, cache-control per class).
(5) Name sweep restated (no change expected). (6) Owed evidence still absent (Safari hero screenshot, iPhone 16 Pro walk recording): list as owed; do not wait.
Verdict: 6b DONE (mobile loads and draws the whole scene at all six stations with no hole, resident < 700 MB, desktop unchanged, payload <= 50 MB on the URL,
0 page errors) or 6b DONE WITH RESIDUALS (the same, with named non-blocking defects and owners) or NOT DONE (a hole, a 404, a desktop regression, or payload over).
Write docs/qa_round_18b.md (< 90 lines), renders/web/gate5b_gate.png (960 px composite, mobile row prominent), append docs/quality_checklist.md; commit only those +
scripts/qa_r18b_*.py on main with the attribution lines at the end of the commit message. Report < 15 lines: verdict, mobile per-station findings and resident, desktop
regression numbers, payload, owed evidence, commit id.
