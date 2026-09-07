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


def bake(scene=None, free_first=True):
    """Bake every light probe in the CURRENT scene. Needs the real geometry -> run this on master.blend."""
    s = prepare_scene(scene)
    probes = [o for o in s.objects if o.type == "LIGHT_PROBE"]
    if not probes:
        print("[light_probes] no LIGHT_PROBE objects in the scene; nothing to bake")
        return []
    if s.render.engine != "BLENDER_EEVEE":
        s.render.engine = "BLENDER_EEVEE"
    for p in probes:                       # probes must be visible to be baked
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
        cache = getattr(p.data, "is_runtime_data", None)
        print(f"[light_probes]   {p.name}: baked (grid {p.data.resolution_x}x{p.data.resolution_y}x{p.data.resolution_z})")
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
        bake(scene)
    if "--save" in args:
        path = bpy.data.filepath or str(common.ROOT / "master.blend")
        bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
        print(f"[light_probes] saved {path}")
