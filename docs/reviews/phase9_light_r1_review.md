# phase9-light r1 review — MERGE WITH FIXES (1 fix now, 5 carries, 0 blockers)

Branch `phase9-light` @ 02784e3 vs main, read-only, no Blender run. The change is correct, correctly gated, cheap
and proved through the real chain; every finding is reproducibility or a wrong number in the write-up.

## Verified (no finding)
- `scripts/light_build.py`: the diff is **only** `SKY_DIFFUSE_TINT` :122 and `SKY_DIFFUSE_TINT_ANTISUN` :168 plus
  comments in the file's existing "ROUND N / previous text follows" style. No other executable line moved.
- The negative holds: `light_calibrate.py:286` guards the anti-sun branch with `> 0.0`, so the six nodes
  (`ray_direction … tint_fac_antisun`) are not built — and the skipped `MapRange` would have been identity at
  amount 0 (To Min = 1-0 = 1), so omitting it is exact, not an approximation. `_ANTISUN_P` is correctly marked
  inert and `light_probes.py:157` still reads it, so restoring the weight is symmetric.
- Nothing downstream reads those names: no `antisun` hit anywhere in `export/` or `web/`, and
  `export/bake_lut.py:257-261` finds the Light Path node by `bl_idname` and derives its link list at runtime. The
  count is unchanged anyway (tint and sunside branches reuse `vis_out`, still 6 links), so the camera/glossy
  equirects and the AgX LUT genuinely do not need re-baking.
- "Diffuse sockets only" is consistent with the gating: the tint Fac is `not_cam_or_glossy_tint` =
  1 - min(IsCamera+IsGlossy,1) (`light_calibrate.py:273-276`) and the camera/glossy gain and saturation stages
  (:225-232, :246-256) are untouched. Committed readback: `renders/logs/r19_ship_leadbuild.log:28` =
  `tint (1.0, 0.75, 8.0), antisun 0.00`.
- `light_r19_measure.py`: CIELAB = `p8b_c_cielab.srgb_to_lab` per pixel then mean (:74-75, the published method);
  `BOXES = m17.BOXES` = r16's (:42); windows exactly the brief's — b* >= 5, h_ab 40-80, R-B >= 10 (:46), frieze
  11.4 +- 1.5 = 9.9-12.9 (:47), hold 3 % luma / 2 deg hue (:48, :97-109); `--mae` seed-1 noise floor (:112).
- Full chain ran (light_build -> lead_build.sh -> phase5_deliver 1b -> p8_cycles_refs on a scratch copy) and
  `grep -c 'does not exist'` = **0** in all 46 r19 logs, sweep scratchpad copies included, so note 29.6's texture
  trap did not touch the shipped numbers.
- Hygiene clean: no tracked file > 5 MB; `assets/lighting.blend` 1005 KB -> 980 KB (fewer nodes, as claimed); the
  1080p PNGs untracked; no other owner's file; MAIN master / master_delivery untouched; worktree clean.

## Findings
1. **fix now (doc)** — report §3 and notes 29.6 say "cam03 8/8"; `light_r17_measure.py:50-53` gives cam03 **7**
   boxes, so the hold can only be 7/7. Correct before QA reads it (cam01 12 / cam04 6 are right).
2. **carry** — notes 29.4's dose model is in no committed script: `light_r19_measure.py` has no fit despite the
   report crediting it, and `light_r19_predict.py` is a different model whose `BASE` is the pre-round tint (:28)
   and which hard-codes the anti-sun weight with no amount parameter (:6-8, :72), so it cannot evaluate the
   shipped antisun = 0 rig. Re-running 29.4's arithmetic by hand does reproduce the shipped six boxes to
   0.12-0.77 b*, inside the claimed 1.5 — true but unrunnable. Fix: add the `c - k·ln(mult)` fit to
   `light_r19_measure.py`, reading its own `--json`.
3. **carry** — `light_r19_sweep.py:104` prints tint / antisun_p / horizon_p but not the `antisun` **amount**, the
   socket the round shipped; the 32 sweep logs identify the candidate by filename only. One-line fix: add it.
4. **carry** — no measurement artifact committed: `--json` exists (`light_r19_measure.py:169`) but no output is on
   the branch, so every b* and hold table lives as prose. Commit the BEFORE/AFTER JSONs next round.
5. **carry** — `light_r19_sheet.py:29` hard-codes the main checkout path instead of `common.REFERENCE_DIR`
   (repo-wide pattern in 10 scripts, so not new; worth one central fix).
6. **carry** — `renders/previews/lighting/calibration/calibration_report.json` differs only in `seconds`
   (5.17 -> 6.39): incidental churn from the light_build re-run, harmless.
