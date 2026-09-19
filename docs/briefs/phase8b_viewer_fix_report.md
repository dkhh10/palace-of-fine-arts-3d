# Phase 8b viewer fix round — report (branch `phase8b-viewer`, 2026-09-19)

Brief `docs/briefs/phase8b_viewer_fix.md` + item **d** added by the lead mid-round. Every table, every
`?` switch and the full sweeps: `web/README.md` → "Phase 8b fix round (QA 20 carries)". `npm test`
green (12 suites). No deploy, no Blender, nothing under `export/` touched; Chrome only through
`scripts/chrome_run.sh` with the bake queue `idle` and no Blender alive, re-checked before every run.

## a — `env_shrubs.glb` drawn in full at every station — FIXED (`1b5aa9c`, `9910ceb`)

**Cause.** The shrub LOD1 set had only the *fragment* half of its switch: the dissolve discards beyond
25/30 m, but a discard still pays the vertex shader and the rasterisation and `renderer.info` counts
the submitted triangle. The *CPU* half `loadFarTrees` has had since 6c round 2 — chunk, then hide any
batch whose every row is beyond the limit — was never written for the shrubs. `shrubLod: lod1 0` is a
red herring: that is `applyShrubLod`, an idle path reading a manifest block that does not exist.

**Measured, not inferred.** New `window.__pfaTrisByGroup()` (one frame, a counting hook per mesh,
checked against `renderer.info`; `screenshot.mjs --groups`). Before, at the hero: `WEB_glb_env_shrubs`
**2 024 352 tris in 50 draws** (25 meshes × the Reflector's second pass) of 6 361 468 — the whole set,
at every station including the aerial. `?shrubcull=0` reproduces gate9's counts to the unit.

**Fix.** Far-tree chunk-and-cull extracted to `buildDistanceCull()` and applied at the shrub set's own
distance + fade band + `CULL_MARGIN_M`. `?shrubcull=0` restores the old behaviour; `?shrubcull=<n>` is
the chunk budget (default **48**; 128 buys 0.4 M more tris at the hero for +53 draws at cam02 and is
no faster in two interleaved pairs).

Desktop 2560x1440, interleaved A/C/A/C in one session:

| st | ms before → after | tris before → after | Δ tris | draws | shrub tris |
|---|---|---|---|---|---|
| 1 | 30.90 → 29.30 | 6 361 468 → 4 952 588 | **−1 408 880** | 335 → **317** | 2 024 352 → 615 472 |
| 2 | 34.80 → 33.05 | 6 344 584 → 5 510 136 | −834 448 | 329 → 341 | → 1 189 904 |
| 3 | 39.35 → 36.50 | 7 111 092 → 6 030 448 | −1 080 644 | 351 → **343** | → 943 708 |
| 4 | 25.70 → 26.80 | 3 293 588 → 2 961 488 | −332 100 | 184 → 197 | 1 012 176 → 680 076 |
| 5 | 30.50 → 30.55 | 6 125 874 → 4 928 054 | −1 197 820 | 320 → **308** | → 826 532 |
| 6 | 33.75 → 32.25 | 6 729 552 → 4 705 200 | **−2 024 352** | 355 → **305** | → **0** |

`?tier=mobile`: −0.34 M to −2.02 M tris, draws −50 to +12, frame times at the 16.6 ms vsync floor
before and after. **The ms column is reported, not claimed** — an A-vs-A repeat moved up to 7.8 ms;
the triangle and draw counts are the claim. **Pixel parity:** cam02/03/04 differ by 0 px, cam01 7,
cam05 5, cam06 122 — and an A-vs-A repeat of cam06 differs by 134. Pure culling.

## b — `resident()` never counted the impostor atlases — FIXED, restated (`bc643cd`)

**Cause.** Textures were reached through eight `MeshStandardMaterial` slots only, so everything in a
custom uniform was billed by nothing (16 impostor atlases, translucency maps, the LUT). Opposite error
beside it: geometry billed per geometry OBJECT while chunks *share* their vertex buffers.

**Fix.** Reached by TYPE — every `uniforms` entry whose value `isTexture`, the post chain,
`scene.background`/`environment`, a widened slot list — with render-target textures collected first and
refused (143 hits at the hero, i.e. `tDiffuse`/`envMap` no longer double-billed). Geometry summed per
`BufferAttribute`. New keys: `texture_bytes_by_kind`, `render_target_textures_skipped`,
`geometry_bytes_before_dedup`, `info_memory`, `counted_vs_renderer`.

**Figure of record, hero:** geometry 261.5 → **114.5**, textures 1 157.6 → **1 255.6**, targets 443.8,
**total 1 862.9 → 1 814.2 MB (−48.7)**. The +98.0 MB of texture: impostor atlases **67.1** (never
counted), sheen/clearcoat/transmission slots **25.2**, `pfaTrnMap` **5.6**, LUT **0.07**. 67.1 MB =
16 × 4 194 304 texels × 1 B (ASTC 4x4), so band (4096x1024) and 2K octahedral (2048x2048) cost exactly
the same — `?impband=0` measures 1 814.2 too. `?tier=mobile`: **547.9 MB** (was 563.5); of its 236.4 MB
of texture the **sky equirect alone is 67.1 MB (28 %)** — worth a look in 6b. Item a's chunking costs
**0 MB**. README restated in three places; `__pfaInfo().resident` documented key by key.

## c — blue-violet shaded stone at cam02 — MEASURED, NOT A VIEWER FAULT, NOT IMPLEMENTED (`a78f29d`)

**The Phase 5 Cycles reference is MORE violet than the viewer at every shaded box.** CIELAB, boxes
`light_r16_measure.py BOXES["02"]`, ref `round13_02_…_cycles.png`, photo `ref_062`. Sheet:
`renders/web/960/p8b_c_cam02_shade_sheet.jpg`. b* (warm stone is positive):

| box | viewer | Cycles | photo |
|---|---|---|---|
| shade_pier | **−2.73** | −5.01 | **+10.89** |
| shade_pier_r | **−10.97** | −18.35 | **+10.99** |
| shade_arch | **+0.19** | −3.29 | **+5.33** |
| shade_frieze (control) | +11.44 | +12.24 | +11.07 |

Viewer warmer than Cycles by Δb* +2.28 / +7.38 / +3.48; the remaining gap is Cycles' own
(photo − Cycles = +15.9 / +29.3 / +8.6). **Pipeline verified neutral on the same frame**: `sky` Δa*
0.03 / Δb* 0.31, `shade_frieze` Δb* 0.80, `sunlit_pier` chroma Δb* 0.37. What differs is LEVEL (viewer
1.07-1.33x brighter on stone) — the known parity gap, not a tint.

**Flag sweep** (`shade_pier_r` b*): `?probe=0` **−10.94** (probe and sky-branch equirect exonerated);
`?lut=0` **−11.15**, hue unmoved (LUT exonerated); `?probespec=1` −10.69; `?post=none` **−15.25** (the
post chain *warms* the shade by Δb* +4.3); `?lighting=direct` −16.02 and at `shade_pier` −2.73 →
**−24.88** (the direct sky fill is where the violet lives; the bake already tames it). This is
**QA-08-2 / QA-09-6**, opened in round 08 and never closed.

**Proposal.** (1) *Recommended: no viewer change* — any chroma correction departs from the frozen
Phase 5 look, breaks the station-2 parity score and needs approval; the viewer already beats its own
reference. (2) *The correct fix is upstream, owner LIGHTING/MATERIALS*: the NNE sky fill on the
camera-facing face + a rotunda lightmap re-bake; acceptance **b* ≥ +5, h_ab 40-80°, R−B ≥ +10** on the
three boxes with `shade_frieze` held at +11.4 ± 1.5 and the hero's shaded attic unmoved — a Phase 5
asset change, so `docs/decisions.md` + the user's approval first. (3) If a warmer web frame is wanted
without a re-bake, the post chain is the only measured lever (Δb* +4.3); still a look change, still an
approval. `gate9m` cannot be read with these boxes (1170x2532 portrait vs a 16:9 fixture:
`shade_frieze` lands on open sky); a mobile number needs a 16:9 `?tier=mobile` capture.

## d — translucency map wrap follows the albedo's glTF sampler (`a610c6b`, Phase 8e prep)

`applyFoliageTextures` hard-coded `ClampToEdge` on the translucency FACTOR map while the albedo beside
it already took the glTF sampler. Both use the same leaf-card UVs, so 8e's k = 2.0 (willow 1.5) UV
scale + REPEAT samplers would tile the albedo and smear the trn map's edge texel. Now copied from the
albedo texture — neither mode hard-coded — recorded in `trnWrap` and named in the boot log. Carried to
the LAZY roots too (`applyFoliageAlbedo` already re-wrapped the shared albedo per root and left the trn
map on env.glb's value; it now re-wraps both).

**EXPORT ACTION for 8e:** both maps are **one texture object shared by every root** using that material
name, so if 8e patches `env_trees.glb` to REPEAT and leaves the same material name on `env.glb` at
clamp, the last root loaded wins for both. The viewer now says so in the boot log rather than
mis-serving silently. **Patch the samplers of every glb carrying a leaf material, or give the re-scaled
cards their own material name.**

**Pixel-neutral, verified:** six stations pre-d vs post-d differ by 61-233 px of 2 073 600, and a
SAME-BUILD control of the same six differs by 61-228 with cam02/03/04 identical between the two
comparisons. Boot log: `translucency wrap taken from the glb albedo sampler(s): 1001/1001` (clamp) on
all 8 leaf materials. Test: `foliage_lazy_test.mjs` §8.

## Carried / not done

- Review r2 carries 3, 4, 5, 6 (the `min(cols-1)` guard, the NaN `vDirBlender`, `row_origin` matched as
  a substring, the wasted `c2` tap) were not in this brief and are untouched.
- `?lmscale=0` produced a frame byte-identical to base — that override does not reach the baked ARCH
  materials on this manifest. Reported, not chased; the `lighting=direct` row makes the point instead.
- Full-resolution A/B and sweep frames are gitignored as regenerable (`renders/web/p8b_*.png`); the
  perf JSONs and the 960 px composite are committed.
