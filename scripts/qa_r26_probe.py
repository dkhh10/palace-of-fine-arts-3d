#!/usr/bin/env python3
"""QA round 26 (the ENV R3 backdrop tiles on deploy 14) probe.  No Blender, no Chrome.

An EXTENSION of `scripts/qa_r25_probe.py` (-> r24 -> ... -> r13): every carried measure keeps its
earlier definition, retargeted to `gate14` (before = `gate13`).  The backdrop boxes are QA 22's
`qa_r22_probe.BACKDROP` -- the same boxes the ENV round and the export round measured on.

    python3 scripts/qa_r26_probe.py backdrop   # the 8d boxes: gate13 -> gate14, cycles p9, ref 105
    python3 scripts/qa_r26_probe.py seam       # the QA-21 grid index on the same boxes (lattice test)
    python3 scripts/qa_r26_probe.py diff       # gate14 vs gate13 per station: MAE, moved px, extent
    python3 scripts/qa_r26_probe.py parity     # MAE vs cycles_p9 per station, gate13 -> gate14
    python3 scripts/qa_r26_probe.py counters   # payload / perf / resident / page errors / mobile
    python3 scripts/qa_r26_probe.py mobile     # gate14m vs gate13m per station
    python3 scripts/qa_r26_probe.py band       # the 4K hero dark band above the right entablature
    python3 scripts/qa_r26_probe.py all
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_r22_probe as P22  # noqa: E402

P = P22.P
ROOT = P22.ROOT
WEB = P22.WEB
P9 = ROOT / "renders/qa_comparisons/cycles_p9"
HERO4K = ROOT / "renders/final/hero_cam01_3840x2160_128spp.png"

CUR, PREV = "gate14", "gate13"


def _f(tag, st):
    return P.rgb(str(WEB / f"{tag}_cam{st:02d}.png"))


def _cyc(st):
    return P.rgb(str(P9 / f"cam{st:02d}_1080_32spp.png"))


def _ref105():
    return P.rgb(str(P22.REF105))


def _mask(st, a):
    y = P22.WATERLINE.get(st)
    return a if y is None else a[:y]


# ------------------------------------------------------------------------------------- backdrop
def cmd_backdrop(_a=()):
    print(f"== the 8d backdrop boxes, {PREV} -> {CUR} (the R3 gain tiles), with cycles p9 and ref 105 ==")
    print("   NOTE cycles_p9 was rendered BEFORE ENV R3, so at these boxes it is a pre-tile state,")
    print("   not the target; ref 105 is the aerial photograph, unregistered (its own framing).")
    r105 = _ref105()
    print(f"{'box':24s} {'st':>2s} {'frame':10s} {'luma':>7s} {'sat':>7s} {'hf':>8s} {'sd':>7s} {'d hf %':>8s}")
    for name, st, box, why in P22.BACKDROP:
        base = None
        for lbl, img in ((PREV, _f(PREV, st)), (CUR, _f(CUR, st)), ("cycles p9", _cyc(st))):
            b = P22._bd(img, box)
            if lbl == PREV:
                base = b["hf"]
            d = 100.0 * (b["hf"] - base) / base if base else 0.0
            print(f"{name if lbl == PREV else '':24s} {st if lbl == PREV else '':>2} {lbl:10s} "
                  f"{b['lum']:7.3f} {b['sat']:7.3f} {b['hf']:8.4f} {b['sd']:7.3f} "
                  f"{('' if lbl == PREV else f'{d:+7.1f}'):>8s}")
        if st == 6:
            h, w = r105.shape[:2]
            x0, y0, x1, y1 = box
            rb = (int(x0 * w / 1920), int(y0 * h / 1080), int(x1 * w / 1920), int(y1 * h / 1080))
            b = P22._bd(r105, rb)
            print(f"{'':24s} {'':>2} {'ref105*':10s} {b['lum']:7.3f} {b['sat']:7.3f} "
                  f"{b['hf']:8.4f} {b['sd']:7.3f}  (* box scaled to the photo, not registered)")
        print(f"{'':24s} ({why})")


def cmd_seam(_a=()):
    """A repeat lattice would show as an ordered grid in the high-pass residual (QA 21 index)."""
    import qa_r21_probe as P21
    print(f"== lattice / seam test on the same boxes, {PREV} -> {CUR} (cycles p9 = control) ==")
    print(f"{'box':24s} {'st':>2s} {'frame':10s} {'grid x':>7s} {'grid y':>7s} {'grid':>7s} "
          f"{'period':>6s} {'hp std':>7s}")
    for name, st, box, _why in P22.BACKDROP:
        for lbl, img in ((PREV, _f(PREV, st)), (CUR, _f(CUR, st)), ("cycles p9", _cyc(st))):
            g = P21.grid_index(img, box)
            print(f"{name if lbl == PREV else '':24s} {st if lbl == PREV else '':>2} {lbl:10s} "
                  f"{g['grid_x']:7.2f} {g['grid_y']:7.2f} {g['grid']:7.2f} {g['period']:6d} "
                  f"{g['hp_std']:7.2f}")


# ------------------------------------------------------------------------------------ regression
def _diff(a, b):
    d = np.abs(a.astype(np.float32) - b.astype(np.float32)).max(2)
    return d


def cmd_diff(_a=()):
    print(f"== {CUR} vs {PREV}, per station: whole frame and above the waterline ==")
    print(f"{'st':>2s} {'MAE':>8s} {'MAE %':>7s} {'px>1/255':>9s} {'y span (5-95 pct)':>20s} "
          f"{'x span':>14s} {'MAE masked':>11s} {'luma ratio':>11s}")
    for st in range(1, 7):
        a, b = _f(PREV, st), _f(CUR, st)
        mae = float(np.abs(a.astype(np.float32) - b.astype(np.float32)).mean())
        d = _diff(a, b)
        moved = d > 1
        frac = 100.0 * moved.mean()
        ys, xs = np.nonzero(moved)
        span_y = f"{int(np.percentile(ys, 5))}-{int(np.percentile(ys, 95))}" if ys.size else "-"
        span_x = f"{int(np.percentile(xs, 5))}-{int(np.percentile(xs, 95))}" if xs.size else "-"
        am, bm = _mask(st, a), _mask(st, b)
        maem = float(np.abs(am.astype(np.float32) - bm.astype(np.float32)).mean())
        lr = float((bm @ P.LUMA).mean() / max(1e-6, (am @ P.LUMA).mean()))
        print(f"{st:>2} {mae:8.4f} {100*mae/255:7.3f} {frac:8.2f}% {span_y:>20s} {span_x:>14s} "
              f"{maem:11.4f} {lr:11.5f}x")


def cmd_parity(_a=()):
    print(f"== parity vs cycles_p9 (full resolution), {PREV} -> {CUR}, above-waterline mask ==")
    print(f"{'st':>2s} {'MAE% g13':>9s} {'MAE% g14':>9s} {'delta':>8s} {'p10 g13':>8s} "
          f"{'p10 g14':>8s} {'p10 cyc':>8s} {'luma g14':>9s} {'luma cyc':>9s}")
    for st in range(1, 7):
        a, b, c = _mask(st, _f(PREV, st)), _mask(st, _f(CUR, st)), _mask(st, _cyc(st))
        ma = 100 * float(np.abs(a.astype(np.float32) - c.astype(np.float32)).mean()) / 255
        mb = 100 * float(np.abs(b.astype(np.float32) - c.astype(np.float32)).mean()) / 255
        pa, pb, pc = (float(np.percentile(x @ P.LUMA, 10)) for x in (a, b, c))
        la, lc = float((b @ P.LUMA).mean()), float((c @ P.LUMA).mean())
        print(f"{st:>2} {ma:9.3f} {mb:9.3f} {mb-ma:+8.3f} {pa:8.1f} {pb:8.1f} {pc:8.1f} "
              f"{la:9.1f} {lc:9.1f}")


def cmd_mobile(_a=()):
    print(f"== mobile: {CUR}m vs {PREV}m per station (MAE 0-255, whole frame) ==")
    for st in range(1, 7):
        a, b = _f(PREV + "m", st), _f(CUR + "m", st)
        mae = float(np.abs(a.astype(np.float32) - b.astype(np.float32)).mean())
        print(f"   cam{st:02d}  MAE {mae:7.3f}   moved px {100*float((_diff(a,b)>1).mean()):5.2f} %")


def cmd_counters(_a=()):
    for tag in (PREV, CUR):
        n = json.loads((WEB / f"{tag}_net.json").read_text())
        m = json.loads((WEB / f"{tag}m_net.json").read_text())
        p = json.loads((WEB / f"{tag}_perf.json").read_text())
        c = json.loads((WEB / f"{tag}_cam.json").read_text())
        cm = json.loads((WEB / f"{tag}m_cam.json").read_text())
        st = p["stations"]
        med = [s["frame_ms"]["median"] for s in st]
        res = st[0]["resident"]
        print(f"== {tag} ==")
        print(f"   desktop first frame {n['bytes_before_first_frame']/1e6:7.2f} MB / "
              f"{n['requests_before_first_frame']} req, total {n['bytes_total']/1e6:7.1f} MB, "
              f"ttff {n.get('time_to_first_frame_s')} s")
        print(f"   mobile  first frame {m['bytes_before_first_frame']/1e6:7.2f} MB / "
              f"{m['requests_before_first_frame']} req, total {m['bytes_total']/1e6:7.1f} MB")
        print(f"   medians ms {[round(x,1) for x in med]}  fps {[round(1000/x,1) for x in med]}")
        print(f"   draws {[s['draw_calls'] for s in st]}  tris "
              f"{[round(s['triangles']/1e6,2) for s in st]}  programs {[s['programs'] for s in st]}")
        print(f"   resident tex {res['texture_bytes']/1e6:.1f} MB geo "
              f"{res['geometry_bytes']/1e6:.1f} MB")
        print(f"   pageErrors desktop {c['pageErrors']} mobile {cm['pageErrors']} "
              f"walkProbes {c.get('walkProbes')}")
        for key in ("info", "breakdown"):
            v = c.get(key)
            if isinstance(v, dict):
                print(f"   {key}: " + ", ".join(f"{k}={v[k]}" for k in list(v)[:12]))


# ---------------------------------------------------------------------- the 4K hero's dark band
def cmd_band(_a=()):
    """Row-mean luma across the entablature band, 4K hero vs the viewer's cam01, same world band."""
    hero = np.asarray(Image.open(str(HERO4K)).convert("RGB")).astype(np.float32)
    v = _f(CUR, 1).astype(np.float32)
    print("== the 4K hero band above the right colonnade entablature ==")
    for tag, im, x0, x1, y0, y1, sc in (("hero4k", hero, 2400, 3040, 860, 1010, 2.0),
                                        ("gate14 cam01", v, 1200, 1520, 430, 505, 1.0)):
        lum = (im[:, :, 0] * 0.2126 + im[:, :, 1] * 0.7152 + im[:, :, 2] * 0.0722)
        print(f"-- {tag} rows y {y0}-{y1} (frame px), x {x0}-{x1}, 1 row = {1/sc:.1f} hero px")
        for y in range(y0, y1):
            row = lum[y, x0:x1]
            rgb = im[y, x0:x1].mean(0)
            print(f"   y {y:5d}  luma {row.mean():7.2f}  rgb "
                  f"{rgb[0]:6.1f} {rgb[1]:6.1f} {rgb[2]:6.1f}")


def cmd_all(_a=()):
    for fn in (cmd_backdrop, cmd_seam, cmd_diff, cmd_parity, cmd_mobile, cmd_counters):
        fn()
        print()


if __name__ == "__main__":
    CMDS = {"backdrop": cmd_backdrop, "seam": cmd_seam, "diff": cmd_diff, "parity": cmd_parity,
            "mobile": cmd_mobile, "counters": cmd_counters, "band": cmd_band, "all": cmd_all}
    a = sys.argv[1:] or ["all"]
    CMDS[a[0]](a[1:])
