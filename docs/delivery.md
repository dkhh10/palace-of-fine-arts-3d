# Palace of Fine Arts — Phase 5 delivery (lead, 2026-09-10)

## Deliverables
| item | path | note |
|---|---|---|
| Scene, self-contained | `master_delivery.blend` (277.7 MB, 89 images packed) | opens in 0.86 s; LOD1 in the viewport, LOD0 at render; Eevee viewport preset saved; gitignored (rebuild: `scripts/lead_build.sh` then `PFA_PACK=1 scripts/phase5_deliver.sh 1b`) |
| Scene, linked | `master.blend` (160.9 MB) + `assets/*.blend` | what QA rounds 8-9 scored; links `assets/architecture / ornament / materials / environment / lighting.blend` by relative path |
| 4K Cycles hero | `renders/final/hero_cam01_3840x2160.png` | native 3840x2160, 384 spp fixed, adaptive off, OIDN, AgX High Contrast, exposure -2.833 (see the final status entry for wall time) |
| 4K timing probe | `renders/final/hero_cam01_3840x2160_128spp.png` | 128 spp fixed: 1432.6 s wall, peak RSS 6.2 GB (QA-03-16 closed) |
| Side-by-side | `renders/qa_comparisons/final_hero_vs_ref169.png` | render / ref 169 aligned (scale 1.3108) / blend; `qa_silhouette.py align` |
| Flythrough path | `CAM_flythrough` in the scene, frames 1-1224 @ 24 fps (51 s, 251 m) | `scripts/light_flythrough.py`; clearance 1.57 m outside / 1.43 m gallery with ornament linked (`light_flythrough_check.py --master`) |
| Flythrough test | `renders/final/flythrough_test_640.mp4` | Eevee 640x360, 16 TAA, every 2nd frame at 12 fps; ~14 s per frame on the M2 |
| Delivery tooling | `scripts/phase5_deliver.sh`, `phase5_cleanup.py`, `phase5_hero.py`, `phase5_flythrough.py` | each step individually runnable; every Blender run through `scripts/blender_run.sh` |
| QA record | `docs/qa_round_09.md` (final scores + known issues), `renders/qa_comparisons/round09_gate.png` | hero 3.67 / 5 on the QA rubric; the gate rule (two flat rounds after the projection) closed the polish loop |
| Decisions | `docs/decisions.md` (final gate judgement 2026-09-10), `docs/status.md` | |

## Opening and rendering
See docs/tech_notes.md "Opening and rendering (Phase 5)". Short form: open `master_delivery.blend`; the viewport is Eevee at LOD1. To re-render the
hero: `scripts/blender_run.sh 7200 -- --background --python scripts/phase5_hero.py -- --blend master_delivery.blend --spp 384 --res 3840 2160 --adaptive off --denoise on`.
Flythrough frames: `scripts/phase5_flythrough.py --blend master_delivery.blend --res W H --samples N --frame-step S [--frame-start F]`.

## Measured on the delivered hero (4K frame downscaled to 1920x1080, QA boxes; photo = ref 169)
| box | render | ref 169 | QA window |
|---|---|---|---|
| sunlit attic lum / sat / R-B | 187.2 / 0.488 / +110 | 188 / 0.582 / +134 | 178-201 / 0.53-0.62 / >= 120 (sat capped by the view transform, accepted) |
| shaded attic lum / hue / sat | 126.7 / 35.1 / 0.448 | 118.8 / ~30 / 0.454 | 103.5-126.5 / 23.5-35.5 / <= 0.50 |
| reflection lum / hue / R-B | 114.4 / 41.2 / +52 | 164.8 / ~38 / +72 | 124-208 / 25-45 / >= +35 (mirror 0.61 of sunlit vs 0.87) |
| near water lum / hue / sat | 124.1 / 207.5 / 0.202 | 105.4 / 190 / 0.246 | 79-131 / 185-200 / 0.22-0.32 |
| lagoon flank lum / hue | 159.9 / 209.6 | 152.4 / 200.3 | 114-190 / <= 210 |

## Known issues (open at delivery, ordered by hero visibility; owners and one-line fixes in docs/qa_round_09.md)
1. Hero mirror at 0.61 of its own sunlit stone vs the photo's 0.87 (materials: grazing-incidence lobe). 2. Archivolt band and bed-mould modillions
blank on 8 sockets (ornament). 3. Building block 1.10x the photo's saturation off the attic box (lighting tint b 70 -> ~55). 4. Shoreline reads as a
hedge: no trunks, shed, figures (environment). 5. cam03 walk hue green (lighting + environment). 6. cam02 shaded face violet in Cycles (lighting
tuned on Eevee). 7. cam05 lagoon band bright (the hero / cam05 gloss-mix trade). 8. Coffer field / rim saturation (materials). 9. Eevee-Cycles
west-soffit gap +0.22 (probe coverage; the Eevee test animation mispredicts that corner). 10. Entablature cornice / frieze sub-courses 1.33x / 0.87x
(architecture option A). 11. Entablature row std 37 vs 40. 12. Sunlit chroma capped by AgX High Contrast (accepted). 13. ref 062 is a midday photo:
cam02 matches its framing, never its tonality at golden hour.
