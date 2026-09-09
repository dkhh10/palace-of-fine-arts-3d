"""Build the ornament library assets/ornament.blend (collection ORN) headless and idempotently.

    blender --background --python scripts/orn_build.py -- [--only capital_rotunda,maiden] [--no-bake] [--fast]
                                                          [--variants N] [--fresh] [--out other.blend]
    blender --background --python scripts/orn_build.py -- --bake-pending     # list assets whose LOD1 has no
                                                                            # normal map + the command to bake them

Without --only every asset type is rebuilt from an empty file. With --only the existing ornament.blend is opened and
just those sub-collections (ORN_<type>) are wiped and rebuilt, so heavy assets can be iterated one at a time.
Every asset: origin bottom-centre, +Z up, +Y outward, real size, LOD0/1/2, baked normal map on LOD1 (custom props
normal_map / ao_map), material MAT_ornament_concrete. See docs/ornament_notes.md.
"""
import bpy, math, random, os, sys, time
from pathlib import Path
from mathutils import Vector, Matrix, Euler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import orn_lib as L

TAU = math.tau
ARGS = common.script_args()
FAST = "--fast" in ARGS
BAKE = "--no-bake" not in ARGS
NVAR = int(ARGS[ARGS.index("--variants") + 1]) if "--variants" in ARGS else 3
OUT = Path(ARGS[ARGS.index("--out") + 1]) if "--out" in ARGS else common.ASSET_FILES["ORN"]


def rot_z(deg):
    return Euler((0.0, 0.0, math.radians(deg)), "XYZ").to_matrix().to_4x4()


def place(obj, rot_z_deg=0.0, loc=(0, 0, 0), tilt_x_deg=0.0, scale=1.0):
    """Bake a transform into the mesh: scale, tilt about local X, rotate about Z, translate."""
    m = Matrix.Translation(loc) @ rot_z(rot_z_deg) @ Euler((math.radians(tilt_x_deg), 0, 0), "XYZ").to_matrix().to_4x4()
    m = m @ Matrix.Scale(scale, 4)
    obj.data.transform(m)
    return obj


# =============================================================================== CAPITALS
# Proportions in units of H (capital height) for z and R (shaft-top radius) for r. Measured against the crops
# corinthian_capital_1-3 (rotunda), inner_capital_1-2, colonnade_capital_1-2, pylon_capital_1.
#
# Round 4 (QA-03-15). The round-3 bell flared to 1.30 R while the leaves' bodies sat at ~1.00 R, so every leaf was
# BURIED inside the bell and only the last third of its tip broke the surface: the capital rendered as a smooth vase
# with faint embossed outlines ("low-contrast blob"). The kalathos is now a slim vase that necks in to 0.865 R and
# only flares to 1.10 R under the volutes; the leaves are lofted along an explicit spine that hugs that surface and
# then curls its tip outward AND DOWN through a 105-120 deg arc, so each tip has a genuine sky-lit-only undercut.
BELL_PROFILE = [(1.00, 0.000), (1.06, 0.020), (1.055, 0.040), (0.995, 0.062), (0.925, 0.090), (0.885, 0.140),
                (0.868, 0.230), (0.865, 0.340), (0.880, 0.450), (0.912, 0.560), (0.960, 0.660), (1.040, 0.750),
                (1.100, 0.820), (1.145, 0.870), (1.155, 0.890), (1.158, 0.900)]

# Where the bell is scalloped: radius dips between the leaves of each row so the slot between two neighbouring
# leaves bottoms out in a real groove instead of on a smooth cylinder.
# ------------------------------------------------------------------ ARCH round-6 course heights (see ORN round 6)
# The three numbers ORN builds to. They come from the registered stack (arch_params r6, ref 169) and are re-checked
# against the socket properties by scripts/orn_r5_stats.py sections 6/7, which FAILS if ARCH and ORN disagree:
#   CAPITAL_H 2.6 -> 3.0   (COL_SHAFT_Z1 22.96 + 3.0 = ENTABLATURE_Z0 25.96, so the capital fills the course exactly)
#   FRIEZE_H  0.90 -> 0.81 (ARCHITRAVE_H 1.04 / FRIEZE_H 0.81 / CORNICE_H 1.37 = the 3.22 m entablature)
#   panel_height 4.50 -> 5.27 (ATTIC_Z1 38.30 - 2.10 - 0.45 minus ATTIC_Z0 29.18 + 0.85 + 0.45)
ARCH_R6 = dict(capital_rotunda_H=3.0, frieze_band_H=0.81, attic_panel_H=5.27)

CAPITAL_PRESETS = {
    # rotunda: h 3.0 (r6 course; was 2.6), shaft top D 2.1, abacus ~3.0 across corners; figured centre.
    # 3.0 / 2.1 = 1.43 is the classical Corinthian ratio (capital = 7/6 of the LOWER diameter, top = 5/6 of it);
    # at 2.6 the capital was 1.24 of the top diameter, i.e. a short capital, which is half of QA-06-6's 24 px.
    #
    # ROUND 7 (r6 review finding 2). The 3.0 m capital used to be the 2.6 m design stretched in Z: only the
    # H-keyed entries grew, so the tiers ran 0.354 / 0.288 H (leaf 1.32 / 1.11 m long) at unchanged R-keyed width
    # and projection. The lay-out below is solved by scripts/orn_r7_capital_layout.py against ref_002
    # (the frontal pier capital): both acanthus tiers 0.300 H of VERTICAL EXTENT, the upper row springing 0.03 H
    # behind the lower row's tips, the caulicoli + volutes filling the top 0.35 H (spirals 0.663-0.887 H) and the
    # abacus 0.100 H. `proud` is now a fraction of H (0.20 / 0.17 of the row's own extent), and lower_w / upper_w
    # are re-derived so leaf width / extent = 1.02 / 1.08 as measured on ref_002 - none of the three is inherited
    # from the 2.6 m capital any more.
    "capital_rotunda": dict(H=ARCH_R6["capital_rotunda_H"], R=1.05, abacus_across=3.0, figure=True, lower_len=0.372, upper_len=0.378,
                            lower_w=1.053, upper_w=1.361, ribs=7, curl=0.32, droop=0.18, volute_r=0.112, helix_r=0.055,
                            lower_z=0.030, upper_z=0.300, rows=2, voxel=0.011, leaf_tilt=(3.0, 4.0),
                            proud=(0.060, 0.052), arc_deg=(100.0, 90.0), arc_frac=(0.28, 0.26), mid_dip=0.078,
                            scallop=0.078, thickness=0.062, volute_z=0.775, volute_er=1.380, helix_er=1.245,
                            helix_z=0.745, abacus_z0=0.900, fig_t=0.545),
    # inner tan columns: h 1.8 on a ~1.6 m shaft, same design, fleuron centre
    # inner / colonnade: NOT re-laid this round (they were never Z-stretched - they have stood at H 1.8 since
    # round 4, and 122 instances are the wrong thing to change in a round with no GPU to look at them). `proud` is
    # restated in H so the units match the rotunda: 0.140 x R 0.80 / 1.8 = 0.0622 H etc., i.e. the same metres.
    "capital_inner": dict(H=1.8, R=0.80, abacus_across=2.15, figure=False, lower_len=0.44, upper_len=0.37,
                          lower_w=1.26, upper_w=1.30, ribs=7, curl=0.32, droop=0.18, volute_r=0.115, helix_r=0.058,
                          lower_z=0.060, upper_z=0.440, rows=2, voxel=0.009, leaf_tilt=(3.0, 4.0),
                          proud=(0.06222, 0.05778), arc_deg=(99.0, 89.0), arc_frac=(0.28, 0.26), mid_dip=0.078,
                          scallop=0.078, thickness=0.064, volute_z=0.805, volute_er=1.380, helix_er=1.245,
                          helix_z=0.775, abacus_z0=0.890, fig_t=0.600),
    # colonnade: h 1.8 on a 1.7 m shaft: squatter, big shell leaves + big scrolls, small lower leaves, fleuron
    "capital_colonnade": dict(H=1.8, R=0.85, abacus_across=2.3, figure=False, lower_len=0.36, upper_len=0.40,
                              lower_w=1.20, upper_w=1.34, ribs=7, curl=0.30, droop=0.16, volute_r=0.122, helix_r=0.058,
                              lower_z=0.058, upper_z=0.420, rows=2, voxel=0.009, leaf_tilt=(3.0, 4.0),
                              proud=(0.06375, 0.06375), arc_deg=(98.0, 94.0), arc_frac=(0.28, 0.27), mid_dip=0.075,
                              scallop=0.076, thickness=0.066, volute_z=0.800, volute_er=1.390, helix_er=1.250,
                              helix_z=0.770, abacus_z0=0.890, fig_t=0.638),
}


def bell_radius(P, z_m):
    """Kalathos radius (metres) at height z_m, interpolated from BELL_PROFILE (r in R, z in H)."""
    R, H = P["R"], P["H"]
    t = max(0.0, min(z_m / H, BELL_PROFILE[-1][1]))
    prev = BELL_PROFILE[0]
    for r, z in BELL_PROFILE:
        if z >= t:
            if z - prev[1] < 1e-9:
                return r * R
            f = (t - prev[1]) / (z - prev[1])
            return (prev[0] + (r - prev[0]) * f) * R
        prev = (r, z)
    return BELL_PROFILE[-1][0] * R


def leaf_spine(P, base_z, length, proud, arc_deg, arc_frac, lean=0.060, n=30):
    """Centreline for one acanthus leaf, in the leaf-local (y outward, z up) frame with the base at (0, 0).
    Body: follows the bell surface with a growing outward offset (so the whole leaf stands proud, not just the tip).
    Tip: a circular arc of `arc_deg` over the last `arc_frac` of the length, bending outward and then downward -
    the down-turned underside is what stays unlit under a 7.4 deg sun and reads as the dark recess QA-03-15 asks for."""
    r0 = bell_radius(P, base_z)
    body_frac = 1.0 - arc_frac
    nb = max(6, int(n * 0.62))
    pts = []
    for i in range(nb + 1):
        u = i / nb
        z = length * body_frac * u
        y = (bell_radius(P, base_z + z) - r0) + proud * (u ** 0.85) + lean * length * u * u
        pts.append((y, z))
    (y1, z1), (y0, z0) = pts[-1], pts[-2]
    th0 = math.atan2(y1 - y0, max(z1 - z0, 1e-6))
    La = length * arc_frac
    na = max(6, n - nb)
    A = math.radians(arc_deg)
    y, z = y1, z1
    for k in range(1, na + 1):
        th = th0 + A * (k / na)
        y += math.sin(th) * La / na
        z += math.cos(th) * La / na
        pts.append((y, z))
    return pts


def row_extent_H(P, row):
    """Vertical extent of one acanthus row, in units of H: the highest point of the tilted leaf spine above the
    row's own base. This is the number the round-7 lay-out targets (0.300 H for both rows of capital_rotunda);
    `lower_len` / `upper_len` are spine lengths, which run ~24 % longer because the tip curls outward and down.
    Kept in sync with scripts/orn_r7_capital_layout.py, which solves the lengths offline."""
    key = ("lower", "upper")[row]
    H = P["H"]
    sp = leaf_spine(P, P[key + "_z"] * H, P[key + "_len"] * H, proud=P["proud"][row] * H,
                    arc_deg=P["arc_deg"][row], arc_frac=P["arc_frac"][row])
    a = math.radians(-P["leaf_tilt"][row])
    return max(y * math.sin(a) + z * math.cos(a) for (y, z) in sp) / H


def abacus_outline(R, across, sag=0.16, chamfer=0.12, per_side=14):
    """Concave-sided square abacus plan with chamfered corners. Returns a list of Vector (counter-clockwise)."""
    half_diag = 0.5 * across          # corner tip radius
    corner = half_diag / math.sqrt(2)  # half side of the un-cut square
    c = chamfer * R
    pts = []
    corners = [Vector((corner, corner)), Vector((-corner, corner)), Vector((-corner, -corner)), Vector((corner, -corner))]
    for k in range(4):
        A, B = corners[k], corners[(k + 1) % 4]
        d = (B - A)
        L_ = d.length
        d.normalize()
        inward = Vector((-A.x - B.x, -A.y - B.y)).normalized()
        a = A + d * c
        b = B - d * c
        for i in range(per_side):
            t = i / per_side
            p = a + (b - a) * t + inward * (sag * R * math.sin(math.pi * t))
            pts.append(p)
    return pts


def abacus_z(P, u):
    """Height (in H) of a point u = 0..1 through the abacus moulding. The abacus seat `abacus_z0` is a preset
    number so the rotunda can carry the reference's 0.100 H abacus without moving the inner / colonnade ones."""
    z0 = P.get("abacus_z0", 0.890)
    return z0 + u * (1.0 - z0)


# profile through the abacus moulding: (scale, u) from the bottom fillet (u = 0) to the top face (u = 1)
ABACUS_PROFILE = [(0.86, 0.0), (0.88, 0.13636), (0.90, 0.27273), (0.955, 0.59091), (0.985, 0.77273),
                  (1.0, 0.86364), (1.0, 1.0)]


def build_abacus(name, P, coll):
    R, H = P["R"], P["H"]
    outline = abacus_outline(R, P["abacus_across"])
    prof = [(s, abacus_z(P, u)) for s, u in ABACUS_PROFILE]
    rings = []
    for s, z in prof:
        rings.append([Vector((p.x * s, p.y * s, z * H)) for p in outline])
    ab = L.loft_rings(name, rings, coll)
    L.shade_smooth(ab, sharp_angle_deg=40)
    return ab


def build_leaf_ring(P, count, offset_deg, base_zH, length_H, width_scale, rng, coll, tag, row):
    """One ring of `count` acanthus leaves standing proud of the kalathos, tips curled outward and down."""
    R, H = P["R"], P["H"]
    base_z = base_zH * H
    r0 = bell_radius(P, base_z)
    leaves = []
    width = (TAU * r0) / count * width_scale     # < pitch, so a real slot is left between neighbours
    for k in range(count):
        phi = offset_deg + k * (360.0 / count) + rng.uniform(-1.6, 1.6)
        ln = length_H * H * rng.uniform(0.96, 1.04)
        # `proud` is a fraction of H (round 7): the leaf body's stand-off from the kalathos has to grow with the
        # course, or a taller capital gets longer, flatter leaves - which is exactly what the r6 stretch produced.
        sp = leaf_spine(P, base_z, ln,
                        proud=P["proud"][row] * H * rng.uniform(0.88, 1.12),
                        arc_deg=P["arc_deg"][row] * rng.uniform(0.94, 1.07),
                        arc_frac=P["arc_frac"][row])
        leaf = L.acanthus_leaf(f"leaf_{tag}_{k}", length=ln, width=width * rng.uniform(0.96, 1.04), spine=sp,
                               ribs=P["ribs"], rib_amp=0.032 * R, bulge=0.032 * R, mid_dip=P["mid_dip"] * R,
                               thickness=P["thickness"] * R, lobes=5, lobe_depth=0.26, nu=30, nv=len(sp) - 1,
                               coll=coll, seed=rng.randint(0, 9999), base_width=0.55)
        tilt = -P["leaf_tilt"][row] + rng.uniform(-1.5, 1.5)
        place(leaf, rot_z_deg=phi - 90.0, loc=(r0 * 0.965 * math.cos(math.radians(phi)),
                                               r0 * 0.965 * math.sin(math.radians(phi)), base_z), tilt_x_deg=tilt)
        leaves.append(leaf)
    return leaves


def build_capital_figure(P, phi_deg, rng, coll):
    """Half-length female figure at a face centre (rotunda capitals only): torso rising from the upper leaves,
    head under the abacus, arms spread down to the inner helices."""
    R, H = P["R"], P["H"]
    r_fig = 1.24 * R
    # Round 7 (r6 review finding 2): the joint HEIGHTS are fractions of H but every transverse half-width used to
    # be a fraction of R, so raising the course 2.6 -> 3.0 produced a 15 % vertically stretched human. `fig_t` is
    # the same coefficient expressed per metre of capital: 0.545 = R 1.05 x the old F 1.35 / the 2.6 m design
    # height, so at H = 2.6 the figure is identical and at H = 3.0 it is a uniform 15.4 % larger.
    # Heights against ref_002 (H = 400 px, base y 785): hip y 619 = 0.415 H, waist 577 = 0.520, chest 529 = 0.640,
    # shoulders 505 = 0.700, neck 491 = 0.735, head centre 457 = 0.820, bun top 443 = 0.855.
    T = P.get("fig_t", 0.545) * H
    j = {
        "hip": (Vector((0, -0.06 * R, 0.415 * H)), (0.16 * T, 0.11 * T)),
        "waist": (Vector((0, -0.01 * R, 0.520 * H)), (0.13 * T, 0.09 * T)),
        "chest": (Vector((0, 0.04 * R, 0.640 * H)), (0.17 * T, 0.115 * T)),
        "neck": (Vector((0, 0.06 * R, 0.735 * H)), (0.06 * T, 0.06 * T)),
        "head": (Vector((0, 0.07 * R, 0.820 * H)), (0.11 * T, 0.12 * T)),
        "shl": (Vector((0.24 * T, 0.01 * R, 0.700 * H)), (0.07 * T, 0.07 * T)),
        "shr": (Vector((-0.24 * T, 0.01 * R, 0.700 * H)), (0.07 * T, 0.07 * T)),
        "ell": (Vector((0.42 * T, 0.07 * R, 0.620 * H)), (0.055 * T, 0.055 * T)),
        "elr": (Vector((-0.42 * T, 0.07 * R, 0.620 * H)), (0.055 * T, 0.055 * T)),
        "hal": (Vector((0.52 * T, 0.13 * R, 0.560 * H)), (0.05 * T, 0.045 * T)),
        "har": (Vector((-0.52 * T, 0.13 * R, 0.560 * H)), (0.05 * T, 0.045 * T)),
    }
    bones = [("hip", "waist"), ("waist", "chest"), ("chest", "neck"), ("neck", "head"), ("chest", "shl"), ("chest", "shr"),
             ("shl", "ell"), ("shr", "elr"), ("ell", "hal"), ("elr", "har")]
    fig = L.skin_figure(f"capfig_{int(phi_deg)}", j, bones, coll, subdiv=2)
    bun = L.sphere(f"capfig_bun_{int(phi_deg)}", 0.10 * T, coll, location=(0, -0.08 * R, 0.855 * H))
    parts = [fig, bun]
    for p in parts:
        place(p, rot_z_deg=phi_deg - 90.0, loc=(r_fig * math.cos(math.radians(phi_deg)), r_fig * math.sin(math.radians(phi_deg)), 0))
    return parts


def build_fleuron(P, phi_deg, coll):
    """Rosette on the abacus face centre (inner / colonnade capitals)."""
    R, H = P["R"], P["H"]
    rad = 0.17 * R
    prof = [(0.0, 0.0), (rad * 0.9, 0.0), (rad, 0.02 * R), (rad * 0.8, 0.06 * R), (rad * 0.35, 0.085 * R), (0.0, 0.10 * R)]
    def petals(th, t):
        return 1.0 + 0.10 * math.cos(8 * th) * t
    ros = L.revolve(f"fleuron_{int(phi_deg)}", L.resample_profile(prof, 10), segments=32, coll=coll, scale_fn=petals)
    # lying on the abacus face: axis -> +Y (outward) then rotate to phi
    ros.data.transform(Euler((math.radians(-90), 0, 0), "XYZ").to_matrix().to_4x4())
    r_face = 0.5 * P["abacus_across"] / math.sqrt(2) * 0.93 - 0.14 * R
    place(ros, rot_z_deg=phi_deg - 90.0, loc=(r_face * math.cos(math.radians(phi_deg)),
                                              r_face * math.sin(math.radians(phi_deg)), abacus_z(P, 0.409) * H))
    return ros


# Per-variant silhouette styles (QA-01-18: variants must differ at hero distance, not just in weathering seed)
CAPITAL_STYLE = {
    1: {},
    2: {"lower_w": 1.06, "volute_r": 1.15, "upper_len": 0.95, "clip_leaf": 3,
        "arc_mul": (1.08, 0.92), "proud_mul": (1.20, 0.85)},
    3: {"upper_len": 1.07, "volute_r": 0.88, "lower_w": 0.94, "tilt_add": 4.0, "helix_r": 1.2,
        "arc_mul": (0.90, 1.10), "proud_mul": (0.85, 1.25)},
}


def build_capital(typ, variant, coll, bake=True):
    P = dict(CAPITAL_PRESETS[typ])
    style = CAPITAL_STYLE.get(variant, {})
    for k, v in style.items():
        if k in P and isinstance(P[k], (int, float)):
            P[k] = P[k] * v
    for key, mul in (("arc_deg", "arc_mul"), ("proud", "proud_mul")):
        if mul in style:
            P[key] = tuple(a * b for a, b in zip(P[key], style[mul]))
    if "tilt_add" in style:
        P["leaf_tilt"] = (P["leaf_tilt"][0] + style["tilt_add"], P["leaf_tilt"][1] + style["tilt_add"] * 0.5)
    P["clip_leaf"] = style.get("clip_leaf", -1)
    R, H = P["R"], P["H"]
    rng = random.Random(7919 * variant + len(typ))
    work = L.work_collection()
    parts = []
    # Kalathos, scalloped so the slot between two neighbouring leaves bottoms out in a groove. cos(16*th) peaks at
    # every 22.5 deg, which is exactly where a leaf sits (lower row 0 + k*45, upper row 22.5 + k*45), so the sign must
    # be MINUS: full radius under each leaf (a firm seat for the union), the dip 11.25 deg away, in the gap.
    sc = P["scallop"]

    def bell_scallop(th, t):
        band = math.sin(math.pi * min(max((t - 0.03) / 0.80, 0.0), 1.0)) ** 0.6
        return 1.0 - sc * band * (0.55 - 0.45 * math.cos(16.0 * th))

    bell = L.revolve("bell", L.resample_profile([(r * R, z * H) for r, z in BELL_PROFILE], 44), segments=96,
                     coll=work, scale_fn=bell_scallop)
    parts.append(bell)
    parts.append(build_abacus("abacus", P, work))
    # leaves
    lower = build_leaf_ring(P, 8, 0.0, P["lower_z"], P["lower_len"], P["lower_w"], rng, work, "lo", 0)
    if P.get("clip_leaf", -1) >= 0:      # one damaged/short leaf tip on this variant
        lf = lower[P["clip_leaf"] % len(lower)]
        (x0, y0, z0), (x1, y1, z1) = L.bbox(lf)
        for v in lf.data.vertices:
            if v.co.z > z0 + 0.65 * (z1 - z0):
                v.co.z = z0 + 0.65 * (z1 - z0) + 0.15 * (v.co.z - z0 - 0.65 * (z1 - z0))
    parts += lower
    parts += build_leaf_ring(P, 8, 22.5, P["upper_z"], P["upper_len"], P["upper_w"], rng, work, "up", 1)
    # volutes: two per corner (one facing each side), stems rising from the gaps between the upper leaves.
    # The caulis has to start just BEHIND the top of the upper acanthus row, not at a fixed 0.26 H below the eye:
    # round 7 moved that row's top from 0.728 H to 0.600 H, which would have left the stem hanging in the open.
    up_top = P["upper_z"] + row_extent_H(P, 1)
    CAUL_DROP = (max(0.10, P["volute_z"] - up_top + 0.015), max(0.09, P["helix_z"] - up_top + 0.015))
    eye_r = P["volute_er"] * R
    eye_z = P["volute_z"] * H
    for face in (0, 90, 180, 270):
        for sign in (+1, -1):
            phi_c = face + sign * 45.0
            n_dir = face + sign * 22.0
            eye = Vector((eye_r * math.cos(math.radians(phi_c)), eye_r * math.sin(math.radians(phi_c)), eye_z))
            eye -= Vector((math.cos(math.radians(phi_c)), math.sin(math.radians(phi_c)), 0)) * 0.03 * R
            # local frame: X = radial at n_dir, Y = tangential (increasing phi)
            v = L.volute(f"vol_{face}_{sign}", eye=(0, 0, 0), radius=P["volute_r"] * H, turns=2.25,
                         band=(0.24 * R, 0.105 * R), stem_base=(-0.24 * R, -sign * 0.20 * R, -CAUL_DROP[0] * H),
                         stem_ctrl=(-0.13 * R, -sign * 0.09 * R, -0.40 * CAUL_DROP[0] * H), coll=work,
                         direction=sign, taper=0.55)
            place(v, rot_z_deg=n_dir, loc=eye)
            parts.append(v)
            # eye button: closes the spiral so the volute reads as a rolled scroll, not a length of pipe
            btn = L.sphere(f"volb_{face}_{sign}", 0.075 * R, work, scale=(0.85, 1.0, 1.0))
            place(btn, rot_z_deg=n_dir, loc=eye)
            parts.append(btn)
        # inner helices flanking the face centre, rolling toward the centre
        for sign in (+1, -1):
            phi_h = face + sign * 16.0
            eye = Vector((P["helix_er"] * R * math.cos(math.radians(phi_h)),
                          P["helix_er"] * R * math.sin(math.radians(phi_h)), P["helix_z"] * H))
            v = L.volute(f"hel_{face}_{sign}", eye=(0, 0, 0), radius=P["helix_r"] * H, turns=1.9,
                         band=(0.15 * R, 0.075 * R), stem_base=(-0.20 * R, sign * 0.16 * R, -CAUL_DROP[1] * H),
                         stem_ctrl=(-0.10 * R, sign * 0.06 * R, -0.38 * CAUL_DROP[1] * H), coll=work,
                         direction=-sign, taper=0.5)
            place(v, rot_z_deg=face + sign * 8.0, loc=eye)
            parts.append(v)
        if P["figure"]:
            parts += build_capital_figure(P, face, rng, work)
        else:
            parts.append(build_fleuron(P, face, work))
    # union into one cast-concrete surface, soften, weather
    t = time.time()
    voxel = P["voxel"] * (1.6 if FAST else 1.0)
    # smooth=1 at 0.30 (was 2 at 0.50): the round-3 pass rounded the leaf edges away with the undercuts
    hi = L.union_blob(parts, f"{typ}_v{variant}", voxel=voxel, smooth=1, smooth_factor=0.30, coll=work, adaptivity=0.35)
    print(f"[orn] {typ} v{variant}: remesh {L.tri_count(hi)} tris in {time.time() - t:.1f}s")
    L.displace_noise(hi, strength=0.005 * R, size=0.12 * R, seed=100 + variant, depth=2)
    L.displace_noise(hi, strength=0.0022 * R, size=0.025 * R, seed=200 + variant, depth=1)
    # LOD2: bell + abacus only
    bell2 = L.revolve("bell2", L.resample_profile([(r * R, z * H) for r, z in BELL_PROFILE], 8), segments=16, coll=work)
    ab2 = L.loft_rings("ab2", [[Vector((p.x * s, p.y * s, z * H)) for p in abacus_outline(R, P["abacus_across"], per_side=4)]
                                for s, z in ((0.87, 0.89), (1.0, 0.985), (1.0, 1.0))], work)
    lod2 = L.join([bell2, ab2], f"{typ}_v{variant}_lod2", work)
    return L.finalize_asset(hi, typ, variant, coll, bake=bake, bake_size=2048, lod2_obj=lod2, ao=True, cavity=True,
                            size_note=f"h {H} m, shaft top r {R} m, abacus {P['abacus_across']} m across corners")


# =============================================================================== FIGURES: shared drapery
def drapery_tube(name, sections, coll, folds=10, fold_amp=(0.02, 0.09), seed=0, nu=96, nz=90, power=2.3,
                 fold_side=None, close_top=True, close_bottom=True, sharp=0.7):
    """Lofted garment: sections = list of (z, cx, cy, a, b) bottom->top (centre, half-widths). Vertical folds as
    radial ridges whose amplitude grows from fold_amp[0] at the top to fold_amp[1] at the hem. fold_side: None = all
    around, or (angle_deg, half_width_deg) to restrict the folds to one side (the visible one)."""
    rng = random.Random(seed)
    ph0, ph1, ph2 = rng.uniform(0, TAU), rng.uniform(0, TAU), rng.uniform(0, TAU)
    wob = rng.uniform(0.8, 1.6)
    zs = [sc[0] for sc in sections]
    z0, z1 = zs[0], zs[-1]
    def interp(z):
        for i in range(len(sections) - 1):
            za, zb = sections[i][0], sections[i + 1][0]
            if za <= z <= zb:
                f = 0.0 if zb == za else (z - za) / (zb - za)
                f = f * f * (3 - 2 * f)   # smoothstep between sections
                return [sections[i][k] * (1 - f) + sections[i + 1][k] * f for k in range(1, 5)]
        return list(sections[-1][1:])
    def se(c, k):
        return math.copysign(abs(c) ** (2.0 / k), c)
    def fn(u, v):
        th = u * TAU
        z = z0 + (z1 - z0) * v
        cx, cy, a, b = interp(z)
        t_top = (z - z0) / (z1 - z0)
        amp = fold_amp[1] * (1 - t_top) ** 1.3 + fold_amp[0] * t_top
        # ridges: sharp folds + a slow undulation; slight drift with height
        phase = ph0 + 0.35 * math.sin(z * wob + ph1)
        ridge = 2.0 * abs(math.cos(0.5 * folds * th + phase)) ** sharp - 1.0
        slow = 0.35 * math.cos(3 * th + ph2)
        f = ridge * 0.75 + slow
        if fold_side is not None:
            c, hw = math.radians(fold_side[0]), math.radians(fold_side[1])
            d = abs(((th - c + math.pi) % TAU) - math.pi)
            f *= max(0.0, min(1.0, (hw - d) / (0.3 * hw) + 1.0)) if d > hw * 0.7 else 1.0
        r = 1.0 + amp * f
        return (cx + a * r * se(math.cos(th), power), cy + b * r * se(math.sin(th), power), z)
    obj = L.surface(name, fn, nu, nz, coll, wrap_u=True, smooth=True, cap_v0=close_bottom, cap_v1=close_top)
    return obj


def build_maiden(variant, coll, bake=True):
    """Ellerhusen weeping maiden. Built in a feet frame (feet at z=0, box corner edge at (0,-0.32), rim at rim_z), then
    moved into ARCH's socket frame: the socket sits ON THE BOX LID 0.78 m inward from the corner along the diagonal
    (arch_build.py planter box), +Y = outward diagonal. So in the delivered mesh the origin is on the lid, the box
    corner edge is at (0, +0.78, 0), the figure hangs down the outside of the corner (feet at z = -rim_z) with the
    forearms on the rim (z ~ 0) and the head bowed over the corner into the box (QA-01-13)."""
    rng = random.Random(4242 + variant)
    work = L.work_collection()
    height = {1: 4.30, 2: 4.22, 3: 4.36}.get(variant, 4.3)
    S = height / 1.75
    lean = {1: 0.22, 2: 0.30, 3: 0.26}.get(variant, 0.24) + rng.uniform(-0.02, 0.02)
    bow = {1: 0.50, 2: 0.58, 3: 0.44}.get(variant, 0.50)
    turn = {1: 0.0, 2: 12.0, 3: -9.0}.get(variant, 0.0)
    rim_z = 3.30
    corner = Vector((0.0, -0.32, 0.0))
    def rim_point(side, d):
        return corner + Vector((side * 0.7071, -0.7071, 0.0)) * d
    parts = []
    k = height / 4.5
    j = {
        "pelvis": (Vector((0, 0.0, 2.40 * k)), (0.36, 0.23)),
        "hipL": (Vector((0.20, 0.0, 2.30 * k)), (0.21, 0.19)), "hipR": (Vector((-0.20, 0.0, 2.30 * k)), (0.21, 0.19)),
        "kneeL": (Vector((0.18, -0.02, 1.25 * k)), (0.16, 0.16)), "kneeR": (Vector((-0.17, 0.0, 1.22 * k)), (0.16, 0.16)),
        "ankL": (Vector((0.17, 0.02, 0.25)), (0.10, 0.11)), "ankR": (Vector((-0.16, 0.04, 0.25)), (0.10, 0.11)),
        "waist": (Vector((0, -0.03 - lean * 0.3, 2.78 * k)), (0.27, 0.18)),
        "chest": (Vector((0, -lean * 0.7, 3.28 * k)), (0.35, 0.22)),
        # hunched over the rim (refs 187/163): the shoulders come up, the head sinks between them and bows forward
        "shL": (Vector((0.55, -lean, 3.66 * k)), (0.16, 0.15)), "shR": (Vector((-0.55, -lean, 3.66 * k)), (0.16, 0.15)),
        "neck": (Vector((0, -lean - 0.09, 3.70 * k)), (0.13, 0.13)),
        "head": (Vector((0, -lean - bow, 3.74 * k)), (0.25, 0.28)),
    }
    # forearms folded onto the rim near the corner, elbows out (refs 163/187)
    for side, tag in ((1, "L"), (-1, "R")):
        el = rim_point(side, 0.55) + Vector((side * 0.05, 0.02, rim_z + 0.09))
        ha = rim_point(side, 0.12) + Vector((-side * 0.10, -0.22, rim_z + 0.07))
        j["el" + tag] = (el, (0.11, 0.10))
        j["ha" + tag] = (ha, (0.09, 0.05))
    bones = [("pelvis", "hipL"), ("pelvis", "hipR"), ("hipL", "kneeL"), ("hipR", "kneeR"), ("kneeL", "ankL"),
             ("kneeR", "ankR"), ("pelvis", "waist"), ("waist", "chest"), ("chest", "shL"), ("chest", "shR"),
             ("chest", "neck"), ("neck", "head"), ("shL", "elL"), ("shR", "elR"), ("elL", "haL"), ("elR", "haR")]
    body = L.skin_figure("maiden_body", j, bones, work, subdiv=2)
    parts.append(body)
    hc = j["head"][0]
    hair = L.sphere("maiden_hair", 0.23, work, location=hc + Vector((0, 0.10, 0.08)), scale=(1.05, 0.95, 0.85))
    bun = L.sphere("maiden_bun", 0.13, work, location=hc + Vector((0, 0.27, 0.16)))
    parts += [hair, bun]
    if turn:
        m = Matrix.Translation(hc) @ Euler((0, 0, math.radians(turn)), "XYZ").to_matrix().to_4x4() @ Matrix.Translation(-hc)
        for o in (hair, bun):
            o.data.transform(m)
    ly = -lean
    hem = {1: 0.62, 2: 0.68, 3: 0.57}.get(variant, 0.62)
    sections = [
        (0.03, 0.0, 0.02, hem, hem * 0.87),
        (0.60, 0.0, 0.01, 0.55, 0.47),
        (1.30 * k, 0.0, 0.0, 0.48, 0.40),
        (2.10 * k, 0.0, 0.0, 0.44, 0.33),
        (2.45 * k, 0.0, 0.0, 0.43, 0.30),
        (2.80 * k, 0.0, ly * 0.3, 0.37, 0.26),
        (3.30 * k, 0.0, ly * 0.65, 0.45, 0.28),
        (3.55 * k, 0.0, ly * 0.9, 0.56, 0.27),
        (3.68 * k, 0.0, ly, 0.44, 0.24),
        (3.78 * k, 0.0, ly, 0.26, 0.19),
        (3.86 * k, 0.0, ly - 0.03, 0.14, 0.14),
    ]
    folds = {1: 10, 2: 12, 3: 9}.get(variant, 10)
    gar = drapery_tube("maiden_peplos", sections, work, folds=folds, fold_amp=(0.035, 0.155 + rng.uniform(-0.012, 0.018)),
                       seed=variant * 31, fold_side=(90.0, 120.0), sharp=0.6)
    parts.append(gar)
    zo = {1: 2.25, 2: 2.45, 3: 2.10}.get(variant, 2.3) * k
    over = drapery_tube("maiden_overfold", [(zo, 0.0, 0.03, 0.46, 0.34),
                                            (zo + 0.25, 0.0, 0.03, 0.44, 0.32),
                                            (2.80 * k, 0.0, ly * 0.3 + 0.03, 0.39, 0.28),
                                            (3.30 * k, 0.0, ly * 0.65 + 0.03, 0.47, 0.30),
                                            (3.55 * k, 0.0, ly * 0.9 + 0.02, 0.57, 0.28),
                                            (3.70 * k, 0.0, ly, 0.42, 0.23)],
                        work, folds=folds + 2, fold_amp=(0.03, 0.10), seed=variant * 31 + 5, fold_side=(90.0, 120.0), nz=40)
    for v in over.data.vertices:
        if v.co.z < zo + 0.3:
            ang = math.atan2(v.co.y, v.co.x)
            v.co.z -= 0.12 * abs(math.cos(ang)) * max(0.0, 1.0 - (v.co.z - zo) / 0.3)
    parts.append(over)
    for side, tag in ((1, "L"), (-1, "R")):
        el = j["el" + tag][0]
        casc = drapery_tube(f"maiden_casc{tag}", [(el.z - 0.9, el.x + side * 0.05, el.y + 0.08, 0.16, 0.13),
                                                   (el.z - 0.3, el.x, el.y + 0.04, 0.15, 0.12),
                                                   (el.z + 0.05, el.x, el.y, 0.12, 0.11)],
                            work, folds=5, fold_amp=(0.02, 0.10), seed=variant * 7 + side, nu=40, nz=20)
        parts.append(casc)
    t = time.time()
    hi = L.union_blob(parts, f"maiden_v{variant}", voxel=(0.03 if FAST else 0.02), smooth=3, smooth_factor=0.5, coll=work)
    print(f"[orn] maiden v{variant}: remesh {L.tri_count(hi)} tris in {time.time() - t:.1f}s")
    L.displace_noise(hi, strength=0.010, size=0.35, seed=300 + variant, depth=2)
    L.displace_noise(hi, strength=0.003, size=0.05, seed=400 + variant, depth=1)
    # feet frame -> socket frame: corner edge (0,-0.32, rim_z) must land on (0, +0.78, 0)
    hi.data.transform(Matrix.Translation((0.0, 0.78 + 0.32, -rim_z)))
    return L.finalize_asset(hi, "maiden", variant, coll, bake=bake, bake_size=2048, y_mode="asis",
                            size_note=f"{height} m standing; ORIGIN ON THE BOX LID (ARCH socket): box corner edge at (0, +0.78, 0), feet at z=-{rim_z}, forearms on the rim at z~0",
                            extra_props={"rim_height": rim_z, "box_corner_y": 0.78, "feet_z": -rim_z,
                                         "origin_note": "socket frame = on the box lid 0.78 m inward from the corner (arch_build planter box); NOT bottom-centre"})


# =============================================================================== ATTIC CORNER FIGURES (6.7 m)
def human_joints(S, front=1.0, pose="attic_male"):
    """Joint dictionary for a standing figure in a 1.75 m frame scaled by S. Faces +Y * front."""
    f = front
    J = {
        "pelvis": ((0, 0, 0.95), (0.17, 0.11)),
        "hipL": ((0.10, 0, 0.90), (0.105, 0.10)), "hipR": ((-0.10, 0, 0.90), (0.105, 0.10)),
        "kneeL": ((0.10, 0.01 * f, 0.50), (0.075, 0.08)), "kneeR": ((-0.11, -0.02 * f, 0.50), (0.075, 0.08)),
        "ankL": ((0.10, 0.02 * f, 0.08), (0.05, 0.06)), "ankR": ((-0.12, -0.03 * f, 0.08), (0.05, 0.06)),
        "footL": ((0.10, 0.13 * f, 0.03), (0.05, 0.03)), "footR": ((-0.13, 0.08 * f, 0.03), (0.05, 0.03)),
        "waist": ((0, 0.0, 1.12), (0.15, 0.10)),
        "chest": ((0, 0.01 * f, 1.33), (0.195, 0.125)),
        "shL": ((0.215, 0.0, 1.46), (0.075, 0.07)), "shR": ((-0.215, 0.0, 1.46), (0.075, 0.07)),
        "neck": ((0, 0.015 * f, 1.53), (0.06, 0.06)),
        "head": ((0, 0.035 * f, 1.655), (0.115, 0.125)),
    }
    if pose == "attic_male":       # both arms raised, hands at the chest / opposite shoulder (attic_corner_figure_1-2)
        J.update({"elL": ((0.37, 0.09 * f, 1.30), (0.06, 0.06)), "haL": ((0.02, 0.17 * f, 1.31), (0.055, 0.045)),
                  "elR": ((-0.36, 0.11 * f, 1.33), (0.06, 0.06)), "haR": ((-0.04, 0.16 * f, 1.44), (0.055, 0.045))})
    elif pose == "attic_female":   # one arm across the chest, the other down holding the drapery
        J.update({"elL": ((0.30, 0.12 * f, 1.26), (0.055, 0.055)), "haL": ((-0.07, 0.17 * f, 1.39), (0.05, 0.04)),
                  "elR": ((-0.27, 0.05 * f, 1.16), (0.055, 0.055)), "haR": ((-0.21, 0.13 * f, 0.96), (0.05, 0.04))})
    elif pose == "winged":         # arms down-forward holding cornucopias at the hips
        J.update({"elL": ((0.29, 0.06 * f, 1.08), (0.055, 0.055)), "haL": ((0.24, 0.16 * f, 0.92), (0.05, 0.04)),
                  "elR": ((-0.29, 0.06 * f, 1.08), (0.055, 0.055)), "haR": ((-0.24, 0.16 * f, 0.92), (0.05, 0.04))})
    elif pose == "arms_up":        # both arms raised above the head (central figure, zimm_panel_1)
        J.update({"elL": ((0.34, 0.02 * f, 1.62), (0.055, 0.055)), "haL": ((0.22, 0.03 * f, 1.90), (0.05, 0.04)),
                  "elR": ((-0.36, 0.02 * f, 1.60), (0.055, 0.055)), "haR": ((-0.20, 0.03 * f, 1.92), (0.05, 0.04))})
    elif pose == "stride":         # striding, one arm thrust forward, the other back
        J.update({"kneeL": ((0.28, 0.02 * f, 0.52), (0.075, 0.08)), "ankL": ((0.42, 0.02 * f, 0.10), (0.05, 0.06)),
                  "footL": ((0.50, 0.08 * f, 0.03), (0.05, 0.03)),
                  "kneeR": ((-0.20, 0.0, 0.50), (0.075, 0.08)), "ankR": ((-0.36, 0.0, 0.08), (0.05, 0.06)),
                  "footR": ((-0.44, 0.04 * f, 0.03), (0.05, 0.03)),
                  "elL": ((0.42, 0.06 * f, 1.42), (0.055, 0.055)), "haL": ((0.66, 0.08 * f, 1.52), (0.05, 0.04)),
                  "elR": ((-0.36, 0.0, 1.20), (0.055, 0.055)), "haR": ((-0.48, 0.02 * f, 0.98), (0.05, 0.04))})
    elif pose == "kneel":          # one knee down, torso upright, one arm raised in defence
        J.update({"pelvis": ((0, 0, 0.62), (0.17, 0.11)), "hipL": ((0.10, 0, 0.58), (0.105, 0.10)), "hipR": ((-0.10, 0, 0.58), (0.105, 0.10)),
                  "kneeL": ((0.34, 0.02 * f, 0.30), (0.075, 0.08)), "ankL": ((0.22, 0.0, 0.06), (0.05, 0.06)), "footL": ((0.30, 0.06 * f, 0.03), (0.05, 0.03)),
                  "kneeR": ((-0.22, 0.0, 0.08), (0.075, 0.08)), "ankR": ((-0.50, 0.0, 0.08), (0.05, 0.06)), "footR": ((-0.58, 0.02 * f, 0.04), (0.05, 0.03)),
                  "waist": ((0, 0, 0.80), (0.15, 0.10)), "chest": ((0.03, 0.01 * f, 1.02), (0.195, 0.125)),
                  "shL": ((0.24, 0.0, 1.15), (0.075, 0.07)), "shR": ((-0.19, 0.0, 1.15), (0.075, 0.07)),
                  "neck": ((0.03, 0.015 * f, 1.22), (0.06, 0.06)), "head": ((0.05, 0.035 * f, 1.35), (0.115, 0.125)),
                  "elL": ((0.42, 0.05 * f, 1.35), (0.055, 0.055)), "haL": ((0.30, 0.06 * f, 1.60), (0.05, 0.04)),
                  "elR": ((-0.36, 0.02 * f, 0.95), (0.055, 0.055)), "haR": ((-0.28, 0.08 * f, 0.72), (0.05, 0.04))})
    elif pose == "arms_out":       # arms spread diagonally up (garland bearer / dancer)
        J.update({"elL": ((0.44, 0.03 * f, 1.60), (0.055, 0.055)), "haL": ((0.66, 0.05 * f, 1.78), (0.05, 0.04)),
                  "elR": ((-0.44, 0.03 * f, 1.58), (0.055, 0.055)), "haR": ((-0.68, 0.05 * f, 1.74), (0.05, 0.04))})
    out = {k: (Vector(v[0]) * S, (v[1][0] * S, v[1][1] * S)) for k, v in J.items()}
    return out


HUMAN_BONES = [("pelvis", "hipL"), ("pelvis", "hipR"), ("hipL", "kneeL"), ("hipR", "kneeR"), ("kneeL", "ankL"),
               ("kneeR", "ankR"), ("ankL", "footL"), ("ankR", "footR"), ("pelvis", "waist"), ("waist", "chest"),
               ("chest", "shL"), ("chest", "shR"), ("chest", "neck"), ("neck", "head"), ("shL", "elL"), ("shR", "elR"),
               ("elL", "haL"), ("elR", "haR")]


def narrow(secs, f):
    """Scale the half-widths of a drapery section list. QA-02-10: the corner figure's wrap was 2.07 m wide on a
    6.7 m figure (a_hem 0.27 * S) which turned the whole figure into a bell; a standing draped figure that tall
    is ~1.2 m across the cloth, ~2.2 m including the flanking cascades."""
    return [(z, cx, cy, a * f, b * f) for (z, cx, cy, a, b) in secs]


def attic_side_cascades(S, work, variant, top_z=1.44, hem_z=0.05, out=0.42, a=0.20, b=0.135, cy=-0.05,
                        folds=6, fold_amp=(0.16, 0.36)):
    """QA-02-10: the two heavy cloth panels that hang from behind the figure's arms down past the knees on BOTH
    sides (attic_corner_figure_1 / ref 085). They are what gives the corner figure its wide, broken silhouette and
    the deep vertical shadow channels that survive a near-normal sun; without them a nude torso in a niche is a
    smooth tapered mass = the 'bollard' QA saw. Fold depth here is a * fold_amp[1] ~ 0.26-0.28 m at the hem."""
    made = []
    for side in (1, -1):
        cx = side * out * S
        secs = [(hem_z * S, cx, cy * S, a * S * 0.98, b * S),
                (0.30 * S, cx + side * 0.02 * S, cy * S, a * S, b * S * 1.03),
                (0.70 * S, cx + side * 0.01 * S, cy * S * 0.9, a * S * 0.92, b * S * 0.98),
                (1.05 * S, cx, cy * S * 0.8, a * S * 0.80, b * S * 0.88),
                (top_z * S, cx - side * 0.06 * S, cy * S * 0.6, a * S * 0.52, b * S * 0.62)]
        made.append(drapery_tube(f"attic_cascade{side}", secs, work, folds=folds, fold_amp=fold_amp,
                                 seed=variant * 23 + side, nu=72, nz=64, power=2.5, sharp=0.5))
    return made


def build_attic_figure(variant, coll, bake=True):
    """Attic corner figure ('Contemplation / Wonderment / Meditation'), 6.7 m, standing frontal in its niche,
    facing +Y. Odd variants male (nude torso, wrapped cloth from the waist, mantle behind), even variants female
    (fully draped)."""
    rng = random.Random(9000 + variant)
    work = L.work_collection()
    S = 6.7 / 1.75
    male = (variant % 2 == 1)
    J = human_joints(S, front=1.0, pose="attic_male" if male else "attic_female")
    # per-variant head turn / tilt
    J["head"] = (J["head"][0] + Vector((rng.uniform(-0.06, 0.06), 0.0, rng.uniform(-0.04, 0.04))), J["head"][1])
    body = L.skin_figure("attic_body", J, HUMAN_BONES, work, subdiv=2)
    parts = [body]
    hc = J["head"][0]
    if male:
        parts.append(L.sphere("attic_hair", 0.105 * S, work, location=hc + Vector((0, -0.02 * S, 0.03 * S)), scale=(1.0, 0.95, 0.9)))
        # wrapped cloth from the waist down, heavy vertical folds on the front
        secs = [(0.03 * S, 0.0, 0.02 * S, 0.27 * S, 0.21 * S), (0.30 * S, 0.0, 0.01 * S, 0.24 * S, 0.18 * S),
                (0.60 * S, 0.0, 0.0, 0.22 * S, 0.16 * S), (0.92 * S, 0.0, 0.0, 0.215 * S, 0.15 * S),
                (1.08 * S, 0.0, 0.0, 0.18 * S, 0.12 * S), (1.14 * S, 0.0, 0.0, 0.16 * S, 0.11 * S)]
        parts.append(drapery_tube("attic_wrap", narrow(secs, 0.56), work, folds=rng.choice([6, 7, 8]), fold_amp=(0.03, 0.12),
                                  seed=variant * 13, fold_side=(90.0, 130.0), nu=80, nz=60, sharp=0.6))
        # mantle hanging behind the shoulders to the calves, seen beside the torso
        msecs = [(0.35 * S, 0.0, -0.12 * S, 0.34 * S, 0.07 * S), (0.9 * S, 0.0, -0.12 * S, 0.33 * S, 0.075 * S),
                 (1.30 * S, 0.0, -0.10 * S, 0.30 * S, 0.07 * S), (1.47 * S, 0.0, -0.06 * S, 0.24 * S, 0.06 * S)]
        parts.append(drapery_tube("attic_mantle", narrow(msecs, 0.56), work, folds=9, fold_amp=(0.06, 0.16), seed=variant * 17,
                                  nu=64, nz=40, power=3.0, sharp=0.55))
        parts += attic_side_cascades(S, work, variant, top_z=1.44, hem_z=0.05, out=0.325, a=0.115, b=0.105,
                                     cy=-0.05, folds=5, fold_amp=(0.20, 0.44))
    else:
        parts.append(L.sphere("attic_hair", 0.115 * S, work, location=hc + Vector((0, -0.02 * S, 0.035 * S)), scale=(1.05, 1.0, 0.85)))
        parts.append(L.sphere("attic_bun", 0.06 * S, work, location=hc + Vector((0, -0.11 * S, 0.06 * S))))
        secs = [(0.03 * S, 0.0, 0.02 * S, 0.29 * S, 0.23 * S), (0.35 * S, 0.0, 0.01 * S, 0.25 * S, 0.19 * S),
                (0.70 * S, 0.0, 0.0, 0.22 * S, 0.165 * S), (0.95 * S, 0.0, 0.0, 0.215 * S, 0.15 * S),
                (1.12 * S, 0.0, 0.0, 0.19 * S, 0.13 * S), (1.33 * S, 0.0, 0.01 * S, 0.22 * S, 0.145 * S),
                (1.44 * S, 0.0, 0.01 * S, 0.245 * S, 0.12 * S), (1.50 * S, 0.0, 0.01 * S, 0.14 * S, 0.09 * S),
                (1.55 * S, 0.0, 0.015 * S, 0.07 * S, 0.07 * S)]
        parts.append(drapery_tube("attic_gown", narrow(secs, 0.57), work, folds=rng.choice([9, 10, 11]), fold_amp=(0.02, 0.10),
                                  seed=variant * 13, fold_side=(90.0, 140.0), nu=96, nz=80, sharp=0.6))
        # overfold to the hips
        osecs = [(0.98 * S, 0.0, 0.03 * S, 0.24 * S, 0.17 * S), (1.15 * S, 0.0, 0.02 * S, 0.21 * S, 0.15 * S),
                 (1.34 * S, 0.0, 0.02 * S, 0.235 * S, 0.155 * S), (1.45 * S, 0.0, 0.02 * S, 0.25 * S, 0.13 * S),
                 (1.50 * S, 0.0, 0.02 * S, 0.15 * S, 0.10 * S)]
        parts.append(drapery_tube("attic_over", narrow(osecs, 0.57), work, folds=12, fold_amp=(0.02, 0.08), seed=variant * 19,
                                  fold_side=(90.0, 140.0), nu=80, nz=30))
        parts += attic_side_cascades(S, work, variant, top_z=1.40, hem_z=0.04, out=0.315, a=0.105, b=0.095,
                                     cy=-0.04, folds=5, fold_amp=(0.18, 0.42))
    t = time.time()
    # QA-02-10: smooth=3 at 2.8 cm closed the arm-to-torso gaps and the drapery channels, which is what made the
    # figure read as a featureless bollard at cam05. One light pass at 2.2 cm keeps the silhouette breaks open.
    hi = L.union_blob(parts, f"attic_figure_v{variant}", voxel=(0.045 if FAST else 0.022), smooth=1,
                      smooth_factor=0.25, coll=work)
    print(f"[orn] attic_figure v{variant}: remesh {L.tri_count(hi)} tris in {time.time() - t:.1f}s")
    L.displace_noise(hi, strength=0.014, size=0.5, seed=500 + variant, depth=2)
    L.displace_noise(hi, strength=0.004, size=0.07, seed=600 + variant, depth=1)
    return L.finalize_asset(hi, "attic_figure", variant, coll, bake=bake, bake_size=2048, y_mode="keep",
                            size_note="6.7 m (22 ft) standing, faces +Y; odd variants male, even female; "
                                      "flanking cloth cascades (attic_corner_figure_1) break the silhouette")


def build_winged_figure(variant, coll, bake=True):
    """'Priestess of Culture' (Herbert Adams), 4.6 m, winged and draped, holding paired cornucopias, stands on the
    inner entablature block facing the rotunda centre = local -Y (socket +Y is outward)."""
    rng = random.Random(7000 + variant)
    work = L.work_collection()
    S = 4.6 / 1.75
    J = human_joints(S, front=-1.0, pose="winged")
    J["head"] = (J["head"][0] + Vector((0, 0.0, -0.02 * S)), J["head"][1])   # gazes downward: head slightly forward
    J["head"] = (J["head"][0] + Vector((0, -0.03 * S, 0)), J["head"][1])
    body = L.skin_figure("winged_body", J, HUMAN_BONES, work, subdiv=2)
    parts = [body]
    hc = J["head"][0]
    parts.append(L.sphere("winged_hair", 0.11 * S, work, location=hc + Vector((0, 0.03 * S, 0.035 * S)), scale=(1.05, 1.0, 0.85)))
    # gown with front folds (front = -Y -> angle 270)
    secs = [(0.03 * S, 0.0, -0.01 * S, 0.30 * S, 0.24 * S), (0.40 * S, 0.0, -0.01 * S, 0.25 * S, 0.19 * S),
            (0.80 * S, 0.0, 0.0, 0.22 * S, 0.16 * S), (1.10 * S, 0.0, 0.0, 0.19 * S, 0.13 * S),
            (1.33 * S, 0.0, -0.01 * S, 0.22 * S, 0.145 * S), (1.45 * S, 0.0, -0.01 * S, 0.245 * S, 0.12 * S),
            (1.51 * S, 0.0, -0.01 * S, 0.13 * S, 0.09 * S), (1.56 * S, 0.0, -0.015 * S, 0.07 * S, 0.07 * S)]
    parts.append(drapery_tube("winged_gown", secs, work, folds=rng.choice([10, 11, 12]), fold_amp=(0.02, 0.10),
                              seed=variant * 23, fold_side=(270.0, 140.0), nu=96, nz=80, sharp=0.6))
    # wings: two tall fluted slabs behind the shoulders, rounded top above the head, tips at the calves
    for side in (1, -1):
        x = side * 0.19 * S
        wsecs = [(0.35 * S, x + side * 0.02 * S, 0.18 * S, 0.05 * S, 0.03 * S),
                 (0.7 * S, x + side * 0.04 * S, 0.19 * S, 0.09 * S, 0.035 * S),
                 (1.1 * S, x + side * 0.06 * S, 0.20 * S, 0.12 * S, 0.04 * S),
                 (1.45 * S, x + side * 0.07 * S, 0.21 * S, 0.13 * S, 0.045 * S),
                 (1.72 * S, x + side * 0.07 * S, 0.21 * S, 0.11 * S, 0.04 * S),
                 (1.88 * S, x + side * 0.05 * S, 0.20 * S, 0.05 * S, 0.025 * S)]
        parts.append(drapery_tube(f"wing{side}", wsecs, work, folds=7, fold_amp=(0.10, 0.10), seed=variant * 5 + side,
                                  nu=48, nz=40, power=3.2, sharp=0.5))
    # cornucopias: tapered horns from the hands, curling up and outward
    for side in (1, -1):
        h = J["haL" if side > 0 else "haR"][0]
        path = L.bezier(h + Vector((0, -0.02 * S, -0.06 * S)), h + Vector((side * 0.04 * S, -0.08 * S, 0.10 * S)),
                        h + Vector((side * 0.10 * S, -0.10 * S, 0.22 * S)), h + Vector((side * 0.14 * S, -0.06 * S, 0.30 * S)), 14)
        parts.append(L.tube(f"horn{side}", path, lambda t: 0.02 * S + 0.045 * S * t, work, segments=12))
    t = time.time()
    hi = L.union_blob(parts, f"winged_figure_v{variant}", voxel=(0.035 if FAST else 0.022), smooth=3, coll=work)
    print(f"[orn] winged_figure v{variant}: remesh {L.tri_count(hi)} tris in {time.time() - t:.1f}s")
    L.displace_noise(hi, strength=0.010, size=0.4, seed=700 + variant, depth=2)
    L.displace_noise(hi, strength=0.003, size=0.06, seed=800 + variant, depth=1)
    return L.finalize_asset(hi, "winged_figure", variant, coll, bake=bake, bake_size=2048, y_mode="keep",
                            size_note="4.6 m (15 ft); faces -Y (toward the rotunda centre), wings toward +Y")


# =============================================================================== URNS, KEYSTONE, FINIAL, ROSETTE
def build_urn(variant, coll, bake=True):
    """Podium urn, 3.0 m incl. plinth (SFGate '10-foot urns'): gadrooned ovoid body, figure band at the shoulder,
    two loop handles, domed lid with a knob, on a square plinth (urn_pedestal_1-2)."""
    rng = random.Random(5000 + variant)
    work = L.work_collection()
    k = 1.0 + rng.uniform(-0.03, 0.03)
    parts = [L.box("urn_plinth", (0.95, 0.95, 0.32), work, location=(0, 0, 0.16), bevel=0.02)]
    foot = [(0.40, 0.32), (0.40, 0.40), (0.30, 0.44), (0.22, 0.52), (0.19, 0.60), (0.24, 0.66), (0.30, 0.70)]
    body = [(0.30, 0.70), (0.42, 0.80), (0.58, 1.00), (0.70, 1.30), (0.745, 1.60), (0.72, 1.85), (0.66, 2.05),
            (0.58, 2.20), (0.44, 2.32), (0.36, 2.40), (0.40, 2.46), (0.46, 2.50), (0.46, 2.55)]
    lid = [(0.46, 2.55), (0.40, 2.60), (0.34, 2.72), (0.22, 2.84), (0.12, 2.90), (0.12, 2.94), (0.05, 3.0), (0.0, 3.0)]
    def gadroon(th, t):
        z = 0.32 + t * (2.55 - 0.32)   # approximate z of the resampled profile
        g = 1.0 if z < 1.45 else max(0.0, 1.0 - (z - 1.45) / 0.35)
        band = 1.0 + 0.045 * math.cos(24 * th) * (0.5 + 0.5 * g) if 0.75 < z < 1.85 else 1.0
        fig = 1.0 + 0.03 * max(0.0, math.sin(9 * th + 1.7) * math.sin(4 * th)) if 1.85 <= z <= 2.10 else 1.0
        return band * fig
    prof = L.resample_profile(foot + body[1:], 48)
    parts.append(L.revolve("urn_body", [(r * k, z) for r, z in prof], segments=96, coll=work, scale_fn=gadroon))
    parts.append(L.revolve("urn_lid", L.resample_profile([(r * k, z) for r, z in lid], 16), segments=48, coll=work))
    # shoulder band ridge lines
    for zb in (1.83, 2.12):
        parts.append(L.revolve(f"urn_ring{zb}", [(0.60 * k, zb - 0.025), (0.71 * k, zb - 0.02), (0.72 * k, zb), (0.71 * k, zb + 0.02), (0.60 * k, zb + 0.025)], segments=64, coll=work))
    # handles: loops from the neck out and down to the shoulder
    for side in (1, -1):
        path = L.bezier((side * 0.40 * k, 0, 2.42), (side * 0.85 * k, 0, 2.55), (side * 0.95 * k, 0, 2.20), (side * 0.66 * k, 0, 1.98), 16)
        parts.append(L.tube(f"urn_handle{side}", path, lambda t: 0.055, work, segments=12))
        parts.append(L.sphere(f"urn_boss{side}", 0.075, work, location=(side * 0.68 * k, 0, 1.98)))
    hi = L.union_blob(parts, f"urn_v{variant}", voxel=(0.02 if FAST else 0.012), smooth=2, coll=work)
    L.displace_noise(hi, strength=0.006, size=0.15, seed=900 + variant, depth=2)
    L.displace_noise(hi, strength=0.002, size=0.03, seed=950 + variant, depth=1)
    return L.finalize_asset(hi, "urn", variant, coll, bake=bake, bake_size=2048, budgets=L.BUDGETS["urn"],
                            size_note="podium urn 3.0 m incl. 0.32 m plinth, 1.5 m across the body")


def build_urn_niche(variant, coll, bake=True):
    """Drum-level urn on the attic corner blocks (DPR 'Roman funerary urns'), ~1.6 m: bowl with an imbricated scale
    pattern, small handles, on a low plinth (drum_urn_finial_1-2)."""
    rng = random.Random(5100 + variant)
    work = L.work_collection()
    k = 1.0 + rng.uniform(-0.03, 0.03)
    parts = [L.box("un_plinth", (0.7, 0.7, 0.22), work, location=(0, 0, 0.11), bevel=0.015)]
    prof = [(0.28, 0.22), (0.20, 0.30), (0.16, 0.40), (0.22, 0.48), (0.42, 0.62), (0.56, 0.85), (0.60, 1.05),
            (0.58, 1.25), (0.53, 1.40), (0.52, 1.47), (0.58, 1.52), (0.60, 1.58), (0.56, 1.60), (0.0, 1.60)]
    def scales(th, t):
        z = 0.22 + t * (1.60 - 0.22)
        if not (0.55 < z < 1.35):
            return 1.0
        row = int((z - 0.55) / 0.13)
        u = (th / TAU * 22 + (0.5 if row % 2 else 0.0)) % 1.0
        v = ((z - 0.55) / 0.13) % 1.0
        d = ((u - 0.5) * 1.4) ** 2 + (v - 0.35) ** 2
        return 1.0 + 0.04 * max(0.0, 1.0 - d * 3.0)
    parts.append(L.revolve("un_body", [(r * k, z) for r, z in L.resample_profile(prof, 56)], segments=88, coll=work, scale_fn=scales))
    for side in (1, -1):
        path = L.bezier((side * 0.50 * k, 0, 1.42), (side * 0.75 * k, 0, 1.50), (side * 0.78 * k, 0, 1.20), (side * 0.58 * k, 0, 1.05), 14)
        parts.append(L.tube(f"un_handle{side}", path, lambda t: 0.04, work, segments=10))
    hi = L.union_blob(parts, f"urn_niche_v{variant}", voxel=(0.015 if FAST else 0.009), smooth=2, coll=work)
    L.displace_noise(hi, strength=0.004, size=0.10, seed=1000 + variant, depth=2)
    return L.finalize_asset(hi, "urn_niche", variant, coll, bake=bake, bake_size=1024, budgets=L.BUDGETS["urn"],
                            size_note="attic/drum corner urn 1.6 m")


def build_urn_tub(variant, coll, bake=True):
    """Large planter tub on the colonnade pylons (urn_tub_1): wide bowl 1.6 m across, 1.0 m tall, Greek-key rim."""
    work = L.work_collection()
    prof = [(0.35, 0.0), (0.35, 0.08), (0.42, 0.14), (0.55, 0.35), (0.68, 0.62), (0.77, 0.86), (0.80, 0.94),
            (0.80, 1.0), (0.72, 1.0), (0.66, 0.92), (0.0, 0.92)]
    def rim(th, t):
        z = t * 1.0
        return 1.0 + (0.012 if 0.86 < z < 0.95 and (int(th / TAU * 48) % 2 == 0) else 0.0)
    tub = L.revolve("tub", L.resample_profile(prof, 40), segments=96, coll=work, scale_fn=rim)
    hi = L.union_blob([tub], f"urn_tub_v{variant}", voxel=0.012, smooth=1, coll=work)
    L.displace_noise(hi, strength=0.004, size=0.12, seed=1100 + variant, depth=2)
    return L.finalize_asset(hi, "urn_tub", variant, coll, bake=bake, bake_size=1024, budgets=L.BUDGETS["urn"],
                            size_note="pylon planter tub 1.6 m diameter x 1.0 m")


def build_keystone(variant, coll, bake=True):
    """Lion mask keystone, 0.8 m: face blob with muzzle, open mouth, brow, ears, and a radiating mane of small
    shell leaves. Origin at the bottom-centre of the BACK face; projects toward +Y."""
    rng = random.Random(3000 + variant)
    work = L.work_collection()
    parts = []
    S = 1.0 + 0.04 * (variant - 2)      # small per-variant size drift
    # Round 4 (carried defect: "keystone depth on the arches"). Two things were missing.
    # 1. The keystone had no VOUSSOIR: the mask sat straight on a 0.10 m plate flush with the archivolt, so at
    #    hero distance it was a pale disc with nothing to cast a shadow. Ref keystone_mask_1/2 show a wedge block
    #    that breaks forward out of the archivolt roll and carries a moulded cap under the frieze.
    # 2. The mask itself was all convex blobs: the eye/mouth dents were 0.03-0.09 m on a 0.006 m remesh and
    #    smooth=2 wiped them. Now the brow, cheeks and mane overhang, and the dents are 2-3x deeper.
    KEY_PROUD = 0.30 * S                # the voussoir face, proud of the archivolt (y = 0 is the archivolt face)
    parts.append(L.box("ks_back", (0.62 * S, 0.10, 0.66 * S), work, location=(0, 0.05, 0.0), bevel=0.02))
    # tapered voussoir: narrow at the springing side, wide under the cap
    VOUSSOIR = ((0.215, 0.10, -0.33), (0.245, 0.20, -0.20), (0.268, 0.26, 0.00),
                (0.283, 0.28, 0.16), (0.290, 0.24, 0.29), (0.300, 0.16, 0.33))
    parts.append(L.loft_rings("ks_voussoir",
                              [[Vector((-w * S, 0.02, z * S)), Vector((-w * S, y, z * S)),
                                Vector((w * S, y, z * S)), Vector((w * S, 0.02, z * S))]
                               for w, y, z in VOUSSOIR], work, cap_bottom=True, cap_top=True))
    # moulded cap under the frieze: a hard horizontal shadow line at the top of the block
    # depth 0.30 (not 0.34): the cap must not reach behind y = 0, or origin_bottom_centre(y_mode="back") re-origins
    # off the mounting plane and the whole keystone floats 2 cm proud of the archivolt.
    parts.append(L.box("ks_cap", (0.66 * S, 0.30, 0.075 * S), work, location=(0, 0.15, 0.335 * S), bevel=0.012))
    face = L.sphere("ks_face", 0.235 * S, work, location=(0, KEY_PROUD + 0.06, 0.00), scale=(1.02, 0.80, 1.05))
    parts.append(face)
    parts.append(L.sphere("ks_muzzle", 0.135 * S, work, location=(0, KEY_PROUD + 0.20, -0.075 * S), scale=(1.15, 0.95, 0.82)))
    parts.append(L.sphere("ks_nose", 0.055 * S, work, location=(0, KEY_PROUD + 0.30, -0.02 * S), scale=(1.25, 0.85, 0.72)))
    parts.append(L.sphere("ks_jaw", 0.115 * S, work, location=(0, KEY_PROUD + 0.16, -0.20 * S), scale=(1.1, 0.95, 0.68)))
    for side in (1, -1):
        # brow ridge, pushed forward and up so it OVERHANGS the eye socket (the dark accent at hero distance)
        parts.append(L.sphere(f"ks_brow{side}", 0.078 * S, work,
                              location=(side * 0.098 * S, KEY_PROUD + 0.235, 0.105 * S), scale=(1.5, 0.85, 0.62)))
        parts.append(L.sphere(f"ks_cheek{side}", 0.098 * S, work,
                              location=(side * 0.152 * S, KEY_PROUD + 0.155, -0.065 * S), scale=(1.0, 0.9, 1.0)))
        parts.append(L.sphere(f"ks_ear{side}", 0.062 * S, work,
                              location=(side * 0.205 * S, KEY_PROUD + 0.05, 0.205 * S), scale=(1.0, 0.62, 1.25)))
    # mane: fewer, bolder, thicker leaves standing clear of the face so a shadow slot is left behind each
    n = 10
    for i in range(n):
        ang = i * 360.0 / n + rng.uniform(-5, 5)
        leaf = L.acanthus_leaf(f"ks_mane{i}", length=0.30 * S * rng.uniform(0.86, 1.12), width=0.20 * S, curl=0.62,
                               droop=0.30, ribs=4, rib_amp=0.016, bulge=0.012, mid_dip=0.022, thickness=0.036,
                               lobes=3, lobe_depth=0.26, nu=14, nv=16, coll=work, seed=i, base_width=0.42)
        m = (Matrix.Translation((0.215 * S * math.sin(math.radians(ang)), KEY_PROUD + 0.055,
                                 0.02 + 0.215 * S * math.cos(math.radians(ang))))
             @ Euler((0, math.radians(ang), 0), "XYZ").to_matrix().to_4x4()
             @ Euler((math.radians(-32), 0, 0), "XYZ").to_matrix().to_4x4())
        leaf.data.transform(m)
        parts.append(leaf)
    hi = L.union_blob(parts, f"keystone_v{variant}", voxel=(0.009 if FAST else 0.005), smooth=1, smooth_factor=0.25,
                      coll=work)
    # open mouth + eye sockets + nostrils: dent the remeshed surface (booleans after a remesh proved unreliable)
    yb = KEY_PROUD
    dents = [((0.0, yb + 0.35, -0.135 * S), (0.105, 0.115, 0.062), 0.115),     # mouth
             ((0.088 * S, yb + 0.245, 0.048 * S), (0.045, 0.060, 0.040), 0.072),   # eyes, under the brow
             ((-0.088 * S, yb + 0.245, 0.048 * S), (0.045, 0.060, 0.040), 0.072),
             ((0.030 * S, yb + 0.315, 0.008 * S), (0.024, 0.040, 0.024), 0.035),   # nostrils
             ((-0.030 * S, yb + 0.315, 0.008 * S), (0.024, 0.040, 0.024), 0.035)]
    for v in hi.data.vertices:
        for (cx, cy, cz), (rx, ry, rz), depth_ in dents:
            d = ((v.co.x - cx) / rx) ** 2 + ((v.co.y - cy) / ry) ** 2 + ((v.co.z - cz) / rz) ** 2
            if d < 1.0 and v.co.y > cy - ry * 0.3:
                v.co.y -= depth_ * (1.0 - d) ** 0.7
    hi.data.update()
    L.displace_noise(hi, strength=0.003, size=0.05, seed=1200 + variant, depth=2)
    return L.finalize_asset(hi, "keystone", variant, coll, bake=bake, bake_size=1024, y_mode="back", ao=True,
                            cavity=True, budgets=L.BUDGETS["keystone"],
                            size_note=f"lion-mask keystone: {0.30 * S:.2f} m voussoir + mask to ~{0.30 * S + 0.36:.2f} m "
                                      f"proud of the archivolt face; origin = back-face bottom-centre")


def build_finial(variant, coll, bake=True):
    """Dome apex cap: a small metal-clad nub (085 shows only a tiny nub): 0.6 m."""
    work = L.work_collection()
    prof = [(0.40, 0.0), (0.40, 0.06), (0.30, 0.10), (0.24, 0.18), (0.26, 0.24), (0.22, 0.30), (0.14, 0.40),
            (0.12, 0.44), (0.16, 0.48), (0.10, 0.54), (0.04, 0.60), (0.0, 0.60)]
    fin = L.revolve("finial", L.resample_profile(prof, 30), segments=48, coll=work)
    hi = L.union_blob([fin], f"finial_v{variant}", voxel=0.006, smooth=1, coll=work)
    return L.finalize_asset(hi, "finial", variant, coll, bake=bake, bake_size=512, budgets=L.BUDGETS["finial"],
                            size_note="dome apex cap 0.8 m diameter x 0.6 m")


def rosette_petal(name, length, width, rise, curl, coll, seed=0, thickness=0.018, lobes=3, nu=16):
    """One rosette petal, built in the leaf frame (grows +Z, curls toward +Y) so it can be laid radially into the
    rosette plane: nearly flat for the first 70 % of its length, then the tip lifts off the ground plane."""
    n = 20
    sp = []
    for i in range(n + 1):
        u = i / n
        z = length * u
        y = 0.004 + rise * (u ** 1.5)
        if u > 0.66:
            f = (u - 0.66) / 0.34
            y += curl * (f ** 1.7)
            z -= curl * 0.35 * (f ** 2.2)
        sp.append((y, z))
    return L.acanthus_leaf(name, length=length, width=width, spine=sp, ribs=3, rib_amp=0.010, bulge=0.010,
                           mid_dip=0.014, thickness=thickness, lobes=lobes, lobe_depth=0.22, nu=nu, nv=n,
                           coll=coll, seed=seed, base_width=0.42)


# Per-variant rosette designs (petals outer/inner, overall diameter, relief). Measured against ref 083 / 003 /
# coffered_ceiling_1-3: the rib rosettes are 0.45-0.60 m across and stand roughly a quarter of their diameter
# proud of the rib face, with a deep annular groove between the petal ring and the central boss.
# relief raised from 0.155 to 0.21 m on 2026-09-07 after ARCH deepened the coffer interiors (saucer coffers
# 0.55 m, barrel vault 0.38 m): a 0.155 m boss disappears at the bottom of a 0.55 m box.
ROSETTE_STYLE = {
    1: dict(n_out=8, n_in=8, dia=0.60, relief=0.210),
    2: dict(n_out=10, n_in=10, dia=0.56, relief=0.196),
    3: dict(n_out=6, n_in=6, dia=0.62, relief=0.225),
}


def build_rosette(variant, coll, bake=True):
    """Coffer / rib rosette, ~0.6 m across. Origin at the back (mounting) face centre; like every wall-mounted
    piece it projects toward +Y, so it is built face-up along +Z and laid down at the end.

    Round 4 (QA-03-8): the round-3 rosette was a lathe with a cos(12*theta) radius wobble - a smooth 12-point star
    with no undercut anywhere, which is exactly the "flat outline" QA saw at cam04. It is now modelled: a sunk
    back disc, a ring of real petals whose tips lift 0.055 m off the disc (so there is a shadow slot behind every
    petal tip), a second ring rotated half a pitch, a 0.045 m annular groove and a beaded central boss."""
    st = ROSETTE_STYLE.get(variant, ROSETTE_STYLE[1])
    Rr = st["dia"] / 2.0
    relief = st["relief"]
    rng = random.Random(2000 + variant)
    work = L.work_collection()
    parts = []
    # back disc with a raised rim: the rim is what the annular groove is cut against
    disc = L.revolve("ros_disc", L.resample_profile(
        [(0.0, 0.0), (Rr * 0.60, 0.0), (Rr * 0.88, 0.008), (Rr * 0.97, 0.030), (Rr, 0.050),
         (Rr * 0.97, 0.062), (Rr * 0.86, 0.052), (Rr * 0.55, 0.018), (0.0, 0.014)], 26), segments=72, coll=work)
    parts.append(disc)
    for ring, (count, r0, ln, wd, rise, curl, z0) in enumerate((
            (st["n_out"], Rr * 0.34, Rr * 0.70, TAU * Rr * 0.62 / st["n_out"] * 1.02, 0.044, 0.082, 0.016),
            (st["n_in"], Rr * 0.16, Rr * 0.40, TAU * Rr * 0.30 / st["n_in"] * 1.06, 0.038, 0.064, 0.068))):
        off = 0.0 if ring == 0 else 180.0 / count
        for k in range(count):
            a = off + k * 360.0 / count + rng.uniform(-2.0, 2.0)
            p = rosette_petal(f"ros_p{ring}_{k}", ln * rng.uniform(0.95, 1.05), wd, rise, curl, work,
                              seed=100 * ring + k, thickness=0.020 if ring == 0 else 0.016)
            # leaf frame (+Z growth, +Y curl) -> radial in the XY plane with the curl lifting toward +Z
            m = (Matrix.Translation((r0 * math.cos(math.radians(a)), r0 * math.sin(math.radians(a)), z0))
                 @ Euler((0, 0, math.radians(a + 90.0)), "XYZ").to_matrix().to_4x4()
                 @ Euler((math.radians(90.0), 0, 0), "XYZ").to_matrix().to_4x4())
            p.data.transform(m)
            parts.append(p)
    # beaded central boss standing the full relief height
    boss = L.revolve("ros_boss", L.resample_profile(
        [(0.0, 0.045), (Rr * 0.30, 0.045), (Rr * 0.33, 0.062), (Rr * 0.28, 0.082), (Rr * 0.30, 0.098),
         (Rr * 0.24, relief * 0.80), (Rr * 0.13, relief * 0.96), (0.0, relief)], 24), segments=40, coll=work,
        scale_fn=lambda th, t: 1.0 + 0.07 * math.cos(10 * th) * (1.0 - t))
    parts.append(boss)
    hi = L.union_blob(parts, f"rosette_ceiling_v{variant}", voxel=0.004, smooth=1, smooth_factor=0.25, coll=work)
    L.displace_noise(hi, strength=0.0018, size=0.03, seed=1300 + variant, depth=1)
    # lay it down: +Z -> +Y
    hi.data.transform(Euler((math.radians(-90), 0, 0), "XYZ").to_matrix().to_4x4())
    return L.finalize_asset(hi, "rosette_ceiling", variant, coll, bake=bake, bake_size=1024, y_mode="back",
                            ao=True, cavity=True, budgets=L.BUDGETS["rosette_ceiling"],
                            size_note=f"rib/coffer rosette {st['dia']:.2f} m across, {relief:.3f} m of relief "
                                      f"({relief / st['dia']:.2f} of the diameter); back face at y=0, projects +Y")


# =============================================================================== ZIMM ATTIC RELIEF PANELS
SCAN_DIR = common.REFERENCE_DIR / "scans"
# name -> (file, pre-rotation to the 'face +Z, up +Y' frame, background depth fraction (0=back .. 1=front))
SCANS = {
    "centaur": ("centaur_metope.stl", None, 0.35),
    "soldiers": ("trajan_soldiers.stl", None, 0.45),
    "dacians": ("trajan_dacians.stl", Euler((0, 0, math.pi), "XYZ").to_matrix().to_4x4() @ Euler((-math.pi / 2, 0, 0), "XYZ").to_matrix().to_4x4(), 0.40),
}
_scan_cache = {}


def load_scan(key, tris=120000):
    """Import a public-domain relief scan (cm -> m), decimate, orient to face +Y with +Z up, bottom at z=0, centred
    in x, back plane at y=0. The oriented mesh is cached (fake user, survives clear_work); every call returns a fresh
    work-collection object with its own copy of the mesh."""
    me = _scan_cache.get(key)
    if me is not None:
        try:
            _ = me.name
        except ReferenceError:
            me = None
    if me is None:
        fname, pre, bgfrac = SCANS[key]
        path = SCAN_DIR / fname
        if not path.exists():
            print(f"[orn] WARNING scan {path} missing")
            return None
        t = time.time()
        bpy.ops.wm.stl_import(filepath=str(path), global_scale=0.01)
        ob = bpy.context.selected_objects[0]
        ob.name = f"scan_{key}"
        common.link_object(ob, L.work_collection())
        ob.data.transform(ob.matrix_world)
        ob.matrix_world = Matrix.Identity(4)
        if pre is not None:
            ob.data.transform(pre)
        # face +Z / up +Y  ->  face +Y / up +Z  (proper rotation: x -> -x, y <-> z)
        ob.data.transform(Matrix(((-1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1))))
        L.decimate(ob, target=tris)
        (x0, y0, z0), (x1, y1, z1) = L.bbox(ob)
        ob.data.transform(Matrix.Translation((-0.5 * (x0 + x1), -y0, -z0)))
        # background depth: area-weighted median of front-facing face-centre y (flat background = few, large faces)
        me = ob.data
        depth = max(1e-6, y1 - y0)
        pairs = sorted((poly.center.y / depth, poly.area) for poly in me.polygons if poly.normal.y > 0.6)
        total = sum(a for _, a in pairs)
        acc, med = 0.0, bgfrac
        for yv, a in pairs:
            acc += a
            if acc >= 0.5 * total:
                med = yv
                break
        me["bg_frac"] = med
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        me.name = f"scancache_{key}"
        me.use_fake_user = True
        _scan_cache[key] = me
        bpy.data.objects.remove(ob)
        print(f"[orn] scan {key}: {len(me.polygons)} tris, {x1 - x0:.2f} x {y1 - y0:.2f} x {z1 - z0:.2f} m, background at {med:.2f} of depth, in {time.time() - t:.1f}s")
    ob = bpy.data.objects.new(f"scan_{key}", me.copy())
    ob["bg_frac"] = me["bg_frac"]
    L.work_collection().objects.link(ob)
    return ob


def release_scans():
    for key, me in list(_scan_cache.items()):
        try:
            me.use_fake_user = False
            if me.users == 0:
                bpy.data.meshes.remove(me)
        except ReferenceError:
            pass
    _scan_cache.clear()


def place_scan(key, x, height, depth, slab_face_y, mirror=False, z=0.0, rot_deg=0.0, coll=None, bg_y=None,
               front_y=None):
    """Copy a scan into the panel: scaled to `height` (m) tall and `depth` (m) of relief, its background surface
    put at absolute y = `bg_y` (QA-02-9: the field ground is now SUNK, so the scan's own background plate must go
    down to it and the figures stand the full `depth` proud of it; the old default put the background at the slab
    face, which is why 100 % of the field measured >= 15 cm proud and the panel rendered as one flat mound)."""
    ob = load_scan(key)
    if ob is None:
        return None
    src = ob
    ob.name = f"rel_{key}_{x:.1f}"
    if front_y is not None and bg_y is not None:
        # solve the depth scale so the scan's own background plate lands on the field ground and its highest
        # figures reach `front_y`; bg_frac differs per scan (0.36 centaur .. 0.63 dacians) so a fixed depth
        # put the three scans at three different heights above the ground.
        depth = max(0.05, (front_y - bg_y) / max(0.15, 1.0 - src["bg_frac"]))
    (x0, y0, z0), (x1, y1, z1) = L.bbox(ob)
    sz = height / (z1 - z0)
    sy = depth / (y1 - y0)
    m = Matrix.Diagonal((-sz if mirror else sz, sy, sz, 1.0))
    ob.data.transform(m)
    if rot_deg:
        ob.data.transform(Euler((0, math.radians(rot_deg), 0), "XYZ").to_matrix().to_4x4())
    bg = src["bg_frac"] * depth
    ty = (bg_y - bg) if bg_y is not None else (slab_face_y - bg - 0.02)
    ob.data.transform(Matrix.Translation((x, ty, z)))
    return ob


HORSE_BONES = [("rump", "belly"), ("belly", "chest"), ("chest", "neckb"), ("neckb", "head"), ("head", "muzzle"),
               ("chest", "fshL"), ("fshL", "fknL"), ("fknL", "fhfL"), ("chest", "fshR"), ("fshR", "fknR"), ("fknR", "fhfR"),
               ("rump", "hipL"), ("hipL", "hkL"), ("hkL", "hhfL"), ("rump", "hipR"), ("hipR", "hkR"), ("hkR", "hhfR"),
               ("rump", "tail1"), ("tail1", "tail2")]


def horse_joints(S, rearing=True):
    """Side-view horse proxy (length along X, faces +X, viewer at +Y), 1.6 m at the withers before scaling."""
    J = {
        "rump": ((-0.60, 0.0, 1.20), (0.30, 0.24)), "belly": ((-0.05, 0.0, 1.05), (0.31, 0.25)), "chest": ((0.50, 0.0, 1.18), (0.28, 0.22)),
        "neckb": ((0.82, 0.0, 1.45), (0.17, 0.14)), "head": ((1.22, 0.0, 1.78), (0.12, 0.10)), "muzzle": ((1.50, 0.0, 1.66), (0.07, 0.06)),
        "fshL": ((0.55, 0.08, 0.95), (0.10, 0.09)), "fknL": ((0.62, 0.09, 0.55), (0.07, 0.07)), "fhfL": ((0.64, 0.09, 0.06), (0.06, 0.06)),
        "fshR": ((0.50, -0.08, 0.95), (0.10, 0.09)), "fknR": ((0.56, -0.09, 0.55), (0.07, 0.07)), "fhfR": ((0.58, -0.09, 0.06), (0.06, 0.06)),
        "hipL": ((-0.60, 0.08, 0.92), (0.11, 0.10)), "hkL": ((-0.72, 0.09, 0.48), (0.07, 0.07)), "hhfL": ((-0.64, 0.09, 0.06), (0.06, 0.06)),
        "hipR": ((-0.66, -0.08, 0.92), (0.11, 0.10)), "hkR": ((-0.78, -0.09, 0.48), (0.07, 0.07)), "hhfR": ((-0.70, -0.09, 0.06), (0.06, 0.06)),
        "tail1": ((-0.95, 0.0, 1.10), (0.06, 0.05)), "tail2": ((-1.15, 0.0, 0.70), (0.04, 0.03)),
    }
    if rearing:   # front legs tucked up, body pitched nose-up about the hind hooves
        J.update({"fshL": ((0.62, 0.08, 1.00), (0.10, 0.09)), "fknL": ((0.95, 0.09, 0.85), (0.07, 0.07)), "fhfL": ((0.90, 0.09, 0.50), (0.06, 0.06)),
                  "fshR": ((0.55, -0.08, 0.98), (0.10, 0.09)), "fknR": ((0.88, -0.09, 0.75), (0.07, 0.07)), "fhfR": ((0.80, -0.09, 0.42), (0.06, 0.06))})
    out = {}
    piv = Vector((-0.67, 0.0, 0.06))
    rot = Euler((0, math.radians(-38.0 if rearing else 0.0), 0), "XYZ").to_matrix()
    for k_, (pos, r) in J.items():
        pv = Vector(pos)
        if rearing and not k_.startswith("hhf") and not k_.startswith("hk"):
            pv = piv + rot @ (pv - piv)
        out[k_] = (pv * S, (r[0] * S, r[1] * S))
    return out


def relief_figure(name, pose, x, face_y, coll, S=2.0, mirror=False, rot_deg=0.0, proud=0.20, z=0.25, rng=None,
                  bulk=1.45, drape=True, seed=0, flatten=1.0):
    """A from-scratch figure in high relief: skin-figure body proxy embedded in the slab so that about `proud` m of
    its front stands out of the panel face; mirrored/rotated for variety.
    QA-01-10: `bulk` fattens the limbs (Zimm's figures are heavy, not stick-thin) and `drape` adds a folded garment
    mass from the chest to the ankles, so a figure covers ~0.9 x 3.2 m of field instead of a thin silhouette."""
    J = human_joints(S, front=1.0, pose=pose)
    if bulk != 1.0:
        J = {k: (p, (r[0] * bulk, r[1] * bulk)) for k, (p, r) in J.items()}
    body = L.skin_figure(name, J, HUMAN_BONES, coll, subdiv=2)
    hc = J["head"][0]
    hair = L.sphere(name + "_hair", 0.115 * S * min(bulk, 1.05), coll, location=hc + Vector((0, -0.02 * S, 0.03 * S)),
                    scale=(1.0, 0.95, 0.9))
    made = [body, hair]
    if drape:
        (bx0, by0, bz0), (bx1, by1, bz1) = L.bbox(body)
        H = bz1 - bz0
        cx, cy = 0.5 * (bx0 + bx1), 0.5 * (by0 + by1)
        a_hem, a_top = 0.128 * H, 0.082 * H
        b = 0.50 * a_hem
        g = drapery_tube(f"{name}_drape",
                         [(bz0 + 0.012 * H, cx, cy, a_hem, b),
                          (bz0 + 0.30 * H, cx, cy, a_hem * 0.94, b * 0.95),
                          (bz0 + 0.55 * H, cx, cy, a_hem * 0.80, b * 0.90),
                          (bz0 + 0.70 * H, cx, cy, a_top, b * 0.85)],
                         coll, folds=7, fold_amp=(0.03, 0.10), seed=seed, nu=48, nz=44, power=2.4)
        made.append(g)
    # QA-02-9: relief sculptors compress the depth of the figure and let it stand well proud of a sunk ground.
    # Scale in y FIRST (about the figure's own mid-depth) so more of the body's curvature is exposed above the
    # ground: with the old 1:1 depth only the outermost 0.28 m cap of a ~1.5 m thick body showed, and every
    # exposed normal pointed within ~40 deg of +Y -> one flat luminance under a near-normal sun.
    lo = Vector((min(L.bbox(o)[0][i] for o in made) for i in range(3)))
    hi = Vector((max(L.bbox(o)[1][i] for o in made) for i in range(3)))
    pre = (Euler((0, 0, math.radians(rot_deg)), "XYZ").to_matrix().to_4x4()
           @ Matrix.Diagonal((-1.0 if mirror else 1.0, flatten, 1.0, 1.0))
           @ Matrix.Translation((0, -0.5 * (lo.y + hi.y), 0)))
    for o in made:
        o.data.transform(pre)
    hi2 = Vector((max(L.bbox(o)[1][i] for o in made) for i in range(3)))
    post = Matrix.Translation((x, face_y - (hi2.y - proud), z))
    for o in made:
        o.data.transform(post)
    return made


def relief_horse(name, x, face_y, coll, S=1.85, mirror=False, proud=0.22, z=0.25, rearing=True, flatten=1.0):
    J = horse_joints(S, rearing=rearing)
    h = L.skin_figure(name, J, HORSE_BONES, coll, subdiv=2)
    (x0, y0, z0), (x1, y1, z1) = L.bbox(h)
    h.data.transform(Matrix.Diagonal((-1.0 if mirror else 1.0, flatten, 1.0, 1.0))
                     @ Matrix.Translation((0, -0.5 * (y0 + y1), 0)))
    (_, y0b, _), (_, y1b, _) = L.bbox(h)
    h.data.transform(Matrix.Translation((x, face_y - (y1b - proud), z)))
    return [h]


PANEL_GROUND_Y = 0.015    # QA-02-9: the field ground, sunk behind the 0.16 m frame plane
PANEL_W = 10.5            # FACE_LENGTH 17.81 - 2*RESSAUT_ALONG 3.2 - 2*ATTIC_PANEL_FRAME 0.45 = 10.51 (unchanged in r6)
PANEL_H = ARCH_R6["attic_panel_H"]        # r6: 4.50 -> 5.27
PANEL_K = round(PANEL_H / 4.50, 4)        # 1.1711: the figures scale WITH the field, so the reference ratio holds.
# Why a similarity scale and not a taller plinth: measured on ref 069 (the frontal left panel, field 450 px tall at
# 85 px/m), the central standing figure runs head 160 px to feet 555 px = 395 px = 0.88 of the field, and the group
# heads sit at 0.75-0.85 of it. The round-4 panel put a 3.5 m figure in a 4.5 m field = 0.78. Holding that ratio in
# the 5.27 m field means 4.10 m figures. Everything in X and Z scales by PANEL_K; nothing in Y does, because the
# depth budget (ARCH's 0.28 m recess, ATTIC_PANEL_DEPTH 0.25) did not move -- so every `flatten` is divided by
# PANEL_K to cancel the Y growth that the figure scale S would otherwise cause.

# Panel layouts (QA-01-10): >= 8 figures per 10.5 m field, three distinct designs. The x / scan-height numbers
# below are the round-4 layout for a 4.5 m field; build_attic_panel multiplies every height by PANEL_K so the same
# composition fits the r6 5.27 m field (figures 3.5 -> 4.10 m, ratio to the field held at 0.78).
# ("scan", key, x, height, mirror) | ("fig", pose, x, mirror, rot) | ("horse", x, mirror)
PANEL_LAYOUTS = {
    1: [("scan", "soldiers", -4.05, 4.15, True), ("fig", "kneel", -2.60, True, 0), ("fig", "arms_up", -1.80, False, 5),
        ("fig", "stride", -1.05, True, -4), ("fig", "arms_out", -0.30, False, 3), ("horse", 0.55, False),
        ("fig", "kneel", 1.15, True, 0), ("fig", "arms_up", 1.85, False, 4), ("fig", "kneel", 2.55, True, 0),
        ("fig", "stride", 3.30, False, -5), ("scan", "dacians", 4.35, 4.20, True)],
    2: [("scan", "dacians", -4.00, 4.20, False), ("fig", "stride", -2.35, False, -5), ("fig", "arms_out", -1.60, False, 0),
        ("fig", "stride", -0.85, True, 5), ("fig", "arms_up", -0.10, False, 0), ("fig", "arms_out", 0.65, True, -3),
        ("scan", "soldiers", 2.45, 4.15, False), ("fig", "stride", 4.15, True, 4), ("fig", "kneel", 4.90, False, 0)],
    3: [("scan", "centaur", -3.95, 3.30, False), ("fig", "stride", -2.45, True, 0), ("fig", "kneel", -1.75, False, 0),
        ("fig", "arms_up", -1.00, False, 3), ("fig", "kneel", -0.30, True, 0), ("fig", "stride", 0.45, False, -4),
        ("fig", "arms_out", 1.20, True, 0), ("fig", "kneel", 1.95, False, 0), ("fig", "stride", 2.70, True, 4),
        ("scan", "dacians", 4.05, 4.20, True)],
}


def build_attic_panel(variant, coll, bake=True):
    """One of the three Zimm 'Struggle for the Beautiful' relief designs, field PANEL_W x PANEL_H (r6: 10.5 x 5.27 m),
    relief ~0.25 m,
    composed from the public-domain relief scans (cut, scaled, mirrored, embedded, decimated, weathered - lead
    decision: scans only as reworked raw material for these panels). Design 1 = combat with centaur (centre),
    2 = procession (draped spectators), 3 = kneeling/standing group. Origin: back-face bottom-centre; +Y = face."""
    rng = random.Random(6000 + variant)
    work = L.work_collection()
    W, Hh, T, K = PANEL_W, PANEL_H, 0.16, PANEL_K
    face_y = T                     # the frame / border plane ARCH's moulding meets
    GROUND = PANEL_GROUND_Y        # the sunk field ground behind the figures
    RIM = 0.115                    # width of the border left standing at the frame plane
    # ARCH's recess measured from architecture.blend: ARCH_rotunda_attic_panel_* (the sunk field block) has its
    # front face at socket-local y = 0.00 and ARCH_rotunda_attic_frame_* (the moulding ring, 4.7 cm thick) stands
    # at y = 0.234-0.281. So the panel has 0.28 m of recess to work in; the boldest figures break the frame plane
    # by ~0.17 m as they do in ref 063, nothing more.
    FRONT_HI, FRONT_MID, FRONT_LO = 0.575, 0.415, 0.215
    design = (variant - 1) % 3 + 1
    # QA-02-9: a sunk field with a standing border, not a flat slab. The ground is 0.42-0.50 m behind the fronts
    # of the figures, so the slivers of ground between them go dark by occlusion even when the low morning sun
    # hits the panel nearly head-on (s.n = 0.98 on the face cam05 sees) and casts almost no shadow of its own.
    parts = [L.box("panel_ground", (W, GROUND, Hh), work, location=(0, GROUND / 2, Hh / 2)),
             L.box("panel_rim_b", (W, T, RIM), work, location=(0, T / 2, RIM / 2)),
             L.box("panel_rim_t", (W, T, RIM), work, location=(0, T / 2, Hh - RIM / 2)),
             L.box("panel_rim_l", (RIM, T, Hh), work, location=(-W / 2 + RIM / 2, T / 2, Hh / 2)),
             L.box("panel_rim_r", (RIM, T, Hh), work, location=(W / 2 - RIM / 2, T / 2, Hh / 2))]
    depth = 0.80                   # (overridden per scan by front_y/bg_y below)
    fig_count = 0
    for item in PANEL_LAYOUTS[design]:
        if item[0] == "scan":
            _, key, x, h, mirror = item
            parts.append(place_scan(key, x, h * K, depth, face_y, mirror=mirror, z=0.2 * K, bg_y=GROUND + 0.01,
                                    front_y=FRONT_HI - 0.02))
            fig_count += {"soldiers": 3, "dacians": 3, "centaur": 2}[key]
        elif item[0] == "fig":
            _, pose, x, mirror, rot = item
            parts += relief_figure(f"rf_{fig_count}", pose, x, face_y, work, S=2.20 * K * rng.uniform(0.95, 1.05),
                                   mirror=mirror, z=0.25 * K, rot_deg=rot + rng.uniform(-3, 3),
                                   # depth layering: alternate figures sit ~0.17 m further back so the overlaps
                                   # themselves make dark edges (ref 063 is a two-deep crowd, not a single plane)
                                   proud=(rng.uniform(FRONT_HI - 0.04, FRONT_HI + 0.02) if fig_count % 2 == 0
                                          else rng.uniform(FRONT_MID - 0.03, FRONT_MID + 0.03)) - face_y, rng=rng,
                                   bulk=rng.uniform(1.02, 1.18), seed=6000 + variant * 40 + fig_count,
                                   flatten=rng.uniform(0.42, 0.54) / K)
            fig_count += 1
        elif item[0] == "horse":
            _, x, mirror = item
            parts += relief_horse("rf_horse", x, face_y, work, S=2.15 * K, mirror=mirror, proud=0.62 - face_y,
                                  z=0.25 * K, flatten=0.46 / K)
            fig_count += 1
    # QA-02-9: a BACK ROW between the front figures. Zimm's panels are a two-deep crowd (ref 063 / zimm_panel_1):
    # what reads as "carving" at 100 m is the ladder of dark slots between a front body and the half-hidden one
    # behind it, not cast shadow - at az 118.5 / el 7.4 the sun is within 11 deg of this panel's normal and casts
    # essentially none. Front row stands 0.50-0.62 m proud of the sunk ground, the back row 0.19-0.27 m.
    back_poses = ["stride", "arms_up", "arms_out", "kneel", "stride", "arms_out", "arms_up"]
    for i in range(7):
        bx = -4.55 + i * 1.52 + rng.uniform(-0.15, 0.15)
        parts += relief_figure(f"rb_{i}", back_poses[i], bx, face_y, work, S=2.05 * K * rng.uniform(0.94, 1.04),
                               mirror=(i % 2 == 0), z=0.25 * K, rot_deg=rng.uniform(-6, 6),
                               proud=rng.uniform(FRONT_LO - 0.03, FRONT_LO + 0.04) - face_y, rng=rng,
                               bulk=rng.uniform(1.00, 1.12), seed=6500 + variant * 40 + i,
                               flatten=rng.uniform(0.30, 0.40) / K, drape=(i % 3 != 0))
        fig_count += 1
    print(f"[orn] attic_panel v{variant}: design {design}, {fig_count} figures")
    parts = [p for p in parts if p is not None]
    # shields / discs in the remaining gaps (design 1 and 3 are combats)
    if design != 2:
        for i in range(2):
            x = rng.uniform(-4.9, 4.9)
            parts.append(L.sphere(f"shield{i}", rng.uniform(0.3, 0.45) * K, work,
                                  location=(x, 0.20, rng.uniform(0.9, 3.4) * K), scale=(1.0, 0.42 / K, 1.0)))
    # low plinth / rock band the figures stand on (refs 169/022/063 fill the bottom of the field); it now stands
    # 0.36 m proud of the sunk ground so the bottom of the field carries a hard ledge line as it does in ref 063
    parts.append(L.box("panel_plinth", (W - 0.30, 0.34 - GROUND, 0.44 * K), work,
                       location=(0, 0.5 * (GROUND + 0.34), 0.25 * K), bevel=0.03))
    t = time.time()
    hi = L.union_blob(parts, f"attic_panel_v{variant}", voxel=(0.05 if FAST else 0.024), smooth=1, smooth_factor=0.18, coll=work)
    # clamp anything that overhangs the framed field: the frame crops the relief (field W x Hh, r6 10.5 x 5.27 m)
    for v in hi.data.vertices:
        v.co.x = max(-W / 2, min(W / 2, v.co.x))
        v.co.z = max(0.0, min(Hh, v.co.z))
        v.co.y = max(0.0, v.co.y)          # nothing behind the slab's back plane (it is buried in the attic wall)
    hi.data.update()
    print(f"[orn] attic_panel v{variant}: remesh {L.tri_count(hi)} tris in {time.time() - t:.1f}s")
    L.displace_noise(hi, strength=0.02, size=0.6, seed=1400 + variant, depth=2)
    L.displace_noise(hi, strength=0.006, size=0.08, seed=1500 + variant, depth=1)
    return L.finalize_asset(hi, "attic_panel", variant, coll, bake=bake, bake_size=4096 if not FAST else 2048, y_mode="back",
                            budgets=L.BUDGETS["attic_panel"],
                            size_note=f"Zimm panel design {design}: field {W:.2f} x {Hh:.2f} m, ground sunk to y={GROUND:.2f}, border at "
                                      f"y={T:.2f}, relief fronts to y ~0.60 (>= 0.45 m above the ground), {fig_count} figures; "
                                      f"origin back-face bottom-centre")


def build_corner_scroll(variant, coll, bake=True):
    """QA-02-10 / QA-01-13: the PAIRED Ionic volute acroterion that caps each attic corner, directly over the
    corner figure (refs 085 / attic_corner_figure_1 and _3). One asset = TWO volute blocks on a shared moulded
    plinth, their spiral faces looking +Y (outward), 0.83 m apart.

    Placement note (important): ARCH already models a crude pair of volutes on every corner cap
    (`ARCH_rotunda_attic_volute_NN_a/_b`, 290 tris, centres at local x = +-0.415, z 0.25-1.52, y -0.10-0.22, on a
    1.90 x 0.60 x 0.25 plinth) at exactly the `SOCKET_finial_*` (subtype `volute_scroll`) that `build_master.py`
    routes this asset onto. This asset is therefore built to the SAME centres and to an envelope that fully
    encloses ARCH's blocks (x +-1.13 at the bolster, y -0.29..0.55, z 0..1.60), so the two never fight: whichever
    the lead hides, the silhouette is the same and only the detailed one shows. Previously this was a single
    1.78 m block sitting between ARCH's two, which is why QA saw no scroll pair at cam05.

    Origin: bottom-centre of the plinth = the corner cap top (z = 38.30 in world), +Y outward, y_mode 'keep'."""
    rng = random.Random(1900 + variant)
    work = L.work_collection()
    SEP = 0.415          # half the centre-to-centre spacing of the two volute blocks (ARCH's spacing)
    PL_W, PL_D, PL_H = 2.10, 0.68, 0.26
    CY = 0.05            # the blocks sit 5 cm proud of the socket plane, as ARCH's do
    ABZ = 1.40           # abacus underside
    H = 1.60
    parts = [L.box("cs_plinth", (PL_W, PL_D, PL_H), work, location=(0, CY, PL_H / 2), bevel=0.03),
             L.box("cs_plinth_fillet", (PL_W - 0.14, PL_D - 0.10, 0.07), work, location=(0, CY, PL_H + 0.035), bevel=0.015),
             L.box("cs_abacus", (2.14, 0.64, H - ABZ), work, location=(0, CY, 0.5 * (ABZ + H)), bevel=0.025)]
    for side in (1, -1):
        cx = side * SEP
        # cushion / bolster core: the block behind the scrolls (also the piece that hides ARCH's crude volute)
        parts.append(L.box(f"cs_core{side}", (1.42, 0.46, ABZ - 0.24), work,
                           location=(cx, CY, 0.5 * (0.24 + ABZ)), bevel=0.04))
        # channelled cushion fluting across the core
        for i in range(3):
            parts.append(L.box(f"cs_chan{side}_{i}", (1.10, 0.06, 0.05), work,
                               location=(cx, CY + 0.24, 0.62 + 0.20 * i), bevel=0.012))
        # the spiral itself, face toward +Y, overhanging the block outward
        ex = cx + side * 0.30
        v = L.volute(f"cs_scroll{side}", eye=(0, 0, 0), radius=0.44, turns=2.15, band=(0.44, 0.19), coll=work,
                     direction=-side, taper=0.32, segments=12, steps=80)
        v.data.transform(Matrix.Translation((ex, CY + 0.26, 0.94)) @ Euler((0, 0, math.radians(90)), "XYZ").to_matrix().to_4x4())
        parts.append(v)
        parts.append(L.sphere(f"cs_eye{side}", 0.075, work, location=(ex, CY + 0.50, 0.94), scale=(1.0, 0.7, 1.0)))
        # the roll of the volute continuing back into the block
        bol = L.revolve(f"cs_bol{side}", [(0.0, 0.0), (0.17, 0.012), (0.20, 0.08), (0.195, 0.34), (0.16, 0.41), (0.0, 0.42)],
                        segments=28, coll=work)
        bol.data.transform(Euler((math.radians(-90), 0, 0), "XYZ").to_matrix().to_4x4())
        bol.data.transform(Matrix.Translation((ex, CY + 0.10, 0.94)))
        parts.append(bol)
        # egg-and-dart echinus under the scroll, along the front of the core
        for i in range(5):
            ex2 = cx + (i - 2) * 0.26
            parts.append(L.sphere(f"cs_egg{side}_{i}", 0.085, work, location=(ex2, CY + 0.235, 0.40), scale=(0.85, 0.75, 1.15)))
    # palmette fan in the channel between the two blocks (attic_corner_figure_1)
    for k in range(7):
        a = -54 + 18 * k
        lobe = L.acanthus_leaf(f"palm{k}", length=0.28 + 0.05 * (3 - abs(k - 3)), width=0.075, curl=0.20, droop=0.05,
                               ribs=1, rib_amp=0.0, bulge=0.016, thickness=0.04, lobes=1, lobe_depth=0.0, nu=6, nv=10,
                               coll=work, base_width=0.55)
        lobe.data.transform(Matrix.Translation((0, CY + 0.24, 0.52)) @ Euler((0, math.radians(a), 0), "XYZ").to_matrix().to_4x4())
        parts.append(lobe)
    parts.append(L.sphere("palm_base", 0.075, work, location=(0, CY + 0.24, 0.52), scale=(1.4, 1.0, 0.8)))
    hi = L.union_blob(parts, f"corner_scroll_v{variant}", voxel=(0.02 if FAST else 0.011), smooth=1,
                      smooth_factor=0.25, coll=work)
    L.displace_noise(hi, strength=0.005, size=0.14, seed=1950 + variant, depth=2)
    L.displace_noise(hi, strength=0.002, size=0.03, seed=1970 + variant, depth=1)
    return L.finalize_asset(hi, "corner_scroll", variant, coll, bake=bake, bake_size=1024, y_mode="keep",
                            budgets=L.BUDGETS["corner_scroll"],
                            extra_props={"unit_length": PL_W, "pair_separation": 2 * SEP,
                                         "encloses": "ARCH_rotunda_attic_volute_*"},
                            size_note=f"PAIRED attic-corner volute acroterion: plinth {PL_W:.2f} m, two scroll blocks "
                                      f"{2*SEP:.2f} m apart, spiral eye r 0.44, overall ~2.5 x 0.85 x {H:.2f} m; origin "
                                      f"bottom-centre on the corner cap, +Y outward (socket finial/volute_scroll)")


# =============================================================================== LINEAR MOULDINGS (1 m units) + DRUM BAND
def _strip(name, coll, length=1.0, depth=0.05, height=0.2):
    """Backing strip: origin at the bottom-centre of its BACK face, runs along X, projects toward +Y."""
    return L.box(name, (length, depth, height), coll, location=(0, depth / 2, height / 2))


# QA-01-11 rostra / podium band (reference sheet s4 #12: band h ~ 0.5, rosettes ~ 0.45 dia; crops rostra_band_1-2).
# In the photos the meander is INCISED into the top course of the podium (deep rectangular grooves in a flat face)
# and only the round paterae stand proud, so the unit is a flat slab with the fret cut out of it by boolean.
KEY_UNIT = 0.60          # one meander repeat = one greek_key unit (unit_length)
KEY_BAND_H = 0.52        # band height, shared by greek_key and rosette_band so they mix on one run
KEY_FACE = 0.08          # slab thickness (the band face stands 8 cm off the wall behind it)
KEY_GROOVE = 0.045       # how deep the fret is cut into that face  (>= 3 cm required by QA-01-11)
KEY_BAR = 0.052          # groove width (groove : land about 1 : 0.9, as in rostra_band_1/2)
KEY_BOSS = 0.45          # patera diameter


def greek_key_cutters(coll, x0, unit, band_h, tag="k"):
    """Cutter boxes for one classic running-fret repeat starting at local x = x0 and spanning `unit` metres.
    Grid g = unit/7, inner field 5 g tall; the top groove runs the full width so consecutive units join into one
    continuous meander. Each box protrudes through the front face so a boolean difference leaves a groove."""
    g = unit / 7.0
    w = KEY_BAR
    zb = (band_h - 5.0 * g) / 2.0                      # bottom of the inner field
    dy = KEY_GROOVE + 0.02
    y = KEY_FACE - KEY_GROOVE + dy / 2.0
    out = []

    def seg(gx0, gz0, gx1, gz1):
        ax, az = x0 + gx0 * g, zb + gz0 * g
        bx, bz = x0 + gx1 * g, zb + gz1 * g
        out.append(L.box(f"{tag}{len(out)}", (abs(bx - ax) + w, dy, abs(bz - az) + w), coll,
                         location=(0.5 * (ax + bx), y, 0.5 * (az + bz)), segments=1))

    seg(-0.05, 5, 7.05, 5)          # continuous top groove (overlaps the neighbouring unit by 5 %)
    seg(6, 5, 6, 1)                 # down stroke
    seg(6, 1, 1, 1)                 # bottom stroke
    seg(1, 1, 1, 3.5)               # up stroke
    seg(1, 3.5, 4, 3.5)             # inner return
    seg(4, 3.5, 4, 2.0)             # spiral tail
    return out


def cut_boxes(obj, cutters):
    """Boolean-difference every cutter out of `obj` (before any remesh: exact booleans on boxes are reliable)."""
    for c in cutters:
        m = obj.modifiers.new("Cut", "BOOLEAN")
        m.operation = "DIFFERENCE"
        m.solver = "EXACT"
        m.object = c
        L.apply_all(obj)
        L.remove_object(c)
    return obj


def patera_boss(name, coll, diameter=KEY_BOSS, proud=0.055):
    """The round rosette boss of the rostra band: a low petalled patera with a knob centre, facing +Y."""
    r = diameter / 2.0
    prof = [(0.000, proud * 0.95), (0.030, proud * 1.05), (0.060, proud * 0.72), (0.090, proud * 0.62),
            (0.135, proud * 0.80), (0.175, proud * 0.62), (r * 0.93, proud * 0.34), (r, proud * 0.10), (r, 0.0)]

    def petals(th, t):
        return 1.0 + 0.045 * math.cos(12 * th) * t

    ob = L.revolve(name, L.resample_profile(prof, 24), segments=72, coll=coll, scale_fn=petals,
                   cap_bottom=True, cap_top=True)
    ob.data.transform(Euler((math.radians(-90), 0, 0), "XYZ").to_matrix().to_4x4())
    return ob


def build_moulding(kind, variant, coll, bake=True):
    """One-metre unit of a repeating moulding, to be arrayed by ARCH along its profile sweeps. Sizes from the
    reference sheet (dentil pitch 0.15, egg-and-dart ~0.17 pitch, Greek key band 0.45-0.5 with 0.45 rosettes,
    modillion brackets, anthemion/palmette band 0.25 pitch)."""
    rng = random.Random(8000 + variant + hash(kind) % 100)
    work = L.work_collection()
    parts = []
    ulen = 1.0                     # repeat length along X; published as the custom property `unit_length`
    if kind == "dentil":
        n = 6
        pitch = 1.0 / n
        parts.append(_strip("m_back", work, depth=0.04, height=0.22))
        for i in range(n):
            x = -0.5 + pitch * (i + 0.5)
            parts.append(L.box(f"dentil{i}", (pitch * 0.62, 0.12, 0.16), work, location=(x, 0.04 + 0.06, 0.03 + 0.08), bevel=0.006))
        h, d = 0.22, 0.16
    elif kind == "egg_and_dart":
        n = 6
        pitch = 1.0 / n
        parts.append(_strip("m_back", work, depth=0.04, height=0.20))
        for i in range(n):
            x = -0.5 + pitch * (i + 0.5)
            # egg: half-ellipsoid on the strip; shell: a thicker ring around it; dart between
            parts.append(L.sphere(f"egg{i}", 0.052, work, location=(x, 0.06, 0.10), scale=(1.0, 1.1, 1.45)))
            parts.append(L.sphere(f"shell{i}", 0.068, work, location=(x, 0.03, 0.095), scale=(1.0, 0.7, 1.45)))
            parts.append(L.box(f"dart{i}", (0.022, 0.06, 0.13), work, location=(x + pitch / 2, 0.05, 0.10), bevel=0.006))
        h, d = 0.20, 0.13
    elif kind == "greek_key":
        # QA-01-11 running meander (rostra_band_1/2, sheet s4 #12): band 0.52 m, ONE key repeat per unit so the unit
        # tiles seamlessly at any run length. Grid g = U/7, inner field 5g = 0.43 m, groove 4.5 cm deep.
        band_h, ulen = KEY_BAND_H, KEY_UNIT
        slab = L.box("m_face", (ulen, KEY_FACE, band_h), work, location=(0, KEY_FACE / 2, band_h / 2))
        parts.append(cut_boxes(slab, greek_key_cutters(work, x0=-ulen / 2, unit=ulen, band_h=band_h, tag="k")))
        h, d = band_h, KEY_FACE
    elif kind == "rosette_band":
        # QA-01-11 rostra band: a round patera boss (0.45 m) ALTERNATING with one incised meander repeat.
        # unit = 1.20 m = 0.60 boss panel + 0.60 key repeat; same band height as greek_key so the two mix on a run.
        band_h, ulen = KEY_BAND_H, 2 * KEY_UNIT
        slab = L.box("m_face", (ulen, KEY_FACE, band_h), work, location=(0, KEY_FACE / 2, band_h / 2))
        cx = -ulen / 2 + KEY_UNIT / 2
        cut_boxes(slab, greek_key_cutters(work, x0=cx + KEY_UNIT / 2, unit=KEY_UNIT, band_h=band_h, tag="r"))
        parts.append(slab)
        boss = patera_boss("boss", work)
        boss.data.transform(Matrix.Translation((cx, KEY_FACE - 0.004, band_h / 2)))
        parts.append(boss)
        h, d = band_h, KEY_FACE + 0.055
    elif kind == "modillion":
        # block bracket with a scrolled underside, 2 per metre (pitch 0.5), backing = the soffit strip
        parts.append(_strip("m_back", work, depth=0.03, height=0.30))
        for i in range(2):
            x = -0.25 + 0.5 * i
            parts.append(L.box(f"mod{i}", (0.22, 0.30, 0.22), work, location=(x, 0.18, 0.15), bevel=0.01))
            scroll = L.volute(f"mods{i}", eye=(0, 0, 0), radius=0.07, turns=1.3, band=(0.20, 0.05), coll=work, direction=1.0)
            scroll.data.transform(Matrix.Translation((x, 0.32, 0.10)))
            parts.append(scroll)
            parts.append(L.sphere(f"acorn{i}", 0.04, work, location=(x, 0.34, 0.05)))
        h, d = 0.30, 0.36
    elif kind == "anthemion":
        # palmette fan band: 4 fans per metre, each 7 lobes from a small base, alternating with a lotus bud
        parts.append(_strip("m_back", work, depth=0.03, height=0.22))
        for i in range(4):
            x = -0.5 + 0.25 * (i + 0.5)
            for k in range(7):
                a = -60 + 20 * k
                lobe = L.acanthus_leaf(f"lobe{i}_{k}", length=0.14 + 0.02 * (3 - abs(k - 3)), width=0.035, curl=0.15, droop=0.05,
                                       ribs=1, rib_amp=0.0, bulge=0.008, thickness=0.02, lobes=1, lobe_depth=0.0, nu=6, nv=8, coll=work, base_width=0.6)
                lobe.data.transform(Matrix.Translation((x, 0.045, 0.04)) @ Euler((0, math.radians(a), 0), "XYZ").to_matrix().to_4x4())
                parts.append(lobe)
            parts.append(L.sphere(f"base{i}", 0.03, work, location=(x, 0.045, 0.04), scale=(1.3, 1.0, 0.8)))
            parts.append(L.sphere(f"bud{i}", 0.02, work, location=(x + 0.125, 0.045, 0.10), scale=(1.0, 1.0, 3.0)))
        h, d = 0.22, 0.08
    else:
        raise KeyError(kind)
    hi = L.union_blob(parts, f"{kind}_v{variant}", voxel=(0.01 if FAST else 0.006), smooth=1, coll=work)
    L.displace_noise(hi, strength=0.002, size=0.03, seed=1600 + variant, depth=1)
    relief = KEY_GROOVE if kind in ("greek_key", "rosette_band") else d
    return L.finalize_asset(hi, kind, variant, coll, bake=bake, bake_size=1024, y_mode="back", budgets=L.BUDGETS["moulding"],
                            extra_props={"unit_length": ulen, "band_height": h, "relief_depth": relief},
                            size_note=(f"repeat unit: unit_length {ulen:.2f} m along X, {h:.2f} m tall, projects {d:.2f} m "
                                       f"toward +Y (fret incised {relief * 100:.1f} cm into the face); origin back-face "
                                       f"bottom-centre; array with orn_lib.array_unit_along_run"))


def build_drum_band(variant, coll, bake=True):
    """One metre of the drum's 'broad cushion ring with guilloche moulding' (DPR): a torus-section cushion 1.6 m
    tall covered with an imbricated scale pattern (0.35 pitch) over a plain torus, plus the bead moulding of the
    cornice ring above. Straight unit (ARCH curves it with an array + curve modifier or arrays it in 1 m facets
    around r 17.5)."""
    rng = random.Random(8500 + variant)
    work = L.work_collection()
    Hb = 1.6
    prof = [(0.0, 0.0), (0.06, 0.02), (0.14, 0.10), (0.24, 0.30), (0.33, 0.60), (0.36, 0.85), (0.33, 1.10),
            (0.24, 1.35), (0.14, 1.52), (0.06, 1.58), (0.0, Hb)]
    prof = L.smooth_profile(prof, 1)
    n = len(prof)
    pitch = 0.35
    def fn(u, v):
        x = -0.5 + u
        k = v * (n - 1)
        i = min(int(k), n - 2)
        f = k - i
        y = prof[i][0] * (1 - f) + prof[i + 1][0] * f
        z = prof[i][1] * (1 - f) + prof[i + 1][1] * f
        # scales: rows offset by half a pitch, each a shallow dome
        # imbricated scales: each row a line of rounded scales hanging from its top edge, overlapping the row below
        # (height rises toward the free lower edge, then steps down onto the scale beneath); rows offset half a pitch
        bump = 0.0
        if 0.15 < z < Hb - 0.15:
            for row in (int(z / pitch), int(z / pitch) + 1):
                off = pitch / 2 if row % 2 else 0.0
                cx = ((x + 10.0 + off) % pitch) - pitch / 2
                top = row * pitch + pitch * 0.55      # attachment edge of this row's scales
                dz = top - z                          # distance below the attachment edge
                if dz < 0 or dz > pitch * 1.05:
                    continue
                if (cx / (pitch * 0.5)) ** 2 + (dz / (pitch * 1.05)) ** 2 < 1.0:
                    bump = max(bump, 0.012 + 0.03 * (dz / (pitch * 1.05)) ** 0.8)
        # normal of the profile in the yz plane
        dy = prof[i + 1][0] - prof[i][0]
        dz = prof[i + 1][1] - prof[i][1]
        ln = math.hypot(dy, dz) or 1.0
        ny, nz = dz / ln, -dy / ln
        return (x, y + ny * bump, z + nz * bump)
    cushion = L.surface("drum_cushion", fn, 120, 80, work)
    L.solidify(cushion, 0.05, offset=-1.0)
    back = L.box("drum_back", (1.0, 0.08, Hb), work, location=(0, 0.02, Hb / 2))
    hi = L.union_blob([cushion, back], f"drum_band_v{variant}", voxel=(0.02 if FAST else 0.01), smooth=1, coll=work)
    L.displace_noise(hi, strength=0.004, size=0.06, seed=1700 + variant, depth=2)
    return L.finalize_asset(hi, "drum_band", variant, coll, bake=bake, bake_size=1024, y_mode="back", budgets=L.BUDGETS["moulding"],
                            size_note="1 m unit of the drum scale band, 1.6 m tall, 0.36 m proud; origin back-face bottom-centre")


# =============================================================================== registry / main
# --------------------------------------------------------------------------- rotunda frieze rinceau (round 5)
# Reference: sheet s4 #13 ("frieze 1.2, rinceau on ressauts, plain between"; "Rinceau = scrolling acanthus with
# rosette bosses") and sheet line 183-184 (DPR: "angled impost blocks with a rinceau pattern protruding from a plain
# frieze. The blocks serve to 'turn' the rotunda") -> the ornament belongs ONLY on the 24 ressaut faces, which are
# exactly ARCH's SOCKET_frieze_run_000..023 (8 fronts of 5.913 m + 16 returns of 2.999 m, all at z 28.55).
# Band: 0.90 m tall (arch r4b frieze z 28.55-29.45, face at d 0.34). The architrave crown BELOW the band is the
# binding obstruction: scripts/arch_build.py:156 puts it at d 0.44, i.e. it oversails the flush frieze by 0.10 m
# ("architrave crown, oversailing the flush frieze by 0.10"). The 0.50 in docs/arch_notes.md:718 is superseded by
# the r4b row at arch_notes.md:793. So the clearance budget on this band is 0.100 m, NOT 0.160 m (ORN r5 review
# finding 3), and the design caps at 0.090 m -> 10 mm of guaranteed clearance under the crown.
# The two lengths get their own asset (one instance per socket) because build_master.py places ONE object per socket.
RIN_BAND_H = ARCH_R6["frieze_band_H"]   # r6: 0.90 -> 0.81 (arch_params.FRIEZE_H; sockets carry band_height)
RIN_CROWN_CLEAR = 0.10     # architrave crown d 0.44 minus frieze face d 0.34 (arch_build.py:156, unchanged in r6)
RIN_MAX_PROUD = 0.09       # hard cap on the relief; RIN_CROWN_CLEAR - RIN_MAX_PROUD = 10 mm of clearance
RIN_MARGIN = 0.075 / 0.90  # plain margin top and bottom as a fraction of the band, held across the r6 refit
RIN_FIELD_H = round(RIN_BAND_H * (1.0 - 2 * RIN_MARGIN), 4)   # carved field: 0.675 m inside the 0.81 m band
RIN_EMBED = 0.015          # the ornament is sunk 1.5 cm into the frieze face so nothing floats off the wall
RIN_RUNS = {"frieze_rinceau": 5.9128, "frieze_rinceau_return": 2.9994}
RIN_REPEATS = {"frieze_rinceau": 6, "frieze_rinceau_return": 3}
# per-variant character: (stem amplitude, scroll radius, boss diameter, leaf length, phase). amp + 1.78*R is the
# half-height of the design; all three land near 0.375, and the Z normalisation at the end of build_frieze_rinceau
# then squeezes the design onto RIN_FIELD_H/2 = 0.3375 (a 10 % vertical squash for the r6 band, x untouched, so the
# scroll pitch along the run and the relief depth in Y are exactly what round 5b measured).
RIN_VARIANTS = {1: (0.125, 0.140, 0.150, 0.235, 0.00),
                2: (0.110, 0.150, 0.175, 0.260, 0.35),
                3: (0.140, 0.132, 0.140, 0.220, 0.50)}


def _rin_spiral(name, coll, cx, cz, R, sign, start_ang, y0=0.030, r0=0.034, r1=0.015, turns=1.35, steps=34):
    """One scroll of the rinceau: a tapering tube spiralling in the band's XZ face plane, y = out of the wall."""
    pts = []
    for i in range(steps + 1):
        t = i / steps
        th = start_ang + sign * turns * TAU * t
        rr = R * (1.0 - 0.85 * t) ** 1.1
        pts.append((cx + rr * math.cos(th), y0 + 0.010 * t, cz + rr * math.sin(th)))
    return L.tube(name, pts, lambda v: r0 + (r1 - r0) * v, coll=coll, segments=10)


def _rin_leaf(name, coll, x, z, ang_deg, length, seed, y=0.020, width=0.135):
    """An acanthus leaf lying in the band face: grown along +Z then turned about Y so it runs in the XZ plane and
    still bends toward +Y (out of the wall)."""
    lf = L.acanthus_leaf(name, length=length, width=width, curl=0.45, droop=0.30, ribs=5, rib_amp=0.018,
                         bulge=0.034, thickness=0.026, lobes=3, lobe_depth=0.055, nu=10, nv=14, coll=coll,
                         seed=seed, base_width=0.45)
    lf.data.transform(Matrix.Translation((x, y, z)) @ Euler((0, math.radians(ang_deg), 0), "XYZ").to_matrix().to_4x4())
    return lf


def build_frieze_rinceau(kind, variant, coll, bake=True):
    run, nrep = RIN_RUNS[kind], RIN_REPEATS[kind]
    U = run / nrep
    amp, R, boss_d, leaf_l, phase = RIN_VARIANTS[variant]
    rng = random.Random(9100 + variant * 31 + (7 if kind.endswith("return") else 0))
    work = L.work_collection()
    parts = []
    zc = RIN_BAND_H * 0.5
    y_stem, r_stem = 0.030, 0.042

    # continuous stem: everything else touches it, so the asset stays ONE shell and decimates cleanly to LOD2
    steps = 26 * nrep
    path = []
    for i in range(steps + 1):
        x = run * i / steps
        path.append((x, y_stem, zc + amp * math.sin(TAU * (x / U) + phase * TAU)))
    parts.append(L.tube("rin_stem", path, lambda v: r_stem * (0.72 + 0.28 * math.sin(math.pi * v)),
                        coll=work, segments=12))

    def stem_z(x):
        return zc + amp * math.sin(TAU * (x / U) + phase * TAU)

    k = 0
    for i in range(nrep):
        for frac, s in ((0.25, +1.0), (0.75, -1.0)):
            k += 1
            cx = (i + frac) * U - phase * U
            if cx < 0.22 or cx > run - 0.22:
                continue
            jr = 1.0 + rng.uniform(-0.07, 0.07)
            Rk = R * jr
            crest_z = stem_z(cx)
            eye_z = crest_z + s * Rk * 0.78
            # the spiral starts on the stem (angle pointing back at the crest) and curls into the eye
            parts.append(_rin_spiral(f"rin_sc{k}", work, cx, eye_z, Rk, sign=s,
                                     start_ang=(-math.pi / 2 if s > 0 else math.pi / 2),
                                     r0=0.034 * jr, turns=1.35 + rng.uniform(-0.08, 0.08)))
            # rosette boss in the eye of the scroll
            bd = boss_d * (1.0 + rng.uniform(-0.05, 0.05))
            boss = patera_boss(f"rin_bs{k}", work, diameter=bd, proud=0.085)
            boss.data.transform(Matrix.Translation((cx, 0.012, eye_z)))
            parts.append(boss)
            # three acanthus leaves at the springing (two full + one short), running along the stem away from the scroll
            for sgn, ang, fl in ((-1.0, -102.0, 1.00), (+1.0, 102.0, 1.00), (-1.0, -150.0, 0.62)):
                lx = cx + sgn * (0.13 + rng.uniform(0.0, 0.03))
                parts.append(_rin_leaf(f"rin_lf{k}_{int(sgn)}_{int(fl*100)}", work, lx, stem_z(lx),
                                       ang * (1.0 if s > 0 else 0.86) + rng.uniform(-8, 8),
                                       fl * leaf_l * (1.0 + rng.uniform(-0.09, 0.09)), seed=k * 13 + int(sgn)))
            # a berry cluster in the hollow of the scroll and a counter-tendril curling the other way
            parts.append(L.sphere(f"rin_bd{k}", 0.030 * jr, work,
                                  location=(cx + s * 0.10, 0.030, crest_z - s * 0.055), scale=(1.0, 0.8, 1.0)))
            tx = cx + 0.5 * U * (1.0 if s > 0 else -1.0) * 0.55
            if 0.16 < tx < run - 0.16:
                parts.append(_rin_spiral(f"rin_tn{k}", work, tx, stem_z(tx) - s * 0.085, 0.075 * jr, sign=-s,
                                         start_ang=(math.pi / 2 if s > 0 else -math.pi / 2),
                                         r0=0.024, r1=0.011, turns=1.05, steps=22))

    # terminals: a short palmette fan closing each end of the run
    for ex, adir in ((0.0, +1.0), (run, -1.0)):
        for j in range(3):
            a = adir * (62.0 + 34.0 * j)
            parts.append(_rin_leaf(f"rin_tm{int(ex)}_{j}", work, ex + adir * 0.10, stem_z(ex),
                                   a, leaf_l * 0.60, seed=900 + j))

    hi = L.union_blob(parts, f"{kind}_v{variant}", voxel=(0.014 if FAST else 0.011), smooth=1, coll=work)
    L.displace_noise(hi, strength=0.0022, size=0.05, seed=9100 + variant * 7, depth=1)
    lods = L.finalize_asset(hi, kind, variant, coll, bake=bake, bake_size=1024, y_mode="back",
                            budgets=L.BUDGETS[kind],
                            extra_props={"unit_length": run, "run_length": run, "band_height": RIN_BAND_H,
                                         "repeats": nrep, "max_proud": RIN_MAX_PROUD, "field_height": RIN_FIELD_H,
                                         "crown_clearance_budget": RIN_CROWN_CLEAR,
                                         "origin_note": "RUN START: local x=0 is the socket, geometry runs to x=run_length"},
                            size_note=(f"full-run rinceau panel for one rotunda ressaut face: {run:.3f} m long, "
                                       f"{RIN_BAND_H:.2f} m band (carved field z {0.5*(RIN_BAND_H-RIN_FIELD_H):.3f}"
                                       f"-{0.5*(RIN_BAND_H+RIN_FIELD_H):.3f}), projects <= {RIN_MAX_PROUD:.3f} m toward +Y "
                                       f"({RIN_CROWN_CLEAR:.3f} m architrave-crown budget); "
                                       f"origin = RUN START (x=0), back face y=0, band bottom z=0; place directly "
                                       f"on SOCKET_frieze_run_### (no array helper needed)"))
    # deviation from the bottom-CENTRE convention: this panel spans the whole run, so its origin is the run START,
    # exactly where ARCH's frieze_run socket sits. Shift the mesh so bbox min x = 0.
    for o in lods:
        (x0, _, _), _ = L.bbox(o)
        o.data.transform(Matrix.Translation((-x0, -RIN_EMBED, 0)))
        # exact length: the terminal palmettes may overhang the run by ~25 mm; squeeze along X so the panel is
        # exactly `run` long and ends flush with ARCH's socket run (mismatch 0.0 mm).
        (_, ymin, _), (xw, ymax, zh) = L.bbox(o)
        if xw > 1e-6:
            o.data.transform(Matrix.Diagonal((run / xw, 1.0, 1.0, 1.0)))
        # hard cap on the relief so the clearance to the architrave crown plane (d 0.44 vs frieze d 0.34 =
        # RIN_CROWN_CLEAR) is guaranteed, not hoped for
        if ymax > RIN_MAX_PROUD:
            f = (RIN_MAX_PROUD - ymin) / (ymax - ymin)
            o.data.transform(Matrix.Translation((0, ymin, 0)) @ Matrix.Diagonal((1.0, f, 1.0, 1.0))
                             @ Matrix.Translation((0, -ymin, 0)))
        # the carved field is centred in the 0.90 m band with a plain margin top and bottom (finalize_asset put
        # the bbox bottom at z = 0; the socket is at the BOTTOM of the band, so the margin has to be re-added)
        if zh > 1e-6:
            o.data.transform(Matrix.Diagonal((1.0, 1.0, RIN_FIELD_H / zh, 1.0)))
            o.data.transform(Matrix.Translation((0, 0, 0.5 * (RIN_BAND_H - RIN_FIELD_H))))
        (a0, b0, c0), (a1, b1, c1) = L.bbox(o)
        o["size"] = f"{a1 - a0:.2f} x {b1 - b0:.2f} x {c1 - c0:.2f} m (x y z)"
        o["origin_x"] = "run start"
    return lods


def build_type(typ, variants, bake):
    coll = L.rebuild_type(typ)
    t = time.time()
    for v in range(1, variants + 1):
        if typ.startswith("capital_"):
            build_capital(typ, v, coll, bake=bake)
        elif typ == "maiden":
            build_maiden(v, coll, bake=bake)
        elif typ in BUILDERS:
            BUILDERS[typ](v, coll, bake=bake)
        else:
            raise KeyError(typ)
        L.clear_work()
    print(f"[orn] built {typ} x{variants} in {time.time() - t:.0f}s")


BUILDERS = {
    "attic_figure": build_attic_figure, "winged_figure": build_winged_figure, "urn": build_urn,
    "urn_niche": build_urn_niche, "urn_tub": build_urn_tub, "keystone": build_keystone, "finial": build_finial,
    "rosette_ceiling": build_rosette, "attic_panel": build_attic_panel, "drum_band": build_drum_band,
    "corner_scroll": build_corner_scroll,
    "frieze_rinceau": lambda v, c, bake=True: build_frieze_rinceau("frieze_rinceau", v, c, bake),
    "frieze_rinceau_return": lambda v, c, bake=True: build_frieze_rinceau("frieze_rinceau_return", v, c, bake),
    "dentil": lambda v, c, bake=True: build_moulding("dentil", v, c, bake),
    "egg_and_dart": lambda v, c, bake=True: build_moulding("egg_and_dart", v, c, bake),
    "greek_key": lambda v, c, bake=True: build_moulding("greek_key", v, c, bake),
    "rosette_band": lambda v, c, bake=True: build_moulding("rosette_band", v, c, bake),
    "modillion": lambda v, c, bake=True: build_moulding("modillion", v, c, bake),
    "anthemion": lambda v, c, bake=True: build_moulding("anthemion", v, c, bake),
}
ALL_TYPES = ["capital_rotunda", "maiden", "capital_colonnade", "capital_inner", "attic_figure", "urn", "urn_niche",
             "urn_tub", "attic_panel", "keystone", "winged_figure", "finial", "corner_scroll", "drum_band", "rosette_ceiling",
             "dentil", "egg_and_dart", "greek_key", "rosette_band", "modillion", "anthemion",
             "frieze_rinceau", "frieze_rinceau_return"]
VARIANTS = {"capital_rotunda": 3, "capital_inner": 2, "capital_colonnade": 3, "maiden": 3, "attic_figure": 2,
            "urn": 3, "urn_niche": 2, "urn_tub": 1, "keystone": 3, "winged_figure": 2, "finial": 1, "rosette_ceiling": 3,
            "attic_panel": 3, "drum_band": 1, "dentil": 1, "egg_and_dart": 1, "greek_key": 1, "rosette_band": 1,
            "modillion": 1, "anthemion": 1, "corner_scroll": 2, "frieze_rinceau": 3, "frieze_rinceau_return": 3}


def bake_pending():
    """`--bake-pending`: list every asset whose LOD1 carries no baked normal map, and print the exact command that
    bakes them. Nothing is built or written. A Cycles bake is GPU work, so no-GPU rounds build with `--no-bake`
    and this list is how the pending state is handed to a round that may use the GPU (ORN r5 review finding 6)."""
    import re as _re
    src = common.ASSET_FILES["ORN"]
    bpy.ops.wm.open_mainfile(filepath=str(src), load_ui=False)
    pat = _re.compile(r"^ORN_(.+?)_v(\d+)_LOD1$")
    nrm, ao_only, done = {}, {}, {}
    for o in sorted(bpy.data.objects, key=lambda o: o.name):
        m = pat.match(o.name)
        if not m or o.type != "MESH":
            continue
        typ, var = m.group(1), int(m.group(2))
        if not (o.get("normal_map") or ""):
            nrm.setdefault(typ, []).append(var)
        elif not (o.get("ao_map") or ""):
            ao_only.setdefault(typ, []).append(var)
        else:
            done.setdefault(typ, []).append(var)
    print(f"\n[orn] bake state of {src}")
    print(f"  normal map PENDING : {sum(len(v) for v in nrm.values()):3d} LOD1 objects in {len(nrm)} types")
    print(f"  normal only, no AO : {sum(len(v) for v in ao_only.values()):3d} LOD1 objects in {len(ao_only)} types")
    print(f"  normal + AO baked  : {sum(len(v) for v in done.values()):3d} LOD1 objects in {len(done)} types")
    for label, d in (("PENDING normal map", nrm), ("no AO map", ao_only), ("baked", done)):
        for t in sorted(d):
            print(f"    {label:20s} {t:26s} v{','.join(str(v) for v in sorted(d[t]))}")
    if nrm:
        types = ",".join(sorted(nrm))
        print("\n[orn] run this in a round that may use the GPU (rebuilds + bakes only these types, idempotent):")
        print(f"  scripts/blender_run.sh 3600 -- --background --python scripts/orn_build.py -- --only {types}")
        print("[orn] then re-run the stats gate:")
        print("  scripts/blender_run.sh 900 -- --background --python scripts/orn_r5_stats.py")
    else:
        print("\n[orn] nothing pending: every LOD1 has a normal map.")
    return 0 if not nrm else 0


def main():
    if "--bake-pending" in ARGS:
        bake_pending()
        return
    only = None
    if "--only" in ARGS:
        only = [s.strip() for s in ARGS[ARGS.index("--only") + 1].split(",") if s.strip()]
    src = common.ASSET_FILES["ORN"] if "--out" in ARGS else OUT
    if only and src.exists() and "--fresh" not in ARGS:
        bpy.ops.wm.open_mainfile(filepath=str(src))
    else:
        bpy.ops.wm.read_homefile(use_empty=True)
        common.wipe_scene()
    scene = common.setup_scene()
    L.orn_collection()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    failed = []
    for typ in (only or ALL_TYPES):
        n = min(VARIANTS.get(typ, 1), NVAR) if "--variants" in ARGS else VARIANTS.get(typ, 1)
        try:
            build_type(typ, n, BAKE)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[orn] ERROR building {typ}: {e}")
            failed.append(typ)
            L.clear_work()
        if "--no-checkpoint" not in ARGS:
            common.set_lod_visibility(1)
            bpy.ops.wm.save_as_mainfile(filepath=str(OUT), relative_remap=True, compress=False)
    release_scans()
    L.clear_work()
    common.set_lod_visibility(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT), relative_remap=True, compress=True)
    if failed:
        print(f"[orn] FAILED types: {failed}")
    print(f"[orn] saved {OUT}")
    print(L.report())


if __name__ == "__main__":
    main()
