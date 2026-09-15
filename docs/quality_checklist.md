# Quality checklist (maintained by QA / Critic)

Score each canonical viewpoint 0-5 per criterion after every round. Target: every viewpoint >= 4 on every row,
hero (cam_01) >= 4.5 average. Anything that reads as "game asset" or "clean CAD" is a reject regardless of score.

| Criterion | What 5 means |
|---|---|
| Silhouette match | Overlay of render on reference photo: dome, drum, attic, entablature, column edges align within ~2% of frame height. |
| Proportion | Vertical stack (pedestal / column / entablature / attic / drum / dome) and octagon width match measured ratios. |
| Ornament fidelity | Capitals, frieze, maidens, urns, rosettes recognisable as the PFA's specific ornament, not generic classical. |
| Material realism | Concrete reads as cast, weathered, variegated ochre; columns dusty terracotta; no plastic sheen, no flat color. |
| Edge wear | Corners softened, rain streaks, algae line at water, patches, dust in recesses. Visible at hero distance. |
| Lighting mood | Low warm sun, long soft-edged shadows, sky-lit blue shade, warm haze in the distance, no crushed blacks. |
| Water reflection | Reflection broken by ripples, green-tinted murk, Fresnel falloff, correct brightness vs. sky. |
| Repetition visibility | No two ornament instances identical at hero distance; no visible tiling in materials. |
| Scale cues | Trees, shrubs, birds, railings, steps at believable sizes; nothing reads as miniature or giant. |

Also reported every round (not scored 0-5, pass/fail against the brief's Phase 5 deliverables): **Viewport performance**
(master.blend open time < 60 s, viewport LOD1 triangle count, Eevee preview seconds per QA camera) and **Deliverables present**
(Cycles final config, Eevee viewport config, flythrough bezier path `CAM_flythrough_path`; at Phase 5 also the 3840x2160 Cycles
hero and the low-res Eevee test animation).


## Gate checks added 2026-09-10 (binding from round 10)
- Name sweep (`scripts/qa_name_sweep.py`): exceptions on record — `ARCH_rotunda_inner_block_NN` / `_cap_NN` (the real inner piers,
  arch_params INNER_BLOCK), `ENV_backdrop_fill_NNN` / `_fillroof_NNN` (city backdrop blocks, env_city.py). Anything else is a blocker.
- Exception added round 10: **`LIGHT_shade_fill_00`** — a LIGHT, not geometry: the az-25 el-2 blue sun lamp that has stood in for
  sky-shade since round 14 (`light_build.SHADE_FILL`, 49.0 W Cycles / 38.5 Eevee). The exception covers the *name*; the lamp is the
  measured source of the hero's magenta arch jamb (QA-10-2, hue 338.5), which stays open as a defect.
- Six-tile 100 % hero review before scoring; every visible defect is a defect. The v1 hero (round 09, 3.67) shipped with the main arch's upper
  half filled by 67 chord triangles of `ARCH_rotunda_vault_coffers_00` (7-11 m2 each, normals along the bay axis) that no metric caught
  and the 960 px composite hid: that is the case this rule exists for.
- Ray-cast opening test on every arch in view (CLAUDE.md).

## Round log
(QA appends a dated section per round: scores table per camera, defects with camera id and measurable fix.)

### Round 01 — 2026-09-07 (Phase 2 gate; materials still placeholders)

Full report: `docs/qa_round_01.md`. Evidence: `renders/qa_comparisons/round01_*` (per-camera three-panel sheets, contact sheet,
Cycles hero vs ref 169, and the new W_a-aligned overlays `round01_cam01_aligned_vs_ref169.png` / `_vs_user.png`).
Renders: `renders/previews/qa/round01_*` (Eevee 1280x720 x6, Cycles 1920x1080 hero, 65 s).

| row | cam01 | cam02 | cam03 | cam04 | cam05 | cam06 |
|---|---|---|---|---|---|---|
| Silhouette match | 3 | 1 | 1.5 | 4 | 1.5 | 3 |
| Proportion | 3 | 3 | 3.5 | 4 | 3.5 | 3.5 |
| Ornament fidelity | 3 | 3 | 3 | 2.5 | 2.5 | 3 |
| Material realism | 1 | 1 | 1 | 1 | 1 | 1 |
| Edge wear | 0 | 0 | 0 | 0 | 0 | 0 |
| Lighting mood | 3.5 | 3 | 3 | 1 | 3 | 2.5 |
| Water reflection | 1 | n/a | 1 | n/a | 1 | 1.5 |
| Repetition visibility | 2 | 3 | 2 | 3 | 2 | 2 |
| Scale cues | 3 | 2 | 3 | 3 | 2.5 | 3 |
| average | 2.2 | 2.0 | 2.0 | 2.3 | 1.9 | 2.2 |

Verdict: gate not passed for photorealism (no materials yet), but the rotunda body is right: with attic width and corner row
aligned, pedestal-to-attic-cornice edges sit within ~1-2 % of frame height of refs 169 and the user image.

Blockers: **QA-01-1** dome + drum too low/flat (visible rise 0.161 W_a vs 0.195-0.30 in five photos; apex 6.3 % of frame height
low vs ref 169; owner architecture, lead arbitrates vs the sheet's 49.4 m apex). **QA-01-2** shoreline shrubs are polygon slabs
(environment). **QA-01-3** water is a flat brown mirror (materials + environment).
Majors: QA-01-4 hero framing (shoreline at 86 % frame height vs 69 % / 53 %; lead), QA-01-5 cams 02/03/05 miscalibrated (lead),
QA-01-6 tree placement + missing redwood screen (environment), QA-01-7 leaf cards (environment), QA-01-8 hall backdrop box in
the hero arch (environment), QA-01-9 Eevee ceiling 4x too dark, no light probes (lighting), QA-01-10 Zimm panels ~15 % figure
coverage vs ~70 % (ornament), QA-01-11 podium Greek-key band missing (ornament + architecture), QA-01-17 placeholders (materials,
expected).
Minors: QA-01-12..16, 18..20 (see report).

Tools added: `scripts/qa_render_round.py` (round renderer, `--eevee` / `--final`), `scripts/qa_silhouette.py`
(silhouette measure + W_a-aligned overlay; use it for the 2 % silhouette test).

### Round 02 — 2026-09-07 (Phase 3 gate; first round with the real materials library)

Full report: `docs/qa_round_02.md`. **Gate composite: `renders/qa_comparisons/round02_gate.png`** (Cycles hero beside
ref 169, the six Eevee views, and the score deltas burnt in). Evidence: `renders/qa_comparisons/round02_cam0K.png`,
`round02_sheet.png`, `round02_cam01_aligned_vs_ref169 / _vs_ref085 / _vs_user.png`.
Renders: `renders/previews/qa/round02_*` (Eevee 1280x720 x6: 46.3 / 45.4 / 36.7 / 33.6 / 54.8 / 32.8 s;
Cycles hero 1920x1080 128 spp: 446 s).

| row | cam01 | cam02 | cam03 | cam04 | cam05 | cam06 |
|---|---|---|---|---|---|---|
| Silhouette match | 4 | 2 | 1.5 | 3.5 | 2 | 4 |
| Proportion | 3.5 | 3 | 3 | 3.5 | 3 | 3.5 |
| Ornament fidelity | 3 | 2.5 | 2.5 | 1.5 | 2 | 2.5 |
| Material realism | 2.5 | 2 | 2 | 2 | 2 | 1.5 |
| Edge wear | 1 | 1 | 1 | 0.5 | 1 | 0.5 |
| Lighting mood | 3.5 | 2.5 | 2 | 3 | 3 | 2 |
| Water reflection | 3 | 2 | n/a | n/a | 2 | 1.5 |
| Repetition visibility | 2.5 | 2 | 2 | 2 | 2 | 2 |
| Scale cues | 3.5 | 2 | 1.5 | 2.5 | 2 | 2 |
| average (delta vs round 01) | 2.94 (+0.78) | 2.11 (+0.11) | 1.94 (-0.06) | 2.31 (0.00) | 2.11 (+0.22) | 2.17 (0.00) |

**Viewport performance**: master.blend opens in **1.8 s** headless (budget 60 s, pass); LOD1 **15.18 M tris**
(62.0 M over all LODs, 6043 objects); Eevee 1280x720 previews **33-55 s per camera**, 2-7x slower than round 01;
Cycles 1080p/128 spp 65 s -> 446 s.
**Deliverables present**: Cycles final config pass (GPU, 768 spp adaptive, OIDN — but the saved file's own
`cycles.device` is CPU); Eevee viewport config pass (taa 16/32, raytracing, AgX Base Contrast, 2 baked irradiance
volumes); **`CAM_flythrough_path` FAIL — no curve objects in master.blend at all** (QA-02-11).

Verdict: **gate not passed.** Real progress — dome apex now within 1.3 % of ref 169 (was 6.3 %), hero framing fixed,
water believable, ceiling lit, zero placeholder materials — but at 1:1 the stone still reads as clean CAD with decals
and there is effectively no edge wear in the build, the exact failure of attempts 1-2.
Blockers: **QA-02-1** dome reads absent from cam05 (3.7 % vs 12.2 % of rotunda width, architecture); **QA-02-2** blotchy
decal stone, olive cast, per-instance *hue* variation (materials); **QA-02-3** no edge wear and no algae/waterline band
anywhere (materials); **QA-02-4** exposure 0.9 EV under ref 169, measured against the AgX response (lighting).
Majors: QA-02-5 cam03 framing (lead), -6 lagoon tonal range, -7 colonnades buried in trees (environment), -8 haze too
dense and olive (lighting), -9 relief reads as decal, -10 corner figures/scrolls (ornament), -11 flythrough path missing
(lead), -12 vault soffits light-starved (lighting). Minors: QA-02-13..18.

Tools added: `scripts/qa_measure.py` (regions / waterline / EV delta), `scripts/qa_exposure_sweep.py` (measured AgX
exposure response), `scripts/qa_gate_sheet.py` (gate composite). `scripts/qa_silhouette.py`'s building mask changed from
"warm pixels" to "not sky and not foliage" so a pale cream dome cap is no longer lost (`--mask warm` restores round 01).

### Round 03 — 2026-09-07 (Phase 4 polish round 1; all five owners' p4r1 merged, cam03/cam05 re-stationed, Eevee at LOD1)

Full report: `docs/qa_round_03.md`. **Gate composite: `renders/qa_comparisons/round03_gate.png`.** Evidence:
`renders/qa_comparisons/round03_cam0K.png`, `round03_sheet.png`, `round03_cam01_aligned_vs_ref169 / _vs_ref085 / _vs_user.png`,
`round03_cam01_crops_vs_ref169.png` (1:1 crop pairs with the boxes and numbers burnt in).
Renders: `renders/previews/qa/round03_*` (Eevee 1280x720 LOD1 x6: 36.4 / 38.1 / 52.9 / 33.3 / 35.0 / 25.3 s on a quiet machine;
Cycles hero 1920x1080 128 spp capped at 270 s of sampling: 277 s; Cycles cam04 64 spp capped at 180 s: 251 s).

| row | cam01 | cam02 | cam03 | cam04 | cam05 | cam06 |
|---|---|---|---|---|---|---|
| Silhouette match | 4 | 2 | 2.5 | 3.5 | 3 | 4 |
| Proportion | 4 | 3 | 3 | 3.5 | 3 | 3.5 |
| Ornament fidelity | 3 | 2.5 | 2.5 | 1.5 | 3 | 2.5 |
| Material realism | 3 | 2.5 | 1.5 | 1.5 | 2.5 | 1.5 |
| Edge wear | 1.5 | 1 | 0.5 | 0.5 | 1.5 | 0.5 |
| Lighting mood | 4 | 3 | 2.5 | 2 | 3.5 | 2 |
| Water reflection | 3.5 | 2.5 | n/a | n/a | 2.5 | 1.5 |
| Repetition visibility | 3 | 2 | 2 | 2 | 2.5 | 2 |
| Scale cues | 3.5 | 2.5 | 2.5 | 2.5 | 2.5 | 2 |
| average (delta vs round 02) | 3.28 (+0.34) | 2.33 (+0.22) | 2.13 (+0.19) | 2.13 (-0.19) | 2.67 (+0.56) | 2.17 (0.00) |

**Viewport performance**: open **0.96 s** (pass); LOD1 **11.62 M tris** (down from 15.18 M with 9041 objects, pass); Eevee 25-53 s per
camera at LOD1 (was 33-55 s at LOD0). **Deliverables**: `CAM_flythrough_path` + camera + target present (QA-02-11 closed); Eevee config
pass; Cycles config pass via `apply_final_cycles` but the *saved* file has device CPU / 4096 spp / AgX Base Contrast (QA-03-17).
**Infrastructure**: `scripts/blender_watchdog.sh` killed two GPU Cycles renders (CPU-time criterion; Metal renders show no CPU
progress) — QA-03-1, blocker for the 4K deliverable.

Verdict: **gate not passed.** Hero +0.34 (best single-round gain since round 01): exposure closed at the AgX response (attic 0.94 of
ref 169), blotch/olive stone closed, lagoon tonal range closed (flank 1.13), silhouette within 1.0 / 0.6 / 0.5 % of three photos, cam05
now shows the dome. Still failing the photoreal bar: at 1:1 the hero stone is a uniform clean ochre with **no flutes, no streaks, no
recess dirt** (QA-03-4), sunlit chroma **6.4 deg cool, sat 0.43 vs 0.59, R-B 92 vs 138** at delivery resolution (QA-03-2; the 960x540
sweep was ~20 R-B optimistic, as lighting warned), columns 1.54x too bright, interior fills ~2x in both engines (soffit/sky 0.80 Eevee /
0.70 Cycles vs 0.405; coffer/sky 1.04 / 1.00 vs 0.437; QA-03-3).
Near-water dispute settled with one crop: hero (1150 1000 1450 1050) vs ref 169 raw (1103 863 1332 901): render sat 0.382 hue 206 vs ref
sat 0.269 hue 192 (QA-03-7). QA-02-1 closed by camera only: at the new cam05 the render shows >= 19.5 % rise vs ref 063's 7.0 % and the
apex is clipped by the frame top (QA-03-5). QA-02-17: re-point cam02 to land (~(-40, 15, 1.4), 18 mm), keep ref 062 (QA-03-6).
Blockers: QA-03-1 watchdog vs GPU renders (lead), -2 chroma (lighting + materials), -3 interior fills 2x (lighting), -4 clean-CAD stone /
missing flutes at 1:1 (materials + architecture). Majors: -5 cam05 apex clipped (lead), -6 cam02 station (lead), -7 near-water sat and
ripple scale (materials), -8 flat coffers (ornament + architecture), -9 cam03 near shaft unfluted / crushed / flat ground (materials +
architecture + environment), -10 north wing dark (environment), -11 cam06 backdrop 1.04:1 (environment + lighting). Minors: -12..-17.

Tools added: `scripts/qa_crops.py` (matched crop pairs through the align transform, stats burnt in), `scripts/qa_inspect.py`
(deliverables / perf inspection, read-only). `qa_gate_sheet.py` takes `--round NN` for any round (SCORES table per round).

### Round 04 — 2026-09-08 (Phase 4 polish round 2; lighting r09/r10, arch p4r2 + sockets, materials r4/r5, env r4/r5, ornament r4; cam02 re-stationed by QA)

Full report: `docs/qa_round_04.md`. **Gate composite: `renders/qa_comparisons/round04_gate.png`.** Evidence:
`renders/qa_comparisons/round04_cam0K.png`, `round04_sheet.png`, `round04_cam01_aligned_vs_ref169.png` (scale 1.3113 / dx -292.0 / dy -126.3),
`round04_cam01_crops_vs_ref169.png` (1:1 crop pairs with boxes and numbers burnt in).
Renders: `renders/previews/qa/round04_*` (Eevee 1280x720 LOD1 x6: 17.3 / 24.3 / 21.4 / 16.3 / 16.2 / 11.5 s, quiet machine; Cycles hero
1920x1080 128 spp **uncapped**: 335 s; Cycles cam04 64 spp 1280x720: 211 s). Watchdog no longer kills GPU renders (QA-03-1 closed).

| row | cam01 | cam02 | cam03 | cam04 | cam05 | cam06 |
|---|---|---|---|---|---|---|
| Silhouette match | 4 | 3.5 | 2.5 | 3.5 | 3.5 | 4 |
| Proportion | 4 | 3.5 | 3 | 3.5 | 3 | 3.5 |
| Ornament fidelity | 3.5 | 3 | 2.5 | 3 | 3 | 2.5 |
| Material realism | 3 | 2.5 | 1.5 | 1.5 | 2.5 | 2 |
| Edge wear | 1.5 | 1 | 0.5 | 0.5 | 1.5 | 0.5 |
| Lighting mood | 4 | 3 | 1.5 | 2 | 3.5 | 2.5 |
| Water reflection | 3.5 | 2 | n/a | n/a | 2.5 | 2 |
| Repetition visibility | 3 | 2.5 | 2 | 2.5 | 2.5 | 2 |
| Scale cues | 3 | 3 | 2.5 | 3 | 2.5 | 2.5 |
| average (delta vs round 03) | 3.28 (0.00) | 2.67 (+0.33) | 2.00 (-0.12) | 2.44 (+0.31) | 2.72 (+0.06) | 2.39 (+0.22) |

**Viewport performance**: open **0.69 s** (pass); LOD1 **10.95 M tris** (pass); Eevee 11.5-24.3 s per camera at LOD1 (was 25-53 s).
**Deliverables**: saved master carries GPU / 768 adaptive / OIDN / AgX High Contrast / exposure -2.833 and `CAM_flythrough` + path + target
(QA-03-17 closed); saved Eevee state is taa 8/16 with raytracing off (was 16/32 on; QA-04-12); **Eevee ceiling black** (QA-04-1).

Verdict: **gate not passed.** Closed by number: attic chroma (hue 38.9 / sat 0.554 / R-B 122 / lum 180 vs ref 40.3 / 0.588 / 136 / 190),
hero flutes (5 cycles >= 10 % on the front shaft = ref), capitals as leaf tiers, coffers as real boxes, cam05 foliage 0 %, near-water sat
0.272, watchdog, saved preset, cam02 on land (SSE shore path (70.5, 25.6, 1.1) / 24 mm; top 0.02, base 0.86, width 0.44 vs 0.48). Hero
average unchanged at 3.28: the shoreline became a bare quay with dot shrubs (scale cues -0.5). Regressions: Eevee coffer / sky **0.035**
(Cycles 0.26, ref 0.44); cam03 near shaft **0.10** of ref (was 0.33); shaded stone hue 43 vs 29.5; south wing 0.63 (was 0.77); columns
still 1.27x. Stone at 1:1 remains streak-free with std 0.55 / 0.54 of the photo's (third round of the same finding).
Blockers: QA-04-1 Eevee vault black (lighting), -2 shade collapsed / yellow-green (lighting), -3 clean-CAD stone: no streak, no waterline
band (materials). Majors: -4 bare shoreline (environment), -5 columns bright / yellow (lighting + materials), -6 wings dark (lighting +
environment), -7 Cycles coffers 0.26 and CAD ceiling (lighting + materials), -8 near-water hue 209 / grey reflection (environment +
materials). Minors: -9 haze band, -10 cam05 apex 1.4 %, -11 ref 062 station unreproducible on the build's proportions (architecture +
lead), -12 saved Eevee state, -13 cam06 far field, -14 cam02 foreground water.

Tools added: `scripts/qa_cam02_probe.py` (on-land station sweep with visible-top framing solve, ray-cast occlusion, low-cost renders),
`scripts/qa_4k_probe.py` (4K compositor off/on timing). `qa_render_round.py` now always rebuilds the QA cameras from `qa_cameras.py`.

### Round 05 — 2026-09-08 (Phase 4 polish round 3; lighting r11, materials r6, environment r6 + follow-up, architecture mini-round; probes baked on the physical rig)

Full report: `docs/qa_round_05.md`. **Gate composite: `renders/qa_comparisons/round05_gate.png`.** Evidence:
`renders/qa_comparisons/round05_cam0K.png`, `round05_cam01_cycles.png`, `round05_sheet.png`, `round05_cam01_aligned_vs_ref169.png` (raw ref 169: scale
1.3108 / dx -291.8 / dy -124.6, round-04 boxes valid within 2 px), `round05_cam01_crops_vs_ref169.png` (1:1 crop pairs with numbers burnt in).
Renders: `renders/previews/qa/round05_*` (Eevee 1280x720 LOD1 x6: 22.7 / 22.2 / 23.6 / 18.7 / 18.0 / 12.7 s, quiet machine; Cycles hero
1920x1080 128 spp **uncapped**: 355.8 s; Cycles cam04 64 spp 1280x720: 219.1 s).

| row | cam01 | cam02 | cam03 | cam04 | cam05 | cam06 |
|---|---|---|---|---|---|---|
| Silhouette match | 4 | 3.5 | 2.5 | 3.5 | 3.5 | 4 |
| Proportion | 4 | 3.5 | 3 | 3.5 | 3 | 3.5 |
| Ornament fidelity | 3.5 | 3 | 2 | 3 | 3 | 2.5 |
| Material realism | 3 | 2.5 | 1 | 2 | 2.5 | 2 |
| Edge wear | 2 | 1.5 | 0.5 | 1 | 1.5 | 0.5 |
| Lighting mood | 3.5 | 3 | 1 | 2 | 3.5 | 3 |
| Water reflection | 3 | 2.5 | n/a | n/a | 2.5 | 2 |
| Repetition visibility | 3 | 2.5 | 2 | 2.5 | 2.5 | 2.5 |
| Scale cues | 3.5 | 3 | 2 | 3 | 3 | 2.5 |
| average (delta vs round 04) | 3.28 (0.00) | 2.78 (+0.11) | 1.75 (-0.25) | 2.56 (+0.12) | 2.78 (+0.06) | 2.50 (+0.11) |

Trend r02 -> r05: cam01 2.94 / 3.28 / 3.28 / 3.28 (**stuck**; Material 3, Repetition 3 three rounds); cam02 2.11 / 2.33 / 2.67 / 2.78 (slow up);
cam03 1.94 / 2.13 / 2.00 / 1.75 (**declining**; shade 23 -> 7 -> 5.5); cam04 2.31 / 2.13 / 2.44 / 2.56 (flat; Lighting 2 three rounds);
cam05 2.11 / 2.67 / 2.72 / 2.78 (flat since r03); cam06 2.17 / 2.17 / 2.39 / 2.50 (slow up).

**Viewport performance**: open **0.72 s** (pass); LOD1 **11.01 M tris** (pass); Eevee 12.7-23.6 s per camera at LOD1 (pass).
**Deliverables**: GPU / 768 adaptive / OIDN / AgX High Contrast / exposure -2.833, flythrough camera + path + target, Eevee taa 8/16 RT off
logged (QA-04-12 closed); Eevee ceiling dim but readable (coffer / sky 0.16, was 0.035).

Verdict: **gate not passed.** Closed by number: hero shoreline (pale-stone 36.5 -> 7.1 %, base hidden 97 %, willow, 2-4 m mounds), columns
(95.9 vs 95.8, hue 27.8), north wing 0.94, attic std 0.66, cam05 apex 3.75 %, cam06 contrast 2.07:1, cam02 foreground, ref 062 station
documented, Eevee vault no longer black (0.16). Hero average **3.28 for the third round**: scale cues +0.5 and edge wear +0.5 paid for by
lighting -0.5 (sunlit attic 166.5, window 178-201; shaded stone sat 0.82) and water -0.5 (reflection sat 0.106, was 0.146). Not reproduced on
the merged master: lighting's Cycles coffer 0.387 (measures **0.21**, down from 0.26), materials' near-water hue 204 (208.9).
Rejects (game asset / decal): hero stone is an isotropic dirt blotch (streak anisotropy 0.64 vs photo 4.07, crops pane 1); cam04 coffers are
black holes with lit rims (dark / light quarter 0.121 vs 0.265); cam03 80 % black (shaft 0.063 of the sunlit stone, ref-169 anchor 0.61);
near water a flat blue plane (hue 209).
cam03 shade test re-based: shade-vs-sunlit ratio inside the cam03 frame, window 0.30-0.70 anchored on ref 169 (0.607); ref 128's absolute
69.7 retired. Labels fixed: frame-left of the hero is the SOUTH wing.
Blockers: QA-05-1 shade crushed (lighting), -2 stone as dark isotropic decal (materials), -3 Cycles coffers 0.21 / black floors (lighting +
materials, integration). Majors: -4 water hue 209 / grey reflection (materials + environment), -5 south wing 0.63 (lighting + environment),
-6 entablature cornice / dentil shadow (architecture). Minors: -7 haze band, -8 cam06 no streets, -9 Eevee soffit W gap 0.22, -10 shore band
dark (0.63 of photo), -11 cam03 ground bare, -12 cam05 flat stone at 110 m.
Recommendation to the lead: change approach for the hero-facing concrete (photo-projected albedo from the aligned refs); measure every
owner's acceptance number on the lead's post-build master, not the owner's branch.

### Round 06 — 2026-09-09 (Phase 4 polish round 4; ARCH r4, LIGHT r12 + r13, MAT r7, ENV r7 + r8 + paving rebuild; master 9709 objects, LOD1 11.11 M)

Full report: `docs/qa_round_06.md`. Gate composite: `renders/qa_comparisons/round06_gate.png`.

| row | 01 hero | 02 NE 3/4 | 03 colonnade | 04 ceiling | 05 S lawn | 06 aerial |
|---|---|---|---|---|---|---|
| Silhouette match | 4 | 3.5 | 2.5 | 3.5 | 3.5 | 4 |
| Proportion | 3.5 | 3.5 | 3 | 3.5 | 3 | 3.5 |
| Ornament fidelity | 3.5 | 3 | 2.5 | 3 | 3 | 2.5 |
| Material realism | 3 | 2.5 | 1.5 | 2.5 | 3 | 1.5 |
| Edge wear | 2.5 | 2 | 1 | 1 | 2 | 0.5 |
| Lighting mood | 4 | 3 | 2 | 3 | 3.5 | 2 |
| Water reflection | 2 | 1.5 | n/a | n/a | 1.5 | 1.5 |
| Repetition visibility | 3 | 2.5 | 2 | 2.5 | 2.5 | 2.5 |
| Scale cues | 3.5 | 3 | 2.5 | 3 | 3 | 2.5 |
| average (delta vs round 05) | 3.22 (-0.06) | 2.72 (-0.06) | 2.12 (+0.38) | 2.75 (+0.19) | 2.78 (0.00) | 2.28 (-0.22) |

Trend r02 -> r06: cam01 2.94 / 3.28 / 3.28 / 3.28 / **3.22** (stuck four rounds; hero Proportion re-scored 4 -> 3.5 on the
first per-course stack measurement, so 3.28 flat on the round-05 basis); cam02 2.11 / 2.33 / 2.67 / 2.78 / **2.72**;
cam03 1.94 / 2.13 / 2.00 / 1.75 / **2.12** (first gain in three rounds); cam04 2.31 / 2.13 / 2.44 / 2.56 / **2.75** (best);
cam05 2.11 / 2.67 / 2.72 / 2.78 / **2.78**; cam06 2.17 / 2.17 / 2.39 / 2.50 / **2.28** (blue flood).

**Viewport performance**: open **0.72 s** (pass); LOD1 **11.11 M tris** (pass); Eevee six-camera pass **218.6 s**, 22.7-49.7 s
per camera — pass but **+81 %** on round 05 (LIGHT r13's Eevee-only rigs); Cycles hero 128 spp 381.4 s; cam04 64 spp 219.9 s.
**Deliverables**: GPU / 768 adaptive / OIDN / AgX High Contrast / exposure -2.8331, flythrough camera + path + target,
2 light probes, Eevee taa 8/16 RT off, 0 placeholder materials. 4K 768-spp timing not run this round (QA-03-16 still open).

Closed this round: QA-05-3 coffers (Cycles 0.211 -> **0.451**, ref 0.437; dark/light quarter 0.121 -> **0.234**, ref 0.265),
QA-05-7 haze (0.922 vs the aligned ref's 0.921 — measured-equal), QA-05-10 shore band (71.7 -> **91.6**, ref 115.3),
QA-05-11 cam03 walk, QA-05-12 cam05 stone (band std **0.92** of ref 063). Half closed: QA-05-1 (hero shaded attic
**114.7 / 30.7 / 0.373** vs ref 115.0 / 29.5 / 0.425 — exact; cam03 re-based box 480 150 560 600 gives **0.384** of the
sunlit rotunda, in the 0.30-0.70 window, but at sat 0.737), QA-05-2 (attic lum **180.4** in window, std ratio 0.73;
sat 0.473 and anisotropy **0.41** vs 4.07 still fail), QA-05-5 (south wing 86.0 -> **94.2**: raw pass, aligned fail),
QA-05-6 (entablature texture std **0.81** pass, row std 36.5 vs the photo's 54.0 fail). Regressed: QA-05-4 water
(reflection sat 0.106 -> **0.043**, R-B **+2.5** vs +69.0).

cam03 test re-based a second time (brief item 4 / decisions.md): the box moves to a sky-visible shaft face,
**480 150 560 600**, window 0.30-0.70 anchored on ref 169's 0.607; the old box 150 150 420 720 (now 0.151) is retired and
the outer lagoon-side row 880 120 1200 600 (0.066) is reported for the record. Wing labels confirmed: frame-left = SOUTH.
Reflection test re-stated (brief item 8): saturation is dropped, **R-B >= +35 and hue 25-45 and lum 124-208** on
900 760 1020 840 — blue water passed the old sat >= 0.25 test.

Rejects (game asset / clean CAD): the hero's capitals and the ornamented band above them (24 px vs the photo's 37, blank
bed-mould, frieze and archivolt); cam06 as a lavender relief map (roofs / ground / trees at hue 253 / 269 / 240 against
ref 105's 2.7 / 51.2); the cam05 lagoon (lum 120.3 / hue 5.9 / sat 0.123 vs 93.4 / 64.9 / 0.306); the attic's weathering
still organised in rows, not runs (anisotropy 0.41 vs 4.07).

**Stack offset per course (new, item 7)**: attic crown +0.07 m, crown corona +0.30, attic panel frame top +1.27, frame
bottom +2.31, cornice corona +2.01, frieze top +1.34, frieze bottom +1.34, capital top +1.12 (positive = the render sits
higher; 13.42 px/m). Attic storey render / ref **0.70**, capital **0.65**, frieze **1.00**. **Not a rigid shift, so the
photo-projection pass cannot register until architecture closes the stack (QA-06-1).**

Verdict: **gate not passed.** Hero **3.22** (3.28 on the round-05 basis) — no gain for a fourth round: Lighting +0.5 and
Edge wear +0.5 paid for by Water -1.0. Blockers: QA-06-1 stack does not register (architecture), QA-06-2 diffuse sky tint
floods four cameras blue-violet (lighting), QA-06-3 water fails at every distance (materials). Majors: -4 streak direction,
-5 sunlit chroma, -6 capitals / ornament band, -7 cam03 still 46 % black, -8 vault saturation 0.91 vs 0.43, -9 entablature
row std. Minors: -10 Eevee soffit W gap, -11 south wing aligned panel, -12 cam06 streets, -13 Eevee preview cost +81 %.
Recommendation to the lead: one architecture round on the hero-facing stack **before** the photo-projection pass, and a
hold-list of the other five cameras' boxes in every lighting / materials brief from round 07 on.

## Round 07 (2026-09-09) — polish round 5 gate: ARCH r6+r7, ORN r6+r7, LIGHT r14, MAT r8, ENV r9

Scores (r06 -> r07): hero **3.22 -> 3.44 (+0.22)**, cam02 2.72 -> **3.06**, cam03 2.12 -> **2.25**, cam04 2.75 -> **2.88**,
cam05 2.78 -> **3.00**, cam06 2.28 -> **2.50**. First round in which every camera gained, and the first hero gain in five.

Closed this round: **QA-06-1** stack (all eight courses within **5 rows / 0.37 m**, attic storey 100 vs 101 rows, capital
35 vs 30 — was 0.70 / 0.65), **QA-06-4** weathering (anisotropy 0.41 -> **3.12**, photo 4.08; under-cornice run-off
**19.2 % = the photo's 19.2 %**), **QA-06-8** vault (coffer sat 0.914 -> **0.467**, ref 0.427), **QA-06-9** entablature
(row std 36.5 -> **44.0**, test 40), **QA-06-11** south wing (94.2 -> **104.2**, test 103), **QA-06-13** Eevee cost
(218.6 -> **146.1 s**, test 150). Half closed: **QA-06-2** (cam06 plaza / trees hue 269 / 240 -> **33.3 / 32.6**, cam02
water 265 -> 43.5; cam03 walk still 195.6), **QA-06-3** (reflection R-B +2.5 -> **+36.4** at hue 36.5, cam05 sat 0.244;
lum 105.6 and the open lagoon fail), **QA-06-6** (capital alternation **20 maxima vs the photo's 17** at 0.95 of its
contrast; archivolt still blank), **QA-06-7** (cam03 black 46.1 -> **28.0 %**, outer row 0.066 -> 0.097). Open / worse:
**QA-06-5** sunlit chroma (sat 0.473 -> **0.437**, R-B 99 vs 133), **QA-06-10** soffit W gap +0.202, **QA-06-12** cam06
lines 2 -> **0** composited (5 un-composited; the ratio gate passes at **0.631**).

New tests this round: the cam06 gate is the ratio **std(composited) / std(un-composited) >= 0.60** on rows 0-220
(`env_r7_measure.py --c06ratio`, QA renders the un-composited twin with `scripts/qa_r07_c06.py`). Wing shadow on a render
= share below half the band's own p90: south **57.2 %** vs ref 169's 53.9 %, north **36.3 %** vs 39.0 % (ENV's ray probe
21.2 % confirmed at the level the picture resolves). Camera height over water from the mirror row:
**h = H (M - s) / (M - y_direct)** (`qa_r07_measure.py mirror | camheight`); ref 169 = **2.6 m** vs cam01's 2.90 m.

Rejects (game asset / clean CAD): the hero's arch soffit / archivolt (a smooth untextured vault against the photo's moulded
band; 8 sockets shipped, nothing instanced); the open lagoon (flank 189.5 / hue 224 vs 152.4 / 200); cam06's far field
(0 composited street lines against 5 un-composited); the attic relief's soft edges with no cast shadow at 1:1.

**Stack offset per course, round 07** (positive = the render sits higher; 13.42 px/m): crown +0.30, crown corona +0.07,
panel frame top -0.07, panel frame bottom +0.37, cornice corona +0.07, dentil bottom -0.15, frieze top -0.30, architrave
0.00, capital top -0.37. Spread **0.67 m** (round 06: 2.38 m). **The photo-projection pass is cleared to register.**

Verdict: **gate not passed** (hero 3.44 vs the 4.5 target, no row at 4 on four of six cameras). Blockers: QA-07-1 the open
lagoon (materials + lighting), QA-07-2 sunlit stone chroma 25 % short (materials). Majors: -3 mirror at 0.55 of the photo's
0.88, -4 blank archivolt, -5 cam03 28 % black, -6 cam06 far field erased by mist, -7 hero shade level 134.0 over its window.
Recommendation: run the photo-projection pass next (its precondition is met), keep the hold-list, and add the hero
shaded-attic and lagoon-flank boxes to it.

## Round 08 (Phase 4 polish round 6, 2026-09-09) — the first round after the photo-projection pass

Scores (avg per camera) r07 -> r08: **3.44 -> 3.67 / 3.06 -> 2.69 / 2.25 -> 2.56 / 2.88 -> 2.81 / 3.00 -> 3.06 /
2.50 -> 2.67**. **Hero +0.22** (second consecutive gain; +0.45 over rounds 07-08). Full report `docs/qa_round_08.md`,
composite `renders/qa_comparisons/round08_gate.png`.

**Definition of done applied:** gate passes at hero >= 4.0 -> **3.67, not passed**. The two-round "< +0.1 after the
projection pass" clock is **armed with 0 of 2 rounds used**, because round 08 (the first round after the projection)
moved the hero +0.22. One more polish round is owed before the rule can end the loop.

**Re-basing after a station move (new method, binding for later rounds).** When cam01 moves, do NOT shift the round-03
boxes. `qa_silhouette.py align` re-registers the photograph onto the render, so the alignment's `dy` follows the
render's own shift (this round: render courses moved up **4.0 rows** for the commanded 0.30 m at 13.36 px/m; alignment
dy moved **-3.6**; residual **0.4 rows = 3 cm**). The proof is that the cached reference row reproduces at unchanged box
coordinates within 2.3 % on every box except the dome cap (-5.2 %, 25 rows from the apex). Only *round-over-round render*
statistics that depend on which course is inside the box need a control at box-4; print both (entablature row std 37.6
fixed / **40.5** control; attic anisotropy 5.02 fixed / 3.76 control).

**Projection seam test without a projection-off twin** (`scripts/qa_r08_seams.py`): crop the band edge and the
facing-mask ramp on the cameras that are NOT the projector, blur horizontally, take the largest coherent step of the row
profile. A mask edge would make the non-projector frames step *more* than the projector's. Measured: cam02 4.46-9.34,
cam05 8.24-13.55, **cam01 (the projector) 22.44** — every step coincides with a real moulding. **No seam, no doubled
feature, no sun baked into the shade** (the shaded attic *lost* luminance, 134.0 -> 127.8, while gaining the
photograph's chroma, sat 0.310 -> 0.432 vs ref 0.454).

Closed this round: **QA-07-5** (cam03 black 28.0 -> **12.6 %**, outer row 0.097 -> **0.166** at hue 58.9 — both halves),
**QA-07-6** (cam06 far-shore lines 0 -> **3** composited, ratio 0.633), **QA-07-1** on the flank (162.8 / hue 209.6 vs
154.0 / 200.5) and the ripples (R-B -47.6 -> -22.5 vs -17.0). Half closed: **QA-07-7** (shade 134.0 -> **127.8**, 1.3
over its window, hue and sat inside), **QA-07-3** (reflection 105.6 -> **116.3**, mirror ratio 0.55 -> **0.614** vs the
photo's 0.872). Open: **QA-07-2** sunlit chroma (sat 0.437 -> **0.462** of a 0.53-0.62 window; R-B 99 -> **105** of 120)
— the projection carried 28 % of it and albedo cannot carry the rest without breaking the now-passing shaded window.
Worse: cam05 water band 128.6 -> **133.6** (window 70-117), coffer rim sat 0.541 -> **0.626** with the field down to
0.339 (window 0.38-0.50), soffit W gap 0.202 -> **0.222**.

New tests this round: **mirror ratio** = hero reflection box / own sunlit attic (photo **0.872**; render 0.614).
**Camera height at a new station** is checked geometrically, not by row correlation (which is unusable on the render,
best corr 0.63 at a physically impossible M): the stack's rise in rows x px/m must equal the commanded drop (4.0 rows =
0.299 m vs 0.30 m), and the waterline edge's larger k (20.0 px/m vs 13.36) must match the shore's smaller distance.
**cam02 framing** is checked as sky fraction in the top-centre band: ref 062 has 91 % sky in rows 0-27, the render has
**0 %** — the dome is clipped (QA-08-1; the fix is ~27 mm, not 40).

Rejects (game asset / clean CAD): the hero's arch soffit / archivolt (unchanged, and four times larger in frame at the
new cam02); **cam02's whole camera-facing side in indigo shade** (pier hue 263 at sat 0.464, soffit 239 at 0.524, with
one shaded box brighter than the sunlit denominator); the shoreline as a uniform dark hedge (89.2 vs the photo's 115.2,
no trunks, no shed, no figures); the hero mirror as a dim smear where the photo has hard gold-and-blue streaks.

**Stack offset per course, round 08** (positive = the render sits higher; 13.42 px/m): crown +0.07, crown corona +0.15,
panel frame top 0.00, panel frame bottom +0.37, cornice corona +0.15, dentil bottom -0.07, frieze top -0.22, architrave
0.00, capital top -0.30. Spread **0.67 m**, unchanged through the station move; attic storey 97 vs 101 rows = 0.96.

Verdict: **gate not passed** (hero 3.67 vs the 4.5 target). Blockers: **QA-08-1** cam02 clips the dome (lead, lens
40 -> ~27 mm), **QA-08-2** cam02's face is violet (lighting), **QA-08-3** sunlit stone chroma — no longer an albedo item
(lighting/lead: sun colour or look). Majors: -4 blank archivolt, -5 mirror level, -6 cam05 lagoon band, -7 cam03 walk
now green, -8 coffer saucer over-corrected both ways. Recommendation: fix the two cam02 items (cheap, worth ~+0.4 on
that camera), then spend the owed round on QA-08-5 + QA-08-4, which are the hero's two largest named gaps.

---

## Round 09 (2026-09-10) — the LAST polish round. Hero **3.67 -> 3.67 (+0.00)**; averages
01 **3.67** (+0.00) · 02 **2.94** (+0.25) · 03 **2.56** (+0.00) · 04 **2.81** (+0.00) · 05 **3.06** (+0.00) ·
06 **2.67** (+0.00). Full report `docs/qa_round_09.md`; composite `renders/qa_comparisons/round09_gate.png`.

Merged this round and nothing else: cam02's lens 40 -> **27 mm** and **LIGHT r16** (sun-side diffuse tint b 40 -> 70,
a cam03 knob, the flythrough back to 1224 frames). No materials / ornament / environment round.

**New rule adopted this round: a score may not move unless the frame moved.** The round-08 -> round-09 whole-frame
mean |d| in 8-bit luminance is the gate on scoring at all: cam01 **1.24** (Cycles; R 0.53 / G 0.47 / B 2.73 — the tint
is a blue-removal on lit stone and is **Cycles-only**, the Eevee hero's sunlit attic did not move at all),
cam02 **52.1** (a different frame), cam03 **0.18**, cam04 **0.09**, cam05 **0.20**, cam06 **2.34**. Four frames below
a quarter of a luminance level cannot carry a score change, and inventing one corrupts the definition-of-done clock.

**New test this round: the whole-building chroma control.** The QA-07-2 / QA-08-3 window (sunlit attic sat 0.53-0.62)
is defined on ONE box. Measured against the block 700 160 1240 480 the render went **0.528 -> 0.571** against ref 169's
**0.521** — from 1.01x the photograph to **1.10x** — while the attic box is still 0.043 under its floor; the column
population went 0.632 -> **0.694** (ref 0.595) and the entablature 0.700 -> **0.735** (ref 0.588). **Any future chroma
claim must show the block control next to the box**, or it is measuring the box and not the picture.

**New test this round: cam02 framing by top-band sky.** Sky fraction in x 400-900, rows 0-60: **0.2 % -> 91.8 %**
against ref 062's 91 % in its own rows 0-27; dome apex at **0.047** of frame height (acceptance 0.05 +- 0.02).
QA-08-1 closes. The podium-base half of the test is not measurable at this station (near planting occludes it).

**New standing caveat: measure lighting on the delivery engine.** cam02's shaded boxes read hue 28.1 / 301.7 / 260.8 /
28.7 in Eevee and **268.4 / 234.6 / 249.5 / 351.2 in Cycles** — all four violet, all four at negative R-B. Lighting
r16 was tuned on Eevee frames and its cam02 pass does not survive the engine the deliverable renders in.

Rejects (game asset / clean CAD): cam02's whole camera-facing face in Cycles violet; the hero's blank archivolt over
8 empty sockets; the hero mirror at 0.614 of its own sunlit stone (photo 0.872); the shoreline as a dark hedge
(88.4 vs 115.2, no trunks / shed / figures); cam04's grey saucer fields (0.341) between orange ribs (0.634).

Held from round 08 with no drift: alignment scale 1.3108 / dx -291.8 / dy -126.6 (bit-identical), attic std ratio
0.675, anisotropy 5.01 / 8.23, shade 127.6 / 34.8 / 0.443, flank 162.7 / 209.6, ripples -22.4, near water 125.3,
cam03 black 12.8 %, cam06 ratio 0.636 with 3 far-shore lines, weathering 20.0 % / 48.2 %.
Closed this round: **QA-08-1** (cam02 lens) and **QA-08-13** (frame range now 1-1224 = 51.0 s).

**Definition of done.** Gate passes at hero >= 4.0: **3.67, not passed, 0.33 short.** The two-round flat clock reads
**1 of 2** (round 08 +0.22, round 09 +0.00). Under the user's round-08 instruction — one more round after round 08,
then Phase 5 regardless — round 09 is that round and Phase 5 starts now. The round-09 defect list is written as the
Phase 5 known-issues list, ordered by hero visibility, in `docs/qa_round_09.md`.


## Round 10 (2026-09-10) — the first round under the new gate checks; tile review FAIL

Name sweep 520 exempt / 1 hit (exempted above). Ray-cast opening test **14 / 14 PASS** (cam01 bay 00, cam02 bay 07,
z 16-22, `scripts/qa_r10_rays.py`) and the hero's own arch-centre pixel (960, 500) returns **SKY**: the v1 chord fill is
gone by three independent tests, and the sky measured inside the opening is 214.4 against the photograph's 233.3 (0.92x).

**The tile review is what the round is for, and it failed.** Fourteen defects the metrics never saw, in a frame whose
chroma and texture boxes are all within 0.1 of round 09. The two blockers: `ENV_gulls_sitting` is two flat-shaded
icospheres 7.5 m from the hero camera (five more mirror as white posts mid-lagoon), and the rotunda interior fill leaves
the arch's barrel field at **103.1 lum against the photograph's 44.9 (2.30x)** with a **magenta (hue 338.5)** jamb — so
the arch the user complained about still does not read even though it is now open.

Rejects (game asset / clean CAD), round 10: the foreground waterfowl; the arch coffers as round holes in a flat plate;
the two side-bay soffits as 112-face olive plates; cam03's black-and-white chequer paving; cam03's near column as a flat
olive slab filling 34 % of the frame; cam02's untextured stepped backdrop boxes at 116 m; the near-white untextured dome cap.

Held from rounds 08/09 with no drift: alignment 1.3108 / -291.8 / -126.6 (bit-identical, fourth round), attic std 28.9,
aniso 5.03, shaded attic 127.6 / 34.8 / 0.443, flank 162.8, ripples -21.2, near water 125.4, run-off 20.0 %.
Moved: **water reflection column 115.8 -> 131.5 lum** (clears the 124 floor for the first time) but **sat 0.383 -> 0.227**
and **R-B +50.2 -> +31.9** — ARCH r8's open arch now mirrors sky instead of a lit plate.

Hero **3.67 -> 3.56 (-0.11)**; like-for-like, scoring only what the round changed (Proportion +0.5, Lighting -0.5),
**3.67, +0.00**. Full report and the defect table: `docs/qa_round_10.md`; composite `renders/final/v2/round10_gate.png`.


## Round 10b (2026-09-10) — the blocker re-check; tile review PASS

Name sweep **520 exempt / 0 hits** (`LIGHT_shade_fill_00` is out of the rig with the lead's shade-fill-off, so the
round-10 exception is moot; kept on record above for the history). Ray-cast opening test **14 / 14 PASS** again.

**Both round-10 blockers closed.** QA-10-1 / QA-10-6: no waterfowl on the open water, nearest gull a shore bird ~100 m
out (`env_build.py` b058e45). QA-10-2: vault field `900 380 1010 430` **103.1 -> 60.6 lum** (window 45-65, ref 44.9) and
jamb `872 400 892 480` **hue 338.5 -> 25.0 with R-B +36.2** (window 25-60, positive). **No placeholder-grade object
remains anywhere in the hero frame** — the first round that is true.

New rejects, round 10b: the shaded stone reading **mustard-olive** rather than warm neutral grey-tan (QA-10b-1, whole
building sat 0.636 vs ref 0.521 = 1.22x, shaded attic hue 41.2 / sat 0.628 vs 30.6 / 0.454); cam03's near column as a
**near-black slab** (0.192 of the sunlit rotunda vs the photograph's 0.292 — QA-10-17 got worse, not better).

Held: alignment 1.3108 / -291.8 / -126.6 (bit-identical, fifth round), attic std 29.5, aniso 5.15, shaded attic lum
122.1, reflection 128.6 (still clears the 124 floor), water sat 0.250 / R-B +34.4 (still failing).

Hero **3.56 -> 3.61 (+0.05)**; Lighting mood 4 -> 4.5 and Material realism 3.5 -> 3 are the two halves of the same
lamp. Full report and the re-stated defect table: `docs/qa_round_10b.md`; composite `renders/final/v2/round10b_gate.png`.

---

## Round 11 — Phase 6 **Gate 1** (geometry freeze in the viewer), 2026-09-15. **GATE 1: FAIL.**

First round scored on the **exported** geometry as the three.js viewer draws it, not on a Blender render: geometry rows
only (Silhouette, Proportion, Ornament fidelity, Repetition visibility, Scale cues), each station against the Phase 5
render of that station. Materials and lighting are out of scope by design (neutral grey, `direct`), and the Gate 1 glbs
were written with **linear instead of sRGB** albedo/probe textures, so every luma figure in `gate1_pairs.json` is
unusable and no tonal row was scored.

**Name-sweep exemption added, Gate 1:** the viewer's **127 `WEB_far_tree_billboard_<prototype>` quads** (25 prototypes,
`userData.pfaPlaceholder = 'gate3_tree_impostor'`, web/README.md "Far-tree billboards", user's decision in
phase6_plan §4b). Legitimate until the Gate 3 impostor bake — but they are **opaque and camera-facing**, and they cover
16.1 % of cam01, 32.2 % of cam02, 33.9 % of cam03, 25.9 % of cam05 and 28.0 % of cam06 (`scripts/qa_r11_billboards.py`,
validated against the viewer's own logged matrices to 0.03 % of frame area). **Binding from now on: any gate capture
that scores geometry must include a `?billboards=0` frame for every station where the coverage is non-zero** — a
placeholder may never be the thing a metric is satisfied by, and at Gate 1 they hid 37.4 % of the hero's main-arch
opening, the whole shoreline and the podium base.

**Blocker (export).** `env.gltf` / `env_ktx2.gltf` give all ten `MAT_EXP_ENVBD__*` materials
`baseColorTexture.texCoord = -1`; three generates `uv18446744073709552000`, the vertex shader fails
(`VALIDATE_STATUS false`) and 256 `useProgram: program not valid` follow. **151,737 placed triangles — 19.1 % of the ENV
budget, the entire backdrop group (city blocks, far forest, hill, roofs, lawn, birds, lamp posts) — draw at no station.**
Cause: the grey UV1 probe texture was attached to the ten meshes that `export_set.json.uv_missing.uv1` already flags as
having no UV0. New rule: **a shader-compile error or a `PFA_*` console error in a gate capture is a blocker by itself**;
the viewer must also clamp `map.channel < 0 -> 0` so an invalid manifest can never silently drop geometry.

**Blocker 2 (export / ORN).** The three voxel-remeshed `ORN_attic_panel_v*_LOD0` shells (pre-flagged in
`phase6_budget.md` hand-off 1: deviation max 367 mm, normal-map blue mean 0.79-0.81 vs 0.97) do **not** read flat — they
read **torn**: at cam02 and cam05 the figure relief breaks into disconnected speckled fragments with hard black voids;
at the hero it is legible but pocked. The budget doc's own acceptance ("retopologise by hand only if it reads flat")
is hereby restated as **"if it does not read as continuous relief at 100 % at every station where it is > 100 px"**.

**What passed, and passed well.** Name sweep 2540 exported objects / 0 hits. Budget ARCH 844,554 / ORN 1,099,194 /
ENV 792,822 = **2,736,570 of 3.0 M**, 154 batches (140 at cam01, budget 400), resident 1.083 GB of 1.2 GB. 1440p GPU cost
**0.6-2.1 ms median**, presented 16.6-16.8 ms = 60 fps vsync-capped, uncapped 476-1667 fps — ~8x the 45 fps target.
**Silhouette: scale 1.0000, dx 0.0, dy 0.0, apex delta 0.00 %H, per-column profile mean |d| 0.81 px = 0.075 %H** against
the Phase 5 Cycles hero. The LOD0 decimation is silhouette-neutral, the column flutes survive as geometry, and the
rotunda coffer field matches 1:1. The ray-cast opening test holds on its own terms — no near-vault face intrudes — but
is only **PARTIAL** because a placeholder covers the far side.

Station averages (geometry rows, Phase 5 -> Gate 1): 01 **3.50** (-0.20), 02 **3.00** (-0.30), 03 **2.60** (0.00),
04 **3.00** (-0.10), 05 **2.90** (-0.30), 06 **2.80** (-0.30). Station averages are all within 0.5; **three rows are
not** — cam06 Silhouette -1.0 (backdrop gone), cam02 and cam05 Ornament -1.0 (attic panels) — and the parity rule is per
row. Full report `docs/qa_round_11.md`; composite `renders/web/round11_gate.png`.

## Round 11b — Phase 6 Gate 1 re-check (2026-09-15, export `ec4832b`, `?billboards=0`). **GATE 1: FAIL again.**

**Both round-11 blockers are FIXED.** B1: all four Gate 1 glTFs carry zero negative `texCoord`, the ten
`MAT_EXP_ENVBD__*` are plain grey factors with no probe texture, the page log has no shader error and no `useProgram`
warning, programs 13 -> 12, and the backdrop is visibly back (cam06 city blocks / roofs / lawn / hill-forest ridge,
cam05 horizon, cam01 horizon mass) — 151,737 placed tris draw again. B2: `voxel_remeshed` is empty, the three attic
panels are built from the Phase 5 `_LOD1` (35.9k/35.7k/35.8k -> 7,999, exported bbox delta 8.8/5.6/4.2 mm) and read as
continuous relief at 100 % at cam01 r1c2, cam02 (690,165)-(890,290) and cam05 (700,130)-(1200,220): no voids, no
shredding. The restated acceptance from round 11 ("continuous relief at 100 % at every station where it is > 100 px")
is met.

**New blocker, and the reason the re-capture did not settle the gate: `?billboards=0` hides only the VIEWER's
placeholders.** The export ships its own 127 far-tree stand-ins *inside* `env.glb` — `ENV_treeboard_000..126`,
`kind: "tree_board"`, two triangles, `MAT_EXP_treeboard` (grey, **no `alphaMode`, therefore OPAQUE**), axis-aligned,
scaled to the tree's width and height. Measured coverage (`scripts/qa_r11b_probe.py boards`, exact quad projection,
upper bound before the depth test): **cam01 16.0 %, cam02 19.7 %, cam03 23.2 %, cam04 0 %, cam05 25.5 %, cam06 19.6 %
of frame, and 44.5 % of the cam01 main-arch opening box (917,465)-(1000,620).** The widest board is 42.2 x 30.9 m, 43 of
127 are over 20 m wide, and 94 of the 127 far-list trees are within 40 m of the walk path. With `?billboards=1` (the
default) the same 127 trees draw twice.

**Rules added by this round (binding):**
1. The round-11 rule is restated with teeth: *every* placeholder set must be off in a gate capture that scores
   geometry — the viewer's quads **and** the exported `ENV_treeboard_*` boards. A capture with either of them in frame
   cannot satisfy Scale cues, the tile pass or the opening test.
2. **The name-sweep pattern is incomplete.** `placeholder|proxy|blocker|fill|occlud|block|dummy|temp|card` has no
   `board`, `impostor` or `billboard` term, so `export/name_sweep.py` reported 2540 objects / 0 hits / PASS with 127
   placeholders in the render. Add `board|impostor|billboard|standin` to both `scripts/qa_name_sweep.py` and
   `export/name_sweep.py`, and put the boards on this exemption record with their coverage, as the viewer quads are.
3. **A gate capture's tiles must be re-cut from the frames being scored.** `renders/web/tiles/` still held the 14:42
   round-11 tiles beside a 15:31 capture; QA re-cut them before viewing.
4. **A claimed encoding change must be proven in pixels.** The sRGB re-encode is in `gltf_pack.sh` (85 KTX2, was 81) but
   is invisible in the capture: cam04 — no boards, no backdrop, nothing else changed — is pixel-identical to round 11
   (frame mean 88.51 -> 88.52). Tonal rows stay unscored either way: a neutral-grey pass against a full-colour Phase 5
   render makes every luma ratio in `gate1_pairs.json` a sanity check, never a metric.

**Still open from round 11:** QA-11-9, the cam04 ceiling sliver (a thin normal-mapped wedge plus a loose shard across
the coffers, (400,80)-(600,350) at 100 %) — a decimation artefact on the building itself, named a blocker this round.
QA-11-1 / QA-11-3 (colonnade-roof and south-colonnade canopy) carry to the Gate 3 impostor bake. QA-11-5 (ripple-free
mirror water) carries to Gate 4.

**Scores (geometry rows, Phase 5 round 09 -> Gate 1 round 11b):** 01 **3.60** (-0.10), 02 **3.20** (-0.10), 03 **2.60**
(0.00), 04 **3.00** (-0.10), 05 **3.10** (-0.10), 06 **3.00** (-0.10). **Every row is within 0.5 for the first time** —
but provisionally: five rows sit exactly at the limit and four of them (Scale cues at 01, 02, 05, 06) are scored on
frames where a placeholder covers 16-26 % of the image. Silhouette against the Phase 5 Cycles hero is unchanged:
scale 1.0000, dx 0.0, dy 0.0, apex delta 0.00 %H (apex row 84, corner-top row 209 in both). Budget and perf pass on
every line: 2,736,568 placed tris of 3.0 M, 154 batches (140 at cam01), 1440p GPU 0.5-1.5 ms median — the hero is 6.8 %
of the 22.2 ms a 45 fps frame allows — resident 1.016 GB of 1.2 GB. Full report `docs/qa_round_11b.md`; composite
`renders/web/round11b_gate.png`.

## QA round 11c — Phase 6 Gate 1, third check (2026-09-15). **GATE 1: FAIL.**

Capture `2c1c7fe`, six stations 1920x1080 with **both** placeholder sets off (`?billboards=0&treeboards=0`).

1. **A placeholder switch must be proven in pixels, not in the mask.** The geometric board mask still projects
   16-26 % of five frames; the **measured** coverage is **0 % at all six stations**. Three proofs are on record:
   `MAT_EXP_treeboard` ships `alphaMode MASK` / `alphaCutoff 1.0` / `baseColorFactor` alpha 0 in the packed
   `env.glb` (every fragment discarded); the viewer hides the 127 by material name (`hiddenBoards: 127`); and the
   three largest board quads per station went from flat grey (std 0.28-0.65) to structured content (std 21-51,
   79-99 % of pixels changed) against the last capture in which they drew. **Name sweep PASS**: 2540 objects,
   127 exempt `ENV_treeboard_\d+`, 0 to explain, and `scripts/qa_name_sweep.py` carries the same pattern.
2. **A placeholder can hide a second defect — always re-score the rows it covered.** With the boards cut,
   **QA-11c-1 (BLOCKER, export)**: every `ENV_shrub_*_LOD2` node (1379 objects, 25 meshes, 135 880 placed tris)
   is written to `env.gltf` with **no transform** — ARCH writes one on 562/564 mesh nodes, ORN on 436/436, ENV on
   only 147/1536 — so the whole shrub layer draws stacked at the world origin on the rotunda floor. The site
   planting is missing at all six stations and a foliage pile sits inside the rotunda, visible through the cam01
   main arch (the origin projects to (960,655)) and across the cam04 ceiling. Rounds 11 and 11b read the same
   frames as "boards hide the planting".
3. **Fixed and confirmed at 100 %:** QA-11-4 / -6 / -8 (boards cut: shore, quay, riprap, stylobate and the
   main-arch opening all draw), QA-11-9 (the cam04 shard is gone; the rib group exports as modelled at 160 828
   tris), QA-11-2 / -10 (attic relief), QA-11-11 (backdrop). **Arch-opening ray test at cam01: PASS** — sky above
   the springline, the far interior wall below it, no near-vault face, rib plate or archivolt in the opening.
4. **Carries:** QA-11-1 / -3 (colonnade canopies) -> Gate 3; QA-11-5 (ripple-free mirror water) -> Gate 4;
   QA-11c-2 untextured backdrop and flat colonnade pedestals (geometry is undecimated, 36 456 -> 36 456) -> Gate 2;
   **QA-11c-3** the viewer logs `defaulted lightmap rgbm_range … = 7` although the manifest carries
   `lightmap_encoding.rgbm_range = 64` — it reads the wrong key; harmless now, a 9.1x error at the Gate 3 bake.

**Scores (geometry rows, Phase 5 round 09 -> Gate 1 round 11c):** 01 **3.50** (-0.20), 02 **3.10** (-0.20), 03
**2.50** (-0.10), 04 **2.90** (-0.20), 05 **3.00** (-0.20), 06 **2.90** (-0.20). **Parity FAILS**: the Scale-cues
row is **1.0 below Phase 5 at five stations** (01, 02, 04, 05, 06) once scored on frames with no placeholder under
them, twice the 0.5 limit; cam03 is exactly at -0.5. cam04 Ornament recovers +0.5 on the shard fix. Budget and perf
pass on every line: 2 841 396 placed tris of 3.0 M, 154 batches, 1440p GPU 0.5-1.6 ms median (hero 6.8 % of the
22.2 ms a 45 fps frame allows), resident 1.019 GB of 1.2 GB, load 2.31 s / 206.4 MB. Full report
`docs/qa_round_11c.md`; composite `renders/web/round11c_gate.png`.

## Round 11d — Phase 6 Gate 1, fourth check (2026-09-15, QA). **GATE 1 PASS**

1. **A placement bug is proven on the file, not on one pixel.** QA-11c-1 is **FIXED**: `env.gltf` now writes a
   transform on **1526 of 1536** mesh nodes (the 10 without are the merged world-space `ENV_backdropgroup_*`,
   identity by design), **0** shrub nodes sit within 1 m of the world origin, and the 1379 shrubs spread over
   250 x 166 m of site at ground level. `export/verify_glb.py`, re-run by QA, passes on every class (drawn vs
   `export_set`: env **0.000 %**, arch -0.185 %, orn -0.157 %, ground 0.000 %), and the writer's `near_origin`
   assertion record is empty. The frames come from the new pack (41 env meshes / 1526 instances vs 39 / 1458).
2. **The origin-pixel test alone cannot decide this class of defect** — at cam01 / 02 / 05 the world origin
   projects onto ground the reference shows planted, and at cam05 the 11c pile was occluded by a column. The
   discriminator is whether the foliage is an **island**: planted 50-px columns of the reference planting band
   went cam01 1 -> 21 of 29, cam02 0 -> 15 of 31, cam03 0 -> 5 of 39, cam05 0 -> 29 of 33, cam06 0 -> 1 of 33.
   At cam04 a green-excess metric is invalid (the gold ceiling reads as green); that station is judged on the
   100 % crop — the leaf cards are gone, coffers and ribs draw.
3. **Carries:** QA-11-1 / -3 (colonnade canopies, the 127 suppressed impostor carriers) -> Gate 3; QA-11-5
   (ripple-free mirror water) -> Gate 4; QA-11c-2 and the untextured backdrop -> Gate 2. **QA-11c-3 FIXED** (the
   `defaulted lightmap rgbm_range = 7` line is gone; the manifest's 64 is read). **New:** QA-11d-1 (Gate 4) the
   shrub instanced bounds span the whole site, so every env batch draws at every station (cam04 77 -> 99 draws);
   QA-11d-2 (Gate 2) `gltfpack` warns 37 % position error on the re-packed `env.glb` — re-pack with `-vp 16`.

**Scores (geometry rows, Phase 5 round 09 -> Gate 1 round 11d):** 01 **3.60** (-0.10), 02 **3.20** (-0.10), 03
**2.50** (-0.10), 04 **3.10** (0.00), 05 **3.10** (-0.10), 06 **3.00** (-0.10). **Parity PASSES** — no row more
than 0.5 under Phase 5; Scale cues recover 0.5-1.0 at every station and stay 0.5 under only where the far-tree
canopy is missing. Name sweep PASS (2540 objects, 127 exempt, 0 to explain). Budget and perf unchanged: 2 841 396
placed tris of 3.0 M, 154 batches, 1440p GPU 0.6-1.5 ms median (hero 6.8 % of a 45 fps frame), resident 1.019 GB,
load 2.57 s / 206.5 MB. Full report `docs/qa_round_11d.md`; composite `renders/web/round11d_gate.png`.

## Round 12 — Phase 6 **Gate 2** (the baked PBR set alone), 2026-09-15. **GATE 2: FAIL** (one row)

Capture 19:09: `materials=pbr`, `lighting=direct` (sun + PMREM, **no lightmaps, no shadows, no compositor**), both
placeholder sets hidden, six stations 1920x1080, manifest `pfa-phase6/3`, 60 sets. Gate 2 had no cam01 tiles; QA cut
them (`scripts/qa_r12_probe.py tiles` -> `renders/web/tiles/gate2/`) and viewed all six at 100 %, plus two 100 % crops
per station 02-06. Only Material realism / Edge wear / Repetition are scored. **Luminance is not a material metric at
this gate** (no shade term) and is reported, never scored.

1. **Sunlit stone is right.** Sunlit attic hue +1.9 deg, sat **0.97x** of the round-10b Cycles hero; whole building sat
   **0.532 = 0.84x** of that render and **1.02x of photograph 169** — QA-10b-1's 1.22x frame chroma is closed by the
   bake. The round-9 attic photo projection survives registered (mid-band 0.67-1.29x, no seam). ORN relief is real at
   all 33 prototypes. **QA-11c-2 closed on both halves**: all ten backdrop sets attach (cam06 ratio 2.837 -> 1.548),
   attic pedestals textured (std 50.5 / hp9 27.6 vs Phase 5 32.2 / 15.9). 64/74 materials textured, 0 failures, the
   only 10 unmatched are foliage (rule 7). cam02 beats its own reference (viewer hue 47.1 vs the round-09 frame's 262.1).
2. **QA-12-1, BLOCKER, owner bake — ARCH stone carries no surface at walking distance.** cam05 pier face mid(5-21 px)
   **2.68 vs Phase 5's 10.11 (0.27x)**, std 12.3 vs 38.3; attic wall 2.87 vs 9.79; cam03's near column at 5.5 m has no
   grain; cam01's south-colonnade back wall hp9 **0.6-0.8** against **13-19** on the rotunda attic in the same frame.
   Cause, from the manifest: the albedo is a **DIFFUSE colour-only** bake and **7 of 12 ARCH/ground sets ship
   `normal.texture: null`**, so the material's bump is in neither map; the two colonnade atlases also pack only
   **0.16 UV coverage** (every other ARCH group 0.40-0.69). Filtering is not the cause (`pbr.js` sets anisotropy 8).
   Fix: bake each ARCH/ground material's own bump to a normal for all twelve groups and re-pack the colonnade UV1.
   Acceptance: cam05 `1180 560 1280 680` mid(5-21) >= 7.0 and std >= 25; cam01 `1600 590 1670 635` hp9 >= 4.0; the
   sunlit-attic hue/sat must not move.
3. **Not blocking.** QA-12-2 dome cap sat **0.64x** of Phase 5, a smooth near-white lid (QA-10-8 carried; albedo mean
   0.911/0.919/0.671 is faithful, roughness 0.43 takes a sky specular with no shadow). QA-12-3 colonnade atlas coverage
   0.16 (folded into QA-12-1). QA-12-4 per-instance variation is absent **by construction** — one texture per shared
   mesh (export/README Gate 2 finding 3); colonnade shaft-to-shaft CV 0.028 / 0.089 vs Phase 5's 0.072 / 0.319, which
   costs every Repetition row 0.5 and is Gate 3's per-instance lightmap slot, not a re-bake.
4. **Named exception standing at this gate:** the 10 foliage materials (`MAT_bark_*`, `MAT_leaf_*`, `MAT_shrub*`,
   `MAT_reeds`) have no Gate 2 set by design (manifest rule 7) and keep their Gate 1 card textures; under sky-only
   irradiance with no shadow they read as pale chips at 100 %. Gate 3/4, not a Gate 2 defect.

**Scores (round 09 -> round 12).** Material realism 01 3.5->**3.5**, 02 2->**2.5**, 03 2.5->**2**, 04 3->**2.5**,
05 3.5->**2.5**, 06 2.5->**2.5**. Edge wear 3.5->**3**, 2.5->**2**, 1.5->**1**, 1->**1**, 2->**1.5**, 0.5->**0.5**.
Repetition 3->**2.5**, 2.5->**2**, 2->**1.5**, 2.5->**2**, 2.5->**2**, 2.5->**2**. **Parity fails on exactly one row —
cam05 Material realism, -1.0 against a 0.5 window** (cam03/cam05 references are Eevee, not luminance parity targets;
the texture measurement is still valid and the root cause is a manifest fact). Budget PASS: resident 1 333.8 MB at
1440p (textures 855.6 + RT 437.5 + geo 40.6), PBR set 566.2 MB of the 1 200 MB texture budget, hero **267 draws of
400**, GPU **1.7 ms**, load 483.2 MB in 4.17 s. Full report `docs/qa_round_12.md`; composite
`renders/web/round12_gate.png`.

### Round 12b — Phase 6 **Gate 2 re-check**, 2026-09-15 (`docs/qa_round_12b.md`). **GATE 2: PASS**
1. **QA-12-1 CLOSED on its material share.** cam05 pier `787 373 853 453` @1280x720 mid(5-21) **2.68 -> 7.05** (target
   >= 7.0), hp9 **8.14**, std **22.87** (target 25); cam01 S-colonnade wall `1600 590 1670 635` hp9 **0.6-0.8 -> 5.83**
   (target >= 4.0); grain visible at 100 % on the pier and on the cam03 near column at 5.5 m. The control that decides
   it: where the sun reaches the surface in BOTH frames the material amplitude is **at or above parity** (sunlit attic
   mid 1.10x / std 1.17x, attic pedestals 1.33x / 1.49x, dome cap 0.99x), and only where the reference has shade that
   `direct` mode cannot have is it 0.35-0.81x (cam05 pier 0.47x, colonnade pedestal 0.44x). The export measured the
   baked albedo's own ceiling at mid 5.5 on this pier and the viewer delivers 7.05, i.e. **more than the albedo holds**;
   the 8-bit source `*_disp` maps (texel gradient 0.00134-0.00173, below 1/255) cap it there. The cam05 std residual is
   shade/occlusion -> Gate 3, **not** a re-bake.
2. **New at this gate, both LIGHTING, neither a Gate 2 defect.** **QA-12b-1**: sun-less stone reads olive-green — cam02
   RGB 107/125/107, hue 119.4, sat 0.143; **16.0 %** of cam02's and **21.9 %** of cam06's building pixels have G > R
   against **0.1 %** in the Phase 5 hero and **0.0 %** of the baked albedo itself (maiden + concrete_ochre albedos are
   R > G > B on 100 % of their pixels), so it is the sky-only irradiance with no bounce, not the asset. **QA-12b-2**:
   the S-colonnade back wall blows out at mean 201-221 and its recessed panels read as a pasted checker (panel hue 36.7
   / sat 0.217 vs wall 40.4 / 0.362).
3. **Carried.** QA-12-2 dome cap sat **0.69x** (was 0.64x; amplitude now at parity, mid 0.99x) — accepted under MAT
   r10's one-round rule. QA-12-3 closed numerically (back wall 9.4 -> 5.28 cm/texel, columns 1.07 cm); its remaining
   flatness is the blow-out. QA-12-4 per-instance variation stays Gate 3 by construction: world-space detail tiling
   breaks grain-scale identity but cam01 shaft CV is only 0.041 S / 0.133 N. **No seams, no visible detail-tile repeat,
   no colour-space error** in the six cam01 tiles or the ten station crops; 19/19 ARCH/ground sets ship a real normal.
4. **Named exception standing:** the 10 foliage materials (manifest rule 7) still have no Gate 2 set and read as pale
   chips under sky-only light. Gate 3/4.

**Scores (round 09 -> round 12 -> round 12b).** Material realism 01 3.5->3.5->**3.5**, 02 2->2.5->**2.5**,
03 2.5->2->**2.5**, 04 3->2.5->**2.5**, 05 3.5->2.5->**3**, 06 2.5->2.5->**2.5**. Edge wear 3.5->3->**3**,
2.5->2->**2**, 1.5->1->**1.5**, 1->1->**1**, 2->1.5->**2**, 0.5->0.5->**0.5**. Repetition 3->2.5->**3**,
2.5->2->**2**, 2->1.5->**2**, 2.5->2->**2**, 2.5->2->**2.5**, 2.5->2->**2**. **All eighteen rows are 0.0 or -0.5
against round 09 — inside the parity window — and no row's residual is a material gap**, so GATE 2 PASSES. Budget PASS:
resident **1 433.6 MB** at 1440p (textures 953.5 + RT 437.5 + geo 42.6), textures 246.5 MB under the 1 200 MB budget
with the impostor lever (-200 MB) unspent, detail layer 33.6 MB, hero **267 draws of 400**, GPU **1.8 ms** median,
load 537.4 MB in 4.78 s, 62/62 sets used, 0 failures. Composite `renders/web/round12b_gate.png`.
