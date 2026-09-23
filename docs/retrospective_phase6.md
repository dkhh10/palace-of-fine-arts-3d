# Retrospective, Phase 6: from the delivered Blender model (2026-09-10) to the iPhone-ready web walkthrough (2026-09-15 to 2026-09-19)

Audit by the lead (Fable 5.1, session 6cfdbe19, 2026-09-21), read-only on branch `analysis/retro`. Every number below is produced by a
committed script: `docs/usage/usage_from_transcripts.py --turns` (per-request extraction from the Claude Code transcripts, extended, not
rewritten) and `docs/usage/phase6_audit.py` (tables in `docs/usage/phase6_audit.md`, machine copy `docs/usage/phase6_audit.json`).
Times are local (+02:00). Dollar figures are nominal API list rates as defined in `docs/usage/summary.md`; the account is a subscription and
no invoice matches them. Citations: `status.md l.N` = `docs/status.md` line N; commit ids are on `main` unless a branch is named; `sid` =
transcript session id under `~/.claude/projects/-Users-dk-Projects-3d-render-blender-3rd-attempt-building/`.

Companion page for non-technical readers: `docs/phase6_story.html` (it rounds; this file carries the caveats).

## 0. The question and the short answer

The Blender model was delivered on 2026-09-10 (v2, hero 3.61, `docs/delivery.md`). Turning it into a web walkthrough took from
2026-09-15 09:43 (first Phase 6 prompt, sid 6460c313) to 2026-09-18 23:35 (session 6 final stop, `status.md l.929`), 86 hours of wall clock,
with Phase 7 (a foliage fix the user asked for after seeing the live site) closing at 2026-09-19 09:56 (6253d32).

Where the 96 hours of 09-15 to 09-18 went (`phase6_audit.md`, block `phase6_only_15_18`, partition priority agent work > GPU > user > idle):

| bucket | hours | share | note |
|---|---|---|---|
| some agent working (lead or subagent) | 34.4 | 36 % | GPU jobs mostly ran under a polling agent, so they sit inside this bucket |
| GPU busy with no agent active | 0.6 | 1 % | the detached overnight Gate 3 queue ran 6.5 h, but the lead polled it (counted above) |
| blocked on the user (a decision, a restart, or evidence the user owed) | 29.9 | 31 % | 17.6 h of it is one `AskUserQuestion` call at 23:24 on 09-17 answered at 16:57 on 09-18 |
| idle, user away, nothing blocked on the user | 21.5 | 22 % | five machine closures with a written resume procedure |
| before the first Phase 6 prompt on 09-15 | 9.7 | 10 % | |

GPU busy in total (overlapping other buckets): 24.9 h. Nominal cost of 09-15 to 09-18: $1,505 (Opus 5 $1,326, Fable 5.1 $176, Sonnet 5
$2) over 8,068 API requests, 74 subagents, 6.58 M output tokens, 1,784 M cache-read tokens. The week 09-15 to 09-19 including Phase 7 and
the start of Phase 8: $2,148, 11,811 requests, 107 subagents.

So: the week was not one long compute job. Roughly a third was agents working, a third was the pipeline waiting for the user (most of it
overnight, when the user could not have answered), a fifth was the machine closed. The agent-work third is where the money went, and
inside it the largest single sink was the viewer engineer ($540 of $1,505, 36 %), followed by the bake engineer ($286) and the export
engineer ($266).

## 1. Wall clock per gate

Windows are bounded by the commit time of each gate verdict (`git log -1 --format=%ad`), so they are git facts, not the status file's
estimates. Hours are the minute-partition of `phase6_audit.py`; "GPU total" overlaps the other columns.

| gate | window (local) | wall h | agent work | GPU total | blocked on user | idle | subagents | cost USD | verdict chain |
|---|---|---|---|---|---|---|---|---|---|
| 0 vertical slice | 09-15 09:43 -> 11:50 | 2.1 | 2.0 | 1.6 | 0.1 | 0.1 | 4 | 78 | PASS, user "go" (70bfe73; decisions.md l.280-290) |
| 1 geometry freeze | 09-15 11:50 -> 16:58 | 5.1 | 5.1 | 3.0 | 0 | 0 | 11 | 176 | QA 11 FAIL, 11b FAIL, 11c FAIL, 11d PASS (57addb8) |
| 2 material bake | 09-15 16:58 -> 21:55 | 5.0 | 4.4 | 4.7 | 0 | 0 | 8 | 202 | QA 12 FAIL, 12b PASS (19412e4) |
| 3 lightmap bake | 09-15 21:55 -> 09-16 15:09 | 17.2 | 9.5 | 7.7 | 3.2 | 4.5 | 12 | 259 | overnight queue; QA 13 accepted + 1 re-bake (f8c9002) |
| 4 viewer, 6a | 09-16 15:09 -> 09-17 01:23 | 10.2 | 4.7 | 2.5 | 0 | 5.6 | 17 | 254 | QA 14 one more round, QA 15 parity (212ca27) |
| 6c foliage | 09-17 01:23 -> 12:56 | 11.6 | 5.2 | 4.0 | 5.8 | 0.6 | 22 | 322 | QA 16 one more round, QA 17 closed with residuals (47a2f7e) |
| 6b web + 6d | 09-17 12:56 -> 09-19 00:00 | 35.1 | 3.5 | 1.4 | 20.8 | 10.8 | 9 | 209 | QA 18 fix round, QA 18b done (98ab252); bare-URL fix 1c4b0f5; 6d d40a125 |
| Phase 7 | 09-19 00:00 -> 09:56 | 9.9 | 1.2 | 0.9 | 8.7 | 0 | 3 | 44 | QA 19 done with residuals (6253d32) |
| (Phase 8, same day) | 09-19 09:56 -> 24:00 | 14.1 | 8.6 | 3.2 | 2.5 | 2.9 | 31 | 599 | beyond the question; shown because it shares the day and the weekly budget |

Reading the table: Gates 0 to 2 were dense, 12 hours of near-continuous work on 09-15 for $456 and three passed gates. Gate 3 was the
overnight bake plus a rule-driven restart wait. From Gate 4 onward the wall clock is dominated by waits: 6b's 35 hours contain 3.5 hours
of agent work.

### 1.1 The waits, named (from the human-prompt timestamps in the transcripts and the stop states in status.md)

| gap | h | classified as | evidence |
|---|---|---|---|
| 09-16 05:34 -> 08:48 | 3.2 | blocked on user: restart | lead context hit 528k against the 350k rule and stopped (`status.md l.644`); user: "why do you ask me to restart?" 08:48 |
| 09-16 09:31 -> 13:51 | 4.3 | idle, user away | "I have to leave in 10 mins" 09:19; resume steps written (`l.668`) |
| 09-16 17:31 -> 22:31 | 5.0 | idle, user away | "i have to leave in 10 mins" 17:28; stop state `l.808` |
| 09-17 01:26 -> 07:10 | 5.7 | blocked on user, overnight | 6a judged; "Open for the user: default preset, and the iPhone" (`l.834`) |
| 09-17 08:21 -> 08:56 | 0.6 | idle, user away | "i want to leave in the next 10 mins" 08:16 |
| 09-17 13:00 -> 23:16 | 10.3 | idle, user away | "I want to go in the next 10 mins" 12:54; QA 17 finished unattended (`l.880`) |
| 09-17 23:24 -> 09-18 16:57 | 17.6 | blocked on user: the three 6b decisions | one blocking `AskUserQuestion` tool call in sid 3ada03f9 (iPhone model, host, tier-0 look; decisions.md l.716) |
| 09-18 19:51 -> 22:59 | 2.8 | blocked on user: owed evidence | "Owed from the user: Safari screenshot + iPhone walk" (`l.920`); user back 22:59 |
| 09-18 23:35 -> 09-19 08:43 | 9.1 | blocked on user, overnight | "Open decision for the user only" (`l.929`) |
| 09-19 09:58 -> 12:25 | 2.5 | blocked on user | Phase 7 closed, "Nothing scheduled" (`l.942`); user: "Is the job completed or what's next?" |

The single largest item of the week is a question asked at 23:24 to a user who had said at 12:54 that they were leaving. The lead could not
have proceeded without the iPhone model and the host, but it could have asked the question at 12:54 (the decisions were already listed in
`docs/briefs/phase6b_plan.md`, drafted during session 5, `status.md l.849-853`).

## 2. Tokens: by role, model, day and activity

Source: `phase6_audit.md` block `phase6_only_15_18` (09-15 00:00 to 09-19 00:00). Cost = list-rate nominal. Cache reads are 96 % of all
tokens, as in Phase 5.

### 2.1 By role (subagent role from its spawn description; the lead is the main thread)

| role | agents | requests | output k | thinking k | cache read M | cost USD | share |
|---|---|---|---|---|---|---|---|
| viewer engineer (Opus high) | 10 | 2,421 | 1,833 | 620 | 760 | 540 | 36 % |
| bake engineer (Opus xhigh) | 7 | 977 | 1,059 | 417 | 199 | 286 | 19 % |
| export engineer (Opus high) | 8 | 1,409 | 995 | 360 | 321 | 266 | 18 % |
| lead (Fable 5.1 high) | 6 sessions | 954 | 749 | 200 | 231 | 176 | 12 % |
| QA critic (Opus xhigh) | 13 rounds | 1,010 | 842 | 281 | 132 | 102 | 7 % |
| code reviewer (Opus) | 32 | 1,076 | 889 | 451 | 109 | 102 | 7 % |
| materials (Opus xhigh, MAT r10) | 1 | 146 | 185 | 99 | 27 | 30 | 2 % |
| Sonnet helpers | 3 | 75 | 29 | 13 | 6 | 2 | 0 % |

The viewer engineer's share is not one agent: ten viewer agents across Gates 0 to 6b, the most expensive being the Gate 4 "lightmap debug,
capture, items 2-7" agent at $103 (09-16 13:53 to 17:29) and the 6b "progressive load + deploy" agent at $108 (09-18 17:01 to 19:25). The
Gate 3 bake engineer that ran the overnight queue cost $108 (09-15 21:56 to 09-16 05:33), a large part of it polling: 977 bake-role requests
carry 25.7 M cache-write tokens, the highest of any role, because each poll re-wrote a growing context.

### 2.2 By model

| model | requests | output k | cache read M | cost USD | share |
|---|---|---|---|---|---|
| Opus 5 | 7,039 | 5,803 | 1,548 | 1,326 | 88 % |
| Fable 5.1 (lead only) | 952 | 749 | 231 | 176 | 12 % |
| Sonnet 5 | 75 | 29 | 6 | 2 | 0 % |

Casting was followed: every builder, critic and reviewer ran on Opus; Fable was the lead and the single final judgement of 6a
(decisions.md l.543). Sonnet did three mechanical jobs (perf passes, hosting research) for $2.

### 2.3 By day (local)

| day | wall | agent work h | GPU total h | blocked on user h | idle h | subagents started | human prompts | requests | cost USD | share of Phase 6 |
|---|---|---|---|---|---|---|---|---|---|---|
| 09-15 | 24 | 13.6 | 11.3 | 0.1 | 0.1 (+9.7 before start) | 21 | 29 | 2,370 | 495 | 33 % |
| 09-16 | 24 | 10.7 | 7.7 | 3.2 | 10.0 | 22 | 30 | 2,105 | 416 | 28 % |
| 09-17 | 24 | 6.8 | 4.7 | 6.4 | 10.9 | 24 | 32 | 2,568 | 390 | 26 % |
| 09-18 | 24 | 3.3 | 1.4 | 20.2 | 0.5 | 7 | 13 | 1,025 | 204 | 14 % |
| 09-19 (Phase 7 + 8) | 24 | 9.7 | 4.1 | 11.2 | 2.9 | 33 | 43 | 3,743 | 644 | (week 30 %) |

"Human prompts" counts every message typed by the user including one-word ones ("go", "end"); 09-15's 29 include the long session brief.
The user typed 147 messages in the week, 104 of them 09-15 to 09-18; about 26 of those were substantive (the list is in the audit script's `human_prompts`, timestamps only).

### 2.4 By activity (one label per API request, priority rule in `usage_from_transcripts.py`: viewing images > waiting on tools >
editing files > coordination > reading files and logs > running scripts > reasoning and reporting)

| activity | requests | output k | thinking k | cost USD | share |
|---|---|---|---|---|---|
| running scripts (python, npm, git merges, pack chains) | 2,382 | 1,930 | 756 | 434 | 29 % |
| reading files and logs | 2,224 | 1,037 | 679 | 329 | 22 % |
| waiting on tools (polls of status.json, pgrep, Monitor, blender_run) | 1,122 | 977 | 368 | 322 | 21 % |
| editing files | 1,273 | 2,029 | 404 | 246 | 16 % |
| reasoning and reporting (no tool call) | 403 | 83 | 15 | 74 | 5 % |
| viewing images | 493 | 363 | 190 | 71 | 5 % |
| coordination (Agent, SendMessage, AskUserQuestion) | 171 | 162 | 29 | 29 | 2 % |

Thinking tokens (2.44 M, 37 % of output) are inside every row; they are not a separate activity because the API bills them as output of the
request they belong to.

**Limits of this attribution.** (1) A request that read a log and then edited a file is counted once, under the higher-priority label; the
rule is fixed and stated, not tuned. (2) "Waiting on tools" is the cost of the polling turns themselves, not the wall time waited; 21 % of
the money went to turns whose purpose was to check whether something had finished. (3) Image viewing is under-counted where the image
arrived through a `Read` of a `.jpg` in a subagent whose result the extractor saw only as text; the 493 requests are those whose input
carried an image block. (4) Cost per request uses list rates with the 1-hour cache-write price for `ephemeral_1h` and the 5-minute price
otherwise, the same as `summary.md`; Claude Code's own internal tally for the same sessions is 8 to 30 % higher (`summary.md` cross-check
table) because it prices Haiku side calls the transcripts do not carry. (5) The turn-level numbers sum to the session totals in
`summary.md` (same deduplication by message id); the per-window split assigns a request to the window containing its timestamp, so a
subagent that straddled a gate boundary is split, not whole.


### 2.5 Cache misses, and what the output became (added 2026-09-23 after the user's follow-up; `docs/usage/phase6_examples.py`, `phase6_lines.sh`)

A subagent's prompt cache lives five minutes, the lead's one hour. A request that arrives after the cache has expired re-writes its whole
context at the premium price. In Phase 6, **155 requests re-wrote more than 100k tokens each, $343, 23 % of the phase.** By role: bake
engineers 74 requests, $148, **52 % of everything the bake role cost** (they watched hour-long bakes with ten-minute sleeps, so every poll
was a miss: a 267-token "is it done?" cost $2.21 on 09-16 02:08 against $0.17 for the same poll on a warm cache); export engineers 31 / $64
/ 24 %; viewer engineers 39 / $86 / 16 %; the lead 5 / $36 / 21 % (the largest single request of the week, $6.18, was the lead resuming at
22:59 on 09-18 after the evening away, 306k tokens re-written to answer "what else needs to get done?").

How the $1,505 is distributed (2026-09-23 correction: the page had called the $0.63 export-set request "the most expensive of the week"; it
was the largest by output, 21,167 tokens): 8,066 requests at a mean of $0.19, median $0.13; 7,041 requests under $0.25 sum to $880; the most
expensive 1 % carries 15 % of the cost, the top 10 % carries 38 %. The eight most expensive requests were all cold-cache re-writes: the top two
$10.60 and $10.37 by the lead on 09-16 (03:33Z, 06:48Z) with a 528k-token context, the session that had passed the 350k rule (§5.3); the most
expensive warm-cache request was $2.07 (lead, 09-18 16:58, 1,824 output tokens).

What the output tokens were: 37 % thinking (API counter), 61 % tool arguments (code, shell commands, briefs), 2 % prose (by character count
of the visible remainder). What they became, lines added on all branches 09-15 to 09-18 (`phase6_lines.sh`): export and pack scripts
19,329; viewer JavaScript 10,995; bake scripts 6,142; viewer tools and tests 4,917; critic probes 3,807; reviews 1,841; briefs 1,841; QA
reports 1,569; status, decisions, delivery and tech notes 1,143; plus 821,558 lines of generated JSON sidecars under renders/ (capture
metadata, not written by a model).

## 3. Retry loops and rework

| loop | count | where | cost of the extra rounds |
|---|---|---|---|
| QA rounds to pass Gate 1 | 4 (11, 11b, 11c, 11d) | export blockers found one at a time: backdrop `texCoord -1`, torn attic panels, then 127 opaque stand-in boards, then 1,379 shrubs drawn at the origin (`status.md l.585-605`) | critics $29 (of $102 for all 13 rounds); each re-capture by the lead ~25 min |
| QA rounds to pass Gate 2 | 2 (12, 12b) | 7 of 12 stone sets shipped no normal map; then the detail maps shipped all-zero, then at 3-6 % contrast, re-derived twice (`l.629-635`) | bake re-run 2,229 s GPU; three viewer merges in one evening |
| Gate 3 re-bakes | 1 asset + 1 refuted hypothesis | rotunda ceiling: 100 % inverted normals (`l.746`); "sky-branch" hypothesis staged as a 47-job overnight re-bake, refuted by a probe, never run (`l.772`) | ~30 min GPU; the refuted re-bake would have cost 6 h |
| Gate 4 rounds | 2 (14, 15) + a blocked merge | pre-merge review found the probe cube never uploaded (black envMap), QA-13-1 closure withdrawn and re-measured (`l.795-798`) | viewer fixes $12 |
| instance irradiance bake | 2 runs | the first used an opaque stand-in that biased values +64 % (review 7d59c5f, `l.823`) | 2,597 s + ~2,700 s GPU |
| 6c bake anchors | 2 runs + topology rev 2 | bake anchored at object origin, export at bbox centre, 3.4 m apart; far trees placed 300 m off (`l.855-862`) | 562 + 575 + 44 s GPU, one extra export round |
| 6c QA rounds | 2 (16, 17) | crowns "balloons", shrubs 1.3-1.7x bright at 100 % after the numeric acceptance passed (`qa_round_16.md`) | viewer round 3 $74 |
| 6b deploy | 6 deploys in 30 h | mobile glbs unpublished (QA 18 blocker), header rule, canvas 70 %, bare URL drew the test scene (found by the user's phone), 6d reflection | deploys 1-6 logs `renders/logs/6b_deploy_*.log` |
| code reviews | 32 in 09-15..18 (34 with Phase 7) | verdicts: 25 MERGE WITH FIXES, 3 MERGE AFTER FIXES, 1 MERGE BLOCKED, 1 SEND BACK, 1 MERGE; 128 "fix now" mentions | $102 total, max $6.61 per review |
| lead restarts | 6 lead sessions for Phase 6 (sids 6460c313, c47a8492, 87d95e57, 5b1d192d, 4133edbe, 3ada03f9) | one forced by the 350k rule at 528k, four by the user leaving; re-cache cost in the first 15 minutes $1.7 to $5.4 each (`phase6_audit.md` "Lead sessions") | ~$20 total |

Commits: 616 on all branches 09-15 to 09-18 (198 / 187 / 153 / 78 per day), 53 merges into main; 165 subjects (27 %) carry a rework word
(fix, re-bake, re-export, revert, correction, blocker). Phase 5's five days: 792 commits, 150 rework subjects (19 %), 75 merges.

The pattern behind most of the loops: a contract between two agents' outputs was checked by pixels at a QA gate instead of by an assertion at
the hand-off. gltfpack stripped `TEXCOORD_1` from every glb at Gate 1 and nobody noticed until Gate 3 (`decisions.md l.360`); the exporter
inserted a constant-white `COLOR_0` (`l.371`); the bake and the export anchored trees at different points; the deploy plan was built from one
of two manifests. Each was found by the next consumer, one gate later, and each cost a review round plus a re-capture.

## 4. Cost per point of station score

Scores are the QA critic's per-station averages (`docs/qa_round_*.md`); Phase 5 baseline is the delivered hero 3.61 (round 10b, all six
stations from round 9). The parity table in `docs/delivery.md` uses 3.67 (round 9) for the hero; both are shown.

| step | from -> to | hero | mean of six | cost USD | USD per hero point | USD per mean-of-six point |
|---|---|---|---|---|---|---|
| Gates 0-1 (geometry, grey) | 3.61 -> 3.50 (QA 11, geometry rows only) | -0.11 | +0.03 | 254 | no gain | 10,160 |
| Gates 2-3 (materials + lightmaps) | 3.50 -> 3.39 (QA 13, lightmaps alone) | -0.11 | -0.25 | 461 | no gain | no gain |
| Gate 4 (viewer, post, water) | 3.39 -> 3.72 (QA 15) | +0.33 | +0.27 | 254 | 769 | 937 |
| 6c foliage | 3.72 -> 3.78 (QA 17) | +0.06 | +0.06 | 322 | 5,360 | 5,025 |
| 6b web | 3.78 -> 3.78 desktop; mobile first scored 2.9 | 0 | 0 | 209 | no gain (a deployment, not a look) | |
| Phase 7 | 3.78 -> 3.78; cam05 2.94 -> 3.06; mobile 2.9 -> 3.2 | 0 | +0.02 | 44 | no gain on the hero | 2,204 |
| whole of Phase 6 (09-15..18) | 3.61 -> 3.78 | +0.17 | +0.10 | 1,505 | 8,850 | 15,050 |

The intermediate gates score below the baseline by construction (grey geometry, then materials without shadow), so the per-gate ratio is
meaningful only from Gate 4 on. The honest reading: Phase 6 was not bought for points. Its deliverable was a different medium at the same
score, and the score it reached, 3.78 desktop, is 0.17 above the Cycles render it was baked from because the critic scored the viewer against
Cycles renders of the same stations, not against the photograph (see 5.1). For comparison, Phase 5's rounds 6 to 9 bought +0.39 on the hero (3.28 to
3.67) for about $500 of sessions 4 and 5 (`summary.md`), roughly $1,300 per hero point.

## 5. Definition of done, checked against git and the QA reports

CLAUDE.md "Definition of done and stopping rule" (a0a7156, 09-15 10:15), item by item. "Met" means the artefact exists in git or the QA
report states the measurement; the lead's summaries were not used as evidence.

### 5.1 6a (this Mac)

| item | status | evidence |
|---|---|---|
| viewer at 1440p with median frame time and GPU memory reported | met, target missed | QA 15: 28.2 ms median (35.5 fps), 1,677.9 MB; target >= 45 fps not met; `?quality=fast` 36-49 fps (`status.md l.789`) |
| stations 1-6 as presets, screenshots deterministic through headless Chrome | met | `web/tools/gate4.sh`, capture logs; QA 15 "0 page errors" |
| QA scores each station twice: vs the Phase 5 Cycles render (parity) and vs the reference photo (the rubric) | half met | parity rows exist for every round. No Phase 6 QA report scores the viewer against the photograph: `grep -i photo docs/qa_round_15.md` returns nothing; stations 2-6 were scored against `renders/previews/qa/round13_0N_*_cycles.png`, station 1 against the Phase 5 hero (`qa_round_15.md` header). The rubric rows (Silhouette, Ornament, Edge wear...) were filled, but their reference was the render |
| every station within 0.5 of its Phase 5 score, none below 2.5 | met | QA 15: 3.72 / 3.00 / 2.56 / 2.88 / 2.94 / 2.83 vs 3.67 / 2.94 / 2.56 / 2.81 / 3.06 / 2.67 (worst -0.12) |
| water reflects the rotunda at the hero station | met | QA 15 "the hero water reflects the rotunda and now ripples" |
| walk controls with ground clamp, no walking into the lagoon | met | QA 15: 24/24 probes above WATER_Z + 0.1 |
| loading screen with progress | met | QA 15 "the loading bar carries a correct total" (640 MB); denominator bug fixed again in 6b (QA 18 finding 2) |
| stopping rule: parity, or two flat rounds after Gate 4 | met as written | QA 14 "one more round", QA 15 parity; decisions.md l.543 |
| Fable used for QA exactly once, the final gate | met | decisions.md l.543 "the single Fable QA pass of Phase 6" |
| Gate 0 passes before any scale-up | met | 70bfe73; user "go" 09-15 11:55 |
| ORN_ export is the user's decision, three options with counts | met | decisions.md l.259-279, `export/out/gate0/orn_options.json` |
| the LUT baked from Blender's own OCIO and verified against a Cycles render | met | Gate 0: 65^3 LUT, 0.072/255 (`status.md l.544`); tech_notes "Phase 6" |
| lightmap encoding: min, max and clipped-pixel count reported at Gate 0 and every later bake round | not met as intended | reported, but the Gate 3 review (`docs/reviews/phase6_bake_gate3_review.md` l.57) found the "0 clipped texels" figure a tautology (`clipped = (lum > max(lum)).sum()` cannot be non-zero), carried, not fixed in Phase 6 |
| name sweep and six-station 100 % tile review at every gate | met | every QA round 11-19 states the sweep result (0 hits, 127 hidden treeboards as the standing exception) and lists the tiles viewed |

### 5.2 6b (web)

| item | status | evidence |
|---|---|---|
| initial payload <= 50 MB | met | QA 18b: 46,808,904 B before the first frame on the URL, 320 requests |
| progressive loading, meshopt + KTX2 | met | 3 tiers, 0 files over 25 MiB, hot-swap verified (QA 18b §1) |
| Safari and Chrome on macOS | Chrome met; Safari not evidenced | every capture is headless Chrome; the "Safari" evidence is a Playwright WebKit 26.6 render (`renders/web/user/webkit26_hero_1920x1080_20260918.jpg`), not Safari.app; the user's Safari screenshot was never delivered (`delivery.md` "Still owed") |
| mobile fallback (LOD1 geometry, halved textures) that loads and walks, tested in iOS Safari on the iPhone the user names | loads: met by the user's screenshot; walks: not evidenced on the device | `renders/web/user/iphone16pro_hero_portrait_20260918.jpg` (iOS Safari, 5G, portrait); the walk was measured headlessly on the Mac with the mobile tier (`renders/web/6dm_walk.json`); the phone's own frame rate is "unmeasured" (`delivery.md` "Evidence closed by the lead") |
| staging URL with one QA round against it | met | https://pfa-walkthrough.3d-render-blender-3rd-attempt-building.workers.dev; QA 18 (fix round), QA 18b (clean of blockers, "done with residuals") |
| stopping rule: deployment plus one clean QA round; polish beyond is a new phase | bent | 6d (mobile reflection, HUD) was a lead fix after the closing round, logged in decisions.md l.769 as "one round", without a phase decision by the user |
| every file <= 25 MiB (Cloudflare) | met | QA 18b: 0 of 622 |

### 5.3 Machine and process rules in the same CLAUDE.md section

| rule | status | evidence |
|---|---|---|
| Chrome never concurrent with the bake queue | bent once, then relaxed | "One Chrome slip (10 s during a bake, killed)" (`status.md l.612`); `PFA_DEV_SHARE_GPU=1` introduced for development screenshots (decisions.md l.414) |
| at most 3 builders concurrent, 4 Blender-using agents | met | max 3 builders (6c: bake + export + viewer) plus reviewers and critics (no Blender) |
| clean restart past 350k context | broken once | session 1 checkpointed at 528k (`status.md l.644`); sessions 4-6 reached 327k, 313k, 601k (`phase6_audit.md` "Lead sessions": 3ada03f9 max context 601,028 tokens, spanning 6b, 7 and 8) |
| burn logged in status.md at the end of every session | met, with a corrupted line | six burn lines; `status.md l.930` and `l.943` read "Phase 6 to date ≈ ,290" and "≈ ,789": a shell heredoc ate `$1` |
| images downscaled to 960 px before viewing; full-res captures not committed | broken repeatedly, caught by reviews | ~58 MB, 30.6 MB and 22.5 MB of full-res PNGs flagged by three reviews (`status.md l.700`, `l.865`, `l.904`) |
| briefs point at files, fresh agents every session | met | `docs/briefs/phase6*.md` (28 files) plus 11 QA briefs; no agent resumed across sessions (roster in `phase6_audit.json` agents) |
| Phase 6 target <= 40 weekly points | unmeasurable | see 6.3 |

## 6. What an experienced reviewer would flag

### 6.1 Software engineering
- **Contracts checked by pixels, not by assertions.** The four Gate 1 QA rounds each found one export defect that a schema check on the
  packed glb would have found in seconds (`texCoord -1`, missing `TEXCOORD_1`, nodes without transforms). `verify_glb` was written on the
  fourth round (`status.md l.602`). Same shape at Gate 3 (UV2 stripped since Gate 1) and 6b (mobile paths missing from the deploy plan).
- **Tests that could not fail.** Reviews found tautological asserts three times: Gate 3 encode "0 clipped" (bake review l.57), two
  `gate3_test.mjs` checks (viewer r5 review), placement asserts in 6c export r1. A review catching a tautology after the fact is the
  expensive way to learn it.
- **Hard-coded absolute paths to MAIN** in four scripts, each caught by a reviewer (`gate3_relay_check.py`, `hero_boxes.py`, the encoder,
  `manifest_v4.py` mist path). Worktree agents read MAIN's outputs by path; nothing enforced `PFA_MAIN_ROOT`.
- **Generated state overwritten with no archive.** `export/out/bake_queue/status.json`, `compose.json`, `encode.json` and `bake_jobs.json`
  hold only the Phase 9 run now; the Phase 6 Gate 3 job records (65 jobs, 6 h 30 m) survive only as one line in status.md. CLAUDE.md's
  own layout section lists "status files' final copies in docs" as committed; `git ls-files | grep status.json` returns nothing.
- **Large binaries in git.** Three reviews removed full-resolution PNGs from the branch; `renders/web` tracked 102 MB at one point
  (`status.md l.712`).

### 6.2 3D pipeline
- **The two half-hidden defaults of gltfpack.** `-mi` drops node names (the name sweep had to move to the Blender side); `-c` quantises UVs
  to 12 bits and the viewer must undo it on `TEXCOORD_1` (the "dark hero" of Gate 4, `decisions.md l.379`); `-km` merges same-named
  materials (nine backdrop sets attached to nothing). Each was discovered by its symptom.
- **Blender 5.2 exporter behaviours** (constant-white `COLOR_0`, hidden LOD0 objects absent from the depsgraph, `Image.save_render` without
  colour management) cost a round each and are now in `docs/tech_notes.md`; the right time to find them was Gate 0, on the slice.
- **Two anchors for one tree.** Bake and export computed placement anchors differently (up to 3.4 m); the topology file became the record
  only after the mismatch (decisions.md l.605-616).
- **Texture memory over budget from Gate 2.** Resident 1,334 MB at Gate 2 against a 1,200 MB plan, 1,931 MB after 6c (1.61x); the
  budget was re-stated rather than enforced, which is why 6b had to invent tiers.
- **The 45 fps target** was declared unreachable with the Reflector's second scene traversal and bloom (decisions.md l.446-464) and moved
  to a preset. That is a scope change recorded as a decision, which is fine; what is missing is a measured frame budget per feature before
  the features were built.

### 6.3 Multi-agent process
- **The lead polls.** 21 % of the spend is turns whose job was to check whether something had finished. The bake engineer of Gate 3 spent
  $108 largely on polling an overnight queue that a cron-style notification could have watched for nothing.
- **Questions to an absent user.** 29.9 h blocked on the user in a 96 h window, 17.6 h of it one question posted at 23:24. The rule "no
  idling on serial steps" exists (CLAUDE.md, 2026-09-09) but there was no backlog written for 6b's serial wait, and the questions were
  asked after the user had left rather than before.
- **Review verdict inflation.** 25 of 32 reviews said "MERGE WITH FIXES"; only one said "MERGE". The verdict carries almost no
  information; the "fix now" count (128) does.
- **The 40-point budget is unmeasurable.** Nothing in the repository or the transcripts records the subscription meter. The two anchors
  are the user's statements on 09-09 ("~32 % of the weekly limit left", decisions.md l.192; "about 30 %" later that day, l.218). Nominal
  spend by the morning of 09-09 was about $960 (`summary.md` daily table), so one point was roughly $14 to $16 nominal at that time. On
  that scale Phase 6 (09-15..18) is about 100 points and the week 09-15..21 about 165, which cannot be right for a limit that was never
  hit. Either the meter does not scale with list-rate dollars (cache reads dominate and are priced differently) or the anchor was rough.
  The audit therefore reports dollars and shares; the "points" target was never checkable by the lead either.
- **Status timestamps are estimates.** From 09-20 the status file carries "~HH:MM" times; on 09-21 "~23:45" was written for a commit made
  at 20:10 (61311f0). For the Phase 6 week the entries carry no times at all, which is why this audit uses commit times.
- **Who reads the reviews.** Carries accumulated: 9 + 8 + 7 + 9 per review by Gate 3; most were closed by later work only by chance.

## 7. Findings not asked for (three asked, one added later)

1. **The user's own words show a mismatch between availability and the process.** Eight of the 26 substantive user messages in the week are
   "I have to leave in 10 minutes" or "what should I do now". The process assumes a user who signs off gates; the user was present for
   for visits of 10 to 40 minutes, two to four times a day. Every gate that needed sign-off waited for the next visit.
2. **The lead's context grew past its own rule three times** (528k, 601k) and the 601k session spanned three phases (6b, 7, 8). The re-cache
   cost of a restart is $2 to $5; the cost of the alternative was the 09-16 05:34 to 08:48 restart wait and the visible quality drop in the
   late-session status entries (the "≈ ,290" corruption and the "~HH:MM" times date from the long sessions).
3. **The viewer scored above the render it was baked from.** 3.78 vs 3.61 on the hero because the Phase 6 critics compared the viewer to
   Cycles frames of the same stations, and a viewer that reproduces a Cycles frame closely gets the frame's rubric marks back, plus a half
   step wherever the frame's own defect was fixed on the web side (water, foliage). Against the photograph, which is what CLAUDE.md asked,
   the parity ceiling written in `docs/briefs/phase6_plan.md` §4b ("a viewer cannot score above the render it is baked from") should have
   held. The 3.78 is real as a parity number and should not be read as a photoreal score.

4. **(Found after the user's follow-up, 2026-09-23.) A quarter of the phase's cost was cache misses.** 155 requests that re-wrote their
   whole context because a subagent had slept past its five-minute cache, or the lead came back after an hour: $343 of $1,505. The
   bake role, whose job was to wait, spent half of its money on the waiting itself (§2.5).

## 8. Proposed changes to CLAUDE.md (at most ten, with evidence)

### Rules
1. **Ask before the user leaves.** When the user announces a departure, the lead's next message lists every decision the next 24 hours will
   need, with the lead's recommendation, and proceeds on the recommendation if no answer comes within the session. Evidence: 17.6 h on one
   `AskUserQuestion` (09-17 23:24), 5.7 h and 9.1 h overnight waits (§1.1); 29.9 h of 96 blocked on the user.
2. **A written no-render backlog for every serial wait.** The 2026-09-09 "no idling" rule needs a named file (`docs/backlog.md`) that the
   lead consumes during waits and that reviews' carries are appended to. Evidence: the 6b wait had 24 open review carries and nothing ran.
3. **Restart at 350k means restart.** Replace "clean restart past 350k" with a hard stop: the lead writes the checkpoint and ends the turn
   at 350k; no gate verdict may be written by a lead above it. Evidence: 528k and 601k sessions; the corrupted burn lines and estimated
   timestamps both come from long sessions (§5.3, §6.3).
4. **Status entries carry the commit id and the commit time, never an estimated clock time.** Evidence: "~23:45" for 20:10 (61311f0).

### Pipeline
5. **Every hand-off between agents ships with a machine check the consumer runs first**, and the check must be able to fail (a fixture
   that makes it fail is committed next to it). Evidence: four Gate 1 rounds, UV2 stripped since Gate 1, constant-white COLOR_0, the
   two anchors, the missing mobile paths, three tautological asserts (§3, §6.1).
6. **Gate 0 exercises the packer and the exporter on every attribute the pipeline will later rely on** (UV2, COLOR_0, node names, material
   merging, alpha modes), not only the look. Evidence: all five gltfpack/exporter surprises were discoverable on the 62k-triangle slice.
7. **Long GPU jobs are watched by a notification, not by an agent; any poll loop sleeps under five minutes or ends the turn.** The bake
   queue writes its completion into a file the harness watches; no agent turn is spent polling, and no subagent sleeps past its own cache
   lifetime. Evidence: 21 % of spend on "waiting on tools" turns; 155 cache-miss requests for $343 (§2.5), 52 % of the bake role's cost.
8. **Archive generated run records at every gate** (`export/out/bake_queue/status.json` and the compose/encode records copied to
   `docs/runs/<gate>/`). Evidence: the Phase 6 bake records no longer exist (§6.1).

### Casting
9. **Reviews return a fix-now count and a blocker flag, not a verdict word.** Merge when blockers = 0 and fix-nows are closed. Evidence:
   25 of 32 verdicts were the same phrase (§6.3).
10. **QA scores the viewer against the photograph once per phase**, in addition to parity, and the delivery table shows both. Evidence:
    §5.1 third row; §7 finding 3.

## 9. Phase 6 against Phase 5 on the same measures

Same scripts, same rules; Phase 5 window 09-06 12:00 to 09-10 16:00 (`docs/retrospective.md` §2).

| measure | Phase 5 (5 days) | Phase 6 (09-15..18) | week 09-15..19 |
|---|---|---|---|
| wall clock, first prompt to delivery | 100 h | 86 h (96 h window) | 120 h |
| agent work (union) | 42.2 h | 34.4 h | 44.1 h |
| GPU busy total | 33.5 h (renders) | 24.9 h (bakes, captures) | 29.0 h |
| blocked on the user | 0.1 h | 29.9 h | 41.1 h |
| idle, user away | 53.0 h | 21.5 h (+9.7 before start) | 24.4 h |
| nominal cost | $1,483 | $1,505 | $2,148 |
| requests / output tokens | 9,099 / 6.23 M | 8,068 / 6.58 M | 11,811 / 8.07 M |
| subagents | 114 | 74 | 107 |
| lead share of cost | 14 % (Fable) | 12 % (Fable) | 13 % |
| code reviews / cost | 43 / $89 (retrospective.md counted 38 / $66 with its own classifier) | 32 / $102 | 46 / $152 |
| QA rounds / critic cost | 11 / $93 | 13 / $102 | 19 / $142 |
| commits / rework subjects / merges | 792 / 150 (19 %) / 75 | 616 / 165 (27 %) / 53 | 869 / 229 / 82 |
| hero score change | 2.17 -> 3.61 (+1.44) | 3.61 -> 3.78 parity (+0.17) | +0.17 |
| user messages | 927 turns in 5 sessions (`summary.md`), most tool results | 104 typed, about 26 substantive | 147 typed |

Phase 6 cost the same money as Phase 5 for a different deliverable, in fewer agent hours, with a different failure mode: Phase 5 lost time
to renders killed by a watchdog and to three flat polish rounds; Phase 6 lost time to hand-off defects found one gate late and to a user
who was asked questions after leaving. Phase 5's waits were the machine's; Phase 6's were the calendar's.

## 10. This audit's own burn

Session 6cfdbe19 (Fable 5.1 at high effort, no subagents, no Sonnet helpers, no Blender, no Chrome): $19.92 nominal at list rates for the
whole session up to the final burn run (`docs/usage/summary.md`, row 6cfdbe19; 2026-09-21 22:08 to about 23:00 local). Sonnet helpers
were not used: the two mechanical jobs (image crops, contact sheet) were cheaper as one shell loop each than as briefs. In "weekly points"
the figure is unmeasurable for the reason given in section 6.3; on the rough 09-09 calibration it would be about one to two points against
the four allowed.
