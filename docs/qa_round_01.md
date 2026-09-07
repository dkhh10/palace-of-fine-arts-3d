# QA round 01 — Phase 2 gate (2026-09-07)

QA / Critic. Reviewed `master.blend` (110 MB, built by `scripts/build_master.py` 2026-09-07 07:56: ARCH + ENV + ORN + LIGHT appended,
1260 ornament instances on 336 sockets, viewport LOD1 / render LOD0, lighting rig + `AgX - Base Contrast` + `COMP_golden_hour`).
**All 28 materials are still flat placeholders** (single Principled BSDF, roughness 0.7, no textures) because the materials
library has not landed. Material realism and edge wear are scored honestly below but those two rows are *expected* to be
near zero this round; nothing else in this report is excused by it.

## What was rendered and compared

| file | what |
|---|---|
| `renders/previews/qa/round01_0K_*.png` | Eevee 1280x720, 32 TAA, `light_presets.apply_preview_eevee` (raytraced reflections, fast GI). Times: 14 / 25 / 33 / 14 / 8 / 8 s. |
| `renders/previews/qa/round01_01_lagoon_hero_cycles.png` | Cycles 1920x1080, 128 spp adaptive, OIDN, `light_presets.apply_final_cycles`. **65 s** on the M2 (full scene, LOD0). A 4K hero at 768 spp extrapolates to roughly 25-40 min, comfortably inside budget. |
| `renders/qa_comparisons/round01_cam0K.png` | render / canonical photo (letterboxed) / 50 % blend, via `qa_compare.py` |
| `round01_cam01_vs_ref169.png`, `round01_cam01_cycles_vs_ref169.png`, `round01_cam01_cycles.png` | hero against the golden-hour twin (ref 169) and the user image |
| `round01_cam01_aligned_vs_ref169.png`, `round01_cam01_aligned_vs_user.png` | **new** `scripts/qa_silhouette.py align`: photo scaled so its attic-corner width W_a and corner-urn row coincide with the render's, then blended with both silhouette profiles drawn (render red, photo cyan). The stock blend panel letterboxes the photo and cannot be used for the 2 % silhouette test. |
| `round01_cam01_profile_render.png`, `round01_profile_ref169.png`, `round01_profile_ref085.png` | silhouette profiles used for the dome measurement (green = apex row, cyan = corner-urn row, magenta = W_a row) |
| `round01_sheet.png` | contact sheet of the six comparisons |

Renderer: `scripts/qa_render_round.py -- --round 01 --eevee` and `-- --round 01 --final --samples 128 --res 1920 1080 --cams 01`
(the Cycles pass is spelled `--final` because Blender prefix-matches `--cycles-*` even after `--`).

## Score table (0-5, checklist rows; target >= 4 everywhere, hero average >= 4.5)

| row | cam01 hero | cam02 NE 3/4 | cam03 colonnade | cam04 ceiling | cam05 S lawn | cam06 aerial |
|---|---|---|---|---|---|---|
| Silhouette match | 3 | 1 | 1.5 | 4 | 1.5 | 3 |
| Proportion | 3 | 3 | 3.5 | 4 | 3.5 | 3.5 |
| Ornament fidelity | 3 | 3 | 3 | 2.5 | 2.5 | 3 |
| Material realism (placeholders) | 1 | 1 | 1 | 1 | 1 | 1 |
| Edge wear (placeholders) | 0 | 0 | 0 | 0 | 0 | 0 |
| Lighting mood | 3.5 | 3 | 3 | 1 | 3 | 2.5 |
| Water reflection | 1 | n/a | 1 | n/a | 1 | 1.5 |
| Repetition visibility | 2 | 3 | 2 | 3 | 2 | 2 |
| Scale cues | 3 | 2 | 3 | 3 | 2.5 | 3 |
| **average** (n/a excluded) | **2.2** | 2.0 | 2.0 | 2.3 | 1.9 | 2.2 |

Gate verdict: **not passed** as a photoreal gate (expected: no materials yet), but the architecture is in far better shape
than either previous attempt, and every blocker below has a concrete, cheap fix. Rejects for "game asset / clean CAD"
reading: the shoreline shrubs (QA-01-2), the lagoon water (QA-01-3), the leaf cards (QA-01-7), the hall backdrop box (QA-01-8),
the flat placeholder concrete (QA-01-17, expected). Reasons are given per defect.

## What already works (keep it)

- **The vertical stack from pedestal to attic cornice matches the photographs.** With W_a and the corner-urn row aligned
  (`round01_cam01_aligned_vs_ref169.png`, `..._vs_user.png`), the entablature, capitals, arch crown, shafts and pedestal tops
  of the render sit within about 1-2 % of frame height of both ref 169 and the user image. Column pair spacing and arch span
  read right. This is the first time in three attempts that the rotunda's body survives an overlay.
- Ornament is on every socket and at the right sizes (measured in the blend: podium urns 3.0 m, niche urns 1.6, maidens 4.36,
  attic figures 6.8, rotunda capitals 2.6, inner/colonnade capitals 1.8, attic panels 10.5 x 4.5, keystones 0.73).
  Corinthian capitals, urns, keystone masks and the attic corner figures are recognisable as the PFA's at hero distance.
- Colonnade shafts are fluted (cam03 crop), boxes carry four maidens each, both wings follow the OSM arcs, pylons present.
- Lighting direction and character: sun az 118.5 / el 7.4 verified in the file; long soft shadows, the lagoon face lit,
  north faces and arch interiors in sky-lit blue-grey shade, no crushed blacks in the exterior. Reads as morning golden hour.
- Site layout in the aerial matches OSM: lagoon outline, islet, peninsula, both wings. Gulls on the water and shore give scale.
- Performance: full-scene Eevee previews 8-33 s, Cycles 1080p/128 spp 65 s. LOD manager works (717 LOD0 objects render-only).

## Measurements behind the scores

**Dome (the one proportion that is wrong).** Visible dome rise above the attic-corner urns, in units of the attic corner width
W_a, measured with `scripts/qa_silhouette.py measure` on the sky/building silhouette:

| image | viewpoint | rise / W_a |
|---|---|---|
| render, Cycles hero (cam01, 27 mm, 100 m, z 1.0) | lagoon, ground level | **0.161** (apex y 140, urn row 259, W_a 741 px) |
| ref 169 (golden-hour twin) | same spot | 0.252 |
| user image (composition target) | same spot | 0.204 |
| ref 085 (telephoto, the sheet's proportion reference) | east shore, far | 0.195-0.199 |
| ref 022 (frontal) | east shore | 0.262 |
| ref 063 (cam05 photo) | SE, 55-80 m | 0.295 |

Aligned overlay: the render's apex is **67.6 px = 6.3 % of frame height too low** against ref 169 and 3.0 % against the user
image (tolerance 2 %). In all five photos the drum (scale band + cornice ring) is fully visible *above* the corner blocks and
the dome springs steeply from that ring; in the render the drum is a one-pixel sliver behind the attic and the dome is a
saucer. Because the lower stack aligns, the error is in the dome/drum: the apex sits about 4-5 m too low relative to the
attic top, and/or the cap is too flat. Built values (from the blend): `ARCH_rotunda_dome` z 41.85-49.4, cap radius 16.5;
`ARCH_rotunda_drum` z 37.9-39.3. The reference sheet derived "rise 7.6 m" from the *foreshortened* rise in ref 085 and
forced the sum to the DPR's 162 ft; the photographs, which are the art target, disagree with that sum.

**Hero composition.** Far shoreline at 86 % of frame height in the render (y ~930/1080) vs 69 % in the user image and 53 %
in ref 169: the water band that carries the signature reflection is 14 % of the frame instead of 31-47 %. Attic corner
width is 38.6 % of frame width in the render vs 34.1 % in the user image (rotunda ~13 % too large in frame).

**Colour / luminance (sRGB means, render vs photo, same regions).** Hero (Cycles) vs ref 169: sunlit attic panel (184,145,109)
vs (230,186,101) — 20 % darker, hue 29 deg vs 40 deg (less golden); sky at horizon (153,170,184) vs (183,217,236) — 20 % darker
and grey; sky top (122,152,185) vs (118,171,222); dome (170,137,107) vs (229,208,160); water centre (92,81,65) vs (138,94,49);
near water (82,70,58) vs (43,69,84) — the render's water is uniformly brown-grey, the photo's is a warm building reflection
over a blue sky reflection. Ceiling (cam04, Eevee) coffer field (29,26,19) vs ref 083 (123,106,79): **4x too dark in sRGB**.

**Camera framing.** cam02 render shows podium to capitals only (photo: apex at 3 % from top, ground at 95 %). cam05 render
cuts the attic (photo: apex at 4 %). cam03: no near-row shafts framing the view (photo: shafts at x 0-30 % and 50-70 %),
a cypress fills the left 30 %. cam02: a broadleaf tree fills the right 40 % (photo: open).

## Defect list

Severity: **blocker** = must be fixed before the next gate; **major** = fix in the polish loop, visible at hero distance;
**minor** = visible in a specific view or on close approach. "Where" gives object names in `master.blend`.

| id | cam | owner | sev | defect (measurable) | where | acceptance test |
|---|---|---|---|---|---|---|
| QA-01-1 | 01, 05, 06 | architecture (lead to arbitrate vs reference sheet) | **blocker** | Dome + drum too low/flat: visible rise 0.161 W_a vs 0.195-0.30 in five photos; apex 6.3 % of frame height low vs ref 169; drum invisible from the lagoon. Reads as a flat lid — exactly the "dome too smooth / proportions drifted" failure of attempts 1-2, in the opposite direction. Suggested: keep W_a, attic and everything below; drum 3.5 -> ~4.5 m (band r 17.5, cornice r 18.7), dome rise 7.6 -> ~10 m (sphere r ~18.6), apex ~53 m. Lead to log that the photos override the DPR's 162 ft. | `ARCH_rotunda_dome`, `ARCH_rotunda_drum`, `_drum_band`, `_drum_cornice`, `arch_params.py` | `qa_silhouette.py align` on the Cycles hero: apex delta <= 2 % of frame height vs ref 169 **and** vs ref 085 profile; drum band + cornice ring visible above the attic cornice from cam01 (>= 12 px at 1080p, as in ref 169); lower stack unchanged. |
| QA-01-2 | 01, 03, 05 | environment | **blocker** | Shoreline shrubs/reeds are extruded polygon slabs, saturated green (57,63,36); in the hero they form a 6 % tall band across the full width at 78-84 % frame height. Pure game-asset read. Ref 169's shore is mounded foliage and dry reeds, warm (144,108,55). | `ENV_shrubs_shore`, `ENV_shrubs_pen`, `ENV_shrubs_islet`, `ENV_shrubs_col`, `ENV_reeds` | At 1920 px hero no straight-edged leaf card wider than 4 px; per-leaf cards <= 15 cm with translucency; species/colour mix per sheet s6 (mahonia, pittosporum, agapanthus, reeds); side-by-side crop at the waterline accepted by QA. |
| QA-01-3 | 01, 05, 06 | materials + environment | **blocker** | Water is a flat brown-grey mirror: no ripples (reflection unbroken), no murk, no Fresnel falloff, no blue sky reflection near the camera (82,70,58 vs photo 43,69,84), building reflection 35 % darker than the photo's (92,81,65 vs 138,94,49). | `ENV_lagoon_water` (z -1.3, 422 verts, no modifiers), `MAT_water_lagoon` | Ripple normals/displacement breaking the reflection into 0.3-1 m streaks (ref 169); Fresnel; volume absorption (0.04,0.07,0.04) over a 1.5 m bottom; reflection zone luminance >= 70 % of the building's; near water reads blue-green. Compare `round01_cam01_cycles_vs_ref169` water rows. |
| QA-01-4 | 01 | lead | major | Hero composition: shoreline at 86 % frame height (user 69 %, ref 169 53 %); rotunda 13 % too large in frame. The reflection, the point of the hero shot, is cropped to a 14 % band. | `CAM_qa_01_lagoon_hero` (shift_y 0.17, lens 27, z 1.0), `scripts/qa_cameras.py` | Shoreline at 65-72 % frame height, apex >= 8 % from the top, attic width 33-35 % of frame width (e.g. shift_y ~0.06, lens 25 mm or r 110 m). Re-run `qa_silhouette.py align`. |
| QA-01-5 | 02, 03, 05 | lead | major | QA cameras 02/03/05 do not reproduce their photos: 02 and 05 show only the lower half of the rotunda (16:9 sensor + too-long lens for 46-55 m); 03 stands inside the row instead of behind it. Scores on those cams are capped by framing, not by the model. | `CAM_qa_02_*` (26 mm), `CAM_qa_03_*`, `CAM_qa_05_*` (24 mm) | cam02: 17 mm or ~70 m; cam05: 16 mm or ~85 m; cam03: ~4 m outward (r ~90 m about (0,52)) so two near shafts frame the rotunda. Letterboxed blend shows the photo's apex and podium-base rows within 3 %. |
| QA-01-6 | 01, 02, 03 | environment (+ lead for cams) | major | Trees in the wrong places: a broadleaf fills the right 40 % of cam02 and a cypress the left 30 % of cam03 (photos are open there); the redwood/cypress screen behind both wings is missing, so in the hero the colonnades stand against blank sky and the grey hall box (ref 169: trees fill ~80 % of the bays behind the north wing). | `ENV_tree_instances_LOD0` (88 trees: 29 eucalyptus, 19 cypress, 13 pine, 10 redwood, 6 broadleaf, 6 cypress_column, 5 willow) | Hero: sky visible through <= 20 % of the colonnade bay area behind the north wing; cam02/03 lines of sight clear; species per sheet s6 (dark pine/cypress mass NE of the rotunda, willow at the water). |
| QA-01-7 | 01, 02, 05 | environment | major | Leaf cards are hexagonal fans 20-30 px wide at hero distance (crop x 1280-1920, y 440-800 of the Cycles hero); crowns read as low-poly clusters, foliage too light (90,110,50) for Monterey pine/cypress (photo ~60,70,40); no translucency. | `ENV_tree_*_LOD0` source meshes, `MAT_leaf_*` | At 1920 px no single card wider than 6 px at 60-80 m; leaf translucency; crown silhouettes irregular (compare the pine right of the rotunda in the user image). |
| QA-01-8 | 01, 06 | environment | major | Exhibition-hall backdrop is a clean 20 m box (~150,150,150): it appears as a 4 % x 8 % grey rectangle dead centre in the hero's main arch (ref 169 shows the hall's buff wall, cornice and green door there) and dominates cam06 as a white crescent. | `ENV_backdrop_hall` (268 x 119 x 20 m), `ENV_backdrop_hall_detail`, `MAT_backdrop_building` | Through the arch: buff stucco facade with door/cornice matching ref 169 at that crop; from cam06 a curved roof profile and darker walls; no flat untextured face > 2 % of the hero frame. |
| QA-01-9 | 04 | lighting | major | Rotunda ceiling 4x too dark in Eevee (coffer field 29,26,19 vs 123,106,79) — no bounce light; no light probes in the file. The Eevee viewport deliverable will show a black ceiling. | scene `PalaceOfFineArts`, no `LIGHT_PROBE` objects; `light_build.py` | Irradiance volume (or equivalent) covering the rotunda interior baked into `lighting.blend`; cam04 coffer field >= 0.35 of the sunlit exterior wall luminance (photo 0.53); verify Cycles also lifts it (3 diffuse bounces may be short). |
| QA-01-10 | 01, 05 | ornament | major | Zimm attic panels are sparse: one horse + two figures + two rosette motifs on a 10.5 x 4.5 m field (~15-20 % coverage) vs 8-12 figures filling ~70 % of the field in refs 169/022/063. At hero distance the panels are 5 % of frame height and the emptiness is the most visible ornament defect. | `ORN_attic_panel_v1..3_LOD0`, `INST_attic_panel_*` | >= 8 figures ~3.5 m tall per panel, >= 60 % field coverage, three designs A/B/C; crop of the front panel vs ref 169 crop accepted. |
| QA-01-11 | 05, 02 | ornament + architecture | major | Podium (rostra) band is a plain strip; the Greek-key meander with rosette bosses (sheet s4 #12) is absent although `ORN_greek_key` / `ORN_rosette_band` exist and are never instanced (no `INST_greek_key`). In ref 063 the band is ~6 % of frame height across the full width. | `ARCH_site_rostra_band_00..06`, `ORN_greek_key`, `ORN_rosette_band`, socket contract | Relief band (meander depth >= 3 cm, rosettes 0.45 m) along all rostra walls and box bases, readable in cam05 at 720 px. |
| QA-01-12 | 01 | lighting (re-check after materials) | minor | Golden-hour mood slightly under: sunlit stone 20 % darker and less golden than ref 169 (hue 29 vs 40 deg), sky horizon 20 % darker and grey, no warm haze behind the wings. Placeholder albedo confounds the stone numbers; the sky/haze is lighting-only. | `WORLD_golden_hour`, `COMP_golden_hour` mist | After materials land: sunlit attic within +-10 % luminance and +-8 deg hue of ref 169; horizon band luminance within 10 %. |
| QA-01-13 | 01 | ornament | minor | Attic corner niches lack the paired volute scrolls (1.5 m) over the figure; corner caps are plain blocks with urns. Maidens: arms straight out like bars, heads not bowed (crop of the north wing). | `ARCH_rotunda_attic_corner_cap`, `ORN_maiden_v1..3` | Scrolls per ref 085 crop; maiden pose per ref 187/163 (arms on rim, head bowed into the box). |
| QA-01-14 | 01 | architecture | minor | 12 planter boxes / 48 maidens built (8 along the arcs + 4 pylon boxes); the sheet says 13 / 52 (uncertain). Garland relief panels (26) are plain sunk panels. | `ARCH_colonnade_*_box_*`, `INST_maiden_*` | Count boxes on ref 187 + OSM wing polygons and match; garland panel relief or a deliberate decision logged. |
| QA-01-15 | 02, 05 | architecture | minor | Vault coffers read as a rectangular grid of curved cells; ref 062 shows large octagonal coffers alternating with squares, with rosettes. | `ARCH_rotunda_vault_coffers_*` | Octagon/square coffer pattern matching the ref 062 crop. |
| QA-01-16 | 02, 05 | architecture | minor | Lagoon-side stair is a plain flat flight without cheek walls or landing, placed centrally; ref 063 shows the flight running along the podium on the right with cheek walls. | `ARCH_site_stair_*`, `ARCH_site_step_*` | Position and cheek walls per refs 063/031. |
| QA-01-17 | all | materials | major (expected) | All 28 materials are flat placeholders: concrete reads as clean CAD, dome tan instead of cream (170,137,107 vs 229,208,160), columns flat rose, no streaks/algae/patches/dust. | every `MAT_*` in the file (`placeholder` = True) | Materials library per sheet s5 with the weathering map; round 02 re-scores Material realism and Edge wear. |
| QA-01-18 | 01 | ornament + lead | minor | Repetition: 12 of 16 rotunda capitals use variant 2 (`capital_rotunda` variants {1:1, 2:12, 3:3}); the per-instance `instance_seed` exists but nothing consumes it, so instances are pixel-identical. | `INST_capital_rotunda_*`, `build_master.py` variant pick | Round-robin variants per pier; the seed wired into the ornament material for per-instance weathering. |
| QA-01-19 | 01, 06 | environment | minor | Shore edge is a smooth bevelled tan shelf with a few rocks; aerial lawn is flat with no paths/roads; houses are boxes. | `ENV_riprap_*`, `ENV_terrain_ground`, `ENV_backdrop_houses` | Rip-rap boulders 0.3-0.8 m breaking the waterline; paths from OSM in the aerial. |
| QA-01-20 | 06 | lighting | minor | Dome blows out to near white from above (placeholder roughness 0.7 + low sun); re-check with `MAT_dome_membrane` semi-gloss. | `ARCH_rotunda_dome` | After materials: dome top luminance within 15 % of ref 105 relative to the lawn. |

## Notes for the lead

- The dome finding (QA-01-1) contradicts the reference sheet's forced 49.4 m apex. I measured five photos with the same tool
  and they agree with each other and disagree with the model; the aligned overlays show the rest of the stack is right, so
  the fix is local to drum + dome. Please arbitrate and log it in `docs/decisions.md` before the architecture agent touches it.
- Cams 02/03/05 (QA-01-5) are calibration problems, not model problems; until they are fixed those columns of the score
  table measure the camera, not the build.
- `scripts/qa_silhouette.py` is the tool for the "2 % of frame height" test from now on; `qa_compare.py` stays for the
  three-panel sheets.
