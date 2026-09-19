#!/usr/bin/env python3
"""Phase 8a re-scope — question 1: WHAT the shore band is made of at each QA-17 shrub box.

No Blender, no Chrome, no rendering. Pure pixel analysis of captures already on disk.

    python3 scripts/p8a_rescope_boxes.py decomp     # leaf-green gap decomposed: colour / coverage / level
    python3 scripts/p8a_rescope_boxes.py margin     # the G-0.85R margin histogram, viewer vs reference
    python3 scripts/p8a_rescope_boxes.py composition  # what the NON-leaf pixels of each box are
    python3 scripts/p8a_rescope_boxes.py all

The metric under test (`qa_r16_probe.foliage_mask`, unchanged since round 16):

    leaf = (G - 0.85*R > 5) & (B < G)      leaf% = share of box pixels

so it is a *colour* test with an absolute 5/255 margin, applied per pixel. Three things can make
our leaf% fall short of the reference's: (a) COLOUR - our card pixels sit below the margin (too
warm / too gold / too desaturated); (b) COVERAGE - fewer pixels in the box are card at all (water,
ground and stone show through); (c) LEVEL - the margin is absolute, so a darker band clears it less
often at the same chromaticity.  This script separates the three.

`ref` is what every QA round since 13 calls the reference: the Phase 5 Cycles render at that
station (`qa_r13_probe.REF`), not the photograph.  The photograph comparison is a separate axis and
is not what the 8a metric measures.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_r17_probe as P17  # noqa: E402  (registers the shrub boxes; chains to r16 -> r13)
import qa_r16_probe as P16  # noqa: E402

P = P16.P
ROOT = Path(__file__).resolve().parents[1]
MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
WEB = MAIN / "renders" / "web"

CUR, PREV = "gate9", "gate7"          # gate9 = deploy 9 (band atlas live); gate7 = pre-8a
MARGIN, KR = 5.0, 0.85                 # the foliage_mask constants, restated so nothing is hidden

# qa_r13_probe.REF is filled by `P.use(tag)` and is rooted at the repo the script lives in; this
# worktree carries no renders, so the round-14 reference set is rebuilt against the MAIN checkout.
REF = {st: (MAIN / p.relative_to(P.ROOT), lbl) for st, (p, lbl) in P.REF_R14.items()}
P.REF = REF


def frame(tag, st):
    return P.rgb(str(WEB / f"{tag}_cam{st:02d}.png"))


def ref(st):
    return P.rgb(REF[st][0])


def crop_of(a, box):
    x0, y0, x1, y1 = box
    return a[y0:y1, x0:x1]


def margin(crop):
    """The signed distance of each pixel from the leaf test, in 0-255 units."""
    r, g, b = crop[..., 0], crop[..., 1], crop[..., 2]
    return np.minimum(g - KR * r - MARGIN, g - b)


def leaf(crop):
    return margin(crop) > 0.0


def hsv_of(px):
    """(hue deg, sat, value 0-1) of a set of RGB pixels, means over the set."""
    if px.size == 0:
        return float("nan"), float("nan"), float("nan")
    mx, mn = px.max(1), px.min(1)
    v = mx / 255.0
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    h, _ = P.hue_sat(px.mean(0))
    return h, float(s.mean()), float(v.mean())


def sky_water_stone(crop):
    """Coarse composition of the non-leaf pixels. Deliberately crude and stated as such:
    sky   = blue-dominant and bright;  water = blue/neutral and mid;  stone = warm (R > G)."""
    r, g, b = crop[..., 0], crop[..., 1], crop[..., 2]
    lum = crop @ P.LUMA
    nl = ~leaf(crop)
    sky = nl & (b > g) & (lum > 140)
    water = nl & (b >= g * 0.97) & ~sky
    stone = nl & (r > g + 4)
    other = nl & ~sky & ~water & ~stone
    n = crop[..., 0].size
    return {k: float(v.sum()) / n * 100.0 for k, v in
            (("sky", sky), ("water", water), ("stone", stone), ("other", other))}


# ------------------------------------------------------------------ 1. the margin histogram
BINS = [(-1e9, -40), (-40, -20), (-20, -10), (-10, -5), (-5, 0), (0, 10), (10, 30), (30, 1e9)]


def cmd_margin():
    print(f"== the leaf-test margin (G - 0.85R - 5, clipped by G-B), {CUR} vs the Cycles reference ==")
    print("   negative = fails the test; the band just below 0 is what a small green tint would convert.")
    hdr = " ".join(f"{lo:>4.0f}..{hi:<4.0f}".replace("-1000000000", "  -inf").replace("1000000000", "inf")
                   for lo, hi in BINS)
    print(f"{'box':22s} {'frame':6s} {hdr}")
    for name, st, box, _why in P17.SHRUB:
        for lbl, a in ((CUR, frame(CUR, st)), ("ref", ref(st))):
            m = margin(crop_of(a, box)).ravel()
            sh = [float(((m > lo) & (m <= hi)).mean() * 100.0) for lo, hi in BINS]
            print(f"{name:22s} {lbl:6s} " + " ".join(f"{v:9.1f}" for v in sh))
    print("\n-- read: if our mass sits in -10..0 the gap is a small colour push; if it sits below -20")
    print("   the card colour is structurally wrong (or those pixels are not card at all).")


# ------------------------------------------------------------------ 2. the decomposition
def cmd_decomp():
    print(f"== leaf-green gap decomposed per box ({CUR} vs the Cycles reference) ==")
    print(f"{'box':22s} {'st':>2s} {'leaf% cur':>9s} {'ref':>6s} {'x':>5s} "
          f"{'chg%':>6s} {'ceil%':>6s} {'ceil/ref':>8s} {'lum cur':>8s} {'ref':>6s} "
          f"{'leafhue cur':>11s} {'ref':>6s} {'leafsat':>8s} {'ref':>6s} {'leafval':>8s} {'ref':>6s}")
    rows = []
    for name, st, box, _why in P17.SHRUB:
        cur, rf, pv = crop_of(frame(CUR, st), box), crop_of(ref(st), box), crop_of(frame(PREV, st), box)
        lc, lr = leaf(cur), leaf(rf)
        # pixels the 8a card change actually moved: the structural footprint of the cards
        chg = (np.abs(cur - pv) @ P.LUMA) > 8.0
        ceil = (chg | lc)                      # the most leaf% any recolour of the cards could reach
        hc, sc, vc = hsv_of(cur[lc])
        hr, sr, vr = hsv_of(rf[lr])
        r = dict(name=name, st=st, cur=lc.mean() * 100, ref=lr.mean() * 100,
                 chg=chg.mean() * 100, ceil=ceil.mean() * 100,
                 lumc=float((cur @ P.LUMA).mean()), lumr=float((rf @ P.LUMA).mean()),
                 hc=hc, hr=hr, sc=sc, sr=sr, vc=vc, vr=vr)
        rows.append(r)
        print(f"{name:22s} {st:2d} {r['cur']:8.1f}% {r['ref']:5.1f}% {r['cur']/max(r['ref'],1e-6):4.2f}x "
              f"{r['chg']:5.1f}% {r['ceil']:5.1f}% {r['ceil']/max(r['ref'],1e-6):7.2f}x "
              f"{r['lumc']:8.1f} {r['lumr']:6.1f} {hc:11.1f} {hr:6.1f} {sc:8.3f} {sr:6.3f} "
              f"{vc:8.3f} {vr:6.3f}")
    print("\n  chg%  = pixels the 8a densification moved between gate7 and gate9 (the card footprint proxy)")
    print("  ceil% = (card footprint | current leaf) — the leaf% a PERFECT recolour of the cards would give;")
    print("          ceil/ref >= 1 means the gap is COLOUR (enough pixels, wrong chromaticity);")
    print("          ceil/ref <  1 means COVERAGE/SPECIES is the binding term and no tint can close it.")
    return rows


# ------------------------------------------------------------------ 3. non-leaf composition
def cmd_composition():
    print(f"== what the non-leaf pixels are, {CUR} vs reference (crude hue classes, shares of the box) ==")
    print(f"{'box':22s} {'frame':6s} {'leaf%':>6s} {'sky%':>6s} {'water%':>7s} {'stone%':>7s} {'other%':>7s}")
    for name, st, box, _why in P17.SHRUB:
        for lbl, a in ((CUR, frame(CUR, st)), ("ref", ref(st))):
            c = crop_of(a, box)
            comp = sky_water_stone(c)
            print(f"{name:22s} {lbl:6s} {leaf(c).mean()*100:5.1f}% {comp['sky']:5.1f}% "
                  f"{comp['water']:6.1f}% {comp['stone']:6.1f}% {comp['other']:6.1f}%")


def main():
    cmds = {"decomp": cmd_decomp, "margin": cmd_margin, "composition": cmd_composition}
    args = sys.argv[1:] or ["all"]
    for a in args:
        if a == "all":
            for f in (cmd_decomp, cmd_margin, cmd_composition):
                f()
                print()
        elif a in cmds:
            cmds[a]()
        else:
            print(f"unknown command {a!r}; one of {', '.join(cmds)} or all")


if __name__ == "__main__":
    main()
