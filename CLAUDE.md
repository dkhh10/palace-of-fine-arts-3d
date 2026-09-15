# Palace of Fine Arts — photoreal Blender build (3rd attempt)

## Mission
Build a stunningly beautiful, photoreal 3D model of the Palace of Fine Arts (the current 1974 concrete
reconstruction, not the 1915 original) in Blender, lit at golden hour. First deliverable: a .blend we can
open and fly around in. It must be render-ready (Cycles) and camera-ready for a later flythrough video.
Success: a render from the classic lagoon-side viewpoint at golden hour is hard to tell from a photograph.

## Environment (verified 2026-09-06 by the lead)
- Blender **5.2.1 LTS** at `/Applications/Blender.app/Contents/MacOS/Blender` (also `blender` on PATH). Python 3.13.
  The brief said 4.x; 5.2 API differences that matter are listed below.
- GPU: Apple M2, 10-core Metal. Cycles GPU works headless. Keep preview sample counts low.
- Render engines: `BLENDER_EEVEE` (this IS Eevee Next in 4.2+/5.x; there is no `BLENDER_EEVEE_NEXT` id) and `CYCLES`.
- Color management: `view_transform = 'AgX'` works. Looks are set by string, e.g. `'AgX - Punchy'`.
- Sky texture types: `MULTIPLE_SCATTERING` (physically based successor of Nishita), `SINGLE_SCATTERING`, `PREETHAM`, `HOSEK_WILKIE`.
- Cycles denoiser: set by string `scene.cycles.denoiser = 'OPENIMAGEDENOISE'`.
- `ShaderNodeTexSky` props in 5.2: `sky_type, sun_disc, sun_size, sun_intensity, sun_elevation, sun_rotation, altitude, air_density, aerosol_density, ozone_density` (no `sun_azimuth`; **`sun_rotation = azimuth - 90°`** because rotation 0 = world +Y, verified by the lighting agent; use `light_calibrate.make_sky_world`). Sun lights have `use_temperature/temperature`, `angle`, `energy`, `exposure`.
- Installed and enabled extensions (user prefs): `bl_ext.blender_org.sun_position`, `bl_ext.blender_org.sapling_tree_gen`.
  Online access is enabled in prefs; other extensions can be installed headless with
  `bpy.ops.extensions.package_install(repo_index=0, pkg_id='...')` (see scripts/common.py `ensure_extension`).
- ffmpeg 8.1 on PATH.
- Headless Eevee render of a trivial scene at 640x360 takes ~20 s (mostly shader compile); Cycles 32 spp ~12 s.

## Conventions (binding)
- Units metric, 1 BU = 1 m. **World origin = centre of the rotunda floor (z = 0 is the rotunda floor slab).**
  Lagoon water surface is at z = WATER_Z (see common.py; currently -1.3 m, confirm from reference sheet).
- **+Y points toward the lagoon (east). -X is north, +X is south.** The classic hero camera stands at +Y looking toward -Y.
  OpenStreetMap-derived site data in `reference/plans/site_local.json` uses +x = east, +y = north; convert with
  `common.osm_to_world(x_east, y_north) -> (-y_north, x_east)`.
- Sun azimuth convention: degrees clockwise from north. Use `common.sun_direction(az, el)` / `common.aim_sun(...)`.
- All scene construction is Python (bpy) run headless: `blender --background --python scripts/<name>.py [-- args]`.
  Never rely on manual clicks. Everything reproducible from scripts.
- Every script is idempotent: it clears/rebuilds its own collection(s) at the start. Use `common.rebuild_collection`.
- Each specialist owns ONE .blend under `assets/` and ONE top-level collection:
  ARCH -> assets/architecture.blend, ORN -> assets/ornament.blend, materials library -> assets/materials.blend,
  ENV -> assets/environment.blend, LIGHT (+ world) -> assets/lighting.blend. The lead assembles master.blend by linking.
  Nobody edits another agent's file. Requests go through the lead.
- Object naming: `ARCH_rotunda_dome`, `ARCH_colonnade_column_01`, `ORN_capital_corinthian_LOD1`, `ENV_tree_cypress_03`,
  `SOCKET_capital_##`, `SOCKET_maiden_##`, `LIGHT_sun`, `CAM_qa_01_lagoon_hero`. Prefix = owning collection.
- LODs: `<name>_LOD0` (hi), `_LOD1` (mid, viewport default), `_LOD2` (low). Viewport shows LOD1 by default.
- Materials come from the library by name: `common.load_material('MAT_concrete_ochre')` (appends from
  assets/materials.blend, falls back to a flat placeholder if missing). Never duplicate library materials.
- Previews: Eevee, 1280x720, from the fixed QA cameras (scripts/qa_cameras.py) into
  `renders/previews/<agent>/<timestamp>_<cam>.png` via `common.render_previews('<agent>')`. Finals: Cycles + denoise.
- Reference photos live in the MAIN checkout only (gitignored, 175 MB):
  `/Users/dk/Projects/3d render blender 3rd attempt building/reference/` (also `common.REFERENCE_DIR`).
  Worktrees do not contain them; read them via that absolute path.
- Commit often on your own branch. One agent, one branch, one worktree. The lead merges into main.

## Repository layout
```
CLAUDE.md
docs/reference_sheet.md   measurements, ornament catalog, material catalog, photo index, 6 QA viewpoints
docs/decisions.md         lead's log of choices and why
docs/quality_checklist.md living QA rubric (QA agent)
reference/photos/raw/     214 Wikimedia Commons + Flickr photos (index: reference/photos/index_wikimedia.csv)
reference/photos/user/    user-supplied reference (user_wide_midday.png = THE target composition)
reference/plans/          OSM footprints (site_local.json), satellite tiles, prior measurement overlays
reference/prior_attempt_notes/  spec + gate critique + params from attempts 1-2 (useful measurements, NOT the art target)
scripts/common.py         shared helpers   scripts/qa_cameras.py  fixed QA camera set
scripts/build_master.py   assembles master.blend from assets    scripts/<agent>_*.py  each agent's builders
assets/*.blend            one per specialist
master.blend
renders/previews/<agent>/  renders/qa_comparisons/  renders/final/  renders/prior_attempts/ (what NOT to repeat)
```

## Lessons from attempts 1 and 2 (why they failed the photoreal bar)
- Stone read as clean, bright, uniform "CAD". Real PFA concrete is a muted, variegated ochre/tan with rain streaks,
  a dark algae band at the waterline, patched repairs, soft edge wear, and dust in the ornament recesses.
- Columns were rendered saturated salmon-pink. Real ones are a dusty terracotta-rose with strong tonal variation and
  much lower saturation; in golden light they warm up but never look plastic.
- Trees were blobs/scaled cones. Need real branching (Sapling), leaf cards with translucency, and species mix:
  Monterey cypress, eucalyptus, Monterey pine, willows at the water.
- Water was a glossy mirror. Real lagoon: slight murk, green tint, gentle ripples breaking the reflection into streaks,
  correct Fresnel.
- Proportions drifted (attic zone too tall, dome too smooth/bright). Measure, don't eyeball.
- Nothing was ever compared side by side with a photo. This time every acceptance requires a comparison image.

## The team (see the original brief below for full role descriptions)
Lead/Art Director (only agent that talks to the user) · Reference & Research · Architectural Modeler ·
Ornament & Sculpture Modeler · Materials & Texturing · Environment · Lighting & Rendering · QA/Critic.

## Phases
0 Lead setup → 1 Reference sheet (blocking gate) → 2 Parallel build (arch, ornament, materials, env, lighting) →
gate: first master.blend + first comparison sheet → 3 Integration → 4 Polish loop (≥3 rounds) → 5 Deliver
(master.blend opens < 1 min, Eevee navigable, Cycles hero 3840x2160, flythrough path + low-res Eevee test animation).

## Non-negotiables
Real dimensions from reference, never eyeballed. No ornament asset identical twice at hero distance (vary weathering
per instance). No flat/clean/plastic materials. Every "matches reference" claim is backed by a side-by-side in
renders/qa_comparisons/. Keep the file viewable (LODs, mid LOD default). Log every significant decision in docs/decisions.md.

## Operating rules (added 2026-09-07 by the user; binding for the lead and every subagent)

### Model casting (updated 2026-09-09 by the user)
- The lead / art director runs on Fable 5.1 at high effort: coordination, reviewing previews against reference, merging,
  decisions. The lead does not write build scripts unless a fix is under 20 lines.
- Every builder and fix agent runs on **Opus 5** (`model: opus`, set explicitly when spawning): ornament and materials
  at xhigh effort, architecture / environment / lighting at high.
- Mechanical tasks (texture fetching, image cropping/resizing, file inventory, log filtering) run on Sonnet or Haiku.
- **The QA critic runs on Opus 5 at xhigh for every round.** Fable is used for QA exactly once: the final gate judgement
  before Phase 5.
- A code reviewer (Opus, no Blender, read-only) checks every branch before the lead merges it; findings go to
  `docs/reviews/<branch>_<round>_review.md`.
- Dispatch fresh agents every session; never resume an agent from a previous session. Briefs point at files
  (`docs/briefs/<agent>_r<N>.md`, the QA report, the notes' checkpoint section), never pasted content.

### Definition of done (set by the user 2026-09-09; binding)
- The polish gate passes when the hero (cam01) scores **4.0 or higher**, OR when two consecutive rounds after the
  concrete photo-projection pass improve the hero by **less than 0.1**. Either way, stop polishing and move to Phase 5.
- Phase 5 delivery: master.blend opens in under a minute; viewport navigable in Eevee; 4K Cycles hero from the lagoon
  viewpoint (first time a 128 spp fixed, adaptive-off render, then choose the final sample count from that wall time);
  flythrough camera path plus a short low-res Eevee test animation. Do not keep polishing past the rule.
- Round-5 decision stands (docs/decisions.md 2026-09-08, not to be re-litigated): the shade deficit is structural;
  lighting fixes the shade window first with the sunlit budget withdrawn; lighting and materials run sequentially on the
  merged master; the concrete gets a photo-projection pass if the hero is still flat after round 6.

### Concurrency
- Hard cap of **four** builder / fix agents at the same time. Their files must not overlap. Keep render sample counts
  low on every agent: they share one GPU.
- **Lighting and materials never run concurrently** (they measure on the merged master, sequentially).
- No agent waits on the GPU while another renders: give it a non-render task or do not dispatch it yet.
- Before the master rebuild (`scripts/lead_build.sh`), wait until no builder is mid-render.
- Builders wait for their own renders with ONE blocking shell command (`scripts/blender_run.sh`), never polling turns.
- Do not spawn an agent for anything one shell command can do.
- **No idling on serial steps (added 2026-09-09 by the user).** When the lead is blocked on a review, a master rebuild or a QA
  render, fill the slot with backlog work that needs no render and no write to master, each item on its own branch (Phase 5
  prep counts: flythrough path, delivery docs, projection UV layers, carried review findings). The GPU rule and the
  four-agent cap still apply.

### Blender process hygiene (added 2026-09-07; the machine swapped with three idle Blender instances holding 13 GB)
- Every `blender --background --python` run must exit when its script finishes. Never leave a Blender process
  waiting on stdin, a modal operator, or an interactive prompt; never launch Blender without `--background`;
  do not start a new Blender while your previous one is still running (`pgrep -fl "MacOS/Blender"` first).
- If a run wedges, kill it (`pkill -f "MacOS/Blender --background"` for your own runs) before starting another.
- **Watchdog (rewritten 2026-09-09):** every Blender run is launched through `scripts/blender_run.sh <max_seconds> -- <blender args>`,
  which registers the pid with a maximum duration and blocks until Blender exits. `scripts/blender_watchdog.sh --loop`
  kills ONLY pids whose registered max duration has passed. Idleness is never inferred from CPU (a Metal GPU render uses
  almost none) and never from log silence. Unregistered Blender pids are only reported, never killed. Choose the max
  duration honestly (Eevee preview pass 600 s, Cycles 1080p hero 1200 s, probe bake 1800 s, 4K timing 7200 s).
- Keep memory in mind: one full-scene render per agent at a time, low samples, and `bpy.ops.wm.quit_blender()` /
  natural script end, never `input()` or `time.sleep` loops inside Blender.


### Gate checks added 2026-09-10 (user; after the v1 hero shipped with the main arch filled by chord triangles)
- **Object-name sweep before every gate.** QA runs `scripts/qa_name_sweep.py` on master.blend before scoring: every render-visible
  object whose name matches placeholder / proxy / blocker / fill / occluder / block / dummy / temp / card is listed with its collection
  and owner; each hit is either a named, justified exception in docs/quality_checklist.md (e.g. ARCH_rotunda_inner_block_* are the real
  inner piers; ENV_backdrop_fill_* are the city blocks) or a blocker. No metric may be satisfied by an object that is not the building.
- **Full-resolution tile review of the hero before scoring.** The critic cuts the Cycles hero into six 100 % tiles (3 x 2 at the delivery
  resolution, 1920x1080 minimum) and views each tile, not the 960 px downscale, and reports every visible geometry or material defect
  (filled openings, flat untextured surfaces, missing ornament, plain cylinders, z-fighting, seams) as a defect regardless of the numeric
  metrics. The numeric boxes never override what the tiles show. The lead does the same tile pass on any final render before delivery.
- **Ray-cast test for openings.** Every arch / opening the hero or a QA camera looks through gets a ray test (`scene.ray_cast` from the
  camera station through the opening centre): the first hit must be the far side of the opening or the vault soffit at its modelled radius,
  never a face of the near vault, rib plate or archivolt inside the opening.

### Durability
- Every agent commits after every script that runs successfully, or every 15 minutes, whichever comes first.
  No agent may run 30 minutes without a commit.
- `docs/status.md` is the handoff file. The lead appends an entry (three lines max) on every merge, dispatch, agent
  report, or QA result: what is merged, what is in flight and on which branch, what is next.
- If a usage limit hits: stop. Do not wait or auto-resume. The user restarts the session, which resumes from
  `docs/status.md` and git.

### Context and image discipline
- Before viewing any render or comparison sheet, downscale it to 960 px wide JPEG
  (`sips -Z 960 in.png --out out.jpg` or `magick in.png -resize 960x out.jpg`). View one composite per gate or per fix,
  not individual crops. Never re-view an image already judged unless the underlying scene changed.
- Read files with offset and limit. Never read a file over 300 lines in full; grep first.
  Never read .blend, image, or texture files as text.
- Spawn prompts point at files (the brief, the defect list in `docs/qa_round_01.md`, `docs/sockets.md`) instead of
  pasting their contents.

# Phase 6 — Three.js walkthrough (added 2026-09-15; approved by the user with four changes, applied)

Nothing below changes Phases 0-5; the Phase 5 look (materials, lighting, AgX High Contrast, exposure -2.833)
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
- **ORN_ export is the user's decision.** Before the Gate 1 budget is written the lead logs in docs/decisions.md the three
  options — (a) unique mesh per instance, (b) true instancing with shared PBR and no ornament lightmap, (c) instancing with
  a per-instance lightmap-atlas offset and a custom material — each with its triangle count, texture memory and
  hero-visible cost, measured on the Gate 0 slice. The user chooses.
- **The LUT.** Blender does not expose OCIO to Python: `export/bake_lut.py` pushes an identity Hald image through Blender's
  own view transform at -2.833 EV and reads it back; anything else is documented in docs/tech_notes.md after Gate 0 with
  its verification against a Cycles render. A wrong LUT makes every parity score wrong.
- **Lightmap encoding.** The EXR -> three.js conversion must survive the linear value range implied by -2.833 EV; Gate 0
  reports min, max and clipped-pixel count for the slice assets, and every later bake round reports the same per asset.

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
  fallback (LOD1 geometry, halved textures) that loads and walks, tested in iOS Safari on the iPhone the user names at Gate 5; staging URL with one QA round against it.
- 6a stops at parity or after two flat QA rounds following Gate 4. 6b stops at deployment plus one clean QA round.
  Polish beyond that is a new phase. Gaussian splats only if the user asks, off the critical path.
- Gates 0-5 as docs/briefs/phase6_plan.md; every gate carries the name sweep (`scripts/qa_name_sweep.py` on the export
  set) and the six-station full-resolution tile review; Gate 0 (one ARCH_ asset, one INST_ ornament instance, ground, sky) must pass before any scale-up.

## Budget
Claude Max 20x; Phase 6 target <= 40 weekly points. Burn logged in docs/status.md at the end of every session
(`python3 docs/usage/usage_from_transcripts.py`). Clean restart past 350k context; on a usage limit stop.
