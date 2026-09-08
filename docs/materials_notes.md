# Materials library notes (Materials & Texturing specialist)

Library: `assets/materials.blend` (built by `scripts/mat_build.py`; helpers in `scripts/mat_lib.py`). Every material carries
`use_fake_user`. Test scene: collection `MAT_test` in the same file. Lineup renders: `scripts/mat_lineup.py` into
`renders/previews/materials/`. Comparisons: `renders/qa_comparisons/materials_r*_*.png`.

```
blender -b --python scripts/mat_fetch_textures.py      # once: CC0 Poly Haven sets -> assets/textures/polyhaven/ (network)
blender -b --python scripts/mat_leaf_textures.py       # procedural foliage RGBA cards -> assets/textures/foliage/
blender -b --python scripts/mat_build.py               # rebuilds assets/materials.blend from scratch (idempotent)
blender -b --python scripts/mat_lineup.py -- [--engine eevee|cycles|both] [--quick] [--rig] [--env] [--cams a,b,hero]
                                              [--debug "Streak Mask"] [--neutral] [--no-hero] [--spp 128]
blender -b --python scripts/mat_measure.py -- render.png x,y,w,h ...     # mean sRGB/linear of rectangles
```
`--rig` links the lighting agent's `LIGHT` + `WORLD_golden_hour` + look (exposure -3.9 EV, AgX Base Contrast) instead of
the local test sun; `--env` appends `ENV` into the hero scene (materials remapped by name) so foliage is checked at 120 m;
`--neutral` is a lab light (white sun at irradiance pi, black world, Standard view) so rendered pixel values ARE albedo;
`--debug <output>` emits one mask of the concrete group (Streak/Ledge/Edge/Dirt/Algae Mask, Tone) for calibration.

## How the library is meant to be used
- Assign by name: `common.load_material("MAT_concrete_ochre")`. Appending pulls the `PFA_*` node groups and the images
  along; image paths are relative (`//textures/...`), so `assets/textures/` must travel with the library.
- **Lead / build_master: append all needed materials in ONE `bpy.data.libraries.load` call** (or link the library).
  Appending one material at a time creates `PFA_concrete.001`, `.002` ... copies of the shared node groups and images.
  `mat_lib.dedupe_node_groups()` remaps such copies back to the originals after an append.
- Nothing depends on scene objects. The only scene constant baked into node values is `common.WATER_Z` (-1.3 m), the
  centre of the algae band (`Algae Z` input of the concrete group on MAT_concrete_podium, and the rip-rap). If the water
  level changes: rebuild the library (or edit the `Algae Z` value on the group node).
- All concrete/stone/bark/ground materials are UV-free: photo textures are box-projected on object coordinates, procedural
  layers use object coordinates (+ a per-instance random offset) or the world position/normal. Foliage cards use `UVMap`.
- ORN baked maps: `MAT_ornament_concrete` has two empty image nodes `BAKED_NORMAL`, `BAKED_AO` and a value node
  `BAKED_WEIGHT` (0). To use an asset's bakes: duplicate the material (`MAT_ornament_concrete__<asset>`), set the two
  images (normal: Non-Color, OpenGL tangent space, needs the asset's UVs; AO: Non-Color) and `BAKED_WEIGHT` = 1. The AO map
  adds to the recess-dirt term, the normal map becomes the base normal under the procedural bump. Without bakes the
  material is fully geometry-driven (AO node + Bevel node), which already gives dust in the hollows on LOD0/LOD1 meshes.

## Shared node groups
| group | what it does | engines |
|---|---|---|
| `PFA_instance` | Object Info Random -> 4 decorrelated randoms + a 3D pattern offset (per object / per instance); `Seed` decorrelates materials | both |
| `PFA_edge` | convex-edge mask = max(Bevel-normal difference x3 [Cycles only], inside-AO thinness mapped 0.9->0.7 [both]) | both (weaker in Eevee) |
| `PFA_streaks` | vertical rain-streak field in world space (10:1 stretched FBM, two octaves, drips fade along their length), only on vertical faces, weighted by a *shelter* term: `1 - AO(normal, Ledge Distance)` so streaks concentrate under cornices/ledges and in corners; optional north-face bias | both |
| `PFA_algae` | dark band up to `Band Z + Height x (0.55..1.35 by noise)` with mottling, plus a pale efflorescence zone above it (x/y-only instance offset so z stays world height) | both |
| `PFA_concrete` | the concrete stack (below); inputs are the material parameters, outputs Color/Roughness/Normal + debug masks | both |
| `PFA_column` | drum joints and per-drum tone (object z / `Drum Height`), dark zone under the capital (`Top Z`), pale wash streaks | both |
| `PFA_dome` | membrane: meridional lap seams (`Seams`=48 -> ~2.2 m at the base), radial streaks in polar coords, moss on the north (-X) flank, grime ring at the base (from the world normal's z so it works for any dome origin) | both |

## The concrete stack (`PFA_concrete`), in evaluation order
1. base albedo (sheet values, warmed: see "calibration") with per-instance hue +-0.3 % (~1.7 deg) / value +-11 %, plus
   `wvar` = a per-instance weathering multiplier (0.05..1.9 at `Instance Variation` 1.7) applied to the streak, ledge and
   recess-dirt masks. Round 3: the per-instance spread is VALUE and WEATHERING, not hue (QA-02-2);
2. tone: soft drift (`Drift Size`, 8-22 m, +-`Tone Variation`) x mid-scale mottle (`Blotch Size`, +-`Tone Variation`) x
   noise-warped cast-block steps (`Block Size`, only +-0.35 x TV, borders broken so they do not read as pasted blotches)
   x fine speckle (30/m, +-7 %);
3. photo detail: box-projected CC0 concrete diffuse used as *luminance only*, normalised by its mean (`Detail Mean`) so it
   never changes the hue, weight `Detail Strength`; its roughness map modulates roughness, its displacement drives the bump;
4. grey/damp drift toward `Grey Color`: 0.7 x (world z below `Grey Below Z`..`Grey Above Z`) + noise; the lower 8 m of the
   rotunda go grey-tan, the attic stays warm;
5. formwork/pour lines every `Pour Spacing` (object z), broken by noise; slab grid joints (`Grid Joints`, paving);
6. repair patches: noise-warped Chebychev cells with a 0.05-wide threshold ramp (feathered skim coats, not stencils),
   +6 % value, -8 % saturation, tiny bump step;
7. ledge run-off band (`PFA_streaks` Ledge x 0.40 x `Streaks` x `wvar`), tint x (0.74, 0.695, 0.615): the continuous
   soiling directly under every overhang; then rain streaks (`PFA_streaks` x `Streaks` x `wvar`), tint x
   (0.46, 0.405, 0.325) -- warm dark grey, R > G > B. Round 3: the old (0.36, 0.37, 0.31) had G > R and was the olive
   cast QA-02-2 measured on the shaded piers and arch soffits;
8. recess dirt: `1 - AO(Recess Distance)` x `Recess Dirt` x `wvar` (+ `Extra Dirt` from bakes, + `Underside Dirt` on
   down-facing faces for soffits), tint x (0.56, 0.495, 0.405);
9. edge wear (`PFA_edge` x `Edge Wear`): +22 % value, -15 % saturation, -0.15 roughness on convex arrises. `Edge Radius`
   is 0.10-0.12 m on wall-scale materials (0.05 on ornament, whose features are 0.4 m): at the hero's 7 cm/px a 3 cm
   arris is sub-pixel and cannot read, which is why round 2 scored "no edge wear anywhere" (QA-02-3);
10. algae band + efflorescence (`Algae`, `Algae Z`, `Algae Height`): band -> 65 % toward (0.045, 0.07, 0.04), roughness 0.45
    (slick); efflorescence -> chalky (0.58, 0.56, 0.50), roughness 0.92;
11. bird droppings on up-facing surfaces (sparse Voronoi, `Bird Droppings`, ornament only);
12. roughness = base +- variation (noise 4/m) + 0.3 x photo roughness + dirt - edge wear + streaks; normal = Bump(photo
    height x strength + fine grain - lines - joints + patch step, `Bump`, distance 15 mm).

## Materials
Base albedos are linear RGB. "Y" = luminance. Photo texture sets are CC0 from Poly Haven (URLs + license in
`assets/textures/polyhaven/sources.json`; 2K JPG diffuse/rough/normal/AO/displacement; 100 MB total).

| material | base albedo (Y) | texture set | notes |
|---|---|---|---|
| MAT_concrete_ochre | (0.640, 0.398, 0.070) Y 0.43 | concrete_wall_008 (2.71 m tile: precast panel with tie holes + faint joints) | upper rotunda: walls, entablature, attic, drum. Streaks 1.0 under ledges (shelter 3 m, weight 0.55), patches 0.25, edge wear 0.45 @ 3 cm, recess dirt 0.55 @ 0.4 m, pour lines 0.6 m, rough 0.78 +- 0.12 |
| MAT_concrete_podium | (0.37, 0.30, 0.19) Y 0.31 | concrete_wall_007 (2.16 m: streaky, pour layers) | piers, pedestals, rostra, platform; greyer/damper (grey drift 0.5 below z 0.5..5), **algae band at WATER_Z** (height 0.6), patches 0.35 |
| MAT_concrete_colonnade | (0.48, 0.315, 0.135) Y 0.34 | concrete_wall_007 | strongest streaks (0.8, 12 m long, shade-side bias 0.6 = north/-X faces), shelter weight 0.4 so shafts streak too |
| MAT_concrete_inner | (0.36, 0.27, 0.14) Y 0.28 | concrete_wall_008 | vault soffits / inner rings: full grey drift, recess dirt 0.7 @ 0.5 m, underside soot 0.6, rough 0.85 |
| MAT_ornament_concrete | (0.47, 0.31, 0.135) | concrete_wall_008 (0.4) | capitals, maidens, urns, panels: recess dirt 0.75 @ 0.3 m, edge wear 0.5 @ 2 cm, streaks 0.35 (5/m, short), bird droppings 0.12, instance variation 1.0, baked-map hooks |
| MAT_column_rose | (0.40, 0.165, 0.105) Y 0.21 | concrete_wall_008 (0.45) | 16 fluted pink shafts: dusty terracotta; `PFA_column` drums 3.25 m (+-7 %), dark zone in the top 1.8 m below `Top Z` 16.3, mauve-grey wash (0.42, 0.24, 0.21) streaks 0.55; flute hollows darken by AO, fillets lighten by edge wear |
| MAT_column_tan_inner | (0.45, 0.32, 0.15) | concrete_wall_008 | 8 inner columns: drums 3.0 m, `Top Z` 11, wash 0.35 |
| MAT_paving | (0.45, 0.45, 0.42) | concrete_wall_008 | platform floor/steps: 1.5 m slab joints (object x/y), patches, rough 0.7 |
| MAT_plaster_ceiling | (0.50, 0.40, 0.23) | concrete_wall_008 (0.3) | coffers: recess dirt 0.7, rough 0.9, low specular |
| MAT_drum_band | (0.28, 0.18, 0.09) | concrete_wall_007 | bronze-brown guilloche: recess dirt 0.7 @ 0.25 m -> 0.15 in the pattern hollows |
| MAT_backdrop_building | (0.50, 0.42, 0.27) | concrete_wall_008 (0.3) | exhibition hall / massing: coarse 4-6 m variation, streaks 0.4 |
| MAT_dome_membrane | (0.905, 0.720, 0.442) | procedural | semi-gloss urethane: roughness 0.35 (+0.22 in streaks), Coat 0.4 where clean, specular 0.5; 48 lap seams (5 cm, bump), radial streaks strongest on the lower third (`Base Normal Z` 0.66 = the cap's base slope), moss patches (0.34, 0.42, 0.28) on the -X flank, grime ring (0.20, 0.13, 0.06) at the base with a 6 mm-in-nz irregular edge |
| MAT_water_lagoon | Cycles: green murk base (0.042,0.084,0.055)..(0.078,0.140,0.086), IOR 1.333, transmission 0.45 + volume; Eevee: opaque murk (0.025-0.045, 0.05-0.075, 0.035-0.045) glossy, IOR 1.333 | procedural | roughness 0.02-0.06 (noise 0.12/m), normal = bump of 0.3 m + 3 m + 0.1 m ripple noises (4D, `WATER_TIME` value driven by `frame*0.03`), calmer patches (wind shadow, 25 m noise); volume (Cycles output): one Principled Volume, density 0.5, scatter colour (0.06, 0.10, 0.07), absorption colour (0.23, 0.45, 0.21), anisotropy 0.4 (= absorption ~0.39/0.28/0.40 per m + weak scatter; Absorption+Scatter+Add exceeded Cycles' 64-closure budget). Two Material Output nodes (`target` CYCLES / EEVEE); the Eevee one is Diffuse+Glossy by Fresnel |
| MAT_lawn | green (0.11, 0.19, 0.05) / dry (0.22, 0.21, 0.07) / wet (0.07, 0.13, 0.035) | procedural | patchy November lawn: 8 m dry patches, 12 m damp patches, blade grain 90/m (+-25 %), bump, rough 0.85, sheen 0.1 |
| MAT_soil | (0.18, 0.12, 0.08) mixed 40 % with the photo | forest_ground_04 (3.15 m) | bump 0.5, rough 0.9 |
| MAT_gravel_path | (0.32, 0.28, 0.21) mixed 45 % with the photo | gravelly_sand (2.48 m) | decomposed granite; damp patches |
| MAT_rock_riprap | (0.30, 0.28, 0.22) per-instance hue +-3 % value +-15 % | rock_boulder_dry (1.8 m) | lichen speckle on up-faces, dark wet band below WATER_Z + 0.05 (+0.35 m), AO dirt |
| MAT_bark_cypress | (0.20, 0.15, 0.11) 35 % with the photo | chinese_cedar_bark (1.6 m tile) | object-space triplanar; extra vertical fibre noise (12/m x 0.6/m), bump 0.7, rough 0.9 |
| MAT_bark_eucalyptus | (0.40, 0.35, 0.29) | bark_bluegum (1.82 m) | smooth peeling blue-gum bark, bump 0.5, rough 0.75 |
| MAT_leaf_cypress | texture | foliage/needles_cypress.png | alpha-cut card (see below), translucency 0.25, rough 0.6 |
| MAT_leaf_eucalyptus | texture | foliage/leaves_eucalyptus.png | translucency 0.3, rough 0.42, specular 0.4 (waxy) |
| MAT_leaf_broadleaf | texture | foliage/leaves_broadleaf.png | translucency 0.35 |
| MAT_shrub | texture | foliage/leaves_shrub.png (v = up: solid below, feathered crown) | translucency 0.2, specular 0.4 |
| MAT_reeds | texture | foliage/reeds.png (v = up: blades from the bottom) | translucency 0.35, cluster variation +-35 % (green / straw) |
| MAT_backdrop_forest | (0.035, 0.07, 0.03)..(0.07, 0.11, 0.045) | procedural | 9 m Voronoi crown clumps with bump, 50 m haze variation |
| MAT_backdrop_hill | (0.26, 0.26, 0.17) / scrub (0.09, 0.12, 0.06) | procedural | dry grass hill |
| MAT_lamp_post | iron (0.035) rough 0.45 metallic 0.15; globe (0.75, 0.74, 0.68) above object z 3.55 | procedural | ENV's post+globe share one material |
| MAT_bird_white | (0.80, 0.80, 0.78), grey mantle above object z 0.05..0.12 | procedural | gulls; slight subsurface |
| MAT_test_greycard18 | 0.18 | - | test-only 18 % card next to the ochre wall |

### Foliage card materials
Generated textures (`scripts/mat_leaf_textures.py`, numpy rasteriser, 1024 px RGBA, sRGB-encoded colour + straight alpha):
needle sprays / leaf clusters drawn around 6 random sub-centres with an elliptical falloff so they read the same for any
in-plane orientation of Sapling's `rect`/`hex` cards; shrub and reed textures assume v = up (ENV's 0-1 quad cards).
Material: `UVMap` -> image; colour x per-tree hue/value (Object Info Random) x cluster noise; alpha remapped around
`alpha_cut` (soft rim at 3 m, solid at 120 m) -> Mix(Transparent, Mix(Principled, Translucent 0.25-0.35)); two-sided
(`use_backface_culling` off), `surface_render_method = DITHERED`, transparent shadows. Coverage (alpha > 0.5) of the cards:
cypress 0.28, pine 0.23, eucalyptus 0.31, broadleaf 0.39, shrub 0.53, reeds 0.33.

## Calibration (why the numbers are what they are)
- Neutral-light renders (`--neutral`, pixel value = albedo x cos): 18 % card reads 0.18-0.19; the plain ochre wall read
  (0.33, 0.21, 0.15), Y 0.23 with the sheet's (0.42, 0.29, 0.17) base (the weathering layers cost ~25 % and the grey drift
  added blue). Under the real rig the plain wall then read sRGB 176/126/84 vs the photo's sunlit attic (ref 169)
  201/152/80, i.e. the right hue (linear ratios 1:0.48:0.20 vs 1:0.54:0.14) but ~25 % dark, so the concrete family was
  warmed and lifted: ochre (0.47, 0.31, 0.135) Y 0.33 (attempt 2 was Y 0.59), grey-drift colour warmed to (0.32, 0.26, 0.175).
- In ref 169 the near-white dome renders as warm as the walls (200/141/80); the membrane base was therefore warmed to
  cream-peach (0.70, 0.645, 0.535). The remaining warmth is the illuminant (lighting agent).
- Rose column under the rig: terracotta in sun, dusty mauve in shade; neutral albedo read (0.32, 0.14, 0.095), ratios
  1:0.43:0.30 vs the sheet's overcast samples 1:0.37:0.25 .. 1:0.45:0.36.
- Block-tone steps were the biggest "wrong" read at hero distance (a mosaic of squares at +-22 %); now +-8 % on 3.6 m cells
  with the soft blotches and photo detail carrying most of the variation.

## Eevee vs Cycles
- AO node: works in both; Eevee's is weaker/softer (horizon scan), so recess dirt and the under-ledge shelter read at
  roughly half strength in Eevee. Bevel node: Cycles only (Eevee silently passes the normal through), so Eevee edge wear
  comes only from the inside-AO term (faint). Nothing breaks; Cycles is simply dirtier at the edges and in the hollows.
- Water: Cycles gives proper Fresnel reflections + murk (transmission tint + volume). Eevee Next does not reflect
  through its transmission path (A/B tested with and without raytraced refraction and with the lighting preset: no
  Fresnel reflection at all), so the material has a second Material Output targeted at EEVEE: an opaque dark-murk
  Principled surface with the same ripple normal and IOR; reflections then come from Eevee raytracing/probes and the
  hero water reads like the Cycles one. The Cycles volume only works inside a closed mesh (ENV's lagoon bed + surface
  should form a closed volume for the murk; on a single plane only the surface tint acts).
- Foliage alpha: hashed/dithered in Eevee (noisy at low samples, clean at 32), exact in Cycles.
- Driver `frame * 0.03` on `WATER_TIME` animates the ripples; if drivers are disabled the value stays 0 (static water).

## Test objects (`MAT_test`) and lineup cameras
Ochre wall 3 x 3 m with cornice + recessed panel (elevated to z 8-11 so it reads as an upper wall), podium wall at ground
with the open basin (podium walls, soil bed, water surface at WATER_Z) and rip-rap, colonnade wall + ledge + column,
fluted columns (24 flutes with fillets: rose, tan, colonnade), ornament block + 3 notched capital proxies (deep recesses,
per-instance variation) + a blob, the dome at true scale (33 m cap, 7.6 m rise), lawn/soil/gravel/paving patches, foliage
cards at 1 m + crossed clusters, bark cylinders, backdrop blocks, lamp post, bird, grey card. Cameras `CAM_mat_*`: wall,
column, waterline, ornament, colonnade, dome_close, dome_wide, ground, foliage, foliage_far, misc, lineup; plus the QA
hero cameras on the placeholder blockout (+ ENV with `--env`).

## Open issues / requests
- ARCH: columns must be real fluted geometry at LOD0/LOD1 (the flute dust/crest logic is geometry-driven; a plain LOD2
  cylinder just gets the drum joints and wash). Column origins at the shaft base (drum spacing and `Top Z` use object z).
  Dome origin on the dome axis (any z). Bevel modifiers 2-4 cm on arrises are what the edge wear reads.
- ENV: make the lagoon a closed volume (surface + bed + shore walls) so the water murk works; the water plane's origin
  does not matter (world coordinates). Reeds/shrub cards: v = up.
- ORN: LOD1 bakes plug into `MAT_ornament_concrete` per asset (see above); the lead's build_master should do the wiring.
- Lead: append materials in one call (node-group duplicates) — helper `mat_lib.append_materials(names)` /
  `mat_lib.dedupe_node_groups()`.
- Lighting: the sunlit-stone hue now matches ref 169 within a few percent in the green/blue ratios; remaining brightness
  and warmth differences are illuminant/exposure. Eevee water reflections depend on the preview preset (raytracing on).
- Not done (after round 2): rustication joints for the podium (expected as geometry from ARCH); a photographed
  efflorescence texture (still procedural); baked ORN normal/AO maps are wired but no asset has supplied them yet.

## Round 2 (Phase 3 fix round, 2026-09-07) -- what changed and why

All numbers are sRGB means from `scripts/mat_measure.py` on `--rig --env` Cycles heroes (960x540, 48 spp) at
`renders/previews/materials/`; comparison sheet `renders/qa_comparisons/materials_r2_water_stone.png`
(`scripts/mat_compare.py` builds it: labelled tiles, optional per-tile crop).

### QA-01-3 water (blocker)
The v1 water was a transmission-1.0 glass over a nearly black absorbing volume, with a full-amplitude 0.3 m ripple at
every distance. At 120-200 m one ripple is far smaller than a pixel, so its slope tipped every grazing reflection ray
off the sunlit building and into the dark shore: the lagoon read brown-black. Three changes:
1. **Distance filtering (Toksvig).** `Camera Data > View Z Depth` drives `ripple_lod` (1.0 at 30 m -> 0.13 at 180 m) on
   the bump strength, and adds up to +0.030 roughness over the same range. Near water keeps the full ripple (the
   0.3-1 m streaks QA asked for), far water becomes a slightly blurred mirror instead of noise.
2. **Anisotropy.** The 0.3 m ripple noise is stretched 3x along X (0.55x for the 3 m swell), so crests run across the
   hero view and the reflection breaks into *vertical* streaks as in ref 169.
3. **Lit green murk instead of black.** Transmission 1.0 -> **0.45** with a green murk base colour
   (0.042,0.084,0.055)..(0.078,0.140,0.086); the volume went from single-scatter albedo 0.07-0.15 to 0.25/0.63/0.29
   (Principled Volume: density 0.9, Color (0.13,0.26,0.16), Absorption Color (0.60,0.85,0.60), anisotropy 0.3 ->
   scatter (0.117,0.234,0.144)/m, absorption (0.36,0.135,0.36)/m). The material now reads the same on ENV's single
   water plane (the opaque 45 % carries the murk) and inside a closed lagoon volume (the transmissive 55 % carries it).
   The Eevee output branch got the same brighter murk and is unchanged otherwise.

| region (hero cam 01) | before | after | ref 169 |
|---|---|---|---|
| reflection under the rotunda | 90,64,40 | 108,80,48 | 129,95,57 |
| its own source (the shore band it mirrors) | 123,105,80 | 109,86,53 | - |
| reflection / source | 73 % | **99 %** | - |
| reflection / sunlit stone | 55 % | 59 % | 61 % |
| near water | 77,106,132 | 44,87,116 | 43,69,84 |
| far water (left of the rotunda) | 30,28,23 brown | 37,32,24 green-grey | - |

Reflection-vs-*building* is 59 % against the acceptance test's 70 %, but ref 169 itself is 61 %: the water in our hero
mirrors the shaded lower building and the shore band, not the sunlit attic, because the water band is only ~14 % of the
frame. Once the hero camera pulls back (lead/QA item) the attic lands in the water and the ratio follows the photo.
Aerial haze over 150 m of water (the other half of ref 169's bright far water) is a lighting/compositing mist pass.

### Sunlit stone luminance and warmth
Concrete base albedos were lifted ~20-25 % and the blue channel cut ~40 % across the family (ochre
(0.47,0.31,0.135) Y 0.33 -> **(0.640,0.398,0.070) Y 0.43**; colonnade, ornament, inner, podium, tan columns, paving,
plaster, backdrop and the rose column moved with it; grey-drift colours warmed to match). Ochre stays well under
attempt 2's Y 0.59.
Measured (hero cam 01, merged lighting rig): sunlit attic **183,148,111** vs ref 169 212,167,103 -- 14 % under in sRGB,
hue 30.4 deg vs 35.2 deg (**4.8 deg**, inside the 8 deg tolerance). Every further +10 % of albedo now buys only ~2 % of
display value: AgX's shoulder is compressing it, so the last of the luminance is exposure, not albedo. Diagnostic
`mat_lineup --ev <delta>`: at **+1.0 EV** the same shader reads 195,160,126 (Y 0.384 vs ref 0.4235 = 9 % under, hue
29.6 deg) -- i.e. one more stop closes the acceptance test on both axes. **Left to lighting:** that last stop, the
remaining R-B spread (ours 72, ref 109 -- the blue is skylight fill, not albedo), the grey horizon band and warm haze.

### QA-01-20 dome
`MAT_dome_membrane`: roughness 0.35 -> 0.42, Specular IOR Level 0.5 -> 0.44, coat weight x0.35 (was a flat 0.4) and
coat roughness 0.25 -> 0.30, so the broad sheen that blew out from above is gone; then, on lighting's master-scene
measurement (dome/attic 0.74 vs the photo's 1.36 and 9.5 deg cooler), the base albedo was raised and saturated:
(0.70,0.645,0.535) -> **(0.905,0.720,0.442)** (ratios 1:0.79:0.49 vs ref 169's dome 1:0.81:0.46), streak colour
(0.50,0.50,0.47) -> (0.62,0.555,0.42). In `CAM_mat_dome_wide` the dome top now reads 178,169,164 (Y 0.403) against the
lawn's 111,111,82 (Y 0.153), ratio 2.63. The dome/attic ratio in `master.blend` must be re-measured by lighting/QA:
my lineup has no attic next to the dome, and the hero placeholder dome is not ARCH's geometry.

### Foliage
`scripts/mat_leaf_textures.py` now accumulates a **HEIGHT** and a **RIB** buffer while it draws (a half-cylinder profile
for needles/twigs, a cross-blade bulge plus a midrib ridge for leaves) and writes two more maps per texture:
`<name>_nrm.png` (tangent-space OpenGL normal, Non-Color, from the smoothed height gradient) and `<name>_trn.png`
(translucency: thin margins and tips transmit, midribs/stems/needle spines do not). `leaf_material()` plugs the normal
into both the Principled and the Translucent BSDF and multiplies the translucency mix by the mask
(0.35..1.55 x the material's base value). New materials: **MAT_leaf_pine** (needles_pine, darker and bluer than cypress,
tint (0.80,0.92,0.78), translucency 0.18 -- ENV maps pines and redwoods here), **MAT_shrub_light** (pale grey-green
pittosporum/agapanthus) and **MAT_shrub_dry** (straw, tint (4.50,1.15,0.70): reads 102,95,61 at 3 m against ref 169's
dry shore 144,108,55).

### Efflorescence / salt bloom
`PFA_concrete` gained an **Efflorescence** input (0-3, default 1.0) scaling the `PFA_algae` Effl mask; the wash is
chalkier (0.68 x a 0.85-mix toward (0.66,0.635,0.575), was 0.55 x 0.6) and now adds a crusty bump (0.30 x a 22/m noise).
`MAT_concrete_podium` runs it at 1.15, so the 0.6-1.2 m zone above WATER_Z carries a salt bloom over the algae band.

### Per-instance ornament variation (verified, and it was broken)
`PFA_instance` now hashes **three** sources into the per-instance random: Object Info Random, the `instance_seed`
object custom property (`ShaderNodeAttribute`, `attribute_type='OBJECT'`; absent -> 0 -> no shift, so nothing breaks)
and the object's **origin** from Object Info Location -- Random is identical for linked duplicates and 0 in some
evaluated contexts, which is why v1's ornament looked uniform. `MAT_ornament_concrete` runs Instance Variation 1.7
(hue +-5 %, value +-14 %). Test: six capital proxies with `instance_seed` 0.37..8.47 at 60 m
(`CAM_mat_ornament_far`, 200 mm) read 187,140,81 / 185,133,77 / 180,136,74 / 183,126,71 / 178,135,71 / 182,121,71 --
Y 0.241..0.298, a 20 % spread, clearly different by eye (sheet tile 4).
Debug hooks added to `mat_lineup`: `--debug R1|R2|R3|R4` emits `PFA_instance`'s output as emission, `--debug RND|LOC|ISEED`
emits Object Info Random / Location / the `instance_seed` attribute. That is how the dead variation was found.

### ENV-requested materials (new, all `use_fake_user`)
**MAT_leaf_pine**, **MAT_shrub_light**, **MAT_shrub_dry**, **MAT_backdrop_roof** (grey built-up membrane, tar seams,
pooled grime, rough 0.82), **MAT_backdrop_skylight** (dirty wired glass: dark base, roughness 0.14+0.30 x dirt, coat 0.25),
**MAT_backdrop_door_green** (park-service green on boards, chalked, damp lower edge, dull bronze push-plate zone at
object z 1.00-1.25 -- the door on the rotunda axis seen through the central arch). Test objects for all of them are in
`MAT_test` (`CAM_mat_misc` was widened and moved to x -16.5 to frame the backdrop details; the two shrub variants sit in
a second foliage row at y 10.5 / y 32.5). Library is now **35 materials**.

### Other round-2 tooling
- `scripts/mat_compare.py` -- labelled comparison sheets from renders/photos with optional crops (plain PIL).
- `mat_lineup --ev <delta>` -- exposure-offset diagnostic (used to quantify what lighting owed).
- `CAM_mat_ornament_far` -- the 60 m per-instance variation camera.

## Round 3 (Phase 4 polish round 1, 2026-09-07) -- QA-02-2 / -3 / -6 / -14

Everything below was judged at the exposure the build will ship at (`scene.view_settings.exposure` -3.2911 **+0.9 EV**
= -2.3911, lighting's QA-02-4 change), so none of it silently compensates for the exposure. Two new tools:
`scripts/mat_scene_check.py` renders a waterline / stone / hero set out of the *assembled* master with that exposure
applied (`--ev`, default +0.9), because the lineup in `materials.blend` has neither ARCH's geometry nor ENV's water and
was giving the wrong answer about both the algae band and the sunlit-stone colour.

### QA-02-2 blotchy "decal" stone, olive cast, per-instance hue (blocker)
Three separate causes, all confirmed by reading the shader rather than by eye:

1. **Hard-edged pale blotches.** Two node stages produced literal hard borders. The cast-block tone step is an
   axis-aligned Chebychev Voronoi (`Block Size` 2.4-4.0 m = 34-56 px on the hero) and the repair patches used a
   `maprange(cell, thr, thr+0.004)` -- a 0.4 %-wide ramp, i.e. a stencil. Fixes: both cell fields are now noise-warped
   before the Voronoi so their borders are broken and plaster-like; the block step amplitude is cut to 0.35 x
   `Tone Variation`; the patch ramp is 0.05 wide and the patch tone step is +6 % value / -8 % sat (was +14 % / -20 %).
   A new `Drift Size` input (8-22 m, +- full `Tone Variation`) carries the large soft tonal drift that is what actually
   reads across 100 m of wall, and the mid-scale mottle went from +-0.6 x TV to +-1.0 x TV.
2. **Olive cast on shaded piers and arch soffits.** The rain-streak tint was `(0.36, 0.37, 0.31)` -- **G > R**, a green
   multiplier, riding a broad low-contrast mask, so it read as a green wash over every sheltered surface instead of as
   drips. It is now `(0.46, 0.405, 0.325)` (R > G > B, warm dark grey) on a narrow high-contrast mask. Measured on the
   hero's shaded pier: hue **28.0 -> 33.6 deg** (acceptance 34-42; the albedo-blue cut below carries it the rest of the
   way). The recess-dirt tint was warmed the same way, (0.5, 0.47, 0.42) -> (0.56, 0.495, 0.405).
3. **Per-instance hue instead of weathering.** `PFA_concrete` spread instances by +-0.06 in HSV hue x
   `Instance Variation` 1.7 = **+-18 deg**, which is why a yellow capital (hue ~55) stood next to a salmon one (~20).
   Hue variation is now +-0.0055 x IV (+-1.7 deg, pigment-lot scale), value went +-0.16 -> +-0.22 x IV, and a new
   per-instance `wvar` (0.05..1.9 at IV 1.7) scales that instance's streak, ledge and recess-dirt masks, so instances
   differ by how weathered they are. Measured on `CAM_mat_ornament_far` (four capitals, 60 m, 200 mm, +0.9 EV):
   hue **32.4 / 32.6 / 33.0 / 33.6 deg = 1.2 deg spread** (was ~35 deg; acceptance <= 4), luminance 124.8 / 128.5 /
   133.0 / 148.4 = a 19 % value spread.

### QA-02-3 no edge wear, no rain streaks, no algae band (blocker)
- **Edge wear could not read at any strength.** `Edge Radius` was 0.02-0.03 m; the hero is ~7 cm/px, so a 3 cm arris is
  sub-pixel. It is now 0.10-0.12 m on wall-scale materials (0.05 m on ornament, whose features are 0.4 m, 0.03 m on the
  drum band), with `Edge Wear` 0.45 -> 0.6. The `PFA_edge` group is unchanged (Bevel-normal difference in Cycles,
  inside-AO in both engines).
- **Streaks were a wash, not drips.** `Streak Scale` 1.5-3.0 / `Streak Length` 3-10 gave features 0.3-0.7 m wide and
  ~2 m long -- a 3:1 aspect, which averages to a flat tint. Now 6-14 / 4-10 = 0.07-0.17 m wide by 1-1.4 m long
  (8-15:1), with tighter smoothstep ramps in `PFA_streaks`. `Ledge Weight` went the *other* way, 0.75-0.85 -> 0.45-0.55:
  the ledge mask is an AO probe only ~3 m deep, so a high weight left the open wall faces bare instead of streaked.
  A new **ledge run-off band** (`Ledge` x 0.40 x `Streaks` x `wvar`, tint x (0.74, 0.695, 0.615)) puts continuous
  soiling directly under every overhang, under the drips.
- **The algae band was switched off nearly everywhere.** `Algae` defaulted to 0.0 and only `MAT_concrete_podium` set
  it. The band mask is height-gated, so it costs nothing on high geometry: the default is now 1.0 and every material
  that can reach the water carries it (ochre, podium, colonnade, inner, paving; off on ornament, columns, ceiling,
  drum band, backdrop). `MAT_rock_riprap`'s band went 0.35 m at WATER_Z+0.05 -> 0.55 m at WATER_Z+0.10.
- **The podium does not actually touch the water in this site.** Its base sits at z ~ -0.9 behind a soil/rip-rap shore
  while WATER_Z is -1.3, so a 0.55 m band at the water line was entirely underground. The podium/colonnade/ochre band
  heights are 1.0-1.1 m, which puts ~0.6 m of dark damp stone on the *visible* podium base -- what the acceptance is
  measuring. **For ARCH/ENV:** in ref 169 the podium stonework runs straight into the lagoon; here a shore band is
  interposed, which is a terrain/footprint difference, not a shader one.

### QA-02-6 lagoon flanks 3.9x dark, near field over-saturated cyan (shared with environment)
Same single cause: 45 % of the water surface was transmitting into a dense absorbing volume, so the lagoon body was a
light sink and the only bright thing left was the specular sky mirror -- a black body with a blue mirror on it.
`Transmission Weight` 0.45 -> 0.28, murk brightened and moved toward neutral green-grey ((0.042, 0.084, 0.055) /
(0.078, 0.140, 0.086) -> (0.088, 0.122, 0.086) / (0.140, 0.178, 0.130), Eevee's opaque murk to match), volume density
0.9 -> 0.7. **ENV still owns the mesh and the bed depth**; if the flanks are still short after this, the next lever is
the bed, not the shader.

### QA-02-14 sunlit stone 5-9 deg cool and under-saturated
The blue channel, not the red or green, is the whole error: at +0.9 EV the sunlit attic read **216, 182, 140**
(hue 32.9, sat 0.352) against ref 169's **220, 176, 93** (hue 39.1, sat 0.577) -- R and G already match to within 3 %.
Albedo blue was cut ~40-45 % across the concrete family (ochre/colonnade/ornament 0.068 -> 0.038, podium 0.115 ->
0.082, inner and tan columns 0.082 -> 0.052, rose 0.086 -> 0.048, paving/plaster/backdrop/drum in proportion), and the
`Grey Color` of each material with it so the damp drift does not put the blue back. `MAT_dome_membrane` went
(0.905, 0.720, 0.442) -> (0.905, 0.720, 0.378) (measured hue 32.6 vs ref 37.4). **Left to lighting:** a real part of
the residual blue is skylight fill rather than albedo -- the render's R-B spread is far narrower than ref 169's -- and
albedo cannot be pushed further without becoming an orange pigment rather than concrete.

### The saturation result, and why it is now lighting's (measured, QA-02-14)
Cutting the concrete albedo blue by **44 %** (0.068 -> 0.038) moved the hero attic's *display* blue by **3 %**
(140 -> 136) and its saturation from 0.352 to 0.372. That is the whole experiment: at the shipping +0.9 EV the sunlit
stone sits on the **AgX shoulder**, where albedo has almost no authority over display chroma. Pushing albedo further
would make the concrete an orange pigment and still not reach ref 169's sat 0.577.

What is left is illuminant and view transform, not albedo:
- ref 169's R-B spread on sunlit stone is **127** (220,176,93); ours is **81** (216,181,136). A photograph of low sun
  through coastal haze is a much redder illuminant than our sun + sky mix.
- The measured AgX response is -1.1 deg of hue and falling saturation per +1 EV, so the exposure lift QA asked for
  costs chroma; our attic lands at lum 185.6 against ref's 179.4, i.e. ~4 % hot, which costs a little more.

**Requests to lighting:** (a) warm `LIGHT_sun` (temperature) rather than expecting albedo to carry it; (b) the sky
saturation node currently puts a lot of blue fill on every surface -- the shaded pier reads sat 0.315 where the photo's
shade is far warmer; (c) if the hero still reads pale after that, half a stop less exposure buys chroma back.
The one lever materials still had was the specular veil (a 0.4 Specular IOR Level on rough concrete reflects the blue
sky straight back); it is now 0.25 across the concrete family, 0.30 paving, 0.20 plaster.

### Coordinator additions folded into round 3
- **Near-water chroma (with ENV).** The murk was still doing half the colouring, so murk and sky reflection compounded.
  Murk moved toward neutral grey-green: near (0.088, 0.122, 0.086) -> (0.104, 0.118, 0.100), far (0.140, 0.178, 0.130)
  -> (0.152, 0.168, 0.142), volume Color (0.16, 0.28, 0.18) -> (0.205, 0.250, 0.195), Absorption (0.60, 0.85, 0.60) ->
  (0.70, 0.80, 0.68); the Eevee opaque murk follows. The Fresnel sky reflection now supplies the blue on its own.
  **Note a conflict in the reference numbers:** QA round 2 measured ref 169's near water at sat **0.426**, ENV reports
  **0.11** for the same region. Our r3t near-field box already reads 0.341, i.e. below QA's figure. The step above is
  deliberately moderate; if 0.11 is the right target the murk should go essentially neutral, but that should be settled
  against one agreed crop before pushing further.
- **QA-01-8 hall wall through the hero arch.** `MAT_backdrop_building` had `Detail Strength` 0.3 with a 22 m drift --
  nothing at all at the 60-90 m the hall actually sits at, hence "flat untextured cream". Now Detail Strength 0.7,
  Tone Variation 0.16 -> 0.24, Drift Size 22 -> 11 m, Blotch Size 6 -> 3.2 m, Bump 0.25 -> 0.5 (stucco), Streaks
  0.5 -> 0.8 with `Ledge Distance` 3.5 m and `Recess Distance` 0.9 m so the cornice throws a real soiling band, and
  Patches 0.1 -> 0.18. `MAT_backdrop_skylight`'s base was lifted off black ((0.055, 0.062, 0.070) ->
  (0.072, 0.080, 0.092)) so a dark opening reads as dirty glazing catching sky rather than a hole in the image.
  **The hard black opening itself is geometry:** if that aperture is an unfilled hole rather than a face carrying
  `MAT_backdrop_skylight`, no shader change will close it -- it needs a face from whoever owns the hall massing.

### Round 3 result: hero regions vs ref 169 (aligned, identical boxes, both at the shipping +0.9 EV)
`renders/previews/materials/r3v_scene_hero.png` against the aligned ref 169 panel of
`renders/qa_comparisons/round02_cam01_aligned_vs_ref169.png`. Composite:
`renders/qa_comparisons/mat_r3_stone_water.png`.

| region | round 2 | round 3 | ref 169 | verdict |
|---|---|---|---|---|
| sunlit attic | 194,144,94 hue 29.7 sat 0.519 | 216,180,134 hue **33.8** sat 0.383 | 220,171,87 hue 37.8 sat 0.603 | hue 4.0 deg (was 8.1); saturation still short |
| dome cap | hue 33.3 | hue **33.5** | hue 33.9 | 0.4 deg **pass** |
| column shaft | hue 23.4 | hue **29.2** | hue 25.0 | now 4.2 deg *warm* |
| shaded pier | hue 28.0 sat 0.414 | hue **34.6** sat 0.313 | hue 32.9 sat 0.491 | inside QA-02-2's 34-42 band |
| lagoon mid-left | lum 55.1 | lum **140.2** | lum 134.6 | **+4 % of the photo** (was 3.9x dark) -- QA-02-6 luminance **pass** |
| lagoon mid-left sat | 0.601 | 0.367 | 0.118 | still 3x: this water is a mirror, so its colour *is* the horizon sky's |
| near water | lum 55.5 sat 0.534 | lum 93.7 sat **0.298** | lum 76.9 sat 0.611 | now slightly *under*-saturated; ENV's 0.11 target was the flank, not the near field |
| capitals at 60 m (4 instances) | hue spread ~35 deg | **1.2 deg**, value spread 19 % | - | QA-02-2 per-instance **pass** |

Round 2's saturation numbers are 0.9 EV darker and so are not comparable on that axis; the hue and lagoon numbers are.
**Remaining, and not materials':** the flank water's chroma is the reflected horizon sky (lighting's haze/aerosol), and
the sunlit-stone saturation gap is illuminant warmth plus the AgX shoulder (see the section above).

## Round 4 (Phase 4 polish round 2, 2026-09-07/08) -- QA-03-2 / -03-4 / -03-7 / -03-9 / -03-15 + QA-02-3

Everything below is measured on the **1920x1080 Cycles hero out of the assembled master**, on lighting's round-09
rig (`assets/lighting.blend` commit 8ac655c), `AgX - High Contrast`, `view_settings.exposure -2.3331`, `--ev 0.0`.
Two things had to be sorted out before any number meant anything:

- **The worktree's `master.blend` was stale.** `build_master.py` *appends* the library rather than linking it, so a
  rebuilt `assets/materials.blend` does not reach an existing master, and the master also still carried lighting's
  round-08 rig (`LIGHT_sun["exposure_ev"] = -3.2911`, i.e. 0.96 EV under the shipping value). Every measurement round
  here is therefore `mat_build.py` -> `build_master.py` -> `mat_scene_check.py`. Round 3's `--ev 0.9` compensation is
  **obsolete**: with lighting r09 merged, use `--ev 0.0`.
- **New tool `scripts/mat_r4_measure.py`** (plain python + PIL, no Blender). It reads the QA round-03 hero boxes and
  prints mean sRGB / luminance / hue / saturation / R-B, plus the column mask, the entablature luminance std-dev and
  a near-water ripple run-length. `--panel 1` runs the identical boxes against panel 1 of
  `renders/qa_comparisons/round03_cam01_aligned_vs_ref169.png` (QA's warped photo), and it reproduces QA's published
  reference numbers to within 0.5 -- so render and photo are read with one yardstick.
  `scripts/mat_r4_sheet.py` builds the deliverable composite `renders/qa_comparisons/mat_r4_sheet.png`.

### QA-03-2 sunlit stone chroma -- what albedo can and cannot do (measured twice)

Baseline on the r09 rig was **236,188,130** against ref 169's **231,187,95**: R and G already matched to 2 %, the
whole error was **blue, +35**. Cutting the concrete albedo blue 0.038 -> 0.024 (**-37 %**) moved display blue by
**+2**. That is not a tuning failure, it is AgX's inset matrix: the blue output channel is
`0.048 R + 0.101 G + 0.811 B` *before* the log curve, and on sunlit ochre stone (linear ~0.68 / 0.38 / 0.026) about
**77 % of the blue channel is leakage from R and G**. Zeroing albedo blue entirely could move it -0.38 EV, ~14 display
levels; the gap is 35. Round 3 measured the same thing from the other end (-44 % blue -> -3 % display blue).

So the hue was carried by **green** instead, which does have authority (albedo G is 0.38 linear, no leakage problem):
`MAT_concrete_ochre` Base Color went `(0.645, 0.436, 0.038)` -> `(0.655, 0.545, 0.018)`, and the ochre / colonnade /
ornament / podium / paving / drum / backdrop family with it (each `Grey Color` moved in step so the damp drift does
not put the old hue back).

| hero box | round 3 library | round 4 library | ref 169 | QA-03-2 acceptance |
|---|---|---|---|---|
| attic sunlit 900 222 1020 256 | hue 32.8 sat 0.452 R-B 107 lum 194.1 | hue **37.7** sat 0.440 R-B 102 lum 197.6 | hue 40.3 sat 0.588 R-B 136 lum 189.6 | hue >= 37 **pass**; sat >= 0.53 **fail**; R-B >= 118 **fail**; lum +-10 % **pass** (1.04) |
| attic string course | hue 33.7 | hue **38.6** | hue 39.3 | - |
| entablature | hue 33.1 | hue **38.0** | hue 34.0 | now slightly warm |
| dome cap | hue 29.8 lum 205.8 sat 0.283 | hue **36.6** lum 210.0 sat 0.288 | hue 42.7 lum 215.6 sat 0.288 | +6.8 deg, saturation and luminance both land |
| columns (mask) | lum 186.4 hue 29.6 | lum **155.1** hue 30.1 | lum 95.8 hue 24.5 | still 1.62x -- see below |

`MAT_dome_membrane`: the cap needed **green**, not less blue (render B 168 vs ref 167 already). Base Color
`(0.905, 0.720, 0.378)` -> `(0.905, 0.960, 0.320)`, `Specular IOR Level` 0.44 -> 0.26 and coat weight x0.35 -> x0.18,
because a 0.44 specular on an up-facing dome is a blue sky mirror.

**Saturation and R-B are not materials'.** Two independent albedo experiments (round 3: -44 % blue; round 4: -37 %
blue with +25 % green) moved the sunlit attic's saturation by less than 0.02 in either direction. At lum ~195 the
stone sits where AgX compresses R hardest, so `(R-B)/R` cannot be opened from the albedo side. What is left is the
illuminant: ref 169's sunlit stone has an R-B spread of 136 where ours has 102, and our **shaded** stone is the
mirror image of the problem -- see the next paragraph.

**The one real regression, and it is a hand-off.** Albedo has one hue and cannot know which light hits it. Warming it
for the sunlit faces also warms the shaded ones, and the shaded ones were already too warm:

| | render | ref 169 |
|---|---|---|
| sunlit attic hue | 37.7 | 40.3 |
| shaded north attic hue (1110 225 1150 260) | **42.5** | **29.5** |
| shaded saturation | 0.618 | 0.425 |

The photo drops **11 deg from sun to shade**; we rise 5. That is the sky's share of the fill being too small and too
warm, and it is the same quantity that sets the missing sunlit R-B. **For lighting:** more (and bluer) sky fill on
shaded stone would fix the shade hue *and* widen the sunlit R-B spread at once; albedo cannot do either.
Materials did put back what it could: the concrete `Specular IOR Level` went 0.25 -> **0.30** (it only ever reflects
sky, so it lands almost entirely on the shade) after a trial at 0.18 made the olive worse.

**Interior split (found from the cam04 crop, not from a number).** With the family green raised, the vault soffits and
the coffered saucer -- lit only by warm bounce, with no sun to oppose the shift -- went visibly **olive**. The family
is therefore split: sun-facing materials (`MAT_concrete_ochre` / `_colonnade` / `_podium` / `MAT_ornament_concrete`)
keep the round-4 green; the shade-only ones went most of the way back (`MAT_concrete_inner` `(0.475, 0.358, 0.034)`,
`MAT_plaster_ceiling` `(0.572, 0.470, 0.130)`, `MAT_column_tan_inner` `(0.565, 0.428, 0.032)`).

### QA-03-4 / QA-02-3 "clean CAD" at 1:1 -- wear that reads at hero distance

Sizes first, because that is what was wrong: the hero is ~5 cm/px, and round 3's rain streaks were 0.07-0.17 m wide,
i.e. **1.4-3.4 px**, which averages to a flat tint no matter how dark the tint is.

- `Streak Scale` 7.0 -> **3.2** on the ochre (6.0 -> 3.0 podium, 7.5 -> 3.4 colonnade, 12 -> 6 ornament): drips are
  now ~0.31 m wide by ~2.2 m long, 6 px by 44 px on the hero.
- `PFA_streaks` ramps widened (`m1` 0.54-0.60 -> 0.47-0.58, `m2` 0.58-0.64 -> 0.51-0.62) and the along-length fade
  floor 0.2 -> 0.35, so drips cover a useful fraction of a wall instead of ~15 % of it.
- The **ledge run-off band** under every overhang went `Streaks x 0.40` -> `x 0.62` and its tint
  (0.74, 0.695, 0.615) -> (0.655, 0.605, 0.515). This is the "dark streak under the cornice" the acceptance asks for.
- `Edge Radius` 0.12 -> **0.20 m** and `Edge Wear` 0.60 -> 0.70 on wall-scale concrete (a 0.12 m arris is 2 px).
- `Recess Distance` 0.4 -> **0.7 m** with `Recess Dirt` 0.60 -> 0.72, and `Tone Variation` 0.15 -> **0.30** with
  `Blotch Size` 1.8 -> 0.9 m (17 px features rather than 34 px ones), `Detail Strength` 0.85 -> 1.0.
- **New `Cavity` input on `PFA_concrete`** (default 0.0, so nothing not listed changes): a second AO probe at
  `Recess Distance x 0.34`, squared, darkening value only (`x (1 - 0.55 cav)`) -- pure shading depth, no hue shift,
  where `Recess Dirt` is a tint on a much longer probe. Ochre 0.70, colonnade 0.65, inner/plaster 0.70/0.50,
  ornament 1.0, columns 0.90-0.95.

Measured: entablature luminance std-dev **30.8 -> 32.8** against the photo's 63.8 (the acceptance is >= 38.3). The
crop pair in `mat_r4_sheet.png` shows the difference the number understates -- the round-3 panel is one flat ochre,
the round-4 panel has mottle, drips and a soiling band under the cornice. **The rest of that std-dev is geometry, not
shading:** in ref 169 the same box contains dentils, modillions and a deep cornice undercut throwing near-black
shadow; ours contains a much shallower cornice, and no albedo texture makes a 5 cm shadow that is not modelled.
**For architecture:** cornice projection / dentil depth on the attic entablature is the remaining half of QA-03-4.

### QA-03-9 / QA-03-15 columns and capitals

- `MAT_column_rose` Base Color `(0.505, 0.258, 0.048)` -> `(0.316, 0.158, 0.021)` (**-37 % albedo**, and G/R 0.51 ->
  0.50 so it is less yellow), `Tone Variation` 0.14 -> 0.24, `Drift Size` 6 -> 4.5 m, `Detail Strength` 0.45 -> 0.70,
  `Streaks` 0.25 -> 0.45, `Drum Variation` 0.07 -> 0.11, `Wash` 0.45 -> 0.55. Hero column mask **186.4 -> 155.1**
  against ref 169's 95.8: still **1.62x**, and the remaining factor is fill, not albedo -- in the photo the shafts sit
  in the entablature's shadow at 0.50 of the sunlit attic, in the render at 0.78. Another 40 % off the albedo would
  make them brown mud in the sun-struck lower half. **For lighting: this is the other half of QA-03-2.**
- **Flute relief (architecture's hand-off).** With 24 flutes at ~2.2 px on the hero, geometry alone gives 37 %
  modulation against the photo's 68-79 %. Phase-locking is done *without* knowing ARCH's flute phase: the `Cavity` AO
  probe is sized to half a flute pitch (`Recess Distance` 0.40 -> 0.30 m, so the probe is ~0.10 m on a 0.26 m pitch)
  so it darkens the hollows, and the edge mask is narrowed to ~1 px (`Edge Radius` 0.07 -> 0.045, `Edge Wear`
  0.5 -> 0.85) so it lights only the arrises. A radial-angle modulation would have to guess the phase and would beat
  against the mesh. Same treatment on `MAT_column_tan_inner`.
- **Capitals:** `MAT_ornament_concrete` `Cavity` 1.0, `Recess Dirt` 0.8 -> 0.85 at `Recess Distance` 0.3 -> 0.42,
  `Edge Wear` 0.65 -> **0.85**. Dark hollows plus lit arrises is what makes leaf tiers separate at 100 m.
- **Coffer ribs (architecture's second hand-off).** New `Rib Grime` input on `PFA_concrete` (default 0.0), keyed on
  `|Nz|` (`maprange(|Nz|, 0.60, 0.16, 0, 1)`): rib flanks are near-vertical where the coffer panels face down, so it
  picks the ribs and nothing else. `MAT_plaster_ceiling` runs it at 0.85. In the cam04 crop the ribs now read as dark
  lines; they are thin because the modelled rib relief is shallow, so how far this goes is geometry's call.

### QA-03-7 near water -- what moved and what did not

Four configurations were rendered and measured at the same boxes:

| | flank lum (ref 155.2) | flank sat (ref 0.279) | near sat (ref 0.270) | ripple runs (ref 15.3) |
|---|---|---|---|---|
| round 3 (glassy) | 158.2 | 0.387 | 0.463 | 19.3 |
| + near roughness | 135.9 | 0.489 | 0.501 | 29.2 |
| + strong near chop | 105.3 | 0.651 | 0.580 | 13.1 |
| **shipped** (moderate chop) | **143.9** (0.93) | 0.450 | 0.486 | 27.8 |

Three separate levers were tried and **measured to do nothing** to the near-water chroma: brightening the murk 1.8x
(near saturation 0.475 -> 0.473), a warm `Specular Tint` on the Principled (0.475 -> 0.473 -- Blender tints only the
*facing* reflectance and this crop is grazing, where Fresnel goes white whatever the tint), and dropping
`Transmission Weight` / `Specular IOR Level`. All were reverted. At these angles the lagoon **is** a Fresnel mirror
and its colour is the reflected horizon sky, which QA itself measured 0.74 of the photo's brightness with no haze
band. **For lighting: the near-water hue (204.8 vs 192.1) and saturation (0.486 vs 0.270) are the horizon sky's, not
this shader's** -- the same conclusion round 3 reached for the flank, now with the murk experiment to back it.

What the shader does own is break-up, and there is a real cost curve: any near-field ripple amplitude tips grazing
rays off the bright sky and onto a dark far shore, so it buys texture with flank luminance. The shipped setting
(`near = maprange(depth, 70, 10, 0, 1)`, capillary gain +0.28, a 0.04 m chop layer at +0.18, bump +0.14) puts the
flank at 0.93 of the photo -- comfortably inside QA-02-6's 25 % test -- and the 1:1 crop now shows a broken
reflection where round 3 showed glass. **The run-length metric disagrees (19.3 -> 27.8 px) and the metric is the
thing that is wrong here:** it counts sign changes about a row median, so render noise shortens runs and a smoother
low-noise render lengthens them; judge this one from the crop pair in the sheet. The crest anisotropy stays
X-elongated (0.36): at 0.62 the normals sweep sideways into open sky and the flank saturation went 0.387 -> 0.484.

### Files

`renders/previews/materials/r4b_scene_hero.png` (before, round-3 library on the r09 rig),
`r4m_scene_hero.png` + `r4m_scene_ceiling.png` (after), composite
`renders/qa_comparisons/mat_r4_sheet.png`. `mat_scene_check.py` gained a `ceiling` job (`CAM_qa_04_rotunda_ceiling`).

### Open, and whose

1. **Lighting** -- sunlit stone saturation 0.440 vs 0.588 and R-B 102 vs 136; shaded stone hue 42.5 vs 29.5 (the
   photo drops 11 deg sun-to-shade, we rise 5). One cause: not enough blue sky fill in shade / not enough spread
   between sun and sky. Albedo is exhausted, twice measured.
2. **Lighting** -- hero column shafts 1.62x the photo after a 37 % albedo cut: fill on surfaces that should be in the
   entablature's shadow.
3. **Lighting** -- near-water hue/saturation is the reflected horizon sky (no haze band, QA measured 0.74).
4. **Architecture** -- the other half of QA-03-4: the entablature std-dev gap is cornice/dentil depth, not shading.

## Round 5 (Phase 4 polish round 3, 2026-09-08) -- ornament cavity/AO, far-field library gaps, coffer ribs

Method as in round 4, with one change that saved two master builds: `mat_scene_check.py` gained **`--swap`**, which
re-appends `assets/materials.blend` over the copies `build_master` baked into an existing `master.blend` and then
redoes the ornament per-asset material pass exactly as `build_master.orn_material_for()` does. The before/after pairs
below therefore differ **by the library and by nothing else** -- same geometry, same lighting r09 rig, same baked
light probes, same exposure -2.3331 -- instead of by two whole master builds. It also gained a `capital` camera, a
`cam06` job, `--engine eevee --lod 1`, and `--debug-attr` (see below). New tools: `scripts/mat_r5_measure.py`
(PIL only) and `scripts/mat_r5_sheet.py` -> `renders/qa_comparisons/mat_r5_sheet.png`.

The **capital camera** stands at the hero station with a 400 mm lens at 768 px. That is exactly **8x** the hero's
angular resolution (the hero is 20 mm at 1920 px), so downsampling the render by 8 reproduces the hero pixel for
pixel; the sheet shows both. The nearest rotunda capital is 82 m away, ~39 px wide in the hero.

### 1. ORN's `cavity` attribute and the baked AO / normal maps -- both live now

**The maps.** `concrete_material(baked=True)` built nodes called `BAKED_NORMAL` / `BAKED_AO`; `build_master` looks for
`ORN_NORMAL` / `ORN_AO`, so it always returned `None`. Renamed. The harder half was the default: **an Image Texture
node with no image is not neutral.** Measured in both engines: it returns **Alpha 1.0** (so the alpha is not a
"is a map plugged in?" flag) and Color **(1,0,1) in Cycles / (0,0,0) in Eevee** -- a pink normal, and in Eevee full AO
occlusion over the whole asset. The old `BAKED_WEIGHT` value node defaulted to 0.0 to dodge this and nothing ever
raised it. Both nodes now ship a 4x4 generated neutral image (`mat_lib.neutral_image`: flat tangent normal, white AO),
so the library material behaves exactly as if the hooks were absent and `build_master` only has to swap the image
datablock. Verified on the assembled master: **27 per-asset materials on 307 LOD1 instances**, and the cam04 Eevee
before/after differs by up to **109 levels in the four corner cells** -- that is the LOD1 ornament picking up its
bakes. (LOD0 is the render LOD and has no UVs, so the maps are a LOD1/viewport feature by construction; LOD0 is what
the vertex attribute is for.)

**The attribute.** New `Vertex Cavity` / `Vertex Dust` inputs on `PFA_concrete` (both default 0.0, so nothing outside
`MAT_ornament_concrete` changes), read through a Geometry Attribute node named `cavity`.

*A shader cannot tell "attribute missing" from "attribute = 0".* Measured in Cycles and Eevee: a missing geometry
attribute reads Fac 0, Color 0 and **Alpha 1.0**. 92 of the 106 ORN meshes (maidens, urns, attic panels and figures,
mouldings) carry no `cavity` and share this material, so the naive `1 - cavity` would paint every one of them black.
The presence ramp `vpres = maprange(cavity, 0.0, 0.05, 0, 1)` is therefore **exactly 0 at cavity = 0**: the term
vanishes on meshes without the attribute, and on meshes with it the only cost is the deepest ~0.5 % of the visible
surface, whose neighbours still get the full effect.

*The ramp has to be keyed on the screen-space distribution, not the vertex one.* The first attempt used ORN's
published vertex statistics (capitals p25 0.30 / p50 0.60) and moved the rendered capital by **0.7 %** -- invisible.
`mat_scene_check.py --debug-attr` renders every ornament instance as a raw emission of `cavity`; on the hero capital
the **visible** surface measures **p02 0.61 / p10 0.75 / p25 0.93 / p50 1.00, mean 0.94**. ORN's probe is 10 rays over
6 % of the object diagonal (~66 mm on a capital), so it only finds enclosure deep inside crevices the camera never
sees, and the vertex p25 of 0.30 is almost entirely hidden geometry. Ramp changed to `1.00 -> 0.60`.

| capital bell box (320x275 at 8x hero res) | round-4 library | round-5 | direction |
|---|---|---|---|
| luminance mean | 152.4 | **138.2** | -9.3 % |
| p10 (the recesses) | 45.4 | **36.6** | -19 % |
| p50 | 180.7 | **161.3** | |
| p10/p90 | 0.209 | **0.173** | recesses further below the crests |
| readable leaf tiers (dips >= 4 levels in the row profile) | 8 | **10** | QA-03-15 asks for >= 2 |
| control: plain wall behind | 188.6 | 188.5 | unchanged, as intended |

`MAT_ornament_concrete`: `Vertex Cavity` 0.85, `Vertex Dust` 0.55. The dust rides the existing recess-dirt tint
(0.56, 0.495, 0.405) so the hollows go warm-grey, not just dark; the value darkening is clamped so the deepest point
stops at 78 %.

**For ORN (two requests).** (a) The cavity probe radius is too small to reach the screen: at 6 % of the diagonal the
visible surface is 94 % "open". A second bake at ~15-20 % of the diagonal (leaf-tier scale, not crevice scale) would
give the shader a signal at the scale that actually reads at 80-100 m; we would then drop the remapping. (b) Please
extend `finalize_asset(..., cavity=True)` to the maidens, attic panels/figures, urns and mouldings -- 92 meshes have
no attribute today, and with all of them covered the presence ramp can go away.

### 2. Far-field library gaps (ENV)

`MAT_backdrop_asphalt` and `MAT_backdrop_roof_tile` did not exist, so ENV's new Marina/Presidio city field shipped on
`env_lib`'s flat placeholders. Both are now in the library, cheap by design (no textures, world-space noise only) with
per-object variation through `PFA_instance` (Object Info Random hashed with ENV's `instance_seed` property):

- **MAT_backdrop_asphalt** -- centred on the placeholder's 0.052 grey: sun-bleached wheel tracks (0.030 -> 0.078),
  darker resurfacing patches, grit, +-15 % per object, roughness 0.72 +- 0.09.
- **MAT_backdrop_roof_tile** -- mission tile: 0.31 m courses off world Z (parallel to the eaves whichever way a
  building faces) and pans off world X+Y, both sub-pixel past 250 m; the part that reads is the per-building spread,
  **+-6 deg of hue and +-17 % of value**, with ~15 % of roofs grey composition instead of clay, plus moss.
  Test objects for both are in `MAT_test` (three rotated roof blocks with different `instance_seed`, an asphalt strip).

**MAT_backdrop_forest** darkened and cooled: albedo -55 % and B/G 0.43 -> 0.63 (so warm sun cannot drive it yellow),
a new two-scale gap-shadow mask with a downward bias that puts ~40 % of the surface at 0.34x, specular 0.15 -> 0.06,
roughness 0.90 -> 0.92. Justification from ref 105: its tree masses measure lum 120-152 against a sunlit lawn at 142
and sunlit stucco at 182, at saturation 0.04-0.13 -- a canopy is never brighter than grass and is barely coloured,
because most of what the eye sees is self-shadowed gaps, not leaf albedo.

**What that bought, and the measurement that matters more.** On cam06 the canopy band went lum 128.0 -> 121.7 and
hue 38.6 -> 36.0; canopy/lawn 1.158 -> **1.128** against ref 105's 0.85. A 55 % albedo cut moving the display value
by 5 % is not a tuning failure: solving `L = H + k*A` across the two renders gives **H = 112 of 128 display levels**,
i.e. **88 % of a 250-450 m canopy pixel is the atmospheric veil**, and albedo has 12 % authority over it. **For
lighting: the far field's brightness and its yellow are the haze, not the canopy shader** -- the same conclusion
round 4 reached for the near water, now measured on land. Going further on albedo would leave the canopy as mud the
moment the veil is reduced.

### 3. Coffer ribs -- checked, and it is not materials'

Ref 083 / `coffered_ceiling_1` is unambiguous: the panel fields are the **palest** surface in the rotunda and the rib
bands are dark golden-brown. Statistic used (robust, no hand-placed boxes): over the saucer, mean of the darkest
quarter of pixels over mean of the lightest quarter.

| | dark quarter | light quarter | ratio | sd |
|---|---|---|---|---|
| ref 083 | 68.3 | 155.6 | **0.439** | 34.9 |
| render, round-4 library (cam04 Eevee LOD1) | 72.2 | 127.1 | **0.568** | 23.6 |
| + `Recess Dirt` and `Cavity` halved | 72.5 | 127.1 | 0.571 | 23.5 |
| + rib mask keyed on AO openness, `Recess Distance` 1.1 m | 66.4 | 103.4 | **0.642** (worse) | 16.8 |

`Rib Grime` **is** driven (0.85 on `MAT_plaster_ceiling`) but it is keyed on `|Nz|`, so it only ever reaches the 1-2 px
coffer *returns*, never the rib web. And a shader cannot reach the web: ARCH hangs the rib plate 0.55 m **below** the
panel field (`arch_build.build_ceiling`, both objects on the same sphere, both `MAT_plaster_ceiling`), so ribs and
panels are parallel down-facing planes -- same normal, same object-space frame, and an AO probe reads both as open,
which is why keying on openness simply dirtied the whole saucer. Halving the AO terms moved the ratio by 0.003, so
the saucer's tone is geometry and light, not shading. **`MAT_plaster_ceiling` is therefore left exactly at its
round-4 values** rather than shipping a change that measures as nothing.

**For architecture:** give the rib plate its own material name (say `MAT_plaster_rib`) -- one string in
`arch_build.build_ceiling`, since the field and the plate are already separate objects. Materials will ship a dark,
grimy, ornamented rib material against ref 083 the same day. **For ornament:** ref 083's ribs are dark partly because
they carry guilloche / bead-and-reel mouldings that self-shadow; ours are plain flat bands.

### Files

Before/after (round-4 library vs round-5, same master, `--swap`): `renders/previews/materials/r5before_scene_*.png`
and `r5after_scene_*.png` (`capital`, `cam06`, `ceiling`), attribute debug `r5dbg_scene_capital.png`, composite
**`renders/qa_comparisons/mat_r5_sheet.png`**, raw numbers `renders/qa_comparisons/mat_r5_numbers.txt`.

### Open, and whose

1. **Ornament** -- cavity probe radius (6 % of the diagonal is below the visible scale) and cavity coverage (92 of
   106 meshes have none).
2. **Architecture** -- a separate material name for the coffer rib plate; ref 083's panels are the palest surface in
   the rotunda and ours are not.
3. **Lighting** -- 88 % of a 250-450 m canopy pixel in cam06 is the atmospheric veil; the far field's brightness and
   yellow cast are the haze, not `MAT_backdrop_forest`.
4. Round 4's three lighting hand-offs (sunlit stone saturation/R-B, shaded stone hue, column-shaft fill, near-water
   hue) are unchanged and still open.
## Round 6 (Phase 4 polish round 4, 2026-09-08) -- QA-04-3 (blocker) / -04-5 / -04-7 / -04-8

Method as in rounds 4 and 5: two library versions rendered on ONE `master.blend` with
`mat_scene_check.py --swap`, so every before/after pair below differs **by the library and by nothing else** --
same geometry, same lighting r10 rig, same baked probes, same exposure. "Before" is the round-5 library
(`git show HEAD~1:assets/materials.blend`), "after" is round 6. Hero at 1920x1080 Cycles 96 spp; the chroma and
std-dev boxes are `mat_r4_measure.py`'s (unchanged since round 4, so the numbers are comparable across four
rounds), and the three tests QA-04 wrote in prose are now scripted in `scripts/mat_r6_measure.py`.

### QA-04-3 (blocker, third round of the same finding) -- why procedural tuning could not fix it

Rounds 4 and 5 moved the attic's luminance std-dev by 0.02 of the photo's between them. The reason is scale, and
it is arithmetic, not taste. The library's only photographic input was the Poly Haven concrete set, box-projected
on a **2.2-2.7 m tile**. The hero is 1920 px across a ~95 m frame, i.e. **~5 cm/px**; a 2K map on a 2.7 m tile is
**1.3 mm/texel**, so every hero pixel averages ~1500 texels of it. No amount of `Detail Strength` survives that.
Everything the eye actually reads as weathering on a building at 100 m lives at **0.3-3 m**, and the library had
nothing there except band-limited procedural noise, whose amplitude had already been pushed to where any more
would read as blotches rather than as surface.

So this round brings real surface information in at the right scale.

**`scripts/mat_make_grunge.py`** builds three macro maps from **CC0 ambientCG** flat-wall scans:

| map | source (CC0 1.0) | tile | std | what it carries |
|---|---|---|---|---|
| `pfa_macro_stain` | Concrete019 | 9.0 m | 0.137 | broad soft pour / damp blotches, 1-3 m |
| `pfa_macro_blotch` | Concrete035 | 5.5 m | 0.126 | mid-scale weathered mottle, 0.3-1.5 m (second, decorrelating layer) |
| `pfa_macro_streak` | Concrete036, stretched 3.2x vertically | 7.0 m | 0.188 | run-off: 0.2-0.6 m wide, 1-3 m long dark runs |

Each is luminance **divided by a heavy gaussian blur of itself** -- the scan's own lighting and exposure removed,
leaving the reflectance ratio at mean exactly 1.0 -- then clipped at 3 sigma, rescaled to the amplitude that reads
at hero distance, and made tileable by a crop-and-feather wrap (no mirroring: mirror symmetry is visible on a
40 m wall). 8-bit greyscale, **128 = ratio 1.0**. Licence, URL, crop and derivation per map in
`assets/textures/pfa/sources.json`; the downloaded colour maps are kept under `assets/textures/pfa/_src/` so the
build is reproducible offline.

**Why CC0 scans and not the PFA photos.** The reference corpus was tried first (`mat_make_grunge.py --preview`
-> `renders/qa_comparisons/mat_grunge_candidates.png`). Every raw photo in `reference/photos/raw` is capped at
1920 px on its long edge, and at that size every frontal wall region of this building also contains a moulding, a
dentil course or a sculpture group. Tiling one of those over a wall stamps fake architecture on it. The
PFA-specific part of the look is carried instead by the amplitudes, the tile sizes and the band placements, all
measured from the reference, and by the procedural layers already in `PFA_concrete`.

**New `PFA_concrete` inputs** (all default 0.0 except `Macro Rough`/`Ledge Band`, so nothing not listed changes):
`Macro`, `Macro Scale`, `Macro Streak`, `Macro Rough`, `Ledge Band`, `Damp Band`. The maps are box-projected in
**world** space (plus the per-instance offset), not object space, so the field runs continuously across ARCH's
separate meshes and the run-off runs down the wall whatever an object's own axes are. They multiply albedo value
(mean 1.0, so round 4's calibrated chroma is untouched) and push roughness with the same signal, because a dark
stain on concrete is also a rougher, more porous patch -- that pairing is what stops it reading as a printed decal
in raking sun.

### QA-04-3b -- the dark streak under the cornice and the string course

Round 4 already had a "ledge run-off" band, and QA still found no streak. The mask was the problem: the streak
group's `Ledge` output is an **isotropic** shelter probe (AO along the surface normal), so it drops in every
inside corner and only weakly under a projection -- it cannot tell "there is a cornice above me" from "I am in a
reveal". Round 6 adds a second probe that asks the actual question: an AO probe whose **normal is tilted hard
toward +Z** (`normalize(N + 1.6 Z)`), so most of its rays leave the wall going upward and only a cornice, string
course or box rim above can occlude them. A pure +Z normal cannot be used -- half its rays would start into the
wall itself and return a constant ~0.5 regardless of the geometry above.

The band is then `max(isotropic ledge, overhang)`, gated to near-vertical faces, **broken up along its length by
the macro streak map** (a clean painted stripe is exactly what a cornice does not have), scaled by the new
`Ledge Band` input (ochre 1.20, podium 1.10, colonnade 1.15 against round 4's flat 0.62) and tinted
(0.50, 0.455, 0.375) where round 4 used (0.655, 0.605, 0.515). Peak darkening goes from ~34 % to ~50 %.

### QA-04-3c -- the waterline

`--probe` (new in `mat_scene_check.py`) first checked the obvious explanation, that the shore belongs to somebody
else's material: it does not. Every mesh crossing z = WATER_Z +- 1 m within 220 m of the origin carries a library
material (626 slots `MAT_concrete_colonnade`, 61 `MAT_concrete_podium`, plus soil / lawn / gravel / rip-rap). The
band was simply too narrow and too high-contrast-free to read: it was a hard algae line with nothing above it.

`PFA_algae` now also outputs **`Damp`** (a wet zone reaching ~1.35 band-heights above the growth line, noise
broken) and **`Brown`** (a second field that splits the band between filamentous green low down and rust-brown
tide scum at the top edge, per the reference sheet's "green algae/black tide band ... efflorescence streaks below
the band", refs 093 and 091). Concrete mixes the damp zone at 0.60 toward (0.60, 0.605, 0.575) of its own colour
and drops roughness to 0.34 there (wet stone is dark and glossy); the algae band itself is mixed 0.70 toward
green (0.052, 0.082, 0.040) / brown (0.098, 0.076, 0.040). `Algae Height` came down (ochre 1.0 -> 0.75, podium
1.1 -> 0.85) so the growth line sits **0.3-0.8 m above WATER_Z**, which is what the lead specified and what the
reference shows. The same damp zone is now on `MAT_soil`, `MAT_lawn`, `MAT_gravel_path` and `MAT_rock_riprap`.

### QA-04-3d -- patched repairs

The cell field was already Chebychev (rectangles) and noise-warped; what was wrong was that every patch was
6 % *lighter* with a 0.05-wide ramp. Round 6: the ramp is 0.11 (a skim coat feathers into the wall), the tone step
is +-16 % taken from a second component of the same cell, so roughly half the patches are lighter and half darker,
and coverage went from ~5 % to ~7 % on the walls (`Patches` 0.22 -> 0.30 ochre, 0.22 -> 0.32 podium, 0.15 -> 0.22
colonnade, 0.16 -> 0.24 paving).

### QA-04-5 columns -- chroma, not level

The hero column mask measured lum 122 (test <= 120), hue 31.2 (test 20-29) and sat 0.753 (ref 0.588). Round 4 had
already cut 37 % of the albedo for 3 % of display value, so cutting again would only make brown mud in the sun.
The error QA names is chroma, and chroma is cheap: `MAT_column_rose` Base Color
`(0.316, 0.158, 0.021)` -> `(0.300, 0.1415, 0.056)`. Blue x2.7 (these shafts are integral-pigment concrete
weathered toward mauve-grey, not saturated terracotta -- ref sheet: "vertical streaks of paler mauve-grey
(0.42, 0.24, 0.21) where washed", "saturation ... never above 0.6") and G/R 0.500 -> 0.472, which is the -6 deg of
hue the mask asks for, at only -6 % luminance. `Wash Color` follows to (0.372, 0.246, 0.172), `Wash` 0.55 -> 0.60,
`Tone Variation` 0.24 -> 0.34, `Drum Variation` 0.11 -> 0.13, plus the macro layer at `Macro Scale` 0.45 -- that
is the "strong tonal variation" the sheet describes and the lead asked for instead of a blind albedo cut.

### QA-04-7 coffers -- the rib material the lead named

`MAT_plaster_ceiling_rib` now exists (ARCH assigns it to the saucer-dome and barrel-vault rib faces this round).
Ref 083 / `coffered_ceiling_1`: panel fields are the palest surface in the rotunda at L 93-130 and the rib bands
read L 22-50, so the rib albedo is ~0.37-0.40 of the panel's and cooler. Base Color (0.212, 0.186, 0.070) against
the panel's (0.572, 0.470, 0.130), red pulled down harder than green, `Recess Dirt` 0.85 at 0.35 m, `Cavity` 0.95,
`Underside Dirt` 0.35, roughness 0.92, specular 0.18.

The second half of QA-04-7 -- "no dirt gradient inside any coffer" -- becomes possible for the first time *because*
of the split. Round 5 measured that a long AO probe on a shared material dirties the whole saucer (dark/light
quarter ratio 0.568 -> 0.642 against ref 083's 0.439), because the rib plate hangs 0.55 m below the panel field on
the same sphere: both are parallel down-facing planes with the same normal and the same AO openness. With the ribs
carrying their own material, a **1.3 m AO probe on the panel material is exactly the in-coffer gradient** -- it
sees the rib plate below and the coffer returns around, darkens each panel toward its own frame and leaves the
middle of the field clean. `Recess Distance` 0.5 -> 1.30, `Recess Dirt` 0.70 -> 0.82, `Rib Grime` 0.85 -> 0.30
(it only ever reached the 1-2 px coffer returns, which do belong to the panel object), `Tone Variation`
0.13 -> 0.20 and the macro layer at `Macro Scale` 0.32 for per-coffer tonal spread.

### QA-04-8 near water -- where the missing green can come from

Round 4 measured three levers that did nothing: brightening the murk 1.8x, a warm `Specular Tint` (Blender tints
F0 only and this crop is all F90) and dropping `Transmission Weight`. Round 6 uses the one grazing-weighted lobe
the Principled has: **sheen**. A teal `Sheen Tint` (0.22, 0.62, 0.46) at `Sheen Weight = 0.34 x near` lands on the
near, grazing water -- the same angular dependence a surface scum / biofilm film has -- and leaves the facing water
and the building's reflection alone. The near murk also goes properly green, (0.140, 0.158, 0.130) ->
(0.104, 0.186, 0.132), so the 15-25 % of the pixel that is not Fresnel carries green instead of green-grey.

For the second half of QA-04-8 -- the sunlit-stone reflection reading grey (sat 0.146 vs ref 0.339) -- the cause is
the chop, not the tint: at 20-45 m the ripple was smearing the ochre reflection together with the sky directly
above it until the two averaged out. The near band is pulled in from 70 m to **45 m** and its 0.04 m chop layer
weakened 0.18 -> 0.13, so the mid-distance reflection holds its colour while the last 20 m in front of the camera
keep the break-up QA-03-7 bought.

### Measured: round-5 library vs round-6 library, one master, `--swap`, 1920x1080 Cycles 48 spp

Both columns are the same `master.blend`, the same lighting rig and the same exposure (-2.3331, `--ev 0.0`); only
the library differs. **These absolute numbers are NOT comparable to QA round 04's**, which was rendered on
lighting's r10 rig: this worktree's master still carries the rig it was built with, so the r5 column is the honest
baseline here, not QA's table. Reference is QA's ref 169 warped into the render frame (panel 1 of
`round04_cam01_aligned_vs_ref169.png`), read with the same script.

| metric (mat_r4_measure boxes) | round-5 library | **round-6 library** | ref 169 | test |
|---|---|---|---|---|
| **attic luminance std** 900 222 1020 256 | 20.84 (0.476 of ref) | **26.15 (0.598)** | 43.77 | >= 0.60 -- **at the bar** |
| **entablature luminance std** 900 262 1020 296 | 33.07 (0.512) | **32.79 (0.507)** | 64.62 | >= 0.60 -- **fails, see below** |
| attic sunlit lum / hue / sat / R-B | 197.7 / 37.7 / 0.440 / 102 | **185.5 / 38.3 / 0.511 / 114** | 189.2 / 40.6 / 0.581 / 134 | lum 0.98 pass |
| entablature lum / hue / sat | 181.1 / 38.0 / 0.507 | **152.7 / 39.1 / 0.681** | 145.5 / 33.7 / 0.586 | lum 1.24 -> **1.05** |
| dome cap lum / sat | 209.9 / 0.288 | 206.6 / 0.305 | 227.9 / 0.266 | unchanged, as intended |
| **columns (mask) lum / hue / sat** | 154.7 / 30.1 / 0.650 | **119.4 / 26.8 / 0.647** | 95.3 / 24.5 / 0.589 | hue 20-29 **pass**; lum 1.25x |
| under-cornice run-off, attic col sd | 8.2 | **9.4** | 19.4 | |
| under-cornice run-off, entablature col sd | 10.7 | **12.8** | 13.8 | **0.93 of the photo** |
| waterline: columns >= 20 lum darker | 50.0 % | **59.2 %** | 39.2 % | median drop 19.4 -> **26.7** |
| near water hue / sat | 204.8 / 0.487 | 203.8 / 0.505 | 189.9 / 0.248 | **fails** (185-200) |
| sunlit-stone reflection hue / sat | 43.8 / 0.143 | 48.9 / 0.130 | 33.6 / 0.363 | **fails** (sat >= 0.28) |
| coffer field dark/light quarter | 0.212 | 0.195 | 0.439 (ref 083) | ARCH's rib split not in this master yet |

**Getting there took three passes and both of the first two are worth recording.**

*r6a (macro at 9.0 / 5.5 / 7.0 m tiles, amplitude 0.15):* attic std 20.84 -> 23.36. Far less than the close-range
A/B suggested, and the reason is that **QA measures the attic on a 120 x 34 px box, which is 6.0 x 1.7 m at the
hero's 5 cm/px**. A 9 m tile puts most of its energy *outside* the measurement window. Tiles came down to
5.5 / 3.2 / 4.5 m and amplitudes up to 0.19 / 0.17 / 0.24.

*r6b (smaller tiles):* 23.36 -> 24.75. Still short, and the reason is AgX: a symmetric +-19 % linear swing at
lum ~190 is only about +-5 % of display, because that is exactly where the curve compresses hardest. The macro
layer is therefore **biased 35 % toward its dark half** (which is also what real staining does -- it darkens far
more than it lightens) and `Macro` went to 1.85-1.95 on the wall concretes: **24.75 -> 26.15**.

**The entablature box is not shading and this is now the second round saying so.** Its luminance std did not move
(33.07 -> 32.79) while its *mean* fell 181 -> 153, i.e. relative contrast went 0.183 -> 0.215 against the photo's
0.444. In ref 169 that box contains dentils, modillions and a deep cornice undercut throwing near-black shadow;
ours contains a much shallower cornice. **For architecture: cornice projection and dentil depth on the attic
entablature is the remaining half of QA-04-3, unchanged from the round-4 hand-off.** The columnwise run-off metric
is the one that isolates shading in that box, and it now reads 12.8 against the photo's 13.8.

### QA-04-8 -- three shader levers measured, and the conclusion is that this is not the water shader's to fix

Environment's magenta-bed probe settled one half of it: at QA's 18-20 deg grazing crop **0.00 %** of the near-water
pixels see the lagoon bed, so there is no upwelling to tint. That leaves the surface, and the surface has been
measured three ways now:

| water configuration | near-water hue (ref 189.9) | sunlit-stone reflection hue / sat (ref 33.6 / 0.363) |
|---|---|---|
| round 5 | 204.8 | 43.8 / 0.143 |
| r6a: hard green near murk, chop band 45 m | 202.6 | **66.5 / 0.122** |
| **r6c (shipped): teal sheen on a 22 -> 5 m ramp, near-neutral murk, chop band 62 m** | 203.8 | 48.9 / 0.130 |
| r6d experiment: sheen weight 1.0 on a 70 -> 6 m ramp, tint (0.09, 0.72, 0.50) | 201.2 | **134.1 / 0.143** (green) |

Round 4 had already measured the fourth lever, `Specular Tint`, at 0.475 -> 0.473 (Blender tints F0 only and this
crop is all F90). So: **every knob that reaches the sky-reflecting crop also sits under the reflection column**, and
the most any of them moves the crop hue is ~3.6 deg out of the ~14 deg needed, at the cost of turning the stone
reflection green. That is not a tuning failure, it is what the crop is: at 18-20 deg the surface is >= 85 % Fresnel
mirror, so its hue *is* the reflected sky's hue plus a few degrees of surface tint. **For lighting: the near-water
hue 203.8 vs 189.9 is the horizon sky's, the third round in a row this measurement has landed there** (round 3 for
the flank, round 4 for the near field with the murk experiment, round 6 with the sheen experiment and ENV's bed
probe). The shipped r6c setting keeps the small honest gain (the murk stays near-neutral so the reflection is not
greyed, the chop band is back to 62 m so the mid-distance reflection holds its colour) and does not fake the rest.

### ENV hand-offs folded in this round

- **`MAT_lagoon_bed`** (new, `use_fake_user`): the lagoon floor ENV split onto its own name. Deliberately cheap --
  no textures, world-space silt drifts (5-15 m) over a mud/weed mottle (1-3 m), a lighter exposed-silt zone in the
  last 0.5 m before the shore, roughness 0.94, specular 0.15. It is only ever seen through the first metre or two
  of water at the shore.
- **Shore foliage albedo**: ENV measured the hero shoreline crop at lum 72.9 against the photo's 107.2 and
  attributed it to leaf albedo rather than planting. `MAT_shrub` (1.0 -> 1.42), `MAT_shrub_light`
  (1.25 -> 1.78), `MAT_shrub_dry` (4.50 -> 6.30 on red) and `MAT_reeds` (1.0 -> 1.40) tints raised ~1.4x. This is a
  first pass on somebody else's measurement and it wants re-measuring on the next hero.

### Files

Before/after on one master, `--swap` (round-5 library vs round-6): `renders/previews/materials/r6before_scene_*`
and `r6after_scene_*` (`hero`, `ceiling`, `stone`); the maxed-sheen experiment is `r6sheen_scene_hero.png`.
Composite **`renders/qa_comparisons/mat_r6_sheet.png`**; PFA-photo macro candidates (evaluated and rejected)
`renders/qa_comparisons/mat_grunge_candidates.png`. New scripts: `mat_make_grunge.py`, `mat_r6_measure.py`,
`mat_r6_sheet.py`; `mat_scene_check.py` gained `--probe` and `--lib`.

### Open, and whose

1. **Architecture** -- cornice projection / dentil depth on the attic entablature. Second round: the entablature
   box's std did not move under shading (33.07 -> 32.79) while its mean fell to 1.05 of the photo's, and the
   columnwise run-off metric that isolates shading now reads 12.8 against the photo's 13.8.
2. **Architecture** -- `MAT_plaster_ceiling_rib` is built and waiting; this master does not carry the assignment
   yet, so the coffer dark/light ratio (0.195 vs ref 083's 0.439) cannot be scored until it lands.
3. **Lighting** -- near-water hue, third round (see the table above); column-shaft fill (the mask is 1.25x the
   photo after this round's chroma work, down from 1.62x in round 4); sunlit stone saturation and the shaded-stone
   hue from round 4 are unchanged and still open.
4. **QA** -- the attic std ratio is 0.598 against a 0.60 bar. It is at the bar, not past it; the remaining lever on
   the materials side is more macro amplitude, which starts to read as blotch rather than surface.
