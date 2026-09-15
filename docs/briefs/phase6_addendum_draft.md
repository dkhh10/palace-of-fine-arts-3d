# Phase 6 addendum to CLAUDE.md — DRAFT for the user's approval (lead, 2026-09-15)

Once approved this block is appended verbatim to CLAUDE.md under the heading "Phase 6 — Three.js walkthrough (added
2026-09-15)". Nothing below changes Phases 0-5; the Phase 5 look (materials, lighting, AgX High Contrast, exposure -2.833)
is frozen and inherited, known defects included (docs/delivery.md). Any change to assets/*.blend materials or lighting
needs a docs/decisions.md entry and the user's approval before work starts.

## Sources and conventions
- `master.blend` is linked and cannot be baked to. `master_delivery.blend` (`PFA_PACK=1 scripts/phase5_deliver.sh 1b`,
  packed, local objects) is the ONLY bake and export source. Regenerate it, never edit it, never save over it.
- LOD is chosen by name suffix (`_LOD0/_LOD1/_LOD2`), never by visibility. Export set: ARCH_ and ORN_ (as the placed
  `INST_*` instances of the `ORN_*` prototypes) at LOD0, ENV_ at LOD1 (LOD2 where the budget in
  docs/briefs/phase6_budget.md says so). Unsuffixed ARCH_/ENV_ objects are single-LOD and always exported.
- Units and axes as Phases 0-5 (1 BU = 1 m, origin = rotunda floor, +Y toward the lagoon, water at `common.WATER_Z`).
  glTF is Y-up: Blender's exporter does the swap (Blender +Y -> glTF -Z, Blender +Z -> glTF +Y); the viewer never
  re-rotates the scene and places the water plane at `y = WATER_Z`. Verified with the hero station, never by eye.
- Colour: the viewer reproduces `AgX - High Contrast` at exposure -2.833 EV as read from master_delivery.blend, by a
  3D LUT baked from Blender's own OCIO (export/bake_lut.py), not by three.js' built-in AgX (which has no looks).
- Hero camera `CAM_qa_01_lagoon_hero`; the six `scripts/qa_cameras.py` stations are the QA fixtures (keys 1-6).

## Layout
```
export/            Python (bpy) + shell that regenerate every web asset from master_delivery.blend, no hand steps.
  export_set.py      select by LOD name, decimate to the per-asset budget, UV2 unwrap, write the bake manifest
  bake_*.py          normal (hi->lo), PBR (albedo/rough/normal from the node trees), lightmap (Cycles diffuse, UV2)
  bake_queue.sh      detached queue over the manifest: one Blender per asset via blender_run.sh, status.json, resume
  bake_lut.py        AgX High Contrast 3D LUT + sky equirects (camera branch = background, glossy branch = PMREM)
  gltf_pack.sh       glTF -> gltfpack (meshopt) -> toktx (KTX2 UASTC desktop / ETC1S mobile)
  out/               generated (gitignored): glb, ktx2, exr, hdr, lut, manifest.json, bake_queue/status.json
web/               the viewer (Vite + three.js). `npm run build` -> web/dist (static). web/public/assets -> export/out.
  tools/screenshot.mjs   puppeteer-core headless screenshots of stations 1-6 (through scripts/chrome_run.sh)
tools/             gltfpack + toktx binaries (gitignored; `tools/install.sh` re-fetches pinned versions)
renders/web/       viewer screenshots per QA round (committed at 960 px; full-res tiles gitignored)
docs/qa_round_10+.md, docs/briefs/phase6_*.md, docs/reviews/phase6_*.md
```
Gitignored (regenerable): `export/out/`, `web/node_modules/`, `web/dist/`, `web/public/assets/`, `tools/bin|lib|dl`,
`*.glb *.ktx2 *.exr *.hdr` outside reference/, `renders/web/**/tiles/`. Committed: scripts, manifests' schemas, budgets,
web source, QA screenshots at 960 px, status files' final copies in docs.

## Machine rules (in addition to every rule above)
- Bakes are GPU renders. `export/bake_queue.sh` owns the GPU while `export/out/bake_queue/status.json` says `running`.
  No agent waits on it; idleness is read from that file, never from CPU or log silence. One Blender per asset through
  `scripts/blender_run.sh <honest seconds>`; many short jobs, never one long one (the Air throttles).
- Headless Chrome uses the GPU: never concurrent with the bake queue. Every Chrome run goes through
  `scripts/chrome_run.sh <max_seconds> -- <command>` (registers the pid with the watchdog, kills leftover headless
  Chrome on exit). Screenshots are taken by `web/tools/screenshot.mjs` (puppeteer-core on the installed Chrome, waits
  for `window.__pfaReady`), because a raw `--headless=new --screenshot` lingers 60-90 s per frame on Chrome 152.
- Hard cap 4 Blender-using agents; at most 3 builders concurrent; lighting and materials never concurrent.
- Images: downscale to 960 px before viewing, except the full-resolution tile review at QA gates.

## Casting
Lead: Fable 5.1 high; plans, assigns, merges, keeps status.md; no build code beyond 20-line fixes; one final Fable
judgement at the end of 6a. Builders on Opus 5 (`model: opus`, explicit): bake engineer xhigh, export engineer high,
viewer engineer high. Mechanical batch work (toktx/gltfpack runs, downscaling, inventories, log filtering) on Sonnet or
Haiku. QA critic Opus xhigh with the full-resolution tile review before scoring; report before changing anything. Code
reviewer (Opus, read-only, no Blender) before every merge, findings to docs/reviews/. Fresh agents every session; briefs
point at files. Branches: `phase6-bake`, `phase6-export`, `phase6-viewer`, one worktree each; the lead merges.

## Definition of done and stopping rule
- **6a (this Mac):** viewer at 1440p with the median frame time and GPU memory reported (target >= 45 fps); stations
  1-6 as presets, screenshots deterministic through headless Chrome; QA scores each station twice (viewer vs the Phase 5
  Cycles render = parity; viewer vs the reference photo = the rubric): done when every station is within 0.5 of its
  Phase 5 score and none is below 2.5; water reflects the rotunda at the hero station; walk controls with ground clamp,
  no walking into the lagoon; loading screen with progress.
- **6b (web):** initial payload <= 50 MB, progressive loading, meshopt + KTX2; Safari and Chrome on macOS; a mobile
  fallback (LOD1 geometry, halved textures) that loads and walks; staging URL with one QA round against it.
- 6a stops at parity or after two flat QA rounds following Gate 4. 6b stops at deployment plus one clean QA round.
  Polish beyond that is a new phase. Gaussian splats only if the user asks, off the critical path.
- Gates 0-5 as docs/briefs/phase6_plan.md; every gate carries the name sweep (`scripts/qa_name_sweep.py` on the export
  set) and the six-station full-resolution tile review; Gate 0 must pass before any scale-up.

## Budget
Claude Max 20x; Phase 6 target <= 40 weekly points. Burn logged in docs/status.md at the end of every session
(`python3 docs/usage/usage_from_transcripts.py`). Clean restart past 350k context; on a usage limit stop.
