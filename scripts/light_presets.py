"""Render presets owned by the Lighting & Rendering specialist. Import from any script:

    import light_presets as lp
    lp.apply_final_cycles(scene)      # 4K hero / finals: denoise, adaptive sampling, light tree (budget: see notes)
    lp.apply_viewport_eevee(scene)    # fast navigation: shadows on, raytracing off, no volumetrics
    lp.apply_preview_eevee(scene)     # QA previews: raytracing + shadows, 32 TAA samples
    lp.apply_look(scene)              # AgX + look + calibrated exposure + mist/depth passes + COMP_golden_hour compositor
    lp.apply_rig(scene)               # link LIGHT + WORLD_golden_hour from assets/lighting.blend, then apply_look

Standalone timing test (renders the placeholder with each preset and extrapolates to 3840x2160):
    blender -b --python scripts/light_presets.py -- --time [--samples 512]
"""
import bpy, os, sys, math, time, json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

LIGHT_BLEND = common.ASSET_FILES["LIGHT"]
# THE look, and the ONE place it is defined. Round 08b set light_build.LOOK to "AgX - High Contrast" but this
# constant kept its round-05 value, and it is THIS one that build_master.py writes into master.blend (via
# apply_look), so the delivered master rendered at Base Contrast and the whole round-08b chroma gain was invisible
# in every QA render. Measured on the cam01 hero, same rig, same exposure: Base Contrast gives the sunlit attic
# R-B 94.8 at 960x540 and 97.4 at 1920x1080; High Contrast gives 117.9 at 960x540. In other words round 08b's
# "the sweep is 20 R-B optimistic at delivery resolution" was not a resolution effect at all (resolution is worth
# +2.6 R-B / -2.1 luminance) - it was this divergence. light_build.LOOK now aliases this constant so the two files
# cannot drift apart again.
# Why High Contrast: at +0.9 EV (QA-02-4) the sky-lit shade is 25 % LIGHTER than ref 169, so crushing it is the
# correction rather than the damage that made round 05 pick Base Contrast. Looks measured at strength 1.0 -
# Base 94.8, Medium High 108.6, High 117.9, Punchy 112.7; Punchy also costs a stop on the attic and drops the water
# from 111 to 71 for no extra chroma.
LOOK = "AgX - High Contrast"
FINAL_SAMPLES = 768          # sized by the timing test in docs/lighting_notes.md (4K in < 2 h on the M2 10-core)
FINAL_TIME_LIMIT_S = 0.0     # 0 = none; the lead may set e.g. 6000 s per 4K frame as a hard stop
IRRADIANCE_POOL = "64"       # MB of Eevee irradiance pool; the default 16 cannot hold the two baked probe volumes


def _metal_gpu():
    prefs = bpy.context.preferences.addons.get("cycles")
    if prefs:
        try:
            prefs.preferences.compute_device_type = "METAL"
            prefs.preferences.refresh_devices()
            for d in prefs.preferences.devices:
                d.use = d.type == "METAL"
        except Exception:
            pass


# ----------------------------------------------------------------------------- item 6: the Eevee vault fills
# QA-03 / round-10 item 6. On cam04 the two engines disagreed 3x on the coffered dome (Cycles soffit/own-sky 0.536 and
# coffer/own-sky 0.364; Eevee 0.375 and 1.075). Round 09 blamed the emitters' 45 deg spread. Round 10 measured it
# properly and it is not the spread and not Fast GI:
#   * turning Fast GI off, or dropping fast_gi_distance 60 -> 10 m, moves the Eevee coffer by less than 0.05;
#   * the same file renders the Eevee coffer at 0.246 (960x540) and 1.075 (1280x720), which no real light can do.
# Eevee Next's screen-traced ambient term fills the closed vault volume with light that is proportional to how much of
# the vault is ON SCREEN, and cam04 looks straight up into it. Cycles has no such term. There is no rig that satisfies
# both engines, so the fix is engine-conditional, and the honest lever is `cutoff_distance` (Blender's "Custom
# Distance"), which EEVEE honours and CYCLES ignores: at 13 m each vault emitter still reaches its own soffit (4.5-11 m)
# but can no longer reach the central coffered dome 20.7 m away. Measured on cam04 at 1280x720, Eevee:
#   control                soffit 0.375  coffer 1.075
#   cutoff 13 m            soffit 0.145  coffer 0.246
#   cutoff 13 m, energy x2 soffit 0.201  coffer 0.247
#   cutoff 20 m            soffit 0.165  coffer 0.256
#   cutoff 13 m, energy x5 soffit 0.322  coffer 0.252
#   cutoff 16 m, energy x5 soffit 0.348  coffer 0.255
#   cutoff 13 m, energy x8 soffit 0.408  coffer 0.255   <- shipped: |0.128| and |0.109| from Cycles, both inside 0.15
# Cost on record: Eevee's soffit W/E balance is 0.562 / 0.253 where Cycles reads 0.395 / 0.678, i.e. the two engines
# now lean opposite ways across the vault. The engines agree on the two numbers QA measures and not on their split.
# The coffer lands inside +-0.15 of Cycles as soon as the cutoff is on, and the energy then buys the soffit back
# without touching it. Cycles keeps the physical rig exactly as light_build writes it.
# ROUND 11 REPLACES THE READING ABOVE. The Eevee vault was never short of an ambient term: with the probe volumes
# baked on the physical rig (light_probes.bake, QA-04-1) the baked irradiance ALREADY contains the vault emitters,
# and Eevee then adds their direct light on top, while Cycles path-traces the whole thing once. Eevee with no cutoff
# at the plain physical energy puts the coffer field at 0.839 of the frame's own sky where Cycles reads 0.387: it is
# counting the same eight emitters twice. `cutoff_distance` removes the duplicate rather than faking an ambient term
# - at 21 m each emitter still lights its own soffit (4.5-11 m) and stops double-counting into the coffered dome
# 20.7 m away. Measured on cam04 at 1280x720 against the round-11 Cycles frame (soffit W 0.316 / E 0.532 /
# mean 0.424, coffer 0.387); QA's box is 0.15:
#   x8  + 13 m, baked WITH the cutoff (what QA measured)  W 0.399  E 0.142  mean 0.270  coffer 0.034
#   x8  + 13 m, physical bake                            W 0.428  E 0.194  mean 0.311  coffer 0.240
#   x8  + 18 m                                           W 0.469  E 0.228  mean 0.349  coffer 0.246
#   x6  + 21 m                                           W 0.546  E 0.419  mean 0.483  coffer 0.325   <- SHIPPED
#   x5  + 24 m                                           W 0.517  E 0.413  mean 0.465  coffer 0.568
#   x3  + 25 m                                           W 0.382  E 0.320  mean 0.351  coffer 0.530
#   x4  + 25 m                                           W 0.459  E 0.375  mean 0.417  coffer 0.611
#   x2  + 45 m                                           W 0.443  E 0.392  mean 0.418  coffer 1.145
#   x1, no cutoff (physical)                             W 0.293  E 0.276  mean 0.284  coffer 0.839
# Shipped x6 + 21 m: it puts BOTH numbers QA flagged inside 0.15 of Cycles - the coffer field 0.325 (gap 0.062,
# against 0.227 before) and the soffit E 0.419 (gap 0.113, against 0.380 before) - and the soffit mean, which is how
# ref 083 is quoted, at 0.483 against 0.424 (gap 0.059).
# COST ON RECORD: the soffit W goes to 0.546 against Cycles' 0.316, i.e. 0.230 outside the box, and it was inside
# before (0.399 vs 0.289). W and E move together in Eevee at every cutoff tried, while Cycles wants them 0.22 apart
# in the other direction, so no single override lands all three. The two QA tabulates a window for are the two that
# are landed; the split is an engine-level disagreement and is written up in docs/lighting_notes.md 20.7.
EEVEE_VAULT = dict(energy_scale=6.0, cutoff_distance=21.0)


def _vault_lights():
    # round-10 review nit: the name lives in light_build.VAULT_FILL, not in a literal here. Imported lazily because
    # light_build imports light_presets (for LOOK), so a module-level import would be circular.
    try:
        import light_build
        prefix = light_build.VAULT_FILL["name"]
    except Exception:
        prefix = "LIGHT_rotunda_vault_bounce"
    return [o for o in bpy.data.objects if o.type == "LIGHT" and o.name.startswith(prefix)]


def apply_vault_for_engine(engine):
    """Restore the physical vault-emitter energies for Cycles, or apply the Eevee-only cutoff + energy (see above).
    The Cycles energy is read from the object's own `energy_W` custom property (written by light_build), so calling
    this twice, or in either order, is idempotent."""
    n = 0
    for o in _vault_lights():
        base = o.get("energy_W")
        if base is None:                     # review fix: seed once, so a repeat Eevee call can never compound the x8
            base = o.data.energy
            o["energy_W"] = base
        base = float(base)
        try:
            if "EEVEE" in engine:            # accepts "EEVEE" and Blender's "BLENDER_EEVEE"
                cut = float(EEVEE_VAULT["cutoff_distance"])
                o.data.use_custom_distance = cut > 0.0        # round 11: 0 means "no cutoff", not "zero reach"
                if cut > 0.0:
                    o.data.cutoff_distance = cut
                o.data.energy = base * EEVEE_VAULT["energy_scale"]
            else:
                o.data.use_custom_distance = False
                o.data.energy = base
        except Exception as e:               # linked (read-only) light data: master appends LIGHT, but be safe
            print(f"[light_presets] cannot retune {o.name} ({e}); leaving it at the physical energy")
            try:
                o.data.energy = base
            except Exception:
                pass
            continue
        n += 1
    if n:
        print(f"[light_presets] vault emitters for {engine}: {n} lights, "
              f"{'x%.1f + %.0f m cutoff' % (EEVEE_VAULT['energy_scale'], EEVEE_VAULT['cutoff_distance']) if engine == 'EEVEE' else 'physical energy, no cutoff'}")
    return n


def _lamp_weight(light_build, o):
    """The per-lamp weight `w` of SHADE_FILL["lamps"] for a lamp named LIGHT_shade_fill_NN (1.0 if unknown)."""
    try:
        k = int(o.name.rsplit("_", 1)[1])
        return float(light_build.SHADE_FILL["lamps"][k].get("w", 1.0))
    except Exception:
        return 1.0


def _shade_lights():
    try:
        import light_build
        prefix = light_build.SHADE_FILL["name"]
    except Exception:
        prefix = "LIGHT_shade_fill"
    return [o for o in bpy.data.objects if o.type == "LIGHT" and o.name.startswith(prefix)]


def _gallery_lights():
    try:
        import light_build
        prefix = light_build.GALLERY_FILL["name"]
    except Exception:
        prefix = "LIGHT_gallery_fill"
    return [o for o in bpy.data.objects if o.type == "LIGHT" and o.name.startswith(prefix)]


def apply_gallery_for_engine(engine):
    """ROUND 17: LIGHT_gallery_fill is a CYCLES-ONLY rig (light_build.GALLERY_FILL: 1000 W a strip in Cycles,
    0 W in Eevee), the round-13 shade-fill pattern with the engines the other way round. Eevee's baked irradiance
    volume already carries the colonnade gallery at 5x the Cycles level (cam03 near column 16.9 vs 3.3 lum), and
    sixteen shadow-mapped area lights in the Eevee preview would re-open QA-06-13. Idempotent, and safe on a
    master built before round 17 (no lamps -> no output)."""
    n = 0
    for o in _gallery_lights():
        base = float(o.get("energy_W", o.data.energy))
        eev = float(o.get("energy_W_eevee", 0.0))
        e = eev if "EEVEE" in engine else base
        try:
            o.data.energy = e
            o.hide_render = e <= 0.0
        except Exception as err:
            print(f"[light_presets] cannot retune {o.name} ({err}); leaving it as it is")
            continue
        n += 1
    if n:
        g0 = _gallery_lights()[0]
        print(f"[light_presets] gallery fill for {engine}: {n} strips at {g0.data.energy:.0f} W, "
              f"hidden in render: {g0.hide_render}")


def apply_shade_for_engine(engine):
    """ROUND 13 (QA-05-1, the Eevee half), AMENDED IN ROUND 14 -- read this paragraph, not the round-13 one that
    used to stand here (r15 review carry 4). LIGHT_shade_fill is NOT an Eevee-only rig any more: since round 14 it
    carries a DIFFERENT irradiance per engine, both non-zero (SHADE_FILL 49.0 W/m2 in Cycles, 38.5 in Eevee as
    shipped in round 15), and this function is the switch between them, on the same pattern as the vault override
    above. `hide_render` is therefore False in BOTH engines as shipped; it is set only for whichever energy is 0.
    The round-13 reason the rig exists still stands: Eevee's shaded stone is lit by its screen-traced horizon scan
    rather than by the world, so the round-12 DIFFUSE-only world sockets never reach it (measured: 2.8x the whole
    diffuse sky moves the hero's shaded attic 93.3 -> 96.0 while it moves the near-water box +19.6 % -> +70.2 %;
    freeing the baked irradiance volumes moves it 1.8 lum), and only a directional lamp does.

    Both energies are read from the objects' own custom properties (written by light_build.build_shade_fill), so
    calling this twice, or in either order, is idempotent."""
    n = 0
    for o in _shade_lights():
        base = o.get("energy_W")
        if base is None:
            # r13 review carry 6: NOT o.data.energy -- in the saved state that is the EEVEE 55 W/m2, so a lamp
            # arriving without the custom property would seed the CYCLES energy at the Eevee override's value.
            try:
                import light_build
                # r14 review carry 7: the per-lamp WEIGHT has to be applied too. `SHADE_FILL["energy"]` is the
                # rig total; a lamp whose w is 0.70 must come back at 0.70 x 70, not at 70.
                base = float(light_build.SHADE_FILL["energy"]) * _lamp_weight(light_build, o)
            except Exception:
                base = 0.0
            o["energy_W"] = base
        eev = float(o.get("energy_W_eevee", 0.0))
        try:
            if "EEVEE" in engine:
                o.data.energy = eev
                o.hide_render = eev <= 0.0
            else:
                o.data.energy = float(base)
                o.hide_render = float(base) <= 0.0
        except Exception as e:
            print(f"[light_presets] cannot retune {o.name} ({e}); leaving it as it is")
            continue
        n += 1
    if n:
        e0 = _shade_lights()[0]
        print(f"[light_presets] shade fill for {engine}: {n} lamps at {e0.data.energy:.1f} W/m2, "
              f"hidden in render: {e0.hide_render}")
    # ROUND 17: the gallery rig is switched HERE rather than at every call site. `common.configure_cycles` is the
    # entry point every non-lighting script renders Cycles through and it is not lighting's file to edit, so
    # chaining the two per-engine switches is what guarantees LIGHT_gallery_fill is never left at its Eevee 0 W
    # in a Cycles render (or at 1000 W in an Eevee one). Both are idempotent, so a caller that also calls
    # apply_gallery_for_engine explicitly is still correct.
    apply_gallery_for_engine(engine)
    return n


def apply_final_cycles(scene=None, samples=None, time_limit=None):
    """Cycles settings for the 3840x2160 hero and the flythrough finals."""
    s = scene or bpy.context.scene
    s.render.engine = "CYCLES"
    _metal_gpu()
    c = s.cycles
    c.device = "GPU"
    c.samples = samples or FINAL_SAMPLES
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.01          # noise level target; adaptive stops most pixels well before `samples`
    c.adaptive_min_samples = 64
    c.time_limit = FINAL_TIME_LIMIT_S if time_limit is None else time_limit
    c.use_denoising = True
    c.denoiser = "OPENIMAGEDENOISE"
    c.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    c.denoising_prefilter = "ACCURATE"
    try:
        c.denoising_quality = "HIGH"
        c.denoising_use_gpu = True
    except Exception:
        pass
    c.use_light_tree = True
    c.light_sampling_threshold = 0.01
    c.max_bounces = 8
    c.diffuse_bounces = 3                # sky-lit shade needs real bounce light between warm stone faces.
                                         # QA-01-9: measured on master, cam04 coffers render 11.9/255 at 3 bounces and
                                         # 12.3/255 at 8 - the rotunda vault is starved of light, not of bounces, so
                                         # raising this buys nothing and costs render time. See FILL in light_build.
    c.glossy_bounces = 4
    c.transmission_bounces = 4
    c.transparent_max_bounces = 16       # leaf cards
    c.volume_bounces = 0
    c.caustics_reflective = False
    c.caustics_refractive = False
    c.blur_glossy = 0.5                  # filter glossy: kills water/dome fireflies at little visible cost
    c.sample_clamp_direct = 0.0
    c.sample_clamp_indirect = 10.0
    c.sampling_pattern = "AUTOMATIC" if "AUTOMATIC" in [e.identifier for e in c.bl_rna.properties["sampling_pattern"].enum_items] else c.sampling_pattern
    c.use_auto_tile = True
    c.tile_size = 2048
    s.render.use_persistent_data = True
    s.render.film_transparent = False
    s.render.filter_size = 1.5
    s.render.use_motion_blur = False
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_depth = "16"
    # r13 review carry 11 (root cause of the 10 MB tracked panels): film_transparent is False two lines up, so the
    # alpha plane was 25 % of every file at a constant 1.0, and compression 15 left the rest barely deflated.
    # Both changes are LOSSLESS -- the RGB planes are bit-identical, only the file gets smaller.
    s.render.image_settings.color_mode = "RGB"
    s.render.image_settings.compression = 90
    apply_vault_for_engine("CYCLES")
    apply_shade_for_engine("CYCLES")
    return s


def apply_viewport_eevee(scene=None):
    """Eevee for flying around in the viewport: cheap but with real sun shadows."""
    s = scene or bpy.context.scene
    s.render.engine = "BLENDER_EEVEE"
    e = s.eevee
    e.taa_samples = 8
    e.taa_render_samples = 16
    e.use_shadows = True
    e.shadow_ray_count = 1
    e.shadow_step_count = 2
    e.shadow_resolution_scale = 0.5
    e.use_shadow_jitter_viewport = False
    # QA-04-12, ROUND 11. The brief asked whether the viewport preset should carry raytracing on, because Eevee's
    # screen-traced ambient was "likely what lights the vault". It is not, and the measurement is unambiguous: on
    # cam04 at 1280x720 with the round-11 rig and a physical bake, turning raytracing ON in THIS preset moved the
    # coffer field 0.218 -> 0.218 and the soffit E 0.084 -> 0.089. Nothing. So raytracing STAYS OFF here, which is
    # what this preset is for (fast navigation); apply_preview_eevee keeps it on because the QA previews need
    # screen-space reflections in the lagoon.
    e.use_raytracing = False
    e.use_fast_gi = False
    e.use_volumetric_shadows = False
    e.volumetric_tile_size = "16"
    e.volumetric_samples = 16
    e.use_overscan = False
    # ROUND 11, and this is the actual QA-04-12 answer: 0.05 culls the eight vault emitters wherever their estimated
    # contribution is small, which is exactly the coffered dome. Dropping the threshold to the preview preset's 0.01
    # is what lets the viewport see the vault - not raytracing (see the note above). cam04, 1280x720, round-11 rig:
    #   threshold 0.05, rt off  soffit W 0.315  E 0.084  coffer 0.218
    #   threshold 0.05, rt on   soffit W 0.315  E 0.089  coffer 0.218   <- raytracing buys nothing
    #   threshold 0.01, rt off  soffit W 0.334  E 0.124  coffer 0.319   <- SHIPPED (7.9 s/frame)
    # against a Cycles ground truth of W 0.316 / E 0.532 / coffer 0.387: the coffer lands within 0.07 of Cycles and
    # level with apply_preview_eevee's 0.325, so the ceiling is readable when a viewport user flies under it.
    e.light_threshold = 0.01
    # review fix 3: one try per assignment, and never a silent pass. Sharing a block meant that if "512"/"1024" were
    # not valid enum items on this build, the irradiance pool assignment below it was skipped too and the baked
    # LIGHTPROBE volumes went silently unused - exactly the failure this round spent a day diagnosing.
    try:
        e.shadow_pool_size = "512"      # round 11: 256 overflowed (see apply_preview_eevee)
    except Exception as ex:
        print("[light_presets] viewport shadow_pool_size:", ex)
    try:
        e.gi_irradiance_pool_size = IRRADIANCE_POOL   # must hold the baked LIGHTPROBE volumes (QA-01-9)
    except Exception as ex:
        print("[light_presets] viewport gi_irradiance_pool_size:", ex)
    s.render.use_motion_blur = False
    apply_vault_for_engine("EEVEE")
    apply_shade_for_engine("EEVEE")
    return s


def apply_preview_eevee(scene=None, samples=32):
    """Eevee for the 1280x720 QA previews: raytraced reflections (water!), soft sun shadows, fast GI OFF
    since round 15 (QA-07-5; see the comment on `use_fast_gi` below)."""
    s = scene or bpy.context.scene
    s.render.engine = "BLENDER_EEVEE"
    e = s.eevee
    e.taa_render_samples = samples
    e.taa_samples = 16
    e.use_shadows = True
    e.shadow_ray_count = 2
    e.shadow_step_count = 4
    e.shadow_resolution_scale = 1.0
    e.use_shadow_jitter_viewport = False
    e.use_raytracing = True
    try:
        e.ray_tracing_method = "SCREEN"
        rt = e.ray_tracing_options
        rt.resolution_scale = "2"
        rt.use_denoise = True
        rt.denoise_spatial = True
        rt.denoise_temporal = True
        rt.denoise_bilateral = True
        rt.screen_trace_quality = 0.25
        rt.trace_max_roughness = 0.5
    except Exception as ex:
        print("[light_presets] raytracing options:", ex)
    # ROUND 15 (QA-07-5), SHIPPED OFF. Fast GI is Eevee's screen-traced horizon scan: it decides how much of the
    # world's SH an occluded surface is allowed to see, and inside a 12 m colonnade it decides that the answer is
    # almost none. It -- not the light rig -- is what made cam03 "a black frame". Measured on the round-15 master,
    # same rig, same 32 TAA, same frame (docs/lighting_notes.md 25.4):
    #     fast GI on (60 m)   outer row 0.120 of the sunlit rotunda, frame under lum 10 = 18.5 %, walk hue 193.3
    #     fast GI OFF         outer row 0.189                      , frame under lum 10 =  4.5 %, walk hue  89.1
    # QA-07-5's two tests are >= 0.15 and <= 20 %; the shade fill provably cannot reach that box (raising the SSW
    # lamp 1.0 -> 2.0 moved it 0.115 -> 0.110, and switching the whole rig off moved it 0.115 -> 0.119). It also
    # closes the r14 carry on cam06's roofs (hue 334.5 -> 33.3, QA's window 22-52) and improves the Eevee/Cycles
    # hero agreement (shaded attic -10.6 % -> -3.3 % of the Cycles frame). It costs 11 % of the five-camera pass
    # (197 -> 218 s) and 0.025 of the Eevee-vs-Cycles saturation delta (0.097 -> 0.125 against a 0.10 window).
    e.use_fast_gi = False
    e.fast_gi_method = "GLOBAL_ILLUMINATION"
    e.fast_gi_ray_count = 2
    e.fast_gi_step_count = 8
    e.fast_gi_distance = 60.0
    e.use_volumetric_shadows = False
    e.volumetric_tile_size = "8"
    e.use_overscan = True
    e.overscan_size = 3.0
    e.light_threshold = 0.01
    # ROUND 11: 512 -> 1024. At 512 the QA previews log "Shadow buffer full (2118 / 2048)" on every frame, i.e.
    # Eevee is dropping shadow pages and the preview silently loses shadows it should be casting. The scene has
    # ten shadow-casting lights (sun + disk + eight vault emitters) over 11 M triangles.
    # review fix 3: separate try blocks, exceptions printed (see apply_viewport_eevee).
    try:
        e.shadow_pool_size = "1024"
    except Exception as ex:
        print("[light_presets] preview shadow_pool_size:", ex)
    try:
        e.gi_irradiance_pool_size = IRRADIANCE_POOL   # must hold the baked LIGHTPROBE volumes (QA-01-9)
    except Exception as ex:
        print("[light_presets] preview gi_irradiance_pool_size:", ex)
    s.render.use_motion_blur = False
    apply_vault_for_engine("EEVEE")
    apply_shade_for_engine("EEVEE")
    return s


# ----------------------------------------------------------------------------- rig + look
def _ensure_from_light_blend(kind, name, link=True):
    """Fetch a datablock (worlds/node_groups/collections) by name from assets/lighting.blend if not already present."""
    coll = getattr(bpy.data, kind)
    existing = coll.get(name)
    if existing is not None:
        return existing
    if not LIGHT_BLEND.exists():
        print(f"[light_presets] {LIGHT_BLEND} missing; cannot fetch {kind}/{name}")
        return None
    with bpy.data.libraries.load(str(LIGHT_BLEND), link=link) as (src, dst):
        names = getattr(src, kind)
        if name in names:
            setattr(dst, kind, [name])
    return coll.get(name)


def build_scene_compositor(scene, group, name="COMP_scene_golden_hour"):
    """A LOCAL scene-level compositor tree: Render Layers (this scene) -> COMP_golden_hour group -> output.
    Built per scene on purpose: a linked scene tree would carry a Render Layers node bound to lighting.blend's scene."""
    scene.view_layers[0].use_pass_mist = True
    scene.view_layers[0].use_pass_z = True
    old = bpy.data.node_groups.get(name)
    if old is not None and old.library is None:
        bpy.data.node_groups.remove(old)
    st = bpy.data.node_groups.new(name, "CompositorNodeTree")
    st.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl = st.nodes.new("CompositorNodeRLayers"); rl.location = (-400, 0); rl.scene = scene; rl.layer = scene.view_layers[0].name
    grp = st.nodes.new("CompositorNodeGroup"); grp.location = (0, 0); grp.node_tree = group; grp.name = grp.label = group.name
    out = st.nodes.new("NodeGroupOutput"); out.location = (400, 0)
    for sock in ("Image", "Mist", "Depth"):
        if sock in rl.outputs:
            st.links.new(rl.outputs[sock], grp.inputs[sock])
        else:
            print(f"[light_presets] WARNING render layer output {sock} missing")
    st.links.new(grp.outputs["Image"], out.inputs["Image"])
    scene.compositing_node_group = st
    scene.render.use_compositing = True
    try:
        scene.render.compositor_device = "GPU"
    except Exception:
        pass
    return st


def apply_look(scene=None, exposure=None, link=True):
    """AgX + look + exposure from LIGHT_sun's calibration, passes for the compositor, and COMP_golden_hour wired in."""
    s = scene or bpy.context.scene
    common.setup_scene(s)
    s.view_settings.view_transform = "AgX"
    s.view_settings.look = LOOK
    s.view_settings.gamma = 1.0
    sun = bpy.data.objects.get("LIGHT_sun")
    if exposure is None:
        exposure = float(sun["exposure_ev"]) if sun is not None and "exposure_ev" in sun.keys() else -4.0
    s.view_settings.exposure = exposure
    vl = s.view_layers[0]
    vl.use_pass_mist = True
    vl.use_pass_z = True
    group = _ensure_from_light_blend("node_groups", "COMP_golden_hour", link=link)
    if group is not None:
        build_scene_compositor(s, group)
    return exposure


def reload_rig(scene=None, link=False):
    """Swap the rig in an ALREADY ASSEMBLED scene (master.blend) for the current assets/lighting.blend, so a rig change
    can be tested without a full build_master run. Removes the local LIGHT collection, its objects, the world and the
    compositor group, then re-appends. build_master.py is unaffected; the lead still rebuilds master normally."""
    s = scene or bpy.context.scene
    for name in ("LIGHT",):
        c = bpy.data.collections.get(name)
        if c is not None and c.library is None:
            for ob in list(c.all_objects):
                bpy.data.objects.remove(ob, do_unlink=True)
            bpy.data.collections.remove(c)
    for coll, names in ((bpy.data.worlds, ("WORLD_golden_hour",)),
                        (bpy.data.node_groups, ("COMP_golden_hour", "COMP_scene_golden_hour"))):
        for n in names:
            d = coll.get(n)
            if d is not None and d.library is None:
                coll.remove(d)
    for ob in list(bpy.data.objects):          # stale probes from an earlier rig
        if ob.type == "LIGHT_PROBE":
            bpy.data.objects.remove(ob, do_unlink=True)
    bpy.ops.outliner.orphans_purge(do_recursive=True)
    return apply_rig(s, link=link)


def apply_rig(scene=None, link=True):
    """Link LIGHT (collection) + WORLD_golden_hour from assets/lighting.blend into the scene and apply the look."""
    s = scene or bpy.context.scene
    coll = common.link_collection(LIGHT_BLEND, "LIGHT", link=link, parent=s.collection)
    world = _ensure_from_light_blend("worlds", "WORLD_golden_hour", link=link)
    if world is not None:
        s.world = world
    exposure = apply_look(s, link=link)
    print(f"[light_presets] rig applied: collection {coll.name if coll else None}, world {world.name if world else None}, exposure {exposure:.2f} EV")
    return coll, world


# ----------------------------------------------------------------------------- timing test
def _time_render(scene, path, res):
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(path)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    return time.time() - t


def timing_test(samples_list=(256, 768), res=(1280, 720)):
    """Render the placeholder hero with each preset and extrapolate Cycles to 3840x2160 (9x the pixels)."""
    bpy.ops.wm.read_homefile(use_empty=True)
    common.wipe_scene()
    s = bpy.context.scene
    common.link_collection(common.ASSETS / "placeholder_blockout.blend", "PLACEHOLDER", link=True)
    for name in ("PLACEHOLDER_LIGHT",):
        c = bpy.data.collections.get(name)
        if c:
            c.hide_render = True
    apply_rig(s)
    cams = common.qa_cameras(s)
    s.camera = [c for c in cams if "01_lagoon_hero" in c.name][0]
    out = common.RENDERS / "previews" / "lighting" / "timing"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    apply_preview_eevee(s)
    t = _time_render(s, out / "eevee_preview_1280.png", res)
    t2 = _time_render(s, out / "eevee_preview_1280_b.png", res)     # second run = without shader compile
    rows.append(dict(preset="preview_eevee", res=res, samples=s.eevee.taa_render_samples, seconds=t, seconds_warm=t2))
    apply_viewport_eevee(s)
    t = _time_render(s, out / "eevee_viewport_1280.png", res)
    rows.append(dict(preset="viewport_eevee", res=res, samples=s.eevee.taa_render_samples, seconds=t))
    for n in samples_list:
        apply_final_cycles(s, samples=n)
        t = _time_render(s, out / f"cycles_final_{n}_1280.png", res)
        est4k = t * (3840 * 2160) / (res[0] * res[1])
        rows.append(dict(preset="final_cycles", res=res, samples=n, seconds=t, est_4k_seconds=est4k, est_4k_minutes=est4k / 60))
    (out / "timing.json").write_text(json.dumps(rows, indent=1))
    for r in rows:
        print("[light_presets] timing:", r)
    return rows


if __name__ == "__main__":
    args = common.script_args()
    if "--time" in args:
        samples = [int(args[args.index("--samples") + 1])] if "--samples" in args else [256, 768]
        timing_test(samples)
