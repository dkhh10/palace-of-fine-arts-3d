# 6b export brief — load tiers + mobile manifest (Opus high, fresh agent). Branch `phase6b-export` (worktree .claude/worktrees/phase6b-export, branched from main today).
Read first: CLAUDE.md "Phase 6" (sources, machine rules, casting), docs/briefs/phase6b_plan.md (items 1 and 3; the definition of done), docs/decisions.md from
"2026-09-18 · 6b" to the end (the user's three decisions: iPhone 16 Pro, Cloudflare Pages free tier with a 25 MiB per-file cap, the tier-0 look may be low-res),
export/README.md "Gate 3 export hand-off" and "Phase 6c" sections (the chain: export_set -> gltf_pack -> bake_queue -> manifest_v4 -> sync_main), export/manifest_v4.py,
export/gltf_pack.sh (the ETC1S path, lines 48-62), docs/briefs/phase6_budget.md (per-asset table, texture plan). Reference photos and master_delivery.blend live in the MAIN
checkout; `export/out` is MAIN's (gitignored); you write new outputs under MAIN `export/out/gate5/` via export/sync_main.sh (no --delete), never into gate1-3.

## Deliverables (measured, scripted, idempotent; commit after every script that runs)
A. **Per-station visibility, per asset.** `export/gate5_visibility.py` (bpy, headless, blender_run.sh, NO GPU render): from each of the six QA stations plus the hero,
   a `scene.ray_cast` grid at the station's own resolution/aspect (>= 480x270 rays), counting the first-hit object per asset of the export set (ARCH_, INST_*, ENV_, ground,
   backdrop, water). Output `export/out/gate5/visibility.json` {asset: {station: pixel_fraction}} and per-asset "first station where visible" + hero fraction. This is the
   ordering key for the tiers. CPU only; one Blender at a time.
B. **Tiers, manifest v5 block `tiers`.** `export/tiers.py` reads manifest v4 + visibility.json + the on-disk sizes and writes `export/out/gate5/manifest.json` (schema
   pfa-phase6/5, everything v4 has plus `tiers` and `files`): tier 0 = the hero station's first frame within **50 MB total** (arch + ground glb, the LUT, the sky equirect,
   the probe, the hero-visible albedos at low resolution: ETC1S KTX2 or quarter-res UASTC, whichever is smaller at equal or better look; ORN geometry at the lowest LOD that
   fits — `orn_lo_from_lod1` — split by hero visibility; no ORN lightmaps); tier 1 = the rest of the full-look textures, lightmaps and ORN LOD0 groups in hero-visibility
   order (visibility.json); tier 2 = everything else (backdrop, far ENV, foliage 2K, walk-up set) in the order of the stations 2-6. **Every published file <= 25 MiB**
   (Cloudflare Pages' cap): split orn.glb and env.glb into per-tier groups (gltfpack per group, instancing preserved within a group; the manifest `assets` keep their identity;
   `glb.per_class` becomes `glb.groups` with tier, bytes, station visibility); any file that cannot be split under 25 MiB is listed in `tiers.oversize` with its reason. Textures
   get a per-tier variant ONLY where a tier needs one (no second full set). `tiers.py` prints and writes the byte total per tier; the loading screen reads it (viewer).
C. **Mobile manifest.** `export/out/gate5/manifest_mobile.json`: LOD1 geometry (ENV `_LOD1`; ARCH/ORN LOD1 where exported, else the decimated LOD0 at half the Gate 1
   budget — record which), textures halved (ETC1S, `--encode etc1s --clevel 2 --qlevel 128`, the gltf_pack.sh path; gate3 impostor atlas at 1K = `variant_2k` off), impostors
   for ALL trees (no near mesh, no walk-up set), shrubs LOD2 only, no ORN 2K, lightmaps at half; the same `tiers` structure with tier 0 <= 50 MB. Target on the iPhone 16 Pro:
   resident < 700 MB (report the ASTC-rule estimate per class as budget_doc does), all files <= 25 MiB. `?tier=mobile` is the viewer's switch (the viewer brief).
D. **Verification.** `export/verify_glb.py` extended to the groups (every v4 asset present exactly once across the desktop groups; instancing rows unchanged; a 6-station
   ray test unaffected — geometry is identical to gate3). `export/gate5_report.py` -> docs/briefs/phase6b_export_report.md: tier byte table (desktop, mobile), per-tier file
   count, oversize list, the ETC1S wall time and size per texture class, the mobile resident estimate, hero-visible assets not in tier 0 (must be empty or justified).
E. Sync to MAIN (`export/sync_main.sh`, gate5 only) and tell the lead in the report when tier 0 + 1 files are in MAIN (the viewer engineer captures against them).

Rules: Blender through `scripts/blender_run.sh <honest seconds>`, CPU work only (no Cycles/Eevee renders; the viewer engineer owns Chrome and the GPU); `pgrep -fl MacOS/Blender`
before every run; commit on phase6b-export after every script or 15 min; do not edit manifest v4, gate1-3 outputs, web/, or master_delivery.blend; do not hand-edit JSON.
Report < 25 lines to the lead: tier bytes, file counts, oversize list, mobile estimate, files, commit id. Code review before merge (the lead dispatches it).
