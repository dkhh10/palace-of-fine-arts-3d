# 6c export brief (Opus high, fresh agent). Branch phase6-export (worktree .claude/worktrees/phase6-export; `git merge main` first). Read docs/briefs/phase6c_foliage.md (items A, D, E),
CLAUDE.md "Phase 6" and machine rules, export/README.md (the export chain, items 1-32; the shrub/reed export and cut chain, gate 3 items 30-32), export/export_set.py,
export/gltf_pack.sh, export/manifest_v4.py, docs/briefs/phase6_budget.md (tree rows), docs/decisions.md from "2026-09-17" to the end.
A. Far-tree meshes: the 127 tree_far placements use 16 prototypes (manifest `impostors`). Export each prototype at LOD2 from master_delivery.blend (the `_LOD2` object if it exists,
   else decimate the `_LOD1` to <= 8 k tris with the export's decimate path; own UVs kept; card materials as the near trees), into `env_trees.glb` with EXT_mesh_gpu_instancing
   (127 rows, transforms identical to the impostor placements — assert against the manifest's tree_far entries), gltfpack -mi -vp 16 as env.glb, KTX2 as Gate 3. Manifest block
   `trees.far_mesh` {glb, prototypes:[{name, tris, verts}], placements, join key}. Write the LOD2 topology (verts per prototype) to export/out/gate3/trees_far/topology.json for the
   bake engineer and report in docs/status.md-style words to the lead when it is in MAIN (the bake waits on it).
D. Leaf textures at 2K: for the MAT_leaf_* materials (near trees and far prototypes), bake/export albedo+alpha at 2048 from the Phase 5 node trees (same path as the Gate 2 PBR
   bake; the cut chain per README item 30) and a translucency mask if the tree has a Translucent/Subsurface term (else record the constant); KTX2 UASTC; manifest `materials`
   entries updated with the 2K paths beside the 1K (`leaf_2k`), alphaMode MASK with the read cutoff.
E. Shrub/reed LOD1: export the `_LOD1` versions of the 28 shrub/reed card meshes into env.glb beside the LOD2 (same 1 379 placements; manifest `lightmaps.instance_irradiance`
   rows must still join — extend the join so both LODs share the placement's irradiance), name-suffixed so the viewer can pick. Albedo hue: bake the MAT_shrub_light / shrub_dry /
   shrub / reeds albedo as the export does and compare its mean hue with the Cycles cam02 reference's foliage (102.4°) and with the Phase 5 material's base colour read from the
   node tree; if the export's albedo differs from the material (colour space, tint, cut chain), fix the export and report before/after hue; if the material itself is that warm,
   report it (a materials change needs the user's approval per CLAUDE.md). verify_glb extended for env_trees.glb and the LOD1 set; sync to MAIN (no --delete); commit after every
   script; Blender through blender_run.sh (CPU decimation only; no GPU renders — the bake owns the GPU). Report < 20 lines: tri counts, bytes, placements check, hue numbers,
   files, commit id. Do NOT edit manifest.json by hand (the lead runs manifest_v4).
