# Brief: Environment

You own `assets/environment.blend` (collection `ENV`) and `scripts/env_*.py`. Read: `CLAUDE.md`, `docs/reference_sheet.md`
(site, vegetation, surroundings), `docs/tech_notes.md` (Sapling headless recipe), `scripts/common.py`
(`load_site_local` gives OSM footprints in world coordinates), `scripts/lead_placeholder_blockout.py` (how the lagoon
polygon and ground were cut). Study the user's target image and the canonical photos: the trees are half the picture.

## Deliverables
1. `scripts/env_build.py` (+ `scripts/env_trees.py`, `scripts/env_lib.py`): idempotent rebuild of `ENV`, saved to
   `assets/environment.blend`. Sub-collections: `ENV_terrain`, `ENV_water`, `ENV_trees` (source trees, hidden), `ENV_tree_instances`,
   `ENV_shrubs`, `ENV_backdrop`, `ENV_extras` (birds, rip-rap, lamp posts if any).
2. `scripts/env_preview.py`: temp scene = ENV + linked `assets/placeholder_blockout.blend` (PLACEHOLDER collection,
   only until architecture.blend exists; if `assets/architecture.blend` exists link ARCH instead) + placeholder sun
   (az 118, el 7.8) + sky; render the QA cameras into `renders/previews/environment/`.
3. `docs/environment_notes.md`: planting plan (table of species, position, height), tri counts, LOD strategy, sources.

## What to build
- Terrain: lawn mesh covering ~600 x 600 m around the origin with the lagoon basin cut from the OSM polygon
  (`lagoon0`, plus islets `lagoon1`/`lagoon2` as land if the sheet says they are islands), gentle undulation, the
  rotunda island with its shoreline shape, lawn edges, gravel paths (from OSM if present, else from the satellite
  tile), soil beds. Lagoon bed sloping from the shore (0.3 m deep) to ~1.5 m in the middle. Rip-rap rocks along the
  rotunda island shore (scattered instanced rocks, 0.3-0.8 m).
- Water: `ENV_lagoon_water` plane cut to the lagoon polygon at `common.WATER_Z`, material `MAT_water_lagoon`.
- Trees with Sapling, one source per species preset (2-3 seeds each), converted to meshes: Monterey cypress (dense
  dark, layered, 15-25 m), eucalyptus (tall, open, pendulous, 20-30 m), Monterey pine (15-20 m), willow (near water,
  8-12 m), plus a generic broadleaf. Leaves: Sapling leaf meshes with `MAT_leaf_*`, dense enough to read as foliage at
  hero distance (cypress especially: many small leaves, or leaf clusters). LOD0 full, LOD1 half leaves, LOD2 a few
  billboard-style cards. Place instances from the planting plan derived from the satellite tile and the photos: the
  hero view needs the big cypress/eucalyptus mass behind and to the right (north) of the rotunda and the trees between
  the rotunda and each colonnade end, exactly as in the user's image. Use collection instances or geometry-nodes
  instancing; random rotation/scale per instance.
- Shrubs on the island and shore (scatter low-poly shrub meshes), reeds at the water edge.
- Backdrop: the exhibition hall (OSM `b302`, 20 m high, long curved wall with pilasters and the big arched entrance
  facing the rotunda), Marina district houses within 400 m as simple massing from OSM (`_osm.json`, buildings with
  heights), the wooded Presidio ridge to the west/north-west as a low tree-covered mass, and a distant hill silhouette.
  All low poly with `MAT_backdrop_building` / simple materials.
- Birds: 10-20 low-poly gulls sitting on the shore and floating (optional, cheap).
- Performance: ENV at LOD1 under 3 M triangles; the source trees hidden; instances share mesh data.

Assign materials by library name via `common.load_material` (placeholders OK). Commit after terrain, after trees, after
backdrop. Budget: terrain + water first hour; trees are the big job; backdrop last.
