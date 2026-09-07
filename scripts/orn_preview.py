"""Preview renders of the ornament assets: LOD0 (left) next to LOD1 with its baked normal map (right), clay material,
neutral ground, placeholder golden-hour sun (az 118.5, el 7.4), Eevee 1280x720.

    blender --background --python scripts/orn_preview.py -- [--only capital_rotunda,maiden] [--tag t] [--lod2]
                                                            [--engine cycles] [--sheet]
Output: renders/previews/ornament/<timestamp>_<asset>[_tag].png (+ contact sheet with --sheet).
"""
import bpy, math, os, sys, time, subprocess
from pathlib import Path
from mathutils import Vector, Matrix, Euler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import orn_lib as L

ARGS = common.script_args()
OUT_DIR = common.RENDERS / "previews" / "ornament"
SUN_AZ, SUN_EL = 118.5, 7.4


def clay_material(name, normal_map=None, color=(0.50, 0.46, 0.41, 1.0)):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = 0.85
    if normal_map:
        p = normal_map
        if p.startswith("//"):
            p = str(common.ASSETS / p[2:])
        if Path(p).exists():
            img = bpy.data.images.load(p, check_existing=True)
            img.colorspace_settings.name = "Non-Color"
            tex = nt.nodes.new("ShaderNodeTexImage")
            tex.image = img
            nm = nt.nodes.new("ShaderNodeNormalMap")
            nm.inputs["Strength"].default_value = 1.0
            nt.links.new(tex.outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
        else:
            print(f"[orn_preview] missing normal map {p}")
    return m


def build_rig():
    coll = common.rebuild_collection("ORN_PREVIEW")
    # ground
    g = L.box("preview_ground", (80, 80, 0.2), coll, location=(0, 0, -0.1))
    gm = bpy.data.materials.new("preview_ground_mat")
    gm.use_nodes = True
    b = gm.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (0.32, 0.32, 0.31, 1.0)
    b.inputs["Roughness"].default_value = 0.95
    common.assign_material(g, gm)
    # sun
    sun = bpy.data.lights.new("preview_sun", "SUN")
    sun.energy = 4.0
    sun.angle = 0.0093
    sun.color = (1.0, 0.82, 0.62)
    so = bpy.data.objects.new("preview_sun", sun)
    coll.objects.link(so)
    common.aim_sun(so, SUN_AZ, SUN_EL)
    # world
    w = bpy.data.worlds.get("preview_world") or bpy.data.worlds.new("preview_world")
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.45, 0.58, 0.80, 1.0)
    bg.inputs[1].default_value = 0.45
    bpy.context.scene.world = w
    # camera
    cam = bpy.data.cameras.new("preview_cam")
    cam.lens = 50.0
    cam.sensor_width = 36.0
    co = bpy.data.objects.new("preview_cam", cam)
    coll.objects.link(co)
    bpy.context.scene.camera = co
    return coll, co


def frame_camera(cam_obj, lo, hi, side_deg=30.0, elev_deg=8.0, pad=1.12):
    lo, hi = Vector(lo), Vector(hi)
    centre = (lo + hi) * 0.5
    size = hi - lo
    fov = 2 * math.atan(36.0 / (2 * cam_obj.data.lens))
    aspect = bpy.context.scene.render.resolution_x / bpy.context.scene.render.resolution_y
    fov_v = 2 * math.atan(math.tan(fov / 2) / aspect)
    # horizontal extent as seen from the side angle, vertical extent from the height
    s, e = math.radians(side_deg), math.radians(elev_deg)
    w = abs(size.x * math.cos(s)) + abs(size.y * math.sin(s))
    depth = abs(size.x * math.sin(s)) + abs(size.y * math.cos(s))
    dist_h = 0.5 * w * pad / math.tan(fov / 2)
    dist_v = 0.5 * size.z * pad / math.tan(fov_v / 2)
    dist = max(dist_h, dist_v) + 0.5 * depth
    d = Vector((math.sin(s) * math.cos(e), math.cos(s) * math.cos(e), math.sin(e)))
    cam_obj.location = centre + d * dist
    cam_obj.rotation_euler = common.lookat_rotation(cam_obj.location, centre)


def asset_groups(only=None):
    groups = {}
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.name.startswith("ORN_") or "_LOD" not in o.name:
            continue
        base = o.name.rsplit("_LOD", 1)[0]
        typ = o.get("orn_type", base.split("_v")[0][4:])
        if only and typ not in only and base[4:] not in only:
            continue
        groups.setdefault(base, {})[o.name[-1]] = o
    return groups


def context_geometry(o, coll):
    """Proxy architecture so poses can be judged: planter-box corner for maidens."""
    made = []
    typ = o.get("orn_type", "")
    if typ == "maiden":
        # socket frame: origin on the box lid, corner edge at (0, box_corner_y, 0), rim top at z=0, walls hang below
        cy = float(o.get("box_corner_y", 0.78))
        depth = abs(float(o.get("feet_z", -3.3)))
        mat = bpy.data.materials.get("preview_ground_mat")
        for side in (1, -1):
            wall = L.box(f"ctx_wall_{side}", (2.6, 0.3, depth), coll, location=(1.3, 0, -depth / 2 + 0.02))
            ang = -45.0 if side > 0 else -135.0
            wall.data.transform(Matrix.Translation((0, cy, 0)) @ Euler((0, 0, math.radians(ang)), "XYZ").to_matrix().to_4x4()
                                @ Matrix.Translation((0, -0.15 if side > 0 else 0.15, 0)))
            common.assign_material(wall, mat)
            made.append(wall)
    return made


def render_group(base, objs, cam, tag, lod2=False, engine="EEVEE"):
    scene = bpy.context.scene
    for o in bpy.data.objects:
        if o.name.startswith("ORN_") and o.type == "MESH":
            o.hide_render = True
            o.hide_viewport = True
    shown = []
    ctx_objs = []
    lo0, hi0 = L.bbox(objs["0"])
    width = max(hi0[0] - lo0[0], hi0[1] - lo0[1])
    gap = width * 1.25
    order = ["0", "1"] + (["2"] if lod2 else [])
    for k, key in enumerate(order):
        o = objs.get(key)
        if o is None:
            continue
        o.hide_render = False
        o.hide_viewport = False
        o.location = (gap * (len(order) - 1) / 2 - k * gap, 0, 0)   # camera at +X+Y: +X shows on the left
        nm = o.get("normal_map") if key == "1" else None
        m = clay_material(f"preview_{o.name}", normal_map=nm)
        o.data.materials.clear()
        o.data.materials.append(m)
        shown.append(o)
        for c in context_geometry(o, bpy.data.collections["ORN_PREVIEW"]):
            c.location = o.location
            ctx_objs.append(c)
    lo = Vector((min(L.bbox(o)[0][i] + o.location[i] for o in shown) for i in range(3)))
    hi = Vector((max(L.bbox(o)[1][i] + o.location[i] for o in shown) for i in range(3)))
    ground = bpy.data.objects.get("preview_ground")
    if ground is not None:
        ground.location.z = min(0.0, lo.z)
    frame_camera(cam, lo, hi)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fp = OUT_DIR / f"{tag}_{base[4:]}.png"
    scene.render.filepath = str(fp)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[orn_preview] {fp.name} in {time.time() - t:.1f}s")
    for o in shown:
        o.location = (0, 0, 0)
    for c in ctx_objs:
        L.remove_object(c)
    return fp


def main():
    src = Path(ARGS[ARGS.index("--src") + 1]) if "--src" in ARGS else common.ASSET_FILES["ORN"]
    if not src.exists():
        print("[orn_preview] no assets/ornament.blend yet")
        return
    bpy.ops.wm.open_mainfile(filepath=str(src))
    scene = common.setup_scene()
    if ("--engine" in ARGS and ARGS[ARGS.index("--engine") + 1].lower() == "cycles"):
        common.configure_cycles(scene, samples=64)
    else:
        common.configure_eevee(scene, samples=32)
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    scene.view_settings.look = "AgX - Base Contrast"
    only = None
    if "--only" in ARGS:
        only = [s.strip() for s in ARGS[ARGS.index("--only") + 1].split(",") if s.strip()]
    tag = ARGS[ARGS.index("--tag") + 1] if "--tag" in ARGS else common.timestamp()
    coll, cam = build_rig()
    outs = []
    for base, objs in sorted(asset_groups(only).items()):
        if "0" not in objs or "1" not in objs:
            continue
        outs.append(render_group(base, objs, cam, tag, lod2="--lod2" in ARGS, engine="CYCLES" if ("--engine" in ARGS and ARGS[ARGS.index("--engine") + 1].lower() == "cycles") else "EEVEE"))
    if "--sheet" in ARGS and outs:
        sheet = OUT_DIR / f"{tag}_contact_sheet.png"
        cmd = ["python3", str(common.ROOT / "scripts" / "qa_compare.py"), "--sheet", str(sheet)] + [str(p) for p in outs]
        subprocess.run(cmd, check=False)
        print(f"[orn_preview] sheet {sheet}")


if __name__ == "__main__":
    main()
