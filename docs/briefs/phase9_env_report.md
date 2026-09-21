# Phase 9 ENV — 8d R3 (tiled backdrop atlas) + the belt / shrub item — build report
Branch `phase9-env`, worktree `.claude/worktrees/phase9-env`, from main 711b63b. Brief: `docs/briefs/phase9_env.md`.

## Files
* `scripts/env_p9_tiles.py` (new) — generates the four tileable **gain** maps into `assets/textures/backdrop/`
  (numpy, project-owned / CC0, nothing fetched). Every channel mean is exactly **0.505** by construction:
  0.500 would be mean-preserving in linear albedo, but AgX is concave there and rendered ~1 % dark (measured).
* `scripts/env_p9_uv0.py` (new) — lays UV0 (`"UVMap"`, layer 0 = TEXCOORD_0) on the backdrop, per face, in **tile
  units**. Called last from `env_backdrop.build_all`; also runnable standalone to patch an existing ENV file.
* `scripts/env_p9_preview.py` (new) — Eevee 1920x1080 previews of cam01/05/06 from the rebuilt master.
* `scripts/env_p9_probe.py` (new) — the measurement tables (`--sheet`, `--belt`, `--all`); re-uses
  `qa_r22_probe._bd` / `BACKDROP` (QA's own definitions) and adds the item-2 belt table.
* `scripts/env_p9_shrubhash.py` (new) — the item-2 shrub-placement hash, so that claim is reproducible.
* `scripts/mat_build.py` — `BACKDROP_TILES` / `BACKDROP_HAZE`, `backdrop_tile_detail()`, `apply_backdrop_tiles()`
  (MAT_backdrop_* block only, the 8d precedent).
* `scripts/env_backdrop.py` — one call to `env_p9_uv0.apply()` at the end of `build_all`.
* `assets/environment.blend`, `assets/materials.blend`, `assets/textures/backdrop/*.png`.

## Two findings that shaped the round (both cost a measurement pass)
1. **`scripts/build_master.py` APPENDS.** `master.blend` carries `bpy.data.libraries == []`, so swapping
   `assets/*.blend` under an already-built master changes nothing in the render. Every before/after pair here is
   **two full `scripts/lead_build.sh` runs**. (Image *files* are still read from disk at open, which is what made
   the first, wrong pass look like it had a small effect — it was Eevee sampling noise on foliage edges.)
2. **Applied before `backdrop_atmosphere` the gain is erased.** cam06's Marina houses are at 506 m, where R1's
   haze replaces 58.5 % of the albedo with a flat tint; the measured hf gain over the whole first pass was
   +0.0002. The gain now runs **after** the haze with a rolloff of its own (`keep` = the fraction of amplitude
   that survives full haze). R1's means are still exact: the gain is mean-1.0, so it moves variance, not level.

## Item 1 — the tiled facade / roof / canopy atlas
| image | px | tile (m) | texels/m | channel sd | material | strength / keep |
|---|---|---|---|---|---|---|
| `bd_facade.png` | 1024² | 16.0 x 13.2 (4 bays x 4 storeys: bay 4.0 m, storey 3.3 m) | **64.0 x 77.6** | 0.128 | MAT_backdrop_building | 1.25 / 0.70 |
| `bd_roof.png` | 512² | 16.0 x 16.0 | 32.0 | 0.109 | MAT_backdrop_roof | 1.15 / 0.70 |
| `bd_rooftile.png` | 512² | **8.10 x 7.92** (27 pans of 0.30 m x 24 courses of 0.33 m) | 63.2 x 64.6 | 0.095 | MAT_backdrop_roof_tile | 1.10 / 0.70 |
| `bd_canopy.png` | 1024² | 24.0 x 24.0 | 42.7 | 0.115 | MAT_backdrop_forest | 1.20 / 0.70 |

Texel density on the facades seen from the hero is **64 x 77.6 texels/m**, against the brief's >= 8 and against
the Gate-2 bake's 0.79. UV0 per face: `|nz| >= 0.5` -> planar world XY; otherwise u along the face's own
horizontal tangent (the street), v = height above the object's own base, plus a name-hashed phase per object so
neighbouring blocks do not line their storeys up. 1 291 meshes, 406 495 loops, **UV1 untouched**.

**Tileability (review r1 fix-now 1).** `python3 scripts/env_p9_tiles.py` now ends with `seam()`, the reviewer's own
measure: the mean |Δ| between the first and last row (V) / column (H) — the pair the repeat makes adjacent —
against every interior neighbouring pair. Two comparisons, because an image with designed hard edges (a storey
line, a course butt, a felt seam) *should* have a wrap that looks like one of them: **vs the interior mean** says
whether there is an edge at all, **vs the interior maximum** says whether it is unlike every edge the image
already contains. A wrap above the interior max is a seam.

`bd_rooftile` was 8.0 x 8.0 m = 26.67 pans of 0.30 m and 24.24 courses of 0.33 m — the phase did not close:

| tile | wrap V | / interior max | wrap H | / interior max | verdict |
|---|---|---|---|---|---|
| bd_rooftile **8.0 x 8.0 (before)** | 0.1491 | **1.12x** | 0.1158 | **5.11x** | **SEAM both axes** |
| bd_rooftile **8.10 x 7.92 (shipped)** | 0.1235 | 0.91x | **0.0039** | 0.17x | ok |
| bd_facade 16.0 x 13.2 | 0.1749 | 0.38x | 0.1479 | 0.57x | ok (its own storey / pier lines) |
| bd_roof 16.0 x 16.0 | 0.1826 | 0.92x | 0.1514 | 1.00x | ok (its own felt seams) |
| bd_canopy 24.0 x 24.0 | 0.0029 | 0.13x | 0.0013 | 0.03x | ok (seamless by construction) |

The pitches are the real ones (a mission pan is ~0.30 m, a course ~0.33 m), so the **tile** moved to the nearest
integer multiple of each rather than the pitch moving. The shipped V wrap of 0.1235 is not a seam: it sits inside
the interior course-line population (24 interior row pairs run 0.051-0.1363), i.e. the wrap **is** a course line,
which is what a course line should look like. Texel density 64.0 -> **63.2 x 64.6**, still 8x the brief's floor.
**Because UV0 is stored pre-divided, the tile size lives on the mesh**: `env_p9_uv0.TILE["MAT_backdrop_roof_tile"]`
moved 8.0/8.0 -> 8.10/7.92 and `assets/environment.blend` was rebuilt. Nothing else in the chain changes —
`assets/materials.blend` is untouched (the material never sees a tile size) and the ENV tri delta is still 0.

RESULTS — re-measured on the **shipped** tiles after the fix-1 re-tile (Eevee 1920x1080 from the rebuilt
master, `scripts/env_p9_probe.py`, QA-22 boxes and definitions):

| box | st | before | after | Δ | cycles p9 | photo |
|---|---|---|---|---|---|---|
| **06 top row** hf | 6 | 0.0319 | **0.0356** | **+11.6 %** | 0.0274 | 0.1547 |
| 06 top row luma / sat | 6 | 0.484 / 0.297 | 0.480 / 0.301 | -0.004 / +0.005 | 0.401 / 0.365 | 0.788 / 0.094 |
| **06 city r1c3** hf | 6 | 0.0239 | **0.0297** | **+24.3 %** | 0.0147 | 0.0728 |
| 06 city r1c3 lum sd | 6 | 0.124 | 0.126 | +0.002 | 0.086 | 0.111 |
| **06 far field** hf | 6 | 0.0261 | **0.0314** | **+20.3 %** | 0.0211 | 0.1967 |
| 06 far field lum sd | 6 | 0.102 | 0.105 | +0.003 | 0.073 | 0.153 |
| 06 far lawn hf | 6 | 0.0503 | 0.0514 | +2.2 % | 0.0603 | 0.2190 |
| 01 N-colonnade band hf | 1 | 0.0506 | 0.0491 | **-3.0 %** | 0.0970 | 0.2027 |
| 01 N-colonnade band luma / sat | 1 | 0.195 / 0.666 | 0.193 / 0.676 | -0.002 / **+0.010** | 0.238 / 0.695 | 0.337 / 0.395 |
| 01 S-colonnade band hf | 1 | 0.0923 | 0.0911 | -1.3 % | 0.1137 | 0.2338 |
| 05 backdrop band hf | 5 | 0.0801 | 0.0786 | -1.9 % | 0.0997 | — |

**Sheet: `renders/qa_comparisons/env_p9_r3_sheet.jpg`** — row 1 cam06 whole frame, **row 2 the cam06 city band at
100 %**, row 3 cam01; left before, right after. At 100 % the blocks carry a bay/storey grid, sills, string courses
and roof furniture where they were pale untextured boxes. That is the qualitative half of the acceptance and it
is the clearest thing in the sheet.

**Cycles sees it** (`scripts/env_p9_cycles.py`, the same master rendered twice with only the tile PNGs swapped
for flat 0.505 stand-ins — master.blend reads them from disk, so no second build is needed; cam06 city band,
640x200 border, 24 spp): **hf 0.0225 -> 0.0287, +27.6 %**, luma 0.441 -> 0.440, sat 0.284 -> 0.287, and
**33.5 % of the band's pixels move by more than 4 levels**. The phase's 4K Cycles hero will carry the tile.

**What did NOT go the right way, stated plainly.** At cam01 and cam05 the backdrop bands lose 1-3 % of their hf
and gain 0.010-0.018 saturation, against a photograph that wants *more* hf and *less* saturation. Cause: in those
boxes the backdrop is a minority of the pixels (the hero band is 21 204 backdrop px in a 93 440 px box, and the
R2 belt covers most of the hall wall), so the tile only modulates thin slivers between columns, while the gain's
1 % AgX darkening applies to all of them — AgX then reads the slightly darker pixels as more saturated. Four
rounds were spent on this: amplitude up (round 2), a +0.005 mean lift to cancel the AgX concavity (round 3,
recovered 0.001 luma), and a raised tile floor to stop the darkest window texels crushing in the AgX toe (round 4,
moved cam01 by 0.0000). **It is a property of modulating a small minority of a box's pixels, not of the tile**,
and I stopped rather than trade cam06's +12-25 % away for it.

**The honest ceiling.** cam06's hf is 0.0358 against the photograph's 0.1547. R1 named this ceiling for luma
("an albedo can only reach 1.0"); the same applies here — ref 105's city is at luma 0.79 / sat 0.09, a tonal
regime an albedo-side change cannot reach, and hf at that level is partly a *consequence* of the level. R3 buys
the structure; the remaining 4.3x is not an ENV-side number.

**Pin: ENV tri delta is 0.** LOD0 15 444 910 / LOD1 5 298 928 / LOD2 833 874, 6 042 objects — identical before
and after (`renders/logs/p9_env_build{1..5}.log`). No object renamed, none added, none removed. UV1 untouched.

## Item 2 — the belt cover and the shrub hard edge
The QA-24 residuals are stated **viewer vs Cycles**. The brief's question is a different one — *is the belt's
cover in Blender under the photograph's?* — and station 1 is the only station with a photo registration
(`env_r8_fit.REF_XF`), so it is the only place it can be answered with a number.

`python3 scripts/env_p9_probe.py --belt`, the QA-23 `BELT` boxes, Cycles p8 -> Cycles p9 -> ref 169, printed:

```
== item 2: the belt bands in Cycles, p8 -> p9, against the photograph where one is registered ==
box                  st frame       luma     sat      hf  lum sd   dark%
01 belt N (r2c1)      1 cyc_p8     0.274   0.667  0.0961   0.191  48.98%
                        cyc_p9     0.271   0.667  0.0965   0.190  50.09%
                        photo      0.350   0.377  0.2100   0.219  30.36%
01 belt S             1 cyc_p8     0.420   0.763  0.1121   0.245  24.08%
                        cyc_p9     0.418   0.759  0.1128   0.245  24.43%
                        photo      0.521   0.538  0.2449   0.261  12.02%
02 belt band R        2 cyc_p8     0.264   0.598  0.0696   0.246  61.37%
                        cyc_p9     0.260   0.606  0.0688   0.247  62.93%
05 belt band          5 cyc_p8     0.484   0.704  0.0912   0.242  15.37%
                        cyc_p9     0.481   0.701  0.0921   0.243  15.85%
```
(stations 2 and 5 have no photo registration, so they carry no photo row.)

**The belt's Cycles cover is OVER the photograph's, not under it** — 0.271 against 0.350 and a dark share of
50.1 % against 30.4 % at the hero band, 24.4 % against 12.0 % at the south band. The brief's conditional
("if the belt's Cycles cover is itself under the photo's, add crowns in the gaps") therefore does **not** fire:
adding crowns would move away from the reference. **No crown added, 39 rows untouched, far-tree JSON not
re-dumped** (no row moved). The Phase 9 relight moved the belt bands by at most 0.004 luma, so the p8 -> p9
Cycles control is unchanged for this question.

The 2.4-point cam02 / 3.6-point cam05 shortfalls of QA 24 are **viewer under Cycles**, and at gate13 they are
wider, not narrower (`qa_r25_probe crossings`: cam02 foliage share 57.71 % against Cycles 72.26; cam05 crossings
9.79 against 15.89, foliage 5.82 % against 20.50) — measured against the *Phase 8* Cycles column that the probe
still carries, i.e. before the Phase 9 relight. **Hand-off to BAKE / EXPORT: the belt geometry matches the photo
in Cycles; what the viewer loses is in the impostor bake, not in `assets/environment.blend`.**

**The shrub hard-edge rise is not a placement.** The four belt-r2 commits (`10f9f5f`, `8adb4ba`, `498137a`,
`0748e42`) touch only `scripts/env_trees.py` and `scripts/env_backdrop.py`; `scripts/env_build.py`, which owns
`build_shrubs()` and its seeded RNG, is untouched since Phase 8a (`0f7eee1`), and shrubs are built *before* the
trees, so no shrub was re-seeded or moved. Verified on the files, not inferred: the shrub/reed world-position
hash is identical in the pre-belt `assets/environment.blend` and in the current one (see below). QA 24's own
wording is the right diagnosis — the edges rose because **the belt stands behind those shrubs**, raising the
local contrast at an unchanged silhouette. There is nothing to restore. Residual stays with the belt's
brightness (BAKE), not with ENV placement.

**Shrub-position hash — reproducible** (`scripts/env_p9_shrubhash.py`, committed after review r1 carry 5):

```
git show 10f9f5f:assets/environment.blend > /tmp/env_prebelt.blend
scripts/blender_run.sh 600 -- --background --python scripts/env_p9_shrubhash.py -- \
    /tmp/env_prebelt.blend assets/environment.blend
[env_p9_shrubhash] /tmp/env_prebelt.blend: 4137 shrub/reed objects, md5 748f334363711ebd75565d0fd4526498
[env_p9_shrubhash] .../assets/environment.blend: 4137 shrub/reed objects, md5 748f334363711ebd75565d0fd4526498
[env_p9_shrubhash] IDENTICAL across 2 files
```
Bit-identical placement pre-belt and now. Nothing to restore.

## Export hand-off (export engineer)
The tiled UV0 **cannot ride the baked 1K UV1 atlas** — that atlas is 0.79 texels/m on the facades and the tile is
64. The exporter must pass the tile images through as REPEAT-sampled textures on **TEXCOORD_0**, multiplied over
the baked atlas.

**The UVs are already divided by the tile size, so there is no texture transform to carry** — sample with wrap
REPEAT and nothing else.

* Images (`assets/textures/backdrop/`, 8-bit RGB PNG, **Non-Color / raw**, wrap REPEAT, mipmaps on):
  `bd_facade.png` 1024² (2.0 MB raw), `bd_roof.png` 512², `bd_rooftile.png` 512², `bd_canopy.png` 1024².
  All four are tileable under `env_p9_tiles.seam()`; **`bd_rooftile`'s world tile is 8.10 x 7.92 m, not square** —
  it does not matter to the exporter (UV0 is pre-divided) but it matters if anyone re-derives the UV.
  KTX2 candidates: UASTC for `bd_facade`, ETC1S is enough for the other three.
* UV layer: `"UVMap"`, **layer 0**, on all 1 291 `ENV_backdrop_*` meshes. It survives Gate 1 unchanged —
  `gate1_set.py:804` excludes `kind == "backdrop"` from the UV1 atlas groups (so the layer-dropping loop at
  `:818` never runs on it) and `exp_mesh` uses `meshes.new_from_object`, which preserves UV layers; the per-
  material join at `:583` matches UV layers by name, which is why every object carries the same one.
  **Check at Gate 1:** the backdrop merges must come out with TEXCOORD_0 = the tile UV, and Gate 2's
  `smart_uv1` must land UV1 at **index 1** (TEXCOORD_1), not overwrite index 0.
* Node layout to reproduce (per backdrop group, `MAT_EXP_ENVBD__<src material>`):

      haze  = smoothstep(r0, r1, length(worldPos.xz)) * amount        // glTF Y-up: the Blender XY plane
      amp   = 2 * strength * (1 - (1 - keep) * haze)
      gain  = 1 + (texture(tile, TEXCOORD_0).rgb - 0.5) * amp         // per channel
      albedo = texture(bakedAtlas, TEXCOORD_1).rgb * gain

  | group | tile | strength | keep | r0 | r1 | amount |
  |---|---|---|---|---|---|---|
  | `MAT_backdrop_building` | bd_facade | 1.25 | 0.70 | 150 | 720 | 0.86 |
  | `MAT_backdrop_roof` | bd_roof | 1.15 | 0.70 | 150 | 720 | 0.86 |
  | `MAT_backdrop_roof_tile` | bd_rooftile | 1.10 | 0.70 | 180 | 720 | 0.84 |
  | `MAT_backdrop_forest` | bd_canopy | 1.20 | 0.70 | 210 | 1500 | 0.82 |

  The gain is mean-1.0, so it cannot move the group's mean albedo — parity against the Phase 9 Cycles refs is
  unaffected in level, only in variance.
* **Cheap variant** if a world-position term in the viewer shader is unwelcome: `keep` = 0.70 means `amp` only
  varies by 26 % across the whole haze range, so a constant `amp = 2 * strength * 0.82` is within 13 % of the
  Blender value everywhere and needs no world position. State which variant is used; the parity numbers should
  be taken on whichever ships.
* **Alternative:** bake at the tile's own repeat instead. Rejected here — it would need the backdrop atlas at
  ~64 texels/m, i.e. 1 170 168 m² of `MAT_backdrop_building` at 64 texels/m, which no atlas can hold.
