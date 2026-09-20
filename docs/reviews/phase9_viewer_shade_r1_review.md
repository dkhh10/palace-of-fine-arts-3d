# phase9-viewer-shade r1 (7e12bcf) — MERGE

Reviewer: Opus 5, read-only, no Blender, no Chrome. Diff `main...HEAD` = 10 files, all in scope
(web/src, web/test, web/tools/p9v_rim.py, web/README.md, web/package.json to wire the new suite,
export/manifest_v4.py + its schema test). tiers.py, scripts/, assets/, export/out untouched.

**Verified independently**
1. `export/manifest_v4.py:344-408` reads the shipped equirect itself. I re-ran `sky_open_irradiance_over_pi`
   read-only on `export/out/gate3/sky_diffuse_1024x512.exr`: **(2.195763, 3.432181, 11.255903)**,
   `quadrature_unit_check = 1.00000627` (assert < 1e-4), k = 2π/(hw) with cosθ·sinθ — the correct
   E/π quadrature. `manifest_v4.py:436-455`: 67.31939697/π = **21.42843**, audit LIGHT_sun 67.319
   (assert 1e-2 holds). Nothing hard-coded; schema test `web/test/manifest_test.mjs:76-114`.
2. Units are right at **both** ends. `manifest.json lightmaps.scale = 3.14159265`; `lightmaps.js:248,272`
   pass `gate3.scale` to `attachLightMap` → `materials.js:267 mat.lightMapIntensity`; the chunk's
   `lightMapIrradiance` = decoded texel × that (three 0.186 `lights_fragment_maps`), and
   `materials.js:207 specGateGlsl` divides it back out, so both ratios are in the bake's irradiance/π.
   `radiance += iblRadiance * pfaSkyVis` (materials.js:212) is the only IBL-specular accumulation;
   `reflectedLight.directSpecular *= pfaSunVis` (materials.js:214) runs after `lights_fragment_begin`
   and before `lights_fragment_end` (indirect only) — directSpecular is complete. `SPEC_GATE_DECLS`
   (materials.js:43) sits outside every `#if`. Only `lightmaps.js:245` and `:271` pass `specGate`;
   the vertex/instance-irradiance, impostor, water and backdrop `patchBakedMaterial` sites do not.
   `finishMaterials()` (main.js:1767) returns early under gate3, so nothing pre-patches these materials.
3. `?specgate=0` → `gate = null` → no GLSL and no cache-key term emitted (materials.js:170, 251-253);
   spec_gate_test §4 compares fragment, vertex and cache key. Confirmed by running it.
4. `npm test` in the worktree: **673 checks, 0 failures, exit 0** (spec_gate_test = 43, not 45). See F3.
5. MAIN untouched: `find export/out -newer 2026-09-20T00:00` → **0 files**; newest artefact 2026-09-19 23:56.
   `tiers.py:483 man5 = json.loads(json.dumps(man))` is a deep copy of the gate3 manifest, so the v4
   block carries to both gate5 variants with no tiers.py change — the claim is structurally sound.
6. r2 carries closed: p9v_rim.py:53-60 (resample-not-re-aim), README:1349-1352 (mobile = whole-frame MAE).

**Findings** (no blockers)
1. `export/manifest_v4.py:355-356` (carry) — "a flipped row order … cannot ship silently" overclaims:
   the unit assert is symmetric in row index and passes on a vertically flipped EXR. The record
   already has `upper_mean 5.736 / lower_mean 0.060` and the function computes
   `upper_half_solid_angle_mean` but never compares them. Fix: assert upper > lower, or drop the claim.
2. `web/src/materials.js:44` + README:1155 (carry) — "keeps `?lmscale=` honest" is not true of this path:
   `?lmscale=` overrides `lightmapScale` (main.js:1415) only, while gate3 uses `gate3.scale`
   (manifest.js:951). The division is still correct; only the rationale is wrong. Fix: reword.
3. README:1200 / commit messages (carry) — "690 checks" reproduces only against an `export/out` whose
   manifests already carry the block. On MAIN today it is **673** and spec_gate_test is 43: the 15
   manifest_test rows and the 2 spec_gate §6 rows skip loudly. Expect 690 only after the lead runs
   `manifest_v4.py` in MAIN — not a regression.
4. `web/src/materials.js:214` (carry) — the sun gate multiplies *all* direct specular. Correct today
   because main.js:651 adds exactly one light; note the invariant if a second light is ever added.
5. `export/manifest_v4.py:446-448` (carry) — a stale `scene_audit.json` (found via MAIN by `find()`)
   aborts the whole manifest write with an AssertionError, though the assert never changes the value
   written. Consider a printed WARNING if the re-bake chain can reach manifest_v4 before gate3_set.py.
6. `.claude/worktrees/phase9-viewer-shade/export/out` (carry, hygiene) — the read-only mirror is still
   there and `gate0/1/2` are *directory* symlinks into MAIN. Delete it after the merge.
