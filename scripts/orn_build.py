"""Build the ornament library assets/ornament.blend (collection ORN) headless and idempotently.

    blender --background --python scripts/orn_build.py -- [--only capital_rotunda,maiden] [--no-bake] [--fast]
                                                          [--variants N] [--fresh] [--out other.blend]

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
BELL_PROFILE = [(0.97, 0.0), (1.05, 0.012), (1.085, 0.035), (1.05, 0.058), (1.00, 0.075), (0.99, 0.12), (0.99, 0.30),
                (1.02, 0.50), (1.08, 0.66), (1.16, 0.78), (1.24, 0.86), (1.30, 0.89)]

CAPITAL_PRESETS = {
    # rotunda: h 2.6, shaft top D 2.1, abacus ~3.0 across; figured centre
    "capital_rotunda": dict(H=2.6, R=1.05, abacus_across=3.0, figure=True, lower_len=0.42, upper_len=0.50,
                            lower_w=1.12, upper_w=1.15, ribs=9, curl=0.32, droop=0.18, volute_r=0.165, helix_r=0.08,
                            lower_z=0.075, upper_z=0.34, rows=2, voxel=0.014, leaf_tilt=(9.0, 11.0)),
    # inner tan columns: h 1.8 on a ~1.6 m shaft, same design, fleuron centre
    "capital_inner": dict(H=1.8, R=0.80, abacus_across=2.15, figure=False, lower_len=0.42, upper_len=0.50,
                          lower_w=1.12, upper_w=1.15, ribs=9, curl=0.32, droop=0.18, volute_r=0.165, helix_r=0.085,
                          lower_z=0.075, upper_z=0.34, rows=2, voxel=0.010, leaf_tilt=(9.0, 11.0)),
    # colonnade: h 1.8 on a 1.7 m shaft: squatter, big shell leaves + big scrolls, small lower leaves, fleuron
    "capital_colonnade": dict(H=1.8, R=0.85, abacus_across=2.3, figure=False, lower_len=0.30, upper_len=0.54,
                              lower_w=1.0, upper_w=1.18, ribs=9, curl=0.30, droop=0.16, volute_r=0.18, helix_r=0.085,
                              lower_z=0.075, upper_z=0.24, rows=2, voxel=0.010, leaf_tilt=(8.0, 10.0)),
}


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


def build_abacus(name, P, coll):
    R, H = P["R"], P["H"]
    outline = abacus_outline(R, P["abacus_across"])
    # moulding profile: (scale, z) from bottom fillet to top
    prof = [(0.86, 0.89), (0.88, 0.905), (0.90, 0.92), (0.955, 0.955), (0.985, 0.975), (1.0, 0.985), (1.0, 1.0)]
    rings = []
    for s, z in prof:
        rings.append([Vector((p.x * s, p.y * s, z * H)) for p in outline])
    ab = L.loft_rings(name, rings, coll)
    L.shade_smooth(ab, sharp_angle_deg=40)
    return ab


def build_leaf_ring(P, count, offset_deg, base_z, length_H, width_scale, rng, coll, tag, row):
    R, H = P["R"], P["H"]
    r_bell = 0.985 * R if row == 0 else 1.0 * R
    leaves = []
    circ = TAU * r_bell
    width = circ / count * width_scale
    for k in range(count):
        phi = offset_deg + k * (360.0 / count) + rng.uniform(-2.0, 2.0)
        ln = length_H * H * rng.uniform(0.95, 1.05)
        curl_row = P["curl"] * (1.0 if row == 0 else 1.5)
        droop_row = P["droop"] * (1.0 if row == 0 else 1.4)
        leaf = L.acanthus_leaf(f"leaf_{tag}_{k}", length=ln, width=width, curl=curl_row * rng.uniform(0.9, 1.1),
                               droop=droop_row * rng.uniform(0.85, 1.15), ribs=P["ribs"], rib_amp=0.018 * R,
                               bulge=0.09 * R, thickness=0.065 * R, lobes=4, lobe_depth=0.12, nu=20, nv=26, coll=coll,
                               seed=rng.randint(0, 9999), base_width=0.30)
        tilt = -P["leaf_tilt"][row] + rng.uniform(-1.5, 1.5)
        place(leaf, rot_z_deg=phi - 90.0, loc=(r_bell * 0.96 * math.cos(math.radians(phi)),
                                                r_bell * 0.96 * math.sin(math.radians(phi)), base_z * H), tilt_x_deg=tilt)
        leaves.append(leaf)
    return leaves


def build_capital_figure(P, phi_deg, rng, coll):
    """Half-length female figure at a face centre (rotunda capitals only): torso rising from the upper leaves,
    head under the abacus, arms spread down to the inner helices."""
    R, H = P["R"], P["H"]
    r_fig = 1.24 * R
    F = 1.35
    j = {
        "hip": (Vector((0, -0.06 * R, 0.40 * H)), (0.16 * R * F, 0.11 * R * F)),
        "waist": (Vector((0, -0.01 * R, 0.51 * H)), (0.13 * R * F, 0.09 * R * F)),
        "chest": (Vector((0, 0.04 * R, 0.635 * H)), (0.17 * R * F, 0.115 * R * F)),
        "neck": (Vector((0, 0.06 * R, 0.735 * H)), (0.06 * R * F, 0.06 * R * F)),
        "head": (Vector((0, 0.07 * R, 0.805 * H)), (0.11 * R * F, 0.12 * R * F)),
        "shl": (Vector((0.24 * R, 0.01 * R, 0.705 * H)), (0.07 * R * F, 0.07 * R * F)),
        "shr": (Vector((-0.24 * R, 0.01 * R, 0.705 * H)), (0.07 * R * F, 0.07 * R * F)),
        "ell": (Vector((0.42 * R, 0.07 * R, 0.62 * H)), (0.055 * R * F, 0.055 * R * F)),
        "elr": (Vector((-0.42 * R, 0.07 * R, 0.62 * H)), (0.055 * R * F, 0.055 * R * F)),
        "hal": (Vector((0.52 * R, 0.13 * R, 0.56 * H)), (0.05 * R * F, 0.045 * R * F)),
        "har": (Vector((-0.52 * R, 0.13 * R, 0.56 * H)), (0.05 * R * F, 0.045 * R * F)),
    }
    bones = [("hip", "waist"), ("waist", "chest"), ("chest", "neck"), ("neck", "head"), ("chest", "shl"), ("chest", "shr"),
             ("shl", "ell"), ("shr", "elr"), ("ell", "hal"), ("elr", "har")]
    fig = L.skin_figure(f"capfig_{int(phi_deg)}", j, bones, coll, subdiv=2)
    bun = L.sphere(f"capfig_bun_{int(phi_deg)}", 0.10 * R, coll, location=(0, -0.08 * R, 0.84 * H))
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
    place(ros, rot_z_deg=phi_deg - 90.0, loc=(r_face * math.cos(math.radians(phi_deg)), r_face * math.sin(math.radians(phi_deg)), 0.935 * H))
    return ros


def build_capital(typ, variant, coll, bake=True):
    P = CAPITAL_PRESETS[typ]
    R, H = P["R"], P["H"]
    rng = random.Random(7919 * variant + len(typ))
    work = L.work_collection()
    parts = []
    bell = L.revolve("bell", L.resample_profile([(r * R, z * H) for r, z in BELL_PROFILE], 36), segments=64, coll=work)
    parts.append(bell)
    parts.append(build_abacus("abacus", P, work))
    # leaves
    parts += build_leaf_ring(P, 8, 0.0, P["lower_z"], P["lower_len"], P["lower_w"], rng, work, "lo", 0)
    parts += build_leaf_ring(P, 8, 22.5, P["upper_z"], P["upper_len"], P["upper_w"], rng, work, "up", 1)
    # volutes: two per corner (one facing each side), stems rising from the gaps between the upper leaves
    eye_r = 1.30 * R
    eye_z = 0.76 * H
    for face in (0, 90, 180, 270):
        for sign in (+1, -1):
            phi_c = face + sign * 45.0
            n_dir = face + sign * 22.0
            eye = Vector((eye_r * math.cos(math.radians(phi_c)), eye_r * math.sin(math.radians(phi_c)), eye_z))
            eye -= Vector((math.cos(math.radians(phi_c)), math.sin(math.radians(phi_c)), 0)) * 0.03 * R
            # local frame: X = radial at n_dir, Y = tangential (increasing phi)
            v = L.volute(f"vol_{face}_{sign}", eye=(0, 0, 0), radius=P["volute_r"] * H, turns=1.8,
                         band=(0.30 * R, 0.14 * R), stem_base=(-0.26 * R, -sign * 0.22 * R, -0.30 * H),
                         stem_ctrl=(-0.14 * R, -sign * 0.10 * R, -0.12 * H), coll=work, direction=sign, taper=0.45)
            place(v, rot_z_deg=n_dir, loc=eye)
            parts.append(v)
        # inner helices flanking the face centre, rolling toward the centre
        for sign in (+1, -1):
            phi_h = face + sign * 16.0
            eye = Vector((1.31 * R * math.cos(math.radians(phi_h)), 1.31 * R * math.sin(math.radians(phi_h)), 0.735 * H))
            v = L.volute(f"hel_{face}_{sign}", eye=(0, 0, 0), radius=P["helix_r"] * H, turns=1.6,
                         band=(0.18 * R, 0.10 * R), stem_base=(-0.22 * R, sign * 0.18 * R, -0.26 * H),
                         stem_ctrl=(-0.11 * R, sign * 0.07 * R, -0.10 * H), coll=work, direction=-sign, taper=0.4)
            place(v, rot_z_deg=face + sign * 8.0, loc=eye)
            parts.append(v)
        if P["figure"]:
            parts += build_capital_figure(P, face, rng, work)
        else:
            parts.append(build_fleuron(P, face, work))
    # union into one cast-concrete surface, soften, weather
    t = time.time()
    voxel = P["voxel"] * (1.6 if FAST else 1.0)
    hi = L.union_blob(parts, f"{typ}_v{variant}", voxel=voxel, smooth=2, smooth_factor=0.5, coll=work, adaptivity=0.4)
    print(f"[orn] {typ} v{variant}: remesh {L.tri_count(hi)} tris in {time.time() - t:.1f}s")
    L.displace_noise(hi, strength=0.006 * R, size=0.12 * R, seed=100 + variant, depth=2)
    L.displace_noise(hi, strength=0.0025 * R, size=0.025 * R, seed=200 + variant, depth=1)
    # LOD2: bell + abacus only
    bell2 = L.revolve("bell2", L.resample_profile([(r * R, z * H) for r, z in BELL_PROFILE], 8), segments=16, coll=work)
    ab2 = L.loft_rings("ab2", [[Vector((p.x * s, p.y * s, z * H)) for p in abacus_outline(R, P["abacus_across"], per_side=4)]
                                for s, z in ((0.87, 0.89), (1.0, 0.985), (1.0, 1.0))], work)
    lod2 = L.join([bell2, ab2], f"{typ}_v{variant}_lod2", work)
    return L.finalize_asset(hi, typ, variant, coll, bake=bake, bake_size=2048, lod2_obj=lod2,
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
    """Ellerhusen weeping maiden, 4.5 m: stands at a planter-box corner, back to the outside (+Y), forearms on the
    box rim (rim 3.55 m above the feet; box corner edge at local (0, -0.32)), head bowed into the box."""
    rng = random.Random(4242 + variant)
    work = L.work_collection()
    S = 4.5 / 1.75
    lean = 0.22 + rng.uniform(-0.03, 0.03)          # forward (-Y) shift of the shoulders
    bow = 0.22 + rng.uniform(-0.03, 0.03)           # head forward
    corner = Vector((0.0, -0.32, 0.0))
    rim_z = 3.55
    def rim_point(side, d):
        dirv = Vector((side * 0.7071, -0.7071, 0.0))
        return corner + dirv * d
    parts = []
    # body proxy
    j = {
        "pelvis": (Vector((0, 0.0, 2.40)), (0.36, 0.23)),
        "hipL": (Vector((0.20, 0.0, 2.30)), (0.21, 0.19)), "hipR": (Vector((-0.20, 0.0, 2.30)), (0.21, 0.19)),
        "kneeL": (Vector((0.18, -0.02, 1.25)), (0.16, 0.16)), "kneeR": (Vector((-0.17, 0.0, 1.22)), (0.16, 0.16)),
        "ankL": (Vector((0.17, 0.02, 0.25)), (0.10, 0.11)), "ankR": (Vector((-0.16, 0.04, 0.25)), (0.10, 0.11)),
        "waist": (Vector((0, -0.03 - lean * 0.3, 2.78)), (0.27, 0.18)),
        "chest": (Vector((0, -lean * 0.7, 3.28)), (0.35, 0.22)),
        "shL": (Vector((0.56, -lean, 3.70)), (0.16, 0.14)), "shR": (Vector((-0.56, -lean, 3.70)), (0.16, 0.14)),
        "neck": (Vector((0, -lean - 0.03, 3.86)), (0.12, 0.12)),
        "head": (Vector((0, -lean - bow, 4.10)), (0.24, 0.27)),
    }
    for side, tag in ((1, "L"), (-1, "R")):
        el = rim_point(side, 0.45) + Vector((0, 0, rim_z + 0.06))
        ha = rim_point(side, 1.12) + Vector((0, 0, rim_z + 0.05))
        j["el" + tag] = (el, (0.11, 0.10))
        j["ha" + tag] = (ha, (0.09, 0.05))
    bones = [("pelvis", "hipL"), ("pelvis", "hipR"), ("hipL", "kneeL"), ("hipR", "kneeR"), ("kneeL", "ankL"),
             ("kneeR", "ankR"), ("pelvis", "waist"), ("waist", "chest"), ("chest", "shL"), ("chest", "shR"),
             ("chest", "neck"), ("neck", "head"), ("shL", "elL"), ("shR", "elR"), ("elL", "haL"), ("elR", "haR")]
    body = L.skin_figure("maiden_body", j, bones, work, subdiv=2)
    parts.append(body)
    # hair: bound in a bun at the back of the bowed head
    hc = j["head"][0]
    parts.append(L.sphere("maiden_hair", 0.23, work, location=hc + Vector((0, 0.10, 0.08)), scale=(1.05, 0.95, 0.85)))
    parts.append(L.sphere("maiden_bun", 0.13, work, location=hc + Vector((0, 0.27, 0.16))))
    # garment: peplos from the shoulders to the ground, folds on the back and sides
    ly = -lean
    sections = [
        (0.03, 0.0, 0.02, 0.62 + rng.uniform(-0.04, 0.04), 0.54),
        (0.60, 0.0, 0.01, 0.55, 0.47),
        (1.30, 0.0, 0.0, 0.48, 0.40),
        (2.10, 0.0, 0.0, 0.44, 0.33),
        (2.45, 0.0, 0.0, 0.43, 0.30),
        (2.80, 0.0, ly * 0.3, 0.37, 0.26),
        (3.30, 0.0, ly * 0.65, 0.45, 0.28),
        (3.60, 0.0, ly * 0.9, 0.56, 0.27),
        (3.74, 0.0, ly, 0.46, 0.24),
        (3.84, 0.0, ly, 0.28, 0.19),
        (3.94, 0.0, ly - 0.02, 0.14, 0.14),
    ]
    folds = rng.choice([9, 10, 11, 12])
    gar = drapery_tube("maiden_peplos", sections, work, folds=folds, fold_amp=(0.015, 0.11 + rng.uniform(-0.01, 0.015)),
                       seed=variant * 31, fold_side=(90.0, 120.0), sharp=0.6)
    parts.append(gar)
    # overfold (apoptygma) from the shoulders to the hips, a little wider, with its own folds
    zo = 2.30 + rng.uniform(-0.1, 0.1)
    over = drapery_tube("maiden_overfold", [(zo, 0.0, 0.03, 0.46, 0.34),
                                            (zo + 0.25, 0.0, 0.03, 0.44, 0.32),
                                            (2.80, 0.0, ly * 0.3 + 0.03, 0.39, 0.28),
                                            (3.30, 0.0, ly * 0.65 + 0.03, 0.47, 0.30),
                                            (3.60, 0.0, ly * 0.9 + 0.02, 0.57, 0.28),
                                            (3.76, 0.0, ly, 0.42, 0.23)],
                        work, folds=folds + 2, fold_amp=(0.02, 0.07), seed=variant * 31 + 5, fold_side=(90.0, 120.0), nz=40)
    # dipping hem: pull the overfold's bottom down at the sides and up at the back centre
    for v in over.data.vertices:
        if v.co.z < zo + 0.3:
            ang = math.atan2(v.co.y, v.co.x)
            v.co.z -= 0.12 * abs(math.cos(ang)) * max(0.0, 1.0 - (v.co.z - zo) / 0.3)
    parts.append(over)
    # sleeve/fold cascades hanging from the forearms over the rim
    for side, tag in ((1, "L"), (-1, "R")):
        el = j["el" + tag][0]
        casc = drapery_tube(f"maiden_casc{tag}", [(el.z - 0.9, el.x + side * 0.05, el.y + 0.05, 0.16, 0.13),
                                                   (el.z - 0.3, el.x, el.y + 0.02, 0.15, 0.12),
                                                   (el.z + 0.05, el.x, el.y, 0.12, 0.11)],
                            work, folds=5, fold_amp=(0.02, 0.10), seed=variant * 7 + side, nu=40, nz=20)
        parts.append(casc)
    t = time.time()
    hi = L.union_blob(parts, f"maiden_v{variant}", voxel=(0.03 if FAST else 0.02), smooth=3, smooth_factor=0.5, coll=work)
    print(f"[orn] maiden v{variant}: remesh {L.tri_count(hi)} tris in {time.time() - t:.1f}s")
    L.displace_noise(hi, strength=0.010, size=0.35, seed=300 + variant, depth=2)
    L.displace_noise(hi, strength=0.003, size=0.05, seed=400 + variant, depth=1)
    return L.finalize_asset(hi, "maiden", variant, coll, bake=bake, bake_size=2048, y_mode="keep",
                            size_note="4.5 m standing (head bowed: 4.3 m tall); rim at +3.55 m; box corner at (0, -0.32)",
                            extra_props={"rim_height": rim_z, "box_corner_y": -0.32})


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
    out = {k: (Vector(v[0]) * S, (v[1][0] * S, v[1][1] * S)) for k, v in J.items()}
    return out


HUMAN_BONES = [("pelvis", "hipL"), ("pelvis", "hipR"), ("hipL", "kneeL"), ("hipR", "kneeR"), ("kneeL", "ankL"),
               ("kneeR", "ankR"), ("ankL", "footL"), ("ankR", "footR"), ("pelvis", "waist"), ("waist", "chest"),
               ("chest", "shL"), ("chest", "shR"), ("chest", "neck"), ("neck", "head"), ("shL", "elL"), ("shR", "elR"),
               ("elL", "haL"), ("elR", "haR")]


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
        parts.append(drapery_tube("attic_wrap", secs, work, folds=rng.choice([6, 7, 8]), fold_amp=(0.03, 0.12),
                                  seed=variant * 13, fold_side=(90.0, 130.0), nu=80, nz=60, sharp=0.6))
        # mantle hanging behind the shoulders to the calves, seen beside the torso
        msecs = [(0.35 * S, 0.0, -0.12 * S, 0.34 * S, 0.07 * S), (0.9 * S, 0.0, -0.12 * S, 0.33 * S, 0.075 * S),
                 (1.30 * S, 0.0, -0.10 * S, 0.30 * S, 0.07 * S), (1.47 * S, 0.0, -0.06 * S, 0.24 * S, 0.06 * S)]
        parts.append(drapery_tube("attic_mantle", msecs, work, folds=9, fold_amp=(0.06, 0.16), seed=variant * 17,
                                  nu=64, nz=40, power=3.0, sharp=0.55))
    else:
        parts.append(L.sphere("attic_hair", 0.115 * S, work, location=hc + Vector((0, -0.02 * S, 0.035 * S)), scale=(1.05, 1.0, 0.85)))
        parts.append(L.sphere("attic_bun", 0.06 * S, work, location=hc + Vector((0, -0.11 * S, 0.06 * S))))
        secs = [(0.03 * S, 0.0, 0.02 * S, 0.29 * S, 0.23 * S), (0.35 * S, 0.0, 0.01 * S, 0.25 * S, 0.19 * S),
                (0.70 * S, 0.0, 0.0, 0.22 * S, 0.165 * S), (0.95 * S, 0.0, 0.0, 0.215 * S, 0.15 * S),
                (1.12 * S, 0.0, 0.0, 0.19 * S, 0.13 * S), (1.33 * S, 0.0, 0.01 * S, 0.22 * S, 0.145 * S),
                (1.44 * S, 0.0, 0.01 * S, 0.245 * S, 0.12 * S), (1.50 * S, 0.0, 0.01 * S, 0.14 * S, 0.09 * S),
                (1.55 * S, 0.0, 0.015 * S, 0.07 * S, 0.07 * S)]
        parts.append(drapery_tube("attic_gown", secs, work, folds=rng.choice([9, 10, 11]), fold_amp=(0.02, 0.10),
                                  seed=variant * 13, fold_side=(90.0, 140.0), nu=96, nz=80, sharp=0.6))
        # overfold to the hips
        osecs = [(0.98 * S, 0.0, 0.03 * S, 0.24 * S, 0.17 * S), (1.15 * S, 0.0, 0.02 * S, 0.21 * S, 0.15 * S),
                 (1.34 * S, 0.0, 0.02 * S, 0.235 * S, 0.155 * S), (1.45 * S, 0.0, 0.02 * S, 0.25 * S, 0.13 * S),
                 (1.50 * S, 0.0, 0.02 * S, 0.15 * S, 0.10 * S)]
        parts.append(drapery_tube("attic_over", osecs, work, folds=12, fold_amp=(0.02, 0.08), seed=variant * 19,
                                  fold_side=(90.0, 140.0), nu=80, nz=30))
    t = time.time()
    hi = L.union_blob(parts, f"attic_figure_v{variant}", voxel=(0.045 if FAST else 0.028), smooth=3, coll=work)
    print(f"[orn] attic_figure v{variant}: remesh {L.tri_count(hi)} tris in {time.time() - t:.1f}s")
    L.displace_noise(hi, strength=0.014, size=0.5, seed=500 + variant, depth=2)
    L.displace_noise(hi, strength=0.004, size=0.07, seed=600 + variant, depth=1)
    return L.finalize_asset(hi, "attic_figure", variant, coll, bake=bake, bake_size=2048, y_mode="keep",
                            size_note="6.7 m (22 ft) standing, faces +Y; odd variants male, even female")


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
    # back plate hugging the archivolt
    parts.append(L.box("ks_back", (0.62, 0.10, 0.62), work, location=(0, 0.05, 0.0), bevel=0.03))
    face = L.sphere("ks_face", 0.24, work, location=(0, 0.16, 0.02), scale=(1.0, 0.75, 1.05))
    parts.append(face)
    parts.append(L.sphere("ks_muzzle", 0.14, work, location=(0, 0.33, -0.05), scale=(1.15, 0.9, 0.85)))
    parts.append(L.sphere("ks_nose", 0.055, work, location=(0, 0.44, -0.01), scale=(1.2, 0.8, 0.7)))
    parts.append(L.sphere("ks_jaw", 0.11, work, location=(0, 0.30, -0.17), scale=(1.1, 0.9, 0.7)))
    for side in (1, -1):
        parts.append(L.sphere(f"ks_brow{side}", 0.07, work, location=(side * 0.10, 0.34, 0.09), scale=(1.4, 0.8, 0.7)))
        parts.append(L.sphere(f"ks_cheek{side}", 0.09, work, location=(side * 0.15, 0.30, -0.06)))
        parts.append(L.sphere(f"ks_ear{side}", 0.06, work, location=(side * 0.20, 0.20, 0.20), scale=(1.0, 0.6, 1.2)))
    # mane: ring of leaves radiating in the mask plane, tilted forward
    n = 14
    for i in range(n):
        ang = i * 360.0 / n + rng.uniform(-4, 4)
        leaf = L.acanthus_leaf(f"ks_mane{i}", length=0.25 * rng.uniform(0.85, 1.1), width=0.16, curl=0.5, droop=0.25,
                               ribs=5, rib_amp=0.012, bulge=0.02, thickness=0.02, lobes=3, lobe_depth=0.15, nu=10, nv=14,
                               coll=work, seed=i, base_width=0.4)
        # leaf grows along +Z, curls toward +Y: rotate so it radiates at 'ang' in the XZ plane, base at the face rim
        m = (Matrix.Translation((0.22 * math.sin(math.radians(ang)), 0.14, 0.03 + 0.22 * math.cos(math.radians(ang))))
             @ Euler((0, math.radians(ang), 0), "XYZ").to_matrix().to_4x4()
             @ Euler((math.radians(-25), 0, 0), "XYZ").to_matrix().to_4x4())
        leaf.data.transform(m)
        parts.append(leaf)
    hi = L.union_blob(parts, f"keystone_v{variant}", voxel=(0.01 if FAST else 0.006), smooth=2, coll=work)
    # open mouth: push a recess in with a sphere (boolean difference)
    cutter = L.sphere("ks_mouth", 0.075, work, location=(0, 0.42, -0.10), scale=(1.3, 1.0, 0.7))
    for side in (1, -1):
        L.sphere(f"ks_eye{side}", 0.035, work, location=(side * 0.085, 0.395, 0.055))
    for name in ("ks_mouth", "ks_eye1", "ks_eye-1"):
        cut = bpy.data.objects[name]
        m = hi.modifiers.new("Bool", "BOOLEAN")
        m.operation = "DIFFERENCE"
        m.solver = "EXACT"
        m.object = cut
        L.apply_all(hi)
        L.remove_object(cut)
    L.displace_noise(hi, strength=0.003, size=0.05, seed=1200 + variant, depth=2)
    return L.finalize_asset(hi, "keystone", variant, coll, bake=bake, bake_size=1024, y_mode="back",
                            budgets=L.BUDGETS["keystone"], size_note="lion mask 0.8 m; origin = back-face bottom-centre")


def build_finial(variant, coll, bake=True):
    """Dome apex cap: a small metal-clad nub (085 shows only a tiny nub): 0.6 m."""
    work = L.work_collection()
    prof = [(0.40, 0.0), (0.40, 0.06), (0.30, 0.10), (0.24, 0.18), (0.26, 0.24), (0.22, 0.30), (0.14, 0.40),
            (0.12, 0.44), (0.16, 0.48), (0.10, 0.54), (0.04, 0.60), (0.0, 0.60)]
    fin = L.revolve("finial", L.resample_profile(prof, 30), segments=48, coll=work)
    hi = L.union_blob([fin], f"finial_v{variant}", voxel=0.006, smooth=1, coll=work)
    return L.finalize_asset(hi, "finial", variant, coll, bake=bake, bake_size=512, budgets=L.BUDGETS["finial"],
                            size_note="dome apex cap 0.8 m diameter x 0.6 m")


def build_rosette(variant, coll, bake=True):
    """Coffer rosette for the plaster ceiling, 0.6 m diameter: two rings of petals around a boss. Origin at the
    back (mounting) face centre; the rosette projects toward +Z... no: like all wall-mounted pieces it projects
    toward +Y (socket +Y = radially outward on the ceiling), so it is built lying in the XZ plane."""
    rng = random.Random(2000 + variant)
    work = L.work_collection()
    prof = [(0.30, 0.0), (0.30, 0.02), (0.26, 0.05), (0.18, 0.08), (0.10, 0.10), (0.06, 0.13), (0.0, 0.14)]
    def petals(th, t):
        return 1.0 + 0.10 * math.cos(12 * th + variant) * (0.3 + 0.7 * (1 - t)) + 0.05 * math.cos(6 * th) * t
    ros = L.revolve("rosette", L.resample_profile(prof, 20), segments=96, coll=work, scale_fn=petals)
    boss = L.sphere("ros_boss", 0.06, work, location=(0, 0, 0.11))
    hi = L.union_blob([ros, boss], f"rosette_ceiling_v{variant}", voxel=0.005, smooth=1, coll=work)
    L.displace_noise(hi, strength=0.002, size=0.03, seed=1300 + variant, depth=1)
    # lay it down: +Z -> +Y
    hi.data.transform(Euler((math.radians(-90), 0, 0), "XYZ").to_matrix().to_4x4())
    return L.finalize_asset(hi, "rosette_ceiling", variant, coll, bake=bake, bake_size=512, y_mode="back",
                            budgets=L.BUDGETS["rosette_ceiling"], size_note="coffer rosette 0.6 m; back face at y=0, projects +Y")


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
    in x, back plane at y=0. Cached per session. Returns a work-collection object (copy it before editing)."""
    if key in _scan_cache and _scan_cache[key].name in bpy.data.objects:
        return _scan_cache[key]
    fname, pre, bgfrac = SCANS[key]
    path = SCAN_DIR / fname
    if not path.exists():
        print(f"[orn] WARNING scan {path} missing")
        return None
    t = time.time()
    bpy.ops.wm.stl_import(filepath=str(path), global_scale=0.01)
    ob = bpy.context.selected_objects[0]
    ob.name = f"scan_{key}"
    L.common.link_object(ob, L.work_collection())
    ob.data.transform(ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)
    if pre is not None:
        ob.data.transform(pre)
    # face +Z / up +Y  ->  face +Y / up +Z  (proper rotation: x -> -x, y <-> z)
    ob.data.transform(Matrix(((-1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1))))
    L.decimate(ob, target=tris)
    (x0, y0, z0), (x1, y1, z1) = L.bbox(ob)
    ob.data.transform(Matrix.Translation((-0.5 * (x0 + x1), -y0, -z0)))
    # background depth: area-weighted median of face-centre y (flat background = few, large faces)
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
    ob["bg_frac"] = med
    bgfrac = med
    ob.data.polygons.foreach_set("use_smooth", [True] * len(ob.data.polygons))
    _scan_cache[key] = ob
    print(f"[orn] scan {key}: {L.tri_count(ob)} tris, {x1 - x0:.2f} x {y1 - y0:.2f} x {z1 - z0:.2f} m, background at {bgfrac:.2f} of depth, in {time.time() - t:.1f}s")
    return ob


def place_scan(key, x, height, depth, slab_face_y, mirror=False, z=0.0, rot_deg=0.0, coll=None):
    """Copy a scan into the panel: scaled to `height` (m) tall and `depth` (m) of relief, its background surface
    sunk to the slab face so only the figures stand proud."""
    src = load_scan(key)
    if src is None:
        return None
    ob = L.duplicate(src, f"rel_{key}_{x:.1f}", coll or L.work_collection())
    (x0, y0, z0), (x1, y1, z1) = L.bbox(ob)
    sz = height / (z1 - z0)
    sy = depth / (y1 - y0)
    m = Matrix.Diagonal((-sz if mirror else sz, sy, sz, 1.0))
    ob.data.transform(m)
    if rot_deg:
        ob.data.transform(Euler((0, math.radians(rot_deg), 0), "XYZ").to_matrix().to_4x4())
    bg = src["bg_frac"] * depth
    ob.data.transform(Matrix.Translation((x, slab_face_y - bg - 0.02, z)))   # background 2 cm behind the face
    return ob


def build_attic_panel(variant, coll, bake=True):
    """One of the three Zimm 'Struggle for the Beautiful' relief designs, field 10.5 x 4.5 m, relief ~0.25 m,
    composed from the public-domain relief scans (cut, scaled, mirrored, embedded, decimated, weathered - lead
    decision: scans only as reworked raw material for these panels). Design 1 = combat with centaur (centre),
    2 = procession (draped spectators), 3 = kneeling/standing group. Origin: back-face bottom-centre; +Y = face."""
    rng = random.Random(6000 + variant)
    work = L.work_collection()
    W, Hh, T = 10.5, 4.5, 0.16
    face_y = T
    parts = [L.box("panel_slab", (W, T, Hh), work, location=(0, T / 2, Hh / 2))]
    depth = 0.40
    design = (variant - 1) % 3 + 1
    if design == 1:
        parts.append(place_scan("centaur", 0.0, 4.2, depth, face_y, z=0.15))
        parts.append(place_scan("soldiers", -3.7, 4.1, depth, face_y, mirror=True, z=0.2))
        parts.append(place_scan("soldiers", 3.7, 4.1, depth, face_y, z=0.2))
    elif design == 2:
        parts.append(place_scan("dacians", -3.6, 4.2, depth, face_y, z=0.15))
        parts.append(place_scan("soldiers", 0.0, 4.1, depth, face_y, z=0.2))
        parts.append(place_scan("dacians", 3.6, 4.2, depth, face_y, mirror=True, z=0.15))
    else:
        parts.append(place_scan("soldiers", -3.6, 4.1, depth, face_y, z=0.2))
        parts.append(place_scan("centaur", 0.0, 4.2, depth, face_y, mirror=True, z=0.15))
        parts.append(place_scan("dacians", 3.7, 4.2, depth, face_y, mirror=True, z=0.15))
    parts = [p for p in parts if p is not None]
    # a few modelled extras so the composition is not just the scans: shields / discs in the gaps
    for i in range(3):
        x = rng.uniform(-4.8, 4.8)
        parts.append(L.sphere(f"shield{i}", rng.uniform(0.25, 0.45), work, location=(x, face_y - 0.05, rng.uniform(0.8, 3.6)), scale=(1.0, 0.25, 1.0)))
    t = time.time()
    hi = L.union_blob(parts, f"attic_panel_v{variant}", voxel=(0.05 if FAST else 0.025), smooth=1, smooth_factor=0.3, coll=work)
    print(f"[orn] attic_panel v{variant}: remesh {L.tri_count(hi)} tris in {time.time() - t:.1f}s")
    L.displace_noise(hi, strength=0.02, size=0.6, seed=1400 + variant, depth=2)
    L.displace_noise(hi, strength=0.006, size=0.08, seed=1500 + variant, depth=1)
    return L.finalize_asset(hi, "attic_panel", variant, coll, bake=bake, bake_size=4096 if not FAST else 2048, y_mode="back",
                            budgets=L.BUDGETS["attic_panel"],
                            size_note=f"Zimm panel design {design}: field 10.5 x 4.5 m, slab 0.16 + relief 0.3 m; origin back-face bottom-centre")


# =============================================================================== LINEAR MOULDINGS (1 m units) + DRUM BAND
def _strip(name, coll, length=1.0, depth=0.05, height=0.2):
    """Backing strip: origin at the bottom-centre of its BACK face, runs along X, projects toward +Y."""
    return L.box(name, (length, depth, height), coll, location=(0, depth / 2, height / 2))


def build_moulding(kind, variant, coll, bake=True):
    """One-metre unit of a repeating moulding, to be arrayed by ARCH along its profile sweeps. Sizes from the
    reference sheet (dentil pitch 0.15, egg-and-dart ~0.17 pitch, Greek key band 0.45-0.5 with 0.45 rosettes,
    modillion brackets, anthemion/palmette band 0.25 pitch)."""
    rng = random.Random(8000 + variant + hash(kind) % 100)
    work = L.work_collection()
    parts = []
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
        # meander: a path of square turns, relief 0.02 on a 0.45 band, two repeats per metre
        band_h = 0.45
        parts.append(_strip("m_back", work, depth=0.03, height=band_h))
        w = 0.035   # line width
        def seg(x0, z0, x1, z1):
            cx, cz = 0.5 * (x0 + x1), 0.5 * (z0 + z1)
            parts.append(L.box(f"key_{len(parts)}", (abs(x1 - x0) + w, 0.02, abs(z1 - z0) + w), work, location=(cx, 0.04, cz)))
        rep = 2
        pw = 1.0 / rep
        for r in range(rep):
            ox = -0.5 + r * pw
            u = pw / 6.0
            zb, zt = 0.07, band_h - 0.07
            zm = 0.5 * (zb + zt)
            # classic meander (one repeat): outer top rail, hook down, inner spiral
            seg(ox + 0.5 * u, zt, ox + 5.5 * u, zt)
            seg(ox + 5.5 * u, zt, ox + 5.5 * u, zb)
            seg(ox + 5.5 * u, zb, ox + 2.0 * u, zb)
            seg(ox + 2.0 * u, zb, ox + 2.0 * u, zm + 0.5 * u)
            seg(ox + 2.0 * u, zm + 0.5 * u, ox + 4.0 * u, zm + 0.5 * u)
            seg(ox + 4.0 * u, zm + 0.5 * u, ox + 4.0 * u, zm - 0.6 * u)
            seg(ox + 0.5 * u, zt, ox + 0.5 * u, zm - 0.6 * u)
        h, d = band_h, 0.05
    elif kind == "rosette_band":
        # rostra band: square rosette bosses 0.45 alternating with meander squares; unit = 1 m = rosette + key field
        band_h = 0.5
        parts.append(_strip("m_back", work, depth=0.03, height=band_h))
        parts.append(L.box("frame", (0.44, 0.02, 0.44), work, location=(-0.27, 0.04, band_h / 2)))
        prof = [(0.19, 0.0), (0.19, 0.01), (0.16, 0.035), (0.10, 0.06), (0.05, 0.075), (0.0, 0.08)]
        def petals(th, t):
            return 1.0 + 0.09 * math.cos(10 * th) * (1 - t)
        ros = L.revolve("rosette", L.resample_profile(prof, 14), segments=64, coll=work, scale_fn=petals)
        ros.data.transform(Euler((math.radians(-90), 0, 0), "XYZ").to_matrix().to_4x4())
        ros.data.transform(Matrix.Translation((-0.27, 0.05, band_h / 2)))
        parts.append(ros)
        w = 0.035
        u = 0.5 / 6.0
        ox = 0.0
        zb, zt = 0.07, band_h - 0.07
        zm = 0.5 * (zb + zt)
        def seg(x0, z0, x1, z1):
            cx, cz = 0.5 * (x0 + x1), 0.5 * (z0 + z1)
            parts.append(L.box(f"key_{len(parts)}", (abs(x1 - x0) + w, 0.02, abs(z1 - z0) + w), work, location=(cx, 0.04, cz)))
        seg(ox + 0.5 * u, zt, ox + 5.5 * u, zt)
        seg(ox + 5.5 * u, zt, ox + 5.5 * u, zb)
        seg(ox + 5.5 * u, zb, ox + 2.0 * u, zb)
        seg(ox + 2.0 * u, zb, ox + 2.0 * u, zm + 0.5 * u)
        seg(ox + 2.0 * u, zm + 0.5 * u, ox + 4.0 * u, zm + 0.5 * u)
        seg(ox + 4.0 * u, zm + 0.5 * u, ox + 4.0 * u, zm - 0.6 * u)
        seg(ox + 0.5 * u, zt, ox + 0.5 * u, zm - 0.6 * u)
        h, d = band_h, 0.08
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
    return L.finalize_asset(hi, kind, variant, coll, bake=bake, bake_size=1024, y_mode="back", budgets=L.BUDGETS["moulding"],
                            size_note=f"1 m unit along X, {h:.2f} m tall, projects {d:.2f} m toward +Y; origin back-face bottom-centre")


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
        # hex lattice of overlapping scale domes (continuous: max over the two nearest rows)
        bump = 0.0
        for row in (int(z / pitch), int(z / pitch) + 1):
            off = pitch / 2 if row % 2 else 0.0
            cx = ((x + 10.0 + off) % pitch) - pitch / 2
            cz = z - (row * pitch - pitch * 0.45)
            d = (cx / (pitch * 0.55)) ** 2 + (cz / (pitch * 0.55)) ** 2
            bump = max(bump, 0.035 * max(0.0, 1.0 - d))
        if not (0.15 < z < Hb - 0.15):
            bump = 0.0
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
    "dentil": lambda v, c, bake=True: build_moulding("dentil", v, c, bake),
    "egg_and_dart": lambda v, c, bake=True: build_moulding("egg_and_dart", v, c, bake),
    "greek_key": lambda v, c, bake=True: build_moulding("greek_key", v, c, bake),
    "rosette_band": lambda v, c, bake=True: build_moulding("rosette_band", v, c, bake),
    "modillion": lambda v, c, bake=True: build_moulding("modillion", v, c, bake),
    "anthemion": lambda v, c, bake=True: build_moulding("anthemion", v, c, bake),
}
ALL_TYPES = ["capital_rotunda", "maiden", "capital_colonnade", "capital_inner", "attic_figure", "urn", "urn_niche",
             "urn_tub", "attic_panel", "keystone", "winged_figure", "finial", "drum_band", "rosette_ceiling",
             "dentil", "egg_and_dart", "greek_key", "rosette_band", "modillion", "anthemion"]
VARIANTS = {"capital_rotunda": 3, "capital_inner": 2, "capital_colonnade": 3, "maiden": 3, "attic_figure": 2,
            "urn": 3, "urn_niche": 2, "urn_tub": 1, "keystone": 2, "winged_figure": 2, "finial": 1, "rosette_ceiling": 2,
            "attic_panel": 3, "drum_band": 1, "dentil": 1, "egg_and_dart": 1, "greek_key": 1, "rosette_band": 1,
            "modillion": 1, "anthemion": 1}


def main():
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
    for typ in (only or ALL_TYPES):
        n = min(VARIANTS.get(typ, 1), NVAR) if "--variants" in ARGS else VARIANTS.get(typ, 1)
        build_type(typ, n, BAKE)
    L.clear_work()
    common.set_lod_visibility(1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT), relative_remap=True, compress=True)
    print(f"[orn] saved {OUT}")
    print(L.report())


if __name__ == "__main__":
    main()
