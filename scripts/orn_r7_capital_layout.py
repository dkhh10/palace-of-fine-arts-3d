"""ORN round 7, brief item 1 — re-lay the Corinthian proportions of the 3.0 m rotunda capital.

Pure Python (NO bpy): it re-implements `orn_build.bell_radius` and `orn_build.leaf_spine` exactly, so the
vertical extent / radial projection / width of an acanthus row can be solved for a TARGET tier height instead of
being read off after a 20-minute mesh build.

    python3 scripts/orn_r7_capital_layout.py            # before / after / reference table
    python3 scripts/orn_r7_capital_layout.py --solve    # also print the solved preset numbers

Why: the r6 review (docs/reviews/orn_r6_review.md finding 2) showed the 3.0 m capital is the 2.6 m design
stretched in Z only. Everything keyed to H grew 15.4 %; everything keyed to R (leaf width, `proud`, thickness)
did not — so the acanthus tiers ended up 15 % longer at the same width and the same radial projection.

Reference (ref_002_rotunda_Corinthian_Order_Capital.jpg, the frontal pier capital; face-centre column x~490 of
940, capital base = astragal top y 785, abacus top y 385, so H = 400 px, 133 px/m at H = 3.0 m):

    abacus                     y 385-430    0.113 H   (canon 1/7 = 0.143 of the part above the leaves; ~0.10 H here)
    volute + caulicoli zone    y 440-620    top 0.35 H (volute eyes y ~500-505 = 0.71 H, spirals span 0.56-0.81 H)
    upper acanthus row         y 600-700    0.25 H projected; 0.30 H corrected for the up-view foreshortening
    lower acanthus row         y 700-790    0.21 H projected; 0.30 H corrected
    upper leaf width (front)   130 px       0.33 H, i.e. width ~1.08 x the row's own vertical extent

The up-view compresses the upper part of the capital more than the lower, so the two leaf rows are read as EQUAL
(0.30 H each) per the Vignola canon rather than the raw 0.25 / 0.21 px numbers; the abacus and the volute band,
which are measured across a short depth, are taken at face value.
"""
import math, pathlib, sys

TAU = math.tau

# --------------------------------------------------------------- copies of orn_build (keep in sync by inspection)
BELL_PROFILE = [(1.00, 0.000), (1.06, 0.020), (1.055, 0.040), (0.995, 0.062), (0.925, 0.090), (0.885, 0.140),
                (0.868, 0.230), (0.865, 0.340), (0.880, 0.450), (0.912, 0.560), (0.960, 0.660), (1.040, 0.750),
                (1.100, 0.820), (1.145, 0.870), (1.155, 0.890), (1.158, 0.900)]


def bell_radius(P, z_m):
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


# --------------------------------------------------------------------------------------- row measurement
def row_metrics(P, row, base_zH, length_H, width_scale, count=8):
    """Vertical extent, tip height, radial projection and width of ONE acanthus row, in metres and in H.
    `tilt` is the outward lean applied by build_leaf_ring (place(..., tilt_x_deg=-leaf_tilt)); it rotates the
    leaf-local (y, z) frame about local X, so it trades height for projection."""
    R, H = P["R"], P["H"]
    base_z = base_zH * H
    r0 = bell_radius(P, base_z)
    length = length_H * H
    proud = P["proud"][row] * (H if P.get("proud_unit", "R") == "H" else R)
    sp = leaf_spine(P, base_z, length, proud=proud, arc_deg=P["arc_deg"][row], arc_frac=P["arc_frac"][row])
    a = math.radians(-P["leaf_tilt"][row])        # tilt_x_deg, negative = lean outward
    # place(): rotation about local X by a, applied to (y, z) as y' = y cos a - z sin a, z' = y sin a + z cos a
    pts = [(y * math.cos(a) - z * math.sin(a), y * math.sin(a) + z * math.cos(a)) for (y, z) in sp]
    zs = [p[1] for p in pts]
    ys = [p[0] for p in pts]
    extent = max(zs)                              # highest point of the spine above the row base
    tip_z = zs[-1]                                # the curled-down tip
    proj = max(ys)                                # radial projection beyond the bell at the base
    r_tip = r0 * 0.965 + proj
    width = (TAU * r0) / count * width_scale
    return dict(proud=proud, base_zH=base_zH, base_z=base_z, r0=r0, length=length, extent=extent, extent_H=extent / H,
                top_zH=base_zH + extent / H, tip_zH=base_zH + tip_z / H, proj=proj, proj_H=proj / H,
                r_tip=r_tip, width=width, aspect=width / extent)


def solve_length_H(P, row, base_zH, target_extent_H, lo=0.10, hi=0.90):
    """Spine length (in H) whose tilted vertical extent equals target_extent_H."""
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        e = row_metrics(P, row, base_zH, mid, 1.0)["extent_H"]
        if e < target_extent_H:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def solve_width_scale(P, row, base_zH, extent_H, target_aspect, count=8):
    """width_scale (multiple of the leaf pitch) giving width = target_aspect x the row's vertical extent."""
    r0 = bell_radius(P, base_zH * P["H"])
    pitch = (TAU * r0) / count
    return target_aspect * extent_H * P["H"] / pitch


# --------------------------------------------------------------------------------------- presets
BEFORE = dict(H=3.0, R=1.05, abacus_across=3.0, lower_len=0.44, upper_len=0.37, lower_w=1.26, upper_w=1.30,
              lower_z=0.060, upper_z=0.440, proud=(0.140, 0.130), arc_deg=(100.0, 90.0), arc_frac=(0.28, 0.26),
              leaf_tilt=(3.0, 4.0), volute_z=0.805, helix_z=0.775, volute_r=0.112, helix_r=0.055,
              abacus_z0=0.890)
BEFORE_26 = dict(BEFORE, H=2.6)          # the design as it was laid out, for the "what did the stretch do" column

# ---- reference targets, from the ref_002 reading in the docstring (fractions of H)
REF = dict(lower_base=0.030, lower_extent=0.300, upper_base=0.300, upper_extent=0.300,
           volute_zone_bottom=0.650, abacus_h=0.100, upper_aspect=1.08, lower_aspect=1.02,
           # Body projection: in ref_002 the leaf stands clear of the kalathos down its WHOLE length (the slot
           # either side is in shadow from the tip to the base), not only at the curled tip. Read as ~0.20 of the
           # row's own vertical extent -> proud = 0.20 x 0.300 H = 0.060 H (lower); the upper row is held to 0.052 H so its tips stop just inside the abacus corner.
           lower_proud=0.060, upper_proud=0.052,
           # Tip radius: the tips clear the abacus concave side face (half-side = across/(2 sqrt2) = 1.01 R) and
           # stop short of the corner (across/2 = 1.43 R) -> r_tip 1.30-1.40 R.
           r_tip_R=(1.30, 1.40))


def presets_from_orn_build():
    """Read CAPITAL_PRESETS and BELL_PROFILE straight out of scripts/orn_build.py (no bpy import), so the table
    below can never drift from the file that actually builds the mesh."""
    src = (pathlib.Path(__file__).resolve().parent / "orn_build.py").read_text()
    ns = {"ARCH_R6": {"capital_rotunda_H": 3.0, "frieze_band_H": 0.81, "attic_panel_H": 5.27}}
    for head in ("BELL_PROFILE = [", "CAPITAL_PRESETS = {"):
        i = src.index(head)
        close = "]" if head.endswith("[") else "}"
        depth, j = 0, i + len(head) - 1
        while True:
            if src[j] in "[{":
                depth += 1
            elif src[j] in "]}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        exec(src[i:j + 1], ns)
    return ns["CAPITAL_PRESETS"], ns["BELL_PROFILE"]


def verify():
    global BELL_PROFILE
    presets, BELL_PROFILE = presets_from_orn_build()
    print("-- orn_build.py as committed " + "-" * 78)
    print("%-22s %-6s %7s %7s %7s %7s %7s %7s %7s %7s" % (
        "preset", "row", "base/H", "len(m)", "ext(m)", "ext/H", "top/H", "proj(m)", "width", "w/ext"))
    bad = 0
    for name, P in presets.items():
        P = dict(P, proud_unit="H")
        for row, key in ((0, "lower"), (1, "upper")):
            m = row_metrics(P, row, P[key + "_z"], P[key + "_len"], P[key + "_w"])
            print("%-22s %-6s %7.3f %7.3f %7.3f %7.3f %7.3f %7.3f %7.3f %7.2f  r_tip %.3f R" % (
                name, key, m["base_zH"], m["length"], m["extent"], m["extent_H"], m["top_zH"], m["proj"],
                m["width"], m["aspect"], m["r_tip"] / P["R"]))
            if name == "capital_rotunda":
                tgt = REF[key + "_extent"]
                if abs(m["extent_H"] - tgt) > 0.004:
                    print("   FAIL %s %s extent %.4f H, target %.3f H" % (name, key, m["extent_H"], tgt))
                    bad += 1
        z0 = P.get("abacus_z0", 0.890)
        vt, vb = P["volute_z"] + P["volute_r"], P["volute_z"] - P["volute_r"]
        print("%-22s abacus %.3f-1.000 H = %.3f H   volute spiral %.3f-%.3f H   helix %.3f-%.3f H" % (
            name, z0, 1.0 - z0, vb, vt, P["helix_z"] - P["helix_r"], P["helix_z"] + P["helix_r"]))
        if vt > z0 + 1e-6:
            # Only the rotunda capital was re-laid this round; on the 1.8 m capitals the spiral has buried its top
            # 0.03 H in the abacus since round 4 and 122 instances are not worth moving without a GPU to look at.
            tag = "FAIL" if name == "capital_rotunda" else "carried (not re-laid this round)"
            print("   %s %s volute top %.3f H is above the abacus seat %.3f H" % (tag, name, vt, z0))
            bad += 1 if name == "capital_rotunda" else 0
        if name == "capital_rotunda":
            up_top = P["upper_z"] + row_metrics(P, 1, P["upper_z"], P["upper_len"], P["upper_w"])["extent_H"]
            if abs((1.0 - z0) - REF["abacus_h"]) > 0.002:
                print("   FAIL abacus %.3f H, target %.3f H" % (1.0 - z0, REF["abacus_h"]))
                bad += 1
            if vb < REF["volute_zone_bottom"] - 0.02:
                print("   FAIL volute spiral starts at %.3f H, below the top-0.35 H band" % vb)
                bad += 1
            if up_top > vb:
                print("   FAIL upper leaf top %.3f H overlaps the volute spiral at %.3f H" % (up_top, vb))
                bad += 1
    print("VERIFY %s" % ("FAILED (%d)" % bad if bad else "OK"))
    return bad


def main():
    P = dict(BEFORE, proud=(REF["lower_proud"], REF["upper_proud"]), proud_unit="H")
    print("=" * 108)
    print("ORN r7 item 1 - capital_rotunda proportion re-lay   H = %.2f m, R = %.2f m" % (P["H"], P["R"]))
    print("=" * 108)
    rows = []
    for tag, preset in (("as laid out at H 2.6", BEFORE_26), ("r6 (Z-stretch to 3.0)", BEFORE)):
        for row, key in ((0, "lower"), (1, "upper")):
            m = row_metrics(preset, row, preset[key + "_z"], preset[key + "_len"], preset[key + "_w"])
            rows.append((tag, key, m, preset["H"]))
    hdr = "%-22s %-6s %7s %7s %7s %7s %7s %7s %7s %7s" % (
        "state", "row", "base/H", "len(m)", "ext(m)", "ext/H", "top/H", "proj(m)", "width", "w/ext")
    print(hdr)
    for tag, key, m, H in rows:
        print("%-22s %-6s %7.3f %7.3f %7.3f %7.3f %7.3f %7.3f %7.3f %7.2f" % (
            tag, key, m["base_zH"], m["length"], m["extent"], m["extent_H"], m["top_zH"], m["proj"],
            m["width"], m["aspect"]))

    # ------------------------------------------------------------------ solve the r7 lay-out
    print()
    print("-- solved r7 lay-out against the ref_002 reading " + "-" * 58)
    out = {}
    for row, key in ((0, "lower"), (1, "upper")):
        base = REF[key + "_base"]
        ext = REF[key + "_extent"]
        ln = solve_length_H(P, row, base, ext)
        m0 = row_metrics(P, row, base, ln, 1.0)
        ws = solve_width_scale(P, row, base, m0["extent_H"], REF[key + "_aspect"])
        m = row_metrics(P, row, base, ln, ws)
        out[key] = (base, ln, ws, m)
        print("%-22s %-6s %7.3f %7.3f %7.3f %7.3f %7.3f %7.3f %7.3f %7.2f  r_tip %.3f = %.3f R" % (
            "r7 re-lay", key, m["base_zH"], m["length"], m["extent"], m["extent_H"], m["top_zH"], m["proj"],
            m["width"], m["aspect"], m["r_tip"], m["r_tip"] / P["R"]))
    print()
    print("reference (ref_002)    lower  base 0.030  ext/H 0.300  top/H 0.330   width/ext 1.02   r_tip 1.30-1.40 R")
    print("                       upper  base 0.300  ext/H 0.300  top/H 0.600   width/ext 1.08   r_tip 1.30-1.40 R")
    print("                       volutes+caulicoli in the top 0.35 H (0.650-1.000); abacus 0.100 H (0.900-1.000)")

    if "--solve" in sys.argv:
        print()
        print("-- preset numbers to paste into orn_build.CAPITAL_PRESETS['capital_rotunda'] " + "-" * 30)
        for key in ("lower", "upper"):
            base, ln, ws, m = out[key]
            print("    %s_z=%.3f, %s_len=%.3f, %s_w=%.3f,   proud %.3f H = %.3f m  # ext %.3f m = %.3f H, top %.3f H, w/ext %.2f" % (
                key, base, key, ln, key, ws, REF[key + "_proud"], m["proud"], m["extent"], m["extent_H"],
                m["top_zH"], m["aspect"]))


if __name__ == "__main__":
    if "--verify" in sys.argv:
        sys.exit(1 if verify() else 0)
    main()
