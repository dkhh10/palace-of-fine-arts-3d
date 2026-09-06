# Decisions log (lead / art director)

Format: date · decision · why · consequences. Newest at the bottom.

## 2026-09-06 · Phase 0

- **Blender 5.2.1 LTS, not 4.x.** It is what is installed. Engine ids are `BLENDER_EEVEE` (= Eevee Next) and `CYCLES`;
  sky texture is `MULTIPLE_SCATTERING`; AgX available. Everything in CLAUDE.md "Environment".
- **Reuse the 214-photo Wikimedia/Flickr corpus and OSM footprints gathered in attempt 2** instead of re-downloading.
  Licensed (Commons), already indexed (`reference/photos/index_wikimedia.csv`, sources per row). The reference agent
  curates, names canonical views, and may add targeted downloads (golden hour views, weeping maidens, concrete close-ups).
  Reference photos are gitignored (175 MB) and read from the main checkout by absolute path.
- **Art target = the user's own reference image** `reference/photos/user/user_wide_midday.png` for composition and
  proportion, re-lit to golden hour. Muted variegated ochre concrete, dusty terracotta-rose columns, dense mature
  trees, distant colonnade wings, still green-tinted lagoon with broken reflections. No people, no cars.
- **Coordinate convention**: origin = rotunda floor centre, +Y toward the lagoon (east), -X north. OSM data converted
  with `common.osm_to_world`. z = 0 is the rotunda floor slab; water is ~1.3 m lower (attempt-2 measurement, to confirm).
- **Golden hour = MORNING, sun from the east-south-east (azimuth ~110-125 deg), elevation 5-8 deg.** The brief asks for a
  west-northwest azimuth "so the rotunda face toward the lagoon is warmly lit", but the lagoon lies EAST of the rotunda
  (OSM, satellite, every photo: the classic view looks west across the water). A WNW sun would put the hero face in
  shadow and silhouette the rotunda. The stated goal (warm direct light on the lagoon face plus still reflections)
  is only physically possible with a morning sun. The lighting rig is parametric (real date/time via Sun Position),
  so an evening WNW variant is one parameter change and will be rendered as an alternate at delivery.
  Candidate real date/time: late Oct to Nov 2026, ~07:40 PST (lighting agent computes and documents the exact value).
- **Sun Position and Sapling Tree Gen extensions installed headless** and enabled in user prefs. Bagapie/Modular Tree
  exist on extensions.blender.org if the environment agent needs them (`common.ensure_extension`).
- **Weeping maidens**: sculpting by hand is impossible headless. Plan: posed capsule/skin-modifier body proxy + cloth
  simulation of a draped sheet baked to a mesh, then multires displacement for folds. Ornament agent owns this and
  may propose alternatives. The attempt-2 approach (public-domain classical statue scans as stand-ins) was rejected
  by the user; the figures must read as Ulric Ellerhusen's maidens: back to the viewer, arms on the box rim, head bowed.
- **Team mechanics**: one branch + worktree per specialist via the Agent tool's worktree isolation; lead merges to main.
  Blend files are committed (binary, ~MBs). Renders/previews are committed as evidence; raw photos are not.
- **QA cameras**: six canonical views defined in `scripts/qa_cameras.py` (lead-owned). Initial positions are estimates;
  the reference agent proposes refinements matched to specific photos, lead applies them.
