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


def world_matrix(o):
    """matrix_world is stale (identity) for objects hidden in the view layer; socket empties are not hidden, but
    use the same accessor the probes use so the two never disagree."""
    if o.parent is not None:
        return o.matrix_world
    return o.matrix_basis

# ----------------------------------------------------------------------------- frieze_run frame contract
# (orn r5 review findings 1 and 2, added in architecture round 6.) A frieze_run socket is a RUN, not a point:
#   origin = the run START,  local +X = run_dir,  local +Y = the outward face normal (away from the host block),
#   local +Z = world up.
# +Y is checked against a block centre derived here, not against anything the builder stamped: the 24 rotunda runs
# come in threes on each of the 8 ressaut corner blocks, so grouping them by nearest ressaut azimuth
# (VERTEX_AZ0 + 45k) and averaging that group's run midpoints reconstructs the block centre independently.
if want == "frieze_run":
    import arch_params as P
    bad = 0
    # The 24 rotunda runs come in threes on each of the 8 ressaut corner blocks, so grouping them by nearest ressaut
    # azimuth (VERTEX_AZ0 + 45k) and averaging that group's run midpoints reconstructs the block centre here,
    # independently of anything the builder stamped. Other hosts get the frame checks that apply to them: the
    # colonnade runs are ARCS (arc_center / arc_radius, no run_dir), the rostra / planter_box runs are straight but
    # sit on free-standing bands with no reconstructible block centre, so only their +X / +Y / +Z frame is asserted.
    groups = {}
    for o in socks:
        p = world_matrix(o).translation
        az = math.degrees(math.atan2(p.y, -p.x)) % 360.0
        k = min(range(8), key=lambda i: abs((az - (P.VERTEX_AZ0 + 45.0 * i) + 180.0) % 360.0 - 180.0))
        rd, rl = o.get("run_dir", None), float(o.get("run_length", 0.0))
        mid = (p.x + (rd[0] if rd else 0.0) * rl / 2.0, p.y + (rd[1] if rd else 0.0) * rl / 2.0)
        groups.setdefault((o.get("host", None), k if o.get("host", None) == "rotunda" else -1), []).append((o, mid))
    print(f"{'socket':26s} {'host':13s} {'subtype':11s} {'len':>6s} {'+X.run_dir':>11s} {'+Y.out':>8s} {'+Z.z':>6s}"
          f"  result")
    for g, v in sorted(groups.items(), key=lambda t: str(t[0])):
        cx = sum(m[0] for _, m in v) / len(v), sum(m[1] for _, m in v) / len(v)
        for o, mid in v:
            M = world_matrix(o)
            x = (M.to_3x3() @ Vector((1.0, 0.0, 0.0))).normalized()
            y = (M.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()
            z = (M.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()
            rd, host, sub = o.get("run_dir", None), o.get("host", None), o.get("subtype", None)
            ac = o.get("arc_center", None)
            dx = (x.x * rd[0] + x.y * rd[1] + x.z * rd[2]) if rd else float("nan")
            frame_ok = abs(y.z) < 1e-3 and z.z > 0.999
            if host == "rotunda":                       # the full contract (orn r5 review findings 1 and 2)
                ry = (mid[0] - cx[0], mid[1] - cx[1])
                n = math.hypot(*ry)
                dy = (y.x * ry[0] + y.y * ry[1]) / n if n > 1e-6 else float("nan")
                ok = rd is not None and dx > 0.99 and dy > 0.0 and frame_ok and sub is not None
            elif ac is not None:                        # arc run: +Y must point outward from the arc centre
                ry = (o.location.x - ac[0], o.location.y - ac[1])
                n = math.hypot(*ry)
                dy = (y.x * ry[0] + y.y * ry[1]) / n if n > 1e-6 else float("nan")
                ok = frame_ok and dy > 0.9 and sub is not None
            else:                                       # straight run on a free-standing band
                dy = float("nan")
                ok = rd is not None and dx > 0.99 and frame_ok and sub is not None
            bad += not ok
            print(f"  {o.name:24s} {str(host):13s} {str(sub):11s} {float(o.get('run_length', 0)):6.2f} "
                  f"{dx:11.3f} {dy:8.3f} {z.z:6.3f}  {'OK' if ok else 'WRONG'}")
    print("[socket_check] rotunda contract: origin at the run START, +X = run_dir (dot > 0.99), +Y away from the "
          "ressaut block centre (> 0), +Z world up, host + subtype present")
    print(f"[socket_check] {'ALL OK' if not bad else str(bad) + ' WRONG'}")
    raise SystemExit(0)

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
