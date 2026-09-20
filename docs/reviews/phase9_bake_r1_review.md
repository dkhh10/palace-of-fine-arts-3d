# MERGE WITH FIXES

`phase9-bake` @ fbdbed9, analysis-only: `export/p9_shade_terms.py` (new) + `docs/briefs/phase9_bake_analysis_report.md` (new).
No other owner's file touched; `docs/status.md` untouched; no binaries. `git merge-base HEAD main` = 24d492c, so the diff-stat
deletions of `phase9_env.md` / `phase9_viewer_r1_review.md` are staleness, **not findings** (confirmed).

**Independently reproduced by this review, all exact:** the A.1 wall times (109 records in `export/out/gate3/bake/*.json`,
0 failures, every group to 0.1 s), the A.1/A.2 totals (26 668 / 26 670 / 13 172 / 12 720 s, 86 / 87 / 44 jobs, 316 s probe),
A.3's 64/44.409718 = 1.441x, B.1's whole table (`--boxes` re-run, byte-identical), B.3's equirect means and FssEss products,
B.5's mist 0.055/0.18, B.6's decile table, (2.196, 3.432, 11.256), 0.1951, 21.428 and sunVis 0.0016/0.747. A.0 verified in
`main`: `scripts/light_build.py:562` `SHADE_FILL energy=0.0, energy_eevee=0.0`, the zero-guard `return []` at :688-694,
`SKY_DIFFUSE_TINT` at :125, `scene_audit.json` `bake.lights` = the 20 named lights with no `LIGHT_shade_fill`, and the
shaper constants vs `export/gate0_common.py:49-51`. The analysis is sound; the fixes below are reproducibility.

1. `export/p9_shade_terms.py:90` — **fix now.** `import cv2` without `OPENCV_IO_ENABLE_OPENEXR`; on this machine (cv2 4.13)
   `--lightmaps` dies with `cv2.error: OpenEXR codec is disabled`, and the env var must be set *before* the import — the
   file states it only in a comment. Fix: `os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "1")` at module top.
2. `export/p9_shade_terms.py:26-29` — **fix now.** `MAIN` is a hard-coded absolute path; the `export/` convention is
   `PFA_MAIN_ROOT` (`export/gate1_common.py:20`). Fix: `MAIN = Path(os.environ.get("PFA_MAIN_ROOT", "<default>"))`.
3. `docs/briefs/phase9_bake_analysis_report.md:3-5` — **fix now.** Claims every number comes from `p9_shade_terms.py` or a
   quoted probe. The script never opens `export/out/gate3/bake/*.json` (A.1), and B.3's equirect means and B.6's decile
   table / sky constants have no committed producer and no quoted probe (all reproduce, so: documentation, not accuracy).
   Fix: add `--chain` / `--sky` modes, or quote the three one-liners beside those tables.
4. `report:159-161` — **carry.** "the excess barely moves (+0.33…+0.54 R, +0.24…+0.43 G)" silently omits `shaft_flank`'s
   +0.8368 R / +0.5752 G from its own table. Fix: widen to +0.33…+0.84 or state why that box is excluded.
5. `report:162` — **carry.** "2.55x in the column shade, 1.79x on the bush" are display-space figures carried from
   `docs/decisions.md:1029`; the B.1 table gives 1.93x and 2.14x in linear R (only 1.37x on the walk is from the table).
   Fix: cite the source and the space, so the paragraph's three ratios share one basis.
6. `report:66` — **carry.** `ARCH_rotunda_dome_membrane_merged` at 108.3 s is the third-cheapest own map, not "the
   cheapest" (`lm_ENV_lagoon_bed` 65.8 s, `lm_ENV_riprap_merged` 73.4 s). Fix: "the cheapest ARCH own map". 316 s is right.
7. `report:264-267` — **carry.** The predicted ≈(0.51, 0.31, 0.02) subtracts B.3's env midpoint (~0.145 R) while B.3's own
   two-basis solve gives 0.168 R; exact subtraction lands at ≈(0.49, 0.30, 0.00). Fix: name which estimate is used.
8. `export/p9_shade_terms.py:27` — **carry.** `BAKE_WT` reaches into the sibling `phase6-bake` worktree for gitignored
   EXRs; B.2 becomes unreproducible the moment that worktree is pruned. Fix: env override + an explicit error message.
9. `export/p9_shade_terms.py:129-140,153` — **carry.** `BOXES` duplicates `scripts/light_r17_measure.py:50,53` (and the
   r14/r13 sets) with a ×1.5 factor, and `:153` clamps x1/y1 to `V` only, so a `--cycles` frame at another resolution
   mis-registers silently. Fix: import the boxes, and assert `V.shape == C.shape`.
10. `export/p9_shade_terms.py:116` — **carry.** `t = np.percentile(A[m], q)` is a percentile over all channel values but is
    applied to `A.mean(2)`, so the tails are not the stated percentile. Nits: `:25` `ROOT` unused; `:204` `--out` -> /tmp.
