# SfM feasibility probe: PFA reference photos (2026-09-24)

## Tools
- `brew install colmap` **failed**: Homebrew needs the Xcode licence accepted (sudo). I used **pycolmap 4.2.0 (COLMAP 4.2.0)** from PyPI in `work/.venv` (uv, Python 3.12) instead. It is **CPU-only** (no CUDA, no Metal SIFT).
- Pillow 12.3, matplotlib, numpy.

## Image set
- 219 raw files. `flickr_1..5` duplicate `ref_210..214`, so they were dropped.
- Excluded 44: night, ppie1915 and 1915/exposition/postcard descriptions. This includes 10 night-heron bird photos.
- Detail list: 11 files.
- **Kept 159** (86 rotunda, 73 main), resized to 1600 px in `work/images/`. Only 9 have an EXIF focal length.
- One night image leaked through the filter (ref_037).

## Timings (CPU)
One SIFT SIMPLE_RADIAL camera per image, exhaustive matching, incremental mapper.

| stage | time |
|---|---|
| extraction (11.3k keypoints/img; 8.4 GB peak) | 55 s |
| matching (12,561 pairs; 1,450 verified with ≥15 inliers) | 329 s |
| mapping | 47 s |
| **total** | **about 7 min** |

## Reconstructions (114 of 159 registered, split across 8 sub-models)

| model | images | points | track | reproj px | categories | content |
|---|---|---|---|---|---|---|
| 2 | **71** | 11,452 | 5.07 | 0.430 | rot 44 / main 27 | rotunda exterior, lagoon side |
| 3 | 19 | 2,071 | 3.60 | 0.733 | rot 17 / main 2 | interior dome coffers |
| 1 | 11 | 432 | 4.84 | 0.430 | rot 11 | one photographer's burst |
| 6, 7, 4, 5, 0 | 4, 3, 3, 3, 2 | 150, 1,615, 67, 38, 35 | 2.0-3.0 | 0.21-0.45 | mixed | fragments |

The sub-models are not connected: the interior (model 3) is separate from the exterior (model 2).

**10 largest unregistered images** (raw files are capped at 1920 px):
- Detail or statue crops: ref_106 Angel, ref_136 Garland Lady, ref_125 Ceiling Angel, ref_146 Light & dark
- Vegetation close-up: ref_129 ivy
- Night: ref_037
- Rear/Exploratorium side, which no other photo covers: ref_131
- Oblique or distant views with little overlap: ref_007 Rostra, ref_096 road trip, ref_182 March 2018 (guess)

The only colonnade-named photo (ref_138) did not register.

## Outputs
- `work/ply/model_2.ply`
- `work/plots/model_2_top_side.png` (960 px; top-down and side views, sparse points plus cameras)
- `work/plots/contact_model_{1,2,3}.jpg`
- `work/models.json`
- Scripts: `work/{build_set,run_sfm,analyze}.py`

**The plot:** all 71 cameras sit on one side of the cloud. Their azimuths span -34° to +23° (5th to 95th percentile), about **57°**. The largest empty sector is 274°. The views are **lagoon-side only**. The colonnade appears only as background, with no dedicated views and nothing from the walkway or the rear.

## Verdict
(a) **Rotunda from the lagoon: borderline yes.** 71 views over about 57° passes the ≥60-view, ≥20° rule for the lagoon-facing half, and 0.43 px reprojection error says the geometry is sound. Expect a splat that holds near the hero views, degrades beyond about ±40°, and has no back side. The photos mix dates and exposures, which calls for appearance embeddings, and OpenSplat has none.

(b) **Whole colonnade: no.** No model covers it, and the dome interior can't be joined to the exterior.

(c) **Fixes:**
- Mapillary / KartaView street sequences along Baker St, Marina Blvd and the colonnade walk.
- Flickr API search by geotag (within 200 m, after 2010, daytime).
- Best: a site visit with a video walk of the colonnade arc plus a 360° loop of the rotunda (frames every 0.5-1 m, overcast light).
