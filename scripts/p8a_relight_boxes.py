#!/usr/bin/env python3
"""Phase 8a stage 2 — the eight QA-17 shrub boxes for one or more `?cardsun=` captures.

No Blender, no Chrome: pure pixel analysis of captures already on disk.

    python3 scripts/p8a_relight_boxes.py p8a_cs0 p8a_cs05 p8a_adopt
    python3 scripts/p8a_relight_boxes.py --json out.json p8a_cs0 p8a_cs05

Captures are read from THIS checkout's `renders/web/<tag>_cam%02d.png`; `ref` is what every QA round
since 13 calls the reference — the Phase 5 **Cycles** frame at that station (`qa_r13_probe.REF`), in
the MAIN checkout. The metrics are QA 16's own (`qa_r16_probe.box_stats`), not new ones:

    leaf%  (G - 0.85R > 5) & (B < G)     the foliage mask — REPORTED in 8a, not gated
    hard%  share of pixels whose luma gradient > 40/255   — must not rise above the reference
    lum    mean luma of the box, and `x ref`; `fn` divides it by the whole-frame ratio of the same
           station (QA 16 §3's frame-normalised level) — the CONSTRAINT: within 3 % of cardsun 0
    hue / sat   of the leaf pixels, reported

The first tag on the command line is the baseline (cardsun 0 = today); every later tag is shown
against it as well as against the reference.
"""
import json
import sys
from pathlib import Path

import numpy as np

MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
sys.path.insert(0, str(MAIN / "scripts"))
import qa_r17_probe as P17  # noqa: E402
import qa_r16_probe as P16  # noqa: E402

P = P16.P
HERE = Path(__file__).resolve().parents[1]
WEB = HERE / "renders" / "web"
REF = {st: (MAIN / p.relative_to(P.ROOT), lbl) for st, (p, lbl) in P.REF_R14.items()}
P.REF = REF


def frame(tag, st):
    return P.rgb(str(WEB / f"{tag}_cam{st:02d}.png"))


def ref(st):
    return P.rgb(REF[st][0])


def leaf_px(crop):
    r, g, b = crop[..., 0], crop[..., 1], crop[..., 2]
    return (np.minimum(g - 0.85 * r - 5.0, g - b)) > 0.0


def row(a, box, frame_lum):
    s = P16.box_stats(a, box)
    x0, y0, x1, y1 = box
    crop = a[y0:y1, x0:x1]
    m = leaf_px(crop)
    px = crop[m]
    hue, sat = (float("nan"), float("nan"))
    if px.size:
        hue, _ = P.hue_sat(px.mean(0))
        mx, mn = px.max(1), px.min(1)
        sat = float(np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0.0).mean())
    return dict(leaf=float(m.mean() * 100.0), hard=s["hard"], soft=s["soft"], lum=s["lum"],
                hue=hue, sat=sat, frame_lum=frame_lum)


def main():
    args = sys.argv[1:]
    out_json = None
    if args and args[0] == "--json":
        out_json = args[1]
        args = args[2:]
    if not args:
        print(__doc__)
        return 1
    base = args[0]
    data = {}
    print(f"== the eight QA-17 shrub boxes, ?cardsun= captures vs the Cycles reference "
          f"(baseline {base}) ==")
    print(f"{'box':22s} {'tag':12s} {'leaf%':>6s} {'/ref':>6s} {'hard%':>6s} {'ref':>6s} "
          f"{'lum':>7s} {'/ref':>6s} {'fn':>6s} {'/base':>7s} {'hue':>6s} {'sat':>6s}")
    for name, st, box, _why in P17.SHRUB:
        rf_img = ref(st)
        rf_frame = float((rf_img @ P.LUMA).mean())
        rf = row(rf_img, box, rf_frame)
        rows = {"ref": rf}
        for tag in args:
            a = frame(tag, st)
            rows[tag] = row(a, box, float((a @ P.LUMA).mean()))
        for tag in ("ref", *args):
            r = rows[tag]
            fn = (r["lum"] / max(rf["lum"], 1e-6)) / max(r["frame_lum"] / max(rf_frame, 1e-6), 1e-6)
            base_fn = ((rows[base]["lum"] / max(rf["lum"], 1e-6))
                       / max(rows[base]["frame_lum"] / max(rf_frame, 1e-6), 1e-6))
            print(f"{name if tag == 'ref' else '':22s} {tag:12s} {r['leaf']:5.1f}% "
                  f"{r['leaf'] / max(rf['leaf'], 1e-6):5.2f}x {r['hard']:5.2f}% {rf['hard']:5.2f}% "
                  f"{r['lum']:7.1f} {r['lum'] / max(rf['lum'], 1e-6):5.2f}x {fn:5.2f}x "
                  f"{fn / max(base_fn, 1e-6):6.3f}x {r['hue']:6.1f} {r['sat']:6.3f}")
        data[name] = {t: rows[t] for t in rows}
    print("\n  /base on `fn` is the LEVEL constraint: 1.000 +- 0.03 at every box.")
    print("  hard% must not rise above the reference's column where it is already below it.")
    print("  leaf%/ref is REPORTED (8a decision 2: 1 % of red moves it 2-9 % relative).")
    if out_json:
        Path(out_json).write_text(json.dumps(data, indent=1))
        print(f"  wrote {out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
