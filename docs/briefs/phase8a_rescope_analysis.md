# Phase 8a re-scope — the shrub / reed shore band: what the gap actually is, and what each fix costs

Analysis only, CPU only (no Blender, no Chrome, no render). Captures `renders/web/gate9_*` (deploy 9) against the
QA reference (the Phase 5 **Cycles** frames `qa_r13_probe.REF`, which is what "ref" means in every QA-17/20 shrub
number — not the photograph). Probes: `scripts/p8a_rescope_boxes.py`, `p8a_rescope_terms.py`, `p8a_rescope_sim.py`,
`p8a_rescope_lod.py`. Evidence image: `renders/qa_comparisons/p8a_rescope_boxes_viewer_vs_cycles.jpg`
(four boxes, viewer over Cycles, 960 px).

## 1. Q1 — what the gap is, per box: **colour, not coverage and not species**

`p8a_rescope_boxes.py decomp`. `ceil%` is the leaf share a *perfect recolour of the cards* would reach — the union of
the pixels the 8a densification moved (gate7 -> gate9) with today's leaf pixels.

| box | leaf% now (ref) | now/ref | card footprint | ceil/ref | level/ref | leaf hue now (ref) | leaf sat now (ref) |
|---|---|---|---|---|---|---|---|
| 01 shore shrub/reed | 15.4 (17.9) | 0.86x | 40.5 % | **2.62x** | 1.39x | 54.4 (63.0) | 0.52 (0.68) |
| 01 shore shrub S | 11.2 (13.6) | 0.82x | 44.4 % | **3.57x** | 1.13x | 57.5 (58.9) | 0.78 (0.89) |
| 02 shrub/reed shore | 56.6 (88.6) | 0.64x | 73.4 % | **1.04x** | 1.19x | 71.6 (90.3) | 0.64 (0.59) |
| 02 reed clump SE | 21.1 (24.9) | 0.85x | 45.5 % | **2.61x** | 1.18x | 53.5 (63.7) | 0.30 (0.43) |
| 05 shrub/reed shore | 10.4 (33.4) | **0.31x** | 55.0 % | **1.83x** | 1.06x | 55.3 (61.1) | 0.52 (0.93) |
| 05 shrub/reed W | 22.7 (20.1) | 1.13x | 49.1 % | 2.77x | 0.98x | 58.8 (58.3) | 0.95 (0.94) |
| 03 shrub cards | 14.2 (26.5) | 0.54x | 53.6 % | **2.31x** | 1.44x | 67.2 (70.9) | 0.40 (0.83) |
| 06 shore planting | 35.4 (20.0) | 1.76x | 23.9 % | 2.70x | 1.05x | 50.1 (52.1) | 0.29 (0.41) |

* **Coverage is not the constraint anywhere.** `ceil/ref` is 1.04-3.6x: there are already more card pixels in every box
  than the reference has leaf pixels. More cards cannot help; QA 20 paid 5.5x the priced triangles for one box of eight.
* **Species is not the constraint.** `p8a_rescope_lod.py boxes` projects all 1 379 placements with the station cameras
  (validated below): every box is filled by the same mix (pittosporum-dominant, then agapanthus / twig / mahonia / reed),
  54-258 m away. Nothing is missing that the reference has.
* **Colour is the constraint, and it is the SHADING and not the albedo.** The leaf test is
  `G - 0.85R > 5 & B < G`; over the card pixels our margin mean is **-13 to -0.6** where the reference's is **-2 to +11**
  — a mean shift of 6-14/255, with our spread already *wider* than the reference's (`sim spread`). The fitted
  per-channel gain that would map our card pixels onto the reference's (`sim fit`) is a **luma-neutral G/R rotation of
  1.15x median** plus a **level drop (median kR 0.65, kG 0.81)**: our cards are both too warm and too bright.
* The tiles say the same thing in one look: the reference's shore is **dark green bushes with gold sunlit rims and deep
  shadow between them**; ours is a **uniformly sun-gold mass of angular cut-outs** at the same places, same sizes.

## 2. Q2 — where the colour comes from, and which term dominates

`p8a_rescope_terms.py` reads the export's own json; `web/src/foliage.js` is read, not run.

* **Albedo is green and is not the fault.** `MAT_shrub` tinted linear `[0.094 0.182 0.051]` = hue **100.3**, sat 0.72;
  `MAT_shrub_light` 99.8; `MAT_reeds` 72.2; `MAT_shrub_dry` 26.7 (dry by design). Clipped texels 0.
* **The card diffuse is one flat, warm, per-placement irradiance.** The viewer removes the cards' sun diffuse
  (`specularOnlySun`) and adds `instance_irradiance.json` with **no cosine**: mean `[1.83 1.42 1.36]` over 1 379
  placements, **G/R 0.774** — a warm light applied identically to every texel of every card, front and back.
  Albedo x that irradiance = hue **87.4** (sat 0.73); albedo x the *darkest decile* of the same irradiance = hue **130**.
  The scene therefore contains the green the metric wants — in the shade that the viewer's cards never get.
* Secondary terms, all smaller: the environment lobe at `CARD_ENV = 0.3` (diffuse + specular + **sheen 0.15**), and the
  Phase 5 translucent lobe which cards do **not** get (`?leaftrn=shrubs`); its tint `[0.85 1.15 0.60]` is a green push.
* **Simulated on the capture pixels** (`sim solve` / `sim global` / `sim relight`; display-space, so a lower bound on
  the scene-linear change). Per box, the strength needed to reach 1.00x and what it lands on:
  01 shore R x0.96 · 01 S R x0.97 · 02 shore R x0.54 · 02 reed R x0.84 · 05 shore R x0.88 · 03 cards R x0.84 —
  and 05 W and 06 are already **above** the reference and get worse. **No single global constant works:**
  the best global G/R rotation (1.04x) gives mean 0.99x with **3 of 8** boxes inside 0.85-1.15x — exactly the 3 of 8 we
  have today. The directional relight (the same light redistributed 45 % shade / 55 % sun with the bake's own shade
  chroma `[0.68 1.02 2.05]`, level held) gives **1.32 / 1.89 / 0.64 / 0.75 / 0.96 / 1.92 / 0.71 / 1.60x**: it moves the
  three starved boxes the most (05 shore 0.31 -> 0.96x, 03 cards 0.54 -> 0.71x, hero 0.86 -> 1.32x) and overshoots the
  three that were already high.
* **The metric is knife-edge and should stop being an acceptance gate.** A **1 %** change in the cards' red channel
  moves the leaf-green share by **2-9 % relative** (per box); 4 % of red takes the hero from 0.86x to 1.00x and 8 %
  takes it to 1.42x. Nothing in the rubric distinguishes those three states visually.

## 3. Q3 — which LOD set draws, and what moving the switch costs

`p8a_rescope_lod.py`. The station cameras are rebuilt from the manifest's own Euler + shift and agree with the gate9
projection to **0.02 px horizontally**; the capture and the Cycles frame cross-correlate at **dy = 0 at every station**
(`framecheck`), so the framing is sound. (One artefact for the record: the `cameraWorldMatrix` field *recorded in the
gate9 sidecar* is a look-at aimed at the world origin, 0.738 deg = 13.7 px below the camera that actually rendered.
Stale metadata, not a rendering fault — but do not use that field to place boxes.)

| box | station | placements in box | distance p10/med/p90 (m) | inside the 30 m switch |
|---|---|---|---|---|
| 01 shore / 01 S | 1 | 180 / 222 | 73/89/122 · 78/92/121 | 0 |
| 02 shore / 02 reed | 2 | 306 / 41 | 55/105/151 · 54/61/68 | 0 |
| 05 shore / 05 W | 5 | 212 / 102 | 74/99/137 · 117/143/156 | 0 |
| 03 cards | 3 | 550 | 112/154/190 | 5 |
| 06 shore | 6 | 136 | 239/246/258 | 0 |

**Every QA box is LOD2**, as the ENV report said. Moving the switch out (LOD1 everywhere) costs **+774 880 placed
triangles per pass**, doubled at the five water stations by the Reflector: station 1 6.36 M -> **7.91 M (1.24x)**,
station 4 3.29 M -> 4.84 M (**1.47x**), stations 2/5/6 1.23-1.25x. At 30.5 fps today on the hero at 1440p that is not
affordable, and it buys geometry where the measurement says geometry is not the constraint. **And it is mispriced until
QA 20's bug is fixed**: `env_shrubs.glb` (the LOD1 walk-in set) is already submitted in full at every station, so part
of this cost is being paid today for nothing.

## 4. Costed options

| # | what changes | files | GPU | MB | predicted leaf/ref at the 8 boxes | risk |
|---|---|---|---|---|---|---|
| A | **viewer-only card chroma**: a luma-neutral G/R rotation on the cards' baked irradiance, `?cardtint=` | `web/src/foliage.js` | 0 | 0 | best global 1.04x: 0.99/1.04/0.72/0.88/0.42/1.38/0.61/1.90 (mean 0.99x, **3/8** in band — no better than today) | hard% rises at 8/8 (today 7/8); overshoots 06 and 05 W |
| B | **viewer-only directional relight**: split the flat per-placement irradiance into a sun term (cosine on the card normal + clump shadow, sun vector and colour from the manifest) and a sky term; `?cardsun=` | `web/src/foliage.js` (+ the sun block it already reads) | 0 | 0 | 1.32/1.89/0.64/0.75/**0.96**/1.92/**0.71**/1.60 (mean 1.09x, moves all three starved boxes) | the crude pixel simulation triples the hard-edge share; a real per-fragment N·L on smooth normals will not, but it **must be measured**, and the level must be held (it is held by construction here) |
| C | **export/bake**: bake the card irradiance as two terms (sun-only, sky-only) so B is physical instead of estimated | `export/bake_*.py`, gate 3 instance irradiance, re-export, re-deploy | a two-pass vertex bake over 28 prototypes (bake engineer to price) | ~0 (same json, two triples per placement) | same as B, better grounded | a full bake -> export -> tier -> deploy chain for a term B can estimate for free |
| D | **ENV blend + master rebuild + export**: more / smaller cards again | `scripts/env_build.py`, `assets/environment.blend`, master, export | hours | +MB | **rejected by measurement**: the card footprint is already 1.04-3.6x the reference's leaf share | QA 20 already paid 5.5x the priced triangles for 1 box of 8 |
| E | **frozen `MAT_shrub*` re-tint** (would need the user's approval) | `assets/materials.blend` + master + full re-export | hours | 0 | **cannot close the metric**: the reference IS the Cycles render of those same materials, so a MAT_ change moves the target with the measurement | approval cost for no parity gain |
| F | **re-scope**: fix nothing for the metric; report the leaf-green share, stop gating on it | docs only | 0 | 0 | unchanged | the tiles' defect (flat sun-gold cut-outs) stays visible |

## 5. Recommendation — ONE

**Option B, with the leaf-green share demoted from gate to report.** It is the only lever that addresses what the
tiles actually show (the reference's shore is modelled light and shade; ours is one flat sun-gold value), it is
viewer-only — no Blender, no bake, no master rebuild, no export, no MB, no user approval, no frozen-asset change —
and it is the only one that moves the three starved boxes (05 shore 0.31 -> ~0.96x, 03 cards 0.54 -> ~0.71x,
hero 0.86 -> ~1.32x) instead of trading them against the three already above the reference. Ship it behind `?cardsun=`
with `0` restoring today's look, measure the eight boxes **and** the 100 % tiles at cam01/03/05, and hold the level
(QA 17's one closed shrub item) and the hard-edge share as the constraints.

Two riders for the lead, both measured above and neither part of option B:
1. **Fix the `env_shrubs.glb` walk-in bug first** (QA 20). Until it is fixed every shrub triangle budget, including the
   LOD-switch price in §3, is wrong by +463 922 triangles per pass.
2. **Close 8a on the tiles, not on the 0.85-1.15x band.** 1 % of red moves the metric 2-9 % relative; three of the eight
   boxes are already at or above the reference; no global change puts more than 3 of 8 inside the band. Chasing the
   number past option B is the flat-round rule's definition of stopping.
