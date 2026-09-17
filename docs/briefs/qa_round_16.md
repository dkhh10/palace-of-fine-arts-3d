# QA round 16 — the 6c foliage gate (brief from the lead, 2026-09-17). Opus 5 xhigh. Fresh agent. Do NOT run Chrome or Blender.
Read: docs/qa_round_15.md (the 6a parity scores that are the baseline: 01 3.72 / 02 3.00 / 03 2.56 / 04 2.88 / 05 2.94 / 06 2.83; the residual defect list),
docs/briefs/qa_round_15.md (method), docs/briefs/phase6c_foliage.md (the 6c acceptance: no station drops more than 0.1, station 2 must rise, frame time within +3 ms of
round 15's 28.2 ms at 1440p, resident GPU memory reported), docs/decisions.md from "2026-09-17 · Delivery defect found by the user" to the end (what 6c changed and why:
every far tree is a mesh within 40 m, impostors modulated by E_placement/E_bake beyond, leaf shader, shrub LOD1 within 30 m, tinted shrub albedo), web/README.md on
main (the "QA notes — read before scoring" 6c section: every default, every A/B switch, the round-16 and round-16b numbers), CLAUDE.md "Phase 6" gate checks (the name
sweep on the export set and the six-station full-resolution tile review before scoring — the numeric boxes never override what the tiles show).
Inputs: the "round16b" capture on main (six stations, post-off control, pair sheets, renders/web/tiles/round16b/, round16b_perf.json, round16b_walk.json, the bare-URL
capture, the station-2 walk-in shot), named in the latest docs/status.md entry. References as round 15: Phase 5 hero for station 1, renders/previews/qa/round13_0N_*_cycles.png
for 2-6; stations 3 and 5 keep their round-15 caveat (no Cycles frame). Method: extend scripts/qa_r15_gate.py / qa_r15_probe.py to qa_r16_*; whole-frame ratios, the
round-10b boxes, the round-14/15 boxes, PLUS foliage boxes at stations 1, 2 and 5 (near tree, far-tree band, shrub/reed shore: level, hue, saturation and edge softness
against the reference), the cam01 six tiles at 100 % AND the cam02 and cam05 six tiles at 100 % (6c is judged on foliage at close range), the name sweep restated, the
bare-URL capture checked against the station-1 preset (same look, no dev defaults), the walk-in shot judged as a tile (does the tree at 3 m read as a tree?).
Score table per station vs round 15 and Phase 5. Verdict: 6c ACCEPTED (no station dropped more than 0.1, station 2 rose, perf within +3 ms) or ONE MORE ROUND (name the
station, the box and the owner: bake / export / viewer) — two rounds maximum, this is round one. Then the residual defect list for docs/delivery.md.
Write docs/qa_round_16.md (< 120 lines), renders/web/round16b_gate.png (960 px composite), append docs/quality_checklist.md; commit only those + scripts/qa_*.py on main.
Report < 20 lines: the verdict, per-station scores with the delta to round 15, the foliage boxes at 1/2/5, the tile defects, perf and memory, commit id.
Addendum (lead, after the merge b661489): the full-resolution tiles are gitignored and live only in the viewer worktree — read them at
.claude/worktrees/phase6-viewer/renders/web/tiles/round16b/ (read-only; cut your own 100 % tiles from renders/web/round16b_cam0N.png on main for stations 1-6 as the
gate requires). The foliage boxes the viewer measured are renders/web/round16b_foliage_boxes.json and round16b_hero_boxes.json; the A/B for the 12 m far-tree mesh default
is renders/web/960/round16b_meshdist_ab.jpg. Do your six-station tile review and write its defect list BEFORE reading docs/decisions.md's entry "Lead 100 % tile judgement of
round16b" (it exists; read it afterwards and state where you agree and disagree). Add to the method: shrub/reed boxes at stations 2 and 5 and a tree-crown box at 5 with
level, hue, sat, and an interior-vs-rim contrast measure (crown centre luminance / crown edge luminance) against the reference, so the round-2 owners can be assigned from
numbers. Resident GPU memory: report 1 717 MB against the 1 200 MB Gate 1 budget as a finding with an owner suggestion, not a blocker for 6c.
