# Phase 6 Gate 1 — viewer engineer (lead, 2026-09-15). Branch `phase6-viewer` (round 2, fresh agent), worktree .claude/worktrees/phase6-viewer. Opus high.
Read first: CLAUDE.md "Phase 6" section, docs/briefs/process.md, web/README.md (your predecessor's carries 7-11), docs/reviews/phase6_viewer_gate0_review.md,
export/README.md, docs/briefs/phase6_gate1_export.md (the export engineer works in parallel; manifest v2 lands in export/README.md first).
1. Load manifest v2: several glbs, EXT_mesh_gpu_instancing (GLTFLoader -> InstancedMesh), neutral grey MeshStandardMaterial with the ORN
   normal + AO maps (KTX2), the Gate 0 LUT / sky / exposure pipeline unchanged, water plane at WATER_Z, far-tree billboards drawn as flat
   tagged quads (impostors come at Gate 3). Progressive: glbs load in the manifest's order with a loading screen showing bytes / total.
2. Carries 7-11 from the Gate 0 review: fix 9 (sky rotation from the manifest — done), 10 (stations and WATER_Z from the manifest, no
   hand copy), 11a (FloatType LUT), 11c (`npm run shot` through scripts/chrome_run.sh); leave 7 and 8 listed.
3. `web/tools/screenshot.mjs --stations 1-6` in ONE browser session at 1920x1080 (QA fixtures) -> renders/web/gate1_cam0K.png, and a
   1440p (2560x1440) performance pass at each station: median presented frame time over 120 frames, gl.finish GPU cost, draw calls,
   triangles, and the resident texture/geometry bytes from renderer.info plus your own byte sum -> renders/web/gate1_perf.json. Chrome
   only through scripts/chrome_run.sh and only when export/out/bake_queue/status.json says idle AND `pgrep -fl "MacOS/Blender"` is empty,
   checked in a separate command before each run (a materials builder and the export queue use the GPU this session).
4. Pair sheets: renders/web/gate1_pair_cam0K.png = viewer | the Phase 5 QA render of that station (renders/previews/qa/round09_0K_*.png
   Eevee 1280x720; cam01 = the round-10b Cycles hero) | 50 % blend, plus the six 100 % tiles of cam01 (3 x 2) for the QA critic.
5. Report < 25 lines: per station frame time / GPU cost / draws / tris at 1440p, bytes loaded, load time, every failure, last commit id.
