"""Round-10 item A probe: what the hero's dome-cap box (920 95 1000 120, 1920x1080) actually sees.

    blender --background master.blend --python scripts/mat_r10_probe.py

Ray-casts CAM_qa_01_lagoon_hero through a grid of pixels in the box (and a wider dome window) and reports, per
hit, the object, the OBJECT-space position the shader's `Texture Coordinate > Object` delivers and the WORLD
normal its `Geometry > Normal` delivers -- the two inputs `PFA_dome` is driven by.  Printed as the ranges of the
cylindrical radius r, the height pz and the normal z, because those are what the seam / streak / grime masks key
off and what degenerates at the crown.
"""
import sys
import math
import bpy
from mathutils import Vector

CAM = "CAM_qa_01_lagoon_hero"
RES = (1920, 1080)
BOXES = {"dome_cap": (920, 95, 1000, 120), "dome_wide": (860, 80, 1070, 150),
         "vault_field": (900, 380, 1010, 430), "jamb": (872, 400, 892, 480)}


def ray(scene, depsgraph, cam, px, py):
    """Pixel centre (px, py) in RES, top-left origin -> (obj, world hit, world normal)."""
    w, h = RES
    # camera-space ray through the pixel, using the camera's own frame
    frame = cam.data.view_frame(scene=scene)            # 4 corners at z = -1 in camera space
    tr, br, bl, tl = frame
    u = (px + 0.5) / w
    v = (py + 0.5) / h
    top = tl.lerp(tr, u)
    bot = bl.lerp(br, u)
    d = top.lerp(bot, v)
    mw = cam.matrix_world
    origin = mw.translation
    direction = (mw.to_3x3() @ d).normalized()
    hit, loc, nrm, idx, obj, mat = scene.ray_cast(depsgraph, origin, direction, distance=5000.0)
    return (obj, loc, nrm) if hit else (None, None, None)


def main():
    scene = bpy.context.scene
    scene.render.resolution_x, scene.render.resolution_y = RES
    scene.render.resolution_percentage = 100
    cam = bpy.data.objects[CAM]
    scene.camera = cam
    dg = bpy.context.evaluated_depsgraph_get()

    for name, (x0, y0, x1, y1) in BOXES.items():
        counts, rows = {}, []
        for py in range(y0, y1, max(1, (y1 - y0) // 14)):
            for px in range(x0, x1, max(1, (x1 - x0) // 14)):
                obj, loc, nrm = ray(scene, dg, cam, px, py)
                if obj is None:
                    counts["<sky>"] = counts.get("<sky>", 0) + 1
                    continue
                mats = [sl.material.name for sl in obj.material_slots if sl.material]
                key = f"{obj.name} [{','.join(mats)}]"
                counts[key] = counts.get(key, 0) + 1
                po = obj.matrix_world.inverted() @ loc
                rows.append((key, po, nrm, px, py))
        print(f"\n[{name}] {x1 - x0}x{y1 - y0} px, {sum(counts.values())} rays")
        for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
            print(f"    {v:4d}  {k}")
        for target in {r[0] for r in rows}:
            sel = [r for r in rows if r[0] == target]
            r_ = [math.hypot(p.x, p.y) for _, p, _, _, _ in sel]
            z_ = [p.z for _, p, _, _, _ in sel]
            nz = [n.z for _, _, n, _, _ in sel]
            ang = [math.degrees(math.atan2(p.y, p.x)) for _, p, _, _, _ in sel]
            print(f"    {target}: object r {min(r_):.2f}-{max(r_):.2f} m, object z {min(z_):.2f}-{max(z_):.2f} m, "
                  f"world nz {min(nz):.3f}-{max(nz):.3f}, object azimuth {min(ang):.0f}..{max(ang):.0f} deg")

    d = bpy.data.objects.get("ARCH_rotunda_dome")
    if d:
        bb = [d.matrix_world @ Vector(c) for c in d.bound_box]
        xs = [v.x for v in bb]; ys = [v.y for v in bb]; zs = [v.z for v in bb]
        print(f"\n[ARCH_rotunda_dome] world bbox x {min(xs):.2f}..{max(xs):.2f}  y {min(ys):.2f}..{max(ys):.2f}  "
              f"z {min(zs):.2f}..{max(zs):.2f}")
        print(f"    matrix_world translation {tuple(round(v, 3) for v in d.matrix_world.translation)}  "
              f"scale {tuple(round(v, 4) for v in d.matrix_world.to_scale())}")
        print(f"    material slots: {[s.material.name if s.material else None for s in d.material_slots]}")
        me = d.data
        lz = [v.co.z for v in me.vertices]
        lr = [math.hypot(v.co.x, v.co.y) for v in me.vertices]
        print(f"    local mesh: z {min(lz):.3f}..{max(lz):.3f}, r {min(lr):.3f}..{max(lr):.3f}, "
              f"{len(me.vertices)} verts")
    else:
        print("\n[ARCH_rotunda_dome] NOT FOUND; dome-material objects:")
        for o in bpy.data.objects:
            for s in o.material_slots:
                if s.material and s.material.name.startswith("MAT_dome"):
                    print("   ", o.name, s.material.name)
                    break


main()
