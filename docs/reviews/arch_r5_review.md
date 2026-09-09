# ARCH round 5 (branch `architecture`, head db35484) — code review

**MERGE WITH FIXES** — every claim in the report reproduces from the committed scripts and logs; the layer, the
course table and the four carries are all done. One wiring gap (a rebuild silently drops `UVProj`) should be closed
before materials r8 depends on it.

1. **`arch_uvproj.py` is a post-step nothing calls — fix now (blocker for materials r8 if missed).**
   `grep -rn uvproj scripts/` matches only the file itself: `arch_build.py` never invokes it, and the layer lives
   only in the saved `assets/architecture.blend`. Any future `arch_build.py` rebuild drops `UVProj` +
   `UVProj_valid` **silently** — a projection shader then samples the triplanar world-metre `UVMap` and just looks
   wrong. Fix: call it (or its `write_layer`) at the end of `arch_build.py`, or at minimum add the mandatory
   two-command build order to `arch_build.py`'s header and to the hand-off paragraph of arch_notes (which today only
   says "if the projector camera ever moves"). arch_notes:975 is the place.
2. **The named-point check is self-consistent, not independent — carry.** `arch_uvproj.py:204` predicts with
   `ray_px` → `frame_px` → `world_to_camera_view` on the *same* `scene`/`cam`/`RES` the write path uses
   (`:127`). It proves the plumbing (loop→vertex map, the `v = 1 - row/H` flip, clamping, the barycentric read) and
   the `(az, r, z)` arithmetic; it cannot catch a wrong camera, resolution or shift — both sides would be wrong
   identically. Same for the "round-trip 0.00 px" loop (`:145-151`), which recomputes the identical expression.
   The genuinely external anchor is already in hand and should be cited as such: `--courses` puts the corona soffit
   at row **253.9**, and round 4's *rendered* corona half-drop was row **254**. Add that sentence to the notes.
   The three hand-entered offsets (0.74, 1.66, 3.48, −0.15) are also model-fitted, not independent; 1.66 happens to
   agree with the ray-measured d in the course table, which is worth stating.
3. **`world_matrix()` trusts `matrix_world` exactly where it would still be stale — carry.**
   `arch_uvproj.py:77-82` and `arch_entab_probe.py:70-72`: `return o.matrix_world if o.parent is not None else
   o.matrix_basis`. A *parented* hidden object has the same stale `matrix_world`, and `matrix_basis` alone would be
   wrong for it — so the fallback is unusable either way. Harmless today (no `.parent`, no `delta_*` anywhere in
   `arch_build.py`/`arch_lib.py`, so `matrix_basis == matrix_world` for all 33), but it is a trap for whoever first
   parents an ARCH object. Fix: `raise` on a parented object instead of silently using the stale matrix, or walk
   the parent chain. The underlying 5.2 gotcha (hidden ⇒ no depsgraph eval ⇒ stale matrix; `Object.ray_cast` has no
   evaluated mesh, hence `BVHTree.FromPolygons`) is correctly diagnosed and used consistently in both scripts.
4. **Shared-mesh transform agreement is printed, not enforced — carry.** `arch_uvproj.py:100-105` reports the LOD
   pair's matrix delta (0.00e+00 for both pairs, verified in the log) but line 120 then unconditionally uses
   `group[0]`'s matrix. One `fails += 1` when the delta exceeds ~1e-6 makes the guarantee real.
5. **`uv` handle is taken before the attribute is removed/added — carry.** `arch_uvproj.py:121` gets the
   `MeshUVLoopLayer`, then `:123-124` remove and re-add a POINT attribute; CustomData can reallocate and invalidate
   the handle. Different domain, so low risk (and the round-trip would have caught it), but re-fetch
   `me.uv_layers[UV_NAME]` after the attribute calls.
6. **`p.x / r * r` is a no-op — carry (cosmetic).** `arch_entab_probe.py` capital-top block; it reads as an
   intended radius normalisation that was neutered. Write `Vector((p.x, p.y, ztop))`. The same block uses
   `o.matrix_world` on the socket empties rather than `world_matrix()` — inconsistent with finding 3's own rule.
7. **`--courses`/`--sil` also emit the `--map` grid.** `arch_entab_probe.py:259` is `if "--map" in args or OUT is
   None:` — noise only, visible in `renders/logs/arch_r5_courses.log`. Change to `if "--map" in args or (OUT is None
   and "--courses" not in args and "--sil" not in args)`.
8. **`arch_params.MAIN_ROOT` duplicates `common.MAIN_ROOT` — carry.** `arch_params.py:216` re-declares the absolute
   checkout path and the `PFA_REFERENCE_DIR` env default that `common.py:15-16` already owns. Unavoidable given
   `common` imports bpy, but the two must be edited together; say so in a comment. `arch_p4r4_sheet.py:8` also
   still spells the alignment triple out in prose.
9. **Carries 1, 4, 7, 8 all verified — no action.** (1) `arch_build.py:420-421` now reads 0.34/0.20 and 0.86/0.56,
   matching `CORNICE`. (7) `REF169_XF` and `ref169_path()` live once in `arch_params`; the `import common` /
   `PFA_REFERENCE_DIR` / `MAIN_ROOT` ladder resolves under both Blender and bare python3, and the old relative path
   is gone. (8) `cmd_stats` prints `row std >= 35` absolute and `tex ratio >= 0.60` with the raw ratios kept, and the
   report honestly records the QA box as **32.5 FAIL**. (4) `--sil` reproduces `qa_silhouette.measure`'s arithmetic
   line for line (central 30 % min, outer 12 % median, `corner_top + max(4, 0.06·H)` row, absolute image rows —
   compared against `qa_silhouette.py:70-79`) and lands within 1 px of the round-4 alpha render on all four metrics.
   Minor argparse trap introduced with `--ref` `nargs="?"`: `--ref` placed before the positional `img` will swallow
   it; keep it last.
10. **Numbers recomputed, internally consistent — no action.** 33 objects / 31 meshes with the two LOD pairs sharing
    one mesh; `UVMap` first, active and `active_render` (`:136-139`; only *active* is echoed in the log, so
    `active_render` is asserted by code, not by the artifact — printing it would close that). 26,216 verts, 0
    clamped. Course rows reconcile with the `--map` grid to 0.1 px (z 38.30 d 0.71 → 158.3 against 159.6/156.4 at
    d 0.50/1.00; z 32.10 d 0.04 → 245.7 against 245.9 at d 0). `soffit_z` 30.88 = `ENTABLATURE_Z0 + 3.48`, found by
    ray scan and matching the hand-entered check offset. `FACE_HALF` = 17.81/2 − 3.2 − 1.7 = 4.01 as stated.
    tris 2,694,366 / 1,109,070 / 726,222 and 2,281 objects identical to `arch_stats.json`, and the script refuses to
    save on any mismatch (`:230`). `arch_socket_check` ALL OK.
11. **Idempotency holds — no action.** `uv_layers.get(...) or uv_layers.new(...)` reuses the layer and rewrites
    every loop; the flag attribute is removed and recreated. A re-run cannot stack layers or drift. (No re-run log
    is committed; construction is clear enough not to require one.)
12. **Ownership and binaries clean — no action.** The diff touches only `assets/architecture.blend`,
    `docs/arch_notes.md`, `scripts/arch_*.py` and `renders/logs/arch_r5_*.log`. No render call reachable by default
    (`arch_entab_probe.py:276` `if OUT:` is the only `bpy.ops.render.render`, and neither new flag sets `OUT`); no
    master write; no new object or material names. Only tracked binary is the owner's own asset,
    49.2 → 50.1 MB (~1 MB for 26,216 verts × 2 UV floats + 1 point float — plausible). Other owners' `env_sheet_*`
    / `mat_r7_sheet` keep their own ref-169 paths; not architecture's to consolidate.
