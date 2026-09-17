# 6c export brief, round 3 = the LAST 6c round (Opus high, fresh agent, 2026-09-17). Branch phase6-export (worktree .claude/worktrees/phase6-export; `git merge main` first).
Read: docs/qa_round_16.md (verdict ONE MORE ROUND; the shrub/reed boxes at stations 1/2/3/5 — level 1.34-1.70x the Cycles reference, hard-edge share 2-8x, leaf-green share
half; the 3 m walk-in "wants the LOD1 set"), docs/decisions.md from "2026-09-17 · Lead 100 % tile judgement" to the end, docs/briefs/phase6c_foliage.md, CLAUDE.md "Phase 6"
and machine rules, export/README.md "Phase 6c" sections (yours and the bake's), export/trees_far.py, export/foliage_tex.py, export/gpu_lock.sh (`run <secs> -- <cmd>` claims
MAIN's GPU lock with a trap; every GPU render of yours goes through it, because the viewer's Chrome pauses on that lock).
1. SETTLE THE SHRUB ALBEDO with numbers (first, GPU, ~10 min): render the Cycles Diffuse Colour pass (DiffCol AOV, 16 spp, 1920x1080, master_delivery.blend, the QA
   station cameras cam02 and cam05 from scripts/qa_cameras.py; `export/gpu_lock.sh run 900 -- scripts/blender_run.sh 900 -- --background master_delivery.blend --python <your script>`,
   never save the blend) and compare, in the QA shrub boxes (docs/qa_round_16.md names them; scripts/qa_r16_probe.py has the coordinates), the pass's mean albedo per material
   against the shipped tinted KTX2 albedo (sample the texture where the cards are opaque) — if they agree within 10 % the level gap is LIGHTING (viewer: irradiance reducer
   / translucency / missing self-shadow) and you say so; if the shipped albedo is brighter, fix the export (which node the tint chain misses, e.g. a multiply after the
   HueSaturation or a Mix factor) and report before/after. Write the numbers to export/out/gate3/foliage/albedo_check.json and a 960 px sheet renders/web/960/6c_albedo_check.jpg.
2. WALK-UP LOD1 for the 16 far-tree prototypes (CPU): export each prototype's `_LOD1` object decimated to <= 30 k tris (card-aware as trees_far.py, same anchor, same
   127 placements, same instance order as env_trees.glb so the viewer can reuse the placement rows and the per-placement irradiance) into a third lazily-loaded
   `env_trees_lod1.glb` (gltfpack as env_trees.glb, KTX2 as before), NO vertex AO (the viewer's interior term covers it), manifest block `trees.walkup_mesh` written by
   manifest_v4.py {glb, bytes, prototypes, placements, join}. verify_glb extended. Report bytes; the viewer draws it only within ~15 m.
Sync to MAIN with sync_main.sh when no headless Chrome is running (ONE `until` loop on `pgrep -f headless`, sleep 60 s, max 60 min). Commit after every script. Report < 15 lines:
the albedo verdict with numbers per material, the LOD1 tri counts and bytes, files, commit id, confirmation that the lock is idle and no Blender runs.
