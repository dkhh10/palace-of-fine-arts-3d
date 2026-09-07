"""Preview renders for the environment: temp scene = linked ENV + linked ARCH (or the lead's PLACEHOLDER while
architecture.blend does not exist) + a placeholder golden-hour sun (az 118.5, el 7.4) + physically based sky.

    blender --background --python scripts/env_preview.py [-- --cams 01,02,06 --samples 16 --tag x --cycles]

Writes renders/previews/environment/<timestamp>_<cam>[_tag].png (Eevee, 1280x720 by default).
"""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

SUN_AZ, SUN_EL = 118.5, 7.4


def build_scene():
    bpy.ops.wm.read_homefile(use_empty=True)
    common.wipe_scene()
    scene = common.setup_scene()
    env = common.link_collection(common.ASSET_FILES["ENV"], "ENV", link=True)
    if env is None:
        raise SystemExit("assets/environment.blend has no ENV collection - run env_build.py first")
    arch = common.ASSET_FILES["ARCH"]
    if arch.exists():
        common.link_collection(arch, "ARCH", link=True)
    else:
        # append (not link) so the placeholder's own ground/water can be dropped: ENV provides those now
        ph = common.link_collection(common.ASSETS / "placeholder_blockout.blend", "PLACEHOLDER", link=False)
        if ph:
            for obj in list(ph.all_objects):
                if obj.name.startswith(("PH_ground", "PH_lagoon")):
                    bpy.data.objects.remove(obj, do_unlink=True)
    # sun
    lc = common.rebuild_collection("PREVIEW_LIGHT")
    sun = bpy.data.lights.new("PREVIEW_sun", "SUN")
    sun.energy = 4.0
    sun.angle = 0.0093
    try:
        sun.use_temperature = True
        sun.temperature = 3600.0
    except Exception:
        sun.color = (1.0, 0.70, 0.42)
    so = bpy.data.objects.new("PREVIEW_sun", sun)
    lc.objects.link(so)
    common.aim_sun(so, SUN_AZ, SUN_EL)
    # sky: MULTIPLE_SCATTERING, no disc (the sun light provides the direct light)
    world = bpy.data.worlds.new("WORLD_preview")
    world.use_nodes = True
    nt = world.node_tree
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_disc = False
    sky.sun_elevation = math.radians(SUN_EL)
    sky.sun_rotation = math.radians(sky_rotation_for_azimuth(SUN_AZ))
    sky.altitude = 5.0
    sky.air_density = 1.0
    sky.aerosol_density = 1.6      # hazy bay morning
    bg = nt.nodes.get("Background")
    nt.links.new(sky.outputs[0], bg.inputs[0])
    bg.inputs[1].default_value = 0.35
    scene.world = world
    scene.view_settings.exposure = -0.8
    try:
        scene.view_settings.look = "AgX - Base Contrast"
    except Exception:
        pass
    return scene


def sky_rotation_for_azimuth(az_deg):
    """Verified empirically (Blender 5.2.1, MULTIPLE_SCATTERING, sun disc renders): sun_rotation = 0 puts the sun
    toward world +Y (= east, compass 90 deg) and sun_rotation = +90 deg puts it toward +X (= south, 180 deg).
    So rotation = az - 90 (degrees) places the sun at compass azimuth az in our world (north = -X)."""
    return az_deg - 90.0


def render(tag="", cams=None, samples=16, engine="EEVEE"):
    build_scene()
    return common.render_previews("environment", cameras=cams, samples=samples, tag=tag, engine=engine, cycles_samples=48)


if __name__ == "__main__":
    args = common.script_args()
    cams = None
    samples = 16
    tag = ""
    engine = "EEVEE"
    for i, a in enumerate(args):
        if a == "--cams":
            cams = args[i + 1].split(",")
        elif a == "--samples":
            samples = int(args[i + 1])
        elif a == "--tag":
            tag = args[i + 1]
        elif a == "--cycles":
            engine = "CYCLES"
    outs = render(tag=tag, cams=cams, samples=samples, engine=engine)
    print("[env_preview] wrote:", *[str(o) for o in outs], sep="\n  ")
