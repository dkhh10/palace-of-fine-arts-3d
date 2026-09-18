# QA round 18b — Phase **6b, the Gate 5 fix round** (the closing 6b round). Verdict: **6b DONE WITH RESIDUALS**

Main @ 2aea7b2 against `https://pfa-walkthrough.3d-render-blender-3rd-attempt-building.workers.dev`. Inputs: desktop `gate5b_*` (deploy 3), mobile `gate5cm_*` (deploy 4, viewer
13a673c = the canvas fix), the pre-fix mobile `gate5bm_*`, round 18's `gate5*`, the deploy logs. No Blender, no Chrome; curl for the live checks. Tools
`scripts/qa_r18b_{probe,live,tiles,gate}.py` (the probe imports qa_r18 -> r17 -> r16 -> r13 unchanged). Sheet `renders/web/gate5b_gate.png`.

## 1. Verdict against the 6b definition of done (CLAUDE.md)
| conjunct | result |
|---|---|
| initial payload <= 50 MB on the URL | **PASS** — desktop **46 808 904 B = 46.81 MB (44.64 MiB)**, 320 requests, first frame 8.77 s |
| progressive loading, meshopt + KTX2, every file <= 25 MiB | **PASS** — 3 tiers, 0 failures, 182+4 upgrades landed, 0 lowres left, 0 of 622 over 25 MiB |
| **mobile fallback loads and walks** | **PASS** — all 7 `m_*.glb` serve 200; **142-180 draws / 1.51-1.91 M tris** per station; **0 page errors, 0 404s** |
| mobile resident vs the 700 MB target | **PASS — 499.7 MB** (tex 204.8 all-ETC2, geo 57.3, render targets 237.4) = 0.71x |
| desktop unchanged by the fix | **PASS** — MAE vs round-18 `gate5` **<= 0.001/255** at every station; resident **1 861.3 MB**, identical |
| loading screen with progress (QA 18 finding 2) | **PASS** — the tier-0 bar reads **95.2 %** desktop / **98.0 %** mobile at tier 0 (was 161 % / 7 %) |
| Safari on macOS; iPhone 16 Pro walk | **STILL NOT EVIDENCED** — `renders/web/user/` does not exist; both owed (§6) |

No hole, no 404, no desktop regression, no payload overrun, so 6b is done — **with residuals**: the mobile water reflection is empty (§4.1) and the portrait frame exposes
far-field defects the landscape stations never showed (§4.2). The fix round is spent: these are named with owners for the next phase.

## 2. The round-18 blocker is closed, verified live
`manifest.json` now names **149 rows with tier `mobile`** and **0** of the mobile plan's 341 paths is missing from it (was 7). `verify_publish`'s 1 051 = 706 + 341 rows + both
manifests + both relay-status files, and it checks the **publish directory**, not the URL — so `qa_r18b_live.py` curled the URL: the **7 `groups/m_*.glb` return 200,
`model/gltf-binary`, `max-age=31536000, immutable`, byte-exact against the plan** (full GETs; HEAD carries no `content-length` here), and 39 further paths (20 per manifest by
stride) are 200 with the right class — bake assets immutable, plan JSONs `max-age=60`, `/` `max-age=300`. Each capture's only response >= 400 is `/favicon.ico`; 0 over 25 MiB.
Mobile loads 4 tier-0 and 3 tier-2 groups, 7 of 7, with 16 lightmaps, 87 patched materials, 0 failures and 110 ETC2 substitutions.

## 3. Mobile: the six stations at 100 %, and the first mobile scores
36 tiles (2 x 3 per station, 585x844, no downscale; `qa_r18b_tiles.py`). **Every station draws the whole scene** — rotunda, both colonnades, attic ornament, capitals, urns,
weeping figures, coffered vault, ground, paving, shrubs, reed and tree cards, impostors, backdrop city, water — with **no hole, no missing group, no unbound lightmap, no
z-fighting, no filled opening, no placeholder, no sky banding.** The frame renders at 832x1801 (the 1.5 Mpx cap, dpr 0.71) upscaled to the 1170x2532 page, so mobile is softer by
construction and softness is not scored; and it keeps the desktop **horizontal** FOV while tripling the vertical (125.6° vs 53.7°), so rows 1 and 3 of every station are scene the
landscape stations never showed. Centre band = mobile rows 936-1595, which *are* the desktop frame, resampled to 1920x1080 against `gate5b_cam0N`:

| station | 01 hero | 02 lagoon NE | 03 colonnade | 04 ceiling | 05 south lawn | 06 aerial |
|---|---|---|---|---|---|---|
| mobile/desktop luma, centre band | **1.140x** | 1.001x | 0.980x | 1.000x | **1.105x** | 1.003x |
| MAE /255, centre band | **23.5** | 15.2 | 9.6 | 5.2 | **23.9** | 5.2 |
| desktop score (carried, QA 17/18) | 3.78 | 3.25 | 2.63 | 2.88 | 2.94 | 2.83 |
| **mobile score (first scoring)** | **2.9** | **3.0** | **2.3** | **2.7** | **2.5** | **2.4** |

Four stations are within 2 % of the desktop frame; the two that are not are the two water stations, and they are *brighter* — the missing reflection puts sky where the building
should be. Deductions: the reflection at 01 and 05, near-field smear and faceted bases at 03, the portrait far-field at 06. Mobile's conjunct is "loads and walks", not 6a's 2.5
desktop floor, so 03 and 06 are not gate failures.

## 4. Mobile residuals, by owner
1. **The mobile water reflects nothing (VIEWER).** `reflectionSet` is `{excluded: 169, kept: 1, all: true}` against desktop's `{excluded: 36, orn: 36, kept: 134}`: the pass
   renders one object while the readout claims `reflSet: "all"`. One cause, three symptoms — the hero lagoon is a bare sky gradient with no rotunda, colonnade or ripple streaks
   (`cam01_r2c1/r2c2/r3c1`; row std 7-15 near the shore and 0.45 far out, against desktop's 33-56 at ptp ~200); 05's whole lower half is flat (`cam05_r3c1/r3c2`); and at 06 the
   distant bay, where reflection dominates at grazing incidence, is a **near-black band** on the horizon (`cam06_r1c1/r1c2`, min luma 7.7; no desktop row is below 48). 6a's
   "water reflects the rotunda at the hero" holds on desktop, not on mobile.
2. **Carried and amplified, not new (ENV, EXPORT/MATERIALS).** `cam06_r2c1/r2c2/r3c1/r3c2`: the aerial trees are flat lavender-grey or black impostor silhouettes and the far
   terrain and backdrop parcels show decimation facets and hard colour banding, mostly in the mobile-only rows. `cam03_r1c2, r2c2, r3c2`: the blurred, vertically banded column
   concrete QA 17 and 18 both named is worse on mobile (half-res maps plus the 0.71 scale) and the base at ~0.5 m shows the `-si 0.5` decimation as facets. No missing geometry.
   Foliage is cards only by design — `foliage.meshDist` 0 (desktop 40), `shrubLod` `dist 0, lod1 0, lod2 0`, the groups ship pre-decimated — so shrubs and reeds are hard-edged
   alpha cards at every distance (`cam02_r2c1, r3c1, r3c2`), which is why 02 loses 0.25.
3. **Found and fixed inside this round (VIEWER; closed).** `gate5bm` painted the canvas **832x1801 in the top-left of the 1170x2532 page** at all six stations — 50.6 % of it,
   the rest background `#0B0D10`; the aspect was right, so only the canvas size was wrong. Viewer a7eee7e (merged 13a673c) sets full CSS size and caps the pixel ratio instead,
   and `gate5cm` fills the page. Every tile above is from `gate5cm`.
4. **The export still does not list 302 by-reference paths (EXPORT; carried, harmless today).** Deploys 3 and 4 warn that the mobile plan resolves 302 paths from material keys,
   not `files[]`. They publish because the union walks the desktop plan and the capture proves 0 404s — but `verify_publish` cannot cover a path no `files[]` names, so the
   assertion that closed this blocker does not cover those 302.

## 5. Desktop: no regression, payload, bar, perf, memory
**Regression.** `gate5b` vs round-18 `gate5`, same URL: luma **1.0000x at all six stations**, whole-frame **MAE 0.0000-0.0010/255**, and 0.000-0.015 % of pixels moving at all,
in the foliage-edge and water bands round 18 attributed to alpha-test and reflection sampling; 02 and 04 are bit-identical and MAE against the Cycles references is unchanged to
two decimals. **The desktop scores carry again: 01 3.78 · 02 3.25 · 03 2.63 · 04 2.88 · 05 2.94 · 06 2.83**; no desktop tile was re-reviewed, they are the pixels round 18
reviewed at 100 %.

| | before frame 1 | first frame | tier 0 | tier 1 | tier 2 | all tiers | total |
|---|---|---|---|---|---|---|---|
| desktop (gate5b) | **46 808 904 B = 46.81 MB** | 8.77 s | 47.0 MB / 8.26 s | 456.3 MB / 39.05 s | 69.6 MB / 7.68 s | 56.07 s | 581.1 MB |
| mobile (gate5cm) | **46 738 628 B = 46.74 MB (44.57 MiB)** | 8.57 s | 46.6 MB / 7.95 s | 3.8 MB / 0.43 s | 11.1 MB / 2.49 s | 11.31 s | 61.7 MB |

Desktop is 5 404 B lighter than round 18, 3.19 MB inside the conjunct. **The mobile first look is only 0.07 MB lighter than desktop**: halved textures are not what dominates it
— 15.65 MB sky HDR + 7.42 MB LUT cube + 14.58 MB glb are identical in both, and mobile ktx2 traffic is 22.9 MB against desktop's 531.7 MB, so the fallback saves 519 MB of
*total* traffic and nothing on the first look. Both: 0 oversize, 0 failures, 0 lowres left, 0 deferred lightmaps. **Loading bar (finding 2, fixed):** `tier0_planned_bytes` vs
bytes fetched at tier 0 = desktop 49 317 469 / 46 953 057, mobile 47 555 413 / 46 621 188; declared-vs-loaded -2.6 % and +0.3 %, against round 18's 160.9 % and 7.4 % — inside
5 % on both, the 4.8 % under-fill left being the export's estimate. **Perf, 2560x1440 medians (ms)**, right after the capture, so the drift caveat of decisions.md 2026-09-18
stands and no re-measure was made:

| station | 01 | 02 | 03 | 04 | 05 | 06 |
|---|---|---|---|---|---|---|
| gate5b | 31.2 | 35.6 | 38.9 | 25.5 | 34.5 | 36.5 |
| gate5 / gate5cold | 31.7 / 30.8 | 38.0 / 37.2 | 37.7 / 37.9 | 25.1 / 24.3 | 34.2 / 33.2 | 34.2 / 34.3 |
| delta vs cold | +0.4 | **-1.6** | +1.0 | +1.2 | +1.3 | +2.2 |

Every station is inside ±3 ms of the cold pass and 02 is faster, so the fix costs nothing; draws (184-355), triangles (2.74-5.98 M), programs (141-143) and `gpu_cost_ms`
(1.1-3.6) are unchanged and `max/p95` stays 19-21x (the single-outlier signature). Carried: the hero runs **32.1 fps** at 1440p against 6a's 45, and resident is byte-identical
to round 18 at **1 861.3 MB** = 1.55x the 1 200 MB Gate 1 budget. Of mobile's 499.7 MB, 237.4 MB is render targets, so geometry and textures cost 262 MB: real headroom.

## 6. Name sweep, and the evidence owed
**Name sweep** (`qa_r18b_probe names`, CLAUDE.md's pattern with qa_r16's object-shaped filter, over both manifests including the 149 new rows): **0 hits in either** (706 and 341
rows). As in round 18 it restates round 17's gate1/gate3 object sweep rather than replacing it; its named exceptions stand, 0 new. **Owed, not waited for:** the user's **macOS
Safari** hero screenshot — every 6b capture is HeadlessChrome/152, so that conjunct has no evidence at all and cannot be claimed — and the **iPhone 16 Pro** 30 s walk, takeable
now that the phone would see the scene of §3.
