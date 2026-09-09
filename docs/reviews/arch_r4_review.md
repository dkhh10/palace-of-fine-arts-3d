# ARCH round 4 (branch `architecture`, head 78f0e81) — code review

**MERGE WITH FIXES** — geometry is sound, idempotent, 5.2-clean and genuinely measured; the acceptance is a
*partial* pass (texture std yes, row std on QA's box no) and three doc/method items should be fixed before merge.

1. **arch_build.py:420-423 comment is stale — carry.** "dentils 0.30 deep vs a 0.16 gap, modillions 0.58 deep vs a
   0.64 gap" contradicts the code it annotates (dentil_d 0.34 / gap 0.20; modillion_d 0.86 / gap 0.56). Fix: restate
   as 0.34 vs 0.20 and 0.86 vs 0.56.
2. **docs/arch_notes.md "The profile as built" table is pre-r4b — fix now.** It still says frieze d **0.20**,
   architrave crown 0.50 "overhangs the frieze by 0.30", modillions **0.68 deep**, and — the one that matters —
   "`frieze_run` sockets moved with it (**0.24 → 0.20**)", which directly contradicts the report's own +0.10 outward
   (0.24 → 0.34). Code (`CORNICE["frieze_d"]=0.34`, `modillion_d=0.86`) and the r4b prose are right; the table is
   wrong and is what the next reader will use. Same stale d 0.24→0.20 in commit 6069749's message (harmless).
3. **Before/after are not rendered at the same sample count — fix now (cheap).** "Before" = QA's round-05 hero at
   **128 spp** (renders/logs/qa_r05_cycles_hero.log); "after" = `arch_entab_probe --render` whose SPP default is 48
   and whose log records no sample count (renders/logs/arch_r4b_render.log). Residual noise inflates *texture* std,
   which is the metric that passes. Re-run the 300x180 border crop at 128 spp and have the probe print `c.samples`.
   (Row std 20.9→32.4 is far too large to be noise; that conclusion stands.)
4. **The 0.000 % silhouette claim has no committed artifact — carry.** `arch_r4_sil_before.log` only shows the alpha
   render; no after-log and no `--sil` JSON is committed, and nothing shows the silhouette re-measured after **r4b**.
   Low risk (r4b changed only frieze_d 0.34 and modillion front 1.38, both inside the unchanged corona 1.66), but
   commit the arch_silhouette measure output for before/after.
5. **Sockets: claim verified, and nothing downstream hard-codes them — no action.** arch_r4b_build.log sums to
   **434** (frieze_run 126 = 24 rotunda + 102 colonnade). Socket plane is now derived (`fd = CORNICE["frieze_d"]`),
   z = ENTABLATURE_Z0 + ARCHITRAVE_H = 28.55. `build_master.py` reads sockets from the .blend and its `ORN_COLL` map
   has **no `frieze_run` key**, so rotunda frieze_run sockets place nothing today; `orn_lib`/`orn_frieze_test` read
   `run_length` off the empty and use their own stand-ins. No file hard-codes 28.80 or 0.24. Note for the lead: the
   frieze band itself shrank 1.2 → 0.90 m and the socket carries only `run_length`, so ORN must be told the height.
6. **arch_entab_probe bug fix is correct — no action.** `world_to_camera_view` now gets a `Vector` (required in 5.2)
   and the `qa_cameras.ensure` fallback lets `--map` run on the asset file. Both verified against the 5.2 API.
7. **Duplicated QA alignment constant — carry.** `(1.3108, -291.8, -124.6)` is hard-coded in both
   arch_entab_measure.py:24 and arch_p4r4_sheet.py:17; a QA re-alignment silently invalidates both. Also
   arch_entab_measure.py:23 `REF169` is an unused *relative* photo path that would break in a worktree — delete it
   or point it at `common.REFERENCE_DIR`.
8. **The tool prints a threshold the brief does not use — carry.** arch_entab_measure's docstring and `cmd_stats`
   announce "row std >= 0.75 of the photo (= 40.2)"; the brief's test is row std >= 35 absolute and tex >= 0.60.
   The sheet's headline line therefore reads FAIL while the brief's own model-box test reads PASS (43.1). Align the
   printed acceptance with the brief so the sheet is not self-contradictory.
9. **Numbers recomputed and consistent — no action.** 32.4/54.1 = 0.599 ("0.60"); 47.6/65.5 = 0.727 ("0.73", 0.74
   against the brief's ref figure 64.6 — the owner measures the ref band at 65.5, a 1.4 % box-mapping difference).
   arch_stats.json (objects 2279→2281 = the two new LOD1 objects; LOD1 +7,744, LOD2 +256) reconciles with the
   notes' per-LOD deltas (+7,488 + 256 of shared sweep). LOD1 duplicates share `ob.data`, and `common.set_lod`
   hides LOD1 in render / LOD0 in viewport, so no double geometry; materials ride on the mesh, `instance_seed` and
   `part_type` are copied. Profile z-monotone, `rebuild_collection` still makes the build idempotent.
10. **Ownership clean — no action.** Diff touches only assets/architecture.blend, scripts/arch_*.py,
    docs/arch_notes.md, docs/arch_stats.json, renders/logs/arch_r4*.log, renders/previews/architecture/,
    renders/qa_comparisons/arch_r4_sheet.png. No other owner's file, no new object/material name collisions.
    Tracked binaries: architecture.blend 45.7→49.2 MB (the owner's own asset, already tracked), sheet 1.1 MB, two
    431 KB preview crops (arch_r4_entab_after.png is an r4a intermediate superseded by arch_r4b_; could be dropped).

**Lead's decision, not a code defect:** the brief's row-std >= 35 on box 900 262 1020 296 is **not met** (32.4).
The owner's explanation is measured two independent ways (profile cross-correlation peak +14 rows, corona half-drop
row 254 vs 268) and puts the model's cornice 1.04 m high in the frame vs ref 169 — a stack question (attic vs
entablature height against the arbitrated round-1 dome fit), not a cornice one. On the model's own 34-row window
(900 238 1020 272) the same metric gives 43.1 (PASS) and the owner shows it is the best window in rows 238-286.
The drum-ring item was correctly reported, not changed. The UV answer is correct and specific: one `UVMap` per ARCH
mesh from `arch_lib.cube_project_uv` (triplanar, world metres, overlapping, not 0..1) — a camera projection needs
its own second layer, and it must be added to *both* dentil/modillion LOD objects since they share one mesh.
