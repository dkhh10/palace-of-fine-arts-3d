# Phase 9 viewer capture 2 — the round-2 specular gate on the re-baked assets (2026-09-21; no Blender, no deploy, no web/src edit)

Source: MAIN's `web/dist` (built 21 Sep 17:06 from main d1ac476+) served by `screenshot.mjs` with `/assets/*` -> MAIN's `export/out`
(`gate5/manifest.json` re-written 17:06, carries `sky.diffuse_lobes`, so the gate is ON by default — r2 review finding 5 is closed).
Four Chrome runs, all through `scripts/chrome_run.sh` (1500/900/900/1500 s), `pgrep -fl "MacOS/Blender|headless"` clear before each, bake queue
`idle`. **Hygiene: `find MAIN/export/out -newer <marker>` is empty — nothing written into MAIN's export/out.** Gate5 look query as the previous
window, 1920x1080 `--frames 0` desktop / 1170x2532 `?tier=mobile`. Luma = 0.2126R+0.7152G+0.0722B on the 8-bit frame; shade = Cycles luma < 64,
Cycles-sunlit = > 150 (the previous report's definitions). Sidecar `info.gate3.specGate`: **mode "r2"**, 40 lobes, openSkyB 5.824768,
skyRedOverBlue 0.37711, sunIrrOverPi 21.428439, zenithB 5.900423, floor 0.29502 — the re-baked constants, live. `pageErrors: []` on all four runs
(one 404, the favicon, as on every gate).

## Parity — viewer (gate ON) vs the NEW `cycles_p9` refs, and vs gate12 for the size of the whole Phase 9 change
| st | MAE whole % | outside shade % | Cycles-sunlit % | MAE vs gate12 % | p10 g12 / now / Cyc | mean g12 / now / Cyc |
|---|---|---|---|---|---|---|
| cam01 | 10.271 | 10.356 | 8.543 | 1.373 | 53.6 / 50.3 / 49.0 | 129.7 / 128.1 / 139.1 |
| cam02 | 6.272 | 4.846 | 2.894 | 2.936 | 25.6 / 25.9 / 19.6 | 104.0 / 100.5 / 97.5 |
| cam03 | 6.640 | 7.609 | 10.618 | 8.787 | 37.5 / 13.3 / 6.1 | 79.2 / 57.5 / 47.4 |
| cam04 | 3.173 | 3.781 | 5.390 | 3.327 | 28.7 / 20.5 / 20.9 | 70.6 / 62.8 / 62.5 |
| cam05 | 8.455 | 8.204 | 5.659 | 2.101 | 64.3 / 60.2 / 64.0 | 148.6 / 146.8 / 150.6 |
| cam06 | 7.625 | 7.608 | 6.722 | 1.756 | 71.9 / 67.1 / 64.1 | 100.8 / 98.6 / 98.6 |

These are the first absolute viewer-vs-Cycles numbers (round 1 measured viewer-vs-gate12 only), and they are **whole-frame, sky and water included**:
at cam01 the sky is 57.7 % of the pixels and carries 9.25 % MAE on its own (non-sky 11.67 %, frame median abs 5.75 %); at cam05 sky MAE is 3.74 %
against 11.98 % non-sky. p10 moves toward Cycles at cam04/05/06 and past it at cam01/02/03. Mobile `?tier=mobile` vs `gate12m_cam0N`, whole-frame
MAE: cam01 0.709, cam02 2.503, cam03 8.952, cam04 4.236, cam05 1.533, cam06 1.103 %.

## The specgate A/B at station 3 (near_column box, scene-linear through the delivery LUT) and the cam05 control
| cam03 | near_column linear RGB | vs Cycles (0.4879 0.2891 0.0000) | frame p10 | box p10 |
|---|---|---|---|---|
| `specgate=0` (Phase 8 path) | 0.9242 0.6375 0.2337 | R 1.89x G 2.21x, B +0.234 | 37.25 | 34.11 |
| `specgate=1` (round 1) | 0.6997 0.4275 0.0188 | R 1.43x G 1.48x, B +0.019 | 12.41 | 21.11 |
| `specgate=2` (round 2, shipped) | 0.7025 0.4288 0.0178 | R 1.44x G 1.48x, B +0.018 | 13.34 | 21.18 |
| Cycles p9 | 0.4879 0.2891 0.0000 | — | 6.13 | 9.34 |

**Round 2 is round 1 on this box**: near_column moves 0.4 % (R 0.6997 -> 0.7025), frame p10 12.41 -> 13.34. The per-normal lobes fixed the
*upward/attic* normals (r2 finding 9), not cam03's colonnade: the 1.44x red excess stands. **cam05 regression: reduced, not gone.** p10 `specgate=0`
68.38 / `specgate=2` 60.23 / Cycles 64.04 — the gate is **−5.9 %** of Cycles (budget ±3 %), the ungated path **+6.8 %**; neither passes, and the gate
overshoots down by about the amount the Phase 8 path overshoots up. Mean luma 149.88 / 146.76 / 150.63 (gate −2.6 %, ungated −0.5 %).

## Counters (identical on all four runs unless noted)
`far-tree impostor modulation: 166/166 placement(s) joined by location (0 unmatched), mode full, strength 1, clamp 4` — as expected.
`far-tree impostors: 131 placement(s) over 16 batch(es) now fade to a MESH (iNear = 1), 131 re-lit` desktop; **149 / 149 mobile** — both as expected.
One change from round 1 worth a line: `impostor irradiance modulation … 166 far + 0 near placement(s) modulated`, `impostors: 166/184 carry a
modulation`, where round 1 read 184/184 (166 far + 18 near). The belt rule now excludes the 18 near placements — expected if they draw as meshes,
but it is a counter QA 25 will see move. Gate3 lightmaps settle at 16/16 own maps, 988/988 instance slots, 0 materials cloned.

960 px copies of all 15 frames in `renders/web/960/p9s2*.jpg`; full-size PNGs left untracked in MAIN (`renders/web/*_cam0*.png` is gitignored).
No test suite run: capture only.
