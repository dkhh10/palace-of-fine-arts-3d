"""Round-19 lighting measurement (QA-08-2 / QA-09-6, the blue-violet shaded stone at cam02).

`light_r17_measure`'s box set and verdicts, plus the CIELAB columns the Phase 8b item-c table is written in
(`scripts/p8b_c_cielab.py`: per-pixel sRGB -> linear -> XYZ D65 -> L*a*b*, averaged over the box -- NOT the Lab of
the box's mean colour, which differs by ~0.3 on a high-contrast box), and the delta of every column against a
BEFORE frame.  The brief's acceptance is stated in these units, so it is checked in code:

    station 2, boxes shade_pier / shade_pier_r / shade_arch / soffit_l / soffit_r:  b* >= +5, h_ab 40-80, R-B >= +10
    shade_frieze (control):  b* = +11.4 +- 1.5        sky: unmoved (camera rays)
    hero (cam01):  every box within 3 % of luma and 2 deg of hue of BEFORE

    python3 scripts/light_r19_measure.py --before <BEFORE.png> --after <AFTER.png> [...]
    python3 scripts/light_r19_measure.py --shade <dir-or-pngs>            # no BEFORE, absolute numbers only
    python3 scripts/light_r19_measure.py --mae A.png B.png                # the noise floor control
"""
import sys, os, json, argparse
from pathlib import Path
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import light_r10_measure as m10
import light_r14_measure as m14
import light_r17_measure as m17
import p8b_c_cielab as lab


def _named(path, cam):
    """m17.measure resolves the camera from the FILE NAME; hand it a name it can resolve without copying
    the frame, by symlinking into a scratch dir only when the name does not already carry `_0N`."""
    import tempfile
    if m17.cam_of(path) == cam:
        return str(path)
    d = Path(tempfile.gettempdir()) / "pfa_r19_names"
    d.mkdir(exist_ok=True)
    link = d / f"{Path(path).stem}_{cam}{Path(path).suffix}"
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(Path(path).resolve())
    return str(link)

ROOT = Path(__file__).resolve().parents[1]
BOXES = m17.BOXES

# brief item 1, in code so the verdict cannot drift from the text
SHADE_BOXES = ("shade_pier", "shade_pier_r", "shade_arch", "soffit_l", "soffit_r")
ACCEPT = dict(b=(5.0, 1e9), h_ab=(40.0, 80.0), r_minus_b=(10.0, 1e9))
FRIEZE = (11.4 - 1.5, 11.4 + 1.5)
HERO_HOLD = dict(lum_pct=3.0, hue_deg=2.0)


def cam_of(name):
    """m17.cam_of, plus the lead's `cam0N_1080_32spp.png` naming for the Phase 8/9 station references
    (its stem's last token is `32spp` and it has no `_0N`, so the r17 resolver returns None on it)."""
    stem = Path(name).stem
    for k in BOXES:
        if stem.startswith("cam" + k) or f"_cam{k}" in stem:
            return k
    return m17.cam_of(name)


def measure(path, cam=None):
    """r17's stats for every box of the frame's camera, with the CIELAB columns merged in."""
    cam = cam or cam_of(path)
    if cam is None:
        return None
    got = m17.measure(_named(path, cam))
    if got is None:
        return None
    cam, out = got
    spec = BOXES[cam]
    a = m14.load(str(path), spec["size"])
    for k, (x0, y0, x1, y1) in spec["boxes"].items():
        crop = a[y0:y1, x0:x1].reshape(-1, 3)
        L = lab.srgb_to_lab(crop).mean(0)
        out[k]["L"] = float(L[0]); out[k]["a"] = float(L[1]); out[k]["b"] = float(L[2])
        out[k]["chroma"] = float(np.hypot(L[1], L[2]))
        out[k]["h_ab"] = float(np.degrees(np.arctan2(L[2], L[1])) % 360.0)
        mean = crop.mean(0)
        out[k]["r_minus_b"] = float(mean[0] - mean[2])
    return cam, out


def verdict(cam, box, s):
    if cam != "02":
        return ""
    if box in SHADE_BOXES:
        bits = []
        for key, (lo, hi) in ACCEPT.items():
            v = s[key]
            bits.append(f"{key} {'PASS' if lo <= v <= hi else 'FAIL'}")
        return "  " + " ".join(bits)
    if box == "shade_frieze":
        return f"  frieze {'PASS' if FRIEZE[0] <= s['b'] <= FRIEZE[1] else 'FAIL'}[{FRIEZE[0]}-{FRIEZE[1]}]"
    return ""


def hold(before, after):
    """cam01/03/04 HOLD: |dlum| <= 3 % and |dhue| <= 2 deg, per box.  Returns (rows, n_fail)."""
    rows, bad = [], 0
    for k in before:
        if k not in after or "lum" not in before[k]:
            continue
        b0, a0 = before[k], after[k]
        dl = 100.0 * (a0["lum"] - b0["lum"]) / max(1e-6, b0["lum"])
        dh = (a0["hue"] - b0["hue"] + 180.0) % 360.0 - 180.0
        ok = abs(dl) <= HERO_HOLD["lum_pct"] and abs(dh) <= HERO_HOLD["hue_deg"]
        bad += 0 if ok else 1
        rows.append((k, b0["lum"], a0["lum"], dl, b0["hue"], a0["hue"], dh, "ok" if ok else "MOVED"))
    return rows, bad


def mae(p, q):
    """Mean absolute sRGB difference of two frames at NATIVE resolution: the 32 spp + OIDN noise floor
    when the two frames are the same scene at two seeds, and the control every later delta is read against."""
    from PIL import Image
    a = np.asarray(Image.open(p).convert("RGB"), dtype=np.float64)
    b = np.asarray(Image.open(q).convert("RGB"), dtype=np.float64)
    assert a.shape == b.shape, (a.shape, b.shape)
    return float(np.abs(a - b).mean()), float(np.abs(a - b).max())


def _print(tag, cam, out):
    print(f"\n-- {tag}   (cam {cam}, boxes at {BOXES[cam]['size'][0]}x{BOXES[cam]['size'][1]})")
    print(f"   {'box':15s} {'lum':>6s} {'hue':>6s} {'sat':>6s} {'R-B':>7s} | {'L*':>6s} {'a*':>6s} "
          f"{'b*':>7s} {'h_ab':>6s}")
    for k, s in out.items():
        if "L" not in s:
            continue
        print(f"   {k:15s} {s['lum']:6.1f} {s['hue']:6.1f} {s['sat']:6.3f} {s['r_minus_b']:+7.1f} | "
              f"{s['L']:6.2f} {s['a']:+6.2f} {s['b']:+7.2f} {s['h_ab']:6.1f}{verdict(cam, k, s)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", default=None)
    ap.add_argument("--after", nargs="*", default=[])
    ap.add_argument("--shade", nargs="*", default=[])
    ap.add_argument("--mae", nargs=2, default=None)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    if args.mae:
        m, mx = mae(*args.mae)
        print(f"MAE {m:.4f}  max {mx:.1f}   {Path(args.mae[0]).name} vs {Path(args.mae[1]).name}")
        raise SystemExit

    res = {}
    base = None
    if args.before:
        cam, base = measure(args.before)
        _print(f"BEFORE {Path(args.before).name}", cam, base)
        res["BEFORE"] = base
    for f in m14.frames_of(args.after + args.shade):
        got = measure(f)
        if got is None:
            print(f"   (skipped {Path(f).name}: no camera id in the name)")
            continue
        cam, out = got
        _print(Path(f).name, cam, out)
        res[Path(f).name] = out
        if base is not None and cam == cam_of(args.before):
            rows, bad = hold(base, out)
            print(f"   HOLD vs BEFORE (<= {HERO_HOLD['lum_pct']} % lum, {HERO_HOLD['hue_deg']} deg hue): "
                  f"{len(rows) - bad}/{len(rows)} held")
            for k, l0, l1, dl, h0, h1, dh, ok in rows:
                if ok != "ok":
                    print(f"      {k:15s} lum {l0:6.1f} -> {l1:6.1f} ({dl:+5.1f} %)  hue {h0:6.1f} -> "
                          f"{h1:6.1f} ({dh:+5.1f} deg)  {ok}")
    if args.json:
        Path(args.json).write_text(json.dumps(res, indent=1))
        print(f"\n[r19] wrote {args.json}")
