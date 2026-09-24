# phase10-water r2 (2baa190) — MERGE WITH FIXES

This is a read-only review of `git diff main...phase10-water`: 10 commits, ae8791d6 .. **2baa1902**, and it merges clean into main (`git merge-tree`).
The fixes are documentation only. No code change blocks the merge.

**Scope is clean.** 13 files changed: `scripts/mat_build.py`, `scripts/mat_p10w_{measure,sweep,sheet}.py`, `assets/materials.blend`, the notes section,
six `renders/previews/materials/p10w_*` frames and the sheet. There is no ARCH, ENV, lighting, export/, web/ or master change.
- **mat_build.py** changes only three materials. `MAT_water_lagoon` gets `WATER_ANISO_X` 0.36 -> 0.8, the wind-wave layer, `WATER_FINE` and the murk colour.
  `WATER_MURK_GAIN` near end goes 0.15 -> 0.70. The leaf materials get a neutral-default `LEAF_SAT`/`LEAF_GRADE` grade plus per-material values. `MAT_column_rose` gets `COL_VALUE` x1.22.
- **Untouched:** `WATER_GLOSS_MIX` 0.45, `WATER_GLOSS_TINT`, transmission, volume, `WATER_BUMP_DIST` and `WATER_MURK_EEVEE`, so the decisions.md lighting split stands.
  Eucalyptus and the other callers get the two grade nodes at identity.
- **Blender runs:** all 24 `renders/logs/p10w_*.log` show one `blender_run.sh` launch ending `rc=0`.

**Reproduced without Blender.** `mat_p10w_measure.py hero` on the two committed cam01 PNGs gives every hero row of the notes' table exactly
(reflection, open water, stone holds, jamb, column mask, conifer, willow, box 1/2 dark). The boxes match the brief:
`water_refl` 900 760 1020 840, `near_water_sky` 1150 1000 1450 1050, ripples, flank (`mat_r7_measure.BOXES`).
The texture metric is as documented:
- Lx and Ly are the lag at which the mean-removed row / column autocorrelation falls to 0.5.
- aspect is Lx/Ly. aniso is std(column means) / std(row means). cv is std/mean. dark is the share of pixels below 0.6 x mean.
- Ref 169 is measured on `warp_ref169`, a 1.31x bilinear upsample of the JPEG with a constant row shift (5 px) in the water rows.
  Its Ly (1.12) therefore sits at the pixel floor on both sides, and aspect is effectively Lx.

**Weight 0 is an exact no-op (read).** `P10_w` = conf x 0, so the `P10_mix` factor is 0 and the output is A. With `tied`, `P10_r9k` = conf x 0, so the `P10_unr9` factor is 0 and the output is A = the round-9 colour.
The only residual cost is two sampled image textures in every PFA_concrete shader, with no colour change.
Re-runs are idempotent: `P10_*` and `P10_colsat` are removed and their links restored first. The logs show 5 `mat_build` -> `integrate` cycles, all
`weight 0.0`, `removal: tied`, `saturation x0.68, hue -10.0 -> 1 consumer`. The recipe is documented in the notes and in `mat_build.py`.

## Hold table (brief rule: per box, pass / fail / closer to ref)
| box | before -> after (ref) | verdict |
|---|---|---|
| reflection lum / hue / sat / R-B | 118.4/49.0/.194/+23.9 -> 119.9/48.0/.384/+50.1 (162.1/33.8/.403/+77.2) | R-B pass (was fail); lum and hue still fail, both failed before; all four closer. No regression |
| reflection Lx / aspect / aniso | 12.1/12.4/10.6 -> 6.4/6.1/1.94 (7.9/7.05/2.36) | closer; Lx and aniso now slightly past ref |
| reflection cv / dark | .309/15.9 % -> .277/6.3 % (.312/16.2 %) | **further from ref** (finding 1) |
| near water lum / hue / sat | 108.2/204.4/.229 -> 119.0/195.5/.191 (103.6/187.4/.229) | hue pass (was fail); **sat fail (was pass) = a regression QA will flag**; lum still passes but moved away from ref |
| ripples / flank | R-B -20.5 -> -16.3 (window -36..-16, passes by 0.3); flank 162.3 -> 161.4 | pass; ripple lum away from ref (106.9 -> 117.9 vs 103.1) |
| stone attic / entablature / vault | <= 0.3 lum, 0 deg | held |
| jamb | 52.7/30.2/.614 -> 57.9/26.9/.504 (95.4/22.3/.469) | the +-2 hold was already broken before (30.2 vs 24); closer on all three. It holds column pixels. Not a regression |
| column shafts, QA mask | 73.5/28.9/.700 -> 104.2/28.6/.614 (96.8/24.8/.585) | hue pass by 0.2 deg, sat pass; lum overshoots +7.4 (was -23.3), closer |
| column shafts, fixed crop 1000 360 1240 480 | 105.6/38.2/.744 -> 111.3/37.9/.681 (112.3/33.8/.599) | **sat fails** (+.082), hue fails +4.1; closer on all three (finding 2) |
| conifer luma / B/G | 54.1/.29 -> 100.3/.35 (107.9/.77) | luma pass, B/G fail; closer |
| cam05 sat / cam06 lagoon | .790 -> .795 / 107.3 -> 107.6 | pass / pass |

## Findings
1. **fix now (notes)**: the cv / dark row blames the drop entirely on "the brighter foliage".
   The sweep contradicts that, and the sweep is a fair comparison: shipped w0 at 64 spp reads .309 / 15.6 %, the same as the 32-spp before (.309 / 15.9 %).
   The water alone (y2, before the leaf change) takes dark 15.6 -> 9.5 %; the leaves then take it from 9.5 to 6.3 %.
   So the brief's headline, "short streaks with dark gaps", is half met: the streak shape moved toward ref, but the dark gaps moved away through the water change itself.
   State this, and log it as the next water lever (murk gain near 0.70 fills the gaps: the x1 / y2 cases show the trade).
2. **fix now (notes)**: add the fixed shaft-crop row, which the measure script prints and the table leaves out.
   The column hue/sat pass is on a colour-threshold mask whose membership moves with the tint. Our mask holds 8-12 k px against ref's 55 k.
   The agent's own k1 check on fixed pixels reads .544, which is outside +-0.04. On the fixed crop the columns are closer but outside the window.
   Report the pass as mask-dependent.
3. **fix now (notes; lead's decisions.md wording)**: the sat-floor hand-off conflates two boxes.
   Ref 169's NEAR box is .229, inside the .22-.32 window. The 0.143 belongs to the ripples box, which has no sat window.
   Near-water sat .191 is therefore a genuine pass -> fail regression on the near box, and it is the price of the hue move.
   It is not evidence that the floor "describes the render, not the photo". Rewrite the hand-off: this is a trade (hue +9 deg closer, sat -.038 below ref) for the lead to accept or send back.
4. **carry (Eevee / web parity)**: Eevee now shares the new normal (aniso, wave, fine) but not the murk.
   `WATER_MURK_EEVEE` stays neutral grey and the 0.70 near gain is Cycles-only. Cycles near water moved +10.8 lum and -8.9 deg hue; Eevee was not rendered at all.
   Consequences:
   (a) the navigable Eevee file and the flythrough no longer match the Cycles hero's water.
   (b) `web/src/water.js` derives its murk from `WATER_VOLUME` and has its own ripple map, so neither change reaches the viewer.
   Any Phase 6 parity reference rendered before this merge (stations 1, 5, 6) is stale for water: re-render the Cycles references before the next parity score, or the viewer is scored against old water.
   (c) the leaf grade (HSV + gain between the image texture and the BSDF) will not survive the glTF export of the "original leaf materials" (`export/budget_doc.py`).
   The +1 stop foliage needs a baked albedo to reach the web.
5. **carry (foliage B/G)**: rejecting the blue albedo is right. The stated cause is half right.
   The sun carries almost no blue: `LIGHT_sun` irradiance is (8.62, 5.24, 0.0) in `web/src/water.js`, so a sunlit needle's B comes only from sky.
   The NE mass is front-lit by the morning sun behind the camera, so the translucency change (B 0.5 -> 0.8) is nearly inert there: it multiplies sun-coloured back-light.
   The sheet shows the actual gap is structural. Ref's crown has blue-grey sky-lit shade between sunlit clumps; ours reads uniformly sunlit yellow-green.
   The untried levers are shading, not albedo: crown-normal transfer / sky visibility on the cards and card density (ENV), and aerial perspective at 100 m+ (lighting, frozen).
   A translucency tint or backface colour sweep is not worth GPU at this station. The cam06 "lavender" rejection has no number: give it one (hue / B/G on the cam06 conifer tops).
6. **carry (recipe coupling)**: `COL_VALUE` 1.22 in `mat_build.py` and `--col-sat 0.68 --col-hue -10` in integrate were tuned together, and nothing enforces running the second after the first.
   ARCH has a hook for `arch_uvbake`; materials has none. A bare `mat_build.py` run would ship x1.22 albedo without the desaturation (sat ~.70+, lum up).
   Either have `mat_build.py` exec integrate with the final arguments, or make `build_master` assert that `P10_colsat` is present.
7. **note (process)**: the brief's budget was overrun, and the notes declare it honestly.
   - Brief: <= 4 water cases in one sweep, <= 3 column settings, one hero at 64 spp plus one cam05/cam06.
   - Delivered: 12 water cases (4 passes), 14 foliage, 7 column (c0-c3, k1-k3) and two acceptance sets. One pass was a re-run caused by a set-selection bug.
   - The logs sum to about 41 min of GPU (sweeps 1,539 s, before 249 s, accept 695 s).
   The next brief should price the foliage and column items separately. The 24 logs are untracked in the worktree; commit them as ENV r2 did.
8. **note (QA)**: col-hue -10 moves the shafts toward magenta. cam06's shaded shafts read mauve (the agent flagged this). QA should check it in the tiles. All 10 commits carry the `Claude Fable 5.1` co-author line (lead convention).
