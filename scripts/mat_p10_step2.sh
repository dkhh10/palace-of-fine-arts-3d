#!/bin/zsh
# Phase 10 r1, step 2 recipe (registration), in order -- as run for the committed cameras.json.
# Metric (review part 1, finding 1): `peak` = the image shift that maximises the photo gradient along the model's
# occluding contour (+-40 px search); self-calibrating (a control shift s of the model reads back as s).  The first,
# chamfer-based metric (`check`) is kept only as a weak independent check: its control ratio is 1.05 at 10 px.
# The depth_arch renders are only a source of world-space contour points, valid while cameras are refined.
set -e
cd "$(dirname "$0")/.."
PY=.venv-p10/bin/python
W=assets/textures/projection2/work
$PY scripts/mat_p10_sfm.py dump                                   # 1  work/sfm.npz from the probe model
$PY scripts/mat_p10_align.py icp --sector=0                       # 2a similarity (deletes stale refine / edges files)
$PY scripts/mat_p10_align.py cameras                              # 2b cameras.json from the similarity alone
[ -f $W/depth_arch/meta.json ] || scripts/blender_run.sh 1500 -- --background assets/architecture.blend \
    --python scripts/mat_p10_depth.py -- --out $W/depth_arch --arch-only      # 2c ARCH LOD0 position passes, 71 cams
$PY scripts/mat_p10_edges.py peakfix $W/depth_arch                # 2d per-camera rotation from the peak -> refine_cams.json
$PY scripts/mat_p10_align.py cameras --with-cams
$PY scripts/mat_p10_edges.py peakfix $W/depth_arch                # 2e second iteration (composed)
$PY scripts/mat_p10_align.py cameras --with-cams
$PY scripts/mat_p10_edges.py peak   $W/depth_arch                 # 2f residual + control table -> edges.json
$PY scripts/mat_p10_edges.py check  $W/depth_arch --sheet renders/qa_comparisons/mat_p10_registration.jpg  # 2g weak check
$PY scripts/mat_p10_align.py cameras --with-cams --with-edges     # 2h residual_px, refine_rot_deg, physical gate
# usable for projection (mat_p10_project.py): residual <= 6 px, physical gate, per-camera correction <= 1.5 deg
