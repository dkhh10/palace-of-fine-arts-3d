"""Round-12 lighting measurement. Plain python3 + PIL/numpy, no Blender.

Round 12's blockers are stated on boxes QA changed in round 05, so this script re-states them rather than reusing
round 11's:

  QA-05-1  cam03 is now a RATIO inside its own frame -- near shaft (0 150 420 720) over the sunlit far rotunda
           (560 0 880 320) in the same frame, window 0.30-0.70, plus shade hue 25-42 and sat <= 0.55. The absolute
           ref-128 number (69.7) is retired: ref 128 is a midday photo and our sun is 7.4 deg up.
           On the hero the same defect is the shaded attic box (1110 225 1150 260): hue 29.5 +- 8, sat <= 0.55.
  QA-05-3  cam04 coffer / own sky 0.35-0.55 AND the robust dark-quarter / light-quarter statistic >= 0.20
           (mat_r6_measure's, reproduced here so one command prints both owners' numbers on the same file).
  QA-05-9  Eevee - Cycles gap on BOTH soffits <= 0.15.

    python3 scripts/light_r12_measure.py --cam03 a.png b.png --hero hero.png --cam04 c.png
    python3 scripts/light_r12_measure.py --cam04gap eevee.png cycles.png
    python3 scripts/light_r12_measure.py --ref                     # ref 169 row through QA's aligned panel
"""
import sys, os, json, argparse
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import light_r10_measure as m10
import light_r11_measure as m11

ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------- cam03, QA round-05 (d), pixels at 1280x720
CAM03_BOXES = {
    "near_shaft":     (0, 150, 420, 720),
    "sunlit_rotunda": (560, 0, 880, 320),
    "ground":         (420, 560, 900, 720),
}
CAM03_RES = (1280, 720)
# ref 169's golden-hour anchor for open shade over sunlit stone, QA round-05 (d)
CAM03_ANCHOR = 0.607
CAM03_WINDOW = (0.30, 0.70)

# hero shade, QA-05-1 second half
HERO_SHADE_TARGET = dict(hue=29.5, hue_tol=8.0, sat_max=0.55, lum=115.0, lum_tol=0.15)
# hero sunlit attic, priority 2 of the round-12 dispatch (relaxed from round 10's 0.55 / 121)
HERO_SUNLIT_TARGET = dict(sat_min=0.50, rb_min=110.0, lum=(178.2, 201.0))


def measure_cam03(path):
    im = Image.open(path).convert("RGB")
    if im.size != CAM03_RES:
        im = im.resize(CAM03_RES, Image.LANCZOS)
    a = np.asarray(im, dtype=np.float64)
    out = {}
    for name, (x0, y0, x1, y1) in CAM03_BOXES.items():
        sub = a[y0:y1, x0:x1]
        s = m10.stats(sub)
        s["std"] = float(sub.reshape(-1, 3).mean(axis=1).std())
        out[name] = s
    sunlit = max(1e-6, out["sunlit_rotunda"]["lum"])
    out["shade_ratio"] = out["near_shaft"]["lum"] / sunlit
    out["ground_ratio"] = out["ground"]["lum"] / sunlit
    return out


def report_cam03(path, m, label=""):
    print(f"\n=== cam03 {label or Path(path).name} ===")
    for k in CAM03_BOXES:
        v = m[k]
        print(f"  {k:15s} sRGB {int(round(v['rgb'][0])):3d},{int(round(v['rgb'][1])):3d},{int(round(v['rgb'][2])):3d}"
              f"  lum {v['lum']:6.2f}  hue {v['hue']:5.1f}  sat {v['sat']:.3f}  std {v['std']:5.1f}")
    lo, hi = CAM03_WINDOW
    ok = lo <= m["shade_ratio"] <= hi
    ns = m["near_shaft"]
    hue_ok = 25.0 <= ns["hue"] <= 42.0
    sat_ok = ns["sat"] <= 0.55
    print(f"  >> QA-05-1 shade/sunlit {m['shade_ratio']:.3f}  [{lo}-{hi}] {'PASS' if ok else 'FAIL'}"
          f"   (ref 169 anchor {CAM03_ANCHOR})   ground/sunlit {m['ground_ratio']:.3f}")
    print(f"  >> QA-05-1 shade hue {ns['hue']:.1f} [25-42] {'PASS' if hue_ok else 'FAIL'}"
          f"   sat {ns['sat']:.3f} [<=0.55] {'PASS' if sat_ok else 'FAIL'}")
    return m


# ------------------------------------------------------------------------------------------------------ hero
def report_hero(path, m, label=""):
    a, s = m["attic_sunlit"], m["attic_shaded"]
    t, u = HERO_SUNLIT_TARGET, HERO_SHADE_TARGET
    print(f"\n=== hero {label or Path(path).name} ===")
    for k in ("attic_sunlit", "attic_shaded", "entablature", "columns", "near_water_sky", "water_refl"):
        v = m[k]
        r = m10.REF.get(k)
        rs = (f"   ref {r['lum']:6.1f} {r['hue']:5.1f} {r['sat']:.3f}" if r else "")
        print(f"  {k:16s} lum {v['lum']:6.1f} hue {v['hue']:6.1f} sat {v['sat']:6.3f} R-B {v['rb']:7.1f}{rs}")
    print(f"  >> p2 sunlit attic sat {a['sat']:.3f} (>={t['sat_min']}) R-B {a['rb']:.1f} (>={t['rb_min']}) "
          f"lum {a['lum']:.1f} ({t['lum'][0]}-{t['lum'][1]}) "
          f"{'PASS' if a['sat'] >= t['sat_min'] and a['rb'] >= t['rb_min'] and t['lum'][0] <= a['lum'] <= t['lum'][1] else 'FAIL'}")
    dh = abs(s["hue"] - u["hue"])
    print(f"  >> p1 shaded attic hue {s['hue']:.1f} (29.5+-{u['hue_tol']:.0f}, off by {dh:.1f}) "
          f"sat {s['sat']:.3f} (<={u['sat_max']}) lum {s['lum']:.1f} (115+-15%) "
          f"{'PASS' if dh <= u['hue_tol'] and s['sat'] <= u['sat_max'] else 'FAIL'}")
    print(f"  >> p3 columns {m['columns']['lum']:.1f} = {m['columns']['lum']/95.8:.2f}x ref (<=1.3x) "
          f"{'PASS' if m['columns']['lum'] <= 1.3 * 95.8 else 'FAIL'}")
    print(f"  >> p4 sky_top {m['sky_top']['lum']:.1f} (149-182) sky_left/top {m['sky_ratio']:.3f} (1.05-1.29); "
          f"near water sat {m['near_water_sky']['sat']:.3f} (0.22-0.32); water_refl {m['water_refl']['lum']:.1f}")
    print(f"  >> shade/sunlit on the hero {s['lum']/max(1e-6, a['lum']):.3f} (ref 169 {CAM03_ANCHOR})")


# ------------------------------------------------------------------------------------------------------ cam04
def quarter_ratio(path):
    """mat_r6_measure's robust coffer statistic, on its own default box (28-72 % x, 20-80 % y of the frame)."""
    a = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64)
    g = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]   # mat_r6_measure.lum, exactly
    H, W = g.shape
    v = g[int(H * 0.20):int(H * 0.80), int(W * 0.28):int(W * 0.72)].ravel()
    v = v[v > 1.0]
    if v.size < 100:
        return dict(dark=0.0, light=0.0, ratio=0.0, std=0.0, mean=0.0)
    q1, q3 = np.percentile(v, 25), np.percentile(v, 75)
    dark, light = float(v[v <= q1].mean()), float(v[v >= q3].mean())
    return dict(dark=dark, light=light, ratio=dark / max(1e-6, light), std=float(v.std()), mean=float(v.mean()))


def report_cam04(path, m, q, label=""):
    print(f"\n=== cam04 {label or Path(path).name} ===")
    print(f"  own_sky {m['own_sky']['lum']:6.1f}   soffit W {m['soffit_w']['lum']:6.1f} E {m['soffit_e']['lum']:6.1f}"
          f"   coffer {m['coffer']['lum']:6.1f}")
    print(f"  >> soffit/sky  W {m['r_soffit_w']:.3f}  E {m['r_soffit_e']:.3f}  mean {m['r_soffit']:.3f} (ref 083 0.405)")
    print(f"  >> QA-05-3 coffer/sky {m['r_coffer']:.3f} [0.35-0.55] {'PASS' if 0.35 <= m['r_coffer'] <= 0.55 else 'FAIL'}"
          f"   (ref 083 0.437)")
    print(f"  >> QA-05-3 dark/light quarter {q['ratio']:.3f} [>=0.20] {'PASS' if q['ratio'] >= 0.20 else 'FAIL'}"
          f"   (dark {q['dark']:.1f} light {q['light']:.1f}; ref 083 0.265)   field std {q['std']:.1f} (ref 31.2)")


def report_gap(eev, cyc):
    a, b = m11.measure_cam04(eev), m11.measure_cam04(cyc)
    print(f"\n=== QA-05-9 Eevee vs Cycles on cam04 ===")
    for k, lbl in (("r_soffit_w", "soffit W"), ("r_soffit_e", "soffit E"), ("r_coffer", "coffer")):
        d = abs(a[k] - b[k])
        print(f"  {lbl:9s} eevee {a[k]:.3f}  cycles {b[k]:.3f}  gap {d:.3f}  {'PASS' if d <= 0.15 else 'FAIL'}")
    return a, b


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cam03", nargs="*", default=[])
    ap.add_argument("--hero", nargs="*", default=[])
    ap.add_argument("--cam04", nargs="*", default=[])
    ap.add_argument("--cam04gap", nargs=2, default=None, metavar=("EEVEE", "CYCLES"))
    ap.add_argument("--ref", action="store_true")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    allm = {}
    if a.ref:
        m = m10.measure(m10.ALIGNED, panel=1)
        report_hero(str(m10.ALIGNED), m, "REF 169 warped into the render frame (panel 1)")
        allm["ref169"] = m
    for p in a.cam03:
        m = measure_cam03(p)
        report_cam03(p, m)
        allm["cam03:" + Path(p).name] = m
    for p in a.hero:
        m = m10.measure(p)
        report_hero(p, m)
        allm["hero:" + Path(p).name] = m
    for p in a.cam04:
        m = m11.measure_cam04(p)
        q = quarter_ratio(p)
        report_cam04(p, m, q)
        m = dict(m, quarter=q)
        allm["cam04:" + Path(p).name] = m
    if a.cam04gap:
        e, c = report_gap(*a.cam04gap)
        allm["gap"] = dict(eevee=e, cycles=c)
    if a.json:
        Path(a.json).write_text(json.dumps(allm, indent=1, default=float))
