"""Phase 10 r2 materials (water + foliage + column tint): every box of the round, on any 1920x1080 cam-01 frame.
Plain python (numpy + PIL), no Blender.

    /opt/homebrew/bin/python3.13 scripts/mat_p10w_measure.py hero  label=frame.png [label=frame.png ...]
    /opt/homebrew/bin/python3.13 scripts/mat_p10w_measure.py band  label=frame.png ...   (water band only: rows >= 740)
    /opt/homebrew/bin/python3.13 scripts/mat_p10w_measure.py cam05 label=frame.png ...   (1280x720)
    /opt/homebrew/bin/python3.13 scripts/mat_p10w_measure.py cam06 label=frame.png ...   (1280x720)

References, both measured here (never quoted):
  * stone / water boxes: ref 169 warped into the hero frame by `mat_projection.warp_ref169()` (arch_params.REF169_XF,
    the transform the round-1 projection hold table used; its column row 96.8 / 24.8 / 0.585 is reproduced here).
  * foliage boxes: ref 169 by `env_p10_boxes.ref_frame()` (env_r8_fit.REF_XF), the ENV round-1/2 transform.

Water texture (the brief's "row-wise luminance autocorrelation / anisotropy") on the reflection column box
900 760 1020 840, Rec.709 luminance of the 8-bit frame:
  acx(k) / acy(k)   mean normalised autocorrelation at lag k px along rows (x) / along columns (y), row / column
                    means removed first -- a horizontal streak is long in x and short in y
  Lx / Ly           lag (px, linear interpolation) where that autocorrelation first falls below 0.5
  aspect            Lx / Ly (> 1 = horizontal streaks)
  aniso             std(column means) / std(row means) (mat_r7_measure's definition; < 1 = rows differ = streaks)
  cv                std / mean of the box luminance (streak contrast)
  dark              share of box pixels below 0.6 x the box mean (the dark gaps between streaks)
Foliage (definitions fixed here, used for every column):
  * conifer mass    box 1s (x .655-.740, y .280-.440, the part of the NE box a tree fills) -- mean RGB of the
                    NON-sky pixels (env_p10_boxes' sky mask), luma Rec.601, B/G of the mean
  * willow leaf     box 2 (x .390-.470, y .450-.620) -- mean RGB of the env_p10_boxes leaf-mask pixels
  * box 2 dark      env_p10_boxes' dark share (luma < 60) on box 2, the ENV acceptance number
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mat_r7_measure import stats, columns, BOXES           # noqa: E402
import env_p10_boxes as EB                                 # noqa: E402

W, H = 1920, 1080
REFL = BOXES["water_refl"]
OPEN = ("near_water_sky", "ripples", "lagoon_flank")
CAM05_LAGOON = (0, 560, 1280, 720)       # cam05 lagoon band (bottom of the 1280x720 frame): sat >= 0.25
CAM06_LAGOON = (60, 380, 340, 500)       # mat_r7fix_cam06's open-water box (1280x720)


def load(p, res=(W, H)):
    im = Image.open(p).convert("RGB")
    if im.size != res:
        im = im.resize(res, Image.Resampling.LANCZOS)
    return np.asarray(im).astype(np.float64)


_REF = {}


def ref_stone():
    if "s" not in _REF:
        import mat_projection as MP
        _REF["s"] = MP.warp_ref169()[0]
    return _REF["s"]


def ref_foliage():
    if "f" not in _REF:
        _REF["f"] = EB.ref_frame()
    return _REF["f"]


def lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def _ac(g, axis, k):
    g = g - g.mean(axis=axis, keepdims=True)
    if axis == 1:
        a, b = g[:, :-k], g[:, k:]
    else:
        a, b = g[:-k, :], g[k:, :]
    return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))


def _len(g, axis, maxk=30):
    prev = 1.0
    for k in range(1, maxk + 1):
        c = _ac(g, axis, k)
        if c < 0.5:
            return k - 1 + (prev - 0.5) / max(prev - c, 1e-6)
        prev = c
    return float(maxk)


def texture(a, bx=REFL):
    x0, y0, x1, y1 = bx
    g = lum(a[y0:y1, x0:x1])
    lx, ly = _len(g, 1), _len(g, 0)
    return dict(acx3=_ac(g, 1, 3), acy3=_ac(g, 0, 3), Lx=lx, Ly=ly, aspect=lx / max(ly, 1e-6),
                aniso=float(g.mean(axis=0).std() / max(g.mean(axis=1).std(), 1e-6)),
                cv=float(g.std() / max(g.mean(), 1e-6)), dark=float((g < 0.6 * g.mean()).mean()))


def boxstats(a, bx):
    x0, y0, x1, y1 = bx
    return stats(a[y0:y1, x0:x1])


def foliage(a):
    sky, dark, leaf = EB.masks(a)
    out = {}
    for key, name in (("con", "1s NE mass sky side"), ("wil", "2  willow box"), ("ne", "1  NE mass (brief)")):
        x0, y0, x1, y1 = EB.BOXES[name]
        sl = (slice(int(y0 * H), int(y1 * H)), slice(int(x0 * W), int(x1 * W)))
        px = a[sl]
        m = (~sky[sl]) if key != "wil" else leaf[sl]
        rgb = px[m].mean(axis=0) if m.sum() > 20 else np.zeros(3)
        out[key] = dict(rgb=rgb, luma=float(0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]),
                        bg=float(rgb[2] / max(rgb[1], 1e-6)), dark=100 * float(dark[sl].mean()),
                        sky=100 * float(sky[sl].mean()), leaf=100 * float(leaf[sl].mean()), n=int(m.sum()))
    return out


def fs(s):
    return f"{s['lum']:6.1f}/{s['hue']:5.1f}/{s['sat']:.3f}/{s['rb']:+6.1f}"


def hero(frames, band_only=False):
    rows = [("ref169", ref_stone(), ref_foliage())] + [(l, a, a) for l, a in frames]
    print("== water reflection box 900 760 1020 840: lum/hue/sat/R-B | texture")
    for l, a, _ in rows:
        s, t = boxstats(a, REFL), texture(a)
        print(f"  {l:14s} {fs(s)} | acx3 {t['acx3']:.2f} acy3 {t['acy3']:.2f} Lx {t['Lx']:5.2f} Ly {t['Ly']:5.2f} "
              f"aspect {t['aspect']:4.2f} aniso {t['aniso']:4.2f} cv {t['cv']:.3f} dark {100 * t['dark']:4.1f} %")
    print("== open water (lum/hue/sat/R-B)")
    for k in OPEN:
        for l, a, _ in rows:
            print(f"  {k:15s} {l:14s} {fs(boxstats(a, BOXES[k]))}")
    if band_only:
        return
    print("== stone hold boxes (lum/hue/sat/R-B)")
    for name, get in (("attic_sunlit", lambda x: boxstats(x, BOXES["attic_sunlit"])),
                      ("attic_shaded", lambda x: boxstats(x, BOXES["attic_shaded"])),
                      ("entablature", lambda x: boxstats(x, BOXES["entablature"])),
                      ("vault field", lambda x: stats(x[380:430, 900:1010])),
                      ("jamb", lambda x: stats(x[400:480, 872:892])),
                      ("columns(mask)", columns),
                      ("shaft crop", lambda x: boxstats(x, (1000, 360, 1240, 480)))):
        for l, a, _ in rows:
            print(f"  {name:15s} {l:14s} {fs(get(a))}")
    print("== foliage: conifer (box 1s non-sky) | willow leaf (box 2 leaf px) | box 2 dark/leaf % | box 1 dark/sky %")
    for l, _, f in rows:
        d = foliage(f)
        c, w = d["con"], d["wil"]
        print(f"  {l:14s} con RGB ({c['rgb'][0]:5.1f},{c['rgb'][1]:5.1f},{c['rgb'][2]:5.1f}) luma {c['luma']:5.1f} B/G {c['bg']:.2f}"
              f" | wil RGB ({w['rgb'][0]:5.1f},{w['rgb'][1]:5.1f},{w['rgb'][2]:5.1f}) luma {w['luma']:5.1f} B/G {w['bg']:.2f}"
              f" | box2 dark {w['dark']:4.1f} leaf {w['leaf']:4.1f} | box1 dark {d['ne']['dark']:4.1f} sky {d['ne']['sky']:4.1f}")


def small(frames, bx, name):
    print(f"== {name} box {bx} (1280x720): lum/hue/sat/R-B")
    for l, p in frames:
        print(f"  {l:14s} {fs(boxstats(load(p, (1280, 720)), bx))}")


if __name__ == "__main__":
    cmd, fr = sys.argv[1], [a.partition("=")[::2] for a in sys.argv[2:]]
    if cmd in ("hero", "band"):
        hero([(l, load(p)) for l, p in fr], band_only=(cmd == "band"))
    elif cmd == "cam05":
        small(fr, CAM05_LAGOON, "cam05 lagoon")
    elif cmd == "cam06":
        small(fr, CAM06_LAGOON, "cam06 lagoon")
    else:
        raise SystemExit(__doc__)
