# Phase 10 round 1 — registered multi-view photo projection onto the rotunda and columns (brief from the lead, 2026-09-24)

Opus 5 xhigh. Fresh agent, "projection engineer". Branch `phase10-proj`, worktree `.claude/worktrees/phase10-proj` (already created from main;
`git merge main` first anyway). Read `docs/briefs/process.md` first, then `docs/approach_review_2026-09-24.md` §1-§4 and `docs/recon_probe/REPORT.md`.

## Why
Nine procedural rounds took the hero from 3.2 to 4.05. What still reads as CG is the *distribution* of surface appearance: one uniform yellow-brown
mottle at one frequency, columns that lost their dusty rose, no large-scale variation (rain streaks, patched panels, the waterline band). The
round-9 pass (`scripts/mat_projection.py`, one photo, one camera, `UVProj` from cam01, drum/attic/entablature only) proved the direction (+0.22).
This round is the registered, multi-view, delit version, on the rotunda's lagoon-facing half and its columns, baked into a proper UV atlas so it
works from every camera and survives the web export.

## You own (nothing else)
`assets/materials.blend` (MAT_concrete_* and the column materials; read `docs/materials_notes.md` last section for the hold list and node layout),
`assets/textures/projection2/` (new), `scripts/mat_p10_*.py` (new), `scripts/arch_uvbake.py` (new, ARCH-routed by the lead: it may add exactly ONE
UV layer `UVBake` plus nothing else to the listed ARCH meshes and save `assets/architecture.blend`, the precedent being `scripts/arch_uvproj.py`;
`UVMap` stays first, active and active_render; `UVProj` and `UVProj_valid` untouched), `docs/materials_notes.md` (new section "Phase 10 r1"),
`renders/previews/materials/*`, `renders/qa_comparisons/mat_p10_*`. Lighting is frozen (no edit to assets/lighting.blend, light_*.py). No ENV edits.
No geometry change. No edit to export/ or web/.

## Environment
`/usr/bin/python3` is the Xcode stub: never use it. Use `uv` (`uv venv --python 3.12` in your worktree under `.venv-p10/`, gitignored; or
`uv run --python 3.12 --with ...`). pycolmap 4.2 wheels, numpy, pillow, scipy, torch (MPS works: torch 2.14, diffusers 0.40 verified on this Mac),
matplotlib. Blender only through `scripts/blender_run.sh`. `pgrep -fl "MacOS/Blender"` before every run: a GUI Blender (pid 5262, the user's) may be
open; it is not yours, leave it, but do not start a Blender while one of YOUR runs is alive. The GPU is shared with the ENV agent (Eevee previews):
one full-scene render at a time per agent, never wait for the other agent.

## Steps (measure and commit after each)
1. **Registration.** Re-run the probe's SfM (`docs/recon_probe/{build_set,run_sfm,analyze}.py`, 7 min CPU) or load `docs/recon_probe/sparse/2` from the MAIN checkout (on disk, gitignored: 20 MB)
   (71 images, the lagoon-facing rotunda). Time-boxed option (<= 45 min): try hloc SuperPoint+LightGlue on MPS on the same 159 images; keep it only if
   it registers more rotunda / colonnade views into ONE model; report the counts either way.
2. **Align the SfM model to master world** (metres, origin = rotunda floor centre, +Y toward the lagoon): a 7-DOF similarity from >= 6 3D-3D
   correspondences (sparse points you can identify in the contact sheets at features whose world coordinates `scripts/arch_params.py` defines:
   column bases and capitals, drum cornice corners, the attic corners, the arch impost), then ICP refinement of the sparse cloud against points
   sampled from the ARCH rotunda meshes. Acceptance: reproject the master mesh's silhouette / strong edges into >= 5 registered photos (any
   Blender Freestyle or Z-edge render from the recovered camera at the photo's size) and report the median edge offset; target <= 4 px at 1600 px
   wide. Write `assets/textures/projection2/cameras.json` (per image: file, K, R, t in world space, registered size, alignment residual).
3. **`UVBake`** (`scripts/arch_uvbake.py`): a non-overlapping UV layer on the hero-facing rotunda meshes — the `arch_uvproj.py` object list (attic
   sweeps and the 00/07/01 panels, frames, niches, pilasters; entablature and its courses; drum, band, cornice) PLUS `ARCH_rotunda_column_*`,
   `ARCH_rotunda_colbase_*`, the archivolts and imposts of the lagoon arch; colonnade columns and entablature only if step 1 registers views of them.
   Group into at most four 4096x4096 atlases by band (attic / entablature / drum+columns / arch). Report texels per metre per group (target >= 200 on
   the rotunda). Both LOD objects share one mesh: write the layer on the mesh once. Verify with a check that fails (overlap test, layer order test).
4. **Bake position and normal atlases** (Cycles bake from `assets/architecture.blend` or the rebuilt master, world space, 32-bit EXR, one run
   <= 600 s) per atlas group.
5. **Depth per registered camera** from the rebuilt master in your worktree (`scripts/lead_build.sh` first): ARCH + ENV geometry, Z pass EXR at
   the photo's registered size, all cameras in ONE Blender run (Eevee or Cycles 1 spp, <= 1800 s). Trees and the colonnade must occlude.
6. **Projection in numpy** (`scripts/mat_p10_project.py`, no bpy): for every texel with valid position: project into each camera; depth test
   (tolerance ~ 0.05 m + 1 % of depth); facing weight (n·v)^k; border feather; a footprint-matched blur of the photo (texel size vs pixel size)
   before sampling. Aggregate with a weighted median in a luminance-normalised space; output per group: colour map, view-count / confidence map,
   and the hole mask (procedural fallback). Report per group: texel coverage %, median view count, the inter-view luminance std BEFORE delighting.
7. **Delighting, measured not assumed.** Candidates: (a) the multi-view median itself (photos of different dates and sun angles); (b) Marigold IID
   appearance (`prs-eth/marigold-iid-appearance-v1-1`, diffusers, MPS at 768 px, cap 40 photos, <= 2 h) applied per photo before projection;
   (c) the round-9 ratio method for ref 169's own view. Metric: the inter-view std of the projected colour on the sunlit-vs-shaded attic panels
   (the same panel under different suns must end equal) and the residual sun gradient across the drum. Pick the lowest, report all three.
8. **Integrate** in MAT_concrete_* and the column material: sample the atlas via `UVBake`; split into LF / MF / HF bands as `mat_projection.py`
   does and apply the LF + MF bands as the large-scale variation the procedural lacks (the procedural keeps its fine grain); global chroma handled
   as round 9's `M_chroma` (applied to the base albedo, so it holds from every camera and cannot seam); weight <= 0.7, multiplied by the confidence
   mask, procedural fallback elsewhere and on every unregistered face. The round-10b hold list (docs/briefs/materials_r10.md last lines: sunlit attic
   lum 186 +-2 / sat 0.52 / R-B +117; shaded attic 121 / 41 / 0.63; jamb hue 24; vault field 60.5) holds unless the new value is CLOSER to ref 169's
   box, which you state per box. Columns: measure ref 169's column-shaft boxes (hue / sat / lum at 1080p, the round-9 box tools) and land the
   shafts inside +-4 deg / +-0.04 of them.
9. **Measure on the rebuilt master**: ONE Cycles hero 1920x1080 64 spp (<= 900 s), ONE cam02 1280x720 64 spp and ONE cam03 1280x720 64 spp
   (<= 600 s each; seams and the far side), ONE Eevee hero (parity). Sheet `renders/qa_comparisons/mat_p10_sheet.png`: 100 % crops of attic, drum,
   column shaft, entablature, arch — before / after / ref 169, with the numbers; the anisotropy and std-ratio metrics from round 9 on the same boxes;
   the hold table; cam02 / cam03 seam crops. View composites only, at 960 px.
10. **Texture budget**: 8-bit PNG atlases, at most four at 4096 (2048 where the texel density allows), total MB stated; masks packed into one RGB.
    Hand-off to EXPORT in your report: the atlas rides inside the material node tree, so the Phase 6 PBR bake picks it up; say whether `UVBake`
    must survive the export (it should not need to) and list the images.

## Acceptance for the round (the lead judges on the sheet; QA 27 scores after the merge)
Registration residual <= 4 px; atlas coverage >= 80 % of the lagoon-facing texels; inter-view std after delighting <= 0.5x before; column shafts in
window; hold table within tolerance or closer to ref; no seam visible at 100 % on cam02 / cam03; hero attic anisotropy >= 2.0 (round-9 metric).
Report < 30 lines: files, each step's numbers, the sheet path, texture MB, open items, hand-offs, last commit id. Commit after every successful
script with the attribution line. If a step is impossible as written, say so with the measurement that shows it and do the nearest thing.
