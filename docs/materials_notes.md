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
1. base albedo (sheet values, warmed: see "calibration") with per-instance hue +-3 % / value +-8 % (`Instance Variation`);
2. cast-block tone steps: axis-aligned Chebychev Voronoi cells (`Block Size`, +-`Tone Variation`), soft pour blotches
   (`Blotch Size`), fine speckle (30/m, +-7 %);
3. photo detail: box-projected CC0 concrete diffuse used as *luminance only*, normalised by its mean (`Detail Mean`) so it
   never changes the hue, weight `Detail Strength`; its roughness map modulates roughness, its displacement drives the bump;
4. grey/damp drift toward `Grey Color`: 0.7 x (world z below `Grey Below Z`..`Grey Above Z`) + noise; the lower 8 m of the
   rotunda go grey-tan, the attic stays warm;
5. formwork/pour lines every `Pour Spacing` (object z), broken by noise; slab grid joints (`Grid Joints`, paving);
6. repair patches: sparse sharp Chebychev cells, +14 % value, -20 % saturation, tiny bump step;
7. rain streaks (`PFA_streaks` x `Streaks`), tint x (0.36, 0.37, 0.31);
8. recess dirt: `1 - AO(Recess Distance)` x `Recess Dirt` (+ `Extra Dirt` from bakes, + `Underside Dirt` on down-facing
   faces for soffits), tint x (0.5, 0.47, 0.42) = the sheet's "recesses 0.55 x plain";
9. edge wear (`PFA_edge` x `Edge Wear`): +22 % value, -15 % saturation, -0.15 roughness on convex arrises;
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
| MAT_concrete_ochre | (0.47, 0.31, 0.135) Y 0.33 | concrete_wall_008 (2.71 m tile: precast panel with tie holes + faint joints) | upper rotunda: walls, entablature, attic, drum. Streaks 1.0 under ledges (shelter 3 m, weight 0.55), patches 0.25, edge wear 0.45 @ 3 cm, recess dirt 0.55 @ 0.4 m, pour lines 0.6 m, rough 0.78 +- 0.12 |
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
| MAT_dome_membrane | (0.70, 0.645, 0.535) | procedural | semi-gloss urethane: roughness 0.35 (+0.22 in streaks), Coat 0.4 where clean, specular 0.5; 48 lap seams (5 cm, bump), radial streaks strongest on the lower third (`Base Normal Z` 0.66 = the cap's base slope), moss patches (0.34, 0.42, 0.28) on the -X flank, grime ring (0.20, 0.13, 0.06) at the base with a 6 mm-in-nz irregular edge |
| MAT_water_lagoon | Cycles: surface tint (0.62, 0.80, 0.68), IOR 1.333, transmission 1 + volume; Eevee: opaque murk (0.025-0.045, 0.05-0.075, 0.035-0.045) glossy, IOR 1.333 | procedural | roughness 0.02-0.06 (noise 0.12/m), normal = bump of 0.3 m + 3 m + 0.1 m ripple noises (4D, `WATER_TIME` value driven by `frame*0.03`), calmer patches (wind shadow, 25 m noise); volume (Cycles output): one Principled Volume, density 0.5, scatter colour (0.06, 0.10, 0.07), absorption colour (0.23, 0.45, 0.21), anisotropy 0.4 (= absorption ~0.39/0.28/0.40 per m + weak scatter; Absorption+Scatter+Add exceeded Cycles' 64-closure budget). Two Material Output nodes (`target` CYCLES / EEVEE); the Eevee one is Diffuse+Glossy by Fresnel |
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
- Not done: a leaf normal/translucency map (single colour+alpha only), separate pine/redwood needle material
  (`needles_pine.png` is generated but ENV maps all conifers to MAT_leaf_cypress), rustication joints for the podium
  (expected as geometry from ARCH), a dedicated efflorescence texture (procedural only).
