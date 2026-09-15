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
- **2026-09-08 · QA-04-12 saved Eevee viewport state** (lighting r11): raytracing stays OFF in `apply_viewport_eevee` (measured: RT moved the vault 0.218 -> 0.218), `light_threshold`
  0.05 -> 0.01 is the fix (0.05 culled the eight vault emitters: viewport coffer 0.218 -> 0.319 in 7.9 s vs 12.2 s), shadow_pool_size 512 viewport / 1024
  preview (previews were logging "Shadow buffer full"), taa 8/16 kept. The Eevee vault blocker (QA-04-1) was the probe bake
  running on the Eevee cutoff rig; `light_probes.bake` now bakes the physical rig and restores the override, so
  `scripts/lead_build.sh` (build then bake) is the only valid master build.
- **QA-04-2 shaded-stone hue is albedo, not lighting**: three independent lighting levers (diffuse sky boost, cool shade fill at
  two elevations) all warm the shaded attic further or break the sunlit/near-water numbers; assigned to materials. cam03's
  reference (ref 128) is a midday photo, so its 0.5-of-ref shade target is not a golden-hour number: QA to re-base that test.
- **2026-09-08 · After QA round 5 (hero 3.28 for the third round): method change, not more of the same.** (1) The shade is starved
  structurally: the rig lights shade with sky x0.8 while the camera sees that sky x2.1 and the lagoon x5.25, so the diffuse
  sky is 2-5x weaker than the sky the photo shows and cam03's shade sits at 0.06 of sunlit vs the photo's 0.6. Lighting r12
  is told to fix the shade window first and may spend sunlit saturation down to 0.50 / R-B 110 to do it (the r10/r11 budget
  that forbade this is withdrawn). (2) Lighting and materials now run SEQUENTIALLY and measure on the merged master: the
  QA-05-3 coffer regression came from merging materials' in-coffer gradient onto lighting's re-tuned fill with neither owner
  measuring the combination. Geometry owners (architecture cornice/dentils, environment south wing / shore / cam03 ground /
  cam06 streets / NE shoreline) run in parallel with lighting; materials r7 (macro amplitude and anisotropy down from the
  r6 overshoot: attic lum 166 vs window 178-201, sat 0.64-0.84, streak anisotropy 0.64 vs photo 4.07) follows on the new rig.
  (3) If the hero does not move at round 6, the concrete gets a texture-projection pass from the reference photos.

## 2026-09-09 · Polish round 4 (lead)
- **QA-05-1 cam03 test re-based, not chased.** Lighting r12 proved the near-shaft box (150 150 420 720) is occluded from the sky and
  from the anti-sun hemisphere: 8x the whole diffuse sky moves it to 0.122 of sunlit while the walk in the same frame goes to 1.4x;
  a directional fill reaches 0.073. The hero's shaded attic, the same physics one bounce away, now measures 35.4 / 0.412 / 116.7 vs
  ref 115.0 / 29.5 / 0.425, so the rig is right and the box is wrong. QA round 6 measures cam03 shade on a sky-visible shaded shaft
  face (outer colonnade, the face toward the lagoon) with the same 0.30-0.70 window, and states the box. No owner tunes for the old box.
- **QA-05-7 sky_left / sky_top closed as measured-equal**: ref 169 warped into the render frame scores 0.921 vs the render's 0.922; the
  1.17 came from the raw-ref mapping's framing. Lighting's atmosphere stays.
- **Entablature (QA-05-6) accepted on the model's own cornice window**: texture std 0.73 of ref on QA's box (pass), row std 32.4 on QA's
  box / 43.1 on the model's cornice window because the model's cornice sits 1.04 m higher in frame than ref 169's under the round-05
  alignment. That is an attic-vs-entablature stack question against the arbitrated round-1 dome fit (ref 169/085 within 1 %); not
  re-opened this round. Drum ring: ref 062 would need -2.5 m radius; not changed for the same reason.
- **Near-water saturation is now materials' number.** Lighting's diffuse-only sky sockets do not touch camera or glossy rays, so the
  r12 rise 0.281 -> 0.418 is MAT_water_lagoon's murk under a brighter diffuse term; materials r7 cuts murk chroma by about a third.
- **Pin rule beats the band clearer; the cluster moves by measurement, not by sweep.** ENV r7's review fix pinned every hand-placed
  tree on all three frame bands (the r5 lesson) and the north-wing band fell 137.5 -> 91.9 (0.63 of ref, QA-04-6 again) because
  the hand-placed A/A2 cluster sits at x 0.76-0.985 of the hero frame while ref 169's dark mass is at x 0.71-0.76. Sweeping trees
  out of the band hid a placement error. Environment r8 (before QA round 6) re-derives the cluster's plan positions from ref 169 so
  the mass lands at 0.71-0.76 and the band clears with 0 trees moved or dropped by the clearer.
- **ENV r7's first panels were rendered on the main checkout's master** (env_r5_hero.py defaulted to the main root). Fixed to the
  worktree root; rule for every owner: the measure/sheet scripts default to `common.ROOT/master.blend` and the notes state which
  master (object count) a number came from.
- **2026-09-09 · After QA round 6 (hero 3.22 / 3.28 held, fourth flat round): the projection pass is triggered, but it needs a registered stack.**
  QA's per-course table (aligned overlay, 13.42 px/m) shows the render's attic storey at 0.70 and the capital at 0.65 of ref 169's,
  offsets +0.07 to +2.31 m and not rigid, while the outer silhouette fits within 1 %. That is a course-height error inside a correct
  envelope, and a projected photo cannot register on it. Order for polish round 5: (1) architecture r6 closes the attic storey, panel
  frame and capital rows against QA's table with the envelope held (the round-1 dome fit stays; the courses inside it move) and re-runs
  UVProj; (2) lighting r14 removes the r12 tint's violet flood on the non-hero cameras (hue 253 in shade on cam06 roofs; the shade
  window on the hero stays) and restores the reflection's warmth; (3) materials r8 = water blocker + the photo-projection pass on the
  registered stack. The definition-of-done clock (two rounds < +0.1 on the hero) starts at the first QA round after materials r8.
- **Water is now the hero's largest visible defect**: reflection R-B +2.5 vs +69 in the photo, sat 0.04 vs 0.36; the lagoon reads as a flat
  blue plane. Materials owns the mirror/murk balance; lighting owns the horizon sky it mirrors; QA's reflection test gains an R-B term.
- **2026-09-09 · Stack registered on ref 169; ref 062 disagrees by 1.02 m and loses.** ARCH r6 moved the rotunda courses (entablature
  25.96-29.18, capital 3.0, shaft 14.46, attic 9.12 with a real crown corona) so every course on the hero lands within 5 rows of ref 169
  with the silhouette fit held within 0.6 %. Ref 062 (cam02's photo) fits best with the entablature crown 1.02 m higher; its podium-base
  and attic-width residuals are now 5-6 % (bar 3 %, QA-04-11). The hero photo is the target of record; cam02's station may be re-fitted
  by QA on the new stack, the courses are not moved back. Socket contract now carries heights (capital_height, band_height, panel_height)
  and arch_socket_check --type props asserts them (docs/sockets.md).
- **2026-09-09 · Entablature sub-courses (ref 085): deferred, not rejected.** Architecture r7 measured the modillions 42 % taller than built
  and a 0.58 m Greek-key band we do not model; fitting them needs CORNICE_H 1.37 -> 1.79 with the frieze 0.81 -> 0.61 (ornament refits the
  rinceau). Not built this round: QA round 7 first scores the registered stack; if the entablature row std still fails (QA-06-9), option A
  goes into the next architecture round with the ornament refit in the same wave.
- **2026-09-09 · Budget plan (user: ~32 % of the weekly limit left, Phase 5 needs ~10, gate must close within ~20).** Remaining rounds:
  (1) polish round 5 closes with LIGHT r14 (running) + MAT r8 re-scoped to the water blocker QA-06-3 and the coffer albedo only; lead runs
  the ornament LOD1 bake in the GPU window; lead_build.sh; QA round 7. (2) If the hero is under 3.6 after QA round 7, the next round is
  the photo-projection pass (docs/briefs/materials_r8_projection.md, as MAT r9) with no other knob round; then QA round 8. (3) The
  definition of done then applies (hero >= 4.0, or two rounds < +0.1 after the projection pass) and Phase 5 starts
  (docs/phase5_checklist.md). The entablature re-split (option A) stays deferred unless QA shows it in the hero score. Reviews stay,
  briefs stay short, one render set per agent.
- **2026-09-09 · After QA round 7 (hero 3.44, +0.22, every view up): projection pass next, preceded by one short lighting round.**
  The 3.6 rule (user, budget plan) puts the photo-projection pass (MAT r9, docs/briefs/materials_r8_projection.md item B) next with no
  other knob round for the stone. Two of the three blockers are the lagoon: QA-07-1 open lagoon 1.24x bright / hue 224-228 (the r14 sky
  moved it 214 -> 228 with the water untouched: lighting's horizon term first, then materials), QA-07-3 mirror 0.55 of direct stone vs
  0.88 (materials, with the camera height confirmed at 2.6 m photo vs 2.90 m built: not moved). Order next session: LIGHT r15 (lagoon
  horizon hue/level, hero shade level 134 -> 103-127, cam03 lagoon-side row; short, one sweep) -> MAT r9 (projection + mirror level +
  sunlit chroma QA-07-2) -> lead_build.sh -> QA round 8 (Opus xhigh). Then the definition of done applies. Entablature re-split stays
  deferred (row std 44.0 vs test 40 passes; not in the hero score). cam02 re-station to (-79.8, 24.4, 1.55) -> (0, 0, 23.5), 40 mm, at the
  start of round 8 (QA's fit; lead applies in qa_cameras.py before the next QA renders).
- **2026-09-09 · Session after QA round 7 (user's plan, not re-derived): stations moved, LIGHT r15, MAT r9 = projection, QA round 8.**
  cam01 is now 2.6 m over the water (z 1.3; QA round 07 item 5's measurement of ref 169) and cam02 stands at QA's fitted ref-062 NNE station
  (-79.8, 24.4, 1.55) -> (0, 0, 23.5) at 40 mm; the old cam02 stood on the mirror-image face. The silhouette / stack registration was re-run on
  the new hero height before any builder started (every course within 6 rows of ref 169; the widest is the attic panel bottom). The QA-07
  hero boxes are kept; QA round 8 re-bases them if the aligned overlay says so.
- **The lagoon flood was the shade fill, not the sky.** LIGHT r15 isolated the three blue shade lamps at el 2 and found WNW / SSW put 7.3 W/m2
  flat on the water against the sun's 8.2: one lamp (NNE) survives, glossy boost 5.25 -> 4.20. Eevee fast GI was the cam03 black-frame lever
  (18.5 -> 4.6 % under lum 10), not lamp reach. The hero's shaded attic stays at 136 with the fill nearly off, so QA-07-7 is re-owned by
  materials as a shaded-albedo item (the shaded stone runs ~12 % hot relative to the sunlit stone on the same wall). cam02's shaded pier
  (hue 260) stays a minor: no lamp weight lands both the hero attic and the pier.
- **Budget (about 30 % of the weekly limit at the start of this session; Phase 5 needs ~10).** Spent on LIGHT r15 + two reviews + ORN r8 merge
  and bake + Phase 5 prep. MAT r9 and QA round 8 come next; the ornament archivolt band (QA-07-4, 8 empty sockets) is NOT dispatched this
  session: it needs a bake and a render round and is worth ~0.5 of one hero row. If the hero is under 4.0 after round 8, at most one more
  round, then the definition of done applies regardless. Phase 5 tooling is on branch phase5, reviewed, held until the gate.
- **2026-09-10 · Final gate judgement (Fable, the one use of it for QA) and the move to Phase 5.** QA rounds 8 and 9 score the hero 3.67 / 3.67
  (+0.22 then +0.00 after the projection pass); the user's rule (one round after round 8, then Phase 5 regardless) applies. Lead's judgement on
  renders/qa_comparisons/round09_gate.png: the silhouette, course stack and ornament read as the building, the projected concrete has the
  photograph's streak grain and the shade its colour; what still separates the frame from ref 169 is (1) the mirror at 0.61 of the sunlit stone,
  blue where the photo's is warm, (2) the sky's flat pale blue against the photo's warm horizon haze, (3) the shoreline's tree masses (a hedge
  where the photo has trunks and dark crowns), (4) the building block 1.10x the photo's saturation off the attic box. None is a lighting or
  colour-management item that another knob round would close within budget; the AgX High Contrast cap on the sunlit attic (sat ~0.49) is
  accepted. QA-09's known-issues list (docs/qa_round_09.md) is the delivery's open list. Phase 5 runs on the master built at a25b2ce
  (9679 objects, frames 1-1224), through scripts/phase5_deliver.sh on a packed delivery copy.
- **2026-09-10 · v2 after the user's arch finding.** The v1 hero's main arch was closed by chord triangles of the vault rib plate (a round-1
  tessellation bug: the flat plate with holes was triangulated, then its vertices bent onto the barrel; 67 faces of 7-11 m2 across every bay).
  No metric caught it and the 960 px composite hid it; three gate checks now exist (name sweep, six-tile 100 % hero review, ray-cast opening
  test). ARCH r8 grids the plate before the mapping. Consequences accepted: the open arch mirrors sky and vault, so the hero reflection's R-B
  fell +50 -> +32 and the reflection lum rose past its floor; the hero entablature reads 0.83x the photo. **The blue shade-fill lamp is off**
  (it was the magenta on the arch jamb and the violet on cam02's face): the hero's shaded attic now sits at hue ~41 / sat ~0.63 against its
  23.5-35.5 / <= 0.50 window and the building block reads 1.22x the photo's saturation (QA-10b-1). The arch reading right at 100 % outranks
  those windows; the next lighting round, if any, replaces the blue lamp with a low-energy NEUTRAL shade fill. The rotunda interior fill runs
  on bays 06 + 07 only (the hero's "vault field" is the central ceiling seen through the arch, the same surface as cam04's coffers).
  Floating gulls removed (icospheres 7.5 m from the hero camera). v1 kept under renders/final/v1; v2 renders under renders/final/v2.

## 2026-09-15 · Phase 6 start (lead): Three.js walkthrough, Gate 0 prepared
- Inventory (export/inventory.py on master_delivery.blend): the export set as the user stated it (ARCH_+ORN_ LOD0, ENV_ LOD1) is 30.5 M
  placed tris (ORN instances 22.9 M, ENV LOD1 4.8 M, ARCH 2.85 M) against the 3 M budget. Decision: Gate 1 is a decimation gate with
  per-class budgets ARCH 1.1 / ORN 1.1 / ENV 0.8 M (docs/briefs/phase6_plan.md §2); ENV trees outside the station band go to LOD2.
  The user's note "ENV assets exist only as _LOD1" is not what the file holds (ENV has LOD0/1/2 for 1526 objects) — flagged.
- Colour: the shipped look is `AgX - High Contrast` at exposure -2.833 (read from the file). three.js AgX has no looks, so the viewer
  applies a 3D LUT baked through Blender's OCIO with tone mapping off. Verified at Gate 0 on a grey plane (1/255 tolerance).
- Lighting transfer: lightmap = Cycles diffuse direct+indirect (sun included) -> the viewer's sun is specular-only; sky exported twice
  (camera branch = background, glossy branch = PMREM); ORN instances get prototype normal+AO and a per-instance vertex-colour
  irradiance bake (decided finally at Gate 3 from Gate 0 timings).
- Toolchain: gltfpack 1.2 native and KTX-Software 4.4.2 (toktx) are not in Homebrew; installed from GitHub releases into tools/
  (gitignored, tools/install.sh re-fetches). Chrome 152 headless has WebGL2 on ANGLE Metal, but a raw `--screenshot` lingers
  60-90 s per frame: screenshots go through puppeteer-core inside scripts/chrome_run.sh (registered deadline, leftover kill).
- Gate 0 runs as two agents (bake engineer xhigh, viewer engineer high) on a manifest contract (docs/briefs/phase6_gate0.md);
  the slice is the 16 rotunda columns (one shared mesh, decimated 14.4 k -> 3.5 k) + the ground under them + the world sky.
- Dispatch of any builder waits for the user's approval of docs/briefs/phase6_addendum_draft.md (user's rule).

## 2026-09-15 · Gate 0 bake report in (phase6-bake 536fc15); lead's calls and the ORN_ decision for the user
- **ORN_ export, three options measured on the capital slice (2K 128 spp lightmap 221 s; per-prototype normal+AO+PBR bake 290 s;
  shared PBR KTX2 10.8 MB per prototype; 436 placements of 33 prototypes; a 3.0 m capital is 23 px at 1280 / 68 px at 3840 from cam01):**
  (a) unique mesh per instance with its own 2K lightmap: 2.62 M unique tris, ~4 300 MB textures, 221 s x 436 = **29.5 h** of bakes;
  (b) true instancing, shared PBR, no ornament lightmap (lit by sky PMREM + sun + prototype AO): 198 k unique tris, **357 MB**, **2.7 h**;
  (c) instancing + a 256 px per-instance lightmap-atlas slot (two 4K atlases) and a custom material with a per-instance UV offset:
  198 k unique tris, **451 MB**, 5.1 s x 436 = **3.3 h**; the 256 px slot is 3.8x the hero's sampling of a capital.
  Hero-visible cost: (a) exact Cycles shade per capital at 29 h and 4 GB (not affordable on 6b); (b) the shaded side of every capital is
  the PMREM's average, so the sun/shade contrast on the 16 rotunda capitals and 114 colonnade capitals is lost (the hero's capital
  row sits in the shade band the round-10b boxes measure); (c) keeps that contrast at 94 MB over (b) and 0.6 h more.
  **Lead recommends (c).** Numbers in export/out/gate0/orn_options.json. **The user chooses before the Gate 1 budget is written.**
- gltfpack 1.2 refuses `-mi` with `-kn`: lead picks **`-cc -mi` (EXT_mesh_gpu_instancing, node names dropped)**; asset identity lives in
  the manifest and the name sweep runs on the Blender-side export set (export/out/*/export_set.json), not on the glb.
- Lightmaps: RGBM8 (range 64) PNG in emissiveTexture on TEXCOORD_1 for Gate 0 (0 clipped pixels, worst round-trip 4.8 % relative at p99).
  For Gate 3 they become lossless KTX2 (toktx `--zcmp` without a Basis encode, so the M channel is not block-quantised) and the viewer
  moves emissiveMap -> lightMap and decodes rgb * a * 64; a gamma-2 encode halves the round-trip error and is taken at Gate 3.
- Three Blender 5.2 findings from the bake engineer go into docs/tech_notes.md "Phase 6" at the merge: `Image.save_render()` applies
  no colour management; `scene.use_nodes = False` does not disable the compositor (`scene.compositing_node_group = None` does, and the
  compositor moved 0.18 grey from 0.0821 to 0.0750); LOD0 objects are `hide_viewport` in the delivery file and absent from the depsgraph
  (matrix_world reads identity, ray casts miss) until un-hidden and `view_layer.update()`.

## 2026-09-15 · Gate 0 verdict (lead): PASS on the vertical slice, pending the user's sign-off before scale-up
Merged: phase6-bake (f8871f2) and phase6-viewer (cdca62f), both reviewed (docs/reviews/phase6_*_gate0_review.md) with every fix-now item
applied; carries listed in export/README.md and web/README.md. Evidence: renders/web/gate0_pair.png (viewer vs the no-compositor Cycles
frame, column bbox delta 0 px, sky 1.011, lit column sunlit 0.922 / shaded 0.985 at lightmap_scale = pi; 0.78 / 0.88 at 1 -> pi is the
contract). Against the composited Phase 5 frame the same column is 0.897 / 0.952: the remainder is the compositor (haze, bloom, vignette),
a Gate 4 item with the numbers now carried in the manifest. Pipeline per slice asset: decimate + UV 19 s, normal+AO 146-238 s,
PBR 48-65 s, lightmap 2K 128 spp 221-306 s, pack 30 s. Gate 3 projection for ~40 lightmapped assets: 5.9 h of GPU in per-asset jobs.
Still owed by the user before Gate 1: the ORN_ option (a/b/c above; lead recommends c) and the trees option (plan §4b; lead recommends
impostors beyond 25 m plus thinned LOD1 near the walk); and whether one bounded material round on dome and stone runs before Gate 2.

## 2026-09-15 · User's three decisions ("go"): ORN option (c), trees = impostors + thinned near set, one bounded material round
- ORN_: instancing with a 256 px per-instance lightmap-atlas slot and a custom material (option c; 3.3 h bakes, 451 MB desktop);
  mobile fallback = option (b) at 1K. Trees: Cycles-baked octahedral impostors for every tree beyond 25 m of the walkable area,
  thinned LOD1 (50 %) for the ~20 reachable trees; mobile = impostors everywhere. Impostor atlases are baked in the Gate 3 queue;
  Gate 1 fixes the near/far tree lists and exports far trees as tagged billboard quads.
- One bounded material round (MAT r10) before Gate 2: dome cap texture (QA-10-8) and the coffer saucer (QA-09-8) only, measured on one
  Cycles hero + one cam04 frame, lighting untouched, hold list = the round-10b hero boxes. master_delivery.blend is regenerated after it
  merges and before any Gate 2 PBR bake. The lagoon mirror and the compositor are viewer-side levers (Gate 4), not materials.
- GPU sharing rule for Phase 6 (lead): a bake queue job or a builder's Cycles frame starts only when the watchdog state dir
  (~/.cache/pfa_blender_watchdog) holds no live registered Blender pid other than its own; the detached queue waits, agents do not.

## 2026-09-15 · MAT r10 merged (e0980f5): the bounded material round is closed
Dome cap box lum 187.6 -> 205.4 and coffer field/rim 0.422 / 0.454 land in window; the cap's sat 0.352 and col-sd 5.4 stay outside because the
QA box is one-third drum cornice (sat 0.92, QA-10b-1 lighting) and a structure-off control bounds the box at 207 lum / col-sd 4.6 — accepted, not
chased (the user's rule: one round). QA re-scores QA-10-8 on rows 95-111. Jamb hue 23.8 (QA-10-2 floor 25) accepted as a rib-albedo side effect.
Next: lead_build.sh + `PFA_PACK=1 scripts/phase5_deliver.sh 1b` regenerate master.blend / master_delivery.blend AFTER the Gate 1 ORN queue is
idle (GPU rule); Gate 2 PBR bakes read the regenerated delivery file. Gate 1 geometry is unaffected (materials only).

## 2026-09-15 · Gate 1 PASSED (QA round 11d, 57addb8) — geometry frozen
Export set at a9b2d3d: 2 841 396 placed tris (ARCH 949 382 / ORN 1 099 192 / ENV 679 779 + ground 113 043), 140 unique meshes, 2 540 placements,
154 batches; every geometry row within 0.5 of the Phase 5 round-9 rows (station averages 3.60 / 3.20 / 2.50 / 3.10 / 3.10 / 3.00); silhouette vs the
Cycles hero scale 1.0000, apex delta 0.00 %H; arch-opening test PASS; name sweep 2 540 / 127 exempt boards / 0 hits; 1440p GPU 1.5 ms median at the hero.
Four QA rounds were needed (11, 11b, 11c, 11d): backdrop texCoord -1, torn voxel-remeshed attic panels, opaque exported tree boards, and ENV LOD2 stubs
exported without placements. Lessons carried into the writer: assert texCoord >= 0, mesh nodes == objects, 0 objects near the origin, drawn tris vs
export_set within 1 % (export/verify_glb.py); placeholders are hidden in every QA capture and listed as exempt, never silent. Carried to Gate 2: QA-11c-2
untextured backdrop / pedestals (PBR bake), QA-11d-2 gltfpack -vp 16 on env.glb; Gate 3: the 127 impostor carriers (QA-11-1/-3); Gate 4: mirror water
(QA-11-5), shrub InstancedMesh bounds spanning the site (QA-11d-1, split per region).

## 2026-09-15 · Gate 2 bake in (phase6-bake a9794e8), lead's calls
- 4K hero-near set: the rule ("inside the cam01 frame within 30 m") selects nothing — cam01 stands 100 m out and the nearest in-frame group is 36 m
  away. No 4K textures at 6a; the walk-near alternative (+256 MB) would break the 1 200 MB budget. Texel density at close range (podium 1.7 cm/texel
  from 5 m) is a Gate 4 item: a tiling detail texture, not resolution.
- Resident projection 1 166 MB of 1 200 after ORN roughness at 1K and albedo 1K under 2 m (measured against the nearest station's pixel size);
  the impostor lever (-200 MB) stays unspent for Gate 3.
- ARCH hi->lo normals were never in scope (the columns' flutes went 14 396 -> 3 500 tris with material bump only): carried to Gate 4 as a
  polish item if the fluted shafts read flat at cam03; per-instance weathering variation survives only through the Gate 3 lightmap slot.
- Hand-offs: export re-exports env.glb with the generated backdrop UV1 (backdrop_uv1.npz) and -vp 16; the viewer uses the Gate 2 ORN normal
  in place of the Gate 1 one and honours uv1_in_glb: false meanwhile.

## 2026-09-15 · QA-12-1: merged UV1 groups get their own atlases (lead's call, after the export engineer's measurement)
Every merged multi-object ARCH/ENV group packed its UV1 at 0.04-0.10 of the square (multi-object smart project + a sub-texel margin + a fixed tile
guess): colonnade N/S 0.040/0.039, rotunda ochre 0.056 (the hero's stone), plaster rib 0.065, site podium 0.083, riprap 0.013 — the 0.40-0.69 figures
were the single-object ORN prototypes. Decision: each merged mass goes onto its own 2K atlas (new material + set), the instanced meshes keep theirs
(~0.40); +~50 MB resident accepted against the impostor lever; the affected groups are re-baked (albedo/roughness/normal) and every ARCH/ground set
gets a bump-derived tangent normal (7 of 12 shipped none). Texel density where the hero looks is the reason; coverage numbers alone were not.

## 2026-09-15 · QA-12-1 resolution: the concrete grain ships as a tiling detail layer, not in the atlas normals
Measured by the bake engineer: a Cycles NORMAL bake of the stone bump on a 2K atlas has std 0.0017 (0.0027 at 4K) because the Bump distance is
0.015 m against 4-12 cm atlas texels — the grain is under the bake's Nyquist; Cycles renders it per camera pixel. So every ARCH/ground set now ships
a real (low-frequency) normal, and the grain comes from `materials.detail`: five shared 1K object-space tiling sets (albedo, roughness, normal from
the source height at the true tile scale), 20 MB resident, applied in the viewer shader (albedo x detail / mean, normal blend). Resident projection
1 248 MB with Gate 3 reservations; the impostor 2K -> 1K lever (-200 MB) covers it. Process rule added: the export sync writes export_set.json LAST
(the bake engineer caught a blend/JSON mismatch mid-run).

## 2026-09-15 · QA-12-1 closed as far as materials can close it (lead)
The detail layer now ships the honest slope of the Phase 5 materials (Bump Distance 0.015 m differentiated at the 2K source: normal std 0.024 /
0.019 on the two concrete sets, albedo contrast 3.3 %); the source height maps are 8-bit low-frequency JPEGs (texel gradient below 1/255), so no
derivation yields the 10x the QA box asks for, and a gain knob or a generated grain map would be invented relief. The rest of the cam05 pier-face
amplitude is shading and occlusion, which Gate 2's direct mode excludes by construction and Gate 3's lightmaps carry. QA 12b re-scores with that
attribution; Gate 2 passes on material rows only if the material share is within parity.
