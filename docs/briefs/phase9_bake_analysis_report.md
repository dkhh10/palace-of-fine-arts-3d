# Phase 9 bake analysis — the lighting re-bake chain, priced; station 3's shade excess, decomposed
Bake engineer, branch `phase9-bake`, 2026-09-20. CPU only: no Blender run, no bake, no Chrome, no GPU.
Every number below is measured from files already on disk (`export/out/gate3/bake/*.json`, the archival EXRs in the
`phase6-bake` worktree, the shipped KTX2, the manifest, the frames named in the brief) by
`export/p9_shade_terms.py` (committed on this branch) or by the one-line probes quoted beside it.
*Provenance note (review r1 fix 3):* the script does not read the bake JSON (A.1's wall times were summed by a one-line probe over
`export/out/gate3/bake/*.json`, reproduced exactly by the review), and B.3's equirect means and B.6's decile table / sky constants have no
committed producer here. The constants (2.196, 3.432, 11.256) and 21.428 are NOT to be hard-coded in the viewer: per docs/decisions.md
(session 10) `export/manifest_v4.py` re-derives them from the shipped sky_diffuse EXR and the sun energy on every manifest run.

---

# Part A — the chain that follows a change to `assets/lighting.blend`

## A.0 The premise of docs/briefs/phase9_light.md needs one correction before the chain is priced

`LIGHT_shade_fill` is **not in the delivery rig and not in the bake rig**. `scripts/light_build.py:562` has shipped
`energy=0.0, energy_eevee=0.0` since commit `f40d0e7` ("QA-10-2 jamb: LIGHT_shade_fill energy 49 -> 0 … lighting.blend
rebuilt"), and `build_shade_fill` builds **no lamps at all** when both energies are zero (r11 review fix 4). The Gate 3
scene audit confirms it on the file that was actually baked: `export/out/gate3/scene_audit.json` → `bake.lights` is
**20 lights — 16 `LIGHT_gallery_fill_*`, `LIGHT_rotunda_bounce`, 2 `LIGHT_rotunda_vault_bounce_*`, `LIGHT_sun` — and
no `LIGHT_shade_fill`**. So station 2's blue-violet shaded stone cannot be "the direct NNE sky fill at 70 W/m²"; the
only anti-sun blue left in the rig is the **world's diffuse branch** (`SKY_DIFFUSE_TINT = (1.0, 0.65, 70.0)`, round 16,
anti-sun weighted, `light_build.py:125`). This matters for the chain because the two classes skip different things.
**Hand-off to LIGHTING: say in your report which of the two you changed — a lamp, or diffuse-branch sockets.**

Two other facts the chain depends on, both verified in code:
* The diffuse tints are gated `Fac = 1 − min(Is Camera Ray + Is Glossy Ray, 1)` (`scripts/light_calibrate.py:264-380`),
  so **`sky.camera` and `sky.glossy` are held still by construction** when only `SKY_DIFFUSE_*` moves. The LUT is the
  view transform and does not move unless the look or the exposure moves (it does not).
* `LIGHT_shade_fill` is a **SUN** lamp (infinite, az 25 / el 2). Re-arming it reaches every NNE-facing surface in the
  scene *and* the impostor nursery. There is no hero-only subset: the ARCH masses are merged (one map wraps the whole
  rotunda), so no own map can be skipped on geometry grounds.

## A.1 The priced chain — measured GPU seconds, per job group

All wall times are the records' own `wall_s` (`export/out/gate3/bake/*.json`, 109 records, 0 failures). "Lamp" = a
`LIGHT_*` energy/colour/angle change with the world untouched; "Sky-d" = a `SKY_DIFFUSE_*` socket change with the lamps
untouched. Ordered as `bake_queue.sh --gate3` runs them.

| # | job group | script / job id | n | measured GPU wall | lamp? | sky-d? | why |
|---|---|---|---|---|---|---|---|
| 1 | own lightmaps | `bake_lm.py --job lm_*` | 16 | **9 481.5 s** (158.0 m, mean 592.6) | **re-bake** | **re-bake** | Cycles diffuse pass; every lamp and the diffuse world are inside it |
| 2 | ORN slot atlases | `slot_orn_*` | 12 | **5 697.3 s** (95.0 m) | **re-bake** | **re-bake** | same bake, 988 instances over 5 atlases |
| 3 | ARCH slot atlases | `slot_arch_inst_*` | 15 | **7 023.0 s** (117.0 m) | **re-bake** | **re-bake** | idem |
| 4 | near-tree vertex colour | `vc_00/01` | 2 | **113.9 s** | **re-bake** | **re-bake** | COLOR_0 = baked irradiance on the 14 near trees |
| 5 | shrub/reed instance irradiance | `inst_irr_00..03` | 4 | **2 510.3 s** (41.8 m) | **re-bake** | **re-bake** | 1 379 placements, 128 spp, shadow-ray override |
| 6 | far-tree instance irradiance | `tfirr_00..03` | 4 | **779.3 s** (13.0 m) | **re-bake** | **re-bake** | 166 placements (127 + the 39 belt); see A.4 |
| 7 | far-tree prototype `E_bake` | `tfeb_*` | 16 | **144.9 s** | **re-bake** | **re-bake** | the impostor divisor; must be baked in the same rig as the atlas |
| 8 | impostor atlases | `imp_*` | 16 | **777.8 s** (13.0 m) | **re-bake**† | **re-bake**† | the nursery carries the real rig (`rig.lights = 20`, `world = WORLD_golden_hour`) |
| 9 | far-tree vertex AO | `tfao_*` | 16 | 23.6 s | **SKIP** | **SKIP** | `world = GATE3_ao_white`, `rig.lights = 0` — no rig in it at all |
| 10 | gate1-layout own maps | `lmg1_*` | 2 | 66.4 s | **SKIP** | **SKIP** | dead weight: all 16 assets now ship `uv2_in_glb: true`; retire them |
| 11 | hero probe cube | `probe_hero` | 1 | **140.5 s** | **re-bake** | **re-bake** | it is a render of the SCENE; its first bounce is diffuse |
| 12 | `sky.diffuse` equirect | `sky_diffuse` | 1 | **1.7 s** | SKIP | **re-bake** | pure world render of the diffuse branch |
| 13 | `sky.camera` / `sky.glossy` equirects | `bake_lut.py` (gate0) | 2 | not in the gate3 queue | SKIP | SKIP | branch-isolated; the diffuse tints are gated off camera and glossy rays |
| 14 | the AgX LUT | `bake_lut.py` | 1 | — | SKIP | SKIP | the look and the exposure are frozen |
| — | diagnostics (`inst_probe*`, `inst_split*`) | — | 4 | 129.4 s | n/a | n/a | not part of a re-bake |

**Totals.**
* **FULL chain (lamp change):** rows 1–8 + 11 = **86 jobs, 26 668 s GPU = 7 h 24 m.**
* **FULL chain (diffuse-socket change):** rows 1–8 + 11 + 12 = **87 jobs, 26 670 s = 7 h 24 m.**
* **What the "skip" column actually saves:** 90 s (rows 9 + 10). The lighting change is a *global* change; there is no
  cheap subset by asset. The Gate 3 queue measured 23 495 s wall for its 65 jobs against 23 419 s of records, so queue
  overhead is ~0.3 % — the table is the wall.

## A.2 The only real lever: a two-job probe before the 7 h is spent

The honest reduction is by **measured delta**, not by asset:

1. Re-bake **one own map** — `ARCH_rotunda_dome_membrane_merged`, the cheapest at **108.3 s** — plus `sky_diffuse`
   (1.7 s), and, for a slot verdict, **one slot batch** — `slot_arch_inst_1_06`, 16 instances, **205.9 s**.
2. Compare the new EXR to the old one in stops. The floor is the shipped texture's own error, which I measured for the
   first time on the KTX2 itself (Part B, term 1): **p50 0.015–0.097 stops, p99 0.097–1.077 stops**.
3. **If the change is under that floor, ship the lighting with the OLD bake** — total cost **3 jobs, 316 s**, nothing
   re-packed, nothing re-pinned, and the viewer's parity is untouched.
4. If the own maps move but the slot atlases do not (the likely case for a low anti-sun lamp: the ornament sits in
   niches and the slot bake is dominated by the local bounce), the **reduced chain** is rows 1, 4, 5, 6, 7, 11, 12 =
   **44 jobs, 13 172 s = 3 h 39 m** — the 27 slot atlases are **12 720 s = 47 % of the whole chain**, the single
   biggest saving available.

## A.3 After the queue — pack, manifest, tiers, verify, deploy (CPU)

Before the bake, the gate: rebuild `master.blend` (`scripts/lead_build.sh`) → regenerate `master_delivery.blend`
(`PFA_PACK=1 scripts/phase5_deliver.sh 1b`) → `export_set.py --gate1` + **`python3 export/p8d_pin.py`** (21 checks; the
"8a export gate" rule, docs/decisions.md 2026-09-19). The pin is what says the geometry did **not** move, so the new
lightmaps land on the same UV2 and **no GLB has to be re-exported or re-packed**. Stop if it fails.
Then `gate3_probe.py` (6.9 s) → `gate3_set.py` (20.5 s) → the queue → and afterwards:

```sh
export/gate3_pack.sh                     # EXR -> PNG encode 51.9 s measured + toktx over the maps that changed (~1-3 min)
python3 export/manifest_v2.py && python3 export/manifest_v3.py && python3 export/manifest_v4.py   # v2 FIRST
python3 export/budget_doc.py && export/sync_main.sh
python3 export/tiers.py && python3 export/tiers.py --mobile && python3 export/tiers.py --no-pack  # ~2-5 min
python3 export/verify_glb.py --gate5 && (cd web && node test/tiers_test.mjs) && python3 export/name_sweep.py
export/sync_main.sh                      # then the web build + deploy
```

**What re-pins.** Only the manifests: `manifest_v4.py` rewrites `lightmaps.assets[*].range` and `.stats` and
`textures.gate3.files[*].stats`, and `gate3_encode.py` sets each map's `range` to **that map's own maximum**, so the
range moves whenever the bake moves. Tier files re-pin because the KTX2 bytes change (`tiers.py` ×3), and
`verify_glb --gate5` + `tiers_test` re-assert the 50 MB first-frame rule. The GLBs, the Gate 1/Gate 2 pins and
`backdrop_uv1_shipped.npz` do **not** move for a lighting-only change.
**Never ship a new texture against an old manifest.** I measured the failure mode exactly: decoding the colonnade
lightmap at the old `range = 64` instead of the manifest's `44.409718` gives a flat **1.441x** (= 64/44.41) on every
texel — a full half-stop of extra light, everywhere.

## A.4 Resume, partial failure, and the QA-23 far-tree rule

* `export/bake_queue.sh --gate3` is detached and owns the GPU while `export/out/bake_queue/status.json` says
  `running`; idleness is read from that file only, never from CPU or log silence. It runs **one Blender per job**
  through `scripts/blender_run.sh` and records `{id, wall_s, rc, at}` per job.
* **Resume** = re-run the queue: a job whose record JSON exists in `out/gate3/bake/` is skipped. **To force one job,
  delete its record** (the Phase 8d chain does exactly this: `rm export/out/gate2/bake/ENVBD__*.json`). A crashed
  queue leaves `state: running` with an `expires_at`; the watchdog kills only pids past their registered duration.
* **QA-23 far-tree rule.** The shipped `trees_far/instance_irradiance.json` is a **merge**: 127 rows from the 6c bake
  (md5 `11212fbcc3bbe8482f5396f8a8f9917b`, 2026-09-17) and 39 hall-belt rows from the 8d-r2 bake, joined by world
  location on a 0.02 m grid, each row carrying `source`. It exists because a **partial** re-bake — the belt alone, at a
  different scene state — brightened every crown by 4–16 % and moved 7 of 10 boxes *away* from the Cycles references.
  For Phase 9 that means: **re-bake all 166 placements in one `tfirr_00..03` set at the new rig, or re-bake none.** The
  four jobs already cover the whole population (`override_scope.objects = 166`, 42 placements per job). A re-bake makes
  `export/p8d_irr_restore.py`'s 6c source stale — retire it in the same commit, or the file's `rows_source` block will
  claim a provenance it no longer has.
* **The impostor "neutral nursery" question** (†, row 8). `gate3_imp.blend` is one prototype alone on a lawn, but the
  record shows it is baked in the **real rig** (`rig.lights = 20`, `world = WORLD_golden_hour`, 64 spp). The viewer then
  draws `atlas_frame × (E_placement / E_bake)` **per channel**, so a change that scales the nursery's irradiance is
  cancelled by the divisor and only the **directional** part survives (which side of the crown is lit). Skip rule, with
  its number: skip the 16 atlases (777.8 s) and re-bake only the 16 `E_bake` values (144.9 s) **when the changed lamp's
  irradiance at the nursery is under ~5 % of `LIGHT_sun`'s 67.32 W/m² (i.e. under 3.4 W/m²)**. A re-armed NNE lamp at
  the round-14 value of 70 W/m² is 104 % of the sun and cannot be skipped; a diffuse-socket change moves the sky the
  nursery sees and cannot be skipped either.

---

# Part B — station 3: where the viewer's shade brightness comes from

## B.0 Method

Viewer `renders/web/gate12_cam03.png` against Cycles `renders/qa_comparisons/cycles_p8/cam03_1080_32spp.png` (the
lead's reference, rendered today from the current master; it agrees with the round-13 frame to MAE 2.01/255). Both are
inverted to **scene-linear through the delivery LUT itself** — a full 3-D Gauss-Newton inverse of
`lut_agx_high_contrast_65.cube` at −2.8331399 EV, exact to <1e-4 display units, not a per-channel approximation —
because the terms are additive in linear and not in display. Pixels at or above display 245 in either frame are
excluded (an 8-bit ceiling inverts to nonsense). Boxes: `light_r17_measure` / `light_r14_measure` cam03 (stated at
1280×720, scaled ×1.5), the 8a-4 bush box, and `qa_r13_probe`'s cam03 boxes.

## B.1 What the excess is: a frame-wide ADDITIVE veil, not a gain error

`python3 export/p9_shade_terms.py --boxes`, scene-linear RGB:

| box | n px | Cycles R G B | viewer R G B | excess R G B | excess/Cycles (R) |
|---|---|---|---|---|---|
| near_column (r17) | 457 875 | 0.4880 0.2897 0.0000 | 0.9402 0.6586 0.2398 | **+0.4522 +0.3689 +0.2397** | 0.93x |
| flute_band (r17) | 116 550 | 0.4770 0.2832 0.0000 | 0.9266 0.6465 0.2367 | +0.4496 +0.3633 +0.2367 | 0.94x |
| outer_row (r14) | 345 600 | 0.4621 0.2727 0.0000 | 0.9981 0.7035 0.2614 | +0.5360 +0.4308 +0.2614 | 1.16x |
| shaft_flank (r14) | 80 963 | 1.5588 0.8900 0.0168 | 2.3956 1.4653 0.2833 | +0.8368 +0.5752 +0.2665 | 0.54x |
| walk (r14) | 172 800 | 0.9604 0.7679 0.4969 | 1.3160 1.1134 0.7693 | +0.3557 +0.3455 +0.2724 | 0.37x |
| bush (8a-4) | 35 195 | 0.3260 0.2943 0.0810 | 0.6980 0.5297 0.2012 | +0.3721 +0.2354 +0.1202 | 1.14x |
| fg_foliage (r13) | 264 000 | 0.5573 0.3323 0.0001 | 1.0050 0.6972 0.2436 | +0.4477 +0.3649 +0.2435 | 0.80x |
| near 10–25 m (r13) | 179 969 | 0.7942 0.6509 0.4402 | 1.1281 0.9767 0.7122 | +0.3339 +0.3258 +0.2720 | 0.42x |
| far 120 m+ (r13) | 46 727 | 2.0433 1.0888 0.2117 | 2.4599 1.3745 0.3614 | +0.4166 +0.2858 +0.1497 | 0.20x |
| sunlit_rotunda | 223 815 | 3.7409 1.7261 0.8657 | 2.8334 1.8462 1.0017 | −0.9075 **+0.1201 +0.1359** | −0.24x |

The Cycles level ranges over **11x** (0.33 → 3.74) while the excess barely moves (**+0.33…+0.54 R**, +0.24…+0.43 G,
+0.12…+0.27 B). At 8× downsample the excess R has a 4×6-grid median of 0.15–0.83 and does **not** track the Cycles
brightness, so it is a frame-wide veil, not a local bloom halo. **The defect is additive, ≈ (+0.45, +0.35, +0.24)
scene-linear.** That is why it reads as 2.55x in the column shade, 1.79x on the bush and 1.37x on the pavement: one
constant divided by three different bases. A multiplicative error (albedo, `lightmap_scale`, exposure, the LUT) is ruled
out by the same table — the sunlit rotunda is within **+7 % G / +16 % B** and its red is *low*, not high.

## B.2 Term 1 — the lightmap texels: **not the term**, and measured for the first time on the shipped KTX2

`python3 export/p9_shade_terms.py --lightmaps` transcodes each shipped `..._gamma2.ktx2` (UASTC) back to RGBA8 with
`tools/bin/ktx`, decodes it with the manifest's own per-texture `range`, and compares it to the archival EXR the bake
wrote. This closes a real hole: `export/gate3_encode.py`'s roundtrip numbers (and the README's "gamma2 0.028–0.163
stops") are the **PNG's**; the UASTC step after it had never been measured.

All 16 own maps: whole-map **0.993–0.999x**; the deep-shade tail (texels below the map's own p10) **0.73–0.99x on 14 of
16**; |error| **p50 0.015–0.097 stops, p99 0.097–1.077 stops** over signal texels. The two exceptions are near-black
tails with no pixels behind them (`ENV_riprap` p5 25.6x on a 0.0004 base, `ARCH_site_paving` p10 0.03x). The asset the
`near_column` box stands on, `ARCH_colonnade_south_concrete_colonnade_merged` (range 44.41, 10.95 cm/texel):
**0.997x whole, 0.985x at p20, 0.977x at p10, p50 0.033 / p99 0.373 stops.**

**The shipped lightmap is if anything slightly *darker* in shade than the bake.** Term 1 contributes nothing to the
excess, and the encode/compression chain is clean.

## B.3 Term 2 — the environment specular, unoccluded: it carries all of the viewer's blue

`LIGHT_sun` ships at **(1.0, 0.607324, 0.0)** — zero blue — and the deep-shade bounce off ochre stone is blue-free, so
Cycles' shaded stone at cam03 reads **B < 0.003** (display 0) in all four shade boxes. **Every one of the viewer's
0.2397 blue units there is added after the lightmap.**

`web/src/main.js:assignSpecularEnv` gives every patched material `material.envMap = the glossy sky PMREM` at
`envMapIntensity = 1`, and three.js has **no specular occlusion** — a shaft inside the colonnade reflects the whole open
sky. Measured on the shipped equirect: `sky_glossy_4096x2048.exr` has whole-sphere solid-angle mean radiance
**(4.933, 5.554, 7.045)** and upper-hemisphere cosine-weighted mean **(4.379, 6.276, 10.294)**. At the colonnade's
measured roughness **0.840** (`export/out/gate2/bake/ARCH_colonnade_south__concrete_colonnade__merged.json`, mean over
2 010 103 covered texels) and F0 = 0.04, three.js' `DFGApprox` gives `FssEss = 0.0220` at dotNV 0.7, so the env specular
is between **(0.109, 0.122, 0.155)** and **(0.096, 0.138, 0.226)** depending on where the reflection vector points —
**65–94 % of the measured blue excess.**

## B.4 Term 3 — the sun `DirectionalLight`, specular-only and **unshadowed**: the warm remainder

`web/src/main.js:643-646`: `new THREE.DirectionalLight(sun.color, manifest.sun.irradiance)` at **67.32 W/m²** with
`sunLight.castShadow = false` — "shadows are in the lightmap". They are, for the **diffuse** term only: `materials.js`
deletes `reflectedLight.directDiffuse` and keeps `directSpecular`. So a shaft deep in the colonnade with `dotNL > 0`
takes the same specular lobe as one in full sun.

Subtracting term 2 from the `near_column` excess leaves **(0.356, 0.231, 0.014)** — ratio 1 : 0.65 : 0.04 against the
sun's own 1 : 0.607 : 0. A two-basis solve of the whole excess on (sun colour) + (glossy-sky colour) closes all three
channels to 2 %: **0.284 sun-coloured + 0.168 sky-coloured = (0.452, 0.362, 0.240)** against the measured
(0.452, 0.369, 0.240). **≈ 63 % unshadowed sun specular / 37 % unoccluded sky specular.**

*Honest caveat.* The sun's colour and the deep shade's own colour are collinear to within 2 %, so this basis alone
cannot separate "unshadowed sun specular" from "a lightmap carrying too much warm light". **B.2 is what separates
them** — the lightmap is correct to 0.3 %, and B.1's sunlit boxes rule out any gain error.

## B.5 Term 4 — the post chain: measured, and ~0 at the near column

The only flag captures on disk are station 1's (`renders/web/post_{none,mist,bloom,vignette,all}.png`); there is **no
cam03 capture at any flag**. Masked and inverted (`--post`), on station 1's shaded stone (`shaded_attic`, base
2.767/1.699/0.417): **bloom +0.1557 / +0.1014 / +0.0347**, vignette −0.0073 / −0.0038 / −0.0005, **mist +0.0000** (that
build refused the mist: `compositor.mist` was not yet in the manifest; the gate12 capture *does* carry it —
`mistSpec near 20 / far 2020 / cap 0.25 / k 5 / LINEAR`).

At cam03 the mist term is bounded by its own definition. The r17 near column subtends 33 % of the frame width
(ARCH r8's hand-off), i.e. it stands ~3 m from the station — **inside `mist.start` = 20 m, so mist = 0 on it**. On the
r13 far box (120 m+): `f = 0.25·(1 − e^(−5·0.05)) = 0.055`, adding `0.055·(5.321 − 2.043) = 0.18` R = **43 % of that
box's +0.417**. So post explains part of the far boxes and **none** of the near column; bloom's warm veil is real but is
an order below the 0.45 measured here.

**The capture the viewer engineer must take** (one Chrome run, six frames, no bake): station 3 at 1920×1080 with
`?post=none`, `?probe=0` and `?lighting=direct`, plus the `post=all` control, saved as
`renders/web/p9_cam03_{postnone,probe0,direct,all}.png`. `p9_shade_terms.py --boxes --cycles <ref>` reads them as-is and
will confirm the split above to the channel. It is the only thing missing from this decomposition.

## B.6 Verdict and the one recommended fix

**The 2.55x is the viewer's specular path, which is neither shadowed nor occluded, on a diffuse term that is correct.**
It is a **viewer-side composition** defect. It is *not* bake-side (term 1 measured at 0.997x), and it is *not* a
`lighting.blend` change — Cycles' cam03 shade is the reference and must not be opened.

**Recommended fix — gate the specular path by the sky visibility the lightmap already carries. Zero GPU.**
Because `LIGHT_sun` carries **zero blue**, a lightmap texel's blue channel *is* the sky's own contribution at that
point. Measured on the colonnade map, by luminance decile (EXR, irradiance/π):

| lightmap luma band | mean R G B | `B / 11.256` | reading |
|---|---|---|---|
| p0–10 (deep shade) | 0.051 0.051 0.088 | **0.008** | sees almost no sky |
| p10–25 | 0.244 0.237 0.404 | 0.036 | |
| p25–50 | 0.568 0.544 0.951 | 0.084 | |
| p50–75 | 1.076 1.145 3.622 | 0.322 | half-open |
| p75–95 | 3.190 3.035 9.128 | **0.811** | sky-exposed |
| p95–100 (sunlit) | 16.334 11.130 1.604 | 0.142 | sun-dominated, B/R 0.098 |

`11.256` is the blue of the **open-sky irradiance/π**, measured here as the upper-hemisphere cosine-weighted mean
radiance of the shipped `sky_diffuse_1024x512.exr`: **(2.196, 3.432, 11.256)**. In `web/src/materials.js`, inside the
same `lights_fragment_maps` patch that already deletes the env diffuse:

```glsl
float skyVis = clamp( lightMapIrradiance.b / 11.256, 0.0, 1.0 );                       // IBL specular occlusion
float sunVis = clamp( ( lightMapIrradiance.r - 0.1951 * lightMapIrradiance.b ) / 21.428, 0.0, 1.0 );  // sun visibility
```
`0.1951 = 2.196/11.256` removes the sky's own share of red; `21.428 = 67.32/π` is the sun's direct irradiance/π at
dotNL = 1. Scale `radiance` (the IBL specular) by `skyVis` and `reflectedLight.directSpecular` by `sunVis`.
Checked against the table: deep shade gives `sunVis = (0.051 − 0.195·0.088)/21.428 = 0.0016` ≈ 0, and the sunlit band
gives `(16.33 − 0.195·1.60)/21.428 = 0.747` ≈ its own dotNL — the gate is right at both ends.

**Predicted effect at `near_column`**, from the numbers above: the env term falls from 0.10–0.23 to ~0.005 and the sun
term from 0.284 to ~0.001, so the viewer goes from (0.940, 0.659, 0.240) to **≈ (0.51, 0.31, 0.02)** against Cycles'
(0.488, 0.290, 0.000) — **1.93x → ≈1.05x in R, and the frame's p10 luma from 37.5 toward Cycles' 6.1.** The sunlit
boxes move by ≤ 4 % (there `skyVis` ≈ 0.14 against an env term already ≤ 4 % of the base).

**Chain cost, from Part A: none.** No bake job, no KTX2, no GLB, no pin. Two new manifest constants
(`sky.open_irradiance_over_pi = [2.196, 3.432, 11.256]`, `sun.irradiance_over_pi = 21.428`) written by
`manifest_v4.py`, then `tiers.py` ×3 → `verify_glb --gate5` → `tiers_test` → `name_sweep` → build → deploy: **~10–20
minutes of CPU.** Validate at all six stations, hero parity first.

**The bake-side alternative, priced for comparison:** bake a real specular-occlusion / sun-visibility pair as a second
map. That is rows 1–3 of Part A again (**22 202 s = 6 h 10 m GPU**) plus a new texture set (the slot atlases alone are
106.65 MB resident today, so a second channel set is not affordable inside the 1 200 MB line). Not recommended when the
lightmap's own blue channel already measures the sky visibility.

## B.7 Hand-offs

* **VIEWER** — owns the fix (B.6) and owes the four cam03 flag captures (B.5). Constants supplied and measured here.
* **LIGHTING** — say which class you changed (lamp / diffuse sockets), and note A.0: `LIGHT_shade_fill` is at 0 W and
  is not in the file; the anti-sun blue is `SKY_DIFFUSE_TINT`.
* **EXPORT** — `lmg1_*` (2 maps, 66.4 s, 4 KTX2) is dead weight now that all 16 assets ship `uv2_in_glb: true`; and if
  the far-tree irradiance is ever re-baked, `export/p8d_irr_restore.py` must be retired in the same commit (A.4).
* **LEAD** — the decision A.2 asks for: spend 316 s on the two probe jobs before committing 7 h 24 m of GPU.

---
*Test suites: `web/` is not runnable in this worktree (`node_modules` absent); `export/` has no python suite
(`gate4_order_selftest.py` needs `out/` artefacts that live in MAIN). 0 suites run — stated in every commit message.*
