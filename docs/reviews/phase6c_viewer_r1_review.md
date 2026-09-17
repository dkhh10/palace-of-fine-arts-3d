# phase6-viewer 6c round 1 — SEND BACK (one shader line; everything else is fix-now / carry)

Range reviewed: `main...063c100` (9e1560c..063c100), pinned. Verified good: every `?` default in the README's
switch table is the shipped one — `round16_bareurl.json` (bare URL `?station=1&size=1280x720&hud=0`) reports
`normalBlend 0.5, cardNormalBlend 0, meshDist 40, fadeBand 5, trnScale 1, trnShrubs false, msaa true,
shrubLod 30, impmod chroma, E_bake 100.98/79.14/213.74, 0 far + 18 near`; the crown bend is per flood-filled
cluster per geometry (foliage.js:83-160), i.e. per tree and not per gltfpack-merged primitive; `alphaToCoverage`
is gated on a multisampled target (main.js:608) and the manifest MASK cutoffs are untouched; `irradianceRatio`
(foliage.js:497) cannot divide by zero or return a non-finite ratio, and `farTreeIrradiance` refuses to guess
(0/127 today); the only code change after the round-16 capture (d9b121d) is a note string, so the screenshots
are valid for the pixels; frame numbers cited (cam01 133.1, MAE 26.75) are in `round16_pairs.json`.

1. **BLOCKER — the dissolve is not complementary.** `foliage.js:235` and `impostors.js:113` both discard on
   `pfaHash(gl_FragCoord.xy) > vPfaFade`, but the mesh's fade is `1-t` (foliage.js:227) and the impostor's is
   `t` (impostors.js:59). Both therefore KEEP the same set `{hash <= min(t,1-t)}`: at mid-crossfade ~50 % of the
   crown is drawn twice and ~50 % shows background through the tree. `renders/web/960/6c_lod_switch.png`'s
   middle panel is visibly see-through, and the README's "exact complements … no tree is ever drawn twice or
   not at all" is false. Fix: impostor test becomes `... && pfaHash( gl_FragCoord.xy ) <= 1.0 - vPfaFade`.
2. **Fix now — the trunk switches at a different distance from its crown.** Bark materials get the same fade
   patch, but their `pfaCrown` is the BARK cluster's own centre, while the impostor's `iSwitch` is the crown
   centre (impostors.js:277 comment says the crown centre is used "never the billboard centre" — it is not used
   for the bark). A trunk centre several metres below the crown crosses 40 m at a different frame. Fix: pair the
   bark cluster to its crown (the `PAIR_MAX_M` join already exists) and write the crown centre into `pfaCrown`.
3. **Fix now — NaN switches erase the canopy.** `?treefade=` non-numeric → `Math.max(NaN,1e-3)` = NaN
   (foliage.js:210) → `smoothstep` NaN → every foliage fragment discards; `?leafnormal=`/`?cardnormal=` are
   unclamped and NaN-unguarded (main.js:112-113). Fix: `Number.isFinite` fallbacks to the defaults, clamp 0..1.
4. **Fix now — an unmatched near tree vanishes past the switch.** `foliage.js:556/567` silently skip a unit with
   no `SPECIES_OF` entry or no prototype, but the mesh fade is a per-MATERIAL uniform, so that tree still
   dissolves at 40 m with no impostor behind it (18/18 match today, so nothing shows). Fix: when any unit of a
   material fails to match, leave that material's `pfaSwitchDist` at Infinity and say so in the note.
5. **Fix now — the impostor summary reports the wrong atlas.** `impostors.js:331` prints `impostors.framePx /
   atlasPx` (85 px / 1024 px) even when `use2k` drew the 2048/170 px variant, which is what the sidecar shows;
   and `__pfaInfo().impostors` (main.js:1232) carries neither `atlas2k`, `nearInstances` nor `modulated`, so the
   commit's "the info block records every 6c default" does not hold for those three. Fix: print `geom.*` and add
   the three fields.
6. **Carry — 2K byte accounting.** `impostors.js:298` does `bytes += (p.bytes2k||0) - (p.bytes||0)`, so a
   manifest with no declared 2K byte count subtracts the 1K figure instead of keeping it.
7. **Carry — the 6c box numbers cannot be re-derived.** The cam02 `60 520 700 980` table, the `700 660 1240 950`
   hp9/mid/std table and the cam01 shore box are in no committed sidecar; `foliage_boxes.py` prints the first
   table's columns (rgb/lum/hue/sat/G>R, plus p10) but nothing writes its output, the full-res PNGs are
   gitignored, and no committed tool produces hp9/mid/std at all. Save the tool output beside the capture.
8. **Carry — clustering and caching edges.** The 6 m 8-neighbour flood fill merges two crowns whose canopies
   touch within one cell, and `prepareGeometry` caches per geometry uuid, so a geometry first seen through a
   cards-only mesh keeps bend 0 for a later leaf mesh; `report.bent` counts meshes, not geometries. Nothing
   asserts clusters == trees (18 found vs 20 declared `tree_near` rests on the README alone).
9. **Carry — `applyShrubLod` sentinel.** `dist === 30` is used as "the caller did not ask" (foliage.js:441), so an
   explicit `?shrublod=30` cannot be overridden by the manifest and any other explicit value silently wins over
   `raw.shrub_lod.dist_m`. Also `once()` throws inside `onBeforeCompile`, i.e. at first render, where it kills the
   frame instead of surfacing as `__pfaError` the way the r7b guards do.
