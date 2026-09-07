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
