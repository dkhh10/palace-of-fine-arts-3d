# QA round 18 — Phase **6b, Gate 5: the staging deployment**. Verdict: **ONE FIX ROUND** (one blocker, on mobile)

Scored on main @ 66ae3b1 against `https://pfa-walkthrough.3d-render-blender-3rd-attempt-building.workers.dev` (deploy 2; it differs from the captured
deploy 1 only in `_headers`, re-verified live in §4). Inputs: the lead's `gate5` capture (1920x1080, `tiers=all`), `gate5_net.json`, `gate5_perf.json`
(2560x1440), the mobile capture + `gate5m_net.json` (`?tier=mobile`), `gate5_tier0_net.json` (the LOCAL dev-server pass), the pop pair, the deploy logs,
the export report. No Blender, no Chrome; curl for live headers only. Tools `scripts/qa_r18_{probe,tiles,gate}.py` (the probe imports qa_r17 -> r16 -> r15
-> r13 unchanged). Composite `renders/web/gate5_gate.png`.

## 1. Verdict against the 6b definition of done (CLAUDE.md)

| conjunct | result |
|---|---|
| initial payload <= 50 MB on the URL | **PASS** — **46 814 308 B = 46.81 MB (44.65 MiB)** before the first frame, 320 requests, 8.11 s |
| progressive loading, meshopt + KTX2; every file <= 25 MiB | **PASS** — 3 tiers, 0 failures, 182+4 upgrades all landed, 0 lowres left; 0 of 622 over 25 MiB |
| desktop parity with round16c; no new tile defect (36 at 100 %) | **PASS** — luma 0.998-1.002x, MAE 0.03-1.37/255, **0 of 25 boxes > 3 %**; nothing new |
| perf and memory unchanged | **PASS with a caveat** — §3; the pass is not throttled, no cold re-measure needed for the gate |
| **mobile fallback loads and walks** | **FAIL — BLOCKER.** The mobile tier 404s on **all 7 of its group glbs**: no building at any station |
| Safari on macOS (user screenshot); iPhone 16 Pro walk recording | **NOT EVIDENCED** — `renders/web/user/` does not exist; both owed (§5) |

6b stops at deployment plus **one clean** QA round. This one is not clean: the mobile fallback, named explicitly in the definition of done, does not render
the building on the URL. Everything else passes, and the fix is 14.6 MB of files that already exist on disk.

## 2. Blocker 1 — the mobile variant has no geometry on the URL (owner: EXPORT, with DEPLOY)

`gate5m_cam.json` carries **18 page errors**, all 404s, and the mobile scene draws **49 calls / 548 triangles at every one of the six stations** (desktop
329-355 / 2.7-6.0 M): sky, water and far-tree impostors only — no rotunda, colonnade, ornament or ground (row 3 of the gate sheet).

| files | tier | bytes | on disk | in `manifest_mobile.files` | in `manifest.json` (the deploy plan) | live |
|---|---|---|---|---|---|---|
| `m_arch_t0` / `m_orn_t0` / `m_env_t0` / `m_ground_t0` | 0 | 2 328 940 / 1 134 744 / 2 116 728 / 1 957 112 | yes | yes | **no** | **404** |
| `m_arch_t2` / `m_orn_t2` / `m_env_t2` | 2 | 80 200 / 175 144 / 6 778 276 | yes | yes | **no** | **404** |

Root cause, from the deploy log: *"tiers.deploy_from says the desktop plan is the whole deploy set; the mobile manifest is published as a file, not
walked"* — and `deploy.sh` is right to trust that contract, because the export report asserts it ("Build the publish directory from `manifest.json` only —
every path both variants fetch is named here"). It holds for the 142 `mobile_lo` textures and **fails for the 7 mobile group glbs**, the only mobile-only
paths missing from the desktop `files` table: **14 571 144 B**, the entire difference between the plans. *Fix:* add them to `manifest.json.files` (export,
primary — the contract is the export's), or publish the union of both plans and assert every path resolves (deploy); the re-capture is one mobile run.
Unjudgeable until then: mobile resident vs the 700 MB target (export estimate 306 MB), the 30 fps target, the iPhone walk, the mobile scores — and the
mobile payload below (23.88 MB) is **not** a pass, it is what a scene with no building costs.

**Finding 2, not a blocker (owner VIEWER):** `viewer_tiers.tier0_planned_bytes` disagrees with both `tiers.bytes.0` and the bytes fetched, in opposite
directions — desktop **29 183 503** planned vs 48 214 316 declared vs **46 943 046** fetched (the bar reads 100 % at ~62 % of the download); mobile
**325 775 019** vs 46 461 150 vs 24 140 193 (~7 % when done: the mobile material sets name the full-resolution keys the viewer redirects, as the export
report warns). "Loading screen with progress" is a 6a conjunct and the progress shown on the URL is wrong in both variants.

## 3. Desktop: parity, tiles, payload, perf, memory

**Parity** (`qa_r18_probe parity`, full frames, gate5 vs round16c):

| station | 01 | 02 | 03 | 04 | 05 | 06 |
|---|---|---|---|---|---|---|
| luma ratio | 0.998x | 0.999x | 0.999x | 1.000x | 0.998x | 1.002x |
| MAE /255 | 0.94 | 1.16 | 0.23 | **0.03** | 1.37 | 1.05 |

MAE against the Cycles references moves by at most 0.10 (24.80/24.75, 18.58/18.68, 34.76/34.80, 13.08/13.08, 21.39/21.32, 18.15/18.14).
`qa_r18_probe boxes` re-runs every round-13/15/16 box (11 architecture + 14 foliage): largest move **0.987x** (cam02's fill-tree crown), **0 of 25** over
3 %. The streamed build after tier 2 **is** the 6c build; the residual difference is foliage-edge and reflection pixels (p99 |d| 19-26/255 at stations 1,
2, 5, 6 against 0.9 at station 4), i.e. alpha-test and reflection sampling, not a tier or a texture. **Scores therefore carry from round 17 unchanged**
rather than being re-derived from an identical image: **01 3.78 · 02 3.25 · 03 2.63 · 04 2.88 · 05 2.94 · 06 2.83** — none below 2.5, none outside 0.5 of
Phase 5, so the 6a parity conjunct holds on the deployed build. **Mobile: no scores — the building is not in the frames.**

**Tiles (36, 3 x 2 at 100 %, each beside the same crop of round16c).** **No defect is new to the deployment**: no unbound lightmap, hot-swap seam, texture
that never sharpened, wrong tier order, filled opening or z-fighting. Every 6c residual reproduces — cam01 r2c1 flat olive N-colonnade backdrop and the
pale crown halo, r2c2/r2c3 flat card shrubs and the cooler reflection; cam02 r2c1 flat blades and orange reeds, r2c3 flat cream backdrop planes; cam03
r1c3/r2c3 the **blurred, vertically banded column concrete at 1 m**; cam04 r2c3 the blown entablature aliasing; cam05 r2c1-r2c3 cold crowns and a flat
backdrop band; cam06 r1c1/r1c3 faceted backdrop trees and lavender impostors (in the Cycles source too), r2c1 the water moiré. Per-tile MAE peaks at 3.58
and is < 1 on 24 of 36.

**Payload and tiers** (`gate5_net.json`; the figure of record is the URL, not the dev server):

| | before frame 1 | first frame | tier 0 | tier 1 | tier 2 | all tiers | total |
|---|---|---|---|---|---|---|---|
| desktop URL | **46 814 308 B (46.81 MB)** | 8.11 s | 46.9 MB / 7.61 s | 456.3 MB / 51.81 s | 69.6 MB / 12.91 s | 74.51 s | 581.1 MB |
| mobile URL (incomplete, see §2) | 23 880 876 B | 4.46 s | 24.1 MB / 4.29 s | 0 / 0 s | 12.0 MB / 1.88 s | 6.30 s | 36.2 MB |

The **50.24 MB local dev-server figure in web/README is not the figure of record**: that capture is `http://127.0.0.1`, HTTP/1.1 headers, no compression
(its `json` 2.55 MB and `js` 1.24 MB arrive at 0.24 / 0.36 MB on the URL). 46.81 MB is 3.19 MB inside the conjunct and 2.50 MB under the export's 49.32 MB
estimate. 0 oversize, 0 tier failures, 0 lowres remaining, 0 deferred lightmaps; the only desktop 4xx is `/favicon.ico`.

**Perf, 2560x1440, medians:**

| station | 01 | 02 | 03 | 04 | 05 | 06 |
|---|---|---|---|---|---|---|
| gate5 (URL) | 31.7 | 38.0 | 37.7 | 25.1 | 34.2 | 34.2 |
| perf_ab pass B | 29.7 | 30.4 | 33.5 | 22.0 | 29.8 | 32.3 |
| delta vs pass B | +2.0 | **+7.6** | **+4.2** | **+3.1** | **+4.4** | +1.9 |
| round16c cold (on disk) | 32.4 | 37.0 | 35.1 | 22.1 | 32.2 | 34.0 |
| delta vs round16c cold | -0.7 | +1.0 | +2.6 | +3.0 | +2.0 | +0.2 |

**The pass is not throttled; the gate needs no cold re-measure.** (a) `gpu_cost_ms` medians 1.0-3.7 ms against pass B's 1.0-3.4 — the GPU work is
unchanged, the delta is CPU/present side. (b) `frame_ms.max / p95` is 18.4-22.5x at every station: the single-outlier signature `perf_ab_6c.md` §3 found
in all three of its passes, not the sustained rise of a throttled Air. (c) The lead's independent cold URL pass (decisions.md 2026-09-18: 30.8 / 37.2 /
37.9 / 24.3 / 33.2 / 34.3) agrees within 1.1 ms at five stations, and its same-session A/B puts the tiered plan at -0.1 / +2.0 ms — so +7.6 / +4.2 against
pass B is drift plus the split's structural cost (141/143 programs vs 97/99, +5 draws), not the deployment. Carried, not a 6b regression: the hero runs
**31.5 fps** at 1440p against 6a's 45. **Memory:** resident **1 861.3 MB** vs round16c's 1 931.4 = **0.964x, -69.9 MB** — outside the +-2 % band in the
favourable direction, and explained: the split uploads **269 unique texture sources for 333 texture objects** (64 shared) where round16c uploaded 289 for
289. Streaming costs nothing resident; it saves. The 1 200 MB Gate 1 budget is still exceeded 1.55x — carried from 6c.

## 4. Headers, files and the name sweep

Live on deploy 2, one curl per path class: `groups/*.glb`, `gate0/*.cube`, `tex_lo/*.ktx2` -> `public, max-age=31536000, immutable`; `manifest.json`,
`manifest_mobile.json`, `uv2_relay_status.json` -> `public, max-age=60, must-revalidate` (brotli on the JSON); `/` and `index.html` -> `public,
max-age=300, must-revalidate`. Exactly the scheme the lead deployed; deploy 2 changes nothing else. Largest published file 16.7 MB against the 25 MiB cap.

**Name sweep** (`qa_r18_probe names`, CLAUDE.md's pattern with qa_r16's object-shaped filter, over **both** gate5 manifests): **0 hits in either** — they
key on texture and group names, so it restates rather than replaces round 17's gate1/gate3 sweep (the named exceptions standing there). **0 new.**
**Observation, not a defect** (`gate5_pop_cam01.jpg`): the approved first frame does show the building at placeholder resolution, but the shore planting
and near trees are **absent** at tier 0 rather than low-resolution, so the pop when tiers 1-2 land is larger than "it sharpens" — inside what was
approved, flagged so the lead can decide whether the readout should name it.

## 5. The fix round, and the evidence owed

1. the 7 mobile group glbs are in no deploy plan -> mobile has no geometry — **export** (primary), **deploy** (assert); 14.6 MB, files already on disk.
2. `tier0_planned_bytes` disagrees with the bytes fetched (desktop 29.2 vs 46.9 MB; mobile 325.8 vs 24.1 MB) — **viewer**; one denominator.
3. **owed: the user's macOS Safari screenshot** at the hero ("Safari and Chrome on macOS"). `renders/web/user/` does not exist and every capture here is
   HeadlessChrome/152, so **no Safari claim of any kind can be made yet**.
4. **owed: the iPhone 16 Pro recording** (30 s iOS Safari walk) — not takeable until fix 1 lands; the phone would record the same empty lagoon. After the
   fix, a mobile re-capture with resident memory and frame time, scored on the rubric for the first time.
5. nothing else. Desktop is done: payload inside budget, parity exact, tiles clean, headers right, perf explained, memory better than the build it came from.
