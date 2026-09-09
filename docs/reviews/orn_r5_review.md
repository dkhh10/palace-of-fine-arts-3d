# ORN round 5 review (branch `ornament`, head 70dc10d) — code review, Opus 5, no Blender

**MERGE WITH FIXES** — the assets and the five scripts are ORN-only, idempotent and clean, and merging them changes
nothing in the master (nothing is instanced yet). But do **not** wire `build_master.py` to the rinceau until 1–3 are
fixed: as written the guard places zero panels, and if it did place them they would land off the face.

1. **BLOCKER — the guard on main can never fire.** `scripts/build_master.py:155-157` selects on
   `sk.get("subtype") == "rinceau"`, but ARCH never writes `subtype` (or `host`) on the 24 rotunda ressaut sockets:
   `scripts/arch_build.py:317` passes `extra={"run_length", "run_dir"}` only, and `rinceau` appears nowhere in
   `arch_build.py`/`arch_lib.py`. Result: all 24 fall to `coll_name = None` and are skipped. The `host=rotunda /
   subtype=rinceau` row in the round-5 notes table is an artefact of `scripts/orn_r5_stats.py:68`
   (`s["host"] or "rotunda", s["subtype"] or "rinceau"`), which substitutes those labels when the props are absent —
   so the notes' central socket claim is not measured, it is defaulted. Fix (lead, one line): select the rotunda band
   by exclusion, `coll_name = None if sk.get("subtype") in ("greek_key", "greek_fret") else (...)`; better, ask ARCH
   to stamp `subtype="rinceau"`, `host="rotunda"`, `band_height=0.90` at arch_build.py:317.

2. **BLOCKER — the socket frame is not "run start, +X along the run" for these 24.** `arch_lib.py:750` sets
   `yaw = atan2(-dx, dy)`, so socket local **+X = (out_y, −out_x)** = outward normal rotated −90°. For the 8 FRONT
   segments (`cb[1]→cb[2]`, arch_build.py:310-318) the right-hand normal already points outward, the
   `dot2(out, fr.v) < 0` flip does not fire, and +X comes out **anti-parallel to the run** (`run_dir` is stored as
   `+d`, the opposite of what `add_frieze_sockets` stores). A run-start-origin panel therefore runs 5.913 m off the
   ressaut into the next bay and leaves the face bare. For the 16 RETURN segments the segment is exactly radial, so
   `dot2(out, fr.v)` is analytically 0 and the flip is decided by the ~19 mm tilt the `inset=0.05` puts on the
   segment: it fires, giving +X along the run (good) but **+Y pointing into the block** (the rosette_ceiling failure
   again). ORN's `orn_r5_sockets.py` prints `dot(+Y, radial)` and `|X.z|`, neither of which can see either error.
   Fix: ARCH rebuilds these three sockets with `add_frieze_sockets`-style logic (socket at the far end, +Y from the
   block centroid), and asserts `dot(+X, run_dir) > 0.99` and `dot(+Y, p − block_centroid) > 0` for all 24, as it
   already does for the 98 greek_key sockets.

3. **FIX NOW — the 160 mm cap is derived from a stale doc row; the real clearance is 100 mm.**
   `scripts/orn_build.py:1487` and the notes take the architrave crown at d 0.50. `arch_build.py:156` (r4b) puts the
   crown at **d 0.44** over a frieze at d 0.34 — `docs/arch_notes.md:793` records the change 0.50 → 0.44; the 0.50 in
   the notes is the superseded row at `arch_notes.md:718`. So the budget is 0.10 m, not 0.16 m, and the measured max
   proud of 110–124 mm **exceeds** it by 10–24 mm: the claimed "34–50 mm of clearance, guaranteed" is −10 to −24 mm.
   Fix: `RIN_MAX_PROUD = 0.09` and rebuild the six panels (the ray-cast p50/p90 of 65–89 mm survives the reclamp).

4. **CARRY — run lengths are hard-coded, not read from the sockets.** `orn_build.py:1490` fixes 5.9128 / 2.9994; the
   builder never opens architecture.blend. The values are correct today (2·cos22.5·RESSAUT_ALONG = 5.9128 checks out),
   but a change to `RESSAUT_ALONG` or `CHAMFER_CIRCUMRADIUS` desynchronises silently. Fix: make
   `orn_r5_stats.py` §2 exit non-zero when the mismatch exceeds 5 mm, so a rebuild fails loudly.

5. **CARRY — the LOD2 fix is a one-off that a rebuild undoes.** `orn_r5_lod2fix.py` is correct and idempotent (skips
   in-budget LOD2s; replaces only `lod2.data`, so name, material slots, custom props and viewport state survive; UVs
   are lost but LOD2 carries no maps). It is not part of `orn_build.py`, so `orn_build.py --only attic_panel` (or a
   full rebuild, which starts from an empty homefile) restores the 5231–15343 tri LOD2s. Fix: add the voxel-weld
   path to `build_attic_panel`'s `lod2_obj`, or note in `ornament_notes.md` that the fix must be re-run after any
   attic_panel rebuild.

6. **CARRY — pending bake.** The rinceau was built `--no-bake`, so `finalize_asset` (orn_lib.py:918-929) leaves
   `normal_map`/`ao_map` empty on LOD1; `build_master.orn_material_for` then makes a per-variant material copy with no
   image in ORN_NORMAL/ORN_AO. The master gets geometric relief only (1523 tris/m at LOD1) — acceptable at the 12 px
   hero scale. Re-run `orn_build.py --only frieze_rinceau,frieze_rinceau_return` (the `--only` path is incremental and
   idempotent) in a GPU round. Correctly logged as an open issue.

7. **OK.** Ownership clean (assets/ornament.blend, scripts/orn_*.py, docs/ornament_notes.md only; build_master.py
   untouched as instructed). No absolute paths — every script goes through `common.ASSET_FILES`. Tri budgets: new
   `BUDGETS` entries and the 24-instance totals (144 k LOD1 / 768 k LOD0) are consistent. Per-instance seeds are real:
   `SocketCounter.add` gives `variant_seed = i*7919 % 1000`, distinct across all 126 frieze_run sockets. No new
   tracked binaries beyond ORN's own .blend (87 MB, its owned deliverable, but two more full copies in git this round).
   Minor: the comment at orn_build.py:1554 says "two acanthus leaves" where the loop builds three.
