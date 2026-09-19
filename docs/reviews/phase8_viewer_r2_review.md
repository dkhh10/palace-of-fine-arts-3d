# phase8-viewer r2 (9b829a6) — MERGE WITH FIXES

## Verified — diff f0ad577...9b829a6, against docs/briefs/phase8b_band_atlas.md and the shipped sidecar. No Blender/Chrome/edits.
- **Azimuth.** `cth = a0.x*d.x + a0.y*d.y`, `sth = a0.y*d.x - a0.x*d.y`, `atan(sth,cth)` with `a0 = (1,0)` IS `atan2(-d.y, d.x)`
  — the shipped `impostors.band.frame_lookup` verbatim. Cardinals re-derived independently: (1,0,0)→0, −Y→3, −X→6, +Y→9;
  the wrap carries −1° to col 11 f=0.967 and back into col 0. The compass fallback (180 → (1,0)) lands on the same heading.
- **Elevation.** Nearest of 0/20/40 puts every negative elevation on row 0 (row 1 needs > +10°); the bake's stations
  (−0.5/−2.3/−3.5/−9/−18) are pinned in the test. **UV/pad:** 12×341 = 4092, 3×341 = 1023; max u texel 4084 (+1 for the
  premul tap, inside the 8 px gutter), max py 1015 — the 4 px right and 1 px top pad are unreachable at either `row_origin`.
- **Sampler.** impostors.js:834-839 NoColorSpace, flipY false, ClampToEdge, Linear/Linear, `generateMipmaps:false`,
  `anisotropy:1`; nothing else in web/src touches an impostor texture (pbr/detail/foliageLazy set 8 on their own).
- **Scope.** The band swaps the albedo URL only; `p.normalDepth` is still the 1K octahedral, loaded and never sampled;
  `lin *= vPfaIrr` appears exactly once, in the shared tail both paths reach (interior term and floor likewise).
- **`impband=0`.** `PFA_IMP_BAND` undefined, `atlasWH = (atlasPx, atlasPx)`, `rowFromTop = 0`, `mix(x,y,0.0)` is exactly `x`
  — the octahedral/2K path is bit-identical (test 6). `impTier` now counts `albedo2k` and `band.albedo` (r1 carry 4); the
  boot log reads "impostor atlases tier 1" and the pass runs at tier 2 (env), so no band byte lands before tier 1.
- All seven r1 findings addressed. Both impostor tests pass at 9b829a6, the band one wired into `npm test`; images 960 px
  wide, largest added file 224 KB, no binary > 5 MB, 24 stale sweep sidecars deleted (r1 carry 7).

## Findings
1. **fix now** — manifest.js:1113-1121 drops the band's own `range` / `range_same_as_octahedral` and impostors.js:731 keeps
   `range: p.range` from the octahedral block. Equal today, but the bake report names `PFA_BAND_RANGE=band` as the willow
   highlight lever; that re-bake would decode all 16 atlases at the wrong range in silence. Read `e.range`, or refuse the
   block when `range_same_as_octahedral !== true`.
2. **fix now (doc)** — README:992 "Resident is identical at 3553.3 MB" is a **reporting double-count, not a doubling**:
   `web/tools/p8_perf_table.py:17-19` sums every key ending in `_bytes`, which includes `total_bytes` itself, then divides by
   1048576. On p9b_perfband_perf.json: 261.2 + 0.3 + 1157.6 + 443.8 + **1862.9** = 3725.8e6 / 1048576 = 3553.3. The real
   resident is `total_bytes` = **1862.9 MB** at all six stations, byte-identical to p9b_perf2k — the "identical" claim stands,
   the number does not. Same inflation at README:1044-1049 (3550.1) vs the 1861.3 MB README:662 quotes from that same gate7
   capture. Fix `resident_mb()` to `total_bytes / 1e6`; restate 1862.9.
3. **carry** — impostors.js:262 `float i0 = floor( cf );` lacks the `min( cols-1.0 )` guard JS `bandSelect` has as `% columns`.
   In float32 any `cf` in [−4.8e-7, 0) becomes exactly 12.0 after `+cols` → column 12 → u > 1 → the zero right pad at weight
   1−f ≈ 1, i.e. the card blanks that frame. ~1 tree-frame in 1e7, invisible to the JS test. `i0 = min(i0, cols-1.0);`
4. **carry** — a NaN `vDirBlender` (camera exactly at a billboard centre) gives NaN uv; the fetch is hardware-clamped, no
   out-of-range access, row stays 0. Same exposure as the octahedral `normalize(0)`, so not a regression.
5. **carry** — manifest.js:1129 tests `row_origin` with `/top/` as a SUBSTRING ("bottom_to_top" would flip every row: match
   the token); same block accepts `rows` > 4, which `pfaBandEl` (a vec4) and the shader loop truncate silently.
6. **carry** — the band branch still fetches `c2` (= `c1`) at weight 0: 4 wasted taps per fragment in the premul path. And
   README:976-992's table/perf line name no script — they are `export/p8_atlas_probe.py viewer` and `p8_perf_table.py`.
