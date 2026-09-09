MERGE WITH FIXES — the shipped rig is what the scripts build and what the committed logs measure; every fix below is a doc
correction or a guard, none touches assets/lighting.blend. Nothing blocks the merge.

Verified clean. The sun-side socket is diffuse-only by construction (`light_calibrate.py:373-414`: mix Fac =
`(1 - min(is_camera+is_glossy,1)) * clamp(0.5 - 0.5*(Incoming.sun))^p`, the exact mirror of `antisun_weight:292`, same sign
convention), so camera and glossy rays get Fac 0 — which is why §26.6's sky_top/sky_left are identical. With
`split_rays=False` `vis_out` is a 0.0 Value node, so `inv3 = 1` and the probe bake carries the socket on every ray, as
`light_probes.py:161-165` intends; r15 finding 2 is fixed at `light_calibrate.py:210` (`glossy_hue = 0.5`) and finding 3 at
`light_r16_sweep.py:248-256` (lamps keyed by azimuth, not index). `apply_viewport_eevee` / `apply_preview_eevee` untouched.
`--master` opens master.blend and never writes it (no `save_mainfile`; master.blend is untracked). The shrub fix is in
`light_flythrough.py:126-137`, no ENV file touched. Numbers backed: `light_r16_check_master3_step4.log:315-320`
(1.57 / 1.43, agl 1.56, 5.60 / 9.20, holds 3.50 / 4.00), `light_r16_flythrough3.log:3` (251.0 m, 1224 frames),
`light_r16_master4.log:16` (9679 objects), acc.json + acc_measure.log committed. Largest tracked add 3.0 MB (the sheet),
26 MB of r15 panels deleted, nothing outside lighting's ownership.

1. docs/lighting_notes.md:2415 + 2722 — **fix now** (doc). §25.2's case-A row still reads "glossy boost 5.25 -> 4.20 **and
   glossy hue -14.4 deg**", the claim the r15 blocker showed was never applied (`ghue` never reached `make_sky_world`), and
   §26.7 says carries "1/2/3 were closed inside round 15 itself" — 1 was not. Strike the hue clause and call it metadata;
   the code path itself is fixed (`light_r16_sweep.py:196`).
2. scripts/light_flythrough.py:86,145 — **fix now**. `hero` and `dome` still read `qa_xy(CAM_qa_01/04)` and nothing asserts
   the route's design window, so a re-stationing there can silently change the length again (QA-08-13 through another
   camera). One guard in `schedule()`: raise if `sch["frames"]` is outside 1150-1350.
3. scripts/light_flythrough_check.py:1-19, 244-262 — **carry**. Docstring still says "Opens assets/lighting.blend" and never
   documents `--master`; `--master` prints no route fingerprint, so a master built from a stale assets/lighting.blend passes
   the gates silently (print `sch["path_length_m"]` + station count). Cosmetic: the leg table prints the boundary frame in
   both legs ("water 1-404  shore 404-571") beside "first land frame 405" — print `f0+1` after the first leg.
4. docs/lighting_notes.md §26.2 vs §26.6 — **carry**. SHIPPED (35.1 / 0.451 / 127.4, R-B 111.5) and AFTER (35.0 / 0.447 /
   127.7, 111.4) are different frames (bordered sweep vs full acceptance); one sentence saying so.
5. scripts/light_r16_sheet.py:21 — **carry**, accepted. `$PFA_REFERENCE_DIR` closes r15 carry 6 in spirit; the hard-coded
   fallback is still correct on this machine only.
