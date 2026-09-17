# Perf A/B for 6c — round-15 look vs 6c look, same session

Mechanical measurement per `docs/briefs/perf_ab_6c.md`. Three passes, back to back, one Chrome session each,
nothing else running. GL renderer for all three passes: `ANGLE (Apple, ANGLE Metal Renderer: Apple M2,
Unspecified Version)`.

Pass tags: A = `perfab_r15look` (round-15 look), B = `perfab_6c` (6c look, base query only),
C = `perfab_r15look2` (round-15 look again, drift control). All three passes exited rc=0 on the first try; none
was retried.

## 1. Per-station table (2560x1440, medians in ms unless noted)

| station | name | A | B | C | mean(A,C) | B − mean(A,C) | A − C (drift) | B gpu_cost_ms | B draw_calls | B triangles | A draw_calls | A triangles |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | CAM_qa_01_lagoon_hero | 28.10 | 29.70 | 27.80 | 27.95 | +1.75 | +0.30 | 3.10 | 329 | 5,242,248 | 279 | 4,142,680 |
| 2 | CAM_qa_02_lagoon_ne_threequarter | 32.20 | 30.40 | 30.10 | 31.15 | −0.75 | +2.10 | 3.40 | 324 | 5,235,144 | 274 | 4,135,576 |
| 3 | CAM_qa_03_colonnade_walk | 30.80 | 33.50 | 30.00 | 30.40 | +3.10 | +0.80 | 3.40 | 347 | 5,983,404 | 297 | 4,487,662 |
| 4 | CAM_qa_04_rotunda_ceiling | 22.80 | 22.00 | 21.40 | 22.10 | −0.10 | +1.40 | 1.00 | 183 | 2,754,810 | 158 | 2,204,990 |
| 5 | CAM_qa_05_south_lawn | 28.90 | 29.80 | 28.90 | 28.90 | +0.90 | +0.00 | 3.10 | 314 | 5,006,654 | 264 | 3,907,086 |
| 6 | CAM_qa_06_aerial | 31.10 | 32.30 | 31.80 | 31.45 | +0.85 | −0.70 | 3.40 | 351 | 5,601,864 | 301 | 4,502,296 |

Resident memory (`stations[0].resident.total_bytes`, MB — same figure reported at every station within a pass):
A = 1788.0 MB, B = 1931.4 MB, C = 1788.0 MB.

## 2. Context: same medians from the on-disk round-15 and round-16c-cold JSONs

| station | name | round15_perf median | round16c_cold_perf median |
|---|---|---|---|
| 1 | CAM_qa_01_lagoon_hero | 28.20 | 32.40 |
| 2 | CAM_qa_02_lagoon_ne_threequarter | 32.20 | 37.00 |
| 3 | CAM_qa_03_colonnade_walk | 32.90 | 35.10 |
| 4 | CAM_qa_04_rotunda_ceiling | 22.50 | 22.10 |
| 5 | CAM_qa_05_south_lawn | 30.40 | 32.20 |
| 6 | CAM_qa_06_aerial | 32.10 | 34.00 |

Resident memory: round15_perf = 1677.9 MB, round16c_cold_perf = 1931.4 MB.

## 3. Facts

Measured in the same session, the 6c look costs more than +3.0 ms over the round-15 look at only one station:
station 3 (colonnade_walk), where B − mean(A,C) = +3.10 ms against an A−C drift of +0.80 ms, so the delta there is
larger than the drift but sits right at the +3.0 ms line. At the other five stations the 6c-look cost is below
+3.0 ms and in two cases negative (station 2: −0.75 ms; station 4: −0.10 ms). The A−C drift control ranges from
+0.00 ms (station 5) to +2.10 ms (station 2), i.e. of the same order as several of the B − mean(A,C) deltas
(stations 1, 2, 4, 5, 6), so at those five stations the measured 6c-vs-round15 delta is not clearly attributable
to the look change against session-to-session drift; only station 3's delta (+3.10 ms vs +0.80 ms drift) is larger
than its own drift control. GL renderer for all three passes: `ANGLE (Apple, ANGLE Metal Renderer: Apple M2,
Unspecified Version)`. Every station in every pass shows `frame_ms.max` roughly 17-22x its own `frame_ms.p95`
(e.g. station 1 pass A: max 642.5 ms vs p95 30.8 ms, ratio 20.9x; station 6 pass B: max 735.3 ms vs p95 34.8 ms,
ratio 21.1x), consistent across all three passes and all six stations, indicating a single outlier frame per
station-pass (e.g. a compile/GC stall) rather than pass-specific throttling. Resident memory is higher for the 6c
look (1931.4 MB) than for either round-15-look pass (1788.0 MB each, byte-identical between A and C), and matches
round16c_cold_perf's 1931.4 MB; round15_perf's own resident figure (1677.9 MB) is lower than the same-session round-15
passes A/C (1788.0 MB) taken today. B's draw calls and triangle counts are higher than A's at every station (e.g.
station 3: 347 vs 297 draws, 5,983,404 vs 4,487,662 triangles).

## 4. Confirmation

- `pgrep -fl "headless"`: empty (no output).
- `git status --porcelain` shows no tracked files changed other than this report; the only new files under
  version control review are `renders/web/perfab_r15look_perf.json`, `renders/web/perfab_r15look_perf_shot.json`,
  `renders/web/perfab_6c_perf.json`, `renders/web/perfab_6c_perf_shot.json`, `renders/web/perfab_r15look2_perf.json`,
  `renders/web/perfab_r15look2_perf_shot.json` (the three JSON pairs) plus `docs/perf_ab_6c.md` itself. All other
  entries in `git status --porcelain` predate this task (pre-existing untracked logs/renders and the pre-existing
  modified `docs/usage/*` files) and were not touched by this run.
