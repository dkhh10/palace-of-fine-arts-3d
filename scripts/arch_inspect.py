"""Ad-hoc inspection renders of assets/architecture.blend (ARCH QA helper; nothing is saved).

    blender -b assets/architecture.blend --python scripts/arch_inspect.py -- --cam X,Y,Z --target X,Y,Z [--lens 24]
        [--lod 0|1|2] [--out renders/previews/architecture/inspect_name.png] [--sun az,el] [--res 1280x720] [--cycles]
"""
import bpy, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

args = common.script_args()


def opt(name, default=None):
    return args[args.index(name) + 1] if name in args else default


cam = tuple(float(v) for v in opt("--cam", "-40,60,8").split(","))
tgt = tuple(float(v) for v in opt("--target", "0,0,20").split(","))
lens = float(opt("--lens", "24"))
lod = opt("--lod", "0")
out = opt("--out", str(common.RENDERS / "previews" / "architecture" / f"inspect_{common.timestamp()}.png"))
sun_az, sun_el = (float(v) for v in opt("--sun", "135,38").split(","))
rx, ry = (int(v) for v in opt("--res", "1280x720").split("x"))

scene = common.setup_scene()
for o in list(bpy.data.objects):
    if "_LOD" in o.name:
        o.hide_render = o.name.rsplit("_LOD", 1)[1][:1] != lod
if "--no-placeholders" in args:
    for o in bpy.data.collections["ARCH_placeholders"].objects:
        o.hide_render = True
rig = common.rebuild_collection("INSPECT_RIG")
sun = bpy.data.lights.new("INSPECT_sun", "SUN")
sun.energy, sun.angle = 4.0, 0.0093
so = bpy.data.objects.new("INSPECT_sun", sun)
rig.objects.link(so)
common.aim_sun(so, sun_az, sun_el)
world = bpy.data.worlds.new("INSPECT_world")
world.use_nodes = True
nt = world.node_tree
sky = nt.nodes.new("ShaderNodeTexSky")
sky.sky_type = "MULTIPLE_SCATTERING"
sky.sun_elevation, sky.sun_rotation, sky.sun_disc = math.radians(sun_el), math.radians(sun_az), False
bg = nt.nodes["Background"]
nt.links.new(sky.outputs[0], bg.inputs[0])
bg.inputs[1].default_value = 0.35
scene.world = world
scene.view_settings.exposure = -1.0
cd = bpy.data.cameras.new("INSPECT_cam")
cd.lens, cd.sensor_width, cd.sensor_fit, cd.clip_end = lens, 36.0, "HORIZONTAL", 5000.0
co = bpy.data.objects.new("INSPECT_cam", cd)
co.location = cam
if abs(cam[0] - tgt[0]) < 1e-6 and abs(cam[1] - tgt[1]) < 1e-6:
    co.rotation_euler = (math.pi if tgt[2] > cam[2] else 0.0, 0.0, 0.0)
else:
    co.rotation_euler = common.lookat_rotation(cam, tgt)
rig.objects.link(co)
scene.camera = co
if "--cycles" in args:
    common.configure_cycles(scene, samples=64)
else:
    common.configure_eevee(scene, samples=16)
scene.render.resolution_x, scene.render.resolution_y = rx, ry
scene.render.filepath = out
bpy.ops.render.render(write_still=True)
print("[inspect] wrote", out)
