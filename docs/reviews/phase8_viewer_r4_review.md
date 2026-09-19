# Code review — branch `phase8a-viewer` (95a0114..fffb153), round 4

Reviewer: Opus 5, read-only, no Blender, no Chrome. Reviewed against main at 19e7e1a
(`git diff 19e7e1a..fffb153`), the brief `docs/briefs/phase8a_viewer_relight.md`, decisions.md
"8a decision 2 (re-scope)", the branch's `docs/briefs/phase8a_relight_report.md` and
`web/README.md` "Phase 8a", and the carries in `docs/reviews/phase8_viewer_r3_review.md`.
`npm test` was run in the worktree's `web/` and, after the one-line repair below, in a scratch copy.

## VERDICT: DO NOT MERGE

One build-breaking blocker (finding 1). It is a three-line repair; with it applied and `npm test`
re-run the branch becomes **MERGE WITH FIXES** (findings 3–6 to send back, finding 7 for the lead to
accept explicitly). Everything else in the branch checks out, including the whole of the relight
maths, the sun space, and every numeric claim in the report.

---

## Findings

### 1. BLOCKER — `web/src/impostors.js:222`, `:286`, `:288`: backticks inside the GLSL template literal; the module does not parse

`fragmentShader` is a JS template literal (`const fragmentShader = /* glsl */\`` at line 138, closed at
line 479). The r2-6 explanatory comments added inside it in commit **f099e0c** contain backtick-quoted
identifiers:

```
222:  // COMPILE-TIME count and not a `w.z > 0.0` test: `texelAt` is an implicit-LOD fetch, and an
286:  // r2 review 6: the band blends TWO frames.  `c2` is set so the shared code below has a
288:  // (`wk <= 0.0` below) - four texel fetches per band fragment in the premul path and one
```

The first backtick on line 222 closes the template literal and the rest of the line is parsed as JS:

```
$ node --check web/src/impostors.js
web/src/impostors.js:222
	// COMPILE-TIME count and not a `w.z > 0.0` test: ...
	                                 ^
SyntaxError: Unexpected identifier 'w'
```

Why it matters: `impostors.js` is imported by the viewer bundle and by three test files, so

* `npm test` **fails at HEAD** — it dies importing `foliage_lazy_test.mjs`, and
  `foliage_lazy_test.mjs`, `foliage_cardsun_test.mjs`, `impostor_cov_test.mjs` and
  `impostor_band_test.mjs` never run (all four fail to load individually);
* `vite build` would fail the same way, i.e. **the viewer does not build from this branch**.

Introduced by f099e0c and still present at fffb153 (verified per commit: da66b1e parses, f099e0c does
not). The working tree is clean, so this is the committed state.

**Fix:** strip or requote the backticks on those three lines (single quotes, or nothing — they are GLSL
`//` comments, not markdown). Verified: with exactly those three lines' backticks removed in a scratch
copy of `web/src`+`web/test`, `PFA_MAIN_ROOT=<main checkout> npm test` is fully green — 12 suites, all
of the new 8a and carry assertions passing. No other change is needed to make the suite pass.

### 2. MAJOR (process) — four commits claim "npm test green" after the tree stopped parsing

f099e0c ("npm test green."), and by implication 6b24c4a, a0caf9b and fffb153, were committed on a tree
whose `npm test` cannot start. The r2-6 measurements quoted in f099e0c (band frame cost, the
0.0045 % / 0.0074 % capture diffs, the 1.18 % divergent-control-flow result) must therefore have been
taken on a working tree that differs from what was committed, and are not reproducible from this
branch as it stands. **Fix:** after finding 1, re-run `npm test` and state it honestly; if the band
captures were taken before the comment was written, say so in the report.

### 3. MINOR — `web/src/impostors.js:286-289`: the comment contradicts the code

It says the zero-weight taps "are skipped (`wk <= 0.0` below)" and then, two lines later, that they are
"dropped at COMPILE time (PFA_FRAMES), never by a per-fragment test". There is no `wk <= 0.0` test in
the file (grep: `wk` appears only at 341/347, as the weight); the per-fragment form is the one the
commit explicitly rejected. **Fix:** delete the parenthesis while repairing the backticks.

### 4. MEDIUM — the relight leaves no runtime evidence: no `note()`, and `__pfaInfo()` omits it

`applyFoliage` builds `report.cardSun / cardSunMaterials / cardSunSkipped`
(`web/src/foliage.js:759-760, 861-863`) but **nothing ever prints or exports them**: there is no
`note()` line for the relight (unlike `cardEnv`, which has one), and the `__pfaInfo().foliage` block
(`web/src/main.js:2027-2038`) lists `cardEnv`, `cardEnvMaterials`, `cardEnvAlready`, `cardInterior`,
`cardMipBias` … and no `cardSun*`. Consequences in this branch's own evidence:

* `renders/logs/p8a_adopt.log` and `renders/logs/p8a_mobile.log` carry no `?cardsun=` in the URL (both
  ran on the built default, which is correct) and no relight line anywhere, so no committed log shows
  that a single card material was actually patched;
* the **mobile check** (brief: "mobile tier drawn once at station 1 to confirm nothing breaks") is
  evidenced only by "loads and draws, no shader-patch error, 312 draws". That confirms the page does
  not fall over; it does not confirm the patch was applied there. The mobile log shows the same 27 card
  materials patched by the foliage pass, but `cardSunMaterials` is unknown for that run;
* a QA round reading a `*_shot.json` cannot tell whether the relight was on.

**Fix:** one `note()` line (`cardSun` parameters, `cardSunMaterials`, and `cardSunSkipped` when
non-empty) and the three fields in the `__pfaInfo().foliage` block; re-capture station 1 on the mobile
manifest once and quote `cardSunMaterials` in the report.

### 5. MINOR — `web/src/foliageLazy.js:282`: the new `needsUpdate` forces a re-upload it does not need

`t.needsUpdate = true` is unconditional inside `if ( old )`. In three r186 the setter bumps
`source.version`, so every lazily loaded root re-uploads the whole shared tinted albedo atlas — today,
always, because the wrap it copies is always the same clamp. The reasoning for the line is right (8e
will change the wrap and `uploadTexture` is the only place sampler state is applied); the cost is a
needless multi-MB re-upload per lazy root at stream time, which can show as a hitch.
**Fix:** `if ( t.wrapS !== old.wrapS || t.wrapT !== old.wrapT || t.channel !== old.channel ) t.needsUpdate = true;`
(and note that the pre-existing `tr.needsUpdate` at :298 has the same property).

### 6. MINOR (docs) — two stale statements in `web/src/foliage.js`

* `:168` — "`chroma` 0.65 lands that ratio near the measured one" is the stage-1 text; the adopted
  default is `chroma = 1.0`, and the README's own property 3 explains why (the level, not the chroma,
  was the binding constraint). The same block correctly lists the adopted eight, so the file
  contradicts itself.
* `:220` — `parseCardSun`'s docstring lists seven fields
  (`"amt[,share[,wrap[,shade[,mean[,chroma[,cap]]]]]]"`) and omits `two`, which the parser does read and
  which is the parameter the report says makes the level stable across stations.

### 7. INFORMATIONAL (for the lead / QA to accept explicitly) — the hard-edge constraint was reframed

The brief says "the hard-edge share must not rise above the reference at any of the eight boxes".
As written that constraint was already broken before 8a: seven of the eight boxes are above the
reference at `cardsun 0` (a standing QA-16 item). The branch reframes it as "no box crosses the
reference that was not already across it" and holds the one box below it (05 shore, 4.27 % against
4.30 %). Three of the already-crossed boxes do rise further (+0.12, +0.20, +0.14 pp). This is stated
plainly in both the report and the README — it is disclosed, not hidden — but it is a change of
acceptance criterion and should be accepted in writing rather than absorbed silently.

---

## What was checked and is correct

**The relight maths (`web/src/foliage.js:145-265, 636-687`).** The shader term is
`E' = E · max(0, 1 + amt·f·ŝ·(g−1))` with `ŝ = mix(1, pfaSunIrr/luma(pfaSunIrr), chroma)`,
`f = min(share, 0.98/max(ŝ))`, `nl = clamp((mix(N·L, |N·L|, two) + wrap)/(1+wrap), 0, 1)`,
`clump = 1 − shade·clamp(vPfaCrownD.z, 0, 1)`, `g = clamp(nl·clump/mean, 0, cap)` — sun share on a
two-sided cosine times the clump term, sky share as the remainder, redistributed about the scene mean.
At `g = 1` the factor is exactly `vec3(1)` in every channel, independent of every other parameter: the
"returns the baked value exactly" claim is true as stated. Stronger: **on the adopted parameters the
term never clamps**, so it is exactly affine in `g` and `mean(factor) = factor(mean g)` holds without
qualification — with `two = 1` and `wrap = 0.35`, `nl ∈ [0.259, 1]`, `clump ∈ [0.1, 1]`, so
`g ∈ [0.07, 2.63]` against `cap = 3`, and the minimum red factor is `1 − 0.6·0.634·1.546 = 0.412 > 0`.
The `0.98/max(ŝ)` clamp keeps the sky share non-negative for a degenerate sun colour (tested with a
pure-red sun). `cardSunFactor` is a term-for-term mirror of the GLSL, including the `mix` forms and the
`max(mean, 1e-3)` / `1e-6` guards.

**`?cardsun=0` / `off` is byte-identical.** `cardSunOff` → `cs = null` → the fragment patch is not
emitted at all; the test asserts no `pfaCard` token in either stage, that `0` and `off` compile the
same source, that the flat `irradiance += vPfaInstIrr * 3.141593;` line is untouched, and that the
program cache key carries the bit. Re-run here: all pass. The two `pfaCardSun*` uniforms are still put
in the uniform map when off, which is inert (GLSL source decides the program) and costs nothing.

**The sun vector and colour, and their space (item 3 of the brief).** `manifest.js:565-585` turns
`sun.direction_blender` (travel direction) into `toSunBlender`; `main.js:643-644` builds the
DirectionalLight at `b2t(toSunBlender)·1000` — the Blender→glTF axis swap is applied there, once — and
`foliage.js:767` sets `pfaSunDir` to that position normalised, i.e. three **world** space. The patch
does `normalize((viewMatrix * vec4(pfaSunDir, 0)).xyz)` and dots it with `normal`, which is view space
at `lights_fragment_maps`: the two are in the same space. It is the identical expression the existing
translucency lobe uses at `:621`, so it inherits a term already validated against Cycles. `pfaSunIrr` is
`sun.color × sun.irradiance` from the manifest, and dividing by luma cancels the intensity, so only the
manifest's chroma enters. The `trn > 0` guard on the redeclaration exactly matches the other
declaration site (`:616-618`), and the test asserts `uniform vec3 pfaSunDir;` appears exactly once.
The cards' normals are not bent (`shrub/reed cards at 0.00` in every capture log), so `|N·L|` really is
the card plane against the sun. Note that the manifest sun has `B = 0`, so at `chroma = 1` the blue
channel is unmodulated and the "cool shade" is a relative shift only — correctly stated as a chroma
shift, not a blue gain, in both README and test.

**The adopted default and the numbers (item 2).** `CARD_SUN = {amt 0.6, share 0.8, wrap 0.35,
shade 0.9, mean 0.38, chroma 1.0, cap 3, two 1}` matches the README switch table, the report's adopted
string, and the test's explicit assertion of all eight. Every level / hard-edge / hue figure in
`docs/briefs/phase8a_relight_report.md` and in the README table reconciles line for line with
`renders/web/p8a_boxes.txt` (worst level 0.972× = 2.8 % against the 3 % budget; hard-edge movement
−0.13 to +0.20 pp; leaf/ref within ±0.02×; the station-2 hue 71.6 → 75.7 of 90.3). The `fn` column is
the frame-normalised level from `qa_r16_probe.box_stats`, the QA-16 metric, not a new one
(`scripts/p8a_relight_boxes.py:10-20`). `p8a_adopt` was captured on the built default (no `?cardsun=`
in `renders/logs/p8a_adopt.log`) and `p8a_a6` on the explicit
`cardsun=0.6,0.8,0.35,0.9,0.38,1,3,1` (`renders/logs/p8a_a6.log`), which is exactly the
default-equals-measured check the report describes. One maintenance caveat worth carrying forward:
`mean` is a hand-fitted constant, not the scene mean computed at runtime, so the level guarantee is
only as good as that fit — it must be re-measured if the sun, the LOD distances or the shrub placement
change. The README says this.

**The carries (item 5).**
* r3-3 — `applyFoliageTextures` now decides the wrap once from `srcMaps[0]` and writes it to both the
  tinted albedo and the translucency factor; the note text names both maps. Test added (two materials
  of one name, clamp then repeat → both maps on the first's wrap, one note).
* r3-4 — `pad = mesh.isInstancedMesh ? 0 : rad`, per-batch `lim + pad`, `lim2` moved inside the loop.
  Correct, and only ever makes a batch visible sooner. Test added (100 m plane visible at 45 m with a
  40 m limit, hidden at 200 m, pad 0 for the instanced batch). Pixel-neutral on today's assets by
  argument rather than capture — `buildDistanceCull` is only called on the env_shrubs / env_trees
  instanced roots — which is the right kind of claim to make without a mask.
* r3-5 — the `__pfaTrisByGroup` note now says "must match WITHIN the post chain's full-screen quads"
  with the measured 4 952 550 vs 4 952 588 / 301 vs 317.
* r3-6 — `scripts/p8b_c_cielab.py` committed, fixture is `light_r16_measure.BOXES`, resampling matches
  `light_r14_measure.load`, per-pixel Lab averaged over the box with the Lab-of-mean printed beside it.
  It reports honestly that the photo column is not reproducible from the tree because the box set used
  on ref_062 was never recorded — that is a finding, correctly logged, not an omission.
* r2-5b — `manifest.js:1104-1110` pushes a g3note when `impostors.band.rows > 4` explaining that
  `pfaBandEl` is a vec4 and rows 5+ are ignored. Today's band is 3 rows, so it does not fire.
* r2-6 — the premul path is **exactly** neutral: the dropped `k = 2` iteration contributes
  `wk = w.z = 0`, so `accA` and `acc` are unchanged bit-for-bit; the straight path's `s2 = vec4(0)` is
  multiplied by `w.z = 0`. `tc[2]` is left unwritten on the band path and is not read (`PFA_FRAMES = 2`).
  `PFA_FRAMES` is declared inside `#ifdef PFA_IMP_PREMUL` (204-230) and used inside the same block
  (323-352) — scope is fine. The stated reason for not using a per-fragment test is correct:
  `texelAt` is an implicit-LOD `texture2D`, and an implicit-LOD fetch under divergent control flow has
  undefined derivatives, so the mip choice is corrupted; the measured 1.18 % is consistent with that.
  (The GLSL itself cannot be compiled in this review — no GPU — and the file does not parse today;
  see findings 1 and 3.)

**The 8e `needsUpdate` line (item 6).** It covers both maps on both roots: lazy path
`foliageLazy.js:282` (albedo) and `:298` (translucency, pre-existing); eager path `:972` (translucency)
and `:987` (albedo, pre-existing). Correct in coverage; see finding 5 for the cost.

**The A/A water caveat (item 7).** Documented in `web/README.md` "Phase 8a" (34.2 % of cam01 and 13.3 %
of cam05 differ between sessions on the same build, all below the waterline; above the waterline
identical) and repeated in the report and in f099e0c. I found no pixel-parity claim in the branch that
is stated at a water station without that mask: the r2-6 numbers are given as "stable pixels", the
default-equality check is same-session (0.000–0.007 %, far below the between-session floor), and the
r3 carries claim neutrality by argument about which objects are affected, not from a capture.

**`.gitignore`** — `renders/web/p8a_*.png` added after the `!renders/web/960/*` negation; the patterns do
not overlap (different directory, different extension), and the committed 960 px composites are
unaffected.
