# phase6-viewer r3 (33903b8) — MERGE WITH FIXES

`git merge-tree main 33903b8`: **clean, 0 conflicts**; only `web/**` and `renders/web/**` are touched. `npm test` in the worktree:
**exit 0**, including the 7 walk-up tests (set chosen, 254/254 joined, 127 placements via `same_as`, `draw_within_m` 15, all 254 lit
from `far_mesh.lighting`, **missing glb -> `far_mesh`, `walkupFellBack=true`**, `?walkupmesh=0` -> LOD2 at 12 m). The atlas enclosure term (impostors.js:173-196) is bounded and edge-safe — `frameUv` clamps `f` to [0,1] and
samples texel centres inside the gutter, the taps are `clamp(vQuadUv±r,0,1)`, the factor is `1 - str·smoothstep(0.25,0.95,e)`,
`str∈[0,1]`, `r∈[0.002,0.4]`: no NaN, no division; at `?impint=0` the branch is not entered and no program differs (true no-op),
and it patches the impostor fragment shader only. The mesh sun-path term is likewise bounded (`|u| ≤ 1`, `sqrt(max(·,0))`, clamped)
on the shared, assigned `pfaSunDir` (foliage.js:553/360). `?shrubcov=` is off at both call sites (`covK=0 -> f=1`) and cannot leak.
**Partition** (walkup on): the LOD2 `far_mesh` glb is never fetched, so d ≤ 15 m = LOD1 mesh, the 15 m dither band is the exact
complement (mesh keeps `hash ≤ 1-t`, impostor `hash > 1-t`, same `farDist` both sides — foliageLazy.js:554/582/625), d > 15 m =
impostor; with `?walkupmesh=0`, a 404 or a failed join it is 12 m / impostor. No band draws two crowns, none draws zero. Frame ms
(29.7/33.5/33.2/21.3/31.5/34.0) and the round-15 deltas, resident 1 931.4 MB (and the 1 800.6 MB correction, both decimal MB),
walk clamp 24 probes / lowest **-0.750** / 0 below -1.20, and the bare-URL defaults (cardEnv 0.3, shrubLod1 envScale 0.3, impint 0.90/0.015, walk-up at 15 m, 0 page errors) all reproduce from the committed sidecars. No new tracked file over 5 MB.

1. **fix now** — `web/src/foliageLazy.js:716-731` + `web/src/foliage.js:627`: the LOD1 shrub env lobe is applied **twice**.
   `loadShrubLod1` scales `envMapIntensity`/`sheenColor` by 0.3 over its 25 materials, then calls `applyFoliage` without
   `cardEnv`, which defaults to `CARD_ENV` and scales the same 25 `MAT_shrub*/MAT_reeds` clones (names survive the clone,
   lightmaps.js:549) by 0.3 again -> **0.09**. The round16c log shows both passes (`environment term x0.3 on 25`, then a third
   `foliage interior: 25 material(s)`), so the LOD1 set ships at 3x less environment than the LOD2 cards it switches with — the
   exact discontinuity the README says the shared constant prevents, and station 3's 1.32x was measured through it. Fix: pass
   `cardEnv: 1` in that `applyFoliage` call (or guard the block on `mat.userData.pfaEnvScaled`), then re-read boxes 01/03.
2. **fix now** — `web/README.md:650-652`: the "MAE … delta vs round16b" row is not reproducible from any committed sidecar.
   `round16c_pairs.json` vs `round16b_pairs.json` (the only MAE source, gate1_sheets.py:108) gives
   **-0.25 / -1.73 / -0.66 / 0.00 / +0.28 / -0.29**, not -0.24/-1.00/-0.84/0.00/-1.30/-0.91; neither RMS nor the post-off set
   matches. Station 5 is **worse**, so "every station's parity improves or holds" is false. Recompute the row and restate 05.
3. **fix now** — the crown numbers (0.394 / 1.722 / 1.705) and the seven shrub levels (1.36/1.10/1.12/1.06/1.02/0.88/1.32) exist
   **only** in `web/README.md`: `r3_boxes.py` prints to stdout and the full-res `round16c_cam0N.png` are gitignored, so nothing
   committed reproduces them. Commit that output as `renders/web/round16c_r3boxes.txt`.
4. **carry** — `foliageLazy.js:538`: with the walk-up set on, `?fartreemesh=` is silently ignored; document it or honour it.
5. **carry** — `walkupDist()` (foliageLazy.js:57-62) is unclamped: `?walkupmesh=-5` kills the mesh, a huge value submits all 254
   rows. Clamp to [0, 60] like the other switches.
6. **carry** — `web/tools/r3_crown_tile.py:17` hardcodes the main checkout; use the `PFA_MAIN_ROOT` fallback its siblings use.
7. **carry** — `renders/web/round16c_gate.png` (2.4 MB, 1456x1104) is tracked beside its own 960 px jpg; drop the PNG.
