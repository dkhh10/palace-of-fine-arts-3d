#!/usr/bin/env python3
"""ARCH / QA-04-11: fit a camera station to reference photo 062 ("View of Rotunda from north-east"),
the way `arch_domecheck.fit_photo` fitted ref 063 in polish round 1 -- but on hand-read LANDMARK ROWS
instead of the sky-silhouette profile, because ref 062's top silhouette is dominated by ORNAMENT
(the attic corner-block volutes, urns and standing figures rise 20-80 px above the cornice the
analytic model knows about), so a profile fit would measure the sculpture, not the architecture.

Method (no Blender; numpy only). All landmarks lie on the near octagon face's centre line, so their
image ROW is what carries the information:

    row(z, d) = ry/2 - f * ( -d sin(t) + (z - h) cos(t) ) / ( d cos(t) + (z - h) sin(t) )

with f = rx * lens / 36 (Blender, sensor_fit HORIZONTAL), t = camera pitch (up positive), h = eye height,
d = the landmark's horizontal distance from the camera = D - (its radius from the rotunda axis).
This is exactly `arch_domecheck.Cam`, which the script uses so the fit and the overlay cannot drift apart.

Unknowns: D (station distance from the rotunda axis), lens, pitch. Eye height h is held (default 1.55 m,
a hand-held photograph) and swept for sensitivity. Four landmark rows -> one degree of freedom of residual,
then the fitted station PREDICTS the podium base row and the on-screen width, which are the independent test
(QA-04-11's acceptance: top, base and width within 3 %).

    python3 scripts/arch_ref062_fit.py                    # fit, residual, predictions, sensitivity
    python3 scripts/arch_ref062_fit.py --overlay out.png  # + red analytic silhouette drawn on ref 062
"""
import argparse, math, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arch_params as P
import arch_domecheck as DC

PHOTO = ("/Users/dk/Projects/3d render blender 3rd attempt building/"
         "reference/photos/canonical/cam_02_ne_shore_threequarter.jpg")   # = reference/photos/raw/ref_062_*.jpg
RES = (1920, 1371)
NEAR_FACE_AZ = 37.0        # the octagon face the camera looks at (faces at FACE_AZ0 + 45k = 82,127,...,352,37)

# ---------------------------------------------------------------- landmarks read off ref 062 (rows, 1920x1371)
# Each: (label, z, radius from the rotunda axis, measured row, sigma).  Radius = how far the feature stands out
# from the axis, so its distance from the camera is D - radius.  Rows were read from 1.6-2x zoomed crops with a
# 20 px ruler (scratchpad ref062_center / ref062_arch); sigma is the width of the moulding the line sits on.
LANDMARKS = [
    ("dome apex (cap top)",      P.DOME_APEX_Z + 0.6, 0.0,                  35.0,  4.0),
    ("attic top (drum springs)", P.ATTIC_Z1,          P.WALL_APOTHEM + P.ATTIC_CORNICE_D, 99.0,  6.0),
    ("attic base (modillions)",  P.ATTIC_Z0,          P.WALL_APOTHEM,       330.0, 12.0),
    ("outer arch springing",     P.ARCH_SPRING_Z,     P.WALL_APOTHEM,       700.0, 15.0),
]
# Independent predictions (not fitted): the near podium lobe, which is what QA's "base at 0.85 of frame height"
# and "width" refer to.  Measured on the same photo, left-hand lobe.
PODIUM_BASE_ROW = 1345.0       # rusticated wall meets the ground behind the planting, near-left lobe
PODIUM_BASE_SIGMA = 25.0
# Widths.  The podium reading is only a LOWER bound on the model side: the masonry that runs to both frame edges
# in ref 062 is the planter sweeps (r 29.9-37.6), which podium_points() does not carry, and the right-hand run is
# cut by the frame.  The attic ring is the clean width landmark (it is also QA's W_a): outermost attic corner-block
# masonry against the sky, read from the sky boundary of the photo.
PHOTO_WIDTH_PX = (233.0, 1900.0)   # outermost podium/planter masonry, left and right
PHOTO_ATTIC_PX = (395.0, 1660.0)   # outermost attic corner-block masonry against the sky


def rows(D, lens, pitch_deg, h):
    """Predicted rows for LANDMARKS at a station D metres from the axis on the near face's normal."""
    cam = station(D, lens, pitch_deg, h)
    n = np.array(P.az_dir(NEAR_FACE_AZ))
    pts = np.array([[n[0] * r, n[1] * r, z] for _, z, r, _, _ in LANDMARKS])
    return cam.project(pts)[:, 1]


def station(D, lens, pitch_deg, h, res=RES):
    """arch_domecheck.Cam for the fitted station (camera on the near face's normal, looking at the axis)."""
    x, y = P.az_to_xy(NEAR_FACE_AZ, D)
    tz = h + D * math.tan(math.radians(pitch_deg))
    return DC.Cam(dict(loc=(x, y, h), target=(0.0, 0.0, tz), lens=lens, shift_y=0.0, res=res))


def cost(q, h):
    D, lens, pitch = q
    if not (25 < D < 400 and 8 < lens < 200 and -5 < pitch < 45):
        return 1e9
    r = rows(D, lens, pitch, h)
    if not np.isfinite(r).all():
        return 1e9
    obs = np.array([m[3] for m in LANDMARKS])
    sig = np.array([m[4] for m in LANDMARKS])
    return float(np.sum(((r - obs) / sig) ** 2))


def fit(h=1.55, start=(70.0, 26.0, 12.0)):
    q = list(start)
    steps = [20.0, 8.0, 6.0]
    while max(steps) > 1e-4:
        moved = False
        for i in range(3):
            for s in (steps[i], -steps[i]):
                t = list(q)
                t[i] += s
                if cost(t, h) < cost(q, h) - 1e-9:
                    q, moved = t, True
        if not moved:
            steps = [s * 0.5 for s in steps]
    return q, cost(q, h)


# ---------------------------------------------------------------- podium (for the base row and the width)
def podium_points(nseg=60):
    """Outer face of the 8 rostra lobes (r = PODIUM_LOBE_R, +-PODIUM_LOBE_HALF_ANGLE about each pier azimuth),
    from the lawn to the podium top, plus the paved platform octagon between them."""
    pts = []
    for k in range(8):
        az0 = P.VERTEX_AZ0 + 45 * k
        for a in np.linspace(az0 - P.PODIUM_LOBE_HALF_ANGLE, az0 + P.PODIUM_LOBE_HALF_ANGLE, nseg):
            x, y = P.az_to_xy(a, P.PODIUM_LOBE_R)
            for z in (P.GROUND_Z, P.PODIUM_TOP_Z):
                pts.append((x, y, z))
    oc = [P.az_to_xy(P.FACE_AZ0 + 45 * k, P.PLATFORM_APOTHEM) for k in range(8)]
    for i in range(8):
        a, b = np.array(oc[i]), np.array(oc[(i + 1) % 8])
        for t in np.linspace(0, 1, 40, endpoint=False):
            p = a + (b - a) * t
            pts += [(p[0], p[1], P.GROUND_Z), (p[0], p[1], P.FLOOR_Z)]
    return np.array(pts)


def predictions(D, lens, pitch, h):
    cam = station(D, lens, pitch, h)
    pod = cam.project(podium_points())
    ok = np.isfinite(pod[:, 0])
    pod = pod[ok]
    base_row = float(pod[:, 1].max())          # the lowest (nearest) podium point on screen
    x_lo, x_hi = float(pod[:, 0].min()), float(pod[:, 0].max())
    # dome clearance over the NEAR face's attic cornice and over the whole attic ring (QA's stricter test)
    n = np.array(P.az_dir(NEAR_FACE_AZ))
    near_att = cam.project(np.array([[n[0] * (P.WALL_APOTHEM + P.ATTIC_CORNICE_D), n[1] * (P.WALL_APOTHEM + P.ATTIC_CORNICE_D), P.ATTIC_Z1]]))[0, 1]
    apex = cam.project(np.array([[0.0, 0.0, P.DOME_APEX_Z + 0.6]]))[0, 1]
    ring = DC.top_profile(cam, DC.attic_top_ring(), cam.rx)
    ring_top = float(np.nanmin(ring[np.isfinite(ring)]))
    at = cam.project(DC.attic_top_ring())
    at = at[np.isfinite(at[:, 0])]
    a_lo, a_hi = float(at[:, 0].min()), float(at[:, 0].max())
    return dict(base_row=base_row, x_lo=x_lo, x_hi=x_hi, width=x_hi - x_lo,
                a_lo=a_lo, a_hi=a_hi, attic_width=a_hi - a_lo,
                clear_near_face=near_att - apex, clear_attic_ring=ring_top - apex)


def clearance_threshold(h=1.55):
    """The one lens- and tilt-INDEPENDENT fact in ref 062: the dome cap is visible above the near face's attic
    cornice, i.e. the apex's elevation angle exceeds the cornice's.  That is a pure comparison of two
    (height / distance) ratios, so it fixes a MINIMUM station distance for any given vertical stack:

        (apex - h) / D  >  (ATTIC_Z1 - h) / (D - r_att)   ->   D  >  r_att (apex - h) / (apex - ATTIC_Z1)

    and, inverted, it says what the stack would have to be for a CLOSE station to show the same thing."""
    apex = P.DOME_APEX_Z + 0.6
    r_att = P.WALL_APOTHEM + P.ATTIC_CORNICE_D
    d_min = r_att * (apex - h) / (apex - P.ATTIC_Z1)
    out = dict(d_min=d_min)
    for D in (45.0, 50.0):
        # apex needed at this D with the attic where it is; attic needed at this D with the apex where it is
        out[f"apex_needed_at_{D:.0f}"] = h + (P.ATTIC_Z1 - h) * D / (D - r_att)
        out[f"attic_needed_at_{D:.0f}"] = h + (apex - h) * (D - r_att) / D
    return out


def land_check(azs=(15, 25, 35, 45, 60), dists=(45, 60, 75, 92, 105, 120)):
    """Is the fitted station on land?  Point-in-polygon against the OSM lagoon rings in
    reference/plans/site_local.json (which uses +x east, +y north; world (X, Y) = (-y_north, x_east))."""
    import json
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reference", "plans", "site_local.json")
    if not os.path.exists(p):
        p = ("/Users/dk/Projects/3d render blender 3rd attempt building/reference/plans/site_local.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p))
    rings = [[(q[0], q[1]) for q in ring] for k in d if k.startswith("lagoon") for ring in d[k]]

    def inside(poly, pt):
        x, y = pt
        c, j = False, len(poly) - 1
        for i in range(len(poly)):
            xi, yi = poly[i]
            xj, yj = poly[j]
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                c = not c
            j = i
        return c
    rows_out = []
    for az in azs:
        cells = []
        for D in dists:
            X, Y = P.az_to_xy(az, D)
            n = sum(1 for rg in rings if inside(rg, (Y, -X)))
            cells.append("water" if n % 2 == 1 else "LAND ")
        rows_out.append((az, cells))
    return dists, rows_out


def draw_overlay(q, h, out):
    from PIL import Image, ImageDraw
    D, lens, pitch = q
    im = Image.open(PHOTO).convert("RGB")
    W, H = im.size
    cam = station(D, lens, pitch, h, res=(W, H))
    d = ImageDraw.Draw(im)
    # analytic top silhouette (attic ring + drum + dome) in red
    allpts = np.vstack([DC.attic_top_ring(), DC.dome_drum_surface(), DC.drum_wall_surface()])
    mp = DC.top_profile(cam, allpts, W)
    prev = None
    for i in range(W):
        if np.isfinite(mp[i]) and 0 <= mp[i] < H:
            if prev is not None and i - prev[0] <= 2:
                d.line([prev, (i, mp[i])], fill=(255, 40, 40), width=3)
            prev = (i, mp[i])
        else:
            prev = None
    # podium silhouette in cyan
    pod = cam.project(podium_points())
    for u, v in pod:
        if np.isfinite(u) and 0 <= u < W and 0 <= v < H:
            d.ellipse([u - 2, v - 2, u + 2, v + 2], fill=(40, 230, 255))
    # measured landmark rows in yellow, predicted rows in green
    pr = rows(D, lens, pitch, h)
    for (lab, z, r, obs, sig), py in zip(LANDMARKS, pr):
        d.line([(0, obs), (W, obs)], fill=(255, 220, 0), width=2)
        d.line([(0, py), (W, py)], fill=(60, 255, 60), width=1)
        d.text((8, obs + 3), f"{lab}  z={z:.1f}  obs {obs:.0f}  fit {py:.0f}", fill=(255, 220, 0))
    p = predictions(D, lens, pitch, h)
    d.line([(0, PODIUM_BASE_ROW), (W, PODIUM_BASE_ROW)], fill=(255, 220, 0), width=2)
    d.line([(0, p["base_row"]), (W, p["base_row"])], fill=(60, 255, 60), width=1)
    d.text((8, PODIUM_BASE_ROW - 22), f"podium base  obs {PODIUM_BASE_ROW:.0f}  pred {p['base_row']:.0f}",
           fill=(255, 220, 0))
    for x in PHOTO_WIDTH_PX:
        d.line([(x, 0), (x, H)], fill=(255, 220, 0), width=2)
    for x in (p["x_lo"], p["x_hi"]):
        d.line([(x, 0), (x, H)], fill=(60, 255, 60), width=1)
    d.rectangle([0, 0, 980, 60], fill=(0, 0, 0))
    d.text((8, 6), f"QA-04-11  ref 062 fit: az {NEAR_FACE_AZ:.0f} (yaw ~1.7 deg)  D {D:.1f} m  lens {lens:.1f} mm  "
                   f"pitch +{pitch:.1f} deg  eye {h:.2f} m", fill=(255, 255, 255))
    d.text((8, 24), "red = analytic attic ring + drum + dome silhouette;  cyan = rostra lobes + platform;",
           fill=(255, 255, 255))
    d.text((8, 40), "yellow = measured landmark row / width;  green = the fitted model's prediction",
           fill=(255, 255, 255))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    im.save(out)
    return out


def sheet(overlay_png, render_png, out):
    """Stack the annotated overlay over a [model render at the fitted station | ref 062] pair.
    The render comes from
        blender -b assets/architecture.blend --python scripts/arch_inspect.py -- \
            --cam -73.2,55.2,1.55 --target 0,0,23.5 --lens 42.4 --lod 1 --res 1280x914
    i.e. exactly the fitted station, so the two bottom panels are the same camera on the same building."""
    from PIL import Image, ImageDraw
    top = Image.open(overlay_png).convert("RGB")
    ren = Image.open(render_png).convert("RGB")
    pho = Image.open(PHOTO).convert("RGB")
    Wt = top.width
    half = Wt // 2
    ren = ren.resize((half, int(ren.height * half / ren.width)))
    pho = pho.resize((half, int(pho.height * half / pho.width)))
    hb = max(ren.height, pho.height)
    im = Image.new("RGB", (Wt, top.height + hb + 34), (16, 16, 16))
    im.paste(top, (0, 0))
    im.paste(ren, (0, top.height + 34))
    im.paste(pho, (half, top.height + 34))
    d = ImageDraw.Draw(im)
    d.text((10, top.height + 10), "ARCH at the fitted station: (-73.2, 55.2, 1.55) -> (0, 0, 23.5), 42.4 mm, LOD1",
           fill=(255, 255, 255))
    d.text((half + 10, top.height + 10), "ref 062  (reference/photos/raw/ref_062_*.jpg)", fill=(255, 255, 255))
    im.save(out)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--eye", type=float, default=1.55)
    ap.add_argument("--overlay")
    ap.add_argument("--render", help="model render at the fitted station; appended as a second row")
    a = ap.parse_args()
    q, c = fit(a.eye)
    D, lens, pitch = q
    print(f"# ref 062 fit  az {NEAR_FACE_AZ:.1f} (face-on)  eye {a.eye:.2f} m")
    print(f"  D = {D:.1f} m   lens = {lens:.1f} mm   pitch = +{pitch:.2f} deg   chi2 = {c:.2f} (4 rows, 3 dof used)")
    x, y = P.az_to_xy(NEAR_FACE_AZ, D)
    print(f"  station (x, y, z) = ({x:.1f}, {y:.1f}, {a.eye:.2f}),  target (0, 0, "
          f"{a.eye + D * math.tan(math.radians(pitch)):.1f})")
    pr = rows(D, lens, pitch, a.eye)
    print("  landmark                     z      obs     fit    d(px)   d(%H)")
    for (lab, z, r, obs, sig), py in zip(LANDMARKS, pr):
        print(f"  {lab:26s} {z:6.2f} {obs:7.1f} {py:7.1f} {py - obs:7.1f} {100*(py-obs)/RES[1]:7.2f}")
    p = predictions(D, lens, pitch, a.eye)
    ow = PHOTO_WIDTH_PX[1] - PHOTO_WIDTH_PX[0]
    print(f"  PREDICTED podium base row {p['base_row']:.0f} vs measured {PODIUM_BASE_ROW:.0f} "
          f"({(p['base_row']-PODIUM_BASE_ROW)/RES[1]*100:+.2f} %H; base at {p['base_row']/RES[1]:.3f} of frame "
          f"vs photo {PODIUM_BASE_ROW/RES[1]:.3f})")
    print(f"  PREDICTED podium width {p['width']:.0f} px (x {p['x_lo']:.0f}..{p['x_hi']:.0f}) vs measured "
          f"{ow:.0f} px (x {PHOTO_WIDTH_PX[0]:.0f}..{PHOTO_WIDTH_PX[1]:.0f})  -> {100*(p['width']-ow)/ow:+.1f} % "
          f"(lower bound: the planter sweeps are not in the model's podium set)")
    aw = PHOTO_ATTIC_PX[1] - PHOTO_ATTIC_PX[0]
    print(f"  PREDICTED attic-ring width {p['attic_width']:.0f} px (x {p['a_lo']:.0f}..{p['a_hi']:.0f}) vs measured "
          f"{aw:.0f} px (x {PHOTO_ATTIC_PX[0]:.0f}..{PHOTO_ATTIC_PX[1]:.0f})  -> {100*(p['attic_width']-aw)/aw:+.1f} %")
    yaw = math.degrees(math.atan(((PHOTO_ATTIC_PX[0] + PHOTO_ATTIC_PX[1]) / 2 - RES[0] / 2)
                                 / (RES[0] * lens / 36.0)))
    print(f"  photo's building centre is {(PHOTO_ATTIC_PX[0]+PHOTO_ATTIC_PX[1])/2 - RES[0]/2:+.0f} px off frame "
          f"centre -> camera yaw {yaw:+.1f} deg, i.e. az {NEAR_FACE_AZ - yaw:.1f} rather than the face normal 37")
    print(f"  dome apex above the NEAR face attic cornice: {p['clear_near_face']:+.1f} px "
          f"({p['clear_near_face']/p['width']*100:+.1f} % of the on-screen width)")
    print(f"  dome apex above the HIGHEST attic point (near corner block): {p['clear_attic_ring']:+.1f} px")
    ct = clearance_threshold(a.eye)
    print("\n# the lens- and tilt-independent constraint (why no close station can reproduce ref 062)")
    print(f"  ref 062 shows the dome cap ABOVE the near face's attic cornice. With the current stack "
          f"(apex {P.DOME_APEX_Z + 0.6:.1f}, attic {P.ATTIC_Z1:.1f} at r {P.WALL_APOTHEM + P.ATTIC_CORNICE_D:.1f}) that needs")
    print(f"      D > {ct['d_min']:.1f} m  -- independent of lens, tilt, framing and azimuth.")
    for D in (45.0, 50.0):
        print(f"  to show it from D = {D:.0f} m instead you would need the apex at "
              f"{ct[f'apex_needed_at_{D:.0f}']:.1f} m (now {P.DOME_APEX_Z + 0.6:.1f}) OR the attic top at "
              f"{ct[f'attic_needed_at_{D:.0f}']:.1f} m (now {P.ATTIC_Z1:.1f})")
    print("  The podium/rostra radius does not enter this inequality at all.")

    lc = land_check()
    if lc:
        dists, rr = lc
        print("\n# is the fitted station reachable? OSM lagoon rings, reference/plans/site_local.json")
        print("  az \\ D  " + " ".join(f"{d:>6.0f}" for d in dists))
        for az, cells in rr:
            print(f"  {az:5.0f}  " + " ".join(f"{c:>6s}" for c in cells))

    print("\n# sensitivity to the assumed eye height")
    for h in (1.30, 1.45, 1.55, 1.70, 1.85):
        qq, cc = fit(h)
        pp = predictions(*qq, h)
        print(f"  eye {h:.2f} -> D {qq[0]:6.1f} m  lens {qq[1]:5.1f} mm  pitch {qq[2]:5.2f}  chi2 {cc:6.2f}  "
              f"base row {pp['base_row']:6.0f}  width {pp['width']:5.0f} px")
    if a.overlay:
        print("\nwrote", draw_overlay(q, a.eye, a.overlay))
        if a.render:
            print("wrote", sheet(a.overlay, a.render, a.overlay))
