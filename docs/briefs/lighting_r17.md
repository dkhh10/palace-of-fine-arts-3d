# Lighting round 17 — the arch soffits and the colonnade shade, on the fixed vaults (brief from the lead, 2026-09-10). Branch `lighting`.
Read docs/briefs/process.md. `git merge main` first (main has ARCH r8: the vault chord triangles are gone on all 8 bays, so every box that looked at
an arch soffit measured a wrong surface until now). Opus high, SHORT: one Eevee five-camera pass, at most 2 Cycles hero frames (64 spp), 1 Cycles
cam02 + 1 Cycles cam03 at 720p 64 spp. Renders to renders/previews/light/r17_*. Report < 20 lines. Inspect cam02 / cam03 in 100 % tiles (PIL crops).
Read: docs/status.md "USER DEFECT" and "ARCH r8 reported"; docs/qa_round_09.md QA-09-6 (cam02 face violet in CYCLES), QA-09-5; docs/reviews/light_r16_review.md carries.
0. Re-base every box that looked at an arch soffit or through an arch (cam02 shade_soffit and pier_r, any hero box inside the main arch) on the new
   geometry, Cycles frame, and state the before / after of the SAME box on the same rig so the lead sees what the geometry change alone moved.
1. cam02 arch soffits (user: "render flat blue", QA FAIL): the soffit is now a coffered barrel; land it as a shaded warm plaster surface (hue 25-60,
   sat <= 0.35, and the coffers readable: rib / field contrast >= 15 lum in the Cycles tile). Lever: the warm interior fills (cam04's hold) and the
   tint discriminators measured on a CYCLES frame this time (QA-09-6: r16 tuned on Eevee; Cycles pier 268 / soffit 250). Hold cam04's coffer boxes.
2. cam03 near column (ARCH_colonnade_south_column_028, 33 % of the frame, mean lum 3.7): a fluted shaft that renders black. Target: the shaft's
   flute modulation visible (p95 >= 25 lum, flute ridge / flute floor >= 8 lum) with the frame under lum 10 held <= 20 % and the outer row >= 0.15.
   Also the violet cast on the shaded shafts and the speckle on the sunlit ones (ARCH r8 tiles): say what each is (probe grid, clamp, fill) and fix
   what is one knob.
3. Hero holds: sunlit attic, shaded attic, reflection, sky boxes, columns hue as r16. Do not move the sun.
Deliverables: light_presets values, assets/lighting.blend, light_r17_sheet.png (cam02 + cam03 before / after tiles + hero hold table), §27 in the
notes with the acceptance table on your rebuilt master (object count), commits after every successful script, report with the last commit id.
