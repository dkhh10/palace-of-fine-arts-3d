"""Round-19 CPU predictor: what the DIFFUSE sky tint actually delivers to a given surface normal.

No Blender, no render.  It evaluates exactly the node graph `light_calibrate.make_sky_world` builds for the
diffuse branch -- and nothing else -- as a cosine-weighted hemisphere integral about a surface normal:

    g_c(d) = [1 + (tint_c      - 1) * wa(d)^pa * wh(d)^ph]        # SKY_DIFFUSE_TINT, anti-sun x horizon weighted
           * [1 + (sunside_c   - 1) * ws(d)^ps]                    # SKY_DIFFUSE_TINT_SUNSIDE, sun-side weighted
    wa(d) = clamp(0.5 - 0.5 * (d . s))      ws(d) = clamp(0.5 + 0.5 * (d . s)) = 1 - wa      wh(d) = clamp(1 - |d.z|)

(`Incoming` in a world shader is -d, which is why the node's `0.5 + 0.5 * Incoming.s` is `0.5 - 0.5 * d.s` here.)

    G_c(n) = E_cos[ L(d) g_c(d) ] / E_cos[ L(d) ]

is then the per-channel gain the tint puts on the light a wall of normal n collects DIRECTLY from the sky.  It is
a RANKING tool, not a prediction of the render: it has no occlusion and no interreflection, and on these boxes
most of the light has bounced off warm stone first (docs/lighting_notes 21.4).  What it is good for is the one
thing the round needs -- the SEPARATION between two normals, which is pure geometry -- and solving for the b that
holds a chosen normal's blue when an exponent moves.

    python3 scripts/light_r19_predict.py                      # the shipped rig + the candidate table
    python3 scripts/light_r19_predict.py --n-az 37 --n-el 0   # one normal
"""
import math, argparse

AZ, EL = 118.5, 7.4          # light_build.FALLBACK_SUN["morning"]; build() re-solves it to the same values

# shipped (light_build.py, round 16 + the lead's 2026-09-10 shade-fill off)
BASE = dict(tint=(1.0, 0.65, 70.0), pa=3.0, ph=6.0, sunside=(1.0, 1.0, 0.0), ps=3.0)


def sun_dir(az_deg=AZ, el_deg=EL):
    """common.sun_direction: azimuth clockwise from north, north = -X, east = +Y."""
    az, el = math.radians(az_deg), math.radians(el_deg)
    return (-math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))


def normal(az_deg, el_deg=0.0):
    return sun_dir(az_deg, el_deg)          # same convention: an azimuth clockwise from north


def hemisphere(n, m=20000):
    """Cosine-weighted directions about n, as a Fibonacci disc lifted to the hemisphere (equal weights)."""
    nx, ny, nz = n
    # an orthonormal basis about n
    ax = (0.0, 0.0, 1.0) if abs(nz) < 0.9 else (1.0, 0.0, 0.0)
    t = (ny * ax[2] - nz * ax[1], nz * ax[0] - nx * ax[2], nx * ax[1] - ny * ax[0])
    tl = math.sqrt(sum(c * c for c in t)); t = tuple(c / tl for c in t)
    b = (ny * t[2] - nz * t[1], nz * t[0] - nx * t[2], nx * t[1] - ny * t[0])
    ga = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(m):
        r = math.sqrt((i + 0.5) / m)                 # cosine-weighted: r = sqrt(u)
        th = i * ga
        u, v = r * math.cos(th), r * math.sin(th)
        w = math.sqrt(max(0.0, 1.0 - u * u - v * v))
        yield (u * t[0] + v * b[0] + w * nx, u * t[1] + v * b[1] + w * ny, u * t[2] + v * b[2] + w * nz)


def sky_L(d, horizon_gain=3.0):
    """A crude radiance weight: the MULTIPLE_SCATTERING sky at a 7 deg sun is ~5:1 horizon:zenith
    (light_build.SKY comment).  Only the SHAPE matters here, and only through E_cos[L g] / E_cos[L]."""
    return 1.0 + (horizon_gain - 1.0) * max(0.0, 1.0 - abs(d[2])) ** 3


def gains(n, tint, pa, ph, sunside, ps, s=None, m=20000, horizon_gain=3.0):
    s = s or sun_dir()
    num = [0.0, 0.0, 0.0]
    den = 0.0
    for d in hemisphere(n, m):
        if d[2] <= 0.0:            # below the horizon: ground, not sky.  Excluded from both sums.
            continue
        ds = d[0] * s[0] + d[1] * s[1] + d[2] * s[2]
        wa = min(1.0, max(0.0, 0.5 - 0.5 * ds))
        wh = min(1.0, max(0.0, 1.0 - abs(d[2])))
        ws = min(1.0, max(0.0, 0.5 + 0.5 * ds))
        fa = (wa ** pa) * (wh ** ph)
        fs = ws ** ps
        L = sky_L(d, horizon_gain)
        den += L
        for c in range(3):
            num[c] += L * (1.0 + (tint[c] - 1.0) * fa) * (1.0 + (sunside[c] - 1.0) * fs)
    return tuple(x / max(1e-9, den) for x in num), den


def solve_b(n_hold, target_gb, pa, ph, sunside, ps, lo=1.0, hi=20000.0, m=20000):
    """The b that puts `target_gb` of blue gain on the HOLD normal at this exponent (G_b is linear in b)."""
    g1, _ = gains(n_hold, (1.0, 0.65, 1.0), pa, ph, sunside, ps, m=m)
    g2, _ = gains(n_hold, (1.0, 0.65, 2.0), pa, ph, sunside, ps, m=m)
    slope = g2[2] - g1[2]                       # dG_b / db
    if slope <= 1e-12:
        return float("inf")
    return 1.0 + (target_gb - g1[2]) / slope


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-az", type=float, default=None)
    ap.add_argument("--n-el", type=float, default=0.0)
    ap.add_argument("--hold-az", type=float, default=0.0, help="hero shaded attic normal azimuth (north = 0)")
    ap.add_argument("--fix-az", type=float, default=37.0, help="cam02 camera-facing face normal azimuth")
    ap.add_argument("--samples", type=int, default=20000)
    a = ap.parse_args()
    s = sun_dir()
    print(f"sun az {AZ} el {EL} -> direction ({s[0]:+.4f}, {s[1]:+.4f}, {s[2]:+.4f})")
    if a.n_az is not None:
        n = normal(a.n_az, a.n_el)
        g, _ = gains(n, m=a.samples, **BASE)
        print(f"n az {a.n_az} el {a.n_el}: n.sun {sum(n[i]*s[i] for i in range(3)):+.4f}  G {g[0]:.3f} {g[1]:.3f} {g[2]:.3f}")
        raise SystemExit

    nh, nf = normal(a.hold_az), normal(a.fix_az)
    print(f"HOLD  (hero shaded attic) n az {a.hold_az:5.1f}  n.sun {sum(nh[i]*s[i] for i in range(3)):+.4f}")
    print(f"FIX   (cam02 NNE face)    n az {a.fix_az:5.1f}  n.sun {sum(nf[i]*s[i] for i in range(3)):+.4f}\n")
    gh0, _ = gains(nh, m=a.samples, **BASE)
    gf0, _ = gains(nf, m=a.samples, **BASE)
    print(f"{'candidate':34s} {'b':>8s} {'hero G_rgb':>22s} {'cam02 G_rgb':>22s} {'cam02 B/R':>9s} {'vs base':>8s}")
    print(f"{'BASE pa 3 ps 3 b 70':34s} {70.0:8.1f} "
          f"{gh0[0]:6.3f}{gh0[1]:7.3f}{gh0[2]:8.3f} {gf0[0]:6.3f}{gf0[1]:7.3f}{gf0[2]:8.3f} "
          f"{gf0[2]/gf0[0]:9.3f} {1.0:8.2f}")
    for pa in (4.0, 6.0, 8.0, 10.0):
        for ps in (3.0, 1.5):
            ss = BASE["sunside"]
            b = solve_b(nh, gh0[2], pa, BASE["ph"], ss, ps, m=a.samples)
            if not math.isfinite(b) or b > 1e5:
                print(f"{'pa %g ps %g' % (pa, ps):34s} {'--':>8s}  (cannot hold the hero at any b)")
                continue
            gh, _ = gains(nh, (1.0, 0.65, b), pa, BASE["ph"], ss, ps, m=a.samples)
            gf, _ = gains(nf, (1.0, 0.65, b), pa, BASE["ph"], ss, ps, m=a.samples)
            print(f"{'pa %g ps %g' % (pa, ps):34s} {b:8.1f} "
                  f"{gh[0]:6.3f}{gh[1]:7.3f}{gh[2]:8.3f} {gf[0]:6.3f}{gf[1]:7.3f}{gf[2]:8.3f} "
                  f"{gf[2]/gf[0]:9.3f} {(gf[2]-1)/max(1e-9, gf0[2]-1):8.2f}")
