# Status / handoff (lead). Newest at the bottom. Three lines per entry.

## 2026-09-07 15:05 · session restart, Phase 3 start
Merged: materials branch (library v1: concrete family, columns, dome membrane, water, foliage cards, ground, backdrop) into main at 4364e98. All five asset .blends now on main.
In flight: nothing (all worktrees idle; arch/env/light/orn branches fast-forwarded to main before dispatch).
Next: rebuild master.blend with the library, view hero, arbitrate dome (QA-01-1), dispatch wave 1 (architecture + environment).

## 2026-09-07 15:15 · wave 1 dispatched
Merged: 8ac4870 (rules, status, dome arbitration). master.blend rebuilding with the materials library in the background (hero Cycles render to renders/previews/qa/p3mat_*).
In flight: ARCH fix agent (branch architecture, Opus: QA-01-1 dome, maiden sockets to box base, greek-key frieze sockets, bevels/rustication, 14/15/16); ENV fix agent (branch environment, Opus: QA-01-2, 3 geometry, 6, 7, 8, 19).
Next: judge the materials hero from master; when a wave-1 agent reports, merge and dispatch wave 2 (ornament: QA-01-10/11/13/18; lighting: QA-01-9/12/20); then QA round 2 on Opus.

## 2026-09-07 15:20 · master rebuilt with materials; hero judged
Merged: master.blend rebuilt (28 library materials, 28 placeholders remapped); Cycles hero at renders/previews/qa/roundp3mat_01_lagoon_hero_cycles.png, composite renders/qa_comparisons/p3mat_cam01_vs_ref169.png.
Lead read: concrete/columns/water direction right. Sunlit attic (178,134,89) vs ref 169 (212,167,103): 17 % dark, less golden; reflection centre (86,70,54) vs (129,95,57): 35 % dark; sky flat grey-blue; dome absent (ARCH), shore slabs + blob trees (ENV) in flight.
Next: lighting agent (wave 2) owns exposure/warmth/sky (QA-01-12) with these numbers; re-judge water after ENV closes the lagoon volume; hero camera may need re-framing once the dome rises (apex now at 5 % from top).

## 2026-09-07 15:35 · cap raised to 4; wave 2 dispatched alongside wave 1
Merged: mission.md audit (checklist reports viewability + deliverables each round); CLAUDE.md concurrency cap 2 -> 4 (user).
In flight: ARCH (architecture), ENV (environment) from wave 1; ORN fix agent (branch ornament, Opus: QA-01-10/11 unit + array helper/13/18); MAT fix agent (branch materials, Opus: QA-01-3 water shader, stone luminance/warmth vs ref 169, QA-01-20 dome, leaf translucency, pine needles).
Next: merge each branch as it reports, rebuild master, then lighting (QA-01-9/12) and QA round 2 on Opus.

## 2026-09-07 15:58 · architecture merged (cf419b4)
Merged: ARCH fix round: dome rise 9.4 m / drum 5.1 m / apex 52.8 (apex +1.8 % vs ref 169, -1.7 % vs ref 085; drum 51 px above attic), maiden sockets at box base, 126 frieze_run sockets (98 greek_key) + meander geometry, 3 cm bevels on 249 objects, rustication, octagonal coffers, stair cheek walls; 12 boxes kept (decision in arch_notes). Composite renders/qa_comparisons/arch_06_phase3_sheet.png, lead accepts.
In flight: ENV (environment), ORN (ornament), MAT (materials); LIGHT dispatched now (branch lighting, Opus: QA-01-9 probes, QA-01-12 exposure/warmth/haze, QA-01-20 dome check).
Next: merge ENV/ORN/MAT as they report, rebuild master (hide ARCH_*_meander_* if ORN units are arrayed), re-frame hero cam for the taller dome, QA round 2. Note for QA: qa_silhouette's r>b+0.06 sky mask misses the pale dome; use arch_silhouette.py flatten / arch_inspect.py --alpha.

## 2026-09-07 16:45 · environment merged (1bc0491); Blender hygiene rule
Merged: ENV fix round: 1461 shrub objects from leaf cards, closed lagoon volume (0 open edges), tree screens (sky through bays N 1.7 % / S 9.5 %), cam03 clear, hall facade with green door, 1273 rip-rap boulders, satellite paths. LOD1 7.67 M tris. Composite renders/qa_comparisons/env_fix_round_sheet.png.
In flight: ORN, MAT, LIGHT; ENV asked for a follow-up (peninsula planting band 9-18 m back from the water; cam02 stays where it is, decision: the reference cluster and OSM shoreline leave no room). MAT asked for MAT_leaf_pine, MAT_shrub_light/_dry, MAT_backdrop_roof/_skylight/_door_green.
Next: user reported swapping from idle Blender processes: scripts/blender_watchdog.sh added, rule in CLAUDE.md, loop running in the lead session; all agents notified. Then merge ORN/MAT/LIGHT, rebuild master, QA round 2.

## 2026-09-07 17:30 · ornament merged (a1bdcc5)
Merged: ORN fix round: attic panels 15/13/13 figures, 62-64 % coverage; ORN_greek_key (0.60 m) / ORN_rosette_band (1.20 m) units + orn_lib.array_unit_along_run (tested on 128 sockets, 1.8 mm error); ORN_corner_scroll; maidens hunched with arms on the rim; capital variants distinct. Composite renders/previews/ornament/qa01_ornament_fixes.png.
In flight: MAT (adds instance_seed attribute wiring + 6 materials), LIGHT, ENV follow-up (peninsula planting).
Next (lead, build_master.py): route finial sockets by subtype (volute_scroll -> ORN_corner_scroll), array rosette_band/greek_key on frieze_run sockets and hide ARCH_*_meander_*; then rebuild master, QA round 2.

## 2026-09-07 16:35 · master rebuilt (ARCH+ENV+ORN+MAT v1); hero cam widened
Merged: master.blend 154 MB, 5725 objects, LOD1 14.45 M tris (up from 8.5 M: shrubs 2.8 M at all LODs + bevels; QA to report viewport performance). Eevee hero renders/previews/qa/roundp3cam_01_lagoon_hero.png: apex 2 % from top (too tight), shoreline 66 %. Hero cam now lens 20 / shift 0.06 (expected apex ~10 %, shoreline ~66 %).
In flight: MAT (water, stone warmth, seed wiring, 6 new materials), LIGHT (probes, exposure, haze), ENV follow-up (peninsula planting). Watchdog v2 running (v1 killed its own shell; fixed to match the Blender binary only).
Next: merge the three, rebuild master, dispatch QA round 2 (Opus) with the silhouette-tool caveat and the viewport numbers.

## 2026-09-07 17:05 · lighting merged (63b4329)
Merged: LIGHT fix round: two irradiance volumes + plaza bounce disk (ceiling 60,46,26 in Eevee; Cycles truth showed the vault is light-starved, ref 083 is ceiling-exposed), exposure bias 1.10, sky saturation node, aerosol 1.6, mist 700 m warm haze; sunlit attic 0.86 of ref 169 (was 0.70), sky within 5 %. Composite renders/qa_comparisons/light_r07_qa0112_hero.png.
Pipeline: probes must be baked in master after assembly: scripts/lead_build.sh = build_master.py + light_probes.py --bake --save. Dome membrane 46 % too dark / 9.5 deg cool vs concrete (albedo) -> materials agent.
In flight: MAT, ENV follow-up. Next: merge both, scripts/lead_build.sh, QA round 2 on Opus.

## 2026-09-07 17:20 · environment follow-up merged
Merged: peninsula planting band (319 bushes, 6 low trees; vegetation cover in the podium-to-water strip 16 -> 26 %), env_lib.mat_or remaps to MAT_leaf_pine / MAT_shrub_light / MAT_shrub_dry as soon as they exist; ENV LOD1 8.39 M tris. Composite renders/qa_comparisons/env_peninsula_band.png.
In flight: MAT only. Next: merge MAT, scripts/lead_build.sh, QA round 2 on Opus.

## 2026-09-07 17:45 · materials merged; all round-1 owners done
Merged: MAT fix round: water (distance-filtered ripples, murk, reflection 108,80,48 vs ref 129,95,57; near water blue-green), concrete +20-25 % albedo (attic hue within 4.8 deg, 14 % under in luminance, asks lighting for +1 EV), dome membrane cream (0.905,0.72,0.44), leaf normal+translucency maps, MAT_leaf_pine/shrub_light/shrub_dry/backdrop_*, efflorescence, instance_seed hashed into PFA_instance (20 % spread over 6 capitals). Library 35 materials. Composite renders/qa_comparisons/materials_r2_water_stone.png.
In flight: none. Building master via scripts/lead_build.sh (assemble + probe bake), then QA round 2 (Opus).
Open for after QA: exposure (materials says +1 EV, lighting says ~+0.15; decide from the QA hero numbers), LOD1 tri count ~15 M.

## 2026-09-07 17:50 · master built with probes; QA round 2 dispatched
Merged: master.blend rebuilt by scripts/lead_build.sh (6043 objects, LOD1 15.18 M tris, 31 library materials remapped, both irradiance volumes baked in 7.6 s).
In flight: QA round 2 (Opus, main checkout, commits only docs/qa_round_02.md, quality_checklist.md, scripts/qa_*.py, renders). Lead does not commit on main until QA reports.
Next: gate report to the user (one composite, score deltas per view, open defects); then Phase 4 polish round 1 by owner from the QA-02 list; exposure decision from QA's numbers.

## 2026-09-07 18:30 · QA round 2 in (0f68d6a): gate NOT passed, hero 2.17 -> 2.94
QA-02 blockers: 1 dome absent from cam05 (arch), 2 blotchy olive stone / per-instance hue (mat), 3 no edge wear or algae band (mat), 4 exposure +0.9 EV (light). Majors 5-12: cam03 framing (lead), lagoon flanks dark + cyan near field (env+mat), colonnades 37-52 % dark and buried in trees (env), haze greys cam06 (light), relief reads as decal (orn), corner figures/scrolls (orn), flythrough path missing from master (lead/light), vault soffits dark (light). Full list docs/qa_round_02.md; composite renders/qa_comparisons/round02_gate.png.
Lead read agrees with QA (strict, keep on Opus). Viewport: opens 1.8 s, LOD1 15.2 M tris, Eevee 33-55 s/cam (2-7x slower than r01), Cycles hero 446 s: performance is a defect to assign (env shrubs LOD-less, arch bevels).
Next: gate report to the user, then Phase 4 polish round 1: lead (cam03, exposure -2.39, flythrough path into master), then mat + light first, arch + env + orn second, 4 at a time.

## 2026-09-07 18:45 · Phase 4 polish round 1 dispatched (4 agents)
In flight: MAT (QA-02-2 stone blotch/olive, -3 edge wear + algae band, -6 water shader), LIGHT (QA-02-4 exposure +0.9 EV, -11 flythrough objects into lighting.blend, -8 haze, -12 soffits), ARCH (QA-02-1 dome from cam05, bevel/LOD perf), ENV (QA-02-7 wings buried/dark, -6 lagoon flanks, shrub LODs perf). ORN (QA-02-9 relief as decal, -10 corner figures/scrolls) queued for the next free slot.
Lead: QA-02-5 cam03 re-station (qa_cameras.py) now. Gate report sent to the user with round02_gate.png.
Next: merge as they report, lead_build.sh, QA round 3.

## 2026-09-07 19:30 · architecture polish merged
Merged: ARCH p4r1: QA-02-1 shown to be cam05's station (ref 063 fit: 115 m, 40 mm), no geometry change; coffer depth 0.20; bevels off in viewport (-20 % ARCH viewport tris); arch_perf.py shows ARCH is 8 % of LOD1 / 6 % of LOD0. cam05 re-stationed by the lead, cam03 with QA.
In flight: MAT, LIGHT, ENV, QA (cam03). ORN queued. Eevee LOD1 render set for previews -> QA to add to qa_render_round.
Next: verify cam05 by render; merge the rest; lead_build.sh; QA round 3.

## 2026-09-07 19:45 · cam05 verified, ornament polish dispatched
Merged: cam05 at (28.1, 111.8, 1.5)/40 mm shows the dome + drum above the attic like ref 063 (renders/qa_comparisons/lead_cam05_restation.png); QA re-tests QA-02-1 at that station in round 3.
In flight: MAT, LIGHT, ENV, ORN (QA-02-9 relief depth, -10 corner figures), QA (cam03 calibration + LOD1 Eevee pass in qa_render_round).
Next: merge as they report; lead_build.sh; QA round 3.

## 2026-09-07 20:15 · cam03 station from QA applied; Eevee previews at LOD1
Merged: cam03 = (81.0, 12.04, 1.7), target (0,0,9.2), 18 mm (south-wing walk centreline, rotunda between columns 026/028; QA composite renders/qa_comparisons/qa_cam03_restation.png). qa_render_round --eevee now renders LOD1 (50.1 M -> 15.2 M visible tris). QA-02-1 downgraded to major (cap still reads ~half the photo's depth from cam05; re-measure in round 3).
In flight: MAT, LIGHT, ENV, ORN. Next: merge as they report; lead_build.sh; QA round 3.

## 2026-09-07 20:40 · environment polish merged (9a68bc1)
Merged: ENV p4r1: wings de-shadowed (entablature 78 % lit from 31/4 %; wing luminance 0.75/0.82 of ref at +0.9 EV), sky through bays N 23 % / S 30 %, lagoon shelf bed + shore eucalyptus moved (flank 0.28 -> 0.89 of ref), shrub LODs (ENV LOD1 4.84 M, master LOD1 11.6 M), houses with pitched roofs. Composite renders/qa_comparisons/env_r3_sheet.png.
In flight: MAT, LIGHT, ORN. Open for materials: near-water cyan hue (sat 0.46 vs ref 0.11), hall wall texture (MAT_backdrop_building flat cream).
Next: merge the three; lead_build.sh; QA round 3 (re-time Eevee on a quiet machine).
