# Code review: branch lighting (round 12, d5e6850) — MERGE WITH FIXES

Verified OK: the diffuse/camera/glossy split is correct in the node tree (`Fac = 1 - min(is_camera + is_glossy, 1)`
gates every round-12 socket, so camera and glossy rays are untouched by construction; `sky_top` 167.9 -> 168.0 and
`sky_left/sky_top` 0.922 -> 0.922 are the measurement of that). Anti-sun sign is right: `common.sun_direction` points
TOWARD the sun and `Incoming = -ray`, so w = 1 away from the sun. `1 - |ray.z|` horizon weight, `use_clamp`, MapRange
`To Min = 1 - k` all correct; Mix sockets picked by name+type; 5.2 API names all valid. `energy_W` seeds once
(`light_presets.py:116-119`) and only vault lamps are engine-managed, so no compounding — the r10 bug stays fixed.
`light_probes.bake` restores rig AND engine in `finally` (r11 fixes 1-3 present). `build_shade_fill` returns [] at 0 W
(r11 fix 4, log line 38). Sweep honours `$PFA_MAIN_ROOT` and pristine-copies `SHADE_FILL` (r11 fixes 6-7). Build is
idempotent (`read_homefile(use_empty=True)`), only lighting's files are touched, r11's ~135 MB of intermediates are gone.
Arithmetic checks out: FILL slope 0.115/unit -> x2.81 -> measured 0.438 vs predicted 0.437; tint b 17 interpolates to
hue 34.6 / R-B 111.9 / water 0.411 against measured 35.4 / 112.5 / 0.418; QA-05-7 0.921-vs-0.921 is reproducible
(`light_r12_measure.py --ref`). SKY_DIFFUSE_BOOST 2.5, tint, FILL 10214 W and sun (1.000, 0.607, 0.000) all appear in
`light_r12_build_lighting.log`; `build_master` rebuilds from empty and appends `WORLD_golden_hour`, so master carries them,
and its saved Eevee state ends on `apply_viewport_eevee` with the vault override. All three presets call
`apply_vault_for_engine` with the right engine.

Fix now:
1. **No Eevee hero frame exists for this rig.** Every Eevee number shipped is cam03/cam04 (interior, FILL-dominated).
   Eevee bakes the world into one probe used for both diffuse SH and specular, so it is NOT established that Eevee
   keeps the 42.5x blue off camera/glossy — the Eevee lagoon and visible sky could be violet where Cycles' are not,
   and the deliverable requires an Eevee-navigable master. One `--cams 01e` frame measured for `sky_top` and
   `near_water_sky` settles it; do it before merge.
2. `scripts/light_r12_measure.py:41` — `hue_tol=8.0` (and the docstring, `:9`, and `light_r12_sweep.py:12`) contradict
   the ±6 window the acceptance table scores against ("PASS with 0.1 deg of margin"). Pick one number in the script.
3. `scripts/light_build.py:653-661` — `meta` gained no round-12 entries: add `sky_diffuse_tint`,
   `..._antisun`, `..._horizon`, `sky_diffuse_hue`. `build_world` also never writes `w["sky_diffuse_hue"]`
   (`:518-524`). Same provenance nit the r10 review raised for the three saturations.
4. The round's one regression (near-water sat 0.281 -> 0.418, QA-05-4) has **no cell in the sheet** — three rows,
   none showing the lagoon. Non-negotiables require a side-by-side for it before the lead accepts the hand-off.

Carry:
5. Both hero criteria ship at the noise floor (shade hue 0.1 deg inside ±6; sunlit R-B 112.5 vs a 110 floor) and
   `SUN_BLUE_MULT` is now **0.00** — the counterweight is fully spent, so the next degree of shade hue has no lever
   left in the rig. Say so in decisions.md; also note the sun is now a literally blue-free illuminant, which will show
   on any pure-sun specular (water glint, column highlights).
6. Cycles builds the world importance map from a single shader evaluation that will not see the diffuse-only
   multipliers, so up to 42.5x of the diffuse energy sits in under-sampled directions. Watch shade noise / fireflies
   at final spp; if it bites, raise `sample_map_resolution` or clamp indirect.
7. `light_r12_sweep.py:197-198` — the comment claims `apply_vault_for_engine` rewrites the FILL disk from `energy_W`;
   it only touches `VAULT_FILL` lamps. Harmless (both are set) but misleading for the next round.
8. `light_build.py:611-613` still picks `ShaderNodeMix` sockets by index (`inputs[6]/[7]`, `outputs[2]`) — the exact
   pattern commit c3e448d fixed in `make_sky_world`. `build_master.py:57` hard-codes `"WORLD_golden_hour"` instead of
   `light_build.WORLD_NAME` (lead's file).
9. `light_r12_sweep.py:170` names each swept world `R11_<tag>` (stale prefix) and leaks one world datablock per case;
   `light_r12_measure.py:130` hard-codes 95.8 as the column reference.
10. Two tracked PNGs over 5 MB (`r12ship_base_01c.png` 9.6 MB, `_04c.png` 5.0 MB). They are the acceptance frames, not
    intermediates, so acceptable — but downscale on the way in next round.
