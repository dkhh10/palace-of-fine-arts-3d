# Phase 8b item 1 — the band atlases are baked (bake engineer, branch `phase8-bake`, 2026-09-19)

**Shipped, in MAIN `export/out/gate3/band/`:** 16 x `band_<proto>_albedo_4096.ktx2` (UASTC, zstd 18, NO mips, 4096x1024,
`ktx info` validated) + the `band_<proto>_albedo_4096.png` sources + `band.json` (sidecar, schema `pfa-phase8b/band-atlas/1`)
+ `band_report.json` (histograms, per-column and per-station numbers) + `rec/<proto>.json` (one per bake job).
Scripts: `export/band_common.py`, `band_set.py`, `bake_band.py`, `band_queue.sh`, `band_compose.py`, `band_pack.sh`, `band_crop.py`.
100 % crop: `renders/qa_comparisons/p8b_band_broadleaf_s53.jpg` (960 px wide by construction, so nothing is downscaled).

**Cost.** 16/16 rc=0 through `band_queue.sh` (one Blender per prototype, `blender_run.sh 600`, status.json running -> idle):
GPU render **573.1 s**, queue wall **595 s**, 23.4-45.9 s per prototype (median 37). PNG 28 897 173 B, **KTX2 8 794 976 B**
(+8.39 MB payload, under the contract's 13) and **67.1 MB resident** at ASTC 4x4 (not 128: one map, no mips).

**Source and parity.** Nursery rebuilt from MAIN `master_delivery.blend` (13:01 today) by `band_set.py` = `gate3_set.py`
section 7 verbatim; the saved blend is byte-for-byte the same size as the 09-15 `gate3_imp.blend` and all 16 prototypes'
radius / base_z / centre_z / height_above_base / bbox match the shipped manifest to <5e-4 m (asserted in the set AND in
the compose), so `impostors.placement` is unchanged and the band is a pure albedo-lookup swap. Same rig (20 lights, 64 spp,
OIDN, film_transparent), same coverage alpha (`clip(Combined.A,0,1)`, no threshold/dilate/erode, no 2x reduction), same
un-premultiply floor 0.02, same gamma-2 encode. Normdepth omitted per the contract.

**Layout (the export must name these).** `atlas_px [4096,1024]`, **frame_px 341 (the PITCH), gutter_px 8, inner_px 325**
— 341 is the only reading that fits 4096x1024 (12x341=4092, 3x341=1023; an inner of 341 would need 4284), and 325/341 =
0.9531 is the 2K's 162/170 = 0.9529 rule scaled x2. Pad: right 4 px, top 1 px, zero, never sampled. Columns i=0..11 every
30°, **azimuth 0 = view dir (1,0,0) in Blender Z-up = the octahedral frame (col 11, row 6)** (asserted in `band.json`,
compass 180°), increasing clockwise from above; rows j=0..2 at 0/20/40° measured at the billboard centre, **counted from the
BOTTOM** as `impostors.frame_lookup` counts its rows. `range` per prototype **equals** `impostors.prototypes[p].range`.

**Result.** At the station-2 frame the band roughly doubles silhouette detail per screen pixel (broadleaf_s53: 4.0 vs the 2K's
2.8 crossings/100 screen px, Cycles 7.76) and the crop shows branches and sky where the 2K x2 is a mass. Crown-top alpha at
elevation 0, mean over the 16: 76.1 % empty, 14.1 % partial, 9.8 % opaque, mean 0.182; of covered texels 59.1 % are partial
(2K: 72.5 % — resolution turns mush into structure). Per-prototype tables in `band_report.json`.

**Four things the lead should know.** (1) `range` is the published octahedral one on purpose (one constant decodes both
atlases); because the band's 36 views are all sunlit, its own p99.9 is 1.04-3.2x higher, so 0.18-1.62 % of opaque-crown
texels clip (worst willow_s11: linear 18.6 -> 5.9 = display 244 -> 210). `PFA_BAND_RANGE=band` re-bakes at the band's own
range in 10 min if QA sees flat highlights — the viewer must then read `range` from the band block. (2) The six stations see
the far-tree crowns at **negative** elevation (median -2.3 to -3.5°, min -18°): 100 % of placements pick row 0 at stations
1-5 and only the aerial uses rows 1-2, mean row error 2.6-3.9°, worst nearest-cell error 16.1° before the azimuth blend.
(3) `p8_atlas_probe.py` reads the atlas top-down but calls `bands()`, which assumes bottom-up: its "crown top" numbers are
the frame's trunk third and vice versa (0.055 vs 0.1545 on the 2K broadleaf cam02 frame), and its frame row index is
mirrored too. Everything here reads bottom-up. (4) The atlas keeps the nursery's sky-blue crown (6c item 1): the per-placement
irradiance ratio still has to be applied, exactly as for the octahedral.
