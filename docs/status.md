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
