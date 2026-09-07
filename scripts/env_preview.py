"""Preview renders for the environment: temp scene = linked ENV + linked ARCH (or the lead's PLACEHOLDER while
architecture.blend does not exist) + a placeholder golden-hour sun (az 118.5, el 7.4) + physically based sky.

    blender --background --python scripts/env_preview.py [-- --cams 01,02,06 --samples 16 --tag x --cycles]

Writes renders/previews/environment/<timestamp>_<cam>[_tag].png (Eevee, 1280x720 by default).
"""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

SUN_AZ, SUN_EL = 118.5, 7.4


def build_scene(local=False, lod=0):
    """local=True opens environment.blend itself (objects editable) so any LOD can be rendered: --local --lod=1."""
    if local:
        bpy.ops.wm.open_mainfile(filepath=str(common.ASSET_FILES["ENV"]))
        scene = common.setup_scene()
        for obj in bpy.data.objects:
            if obj.name.startswith("ENV_tree_") and "_LOD" in obj.name and obj.name.split("_")[-2].isdigit():
                obj.hide_render = not obj.name.endswith(f"_LOD{lod}")
        env = bpy.data.collections.get("ENV")
    else:
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
                if obj.name.startswith(("PH_ground", "PH_lagoon", "PH_b302")):   # ENV owns ground, water, hall
                    bpy.data.objects.remove(obj, do_unlink=True)
    # render one tree LOD only (object flags already do this for LOD0; excluding the other collections as well)
    def _exclude(layer_coll):
        for child in layer_coll.children:
            n = child.name
            if n.startswith("ENV_tree_instances_LOD"):
                child.exclude = not n.endswith(f"LOD{lod}")
            _exclude(child)
    _exclude(scene.view_layers[0].layer_collection)
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


def render(tag="", cams=None, samples=16, engine="EEVEE", local=False, lod=0, master=False):
    """master=True renders the lead's master.blend (full scene: ARCH + ORN + ENV + LIGHT rig and look) into
    renders/previews/environment/ - the ENV file must have been rebuilt AND build_master.py run first."""
    if master:
        mp = common.ROOT / "master.blend"
        if not mp.exists():
            raise SystemExit("master.blend missing: run scripts/build_master.py first")
        bpy.ops.wm.open_mainfile(filepath=str(mp))
        scene = bpy.context.scene
        try:
            import light_presets
            if engine.upper() == "CYCLES":
                light_presets.apply_final_cycles(scene)
            else:
                light_presets.apply_preview_eevee(scene)
        except Exception as e:
            print("[env_preview] light_presets not applied:", e)
        cams_all = [o for o in bpy.data.objects if o.type == "CAMERA" and o.name.startswith("CAM_qa_")]
        if cams:
            cams_all = [c for c in cams_all if any(k in c.name for k in cams)]
        scene.render.resolution_x, scene.render.resolution_y = 1280, 720
        scene.render.resolution_percentage = 100
        if engine.upper() == "CYCLES":
            scene.render.engine = "CYCLES"
            scene.cycles.samples = 64
        else:
            scene.render.engine = "BLENDER_EEVEE"
            scene.eevee.taa_render_samples = samples
        out_dir = common.RENDERS / "previews" / "environment"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = common.timestamp()
        outs = []
        for cam in sorted(cams_all, key=lambda c: c.name):
            scene.camera = cam
            fp = out_dir / f"{ts}_{cam.name.replace('CAM_qa_', '')}{('_' + tag) if tag else ''}_master.png"
            scene.render.filepath = str(fp)
            bpy.ops.render.render(write_still=True)
            print("[env_preview] rendered", fp)
            outs.append(fp)
        return outs
    build_scene(local=local, lod=lod)
    return common.render_previews("environment", cameras=cams, samples=samples, tag=tag, engine=engine, cycles_samples=48)


EXTRA_CAMS = [   # diagnostic views (not QA cameras): name, location, target, lens
    ("CAM_env_hall_from_colonnade", (6.0, -36.0, 14.0), (-4.0, -80.0, 12.0), 20.0),
    ("CAM_env_north_wing_from_water", (-60.0, 60.0, 2.0), (-50.0, -20.0, 12.0), 28.0),
    ("CAM_env_east_shore_high", (-40.0, 170.0, 25.0), (0.0, 0.0, 15.0), 35.0),
]


def render_extra(tag="extra", samples=12, local=False, lod=0):
    scene = build_scene(local=local, lod=lod)
    common.configure_eevee(scene, samples=samples)
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    outs = []
    ts = common.timestamp()
    for name, loc, target, lens in EXTRA_CAMS:
        cam = bpy.data.cameras.new(name)
        cam.lens = lens
        cam.clip_end = 5000
        co = bpy.data.objects.new(name, cam)
        co.location = loc
        co.rotation_euler = common.lookat_rotation(loc, target)
        scene.collection.objects.link(co)
        scene.camera = co
        out = common.RENDERS / "previews" / "environment" / f"{ts}_{name.replace('CAM_env_', '')}_{tag}.png"
        scene.render.filepath = str(out)
        bpy.ops.render.render(write_still=True)
        print("[env_preview] wrote", out)
        outs.append(out)
    return outs


def render_topdown(extent=320.0, centre=(0.0, 20.0), res=1024, tag="topdown", local=False, lod=0):
    """Orthographic plan view (image up = north = -X, image right = east = +Y) for checking the planting plan
    against reference/plans/satellite_z18.png (0.472 m/px, rotunda at px 718.6, 633.8)."""
    scene = build_scene(local=local, lod=lod)
    cam = bpy.data.cameras.new("CAM_topdown")
    cam.type = "ORTHO"
    cam.ortho_scale = extent
    cam.clip_end = 2000
    co = bpy.data.objects.new("CAM_topdown", cam)
    co.location = (centre[0], centre[1], 400.0)
    co.rotation_euler = (0.0, 0.0, math.pi / 2)
    scene.collection.objects.link(co)
    scene.camera = co
    common.configure_eevee(scene, samples=8)
    scene.render.resolution_x = scene.render.resolution_y = res
    out = common.RENDERS / "previews" / "environment" / f"{common.timestamp()}_{tag}.png"
    scene.render.filepath = str(out)
    bpy.ops.render.render(write_still=True)
    print("[env_preview] wrote", out)
    return out


if __name__ == "__main__":
    args = common.script_args()
    cams = None
    samples = 16
    tag = ""
    engine = "EEVEE"
    local = "--local" in args
    master = "--master" in args
    lod = 0
    for a in args:
        if a.startswith("--lod="):
            lod = int(a.split("=")[1])
            local = True
    for i, a in enumerate(args):
        if a == "--cams":
            cams = args[i + 1].split(",")
        elif a == "--samples":
            samples = int(args[i + 1])
        elif a == "--tag":
            tag = args[i + 1]
        elif a == "--cycles":
            engine = "CYCLES"
    if "--topdown" in args:
        render_topdown(local=local, lod=lod)
    elif "--extra" in args:
        render_extra(tag=tag or "extra", local=local, lod=lod)
    else:
        outs = render(tag=tag, cams=cams, samples=samples, engine=engine, local=local, lod=lod, master=master)
        print("[env_preview] wrote:", *[str(o) for o in outs], sep="\n  ")
