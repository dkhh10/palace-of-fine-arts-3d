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
