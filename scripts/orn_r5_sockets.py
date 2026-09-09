"""ORN round 5 — inspect the frieze_run sockets in assets/architecture.blend (no render, no writes).

Run: scripts/blender_run.sh 300 -- --background --python scripts/orn_r5_sockets.py
Prints, for every SOCKET_frieze_run_*: index, host/subtype, run_length, band_height, world z, radius from the
rotunda axis, and the local axes, grouped by (host, subtype, rounded run_length).
"""
import sys
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.append(str(Path(__file__).resolve().parent))
import common  # noqa: E402

bpy.ops.wm.open_mainfile(filepath=str(common.ASSET_FILES["ARCH"]))
bpy.context.view_layer.update()

socks = [o for o in bpy.data.objects if o.name.startswith("SOCKET_") and o.get("orn_type") == "frieze_run"]
socks.sort(key=lambda o: o.name)
print(f"[orn_r5] {len(socks)} frieze_run sockets")

groups = defaultdict(list)
for s in socks:
    host = s.get("host", "-")
    sub = s.get("subtype", "-")
    run = float(s.get("run_length", s.get("size_hint", 0.0)) or 0.0)
    groups[(host, sub, round(run, 2))].append(s)

for key in sorted(groups, key=lambda k: (str(k[0]), str(k[1]), k[2])):
    host, sub, run = key
    lst = groups[key]
    zs = sorted({round(o.matrix_world.translation.z, 2) for o in lst})
    bh = sorted({round(float(o.get("band_height", -1)), 3) for o in lst})
    rad = sorted({round(Vector(o.matrix_world.translation[:2]).length, 2) for o in lst})
    arc = sum(1 for o in lst if o.get("arc_center") is not None)
    print(f"  host={host:14s} subtype={sub:12s} run={run:6.2f} n={len(lst):3d} z={zs} band_height={bh} "
          f"radius={rad[:6]}{'...' if len(rad) > 6 else ''} curved={arc}")

print("\n[orn_r5] rotunda-band sockets in detail (z > 25):")
for s in socks:
    if s.matrix_world.translation.z <= 25:
        continue
    M = s.matrix_world
    p = M.translation
    ax = M.to_3x3()
    xr = (ax @ Vector((1, 0, 0))).normalized()
    yr = (ax @ Vector((0, 1, 0))).normalized()
    zr = (ax @ Vector((0, 0, 1))).normalized()
    r = Vector((p.x, p.y, 0.0))
    radial = r.normalized() if r.length > 1e-6 else Vector((0, 0, 0))
    keys = {k: (list(s[k]) if hasattr(s[k], "__len__") and not isinstance(s[k], str) else s[k])
            for k in s.keys() if k not in ("_RNA_UI",)}
    print(f"  {s.name} pos=({p.x:8.3f},{p.y:8.3f},{p.z:7.3f}) r={r.length:6.2f} "
          f"dot(+Y,radial)={yr.dot(radial):+.3f} dot(+Z,up)={zr.dot(Vector((0,0,1))):+.3f} "
          f"|X.z|={abs(xr.z):.3f} scale={tuple(round(v,3) for v in s.scale)} props={keys}")

# the entablature geometry around the band, for the clearance check
for name in sorted(o.name for o in bpy.data.objects if "entab" in o.name.lower() or "frieze" in o.name.lower()):
    o = bpy.data.objects[name]
    if o.type != "MESH":
        continue
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    print(f"  MESH {name}: z {min(v.z for v in bb):.2f}..{max(v.z for v in bb):.2f}, "
          f"xy radius {min(Vector(v[:2]).length for v in bb):.2f}..{max(Vector(v[:2]).length for v in bb):.2f}, "
          f"tris {len(o.data.loop_triangles) if o.data.loop_triangles else sum(len(p.vertices) - 2 for p in o.data.polygons)}")
