# Phase 9 ENV — 8d R3 (tiled backdrop atlas) + the belt / shrub item — build report
Branch `phase9-env`, worktree `.claude/worktrees/phase9-env`, from main 711b63b. Brief: `docs/briefs/phase9_env.md`.

## Files
* `scripts/env_p9_tiles.py` (new) — generates the four tileable **gain** maps into `assets/textures/backdrop/`
  (numpy, project-owned / CC0, nothing fetched). Mean of every channel is exactly 0.5 by construction.
* `scripts/env_p9_uv0.py` (new) — lays UV0 (`"UVMap"`, layer 0 = TEXCOORD_0) on the backdrop, per face, in **tile
  units**. Called last from `env_backdrop.build_all`; also runnable standalone to patch an existing ENV file.
* `scripts/env_p9_preview.py` (new) — Eevee 1920x1080 previews of cam01/05/06 from the rebuilt master.
* `scripts/env_p9_probe.py` (new) — the measurement table; re-uses `qa_r22_probe._bd` / `BACKDROP` (QA's own
  definitions) and adds the item-2 belt table.
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
| `bd_rooftile.png` | 512² | 8.0 x 8.0 | 64.0 | 0.094 | MAT_backdrop_roof_tile | 1.10 / 0.70 |
| `bd_canopy.png` | 1024² | 24.0 x 24.0 | 42.7 | 0.115 | MAT_backdrop_forest | 1.20 / 0.70 |

Texel density on the facades seen from the hero is **64 x 77.6 texels/m**, against the brief's >= 8 and against
the Gate-2 bake's 0.79. UV0 per face: `|nz| >= 0.5` -> planar world XY; otherwise u along the face's own
horizontal tangent (the street), v = height above the object's own base, plus a name-hashed phase per object so
neighbouring blocks do not line their storeys up. 1 291 meshes, 406 495 loops, **UV1 untouched**.

RESULTS (Eevee 1920x1080 from the rebuilt master, `scripts/env_p9_probe.py`, QA-22 boxes and definitions):

<!-- RESULTS -->

## Item 2 — the belt cover and the shrub hard edge
The QA-24 residuals are stated **viewer vs Cycles**. The brief's question is a different one — *is the belt's
cover in Blender under the photograph's?* — and station 1 is the only station with a photo registration
(`env_r8_fit.REF_XF`), so it is the only place it can be answered with a number.

`python3 scripts/env_p9_probe.py` -> `belt()`, the QA-23 `BELT` boxes, Cycles p8 -> Cycles p9 -> ref 169:

| box | cyc_p8 luma | cyc_p9 luma | photo luma | cyc_p9 dark<0.20 | photo dark<0.20 |
|---|---|---|---|---|---|
| 01 belt N (r2c1) | 0.274 | **0.271** | **0.350** | **50.1 %** | **30.4 %** |
| 01 belt S | 0.420 | 0.418 | 0.521 | 24.4 % | 12.0 % |
| 02 belt band R | 0.264 | 0.260 | — (no registration) | 62.9 % | — |
| 05 belt band | 0.484 | 0.481 | — (no registration) | 15.9 % | — |

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

**Shrub-position hash (measured, `/tmp/shrubhash.py` over both files):**
`10f9f5f:assets/environment.blend` (pre-belt) and the current one both give **4 137 shrub/reed objects,
md5 `748f334363711ebd75565d0fd4526498`** over `name|x,y,z`. Bit-identical placement. Nothing to restore.

## Export hand-off (export engineer)
The tiled UV0 **cannot ride the baked 1K UV1 atlas** — that atlas is 0.79 texels/m on the facades and the tile is
64. The exporter must pass the tile images through as REPEAT-sampled textures on **TEXCOORD_0**, multiplied over
the baked atlas.

**The UVs are already divided by the tile size, so there is no texture transform to carry** — sample with wrap
REPEAT and nothing else.

* Images (`assets/textures/backdrop/`, 8-bit RGB PNG, **Non-Color / raw**, wrap REPEAT, mipmaps on):
  `bd_facade.png` 1024² (2.0 MB raw), `bd_roof.png` 512², `bd_rooftile.png` 512², `bd_canopy.png` 1024².
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
