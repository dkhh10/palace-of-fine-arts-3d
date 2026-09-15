# Phase 6 Gate 4 — the viewer proper (lead, 2026-09-15). Branch `phase6-viewer` (round 4, fresh agent). Opus high. Runs after the Gate 3 bake lands manifest v4.
Read first: CLAUDE.md "Phase 6" section (definition of done 6a), docs/briefs/process.md, web/README.md (carries), docs/reviews/phase6_viewer_gate2_review.md, docs/briefs/phase6_gate3_bake.md
and export/README.md manifest v4 section (lightmaps per asset + per-instance slots, vertex irradiance, impostors, probe), docs/qa_round_12.md (Gate 2 verdict, viewer-owned items),
docs/qa_round_10b.md (the hero boxes the parity round will measure), docs/briefs/phase6_plan.md §3 (lighting transfer + traps), scripts/light_flythrough.py (the Phase 5 path, for the walk bounds).
1. Lighting mode `baked`: lightMap on UV2 per asset (lightMapIntensity = manifest.lightmap_scale = pi), the 248/256 px slot atlases for ORN/ARCH instances via a per-instance UV offset
   (InstancedBufferAttribute + onBeforeCompile on the lightMap lookup), vertex-colour irradiance for terrain and near trees, sun specular-only, PMREM (glossy sky) for specular only,
   the camera-branch sky as background. Measure the material bake and the lightmap bake separately before combining (?lighting=direct vs baked on the same station, both captured).
2. Impostors: octahedral impostor material for the 127 far trees from the Gate 3 atlases (view-dependent frame pick + blend of the 3 nearest frames, alpha test, normal+depth for
   lighting), replacing the ENV_treeboard_* stand-ins and the viewer quads; near trees keep their thinned LOD1 cards.
3. Water: planar Reflector on the plane at WATER_Z with the lagoon murk tint, ripple normal map (frozen phase for captures, ?t), Fresnel; the baked hero probe as the fallback when
   the reflector is off (mobile). Acceptance: the rotunda reflects at cam01 (reflection box lum/hue vs the Phase 5 hero: docs/qa_round_10b.md).
4. Post: LUT (as now), bloom, screen-space AO, the compositor's mist as distance fog (colour/strength/falloff from manifest.compositor), vignette; each switchable (?post=...) and
   the hero boxes measured with each on/off so QA can attribute.
5. Walk controls: WASD + mouse look, eye height 1.7 m with a ground clamp by ray cast against the ground/paving/lawn meshes, collision against the water (cannot enter the lagoon:
   clamp to the shoreline polygon derived from the ground meshes' edge at WATER_Z), no walking through columns (capsule vs the ARCH bounding boxes), stations 1-6 on keys 1-6
   (deterministic: controls never move the camera before __pfaReady or before the first input), loading screen with progress (bytes/total, per class).
6. Performance: 1440p median frame time and GPU cost, resident memory (textures + render targets, PMREM once), draw calls — target 45 fps or better with everything on.
7. Capture: web/tools/gate4.sh (all six stations, baked lighting, post on, water on, placeholders gone), pair sheets vs the Phase 5 renders and the cam01 tiles; QA rounds 13+.
Report < 30 lines: per-station numbers, the on/off box table for cam01, what is left, last commit id. Chrome only through scripts/chrome_run.sh with the GPU guard; never during a bake.
