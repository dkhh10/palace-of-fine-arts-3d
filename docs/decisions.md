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
- **Sun moment fixed: 2026-11-08 07:30 PST → azimuth 118.1°, elevation 7.8°** (NOAA via the Sun Position module, table in
  docs/tech_notes.md). Evening alternate for delivery: 2026-10-25 17:30 PDT → az 247°, el 8.4°.
- **Verified headless recipes** (tech_notes.md): Eevee/Cycles render, Sapling tree generation (needs an empty active
  object), cloth simulation + evaluated-mesh bake (for the maidens' drapery), Sun Position NOAA call.
- **Socket contract** written in docs/sockets.md before ARCH and ORN start, so instancing in Phase 3 is mechanical.
- **Specialist briefs** live in docs/briefs/ so each agent's instructions are durable and reviewable.

## 2026-09-06 · Phase 1 gate (reference sheet accepted)

- **Reference sheet accepted** (docs/reference_sheet.md, 499 lines, sources cited). Biggest corrections vs attempt 2:
  dome 33 m Ø × 7.6 m rise (was 36 × 11.5), drum 3.5 m, attic 7.1 m, apothem 21.5 m, column pair 4.5 m, a 4.3 m podium
  under the pedestals, colonnade ~5 m shorter, 52 maidens of ~4.5 m on 13 boxes, attic corner figures 6.7 m.
- **The user's target image is composition/mood only.** Its dome is ~25% too wide and its drum a third of the real height
  (measured against refs 085/022/070). Proportions come from photos; framing, light and colour from the user image and
  ref 169 (a real golden-hour photo from the same spot).
- **Sun moment revised to 2026-11-10 07:30 PST → az 118.5°, el 7.4°** to match ref 169. Evening alternate 2026-10-20 17:45 PDT (az 251, el 6.9).
- **QA cameras replaced** with the sheet's photo-matched set (hero at (-16, 113.9, 1.0), 31 mm, shift_y 0.17).
- **Material names** follow the sheet: MAT_column_rose, MAT_dome_membrane (semi-gloss urethane roof), MAT_concrete_podium,
  MAT_column_tan_inner, MAT_plaster_ceiling, MAT_drum_band, plus MAT_concrete_inner. Placeholder albedos halved to the
  measured values (attempt 2's stone was twice too bright).
- **Agents hit the API session limit** at ~14:30 (reset 18:30). Phase 2 runs five agents in parallel and will burn
  through budget faster; if limits recur, stagger them (arch + materials first, then ornament + environment + lighting).
- **User delegated the gate decisions** ("only have me weigh in where you're not sure"). Lead confirms: morning sun
  primary (evening variant rendered at delivery); user image = composition/mood only; six QA viewpoints as in
  qa_cameras.py; ornament scope = the 18 catalog items minus lamps/signs/fences; public-domain relief scans allowed ONLY
  as heavily reworked raw material for the attic relief panels (never as figures); measured material direction; all five
  Phase 2 builders launched in parallel, resumed after any API limit.
- **2026-09-07 · Lighting and environment merged.** Sky node `sun_rotation = azimuth − 90°` (rotation 0 = +Y), verified by
  two agents independently; recorded in CLAUDE.md and tech notes. Hero camera moved from r = 115 m to the OSM shoreline
  (r = 101 m, (-14.1, 100.0), lens 27 mm) so water reaches the frame bottom as in the user image and ref 169; cam 02 pulled
  3 m onto land at (-30, 35).

## 2026-09-07 · Phase 2 gate

- **First master.blend assembled** (110 MB, 3840 objects, 8.5 M tris at viewport LOD1) by APPENDING all asset
  collections (not linking): materials can then be remapped to the library by name and LODs toggled per object.
  master.blend is a build product (1 min from `build_master.py`) and is gitignored.
- **Ornament instancing**: 336 sockets → 12 types instanced with variant by seed (attic panels by design letter);
  urn sockets pick `ORN_urn_niche` when size_hint ≤ 2 m; inner figures rotated 180° (ARCH socket +Y = facing,
  ORN asset +Y = back); drum band arrayed 113× around the drum. Frieze runs (28) not instanced yet (ARCH models the
  mouldings as geometry; no rinceau unit exists).
- **Lesson**: setting `matrix_world` on freshly created objects before they are evaluated silently left LOD0/LOD2
  copies at the origin; instances are now placed with decomposed location/rotation/scale.
- **Pending for Phase 3**: materials library (agent running); ARCH maiden sockets must move to the box base
  (ORN figures stand at box-base level with the rim 3.55 m above their feet); QA round 1 scores and defects.

## 2026-09-07 · Phase 3 start

- **Operating rules from the user** (model casting, max two builders, commit cadence, docs/status.md handoff, stop on usage
  limits, image downscaling) added to CLAUDE.md verbatim in spirit. Materials merged into main (4364e98).
- **QA-01-1 arbitration: the photographs override the reference sheet's forced 49.4 m apex.** Five photos measured with the
  same tool agree with each other (dome rise 0.195-0.30 W_a) and the aligned overlays show the stack below the attic cornice
  is right, so the error is local to drum + dome. The sheet's 7.6 m rise was derived from a foreshortened telephoto and the
  DPR's 162 ft total was then forced. Target: drum height 3.5 -> ~4.5 m (band r ~17.5, cornice r ~18.7), dome rise
  7.6 -> ~10 m (sphere r ~18.6), apex ~52-53 m; the architecture agent tunes within those ranges until
  `qa_silhouette.py align` puts the apex within 2 % of frame height of ref 169 AND ref 085 and the drum band + cornice ring
  are visible above the attic from cam01. Everything below the attic cornice stays as built.
- **Phase 3 order** (hero-view impact first, two agents at a time): wave 1 architecture (QA-01-1, maiden sockets to box base,
  QA-01-11 geometry, 14, 15, 16) + environment (QA-01-2, 3 geometry, 6, 7, 8, 19); wave 2 ornament (QA-01-10, 11, 13, 18) +
  lighting (QA-01-9, 12, 20 after materials); then materials fixes from the master hero if needed; then QA round 2 on Opus.
- **2026-09-07 · Podium Greek-key band (QA-01-11): ARCH geometry, not ORN units.** ARCH built the meander + rosette bosses
  as geometry standing proud of a recessed band face on all rostra walls and box bases, and it reads correctly in
  `arch_06_phase3_sheet.png`. ORN's `ORN_greek_key` / `ORN_rosette_band` units (8 cm backing slab) and
  `orn_lib.array_unit_along_run` stay in the library for future runs but are not instanced on the 98 greek_key sockets:
  arraying them would double the band (or need the slab thinned to an unmeasured recess) and add ~1400 objects.
- **Corner scrolls (QA-01-13)**: ARCH's 8 `finial` sockets with `subtype='volute_scroll'` already carry the frame ORN
  proposed, so build_master routes them to `ORN_corner_scroll`; no ARCH change.
- **Per-instance seed**: `PFA_instance` decorrelates by Object Info Random today; the materials agent is wiring the
  `instance_seed` object attribute into it so the lead's variant/seed choice is what the shader uses.
- **2026-09-07 · QA-02-1 (dome absent from cam05) is a camera-station error, not geometry.** ARCH's silhouette fit of ref 063
  (`scripts/arch_domecheck.py`, residual 24 px at 1920) puts the photo at az 104°, 115 m, ~40 mm; at that station the
  unmodified model gives rise/W 0.120 vs the photo's 0.118. The geometry sweep that would fake it from 71 m (attic -11 %,
  drum +50 %, dome +12 %) breaks the ref 063 match. cam05 re-stationed to (28.1, 111.8, 1.5), target (0,0,20), 40 mm.
- **Eevee preview regression** is the LOD0 render set (ORN instances 26.7 M + ENV 17.9 M of 50.4 M), not ARCH bevels (0.5 %).
  QA previews render at LOD1 (`common.set_lod(viewport=1, render=1)` in the Eevee pass); Cycles finals stay LOD0.

## 2026-09-08 · Polish rounds 2-3 (lead)
- **QA-04-11 / QA-02-17: no rotunda proportion change for cam02.** Architecture fitted ref 062 on four landmark rows: az 35.3°,
  D 91.7 m, 42.4 mm, chi² 4.09 (`arch_ref062_fit.py`, overlay `renders/qa_comparisons/arch_qa04_11_ref062_fit.png`). The dome
  cap can only show above the near attic beyond 76 m regardless of lens or podium radius, so the photo is simply farther away;
  same conclusion as ref 063 (115 m / 40 mm). cam01 passes three photos within 1 %, so the stack stays. Flagged for ENV: the
  OSM lagoon polygon puts the fitted station (-73, 55) in water while the photo's foreground is dry garden, i.e. the NE
  shoreline in site_local.json is probably short; verify against the satellite tiles.
- **cam02 station**: QA's probe (468 stations) chose (70.5, 25.6, 1.1) -> (0,0,21.1), 24 mm on the SSE shore path; the NE
  ref-062 view is not reproducible on this build without water in the foreground.
- **Ceiling rosette sockets**: 16 band sockets on the vertical inner face of the base ring (+Y = -radial), 8 coffer-floor
  sockets facing down; from the reference sheet's "base ring with rosette band above the inner arches".
- **Rib plate material**: rib plates (saucer ribs + 8 vault coffer plates) carry `MAT_plaster_ceiling_rib`, panels keep theirs,
  so materials can separate rib and panel tone (ref 083 ribs L 22-50 vs panels 93-130).
- **Watchdog**: liveness = CPU time at centisecond resolution; a Metal GPU render accrues ~0.3 s CPU per minute, so the old
  integer-second test killed three live renders (QA-03-1). GPU-utilization readings are useless here (70-80 % idle).
- **Exposure/chroma**: lighting r10 showed the AgX shoulder was killing saturation; bias 1.75 -> 1.25 with sky camera/glossy
  boosts x1.41 keeps the sky and lagoon. The shade collapse this caused (QA-04-2) is lighting r11's first item.
- **Materials direction after three "clean CAD" rounds**: stop tuning procedural noise; bring in photo-based grunge/streak/
  waterline maps at 0.3-3 m feature scale (materials r6). If the hero does not move in round 5, consider texture projection
  from the reference photos.
