#!/usr/bin/env python3
"""Phase 7 (viewer foliage look) measurement probe — items A and B.

No Blender, no Chrome.  It reuses QA 17's own definitions rather than inventing new ones: the crown
boxes, `crown_stats`, `box_stats` and the reference set all come from `scripts/qa_r16_probe.py` in
the MAIN checkout (PFA_QA_ROOT, default the main path), so a Phase 7 number and a QA 17 number are
the same measure.  The CAPTURES are read from this worktree (PFA_VIEWER_WEB), the REFERENCES from
MAIN — nothing in MAIN is written.

    PFA_VIEWER_WEB=renders/web python3 scripts/qa_p7_probe.py crown p7base p7ab
    python3 scripts/qa_p7_probe.py edge  p7base p7ab       # hard-edge share and halo share
    python3 scripts/qa_p7_probe.py frame p7base p7ab       # whole-frame luma vs the reference

`<tag>_cam0N.png` is the file each tag names, as every gate script writes it.

THE HALO SHARE, defined here for the first time (QA 17 reported the halo from the tiles, not from a
number).  Inside a crown box: take the leaf mask, dilate it by 3 px and remove the mask itself — that
ring is the pixels immediately OUTSIDE the silhouette.  Take a second band, 4..8 px out, as the local
background (sky, or whatever the crown stands against).  `halo%` is the share of ring pixels whose
luma exceeds that background band's mean by more than 5/255; `halo dL` is the ring's mean luma minus
the background's.  A cut-out with a pale fringe scores high on both, a correctly filtered silhouette
scores near the reference.
"""
import os
import sys
from pathlib import Path

import numpy as np

MAIN = Path(os.environ.get("PFA_QA_ROOT", "/Users/dk/Projects/3d render blender 3rd attempt building"))
sys.path.insert(0, str(MAIN / "scripts"))
import qa_r17_probe  # noqa: E402,F401  (registers round 17 on the shared module)
import qa_r16_probe as P16  # noqa: E402

P = P16.P
HERE = Path(__file__).resolve().parent.parent
VIEW = Path(os.environ.get("PFA_VIEWER_WEB", HERE / "renders/web"))
P.select_round("17")   # only for REF; the captures below are named by tag, not by the round


def img(tag, st):
    """The capture for `tag` at station `st`, or the reference when tag is 'ref'."""
    if tag == "ref":
        return P.rgb(str(P.REF[st][0]))
    return P.rgb(str(VIEW / f"{tag}_cam{st:02d}.png"))


def dilate(mask, k):
    return ~P16._erode(~mask, k)


def halo_stats(crop):
    """(halo %, halo dL) — see the module docstring."""
    m = P16.foliage_mask(crop)
    lum = crop @ P.LUMA
    if m.sum() < 200:
        return None, None
    ring = dilate(m, 3) & ~m
    band = dilate(m, 8) & ~dilate(m, 4)
    if ring.sum() < 100 or band.sum() < 100:
        return None, None
    bg = float(lum[band].mean())
    return float((lum[ring] > bg + 5.0).mean() * 100.0), float(lum[ring].mean() - bg)


def cmd_crown(tags):
    """QA 17 §3's crown table, one row per tag, the reference last."""
    print("== crown boxes (QA 17 §3): interior vs rim, level, p10 ==")
    print(f"{'crown':22s} {'frame':12s} {'leaf%':>6s} {'c/e':>6s} {'p10':>6s} {'p10/ref':>8s} "
          f"{'p90':>6s} {'range/mean':>11s} {'lum':>7s} {'x ref':>6s}")
    for name, st, box in P16.CROWN:
        x0, y0, x1, y1 = box
        ref = img("ref", st)[y0:y1, x0:x1]
        rlum = ref @ P.LUMA
        rp10 = float(np.percentile(rlum, 10))
        rl = float(rlum.mean())
        for tag in list(tags) + ["ref"]:
            crop = img(tag, st)[y0:y1, x0:x1]
            cover, ci, cr, ratio = P16.crown_stats(crop)
            lum = crop @ P.LUMA
            h, w = lum.shape
            cy, cx = h // 4, w // 4
            centre = lum[cy:h - cy, cx:w - cx]
            ring = lum.sum() - centre.sum()
            ce = centre.mean() / max(ring / max(lum.size - centre.size, 1), 1e-6)
            p10, p90 = float(np.percentile(lum, 10)), float(np.percentile(lum, 90))
            rng = (p90 - p10) / max(lum.mean(), 1e-6)
            print(f"{name if tag == tags[0] else '':22s} {tag:12s} {cover:5.1f}% {ce:6.3f} "
                  f"{p10:6.1f} {p10 / max(rp10, 1e-6):7.3f}x {p90:6.1f} {rng:11.3f} "
                  f"{lum.mean():7.1f} {lum.mean() / max(rl, 1e-6):5.2f}x")
        print()


def cmd_edge(tags):
    """Hard-edge share and halo share in the same crown boxes."""
    print("== crown-box edges: hard-edge share (|grad| > 40) and the halo ring ==")
    print(f"{'crown':22s} {'frame':12s} {'hard%':>7s} {'soft':>7s} {'halo%':>7s} {'halo dL':>8s}")
    for name, st, box in P16.CROWN:
        x0, y0, x1, y1 = box
        for tag in list(tags) + ["ref"]:
            a = img(tag, st)
            r = P16.box_stats(a, box)
            hp, hd = halo_stats(a[y0:y1, x0:x1])
            f = lambda v, w=7, d=2: (f"{v:{w}.{d}f}" if v is not None else " " * (w - 1) + "-")  # noqa: E731
            print(f"{name if tag == tags[0] else '':22s} {tag:12s} {r['hard']:6.2f}% {r['soft']:7.2f} "
                  f"{f(hp)}% {f(hd, 8)}")
        print()


def cmd_frame(tags):
    """Whole-frame luma against the reference, every station the tags have a capture for."""
    print("== whole-frame luma / reference ==")
    print(f"{'station':10s} " + " ".join(f"{t:>12s}" for t in tags) + f"{'ref':>10s}")
    for st in range(1, 7):
        row, ok = [], True
        for t in tags:
            p = VIEW / f"{t}_cam{st:02d}.png"
            if not p.exists():
                ok = False
                break
            row.append(float((img(t, st) @ P.LUMA).mean()))
        if not ok:
            continue
        rl = float((img("ref", st) @ P.LUMA).mean())
        print(f"cam{st:02d}      " + " ".join(f"{v:9.2f} {v / rl:.3f}x" for v in row) + f"{rl:10.2f}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "crown"
    tags = sys.argv[2:] or ["p7base"]
    {"crown": cmd_crown, "edge": cmd_edge, "frame": cmd_frame}[cmd](tags)
