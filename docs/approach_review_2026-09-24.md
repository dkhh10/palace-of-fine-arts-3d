# Approach review: is there a better route to photoreal than the hand-built model? (lead, Fable 5.1, 2026-09-24)

Asked by the user: analyse what has been done, and think about different approaches given the large photo set,
including open-source ML that turns photos into 3D directly. Research by two Fable forks (reconstruction pipelines;
generative and hybrid tooling), a COLMAP registration probe on our own photo set by an Opus agent
(`docs/recon_probe/REPORT.md`), and the lead's own side-by-side of the delivered hero against the target photo.

## 1. Where the current approach stands

- Delivered: Phase 9 closed 2026-09-22, hero 4.05 / 5 against the photo, stations 3.05-3.55, web walkthrough live.
- Spend on the last three sessions alone: about 713 USD (sessions 8-10, docs/status.md), most of it Opus builders.
- The lead's eye on `renders/final/hero_cam01_3840x2160_128spp.png` vs `reference/photos/user/user_wide_midday.png`:
  proportions and massing are right, and the geometry is complete. What still says "CG" is appearance, not shape:
  1. The concrete is one uniform yellow-brown mottle at one spatial frequency everywhere. The real stone is a pale buff
     with large-scale variation (rain streaks, patched panels, the dark waterline band) and small-scale calm.
  2. The columns have lost their dusty rose; they read as the same brown as the entablature.
  3. The foliage silhouette is wrong at the composition level: the photo has tall dark Monterey cypress and pine crowns
     rising above the colonnade behind the rotunda; ours are low shrubs and thin trees. This is the single largest
     difference in the frame and needs no ML at all.
  4. The water is a saturated blue mirror; the real lagoon is olive-green, murky, with the reflection broken into streaks.
  5. Global tone: high saturation orange-on-blue. Golden hour is the brief, but the photo's colour regime is far calmer.
- Every one of these is an appearance residual. Nine rounds of procedural material tuning moved the hero from 3.2 to 4.05;
  the remaining gap is the distribution of real surface appearance, which procedural noise does not reproduce.

## 2. Can the photos be turned into the 3D model directly? (measured, not guessed)

COLMAP 4.2 (pycolmap, CPU) on the 159 usable daytime photos at 1600 px, 7 minutes wall (`docs/recon_probe/REPORT.md`):

| | value |
|---|---|
| registered images | 114 of 159, in 8 disconnected sub-models |
| largest model | 71 images, 11,452 sparse points, 0.43 px reprojection error |
| what it covers | rotunda exterior from the lagoon side only, camera azimuths spanning about 57 degrees |
| colonnade | not covered by any model (only as background) |
| dome interior | separate 19-image model, cannot be joined to the exterior |
| back / Exploratorium side | one photo, unregistered |

Verdict: the collection supports a reconstruction of the lagoon-facing half of the rotunda and nothing else. A pure
photo-to-3D model of the whole Palace from these photos is not possible. Internet photos of a landmark are all taken
from the same three spots.

## 3. What the tooling can and cannot do on this machine (September 2026)

Machine facts: Apple M2 Air, 24 GB, no CUDA. `/usr/bin/python3`, `git` and `brew install` are all blocked until the
Xcode licence is accepted (`sudo xcodebuild -license`); Homebrew Python 3.12/3.13 and `uv` work.

- **Structure-from-motion**: works here. pycolmap 4.2 wheels (CPU SIFT, GLOMAP built in), hloc (SuperPoint + LightGlue
  on MPS, more robust across seasons and lighting than SIFT), MASt3R via an MLX port as a fallback for hard images.
- **Gaussian splatting trainers on a Mac**: Brush (Rust/wgpu, mask training), OpenSplat (Metal), splatx-metal. A
  200-image scene is a 4-6 hour, thermally throttled job. None has per-image appearance embeddings, so a mixed-lighting
  internet collection produces ghosting and colour blotches; the fix is to curate one lighting family and mask people.
- **The good in-the-wild methods are CUDA-only**: WildGaussians, Splatfacto-W, SuGaR / 2DGS / PGSR (splat to mesh),
  LumiGauss / GaRe (relighting from photo collections), VGGT, Depth Anything 3 multi-view, Meshroom (no macOS build),
  RealityScan (Windows only). A borrowed CUDA box for one day would unlock them.
- **Relighting**: no method turns midday photos into a consistent golden-hour scene. Splats and photogrammetry bake the
  lighting of the photos in. Our physically lit Cycles scene is still the only way to the golden-hour brief.
- **Generative image-to-3D** (Hunyuan3D 2.1, TRELLIS.2, SAM 3D, SPAR3D, Tripo, Rodin): object scale, 0.5-1.5 m effective
  detail, invent ornament that is not the PFA's. Not useful for a measured building. Generated PBR textures
  (Hunyuan3D-Paint, Material Anything) reimagine rather than reproduce the weathering. Not recommended.
- **What does run on MPS and is useful**: monocular normals (StableNormal, Marigold) for ornament close-ups; intrinsic
  albedo / delighting models (Marigold-IID class, IDArb on a CUDA box) for the projected photos; Material Palette style
  tileable PBR extraction from our own photos for the algae band and streaks.
- **Splats in our pipelines**: KIRI 3DGS Render 5.1 renders splats in Blender 5.2 Cycles/Eevee; Spark 2.0 or PlayCanvas
  SOG in three.js at 10-14 MB per million splats, inside the 50 MB payload. A splat and the glTF build would not share
  lighting or the LUT.

## 4. Options, ranked

### A. Photo-derived appearance on the existing mesh, done properly (recommended first; no new photos needed)
Use the 71-view registration we already have. Align the SfM model to master.blend (known dimensions, six QA stations),
so every photo has an exact camera. Multi-view project a curated clear-sky subset onto the rotunda concrete, columns,
frieze and attic (UV0), take the median across views to suppress people and exposure differences, delight with an
intrinsic model on MPS, and blend with the existing procedural layer as the large-scale variation it lacks. Add
StableNormal / Marigold normals from the ornament close-ups (the 11 "detail" photos plus the rotunda set) for the
0.02-0.3 m band the critic keeps flagging. Restore the column rose from the projected colour rather than a tuned tint.
Expected gain: hero +0.2 to +0.4; the colonnade gains only what the rotunda projection can be tiled onto it.
Cost: two builders (projection engineer, ornament-normals engineer), a few GPU hours, no new dependencies beyond Python.
Risk: residual photo lighting in the albedo; seams at projection boundaries. The Phase 5 projection pass (MAT r9) already
proved the direction (+0.22) with a single photo and no registration; this is the registered, multi-view version.

### B. Environment and water without ML (recommended alongside A; the biggest visible lever)
Rebuild the tree band behind the rotunda to the photo's silhouette (tall cypress and pine crowns above the colonnade,
Modular Tree or Sapling skeletons with scanned bark and leaf textures from Poly Haven or our photos), and re-tune the
lagoon to olive-green murk with streaked reflection. Expected gain: hero +0.2 or more on the composition rows.
Cost: one ENV builder round plus one lighting/materials round for the water. Risk: none new.

### C. A real capture of the site, then a splat as ground truth and environment layer (best long-term, needs the user)
A phone video walk (colonnade arc, 360 degree loop of the rotunda, lagoon edge; overcast light; a frame every 0.5-1 m;
roughly one hour on site) plus a Flickr / Mapillary geotag harvest. Then hloc + pycolmap, Brush splat (4-6 h), KIRI in
Blender. Three uses, in order of value: (1) a measured overlay to find the last proportion and colour errors and a
colour source for every surface, not just the lagoon face; (2) a photo-textured environment layer (trees, banks, city
backdrop) composited behind the Cycles building; (3) optionally a pure-splat walkthrough via Spark in the web app, which
is the only route to a walkthrough that looks like a photograph, but at midday or overcast light, with no golden hour,
no rotunda reflection in the water and holes where the capture is thin.
Cost: the site visit, then about the size of one Phase 6 gate. Risk: lighting mismatch between a baked splat and the
golden-hour building; CLAUDE.md keeps splats off the critical path until the user asks.

### Not recommended
Generative image-to-3D for the building or its ornament; generated PBR textures; diffusion relighting for bakes;
a pure splat from the current collection (lagoon-facing rotunda only, midday, below 4.05 for the hero).

## 5. Decisions needed from the user
1. Accept the Xcode licence (`sudo xcodebuild -license`) so git, brew and the system Python work again; nothing below
   can be committed or installed until then.
2. Option A + B now (no new photos), or wait for a site capture (C) and do A + B against the fuller set?
3. Is a site visit possible, and when? A one-hour overcast walk is worth more than everything on Wikimedia.
4. Budget cap for the next phase, in weekly points, so the plan is sized to it.

The lead's recommendation: A + B now as Phase 10, sized at two builder rounds each with one QA gate; C when the user
can capture the site, as Phase 11, because it changes what A can reach for the colonnade.
