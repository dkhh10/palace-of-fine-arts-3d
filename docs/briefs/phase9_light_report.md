# Phase 9 lighting round 19 — report (QA-08-2 / QA-09-6, station 2's blue-violet shaded stone)

Changed: `scripts/light_build.py` (`SKY_DIFFUSE_TINT (1.0,0.65,70.0) -> (1.0,0.75,8.0)`, `SKY_DIFFUSE_TINT_ANTISUN
1.0 -> 0.0`, `_ANTISUN_P` annotated inert), `assets/lighting.blend`, `scripts/light_r19_{sweep,measure,predict,sheet}.py`,
`docs/lighting_notes.md` 29. All numbers below are Cycles 1920x1080, 32 spp fixed, adaptive off, OIDN, the delivery look,
measured through the FULL chain (light_build -> lead_build.sh -> phase5_deliver 1b -> p8_cycles_refs on a scratch copy).
Noise floor (cam01 seed 0 vs seed 1) MAE 2.91; the shipped chain vs BEFORE on cam01 is MAE 0.99, i.e. inside it.

**1. Station 2, b* / h_ab / R-B (before -> after / photo ref 062 in the cam02 fixture)**

| box | b* before -> after | photo | h_ab after | R-B after | verdict |
|---|---|---|---|---|---|
| shade_pier | -4.68 -> **+11.26** | +14.10 | 62.1 | +32.8 | PASS PASS PASS |
| shade_pier_r | -18.20 -> **+5.29** | +13.22 | 79.7 | +10.0 | PASS PASS PASS |
| shade_arch | -3.12 -> **+8.80** | +7.49 | 64.7 | +24.5 | PASS PASS PASS |
| soffit_l | +13.87 -> +18.74 | +12.83 | 82.6 | +47.2 | b PASS, h_ab FAIL (+2.6 over 80) |
| soffit_r | +14.99 -> +20.06 | +7.93 | 82.6 | +49.9 | b PASS, h_ab FAIL (+2.6 over 80) |
| shade_frieze (control) | +12.82 -> +23.31 | +10.50 | 86.7 | +52.2 | FAIL (window 9.9-12.9) |
| sky (camera rays) | L 70.50/b -25.35 -> 70.50/-25.34 | -- | -- | -- | unmoved |

Mean |b* - photo| over the six boxes: 11.87 -> 7.16.
**The frieze cannot be held.** `light_r19_measure` fits the per-box sky mix factor from three tint levels
(notes 29.4): holding the frieze pins the dose, and the shafts then depend only on f_box/f_frieze, whose best
value in the whole socket space (antisun 0) still lands shade_pier_r at -5.7. Reaching +5 needs 0.56 against a
measured 1.50. The render's 15-30 b* spread between cam02's shaded boxes is set by warm bounce, not sky colour;
the photograph has no such spread (shafts +14.1/+13.2 vs frieze +10.5). Hand-off to materials/ARCH, not lighting.

**2. Hero (cam01) HOLD: 12/12 boxes** within 3 % luma and 2 deg hue. shaded_attic 123.3 -> 120.3 lum (-2.4 %),
hue 41.2 -> 41.3 (+0.1 deg); sunlit_attic -0.5 % / -1.1 deg; columns -1.0 % / -0.8 deg; near-water sat 0.193 ->
0.185 (window 0.22-0.32 was already missed before this round, unchanged in kind); sky_top/sky_left identical.

**3. Stations 3 and 4 HOLD: cam03 8/8, cam04 6/6** boxes inside the same 3 % / 2 deg. cam03 near_column lum 33.5
-> 33.4, flute_band 33.2 -> 33.2 (the colonnade's deep shade does not open up); cam04 coffer_field 52.1 -> 51.9,
vault_soffit_e 33.6 -> 33.5.

**4. Eevee cost:** cam02 36.9 s -> 34.4 s, cam03 48.7 s -> 34.7 s (1280x720 preview, same machine, GPU idle).
No cost: the shipped world builds FEWER nodes (the anti-sun weight branch is gone at amount 0).

AFTER station frames (960 px): `renders/previews/lighting/r19_ship_0{1,2,3,4}_960.jpg` (the 1920x1080 PNGs beside them are
left uncommitted at 8 MB each).
Sheet: `renders/qa_comparisons/lighting_r19_shade_960.jpg` (cam02 BEFORE / AFTER / ref 062 crops of the four
shaded boxes, plus the hero attic and columns BEFORE / AFTER).
Winning knob values: `SKY_DIFFUSE_TINT = (1.0, 0.75, 8.0)`, `SKY_DIFFUSE_TINT_ANTISUN = 0.0`. Everything else
unchanged. Test suite: no suite — scripts/ has no lighting tests; the round's control is the `base` identity
render (MAE 0.0138) and the seed-1 noise floor (MAE 2.91).

**Hand-off to the bake engineer (read back from the rebuilt master_delivery, not asserted):**
1. Class of change = **diffuse sockets only**. No lamp was armed or added (`shade_fill lamps: []`; the 20 lamps are
   the unchanged sun / rotunda+vault bounce / gallery fills). Camera branch `sky_camera_boost 2.1`,
   `sky_camera_saturation 1.2` and glossy branch `sky_glossy_boost 4.2`, `sky_glossy_saturation 0.9`,
   `sky_glossy_hue 0.5` are byte-identical to the shipped values; the cam02 `sky` box moved 0.01 b*.
   **The camera and glossy equirects and the AgX LUT do not need re-baking. Only the lightmaps do.**
2. Exact socket values shipped: `sky_diffuse_tint = [1.0, 0.75, 8.0]`, `sky_diffuse_tint_antisun = 0.0`;
   unchanged beside them: `antisun_p 3.0` (inert, the branch is not built), `horizon 1.0`, `horizon_p 6.0`,
   `sunside [1.0, 1.0, 0.0]`, `sunside_p 3.0`, `diffuse_boost 2.5`, `diffuse_saturation 1.0`, `diffuse_hue 0.5`,
   `strength_lighting 0.8`, sun az 118.49 / el 7.36.

Open items: soffit_l/soffit_r h_ab 82.6 against a 40-80 window (they were 75.5/76.0 and passing before; the sky
lever moves every shaded box together, and their a* is 2.4-2.6 against the photograph's 10.2 — a red-axis
deficit in the material, not a light one). shade_frieze +23.31 as above.
Last commit: see `git log -1 phase9-light`.
