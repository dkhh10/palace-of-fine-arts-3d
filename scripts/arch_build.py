"""Palace of Fine Arts - architecture builder (rotunda, both colonnades, site platform/rostra, ornament sockets).

    blender --background --python scripts/arch_build.py [-- --preview] [-- --no-save]

Idempotent: starts from an empty file, builds collection ARCH (sub-collections ARCH_rotunda, ARCH_colonnade_north,
ARCH_colonnade_south, ARCH_site, ARCH_sockets, ARCH_placeholders) and saves assets/architecture.blend. With --preview it
then adds a throwaway light/ground rig (NOT saved) and renders the QA cameras into renders/previews/architecture/.
All dimensions come from scripts/arch_params.py (metres, sourced from docs/reference_sheet.md, derivations in
docs/arch_notes.md).
"""
import bpy, bmesh, math, os, sys, time, json
from mathutils import Vector
from mathutils.geometry import normal as face_normal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import arch_params as P
import arch_lib as L
from arch_lib import add2, mul2, norm2, dot2, rot2, SINK

ARGS = common.script_args()
PREVIEW = "--preview" in ARGS
SAVE = "--no-save" not in ARGS
T0 = time.time()

COS22, SIN22, TAN22 = math.cos(math.radians(22.5)), math.sin(math.radians(22.5)), math.tan(math.radians(22.5))


def sub2(a, b):
    return (a[0] - b[0], a[1] - b[1])


def ang_deg(v):
    return math.degrees(math.atan2(v[1], v[0]))


# ============================================================================= scene / collections
bpy.ops.wm.read_homefile(use_empty=True)
common.wipe_scene()
scene = common.setup_scene()
ARCH = common.rebuild_collection("ARCH")


def sub(name):
    return common.get_collection(name, parent=ARCH)


C_ROT = sub("ARCH_rotunda")
C_CN = sub("ARCH_colonnade_north")
C_CS = sub("ARCH_colonnade_south")
C_SITE = sub("ARCH_site")
C_SOCK = sub("ARCH_sockets")
C_PH = sub("ARCH_placeholders")
SOCK = L.SocketCounter(C_SOCK)

M_OCHRE, M_PODIUM, M_ROSE, M_TAN, M_INNER = "MAT_concrete_ochre", "MAT_concrete_podium", "MAT_column_rose", "MAT_column_tan_inner", "MAT_concrete_inner"
M_PLASTER, M_BAND, M_DOME, M_COLON, M_PAVING = "MAT_plaster_ceiling", "MAT_drum_band", "MAT_dome_membrane", "MAT_concrete_colonnade", "MAT_paving"
M_ORN = "MAT_ornament_concrete"
# QA-04-7: the coffer RIB plates used to share the panel material (ceiling ribs M_PLASTER, vault ribs M_INNER), so
# materials had no surface to darken against the panels (ref 083: ribs L 22-50, panels L 93-130). The rib plates now
# carry their own library name. Every object with it is a rib network only; the panels behind the holes are the
# saucer field / barrel soffit and keep their own material. See docs/arch_notes.md "round 3".
M_PLASTER_RIB = "MAT_plaster_ceiling_rib"


# ============================================================================= rotunda frames
def face_dir(k):
    return P.az_dir(P.FACE_AZ0 + 45 * k)


def vertex_dir(k):
    return P.az_dir(P.VERTEX_AZ0 + 45 * k)


class VertexFrame:
    """Pier k at azimuth VERTEX_AZ0 + 45k. Face A = face k (toward vertex k+1), face B = face k-1."""

    def __init__(self, k):
        self.k = k
        self.az = P.VERTEX_AZ0 + 45 * k
        self.v = vertex_dir(k)
        self.V = mul2(self.v, P.WALL_CIRCUMRADIUS)
        self.nA, self.nB = face_dir(k), face_dir(k - 1)
        CA, CB = mul2(self.nA, P.WALL_APOTHEM), mul2(self.nB, P.WALL_APOTHEM)
        self.uA, self.uB = norm2(sub2(CA, self.V)), norm2(sub2(CB, self.V))

    def wall_pt(self, side, along, out=0.0):
        u, n = (self.uA, self.nA) if side == "A" else (self.uB, self.nB)
        return add2(add2(self.V, mul2(u, along)), mul2(n, out))

    def bump(self, along, r_ch, inset=0.0):
        """[wA, cA, cB, wB]: the pier wedge / ressaut / attic corner block plan (A side first)."""
        wA0, wB0 = self.wall_pt("A", along), self.wall_pt("B", along)
        cA = add2(wA0, mul2(self.v, r_ch - dot2(wA0, self.v)))
        cB = add2(wB0, mul2(self.v, r_ch - dot2(wB0, self.v)))
        return [self.wall_pt("A", along, -inset), cA, cB, self.wall_pt("B", along, -inset)]

    def columns(self):
        return [(self.wall_pt("A", P.COL_D_ALONG, P.COL_O_OUT), self.nA, self.uA),
                (self.wall_pt("B", P.COL_D_ALONG, P.COL_O_OUT), self.nB, self.uB)]


FRAMES = [VertexFrame(k) for k in range(8)]


def entablature_plan(along=P.RESSAUT_ALONG, r_ch=P.CHAMFER_CIRCUMRADIUS, inset=0.0):
    pts = []
    for fr in FRAMES:
        wA, cA, cB, wB = fr.bump(along, r_ch, inset)
        pts += [wB, cB, cA, wA]
    return L.ensure_ccw(pts)


# ============================================================================= profiles (d outward, z relative)
# ---------------------------------------------------------------------------------------------------------------
# QA-05-6 / polish round 4: the rotunda cornice rebuilt so it throws the photograph's shadow bands.
#
# Why the old profile could not: the golden-hour sun is az 118.5 / el 7.4 and the hero (lagoon) face normal is
# az 82, so the sun is Delta = 36.5 deg off the face and only 7.4 deg above the horizon. A horizontal ledge then
# drops a shadow of only tan(7.4)/cos(36.5) = 0.16 m per metre of projection -- a 1 m cornice shades 16 cm of the
# frieze. NONE of the photograph's dark bands is a drop shadow. They are:
#   (a) downward-facing soffits, which never see the sun at all and read at 20-25 % of the sunlit wall, and
#   (b) vertical faces hidden BEHIND a projecting course: from cam01 the up-look is ~20 deg, so a projection of
#       p metres lifts a point p * tan(20) = 0.365 m up the frame and hides that much wall behind it, and
#   (c) vertical faces laterally shadowed by the block in front of them: tan(36.5) = 0.74 m of shadow per metre
#       of block depth, which blacks out the gaps between blocks when depth >= gap / 0.74.
# All three are geometry, which is why two rounds of shading work could not supply the band (materials' finding).
#
# Measured on ref 169 at hero scale (14.06 px/m in the 1920x1080 frame, 10.7 px/m in the raw photo; derivations in
# docs/arch_notes.md "Polish round 4"): apparent band heights top-down are bright crown fillet 0.19 m, egg course
# 0.43 m, fascia 0.38 m, modillion band 0.86 m; along the run the egg course repeats at 0.47 m and the modillion
# blocks at 1.07 m. The modillion band's 0.86 m of apparent height fixes the corona projection, since
#   apparent = modillion height + (corona projection - modillion bed) * tan(20 deg).
# Sequence bottom -> top: cyma reversa, dentil band, ovolo, modillion band, egg-and-dart ovolo, corona, cyma recta.
# (The photograph puts the fine 0.47 m course ABOVE the brackets, not below them: the old build had the egg course
# between the dentils and the modillions.)  Dentils / eggs / modillions are block geometry on the beds below.
CORNICE = dict(
    frieze_d=0.20, frieze_z0=1.40, frieze_z1=2.50,
    dentil_z=2.60, dentil_h=0.28, dentil_bed=0.40, dentil_size=0.16, dentil_pitch=0.32, dentil_d=0.30,
    modillion_z=2.96, modillion_h=0.48, modillion_bed=0.62, modillion_w=0.42, modillion_d=0.58, modillion_pitch=1.06,
    egg_z=3.44, egg_h=0.12, egg_bed=0.70, egg_pitch=0.47,
    corona_d=1.72, corona_soffit_z=3.62, corona_z1=3.80)


def rotunda_entablature_profile():
    """d = outward from the wall plane, z relative to ENTABLATURE_Z0. The swept band carries no LOD suffix, so this
    one profile -- every projection in it -- is what both the viewport (LOD1) and the render (LOD0) show."""
    c = CORNICE
    arch = [(0.0, 0.0), (0.14, 0.0), (0.14, 0.46), (0.24, 0.46), (0.24, 0.92), (0.34, 0.92), (0.34, 1.20),
            (0.42, 1.24), (0.42, 1.30),             # bead-and-reel astragal over the third fascia (sheet row 13)
            (0.50, 1.34), (0.50, c["frieze_z0"])]   # architrave crown, projecting 0.50 over a 0.20 frieze
    frieze = [(c["frieze_d"], c["frieze_z0"] + 0.04), (c["frieze_d"], c["frieze_z1"])]
    cornice = [
        (0.22, c["frieze_z1"] + 0.02), (c["dentil_bed"], c["dentil_z"]),           # cyma reversa foot
        (c["dentil_bed"], c["dentil_z"] + c["dentil_h"]),                          # dentil band bed (back face)
        (0.48, 2.92), (c["modillion_bed"], c["modillion_z"]),                      # ovolo under the modillions
        (c["modillion_bed"], c["modillion_z"] + c["modillion_h"]),                 # modillion band bed (back face)
        (0.70, 3.50), (0.80, 3.56), (0.80, c["corona_soffit_z"]),                  # egg-and-dart ovolo + fascia
        (c["corona_d"], c["corona_soffit_z"]),                                     # CORONA SOFFIT: 0.92 m, never sunlit
        (c["corona_d"], 3.74), (c["corona_d"] + 0.04, 3.76),                       # corona fascia + drip
        (1.62, 3.79), (1.40, c["corona_z1"]), (0.0, c["corona_z1"])]               # cyma recta
    return arch + frieze + cornice


def attic_base_profile():
    return [(0.0, 0.0), (0.55, 0.0), (0.55, 0.40), (0.48, 0.48), (0.48, 0.70), (0.34, 0.80), (0.34, 0.86), (0.0, 0.90)]


def attic_top_profile():
    return [(0.0, 0.0), (0.20, 0.05), (0.20, 0.30), (0.40, 0.36), (0.62, 0.50), (0.62, 0.72), (0.74, 0.80), (0.0, 0.80)]


def podium_cap_profile():
    return [(0.0, 0.0), (0.08, 0.0), (0.08, 0.10), (0.0, 0.10)]


def archivolt_profile():
    # (radial from the intrados edge, projection from the wall)
    return [(0.0, 0.0), (0.0, 0.18), (0.22, 0.22), (0.30, 0.30), (0.52, 0.30), (0.60, 0.22), (0.80, 0.18), (0.80, 0.0)]


def colonnade_entablature_profile():
    # architrave with the Greek-fret band recessed 0.04 (z 0.22-0.72), plain frieze, mutule cornice (mutules are geometry)
    right = [(0.80, 0.0), (0.86, 0.02), (0.86, 0.22), (0.82, 0.22), (0.82, 0.72), (0.86, 0.72), (0.86, 0.88), (0.95, 0.94),
             (0.95, 1.0), (0.86, 1.03), (0.86, 1.72), (0.98, 1.78), (1.02, 1.80), (1.02, 2.02), (1.30, 2.06), (1.30, 2.30),
             (1.38, 2.34), (1.38, 2.4)]
    left = [(-d, z) for d, z in reversed(right)]
    return right + left + [right[0]]


# ============================================================================= rotunda
def build_rotunda():
    C = C_ROT
    # ---- outer columns (16): one mesh per LOD, instanced
    r_b, r_t = P.COL_D_BOTTOM / 2, P.COL_D_TOP / 2
    masters = {}
    axes = []
    for fr in FRAMES:
        for (ax, n, u) in fr.columns():
            axes.append((ax, n, u, fr))
    for lod in (0, 1, 2):
        src = None
        for i, (ax, n, u, fr) in enumerate(axes):
            name = f"ARCH_rotunda_column_{i:02d}_LOD{lod}"
            loc = (ax[0], ax[1], P.COL_SHAFT_Z0)
            rz = math.atan2(n[1], n[0])
            if src is None:
                src = L.column_shaft(name, r_b, r_t, P.COL_SHAFT_H, C, lod=lod, mat=M_ROSE, part_type="column",
                                     origin=loc)
                src.rotation_euler = (0, 0, rz)
                masters[lod] = src
            else:
                L.instance(name, src, loc, rz, C)
    # bases (Attic base on a square plinth): plinth box + torus lathe, instanced
    base_src = None
    for i, (ax, n, u, fr) in enumerate(axes):
        loc = (ax[0], ax[1], P.PEDESTAL_TOP_Z - SINK)
        if base_src is None:
            base_src = L.column_base(f"ARCH_rotunda_colbase_{i:02d}", r_b, C, height=P.COL_BASE_H + SINK,
                                     plinth=1.15 * P.COL_D_BOTTOM, mat=M_PODIUM, origin=loc)
            base_src[0].rotation_euler = (0, 0, math.atan2(u[1], u[0]))
        else:
            for j, so in enumerate(base_src):
                L.instance(f"ARCH_rotunda_colbase_{i:02d}_{j}", so, loc, math.atan2(u[1], u[0]) if j == 0 else 0.0, C)
        # capital socket at the shaft top, +Y outward (face normal); astragal bead just below it
        SOCK.add("capital_rotunda", (ax[0], ax[1], P.COL_SHAFT_Z1), n, P.COL_D_TOP)
        astragal(f"ARCH_rotunda_astragal_{i:02d}", ax, P.COL_SHAFT_Z1, r_t, C, M_ROSE)
        # pedestal
        L.box(f"ARCH_rotunda_pedestal_{i:02d}", ax, (P.PEDESTAL_SIZE, P.PEDESTAL_SIZE), P.PODIUM_TOP_Z - SINK,
              P.PEDESTAL_TOP_Z, C, rot_deg=ang_deg(u), mat=M_PODIUM, part_type="pier")
        # pedestal cap moulding
        cap = L.offset_polygon(L.ensure_ccw([add2(ax, rot2(c, ang_deg(u))) for c in
                                             [(-1.7, -1.7), (1.7, -1.7), (1.7, 1.7), (-1.7, 1.7)]]), 0.0)
        L.sweep_closed(f"ARCH_rotunda_pedestal_cap_{i:02d}", cap, [(0.0, 0.0), (0.10, 0.0), (0.10, 0.18), (0.0, 0.24)],
                       C, mat=M_PODIUM, part_type="pier", z0=P.PEDESTAL_TOP_Z - 0.24, origin=(ax[0], ax[1], P.PEDESTAL_TOP_Z))
        # preview capital
        L.placeholder_capital(f"PH_capital_rotunda_{i:02d}", r_t, P.CAPITAL_H, C_PH, mat=M_OCHRE,
                              origin=(ax[0], ax[1], P.COL_SHAFT_Z1))

    # ---- piers: core (triangular, wall to inner ring) + outer wedge (chamfered, behind the columns)
    rin_c = P.INNER_WALL_APOTHEM / COS22
    inner_half = P.INNER_WALL_APOTHEM * TAN22
    for fr in FRAMES:
        jA, jB = fr.wall_pt("A", P.PIER_WALL), fr.wall_pt("B", P.PIER_WALL)
        jA2, jB2 = fr.wall_pt("A", P.PIER_WALL, -P.WALL_THICKNESS), fr.wall_pt("B", P.PIER_WALL, -P.WALL_THICKNESS)
        Vin = mul2(fr.v, rin_c)
        jAi = add2(Vin, mul2(fr.uA, inner_half - P.INNER_ARCH_SPAN / 2))
        jBi = add2(Vin, mul2(fr.uB, inner_half - P.INNER_ARCH_SPAN / 2))
        core = [jA, fr.V, jB, jB2, jBi, Vin, jAi, jA2]
        L.prism(f"ARCH_rotunda_pier_core_{fr.k:02d}", core, 0.0, P.ATTIC_Z1, C, mat=M_OCHRE, part_type="pier")
        # pier wedge: the narrow chamfered block BETWEEN the two columns of the pair (the columns stand free in front
        # of the wall faces; chamfer face ~1.9 m wide at circumradius 25.0, flush with the column fronts)
        wedge = fr.bump(P.WEDGE_ALONG, P.CHAMFER_CIRCUMRADIUS, inset=0.05)
        L.prism(f"ARCH_rotunda_pier_wedge_{fr.k:02d}", wedge, 0.0, P.ENTABLATURE_Z0 + SINK, C, mat=M_OCHRE, part_type="pier")
        # pilaster strip on the chamfer face, from the pedestal level to the entablature
        wA, cA, cB, wB = wedge
        mid = mul2(add2(cA, cB), 0.5)
        L.box(f"ARCH_rotunda_pier_pilaster_{fr.k:02d}", add2(mid, mul2(fr.v, 0.05)), (1.2, 0.12 + 0.1),
              P.PEDESTAL_TOP_Z, P.ENTABLATURE_Z0 - 0.02, C, rot_deg=ang_deg(fr.v) + 90.0, mat=M_OCHRE, part_type="pier")
        # attic corner block (full ressaut width) with the figure niche and pilaster strips
        cb = fr.bump(P.RESSAUT_ALONG, P.CHAMFER_CIRCUMRADIUS, inset=0.05)
        cA, cB = cb[1], cb[2]
        mid = mul2(add2(cA, cB), 0.5)
        # solid ressaut core (fills the entablature tube over the column pair: soffit seen from below) and the
        # corner block cap (the attic roof slab stops at the octagon)
        core_poly = L.offset_polygon(L.ensure_ccw(cb), -0.04)
        L.prism(f"ARCH_rotunda_ressaut_core_{fr.k:02d}", core_poly, P.ENTABLATURE_Z0, P.ENTABLATURE_Z1 - 0.05, C, mat=M_OCHRE,
                part_type="entablature", bevel=False)
        L.prism(f"ARCH_rotunda_attic_corner_cap_{fr.k:02d}", core_poly, P.ATTIC_Z1 - 0.35, P.ATTIC_Z1 - 0.02, C, mat=M_OCHRE,
                part_type="attic", bevel=False)
        L.prism(f"ARCH_rotunda_attic_corner_{fr.k:02d}", cb, P.ATTIC_Z0 + SINK, P.ATTIC_Z1 - P.ATTIC_TOP_CORNICE_H + SINK, C,
                mat=M_OCHRE, part_type="attic")
        # niche: recessed panel = plate with a hole in front of the block face (block face is at chamfer radius)
        w = math.dist(cA, cB)
        z0n, z1n = P.ATTIC_Z0 + P.ATTIC_BASE_MOULDING_H, P.ATTIC_Z1 - P.ATTIC_TOP_CORNICE_H
        tang = norm2(sub2(cA, cB))
        origin = (mid[0] + fr.v[0] * 0.30, mid[1] + fr.v[1] * 0.30, 0.0)
        outline = [(-w / 2, z0n), (w / 2, z0n), (w / 2, z1n), (-w / 2, z1n)]
        hole = L.rect(0.0, (z0n + z1n) / 2, 2.6, z1n - z0n - 0.0)   # full-height niche (figure 6.7 m stands on the ressaut)
        hole = [(x, min(max(y, z0n + 0.01), z1n - 0.3)) for x, y in hole]
        L.plate(f"ARCH_rotunda_attic_niche_{fr.k:02d}", outline, [hole], 0.30, origin, (tang[0], tang[1], 0.0), (0, 0, 1), C,
                mat=M_OCHRE, part_type="attic")
        for sgn in (-1, 1):
            L.box(f"ARCH_rotunda_attic_pilaster_{fr.k:02d}_{'a' if sgn < 0 else 'b'}",
                  add2(add2(mid, mul2(tang, sgn * 1.85)), mul2(fr.v, 0.36)), (0.7, 0.14), z0n, z1n - 0.3, C,
                  rot_deg=ang_deg(tang), mat=M_OCHRE, part_type="attic")
        # sockets on the corner block: figure in the niche, two urns and the volute scroll on top
        SOCK.add("attic_figure", (mid[0] + fr.v[0] * 0.05, mid[1] + fr.v[1] * 0.05, P.ATTIC_Z0 + 0.02), fr.v, 6.7)
        top = P.ATTIC_Z1
        for sgn in (-1, 1):
            p = add2(add2(mid, mul2(tang, sgn * 2.2)), mul2(fr.v, -0.2))
            SOCK.add("urn", (p[0], p[1], top), fr.v, 1.6)
        p = add2(mid, mul2(fr.v, -0.6))
        SOCK.add("finial", (p[0], p[1], top), fr.v, 1.5, extra={"subtype": "volute_scroll", "modelled_by_arch": True})
        build_volutes(f"ARCH_rotunda_attic_volute_{fr.k:02d}", mid, tang, fr.v, top, C, M_OCHRE)
        L.box(f"PH_attic_figure_{fr.k:02d}", add2(mid, mul2(fr.v, -0.25)), (1.4, 0.9), P.ATTIC_Z0, P.ATTIC_Z0 + 6.7, C_PH,
              rot_deg=ang_deg(tang), mat=M_OCHRE, part_type="attic")
        for sgn in (-1, 1):
            p = add2(add2(mid, mul2(tang, sgn * 2.2)), mul2(fr.v, -0.2))
            L.lathe(f"PH_attic_urn_{fr.k:02d}_{'a' if sgn < 0 else 'b'}",
                    [(0, top), (0.45, top), (0.45, top + 0.15), (0.25, top + 0.3), (0.5, top + 0.8), (0.42, top + 1.3),
                     (0.2, top + 1.45), (0.1, top + 1.6), (0, top + 1.6)], C_PH, segments=16, mat=M_OCHRE,
                    part_type="attic", center=p, origin=(p[0], p[1], top), bevel=False)
        # frieze sockets on the three ressaut faces
        for (a, b) in ((cb[0], cb[1]), (cb[1], cb[2]), (cb[2], cb[3])):
            d = norm2(sub2(b, a))
            out = (d[1], -d[0])
            if dot2(out, fr.v) < 0:
                out = (-out[0], -out[1])
            m = mul2(add2(a, b), 0.5)
            fd = CORNICE["frieze_d"]   # the socket plane IS the frieze face: it moved with the round-4 profile
            SOCK.add("frieze_run", (a[0] + out[0] * fd, a[1] + out[1] * fd, P.ENTABLATURE_Z0 + P.ARCHITRAVE_H), out,
                     math.dist(a, b), extra={"run_length": math.dist(a, b), "run_dir": (d[0], d[1], 0.0)}, size=0.4)

    # ---- faces: spandrel + attic plate with the arch notch and the sunk relief panel; vault; inner spandrel
    n_arc = 28
    half = P.ARCH_SPAN / 2
    panel_w = P.FACE_LENGTH - 2 * P.RESSAUT_ALONG - 2 * P.ATTIC_PANEL_FRAME
    panel_z0 = P.ATTIC_Z0 + P.ATTIC_BASE_MOULDING_H + P.ATTIC_PANEL_FRAME
    panel_z1 = P.ATTIC_Z1 - P.ATTIC_TOP_CORNICE_H - P.ATTIC_PANEL_FRAME
    designs = "ABCABCAB"
    for k in range(8):
        n = face_dir(k)
        u = FRAMES[k].uA
        Cw = mul2(n, P.WALL_APOTHEM)
        X = Vector((u[0], u[1], 0.0))
        if X.cross(Vector((0, 0, 1))).dot(Vector((n[0], n[1], 0))) < 0:
            X = -X
        outline = [(half, P.ARCH_SPRING_Z), (half, P.ATTIC_Z1), (-half, P.ATTIC_Z1), (-half, P.ARCH_SPRING_Z)]
        for i in range(1, n_arc):
            a = math.pi - math.pi * i / n_arc
            outline.append((half * math.cos(a), P.ARCH_SPRING_Z + half * math.sin(a)))
        hole = L.rect(0.0, (panel_z0 + panel_z1) / 2, panel_w, panel_z1 - panel_z0)
        L.plate(f"ARCH_rotunda_wall_{k:02d}", outline, [hole], P.WALL_THICKNESS, (Cw[0], Cw[1], 0.0), tuple(X), (0, 0, 1), C,
                mat=M_OCHRE, part_type="wall")
        # sunk relief field 0.25 behind the wall plane
        field = L.rect(0.0, (panel_z0 + panel_z1) / 2, panel_w + 0.2, panel_z1 - panel_z0 + 0.2)
        L.plate(f"ARCH_rotunda_attic_panel_{k:02d}", field, [], 0.6,
                (Cw[0] - n[0] * P.ATTIC_PANEL_DEPTH, Cw[1] - n[1] * P.ATTIC_PANEL_DEPTH, 0.0), tuple(X), (0, 0, 1), C,
                mat=M_OCHRE, part_type="attic", bevel=False)
        SOCK.add("attic_panel", (Cw[0] - n[0] * P.ATTIC_PANEL_DEPTH, Cw[1] - n[1] * P.ATTIC_PANEL_DEPTH, panel_z0), n, panel_w,
                 extra={"panel_height": panel_z1 - panel_z0, "design": designs[k]})
        panel_frame(f"ARCH_rotunda_attic_frame_{k:02d}", (Cw[0], Cw[1], 0.0), tuple(X), panel_w, panel_z1 - panel_z0,
                    (panel_z0 + panel_z1) / 2, P.ATTIC_PANEL_FRAME, C, M_OCHRE)
        # archivolt around the outer arch (leaf-and-dart + bead-and-reel band, 0.8 wide)
        path, nrm, bnr = [], [], []
        for i in range(n_arc + 1):
            a = math.pi - math.pi * i / n_arc
            rad = Vector((X.x * math.cos(a), X.y * math.sin(a) if False else X.y * math.cos(a), math.sin(a)))
            rad = Vector((X.x * math.cos(a), X.y * math.cos(a), math.sin(a)))
            path.append((Cw[0] + X.x * half * math.cos(a), Cw[1] + X.y * half * math.cos(a), P.ARCH_SPRING_Z + half * math.sin(a)))
            nrm.append(tuple(rad.normalized()))
            bnr.append((n[0], n[1], 0.0))
        L.sweep_open(f"ARCH_rotunda_archivolt_{k:02d}", path, nrm, bnr, archivolt_profile(), C, mat=M_OCHRE, part_type="wall",
                     origin=(Cw[0], Cw[1], P.ARCH_SPRING_Z), bevel=False)
        # keystone at the extrados crown + two impost masks at the springing
        SOCK.add("keystone", (Cw[0] + n[0] * 0.30, Cw[1] + n[1] * 0.30, P.ARCH_CROWN_Z + 0.55), n, 0.8)
        for sgn in (-1, 1):
            SOCK.add("keystone", (Cw[0] + X.x * sgn * (half + 0.55) + n[0] * 0.30, Cw[1] + X.y * sgn * (half + 0.55) + n[1] * 0.30,
                                  P.ARCH_SPRING_Z - 0.25), n, 0.5, extra={"subtype": "impost_mask"}, size=0.4)
        L.box(f"PH_keystone_{k:02d}", (Cw[0] + n[0] * 0.30, Cw[1] + n[1] * 0.30), (0.8, 0.5), P.ARCH_CROWN_Z + 0.55,
              P.ARCH_CROWN_Z + 1.35, C_PH, rot_deg=ang_deg(u), mat=M_OCHRE, part_type="wall", bevel=False)
        # vault soffit: tapering barrel from the wall's inner face to the inner ring's outer face
        rings = []
        r0, r1 = half, P.INNER_ARCH_SPAN / 2
        ap0, ap1 = P.INNER_APOTHEM, P.INNER_WALL_APOTHEM
        for j in range(5):
            t = j / 4
            r = r0 + (r1 - r0) * t
            ap = ap0 + (ap1 - ap0) * t
            cz = P.ARCH_SPRING_Z
            ring = []
            for i in range(n_arc + 1):
                a = math.pi - math.pi * i / n_arc
                ring.append((n[0] * ap + X.x * r * math.cos(a), n[1] * ap + X.y * r * math.cos(a), cz + r * math.sin(a)))
            rings.append(ring)
        nrm0 = face_normal(Vector(rings[0][0]), Vector(rings[0][1]), Vector(rings[1][1]))
        L.loft(f"ARCH_rotunda_vault_{k:02d}", rings, C, mat=M_INNER, part_type="wall", flip=(nrm0.z > 0),
               origin=(Cw[0], Cw[1], P.ARCH_SPRING_Z))
        # No LOD suffix: these were built as `_LOD0` only, so common.set_lod(render=1) -- what every QA pass and
        # every preview uses -- HID them and the barrel soffits rendered bare. That is why QA-03-8 saw no coffer
        # shadow on the vaults. 2,036 tris x 8 bays, cheap enough to carry at every LOD like the ceiling ribs.
        build_vault_coffers(f"ARCH_rotunda_vault_coffers_{k:02d}", k, X, n, C)
        # inner ring spandrel plate (outer face at INNER_WALL_APOTHEM, 1.2 thick, arch notch of the inner arch)
        hi = P.INNER_ARCH_SPAN / 2
        Ci = mul2(n, P.INNER_WALL_APOTHEM)
        outline = [(hi, P.INNER_ARCH_SPRING_Z), (hi, P.INNER_WALL_Z1), (-hi, P.INNER_WALL_Z1), (-hi, P.INNER_ARCH_SPRING_Z)]
        for i in range(1, n_arc):
            a = math.pi - math.pi * i / n_arc
            outline.append((hi * math.cos(a), P.INNER_ARCH_SPRING_Z + hi * math.sin(a)))
        L.plate(f"ARCH_rotunda_inner_wall_{k:02d}", outline, [], P.INNER_WALL_THICKNESS, (Ci[0], Ci[1], 0.0), tuple(X), (0, 0, 1),
                C, mat=M_INNER, part_type="wall")
        # inner archivolt on the rotunda side (plain 0.4 band)
        Cb = mul2(n, P.INNER_WALL_APOTHEM - P.INNER_WALL_THICKNESS)
        path, nrm, bnr = [], [], []
        for i in range(n_arc + 1):
            a = math.pi - math.pi * i / n_arc
            path.append((Cb[0] + X.x * hi * math.cos(a), Cb[1] + X.y * hi * math.cos(a), P.INNER_ARCH_SPRING_Z + hi * math.sin(a)))
            nrm.append(tuple(Vector((X.x * math.cos(a), X.y * math.cos(a), math.sin(a))).normalized()))
            bnr.append((-n[0], -n[1], 0.0))
        L.sweep_open(f"ARCH_rotunda_inner_archivolt_{k:02d}", path, nrm, bnr,
                     [(0.0, 0.0), (0.0, 0.12), (0.12, 0.16), (0.28, 0.16), (0.40, 0.10), (0.40, 0.0)], C, mat=M_INNER,
                     part_type="wall", origin=(Cb[0], Cb[1], P.INNER_ARCH_SPRING_Z), bevel=False)

    # ---- entablature (with ressauts), attic base moulding, attic top cornice: mitred sweeps along the bumped octagon
    plan = entablature_plan()
    L.sweep_closed("ARCH_rotunda_entablature", plan, rotunda_entablature_profile(), C, mat=M_OCHRE, part_type="entablature",
                   z0=P.ENTABLATURE_Z0, origin=(0, 0, P.ENTABLATURE_Z0))
    L.sweep_closed("ARCH_rotunda_attic_base", plan, attic_base_profile(), C, mat=M_OCHRE, part_type="attic",
                   z0=P.ATTIC_Z0, origin=(0, 0, P.ATTIC_Z0))
    L.sweep_closed("ARCH_rotunda_attic_cornice", plan, attic_top_profile(), C, mat=M_OCHRE, part_type="attic",
                   z0=P.ATTIC_Z1 - P.ATTIC_TOP_CORNICE_H, origin=(0, 0, P.ATTIC_Z1))
    # Dentils and modillions along the cornice beds. QA-05-6: these blocks are what makes the band read, so they are
    # in BOTH LODs (one mesh, two objects) -- only the egg-and-dart stays LOD0. Their depth is set so each block's
    # lateral shadow (0.74 m per metre of depth at this sun) covers the gap to the next: dentils 0.30 deep vs a
    # 0.16 gap, modillions 0.58 deep vs a 0.64 gap, and the modillion bed is in any case hidden behind the corona.
    c = CORNICE
    for base, kw in (("dentils", dict(z=c["dentil_z"], h=c["dentil_h"], bed=c["dentil_bed"], size=c["dentil_size"],
                                      pitch=c["dentil_pitch"], depth=c["dentil_d"])),
                     ("modillions", dict(z=c["modillion_z"], h=c["modillion_h"], bed=c["modillion_bed"],
                                         size=c["modillion_w"], pitch=c["modillion_pitch"], depth=c["modillion_d"]))):
        ob = build_dentils(f"ARCH_rotunda_{base}_LOD0", plan, P.ENTABLATURE_Z0 + kw["z"], kw["h"], kw["bed"],
                           kw["size"], C, pitch=kw["pitch"], depth=kw["depth"])
        lod1 = bpy.data.objects.new(f"ARCH_rotunda_{base}_LOD1", ob.data)
        lod1.location = ob.location
        lod1["part_type"] = "entablature"
        lod1["instance_seed"] = ob["instance_seed"]
        C.objects.link(lod1)
    build_eggs("ARCH_rotunda_eggs_LOD0", plan, P.ENTABLATURE_Z0 + c["egg_z"] + c["egg_h"] / 2, c["egg_bed"] + 0.02, C,
               size=(0.17, 0.13, 0.13), pitch=c["egg_pitch"])
    # impost mouldings at the arch springing (both jambs of every face) and astragals at the shaft tops
    build_imposts(C)
    # attic roof slab (octagon minus the drum) seen from above
    oct_out = L.octagon_world(P.WALL_APOTHEM + 0.2)
    L.plate("ARCH_rotunda_attic_roof", oct_out, [L.regular_polygon(P.DRUM_BAND_R - 0.3, 64)], 0.4,
            (0, 0, P.ATTIC_Z1 - 0.01), (1, 0, 0), (0, 1, 0), C, mat=M_OCHRE, part_type="attic", bevel=False)

    # ---- drum (plain band, guilloche cushion, cornice ring) and dome
    z0 = P.DRUM_Z0 - 0.4
    zp = P.DRUM_Z0 + P.DRUM_PLAIN_H
    L.lathe("ARCH_rotunda_drum", [(P.DRUM_BAND_R - 0.5, z0), (P.DRUM_BAND_R, z0), (P.DRUM_BAND_R, zp - 0.5),
                                  (P.DRUM_BAND_R + 0.12, zp - 0.4), (P.DRUM_BAND_R + 0.12, zp), (P.DRUM_BAND_R - 0.5, zp)], C,
            segments=128, mat=M_OCHRE, part_type="drum", origin=(0, 0, P.DRUM_Z0), close_top=True, close_bottom=True, bevel=False)
    zb = zp - SINK
    cushion = [(P.DRUM_BAND_R - 0.3, zb), (P.DRUM_BAND_R, zb)]
    for i in range(1, 8):
        a = -math.pi / 2 + math.pi * i / 8
        cushion.append((P.DRUM_BAND_R + 0.55 * math.cos(a) + 0.0, zb + P.DRUM_BAND_H / 2 + (P.DRUM_BAND_H / 2) * math.sin(a)))
    cushion += [(P.DRUM_BAND_R, zb + P.DRUM_BAND_H), (P.DRUM_BAND_R - 0.3, zb + P.DRUM_BAND_H)]
    L.lathe("ARCH_rotunda_drum_band", cushion, C, segments=128, mat=M_BAND, part_type="drum", origin=(0, 0, zb),
            close_top=True, close_bottom=True, bevel=False)
    SOCK.add("drum_band", (P.DRUM_BAND_R + 0.55, 0.0, zb), (1.0, 0.0), P.DRUM_BAND_H,
             extra={"run_length": 2 * math.pi * (P.DRUM_BAND_R + 0.55), "radius": P.DRUM_BAND_R + 0.55}, size=1.0)
    zc = zb + P.DRUM_BAND_H - SINK
    cornice = [(P.DRUM_BAND_R - 0.3, zc), (P.DRUM_BAND_R + 0.2, zc), (P.DRUM_BAND_R + 0.6, zc + 0.2), (P.DRUM_CORNICE_R, zc + 0.45),
               (P.DRUM_CORNICE_R, P.DRUM_Z1 - 0.15), (P.DRUM_CORNICE_R - 0.25, P.DRUM_Z1), (P.DOME_BASE_R + 0.25, P.DRUM_Z1),
               (P.DOME_BASE_R + 0.25, P.DRUM_Z1 + 0.12), (P.DOME_BASE_R - 0.3, P.DRUM_Z1 + 0.12)]
    L.lathe("ARCH_rotunda_drum_cornice", cornice, C, segments=128, mat=M_OCHRE, part_type="drum", origin=(0, 0, zc),
            close_top=True, close_bottom=True, bevel=False)
    dome = []
    th0 = math.asin(P.DOME_BASE_R / P.DOME_SPHERE_R)
    nd = 40
    for i in range(nd + 1):
        th = th0 * (1 - i / nd)
        dome.append((P.DOME_SPHERE_R * math.sin(th), P.DOME_SPHERE_CZ + P.DOME_SPHERE_R * math.cos(th)))
    dome[0] = (P.DOME_BASE_R, P.DRUM_Z1 + 0.05)
    L.lathe("ARCH_rotunda_dome", dome, C, segments=128, mat=M_DOME, part_type="dome", origin=(0, 0, P.DRUM_Z1), bevel=False)
    SOCK.add("finial", (0.0, 0.0, P.DOME_APEX_Z), (0.0, 1.0), 0.6, extra={"subtype": "dome_apex"})
    za = P.DOME_APEX_Z - 0.05
    L.lathe("ARCH_rotunda_dome_apex_cap", [(0.0, za), (0.55, za), (0.55, za + 0.12), (0.35, za + 0.2), (0.3, za + 0.45),
                                           (0.18, za + 0.55), (0.0, za + 0.6)], C, segments=32, mat=M_DOME, part_type="dome",
            origin=(0, 0, za), bevel=False)

    # ---- inner order: 8 tan columns, bases, blocks, capital sockets, winged-figure sockets
    ri = P.INNER_COL_D / 2
    srcs = {}
    for k, fr in enumerate(FRAMES):
        ax = mul2(fr.v, P.INNER_COL_R)
        rz = math.atan2(fr.v[1], fr.v[0])
        for lod in (0, 1, 2):
            name = f"ARCH_rotunda_inner_column_{k:02d}_LOD{lod}"
            loc = (ax[0], ax[1], P.INNER_COL_BASE_H)
            if lod not in srcs:
                srcs[lod] = L.column_shaft(name, ri, ri * 0.86, P.INNER_COL_SHAFT_Z1 - P.INNER_COL_BASE_H, C, lod=lod, mat=M_TAN,
                                           part_type="column", origin=loc)
                srcs[lod].rotation_euler = (0, 0, rz)
            else:
                L.instance(name, srcs[lod], loc, rz, C)
        if "base" not in srcs:
            srcs["base"] = L.column_base(f"ARCH_rotunda_inner_colbase_{k:02d}", ri, C, height=P.INNER_COL_BASE_H + SINK,
                                         plinth=1.15 * P.INNER_COL_D, mat=M_TAN, origin=(ax[0], ax[1], -SINK))
            srcs["base"][0].rotation_euler = (0, 0, rz)
        else:
            for j, so in enumerate(srcs["base"]):
                L.instance(f"ARCH_rotunda_inner_colbase_{k:02d}_{j}", so, (ax[0], ax[1], -SINK), rz if j == 0 else 0.0, C)
        SOCK.add("capital_inner", (ax[0], ax[1], P.INNER_COL_SHAFT_Z1), fr.v, ri * 2 * 0.86)
        astragal(f"ARCH_rotunda_inner_astragal_{k:02d}", ax, P.INNER_COL_SHAFT_Z1, ri * 0.86, C, M_TAN)
        L.placeholder_capital(f"PH_capital_inner_{k:02d}", ri * 0.86, P.INNER_CAPITAL_H, C_PH, mat=M_TAN,
                              origin=(ax[0], ax[1], P.INNER_COL_SHAFT_Z1))
        bz0 = P.INNER_BLOCK_Z0
        L.box(f"ARCH_rotunda_inner_block_{k:02d}", ax, (P.INNER_BLOCK_SIZE, P.INNER_BLOCK_SIZE), bz0 - SINK, bz0 + P.INNER_BLOCK_H - 0.35,
              C, rot_deg=math.degrees(rz), mat=M_TAN, part_type="entablature")
        L.box(f"ARCH_rotunda_inner_block_cap_{k:02d}", ax, (P.INNER_BLOCK_SIZE + 0.5, P.INNER_BLOCK_SIZE + 0.5),
              bz0 + P.INNER_BLOCK_H - 0.35 - SINK, bz0 + P.INNER_BLOCK_H, C, rot_deg=math.degrees(rz), mat=M_TAN, part_type="entablature")
        toward_c = (-fr.v[0], -fr.v[1])
        fp = add2(ax, mul2(toward_c, 0.35))
        SOCK.add("inner_figure", (fp[0], fp[1], bz0 + P.INNER_BLOCK_H), toward_c, 4.6, extra={"note": "+Y = direction the figure faces (toward the rotunda centre)"})
        L.box(f"PH_inner_figure_{k:02d}", fp, (1.2, 0.8), bz0 + P.INNER_BLOCK_H, bz0 + P.INNER_BLOCK_H + 4.6, C_PH,
              rot_deg=math.degrees(rz), mat=M_TAN, part_type="entablature", bevel=False)

    build_ceiling(C)


def _path_segments(plan, closed=True):
    n = len(plan)
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        a, b = plan[i], plan[(i + 1) % n]
        d = norm2(sub2(b, a))
        yield a, b, d, (d[1], -d[0]), math.dist(a, b)


def build_dentils(name, plan, z, h, bed, size, coll, pitch=None, depth=None, closed=True, mat=None, outward_sign=1.0,
                  part_type="entablature"):
    """Blocks (dentils / modillions / mutules) along a plan path at offset `bed` from the path line (outward = right of
    travel for a CCW path), `size` wide, `depth` deep (default = size), `h` tall, every `pitch`."""
    pitch = pitch or size * 2
    depth = depth or size
    bm = bmesh.new()
    for a, b, d, out, length in _path_segments(plan, closed):
        out = mul2(out, outward_sign)
        cnt = int(length // pitch)
        if cnt < 1:
            continue
        start = (length - (cnt - 1) * pitch) / 2
        for j in range(cnt):
            s = start + j * pitch
            c = add2(add2(a, mul2(d, s)), mul2(out, bed))
            corners = [add2(c, mul2(d, -size / 2)), add2(c, mul2(d, size / 2)),
                       add2(add2(c, mul2(d, size / 2)), mul2(out, depth)), add2(add2(c, mul2(d, -size / 2)), mul2(out, depth))]
            vb = [bm.verts.new((x, y, z)) for x, y in corners]
            vt = [bm.verts.new((x, y, z + h)) for x, y in corners]
            for q in range(4):
                bm.faces.new((vb[q], vb[(q + 1) % 4], vt[(q + 1) % 4], vt[q]))
            bm.faces.new(vt)
            bm.faces.new(list(reversed(vb)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return L._finish(name, bm, coll, mat or M_OCHRE, part_type, origin=(0, 0, z), smooth=False, bevel=False)


def build_eggs(name, plan, z, bed, coll, size=(0.11, 0.09, 0.09), pitch=0.30, closed=True, mat=None, outward_sign=1.0):
    """Egg-and-dart 'eggs': half-embedded ellipsoids along a plan path (LOD0 ornament as geometry)."""
    egg = bmesh.new()
    bmesh.ops.create_uvsphere(egg, u_segments=8, v_segments=6, radius=1.0)
    egg_me = bpy.data.meshes.new("_egg_tmp")
    egg.to_mesh(egg_me)
    egg.free()
    bm = bmesh.new()
    from mathutils import Matrix
    for a, b, d, out, length in _path_segments(plan, closed):
        out = mul2(out, outward_sign)
        cnt = int(length // pitch)
        if cnt < 1:
            continue
        start = (length - (cnt - 1) * pitch) / 2
        for j in range(cnt):
            s = start + j * pitch
            c = add2(add2(a, mul2(d, s)), mul2(out, bed))
            n0 = len(bm.verts)
            bm.from_mesh(egg_me)
            bm.verts.ensure_lookup_table()
            new = bm.verts[n0:]
            M = Matrix(((d[0] * size[0], out[0] * size[1], 0.0, c[0]),
                        (d[1] * size[0], out[1] * size[1], 0.0, c[1]),
                        (0.0, 0.0, size[2], z),
                        (0.0, 0.0, 0.0, 1.0)))
            bmesh.ops.transform(bm, matrix=M, verts=new)
    bpy.data.meshes.remove(egg_me)
    for f in bm.faces:
        f.smooth = True
    return L._finish(name, bm, coll, mat or M_OCHRE, "entablature", origin=(0, 0, z), smooth=False, bevel=False)


def build_imposts(C):
    """Impost moulding (short horizontal cornice) on each arch jamb at the springing, and astragal rings at the shaft tops."""
    prof = [(0.0, -0.30), (0.10, -0.30), (0.10, -0.12), (0.22, -0.06), (0.30, 0.0), (0.30, 0.08), (0.0, 0.08)]
    half = P.ARCH_SPAN / 2
    for k in range(8):
        n = face_dir(k)
        u = FRAMES[k].uA
        Cw = mul2(n, P.WALL_APOTHEM)
        for sgn in (-1, 1):
            a = add2(Cw, mul2(u, sgn * (half + 0.82)))
            b = add2(Cw, mul2(u, sgn * (half + 2.10)))
            p3, nrm, bnr = L.plan_path_to_3d([a, b], P.ARCH_SPRING_Z)
            if dot2((nrm[0][0], nrm[0][1]), n) < 0:
                nrm = [(-x, -y, zz) for x, y, zz in nrm]
            L.sweep_open(f"ARCH_rotunda_impost_{k:02d}_{'a' if sgn < 0 else 'b'}", p3, nrm, bnr, prof, C, mat=M_OCHRE,
                         part_type="wall", origin=(a[0], a[1], P.ARCH_SPRING_Z), bevel=False)


_ASTRAGALS = {}


def astragal(name, xy, z, r, coll, mat):
    """Bead ring at the top of a shaft (r = shaft top radius); one mesh per radius, instanced."""
    key = (round(r, 3), mat)
    if key in _ASTRAGALS:
        return L.instance(name, _ASTRAGALS[key], (xy[0], xy[1], z), 0.0, coll)
    prof = [(r * 0.96, z - 0.16), (r * 1.0, z - 0.15), (r * 1.06, z - 0.11), (r * 1.08, z - 0.07), (r * 1.06, z - 0.03),
            (r * 1.0, z + 0.0), (r * 0.96, z + 0.01)]
    o = L.lathe(name, prof, coll, segments=48, mat=mat, part_type="column", origin=(xy[0], xy[1], z), center=xy, bevel=False)
    _ASTRAGALS[key] = o
    return o


def panel_frame(name, origin3d, X, w, h, cy, band, coll, mat, proud=0.035):
    """Raised Greek-key frame band around a sunk panel: a thin plate ring `band` wide standing `proud` of the wall."""
    outer = L.rect(0.0, cy, w + 2 * band, h + 2 * band)
    inner = L.rect(0.0, cy, w, h)
    N = Vector(X).cross(Vector((0, 0, 1))).normalized()
    o = (origin3d[0] + N.x * proud, origin3d[1] + N.y * proud, origin3d[2])
    return L.plate(name, outer, [inner], proud + 0.02, o, X, (0, 0, 1), coll, mat=mat, part_type="attic", bevel=False)


def build_vault_coffers(name, k, X, n, coll):
    """Rib network (frames) on the tapering barrel soffit of bay k: 3 rows x 9 coffers, mapped from a flat plate."""
    half = P.ARCH_SPAN / 2
    r0, r1 = half, P.INNER_ARCH_SPAN / 2
    ap0, ap1 = P.INNER_APOTHEM, P.INNER_WALL_APOTHEM
    depth = ap0 - ap1
    r_mean = (r0 + r1) / 2
    arc = math.pi * r_mean
    # ref 062: two rows of large octagonal coffers with small square (diamond) coffers between them
    rows, cols = 2, 7
    pitch_s = (arc - 0.8) / cols
    row_t = [depth * 0.27, depth * 0.73]
    oct_r = min(0.95, pitch_s * 0.42, (row_t[1] - row_t[0]) * 0.45)
    holes = []
    for j, ty in enumerate(row_t):
        for i in range(cols):
            cx = 0.4 + pitch_s * (i + 0.5)
            holes.append([add2((cx, ty), p) for p in L.regular_polygon(oct_r, 8, 22.5)])
            if i < cols - 1:
                # Review item 1: at factor 0.8 the in-row diamond left only 75 mm of rib to its octagons, so the
                # 70 mm reveal splay overlapped them. 0.55 opens that to 180 mm, which carries the full register.
                dx = cx + pitch_s / 2
                dr = min(0.33, (pitch_s / 2 - oct_r * 0.924) * 0.55)
                holes.append([(dx + dr * 1.02, ty), (dx, ty + dr), (dx - dr * 1.02, ty), (dx, ty - dr)])
    tm = (row_t[0] + row_t[1]) / 2
    for i in range(cols):
        cx = 0.4 + pitch_s * (i + 0.5)
        dr = min(0.33, ((row_t[1] - row_t[0]) / 2 - oct_r * 0.924) * 0.8)
        # ... and the mid-row diamond came out 0.26 m across with only 29 mm of rib above and below the octagons,
        # i.e. a hole too small to read at cam04 and far too tight for a reveal. Gated off below 0.2 m.
        if dr > 0.2:
            holes.append([(cx + dr, tm), (cx, tm + dr * 1.02), (cx - dr, tm), (cx, tm - dr * 1.02)])
    outline = [(0.0, 0.0), (arc, 0.0), (arc, depth), (0.0, depth)]
    # QA-02-9 / QA-01-15 / QA-03-8: the rib plate stands proud of the soffit, so its thickness IS the coffer depth.
    # 0.12 -> 0.20 (round 1) -> 0.38 now, which is 0.20 x the 1.9 m octagon width, the depth-to-width ratio measured
    # off ref 083 (see arch_params). The room face carries VAULT_COFFER_REGISTERS so each coffer
    # has an outer register: at cam04 the vaults are seen near edge-on and a single straight reveal showed nothing.
    obj = L.plate(name, outline, holes, P.VAULT_COFFER_DEPTH, (0, 0, 0), (1, 0, 0), (0, 1, 0), coll, mat=M_PLASTER_RIB,
                  part_type="wall", bevel=False, smooth=False, registers=P.VAULT_COFFER_REGISTERS)
    obj["surface"] = "coffer_rib"      # QA-04-7: rib network only; the panel behind is ARCH_rotunda_vault_NN
    me = obj.data
    for v in me.vertices:
        s = v.co.x / r_mean            # angle 0..pi
        t = v.co.y / depth             # 0 at the outer wall face
        delta = -v.co.z                # 0 front (on the soffit), VAULT_COFFER_DEPTH back (proud of it)
        r = r0 + (r1 - r0) * t - delta
        ap = ap0 + (ap1 - ap0) * t
        a = math.pi - s
        v.co = (n[0] * ap + X.x * r * math.cos(a), n[1] * ap + X.y * r * math.cos(a), P.ARCH_SPRING_Z + r * math.sin(a))
    me.update()
    obj.location = (0, 0, 0)
    L.cube_project_uv(obj)
    return obj


def _lbox(bm, a, d, out, zb, x0, x1, y0, y1, z0, z1):
    """Axis box in a segment-local frame: x along d, y along out (proud of the face), z up; zb = base height."""
    pts = []
    for (x, y) in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        pts.append((a[0] + d[0] * x + out[0] * y, a[1] + d[1] * x + out[1] * y))
    vb = [bm.verts.new((px, py, zb + z0)) for px, py in pts]
    vt = [bm.verts.new((px, py, zb + z1)) for px, py in pts]
    for q in range(4):
        bm.faces.new((vb[q], vb[(q + 1) % 4], vt[(q + 1) % 4], vt[q]))
    bm.faces.new(vt)
    bm.faces.new(list(reversed(vb)))


def _ldisc(bm, a, d, out, zb, cx, cz, r, y0, y1, n=12):
    """Disc (n-gon prism) in the local x-z plane, extruded from y0 to y1 along out."""
    ring0, ring1 = [], []
    for i in range(n):
        ang = 2 * math.pi * i / n
        x, z = cx + r * math.cos(ang), cz + r * math.sin(ang)
        ring0.append(bm.verts.new((a[0] + d[0] * x + out[0] * y0, a[1] + d[1] * x + out[1] * y0, zb + z)))
        ring1.append(bm.verts.new((a[0] + d[0] * x + out[0] * y1, a[1] + d[1] * x + out[1] * y1, zb + z)))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((ring0[i], ring0[j], ring1[j], ring1[i]))
    bm.faces.new(ring1)
    bm.faces.new(list(reversed(ring0)))


def build_meander_band(name, poly, zb, h, coll, mat, closed=True, proud=P.BAND_PROUD, unit=P.BAND_UNIT, part_type="rostra"):
    """Greek-key meander units alternating with square rosette bosses along a plan path (the recessed band face is the
    path line; the pattern stands `proud` of it, still behind the wall plane). One mesh per path."""
    bm = bmesh.new()
    w = 0.075     # key-line width: reads at 720 px in cam05 (sheet s4 #12)
    m = 0.04
    idx = 0
    for a, b, d, out, length in _path_segments(poly, closed):
        cnt = int(length // unit)
        if cnt < 1:
            continue
        start = (length - cnt * unit) / 2
        for j in range(cnt):
            s = start + j * unit
            c = add2(a, mul2(d, s))
            if idx % 2 == 0:
                # meander hook: top rail, descender, inner return, bottom rail (continuous key line)
                _lbox(bm, c, d, out, zb, 0.08, 0.08 + w, m + 0.10, h - m, 0.0, proud)                 # left riser
                _lbox(bm, c, d, out, zb, 0.08, 0.66, h - m - w, h - m, 0.0, proud)                    # top rail
                _lbox(bm, c, d, out, zb, 0.66 - w, 0.66, m + 0.18, h - m, 0.0, proud)                # right descender
                _lbox(bm, c, d, out, zb, 0.30, 0.66, m + 0.18, m + 0.18 + w, 0.0, proud)             # inner return
                _lbox(bm, c, d, out, zb, 0.30, 0.30 + w, m, m + 0.18 + w, 0.0, proud)                # inner riser
                _lbox(bm, c, d, out, zb, 0.30, 0.92, m, m + w, 0.0, proud)                           # bottom rail
                _lbox(bm, c, d, out, zb, 0.92 - w, 0.92, m, h - m - 0.10, 0.0, proud)                # end riser
            else:
                _lbox(bm, c, d, out, zb, 0.12, 0.88, 0.02, h - 0.02, 0.0, proud * 0.5)                # boss plate
                _ldisc(bm, c, d, out, zb, 0.50, h / 2, (h - 0.05) * 0.5, proud * 0.5 - 0.005, proud, 16)   # rosette disc
                for pk in range(8):                                                                      # petals
                    import math as _m
                    ang = 2 * _m.pi * pk / 8
                    _ldisc(bm, c, d, out, zb, 0.50 + (h - 0.05) * 0.30 * _m.cos(ang),
                           h / 2 + (h - 0.05) * 0.30 * _m.sin(ang), (h - 0.05) * 0.14, proud - 0.004, proud + 0.012, 8)
                _ldisc(bm, c, d, out, zb, 0.50, h / 2, 0.05, proud - 0.005, proud + 0.03, 8)                # centre knob
            idx += 1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return L._finish(name, bm, coll, mat, part_type, origin=(0, 0, zb), smooth=False, bevel=False)


def add_frieze_sockets(poly, zb, h, subtype="greek_key", closed=True, min_len=1.4, extra=None):
    """One `frieze_run` socket per straight run of a band, per the frame convention in docs/sockets.md:
    origin at the RUN START, +Y = the outward face normal, +X along the run. `_path_segments` walks a CCW polygon
    so its `out` is the right-hand (outward) normal and the run therefore starts at the segment's far end `b` and
    runs back along -d (that is the direction that lands on local +X in a right-handed frame with +Y = out)."""
    n = 0
    for a, b, d, out, length in _path_segments(poly, closed):
        if length < min_len:
            continue
        e = dict(run_length=round(length, 3), run_dir=(-d[0], -d[1], 0.0), band_height=round(h, 3), subtype=subtype)
        if extra:
            e.update(extra)
        SOCK.add("frieze_run", (b[0], b[1], zb), out, length, extra=e, size=0.35)
        n += 1
    return n


def build_rustication(name, poly, z0, z1, coll, mat, course=0.6, joint=0.04, recess=0.035, part_type="rostra"):
    """Rusticated podium wall: the core is set back by `recess` and the ashlar courses stand out to the real face,
    leaving a `joint` gap at every course line (sheet s4 #12 / s5: 'plain rusticated courses, joints ~0.6 m').
    Modelled as geometry (no booleans) so the joints throw a real shadow line; the materials agent asked for this."""
    inner = L.offset_polygon(poly, -recess)
    L.prism(name, inner, z0, z1, coll, mat=mat, part_type=part_type, ngon=False)
    n = max(1, int(round((z1 - z0) / course)))
    ch = (z1 - z0) / n
    objs = []
    for i in range(n):
        a = z0 + i * ch
        b = a + ch - joint
        if i == n - 1:
            b = z1                      # top course runs into the band above, no joint at the very top
        objs.append(L.prism(f"{name}_course_{i:02d}", poly, a, b, coll, mat=mat, part_type=part_type, ngon=False,
                            bevel=False))
    return objs


def build_volutes(name, mid, tang, v, z_top, coll, mat):
    """Pair of volute scrolls (Ionic-like, ~1.5 m) side by side on a corner-block cap; spirals in the (tang, z) plane."""
    objs = []
    objs.append(L.box(name + "_plinth", add2(mid, mul2(v, -0.55)), (1.9, 0.6), z_top - SINK, z_top + 0.22, coll, rot_deg=ang_deg(tang),
                      mat=mat, part_type="attic"))
    for sgn, tag in ((-1, "a"), (1, "b")):
        cz = z_top + 0.22 + 0.62
        cxy = add2(add2(mid, mul2(tang, sgn * 0.47)), mul2(v, -0.55))
        path, nrm, bnr = [], [], []
        turns = 2.4
        n = 72
        for i in range(n + 1):
            t = turns * 2 * math.pi * i / n
            r = 0.60 - 0.52 * (i / n)
            ang = math.pi / 2 + sgn * t          # start at the top, spiral inward
            px, pz = r * math.cos(ang), r * math.sin(ang)
            path.append((cxy[0] + tang[0] * px, cxy[1] + tang[1] * px, cz + pz))
            nrm.append((tang[0] * math.cos(ang), tang[1] * math.cos(ang), math.sin(ang)))
            bnr.append((v[0], v[1], 0.0))
        prof = [(-0.09, -0.16), (0.09, -0.16), (0.09, 0.16), (-0.09, 0.16), (-0.09, -0.16)]
        objs.append(L.sweep_open(f"{name}_{tag}", path, nrm, bnr, prof, coll, mat=mat, part_type="attic",
                                 origin=(cxy[0], cxy[1], cz), bevel=False))
    return objs


def build_kerb_wall(coll):
    """Low concrete kerb along the lagoon edge of the rotunda peninsula (OSM lagoon polygon within 52 m of the centre)."""
    site = common.load_site_local()
    poly = site["lagoon0"][0]
    n = len(poly)
    runs, cur = [], []
    for i in range(n + 1):
        p = poly[i % n]
        if math.hypot(p[0], p[1]) < 52.0 and p[1] > -22.0:
            cur.append(p)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    prof = [(-0.3, -0.5), (0.3, -0.5), (0.3, 0.55), (0.25, 0.6), (-0.25, 0.6), (-0.3, 0.55), (-0.3, -0.5)]
    for i, run in enumerate(runs):
        if len(run) < 2:
            continue
        p3, nrm, bnr = L.plan_path_to_3d(run, P.WATER_Z)
        L.sweep_open(f"ARCH_site_lagoon_kerb_{i}", p3, nrm, bnr, prof, coll, mat=M_PODIUM, part_type="rostra",
                     origin=(run[0][0], run[0][1], P.WATER_Z))


def build_ceiling(C):
    """Coffered star ceiling: plain field saucer + rib plate with the coffers as holes, both on the sphere."""
    R, cz = P.CEILING_SPHERE_R, P.CEILING_SPHERE_CZ
    apo = P.INNER_WALL_APOTHEM - P.INNER_WALL_THICKNESS      # inner face of the inner ring (14.18)
    # sphere through the octagon face centres at CEILING_RING_Z with the given rise
    R = (apo ** 2 + P.CEILING_RISE ** 2) / (2 * P.CEILING_RISE)
    cz = P.CEILING_RING_Z + P.CEILING_RISE - R

    def sz(x, y):
        r2 = x * x + y * y
        return cz + math.sqrt(max(R * R - r2, 0.0))

    octo = L.octagon_world(apo)
    per_side = 6
    rim = []
    for i in range(8):
        a, b = octo[i], octo[(i + 1) % 8]
        for j in range(per_side):
            t = j / per_side
            rim.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    rings = []
    for f in [0.06] + [0.12 + 0.88 * i / 10 for i in range(11)]:
        rings.append([(x * f, y * f, sz(x * f, y * f) + P.CEILING_FIELD_LIFT) for x, y in rim])
    nrm0 = face_normal(Vector(rings[0][0]), Vector(rings[0][1]), Vector(rings[1][1]))
    field = L.loft("ARCH_rotunda_ceiling_field", rings, C, mat=M_PLASTER, part_type="ceiling", flip=(nrm0.z > 0), closed=True,
                   origin=(0, 0, P.CEILING_RING_Z))
    # close the centre with an n-gon
    bm = bmesh.new()
    bm.from_mesh(field.data)
    bm.verts.ensure_lookup_table()
    centre = [v for v in bm.verts if (v.co.x ** 2 + v.co.y ** 2) < (0.07 * apo) ** 2]
    if len(centre) >= 3:
        centre.sort(key=lambda v: math.atan2(v.co.y, v.co.x))
        f = bm.faces.new(centre)
        if f.normal.z > 0:
            f.normal_flip()
        bm.to_mesh(field.data)
    bm.free()
    # coffer holes
    holes = [L.regular_polygon(3.0, 32)]
    for k in range(8):
        n = face_dir(k)
        v = vertex_dir(k)
        an = ang_deg(n)
        av = ang_deg(v)
        holes.append([add2(mul2(n, 5.0), p) for p in L.regular_polygon(1.0, 8, an + 22.5)])
        holes.append([add2(mul2(v, 5.2), rot2(p, av)) for p in [(-0.7, -0.7), (0.7, -0.7), (0.7, 0.7), (-0.7, 0.7)]])
        holes.append([add2(mul2(n, 8.6), p) for p in L.regular_polygon(1.8, 8, an + 22.5)])
        holes.append([add2(mul2(v, 9.1), rot2(p, av)) for p in [(-1.9, -0.5), (1.9, -0.5), (1.9, 0.5), (-1.9, 0.5)]])
        trap = [add2(mul2(n, 11.0), rot2((0.0, -1.6), an)), add2(mul2(n, 11.0), rot2((0.0, 1.6), an))]
        for i in range(0, 9):
            a = math.radians(14.0 - 28.0 * i / 8)
            trap.append(rot2((12.9 * math.cos(a), 12.9 * math.sin(a)), an))
        holes.append(trap)
        holes.append([add2(mul2(v, 12.0), (0, 0)), add2(mul2(v, 12.9), rot2((0.0, 0.8), av)), add2(mul2(v, 12.9), rot2((0.0, -0.8), av))])
    # QA-03-8: 0.30 -> 0.55 deep (depth / width 0.20, measured off ref 083) with COFFER_REGISTERS at the room face.
    ribs = L.plate("ARCH_rotunda_ceiling_ribs", octo, holes, P.COFFER_DEPTH, (0, 0, 0), (1, 0, 0), (0, 1, 0), C,
                   mat=M_PLASTER_RIB, part_type="ceiling", bevel=False, registers=P.COFFER_REGISTERS)
    me = ribs.data
    for vtx in me.vertices:
        vtx.co.z += sz(vtx.co.x, vtx.co.y)
    me.update()
    ribs.location = (0, 0, 0)
    ribs["part_type"] = "ceiling"
    ribs["surface"] = "coffer_rib"     # QA-04-7: rib network only; the panel behind is ARCH_rotunda_ceiling_field
    # Rosette sockets (review item 2 -- the plane is now stated per socket instead of keyed off COFFER_DEPTH).
    # Two different kinds share the `rosette_ceiling` type:
    #   * 16 on the rim band (rr 13.73 / 14.85, between the outermost coffers and the octagon edge): that band is
    #     SOLID rib, not a coffer, so these are bosses applied to the rib's room face -- the sheet's "base ring
    #     with rosette band above the inner arches" (083). Their plane is the rib underside, which moved down with
    #     COFFER_DEPTH; that is correct, and P.ROSETTE_RIM_INSET lifts them back into the plaster by 0.02 m.
    #   * 8 inside the ring-1 square coffers (rr 5.2): a rosette inside a box belongs on the box FLOOR, i.e. the
    #     field saucer, which sits P.CEILING_FIELD_LIFT above the sphere -- not on the sphere as before.
    # Two families of rosette, both `rosette_ceiling`. Socket contract: ARCH socket +Y = the way the ornament's
    # FRONT faces (ornament, 2026-09-08: all 24 used to face radially outward, into the masonry).
    #  * 16 BASE-RING BAND rosettes on the VERTICAL inner face of the inner ring wall, the sheet's "base ring with
    #    rosette band above the inner arches" (line 258). Two per octagon face at +-ROSETTE_BAND_HALF_ANGLE from
    #    the face normal, so all 16 stand on a real flat face at the same 22.5 deg spacing the ring had before.
    #    +Y = -face normal (they face the rotunda axis), +Z = world up, i.e. up the face.
    #  * 8 rosettes on the floor of the ring-1 square coffers: they lie on a ceiling, so +Y points straight DOWN
    #    into the room (pitch -90; the horizontal argument then only sets their in-plane roll).
    ca = math.cos(math.radians(P.ROSETTE_BAND_HALF_ANGLE))
    for k in range(8):
        n, v = face_dir(k), vertex_dir(k)
        inward = (-n[0], -n[1])
        for s in (-1, 1):
            d = rot2(n, s * P.ROSETTE_BAND_HALF_ANGLE)      # on the face plane, apo away along the face normal
            q = mul2(d, apo / ca)
            SOCK.add("rosette_ceiling", (q[0], q[1], P.ROSETTE_BAND_Z), inward, 0.7, size=0.3)
        p = mul2(v, 5.2)
        SOCK.add("rosette_ceiling", (p[0], p[1], sz(p[0], p[1]) + P.CEILING_FIELD_LIFT), v, 0.5,
                 size=0.3, pitch_deg=-90.0)


# ============================================================================= site (platform, steps, rostra, planters, stairs)
def lobe_polygon(az_c, side, reach):
    """Podium lobe sector (r 21 -> 27.3, +-14.5 deg) merged with the planter sweep on `side` reaching `reach`."""
    pts = []
    n_in = 10
    for i in range(n_in + 1):
        a = az_c - P.PODIUM_LOBE_HALF_ANGLE + 2 * P.PODIUM_LOBE_HALF_ANGLE * i / n_in
        pts.append(P.az_to_xy(a, P.WALL_APOTHEM - 0.5))
    sweep = []
    if reach and reach > P.PODIUM_LOBE_R + 0.5:
        k = (reach - P.PODIUM_LOBE_R) / (37.0 - P.PODIUM_LOBE_R)
        raw = [(8.3, 27.3), (8.3, 28.6), (7.6, 30.7), (7.6, 32.3), (8.3, 32.9), (1.7, 37.0), (-0.6, 35.2), (-2.0, 33.6),
               (-3.6, 31.3), (-4.1, 29.4), (-4.1, 28.1), (-4.1, 27.3)]
        for (da, r) in raw:
            rr = P.PODIUM_LOBE_R + (r - P.PODIUM_LOBE_R) * k
            sweep.append((az_c + side * da, rr))
        if side < 0:
            sweep = list(sweep)
    outer = []
    if sweep:
        lo, hi = min(s[0] for s in sweep), max(s[0] for s in sweep)
        # outer arc from +half to hi, then sweep (ordered from hi to lo), then arc from lo to -half
        seq = sorted(sweep, key=lambda s: -s[0]) if side > 0 else sorted(sweep, key=lambda s: -s[0])
        seq = sweep if side > 0 else [(a, r) for (a, r) in reversed(sweep)]
        a_start = az_c + P.PODIUM_LOBE_HALF_ANGLE
        first_a = seq[0][0]
        for i in range(6):
            a = a_start + (first_a - a_start) * i / 6
            outer.append(P.az_to_xy(a, P.PODIUM_LOBE_R))
        for (a, r) in seq:
            outer.append(P.az_to_xy(a, r))
        last_a = seq[-1][0]
        a_end = az_c - P.PODIUM_LOBE_HALF_ANGLE
        for i in range(1, 7):
            a = last_a + (a_end - last_a) * i / 6
            outer.append(P.az_to_xy(a, P.PODIUM_LOBE_R))
    else:
        for i in range(n_in + 1):
            a = az_c + P.PODIUM_LOBE_HALF_ANGLE - 2 * P.PODIUM_LOBE_HALF_ANGLE * i / n_in
            outer.append(P.az_to_xy(a, P.PODIUM_LOBE_R))
    return L.ensure_ccw(pts + outer)


def build_site():
    C = C_SITE
    # platform (paved octagonal floor at z=0) and three steps down to the lawn
    r_plat = 26.0
    L.prism("ARCH_site_platform", L.regular_polygon(r_plat, 96), P.GROUND_Z - 0.3, P.FLOOR_Z, C, mat=M_PAVING, part_type="platform",
            ngon=False, origin=(0, 0, 0))
    for i in range(1, P.PLATFORM_STEPS):
        r0 = r_plat + 0.35 * (i - 1) - 0.1
        r1 = r_plat + 0.35 * i
        L.ring_prism(f"ARCH_site_step_{i}", L.regular_polygon(r1, 96), L.regular_polygon(r0, 96), P.GROUND_Z - 0.3,
                     P.FLOOR_Z - 0.2 * i, C, mat=M_PAVING, part_type="platform")
    sweeps = {az: (side, reach) for az, side, reach in P.PLANTER_SWEEPS}
    for k, fr in enumerate(FRAMES):
        side, reach = sweeps.get(fr.az, (1, None))
        poly = lobe_polygon(fr.az, side, reach)
        band_z0 = P.PODIUM_TOP_Z - P.PODIUM_BAND_H - 0.1
        build_rustication(f"ARCH_site_rostra_{k:02d}", poly, P.GROUND_Z - 0.3, band_z0 + SINK, C, M_PODIUM)
        inner = L.offset_polygon(poly, -P.PODIUM_BAND_RECESS)
        L.prism(f"ARCH_site_rostra_band_{k:02d}", inner, band_z0, P.PODIUM_TOP_Z - 0.1 + SINK, C, mat=M_PODIUM, part_type="rostra",
                ngon=False, bevel=False)
        # Greek-key meander with rosette bosses standing proud of the recessed band face (catalog #12, QA-01-11).
        # ARCH models it as geometry; the sockets let ORN replace it with ORN_greek_key / ORN_rosette_band (hide the
        # ARCH_*_meander_* objects first - see docs/sockets.md, contract additions 2026-09-07).
        build_meander_band(f"ARCH_site_rostra_meander_{k:02d}", inner, band_z0, P.PODIUM_BAND_H, C, M_PODIUM)
        add_frieze_sockets(inner, band_z0, P.PODIUM_BAND_H, extra={"host": "rostra", "modelled_by_arch": True})
        L.prism(f"ARCH_site_rostra_cap_{k:02d}", poly, P.PODIUM_TOP_Z - 0.1, P.PODIUM_TOP_Z, C, mat=M_PODIUM, part_type="rostra",
                ngon=False)
        # urn plinths: one in front of the chamfer and one each side beyond the pedestals
        for da in (-11.5, 0.0, 11.5):
            p = P.az_to_xy(fr.az + da, 26.2)
            L.box(f"ARCH_site_urn_plinth_{k:02d}_{int(da + 20):02d}", p, (P.URN_PLINTH, P.URN_PLINTH), P.PODIUM_TOP_Z - SINK,
                  P.PODIUM_TOP_Z + P.URN_PLINTH_H, C, rot_deg=ang_deg(fr.v), mat=M_PODIUM, part_type="rostra")
            ztop = P.PODIUM_TOP_Z + P.URN_PLINTH_H
            SOCK.add("urn", (p[0], p[1], ztop), fr.v, P.URN_H)
            L.lathe(f"PH_podium_urn_{k:02d}_{int(da + 20):02d}",
                    [(0, ztop), (0.5, ztop), (0.55, ztop + 0.2), (0.35, ztop + 0.45), (0.8, ztop + 1.3), (0.78, ztop + 2.0),
                     (0.5, ztop + 2.45), (0.35, ztop + 2.6), (0.15, ztop + 2.85), (0.0, ztop + 3.0)], C_PH, segments=20,
                    mat=M_PODIUM, part_type="rostra", center=p, origin=(p[0], p[1], ztop), bevel=False)
        # stairs on the lagoon side
        if fr.az in P.STAIR_PIERS:
            build_stair(f"ARCH_site_stair_{k:02d}", fr, side, C)
    build_kerb_wall(C)


def build_stair(name, fr, side, C):
    """Straight flight along the outside of the podium, descending away from the planter sweep."""
    rise, tread, width = 0.175, 0.30, 2.0
    n_steps = int(round((P.PODIUM_TOP_Z - P.GROUND_Z) / rise))
    a_top = fr.az + side * 9.0
    p_top = P.az_to_xy(a_top, P.PODIUM_LOBE_R + 0.3 + width / 2)
    tdir = norm2(sub2(P.az_to_xy(a_top + side * 1.0, P.PODIUM_LOBE_R), P.az_to_xy(a_top, P.PODIUM_LOBE_R)))
    prof = [(0.0, P.GROUND_Z - 0.3)]
    for i in range(n_steps):
        z = P.PODIUM_TOP_Z - i * rise
        prof.append((i * tread, z))
        prof.append(((i + 1) * tread, z))
    prof.append((n_steps * tread, P.GROUND_Z - 0.3))
    radial = norm2(p_top)
    X = (tdir[0], tdir[1], 0.0)
    N = Vector(X).cross(Vector((0, 0, 1)))
    sgn = 1.0 if N.dot(Vector((radial[0], radial[1], 0))) > 0 else -1.0
    origin = (p_top[0] + sgn * radial[0] * width / 2, p_top[1] + sgn * radial[1] * width / 2, 0.0)
    L.plate(name, prof, [], width, origin, X, (0, 0, 1), C, mat=M_PAVING, part_type="platform")
    # cheek walls (refs 063/031): 0.35 thick, parapet 0.9 above the treads, following the slope
    run = n_steps * tread
    cheek = [(-0.35, P.GROUND_Z - 0.3), (-0.35, P.PODIUM_TOP_Z + 0.9), (run + 0.35, P.GROUND_Z + 0.9), (run + 0.35, P.GROUND_Z - 0.3)]
    # `plate` puts its front face on the origin plane and extrudes `thickness` along -N; with u = sgn * radial the
    # flight itself spans u in [-width/2, +width/2] about p_top, so a cheek at origin p_top + u*c spans [c - 0.35, c].
    for c, tag in ((width / 2 + 0.35, "a"), (-width / 2, "b")):
        o = (p_top[0] + sgn * radial[0] * c, p_top[1] + sgn * radial[1] * c, 0.0)
        L.plate(f"{name}_cheek_{tag}", cheek, [], 0.35, o, X, (0, 0, 1), C, mat=M_PODIUM, part_type="rostra")


# ============================================================================= colonnade
class Wing:
    def __init__(self, name, coll):
        self.name, self.coll = name, coll
        spec = P.WINGS[name]
        cx, cy = P.COL_ARC_CENTER
        self.C = (cx, cy)
        self.R = P.COL_ARC_R
        s0, s1 = spec["start"], spec["pylon"]
        th0 = math.atan2(s0[1] - cy, s0[0] - cx)
        th1 = math.atan2(s1[1] - cy, s1[0] - cx)
        d = th1 - th0
        while d > math.pi:
            d -= 2 * math.pi
        while d < -math.pi:
            d += 2 * math.pi
        self.th0, self.sgn = th0, (1 if d > 0 else -1)
        self.L = abs(d) * self.R

    def theta(self, s):
        return self.th0 + self.sgn * s / self.R

    def pt(self, s, r):
        th = self.theta(s)
        return (self.C[0] + r * math.cos(th), self.C[1] + r * math.sin(th))

    def tangent(self, s):
        th = self.theta(s)
        return (-math.sin(th) * self.sgn, math.cos(th) * self.sgn)

    def inward(self, s):
        th = self.theta(s)
        return (-math.cos(th), -math.sin(th))


def build_wing(name, coll):
    W = Wing(name, coll)
    g = P.COLONNADE_GROUND_Z
    r_in, r_out = W.R - P.COL_ROW_SPACING / 2, W.R + P.COL_ROW_SPACING / 2
    # ---- layout along the arc
    clusters = []
    sc = P.COL_FIRST_CLUSTER_S
    while sc + P.COL_MODULE < W.L - 6.0:
        clusters.append(sc)
        sc += P.COL_MODULE
    pos = []   # (s, kind)
    for i, c in enumerate(clusters):
        pos += [(c - P.COL_CLUSTER_PAIR / 2, "cluster"), (c + P.COL_CLUSTER_PAIR / 2, "cluster")]
        nxt = clusters[i + 1] - P.COL_CLUSTER_PAIR / 2 if i + 1 < len(clusters) else W.L - P.COL_CLUSTER_PAIR / 2
        gap = nxt - (c + P.COL_CLUSTER_PAIR / 2)
        n_plain = max(1, int(round(gap / P.COL_BAY)) - 1)
        for j in range(1, n_plain + 1):
            pos.append((c + P.COL_CLUSTER_PAIR / 2 + gap * j / (n_plain + 1), "plain"))
    pos += [(W.L - P.COL_CLUSTER_PAIR / 2, "pylon"), (W.L + P.COL_CLUSTER_PAIR / 2, "pylon")]
    pos.sort()
    # ---- shafts (shared meshes), bases, capital sockets
    r_b, r_t = P.COLONNADE_D / 2, P.COLONNADE_D_TOP / 2
    shaft_src, pylon_src, base_src = {}, {}, None
    idx = 0
    cols = []   # (xy, z_top_of_shaft, is_pylon, inward)
    ret_dir = P.PYLON_RETURN_DIR

    def place_column(xy, inward, tall, tag):
        nonlocal base_src, idx
        h = P.COLONNADE_SHAFT_H + (P.PYLON_EXTRA_H if tall else 0.0)
        srcd = pylon_src if tall else shaft_src
        rz = math.atan2(inward[1], inward[0])
        for lod in (0, 1, 2):
            nm = f"ARCH_colonnade_{name}_column_{idx:03d}_LOD{lod}"
            loc = (xy[0], xy[1], g + P.COLONNADE_BASE_H)
            if lod not in srcd:
                srcd[lod] = L.column_shaft(nm, r_b, r_t, h, coll, lod=lod, mat=M_COLON, part_type="colonnade_column", origin=loc)
                srcd[lod].rotation_euler = (0, 0, rz)
            else:
                L.instance(nm, srcd[lod], loc, rz, coll)
        if base_src is None:
            base_src = L.column_base(f"ARCH_colonnade_{name}_colbase_{idx:03d}", r_b, coll, height=P.COLONNADE_BASE_H + SINK,
                                     plinth=1.15 * P.COLONNADE_D, mat=M_COLON, origin=(xy[0], xy[1], g - SINK))
            for o in base_src:
                o["part_type"] = "colonnade_column"
        else:
            for j, so in enumerate(base_src):
                L.instance(f"ARCH_colonnade_{name}_colbase_{idx:03d}_{j}", so, (xy[0], xy[1], g - SINK), 0.0, coll)
        ztop = g + P.COLONNADE_BASE_H + h
        SOCK.add("capital_colonnade", (xy[0], xy[1], ztop), inward, P.COLONNADE_D_TOP, extra={"tall": bool(tall), "wing": name})
        astragal(f"ARCH_colonnade_{name}_astragal_{idx:03d}", xy, ztop, r_t, coll, M_COLON)
        L.placeholder_capital(f"PH_capital_colonnade_{name}_{idx:03d}", r_t, P.COLONNADE_CAPITAL_H, C_PH, mat=M_COLON,
                              origin=(xy[0], xy[1], ztop))
        cols.append((xy, ztop, tall, inward))
        idx += 1

    for (s, kind) in pos:
        for r in (r_in, r_out):
            place_column(W.pt(s, r), W.inward(s), kind == "pylon", kind)
    # return section to the second pylon (17 m west of the first)
    A_cols = [(W.pt(W.L - P.COL_CLUSTER_PAIR / 2, r_out)), (W.pt(W.L + P.COL_CLUSTER_PAIR / 2, r_out))]
    for a in A_cols:
        for j in (1, 2):
            p = add2(a, mul2(ret_dir, P.PYLON_RETURN * j / 3))
            place_column(p, (-ret_dir[0], -ret_dir[1]), False, "return")
    B_cols = []
    for s in (W.L - P.COL_CLUSTER_PAIR / 2, W.L + P.COL_CLUSTER_PAIR / 2):
        for r in (r_in, r_out):
            p = add2(W.pt(s, r), mul2(ret_dir, P.PYLON_RETURN))
            B_cols.append(p)
            place_column(p, (-ret_dir[0], -ret_dir[1]), True, "pylon")
    # ---- entablatures: two row sweeps (arc), pylon blocks, return beams, pergola beams
    z_ent = g + P.COLONNADE_ABACUS
    prof = colonnade_entablature_profile()
    s_a, s_b = pos[0][0] - 1.0, W.L - P.COL_CLUSTER_PAIR / 2 - 0.9
    nseg = max(8, int((s_b - s_a) / 2.0))
    for r, tag in ((r_in, "inner"), (r_out, "outer")):
        path2 = [W.pt(s_a + (s_b - s_a) * i / nseg, r) for i in range(nseg + 1)]
        p3, nrm, bnr = L.plan_path_to_3d(path2, z_ent, outward_sign=-1.0 if W.sgn > 0 else 1.0)
        # make the profile's +d side point away from the arc centre (radially outward) for consistency
        rad = (path2[0][0] - W.C[0], path2[0][1] - W.C[1])
        if dot2((nrm[0][0], nrm[0][1]), rad) < 0:
            nrm = [(-a, -b, c) for a, b, c in nrm]
        L.sweep_open(f"ARCH_colonnade_{name}_entablature_{tag}", p3, nrm, bnr, prof, coll, mat=M_COLON,
                     part_type="colonnade_entablature", origin=(path2[0][0], path2[0][1], z_ent))
        # mutules under the corona on both sides of the row (LOD0 geometry)
        for sgn, side in ((1.0, "o"), (-1.0, "i")):
            build_dentils(f"ARCH_colonnade_{name}_mutules_{tag}_{side}_LOD0", path2, z_ent + 1.80, 0.20, 1.02, 0.50, coll,
                          pitch=1.125, depth=0.26, closed=False, mat=M_COLON, outward_sign=sgn if W.sgn > 0 else -sgn,
                          part_type="colonnade_entablature")
        SOCK.add("frieze_run", (path2[0][0], path2[0][1], z_ent + 0.02), (rad[0], rad[1]), s_b - s_a,
                 extra={"run_length": s_b - s_a, "arc_center": (W.C[0], W.C[1], 0.0), "arc_radius": r, "subtype": "greek_fret"}, size=0.5)
    # pergola cross beams, one per bay, spanning the two rows
    seen = set()
    for (s, kind) in pos:
        if kind == "pylon":
            continue
        key = round(s, 2)
        if key in seen:
            continue
        seen.add(key)
        a, b = W.pt(s, r_in + 0.5), W.pt(s, r_out - 0.5)
        mid = mul2(add2(a, b), 0.5)
        L.box(f"ARCH_colonnade_{name}_beam_{key:06.1f}", mid, (math.dist(a, b), P.PERGOLA_BEAM), z_ent + P.COLONNADE_ENTABLATURE_H - P.PERGOLA_BEAM,
              z_ent + P.COLONNADE_ENTABLATURE_H - 0.02, coll, rot_deg=ang_deg(sub2(b, a)), mat=M_COLON, part_type="colonnade_entablature")
    # pylon entablature blocks (closed rectangular sweeps, one level up) + boxes
    z_py = z_ent + P.PYLON_EXTRA_H
    for label, centre, tang in (("A", W.pt(W.L, W.R), W.tangent(W.L)),
                                ("B", add2(W.pt(W.L, W.R), mul2(ret_dir, P.PYLON_RETURN)), W.tangent(W.L))):
        w_along = P.COL_CLUSTER_PAIR + 1.9
        w_across = P.COL_ROW_SPACING + 1.9
        rectp = [add2(centre, rot2(c, ang_deg(tang))) for c in [(-w_along / 2, -w_across / 2), (w_along / 2, -w_across / 2),
                                                                (w_along / 2, w_across / 2), (-w_along / 2, w_across / 2)]]
        pyl_prof = [(0.0, 0.0), (0.06, 0.02), (0.06, 0.9), (0.15, 0.95), (0.15, 1.0), (0.06, 1.03), (0.06, 1.75), (0.2, 1.8), (0.35, 1.95),
                    (0.55, 2.0), (0.55, 2.4), (-0.55, 2.4), (-0.55, 0.0), (0.0, 0.0)]
        L.sweep_closed(f"ARCH_colonnade_{name}_pylon_{label}_entablature", rectp, pyl_prof, coll, mat=M_COLON,
                       part_type="colonnade_entablature", z0=z_py, origin=(centre[0], centre[1], z_py))
        L.prism(f"ARCH_colonnade_{name}_pylon_{label}_core", L.offset_polygon(L.ensure_ccw(rectp), -0.5), z_py, z_py + P.COLONNADE_ENTABLATURE_H - 0.03,
                coll, mat=M_COLON, part_type="colonnade_entablature", bevel=False)
        build_box(f"ARCH_colonnade_{name}_pylon_{label}_box", centre, ang_deg(tang), z_py + P.COLONNADE_ENTABLATURE_H, coll,
                  W.inward(W.L) if label == "A" else (-ret_dir[0], -ret_dir[1]))
    # return beams (row height) between the pylons, two rows
    for a in A_cols:
        p0 = add2(a, mul2(ret_dir, 0.9))
        p1 = add2(a, mul2(ret_dir, P.PYLON_RETURN - 0.9))
        p3, nrm, bnr = L.plan_path_to_3d([p0, p1], z_ent)
        L.sweep_open(f"ARCH_colonnade_{name}_return_beam_{len([o for o in coll.objects if 'return_beam' in o.name])}", p3, nrm, bnr, prof,
                     coll, mat=M_COLON, part_type="colonnade_entablature", origin=(p0[0], p0[1], z_ent))
    # cluster boxes on the row entablature
    for c in clusters:
        centre = W.pt(c, W.R)
        build_box(f"ARCH_colonnade_{name}_box_{c:05.1f}", centre, ang_deg(W.tangent(c)), z_ent + P.COLONNADE_ENTABLATURE_H, coll, W.inward(c))
    return dict(columns=idx, clusters=len(clusters), arc_length=W.L, pylons=2)


def build_box(name, centre, rot_deg, z0, coll, inward):
    """Planter box on a 2x2 cluster: four walls with sunk Greek-key-framed panels, a Greek-key base band, lid; maiden sockets."""
    S, H = P.BOX_SIZE, P.BOX_H
    half = S / 2
    band_h = 0.5
    # base band (recessed 0.06) as a slightly smaller prism, then the walls above
    base = [add2(centre, rot2(c, rot_deg)) for c in [(-half + 0.06, -half + 0.06), (half - 0.06, -half + 0.06), (half - 0.06, half - 0.06), (-half + 0.06, half - 0.06)]]
    L.prism(name + "_band", base, z0 - SINK, z0 + band_h + SINK, coll, mat=M_COLON, part_type="box", bevel=False)
    build_meander_band(name + "_meander", L.ensure_ccw(base), z0 + 0.05, band_h - 0.08, coll, M_COLON, part_type="box")
    add_frieze_sockets(L.ensure_ccw(base), z0 + 0.05, band_h - 0.08, min_len=1.0,
                       extra={"host": "planter_box", "modelled_by_arch": True})
    full = [add2(centre, rot2(c, rot_deg)) for c in [(-half, -half), (half, -half), (half, half), (-half, half)]]
    L.prism(name + "_plinth", L.offset_polygon(L.ensure_ccw(full), 0.08), z0 - SINK, z0 + 0.12, coll, mat=M_COLON, part_type="box")
    # walls: plates with a panel hole per face, lid on top
    zw0, zw1 = z0 + band_h, z0 + H
    for i in range(4):
        a, b = full[i], full[(i + 1) % 4]
        d = norm2(sub2(b, a))
        out = (d[1], -d[0])
        if dot2(out, sub2(mul2(add2(a, b), 0.5), centre)) < 0:
            out = (-out[0], -out[1])
            d = (-d[0], -d[1])
            a, b = b, a
        mid = mul2(add2(a, b), 0.5)
        outline = [(-S / 2, zw0), (S / 2, zw0), (S / 2, zw1), (-S / 2, zw1)]
        pw, ph = S - 2 * 0.9, (zw1 - zw0) - 2 * 0.55
        hole = L.rect(0.0, (zw0 + zw1) / 2 - 0.05, pw, ph)
        X = (d[0], d[1], 0.0)
        N = Vector(X).cross(Vector((0, 0, 1)))
        if N.dot(Vector((out[0], out[1], 0))) < 0:
            X = (-d[0], -d[1], 0.0)
        L.plate(f"{name}_wall_{i}", outline, [hole], 0.45, (mid[0], mid[1], 0.0), X, (0, 0, 1), coll, mat=M_COLON, part_type="box")
        fr_obj = panel_frame(f"{name}_frame_{i}", (mid[0], mid[1], 0.0), X, pw, ph, (zw0 + zw1) / 2 - 0.05, 0.30, coll, M_COLON, proud=0.03)
        fr_obj["part_type"] = "box"
        field = L.rect(0.0, (zw0 + zw1) / 2 - 0.05, pw + 0.2, ph + 0.2)
        L.plate(f"{name}_panel_{i}", field, [], 0.5, (mid[0] - out[0] * 0.15, mid[1] - out[1] * 0.15, 0.0), X, (0, 0, 1), coll,
                mat=M_COLON, part_type="box", bevel=False)
    lid = [add2(centre, rot2(c, rot_deg)) for c in [(-half + 0.4, -half + 0.4), (half - 0.4, -half + 0.4), (half - 0.4, half - 0.4), (-half + 0.4, half - 0.4)]]
    L.prism(name + "_lid", lid, zw1 - 0.5, zw1 + 0.05, coll, mat=M_COLON, part_type="box", bevel=False)
    # maidens at the four corners: feet at the box BASE level (top of the entablature), standing 0.32 m outward from
    # the box's vertical corner edge on the corner diagonal, backs outward; the rim is BOX_H above their feet
    for cx, cy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
        diag = norm2(rot2((cx, cy), rot_deg))
        p = add2(centre, mul2(diag, half * math.sqrt(2) + P.MAIDEN_OUT))
        SOCK.add("maiden", (p[0], p[1], z0), diag, 4.4, extra={"rim_height": P.BOX_H, "box_corner_y": -P.MAIDEN_OUT}, size=0.5)
        L.box(f"PH_{name.split('ARCH_')[-1]}_maiden_{cx + 1}{cy + 1}", add2(p, mul2(diag, -0.5)), (0.9, 0.7), z0, z0 + 4.4, C_PH,
              rot_deg=ang_deg(diag) + 90, mat=M_COLON, part_type="box", bevel=False)


# ============================================================================= build everything
print("[arch] building rotunda ...")
build_rotunda()
print(f"[arch] rotunda done {time.time() - T0:.1f}s; building site ...")
build_site()
print(f"[arch] site done {time.time() - T0:.1f}s; building colonnades ...")
wing_stats = {n: build_wing(n, c) for n, c in (("north", C_CN), ("south", C_CS))}
print(f"[arch] colonnades done {time.time() - T0:.1f}s")

# ---- bevel sweep (materials request 2026-09-07: 2-4 cm on every arris the edge-wear mask reads from -- cornices,
# pedestals, attic blocks, podium edges, box and pylon blocks, column bases). Objects built with bevel=False for a
# reason (flute geometry, dentil/egg arrays, meander and coffer detail, the dome shell, sunk panels) stay unbevelled:
# a 3 cm bevel on a 15 cm dentil eats the moulding and multiplies the tri count.
BEVEL_ALSO = ("attic_corner_cap", "attic_frame", "attic_roof", "attic_volute", "drum_cornice", "dome_apex_cap",
              "colbase", "ressaut_core", "impost_", "archivolt", "rostra_band", "rostra_cap", "rostra_course",
              "pylon_A_core", "pylon_B_core", "box_band", "box_lid", "box_frame", "stair")
_bev = 0
for o in ARCH.all_objects:
    if o.type != "MESH" or not o.name.startswith("ARCH_"):
        continue
    if any(m.type == "BEVEL" for m in o.modifiers):
        continue
    if any(t in o.name for t in BEVEL_ALSO):
        L.add_bevel(o)
        _bev += 1
print(f"[arch] bevels added to {_bev} objects (width {P.BEVEL_WIDTH} m, {P.BEVEL_SEGMENTS} segments)")

# LOD default: LOD1 in the viewport AND in renders (LOD0/LOD2 are hide_render=True in the saved file so that a naive
# render never stacks three shafts; the lead's common.set_lod_visibility switches hide_viewport, flip hide_render alike)
common.set_lod_visibility(1)   # lead's convention since Phase 3: viewport LOD1, render LOD0 (common.set_lod)

# ---- stats
stats = {"sockets": dict(SOCK.counts), "wings": wing_stats}
for lod in (0, 1, 2):
    objs = [o for o in ARCH.all_objects if o.type == "MESH" and (f"_LOD{lod}" in o.name or "_LOD" not in o.name) and not o.name.startswith("PH_")]
    stats[f"tris_LOD{lod}"] = L.tri_count(objs)
stats["tris_placeholders"] = L.tri_count([o for o in C_PH.objects])
stats["objects"] = len(ARCH.all_objects)
stats["build_seconds"] = round(time.time() - T0, 1)
print("[arch] stats:", json.dumps(stats, indent=1))
(common.DOCS / "arch_stats.json").write_text(json.dumps(stats, indent=1))

if SAVE:
    common.save_blend(common.ASSETS / "architecture.blend")

# ============================================================================= preview rig (not saved)
if PREVIEW:
    if "--lod1" in ARGS:   # preview the viewport LOD instead of the render default (LOD0)
        common.set_lod(viewport=1, render=1)
    rig = common.rebuild_collection("PREVIEW_RIG")
    site = common.load_site_local()
    sun = bpy.data.lights.new("PREVIEW_sun", "SUN")
    sun.energy = 4.0
    sun.angle = 0.0093
    so = bpy.data.objects.new("PREVIEW_sun", sun)
    rig.objects.link(so)
    sun_az, sun_el = (118.5, 7.4) if "--golden" in ARGS else (135.0, 38.0)
    common.aim_sun(so, sun_az, sun_el)
    world = bpy.data.worlds.new("PREVIEW_world")
    world.use_nodes = True
    nt = world.node_tree
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_elevation = math.radians(sun_el)
    sky.sun_rotation = math.radians(sun_az)
    sky.sun_disc = False
    bg = nt.nodes.get("Background")
    nt.links.new(sky.outputs[0], bg.inputs[0])
    bg.inputs[1].default_value = 0.35
    scene.world = world
    scene.view_settings.exposure = -1.0
    # ground + water for context
    lawn = common.placeholder_material("MAT_lawn")
    water = common.placeholder_material("MAT_water_lagoon", roughness=0.05)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=700)
    me = bpy.data.meshes.new("PREVIEW_ground")
    bm.to_mesh(me)
    bm.free()
    g = bpy.data.objects.new("PREVIEW_ground", me)
    g.location = (0, 0, P.GROUND_Z - 0.02)
    rig.objects.link(g)
    common.assign_material(g, lawn)
    for i, poly in enumerate(site["lagoon0"]):
        bm = bmesh.new()
        vs = [bm.verts.new((x, y, P.WATER_Z)) for x, y in poly]
        f = bm.faces.new(vs)
        bmesh.ops.triangulate(bm, faces=[f])
        me = bpy.data.meshes.new(f"PREVIEW_water_{i}")
        bm.to_mesh(me)
        bm.free()
        w = bpy.data.objects.new(f"PREVIEW_water_{i}", me)
        rig.objects.link(w)
        common.assign_material(w, water)
        w.location.z = 0.03   # water plane slightly above the ground plane
    cams = None
    if "--hero-only" in ARGS:
        cams = ["01_lagoon"]
    if "--cams" in ARGS and ARGS.index("--cams") + 1 < len(ARGS):   # e.g. --cams 01,03 (matched as substrings)
        cams = ARGS[ARGS.index("--cams") + 1].split(",")
    tag = "" if "--tag" not in ARGS else ARGS[ARGS.index("--tag") + 1]
    res = (tuple(int(v) for v in ARGS[ARGS.index("--res") + 1].split("x"))
           if "--res" in ARGS and ARGS.index("--res") + 1 < len(ARGS) else (1280, 720))
    outs = common.render_previews("architecture", cameras=cams, samples=16, tag=tag, res=res)
    # extra: an up-looking ceiling camera (the QA cam 04 rotation (0,0,pi) looks down; reported to the lead)
    if not cams or any("04" in c for c in cams):
        cd = bpy.data.cameras.new("CAM_arch_ceiling_up")
        cd.lens, cd.sensor_width, cd.sensor_fit, cd.clip_end = 15.0, 36.0, "HORIZONTAL", 5000.0
        co = bpy.data.objects.new("CAM_arch_ceiling_up", cd)
        co.location = (0.0, 3.0, 1.6)
        co.rotation_euler = (math.pi, 0.0, 0.0)
        rig.objects.link(co)
        scene.camera = co
        fp = common.RENDERS / "previews" / "architecture" / f"{outs[0].name.split('_')[0]}_{outs[0].name.split('_')[1]}_04b_ceiling_up{('_' + tag) if tag else ''}.png"
        scene.render.filepath = str(fp)
        bpy.ops.render.render(write_still=True)
        outs.append(fp)
    print("[arch] previews:", [str(p) for p in outs])
print(f"[arch] total {time.time() - T0:.1f}s")
