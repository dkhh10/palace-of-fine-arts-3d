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
- `frieze_run` (28): 24 on the ressaut faces (`run_length`, `run_dir`) + 4 colonnade row runs (`subtype='greek_fret'`,
  `arc_center`, `arc_radius`, `run_length`) for the fret architrave.
- `rosette_ceiling` (24): 8 rim (face centres), 8 rim (corners), 8 ring-1 squares.
- Bases are modelled by ARCH (no `base_*` sockets). Dentils are geometry (LOD0 object); egg-and-dart is a plain ovolo
  in the sweep profile (ORN may overlay a strip using the `frieze_run` sockets' geometry).

## Known gaps / open issues

- Placeholders: `ARCH_placeholders` holds crude capitals, urns, figures, keystones so previews have a silhouette; the lead
  should EXCLUDE that collection when linking if ORN assets are present.
- Hero camera: with the sheet's dimensions the attic corner blocks span 509 px of the 1280 px hero frame; the user photo
  spans ~436 of 1320 (33 %). The model matches OSM/satellite/085, so the camera is ~20 % too close for that photo
  (or the photo's lens is ~37 mm). Comparisons use `arch_compare.py --ref-zoom 1.2` to check proportions.
- QA cam 04 (`CAM_qa_04_rotunda_ceiling`) has rotation (0,0,pi) which looks DOWN; (pi,0,0) looks up with the top of the
  frame toward -Y. Previews add `CAM_arch_ceiling_up` for the ceiling view.
- `common.set_lod_visibility` toggles only `hide_viewport`; the saved file also has `hide_render=True` on LOD0/LOD2.
