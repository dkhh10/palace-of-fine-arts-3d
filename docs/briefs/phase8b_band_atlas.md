# 8b band atlas — the lead's decision after 2K + coverage and the LOD2 mesh A/B both fell short (2026-09-19). Three owners in lockstep; one contract.
Why: at 100 % the station-2 crown is still a mass with 2K frames (170 px) + coverage; the LOD2 mesh at 100 m is a faceted skeleton (web/README.md "Phase 8 far-tree
A/B"). Option 4 of docs/briefs/phase8b_bake_analysis.md: a BAND atlas per prototype, 12 azimuths x 3 elevations at 341 px frames on a 4096x1024 atlas (frames 2x the
2K per axis; ~13 min GPU for the 16 prototypes at ~50 s each; +128 MB resident desktop; +13 MB payload at tier 1; mobile stays on the octahedral 1K).
## Contract (manifest v5 block `impostors.band`, written by the export; the bake writes the atlases and a sidecar the export reads)
- Per prototype: `band/<proto>_albedo_4096.ktx2` (UASTC, alpha = coverage exactly as the octahedral bake: no threshold, no dilate), optional normdepth omitted
  (the viewer has no 2K normdepth path; the band albedo replaces the albedo lookup only, lighting terms unchanged).
- Layout: columns = azimuth i in 0..11 at 30° steps, azimuth 0 = the same world heading the octahedral frame (u=0.5,v=0.5) faces (state it in the sidecar and assert
  in the viewer from the boot log), increasing clockwise seen from above; rows = elevation j in 0..2 at {0°, 20°, 40°} above the horizon (the stations look at the
  crowns from 0-15°; row 2 is the aerial's). Frame = 341 px inner + the same gutter rule as the octahedral bake, scaled; `frame_px`, `gutter_px`, `inner_px`,
  `azimuth0_deg`, `elevations_deg`, `atlas_px [4096,1024]`, `crown_sphere_m` per prototype in the sidecar `band/band.json`.
- Viewer: `?impband=` (default on when the manifest carries `impostors.band`, `0` = the octahedral 2K path). The card selects the nearest azimuth column and
  elevation row from the camera-to-tree direction, blends the two nearest azimuths (linear in angle) as the octahedral path blends its three frames, samples
  with the Phase 7 premultiplied reconstruction and the Phase 8b coverage share re-swept for 4096 (expect a lower share: ~2.2 px/texel at station 2), applies the
  same irradiance modulation and darkening floor. Tier: the band atlas at tier 1 with the 1K octahedral as the tier-0 stand-in (no tier-0 change).
- Acceptance (QA 20, same rubric): station-2 crown crossings per 100 px toward 7.76 with the tile showing branch structure and sky between them; QA-17 boxes'
  level and centre/edge within the Phase 7 tolerances; hero leaf share within 3 points of 22.2; +3 ms / +150 MB at 1440p same-session; tier 0 unchanged.
## Order
1. Bake engineer (branch phase8-bake, GPU via the bake queue, starts when the export's Gate 1 chain has synced — the lead says when): the band render + compose,
   16 prototypes, `band/band.json`, a 100 % crop of one prototype's frame beside the 2K frame; commit; report bytes, wall time, alpha histogram at the crown top.
2. Export (branch phase8-export, after its 8a sync): the `impostors.band` block + `files[]` at tier 1 + lowres pairing to the 1K stand-in, verify, sync.
3. Viewer (branch phase8-viewer, now): the band sampling path against a synthetic band atlas (a test fixture generated from the 2K octahedral frames re-laid as
   12x3, so the code path is exercised before the bake lands), unit tests for the azimuth/elevation selection and blend, then the real atlas when synced.
