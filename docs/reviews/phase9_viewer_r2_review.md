# phase9-viewer r2 (11cf875) — MERGE WITH FIXES

Diff `main...phase9-viewer`: 7 files, +996 / −6, **all under `web/`** (README, package.json, src/{impostors,main}.js, test/{impostor_rim,detail_proj}_test.mjs, tools/p9v_rim.py) — nothing outside the viewer's scope, no binaries.
`npm test` in the worktree: **558 checks, 0 failures** (549 at r1; the +9 are the new r1-fix pins). `p9v_rim.py selftest`: all pass, including "a 960x540 frame is refused". `p9v_rim.py capture` on MAIN's `renders/web/gate12_cam0N.png` still prints **0.264 / 0.369 / 0.080** — the r1 numbers are unmoved by the frame guard and the derived boxes, so the fix changed no measurement.

## r1 findings 1-7 — checked by substance, all closed

1. `main.js:2061-2064` adds `quantise: impostorReport.quantise` to `__pfaInfo.impostors`; `impostors.js:803-807` adds `why`. The owed A/B is self-attesting.
2. Claim now true and source-checkable (`README:1197-1204` states mobile IS quantised): `main.js:685-687` builds the composer `samples: 4` **unconditionally**, `device.js:82-112` (`TIER_SETTINGS.mobile`) overrides neither `leafSoft` nor `impEdge`, so mobile gets `msaa` → `a2c` → the define. QA 21 §4's byte-identity invariant is retracted, not re-asserted.
3. `README:1181-1188`, `impostors.js:118-127`: scoped to the per-pixel scalar OFFSET family, with part 3's "after" column called arithmetic, not evidence.
4. `README:1158-1162`, `impostors.js:110-114`, `p9v_rim.py:25-27` carry the spec's own sentence.
5. Closed by the stronger option: `parseImpQuant` takes `coverage` (`impostors.js:738`), the single call site passes `impCov.on` (:787), and `impostor_rim_test.mjs:180-185` pins that `?impcov=0` compiles neither `PFA_IMP_COV` nor `PFA_IMP_QUANT`. `impostors.js:90`, `:1063-1069` and `README:797` are true again as written.
6. `_box` (`p9v_rim.py:111-121`) asserts `(1080, 1920)` and raises; `part_ab` (:132-147) derives ONE mask from the BEFORE frame and applies it unchanged to both; `selftest` proves both without a GPU.
7. **Acceptable as a wording fix.** r1 graded it a carry whose fix *was* the wording, and it is now right in four places plus a README carve-out (`:1216-1222`). The substance — `pfaViewDir` is `normalize(v)` verbatim on every non-degenerate fragment (`impostors.js:232`, used at :308/:349), pinned by three checks — was settled at r1; a revert switch would buy nothing measurable.

Carries 8-14 are tabled at `README:1224-1238`; line refs spot-checked and right (`foliage.js:862`, `water.js:302`, `main.js:1040`, `impostors.js:305` — corrected from r1's stale :293 — `impostor_rim_test.mjs:70`, `:115-117`).

## Findings

1. **fix now (one line, wrong in the shipped doc)** — `README.md:1238`, carry-14 row: "r2's commits (this round) are Opus 5". `486518e`, the commit closing findings 1 and 5, carries `Co-Authored-By: Claude Fable 5.1`; the other six are Opus 5. Fix: "six of r2's seven commits are Opus 5; 486518e is Fable 5.1".
2. **carry** — `p9v_rim.py:53-70`: "change FRAME alone and the rectangles follow … to the same crowns" does not hold off the delivery aspect (the camera aspect changes with the canvas, so a crown does not move affinely with the box), and the guard refuses every frame where `boxes_for` is not the identity. Scope the comment, or drop the lever.
3. **carry** — `README:1233-1236` owes `?tier=mobile` stations 1-6 in the paragraph whose measure is `p9v_rim.py ab`, but the mobile frames are 1170x2532 (`renders/web/gate12m_cam0N.png`) and the guard refuses them by design. Name the mobile measure explicitly (whole-frame MAE against `gate12m`), not the rim index.

**MERGE WITH FIXES** — 1 is a one-line correction the lead can take at merge; 2 and 3 are capture-round notes and block nothing. The seven closures are real, the measurement is unmoved, the branch is ready for the GPU window.
