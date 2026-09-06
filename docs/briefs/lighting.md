# Brief: Lighting and Rendering

You own `assets/lighting.blend` (collection `LIGHT`, world `WORLD_golden_hour`) and `scripts/light_*.py`, and you own
the final render settings the lead applies in master.blend. Read: `CLAUDE.md`, `docs/decisions.md` (why the sun is a
MORNING sun from the east-south-east), `docs/reference_sheet.md` (golden-hour section), `docs/tech_notes.md` (sun table,
sky node API, NOAA function), `scripts/common.py` (`aim_sun`, `configure_*`).

## Chosen moment
2026-11-10 07:30 PST at 37.8029 N, 122.4484 W: sun azimuth 118.5 deg (clockwise from north; north = -X, east = +Y),
elevation 7.4 deg (matches the golden-hour reference photo ref 169). Recompute with `sun_calc.get_sun_coordinates(7.5, 37.8029, -122.4484, 8, 11, 10, 2026)` and store
date/time/lat/lon as custom properties on the sun object and in the notes. Make the time a single parameter so the lead
can render an evening alternate (2026-10-20 17:45 PDT, az 251, el 6.9) with one change.

## Deliverables
1. `scripts/light_build.py`: idempotently builds `LIGHT` (sun `LIGHT_sun` aimed with `common.aim_sun`, any fill you
   justify) and `WORLD_golden_hour` (sky texture `MULTIPLE_SCATTERING` with the same elevation/azimuth, sun disc OFF in
   the world because the lamp provides the disc, unless you show the disc-on approach is better; aerosol/haze tuned for
   a clear autumn morning with a warm horizon), and saves `assets/lighting.blend`. Verify the sky's `sun_rotation`
   convention empirically: render with sun disc ON and confirm the disc sits in the same direction as the lamp's shadow.
2. Calibrated exposure: the sky node is physically scaled. Match the lamp irradiance to the sky's own sun disc (render
   the sky alone to EXR with the disc on, integrate the disc) or use the Sun Position addon's sun/sky binding; then set
   `scene.view_settings.exposure` so an 18% grey card facing the sun renders around middle grey with AgX. Document the numbers.
3. Atmosphere: mist pass + compositor node group (`COMP_golden_hour`): warm aerial haze increasing with depth, subtle
   glare/bloom on the sun-lit highlights, no vignette heavier than 0.1. If you add a world volume, prove it costs under
   30% render time; otherwise stay with the compositor haze.
4. `scripts/light_presets.py` with functions `apply_final_cycles(scene)` (denoise, adaptive sampling, light tree,
   sample count sized for a 4K frame in under ~2 h on this Apple M2 10-core GPU; test with a timed 1280x720 render and
   extrapolate), `apply_viewport_eevee(scene)` (shadows, raytracing, volumetric off, fast), `apply_preview_eevee(scene)`.
   Colour management: AgX, look 'AgX - Base Contrast' or 'Punchy' (justify), gentle contrast, no crushed blacks.
5. Flythrough camera: `scripts/light_flythrough.py` creates in `LIGHT` a bezier curve `CAM_flythrough_path` around the
   lagoon and through the colonnade (start at the east shore hero position, glide along the shore, approach the south
   colonnade, pass between the columns, arrive under the rotunda looking up), a camera `CAM_flythrough` following it
   (Follow Path + Track To an animated empty target), 720 frames at 24 fps, gentle easing. Test by rendering 6
   evenly spaced frames at 640x360 Eevee into `renders/previews/lighting/flythrough_test_*.png`.
6. `scripts/light_preview.py`: temp scene = link `assets/placeholder_blockout.blend` (or ARCH/ENV if present) + your
   LIGHT + world + compositor; render QA cameras Eevee AND a Cycles 128 spp hero into `renders/previews/lighting/`.
7. `docs/lighting_notes.md`: all numbers, the convention checks, render timings, the flythrough timing table.

Compare your hero preview against the golden-hour reference photos from the sheet with `scripts/qa_compare.py`. The
look target: low warm sun, long soft-edged shadows, sky-lit bluish shade that is clearly not black, warm haze on the
distant colonnade, water reflecting a bright warm sky. Commit after each deliverable.
