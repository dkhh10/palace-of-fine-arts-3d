# Phase 8d — the Cycles haze / shade check (review r2 finding 4), env builder, 2026-09-19

**Question.** `HAZE_TINT` is a 0.78 linear albedo over ~23 km² of far ground, hills and city — free in the viewer
(no GI), taken literally by Cycles in the Phase-8 4K hero; and the 8d palace-shadow term multiplies with Cycles'
*real* cast shadow on the hall. **Verdict: no fix needed** — worst architecture box 0.39 % against the 1 % limit
and sign-mixed (sampling noise), no double-darkening. Nothing applied, nothing proposed.

**Method.** `scripts/p8d_haze_check.py` on a **scratch copy** of `master_delivery.blend` (deleted after; master and
master_delivery never touched). Delivery look as found and asserted: `AgX` / `AgX - High Contrast` / −2.8331 EV.
Cycles GPU, 1920x1080, **32 spp, adaptive OFF**, `time_limit 0` so A and B spend the same samples on every pixel,
OIDN per `light_presets.apply_final_cycles`; 100–109 s per frame, four frames. **A** = as merged; **B** = the three
added terms bypassed (haze mix on Base Color / Roughness / Specular, the per-lot spread, the palace shadow). The
bypass is structural and **asserted at every step**, aborting if the graph is not what it expects: it neutralised
`{haze: 24, scale: 10, hsv: 7}` over **8 materials**, exactly what `apply_backdrop_atmosphere`'s arguments predict.
The 8d *base colours* stay in **both** variants — the question is about the added terms only.

## cam01 hero — luma B (terms off) → A (as merged)

| box | B → A | Δ | sat B → A |
|---|---|---|---|
| whole frame | 0.5462 → 0.5462 | **−0.01 %** | 0.474 → 0.474 |
| ARCH rotunda block `700 160 1240 480` | 0.4963 → 0.4971 | **+0.15 %** | 0.701 → 0.699 |
| ARCH S-colonnade wall `1600 590 1670 635` | 0.4643 → 0.4625 | **−0.39 %** | 0.807 → 0.806 |
| ARCH vault field `900 380 1010 430` | 0.2360 → 0.2362 | **+0.10 %** | 0.625 → 0.622 |
| ARCH jamb `872 400 892 480` | 0.2144 → 0.2148 | **+0.18 %** | 0.446 → 0.445 |
| N-colonnade band `20 520 540 645` | 0.2328 → 0.2332 | +0.17 % | 0.669 → 0.667 |
| water `1150 1000 1450 1050` | 0.4909 → 0.4910 | +0.02 % | 0.397 → 0.397 |
| hall band L `40 470 520 630` | 0.3566 → 0.3569 | +0.10 % | 0.578 → 0.577 |
| hall band R `1200 470 1680 630` | 0.4579 → 0.4575 | −0.09 % | 0.636 → 0.635 |

The mixed signs say this is 32-spp noise, not a lift: the hazed ground is behind the building and below the horizon
from a 1.3 m eye, so its bounce reaches the stone through nothing but the sky the stone already sees.
**No double-darkening**: the hall bands move ±0.1 % and the 100 % crops (rows 3–4 of the composite) are
indistinguishable — at the hero the hall's east wall is behind the tree belt and already inside Cycles' real
colonnade shadow, so the albedo shade term has nothing left to darken.

## cam06 aerial — the term doing its job, on the backdrop only

Luma B → A: whole frame 0.3910 → 0.3943 (+0.86 %); top row `0 0 1920 360` 0.4236 → 0.4339 (**+2.43 %**); top-left
`0 0 640 240` 0.4276 → 0.4479 (**+4.75 %**); r1c3 `1280 0 1920 360` 0.3723 → 0.3824 (+2.70 %). Saturation falls
slightly in each (0.290 → 0.285, 0.269 → 0.263, 0.336 → 0.333). The lift lands where it was aimed and no
architecture box is in these frames.

## Is the backdrop change visible at 4K in the hero?

**Yes, plainly.** The phase-5 v2 4K hero is `renders/final/hero_cam01_3840x2160_128spp.png` (3840x2160, 128 spp,
2026-09-10, pre-8d). The bottom row of `renders/qa_comparisons/phase8d_haze_check_960.jpg` puts its N-colonnade
band beside the 8d render at the same framing: the 4K hero shows the pale olive wall with its row of dark
rectangular panels through every intercolumniation, the 8d frame shows dark foliage and shade. The QA-17 hero
defect is gone. What is visible at 4K is the **belt plus the base-colour work** — the haze and shade terms
themselves are invisible at the hero, per the table above.

Caveat: this covers the six QA stations' geometry. If a future camera ever looks *down* the hazed ground from close
range, re-measure.
