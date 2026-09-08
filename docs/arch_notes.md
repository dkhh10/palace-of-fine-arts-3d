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

### Base-ring rosette band moved onto the vertical face (lead, 2026-09-08)

Following the caveat above, the 16 band rosettes are off the rib's horizontal underside and onto the surface the
sheet actually describes (line 258, "base ring with rosette band above the inner arches"): the **vertical inner
face of the inner ring wall**, radius `INNER_WALL_APOTHEM - INNER_WALL_THICKNESS` = **14.182 m** from the axis.
Band height is derived from the two things that bound it, not eyeballed:

| bound | value |
|---|---|
| crown of the inner arches `INNER_ARCH_SPRING_Z + INNER_ARCH_SPAN / 2` | 22.423 |
| underside of the saucer rim `CEILING_RING_Z - COFFER_DEPTH` | 23.950 |
| **`P.ROSETTE_BAND_Z`** = midpoint of that 1.53 m zone | **23.186** |

Placement is now **two per octagon face at ±`ROSETTE_BAND_HALF_ANGLE` (11.25 deg) from the face normal** instead of
alternating face centre / octagon vertex: same 16 sockets and the same 22.5 deg spacing round the ring, but every
one of them stands on a real flat face (the old vertex sockets sat on the corner, where there is no face). Each
socket's own distance from the axis is 14.182 / cos 11.25 = **14.46 m**; its `+Y` is the inward **face** normal, so
`dot(+Y, radial)` is **-0.981**, not -1.000 — the two sockets sharing a face lean 11.25 deg either side of their
own radius. `+Z` is world up (upright on the face). `size_hint` is 0.7 for all 16 (they are one band, one size);
the 8 coffer-floor sockets are unchanged at z 28.914, r 5.20, `+Y.z = -1.000`.

`scripts/arch_socket_check.py` now checks the band against its face plane rather than against radial, and reports
the spread of the 16 face-plane distances (0.0 mm). All 24 OK. Counts and types unchanged; `docs/sockets.md` has
the one-line placement note the lead authorised.

## Polish round 3 (QA-04-7 rib material, QA-04-11 ref 062 station)

### QA-04-7 (architecture half) — the coffer rib plates now carry their own material

QA: "no tonal difference between rib and panel (ribs share the panel material; ARCH rib plate material name still
pending)". Ref 083 has coffer **panels at L 93-130 and ribs at L 22-50**, a 2.5-3x ratio, so materials needs two
surfaces to work with. Every coffer in the build is a *rib plate* (a slab whose holes are the coffers) standing proud
of a *panel surface* behind it, so the split is one material per OBJECT — no face groups, no second slot:

| surface | objects | material before | material now | part_type |
|---|---|---|---|---|
| saucer-dome ribs | `ARCH_rotunda_ceiling_ribs` (1) | `MAT_plaster_ceiling` | **`MAT_plaster_ceiling_rib`** | ceiling |
| saucer-dome panels (coffer floors) | `ARCH_rotunda_ceiling_field` (1) | `MAT_plaster_ceiling` | unchanged | ceiling |
| barrel-vault ribs | `ARCH_rotunda_vault_coffers_00..07` (8) | `MAT_concrete_inner` | **`MAT_plaster_ceiling_rib`** | wall |
| barrel-vault panels (soffit) | `ARCH_rotunda_vault_00..07` (8) | `MAT_concrete_inner` | unchanged | wall |

9 objects carry the new name. They also carry a custom property **`surface = "coffer_rib"`**, so materials can select
them without matching object names (`[o for o in bpy.data.objects if o.get("surface") == "coffer_rib"]`). Assigned
through `common.load_material` as usual, so it falls back to a placeholder until materials ships the material — it is
a placeholder in `assets/architecture.blend` today, which is expected and harmless.

Note for materials: the rib plate's geometry is **rib face + reveal walls + the coffer box sides** (the registers of
`P.COFFER_REGISTERS` / `P.VAULT_COFFER_REGISTERS`); the coffer *floor* is the other object. So a recess-dirt gradient
authored on `MAT_plaster_ceiling_rib` lands on the rib soffit and the splays, and the bright panel stays on
`MAT_plaster_ceiling` / `MAT_concrete_inner`. Geometry, tri counts, sockets and `docs/sockets.md` are unchanged.

### QA-04-11 — ref 062's station fitted: 92 m at 42 mm, not 50 m at 26 mm

New tool `scripts/arch_ref062_fit.py` (numpy only, imports `arch_domecheck`'s camera and solids so the fit and the
overlay cannot drift apart). Sheet: `renders/qa_comparisons/arch_qa04_11_ref062_fit.png` (annotated overlay on top;
below, ARCH rendered at the fitted station beside the photograph).

**Why not `arch_domecheck --fit` as for ref 063.** ref 063's fit matched the model's sky silhouette to the photo's.
That cannot work on ref 062: its top silhouette is **ornament** — the attic corner-block volutes, urns and standing
figures sit 20-80 px above the cornice the analytic model knows about (measured: the photo's top-profile minimum is
row 13-19 at x 800-850, on a volute, while the attic cornice on the same face is at row 99). So the fit is on
hand-read **landmark rows** on the near face's centre line instead, each at a known (z, radius from the axis):

| landmark | z | radius | measured row | fitted row | Δ |
|---|---|---|---|---|---|
| dome apex (cap top) | 53.4 | 0 | 35 | 34.9 | -0.1 px |
| attic top (drum springs) | 38.3 | 22.24 | 99 | 102.8 | +3.8 px (0.27 %H) |
| attic base (modillion corbels) | 31.2 | 21.5 | 330 | 308.6 | -21.4 px (1.56 %H) |
| outer arch springing | 17.5 | 21.5 | 700 | 710.7 | +10.7 px (0.78 %H) |

**Fit (ref 062, 1920x1371): az 35.3 deg, D = 91.7 m, lens = 42.4 mm, pitch +13.45 deg, eye 1.55 m**, i.e. station
world **(-73.2, 55.2, 1.55) looking at (0, 0, 23.5)**; chi2 4.09 on 4 rows / 3 free parameters. Eye height is not
recoverable (1.30-1.85 m all give D 91.1-92.1, lens 42.0-42.7 — the fit is flat in it).

**Independent checks the fit did not use:**

| check | model at the fitted station | photo | error |
|---|---|---|---|
| attic-ring on-screen width | 1241 px | 1265 px | **-1.9 %** |
| podium base row | 1306 | 1345 | -2.8 %H (0.953 vs 0.981 of frame) |
| architrave bottom (z 27.4) | row 417 | 405-418 | within the moulding |
| drum guilloche cushion top (z 42.5) | row 58 | 55 | +3 px |
| a 1.7 m figure at r 47 | 92 px tall | 87 px | +6 % |

Top, base and width are all inside QA-04-11's 3 % bar except the base row at 2.8 %H, which is itself inside it.

**Which hypothesis this supports: (c), the photo was taken from farther away with a longer lens.** Not the attic/drum
height and not the podium radius. The decisive point is *lens-, tilt- and framing-independent*: ref 062 shows the dome
cap above the near face's attic cornice, which is purely a comparison of two elevation angles,

    (apex - h) / D  >  (ATTIC_Z1 - h) / (WALL_APOTHEM + 0.74)   ->   D > 76.4 m

with the current stack. Nothing about the camera can change that number. Inverted, to see the same thing from
**45 m** the apex would have to be at **74.2 m** (it is 53.4) or the attic top at **27.8 m** (it is 38.3, and 27.8 is
*below* the entablature) — and from 50 m, 67.7 m or 30.3 m. Both are impossible, and both would destroy the cam01
silhouette that matches refs 169/085/169-crop within 1 %. **The podium (rostra) radius does not appear in the
inequality at all**, so QA's hypothesis (2) cannot be the cause either. Recommendation to the lead: **change nothing
in the rotunda's proportions**; ref 062 is a ~92 m / ~42 mm photograph and QA's "~50 m, ~26 mm" reading of it is the
error. This is the same finding as round 1's ref 063 (fitted at 115 m / 40 mm when cam05 stood at 71 m / 20 mm): both
canonical "close" photographs are long-lens shots.

**One thing the fit does raise, for the lead not for me.** The OSM lagoon rings in
`reference/plans/site_local.json` put every station at az 25-60 beyond ~45 m **in the water**, so the fitted station
is not standable on the site as modelled — yet ref 062's foreground is dry garden with people on a path. Since the fit
is face-on to the az-37 face within 1.7 deg, the likelier explanation is that the OSM shoreline is short on the north-
east side (the peninsula/lawn there is bigger than `site_local.json` says) rather than that the photo is from due
north. That is an ENV/site question and it is exactly what stopped QA reproducing the station on land; it is not a
rotunda-proportion question. `arch_ref062_fit.py` prints the land/water table so the lead can see it.

**Sub-metre detail noticed while fitting, NOT changed.** At the fitted station the drum's cornice-ring top rim
(`DRUM_CORNICE_R` 18.7 at z 43.4) projects to row 22, i.e. **13 px above the dome apex**, whereas ref 062 has the dome
apex 20 px above the ring. Everything else in the drum matches (the guilloche cushion top is 3 px out), so this is
about **0.4 m of ring radius**, or the same amount of ring height — a moulding refinement, not a proportion. Left for
the lead to decide, since any drum change touches the arbitrated round-1 dome fit.

## Polish round 4 (QA-05-6 rotunda entablature; drum-ring re-measurement, report only)

### QA-05-6 — why two rounds of shading could not put a shadow band under the cornice

QA: "row-profile std **20.9** vs the photo's **53.6** on box 900 262 1020 296 of the cam01 Cycles hero; texture std
0.52 of the photo's, unchanged three rounds; the dentil row casts no shadow under the corona." Materials had already
shown twice that shading cannot supply it. The reason is in the solar geometry, and it is worth writing down because
it inverts the usual intuition:

- Sun **az 118.5 / el 7.4** (lighting's NOAA position); the hero (lagoon) face normal is **az 82**, so the sun is
  Δ = 36.5° off the face and 7.4° above the horizon.
- A horizontal ledge projecting *p* therefore drops a shadow of only `p · tan(7.4°)/cos(36.5°)` = **0.16 p** down the
  wall. A 1 m cornice shades 16 cm of frieze. **None of ref 169's dark bands is a cast shadow** — at this sun the
  light slides in under every overhang.

What the photograph's bands actually are, all three of them geometry:

| mechanism | rule | consequence for the profile |
|---|---|---|
| (a) downward-facing soffit | never sees the sun at any elevation; reads at 20-25 % of the sunlit wall | the corona needs a **deep** soffit, not just a projecting edge |
| (b) wall hidden *behind* a projecting course | cam01 looks up at ~20°, so `p` metres of projection lift a point `p · tan 20° = 0.365 p` up the frame and hide that much wall | the corona's projection sets the *height* of the dark band |
| (c) gaps laterally shadowed by the block in front | `tan 36.5° = 0.74` m of shadow per metre of block depth | dentils/modillions must be **deep** relative to their gaps |

The old profile satisfied none of them: corona edge at d 1.05 with the modillion fronts at d 1.02 (0.03 m of
overhang → **no visible soffit at all**), dentils at d 0.36-0.51 sitting *behind* the ovolo above them at d 0.56-0.62
(so they could neither catch light nor shade anything), modillions 0.40 deep on a 0.45 gap (0.30 m of lateral
shadow → a third of every gap stayed sunlit).

### Measurements on ref 169 at hero scale

Scale: QA's round-05 alignment maps ref 169 → the 1920x1080 hero by `p·1.3108 + (−291.8, −124.6)`; the render runs
at **13.6-14.1 px/m** on the near face (two independent reads: the spacing of the two cornice bands the old build
puts on screen, and the entablature's own on-screen height), so the raw photo is **10.7 px/m**.

| measured on ref 169 | photo px | metres | used for |
|---|---|---|---|
| entablature, whole on-screen height (cornice top edge → the black line at the capitals) | 47.5 | 4.35 apparent | corona projection |
| cornice band (crown fillet → bottom of the bracket band) | 20 | 1.83 apparent | `CORNICE_H` |
| plain face below it (frieze + architrave read as one surface) | 22 | 2.02 apparent | `ARCHITRAVE_H + FRIEZE_H` |
| bracket (modillion) band | 9 | 0.86 apparent | modillion height + corona projection |
| fine course above the brackets | 4.5 | 0.43 apparent | egg-and-dart course |
| fine course pitch along the run (sign changes + FFT) | 5.0 | **0.47** | `egg_pitch` |
| bracket pitch along the run | 11.4 | **1.07** | `modillion_pitch` |

Two derivations follow, neither of them eyeballed:

1. **Corona projection.** 3.8 m of entablature reads 4.35 m tall on screen because its top course projects and its
   bottom course does not: `4.35 = 3.80 + 0.365 · (corona_d − 0.14)` → **corona_d = 1.65 m** (built at 1.66).
2. **The split.** `1.83 = CORNICE_H + 0.365 · (corona_d − frieze_d)` → `CORNICE_H = 1.83 − 0.53 = 1.30`; reading the
   band down to where the last dark course ends instead gives 1.72. Built at **1.75**, with the plain face split
   1.15 architrave / 0.90 frieze. **The 3.8 m total is untouched** — it is what carries the silhouette — but the
   sheet's 1.4 / 1.2 / 1.2 split is superseded (the sheet's own "measured" column had the whole entablature at 3.3).
3. **Order.** ref 169 puts the fine 0.47 m course **above** the brackets, not below: corona → egg-and-dart ovolo →
   modillions → ovolo → dentils → frieze. The old build had the egg course between the dentils and the modillions.

### The profile as built (d = outward from the wall plane at apothem 21.5, z relative to ENTABLATURE_Z0 = 27.4)

| course | z | d | note |
|---|---|---|---|
| fascia 1 / 2 / 3 | 0.00-0.42 / 0.42-0.82 / 0.82-1.02 | 0.14 / 0.24 / 0.34 | 0.10 m steps (0.08 before) |
| bead-and-reel astragal | 1.06-1.11 | 0.42 | sheet row 13 |
| architrave crown | 1.14-1.15 | 0.50 | overhangs the frieze by 0.30 |
| frieze | 1.15-2.05 | 0.20 | `frieze_run` sockets moved with it (0.24 → 0.20) |
| cyma reversa foot | 2.05-2.17 | 0.24-0.40 | |
| **dentils** | 2.17-2.57 | bed 0.40, **0.34 deep**, 0.18 wide, **0.38 pitch** | lateral shadow 0.25 > the 0.20 gap → every gap black |
| ovolo | 2.57-2.71 | 0.46-0.52 | |
| **modillions** | 2.71-3.29 | bed 0.52, **0.68 deep**, 0.50 wide, **1.06 pitch** | lateral shadow 0.50 vs a 0.56 gap; the bed is in any case hidden behind the corona for 0.38 m |
| egg-and-dart ovolo | 3.29-3.43 | 0.52-0.80, eggs at 0.47 pitch | LOD0 only |
| **corona soffit** | 3.48 | **0.80 → 1.66 (0.86 m deep)** | downward-facing: never sunlit |
| corona fascia / drip / cyma recta | 3.48-3.80 | 1.66-1.70 → 1.36 | |

Dentils and modillions are now in **both LODs** (one mesh, two objects: `_LOD0` and `_LOD1`) because they are what
makes the band read; only the egg-and-dart stays LOD0.

### Drum cornice ring — re-measured, NOT changed (round 3 flagged it as "about 0.4 m")

Recomputed at round 3's own fitted ref-062 station (D 91.7 m, 42.4 mm, pitch +13.45°, eye 1.55 m), with
`row(z, r)` from `arch_domecheck.Cam`:

| | model | ref 062 (measured on the photo) |
|---|---|---|
| dome apex (z 54.0, r 0) | row 35.6 | row 34-35 |
| drum cornice ring near rim (`DRUM_CORNICE_R` 18.7 at z 43.4) | row 21.0 — **14.6 px ABOVE the apex** | the ring's dark underside runs rows 90-120, its top rim ≈ row 88 — **~54 px BELOW the apex** |
| guilloche/scale cushion top (z 42.5, r 17.5) | row 60.8 | scale band runs rows ~50-88 — the cushion itself is right |

Closing ~69 px of image displacement needs `DRUM_CORNICE_R` 18.7 → **≈ 16.2 (−2.5 m)** or the ring top 43.4 →
**≈ 42.0 (−1.4 m)**, not the 0.4 m round 3 estimated (that figure came from a different reading of the ring's rim).
There is a second, larger finding behind it: **ref 062 puts the imbricated scale band directly under the dome, with
the moulded ring BELOW the scale band**, while the model (following the catalog's "scale pattern over a plain torus,
*then* a moulded cornice ring") stacks the ring on top of the cushion. Since the cushion's own row is within 6-10 px,
the whole discrepancy lives in that ring. Reported only — any drum change touches the arbitrated round-1 dome fit.

### Round 4 checkpoint (session stopped before any Blender run)

**Changed (code only — `assets/architecture.blend` has NOT been rebuilt yet, so the .blend on disk is still round 3):**
`arch_params.ARCHITRAVE_H / FRIEZE_H / CORNICE_H` 1.4 / 1.2 / 1.2 → **1.15 / 0.90 / 1.75** (3.80 total unchanged);
`arch_build.CORNICE` + `rotunda_entablature_profile()` rebuilt per the table above (corona 0.24 → **1.66 m** with a
0.86 m soffit, modillions 1.06 pitch × 0.68 deep, dentils 0.38 pitch × 0.34 deep, egg-and-dart moved above the
modillions, frieze 0.24 → 0.20 with its `frieze_run` sockets); dentils + modillions duplicated into `_LOD1`.
New tools: `arch_entab_measure.py` (reproduces QA's metric exactly: 20.9 vs the photo's 54.1, texture 0.512),
`arch_entab_probe.py` (prints which model (d, z) owns which cam01 row; renders border crops with QA's Cycles preset),
`arch_p4r4_sheet.py` (the before/after/ref composite).

**Measured:** everything in the two sections above — the solar geometry that rules out cast shadows, the ref-169 band
heights and pitches, the two derivations (corona projection 1.65 m, cornice height 1.5-1.7 m), and the drum-ring
re-measurement (−2.5 m of ring radius or −1.4 m of ring height, not round 3's 0.4 m; and ref 062 puts the scale band
above the ring, not below).

**Not yet done — next session, in this order:** (1) `blender -b master.blend --python scripts/arch_entab_probe.py --
--map` to pin the row↔(d, z) mapping (the whole design was laid out on a 13.6-14.1 px/m estimate derived from the
round-05 hero, and one number in it — which of the two dark rows at 262-270 is the modillion band — is still
inferred); (2) BEFORE silhouette off the current .blend, then `arch_build.py`, then AFTER silhouette (crop
690 40 1235 520, apex/corner rows within 1 %); (3) `build_master.py` in this worktree and a border-crop Cycles render
of rows 180-340 with `arch_entab_probe --render`; (4) `arch_entab_measure stats` on box 900 262 1020 296 and iterate.

**Known risk to flag to the lead now:** under QA's round-05 alignment the model's entablature sits ~15 px (≈1.1 m)
HIGHER in the hero frame than ref 169's — the photo's cornice occupies render rows ~263-290, the model's rows
~250-271 — while the entablature's *size* on screen matches (4.25 m apparent vs the photo's 4.35). The QA box
900 262 1020 296 was drawn on the photograph's cornice, so part of it lands on the model's frieze no matter how the
cornice is built. The rebuild should still roughly double the row-profile std; if it lands short of 0.75, the
residual is a stack question (attic height vs entablature height, the arbitrated round-1 fit), not a cornice one,
and the honest test is the same 34-row box placed on the model's own cornice. Nothing here changes the silhouette.
