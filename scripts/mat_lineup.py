"""Materials lineup / QA renders.

    blender --background --python scripts/mat_lineup.py [-- --engine eevee|cycles|both] [--cams wall,column,...] [--hero] [--no-hero] [--spp 128] [--quick]

Opens assets/materials.blend (built by mat_build.py), lights the MAT_test objects with the golden-hour sun (az 118.5,
el 7.4) and a physically scaled sky, and renders fixed close-up cameras with Eevee and Cycles into
renders/previews/materials/<timestamp>_<cam>_<engine>.png. With --hero it also appends the lead's placeholder blockout
into a second scene, swaps its placeholder materials for the library ones BY NAME, and renders CAM_qa_01 / CAM_qa_05.
Nothing is saved back into materials.blend.
"""
import bpy, sys, os, math, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from mathutils import Vector

args = common.script_args()


def arg(name, default=None):
    if name in args:
        i = args.index(name)
        return args[i + 1] if i + 1 < len(args) else True
    return default


ENGINE = str(arg("--engine", "both")).lower()
DEBUG = arg("--debug", None)          # e.g. --debug "Streak Mask": render that PFA_concrete output as emission
TS = arg("--ts", None)
NEUTRAL = "--neutral" in args      # lab light: white sun, irradiance pi, black world, Standard view -> pixels = albedo
RIG = "--rig" in args              # use the lighting agent's rig (assets/lighting.blend: LIGHT + WORLD_golden_hour + look)
ENV = "--env" in args              # append ENV (trees, terrain, water) into the hero scene, materials remapped by name
EEVEE_PRESET = "--eevee-preset" in args   # use light_presets.apply_preview_eevee instead of common.configure_eevee
NO_REFRACTION = "--no-refraction" in args # A/B: water without raytraced transmission in Eevee
CPU = "--cpu" in args                     # Cycles on the CPU (fallback when Metal is wedged)
CAMS = arg("--cams", None)
CAMS = CAMS.split(",") if isinstance(CAMS, str) else None
HERO = "--no-hero" not in args
SPP = int(arg("--spp", 128))
EV = float(arg("--ev", 0.0))         # diagnostic: offset the view exposure (to quantify what lighting still owes)
QUICK = "--quick" in args
RES = (1280, 720)

LIB = common.ASSETS / "materials.blend"
if ENGINE == "both":
    # one Blender process per engine: Cycles/Metal leaks GPU memory across many renders in one session
    import subprocess
    ts = common.timestamp()
    for eng in ("eevee", "cycles"):
        cmd = [common.BLENDER_BIN, "--background", "--python", os.path.abspath(__file__), "--"] + \
              [a for a in args if a not in ("--engine", "both")] + ["--engine", eng, "--ts", ts]
        print("[mat_lineup] spawning", eng)
        subprocess.call(cmd)
    sys.exit(0)
bpy.ops.wm.open_mainfile(filepath=str(LIB))
if isinstance(DEBUG, str):
    for m in bpy.data.materials:
        if not m.node_tree:
            continue
        nt = m.node_tree
        grp = [n for n in nt.nodes if n.type == "GROUP" and n.node_tree and n.node_tree.name == "PFA_concrete"]
        outn = [n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"]
        if grp and outn and DEBUG in grp[0].outputs:
            em = nt.nodes.new("ShaderNodeEmission")
            nt.links.new(grp[0].outputs[DEBUG], em.inputs["Color"])
            em.inputs["Strength"].default_value = 1.0
            nt.links.new(em.outputs[0], outn[0].inputs["Surface"])
    print(f"[mat_lineup] DEBUG mode: emitting '{DEBUG}'")
scene = bpy.context.scene
scene.name = "MAT_LINEUP"
common.setup_scene(scene)
scene.view_settings.look = "AgX - Base Contrast"

SUN_AZ, SUN_EL = 118.5, 7.4


def make_light_rig(sc, name_suffix=""):
    lc = common.rebuild_collection("MAT_lineup_light" + name_suffix, parent=sc.collection)
    sun = bpy.data.lights.new("MAT_lineup_sun" + name_suffix, "SUN")
    sun.energy = 3.0
    sun.color = (1.0, 0.72, 0.45)
    sun.angle = 0.0093
    so = bpy.data.objects.new(sun.name, sun)
    lc.objects.link(so)
    common.aim_sun(so, SUN_AZ, SUN_EL)
    if NEUTRAL:
        sun.energy = math.pi
        sun.color = (1.0, 1.0, 1.0)
        common.aim_sun(so, 90.0, 20.0)      # square-ish onto the +Y faces
    w = bpy.data.worlds.get("WORLD_mat_lineup")
    if w is None:
        w = bpy.data.worlds.new("WORLD_mat_lineup")
        w.use_nodes = True
        nt = w.node_tree
        sky = nt.nodes.new("ShaderNodeTexSky")
        sky.sky_type = "MULTIPLE_SCATTERING"
        sky.sun_elevation = math.radians(SUN_EL)
        sky.sun_rotation = math.radians(SUN_AZ)
        sky.sun_disc = False
        sky.altitude = 5.0
        bg = nt.nodes.get("Background")
        nt.links.new(sky.outputs[0], bg.inputs[0])
        bg.inputs[1].default_value = 0.6
    sc.world = w
    sc.view_settings.exposure = -1.0
    if isinstance(DEBUG, str) or NEUTRAL:
        sc.view_settings.view_transform = "Standard"
        sc.view_settings.look = "None"
        sc.view_settings.exposure = 0.0
        w.node_tree.nodes["Background"].inputs[1].default_value = 0.0
    return so


def add_cam(sc, name, loc, target, lens=31.0, shift_y=0.0):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens; cd.sensor_width = 36.0; cd.sensor_fit = "HORIZONTAL"; cd.clip_end = 5000.0; cd.shift_y = shift_y
    o = bpy.data.objects.new(name, cd)
    o.location = loc
    o.rotation_euler = common.lookat_rotation(loc, target)
    sc.collection.objects.link(o)
    return o


GZ = -2.0


def light(sc, suffix=""):
    if RIG and (common.ASSETS / "lighting.blend").exists():
        import light_presets as lp
        lp.apply_rig(sc, link=True)
        if NEUTRAL or isinstance(DEBUG, str):
            sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"; sc.view_settings.exposure = 0.0
        return None
    return make_light_rig(sc, suffix)


light(scene)
lineup_cams = [
    add_cam(scene, "CAM_mat_wall", (-3.5, 3.6, 9.55), (-3.5, 0.0, 9.5)),
    add_cam(scene, "CAM_mat_column", (-3.5, 5.4, GZ + 2.4), (-3.5, 0.0, GZ + 2.2)),
    add_cam(scene, "CAM_mat_waterline", (1.5, 6.2, GZ + 1.6), (1.5, 0.3, GZ + 0.9)),
    add_cam(scene, "CAM_mat_ornament", (4.9, 3.8, GZ + 1.3), (4.9, 0.0, GZ + 1.0)),
    add_cam(scene, "CAM_mat_colonnade", (7.5, 5.5, GZ + 1.8), (7.5, 0.0, GZ + 1.5)),
    add_cam(scene, "CAM_mat_dome_close", (0.0, 81.5, GZ + 1.6), (0.0, 76.0, GZ + 1.4)),
    add_cam(scene, "CAM_mat_dome_wide", (0.0, 98.0, GZ + 8.0), (0.0, 60.0, GZ + 3.5)),
    add_cam(scene, "CAM_mat_ground", (-9.5, 12.0, GZ + 4.0), (-10.0, 6.0, GZ)),
    add_cam(scene, "CAM_mat_foliage", (9.7, 12.0, GZ + 1.3), (9.7, 8.0, GZ + 0.7), lens=26.0),
    add_cam(scene, "CAM_mat_foliage_far", (9.7, 150.0, GZ + 8.0), (9.7, 30.0, GZ + 1.0), lens=80.0),
    add_cam(scene, "CAM_mat_misc", (-16.5, 9.5, GZ + 2.2), (-16.5, 0.0, GZ + 1.6), lens=20.0),
    add_cam(scene, "CAM_mat_lineup", (0.0, 19.0, GZ + 5.0), (0.0, 0.0, GZ + 2.5), lens=22.0),
    # per-instance ornament variation, judged at 60 m (six capital proxies with different `instance_seed`)
    add_cam(scene, "CAM_mat_ornament_far", (24.9, 80.0, GZ + 2.6), (24.9, 20.0, GZ + 1.55), lens=200.0),
]

# --------------------------------------------------------------------------- hero scene: placeholder blockout with the library materials
hero_cams = []
if HERO:
    hero = bpy.data.scenes.new("MAT_HERO")
    common.setup_scene(hero)
    hero.view_settings.look = "AgX - Base Contrast"
    bl = common.ASSETS / "placeholder_blockout.blend"
    with bpy.data.libraries.load(str(bl), link=False) as (src, dst):
        dst.collections = ["PLACEHOLDER"]
    ph = [c for c in bpy.data.collections if c.name.startswith("PLACEHOLDER") and c.library is None][-1]
    hero.collection.children.link(ph)
    if ENV and common.ASSET_FILES["ENV"].exists():
        with bpy.data.libraries.load(str(common.ASSET_FILES["ENV"]), link=False) as (src, dst):
            dst.collections = ["ENV"]
        envc = [c for c in bpy.data.collections if c.name.startswith("ENV") and c.library is None and "." not in c.name]
        for c in envc:
            if c.name == "ENV":
                hero.collection.children.link(c)
        # ENV brings its own lagoon/terrain: hide the placeholder's ground and water
        for o in ph.objects:
            if o.name.startswith(("PH_ground", "PH_lagoon_water")):
                o.hide_render = True
        print("[mat_lineup] ENV appended")
    # placeholder materials came in as MAT_x.001 (the library names already exist): remap them by name
    swapped = 0
    for m in list(bpy.data.materials):
        if m.get("placeholder") or (m.name.startswith("MAT_") and ".0" in m.name):
            base = m.name.split(".")[0]
            lib = bpy.data.materials.get(base)
            if lib is not None and lib is not m:
                m.user_remap(lib)
                bpy.data.materials.remove(m)
                swapped += 1
    print(f"[mat_lineup] remapped {swapped} placeholder materials to library materials")
    # a muddy lagoon bed so transmission rays through the (single-face) placeholder water hit something
    bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 40, common.WATER_Z - 1.5))
    bed = bpy.context.object
    bed.name = "MAT_hero_lagoon_bed"
    for c in list(bed.users_collection):
        c.objects.unlink(bed)
    hero.collection.objects.link(bed)
    common.assign_material(bed, bpy.data.materials["MAT_soil"])
    # the placeholder's flat water gets a bit of colour variation from the bed; ok for a materials test
    light(hero, "_hero")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import qa_cameras as qc
    old = bpy.context.scene
    # qa_cameras.ensure uses bpy.context.scene; build cameras then move them into the hero scene
    cams = qc.ensure(old)
    for c in cams:
        for col in list(c.users_collection):
            col.objects.unlink(c)
        hero.collection.objects.link(c)
    hero.camera = cams[0]
    hero_cams = [c for c in cams if c.name.endswith("01_lagoon_hero") or c.name.endswith("05_south_lawn")]
    if ENV:
        hero_cams = [c for c in cams if any(k in c.name for k in ("01_lagoon_hero", "02_lagoon", "05_south_lawn"))]

# --------------------------------------------------------------------------- render
out_dir = common.RENDERS / "previews" / "materials"
out_dir.mkdir(parents=True, exist_ok=True)
ts = TS or common.timestamp()
engines = [ENGINE.upper()]
if NO_REFRACTION:
    w = bpy.data.materials.get("MAT_water_lagoon")
    if w:
        w.use_raytrace_refraction = False
        w.use_screen_refraction = False
if QUICK:
    RES = (960, 540)
    SPP = min(SPP, 48)


def configure(sc, engine):
    if engine == "CYCLES":
        common.configure_cycles(sc, samples=SPP, device="CPU" if CPU else "GPU")
        sc.cycles.denoising_use_gpu = False
        sc.cycles.adaptive_threshold = 0.03
        sc.cycles.max_bounces = 8
        sc.cycles.transmission_bounces = 6
        sc.cycles.volume_bounces = 1
        sc.cycles.volume_step_rate = 2.0
    elif EEVEE_PRESET:
        import light_presets as lp
        lp.apply_preview_eevee(sc, samples=32 if not QUICK else 16)
    else:
        common.configure_eevee(sc, samples=32 if not QUICK else 16)
        sc.eevee.use_raytracing = True
        try:
            sc.eevee.ray_tracing_options.resolution_scale = "1"
            sc.eevee.ray_tracing_options.trace_max_roughness = 0.6
        except Exception:
            pass
        sc.eevee.volumetric_tile_size = "8"
        sc.eevee.volumetric_samples = 32
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.film_transparent = False
    if EV:
        sc.view_settings.exposure += EV


def render(sc, cam, engine, tag):
    sc.camera = cam
    dbg = ("_dbg_" + DEBUG.replace(" ", "").lower()) if isinstance(DEBUG, str) else ("_neutral" if NEUTRAL else "")
    dbg += "_rig" if RIG else ""
    dbg += "_preset" if EEVEE_PRESET else ""
    dbg += "_norefr" if NO_REFRACTION else ""
    dbg += f"_ev{EV:+.1f}" if EV else ""
    fp = out_dir / f"{ts}_{tag}{dbg}_{engine.lower()}.png"
    sc.render.filepath = str(fp)
    t0 = time.time()
    bpy.ops.render.render(write_still=True, scene=sc.name)
    print(f"[mat_lineup] {fp.name} {time.time() - t0:.1f}s")
    return fp


outputs = []
for eng in engines:
    configure(scene, eng)
    for cam in lineup_cams:
        short = cam.name.replace("CAM_mat_", "")
        if CAMS and short not in CAMS:
            continue
        outputs.append(render(scene, cam, eng, short))
    if HERO and hero_cams:
        configure(hero, eng)
        for cam in hero_cams:
            short = cam.name.replace("CAM_qa_", "hero_")
            if CAMS and short not in CAMS and "hero" not in CAMS:
                continue
            outputs.append(render(hero, cam, eng, short))
print("[mat_lineup] outputs:")
for o in outputs:
    print("  ", o)
