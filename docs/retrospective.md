# Retrospective — Palace of Fine Arts, attempt 3 (2026-09-10, after the v2 delivery)

Chief architect's review. Token and dollar figures come from `docs/usage/summary.md` and `docs/usage/sessions.json`
(list rates stated there; the account is on a subscription, so costs are nominal). Times are local (+02:00).
Inferred numbers are marked.

## 1. Outcome

**Success criterion ("hard to tell from a photograph"): not met.** The delivered hero scores **3.61 / 5** (round 10b,
scored at 100 % tiles). The brief asked 4.5 on the hero and 4 on every row; the user's definition of done asked 4.0. The
loop closed on the fallback rule (two rounds after the photo projection under +0.1), not on the score.

| Non-negotiable / deliverable | Status | Evidence |
|---|---|---|
| Real dimensions, never eyeballed | Met with one reversal: the sheet's 7.6 m dome rise was wrong, photos overrode it; the course stack was registered only at architecture r6 | decisions 09-07, 09-09 |
| No ornament identical twice | Partly: per-instance seed in the shader; hero Repetition row 3 | qa_round_09 |
| No flat / clean / plastic materials | Partly: hero Material realism 3.5, Edge wear 3.5; cam06 Edge wear 0.5 | qa_round_09 |
| Side-by-side for every claim | Met: gate composite every round, aligned overlays from round 2 | renders/qa_comparisons |
| Viewable file, mid LOD default | Met: 277.7 MB, opens 0.86 s, LOD1 11.5 M tris, Eevee 17-29 s per camera | delivery.md |
| Decisions logged | Met: docs/decisions.md, 240 lines | |
| 4K Cycles hero | Met: 3840x2160, 384 spp, 4207.8 s (v2) | renders/final/v2 |
| Flythrough path + Eevee test | Met: 1224 frames; 612-frame test, 640x360, 6970 s | delivery.md |
| Evening WNW alternate (promised Phase 0) | Not delivered (inferred: absent from delivery.md) | decisions 09-06 |

**Final scores per view** (round 9, all cameras; hero re-scored in 10b):

| cam01 hero | cam02 NE 3/4 | cam03 colonnade | cam04 ceiling | cam05 S lawn | cam06 aerial |
|---|---|---|---|---|---|
| 3.67 → **3.61** | 2.94 | 2.56 | 2.81 | 3.06 | 2.67 |

**Hero trajectory** (critic model, transcript cost):

| round | when | hero | delta | critic | note |
|---|---|---|---|---|---|
| 01 | 09-07 08:22 | 2.17 | — | Fable $6 | Phase 2 gate, placeholder materials |
| 02 | 09-07 17:17 | 2.94 | +0.78 | Opus $14 | Phase 3 gate, real materials |
| 03 | 09-07 20:49 | 3.28 | +0.34 | Fable $9 | watchdog killed three renders |
| 04 | 09-08 04:50 | 3.28 | 0.00 | Fable $13 | boxes traded, no net gain |
| 05 | 09-08 08:20 | 3.28 | 0.00 | Fable $8 | third flat round; method change |
| 06 | 09-09 14:19 | 3.22 | -0.06 | Opus $11 | attic storey found at 0.70x the photo |
| 07 | 09-09 17:54 | 3.44 | +0.22 | Opus $10 | first round with every view up |
| 08 | 09-09 23:33 | 3.67 | +0.22 | Opus $7 | after the photo projection |
| 09 | 09-10 01:10 | 3.67 | 0.00 | Opus $7 | gate rule fires, Phase 5 |
| 10 | 09-10 09:10 | 3.56 | -0.11 | Opus $5 | tile review FAIL |
| 10b | 09-10 10:31 | 3.61 | +0.05 | Opus $4 | tile review PASS, v2 |

## 2. Timeline

| row | when | wall h | in flight → merged / result | hero |
|---|---|---|---|---|
| Phase 0 | 09-06 13:35 | — | scaffold, common.py, QA cameras, briefs | — |
| API limit | 09-06 14:30 | 0.9 | 4 Fable research agents paused to the 18:30 reset | — |
| Phase 1 gate | 09-06 20:43 | 6.2 | reference sheet accepted; 5 Fable builders launched 20:53 | — |
| Phase 2 gate, QA r1 | 09-07 08:22 | 11.7 | builders ran 12 h overnight ($153); first master, 20 defects | 2.17 |
| Restart 1 | 09-07 14:47→15:04 | 6.4 | session 1 ends after 26 h; materials merged, Phase 3 | |
| QA r2 (Phase 3 gate) | 09-07 17:17 | 2.2 | 10 Opus fix/polish agents merged | 2.94 |
| Restart 2 | 09-07 19:32→20:11 | 2.3 | session 2 ends after 4.5 h | |
| QA r3 | 09-07 20:49 | 0.6 | polish round 1; watchdog kills, fixed 22:41 | 3.28 |
| Checkpoint | 09-07 22:40 | 1.9 | user closes the machine; same session resumed ~00:15 | |
| QA r4 | 09-08 04:50 | 6.2 | LIGHT r09/r10, ARCH p4r2, MAT r4/r5, ENV r4/r5, ORN r4 | 3.28 |
| QA r5 | 09-08 08:20 | 3.5 | LIGHT r11, MAT r6, ENV r6; shade declared structural | 3.28 |
| Restart 3 | 09-08 09:56→09-09 07:42 | 21.8 | 4K timing killed at 94 min, no frame; new rules on resume | |
| QA r6 | 09-09 14:19 | 6.6 | LIGHT r12/r13, ARCH r4, MAT r7, ENV r7/r8 | 3.22 |
| QA r7 | 09-09 17:54 | 3.6 | ARCH r6/r7 (stack), ORN r6/r7, LIGHT r14, MAT r8, ENV r9 | 3.44 |
| Restart 4 | 09-09 19:38 | 1.7 | deliberate restart, lead context 384k | |
| QA r8 | 09-09 23:33 | 3.9 | LIGHT r15, MAT r9/r9b projection, ORN r8 | 3.67 |
| QA r9, Phase 5 | 09-10 01:10 | 1.6 | LIGHT r16; gate rule, Phase 5 starts | 3.67 |
| v1 hero | 09-10 05:12 | 4.0 | flythrough cut at 7200 s; resume wiped 1021 frames | |
| User defect | 09-10 06:32 | 1.3 | main arch filled by chord triangles; v1 archived; 3 gate checks | |
| QA r10 / r10b | 09-10 09:10 / 10:31 | 2.6 / 1.4 | ARCH r8, LIGHT r17/r18; tile FAIL then PASS | 3.56 / 3.61 |
| v2 delivered | 09-10 13:39 | 3.1 | 4K hero, flythrough test, delivery notes | 3.61 |

**Restart cost in re-cached tokens** (lead thread's cache writes in its first 15 minutes): 84k, 53k, 84k, 99k, and 137k
for this session. Under $3 each at the Fable 1-hour write rate, about $8 in total. Restarts were cheap; the 21.8 h gap and
the killed 94-minute render were the real losses.

## 3. Resources

**Tokens by model** (`summary.md`, deduplicated by message id):

| model | requests | output | cache write | cache read | cost |
|---|---|---|---|---|---|
| Opus 5 | 7,634 | 4.66 M | 49.7 M | 1,268 M | $1,061 |
| Fable 5.1 | 1,393 | 1.46 M | 17.2 M | 308 M | $407 |
| Sonnet 5 | 25 | 25 k | 0.1 M | 1.9 M | $1 |
| **total** | 9,052 | 6.14 M | 67.0 M | 1,578 M | **$1,469** |

Cross-checks: Claude Code's internal tally in the transcripts sums to $1,766 (its own price table, plus Haiku side calls);
ccusage's account-wide 09-06..09-10 total is $1,602 (`daily.json`). Cache reads are 96 % of all tokens.

**By session:**

| session | local span | wall h | lead | subagents | total | agents |
|---|---|---|---|---|---|---|
| 1 | 09-06 12:41 → 09-07 14:47 | 26.1 | $33 | $182 | $214 | 10, all Fable |
| 2 | 09-07 15:04 → 19:32 | 4.5 | $16 | $265 | $282 | 11 Opus |
| 3 | 09-07 20:11 → 09-08 09:56 | 13.7 | $48 | $415 | $463 | 30 (3 Fable QA) |
| 4 | 09-09 07:42 → 19:38 | 11.9 | $37 | $266 | $303 | 40 Opus |
| 5 | 09-09 19:38 → 09-10 14:10 | 18.5 | $60 | $145 | $205 | 23 (1 Sonnet) |

**Agents by role** (114): research 4 ($24), architecture 12 ($126), ornament 9 ($126), materials 11 ($217), environment 12
($299), lighting 15 ($314), QA critic 11 ($93), code review 38 ($66), Phase 5 prep 2 ($6). The lead thread cost $200
(14 %). The most expensive single agent: session 2's environment fix agent, $103 in 84 minutes.

**Rendering time.** 16.7 h summed over 52 Blender logs in renders/logs (file birth to last write, wrappers excluded); a
lower bound, since builders' renders logged in their worktrees. Phase 5 alone 9.2 h (4K probes 1432 + 649 s, v1 hero
4187 s, v2 hero 4208 s, flythrough runs 7204 + 4189 + 4142 + 6970 s). Claude Code's tool-time counter: 35.2 h (upper bound).

**Kill-and-resume events:** API limit 09-06 14:30; four restarts above; watchdog v1 killed three live renders 09-07
20:23; 4K 768-spp render killed at the 09-08 checkpoint after 94 min; flythrough cut at 7200 s and its resume wiped 1021
frames 09-10 04:00; flythrough chain 2 killed after the arch defect 09-10 06:30.

## 4. What worked

- **Photos override the sheet.** QA-01-1 measured the dome against five photos and the lead arbitrated the same day
  (decisions 09-07). Hero Silhouette went 3 → 4; the apex has sat within 0.44 % of frame height since round 7.
- **Numeric boxes with windows** from round 3. They made the round-5 diagnosis possible: shade starved by the rig
  (diffuse sky x0.8 vs camera sky x2.1 / lagoon x5.25), so a method change instead of a fourth knob round.
- **Lighting and materials sequential on the merged master** (decisions 09-08). Round 7 was the first with no passing box
  lost and every view up (+0.22 hero).
- **Register the stack, then project** (decisions 09-09). Architecture r6 put every course within 5 rows of ref 169; the
  projection landed seamless in round 8 (+0.22).
- **Code review before merge.** 38 reviews for $66 (4.5 % of spend); session 4 carried 16 reviews and 8 no-render fix
  rounds for $266, the cheapest merged round of the project.
- **status.md as the handoff.** Four restarts, one across a 21.8 h gap, resumed without loss at under $3 of re-caching each.
- **The definition-of-done rule** closed the loop at round 9 as written, and the user's tile check found and fixed the arch
  in 3.5 h for about $55 (ARCH r8 $8, LIGHT r17/r18 $36, QA r10/10b $9).

## 5. What went wrong

**The arch block that survived to v1.** Root cause: a round-1 tessellation bug in `build_vault_coffers` (a flat rib plate
triangulated with holes, then bent onto the barrel: 67 chord faces of 7-11 m² per bay, all eight bays). Caught by the user
on the v1 4K after nine QA rounds. The process could not see it: every reviewer looked at a 960-px composite (the context
rule) and the boxes measured the chords as "soffit"; lighting r15/r16 tuned cam02's shade box on them. A 100 % crop of the
hero's central 400 px in every composite, or one ray cast per opening, would have caught it in round 1. Cost: the v1
finals (about 5.5 h GPU) plus the v2 chain (4.5 h GPU) and $55.

**Three rounds at 3.28** (09-07 20:49 → 09-08 08:20, 11.5 h, inside the $463 session). Root cause: knob rounds on a rig
whose shade was starved by design, and materials tuning noise into a "dirt decal" (QA-05-2, anisotropy 0.64 vs 4.07 in the
photo). Each round passed its own boxes and lost another: round 4 fixed attic chroma and put columns at 1.27x; round 5
fixed columns and dropped attic luminance to 0.88. Four owners in parallel merged untested combinations (QA-05-3). Caught by
QA-05's trend table and the 09-08 decision. Earlier catch: a rule that a hero delta under 0.1 forces a method change, and
the course registration (done at round 6, where it found the attic storey at 0.70x) done at round 2.

**QA critic on Fable.** Rounds 1, 3, 4, 5: $5.83 + $8.82 + $12.96 + $7.72 = $35; the seven Opus rounds $58, so $8.8 vs
$8.3 per round. The casting rule saved almost nothing per round; the Fable critic's fault was three identical scores while
$300 of builders ran between them. The expensive Fable work was the lead thread ($200) and session 1's builders ($153).

**Watchdog killing GPU renders.** v1 (09-07, after the user found 13 GB of idle Blender) inferred liveness from
integer-second CPU time; a Metal render sits in `synchronize()` at 0.3 s CPU per minute, so it killed QA's 128-spp hero at
330 s and two more, and round 3's Cycles frames were capped at 270 s (QA-03-1). Fixed that night (7c164d5), rewritten 09-09
to registered maximum durations. Third incident 09-10: the honest 7200 s cap cut the flythrough at 511/612 frames, then the
resume script cleared its own output directory (2.3 h GPU lost). Each time a proxy was guarded instead of the thing. The
ten-minute Cycles test under `--loop` that QA-03-1 asked for, run before deployment, would have caught v1.

**The five-Fable-agent first session.** Session 1 ran 26 h. The API limit hit at 14:30 with four research agents running;
the five Phase 2 builders launched at 20:53 on Fable and ran unattended for 12 h ($153: materials $44, ornament $41,
architecture $27, environment $22, lighting $18). Dollars were not the damage (one Opus fix agent later cost $103); the
damage was twelve hours of five agents building on an unvalidated socket contract (maiden sockets at the wrong height, LOD
copies at the origin, decisions 09-07) and the rib-plate bug above. A one-hour blockout gate with one architecture agent
would have caught the contract; limit awareness would have staggered the launch.

## 6. How to do this again with half the resources

Target about $700 and two working days for the same deliverables.

- **Collapse Phases 1-2 into one blockout day with two agents** (architecture, reference). Measure from photos with the
  silhouette tool from hour one. Gate the blockout on the aligned overlay and a ray cast per opening before anyone else
  starts.
- **Drop the agents that never moved the hero.** Ornament r5/r7/r8 (no-render verify rounds) left the archivolt sockets
  empty; environment spent $299 over 12 agents and the shoreline is still known issue 4; lighting rounds 10, 11, 13, 16
  were knob rounds. One agent per owner per round, five rounds at most, lighting and materials never in the same round.
- **Lead on Opus**, Fable once for the final judgement. The lead thread was $200, mostly cache reads of status and reports.
- **The rubric on day one** must carry what it only had by round 10: numeric windows per region, aligned overlay with
  per-course registration, the 100 % six-tile hero pass, a ray cast per opening, the name sweep, a no-regression rule, the
  trend table, and "hero delta under 0.1 forces a method change".
- **One person, by hand, 15 minutes per gate:** pick the camera stations (four rounds went to cam02/cam05 searches), look at
  the hero at 100 %, read the composite. The 960-px rule saved context and cost the arch.
- **Render plan.** Every round: Eevee 1280x720 at LOD1 (20-30 s per camera). Gate rounds only: one Cycles 1920x1080 hero at
  64 spp (about 380 s). 4K twice: 128 spp fixed to time it (1432 s), then the final at what the timing allows (384 spp,
  4200 s). Never adaptive at 4K. Flythrough test every fourth frame (306 frames, about 1 h).
- **Keep:** reviews before merge, status.md handoff, registered-duration watchdog, sequential lighting/materials.
  **Drop:** four-owner parallel waves, briefs over 60 lines, re-viewing composites already judged.

## 7. Next three improvements, by visible gain per machine hour

1. **Hero mirror level** (QA-09-2): the lagoon reflects the building at 0.61 of its sunlit stone vs 0.87 in the photo, the
   largest area in the frame. Materials, grazing lobe; one 1080p Cycles hero to verify (380 s). Expected: Water reflection
   3 → 4, hero about +0.1.
2. **Neutral low-energy shade fill in place of the blue lamp** (QA-10b-1): with the lamp off the building reads 1.22x the
   photo's saturation and the shaded attic sits at hue 41 vs 30. Lighting, one 960x540 sweep plus one hero (under 15 min
   GPU). Expected: Material realism back to 3.5, hero about 3.7.
3. **Archivolt band and modillions on the eight empty sockets** (QA-09-3): the largest untextured surface at 1:1 in the
   hero's centre. Ornament instancing plus one LOD bake (about 30 min). Expected: Ornament fidelity 3.5 → 4.

The shoreline (QA-09-4, a hedge at 0.77 of the photo's luminance with no trunks) is next in visibility but needs tree
generation and a probe re-bake: lower gain per hour.
