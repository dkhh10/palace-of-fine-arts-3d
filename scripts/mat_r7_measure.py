"""Round-7 materials acceptance tests (plain python + PIL/numpy, no Blender).

    python3 scripts/mat_r7_measure.py hero  <hero.png> [--panel N] [--label X]
    python3 scripts/mat_r7_measure.py shore <hero.png>
    python3 scripts/mat_r7_measure.py cam05 <cam05.png>
    python3 scripts/mat_r7_measure.py ref                     # the reference row, ref 169 warped into the frame

Everything is measured on QA's round-03/05 boxes in the 1920x1080 hero grid; any other resolution is bilinearly
resized to that grid first (lighting r12 verified on its own boxes that a 1280x720 render upsampled this way
reproduces the 1920x1080 numbers to ~1 lum, so iteration can be run at 2/3 scale).

New this round, because QA-05-2 is a *direction* defect and no previous tool measured direction:

  anisotropy   std(column means) / std(row means) over a box.  Vertical run-off makes the column profile vary and
               the row profile flat, so the photo scores 4.07 on the attic field and an isotropic blotch scores
               0.64.  Round-7 target >= 2.0 with the luminance std ratio held >= 0.60 of the photo's.
  runs         the same statistic read as a count: columns whose mean sits >= 15 lum below the box median (the
               run-off streaks), and the mean vertical run length of below-median pixels (a streak is long).
"""
import sys, os
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
HERO = (1920, 1080)
ALIGNED = ROOT / "renders" / "qa_comparisons" / "round05_cam01_aligned_vs_ref169.png"

BOXES = {                                        # QA round-03/05 hero boxes, 1920x1080
    "attic_sunlit":   (900, 222, 1020, 256),
    "attic_string":   (880, 214, 1040, 222),
    "entablature":    (900, 262, 1020, 296),
    "dome_cap":       (920, 95, 1000, 120),
    "attic_shaded":   (1110, 225, 1150, 260),
    "water_refl":     (900, 760, 1020, 840),
    "near_water_sky": (1150, 1000, 1450, 1050),
    "ripples":        (1100, 960, 1500, 1060),   # QA-05-4: the ripples must carry the stone's warm colour
    "lagoon_flank":   (100, 900, 400, 960),
    "shore_band":     (700, 600, 1200, 740),     # QA-05-10
}
COL_BOX = (680, 280, 1240, 470)
ANISO_BOXES = ["attic_sunlit", "entablature"]
# reference (ref 169 warped into the render frame, panel 1 of the round-05 aligned sheet) -- measured by `ref`
REF = {
    "attic_sunlit":   dict(lum=188.5, hue=40.5, sat=0.582, rb=133.2, std=44.50, aniso=4.07),
    "entablature":    dict(lum=146.3, hue=33.8, sat=0.585, rb=110.5, std=64.50, aniso=0.24),
    "attic_shaded":   dict(lum=120.2, hue=30.7, sat=0.457, rb=68.0),
    "water_refl":     dict(lum=168.9, hue=33.7, sat=0.339),
    "near_water_sky": dict(hue=189.9, sat=0.249),
    "ripples":        dict(rb=-26.0),
    "shore_band":     dict(lum=115.6, sat=0.663),
}
TESTS = {   # QA-05-2 / -4 / -10 acceptance windows as re-stated in the round-7 brief
    "attic_lum": (178.0, 201.0), "attic_sat": (0.53, 0.62), "attic_aniso": 2.0, "attic_std_ratio": 0.60,
    "entab_sat_max": 0.70, "entab_hue": (30.0, 40.0),
    "shaded_hue_tol": 6.0, "shaded_hue": 29.5, "shaded_sat_max": 0.55,
    "refl_sat_min": 0.25, "near_water_sat": (0.22, 0.32), "near_water_hue": (185.0, 200.0),
}


def load(path, panel=0, res=HERO):
    im = Image.open(path).convert("RGB")
    W, H = im.size
    n = max(1, round(W / res[0])) if W % res[0] == 0 and W // res[0] > 1 else 1
    if n > 1:
        im = im.crop((panel * (W // n), 0, (panel + 1) * (W // n), H))
    if im.size != res:
        im = im.resize(res, Image.BILINEAR)
    return np.asarray(im).astype(np.float64)


def lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def stats(c):
    m = c.reshape(-1, 3).mean(axis=0)
    r, g, b = m
    L = 0.2126 * r + 0.7152 * g + 0.0722 * b
    mx, mn = float(max(m)), float(min(m))
    d = mx - mn
    if d < 1e-6:
        h = 0.0
    elif mx == r:
        h = 60 * (((g - b) / d) % 6)
    elif mx == g:
        h = 60 * ((b - r) / d + 2)
    else:
        h = 60 * ((r - g) / d + 4)
    gg = lum(c)
    return dict(lum=float(L), hue=float(h), sat=float(d / mx if mx > 0 else 0.0), rb=float(r - b),
                std=float(gg.std()), rowsd=float(gg.mean(axis=1).std()), colsd=float(gg.mean(axis=0).std()),
                aniso=float(gg.mean(axis=0).std() / max(gg.mean(axis=1).std(), 1e-6)))


def box(a, name):
    x0, y0, x1, y1 = BOXES[name]
    return stats(a[y0:y1, x0:x1])


def columns(a):
    """QA's column mask: hue < 32 and sat > 0.30 inside the shaft box."""
    x0, y0, x1, y1 = COL_BOX
    c = a[y0:y1, x0:x1]
    mx = c.max(axis=-1); mn = c.min(axis=-1); d = mx - mn
    r, g, b = c[..., 0], c[..., 1], c[..., 2]
    dd = np.where(d == 0, 1, d)
    im = c.argmax(axis=-1)
    h = np.where(im == 0, 60 * (((g - b) / dd) % 6), np.where(im == 1, 60 * ((b - r) / dd + 2), 60 * ((r - g) / dd + 4)))
    s = np.where(mx > 0, d / np.where(mx == 0, 1, mx), 0.0)
    msk = (h < 32) & (s > 0.30)
    return stats(c[msk][None, :, :]) if msk.sum() > 50 else dict(lum=0, hue=0, sat=0, rb=0, std=0, aniso=0)


def runs_down(a, name):
    """How much of the box's darkening is organised into vertical runs: the fraction of columns whose mean is
    >= 15 lum below the box median (QA-04-3b's statistic) and the mean vertical run length of below-median pixels
    as a fraction of the box height (1.0 = a run the full height of the box, i.e. a streak)."""
    x0, y0, x1, y1 = BOXES[name]
    g = lum(a[y0:y1, x0:x1])
    cm = g.mean(axis=0)
    med = float(np.median(cm))
    below = g < np.median(g)
    lens = []
    for x in range(below.shape[1]):
        n = 0
        for y in range(below.shape[0]):
            if below[y, x]:
                n += 1
            elif n:
                lens.append(n); n = 0
        if n:
            lens.append(n)
    return dict(cols15=float((cm <= med - 15.0).mean()), runlen=float(np.mean(lens) / below.shape[0]) if lens else 0.0)


def report_hero(a, label=""):
    print(f"\n=== hero {label} ===")
    m = {k: box(a, k) for k in BOXES}
    m["columns"] = columns(a)
    for k in ("attic_sunlit", "attic_string", "entablature", "attic_shaded", "dome_cap", "columns",
              "water_refl", "near_water_sky", "ripples", "shore_band"):
        v = m[k]
        r = REF.get(k, {})
        rs = "".join(f"  ref_{kk} {r[kk]:.3f}" if isinstance(r[kk], float) and kk in ("sat",) else
                     f"  ref_{kk} {r[kk]:.1f}" for kk in r)
        print(f"  {k:15s} lum {v['lum']:6.1f} hue {v['hue']:6.1f} sat {v['sat']:.3f} R-B {v['rb']:7.1f} "
              f"std {v['std']:5.1f}{rs}")
    for k in ANISO_BOXES:
        v, r = m[k], REF[k]
        rr = runs_down(a, k)
        print(f"  ~ {k:13s} colsd {v['colsd']:5.2f} rowsd {v['rowsd']:5.2f} ANISO {v['aniso']:5.2f} (ref {r['aniso']:.2f})"
              f"   std ratio {v['std'] / r['std']:.2f}   cols<=-15 {rr['cols15'] * 100:4.1f} %   runlen {rr['runlen']:.2f}")
    a_, e_, s_, w_, n_ = m["attic_sunlit"], m["entablature"], m["attic_shaded"], m["water_refl"], m["near_water_sky"]
    T = TESTS
    ok = lambda c: "PASS" if c else "FAIL"
    print(f"  >> QA-05-2 attic lum {a_['lum']:.1f} {T['attic_lum']} {ok(T['attic_lum'][0] <= a_['lum'] <= T['attic_lum'][1])}"
          f" | sat {a_['sat']:.3f} {T['attic_sat']} {ok(T['attic_sat'][0] <= a_['sat'] <= T['attic_sat'][1])}"
          f" | aniso {a_['aniso']:.2f} (>=2.0) {ok(a_['aniso'] >= T['attic_aniso'])}"
          f" | std {a_['std'] / REF['attic_sunlit']['std']:.2f} (>=0.60) {ok(a_['std'] / REF['attic_sunlit']['std'] >= 0.60)}")
    print(f"  >> QA-05-2 entablature sat {e_['sat']:.3f} (<=0.70) {ok(e_['sat'] <= T['entab_sat_max'])}"
          f" | hue {e_['hue']:.1f} (30-40) {ok(T['entab_hue'][0] <= e_['hue'] <= T['entab_hue'][1])}")
    dh = abs(s_["hue"] - T["shaded_hue"])
    print(f"  >> item 2 shaded attic hue {s_['hue']:.1f} (29.5+-6, off {dh:.1f}) {ok(dh <= T['shaded_hue_tol'])}"
          f" | sat {s_['sat']:.3f} (<=0.55) {ok(s_['sat'] <= T['shaded_sat_max'])} | lum {s_['lum']:.1f} (ref 120.2)")
    print(f"  >> QA-05-4 reflection sat {w_['sat']:.3f} (>=0.25) {ok(w_['sat'] >= T['refl_sat_min'])}"
          f" lum {w_['lum']:.1f} (ref 168.9) | near water sat {n_['sat']:.3f} {T['near_water_sat']} "
          f"{ok(T['near_water_sat'][0] <= n_['sat'] <= T['near_water_sat'][1])} hue {n_['hue']:.1f} (185-200) "
          f"{ok(T['near_water_hue'][0] <= n_['hue'] <= T['near_water_hue'][1])}"
          f" | ripple R-B {m['ripples']['rb']:.1f} (ref -26 +-10) {ok(abs(m['ripples']['rb'] + 26.0) <= 10.0)}")
    sb = m["shore_band"]
    print(f"  >> QA-05-10 shore band lum {sb['lum']:.1f} (ref 115.6, +-25 %) {ok(abs(sb['lum'] - 115.6) <= 28.9)}"
          f" sat {sb['sat']:.3f} (ref 0.663, must not rise) hue {sb['hue']:.1f}")
    return m


# ---------------------------------------------------------------------------------------------------- cam05
CAM05_BAND = (300, 150, 980, 260)      # the attic / colonnade band at 115 m in the 1280x720 cam05 frame


def report_cam05(path, label=""):
    a = load(path, res=(1280, 720))
    x0, y0, x1, y1 = CAM05_BAND
    c = a[y0:y1, x0:x1]
    s = stats(c)
    print(f"\n=== cam05 {label or Path(path).name} band {CAM05_BAND} ===")
    print(f"  lum {s['lum']:6.1f} hue {s['hue']:5.1f} sat {s['sat']:.3f} std {s['std']:5.2f} "
          f"colsd {s['colsd']:5.2f} rowsd {s['rowsd']:5.2f} aniso {s['aniso']:.2f}")
    return s


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "ref"
    argv = sys.argv[2:]
    panel = int(argv[argv.index("--panel") + 1]) if "--panel" in argv else 0
    label = argv[argv.index("--label") + 1] if "--label" in argv else ""
    if what == "ref":
        a = load(ALIGNED, panel=1)
        return report_hero(a, "ref 169 aligned (panel 1)")
    path = argv[0]
    if what == "cam05":
        return report_cam05(path, label)
    a = load(path, panel=panel)
    return report_hero(a, label or Path(path).name)


if __name__ == "__main__":
    main()
