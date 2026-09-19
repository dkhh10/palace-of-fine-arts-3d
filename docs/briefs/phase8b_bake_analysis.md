# Phase 8b — far-tree impostor atlas alpha: analysis (no GPU, no Blender). Probe: `export/p8_atlas_probe.py` → `export/out/p8/`

Sources: the Gate 3 composed 1K/2K albedo PNGs (straight alpha), `impostor_diag_{atlas,ref}.json`, `renders/previews/qa/round13_02_lagoon_ne_threequarter_cycles.png`.
Prototypes broadleaf_s53 / cypress_s3 / pine_s7, each at its own **cam02 frame** (1/7, 9/8, 4/10). 100 % crop pair: `export/out/p8/p8_crownpair_100pct.png`.

## (a) The atlas alpha is NOT the problem
- **Nothing thresholds, dilates or erodes alpha.** `bake_lm.py` (`kind == "impostor"`) writes `clip(Combined.A, 0, 1)` straight
  (the 0.02 floor is only on the RGB un-premultiply); `reduce2` (2K→1K) is a premultiplied 2x2 box — correct, but a low-pass
  on alpha; `trees_far_compose.py`, `gate3_compose.py`, `gate3_encode.py` carry no alpha op at all.
- The alpha is almost entirely **partial** (broadleaf / cypress / pine, 1K): of the covered crown-top texels **93.5 / 100 /
  97.5 %** are `0 < a < 1`; only **0.7 / 0.0 / 0.2 %** are fully opaque. Mean alpha, crown top **0.055 / 0.018 / 0.026** vs
  trunk band **0.155 / 0.223 / 0.210** — the crown top is the thinnest, most partial part, where the cut hurts most.
- The viewer's `ALPHA_TEST = 0.33` makes **2.3–5.9 %** of crown-top texels *fully opaque* and discards 1.3–4.2 %. The a2c
  ramp `(a-0.33)/fwidth(a)` cannot help: under 9–12x magnification `fwidth(a)` is ~1/10 of a texel step, so the ramp
  saturates and the mask is binary — a texel at `a = 0.45` paints **81 solid screen px** where 45 % should be sky.
- The 3-frame octahedral blend is **not** the cause: crown interior sky goes 21.2→28.4 / 14.3→19.3 / 27.2→26.8 %.

## (b) Atlas frame vs the Cycles crown at station 2 — resolution first, then the binary cut
- The bake maps the bounding-sphere diameter onto the frame's inner 81 px (1K) / 162 px (2K); at station 2 the same
  broadleaf crown (40.19 m) is **736 px** across at 1920x1080. One 1K texel = **9.1 screen px at 1080p, 12.1 at 1440p**;
  at 2K, 4.5 / 6.1 px.
- Silhouette detail density (foliage↔gap crossings per 100 screen px, same measure both sides): **Cycles 7.76** ·
  **1K atlas 2.40** (31 %) · **2K atlas 3.28** (42 %). Per 100 *texels* the 1K frame scores 21.8 — the bake's leaf density
  is right; the frame is simply ~3x too coarse for the screen.
- **Diagnosis: (1) frame resolution — 85 px frames magnified 12x at the hero; (2) the viewer resolving that coverage alpha as a binary mask. Not the compose, not leaf density, not the view blend.**

## (c) Options, costed (today: 32.00 MB GPU, 5.77 MB payload; bake median 50.5 s/prototype, 787 s for all 16)
| option | GPU time | GPU mem | payload | detail |
|---|---|---|---|---|
| **1. ship the 2K albedo** (already on disk; `tiers.py` strips the 2K keys today) | **0 s** | +48 MB | +6.4 MB | 2.40→**3.28** |
| **2. coverage instead of a binary cut** (viewer: feed atlas alpha to a2c/dither under magnification) | **0 s** | 0 | 0 | recovers the *amount* of sky |
| 3. 4K atlas (341 px frames) | ~202 s/proto, **54 min** | **512 MB** | +37 MB | ~5–6 |
| 4. band atlas, 12 az x 3 el at 341 px (4096x1024) | ~787 s, **13 min** | 128 MB | +13 MB | ~5–6; bake+export+viewer in lockstep |
| 5. alpha remap in the compose (raise the crown cut) | 0 s | 0 | 0 | 0.33→0.70 gives only 2.40→**3.54** and eats 5 % of the silhouette |

**Recommended: 1 + 2 together.** 2 is the real fix (80–100 % of the crown is semi-transparent and every texel above 0.33
paints solid); 1 halves the texel footprint for free. **Watch the payload:** 46.81 MB of a 50 MB cap, so +6.4 MB needs the
atlases out of the first frame, or desktop-only (mobile stays 1K). Reject 3 (out of budget) and 5 (an eaten crown, not a
twiggy one); 4 is the stretch if 1+2 miss. **Lead's call — no export-chain edit made.**
