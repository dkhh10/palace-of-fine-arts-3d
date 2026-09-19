# Phase 8b viewer fix round — report (branch `phase8b-viewer`, 2026-09-19)

Brief: `docs/briefs/phase8b_viewer_fix.md`. Full detail, every table and every `?` switch:
`web/README.md` → "Phase 8b fix round (QA 20 carries)". Tests green (`npm test`, 12 suites).
No deploy, no Blender, nothing under `export/` touched. Chrome only through `scripts/chrome_run.sh`,
bake queue `idle` and `pgrep -fl "MacOS/Blender|headless"` empty before every run.

## a — `env_shrubs.glb` drawn in full at every station — **FIXED** (`1b5aa9c`, `9910ceb`)

**Cause.** The shrub/reed LOD1 set had only the *fragment* half of its distance switch. `loadShrubLod1`
sets `pfaSwitchDist` / `pfaSwitchSign`, and beyond 25 m (mobile) / 30 m (desktop) the dissolve discards
every fragment — but a discard costs the whole vertex shader and the whole rasterisation, and
`renderer.info` counts the submitted triangle either way. The *CPU* half — chunk the site-spanning
batches, then hide per frame any batch whose every row is beyond the limit — exists in `loadFarTrees`
since 6c round 2 and was never written for the shrubs. `shrubLod: lod1 0, source null` is a red
herring: that is `applyShrubLod`, an idle path reading a `raw.shrub_lod` block the manifest does not
carry.

**Measured, not guessed.** New `window.__pfaTrisByGroup()` renders one frame with a counting hook on
every mesh and attributes the submitted triangles and draws to the scene-level group, checked against
`renderer.info` for the same frame; `screenshot.mjs --groups` writes it per station. Before, at the
hero: `WEB_glb_env_shrubs` **2 024 352 tris in 50 draws** (25 meshes × the Reflector's second pass) of
6 361 468 — the whole set, at every station including the aerial. `?shrubcull=0` reproduces gate9's
triangle counts to the unit.

**Fix.** The far-tree chunk-and-cull extracted into `buildDistanceCull( root, { chunk, limit } )` and
applied to the shrub set at its own distance + fade band + `CULL_MARGIN_M`. `shrubLodUpdate` runs in
`renderFrame()`. **`?shrubcull=0`** restores the old behaviour; `?shrubcull=<n>` sets the chunk budget
(default **48**, swept against 128 — 128 buys 0.4 M more triangles at the hero for +53 draws at cam02
and is no faster in two interleaved pairs).

Desktop 2560x1440, interleaved A/C/A/C in one session (A = `?shrubcull=0`):

| st | ms before → after | tris before → after | Δ tris | draws | shrub tris before → after |
|---|---|---|---|---|---|
| 1 | 30.90 → 29.30 | 6 361 468 → 4 952 588 | **−1 408 880** | 335 → **317** | 2 024 352 → 615 472 |
| 2 | 34.80 → 33.05 | 6 344 584 → 5 510 136 | −834 448 | 329 → 341 | 2 024 352 → 1 189 904 |
| 3 | 39.35 → 36.50 | 7 111 092 → 6 030 448 | −1 080 644 | 351 → **343** | 2 024 352 → 943 708 |
| 4 | 25.70 → 26.80 | 3 293 588 → 2 961 488 | −332 100 | 184 → 197 | 1 012 176 → 680 076 |
| 5 | 30.50 → 30.55 | 6 125 874 → 4 928 054 | −1 197 820 | 320 → **308** | 2 024 352 → 826 532 |
| 6 | 33.75 → 32.25 | 6 729 552 → 4 705 200 | **−2 024 352** | 355 → **305** | 2 024 352 → **0** |

`?tier=mobile`: −0.34 M to −2.02 M triangles, draws −50 to +12, frame times at the 16.6 ms vsync floor
before and after (no ms signal there).

**Read the ms column as reported, not claimed**: an A-vs-A repeat in this session moved by up to
**7.8 ms**. The triangle and draw counts are deterministic and are what item a claims.

**Pixel parity.** Six desktop stations before vs after: cam02/03/04 **0 pixels** differ; cam01 7,
cam05 5, cam06 122 of 2 073 600 — and an A-vs-A repeat of cam06 differs by **134**. Pure culling.

## b — `resident()` never counted the impostor atlases — **FIXED, figure restated** (`bc643cd`)

**Cause.** A texture was reached through exactly eight `MeshStandardMaterial` slots, so everything in a
**custom uniform** was billed by nothing: the 16 impostor atlases (`uniform atlas`), the foliage
translucency maps, the AgX LUT. An opposite error sat beside it: geometry billed **per geometry
object**, while `chunkGeometry` gives every chunk a `BufferGeometry` that *shares* its vertex buffers.

**Fix.** Textures reached by TYPE — every `uniforms` entry whose value `isTexture`, plus the post
chain, plus `scene.background` / `scene.environment`, plus a widened slot list — with render-target
textures collected first and refused so `tDiffuse` / `envMap` are not billed twice (143 hits at the
hero). Geometry summed one entry per `BufferAttribute`. New keys: `texture_bytes_by_kind`,
`render_target_textures_skipped`, `geometry_bytes_before_dedup`, `info_memory`, `counted_vs_renderer`.

**The figure of record, hero, 2560x1440 desktop:**

| | pre-8b | restated | Δ |
|---|---|---|---|
| geometry | 261.5 MB | **114.5** | −147.0 |
| instance matrices | 0.3 | 0.3 | 0 |
| textures | 1 157.6 | **1 255.6** | **+98.0** |
| render targets | 443.8 | 443.8 | 0 |
| **total** | **1 862.9 MB** | **1 814.2 MB** | **−48.7** |

The +98.0 MB: impostor atlases **67.1** (never counted), sheen/clearcoat/transmission slots **25.2**
(never counted), `pfaTrnMap` **5.6**, LUT **0.07**. 67.1 MB = 16 × 4 194 304 texels × 1 B (ASTC 4x4),
so the band (4096x1024) and the 2K octahedral (2048x2048) cost **exactly the same** — `?impband=0`
measures 1 814.2 MB too, i.e. the "resident identical across the 1K→2K swap" claim was right about the
equality and wrong about the number.

`?tier=mobile` hero: **547.9 MB** (was 563.5); of its 236.4 MB of texture the sky equirect alone is
67.1 MB — **28 % of the mobile texture budget is the sky**, worth a look in 6b.
Item a's chunking costs **0 MB** (114.5 → 114.5 correct; 261.2 → 265.4 under the old rule).

README restated in three places that quoted the old level, and the `__pfaInfo().resident` schema is
now documented key by key. `p8_perf_table.py`'s `resident_mb()` (review r2 finding 2) was already fixed
on this branch.

## c — blue-violet shaded stone at desktop cam02 — **MEASURED, NOT A VIEWER FAULT; NOT IMPLEMENTED**

**The Phase 5 Cycles reference is MORE blue-violet than the viewer at every shaded box.** CIELAB, boxes
from `scripts/light_r16_measure.py BOXES["02"]`, reference `round13_02_…_cycles.png`, rubric photo
`ref_062`. Sheet: `renders/web/960/p8b_c_cam02_shade_sheet.jpg`.

| box | viewer b* | Cycles b* | photo b* | viewer R−B | Cycles R−B | photo R−B |
|---|---|---|---|---|---|---|
| shade_pier | **−2.73** | −5.01 | **+10.89** | +4.9 | +1.8 | +29.9 |
| shade_pier_r | **−10.97** | −18.35 | **+10.99** | −21.2 | −35.8 | +41.0 |
| shade_arch | **+0.19** | −3.29 | **+5.33** | +7.6 | +1.6 | +15.1 |
| shade_frieze (control) | +11.44 | +12.24 | +11.07 | +27.3 | +30.1 | +27.9 |

The viewer is warmer than Cycles by Δb* **+2.28 / +7.38 / +3.48**; the gap that remains is Cycles' own
(photo − Cycles = **+15.9 / +29.3 / +8.6**).

**The colour pipeline is neutral on this frame**: `sky` viewer vs Cycles **Δa* 0.03, Δb* 0.31**;
`shade_frieze` Δb* 0.80; `sunlit_pier` chroma Δb* 0.37. A LUT, exposure or colour-space error would
move all three. What does differ is LEVEL (viewer 1.07-1.33x brighter on stone) — the known parity gap.

**Where it enters, one flag at a time** (`shade_pier_r`): `?probe=0` **−10.94** (no change — the probe
and the sky-branch equirect are exonerated); `?lut=0` **−11.15** (hue unmoved — the LUT is exonerated);
`?probespec=1` −10.69; `?post=none` **−15.25** (the post chain is *warming* the shade by Δb* +4.3);
`?lighting=direct` **−16.02**, and at `shade_pier` −2.73 → **−24.88** (the direct sky fill is where the
violet lives; the bake already tames it). So the tint is in the SOURCE, and every viewer stage either
leaves it alone or reduces it. This is **QA-08-2 / QA-09-6**, opened in round 08 and never closed.

**Proposal.**
1. **Recommended — no viewer change.** Any chroma correction on the shaded stone departs from the
   frozen Phase 5 look, breaks the station-2 parity score, and needs a `docs/decisions.md` entry plus
   the user's approval. The viewer already beats its own reference here.
2. **The correct fix is upstream, owner LIGHTING / MATERIALS**: the NNE sky fill on the camera-facing
   rotunda face, then a rotunda lightmap re-bake. Acceptance: `shade_pier`, `shade_pier_r`,
   `shade_arch` at **b* ≥ +5**, **h_ab 40-80°**, **R−B ≥ +10**, with `shade_frieze` held at
   b* +11.4 ± 1.5 and the hero's shaded attic unmoved. Phase 5 asset change → approval first.
3. If a warmer web frame is wanted without a re-bake, the post chain is the only measured lever in the
   viewer today (Δb* +4.3). Still a look change, still an approval.

`gate9m` cannot be read with these boxes: 1170x2532 portrait against a 16:9 fixture, so every box lands
on different content (`shade_frieze` falls on open sky). A mobile number needs a 16:9 `?tier=mobile`
capture.

## Carried / not done

- Review r2 carries 3, 4, 5, 6 (the `min(cols-1)` guard, the NaN `vDirBlender`, `row_origin` matched as
  a substring, the wasted `c2` tap) were **not** in this brief and are untouched.
- `?lmscale=0` produced a frame byte-identical to base, i.e. that override does not reach the baked
  ARCH materials on this manifest. Reported, not chased.
