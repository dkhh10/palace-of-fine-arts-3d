"""Print the facing frame of every SOCKET_* of a given type (default rosette_ceiling) in assets/architecture.blend.

    blender -b assets/architecture.blend --python scripts/arch_socket_check.py [-- --type rosette_ceiling]

Socket contract: local +Y is the direction the ornament's FRONT faces. For the ceiling rosettes the rim-band
bosses must face the rotunda axis (dot(+Y, radial) = -1) and the coffer-floor ones straight down (+Y.z = -1).
"""
import bpy, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

args = common.script_args()
want = args[args.index("--type") + 1] if "--type" in args and args.index("--type") + 1 < len(args) else "rosette_ceiling"
socks = sorted((o for o in bpy.data.objects if o.name.startswith(f"SOCKET_{want}_")), key=lambda o: o.name)
print(f"[socket_check] {len(socks)} SOCKET_{want}_* sockets")
bad = 0
for o in socks:
    M = o.matrix_world
    y = (M.to_3x3() @ __import__("mathutils").Vector((0.0, 1.0, 0.0))).normalized()
    p = M.translation
    rad = math.hypot(p.x, p.y)
    r = (p.x / rad, p.y / rad, 0.0) if rad > 1e-6 else (0.0, 0.0, 0.0)
    dot = y.x * r[0] + y.y * r[1]
    kind = "coffer-floor" if abs(y.z) > 0.5 else "rim-band"
    ok = (y.z < -0.999) if kind == "coffer-floor" else (dot < -0.999)
    bad += not ok
    print(f"  {o.name}  r={rad:6.2f} z={p.z:7.3f}  +Y=({y.x:+.3f},{y.y:+.3f},{y.z:+.3f})  "
          f"dot(+Y,radial)={dot:+.3f}  +Y.z={y.z:+.3f}  {kind:12s} {'OK' if ok else 'WRONG'}")
print(f"[socket_check] {'ALL OK' if not bad else str(bad) + ' WRONG'}")
