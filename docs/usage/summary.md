# Token usage summary (from Claude Code transcripts)

Generated 2026-09-15T19:56:23Z by `docs/usage/usage_from_transcripts.py` from `/Users/dk/.claude/projects/-Users-dk-Projects-3d-render-blender-3rd-attempt-building` (9 main sessions, 134 subagent transcripts). Usage is deduplicated by API message id. Tokens in thousands (k) unless stated.

Also in this folder: `daily.json` and `sessions_all.json` are raw `ccusage` exports (account-wide, every project, its own price table; `sessions_all.json` has no project field, which is why this script exists). `make_timeline.py` renders `docs/timeline.html` from `sessions.json`.

## Rates used (Anthropic list, USD per million tokens)

| model | input | output | cache write 5m | cache write 1h | cache read |
|---|---|---|---|---|---|
| claude-fable-5-1 | 10.00 | 50.00 | 12.50 | 20.00 | 0.25 |
| claude-opus-5 | 5.00 | 25.00 | 6.25 | 10.00 | 0.50 |
| claude-sonnet-5 | 2.00 | 10.00 | 2.50 | 4.00 | 0.20 |
| claude-haiku-4-5-20251001 | 1.00 | 5.00 | 1.25 | 2.00 | 0.10 |

Source: claude-api skill pricing table (cached 2026-06-24). Cache write = 2x input for the 1-hour TTL Claude Code uses, 1.25x for 5-minute; cache read = 0.1x input except Fable 5.1 at $0.25/MTok. Nominal API cost only; the account runs on a subscription, so no invoice matches these numbers.

## Grand total by model

| model | requests | input k | output k | thinking k (of output) | cache write 1h k | cache write 5m k | cache read k | cost USD |
|---|---|---|---|---|---|---|---|---|
| claude-opus-5 | 9580 | 19 | 6,910 | 3,286 | 0 | 72,563 | 1,687,937 | 1,470.34 |
| claude-fable-5-1 | 1738 | 45 | 1,786 | 625 | 7,145 | 11,613 | 420,125 | 482.84 |
| claude-sonnet-5 | 25 | 0 | 25 | 15 | 0 | 107 | 1,903 | 0.90 |
| <synthetic> | 27 | 0 | 0 | 0 | 0 | 0 | 0 | 0.00 |

**Grand total nominal cost: $1,954.08**

## Sessions

| # | session | first (UTC) | last (UTC) | wall h | user turns | subagents | cost USD | cost by model |
|---|---|---|---|---|---|---|---|---|
| 1 | db75376f | 2026-09-06T10:40 | 2026-09-07T12:47 | 26.12 | 184 | 10 | 214.35 | fable-5-1 214 |
| 2 | 747b5259 | 2026-09-07T13:04 | 2026-09-07T17:32 | 4.46 | 143 | 11 | 281.72 | opus-5 265, fable-5-1 16 |
| 3 | f6551679 | 2026-09-07T18:11 | 2026-09-08T07:56 | 13.74 | 197 | 30 | 463.05 | opus-5 386, fable-5-1 77 |
| 4 | 1e741676 | 2026-09-09T05:42 | 2026-09-09T17:38 | 11.93 | 202 | 40 | 302.70 | opus-5 266, fable-5-1 37 |
| 5 | c1c6cc77 | 2026-09-09T17:38 | 2026-09-10T12:10 | 18.52 | 201 | 23 | 205.23 | opus-5 144, fable-5-1 60 |
| 6 | 797d734e | 2026-09-10T12:11 | 2026-09-15T08:18 | 116.12 | 69 | 0 | 29.89 | fable-5-1 30 |
| 7 | 11484ff4 | 2026-09-15T07:43 | 2026-09-15T07:43 | 0.0 | 3 | 0 | 0.64 |  |
| 8 | 6460c313 | 2026-09-15T07:49 | 2026-09-15T19:56 | 12.12 | 306 | 20 | 455.69 | opus-5 409, fable-5-1 46 |
| 9 | 52e90d0f | 2026-09-15T08:18 | 2026-09-15T08:20 | 0.03 | 3 | 0 | 0.82 |  |

## Cross-check: Claude Code internal cost-state per session

Claude Code keeps its own running tally in the transcript (`cost-state` rows, its internal price table, and it includes Haiku side calls such as web search and title generation that leave no assistant usage rows). Reported for comparison; the list-rate figures above are the ones cited elsewhere.

| session | Claude Code totalCostUSD | API-call hours | tool hours | lines +/- | this script USD |
|---|---|---|---|---|---|
| 1 db75376f | 43.10 | 1.05 | 0.16 | 23/0 | 214.35 |
| 2 747b5259 | 381.55 | 6.68 | 6.44 | 1949/153 | 281.72 |
| 3 f6551679 | 641.83 | 17.67 | 16.18 | 7335/762 | 463.05 |
| 4 1e741676 | 437.94 | 11.19 | 8.43 | 4830/328 | 302.70 |
| 5 c1c6cc77 | 261.44 | 6.25 | 3.97 | 5131/120 | 205.23 |
| 6 797d734e | 5.89 | 0.01 | 0.0 | 0/0 | 29.89 |
| 7 11484ff4 | 0.64 | 0.0 | 0.0 | 0/0 | 0.64 |
| 9 52e90d0f | 0.82 | 0.01 | 0.0 | 0/0 | 0.82 |
| total | 1,773.21 | | | | 1,954.08 |

## Daily nominal cost (this project only, UTC)

| day | cost USD | fable-5-1 | opus-5 | other |
|---|---|---|---|---|
| 2026-09-06 | 57.75 | 57.75 | 0.00 | 0.00 |
| 2026-09-07 | 602.56 | 194.65 | 407.91 | -0.00 |
| 2026-09-08 | 298.82 | 55.81 | 243.01 | 0.00 |
| 2026-09-09 | 401.76 | 50.22 | 350.64 | 0.90 |
| 2026-09-10 | 130.25 | 70.93 | 59.32 | 0.00 |
| 2026-09-15 | 462.95 | 53.48 | 409.47 | 0.00 |

## Subagents per session (by model, count and cost)

- Session 1 (db75376f): 6 x <synthetic>,fable-5-1 ($163); 4 x fable-5-1 ($19). Types: {'general-purpose': 10}
- Session 2 (747b5259): 11 x opus-5 ($265). Types: {'general-purpose': 11}
- Session 3 (f6551679): 27 x opus-5 ($386); 3 x fable-5-1 ($30). Types: {'general-purpose': 30}
- Session 4 (1e741676): 40 x opus-5 ($266). Types: {'general-purpose': 40}
- Session 5 (c1c6cc77): 22 x opus-5 ($144); 1 x sonnet-5 ($1). Types: {'general-purpose': 23}
- Session 6 (797d734e): . Types: {}
- Session 7 (11484ff4): . Types: {}
- Session 8 (6460c313): 20 x opus-5 ($409). Types: {'general-purpose': 20}
- Session 9 (52e90d0f): . Types: {}

## Agents dispatched by role (subagent transcripts, classified from their spawn descriptions)

| session | research | architecture | ornament | materials | environment | lighting | QA critic | code review | phase 5 prep | other | total |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 4 ($24) | 1 ($27) | 1 ($41) | 1 ($44) | 1 ($22) | 1 ($18) | 1 ($6) | - | - | - | 10 ($182) |
| 2 | - | 2 ($15) | 2 ($33) | 2 ($33) | 2 ($114) | 2 ($58) | 1 ($14) | - | - | - | 11 ($265) |
| 3 | - | 3 ($43) | 1 ($29) | 3 ($73) | 4 ($114) | 4 ($110) | 3 ($30) | 12 ($16) | - | - | 30 ($415) |
| 4 | - | 5 ($32) | 5 ($24) | 3 ($36) | 5 ($50) | 4 ($69) | 2 ($21) | 16 ($33) | - | - | 40 ($266) |
| 5 | - | 1 ($8) | - | 2 ($30) | - | 4 ($60) | 4 ($23) | 10 ($16) | 2 ($6) | - | 23 ($145) |
| 6 | - | - | - | - | - | - | - | - | - | - | 0 ($0) |
| 7 | - | - | - | - | - | - | - | - | - | - | 0 ($0) |
| 8 | - | - | - | 1 ($30) | - | - | 6 ($41) | 7 ($23) | - | 6 ($316) | 20 ($409) |
| 9 | - | - | - | - | - | - | - | - | - | - | 0 ($0) |
| all | 4 ($24) | 12 ($126) | 9 ($126) | 12 ($246) | 12 ($299) | 15 ($314) | 17 ($135) | 45 ($88) | 2 ($6) | 6 ($316) | 134 ($1682) |

Lead (main thread) cost per session, same rates: session 1 $33, session 2 $16, session 3 $48, session 4 $37, session 5 $60, session 6 $30, session 7 $1, session 8 $46, session 9 $1.

## Subagent list (cost >= $5)

| session | agent | type | model(s) | first | last | output k | cache read k | cost USD | description |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ab82b0f51 | general-purpose | <synthetic>,fable-5-1 | 09-06T18:53 | 09-07T06:49 | 75 | 20,713 | 44.12 | Materials specialist (Phase 2) |
| 1 | afe4bd7e6 | general-purpose | <synthetic>,fable-5-1 | 09-06T18:53 | 09-07T06:48 | 81 | 23,136 | 40.67 | Ornament modeler (Phase 2) |
| 1 | a7608bfcb | general-purpose | <synthetic>,fable-5-1 | 09-06T18:53 | 09-07T06:49 | 104 | 24,515 | 27.38 | Architecture modeler (Phase 2) |
| 1 | ab19eb1f3 | general-purpose | <synthetic>,fable-5-1 | 09-06T18:54 | 09-07T06:49 | 100 | 14,729 | 21.66 | Environment builder (Phase 2) |
| 1 | a1cfa498e | general-purpose | <synthetic>,fable-5-1 | 09-06T18:54 | 09-07T06:49 | 50 | 8,736 | 17.53 | Lighting and rendering (Phase 2) |
| 1 | a4ade4006 | general-purpose | <synthetic>,fable-5-1 | 09-06T11:35 | 09-06T12:27 | 45 | 4,955 | 11.53 | Phase 1 reference research |
| 1 | a7342dfe6 | general-purpose | fable-5-1 | 09-06T11:53 | 09-06T12:06 | 15 | 1,768 | 7.52 | Ornament crops and catalog |
| 1 | af73045d9 | general-purpose | fable-5-1 | 09-07T05:58 | 09-07T06:22 | 38 | 3,420 | 5.83 | QA critic round 1 (Phase 2 gate) |
| 2 | a8595907d | general-purpose | opus-5 | 09-07T13:08 | 09-07T14:32 | 98 | 191,154 | 102.80 | ENV fix agent, QA round 1 |
| 2 | ab45d3562 | general-purpose | opus-5 | 09-07T13:31 | 09-07T14:26 | 76 | 53,809 | 30.53 | LIGHT fix agent, QA round 1 |
| 2 | a327f7c6c | general-purpose | opus-5 | 09-07T15:20 | 09-07T17:30 | 58 | 35,819 | 27.30 | LIGHT polish round 1 (QA-02) |
| 2 | adf99a1d4 | general-purpose | opus-5 | 09-07T15:20 | 09-07T17:01 | 31 | 23,316 | 22.18 | MAT polish round 1 (QA-02) |
| 2 | acf583f2e | general-purpose | opus-5 | 09-07T15:49 | 09-07T16:46 | 48 | 26,581 | 17.39 | ORN polish round 1 (QA-02) |
| 2 | a336431db | general-purpose | opus-5 | 09-07T13:24 | 09-07T14:16 | 47 | 24,493 | 15.17 | ORN fix agent, QA round 1 |
| 2 | a35d47193 | general-purpose | opus-5 | 09-07T14:43 | 09-07T16:10 | 42 | 12,252 | 13.77 | QA round 2 critic |
| 2 | a0e28da83 | general-purpose | opus-5 | 09-07T15:21 | 09-07T16:28 | 21 | 14,101 | 10.74 | ENV polish round 1 (QA-02) |
| 2 | a50165999 | general-purpose | opus-5 | 09-07T13:25 | 09-07T14:41 | 50 | 14,553 | 10.57 | MAT fix agent, QA round 1 |
| 2 | a2ede30f3 | general-purpose | opus-5 | 09-07T13:07 | 09-07T13:30 | 38 | 13,405 | 8.99 | ARCH fix agent, QA round 1 |
| 2 | a8b77e258 | general-purpose | opus-5 | 09-07T15:20 | 09-07T15:47 | 24 | 8,392 | 5.87 | ARCH polish round 1 (QA-02) |
| 3 | a5cd2082e | general-purpose | opus-5 | 09-08T03:02 | 09-08T05:41 | 143 | 44,522 | 45.13 | Materials round 6 (Opus xhigh) |
| 3 | ab779a51b | general-purpose | opus-5 | 09-08T06:24 | 09-08T07:55 | 143 | 66,668 | 41.56 | Environment round 7 (Opus) |
| 3 | a5d54c0c3 | general-purpose | opus-5 | 09-08T03:01 | 09-08T05:46 | 131 | 40,108 | 40.87 | Lighting round 11 (Opus) |
| 3 | a626ed666 | general-purpose | opus-5 | 09-07T22:20 | 09-08T02:04 | 115 | 16,431 | 37.83 | Lighting round 10 (Opus) |
| 3 | ab8728bd7 | general-purpose | opus-5 | 09-07T20:44 | 09-07T22:50 | 124 | 36,431 | 29.00 | Ornament polish round 2 (Opus xhigh) |
| 3 | a51334cdb | general-purpose | opus-5 | 09-08T03:02 | 09-08T05:19 | 116 | 24,315 | 27.74 | Environment round 6 (Opus) |
| 3 | a13969ad1 | general-purpose | opus-5 | 09-07T22:52 | 09-08T02:01 | 100 | 13,642 | 25.08 | Environment round 5 (Opus) |
| 3 | a3617fb82 | general-purpose | opus-5 | 09-07T18:14 | 09-07T20:17 | 52 | 11,092 | 19.55 | Lighting polish round 2 (Opus) |
| 3 | ad1f5eecc | general-purpose | opus-5 | 09-07T20:44 | 09-07T22:10 | 159 | 27,161 | 19.53 | Environment polish round 2 (Opus) |
| 3 | aff2fc3b4 | general-purpose | opus-5 | 09-08T06:24 | 09-08T07:56 | 116 | 15,620 | 18.56 | Architecture round 4 (Opus) |
| 3 | a1ce8866f | general-purpose | opus-5 | 09-07T20:43 | 09-07T22:38 | 117 | 21,172 | 17.79 | Architecture polish round 2 (Opus) |
| 3 | a6b3a75a3 | general-purpose | opus-5 | 09-07T22:51 | 09-08T00:07 | 106 | 22,073 | 16.69 | Materials round 5 (Opus xhigh) |
| 3 | a58e29625 | general-purpose | fable-5-1 | 09-08T02:10 | 09-08T02:58 | 96 | 7,882 | 12.96 | QA round 4 critic (Fable, xhigh) |
| 3 | a2cc93614 | general-purpose | opus-5 | 09-07T20:43 | 09-07T22:10 | 81 | 6,884 | 11.65 | Materials polish round 2 (Opus xhigh) |
| 3 | a7ea51138 | general-purpose | opus-5 | 09-08T06:23 | 09-08T07:56 | 41 | 5,957 | 11.47 | Lighting round 12 (Opus) |
| 3 | ae7e8d18f | general-purpose | fable-5-1 | 09-07T18:13 | 09-07T18:49 | 30 | 8,898 | 8.82 | QA round 3 critic (Fable, xhigh) |
| 3 | a6a9959c5 | general-purpose | fable-5-1 | 09-08T05:48 | 09-08T07:56 | 38 | 2,950 | 7.72 | QA round 5 critic (Fable, xhigh) |
| 3 | a738f1851 | general-purpose | opus-5 | 09-08T03:02 | 09-08T03:31 | 61 | 8,830 | 7.00 | Architecture mini-round (Opus) |
| 4 | ad1161fe1 | general-purpose | opus-5 | 09-09T12:35 | 09-09T14:23 | 62 | 23,982 | 26.19 | LIGHT r14 violet flood |
| 4 | aacaefe7e | general-purpose | opus-5 | 09-09T07:22 | 09-09T09:31 | 69 | 19,271 | 24.30 | MAT r7 stone, water, paving |
| 4 | afdc30487 | general-purpose | opus-5 | 09-09T07:14 | 09-09T09:03 | 74 | 17,941 | 20.44 | ENV r8 cluster re-derive |
| 4 | abc4cd70b | general-purpose | opus-5 | 09-09T05:46 | 09-09T07:20 | 62 | 27,038 | 18.85 | LIGHT r12 shade window |
| 4 | af1b0769a | general-purpose | opus-5 | 09-09T10:05 | 09-09T11:27 | 95 | 24,186 | 16.15 | LIGHT r13 Eevee shade, mist |
| 4 | aeef51ec8 | general-purpose | opus-5 | 09-09T11:36 | 09-09T12:19 | 47 | 16,416 | 11.36 | QA round 6 gate |
| 4 | a19799835 | general-purpose | opus-5 | 09-09T15:28 | 09-09T15:54 | 60 | 13,965 | 9.87 | QA round 7 gate |
| 4 | a5200bed5 | general-purpose | opus-5 | 09-09T13:27 | 09-09T14:08 | 41 | 14,216 | 9.81 | ARCH r7 archivolt sockets, no render |
| 4 | a98691460 | general-purpose | opus-5 | 09-09T12:30 | 09-09T13:01 | 42 | 14,148 | 9.45 | ENV r9 walk clearance, no render |
| 4 | ab40c83dd | general-purpose | opus-5 | 09-09T05:47 | 09-09T07:01 | 22 | 9,950 | 8.20 | ENV r7 build and render |
| 4 | a0ac52855 | general-purpose | opus-5 | 09-09T11:59 | 09-09T12:28 | 73 | 9,410 | 7.82 | LIGHT r14 prep flythrough, no render |
| 4 | ac52dfbd9 | general-purpose | opus-5 | 09-09T14:30 | 09-09T15:20 | 75 | 7,672 | 7.61 | MAT r8 water blocker |
| 4 | a22519a1a | general-purpose | opus-5 | 09-09T12:23 | 09-09T12:49 | 43 | 10,185 | 7.40 | ARCH r6 register the stack |
| 4 | a0c03a96c | general-purpose | opus-5 | 09-09T06:40 | 09-09T07:13 | 24 | 9,164 | 7.38 | ENV r7 review fixes |
| 4 | ad9506f5f | general-purpose | opus-5 | 09-09T12:58 | 09-09T13:26 | 28 | 10,480 | 7.15 | ORN r6 refit to new stack |
| 4 | a294b6960 | general-purpose | opus-5 | 09-09T11:59 | 09-09T12:17 | 41 | 7,736 | 5.93 | ARCH r5 UVProj, no render |
| 4 | a1eb4bc3d | general-purpose | opus-5 | 09-09T12:00 | 09-09T12:20 | 47 | 5,783 | 5.16 | ORN r5 frieze band, no render |
| 5 | a3a4e0439 | general-purpose | opus-5 | 09-09T19:03 | 09-09T20:18 | 151 | 20,178 | 20.66 | Materials round 9 builder |
| 5 | ae9b7d57f | general-purpose | opus-5 | 09-10T05:12 | 09-10T06:38 | 109 | 20,565 | 19.46 | Lighting round 17 builder |
| 5 | aed5d7347 | general-purpose | opus-5 | 09-10T07:12 | 09-10T08:07 | 78 | 26,118 | 16.56 | Lighting round 18 fill fix |
| 5 | a0566941a | general-purpose | opus-5 | 09-09T21:35 | 09-09T22:33 | 87 | 14,512 | 12.41 | Lighting round 16 builder |
| 5 | a3a0a1dbd | general-purpose | opus-5 | 09-09T17:44 | 09-09T18:55 | 82 | 8,093 | 11.81 | Lighting round 15 builder |
| 5 | a0fa32648 | general-purpose | opus-5 | 09-09T20:26 | 09-09T20:54 | 83 | 12,158 | 9.54 | Materials round 9b fix |
| 5 | a133676dd | general-purpose | opus-5 | 09-10T04:40 | 09-10T05:05 | 55 | 11,790 | 8.48 | Architecture round 8 vault fix |
| 5 | ad77e40f0 | general-purpose | opus-5 | 09-09T21:02 | 09-09T21:33 | 62 | 8,326 | 7.28 | QA round 08 critic |
| 5 | a83df7f1c | general-purpose | opus-5 | 09-09T22:39 | 09-09T23:10 | 49 | 7,921 | 6.52 | QA round 09 critic |
| 5 | a7e68bea5 | general-purpose | opus-5 | 09-09T19:06 | 09-09T19:22 | 58 | 6,060 | 5.48 | Phase 5 cleanup + flythrough plan |
| 5 | aabeb619c | general-purpose | opus-5 | 09-10T06:46 | 09-10T07:11 | 45 | 6,045 | 5.44 | QA round 10 hero tiles |
| 8 | a1c9d5b70 | general-purpose | opus-5 | 09-15T09:58 | 09-15T17:56 | 329 | 84,265 | 92.66 | Gate 1 export engineer (Opus high) |
| 8 | a0547b30a | general-purpose | opus-5 | 09-15T14:59 | 09-15T19:41 | 308 | 93,362 | 76.55 | Gate 2 viewer engineer r3 (Opus high) |
| 8 | a97ad170e | general-purpose | opus-5 | 09-15T14:59 | 09-15T19:38 | 275 | 59,503 | 69.35 | Gate 2 bake engineer r2 (Opus xhigh) |
| 8 | a8f5d528f | general-purpose | opus-5 | 09-15T08:16 | 09-15T09:50 | 179 | 39,072 | 32.35 | Gate 0 viewer engineer (Opus high) |
| 8 | ae7c200ab | general-purpose | opus-5 | 09-15T09:58 | 09-15T12:32 | 185 | 26,666 | 29.50 | Materials r10: dome cap + coffer (Opus xhigh) |
| 8 | a48266d83 | general-purpose | opus-5 | 09-15T08:15 | 09-15T09:48 | 210 | 28,536 | 26.82 | Gate 0 bake engineer (Opus xhigh) |
| 8 | a2e9b4615 | general-purpose | opus-5 | 09-15T09:58 | 09-15T11:01 | 111 | 17,036 | 18.46 | Gate 1 viewer engineer r2 (Opus high) |
| 8 | a76617896 | general-purpose | opus-5 | 09-15T13:32 | 09-15T13:54 | 91 | 10,191 | 8.52 | QA round 11b: Gate 1 re-check (Opus xhigh) |
| 8 | afe967a74 | general-purpose | opus-5 | 09-15T12:43 | 09-15T12:59 | 62 | 8,829 | 7.03 | QA round 11: Gate 1 geometry check (Opus xhigh) |
| 8 | af101b740 | general-purpose | opus-5 | 09-15T14:12 | 09-15T14:31 | 75 | 8,324 | 7.02 | QA round 11c: Gate 1 final re-check (Opus xhigh) |
| 8 | a186f187b | general-purpose | opus-5 | 09-15T14:42 | 09-15T14:58 | 66 | 8,325 | 6.70 | QA round 11d: Gate 1 re-check (Opus xhigh) |
| 8 | adbd17ca1 | general-purpose | opus-5 | 09-15T17:09 | 09-15T17:26 | 63 | 6,931 | 6.06 | QA round 12: Gate 2 materials check (Opus xhigh) |
| 8 | afe3651bf | general-purpose | opus-5 | 09-15T19:42 | 09-15T19:55 | 55 | 7,201 | 5.90 | QA round 12b: Gate 2 re-check (Opus xhigh) |
