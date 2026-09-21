# Palace of Fine Arts — Phase 5 delivery (lead, 2026-09-10; v2 after the user's arch finding)

## v2 (delivered) vs v1 (kept under renders/final/v1)
v1's main arch was closed by chord triangles of the vault rib plate (docs/status.md "USER DEFECT", docs/decisions.md 2026-09-10). v2 = the
master at a765b9d: vault rib plates gridded before the arc mapping (all 8 bays), rotunda interior fill on bays 06+07 only, blue shade-fill lamp
off, floating gulls removed. Hero 4K: `renders/final/v2/hero_cam01_3840x2160.png` (384 spp fixed, adaptive off, OIDN, 4207.8 s wall, peak RSS
5.7 GB). Side-by-sides: `renders/final/v2/final_hero_vs_ref169.png` (aligned, apex 0.44 %H) and `renders/final/v2/v1_v2_ref169.png`
(v1 | v2 | ref 169 with the main-arch 2x crops). QA: docs/qa_round_10.md (FAIL, two blockers) -> docs/qa_round_10b.md (PASS, hero 3.61).
Lead's six-tile pass on the v2 4K: main arch open with the coffered barrel, far arch and sky; remaining visible items are in the known-issues list
below (coffers read as punched holes, no archivolt moulding, dome cap untextured, shoreline hedge + flat ledge slabs, side reflections faint,
leaf-card shards in the near trees, a dark slot at the podium base centre).
Boxes on the v2 4K (1920 grid): sunlit attic 186.1 / sat 0.520 / R-B +117; shaded attic 121.3 / hue 41.3 / sat 0.633 (outside 23.5-35.5 / 0.50:
the cost of the shade lamp off); reflection 126.8 / hue 44.9 / R-B +37; near water 123.9 / hue 205.7; vault field 60.5 (ref 44.9, window 45-65);
jamb hue 24.0 / R-B +33.

## Deliverables
| item | path | note |
|---|---|---|
| Scene, self-contained | `master_delivery.blend` (277.7 MB, 89 images packed) | opens in 0.86 s; LOD1 in the viewport, LOD0 at render; Eevee viewport preset saved; gitignored (rebuild: `scripts/lead_build.sh` then `PFA_PACK=1 scripts/phase5_deliver.sh 1b`) |
| Scene, linked | `master.blend` (160.9 MB) + `assets/*.blend` | what QA rounds 8-9 scored; links `assets/architecture / ornament / materials / environment / lighting.blend` by relative path |
| 4K Cycles hero | `renders/final/v2/hero_cam01_3840x2160.png` (v1: `renders/final/v1/`) | native 3840x2160, 384 spp fixed, adaptive off, OIDN, AgX High Contrast, exposure -2.833; v2 4207.8 s wall |
| 4K timing probe | `renders/final/hero_cam01_3840x2160_128spp.png` | 128 spp fixed: 1432.6 s wall, peak RSS 6.2 GB (QA-03-16 closed) |
| Side-by-side | `renders/final/v2/final_hero_vs_ref169.png`, `renders/final/v2/v1_v2_ref169.png` | render / ref 169 aligned (scale 1.3108) / blend; `qa_silhouette.py align` |
| Flythrough path | `CAM_flythrough` in the scene, frames 1-1224 @ 24 fps (51 s, 251 m) | `scripts/light_flythrough.py`; clearance 1.57 m outside / 1.43 m gallery with ornament linked (`light_flythrough_check.py --master`) |
| Flythrough test | `renders/final/v2/flythrough_test_640.mp4` | Eevee 640x360, 16 TAA, every 2nd frame at 12 fps; ~14 s per frame on the M2 |
| Delivery tooling | `scripts/phase5_deliver.sh`, `phase5_cleanup.py`, `phase5_hero.py`, `phase5_flythrough.py` | each step individually runnable; every Blender run through `scripts/blender_run.sh` |
| QA record | `docs/qa_round_09.md` (final scores + known issues), `renders/qa_comparisons/round09_gate.png` | hero 3.67 / 5 on the QA rubric; the gate rule (two flat rounds after the projection) closed the polish loop |
| Decisions | `docs/decisions.md` (final gate judgement 2026-09-10), `docs/status.md` | |

## Opening and rendering
See docs/tech_notes.md "Opening and rendering (Phase 5)". Short form: open `master_delivery.blend`; the viewport is Eevee at LOD1. To re-render the
hero: `scripts/blender_run.sh 7200 -- --background --python scripts/phase5_hero.py -- --blend master_delivery.blend --spp 384 --res 3840 2160 --adaptive off --denoise on`.
Flythrough frames: `scripts/phase5_flythrough.py --blend master_delivery.blend --res W H --samples N --frame-step S [--frame-start F]`.

## Measured on the delivered hero (4K frame downscaled to 1920x1080, QA boxes; photo = ref 169)
| box | render | ref 169 | QA window |
|---|---|---|---|
| sunlit attic lum / sat / R-B | 187.2 / 0.488 / +110 | 188 / 0.582 / +134 | 178-201 / 0.53-0.62 / >= 120 (sat capped by the view transform, accepted) |
| shaded attic lum / hue / sat | 126.7 / 35.1 / 0.448 | 118.8 / ~30 / 0.454 | 103.5-126.5 / 23.5-35.5 / <= 0.50 |
| reflection lum / hue / R-B | 114.4 / 41.2 / +52 | 164.8 / ~38 / +72 | 124-208 / 25-45 / >= +35 (mirror 0.61 of sunlit vs 0.87) |
| near water lum / hue / sat | 124.1 / 207.5 / 0.202 | 105.4 / 190 / 0.246 | 79-131 / 185-200 / 0.22-0.32 |
| lagoon flank lum / hue | 159.9 / 209.6 | 152.4 / 200.3 | 114-190 / <= 210 |

## Known issues (open at delivery, ordered by hero visibility; owners and one-line fixes in docs/qa_round_09.md)
1. Hero mirror at 0.61 of its own sunlit stone vs the photo's 0.87 (materials: grazing-incidence lobe). 2. Archivolt band and bed-mould modillions
blank on 8 sockets (ornament). 3. Building block 1.10x the photo's saturation off the attic box (lighting tint b 70 -> ~55). 4. Shoreline reads as a
hedge: no trunks, shed, figures (environment). 5. cam03 walk hue green (lighting + environment). 6. cam02 shaded face violet in Cycles (lighting
tuned on Eevee). 7. cam05 lagoon band bright (the hero / cam05 gloss-mix trade). 8. Coffer field / rim saturation (materials). 9. Eevee-Cycles
west-soffit gap +0.22 (probe coverage; the Eevee test animation mispredicts that corner). 10. Entablature cornice / frieze sub-courses 1.33x / 0.87x
(architecture option A). 11. Entablature row std 37 vs 40. 12. Sunlit chroma capped by AgX High Contrast (accepted). 13. ref 062 is a midday photo:
cam02 matches its framing, never its tonality at golden hour.

# Phase 6a — three.js walkthrough, local delivery (lead, 2026-09-17; closed at parity by docs/decisions.md "FINAL JUDGEMENT OF 6a")
## Deliverables
- Viewer: `web/` (Vite + three.js); `cd web && npm install && npm run dev`, or `npm run build` -> `web/dist`. Assets: `web/public/assets -> export/out` (gitignored, regenerable
  from master_delivery.blend by the export/ chain: export_set -> gltf_pack -> bake_queue -> manifest_v4 -> sync_main; see export/README.md items 1-32).
- Stations 1-6 as presets (keys 1-6), hero = CAM_qa_01_lagoon_hero; walk controls with ground clamp (shore margin 0.15 m, 24/24 probes above WATER_Z + 0.1); loading screen with
  a correct total (640.1 MB); deterministic captures via `web/tools/gate4.sh` through scripts/chrome_run.sh.
- Look: AgX High Contrast at -2.833 EV by the OCIO-baked 3D LUT; lightmaps (gamma-2, UV2 dequantised in the viewer), ORN slot atlases, hero probe, vertex irradiance on the 14 near
  trees, per-placement irradiance on 1 379 shrubs/reeds, procedural ripple water with the reference sheet's murk, compositor airlight and bloom.
## Measured (round15, 43b1e0a; docs/qa_round_15.md)
| station | viewer vs Phase 5 score | Phase 5 | frame luma vs Cycles |
|---|---|---|---|
| 01 hero | 3.72 | 3.67 | 0.897x |
| 02 | 3.00 | 2.94 | 1.030x |
| 03 | 2.56 | 2.56 | 1.804x |
| 04 | 2.88 | 2.81 | 1.118x |
| 05 | 2.94 | 3.06 | 1.001x |
| 06 | 2.83 | 2.67 | 0.993x |
Frame time at 2560x1440, full look: 28.2 ms median (35.5 fps), 279 draws, 4.14 M tris, resident 1 677.9 MB. `?quality=fast` is the documented preset for the 45 fps target
(to be measured on this build at delivery; the default is the user's choice).
## Known issues (what a walker sees that the Cycles frames do not; owners in decisions.md "FINAL JUDGEMENT OF 6a")
1. Shoreline shrubs/reeds are sparse pale-yellow leaf cards with alpha gaps; their hue is 45° too warm (albedo). 2. Near trees: blue-violet impostor smear at cam01/05, a
hard-edged dark blob at cam02; two trees (broadleaf_s19, pine_s29) genuinely unlit. 3. Probe-lit surfaces without baked light have no occlusion: cam03 near shade p10 53 vs 17,
S-colonnade wall flat, backdrop wall 1.26x. 4. Backdrop: untextured mustard blocks and faceted far trees (cam06). 5. Open water beside the reflection: hue 196 vs 145°,
sat 8.9x, lum 0.75x (reflection lobe vs sky). 6. Column shafts at cam03 smear vertically at 100 %. 7. 35.5 fps, not 45. 8. Walk probe re-run at 30 s per heading owed.

# Phase 6c — the foliage gate (lead, 2026-09-17; CLOSED WITH RESIDUALS by docs/qa_round_17.md and decisions.md "6c CLOSED WITH RESIDUALS")
## What changed (main at 401e6dd, captured as round16c; branches phase6-bake 784808e, phase6-export edaa437, phase6-viewer a1bf41d)
- Trees: crown-bent leaf normals and translucency on the near meshes; a 2K impostor atlas with per-prototype irradiance modulation (`impmod=full`) and an
  enclosure term (`impint 0.90/0.015`) that gives the far crowns a dark interior and a lit rim; far trees switch to mesh at 12 m, near trees at 40 m; a walk-up
  LOD1 glb (`env_trees_lod1.glb`, 7.6 MB, 25.6-30 k tris per prototype, drawn within 15 m) for the 16 prototypes.
- Shrubs and reeds: LOD1 card clusters within the walk-in distance (`shrublod`), a Cycles-measured albedo check (shipped albedo 0.87-0.98 of what Cycles uses;
  `albedo_check.json`), the environment lobe on flat cards cut to 0.3 (`cardenv`/`shrubenv`), crown/card interior terms (`crownint`, `cardint`), `foliagebias 0.8`.
- Every switch and its shipped default is in web/README.md ("src/foliage.js"); the bare URL boots this look. Nothing outside foliage changed: every round-14/15
  architecture box is unmoved (hero shade band 0.99x, S-colonnade mid 0.45x, attic sat 0.87x, cam04 coffer 1.02x, N-colonnade wall 1.26x).
## Measured (round16c; docs/qa_round_17.md)
| station | round 17 | round 15 | Phase 5 | MAE vs Cycles (full frame, r16b -> r16c) |
|---|---|---|---|---|
| 01 hero | 3.78 | 3.72 | 3.67 | 24.79 -> 24.75 |
| 02 | 3.25 | 3.00 | 2.94 | 20.48 -> 18.68 |
| 03 | 2.63 | 2.56 | 2.56 | 35.41 -> 34.80 |
| 04 | 2.88 | 2.88 | 2.81 | 13.08 -> 13.08 |
| 05 | 2.94 | 2.94 | 3.06 | 20.37 -> 21.32 |
| 06 | 2.83 | 2.83 | 2.67 | 18.41 -> 18.14 |
Foliage boxes: shrub bands 0.91-1.47x of the reference (round 15: 1.34-1.70x) with the hard-edge share halved (hero 6.82 -> 3.44 %, ref 1.77); crowns at target
(cam02 centre/edge 0.393 vs ref 0.364, cam05 range/mean 1.722 vs 1.773); the 3 m walk-in reads as a canopy. Frame time at 2560x1440, cold pass of record:
32.4 / 37.0 / 35.1 / 22.1 / 32.2 / 34.0 ms (hero 30.9 fps); resident 1 931.4 MB (texture 1 227.5 + render targets 443.8 + geometry 260.0; 1.61x the Gate 1
budget); load 664.0 MB in 6.74 s; walk clamp 24/24 probes at 30 s above WATER_Z + 0.1 (lowest -0.750 m); name sweep 0 new; bare URL = station-1 preset
(luma 0.9999x).
## Known issues (residuals from docs/qa_round_17.md §7 and decisions.md; owners; nothing here is worked before 6b ships)
1. Shrub and reed STRUCTURE: level, hue and edge softness at the reference, but the cards are broad flat angular blades with ~half the reference's leaf-green
   share at five boxes (cam03 1.53x at 8 m, hero 1.47x). Owner EXPORT: a denser LOD1 card set (more, smaller, more varied cards per cluster). 2. The darkening
   overshoots: hero crown p10 0.57x of the reference, station 5 runs 3 % under and is the only station whose MAE rises, some crowns blotchy near-black. Owner
   VIEWER: clamp the stacked impint + crownint + sun-path darkening, hold the frame at 1.00x. 3. A pale halo around the now-dark crowns (alpha fringe on the
   impostor cut-out). Owner VIEWER: premultiply / mip bias on the atlas edge. 4. Far-tree tops opaque where the reference shows sky (cam02, cam03). Owner
   BAKE/EXPORT: atlas alpha at the crown top or a mesh at that distance. 5. Lavender far impostors at the horizon band (station 2 top-left). Owner VIEWER: the
   modulation at the horizon. 6. One reed spray several times the reference's size (station 2). Owner EXPORT. 7. MAT_reeds albedo 1.49x on 0.6 % of card pixels,
   measured and left (moves the worst box < 0.3 %). Owner EXPORT. 8. Resident 1 931.4 MB (1.61x budget) and a 664 MB payload: 6b's tiers. 9. Carried from 6a
   unchanged: cam03 has no deep shade (1.64x) and its column concrete is blurred and banded at 1 m (materials/export texel budget); cam06 water moiré at grazing
   incidence; backdrop city blocks flat and untextured, backdrop trees faceted (in the Cycles source too); S- and N-colonnade backdrop walls untextured (N 1.26x);
   hero reflection cooler and less saturated than Cycles, open lagoon a flat teal slab; 30.9 fps cold at the hero against the 45 target.
Perf A/B (same session, docs/perf_ab_6c.md): the 6c look costs +1.75 / -0.75 / +3.10 / -0.10 / +0.90 / +0.85 ms over the round-15 look at stations 1-6
(drift control 0.0-2.1 ms), so the +3 ms gate passes at five stations and sits on the line at station 3 (the walk-up LOD1 within 15 m, +1.5 M tris);
the cold pass's +4 ms at stations 1/2 was machine drift. Resident 1 931.4 vs 1 788.0 MB on the same build (the walk-up set).

# Phase 6b — web deployment (lead, 2026-09-18; verdict per docs/qa_round_18.md, appended below when it lands)
## Deliverables
- Staging URL (unlisted, no auth): https://pfa-walkthrough.3d-render-blender-3rd-attempt-building.workers.dev — Cloudflare Workers static assets (free tier; wrangler 4.135
  delegates Pages to it), 694 files / 615 MB published from the manifest's `files` plan across export/out/gate0..gate5, every file under 25 MiB, HTTP/2 + Brotli on
  html/js/json, cache: site 300 s, plan JSONs 60 s, bake files immutable. Deploy = `web/deploy.sh --project pfa-walkthrough` (dry-run needs no login); logs renders/logs/6b_deploy_*.log.
- Load tiers (manifest v5, export/tiers.py, export/gate5_visibility.py): tier 0 = the hero's first frame (arch + ground glb, ORN low LOD groups, the LUT, sky, probe, half-res
  ETC1S stand-ins of the hero-visible maps) 48.2 MB planned / 46.8 MB measured on the wire before the first frame; tier 1 = 490.4 MB (full-look textures, lightmaps, ORN LOD0
  groups in hero-visibility order); tier 2 = 69.8 MB. The viewer boots on tier 0 (`window.__pfaReady`), streams tiers 1-2 with material hot-swap and lightmap binding, one GPU
  upload per URL, `?tiers=0|N|all`, a tier readout; after tier 2 the frame is the 6c frame (parity vs round16c MAE 0.02-0.26 of 255 at the six stations, luma 1.000-1.002).
- Mobile tier (`?tier=mobile`, auto by a GL/UA/dpr probe; iPhone 16 Pro target): manifest_mobile.json, 61.4 MB total, first frame 47.6 MB planned; LOD1/decimated geometry,
  half-res ETC1S, impostors for every tree, shrubs LOD2, sky-only reflection, LUT-only post, drawing buffer <= 1.5 Mpx; resident estimate 306 MB (< 700).
- Reproduction: export chain items 27-47 in export/README.md; viewer "Phase 6b" in web/README.md; captures by `web/tools/gate5.sh <url>` (stations 1-6, payload log, perf,
  mobile), QA fixtures renders/web/gate5_* and 960 px copies in renders/web/960/.
## Measured on the staging URL (gate5 capture, 2026-09-18)
| item | value |
|---|---|
| bytes before the first frame | 46 814 308 B (320 requests) — definition of done <= 50 MB PASS |
| time to first frame / all tiers | 8.1 s / 74.5 s on the lead's connection; 581 MB over 622 requests |
| hero draws / tris after tier 2 | 335 / 5 245 128 (round16c 329 / 5 242 248) |
| 1440p medians, right after the 30-min capture | 31.7 / 38.0 / 37.7 / 25.1 / 34.2 / 34.2 ms, resident 1 861 MB (A/B pass B 29.7 / 30.4 / 33.5 / 22.0 / 29.8 / 32.3) |
| 1440p medians, cold pass (machine idle 15 min) | 30.8 / 37.2 / 37.9 / 24.3 / 33.2 / 34.3 ms, resident 1 861 MB — the tiered build costs about +1 / +7 / +4 / +2 / +3 / +2 ms over the A/B baseline; stations 2-3 under diagnosis |
## Known issues (owners)
1. The tier-0 first look (approved by the user): low-res concrete, saturated columns, coarse water reflection, no trees for the first seconds; trees and sharp maps arrive with
   tiers 1-2. 2. Three `.001` shrub cards are drawn inside a gltfpack-merged node and stay probe-lit (no irradiance key) — export. 3. arch.glb / ground.glb embed 15 / 4 Gate 1
   stand-in images (overwritten by the Gate 2 sets; not tier-upgradable) — export. 4. Workers static assets serve no byte ranges (200 to a Range request); the loaders fetch
   whole files — viewer carry for any future range loader. 5. The 28 + 31 trimmed placeholder maps (<= 0.019 % of the hero frame each) carry no map until tier 1 — export.
6. Every 6c residual in the Phase 6c section stands. 7. Owed from the user: the Safari hero screenshot and the iPhone 16 Pro 30 s walk against the URL.

## Verdict and close (QA 18 -> ONE FIX ROUND -> QA 18b: 6b DONE WITH RESIDUALS, 98ab252; decisions.md "6b DONE WITH RESIDUALS")
| item | desktop | mobile (iPhone 16 Pro tier, `?tier=mobile`) |
|---|---|---|
| bytes before the first frame on the URL | 46 808 904 B (PASS <= 50 MB) | 46 738 628 B |
| total stream | 581 MB / 622 requests / 74.5 s | 61.7 MB |
| resident | 1 861 MB | 499.7 MB (target < 700) |
| draws / tris (hero) | 335 / 5.25 M | 169 / 1.78 M |
| scores 01-06 | 3.78 / 3.25 / 2.63 / 2.88 / 2.94 / 2.83 (carry) | 2.9 / 3.0 / 2.3 / 2.7 / 2.5 / 2.4 (first) |
| page errors / 404s | 0 / 0 | 0 / 0 (favicon only) |
Fix round: the seven mobile group glbs were unpublished (deploy plan from the desktop manifest only) -> publish set = union of both plans with verify_publish (1 051 paths);
the mobile tier was fetching the desktop textures -> by-name redirect (resident 1 453 -> 500 MB); loading-bar denominators; the mobile canvas filled 51 % of the page ->
full CSS size with the cap on the pixel ratio (found and fixed inside the closing round, gate5c).
Residuals (owners): 1. mobile water reflects nothing — hero lagoon without the rotunda, station 6 bay near-black (viewer; reduced reflection set on the mobile Reflector).
2. mobile portrait framing small and centred (viewer/station choice). 3. 302 by-reference mobile paths not named in files[] (export). 4. per-group duplicate
materials/programs, -si 0.5 facets, three .001 cards probe-lit, arch/ground embedded stand-ins (export). 5. every 6c residual above. Owed from the user: Safari hero
screenshot; iPhone 16 Pro 30 s walk on the URL. Redeploy = `PFA_MAIN_ROOT=<main> web/deploy.sh --project pfa-walkthrough` after `npx wrangler login`; captures = `web/tools/gate5.sh <url>`.
Post-close fix (2026-09-18, 1c4b0f5, deploy 5): the bare URL defaulted to the unpublished gate3 manifest and drew the viewer's test scene; the default is now the gate5
manifest and the bare URL was verified headlessly (renders/web/960/bareurl_cam01.jpg). If a phone still shows the test scene, reload: index.html is cached 300 s.
User evidence 2026-09-18 20:59: iPhone 16 Pro, iOS Safari, 5G, bare URL, portrait — the mobile tier auto-selected and drew the whole hero scene
(renders/web/user/iphone16pro_hero_portrait_20260918.jpg). Visible in it: the two mobile residuals (no reflection in the water; the building small and centred in portrait)
and a cosmetic one: the station HUD prints shift_y as 0.05999999865889549 (viewer, format to 2 decimals). Still owed: the 30 s walk recording and the Mac Safari screenshot.
6d (2026-09-18, d40a125, deploy 6): the mobile water now reflects the building (reflection set `both`, half-res target; +~110 draws per station); HUD shift_y formatted.
Residual 1 of the 6b list is closed pending the phone's own frame rate from the user's walk recording.

## Evidence closed by the lead (2026-09-18, session 6 end)
- iOS Safari, iPhone 16 Pro, 5G, bare URL (user's screenshot): the mobile tier auto-selects and draws the hero scene — renders/web/user/iphone16pro_hero_portrait_20260918.jpg.
- Mobile-tier walk on the URL (headless, viewer walk probe, renders/web/6dm_walk.json): 24 probes = six stations x four headings x 30 s at 3.2 m/s; lowest ground -0.75 m
  against water -1.3 (floor -1.2); every lagoon-ward heading refused; 0 errors. The phone's own frame rate with the 6d reflection remains unmeasured (a walk recording on
  the device would settle it; the Mac cannot).
- Safari-engine desktop render: WebKit 26.6 (Playwright's WebKit build; Safari.app itself could not be captured — screen recording is not granted to the terminal and
  safaridriver needs the user's password) at 1920x1080 after 120 s draws the full 6c look with the reflection and the formatted HUD, matching the Chrome capture —
  renders/web/user/webkit26_hero_1920x1080_20260918.jpg. A Safari.app screenshot by the user would be a confirmation, not a requirement.

# Phase 7 — foliage look on the live site (lead, 2026-09-19; QA 19: PHASE 7 DONE WITH RESIDUALS, 6253d32; decisions.md "PHASE 7 DONE WITH RESIDUALS")
Live: https://pfa-walkthrough.3d-render-blender-3rd-attempt-building.workers.dev (deploy 7). What changed (viewer only, 91f08b4): premultiplied impostor edge reconstruction + alpha-to-coverage; a 0.35 floor on the stacked crown darkening;
near-tree mesh switch 80 m; mobile far-tree meshes within 45 m, LOD1 shrubs within 25 m, LOD2 walk-up set, eased impostor darkening.
| item | before (gate5b/c) | after (gate7) |
|---|---|---|
| hero crown p10 vs Cycles | 0.564x | 0.894x |
| cam02 crown centre/edge (ref 0.364) | 0.368 | 0.397 |
| desktop scores 01-06 | 3.78 / 3.25 / 2.63 / 2.88 / 2.94 / 2.83 | 3.78 / 3.25 / 2.63 / 2.88 / 3.06 / 2.83 |
| mobile scores 01-06 | 2.9 / 3.0 / 2.3 / 2.7 / 2.5 / 2.4 | 3.2 / 3.3 / 2.3 / 2.7 / 2.8 / 2.4 |
| mobile resident | 499.7 MB | 561.9 MB (ceiling 700) |
| desktop first frame on the URL | 46 808 904 B | 46 811 106 B |
| desktop 1440p vs idle baseline | — | +0.8 / +0.1 / +1.0 / +2.0 / +2.7 / +2.2 ms |
Known issues (owners): 1. far-tree cards opaque where Cycles shows sky through twigs (bake/export: atlas alpha). 2. shrub/reed card density (export, Blender; deferred).
3. crown floor overshoot at cam02/cam05 (viewer). 4. station 5 frame 0.976x (carried). 5. mobile LOD2 leaf cards too large at 37 m; shaded colonnade blue-violet on mobile
(export / viewer). 6. walk-up LOD1 set lit brighter than its impostor (export/bake). Every earlier residual not named here stands.

# Phase 8 — the five remaining art items (lead, 2026-09-19; QA 23 8d775ae + QA 24 b683412: ALL FIVE CLOSED, no open blocker; decisions.md "QA 23", "QA 24")
## Deliverables
- Live site deploy 12: https://pfa-walkthrough.3d-render-blender-3rd-attempt-building.workers.dev (version 6513cf48). First frame on the wire 46 756 312 B desktop / 46 824 683 mobile
  (rule 50 000 000); resident 1 814.2 MB desktop / 550.3 mobile (counter rewritten this phase: the impostor atlases are now billed); 0 page errors; name sweep 0 hits.
- Before/after sheet the user asked for: renders/qa_comparisons/phase8_before_after_960.jpg (viewer hero deploy 7 vs deploy 12; Cycles 4K hero Phase 5 v2 vs the new
  Phase 8 render; ref 169), full-resolution crops in renders/qa_comparisons/phase8_tiles/ (colonnade backdrop band, shore shrub band, far crown; boxes.json), station pairs
  renders/qa_comparisons/phase8_stations/phase8_cam0[2-6]_960.jpg. New 4K Cycles hero renders/final/hero_cam01_3840x2160_128spp.png (128 spp fixed, 1 468 s; lead tile pass
  clean); the Phase 5 v2 renders preserved in renders/final/phase5_v2/. Phase 8 Cycles station references (1080p / 32 spp) at renders/qa_comparisons/cycles_p8/960/.
- master.blend / master_delivery.blend rebuilt (belt r2 + backdrop materials); every web asset regenerated by the export chain (export/README.md "Phase 8d", "Phase 8e").
## What changed, per item (scores hero 3.78 -> 4.01; stations 3.25 / 2.75 / 2.88 / 3.06 / 2.89 -> 3.30 / 2.83 / 2.88 / 3.28 / 3.07; mobile 3.2 -> 3.40 at the hero)
- 8a shrubs: the LOD2 set clumped and densified (ENV), then re-scoped — the gap was the cards' flat warm shading, not their count: a viewer-side directional relight
  (`?cardsun=`, level held) plus an export-side per-card UV scale k = 2 (shrub_dry ku 1 kv 2, reeds 1) that made the 25 m LOD switch invisible. CLOSED at 1 and 5 on the tiles;
  residual: the cam03 bush interior is 2.4x too bright — a lighting carry (the station's missing deep shade), not a card defect.
- 8b far-tree crowns: the 2K atlases restored to tier 1 and alpha sampled as coverage, then the 12x3 band atlas (341 px frames) adopted as default at share 0.10 —
  hero crossings 5.73 -> 11.97 (Cycles 11.73), station-2 crown with limbs and sky. CLOSED (QA 21). Residual: a 1-2 px dotted rim on far-crown silhouettes at 2 and 5.
- 8c column concrete: the vertical banding was the detail layer's objxy projection on a vertical shaft; `?detailproj=dominant` default. CLOSED (QA 20).
- 8d backdrop: the hall wall behind the north colonnade sits at 0.79 texels/m so no bake can texture it; instead R1 low-frequency backdrop materials (haze, lot spread, palace
  shade, desaturated hall face) and a belt of 39 real far trees on baked impostor prototypes along the hall's east face (the icosphere belt of r1 failed QA 22 as shards).
  CLOSED (QA 23): real crowns with sky gaps between the columns, parity to the Phase 8 Cycles refs improved at every band. Residuals: the belt covers less pale backdrop
  than Cycles; cam06's city blocks stay faceted (R3 tiled facade atlas deferred; faceted in Cycles too); cam03 draws 3 belt trees as meshes (+1.3 M tris; a walk-up rule
  for HB-tagged trees would save 1.16 M, recorded).
- 8e mobile leaf cards: the "40 px blades" were a mip artefact; export-only UV tiling ku 2 / kv 3 with per-material cutoffs solved for coverage. CLOSED: blade p90 29.5 -> 22.7 px,
  5/6 boxes <= 25, coverage 0.99-1.00x; the 2.5 m walk-up frame delivered.
- Fix round: the LOD1 walk-in shrub set never had a distance cull (2.02 M tris per frame at every station) — culled; resident counter rewritten; the cam02 blue-violet shade
  measured as the Phase 5 lighting itself (viewer at parity, deferred to the user); every glTF root now agrees on leaf-sampler wrap.
## Process notes worth keeping
- Two deploy-breaking bugs were caught by review, not by tests: a GLSL literal that broke the build (four "tests green" claims were false — builders now paste the suite
  count), and manifests written before the far-tree glbs (127 vs 166 rows would have dropped the whole far-tree layer; count guards now in manifest_v4 and verify_glb).
- The far-tree irradiance re-bake moved the 127 existing rows +48 %; accepted for verification, failed QA 23, reverted to the md5-verified 6c rows in one CPU round (QA 24).
- Parity is measured against Phase 8 Cycles references for the backdrop boxes (the viewer moved away from the frozen Phase 5 look there by design); architecture parity
  with Phase 5 holds inside the 32 spp noise floor.
## Known issues (owners), carried
cam03 deep shade / bush interior (LIGHTING); far-crown dotted rim (VIEWER); belt pale-backdrop cover and the shrub hard-edge rise 5.95 / 7.12 % (ENV); cam03 belt meshes
(EXPORT/VIEWER); cam06 faceted city (ENV, R3 deferred); the cam02 blue-violet Phase 5 shade (user's call); 1440p medians drift up to +5 ms between sessions (re-take idle);
water reflector not session-reproducible (A/A mask rule); the Phase 8 Cycles refs survive at 960 px only.

# Phase 9 — everything carried, finished (lead, 2026-09-21; QA 25 a228268: PHASE 9 GATE PASSED, hero 4.05, no open blocker; decisions.md 2026-09-20/21). [deploy 14 / QA 26 / hero wall time filled at the close]
## Deliverables
- Live site deploy 13: https://pfa-walkthrough.3d-render-blender-3rd-attempt-building.workers.dev (version 201908ca). First frame on the wire 49.30 MB desktop / 47.32 mobile
  (rule 50 MB); resident 1 814.1 MB; 0 page errors; name sweep 0 hits over 738 + 341 manifest rows; belt frustum invariant PASS. Deploy 14 (the ENV R3 tiles) follows: [filled at the close].
- Phase 9 before/after sheet: renders/qa_comparisons/phase9_before_after_960.jpg (scripts/phase9_sheet.py; viewer hero deploy 12 vs deploy 13/14; Cycles 4K hero Phase 8 vs Phase 9; ref 169),
  station pairs renders/qa_comparisons/phase9_stations/, tiles renders/qa_comparisons/phase9_tiles/. New 4K Cycles hero renders/final/hero_cam01_3840x2160_128spp.png
  (128 spp fixed, [wall s]; lead tile pass [result]); the Phase 8 hero preserved in renders/final/phase8/. Phase 9 Cycles station references (1080p / 32 spp) at
  renders/qa_comparisons/cycles_p9/960/; QA gate sheet renders/web/gate13_gate.png.
- master.blend / master_delivery.blend rebuilt twice (r19 lighting; ENV R3 tiles); every lightmap re-baked (87 jobs, 0 failures, 455 min, 0 clipped pixels); the export chain
  regenerated every web asset (export/README.md "Phase 9"); scripts/build_master.py APPENDS (no --link): a before/after needs two lead_build.sh runs.
## What changed, per item (scores hero 4.01 -> 4.05; stations 3.30 / 2.83 / 2.88 / 3.28 / 3.07 -> 3.51 / 3.08 / 3.05 / 3.24 / 3.07; mobile 3.40 -> 3.44 at the hero)
- Lighting (station 2's blue-violet shaded stone, QA-08-2): the mechanism was not the NNE shade-fill lamp (0 W since f40d0e7) but the world's diffuse tint; SKY_DIFFUSE_TINT
  (1.0, 0.65, 70.0) -> (1.0, 0.75, 8.0), anti-sun weight 1 -> 0, diffuse sockets only. Cycles shafts b* -4.7 / -18.2 / -3.1 -> +11.3 / +5.3 / +8.8 (photo +10.9 / +11.0 / +5.3);
  hero 12/12, cam03 7/7, cam04 6/6 held at the noise floor. The frieze (+23.3 vs 9.9-12.9) and soffits (h_ab 82.6 vs 80) overshoot: proven structural (the shafts' a* 2.5 vs the
  photo's 10.2 is a materials property) and shipped on the user's decision. In the viewer after the re-bake: station 2 mean |b* − photo| 10.34 -> 6.85. CLOSED with residual.
- Station 3's deep shade (QA-21 carry): decomposed by term on disk — the lightmap matched Cycles at 0.997x; the whole 2.55x excess was the viewer's unoccluded specular
  (environment PMREM + unshadowed sun). Fixed viewer-side, zero GPU: skyVis = lightmap blue / the unoccluded sky irradiance for the surface's own normal (a 40-lobe fit of the
  shipped sky, written by manifest_v4), sunVis = (lightmap red − sky share) / (sun irradiance/π · dotNL); ?specgate=0/1 keep the Phase 8 and round-1 paths. near_column 1.80x ->
  1.38x, blue closed, frame p10 37.5 -> 13.3 (Cycles 6.1). Residual: the remaining 1.4x red is not in either specular term (bake/materials).
- Far-crown dotted rim (QA 21): the impostor mask's own alpha-to-coverage pixel dither; coverage quantised to the sample ladder. Rim index 0.264 -> 0.043 at 5, 0.369 -> 0.058 at 2. CLOSED.
- Belt trees at cam03 (+1.3 M tris): a billboard-only rule — an HB-tagged row keeps its mesh only within its set's draw distance + 5 m of a QA station; walk-up 4 kept / 35 billboard-only
  (−1 047 151 tris), far 22 / 17; the --frustum invariant fails by name if any in-frame belt row ever goes billboard-only. No viewer change was needed (all far trees are lit at build). CLOSED.
- Aerial city blocks (8d R3): four tileable gain maps (facade 64 texels/m, roof, mission tile 8.10 x 7.92 m, canopy) on a per-face UV0 in tile units over 1 291 backdrop meshes,
  multiplied after the atmosphere term; cam06 city hf +11.6 / +24.3 / +20.3 % (Cycles +27.6 %), ENV tri delta 0. The belt cover measured OVER the photo (no crown added); the shrub
  hard-edge rise is the belt behind them (positions md5-identical). In the viewer: [deploy 14 / QA 26, filled at the close].
- Review carries closed across viewer, export and bake (docs/reviews/phase9_*): 12 branches merged, every one reviewed; the far-tree irradiance restore patch retired (all 166 rows one population).
## Process notes worth keeping
- The bake queue's resume rule skips any job whose record file exists: a re-bake must archive the old records first (done: export/out/gate3/bake/bake_p8_backup). The A.2 probe
  (3 jobs, 321 s) showed the slot atlases move too (p50 0.18 stops, 1.8x the floor), so the full chain ran; the shipped bake had been dated Sep 15-16, so this caught up every
  lighting round since.
- gate3_relay_check must run before manifest_v4 (it writes the COLOR_0 range v4 copies); the README chain now says so; web/test/gate3_test.mjs caught the stale range.
- A viewer constant derived from the sky (open irradiance, lobes) must be re-derived by the manifest on every bake, never hard-coded: the r19 tint halved the open-sky blue (11.26 -> 5.82).
## Known issues (owners), carried
Station 2 frieze/soffit over-warm and the shafts' a* deficit (MATERIALS; accepted residual); cam03 near_column 1.4x red (BAKE/MATERIALS); far-crown deviation 7.5 -> 9.6 % at two
boxes after the full far-tree re-bake (BAKE/EXPORT; QA 23 residual 1 partially re-opened); cam05 shade p10 −5.9 % vs Cycles with the gate on (VIEWER; ungated +6.8 %); frame rate
22-37 fps at the stations, never measured idle (perf re-take); cam01/cam05 backdrop bands −1..3 % hf after R3 (ENV, named); the 4.3x hf gap to the photo at cam06 is the R1 ceiling.
