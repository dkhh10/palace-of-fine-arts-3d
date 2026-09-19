# Phase 8d — the backdrop: textured city blocks, real backdrop trees, the exhibition-hall wall behind the N colonnade (brief from the lead, 2026-09-19).
Opus 5 high. Fresh agent. Branch `phase8d-env` from main, worktree .claude/worktrees/phase8d-env. Owns: assets/environment.blend, scripts/env_backdrop.py, scripts/env_city.py,
the MAT_backdrop_* block of scripts/mat_build.py (assets/materials.blend, ONLY those materials — no other MAT_ may change; the Phase 8 approval in docs/decisions.md
"PHASE 8 APPROVED" covers item 8d, so no further user approval is needed for MAT_backdrop_* textures, but every material change is logged in the report).
Two parts. PART 0 is CPU-only and stops for the lead; PART 1 builds in Blender after the lead's go.
Read: CLAUDE.md (Blender hygiene, blender_run.sh, the GPU rules), docs/qa_round_17.md §"cam05"/"cam06" and residual 7 in docs/qa_round_19.md/20.md (the defects: flat
saturated city planes at cam06, the flat pale backdrop band through the arches at cam05, the N-colonnade backdrop wall "a flat olive field with dark rectangles" at the
HERO r2c1 — this last one is the highest-impact target), scripts/env_backdrop.py and scripts/env_city.py headers (what exists, the OSM sources, the tri classes),
scripts/mat_build.py lines 1060-1100 and 1430-1510 and 1669-1710 (the backdrop materials), export/README.md "Phase 8a" and the ENV budget table (backdrop groups are
"flat colour, no bake", source UV; `EXPM_ENV_backdropgroup_*` rows), docs/decisions.md "8a export gate" (the UV1 pin rule: gate1 in a worktree must reproduce MAIN's
uv1 coverage/tiles/groups; arch/orn/ground glbs byte-identical; near 20 / far 127 impostor placements byte-identical — else stop), docs/briefs/phase8b_band_atlas.md
(the impostor prototypes and band atlases that already exist for far trees), reference photos ref 105, 092, 097 (cam06/aerial), ref 169 (hero), the cam05 reference.
PART 0 — analysis (< 80 lines, docs/briefs/phase8d_analysis.md), numbers not opinions:
  1. Inventory of what the six stations actually see of the backdrop (pixels per station per backdrop group from the gate9 capture's colour masks or from the export's
     per-group draw; the hero's N-colonnade wall box in px), so the work goes where the pixels are.
  2. Trees: the backdrop canopies are 40-tri blobs / faceted cones (ENV_backdrop_forest 99 640 tris). Options with placed-triangle and export cost: (a) re-use the existing
     far-tree impostor prototypes (band/2K atlases already baked) as extra billboard placements for the backdrop trees within ~450 m, (b) Sapling LOD2 meshes for the
     nearest backdrop rows + impostors beyond, (c) a textured canopy mass. For each: tris, MB, whether the impostor instance rows/order change (the pin), whether the
     Cycles side (the 4K hero re-render at the end of Phase 8) sees the change too — the user wants the Cycles before/after, so the blend must change, not only the export.
  3. City blocks: textured facades (window/floor tiling from a small atlas with per-building UV offset, roof texture, a street-level dark band) vs per-vertex colour noise;
     what the export needs (a texture on a group that is "flat colour, no bake" today, UV on the merged group) and whether it touches UV1 packing (it must not; backdrop UV1
     came from the Gate 2 bake — say whether a new UV0 for the facade tiling coexists with it).
  4. The N-colonnade backdrop wall (exhibition hall crescent, MAT_backdrop_building): what the reference shows there (pilasters, a cornice, ochre plaster, shadow under the
     eave) and the cheapest way to get it (texture + normal, a few real pilaster prisms, or both).
  5. A recommendation with the GPU minutes (ENV previews at cam 1/5/6, the export re-run), the ENV budget delta against 902 000, and the export re-run scope.
  Commit the analysis on the branch; report to the lead < 12 lines; wait.
PART 1 — build after the lead's go (the lead may prune the scope): idempotent scripts, rebuild the backdrop collection(s) only; previews with common.render_previews('env')
at cams 1, 5, 6 through scripts/blender_run.sh (600 s each) only when `pgrep -fl "MacOS/Blender|headless"` is empty and export/out/bake_queue/status.json is idle;
one Blender at a time; commit after every successful script. Do NOT rebuild master, do NOT touch export/ (the lead rebuilds master + master_delivery and queues the export).
Report: docs/briefs/phase8d_env_report.md (< 80 lines: what changed, tri counts before/after per group, materials changed, the preview composite at 960 px).
