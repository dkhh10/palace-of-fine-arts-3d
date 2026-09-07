# Ornament and sculpture notes (ORN agent)

Owner: Ornament & Sculpture Modeler. File: `assets/ornament.blend`, collection `ORN` with one sub-collection per type
(`ORN_capital_rotunda`, `ORN_maiden`, ...). Scripts: `scripts/orn_lib.py` (helpers), `scripts/orn_build.py` (builders),
`scripts/orn_preview.py` (previews). Previews: `renders/previews/ornament/`.

Rebuild everything: `blender --background --python scripts/orn_build.py`
Rebuild one type (keeps the rest): `... orn_build.py -- --only maiden [--no-bake] [--fast] [--variants 1]`
Previews: `blender --background --python scripts/orn_preview.py -- [--only maiden] [--sheet] [--lod2]`

## Frame and delivery conventions (docs/sockets.md)
- Every asset: origin at the bottom-centre of its footprint, +Z up, +Y outward (toward the viewer), metres, scale 1.
  Figures keep their feet at the origin (`y_mode="keep"`); wall-mounted reliefs (attic panels, keystones) have the
  origin on their back face (`y_mode="back"`) and project toward +Y.
- Names `ORN_<type>_v<variant>_LOD<0|1|2>`. LOD1 is the viewport default (LOD0/LOD2 have `hide_viewport`).
- Material `MAT_ornament_concrete` via `common.load_material` (placeholder until the library lands).
- LOD1 carries custom props `normal_map` / `ao_map` (`//textures/orn/<name>_nrm.png`, relative to assets/) plus
  `orn_type`, `variant`, `tris`, `size`, `size_note` (and asset-specific props, e.g. `rim_height` on the maidens).
- Baked maps: tangent-space normal 4096 px (attic panels), 2048 px (figures, capitals, urns), 1024 px (small pieces),
  Cycles GPU selected-to-active LOD0 -> LOD1, smart-UV islands on LOD1, **cage 0.5 % of the diagonal, unlimited ray**
  (verified: larger cages make rays hit neighbouring leaves first and leave black patches on curled acanthus).
  AO is not baked (the materials agent's shader has its own cavity; `ao_map` is left empty).

## How things are generated (and deviations from the brief)
- **No sculpting, no cloth sim.** Everything is parametric geometry built with bmesh/parametric surfaces, joined and
  then **voxel-remeshed into one watertight surface** (`orn_lib.union_blob`), lightly smoothed (softens every arris
  the way cast concrete does), then given two layers of procedural displacement (cm-scale weathering + mm-scale
  grain) with a per-variant seed, then decimated to the LOD budgets and baked.
- **Cloth simulation was tested and rejected** (2026-09-06/07): with Blender 5.2.1 headless the cloth falls straight
  through collision objects in every configuration tried (collision modifier first/last, thickness_outer 0.05,
  distance_min 0.03, quality 10-15, ptcache.bake_all, reduced gravity) - same result as the lead's smoke test.
  The Ellerhusen drapery is also strongly stylised (parallel vertical fluting, not free cloth), so the garments are
  built as **lofted drapery tubes** (`orn_build.drapery_tube`): superellipse cross-sections following the body proxy,
  with sharp radial fold ridges whose amplitude grows toward the hem, phase-drifting with height, restricted to the
  visible side. A second, slightly larger tube makes the peplos overfold. This gives deterministic, controllable folds
  that read as carved concrete at 15-100 m.
- **Body proxies**: skin-modifier stick figures (`orn_lib.skin_figure`, joints with per-joint ellipsoidal radii,
  subdivided), plus spheres for head/hair. The proxy is mostly hidden inside the garment; what shows is the head,
  neck, shoulders, arms/hands.
- **Capitals**: bell (lathe) + concave-sided abacus (loft) + two rows of eight parametric "shell" acanthus leaves
  (the Palace leaves are broad radially-ribbed fans with a rolled lip, see inner_capital_2 / corinthian_capital_1)
  + eight corner scrolls (band sweeps along a shrinking spiral with a caulis stem; two per corner, one facing each
  side) + eight inner helices + (rotunda only) a half-length female figure at every face centre - the Palace's
  rotunda capitals have a figure where a classic Corinthian has the fleuron (corinthian_capital_1-3). Inner and
  colonnade capitals get a rosette fleuron instead. Every leaf/scroll gets small random rotation/length/curl jitter
  per variant so no two variants are identical.

- **Relief panels**: the three public-domain relief scans (`reference/scans/`: Parthenon centaur metope, two
  Trajan's-column cast slabs; 1-2 M tris each) are imported (cm -> m), decimated to 120 k, re-oriented (face +Y,
  up +Z), scaled to ~4.1-4.2 m figure height and 0.40 m relief depth, mirrored where needed, and sunk into the slab
  so that their own background plane sits 2 cm behind the panel face (background depth = area-weighted median of
  the front-facing faces). The union is voxel-remeshed at 2.5 cm, so the scan surfaces merge with the slab and lose
  their scan-specific crispness (they become "cast concrete" like everything else). Three designs by variant.
- **Urns, finial, rosettes, mouldings**: lathe profiles with angular scale functions (gadroons, scales, petals),
  band sweeps for handles/scrolls, boxes for dentils/keys, all unioned by voxel remesh.

## Assets

(Sizes = LOD0 bounding box in metres (x width, y depth, z height). Tri counts LOD0 / LOD1 / LOD2. Previews are
`renders/previews/ornament/full01_<asset>.png` (LOD0 on the left, LOD1 with its baked normal map on the right) and
the contact sheet `full01_contact_sheet.png`; render-vs-crop sheets `compare_<asset>.png` / `compare_sheet.png`
from `scripts/orn_compare.py`.)

ASSET_TABLE_PLACEHOLDER

### Per-asset notes
- **capital_rotunda** (h 2.60, shaft-top r 1.05, abacus 3.0 m across the corners, overall 3.5 m across the leaf tips).
  Figured Corinthian per corinthian_capital_1-3: lower row of 8 shell leaves (0.42 H), upper row (0.50 H, more curl),
  8 corner scrolls (band 0.30 R wide) + 8 helices, a half-length female figure at each face centre (torso rising from
  the upper leaves, arms to the helices, head under the abacus), bead astragal at the bottom. Variants differ in leaf
  jitter, curl/droop and the weathering seed. LOD2 = bell + abacus only.
- **capital_inner** (h 1.8, shaft-top r 0.80, abacus 2.15) and **capital_colonnade** (h 1.8, r 0.85, abacus 2.3,
  squatter: small lower leaves, big upper shells and scrolls) share the generator; rosette fleuron instead of the figure.
  The pylon-cluster capitals are the colonnade capital (ARCH raises the shaft 2.4 m).
- **maiden** (4.5 m standing, 4.3 m tall with the head bowed, footprint about 1.3 x 1.3 m). Skin-figure body leaning
  forward, forearms along the two rim edges of the box corner, peplos tube + overfold with dipping hem, sleeve
  cascades under the elbows, hair bound in a bun. Custom props `rim_height` = 3.55, `box_corner_y` = -0.32.
- **attic_figure** (6.7 m). v1 male: skin body with a nude torso, both arms raised to the chest, wrapped cloth from
  the waist with heavy frontal folds, mantle behind; v2 female: full gown + overfold, one arm across the chest.
  Faces +Y; the niche (ARCH) is 0.6 m deep behind it.
- **winged_figure** (4.6 m): gown with frontal folds, two tall fluted wing slabs behind the shoulders (top above the
  head, tips at the calves), cornucopia horns from the hands. Faces -Y (toward the rotunda centre).
- **urn** (3.0 m podium urn incl. 0.32 m plinth), **urn_niche** (1.6 m corner urn with a scale pattern), **urn_tub**
  (pylon planter 1.6 m diameter): note the three are separate socket types.
- **keystone** (0.8 m lion mask on a 0.62 m back plate, mane of 14 shell leaves), origin at the back-face bottom-centre.
- **attic_panel** v1/v2/v3 = designs A/B/C (combat with centaur; procession of draped figures; kneeling group).
- **finial** (dome apex cap 0.6 m), **rosette_ceiling** (0.6 m coffer rosette, projects +Y), **drum_band** (1 m
  unit, 1.6 m tall scale cushion), **dentil / egg_and_dart / greek_key / rosette_band / modillion / anthemion**
  (1 m units, origin at the back-face bottom-centre, projecting +Y; sizes in the table).

## Open issues / requests
- ARCH (`maiden` socket): the socket must be at the figure's FEET, which are at the level of the box base (top of the
  colonnade entablature / capital block), NOT on the box top rim: photos 163/187 show the figures standing beside the
  box with the rim at shoulder height. The asset assumes the box rim is **3.55 m above the socket** and the box's
  vertical corner edge at local (0, -0.32); +Y = the direction the back faces (outward, on the corner diagonal).
  If ARCH's box is a different height, tell the lead and I will re-pose (it is one parameter).
