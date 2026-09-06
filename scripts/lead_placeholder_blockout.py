"""Lead's Phase-0 placeholder: crude true-scale massing from OSM footprints + attempt-2 vertical stack.
Purpose: validate coordinate conventions, QA camera framing and the preview pipeline. NOT an art asset.
    blender -b --python scripts/lead_placeholder_blockout.py [-- --preview]
Writes assets/placeholder_blockout.blend (collection PLACEHOLDER).
"""
import bpy, bmesh, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from mathutils import Vector

bpy.ops.wm.read_homefile(use_empty=True)
common.wipe_scene()
scene = common.setup_scene()
coll = common.rebuild_collection("PLACEHOLDER")
site = common.load_site_local()


def prism_from_polygon(name, poly, z0, z1, mat=None):
    bm = bmesh.new()
    verts = [bm.verts.new((x, y, z0)) for (x, y) in poly]
    if len(verts) >= 3:
        try:
            f = bm.faces.new(verts)
        except ValueError:
            bm.free(); return None
        bmesh.ops.triangulate(bm, faces=[f])
        geom = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
        up = [v for v in geom["geom"] if isinstance(v, bmesh.types.BMVert)]
        bmesh.ops.translate(bm, verts=up, vec=(0, 0, z1 - z0))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    if mat: common.assign_material(obj, mat)
    return obj


def flat_from_polygon(name, poly, z, mat=None):
    bm = bmesh.new()
    verts = [bm.verts.new((x, y, z)) for (x, y) in poly]
    f = bm.faces.new(verts)
    bmesh.ops.triangulate(bm, faces=[f])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    obj = bpy.data.objects.new(name, me); coll.objects.link(obj)
    if mat: common.assign_material(obj, mat)
    return obj


def octagon(apothem, rot_deg=8.0):
    r = apothem / math.cos(math.radians(22.5))
    return [(r * math.sin(math.radians(rot_deg + 22.5 + 45 * k)), r * math.cos(math.radians(rot_deg + 22.5 + 45 * k))) for k in range(8)]


def ring(name, a_out, a_in, z0, z1, mat, rot=8.0):
    """Octagonal ring (outer minus inner) via two prisms + boolean."""
    outer = prism_from_polygon(name, octagon(a_out, rot), z0, z1, mat)
    inner = prism_from_polygon(name + "_cut", octagon(a_in, rot), z0 - 1, z1 + 1)
    inner.hide_render = True; inner.hide_viewport = True; inner.display_type = "WIRE"
    b = outer.modifiers.new("cut", "BOOLEAN"); b.operation = "DIFFERENCE"; b.object = inner
    return outer


stone = common.placeholder_material("MAT_concrete_ochre", (0.62, 0.50, 0.34, 1))
col = common.placeholder_material("MAT_column_terracotta", (0.45, 0.26, 0.20, 1))
dome_m = common.placeholder_material("MAT_dome_plaster", (0.72, 0.64, 0.50, 1))
water = common.placeholder_material("MAT_water_lagoon", (0.05, 0.10, 0.09, 1), roughness=0.05)
lawn = common.placeholder_material("MAT_lawn", (0.10, 0.18, 0.05, 1))

# ---- rotunda vertical stack (attempt-2 params relative to water; convert to floor z=0 => subtract 1.3)
W = common.WATER_Z
z_ent_top, z_attic_top, z_drum_top, z_apex = 29.6 + W, 35.7 + W, 37.7 + W, 49.2 + W
ring("PH_rotunda_arcade", 19.8, 14.8, 0.0, z_ent_top, stone)
ring("PH_rotunda_attic", 18.8, 14.0, z_ent_top, z_attic_top, stone)
# drum + dome (lathe)
bm = bmesh.new()
prof = [(18.5, z_attic_top), (18.5, z_drum_top)]
for i in range(1, 17):
    t = i / 16 * math.pi / 2
    prof.append((18.0 * math.cos(t), z_drum_top + (z_apex - z_drum_top) * math.sin(t)))
rings = []
for (r, z) in prof:
    rings.append([bm.verts.new((r * math.cos(a), r * math.sin(a), z)) for a in [k * math.pi / 24 for k in range(48)]] if r > 1e-3 else None)
apex = bm.verts.new((0, 0, z_apex))
for i in range(len(rings) - 1):
    a, b_ = rings[i], rings[i + 1]
    for k in range(48):
        if b_ is None:
            bm.faces.new((a[k], a[(k + 1) % 48], apex))
        else:
            bm.faces.new((a[k], a[(k + 1) % 48], b_[(k + 1) % 48], b_[k]))
me = bpy.data.meshes.new("PH_rotunda_dome"); bm.to_mesh(me); bm.free()
for p in me.polygons: p.use_smooth = True
dome = bpy.data.objects.new("PH_rotunda_dome", me); coll.objects.link(dome); common.assign_material(dome, dome_m)
# 16 pier columns (2 per pier) as cylinders at true diameter
for k in range(8):
    a = math.radians(8.0 + 22.5 + 45 * k)          # pier at octagon vertex
    vx, vy = math.sin(a), math.cos(a)
    R = 19.8 / math.cos(math.radians(22.5)) + 1.3
    for s in (-1, 1):
        px, py = vx * R + s * 1.75 * vy, vy * R - s * 1.75 * vx
        bpy.ops.mesh.primitive_cylinder_add(radius=1.2, depth=20.4, location=(px, py, 5.9 + W + 10.2), vertices=24)
        o = bpy.context.object; o.name = f"PH_pier_column_{k:02d}_{'a' if s < 0 else 'b'}"; common.link_object(o, coll); common.assign_material(o, col)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(px, py, (5.9 + W) / 2 + 0.0))
        o = bpy.context.object; o.scale = (3.1, 3.1, 5.9 + W); o.name = f"PH_pedestal_{k:02d}_{'a' if s < 0 else 'b'}"; common.link_object(o, coll); common.assign_material(o, stone)
# rotunda platform
bpy.ops.mesh.primitive_cylinder_add(radius=32, depth=1.3, location=(0, 0, -0.65), vertices=64)
o = bpy.context.object; o.name = "PH_platform"; common.link_object(o, coll); common.assign_material(o, stone)

# ---- colonnade wings + pylons + exhibition hall from OSM
gz = common.GROUND_Z
for key, h in (("roof306 h20", 20), ("roof310 h19", 19), ("roof313 h21", 21), ("roof314 h21", 21), ("b302 h20m", 20), ("b317 h16", 16)):
    for i, poly in enumerate(site[key]):
        prism_from_polygon(f"PH_{key.split()[0]}_{i}", poly, gz, gz + h, stone)

# ---- lagoon + ground
for i, poly in enumerate(site["lagoon0"]):
    flat_from_polygon(f"PH_lagoon_water_{i}", poly, W, water)
    cutter = prism_from_polygon(f"PH_lagoon_cutter_{i}", poly, W - 2.0, gz + 1.0)
    cutter.hide_render = True; cutter.hide_viewport = True; cutter.display_type = "WIRE"
bpy.ops.mesh.primitive_plane_add(size=1400, location=(0, 0, gz))
ground = bpy.context.object; ground.name = "PH_ground"; common.link_object(ground, coll); common.assign_material(ground, lawn)
sol = ground.modifiers.new("solid", "SOLIDIFY"); sol.thickness = 2.0; sol.offset = -1
for ob in coll.objects:
    if ob.name.startswith("PH_lagoon_cutter"):
        b = ground.modifiers.new("cut_" + ob.name, "BOOLEAN"); b.operation = "DIFFERENCE"; b.object = ob

# report shore position for the hero camera line (x in [0,12])
pts = [p for poly in site["lagoon0"] for p in poly if 0 <= p[0] <= 12]
print("[placeholder] east shore y at x in [0,12]:", round(max(p[1] for p in pts), 1) if pts else "n/a")
allpts = [p for poly in site["lagoon0"] for p in poly]
print("[placeholder] lagoon bbox world x:", round(min(p[0] for p in allpts), 1), round(max(p[0] for p in allpts), 1), "y:", round(min(p[1] for p in allpts), 1), round(max(p[1] for p in allpts), 1))

# sun + world
lc = common.rebuild_collection("PLACEHOLDER_LIGHT")
sun = bpy.data.lights.new("PH_sun", "SUN"); sun.energy = 3.0; sun.color = (1.0, 0.72, 0.45); sun.angle = 0.0093
so = bpy.data.objects.new("PH_sun", sun); lc.objects.link(so); common.aim_sun(so, 118, 7)
world = bpy.data.worlds.new("WORLD_placeholder"); world.use_nodes = True
nt = world.node_tree; sky = nt.nodes.new("ShaderNodeTexSky"); sky.sky_type = "MULTIPLE_SCATTERING"
sky.sun_elevation = math.radians(7); sky.sun_azimuth = math.radians(0); sky.sun_disc = False
bg = nt.nodes.get("Background"); nt.links.new(sky.outputs[0], bg.inputs[0]); bg.inputs[1].default_value = 0.6
scene.world = world
scene.view_settings.exposure = -1.0

common.save_blend(common.ASSETS / "placeholder_blockout.blend")
if "--preview" in common.script_args():
    common.render_previews("lead", samples=8, tag="placeholder")
