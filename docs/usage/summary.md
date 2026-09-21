# Token usage summary (from Claude Code transcripts)

Generated 2026-09-21T20:42:41Z by `docs/usage/usage_from_transcripts.py` from `/Users/dk/.claude/projects/-Users-dk-Projects-3d-render-blender-3rd-attempt-building` (18 main sessions, 254 subagent transcripts). Usage is deduplicated by API message id. Tokens in thousands (k) unless stated.

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
| claude-opus-5 | 20522 | 41 | 12,084 | 5,101 | 0 | 142,776 | 4,043,126 | 3,216.22 |
| claude-fable-5-1 | 3078 | 73 | 2,969 | 954 | 15,120 | 11,613 | 751,430 | 784.59 |
| claude-sonnet-5 | 152 | 0 | 72 | 31 | 0 | 694 | 11,318 | 4.71 |
| <synthetic> | 30 | 0 | 0 | 0 | 0 | 0 | 0 | 0.00 |

**Grand total nominal cost: $4,005.52**

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
| 8 | 6460c313 | 2026-09-15T07:49 | 2026-09-16T06:48 | 22.99 | 317 | 21 | 586.08 | opus-5 517, fable-5-1 69 |
| 9 | 52e90d0f | 2026-09-15T08:18 | 2026-09-15T08:20 | 0.03 | 3 | 0 | 0.82 |  |
| 10 | c47a8492 | 2026-09-16T06:49 | 2026-09-16T11:51 | 5.03 | 46 | 4 | 46.70 | opus-5 42, fable-5-1 5 |
| 11 | 87d95e57 | 2026-09-16T11:51 | 2026-09-16T15:45 | 3.89 | 181 | 12 | 217.93 | opus-5 199, fable-5-1 19 |
| 12 | 5b1d192d | 2026-09-16T20:31 | 2026-09-17T06:56 | 10.41 | 167 | 11 | 179.50 | opus-5 154, fable-5-1 25 |
| 13 | 4133edbe | 2026-09-17T06:56 | 2026-09-17T11:12 | 4.27 | 149 | 18 | 259.54 | opus-5 239, fable-5-1 18, sonnet-5 2 |
| 14 | 3ada03f9 | 2026-09-17T21:16 | 2026-09-19T19:15 | 45.98 | 333 | 21 | 474.88 | opus-5 377, fable-5-1 97 |
| 15 | a87300f7 | 2026-09-19T16:07 | 2026-09-20T06:10 | 14.06 | 242 | 20 | 387.06 | opus-5 347, fable-5-1 39 |
| 16 | d073013c | 2026-09-20T06:10 | 2026-09-20T07:44 | 1.58 | 71 | 5 | 56.26 | opus-5 49, fable-5-1 7 |
| 17 | e93f113b | 2026-09-20T07:45 | 2026-09-21T20:01 | 36.27 | 243 | 28 | 279.27 | opus-5 231, fable-5-1 48 |
| 18 | 6cfdbe19 | 2026-09-21T20:08 | 2026-09-21T20:42 | 0.57 | 81 | 0 | 19.92 | fable-5-1 20 |

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
| 8 6460c313 | 766.31 | 10.61 | 15.13 | 11640/315 | 586.08 |
| 9 52e90d0f | 0.82 | 0.01 | 0.0 | 0/0 | 0.82 |
| 10 c47a8492 | 59.76 | 1.34 | 0.13 | 1644/91 | 46.70 |
| 11 87d95e57 | 293.52 | 5.3 | 1.14 | 4532/434 | 217.93 |
| 12 5b1d192d | 258.74 | 6.39 | 3.02 | 5425/341 | 179.50 |
| 13 4133edbe | 338.31 | 6.03 | 0.99 | 4989/669 | 259.54 |
| 14 3ada03f9 | 643.60 | 9.68 | 1.68 | 10589/1084 | 474.88 |
| 16 d073013c | 83.09 | 1.86 | 0.44 | 467/1 | 56.26 |
| 17 e93f113b | 378.02 | 7.24 | 2.06 | 6738/933 | 279.27 |
| total | 4,594.56 | | | | 4,005.52 |

## Daily nominal cost (this project only, UTC)

| day | cost USD | fable-5-1 | opus-5 | other |
|---|---|---|---|---|
| 2026-09-06 | 57.75 | 57.75 | 0.00 | 0.00 |
| 2026-09-07 | 602.56 | 194.65 | 407.91 | -0.00 |
| 2026-09-08 | 298.82 | 55.81 | 243.01 | 0.00 |
| 2026-09-09 | 401.76 | 50.22 | 350.64 | 0.90 |
| 2026-09-10 | 130.25 | 70.93 | 59.32 | 0.00 |
| 2026-09-15 | 521.86 | 54.86 | 467.00 | 0.00 |
| 2026-09-16 | 453.91 | 54.95 | 398.97 | -0.00 |
| 2026-09-17 | 325.17 | 37.70 | 285.13 | 2.34 |
| 2026-09-18 | 203.96 | 28.91 | 175.05 | -0.00 |
| 2026-09-19 | 644.47 | 94.01 | 549.54 | 0.92 |
| 2026-09-20 | 143.70 | 24.96 | 118.19 | 0.55 |
| 2026-09-21 | 221.31 | 59.84 | 161.46 | 0.00 |

## Subagents per session (by model, count and cost)

- Session 1 (db75376f): 6 x <synthetic>,fable-5-1 ($163); 4 x fable-5-1 ($19). Types: {'general-purpose': 10}
- Session 2 (747b5259): 11 x opus-5 ($265). Types: {'general-purpose': 11}
- Session 3 (f6551679): 27 x opus-5 ($386); 3 x fable-5-1 ($30). Types: {'general-purpose': 30}
- Session 4 (1e741676): 40 x opus-5 ($266). Types: {'general-purpose': 40}
- Session 5 (c1c6cc77): 22 x opus-5 ($144); 1 x sonnet-5 ($1). Types: {'general-purpose': 23}
- Session 6 (797d734e): . Types: {}
- Session 7 (11484ff4): . Types: {}
- Session 8 (6460c313): 21 x opus-5 ($517). Types: {'general-purpose': 21}
- Session 9 (52e90d0f): . Types: {}
- Session 10 (c47a8492): 4 x opus-5 ($42). Types: {'general-purpose': 4}
- Session 11 (87d95e57): 12 x opus-5 ($199). Types: {'general-purpose': 12}
- Session 12 (5b1d192d): 11 x opus-5 ($154). Types: {'general-purpose': 11}
- Session 13 (4133edbe): 16 x opus-5 ($239); 2 x sonnet-5 ($2). Types: {'general-purpose': 18}
- Session 14 (3ada03f9): 20 x opus-5 ($377); 1 x sonnet-5 ($0). Types: {'general-purpose': 21}
- Session 15 (a87300f7): 19 x opus-5 ($347); 1 x sonnet-5 ($1). Types: {'general-purpose': 20}
- Session 16 (d073013c): 4 x opus-5 ($36); 1 x <synthetic>,opus-5 ($13). Types: {'general-purpose': 5}
- Session 17 (e93f113b): 27 x opus-5 ($231); 1 x sonnet-5 ($1). Types: {'general-purpose': 27, 'Explore': 1}
- Session 18 (6cfdbe19): . Types: {}

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
| 8 | - | - | - | 1 ($30) | - | - | 6 ($41) | 7 ($23) | - | 7 ($424) | 21 ($517) |
| 9 | - | - | - | - | - | - | - | - | - | - | 0 ($0) |
| 10 | - | - | - | - | - | - | - | - | - | 4 ($42) | 4 ($42) |
| 11 | - | - | - | - | - | 1 ($103) | 2 ($17) | 7 ($21) | - | 2 ($57) | 12 ($199) |
| 12 | - | - | - | - | - | - | 1 ($7) | 3 ($6) | - | 7 ($141) | 11 ($154) |
| 13 | 1 ($1) | - | - | - | - | - | 2 ($19) | 3 ($7) | - | 12 ($215) | 18 ($241) |
| 14 | - | - | - | - | 1 ($10) | - | 4 ($37) | 7 ($20) | - | 9 ($311) | 21 ($378) |
| 15 | - | - | - | - | - | 1 ($24) | - | 7 ($26) | - | 12 ($298) | 20 ($348) |
| 16 | - | - | - | - | - | 1 ($4) | - | 1 ($2) | - | 3 ($42) | 5 ($49) |
| 17 | - | - | - | - | 1 ($38) | 1 ($16) | 2 ($14) | 9 ($23) | - | 15 ($140) | 28 ($231) |
| 18 | - | - | - | - | - | - | - | - | - | - | 0 ($0) |
| all | 5 ($25) | 12 ($126) | 9 ($126) | 12 ($246) | 14 ($347) | 19 ($462) | 28 ($228) | 82 ($193) | 2 ($6) | 71 ($1671) | 254 ($3432) |

Lead (main thread) cost per session, same rates: session 1 $33, session 2 $16, session 3 $48, session 4 $37, session 5 $60, session 6 $30, session 7 $1, session 8 $69, session 9 $1, session 10 $5, session 11 $19, session 12 $25, session 13 $18, session 14 $97, session 15 $39, session 16 $7, session 17 $48, session 18 $20.

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
| 8 | ac0a24990 | general-purpose | opus-5 | 09-15T19:56 | 09-16T03:33 | 212 | 27,285 | 107.85 | Gate 3 bake engineer r3 (Opus xhigh) |
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
| 10 | ab7a668c0 | general-purpose | opus-5 | 09-16T06:52 | 09-16T07:21 | 114 | 26,330 | 17.97 | Gate 4 viewer round |
| 10 | a62ae3479 | general-purpose | opus-5 | 09-16T06:52 | 09-16T07:20 | 101 | 17,818 | 13.96 | Export Gate 3 UV2/COLOR_0 re-export |
| 10 | a765607a7 | general-purpose | opus-5 | 09-16T07:05 | 09-16T07:17 | 54 | 5,596 | 5.04 | Gate 3 bake review fixes |
| 11 | a8f986e98 | general-purpose | opus-5 | 09-16T11:53 | 09-16T15:29 | 442 | 154,373 | 103.42 | Viewer engineer: lightmap debug, capture, items 2-7 |
| 11 | a8c5028be | general-purpose | opus-5 | 09-16T11:53 | 09-16T15:28 | 146 | 34,479 | 31.40 | Export engineer: Gate 3 COLOR_0 + 988 placements |
| 11 | ac740cdd8 | general-purpose | opus-5 | 09-16T13:12 | 09-16T15:29 | 139 | 23,990 | 25.65 | Bake engineer: rotunda ceiling re-bake |
| 11 | a945eb6bf | general-purpose | opus-5 | 09-16T12:44 | 09-16T13:09 | 87 | 12,073 | 9.59 | QA round 13: lightmaps alone |
| 11 | a3688d82c | general-purpose | opus-5 | 09-16T14:46 | 09-16T15:03 | 71 | 8,113 | 7.08 | QA round 14: Gate 4 |
| 12 | af95ec134 | general-purpose | opus-5 | 09-16T20:34 | 09-16T23:18 | 20 | 65,693 | 53.86 | Viewer water murk and tile |
| 12 | a965d8a7b | general-purpose | opus-5 | 09-16T21:34 | 09-16T22:49 | 36 | 29,989 | 19.95 | Export instance irradiance manifest |
| 12 | a0a857ca7 | general-purpose | opus-5 | 09-17T05:28 | 09-17T06:19 | 38 | 33,505 | 19.78 | 6c viewer: leaf shader, runtime LOD |
| 12 | a04ee4a2d | general-purpose | opus-5 | 09-16T20:34 | 09-16T22:41 | 29 | 13,877 | 18.42 | Bake per-placement shrub irradiance |
| 12 | a0104e867 | general-purpose | opus-5 | 09-17T05:28 | 09-17T06:18 | 33 | 29,778 | 17.96 | 6c export: far-tree LOD2, leaf 2K, shrub LOD1 |
| 12 | a2de76438 | general-purpose | opus-5 | 09-17T05:28 | 09-17T05:54 | 26 | 12,376 | 8.13 | 6c bake: impostor diagnosis, tree AO |
| 12 | ae2445890 | general-purpose | opus-5 | 09-16T23:04 | 09-16T23:23 | 32 | 10,723 | 7.32 | QA round 15 critic |
| 13 | a73718fbf | general-purpose | opus-5 | 09-17T07:01 | 09-17T08:55 | 291 | 103,934 | 73.69 | 6c viewer engineer round 2 |
| 13 | ad667cdf5 | general-purpose | opus-5 | 09-17T09:22 | 09-17T10:39 | 191 | 54,285 | 36.34 | 6c viewer engineer round 3 |
| 13 | a70741aaf | general-purpose | opus-5 | 09-17T07:00 | 09-17T08:25 | 164 | 40,328 | 31.14 | 6c export engineer round 2 |
| 13 | a36dbe3d7 | general-purpose | opus-5 | 09-17T07:00 | 09-17T08:17 | 168 | 33,460 | 30.17 | 6c bake engineer round 2 |
| 13 | a38ad9555 | general-purpose | opus-5 | 09-17T09:21 | 09-17T09:55 | 125 | 23,240 | 16.59 | 6c export engineer round 3 |
| 13 | a2eadf2f7 | general-purpose | opus-5 | 09-17T08:56 | 09-17T09:20 | 93 | 12,660 | 10.21 | QA round 16 critic |
| 13 | a61a5d269 | general-purpose | opus-5 | 09-17T10:40 | 09-17T10:59 | 56 | 11,848 | 8.58 | QA round 17 critic |
| 13 | adfd1a0b5 | general-purpose | opus-5 | 09-17T08:37 | 09-17T08:50 | 47 | 8,743 | 6.61 | Delta review phase6-viewer r2 |
| 13 | ab1172b84 | general-purpose | opus-5 | 09-17T10:16 | 09-17T10:26 | 41 | 7,641 | 5.77 | Delta review phase6-viewer r3 |
| 14 | a315c5315 | general-purpose | opus-5 | 09-18T15:01 | 09-18T17:25 | 139 | 172,887 | 107.84 | 6b viewer: progressive load + deploy |
| 14 | a642069f1 | general-purpose | opus-5 | 09-19T10:30 | 09-19T12:46 | 49 | 96,553 | 66.12 | 8c analysis: column texel budget |
| 14 | af59030b9 | general-purpose | opus-5 | 09-19T10:40 | 09-19T13:08 | 45 | 78,720 | 56.77 | 8b viewer: alpha as coverage |
| 14 | a7e959e61 | general-purpose | opus-5 | 09-18T15:01 | 09-18T17:09 | 62 | 60,804 | 42.24 | 6b export: tiers + mobile manifest |
| 14 | a27cf99ae | general-purpose | opus-5 | 09-19T06:52 | 09-19T07:39 | 20 | 39,561 | 24.21 | Phase 7 viewer: foliage look |
| 14 | a8085303b | general-purpose | opus-5 | 09-19T12:39 | 09-19T13:05 | 39 | 19,952 | 12.60 | QA round 20: Phase 8 items on the URL |
| 14 | aba2901e8 | general-purpose | opus-5 | 09-18T17:22 | 09-18T17:48 | 70 | 15,446 | 10.96 | QA round 18b: closing 6b round |
| 14 | ac3f3ceb7 | general-purpose | opus-5 | 09-19T10:30 | 09-19T10:54 | 33 | 14,816 | 9.70 | 8a ENV: denser shrub cards |
| 14 | aa70c37e8 | general-purpose | opus-5 | 09-19T12:14 | 09-19T12:38 | 36 | 11,234 | 7.90 | 8b band-atlas bake |
| 14 | ad5ef488d | general-purpose | opus-5 | 09-18T16:49 | 09-18T17:06 | 21 | 11,004 | 7.44 | QA round 18: Gate 5 on the URL |
| 14 | ae3782120 | general-purpose | opus-5 | 09-19T07:44 | 09-19T07:56 | 18 | 8,326 | 5.58 | QA round 19: Phase 7 closing |
| 15 | a8e341307 | general-purpose | opus-5 | 09-19T16:31 | 09-19T21:42 | 187 | 311,167 | 192.01 | 8e mobile leaf-card analysis |
| 15 | a30fcad8c | general-purpose | opus-5 | 09-19T16:12 | 09-19T19:10 | 96 | 30,657 | 26.44 | 8d backdrop analysis (Part 0) |
| 15 | ab8bf6931 | general-purpose | opus-5 | 09-19T17:06 | 09-19T18:00 | 102 | 34,582 | 24.00 | 8a shrub relight stage 1 (code) |
| 15 | afc7ec379 | general-purpose | opus-5 | 09-19T19:14 | 09-19T21:18 | 65 | 30,574 | 23.41 | 8d belt r2: real crowns |
| 15 | a69699cec | general-purpose | opus-5 | 09-19T16:10 | 09-19T17:05 | 71 | 26,652 | 18.80 | Viewer fix round 8b |
| 15 | a4bb5af97 | general-purpose | opus-5 | 09-19T18:57 | 09-19T19:12 | 13 | 10,416 | 6.75 | QA 22 on gate10 capture |
| 15 | a26825723 | general-purpose | opus-5 | 09-19T16:10 | 09-19T16:29 | 22 | 9,746 | 6.69 | 8a shrub re-scope analysis |
| 15 | a1c7d613f | general-purpose | opus-5 | 09-19T16:10 | 09-19T16:23 | 27 | 9,533 | 6.64 | QA 21 on gate9 capture |
| 15 | a48964764 | general-purpose | opus-5 | 09-19T21:23 | 09-19T21:36 | 28 | 7,425 | 5.58 | QA 23 on gate11 capture |
| 15 | ace92e560 | general-purpose | opus-5 | 09-19T20:51 | 09-19T21:05 | 57 | 6,165 | 5.44 | Delta review chain r2 fixes |
| 16 | a4ea7aa98 | general-purpose | opus-5 | 09-20T06:18 | 09-20T07:10 | 2 | 31,776 | 17.94 | Phase 9 export belt rule (CPU) |
| 16 | a22b6e5a0 | general-purpose | <synthetic>,opus-5 | 09-20T06:18 | 09-20T07:10 | 14 | 19,937 | 13.37 | Phase 9 viewer dotted rim (CPU) |
| 16 | a2d92d06d | general-purpose | opus-5 | 09-20T06:18 | 09-20T06:46 | 1 | 18,384 | 11.00 | Phase 9 bake analysis (CPU) |
| 17 | ac38f97c4 | general-purpose | opus-5 | 09-21T04:51 | 09-21T16:02 | 24 | 52,395 | 39.14 | Phase 9 re-bake chain (GPU) |
| 17 | ae4e07420 | general-purpose | opus-5 | 09-21T16:09 | 09-21T17:18 | 37 | 66,587 | 38.46 | ENV aerial-blocks round (Blender) |
| 17 | a59829f04 | general-purpose | opus-5 | 09-21T17:18 | 09-21T18:16 | 36 | 47,319 | 29.26 | Backdrop export + viewer round |
| 17 | a8dec1a80 | general-purpose | opus-5 | 09-21T04:51 | 09-21T05:35 | 57 | 29,617 | 18.19 | Viewer shade r2 build (CPU) |
| 17 | a9bd5a191 | general-purpose | opus-5 | 09-20T07:49 | 09-20T09:24 | 4 | 15,384 | 15.94 | Lighting round 19, corrected premise |
| 17 | ad9150efa | general-purpose | opus-5 | 09-20T08:27 | 09-20T08:50 | 26 | 23,242 | 13.94 | Viewer shade: specular gating build |
| 17 | a06e637e1 | general-purpose | opus-5 | 09-21T16:09 | 09-21T16:28 | 42 | 10,796 | 7.78 | QA round 25 gate on deploy 13 |
| 17 | abc5a8531 | general-purpose | opus-5 | 09-20T08:10 | 09-20T08:22 | 20 | 11,541 | 7.33 | Export r2: review blocker and fix-now |
| 17 | abda29b01 | general-purpose | opus-5 | 09-21T18:28 | 09-21T18:44 | 25 | 8,989 | 6.34 | QA round 26 on deploy 14 |
| 17 | a1ed14712 | general-purpose | opus-5 | 09-20T07:50 | 09-20T08:01 | 23 | 9,562 | 6.30 | Finish and report phase9-export |
| 17 | a140d5dbb | general-purpose | opus-5 | 09-21T18:02 | 09-21T18:20 | 2 | 9,208 | 5.62 | Backdrop tiles capture (Chrome) |
| 17 | a75b08dec | general-purpose | opus-5 | 09-20T09:26 | 09-20T09:40 | 9 | 8,552 | 5.33 | Viewer capture window (Chrome) |
