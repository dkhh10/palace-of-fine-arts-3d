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
