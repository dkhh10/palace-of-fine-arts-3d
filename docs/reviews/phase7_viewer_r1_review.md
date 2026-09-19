# MERGE WITH FIXES — `phase7-viewer` @ ca558ae vs main a26228f (Opus 5, read-only, no Blender/Chrome)

## Verified correct (the brief's specific checks)
- **Premultiplied reconstruction cannot shift an opaque texel.** `impostors.js:212-233`: barycentric `w`
  sums to 1 and is non-negative in both cell triangles (`:180-195`), the four bilinear weights sum to 1,
  so for a=1 texels `accA` = 1 exactly and `rgb = acc/accA` is a pure weighted mean. The hand bilinear
  reproduces the hardware footprint exactly (`frameTexel` returns `px` and `atlasPx-1-pyFromBottom`,
  which is `uv*atlasPx-0.5` on both axes), and the atlas is `LinearFilter` with `generateMipmaps=false`
  (`:500-502`), so the texel-centre taps have no LOD ambiguity.
- **A2C is never enabled without MSAA.** `parseImpEdge(v, msaa)` ANDs `a2c` with `msaa` (`:345`), fed from
  `foliageReport.msaa` (`main.js:1090`), which tests composer `samples > 0` or ctx `SAMPLES > 0`
  (`main.js:1011`). Renderer is `alpha` unset (`main.js:189`), so the README's opaque-canvas claim holds.
- **Floors cannot exceed 1 or invert.** Both clamped to [0,1] (`impostors.js:325`, `foliage.js:157-159`)
  and applied as `max(factor, floor)` on factors that are themselves ≤1, so they only raise, never brighten
  past unity. `interiorOff` (`foliage.js:162`) ignores `floor`, which is harmless: with every term off the
  factor is already 1.
- **Tier defaults only where the URL asked nothing**: `set()` guards on `!qs.has(key)` (`main.js:210`), and
  the new `set('impint', …)` follows it.
- **treemesh 80 costs no payload**: `meshDist` is a runtime switch only; `loadLazyFoliage()` runs after the
  tiers regardless (`main.js:871`), and the committed JSONs show identical draws/tris/resident at 40/60/80.
- **A/B arithmetic checks out** against all 16 perf JSONs: every median, delta, drift, triangle and draw
  figure in README "Phase 7" tables C and the A+B cost table reproduces exactly; mobile +190.0 / +188.3 /
  +62.2 / +1.7 MB all reconcile (decimal MB, as 6b used).

## Findings
1. **fix now** — `renders/web/p7basem_orbit{,_h02150,_h02530}.png` (1170x2532, 1.0–3.0 MB) are tracked at
   ca558ae although the same branch's `.gitignore:87` says `renders/web/p7*.png`. `git rm --cached` all three.
2. **fix now** — no committed script measures the branch's three equivalence/engagement headlines: the
   6c-restore MAE (0.0001/0.0000/0.0005), premul 4.95–6.97 % and a2c 0.60–3.10 % of pixels, and the mesh-floor
   0.005–0.012 %. `scripts/qa_p7_probe.py` has only crown/edge/frame. Add a `diff <tagA> <tagB>` command.
3. **fix now** — README item D reports resident memory only; the committed JSONs show mobile *downloaded*
   bytes 61.49 → 69.56 MB (**+8.06 MB**, `p7basem_perf.json` vs `p7m_orbit_perf.json`). Add that row.
4. **carry** — `scripts/qa_p7_probe.py:34` uses `PFA_QA_ROOT`; the repo convention is `PFA_MAIN_ROOT`
   (`env_sheet_r8.py`, `light_r11_sweep.py`, `p7.sh:24`), so `p7.sh`'s export does not steer the probe.
5. **carry** — two committed captures exceed 960 px: `p7_D_mobile_orbit.jpg` 1224, `p7_D_mobile_stations.jpg` 965.
6. **carry** — `?leafsoft=0` silently disables impostor a2c, and the boot note then reports "asked but OFF
   (no multisampled target)", which is the wrong reason (`impostors.js:531-533`).
7. **carry** — an unrecognised `?impedge=` value silently falls back to both; and `debugMode==1` now returns the
   reconstructed `rgb` (`:339`), so `?impedge=0` is byte-identical only outside that debug path.
8. **carry** — evidence for the mobile stations 2–6 row and for "`?fartreemesh=` is inert" lives in the
   gitignored `p7*_cam.json` / `p7*_shot.json`; the committed perf JSONs support it only indirectly.
9. **carry** — mobile 689.7 MB vs the 700 MB ceiling is Mac-proxy only; no iPhone run. `?walkupmesh=0` (561.9 MB)
   is the documented lever. Lead: the adopted defaults (treemesh 80, floors 0.35) need a `docs/decisions.md` entry.
