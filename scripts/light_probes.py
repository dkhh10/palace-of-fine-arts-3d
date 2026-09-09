"""Eevee Next light probe volumes (irradiance) for the rotunda interior and the colonnade vaults.
Lighting & Rendering specialist. Fixes QA-01-9 (rotunda ceiling 4x too dark in Eevee: no bounce, no probes).

Two halves, because a probe bake needs GEOMETRY and assets/lighting.blend has none:

 1. `ensure_probes(scene)` creates the LIGHT_PROBE objects inside the LIGHT collection. `light_build.py` calls it, so
    the probes live in assets/lighting.blend and are appended into master.blend with the rest of the rig. UNBAKED.
 2. `bake(scene)` runs the actual irradiance bake. It must run on the assembled scene, so the lead runs this script
    on master.blend AFTER scripts/build_master.py:

        blender --background --python scripts/light_probes.py -- --blend master.blend --bake --save

    The baked cache is stored on the probe objects and saved into master.blend; nothing else in master changes.
    Re-run it whenever the architecture or the sun moves. `--free` clears the caches again.

Why not bake into assets/lighting.blend: the volume would only see an empty world (no rotunda), so every sample would
be plain sky and the coffers would stay dark. A bake is a function of the scene, not of the rig.
"""
import bpy, os, sys, time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

COLLECTION = "LIGHT"

# location / half-extent (the volume spans location +- scale) / grid resolution.
# Rotunda: interior floor z 0, coffered ceiling + dome soffit up to z ~32; outer radius 26.4 m.
# Colonnade: both wings, x -110..104, y -35..51, walkway and vault soffits z -1..15.
PROBES = {
    # QA-02-12, round 08 - TESTED AND REJECTED, recorded so nobody spends the GPU on it again. The Cycles ground
    # truth for this rig reads vault soffit / sky 0.479 where Eevee reads 0.360, while the two engines agree to 2 % on
    # the coffer field. The obvious hypothesis was bake resolution: 2.6 m of vertical spacing puts only 2-3 samples
    # through a barrel vault running from the 17.5 m springing to the 23.75 m crown. Re-baked at (28, 28, 20), i.e.
    # 2.0 x 2.0 x 1.8 m and 2.8x the samples, the soffit moved 0.360 -> 0.359. Not resolution: it is Eevee's
    # irradiance-volume + screen-trace approximation under-lighting a concave soffit that Cycles path-traces properly.
    # Reverted, because the finer grid cost a 128 MB pool and 3x the bake time for nothing.
    "LIGHTPROBE_rotunda": dict(
        location=(0.0, 0.0, 15.0), scale=(27.0, 27.0, 17.0), resolution=(20, 20, 14),
        note="rotunda interior: coffered ceiling, vault soffits, the four great arches"),
    "LIGHTPROBE_colonnade": dict(
        location=(-3.0, 8.0, 6.5), scale=(112.0, 46.0, 8.0), resolution=(48, 20, 6),
        note="both colonnade wings: gallery floor, vault soffits, box interiors"),
}
# Shared LightProbe data settings. capture_world keeps the sky in the bake; the low clamp keeps the sunlit floor from
# firing a single sample into the roof. surfel_density is per metre of the scene surface cache: 1.0 is plenty at this
# scale (a 3 cm ornament recess does not need its own surfel).
PROBE_DATA = dict(bake_samples=1024, capture_world=True, capture_indirect=True, capture_emission=True,
                  surfel_density=2, clamp_direct=0.0, clamp_indirect=10.0,
                  normal_bias=0.05, view_bias=0.02, facing_bias=0.5, dilation_threshold=0.5, dilation_radius=2.0,
                  capture_distance=60.0, influence_distance=1.0, intensity=1.0, validity_threshold=0.4)
IRRADIANCE_POOL = "64"      # MB; the default 16 is not enough for two volumes at these resolutions


def ensure_probes(scene=None, coll=None):
    """Create/refresh the LIGHT_PROBE objects. Idempotent: existing ones are removed and rebuilt."""
    scene = scene or bpy.context.scene
    coll = coll or bpy.data.collections.get(COLLECTION) or scene.collection
    made = []
    for name, cfg in PROBES.items():
        old = bpy.data.objects.get(name)
        if old is not None:
            data = old.data
            bpy.data.objects.remove(old, do_unlink=True)
            if data is not None and data.users == 0:
                bpy.data.lightprobes.remove(data)
        lp = bpy.data.lightprobes.new(name, type="VOLUME")
        for k, v in PROBE_DATA.items():
            try:
                setattr(lp, k, v)
            except Exception as e:
                print(f"[light_probes] {name}: cannot set {k}: {e}")
        lp.resolution_x, lp.resolution_y, lp.resolution_z = cfg["resolution"]
        obj = bpy.data.objects.new(name, lp)
        obj.location = cfg["location"]
        obj.scale = cfg["scale"]
        obj["note"] = cfg["note"]
        obj["bake_where"] = "master.blend, via scripts/light_probes.py --bake (needs geometry)"
        coll.objects.link(obj)
        made.append(obj)
        n = cfg["resolution"][0] * cfg["resolution"][1] * cfg["resolution"][2]
        sp = [2 * cfg["scale"][i] / max(1, cfg["resolution"][i] - 1) for i in range(3)]
        print(f"[light_probes] {name}: {cfg['resolution']} = {n} samples, spacing "
              f"{sp[0]:.1f} x {sp[1]:.1f} x {sp[2]:.1f} m")
    return made


def prepare_scene(scene=None):
    """Eevee settings the baked volumes need (the pool must hold them)."""
    s = scene or bpy.context.scene
    try:
        s.eevee.gi_irradiance_pool_size = IRRADIANCE_POOL
    except Exception as e:
        print("[light_probes] gi_irradiance_pool_size:", e)
    return s


BAKE_WORLD_NAME = "WORLD_bake_lighting_only"


def bake_world(scene=None):
    """ROUND 13 (QA-05-1, Eevee half). Build the world the BAKE must see, or return None if there is nothing to fix.

    Round 12 put the shade fix on DIFFUSE-only world sockets (boost 2.50, a blue tint weighted anti-sun and toward
    the horizon) gated by `Fac = 1 - min(is_camera + is_glossy, 1)`. Measured on a one-sphere scene with no lamps
    (`scripts/light_r13_probe.py`, linear EXR, so every number is a physical ratio):

        Eevee, world spherical harmonics, no probe   ship 3.435/3.443/28.641   camera_boost=1 3.435/3.443/28.641
                                                     split_rays=False 3.435/3.443/28.641
        Eevee, BAKED irradiance volume, bake=ship         4.084/4.355/28.032   <- warmer: R +19 %, G +26 %
        Eevee, BAKED irradiance volume, bake=split_rays=False  3.412/3.365/28.069

    So Eevee's WORLD SH already evaluates the diffuse branch (changing camera_boost moves it by nothing, and the
    unconditional world is bit-identical to it), but the LIGHT PROBE CAPTURE evaluates the world as a CAMERA ray:
    with the shipped world the baked grid holds camera_boost 2.10 and camera_saturation 1.20 and none of the tint.
    Everything inside LIGHTPROBE_rotunda / LIGHTPROBE_colonnade - which is where the hero's shaded stone is - is lit
    from that grid, so the round-12 shade fix was Cycles-only in Eevee.

    The fix is to bake with the SAME sky built `split_rays=False`, i.e. the diffuse branch applied to every ray. It
    is not a look and not a fudge: it makes the capture agree with what Cycles' diffuse rays get, whatever ray class
    Eevee decides the capture is. The parameters are read from the world's own custom properties (written by
    `light_build.build_world`), so a master built from any rig bakes its own rig, and only fall back to
    `light_build`'s constants if a property is missing."""
    s = scene or bpy.context.scene
    w = s.world
    if w is None:
        return None
    try:
        import light_build as lb
        import light_calibrate as cal
    except Exception as e:
        print("[light_probes] cannot import the lighting rig, baking with the scene world as-is:", e)
        return None

    def prop(key, default):
        v = w.get(key)
        return default if v is None else v

    az = prop("sun_azimuth_deg", None)
    el = prop("sun_elevation_deg", None)
    if az is None or el is None:
        print(f"[light_probes] world {w.name!r} carries no sun_azimuth_deg/sun_elevation_deg; "
              f"baking with the scene world as-is")
        return None
    sky = {k: float(prop("sky_" + k, v)) for k, v in lb.SKY.items()}
    tint = prop("sky_diffuse_tint", list(lb.SKY_DIFFUSE_TINT))
    old = bpy.data.worlds.get(BAKE_WORLD_NAME)
    if old:
        bpy.data.worlds.remove(old)
    bw = cal.make_sky_world(
        BAKE_WORLD_NAME, float(az), float(el), sky, sun_disc=False,
        strength=float(prop("sky_strength_lighting", lb.SKY_STRENGTH)),
        diffuse_boost=float(prop("sky_diffuse_boost", lb.SKY_DIFFUSE_BOOST)),
        diffuse_saturation=float(prop("sky_diffuse_saturation", lb.SKY_DIFFUSE_SATURATION)),
        diffuse_hue=float(prop("sky_diffuse_hue", lb.SKY_DIFFUSE_HUE)),
        diffuse_tint=tuple(float(c) for c in tint),
        diffuse_tint_antisun=float(prop("sky_diffuse_tint_antisun", lb.SKY_DIFFUSE_TINT_ANTISUN)),
        diffuse_tint_horizon=float(prop("sky_diffuse_tint_horizon", lb.SKY_DIFFUSE_TINT_HORIZON)),
        split_rays=False)
    bw["baked_from_world"] = w.name
    bw["why"] = ("Eevee evaluates the light-probe capture as a camera ray; this is the same sky with the DIFFUSE "
                 "branch applied to every ray (light_probes.bake_world, round 13)")
    print(f"[light_probes] bake world {BAKE_WORLD_NAME}: diffuse branch of {w.name!r} on every ray "
          f"(strength {float(prop('sky_strength_lighting', lb.SKY_STRENGTH)):.3f} x boost "
          f"{float(prop('sky_diffuse_boost', lb.SKY_DIFFUSE_BOOST)):.2f}, tint "
          f"{tuple(round(float(c), 2) for c in tint)}, antisun "
          f"{float(prop('sky_diffuse_tint_antisun', lb.SKY_DIFFUSE_TINT_ANTISUN)):.2f}, horizon "
          f"{float(prop('sky_diffuse_tint_horizon', lb.SKY_DIFFUSE_TINT_HORIZON)):.2f})")
    return bw


def bake(scene=None, free_first=True, physical_vault=True, lighting_world=True):
    """Bake every light probe in the CURRENT scene. Needs the real geometry -> run this on master.blend.

    ROUND 11 / QA-04-1. The bake is a function of the rig that is LIVE when it runs, and `build_master.py` now ends
    with `light_presets.apply_viewport_eevee`, which applies the Eevee-only vault override (x8 energy, 13 m cutoff).
    `lead_build.sh` then runs this script, so the irradiance volumes were being baked with the vault emitters CUT OFF
    at 13 m - and the central coffered dome is 20.7 m from them. That starved the coffers in the baked indirect term
    itself, not only in the direct one: QA measured the Eevee coffer field at 0.035 of the frame's own sky against
    Cycles' 0.261, where round 10's probe (baked before the review fix, i.e. on an uncut rig) had read 0.255.
    Measured on the lead's master, cam04, Eevee 1280x720, everything else identical:
        bake taken with the EEVEE override (as shipped in round 10) -> coffer / own sky 0.035
        bake taken with the PHYSICAL rig (this fix)                 -> see docs/lighting_notes.md section 20
    A light probe volume is supposed to store the scene's real indirect light, so baking a render-time engine hack
    into it was simply a bug.

    ROUND-11 REVIEW FIXES 1 and 2. Both the vault rig and the render engine are restored in a `finally`, and the rig
    that is restored is decided from the engine the file arrived with, captured BEFORE anything is forced:
      * the probe-less early-out used to sit after the vault switch, so a master with no LIGHT_PROBE objects was left
        holding the physical energies and `--save` wrote them as the saved "Eevee" state;
      * `restore` used to be read after `s.render.engine` had already been forced to BLENDER_EEVEE, so `--bake --save`
        on a Cycles-engine blend saved an Eevee engine with physical vault energies.
    Whatever the file arrived as, it leaves as."""
    s = prepare_scene(scene)
    eng0 = s.render.engine                      # review fix 2: the engine the file ARRIVED with, before anything forces it
    probes = [o for o in s.objects if o.type == "LIGHT_PROBE"]
    if not probes:                              # review fix 1: bail out BEFORE touching the rig
        print("[light_probes] no LIGHT_PROBE objects in the scene; nothing to bake")
        return []
    switched = False
    world0 = s.world                            # round 13: restored in the same finally as the engine and the vault
    if physical_vault:
        try:
            import light_presets as lp
            lp.apply_vault_for_engine("CYCLES")
            lp.apply_shade_for_engine("CYCLES")   # round 13: the Eevee shade fill is an engine hack, not real light
            switched = True
            print("[light_probes] baking with the PHYSICAL vault rig (QA-04-1): the probe volumes must hold the "
                  "scene's real indirect light, not the Eevee render-time override")
        except Exception as e:
            print("[light_probes] could not force the physical vault rig:", e)
    bw = bake_world(s) if lighting_world else None
    if bw is not None:
        s.world = bw
    try:
        if s.render.engine != "BLENDER_EEVEE":
            s.render.engine = "BLENDER_EEVEE"   # the bake operator only exists for Eevee
        for p in probes:                        # probes must be visible to be baked
            p.hide_viewport = False
            p.hide_render = False
        if free_first:
            try:
                bpy.ops.object.lightprobe_cache_free(subset="ALL")
            except Exception as e:
                print("[light_probes] cache_free:", e)
        t = time.time()
        res = bpy.ops.object.lightprobe_cache_bake(subset="ALL")
        print(f"[light_probes] bake {res} in {time.time() - t:.1f}s for {[p.name for p in probes]}")
        for p in probes:
            print(f"[light_probes]   {p.name}: baked "
                  f"(grid {p.data.resolution_x}x{p.data.resolution_y}x{p.data.resolution_z})")
    finally:
        s.render.engine = eng0
        s.world = world0                        # round 13: the bake-only world never survives into the saved file
        if bw is not None and bw.users == 0:
            bpy.data.worlds.remove(bw)
        if switched:
            try:
                import light_presets as lp
                rig = "EEVEE" if eng0.endswith("EEVEE") else "CYCLES"
                lp.apply_vault_for_engine(rig)
                lp.apply_shade_for_engine(rig)
            except Exception as e:
                print("[light_probes] could not restore the vault rig:", e)
        print(f"[light_probes] restored: engine {eng0}, world {world0.name if world0 else None}, vault rig "
              f"{'EEVEE override' if eng0.endswith('EEVEE') else 'physical'}")
    return probes


def free(scene=None):
    try:
        bpy.ops.object.lightprobe_cache_free(subset="ALL")
        print("[light_probes] caches freed")
    except Exception as e:
        print("[light_probes] cache_free:", e)


if __name__ == "__main__":
    args = common.script_args()

    def arg(k, d=None):
        return args[args.index(k) + 1] if k in args else d

    blend = arg("--blend")
    if blend:
        bpy.ops.wm.open_mainfile(filepath=str(common.ROOT / blend) if not os.path.isabs(blend) else blend, load_ui=False)
    scene = bpy.context.scene
    if "--ensure" in args:
        coll = bpy.data.collections.get(COLLECTION)
        ensure_probes(scene, coll)
    if "--free" in args:
        free(scene)
    if "--bake" in args:
        bake(scene, lighting_world="--camera-bake" not in args)   # --camera-bake reproduces the round-12 bake
    if "--save" in args:
        path = bpy.data.filepath or str(common.ROOT / "master.blend")
        bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
        print(f"[light_probes] saved {path}")
