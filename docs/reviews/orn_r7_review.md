# ORN round 7 review (branch `ornament`, head 676897d) — code review, Opus 5, no Blender

**MERGE WITH FIXES** — the re-lay is real, not a restatement: `CAPITAL_PRESETS["capital_rotunda"]` no longer inherits a
single number from the 2.6 m design, the offline solver reproduces the committed table to 3 decimals (I re-ran its maths
against the file: v1 rows 0.3000 / 0.3003 H, aspects 1.020 / 1.079, volutes 0.663-0.887 H, abacus 0.100 H), `clamp_z`
does what the report claims, and the gate log is exit 0 with no FAIL lines. Merge, then fix 1, 2 and 4 (4 before any
master rebuild). Every touched file is ORN's own; no absolute paths; `ornament.blend` committed once.

1. **FIX NOW — `--verify` cannot catch the drift it exists to prevent, twice over.**
   (a) `orn_r7_capital_layout.py:143` seeds the exec namespace with a hard-coded `ARCH_R6 = {"capital_rotunda_H": 3.0, …}`,
   so `CAPITAL_PRESETS["capital_rotunda"]["H"]` resolves to 3.0 whatever `orn_build.ARCH_R6` says — if ARCH moves the
   course again, verify passes against a stale H and reports 0.300 H tiers that the mesh no longer has.
   (b) `bell_radius` / `leaf_spine` (`:37-72`) are hand copies; `--verify` reads back only DATA (`BELL_PROFILE`,
   `CAPITAL_PRESETS`), never the functions. I diffed both bodies against `orn_build.py:103-143`: identical today, so no
   number in the report is wrong — but a formula edit in the builder would pass verify in silence, which is exactly the
   failure mode the docstring promises to close. Fix: parse `ARCH_R6` and the two `def`s out of the source the same way
   the presets are read (same `src.index` + `exec` trick, ~8 lines), and drop the `proud_unit="R"` branch, which no
   longer exists in the builder.
2. **FIX NOW — verify only checks variant 1; the three built variants are not the table.** `CAPITAL_STYLE`
   (`orn_build.py:284-290`) multiplies the preset per variant, and verify never applies it. Re-running the solver with
   the styles: v2 (`volute_r` x1.15) puts the volute spiral top at **0.904 H, above the abacus seat 0.900** — 12 mm of
   spiral buried in the abacus, the exact condition verify FAILs on for the base preset; v3 (`upper_len` x1.07,
   `tilt_add` 4) gives upper extent 0.310 H and `r_tip` **1.51 R**, outside the ref window 1.30-1.40 R. So "spirals
   0.663-0.887 H, under the abacus" and "both tiers 0.300 H" hold for v1 only. Fix: loop `verify()` over `CAPITAL_STYLE`.
3. **CARRY — the ref_002 column is a hand reading plus a canon, not a committed measurement.** The pixel frame
   (`x~490 of 940`, `y 385-785`) matches no committed file: `reference/photos/raw/ref_002_*.jpg` is 1920x2561 and
   `ornament_crops/corinthian_capital_1.jpg` is 1920x1500, so the 940-px view the numbers were read on is not in the
   repo and the reading cannot be reproduced. And the two tier heights in the "ref" column are **not** the reading
   (0.25 / 0.21 H raw) but Vignola's 0.30/0.30 substituted for it on a foreshortening argument — defensible, stated
   plainly in the notes, but it is a canon, not a measurement. Fix: commit the crop or overlay actually measured.
4. **BLOCKER for the next master build (not for the merge) — six LOD1 objects lost their baked maps.** On main,
   `ORN_capital_rotunda_v1-3_LOD1` carried normal **and** AO and `ORN_attic_panel_v1-3_LOD1` carried a normal map
   (`renders/logs/orn_r6_build5.log:39-69`); after the `--no-bake` rebuild all six are `normal_map=""` / `ao_map=""`
   (`orn_lib.py:1011`). `build_master.orn_material_for` (`build_master.py:116-130`) keys the per-asset material on those
   props, so a master built now renders the **16 rotunda capitals and 8 attic panels with LOD1 geometry only** — no
   normal, no AO — flatter than the r6 master in precisely the crop QA-06-6 scores. The r6 PNGs are still on disk and
   tracked but were baked from the pre-r7 geometry, so they must not be re-pointed. `--bake-pending` names all six and
   prints the right command (`--only attic_panel,capital_rotunda`, deterministic seeds, so the rebuild reproduces).
5. **CARRY — the back-row count sits on an integer cliff.** `n_back = int((W - 1.6) / back_pitch) + 1` with
   (10.5-1.6)/1.780072 = **4.9998** → 5 (`orn_build.py:1274`). A 0.02 % change in `PANEL_H` or in the 1.52 seed pitch
   flips it to 6 and re-crowds the row this round un-crowded. Fix: derive the count from a stated gap, or round with a
   margin instead of truncating on the boundary.
6. **CARRY — `panel_x` drops on the CENTRE, so wide elements are still cropped, not dropped.** Scan groups are placed by
   centre and are metres wide; x*K moves design 1's `soldiers` -4.05 → -4.74 and design 3's `dacians` 4.05 → 4.74, so
   more of each end group is pinned onto the frame plane by the hard x clamp in `build_attic_panel` (verts are clamped
   to ±W/2, not deleted → a flattened smear at the border). The gate's 10.500-10.501 m widths are consistent with both
   edges being clipped. Not new (r6 clipped 0.69 m less) and nothing overlaps — the only drop is design 2's `kneel@4.9`,
   and the back row spans ±3.56 m inside the field — but it wants an eye on the first render.
7. **CARRY — `rin_normalise` is correct and idempotent, and has never run.** By algebra the second application is a
   no-op (sx, sy, sz all → 1, translation → 0) and it reproduces the old four-step block exactly. But the rinceau was
   not rebuilt, so the new before-the-bake path (`orn_build.py:1728`) is untested and the committed rinceau LOD1 normals
   are still the r6 pre-squash ones. Finding 4 of r6 is fixed in code only; it lands at the next rebuild + bake.
8. **CARRY — one claim overstated.** "capital plan extent 2.98-3.14 m: leaves and volutes reach the abacus corners and
   stop" reads the gate's line 145, which is labelled `abacus` but is `x_extent()` over the whole LOD0
   (`orn_r5_stats.py:289`) — and section 8 gives max radius 1.697-1.714 m, i.e. the corner volutes reach **3.40 m across
   the diagonal**, 0.4 m past the abacus corners. Unchanged from r6 (`volute_er` / `volute_r` untouched), so not a
   regression; the sentence is just not what the logs measure. Same section: the `clamp_z` print reports the target
   range as if achieved even when the bbox was inside it (attic v1/v3 LOD2) — cosmetic.
9. **OK.** `clamp_z` fires after decimate + weld on every LOD and logs it (`orn_lib.py:973-982`); worst course error
   4.2 mm attic / 1.5 mm capital in the committed logs, matching the report. `orn_r6_hero_px.py` reads sensor and lens
   off the camera `qa_cameras.ensure()` builds and regex-parses `qa_render_round.py:37`'s `--res` default (pattern
   matches the source; both reads happen before `open_mainfile`, so they are not wiped) — 40.0-40.9 px for the nearest
   four, log committed as the r6 review asked. `enforce_tri_budget`'s small-asset WARNING is in. Ownership clean:
   `assets/ornament.blend`, `docs/ornament_notes.md`, `scripts/orn_*.py`, `renders/logs/orn_r7_*.log` — `architecture.blend`
   byte-identical to main, no `build_master.py`, no `docs/sockets.md`. Only tracked binary > 5 MB is `ornament.blend`
   (85.6 MB, one commit, down 2.5 MB). Minor: `bake_pending()` returns `0 if not nrm else 0` (`orn_build.py:1829`) — it
   can never signal pending state by exit code; make it return 1 if the lead ever gates on it.
