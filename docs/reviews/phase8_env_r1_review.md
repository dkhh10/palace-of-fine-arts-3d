# MERGE WITH FIXES — `phase8-env` @ 5509624 (6 commits, `git diff 846a4f0...HEAD`), reviewed 2026-09-19, no Blender run

1. **fix now** — `docs/briefs/phase8a_env_report.md` placed-triangle table, LOD0/LOD1 columns: hand-multiplied
   (unique × placements), and they contradict the script's own logged placed counts. `renders/logs/p8a_build_lod2.log:17`
   measures LOD0 **2 420 864** / LOD1 **1 012 912** / LOD2 238 032; the report says 2 425 986 / 1 015 498 / 238 032. Only
   the LOD2 column (and the +102 152 the lead quoted) is the measured one. Cause: `scripts/env_build.py:1094-1104`
   substitutes the LOD1/LOD2 mesh for placements past `SHRUB_FAR`, so unique × count overestimates. Fix: quote the build
   log in the report (and in the decisions entry).
2. **fix now** — "LOD0 placed 2 425 986 → 2 425 986 (1.000×)" is not established. *Unique* LOD0 is unchanged to the
   triangle (79 814 in both `p8a_stats_before.log` / `p8a_stats_after.log`, script-measured; the clump loops consume
   exactly `n_cards`, `env_build.py:672-700`). *Placed* LOD0 rose slightly, because far placements draw the densified
   LOD1 mesh — the same mechanism moved placed LOD1 by +328 between the two builds. Reword to "unique LOD0 unchanged;
   placed LOD0 +~1-2 k via the far-LOD substitution", or log a pre-change build.
3. **carry** — instance *scale* did change, so "no placement change" is over-stated. `REAL_H` (`env_build.py:878-885`)
   is the max z extent over the three LOD meshes and drives the sightline clamp `sc *= cap / h` (`:924-930`); the
   narrower LOD1/LOD2 cards lower `REAL_H`, so cap-bound shrubs get a larger `sc` and the LOD0 mounds grow toward the
   cap. Keys, positions, rotations, count (1 379) and the random draw order are untouched, and the cap still bounds
   every LOD, so the podium sightline guarantee holds — but say so in the report.
4. **carry** — `env_build.py:940-942`: `MOUNDS`/`BIG` now come from `sorted(k for k in src if k.startswith(...))`.
   Correct for today's 9 + 4 sources; at ≥10 the lexicographic order (`pitto10` < `pitto2`) silently reshuffles the
   placement keys. Fix: sort by the trailing integer.
5. **carry** — `env_build.py:1216-1222`: the `--lod2=...,clump` flag is dead (`CLUMP_LODS`/`TUFT_LODS` are already
   `(0,1,2)`), and the parser `IndexError`s on fewer than four values. Drop the flag or guard it.
6. **carry** — `scripts/env_p8_boxes.py:43` hardcodes the main checkout root; peers use
   `os.environ.get("PFA_MAIN_ROOT", ...)` (`env_sheet_r7/r8`, `light_r10/11`). Same one-line fix. The qa_r13 worktree
   bug is only worked around locally in `ref_path()`; `scripts/qa_r13_probe.py:40-45` still degrades silently for every
   other probe run in a worktree — separate harness fix.
7. **OK** — idempotency: module scope does `read_homefile(use_empty=True)` + `wipe_scene()` + `rebuild_collection("ENV")`
   (`env_build.py:29-35`); all emitter randomness is per-mesh `random.Random(seed)` / placement `Random(23)` with an
   unchanged draw order, so a rerun reproduces counts and LOD0 triangles exactly. `--shrub-stats` returns before any save.
8. **OK** — no material, object-name or LOD-name change in the diff (`MAT_shrub{,_light,_dry}`/`MAT_reeds`,
   `ENV_shrub_<key>_<i>_LOD<n>` untouched); nothing outside `scripts/env_*.py`, the report, `assets/environment.blend`,
   `renders/`; no master.blend, no export/. Blender 5.2 API clean (no new API surface).
9. **note (size)** — `assets/environment.blend` is committed twice (496d880, 0f7eee1): 69.2 MB + 69.3 MB on disk
   (188.3 → 189.6 MB uncompressed) plus 13 preview PNGs ≈ 19 MB. The asset is meant to be committed; squashing the two
   blend commits before merging would halve the history cost. Report is 35 lines vs the brief's "under 25".
