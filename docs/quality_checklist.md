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
