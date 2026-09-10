MERGE WITH FIXES

1. **bay_weights, end to end — correct** (carry, cosmetic). `light_build.py:744-780` builds a lamp only for a bay with
   weight > 0, writing the weighted energy to both `light.energy` and `obj["energy_W"]`; `apply_vault_for_engine`
   (`light_presets.py:110-127`) and the probe bake read each object's own `energy_W`, so no path resets a bay to 1; a skipped bay has no object. `light_r11_verify.py:73` compares `energy_W` to `VAULT_FILL["energy"]`: fine at full weight, spurious NOTE for a fractional one. `weights[k % len(weights)]` (`light_build.py:759`) wraps a short list — assert `len(bay_weights) == n`.
2. **Probe bake — correct.** `light_probes.py:210-230` bakes the vault at Cycles physical energies (the two built bays
   only), the shade fill at its Cycles energy (now no lamps), and the gallery forced to its EEVEE state (0 W,
   `hide_render`), so the 1200 W strips are no longer baked in. The `finally` (`light_probes.py:266-274`) still restores
   both rigs for the arrival engine, and `apply_shade_for_engine` chains the gallery back either way.
3. **SHADE_FILL = 0 — no NaN, no hidden lamp, but the lead's claim is wrong** (carry). Nothing divides or scales by
   `SHADE_FILL["energy"]` (`_lamp_weight` uses only per-lamp `w`; the sweeps' `cfill`/`fill` defaults read 0 from the
   dict, so a sweep baseline still matches the shipped rig). `build_shade_fill`'s `max(e_total, e_eevee) <= 0` early-out
   (`light_build.py:687-693`) builds **no lamps at all**, so "the lamp object stays (rig shape)" is not what the code
   does; the result is safer (no 0 W lamp in either light list) and `_shade_lights()[0]` sits inside `if n:`, so an empty
   rig cannot raise. The rebuilt `assets/lighting.blend` is unverifiable without Blender — f40d0e7 commits no log and
   does not touch `calibration_report.json`; confirm next run that the build log prints "0 W/m2 ... no lamps built".
4. **FIX NOW — the acceptance evidence predates the shipped rig.** Notes 28.4, `light_r18_sheet.png` and every
   `r18FINAL_*` frame were measured at `cfill` 49; head ships 0. By the branch's own 28.2 table that moves the hero
   shaded attic to hue ~40.8 (window 23.5-35.5) and sat ~0.533 (ceiling 0.50) and the jamb to 25.9 — three holds change
   and no committed frame measures what is merged. Re-render the bordered hero, restate 28.4, and re-bake the master's
   probe volumes (the old bake still carries the withdrawn shade fill).
5. **Logs** — r18 logs committed, 28.1-28.4 all traceable; only the lead's rebuild has none.
6. **Ownership / paths / binaries** — lighting's own files only, no absolute paths (`ROOT` from `__file__`), QA's
   `renders/final/v2/*` read only. `r18FINAL_ship_01c.png` is 8.5 MB tracked (r17 carry 6): drop or JPEG the full frame.
