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

### Round 13 — Phase 6 **Gate 3, the lightmaps alone**, 2026-09-16 (`docs/qa_round_13.md`). **LIGHTMAPS ACCEPTED, one re-bake**
1. **The maps attach and they work.** 16/16 own maps (max match error 0.019 m) and 988/988 per-instance slots (0.005 m)
   applied, 21/21 textures loaded, 0 failed. Hero whole-frame luma **117.5 -> 135.99** against the Cycles hero's 139.98
   (**0.971x**), p10 52.89 vs 52.22; MAE against each station's reference falls on **all six** (hero 36.67 -> 29.88).
   Boxes, Gate 2 -> baked vs Phase 5: hero shade band 1.18x -> **0.93x**, entablature 1.20x -> **0.99x**, columns
   1.22x -> **1.00x**, capital row 1.25x -> **1.11x**, S-colonnade wall 1.44x -> **1.23x** with hp9 5.83 -> **27.71**
   (ref 26.32), cam05 pier std 23.6 -> **29.4** and mid 5.82 -> **10.23** (ref 38.1 / 12.50). Seven of ten boxes close or
   halve the deficit round 12b attributed to lighting. **No seam at any UV2 island edge, no slot bleed, no texel
   blockiness, no encoding banding, no double shadow** in the six cam01 100 % tiles.
2. **QA-13-2 — the one re-bake: `ARCH_rotunda_plaster_ceiling_merged`.** cam04's coffer field is **24.3 vs 60.7 = 0.40x**,
   p10 **0.00**, **37.8 %** of pixels below luma 8 (Phase 5 0.0 %, p10 27.8). The ribs are lit from their own relaid map;
   the coffer beds take the plaster shell's map, whose max is **0.72** over 4.9 % non-zero texels. The draw order is fine
   (the rib/coffer mesh is in front). Re-bake with the visible shell split from the merged mass's interior/backing faces.
3. **QA-13-1 NEW, largest colour error in the hero, NOT the bake.** The north colonnade bays read as saturated blue
   rectangles (RGB ~52/86/188): **23.0 %** of the band `20 520 540 645` is B > R + 20 against **3.9 %** at Gate 2 and
   **0.0 %** in Phase 5, and **96.4 %** of those pixels are **bit-identical with the lightmaps off**, so the surface takes
   no light from either path. Not the background sky (the sky 30 px above is 181/204/222). Same blue at cam05 and cam06.
   Owner viewer / export: identify the surface before Gate 4.
4. **Carried.** QA-12b-1 olive **not closed and worse at cam02** (16.0 -> 19.7 %, cam06 21.9 -> 20.2 %, Phase 5 0.1 / 9.7 %;
   30.9 % vs 2.3 % in the 40-60 luma bin, so not a brightness artefact) and **not** caused by the lightmaps — `direct` is as
   green. QA-12b-2 halved but still a flat cream field at 100 %. QA-12-4 shaft CV 0.041/0.133 -> **0.088/0.187** (Phase 5
   0.469/0.539). **The sunlit-attic saturation hold BREAKS: 0.94x -> 0.89x.** Colonnade-roof soffit leaks at 1.68x; the
   vault field over-darkens to 0.76x. Accepted: QA-12-2 dome cap.
5. **Named exceptions standing:** post, the 127 far-tree impostors (`WEB_far_tree_billboard_*`, hidden, declared
   placeholders — the export-set name sweep is **0 to explain**), the 14 near-tree vertex irradiance (the blue foliage at
   every station) and mist are Gate 4 and are **not** scored as defects.
6. **Parity references.** Only station 1 has a reference rendered from the lighting the lightmaps were baked from.
   3 / 5 are Eevee round-09, 6 is round-09 Cycles with no compositor, and **2 and 4 are round-09 Cycles frames that predate
   LIGHT r18 and the shade-fill-off** (cam02's reference still shows the violet round 10b recorded as fixed). Stations
   2-6 are scored provisionally; the Cycles re-renders must cover **2 and 4** as well as 3 / 5 / 6.

**Scores (round 09 -> round 13).** 01 3.67->**3.39**, 02 2.94->**2.69**, 03 2.56->**2.69**, 04 2.81->**2.31**,
05 3.06->**2.89**, 06 2.67->**2.33**. Every station average is inside the 0.5 window; cam04 and cam06 are below the 2.5
floor; four individual rows are outside 0.5 (cam01 Lighting mood and Scale cues, cam04 Lighting mood and Ornament
fidelity). Budget PASS: resident **1 677.8 MB** at 1440p (textures 1 171.6, 28.4 MB under the line with impostors still to
come, RT 443.8, geo 62.4), hero **269 draws of 400**, GPU **2.3 ms** median / 435 fps uncapped, presented 39-45 fps,
load 629.1 MB in 5.82 s, 62/62 sets, 0 failures. Composite `renders/web/round13_gate.png`.

## Round 14 — Phase 6 **Gate 4** (the viewer proper: baked + probe + impostors + water + post), 2026-09-16. **ONE MORE ROUND**

Full report `docs/qa_round_14.md`; composite `renders/web/round14_gate.png`; capture `round14` (phase6-viewer 1cc73fd,
`lighting=baked&post=all&probe=1&impostors=1&water=1&billboards=0&treeboards=0&t=0`), references station 1 the Phase 5
Cycles hero and 2-6 the round-13 Cycles frames (128 spp, compositor on). Tools: `scripts/qa_r13_probe.py --round 14`
(now carries `band / foliage / mist / water / walk` and a `--round` capture selector) and `qa_r13_gate.py --round 14`.

1. **Closed.** **QA-13-1** the blue colonnade bays: band `20 520 540 645` B > R+20 **23.0 % -> 0.2 %** (Cycles 0.0 %,
   gate 3.9 %), hue 219.9 -> 40.2 (ref 40.9), level 1.00x; the same surface at cam06 64.7 -> 4.6 % (ref 10.9 %).
   **QA-13-2** the coffer field: **0.40x -> 1.02x**, p10 0.00 -> 29.5 (ref 28.6), below luma 8 **37.78 -> 0.02 %**.
   **QA-12b-1** at cam06 (G>R 20.2 -> **1.5 %**, ref 1.4 %) and cut to a third at cam02 (19.7 -> **7.4 %**, ref 2.2 %)
   — all of it the compositor airlight, none of it the lightmaps. **QA-12-4** shaft CV 0.088/0.187 -> **0.327/0.361**
   (Phase 5 0.469/0.539).
2. **New, open.** **QA-14-1 water at cam01** — the ripple does not exist: row high-pass in the open lagoon **0.97 vs
   13.23 (0.07x)**, row/col 0.72 vs **3.24**, open water 66.8 vs 118.0 (0.57x), hue **200 vs 145 deg**, sat 0.326 vs
   0.041, and the near-edge Fresnel flattens to ~41 where the reference falls 96.5 -> 60.4. The rotunda *does* reflect,
   so the 6a criterion passes. **QA-14-2** cam03 1.67x, p10 39.8 vs 7.3 (no deep shade). **QA-14-3** cam06 p10 9.7 vs
   65.6, near ground 0.53x, far terrain sat 3.7x (the haze never desaturates). **QA-14-4** bloom flattens the hero:
   capital-row std 0.93x -> **0.69x**, S-colonnade mid **0.40x**, vault field 0.76x -> **1.25x**, sunlit-attic sat hold
   0.89x -> **0.80x**, a halo on the dome cap and fireflies on the leaf-card edges. **QA-14-5** near foliage reads as
   flat angular cut-outs with black gaps; cam02 hue **-45.9 deg** against Cycles' olive (held decision, still open).
3. **Named exceptions standing.** The 127 `WEB_far_tree_billboard_*` carriers are in `env.glb` and hidden
   (`hiddenBoards: 127`) with the octahedral impostors drawn in their place — on record, not a sweep hit; the export
   set's own sweep is **0 to explain**. The backdrop wall reading as one flat mustard field is the hero probe's
   single-point irradiance, accepted in `docs/decisions.md`. cam06's 0.71x level is a real deficit the old
   no-compositor reference hid, not a regression.
4. **6a criteria.** Within 0.5 of Phase 5 at every station **PASS** (worst -0.23); none below 2.5 **PASS but thin**
   (cam03 and cam06 both 2.56); water reflects the rotunda **PASS**; walk never in the lagoon **PASS** (24/24) but
   **3 of 24 probes stand at -1.225 m, 25 mm below the `WATER_Z + 0.1` floor**; loading screen **PASS** with an 18 %
   denominator error (planned 522.3 MB vs 639.0 MB loaded); **>= 45 fps NOT MET** — 28.9 ms = **34.6 fps** at 1440p
   (45.0 only at cam04), GPU median 2.7 ms, 314 draws, resident 1 677.8 MB; the frame is vsync-quantised, attributed.

**Scores (round 09 -> round 13 -> round 14).** 01 3.67 -> 3.39 -> **3.61**, 02 2.94 -> 2.69 -> **2.94**,
03 2.56 -> 2.69 -> **2.56**, 04 2.81 -> 2.31 -> **2.88**, 05 3.06 -> 2.89 -> **2.83**, 06 2.67 -> 2.33 -> **2.56**.
Delta vs Phase 5: -0.06 / 0.00 / 0.00 / +0.07 / -0.23 / -0.11.

## Round 15 — Phase 6 Gate 4, round two (`round15`, phase6-viewer 43b1e0a). **6a PARITY REACHED**

1. **Closed this round.** **QA-14-1 water** (largely): open-water row high-pass **0.97 -> 6.92** (ref 13.23, the
   0.5x-2x acceptance), row/col **0.72 -> 3.71** (ref 3.24), reflection mass **0.85x -> 1.00x** with hue within
   2.8 deg, Fresnel now falls 95.5 -> 65.1 where the reference falls 87.8 -> 60.4 (round 14 was flat at 41), and the
   hard reflection line is gone. **QA-14-3 cam06**: near half **0.53x -> 0.98x**, p10 **3.6 -> 69.1** (ref 58.0),
   whole frame 0.75x -> **1.00x**, MAE 37.1 -> **18.7**. **QA-14-4 bloom** to its ceiling: capital-row std
   **0.69x -> 0.85x** (gate 0.85x), dome-cap halo +12.0 -> **+5.1** over the reference (post-on minus post-off
   +7.65 -> **+0.76**), attic sat 0.80x -> **0.87x** against a post-off ceiling of 0.887x. **Minors:** walk floor
   **0 of 24** probes below `WATER_Z + 0.1` (was 3); loading bar **640.1 / 640.1 MB = 100.0 %** (was 122.3 %);
   the README's QA-notes section is back.
2. **Open, carried.** **QA-14-1 residual**: the lagoon away from the reflection is a flat saturated teal slab —
   hue **195.6 vs 144.8 deg**, sat **0.363 vs 0.041**, lum 0.75x, no crests at 100 %. **QA-14-2 cam03** flat: near
   p10 **53.1 vs 17.0**, frame 1.65x — surfaces with no baked light on a single-point probe; bake/export, post-6a.
   **QA-14-5 foliage** half: cam02 near-tree level **0.99x** and the cyan gone, hue still **-44.7 deg** (albedo).
   **QA-12b-2**: S-colonnade wall mid **0.44x**, post-off ceiling 0.51x — the flat cream wall itself, not bloom.
   **New:** the probe-lit N-colonnade / backdrop wall **1.00x -> 1.26x**; north shaft CV 0.361 -> 0.248; cam01
   shore-planting sat 1.54x of Cycles.
3. **Named exceptions standing.** Export-set name sweep **0 to explain** (Gate 3 r2; membership unchanged — the only
   re-export was `env.glb`'s COLOR_0 re-encode and the `instance_irradiance` manifest block). The 127
   `ENV_treeboard_*` carriers stay in `env.glb` and stay hidden (`?treeboards=0`) with the octahedral impostors drawn
   in their place. The backdrop wall as one flat field is the hero probe's single-point irradiance (decisions.md).
4. **6a criteria.** Within 0.5 of Phase 5 **PASS** (worst -0.12, cam05); none below 2.5 **PASS** (floor cam03 2.56);
   water reflects the rotunda **PASS**, now as ripple streaks; walk clamp **PASS** 24/24 with **0 below the floor**
   — caveat, the probe ran 6 s / 19.3 m per heading against round 14's 30 s / 96 m, so only 2 of the 3 round-14
   violations fall inside the re-tested window (re-run once at 30 s, post-6a); loading screen **PASS** with a correct
   total; **>= 45 fps NOT MET** — 28.2 ms = **35.5 fps** at 1440p (44 only at cam04), GPU median 2.5 ms, 279 draws,
   resident 1 677.9 MB, load 640.1 MB in 6.11 s; deterministic screenshots **PASS**, 0 page errors.

**Scores (round 09 -> 13 -> 14 -> round 15).** 01 3.67 -> 3.39 -> 3.61 -> **3.72**, 02 2.94 -> 2.69 -> 2.94 ->
**3.00**, 03 2.56 -> 2.69 -> 2.56 -> **2.56**, 04 2.81 -> 2.31 -> 2.88 -> **2.88**, 05 3.06 -> 2.89 -> 2.83 ->
**2.94**, 06 2.67 -> 2.33 -> 2.56 -> **2.83**. Delta vs Phase 5: **+0.05 / +0.06 / 0.00 / +0.07 / -0.12 / +0.17**.

## Round 16 (Phase 6c, the foliage gate, round one of two) — 2026-09-17, `round16b` on main @ 98b9f3e
**Verdict: ONE MORE ROUND.** The stated 6c acceptance passes — no station drops, station 2 rises **+0.13**, every
frame time is within **+1.9 ms** of round 15 (gate +3), resident memory reported — but 6c's own goal ("foliage
credible at 3 m from every station and along the walk") is not met, and CLAUDE.md's rule is that the numeric boxes
never override the tiles. Full report `docs/qa_round_16.md`; composite `renders/web/round16b_gate.png`.
1. **Closed by 6c.** The impostor blue cast, by per-placement `E_placement / E_bake` modulation and not by a
   re-bake: cam02's fill tree **1.41x -> 1.28x**, hue **68.2 -> 54.3** (ref 45.5), sat **0.100 -> 0.594** (ref
   0.530); the hero's far-tree roofline **1.12x -> 1.01x**, hue **137.5 -> 75.3** (ref 76.9); cam02 near trees
   G>R **37.4 -> 66.2 %** (ref 70.9). cam02 MAE **23.11 -> 20.48**, the round's largest move.
2. **Open, with owners.** *(a) Shrub/reed cards, EXPORT:* frame-normalised level against Cycles st1 **1.70x**,
   st2 1.47x, st3 1.34x, st5 1.34x, with **2-8x** the reference's hard-edge share and about half its leaf-green
   pixel share (st5 15.1 % vs 33.4 %). The tinted albedo fixed the hue (st2 G>R 4.2 -> 58.8 %) and pushed the level
   FURTHER out at four boxes of five; `post=off` is identical, so it is the albedo. *(b) Crown interiors, VIEWER:*
   centre/edge 0.504 vs the reference's 0.364 at cam02 and (p90-p10)/mean 1.26 vs 1.77 at cam05, every viewer crown
   at 1.6-4.5x the reference's p10 — and 6c's soft edges flattened cam05 a further 6 %. *(c) The 3 m walk-in,
   EXPORT:* the LOD2 crown at 3 m is magnified cream cut-outs and bare sticks; it wants its LOD1.
3. **Named exceptions standing, 0 new to explain.** Export-set sweep over the manifests: only
   `ARCH_rotunda_inner_block`, `ENV_backdrop_fill(roof)` and the bake-side `LIGHT_gallery_fill_*`; 6c's new members
   (`ENV_tree_<species>_s##` x16, `EXPM_ENV_src_*_LOD2` x25) carry no hit, and every other pattern match in those
   files is a JSON field name, not an object. The 127 hidden `ENV_treeboard_*` carriers stay as before.
4. **Perf and memory.** 30.1 / 33.5 / 32.7 / 22.7 / 31.8 / 33.5 ms at 2560x1440 (hero **33.2 fps**); draws 329-351,
   5.24-5.60 M tris, load 660.0 MB in 6.43 s. **Resident 1 800.6 MB = 1.50x the 1 200 MB Gate 1 budget** — note
   `web/README.md` and `docs/decisions.md` both say 1 717 MB; the committed `round16b_perf.json` says 1 800.6
   (+115.9 over round 16), so the two documents are wrong by ~83 MB (viewer, documentation only).
5. **Bare URL = the delivery look.** Luma 1.0002x of the station-1 preset, 0 page errors, 0 shader errors,
   `impmod` full with 16 `E_bake`, 254/254 far-tree rows lit, 1 376/1 376 LOD1 shrubs, 2K atlas on 16/16.
6. **New tile defects, carried not caused by 6c:** cam03's shrub cards are the same straw-pale confetti at ~8 m with
   the round's worst hard-edge share (12.1 % vs the reference's 1.5 %); cam06's water carries a regular diagonal
   moiré at grazing incidence (hp9 identical to round 15, so it is a round-15 carry this tile pass first reports).
7. **Not re-measured on round16b:** the walk clamp. `round16_walk.json` (6c round one, before `env_trees.glb` and
   `env_shrubs.glb`) reads 24/24 probes, lowest -0.702 m, 0 below `WATER_Z + 0.1`; re-run once at 30 s on the 6c
   scene, which added 1.0 M placed triangles a ground clamp may hit.

**Scores (round 13 -> 14 -> 15 -> round 16).** 01 3.39 -> 3.61 -> 3.72 -> **3.72**, 02 2.69 -> 2.94 -> 3.00 ->
**3.13**, 03 2.69 -> 2.56 -> 2.56 -> **2.56**, 04 2.31 -> 2.88 -> 2.88 -> **2.88**, 05 2.89 -> 2.83 -> 2.94 ->
**2.94**, 06 2.33 -> 2.56 -> 2.83 -> **2.83**. Delta vs round 15: **0.00 / +0.13 / 0 / 0 / 0 / 0**; vs Phase 5:
**+0.05 / +0.19 / 0.00 / +0.07 / -0.12 / +0.17**.

## Round 17 (Phase 6c foliage gate, round two of two, `round16c`) — 6c CLOSED WITH RESIDUALS
1. **Crown interior CLOSED.** cam02 centre/edge 0.504 -> **0.393** (ref 0.364), p10 18.6 -> **5.3** (ref 4.1); cam05 range/mean
   1.26 -> **1.72** (ref 1.77); every crown box's level inside 0.94-1.05x. **Shrub/reed LEVEL CLOSED**: frame-normalised
   1.09-1.70x -> **0.91-1.47x** over eight boxes, hard-edge share down at seven of eight. **3 m walk-in CLOSED**: the walk-up
   LOD1 set reads as a canopy (overlapping cards, branches, sky through the gaps).
2. **Shrub STRUCTURE still open (export).** Broad flat angular cards at 3 m and 8 m; leaf-green pixel share ~half the
   reference's at five boxes; worst boxes cam03 1.53x and the hero's own band 1.47x.
3. **The darkening overshoots (viewer).** Hero crown p10 20.9 vs ref 36.8 and centre/edge 0.491 vs 0.852; station 5's frame
   146.8 vs the reference's 151.2 and the only station whose MAE rises; blotchy near-black crowns; a pale halo now reads
   around the darker crowns (carried from round16b, newly conspicuous).
4. **Far-tree tops stay opaque (bake/export):** cam02 r1c3, cam03 r1c1 — solid cut-outs where the reference shows sky
   through the twigs. Unmoved by round 3.
5. **New at 100 %, carried not caused by 6c:** cam03's column concrete is visibly blurred and vertically banded at 1 m;
   cam06's backdrop trees are faceted low-poly **in the Cycles reference too**, so they are a Phase 5 asset, not a viewer defect.
6. **Named exceptions standing, 0 new to explain** (export-set sweep over the manifests; the round-3 walk-up set adds no hit).
7. **Perf and memory.** Cold 1440p pass of record 32.4 / 37.0 / 35.1 / 22.1 / 32.2 / 34.0 ms = **+4.2 / +4.8 / +2.2 / -0.4 /
   +1.8 / +1.9** on round 15 — the **+3 ms gate fails at stations 1 and 2 on the pass of record**, cause unestablished
   (draws identical to round16b at all six, triangles identical at five; only cam03 adds geometry, +0.39 M). Same-session
   A/B pending. Hero **30.9 fps**. **Resident 1 931.4 MB = 1.61x the 1 200 MB Gate 1 budget** (+130.8, all walk-up geometry);
   this supersedes every earlier figure. Load 664.0 MB in 6.74 s.
8. **Walk clamp re-run at 30 s on the full 6c scene:** 24/24 probes, lowest ground **-0.750 m** vs the -1.20 floor, **0 below**. Closed.
9. **Bare URL = the delivery look:** luma 0.9999x of the station-1 preset, MAE 8.09/255 (upscale), 0 page errors, every round-3 default in the boot log.

**Scores (round 14 -> 15 -> 16 -> round 17).** 01 3.61 -> 3.72 -> 3.72 -> **3.78**, 02 2.94 -> 3.00 -> 3.13 -> **3.25**,
03 2.56 -> 2.56 -> 2.56 -> **2.63**, 04 2.88 -> 2.88 -> 2.88 -> **2.88**, 05 2.83 -> 2.94 -> 2.94 -> **2.94**, 06 2.56 ->
2.83 -> 2.83 -> **2.83**. Delta vs round 16: **+0.06 / +0.12 / +0.07 / 0 / 0 / 0**; vs round 15: **+0.06 / +0.25 / +0.07 /
0 / 0 / 0**; vs Phase 5: **+0.11 / +0.31 / +0.07 / +0.07 / -0.12 / +0.17**. None below 2.5; none outside 0.5 of Phase 5.

## Round 18 — Phase 6b Gate 5, the staging deployment (2026-09-18, Opus xhigh; docs/qa_round_18.md). **ONE FIX ROUND**
1. **Payload on the URL is the figure of record: 46 814 308 B = 46.81 MB before the first frame** (320 requests, first frame 8.11 s), 3.19 MB inside the
   50 MB conjunct. The local dev-server 50.24 MB in web/README is HTTP/1.1 headers and no compression and is NOT the figure. Tiers 46.9 / 456.3 / 69.6 MB
   in 7.6 / 51.8 / 12.9 s, all tiers 74.5 s, 581.1 MB total; 0 files over 25 MiB, 0 tier failures, 0 lowres left, 182+4 upgrades all succeeded.
2. **Desktop parity with the 6c build is exact.** Luma 0.998-1.002x, MAE 0.03-1.37/255, **0 of 25 round-13/15/16 boxes move > 3 %** (worst 0.987x); MAE
   against the Cycles references moves by <= 0.10. Scores carry unchanged: **01 3.78 · 02 3.25 · 03 2.63 · 04 2.88 · 05 2.94 · 06 2.83**; none below 2.5,
   none outside 0.5 of Phase 5. 36 tiles at 100 % beside round16c: **no new defect**; every 6c residual reproduces (blurred banded cam03 columns, flat
   card shrubs, pale crown halo, flat backdrop planes, cam06 water moiré, cam04 entablature aliasing).
3. **BLOCKER — the mobile fallback has no geometry on the URL.** All 7 `groups/m_*.glb` 404: 18 page errors, **49 draws / 548 triangles at every station**
   (sky, water, far-tree impostors only). They exist on disk and in `manifest_mobile.files` but are in **no** deploy plan: `manifest.json.files` omits
   them while `tiers.deploy_from` asserts the desktop plan is complete, and deploy.sh trusts it. 14 571 144 B. Owner export (primary), deploy (assert).
   Mobile is therefore unscorable, and its resident (<700 MB) and 30 fps targets are unmeasured.
4. **Loading-screen denominator is wrong in both variants** (viewer): `tier0_planned_bytes` 29.2 MB desktop vs 46.9 MB fetched; 325.8 MB mobile vs 24.1 MB.
5. **Perf is not throttled; no cold re-measure needed.** 1440p medians 31.7 / 38.0 / 37.7 / 25.1 / 34.2 / 34.2 = +2.0 / +7.6 / +4.2 / +3.1 / +4.4 / +1.9
   on perf_ab pass B but only -0.7 / +1.0 / +2.6 / +3.0 / +2.0 / +0.2 on round16c cold; gpu_cost medians unchanged (1.0-3.7 vs 1.0-3.4 ms), max/p95
   18-22x = the single-outlier signature of every earlier pass, and the lead's independent URL cold pass agrees within 1.1 ms at five stations. Carried:
   hero **31.5 fps** against the 45 target. **Resident 1 861.3 MB = 0.964x of round16c's 1 931.4** — lighter, because the split uploads 269 unique texture
   sources for 333 texture objects where round16c uploaded 289 for 289. Streaming costs nothing resident.
6. **Headers verified live per path class** (deploy 2): bake assets `max-age=31536000, immutable`; manifests and the relay status `max-age=60,
   must-revalidate` (brotli); site `max-age=300, must-revalidate`. Largest published file 16.7 MB against the 25 MiB cap.
7. **Name sweep over BOTH gate5 manifests: 0 hits** (they key on texture and group names); round 17's gate1/gate3 exceptions stand, 0 new to explain.
8. **Evidence owed:** the user's macOS **Safari** screenshot (no capture in this round is anything but HeadlessChrome/152 — no Safari claim can be made)
   and the **iPhone 16 Pro** 30 s iOS Safari walk, which cannot be taken until item 3 is fixed.

## Round 18b — Phase 6b Gate 5, the fix round and the closing 6b round (2026-09-18, Opus xhigh; docs/qa_round_18b.md). **6b DONE WITH RESIDUALS**
1. **The round-18 blocker is closed.** `manifest.json` names 149 mobile-tier rows, 0 mobile paths are missing from the desktop plan, the publish set is the
   union with `verify_publish` (1 051 paths, 0 missing). Curl on the live URL: **all 7 `groups/m_*.glb` 200, `model/gltf-binary`, immutable, byte-exact**;
   39 further sampled paths 200 with the right cache class; the only >= 400 in either capture is `/favicon.ico`; 0 files over 25 MiB.
2. **Mobile loads and walks at all six stations.** 142-180 draws / 1.51-1.91 M tris, 0 page errors, 7 of 7 groups, 16 lightmaps, 110 ETC2 substitutions.
   **Resident 499.7 MB against the 700 MB target.** Mobile bytes before the first frame **46 738 628 B = 46.74 MB** in 8.6 s, 61.7 MB total.
3. **First mobile scores** (36 tiles at 100 %, 2 x 3 per portrait station): **01 2.9 · 02 3.0 · 03 2.3 · 04 2.7 · 05 2.5 · 06 2.4** against desktop's
   3.78 / 3.25 / 2.63 / 2.88 / 2.94 / 2.83. The centre band (mobile rows 936-1595 = the desktop frame) matches desktop within 2 % at four stations; the two
   water stations are 1.14x and 1.11x brighter. Mobile's conjunct is "loads and walks", not 6a's 2.5 desktop floor.
4. **Residual (VIEWER): the mobile water reflects nothing.** `reflectionSet` `{excluded: 169, kept: 1, all: true}` vs desktop's `kept: 134` — no rotunda in
   the hero lagoon, a flat lower half at station 05, and a **near-black bay band** at station 06. One cause, three symptoms; 6a's "water reflects the
   rotunda at the hero" does not hold on the mobile tier.
5. **Residual (ENV / EXPORT):** aerial impostors read as flat lavender-grey or black cards and the far terrain shows decimation facets; the 1 m column
   concrete blur is worse on mobile and the column base shows `-si 0.5` facets; foliage is cards only by design. **Residual (EXPORT):** 302 by-reference
   mobile paths are still outside `files[]`, so `verify_publish` cannot cover them.
6. **Found and fixed inside the round (VIEWER):** `gate5bm` painted the canvas 832x1801 in the top-left of the 1170x2532 page (50.6 % of it) at every
   station; viewer 13a673c sets full CSS size and caps the pixel ratio, and `gate5cm` fills the page. The mobile tiles above are all `gate5cm`.
7. **Desktop is untouched by the fix.** MAE vs round-18 `gate5` <= 0.001/255 at every station (02 and 04 bit-identical), payload **46 808 904 B = 46.81 MB**
   before the first frame, resident **1 861.3 MB** identical, perf within ±3 ms of the cold pass (31.2 / 35.6 / 38.9 / 25.5 / 34.5 / 36.5), hero 32.1 fps.
   Desktop scores carry: 01 3.78 · 02 3.25 · 03 2.63 · 04 2.88 · 05 2.94 · 06 2.83.
8. **Loading bar fixed:** tier-0 denominator vs bytes fetched now 95.2 % desktop / 98.0 % mobile (round 18: 160.9 % / 7.4 %). **Name sweep 0 hits** over both
   manifests including the 149 new rows. **Still owed by the user:** the macOS Safari hero screenshot (every capture is HeadlessChrome/152) and the
   iPhone 16 Pro walk recording, takeable for the first time now.

## Gate rule added 2026-09-18 (lead, after the bare staging URL drew the test scene)
- Every QA round against a deployed host captures the BARE URL (no query string) at the hero in addition to the parameterised stations; the manifest note in the boot
  log must name the delivery manifest and the glb count must equal the plan's; the test-scene fallback on a bare URL is a blocker regardless of every other metric.

## QA round 19 (Phase 7, the foliage look on the live URL, tag `gate7`, 2026-09-19) — PHASE 7 DONE WITH RESIDUALS
1. **The two defects that opened the phase are closed on the tiles.** Desktop: at 800 % the one-pixel pale fringe along every impostor silhouette is gone and
   the binary edge steps are resolved; the shore crowns' near-black blotches are gone (hero crown p10 **0.564x -> 0.894x** of Cycles, the brief's >= 0.8x).
   Mobile: the close-orbit crowns at 37-40 m are meshes with branches and sky through them, `farTrees.meshDist` 45 m live, near-black share 0.00-4.47 % (the
   4.47 % is a shaded trunk, not a card core).
2. **The one acceptance metric that misses:** station 5's whole frame is **0.976x** of the reference against the required 1.00 +- 0.01; the branch's own sweep
   shows the lever tops out at 0.981x, so the remaining 2 % is not foliage. Recorded as residual 1, not as a blocker.
3. **No regression.** 0 of 11 architecture boxes move more than 3 % (max 1.006x); 4 of 14 foliage boxes move, all intended; cam04 bit-identical; MAE against
   the Cycles reference falls at four stations and is unchanged at two. Perf inside +3 ms at every station against the idle cold pass with identical draws,
   triangles and programs; desktop resident 1 861.3 MB unchanged; mobile resident 561.9 MB against the 700 ceiling.
4. **Payload rule held:** 46 811 106 B before the first frame over the same 320 requests (the +2 202 B over round 18b is the rebuilt JS bundle); tier 0 carries
   the same asset files; the mobile +4.13 MB is lazy tier 2. Name sweep 0 over both manifests.
5. **Scores.** Desktop 01 3.78 · 02 3.25 · 03 2.63 · 04 2.88 · **05 3.06** · 06 2.83 (only station 5's Lighting mood moves, 2.5 -> 3.0). Mobile 3.2 / 3.3 / 2.3
   / 2.7 / 2.8 / 2.4 from 2.9 / 3.0 / 2.3 / 2.7 / 2.5 / 2.4, the water half of that move being the 6d reflection fix rather than Phase 7.
6. **Rule restated for later rounds:** a "before" capture must be on the same deployment as the change being judged. `gate5cm` predates the 6d mobile
   reflection, so the mobile before/after deltas in this round bundle two changes and are reported as such rather than credited to one.

## QA round 20 (Phase 8 items 8a / 8b part 1 / 8c on the live URL, tag `gate8`, 2026-09-19) — 8c CLOSED, 8a NOT CLOSED, 8b measured
1. **A lever that cannot be measured on the build that ships has to be measured after export, and the export can reach one box only.** 8a's densification
   moved the hero's shore band (leaf-green 0.62x -> **0.84x** of the reference) and left the other four half-share boxes where they were (05 shore **0.29x**,
   03 cards 0.54x, 02 shore 0.65x). 56-95 % of the pixels in every shrub box changed and at 100 % only one band looks different: **pixel change is not look
   change**, and the tile decides.
2. **A budget exception must be priced in DRAWN triangles, not placed ones.** The accepted "+~105 k placed" cost **+~560 k rendered triangles per pass**
   (+1.12 M per frame at the five water stations, identical on mobile) because the LOD1 walk-in shrub set is submitted in full every pass although
   `shrubLod` reports `lod1: 0, source: null`. Price the exception against `renderer.info.render.triangles` at the stations before accepting it.
3. **A sampling trick that manufactures structure the data does not have shows up as a pattern.** The 2K atlas plus coverage share 0.15 improves every
   crossings number (2.92 -> 6.97 at station 2) and paints a **regular ordered dot grid** on every far-tree crown seen against the sky, visible at 100 % on
   the delivered hero. The tiles override the metric (gate rule, 2026-09-10) and this is recorded as a new defect, not as a win.
4. **A memory figure is only as good as what it traverses.** `resident()` bills textures reachable from material slots; the impostor atlas is a custom
   uniform, so ~32-89 MB of atlas has been absent from every GPU-memory number quoted in Phases 6-8 — `texture_bytes` was byte-identical across a 1K -> 2K
   swap of 16 atlases. Any resident claim must name what its traversal can and cannot see.
5. **A projection default is worth more than a re-bake.** 8c cost 0 bytes, 0 bake and 0 tier change and took the near shaft's banding anisotropy from
   **4.76 to 1.39** (reference 1.60) with grain and pores back at 100 %. Measure the cause before buying resolution.
6. **Scores.** Desktop 01 3.78 · 02 3.25 · **03 2.75** · 04 2.88 · 05 3.06 · **06 2.89**; mobile 3.2 / 3.3 / 2.4 / 2.7 / 2.8 / 2.5. The hero holds because
   its two real gains and its one new artefact are in the same frame.

## QA round 21 (Phase 8 item 8b, the band atlas on the live URL, tag `gate9`, 2026-09-19) — **8b CLOSED**
1. **Resolution fixes what a sampling trick only disguises.** Round 20's coverage share bought crossings and paid with an ordered dot grid on every crown.
   The band atlas (12 az x 3 el at 341 px) takes cam01 from 7.99 to **11.97** against Cycles' 11.73 — *and* the grid measures away: the lattice index falls
   from 8/10 boxes above their Cycles control to **3/10**, and at 300 % the hero's roof-line crowns are clean. Buy the data before buying the filter.
2. **A defect is closed only where it was seen.** The grid is gone from every crown *body*; a period-2 **rim** one to two pixels deep survives at stations 2
   and 5, and the share cannot touch it (the viewer's own sweep records 1 and 5 byte-identical across share 0 to 0.40). Name the surviving mechanism, or the
   next round spends the wrong lever on it.
3. **A risk flagged by the bake is not a defect until the delivered frame shows it.** The willows' 1.62 % clipped texels move p99 by 0.2/255 and produce
   **0 pixels over 240** anywhere in six frames: the 10-minute `PFA_BAND_RANGE=band` re-bake is not spent. Measure the tail on the frame, not in the atlas.
4. **"Byte-identical" is a claim to verify, not to quote.** The export said tier-mobile was untouched; MAE 0.00000 and max |d| 0 at all six stations say so —
   and therefore the mobile scores must not move either.
5. **A cost can be negative.** The band replaced the 2K albedo atlases: +8.4 MB in, -9.3 MB out, resident byte-identical (same 4 M texels), medians 0.3-4.2 ms
   *faster* than gate8 at every station, and station 3's QA-20 perf flag clears (+3.1 -> +0.1 vs the idle baseline).
6. **Scores.** Desktop 01 **3.89** · 02 **3.31** · 03 2.75 · 04 2.88 · 05 **3.12** · 06 **2.95**; mobile unchanged at 3.2 / 3.3 / 2.4 / 2.7 / 2.8 / 2.5.

## QA round 22 (Phase 8 items 8a / 8a-3, 8d, 8e + the viewer fix round, live URL, tag `gate10`, 2026-09-19) — **8a NOT CLOSED · 8d BLOCKER · 8e CLOSED · fix round VERIFIED**
1. **A preview harness proves a direction, not a delivery.** 8d's Eevee before/after promised the hero band's luma sd would rise 0.159 -> 0.177; on the
   delivered frame it *fell* 0.156 -> 0.153 and the hf did not move, while cam06 reached ~15 % of its saturation target and ~5 % of its luma target.
   Re-measure every preview claim on the shipped frame before calling an item closed.
2. **Replacing a flat thing with a flat thing is not a fix.** The R2 tree belt (6 986 tris over ~120 crowns = ~58 tris each) swapped a pale wall with dark
   panels for hard-edged untextured faceted spikes in every intercolumniation at cam01 / 02 / 05 and in the reflection. The colour metrics improved; the
   tiles got worse. The tile review overrides the numeric boxes, as the 2026-09-10 gate rule says.
3. **A fix closes only the asset it touched.** 8a-3 scaled the LOD2 shrub cards and shore bands at 1 and 5 now read as lit-and-shaded bushes — cam03 sees the
   LOD1 walk-in set at 8 m and is pixel-for-pixel the same cut-outs. Name the asset, not the defect, when scoping.
4. **Measure the delivered frame at its own resolution.** `qa_r13_probe.rgb` resizes every input to 1920x1080, so QA 19's mobile-orbit statistics were read
   off 1170x2532 portrait frames squashed to landscape. Read natively; the 8e result (run p90 29.5 -> 22.7 px, coverage 1.02-1.23x, no thinning) only
   appears when you do.
5. **A cull is verifiable to the triangle.** The fix round claimed -1 410 000 at the hero and -2 020 000 at cam06; the delivered frames say -1 395 080 and
   -2 010 552, with every 1440p median equal or faster and the hero at 35.5 fps. A claim with a number attached is a claim QA can settle in one command.
6. **Scores.** Desktop 01 **3.81** · 02 **3.14** · 03 2.75 · 04 2.88 · 05 3.12 · 06 **3.03**; mobile 3.2 / 3.22 / 2.44 / 2.7 / 2.88 / 2.58.

## QA round 23 (Phase 8 closing: 8d belt r2 + the far-tree irradiance re-bake, live URL, tag `gate11`, 2026-09-19) — **8d CLOSED · re-bake = BRIGHTNESS REGRESSION (blocker, EXPORT) · 8a closed with residual · 8e closed · fix round VERIFIED with a new cost**
1. **Build the thing out of the thing.** The belt rebuilt from the real Sapling prototypes through the far-tree path cleared in one round what two
   rounds of icosphere shaping could not: crowns with sky gaps and trunks at 1 / 2 / 3 / 5 and in the reflection, parity to the Phase 8 Cycles
   reference improving at every band (hero N 11.24 -> 9.62 % MAE), and the hero band's sd and hf finally moving toward ref 169 instead of away.
2. **A correction is still a regression if it moves away from the reference.** The far-tree irradiance re-bake was accepted as a topology fix
   (modulation median 0.942 -> 1.390). On the far trees it buys ~1 % of screen luma — harmless. On every crown read against a background it is
   +4 to +16 %, moves 7 of 10 boxes away from Cycles, and drops 8e's blade metric from 5/6 to 2/6 under target. Accept a bake correction only with
   the delivered frames measured against the reference, not against the bake's own inputs.
3. **When a threshold metric moves, ask whether the picture moved.** 8e's blade p90 rose 22.7 -> 25.2 px and the tile shows the same leaves in the
   same places, only brighter: a brightness-thresholded run metric widens when the subject brightens. State the photometric confound before
   scoring the geometric claim.
4. **A control box is a control only while its background holds still.** The three QA-17 "building behind" crowns moved most this round (up to
   1.246x Cycles) because the belt behind them changed — not the crowns. Decompose foliage share from background share before attributing a move.
5. **Removing geometry in one frame can add it in another.** The belt cost -13 644 triangles at five stations and **+1 301 870 at cam03**, where
   the far-tree path draws it as LOD2 meshes instead of billboards: +3.5 ms, 25.9 fps, the slowest station. Check every station's triangle count,
   not the hero's.
6. **When the reference set is regenerated, keep it at full resolution.** Only the 960 px JPEG copies of the Phase 8 Cycles references survived
   (PNGs gitignored, the worktree gone), so this round's parity is measured at 960 px on both sides and no sharpness claim can be made from them.
7. **Scores.** Desktop 01 **3.97** · 02 **3.22** · 03 **2.83** · 04 2.88 · 05 **3.20** · 06 3.03; mobile **3.32 / 3.30 / 2.52 / 2.70 / 2.96 / 2.58**.

## QA round 24 (verification of the far-tree irradiance re-key, live URL, tag `gate12`, 2026-09-19) — **BLOCKER CLOSED; no open blocker in Phase 8**
1. **A revert is verified on the delivered frames, box by box, against the same reference the regression was measured with.** Nine of the ten
   far-crown boxes return to within 3 % of gate10 (seven to three decimals), the mean deviation from the Phase 8 Cycles set goes 6.7 -> 9.7 ->
   **6.3 %**, and the one box that does not return moves *toward* the reference. "The bake was re-keyed" is not the evidence; these numbers are.
2. **Reverting a photometric change reverts the metrics it confounded — and only those.** 8e's blade p90 returns to 22.7 px and 5/6 boxes under
   target, each box to the pixel, with coverage 0.991-1.000x. That the *same six numbers* come back confirms round 23's reading that the rise was
   brightness widening a thresholded run, not geometry.
3. **What does not revert tells you the attribution was wrong.** The shrub hard-edge rise stayed (5.95 / 7.12 % against gate10's 2.78 / 5.73)
   while the luma it was blamed on went all the way back. One round's cause can be another round's coincidence: re-attribute in writing, to the
   belt that actually changed, and carry it with an owner.
4. **Hold the rest of the frame to a byte rule.** Station 4 bit-identical, seven of nine architecture boxes bit-identical, MAE 0.00-0.44 % at every
   station, payload -5 105 B, resident and draw calls identical to the digit. A one-item fix that leaves that trail needs no argument.
5. **Identical geometry with slower frames is a measurement, not a regression.** Draws, triangles, programs and 1 814.2 MB resident matched gate11
   exactly while the 1440p medians read up to +5.4 ms — the machine had just finished a 4K Cycles render. Say so, do not charge it, and re-take
   the number on an idle machine.
6. **Scores.** Desktop 01 **4.01** · 02 **3.30** · 03 2.83 · 04 2.88 · 05 **3.28** · 06 **3.07**; mobile **3.40 / 3.38 / 2.52 / 2.70 / 3.04 / 2.62**.

## QA round 25 (the Phase 9 gate on deploy 13, tag `gate13`, 2026-09-21) — **GATE PASSED; hero 4.05, no blocker**
1. **A look change is only shipped once it is read back out of the delivered frame, in the units it was specified in.** Station 2's
   acceptance was written in b\* / h_ab / R-B on named boxes; the same boxes on the deployed frame give -2.7 -> **+10.4**, -11.2 ->
   **+4.5**, +0.2 -> **+9.0**, tracking the re-rendered Cycles master within 0.9 b\*. That — not "the re-bake ran" — is what closes a
   defect that had been open since QA-08-2.
2. **When the whole scene changes, a fixed 0.5 % regression budget measures nothing.** This round re-baked every lightmap and gated the
   specular at every station, so no pixel is "outside the changed boxes". Score the *direction* instead: all six stations moved toward
   the new Cycles references, five of six toward the old ones, and the architecture boxes landed on their reference (`columns` 113.5 vs
   114.3, `vault field` 60.3 vs 60.6).
3. **Re-score a carried defect against the AFTER reference, and check whether the reference moved.** The far crowns' deviation went
   7.5 -> 9.6 %, and because `cycles_p9 / cycles_p8` is 0.970-0.998x on those boxes the reference did *not* move — so the rise is the
   viewer's. Two boxes, not nine as in QA 23: name the width as well as the direction, and it stays a residual rather than a blocker.
4. **The tiles keep finding what no box is pointed at.** 36 tiles at 100 % gave the faceted aerial backdrop and the lagoon moiré at
   station 6, the flat pale backdrop slabs behind the colonnade at 1 / 2 / 5, and the violet column shafts — none of which any metric in
   this round's brief covers. Conversely a tile defect can be exonerated by one measurement: those shafts read b\* -1.02 in the viewer
   against -1.52 in Cycles, so the viewer is faithful and the fault is the master's.
5. **A frustum rule is cheaper than a viewer capture.** `export/belt_rule.py --frustum` re-derives from the manifest which belt rows are
   in frame at cam03 and FAILs if an in-frame row is billboard-only — the whole "no magnified card" gate check, with no GPU.
6. **Scores.** Desktop 01 **4.05** · 02 **3.51** · 03 **3.08** · 04 **3.05** · 05 **3.24** · 06 3.07; mobile **3.44 / 3.59 / 2.77 / 2.87 / 3.00 / 2.62**.

## QA round 26 (the ENV R3 backdrop tiles on deploy 14, tag `gate14`, 2026-09-22) — **PHASE 9 CLOSE CONFIRMED; hero 4.05**
1. **A reference can go stale, and then parity measures the reference.** Station 6's MAE against `cycles_p9` rose 7.065 -> 7.306 while the
   frame improved: those refs were rendered before ENV R3 and the ENV round had already measured the same +27.6 % hf in the Cycles master.
   Before scoring a station as a regression, check whether the reference contains the change being scored.
2. **"Reads as texture, not as a lattice" is measurable.** The QA-21 grid index falling (-9.86 -> -10.14) while the high-pass std rises
   (8.06 -> 8.86) is exactly "more detail, no more order" — the number that separates a tile that works from a repeat.
3. **A dark sliver at 4K is not automatically a 4K defect.** Sampling the same world pixel in the 4K hero, the Cycles ref and both deploys
   gave (57,43,24) / (56,43,24) / (73,75,81) / (74,77,83): a shaded surface present in every renderer since before the round, not a hole,
   not new. Four numbers settled what a tile could only raise.
4. **Byte-close is a gate check, not a formality.** Stations 3 and 4 moved 0.001 % / 0.000 % and station 4 not at all — which is what lets
   the round leave their carried defects unre-scored and keeps the gate short.
5. **Scores.** Desktop 01 **4.05** · 02 **3.55** · 03 3.08 · 04 3.05 · 05 3.24 · 06 **3.15**; mobile **3.44 / 3.63 / 2.77 / 2.87 / 3.00 / 2.70**.
