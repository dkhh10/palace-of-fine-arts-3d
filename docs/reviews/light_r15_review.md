MERGE WITH FIXES — the shipped rig (1 NNE lamp, 49.0/38.5 W/m2, gb 4.20, fast GI off) is exactly what the scripts
build and what the committed logs measure; the blocker is a sweep bug that invalidates one headline claim, not the
blend. Finding 1 must be settled BEFORE materials r9 acts on the 9.4 deg hand-off.
Verified clean: `light_r15_final.log:3,5,12` and `light_r15_lightingblend.log:38` show ONE lamp at (25, 2), Cycles
49.00 / Eevee 38.50, `hide_render False` in both engines — no hidden WNW/SSW leftovers, `build_shade_fill` deletes by prefix first
(idempotent). `apply_viewport_eevee:281` and `apply_preview_eevee:349` are both `use_fast_gi = False`; the probe bake
never touches fast GI and still runs `apply_shade_for_engine("CYCLES")`. `_lamp_weight` parses `_00` -> `lamps[0]`.
Every claimed number has a committed measure stdout; 196.4 s is `light_r15_final.log:41`, 9679 objects
`light_r15_master2.log:16`. Sweep DEFAULTS read from `lb.` (r14 carries 1/2 closed). No tracked file > 5 MB (max
4.4 MB sheet), nothing outside lighting's ownership.
1. scripts/light_r15_sweep.py:170-177 — **blocker (claim, not ship)**. `ghue` is added to DEFAULTS, to SKY_KEYS, to
   the world's custom props and to the case header, but is NEVER passed to `cal.make_sky_world`. Case
   `A_gb42_gh460` (`light_r15_sweep1.log:44`) rendered at glossy_hue 0.500 with only gb 5.25 -> 4.20 moved; its
   world prop 0.4600 is metadata. So §25.2's headline — "case A rotates the glossy sky 14.4 deg and the water's hue
   moves 0.1 deg", the stated proof that the glossy socket has no hue authority — measures nothing, and it is half
   the evidence for the 9.4 deg hand-off to materials r9 (case B, the fill-off floor at 208.6, is valid and
   independent). Nothing shipped is wrong: `SKY_GLOSSY_HUE` ships at the null
   0.500. **Fix**: add `glossy_hue=c["ghue"]`, re-run case A on the bordered hero (~3 min), restate 25.2 point 1
   from that frame — or drop the claim and rest the hand-off on case B alone.
2. scripts/light_calibrate.py:205-211 — **fix now**, latent crash. The `split_rays=False` branch forces
   `camera_saturation = glossy_saturation = 1.0` but not `glossy_hue`, while the new guard at :234/:245 fires on
   `glossy_hue != 0.5` and calls `_sat_stage(..., gl_ray, ...)` with `gl_ray = None`. Safe only because
   `light_probes.bake_world` does not pass the socket; a future non-null ship breaks the bake. Add
   `glossy_hue = 0.5` on line 210.
3. scripts/light_r15_sweep.py:219-223 — **fix now**. `wwnw / wssw / wnne` map POSITIONALLY onto
   `SHADE_FILL["lamps"]`, which is now a one-element list holding the NNE lamp. In r16 `wwnw=0.5` will silently
   scale NNE and `wnne=` be ignored. Key the override by the lamp's `az`, not by index.
4. scripts/light_presets.py:164-171 — **carry**. `apply_shade_for_engine`'s docstring still says "an EEVEE-ONLY
   rig ... `energy_W` is 0.0 as shipped and the lamps are hidden from the render". False since r14 (the r14 carry
   was fixed on `build_shade_fill` only). Same stale text at light_r15_sweep.py:214 ("the Cycles energy stays at
   the shipped 0.0" — it is 49.0).
5. docs/lighting_notes.md §25.3 — **carry**. The AFTER column mixes two runs: the hero/Cycles boxes come from
   `r15a_r15SHIP` (fast GI ON, 3 lamp objects at w 0,0,0.7) and the cam03/05/06 Eevee boxes from `r15f_SHIPPED`
   (fast GI OFF, 1 lamp) — equivalent for Cycles, but say so. Also: the SHIPPED **Eevee** hero shaded attic is hue
   36.5 / lum 131.6 (`light_r15_final_measure.log`), outside the 23.5-35.5 window the table records as PASS at 32.7
   from the Cycles frame. QA scores previews — state both.
6. scripts/light_r15_sheet.py:13 — **carry**. Hard-coded `MAIN = Path("/Users/dk/.../3rd attempt building")` where
   `common.REFERENCE_DIR` / `$PFA_REFERENCE_DIR` exists and r10-r12's sheets used it. Correct on this machine only.
7. **carry** (r14 finding 9 repeats): 26 MB of new tracked PNG panels, all under the per-file bar; drop the per-camera acceptance panels once QA has read the sheet.
