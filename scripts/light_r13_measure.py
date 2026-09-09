"""Round-13 lighting measurement. Plain python3 + PIL/numpy, no Blender.

Three modes, one per brief item:

  --herogap EEVEE CYCLES   item 1. The Eevee preview must carry the round-12 shade: shaded attic within 6 deg of
                           hue, 0.1 of saturation and 15 % of luminance of the Cycles frame, while the sky and the
                           lagoon stay where they already are (they matched to 0.2 lum in round 12 and must not move).
  --cam06 A B ...          item 2. QA-05-8 / ENV's hand-off, measured on ENVIRONMENT'S OWN crop and statistic:
                           rows 0-220 of the 1280-wide frame, mean / std, and env_r7_measure.count_lines on the
                           far-field band (rows 0-110), which is the number environment reports.
  --hero A B ...           item 3. The hero row plus the two wing bands and the shore band, so a change to the sky
                           term can be read against the sunlit windows it is not allowed to break.

    python3 scripts/light_r13_measure.py --herogap eevee.png cycles.png
    python3 scripts/light_r13_measure.py --cam06 nocomp.png ship.png cand.png
    python3 scripts/light_r13_measure.py --hero base.png db3.5.png
"""
import sys, os, json, argparse
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import light_r10_measure as m10
import light_r12_measure as m12

ROOT = Path(__file__).resolve().parents[1]

# item 1 windows (the brief): the Eevee preview against the Cycles frame of the same rig
GAP = dict(hue=6.0, sat=0.10, lum=0.15)
GAP_KEYS = ("attic_shaded", "attic_sunlit", "entablature", "columns",
            "sky_top", "sky_left", "near_water_sky", "lagoon_flank", "water_refl")
HOLD = ("sky_top", "sky_left")     # must stay identical to Cycles (the lagoon boxes are screen-trace vs path-trace: reported, not gated; r13 review 3)

# item 3: the shore band is ENVIRONMENT'S box (env_r7_measure.measure, hero (700, 600, 1200, 740)); ref 115.6
SHORE_BOX = (700, 600, 1200, 740)
SHORE_REF = 115.6


def _hero(path):
    m = m10.measure(path)
    a = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64)
    if a.shape[1] != 1920 or a.shape[0] != 1080:
        a = np.asarray(Image.fromarray(a.astype(np.uint8)).resize((1920, 1080), Image.LANCZOS), dtype=np.float64)
    x0, y0, x1, y1 = SHORE_BOX
    m["shore_band"] = m10.stats(a[y0:y1, x0:x1])
    m["wings"] = m12.measure_wings(path)
    return m


def report_gap(eev, cyc):
    e, c = _hero(eev), _hero(cyc)
    print(f"\n=== item 1: Eevee ({Path(eev).name}) vs Cycles ({Path(cyc).name}), same rig, 1920x1080 ===")
    print(f"  {'box':16s} {'eevee lum/hue/sat':>26s} {'cycles lum/hue/sat':>26s}   d_lum   d_hue  d_sat  verdict")
    ok = True
    for k in GAP_KEYS:
        a, b = e[k], c[k]
        dl = (a["lum"] - b["lum"]) / max(1e-6, b["lum"])
        dh, ds = a["hue"] - b["hue"], a["sat"] - b["sat"]
        passed = abs(dh) <= GAP["hue"] and abs(ds) <= GAP["sat"] and abs(dl) <= GAP["lum"]
        if k == "attic_shaded" or k in HOLD:
            ok = ok and passed
        print(f"  {k:16s} {a['lum']:8.1f} {a['hue']:7.1f} {a['sat']:8.3f} "
              f"{b['lum']:9.1f} {b['hue']:7.1f} {b['sat']:8.3f}   {100*dl:+6.1f}% {dh:+7.1f} {ds:+6.3f}  "
              f"{'PASS' if passed else 'FAIL'}{'  (must hold)' if k in HOLD else ''}")
    s = e["attic_shaded"]
    print(f"  >> item 1 shaded attic: Eevee {s['lum']:.1f} / {s['hue']:.1f} / {s['sat']:.3f} vs Cycles "
          f"{c['attic_shaded']['lum']:.1f} / {c['attic_shaded']['hue']:.1f} / {c['attic_shaded']['sat']:.3f} "
          f"-- {'PASS' if ok else 'FAIL'}")
    return dict(eevee=e, cycles=c)


def report_cam06(paths):
    """Environment's own crop and statistic (env_r7_measure), so lighting's number is comparable with theirs."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import env_r7_measure as env                    # environment's tool, READ-ONLY: we call it, we never edit it
    print(f"\n=== item 2: cam06 horizon crop (env_r7_measure: rows 0-220 of the 1280-wide frame) ===")
    print(f"  {'frame':44s} {'mean':>7s} {'std':>7s}   far-field lines (rows 0-110)")
    out = {}
    for p in paths:
        L = env.load(p, 1280)
        c = L[0:220, 0:1280]
        kf, detf = env.count_lines(L[0:110, 0:1280])
        k, det = env.count_lines(c)
        out[Path(p).name] = dict(mean=float(c.mean()), std=float(c.std()), lines_far=kf, lines_all=k)
        print(f"  {Path(p).name[:44]:44s} {c.mean():7.1f} {c.std():7.1f}   {kf} far / {k} whole crop")
    return out


def report_hero(paths):
    print(f"\n=== item 3: hero row, wing bands and the shore band ===")
    out = {}
    for p in paths:
        m = _hero(p)
        a, s = m["attic_sunlit"], m["attic_shaded"]
        w = m["wings"]
        print(f"\n  -- {Path(p).name}")
        print(f"     sunlit attic  lum {a['lum']:6.1f} (178.2-201.0)  sat {a['sat']:.3f} (>=0.50)  "
              f"R-B {a['rb']:6.1f} (>=110)  "
              f"{'PASS' if 178.2 <= a['lum'] <= 201.0 and a['sat'] >= 0.50 and a['rb'] >= 110.0 else 'FAIL'}")
        print(f"     shaded attic  lum {s['lum']:6.1f}  hue {s['hue']:5.1f} (29.5+-6)  sat {s['sat']:.3f} (<=0.55)")
        print(f"     south wing    lum {w['south_wing']['lum']:6.1f}  (>=82 raw / >=103 aligned; ref 109.5)")
        print(f"     north wing    lum {w['north_wing']['lum']:6.1f}  (0.9-1.1 of 146.5 -> "
              f"{w['north_wing']['lum']/146.5:.2f}x)")
        print(f"     shore band    lum {m['shore_band']['lum']:6.1f}  (ref {SHORE_REF})")
        print(f"     columns {m['columns']['lum']:6.1f} ({m['columns']['lum']/m10.REF['columns']['lum']:.2f}x)   "
              f"near water sat {m['near_water_sky']['sat']:.3f} (0.22-0.32)   "
              f"sky_top {m['sky_top']['lum']:.1f} (149-182)  sky_left/top {m['sky_ratio']:.3f}")
        out[Path(p).name] = m
    return out


LAGOON = (0, 700, 1920, 1080)      # everything below the shoreline in the hero frame


def report_glint(paths):
    """Review carry 5: SUN_BLUE_MULT is 0.00, i.e. LIGHT_sun is a literally blue-free illuminant, which shows on any
    pure-sun specular. The glint statistic is the mean of the brightest 0.2 % of the lagoon (y 700-1080), which is
    where the sun's own specular lives, reported with its R-B so a blue-free highlight is visible as a number."""
    print(f"\n=== carry 5: sun glint on the lagoon (brightest 0.2 % of y 700-1080) ===")
    print(f"  {'frame':40s} {'glint lum':>10s} {'R-B':>8s} {'hue':>7s} | shaded attic hue / sunlit R-B / sat")
    for p in paths:
        a = np.asarray(Image.open(p).convert("RGB"), dtype=np.float64)
        if a.shape[1] != 1920:
            a = np.asarray(Image.fromarray(a.astype(np.uint8)).resize((1920, 1080), Image.LANCZOS), dtype=np.float64)
        x0, y0, x1, y1 = LAGOON
        sub = a[y0:y1, x0:x1].reshape(-1, 3)
        g = 0.2126 * sub[:, 0] + 0.7152 * sub[:, 1] + 0.0722 * sub[:, 2]
        thr = np.percentile(g, 99.8)
        st = m10.stats(sub[g >= thr])
        m = m10.measure(p)
        print(f"  {Path(p).name[:40]:40s} {st['lum']:10.1f} {st['rb']:8.1f} {st['hue']:7.1f} | "
              f"{m['attic_shaded']['hue']:.1f} (29.5+-6) / {m['attic_sunlit']['rb']:.1f} (>=110) / "
              f"{m['attic_sunlit']['sat']:.3f} (>=0.50)")


def report_noise(paths, box=("attic_shaded",)):
    """Review carry 6: the Cycles world importance map cannot see the diffuse-only multipliers, so the shade may be
    under-sampled. Noise is measured as the standard deviation of the box AFTER removing its own linear gradient,
    which leaves the sampling noise and not the shading."""
    print(f"\n=== carry 6: shade noise (per-box std after removing a linear ramp) ===")
    for p in paths:
        a = np.asarray(Image.open(p).convert("RGB"), dtype=np.float64)
        if a.shape[1] != 1920:
            a = np.asarray(Image.fromarray(a.astype(np.uint8)).resize((1920, 1080), Image.LANCZOS), dtype=np.float64)
        row = [Path(p).name[:44]]
        for k in box:
            x0, y0, x1, y1 = m10.BOXES[k]
            g = a[y0:y1, x0:x1].mean(axis=2)
            yy, xx = np.mgrid[0:g.shape[0], 0:g.shape[1]]
            A = np.stack([np.ones(g.size), xx.ravel(), yy.ravel()], axis=1)
            coef, *_ = np.linalg.lstsq(A, g.ravel(), rcond=None)
            resid = g.ravel() - A @ coef
            row.append(f"{k} mean {g.mean():.1f} noise {resid.std():.2f}")
        print("  " + "  ".join(row))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--herogap", nargs=2, default=None, metavar=("EEVEE", "CYCLES"))
    ap.add_argument("--cam06", nargs="*", default=[])
    ap.add_argument("--hero", nargs="*", default=[])
    ap.add_argument("--noise", nargs="*", default=[])
    ap.add_argument("--glint", nargs="*", default=[])
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    allm = {}
    if a.herogap:
        allm["gap"] = report_gap(*a.herogap)
    if a.cam06:
        allm["cam06"] = report_cam06(a.cam06)
    if a.hero:
        allm["hero"] = report_hero(a.hero)
    if a.noise:
        report_noise(a.noise)
    if a.glint:
        report_glint(a.glint)
    if a.json:
        Path(a.json).write_text(json.dumps(allm, indent=1, default=float))
