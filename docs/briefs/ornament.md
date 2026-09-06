# Brief: Ornament and Sculpture Modeler

You own `assets/ornament.blend` (collection `ORN`) and `scripts/orn_*.py`. Read, in order: `CLAUDE.md`,
`docs/reference_sheet.md` (ornament catalog), `docs/sockets.md` (the frame contract, binding), `docs/tech_notes.md`,
`scripts/common.py`. Study the crops in `reference/photos/ornament_crops/` (Read tool shows images) before modelling.

## Deliverables
1. `scripts/orn_build.py` (+ `scripts/orn_lib.py`) rebuilding `ORN` idempotently and saving `assets/ornament.blend`.
   Heavy generation (cloth sims, bakes) may be split into cached steps that save intermediate meshes in the same file,
   but a clean rebuild must work with one command.
2. Assets, each in sub-collection `ORN_<type>` with `_LOD0/_LOD1/_LOD2` and 2-3 `_v<n>` variants where the catalog
   says instances are visible together (maidens, urns, capitals at least): capital_rotunda, capital_inner,
   capital_colonnade, base_* (if ARCH requests), maiden, urn (each type), attic_panel (each distinct panel design),
   attic_figure, keystone, finial, rosette_ceiling, and the linear mouldings as unit meshes (dentil, egg_and_dart,
   greek_key, rosette_band, modillion, anthemion) 1 m long unless the sheet says otherwise.
3. Baked normal (and where useful cavity/AO) maps from LOD0 sculpt-level detail onto LOD1, saved as PNG under
   `assets/textures/orn/` with relative paths. Materials: assign `MAT_ornament_concrete` (placeholder until the
   materials library exists) so the materials agent can hook the baked maps: put the image texture nodes in the object's
   material slot named `MAT_ornament_concrete_<type>` that duplicates the library material... simpler: store the map
   paths as custom properties `normal_map`, `ao_map` on each LOD1 object and let the lead/materials agent wire them.
4. `docs/ornament_notes.md`: per asset: size, origin frame, tri counts per LOD, variants, how it was generated, and a
   preview image path. Previews: `scripts/orn_preview.py` renders each asset at 1280x720 Eevee from a fixed close camera
   with a neutral grey ground and the placeholder sun into `renders/previews/ornament/`, plus one contact sheet.

## Approach guidance (you may deviate if you find better, say so in the notes)
- Corinthian capitals: bell + two rows of eight acanthus leaves (each leaf a lofted profile with lobed silhouette,
  curled tip, solidify + subdivision), cauliculi, corner volutes (spiral sweep), inner helices, concave abacus with
  fleuron. Compare the rotunda capital vs. the colonnade capital in the crops; they differ in proportion. LOD0 via
  subdivision; LOD1 decimated/rebuilt with the baked normal map; LOD2 a simple bell.
- Weeping maidens (Ellerhusen): a draped standing female figure, back to the viewer, arms resting on the box rim, head
  bowed. Build a posed body proxy (metaballs or skin-modifier armature stick figure, converted to mesh), drape a cloth
  sheet over it with the cloth simulation (verified headless in tech notes; pin a vertex group at the shoulders and hands),
  bake the drape to a mesh, add a head (bowed, hair as a smooth mass) and forearms/hands on the rim, then smooth and add
  fold detail with a displacement (noise along the fold direction). Three variants with different sim seeds. Height per
  the sheet. The figure must read as a specific sculpture, not a ghost sheet: check the silhouette against the crops.
- Zimm attic relief panels: figures in high relief on a rectangular slab. You may compose them from the public-domain
  classical relief scans in `reference/scans/` (sources in `sources.json`, e.g. the Parthenon metope and Trajan slabs)
  by cutting, scaling, mirroring and embedding them into a panel with a border, then decimating and baking; supplement
  with simple modelled elements (horses, shields) where the crops show them. They are read at 30 m; silhouette and shadow
  matter more than anatomy.
- Urns, finials, rosettes, keystone masks: lathe/profile sweeps plus displacement.
- Every asset: origin per `docs/sockets.md` (bottom-centre, +Z up, +Y outward), real size, scale applied, quads where
  practical, smooth shading, `bevel`/rounding so nothing is knife-sharp. Triangle budgets in sockets.md.
- Use Cycles bake in background mode for normal maps (recipe in tech notes). Validate each bake by rendering LOD1 next
  to LOD0 in the preview.

Commit after each asset lands. Budget: capitals and maidens are the two assets that matter most for the hero view;
do them first and get them right before spending time on small mouldings.
