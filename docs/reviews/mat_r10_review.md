# Review: branch `materials` r10 @ e1a4964 — MERGE WITH FIXES

Verified clean, no finding: (a) `git diff main...HEAD` touches only `scripts/mat_{build,r10_probe,r10_render,r10_measure}.py`,
`docs/materials_notes.md`, `assets/materials.blend`, `renders/{logs,previews/materials,qa_comparisons}/mat_r10*` — no lighting file,
no other owner's file; (b) inside `mat_build.py` only `build_group_dome`, the two `MAT_plaster_ceiling*` albedo rows and `build_dome`
changed — `PFA_dome` has exactly one consumer (`MAT_dome_membrane`, mat_build.py:1083) and `mat_lib.py` is untouched, so the
"library rebuilt" commits re-emit every other material identically (deterministic; `read_homefile(use_empty=True)` at
mat_build.py:19, `new_group`/`new_material` remove-then-create — rebuild-from-scratch is idempotent); (c) the four albedo edits hold
hue and Rec.709 luminance to 6 dp as claimed (recomputed 46.45/41.65/48.79/49.18 deg, 0.466062/0.316271/0.183129/0.147175) at HSV
sat 0.500/0.500/0.109/0.109; (d) 5.2 API names valid (`ShaderNodeTexWhiteNoise` 1D + `W`, VectorMath MINIMUM, Map Range clamp on by
default); (e) the frame is Cycles — `apply_final_cycles` sets engine/device before `common.setup_scene`, which never touches the
engine; (f) the probe splits are in the logs (dome_cap 267/133 = rows 95-111/112-119; jamb 77/320 = 24 % rib; vault_field
200/272 = 74 % rib), so the jamb-hue attribution holds and its direction is consistent; (g) nothing unmeasured can move — clamp/specular/coat live inside the dome material and the only route
out (dome bounce) lands in the attic and water boxes, measured and flat; (h) no new tracked binary > 5 MB, and `BEFORE`/`ALIGNED10B`
are tracked so `mat_r10_measure.py` reproduces the tables from the committed hero; (i) 13 commits behind main, none touching
`mat_*` or `assets/materials.blend` — clean merge.

1. **scripts/mat_build.py:693-699, 704, 736 — fix now.** `MAT_dome_membrane` is on TWO objects (sweep logs: "on 2 object(s)";
   arch_build.py:538 `ARCH_rotunda_dome_apex_cap`, r = 0.55 m). At 28 panels its arc is 0.123 m, under `Ridge Width` 0.30 m, so
   `ed <= 0.06 < 0.22*0.30` forces `ridge_line == 1` over the whole finial: the apex cap ships ~45 % dark plus roughness +0.10 and
   full bump, and the r = 14 m streak scale (line 704) degenerates too. ~6 px at the hero crown, on the silhouette. Fix: `rw = t.minimum(I["Ridge Width"], t.mul(arc, 0.35))` in `ridge_line`, `ridge_lit` and the bump height;
   verify with one bordered crop over rows 70-95, not a new hero.
2. **docs/materials_notes.md:1937 — fix now.** The clean control is **sweep 9 variant a** (`Panel Tone` 0, `Ridge Dark` 0, `Ring` 0,
   `Streaks` 0, mat_r10_sweep9.log); sweep 4 variant a is `Panel Tone` 0.3 / `Ridge Dark` 0.7 / `Streaks` 0.7, no control. The
   207.1 / 4.64 bounds are supported by sweep 9, and the "sat + col-sd jointly unreachable" case rests on them — fix the citation.
3. **scripts/mat_build.py:725, notes:1954/2044 — carry.** The per-channel `MINIMUM(base*fac, 1)` on a base whose G is 1.000 clips
   the bright half of `Panel Tone` (the owner's col-sd stall at 5.41) and shifts clipped panels off hue; 0.955 Rec.709 is also not a
   weathered membrane. Cleaner: drop the base ~10 % for two-sided `Panel Tone` headroom, leaving the level deficit with the sky.
4. **scripts/mat_build.py:676-687 — carry.** `u` reaches 1.0 on the -X meridian, so `pidx = FLOOR(u*Panels)` yields a 29th
   one-sample panel with its own hash (hairline seam, outside the hero box). Wrap with a MODULO before the white-noise `W`.
5. **scripts/mat_r10_render.py:29-37 — carry.** `VARIANTS` was overwritten for each of the 8 sweeps, so the committed script
   reproduces none of them, including the control of finding 2. Keep them as `SWEEPS = {4: [...], 9: [...]}` selected by `--sweep`.
6. **scripts/mat_r10_measure.py:109 — carry.** `REF083` hard-codes the main-checkout absolute path; use `common.REFERENCE_DIR`.
7. **Process, lead's call — carry.** Disclosed and reasoned in the notes, but outside the brief: renders ran concurrently with the
   Phase 6 bake queue instead of waiting for an empty watchdog registry, and 2 heroes + 3 cam04 were spent against a cap of 1 + 1.
   Every run went through `blender_run.sh` with honest maxima and no two of the owner's jobs overlapped.
8. **QA-10-8 still fails two of four boxes (sat 0.352, col-sd 5.41) — carry, not a merge blocker.** The evidence that the box is
   33 % `MAT_concrete_ochre` cornice and that its luminance ceiling is 207.1 is real; QA should re-score rows 95-111 (the membrane)
   or re-own the box under lighting/ARCH rather than send materials back for another pass.
