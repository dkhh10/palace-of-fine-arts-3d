MERGE WITH FIXES — the shipped rig and the acceptance numbers are sound; the defects are in the sweep's defaults, one mislabelled measurement, and stale docstrings.

Verified clean: no absolute paths, no file outside lighting's ownership, no tracked binary > 5 MB (max 3.3 MB), the new POWER nodes sit inside the
diffuse-only weight chain so camera/glossy rays are still excluded by construction, `hide_render` is now False everywhere for the Cycles fill
(`light_r14_acc.log:32,34,47`), `apply_final_cycles` / `common.configure_cycles` / `light_probes.bake` all call `apply_shade_for_engine`, the vault keeps
its own Eevee-only pattern untouched, the shadow settings are lamp *data* (saved in lighting.blend) so `apply_viewport_eevee` needs no change,
361.6 -> 229.9 s is arithmetic on `light_r14_acc.log:116`, and the step-4 gate quotes 1.42 gallery / 1.57 outside against `CLEAR_MIN_GALLERY` 1.35 in
`light_r14_check_step4_shipped.log:316` (307 samples = 1224/4). Stations now read from `qa_cameras` and match its locs; `st[5]` is fixed.

1. scripts/light_r14_sweep.py:99-100 — `tap=1.0, thp=1.0` are hard-coded, while every other sky key reads from `lb.`. Any future case that moves ONE sky
   key rebuilds the world at p=1/p=1 and silently un-ships r14. **fix now**: `tap=lb.SKY_DIFFUSE_TINT_ANTISUN_P, thp=lb.SKY_DIFFUSE_TINT_HORIZON_P`.
   (The r14 acceptance is unaffected: `r14SHIP` moved no sky key, so it reused the master's own world — but the case header still prints "ta 1^1 th 1^1"
   for it, `light_r14_acc.log:44`, which reads as if the exponents were off. Print the world's props, not the case keys.)
2. scripts/light_r14_sweep.py:92 — `fill=0.0` (Eevee) while `cfill=-1.0` now resolves to the shipped 70 W/m2. A case that forgets `fill=55` renders
   Cycles WITH the fill and Eevee WITHOUT it. **fix now**: default `fill=lb.SHADE_FILL["energy_eevee"]`.
3. docs/lighting_notes.md §24.3 — the water isolation pair is labelled "shipped (gb 5.25)" but `light_r14_w2.log:144,152` shows case `gb0` ran on
   tint 1,0.65,**17** at ta 1^1 th 1^1, i.e. the r13 sky. The acceptance table gives the same box +4.4 on the r14 sky, not +2.1. **fix now**: re-label the
   table as r13-sky, or re-run the pair on the shipped rig before materials r8 acts on the 2.3x hand-off.
4. No committed log holds any *measure* output: §24.7's whole acceptance table, §24.6's shade boxes and the "sky_top/sky_left identical" hold exist only in
   the notes (the r13 review raised the same thing about "bit-identical"). Frames and `light_r14_measure.py` are committed, so it reproduces. **fix now,
   cheap**: commit the `light_r14_measure` stdout as `renders/logs/light_r14_measure.log`.
5. scripts/light_probes.py:210 — the bake now runs the fill at the **Cycles** 70 W/m2 while Eevee renders it at 55 W direct, and the comment still reads
   "the Eevee shade fill is an engine hack, not real light". It is real light now. **carry**: fix the comment and state whether 70-in-the-bake /
   55-at-render is intended (§24.6 measures the result, so this is documentation, not a regression).
6. scripts/light_build.py:498-501 — `build_shade_fill`'s docstring still says "`energy` ... (0.0 as shipped)" and "the lamps ship `hide_render`". **carry**.
7. scripts/light_presets.py:169-175 — the `energy_W`-missing fallback seeds every lamp with `SHADE_FILL["energy"]` (70) instead of `energy * w`, so the
   NNE lamp would come back at 70 instead of 49. Harmless while the prop exists; now non-zero, so it matters. **carry**: multiply by `cfg["w"]`.
8. Comment arithmetic contradicts itself: light_build.py:141-146 says the wall keeps "4.8x at p = 10", light_calibrate.py:319-321 says "~4.7x at p = 3",
   and neither states p = 6, the shipped value. **carry**: one consistent table, at the shipped exponents.
9. 29 MB of new tracked PNGs (11 files); commit cac6ee1's "(17 -> 5 MB)" describes a re-encode, not the tracked total. Under the 5 MB/file bar, but the
   ten acceptance panels are per-round intermediates. **carry**: keep the sheet, drop the panels once QA has read them.
10. Two boxes are over-corrected past neutral (cam06 roofs hue 315.8, cam02 pier 3.8) and §24.7 flags them honestly — lead's call, not a code defect.
