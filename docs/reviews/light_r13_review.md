# Code review: branch lighting (round 13, 3991518) — MERGE WITH FIXES

Verified OK: `make_sky_world(split_rays=False)` is correct — no Light Path node, `strength *= diffuse_boost`,
`gain_out` stays None so the constant strength reaches Background, the camera/glossy saturation stages are skipped
(their Fac would be 0) and the tint's `inv2 = 1 - 0 = 1`, so the diffuse branch is applied to every ray exactly as
claimed. `light_probes.bake` captures `world0`, `eng0` and the vault BEFORE anything is forced and restores all four
in the `finally`, removing the bake world only at `users == 0`, so nothing bake-only survives into the saved file
(log `light_r13_build3.log`: "restored: engine BLENDER_EEVEE, world WORLD_golden_hour"). `bake_world` reads the
scene world's own props (all `lb.SKY` values are numeric, no `float()` hazard, no key collision) and falls back to
`light_build`'s constants. `lead_build.sh` still ends on the Eevee rig; `build_master.py:259` unchanged. No
compounding: `energy_W` / `energy_W_eevee` are written once by `build_shade_fill` and `apply_shade_for_engine` only
reads them, so repeated `apply_preview_eevee` / `apply_viewport_eevee` calls are idempotent. No 0 W lamp is ever
rendered (Cycles 0 W + `hide_render`), `apply_final_cycles` and the probe bake both call the CYCLES branch. r12
findings 3, 7, 8, 9 (hue_tol, meta/world provenance, `_mix_in`/`_mix_out`, the 95.8 reference) and the near-water
cell (finding 4) are in. Item-3 slope table checks out (5.2 / 6.3 / 3.5 / -11.0 / -0.055 per unit db; db 4.1 and 6.3
and the R-B 61 / sat 0.27 extrapolations all reproduce), `cap x k = 1.25` and `L = 2000/5 = 400 m` are right, the
128-spp noise carry is a real measurement, and only lighting's files are touched.

Fix now:
1. **The saved master ships three 55 W/m2 blue suns visible to render.** `apply_viewport_eevee` leaves
   `LIGHT_shade_fill` at `energy 55`, `hide_render False` (`light_presets.py:170-172`), so any Cycles render that
   does not go through `apply_final_cycles` gets them at 0.82 of the sun each: `common.render_previews(engine=
   "CYCLES")` (common.py:373), `scripts/env_r5_hero.py`, `mat_lineup.py`, or a UI F12. The vault override has the
   same shape but is interior-only and x6; this one lands on the hero. Ask the lead to put
   `apply_vault_for_engine/apply_shade_for_engine("CYCLES")` into `common.configure_cycles` (lead's file).
2. `light_r13_sweep.py:192` — `build_shade_fill(..., energy=c["fill"])` never passes `energy_eevee`, so it defaults
   to the shipped 55 and `apply_preview_eevee` then overwrites `data.energy` from `energy_W_eevee`: the `fill=` key
   is dead in Eevee and `fill=0` renders the full fill. The round's own ladder is no longer reproducible with this
   script (the tables were measured before `apply_shade_for_engine` existed — w3/w6/w7 have no shade-preset line).
   Fix: `energy_eevee=c["fill"]`.
3. `light_r13_measure.py:33,61` — `HOLD` contains `near_water_sky` and `lagoon_flank`, which are +20.2 % lum and
   +11.3 hue and cannot pass the 15 % / 6 deg gate, so `--herogap` prints ">> item 1 ... FAIL" for the shipped rig
   while §22.2 / §22.6 score item 1 PASS. Drop the two lagoon boxes from `HOLD` (they are the pre-existing
   screen-trace gap) and report them on their own line, or the lead runs the tool and reads a FAIL.
4. **"the Cycles hero is bit-identical before and after" (§22.2, §22.6) has no script and no log.** It is true by
   construction (`hide_render` + 0 W), but the two frames it compares — `r13a_r13bake_01c`, `r13ship_base_01c` — are
   not committed and no measure output is logged; the committed 01c pair differs by the COMP change. Paste the
   `--hero` output for that pair, or diff the pixels, per the non-negotiable on backed claims.
5. `light_build.py:205-215` — the surviving pre-r13 paragraph directly above `COMP` still argues for "L = 800 m ...
   not the 400 m of round 07's ramp", which is exactly what k 5.0 now ships. Amend it.

Carry:
6. `light_presets.py:161-164` — the `energy_W` fallback seeds from `data.energy`, and in the saved state that is the
   EEVEE 55 W; a shade lamp arriving without `energy_W` would seed the CYCLES energy at 55. Seed from
   `light_build.SHADE_FILL["energy"]`.
7. `light_probes.py:210-213` — `bake_world()` and `s.world = bw` run outside the `try`, after the rig has already
   been switched to CYCLES; if `make_sky_world` raises, the rig is left switched. Move the swap inside the `try`.
8. No frame was rendered through `apply_viewport_eevee` this round (every 01e is the preview preset). The viewport
   preset's `shadow_pool_size` is 512 against preview's 1024 and r11 recorded 256 overflowing; the round adds three
   sun lamps. One `--cams 01v` frame would show the navigable master still fits its pool.
9. cam06's ">= 35" was set against ENV's scale (44.0 un-composited / 23.5 composited); on lighting's measurement of
   the same crop the scale is 59.8 / 33.8, so 38.1 is 0.64 of the un-composited std, not what ">= 35" implies on
   env's numbers. One line to the lead / environment so the threshold means the same thing on both sides.
10. §22.2 quotes the cap-0.50 pair (119.3 vs 114.6 / hue 30.8) and §22.6 the shipped cap-0.25 pair (119.0 vs 114.3 /
    30.9), which is what the sheet burns in. Say which frame each table is measured on.
11. Housekeeping: two tracked PNGs over 5 MB again (`r13SHIP_r13_01c`, `r13h_db40_01c`, 10.3 MB each) — the r12
    finding-10 nit; `light_r13_sheet.py:104` leaves `_r13_sheet_tmp.png` in the tracked previews dir (use the
    scratch dir); `calibration_report.json` is rewritten with 1e-7 re-measurement churn; `light_r12_sweep.py:170`
    still names swept worlds `R11_<tag>` and leaks one per case (only the r13 sweep got that fix, contra §22.5);
    `build_master.py:57` still hard-codes `"WORLD_golden_hour"` (lead's file).
