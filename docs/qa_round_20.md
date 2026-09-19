# QA round 20 — Phase 8 items **8a (shrubs), 8b part 1 (2K crowns + coverage), 8c (column projection)** on the live URL, 2026-09-19

Verdict: **8c CLOSED · 8a NOT CLOSED (it moved one box of eight, the hero's own) · 8b part 1 improves every crossings number and introduces a visible dither.**

Capture `gate8` on the staging URL (deploy 8, main 59fe023): desktop stations 1-6 at 1920x1080, `gate8_net.json`, 1440p `gate8_perf.json`, `?tier=mobile` stations 1-6,
`gate8m_net.json`; no orbit. Before = `gate7` / `gate7m` (round 19), same deployment path. Measures: `scripts/qa_r20_probe.py` (extending r19 -> r18b -> r18 -> r17 -> r16 -> r13
unchanged) and `export/p8_atlas_probe.py viewer` as-is — **`viewer` mode, so the bake report's crown-top/trunk label swap (which is in the ATLAS mode's `bands()`) does not apply
to any number here.** No Blender, no Chrome; the URL read with `curl` only. Composite `renders/web/gate8_gate.png`; tiles: 36 station tiles at 100 % both captures, 12
before/after/reference strips at 100 %, 2 crown pairs at 200 %.

## 1. Verdict per item

* **8a (shrubs) — NOT CLOSED.** Target: the leaf-green share from ~0.5x of the reference toward 1.0x, hard-edge share not rising above it. **One box of eight moved** (01 shore
  0.62x -> **0.84x**); the other four half-share boxes are unmoved; the mean goes 0.83x -> **0.84x**.
* **8b part 1 (2K atlas + coverage 0.15) — improvement measured, closure waits for the band atlas.** Crossings **5.73 -> 7.99 / 2.92 -> 6.97 / 6.51 -> 8.53** at cam01/02/05
  against Cycles' 11.73 / 7.76 / 15.89 — and a **new, visible dither defect** on the delivered hero (§3).
* **8c (column projection) — CLOSED.** Banding anisotropy dx/dy **4.76 -> 1.39** on the near shaft (reference 1.60), grain 1.16x -> **1.25x** of the reference's, no flute seam,
  0 bytes and 0 bake.

## 2. 8a — the shrub boxes (`qa_r20_probe shrubs`), gate7 -> **gate8** (reference = 1.00x)

| box | leaf-green % g7 -> **g8** (ref) | **g8/ref** | hard-edge % g7 -> **g8** (ref) | level g7 -> **g8** | frame-norm |
|---|---|---|---|---|---|
| 01 shore shrub/reed | 11.1 -> **15.1** (17.9) | **0.84x** (was 0.62) | 3.01 -> 3.13 (1.77) | 1.37 -> 1.38x | 1.47 -> 1.48x |
| 01 shore shrub S | 9.7 -> **10.1** (13.6) | 0.74x | 4.25 -> 5.07 (3.38) | 1.10 -> 1.11x | 1.19 -> 1.20x |
| 02 shrub/reed shore | 57.6 -> **57.4** (88.6) | 0.65x | 8.71 -> 9.22 (3.44) | 1.18 -> 1.19x | 1.12 -> 1.12x |
| 02 reed clump SE | 25.2 -> **21.0** (24.9) | 0.84x | 2.05 -> 1.73 (1.57) | 1.14 -> 1.19x | 1.08 -> 1.12x |
| 05 shrub/reed shore | 9.6 -> **9.5** (33.4) | **0.29x** | 3.18 -> 3.44 (4.30) | 1.03 -> 1.04x | 1.06 -> 1.06x |
| 05 shrub/reed W | 22.3 -> **21.8** (20.1) | 1.09x | 5.20 -> 5.28 (4.06) | 0.92 -> 0.95x | 0.95 -> 0.97x |
| 03 shrub cards | 14.9 -> **14.3** (26.5) | 0.54x | 4.80 -> 4.85 (1.48) | 1.53 -> **1.44x** | 0.94 -> 0.89x |
| 06 shore planting | 34.3 -> **34.5** (20.0) | 1.72x | 0.53 -> 0.48 (0.20) | 1.04 -> 1.04x | 1.06 -> 1.06x |

Hue holds within 1.3 deg; level moves at most 0.05x and the one material move (03, 1.53 -> 1.44x) is **toward** the reference. Hard-edge share rises at six boxes and is above the
reference at seven of eight — it was above at seven before, largest rise +0.82 pt: not breached, not improving. **Tiles:** the band genuinely changed (56-95 % of pixels in every
box, MAE 14-54/255) but only at 200 % does it read — broad blades become tufts, gaps fill in. At 100 % on the delivered frames **cam01's shore band visibly gains** and **cam05's
is indistinguishable from gate7**, still wide flat gold blades where the reference is dense rounded masses; cam02's 3 m band and cam03's 8 m cards are denser, still angular
cut-outs. **The 8a cost is 5.5x what was priced.** Rendered triangles per frame 5 245 128 -> **6 361 468** at station 1 (+1 116 340), +1 128 504 at 3 and 6, **+557 246 at station
4**, identical to the triangle on mobile. The doubling at the water stations is the reflector pass, so the per-pass cost is **+~560 k against the +102 152 placed triangles the
exception was logged for** — it matches LOD2 (+102 152) **plus** the LOD1 walk-in set (+463 922) to 0.3 %, i.e. `env_shrubs.glb` is submitted in full every pass although
`shrubLod` reports `lod1: 0, source: null, asked: false`. Draws, programs and geometry count unchanged; geometry resident +1.68 MB. **Owner EXPORT/VIEWER to confirm and
re-price.**

## 3. 8b part 1 — the 2K atlas and the coverage share (`p8_atlas_probe viewer`, `qa_r20_probe crowns`)

Live from the sidecar: `impostors.atlas2k true`, `{framePx 170, atlasPx 2048, innerPx 162}`, 16/16 prototypes, 9.72 MB declared (gate7 false / 85 / 1024 / 6.05 MB); the manifest
on the URL carries `variant_2k` and `albedo_2k` and **no `band` block**, as expected. Per station cam01 / cam02 / cam05, gate7 -> **gate8** (Cycles): crossings per 100 px **5.73
-> 7.99** (11.73) / **2.92 -> 6.97** (7.76) / **6.51 -> 8.53** (15.89); crown-box centre/edge **0.532 -> 0.566** (0.852) / **0.397 -> 0.434** (0.364) / 0.912 -> 0.910 (0.960);
crown leaf % 25.2 -> **24.1** (22.2) / 29.6 -> 31.2 (17.4) / 22.0 -> 20.7 (9.4); the hero's p10 0.894x -> **0.913x** of the reference's.

Every crossings number improves and the hero's dark end and leaf share move toward Cycles; cam02 overshoots its reference centre/edge further and its box level goes 1.04 ->
1.10x, as the viewer's own sweep predicted.

**Plainly, from the tiles: the crown still reads as a mass, and the mechanism is now visible.** At 100 % — not 200 % — every far-tree crown seen against the sky carries a
**regular ordered dot grid**: cam01 r1c1/r1c3 and r2c2/r2c3 (all four shore crowns), cam02 r1c3 and the fill tree, cam03 r1c1. It is the coverage share spending an alpha constant
across 9 screen pixels — the halftone the README judged subtle at 0.15; against a bright sky at 100 % it is not, and it is on the frame we deliver. Where the background is
mid-tone the same dither *helps*: **cam06's far trees gain real branch structure**, the round's clearest 8b win. Per the gate rule the tiles override the metric: a **new
defect**, owner BAKE/VIEWER, and the band atlas must be re-swept rather than inheriting `share 0.15` on 341 px frames.

## 4. 8c — the cam03 columns (`qa_r20_probe column`)

Banding anisotropy dx/dy (mean |d/dx| over mean |d/dy| inside the box — the objxy detail plane streaks vertically, so it runs high), gate7 -> **gate8** (reference): near right
shaft at ~1 m 4.76 -> **1.39** (1.60), near left at ~3 m 4.59 -> **1.91** (2.76), mid shaft 3.90 -> **2.64** (2.91). Grain (`hp9`) on the near right shaft 1.16x -> **1.25x** of
the reference's; level 2.12x / 1.77x / 2.64x, unchanged. `detail.projection` is `dominant` in the deployed boot log. The near shaft's vertical energy rises 0.49 -> 1.72 (3.5x)
while the horizontal barely moves — the streak is gone, not merely blurred. The 100 % tile is unambiguous: gate7's shaft is vertical smears with no pores; gate8's carries
aggregate speckle, pores and mottled staining with crisp flute edges, and there is **no flute-to-flute seam**, so the reserved triplanar blend is not needed. New observation: a
faint horizontal joint line is now legible across the near shafts (same world height on two columns) — almost certainly the modelled drum joint the smear used to hide; reported,
not a defect. cam03's frame luma moves 1.623x -> **1.617x** of the reference; its deep-shade deficit is untouched.

## 5. Regression, payload, perf, memory, sweep

* **Frames and boxes.** g8/g7 luma 1.0031 / 1.0050 / 0.9958 / 1.0000 / 1.0035 / 1.0018x; MAE against the Cycles reference falls at five stations (24.52 -> **24.45**, 18.44 ->
  **18.34**, 34.76 -> **34.47**, 20.69 -> **20.56**, 18.03 -> **18.01**), unchanged at 04. 3 of 25 boxes move over 3 %, all foliage and all explained (02 far tree 1.051x,
  02 reed clump 1.039x, 03 shrub cards 0.940x, toward the reference); **0 of 11 architecture boxes move** (max 1.016x, the capital row = the trees behind it).
* **Payload.** Desktop **46 872 821 B / 320 requests** before the first frame (+61 715 B, inside the rule; the brief's ~49.4 MB did not materialise because the 2K atlases went
  to tier 1 and only `env_t0.glb` (+55 680) and the JS bundle (+4 654) grew tier 0); total 588.1 MB. Mobile **46 801 034 B**, total **66.1 MB**. Asset diff: 16 `_albedo_1024`
  replaced by 16 `_albedo_2048` plus the JS bundle, nothing else; one 404 (favicon) as before; `curl` gives `/` 200 `max-age=300`, manifests `max-age=60`, atlas `immutable`.
* **Perf, 1440p medians.** 32.8 / 37.7 / **42.0** / 26.2 / 33.7 / 36.6 ms; vs gate7 +1.2 / +0.4 / **+3.1** / -0.1 / -2.2 / +0.1, vs the idle `gate5cold` +2.0 / +0.5 / **+4.1** /
  +1.9 / +0.5 / +2.3. **Station 3 is outside the +3 ms rule on both baselines** — it also gained the most triangles (+1.13 M) and carries the whole detail-projection change.
  The drift caveat stands (the viewer's own A/B measured the same default at 31.85 and 36.75 ms in one session), so this is flagged, not failed; a same-session A/B at station 3
  would settle it. Draws and programs identical to gate7 at every station.
* **Memory.** Desktop resident **1 862.9 MB** (+1.68 MB, all geometry). **`texture_bytes` is byte-identical to gate7** across a 1K -> 2K swap of 16 atlases: `resident()` in
  `web/src/main.js` bills only textures reachable from material slots and the impostor atlas is a custom `atlas` uniform, so it has never been counted; the real GPU cost is
  ~**+67 MB**. Mobile **563.5 MB** (+1.6, against the 700 ceiling).
* **Sweep, errors, mobile.** 0 object-shaped name hits over 722 + 341 manifest rows; 0 mobile paths absent from the desktop plan; 0 page errors; the bare-URL frame check needs
  Chrome and stands from the 6b close. Mobile luma within 0.35 % at all six, same densified LOD2 shrubs, same coverage dither on the 1K atlas (coarser), draws identical to
  gate7; the blue-violet shaded stone at cam02 is as strong as ever — and the tile pass shows it on **desktop** cam02 r1c2 too, so it is not a mobile-tier fault.

## 6. Scores

Desktop (rubric rows as QA 17): **01 3.78 · 02 3.25 · 03 2.75 · 04 2.88 · 05 3.06 · 06 2.89** — deltas vs QA 19 0 / 0 / **+0.12** / 0 / 0 / **+0.06**. **03** Material realism 3.5
-> 4 and Edge wear 2 -> 2.5 (the near shafts are that frame's dominant surface and go from smear to grain, pores and mottle); **06** Material realism 3 -> 3.5 (the aerial's far
trees gain branch structure); **04** unchanged. **01 and 02 hold, deliberately**: the hero's two real gains (its shore band 0.62x -> 0.84x of the reference's leaf share, its
columns' grain) are cancelled inside the same frame by the ordered dot texture the coverage share paints on all four shore crowns and both roof-line crowns — the tiles override
the crossings metric, as the gate rule requires. Mobile: **01 3.2 · 02 3.3 · 03 2.4 · 04 2.7 · 05 2.8 · 06 2.5** (deltas 0 / 0 / +0.1 / 0 / 0 / +0.1, the same two causes).

## 7. Residuals for `docs/delivery.md`, with owners

1. **The shrub band is unfixed at every station but the hero's own — owner ENV/EXPORT.** 05 shore 0.29x of the reference's leaf share (unmoved), 03 cards 0.54x, 02 shore 0.65x.
   The LOD2 densification is spent; the remaining gap is card *shape* (flat wide blades vs rounded masses), not card count.
2. **NEW — the coverage dither is a visible ordered dot texture at 100 % — owner BAKE/VIEWER.** Every far-tree crown against the sky at stations 1, 2, 3. Re-sweep the share on
   the band atlas; do not carry 0.15 to 341 px frames assuming a finer texel hides it.
3. **The far-tree crown is still a mass, not twigs — owner BAKE** (QA 17 residual 4, improved not closed; the band atlas is next).
4. **Station 3 outside the +3 ms rule on both baselines — owner VIEWER/EXPORT**, with the drift caveat; and the ENV budget exception draws ~+560 k triangles per pass, 5.5x the
   +102 152 it was logged for.
5. **The resident figure has never counted the impostor atlases — owner VIEWER**: 32 -> 89 MB absent from every memory number in Phases 6-8.
6. **Blue-violet shaded stone is a desktop fault too — owner MATERIALS/LIGHTING** (QA 19 §4.4b called it mobile-only).
7. **Carried unchanged:** flat backdrop city blocks and colonnade backdrop walls; cam03's missing deep shade (1.62x) and the shaft still 12x under its texel need; cam06's water
   moiré; the reflection cooler and less saturated than Cycles; station 5's frame 0.979x; the crown floor overshooting at cam02/05; mobile leaf scale; hero 30.5 fps at 1440p against 45; owed by the user — the
   Safari hero screenshot and the iPhone walk recording.
