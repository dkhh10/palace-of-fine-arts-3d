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

## 2026-09-15 · Gate 2 PASSED (QA round 12b, 19412e4) — materials frozen
62 material sets (60 baked + 2 from the atlas split), every ARCH/ground set with a real normal, a 33.6 MB tiling detail layer on 20 materials, 62/62 attached.
Material rows: no station's residual is a material gap (the critic attributes every remaining deficit to shade/occlusion, per-instance weathering — Gate 3 —
or the water — Gate 4). Where the sun reaches both frames the export is at or above Phase 5 (sunlit attic mid 1.10x / std 1.17x, pedestals 1.33x).
Two rounds were needed (12, 12b): the missing ARCH normals and the merged-atlas coverage. Textures 953 MB resident (246 under budget; impostor lever unspent),
hero 267 draws, GPU 1.8 ms at 1440p. Carried to Gate 3: QA-12b-1 sun-less stone reads olive (16-22 % of cam02/cam06 building pixels G > R; 0 % in the
albedos themselves — the direct-mode PMREM diffuse; lightmaps replace it), QA-12b-2 S-colonnade wall blow-out 201-221 (shade), QA-12-4 per-instance
weathering via the slot atlases, the sunlit-attic saturation at 0.94x must not drift further. QA-12-2 dome cap sat 0.69x stays open, non-blocking.

## 2026-09-16 · Gate 3 hand-off: gltfpack had stripped UV2 from every glb since Gate 1; ORN ships without its cavity COLOR_0
The export engineer measured that gltfpack removes any vertex attribute no glb material references, so TEXCOORD_1 was absent from arch/ground/env/orn.glb since
Gate 1 (Gate 0 kept it only because its RGBM lightmap sat in the material's emissive slot). `uv2_in_glb: true` on the nine Gate 1-layout assets was never true; no
Gate 3 lightmap could have attached. Fix: `-kv` per class when its .gltf carries TEXCOORD_1/COLOR_0 (arch + ground re-exported, +1.74 MB; verify_glb now asserts
TEXCOORD_1 reach). ORN: `-kv` would also ship the prototypes' `cavity` FLOAT_COLOR attribute (scripts/orn_lib.py vertex_cavity), which the ornament material reads
for recess dust and which the Gate 2 albedo bake therefore already contains; three.js would multiply it into base colour a second time. Lead's call: the ORN
export strips vertex colour attributes and packs with `-kv`, so orn.glb carries TEXCOORD_1 for the slot atlases and no COLOR_0. Vertex irradiance (14 near
trees, env.glb): the bake writes float32 scene-linear per mesh; the export encodes gamma-2 at a per-mesh range as FLOAT_COLOR and packs env.glb with `-vc 16`;
the per-mesh range and decode string travel in export/out/gate3/uv2_relay_status.json and the manifest writer copies them into `lightmaps.vertex_irradiance`.
Carried: three of the seven relaid assets still pack under the 0.15 UV2 threshold (riprap 0.114, colonnades 0.116/0.121) — baked against that layout, accepted.

## 2026-09-16 · Gate 3 export r2 (lead): the 114 merged slot nodes are un-merged by a same-named material copy, not by gltfpack -kn
gltfpack merges two meshes that share a material and an identical node-transform set; the colonnade colbase plinth/torus pairs qualify, so 114 of the 988 ORN/ARCH slot placements
had no mesh of their own and the viewer could attach only 438 slots. `-kn` restores them only by disabling `-mi` (27 -> 564 draw calls, +52 kB). Accepted instead: the export gives the
second mesh of each colliding group its own material copy under the same name, so `-km` keeps them apart while both stay instanced (27 -> 29 draw calls, +3.6 kB, placements 552 + 436
= 988); the viewer joins materials by name and sees no new material. Also on record: Blender 5.2's glTF exporter emits a fake constant-white u8 COLOR_0 when the material's node tree
references no colour attribute and pushes the real attribute to COLOR_1; the export drops the fake (u8, constant 1.0) and renumbers, asserting the survivor is u16/float. Vertex
irradiance ships gamma-2 at each mesh's own max (0.469-43.32), 16-bit, decode v = c^2 * range_mesh * lightmaps.scale.

## 2026-09-16 · Gate 4 round 5 (lead): the dark lightmapped hero was gltfpack's 12-bit UV quantisation, never undone on TEXCOORD_1; vertex irradiance goes to one global range; Cycles references for stations 3/5/6
Finding (viewer engineer): gltfpack stores every TEXCOORD as normalised 12-bit ints and puts the dequantisation in KHR_texture_transform on the material's baseColorTexture, which
three.js applies only to that texture's own uv channel. TEXCOORD_1 carries no texture in the glb, so each lightmap sampled the bottom-left 1/16 x 1/16 of its map (hero luma 117.5 vs
Cycles 140.0; no decode or flip could reach it). Second defect, same cause: the PBR/detail passes replaced material.map with an identity-transform texture, so albedo/roughness/normal
had sampled the same window since Gate 2. The export owes nothing: with the transform undone the glb's UV2 matches the bake npz at IoU 0.994-0.999 on all seven relaid assets.
Fix in the viewer (web/src/uvDequant.js, once per geometry attribute, before any pass): hero 134.3, p10 51.4 vs Cycles 52.2; V-flip stays off (worse). Gate 2's material parity
scores (round 12b) were measured with this defect present and are therefore conservative; they are not re-scored.
Vertex irradiance: the per-mesh range (decision above) is unusable because gltfpack -mi instances primitives across different trees (14 buffers, 26 placements, 2 unambiguous joins).
Lead's call: ONE global range (max over the 14 = 43.32), gamma-2, 16-bit FLOAT_COLOR, -vc 16, -mi kept. Estimate: the darkest meaningful mesh (mean ~0.001) codes at c = 0.005 with a
16-bit step of 1.5e-5, a relative step of ~0.6 % in linear value, so the uint8 shared-range defect (rel_p99 0.244) does not recur; the export reports roundtrip_rel_p99 per mesh and
the fallback is keeping the 14 trees out of -mi if any mesh above 0.01 exceeds 2 %. Mist: world.mist_settings start/depth/falloff were never in the manifest (the compositor block
recorded the group input as 0.0); they are read from master_delivery.blend into compositor.mist; the viewer's placeholder 60/1400 m is a no-op and is not scored.
Parity references: stations 3 and 5 only had Eevee round-09 frames and station 6 a Cycles frame without the compositor, so 6a's "within 0.5 of its Phase 5 score" was unmeasurable on
half the stations. The lead renders Cycles 1920x1080 128 spp compositor-on frames for cams 03/05/06 from master.blend (scripts/qa_render_round.py --round 13 --final) as the Gate 4
references; QA 13 scores 3/5/6 provisionally until they land.

## 2026-09-16 · Gate 4 item 2 (lead): leaf-card alpha is fixed in the export, not guessed in the viewer; impostor row order recorded
The four MAT_leaf_* materials reached env.glb without alphaMode, so glTF drew every near-tree leaf card as an opaque rectangle (sky-lit blue shards over a third of cam02). The export
sets alphaMode MASK with the cutoff read from each source material in master_delivery.blend and verify_glb asserts MASK/BLEND on every material whose base colour texture carries alpha;
a viewer-side alphaTest would pick the cutoff by guess. The far-tree impostors (16 InstancedMeshes, 127 trees, 16 draw calls) needed a V flip because the KTX2 atlases are top-down
(KTXorientation rd) while the manifest's frame rows count from the bottom; recorded in web/README.md with the measured codes so the bake side can align the convention at the next bake.

## 2026-09-16 · QA-13-1 and QA-12b-1 after the viewer's pixel picks (lead)
QA-13-1 (blue bays between the north colonnade columns) is the backdrop city blocks, not a colonnade surface: env.glb carries no TEXCOORD_1, nothing patched them, and they take
all their light from scene.environment, which Gate 3 switched from the glossy equirect to the DIFFUSE sky PMREM (3.9 % -> 23.0 % of the band B > R+20). Decision: viewer-side; the
unpatched surfaces go on the existing direct path (sun Lambert + diffuse sky at the `direct` mode's weights). No UV2 or lightmap for the backdrop: it is far and never hero-critical.
QA-12b-1 (olive cast in shade, 19.7 % at cam02): the viewer engineer showed the green is lightmap texel x warm albedo with the texel itself blue in shade, and proposed that
`use_pass_color=false` bakes the indirect against a white albedo. Not accepted as the mechanism: Cycles' colour toggle strips only the baked surface's own albedo, bounced light keeps
the neighbours' colours, and bake_lm.py does not touch bounces. Two candidates are checked before any re-bake is considered: round13b was captured with post OFF and so lacks the
compositor's warm airlight (cap 0.25, k 5 as an extinction coefficient) that every shaded Phase 5 pixel has (viewer re-measures with ?post=all now that compositor.mist is real);
and the bake scene's bounce-surface materials / Cycles-only gallery fills / world (bake engineer, read-only). A colour-on lightmap bake is not an option: it would bake albedo at
5-17 cm/texel under the 2K PBR maps.
Mist: the viewer had implemented the haze falloff 5.0 as an exponent; scripts/light_build.py uses it as an extinction coefficient, airlight = cap * (1 - exp(-k * mist)) — corrected,
hero luma with post 127.3 -> 131.8 (Cycles 140.0).

## 2026-09-16 · Chrome during a lead render (lead): PFA_DEV_SHARE_GPU=1 for development screenshots only
While the lead's Cycles reference renders (stations 2-6, ~20 min each) occupied the GPU, the viewer engineer was allowed to keep taking development screenshots through
scripts/chrome_run.sh with PFA_DEV_SHARE_GPU=1, which keeps the bake-queue guard and refuses --perf outright. Scored captures and every perf measurement still require the GPU
free (no bake queue, no lead render). The CLAUDE.md rule "never concurrent with the bake queue" is unchanged; this is the lead's standing exception for a lead render only.

## 2026-09-16 · QA-13-1 revised (lead): the direct-path fix was a no-op; unlit-mapped surfaces take irradiance from the baked hero probe
The viewer engineer measured the prescribed fix before shipping it: the blue backdrop wall is back-facing to the sun (NdotL −0.065) and its pixel is bit-identical in baked and direct
modes, so no weighting of sun + sky changes it; what Cycles gives it and the viewer does not is the warm indirect bounce. The shrubs and reeds (no lightmap, no COLOR_0) sit on the same
sky-only path, which is why the leaf cards cut out correctly after the alphaMode fix but stay blue: QA-13-1 and the blue foliage are one problem. Decision: manifest.probe (the baked
6-face hero probe, real bounce in it) convolved to irradiance is the diffuse environment for every surface without a lightmap or COLOR_0; lightmapped and vertex-lit materials are
unchanged; a warm irradiance floor was refused as a fudge. Single-point approximation for far surfaces, documented; Gate 4 QA judges it. Post on moves the olive fraction at cam02
from 46.5 to 32.2 % on the viewer's own mask (−14 points): the missing airlight is a large contributor but does not close QA-12b-1 alone; the bake-scene check is still pending.

## 2026-09-16 · QA-13-2 root cause is inverted normals, not UV2; QA-12b-1 is not the bake scene (lead, from the bake engineer's measurements)
The rotunda plaster shell's visible faces already own 60.6 % of their map at 1.53 cm/texel; every one of them has its normal pointing UP, away from cam04 (normal·to_camera −0.99).
A Cycles render flips the shading normal toward the ray, a bake has no ray, so the DIFFUSE bake integrated the enclosed cavity between shell and dome (median hit 11.55 m, no sky)
instead of the lit rotunda below. The six-station sweep finds no second 100 %-backface object. Fix: re-bake this one asset with its winding reversed in the bake process only
(FLIP_NORMALS_FOR_BAKE; UV2 corner sets asserted bit-identical, blend never saved), map replaced in place under the same keys; no relay, no glb change.
The bake scene is the Cycles rig: same 11 warm ARCH bounce materials, same 20 LIGHT_* incl. the 16 x 1200 W gallery fill, world identical (WORLD_golden_hour, sun_disc off,
elevation 7.357°, rotation 28.493°), Cycles bounces identical (max 8, diffuse 3, clamp_indirect 10). So the blue shade texel is not a grey bounce, a missing lamp, a different sky
or a shorter path. Remaining hypothesis under test: the Phase 5 world's warm tint lives on the diffuse-ray branch of a Light Path gate; a bake may sample the sky under the
camera-ray flag and miss it. Two-colour debug-world bake vs render queued after the ceiling bake.

## 2026-09-16 · QA-13-1 closed with the hero probe as the diffuse environment for unlit-mapped surfaces (lead override of manifest probe.use)
Result (viewer c79b7b6, post on): cam01 band B > R+20 15.5 % -> 0.2 % (Cycles 0.0 %), band mean RGB [105 92 68] -> [95 76 30] against Cycles [80 64 24]; cam02 shrub/reed/backdrop
median hue 220° -> 41°; 15 materials touched, 77 lightmapped or vertex-lit untouched. The manifest's probe.use says the probe is the water fallback, not the diffuse environment;
the lead overrides that for surfaces with no baked irradiance because the probe is the only baked data with the courtyard's warm bounce in it. Caveats on record: single-point
(hero station) approximation for surfaces 140-190 m away and at the other stations; the probe was rendered on the sky's glossy branch. Foliage now reads amber-brown where Cycles has
olive-green (ground bounce dominates a sideways leaf card): decision held until the light-path branch test; the candidates are a corrected bake branch or vertex irradiance for
shrubs/reeds as for the 14 near trees. Re-measured against the new compositor-on Cycles references: cam03 1.67x (was 2.08x vs the Eevee frame), cam05 1.08x, cam06 0.71x — a
real deficit the no-compositor reference had hidden.

## 2026-09-16 · Gate 4 item 6 (lead): the 1440p frame is vsync-quantised, not GPU-bound; bloom and the water Reflector go to half resolution
Measured (viewer 184d785): with the Gate 4 look the presented frame is 29.5-32.2 ms (33 fps) at stations 1-3, 5, 6 while CPU submit is 1.0-4.1 ms and gl.finish 0.5-2.6 ms; with
water and post off the frame is 17.3 ms = one vsync interval. The Reflector's second scene pass costs 6.3-8.6 ms (draw calls 314 -> 164 without it) and the full-res bloom chain
7.8-8.4 ms; together they push the frame a few ms past one interval, which quantises to two. Decision: bloom from a half-res source and the Reflector to a half-res target (its
result is blurred by reflBlur regardless); every-other-frame reflection refused (temporal artefacts while walking). Acceptance: >= 45 fps at all six stations and every cam01 hero
box within 0.03x of its full-res value; a lever whose box moves more is reverted and the trade-off reported.

## 2026-09-16 · Sky-branch hypothesis REFUTED; no lightmap re-bake; QA-13-2 closed by the flipped-winding bake (lead, from the bake engineer's probe)
Debug world (R = camera ray, G = neither camera nor glossy, B = glossy), lamps off: the podium DIFFUSE bake reads exactly [0, 1, 0]; the cam02 render's ARCH pixels [0.108, 0.878,
0.014]; the sky [0.989, 0.001, 0]. Cycles bake rays take the diffuse branch exactly as the render does. Independently, the diffuse branch is the BLUER one (diffuse/camera =
[1.49, 1.34, 4.16], SKY_DIFFUSE_TINT b = 70), so a camera-branch bake would have been less blue, the opposite of the symptom. The prepared 47-job corrected queue
(PFA_BAKE_DIFFUSE_WORLD=1) stays unarmed and is not run; the overnight GPU slot is not needed. sky.diffuse matches the diffuse-branch equirect to three decimals.
QA-12b-1 is therefore downstream of the bake: not the asset, the lightmap, the bake scene or the sky branch. Remaining candidates, in test order: the viewer's specular term (a
sky-only glossy PMREM where Cycles' shaded stone reflects the warm sunlit surroundings — A/B with the hero probe as the specular envMap for lightmapped materials), then the
Gate 2 albedo bake's tone against the Phase 5 material. The compositor's airlight is already a measured −14-point contributor with post on.
Ceiling: re-baked with the winding flipped in the bake process only (UV2 bit-identical), max 0.721 -> 16.755, mean_nonzero 2.06 (rib map 1.70), 30.7 % non-zero texels, gamma2
round-trip error 0.163 -> 0.025 stops; map replaced in place, manifest range updated by the lead's manifest_v4 run.

## 2026-09-16 · Gate 4 frame rate (lead): the default keeps the look; 45 fps at 1440p is not reachable with the Reflector and bloom, so a documented fast preset carries the trade-off
Measured (viewer 7007645): reflset=orn (the 436 ORN instances skipped in the reflection pass, 36 meshes on a reflection-excluded layer, reflection box within 0.03x on all four
metrics) saves ~2 ms because the instances were already ~36 draw calls; excluding the backdrop was rejected (it is in the reflected frustum: sat 0.527x, R-B sign flip).
Attribution stands: water off alone 25.7 ms, water and bloom off 17.3 ms; both are needed to reach 22.2 ms. The reflection at the hero station is a hard requirement of 6a and
the Phase 5 look (bloom = the compositor's glare) is frozen, so the default ships the full look at the measured frame time (34.6 fps at 1440p, everything on) and a non-default
`?quality=fast` preset (half-res bloom, half-res Reflector, reflset=orn) is measured and documented with its box deltas for the user to choose at delivery. This is flagged to the
user as an open choice, not decided for them.

## 2026-09-16 · QA 14 verdict ONE MORE ROUND: 6a parity criteria met (thin), one bounded polish round, then the final judgement
Scores 01 3.61 (P5 3.67) · 02 2.94 (2.94) · 03 2.56 (2.56) · 04 2.88 (2.81) · 05 2.83 (3.06) · 06 2.56 (2.67): every station within 0.5 of its Phase 5 score and none below 2.5;
the reflection at the hero, the walk clamp and the loading screen pass; 45 fps is not met (34.6 fps, attribution accepted). QA-13-1, QA-13-2 closed; QA-12b-1 closed at cam06
(1.5 % vs ref 1.4 %) and cut to a third at cam02 (7.4 % vs 2.2 %) — the airlight, as tested. By the stopping rule 6a could close here. Lead's call: ONE bounded round (round 15,
docs/briefs/phase6_gate4_r6_viewer.md) because the hero water is an evenly blurred dark mirror where the reference has golden ripple streaks (ripple std 0.07x) — exactly the water
lesson of attempts 1-2 — and because a smaller bloom radius serves both the flattened hero and the frame budget. Then QA 15 and the single Fable final judgement; 6a closes after
that regardless of the round-15 delta (two rounds after Gate 4).

## 2026-09-16 · CORRECTION: the probe-irradiance result of QA-13-1 was measured on a black environment (lead, from the pre-merge review 5d034d6)
The code reviewer found that probeEnv.js built the CubeTexture from bare image records, so three.js took the DOM-source upload path and threw six swallowed texSubImage2D errors
(visible in the committed round14_cam.json page log); the PMREM was of a black cube, and a black envMap overrides scene.environment, so the 15 unlit-mapped materials LOST their
sky irradiance rather than gaining the warm bounce. The band measurements (0.2 %, mean RGB beside Cycles), the amber-brown foliage, and the probespec lead are all artefacts of
that. The decision to use the probe stands in principle; its result is void until re-measured with the real cube. QA-14's QA-13-1 "closed" is withdrawn pending round 15.
Process lesson recorded: a scored capture must fail on any page error (gate4.sh / screenshot.mjs now do), and a "fix" that lands exactly on the reference numbers deserves the
same suspicion as one that misses.

## 2026-09-16 · Probe re-measured on the real cube (viewer 1e9d2be / 82d44c5): QA-13-1 closure stands; the probe does not touch QA-12b-1; foliage gets vertex irradiance
Real cube, probe off -> on: cam01 band B > R+20 15.51 % -> 0.29 % (Cycles 0.05 %, gate 3.9 %), band mean RGB 105/92/68 -> 103/86/41 toward the reference 80/64/24; every cam01
box outside the water moves < 0.01x. cam02 building G > R 32.2 -> 41.7 % (reference 26.9 %): the probe makes the olive WORSE at cam02, so the earlier "half-closed" statement is
struck; probespec (15/32 boxes hold) stays off. Foliage reads cyan (hue 180 vs 102 reference): sky-lit cards with no baked light — the amber-brown of round 14 was the deleted
sky. Decision: the shrub/reed/card meshes get bake-side vertex irradiance exactly as the 14 near trees (bake -> npz -> env.glb COLOR_0 -> viewer's existing consumer), inside
round 15. Water (QA-14-1): the hard reflection edge is not clipping but the surface model (a near-mirror reflects the dark zenith where a rough lagoon samples the bright
near-horizon); an isotropic ripple strong enough to satisfy the row-frequency metric reads as cobblestones, so the metric alone cannot accept the fix — the lead judges a 100 %
open-water tile. Rebuild: anisotropic ripple normal (elongated crests) plus a horizon-stretched rough lobe.

## 2026-09-16 · Shrub/reed irradiance is baked PER PLACEMENT, not per mesh (lead, at session close; to execute next session)
The bake engineer measured (phase6-bake 67f4e90, export/out/gate3/env_cards.json): 28 shrub/reed card meshes carry 1 379 placements, up to 101 per mesh, 279 m apart on average, so
a per-mesh vertex bake would give 1 379 shrubs 28 wrong values. Decision: one scene-linear RGB per PLACEMENT (the mesh's vertex-averaged Cycles DIFFUSE irradiance at that
instance's transform; ~16.5 kB), written to a new manifest block `lightmaps.instance_irradiance` {mesh: [rgb per placement in placement order], range_global, encoding}, consumed
by the viewer as an InstancedBufferAttribute exactly like the ORN slot offsets (instancing kept; no COLOR_0). Estimated 3-5 GPU minutes. The 14 near trees keep their per-vertex
COLOR_0 (one placement each).

## 2026-09-16 · reflset=orn is the default reflection set (lead, session 4, from the r7 review's should-fix)
The Gate 4 frame-rate entry said the default ships "everything on" while the viewer shipped `?reflset=orn` (the 436 ORN instances skipped in the reflection pass) as the look default.
Authorised: it was measured within 0.03x on all four hero reflection boxes (the acceptance the frame-rate entry set for any lever) and saves ~2 ms; the backdrop stays in the
reflection. The r7 review's two fix-now items (far-water uv leaving [0,1] under the grazing factor; the WIP water on by default before the tile is judged) go to the viewer
engineer inside item 1; the default is decided by the lead after the 100 % open-water tile.

## 2026-09-16 · Water tile judged (lead, session 4): the derived murk stays, the ripple must be 5-8x finer, the reflection's warm drain is reflSat
Viewer 58fa59e: murk derived from MAT_water_lagoon's volume (σ_a, σ_s, g, 1.5 m, bed 0.12/0.10/0.06) gives an upwelling albedo (0.150,0.180,0.112) within 10 % of the Phase 5
hand-set WATER_MURK; open-water lum 68.0 -> 87.3 (ref 118), the body term is now right and the residual is the reflection (0.45x in red). The 100 % open-water composite
(renders/web/960/qa14_1_openwater_100pct.png): the viewer's water is a warped mirror with 40-80 px waves, contour banding from an 8-bit normal map times a large displacement,
olive reflected stone, and featureless open water beside the reflection; the Cycles frame has 5-10 px crests everywhere breaking gold into short streaks. Decision: the new
water is the default (settles the r7 review's fix-now 2); one more bounded pass — ripple frequency 5-8x finer with the displacement scaled down (2-5 cm ripples, 0.3-1 m streaks
in metres), procedural or 16-bit normal, reflSat 0.66 tested at 1 before any other cause of the red deficit — then items 2-5 and the round-15 capture regardless.

## 2026-09-16 · Shrub/reed bake re-run with a shadow-ray-only override; placements joined by location (lead, from the bake review 7d59c5f)
The first per-placement bake (aaab677) made every card in the current job an opaque grey Principled with visible_shadow off so cut-out cards would not return 0 at transparent
vertices (coverage 0.107 -> 0.859). The reviewer showed on the engineer's own probe arrays that this is not value-preserving: on vertices lit in both variants the opaque values
are median 1.64x (up to 5.25x), because the real cut-out shadow is removed while the grey card still occludes indirect; and since the override was per job, only 28.9 % of a
placement's nearest neighbours shared its job, so the numbers depended on the 4-way split. Decision: re-bake all 1 379 with the override applied to EVERY card in every job and
only on non-shadow rays (Light Path Is Shadow Ray: the original cut-out chain for shadow rays, opaque grey otherwise; shadow visibility on), so the cut-out shadows are real and
the result is partition-independent; verified by the probe ratio and one placement baked under two splits. 128 spp as before, ~43 GPU minutes accepted; Chrome pauses on
status.json meanwhile. Join key: object names do not survive gltfpack -mi and the manifest's instancing.objects is truncated at 16, so the export joins by nearest instance
translation with a stated tolerance and a loud failure on unmatched or duplicate rows; the name is a label. The 7 fully enclosed placements ship rgb 0 / cov 0 and the viewer
falls back to the probe irradiance for cov == 0. The 14 near trees' COLOR_0 carries the same artefact (77-99 % exact zeros -> black patches): re-baked with the same override
if it fits in 15 GPU minutes, else post-6a.

## 2026-09-17 · Shadow-ray bake measured and merged; the 14 near trees' COLOR_0 was mostly the cut-out-zero artefact (lead, bake f9feec3)
Partition independence is exact (one placement under two splits: delta 0.000000). Shadow-ray vs the withdrawn opaque/no-shadow values: median 1.138x, up to 2.01x on sunlit
cards — the first bake was up to 2x too bright; global lum mean 2.02 -> 1.50. The camray variant (cut-out kept for diffuse bounces too) reads 0.929x of the shadow-ray form and
is recorded, not used. Trees: the same override lifts vertex coverage 0.203 -> 0.756 over 347 840 verts (12 of 14 meshes 0.09-0.33 -> 0.86-0.98); broadleaf_s19 and pine_s29
genuinely receive nothing (confirmed full shadow). So most of the zeros in the shipped COLOR_0 since Gate 3 were transparent-vertex artefacts, not shade; the export re-encodes
COLOR_0 from the new npz. Join: per mesh, nearest translation, tolerance 0.02 m (closest same-mesh pair 0.088 m).

## 2026-09-17 · Water round 7 accepted as the 6a default: reflSat 1.0, procedural ripple, derived displacement (lead, from the r7b review's note)
The 09-16 entry said reflSat 0.66 was to be "tested at 1"; the test showed it was the warm drain (it double-counted the murk the body term now carries; a dielectric's reflection is
spectrally flat), so reflSat 1.0 and reflectTint 1.0 ship, with reflBlur 0.003 and the procedural 8-octave ripple (1.20 m -> 0.034 m, slope rms 0.0131 rad from the reference's
reflection wander) and the displacement as the projection of the slope. Where the building reflects, lum 1.01x and hue within 3.3° of Cycles; the open water's residual (lum 0.75x,
hue 196 vs 145°) is the reflection lobe against the sky and stays as a delivery note. The displacement is world-axis-locked and exact only near the hero heading (documented).

## 2026-09-17 · FINAL JUDGEMENT OF 6a (lead, Fable; the single Fable QA pass of Phase 6): 6a CLOSED at parity, 45 fps left to the user's preset choice
Inputs: QA 15 (212ca27, Opus xhigh: 6a PARITY REACHED, scores 01 3.72 / 02 3.00 / 03 2.56 / 04 2.88 / 05 2.94 / 06 2.83 against Phase 5 3.67 / 2.94 / 2.56 / 2.81 / 3.06 / 2.67,
every station within 0.5, none below 2.5, MAE down at all six) and the lead's own six-station 100 % tile pass on round15 (43b1e0a). The lead's tiles agree with the critic's:
architecture, ornament, lightmaps and the sky are at parity at every station (the rotunda pair tiles at cam01 are near-indistinguishable from Cycles; the cam04 ceiling has no
defect); the hero water is now credible (the reflection breaks into warm streaks as Cycles', the hard line is gone); the residual that a walker will see is the FOLIAGE and the
BACKDROP, not the building: shoreline shrubs are sparse pale-yellow leaf-card confetti with black alpha gaps, near trees read as blue-violet smeared blobs (impostors beside sharp
neighbours at cam01/05, a hard-edged dark blob at cam02), the S-colonnade wall is a flat cream field with hard-edged leaf cards, the backdrop is untextured mustard boxes with
faceted polyhedral far trees at cam06, the open water beside the reflection is a saturated blue slab (hue 196 vs 145°, sat 8.9x), the near colonnade shafts show vertical smearing
at 100 % at cam03, and cam03's near shade floors at p10 53 vs 17 because probe-lit surfaces without baked light have no occlusion.
Verdict: 6a is closed by both halves of the stopping rule (parity, and the second round after Gate 4). Not met: the >= 45 fps target (35.5 fps at 1440p with the full look;
`?quality=fast` half-res bloom + half-res Reflector + reflset=orn is the documented preset; a scored 1440p measurement of that preset on the round15 build is owed at delivery and
the choice of default is the user's, as decided 09-16). Post-6a backlog, in hero-visibility order: (1) shrub/reed/leaf-card albedo and card density (bake/export: the cards' hue is
57.7 vs 102.4°, a material/albedo bake matter, and the cut-out cards need volume — denser cards or a card-cluster impostor); (2) near-tree impostor smear and colour at cam01/05;
(3) baked occlusion or a lightmap for the probe-lit surfaces (cam03 near shade, S-colonnade wall, backdrop wall 1.26x); (4) backdrop textures and far-tree impostors at cam06;
(5) open-water reflection lobe vs sky (hue/sat); (6) column-shaft UV stretch at cam03; (7) walk probe re-run at 30 s per heading; (8) the frame budget. None of these is a
building defect; the export set has 0 placeholders to explain (name sweep), 127 hidden ENV_treeboard_* the standing exception. Phase 6b (web deployment) is the next plan:
docs/briefs/phase6_plan.md Gate 5, and the user names the iPhone.

## 2026-09-17 · Delivery defect found by the user: the viewer's bare-URL defaults were the Gate 0 development settings (lead fix 5e1fffa)
The user opened the viewer at its bare URL and saw six bare column shafts on a flat lagoon: main.js defaulted `manifest` to the Gate 0 slice (18 meshes, 73 MB), `billboards`
and `treeboards` (placeholder quads) to ON and `post` to none. Every QA capture passed the delivery flags explicitly through gate4.sh, so no round ever saw the bare page. Fix:
the defaults are now the QA'd look (gate3 manifest, billboards/treeboards off, post all); the captures are unaffected because they still pass the flags. Verified in headless
Brave (the user's browser) at the user's 1422x1630 window: 640.1 MB, 279 draws, the full building. Lesson for the checklist: a gate must include one capture with NO query
string. Also: web/node_modules had become a symlink loop across the checkouts (the viewer and export worktrees link to MAIN's; MAIN's pointed at itself); reinstalled from the
lockfile in MAIN. `npm run dev` crashes in a Vite middleware hook and is unfixed (the static build is what the captures and the user use).
Foliage at close range (user's cam02 screenshot): the near-left tree is a leaf-card tree at LOD1 (large flat cards, low-res cut-out, no translucency, one irradiance per vertex),
the centre blob is a far-tree IMPOSTOR whose "far" classification is fixed at export by distance to the hero station, so at cam02 it stands a few metres from the camera at
85 px per frame, and the shrubs/reeds are LOD2 card meshes with a hard mask. These are the post-6a residuals already listed in the final judgement; the proposed fix is a foliage
pass (6c) offered to the user, not started.

## 2026-09-17 · User: foliage pass (6c) before 6b; the full look stays the default preset; the iPhone is still to be named
Plan docs/briefs/phase6c_foliage.md: every tree gets a mesh (127 far trees at LOD2 in a lazily-loaded env_trees.glb, runtime mesh/impostor switch by walker distance, 2K impostor
atlas), a leaf shader (two-sided, translucency, soft edges, bent normals), shrub/reed LOD1 within 30 m with the albedo hue fixed in the export, 2K leaf textures. Acceptance by
100 % tiles at stations 1/2/5 and QA 16 (no station drops > 0.1, station 2 rises, +3 ms budget). Two rounds maximum. The impostor blue cast is diagnosed atlas-vs-viewer before any
re-bake. 6b (deployment) follows; the fast preset stays documented and non-default.

## 2026-09-17 · Impostor blue cast is the isolated bake's open sky, not the encode or the viewer (bake f41ba19); impostors get per-placement modulation, no atlas re-bake
The shipped atlas frame matches a fresh Cycles render of the same view within 4 % (hue 211° vs 213°), the diffuse-branch sky would move it +2.4° the wrong way, the leaf albedo
has no blue (sun-only hue 59°), and 100 % of the blue is the sky term: gate3_imp.blend bakes each prototype alone on a lawn under the whole unoccluded sky, whereas in the
scene the same tree as a mesh in the Phase 5 reference at station 2 reads hue 52° (147° apart, 3.4x the blue). Decision: impostors beyond the mesh distance are drawn as
atlas x (E_placement / E_bake): the per-placement irradiance of item B divided by the irradiance of the isolated bake environment per prototype (16 values, bake item 2). The
one-off diagnosis used export/gpu_lock.sh for status.json (accepted); export/sync_main.sh must stop copying bake_queue/status.json (export engineer) — it overwrote the lock once.

## 2026-09-17 · 6c export findings (export d553a5a) — three lead decisions
(1) The shrub warmth is not a hue error in the albedo: env.glb ships the raw 1K card PNG, so MAT_shrub / shrub_light / shrub_dry are three identical mid-green cards (hue 95, value
0.34) where the Phase 5 materials tint them to 95/0.46, 94/0.52 and 36/0.60 (straw) and MAT_reeds to 0.65; the cam02 warmth is the missing Translucent branch (a green-biased
colour multiplier x translucency), which now ships as a per-material factor map. Decision: the export bakes the TINTED albedo per material (export fidelity, not a Phase 5 change)
and the viewer's leaf shader consumes the translucency factor; next session. (2) There is no 2K foliage source (every map is generated at 1024): the 2K set is an upsample and does
not ship; 1K stays; a real 2K would be a Phase 5 material regeneration and is not requested. (3) Shrub LOD1 in its own env_shrubs.glb (accepted: putting it in env.glb would rebuild
the UV1 atlases every bake is pinned to). Also accepted for review: -vpf instead of -vp 16 on the new glbs (with -vp 16 gltfpack folds the dequantisation into the instance rows
and the positional join is unrecoverable); 3 of 28 shrub meshes have no LOD1 and stay LOD2.

## 2026-09-17 · Session 5: three round-1 reviews (docs/reviews/phase6c_{bake,export,viewer}_r1_review.md) and what they change
Bake MERGE WITH FIXES, export MERGE WITH FIXES, viewer SEND BACK on one line: the mesh/impostor dissolve keeps the same hash set on both sides (mesh `hash > 1-t`,
impostor `hash > t`), so mid-fade half the crown is drawn twice and half is see-through; the impostor test becomes the exact complement. All fix-now items are forwarded
to the running round-2 engineers (messages recorded in status.md). Two lead decisions from the bake review: (a) E_bake is measured on the body that produced the atlas
(the gate3_imp.blend _LOD1 prototype), with the same mean_nonzero-over-cov reducer as E_placement, both taken raw; (b) because the review shows the atlas blue is not a
diffuse term (a sun-only render reads B = 0 with three blue fill lamps in the rig, a sky-only render reads B 0.387: a specular/transmission response to sky radiance),
the E_placement/E_bake ratio is VALIDATED ON ONE PLACEMENT (the prototype nearest cam02; B/G must move from 1.356 toward the reference 0.648) before the 16 jobs are queued.
If it fails, the lead chooses between a neutral-nursery atlas re-bake (sun + grey ambient, no sky) and shipping the far-tree meshes without impostor modulation; the vertex
AO and the 127-placement irradiance run regardless. The overwritten asis/diffuse diagnosis numbers (finding 3) are not re-spent on the GPU; the README notes their provenance.

## 2026-09-17 · E_placement/E_bake validated on one placement (bake 3f2dc91): the RAW ratio ships; and the far-tree meshes were 300 m off
TREEFAR_000 (broadleaf_s53, 40 m on station 2's axis): E_bake [3.04, 2.25, 5.58] on the _LOD1 nursery object that produced the atlas, E_placement [3.19, 2.24, 0.98] ->
ratio [1.05, 0.99, 0.175]: same warm light, 5.7x less blue; through the delivery LUT the crown hue goes 205.5° -> 72.6° against the reference 52.2° (86.7 % of the gap,
no overshoot in hue). On B/G alone it overshoots (1.267 -> 0.041 vs 0.648), a ratio of a 1.2/255 blue channel. Decision: ship the raw per-channel ratio, no exponent
(the k = 0.4386 variant that matches B/G lands the hue at 105.4°, worse), clamp 4.0, fall back to 1 on a zero E_bake channel; `?impmod=full` becomes the viewer default
once the manifest block exists. All 36 jobs ran (764 s): vertex AO calibrated (1 km plane = 1.0000 in every job), 127 placements none dark, E_bake per prototype with cov.
Defect surfaced by the bake's own placement of the same meshes: export/trees_far.py bakes the prototype world matrix into the LOD2 mesh and never subtracts the anchor,
so every far tree in the shipped env_trees.glb stands ~300 m from its impostor; only the z assert fired (review finding 1: the placement assert was a tautology).
The export engineer fixes it before the COLOR_0 re-run; the new assert compares the gltf node translation with the impostor placement AND the placed bbox with the
impostor quad; the viewer's round16b info block reports the max mesh-vs-impostor deviation and stops if it exceeds 1 m.

## 2026-09-17 · Export r2 (ebdf4e5): tinted albedo ships, 2K dropped, COLOR_0 was constant white, and the far-tree LOD2 gets a topology revision 2
Tinted shrub/reed albedo: value 1.35-1.5x up (shrub 0.344 -> 0.464, reeds 0.491 -> 0.651), dry shrub hue 36° straw; the near-tree materials carry an identity tint, so
the cam02 hue gap (57.7° vs 102.4°) is the missing Translucent branch, which the viewer's 6c leaf shader supplies, not the albedo. 2K set dropped (22 KTX2, 13.0 MB).
Defect the export found in its own output: the glTF exporter wrote a constant white byte COLOR_0 beside the real AO layer in COLOR_1, so the far-tree AO would have been a
silent no-op in three.js; the attach now decodes every colour attribute from the .bin, promotes the one non-constant layer and drops constants, and verify_glb reads
COLOR_0 from the glb rather than echoing the builder. Decision: two prototypes floating 2.4-2.8 m x s above trunk_base (cypress_column_s2, redwood_s13; cause = the
branch COLLAPSE decimate dropping the lowest geometry, not the cards) are fixed with Decimate vertex-group protection, shipped as ONE topology revision (`topology_rev: 2`)
together with the card-thinning stride from review finding 3; the AO is re-baked on rev 2 (16 jobs, 44 s GPU) and the attach refuses a revision mismatch. The bake's
four irradiance jobs on the export's anchor are unaffected (join by location). shrub_lod1's placement check is the exported node translation against to_gltf (0.050 mm),
not the LOD2 bbox-centre distance the brief named (0.2-1.95 m by construction, reported only).
Addendum (bake r2b 9844bc0, after the anchor fix): the one-placement validation re-measured E_placement [3.159, 2.223, 1.020], ratio [1.038, 0.989, 0.183], display hue
205.5° -> 73.1° vs 52.2° (86.4 % of the gap, no overshoot); the B/G-matching exponent would be k = 0.4506 (hue 105.6°, worse). Conclusion unchanged: strength 1.0 ships.

## 2026-09-17 · Viewer r2 (1dc121d): far-tree meshes only within 12 m; the modulated atlas wins at distance; resident memory 1 717 MB
Measured by the viewer engineer at the stations: the 8 k-triangle LOD2 crown at station distance scores worse than the modulated atlas (far-tree box 1.957x, hp9 34.56 vs
the atlas's 1.284x / 17.12 against the reference 39.4 / 17.46) because the atlas carries the dense tree's self-shadowing and a thinned crown does not; translucency, tinted
albedo and environment AO each move it under 0.05x. Decision (engineer's, accepted by the lead): `?fartreemesh=` defaults to 12 m per placement (the walker sees a mesh
only when standing at a far tree), near trees keep 40 m; the blue blob at station 2 is fixed by the E_placement/E_bake modulation (`?impmod=full` default, 145 trees
modulated), station 2 MAE 23.13 -> 20.08. A permanent placement gate (mesh bbox centre vs impostor quad centre < 1 m; today max 0.73 m, median 0.25) refuses to draw
env_trees.glb otherwise — it read 905 m on the pre-fix glb. Cost: every station within +3 ms of round 15 (hero +1.9 ms); resident GPU memory 1 800.6 MB (round16b_perf.json; the README and this entry first said 1 717), +116 over
round 16 and above the 1 200 MB Gate 1 budget (6a shipped at ~1 055 resident in the manifest's accounting) — QA 16 reports it; 6b's mobile tier is where it is cut.
Open (export, post-6c): a walk-up that stops at a far tree sees the LOD2's grown cards and the magnified 1 K atlas; that tree wants its LOD1.

## 2026-09-17 · Lead 100 % tile judgement of round16b at stations 1, 2, 5 (renders/web/960/lead_tiles_r16b_cam0{1,2,5}.jpg; 640x460 crops at 100 % beside the Cycles frame)
Verdict: the 6c round-1 fixes hold (no blue blob, far trees placed, station 2 numerically up), but foliage at close range is NOT yet credible; a second 6c round is
needed (the brief allows two). What the tiles show, station by station:
- Station 2 (the user's complaint): the tree that fills the frame is now green but a smooth opaque rounded mass with no leaf or branch structure — a magnified 85 px
  impostor frame beyond the 12 m mesh distance; the reference is a dark tree with visible branching. The near-left tree is a soft mass; the far impostors at the top-left
  read pale lavender against the reference's dark green; one reed spray is several times the reference's size; the shore shrubs are pale confetti.
- Station 5: the near trees (meshes, within 40 m) render as uniformly lit yellow-green clouds — the crown-bent normals plus soft edges remove the interior shadow that
  gives the reference's trees their volume; the shore shrubs are straw-yellow sparse card clusters where the reference has dense, dark-green, species-distinct shrubs.
- Station 1: acceptable at distance; trees in front of the colonnade are lighter and yellower than the reference, the left-shore shrubs pale; the untextured backdrop
  wall behind the north bays is the known 6a residual.
Round-2 items, owners to be fixed after QA 16's boxes (the critic measures level/hue/sat of the shrub and tree boxes at 2 and 5): (a) viewer — tree interior shading:
reduce or gate the crown-bent normal blend and add an interior-darkening term (the near trees carry COLOR_0 irradiance, the far meshes vertex AO) so crowns stop reading
as balloons; (b) shrub brightness/colour — decide from the boxes whether the tinted albedo, the per-placement irradiance or the translucency term is what makes them
straw-pale (export or viewer accordingly); (c) the station-2 fill tree — measure its distance; if the mesh at that magnification reads better than the blob in a tile
(not in the box metric alone), raise fartreemesh to cover it; else the impostor atlas needs a finer near-frame set for that prototype. Reed-card scale checked against
the reference at station 2.
Ratified (viewer r2 review carry 9): the 12 m far-tree mesh default (above) and `?farao=1` — the far meshes' vertex AO also attenuates the environment lobes
(iblIrradiance / radiance), beyond the manifest's stated COLOR_0 x placement rgb use; measured 0.042x on the far-tree box and kept on its merits.

## 2026-09-17 · QA 16 (8cf34ec): ONE MORE ROUND — the last 6c round; owners
Scores 01 3.72 / 02 3.13 (+0.13) / 03 2.56 / 04 2.88 / 05 2.94 / 06 2.83; the stated acceptance passes (no drop, station 2 rises, +1.9 ms) but the tiles do not: crowns are
balloons (cam02 centre/edge 0.504 vs 0.364, cam05 1.26 vs 1.77), shrubs 1.34-1.70x too bright with 2-8x the hard-edge share, the walk-in reads as cut-outs. Round 2 of 2:
viewer owns crown interior/rim and the shrub level/edges (after the export settles the albedo with a Cycles DiffCol pass — the lead doubts "albedo" because the tint is the
Phase 5 material's own; the likelier cause is the mean_nonzero irradiance reducer without cov and no self-shadow); export ships a walk-up LOD1 glb for the 16 prototypes
(<= 30 k tris each, no AO bake). Resident memory is 1 800.6 MB (1.5x the Gate 1 budget); accepted for 6c, cut in 6b's tiers. After round16c: QA 17, the lead's tiles, then
6b regardless of the result (the two-round rule).

## 2026-09-17 · Export r3 (edaa437): the shrub albedo is NOT the cause of the shrub brightness — it is lighting (viewer); walk-up LOD1 glb shipped
A Cycles Diffuse Colour pass at cam02/cam05 (foliage isolated, film transparent) divided into the shipped tinted albedo gives 0.87-0.98 in every QA-16 shrub box (per
material shrub_light 0.98, shrub 0.92, shrub_dry 0.90) — the shipped albedo is at or below what Cycles uses, so QA 16's "owner EXPORT" is overturned by measurement and
the 1.34-1.70x level excess is the viewer's lighting of the cards (the mean_nonzero irradiance without cov, no self-shadow, the translucency term). Three confounders
were measured (alpha population 1 %, footprint < 1 %, packed vs disk PNG identical). Residual: MAT_reeds reads 1.49 on 0.6 % of card pixels with a node chain identical
to the seven that agree; left unfixed (a 0.69 scale would be fitting a number; moves the worst box < 0.3 %) — delivery-notes residual. env_trees_lod1.glb (7.6 MB,
25.6-30 k tris per prototype, no AO, same placements and order) is the walk-up set, manifest `trees.walkup_mesh` draw_within_m 15.

## 2026-09-17 · Viewer r3 (33903b8): two look decisions ratified, and the lead's 100 % tile judgement of round16c (renders/web/960/lead_tiles_r16c_cam0{1,2,5}.jpg)
Look decisions (viewer engineer's, measured, accepted): (1) the environment lobe on flat foliage cards (PMREM + sheen) was the shrub brightness — `?cardenv=`/`?shrubenv=`
default 0.3 takes the shrub boxes from 1.34-1.70x to 0.88-1.36x of the reference and cuts the hard-edge share at six boxes of seven; the brief's cov hypothesis was
measured wrong (< 0.01x). (2) An enclosure term on the impostor atlas (`?impint=0.90,0.015`) gives the crowns their interior: cam02 centre/edge 0.394 vs ref 0.364,
cam05 range/mean 1.722 vs 1.773; the mesh-side crown bend is gated to the outer shell and kept for the walk-up. Resident memory 1 931.4 MB (+131, all the walk-up set's
472 k unique tris; 1.61x the Gate 1 budget) — accepted for 6c on this Mac, 6b's tiers cut it.
Lead's tiles, before/after/reference at 100 %: station 2 — the fill tree is now a dark crown with a lit rim instead of a green cloud, the near-left tree likewise; the
shrubs are darker but still read as card clusters; the far impostors at the top-left are still lavender; one reed spray is still several times the reference's size.
Station 5 — the crowns have volume (dark cores, lit shells) and the shore shrubs sit near the reference level; a few crowns go blotchy near-black where the enclosure term
and the sun-path term stack. Station 1 — the colonnade trees now have shadowed cores; the left-shore band is still paler and sparser than the reference. Verdict: a
clear improvement, credible at the stations, not yet at 3 m in the shrub band; the two-round rule closes 6c after QA 17 whatever it scores; the residuals above go to
docs/delivery.md with owners (shrub structure = a denser LOD1 card set, export; lavender far impostors = the modulation at the horizon band, viewer; reed scale =
export; blotchy crowns = clamp the stacked darkening, viewer).

## 2026-09-17 · 6c CLOSED WITH RESIDUALS (QA 17 at 47a2f7e on round16c; the two-round rule) — residual owners; 6b starts
QA 17 scores 01 3.78 / 02 3.25 / 03 2.63 / 04 2.88 / 05 2.94 / 06 2.83 (round 15: 3.72 / 3.00 / 2.56 / 2.88 / 2.94 / 2.83; no station drops, three rise;
station 2 +0.25). The 6c acceptance passes on three conjuncts of four (no drop; station 2 up; crowns with interior AND shrubs at the reference level) and
fails the +3 ms conjunct on the cold pass of record (+4.2 / +4.8 ms at stations 1 / 2 against a round-15 figure from another day; draws and triangles
identical there). Round 2 of 2 is spent, so 6c closes whatever the tiles still show (QA 16 decision). The lead's round16c tile judgement (above) and QA 17
§4-5 agree: crowns credible at the stations, the shrub band still card clusters at 3 m, station 5 the one station 6c made measurably worse (frame 3 %
under, blotchy near-black crowns where the enclosure and sun-path terms stack).
Residuals, with owners, carried to docs/delivery.md (Phase 6c section) — none is worked before 6b ships; every one is 6b-or-later backlog, and any fix
that touches the frozen look needs its own entry here first: (1) shrub/reed card STRUCTURE = a denser, smaller, more varied LOD1 card set, EXPORT
(not another shading term); (2) the stacked darkening overshoots (hero crown p10 0.57x, station 5 under, blotchy crowns) = clamp impint + crownint +
sun-path and hold the frame at 1.00x, VIEWER; (3) the pale halo around dark crowns = the impostor alpha fringe (premultiply / mip bias), VIEWER;
(4) far-tree tops opaque where the reference shows sky = atlas alpha at the crown top or a mesh at that distance, BAKE/EXPORT; (5) the lavender far
impostors at the horizon band (lead's tiles) = the modulation at the horizon, VIEWER; (6) one reed spray several times the reference's size = EXPORT;
(7) MAT_reeds albedo 1.49x on 0.6 % of card pixels = EXPORT, deliberately left (measured, < 0.3 % on the worst box); (8) resident 1 931.4 MB = 1.61x the
Gate 1 budget and a 664 MB payload = 6b's tiers; (9) the +3 ms gate = settled by the same-session perf A/B (result appended below); (10) carried from
6a unchanged: cam03 no deep shade and blurred/banded column concrete at 1 m (materials/export texel budget), cam06 water moiré, flat backdrop blocks and
faceted backdrop trees (in the Cycles source too), untextured colonnade backdrop walls (N 1.26x), hero reflection cooler/less saturated than Cycles,
30.9 fps cold at the hero against 45.
Perf A/B result (same session, docs/perf_ab_6c.md; passes A/B/C = round-15 look / 6c look / round-15 look, 2560x1440, gate4 settings): 6c look minus
the mean of the two round-15 passes = +1.75 / -0.75 / +3.10 / -0.10 / +0.90 / +0.85 ms at stations 1-6, with an A-C drift of +0.30 / +2.10 / +0.80 / +1.40 /
0.00 / -0.70 ms. The +3 ms conjunct therefore PASSES at stations 1, 2, 4, 5, 6 and sits on the line at station 3 (+3.10 against a 0.80 drift; the only
station whose triangles rose, 4.49 -> 5.98 M, the walk-up LOD1 within 15 m). The cold pass's +4.2 / +4.8 ms at stations 1 / 2 was day-to-day machine drift
(the same-day round-15 look reproduces round 15's 28.2 ms and its 279 draws / 4.14 M tris exactly), not a 6c regression. Resident 1 931.4 MB for the 6c
look against 1 788.0 MB for the round-15 look on the same build (+143 MB = the walk-up set). Residual 9 is closed; station 3's +3.1 ms goes to 6b's tiers
with the memory.
Decision: 6c is closed. Phase 6b starts on the user's three answers (iPhone model; host — the lead recommends Cloudflare Pages + R2 per
docs/briefs/phase6b_hosting.md; whether the 50 MB tier-0 first look may be lower-resolution). The Gate 5 briefs are written only after those answers.

## 2026-09-18 · 6b: the user's three decisions, and the hosting refinement (free tier)
User's answers to docs/briefs/phase6b_plan.md: (1) iPhone **16 Pro / 16 Pro Max** (A18 Pro, 8 GB; ASTC via KTX2 transcode; mobile tier target 30 fps,
< 700 MB resident); (2) host: "I have a free Vercel plan; if you have something free, go ahead" — Vercel Hobby cannot serve the payload (Blob stops at
10 GB/month, ~12 downloads), so the host is **Cloudflare, free tier**; (3) the 50 MB tier-0 first look **may** show the building at placeholder resolution
with a progress readout; tier 1 sharpens it.
Hosting refinement (lead): Cloudflare **Pages alone** (unmetered bandwidth, 20 000 files, 25 MiB per file, same origin, no CORS/COEP) carries everything
once no file exceeds 25 MiB — the tier split cuts orn.glb (154 MB) into visibility-ordered groups anyway, and the mobile textures are half-size ETC1S.
Any file that must stay over 25 MiB (a 4K UASTC atlas, if one survives the tiers) goes to R2 (free: 10 GB, free egress) behind a Pages Function binding at
the same `/assets/...` path, so the viewer sees one origin either way. No custom domain: `<project>.pages.dev` is the unlisted staging URL. The user
runs `npx wrangler login` once, in the session, when the deploy script is ready (the lead asks; no credential is stored in the repo).
Gate 5 briefs: docs/briefs/phase6b_export.md (tiers, per-station visibility, mobile manifest, ETC1S; branch phase6b-export) and
docs/briefs/phase6b_viewer.md (progressive loading, tier switch, deploy script, Pages Function fallback; branch phase6b-viewer). Both Opus high.

## 2026-09-18 · Gate 5 export merged (939eb53); tier-0 budget is wire bytes; the third delta was lead-verified, not re-reviewed
The 50 MB initial payload is measured as Chrome's network log sees it (body + headers, Brotli where Pages compresses), which is what the QA brief reads.
The export's estimate carries a measured 162 B per-request header allowance and counts .hdr/.glb/.cube/.wasm at disk size; desktop first frame 49 316 003 B,
mobile 47 556 566 B, target 49 500 000 to leave margin for Chrome's count. Trim = 31 placeholder maps (largest 0.019 % of the hero frame) dropped from tier 0,
their full-res files being in tier 1 anyway. The probe is in tier 0 (the viewer showed tier 0 without it as sky-lit blue on the colonnade and podium). The water
ripple is procedural, so the tier-0 water differs only in what it reflects. The three `.001` shrub cards are drawn inside a gltfpack-merged plain node; their
irradiance row cannot be keyed and they stay on the probe (3 of 1 379) — carried. Reviews r1 and r2 (MERGE WITH FIXES, all applied); the third delta (the wire
pass) was verified by the lead against the MAIN manifests (first_frame_on_wire_bytes, tier0_within_target, unpublished 0, verify_gate5 fail [] on 2 540 assets)
instead of a third reviewer round, to hold the budget; logged here as the deviation.

## 2026-09-18 · Gate 5 frame time: the tiered plan costs -0.1 / +2.0 ms at stations 2 / 3 (same session); the URL's +7 / +4 vs the A/B baseline is drift — no change
A cold pass on the staging URL gave 30.8 / 37.2 / 37.9 / 24.3 / 33.2 / 34.3 ms against the 6c A/B pass B (29.7 / 30.4 / 33.5 / 22.0 / 29.8 / 32.3). The viewer engineer's
same-session A/B on one build (gate5 plan vs v4 plan, stations 2 / 3): 35.30 / 35.30 vs 35.40 / 33.30 ms, so the plan costs -0.1 / +2.0 ms and the v4 build itself sits
+5.0 ms over the pass-B figure in this session — the same day-to-day drift the 6c A/B found; only a same-session A/B is callable. Structural cost of the split, carried:
a class shipped as two groups is parsed twice, so shared materials exist once per group and compile their own programs (141 / 143 programs vs 94 / 96, 254 vs 198
geometries, 135 vs 112 materials, +5 / +4 draws); the texture cache is net lighter (resident 1 861 vs 1 906 MB). The export lever (one group per class, ~7 MB more
geometry in tier 0) would push tier 0 over 50 MB on the wire, and the viewer lever (materials shared across groups) is large and risky; neither is taken in 6b.

## 2026-09-18 · 6b DONE WITH RESIDUALS (QA 18b, 98ab252) — the project's web deliverable is live; stopping per the 6b rule
Staging: https://pfa-walkthrough.3d-render-blender-3rd-attempt-building.workers.dev (Cloudflare Workers static assets, free tier, unlisted). Desktop: 46 808 904 B before the first frame on the URL (<= 50 MB), parity with round16c at
all six stations (luma 1.000, MAE <= 0.001/255 vs the previous capture; 0 of 25 boxes > 3 % vs round16c), scores carry 3.78 / 3.25 / 2.63 / 2.88 / 2.94 / 2.83,
resident 1 861 MB (-70 vs 6c), hero ~32 fps. Mobile (iPhone 16 Pro tier, scored on gate5c): whole scene at all six stations, 142-180 draws / 1.5-1.9 M tris, resident
499.7 MB (< 700), first frame 46.7 MB, total 61.7 MB, 0 page errors; first mobile scores 2.9 / 3.0 / 2.3 / 2.7 / 2.5 / 2.4. One fix round was spent (mobile groups
unpublished; canvas scaling fixed within the closing round). The rule "6b stops at deployment plus one clean QA round" is met; polish beyond is a new phase.
Residuals, owners, first items of any follow-on: (1) VIEWER — the mobile water reflects nothing (reflectionSet kept 1 vs desktop 134): no rotunda in the hero lagoon,
station 5's lower half flat, station 6's bay a near-black band; fix = a reduced reflection set (ARCH class only) on the mobile Reflector at 512, then re-measure mobile
frame time. (2) VIEWER — mobile portrait framing: the horizontal sensor fit at 1170x2532 leaves the building small and centred; a portrait station/sensor-fit choice.
(3) EXPORT — 302 by-reference mobile paths outside files[] (published via the desktop plan; verify_publish covers them, the plan does not name them). (4) EXPORT —
the split's duplicate materials/programs per group (141 vs 94 programs) and the -si 0.5 mobile decimation facets; the three .001 cards on the probe; arch/ground
embedded stand-ins. (5) Carried from 6c/6a unchanged (docs/delivery.md). Owed from the user, not blockers: the macOS Safari hero screenshot and the iPhone 16 Pro
30 s walk on the URL (every capture is headless Chrome).

## 2026-09-18 · Post-close fix: the bare staging URL drew the TEST SCENE (default manifest path was the unpublished gate3 one)
The user opened the bare URL on the iPhone and saw the viewer's test scene (a cylinder and posts on a plane). Cause: main.js defaulted `?manifest` to
/assets/gate3/manifest.json, which is not in the published set (404), so the manifest yielded 0 glbs and the viewer fell back to its test scene. Every capture and both
QA rounds passed `?manifest=/assets/gate5/manifest.json` explicitly; QA 17's bare-URL check ran locally where gate3 exists. Fix (lead, one line, 1c4b0f5): default =
/assets/gate5/manifest.json; rebuilt, redeployed (deploy 5), verified with a headless capture of the bare URL at the hero (6 glbs loaded, building present). Gate rule
added to docs/quality_checklist.md: every deployment QA round captures the BARE URL on the deployed host with no query string, and a test-scene fallback on a bare
URL is a blocker. Viewer carry: on the bare URL a missing manifest should show an error screen, never the test scene.

## 2026-09-18 · 6d (mobile polish, lead fix, one round): the mobile water reflects the building; HUD formatting; worktrees removed
After the user's iPhone screenshot confirmed the mobile tier loads, the first 6b residual was fixed as a lead fix under 20 lines (d40a125): the mobile tier's
reflection set goes from `all` (sky only) to `both` (ARCH, ground, water-adjacent ENV and impostors reflect; ORN and backdrop excluded) at the half-res 512 target.
Local mobile captures at stations 1 / 5 / 6 (renders/web/960/6dm_cam0N.jpg): the rotunda and colonnade reflect in the hero lagoon, station 5's lower half has its
reflection, station 6's bay is water again. Cost: 278 / 265 / 300 draws against 169 / 163 / 180 (the second scene pass); the headless Mac measure is vsync-capped
at 16.7 ms so the phone's own frame rate is judged from the user's walk recording (owed). The station HUD prints shift_y to two decimals. Deployed (deploy 6).
The merged phase6b worktrees were removed (branches kept). Remaining residuals stand as listed under "6b DONE WITH RESIDUALS"; no further polish is scheduled
until the user says whether the 4.0 hero target (Phase 5 / 6c backlog) is still the goal.

## 2026-09-19 · PHASE 7 APPROVED by the user (foliage look, desktop far trees + mobile near trees) — reopens the 6c-frozen foliage look
The user's two screenshots on the live site (desktop hero: jagged dithered far-tree silhouettes, black-blotched crowns, flat shrub clusters; iPhone close orbit:
flat impostor cut-outs with black cores because the mobile tier draws every tree as an impostor) and the lead's recommendation. Scope, all viewer-side and measured
same-session: (A) impostor alpha edge softening (premultiplied alpha / mip bias / alpha-to-coverage) — QA 17 residual 3; (B) a floor on the stacked crown darkening
(impint + crownint + sun path) so no crown goes near-black and station 5's frame returns to 1.00x — QA 17 residual 2; (C) a same-session A/B of the mesh switch
distances at the hero (treemesh 40 -> 60 / 80, fartreemesh 12 -> 30 / 60): adopt the largest that stays within +3 ms of the current default and +100 MB resident;
(D) mobile tier: near-tree meshes within ~25 m, the walk-up set within ~10 m, LOD1 shrubs inside that radius, impostor darkening eased; resident must stay < 700 MB,
triangles reported; (E) the shrub card density (export, Blender) is DEFERRED unless A-D leave it as the obvious fault. One QA round (QA 19) on the URL closes it.
Branch phase7-viewer; brief docs/briefs/phase7_viewer.md; the 6c look switches remain available for A/Bs.

## 2026-09-19 · Phase 7 viewer merged (91f08b4): the adopted foliage defaults and why
Desktop: (A) impostor edge — premultiplied 12-tap atlas reconstruction + alpha-to-coverage with an fwidth ramp (`?impedge=`, `0` restores 6c byte-for-byte);
QA-17 crown boxes: hard-edge share down at all three, the halo ring dL toward the reference at all three. (B) crown darkening floor 0.35 on the atlas and the
mesh crowns: hero crown p10 0.564x -> 0.894x of Cycles, cam02 centre/edge held at 0.397 (ref 0.364); station 5's frame reaches 0.976x and cannot reach 1.00 by
this lever (carry). (C) same-session switch-distance A/B: `?fartreemesh=` is inert in the shipped manifest (the live lever is `?walkupmesh=`); treemesh 80
adopted (free at every station); the walk-up mesh set at 60 m passes +3 ms but over-brightens the cam02 fill tree to 1.97x the Cycles level — the walk-up LOD1 set
is lit brighter than the card it replaces (new item, owner far-tree mesh lighting / export) — so the far-tree switch stays at 15 m on desktop. A+B cost -0.6 ms
at the hero. Mobile: (D) the user's close-up crowns were far-tree cards at 37-40 m (the far-tree mesh radius was 10 m; `treeMesh` governs only the 18 near trees,
nearest 128 m away): new tier field farTreeMesh 45 on mobile, walkupMesh 0 (the LOD2 set, which carries vertex AO and does not over-brighten), LOD1 shrubs 25 m,
impostor darkening eased; resident 561.9 MB (ceiling 700), station 1 340 draws / 4.17 M tris, download +4.1 MB in tier 2, tier 0 unchanged to the byte. The
alpha-to-coverage-at-0.71-ratio hypothesis was tested and ruled out. Review r1 MERGE WITH FIXES, all applied. Shrub card density (export) remains deferred.

## 2026-09-19 · PHASE 7 DONE WITH RESIDUALS (QA 19, 6253d32) — the user's two foliage defects are closed on the live site
Desktop: the jagged/dithered far-tree silhouettes and the near-black crown blotches are gone at 100 % (hero crown p10 0.894x of Cycles, cam02 centre/edge 0.397 held,
halo toward the reference at all three boxes); scores 3.78 / 3.25 / 2.63 / 2.88 / 3.06 / 2.83 (station 5 +0.12). Mobile: crowns at 37-40 m are meshes with branches and
sky through them; resident 561.9 MB; scores 3.2 / 3.3 / 2.3 / 2.7 / 2.8 / 2.4 (from 2.9 / 3.0 / 2.3 / 2.7 / 2.5 / 2.4). Perf inside +3 ms at every station vs the
idle baseline; payload 46 811 106 B before the first frame (+2.2 kB of bundle, no new tier-0 asset). Residuals, owners: (1) far-tree cards are pale opaque masses where
Cycles shows sky through the twigs — now the dominant far-tree fault (QA 17 residual 4; atlas alpha at the crown top, BAKE/EXPORT); (2) shrub/reed card density
unchanged by decision (EXPORT, Blender); (3) the crown floor overshoots where it was not fitted (cam02 crown p10 2.49x, cam05 1.30x of the reference; a per-station
or per-prototype floor, VIEWER); (4) station 5's frame stays 0.976x (not foliage; carried from 6c); (5) mobile: LOD2 leaf cards read too large at 37 m and the shaded
colonnade stone reads blue-violet (present since 6c on mobile; EXPORT card scale / VIEWER probe tint); (6) the walk-up LOD1 set is lit brighter than the impostor
it replaces (far-tree mesh lighting, EXPORT/BAKE). Phase 7 stops here per the one-round rule; the next foliage step, if any, is the export/Blender work in (1), (2), (5).

## 2026-09-19 · PHASE 8 APPROVED by the user: the five remaining art items, in hero-impact order, then a before/after
The user: "finish those as well and show me the difference once it's done". Items and owners: (8a) shrub/reed card density — ENV builder in Blender
(assets/environment.blend LOD1 card meshes, placements unchanged) -> master rebuild -> master_delivery -> export shrub LOD1 + albedo + tiers -> deploy -> QA;
(8b) far-tree impostor atlas alpha at the crown tops (sky through twigs) — bake engineer, analysis first (CPU), then re-compose/re-bake through the bake queue;
(8c) column concrete texel budget at cam03 (blurred/banded at 1 m) — export engineer, analysis first (CPU: texel density per near asset, the 2K set and its
memory/tier cost), then bake/encode; (8d) backdrop city blocks and trees (cam06) — ENV builder after 8a; (8e) mobile LOD2 leaf-card scale (export) and the
shaded-stone blue-violet tint on mobile (viewer). One builder on the GPU at a time (ENV previews, bakes, encodes); CPU analyses run alongside; Chrome never
while Blender is alive. Each item closes with one QA round on the URL; the phase closes with a comparison sheet: viewer hero before (gate7) / after, Cycles
4K hero before (Phase 5 v2) / after (a new render on the changed master), and the reference photo. Budget: the user accepts multi-session; on a usage limit stop.

## 2026-09-19 · 8b decision: ship the baked 2K impostor atlases in tier 1 and sample alpha as coverage — zero GPU time
The bake engineer's analysis (docs/briefs/phase8b_bake_analysis.md, 6072db3): the crown's bounding sphere maps onto 81 inner px at 1K / 162 at 2K while the station-2
crown is 736 px across at 1080p (one 1K texel = 9 screen px); silhouette crossings per 100 screen px: Cycles 7.76, 1K 2.40, 2K 3.28; the bake's leaf density is right
(21.8 per 100 texels). Nothing thresholds alpha in the bake or compose; 93-100 % of covered crown-top texels are semi-transparent and the viewer's ALPHA_TEST 0.33 plus
a saturated a2c ramp under magnification paints them solid — the "pale opaque mass". Since the 6b tiering, tiers.py has stripped the already-baked 2K keys, so the
viewer has drawn 1K atlases (a 6b regression of the 6c look, unnoticed because the QA parity baseline round16c was captured on the same 1K path... to be confirmed by
the export when it restores them). Decision: (1) export names the 2K albedo/normdepth atlases in tier 1 with the 1K as the tier-0 lowres stand-in (tier 0 unchanged
to the byte; +6.4 MB in tier 1; mobile stays 1K); (2) the viewer samples atlas alpha as coverage under magnification (dither / a2c fed by the atlas alpha, no
binary cut) — `?impcov=` switch, 0 restores. Rejected: 4K atlas (54 min GPU, 512 MB), compose-side remap (eats the silhouette). Stretch, only if 1+2 miss the
station-2 crossings target: a 12x3 band atlas at 341 px frames (13 min GPU, 128 MB, +13 MB).

## 2026-09-19 · 8a decision: the shrub lever is LOD2 — clumped AND densified; the Gate 1 ENV placed-triangle budget gets a logged exception
The ENV builder (docs/briefs/phase8a_env_report.md, 496d880): the web export draws the LOD2 shrub set for all 1 379 placements at the stations (the 6c LOD1 set is
the walk-in only), so the QA-17 shrub boxes at 80-160 m measure LOD2 and the brief's LOD1-only change could not move them; the ENV preview harness cannot measure
the boxes either (its olive look saturates the leaf mask, the 1280 -> 1920 upscale destroys the hard-edge share) — the measurement comes from the viewer capture
after export. Delivered: a clump emitter (4-9 cards at four leaf scales, tufted blades), LOD1 unique 17 094 -> 31 268 (1.83x), LOD0 / LOD2 unchanged. Decision:
apply the clumping at LOD2 (zero triangles) plus the densification `card 3.30 / cover 0.85 / blade 0.24` (unique 3 920 -> ~6 948, placed +~105 k against the frozen
800 k ENV budget = +13 %, accepted for the hero; the viewer's frame cost is measured after export). Two harness bugs fixed on the way (env_preview --lod, the
qa_r13 reference root in worktrees). Then: master rebuild + master_delivery, ENV re-export (env groups, shrub LOD1, instance irradiance join by translation),
tiers, deploy, QA 20 measuring the shrub boxes against the reference photo.
Correction after review (docs/reviews/phase8_env_r1_review.md, MERGE WITH FIXES): the script-measured placed counts after the LOD2 change are LOD0 2 420 864 /
LOD1 1 012 912 / LOD2 238 032 (renders/logs/p8a_build_lod2.log); the report's LOD0/LOD1 placed figures were hand-multiplied. Unique LOD0 is unchanged to the
triangle; placed LOD0 moves slightly because far placements draw the LOD1 mesh. Instance scale moved for cap-bound shrubs (REAL_H over narrower cards) with the
sightline cap still holding; keys, positions, rotations and the count (1 379) are untouched. Carries: sorted() source keys past 9 sources, dead `--lod2 clump` arg,
env_p8_boxes hardcoded root, qa_r13 worktree fallback; the blend committed twice on the branch (not squashed).

## 2026-09-19 · 8c decision: the column banding is the detail layer's projection, not the bake — flip `?detailproj` to `dominant` (free); 8b deviations accepted
Export analysis (docs/briefs/phase8c_export_analysis.md, 4a9125b): cam03 resolves 960 px/m at 1 m against 77 texels/m on the near colonnade atlas (12.4:1 = the
blur) and 8.8 texels/m on the merged entablature mass (110:1); the shaft UV is not stretched (1.11); the vertical BANDING is the detail tiling map's objxy
projection on a vertical shaft (15.2 texels/m vertical vs 948 horizontal: every detail texel is a streak the column's full 11.2 m); KTX2 is a measured no-op.
Decision: the shipped `?detailproj=dominant` becomes the default (0 MB, 0 bake; one QA capture round since every station is touched); reserve a triplanar blend
in detail.js if the tile still bands; a 4K re-bake of the two south sets (+75.5 MB resident, +26 MB tier 2, ~20 min queue, still 6.2:1) only if the hero still
reads flat. Rejected: UV re-layout (forces gate1 -> gate3 -> gate5 re-runs, no gain on the merged mass), a finer detail map (already 1.05 mm/texel).
8b export (b4ef4af): the 2K impostor ALBEDO atlases are published at tier 1 (+9.72 MB; the 1K stays published for `?imp2k=0`), the 1K ETC1S stand-in at tier 0;
tier-0 files byte-identical; the 2K normdepth stays stripped because the viewer has no code path for it. Both deviations accepted.

## 2026-09-19 · 8a export gate: the UV1 pin held; CLASS_BUDGET['ENV'] raised 800 000 -> 902 000 so the accepted shrub overage is not taken from the near trees
export_set --gate1 in the worktree reproduced MAIN's uv1 coverage/tiles/groups, uv2 meshes and lightmap slots exactly (Gate 2 bakes and Gate 3 lightmaps stay
valid). But with the ENV budget constant unchanged the allocator took the +102 152 LOD2 shrub triangles out of the near-tree allowance: near trees 20 -> 15, far
impostors 127 -> 132, the billboard list re-indexed (would have forced instance rows/order and possibly an impostor re-bake). Decision: option (b) — the
constant becomes 902 000, which is what "+~105 k accepted" meant; the gate is near 20 / far 127 / impostor placements byte-identical, then the chain runs.
8c-A applied by the viewer (detailproj dominant default): cam03's vertical smear becomes grain and pores, no flute seam, other stations unchanged (MAE <= 0.37/255).
8b-B measured: 2K + coverage 0.15 gives crossings 7.65 / 6.98 / 8.54 at cam01/02/05 (Cycles 11.73 / 7.76 / 15.89) with the boxes holding; at 100 % the
station-2 crown is still a mass ("no sampling of a 162 px frame puts branches back"). Before the band atlas (13 min GPU, +128 MB, three-team lockstep) a free
A/B runs: the LOD2 far-tree mesh set (vertex-AO lit, already in tier 2) at 60 / 120 / all distances on desktop, same session, tiles vs Cycles.

## 2026-09-19 · 8b decision 2: the band atlas goes ahead (after the LOD2-mesh A/B fell short)
The free A/B (web/README.md "Phase 8 far-tree A/B", f0ad577): the LOD2 far-tree set at 60 / 120 / all distances costs nothing (inside +3 ms same-session, -244 MB
resident) but reads as a faceted polygon skeleton at 100 m with the colonnade visible through it — hero crown leaf share 4.0 % vs the reference's 22.2 % (the 2K
card 24.5 %); its crossings score is an artefact of isolated leaf cards. Nothing adopted. Decision: the band atlas per docs/briefs/phase8b_band_atlas.md (12 az x 3 el
at 341 px, 4096x1024, ~13 min GPU, +128 MB, +13 MB tier 1; bake -> export -> viewer in lockstep under one contract), sequenced after the 8a export sync so the
shrub and column improvements deploy first. If the band atlas does not put branch structure in the station-2 tile, the crown stays a residual and Phase 8 closes.

## 2026-09-19 · QA 20 (1a4f401) on deploy 8: 8c CLOSED; 8a NOT CLOSED (+ a walk-in shrub-set bug); 8b part 1 improved but dithered at 100 %
8c: cam03 shaft banding anisotropy 4.76 -> 1.39 (ref 1.60), grain 1.25x of the reference, no flute seam — closed. 8a: the LOD2 densification moved the leaf-green share at
one box of eight (hero shore 0.62x -> 0.84x); the others are unmoved (cam05 shore 0.29x), hard-edge share up at 6/8; at 100 % cam05's band is indistinguishable from
gate7. The structure change is real at 200 % but the metric and the tiles say the shore bands need more than card density (the leaf-green share is a colour-coverage
measure: the cards' albedo/lighting, not their count, dominates it) — owner ENV/EXPORT, re-scoped next session. BUG (owner VIEWER/EXPORT): `env_shrubs.glb` (the 6c
LOD1 walk-in set, 463 922 tris) is drawn in full at every station although `shrubLod` reports lod1:0 — +1.12 M triangles per frame at the five water stations, on
mobile too; fix before any further perf claim. 8b part 1: crossings 5.73 -> 7.99 / 2.92 -> 6.97 / 6.51 -> 8.53 with the boxes improving, BUT every far crown against
the sky carries an ordered dot grid at 100 % (share 0.15 on 2K) — the band pass moved the default to share 0.10 on the band atlas; QA 21 must check the 100 % tiles
for the grid before the band ships as closed. Resident: `resident()` never counted the impostor atlases (~+67 MB unbilled in every Phase 6-8 memory figure) —
correct the counter (viewer) and restate. Station 3 perf +3.1 ms vs gate7 (drift caveat; re-measure same-session after the shrub-set bug). Scores desktop
3.78 / 3.25 / 2.75 / 2.88 / 3.06 / 2.89; mobile 3.2 / 3.3 / 2.4 / 2.7 / 2.8 / 2.5. Blue-violet shaded stone visible on desktop cam02 too (carry).

## 2026-09-19 · SESSION 7 CLOSES mid-Phase 8 (context past the restart threshold) — what is live, what is proven, what is next
Live (deploy 9): band-atlas impostors (default, share 0.10; hero crossings 11.97 vs Cycles 11.73, station-2 crown with limbs and sky), 2K atlases with alpha as
coverage, dense LOD2 shrubs, detail projection dominant (8c CLOSED by QA 20). Proven but not yet QA'd on the URL: the band (gate9 capture on disk). Open: 8a not closed
(leaf share moved at 1/8 boxes; re-scope), the env_shrubs LOD1 walk-in set drawn at every station (+1.12 M tris; viewer/export bug), resident() omitting the impostor
atlases, the 100 % dot-grid check on the band, willow highlight clipping, 8d backdrop, 8e mobile card scale, the closing comparison sheet with a new 4K Cycles hero.
Plan: docs/briefs/phase8_next_session.md. Every merge this session was reviewed except two documented lead-verified deltas (export wire pass; export band block).

## 2026-09-19 · QA 21 (f264b69) on deploy 9: 8b CLOSED — the band atlas is the shipped far-tree look
Crossings per 100 px cam01/02/05: gate8 7.99 / 6.97 / 8.53 -> gate9 11.97 / 7.35 / 11.67 (Cycles 11.73 / 7.76 / 15.89); hero crown hard-edge 4.73 % (ref 4.94),
leaf share 23.4 % (ref 22.2); the station-2 crown tile at 100 % has limbs, needle clumps and sky between the masses (the contract's acceptance). The QA-20 ordered dot
grid is gone from every crown body at share 0.10 (lattice index above control at 3/10 boxes, was 8/10); a new residual: a 1-2 px period-2 dotted rim on far-crown
silhouettes at stations 2 and 5 at 100 %, share-independent (the viewer's sweep shows 1 and 5 byte-identical across share 0-0.40) — owner VIEWER, not blocking.
Willows: no flat highlight (0 px over 240 in six frames), so the `PFA_BAND_RANGE=band` re-bake is not needed. Scores 3.89 / 3.31 / 2.75 / 2.88 / 3.12 / 2.95
(+0.11 / +0.06 / 0 / 0 / +0.06 / +0.06); mobile byte-identical to gate8m. Payload 46 877 329 B desktop / 46 807 348 B mobile before the first frame (the export's
49.4 / 47.6 MB are the planned tier 0). Perf 32.5 / 33.5 / 38.0 / 24.8 / 30.3 / 36.1 ms, faster than gate8 at every station; QA-20's station-3 flag clears. Resident
sidecar 1 862.9 MB; corrected estimate ~1 978 MB until the counter fix (viewer fix round). Lead viewed the sheet: the station-2 crown is still softer than Cycles
(a residual of the 341 px frame, accepted by decision 2: "if the band does not put structure in the tile the crown stays a residual" — it did, so 8b closes).

## 2026-09-19 · 8a decision 2 (re-scope): the shrub gap is the cards' flat warm shading — viewer-only directional relight; the leaf-green share becomes a report figure
The analysis (docs/briefs/phase8a_rescope_analysis.md, 9707e98; evidence renders/qa_comparisons/p8a_rescope_boxes_viewer_vs_cycles.jpg, viewed by the lead): at all
eight QA-17 shrub boxes the gap is colour, not coverage (the card footprint is already 1.04-3.6x the reference's leaf share) and not species (same mix, all LOD2).
The viewer strips the cards' sun diffuse and adds one warm per-placement irradiance with no cosine (G/R 0.774): an albedo of hue 100° renders at hue 54 under that flat
light and at 130 under the same bake's darkest decile — the reference's dark green bushes with gold rims are modelled light and shade; ours are one sun-gold value.
Decision: option B — split the flat card irradiance into a sun term (N·L on the card normal + clump shadow, sun vector and colour from the manifest) and a sky term,
`?cardsun=` with 0 restoring today; web/src/foliage.js only; 0 GPU, 0 MB, no bake, no master rebuild, no export, no frozen MAT_ change (option E rejected: the reference
IS the Cycles render of those materials, so a re-tint moves target and measurement together). Predicted leaf/ref 1.32 / 1.89 / 0.64 / 0.75 / 0.96 / 1.92 / 0.71 / 1.60
(today 0.86 / 0.82 / 0.64 / 0.85 / 0.31 / 1.13 / 0.54 / 1.76); constraints held: level (QA 17's closed item) and the hard-edge share (the crude simulation triples it; the
per-fragment N·L must be measured). Riders accepted: the env_shrubs walk-in bug is fixed first (viewer fix round, in flight); 8a closes on the tiles at 1/3/5 with the
leaf-green share reported, not gated (1 % of red moves it 2-9 % relative). Sequenced after the viewer fix round (same Chrome, same file).

## 2026-09-19 · 8d decision: R1 (low-frequency backdrop materials) + R2 (a tree belt on the hall's east face, ≤ 6 986 tris) go; R3 (tiled facade atlas, new UV0) deferred
The analysis (docs/briefs/phase8d_analysis.md, phase8d-env 7553f31): the backdrop is 1.1-4.7 % of the hero frame (the N-colonnade hall wall 21 204 px, of which the 102
glazed bays are 8 120 px = QA's "dark rectangles") and 35-40 % of cam06; backdrop_forest is visible at cam06 only. Root cause measured: the Gate 2 backdrop bake gives
0.79 texels/m on backdrop_building while the hall wall is 146-154 m away = 7 px/m on screen, so every texel spans 9 px and any detail averages to a flat field; a 2048
bake buys 1.58 texels/m and cannot fix it. Ref 169 at 100 % shows no lit wall behind the north colonnade at all: a dark tree belt and deep shade in every intercolumniation.
Pin window (binding): the backdrop groups sit inside env_so_far, so a backdrop delta of -5 900 … +6 986 tris keeps near 20 / far 127 byte-identical at CLASS_BUDGET
902 000. Decision: R1 — MAT_backdrop_building/_skylight/_roof/_forest/_lawn carry only low-frequency signal (bakeable distance haze toward the sky, per-building albedo
spread, a shaded desaturated hall face with the glazed-bay contrast dropped; targets cam06 top-row luma 0.435 -> ~0.80, sat 0.387 -> ~0.10, hero wall sat 0.654 -> ~0.43);
R2 — a tree belt on the hall's east face capped at 6 986 tris (~120 crowns) so the pin holds; R3 deferred; rejected: viewer-side fog (Cycles would not see it), Sapling
LOD2 backdrop trees (+1 M tris), band-atlas billboards for the backdrop (three-team lockstep, forces the budget constant). These change frozen MAT_backdrop_* materials in
assets/materials.blend and assets/environment.blend: covered by the user's Phase 8 approval of item 8d ("backdrop city blocks and trees"), reported to the user before the
build starts. Export scope: Gate 1 re-run to prove the pin, Gate 2 re-bake of the changed backdrop groups only, manifests, tiers, verify; no Gate 3. GPU ≤ 25 min previews
+ 8-15 min bake. The build starts when Blender is free (after the viewer fix round releases Chrome).

## 2026-09-19 · 8e decision: the mobile leaf blades are a mip artefact — export-only UV scale k = 2.0 (willow 1.5) on the far-tree leaf cards; no material touched
The analysis (docs/briefs/phase8e_analysis.md, phase8e-export ff852f8; probe export/p8e_leaf_probe.py): at the mobile orbit (86.9 px/m at 40 m) a far-tree card is one
quad carrying a centred strip of the 1024 px cluster texture; the painted leaves are 4-10 px and plausible, but at 20-30 texels/px the mip merges them and alphaMode MASK
re-hardens them into blades of p90 17-22 px / max 22-28 px — QA 19's "~40 px duotone blades", reproduced from texture and geometry alone (plausible clump 9-13 px).
The scale is Sapling's leaf scale x trees_far.thin_and_grow CARD_SCALE_MAX 1.6 x placement scale; scripts/env_trees.py _lod2_cards is not the source (trees_far.py
rebuilds from _LOD1). Decision: a UV scale k about each card's own UV centre on leaf faces only, in export/trees_far.py between thin_and_grow and join, gated to the
'far' set, with a deterministic per-card offset; alpha coverage is invariant (0.45-0.61 at every k), no vertex moves (vertex_ao.npz and the instance rows hold);
k = 2.0 for broadleaf, cypress, cypress_column, eucalyptus, pine, redwood, 1.5 for willow (lands p90 <= 11 px / max <= 14 px; 2.5 is the next step). Dependencies: the eight
leaf samplers in env_trees.gltf go CLAMP_TO_EDGE -> REPEAT by a JSON patch on the written gltf (no MAT_leaf_* or albedo texture touched); the viewer's runtime translucency
map follows the albedo sampler's wrap mode instead of a hard-coded ClampToEdge (one line, given to the viewer fix round as item (d)). env_trees.glb is tier 2 / glb_lazy
and only the mobile tier draws it (desktop draws env_trees_lod1.glb); tier 0 must stay byte-identical. Part 1 runs when Blender is free.

## 2026-09-19 · Viewer fix round (phase8b-viewer a610c6b): the cam02 blue-violet shade is the Phase 5 lighting, not a viewer fault — deferred to the user
Item (a): the env_shrubs LOD1 walk-in set never had a CPU distance cull (only the shader switch, since 6c r2), so it drew 2.02 M tris per frame at every station including the
aerial; a chunk cull with budget 48 (`?shrubcull=0` restores) removes 1.41 M at the hero and 2.02 M at cam06 with pixel parity (0-7 px differ at 1-5; 122 at cam06 vs a
134-px A-vs-A control). Item (b): resident() reached textures through eight material slots only and billed chunked geometry per object; rewritten by type with render targets
excluded — figure of record at the hero 1 814.2 MB (was 1 862.9: geometry 261.5 -> 114.5, textures 1 157.6 -> 1 255.6, of which the impostor atlases 67.1 were never
counted), mobile 547.9 MB (28 % of it the 67.1 MB sky equirect — a 6b lever, noted). Item (c): measured in Lab at the QA-17 shaded-stone boxes, the Phase 5 Cycles
reference is MORE blue-violet than the viewer (b* shade_pier -5.01 vs the viewer's -2.73; the photo +10.89); the probe, sky equirect and LUT are exonerated by flag sweeps;
the source is the direct NNE sky fill in the Phase 5 lighting (QA-08-2 / QA-09-6, never closed). The viewer is at parity; a fix is upstream (sky fill + rotunda lightmap
re-bake), a Phase 5 look change with a full lightmap chain. Lead's recommendation: NOT in Phase 8 — the closing comparison is viewer-vs-Cycles and Cycles-vs-photo, and this
moves both; the user decides whether it becomes a later item. Item (d): the translucency map copies the albedo's glTF sampler wrap (eager and lazy roots) for 8e.

## 2026-09-19 · 8e built (phase8e-export eed90be): vertical-only UV scale kv = 2.5 (willow 1.5), ku = 1.0 — the isotropic k = 2 would have thinned every far crown by a third
Measured per species at 40 m: an isotropic k = 2 keeps only 0.62-0.76x of the crown's alpha coverage because the card's u window is the cluster texture's dense core and
widening it pulls in the faded rim; ku = 1 / kv = 2.5 keeps coverage at 0.96-1.00x for the same blade size (p90 11-14 px, max 14-20 px, against 17-22 / 22-28 shipped;
kv = 3.0 is the next step, a u factor is not). Accepted as the decision in place of the analysis' k = 2.0. Route: env_trees.glb's leaf samplers patched to REPEAT, materials
not renamed (renaming loses the tinted albedo in applyFoliageTextures and duplicates ~8-10 MB on mobile); the tier-0 env_t0 glbs carry the same materials and stay at
clamp, which is a no-op because every leaf UV there is inside 0-1 (decoded). Block 3 699 324 -> 3 856 412 B (+4.2 %, the UV stream); tier 0 byte-identical; instance rows,
walk-up order and vertex AO unchanged. One viewer dependency (albedo needsUpdate beside the wrap copy) given to the phase8a-viewer engineer.

## 2026-09-19 · 8e decision 2: isotropic k = 2 with per-material alpha cutoffs solved for coverage (`iso_cut`) replaces the vertical-only kv 2.5
The review (docs/reviews/phase8_export_r2_review.md) showed kv-only shrinks blade thickness, not width, and QA 19's complaint was width. Measured at 40 m (probe committed,
911af2d): kv 2.5 leaves run width p90 at 36.2 / 26.7 / 23.9 / 30.9 / 22.5 / 21.1 / 12.6 px (unchanged from k = 1); isotropic k = 2 halves it but drops coverage to
0.62-0.76x; isotropic k = 2 with the leaf materials' alphaCutoff solved per material (broadleaf 0.50 -> 0.27, cypress 0.45 -> 0.21, eucalyptus 0.50 -> 0.10, pine 0.42 ->
0.12) gives width 18.4 / 23.9 / 21.1 / 25.3 / 22.5 / 19.7 / 12.6 px at coverage 0.93-1.07x, and 0.82-1.03x at the 2.5 m mobile walk-up (no fattening close up). A blade's
width at 40 m is its card's width for every species but the broadleaf, whose 40 px card is the crown in the user's orbit frames (35.7 -> 18.4 px). Adopted: `iso_cut` as
UV_TILE_MODE default (`kv25` and `off` kept for the A/B). Re-export ≈ 1 min of Blender, no GPU, in the next Blender window; the shipped env_trees.glb is kv 2.5 until then.

## 2026-09-19 · 8a relight built (phase8a-viewer fffb153): adopted as default; the remaining shrub defect is the cards' magnified leaf texture — routed to the export (8a-3)
Option B shipped as `?cardsun=0.6,0.8,0.35,0.9,0.38,1,3,1` (sun share with |N·L| — the one-sided cosine made the level view-dependent, backlit station 2 fell to 0.85x —
times a clump/self-shadow term, sky share, redistributed around the scene mean so g = 1 returns the baked value; `?cardsun=0` byte-identical to today). Eight boxes: level
held (0.972-1.012 vs a 3 % budget), hard-edge within ±0.2 points and no box newly across the reference, leaf/ref unchanged within 0.02x (reported, not gated), hue toward
the reference at station 2 only. Perf inside the noise (three paired 1440p runs). Lead viewed the tiles: at the hero the relit and today's frames are hard to tell apart;
at 3 and 5 the cards read lit-and-shaded but the dominant defect is the shrub cards' leaf texture magnified to 20-40 px "leaves" with black gaps where Cycles has a dense
small-leaved bush — the far-tree mip defect on a different asset. Decision: merge the relight (small, safe, no cost); the shrub closure moves to an export-side per-card UV
scale with solved cutoffs (8a-3; analysis by the 8e engineer, then decide, tier-0 impact reported). Carries r3-3/4/5/6 and r2-5b/6 closed on the branch. New caveat: the
planar water reflector is not session-reproducible (34 % of cam01 pixels below the waterline differ between captures of the same build) — viewer-vs-viewer pixel claims at
water stations need an A/A mask (web/README.md).

## 2026-09-19 · 8a-3 decision: shrub-card UV scale k = 2 (reeds 1.0) on the LOD2 set, riding the 8d export chain — tier 0 moves by ~4 kB
The analysis (docs/briefs/phase8a3_shrub_cards_analysis.md, phase8e-export 24eb45e): the magnified shrub "leaves" are env.glb's LOD2 cards (tier 0, env_t0.glb), not the
LOD1 walk-in set; the LOD2 card is exactly 2x the LOD1 card on the same texture, blobs 21.7-23.8 px wide at the 25 m LOD switch and 15.4 px at 54 m while the painted leaves
are 0.6-2.3 px and gone to the mip. The cards sample the whole texture, so an isotropic k only repeats it: coverage neutral (0.95-1.09x), no cutoff solve. k = 2 halves the
blob (23.8 -> 16.4 px at 25 m, 15.4 -> 7.0 at 54 m) and makes the 25 m LOD switch invisible (LOD2 tile 0.215-0.255 m vs the LOD1 card 0.21-0.26 m); k = 3-4 aliases at
54 m+; reeds stay at 1.0 (k > 1 erodes the 1-5 px blades to nothing). Samplers REPEAT in env.gltf and env_shrubs.gltf together (no shared-texture wrap race, no viewer
change). Cost: rides the ENV chain (export_set -> gate1 -> pack -> manifests -> tiers) with 8d; ~4 kB over the ENV set against 606 224 B first-frame headroom. Accepted.
8e exported: iso_cut env_trees.glb 3 768 500 B (+1.9 % over pre-8e), tier 0 untouched, verify PASS, synced to MAIN.

## 2026-09-19 · Relight review r4 (47a3aec): DO NOT MERGE until the build blocker is fixed; the hard-edge constraint's reframing accepted in writing
The branch did not parse (backticks inside the GLSL template literal in impostors.js from the r2-6 carry), so four commits' "npm test green" claims after it were false —
the fix is three lines; from now on every builder pastes the suite count into the commit message. Finding 7: the relight brief said the hard-edge share "must not rise above
the reference at any box"; seven of eight boxes were already above it before the relight (a standing QA-16 item), so the engineer measured "no box newly crosses, 05 shore
stays below" (largest move +0.20 points). Accepted: the constraint is "no new crossing and no box moves more than 0.3 points", logged here so QA 22 scores it that way.

## 2026-09-19 · 8e merged (7b59637 export, review r3 7e17b26): correction — the shipped `iso_cut` is ku 2.0 / kv 3.0 (anisotropic), not isotropic k = 2
The r3 review measured the shipped mode at 43.5 vs 65.4 texels/px; the "8e decision 2" entry's "isotropic k = 2" is amended to ku 2.0 / kv 3.0 with the per-material
cutoffs 0.27 / 0.21 / 0.10 / 0.12; the width/coverage numbers stand (re-measured by the reviewer exactly). Fixes carried into the 8d export chain (no shipped bytes): the
probe's defaults print the shipped mode; an unknown species must export at k = 1 (untiled) rather than the global ku 2 without a solved cutoff; `off` becomes a true
baseline (no v offset, no REPEAT). 8a-3 corrections from the same review, binding on the chain: the instance rows are re-dumped (instance_rows.mjs x2, gate4_instance_order
x2, gate5_instance_rows) or manifest_v4's glb_bytes asserts abort; MAT_shrub_dry's LOD2/LOD1 ratio is 0.89x wide / 1.77x tall, so it takes ku 1 / kv 2 (shrub / shrub_light
keep k = 2, reeds 1.0); coverage neutrality is measured per material, not claimed by construction.

## 2026-09-19 · 8d export chain DONE (phase8d-export 1aa1abc): pin held 21/21; backdrop re-baked in 53 s GPU; tier 0 +312 B; shrub UV scale coverage 0.98-1.08x
Pin: uv1 groups/tiles/coverage, uv2 meshes, lightmap slots identical to MAIN; near 20 / far 127 identical in content and order; ENV placed 894 974 -> 901 874 (+6 900 exactly);
arch/orn/ground glbs byte-identical after the pack. Gate 2: 7 backdrop jobs, zero clipped albedo/roughness, stale ENVBD__lawn purged. Tier 0 48 269 972 -> 48 270 284 B
(+312, env_t0 only); first frame 49 394 896 B (605 104 under the rule); mobile 47 630 546. Shrub tiling at the shipped factors: MAT_shrub 1.08x / shrub_light 1.07x /
shrub_dry (ku 1 kv 2) 0.98x / reeds 1.00x coverage at the 25 m switch, blobs 21.7 -> 16.9 px. Three chain traps fixed (GATE1_BLEND_DIR default, the npz path, the --gate2
tex_ktx2 wipe). Lead decision on the reflection: the renamed far-ground group (slot-0 material MAT_backdrop_lawn) matched water.js' backdrop exclusion and would have left
the reflection, putting a sky strip at the reflected horizon — fixed on main (1efdf56) with `backdrop_(?!lawn)` so the reflection set is exactly the pre-8d set.

## 2026-09-19 · QA 22 (234977b) on deploy 10: 8e CLOSED, fix round VERIFIED, 8a closed at 1/5 but not at cam03, 8d NOT CLOSED (blocker: the belt) — hero 3.89 -> 3.81
8d: at 100 % the R2 belt (89 icosphere crowns at subdivision 1, 6 900 tris) is a row of hard-edged untextured faceted shards in every intercolumniation at the hero, cam02 and
cam05, reflected in the lagoon — it replaced a flat wall with flat spikes (lead viewed the sheet: agreed). R1 moved the right way but reached ~15 % of the cam06 saturation
target. Decision (belt r2): the belt is rebuilt from the real tree prototypes through the far-tree path in scripts/env_trees.py (the "back screen rows" mechanism: Sapling
species meshes — LOD2 for Cycles at 150 m, band-atlas impostors of the same prototypes in the viewer), placed along the hall's east face where ref 169 shows the dark belt;
the icosphere belt objects are removed. The export pin will move on purpose: far billboards 127 -> 127 + N and the instance rows re-dump; no atlas re-bake because the
prototypes are already baked (the prototype_map must resolve every new tree); CLASS_BUDGET['ENV'] moves by exactly the placed delta the export measures. The 4K hero render
started on the faceted belt was killed (obsolete). 8a: closed on the tiles at stations 1 and 5 (lit-and-shaded small-leaved bushes; the 25 m LOD switch invisible); at
cam03 the LOD1 walk-in set (env_shrubs.glb, tier 2) still shows magnified leaves — 8a-4: the export measures the LOD1 cards at 3 m and applies the same UV-scale
treatment if warranted (tier 2 only). 8e closed (blade run p90 29.5 -> 22.7 px, 5/6 boxes <= 25, coverage 1.02-1.23x); the 2.5 m walk-up frame is captured with gate11.
Parity: 8d moves the viewer away from the frozen Phase 5 Cycles references at the backdrop boxes by design. Decision: the six Cycles station references are re-rendered
from the Phase 8 master (1080p, 32 spp fixed, delivery look — the haze-check script's settings) after the belt fix, and QA 23 measures parity against those; the Phase 5
references remain the record of the frozen look for the architecture boxes (which did not move: MAE rises only where the backdrop is). cam05 crown crossings 11.67 -> 10.80
is the belt's brighter backing, same root cause. Scores 3.81 / 3.14 / 2.75 / 2.88 / 3.12 / 3.03; mobile 3.2 / 3.22 / 2.44 / 2.7 / 2.88 / 2.58.

## 2026-09-19 · 8a-4 decision: no export change for cam03 — 8a CLOSED WITH A RESIDUAL (the cam03 bush interior is a lighting carry, not a card-scale defect)
The analysis (docs/briefs/phase8a4_lod1_shrubs_analysis.md, 16882b0): at cam03 the nearest LOD1 row in frame is 17.3 m, cards 5-13 px wide, a painted leaf 0.4-0.9 px —
sub-pixel, nothing to de-magnify; grain median 2.0 / p90 4.0 px in both the viewer and Cycles. What differs is light: bush body luma 0.142 vs Cycles 0.058 (2.4x), dark
share 0.062 vs 0.248 (no dark core), a gold cast g-r -0.030 vs +0.003; the column shade at the same station is 2.55x, the far shore 1.78x — the bush carries cam03's own
missing deep shade (carried since Phase 6, QA-21 residual) plus ~1.3x of its own. A UV scale would halve a blob that already matches the reference and break the LOD-switch
match that is in frame at cam03. Decision: 8a closes on the tiles at 1 and 5 with the cam03 interior darkness logged as a lighting residual (owner VIEWER/LIGHTING, with
the cam03 deep-shade carry); the 3 m walk-in option (k = 2 on shrub / shrub_light, +16 kB tier 2) is recorded, not taken — no station shows it.

## 2026-09-19 · Belt export chain r2 merged (66aace8; reviews r5 af110d5 and r6 7b8a111): the far-tree irradiance re-bake is accepted as a correction, verified by QA 23
r5 caught a deploy blocker: manifest_v4 had run before the far glbs were re-written (127 placements against 166 instances; the viewer would have dropped the whole
far-tree mesh layer on join failure) and the per-tree irradiance was keyed by the TREEFAR index the interleave had shifted. Fixed: the join is by world location (0.02 m
cells, unique, residual 0), the 39 belt rows were BAKED (4 jobs, 13 min GPU; not stood in), manifest_v4 asserts placements == tree_far + billboard identity + glb newer than
its report, verify_glb --gate5 check 5 compares all four counts, no hard-coded 127 remains. r6 finding: the re-bake also moved the 127 existing rows — full-mode modulation
median 0.942 -> 1.390 (+48 %; 116 of 127 bake bodies changed verts and now match the exported LOD2/AO topology exactly where the 6c bodies did not; E_bake bit-identical).
Lead decision: accepted as a correction of the 6c mismatch, NOT re-baked; QA 23 measures the far trees at 1/2/5 against the Phase 8 Cycles references (level, crossings, the
belt trees at cam02/cam05 which ship at median 0.24 modulation) and any brightness regression is a blocker with the fix being a re-key to the 6c bodies. First frame
49 273 775 B (726 225 under the rule); tier 0 48 139 115. Carries: env_trees_lod1 mtime guard, stale 127/254/46 statements inside the delivered manifests, the grid-key
half-cell brittleness, a test pinning the far count to export_set.json.

## 2026-09-19 · QA 23 (8d775ae) on deploy 11: 8d CLOSED — all five Phase 8 art items closed on the tiles; one blocker left, the far-tree irradiance re-key
8d: at 100 % the shards are gone at 1/2/3/5 and in the reflection — real crowns with sky gaps and trunks under the roofline; parity vs the Phase 8 Cycles refs improves at
every band (hero N MAE 11.24 -> 9.62 %) and the QA-22 residual reverses (band sd 0.153 -> 0.165, hf 0.1306 -> 0.1440, toward ref 169). Scores 3.97 / 3.22 / 2.83 / 2.88 /
3.20 / 3.03 (hero +0.16 vs QA 22, +0.08 vs QA 21: the best hero score of the project); mobile 3.32 / 3.30 / 2.52 / 2.70 / 2.96 / 2.58. 8a closed with the cam03 lighting
residual (leaf share 0.92x, reported); 8e closed (2.5 m walk-up delivered, no fattening); fix round verified. Blocker, by the rule set at the chain r2 merge: the far-tree
irradiance re-bake brightened every crown read against a background by +4-16 % (7/10 boxes away from the Cycles refs; dark cores lost; the 8e blade p90 22.7 -> 25.2 px
purely photometric). Fix: the 127 existing rows return to their 6c values, the 39 belt rows keep the r2 bake (export, CPU if the rows are recoverable), then deploy 12 and a
verification capture at 1/2/5 + orbit. New non-blocking residuals: the belt covers less pale backdrop than Cycles (ENV); cam03 draws the 39 belt trees as LOD2 meshes
(+1.3 M tris, +28 draws, 35.1 -> 38.6 ms — the belt is within the mesh distance from that station; EXPORT/VIEWER); cam06's R1 colour under-delivery stands (record).
cam05 crossings 10.80 -> 9.37 decomposed to the belt backing (background share 75.6 -> 79.6 % at flat level), not a crown change. Payload 46 761 417 B desktop / 46 824 683
mobile; perf 28.2 / 32.6 / 38.6 / 26.2 / 29.7 / 32.3 ms; resident 1 814.2 / 550.3 MB. Parity caveat: the Phase 8 Cycles refs survive at 960 px only (PNGs gitignored).

## 2026-09-19 · Phase 8 4K Cycles hero rendered (renders/final/hero_cam01_3840x2160_128spp.png, 128 spp fixed, 1 468 s) — lead's six-tile pass: no defect
Rendered from master_delivery.blend rebuilt 21:58 (belt r2, R1 materials, 8a/8b/8c/8e are viewer/export items and do not appear in Cycles). Wall time 1 468 s vs the Phase 5
probe's time on the same settings (the belt's +1.5 M LOD0 tris). Tile pass at 100 % (3 x 2 of 3840x2160): r1c1/r1c3 sky and entablature clean (a gull in r1c3); r1c2 rotunda,
relief panels, capitals and both vault openings open to the far side; r2c1 the north colonnade with the tree belt reading as dark crowns and trunks between the columns,
the hall roof pale above; r2c2 the shore band and the reflection breaking into streaks; r2c3 the south colonnade with crowns behind. No filled opening, plain cylinder,
seam, z-fighting or shard. The Phase 5 v2 renders are preserved in renders/final/phase5_v2/ for the comparison sheet (scripts/phase8_sheet.py, after = gate12).

## 2026-09-19 · QA 24 (b683412): the far-tree re-key VERIFIED — PHASE 8 CLOSED (all five art items, no open blocker); hero 4.01
127 existing crowns back within 3 % of gate10 at 9/10 boxes (the mover goes toward Cycles), mean deviation from the Cycles refs 6.3 % (was 6.7 pre-re-bake, 9.7 after),
dark cores back; the 39 belt rows keep the r2 bake and read as sky-gapped crowns, not cut-outs; 8e blade p90 back to 22.7 px (5/6 <= 25); regression MAE <= 0.44 %
everywhere, station 4 bit-identical; crossings cam02 7.33 (Cycles 7.76), cam05 12.28. Scores 4.01 / 3.30 / 2.83 / 2.88 / 3.28 / 3.07; mobile 3.40 / 3.38 / 2.52 / 2.70 / 3.04 /
2.62. Phase 8 closes here per the user's approval ("finish those as well and show me the difference"): the difference is docs/delivery.md "Phase 8" and
renders/qa_comparisons/phase8_before_after_960.jpg. Anything further (the carried residuals) is a new phase for the user to open.

## 2026-09-20 · PHASE 9 APPROVED by the user ("I would like everything to get finished eventually"): all carried residuals, in hero-impact order
Scope and order in docs/briefs/phase9_next_session.md: one lighting round for station 3's deep shade and station 2's blue-violet shade (a Phase 5 lighting change — this
entry records the user's approval; the lead reports before it starts), the aerial city blocks (8d R3), the belt/far-tree small items, housekeeping, then a new 4K hero and
sheet. Multi-session accepted; stop on a usage limit.

## 2026-09-20 · Phase 9 session 9 start: the lighting round is station 2 only in Cycles; station 3 is a chain gap, decomposed before anyone builds
Reading the carries before writing the briefs: cam02's blue-violet shade is a Cycles-vs-photo defect (Cycles b* -5.0 / -18.4 / -3.3 vs the photo +10.9 / +11.0 /
+5.3, phase8b_viewer_fix_report item c) and is the LIGHTING change the user approved (docs/briefs/phase9_light.md: acceptance b* >= +5 / h_ab 40-80 / R-B >= +10,
shade_frieze +11.4 +- 1.5, hero and stations 3/4 held within 3 % luma / 2 deg hue of the BEFORE frames plus the 32-spp noise floor). cam03's missing deep shade is
the opposite kind: Cycles HAS the shade (p10 7.3) and the viewer does not (p10 38-40, column shade 2.55x; QA-14-2, phase8a4 §2) — a bake/viewer chain gap that no
round has decomposed by term. So the plan's item 1 splits: the lighting agent changes Cycles for station 2 and HOLDS station 3; the bake engineer (CPU, docs/briefs/
phase9_bake_analysis.md) prices the lightmap chain the lighting change forces and decomposes cam03's excess per term (lightmap texels vs Cycles diffuse, probe/sky
term, specular sun, post) before any re-bake is scheduled, so the one re-bake of the phase carries both fixes if the cam03 fix is bake-side. BEFORE frames = the
six full-size Cycles refs the lead renders now from the Phase 8 master_delivery (housekeeping item 4, same renders). Viewer (dotted rim) and export (belt
billboard rule) start on CPU in parallel; the ENV aerial-blocks round waits for the bake analysis so the builder cap (4) and the one-GPU rule hold.

## 2026-09-20 · Phase 9 session 10: station 3's viewer shade excess is fixed viewer-side, by specular gating on the lightmap's own sky and sun visibility (zero GPU)
The bake analysis (docs/briefs/phase9_bake_analysis_report.md Part B, phase9-bake fbdbed9) decomposed cam03's 2.55x column shade by term on files already on
disk: the lightmap texels match Cycles diffuse at 0.997x (term 1, not the term), the post chain is ~0 on the near column (term 4), and the whole excess is the
viewer's specular path — the environment PMREM specular applied unoccluded (all of the viewer's blue) plus the sun DirectionalLight's specular applied
unshadowed (the warm remainder). Three options priced: (a) viewer-side — scale the IBL specular by skyVis = lightmap.b / open-sky irradiance/π and the sun
specular by sunVis = (lightmap.r − 0.1951·lightmap.b) / sun irradiance/π, both already carried by the lightmap because LIGHT_sun has zero blue; predicted
near_column 1.93x -> ~1.05x, sunlit boxes move <= 4 %, cost 0 GPU and ~20 min CPU (manifest constants + tiers + verify + build + deploy); (b) bake-side — a real
specular-occlusion / sun-visibility map pair: 6 h 10 m GPU (Part A rows 1-3) plus a second texture set the 1 200 MB line cannot carry; (c) open
assets/lighting.blend at station 3 — rejected, Cycles' cam03 shade is the reference (p10 7.3) and is held by the lighting acceptance. **Adopted: (a).**
The two constants are computed by export/manifest_v4.py from the shipped sky_diffuse EXR (upper-hemisphere cosine-weighted mean) and the sun's energy at
manifest time, never hard-coded in the viewer, so the lighting re-bake's new sky_diffuse feeds them automatically. Brief: docs/briefs/phase9_viewer_shade.md.
Validation: the four cam03 flag captures (B.5) before the gating build, then the gated build at all six stations, hero parity first; QA reads the tiles.

## 2026-09-20 · Phase 9 item 1: the belt's billboard-only rule is per SET, measured against the QA stations — the export pin gains four numbers, the export set moves none
QA 23 residual 3 / QA 24 item 3: cam03 submits **+1 301 870 triangles and +28 draws** because three of the 39 hall-east belt trees (8d r2, tag HB) stand inside
`buildDistanceCull`'s limit and a batch is submitted whole as soon as one row is inside. Measured at the cam03 station (81.0, 12.04, 1.7 / 18 mm / 16:9), of the
three inside 15 m **two are in frame**: `ENV_tree_cypress_33` at 6.5 m fills ndc x [-2.27, 0.10] and the whole frame height, `ENV_tree_cypress_34` at 10.4 m fills
x [-1.74, -0.38]; `ENV_tree_redwood_26` at 6.6 m clears the near plane by one corner only, which projects to ndc x -27.8, so it is out of frame. At 1920 px that is
one 1 K impostor texel (81 inner px per frame) at **17.7 and 11.8 screen px** — the magnified-card defect Phase 7 built the walk-up set to cure. The table is
computed, not recorded: `python3 export/belt_rule.py --frustum` re-derives it from the manifest's own station, lens and crown sizes and FAILs if any in-frame belt
row is ever billboard-only. So option (a), billboard-only for all 39, is **rejected**; option (b) as written —
"outside every station's walkable reach" — is **empty**, because all 39 belt trees stand 0.2-7.3 m from a walkable surface (`walk_dist_m`), so that phrase cannot
discriminate. **Chosen: (b) re-cut against the stations, per set.** A tagged row keeps its mesh only if its trunk base is within that SET's own viewer draw
distance + the 5 m fade band of a QA station eye — beyond it the fragment dissolve discards every fragment, so no station can ever see the mesh. Walk-up (desktop,
15 + 5 = 20 m): 4 rows kept, 35 billboard-only, **4 937 933 -> 3 890 782 placed tris (-1 047 151, -21.2 %)**, rows 166 -> 131. Far (mobile, 45 + 5 = 50 m): 22
kept, 17 billboard-only, **1 317 097 -> 1 182 338 (-134 759, -10.2 %)**, rows 166 -> 149. The two sets therefore hold different rows for the first time, walk-up a
subset of far; `foliageLazy` already reads an explicit `walkup_mesh.placements` array, so that needs no viewer change. Option (c), a per-row mesh distance, is
**not taken**: `pfaSwitchDist` is a shared uniform and a per-row distance would need a per-instance attribute in the dissolve as well as in the cull.
**What the pin says.** The EXPORT SET does not move: `tree_rule` stays 186 trees / 166 far billboards / 85 LOD2 blobs / 20 near, ENV placed stays 895 052, and
arch/orn/ground stay byte-identical — a billboard-only row keeps its billboard, its impostor frame and its per-placement irradiance, and loses only its instance
row in the two far-tree MESH glbs. `p8d_pin.py` therefore gains four pins downstream of the export set (`trees_far[far|walkup].placements` 149 / 131,
`billboard_only` 17 / 35, `placed_tris` 1 182 338 / 3 890 782, and the subset relation), so a moved station, a changed belt or a changed `draw_within_m` is a
decision rather than a surprise. **No viewer change is required, and the deploy is not gated on one** (corrected 2026-09-20, export r1 review finding 2; the first version of this
entry said the opposite). `iIrr` is written at BUILD time: `main.js` runs `farTreeIrradiance` over ALL `manifest.treesFar`, joined to `trees.far_mesh.lighting`
BY LOCATION (never by mesh placement), and `buildImpostors` writes it per instance — so a billboard-only row keeps its E_placement / E_bake modulation as long as
that lighting list keeps its row, which `manifest_v4` guarantees (one row per `tree_far` tree, `mesh: false` on the excluded ones, named in
`trees.<set>.billboard_only`) and `verify_glb` / `p9_rule_selftest` both fail on. `foliageLazy` builds its impostor complement from the MESH placements, so such a
row is correctly never flipped to `iNear = 1` and `activateImpostorMeshes` merely never re-writes a value it already has. What moves is REPORTING: that function's
`re-lit` counter reads the loaded set's mesh row count (131 desktop / 149 mobile) instead of 166, while main.js's own modulation line must still read 166 of 166 —
a capture below 166 there is a real defect. `web/test/foliage_lazy_test.mjs` section 4c holds the contract; its `info` line describes the harness, which builds
impostors without `irr`, not the viewer.

## 2026-09-21 · Phase 9: the round-19 lighting ships with a structural residual (user's decision), and the cam03 specular gate gets a second round
Lighting r19 (phase9-light, merged fed0138) moved the world's diffuse tint from (1.0, 0.65, 70.0) to (1.0, 0.75, 8.0) and the anti-sun weight from 1.0 to 0,
diffuse sockets only. Station 2's shafts meet all three targets (b* +11.3 / +5.3 / +8.8, h_ab 62-80, R-B +10..+33; mean |b* − photo| 11.9 -> 7.2); the hero
holds 12/12, cam03 7/7, cam04 6/6 at the noise floor. Two holds fail: shade_frieze +23.3 against its 9.9-12.9 window and the soffits' h_ab 82.6 against 80.
The agent's dose model (notes 29.4) shows the shafts cannot reach +5 while the frieze is pinned: the render's spread between cam02's shaded boxes is warm
interreflection plus the shafts' a* (2.5 against the photo's 10.2), a materials/ARCH property, so no diffuse-socket point satisfies both. Options put to the
user: ship, an intermediate point, or hold. **User: ship it.** The frieze/soffit overshoot is logged as a known structural residual (owner: materials, a later
phase); the re-bake chain starts on this point (probe first, per the bake analysis A.2). Camera/glossy branches and the LUT are untouched, so only lightmaps
re-bake. cam03 hold is 7/7 (review r1 fix 1: light_r17_measure has seven cam03 boxes).
The cam03 specular gate (phase9-viewer-shade, merged b60699c) measured on deploy-12 assets (docs/briefs/phase9_viewer_capture_report.md): near_column
1.93x -> 1.45x in R (B.6 predicted ~1.05x), blue closed, cam03 p10 37.5 -> 11.9 (Cycles 6.1); the cam03 flag frames confirm B.5 to the channel (post -0.012 R,
probe 0). But the parity budget outside shade (0.5 % MAE) is met at no station (0.67-6.59 %) and cam05 regresses (p10 64.3 -> 55.2 against Cycles 64.9): the
gate darkens the sunlit stations. Two normalisation errors, both at the sunlit end: skyVis divides the texel's blue by the open-sky irradiance of an
UPWARD-facing surface, so a vertical wall that sees its whole half-sky reads ~0.5 and a sunlit east wall ~0.14; and sunVis ≈ dotNL multiplies a directSpecular
term that already carries dotNL. **Decision: a viewer round 2 — normalise skyVis by the unoccluded sky irradiance for the surface's own normal (SH9 of the
sky_diffuse equirect, coefficients written by manifest_v4 beside the two constants) and divide sunVis by max(dotNL, ε); ?specgate=0 stays the Phase 8 path.**
Acceptance: cam03 near_column toward ~1.05x and p10 toward 6.1; stations 1, 2, 4, 5, 6 within 0.5 % MAE of their deploy-12 frames outside shade; cam05 p10
back within 3 % of Cycles. CPU build now, capture in the next Chrome window between the bake queue and the pack. The dotted rim is closed on the captures
(rim index 0.264 -> 0.041 at 5, 0.369 -> 0.079 at 2, other stations <= 0.075 % MAE).
