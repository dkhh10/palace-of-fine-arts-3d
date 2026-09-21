# Phase 6 audit tables (generated 2026-09-21T22:29:33 by docs/usage/phase6_audit.py from turns_all.json; local time +02:00)

## Wall clock per window (hours; partition priority agent work > GPU busy > waiting on user > idle)

| window | span | wall | agent work | GPU busy, no agent | GPU busy total (overlaps) | waiting on user | idle | subagents | sum of subagent lifetimes | requests | cost USD |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Gate 0 vertical slice | 09-15 09:43 -> 09-15 11:50 | 2.12 | 1.95 | 0.0 | 1.6 | 0.1 | 0.07 | 4 | 3.37 | 436 | 78 |
| Gate 1 geometry freeze | 09-15 11:50 -> 09-15 16:58 | 5.13 | 5.08 | 0.05 | 2.97 | 0.0 | 0.0 | 11 | 10.22 | 989 | 176 |
| Gate 2 material bake | 09-15 16:58 -> 09-15 21:55 | 4.95 | 4.4 | 0.55 | 4.7 | 0.0 | 0.0 | 8 | 13.1 | 826 | 202 |
| Gate 3 lightmap bake | 09-15 21:55 -> 09-16 15:09 | 17.23 | 9.5 | 0.03 | 7.7 | 3.23 | 4.47 | 12 | 12.36 | 1125 | 259 |
| Gate 4 viewer (6a) | 09-16 15:09 -> 09-17 01:23 | 10.23 | 4.68 | 0.0 | 2.5 | 0.0 | 5.55 | 17 | 14.81 | 1438 | 254 |
| 6c foliage pass | 09-17 01:23 -> 09-17 12:56 | 11.55 | 5.2 | 0.0 | 4.03 | 5.77 | 0.58 | 22 | 10.7 | 2176 | 322 |
| 6b web deployment (+6d) | 09-17 12:56 -> 09-19 00:00 | 35.07 | 3.48 | 0.0 | 1.43 | 20.78 | 10.8 | 9 | 5.73 | 1074 | 209 |
| Phase 7 foliage look | 09-19 00:00 -> 09-19 09:56 | 9.93 | 1.15 | 0.03 | 0.87 | 8.72 | 0.03 | 3 | 1.07 | 311 | 44 |
| Phase 8 (beyond Phase 6, same day) | 09-19 09:56 -> 09-20 00:00 | 14.07 | 8.57 | 0.17 | 3.18 | 2.45 | 2.88 | 31 | 21.4 | 3432 | 599 |

## Waits by role and kind per window (hours, overlapping)

- Gate 0 vertical slice: lead | waiting on agents 0.76; lead | idle until user returned 0.27; viewer engineer | idle until user returned 0.19; bake engineer | idle until user returned 0.13; lead | waiting on user 0.12
- Gate 1 geometry freeze: lead | waiting on agents 1.87; export engineer | idle until user returned 1.23; lead | idle until user returned 0.9; materials | other wait 0.67; viewer engineer | idle until user returned 0.15; materials | idle until user returned 0.13
- Gate 2 material bake: export engineer | idle until user returned 2.17; viewer engineer | idle until user returned 1.79; lead | waiting on agents 1.73; bake engineer | other wait 1.64; lead | idle until user returned 0.61; bake engineer | idle until user returned 0.57; viewer engineer | other wait 0.16
- Gate 3 lightmap bake: lead | waiting on agents 8.18; lead | idle until user returned 4.25; export engineer | idle until user returned 0.41; code reviewer | gpu wait 0.08; viewer engineer | other wait 0.07; QA critic | gpu wait 0.06; code reviewer | other wait 0.06
- Gate 4 viewer (6a): lead | waiting on agents 3.23; bake engineer | idle until user returned 1.0; viewer engineer | other wait 0.85; bake engineer | other wait 0.57; lead | idle until user returned 0.52; export engineer | other wait 0.51; viewer engineer | idle until user returned 0.45; export engineer | idle until user returned 0.26
- 6c foliage pass: lead | idle until user returned 7.8; lead | waiting on agents 1.95; export engineer | idle until user returned 0.63; viewer engineer | idle until user returned 0.41; bake engineer | idle until user returned 0.28; analysis/mechanical | other wait 0.15; lead | waiting on user 0.06; viewer engineer | other wait 0.05
- 6b web deployment (+6d): lead | waiting on user 17.56; lead | idle until user returned 3.47; lead | waiting on agents 2.58; export engineer | idle until user returned 0.85; viewer engineer | idle until user returned 0.3; viewer engineer | other wait 0.28; viewer engineer | waiting on user 0.09; export engineer | other wait 0.08
- Phase 7 foliage look: lead | idle until user returned 8.78; lead | waiting on agents 0.91
- Phase 8 (beyond Phase 6, same day): lead | idle until user returned 10.86; analysis/mechanical | idle until user returned 5.31; lead | waiting on agents 4.57; other | idle until user returned 1.14; viewer engineer | other wait 0.77; viewer engineer | idle until user returned 0.43; lighting | idle until user returned 0.17; analysis/mechanical | other wait 0.08

## Per day

| day | wall | agent work | GPU no agent | GPU total | waiting on user | idle | subagents started | human prompts | requests | output k | cache read M | cost USD |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-09-15 | 24.0 | 13.57 | 0.6 | 11.27 | 0.1 | 0.07 | 21 | 29 | 2370 | 2,632 | 545.9 | 495 |
| 2026-09-16 | 24.0 | 10.72 | 0.03 | 7.65 | 3.23 | 10.02 | 22 | 30 | 2105 | 1,767 | 414.3 | 416 |
| 2026-09-17 | 24.0 | 6.78 | 0.0 | 4.67 | 6.37 | 10.85 | 24 | 32 | 2568 | 1,749 | 515.8 | 390 |
| 2026-09-18 | 24.0 | 3.28 | 0.0 | 1.35 | 20.18 | 0.53 | 7 | 13 | 1025 | 432 | 308.5 | 204 |
| 2026-09-19 | 24.0 | 9.72 | 0.2 | 4.05 | 11.17 | 2.92 | 33 | 43 | 3743 | 1,489 | 924.6 | 644 |

## week: 2026-09-15 00:00 -> 2026-09-20 00:00

wall 120.0 h, agent work 44.07 h, GPU busy (no agent) 0.83 h, GPU busy total 28.98 h, waiting on user 41.05 h, idle 24.38 h; 11811 requests, output 8.07 M, thinking 2.96 M, cache read 2,709 M, cache write 90.7 M, cost $2,148; 107 subagents {'code reviewer': 46, 'viewer engineer': 13, 'analysis/mechanical': 8, 'export engineer': 9, 'QA critic': 19, 'bake engineer': 8, 'materials': 1, 'lighting': 1, 'other': 2}; models {'claude-opus-5': 103, 'claude-sonnet-5': 4}; human prompts 147; image-viewing requests 828; waits by kind {'idle until user returned': 65.14, 'waiting on agents': 25.76, 'waiting on user': 17.83, 'other wait': 5.94, 'gpu wait': 0.17}

| role | requests | output k | thinking k | cache read M | cache write M | cost USD | share |
|---|---|---|---|---|---|---|---|
| viewer engineer | 3040 | 1,969 | 650 | 905.4 | 22.09 | 640 | 30 % |
| analysis/mechanical | 1283 | 405 | 160 | 458.6 | 9.84 | 297 | 14 % |
| bake engineer | 1053 | 1,095 | 421 | 210.3 | 25.88 | 294 | 14 % |
| export engineer | 1510 | 1,028 | 370 | 335.5 | 13.14 | 276 | 13 % |
| lead | 1285 | 1,024 | 273 | 344.8 | 6.59 | 269 | 13 % |
| code reviewer | 1670 | 1,194 | 599 | 170.3 | 5.88 | 152 | 7 % |
| QA critic | 1454 | 992 | 326 | 189.6 | 3.59 | 142 | 7 % |
| materials | 146 | 185 | 99 | 26.7 | 1.85 | 30 | 1 % |
| other | 210 | 75 | 33 | 33.4 | 1.14 | 24 | 1 % |
| lighting | 160 | 102 | 29 | 34.6 | 0.67 | 24 | 1 % |

| model | requests | output k | thinking k | cache read M | cache write M | cost USD | share |
|---|---|---|---|---|---|---|---|
| claude-opus-5 | 10414 | 7,007 | 2,672 | 2,356.0 | 83.59 | 1,876 | 87 % |
| claude-fable-5-1 | 1283 | 1,024 | 273 | 344.8 | 6.59 | 269 | 13 % |
| claude-sonnet-5 | 112 | 38 | 16 | 8.3 | 0.49 | 3 | 0 % |
| <synthetic> | 2 | 0 | 0 | 0.0 | 0.00 | 0 | 0 % |

| activity | requests | output k | thinking k | cache read M | cache write M | cost USD | share |
|---|---|---|---|---|---|---|---|
| running scripts | 3406 | 2,314 | 915 | 826.2 | 20.91 | 611 | 28 % |
| reading files and logs | 3520 | 1,287 | 833 | 619.4 | 29.47 | 532 | 25 % |
| waiting on tools | 1444 | 1,087 | 403 | 428.9 | 25.15 | 396 | 18 % |
| editing files | 1820 | 2,575 | 510 | 429.9 | 9.89 | 343 | 16 % |
| reasoning and reporting | 563 | 109 | 22 | 173.0 | 2.70 | 117 | 5 % |
| viewing images | 828 | 484 | 237 | 167.7 | 1.66 | 109 | 5 % |
| coordination | 230 | 212 | 40 | 64.0 | 0.89 | 40 | 2 % |

| day | requests | output k | thinking k | cache read M | cache write M | cost USD | share |
|---|---|---|---|---|---|---|---|
| 2026-09-19 | 3743 | 1,489 | 521 | 924.6 | 21.11 | 644 | 30 % |
| 2026-09-15 | 2370 | 2,632 | 1,070 | 545.9 | 26.63 | 495 | 23 % |
| 2026-09-16 | 2105 | 1,767 | 646 | 414.3 | 23.38 | 416 | 19 % |
| 2026-09-17 | 2568 | 1,749 | 619 | 515.8 | 13.61 | 390 | 18 % |
| 2026-09-18 | 1025 | 432 | 105 | 308.5 | 5.95 | 204 | 9 % |

| role_model | requests | output k | thinking k | cache read M | cache write M | cost USD | share |
|---|---|---|---|---|---|---|---|
| viewer engineer | claude-opus-5 | 3040 | 1,969 | 650 | 905.4 | 22.09 | 640 | 30 % |
| analysis/mechanical | claude-opus-5 | 1208 | 376 | 147 | 453.1 | 9.45 | 295 | 14 % |
| bake engineer | claude-opus-5 | 1053 | 1,095 | 421 | 210.3 | 25.88 | 294 | 14 % |
| export engineer | claude-opus-5 | 1510 | 1,028 | 370 | 335.5 | 13.14 | 276 | 13 % |
| lead | claude-fable-5-1 | 1283 | 1,024 | 273 | 344.8 | 6.59 | 269 | 13 % |
| code reviewer | claude-opus-5 | 1670 | 1,194 | 599 | 170.3 | 5.88 | 152 | 7 % |
| QA critic | claude-opus-5 | 1454 | 992 | 326 | 189.6 | 3.59 | 142 | 7 % |
| materials | claude-opus-5 | 146 | 185 | 99 | 26.7 | 1.85 | 30 | 1 % |
| lighting | claude-opus-5 | 160 | 102 | 29 | 34.6 | 0.67 | 24 | 1 % |
| other | claude-opus-5 | 173 | 65 | 30 | 30.6 | 1.04 | 23 | 1 % |
| analysis/mechanical | claude-sonnet-5 | 75 | 29 | 13 | 5.5 | 0.38 | 2 | 0 % |
| other | claude-sonnet-5 | 37 | 9 | 3 | 2.8 | 0.10 | 1 | 0 % |
| lead | <synthetic> | 2 | 0 | 0 | 0.0 | 0.00 | 0 | 0 % |


## phase6_only_15_18: 2026-09-15 00:00 -> 2026-09-19 00:00

wall 96.0 h, agent work 34.35 h, GPU busy (no agent) 0.63 h, GPU busy total 24.93 h, waiting on user 29.88 h, idle 21.47 h; 8068 requests, output 6.58 M, thinking 2.44 M, cache read 1,784 M, cache write 69.6 M, cost $1,505; 74 subagents {'code reviewer': 32, 'viewer engineer': 10, 'analysis/mechanical': 3, 'export engineer': 8, 'QA critic': 13, 'bake engineer': 7, 'materials': 1}; models {'claude-opus-5': 71, 'claude-sonnet-5': 3}; human prompts 104; image-viewing requests 493; waits by kind {'idle until user returned': 38.45, 'waiting on agents': 20.29, 'waiting on user': 17.83, 'other wait': 5.09, 'gpu wait': 0.17}

| role | requests | output k | thinking k | cache read M | cache write M | cost USD | share |
|---|---|---|---|---|---|---|---|
| viewer engineer | 2421 | 1,833 | 620 | 760.5 | 18.27 | 540 | 36 % |
| bake engineer | 977 | 1,059 | 417 | 199.0 | 25.66 | 286 | 19 % |
| export engineer | 1409 | 995 | 360 | 320.7 | 12.91 | 266 | 18 % |
| lead | 954 | 749 | 200 | 231.0 | 4.05 | 176 | 12 % |
| QA critic | 1010 | 842 | 281 | 131.7 | 2.48 | 102 | 7 % |
| code reviewer | 1076 | 889 | 451 | 109.4 | 3.96 | 102 | 7 % |
| materials | 146 | 185 | 99 | 26.7 | 1.85 | 30 | 2 % |
| analysis/mechanical | 75 | 29 | 13 | 5.5 | 0.38 | 2 | 0 % |

| model | requests | output k | thinking k | cache read M | cache write M | cost USD | share |
|---|---|---|---|---|---|---|---|
| claude-opus-5 | 7039 | 5,803 | 2,227 | 1,547.9 | 65.13 | 1,326 | 88 % |
| claude-fable-5-1 | 952 | 749 | 200 | 231.0 | 4.05 | 176 | 12 % |
| claude-sonnet-5 | 75 | 29 | 13 | 5.5 | 0.38 | 2 | 0 % |
| <synthetic> | 2 | 0 | 0 | 0.0 | 0.00 | 0 | 0 % |

| activity | requests | output k | thinking k | cache read M | cache write M | cost USD | share |
|---|---|---|---|---|---|---|---|
| running scripts | 2382 | 1,930 | 756 | 574.9 | 15.34 | 434 | 29 % |
| reading files and logs | 2224 | 1,037 | 679 | 336.6 | 21.18 | 329 | 22 % |
| waiting on tools | 1122 | 977 | 368 | 309.3 | 23.18 | 322 | 21 % |
| editing files | 1273 | 2,029 | 404 | 301.1 | 6.46 | 246 | 16 % |
| reasoning and reporting | 403 | 83 | 15 | 118.5 | 1.51 | 74 | 5 % |
| viewing images | 493 | 363 | 190 | 102.6 | 1.12 | 71 | 5 % |
| coordination | 171 | 162 | 29 | 41.5 | 0.76 | 29 | 2 % |

| day | requests | output k | thinking k | cache read M | cache write M | cost USD | share |
|---|---|---|---|---|---|---|---|
| 2026-09-15 | 2370 | 2,632 | 1,070 | 545.9 | 26.63 | 495 | 33 % |
| 2026-09-16 | 2105 | 1,767 | 646 | 414.3 | 23.38 | 416 | 28 % |
| 2026-09-17 | 2568 | 1,749 | 619 | 515.8 | 13.61 | 390 | 26 % |
| 2026-09-18 | 1025 | 432 | 105 | 308.5 | 5.95 | 204 | 14 % |

| role_model | requests | output k | thinking k | cache read M | cache write M | cost USD | share |
|---|---|---|---|---|---|---|---|
| viewer engineer | claude-opus-5 | 2421 | 1,833 | 620 | 760.5 | 18.27 | 540 | 36 % |
| bake engineer | claude-opus-5 | 977 | 1,059 | 417 | 199.0 | 25.66 | 286 | 19 % |
| export engineer | claude-opus-5 | 1409 | 995 | 360 | 320.7 | 12.91 | 266 | 18 % |
| lead | claude-fable-5-1 | 952 | 749 | 200 | 231.0 | 4.05 | 176 | 12 % |
| QA critic | claude-opus-5 | 1010 | 842 | 281 | 131.7 | 2.48 | 102 | 7 % |
| code reviewer | claude-opus-5 | 1076 | 889 | 451 | 109.4 | 3.96 | 102 | 7 % |
| materials | claude-opus-5 | 146 | 185 | 99 | 26.7 | 1.85 | 30 | 2 % |
| analysis/mechanical | claude-sonnet-5 | 75 | 29 | 13 | 5.5 | 0.38 | 2 | 0 % |
| lead | <synthetic> | 2 | 0 | 0 | 0.0 | 0.00 | 0 | 0 % |


## phase5: 2026-09-06 12:00 -> 2026-09-10 16:00

wall 100.0 h, agent work 42.17 h, GPU busy (no agent) 4.78 h, GPU busy total 33.48 h, waiting on user 0.1 h, idle 52.95 h; 9099 requests, output 6.23 M, thinking 2.93 M, cache read 1,582 M, cache write 67.4 M, cost $1,483; 114 subagents {'code reviewer': 43, 'lighting': 14, 'QA critic': 16, 'ornament': 7, 'architecture': 10, 'environment': 9, 'materials': 9, 'phase 5 prep': 2, 'analysis/mechanical': 3, 'other': 1}; models {'claude-opus-5': 100, 'claude-sonnet-5': 1, 'claude-fable-5-1': 13}; human prompts 141; image-viewing requests 1075; waits by kind {'idle until user returned': 95.2, 'waiting on agents': 18.53, 'gpu wait': 1.26, 'waiting on user': 0.12, 'other wait': 0.07}

| role | requests | output k | thinking k | cache read M | cache write M | cost USD | share |
|---|---|---|---|---|---|---|---|
| lighting | 1573 | 1,095 | 555 | 272.0 | 18.38 | 284 | 19 % |
| QA critic | 1910 | 849 | 347 | 389.4 | 5.85 | 262 | 18 % |
| lead | 851 | 848 | 229 | 188.9 | 6.00 | 210 | 14 % |
| materials | 974 | 814 | 422 | 176.8 | 12.61 | 202 | 14 % |
| environment | 1087 | 776 | 380 | 202.7 | 9.33 | 184 | 12 % |
| architecture | 828 | 614 | 344 | 129.8 | 4.53 | 113 | 8 % |
| ornament | 618 | 372 | 182 | 114.4 | 4.84 | 108 | 7 % |
| code reviewer | 1106 | 691 | 393 | 91.6 | 4.14 | 89 | 6 % |
| analysis/mechanical | 61 | 70 | 26 | 7.3 | 1.27 | 21 | 1 % |
| phase 5 prep | 74 | 83 | 40 | 8.0 | 0.27 | 6 | 0 % |
| other | 17 | 16 | 8 | 1.1 | 0.16 | 3 | 0 % |

| model | requests | output k | thinking k | cache read M | cache write M | cost USD | share |
|---|---|---|---|---|---|---|---|
| claude-opus-5 | 7634 | 4,658 | 2,349 | 1,267.8 | 49.67 | 1,061 | 72 % |
| claude-fable-5-1 | 1414 | 1,545 | 562 | 312.3 | 17.61 | 421 | 28 % |
| claude-sonnet-5 | 25 | 25 | 15 | 1.9 | 0.11 | 1 | 0 % |
| <synthetic> | 26 | 0 | 0 | 0.0 | 0.00 | 0 | 0 % |

| activity | requests | output k | thinking k | cache read M | cache write M | cost USD | share |
|---|---|---|---|---|---|---|---|
| reading files and logs | 3307 | 1,362 | 961 | 495.1 | 19.04 | 433 | 29 % |
| running scripts | 1754 | 1,344 | 585 | 306.7 | 17.19 | 319 | 22 % |
| waiting on tools | 1412 | 949 | 474 | 264.2 | 14.29 | 263 | 18 % |
| editing files | 1099 | 1,429 | 350 | 205.4 | 10.20 | 223 | 15 % |
| viewing images | 1075 | 888 | 529 | 210.4 | 4.17 | 166 | 11 % |
| reasoning and reporting | 300 | 99 | 15 | 63.2 | 1.47 | 41 | 3 % |
| coordination | 152 | 156 | 13 | 36.9 | 1.02 | 38 | 3 % |

| day | requests | output k | thinking k | cache read M | cache write M | cost USD | share |
|---|---|---|---|---|---|---|---|
| 2026-09-07 | 3043 | 1,636 | 739 | 642.9 | 20.53 | 535 | 36 % |
| 2026-09-09 | 3247 | 2,129 | 1,075 | 452.5 | 16.53 | 386 | 26 % |
| 2026-09-08 | 1809 | 1,515 | 715 | 340.1 | 22.63 | 366 | 25 % |
| 2026-09-10 | 803 | 656 | 275 | 126.8 | 4.98 | 138 | 9 % |
| 2026-09-06 | 197 | 291 | 121 | 19.7 | 2.72 | 58 | 4 % |

| role_model | requests | output k | thinking k | cache read M | cache write M | cost USD | share |
|---|---|---|---|---|---|---|---|
| lighting | claude-opus-5 | 1519 | 1,045 | 530 | 263.3 | 17.36 | 266 | 18 % |
| QA critic | claude-opus-5 | 1737 | 647 | 251 | 366.3 | 4.30 | 226 | 15 % |
| lead | claude-fable-5-1 | 836 | 848 | 229 | 188.9 | 6.00 | 210 | 14 % |
| environment | claude-opus-5 | 1030 | 676 | 341 | 187.9 | 8.30 | 163 | 11 % |
| materials | claude-opus-5 | 899 | 740 | 382 | 156.1 | 9.80 | 158 | 11 % |
| code reviewer | claude-opus-5 | 1106 | 691 | 393 | 91.6 | 4.14 | 89 | 6 % |
| architecture | claude-opus-5 | 754 | 510 | 281 | 105.3 | 3.25 | 86 | 6 % |
| ornament | claude-opus-5 | 540 | 292 | 147 | 91.3 | 2.37 | 68 | 5 % |
| materials | claude-fable-5-1 | 72 | 75 | 40 | 20.7 | 2.81 | 44 | 3 % |
| ornament | claude-fable-5-1 | 76 | 81 | 35 | 23.1 | 2.47 | 41 | 3 % |
| QA critic | claude-fable-5-1 | 173 | 201 | 96 | 23.1 | 1.55 | 35 | 2 % |
| architecture | claude-fable-5-1 | 72 | 104 | 63 | 24.5 | 1.28 | 27 | 2 % |
| environment | claude-fable-5-1 | 55 | 100 | 39 | 14.7 | 1.04 | 22 | 1 % |
| analysis/mechanical | claude-fable-5-1 | 60 | 70 | 26 | 7.3 | 1.27 | 21 | 1 % |
| lighting | claude-fable-5-1 | 53 | 50 | 25 | 8.7 | 1.03 | 18 | 1 % |
| phase 5 prep | claude-opus-5 | 49 | 58 | 25 | 6.1 | 0.16 | 5 | 0 % |
| other | claude-fable-5-1 | 17 | 16 | 8 | 1.1 | 0.16 | 3 | 0 % |
| phase 5 prep | claude-sonnet-5 | 25 | 25 | 15 | 1.9 | 0.11 | 1 | 0 % |
| lead | <synthetic> | 15 | 0 | 0 | 0.0 | 0.00 | 0 | 0 % |
| lighting | <synthetic> | 1 | 0 | 0 | 0.0 | 0.00 | 0 | 0 % |
| analysis/mechanical | <synthetic> | 1 | 0 | 0 | 0.0 | 0.00 | 0 | 0 % |
| architecture | <synthetic> | 2 | 0 | 0 | 0.0 | 0.00 | 0 | 0 % |
| environment | <synthetic> | 2 | 0 | 0 | 0.0 | 0.00 | 0 | 0 % |
| materials | <synthetic> | 3 | 0 | 0 | 0.0 | 0.00 | 0 | 0 % |
| ornament | <synthetic> | 2 | 0 | 0 | 0.0 | 0.00 | 0 | 0 % |

## Gaps with no agent active (>= 30 min) in the week

| start | end | hours | ended by a human prompt | lead had asked a question | lead last tools | GPU running |
|---|---|---|---|---|---|---|
| 09-15 00:00 | 09-15 09:40 | 9.67 | True | False | [] | False |
| 09-16 05:34 | 09-16 08:48 | 3.23 | True | False | [] | False |
| 09-16 09:31 | 09-16 13:51 | 4.33 | True | False | [] | False |
| 09-16 17:31 | 09-16 22:31 | 5.0 | True | False | [] | False |
| 09-17 01:26 | 09-17 07:10 | 5.73 | True | False | [] | False |
| 09-17 08:21 | 09-17 08:56 | 0.58 | True | False | [] | False |
| 09-17 13:00 | 09-17 23:16 | 10.27 | True | False | [] | False |
| 09-17 23:24 | 09-18 16:57 | 17.55 | False | False | ['AskUserQuestion'] | False |
| 09-18 19:51 | 09-18 20:42 | 0.85 | False | False | [] | False |
| 09-18 21:01 | 09-18 22:59 | 1.97 | True | False | [] | False |
| 09-18 23:35 | 09-19 08:43 | 9.13 | True | False | [] | False |
| 09-19 09:58 | 09-19 12:25 | 2.45 | True | False | [] | False |
| 09-19 15:13 | 09-19 17:35 | 2.37 | True | False | [] | False |

## Lead sessions in the week (restart cost = cache written in the first 15 minutes)

| session | start | end | lead requests | first-15-min cache write k | first-15-min cost | lead cost | max context tokens |
|---|---|---|---|---|---|---|---|
| 11484ff4 | 09-15 09:43 | 09-15 09:43 | 2 | 29 | 0.64 | 0.64 | 58,583 |
| 3ada03f9 | 09-17 23:16 | 09-19 21:15 | 329 | 96 | 3.46 | 96.99 | 601,028 |
| 4133edbe | 09-17 08:56 | 09-17 12:59 | 146 | 116 | 4.82 | 18.43 | 312,754 |
| 52e90d0f | 09-15 10:18 | 09-15 10:19 | 3 | 35 | 0.82 | 0.82 | 63,174 |
| 5b1d192d | 09-16 22:31 | 09-17 08:20 | 122 | 77 | 2.79 | 25.21 | 326,601 |
| 6460c313 | 09-15 09:49 | 09-16 08:48 | 315 | 140 | 5.4 | 68.76 | 557,659 |
| 797d734e | 09-10 14:11 | 09-15 09:42 | 42 | 218 | 8.0 | 29.89 | 336,267 |
| 87d95e57 | 09-16 13:51 | 09-16 17:30 | 128 | 53 | 1.71 | 19.33 | 339,147 |
| a87300f7 | 09-19 18:07 | 09-20 08:10 | 203 | 94 | 3.52 | 38.94 | 441,957 |
| c47a8492 | 09-16 08:49 | 09-16 09:30 | 45 | 75 | 2.51 | 5.07 | 133,324 |

## Reviews (docs/reviews/phase6*, phase7*)

verdicts: {'MERGE WITH FIXES': 25, 'MERGE AFTER FIXES': 3, 'MERGE BLOCKED': 1, 'MERGE': 1, 'SEND BACK': 1}; fix-now mentions total 128

| review | verdict | fix-now mentions | lines |
|---|---|---|---|
| phase6_bake_gate0_review.md | MERGE WITH FIXES | 5 | 41 |
| phase6_bake_gate2_review.md | MERGE WITH FIXES | 4 | 39 |
| phase6_bake_gate3_r2_review.md | MERGE WITH FIXES | 2 | 90 |
| phase6_bake_gate3_review.md | MERGE WITH FIXES | 6 | 115 |
| phase6_bake_gate4_instance_review.md | MERGE AFTER FIXES | 1 | 94 |
| phase6_export_gate1_review.md | MERGE WITH FIXES | 6 | 46 |
| phase6_export_gate3_r3_review.md | MERGE WITH FIXES | 5 | 71 |
| phase6_export_gate3_r4_review.md | MERGE WITH FIXES | 4 | 62 |
| phase6_export_gate3_review.md | MERGE WITH FIXES | 6 | 101 |
| phase6_export_gate4_r5_review.md | MERGE WITH FIXES | 2 | 82 |
| phase6_viewer_gate0_review.md | MERGE WITH FIXES | 5 | 44 |
| phase6_viewer_gate1_review.md | MERGE WITH FIXES | 3 | 39 |
| phase6_viewer_gate2_review.md | MERGE WITH FIXES | 5 | 17 |
| phase6_viewer_gate4_r5_review.md | MERGE WITH FIXES | 3 | 116 |
| phase6_viewer_gate4_r5b_review.md | MERGE WITH FIXES | 2 | 106 |
| phase6_viewer_gate4_r6_review.md | MERGE BLOCKED | 7 | 97 |
| phase6_viewer_gate4_r7_review.md | MERGE AFTER FIXES | 3 | 94 |
| phase6_viewer_gate4_r7b_review.md | MERGE AFTER FIXES | 6 | 96 |
| phase6b_export_r1_review.md | MERGE WITH FIXES | 4 | 43 |
| phase6b_export_r2_review.md | MERGE WITH FIXES | 3 | 38 |
| phase6b_viewer_r1_review.md | MERGE WITH FIXES | 5 | 51 |
| phase6c_bake_r1_review.md | MERGE WITH FIXES | 6 | 25 |
| phase6c_bake_r2_review.md | MERGE WITH FIXES | 6 | 25 |
| phase6c_bake_r2b_review.md | MERGE WITH FIXES | 4 | 21 |
| phase6c_export_r1_review.md | MERGE WITH FIXES | 4 | 44 |
| phase6c_export_r2_review.md | MERGE WITH FIXES | 4 | 14 |
| phase6c_export_r3_review.md | MERGE | 0 | 15 |
| phase6c_viewer_r1_review.md | SEND BACK | 5 | 49 |
| phase6c_viewer_r2_review.md | MERGE WITH FIXES | 6 | 39 |
| phase6c_viewer_r3_review.md | MERGE WITH FIXES | 3 | 34 |
| phase7_viewer_r1_review.md | MERGE WITH FIXES | 3 | 43 |

## QA rounds 11-19

- qa_round_11.md (178 lines): # QA round 11 — Phase 6 **Gate 1** (geometry freeze in the viewer), 2026-09-15. **GATE 1: FAIL.**
- qa_round_11b.md (82 lines): # QA round 11b — Phase 6 **Gate 1** re-check after the two blockers, 2026-09-15. **GATE 1: FAIL.**
- qa_round_11c.md (79 lines): # QA round 11c — Phase 6 **Gate 1**, third check, 2026-09-15. **GATE 1: FAIL.**
- qa_round_11d.md (87 lines): # QA round 11d — Phase 6 **Gate 1**, fourth check, 2026-09-15. **GATE 1: PASS.**
- qa_round_12.md (123 lines): # QA round 12 — Phase 6 **Gate 2**: the baked PBR set alone, 2026-09-15. **GATE 2: FAIL** (one row).
- qa_round_12b.md (120 lines): # QA round 12b — Phase 6 **Gate 2** re-check after QA-12-1, 2026-09-15. **GATE 2: PASS**
- qa_round_13.md (105 lines): # QA round 13 — Phase 6 **Gate 3, the lightmaps alone**, 2026-09-16. **LIGHTMAPS ACCEPTED, one re-bake**
- qa_round_14.md (154 lines): # QA round 14 — Phase 6 **Gate 4, the viewer proper**, 2026-09-16. **ONE MORE ROUND** (no blocker)
- qa_round_15.md (107 lines): # QA round 15 — Phase 6 **Gate 4, round two**, 2026-09-17. **6a PARITY REACHED** (45 fps still not met)
- qa_round_16.md (145 lines): # QA round 16 — Phase **6c, the foliage gate**, round one of two, 2026-09-17. Verdict: **ONE MORE ROUND**
- qa_round_17.md (174 lines): # QA round 17 — Phase **6c, the foliage gate**, round two of two, 2026-09-17. Verdict: **6c CLOSED WITH RESIDUALS**
- qa_round_18.md (119 lines): # QA round 18 — Phase **6b, Gate 5: the staging deployment**. Verdict: **ONE FIX ROUND** (one blocker, on mobile)
- qa_round_18b.md (96 lines): # QA round 18b — Phase **6b, the Gate 5 fix round** (the closing 6b round). Verdict: **6b DONE WITH RESIDUALS**
- qa_round_19.md (108 lines): # QA round 19 — Phase **7, the foliage look on the live URL** (the closing Phase 7 round), 2026-09-19. Verdict: **PHASE 7 DONE WITH RESIDUALS**

## Commits per day (all branches) and rework-flavoured subjects

| day | commits | rework words | merges into main |
|---|---|---|---|
| 2026-09-15 | 198 | 47 | 19 |
| 2026-09-16 | 187 | 50 | 12 |
| 2026-09-17 | 153 | 46 | 13 |
| 2026-09-18 | 78 | 22 | 9 |
| 2026-09-19 | 253 | 64 | 29 |
| Phase 5 (09-06..09-10) | 792 | 150 | 75 |

## Cost per point of station score

| step | from | to | hero delta | mean-of-six delta | cost USD | USD per hero point | USD per mean-of-six point |
|---|---|---|---|---|---|---|---|
| g1 | phase5_10b | g1_qa11_geometry_only | -0.11 | +0.025 | 176 | n/a (no gain) | 7042 |
| g3 | g1_qa11_geometry_only | g3_qa13 | -0.11 | -0.250 | 461 | n/a (no gain) | n/a (no gain) |
| g4 | g3_qa13 | g4_qa15 | +0.33 | +0.271 | 254 | 769 | 937 |
| 6c | g4_qa15 | 6c_qa17 | +0.06 | +0.064 | 322 | 5360 | 5025 |
| 6b | 6c_qa17 | 6b_qa18b_desktop | +0.00 | +0.000 | 209 | n/a (no gain) | n/a (no gain) |
| p7 | 6b_qa18b_desktop | p7_qa19_desktop | +0.00 | +0.020 | 44 | n/a (no gain) | 2204 |
