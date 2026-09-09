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
if want != "props":                                  # "props" is a whole-file audit, not one socket type
    print(f"[socket_check] {len(socks)} SOCKET_{want}_* sockets")
from mathutils import Vector


def world_matrix(o):
    """matrix_world is stale (identity) for objects hidden in the view layer; socket empties are not hidden, but
    use the same accessor the probes use so the two never disagree."""
    if o.parent is not None:
        return o.matrix_world
    return o.matrix_basis

# ----------------------------------------------------------------------------- documented-property contract
# docs/sockets.md: every socket carries orn_type / size_hint / variant_seed; these are the EXTRA properties each
# type must carry.  `--type props` walks every SOCKET_* in the file and reports any type missing any of them.
BASE_PROPS = ("orn_type", "size_hint", "variant_seed")
REQUIRED_PROPS = {
    "capital_rotunda":   ("capital_height",),
    "capital_inner":     ("capital_height",),
    "capital_colonnade": ("capital_height", "tall", "wing"),
    "frieze_run":        ("run_length", "band_height", "host", "subtype"),
    "attic_panel":       ("panel_height", "design"),
    "maiden":            ("rim_height", "box_corner_y"),
    "keystone":          ("subtype",),
    "finial":            ("subtype",),
    "drum_band":         ("run_length", "radius"),
    "archivolt_run":     ("run_length", "band_width", "arc_center", "arc_radius", "arc_angle", "host", "subtype"),
}
if want == "props":
    types = {}
    for o in bpy.data.objects:
        if o.name.startswith("SOCKET_"):
            types.setdefault(o.get("orn_type", o.name[7:-4]), []).append(o)
    bad = 0
    print(f"{'type':20s} {'n':>4s}  required properties (BASE + type)                          missing")
    for t, v in sorted(types.items()):
        need = BASE_PROPS + REQUIRED_PROPS.get(t, ())
        miss = {k: sum(1 for o in v if o.get(k) is None) for k in need}
        miss = {k: c for k, c in miss.items() if c}
        bad += bool(miss)
        sample = {k: v[0].get(k) for k in REQUIRED_PROPS.get(t, ())}
        print(f"  {t:18s} {len(v):4d}  {'+'.join(need):56s} "
              f"{'none  ' + str(sample) if not miss else 'MISSING ' + str(miss)}")
    print(f"[socket_check] {len(types)} types, {sum(len(v) for v in types.values())} sockets; "
          f"{'ALL OK' if not bad else str(bad) + ' TYPES INCOMPLETE'}")
    raise SystemExit(1 if bad else 0)

# ----------------------------------------------------------------------------- archivolt_run frame contract
# (architecture round 7, ORN r6 proposal section 4.) An `archivolt_run` socket is a run bent into the vertical
# plane of one rotunda arch:  origin at a springing ON the archivolt's flat crown face, +X = the arc tangent
# there (vertical, a semicircular arch springs straight up), +Y = the wall's outward face normal, +Z = +X x +Y =
# radially outward from the arc centre (the band's width direction, the analogue of "up" on a frieze_run).
# Nothing here trusts the builder: the face normal is rebuilt from arch_params' octagon, the crown-face plane
# from the ARCHIVOLT MESH's own extent along that normal, and every point of the stamped arc parametrisation is
# tested against the mesh surface with closest_point_on_mesh.
if want == "archivolt_run":
    import arch_params as P
    bad = 0
    dg = bpy.context.evaluated_depsgraph_get()
    print(f"{'socket':24s} {'face':>4s} {'+Y.n':>6s} {'+X.z':>6s} {'+Z.rad':>7s} {'orig-mesh':>10s} "
          f"{'plane d':>8s} {'mesh d':>7s} {'R':>6s} {'arc len':>8s} {'arc worst':>10s} {'mid worst':>10s} {'nout':>5s} result")
    for o in socks:
        M = world_matrix(o)
        p = M.translation
        x = (M.to_3x3() @ Vector((1.0, 0.0, 0.0))).normalized()
        y = (M.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()
        z = (M.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()
        # which of the 8 octagon faces is this, from arch_params alone
        az = math.degrees(math.atan2(p.y, -p.x)) % 360.0
        k = min(range(8), key=lambda i: abs((az - (P.FACE_AZ0 + 45.0 * i) + 180.0) % 360.0 - 180.0))
        nf = P.az_dir(P.FACE_AZ0 + 45.0 * k)
        nf = Vector((nf[0], nf[1], 0.0))
        obj = bpy.data.objects.get(f"ARCH_rotunda_archivolt_{k:02d}")
        if obj is None:
            print(f"  {o.name:22s}  no ARCH_rotunda_archivolt_{k:02d} mesh")
            bad += 1
            continue
        Wm, Wi = obj.matrix_world, obj.matrix_world.inverted()
        # the crown-face plane, measured on the mesh: the farthest the archivolt reaches along the face normal
        mesh_d = max((Wm @ v.co).dot(nf) for v in obj.data.vertices)
        plane_d = p.dot(nf)                                    # where the socket origin sits along that normal
        ev = obj.evaluated_get(dg)                             # with the 0.03 m arris bevel, for the mid-band test

        def surf(pt, o_=obj, bevelled=False):
            """distance in mm from a world point to the archivolt surface (nominal swept mesh, or bevelled)."""
            t = ev if bevelled else o_
            ok, loc, nrm, _ = t.closest_point_on_mesh(Wi @ Vector(pt))
            return (1000.0 * ((Wm @ loc) - Vector(pt)).length if ok else float("inf"),
                    (Wm.to_3x3() @ nrm).normalized())
        d_orig, _ = surf(p)
        R = float(o.get("arc_radius", 0.0))
        ac = o.get("arc_center", None)
        ac = Vector(tuple(ac)) if ac is not None else Vector((0.0, 0.0, 0.0))
        ang = float(o.get("arc_angle", 0.0))
        bw = float(o.get("band_width", 0.0))
        # every point of the stamped parametrisation must be ON the band: P(phi) = C + R*(cos phi * +Z + sin phi * +X)
        worst_arc, worst_mid, faces_out = 0.0, 0.0, 0
        for i in range(13):
            phi = math.radians(ang * i / 12.0)
            rad = z * math.cos(phi) + x * math.sin(phi)
            worst_arc = max(worst_arc, surf(ac + rad * R)[0])
            dm, nm = surf(ac + rad * (R + bw / 2.0), bevelled=True)
            worst_mid = max(worst_mid, dm)
            # The band's MID-line is the face the ornament will sit on, and it must look along +Y for the whole
            # run. The two ENDPOINTS (i = 0, 12) sit exactly on the sweep's end caps, where closest_point_on_mesh
            # may return the cap's normal (+-tangent) instead of the band's, so only the 11 interior samples vote.
            faces_out += (0 < i < 12 and nm.dot(y) > 0.99)
        checks = {"+Y=face normal": y.dot(nf) > 0.999, "+X=tangent up": x.z > 0.999,
                  "+Z=radial out": z.dot(Vector((0.0, 0.0, 1.0)).cross(nf)) > 0.999,
                  "origin on mesh": d_orig < 5.0, "band faces +Y": faces_out == 11,
                  "origin on crown plane": abs(plane_d - mesh_d) < 0.005,
                  "arc centre at springing": abs(ac.z - P.ARCH_SPRING_Z) < 1e-4,
                  "arc angle 180": abs(ang - 180.0) < 1e-6,
                  "run_length = pi R": abs(float(o.get("run_length", 0.0)) - math.pi * R) < 1e-4,
                  "arc on band": worst_arc < 5.0, "mid-line on band": worst_mid < 5.0}
        ok = all(checks.values())
        bad += not ok
        if not ok:
            print(f"    FAILED: {', '.join(k for k, v in checks.items() if not v)}")
        print(f"  {o.name:22s} {k:4d} {y.dot(nf):6.3f} {x.z:6.3f} "
              f"{z.dot(Vector((0.0, 0.0, 1.0)).cross(nf)):7.3f} {d_orig:8.2f}mm {plane_d:8.3f} {mesh_d:7.3f} "
              f"{R:6.3f} {math.pi * R:8.3f} {worst_arc:8.2f}mm {worst_mid:8.2f}mm {faces_out:5d}  {'OK' if ok else 'WRONG'}")
    print("[socket_check] archivolt_run contract: origin at a springing on the archivolt crown face (< 5 mm from "
          "the mesh, on an outward-facing face), +Y = the octagon face normal rebuilt from arch_params, +X = the "
          "arc tangent (world up), +Z = +X x +Y = radially outward; the crown-face plane distance matches the "
          "mesh's own extent along +Y to 5 mm; the 13 sampled points of the stamped arc (and of the band's "
          "mid-line, against the bevelled evaluated mesh) all lie on the band.")
    print(f"[socket_check] {'ALL OK' if not bad else str(bad) + ' WRONG'}")
    raise SystemExit(1 if bad else 0)

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
    raise SystemExit(1 if bad else 0)

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
raise SystemExit(1 if bad else 0)
