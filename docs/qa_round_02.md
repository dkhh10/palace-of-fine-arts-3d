# QA round 02 — Phase 3 gate (2026-09-07)

QA / Critic. Reviewed `master.blend` (155 MB, built by `scripts/lead_build.sh` at 16:42 = `build_master.py` +
`light_probes.py --bake --save`): 6043 objects, 31 library materials, **0 placeholder materials**, two baked irradiance
volumes, LOD1 15.18 M tris (62.0 M tris summed over every LOD in the file). All five owners landed their round-1 fixes
before this build (architecture cf419b4, environment 1bc0491 + peninsula band, ornament a1bdcc5, lighting 63b4329,
materials f84a8ef). This is the first round scored with real materials, so **Material realism** and **Edge wear** are
scored for the first time without an excuse.

## What was rendered and compared

| file | what |
|---|---|
| `renders/previews/qa/round02_0K_*.png` | Eevee 1280x720, 32 TAA, `light_presets.apply_preview_eevee`. Times: **46.3 / 45.4 / 36.7 / 33.6 / 54.8 / 32.8 s** (round 1: 14 / 25 / 33 / 14 / 8 / 8 s). |
| `renders/previews/qa/round02_01_lagoon_hero_cycles.png` | Cycles 1920x1080, 128 spp adaptive, OIDN, GPU (`apply_final_cycles`). **446.4 s** (round 1: 65 s — 6.9x slower). |
| `renders/qa_comparisons/round02_cam0K.png` | render / canonical photo (letterboxed) / 50 % blend, `qa_compare.py` |
| `renders/qa_comparisons/round02_cam01_aligned_vs_ref169.png`, `_vs_ref085.png`, `_vs_user.png` | W_a-aligned overlays, `qa_silhouette.py align`. These, not the letterboxed blends, are the 2 %-of-frame-height test. |
| `renders/qa_comparisons/round02_sheet.png` | contact sheet of the six comparisons |
| **`renders/qa_comparisons/round02_gate.png`** | **the gate composite**: Cycles hero beside ref 169, the six Eevee views as a strip, and the round 1 -> round 2 score table with deltas burnt in (`scripts/qa_gate_sheet.py`). |

Commands: `blender -b --python scripts/qa_render_round.py -- --round 02 --eevee` and
`-- --round 02 --final --samples 128 --res 1920 1080 --cams 01`.

**Tool change (my file).** `scripts/qa_silhouette.py`'s building mask was `r > b + 0.06`, which loses a sky-lit pale
cream dome cap (the architecture agent measured ~3 m of apex lost). The mask is now "**not sky and not foliage**"
(sky = `b >= r - 0.01 and b > 0.30`; foliage = clearly green), with `--mask warm` to reproduce round-01 numbers.
On this hero both masks return the same apex (y 88), so the round-02 dome numbers below are not an artefact of the fix.
New tools: `scripts/qa_measure.py` (region sRGB / luminance / hue / saturation, waterline, EV delta),
`scripts/qa_exposure_sweep.py` (measured AgX exposure response), `scripts/qa_gate_sheet.py` (the gate composite).

## Score table (0-5; target >= 4 every row, hero average >= 4.5). Round 01 -> round 02.

| row | cam01 hero | cam02 NE 3/4 | cam03 colonnade | cam04 ceiling | cam05 S lawn | cam06 aerial |
|---|---|---|---|---|---|---|
| Silhouette match | 3 -> **4** | 1 -> **2** | 1.5 -> **1.5** | 4 -> **3.5** | 1.5 -> **2** | 3 -> **4** |
| Proportion | 3 -> **3.5** | 3 -> **3** | 3.5 -> **3** | 4 -> **3.5** | 3.5 -> **3** | 3.5 -> **3.5** |
| Ornament fidelity | 3 -> **3** | 3 -> **2.5** | 3 -> **2.5** | 2.5 -> **1.5** | 2.5 -> **2** | 3 -> **2.5** |
| Material realism | 1 -> **2.5** | 1 -> **2** | 1 -> **2** | 1 -> **2** | 1 -> **2** | 1 -> **1.5** |
| Edge wear | 0 -> **1** | 0 -> **1** | 0 -> **1** | 0 -> **0.5** | 0 -> **1** | 0 -> **0.5** |
| Lighting mood | 3.5 -> **3.5** | 3 -> **2.5** | 3 -> **2** | 1 -> **3** | 3 -> **3** | 2.5 -> **2** |
| Water reflection | 1 -> **3** | n/a -> **2** | 1 -> n/a | n/a | 1 -> **2** | 1.5 -> **1.5** |
| Repetition visibility | 2 -> **2.5** | 3 -> **2** | 2 -> **2** | 3 -> **2** | 2 -> **2** | 2 -> **2** |
| Scale cues | 3 -> **3.5** | 2 -> **2** | 3 -> **1.5** | 3 -> **2.5** | 2.5 -> **2** | 3 -> **2** |
| **average** | **2.17 -> 2.94 (+0.78)** | 2.00 -> 2.11 (+0.11) | 2.00 -> 1.94 (-0.06) | 2.31 -> 2.31 (0.00) | 1.89 -> 2.11 (+0.22) | 2.17 -> 2.17 (0.00) |

Where a row went **down**, it is because something newly visible is wrong, not because the model regressed:
cam03 lost points to a camera that is still inside the column row (QA-02-5) and to blown-out raking light; cam02/05/06
lost Ornament/Repetition/Scale points because the ornament is now legible enough to judge and reads as engraved decal
(QA-02-9/10); cam04 Ornament dropped because the lit ceiling finally shows that the coffers have no depth.

**Gate verdict: not passed.** The hero is the first render in three attempts that survives a silhouette overlay and
carries a believable lagoon, and it is worth showing the user. But at 1:1 the stone still reads as *clean CAD with
decals* and there is effectively no edge wear anywhere in the build, which is the exact failure mode of attempts 1
and 2. Explicit "game asset / clean CAD" rejects this round: the hero stone at 1:1 (QA-02-2), the total absence of
weathering and the missing algae line (QA-02-3), the attic relief panels and the vault coffers (QA-02-9), the
attic corner figures (QA-02-10), and the cam06 backdrop (QA-02-15).

## What works (keep it)

- **The dome arbitration paid off.** Aligned overlays of the Cycles hero: apex **+1.32 %** of frame height vs ref 169
  (round 1: 6.3 %), **+0.74 %** vs ref 085, **-0.49 %** vs the user image — all inside the 2 % tolerance, against three
  independent photographs. Visible rise / W_a = **0.223** (ref 169 0.249, ref 085 0.237, user 0.214; round 1: 0.161).
  The drum band and cornice ring are visible above the attic from cam01.
- **Hero composition.** Shoreline at ~66 % of frame height (round 1: 86 %), apex 8.1 % from the top, W_a 560 px.
  See the QA-01-4 note below for why the "33-35 % of frame width" number is the wrong yardstick in 16:9.
- **Water.** Ripples break the reflection into streaks, there is murk and Fresnel, the near field is blue-green, and
  the reflection column is at 77 % of the building's luminance (the acceptance asked >= 70 %). Round 1's flat brown
  mirror is gone. It is the single biggest jump in the build.
- **Rotunda ceiling.** Coffer field 53.1 lum vs ref 083's 66.4 (round 1 was 4x too dark). Relative to each image's own
  sky the render is at 0.50 vs the photo's 0.39 — the probes work.
- **Placeholders gone.** 0 placeholder materials, 31 library materials, per-instance seed wired.
- **Aerial silhouette.** From cam06 the dome, drum, both wings and the lagoon outline read correctly and the dome no
  longer blows out (cap 165.7,159.5,150.6 = lum 160.1 against a 140.8 background; QA-01-20 closed).

## Measurements

### Exposure (the contested question). Cycles hero vs ref 169, matched regions via the W_a alignment transform

Display sRGB means; "EV" is the scene-exposure change needed, from the **measured** AgX response, not a gamma guess:
`scripts/qa_exposure_sweep.py` rendered the hero at exposure +0, +0.5, +1.0 EV and the display luminance moved
+32.0 / +35.2 / +30.5 / +33.8 units per EV for attic / column / sky / water reflection respectively.

| region | render (Cycles) | ref 169 | ratio | **EV needed** |
|---|---|---|---|---|
| sunlit attic panel | 176,138,88 · lum 142.4 · hue 33.9 | 220,176,93 · lum 179.4 · hue 39.1 | 1.26 | **+1.16** |
| dome cap | 189,153,120 · lum 158.4 · hue 29.3 | 225,189,131 · lum 192.6 · hue 37.4 | 1.22 | +1.07 |
| column shaft | 170,120,84 · lum 127.9 · hue 24.8 | 203,149,79 · lum 155.2 · hue 33.8 | 1.21 | +0.78 |
| sky top | 116,160,201 · lum 153.7 | 131,183,229 · lum 175.2 | 1.14 | +0.70 |
| sky low (haze band) | 140,167,190 · lum 163.1 | 176,213,240 · lum 206.9 | 1.27 | +1.44 |
| water, reflection column | 129,106,78 · lum 108.9 | 162,138,106 · lum 140.7 | 1.29 | +0.94 |

**Recommendation: +0.9 EV** (`scene.view_settings.exposure` -3.2911 -> **-2.39**), i.e. materials' "+1 EV" is right and
lighting's "~+0.15" is an order of magnitude short. The reason lighting under-estimated is AgX: a 14-26 % display-referred
deficit is close to a full stop of scene exposure, not 0.2. +0.9 EV lands the sunlit attic at ~179 (target 179.4) and the
sky top at ~181 vs 175 (+3 %, acceptable). It does **not** fix warmth: hue *falls* 1.1 deg per +1 EV, so the 5.2 deg
(attic) / 9.0 deg (columns) / 8.1 deg (dome) hue deficit is a separate materials/sun-temperature job (QA-02-14).

### Silhouette and framing

| measure | render | ref 169 | ref 085 | user image | verdict |
|---|---|---|---|---|---|
| apex delta (frac of frame height, aligned) | — | +0.0132 | +0.0074 | -0.0049 | all < 0.02 **pass** |
| visible dome rise / W_a (cam01) | 0.223 | 0.249 | 0.237 | 0.214 | pass |
| shoreline (frac of frame height) | ~0.66 | 0.53 | — | 0.69 | in the 0.65-0.72 band |
| apex from top | 8.1 % | 10.4 % | — | 14.9 % | >= 8 % **pass** |
| W_a as frac of frame **width** | 29.2 % | 20.5 % | — | 34.1 % | fails the literal test |
| W_a as frac of frame **height** | 51.9 % | 33.7 % | — | 49.6 % | +4.6 % rel. **pass** |

### Dome from cam05 (ref 063) — the one that still fails

Crops normalised to 940 px wide (`round02_05_south_lawn.png` x 400-900 y 0-170 vs ref 063 x 560-1360 y 0-272):
visible dome + drum rise above the attic cornice is **~3.7 % of the on-screen rotunda width in the render vs ~12.2 %
in ref 063** — the render shows a sliver of drum wall and **no dome cap at all**. The cam01 numbers are right, so this
is not the apex height; it is that the attic parapet occludes the cap from a close, low, oblique station.

### Other regions

| measure | render | reference | note |
|---|---|---|---|
| lagoon, mid-left band | lum 34.9 | ref 169 134.5 | 3.9x too dark |
| lagoon, near field off-axis | 39,88,121 sat 0.678 | ref 169 45,68,79 sat 0.426 | 25 % bright, over-saturated cyan |
| north colonnade band | lum 66.0 | ref 169 137.2 | 52 % dark — buried in trees |
| south colonnade band | lum 88.2 | ref 169 140.5 | 37 % dark |
| cam04 coffer field / own sky | 0.50 | ref 083 0.39 | pass |
| cam04 arch soffit / own sky | 0.20 | ref 083 0.58 | vaults still light-starved |
| cam06 far background | sat 0.076-0.091, hue 60-76 | — | haze collapses everything to one grey-olive |

## Viewport performance (pass/fail, not scored)

- **master.blend open time: 1.8 s** wall clock headless (`blender -b master.blend --python-expr "import bpy"`),
  6043 objects. Budget 60 s — **pass** with a large margin.
- **Viewport LOD1 triangles: 15.18 M** (lead's build number; 62.0 M summed over all LODs in the file). Up from 8.5 M in
  round 1. Still openable, but this is the number to watch before Phase 5.
- **Eevee preview seconds per QA camera: 46.3 / 45.4 / 36.7 / 33.6 / 54.8 / 32.8** (1280x720, 32 TAA) versus
  14 / 25 / 33 / 14 / 8 / 8 in round 1 — **2-7x slower**. Cycles 1080p/128 spp went 65 s -> 446 s. Not a fail, but the
  round-1 extrapolation of "4K hero in 25-40 min" is stale (see QA-02-16).

## Deliverables present (pass/fail)

- **Cycles final config — pass.** `apply_final_cycles`: GPU (Metal), 768 spp adaptive (threshold 0.01, min 64),
  OIDN denoise, no time limit. The saved file's own `cycles.device` is `CPU`; the preset switches it, so scripted
  finals are fine but a manual F12 from the opened file would run on CPU.
- **Eevee viewport config — pass.** `BLENDER_EEVEE`, taa_samples 16 / taa_render_samples 32, raytracing on,
  AgX + `AgX - Base Contrast`, two baked irradiance volumes (`LIGHTPROBE_rotunda`, `LIGHTPROBE_colonnade`).
- **`CAM_flythrough_path` — FAIL.** master.blend contains **no curve objects at all** and no `CAM_flythrough*`.
  `scripts/light_flythrough.py` builds them, but `build_master.py` does not append them. See QA-02-11.
- Phase-5 items (3840x2160 Cycles hero, low-res Eevee test animation) not yet due.

## Status of every round-01 defect

| id | owner | status | evidence |
|---|---|---|---|
| QA-01-1 dome/drum low | architecture | **closed for cam01, reopened for cam05** | apex within 1.32 % / 0.74 % / 0.49 % of refs 169 / 085 / user; rise/W_a 0.161 -> 0.223. But see QA-02-1. |
| QA-01-2 shrub slabs | environment | **partially closed** | 1461 shrub objects from leaf cards, no straight-edged slab wider than 4 px at 1920. They now read as a regular row of dark pom-poms (QA-02-18) and hide the podium (QA-02-13). |
| QA-01-3 flat water | materials + environment | **closed** | ripples, murk, Fresnel, blue near field; reflection at 77 % of the building's luminance (test: >= 70 %). Residual tonal problems tracked as QA-02-6. |
| QA-01-4 hero framing | lead | **closed** | shoreline ~66 % (was 86 %), apex 8.1 % from top, W_a 51.9 % of frame height vs the user image's 49.6 %. The written test's "33-35 % of frame width" is unsatisfiable together with the other two clauses in 16:9 (the user photo is 1.46:1); measured against frame height, which is aspect-independent, the current lens 20 / shift 0.06 is correct. **No change recommended.** |
| QA-01-5 cams 02/03/05 | lead | **partially closed** | cam05 now frames podium-to-attic; cam02 frames the whole rotunda but from a station the canonical photo was never taken from (QA-02-17); **cam03 is still inside the row (QA-02-5)**. |
| QA-01-6 tree placement / screen | environment | **over-corrected** | sky through the bays is down to 1.7 % / 9.5 %, but both wings are now 37-52 % darker than ref 169 and read as tree mass (QA-02-7). |
| QA-01-7 leaf cards | environment | **partially closed** | no card wider than ~6 px at hero distance; crowns still uniform dark blobs from cam02 and cam06. |
| QA-01-8 hall backdrop box | environment | **partially closed** | a facade with cornice and a green door now sits in the arch instead of a grey box; the wall itself is still flat untextured cream with a hard black opening. |
| QA-01-9 Eevee ceiling | lighting | **partially closed** | coffer field 4x dark -> 0.80 of ref 083; but the barrel-vault soffits are still at 0.20 of the frame's sky vs 0.58 (QA-02-12). |
| QA-01-10 attic panels sparse | ornament | **partially closed** | 13-15 figures, 62-64 % coverage per ORN, but at 60-100 m the panel has no shadow structure and reads flat (QA-02-9). |
| QA-01-11 podium Greek-key band | ornament + architecture | **built, unverifiable** | ARCH geometry per the lead's decision and visible in `arch_06_phase3_sheet.png`; from cam05 and cam01 the shrub band hides the rostra, so QA cannot confirm it in the master (QA-02-13). |
| QA-01-12 golden-hour mood | lighting | **open** | 0.9 EV under, stone 5-9 deg cool (QA-02-4, QA-02-14). |
| QA-01-13 corner scrolls / maiden pose | ornament | **open** | at cam05 the corner figures read as bollards with no visible volute scroll pair (QA-02-10). |
| QA-01-14 box/maiden count | architecture | **closed by decision** | 12 boxes logged in arch_notes. |
| QA-01-15 vault coffers | architecture | **partially closed** | octagonal coffers exist; at cam04 they have no depth (QA-02-9). |
| QA-01-16 lagoon stair | architecture | **closed (unverified)** | cheek walls and repositioning reported by ARCH; not resolvable at these camera distances. |
| QA-01-17 placeholder materials | materials | **closed** | 0 placeholders, 31 library materials in master.blend. |
| QA-01-18 capital repetition | ornament + lead | **partially closed** | variants now spread, but the per-instance difference is a hue tint (yellow vs salmon capitals side by side), which reads as a colour error rather than weathering (QA-02-2). |
| QA-01-19 shore / lawn / houses | environment | **partially closed** | rip-rap boulders break the waterline; the cam06 lawn is still a flat olive plane and the backdrop houses are grey boxes (QA-02-15). |
| QA-01-20 dome blow-out | lighting + materials | **closed** | cam06 dome cap lum 160.1 against a 140.8 background, no clipping. |

## Defect list — round 02

Severity: **blocker** = must be fixed before the next gate; **major** = visible at hero distance, fix in the polish loop;
**minor** = specific view or close approach.

| id | cam | owner | sev | defect (measurable) | where | acceptance test |
|---|---|---|---|---|---|---|
| QA-02-1 | 05, 02 | architecture | **blocker** | Dome reads absent from a close, low, oblique station: visible dome+drum rise above the attic cornice is **3.7 % of the on-screen rotunda width vs 12.2 % in ref 063**; no dome cap is visible at all, only a sliver of drum wall. The cam01 apex is correct, so the cause is the attic parapet / corner-block height relative to the springing, not the apex. | `ARCH_rotunda_attic_*`, `_drum*`, `_dome`, `arch_params.py` | From `CAM_qa_05`: dome cap visible above the attic cornice across >= 60 % of the rotunda width, visible rise >= 9 % of the on-screen rotunda width, compared in the same 940-px-normalised crop pair. cam01 apex must stay within 2 % of ref 169 **and** ref 085. |
| QA-02-2 | 01, 02, 05 | materials | **blocker** | "Clean CAD + decal" stone at 1:1 (hero crop x 760-1230 y 250-460): hard-edged pale blotches 30-120 px across on the entablature and spandrels; an **olive-green cast** on shaded piers and arch soffits; capitals and urns differ by *hue* (a yellow capital, hue ~55, beside a salmon one, hue ~20) rather than by weathering; shafts are smooth untextured cylinders. | `MAT_concrete_*`, `MAT_column_*`, `PFA_instance` seed wiring | The same 1:1 crop: no patch with a hard edge wider than 20 px; shaded stone hue within 34-42 deg (measure with `qa_measure.py regions`); per-instance hue spread <= 4 deg with the variation carried by dirt/streak masks; flute shading broken by grain. QA re-crop accepted. |
| QA-02-3 | all | materials (+ architecture for the bevels) | **blocker** | **No edge wear anywhere.** At 1:1 every arris is razor sharp (the 3 cm bevels do not read), there are no rain streaks under any cornice, no dust in the recesses, and **no algae / damp band at the waterline** on the podium, the stair or the rip-rap — a stated non-negotiable and the headline failure of attempts 1-2. | `MAT_concrete_*` weathering maps, `ARCH_site_rostra_*`, `ENV_riprap_*` | A 0.3-0.6 m dark damp/algae band on every stone surface meeting z = WATER_Z; vertical streaks under the main cornice and the attic string course; dust in the capital and coffer recesses; all three visible in the hero crop x 700-1170 y 560-770 side by side with the ref 169 crop at the same waterline. |
| QA-02-4 | 01, all | lighting | **blocker** | Exposure **0.9 EV under** ref 169, measured against the AgX response curve (table above): sunlit attic 142.4 vs 179.4, dome 158.4 vs 192.6, water reflection 108.9 vs 140.7. Lighting's "+0.15 EV" estimate is short by ~0.75 EV because AgX compresses the display-referred deficit. | `scene.view_settings.exposure` (-3.2911), `light_build.py` / `light_presets.py` | `view_settings.exposure` ~ **-2.39**; re-measure the six regions with `scripts/qa_measure.py`: sunlit attic within +-10 % of 179.4 and sky top within +-10 % of 175.2 on a fresh Cycles hero. |
| QA-02-5 | 03 | lead | major | `CAM_qa_03` is still inside the column row (round-1 QA-01-5 not applied here): the near shaft fills the left 45 % of frame, the rotunda occupies < 15 %, and the column bases and ground are out of frame entirely (target z = 18 m with a 20 mm lens tilts the whole composition up). The camera, not the model, is what this column of the table measures. | `CAM_qa_03_colonnade_walk` in `scripts/qa_cameras.py` (40, -21, 1.7), lens 20, target (0,0,18) | Two near shafts framing the view at x 0-20 % and 45-70 % of frame width; column bases visible in the bottom 15 %; the rotunda's dome + attic inside the middle third, as in ref 128. Letterboxed blend within 3 % on the apex and base rows. |
| QA-02-6 | 01, 05, 06 | environment + materials | major | Lagoon tonal range: the reflection column is right, but the flanking water is **3.9x too dark** (mid-left band lum 34.9 vs ref 169's 134.5) and the near field is an over-saturated cyan (39,88,121 sat 0.678, 25 % brighter than ref 169's 45,68,79 sat 0.426). The lagoon reads as a black mirror with a bright stripe. | `MAT_water_lagoon` (murk/absorption, roughness falloff), `ENV_lagoon_water` | Mid-lagoon left band within 30 % of ref 169's luminance at the same fraction of the water band; near-water saturation <= 0.45; measured on the next Cycles hero with the same boxes. |
| QA-02-7 | 01, 02 | environment | major | The colonnade wings are buried in trees: north band (x 60-560, y 480-600) lum **66.0 vs ref 169's 137.2** (52 % dark), south band 88.2 vs 140.5 (37 % dark). QA-01-6 asked for a screen *behind* the wings; the screen is now in front of them, so the hero loses the sunlit colonnade that carries the composition in ref 169. | `ENV_tree_instances_*` positions along both wings | After the QA-02-4 exposure fix: both colonnade bands within 25 % of ref 169's luminance at the same boxes; the sunlit shaft faces readable across at least 60 % of each wing's width in the hero. |
| QA-02-8 | 06, 02, 05 | lighting | major | Mist/haze too dense and the wrong colour: at cam06 everything past ~150 m collapses to **saturation 0.076-0.091 at hue 60-76 deg** (grey-olive) — dome, lawn and lagoon all read as the same grey; in cam02 the left third of the frame is a grey wall; in cam05 the background is a flat grey band. Mist start 30 m / depth 700 m. | `COMP_golden_hour` mist, `world.mist_settings` | At cam06 the far shoreline keeps saturation >= 0.2 and the lagoon still shows a reflection; haze hue in the 30-45 deg warm band, not olive; the rotunda-to-background contrast at cam06 at least 1.5:1. |
| QA-02-9 | 05, 04, 01 | ornament | major | Relief reads as an engraved decal, not carving. cam05: the front attic panel is a near-uniform field in which no figure casts a shadow, where ref 063 shows overlapping figures with 10-20 cm shadow. cam04: the coffers are flat inset outlines where ref 083 shows deep boxes with hard shadow. | `ORN_attic_panel_v1..3`, `ARCH_rotunda_vault_coffers_*` | At cam05 the panel box's luminance standard deviation >= 60 % of ref 063's over the equivalent box; coffer depth >= 15 cm casting visible shadow at cam04; both shown as side-by-side crops. |
| QA-02-10 | 05, 01 | ornament | major | Attic corner figures read as featureless bollards and the paired volute scrolls (QA-01-13) are not visible flanking them, although ref 063 shows both plainly at the same distance. | `ORN_maiden_*` / attic corner figures, `ORN_corner_scroll` routing on the 8 `volute_scroll` finial sockets | The cam05 top crop (x 400-900, y 0-170) shows an identifiable head / torso / drapery break-up on the corner figures and a scroll pair on each corner cap. |
| QA-02-11 | — | lead | major | **Deliverable missing**: master.blend contains no curve objects and no `CAM_flythrough_path` / `CAM_flythrough` / `CAM_flythrough_target`. `scripts/light_flythrough.py` builds them; `build_master.py` does not append them, so the Phase-5 flythrough deliverable does not exist in the assembled file. | `scripts/build_master.py`, `scripts/lead_build.sh` | After `scripts/lead_build.sh`, all three `CAM_flythrough*` objects present in master.blend and the path evaluable (QA re-runs the inspection). |
| QA-02-12 | 04, 01 | lighting | major | The rotunda's barrel-vault soffits are still light-starved: cam04 soffit band lum 21.3 = **0.20 of the frame's own sky**, vs ref 083's 99.9 = 0.58. The central coffer field was fixed by the probes; the vaults around it were not. | `LIGHTPROBE_rotunda` extent, `LIGHT_rotunda_bounce` | Soffit / sky ratio >= 0.45 at cam04 in Eevee, and confirmed within 25 % of that in a Cycles cam04 render (so the fix is not Eevee-only). |
| QA-02-13 | 05, 02, 01 | environment | minor | Vegetation collides with the architecture and hides it: two dark conifers stand in front of / through the rotunda's SE face at cam05, and the shore shrub band is tall enough to hide the podium — and with it the QA-01-11 Greek-key band — in cams 02 and 05. | `ENV_tree_instances_*`, `ENV_shrubs_shore`, `ENV_shrubs_pen` | No tree crown within 6 m of the rotunda podium; shrub band <= 1.2 m along the rostra so the Greek-key band is legible from cam05 at 720 px. |
| QA-02-14 | 01 | materials + lighting | minor | Sunlit stone 5-9 deg cool: attic hue 33.9 vs ref 169's 39.1, dome 29.3 vs 37.4, columns 24.8 vs 33.8; saturation also low (attic 0.503 vs 0.577). Exposure will not fix it — the measured response is **-1.1 deg of hue per +1 EV**. | `MAT_concrete_*` base hue, `LIGHT_sun` temperature | After the QA-02-4 exposure change, all three regions within 4 deg of hue and 0.06 of saturation of ref 169. |
| QA-02-15 | 06 | environment | minor | cam06 ground is a flat olive plane with no readable paths or roads, and the backdrop houses are plain grey boxes on the horizon. | `ENV_terrain_ground`, `ENV_backdrop_houses` | OSM paths and the Marina street grid readable at cam06 1280x720; backdrop houses with roof pitch and per-building colour variation. |
| QA-02-16 | — | lead | minor | Render budget stale: the Cycles hero at 1080p/128 spp went 65 s -> **446 s** (6.9x) between rounds. Extrapolating, the Phase-5 4K hero at 768 spp is roughly 1.5-2.5 h, not the 25-40 min estimated in round 1; the Eevee previews are 2-7x slower too (33-55 s per camera). | `light_presets.FINAL_SAMPLES`, `docs/lighting_notes.md` | A measured 4K timing test logged before Phase 5, or `FINAL_SAMPLES` revised so one hero frame fits the budget. |
| QA-02-17 | 02 | lead | minor | `CAM_qa_02`'s station does not match its canonical photo: the photo is a close three-quarter taken from the plaza (west) side showing the full podium and the Greek-key band; the camera sits on the NE shore across the water, so the podium is behind vegetation and the comparison measures two different views. | `CAM_qa_02_lagoon_ne_threequarter`, `reference/photos/canonical/cam_02_ne_shore_threequarter.jpg` | Either re-point the camera to the photo's station or re-pick the canonical photo (ref 062 was the intent); the letterboxed blend must put the photo's apex and podium-base rows within 3 %. |
| QA-02-18 | 01, 05 | environment | minor | Shore shrubs are a regular row of near-identical dark green pom-poms at 1:1 (hero crop y 640-700), all within one size and one hue; ref 169's shore mixes mounded foliage with warm dry reeds (144,108,55). | `ENV_shrubs_shore`, `ENV_shrubs_pen`, `MAT_shrub_*` | No two adjacent shrubs with the same silhouette; size spread >= 2:1; warm dry fraction >= 20 % of the band area; hue spread >= 25 deg across the band. |

## Notes for the lead

1. **Exposure is settled by measurement: +0.9 EV.** Materials was right, lighting was not; the disagreement came from
   reading a 20 % display deficit as a 20 % scene deficit under AgX. `scripts/qa_exposure_sweep.py` is in the repo so
   the next argument can be settled the same way in 2 minutes of render time.
2. **QA-01-4 needs no camera change.** The acceptance test I wrote in round 1 mixed an aspect-dependent number
   (attic width as a fraction of frame *width*, taken from a 1.46:1 photo) with two vertical clauses; the three cannot
   all hold in 16:9. Measured against frame height the current lens 20 / shift 0.06 matches the user image to 4.6 %
   relative, and both vertical clauses pass. I have restated the test in the table above.
3. **The dome arbitration was correct and should not be re-opened**, but the cam05 read (QA-02-1) says the attic
   parapet, not the apex, is now the occluder. That is a small local change and it should be checked against the cam01
   overlays so the good numbers there survive it.
4. **The next round is a materials round.** Three of the four blockers (QA-02-2, -3, -4) and two of the majors are
   surface and light, not geometry. Nothing in this build will read as a photograph until there is weathering,
   an algae line and a full stop more light.
