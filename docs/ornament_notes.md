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
- Baked maps: tangent-space normal 2048 px (figures, capitals) / 1024 px (small pieces), Cycles selected-to-active,
  LOD0 -> LOD1, cage 2 % of the diagonal.

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

## Assets

(Sizes are bounding boxes of LOD0 in metres. Tri counts LOD0 / LOD1 / LOD2. Preview = latest accepted render.)

| asset | size (w x d x h) | tris | variants | preview | notes |
|---|---|---|---|---|---|
| capital_rotunda | see table below | | 3 | | in progress |

Detailed per-asset entries are appended below as each asset lands.

## Open issues / requests
- ARCH (`maiden` socket): the socket must be at the figure's FEET, which are at the level of the box base (top of the
  colonnade entablature / capital block), NOT on the box top rim: photos 163/187 show the figures standing beside the
  box with the rim at shoulder height. The asset assumes the box rim is **3.55 m above the socket** and the box's
  vertical corner edge at local (0, -0.32); +Y = the direction the back faces (outward, on the corner diagonal).
  If ARCH's box is a different height, tell the lead and I will re-pose (it is one parameter).
