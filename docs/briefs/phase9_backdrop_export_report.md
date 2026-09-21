# Phase 9 backdrop export + viewer — report (export engineer, branch `phase9-backdrop-export`, 2026-09-21)

Brief: `docs/briefs/phase9_backdrop_export.md`. Spec: `docs/briefs/phase9_env_report.md` "Export hand-off".
Full technical write-up: `export/README.md` "Phase 9 — the backdrop gain tiles" and `web/README.md` "Phase 9".
Everything below is measured; nothing is claimed from the ENV report without re-measuring it here.

## 1. The four KTX2, both tiers

| key | source | px | encode | shipped B | rmse/255 vs the PNG | alternative codec | half-res (tex_lo) |
|---|---|---|---|---|---|---|---|
| `p9_bd_facade` | `bd_facade.png` | 1024² | UASTC q2 zcmp18 | **402 862** | **0.261** | etc1s 57 746 B @ 1.278 | 512 px, 26 199 B |
| `p9_bd_roof` | `bd_roof.png` | 512² | ETC1S c2 q128 | **37 968** | 1.667 | uastc 191 356 B @ 0.396 | 256 px, 11 748 B |
| `p9_bd_rooftile` | `bd_rooftile.png` | 512² | ETC1S c2 q128 | **42 948** | 2.710 | uastc 229 626 B @ 0.569 | 256 px, 11 592 B |
| `p9_bd_canopy` | `bd_canopy.png` | 1024² | ETC1S c2 q128 | **114 149** | 1.712 | uastc 884 888 B @ 0.395 | 512 px, 42 940 B |
| | | | | **597 927** | | | **92 479** |

All four Non-Color / linear, mipmapped, **no texture transform** (the UVs are already in tile units); REPEAT
is set by the viewer. `export/p9_bd_tiles.py` writes both tiers and the hand-off JSON; `--measure` decodes
each file back through `export/p8c_ktx2_compare.py` (pinned `ktx` 4.4.2) and prints the table above. The
codec split is the ENV report's recommendation, now with the numbers behind it: the worst case, `bd_rooftile`
at 2.710/255, is a **2.3 % albedo error at strength 1.10** — 5.3x cheaper in bytes than the UASTC that would
remove it.

## 2. The shader as shipped (`web/src/backdropTiles.js`, per fragment, after `#include <map_fragment>`)

```glsl
vec3  t    = texture2D( pfaBdTile, vPfaBdUv ).rgb;                 // vPfaBdUv = the `uv` ATTRIBUTE
float haze = smoothstep( pfaBdHaze.x, pfaBdHaze.y, length( vPfaBdXZ ) ) * pfaBdHaze.z;
float amp  = 2.0 * pfaBdStrength * ( 1.0 - ( 1.0 - pfaBdKeep ) * haze );
diffuseColor.rgb *= mix( vec3( 1.0 ), 1.0 + ( t - 0.5 ) * amp, pfaBdMix );   // pfaBdMix = ?bdtiles=
```

`vPfaBdXZ = ( modelMatrix * vec4( transformed, 1.0 ) ).xz` — glTF Y-up, i.e. the Blender XY plane, so the
haze radius is the same quantity `apply_backdrop_atmosphere` uses. The **world-position variant, not the
constant-`amp` one**, because the term costs one varying and a `length()` and keeps parity exact. Constants
straight from the ENV report, carried in `manifest.backdrop_tiles.groups` keyed by glb material name:
building 1.25/0.70/150-720 m x 0.86, roof 1.15/0.70/150-720 x 0.86, roof_tile 1.10/0.70/180-720 x 0.84,
forest 1.20/0.70/210-1500 x 0.82. `?bdtiles=0` is the A/B lever. The gain is mean-1.0 (the images measure
0.5050), so it moves variance, never a group's mean albedo.

## 3. The UV index change — both indices, and why it needed three code changes

**In `env.glb`: TEXCOORD_0 = the ENV tile UV, TEXCOORD_1 = the baked Gate 2 atlas.** In the manifest,
`backdrop_tiles.uv = {tile: "TEXCOORD_0", baked: "TEXCOORD_1"}` and `materials.sets[*].texcoord` = **1 on the
8 backdrop merges, 0 on the other 54** — the set is mixed by design, because `bird_white` and `lamp_post`
are merged by the same Gate 1 rule, take no gain tile and keep the atlas at TEXCOORD_0.

1. **`gltf_gate1.py`** — the Gate 2 atlas relay wrote into the layer *named* `"UVMap"`, which is now the tile
   layer (the ENV script uses the same name so `gate1_set.py`'s per-material join keeps it). It would have
   overwritten the tiles and shipped one UV set again. The atlas is now appended as a second layer
   (`"UVBake"`) whenever what is already there is not the npz layout — decided by **comparing against the npz
   array**, not by a UV span: `backdrop_door_green` is one cube and its tile UV spans 0.941.
2. **`pbr.js`** — `t.channel = 0` became `t.channel = set.texCoord` in both `applyPbrSets` and
   `upgradePbrSets`, plus a report of the per-channel counts and of any texture two sets want on different
   channels (three's `channel` is a property of the texture, so that would be silent).
3. **`gltf_pack.sh` AND `tiers.PACK_FLAGS["env"]`** — env takes **`-vtf`** in both packs. gltfpack
   quantises every texcoord stream of a mesh on ONE shared UV box: measured on a purpose-built two-set
   glb, a 0..300 set and a 0..1 set came back under a single `KHR_texture_transform` of scale **4801**,
   leaving the [0,1] set **14 of its 4096 steps**. Review r1 blocker 1: the first round put the flag only
   on `gltf_pack.sh`, which builds `gate1/env.glb` — **not a shipped file**. The viewer fetches
   `gate5/groups/env_t0.glb`, `env_t2.glb` and the `m_*` twins, re-packed by `tiers.pack()`, and those
   came out with both sets as normalised shorts under one transform at scale **483.92** = **8.5 of 4096
   steps** for the bake atlas (reproduced here by re-packing the fixed group without the flag; the
   reviewer measured 483.89 on the file as it shipped). With the flag on both packs there is no shared
   box and no transform, so `uvDequant.js` skips the mesh and the atlas keeps full float precision.

**The test that fails if the two are swapped**: `web/test/backdrop_tiles_test.mjs`, in `npm test`. It pins the
manifest parse, the swapped case (`checkUvContract` reports it and `applyBackdropTiles` then patches
**nothing**), the compiled shader, the amplitude arithmetic, the shipped `env.gltf` (two sets; TEXCOORD_0 in
tile units on 7 of 8 merges; TEXCOORD_1 filling [0,1] on 8/8), the packed `env.glb` (both sets float, no
transform left — on the four PUBLISHED groups `env_t0` / `env_t2` / `m_env_t0` / `m_env_t2`, not on the
`gate1/env.glb` intermediate the first round checked) and both shipped gate5 manifests.
`verify_glb --gate5` now reads the same accessors (`backdrop_tiles.group_primitives_float` 8/8). Export side, the same swap fails twice more:
`manifest_v3`'s cross-check (10/10 meshes match the bake npz at **1.00000**, V-flipped) and
`verify_glb --gate5`. `gate2_common.smart_uv1` carries a hard assert so a future backdrop re-bake cannot
smart-project on top of the tile UV.

**The backdrop lightmaps were NOT re-baked, and did not need to be**: the tiles are an *albedo* modulation
and the bake is lighting-only. No `gate3` output was touched; `gate3_relay_check` PASSes on the same 7 UV2
relays and 14 COLOR_0 attributes as before.

## 4. sha256 before / after the re-export

| glb | before | after | bytes |
|---|---|---|---|
| `arch.glb` | `efc43e8a…` | `efc43e8a…` | 4 613 040 → 4 613 040 **identical** |
| `orn.glb` | `f7f40de7…` | `f7f40de7…` | 154 253 424 → 154 253 424 **identical** |
| `ground.glb` | `816c87de…` | `816c87de…` | 1 959 104 → 1 959 104 **identical** |
| `env_trees.glb` | `d807775b…` | `d807775b…` | 3 769 236 **identical** (not re-run) |
| `env_trees_lod1.glb` | `5de5d7c3…` | `5de5d7c3…` | 7 642 536 **identical** (not re-run) |
| `env_shrubs.glb` | `3a615630…` | `3a615630…` | 668 388 **identical** (not re-run) |
| `env.glb` | `ae4d76a3…` | **`d310e19a…`** | 36 990 836 → **38 560 908 (+1 570 072)** |

Full hashes: `renders/logs/p9bd_sha_before.txt` and the `p8d_pin --glbs` PASS beside them. Placed triangles
ARCH 949 382 / ORN 1 099 192 / ENV 895 052 — unchanged. `verify_glb` PASS; `--gate5` PASS desktop and
mobile; `tiers_test` all green; `name_sweep` PASS.

## 5. Payload

| | tier 0 | first frame on the wire | the four tiles |
|---|---|---|---|
| desktop before the round | 48 128 039 | 49.30 MB | — |
| desktop **after the r1 fix** | **48 164 618** | **49 314 019 B = 49.31 MB** (target 49.5, rule 50.0) | **tier 1, 597 927 B** |
| mobile before the round | 46 187 845 | 47.32 MB | — |
| mobile **after the r1 fix** | **46 542 733** | **47 681 185 B = 47.68 MB** | **tier 1, 92 479 B** (tex_lo) |

Resident (GPU) cost of the four tiles: **3.32 MB** (1.33 + 1.33 + 0.33 + 0.33, the budget doc's
`px² x 1 B x 4/3` rule for ASTC 4x4 + mips); the backdrop class reads 36.57 MB resident with them in.
`manifest_v3`'s projected total prints 1266.89 MB against its 1200 MB line — that projection was already
over before this round and the print is informational, not an assert; the number the viewer pays,
`tiers.resident_estimate_mb`, is **1256 MB desktop / 312 MB mobile**.

The first frame is **not** paying for the tiles — they are tier 1. Desktop ends 79 666 B *below* the
first (quantised) pack and 185 981 B under the 49.5 MB target: `env_t0.glb` grew 2 172 696 → 2 196 928 B
with the float UVs, and the tier-0 trim moved 32 placeholder maps out instead of 29. Mobile has no such
trim, so its +230 679 B is the group growth (`m_env_t0` / `m_env_t2` are byte-identical to their desktop
twins). The four `tex_lo` copies are also named in the DESKTOP plan as `mobile_only` rows, so a deploy
built from `manifest.json` carries them.

## 6. What I could NOT measure, and the commands that do it

The acceptance numbers the brief asks for — **cam06 city band hf before/after at the QA-22 boxes, the
cam01/cam05 backdrop-band regression, and the "nothing else moves > 0.5 % MAE" sweep** — are all *viewer*
measurements and need headless Chrome, which this round was explicitly not allowed to run (the lead owns the
capture window). Nothing in this report stands in for them. To take them, after the lead deploys:

```sh
(cd web && npm run build)                        # the dist the shot server serves
# the A/B: the SAME build and the same tiers, the layer on and then off, six stations per session
scripts/chrome_run.sh 900 -- node web/tools/screenshot.mjs --stations 1-6 \
    --size 1920x1080 --out renders/web/round26_bdtiles_on.png
scripts/chrome_run.sh 900 -- node web/tools/screenshot.mjs --stations 1-6 \
    --size 1920x1080 --query bdtiles=0 --out renders/web/round26_bdtiles_off.png
# the boxes and the metric: QA's own definitions (env_p9_probe re-uses qa_r22_probe._bd / BACKDROP)
python3 scripts/qa_r22_probe.py backdrop         # the cam01 / cam05 / cam06 bands, hf / luma / sat
python3 scripts/qa_r22_probe.py seam             # the cam06 city tiling / seam autocorrelation
python3 scripts/qa_r22_probe.py regress          # luma / MAE against the previous gate, masked
```

Both probes read frames by path, so the two capture sets above have to be the two they are pointed at; the
`*_camNN.png` suffix `--stations` writes is what the round's file names should keep.

Expect, from the Eevee/Cycles side the ENV round measured: cam06 top row **+11.6 %** hf, city r1c3
**+24.3 %**, far field **+20.3 %**; cam01 N-colonnade band **-3.0 %** and cam05 backdrop band **-1.9 %** hf
with +0.010-0.018 saturation — the named regression, caused by the backdrop being a minority of the pixels in
those two boxes. `?bdtiles=0` makes the A/B exact rather than inferred.

## 7. Suites, and where the work is

`npm test` **819 PASS, rc 0** (771 before + 48 new backdrop-tile checks); `web/test/tiers_test.mjs` all
green; `export/name_sweep.py` PASS; `export/verify_glb.py` PASS and `--gate5` PASS on **both** tiers with
`backdrop_tiles 4/4 published`; `export/p8d_pin.py --glbs` PASS; `npm run build` rc 0.

New: `export/p9_bd_tiles.py`, `web/src/backdropTiles.js`, `web/test/backdrop_tiles_test.mjs`.
Changed: `export/manifest_v3.py`, `export/gate5_common.py`, `export/tiers.py`, `export/verify_glb.py`,
`export/gltf_gate1.py`, `export/gate2_common.py`, `export/gltf_pack.sh`, `web/src/{manifest,pbr,main}.js`,
`web/package.json`, `export/README.md`, `web/README.md`, `docs/briefs/phase6_budget.md` (regenerated).

## 8. Hand-offs

* **to the bake engineer** — a Gate 2 backdrop re-bake now hits an assert in `gate2_common.smart_uv1`. The
  fix is in the message: bake to a second layer (`"UVBake"`, which `gltf_gate1.py` ships as TEXCOORD_1) and
  hand THAT layer's loops over in `backdrop_uv1.npz`. Until then the shipped atlas layout is unchanged and
  `backdrop_uv1_shipped.npz` still matches it at 1.00000.
* **to the lead** — `export/out` in this worktree is a symlink to MAIN's, which is how the chain wrote MAIN
  directly (`ROOT == MAIN`, the re-bake round's arrangement) without anything being hand-copied. It is in
  `.git/info/exclude`, not in the branch. Delete it before reusing the worktree.
* **to QA** — `?bdtiles=0` is the A/B lever for round 26; the gain is a pure albedo modulation, so a station
  whose frame has no backdrop pixels must score identically with it on and off.
* **carried, not fixed** — `export/p9_geom_pin.py` was not re-run (it needs a `--shipped` reference this
  round did not produce). Geometry is covered instead by the six byte-identical glbs and the unchanged placed
  triangle counts.

## Capture (lead's window)

Captured by the capture engineer on this branch at **2b2c551** (the `-vtf` re-pack; an earlier window on 28c618b was
discarded because the shipped env groups still carried quantised UV). `(cd web && npm run build)` rc 0, then two
six-station sessions through `scripts/chrome_run.sh 900 -- node web/tools/screenshot.mjs --stations 1-6 --size 1920x1080
--frames 0` with the gate5 look query (`manifest=/assets/gate5/manifest.json tiers=all t=0 billboards=0 treeboards=0
lighting=baked post=all probe=1 impostors=1 water=1`): `renders/web/round26_bdtiles_on_cam0N.png` and, adding
`--query bdtiles=0`, `round26_bdtiles_off_cam0N.png`. No Blender ran (checked in its own shell command — the guard in
screenshot.mjs matches the invoking shell's argv, so the literal process name must stay out of the run's command line).

**Boot state.** ON: `backdrop tiles: 4 group(s), 0.60 MB, tile UV TEXCOORD_0, baked atlas TEXCOORD_1`, patched 2 + 2
materials over the tiers (0.44 + 0.16 MB). OFF: `backdrop gain tiles OFF (?bdtiles=0); the manifest carries 4 group(s)`.
`pageErrors: []` both. The env groups no longer appear in the `uv dequantisation` lines (the `-vtf` sets are float);
resident 1688.2 MB, 145 files / 132.5 MB, draws and triangles identical per station.

### cam06 hf, ON vs OFF, against the ENV round's Eevee deltas (`qa_r22_probe.BACKDROP`)

| box | hf OFF | hf ON | Δ viewer | Δ ENV Eevee | cycles r09 | photo (ref105) |
|---|---|---|---|---|---|---|
| 06 top row | 0.0405 | **0.0470** | **+16.0 %** | +11.6 % | 0.0237 | 0.1409 |
| 06 city r1c3 | 0.0240 | **0.0327** | **+36.7 %** | +24.3 % | 0.0174 | 0.1103 |
| 06 far field | 0.0240 | **0.0329** | **+37.2 %** | +20.3 % | 0.0231 | — |
| 06 far lawn | 0.0845 | 0.0862 | +1.9 % | +2.2 % | 0.0394 | — |

### The named cam01 / cam05 regression does not reproduce in the viewer

| band | hf OFF → ON | Δ viewer | Δ ENV Eevee | Δ sat viewer | Δ sat Eevee |
|---|---|---|---|---|---|
| 01 N-colonnade | 0.1365 → 0.1368 | **+0.2 %** | -3.0 % | +0.0004 | +0.010 |
| 01 S-colonnade | 0.1714 → 0.1719 | +0.3 % | -1.3 % | +0.0007 | — |
| 05 backdrop band | 0.1248 → 0.1252 | +0.3 % | -1.9 % | +0.0007 | +0.018 |

The shader's `(t - 0.5)` term is exactly mean-1.0, so the PNGs' +0.005 AgX-compensation lift — the cause of the Eevee
loss — never reaches the frame. Nothing to fix viewer-side.

### Whole-frame MAE ON vs OFF, and where the pixels moved

| st | MAE (0-255) | MAE % | px > 1/255 | changed rows / cols (5-95 pct) | what is there |
|---|---|---|---|---|---|
| 1 | 0.152 | 0.060 % | 2.14 % | y 549-841 | backdrop band (524-670) + its water reflection |
| 2 | 0.080 | 0.032 % | 0.64 % | y 718-893, x 1409-1708 | the one backdrop patch in frame |
| 3 | 0.0015 | **0.001 %** | 0.02 % | y 535-772, x 840-981 | backdrop slivers between the columns |
| 4 | 0.0000 | **0.000 %** | 0.00 % | — | no backdrop pixels (rotunda interior) |
| 5 | 0.115 | 0.045 % | 1.18 % | y 669-1070 | backdrop band (654-786) + reflection |
| 6 | 1.666 | 0.653 % | 22.94 % | y 17-777 | the aerial's city / far field — the target |

Stations 3 and 4 sit at 0.001 % / 0.000 % against the brief's 0.5 %; elsewhere only backdrop pixels and their water
reflections move. **Seam** (`qa_r22_probe seam`): the grid index falls with the gain on at every cam06 box
(city r1c3 -9.82 → -10.14, far field -9.13 → -9.71, top row -8.66 → -8.92) while hp std rises (8.16 → 8.86,
7.24 → 8.05, 10.08 → 10.54) — added detail, no new lattice.

### Against gate13 (deploy 13), above the waterline

| st | MAE ON vs gate13 | MAE OFF vs gate13 | luma ratio OFF |
|---|---|---|---|
| 1 | 0.231 | 0.187 | 0.9999x |
| 2 | 0.089 | 0.027 | 1.0002x |
| 3 | 0.0018 | 0.0015 | 1.0000x |
| 4 | 0.000 | 0.000 | 1.0000x |
| 5 | 0.114 | 0.061 | 1.0004x |
| 6 | 3.083 | **0.913** | **1.0048x** |

With the gain off the new assets reproduce gate13 to 0.9 MAE / +0.5 % luma on cam06 and to <= 0.19 elsewhere
(city r1c3: luma 0.424 vs 0.423, sat 0.337 vs 0.338, hf 0.0240 vs 0.0237). The whole cam06 change is therefore the
gain, not the re-export. (The discarded 28c618b window measured 6.81 MAE / +4.6 % luma here — that drift was the
quantised env UV, and the `-vtf` re-pack removed it.)

### The 100 % look

`renders/web/960/round26_city_band_100_off_on.jpg` and `round26_city_r1c3_100_off_on.jpg` (plus
`round26_city_r1c3_100_gate13_off.jpg` for the OFF-vs-gate13 control): at the aerial's distance the tiles read as
**facade and roof texture — window and bay rows, storey lines, roof courses on blocks that were flat gradient slabs —
not as noise or moiré**, and no repeat lattice is visible at 100 %.

960 px copies committed under `renders/web/960/round26_*`; full-size PNGs stay gitignored. Re-running the probes needs
MAIN's frames linked into the worktree (`renders/web/gate13_cam0N.png`, `renders/previews/qa/round10b_01_*`,
`reference/photos/raw`; all removed again after this round) and `qa_r22_probe`'s `CUR`/`PREV` repointed at the two tags.
