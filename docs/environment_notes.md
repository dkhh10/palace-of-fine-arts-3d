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
| 00 | pine | -44 | 4 | 17 | A cluster core; QA-01-6: pulled west so cam02's right 40% is clear (42 m, x 0.82-1.10) |
| 01 | redwood | -40 | -2 | 16 | A young redwood at the north arch (ref 070) |
| 02 | cypress | -44 | -1 | 20 | A dark mass right of the dome |
| 03 | pine | -46 | 8 | 18 | A cluster, second crown |
| 04 | willow | -40 | 16 | 10 | A pale weeping willow at the water in front of the cluster (ref 169) |
| 05 | broadleaf | -49 | 13 | 11 | A shore broadleaf at cam02's right edge |
| 06 | cypress | -48 | 0 | 23 | A cluster depth (QA-01-6: mass kept dense after the move west) |
| 07 | pine | -52 | 6 | 20 | A cluster depth |
| 08 | broadleaf | -30 | 30 | 8 | P peninsula bed, right of the rotunda (cam01 x 0.71-0.78) |
| 09 | willow | -22 | 38 | 7 | P low willow at the water in front of the podium (cam01 x 0.64-0.71) |
| 10 | broadleaf | -36 | 20 | 7 | P peninsula bed (cam01 x 0.75-0.80) |
| 11 | broadleaf | 26 | 32 | 7 | P peninsula bed, left of the rotunda (cam01 x 0.21-0.26) |
| 12 | willow | 18 | 40 | 7 | P low willow at the water, left (cam01 x 0.24-0.30) |
| 13 | broadleaf | 34 | 20 | 6 | P peninsula bed (cam01 x 0.24-0.27) |
| 14 | cypress_column | -47 | -39 | 22 | A2 tall column right of the rotunda (user image x~1020) |
| 15 | pine | -47 | -13 | 17 | A2 strip along the north wing (kept below the colonnade entablature) |
| 16 | cypress_column | -58 | -12 | 27 | A2 second column (user image x~1220) |
| 17 | cypress | -74 | -1 | 20 | A2 at the wing's first box |
| 18 | eucalyptus | -90 | 5 | 20 | B big eucalyptus on the strip (ref 141) |
| 19 | pine | -90 | 22 | 16 | B |
| 20 | willow | -100 | 37 | 9 | B willow at the water (refs 144/145) |
| 21 | eucalyptus | -106 | 20 | 30 | B big eucalyptus behind the willows (ref 171) |
| 22 | cypress | -118 | 8 | 22 | B beyond the north pylon |
| 23 | cypress_column | -112 | 40 | 24 | B tall column beyond the north pylon (ref 169 right) |
| 24 | cypress_column | 36 | 21 | 26 | C cypress column left of the rotunda (user image x~290): peninsula south lobe, base at the water |
| 25 | cypress_column | 31 | 28 | 24 | C second column (user image x~330), south lobe |
| 26 | broadleaf | 32 | 27 | 13 | C small dark tree touching the rotunda's left edge (user image x~410), in the podium planter zone |
| 27 | eucalyptus | 62 | -30 | 30 | C broad eucalyptus behind the south wing (ref 169 left) |
| 28 | pine | 62 | -46 | 18 | C QA-01-6: moved out of cam03 (was 24,-22 = 7 m in front of the camera) |
| 29 | broadleaf | 74 | -38 | 10 | C QA-01-6: moved out of cam03 (was 33,-20 = 5 m in front of the camera) |
| 30 | cypress_column | 66 | 40 | 18 | D dense cypress behind the south pylon (ref 169 far left) |
| 31 | eucalyptus | 59 | 15 | 20 | D |
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
| 79 | pine | 67 | -7 | 21 | E1 screen behind the colonnade |
| 80 | cypress | 70 | -3 | 19 | E1 screen behind the colonnade |
| 81 | redwood | 75 | -0 | 22 | E1 screen behind the colonnade |
| 82 | pine | 78 | 4 | 21 | E1 screen behind the colonnade |
| 83 | pine | 86 | 20 | 22 | E1 screen behind the colonnade |
| 84 | redwood | 87 | 25 | 19 | E1 screen behind the colonnade |
| 85 | redwood | 87 | 30 | 21 | E1 screen behind the colonnade |
| 86 | redwood | 83 | 36 | 13 | E1 screen behind the colonnade |
| 87 | redwood | 109 | 37 | 21 | E1 screen behind the colonnade |
| 88 | cypress | 39 | -39 | 20 | E2 screen behind the colonnade |
| 89 | redwood | 50 | -35 | 24 | E2 screen behind the colonnade |
| 90 | eucalyptus | 67 | -21 | 20 | E2 screen behind the colonnade |
| 91 | redwood | 72 | -18 | 22 | E2 screen behind the colonnade |
| 92 | redwood | 74 | -12 | 25 | E2 screen behind the colonnade |
| 93 | redwood | 78 | -7 | 21 | E2 screen behind the colonnade |
| 94 | cypress | 81 | -2 | 25 | E2 screen behind the colonnade |
| 95 | cypress | 88 | 13 | 24 | E2 screen behind the colonnade |
| 96 | redwood | 90 | 18 | 25 | E2 screen behind the colonnade |
| 97 | eucalyptus | 94 | 23 | 21 | E2 screen behind the colonnade |
| 98 | redwood | 119 | 46 | 25 | E2 screen behind the colonnade |
| 99 | eucalyptus | 119 | 52 | 22 | E2 screen behind the colonnade |
| 100 | eucalyptus | 96 | 35 | 25 | E3 screen behind the colonnade |
| 101 | cypress | 123 | 39 | 25 | E3 screen behind the colonnade |
| 102 | eucalyptus | 125 | 47 | 26 | E3 screen behind the colonnade |
| 103 | pine | -118 | 11 | 22 | E1 screen behind the colonnade |
| 104 | cypress | -118 | 6 | 22 | E1 screen behind the colonnade |
| 105 | redwood | -117 | 1 | 22 | E1 screen behind the colonnade |
| 106 | cypress | -114 | -4 | 20 | E1 screen behind the colonnade |
| 107 | redwood | -83 | -11 | 22 | E1 screen behind the colonnade |
| 108 | redwood | -80 | -15 | 21 | E1 screen behind the colonnade |
| 109 | redwood | -75 | -17 | 20 | E1 screen behind the colonnade |
| 110 | redwood | -72 | -22 | 19 | E1 screen behind the colonnade |
| 111 | cypress | -69 | -26 | 21 | E1 screen behind the colonnade |
| 112 | redwood | -54 | -34 | 22 | E1 screen behind the colonnade |
| 113 | cypress | -49 | -35 | 19 | E1 screen behind the colonnade |
| 114 | redwood | -45 | -39 | 21 | E1 screen behind the colonnade |
| 115 | redwood | -40 | -40 | 22 | E1 screen behind the colonnade |
| 116 | redwood | -20 | -45 | 23 | E1 screen behind the colonnade |
| 117 | cypress | -127 | 11 | 21 | E2 screen behind the colonnade |
| 118 | eucalyptus | -125 | 5 | 22 | E2 screen behind the colonnade |
| 119 | redwood | -122 | -0 | 21 | E2 screen behind the colonnade |
| 120 | redwood | -93 | -10 | 22 | E2 screen behind the colonnade |
| 121 | redwood | -90 | -15 | 21 | E2 screen behind the colonnade |
| 122 | redwood | -84 | -19 | 23 | E2 screen behind the colonnade |
| 123 | cypress | -80 | -23 | 24 | E2 screen behind the colonnade |
| 124 | redwood | -77 | -28 | 25 | E2 screen behind the colonnade |
| 125 | redwood | -59 | -38 | 23 | E2 screen behind the colonnade |
| 126 | redwood | -54 | -42 | 24 | E2 screen behind the colonnade |
| 127 | cypress | -48 | -44 | 22 | E2 screen behind the colonnade |
| 128 | redwood | -42 | -45 | 22 | E2 screen behind the colonnade |
| 129 | cypress | -37 | -47 | 20 | E2 screen behind the colonnade |
| 130 | redwood | -20 | -49 | 23 | E2 screen behind the colonnade |
| 131 | redwood | -133 | 3 | 23 | E3 screen behind the colonnade |
| 132 | redwood | -130 | -5 | 23 | E3 screen behind the colonnade |
| 133 | redwood | -104 | -10 | 23 | E3 screen behind the colonnade |
<!-- PLAN_TABLE_END -->

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

- **Materials agent (blocking one QA item)**: the library has no separate pine/redwood needle material.
  `docs/materials_notes.md` says `assets/textures/foliage/needles_pine.png` is generated but unused; QA-01-7 asks for
  "conifer foliage darker (map pines/redwoods to the pine needle material, not cypress)". ENV maps pine, redwood,
  cypress and columnar cypress all to `MAT_leaf_cypress` because creating a local copy would violate the
  library-by-name rule. **Please add `MAT_leaf_pine`** (darker, blue-green, translucency ~0.2) and ENV will remap in
  one line (`env_trees.SPECIES[...]["leaf"]`). Mitigation meanwhile: pine and redwood carry 36–37 k cards per LOD0
  tree, ~55 % more than cypress, so the crowns self-shadow darker.
- **Materials agent**: `MAT_shrub_light`, `MAT_shrub_dry`, `MAT_backdrop_roof`, `MAT_backdrop_skylight` and
  `MAT_backdrop_door_green` are not in the library, so those five are still ENV placeholders (`env_lib.mat` recolours
  them). The shore now uses only library materials — `MAT_shrub` for the mounds and `MAT_reeds` for agapanthus, dry
  reeds and twig shrubs — but a second, lighter/greyer shrub material would let the mahonia read differently from the
  pittosporum. The hall's roof, glazing and green door are the other three.
- **Lead / QA (cam 02)**: see "Sight lines" above — the reference sheet's dark cluster and the new cam 02 at (−45, 52)
  cannot both be satisfied on the available land. The cluster now sits in cam 02's right-edge band at 29–52 m.
- **Lead / build_master**: ENV's materials are appended one at a time by `common.load_material`, which duplicates the
  library's shared node groups; `env_build` now calls `mat_lib.dedupe_node_groups()` before saving, but if the lead
  re-appends ENV into master it should do the same (the materials notes give the one-call recipe).
- **Performance**: LOD0 is 15.1 M tris (LOD1 5.9 M). Trees are ~97 % of it. If the Cycles hero gets too slow, the
  cheapest lever is `env_trees.FAR_RADIUS` (130 m: no QA camera within this distance -> the tree uses the lighter
  mesh); 100 m saves roughly another 2 M.
- The OSM extract has no paths/roads (`_osm.json` contains only buildings and the two water polygons), so QA-01-19's
  "paths from OSM" is served by the satellite-derived path ribbons already baked into the terrain material zones.
- Wind-sculpting of the cypresses (leaning away from the westerlies) is only a 0–4.5° per-instance tilt; no
  per-instance weathering of bark or foliage beyond the library materials' own object-random.
- Diagnostic camera `CAM_env_hall_from_colonnade` mostly sees the colonnade; a proper hall view needs a camera outside
  the wings.
