# Phase 9 viewer captures — sets A, B, C (2026-09-20; one Chrome window, no Blender, no deploy, no web/src edit)
Assets: MAIN's deploy-12 `export/out` mirrored read-only (`find MAIN/export/out -newer` empty). A and C on that mirror (no constants -> gate OFF); B after `manifest_v4.py` + `tiers.py --no-pack`/`--mobile` in the worktree (sky `[2.195763, 3.432181, 11.255903]`, sun `21.42843`, t0 48.1 / 46.5 MB — the shade engineer's numbers). **Control:** local dist+mirror reproduce the deployed gate12 frames exactly (cam04 desktop and mobile MAE 0.0000, max 0), so every delta below is the change under test. 960 px copies in `renders/web/960/`; full-size gitignored (`p9v_*`/`p9vm_*` live in MAIN — `p9v_rim.py` hardcodes MAIN's `renders/web`). Modulation, both asset sets: **166/166 far joined (0 unmatched), mode full, 184/184 (166 far + 18 near) modulated**; belt rule not packed yet.

## A — cam03 flag frames, gate OFF (`?specgate=0`). Box `near_column (r17)`, linear RGB; Cycles (0.4880, 0.2897, 0.0000), frame p10 6.14.
| frame | near_column viewer | excess vs Cycles | frame p10 | box p10 |
|---|---|---|---|---|
| post=all (control) | 0.9402 0.6586 0.2398 | +0.4522 +0.3689 +0.2397 | 37.43 | 35.12 |
| post=none | 0.9522 0.6671 0.2432 | +0.4642 +0.3774 +0.2431 | 37.28 | 35.96 |
| probe=0 | 0.9402 0.6586 0.2398 | +0.4522 +0.3689 +0.2397 | 37.72 | 35.12 |
| lighting=direct | 2.7281 1.8085 1.7646 | +2.2392 +1.5182 +1.7646 | 64.59 | 61.63 |

**B.5 holds to the channel.** The control reproduces B.4's measured excess (0.452, 0.369, 0.240) to four decimals. Post on the near column is **−0.0120 R / −0.0085 G / −0.0034 B** — 2.7 % of the R excess, and it *darkens* (vignette over bloom): B.5's "~0" confirmed, not merely bounded. `probe=0` is **byte-identical** on the box, so the probe contributes exactly 0 there. Everything left is the specular path; Set B's gate then takes the blue 0.2398 -> 0.0089 (96.3 %), which is B.3's "the env specular carries all the blue". B.4's warm remainder is only **half** removed — see B.

## B — gate ON, six stations, 1920x1080. MAE vs `gate12_cam0N.png`; shade = Cycles luma < 64 (my definition, stated; no repo convention exists).
| st | MAE whole % | outside shade % | Cycles-sunlit (>150) % | p10 before / after / Cycles | mean luma before / after / Cycles |
|---|---|---|---|---|---|
| cam01 | 1.395 | 1.134 | 0.521 | 53.6 / 47.3 / 49.8 | 129.7 / 126.8 / 139.5 |
| cam02 | 1.835 | 0.666 | 0.248 | 25.6 / 22.8 / 20.4 | 104.0 / 99.5 / 98.9 |
| cam03 | 9.227 | 6.588 | 2.962 | **37.5 / 11.9 / 6.1** | 79.3 / 56.5 / 47.8 |
| cam04 | 3.506 | 1.594 | 1.358 | 28.7 / 19.3 / 21.4 | 70.6 / 61.6 / 63.1 |
| cam05 | 2.081 | 1.911 | 0.903 | **64.3 / 55.2 / 64.9** | 148.6 / 144.5 / 151.1 |
| cam06 | 1.243 | 1.195 | 1.659 | 72.0 / 65.3 / 64.8 | 100.8 / 98.0 / 100.7 |

cam03 `near_column` **(0.9402, 0.6586, 0.2398) -> (0.7079, 0.4402, 0.0089)** vs Cycles (0.4880, 0.2897, 0.0000): R **1.93x -> 1.45x**, G 2.27x -> 1.52x, B closed. `p9s_cam03_specgate0` vs `gate12_cam03` is **0.0093 % MAE**, so the re-run manifest is neutral and the 9.227 % is the gate alone. **Three findings.** (1) B.6 predicted ~(0.51, 0.31, 0.02) = **1.05x**; shipped lands at **1.45x** — 51 % of the R excess removed, 96 % of the B, not ~97 % of both. (2) **The 0.5 % parity budget outside shade is met at no station** (0.67–6.59 %); in the Cycles-sunlit band it is 0.25–2.96 %, over budget at cam03/04/05/06. (3) **cam05 regresses**: p10 was 64.3 against the reference's 64.9 and is now 55.2, and its mean luma moves away from Cycles — the gate darkens the two most sunlit stations (cam01 56 %, cam05 60 % sunlit pixels), which did not need it. cam02/03/04/06 move toward Cycles on both p10 and mean.

## C — the dotted rim (`?impq=`, default on). ONE rim mask taken from gate12 and applied unchanged to both sides.
| box | rim px | chk gate12 | chk p9v | MAE/255 in box |
|---|---|---|---|---|
| 05 left crown (sky behind) | 2330 | 0.264 | **0.041** | 0.949 |
| 02 right cypress (sky behind) | 1710 | 0.369 | **0.079** | 0.499 |
| 01 hero crown (building behind, control) | 2998 | 0.080 | 0.030 | 0.428 |

Whole-frame MAE vs gate12, desktop: cam01 **0.036** / cam02 0.075 / cam03 0.009 / cam04 **0.000** / cam05 0.040 / cam06 0.029 % — all inside the 0.5 % rule. `?tier=mobile` (1170x2532) vs `gate12m_cam0N.png`: 0.021 / 0.043 / 0.001 / **0.000** / 0.034 / 0.048 % — byte-identity does break at five of six stations, as the branch predicted, and every station is inside the rule. **Carry 10 closes:** `p8_atlas_probe.py viewer gate12 p9v --stations 1` gives crossings/100 px **11.68 -> 11.66** (Cycles 11.73), foliage share 16.57 % both sides, box p10 33.7 both sides — the discard-boundary move is below the measure's noise at the hero.

**Hygiene.** One tool write (`p8_atlas_probe`'s sidecar) reached MAIN's `export/out/p8` through a directory symlink; removed, mirror re-made per-file, `find -newer` empty again (only that directory's mtime moved, no file content). `pgrep` checked clear before each of the five Chrome runs; every run through `scripts/chrome_run.sh`. No test suite run: capture only.
