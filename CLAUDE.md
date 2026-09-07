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

### Model casting
- The lead / art director runs on Fable 5.1 at high effort: coordination, reviewing previews against reference, merging,
  decisions. The lead does not write build scripts unless a fix is under 20 lines.
- Every builder and fix agent (architecture, ornament, materials, environment, lighting) runs on **Opus 5**
  (`model: opus`, set explicitly when spawning).
- Mechanical tasks (texture fetching, image cropping/resizing, file inventory, log filtering) run on Sonnet or Haiku.
- The QA critic runs on Opus 5 for round 2; if its scoring is lenient vs the lead's own read it moves to Fable.

### Concurrency
- At most **four** builder or fix agents run at the same time (raised from two by the user on 2026-09-07). Their files
  must not overlap. Keep render sample counts low on every agent: they share one GPU.
- Do not spawn an agent for anything one shell command can do.

### Blender process hygiene (added 2026-09-07; the machine swapped with three idle Blender instances holding 13 GB)
- Every `blender --background --python` run must exit when its script finishes. Never leave a Blender process
  waiting on stdin, a modal operator, or an interactive prompt; never launch Blender without `--background`;
  do not start a new Blender while your previous one is still running (`pgrep -fl "MacOS/Blender"` first).
- If a run wedges, kill it (`pkill -f "MacOS/Blender --background"` for your own runs) before starting another.
- Any headless Blender whose CPU time stops advancing for more than 5 minutes gets killed. `scripts/blender_watchdog.sh` does this
  (one pass, or `--loop`); the lead keeps the loop running during agent waves. Do not depend on it: exit cleanly.
- Keep memory in mind: one full-scene render per agent at a time, low samples, and `bpy.ops.wm.quit_blender()` /
  natural script end, never `input()` or `time.sleep` loops inside Blender.

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
