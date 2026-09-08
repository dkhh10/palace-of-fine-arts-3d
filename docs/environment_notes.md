# Environment notes (ENV) — terrain, lagoon, trees, backdrop

Owner: Environment specialist. Files: `scripts/env_build.py` (entry), `scripts/env_lib.py`, `scripts/env_trees.py`,
`scripts/env_backdrop.py`, `scripts/env_preview.py`, `assets/environment.blend` (collection `ENV`).
World: +Y east (lagoon), −X north, +X south, z = 0 rotunda floor, water at `common.WATER_Z` = −1.3.

```
blender -b --python scripts/env_build.py                 # full rebuild (~100 s) -> assets/environment.blend
blender -b --python scripts/env_build.py -- --quick      # coarse terrain, one seed per species
blender -b --python scripts/env_preview.py -- --cams 01,02,06 --samples 16 --tag x   # linked ENV + placeholder/ARCH
blender -b --python scripts/env_preview.py -- --topdown                              # plan view vs satellite
blender -b --python scripts/env_preview.py -- --lod=1 --cams 01                      # opens the file directly, any LOD
blender -b --python scripts/env_trees.py -- --lineup                                 # species line-up per LOD
blender -b --python scripts/env_sightlines.py                                        # QA-01-6 tree/camera sight lines
blender -b --python-expr "import sys;sys.path.insert(0,'scripts');import env_preview;env_preview.sky_through_wing('north')" 
```

## Collections and LODs

| collection | content | notes |
|---|---|---|
| `ENV_terrain` | `ENV_terrain_ground`: one mesh, 46.6 k tris, materials lawn / soil (lagoon bed) / gravel (paths, colonnade floors, rotunda apron r<31, hall slab) | constrained Delaunay of a 3-zone grid (2.5 / 6 / 20 m) with the OSM lagoon, islets, colonnade roofs (+2 m), path ribbons and the hall as constraint polygons; heights from `terrain_height(x, y)` (shared by every scatter) |
| `ENV_water` | `ENV_lagoon_water`: **closed volume** (QA-01-3) — surface at z −1.3 triangulated at ~2 m, a bed 0.12–1.50 m below it, vertical walls at the shore and around both islets; 17.4 k tris, 0 open edges, planar UV (10 m tiles) | the murk in `MAT_water_lagoon` is a Cycles volume and only works inside a closed mesh. The bed sits 5 cm above the terrain bed so it never z-fights |
| `ENV_trees` | 15 source tree objects × 3 LODs, hidden (viewport + render), parked at (−600, −600) | one mesh per (species, seed, LOD), shared by all instances |
| `ENV_tree_instances` → `_LOD0/_LOD1/_LOD2` | 169 placed trees, 3 objects each (`ENV_tree_<species>_<nn>_LOD<k>`) | object flags: **viewport shows LOD1, render uses LOD0** (`hide_render` on LOD1/LOD2, `hide_viewport` on LOD0/LOD2). A tree uses the next lighter mesh when no QA camera is within `FAR_RADIUS` = 130 m of it, and the E2/E3 back screen rows always do. Per-instance random z-rotation, asymmetric xy scale (0.82–1.16) and a 0–4.5° wind lean, so no two crowns share a silhouette (QA-01-7). Custom props: species, seed, height_m, note |
| `ENV_shrubs` | 1 761 **separate objects** sharing 15 source meshes: pittosporum mounds (4 sizes), upright mahonia (2), agapanthus clumps (3), dry reeds (3), leafless twig shrubs (3) | QA-01-2. One object per bush so the library foliage materials' per-object random (`PFA_instance`) varies hue/value per plant; a joined belt would be one flat colour. Nothing within 34 m of the hero camera |
| `ENV_backdrop` | exhibition hall from OSM `b302` (20 m, 27 pilasters on the concave east wall every 7 m, 102 glazed bays between them, cornice + string course + plinth bands, curved roof (eave 15.5 m + 4.5 m rise), 24 m arched entrance bay with the green door opposite the rotunda — QA-01-8), 288 Marina/Presidio buildings within 460 m from `_osm.json` heights, far ground to 2.6 km, bay plane north of −480 m, Presidio wooded ridge (az 195–330°, 520–1500 m, up to 70 m + canopy bumps), SW Presidio hill, south/east city hills, Marin headlands | all single low-poly meshes |
| `ENV_extras` | rip-rap (2 rows along the whole OSM shore + islet, 1 273 boulders 0.32–0.80 m straddling the water line, 7 rock meshes baked per 45° sector — QA-01-19), 65 gulls sitting/floating + 6 flying, lamp posts on the shore path | |

Triangle counts (full ENV, 2026-09-07 fix round): **LOD0 17.89 M, LOD1 8.39 M, LOD2 3.76 M** (the lead's budget is
~10 M at LOD1; the brief's original 3 M no longer holds now that the crowns are dense enough to be opaque). Terrain +
water + rip-rap + backdrop + birds ≈ 0.19 M, shrubs 3.29 M (the shrubs have no LOD, so they cost the same at
every level — the lever is `cover` in `make_shrub_mesh`), trees the rest. Per LOD0 tree: cypress 101 k, columnar
cypress 99 k, pine 108 k, redwood 96 k, eucalyptus ~95 k, willow 82 k, broadleaf 64 k (LOD1 ≈ 0.35 x, LOD2 ≈ 0.02 x).
`assets/environment.blend` is ~163 MB uncompressed (21 unique tree meshes dominate; instances share them).

## Terrain and shore (docs/reference_sheet.md §1)

- Lawn base −0.45 m with two octaves of noise (±0.14 m), peninsula lawn −0.6 m (sheet: −0.6), east-shore lawn −0.4…−0.8,
  rip-rap bank top −0.75 m (`SHORE_Z`), islet crown −0.3 m. Blend from the bank to the lawn over 4.5 m.
- Lagoon bed: −0.3 m at the shoreline, 0.16 m/m slope to −1.5 m (sheet: "shallow", 1.0–1.5 m).
- Paths (3 m gravel ribbons): shore loop 7 m outside the water (skipping the peninsula, the colonnade fronts and the
  west), spurs from both pylons, paths behind both colonnades (r 97 about (0, 52)), rotunda west door to the hall,
  two paths from the east shore toward Baker Street. Colonnade floors and the rotunda apron (r < 31, under the ARCH
  platform) are gravel.
- Shoreline (QA-01-19): 1 273 boulders, 0.32–0.80 m, in two rows — a broken waterline row whose centres straddle
  z = WATER_Z (about a third of each stone stands proud, the rest is wet/submerged) and a smaller bank row 0.8–1.9 m
  up the slope; density varies along the shore (noise) and is highest on the rotunda peninsula (refs 022, 063, 187).
- The OSM extract (`reference/plans/_osm.json`) contains **no highway/footway ways** at all, so the paths are the
  satellite-derived polylines above, not OSM geometry; with `MAT_gravel_path` they now read in the cam06 aerial.

## Planting plan

Species presets are Sapling (`bl_ext.blender_org.sapling_tree_gen`) parameter sets in `env_trees.SPECIES`. Leaves are
Sapling `rect` cards carrying the library's alpha-cut cluster textures (a card is a needle spray / leaf clump, not one
leaf). **Foliage sizing (QA-01-7), measured in the built file** — card width x long side, and what that is in pixels
at 70 m in a 1920 px frame through the 24 mm hero lens:

| species | LOD0 cards / tree | card (median instance) | px at 70 m | worst instance |
|---|---|---|---|---|
| cypress | 35 k | 10 x 50 cm | 1.9 x 9.2 px | 12.5 px |
| columnar cypress | 30 k | 10 x 50 cm | 1.8 x 8.6 px | 9.8 px |
| pine | 36 k | 9 x 48 cm | 1.6 x 7.6 px | 9.5 px |
| redwood | 37 k | 11 x 46 cm | 2.1 x 8.5 px | 10.4 px |
| eucalyptus | 33 k | 13 x 52 cm | 2.4 x 9.5 px | 9.8 px |
| willow | 23 k | 5 x 45 cm | 0.9 x 6.8 px | 7.4 px |
| broadleaf | 23 k | 22 x 44 cm | 4.1 x 8.0 px | 8.1 px |

QA-01-7 asked for no card wider than 6 px at 60–80 m. The card **width** is 1–4 px everywhere; the long side is 7–10 px.
Shrinking the long side to 6 px (0.33 m) was tried and rejected: at that size a 25 m crown needs about 95 k cards to
stop being see-through (measured — at 35 k cards of 0.28 m the crowns rendered as bare branches with leaf tufts, see
`renders/previews/environment/20260907_153902_tree_lineup_LOD0.png`), which is ~2.5x the whole LOD0 budget. The cards
carry alpha-cut cluster textures, so no card has a straight edge in the render; crown opacity is measured instead by
the sky-through-the-bays test below.

LOD1 keeps 42 % of the leaves at ×1.25 card size; LOD2 is trunk + main limbs with 4 crossed + 2 horizontal crown cards.
Every instance is rescaled to the plan height, randomly rotated, given an asymmetric xy scale (0.82–1.16) and a
0–4.5° wind lean so crown silhouettes are irregular and never repeat.

Sources: reference sheet §6 table, satellite_z20 (0.118 m/px, rotunda dome centroid at px 828, 740) and satellite_z18
(0.472 m/px, dome at px 718.6, 633.8) crown positions, and the hero-camera geometry. The OSM lagoon polygon's north
embayment reaches Y = −19 at X = −45, so the "dark cluster right of the rotunda" is two groups: the peninsula's north
lobe and the 3–13 m strip between the north colonnade and the water. Trees whose coordinates fall in OSM water are
moved to the nearest land within 15 m (reported by the build) — this is why the A group's plan coordinates and its
built coordinates differ by a few metres.

Groups: A peninsula north lobe · A2 north-wing strip · B north shore · C south side · D south shore/pylon ·
E1/E2/E3 redwood screen behind the colonnades (DPR: planted 1968) · F east / south-east shore rows (Baker Street) and
NE-corner cypresses (DPR) · G wooded islet · H backdrop trees from z18 crowns.

**Screen layout (QA-01-6).** The wings are arcs struck from (0, 52), so `env_trees.redwood_screen` works in polar
coordinates about that point: for every 2° of the wing's sweep it measures the polygon's outermost radius and plants
three staggered rows at +4.5 m (4.0 m spacing, 26–34 m tall), +11 m (5.5 m) and +19 m (8.0 m). The previous version
walked the polygon's edge segments and put trees *inside* the colonnade band — one cypress ended up 1 m from QA cam 03.
Screen positions are now also rejected inside any colonnade polygon, inside the hall, and within 16 m of any QA camera.

**Sight lines (QA-01-6), `blender -b --python scripts/env_sightlines.py`** — projects every planted tree into the QA
cameras and lists those inside a "must stay clear" band:

- cam 03 (left 30 % of frame, within 60 m): **clear**. The two C-group trees that stood 5 m and 7 m in front of the new
  camera at (40, −21) moved to (62, −46) and (74, −38), behind the camera; the screen keep-out did the rest. What is
  left in that band is the north wing's screen at 44–60 m, i.e. background beyond the rotunda, as in ref 128.
- cam 02 (right 40 %, within 60 m): **not fully clear, by design.** The reference sheet §6 puts the dense dark cluster
  at X −20…−40, Y 10…30 and the OSM shoreline gives no land west of about X = −42 there, so the cluster cannot be moved
  out of the new cam 02 at (−45, 52). It was moved as far south-west as the land allows: nearest crown edge 29 m (was
  22 m), trunks now project at x ≥ 0.70 instead of 0.64, i.e. into the right-edge band where ref 062 also shows a dark
  conifer. Moving it further would break the hero (cam 01 x 0.70–0.90 = "right of the rotunda") — **lead's call**.

**Peninsula planting band (lead's call, 2026-09-07).** The hero camera stays at (−14.1, 100), 23 mm, shift 0.07, so the
bare bright lawn between the shore belt and the podium is broken up in ENV instead: `build_shrubs` step 2c walks four
rings 8.5 / 11.5 / 14.5 / 17.5 m outside the lagoon polygon, keeps points with `APRON_R − 1 < r < 58` (between the ARCH
platform apron and the shore belt) and plants clumps of 3-7 pittosporum / mahonia / agapanthus with a 10 m bed noise so
mown lawn still shows between the beds: **319 bushes**. Six low trees (2 willows at the water, 4 broadleaves 6-8 m,
group `P` in the plan) sit in the same strip; all six project to cam 01 x 0.21-0.30 or 0.64-0.80 with their crowns
below y 0.52, so the rotunda's body, arch and dome stay clear. Sheet s6: "low mounded shrubs (Mahonia, agapanthus,
pittosporum) ... small trees in the podium planter zone".

**Library material remaps.** `env_lib.mat_or(preferred, fallback)` takes the library material when the name exists and
falls back while it does not, so the names the materials agent is adding take effect on the next build with no code
change: pine + redwood foliage `MAT_leaf_pine` → `MAT_leaf_cypress`, mahonia `MAT_shrub_light` → `MAT_shrub`, dry reeds
and twig shrubs `MAT_shrub_dry` → `MAT_reeds`. `MAT_backdrop_roof / _skylight / _door_green` come straight from
`common.load_material`, which already swaps in the real material the moment it is in the library.

**Sky through the colonnade bays (QA-01-6 acceptance), `env_preview.sky_through_wing(wing)`**: renders cam 01 with a
transparent film and counts background pixels inside the frame box of that wing between z = 4 m and z = 17 m.

The tool is new this round, so there is no pre-round baseline; these are the three measured states during the fix
(QA's target is <= 20 % for the north wing):

| | polar screen rebuilt | rows densified | final (denser crowns) |
|---|---|---|---|
| north wing (box x 0.622–1.000, y 0.361–0.607) | 10.2 % | 4.1 % | **1.7 %** |
| south wing (box x 0.000–0.370, y 0.361–0.625) | 25.1 % | 14.8 % | **9.5 %** |

<!-- PLAN_TABLE_START -->
| # | species | X (S+) | Y (E+) | height m | note |
|---|---|---|---|---|---|
| 00 | pine | -90 | -2 | 17 | A cluster core; QA-01-6: pulled west so cam02's right 40% is clear (42 m, x 0.82-1.10) |
| 01 | redwood | -40 | -2 | 16 | A young redwood at the north arch (ref 070) |
| 02 | pine | -90 | 2 | 18 | A cluster, second crown |
| 03 | willow | -86 | 10 | 10 | A pale weeping willow at the water in front of the cluster (ref 169) |
| 04 | broadleaf | -85 | 8 | 11 | A shore broadleaf at cam02's right edge |
| 05 | cypress | -96 | -7 | 23 | A cluster depth (QA-01-6: mass kept dense after the move west) |
| 06 | pine | -90 | 1 | 20 | A cluster depth |
| 07 | broadleaf | -30 | 30 | 8 | P peninsula bed, right of the rotunda (cam01 x 0.71-0.78) |
| 08 | willow | -22 | 38 | 7 | P low willow at the water in front of the podium (cam01 x 0.64-0.71) |
| 09 | broadleaf | -36 | 20 | 7 | P peninsula bed (cam01 x 0.75-0.80) |
| 10 | broadleaf | 26 | 32 | 7 | P peninsula bed, left of the rotunda (cam01 x 0.21-0.26) |
| 11 | willow | 18 | 40 | 7 | P low willow at the water, left (cam01 x 0.24-0.30) |
| 12 | broadleaf | 34 | 20 | 6 | P peninsula bed (cam01 x 0.24-0.27) |
| 13 | willow | 9 | 46 | 9 | P hero-shore willow, ref 169 frame x 0.33-0.42 |
| 14 | willow | -2 | 47 | 7 | P hero-shore willow, ref 169 frame x 0.44-0.52 (right of the stair) |
| 15 | willow | -12 | 45 | 8 | P hero-shore willow, ref 169 frame x 0.56-0.64 |
| 16 | cypress_column | -47 | -39 | 22 | A2 tall column right of the rotunda (user image x~1020) |
| 17 | cypress | -92 | -3 | 20 | A2 at the wing's first box |
| 18 | eucalyptus | -90 | 5 | 20 | B big eucalyptus on the strip (ref 141) |
| 19 | pine | -90 | 22 | 16 | B |
| 20 | willow | -100 | 37 | 9 | B willow at the water (refs 144/145) |
| 21 | eucalyptus | -106 | 20 | 30 | B big eucalyptus behind the willows (ref 171) |
| 22 | cypress | -118 | 8 | 22 | B beyond the north pylon |
| 23 | cypress_column | -112 | 40 | 24 | B tall column beyond the north pylon (ref 169 right) |
| 24 | cypress_column | 35 | 20 | 16 | C cypress column left of the rotunda (user image x~290): QA-03-10/-13 26 -> 16 m, the user image spire tops out at the colonnade cornice |
| 25 | cypress_column | 30 | 26 | 13 | C second column (user image x~330), south lobe; QA-03-13 24 -> 13 m |
| 26 | broadleaf | 31 | 26 | 8 | C small dark tree left of the rotunda (user image x~410); QA-03-13 13 -> 9 m, clear of the rotunda silhouette at cam05 |
| 27 | eucalyptus | 62 | -30 | 30 | C broad eucalyptus behind the south wing (ref 169 left) |
| 28 | pine | 62 | -46 | 18 | C QA-01-6: moved out of cam03 (was 24,-22 = 7 m in front of the camera) |
| 29 | broadleaf | 74 | -38 | 10 | C QA-01-6: moved out of cam03 (was 33,-20 = 5 m in front of the camera) |
| 30 | cypress_column | 66 | 40 | 18 | D dense cypress behind the south pylon (ref 169 far left) |
| 31 | eucalyptus | 89 | 19 | 20 | D |
| 32 | pine | 92 | 58 | 15 | D |
| 33 | willow | 78 | 50 | 9 | D willow at the south end of the lagoon |
| 34 | eucalyptus | 104 | 52 | 30 | D south pylon |
| 35 | cypress | 112 | 40 | 22 | D |
| 36 | eucalyptus | -110 | 124 | 30 | F east shore row |
| 37 | eucalyptus | -90 | 126 | 28 | F east shore row |
| 38 | eucalyptus | -70 | 122 | 32 | F east shore row |
| 39 | eucalyptus | -48 | 127 | 30 | F east shore row |
| 40 | broadleaf | 24 | 130 | 8 | F east lawn |
| 41 | eucalyptus | 34 | 126 | 28 | F east shore row |
| 42 | eucalyptus | 54 | 124 | 30 | F east shore row |
| 43 | eucalyptus | 73 | 120 | 30 | F |
| 44 | eucalyptus | 95 | 118 | 32 | F |
| 45 | eucalyptus | 126 | 127 | 23 | F |
| 46 | cypress | 168 | 114 | 22 | F |
| 47 | eucalyptus | 158 | 28 | 32 | F |
| 48 | pine | 130 | -20 | 20 | F |
| 49 | eucalyptus | 130 | -68 | 28 | F |
| 50 | cypress | 110 | 14 | 20 | F |
| 51 | eucalyptus | 125 | 74 | 30 | F |
| 52 | cypress | 155 | 94 | 24 | F |
| 53 | cypress | -130 | 110 | 24 | F NE-corner Monterey cypress (DPR, Harbor View Inn era) |
| 54 | cypress | -118 | 96 | 22 | F NE corner |
| 55 | cypress | -140 | 82 | 22 | F NE corner |
| 56 | eucalyptus | -158 | 131 | 30 | F |
| 57 | willow | -80 | 72 | 9 | G islet willow (herons, DPR) |
| 58 | broadleaf | -92 | 68 | 12 | G |
| 59 | eucalyptus | -108 | 65 | 24 | G |
| 60 | willow | -100 | 72 | 8 | G |
| 61 | broadleaf | -115 | 62 | 10 | G |
| 62 | eucalyptus | -80 | -111 | 30 | H |
| 63 | cypress | -95 | -100 | 22 | H |
| 64 | eucalyptus | -70 | -125 | 28 | H |
| 65 | pine | -105 | -118 | 20 | H |
| 66 | eucalyptus | -268 | -120 | 30 | H |
| 67 | cypress | -245 | -304 | 24 | H |
| 68 | eucalyptus | -280 | -26 | 30 | H |
| 69 | cypress | -197 | 54 | 22 | H |
| 70 | eucalyptus | -216 | 27 | 28 | H |
| 71 | cypress | -255 | 120 | 24 | H |
| 72 | eucalyptus | -259 | -79 | 30 | H |
| 73 | pine | -253 | -174 | 22 | H |
| 74 | eucalyptus | 24 | -295 | 30 | H |
| 75 | cypress | 170 | -102 | 24 | H |
| 76 | eucalyptus | 168 | 112 | 30 | H |
| 77 | eucalyptus | -88 | -308 | 30 | H |
| 78 | cypress | -30 | -290 | 24 | H |
| 79 | pine | 35 | -35 | 21 | E1 screen behind the colonnade |
| 80 | redwood | 39 | -31 | 21 | E1 screen behind the colonnade |
| 81 | redwood | 44 | -31 | 19 | E1 screen behind the colonnade |
| 82 | cypress | 47 | -25 | 19 | E1 screen behind the colonnade |
| 83 | redwood | 60 | -17 | 19 | E1 screen behind the colonnade |
| 84 | pine | 63 | -13 | 19 | E1 screen behind the colonnade |
| 85 | pine | 66 | -8 | 20 | E1 screen behind the colonnade |
| 86 | cypress | 71 | -6 | 20 | E1 screen behind the colonnade |
| 87 | redwood | 88 | 39 | 18 | E1 screen behind the colonnade |
| 88 | redwood | 112 | 41 | 20 | E1 screen behind the colonnade |
| 89 | redwood | 112 | 46 | 20 | E1 screen behind the colonnade |
| 90 | redwood | 35 | -42 | 24 | E2 screen behind the colonnade |
| 91 | eucalyptus | 40 | -40 | 22 | E2 screen behind the colonnade |
| 92 | cypress | 45 | -37 | 21 | E2 screen behind the colonnade |
| 93 | eucalyptus | 62 | -24 | 21 | E2 screen behind the colonnade |
| 94 | redwood | 67 | -21 | 21 | E2 screen behind the colonnade |
| 95 | redwood | 70 | -16 | 21 | E2 screen behind the colonnade |
| 96 | redwood | 75 | -12 | 20 | E2 screen behind the colonnade |
| 97 | redwood | 93 | 39 | 19 | E2 screen behind the colonnade |
| 98 | eucalyptus | 117 | 41 | 22 | E2 screen behind the colonnade |
| 99 | redwood | 119 | 47 | 22 | E2 screen behind the colonnade |
| 100 | redwood | 117 | 53 | 22 | E2 screen behind the colonnade |
| 101 | cypress | 96 | 33 | 20 | E3 screen behind the colonnade |
| 102 | eucalyptus | 124 | 36 | 23 | E3 screen behind the colonnade |
| 103 | eucalyptus | 126 | 42 | 24 | E3 screen behind the colonnade |
| 104 | eucalyptus | 124 | 50 | 27 | E3 screen behind the colonnade |
| 105 | cypress | -118 | 10 | 19 | E1 screen behind the colonnade |
| 106 | redwood | -118 | 5 | 19 | E1 screen behind the colonnade |
| 107 | cypress | -116 | -0 | 17 | E1 screen behind the colonnade |
| 108 | redwood | -90 | 7 | 18 | E1 screen behind the colonnade |
| 109 | redwood | -84 | -9 | 18 | E1 screen behind the colonnade |
| 110 | redwood | -80 | -12 | 17 | E1 screen behind the colonnade |
| 111 | redwood | -77 | -17 | 19 | E1 screen behind the colonnade |
| 112 | pine | -61 | -30 | 19 | E1 screen behind the colonnade |
| 113 | redwood | -57 | -33 | 19 | E1 screen behind the colonnade |
| 114 | cypress | -52 | -35 | 21 | E1 screen behind the colonnade |
| 115 | pine | -31 | -42 | 21 | E1 screen behind the colonnade |
| 116 | pine | -26 | -43 | 18 | E1 screen behind the colonnade |
| 117 | cypress | -21 | -43 | 19 | E1 screen behind the colonnade |
| 118 | redwood | -125 | 7 | 21 | E2 screen behind the colonnade |
| 119 | redwood | -125 | 1 | 23 | E2 screen behind the colonnade |
| 120 | cypress | -122 | -4 | 21 | E2 screen behind the colonnade |
| 121 | redwood | -97 | 1 | 20 | E2 screen behind the colonnade |
| 122 | redwood | -98 | -6 | 20 | E2 screen behind the colonnade |
| 123 | redwood | -85 | -20 | 21 | E2 screen behind the colonnade |
| 124 | eucalyptus | -79 | -23 | 21 | E2 screen behind the colonnade |
| 125 | redwood | -76 | -28 | 21 | E2 screen behind the colonnade |
| 126 | cypress | -71 | -32 | 21 | E2 screen behind the colonnade |
| 127 | redwood | -54 | -42 | 22 | E2 screen behind the colonnade |
| 128 | redwood | -48 | -44 | 22 | E2 screen behind the colonnade |
| 129 | redwood | -41 | -44 | 21 | E2 screen behind the colonnade |
| 130 | eucalyptus | -37 | -48 | 22 | E2 screen behind the colonnade |
| 131 | eucalyptus | -21 | -51 | 22 | E2 screen behind the colonnade |
| 132 | redwood | -132 | 6 | 26 | E3 screen behind the colonnade |
| 133 | cypress | -132 | -1 | 23 | E3 screen behind the colonnade |
| 134 | cypress | -127 | -7 | 23 | E3 screen behind the colonnade |
| 135 | redwood | -103 | -11 | 21 | E3 screen behind the colonnade |
<!-- PLAN_TABLE_END -->

## Polish round 1 (QA round 02 defects) — 2026-09-07

### QA-02-7 — the wings were buried in trees AND standing in tree shadow
Two separate causes, and the second one was invisible until it was measured.

1. **The screen was a wall.** Round 01's `redwood_screen` planted three continuous rows 4.5 / 11 / 19 m outside the
   wing at 26–36 m tall — 5–15 m over a 19–21 m entablature, with no gaps. Now: rows at **6 / 12.5 / 20 m**, crowns
   **18.5–27 m**, and each row is **clumped** (a 15–38 m run of trees, then a 7–13 m gap) so bays open onto sky.
   Pushing the rows further than ~20 m walks them into the exhibition-hall footprint, which deletes the two back
   rows entirely — that is the limit, not a preference.
2. **The low sun.** At az 118.5 / el 7.4 a 30 m crown throws a **230 m** shadow to the north-west. Measured with
   `env_sightlines.py --shadow`, **92.5 % of the south wing and 70 % of the north wing entablature band was in tree
   shadow** — the wings could not have been lit whatever the exposure. The same rays cross the lagoon: **33 % of the
   water the hero camera sees** was shadowed by the east-shore eucalyptus row (Y 118–131, 28–32 m), which is a large
   part of QA-02-6's dark cyan near field.

`env_trees.shadow_relief()` now runs after the plan is assembled. It samples the lagoon-facing colonnade faces at
z = 12 / 17 m plus a grid of the hero camera's water, ray-casts each sample at the sun against every crown
(ellipsoid, 0.35 H–1.02 H), and worst-caster-first lowers the offending crown, pushes it 12 m down-sun, or drops it.
Height floors are by role: generated screen trees 55 % and droppable, east-shore / backdrop trees behind the hero
camera 45 % and droppable, the peninsula "A" cluster (the dark mass right of the rotunda in ref 169) 80 % and never
dropped, everything else 72 %.

Result: **north wing 82.5 → 12.5 %, south wing 70.0 → 20.0 %, hero water 33.3 → 6.1 %** in shadow, for 22 crowns
lowered (80 m of height in total), 14 moved and 1 dropped. Sky through the bays from cam 01
(`env_preview.py -- --skytest`) went **1.7 → 22.8 %** (north) and **9.5 → 30.3 %** (south); ref 169 is 15–20 %, so
the north wing is on target and the south is a little open.

The geometry lives in `env_lib` (`sun_vector`, `crown_ellipsoid`, `ray_hits_ellipsoid`, `wing_samples`,
`shadowed_fraction`) so the planner and the checker cannot drift apart. Re-check any time with
`blender -b --python scripts/env_sightlines.py -- --shadow --only-shadow`.

**Naming warning.** QA round 02 called the x 60–560 band of the hero frame "north". North is −X, and the hero camera
at (−14.1, 100) looking at the origin puts −X on the **right** of the frame, so QA's "north band" is in fact the
**south** (roof306) colonnade and its "south band" is the north (roof310) one. `scripts/env_measure.py` calls them
`left_wing` / `right_wing` to stop the swap propagating.

### QA-02-6 — lagoon flanks and the cyan near field (mesh side; MAT_water_lagoon is the materials agent's)
* The shadow relief above lit the water QA measured (6.1 % shadowed, was 33.3 %).
* **Bed profile.** The old bed dropped to its full 1.5 m within 7.5 m of the shore, so the water the hero sees at
  6–12 m already had the longest possible absorption path through the murk — it could only read near-black cyan.
  The bed is now a shelf: 0.25 m at the edge, 0.85 m at 14 m out, 1.5 m by 30 m (refs 022, 169 show bed pebbles and
  rip-rap several metres out).

### QA-02-13 / QA-02-18 — the shrub band
* Every shrub inside r = 54 m of the rotunda is clamped to **1.2 m** tall, so the podium and its Greek-key band are
  no longer hidden from cams 02 / 05.
* `shadow_relief` also pushes any tree whose crown comes within **6 m** of the podium (r = 31 m) radially out.
* Variety: **9 mound seeds** instead of 4 across three material families (`MAT_shrub` / `MAT_shrub_light` /
  `MAT_shrub_dry`), 3 mahonia sizes, a 2.2:1 instance size spread, no two neighbours drawn from the same source
  mesh, and dry reeds / twigs seeded into the peninsula belt (they used to start past r = 50 m) — **30 % of the band
  is now a warm dry material**, against QA's ">= 20 %" test.

### QA-02-15 — backdrop houses
Round 02 joined every OSM footprint into one flat-topped prism with one material ("plain grey boxes"). Each
building is now its own object — which gives the library material's per-object random a per-building hue and value —
and carries a pitched roof in `MAT_backdrop_roof`: a gable along the footprint's oriented bounding box, hipped on
plans squarer than 1.8:1, pitch 18–29 deg.

### Performance
The round-02 master ran 33–55 s per Eevee camera with LOD1 at 15.2 M tris; 1761 LOD-less shrubs contributed 3.3 M
of that **at every LOD and in every render**. A 0.8 m bush is 8–15 px from the hero camera, so its ~1300 leaf cards
buy nothing. Leaf *coverage* (n_cards x card^2) is what makes the silhouette read, so `SHRUB_LOD` keeps the coverage
and multiplies the card size instead — cards k x wider and k^2 x fewer:

| | cards | tris (1423 instances) |
|---|---|---|
| LOD0 | full | 2.31 M |
| LOD1 | 2.2 x wider | 0.53 M |
| LOD2 | 4.5 x wider, coarser core | 0.14 M |

Each placement is now three objects with the tree convention (`hide_render` on all but LOD0, `hide_viewport` on all
but LOD1), and a shrub farther than `SHRUB_FAR` = 80 m from every QA camera renders its LOD1 mesh even at LOD0
(LOD2 past 160 m). Instance count also came down 1761 -> 1423 as part of the QA-02-18 variety work.

### Verification in the full master (2026-09-07, polish round 1)

Built with `scripts/lead_build.sh` in this worktree (master 8458 -> 9030 objects, viewport LOD1 **11.62 M tris**,
down from round 02's 15.18 M). Measured with `scripts/env_measure.py`, whose boxes reproduce QA round 02's numbers
exactly against the aligned ref-169 panel of `renders/qa_comparisons/round02_cam01_aligned_vs_ref169.png`.

| box (hero frame) | round 02 | ENV round 3 | at +0.9 EV | ref 169 | test |
|---|---|---|---|---|---|
| left_wing (QA's "north", = south colonnade) | 66.0 (0.48) | 82.6 (0.60) | 102.3 (**0.75**) | 137.2 | within 25 % |
| right_wing (QA's "south", = north colonnade) | 88.3 (0.63) | 99.1 (0.70) | 115.4 (**0.82**) | 141.0 | within 25 % |
| water_flank | 35.9 (0.28) | 114.8 (**0.89**) | 145.3 (1.12) | 129.6 | within 30 % |
| water_near saturation | 0.533 | 0.531 | **0.457** | 0.106 | <= 0.45 |

The +0.9 EV column is `scripts/qa_exposure_sweep.py` on the same master (Eevee, 1920x1080) and stands in for
lighting's pending QA-02-4 exposure fix: both wings land inside the 25 % band once it arrives, and the near field's
saturation lands 0.007 over the line — the rest of that one is `MAT_water_lagoon`'s hue, not the mesh.

Composite for the lead: **`renders/qa_comparisons/env_r3_sheet.png`** (round-02 hero | ENV round 3 hero | aligned
ref 169 with the measurement boxes drawn, plus cams 02 / 03 / 06). Frames:
`renders/previews/qa/roundenv3_01_lagoon_hero_cycles.png` (Cycles 64 spp, 314 s),
`roundenv3_0{1,2,3}_*.png` (Eevee), `roundenv3b_0{1,6}_*.png` (Eevee, after the backdrop-roof rebuild).

**Timings are not trustworthy on this machine right now.** Three other agents were rendering throughout: the same
cam-01 Eevee frame at 1280x720 took 124 s, 209 s and 66 s in one three-frame run, and 63 s / 50 s at 1920x1080
when only one other Blender was up. The reliable number is the triangle count. Note also that ENV's *render* path
is LOD0, so the shrub ladder helps the viewport far more than the render: ENV LOD0 is 14.53 M (shrubs 3.3 -> 2.31 M
via the SHRUB_FAR rule and the lower instance count), and trees are still ~85 % of it. The next cheap render-time
lever is still `env_trees.FAR_RADIUS` (130 m -> 105 m, roughly another 2 M), untouched this round because it needs
its own visual check.

Re-checked on the saved `assets/environment.blend` (positions are snapped onto land after the relief pass, so these
are the numbers that ship, slightly off the planner's):
`blender -b --python scripts/env_sightlines.py -- --shadow --only-shadow` ->
**north wing readable band (z >= 12 m) 78.8 % lit, south wing 77.5 % lit** (round 02: ~31 % and ~4 %). The south
wing's z = 6 m shaft band is still 95 % shaded, which matches ref 169 - the low shafts there are in shade in the
photograph too.

LOD1 fidelity: the widest LOD1 leaf card is 0.105 x 2.2 x 1.45 = 33 cm, which at the nearest shore (60 m, 20 mm
lens, 1920 px) subtends ~6 px - at QA-01-7's limit, and only ever in the viewport.

## Polish round 4 (QA round 03 defects) — 2026-09-08

Composite: **`renders/qa_comparisons/env_r4_sheet.png`** (before | after | reference for QA-03-11 / -10 / -13 with
the numbers on each row). Previews: `renders/previews/environment/20260907_2358*_r4g.png` (cams 01 at 1920x1080,
03 / 05 / 06 at 1280x720; Eevee, ENV + linked ARCH, placeholder sun az 118.5 / el 7.4).

**Read the luminance numbers with care.** An ENV preview is lit by `env_preview`'s placeholder sun, not by the
shipped rig, so it cannot be compared with a master render's absolute luminance. Everything below that ENV
actually controls is therefore measured as *coverage* — what fraction of a QA box resolves to foliage rather than
architecture — by ray-casting ENV + ARCH (`env_sightlines.py -- --coverage`, boxes in `COVERAGE_BOXES`).

### QA-03-11 — cam 06 past 150 m ("a flat olive plane with five grey box houses; a game skybox")

New module **`scripts/env_city.py`**. `reference/plans/_osm.json` has 294 building footprints with heights and
street names but **no highway ways at all**, so the street grid is derived from the buildings:

| what | measurement | value used |
|---|---|---|
| grid orientation | total footprint-edge length binned by angle mod 90 deg: 9.6 km at 9 deg, 4.4 km at 8 deg, next peak 1.3 km | `GRID_ANG` 8.5 deg |
| N-S street pitch | line fits through the Lyon / Baker / Broderick centroid groups: 89 and 136 m apart across | `PITCH_V` 137 m, phase 145 (Baker) |
| E-W street pitch | Marina Blvd / Jefferson / Beach / North Point / Bay / Francisco: 83 / 95 / 103 / 103 / 84 m | `PITCH_U` 95 m, phase -119 (Jefferson) |
| where buildings exist | footprints binned by azimuth (0 = +X south, 90 = +Y east): 24-29 per 15 deg between 15 and 165 deg out to r 350; 0-6 per bin between 250 and 355 (Presidio: Thornburg / Edie / Birmingham / Gorgas / O'Reilly / Letterman / Mason); nothing between 170 and 250 (Marina Green, Crissy Field, the bay) | `RESIDENTIAL_AZ` / `PRESIDIO_AZ` / `OPEN_AZ` |

cam 06 puts its horizon crop (rows 0-220) on the ground at r 115-413 m, azimuth 275-357 deg plus a sliver at
0-15 — i.e. mostly the **Presidio**, not the Marina. That is why the Presidio side got as much work as the grid.
What is built: a city ground mesh (2648 quads, r 178-720 m) carrying block yards in lawn / dry grass / soil,
11 m asphalt carriageways with 3.6 m gravel sidewalks on every grid street, Palace Drive as a loop around the
grounds, five Presidio boulevards (Richardson / Lombard / Lincoln / Presidio Blvd / the Main Post approach), and
the theatre car park west of the hall (the shadowed band 125-200 m down-sun of the palace, which was the bare
"olive plane" of the middle distance); 913 synthesised Marina lots in 252 run objects (7.5 m x 15 m lots, four to
an object so the library material's per-object random gives row-house colour runs, 22 % flat-roofed apartment
blocks, hip and gable, tile and membrane roofs) outside the OSM extract at r 320-620 m; 97 Presidio buildings in
six clusters (Lombard Gate, Letterman, two Main Post ranks, the cavalry stables, the Crissy hangars), one object
each; and 1822 far canopy crowns in 4 joined objects.

The canopy took three passes to get right and the log is worth keeping: a single smooth ellipsoid per crown read
as a **bright green boulder** at 250-400 m (nothing broke the highlight, nothing self-shadowed), and a subdiv-1
icosphere read as a faceted crystal. The shipped crown is a cluster of 3-5 offset lobes (`_canopy_mesh`), which
lets the library material's 9 m Voronoi clumps land *inside* one crown. Density is also easy to overdo: the first
tuning buried every backdrop building.

Measured on the 1280x720 aerial, round 03 master panel vs the ENV round-4 preview:

| test (QA-03-11) | round 03 | round 4 | target |
|---|---|---|---|
| horizon crop luminance std-dev | 15.5 | **30.5** | structure, not a flat plane |
| rotunda / far-shore contrast | 1.15 : 1 | **1.45 : 1** | >= 1.5 : 1 (the rest is lighting's mist) |
| building volumes resolved in the crop (ray-cast, 3 px grid) | ~5 by QA's count | **37 objects** (25 wall + 12 roof; the fill runs carry 4 lots each, so >= 60 volumes) | >= 30 |
| distinct materials in the crop | 1-2 | **13** | >= 3 colours |
| ground materials in the crop | lawn only | lawn 2821 / soil 996 / dry 720 / asphalt 488 / gravel 83 samples | paths readable |

### QA-03-10 / QA-03-13 — frame-band relief

Both defects are stated in *frame* coordinates, so they are now enforced in frame coordinates by
`env_trees.frame_band_relief`, which runs **after** `shadow_relief` so the sun pass cannot push a crown back in.
A tree only offends if it stands between the camera and the subject; for the hero that is decided by an exact
**segment-crossing test against the colonnade polygons** (`_crosses`), not by a radius about `ARC_CENTRE` — the
first attempt used radius 93 m and mis-sorted the whole first screen row, because `roof306` runs r 68.7-105.5 m
about that centre (the end pylon sticks out) and it threw three screen trees *in front of* the wing.

* `_qa_01_` band x 0.031-0.205, y 0.40-0.60. It stops at 0.205, not at QA's 0.292, because ref 169 and the user
  image both have a conifer group at x 0.19-0.29 — that is composition, not a defect.
* `_qa_05_` band x 0.235-0.780, y 0.02-0.66 (the rotunda body). Not down to 0.86: the 7-9 m willows and
  broadleaves of the peninsula bed top out at y 0.67-0.69 and belong in the picture. The first version guarded to
  0.86 and threw them 42-48 m away.

Three trees moved: the eucalyptus at (59.0, 14.6) 30 m out to (88.7, 18.8) — behind the wing — and the two "C"
group trees 2 m each. The user-image cypress spires also went **26 / 24 m -> 16 / 13 m** and the small broadleaf
13 -> 9 m: in the user image those spires top out at the colonnade cornice, they are not 26 m columns.

| box | round 03 | round 4 | test |
|---|---|---|---|
| cam 01 left (south) wing, foliage coverage | 43.4 % | **40.0 %** | as low as ref 169's own conifer group allows |
| cam 01 left wing, architecture coverage | 56.6 % | **60.0 %** | — |
| cam 05 rotunda silhouette, foliage | — | **5.1 %** (73.7 % architecture) | no crown inside the silhouette |
| cam 05 podium / Greek-key band box | — | **81.4 % architecture visible** | >= 60 % of the rotunda width |

The remaining foliage in the hero band is the E1/E2 redwood screen seen *through the colonnade bays* — ref 169 has
the same thing (dark fraction below lum 60: render 0.25, ref 0.28). The band's luminance ratio is set by the light
rig: **the lead should re-measure `env_measure.py` left_wing on the merged master**, not on an ENV preview.

### QA-03-14 — the shore shrub row

The row was not evenly spaced by accident: round 03 clamped every shrub inside r = 54 m to *exactly* `ROSTRA_H`
= 1.2 m, so the QA-02-13 fix was what flattened the silhouette. The cap is now drawn per instance from
**`ROSTRA_H_RANGE` (0.42-1.20 m)** and applied to the source mesh's real z extent across all three LODs times the
instancing z jitter — round 03's "1.2 m" shrubs actually measured **1.87 m** in the file, because the mound meshes
overshoot their nominal height and the LOD1/LOD2 meshes are taller still (wider cards). A ~11 m noise gate also
opens and closes the belt so the gaps are metres long rather than Poisson noise, and the base scale range went
(0.72, 1.55) -> (0.58, 1.80) x (0.85, 1.18).

Measured with `env_sightlines.py -- --shrubs` over the world box (-30, 20) - (30, 60), the ground under QA's crop
(700 640 1200 720):

| test (QA-03-14 / QA-03-13) | round 03 | round 4 | target |
|---|---|---|---|
| size spread (p90 / p10 height) | ~1.5 : 1 | **2.51 : 1** | >= 2 : 1 |
| nearest-neighbour spacing sd / mean | — | **62 %** | >= 40 % |
| tallest shrub inside r = 54 m | 1.87 m | **1.13 m** | <= 1.2 m |
| warm dry fraction of the belt | 30 % | **34 %** | >= 20 % |

### QA-03-9 (environment share) — the cam 03 ground and the near foliage

* The colonnade walk now has bands instead of one gravel field: gravel inside the colonnade footprint + 2 m, a
  **soil planting bed from +2 to +5.5 m** (where the foundation shrubs stand), a **1.5 m soil verge along every
  path**, then lawn. All four are CDT constraints, so the edges are clean rather than sampled.
* No shrub is placed within **17 m of cam 03**: a 0.9 m bush 3 m from an 18 mm lens in wing shade is nothing but
  black leaf cards, which is what QA saw.
* The foundation planting along both colonnade fronts switched from `MAT_shrub` to the pale / dry families
  (`MAT_shrub_light`, `MAT_shrub_dry`, `MAT_reeds` twigs) — everything there is in the wing's own shade.
* Crop (0 150 420 720) of cam 03: pixels below luminance 12 went 29.8 % -> 0.1 %, luminance std-dev 14.7 -> 21.4.
  Both numbers move with the light rig as well as with ENV, so treat them as directional. The flutes, the column
  base mouldings and the shaft luminance in that crop are architecture / materials, not ENV.

### Carried — the hall aperture through the hero arch

The 6 m entrance opening between the pavilion piers now has a full-height **backing slab** (9.0 x 11.4 m, wider and
taller than the opening) behind the door surround, plus jambs, a head and a threshold so the doorway still reads as
a recess. Verified in `20260907_235834_01_lagoon_hero_r4g.png`: through the rotunda's west arch the aperture shows
the green door in a lit reveal, no hole.

### Performance

| | round 3 | round 4 |
|---|---|---|
| ENV LOD0 (render path) | 14.53 M tris | **13.98 M** |
| ENV LOD1 (viewport) | 4.84 M tris | **4.80 M** |
| ENV LOD2 | — | 0.65 M |
| objects in ENV | ~4 400 | **5 101** |

`env_city` costs 703 objects and ~0.16 M tris at every LOD (city ground 2648 quads, 504 fill house objects,
194 Presidio objects, 4 canopy objects). It has no LOD ladder of its own: everything in it is already LOD2-class,
and the whole far field is 1.2 % of ENV's triangles. The canopy does split by distance — 4-lobe crowns inside
430 m, 2-lobe beyond.

## Polish round 5 (code review + QA-03-10 measurement) — 2026-09-08

Composite: **`renders/qa_comparisons/env_r5_sheet.png`** — the QA-03-10 wing band and the QA-03-13 cam-05
silhouette, before | after | ref 169, with the numbers on each panel. Renders:
`renders/previews/environment/r5_master_hero.png` (the merged r4b master = before),
`r5_env5b_hero.png` (the same build with ENV round 5), `r5_cam05_before/after.png` — all Cycles from a
built master, not from an ENV preview, because QA-03-10 is a luminance test (`scripts/env_r5_hero.py`).

### The four code-review findings

| finding | what was wrong | fix |
|---|---|---|
| `shift_y` aspect | `env_trees._frame_box`, `env_sightlines.project` and `env_sightlines.coverage` applied cam 01's `shift_y` 0.06 as 0.06 of the frame **height**. Blender's shift is in units of the larger sensor dimension, so it is 0.06 x 16/9 = **0.107 of the height, 115 px of 1080** — every hero frame band sat ~50 px too low | aspect factor `half_w/half_h` in all three; `coverage(shift_aspect=False)` and `env_sightlines -- --coverage --both` reproduce the round-4 boxes for comparison |
| `env_city.azimuth` | 0 deg = +X = south, increasing counter-clockwise: the opposite hand to the project's compass-clockwise-from-north (`env_lib.sun_vector`, `env_build`) | renamed **`city_az`**, handedness and the conversion (`compass = (270 - city_az) mod 360`) in the docstring. Behaviour unchanged |
| `clear()` corners | only quad/segment centroids were tested, on 95 x 137 m blocks, 3 deg x 140 m wedges and 18.2 x 14 m road ribbons | `clear(x, y, *corners)`; blocks pass their four corners, wedges their four, road ribbons their four outer corners. Nothing can cross the lagoon / hall / colonnade keep-out if the pitch, phase or ring radii are retuned |
| `build_all` | built the city only `if lagoon_field is not None`, so a missing argument silently dropped the whole Marina / Presidio far field | `lagoon_field` is a required positional argument |

**Do the round-4 numbers still hold with the corrected boxes?** Yes, with one correction. Re-measured on the
round-4 `assets/environment.blend` (so only the box changed): cam 01 left wing foliage **40.0 % -> 39.5 %**,
architecture 60.0 % -> 53.5 %, and the corrected box now also sees **7.0 % sky** — the round-4 box was low
enough to miss the bay openings, which is why it read as almost pure wing. cam 05 has `shift_y = 0`, so its
box did not move at all; its silhouette foliage reads 6.5 % rather than round 4's 5.1 % purely because
`assets/architecture.blend` changed under it (the 786966a socket re-frame).

`FRAME_BANDS` gained **`x1_exit`**: QA-03-10 measures x 0.031-0.292 while the offence band stops at 0.205
(round 4's call, kept — ref 169 and the user image both have a conifer group at x 0.19-0.29). Round 4 could
therefore push an offender 4 m and park it *inside the box being measured*; a moved tree now has to clear 0.292.

`FRAME_BANDS` also gained **`pin`** (round-5 review, lead decision). A tree whose PLAN group letter is listed
there stands where the reference puts it and is **never relocated and never dropped**: the relief may only
lower its crown, by at most 25 % (the allowance `shadow_relief` already gives a hand-placed tree), and if that
will not clear the band the tree stays and is reported as `kept (hand-placed)`. Both bands pin **P** (the
peninsula bed) and **C** (the user-image group, including the two cypress spires).

This was the review's HIGH finding, and the first version of this section got the diagnosis wrong. Correcting
the record: the corrected `shift_y` moves every hero projection ~50 px down the frame, which pushed three
hand-placed trees — #11 broadleaf (26, 32), #12 willow (18, 40), #26 broadleaf (31, 26) — into the **cam-05**
silhouette band (not the cam-01 band, and not through `x1_exit`, which changes no position on this plan), and
the relief swept them 36-48 m across the site. That is the outcome this same section says was rejected. With
`pin` they stay at their reference coordinates and the bands are cleared by thinning the procedural screen
instead. `frame-band relief` now reports **moved 1, shortened 0, dropped 0, kept (hand-placed) 4** — the only
move left is the round-4 one, the "D" eucalyptus (59.0, 14.6) -> (88.7, 18.8) behind the south wing.

### QA-03-10 — the band, measured on a real master

`scripts/env_measure.py` now carries **both** reference panels QA quotes: the round-02 aligned panel and the
raw ref-169 file with QA's mapped box `269 465 651 557` (which reproduces QA's 109.5 exactly). Note the two
panels disagree by 25 % *with each other*, so the acceptance window is lum 102.9-136.9.

| hero band 60 480 560 600 | lum | vs raw 109.5 | vs aligned 137.2 |
|---|---|---|---|
| QA round 03 master | 87.0 | 0.79 | 0.63 |
| merged r4b master (LIGHT r09, ENV r4) | 100.7 | 0.92 | 0.73 — **fails** |
| ENV r5 on the same build | **103.8** | **0.95** | **0.76** — both inside 25 % |

What moved. `env_sightlines -- --coverage --who` and `-- --boxmap` (new) price each instance: a per-pixel
object map of the box, multiplied by the real render, gives the luminance each crown costs. That said the
two user-image cypress spires and the peninsula bed were only worth 2.5 lum between them, and that the
**band's ceiling with every crown removed was 110.5** (0.81 aligned) — so the band is set by the lit stone,
not by ENV. What was genuinely wrong was the screen: the box carried **36.1 % of pixels below luminance 60
against ref 169's own 27.8 %**, 25.0 of those 36.1 points foliage, and only 13.6 % sky-ish pixels through
the bays against the photo's 16.5 %. So `redwood_screen`'s two front rows run shorter and gap wider
(E1 run 15-27 -> 11-20 m, gap 7-13 -> 11-19 m and crowns 18.5-23 -> **17-21 m**; E2 run 18-33 -> 14-26 m,
gap 7-12 -> 10-16 m). Two thinning knobs were tried and rejected on measurement: widening the gaps further is
**not monotone** — it re-rolls the run/gap RNG and one step put a clump straight into the hero band (foliage
30.9 -> 37.3 %) — and thinning the back row E3 changes the band by exactly nothing, because its crowns sit
behind E1/E2 and are never the first hit. Crown *height* is the one knob that draws the same number of random
numbers, so it thins the band without moving a single crown. Sky through the bays ends at **17.0 %** against
the photo's 16.5 % and QA-02-7's 15-20 % window. Nothing
hand-placed moved (see `pin` above): the user-image spires, the peninsula bed and the "A" mass right of the
rotunda all stay at their reference coordinates and at their reference heights.

| cam 01 left-wing box (ray-cast) | ENV r4 | ENV r5 |
|---|---|---|
| foliage | 39.5 % | **30.5 %** |
| architecture | 53.5 % | 57.8 % |
| sky through the bays (ray-cast) | 7.0 % | **11.6 %** |
| sky-ish pixels in the render | 13.6 % | **17.0 %** (photo 16.5 %) |
| trees in the plan | 143 | 136 |

A widened offence band (x1 0.292) was built and rejected: it passes too, at 103-104 lum, but it costs the
peninsula bed and one user-image spire (2 trees dropped, 6 moved 36-50 m). Composition beats 1 lum.

cam 05's silhouette ends at **6.6 % foliage / 60.4 % architecture** — the same as ENV round 4 measured against
today's `architecture.blend` (6.5 / 60.5). Pinning the peninsula bed gives back the 2.5 points the sweep had
bought; that is the intended trade.

**Residual, for lighting.** The band is still darker in *contrast* than the photo — 35.4 % of pixels below
lum 60 against 27.8 % (35.5 % in the shipped build). The split measured at the same foliage level was
**19.4 points foliage** (was 25.0, and below ref 169's own total) and **16.0 points architecture** (was 11.1): thinning the screen exposed more of the wing's own shaded
stone, which reads mean lum 99.7 in that box against the photo's lit half at 163.4. That remainder is the
light rig and the stone, not the planting.

### MAT r5 pick-up

`assets/materials.blend` now supplies every material ENV names: `env_build` logs **zero** "material not in
library" warnings (round 4: 2). `MAT_backdrop_asphalt` and `MAT_backdrop_roof_tile` needed no code change —
`env_city` already asked for those exact names through `common.load_material` and still writes its
`instance_seed` property, so the carriageways, the theatre car park and the Presidio tile roofs are on the
real library materials. `MAT_leaf_pine` also landed, so pines and redwoods (`mat_or`) are now on the darker
blue-green needle material instead of falling back to cypress — which is why the *remaining* screen foliage
reads darker (mean lum 82.4 -> 78.0) even after the thinning.

### Performance

| | round 4 | round 5 |
|---|---|---|
| ENV LOD0 | 13.98 M tris | **13.40 M** |
| ENV LOD1 (viewport, cap 4.84 M) | 4.80 M | **4.60 M** |
| ENV LOD2 | 0.65 M | 0.64 M |
| objects in ENV | 5 101 | 5 080 |


## Previews and comparisons

Fix round (2026-09-07): `renders/previews/environment/*_fix2_*.png` and `fix3_cam01_1920.png` / `fix3_cam05_1920.png`
(Eevee, QA cams, ENV + linked ARCH, placeholder sun az 118.5 / el 7.4). **The composite for the lead is
`renders/qa_comparisons/env_fix_round_sheet.png`** — cam 01 (1920 px) next to ref 169, and cams 02 / 03 / 05 / 06 next
to refs 062 / 128 / 063 / 105. `env_fix3_waterline.png` is the QA-01-2 waterline crop (render band / ref 169 same band /
cam 05 shore from 60 m); `env_fix2_sheet.png` and `env_fix2_waterline.png` are the same views before the shore was
densified, kept for the before/after. Foliage line-ups: `*_tree_lineup_LOD{0,1,2}.png` and `*_tree_lineup_hero120m.png`.
Sky-through-the-bays test frames: `skytest_north.png`, `skytest_south.png` (transparent film; black = sky).
The Phase 2 set is still there as `*_final*` / `env_final_*`; earlier rounds as `env_trees1..5_*`.

## Sky / sun convention (verified for the preview)

`ShaderNodeTexSky` (MULTIPLE_SCATTERING): `sun_rotation = 0` puts the sun toward world +Y (east, az 90°), +90° toward
+X (south). So `sun_rotation = radians(az − 90)` for compass azimuth az in our world. The preview uses az 118.5°,
el 7.4°, sun 4 W/m² at 3600 K, sky strength 0.35, exposure −0.8.

## Open issues / requests

- ~~**Materials agent (round 4)**: `MAT_backdrop_asphalt` / `MAT_backdrop_roof_tile` missing~~ — **closed by MAT r5
  (round 5)**. Both resolve from the library now; `env_build` logs zero "material not in library" warnings.
- **Materials agent (round 4, believed closed — needs a cam 06 re-check)**: MAT r5 darkened and cooled
  `MAT_backdrop_forest` (albedo -55 %, B/G 0.43 -> 0.63). ENV has not re-rendered cam 06 since; the round-4
  complaint was: `MAT_backdrop_forest` reads noticeably **bright and yellow-green in direct sun**
  on the new mid-distance canopy blobs at cam 06 (250-450 m). It was tuned for the 700 m+ ridge, where it is
  right. A darker, bluer lit response (or a stronger AO / clump darkening) would help the whole Presidio side.
- **Lighting (QA-03-11 share)**: the rotunda / far-shore contrast is now **1.45 : 1** from ENV geometry alone
  (was 1.15 : 1); the last 0.05 is mist density, measured on `env_cam06_audit.py` boxes DOME and FAR_SHORE.
- ~~**Lead (QA-03-10)**: re-measure the band on the merged master~~ — **done in round 5**: 104.0 lum,
  0.95 of the raw ref-169 box and 0.76 of the aligned panel, both inside 25 %. Use
  `blender -b --python scripts/env_r5_hero.py` + `python3 scripts/env_measure.py <hero>` to re-check after any
  lighting change. **Still open for lighting**: the band's dark fraction is 35.4 % against the photo's 27.8 %,
  and 16.0 of those points are now the wing's own shaded stone (mean lum 99.7 in that box vs the photo's lit
  half at 163.4), only 19.4 foliage. ENV's ceiling with every crown removed is 110.5 (0.81 aligned).

- ~~**Materials agent**: no separate pine/redwood needle material~~ — **closed by MAT r5**: `MAT_leaf_pine` is in
  the library and `env_trees` (`mat_or`) maps pine and redwood to it. Original request kept for the record:
  the library has no separate pine/redwood needle material.
  `docs/materials_notes.md` says `assets/textures/foliage/needles_pine.png` is generated but unused; QA-01-7 asks for
  "conifer foliage darker (map pines/redwoods to the pine needle material, not cypress)". ENV maps pine, redwood,
  cypress and columnar cypress all to `MAT_leaf_cypress` because creating a local copy would violate the
  library-by-name rule. **Please add `MAT_leaf_pine`** (darker, blue-green, translucency ~0.2) and ENV will remap in
  one line (`env_trees.SPECIES[...]["leaf"]`). Mitigation meanwhile: pine and redwood carry 36–37 k cards per LOD0
  tree, ~55 % more than cypress, so the crowns self-shadow darker.
- ~~**Materials agent**: five ENV placeholders~~ — **closed by MAT r5** (`env_build` warns about none of them any
  more). Original request: `MAT_shrub_light`, `MAT_shrub_dry`, `MAT_backdrop_roof`, `MAT_backdrop_skylight` and
  `MAT_backdrop_door_green` were not in the library, so those five were ENV placeholders (`env_lib.mat` recoloured
  them). The shore now uses only library materials — `MAT_shrub` for the mounds and `MAT_reeds` for agapanthus, dry
  reeds and twig shrubs — but a second, lighter/greyer shrub material would let the mahonia read differently from the
  pittosporum. The hall's roof, glazing and green door are the other three.
- **Lead / QA (cam 02)**: see "Sight lines" above — the reference sheet's dark cluster and the new cam 02 at (−45, 52)
  cannot both be satisfied on the available land. The cluster now sits in cam 02's right-edge band at 29–52 m.
- **Lead / build_master**: ENV's materials are appended one at a time by `common.load_material`, which duplicates the
  library's shared node groups; `env_build` now calls `mat_lib.dedupe_node_groups()` before saving, but if the lead
  re-appends ENV into master it should do the same (the materials notes give the one-call recipe).
- **Performance**: LOD0 is 13.4 M tris (LOD1 4.60 M as of round 5). Trees are ~97 % of it. If the Cycles hero gets too slow, the
  cheapest lever is `env_trees.FAR_RADIUS` (130 m: no QA camera within this distance -> the tree uses the lighter
  mesh); 100 m saves roughly another 2 M.
- The OSM extract has no paths/roads (`_osm.json` contains only buildings and the two water polygons), so QA-01-19's
  "paths from OSM" is served by the satellite-derived path ribbons already baked into the terrain material zones.
- Wind-sculpting of the cypresses (leaning away from the westerlies) is only a 0–4.5° per-instance tilt; no
  per-instance weathering of bark or foliage beyond the library materials' own object-random.
- Diagnostic camera `CAM_env_hall_from_colonnade` mostly sees the colonnade; a proper hall view needs a camera outside
  the wings.
