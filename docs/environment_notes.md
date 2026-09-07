# Environment notes (ENV) — terrain, lagoon, trees, backdrop

Owner: Environment specialist. Files: `scripts/env_build.py` (entry), `scripts/env_lib.py`, `scripts/env_trees.py`,
`scripts/env_backdrop.py`, `scripts/env_preview.py`, `assets/environment.blend` (collection `ENV`).
World: +Y east (lagoon), −X north, +X south, z = 0 rotunda floor, water at `common.WATER_Z` = −1.3.

```
blender -b --python scripts/env_build.py                 # full rebuild (~30 s) -> assets/environment.blend
blender -b --python scripts/env_build.py -- --quick      # coarse terrain, one seed per species
blender -b --python scripts/env_preview.py -- --cams 01,02,06 --samples 16 --tag x   # linked ENV + placeholder/ARCH
blender -b --python scripts/env_preview.py -- --topdown                              # plan view vs satellite
blender -b --python scripts/env_preview.py -- --lod=1 --cams 01                      # opens the file directly, any LOD
blender -b --python scripts/env_trees.py -- --lineup                                 # species line-up per LOD
```

## Collections and LODs

| collection | content | notes |
|---|---|---|
| `ENV_terrain` | `ENV_terrain_ground`: one mesh, 46.6 k tris, materials lawn / soil (lagoon bed) / gravel (paths, colonnade floors, rotunda apron r<31, hall slab) | constrained Delaunay of a 3-zone grid (2.5 / 6 / 20 m) with the OSM lagoon, islets, colonnade roofs (+2 m), path ribbons and the hall as constraint polygons; heights from `terrain_height(x, y)` (shared by every scatter) |
| `ENV_water` | `ENV_lagoon_water` at z −1.3, planar UV (10 m tiles), islets cut out | the bed slopes from −0.3 m at the shore to −1.5 m (0.16 m/m) |
| `ENV_trees` | 15 source tree objects × 3 LODs, hidden (viewport + render), parked at (−600, −600) | one mesh per (species, seed, LOD), shared by all instances |
| `ENV_tree_instances` → `_LOD0/_LOD1/_LOD2` | 88 placed trees, 3 objects each (`ENV_tree_<species>_<nn>_LOD<k>`) | object flags: **viewport shows LOD1, render uses LOD0** (`hide_render` on LOD1/LOD2, `hide_viewport` on LOD0/LOD2). The lead can swap by excluding the LOD sub-collections in the view layer. Trees beyond 150 m use the LOD1 mesh for LOD0 too. Custom props: species, seed, height_m, note |
| `ENV_shrubs` | shrub belts (peninsula, shore, colonnade fronts, islet) and reed tufts, baked into 5 + 3 objects | 459 shrubs, 160 tufts; none within 24 m of the hero camera |
| `ENV_backdrop` | exhibition hall from OSM `b302` (20 m, pilasters on the concave east wall every 7 m, 24 m arched entrance bay + piers opposite the rotunda), 288 Marina/Presidio buildings within 460 m from `_osm.json` heights, far ground to 2.6 km, bay plane north of −480 m, Presidio wooded ridge (az 195–330°, 520–1500 m, up to 70 m + canopy bumps), SW Presidio hill, south/east city hills, Marin headlands | all single low-poly meshes |
| `ENV_extras` | rip-rap (2 rows of rocks along the whole OSM shore + islet, 6 rock meshes, baked per 45° sector), 65 gulls sitting/floating + 6 flying, lamp posts on the shore path | |

Triangle counts (full ENV): **LOD0 3.70 M, LOD1 1.83 M, LOD2 0.33 M** (budget: LOD1 < 3 M). Terrain + water + rocks +
shrubs + birds + backdrop without trees ≈ 0.19 M. Per tree: cypress 45 k / 17 k / 1.3 k, columnar cypress 50 k / 20 k / 1.8 k,
pine 47 k / 18 k / 1.8 k, eucalyptus 35 k / 13 k / 1.6 k, redwood 27 k / 10 k / 1.6 k, willow 62 k / 37 k / 3.3 k,
broadleaf 22 k / 8 k / 1.5 k (LOD0 / LOD1 / LOD2).

## Terrain and shore (docs/reference_sheet.md §1)

- Lawn base −0.45 m with two octaves of noise (±0.14 m), peninsula lawn −0.6 m (sheet: −0.6), east-shore lawn −0.4…−0.8,
  rip-rap bank top −0.75 m (`SHORE_Z`), islet crown −0.3 m. Blend from the bank to the lawn over 4.5 m.
- Lagoon bed: −0.3 m at the shoreline, 0.16 m/m slope to −1.5 m (sheet: "shallow", 1.0–1.5 m).
- Paths (3 m gravel ribbons): shore loop 7 m outside the water (skipping the peninsula, the colonnade fronts and the
  west), spurs from both pylons, paths behind both colonnades (r 97 about (0, 52)), rotunda west door to the hall,
  two paths from the east shore toward Baker Street. Colonnade floors and the rotunda apron (r < 31, under the ARCH
  platform) are gravel.
- Shoreline: rows of 0.3–0.75 m rocks at the waterline and 0.7 m up the bank (refs 022, 063, 187).

## Planting plan

Species presets are Sapling (`bl_ext.blender_org.sapling_tree_gen`) parameter sets in `env_trees.SPECIES`; leaves are
Sapling leaf cards: `rect` needle strips (0.85–0.95 × 0.3 m) fanning around the twigs for cypress / pine / redwood,
`hex` cards for eucalyptus (1.3 × 0.45 m hanging), willow (0.95 × 0.16 m hanging) and broadleaf (0.75 m). LOD1 halves
the leaf count and enlarges the cards ×1.3; LOD2 is trunk + main limbs with 4 crossed + 2 horizontal crown cards.
Every instance is rescaled to the plan height (source heights 26–38 m), rotated randomly, ±10 % xy scale.

Sources: reference sheet §6 table, satellite_z20 (0.118 m/px, rotunda dome centroid at px 828, 740) and satellite_z18
(0.472 m/px, dome at px 718.6, 633.8) crown positions, and the hero-camera geometry: for the user image / ref 169 the
anchor trees were solved from their pixel position (camera (−16, 113.9, 1.0), 31 mm, image right = north) onto real
land. The OSM lagoon polygon's north embayment reaches Y = −19 at X = −45, so the "dark cluster right of the rotunda"
is two groups: the peninsula's north lobe (X −40…−16, Y 0…26) and the 3–13 m strip between the north colonnade and
the water (canopy overhanging both, as in the satellite tile). Trees whose coordinates fall in OSM water are moved to
the nearest land within 15 m (reported by the build).

Groups: A peninsula north lobe · A2 north-wing strip · B north shore · C south side (columns on the strip between the
south wing and the south embayment, small trees in the podium planter zone r 26–32) · D south shore/pylon · E redwood
screen between colonnades and hall (DPR: planted 1968; generated, 8–11 m spacing, 70 % redwood) · F east / south-east
shore rows (Baker Street) and NE-corner cypresses (DPR) · G wooded islet · H backdrop trees from z18 crowns.

<!-- PLAN_TABLE_START -->
| # | species | X (S+) | Y (E+) | height m | note |
|---|---|---|---|---|---|
| 00 | pine | -31 | 14 | 21 | A peninsula north lobe, cluster core (satellite crown (-35,16)) |
| 01 | redwood | -27 | 8 | 16 | A young redwood in front of the north arch (ref 070) |
| 02 | cypress | -36 | 6 | 24 | A dark mass right of the dome |
| 03 | pine | -38 | 17 | 22 | A |
| 04 | willow | -36 | 24 | 10 | A pale weeping willow at the water in front of the cluster (ref 169) |
| 05 | broadleaf | -30 | 22 | 11 | A shore broadleaf |
| 06 | cypress_column | -36 | -18 | 27 | A2 tall column right of the rotunda (user image x~1020) |
| 07 | pine | -47 | -13 | 17 | A2 strip along the north wing (kept below the colonnade entablature) |
| 08 | cypress_column | -58 | -12 | 27 | A2 second column (user image x~1220) |
| 09 | cypress | -68 | 10 | 24 | A2 at the wing's first box |
| 10 | eucalyptus | -79 | 26 | 28 | B big eucalyptus on the strip (ref 141) |
| 11 | pine | -90 | 22 | 20 | B |
| 12 | willow | -100 | 37 | 9 | B willow at the water (refs 144/145) |
| 13 | eucalyptus | -106 | 20 | 30 | B big eucalyptus behind the willows (ref 171) |
| 14 | cypress | -118 | 8 | 22 | B beyond the north pylon |
| 15 | cypress_column | -112 | 40 | 24 | B tall column beyond the north pylon (ref 169 right) |
| 16 | cypress_column | 45 | -8 | 26 | C cypress column left of the rotunda (user image x~290) |
| 17 | cypress_column | 41 | -13 | 24 | C second column (user image x~330) |
| 18 | broadleaf | 20 | 17 | 13 | C small dark tree touching the rotunda's left edge (user image x~410), in the podium planter zone |
| 19 | eucalyptus | 62 | -30 | 30 | C broad eucalyptus behind the south wing (ref 169 left) |
| 20 | pine | 24 | -22 | 18 | C satellite crown (19,-13) |
| 21 | broadleaf | 31 | -7 | 10 | C satellite crown (26,-3), small |
| 22 | cypress_column | 66 | 40 | 22 | D dense cypress behind the south pylon (ref 169 far left) |
| 23 | eucalyptus | 76 | 46 | 28 | D |
| 24 | pine | 92 | 58 | 18 | D |
| 25 | willow | 78 | 50 | 9 | D willow at the south end of the lagoon |
| 26 | eucalyptus | 104 | 52 | 30 | D south pylon |
| 27 | cypress | 112 | 40 | 22 | D |
| 28 | eucalyptus | -110 | 124 | 30 | F east shore row |
| 29 | eucalyptus | -90 | 126 | 28 | F east shore row |
| 30 | eucalyptus | -70 | 122 | 32 | F east shore row |
| 31 | eucalyptus | -48 | 127 | 30 | F east shore row |
| 32 | eucalyptus | 12 | 128 | 30 | F east shore row |
| 33 | broadleaf | 24 | 130 | 12 | F east lawn |
| 34 | eucalyptus | 34 | 126 | 28 | F east shore row |
| 35 | eucalyptus | 54 | 124 | 30 | F east shore row |
| 36 | eucalyptus | 73 | 120 | 30 | F |
| 37 | eucalyptus | 95 | 118 | 32 | F |
| 38 | eucalyptus | 126 | 127 | 28 | F |
| 39 | cypress | 168 | 114 | 22 | F |
| 40 | eucalyptus | 158 | 28 | 32 | F |
| 41 | pine | 130 | -20 | 20 | F |
| 42 | eucalyptus | 130 | -68 | 28 | F |
| 43 | cypress | 110 | 14 | 20 | F |
| 44 | eucalyptus | 125 | 74 | 30 | F |
| 45 | cypress | 155 | 94 | 24 | F |
| 46 | cypress | -130 | 110 | 24 | F NE-corner Monterey cypress (DPR, Harbor View Inn era) |
| 47 | cypress | -118 | 96 | 22 | F NE corner |
| 48 | cypress | -140 | 82 | 22 | F NE corner |
| 49 | eucalyptus | -158 | 131 | 30 | F |
| 50 | willow | -80 | 72 | 9 | G islet willow (herons, DPR) |
| 51 | broadleaf | -92 | 68 | 12 | G |
| 52 | eucalyptus | -108 | 65 | 24 | G |
| 53 | willow | -100 | 72 | 8 | G |
| 54 | broadleaf | -115 | 62 | 10 | G |
| 55 | eucalyptus | -80 | -111 | 30 | H |
| 56 | cypress | -95 | -100 | 22 | H |
| 57 | eucalyptus | -70 | -125 | 28 | H |
| 58 | pine | -105 | -118 | 20 | H |
| 59 | eucalyptus | -268 | -120 | 30 | H |
| 60 | cypress | -245 | -304 | 24 | H |
| 61 | eucalyptus | -280 | -26 | 30 | H |
| 62 | cypress | -197 | 54 | 22 | H |
| 63 | eucalyptus | -216 | 27 | 28 | H |
| 64 | cypress | -255 | 120 | 24 | H |
| 65 | eucalyptus | -259 | -79 | 30 | H |
| 66 | pine | -253 | -174 | 22 | H |
| 67 | eucalyptus | 24 | -295 | 30 | H |
| 68 | cypress | 170 | -102 | 24 | H |
| 69 | eucalyptus | 168 | 112 | 30 | H |
| 70 | eucalyptus | -88 | -308 | 30 | H |
| 71 | cypress | -30 | -290 | 24 | H |
| 72 | pine | 34 | -36 | 24 | E redwood screen |
| 73 | redwood | 45 | -33 | 31 | E redwood screen |
| 74 | redwood | 55 | -25 | 24 | E redwood screen |
| 75 | redwood | 66 | -18 | 25 | E redwood screen |
| 76 | cypress | 73 | -6 | 22 | E redwood screen |
| 77 | redwood | 85 | 12 | 24 | E redwood screen |
| 78 | pine | 92 | 32 | 22 | E redwood screen |
| 79 | pine | -110 | -4 | 20 | E redwood screen |
| 80 | redwood | -100 | -1 | 25 | E redwood screen |
| 81 | redwood | -83 | -18 | 30 | E redwood screen |
| 82 | cypress | -76 | -22 | 24 | E redwood screen |
| 83 | redwood | -64 | -28 | 30 | E redwood screen |
| 84 | redwood | -52 | -38 | 24 | E redwood screen |
| 85 | pine | -46 | -37 | 20 | E redwood screen |
| 86 | redwood | -34 | -41 | 29 | E redwood screen |
| 87 | cypress | -25 | -47 | 20 | E redwood screen |
<!-- PLAN_TABLE_END -->

## Previews and comparisons

`renders/previews/environment/` (Eevee, QA cameras) and `renders/qa_comparisons/env_*.png` (render | reference | blend):
`env_trees5_cam01_vs_user.png`, `env_trees5_cam01_vs_ref169.png`, `env_trees5_cam06_vs_ref105.png`,
`env_trees5_cam03_vs_ref128.png`, `env_trees4_topdown_vs_satellite_z18.png` (plan view | satellite | blend).

Hero-view check against the user image (cam 01): two narrow dark cypress columns left of the rotunda at x ≈ 250–330 px
with the south colonnade visible through the gap, a small dark tree touching the rotunda's left edge, the dense dark
pine/cypress cluster from the rotunda's right edge to ≈ 1130 px, the tall column at ≈ 1190 px, the north colonnade
visible at the right edge. Tree tops reach the attic base as in the photo. Silhouette match is good; the leaf cards
still read as flat placeholders until the leaf materials arrive (see requests).

## Sky / sun convention (verified for the preview)

`ShaderNodeTexSky` (MULTIPLE_SCATTERING): `sun_rotation = 0` puts the sun toward world +Y (east, az 90°), +90° toward
+X (south). So `sun_rotation = radians(az − 90)` for compass azimuth az in our world. The preview uses az 118.5°,
el 7.4°, sun 4 W/m² at 3600 K, sky strength 0.35, exposure −0.8.

## Open issues / requests

- **Materials agent**: `MAT_leaf_cypress`, `MAT_leaf_eucalyptus`, `MAT_leaf_broadleaf`, `MAT_shrub`, `MAT_reeds` need
  alpha-cut card textures (UV map `UVMap`: conifer cards are `rect` quads 0–1 UV = needle-tuft strip; eucalyptus /
  willow / broadleaf cards are Sapling `hex` (two quads, UV fan) = leaf cluster). Two-sided, translucent. Bark UVs are
  cylindrical fallbacks (u = angle, v = z / 4 m); an object-space triplanar bark is safer. Also requested (not in the
  list): `MAT_backdrop_forest`, `MAT_backdrop_hill`, `MAT_lamp_post` (placeholders exist).
- **Lead / QA**: the hero camera at (−16, 113.9) stands ≈ 14 m behind the OSM shoreline (water at Y ≈ 100 there); the
  user image and ref 169 have water to the frame bottom. Either move the camera to Y ≈ 101 or accept a strip of
  lawn + rip-rap in the foreground (kept clear of shrubs and reeds within 24 m).
- QA cam 02 (−32, 38) is 2–4 m outside the OSM peninsula (in the water); the shore willow was placed at (−36, 24) so it
  stays at the right edge of that frame.
- The OSM north-wing trace is ≈ 5–8 m east of the satellite's; tree positions follow the satellite where they conflict.
- The exhibition hall footprint (`b302`) is the full OSM polygon (97 m deep); the satellite shows a ≈ 45 m crescent
  with roads west of it. Backdrop only — replace when/if ARCH models the hall.
- Wind-sculpting of the cypresses (leaning away from the westerlies) is not modelled; no per-instance weathering.
