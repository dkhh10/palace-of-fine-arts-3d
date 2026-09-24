#!/usr/bin/env python3
"""Phase 10 ENV round 2, item 1: the willow box (cam 01 x 0.39-0.47, y 0.45-0.62) measured on the tree's OWN pixels.

    /opt/homebrew/bin/python3.13 scripts/env_p10r2_willowbox.py [--write-ref-mask] [label=mask.png ...]

No Blender, no colour threshold.
  * ours: `scripts/env_p10r2_mask.py` writes the willow's own-pixel alpha (Cycles, holdout on everything else, LOD0).
    Own pixel = alpha > 0.5.  Also reported: the ENVELOPE (own pixels with holes closed row-wise between the tree's
    outermost pixels in each row of the box), because the photo can only be segmented as an envelope.
  * ref 169 (registered to the cam-01 frame by env_r8_fit.REF_XF, as env_p10_boxes does): the weeping willow is
    HAND-SEGMENTED as a polygon, REF_WILLOW below, traced on a 4.5x gridded zoom of the registered frame (vertices in
    cam-01 1920x1080 px).  It is the drooping crown whose branch arch tops out at row ~601 between x 770-820 and whose
    curtain reaches the water at row ~703; the lacy pale tree behind-left (x 0.33-0.40, top row ~535) is a different
    tree and is excluded.  The willow's top is sparse (stone shows between the strands), so the polygon is an envelope:
    compare it with our ENVELOPE share; our raw own-pixel share is reported next to it.
Numbers per frame:
  share     % of the box's pixels that are the willow (own px / envelope)
  top       crown-top row inside the box's columns: median over the box columns that hold any willow pixel of the
            first row (from the frame top) with 3 consecutive willow pixels; `apex` = the minimum of those rows.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
W, H = 1920, 1080
BOX = (0.390, 0.450, 0.470, 0.620)
REF_WILLOW = [(690, 703), (695, 685), (705, 670), (718, 658), (728, 643), (740, 628), (750, 612), (762, 605),
              (775, 602), (790, 603), (803, 601), (815, 602), (826, 606), (835, 616), (842, 632), (847, 648),
              (850, 664), (848, 680), (845, 703)]
REF_MASK = ROOT / "renders" / "previews" / "environment" / "p10r2_ref169_willow_mask.png"


def ref_mask():
    im = Image.new("L", (W, H), 0)
    ImageDraw.Draw(im).polygon(REF_WILLOW, fill=255)
    return np.asarray(im) > 127


def load_mask(p):
    a = np.asarray(Image.open(p))
    a = a[..., 3] if a.ndim == 3 else a
    return a > 127


def envelope(m):
    """Row-wise hole fill between the outermost willow pixels of each row (box rows only matter)."""
    e = m.copy()
    for r in range(H):
        xs = np.nonzero(m[r])[0]
        if len(xs) > 1:
            e[r, xs.min():xs.max() + 1] = True
    return e


def box_stats(m):
    x0, y0, x1, y1 = int(BOX[0] * W), int(BOX[1] * H), int(BOX[2] * W), int(BOX[3] * H)
    share = 100.0 * m[y0:y1, x0:x1].mean()
    tops = []
    for c in range(x0, x1):
        col = m[:, c]
        if not col[y0:y1].any():
            continue
        run = col[:-2] & col[1:-1] & col[2:]
        k = int(np.argmax(run))
        if run[k]:
            tops.append(k)
    top = float(np.median(tops)) if tops else float("nan")
    apex = float(min(tops)) if tops else float("nan")
    return share, top, apex, len(tops)


def main(argv):
    rm = ref_mask()
    if "--write-ref-mask" in argv:
        a = np.zeros((H, W, 4), dtype=np.uint8)
        a[rm] = (255, 255, 255, 255)
        Image.fromarray(a, "RGBA").save(REF_MASK)
        print(f"wrote {REF_MASK}")
    rows = [("ref169 willow (polygon)", None, rm)]
    for a in argv:
        if "=" not in a:
            continue
        lab, _, p = a.partition("=")
        rows.append((lab, p, load_mask(p)))
    print(f"box x {BOX[0]}-{BOX[2]} y {BOX[1]}-{BOX[3]} (cam-01 1920x1080; rows {int(BOX[1] * H)}-{int(BOX[3] * H)})")
    print(f"{'frame':28s} {'own%':>6s} {'env%':>6s} {'top px':>7s} {'top y':>6s} {'apex':>5s} {'cols':>5s}")
    out = {}
    for lab, _p, m in rows:
        s_own, top, apex, n = box_stats(m)
        s_env = box_stats(envelope(m))[0]
        out[lab] = dict(own=s_own, env=s_env, top=top, apex=apex, cols=n)
        print(f"{lab:28s} {s_own:6.1f} {s_env:6.1f} {top:7.0f} {top / H:6.3f} {apex:5.0f} {n:5d}")
    return out


if __name__ == "__main__":
    main(sys.argv[1:])
