# Phase 9 ENV — 8d R3: the aerial city blocks get a tiled facade / roof / canopy atlas on UV0; the belt cover and the shrub hard-edge (brief from the lead,
2026-09-20). Opus 5 high. Fresh agent. Branch `phase9-env`, worktree .claude/worktrees/phase9-env (merge main first). Owns assets/environment.blend,
assets/materials.blend's MAT_backdrop_* block only (scripts/mat_build.py, the 8d precedent), scripts/env_city.py, scripts/env_backdrop.py, scripts/env_trees.py
(belt placement only), scripts/env_p9_*.py (new), docs/briefs/phase9_env_report.md, renders/previews/environment/*, renders/qa_comparisons/env_p9_*.
Read docs/briefs/process.md first. **GPU: the lead tells you when it is yours** (the lighting round holds it first). Build on CPU (the atlas image, the UV0
layout code, the environment.blend rebuild is a CPU Blender run through scripts/blender_run.sh); render previews only after the lead's go; one Blender at a time.

## Item 1 — 8d R3 (docs/briefs/phase8d_analysis.md §2-§5: the 1K backdrop atlas gives 0.79 texels/m on buildings, 0.35 on forest; R1 fixed the low-frequency
band; R3 is the high-frequency half). The hero's backdrop pixels (21 204 px at 1080p behind the north colonnade, plus cam06's whole upper frame) read as flat
pale boxes and, at cam06, as faceted blocks (docs/qa_round_22.md items 2 and the cam06 tile notes; docs/qa_round_24.md item 5 "cam06 R1 colour move").
Build: a tiled atlas (facade window/bay rhythm at Marina-district scale, roof tile / flat-roof gravel, a canopy leaf-mass tile for the ENV_backdrop_canopy_*
lobes — option (c) of the 8d analysis §4 table: keep the 57-tri lobes, fix the material; NO Sapling and NO cone crowns for the backdrop) painted or generated
procedurally into images stored under reference/textures or assets/textures (state the licence if fetched), mapped on a NEW UV0 laid per face in world metres
(facade: u along the street, v = height, so one tile = one storey / one bay; roof and canopy: planar in world XY), applied inside MAT_backdrop_building /
_roof / _roof_tile / _forest as a multiply/mix on the R1 low-frequency albedo so R1's haze, lot spread and shading survive. Texel density target >= 8 texels/m
on facades seen from the hero (say what the tile size and repeat give). Cycles must see it (the phase closes with a 4K hero). The UV1 export atlas pin
(docs/decisions.md "8a export gate") must hold: do not touch UV1, do not change ENV object names, counts or the tri budget (report the delta, expect 0).
Acceptance (Eevee previews cam01 / cam06 / cam05, 600 s each, 960 px composites against ref 169 hero crop and ref 105 for cam06): the hero backdrop band's
high-frequency energy (docs/qa_round_22.md item 2's hf / luma-sd measures, scripts/env_p8_boxes.py) moves toward the reference; cam06 top row luma toward
~0.80 and sat toward ~0.10 (ref 105 0.834 / 0.071) without losing R1's numbers; at 100 % the blocks read as buildings with storeys, not boxes.
Hand-off to EXPORT (write it in your report): the tiled UV0 texture cannot ride the baked 1K UV1 atlas; the exporter must pass the tile images through as
REPEAT-sampled textures on TEXCOORD_0 multiplied over the baked atlas (or bake at the tile's own repeat) — list the images, their sizes and the node layout so the
export engineer can wire it.

## Item 2 — the belt covers less pale backdrop than Cycles (docs/qa_round_24.md item 2: cam02 dark share 2.4 points under Cycles, cam05 crossings 3.6 under)
and the shrub hard-edge rise attributed to belt r2 (item 4: 01 shore shrub S 2.78 -> 5.95 %, 05 shrub/reed W 5.73 -> 7.12 %). Belt: docs/briefs/phase8d_belt_r2_report.md.
Measure first on the Cycles refs (MAIN renders/qa_comparisons/cycles_p8/cam02/05_1080_32spp.png) vs the viewer gate12 frames with scripts/env_p8_boxes.py /
qa_r24_probe.py; if the belt's Cycles cover is itself under the photo's, add crowns in the gaps within the 39-row prototype set (impostor-baked prototypes only,
export/README.md "Phase 8d r2"); if the hard-edge rise is a placement (shrubs re-seeded by the belt build), restore the pre-r2 shrub seeds/positions for those
two boxes. Report the numbers before/after; ENV placed-tri delta per LOD; the far-tree JSON re-dumped if rows move (the export re-pins).

## Do NOT rebuild MAIN's master, touch export/ or web/, or render before the lead's go. Commit after every successful script with the attribution line and the
test-suite count (scripts/ tests for env, if any; else "no suite"). Report < 15 lines: files, item numbers before / after / reference, composite paths,
UV0 texel density, tri delta, the export hand-off, last commit id.
