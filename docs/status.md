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

## 2026-09-07 21:20 · ornament polish merged (b509ce8)
Merged: ORN p4r1: attic panels re-grounded (p10 depth 0.168 -> 0.022 m, sun-blocked 0.3 -> 6.6 %, 20-22 figures in three depth registers), corner figures slimmed with side cascades, corner scrolls as a real pair enclosing ARCH's volutes, colonnade capital LOD0 80k -> 48k (-3.6 M tris in master). Sheet renders/previews/ornament/orn3_qa02_9_10_sheet.png.
In flight: MAT, LIGHT. Not done by ORN: capital leaf and keystone depth (next round if QA still flags).
Next: merge MAT + LIGHT; lead_build.sh; QA round 3.

## 2026-09-07 22:10 · materials polish merged (e550acc)
Merged: MAT p4r1: blotch/olive fixed (warped cells, streak tint no longer green, per-instance hue spread 35 -> 1.2 deg, value spread 19 %), edge radius 0.10 m, ledge run-off streaks, algae on by default + damp zone on lawn/soil/gravel at the waterline, lagoon no longer a light sink (flank +4 % vs ref), backdrop stucco detail. Composite renders/qa_comparisons/mat_r3_stone_water.png.
Open: sunlit stone still pale/low-chroma vs ref 169 (R-B spread 81 vs 127) — illuminant/exposure, with lighting; hall opening is an unfilled hole in ENV's hall geometry (next ENV round); near-water saturation target disputed (QA 0.43 vs ENV 0.11 on different crops) — QA to fix one crop in round 3.
In flight: LIGHT. Next: merge LIGHT; lead_build.sh; QA round 3.

## 2026-09-07 22:30 · CHECKPOINT (user closing the machine)
Merged into main: all Phase 4 polish round 1 branches except lighting (architecture, environment, ornament, materials). cam03/cam05 re-stationed, Eevee previews at LOD1. master.blend on disk is from 16:42 (pre-polish); rebuild with scripts/lead_build.sh before QA round 3.
In flight at checkpoint: LIGHT p4r1 on branch lighting (13 commits ahead of main; QA-02-4 exposure +0.9 EV, -11 flythrough objects, -8 haze, -12 soffits, plus the chroma request: warmer sun / less blue fill, R-B spread >= 110). Told to commit and stop; see its last commit message and docs/lighting_notes.md for state.
Resume: merge lighting (`git merge lighting`), run scripts/lead_build.sh, dispatch QA round 3 (Opus; re-time Eevee on a quiet machine, fix one near-water crop for the saturation dispute, re-test QA-02-1 at the new cam05), then polish round 2 by owner. Open non-QA items: hall opening is a hole in ENV geometry; capital leaf / keystone depth (ORN); FAR_RADIUS 130 -> 105 (ENV perf).

## 2026-09-07 22:40 · lighting polish merged; checkpoint complete
Merged: LIGHT p4r1 (d62402d): exposure +0.9 EV closed (attic 177.6 vs ref 179.4), flythrough objects now built by light_build.py and present in lighting.blend/master, shaped mist (far-shore sat 0.30), 8 soffit emitters (Cycles 0.48, Eevee 0.36), chroma pass: SKY_STRENGTH 1.0, AgX High Contrast, SKY_GLOSSY_BOOST 3.0, EXPOSURE_BIAS 1.75 (attic R-B 97, target 110).
Caveats from lighting for round 3: its knob sweep ran at 960x540/32 spp and reads ~16 lum / ~20 R-B optimistic vs 1920x1080; interior FILL 7600 / VAULT_FILL 2400 want ~halving after the sky was halved (cam04 soffit/sky 0.80 now); aerial grey-olive is scene colour (env+materials), not haze.
Resume: scripts/lead_build.sh, then QA round 3 (Opus). All worktrees clean, all branches merged, no Blender running. Nothing in flight.

## 2026-09-07 · session resumed (lead on Fable 5.1)
State verified: main 99c8250, five worktrees clean, all branches merged, no Blender running. Stray untracked session.txt (terminal dump) left alone.
In flight: scripts/lead_build.sh (master rebuild + probe bake, log renders/logs/lead_build_r3.log). Next: QA round 3 (Fable 5.1 xhigh per the user; folds in lighting's two caveats: chroma re-measure at 1920x1080, interior fills ~halved), then polish round 2 by owner.

## 2026-09-07 · master rebuilt; QA round 3 + lighting r09 dispatched
Merged: master.blend rebuilt by lead_build.sh (9041 objects, LOD1 11.62 M tris, 34 library materials remapped, both probes baked).
In flight: QA round 3 (Fable 5.1 xhigh, main checkout; commits only qa docs/scripts/renders; touches renders/previews/qa/round03_RENDERS_DONE when renders finish). LIGHT r09 on branch lighting (Opus; chroma re-sweep at 1920x1080 for attic R-B >= 110, interior fills ~halved vs ref 083); waits on the QA marker before its first Blender run.
Next: gate report to the user from round03_gate.png; polish round 2 by owner from the QA-03 list (mat, env, orn, arch), code review (Opus, no Blender) of each branch before merge; lead_build.sh; QA round 4.

## 2026-09-07 · QA round 3 in (03eed9c): gate NOT passed, hero 2.94 -> 3.28; lighting r09 merged (8a9ab71)
QA-03: blockers 1 watchdog killed GPU renders (lead, fixed 7c164d5: centisecond cputime), 2 chroma at 1920x1080 (light+mat), 3 interior fills 2x (light), 4 hero 1:1 clean CAD: no flutes/streaks/recess dirt (mat+arch). Majors 5 cam05 clips apex, 6 cam02 station (lead, both re-stationed b/ 8a9ab71), 7 near-water sat, 8 coffers flat, 9 cam03 shaft, 10 north wing, 11 cam06 backdrop. Composite renders/qa_comparisons/round03_gate.png.
Merged: LIGHT r09 after Opus code review (merge with two latent nits in light_r09_sweep.py, no blockers): the AgX look was defined twice and master rendered at Base Contrast; now once in light_presets (High Contrast); attic R-B 97 -> 120 at 1920x1080, fills 1140/3960 W at 45 deg (Cycles soffit/coffer 0.54/0.38 vs ref 0.58/0.39; Eevee ignores the spread, viewport dome ~3x bright, open for lighting next round).
In flight (4 builders, Opus): MAT r4 (QA-03-2 albedo hue, -4/-02-3 wear, -7 water, -9/-15), ARCH p4r2 (flutes, base profile, coffer depth), ENV r4 (cam06 backdrop, north wing, cam05 conifers, shrubs, cam03 ground, hall hole), ORN r4 (capital tiers, rosettes, keystones). Next: code review + merge each, lead_build.sh, QA round 4 (Fable xhigh). Lead items still open: QA-03-16 4K timing, QA-03-17 saved-file preset.

## 2026-09-07 · lead items between waves
Done: cam05 35 mm (apex in frame, verified renders/previews/lead/*05_south_lawn_restation_r3.png); cam02 station: QA's (-40,15) is under a tree crown and every 40-60 m plaza/NW station puts the colonnade in front of the rotunda (8 candidates rendered), so cam02 stays at (-45,52) and QA round 4 gets the station search with its probe tool; build_master now saves the final Cycles preset (QA-03-17, verify on next lead_build).
Still open for the lead: QA-03-16 4K timing test (run on a quiet GPU after this wave, not during QA timings).
In flight: MAT, ARCH, ENV, ORN (see previous entry). Next: code review + merge each as it reports; lead_build.sh; QA round 4.

## 2026-09-07 · architecture p4r2 merged (28f0caf)
Merged after Opus review + fixes: flute hollows as semicircular arcs at equal arc angles (both LODs, 24 flutes), Attic base profile (plinth/torus/scotia/torus/apophyge), coffers 0.20 x width with three-register reveals, vault coffer gaps opened (70 mm rib) with a clearance clamp in L.plate; vault coffers were LOD0-only and hidden in every QA render (root of QA-03-8 on the vaults), now render at every LOD. ARCH LOD1 0.99 -> 1.10 M (master ~11.73 M). Review: docs/reviews/arch_p4r2_review.md. Sheet renders/qa_comparisons/arch_p4r2_sheet.png.
Hand-offs: ORN rim rosette sockets down 0.23 m (room face), ring-1 rosette sockets up 0.02 m (box floor); MAT flute-phase dirt on MAT_column_rose, rib grime on MAT_plaster_ceiling (both sent). In flight: MAT, ENV, ORN. Next: review + merge those; lead_build.sh; QA round 4.

## 2026-09-08 · ENV r4 (0478083) and MAT r4 (de62414) reported, both in Opus code review
ENV: env_city.py Marina/Presidio field (913 lots, 97 Presidio buildings, roads/paths; cam06 horizon std-dev 15.5 -> 30.5, dome/far-shore 1.15 -> 1.45:1), north-wing trees moved behind the wing, cam05 silhouette foliage 5.1 %, shrubs 2.5:1 / sd 62 %, cam03 ground bands, hall aperture sealed; ENV LOD1 4.80 M. Sheet renders/qa_comparisons/env_r4_sheet.png.
MAT: attic hue 32.8 -> 37.7 (ref 40.3), dome 29.8 -> 36.6, cavity/rib-grime/flute-relief inputs, streaks 0.31 m, edge 0.20 m; sat 0.44 vs 0.59 and R-B 102 vs 136 shown unreachable from albedo (two experiments < 0.02 sat), shade hue 42.5 vs ref 29.5, columns still 1.62x -> all to lighting r10. Sheet renders/qa_comparisons/mat_r4_sheet.png.
In flight: ORN r4; reviews of ENV and MAT. Next: merge both, lead_build.sh, dispatch LIGHT r10 (sat/R-B via sky fill, shade hue, columns, horizon haze QA-03-12, Eevee vault spread, cam06 mist) while ORN finishes; then QA round 4.

## 2026-09-08 · MAT r4 (be94cbb) and ENV r4 merged after review; master rebuild
Reviews: MAT one fix (mat_scene_check --ev 0.9 -> 0.0, applied by the lead), note that water DID change (chop/murk) and QA-03-7 must be judged from the crop pair. ENV no blockers; carried to ENV r5: _frame_box/coverage apply cam01 shift_y without the 16/9 aspect factor (~50 px), env_city azimuth helper has opposite handedness to the project (rename), clear() sampled only at quad centroids, build_all needs lagoon_field. Carried to MAT r5: MAT_backdrop_asphalt and MAT_backdrop_roof_tile (far field ships on placeholders), MAT_backdrop_forest too bright/yellow in sun.
Next: lead_build.sh now (ORN still in flight), dispatch LIGHT r10 from docs/briefs/lighting_r10.md, merge ORN when reviewed, rebuild again, QA round 4.

## 2026-09-08 · master rebuilt (8751 objects, LOD1 11.69 M); LIGHT r10 dispatched; ORN r4 reported (e90abec)
QA-03-17 closed: saved master carries GPU / 768 adaptive / OIDN / AgX High Contrast / CAM_flythrough_path. ORN r4: capitals were buried inside the bell (kalathos re-profiled, leaves on a spine, tips 0.40 m proud, rotunda LOD0 100k -> 64k), rosettes 0.21 m relief in 3 variants, keystone voussoir 0.30 m proud, `cavity` point attribute for materials. Blocking find: all 24 SOCKET_rosette_ceiling point +Y outward, rosettes buried in masonry -> architecture agent fixing socket frames now.
In flight: ORN code review, ARCH socket fix, LIGHT r10 (docs/briefs/lighting_r10.md). Next: merge ORN + ARCH fix, rebuild master, QA round 4 (Fable xhigh) while lighting finishes.

## 2026-09-08 · architecture socket fix merged (786966a); ornament review fixes in flight
Merged: rosette sockets re-framed: 16 band sockets on the vertical inner face of the base ring (r 14.18 m plane, z 23.19, +Y = face normal inward), 8 coffer-floor sockets facing down; scripts/arch_socket_check.py verifies all 24. Socket contract decision logged in docs/reviews/orn_r4_review.md.
In flight: ORN r4 review fixes (scallop phase, keystone plate, sockets.md rewrite), LIGHT r10. Next: merge ORN, lead_build.sh, QA round 4 (Fable xhigh; cam02 station search included), then MAT r5 (cavity attribute + AO in the capital shader, backdrop asphalt/roof tile, backdrop forest) and ENV r5 (shift_y aspect, azimuth helper, clear() corners).

## 2026-09-08 · ornament r4 merged (479f3f6); master rebuilt; MAT r5 + ENV r5 dispatched
Merged: ORN r4 after review + fixes (scallop phase, keystone plate, sockets.md contract, cavity contract in notes). Master rebuilt (log renders/logs/lead_build_r4b.log).
In flight (3 Blender agents): LIGHT r10 (chroma via sky fill, columns, horizon haze, Eevee vault, 4K timing), MAT r5 (cavity/AO into ornament shaders, backdrop asphalt/roof tile/forest, rib grime check), ENV r5 (review fixes, north-wing band re-measure).
Next: review + merge all three, lead_build.sh, QA round 4 (Fable xhigh; cam02 station search included).

## 2026-09-08 · MAT r5 reported (5c360d4), in review
MAT r5: ORN_NORMAL/ORN_AO nodes now match build_master (bakes plug into 27 per-asset materials on 307 instances), PFA_concrete reads ORN `cavity` (capital bell lum 152 -> 138, leaf tiers 8 -> 10), MAT_backdrop_asphalt / roof_tile added, MAT_backdrop_forest -55 % albedo (cam06 canopy moved only 5 %: 88 % of a far canopy pixel is atmosphere -> lighting), coffer ribs share the panel material so rib grime cannot separate them (ARCH: own material name for the rib plate). Sheet renders/qa_comparisons/mat_r5_sheet.png.
In flight: MAT r5 review, LIGHT r10, ENV r5. Carried: ORN bake cavity at 15-20 % of the diagonal and on all meshes; ARCH rib plate material name.

## 2026-09-08 · MAT r5 merged (c0a3b0b) after review (MERGE)
Note for future rounds: RENDER_LOD is 0 and only LOD1 sources carry the ORN bakes, so at render time the recess channel is the `cavity` attribute alone (the ORN_NORMAL/ORN_AO path shows only in LOD1 previews). MAT_backdrop_asphalt / roof_tile reach master only once ENV objects use those names (ENV r5 told).
In flight: LIGHT r10, ENV r5. Next: review + merge both, lead_build.sh, QA round 4.

## 2026-09-08 · ENV r5 reported (9c4b940), in review
ENV r5: shift_y aspect fixed (0.06 = 0.107 of frame height), city_az rename, clear() corners, build_all arg; north-wing band on the merged master 0.92/0.73 -> 0.95/0.76 of ref (both panels inside 25 %) by thinning the redwood screen's front rows; cam05 silhouette foliage 4.0 %; backdrop asphalt/roof tile names already in use, zero library warnings; ENV LOD1 4.60 M. Hand-off to lighting: the wing's own shaded stone is 16 points of the band's dark fraction. Sheet renders/qa_comparisons/env_r5_sheet.png.
In flight: ENV r5 review, LIGHT r10. Next: merge both, lead_build.sh, QA round 4.

## 2026-09-08 · ENV r5 merged (8d2c7e0) after review + fixes
Review: x1_exit did not move trees; the cam05 band under the corrected shift_y swept three hand-placed trees out of frame. Fix: hand-placed groups (peninsula bed, user-image spires) are pinned on both bands (never moved/dropped); band cleared by E1 screen crowns 18.5-23 -> 17-21 m: north-wing band 0.95 raw / 0.76 aligned, sky through bays 17.0 % (photo 16.5). Review file docs/reviews/env_r5_review.md.
In flight: LIGHT r10 (rig shipped on branch, cff3af4: attic sat 0.549 / R-B 120.8 / lum 180.9, columns 1.29x, near-water sat 0.270, Eevee-only vault cutoff; 4K timing test running, 60-min cap). Next: review + merge lighting, lead_build.sh, QA round 4.

## 2026-09-08 · LIGHT r10 reported (dae44ac), in review; QA round 4 brief written
LIGHT r10: exposure was 0.5 EV hot (AgX shoulder kills chroma): EXPOSURE_BIAS 1.75 -> 1.25 with sky camera/glossy boosts x1.41 to keep the sky and lagoon; attic sat 0.441 -> 0.549 (ref 0.588), R-B 102 -> 121 (ref 136), lum 181 (0.95), columns 1.59x -> 1.29x, near-water sat 0.270 = ref, Eevee vault fixed by an engine-conditional cutoff_distance (was mis-diagnosed as spread in r09). Open: shade hue 42.9 vs 29.5 (materials: blue reflectance in shadow), near-water hue 209 vs 192 (env: upwelling green), sky_left/top 0.92 vs 1.17 (partly framing), cam06 1.22:1 (mist cannot raise it), 4K timing test stalled twice in the tail (compositor suspected; FINAL_SAMPLES 768 unvalidated at 4K).
Next: merge lighting after review, lead_build.sh, QA round 4 from docs/briefs/qa_round_04.md (Fable xhigh).

## 2026-09-08 · LIGHT r10 merged (2b6940e) + review fixes (b85eab3); master rebuilding; QA round 4 dispatched
Review fixes by the lead: energy_W seeded once (no compounding x8 on repeated Eevee calls), engine id match ("EEVEE" in engine), safe restore on failure; build_master ends with apply_viewport_eevee so the saved Eevee state carries the vault override (Cycles presets restore the physical energy from energy_W). Review file findings 4-8 (worktree-unsafe absolute paths in light_r10_measure/sheet, name literal, sweep import guard, meta provenance) carried to lighting r11.
In flight: lead_build.sh (log renders/logs/lead_build_r4c.log), QA round 4 (Fable xhigh, docs/briefs/qa_round_04.md; commits only qa docs/scripts/renders; lead does not commit on main until it reports). Next: gate report to the user, polish round 3 by owner from QA-04.

## 2026-09-08 · QA round 4 in (f4b4b33, 465ae52): gate NOT passed; hero 3.28 -> 3.28, cam02 +0.33, cam04 +0.31, cam06 +0.22, cam05 +0.06, cam03 -0.12
Closed: QA-03-1 watchdog, -2 attic chroma (hue 38.9 / sat 0.554 / R-B 122), -4 flutes, -8 coffers + rosettes, -13 conifers, -15 capitals, -17 saved preset; Eevee 11-24 s/cam. cam02 re-stationed by QA to (70.5, 25.6, 1.1)/24 mm (SSE shore path; NE ref-062 station unreproducible on this build, QA-04-11). 4K: compositor exonerated (177 s at 16 spp); 768-spp frame still unproven.
QA-04 blockers: 1 Eevee vault black (light), 2 shade collapsed/yellow-green after the -0.5 EV (light), 3 stone still clean CAD at 1:1, third round (mat). Majors: 4 hero shoreline bare quay (env), 5 columns 1.27x (light+mat), 6 wings 0.63/0.66 of ref (light+env), 7 Cycles coffer 0.26 + no rib/panel difference (light+mat, ARCH rib material name), 8 near-water hue 209 / reflection grey (env+mat). Composite renders/qa_comparisons/round04_gate.png.
Dispatching polish round 3: LIGHT r11, MAT r6, ENV r6, ARCH mini (rib material name, QA-04-11 measurement). Lead: cam05 target z 21.5 (QA-04-10).

## 2026-09-08 · architecture mini-round merged (083937b) after review (MERGE)
Rib plates (ARCH_rotunda_ceiling_ribs + 8 vault coffer plates) carry MAT_plaster_ceiling_rib (placeholder until MAT r6 ships it; colour added to common.PLACEHOLDER_COLORS). Ref 062 fit: D 91.7 m / 42.4 mm, dome cap needs D > 76 m: no proportion change (decisions.md). Flag for ENV r7: OSM NE shoreline likely short (fitted station in water while the photo's foreground is garden).
In flight: LIGHT r11, MAT r6, ENV r6. Next: review + merge, lead_build.sh, QA round 5.

## 2026-09-08 · ENV r6 reported (8995384), in review
ENV r6: shore cap is now a sight line to the Greek-key course from the lagoon cameras (shrubs p90 2.83 m, tallest 3.59 m, podium base hidden 78 %, key band visible 93.6 % from cam05), 3 willows at ref 169 positions, north wing band 1.00 of ref (foliage 74.6 -> 37.8 %), cam06 8 roof colours / 13 footprints, cam02 shore edge. Probe shows the near-water teal is MAT_water_lagoon, not the bed (0.00 % change from a magenta bed at grazing angles) -> materials told; new name MAT_lagoon_bed for materials. Note: qa_round_04 (e) has the wing compass labels swapped (frame-left = south wing). ENV LOD1 4.66 M.
In flight: ENV review, LIGHT r11, MAT r6. Next: merge, lead_build.sh, QA round 5.

## 2026-09-08 · ENV r6 merged (8995384); review follow-up in flight
Review (docs/reviews/env_r6_review.md): visual result stands; four maintenance fixes sent back (hand-copied camera stations in the sight-line cap, bed classified as architecture, loose verts on ENV_lagoon_bed, global 4 m shrub ceiling).
In flight: ENV follow-up, LIGHT r11, MAT r6. Next: merge, lead_build.sh, QA round 5.

## 2026-09-08 · ENV r6 follow-up merged (3c3ad97): stations now read from qa_cameras.py, bed compacted, numbers unchanged (LOD1 4.66 M)
In flight: LIGHT r11 (branch shows Eevee vault x6/21 m: coffer gap 0.227 -> 0.062; Cycles coffer 0.261 -> 0.387), MAT r6 (macro grunge maps, waterline, MAT_lagoon_bed, water teal, ribs). Next: review + merge both, lead_build.sh, QA round 5.

## 2026-09-08 · MAT r6 reported (e7adc25), in review
MAT r6: cause of "clean CAD" was texture scale (the only photo input was a 2.5 m tile sampled 40x below its texel size); three macro grunge maps (0.3-3 m, CC0 ambientCG, mat_make_grunge.py) drive albedo value + roughness at 3-5.5 m tiles; overhang AO probe for cornice run-off; damp/algae waterline zone; patches; MAT_plaster_ceiling_rib (ref 083) + in-coffer gradient; MAT_lagoon_bed; shore foliage x1.4; columns hue 26.8 (pass), lum 119. Attic std 0.476 -> 0.598 of ref (bar 0.60), entablature 0.51 unchanged (hand-off ARCH: cornice projection / dentil depth), near-water hue 204 (hand-off lighting: horizon sky). Sheet renders/qa_comparisons/mat_r6_sheet.png.
In flight: MAT review, LIGHT r11. Next: merge both, lead_build.sh, QA round 5. Carried to ARCH r4: entablature cornice/dentil depth (QA-04-3 second half).

## 2026-09-08 · LIGHT r11 reported (822e92d), in review
LIGHT r11: QA-04-1 root cause = probe bake on the Eevee cutoff rig (bake now forces the physical rig; EEVEE_VAULT x6/21 m: Eevee coffer 0.034 -> 0.325 vs Cycles 0.387); QA-04-7 closed (FILL 3648 W, VAULT_FILL 3564 W: Cycles coffer 0.387); QA-04-2 shade hue reassigned to materials with three measured levers, SHADE_FILL rig shipped at 0 W; sun angle confirmed against ref 169's shadow structure (-3 px); viewport preset raytracing on / light_threshold 0.01 (decisions.md). Sheet renders/previews/lighting/light_r11_sheet.png.
In flight: MAT r6 review, LIGHT r11 review. Next: merge both, scripts/lead_build.sh (mandatory: build then bake), QA round 5 (Fable xhigh; re-base cam03's shade test on a golden-hour reference).

## 2026-09-08 · MAT r6 merged (e7adc25) after review (MERGE, non-blocking findings)
Follow-ups sent to materials: gate mat_make_grunge's network fetch behind --fetch; drop the water sheen (its own table: -1 deg hue for a further-from-ref stone reflection); note ao_up probe (+25 % secondary rays on concrete) if the 4K budget blows; Macro darkens mean albedo ~5 % (do not re-tune base colour to chase it).
In flight: LIGHT r11 review fixes, MAT follow-up. Next: merge both, scripts/lead_build.sh, QA round 5.

## 2026-09-08 · polish round 3 fully merged (LIGHT r11 a72aee4, MAT r6 4336a12, ENV r6 3c3ad97, ARCH 083937b); master rebuilding; QA round 5 dispatched
Lighting review fixes: bake sequence proven (engine + rig restored via try/finally), no 0 W shade suns, viewport RT off (measured), 127 MB of intermediate previews dropped. Master: scripts/lead_build.sh (log renders/logs/lead_build_r5.log).
In flight: QA round 5 (Fable xhigh, docs/briefs/qa_round_05.md; lead does not commit on main until it reports). Next: gate report with trend; decide continue-polish vs approach change for the concrete; carried for ARCH r4: entablature cornice/dentil depth; ENV r7: OSM NE shoreline check.

## 2026-09-08 · QA round 5 in (6c109ef): gate NOT passed; hero 3.28 (third flat round), cam02 2.78, cam03 1.75 (-0.25), cam04 2.56, cam05 2.78, cam06 2.50
Closed: shoreline, columns hue, cam05 apex, north wing, Eevee vault not black, attic std 0.66. Blockers: QA-05-1 shade crushed (cam03 0.063 of sunlit; light), -2 hero stone now a dark isotropic dirt decal (attic lum 166, sat 0.64-0.84, anisotropy 0.64 vs 4.07; mat), -3 Cycles coffer 0.21 (merge regression, light+mat). Majors: -4 water hue 209 / reflection sat 0.11, -5 south wing 0.63, -6 entablature cornice/dentil shadows (arch). Composite renders/qa_comparisons/round05_gate.png. QA's 4K 768-spp timing render in progress (pid 90755, log renders/logs/qa_round05_4k.log); QA appends the result and commits when it exits.
Dispatched (waiting on the 4K pid before their first Blender run): LIGHT r12 (shade window first, sunlit budget relaxed, coffer combination), ARCH r4 (cornice/dentil projection), ENV r7 (south wing, shore shrubs sun reach, cam03 ground, cam06 streets, NE shoreline). MAT r7 follows after LIGHT r12 merges (decisions.md: sequential lighting -> materials). Next: reviews, merges, lead_build.sh, QA round 6.

## 2026-09-08 · CHECKPOINT (user closing the machine) — part 1: state of record
**Merged into main (all reviewed):** lighting r09-r11, architecture p4r2 + socket fixes + rib material, materials r4-r6 (+follow-ups), environment r4-r6 (+follow-ups), ornament r4. Lead items done: watchdog fix, cam02/cam05 stations, saved preset, lighting/materials review fixes. master.blend on disk = lead_build.sh after round 3 (9175 objects, LOD1 11.01 M, probes baked on the physical rig) = what QA round 5 scored.

**Scores by round (average per camera; target >= 4 every row, hero >= 4.5):**
| cam | r02 | r03 | r04 | r05 | trend |
|---|---|---|---|---|---|
| 01 hero | 2.94 | 3.28 | 3.28 | 3.28 | stuck three rounds |
| 02 NE 3/4 | 2.11 | 2.33 | 2.67 | 2.78 | slow up |
| 03 colonnade | 1.94 | 2.13 | 2.00 | 1.75 | declining (shade crushed) |
| 04 ceiling | 2.31 | 2.13 | 2.44 | 2.56 | slow up |
| 05 S lawn | 2.11 | 2.67 | 2.72 | 2.78 | flat |
| 06 aerial | 2.17 | 2.17 | 2.39 | 2.50 | slow up |
Round-05 report docs/qa_round_05.md (6c109ef), composite renders/qa_comparisons/round05_gate.png. Blockers: QA-05-1 shade crushed (lighting), QA-05-2 hero stone a dark isotropic dirt decal (materials overshoot), QA-05-3 Cycles coffer 0.21 (merge regression). Majors: -4 water hue/reflection, -5 south wing, -6 entablature cornice/dentil shadows.

**Decision log (docs/decisions.md, 2026-09-08):** shade deficit is structural (diffuse sky x0.8 vs camera sky x2.1 / lagoon x5.25), lighting r12 fixes the shade window first with the sunlit-saturation budget withdrawn; lighting and materials run sequentially on the merged master (materials r7 after lighting r12); geometry owners in parallel; if the hero does not move at round 6, texture-projection from reference photos for the concrete. Also: no rotunda proportion change (ref 062 fit 92 m / 42 mm), cam02 on the SSE shore path, rosette socket contract, viewport RT off / light_threshold 0.01, watchdog centisecond rule.

## 2026-09-08 · CHECKPOINT — part 2: in-flight agents at stop, processes killed
**4K timing (QA-03-16): killed at checkpoint** after 94 min with no frame (768 spp adaptive, cap 5400 s); QA's note is in docs/qa_round_05.md (66c7570). **Needs re-running**: QA recommends 4K at 128 spp fixed, adaptive off, outer wall-clock guard, before retrying 768.
In flight at checkpoint (each told to commit and stop; all three worktrees clean, no Blender run started by any of them because they were gated on the 4K pid):
- LIGHT r12, branch lighting (last bec0172): brief docs/briefs and the r12 section in docs/lighting_notes.md (§21: QA-05-7 accepted-deviation note done; shade-window work planned, not yet rendered). Resume: read notes §21 and the "lighting r12" dispatch text in this file's previous entry; measure on the lead's master.
- ARCH r4, branch architecture (last c3d94c2): QA-05-6 cornice/dentil derivations and the drum-ring re-measurement written in docs/arch_notes.md "round 4"; geometry change not yet built/rendered.
- ENV r7, branch environment (last 19b4514): measurement + code complete for south wing / shore / cam03 ground / cam06 streets / NE shoreline, no Blender run yet.
Not started: MAT r7 (after LIGHT r12 merges; macro amplitude/anisotropy down, attic lum back to 178-201, coffer gradient with lighting's fill, water hue/reflection, cam05 distance amplitude).
**Resume procedure:** git status in each worktree (should be clean); dispatch fresh agents on branches lighting / architecture / environment pointing at their notes' checkpoint sections; they rebuild + render, code review (Opus) each, merge lighting first, then dispatch MAT r7 on the rebuilt master; scripts/lead_build.sh (build + probe bake, never build_master alone); QA round 6 (Fable xhigh; brief pattern docs/briefs/qa_round_05.md); if the hero is still 3.28, start the photo-projection pass for the concrete (decisions.md). Watchdog: `scripts/blender_watchdog.sh --loop` (restart it; not running now). No Blender processes running at checkpoint.
Addendum from ENV r7's checkpoint report (19b4514): QA-05-5 south wing is LIGHTING's, not planting: the south face is raked at cos 0.318 vs the north's 0.991 under ref 169's own sun (az 118.3, el 7); fitting lum = A + k*cos to both wings gives this build A 61.7 / k 76.5 vs the photo A 97.9 / k 48.4, i.e. the sky term is 36 lum short (same root cause as QA-05-1). QA-05-10 shore band is a uniform 1.5-1.9x level deficit, not occlusion. The OSM NE shoreline is NOT short (satellite z18 agrees; renders/qa_comparisons/env_r7_shoreline.png). ENV's round-7 code (cam03 paving, walk level -0.60, edge planting, shore sun samples, cam06 road pad) is written and committed but not yet built or rendered; its chain scripts live in ENV's scratchpad and must be re-created from env_build.py on resume.

## 2026-09-09 · RESUME (new session): worktrees clean, no Blender running; rules updated; polish round 4 dispatched
User rules recorded in CLAUDE.md: QA critic Opus xhigh every round (Fable once, final gate), definition of done (hero >= 4.0 or two rounds < +0.1 after photo-projection -> Phase 5), lighting/materials never concurrent, watchdog by registered max duration (scripts/blender_run.sh + rewritten scripts/blender_watchdog.sh), briefs in docs/briefs/process.md + <agent>_r<N>.md.
In flight: LIGHT r12 (docs/briefs/lighting_r12.md), ARCH r4 (architecture_r4.md), ENV r7 (environment_r7.md), all fresh Opus agents on their branches. Next: code review each, merge lighting first, MAT r7 on the rebuilt master, lead_build.sh, QA round 6 (Opus xhigh); photo-projection pass for the concrete if the hero is still ~3.28.

## 2026-09-09 · ARCH r4 reported (78f0e81), in review
ARCH r4: cornice/dentil profile rebuilt; QA box 900 262 1020 296 texture std 33.5 -> 47.6 (0.73 of ref, pass), row std 20.9 -> 32.4 (< 35; the model's cornice sits 1.04 m higher than ref 169's under QA's alignment, on the model's own band 43.1 pass); silhouette 0.000 % change, sockets 434 unchanged, ARCH tris -0.4 %. Hand-off ORN: 24 rotunda frieze_run sockets moved -0.25 m z / +0.10 m outward. Drum ring: -2.5 m radius needed for ref 062, reported only (no change). UV answer: all ARCH meshes carry one world-metre triplanar UVMap; a projection needs a second layer, object list in the report / docs/arch_notes.md round 4.
In flight: ARCH review, LIGHT r12, ENV r7. Next: merge arch, then lighting; MAT r7.

## 2026-09-09 · ARCH r4 merged after review (MERGE WITH FIXES; docs/reviews/arch_r4_review.md)
Lead fixes: notes profile table corrected to r4b; 128 spp re-measure identical to the builder's crop (QA box row 32.5 / tex 47.6; model's own cornice box 43.3 / 54.7). Carried to ARCH r5: stale comment, silhouette artifact, hard-coded QA alignment, measure-script threshold text. Open lead question: the model's cornice sits 1.04 m higher than ref 169's under QA's alignment (stack question, no change made). ORN note: rotunda frieze band is now 0.90 m tall; sockets carry run_length only.
In flight: LIGHT r12, ENV r7. Next: lighting review + merge, MAT r7 dispatch, then ENV merge, lead_build.sh, QA round 6.

## 2026-09-09 · ENV r7 reported (99c544c), in review
ENV r7: LOD1 4.62 M; cam03 ground std 14.1 -> 27.8 (walk 16.7 % of box); shore band null (+12 pp sun reach, band 71.7 -> 71.7: needs +43.9 lum from sky/materials, not planting); cam06 ground 13.8 -> 23.4 %, asphalt 2.47 -> 4.08 %; south wing untouched as briefed. Sheet renders/qa_comparisons/env_r7_sheet.png.
Hand-offs: lighting (cam06 mist +58 lum flattens the horizon, wing sky term 36 lum short, shore +43.9 lum), materials (MAT_paving_stone / _worn missing; shore level without saturation), arch (COLONNADE_WALK_Z tracks COLONNADE_GROUND_Z). In flight: ENV review, LIGHT r12. Next: merge lighting, MAT r7.

## 2026-09-09 · ENV r7 review: MERGE WITH FIXES (docs/reviews/env_r7_review.md); fix agent dispatched
Fix now: north/cam05 bands pin only P/C so 7 hand-placed trees were swept and 3 dropped (round-5 lesson again); COLONNADE_WALK_Z / PAVE_CENTRE hand-copied instead of imported from arch_params; two claims quote one box for two boxes; stale verge comment. Carry: paving fallback rationale, sample-count comment, absolute MAIN path, 3 previews > 5 MB, mixed baselines.
In flight: ENV r7 fixes (fresh agent, branch environment), LIGHT r12. Next: merge lighting, MAT r7, merge env, lead_build.sh, QA round 6.

## 2026-09-09 · LIGHT r12 reported (d5e6850), in review
LIGHT r12: diffuse sky x2.5 with an anti-sun/horizon blue tint, sun blue 0, FILL 10214 W. Hero shaded attic hue 43.1 -> 35.4 / sat 0.82 -> 0.41 / lum 117 (all pass); Cycles coffer 0.21 -> 0.438 (ref 0.437), Eevee gap 0.094; south wing 86 -> 94 (0.86 raw); north 0.97; sunlit attic lum 178.0 / sat 0.525 / R-B 112.5; columns 1.14x. cam03 shaft/sunlit 0.066: proven unreachable (box occluded from sky and anti-sun hemisphere; lead to re-base). QA-05-7 sky ratio 0.921 vs 0.922 on matched pixels (close as measured-equal).
Regression handed to materials: near-water sat 0.28 -> 0.42 (murk chroma -1/3). In flight: LIGHT review, ENV fixes. Next: merge lighting, MAT r7 on the rebuilt master.

## 2026-09-09 · ENV r7 merged (f426672) after review fixes; ENV r8 (short) dispatched
Fixes: pin tuple on all bands (moved 0 / dropped 0), arch_params imported, one box per claim, paths via common, 24 MB previews dropped; r7 panels had been rendered on main's stale master, re-rendered on the worktree master with parity proven (0.3 lum). Shore band 71.7 -> 79.6 (not null; 36 short). LOD1 4.76 M.
Regression: pinning restores the A/A2 cluster in the north band (137.5 -> 91.9, 0.63 of ref). Decision: pin stays, cluster re-derived from ref 169 (docs/briefs/environment_r8.md). In flight: LIGHT r12 review, ENV r8. Next: merge lighting, MAT r7.

## 2026-09-09 · LIGHT r12 merged after review (MERGE WITH FIXES; docs/reviews/light_r12_review.md); MAT r7 dispatched
Lead fixes: Eevee hero frame on the r12 rig: sky/lagoon identical to Cycles (208.2 / 0.52), no cast; Eevee misses the diffuse shade term (shaded attic 42.2 / 0.77 vs Cycles 35.4 / 0.41): carried to LIGHT r13 with meta provenance, water sheet cell, SUN_BLUE_MULT 0 and importance-map notes. hue_tol 8 -> 6.
In flight: MAT r7 (docs/briefs/materials_r7.md, Opus xhigh, on the merged master with the r12 rig), ENV r8. Next: reviews, merges, lead_build.sh, QA round 6.

## 2026-09-09 · ENV r8 reported (fa04322), in review
ENV r8: A2 trees were inside the wing's arc (courtyard side) and the A conifers on the peninsula shore; re-solved to COL_ARC_R + 8 m and the grove past the north arch at 120-135 m. North band 91.9 -> 133.1 (0.91 of ref 145.9), foliage 72.5 -> 38.5 %, mass right edge x 0.715 (ref 0.735), clearer moved 0 / dropped 0; south band +5.4 %, shore / cam03 / cam05 / cam06 within 3 %. Measured on its master (9706 objects, LIGHT r11 rig; geometry numbers). Carry: mass 0.025 of frame short in height (shadow_relief ordering, round 9 if wanted). Sheet renders/qa_comparisons/env_r8_sheet.png.
In flight: ENV r8 review, MAT r7. Next: merge env, MAT review + merge, LIGHT r13 (docs/briefs/lighting_r13.md), lead_build.sh, QA round 6.

## 2026-09-09 · ENV r8 merged after review (MERGE WITH FIXES; docs/reviews/env_r8_review.md)
Lead fixes: ref profile widened (mass 0.62-0.735 confirmed, solve accepted as delivered), station from qa_cameras, top-z note. Carries to ENV r9: shadow_relief relocates hand-placed trees (moved 16), mass 0.025 short in height, stale comments.
In flight: MAT r7. Next: MAT review + merge, LIGHT r13, lead_build.sh, QA round 6.

## 2026-09-09 · MAT r7 reported (02b60a8), in review
MAT r7 (on the r12 rig, 9706 objects, Cycles 64 spp): attic lum 180.3 pass, sat 0.474 (window 0.53-0.62, fail: the albedo blue that would fix it regresses the shade hue), std ratio 0.74 pass, anisotropy 0.35 -> 0.40 (target 2.0: 2/3 of the miss is QA's box catching the render's cornice because the attic frame sits ~0.65 m high vs ref 169); shaded attic 30.9 / 0.373 pass; coffer 0.450 pass; near-water sat 0.324 / hue 213.6 (murk is gain-linear; hue floor 209.6 from the water); reflection sat 0.043 (regressed, needs a hue term in QA's test); paving materials shipped (env must assign); shore band 91.7.
Photo-projection answer: window-coordinate lookup or UVProject, photo as a mean-1 ratio, 3 masks, ~120 lines; precondition: architecture freezes the hero-facing stack (attic frame 0.65 m / cornice 1.04 m offsets agree). In flight: MAT review. Next: merge, LIGHT r13, lead_build.sh, QA round 6 (add: stack offset per course).

## 2026-09-09 · MAT r7 review: MERGE WITH FIXES (docs/reviews/mat_r7_review.md); fix agent dispatched
Numbers reproduce. Fix now: sheen case never rendered (Sheen Weight still 0; reflection 0.26 -> 0.04), notes describe a superseded water build (gain 0.55 vs shipped 0.15), aerial lagoon untested at the shipped gain (one cam06), ARCH hand-off overstated (cornice explains 45 % of the row std, not 2/3; 13 px = 1.03 m not 0.65), shore item reported pass on a self-chosen window (not delivered), reflection box never probed.
In flight: MAT r7 fixes (fresh agent). Next: merge materials, env rebuild for paving, LIGHT r13, lead_build.sh, QA round 6.

## 2026-09-09 · MAT r7 merged (59f44a2) after review fixes
Fixes: sheen swept 6 cases and abandoned (every weight passing sat 0.25 does so at hue 213 = blue; QA's reflection test needs an R-B >= 0 term); water notes match the shipped gain 0.15 / transmission 0.18; cam06 lagoon Eevee 1.09x of round 5, Cycles 0.82x (dim, not black); ARCH hand-off restated (cornice 45 % of row std, 13 px = 1.03 m; direction failure mostly materials': authored per-panel streak maps proposed); shore not delivered (+0.6 of +43.9, sat rose); reflection box is 100 % water at 22 m. Near-water sat 0.303 (in window).
Next: env rebuild for MAT_paving_stone (lead, one command), LIGHT r13 (docs/briefs/lighting_r13.md), lead_build.sh, QA round 6.

## 2026-09-09 · ENV rebuilt for paving (lead, one command) and merged; LIGHT r13 dispatched
env_build.py on the merged library: walk 845 slabs on MAT_paving_stone / _worn (9 % worn), tree relief and LOD1 4,756,102 identical to r8. In flight: LIGHT r13 (Eevee shade term, cam06 mist, wings/shore, carries). Next: LIGHT review + merge, lead_build.sh, QA round 6 (Opus xhigh).

## 2026-09-09 · LIGHT r13 reported (3991518), in review
LIGHT r13: probe capture evaluated the diffuse branch as a camera ray (fixed) but the hero's Eevee shade is screen-traced GI, so an Eevee-only LIGHT_shade_fill (55 W/m2, el 5, blue derived from the stone's reflectance) ships on the EEVEE_VAULT pattern: Eevee shaded attic 93.3 / 38.2 / 0.650 -> 119.0 / 35.0 / 0.381 vs Cycles 114.3 / 30.9 / 0.374 (pass); Cycles hero bit-identical. cam06 mist cap 0.50 -> 0.25, extinction 5.0: crop std 33.8 -> 38.1, 2 lines composited. Sky-term headroom on the wings: zero (sunlit R-B 103 / sat 0.475 already under floors on the r7 master). 9709 objects.
Hand-offs: materials +0.025 sat / +6.9 R-B on the sunlit attic; env shore 91.5 of 115.6. In flight: LIGHT review. Next: merge, lead_build.sh, QA round 6.

## 2026-09-09 · LIGHT r13 merged after review (MERGE WITH FIXES; docs/reviews/light_r13_review.md); master rebuilding
Lead fixes: common.configure_cycles hides the Eevee-only vault/shade rigs on every Cycles path (finding 1); measure HOLD = sky boxes; carries 2, 5-11 to r14. Polish round 4 fully merged: ARCH r4, LIGHT r12+r13, MAT r7, ENV r7+r8 (+paving rebuild). scripts/lead_build.sh now runs through blender_run.sh.
In flight: scripts/lead_build.sh (log renders/logs/lead_build_r6.log). Next: QA round 6 (Opus xhigh, docs/briefs/qa_round_06.md), gate report to the user.

## 2026-09-09 · master rebuilt (lead_build.sh, 9709 objects, LOD1 11.11 M, probes baked on the diffuse world); QA round 6 dispatched
In flight: QA round 6 (Opus xhigh, docs/briefs/qa_round_06.md; commits only qa docs/scripts/renders; lead does not commit on main until it reports). Next: gate report with composite, score deltas, open defects; decide photo-projection pass vs Phase 5 per the definition of done.

## 2026-09-09 · no-idling rule added to CLAUDE.md; QA round 6 rendering; three no-render slot agents dispatched
Four agents running: QA round 6 (GPU), ARCH r5 (UVProj layer for the projection pass, course-row table, r4 carries), LIGHT r14 prep (flythrough path rebuilt + ray-cast clearance table, r13 carries, docs/tech_notes.md delivery section), ORN r5 (rotunda frieze band asset for the 24 sockets + ORN_COLL entry, attic relief report, LOD2 budget). None renders or writes master.
Next: QA gate report to the user; reviews + merges of the three slot branches; go/no-go on docs/briefs/materials_r8_projection.md.

## 2026-09-09 · ARCH r5 reported (db35484), in review
ARCH r5 (no render): UVProj layer on 33 hero-facing objects (cam01 frame position, round-trip 0.00 px, named-point checks 0.78 / 0.00 / 0.02 px, UVProj_valid attribute, tris and sockets unchanged); course-row table for cam01 (attic top 158, frame 173-246, corona 251-254, dentil bed 276, frieze 280-292, architrave bottom 308); r4 carries done, silhouette re-measured without a render (within 1 px). 5.2 gotchas: matrix_world stale for hidden objects, use matrix_basis; BVHTree instead of Object.ray_cast.
In flight: ARCH r5 review, QA round 6, LIGHT r14 prep, ORN r5. Next: merge arch r5 after review; QA gate.

## 2026-09-09 · QA round 6 in (6343ccd): gate NOT passed; hero 3.22 (-0.06; 3.28 with proportion held = fourth flat round), cam02 2.72, cam03 2.12 (+0.38), cam04 2.75 (+0.19), cam05 2.78, cam06 2.28 (-0.22)
Closed: hero shade colour, Cycles coffers, cornice/dentil texture std, cam03 shade on the re-based box (0.384), cam05 stone std, north wing. Blockers: QA-06-1 hero stack does not register (+0.07 to +2.31 m by course; attic storey 0.70 and capital 0.65 of ref: architecture, and the projection pass cannot register until it is closed), QA-06-2 the r12 diffuse tint floods cam02/03/05/06 shade blue-violet (roofs hue 37 -> 253: lighting), QA-06-3 water fails everywhere (reflection R-B +2.5 vs +69, cam05 lagoon sat 0.12: materials). Majors: -4 anisotropy 0.41, -5 sunlit chroma (sat 0.473, R-B 103), -6 capitals 24 px vs 37 (ornament), -7 cam03 lagoon-side row, -8 coffer sat 0.91, -9 entablature row std 36.5, -13 Eevee pass +81 %. Composite renders/qa_comparisons/round06_gate.png.
Polish round 5 (decisions.md): ARCH r6 closes the stack first (then re-runs UVProj), LIGHT r14 fixes the violet flood + reflection warmth, then MAT r8 = water blocker + photo-projection on the registered stack. Definition of done clock starts at the round after MAT r8.

## 2026-09-09 · ORN r5 reported (70dc10d), in review
ORN r5 (no render): 24 rotunda frieze_run sockets are host=rotunda subtype=rinceau (8 fronts 5.913 m, 16 returns 2.999 m); new ORN_frieze_rinceau / _return v1-3 with LODs inside budget, proud <= 125 mm under the 160 mm architrave-crown cap, sunk 15 mm; needs the ORN_COLL guard in build_master.py (lead) and a normal/AO bake (was --no-bake). Attic panel depth already 1.6x nominal; the deficit is undercut, not depth; deeper relief blows all three tier budgets (not built). All three attic panels' LOD2 brought to 2400 tris.
In flight: ORN review, ARCH r5 review, LIGHT r14 prep. Next: merges; ARCH r6 (stack), LIGHT r14 (violet flood), MAT r8 (water + projection).

## 2026-09-09 · ARCH r5 merged after review (MERGE WITH FIXES); ARCH r6 dispatched (register the stack)
Fix-now (arch_uvproj not called by the build) carried into ARCH r6 item 0. In flight: ARCH r6 (docs/briefs/architecture_r6.md, Cycles crops only), ORN r5 review, LIGHT r14 prep. Next: LIGHT r14 after prep merges; MAT r8 after LIGHT r14 + ARCH r6.

## 2026-09-09 · LIGHT r14 prep reported (4fa11be), in review
Flythrough rebuilt: cam01 hold -> lagoon crossing -> cam02 station -> one colonnade bay -> gallery centreline at z 1.15 -> arch -> ceiling look-up; 250.1 m, 1224 frames @ 24 fps (51 s; 720 impossible at walking pace); check script: clearance 1.70 m outside / 1.42 in the gallery (2.80 m clear width), speed 5.6 / 9.2, holds 3.5 / 4.2 s. r13 carries done except 8 (needs an Eevee frame). docs/tech_notes.md "Opening and rendering master.blend" written. Hand-offs: env shrub pitto1_1107 overhangs the walk; cam06 std gate to be restated as a ratio.
In flight: LIGHT prep review, ORN r5 review, ARCH r6. Next: merge, LIGHT r14 (violet flood).

## 2026-09-09 · ORN r5 review: MERGE WITH FIXES (docs/reviews/orn_r5_review.md); fixes split by owner
Blockers routed to ARCH r6 (message sent): the 24 rotunda frieze_run sockets carry no host/subtype (the lead's build_master guard never fires) and their frame is wrong (+X anti-parallel to run_dir on fronts, +Y into the block on returns). ORN fix agent: cap is 100 mm (architrave crown d 0.44), RIN_MAX_PROUD 0.09, stats fail loudly on run mismatch, lod2fix into orn_build; the normal/AO bake waits for a GPU round. ENV r9 (no render) dispatched: walk clearance shrub, r7/r8 carries, cam06 gate definition.
In flight: ARCH r6, LIGHT prep review, ORN r5 fix, ENV r9. Next: merges; LIGHT r14.

## 2026-09-09 · LIGHT r14 prep merged (MERGE WITH FIXES; fix-nows carried into LIGHT r14 item 0); build_master sets the flythrough frame range; LIGHT r14 dispatched
In flight: ARCH r6, LIGHT r14 (docs/briefs/lighting_r14.md), ORN r5 fixes, ENV r9. Next: reviews, merges, MAT r8 (water + projection) after LIGHT r14 and ARCH r6.

## 2026-09-09 · ORN r5 merged (5703665) after fixes
RIN_MAX_PROUD 0.09: clearance +10.5 to +13.3 mm on all six variants, tris unchanged; orn_r5_stats is a gate (run mismatch, clearance, budgets); LOD2 budget enforced in orn_lib.enforce_lod2_budget; `orn_build.py -- --bake-pending` lists 6 LOD1 normal-map bakes for a GPU round. Instancing waits for ARCH r6's socket stamp/frame.
In flight: ARCH r6, LIGHT r14, ENV r9. Next: reviews + merges, ORN bake (GPU round), MAT r8.

## 2026-09-09 · ARCH r6 reported (2361006), in review
Stack registered on ref 169: every course within 5 rows (0.37 m; was up to 31), attic storey 101 vs 100 rows; ENTABLATURE_Z0 27.40 -> 25.96 (3.22 m entablature), CAPITAL_H 2.6 -> 3.0, COL_SHAFT_H 16.3 -> 14.46, ATTIC_H 7.1 -> 9.12 with a real crown corona soffit; silhouette 0.6 / 0.0 / 0.0 / 0.35 %; tris +0.012 %; UVProj now a mandatory post-step of arch_build (re-checked 0.84 / 0.00 / 0.02 px); rotunda frieze_run sockets stamped host/subtype and re-framed (arch_socket_check ALL OK on 126). Socket deltas for ornament: capital_rotunda -1.84 m and 3.0 m tall, frieze_run -1.55 m and band 0.81 m, attic_panel -2.07 m and panel_height 5.27, attic_figure -2.02 m.
In flight: ARCH r6 review, LIGHT r14, ENV r9. Next: merge arch; ORN r6 refit (capitals 3.0 m, rinceau 0.81 band, attic panels 5.27 m; no render) then the ORN bake; MAT r8.

## 2026-09-09 · ARCH r6 review: MERGE WITH FIXES (docs/reviews/arch_r6_review.md); fix agent dispatched (no render)
Fix now: stamp capital_height on capital_rotunda sockets (0.40 m void under the architrave until ornament rebuilds), band_height on the rotunda frieze_run sockets, re-run the ref 062 fit (it reads ATTIC_Z0, which moved), commit the qa_stack_offset log, sheet table from data. Carries: uvproj tri guard dead in-build, SystemExit ordering, entablature sub-courses scaled not photo-anchored, socket check exit code, 6.4 MB intermediate.
In flight: ARCH r6 fixes, LIGHT r14, ENV r9. Next: merge arch, ORN r6 refit, MAT r8.

## 2026-09-09 · ENV r9 reported (e0b383f), in review
ENV r9 (no render): walk clearance 0.03 -> 1.71 m to geometry, 0 samples inside the 2.80 m clear width (the OSM roof polygon fell inside the modelled arc; new env_lib.gallery_clear from arch_params, enforced everywhere); shadow_relief no longer relocates pinned trees (corrections baked into PLAN); trees 131, LOD1 4.71 M, band clearer moved 0 / dropped 0; wing shadow 21.2 % vs the 22 % cap (margin 0.8 pt, needs a render check); cam06 gate = std composited / un-composited >= 0.60 (lighting r13 ships 0.637).
In flight: ENV review, LIGHT r14, ARCH r6 fixes, ORN r6. Next: merges, MAT r8.

## 2026-09-09 · ARCH r6 merged (2b1c716) after fixes; ref 062 conflict logged (decisions.md)
Socket props stamped and asserted (capital_height 3.0, band_height 0.81, panel_height 5.27; 434 sockets ALL OK); registration log committed (+1/-1/+1/-3/0/+5/+1/+1 rows); ref 062 wants ATTIC_Z0 30.20 vs 29.18 (hero wins; QA may re-fit cam02). In flight: LIGHT r14, ORN r6 (re-merges main for the socket props), ENV r9 review. Next: LIGHT r14 review + merge, then MAT r8 (water + projection on the registered stack).

## 2026-09-09 · ENV r9 review: MERGE WITH FIXES (docs/reviews/env_r9_review.md); fix agent dispatched (no render)
Fix now: the onto-land spiral snap runs after the gallery gate and moves 6 hand-placed trees up to 5.6 m (PLAN still not the shipped coordinate); pinned-moved counter is a tautology; 137 -> 131 is six refused screen redwoods, not dropped PLAN trees; MASS_X comment; cam06 0.637 must be computed by --c06ratio on lighting's frames. Carries: PLAN --verify mode, wing-shadow probe below its quantum (QA confirms on a render), eye-band gate.
In flight: ENV fixes, LIGHT r14, ORN r6. Next: merges, MAT r8.

## 2026-09-09 · ORN r6 reported (90b183e), in review
ORN r6: capitals 2.6 -> 3.0 m (hero px 34.7-35.5 -> 40.0-40.9 vs ref 38-44), rinceau band 0.81 (clearance 10-11.5 mm), attic panels 5.28 (relief p90 0.376 m; undercut is the limit, not depth); LOD1 budget for attic panels raised 24 k -> 36 k (+95 k tris in the master's LOD1); enforce_tri_budget on LOD1 and LOD2; normal-map bakes done (0 pending), AO missing on 32 LOD1s. Proposal: archivolt_run socket type + modillion/egg subtypes for the bed-mould (hand-off to ARCH). Gate exits 0 on the merged architecture.blend. No render sheet (GPU held).
In flight: ORN review, LIGHT r14, ENV fixes. Next: merges, MAT r8; QA round 7 checks the capital luminance alternation on a render.

## 2026-09-09 · ENV r9 merged (c61cc32) after fixes
land_snap runs before the gates and never moves pinned trees (build fails naming a wet PLAN coordinate); 79 hand-placed trees at 0.000 m from PLAN; --verify and --land gates; c06 ratio computed 0.636; walk clearance 1.71 m, LOD1 4,705,602, 131 trees, wings 21.2 % shadow (QA confirms on a render).
In flight: LIGHT r14, ORN r6 review, ARCH r7. Next: LIGHT review + merge, MAT r8, then lead_build.sh and QA round 7.

## 2026-09-09 · ORN r6 merged (8342aa5) after review (MERGE WITH FIXES; lead fixed the gate's stamp-set fallback)
Carries to ORN r7: capital scaled in Z only (acanthus tiers stretched), attic figures crowd 17 % laterally (X positions not scaled), rinceau normal map baked before the Z squash, hard-coded RES_X/SENSOR, 84 MB blend committed twice; QA-06-6's luminance half needs a render (QA round 7).
In flight: LIGHT r14, ARCH r7. Next: LIGHT review + merge, MAT r8, lead_build.sh, QA round 7.

## 2026-09-09 · ORN r7 reported (676897d), in review
Capital re-laid for H 3.0 (tiers 0.03-0.33 / 0.30-0.60 H, volutes 0.66-0.89 H, abacus 0.10 H vs ref_002; verified by a Blender-free layout solver), attic figure x scaled by PANEL_K, course error 26 -> <= 4.2 mm, rinceau normal normalised, constants from qa_cameras; gate exit 0. Pending: LOD1 bakes for capital_rotunda + attic_panel (rebuilt --no-bake under the GPU rule) — the lead runs `orn_build.py -- --bake-pending` in the next GPU window before the master rebuild; inner/colonnade capitals 17-25 mm over their course (one rebuild).
In flight: ORN review, LIGHT r14, ARCH r7. Next: LIGHT review + merge, ORN bake, MAT r8.

## 2026-09-09 · ORN r7 merged (676897d) after review (MERGE WITH FIXES)
Carried to ORN r8: --verify must parse ARCH_R6 and the two formulas from orn_build.py and loop over CAPITAL_STYLE (v2 volute top 0.904 H above the 0.900 abacus seat; v3 upper extent 0.310 H / r_tip 1.51 R outside the ref window), ref_002 measurement not reproducible, back-row integer cliff, bake_pending exit code. BLOCKER before the next master build: capital_rotunda v1-3 and attic_panel v1-3 LOD1 maps are empty (rebuilt --no-bake); the lead runs `orn_build.py --only attic_panel,capital_rotunda` (with bake) in the next GPU window.
In flight: LIGHT r14, ARCH r7. Next: LIGHT review + merge, ORN bake, MAT r8, lead_build.sh, QA round 7.

## 2026-09-09 · ARCH r7 reported (9d6f8ee), in review
8 archivolt_run sockets (outer arches; origin at the springing, +X up along the arc tangent, +Y outward; arc 6.55 m, run 20.58 m, band 0.22; check 8/8 OK), docs/sockets.md updated. Sub-courses on ref 085: corona / egg pitch / modillion pitch within 3 %; modillion height 0.638 vs 0.45 (+42 %) and an unmodelled 0.58 m Greek-key band: they do not fit in CORNICE_H 1.37; option A (cornice 1.79, frieze 0.61 -> rinceau refit) costed, not built. Ref 062 on the new stack: az 37 / D 88.6 / 41.5 mm, attic base +0.83 m unfittable, station in the lagoon (hand-off to QA for cam02).
Decision: option A deferred until QA round 7 scores the entablature on the registered stack. In flight: ARCH r7 review, LIGHT r14, ORN r8. Next: merges, LIGHT review, ORN bake, MAT r8.

## 2026-09-09 · ARCH r7 merged (9d6f8ee + lead corrections)
Archivolt sockets in (band along local +Z: ornament note), sub-course scale marked as assumed (N = 11), ref 062 reproducible from land at az 17 / D 83.4 (QA may re-station cam02 there). In flight: LIGHT r14, ORN r8. Next: LIGHT review + merge, ORN bake, MAT r8, lead_build.sh, QA round 7.

## 2026-09-09 · BUDGET PLAN (user): ~32 % weekly limit left, Phase 5 needs ~10, gate within ~20
Sequence: LIGHT r14 (running) -> review/merge -> lead runs the ORN bake (`orn_build.py --only attic_panel,capital_rotunda`, with bake) -> MAT r8 = water blocker + coffer albedo only (brief re-scoped) -> review/merge -> lead_build.sh -> QA round 7 -> gate report to the user with the composite -> STOP for a clean restart (lead context 384k). If hero < 3.6 after round 7: MAT r9 = photo-projection pass next, no other knob round. Entablature re-split deferred unless QA shows it in the hero. ORN r8 (verify tool, no render) merges if it lands in time, else stays on its branch.

## 2026-09-09 · ORN r8 reported (2410e95) — held on branch `ornament`, not merged this session (budget)
Verify tool parses all presets/styles from orn_build.py, v2/v3 presets fixed (volute top 0.891 H, v3 r_tip 1.389 R), capital_rotunda rebuilt --no-bake, ref_002 crop committed (H 358 px). Held because merging before the bake would drop the capital maps again; next session: review (docs/briefs/review.md), merge, then `orn_build.py --only capital_rotunda` with bake, then a master rebuild. capital_inner / capital_colonnade v3 still carry the r7 style.
In flight: LIGHT r14. Next: LIGHT review + merge, ORN bake on main's r7 asset, MAT r8 (water), lead_build.sh, QA round 7.

## 2026-09-09 · LIGHT r14 reported (cac6ee1), in review; ORN bake running (lead)
LIGHT r14: the r13 sky is a sky colour (grey card hue 215-219); the flood was quantity on up-facing surfaces. Sharpness exponents on the tint discriminators (horizon p6, anti-sun p3, b 40) + LIGHT_shade_fill live in Cycles (70 W/m2, el 2, blue): hero shaded attic 116.4 / 33.6 / 0.410 (hold), cam06 roofs hue 241 -> 316 (over-corrected warm), plaza / trees 33 / 32, cam05 water band hue 350 -> 40 sat 0.47, cam03 walk 222 -> 204; sky boxes bit-identical; Eevee five-camera pass 361.6 -> 229.9 s (shade lamp shadows 0.20 m/texel, jitter off). Water hand-off: the mirror of the building must be 2.3x brighter (52 -> ~120 lum) with the sky term held to land the reflection box at lum 172 / R-B +69. cam03 outer row responds (0.082 -> 0.138), r15 item. Flythrough: 1.57 m outside / 1.42 gallery at step 4 on the 1.35 gate.
In flight: LIGHT review, ORN bake. Next: merge lighting, MAT r8 (water), lead_build.sh, QA round 7, gate report, stop.

## 2026-09-09 · LIGHT r14 merged (cac6ee1 + lead corrections); MAT r8 (water only) dispatched
Carries to LIGHT r15: sweep defaults, commit measure stdout, docstrings, cam06 roofs / cam02 pier over-warm, cam03 outer row. In flight: MAT r8 (docs/briefs/materials_r8_projection.md RE-SCOPE section: water blocker + coffer albedo; re-measure the building/sky split itself). Next: MAT review + merge, lead_build.sh, QA round 7, gate report, stop.

## 2026-09-09 · MAT r8 reported (6e7d799), in review
MAT r8 (water only, 9681 objects): the mirror ray from the reflection box lands 25 % on a willow, 30 % on the backdrop through the arch, 12.5 % ARCH; fix = Bump Distance ramped by depth (WATER_BUMP_DIST 0.03 -> 0.17 over 14-24 m). Reflection box R-B +8 -> +37 (pass), hue 36.5 (pass), lum 105.6 (window 124-208 fail; frontier ~110 at R-B >= 30); near-water sat 0.301 pass, hue 228 (lighting's r14 sky moved it 214 -> 228); cam05 lagoon sat 0.47 pass; cam06 lagoon Cycles 132 (1.4x) pass; coffer sat 0.97 -> 0.50 pass. Two knobs withdrawn; 6 Cycles + 3 Eevee frames (over the 3+1 cap).
Hand-offs: QA to check the hero camera height (2.90 m over water vs ref 169's near-total mirror at 87-89 deg incidence); environment (willow occludes the rotunda's mirror); lighting r15 (near-water hue / ripple R-B moved by the r14 sky). Next: review, merge, lead_build.sh, QA round 7.

## 2026-09-09 · MAT r8 merged (6e7d799 + lead corrections); polish round 5 fully merged; master rebuilding for QA round 7
Merged this round: ARCH r6+r7, LIGHT r14 (+prep), MAT r8, ENV r9, ORN r6+r7 (+lead bake); ORN r8 held on branch. In flight: scripts/lead_build.sh (log renders/logs/lead_build_r7.log). Next: QA round 7 (docs/briefs/qa_round_07.md), gate report, STOP.

## 2026-09-09 · master rebuilt (9681 objects, LOD1 11.38 M, 24 rinceau instanced, frame range 1-1224, probes baked); QA round 7 dispatched
In flight: QA round 7 (Opus xhigh, docs/briefs/qa_round_07.md items 1-5). Next: gate report with composite; if hero < 3.6 -> MAT r9 photo-projection next session; STOP after the report (lead restart).

## 2026-09-09 · QA round 7 in (b978165): gate NOT passed; hero 3.22 -> 3.44 (+0.22), cam02 3.06 (+0.33), cam03 2.25 (+0.12), cam04 2.88 (+0.12), cam05 3.00 (+0.22), cam06 2.50 (+0.22)
Closed: QA-06-1 stack (all courses within 5 rows, spread 0.67 m), QA-06-2 violet flood, cam03 re-based box 0.516, capitals 35 px, cam06 gate 0.631, wing shadow on a render (south 57 % vs ref 54, north 36 vs 39), Eevee pass 146 s. Blockers: QA-07-1 open lagoon 1.24x bright / blue (lighting horizon then materials), QA-07-2 sunlit stone chroma sat 0.437 / R-B 99 (materials; projection expected to carry it). Majors: -3 mirror 0.55 of direct stone (materials), -4 archivolt/bed-mould blank (ornament; 8 sockets, no asset), -5 cam03 28 % black, -6 cam06 street lines composited 0, -7 hero shade level 134 (lighting). Hero camera height: photo 2.6 m vs built 2.90 m (not moved). cam02 fitted station handed over for round 8. Composite renders/qa_comparisons/round07_gate.png.

## 2026-09-09 · CHECKPOINT (lead stopping for a clean restart; user's budget plan)
**Merged into main (all reviewed):** ARCH r4-r7, LIGHT r12-r14 (+prep), MAT r7-r8, ENV r7-r9, ORN r5-r7 (+lead bake). master.blend on disk = lead_build.sh after polish round 5 (9681 objects, LOD1 11.38 M, probes baked, flythrough 1-1224) = what QA round 7 scored. All five worktrees clean. **Held on branch, not merged:** ORN r8 (2410e95; verify tool + v2/v3 capital presets, capital rebuilt --no-bake): next session review it (docs/briefs/review.md), merge, run `orn_build.py --only capital_rotunda` WITH bake, before the next master build.
**Scores (avg per camera):** r05 3.28 / 2.78 / 1.75 / 2.56 / 2.78 / 2.50 -> r06 3.22 / 2.72 / 2.12 / 2.75 / 2.78 / 2.28 -> r07 **3.44 / 3.06 / 2.25 / 2.88 / 3.00 / 2.50**. Definition of done (CLAUDE.md): hero >= 4.0, or two rounds < +0.1 after the projection pass. Budget plan (user): ~32 % weekly left at the plan, Phase 5 needs ~10, gate within ~20; this session spent polish round 5 + QA round 7.
**Resume procedure (next session):** (1) `git status` in every worktree (clean), `pgrep -fl "MacOS/Blender"` (none), restart `scripts/blender_watchdog.sh --loop`. (2) Apply cam02's fitted station in scripts/qa_cameras.py (decisions.md 2026-09-09 last entry) — lead, < 20 lines. (3) ORN r8 review + merge + bake (above). (4) LIGHT r15 (short brief to write: QA-07-1 lagoon horizon hue/level with the water untouched, QA-07-7 hero shade level 134 -> 103-127 keeping hue 32 / sat 0.31, QA-07-5 cam03 lagoon-side row via the SSW shade lamp, r14 carries; one sweep, Opus high). (5) MAT r9 = photo-projection pass (docs/briefs/materials_r8_projection.md item B + constraints 1-6, plus QA-07-3 mirror level and QA-07-2 sunlit chroma; Opus xhigh) after LIGHT r15 merges. (6) Reviews, merges, lead_build.sh, QA round 8 (Opus xhigh, brief pattern docs/briefs/qa_round_07.md; item: projection seams from cam02/cam05 are blockers). (7) Apply the definition of done; then docs/phase5_checklist.md. Watchdog not running at checkpoint; no Blender processes running.

## 2026-09-09 · Session restart (lead): stations moved, silhouette re-registered, LIGHT r15 + ORN r8 review dispatched
cam01 z 1.6 -> 1.3 (2.6 m over the water, QA round 07 item 5); cam02 to the ref-062 NNE fit (-79.8, 24.4, 1.55) -> (0, 0, 23.5) 40 mm (65ef92c). Registration on one Eevee hero frame upscaled to 1920: align scale 1.3108, apex delta 0.53 %H; stack band 880-1040: crown 164 vs ref 168, panel bottom 255 vs 265 (widest, 6 rows), corona 280 vs 278, architrave 319 vs 324, abacus 333 vs 333 — all inside the +-8 row acceptance; the tool's auto-walk (median +0.52 m) mis-pairs edges on the Eevee frame, the panel round08pre_stack_offset.png is the evidence.
In flight: LIGHT r15 (docs/briefs/lighting_r15.md, Opus high), ORN r8 code review (no Blender), Phase 5 prep on branch phase5 (no render). Next: LIGHT review + merge, MAT r9 projection (Opus xhigh), ORN r8 merge + capital bake, lead_build.sh, QA round 8.

## 2026-09-09 · ORN r8 merged after review (MERGE WITH FIXES; main's baked ornament.blend kept, notes' pending-bake bullet corrected)
Pending before the next master build: `orn_build.py --only capital_rotunda` WITH bake in the GPU gap after LIGHT r15 (attic_panel is baked on main). Carries for a later ornament round: two ref_002 pixel scales in the notes, source_ns() brace counter, --verify skips the two 1.8 m capitals.
In flight: LIGHT r15, Phase 5 prep (branch phase5). Next: LIGHT review + merge, ORN bake, MAT r9.

## 2026-09-09 · Phase 5 prep reported (branch phase5, c9afc7f), in review
scripts/phase5_deliver.sh (checklist steps 2-6 through blender_run.sh, step 5 picks spp/res from step 4's wall time), phase5_hero.py, phase5_flythrough.py, tech_notes "Opening and rendering (Phase 5)". Held on branch until the gate; review docs/reviews/phase5_r1_review.md.
In flight: LIGHT r15, phase5 review. Next: LIGHT review + merge, ORN capital bake, MAT r9.

## 2026-09-09 · LIGHT r15 reported (aec2d77), in review; ORN capital bake running (lead)
LIGHT r15: the lagoon flood was LIGHT_shade_fill (3 blue lamps at el 2), not the sky: 3 lamps -> 1 (NNE) + SKY_GLOSSY_BOOST 5.25 -> 4.20; near water 144.7/h228 -> 107.7/h209.4 (level pass, hue 9.4 deg out = materials' body colour), flank 188 -> 145.2/h210 pass, reflection R-B +39.9 pass, sky boxes identical, cam05 band Cycles 108.4 pass; Eevee fast GI OFF: cam03 under-lum-10 18.5 -> 4.6 %, outer row 0.189 pass, cam06 roofs hue 33, Eevee pass 196.4 s. Unresolved: hero shaded attic 136.4 (130.8 with the fill off; the shaded albedo is ~12 % hot vs sunlit -> MAT r9), cam02 pier hue 260 (lead: hero holds, minor). cam02 water box retired (no water at the NNE station).
Decision: QA-07-7 goes to materials as a shaded-albedo item; QA-07-11 stays minor. Next: LIGHT review + merge, MAT r9 dispatch (brief updated with the hand-offs), lead_build.sh, QA round 8.

## 2026-09-09 · LIGHT r15 merged (aec2d77 + lead corrections); MAT r9 dispatched
Review caveat carried: the "sky rotation moves water hue 0.1 deg" claim was measured at the null hue (sweep bug, fixed); the 9.4 deg hand-off rests on the lamp isolation alone. Carries to a later lighting round: apply_shade_for_engine docstring, §25.3 AFTER column mixes fast-GI states, Eevee hero attic hue 36.5 vs window 35.5, light_r15_sheet.py hard-coded path.
In flight: MAT r9 (docs/briefs/materials_r9.md, Opus xhigh). Next: MAT review + merge, lead_build.sh, QA round 8.

## 2026-09-09 · Phase 5 prep agent 2 dispatched (user's instruction; branch phase5, Opus high, no renders)
Scope: scripts/phase5_cleanup.py (orphan purge, optional texture pack, LOD defaults, JSON report, re-open under 60 s on a delivery copy), docs/flythrough_plan.md (shot list, clearance gate, test-animation timing), wired into phase5_deliver.sh as step 1b. Tests only on a scratchpad copy of master.blend, no render.
In flight: MAT r9 (rendering), Phase 5 prep 2. Next: MAT review + merge, lead_build.sh, QA round 8.

## 2026-09-09 · Phase 5 prep 2 reported (branch phase5, 82bb218); held on branch, review pending at the gate
phase5_cleanup.py tested on a scratchpad copy: 0 orphans, 9681 objects, LOD1 visible / LOD0+LOD2 hidden, stations unchanged, 160.9 MB, re-open 0.78 s; pack not run (87 external images, 116 MB, would give 277 MB). Deliver driver step 1b works on master_delivery.blend (gitignored). Flythrough findings (path unchanged): speed step at the hold boundaries (frames 85, 1105-1129, ~3.2 m/s2 vs ACCEL 2.5), the clearance check links ARCH+ENV only (ORN never tested; gallery 1.42 m is 0.02 over the bound), frames 398-408 in no leg; peak pan 14 deg/s, no station inside geometry.
In flight: MAT r9. Next: MAT review + merge, lead_build.sh, QA round 8; phase5 r2 review before its merge in Phase 5.

## 2026-09-09 · MAT r9 reported (d748c99), in review
Projection shipped (world-position sampling, identical to UVProj to 0.0002 px; ratio map LF+0.5 MF, 1.17 MB): attic std ratio 0.65 / aniso 4.16 pass, seam test no resolvable edge on cam01/02/05. Sunlit chroma sat 0.461 (window 0.53-0.62) FAIL: measured AgX transfer at lum 188 passes only 0.19-0.24 % display blue per 1 % scene blue, so QA-07-2 is unreachable through albedo (needs a look or sun change). Shaded attic 132.9 FAIL (needs -24 % albedo, 2.4x what the photo supports). Water: reflection 110.3 (0.58 of sunlit) FAIL, R-B +43.7 pass; near water hue 208.5 FAIL (third lever measured; the pixel is 95 % mirror = the sky's hue), lum/sat pass; ripples, flank, cam05 pass. Option table: WATER_GLOSS_MIX 0.25 -> 0.45 gives refl 116 / near water 125 / sat 0.20; 0.75 gives refl 124 but near water 134 / sat 0.16 and cam05 over 117.
Lead's call at merge: WATER_GLOSS_MIX 0.45 (hero mirror closer, near-water lum in window, sat 0.02 under). QA-07-2 stays open as a colour-management finding for the gate. In flight: MAT review. Next: merge, lead_build.sh, QA round 8.

## 2026-09-09 · MAT r9 review in (MERGE WITH FIXES); MAT r9b dispatched before the master rebuild
Review: the ratio map is a display-space AgX quotient applied to linear albedo (delivers ~1/3 of its correction); the AgX chart ran at look None while the project ships 'AgX - High Contrast'; "QA-07-2 unreachable" not shown; phtest.py uncommitted. Decision: fix now (docs/briefs/materials_r9b.md: linear-space ratio, transfer at the shipped look, shaded-sat ceiling as the binding constraint, gloss mix 0.45) so QA round 8 scores a correctly scaled projection; one Cycles hero frame. Budget: r9b + QA round 8 + Phase 5 fit; a round 9 does not, so round 8 is the gate round unless the hero lands within reach of 4.0.
In flight: MAT r9b. Next: quick re-review of the r9b diff, merge, lead_build.sh, QA round 8.

## 2026-09-09 · MAT r9b reported (da7f829), delta review running
Linear-space ratio map (LF luminance raised to 1/t_eff at the shipped look; MF exempt; soft roll-off 1.55 up / 2.20 down): Photo 0 -> 1 now moves the shaded attic -11.96 % vs the -8.47 % ask (r9: -3.9 %). Hero Cycles: shaded attic 127.9 (1.4 over the window), sunlit sat 0.463 / R-B +105 (still short; the shaded hue window binds at tint exponent 1.25 — QA-07-2 cannot close through albedo without breaking the shade; Punchy is worse than the shipped look), std ratio 0.64 / aniso 4.84 pass, gloss mix 0.45: reflection 116.3 (0.61 of sunlit), near water 125.3 / sat 0.200, ripples -22.5, flank 162.7. Unmeasured: cam05 band at gloss 0.45 (~118 vs 117 ceiling), seam test not re-run (QA round 8 item 2 covers it). f = 1.09 pedestal left in place (lead: keep).
In flight: mat_r9b review. Next: merge, lead_build.sh, QA round 8 (gate round).

## 2026-09-09 · MAT r9 + r9b merged (eb3d40b); polish round 6 fully merged; master rebuilding for QA round 8
Merged this round: stations (cam01 2.6 m, cam02 NNE), LIGHT r15, ORN r8 + capital bake, MAT r9 + r9b. Carries: MAT r10 albedo clamp per channel (drum red can exceed 1.0 at +55 %), 4 % hard clip at 2.0, Eevee water gloss as tint only; LIGHT carries in light_r15_review. In flight: scripts/lead_build.sh (log renders/logs/lead_build_r8.log). Next: QA round 8 (docs/briefs/qa_round_08.md), gate report.

## 2026-09-09 · master rebuilt (9679 objects, LOD1 11.38 M, probes baked, 23:01); QA round 8 dispatched (gate round)
In flight: QA round 8 (Opus xhigh, docs/briefs/qa_round_08.md). Next: gate report to the user with the composite; apply the definition of done (hero >= 4.0, or the budget rule: round 8 is the gate round unless the hero lands within reach of 4.0); then Phase 5 (branch phase5 second review + merge, docs/phase5_checklist.md).

## 2026-09-09 · phase5 r2 review in (MERGE WITH FIXES; the 16-bit ordering fixed on the branch by the lead); branch ready to merge at the gate
Carries into Phase 5 (lead runs them by hand): step 5 side-by-side + measure numbers, step 6 LOD0 clearance check with ORN linked, cleanup exit code on a failed preset / 1.5 GB.
In flight: QA round 8. Next: gate report, definition of done, Phase 5.

## 2026-09-09 · QA round 8 in (2a755a3): gate NOT passed; hero 3.44 -> 3.67 (+0.22), cam02 3.06 -> 2.69 (-0.37, the 40 mm lens clipped the dome), cam03 2.25 -> 2.56, cam04 2.88 -> 2.81, cam05 3.00 -> 3.06, cam06 2.50 -> 2.67
Projection registered with no seam (std ratio 0.673, aniso 5.02 / 8.23); shaded attic 127.8 with the photo's chroma; cam03 black 12.6 %, far-shore lines 3. Blockers: QA-08-1 cam02 lens (lead: 27 mm applied, 2f-commit above), QA-08-2 cam02 face indigo (lighting), QA-08-3 sunlit chroma sat 0.462 / R-B 105 (the sun, not the albedo). Majors: archivolt blank (not dispatched), mirror 0.61, cam05 band 133.6 (the gloss-mix trade, held for the hero), cam03 walk hue 92, coffer rim/field. Frame range 1-2616 (cam02's station moved the flythrough route: lighting r16 re-plans to ~50 s). Composite renders/qa_comparisons/round08_gate.png.
Rule: hero < 4.0 after round 8 -> ONE more round (LIGHT r16 only: sun chroma, cam02 face, cam03 hue, flythrough), lead_build.sh, QA round 9, then Phase 5 regardless. In flight: LIGHT r16. Next: review + merge, rebuild, QA round 9.

## 2026-09-10 · LIGHT r16 reported (355f3d6), in review
Sun-side diffuse tint socket + tint b 40 -> 70: sunlit attic sat 0.464 -> 0.489 / R-B 105.7 -> 111.4 (window 0.53 / 120 FAIL; the sun has no blue left and AgX High Contrast caps the box near sat 0.49 at the reference luminance: a colour-management call, not lighting); shaded attic hue/sat hold, lum 127.7 (1.2 over); reflection R-B +50.5; cam02 pier / frieze hue 28 PASS at 27 mm, soffit / right shafts 260-301 FAIL (untried lever: the warm interior fills, cam04's hold); cam03 walk hue 89 unchanged (hand-off to environment: grass bounce + walk albedo). Flythrough: 1224 frames / 51.0 s / 251 m, range 1-1224, cam02 pinned off qa_cameras (ne_apron), exact kinematics 2.52 m/s2, ORN linked in the check (138 origin-parked prototypes excluded), one shrub hit re-routed, clearance 1.57 / 1.43 m, all gates PASS on master.blend.
Decision (lead): QA-08-3 closes as "capped by the shipped view transform"; no look change before Phase 5 (every window of rounds 3-8 is measured under AgX High Contrast). In flight: LIGHT r16 review. Next: merge, lead_build.sh, QA round 9 (final polish round), Phase 5.

## 2026-09-10 · LIGHT r16 merged (a25b2ce + lead corrections); master rebuilt (9679 objects, frames 1-1224, probes baked); QA round 9 dispatched (final polish round); phase5 branch merged
In flight: QA round 9 (Opus xhigh, docs/briefs/qa_round_09.md). Next: gate report with the composite, then Phase 5 regardless (docs/phase5_checklist.md via scripts/phase5_deliver.sh; Fable final gate judgement once).

## 2026-09-10 · QA round 9 in (9d3f28d): hero 3.67 -> 3.67 (+0.00, clock 1 of 2), cam02 2.69 -> 2.94; gate NOT passed; PHASE 5 STARTS (user's rule)
Known-issues list for delivery: docs/qa_round_09.md (QA-09-1..13 + QA-03-16). Lead's final gate judgement in docs/decisions.md. In flight: scripts/phase5_deliver.sh (all steps, packed delivery copy; log renders/logs/phase5_driver.log and phase5_<step>.log). Next: deliverables list, tech notes, final status entry.

## 2026-09-10 · Phase 5 driver run 1: steps 1b-5 done, step 6 cut by the watchdog at 7200 s (511 / 612 frames); chain relaunched detached
Delivery copy master_delivery.blend: packed (89 images, 117 MB), 277.7 MB, reopen 0.86 s, 0 orphans, 9679 objects. Eevee six-camera pass 159 s. 4K hero 128 spp fixed adaptive-off: 1432.6 s wall, peak RSS 6.2 GB (renders/final/hero_cam01_3840x2160_128spp.png). Driver auto-picked 2560x1440 @ 128 (648.5 s) + upscale; lead overrides: native 3840x2160 at 384 spp (~72 min est.) as the final. Flythrough test: 14 s/frame at 640x360 (Eevee, LOD1), resumed at frame 1023 with --frame-start, then ffmpeg at 12 fps.
In flight (detached, log renders/logs/phase5_chain.log): flythrough remainder -> ffmpeg -> 384 spp final. Next: side-by-side + measures on the 384 spp frame, deliverables list, tech notes, final status entry.

## 2026-09-10 · Phase 5: final 4K hero done (f549088); flythrough test frames 1-1021 re-rendering
Final: renders/final/hero_cam01_3840x2160.png = native 4K, 384 spp fixed, adaptive off, OIDN, 4186.5 s wall (the 128 spp probe took 1432.6 s; 768 spp would be ~2.3 h, not taken). Side-by-side renders/qa_comparisons/final_hero_vs_ref169.png (apex 0.44 %H). Boxes on the final: sunlit attic 187.1 / sat 0.488 / R-B +110, shaded attic 126.7 / hue 35.0 / sat 0.447 (in window), reflection 114.4 / hue 41.4 / R-B +52, near water 124.0 / hue 207.6, flank 159.8 / 209.6. Flythrough: the first resume wiped frames 1-1021 (script cleared its output dir; fixed with --fresh / --frame-end, 3669a14); re-render running detached (renders/logs/phase5_chain2.log), then ffmpeg to renders/final/flythrough_test_640.mp4 (612 frames at 12 fps = 51 s). docs/delivery.md written.
In flight: chain 2. Next: verify the mp4 (612 frames), commit it, final status entry, report to the user.

## 2026-09-10 · USER DEFECT in the v1 hero: main arch filled. v1 archived (renders/final/v1, c7d6995); every render from now to renders/final/v2/
Ray cast from cam01 along the bay axis (renders/logs/lead_raycast3.log): rays at z 18 / 20 hit ARCH_rotunda_vault_coffers_00 [ARCH_rotunda, arch_build.py:696 build_vault_coffers, assets/architecture.blend] 2 m past the face at z 18.2 / 20.2 (soffit 23.6). Face check: 67 triangles of 7-11 m2 with normals along the bay axis inside the opening (304 m2) = the rib plate's bridge triangles bent onto the arc as chords. Same on all 8 bays (bay 07 = cam02's "blue soffit"). Not a placeholder, not a metric fill; a round-1 tessellation bug. Lighting r15/r16 measured cam02's shade_soffit box on these chords: that box moves when they go (lighting re-bases after ARCH).
Name sweep: hits are ARCH_rotunda_inner_block_* (real piers) and ENV_backdrop_fill_* (city blocks), both now exempt on record. Gate checks added to CLAUDE.md / qa.md / quality_checklist (f994cb7). Flythrough chain 2 killed (re-render after the fix). In flight: ARCH r8 (docs/briefs/architecture_r8.md). Next: ARCH review + merge, LIGHT r17 (cam02 soffit re-base + warm interior fill), rebuild, QA round 10 hero-only with the tile review, v2 4K.

## 2026-09-10 · ARCH r8 reported (3a358ca), in review
Root cause: arch_lib.plate's cap triangulation spans the outline; vertices were then bent onto the barrel -> chords. Fix: bisect_grid before the mapping (arc step 0.22, depth step 0.90; ceiling ribs 1.00). All 8 bays: worst deviation 6.25 -> 0.381 m, faces > 1 m2 79 -> 0; ray tests clear at z 16-22 on bays 00 and 07; tris +5.2 %. The "slab" was the far bay's chords through the rotunda. cam03 column 028: fluted (24 flutes, 86 mm), capital instanced 77 deg above the frame; reads plain because it is near-black (lum 3.7) -> lighting. Tiles: arch fixed on cam01/02/03; remaining non-ARCH defects seen: violet shaded shafts + speckle on sunlit ones (lighting), flat leaf cards / faceted birds / black foliage clumps (environment), checkerboard colonnade paving (materials), untextured near-white dome cap (materials).
In flight: ARCH review. Next: merge, LIGHT r17 (cam02 soffit re-base, warm interior fill, cam03 near column level), rebuild, QA round 10 hero-only with tiles, v2 4K + flythrough re-render.

## 2026-09-10 · ARCH r8 merged (3a358ca + lead correction); LIGHT r17 dispatched
Carries: LOD1 +12.6 % tris (1.25 M on ARCH; re-check open time at Phase 5), cam03 px width hand-derived, ceiling ribs not rendered (cam04). In flight: LIGHT r17 (docs/briefs/lighting_r17.md). Next: LIGHT review + merge, lead_build.sh, QA round 10 hero-only with the tile review, v2 4K, flythrough re-render.

## 2026-09-10 · LIGHT r17 reported (5dfdbf3), in review
Same box / same rig / ARCH r8 geometry: cam02 pier 268 -> 270 (violet stays: the az-25 blue shade lamp seen down its axis from cam02; both discriminators break the hero -> frontier, nothing shipped), r16 shade_arch box was on a shaft cluster (retired); hero reflection R-B +50.5 -> +32.2 from the geometry alone (the open arch now mirrors sky + vault; lead: accepted). Soffits: new soffit_l / soffit_r boxes hue 36 / 34, sat 0.34 / 0.32, rib-field contrast 111 / 115 PASS via the interior fill colour (1,0.86,0.68) -> (1,0.95,0.88), cam04 coffer ratio 0.386 hold. cam03: new LIGHT_gallery_fill (16 warm up-facing strips, 1200 W Cycles / 0 Eevee, level set by ref 128: near column 0.305 vs photo 0.292): p95 20 -> 89, flutes 33 lum, frame < 10 lum 39.9 -> 6.6 %, outer row 0.289. Speckle on sunlit shafts = shaft albedo texture frequency (materials hand-off); walk albedo ~2x light (env/materials). Hero holds identical except reflection. Flythrough gate PASS.
In flight: LIGHT r17 review. Next: merge, lead_build.sh, QA round 10 (hero-only, tiles), v2 4K on PASS, flythrough re-render.

## 2026-09-10 · LIGHT r17 merged (5dfdbf3 + lead docstring fix); master rebuilt for QA round 10
Review carries: the probe bake now includes the gallery strips at 1200 W (the bake deliberately uses the Cycles rig; Eevee cam03 in QA round 10 shows the effect, Phase 5 re-checks the Eevee pass time), the committed AFTER frames are the 2000 W sweep while 1200 W shipped, ref 128's 0.292 not measured by a committed script, uncommitted sweep logs, +43 MB tracked PNGs. In flight: QA round 10 (docs/briefs/qa_round_10.md, hero-only + tiles). Next: on PASS the v2 4K (384 spp) + side-by-sides vs ref 169 and v1, flythrough re-render.

## 2026-09-10 · QA round 10 in (22cd0b2): tile review FAIL; hero 3.67 -> 3.56 on the 100 % re-score (like-for-like +0.00); arch opening real (14/14 rays, sky through the arch)
Blockers: QA-10-1 icosphere gulls 7.5 m from the hero camera (lead: floating gulls removed in env_build.py b058e45, environment.blend rebuilding), QA-10-2 vault field 103 lum vs ref 45 (2.3x) + magenta jamb (LIGHT r18 dispatched). Majors for the known-issues list: archivolt absent, coffers as punched holes, side-bay vaults flat plates, column stripes, dome cap untextured, cam02 violet face + gold-on-indigo soffit, ENV_backdrop_hall boxes, cam03 chequer paving + flat olive near column. Name sweep: LIGHT_shade_fill_00 exempt by name. Reflection column 115.8 -> 131.5 (clears the floor) with R-B +32.
In flight: LIGHT r18, env rebuild (lead). Next: LIGHT review + merge, lead_build.sh, QA round 10b tile re-check (hero only), v2 4K on PASS, flythrough re-render.

## 2026-09-10 · LIGHT r18 reported (fc01eb8) + lead's shade-fill-off (f40d0e7), in review
r18: the hero's "vault field" box is the central ceiling seen through the arch (= cam04's coffer surface); VAULT_FILL bay weights [0,0,0,0,0,0,1,1] -> field 103.1 -> 61.1 (window 45-65) with cam02 soffits held (hue 36 / 34, sat 0.34 / 0.33, field hue 26.5 / 12.9), hero entablature 132.9 -> 120.9, cam04 coffer ratio 0.386 -> 0.347 (0.003 under). Magenta jamb = LIGHT_shade_fill_00 (B +28 on the jamb); landing it (lamp off) costs the hero shaded-attic hue (35 -> ~41) and sat (> 0.50). LEAD'S CALL: lamp off (energy 49 -> 0); the arch reading right at 100 % outranks the two shade windows; cam02's pier lands too (r16: w 0 -> pier hue 23). Moved numbers to be confirmed by QA round 10b.
In flight: LIGHT r18 review. Next: merge, lead_build.sh, QA round 10b (hero tiles re-check), v2 4K on PASS, flythrough re-render.

## 2026-09-10 · LIGHT r18 + shade-fill-off merged (a765b9d); master rebuilt (probes re-baked); QA round 10b dispatched
In flight: QA round 10b (hero tiles re-check, docs/briefs/qa_round_10b.md). Next: on PASS the v2 chain (delivery copy, 4K 384 spp to renders/final/v2, flythrough --fresh, ffmpeg), then the v1 | v2 | ref 169 composite (scripts/qa_v1v2_sheet.py) and the report; on FAIL fix the named tile defect first.

## 2026-09-10 · QA round 10b in (88498ab): tile review PASS; hero 3.56 -> 3.61; sweep 0 hits, rays 14/14
QA-10-2 boxes: vault field 60.6 (45-65), jamb hue 25.0 / R-B +36 PASS. Moved holds (shade fill off): shaded attic 122.1 / hue 41.2 / sat 0.628 (hue + sat FAIL), sunlit attic sat 0.518 (toward ref), reflection 128.6 / +34.4, entablature 0.83x ref, building sat 1.22x ref (QA-10b-1 major: shade reads mustard; the one cheap lever left = a low-energy NEUTRAL shade fill or a shade-side saturation pull on the concrete), cam03 near column 0.192 of sunlit (was 0.305; QA-10-17 worse), cam02 pier warm (44.9) with one shaft cluster still magenta.
In flight: v2 chain (renders/logs/v2_chain.log): packed delivery copy -> 4K 384 spp -> flythrough --fresh -> ffmpeg. Next: v1 | v2 | ref composite (scripts/qa_v1v2_sheet.py), side-by-side vs ref 169, delivery notes v2, report.

## 2026-09-10 · v2 4K hero done (renders/final/v2/hero_cam01_3840x2160.png, 384 spp, 4207.8 s); side-by-sides + delivery notes committed
Lead's six-tile pass: arch open (coffered barrel, far arch, sky); no blocker; known issues as docs/delivery.md. In flight: flythrough --fresh (612 frames) then ffmpeg to renders/final/v2/flythrough_test_640.mp4 (renders/logs/v2_chain.log). Next: commit the mp4, final status entry, report to the user with renders/final/v2/v1_v2_ref169.png.

## 2026-09-10 · PHASE 5 v2 DELIVERED (final status entry of this session)
Deliverables (docs/delivery.md): master.blend (a765b9d build, 9695 objects, LOD1 11.52 M, opens 0.75 s) + assets/*.blend; master_delivery.blend (packed, 277 MB, gitignored; `PFA_PACK=1 scripts/phase5_deliver.sh 1b` rebuilds it); renders/final/v2/hero_cam01_3840x2160.png (384 spp, 4207.8 s); renders/final/v2/final_hero_vs_ref169.png and v1_v2_ref169.png; renders/final/v2/flythrough_test_640.mp4 (612 frames, 51 s, 6970 s wall at 11.4 s/frame Eevee 640x360); v1 kept under renders/final/v1. QA: round 10b PASS (hero 3.61), known issues in docs/qa_round_10b.md + docs/delivery.md. Gate checks in CLAUDE.md. All worktrees clean; no Blender running; watchdog loop still running (pid in renders/logs/watchdog.log).
Next session, if any: QA-10b-1 neutral shade fill (lighting), coffer depth + archivolt band (architecture + ornament), shoreline (environment); every gate with the name sweep + six-tile review + ray test.

## 2026-09-15 · PHASE 6 session 1 (lead): docs read, toolchain installed, inventory run, addendum drafted, Gate 0 brief written; waiting for the user's approval of the addendum before dispatch
Inventory (export/inventory.py, 29 s): the stated export set is 30.5 M placed tris (ORN instances 22.9 M, ENV LOD1 4.8 M, ARCH 2.85 M) vs the 3 M budget -> Gate 1 is decimation (plan §2). Look read from the file: AgX High Contrast, exposure -2.833 -> LUT in the viewer. Tools: gltfpack 1.2 + toktx 4.4.2 in tools/ (not in Homebrew), scripts/chrome_run.sh (raw headless screenshot lingers 60-90 s: puppeteer route).
In flight: nothing (no Blender, no Chrome running; watchdog loop pid 46808 still up). Next: user approves docs/briefs/phase6_addendum_draft.md -> append to CLAUDE.md, dispatch Gate 0 (docs/briefs/phase6_gate0.md: bake engineer on phase6-bake, viewer engineer on phase6-viewer), fill plan §4 from the timings, status + burn.

## 2026-09-15 · Addendum approved (4 changes applied, CLAUDE.md a0a7156); Gate 0 dispatched
In flight: bake engineer (Opus xhigh, branch phase6-bake: export/ scripts, bakes, LUT, sky, manifest, Cycles slice frame) and viewer engineer (Opus high, branch phase6-viewer: web/ Vite+three, station math, LUT pass, screenshot tool). GPU: bake engineer owns it; Chrome only when export/out/bake_queue/status.json is idle.
Next: Gate 0 reports -> lead checks the pair image + numbers, fills plan §4, logs the three ORN options in decisions.md for the user's choice, status + burn, stop and report.

## 2026-09-15 · Gate 0 bake report in (phase6-bake 536fc15): all 7 steps; review dispatched; viewer engineer finishing the pair image
Lightmap 2K 128 spp OIDN: column 306 s, capital 221 s, ground 461 s (plan §4 filled); LUT 65^3 proven 0.072/255; equirects sun az error 0.03 deg; gate0.glb 57 MB (16 column placements + capital + pedestal, 62 k tris); ORN options (a) 29.5 h / 4.3 GB, (b) 2.7 h / 357 MB, (c) 3.3 h / 451 MB -> decisions.md, user chooses. GPU idle (status.json).
In flight: code review of phase6-bake (Opus, read-only) -> docs/reviews/phase6_bake_gate0_review.md; viewer engineer (phase6-viewer) taking the cam01 screenshot + pair sheet. Next: review verdict, lead looks at renders/web/gate0_pair.png (960 px), merge both branches, tech_notes, burn, report.

## 2026-09-15 · Gate 0 viewer report in (phase6-viewer ef6a270): column bbox delta 0 px, sky +2.5/255, GPU cost 0.2 ms at 1280x720 for 62 k tris; lead viewed renders/web/gate0_pair.png (960 px): registration and sky match, 15 borrowed-lightmap columns dark (expected until Gate 3), lit column 0.76-0.85 of Cycles = the missing compositor haze (Gate 4 item; manifest gets a compositor block)
In flight: code reviews of phase6-bake and phase6-viewer (Opus, read-only). Next: merge both with fixes, tech_notes "Phase 6" (three Blender 5.2 findings), Gate 0 verdict to the user, ORN + trees decisions from the user, burn.

## 2026-09-15 · Both Gate 0 reviews in (MERGE WITH FIXES: bake 10 findings, viewer 12 incl. one latent blocker); fixes running
Bake fixes done (290b574): lightmap_scale = pi in the manifest, ground hi-twin excluded (461 -> 300 s, Gate 3 queue projection 5.9 h), NoColorSpace step, clipped count on the source EXR, manifest reset, sync without --delete; carries in export/README.md. Open question the two reviewers split on: is the column's 0.76x a missing pi or the missing compositor haze -> a no-compositor Cycles frame + a two-scale viewer test settles it.
In flight: bake engineer (no-compositor frame, sky.rotation_deg), viewer engineer (findings 1-6, lightmap_scale + sky rotation from the manifest, then the pi parity test, pair sheet vs the no-compositor frame). Next: merge both, tech_notes, Gate 0 verdict, burn.

## 2026-09-15 · GATE 0 PASSED (lead's read; user signs off) — both branches merged into main (70bfe73); session 1 closes
Viewer vs no-compositor Cycles at cam01: bbox delta 0 px, sky 1.011, lit column 0.922 / 0.985 with lightmap_scale = pi (the contract); vs the composited frame 0.897 / 0.952 = the missing compositor (Gate 4). GPU cost 0.1-0.3 ms at 1280x720 for 62 k tris; gate0.glb 58.8 MB (mostly 2K textures); web/dist 2.0 MB. Tech notes "Phase 6" written; carries in export/README.md + web/README.md.
Burn this session (docs/usage/usage_from_transcripts.py, list rates, nominal): $77.94 = Opus 65 (bake xhigh, viewer high, two reviews) + Fable 13 (lead), 2.0 h wall, 4 agents. No Blender/Chrome running, watchdog state dir empty, both worktrees clean.
Next session: user's three decisions (ORN option, trees option, material round yes/no) -> Gate 1 brief for an export engineer (export set, per-asset budgets docs/briefs/phase6_budget.md, decimation, ORN normal bakes, name sweep on export_set.json) + QA critic silhouette/normal check at six stations; keep the uncommitted docs/environment_notes.md edit (two tree heights, pre-session) for the user to confirm.

## 2026-09-15 · User decided (ORN c, impostors + thinned near trees, one material round); Gate 1 + MAT r10 dispatched
Briefs: docs/briefs/phase6_gate1_export.md (Opus high, branch phase6-export), phase6_gate1_viewer.md (Opus high, phase6-viewer r2), materials_r10.md (Opus xhigh, branch materials; dome cap + coffer only, lighting frozen). GPU sharing: queue jobs and builder frames start only with no other live registered Blender pid; Chrome only with status.json idle + no Blender.
Next: reports -> reviews -> merge MAT r10 -> regenerate master_delivery.blend (PFA_PACK=1 phase5_deliver.sh 1b) -> QA critic Gate 1 (silhouette/normal at six stations, tiles, name sweep) -> Gate 2 brief.

## 2026-09-15 · Viewer r2 reported (phase6-viewer 02ccbf3): multi-glb + instancing + progressive loading done; six-station capture blocked on the glbs (ORN bake queue 2/33 at 12:45, ~250 s per job)
Manifest v2 read cleanly: 2 743 570 placed tris (ARCH 0.84 M / ORN 1.10 M / ENV 0.79 M), 154 batches, 127 far trees, 7 stations. FloatType LUT cut the ground-band error 17.1 -> 3.1 of 255. Hand-off to export: rgbm_range missing in v2's texture schema (sent).
In flight: export engineer (queue + glbs), MAT r10 (rendering), viewer r2 code review. Next: when glbs + idle -> lead runs web/tools/gate1.sh (one command) -> Gate 1 QA critic; MAT r10 review + merge -> regenerate master_delivery.blend.

## 2026-09-15 · Viewer r2 merged (d08dd9a, review fixes incl. the per_class blocker and the double-render perf bug); capture waits for the glbs
In flight: export engineer (ORN queue + four glbs), MAT r10. Next: glbs + idle -> lead runs `web/tools/gate1.sh` -> QA critic Gate 1; MAT r10 review/merge -> regenerate master_delivery.blend.

## 2026-09-15 · MAT r10 reported (materials e1a4964), in review; lead viewed both crops
Dome cap: lum 187.6 -> 205.4 (pass), hue pass, sat 0.352 / col-sd 5.4 fail — the box is 1/3 drum cornice (sat 0.92 = QA-10b-1, lighting) and a control render bounds the box at 207 lum; the membrane now shows 28 panels + ridges + wide streaks (crop: reads as the photo's cap, cornice still yellow). Coffer: field sat 0.422 / rim 0.454 (both in window, ratio = ref). Holds within tolerance; jamb hue 23.8 (QA-10-2 floor 25, flagged). Deviations: 2 heroes + 3 cam04; ran concurrent with the ORN queue (one job at a time).
In flight: mat_r10 review, export engineer (queue 4/33 at 12:56). Next: merge MAT r10 -> lead_build.sh + regenerate master_delivery.blend (after the queue is idle: the queue reads the delivery file) -> gate1.sh capture -> QA critic Gate 1.

## 2026-09-15 · MAT r10 merged into main (e0980f5); master rebuild + delivery regeneration queued behind the ORN bake queue
In flight: export engineer (queue). Next: queue idle -> lead_build.sh -> PFA_PACK=1 phase5_deliver.sh 1b -> gate1.sh capture -> QA round 11 (docs/briefs/qa_round_11.md).

## 2026-09-15 · Gate 1 export reported (phase6-export e88da10): 2 736 570 placed tris (ARCH 0.84 / ORN 1.10 / ENV 0.79 M), 140 batches in the hero frustum, name sweep 0 hits, ORN queue 33/33 in 5 766 s; four glbs 187 MB (orn.glb 155 MB); texture projection 1 343 MB vs 1 200 budget (levers named)
Lead ran web/tools/gate1.sh: six stations captured, 1440p GPU cost 2.1 ms median (60 fps vsync-capped), 201.8 MB loaded in 2.6 s. Hero pair sheet viewed at 960 px: silhouette registered, far-tree billboards as flat quads by design, grey materials.
In flight: QA round 11 (Opus xhigh, docs/briefs/qa_round_11.md), phase6-export code review, master rebuild + delivery regeneration with MAT r10 (renders/logs/lead_build_r11.log, phase5_r11_1b.log). Next: merge export on review, Gate 1 verdict, Gate 2 brief (PBR bakes on the regenerated delivery file), burn, stop.

## 2026-09-15 · master.blend rebuilt with MAT r10 (9691 objects, probes 5.4 s) and master_delivery.blend regenerated (280.3 MB, reopen 0.83 s, 89 packed); Gate 2 bake brief drafted (docs/briefs/phase6_gate2_bake.md)
In flight: QA round 11, phase6-export review. Next: export merge, Gate 1 verdict, dispatch Gate 2 (bake engineer r2) + a viewer Gate 2 round, burn, stop.

## 2026-09-15 · QA round 11 in (1bc08bb): GATE 1 FAIL — two export blockers; budget / perf / name sweep / silhouette PASS
Blockers: env.gltf texCoord -1 on the ten backdrop materials (probe texture on UV-less meshes) drops 151 737 ENV tris at every station; the three voxel-remeshed attic panels read torn. Rows out of parity: cam06 Silhouette -1.0 (the missing backdrop), cam02/cam05 Ornament -1.0 (the panels). Station averages 3.50 / 3.00 / 2.60 / 3.00 / 2.90 / 2.80. Silhouette vs the Cycles hero: scale 1.0000, apex delta 0.00 %H. New QA rule: no metric rests on a placeholder (far-tree quads cover 16-34 % of frames) -> re-capture with ?billboards=0. Viewer got the channel clamp (1a47122).
In flight: export engineer (five review fixes + B1 texCoord + B2 attic panels via the LOD1 base, three re-bakes). Next: re-pack -> lead re-captures (billboards off) -> QA round 11b tile re-check -> merge export -> Gate 2 dispatch.

## 2026-09-15 · Export fixes in (ec4832b: sRGB tags, status sync, slot gutters 248/256, manifest flags, B1 backdrop texCoord asserted, B2 attic panels from the LOD1 mesh at 7 999 tris, dev 51-59 mm); phase6-export merged (8bfd907); lead re-captured with billboards off (1440p GPU 1.5 ms hero); QA round 11b dispatched
In flight: QA 11b (tile re-check + re-score). Next: on PASS dispatch Gate 2 (docs/briefs/phase6_gate2_bake.md, bake engineer r2) + write the viewer Gate 2 brief; burn; stop.

## 2026-09-15 · QA 11b (850209e): B1 + B2 FIXED, all rows within 0.5 (provisional) but GATE 1 FAIL: the export's own 127 opaque ENV_treeboard_* stand-ins in env.glb cover 16-26 % of the frames (44.5 % of the arch opening); cam04 ceiling sliver (QA-11-9) open
Lead: viewer ?treeboards=0 hides the boards by material name (gltfpack -mi drops node names; b58240b), re-captured with both placeholder sets hidden (127 hidden, hero frame changed over 341 k px). Export engineer asked for: sweep pattern board|impostor|billboard with the exemption on record, QA-11-9 sliver, boards tagged in the glb.
In flight: QA 11c (re-check on the clean capture), export fixes. Next: Gate 1 verdict -> Gate 2 dispatch.

## 2026-09-15 · Export 2c1c7fe merged (4190b62; boards cut, cam04 rib group as modelled at 160 828 tris, scene 2 841 396); sweep pattern updated; capture 4 taken; QA 11c dispatched; Gate 2 viewer brief written
In flight: QA 11c. Next: on PASS dispatch Gate 2 bake (phase6_gate2_bake.md) then the viewer Gate 2 round (phase6_gate2_viewer.md) once manifest v3 exists; burn; stop.

## 2026-09-15 · QA 11c (9ef4fd7): boards proven out (0 % coverage), QA-11-9 FIXED, arch ray test PASS, budget/perf PASS — GATE 1 FAIL on QA-11c-1: 1379 ENV_shrub_*_LOD2 nodes exported with no transform (drawn at the origin; site planting absent, Scale cues -1.0 at five stations)
Lead: viewer reads lightmap_encoding.rgbm_range (QA-11c-3). Export engineer fixing the ENV node transforms with writer assertions (env.glb only). Next: re-capture -> QA 11d -> Gate 2.

## 2026-09-15 · Export a9b2d3d merged (77eafe8): shrubs placed from their LOD1 siblings (the delivery file keeps LOD0/LOD2 ENV stubs at the origin — tech_notes), writer assertions + verify_glb; capture 5 taken; QA 11d dispatched
Next: on PASS dispatch Gate 2 bake + viewer rounds; burn; stop.

## 2026-09-15 · GATE 1 PASSED (QA 11d, 57addb8; decisions.md). Gate 2 dispatched: bake engineer r2 (PBR bakes, docs/briefs/phase6_gate2_bake.md) + viewer r3 (docs/briefs/phase6_gate2_viewer.md)
Session burn so far (usage_from_transcripts, nominal):  253.40   opus-5 223, fable-5-1 30 . In flight: Gate 2 bake (GPU queue), viewer r3 (waits for manifest v3). Next: reviews, merges, Gate 2 capture + QA round 12 (PBR alone, direct lighting), then Gate 3 brief.

## 2026-09-15 · Gate 2 bake done (a9794e8): 60 jobs / 182 maps / 3 245 s of bakes, KTX2 274.5 MB, resident projection 1 166 MB of 1 200; verification on the Gate 0 slice worst 2.78 % (inside 3 %); manifest v3 synced
In flight: phase6-bake Gate 2 code review; export engineer (backdrop UV1 into env.glb, -vp 16); viewer r3 (PBR wiring + capture, GPU free). Next: review + merges, Gate 2 capture, QA round 12 (PBR alone, direct lighting), Gate 3 brief (lightmaps + impostors + probe), burn, stop.

## 2026-09-15 · Viewer r3 reported (phase6-viewer 875d7d9): PBR wired (55/65 materials, 531 MB of ASTC), 1440p GPU 0.3-1.9 ms, hero pair ratio 1.141 (direct mode, no lightmaps), QA-11d-1 regional batches (cam04 tris -15.6 %); resident 1 395 MB at 1440p incl. 437 MB render targets (textures 921 of the 1 200 budget)
Hand-offs: nine of ten backdrop material bakes reach nothing until env.glb is re-exported with UV1 (export, in progress); direct-mode diffuse needs a camera-branch PMREM (Gate 3 bake adds it). One Chrome slip (10 s during a bake, killed). In flight: bake Gate 2 review, viewer r3 review, export hand-off. Next: merges, gate2 pair sheets, QA round 12.

## 2026-09-15 · Gate 2 reviews in: bake MERGE WITH FIXES (queue own-pid exemption, metallic albedos via emission, ORN size rule), viewer r3 MERGE WITH FIXES (PMREM double-counted in resident memory: real 1 294 MB at 1440p; check_manifest_files unwired; pair sheets gitignore); export hand-offs merged (4f85205: backdrop UV1 in env.glb, -vpf)
Found by the viewer review: gltfpack merged the ten backdrop materials into one, so nine Gate 2 backdrop sets attach to nothing -> export re-packs env.glb with -km; bake flips uv1_in_glb for the ten. In flight: bake fixes, export -km, viewer fixes then the Gate 2 re-capture. Next: merges, QA round 12.

## 2026-09-15 · Gate 2 fully merged (bake c1bdb5a, export 9712f80, viewer dfe8609): all 60 material sets attach incl. the ten backdrop groups; hero pair ratio 1.090 in direct mode, 267 draws, GPU 1.7 ms, resident 1 334 MB at 1440p (textures 921 of 1 200); QA round 12 dispatched (docs/briefs/qa_round_12.md)
Next: Gate 2 verdict -> Gate 3 bake (docs/briefs/phase6_gate3_bake.md) + Gate 4 viewer brief; burn; stop.

## 2026-09-15 · QA round 12 (1a8a2ab): GATE 2 FAIL on one row (cam05 Material realism -1.0): QA-12-1 — 7 of 12 ARCH/ground sets ship no normal map (the material bump is in neither map; pier-face grain 0.27x of Phase 5) and the two colonnade UV1 atlases have 0.16 coverage. Right: whole-building sat 1.02x of the photo (QA-10b-1 closed by the bake), backdrop + pedestals textured (QA-11c-2 closed), ORN relief real on all 33
Dispatched: export re-lays the two colonnade UV1 atlases (>= 0.40), bake bakes bump -> tangent normals for all twelve ARCH/ground groups + re-bakes the two re-laid groups. Carry: QA-12-4 one texture per shared mesh (Repetition -0.5 everywhere) goes to Gate 3's per-instance slot; the report's 921 MB vs the capture's 855.6 MB texture figure to reconcile. Next: re-capture, QA 12b, Gate 3.

## 2026-09-15 · Atlas split merged (2aed50f): 52 UV1 groups, hero stone coverage 0.056 -> 0.191, colonnade 0.040 -> 0.28 (instanced) + 0.11 (merged mass, geometric cap), +2 atlases; bake engineer re-baking the eleven groups + bump-derived normals for every ARCH/ground set
In flight: bake queue (QA-12-1). Next: lead re-captures (gate2.sh), QA 12b, Gate 3 dispatch.

## 2026-09-15 · Bake QA-12-1 pass merged (8a3d06a): 19/19 ARCH/ground re-baked on the split atlases (2 229 s), normals on every set, colonnade texel 9.4 -> 1.07 cm; grain moved to materials.detail (5 tiling sets, 20 MB) — viewer r3 wiring it now, then the Gate 2 re-capture and its own measurement of the QA-12-1 boxes
Next: QA 12b -> Gate 3 dispatch (docs/briefs/phase6_gate3_bake.md) -> burn -> stop.

## 2026-09-15 · Viewer detail layer merged (5eb698e); BLOCKER found by its empty-map guard: all 15 shipped detail maps are all-zero PNGs/KTX2 -> bake engineer re-exporting with on-disk verification + mean_linear per map. Synthetic-noise proof of the layer: cam05 pier std 22.9 -> 25.7 (Phase 5 38.3), cam01 wall hp9 6.0 -> 8.7, attic unmoved
Resident 1 400 MB at 1440p (textures 920 after the 19 normals; detail adds 20 MB as KTX2). Next: real maps -> viewer re-capture + boxes -> QA 12b -> Gate 3.

## 2026-09-15 · Detail layer live (viewer f8b1986 merged): works, but the shipped maps' contrast is 3-6 % and mips filter it -> QA-12-1 boxes move ~1 % (cam05 pier std 22.9 vs Phase 5 38.3; gain 6-10 would reach it, refused as a knob). Bake engineer re-deriving the detail normals at the Bump's real slope (Distance 0.015 m at 2-3 mm/texel) and tagging the albedo KTX2 sRGB
Resident 1 338 MB at 1440p (tex 987 incl. 67 MB of detail PNGs; KTX2 saves 47). Next: viewer re-measure -> QA 12b (with lighting attribution: the Phase 5 box std includes shade) -> Gate 3.

## 2026-09-15 · Detail re-derivation merged (4c763c9): honest slope from 8-bit height sources (normal std 0.024 / 0.019), albedo contrast +35 %, colour spaces verified on disk; decision: the remaining cam05 amplitude is shading/occlusion (Gate 3). Viewer taking the final Gate 2 capture with the KTX2 detail set; QA 12b brief written (docs/briefs/qa_round_12b.md)
Next: QA 12b -> Gate 3 dispatch -> burn -> stop.

## 2026-09-15 · Final Gate 2 capture merged (viewer 9dcdc1e / 3be52fb): KTX2 detail set (33.6 MB), colour spaces right (cam05 box mean 144.8 vs Phase 5 145.4), QA-12-1 boxes moved < 1.5 % (material share exhausted); resident 1 305 MB at 1080p / 1 434 at 1440p; QA 12b dispatched
Next: Gate 2 verdict -> Gate 3 bake dispatch -> burn -> stop.

## 2026-09-15 · GATE 2 PASSED (QA 12b, 19412e4; decisions.md). Gate 3 bake dispatched (docs/briefs/phase6_gate3_bake.md: lightmaps, ORN/ARCH slot atlases, impostors, hero probe; ~6 h detached queue)
Session burn (usage_from_transcripts, nominal):  455.69   opus-5 409, fable-5-1 46 . Next session: Gate 3 report -> review -> merge -> Gate 4 viewer (docs/briefs/phase6_gate4_viewer.md) -> QA round 13 (lightmaps alone) -> Gate 4 QA rounds toward the 6a definition of done.

## 2026-09-15 · CHECKPOINT — lead context 528k (rule: clean restart past 350k); Gate 3 bake queue running detached
State: main at d7ef352 + this entry; all worktrees clean; Gate 0-2 merged; Gate 3 bake engineer (fresh agent this session) launched the detached queue from .claude/worktrees/phase6-bake (export/bake_queue.sh; status.json copied to MAIN export/out/bake_queue/status.json). A restart kills the agent, not the queue.
Resume procedure: (1) `pgrep -fl "bake_queue|MacOS/Blender"`, read export/out/bake_queue/status.json (running -> leave it; idle -> check done == total and the per-job records); (2) if the queue died, re-launch it from the bake worktree (it resumes, skipping done jobs); (3) dispatch a FRESH Gate 3 bake agent (docs/briefs/phase6_gate3_bake.md) to finish/verify from the records, write manifest v4, sync, report; code review; merge; (4) Gate 4 viewer (docs/briefs/phase6_gate4_viewer.md), QA round 13 (lightmaps alone) then the Gate 4 rounds; (5) burn per session via docs/usage/usage_from_transcripts.py. Today's burn: $455.69 nominal (Opus 409, Fable 46).

## 2026-09-16 · Gate 3 bake COMPLETE overnight (phase6-bake 08901f1, unmerged, unreviewed): 65/65 jobs in 6 h 30 m, manifest v4 synced (432 MB), resident Gate 3 251 MB (total 1 055 MB carried / 1 204 vs the measured viewer baseline)
Blocker for export: Gate 1's UV2 is margin-dominated on 7 assets (S colonnade 0.0095 of its map = 33 cm/texel); the bake engineer re-unwrapped them in its own blend (4.6-17 cm/texel) and wrote export/out/gate3/lightmap_uv2.npz — env/arch glbs must be re-exported with that UV2 (and COLOR_0 for the 14 vertex-irradiance meshes) before the viewer applies them (uv2_in_glb false meanwhile). Impostors: 16 atlases (46 far trees mapped to LOD1 prototypes), probe culled below the water, sky.diffuse exported for QA-12b-1. Open for QA 13: cam04 plaster shell in front of the coffer mesh (bakes 4.9 % non-zero), a broadleaf tree inside a city block (Phase 5 placement), near-tree shadows lighter (thinned cards). Tech-note traps: OPEN_EXR_MULTILAYER needs media_type MULTI_LAYER_IMAGE and use_exr_interleave; plan §1's "gallery fill 0 W in Cycles" is wrong (1200 W, Cycles-only).
NOT dispatched (lead context past the restart rule): the phase6-bake Gate 3 code review, the export UV2/COLOR_0 re-export, the Gate 4 viewer round, QA round 13. Next session starts with the review.

## 2026-09-16 · Session 2 (lead): Gate 3 bake review + export UV2/COLOR_0 re-export + Gate 4 viewer round dispatched
GPU idle (queue 65/65, no Blender pids). Dispatched in parallel: code reviewer (Opus, read-only) on phase6-bake 08901f1 -> docs/reviews/phase6_bake_gate3_review.md; export engineer (Opus high, phase6-export) on docs/briefs/phase6_gate3_export.md (Gate 3 UV2 as TEXCOORD_1 on the seven relaid assets, COLOR_0 on the 14 near trees, hand-off json, no manifest edit); viewer engineer (Opus high, phase6-viewer) on docs/briefs/phase6_gate4_viewer.md with item 1 (baked lighting) captured first as the QA-13 input.
Next: merge the bake after review fixes (manifest flags flipped from the export hand-off), QA round 13 (lightmaps alone) on the viewer's baked capture, then the Gate 4 rounds.

## 2026-09-16 · Gate 3 bake review in (79ee07b): MERGE WITH FIXES (5 fix now, 9 carry); bake fix agent dispatched
Fix now: impostor centre/bbox measured from the bbox bottom not the trunk base (willows), normal+depth encode formula misdocumented, vertex_irradiance.npz is uint8 gamma-2 (README promised float32 linear) with one shared range (rel_p99 0.244) -> per-mesh float32, impostor normal+depth declared rgba8 but packed UASTC. Export engineer told to do UV2 first and hold COLOR_0 for the corrected npz; viewer engineer told the three impostor fields change.
Next: merge phase6-bake after the fixes (manifest flags flipped from the export hand-off json), then QA 13 on the viewer's baked capture.

## 2026-09-16 · Export Gate 3 hand-off in (phase6-export 095f855): UV2 relay in arch/ground.glb; BLOCKER found — gltfpack stripped TEXCOORD_1 from every glb since Gate 1
Fixed with -kv on arch + ground (verify_glb PASS, +1.74 MB, hand-off json written with uv2_all_meshes: 33 arch/ground true, 33 orn false); COLOR_0 held for the float32 npz. Lead decided (decisions.md): orn strips its cavity COLOR_0 and packs with -kv; vertex irradiance = gamma-2 per-mesh range, FLOAT_COLOR, env.glb -vc 16. Export engineer resumed for orn now, COLOR_0 after the bake fix lands; bake fix agent told to carry the per-mesh range from the hand-off json; viewer told arch/ground now carry UV2.
Next: bake fix report -> export COLOR_0 -> merge bake + export -> QA 13 on the viewer's baked capture.

## 2026-09-16 · Bake review fixes in (phase6-bake ac63e44) and MERGED (b0ddafe): 5/5 fix-now closed without a re-bake
Willows re-datumed from the trunk base (+22.8 % / +6.4 %), depth formula corrected, vertex irradiance float32 linear (rel_p99 0.244 -> 0 on all 14), normal+depth labelled UASTC, tech notes + README v4 aligned; manifest flags flipped from the export hand-off (16/16 own maps uv2_in_glb true, slots false until orn.glb, vertex in_glb false until COLOR_0). Export engineer resumed for orn -kv + COLOR_0; viewer told the renamed impostor keys.
Next: on the export report, lead runs `python3 export/manifest_v4.py` + `export/sync_main.sh` and merges phase6-export; viewer takes the baked capture; QA 13.

## 2026-09-16 · CHECKPOINT (user leaving; session 2 closes) — bake merged, export mid-COLOR_0, viewer baked capture taken, QA 13 not dispatched
State: main at 78de4f0 + this entry (phase6-bake merged at b0ddafe with all review fixes). phase6-export at f603c14+: orn.glb re-packed with -kv and the cavity COLOR_0 stripped, synced (uv2_relay_status.json: 66/66 meshes uv2_in_glb true); the near-tree COLOR_0 encode into env.glb (gamma-2 per-mesh range, FLOAT_COLOR, -vc 16) was IN PROGRESS and uncommitted when the session closed — the agent was told to commit WIP; check `git -C .claude/worktrees/phase6-export status` and its last commit message first. phase6-viewer at 396bd4b+: Gate 4 item 1 (baked lighting: own maps, 988 slots, sky.diffuse) done and a six-station baked capture committed ("round-13") — it may predate orn.glb's UV2 landing (ORN slot lightmaps missing in it if so); items 2-7 not started. Both agents told to commit WIP and stop.
Resume procedure (fresh agents, briefs on file): (1) `pgrep -fl "MacOS/Blender|chrome"` must be empty; read the two worktrees' last commits. (2) Export: dispatch a fresh export engineer (Opus high) on docs/briefs/phase6_gate3_export.md item (2) only, from the WIP commit: COLOR_0 for the 14 trees from the float32 npz, relay json vertex block, verify_glb, sync; then the LEAD runs `python3 export/manifest_v4.py && export/sync_main.sh` from the main checkout (flips slots + vertex_irradiance flags), code review of phase6-export (docs/reviews/phase6_export_gate3_review.md), merge. (3) Viewer: fresh viewer engineer (Opus high) on docs/briefs/phase6_gate4_viewer.md from the WIP commit: re-sync assets, re-take the six-station baked capture with orn UV2 + COLOR_0 live (post off), then items 2-7. (4) QA round 13 (Opus xhigh) on docs/briefs/qa_round_13.md against that capture; then the Gate 4 rounds. (5) Burn: run `python3 docs/usage/usage_from_transcripts.py` at the start of the next session for today's total (not captured at this close).
Addendum (after the checkpoint): export WIP committed at 784bfe6 (tree clean; item (2) COLOR_0 never started: env.glb unchanged, relay vertex block empty). Lead re-ran manifest_v4.py + sync: lightmaps.slots.uv2_in_glb now TRUE (orn UV2 live), vertex_irradiance.in_glb false. Resume step (2) stands as written.
Addendum 2: viewer WIP committed at d76bee0 (tree clean, no Chrome). CORRECTION to the checkpoint: renders/web/round13_cam01..06.png were captured BEFORE the -kv re-pack landed — they are the Gate 2 look, NOT a baked capture; QA 13 must not score them. Open blocker (viewer-owned, first task of resume step 3): with the lightmaps attached the hero reads mean luma 117.5 vs the Cycles hero's 140.0 and the colonnade wall bands dark/blue; gamma2 117.5 / linear 109.9 / rgbm8 120.0 / V-flip 117.3 — no decode or orientation reaches 140, so a lightmap-only debug pass must check that the glb's TEXCOORD_1 islands land where the bake put them (compare a solid-colour UV2 test map, or bake-side vs glb-side island centroids per mesh) before any capture. Second finding for the export engineer (resume step 2): gltfpack merged away one node of each colonnade colbase plinth/torus pair, so 114 of the 988 slot placements have no mesh of their own — test `-kn` on arch (or exclude those meshes from the merge) and re-verify placements == 988. Item 1 otherwise verified end-to-end (16/16 own maps usable, 15 attach, 438/988 slots attach, position join error <= 0.089 m, npm test green); items 2-7 not started.

## 2026-09-16 · Session 3 (lead): resume from the CHECKPOINT; burn logged; export COLOR_0 + viewer lightmap debug dispatched
Burn (docs/usage/usage_from_transcripts.py, list rates): session 6460c313 (15th 07:49 -> 16th 06:48, incl. the overnight bake) $586.08 total (was $455.69 at the 15th checkpoint, so ~$130 accrued on the 16th); session 2 today (c47a8492) $46.70 (Opus 42, Fable 5). Phase 6 to date ≈ $635 nominal over two days.
State: no Blender / headless Chrome pids; main 8ea8021; phase6-export 784bfe6 clean (COLOR_0 never started); phase6-viewer d76bee0 clean (item 1 done, hero luma 117.5 vs 140 open). Dispatched in parallel: export engineer (Opus high) on docs/briefs/phase6_gate3_export.md "Resume r2"; viewer engineer (Opus high) on docs/briefs/phase6_gate4_viewer.md "Round 5 resume" (lightmap-only UV2 debug first, then the baked capture after the export merge, then items 2-7).
Next: export report -> lead runs manifest_v4.py + sync_main.sh, code review (docs/reviews/phase6_export_gate3_review.md), merge -> viewer re-syncs and captures -> QA 13 (docs/briefs/qa_round_13.md).

## 2026-09-16 · Export Gate 3 r2 in (phase6-export 6798563): COLOR_0 on the 14 trees, 988 placements by material split; manifest v4 flags flipped; code review dispatched
Export report: Blender 5.2's glTF exporter inserts a fake constant-white u8 COLOR_0 when the material references no colour attribute (real data pushed to COLOR_1) — first run shipped all-white; gltf_gate1.py now drops the fake and renumbers (also explains orn's old COLOR_0/COLOR_1 note). COLOR_0 gamma-2 per-mesh range, 16-bit, round-trip p99 <= 0.7 %. `-kn` rejected (+537 draw calls); a same-named material copy on the second mesh of each gltfpack merge-colliding pair keeps them instanced: arch 27 -> 29 draw calls, +3.6 kB, placements 552 + 436 = 988. verify_glb PASS, name sweep 0 to explain, env +1.15 MB.
Lead ran manifest_v4.py + sync_main.sh: 16/16 own maps uv2_in_glb true, slots true, vertex_irradiance in_glb true (14). Code reviewer (Opus, read-only) on main..phase6-export -> docs/reviews/phase6_export_gate3_review.md. Viewer engineer still on step 0 (lightmap UV2 debug). Next: merge on the review, message the viewer to re-sync + capture round13b, QA 13.

## 2026-09-16 · Export Gate 3 review in (c0120b2): MERGE WITH FIXES (3 fix now, 8 carry, Gate 1's 5 fix-now all closed); export engineer resumed for the fixes
Fix now: gate3_relay_check.py hard-codes the MAIN path (PFA_MAIN_ROOT ignored); encoder reads MAIN's out/gate3 while the checker prefers a local one; the material-split guard is one-directional and relies on -km, which orn/ground do not get. Budget doc's Gate 1 byte table now carries a Gate 3 r2 addendum (arch 4.61 MB / 29 draw calls, env 36.95 MB).
Next: merge phase6-export on the fix report; viewer step 0 finding pending, then round13b capture; QA 13.

## 2026-09-16 · phase6-export MERGED (584a79d) with the 3 review fixes (ed00a62); glbs unchanged since the sync, relay check PASS from main
Fixes: PFA_MAIN_ROOT honoured in gate3_relay_check.py, checker and encoder read the same out/gate3, clear FAIL on a missing npz; material-split guard bidirectional (-km required and dup_names >= split; only arch is split today). 8 carries stay in docs/reviews/phase6_export_gate3_review.md.
In flight: viewer engineer (phase6-viewer) on step 0 then round13b. Next: QA 13 on round13b.

## 2026-09-16 · Viewer round 5 in (phase6-viewer 0b08a6b): lightmap blocker was UV quantisation (viewer-owned, fixed, hero 134.3/140), round13b captured (988/988 slots), water + walk done, impostors not started
Baked beats direct at all six stations (cam01 136.0 vs 146.3 vs Cycles 140.0). Open: vertex irradiance not applied (per-mesh range vs -mi instancing -> export re-encodes at one global range), mist numbers missing from the manifest (export adds compositor.mist), stations 3/5/6 lack Cycles references (lead rendering round13_03/05/06_cycles, blender_run 2400 s, log renders/logs/qa_r13_cycles_refs.log), perf 38.8-60.2 fps at 1440p but GPU cost 0.6-2.4 ms (CPU/compositor-bound, item 6 open). Decisions in docs/decisions.md.
Dispatched: QA 13 (Opus xhigh) on round13b from the viewer worktree; code reviewer on d76bee0..0b08a6b -> docs/reviews/phase6_viewer_gate4_r5_review.md; export engineer resumed (global range + mist); viewer engineer continues with item 2 impostors, then item 6 (no perf numbers while the GPU renders). Next: QA 13 verdict; merge phase6-viewer after review; env.glb re-sync -> viewer hooks vertex irradiance + mist; Gate 4 capture.

## 2026-09-16 · Export r3 in (phase6-export 05967b5): global COLOR_0 range 43.32 (worst 16-bit rel_p99 0.92 %, gate 2 %), mist read from master_delivery (start 20 m, depth 2000 m, LINEAR); env.glb synced
manifest_v4.py's new keys (lightmaps.vertex_irradiance.range, compositor.mist) need main's gate2 outputs, so they land after the merge; review of ed00a62..05967b5 dispatched -> docs/reviews/phase6_export_gate3_r3_review.md. Viewer engineer told the numbers and key names. Cycles refs for 03/05/06 still rendering (pid 28283).
Next: merge export r3 -> run manifest_v4.py + sync from main -> message viewer; QA 13 verdict; viewer review verdict.

## 2026-09-16 · Viewer round 5 review in (882b908): MERGE WITH FIXES (3 one-line fix now, 9 carry); UV dequant fix proved sound (transform read from the glb, applied once, idempotent)
Fix now: hero_boxes.py hard-coded MAIN path; empty `?post=` enables the whole chain incl. the placeholder mist; two gate3_test.mjs checks became tautologies. Carries incl. ~58 MB full-res PNGs under renders/web against the 960 px rule — viewer told to commit 960 px copies only and drop the one-shot A/B frames. Gate 2 carries 5 (export-owned), 10, 11 still open.
Next: viewer fixes land with the item 2 (impostor) report -> merge phase6-viewer; export r3 review -> merge; QA 13 verdict; Cycles refs.

## 2026-09-16 · Export r3 review in (ba27a1a): MERGE WITH FIXES (2 fix now, 7 carry); export engineer resumed
Fix now: checks validate carried-over glbs against regenerated .gltf (fail on stale glb, re-pack or prove equality); manifest_v4.py reads mist_settings.json local-only (resolve local-then-MAIN; the file is in MAIN today). Carry for the viewer's item 4: compositor.mist omits the airlight cap/k, so a plain linear fog would be ~5x off near the camera — the viewer must read the compositor block's mapping, not just start/depth.
Next: merge export r3 on the fix report, manifest_v4.py + sync from main, message viewer; QA 13; viewer item 2 + fixes -> merge; Cycles refs (still rendering).

## 2026-09-16 · phase6-export r3 MERGED (14eadad) with the 2 review fixes (77063c6): re-pack of all four glbs byte-identical, stale-glb pins in both checkers, mist path local-then-MAIN
Lead ran manifest_v4.py + sync from main: lightmaps.vertex_irradiance.range = 43.3198 (global), compositor.mist populated (start 20 m, depth 2000 m, LINEAR). Viewer engineer told; export side has nothing open except 5+7+8 carries in docs/reviews/phase6_export_gate3*_review.md.
In flight: QA 13 (round13b), viewer item 2 + 3 fixes, Cycles refs 03/05/06 (pid 28283). Next: QA 13 verdict; merge phase6-viewer on its report; Gate 4 capture.

## 2026-09-16 · Viewer item 2 in (phase6-viewer 08e9262, fixes 827a563): 127 far-tree impostors live (16 draw calls, 16/16 atlases), placeholders gone; NEW defect: MAT_leaf_* have no alphaMode -> opaque leaf cards (export-owned)
Impostor atlases are KTXorientation rd while the manifest counts rows from the bottom (drew the back sides deep blue until V-flipped; measured codes [0.253 0.291 0.487] -> [0.425 0.430 0.281]). cam01 luma 136.0 -> 127.3 (Cycles 140.0; the impostors read paler/flatter than Cycles foliage, inherent at 85 px frames drawn at ~40 px), cam02 110.9 -> 107.0 (Cycles 102.1). Vertex irradiance live (global range). renders/web tracked 102 -> 74 MB, .gitignore refuses full-res captures.
Lead: export engineer resumed for alphaMode MASK on the leaf materials (cutoff read from master_delivery, not guessed); reviewer on 0b08a6b..08e9262 -> docs/reviews/phase6_viewer_gate4_r5b_review.md; viewer continues with compositor.mist mapping then the manifest range source. Cycles refs: cam03 saved (~19 min); the lead's first run was stopped by hand at 22 min (would have hit its 2400 s watchdog mid-cam05) and cams 05/06 relaunched with 3000 s (pid 31668, renders/logs/qa_r13_cycles_refs_b.log). Next: QA 13 verdict; merge phase6-viewer on the r5b review; env.glb leaf fix -> re-sync; Gate 4 capture.

## 2026-09-16 · QA round 13 in (f8c9002): LIGHTMAPS ACCEPTED, one re-bake (ARCH_rotunda_plaster_ceiling_merged, QA-13-2); hero 135.99 vs 139.98 (0.971x), MAE down at all six stations
Scores 01 3.39 · 02 2.69 · 03 2.69 · 04 2.31 · 05 2.89 · 06 2.33 (all inside the 0.5 window; 04/06 below the 2.5 floor). New QA-13-1: saturated blue bays on the N-colonnade (23 % of the band B > R+20, bit-identical with lightmaps off -> a surface lit by neither path; viewer/export to identify). QA-12b-1 olive cast not closed and worse at cam02 (19.7 %); sunlit-attic sat hold broke (0.89x). No seam, slot bleed, blockiness, banding or double shadow at 100 %. Budget/perf PASS (1 678 MB at 1440p, GPU 2.3 ms).
Lead: refs 02/04 chained after 05/06 (QA: the round-09 cam02 reference predates the shade-fill-off; only station 1 had a reference from the baked lighting); rebake brief written (docs/briefs/phase6_gate3_rebake_ceiling.md), bake agent dispatched when the GPU frees; viewer engineer told to identify QA-13-1 and decompose the olive pixel. Next: r5b review -> merge viewer; env.glb leaf fix; rebake; Gate 4 capture + QA 14 against the new references.

## 2026-09-16 · Bake agent dispatched (phase6-bake, docs/briefs/phase6_gate3_rebake_ceiling.md): CPU prep now, the Cycles bake held until the lead's reference renders finish
Agents live: viewer (mist/range hookup, QA-13-1 + olive diagnosis), export (leaf alphaMode MASK), bake (ceiling relay), reviewer (viewer r5b). GPU: refs 05/06 rendering, 02/04 chained (logs renders/logs/qa_r13_cycles_refs_b/_c.log).
Next: merge viewer on r5b; env.glb leaf fix re-sync; bake go-signal when qa_render_round exits; Gate 4 capture + QA 14 vs round13_0N_cycles references.

## 2026-09-16 · Viewer diagnoses in (phase6-viewer 1b7ad84; mist + range hookups 8628736): QA-13-1 = backdrop blocks under the diffuse PMREM (viewer fixes via the direct path); QA-12b-1 mechanism disputed, re-measure with post on + bake-scene check
Viewer told: backdrop/unpatched surfaces onto the direct path; re-measure olive at cam02/06 with ?post=all. Bake agent told: read-only check of the bake scene's bounce materials, gallery fills, world, bounces. Tooling: __pfaPick pixel raycast (note: three's Raycaster does not skip invisible objects). renders/web tracked 44.9 MB.
Waiting: r5b review -> merge viewer; export leaf fix; refs 05/06 then 02/04; bake step 1. Next: bake go-signal at GPU free; Gate 4 capture + QA 14.

## 2026-09-16 · Export leaf alpha in (phase6-export 35865b8): 8 env card materials alphaMode MASK @ 0.5 (read from master_delivery: alpha_threshold under HASHED; the leaf materials route through a node group, which is why the defect survived), synced
verify_glb asserts MASK/BLEND + effective cutoff on every alpha-carrying base colour texture; the stale-glb pin now forces a full re-pack (toktx 258 s) whenever the glTFs regenerate. Review of 77063c6..35865b8 dispatched -> docs/reviews/phase6_export_gate3_r4_review.md; viewer told to re-sync and confirm cam02.
Next: merge export r4 on review; r5b review -> merge viewer; refs; bake step 1; Gate 4 capture + QA 14.

## 2026-09-16 · Viewer r5b review in (18f2e19/6f75281): MERGE WITH FIXES (3 fix now, 9 carry); impostor V flip confirmed correct; barycentric weights swapped (real blend bug)
Fix now routed to the viewer: swapped upper-triangle weights (re-capture cam01/02 after), silent NaN fallbacks in the impostor manifest block, stale README lines; PFA_DEV_SHARE_GPU logged in decisions.md. Refs: 05 saved, 06 rendering, 02/04 chained.
Next: viewer fixes + measurements -> merge phase6-viewer; export r4 review -> merge; bake step 1; GPU-free signal; Gate 4 capture + QA 14.

## 2026-09-16 · Cycles references 03/05/06 done (renders/previews/qa/round13_0N_*_cycles.png, 1920x1080 128 spp, compositor on; 05+06 in 950 s); 02/04 rendering (pid 34504, max 3000 s)
GPU still busy until 02/04 finish (~30 min); bake go-signal and the viewer's --perf after that.

## 2026-09-16 · phase6-viewer MERGED (0458150, through 8d76e7d: r5b fixes d4a9b57 + measurements); QA-13-1 direct-path fix withdrawn on evidence, probe irradiance authorised for unlit-mapped surfaces
Measurements: band B > R+20 17.6 % -> 15.5 % with post (target ≤ 3.9 %); olive cam02 46.5 -> 32.2 % with post (viewer mask), cam06 21.2 %. Leaf cards cut out after the alphaMode re-sync but stay blue (same sky-only path). Impostor rotational pop still unswept (re-check on the corrected-weights re-capture).
Waiting: export r4 review -> merge; bake step 1 + scene check; refs 02/04 (pid 34504) -> GPU-free signal to bake and viewer. Next: probe irradiance measurement; ceiling bake; Gate 4 capture + QA 14.

## 2026-09-16 · Export r4 review in (677b792): MERGE WITH FIXES — the alpha cutoff was read from the inert alpha_threshold; the real cut is mat_build's map_range chain (cypress 0.45, pine 0.42, others 0.5); export engineer resumed
Fix: read_alpha walks the Mix Shader -> Map Range chain in master_delivery.blend, gltf_gate1 cross-checks against it, verify_glb checks non-default cutoffs survive gltfpack; the silent png_has_alpha None skip becomes a failure. Merge of phase6-export r4 waits on this fix.
GPU: 02/04 refs rendering (pid 34504). Waiting: bake step 1 + scene check; viewer probe irradiance.

## 2026-09-16 · Bake step 1 in (phase6-bake d0c2c28): ceiling defect = 100 % inverted normals (UV2 fine, 60.6 % of the map, 1.53 cm/texel); flipped-winding re-bake ready, held for the GPU. Bake scene audit: identical to the Cycles rig (QA-12b-1 not in the bake scene)
Lead queued a light-path branch test (debug world: camera red / glossy blue / diffuse green; bake vs 160x90 render) after the ceiling bake to test whether bake rays miss the sky's warm diffuse-branch tint. Waiting: export cutoff fix -> merge; refs 02/04 (pid 34504) -> GPU-free to bake first, then the viewer's --perf; viewer probe irradiance.

## 2026-09-16 · QA-13-1 closed (phase6-viewer c79b7b6, probe irradiance): band 0.2 %, cam02 foliage hue 220° -> 41° (amber-brown vs Cycles olive: held for the branch test); refs repointed (cam06 real 0.71x)
Viewer: commit repointed refs, prepare the one-command Gate 4 capture, sweep impostor rotational pop; --perf still held. GPU: refs 02/04 at ~7 min (pid 34504); then bake (ceiling + branch test), then viewer --perf, then Gate 4 capture + QA 14.

## 2026-09-16 · Bake staged (phase6-bake 7ed1bdb): ceiling bake + sky-branch probe (debug world R=camera / G=diffuse / B=glossy; bake vs render) held for the GPU; precedent found — Phase 5's Eevee probe capture had the same camera-branch defect and light_probes.bake fixes it with make_sky_world(split_rays=False)
sky.diffuse is confirmed the tinted branch (bake_lm.py isolates Is Diffuse Ray). If the probe confirms, the fix is a full Gate 3 lightmap re-bake with the corrected world (65 jobs, 6 h 30 m overnight last time); the bake engineer prepares the queue but does not start it — lead decides the overnight slot. Gate 4 capture + QA 14 proceed on the current maps for everything except QA-12b-1.
GPU: refs 02/04 (pid 34504, ~9 min). Waiting: export cutoff fix; viewer capture prep + pop sweep.

## 2026-09-16 · phase6-export r4 MERGED (cb4de91, through 0ba4cb8): cutoffs from the real Mix Shader -> Map Range chain (cypress 0.45, pine 0.42 in the glb as float32), png_has_alpha raises on unknown formats; verify_glb PASS from main
Export side closed for Gate 4 (carries in docs/reviews/phase6_export_gate3*_review.md). Viewer told to re-sync. GPU: refs cam04 rendering (pid 34504).

## 2026-09-16 · Staged for the GPU: bake (ceiling as staged, then the sky-branch probe; corrected 47-job queue prepared behind PFA_BAKE_DIFFUSE_WORLD=1, ~6 h 15 m, NOT started) and viewer (gate4.sh one-command delivery capture; impostor rotational pop PASS, 61 frames at 1°, max/median 1.21x)
Viewer 3a84e3f/2e28ade: refs repointed + "QA notes — read before scoring" in web/README.md (cam06 0.71x real, probe override, foliage held). Bake 6a0ec47: only the 47 bake-target jobs are affected by the branch (sky/probe/impostor jobs already correct).
Next: cam04 ref -> GPU-free to bake -> probe verdict -> encode/pack -> manifest + sync -> viewer --perf + Gate 4 capture -> QA 14; overnight re-bake decision on the probe numbers.

## 2026-09-16 · Cycles references complete: round13_02..06 on main (compositor on, 128 spp). GPU handed to the bake engineer (ceiling bake -> sky-branch probe -> encode/pack)
Viewer's --perf and Gate 4 capture follow the bake report. QA 14 (docs/briefs/qa_round_14.md) after the capture.

## 2026-09-16 · Viewer ready for the GPU (phase6-viewer bbe1d7b): refs 2-6 repointed (cam02 1.10x, cam04 0.95x on round13b; cam02 1.01x with the Gate 4 look), item 6 frame-breakdown instrumentation, 173 tests green
Order on the bake's GPU-done signal: re-sync -> --perf + --breakdown -> gate4.sh capture -> QA 14. Bake engineer running the ceiling bake + sky-branch probe now.

## 2026-09-16 · Item 6 measured (phase6-viewer 184d785): 31-34 fps at stations 1-3/5/6, 45 at 4; vsync quantisation (Reflector 6-9 ms + bloom 8 ms push a 17 ms frame past one interval). Lead: half-res bloom + half-res Reflector, box-checked (<= 0.03x)
Resident 1 678 MB (tex 1 172, RT 444). Viewer applies the levers now (GPU free; bake on CPU encode/pack); Gate 4 capture after the manifest signal.

## 2026-09-16 · Bake r2 in (phase6-bake 73d5bb0, synced): ceiling map fixed (0.72 -> 16.76 max, 30.7 % non-zero); sky-branch hypothesis REFUTED (bake [0,1,0] = diffuse branch); NO overnight re-bake
Lead ran manifest_v4.py + sync: ceiling range 16.755 in the manifest (the stale 0.721 would have decoded the new map 23x too dark). Reviewer dispatched on main..phase6-bake -> docs/reviews/phase6_bake_gate3_r2_review.md. Viewer: re-sync, probe-as-specular A/B for QA-12b-1 (ship only if G > R drops and boxes hold), then gate4.sh -> "round14".
Next: merge bake on review; QA 14 on round14; QA-12b-1 remaining candidates per decisions.md.

## 2026-09-16 · Bake r2 review in (8c7b616): MERGE WITH FIXES (3 fix now: env-arming parse, README/tech_notes docs, stale worktree manifest; 9 carry); bake engineer resumed
Merge of phase6-bake follows the fix commit. Viewer: half-res levers, probe-as-specular A/B, then round14.

## 2026-09-16 · phase6-bake r2 MERGED with the 3 review fixes (88a9d6b): env_armed() strict parse, README + tech_notes "Bake-side traps", stale worktree manifest removed. MAIN manifest ceiling range 16.755 confirmed
All three Phase 6 branches merged and in sync with main. Waiting on the viewer: half-res levers + probe-as-specular A/B -> round14 capture -> QA 14.

## 2026-09-16 · round14 CAPTURED (phase6-viewer 1cc73fd; A/Bs b12670a): Gate 4 look on the re-baked ceiling. Whole-frame vs reference: 01 0.92x · 02 1.01x · 03 1.67x · 04 1.11x · 05 1.04x · 06 0.75x; post-off control 0.85/0.97/1.80/1.12/0.98/0.43
Not shipped: half-res bloom/Reflector (only ~4 of the ~12 ms needed; the Reflector's cost is its second scene traversal at 314 draws, not fill; each lever also moved a box: water R-B 0.943x, sunlit attic std 1.035x) and probe-as-specular (G > R cam02 21.7 -> 17.2 % but cam01 boxes moved 1.2-1.5x). Perf everything on: 28.9 ms (34.6 fps), 1 678 MB. Walk: 24 probes, zero in the lagoon. Artefacts: renders/web/round14_cam01..06.png (untracked full-res, 960 px copies tracked), pair sheets, tiles/round14/, round14_perf.json, round14_walk.json, 960/round14_loading_screen.jpg — all in the phase6-viewer worktree.
Dispatched: QA 14 (Opus xhigh, docs/briefs/qa_round_14.md) on round14; viewer engineer on the Reflector draw set (item 6). Open: cam03 1.67x, cam06 0.75x, QA-12b-1, 45 fps.

## 2026-09-16 · Item 6 closed as measured (phase6-viewer 7007645): reflset=orn default (−2 ms, boxes hold); 45 fps needs both the Reflector and bloom off -> default keeps the look, `?quality=fast` preset added for the user's choice
QA 14 running. Waiting: QA verdict; viewer's fast-preset table.

## 2026-09-16 · Fast preset measured (phase6-viewer 2d267ba): look 30.6-45.5 fps vs fast 36.4-49.3 fps at 1440p; 30/32 cam01 boxes within 0.03x (water R-B 0.953x worse, sunlit attic std 1.035x better). Neither reaches 45 fps except station 4. Default = look
Waiting: QA 14 verdict. Then: merge phase6-viewer; Gate 4 decision; burn log.

## 2026-09-16 · QA 14 in (cc14323): ONE MORE ROUND, no blocker; all 6a parity criteria PASS (thin: 03/06 at 2.56), 45 fps not met. Lead: one bounded round 15 (water, bloom, cam06/cam03, minors) then QA 15 + Fable final
Viewer round 6 brief: docs/briefs/phase6_gate4_r6_viewer.md. Reviewer dispatched on phase6-viewer 8d76e7d..2d267ba (probe irradiance, refs, fast preset, reflset) -> docs/reviews/phase6_viewer_gate4_r6_review.md, merge after.

## 2026-09-16 · Viewer pre-merge review (5d034d6): MERGE BLOCKED — probe cube never uploaded (black envMap); QA-13-1 closure withdrawn pending re-measure; 6 further fix-now (capture fails on page errors, orbit/pick layers, slot-atlas fallback, quality case, README notes)
Viewer told to stop round 6 work, fix, re-run the probe A/Bs with the real cube, report, then resume the round 6 brief and capture round15. phase6-viewer stays unmerged until the re-review. QA 15 brief on file (docs/briefs/qa_round_15.md).

## 2026-09-16 · Probe fixes + re-measure in (phase6-viewer 1e9d2be, 82d44c5): all 7 fix-now closed; QA-13-1 still closed (0.29 %); probe worsens cam02 olive (41.7 %); foliage cyan -> vertex irradiance for shrubs/reeds dispatched (bake -> export -> viewer); water rebuild authorised
Viewer continues round 6 items 1-4 (water rebuild first), round15 capture after the foliage env.glb lands; no interim merge (re-review after round 15). Bake engineer: vertex jobs for the card meshes (Chrome paused during the bake window). Export engineer: env re-export with the new COLOR_0 set after the bake.
Lead context 300k: CHECKPOINT below if the session must restart.

## 2026-09-16 · CHECKPOINT (session 3, lead context ~300k; written while round 15 is in flight so a restart can resume)
State of record: main at fcaf606 + this entry. MERGED this session: phase6-export (r2 584a79d, r3 14eadad, r4 cb4de91 — UV2 relay, COLOR_0 global range, 988 placements, mist, leaf alphaMode with true cutoffs), phase6-bake (r2 267c69e — ceiling flipped-winding re-bake, sky-branch probe refuted, unarmed corrected-world switch), phase6-viewer through 8d76e7d (0458150 — UV dequantisation, impostors, mist, walk, items 1-3+5). UNMERGED: phase6-viewer 8d76e7d..HEAD (probe irradiance, refs, presets, reflset, 7 review fixes at 1e9d2be, round 6 water work) — pre-merge review 5d034d6 said MERGE BLOCKED before the fixes; a re-review is required before merging. Cycles references round13_02..06 on main. QA 13 (f8c9002) LIGHTMAPS ACCEPTED; QA 14 (cc14323) ONE MORE ROUND, all 6a parity criteria PASS (thin), 45 fps not met (34.6 fps; decisions.md: default keeps the look, ?quality=fast documented).
In flight at this checkpoint: viewer engineer on docs/briefs/phase6_gate4_r6_viewer.md (water rebuild -> bloom -> cam06/cam03 -> minors -> round15 capture after the foliage env.glb lands); bake engineer on vertex irradiance for the shrub/reed/card meshes (short GPU job; Chrome pauses during it); export engineer to re-export env.glb with the new COLOR_0 set after that bake (not yet told — resume step 2).
Resume procedure (fresh agents; briefs on file): (1) `pgrep -fl "MacOS/Blender|chrome"` empty; read the three worktrees' last commits and `git status`. (2) If the vertex npz for the card meshes is in MAIN export/out/gate3 (check compose.json/the relay json and the bake branch's last commit): dispatch a fresh export engineer on docs/briefs/phase6_gate3_export.md with a new "Resume r5" addendum = re-export env.glb with COLOR_0 for the new mesh set (same global-range gamma-2 encode, relay json vertex block extended), verify_glb, sync; lead runs `python3 export/manifest_v4.py && export/sync_main.sh`; merge phase6-bake and phase6-export after a read-only review each. (3) Viewer: fresh engineer from the worktree HEAD on the round 6 brief's remaining items, then round15 capture (gate4.sh, name "round15"). (4) Code review of phase6-viewer 8d76e7d..HEAD (docs/reviews/phase6_viewer_gate4_r7_review.md) -> merge. (5) QA 15 (Opus xhigh, docs/briefs/qa_round_15.md) on round15. (6) The single Fable final judgement of 6a (lead: six-station 100 % tile pass on round15 + the QA 15 report), then close 6a in docs/decisions.md and docs/delivery.md (Phase 6 section), log burn (`python3 docs/usage/usage_from_transcripts.py`). (7) 6b (web deployment) is a new plan: docs/briefs/phase6_plan.md Gate 5; user names the iPhone.
Burn so far today (list rates): session 6460c313 $586.08 (overnight bake, spanned the 15th/16th), session 2 $46.70, session 3 (87d95e57) $209.06 to 15:26 (Opus 191, Fable 18; 12 subagents) — re-run the script at the next start for the final figure. Phase 6 to date ≈ $845 nominal.

## 2026-09-16 · SESSION 3 CLOSES (user closing the machine; lead context 317k). Stop state — supersedes the checkpoint's "in flight" line
All three agents told to commit WIP and stop. At the stop check: no Blender running; phase6-bake clean at fcaf606 (main merged in, the shrub/reed vertex-irradiance job NOT started — nothing baked, nothing to resume mid-way; re-dispatch it fresh from the message text recorded in decisions.md "Probe re-measured on the real cube" + the checkpoint's step 2); phase6-export clean at 0ba4cb8 (fully merged, nothing open); phase6-viewer at 82d44c5 + a WIP commit of the water rebuild (two files; read its commit message for the exact state: every new water term is opt-in, the default reproduces round14). One headless Chrome (the viewer's) was alive at the check; if `pgrep -fl chrome` still shows a `--headless` Chrome at the next start, kill it.
Next session = the checkpoint's Resume procedure steps (1)-(7) above, with these corrections: step (2) begins with a FRESH bake engineer running the vertex-irradiance job (brief text: decisions.md entry + checkpoint), then the export re-export; step (3) the fresh viewer engineer starts from the WIP commit on the round 6 brief item 1 (water: anisotropic ripple + horizon-stretched lobe, judged on a 100 % tile), then items 2-5; the pre-merge review 5d034d6's seven fix-now items are closed at 1e9d2be (verify in the re-review). Run the burn script first and log it.
Addendum at close: bake engineer stopped at 67f4e90, nothing baked; the shrub/reed job needs the granularity decision — taken in decisions.md: PER PLACEMENT (1 379 RGB values, new manifest block lightmaps.instance_irradiance, viewer per-instance attribute). Next session dispatches the fresh bake engineer with that entry; resume command in its report: `git merge main && python3 export/gate3_env_cards.py` in the bake worktree.
Final at close: viewer WIP committed at 2dab197 (tree clean, no Chrome): anisotropic crests + grazing lobe ON by default (rowHF 0.97 -> 4.60, streaks 0.72 -> 2.23; level/hue/sat still failing; `?watergraze=0` reverts to round14); the water now receives the compositor airlight. Its one next step, for the fresh viewer engineer: raise the murk to the reference sheet's MAT_water_lagoon value (muddy bottom 0.12/0.10/0.06 under 1.5 m of 0.04/0.07/0.04 absorption — current murk ~5x too dark, ~10x too saturated), then the lead judges renders/web/960/qa14_1_openwater_100pct.png before items 2-5. Bake 67f4e90 clean, export 0ba4cb8 clean, main 60e5022 + this line. No Blender, no Chrome. Safe to close.

## 2026-09-16 · SESSION 4 OPENS (lead, Fable). Burn logged; resume from the stop state
Burn (list rates, `docs/usage/usage_from_transcripts.py`): session 3 (87d95e57) final $217.93 (Opus 199, Fable 19; 12 subagents); Phase 6 to date $850.71 nominal (586.08 + 46.70 + 217.93); project grand total $2,350.13.
Start check: no Blender, no headless Chrome; bake 67f4e90 clean, export 0ba4cb8 clean, viewer 2dab197 clean (WIP already committed), main 12f3084. Briefs written: docs/briefs/phase6_gate4_bake_instance_irradiance.md (fresh bake engineer, per-placement irradiance), the "Resume" addendum in docs/briefs/phase6_gate4_r6_viewer.md (fresh viewer engineer: murk from the reference sheet, then the open-water tile for the lead's judgement), "Resume r5" in docs/briefs/phase6_gate3_export.md (export, after the bake).
Dispatching bake (Opus xhigh) and viewer (Opus high) now; export waits for the bake report; then review + merge of phase6-viewer, QA 15, the Fable final judgement of 6a.
Dispatched (session 4, in flight): bake engineer on docs/briefs/phase6_gate4_bake_instance_irradiance.md (phase6-bake); viewer engineer on the Resume section of phase6_gate4_r6_viewer.md, item 1a-1b only, stops for the lead's tile judgement (phase6-viewer); code reviewer on phase6-viewer 8d76e7d..2dab197 -> docs/reviews/phase6_viewer_gate4_r7_review.md (main). Export r5 waits for the bake report.
Review r7 (f778a31): MERGE AFTER FIXES, all seven r6 fix-now items closed; two water fix-now items forwarded to the viewer engineer inside item 1; reflset=orn default authorised (decisions.md). A delta review of commits after 2dab197 is still needed before the merge.
Viewer 58fa59e: item 1a-1b done (derived murk, review fix-nows folded in); lead judged the open-water tile (decisions.md "Water tile judged"): new water is the default, one bounded ripple/reflSat pass, then items 2-5 and the round15 capture. Bake engineer still running the instance-irradiance job.
Bake aaab677 (phase6-bake): per-placement shrub/reed irradiance DONE — 1 379 placements, 28 meshes, 2 597 s GPU (1.88 s/placement, 4 chunks + a probe), keyed by object name, range_global 18.40, 7 enclosed placements legitimately zero; deviation: cards baked with an opaque stand-in material (cut-outs return 0 at transparent verts), rgb = mean over lit verts + cov. Synced to MAIN export/out/gate3/instance_irradiance.json. status.json idle.
Dispatched: export engineer on "Resume r5" (phase6-export, manifest block + verify_glb); reviewer on phase6-bake fcaf606..aaab677 -> docs/reviews/phase6_bake_gate4_instance_review.md. Viewer engineer on the bounded ripple pass then items 2-5. Next: merge bake + export after reviews, lead runs manifest_v4 + sync, viewer item 1c.
Bake review 7d59c5f: MERGE AFTER FIXES — the opaque/shadow-off override biased values +64 % and made them job-split dependent; names unrecoverable in the glb. Decision (decisions.md "Shrub/reed bake re-run"): re-bake with a shadow-ray-only override on every card, join by location; bake engineer resumed on it (~45 min GPU, status.json running); export engineer told to join by nearest translation and re-run when the JSON lands. Viewer codes during the bake.
Export r5 4f19d01 (phase6-export): join by transform done — 28/28 meshes, 1 379/1 379 rows over 25 instanced nodes, axis swap (x,y,z)->(x,z,-y) asserted at 0.6 mm, tol 0.03 m / worst residual 5.7 mm / margin 69x; gltfpack merged three .001 meshes into their base node (nodes 10/16/21 hold 46/102/76 rows) so the manifest block carries per-node ordered (mesh,count) segments; env.glb untouched; manifest +106 kB (lead runs manifest_v4 after the re-baked JSON lands). Reviewer dispatched -> docs/reviews/phase6_export_gate4_r5_review.md.
Export review 72c470f: MERGE WITH FIXES (segments repeat a mesh inside a node -> per-segment offset needed; instance_order.json must be tied to its inputs; the env.gltf name-join harness could ship silently). Export engineer resumed on the three fix-nows. Bake re-run still on the GPU.
Export e0b32b6: all 11 review findings closed (segments [mesh,count,offset], join pinned by sha256 of the irradiance JSON + glb bytes, harness opt-in, 10/10 selftest); the join ran on the production loc path: 1 379/1 379, 28/28, 25 nodes, residual 5.9 mm, margin 55x. Ready to merge; the chain re-runs after the re-baked values land.
2026-09-17 · Bake f9feec3 MERGED into main (70f2418): shadow-ray override partition-independent (delta 0), old values up to 2x too bright, trees' COLOR_0 re-baked (coverage 0.20 -> 0.76). Export engineer resumed: COLOR_0 re-encode, re-dump rows, re-join, sync; then the lead runs manifest_v4 + sync and merges phase6-export. Viewer engineer still on the ripple pass / items 2-5.
Export 7cd0bbf MERGED (0f7e3ba); lead ran manifest_v4 + sync_main: export/out/gate3/manifest.json carries lightmaps.instance_irradiance (1 379 / 28 / 25 nodes, range 17.22), env.glb 38 119 568 B with the trees' re-encoded COLOR_0 (range 44.257). Viewer engineer told: item 1c after the ripple pass, then items 2-5 and the round15 capture. Bake and export trees are fully merged; only phase6-viewer is open.
Viewer 43b1e0a (phase6-viewer): round 7 complete — procedural 8-octave ripple (rowHF 6.92, row/col 3.71 vs ref 13.23/3.24; reflSat 0.66 was the warm drain, now 1.0: reflected-building lum 1.01x, hue within 3.3°), item 1c instance irradiance consumed (1 379/1 379, cam02 tree level 0.99x, cyan gone, hue 57.7 vs 102.4 = albedo, reported to bake/export as post-6a), bloom threshold 2x (capital-row std 0.85x, attic sat 0.88x), walk margin 0.15 m, loading 639/639 MB, round15 captured (luma 01 0.897x, 02 1.030x, 03 1.804x, 04 1.118x, 05 1.001x, 06 0.993x; MAE falls or holds on all six; 28.2 ms median at 1440p = 35.5 fps).
Dispatched: delta review 2dab197..43b1e0a -> docs/reviews/phase6_viewer_gate4_r7b_review.md; QA 15 (Opus xhigh) on docs/briefs/qa_round_15.md against the round15 capture in the viewer worktree. Next: merge phase6-viewer after the review, then the Fable final judgement of 6a.
Delta review r7b (089d172): MERGE AFTER FIXES — two one-line failure-path guards (ERR_ABORTED only for HEAD probes; the missing-node throw), sent to the viewer engineer; merge follows. Lead's own 100 % tile pass on round15 done (scratchpad notes; goes into the final judgement). QA 15 in flight.
