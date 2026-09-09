# ORN round 6 review (branch `ornament`, head 90b183e) — code review, Opus 5, no Blender

**MERGE WITH FIXES** — the refit is real and measured: the three course heights live in one dict (`orn_build.ARCH_R6`),
the gate reads them back off ARCH's sockets and exits 0 against the **merged** r6 `architecture.blend` (identical to
main's, `git diff main HEAD -- assets/architecture.blend` empty), and every touched file is ORN's own. Merge, then fix 1.
All six pending bakes are done; the r5 review's findings 1–6 are all closed.

1. **FIX NOW — the course gate degrades to a self-check in silence.** `orn_r5_stats.py:250-256` (`course_check`) and
   `:176-178` take `course = min(stamped) if len(stamped) == 1 else None`, then `target = course or orn_target`. If ARCH
   stamps nothing, or stamps *two different* values across the 16/8/126 sockets, the "ARCH vs ORN" comparison is skipped
   and the section compares ORN's constant against ORN's own mesh — and still prints "all hard checks passed". Fix: append
   a FAILURE when `stamped` is empty or `len(stamped) > 1` for a type ORN builds to (three lines, no rebuild).
2. **CARRY — the capital was Z-stretched, not re-laid; the notes overstate it.** `H` 2.6 → 3.0 is the only change, and
   only quantities keyed to `H` grow: leaf length `length_H * H` (`orn_build.py:179`), row base `base_zH * H`, volute
   `radius=P["volute_r"] * H`, and the figure's joint heights (`:202-212`). Everything keyed to `R` — leaf *width*
   (`:176`, from `bell_radius`), leaf `proud`, `thickness`, `mid_dip`, volute band, figure shoulder/hip widths — is
   unchanged. So the acanthus tiers are 15.4 % longer at the same width and the same radial projection (flatter leaves),
   and the capital figure is a 15 % vertically stretched human. Defensible for a taller course at a fixed shaft, but the
   notes' "the whole design scales with the course" is true in Z only. Whether the leaves now read stretched is a render
   question, not a mesh one — flag it for the QA crop when a GPU window comes.
3. **CARRY — assets overshoot their course by up to 26 mm inside a 30 mm gate.** Gate log section 6/7:
   `capital_colonnade` LOD0/LOD1 1.824–1.825 in a 1.800 course (+25 mm), `attic_panel_v1_LOD1` 5.296 in 5.270 (+26 mm) —
   passing, but 87 % of `COURSE_TOL`. Cause: `build_attic_panel` clamps `v.co.z` to `[0, Hh]` *before*
   `displace_noise(strength=0.006)` and before the LOD1/LOD2 weld. The overshoot eats into ARCH's 0.45 m frame. Fix
   later: re-clamp z after the noise, or tighten `COURSE_TOL` to 0.015 once it does.
4. **CARRY — the rinceau's normal map is baked before a 10 % anisotropic Z squash.** `build_frieze_rinceau` runs
   `finalize_asset` (which bakes LOD0→LOD1) and only then applies `Diagonal((1,1,RIN_FIELD_H/zh))` plus the Y clamp to
   every LOD (`orn_build.py:1650-1657`). UVs survive, so the map still lands, but the stored tangent-space normals are
   off by a few degrees after the non-uniform scale. Invisible at the 3 px hero scale; fix by scaling before the bake.
5. **CARRY — `enforce_tri_budget` at LOD1 runs on every asset type with an 8 mm floor voxel.** `orn_lib.py:945` calls it
   unconditionally in `finalize_asset`; the voxel is `max(0.008, max_dim/240)`. It is idempotent and deterministic (it
   returns early when `before <= budget`, and rebuilds from the same source), UVs are re-made by `ensure_uv` inside
   `bake_maps`, and the r6 logs confirm it fired **only** on `attic_panel_v1` (34652 → 24000 in build3/4) and no longer
   fires at the raised budget (build5). The residual risk is a 1 m moulding unit that stalls one day: it would be
   voxel-remeshed at 8 mm with no warning. Fix: print a WARNING (or refuse) when `max_dim < 2 m` and the weld fires.
6. **CARRY — master LOD1 total.** With the raise, ORN's instanced LOD1 in the master is **≈ 4.26 M tris**
   (attic panels 8 × ~35.7 k = **286 k**, was 192 k, so **+94 k**, matching the claimed +95 k; colonnade capitals
   1.37 M, maidens 0.96 M, urns 0.48 M, rinceau 8 × 9 k + 16 × 4.5 k = 144 k). `build_master.py:190` shares `src.data`,
   so the cost is draw calls, not memory. The claim is sound; the budget raise is 2.3 % of ORN's LOD1 in the master.
7. **CARRY — `orn_r6_hero_px.py` is arithmetically right but has no committed log and copies two constants.** It reads
   the station from `qa_cameras.CAMERAS` (`CAM_qa_01_lagoon_hero`, eye (-14.1, 100.0, 1.6), lens 20) — correct — but
   hard-codes `RES_X = 1920` and `SENSOR = 36.0` rather than reading `qa_cameras`' `sensor_width` and QA's default
   `--res`. Both happen to match `qa_render_round.py:37` today. The projection is exact, not small-angle (a vertical
   segment's height is `f·h/Z` with `Z` the axial depth, which is what the script uses); I re-derived the headline
   numbers: 3.0/78.2 × 1066.67 = **40.9 px**, 2.6/78.2 = 35.5 px, 3.0/94.0 = 34.0 px. Every other r6 claim has a
   committed log; this one does not — commit the run.
8. **CARRY — attic figures grew 17 % in width at unchanged x spacing.** `PANEL_K` multiplies each figure's `S` (a
   uniform scale) and each `flatten` is divided by K so Y is held — that part is correct, and the socket contract
   (origin back-face bottom-centre, +Y = face, `size_hint` 10.511 vs measured 10.511–10.515) is untouched, so
   `build_master`'s placement still lands the panel on the frame. But the layout **x positions** in `PANEL_LAYOUTS` are
   not scaled (correctly — the field is still 10.5 m wide), so the figures crowd laterally by 17 %; ">= 25 cm proud"
   rose 54.7 → 64.0 %. The notes' "everything in X and Z scales by PANEL_K" is wrong about X positions.
9. **OK.** Ownership clean: `assets/ornament.blend`, `assets/textures/orn/*`, `scripts/orn_*.py`,
   `docs/ornament_notes.md`, `renders/logs/orn_r6_*.log` only — no `build_master.py`, no `arch_*`, no `docs/sockets.md`.
   No absolute paths (`common.REFERENCE_DIR` / `common.ASSET_FILES` throughout). `orn_build` has an
   `if __name__ == "__main__"` guard, so the gate's new `import orn_build as B` is side-effect-free. Stale comment:
   `orn_build.py:1653` still says "centred in the 0.90 m band" (the code uses `RIN_BAND_H`, and the margin *is*
   re-added, 67.5 mm top and bottom, so the field is centred). Binaries: `ornament.blend` 84 MB committed twice this
   round (~175 MB of history), `assets/textures/orn` now 67 MB — all ORN's own deliverables, largest single texture
   3.8 MB (under 5 MB), but the .blend churn is worth a squash at merge.
10. **The archivolt / bed-mould section is a proposal only** — no build, no socket invented, and it is accurate:
   `docs/sockets.md` has neither an `archivolt_run` nor a `bed_mould` type, and the reuse of `frieze_run` +
   `subtype="modillion"` / `"egg_and_dart"` matches the contract the rinceau now proves works. Needs an ARCH decision,
   not an ORN one. Note it also asks ARCH to hide its own `build_dentils` blocks — that is a second owner's change.
11. **Standing risk, not a code defect: three rounds with no render.** No `orn_r6_sheet.png` (the brief allowed the
   skip; the GPU was held). The rinceau band, the 3.0 m capital and the 5.27 m field have all been accepted on ray-cast
   numbers. QA-06-6's remaining half — the luminance alternation count — cannot be closed by any of these gates.
