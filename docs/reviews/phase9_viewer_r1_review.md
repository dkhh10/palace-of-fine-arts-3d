# phase9-viewer r1 (debdd0b) — MERGE AFTER FIXES

Diff `main...phase9-viewer` (5 commits, 7 files, +768 / −5). Read-only: no Blender, no Chrome, no GPU, no edits
outside this file. Ran `npm test` in `.claude/worktrees/phase9-viewer/web` (549 checks, all pass) and
`python3 web/tools/p9v_rim.py` (reproduces the README's 0.264 / 0.369 / 0.080 and the part-2/3 tables exactly).

## Verified

- **The mechanism argument is sound as far as it is scoped.** `floor( cov*N + 0.5 ) / N` with N a power of two lands
  exactly on k/N (1/N is a binary fraction; `impostor_rim_test.mjs:36-48` checks the float product is the integer, not
  near it). For a mask of the form `popcount = floor( cov*N + d(x,y) )`, `d` in [0,1), the popcount is k for every d,
  so the *resolved* value is pixel-independent — and because one fragment invocation writes one colour to every covered
  sample, only the popcount (not which samples) reaches the resolve. That is a real proof for that family.
- **Part 2 of `p9v_rim.py` is the load-bearing evidence and it is good.** The shader re-implemented over the real
  4096x1024 band atlas scores 0.004 / 0.007 on the same index the capture scores 0.264 / 0.369, at *both* regimes
  (`magT` 0 and 1) — which independently explains QA 21 §2c (at station 5 `magT = 0`, so the share literally cannot
  engage). No mips (`generateMipmaps:false`, r2 review), Bayer not compiled under `PFA_IMP_A2C` (r1 review, re-checked
  here per define combination). The elimination down to the hardware mask is honest.
- **Wiring.** `PFA_IMP_QUANT` is set at `impostors.js:827`, *before* the `useBand` branch at :832, so it reaches the band
  and octahedral variants of the one material, and `buildImpostors` has a single call site (`main.js:1117`). The guard
  (`impEdge.a2c && samples > 1`, :715-724) is right: `impEdge.a2c = d.a2c && !!msaa` (:587) and `msaa` is
  `CFG.leafSoft && targetSamples > 0` (`main.js:1042`), so `?leafsoft=0` / `?impedge=0|premul` / an un-multisampled
  target all leave it uncompiled and `pfaCovQ` at 0. Uniform is per-material and never read when the define is absent.
- **No colour or geometry path moves.** `pfaCov` is read only at the discard (:483), `debugMode 5` (:528) and
  `gl_FragColor.a` (:540). The LOD crossfade is a separate `pfaHash` discard (:293) and does not touch `pfaCov`.
- **Tests test the compiled source, not only a re-implementation.** §1-2 are necessarily a JS model, but §4
  (`impostor_rim_test.mjs:174-214`) pins the literal shader statement by regex (:177), its position between the
  coverage block and the discard (:178-181), and walks the real preprocessor over five define combinations. A drift
  between the JS `quantise` (:32) and the GLSL line would fail :177. Adequate.
- **Carries.** r2 carry 4 (degenerate `vDirBlender`) is genuinely closed: `pfaViewDir` (:232) is `normalize(v)` verbatim
  on every non-degenerate fragment and both lookups go through it (:308, :349), pinned by three checks. r1 carry 6's
  open half (nothing pinned the `dominant` default) is closed by `detail_proj_test.mjs` — the parse-validation half was
  already on main at `detail.js:311-313`, so the test is the whole remaining finding, correctly. r2 carry 6b (name the
  scripts behind the README tables) is done and states the `resident_mb()` double-count. r2 carry 3 (`cols-1`) and 6a
  are already on main and are now regression-pinned.

## Findings

1. **should-fix (blocks the capture round)** — `web/src/main.js:2051-2059`: the `__pfaInfo.impostors` block whitelists
   `edge`, `coverage`, `band` and **omits `quantise`**, so neither the before nor the after capture sidecar can state
   whether `?impq` was on — the exact gap r1 finding 5 and r4 finding 4 closed for every other switch, and the owed A/B
   is unattestable without re-reading a boot log. Fix: add `quantise: impostorReport.quantise,` to that object.
2. **should-fix (doc, factually wrong)** — `web/README.md:1187-1189` "the mobile tier and `?leafsoft=0` are untouched by
   construction". `main.js:684-686` creates the composer with `samples: 4` **unconditionally** (mobile's `post:'none'`
   only empties the pass chain) and `device.js:83-112` overrides neither `leafsoft` nor `impedge`, so mobile gets
   `msaa = true` → `a2c` → `PFA_IMP_QUANT`. Mobile frames will change and QA 21 §4's "mobile byte-identical" invariant
   breaks. Fix: say mobile is a 4x target and is quantised too, and add `?tier=mobile` to the owed capture.
3. **should-fix (claim strength)** — `web/README.md:1180-1181` and `impostors.js:119-124`: "the mask therefore stops
   depending on the pixel under **every** dither, not just the one modelled above". The proof covers masks of the single
   per-pixel scalar-offset form only; a spec-legal per-(pixel, sample) threshold table that is not a uniform offset is
   not made location-independent by a ladder point. All three models in `p9v_rim.py:173-186` (`none` / `2x2` / `eighth`)
   are that one family, so part 3's "after the fix" column is arithmetic, not evidence. Fix: scope it to "every dither of
   the modelled offset family", and say the capture is what decides.
4. **should-fix (doc)** — `web/README.md:1158-1159` and `impostors.js:110-112` put `"are not necessarily … a function of
   the sample location"` in quotation marks against GL ES 3.0 §15.1.3. The spec's own sentence is "The algorithm can and
   probably should be different at different pixel locations." Same substance, but it is not a quotation. Fix: quote the
   real sentence or drop the quote marks.
5. **should-fix** — `?impcov=0` no longer restores the Phase 7 frame. `impostors.js:826-828` gates `PFA_IMP_QUANT` on
   `impEdge.a2c` alone, independently of `impCov.on`, so with `?impcov=0` the Phase 7 ramp is now quantised — while
   `impostors.js:90`, `:1030` ("`?impcov=0` restores Phase 7") and `README:797` still claim otherwise. Fix: gate
   `impQuant.on` on `impCov.on` as well, or restate all three as "Phase 7 + the quantiser; add `?impq=0` for Phase 7".
6. **should-fix** — `web/tools/p9v_rim.py:86-92` never asserts the frame size, and `BOXES` (:45-47) are absolute
   1920x1080 rectangles: run on a 960 px copy or a mobile frame it prints plausible numbers for the wrong pixels. Worse
   for the A/B, `rim_mask` (:71-79) re-derives its thresholds *and its mask* from each frame, so the after-capture scores
   a different pixel set and the "rim px" column moves for two reasons at once. Fix: assert the shape is (1080, 1920),
   and for the A/B compute the mask once on the BEFORE frame and reuse it.
7. **carry** — `?impq=0` is not "the Phase 8b program" (`README:1196`, `impostor_rim_test.mjs:159`): the same branch
   replaces `normalize( vDirBlender )` with `pfaViewDir( … )` at `impostors.js:308` and `:349` unconditionally, and no
   switch reverts it. Provably inert on every non-degenerate fragment, but the wording should be "the Phase 8b coverage
   path".
8. **carry** — the fix reaches only the impostor materials. `foliage.js:862` turns `alphaToCoverage` on for every
   near-tree / card MASK material on the same 4x target; those write the same hardware mask unquantised. Out of scope for
   QA 21's far crowns, but if the capture still shows a rim on a near leaf card, that is why.
9. **carry** — the reflection pass agrees only by coincidence: `water.js:302-308` builds the Reflector without
   `multisample`, taking three's default of 4 (`Reflector.js:83`), while `pfaCovQ` comes from
   `composer.renderTarget1.samples` (`main.js:1039-1041`). Two independent defaults, nothing asserts they match and no
   test pins it. Fix: pass `multisample: 4` explicitly in `water.js`, or take the min of the two.
10. **carry** — the discard boundary moved: `quantise(0.124) = 0` (`impostor_rim_test.mjs:70`), so sub-⅛ fringe fragments
    are dropped instead of being drawn at one sample somewhere in the 2x2 — a silhouette erosion of up to half a sample.
    The hero's crossings metric (cam01 11.97 against Cycles 11.73, QA 21 §1) is precisely a silhouette-crossing count.
    The owed capture should re-run `export/p8_atlas_probe.py viewer` on cam01, not only the rim index and the MAE.
11. **carry** — `README:1185-1187` cost line: "N+1 levels instead of the dither's 2N+1" — the dither gives 5 per-pixel
    levels and ~17 over a 2x2 block; 2N+1 = 9 is derived nowhere. And "the mean coverage of an edge is preserved to under
    0.02 of a step" — `impostor_rim_test.mjs:115` checks 0.02 in *coverage* units, i.e. 0.08 of a 0.25 step.
12. **carry** — the elimination in `README:1148-1157` / `p9v_rim.py:15-21` lists mips, the Bayer cell and the derivatives,
    but not the one other genuinely per-PIXEL term in this shader, the LOD-dissolve `pfaHash( gl_FragCoord.xy )` discard
    (`impostors.js:293`). It is ruled out by the data (a hash is not period-2, and `vPfaFade` is 1 on a far crown) but not
    by the write-up. One line closes it. The competing mechanism the offline model *assumes* away — a *fine* (per-pixel)
    `dFdx` implementation, which ES 3.0 permits — is also worth naming: if the rim survives the capture, that is the next
    suspect, and `p9v_rim.py:132-144` hard-codes the coarse/per-quad model.
13. **carry** — report/boot-note nit: with no mask `parseImpQuant` returns `samples: 0` (`impostors.js:717`), so an
    explicit `?impq=0` on a non-MSAA target prints "not asked" rather than "off" (:1034-1038); and `report.quantise.samples`
    carries the target count even when the switch is off, so a sidecar must read `.on`, not `.samples`.
14. **carry (process)** — all five commits carry `Co-Authored-By: Claude Fable 5.1`, while the Phase 6 casting puts the
    viewer builder on Opus 5. Worth confirming which model produced the mechanism argument, since that argument is the
    deliverable.

## Verdict

**MERGE AFTER FIXES** — 1, 2 and 5 before the capture window (1 makes the owed A/B self-attesting, 2 and 5 are wrong
statements in the shipped docs); 3, 4 and 6 are doc/tool corrections that can ride the same commit. The fix itself is
cheap, reverts by a flag, touches no colour, and is the right thing to measure; nothing here argues against shipping it
to the capture.
