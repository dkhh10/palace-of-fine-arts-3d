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
from mathutils import Vector

bad, perps = 0, []
for o in socks:
    M = o.matrix_world
    y = (M.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()
    z = (M.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()
    p = M.translation
    rad = math.hypot(p.x, p.y)
    r = (p.x / rad, p.y / rad) if rad > 1e-6 else (0.0, 0.0)
    dot = y.x * r[0] + y.y * r[1]
    if abs(y.z) > 0.5:                       # facing out of the horizontal plane: a soffit / coffer-floor socket
        kind, ok, note = "coffer-floor", y.z < -0.999, "+Y down"
    else:
        # A band socket stands on one flat octagon face, so its facing is that face's INWARD NORMAL -- horizontal,
        # pointing at the axis, and up to ROSETTE_BAND_HALF_ANGLE off the socket's own radial (two sockets share
        # each face). Verify +Y is horizontal, +Z is world up (the rosette stands upright on the face), the facing
        # leans inward by exactly that half-angle, and the face plane is the same distance from the axis for all.
        kind = "band"
        perp = -(p.x * y.x + p.y * y.y)       # distance from the axis to the face plane the socket faces
        lean = math.degrees(math.acos(max(-1.0, min(1.0, -dot))))
        perps.append(perp)
        ok = (abs(y.z) < 1e-3 and z.z > 0.999 and dot < -0.9)
        note = f"apothem {perp:.3f}, leans {lean:.2f} deg"
    bad += not ok
    print(f"  {o.name}  r={rad:6.2f} z={p.z:7.3f}  +Y=({y.x:+.3f},{y.y:+.3f},{y.z:+.3f}) +Z.z={z.z:+.3f}  "
          f"dot(+Y,radial)={dot:+.3f}  +Y.z={y.z:+.3f}  {kind:12s} {note:28s} {'OK' if ok else 'WRONG'}")
if perps:
    spread = max(perps) - min(perps)
    print(f"[socket_check] band sockets: {len(perps)} on face planes {min(perps):.3f}-{max(perps):.3f} m from the "
          f"axis (spread {spread * 1000:.1f} mm)")
    if spread > 1e-3:
        bad += 1
print(f"[socket_check] {'ALL OK' if not bad else str(bad) + ' WRONG'}")
