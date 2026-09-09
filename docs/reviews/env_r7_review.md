# env r7 code review (branch `environment`, head 99c544c) — MERGE WITH FIXES

Verified reproducible from the committed logs: LOD1 **4,622,046** tris, `build_paving` **845 slabs / 1,690 tris**,
far canopy **2453 -> 1747**, cam03 std 14.1 -> 27.8 / ratio 0.146 -> 0.218, cam06 ground 13.8 -> 23.4 %, asphalt
2.47 -> 4.08 %, shore band 71.7 -> 71.7 (env_r7b_build.log 158/160-161, r7_numbers.json, env_r7_probe_*.log).
Idempotency OK (`rebuild_collection("ENV")` + `get_collection` at env_build.py:29-35; `build_paving` links into the
rebuilt `SUB["ENV_terrain"]`). Camera stations are read from `qa_cameras`, never hand-copied (env_lib.qa_camera,
env_r7_probe.py:76, env_trees._cam_specs). No files outside ENV ownership; no Blender 5.2 API problems.

1. **fix now** — env_trees.py:780-781 (`QA-04-6` north band, `pin=("P","C")`). env_r7b_build.log:120,133-143 shows the
   frame-band relief **moving 7 hand-placed A/A2 trees 18-48 m and dropping 3**, incl. "A dark mass right of the dome" —
   the round-5 lesson and the rule this branch quotes at env_trees.py:759-762. r5 logs moved 1, dropped 0. Fix: give the
   north (and cam05) bands the same full pin tuple the south band got.
2. **fix now** — env_build.py:51 `COLONNADE_WALK_Z = -0.60` and :341 `PAVE_CENTRE = (-11.2, 84.7)` are hand-copied from
   `arch_params.COLONNADE_GROUND_Z` / `COL_ARC_CENTER` (comments say so; the notes' hand-off asks ARCH to tell ENV if it
   moves). Fix: `import arch_params as P` and read both — the values match today, silently drift tomorrow.
3. **fix now** — the "16.7 % of the box" and "std 27.8 on box 560 480 900 720" are **two different boxes**: the share is
   from the probe box `cam03_ground = (0,470,1280,720)` (env_r7_probe.py:32, probe_after.log:63-72), the std from
   env_r7_measure `L[480:720, 560:900]`. Fix: say which box in the notes table (row 4 reads as the std box).
4. **fix now** — same class: shore sun reach 47.4 -> 59.5 % is measured on `cam01_shore = (700,640,1200,720)`
   (env_sightlines.py:115), while the 71.7 luminance and `env_trees.SHORE_BOX` are `(700,600,1200,740)`. The null result
   still holds (the probe box is a subset) but it is stated as one box. Fix: one box, or name both.
5. **carry** — the `MAT_paving_stone` fallback is **not silent**: `common.load_material` warns and env_build.py:406 logs
   the names actually used (`MAT_gravel_path / MAT_soil`), and the notes hand it to materials. But the walk therefore runs
   on the very material the terrain already lays there, and probe cam03 sun reach is 1.3 -> **1.4 %**, which contradicts
   the rationale comment at env_build.py:337-340 ("joints ... self-shadow at a 7.4 deg sun"). The std gain is ambient
   relief plus the 288 edge shrubs. Worth restating in the notes so materials sizes the ask correctly.
6. **fix now (comment only)** — env_city.py:574-575 still says the verges are "near-continuous there rather than a 55 %
   scatter"; the 7b code directly above and below is the opposite (26 m resample, keep 0.62, crowns 8-12 m). Delete it.
7. **carry** — env_trees.py:562-563 says the shore sampling is "~150-250 points"; the build log reports **50 shore**
   samples over 276. A 50-point basis for `SHORE_TARGET` is thin; update the comment (or raise the ring density).
8. **carry** — absolute path `MAIN = Path("/Users/dk/Projects/...")` at env_sheet_r7.py:19 (also env_r5_hero.py:25).
   `common.MAIN_ROOT` / `common.REFERENCE_DIR` exist and honour `PFA_REFERENCE_DIR`. Pre-existing pattern in
   env_sheet_r4/r5/r6, so carry — but new scripts should use the constant.
9. **carry** — tracked intermediates over 5 MB: `renders/previews/environment/r7_hero.png` 10.0 MB, `r7_cam06.png` and
   `r7_cam06_nocomp.png` 5.2 MB each. Net repo effect is positive (about 90 old previews deleted); prefer JPEG next round.
10. **carry** — notes line "foliage 30.6 % (from 42.6), far canopy 2453 -> 1747" mixes baselines in one sentence: 42.6 is
    round-6 BEFORE, 2453 is round-7a. Label the 7a numbers as 7a.
11. **carry** — BEFORE is QA's stored round-05 PNGs, AFTER is a master built in this worktree (ENV r7 + MAT r6 + LIGHT
    r11). Parity is inferred from band/shore reproducing to 0.3 lum, not proven. Fine for the null result; state it.
