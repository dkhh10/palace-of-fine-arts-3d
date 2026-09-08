"""Round-11 lighting measurement. Plain python3 + PIL/numpy, no Blender.

Round 10 measured only the cam01 hero. Round 11's blockers (QA-04-1, QA-04-2) live on cam03 (the colonnade shade)
and cam04 (the rotunda vault), so this tool adds those two frames with QA's own boxes and prints every number the
round-11 brief asks for in one command.

    python3 scripts/light_r11_measure.py --hero  hero_1920x1080.png [...]
    python3 scripts/light_r11_measure.py --cam03 colonnade_1280x720.png [...]
    python3 scripts/light_r11_measure.py --cam04 ceiling.png [...]        # any resolution, boxes are fractional
    python3 scripts/light_r11_measure.py --ref                            # print the reference rows and exit
    python3 scripts/light_r11_measure.py --json out.json --hero a.png --cam04 b.png

Hero boxes / reference row come from light_r10_measure (QA round-03 boxes, ref 169 warped into the render frame).
cam03 boxes are QA round-04 (d); cam04 boxes are lighting's light_measure.REGIONS["ceiling"], which are QA round-03
(e)'s boxes.  Reference values are QA's published ref 128 / ref 083 numbers.

Review fix (round 10 nit): no absolute paths. ROOT is this checkout the way common.ROOT computes it, and the
reference tree honours $PFA_REFERENCE_DIR exactly as common.REFERENCE_DIR does.
"""
import sys, os, json, argparse
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import light_r10_measure as m10

ROOT = Path(__file__).resolve().parents[1]
# reference PHOTOS are gitignored and live in the MAIN checkout only (CLAUDE.md); tracked renders live here.
MAIN_ROOT = Path(os.environ.get("PFA_MAIN_ROOT", "/Users/dk/Projects/3d render blender 3rd attempt building"))
REFERENCE_DIR = Path(os.environ.get("PFA_REFERENCE_DIR", str(MAIN_ROOT / "reference")))

# ---------------------------------------------------------------- cam03, QA round-04 (d), pixel boxes at 1280x720
CAM03_BOXES = {
    "near_shaft": (0, 150, 420, 720),
    "ground":     (420, 560, 900, 720),
}
CAM03_REF = {                       # ref 128, QA round-03 (h) / round-04 (d)
    "near_shaft": dict(lum=69.7, hue=39.5),
    "ground":     dict(lum=None, hue=None),
}
CAM03_RES = (1280, 720)

# ---------------------------------------------------------------- cam04, fractional (x0, y0, x1, y1) of the frame
CAM04_BOXES = {
    "own_sky":  (0.005, 0.830, 0.050, 0.950),
    "soffit_w": (0.075, 0.280, 0.150, 0.500),
    "soffit_e": (0.800, 0.300, 0.875, 0.520),
    "coffer":   (0.400, 0.400, 0.600, 0.600),
}
CAM04_REF = dict(soffit_w=0.38, soffit_e=0.43, soffit=0.405, coffer=0.437)   # ref 083, / its own sky


def _stats(a):
    return m10.stats(a)


# ------------------------------------------------------------------------------------------------------ cam03
def measure_cam03(path):
    im = Image.open(path).convert("RGB")
    if im.size != CAM03_RES:
        im = im.resize(CAM03_RES, Image.LANCZOS)
    a = np.asarray(im, dtype=np.float64)
    out = {}
    for name, (x0, y0, x1, y1) in CAM03_BOXES.items():
        sub = a[y0:y1, x0:x1]
        s = _stats(sub)
        s["std"] = float(sub.reshape(-1, 3).mean(axis=1).std())
        out[name] = s
    out["shaft_ratio"] = out["near_shaft"]["lum"] / CAM03_REF["near_shaft"]["lum"]
    return out


def report_cam03(path, m):
    print(f"\n=== cam03 {Path(path).name} ===")
    for k in CAM03_BOXES:
        v = m[k]
        print(f"  {k:11s} sRGB {int(round(v['rgb'][0])):3d},{int(round(v['rgb'][1])):3d},{int(round(v['rgb'][2])):3d}"
              f"  lum {v['lum']:6.2f}  hue {v['hue']:5.1f}  sat {v['sat']:.3f}  std {v['std']:5.1f}")
    print(f"  >> QA-04-2 near shaft {m['near_shaft']['lum']:.1f} = {m['shaft_ratio']:.2f} of ref 128's 69.7 "
          f"(target >= 0.50), hue {m['near_shaft']['hue']:.1f} (target 34-42); ground {m['ground']['lum']:.1f} "
          f"(round 03: 60.1, round 04: 21.2)")


# ------------------------------------------------------------------------------------------------------ cam04
def measure_cam04(path):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im, dtype=np.float64)
    h, w = a.shape[:2]
    out = {}
    for name, (x0, y0, x1, y1) in CAM04_BOXES.items():
        out[name] = _stats(a[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)])
    sky = max(1e-6, out["own_sky"]["lum"])
    out["r_soffit_w"] = out["soffit_w"]["lum"] / sky
    out["r_soffit_e"] = out["soffit_e"]["lum"] / sky
    out["r_soffit"] = 0.5 * (out["r_soffit_w"] + out["r_soffit_e"])
    out["r_coffer"] = out["coffer"]["lum"] / sky
    sub = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64)
    cx0, cy0, cx1, cy1 = CAM04_BOXES["coffer"]
    c = sub[int(cy0 * h):int(cy1 * h), int(cx0 * w):int(cx1 * w)].reshape(-1, 3).mean(axis=1)
    out["coffer_std"] = float(c.std())
    return out


def report_cam04(path, m, label=""):
    print(f"\n=== cam04 {label or Path(path).name} ===")
    print(f"  own_sky {m['own_sky']['lum']:6.1f}   soffit W {m['soffit_w']['lum']:6.1f} E {m['soffit_e']['lum']:6.1f}"
          f"   coffer {m['coffer']['lum']:6.1f} (std {m['coffer_std']:.1f})")
    print(f"  >> soffit/sky  W {m['r_soffit_w']:.3f}  E {m['r_soffit_e']:.3f}  mean {m['r_soffit']:.3f} "
          f"(ref 083 0.405)")
    print(f"  >> coffer/sky  {m['r_coffer']:.3f}   (ref 083 0.437; QA-04-7 Cycles window 0.35-0.55)")


# ------------------------------------------------------------------------------------- QA-04-6, the wing bands
# QA measured the south wing at 0.63 of ref 169 and the north at 0.82 raw / 0.66 aligned, and asked lighting to check
# the sun elevation / azimuth against the shadow edges BEFORE touching any fill. A shadow-geometry error and a level
# error look identical in a mean: the mean is the same number whether the render's shadow boundary sits in the wrong
# PLACE or the lit stone is simply too dark. So compare the SHAPES: take the horizontal luminance profile of the band
# in the render and in ref 169 warped into the render frame, normalise both to zero mean / unit variance, and find the
# pixel shift that maximises their correlation. A wrong sun azimuth moves every shadow boundary along the wing and
# shows up as a large best shift and/or a poor correlation; a level error leaves the profile shape and position alone.
WING_BANDS = {
    "north_wing": (60, 480, 560, 600),
    "south_wing": (1360, 480, 1860, 600),
}
WING_REF = {"north_wing": 137.2, "south_wing": 146.5}     # ref 169 through QA's aligned panel


def _profile(a, box):
    x0, y0, x1, y1 = box
    return a[y0:y1, x0:x1].reshape(y1 - y0, x1 - x0, 3).mean(axis=2).mean(axis=0)


def measure_wings(render_path, max_shift=60):
    ren = np.asarray(Image.open(render_path).convert("RGB").resize((1920, 1080), Image.LANCZOS), dtype=np.float64)
    ref = np.asarray(Image.open(m10.ALIGNED).convert("RGB"), dtype=np.float64)[:, 1 * 1920:2 * 1920]
    out = {}
    for name, box in WING_BANDS.items():
        pr, pf = _profile(ren, box), _profile(ref, box)
        zr = (pr - pr.mean()) / max(1e-9, pr.std())
        zf = (pf - pf.mean()) / max(1e-9, pf.std())
        best, bestc = 0, -2.0
        for s in range(-max_shift, max_shift + 1):
            a = zr[max(0, s):len(zr) + min(0, s)]
            b = zf[max(0, -s):len(zf) + min(0, -s)]
            c = float((a * b).mean())
            if c > bestc:
                bestc, best = c, s
        out[name] = dict(render_lum=float(pr.mean()), ref_lum=float(pf.mean()),
                         ratio=float(pr.mean() / max(1e-9, pf.mean())),
                         best_shift_px=best, corr_at_best=bestc, corr_at_zero=float((zr * zf).mean()),
                         render_std=float(pr.std()), ref_std=float(pf.std()))
    return out


def report_wings(path, m):
    print(f"\n=== QA-04-6 wing bands {Path(path).name} (ref = ref 169 through QA's aligned panel) ===")
    for k, v in m.items():
        print(f"  {k:11s} render {v['render_lum']:6.1f} (sd {v['render_std']:5.1f})  ref {v['ref_lum']:6.1f} "
              f"(sd {v['ref_std']:5.1f})  ratio {v['ratio']:.2f}  |  profile corr {v['corr_at_zero']:+.3f} at 0 px, "
              f"best {v['corr_at_best']:+.3f} at {v['best_shift_px']:+d} px")
    print("  >> a wrong sun azimuth moves the shadow boundaries: large best shift and/or weak correlation.")


def gap(eevee, cycles):
    print(f"\n  >> QA-04-1 Eevee-Cycles gap: soffit W {eevee['r_soffit_w']-cycles['r_soffit_w']:+.3f} "
          f"E {eevee['r_soffit_e']-cycles['r_soffit_e']:+.3f} coffer {eevee['r_coffer']-cycles['r_coffer']:+.3f} "
          f"(all must be within 0.15)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--hero", nargs="*", default=[])
    ap.add_argument("--cam03", nargs="*", default=[])
    ap.add_argument("--cam04", nargs="*", default=[])
    ap.add_argument("--wings", nargs="*", default=[])
    ap.add_argument("--gap", nargs=2, default=None, metavar=("EEVEE", "CYCLES"))
    ap.add_argument("--ref", action="store_true")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    allm = {}
    if a.ref:
        print(m10.TARGETS)
        r = m10.measure(m10.ALIGNED, panel=1)
        m10.report(str(m10.ALIGNED), r, "REF 169 warped into the render frame (panel 1)")
        allm["ref169"] = r
        print(f"\nref 128 (cam03): near shaft lum 69.7 hue 39.5   |   ref 083 (cam04): soffit/sky 0.405, coffer/sky 0.437")
    for p in a.hero:
        r = m10.measure(p)
        m10.report(p, r)
        allm["hero:" + Path(p).name] = r
    for p in a.cam03:
        r = measure_cam03(p)
        report_cam03(p, r)
        allm["cam03:" + Path(p).name] = r
    for p in a.cam04:
        r = measure_cam04(p)
        report_cam04(p, r)
        allm["cam04:" + Path(p).name] = r
    for p in a.wings:
        r = measure_wings(p)
        report_wings(p, r)
        allm["wings:" + Path(p).name] = r
    if a.gap:
        e, c = measure_cam04(a.gap[0]), measure_cam04(a.gap[1])
        report_cam04(a.gap[0], e, "EEVEE " + Path(a.gap[0]).name)
        report_cam04(a.gap[1], c, "CYCLES " + Path(a.gap[1]).name)
        gap(e, c)
        allm["cam04_eevee:" + Path(a.gap[0]).name] = e
        allm["cam04_cycles:" + Path(a.gap[1]).name] = c
    if a.json:
        Path(a.json).write_text(json.dumps(allm, indent=1))
