# Brief: Materials and Texturing

You own `assets/materials.blend` and `scripts/mat_*.py`. Read: `CLAUDE.md`, `docs/reference_sheet.md` (material catalog,
sampled colours), `docs/tech_notes.md`, `scripts/common.py`. Look at `reference/photos/material_crops/` and the user's
target image before writing a single node. The previous attempts failed on materials above everything else: uniform
bright stone, plastic pink columns, mirror water. Your library is the single biggest lever on photorealism.

## Deliverables
1. `scripts/mat_build.py` (+ `scripts/mat_lib.py` node helpers): idempotently builds every material below into a fresh
   file and saves `assets/materials.blend` (materials only, plus the test-scene objects in a collection `MAT_test`).
   Give every material `use_fake_user = True` so it survives linking.
2. `scripts/mat_lineup.py`: builds a test scene (linked placeholder blockout from `assets/placeholder_blockout.blend`
   for scale, a 3 x 3 m concrete wall panel, a fluted column section, a corner block, a water tank, a lawn patch) lit by
   the golden-hour sun (az 118, el 7.8, see tech notes) and renders each from a fixed camera with BOTH Eevee and Cycles
   (128 spp) into `renders/previews/materials/`. Also render the placeholder blockout from `CAM_qa_01` with your
   materials applied by name to its objects (its objects use the library names already).
3. `docs/materials_notes.md`: per material, the node strategy, parameters, textures used (source, license), how the
   per-instance variation works, and Eevee vs. Cycles differences.
4. Textures under `assets/textures/` (committed, relative paths, 2K max, total under 200 MB). CC0 sources allowed
   (Poly Haven, ambientCG: download with curl, record URL + license in the notes). Procedurally generated images are welcome.

## Material contract (names are binding; other agents assign by these names)
MAT_concrete_ochre (upper rotunda walls, entablature, attic, drum), MAT_concrete_podium (piers, pedestals, rostra,
platform, lower zone with algae band), MAT_concrete_inner (vault soffits, inner arch ring), MAT_column_tan_inner (8 inner columns and their blocks),
MAT_plaster_ceiling (coffered saucer), MAT_drum_band (bronze-brown guilloche band), MAT_column_rose (fluted pink column shafts), MAT_dome_membrane (urethane-coated roof, semi-gloss), MAT_concrete_colonnade, MAT_paving
(platform floor/steps), MAT_ornament_concrete (all ORN instances: capitals, maidens, urns, panels; must include a
per-instance variation and a recess-darkening term that works from geometry, since ornament has dust in the hollows),
MAT_water_lagoon, MAT_lawn, MAT_soil, MAT_gravel_path, MAT_rock_riprap, MAT_bark_cypress, MAT_bark_eucalyptus,
MAT_leaf_cypress, MAT_leaf_eucalyptus, MAT_leaf_broadleaf, MAT_shrub, MAT_backdrop_building, MAT_bird_white.

## Requirements
- Concrete family: base tone from the sheet's sampled colours (they are muted; verify against the crops in golden light
  and midday). Layered: (1) large-scale panel/pour variation (per-pour tonal patches of ~2-4 m), (2) fine aggregate
  speckle and micro-roughness, (3) vertical rain streaks in world space (stretched noise, stronger below horizontal
  ledges: use the normal's Z and a downward-shifted AO/noise), (4) dark algae/moss band near WATER_Z (from world Z,
  fading over ~0.6 m, with irregular upper edge), (5) patch repairs (sparse cells with slightly different tone and
  sharper edges), (6) edge wear (lighter, smoother on convex edges: Bevel node in Cycles, AO-based fallback in Eevee),
  (7) dust/dirt accumulation in concave areas (AO node, works in both engines). Roughness 0.55-0.8 with variation; a
  faint specular sheen in raking sun (do not make it glossy). All in object/world space (triplanar) so no UV seams.
- Per-instance variation via Object Info Random for hue (+-3%), value (+-8%), streak offset and patch pattern.
- Columns: dusty terracotta rose with lighter worn crests on the flute ridges and darker flute valleys; NOT saturated.
- Water: Principled BSDF transmission 1.0, IOR 1.333, roughness 0.02-0.06 with variation, base colour dark green,
  volume absorption tinted green-brown so shallow edges show the bed; normal from two layered procedural ripple noises
  (0.3 m and 3 m scales, low amplitude) with an optional `frame`-driven drift for animation; must render in both engines
  (Eevee: enable screen-space refraction/raytracing on the material).
- Foliage: leaf materials with translucency (Translucent mixed 0.3) and colour variation per instance.
- Everything must survive being appended into another file by name (no dependencies on scene objects except the
  common WATER_Z constant baked into the node values; document it).

Commit after each material group renders acceptably. Test at hero distance (~120 m) AND at 3 m.
