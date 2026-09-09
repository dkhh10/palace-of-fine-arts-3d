# Flythrough timing plan (Phase 5, checklist step 6)

`CAM_flythrough` / `_path` / `_target` are built by `scripts/light_flythrough.py` into `assets/lighting.blend` and
appended into master.blend. **1224 frames @ 24 fps = 51.0 s, 250.1 m, mean 4.90 m/s.** One lens throughout: **24 mm** on a 36 mm horizontal sensor, clip 0.1–5000, DOF off; Follow Path (`offset_factor` keyed LINEAR at every frame, so the designed trapezoidal speed is the speed rendered) + Track To an eased empty. The path is not changed here.

## Shot list (stations/frames from the schedule in `light_flythrough.py`, checked against `renders/logs/light_r14_check_final.log`)

| # | frames | t (s) | station start → end | cap | look-at | in view |
|---|---|---|---|---|---|---|
| 1 | 1–84 | 0.0–3.5 | `hero` (−14.1, 100.0, 1.60), stationary | — | (0,0,14) held | the CAM_qa_01 hero composition: rotunda + south wing across the lagoon, full reflection, agl 2.90 |
| 2 | 85–397 | 3.5–16.5 | `hero` → `shore_over` (68.0, 49.0, 6.20) | 9.2 | (0,0,14)→(0,0,12) at `lagoon_c`, then →(14,2,16) | water streaking under the lens, rotunda swinging to frame left, south wing opening up; climbs 1.60→6.20 m to clear the `ENV_shrub_big1_1047/1051` thicket |
| 3 | 409–565 | 17.0–23.5 | `shore_over` → `apron_b`, **through the CAM_qa_02 station (70.5, 25.6, 1.06) at frame 517** | 5.6 | →(0,0,21.1) at `cam02` | landfall on the colonnade apron, then the cam02 three-quarter over the courtyard |
| 4 | 577–913 | 24.0–38.0 | `bay_line`→`gap_in`→`gap_out`→`gal_turn`→`gal_00…09`→`gal_out` (30.3, −25.1, 1.10) | 4.6 | →(0,0,9.2) at `gal_04` (cam03's target) →(0,0,12) | radial entry through the centre of the 4.5 m bay at θ −43.85, then the 2.80 m gallery centreline at eye height z 1.15: shafts strobing past, rotunda between them, vault soffits overhead |
| 5 | 925–1128 | 38.5–47.0 | `app_a`…`app_i` → `dome` (0, 3, 1.75) | 5.6 | →(0,0,18) at `app_d` →(0,2,26) | south of the `ENV_shrub_pitto7_1159` group, up `ARCH_site_step_1`, in through the az-217 arch (0.45 m off a 12.5 m clear span) |
| 6 | 1129–1224 | 47.0–51.0 | `dome`, stationary | — | (0,2,26)→(0,4.5,45) | the ceiling look-up: coffers, dome soffit, drum; 4.0 s held |

## Clearance gate — `renders/logs/light_r14_check_final.log` (step 12), not re-run

| gate | requirement | measured | |
|---|---|---|---|
| clearance | ≥ 1.50 m (gallery ≥ 1.35; 1.40 is the geometric bound of a 2.80 m gallery) | **1.70 m** outside, **1.42 m** gallery (frame 829, `ARCH_colonnade_south_column_006_LOD1`) | PASS |
| level | agl ≥ 1.50 m; z ≥ −0.80 over water | **1.68 m**; min z over water **1.60** (30 samples) | PASS |
| speed | ≤ 6 m/s, water crossing (frames 1–404) ≤ 10 | land **5.60**, water **9.20** | PASS |
| holds | ≥ 3 s at the hero and under the dome | **3.50 s** / **4.17 s** | PASS |

`--step 4` re-run (`light_r14_check_step4_shipped.log`, 306 samples): same four gates, min clearance **1.42 m**, min agl **1.56 m**, tightest ENV object `ENV_shrub_pitto1_1107` at **1.45 m**.

## Findings (schedule only; the path is not changed)

1. **Velocity step at both hold boundaries.** `speed_profile()` grids arc length at `ds = 0.20 m` and `invert()` interpolates t→s *linearly*, so the last grid interval (v 1.0→0) spans ~0.4 s of constant 0.5 m/s. Sampled speed goes 0.00 → **0.50** at frame 85 (leaving the hero hold) and 2.10 → 0.50 → 0.00 at frames 1105 → 1117 → 1129 (settling under the dome): an effective **3.2 m/s²** against the designed `ACCEL = 2.5`. A small jerk out of shot 1 and a snap into shot 6; cosmetic, no gate covers acceleration.
2. **The clearance table never saw ORN, or LOD0.** `light_flythrough_check.link_site()` links **ARCH + ENV only**, at `set_lod(viewport=1)`. The gallery margin is 0.02 m over its geometric bound, so the LOD0 re-run prep review 5 already asks for is the one that can fail — run it with ORN linked as well, not just at LOD0.
3. **Frames 398–408 belong to no leg.** The leg table ends `water` at 397 and starts `shore` at 409 while the speed gate calls frames 1–404 the water crossing; frame 397 is 6.35 m/s, above the 6 m/s land cap, and passes only on that padding. It really is still over the lagoon (agl 7.46), so the padding is honest — state one window, not two.
4. **Checked and clear:** peak pan **14.0 °/s** (frames 1033–1081, turning onto the rotunda axis), far under 30 °/s; no station inside geometry (min nearest-hit 1.42 m); every leg-to-leg speed transition is inside 2.5 m/s² but finding 1.

## Test animation — checklist step 6, `scripts/phase5_deliver.sh 6`

640×360, `apply_preview_eevee(samples=16)`, `frame_step = 2` → frames 1, 3 … 1223 = **612 frames**, ffmpeg-encoded at `fps / frame_step = 12` fps to `renders/final/flythrough_test_640.mp4` (51.0 s, real time).

Anchor: the shipped r15 rig renders **196.4 s for the five-camera Eevee pass at 1280×720 / 32 TAA** (`docs/status.md`, "LIGHT r15 reported") = **39.3 s/frame**; QA round 07's six-camera log is 145.8 s → 24.3 s/frame on the pre-r15 rig, open + setup only ~3 s, so these are per-frame costs, not startup. 640×360 is 0.25 of the pixels and 16 TAA 0.5 of the samples, but the per-frame fixed cost (depsgraph over 9 681 objects, shadow maps, probe upload) does not scale: **5–10 s/frame, best estimate 7 → 612 frames ≈ 71 min (range 51–102)**. That revises `docs/tech_notes.md`'s 3–6 s/frame upward (it predates the r15 rig). Give `blender_run.sh` 7200 s, as the driver does. **If the first 20 frames average over 12 s, drop to `--frame-step 4`** (306 frames, 6 fps out) or use `apply_viewport_eevee` (raytracing off, ~1/3 the cost, no lagoon reflection).

## Final-animation options, same anchor

| option | frames | est. wall time | note |
|---|---|---|---|
| A 640×360 / 16 TAA / step 2 (the test above) | 612 | **~71 min** (51–102) | the deliverable; one `blender_run.sh 7200` |
| B 640×360 / 16 TAA / step 1, 24 fps out | 1224 | ~2.4 h (1.7–3.4) | two runs (1–612, 613–1224) to stay inside a 7200 s max |
| C 1920×1080 / 32 TAA / step 1 | 1224 | ~30 h | 2.25× the anchor's pixels at full samples ≈ 88 s/frame, ~15 chunked runs. Out of budget |
| D Cycles 1920×1080 / 128 spp | 1224 | ~121 h | the measured hero frame is 355.8 s (`docs/tech_notes.md`). Ruled out |

Ship **A**; record its measured per-frame time in `docs/status.md` so B/C stop being estimates.
