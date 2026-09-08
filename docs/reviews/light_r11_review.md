# Code review: branch lighting (round 11, 822e92d) — MERGE WITH FIXES (not merged yet)

Blockers (small, mechanical):
1. `scripts/light_probes.py:124-126` — `if not probes: return []` sits AFTER `apply_vault_for_engine("CYCLES")`, so a probe-less
   master leaves the physical rig live and `--save` (line 178) writes it as the saved "Eevee" state. Fix: try/finally with the
   restore in the finally, or scan probes before the vault switch.
2. `scripts/light_probes.py:117,128` — `restore` is decided from the engine BEFORE line 128 forces BLENDER_EEVEE, and the original
   engine is never put back: `--bake --save` on a Cycles-engine blend saves Eevee with physical vault energies. Fix: capture
   eng0 = s.render.engine, always apply_vault_for_engine("EEVEE" if the saved engine is Eevee else "CYCLES") and restore
   s.render.engine = eng0 in the same finally.
3. `scripts/light_presets.py:289-290` and `241-242` — shadow_pool_size and gi_irradiance_pool_size share one try/except: pass;
   if "1024" is not a valid enum on 5.2 the pool bump silently fails AND drops the irradiance-pool assignment (baked volumes
   silently unused). Fix: separate try blocks, print the exception.
Non-blocking but fix now:
4. `scripts/light_build.py:609` — build_shade_fill creates 3 shadow-casting SUN lamps even at energy 0.0; they ship in
   lighting.blend and link into master. Fix: return [] after the removal loop when e_total <= 0.
5. `scripts/light_presets.py:207-214` vs `232-236` — contradictory comments on raytracing (credited for 0.218 -> 0.325 vs
   "moved nothing; light_threshold was the fix"). If RT moved nothing, set use_raytracing back to False for viewport speed
   (keep it in the preview preset if QA previews need it) and delete the wrong block; light_r11_sweep.py:193 is stale too.
   State the decision in notes §20 so the lead can correct decisions.md.
6. `scripts/light_r11_sweep.py:56` — default master does not honour $PFA_MAIN_ROOT. 7. `:151` SHADE_FILL replaced when fel>=0,
   later fel=-1 cases inherit the elevation (sweep-only).
8. The branch adds ~135 MB of tracked PNG previews (10 MB each for r11d/f/i/z): downscale to <= 2 MB each or drop the
   intermediates before the merge (keep the sheet).
Verified OK: energy_W single source of truth, presets call apply_vault_for_engine with the right engine, 5.2 API names,
SKY_DIFFUSE_BOOST 1.0 = r10 behaviour, idempotent build, only master write is light_probes --save, no out-of-ownership files.
