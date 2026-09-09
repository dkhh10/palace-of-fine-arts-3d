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

| asset | variant | size w x d x h (m) | tris LOD0 / LOD1 / LOD2 | normal map | preview |
|---|---|---|---|---|---|
| anthemion | v1 | 1.02 x 0.08 x 0.22 | 30000 / 6000 / 600 | yes | `full01_anthemion_v1.png` |
| attic_figure | v1 | 2.96 x 1.68 x 6.78 | 120000 / 20000 / 2000 | yes | `full01_attic_figure_v1.png` |
| attic_figure | v2 | 2.44 x 1.85 x 6.82 | 120000 / 20000 / 2000 | yes | `full01_attic_figure_v2.png` |
| **attic_panel** | v1 (design A) | 10.51 x 0.48 x 4.51 | 142571 / 23960 / 2389 | yes | `fix01_attic_panel_v1.png` |
| **attic_panel** | v2 (design B) | 10.51 x 0.45 x 4.52 | 146564 / 23881 / 5598 | yes | `fix01_attic_panel_v2.png` |
| **attic_panel** | v3 (design C) | 10.51 x 0.47 x 4.51 | 145438 / 23981 / 2386 | yes | `fix01_attic_panel_v3.png` |
| capital_colonnade | v1 | 2.68 x 2.71 x 1.82 | 80000 / 16000 / 344 | yes | `full01_capital_colonnade_v1.png` |
| capital_colonnade | v2 | 2.85 x 2.88 x 1.82 | 80000 / 16000 / 344 | yes | `full01_capital_colonnade_v2.png` |
| capital_colonnade | v3 | 2.70 x 2.64 x 1.82 | 80000 / 16000 / 344 | yes | `full01_capital_colonnade_v3.png` |
| capital_inner | v1 | 2.63 x 2.54 x 1.81 | 80000 / 16000 / 344 | yes | `full01_capital_inner_v1.png` |
| capital_inner | v2 | 2.81 x 2.76 x 1.81 | 80000 / 16000 / 344 | yes | `full01_capital_inner_v2.png` |
| capital_rotunda | v1 | 3.52 x 3.49 x 2.60 | 100000 / 20000 / 344 | yes | `fix01_variants_capital_rotunda.png` |
| capital_rotunda | v2 | 3.72 x 3.80 x 2.60 | 99998 / 20000 / 344 | yes | (same sheet) |
| capital_rotunda | v3 | 3.50 x 3.42 x 2.60 | 100000 / 20000 / 344 | yes | (same sheet) |
| **corner_scroll** | v1 | 1.78 x 0.87 x 0.91 | 40000 / 8000 / 800 | yes | `fix01_corner_scroll_v1.png` |
| **corner_scroll** | v2 | 1.78 x 0.87 x 0.91 | 40000 / 8000 / 800 | yes | `fix01_corner_scroll_v2.png` |
| dentil | v1 | 1.00 x 0.16 x 0.22 | 30000 / 6000 / 600 | yes | `full01_dentil_v1.png` |
| drum_band | v1 | 1.08 x 0.42 x 1.63 | 30000 / 6000 / 600 | yes | `full01_drum_band_v1.png` |
| egg_and_dart | v1 | 1.01 x 0.13 x 0.20 | 30000 / 6000 / 600 | yes | `full01_egg_and_dart_v1.png` |
| finial | v1 | 0.80 x 0.80 x 0.60 | 20000 / 4000 / 400 | yes | `full01_finial_v1.png` |
| **greek_key** | v1 | 0.60 x 0.08 x 0.52 | 30000 / 6000 / 600 | yes | `frieze_run_straight.png` |
| keystone | v1 | 0.75 x 0.50 x 0.73 | 50000 / 8000 / 800 | yes | `full01_keystone_v1.png` |
| keystone | v2 | 0.73 x 0.50 x 0.73 | 50000 / 8000 / 800 | yes | `full01_keystone_v2.png` |
| **maiden** | v1 | 1.39 x 1.46 x 3.84 | 100000 / 20000 / 2000 | yes | `fix01_variants_maiden.png` |
| **maiden** | v2 | 1.52 x 1.67 x 3.77 | 100000 / 20000 / 2000 | yes | (same sheet) |
| **maiden** | v3 | 1.32 x 1.38 x 3.88 | 100000 / 20000 / 2000 | yes | (same sheet) |
| modillion | v1 | 1.00 x 0.40 x 0.30 | 30000 / 6000 / 600 | yes | `full01_modillion_v1.png` |
| **rosette_band** | v1 | 1.20 x 0.13 x 0.52 | 30000 / 6000 / 600 | yes | `frieze_run_rostra_straight.png` |
| rosette_ceiling | v1 | 0.65 x 0.17 x 0.65 | 20000 / 4000 / 400 | yes | `full01_rosette_ceiling_v1.png` |
| rosette_ceiling | v2 | 0.65 x 0.17 x 0.65 | 20000 / 4000 / 400 | yes | `full01_rosette_ceiling_v2.png` |
| urn | v1 | 1.76 x 1.54 x 3.00 | 60000 / 12000 / 1200 | yes | `full01_urn_v1.png` |
| urn | v2 | 1.76 x 1.54 x 3.00 | 60000 / 12000 / 1200 | yes | `full01_urn_v2.png` |
| urn | v3 | 1.72 x 1.49 x 3.00 | 60000 / 12000 / 1200 | yes | `full01_urn_v3.png` |
| urn_niche | v1 | 1.50 x 1.24 x 1.60 | 60000 / 12000 / 1200 | yes | `full01_urn_niche_v1.png` |
| urn_niche | v2 | 1.46 x 1.21 x 1.60 | 60000 / 12000 / 1200 | yes | `full01_urn_niche_v2.png` |
| urn_tub | v1 | 1.60 x 1.60 x 1.00 | 60000 / 12000 / 1200 | yes | `full01_urn_tub_v1.png` |
| winged_figure | v1 | 2.29 x 1.45 x 4.93 | 100000 / 20000 / 2000 | yes | `full01_winged_figure_v1.png` |
| winged_figure | v2 | 2.29 x 1.45 x 4.93 | 100000 / 20000 / 2000 | yes | `full01_winged_figure_v2.png` |

### Per-asset notes
- **capital_rotunda** (h 2.60, shaft-top r 1.05, abacus 3.0 m across the corners, overall 3.5 m across the leaf tips).
  Figured Corinthian per corinthian_capital_1-3: lower row of 8 shell leaves (0.42 H), upper row (0.50 H, more curl),
  8 corner scrolls (band 0.30 R wide) + 8 helices, a half-length female figure at each face centre (torso rising from
  the upper leaves, arms to the helices, head under the abacus), bead astragal at the bottom. Variants differ in leaf
  jitter, curl/droop and the weathering seed. LOD2 = bell + abacus only.
- **capital_inner** (h 1.8, shaft-top r 0.80, abacus 2.15) and **capital_colonnade** (h 1.8, r 0.85, abacus 2.3,
  squatter: small lower leaves, big upper shells and scrolls) share the generator; rosette fleuron instead of the figure.
  The pylon-cluster capitals are the colonnade capital (ARCH raises the shaft 2.4 m).
- **maiden** (3.77-3.88 m of hanging figure in the socket frame; the figure is ~4.3 m from feet to crown). Skin-figure
  body leaning forward and hunched, forearms folded on the two rim edges of the box corner with the elbows out, head
  sunk between the shoulders and bowed over the corner into the box, peplos tube + overfold with a dipping hem and
  deep vertical fluting, sleeve cascades under the elbows, hair in a bun. **Origin = ARCH's socket on the box lid**,
  0.78 m inward from the corner along the diagonal: box corner edge at (0, +0.78, 0), rim at z ~ 0, feet at z = -3.30.
  Custom props `rim_height` 3.30, `box_corner_y` 0.78, `feet_z` -3.30, `origin_note`.
- **attic_figure** (6.7 m). v1 male: skin body with a nude torso, both arms raised to the chest, wrapped cloth from
  the waist with heavy frontal folds, mantle behind; v2 female: full gown + overfold, one arm across the chest.
  Faces +Y; the niche (ARCH) is 0.6 m deep behind it.
- **winged_figure** (4.6 m): gown with frontal folds, two tall fluted wing slabs behind the shoulders (top above the
  head, tips at the calves), cornucopia horns from the hands. Faces -Y (toward the rotunda centre).
- **urn** (3.0 m podium urn incl. 0.32 m plinth), **urn_niche** (1.6 m corner urn with a scale pattern), **urn_tub**
  (pylon planter 1.6 m diameter): note the three are separate socket types.
- **keystone** (0.8 m lion mask on a 0.62 m back plate, mane of 14 shell leaves), origin at the back-face bottom-centre.
- **attic_panel** v1/v2/v3 = designs A/B/C (combat with a rearing horse; procession of draped figures; kneeling group).
  Field exactly 10.5 x 4.5 m, total depth 0.42 m (0.16 slab + up to 0.26 m of relief after the remesh), **15 / 13 / 13
  figures**, measured figure coverage **63.5 / 61.6 / 64.2 %** (`scripts/orn_panel_coverage.py`, LOD1 within 0.3 %).
  Anything overhanging the field is clamped onto the frame plane and nothing sits behind the slab's back face.
- **corner_scroll** v1/v2 (QA-01-13): 1.78 x 0.87 x 0.91 m over the volute rolls, nominal `unit_length` 1.50 m.
- **finial** (dome apex cap 0.6 m), **rosette_ceiling** (0.6 m coffer rosette, projects +Y), **drum_band** (1 m
  unit, 1.6 m tall scale cushion), **dentil / egg_and_dart / greek_key / rosette_band / modillion / anthemion**
  (1 m units, origin at the back-face bottom-centre, projecting +Y; sizes in the table).

## File size and budgets
`assets/ornament.blend` = 84 MB (compressed save), 36 assets, 2.62 M LOD0 tris in total after trimming LOD0 budgets
(panels 150 k, attic figures 120 k, capitals/maidens/winged 100 k, inner/colonnade capitals 80 k, urns 60 k,
mouldings 30 k). Normal maps: 36 PNGs, 67 MB under `assets/textures/orn/`. If the lead needs the file smaller:
LOD0 of the three attic panels (450 k) and the eight capitals (0.9 M) dominate; halving them costs nothing visible
at hero distance because LOD1 + normal map already carries the detail. Full rebuild time about 8 min (the three
relief scans take 40 s to import and decimate).

## QA round 01 fixes (Phase 3, 2026-09-07)

### QA-01-10 — Zimm attic panels were sparse
`PANEL_LAYOUTS` in `orn_build.py` now composes each of the three designs from the relief scans **plus** from-scratch
figures (`relief_figure`, new poses `arms_up` / `stride` / `kneel` / `arms_out` in `human_joints`) and a rearing horse
(`relief_horse`, `horse_joints`). Relief depth 0.40 -> 0.50 m, figures ~0.22 m proud of the face, figure height ~4 m
(the scan groups) / ~3.5 m (the modelled figures). Coverage is measured, not eyeballed:
`blender --background --python scripts/orn_panel_coverage.py` ray-casts a 420-px grid at the panel from the front and
reports the fraction of the field standing >= 6 cm proud of the slab face. Numbers in the asset table below.

### QA-01-11 — podium Greek-key meander with rosette bosses
The photos (rostra_band_1/2) show the fret **incised** into a flat face, not raised, so both units are now a flat slab
with the meander cut out of it by boolean (`greek_key_cutters` + `cut_boxes`), and only the round paterae stand proud.

| unit | `unit_length` | band height | relief | composition |
|---|---|---|---|---|
| `ORN_greek_key` | **0.60 m** (one meander repeat) | 0.52 m | groove **4.5 cm** deep in an 8 cm slab | grid g = U/7, inner field 5g = 0.43 m, groove width 5.2 cm; the top groove overruns the unit by 5 % so consecutive units join into one continuous meander |
| `ORN_rosette_band` | **1.20 m** | 0.52 m | groove 4.5 cm; boss 5.5 cm proud | one **0.45 m** petalled patera boss alternating with one meander repeat (sheet s4 #12) |

Both share the band height, so a run can mix them. Every moulding unit (`dentil`, `egg_and_dart`, `greek_key`,
`rosette_band`, `modillion`, `anthemion`) now carries custom properties `unit_length`, `band_height`, `relief_depth`
on all three LODs.

**Helper for the lead** (in `orn_lib.py`, call from `build_master.py`):

    array_unit_along_run(unit_obj, socket_empty, collection=None, name_prefix=None, instances=True,
                         seed_base=None, extra_props=None, fit="auto", tol=0.06, alternatives=None) -> [objects]

Lays copies of a moulding unit end to end along a `frieze_run` socket and returns them. Straight runs use
`run_length` (or `size_hint`); curved runs use `arc_center` + `arc_radius` and, if present, `arc_start` / `arc_end` —
without the angles the start angle comes from the socket's position and the sweep direction from its local +X, both
per `docs/sockets.md`. `n = round(run / unit_length)`. `fit` decides what happens to the leftover:
`"scale"` stretches every unit along X so the run ends flush; `"centre"` lays `floor(run / unit)` unscaled units
centred on the run with equal plain margins at the ends (what a real frieze does on a short run); `"auto"` (default)
scales when that costs less than `tol` = 6 % and otherwise centres. `alternatives=[other_unit, ...]` makes the helper
pick, per run, whichever unit fits best — hand it `[ORN_rosette_band, ORN_greek_key]` and short box-base runs get the
0.60 m meander while long rostra runs get the 1.20 m rosette band. Curved units are chords of the arc, oriented
X = chord tangent, Z = the socket's up, Y = Z x X (identical to the socket's own frame at the first unit).
With `instances=True` every copy shares the unit's mesh (one mesh in memory). Each copy gets `orn_type`,
`unit_index`, `run_socket` and a decorrelated `instance_seed`.
`orn_lib.unit_length_of(obj)` returns the documented repeat length (falls back to the bbox X size).

Tested by `scripts/orn_frieze_test.py` against the **128 `frieze_run` sockets ARCH now ships** (98 straight rostra /
box-base runs with `subtype='greek_key'`, 1.42-6.18 m, 434 m total; 4 curved colonnade architrave runs with
`subtype='greek_fret'`, r 115.15/119.65, 383 m total; 24 rotunda ressaut runs with no subtype, 3.00 / 5.91 m, 95 m
total) plus two mock sockets. Result: **1432 units on 128 sockets, worst unit-to-unit spacing error 1.8 mm, worst
deviation of a unit from its arc 4.8 mm (the chord sagitta), worst plain margin left at a run end 518 mm** (less than
one 0.60 m unit, by design on a centred fit). Renders in
`renders/previews/ornament/frieze_run_{straight,curved,rostra_straight,rostra_curved}.png`. Mapping used in the test
and recommended to the lead: `subtype == 'greek_key'` (or `'rostra'`) -> `ORN_rosette_band` with
`alternatives=[ORN_greek_key]`; anything else -> `ORN_greek_key`.

### QA-01-13 — attic corner scrolls and the maiden pose

**Proposed `corner_scroll` socket frame (for the lead to pass to ARCH).** Origin at the **bottom-centre of the scroll
block**, i.e. on the top face of the attic-corner cap (`ARCH_rotunda_attic_corner_cap_*`, top at z = 38.28); local
**+Z up, +Y outward** (the same outward direction as the corner's `attic_figure` socket), scale 1, `size_hint` 1.50.
Two per corner niche = **16 sockets**, at local x = **+-1.95 m** from the corner-cap centre (one on each pilaster
flanking the figure niche), i.e. `location = cap_centre + rot_z(rz) @ (+-1.95, 0, 0)`, `z = 38.30`, `rz` copied from
that corner's `attic_figure` socket.

**Interim, no new socket needed:** ARCH already ships 8 `finial` sockets with `subtype='volute_scroll'`,
`size_hint` 1.5, at z = 38.30 on the corner-cap centres (`SOCKET_finial_000..007`) with exactly this frame, so
`ORN_corner_scroll` drops straight onto them — one centred block per corner instead of a flanking pair.
**Important for `build_master.py`:** those 8 sockets are typed `finial`, so the current type -> collection mapping
gives them the 0.6 m dome-apex cap. Route `finial` sockets by subtype: `volute_scroll` -> `ORN_corner_scroll`,
`dome_apex` (`SOCKET_finial_008`, z = 49.4) -> `ORN_finial`.

New asset **`ORN_corner_scroll`** (was drafted as `scroll_attic`; renamed to the socket type the lead asked for).
One unit = the Ionic-type paired volute block that caps ONE pilaster flanking an attic corner figure niche
(refs 085 / attic_corner_figure_1-3): two spiral volutes of 0.40 m eye radius at the ends, a channelled bolster with
an egg-moulded echinus between them, a moulded abacus over the top, a small palmette in the channel and a necking
astragal underneath. 2 variants (weathering seed).

Maiden: rebuilt in the socket frame ARCH actually uses (origin on the box lid, 0.78 m inward from the corner along
the diagonal), forearms folded onto the rim near the corner with the elbows out and the hands drawn in, head bowed
over the corner into the box (refs 187/163), per-variant lean / bow / head turn / hem / fold count so the three read
differently. `rim_z` 3.30 m; feet at z = -3.30 in the socket frame; custom props `rim_height`, `box_corner_y` (0.78),
`feet_z`, `origin_note`.

### QA-01-18 — per-instance variation
- `MAT_ornament_concrete` (materials library) drives its variation from the node group `PFA_instance`, which contains
  an **Object Info** node — so its `Random` output already decorrelates separate instance objects in both engines.
- **It does NOT read the `instance_seed` custom property**: there is no `ShaderNodeAttribute` anywhere in
  `MAT_ornament_concrete` or in `PFA_instance` / `PFA_concrete` / `PFA_streaks` / `PFA_edge` / `PFA_algae`.
  Request to the materials agent (I do not own that file): add
  `ShaderNodeAttribute(attribute_type='OBJECT', attribute_name='instance_seed')` inside `PFA_instance` and add it to
  the `Seed` input, so the lead's deliberate per-instance seed (and the one `array_unit_along_run` writes) actually
  moves the pattern instead of relying on Blender's own object random.
- Geometry side (mine): the capital variants now differ in **silhouette**, not only in the weathering seed —
  `CAPITAL_STYLE` scales lower-leaf width, upper-leaf length, curl, droop, volute radius and helix radius per variant
  and variant 2 has one chipped/short leaf tip. Same for the maidens (pose parameters above) and the urns.

## QA round 02 fixes (Phase 4 polish round 1, 2026-09-07)

### Why the relief read as a decal (QA-02-9) — measured, not guessed
`scripts/orn_relief_check.py` ray-casts a 260 x 120 grid at an asset from the front and reports the depth
histogram, the spread of N·L for the morning sun, the fraction of the surface that shadows itself, and the mean
sky-openness of every sample (the occlusion term). Two measurements explain the defect:

1. **The sun is within 11° of the panel's own normal.** `--sockets` prints s·n for every attic socket with
   sun az 118.5 / el 7.4 (`s = (0.473, 0.872, 0.129)`): `SOCKET_attic_panel_001` — the face cam05 and cam01 both
   see — has **s·n = 0.981**, `attic_figure_001` 0.962, `finial_001` (the corner scroll) 0.962. A body standing
   `d` proud of a vertical wall casts a shadow only `d·√(1−(s·n)²)/(s·n)` along that wall = **2 cm for a 10 cm
   projection** here. No amount of relief will produce ref 063's cast shadows at this sun angle; the darkness has
   to come from *occlusion*, i.e. from ground that is deep and narrow relative to what stands over it.
2. **There was no ground.** The old panel measured p10 depth **0.168 m** with **100 % of the field ≥ 15 cm proud**:
   `place_scan` sank each relief scan's own background plate to 2 cm behind the slab face, so the "field" was the
   scan's backing, and the figures were a 0.28 m mound on top of it. Sun-blocked 0.3 %, sky-openness 0.900 — an
   essentially unoccluded surface, which is exactly what "engraved decal" looks like.

### QA-02-9 — attic panels
| | before | after |
|---|---|---|
| depth p10 / p50 / max above the back plane | 0.168 / 0.287 / 0.482 m | **0.022 / 0.347 / 0.628 m** |
| field ≥ 25 / 40 / 55 cm proud | 58.9 / 8.5 / 0.0 % | 60.6 / 36.4 / 7.0 % |
| N·L relative spread (sun on a +Y face) | 0.189 | **0.328** |
| self-shadowed samples / mean sky-openness | 0.3 % / 0.900 | **6.6 % / 0.737** |
| LOD0 / LOD1 / LOD2 tris (v1) | 142571 / 23960 / 2389 | 128606 / 23751 / 15343 |
| figures per panel | 15 / 13 / 13 | **22 / 20 / 20** |

What changed:
- **The field ground is sunk to y = 0.015** with a 0.115 m border left standing at y = 0.16, and the scans'
  background plates go down to it (`place_scan(..., bg_y=, front_y=)` solves each scan's depth scale from its own
  `bg_frac`, which differs a lot: 0.36 centaur, 0.53 soldiers, 0.63 dacians).
- **Two depth registers plus a back row.** Front row fronts at y ≈ 0.575, alternating figures at 0.415, and a new
  back row of 7 figures at 0.215 filling the gaps. What reads as carving at 100 m is the ladder of dark slots
  between a front body and the half-hidden one behind it (ref 063 / zimm_panel_1 are a two-deep crowd).
- **The figures were far too fat**: `bulk` 1.45–1.70 gave a 1.4 m wide torso on a 3.85 m figure and the garment
  half-width was `0.215·H` = a 1.7 m wide cone, so the whole panel voxel-fused into one pale mound. Now
  `bulk` 1.02–1.18, garment `0.128·H`, and the body is depth-compressed (`flatten` 0.42–0.54 front, 0.30–0.40
  back) so the exposed cap of each body carries the full sweep of turned normals instead of a 40° cap.
- **The envelope is ARCH's, measured**: `ARCH_rotunda_attic_panel_*` (the sunk field block) has its front face at
  socket-local y = 0.00 and `ARCH_rotunda_attic_frame_*` (the 4.7 cm moulding ring) stands at y = 0.234–0.281,
  so the recess is 0.28 m deep. The panel mass stays inside it; only the boldest figures break the frame plane,
  by ≈ 0.35 m, as limbs do in ref 063. An earlier pass at 0.83 m of relief measured better (rendered relative
  luminance std 0.158 vs 0.139) but stood 0.55 m proud of ARCH's frame, which is wrong, so it was pulled back.
- Remesh smoothing 1 pass at factor 0.18 (was 0.3) at a 0.024 voxel.

**Honest limit.** QA-02-9 asks for the panel's luminance std ≥ 60 % of ref 063's over the same box. Measured with
`scripts/orn_relief_stats.py` (relative std = std/mean, exposure-invariant): ref 063 **0.296**, so the bar is
0.178. The rebuilt panel renders **0.139** at exposure −3.29 and 0.117 at −2.39 in the look-dev, against 0.136
for the old panel in the round-02 master. Ref 063 was shot with a high sun that throws 10–20 cm cast shadows
across the field; at az 118.5 / el 7.4 the sun is 11° off this panel's normal and throws none, and AgX compresses
what is left as the exposure rises. The remaining distance is a **materials** job (QA-02-3 dust in the recesses,
which now have recesses to sit in) and a lighting one, not a geometry one — the geometry metrics are all now
between 1.7x and 3x better. Flagged to the lead.

### Verification in the full scene (orn3)
`scripts/lead_build.sh` on this branch, then
`blender -b --python scripts/qa_render_round.py -- --round orn3 --final --samples 64 --cams 01 05`
(Cycles 1920x1080, 363 s cam01 / 621 s cam05, exposure still -3.2911: the lighting agent's -2.39 had not landed).
Sheet: `renders/previews/ornament/orn3_qa02_9_10_sheet.png` (cam05 new / cam05 round 02 / ref 063, then
cam01 new / cam01 round 02 / ref 169). Panel box relative luminance std, `scripts/orn_relief_stats.py`:

| camera | box | round 02 | **orn3** | reference | QA-02-9 bar (60 % of ref) |
|---|---|---|---|---|---|
| cam05 | 872,134-1076,225 (ref 702,199-913,307) | 0.136 | **0.206** | 0.296 (ref 063) | 0.178 — **met** |
| cam01 | 888,197-1038,254 (ref 902,243-1016,288) | 0.123 | **0.162** | 0.271 (ref 169) | 0.163 — at the bar |

So QA-02-9's acceptance is met at cam05 (70 % of ref 063) and lands on the line at cam01. Both numbers will move
when the exposure goes to -2.39: measured in the look-dev, +0.9 EV costs about 0.02-0.03 of relative std because
AgX compresses the highlights, so a re-measure after the lighting merge is worth doing.

### QA-02-10 / QA-01-13 — attic corner figures and the scroll pair
- **Corner figure.** Two failures: `union_blob(..., smooth=3)` at a 2.8 cm voxel closed the arm-to-torso gaps and
  the drapery channels, and the wrap/gown was `0.27·S` half-width = a **2.07 m wide bell** on a 6.7 m figure.
  Now: remesh `smooth=1, factor 0.25` at 2.2 cm; wrap, mantle, gown and overfold narrowed ×0.56–0.57; and
  `attic_side_cascades()` adds the two heavy cloth panels that hang from behind the arms to the hem on both
  sides in `attic_corner_figure_1` / ref 085, at 0.325·S out with 0.20–0.44 relative folds (fold depth 0.09–0.19 m
  on a 0.44 m half-width cascade), leaving a ≈ 0.2 m dark slot between each cascade and the body.
  Bbox 2.96 → **3.71 m** wide (v1) / 3.48 m (v2), height unchanged at 6.78 / 6.82 m, LOD0 still 120 k.
  Measured: relief ≥ 0.55 m over 99 % of the front, N·L relative spread 0.312 → 0.319, sky-openness 0.774 → 0.788.
- **Scroll pair.** `ORN_corner_scroll` is now **a pair** of Ionic volute blocks 0.83 m apart on a shared moulded
  plinth (2.44 × 0.89 × 1.60 m, spiral eye r 0.44, LOD0 40 k), not the single 1.78 m block that used to sit
  *between* ARCH's own pair. ARCH already models crude volutes on the same sockets
  (`ARCH_rotunda_attic_volute_NN_a/_b`, 290 tris, centres at local x = ±0.415, z 0.25–1.52, y −0.10…0.22, on a
  1.90 × 0.60 × 0.25 plinth); the new asset is built to **those centres and to an envelope that fully encloses
  them**, so the two cannot z-fight whichever the lead hides. If the lead prefers the photographed arrangement
  (a scroll over each flanking pilaster, ±1.95 m — attic_corner_figure_1), ARCH must move its volutes and add the
  16 `corner_scroll` sockets proposed under QA-01-13; the asset would then be split back into single blocks.

### LOD0 budget
`capital_colonnade` LOD0 trimmed **80 k → 48 k** in place with `scripts/orn_trim_lod0.py` (no re-bake: LOD1 and
its normal map are untouched). 114 instances, so **−3.6 M tris** in the master. Panel LOD0 also came down
(142–147 k → 129–143 k). No LOD0 budget was raised.

### New tools (ORN-owned)
- `scripts/orn_relief_check.py` — `--sockets` (ARCH socket frames + s·n for the morning sun), `--arch <patterns>`
  (ARCH object sizes in the socket frame), `--objects <names>` (depth histogram, N·L spread, self-shadow and
  sky-openness). Reads only; never writes a .blend.
- `scripts/orn_relief_stats.py` — python3/PIL: relative luminance std of a box in any image, `--save` writes the
  crops side by side. The exposure-invariant form of QA-02-9's acceptance test.
- `scripts/orn_relief_render.py` — the attic band (panel + corner figure + scroll + stand-in wall) from the real
  cam05 station with the real rig, Cycles, ~10 s a look. `--exposure` to preview the lighting agent's −2.39.
- `scripts/orn_trim_lod0.py` — in-place LOD0 decimation.

## Round 4 (2026-09-08) — QA-03-15 capitals, QA-03-8 rosettes, carried keystone depth

Composite: `renders/previews/ornament/orn4_sheet.png` (before / after / reference for all three, hero 1:1 crops at
x6 plus look-dev views). Variant strips: `orn4_variants_capital_rotunda.png`, `..._capital_colonnade.png`,
`..._rosette_ceiling.png`, `..._keystone.png`.

### How this round was measured
`scripts/orn_r4_render.py` places the three assets on their REAL ARCH socket frames with the real lighting rig and
renders each twice: a **hero** view that is a 1:1 crop out of the full CAM_qa_01 (or CAM_qa_04) 1920x1080 frame —
exactly the pixels QA judges — and a **look-dev** view from the angle the reference crop was shot from. One stone
(`MAT_concrete_ochre`) is used for ornament and stand-in wall alike so the sheet compares geometry, not materials.
`scripts/orn_tier_stats.py` turns a hero crop into a vertical luminance profile and reports the relative luminance
std (std/mean) and the number of light/dark alternations clearing a Michelson contrast threshold.

**The bar, measured from the photograph.** Three rotunda capitals cropped out of ref 169 (aligned panel of
`renders/qa_comparisons/round03_cam01_aligned_vs_ref169.png`) are 38-44 px tall — the same scale as ours at cam01
(2.6 m at 82 m through a 20 mm lens = 34 px). They measure **relative std 0.428 / 0.445 / 0.459 with 6-7
alternations** at Michelson >= 0.05. That is the target; a photograph and an AgX render do not share a tone curve,
so treat it as a direction, not a ratio.

### QA-03-15 — Corinthian capitals: why they were blobs
The round-3 bell flared to **1.30 R** at the top while the leaves' bodies sat at ~1.00 R and only their last third
broke the surface: every acanthus leaf was **buried inside the kalathos** and showed as a faint embossed outline.
That is the whole defect — it was never a shading or a tri-budget problem.

Rebuilt:
- **New kalathos**: 1.00 R at the astragal, necks to **0.865 R** at the waist, flares to **1.155 R** under the
  volutes (was 1.30 R). The bell is also **scalloped** (`scallop = 0.078 R`, 16 dips, `revolve(scale_fn=...)`) so
  the slot between two neighbouring leaves bottoms out in a 0.064 m groove instead of on a smooth cylinder.
  *Review fix (2026-09-08):* the phase was inverted on first delivery - `cos(16*theta)` peaks every 22.5 deg, which is
  exactly where a leaf sits (lower row 0 + k*45, upper row 22.5 + k*45), so `+0.45*cos` put the trough UNDER each leaf
  and the ridge in the gap, and left the upper leaf bases seated on air. Now `-0.45*cos`: full radius under each leaf,
  the dip 11.25 deg away. Capital hero rel-std went 0.6202 -> **0.6570** on the fix alone.
- **Leaves on an explicit spine** (`leaf_spine()` + new `spine=` argument on `orn_lib.acanthus_leaf`): the body
  follows the bell surface with a growing outward offset (`proud` 0.14 R lower / 0.13 R upper), then the last
  26-28 % of the length is a circular arc of **100 deg (lower) / 90 deg (upper)** that carries the tip outward and
  DOWN. Leaf tips now stand **0.40 m proud** of the bell (was 0.29 m, and the body was inside it), at radius
  1.31 m (lower) / 1.37 m (upper) against an abacus whose flats are at 1.06 m and corners at 1.50 m — so the
  ornament fills the abacus instead of sitting pinched under it.
- **The upper row was lifted to 0.44 H** (was 0.345 H), clear of the lower row's tips at 0.40 H, which opens a real
  annular notch ~0.35 m deep between the two tiers. That notch, not an overhang shadow, is what reads at hero
  distance: with the sun at el 7.4 deg a 0.3 m overhang throws its shadow 2.3 m down the shaft, so only enclosed
  voids and turned-away normals go dark.
- Leaf cross-section flattened (`bulge` 0.075 -> 0.032 R), 5 lobes at 0.26 depth, `mid_dip` 0.078 R cupping.
- **Volutes** shrunk from 0.17 H to 0.112 H radius (0.58 m across, was 0.88 m), 2.25 turns with a taper of 0.55 and
  a new **eye button** so they read as rolled scrolls, not lengths of pipe; pushed out to 1.38 R, eye at 0.805 H.
  Inner helices 0.055 H at 1.245 R.
- `union_blob` smoothing **2 passes at 0.50 -> 1 pass at 0.30** (the old pass rounded the leaf edges and undercuts
  away), adaptivity 0.40 -> 0.35.
- Per-variant styles now drive the new parameters (`arc_mul`, `proud_mul`) as well as widths and volute size, so the
  three variants still differ in silhouette, not only in weathering seed — see `orn4_variants_capital_rotunda.png`.

| | LOD0 | LOD1 | LOD2 | instances | master tris |
|---|---|---|---|---|---|
| capital_rotunda | 100k -> **64k** | 20k -> **16k** | 344 | 16 | 1.60 M -> **1.02 M** |
| capital_inner | 80k -> **48k** | 16k -> **12k** | 344 | 8 | 0.64 M -> **0.38 M** |
| capital_colonnade | 48k (trim, kept) | 16k -> **12k** | 344 | 114 | 5.47 M (unchanged) |

Measured on the hero 1:1 crop (Cycles 48 spp, rig r09, same session for before and after):

| box | before | after | reference (ref 169) |
|---|---|---|---|
| full crop (bbox + 22 px), rel std | 0.2650 | **0.2857** | — |
| capital only, 44x34 px, rel std | 0.5721 | **0.6570** | 0.428-0.459 (photo tone curve) |
| capital only, alternations >= 0.05 | 3 | **3** | 6-7 |
| keystone only, 22x24 px, rel std | 0.2571 | **0.3672** | — |

**Honest limit.** The tier count did not move: 3 alternations before and after. What did move is the depth and the
darkness of the accents inside the leaf zone (see the x6 crops on the sheet — the round-3 capital is a pale mush
with faint scratches, this one has black slots). The remaining distance to the photograph is recess dirt: QA-03-15
names "shading, recess dirt" alongside the geometry, and the reference's dark accents are mostly dirt in the leaf
recesses, not shadow. The geometry now has the recesses to hold it — see the hand-off below.

### Cavity attribute for materials (new) — what to read

`orn_lib.vertex_cavity()` bakes a per-vertex ambient occlusion into the mesh. **Exact contract for the materials
shader:**

| | |
|---|---|
| attribute name | `cavity` |
| domain | `POINT` (per vertex) |
| type | `FLOAT_COLOR` (greyscale: R = G = B = the value, A = 1) |
| range / sense | **1.0 = fully open surface, 0.0 = fully enclosed recess** — so multiply albedo by it (or by `mix(dirt, 1, cavity)`), never by `1 - cavity` |
| carried by | **LOD0 and LOD1** of `capital_rotunda`, `capital_inner`, `capital_colonnade`, `rosette_ceiling`, `keystone`. LOD2 has none. |
| read it with | a Shader `Attribute` node, Type = Geometry, Name = `cavity`; use the **Color** output (or Fac, same value) |
| marker property | each object also carries `cavity_attr = "cavity"` so a script can detect it |
| measured means | rotunda capital 0.45 (min 0.00), colonnade 0.46, rosette 0.78, keystone 0.79 |
| sampling | 10 cosine-distributed rays per vertex over a radius of 6 % of the object diagonal, deterministic (same value on every rebuild) |

This matters because **LOD0 is the render LOD and has no UVs**, so a vertex attribute is the only channel a shader has
for darkening ornament recesses on the geometry that is actually rendered. `finalize_asset(..., ao=True)` also bakes an
**AO map** for LOD1 next to the normal map, so `ao_map` is no longer empty for those five types
(`assets/textures/orn/ORN_*_ao.png`, tangent-space normals in `ORN_*_nrm.png`).

**Both are inert today** (noted in the round-4 code review): `mat_build.py` creates no `ORN_NORMAL` / `ORN_AO` image
nodes, so `build_master.orn_material_for()` returns `None` and no shader reads a `cavity` Attribute node. The data is
delivered and waiting for materials round 5.

### QA-03-8 (ornament half) — coffer / rib rosettes
The round-3 rosette was a lathe with a `cos(12*theta)` radius wobble: a smooth 12-point star with **no undercut
anywhere**, which is exactly the "flat inset outline" QA saw. Rebuilt as real geometry: a sunk back disc with a
raised rim, a ring of 8 modelled petals (`rosette_petal()`, flat for 66 % of their length then the tip lifts),
a second ring of 8 rotated half a pitch, a 0.045 m annular groove and a beaded central boss.
- **Relief 0.14 m -> 0.21 m on a 0.60 m rosette (0.35 of the diameter)**, petal tips 0.082 m off the disc floor,
  back face at y = 0. Raised from 0.155 m after ARCH deepened the coffer interiors to 0.55 m (saucer) / 0.38 m
  (barrel): a 0.155 m boss disappears at the bottom of a 0.55 m box. Delivered LOD0 y-extent measured from the meshes:
  **v1 0.210 m, v2 0.197 m, v3 0.225 m** (the noise displacement averages out; an earlier note said 0.29 m - wrong).
  So it sits **inside** a 0.55 m saucer coffer with >= 0.32 m to spare and never breaks the rib face.
- 3 variants (was 2): 8+8 petals at 0.60 m / 10+10 at 0.56 m / 6+6 at 0.62 m. LOD0 20k -> **26k** tris, LOD1 5k.
- Depth provenance: ref 083 and `ornament_crops/coffered_ceiling_1-3` are all straight-up shots in which the rib
  rosettes are 0.45-0.60 m across and read as bosses roughly a quarter to a third of their diameter proud. There
  is no photograph in the set that measures a rosette in profile, so 0.35 of the diameter is a reasoned choice from
  the boss/shadow ratio in `coffered_ceiling_1`, not a measured section. Flagged as such.

**The rosettes do not appear at cam04 at all, and it is not the asset.** All 24 `SOCKET_rosette_ceiling_*` point
radially OUTWARD (`dot(+Y, radial) = 1.000`), so every rosette projects into the masonry. Full write-up, the two
different corrections the two socket groups need, and a proof render are in `docs/sockets.md` under
"ORN request 2026-09-08". `renders/previews/ornament/orn4_cam04_rosette_fix2.png` shows the 8 ring-1 rosettes
appearing inside their coffers once the frames are corrected.

### Carried defect — keystone depth
Two things were missing. (1) There was **no voussoir**: the mask sat straight on a 0.10 m plate flush with the
archivolt, so at hero distance it was a pale nub with nothing to cast a shadow — ref `keystone_mask_1/2` show a
wedge block breaking forward out of the archivolt roll with a moulded cap under the frieze. (2) The mask was all
convex blobs and its eye/mouth dents (0.03 / 0.09 m) were wiped by `smooth=2` on a 0.006 m remesh.
- New **tapered voussoir**, 0.43 m wide at the springing to 0.60 m under the cap, standing **0.30 m proud** of the
  archivolt face, plus a 0.075 m moulded cap.
- Mask nose now **0.634 / 0.647 / 0.677 m proud** of the archivolt by variant (was 0.50 m). Brow ridge moved forward and up so it **overhangs**
  the eye sockets. Dents: eye 0.03 -> **0.072 m**, mouth 0.09 -> **0.115 m**, nostrils added at 0.035 m.
- Mane 14 thin leaves -> **10 bold** ones (0.30 m long, 0.036 m thick, `mid_dip` 0.022) standing clear of the face.
- `union_blob` voxel 0.006 -> 0.005, smoothing 2 passes at 0.50 -> 1 at 0.25.
- *Review fix (2026-09-08):* the moulded cap was 0.34 m deep at y = 0.15, i.e. it reached to y = -0.02, so
  `origin_bottom_centre(y_mode="back")` re-originned off the mounting plane and the whole keystone stood 2 cm proud
  of the archivolt. Cap depth is now 0.30 m and all three variants measure local y_min = 0.0000.
- 3 variants (was 2), sized +/-4 %. LOD0 50k tris unchanged. Hero-crop rel std **0.2571 -> 0.3672**.

### Tools added this round (ORN-owned)
- `scripts/orn_r4_render.py` — the socket-frame look-dev + hero 1:1 crop rig described above.
- `scripts/orn_tier_stats.py` — vertical luminance profile, relative std and alternation count for a hero crop.
- `scripts/orn_r4_sheet.py` — assembles `orn4_sheet.png` (pure PIL, no Blender).
- `orn_lib.vertex_cavity()`, `orn_lib.acanthus_leaf(spine=, mid_dip=)`, `finalize_asset(cavity=)`.

## Round 5 (2026-09-09) — rotunda frieze rinceau, attic-panel relief audit, LOD2 budget fix

No renders this round (QA held the GPU). Everything below is measured on meshes and socket empties with
`scripts/orn_r5_stats.py` (socket census / frieze-run fit / band metrics / LOD tri table / per-instance variation),
`scripts/orn_r5_reliefcost.py` (deeper-relief cost) and `scripts/orn_relief_check.py`.

### 1. The 24 rotunda frieze sockets, and what belongs on them

`scripts/orn_r5_sockets.py` on `assets/architecture.blend`: the 126 `frieze_run` sockets split cleanly.

| host | subtype | run_length | n | z | who owns it |
|---|---|---|---|---|---|
| rotunda | `rinceau` | **5.913** | 8 | 28.55 | ORN — the ressaut FRONT faces |
| rotunda | `rinceau` | **2.999** | 16 | 28.55 | ORN — the two ressaut RETURN faces |
| rotunda | `greek_fret` | 94.3 / 97.3 | 4 | 13.42 | ARCH (colonnade architrave meander) |
| rostra | `greek_key` | 1.42-6.18 | 50 | 3.70 | ARCH geometry (`ARCH_site_rostra_meander_*`) |
| planter_box | `greek_key` | 5.18 | 48 | 16.65 | ARCH geometry (`ARCH_colonnade_*_box_*_meander`) |

So the 24 are exactly the ressaut faces, and that is exactly where the reference puts ornament: sheet line 183-184
(DPR) "angled impost blocks with a rinceau pattern protruding from a **plain frieze**", sheet #13 "frieze … rinceau
on ressauts, plain between", "Rinceau = scrolling acanthus with rosette bosses". The plain field between the
ressauts stays plain — which is also what ARCH's r4b measurement of ref 169 requires ("frieze + architrave read as
ONE plain surface").
Geometry of one ressaut, derived from the three sockets (`orn_r5_sockets.py`): the returns run 3.00 m from the wall
at r 22.16 out to r 25.14, the front face is 5.913 m; every run is inset **0.337 m** from the corner arris (solved
from the two run lines), so each panel has a plain 0.34 m margin at the corners — a real frieze panel, not a wrap.

**The colonnade `frieze_run` asset does NOT fit.** `ORN_greek_key` is a 0.60 m unit on a **0.52 m** band with a
4.5 cm incised fret; the rotunda band is **0.90 m**. Stretching it 1.73x would give a fret bar 9 cm wide and a band
that reads as a meander, not a rinceau — wrong ornament for this course. Hence a new asset.

### 2. `ORN_frieze_rinceau` / `ORN_frieze_rinceau_return` (new)

One full-run panel per socket rather than a repeating unit, because `build_master.py` places ONE object per socket
and has no array step; the two run lengths therefore get their own type. **Deviation from docs/sockets.md logged
here**: the origin is the **RUN START** (local x = 0 = the socket, geometry to x = run_length), not the footprint
bottom-centre, because the socket sits at the start of the run. Back face y = 0 = the frieze face, band bottom z = 0.

| asset | length | mismatch vs socket | band | carved field | tris LOD0/1/2 | budget |
|---|---|---|---|---|---|---|
| `ORN_frieze_rinceau` v1-v3 | 5.913 m | **0.2 mm** | 0.90 | 0.75 (0.075 margins) | 48000 / 9000 / 900 | 48000/9000/900 |
| `ORN_frieze_rinceau_return` v1-v3 | 2.999 m | **0.4 mm** | 0.90 | 0.75 | 24000 / 4500 / 450 | 24000/4500/450 |

Band metrics (`orn_r5_stats.py`, ray-cast grid 520 x 100 on LOD1):

| variant | coverage of the 0.90 m band | proud above the frieze face p50 / p90 / max | clearance to the architrave crown | lateral shadow at max proud |
|---|---|---|---|---|
| rinceau v1 / v2 / v3 | 29.5 / 29.7 / 27.0 % | 69 / 89 / 120 mm · 65 / 88 / 123 · 69 / 86 / 114 | 39.8 / 36.8 / 46.4 mm | 88.9 / 91.2 / 84.1 mm |
| return v1 / v2 / v3 | 29.1 / 28.3 / 25.6 % | 69 / 89 / 118 · 66 / 89 / 124 · 68 / 86 / 110 mm | 42.1 / 35.7 / 50.4 mm | 87.2 / 92.0 / 81.1 mm |

Why those numbers: the frieze face is at d 0.34 and the architrave crown at d 0.50 (arch r4b profile), so **nothing
on this band may project more than 0.160 m**; the builder caps at 0.125 m and the measured max is 0.110-0.124 m, i.e.
34-50 mm of clearance, guaranteed by a Y-clamp in the builder rather than by hope. At the hero sun (az 118.5 / el
7.4, face normal az 82, so 36.5 deg off the face) an element standing p metres proud throws `p * tan 36.5 = 0.74 p`
of **lateral** shadow, so the p90 relief writes an 66 mm shadow line beside every scroll: that, not a cast shadow
from above (0.16 p vertically), is what makes the band read. The ornament is sunk **15 mm into the frieze face**
(`RIN_EMBED`) so nothing floats off the wall.

Design: a continuous undulating stem (that is deliberate — one connected shell decimates to LOD2 cleanly, which is
what the attic panels failed at), two alternating scrolls per repeat, a petalled patera boss in each scroll eye,
three acanthus leaves per springing, a berry cluster and a counter-tendril, and a palmette terminal at each end of
the run. 6 repeats on the front, 3 on the return. Variants differ in stem amplitude, scroll radius, boss diameter,
leaf length and phase (`RIN_VARIANTS` in `scripts/orn_build.py`); per-repeat jitter (+-7 % radius, +-9 % leaf length,
+-8 deg leaf angle) means no two scrolls in a run are identical.
Built with `--no-bake`: a Cycles normal bake is GPU work and QA held the GPU. **LOD1 carries the relief
geometrically** (1523 tris/m front, 1500 tris/m return); the normal-map bake is an open item for round 6.

### What the lead must add to `scripts/build_master.py` (ORN does not edit that file)

`ORN_COLL` entry:

```python
    "frieze_run": "ORN_frieze_rinceau",   # rotunda ressaut faces only; the guard below picks front vs return
```

and, in the socket loop beside the existing `urn` / `finial` / `drum_band` special cases (before the
`if coll_name is None:` skip):

```python
        if t == "frieze_run":
            # only the 24 rotunda ressaut faces carry ornament; the other 102 frieze_run sockets are ARCH's own
            # greek-key / greek-fret band geometry (docs/sockets.md, docs/arch_notes.md)
            coll_name = None if sk.get("subtype") != "rinceau" else (
                "ORN_frieze_rinceau" if float(sk.get("run_length", 0.0)) > 4.0 else "ORN_frieze_rinceau_return")
```

LOD object names: `ORN_frieze_rinceau_v{1,2,3}_LOD{0,1,2}` and `ORN_frieze_rinceau_return_v{1,2,3}_LOD{0,1,2}`.
No `ROT_Z_FIX` entry: the socket +Y is the face normal and the asset projects +Y. Nothing to hide — ARCH models no
geometry on the rotunda frieze band. Expected result: 24 instances, 8 x 9000 + 16 x 4500 = **144 k tris at LOD1**,
8 x 48000 + 16 x 24000 = **768 k at LOD0**.

### 3. Attic panels: relief depth is not the deficit (measured)

`orn_relief_check.py` on `ORN_attic_panel_v2_LOD0` (ray-cast 260 x 120 from +Y):
depth above the back plane p50 **0.306** / p90 **0.517** / max **0.558** m on a 0.16 m slab, i.e. relief above the
slab face p50 **0.146** / p90 **0.216** / max **0.398** m; 84.7 % of the field stands >= 6 cm proud, 54.7 % >= 25 cm.
The reference sheet's nominal Zimm relief depth is **0.25 m** — the panel is already at 1.6x that at its deepest.
LOD1 tracks LOD0 to within 2 mm at every percentile (p50 0.304 vs 0.306), so the LOD1 the master uses is not the
problem either.

Cost of going deeper anyway (`orn_r5_reliefcost.py`, relief scaled about the slab face; tris scale with the true
outward-facing surface area, 91.86 m2 today):

| deepening | max proud | front area | tris at constant density LOD0 / LOD1 / LOD2 | vs budget 150000 / 24000 / 2400 |
|---|---|---|---|---|
| x1.00 | 0.398 m | 91.86 m2 | 142897 / 24000 / 2400 | ok |
| x1.25 | 0.497 m | 98.23 (+6.9 %) | 152813 / 25665 / 2567 | **over on all three** |
| x1.50 | 0.597 m | 104.90 (+14.2 %) | 163182 / 27407 / 2741 | over |
| x2.00 | 0.796 m | 118.84 (+29.4 %) | 184878 / 31051 / 3105 | over |

So a deeper relief is cheap (7 % of tris for +25 %) but it is **not built**: it would double the reference depth and
it does not fix what is actually missing. What is missing is measured in the same report: at the hero sun only
**5.3 %** of lit samples are shadowed by the relief itself and mean sky-openness is **0.743** — because the sun is
36.5 deg off the face normal and 7.4 deg up, a proud block sheds 0.74 m of shadow per metre of depth *sideways* and
0.16 m *downward*. The panel has plenty of proud depth and almost no **undercut** (surfaces turned away from the
sun). Recommendation for a render round: undercut the figures (arms, drapery edges, the horse) rather than raise
them; N.L rel-sd is 0.337 today and undercuts move it without touching the tri budget.
Framing, for whoever chases "the panel is half of QA's hero attic box": ARCH's attic band is 7.10 m tall (base 0.90
at z 31.20, frame 5.40, cornice 0.80 to z 38.30) and the ORN panel field is 4.51 m — **63.5 % of the band, 83.5 % of
the 5.40 m frame opening**. The rest of that box is plain ARCH masonry and cornice, not panel.

Per-instance variation actually available (`orn_r5_stats.py` section 5): 8 `attic_panel` sockets carry **8 distinct
`variant_seed` values** and a `design` A/B/C property, against 3 ORN designs; `build_master.py` copies the seed to
`ob["instance_seed"]`, which `MAT_ornament_concrete` reads (`scripts/mat_build.py` line 36-42) to decorrelate the
weathering. The 24 rinceau sockets likewise have 24 distinct seeds against 3 variants. Geometry repeats 2-3 times
per design; the weathering does not repeat at all.

### 4. LOD2 budget fix (open issue closed)

The open issue understated it: **all three** attic panels were over the 2400 tri LOD2 budget, not just v2 —
v1 **15343**, v2 **5231**, v3 **6495** tris (collapse decimation stalls at ~4 faces per shell and the clamped relief
leaves thousands of shells). `scripts/orn_r5_lod2fix.py` voxel-remeshes LOD1 at 0.10 m to weld the shells, then
collapses: v1 15343 -> 24584 -> **2400**, v2 5231 -> 23676 -> **2400**, v3 6495 -> 23680 -> **2400**. Only the mesh
data is replaced, so the object name, material, custom properties and viewport state are untouched and
`build_master.py` sees no change. Silhouette kept: bbox depth 0.63 -> 0.62 / 0.56 -> 0.56 / 0.58 -> 0.58 m and max
vertex y within 5 mm of LOD1. Every ORN asset is now inside its tier budget (`orn_r5_stats.py` section 4).

## Open issues (ORN)
- ~~`ORN_attic_panel_v2_LOD2` decimates to 5598 tris instead of the 2400 budget~~ **fixed in round 5** (and it was
  all three panels, v1 at 15343): `scripts/orn_r5_lod2fix.py` welds the shells with a 0.10 m voxel remesh first.
- `ORN_frieze_rinceau` / `_return` were built `--no-bake` (QA held the GPU in round 5): LOD1 has no normal map and
  no AO map. Re-run `orn_build.py --only frieze_rinceau,frieze_rinceau_return` without `--no-bake` in a round that
  may use the GPU.
- The rinceau band has not been seen in a render yet. Its numbers (coverage 25.6-29.7 % of the band, max proud
  110-124 mm, 34-50 mm of clearance under the architrave crown) are ray-cast measurements on the asset, not a
  photo comparison; it needs a cam02/cam04 pass and a crop against entablature_1-3 (047, 054, 017).
- `corner_scroll` is 1.78 m over the volute rolls, not the 1.50 m the defect quotes; 1.50 is the nominal block width
  (`unit_length`) and the rolls overhang it, as they do in ref 085.
- The rostra band units are modelled as a slab standing 8 cm off the wall. If ARCH's podium top course already has a
  recessed field, the slab will double up - say so and I will drop the backing to 3 cm.
- Attic panels: fixed under QA-01-10 (13-15 figures, 61-64 % coverage, 0.26 m of relief after the remesh). Only three
  scan sources exist, so the three designs still share the scan groups (mirrored / re-ordered); the 8-10 modelled
  figures per panel are what makes them read as three different compositions.
- Winged figure: the cornucopia horns stick out sideways; should curl up in front of the hands. Wings read as two
  tall fluted slabs (right silhouette from cam 04, no feather detail).
- Keystone: the mouth/eye boolean recesses barely show after the remesh; the mask reads as a lion-ish mask with a mane
  at 30 m, not close up.
- Figures have no facial features (a smooth head + hair mass); fine at the 25-115 m QA distances, not for close-ups.
- Drum band unit: the scale cushion is a honeycomb of shallow domes; the real band is imbricated (overlapping)
  scales. ARCH may prefer to model the band itself with a texture.
- Capital: the abacus fleuron/figure and the astragal are simplified; the colonnade and inner capitals share the
  rotunda generator with different proportions (the real colonnade capital has slightly different leaves).
- AO maps: baked from round 4 for capitals, rosettes and keystones (`ao_map` set); still empty for maidens, attic
  panels/figures, urns, mouldings - say the word and they get the same `finalize_asset(..., ao=True, cavity=True)`.
- Capital close-up honesty: at look-dev range the leaves still read as smooth tongues rather than the dense, deeply
  lobed acanthus of `corinthian_capital_1-3`. The design is correct at the 34 px hero scale and at cam02/cam04
  distance; a close fly-through pass would want a real sculpted leaf (more lobes, a curled-under edge roll, a
  carved midrib) rather than a lofted shell.

## Requests
- **ARCH / lead - maiden socket**: the socket must be at the figure's FEET, which are at the level of the box base
  (top of the colonnade entablature / capital block), NOT on the box top rim: photos 163/187 show the figures standing
  beside the box with the rim at shoulder height. The asset assumes the box rim is **3.55 m above the socket** and
  the box's vertical corner edge at local (0, -0.32); +Y = the direction the back faces (outward, on the corner
  diagonal). If ARCH's box is a different height, tell me and I re-pose (one parameter, `rim_z`).
- **ARCH - socket types**: I deliver `urn` (3.0 m podium urn), `urn_niche` (1.6 m attic-corner urn) and `urn_tub`
  (pylon planter) as three types; `attic_panel` origin = back-face bottom-centre (+Y = face normal, the panel is
  0.16 m slab + up to 0.40 m relief, field 10.5 x 4.5); `keystone` origin = back-face bottom-centre of the 0.62 m
  back plate; `rosette_ceiling` projects +Y from its back face; `winged_figure` faces -Y (toward the rotunda centre);
  moulding units (`dentil`, `egg_and_dart`, `greek_key`, `rosette_band`, `modillion`, `anthemion`, `drum_band`) are
  1 m along X with the origin at the back-face bottom-centre, projecting +Y, for `frieze_run`-style arrays.
- **Materials agent**: LOD1 objects carry `normal_map` (tangent space, OpenGL +Y convention as Blender bakes it);
  LOD0 has no UVs (geometry carries the detail), LOD2 has neither.
- **Lead**: the reference crops were viewed for every asset; render-vs-crop sheets are in
  `renders/previews/ornament/compare_<asset>.png` and `compare_sheet.png` (my folder, since renders/qa_comparisons
  is QA's). The maidens and capitals are the two assets that got the most iteration (t01-t11 previews in the same
  folder); everything else is at "reads correctly at QA distance" level and ready for a polish round after the first
  master assembly shows what actually matters in frame.
