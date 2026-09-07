# Architecture notes (ARCH agent)

Owner: Architectural Modeler. Files: `scripts/arch_params.py` (every dimension, metres), `scripts/arch_lib.py` (geometry
helpers), `scripts/arch_build.py` (one idempotent entry point), `scripts/arch_compare.py` (FOV-correct photo overlay),
`assets/architecture.blend` (collection `ARCH`). Rebuild: `blender -b --python scripts/arch_build.py -- --preview`.
Stats of the last build are written to `docs/arch_stats.json`.

## Status log

- **Blockout (milestone 1)**: every element at true scale from the reference sheet — rotunda (podium lobes, pedestals,
  16 fluted columns with entasis + Attic bases, chamfered pier wedges, arch walls with archivolts, tapering barrel
  vaults, inner ring with 8 tan columns/blocks/arches, entablature with ressauts, attic with sunk panels and corner
  niches, drum with cushion band and cornice ring, dome cap, coffered star ceiling), site (platform + steps, rostra
  lobes with the planter sweeps from OSM, Greek-key band recess, urn plinths, two stairs), both colonnades (arc from
  OSM, two rows, 2x2 clusters with boxes, pylon pairs with the return section, entablatures, pergola beams), all
  sockets. Previews: `renders/previews/architecture/20260907_072055_*`; comparison
  `renders/qa_comparisons/arch_02_blockout_cam01_fov.png`.

- **Detail pass 1 (milestone 2)**: Corinthian cornice sequence with dentils, egg-and-dart eggs and modillions as LOD0
  geometry; impost mouldings at the arch springings; astragals on every shaft; raised Greek-key frames on the attic
  panels and the box panels; coffered barrel vault soffits (3 x 9, LOD0) built as an all-quad rib grid mapped onto the
  tapering barrel; colonnade fret-band recess and mutules (LOD0); lagoon-edge kerb wall; `instance_seed` custom
  property on every object; LOD0/LOD2 `hide_render` fixed (iterating `Collection.all_objects` while editing objects
  silently truncates - materialize the list first). Previews `20260907_073920_*_detail2` (LOD1) and
  `20260907_073726_*_detail2_lod0` (LOD0); comparisons `arch_04_detail2_*`. Inspection helper `scripts/arch_inspect.py`.

- **Detail pass 2 (milestone 3, current)**: solid ressaut cores and attic-corner caps (no hollow tube interiors seen
  from below/above), pylon entablature cores, dome apex cap. Final previews `20260907_074425_*_detail3` (LOD1),
  golden-hour hero `20260907_074252_01_lagoon_hero_golden.png`, close-ups `inspect_column_lod0.png`,
  `inspect_vault_lod0_v2.png`; comparison set `renders/qa_comparisons/arch_05_detail3_*` (contact sheet
  `arch_05_detail3_sheet.png`; the hero overlay is `arch_05_detail3_cam01_fov_zoom120.png`).

## Build statistics (docs/arch_stats.json)

| | value |
|---|---|
| objects in ARCH | 2069 (incl. 336 socket empties, 300 preview placeholders) |
| triangles, LOD0 configuration (all non-LOD geometry + `_LOD0`) | 2.71 M |
| triangles, LOD1 configuration (viewport default) | 0.87 M (budget 2.5 M) |
| triangles, LOD2 configuration | 0.53 M (the floor is the non-LOD architecture; column shafts alone: LOD0 15 k, LOD1 2.6 k, LOD2 0.2 k each) |
| build time | ~10 s; save 20 MB |
| columns | rotunda 16 (D 2.5/2.1, shaft 16.3) + inner 8 (D 1.7) + colonnade 114 (north 56, south 58; D 1.7, incl. 2 x 4 pylon columns and 4 return columns per wing) |
| colonnade | 4 row boxes + 2 pylon boxes per wing; arc lengths north 99.2 m, south 102.2 m |

Socket counts: capital_rotunda 16, capital_inner 8, capital_colonnade 114, maiden 48, urn 40 (24 podium + 16 attic),
attic_panel 8, attic_figure 8, keystone 24 (8 crown + 16 impost), frieze_run 28, drum_band 1, finial 9, rosette_ceiling 24,
inner_figure 8 (contract addition) = 336.

## Derivations (where the reference sheet is silent or was refined)

| item | value | derivation |
|---|---|---|
| ressaut / attic corner block width | 5.9 m (meets the wall 3.2 m along each face from the vertex) | ref 085: corner block 185 px vs W_a 1404 px = 0.132 W_a = 5.9 m; also gives panel field 17.8 - 6.4 - 0.9 = 10.5 m = the sheet's panel width |
| pier wedge (between the columns) | chamfer 1.9 m wide at circumradius 25.0, sides parallel to the vertex direction | the column pair (axes 4.5 apart, D 2.5) leaves a 2.0 m gap; the columns' fronts reach circumradius 24.99, i.e. flush with the chamfer (063, 070 show the pilaster strip between and flush with the shafts) |
| wall thickness | 2.0 m (apothem 19.5 to 21.5) | OSM: faces at r 22 between piers; DPR "triangular piers"; vault depth then 21.5 - 15.4 = 6.1 m (sheet: 6.0) |
| pier core | triangular block from the outer wall (vertex +-2.65 m) to the inner ring vertex, passage walls tapering from the 12.5 m outer jamb to the 9.85 m inner jamb | DPR "piers triangular in plan"; 082/083 show solid walls between outer and inner arches |
| inner order | abacus 15.5, block 15.5-17.5, inner arch springing 17.5 (= outer springing), crown 22.4 | 083: inner arches spring from the block tops and their crowns sit just under the ceiling ring (24.5); 070: inner capital about 15 m above the floor; the sheet's 13.0 + 2.0 would leave a 4 m blank band under the ring. Column height/outer order = 0.78 |
| inner ring wall | centreline through the column axes (apothem 14.78), 1.2 thick (faces 14.18 / 15.38) | sheet gives only the axis circumradius 16.0 |
| ceiling | spherical cap through the octagon face centres (apothem 14.18) at z 24.5, rise 5.0 -> sphere R 22.6, centre z 6.9 | sheet 3b; the rim dips ~1 m at the octagon corners as in 083 |
| coffer layout | centre disc r 3.0; ring 1: octagons (circ. 1.0) at r 5.0 on the arm directions, squares (1.4) at r 5.2 on the diagonals; ring 2: octagons (1.8) at r 8.6, radial rectangles 3.8 x 1.0 at r 7.2-11.0; ring 3: rounded trapezoids r 11.0-12.9 (half-widths 1.6 / 28 deg arc) on the arms, triangles r 12.0-12.9 on the diagonals; rim band 0.9 | catalog item 16, ref 083 |
| podium lobes | sector r 21 -> 27.3, +-14.5 deg about each pier axis | OSM rotunda outline, lobes ~29 deg wide, r 27-28 |
| planter sweeps | per pier (az, side, reach): (14.5,+,37.0) (59.5,-,33.9) (104.5,+,34.3) (149.5,-,37.5) (194.5,+,37.6) (239.5,-,29.9) (284.5,-,29.7) (329.5,-,37.5); shape = OSM nodes 178-187 scaled radially | OSM node runs 19-23, 40-42, 70-71, 88-90, 163-164, 181-183 |
| podium urns | 3 per pier (24): one in front of the chamfer, one each side beyond the pedestals, on 1.8 m plinths at podium level | 070 and 022 show three urns per pier at the front, not two (sheet says 16) |
| stairs | straight flights 2.0 wide, 28 risers of 0.175, along the outside of the lobes at piers 59.5 and 104.5 | 022 right pier, 063 right; exact run direction uncertain |
| colonnade arc | ONE circle for both wings: centre world (-11.2, 84.7), r 117.4 (rows at 115.15 / 119.65) | least-squares circle through the box bumps of both OSM wing polygons (residuals < 5 m except the last, dubious, OSM bumps) and the pylon-pair midpoints; z18 satellite confirms a single arc around the west of the rotunda "struck from the eastern side of the lagoon" (DPR) |
| wing extents | south: from world (32,-25.6) to the first pylon (100,47), arc 102 m; north: (-22,-34.5) to (-108.5,13), 99 m | OSM roof306/roof310 end caps and the appendix/roof313-314 pylon footprints |
| box rhythm | first cluster 3 m from the rotunda end, then every 21.0 m (cluster pair 3.0 + 4 bays of 4.5) -> 4 row boxes per wing | OSM bumps at s = 5, 25, 46, 70 (+-3); satellite blobs 20-22 m apart; hero photo boxes at s = 29 and 50 |
| pylons | pair per wing end: pylon A on the arc, pylon B 17 m west (toward the hall), joined by a straight return with 2 intermediate columns per row (rows 3 m apart) | OSM: roof313 vs the roof310 appendix, roof314 vs the roof306 appendix are 17 m apart along E-W; ref 167 shows the two pylons flanking a lower 2-column section |
| box count | 4 row boxes x 2 wings + 2 pylons x 2 wings = 12 boxes, 48 maidens (published: 13 / 52) | OSM; the 13th box is not resolvable in the trace |
| colonnade heights | ground -0.6; base 1.0, shaft 11.2, capital 1.8 (abacus +14.0), entablature 2.4 (+16.4); pylon shafts +2.4; boxes 5.3 x 5.3 x 3.0 | sheet 2b |

## Sockets (see docs/sockets.md)

Counts are in `docs/arch_stats.json` (`sockets`). Additions/interpretations beyond the contract:
- `inner_figure` (8): the winged "Priestess of Culture" figures on the inner blocks; NOT in the contract. +Y = the
  direction the figure faces (toward the rotunda centre). size_hint 4.6.
- `keystone` (24): 8 crown lion masks (size_hint 0.8) + 16 impost masks (size_hint 0.5, custom prop `subtype='impost_mask'`).
- `urn` (40): 24 podium urns (size_hint 3.0) + 16 attic-corner urns (1.6).
- `finial` (9): 8 volute scrolls on the attic corner blocks (`subtype='volute_scroll'`, 1.5) + the dome apex (0.6).
- `frieze_run` (126 after Phase 3): 24 on the ressaut faces (`run_length`, `run_dir`) + 4 colonnade row runs
  (`subtype='greek_fret'`, `arc_center`, `arc_radius`, `run_length`) + **98 new `subtype='greek_key'` runs** (50 on the
  rostra/podium bands, 8 lobes; 48 on the planter-box base bands, 4 per box on 12 boxes) — QA-01-11. Every greek_key
  socket carries `run_length` (1.4-6.2 m on the rostra, 5.18 m on the boxes), `run_dir` (== the socket's local +X,
  asserted in the build), `band_height` (0.5 rostra / 0.42 box), `host` (`rostra` / `planter_box`) and
  `modelled_by_arch=True`.
- `rosette_ceiling` (24): 8 rim (face centres), 8 rim (corners), 8 ring-1 squares.
- Bases are modelled by ARCH (no `base_*` sockets). Dentils are geometry (LOD0 object); egg-and-dart is a plain ovolo
  in the sweep profile (ORN may overlay a strip using the `frieze_run` sockets' geometry).

## Requests for the lead / other agents

1. Hero camera (lead): move to ~138 m on the face normal, e.g. `loc=(-19.3, 137.0, 1.0)`, or lens 37 mm, to match the
   user image's framing with the sheet's dimensions (see the Known gaps entry below; evidence
   `renders/qa_comparisons/arch_02_blockout_cam01_fov.png` vs `_zoom120`).
2. QA cam 04 (lead): `rotation_euler=(pi,0,0)` to look up; the current `(0,0,pi)` looks at the floor.
3. Socket contract (lead/ORN): add type `inner_figure` (8, on the inner blocks, +Y toward the rotunda centre,
   size_hint 4.6); `keystone` sockets carry `subtype='impost_mask'` for the 16 small masks; `finial` carries
   `subtype` (`volute_scroll` x8 on the attic corners, `dome_apex` x1); `frieze_run` carries `run_length`, `run_dir`
   and, on the colonnade, `arc_center`/`arc_radius`/`subtype='greek_fret'`.
4. ORN: podium urns are 24 (3 per pier, 070/022), size_hint 3.0; attic corner urns 16 at 1.6.
5. build_master (lead): exclude `ARCH_placeholders` once ORN assets exist; keep `hide_render` in sync with
   `set_lod_visibility` (LOD0 objects are `hide_render=True` in the file).
6. Materials: every object has `part_type` and `instance_seed` (0-996) custom properties; column shafts are linked
   duplicates (one mesh per type and LOD), so per-instance variation must key on the object, not the mesh.
7. ENV: the colonnade stands on `COLONNADE_GROUND_Z = -0.6`; the rotunda platform steps reach -0.6 at r 26.7; the lagoon
   kerb (`ARCH_site_lagoon_kerb_0`) follows the OSM lagoon polygon within 52 m of the centre, top at -0.7 (0.6 above water).

## Phase 3 fix round (2026-09-07)

### QA-01-1 — dome + drum (blocker): derivation

The lead arbitrated that the photographs override the reference sheet's 49.4 m apex (decisions.md, "Phase 3 start").
Everything below the attic cornice is untouched; only `DRUM_*` and `DOME_*` in `scripts/arch_params.py` moved.

**Measuring tool.** `qa_silhouette.py`'s building mask is `r > b + 0.06`. On the ARCH preview the sky-lit crown of the
dome renders at sRGB (122,117,110), i.e. r-b = 12/255 = 0.047, so the tool walked past the top ~3 m of the dome and
reported an apex three metres too low; the same bug flatters or punishes any dome depending on its material. Added
`arch_inspect.py --alpha` (transparent film + flat white) and `scripts/arch_silhouette.py flatten`, which turn the
alpha channel into a warm-on-blue mask. The photographs need no such treatment (their sunlit stone is strongly warm),
so the comparison stays apples-to-apples, and `ref169`/`ref085` re-measure to exactly QA's round-01 numbers
(rise/W_a 0.252 and 0.195) with QA's crops, which confirms the pipeline.

**Solving the rise.** Camera = the current `CAM_qa_01_lagoon_hero` (loc (-14.1, 100.0, 1.6), 24 mm, shift_y 0.09),
1920x1080, ARCH-only, LOD1. Crops: render (620, 20, 1305, 420); ref 169 1920x1192 (680, 100, 1220, 360);
ref 085 1920x1280 (384, 0, 1536, 576) — the same crops QA used, recovered from the yellow rectangles in
`round01_profile_ref*.png`. W_a = 673 px, corner-urn row 182. `align` scales each photo by W_a and matches the
corner-urn row, so the only free variable is the visible dome rise:

| dome rise | apex_y | rise px | rise / W_a | delta vs ref 169 | delta vs ref 085 |
|---|---|---|---|---|---|
| 7.9 (start of the round) | 45 | 137 | 0.204 | +3.0 % | -0.6 % |
| 9.4 **(chosen)** | 32 | 150 | 0.223 | **+1.8 %** | **-1.7 %** |
| 10.3 | 21 | 161 | 0.239 | +0.8 % | -2.8 % |

The two photographs disagree with each other by 4.5 % of frame height (ref 085 is a distant telephoto and foreshortens
the rise; ref 169 is a stitched wide panorama), so the band that satisfies **both** within 2 % is only
rise/W_a = 0.219-0.228, i.e. dome rise 9.2-9.6 m. Chosen 9.4 (centre of the band): 12.2 px per metre at the dome axis,
so ±0.2 m is ±2.4 px = ±0.22 % of frame height.

**Final values.** `DRUM_H` 5.1 (plain 2.7 + guilloche cushion 1.5 + cornice ring 0.9), `DRUM_Z1` 43.4,
`DOME_BASE_R` 16.5, `DOME_RISE` 9.4, `DOME_SPHERE_R` 19.18, `DOME_APEX_Z` 52.8 (apex cap top 53.4). Total height above
the rotunda floor 53.4 m = 175 ft against the DPR's 162 ft; the photographs win, per the lead's ruling.

**Drum visibility.** Measured by differencing three alpha passes at the centre columns (x 880-1040) with
`arch_inspect.py --hide`: attic cornice behind the drum at y 117, top of the drum cornice ring at y 66, apex at y 32.
The plain band + cushion + cornice therefore stand **51 px** above the attic cornice at 1080p (QA asked for >= 12 px),
and the dome springs a further 34 px above that ring.

Evidence: `renders/qa_comparisons/arch_06_phase3_sheet.png` (panels 1-4),
`arch_06_align_vs_ref169.png`, `arch_06_align_vs_ref085.png`.

### Maiden sockets moved to the box BASE

`BOX_H` 3.0 -> 3.55 (the rim sits 3.55 m above the figures' feet, decisions.md). All 48 `SOCKET_maiden_*` now sit at
the box base plane (z 15.80 on the arc boxes, 18.20 on the pylon boxes) instead of the box rim, 0.32 m outward from
the box's vertical corner edge along the corner diagonal (`MAIDEN_OUT`), +Y still = the direction the figure's back
faces. Each socket carries `rim_height` (3.55) and `box_corner_y` (-0.32) so ORN can seat the arms on the rim.
`size_hint` 4.4.

### QA-01-11 — Greek-key band (ARCH half)

ARCH models the meander as geometry **and** publishes sockets, so the band exists in the master render whether or not
the lead wires ORN to it: `build_meander_band` lays alternating 1.0 m key units (7.5 cm line, 3.5 cm proud) and square
rosette bosses (0.45 m disc with 8 petals) along the recessed band face of every rostra wall and every planter-box base
band — 20 meander meshes. The 98 `frieze_run` / `greek_key` sockets described above let ORN replace that geometry with
`ORN_greek_key` / `ORN_rosette_band`; whoever does that must hide the `ARCH_*_meander_*` objects first (noted in
docs/sockets.md).

### Materials-agent requests (docs/materials_notes.md "Open issues")

- **Fluted at LOD0/LOD1** — verified, not changed: rotunda shaft flute depth 0.120 m (LOD0) / 0.106 m (LOD1) / 0.0
  (LOD2); colonnade 0.088 / 0.072 / 0.0. 24 flutes with fillets as built in Phase 2.
- **Column origins at the shaft base** — verified: every `*_column_*` object has its origin on the shaft axis at the
  shaft base (rotunda z 8.5 = pedestal top).
- **Dome origin on the dome axis** — verified: `ARCH_rotunda_dome` origin (0, 0, 43.4), `_drum` (0, 0, 38.3),
  `_drum_cornice` (0, 0, 42.44).
- **Bevels** — a sweep at the end of `arch_build.py` adds a 3 cm / 2-segment angle-limited bevel to any ARCH mesh in
  `BEVEL_ALSO` that has none: 249 objects (attic corner caps, frames and roof, attic volutes, drum cornice, dome apex
  cap, all column bases, ressaut cores, imposts, archivolts, rostra band/cap/rustication courses, pylon cores, planter
  box band/lid/frames, stairs and cheek walls). Deliberately still sharp: flute geometry, dentil / egg-and-dart /
  modillion arrays, meander units, coffer plates, sunk panels and the dome shell — a 3 cm bevel on a 15 cm dentil eats
  the moulding and multiplies the tri count.
- **Podium rustication as geometry** — `build_rustication`: the podium core is set back 3.5 cm and 0.6 m ashlar courses
  stand out to the true face with a 4 cm joint between them (64 course objects over the 8 lobes), so the joints throw a
  real shadow line instead of relying on a texture. Sheet s4 #12 / s5 ("plain rusticated courses, joints ~0.6 m").

### QA-01-14 — planter box count: DECISION, 12 boxes / 48 maidens (not 13 / 52)

Evidence checked: the OSM wing polygons (`common.load_site_local`, traces `w319/w321/w323` and
`reference/plans/site_northwing_zoom.png`) carry only the two colonnade wall lines — there is no per-cluster geometry,
so OSM cannot place boxes at all; ref 187 shows three boxes on one visible stretch of arc and ref 167 the two boxes of
a pylon pair, neither of which resolves a total; the aerial 105 is far too distant. The reference sheet itself flags
the count "uncertain" and derives 13 arithmetically from secondary sources (52 maidens / 4, 26 garland panels / 2).
**Decision: keep the symmetric 12** — 6 per wing (4 clusters along the arc + the 2 boxes of the end pylon pair). The
building is symmetric about the east-west axis, so an odd 13 cannot be realised without breaking that symmetry, and
the alternative reading of the sheet (5 along the arc per wing + pylons) gives 14, not 13. If the lead wants 52
figures, the cheapest change is 5 clusters per wing (`COL_CLUSTER_PAIR` / `COL_FIRST_CLUSTER_S` in arch_params.py) for
14 boxes / 56 maidens; that would re-cut the colonnade rhythm QA scored as good, so it is not done unilaterally.
Garland relief panels remain plain sunk panels with Greek-key frames (relief is ORN's `attic_panel`-class work).

### QA-01-15 / QA-01-16

- Vault coffers rebuilt as two rows of large octagons (r 0.95 max) with small square lozenges between and between the
  rows, mapped onto the barrel-vault soffit, per ref 062 — replacing the 3x9 rectangular grid. Panel 6 of the sheet.
- Lagoon-side stairs: each flight gets two 0.35 m cheek walls flush with the treads, parapet 0.9 m above the tread
  line and sloping with the flight down to the lawn (refs 063/031). The flight itself keeps its Phase 2 position,
  running tangentially along the podium lobe (refs 063/031 show it beside the podium, not centred on the axis);
  `plate` puts its front face on the origin plane, so the cheek origins are p_top + sgn*radial*(width/2 + 0.35) and
  p_top - sgn*radial*(width/2) - the first version left a 0.18 m gap on one side and straddled the tread edge on the
  other.

## Known gaps / open issues

- Vault coffers: octagon + square lozenge pattern since Phase 3 (QA-01-15). Ref 088 shows the fan converging toward
  the crown; ours keeps a constant pitch along the arc.
- Stairs: two straight flights placed tangentially along the lobes at piers 59.5 and 104.5; run direction not verified.
- Dome seam lines and column pour lines: material work (documented in the sheet), not geometry. Podium rustication IS
  geometry since Phase 3.
- 12 boxes / 48 maidens, by decision (QA-01-14 above), not by omission.
- The return sections between the pylon pairs are an interpretation of ref 167 (two rows 3 m apart, 2 intermediate
  columns each); the OSM trace stops 20-27 m short of the pylons.
- Colonnade bay layout is regenerated from parameters in `arch_params.py` (COL_BAY, COL_MODULE, COL_CLUSTER_PAIR,
  COL_FIRST_CLUSTER_S), not from a geometry-nodes array.

- Placeholders: `ARCH_placeholders` holds crude capitals, urns, figures, keystones so previews have a silhouette; the lead
  should EXCLUDE that collection when linking if ORN assets are present.
- Hero camera: with the sheet's dimensions the attic corner blocks span 509 px of the 1280 px hero frame; the user photo
  spans ~436 of 1320 (33 %). The model matches OSM/satellite/085, so the camera is ~20 % too close for that photo
  (or the photo's lens is ~37 mm). Comparisons use `arch_compare.py --ref-zoom 1.2` to check proportions.
- QA cam 04 (`CAM_qa_04_rotunda_ceiling`) has rotation (0,0,pi) which looks DOWN; (pi,0,0) looks up with the top of the
  frame toward -Y. Previews add `CAM_arch_ceiling_up` for the ceiling view.
- `common.set_lod_visibility` toggles only `hide_viewport`; the saved file also has `hide_render=True` on LOD0/LOD2.

## Phase 4 polish round 1 (2026-09-07)

### QA-02-1 (blocker) — "the dome reads absent from cam05": measured, and it is the camera, not the dome

**The QA metric could not be reproduced, so a new one was built.** `qa_silhouette.measure` is a face-on tool: its
`corner_top` is the median of the outer 12 % of the crop and its `apex` the min over the central 30 %. From an
oblique, low station those land on the *receding* attic edge and on the *near attic corner block* respectively, so
on `round02_05_south_lawn.png` it reports `rise_over_wa = 0.179` where the eye sees a sliver of drum. New tool:
`scripts/arch_domecheck.py` — pure numpy, no Blender. It projects the parameterised solids themselves
(attic top ring = `entablature_plan()` offset out by the 0.74 m cornice projection at `ATTIC_Z1`; drum wall, drum
cornice and dome as surfaces of revolution from `arch_params`) through a pinhole matching Blender
(`f = res_x * lens / 36`, `cy = res_y/2 + shift_y * res_x`; the `+` sign was verified against the round-02 hero,
predicted apex row 76 vs QA's mask apex 88) and reports per image column `attic_top_y - dome_top_y`:

| metric | meaning |
|---|---|
| `W_rot` | on-screen width of the attic top ring = the on-screen rotunda width |
| `rise_over_W` | max visible dome+drum rise above the attic cornice / `W_rot` (QA-02-1 acceptance: >= 0.09) |
| `cover` | fraction of `W_rot` where the dome/drum is above the attic cornice (acceptance: >= 0.60) |
| `clear_over_W` | dome apex above the *highest* attic point (the near corner block) — "does a cap read at all" |

**Current geometry at `CAM_qa_05` (45, 55, 1.4), target (0,0,20), lens 20:** `W_rot` 498 px,
`rise_over_W` **0.046**, `cover` 0.34, `clear_over_W` **-0.005** (the dome apex is *below* the near attic corner
block). That is the defect QA saw, and QA's "3.7 %" is the same reading.

**Same numbers measured off ref 063** (grid read of `reference/photos/canonical/cam_05_south_lawn.jpg`, rotunda
x 480-1640 so W = 1160 px): dome apex row 57-58, flanking-face attic cornice row ~195, near corner-block cornice
row ~103 -> `rise_over_W` **0.118**, `clear_over_W` **+0.037**, dome above the cornice over ~55-65 % of W.

**Cause.** Sweeping the station with the geometry frozen (`arch_domecheck`, az held at a vertex azimuth,
lens scaled to keep the rotunda the same on-screen size):

| station | 71 m | 85 m | 95 m | 105 m | 115 m | 125 m |
|---|---|---|---|---|---|---|
| `rise_over_W` | 0.039 | 0.068 | 0.090 | 0.108 | 0.123 | 0.135 |

Azimuth barely matters (face-on 0.046 vs corner-on 0.039 at 71 m); **distance is the whole effect**, because the
attic cornice is 49 m from a 71 m camera and the dome is 71 m away, so the near parapet eats it. A five-parameter
least-median fit of the silhouette to the photograph (`arch_domecheck.py --fit`) puts ref 063 at
**az 104.1 deg, 115.3 m, eye height ~0.5 m, ~40 mm** (world (28.1, 111.8); residual 23.7 px median on a 1920 px
image) — i.e. the photo is a *long-lens shot from more than 1.6x the distance*, not the 71 mm/20 mm station
`CAM_qa_05` uses. At that fitted station **the unmodified model gives `rise_over_W` = 0.120 and `cover` = 0.69
against the photograph's 0.118** — a 2 % relative match. Overlay:
`renders/qa_comparisons/arch_qa02_1_ref063_fit_overlay.png` (model silhouette in red on ref 063).

**Conclusion: the dome/drum/attic proportion is right; `CAM_qa_05`'s station does not match its canonical photo,
exactly as QA-02-17 found for `CAM_qa_02`.** No geometry change is made for QA-02-1.

**What a geometry fix would have cost** (swept at the current cam05 station, apex held at 52.8 so the cam01
arbitration survives):

| change | cam05 `rise_over_W` | cover | cam01 apex row shift |
|---|---|---|---|
| baseline | 0.046 | 0.34 | 0 |
| `ATTIC_H` 7.1 -> 6.1 | 0.063 | 0.35 | +0.07 %H |
| `DRUM_PLAIN_H` 2.7 -> 4.7 (dome rise 9.4 -> 7.4) | 0.085 | 0.49 | -0.42 %H |
| `DOME_BASE_R` 16.5 -> 19.5 | 0.075 | 0.44 | -0.83 %H |
| `ATTIC_H` 6.3 + `DRUM_PLAIN_H` 5.2 + `DOME_BASE_R` 18.5 | 0.101 | 0.60 | -1.29 %H |

Only the last row clears the 0.09 / 0.60 acceptance, and it needs an 11 % attic cut, a 50 % taller drum and a 12 %
wider dome all at once — three measured/arbitrated values broken, and it would *break* the ref-063 match above
(the model already reads slightly tall against the photo at the fitted station). Not done; handed to the lead.

**Recommended `CAM_qa_05`** (lead's file, not mine): `loc = (28.1, 111.8, 1.5)`, `target = (0, 0, 20)`, `lens 40`.
`arch_domecheck.py` then predicts `rise_over_W` 0.120, `cover` 0.69 against ref 063's 0.118.

### QA-01-15 / QA-02-9 — barrel-vault coffers had 12 cm ribs, under the 15 cm acceptance

`build_vault_coffers` laid the rib network as an `L.plate` whose *thickness is the coffer depth* (the plate's back
face is remapped to a smaller barrel radius, so the ribs stand proud of the soffit into the bay). It was hard-coded
`0.12`, i.e. **12 cm** — under QA-02-9's "coffer depth >= 15 cm casting visible shadow at cam04". Now
`P.VAULT_COFFER_DEPTH = 0.20`. The rotunda *saucer-ceiling* coffers were already right at
`P.COFFER_DEPTH = 0.30` (the rib plate hangs 0.30 m below the field, which sits 2 cm above the sphere).
Verified: `ARCH_rotunda_vault_coffers_00_LOD0`, 384 verts, z 17.50-23.64, `hide_render=False`.
Bottom panel of `renders/qa_comparisons/arch_p4r1_sheet.png` — two rows of octagonal coffers with the diamonds
between them, reading with shadow at 24 mm from under the bay.

At `CAM_qa_04` itself the vault soffits are seen almost edge-on at the frame edge and stay murky; that is
QA-02-12 (soffit / sky 0.20 vs ref 083's 0.58), not depth. The geometry now clears the acceptance by 5 cm.

### Performance — ARCH is 6-8 % of the master, and the bevels are not the regression

`scripts/arch_perf.py` (new) reports base vs *evaluated* triangles; `arch_stats.json`'s `tris_LOD*` are base
polygon counts and never saw the modifiers. Measured on `master.blend` (155 MB, 4022 visible objects):

| | viewport (LOD1) | render (LOD0) |
|---|---|---|
| ENV | 8,391,436 | 17,889,492 |
| ORN socket instances (`INST_*`) | 5,209,485 | **26,648,271** |
| ARCH | 1,250,670 (8.1 %) | 3,095,134 (6.1 %) |
| ORN library assets | 509,822 | 2,684,571 |
| **total** | **15,437,021** | **50,393,076** |

ARCH's 831 bevel modifiers (249 from the `BEVEL_ALSO` sweep + 582 from `_finish(bevel=True)`) add **261,056**
triangles — 1.7 % of the viewport count and **0.5 % of the render count**. Timed directly (Eevee 1280x720,
16 TAA, on `architecture.blend`, warm-up render first, alternated ON/OFF twice):

| | bevels OFF | bevels ON | cost |
|---|---|---|---|
| cam01 | 6.4 / 5.6 s | 7.0 / 6.6 s | **+0.8 s** |
| cam05 | 7.1 / 7.1 s | 9.0 / 8.9 s | **+1.9 s** |

So the whole ARCH bevel set is worth ~1-2 s of the master's 33-55 s per camera, and deleting it would re-open
QA-02-3 (edge wear is a blocker). **Kept in the render, removed from the viewport**: the 685 bevelled objects
carry no LOD suffix, so there is no `_LOD1` copy to strip — the equivalent is `show_viewport=False` /
`show_render=True`, now set in `arch_lib.add_bevel` so a rebuild reproduces it.

**ARCH viewport (LOD1 + un-LODed): 1,250,670 -> 1,002,478 evaluated triangles (-19.8 %).** Render set unchanged
at 3,095,134 (the bevels are still there for Cycles; `arch_perf.py` counts on the viewport depsgraph, so after the
change it reports the render row as 2,846,942 — that is the tool's viewport read, not a render regression).

**For the lead: the regression is not ARCH.** The master renders `INST_*` and `ENV` at **LOD0**, so the Eevee
previews push 50.4 M triangles, of which ornament instances alone are 26.6 M over 412 objects (65 k each) and
environment 17.9 M. Rendering previews with `common.set_lod(viewport=1, render=1)` would take the render set from
50.4 M to ~15.4 M. ARCH's own heavy geometry is the fluted shafts (2.17 M of ARCH's 2.83 M LOD0 across 342
colonnade columns) and they already have LOD1/LOD2, so the viewport never pays for them.

### Socket contract

**Nothing moved.** `docs/sockets.md` is byte-identical before and after the rebuild, and every `arch_stats.json`
socket count and triangle total is unchanged (only `build_seconds` 3.3 -> 4.4). The coffer change alters vertex
positions inside one object per bay; the bevel change touches modifier visibility only.

---

## Polish round 2 (QA-03-4, QA-03-8, QA-03-9)

Three defects, all geometry: no flutes on the shafts, a bell-shaped column base with no torus/scotia, and vault
and saucer coffers that read as flat inset outlines. Before/after/reference contact sheet:
`renders/qa_comparisons/arch_p4r2_sheet.png` (before = the previous commit's geometry rendered from the same
cameras with the same preview rig, so only the geometry differs).

### QA-03-4 / QA-03-9 — the flutes were there; the hollow was the wrong shape

24 flutes with 0.25 fillets have been on every shaft since Phase 2 (`scripts/arch_lib.py column_shaft`), so
"no flutes" was not a missing feature. The cross-section was a **half-sine sampled at even u**: for a 24-flute
2.46 m shaft that made the flute wall at the arris only **56 deg** off the tangent, so both walls of every hollow
caught nearly full sun and the shaft read as a soft gradient. The photographs (054, 128, 169) show the opposite:
wide bright fillets separated by *narrow hard dark lines*.

`L.flute_section()` now lays a **segmental circular arc sampled at EQUAL ARC ANGLES**, which crowds samples
towards the arris. `P.FLUTE_ARC_HALF_DEG = 90` makes it the semicircular hollow of a Roman Corinthian order
(depth / flute width = 0.500, i.e. 0.129 m on the 2.46 m rotunda shafts, 0.088 m on the 1.7 m colonnade shafts).
`k_arc` (samples per hollow) 2 -> 4 at LOD1 and 6 -> 8 at LOD0; the arris wall is now **72 deg** at LOD1 and
**81 deg** at LOD0.

`L.shaft_rings()` replaces the uniform ring ladder with a graded one: rings where the flutes run out (the
apophyge and the 0.35 m fade at each end) and only 6 (LOD1) / 18 (LOD0) across the plain middle, where nothing
but the entasis varies. **LOD1 rings 15 -> 10, LOD0 41 -> 30.** That pays for the extra angular samples:

| | verts/ring | rings | tris/shaft before | tris/shaft after |
|---|---|---|---|---|
| LOD0 | 192 -> 240 | 41 -> 30 | 15,360 | 14,396 (**-6.3 %**) |
| LOD1 | 96 -> 144 | 15 -> 10 | 2,876 | 2,876 (**0 %**) |
| LOD2 | 32 | 7 | 444 | 444 |

So the LOD1 flutes are real geometry at no triangle cost at all; no normal-map shortcut was needed.

**What it buys, measured.** Horizontal luminance profile across a front shaft of the rotunda (crop x 797-824,
y 337-446; detrended, modulation contrast = peak-to-peak / mean):

| | cycles | modulation contrast |
|---|---|---|
| before, 1920x1080 | 6.0 | 38.0 % |
| after, 1920x1080 | 6.0 | 36.8 % |
| **after, 3840x2160** | 7.0 | **51.5 %** (side shaft 61.3 %) |
| ref 169, same crop | 6.5-7.0 | 67.6-79.0 % |

**At 1920 the geometry cannot move this number and neither could any other geometry**: the shaft is 27 px wide,
so 24 flutes are 2.2 px each and the renderer averages each hollow away. The change reads immediately at
CAM_qa_03 (sheet row 2) and gains 14 points at the 4K delivery resolution. The remaining gap to ref 169 at hero
scale is albedo, not shape, and the reference sheet says so itself under MAT_column_rose: *"flute ridges are
paler, flute hollows hold dust"*. **Hand-off to materials: QA-03-4 needs a flute-phase-locked albedo/dirt
modulation on MAT_column_rose (24 cycles round the shaft, in phase with the geometry), not more geometry.**

### QA-03-9 — the Attic base was a smooth flare with a broken top

`attic_base_profile` was one continuous curve: a 0.18 m torus bulge, a **0.06 m** scotia (5 % of the shaft
radius, invisible), and an upper torus whose centre sat at `sc_top + 0.11 h` so its top reached **1.06 h** —
above the base height, so the lathe folded back on itself at the shaft springing. It read as a bell.

Rebuilt from `P.BASE_COURSES`, the classical division of the height above the plinth
(plinth 0.20 h, then lower torus 0.34 / fillet 0.04 / scotia 0.22 / fillet 0.04 / upper torus 0.28 /
apophyge 0.08 of the remaining 0.80 h), with sharp fillets between the courses and both tori capped inside the
square plinth (sheet: plinth = 1.15 x shaft D). Measured off the rebuilt mesh, rotunda column (r 1.25, h 1.0):

| course | z | max radius | projection past the shaft |
|---|---|---|---|
| plinth top | 0.200 | 1.4375 (square) | — |
| lower torus | 0.206 - 0.478 | **1.388** | **+0.138** |
| fillet | 0.486 - 0.519 | 1.269 | +0.019 |
| scotia throat | 0.610 | **1.219** | **-0.031** |
| fillet | 0.700 - 0.733 | 1.261 | +0.011 |
| upper torus | 0.733 - 0.957 | **1.360** | **+0.110** |
| apophyge | 0.957 - 1.000 | 1.250 | 0 |

Colonnade bases (r 0.85, plinth 1.955) come out at +0.077 / -0.021 / +0.062 m; the lower torus is capped by the
plinth there, which is why it is less bold than ref 113 looks. Base torus mesh 2,782 tris (4 unique meshes,
everything else instanced); the base is not LODed, so the cost lands once in every LOD total.

### QA-03-8 (architecture half) — coffer depth measured off ref 083

**Depth-to-width ratio, derived.** On ref 083 a ring-3 trapezoid panel near the left edge of the frame (scan
y 645-665) shows an 18 px splayed reveal on a ~220 px / ~4.5 m panel = 8.2 % of the panel width, at an off-axis
angle of atan(9.5 / 25) = 20.8 deg. That implies a depth of 0.082 x 4.5 / tan(20.8) = **0.95 m**, i.e.
**depth / width = 0.21** (the Pantheon's coffers are 0.23). Applied as 0.20 x the coffer width:

| | width | depth before | depth now |
|---|---|---|---|
| saucer coffers (`ARCH_rotunda_ceiling_ribs`) | 1.4-4.5, mean ~2.75 m | 0.30 | **0.55** |
| barrel-vault coffers (`ARCH_rotunda_vault_coffers_*`) | 1.9 m octagons | 0.20 | **0.38** |

**Stepped reveals.** `L.plate()` takes `registers`, a list of (widen, depth) read from the room face inwards, so
every coffer gets a moulded multi-register reveal instead of one straight wall. Ceiling:
`((-0.05, 0.05), (0.10, 0.13))` — a bolection lip projecting 0.05 m into the opening at the room face, then a
splay 0.10 m wider than the box over 0.13 m, then 0.37 m of straight box to the panel. Vault:
`((-0.04, 0.04), (0.07, 0.10))`. The lip's underside reads bright and the splay floor dark, so each coffer has a
light/shadow line pair even seen almost face-on from CAM_qa_04 — the reason a single straight reveal showed
nothing there. Verified in `renders/previews/architecture/p4r2_vault_check.png` (24 mm from under a bay, LOD0):
the two rows of vault octagons and the diamonds between them are deep dark boxes with visible reveals.

**What it does NOT fix.** Coffer-field luminance std-dev over the central 0.40-0.60 box of the ceiling-up frame
went 11.43 % -> 12.03 % of the mean, against ref 083's 46.65 % — still **26 % of the reference**. Scanning ref
083 shows why: its coffer *panels* are bright (L 93-130) and its *ribs* are dark (L 22-50), a 2.5-3x ratio, and
that darkness is a century of grime on ornate acanthus frames, not shape. Architecture's own contribution is
now depth 0.20 x width with a three-register reveal; the rest is **materials** (recess dirt on the rib faces,
the sheet's own MAT_plaster_ceiling note "coffers darker, ribs lighter" is the wrong way round for these ribs)
and **ornament** (the acanthus rib frames and rosettes). Flagged to the lead rather than forced with geometry.

### Hand-offs

- **Ornament:** the 16 `SOCKET_rosette_ceiling` sockets on the rim band (radius > 6 m) sit on the rib room face,
  which moved down 0.25 m with the coffer depth (`sz(x, y) - COFFER_DEPTH`, 0.30 -> 0.55). The 8 ring-1 sockets
  on the panel face did not move. `docs/sockets.md` is unchanged (counts and types are identical); re-link
  `assets/architecture.blend` to pick up the new z. Vault-coffer interiors are also 0.18 m deeper.
- **Materials:** flute-phase albedo on MAT_column_rose (above); rib-face grime on MAT_plaster_ceiling.
- **Lead:** ARCH LOD1 989,614 -> 1,045,294 base tris (+55,680, +5.6 % of ARCH, ~+0.5 % of the 11.62 M master).
  All of it is the coffers and the bases; the fluted shafts cost nothing. LOD0 2,834,078 -> 2,716,318 (-4.2 %).
- Nothing above the capitals and nothing in the rotunda's proportions was touched.

### Open

- The colonnade lower torus is capped by the sheet's `plinth = 1.15 x shaft D`; ref 113 reads slightly bolder.
  If the sheet's plinth number is revised the cap in `attic_base_profile` will let the torus grow with it.
- Coffer depth is one value per plate. Ring-3 trapezoids (4.5 m wide) would want ~0.9 m by the measured ratio and
  get 0.55; giving each ring its own depth needs the rib network split into three plates or per-coffer lids.
- `scripts/arch_build.py` gained `--cams a,b` and `--res WxH` for the preview rig.

### Polish round 2 — code-review fixes (docs/reviews/arch_p4r2_review.md, items 1-4)

1. **Vault coffer registers overlapped their neighbours (HIGH).** Confirmed the review's numbers by replaying the
   layout: the in-row diamond left only **75 mm** of rib to its octagons and the mid-row diamond only **29 mm**,
   against a 70 mm splay. Fixed by opening the gaps rather than shrinking the reveal to invisibility: the in-row
   diamond factor is 0.8 -> **0.55** (gap 75 -> **180 mm**) and the mid-row diamond, 0.26 m across and unreadable
   at cam04, is gated off (`dr > 0.2`). `VAULT_COFFER_REGISTERS` is now `((-0.030, 0.04), (0.055, 0.10))`, leaving
   **70 mm** of rib. Belt and braces: `L.polygon_clearance()` measures the tightest boundary-to-boundary distance
   in a plate's hole set and `L.plate` **clamps the registers** to keep `REVEAL_CLEARANCE` (20 mm) of solid rib,
   printing when it does — so this class of bug can no longer be silent. It fires once, harmlessly, on the ceiling
   (widen 0.100 -> 0.097). Both plates are now **0 non-manifold edges** (vault 2,250 edges, ceiling 4,696).
2. **`rosette_ceiling` socket planes (MEDIUM).** The 24 sockets are two different things and now say so:
   * **16 rim-band sockets** (rr 13.73 / 14.85) are not in a coffer at all — that band is solid rib between the
     outermost coffers and the octagon edge, and the sheet calls them a "base ring with rosette band above the
     inner arches" (083). They are bosses on the rib's **room face**, so their plane follows it:
     `sz(x, y) - COFFER_DEPTH + ROSETTE_RIM_INSET` = **`sz - 0.53`** (0.02 m set back into the plaster).
     They were at `sz - 0.30`, so the correction for ornament is **down 0.23 m, not 0.25 m.** World z 23.41 / 24.32.
   * **8 ring-1 square-coffer sockets** (rr 5.2) are inside a box, so they sit on the box **floor** — the field
     saucer, `sz + CEILING_FIELD_LIFT` = **`sz + 0.02`**, not on the bare sphere as before: **up 0.02 m.**
     World z 28.91. `CEILING_FIELD_LIFT` now drives both the field loft and this socket, so they cannot drift.
   Counts and types are unchanged, `docs/sockets.md` untouched.
3. **LOD1 flute run-out ladder (LOW).** `height - fade - 0.05` inserted into the top ladder, so the 0.35 m run-out
   is resolved instead of smeared over 1.63 m. LOD1 rings 10 -> 11, +288 tris per shaft.
4. **`--cams` / `--res` index guard (LOW).** Both check `index + 1 < len(ARGS)`.
5. INFO (apophyge flares 4 mm outward, effectively a no-op) left as is: harmless, and the base profile is the one
   part the review verified clean.

**Found while verifying, and fixed:** the barrel-vault coffers were built as `ARCH_rotunda_vault_coffers_NN_LOD0`,
**LOD0 only**, so `common.set_lod(render=1)` — what every QA pass and every preview uses — hid them and the barrel
soffits rendered bare. **That is the real root of QA-03-8's "no coffer casts a shadow" on the vaults: at LOD1 there
were no vault coffers to cast one.** They now carry no LOD suffix and render at every level, like the ceiling ribs
(2,036 tris x 8 bays = 16,288). Verified at LOD1 in `renders/previews/architecture/p4r2fix_vault_check.png`
(24 mm from under a bay): two rows of deep octagons with the diamonds between them, clean reveals, no overlaps.

**Triangles after the fixes:** LOD0 2,834,078 -> **2,713,406** (-4.3 %); LOD1 989,614 -> **1,101,326**
(+111,712, +11.3 % of ARCH, ~+1 % of the 11.62 M master -> ~11.73 M, still under the 13 M cap); LOD2 725,966.
Of the LOD1 increase, 55,680 is the coffers and bases, 39,744 the flute run-out ring, 16,288 the vault coffers
that were previously invisible at this LOD.

### rosette_ceiling socket facings (ornament, 2026-09-08)

All 24 `SOCKET_rosette_ceiling_*` had `dot(+Y, radial) = +1.000`, i.e. every rosette faced radially OUTWARD into
the masonry and none was visible from cam04. `L.add_socket` only ever built a yaw, so a socket's facing could not
leave the horizontal plane. It now takes `pitch_deg` (rotation about the socket's own X applied before the yaw;
-90 points +Y straight down, and `outward` then only sets the ornament's in-plane roll). Fixed in `build_ceiling`:

| sockets | facing | check |
|---|---|---|
| 16 rim-band (r 13.73 / 14.85, z 24.323 / 23.410) | `+Y = -radial` (toward the rotunda axis) | `dot(+Y, radial) = -1.000` |
| 8 ring-1 coffer floor (r 5.20, z 28.914) | `+Y` straight down into the room, `pitch_deg = -90` | `+Y.z = -1.000` |

`scripts/arch_socket_check.py` (new) prints the frame of every socket of a type and passes/fails it; run it with
`blender -b assets/architecture.blend --python scripts/arch_socket_check.py [-- --type <orn_type>]`. All 24 OK.
Positions, counts, types and `docs/sockets.md` are unchanged, and `pitch_deg` defaults to 0 so every other socket
type keeps the exact frame it had.

Caveat for ornament: a -radial facing suits a rosette on the *vertical inner face* of the base ring, but these 16
sockets sit on the rib's horizontal room face (z = `sz - 0.53`). If the band rosettes should stand on that vertical
face instead, say so and I will move them out to the rim edge rather than only re-aim them.
