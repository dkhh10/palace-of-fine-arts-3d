# Reconstruction feasibility probe (exploratory, nothing committed, nothing under the project tree is modified)

Goal: find out whether our internet photo collection of the Palace of Fine Arts registers in structure-from-motion well
enough to support a 3D Gaussian Splatting / photogrammetry route. Report numbers, not opinions.

Inputs (READ-ONLY): /Users/dk/Projects/3d render blender 3rd attempt building/reference/photos/raw/  (219 jpg/png)
and the index reference/photos/index_wikimedia.csv (columns ref,file,cat,w,h,date,desc,src; cat in {rotunda, main, night, ppie1915, ...}).
Work directory (everything you create goes here): /private/tmp/claude-501/-Users-dk-Projects-3d-render-blender-3rd-attempt-building/c29d6ec2-842b-4054-9354-4e207fbf8bf1/scratchpad/recon_probe/

Machine: Apple M2 MacBook Air, 24 GB, no CUDA. Homebrew available. /usr/bin/python3 is the Xcode stub and does NOT work;
use /opt/homebrew/bin/python3.12 or `uv run --python 3.12`. Do not launch Blender. Do not run anything on the GPU except
what COLMAP does natively. Keep every process under 45 minutes wall; if a step will exceed that, downscale or subsample.

Steps:
1. `brew install colmap` (if not present; `which colmap` first). Report the version and whether it has GPU SIFT (Metal) or CPU only.
2. Build the image set: exclude cat night and ppie1915 and anything clearly historical (desc mentions 1915, exposition, postcard) or
   that is a crop of an ornament only (desc mentions capital, detail, statue close-up) — keep those in a second list "detail".
   Downscale the kept set to max 1600 px on the long edge into work/images/ (sips or PIL). Report the counts.
3. COLMAP: feature_extractor (SIFT, single camera per image, EXIF focal if present, else default), then matching. Use
   `exhaustive_matcher` if the set is <= 220 images (it is), otherwise vocab tree. Then `mapper`. Use `--Mapper.ba_global_use_pba 0`
   style safe defaults. Time each stage.
4. Report, per reconstruction (COLMAP may produce several sub-models): number of registered images, number of 3D points,
   mean track length, mean reprojection error, and which categories (rotunda/main) registered. List the 10 largest-resolution
   images that did NOT register and a one-line guess why (night, crop, different era, no overlap).
5. Export the largest model as PLY (model_converter --output_type PLY) and render a quick top-down and side scatter plot of the
   sparse points + camera centres with matplotlib (uv run --with matplotlib) to work/plots/*.png at 960 px. Judge from the plot:
   does the camera set cover the rotunda from the lagoon side only, or all around? Is the colonnade covered?
6. If time remains (< 45 min total used), also run `colmap patch_match_stereo` is NOT required (CPU only, too slow) — skip dense.
   Instead estimate: with this registration, would a 3DGS trainer (OpenSplat, Metal) have enough views? Rule of thumb: >= 60
   registered views with >= 20 deg spread for a facade.

Deliver a report at work/REPORT.md (under 600 words) with: tool versions, counts, timings, the per-model table, the plot
paths, and a one-paragraph verdict: (a) enough for a splat of the rotunda from the lagoon side? (b) of the whole colonnade?
(c) what extra photo sources would fix the gaps (e.g. Mapillary street-level imagery, Flickr API by geotag, a site visit).
Do not commit. Do not touch git. Do not write anywhere under the project tree.
