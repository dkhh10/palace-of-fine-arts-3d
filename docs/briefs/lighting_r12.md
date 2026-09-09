# Lighting round 12 — brief from the lead (2026-09-09). Branch `lighting`, worktree .claude/worktrees/lighting. Read docs/briefs/process.md first.

Context on disk: your branch already holds the r12 WIP (commit 900f3bb): docs/lighting_notes.md §21 ("Round 12 — the shade is a
BLUE deficit", line ~1332) with the measurement tool reproducing QA round-05, the blue-deficit diagnosis, two diffuse-only sky
sockets (hue + tint), sweep/sheet scripts, and the QA-05-7 accepted-deviation note. No Blender run happened last session.
Read: §21 in full; docs/qa_round_05.md sections (a), (c), (d), (e) and "Notes for the lead" 3; docs/decisions.md entry
"2026-09-08 · After QA round 5" (the round-5 decision, binding, not to be re-litigated); docs/status.md entries from "QA round 5 in"
to the end (ENV r7 addendum: the south wing is a sky-term deficit, A 61.7 vs photo 97.9 lum, same root cause as QA-05-1).

Items, in this order (the shade window comes first; the r10/r11 sunlit budget is withdrawn: attic sat may fall to 0.50 / R-B 110):
1. QA-05-1 (blocker) shade window. Tests: cam03 near shaft / sunlit rotunda 0.30-0.70 (QA's re-based test, section (d): near shaft
   box and sunlit box as listed), hero shaded attic (box 1110 225 1150 260) hue within 6 deg of 29.5 and lum within 0.9-1.1 of 115,
   both measured together on the same rig. Report the shade hue / sat / lum on cam03 AND the hero before/after.
2. QA-05-5 south wing (frame-left band 60 480 560 600 on the Cycles hero): 86 vs 109.5 raw ref (0.79). Same lever as item 1
   (diffuse sky term); report the band before/after and the north wing band (1360 480 1860 600) must stay within 0.9-1.1 of 146.5.
3. QA-05-3 Cycles coffer / own sky 0.21 on the merged master (materials' r6 in-coffer gradient is present in the master you
   build). Target >= 0.35 measured on YOUR rebuilt master with materials' gradient in place, not on a lighting-only file. Eevee
   (apply_preview_eevee) within 0.15 of Cycles. Boxes exactly as QA section (c).
4. Sunlit hero numbers after 1-3 (section (a) boxes): attic lum 178-201, hue 34-46, sat >= 0.50, R-B >= 110; columns ratio 0.9-1.1;
   sky top within 149-182. Report all, pass or fail.
5. Secondary, only if 1-4 hold: sky_left / sky_top 0.92 vs ref 1.17 (haze band), water reflection column lum 0.73 / sat 0.11 vs
   ref 0.34 (the horizon-sky share of it; the sheen itself is materials'), near-water hue 209 vs 190-192 (horizon sky colour).
Do NOT touch materials files. Hand-offs for materials r7 (which runs right after your merge, on the master with your rig) go in
the report with numbers: what the shade albedo / water sheen / coffer gradient should do given your final rig.
Deliverables: light_presets/light_build values, assets/lighting.blend rebuilt, composite renders/previews/lighting/light_r12_sheet.png
(before / after / ref for cam01, cam03, cam04 with the numbers burnt in), §21 completed in docs/lighting_notes.md, commits after every
successful script, final report < 30 lines. Reviewer follow-ups carried from r10/r11: no absolute paths in measure/sheet scripts.
