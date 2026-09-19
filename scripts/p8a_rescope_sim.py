#!/usr/bin/env python3
"""Phase 8a re-scope — question 2 (second half): WHICH term moves the leaf-green share, and by how much.

No Blender, no Chrome, no rendering. Every number is a simulation ON THE CAPTURED PIXELS: the
candidate change is applied to the shrub-card pixels of the gate9 capture and the QA-17 box probe is
re-run on the result, so a lever's predicted leaf% is directly comparable with the QA table.

    python3 scripts/p8a_rescope_sim.py spread    # the margin's mean AND spread, viewer vs reference
    python3 scripts/p8a_rescope_sim.py levers    # each candidate lever at several strengths, per box
    python3 scripts/p8a_rescope_sim.py solve     # the strength each lever needs to reach 1.00x, per box
    python3 scripts/p8a_rescope_sim.py all

THE CARD MASK. Nothing in a PNG says "this pixel is a card", so the footprint is the union of
(a) the pixels the 8a densification moved between gate7 and gate9 (|dLuma| > 8) and (b) the pixels
that pass the leaf test today. p8a_rescope_boxes.py `decomp` prints its size; it is 1.04-3.6x the
reference's leaf share at all eight boxes, i.e. never the binding constraint.

CAVEAT, stated once. The levers are simulated in display space (the capture is post-LUT). A change
made in Blender or in the viewer happens in scene-linear and then goes through AgX High Contrast,
which compresses and desaturates as it climbs. A display-space gain of g therefore UNDERSTATES the
scene-linear gain needed - the simulation is a lower bound on the change, not a recipe with a number
to type into a shader.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p8a_rescope_boxes as B  # noqa: E402  (boxes, masks, the reference set rooted at MAIN)
import qa_r17_probe as P17  # noqa: E402
import qa_r16_probe as P16  # noqa: E402

P = B.P
CUR, PREV = B.CUR, B.PREV


def card_mask(cur, pv):
    return ((np.abs(cur - pv) @ P.LUMA) > 8.0) | B.leaf(cur)


def metrics(crop):
    """The three QA numbers the brief cares about: leaf%, hard-edge%, mean level."""
    lum = crop @ P.LUMA
    g = P16._grad(lum)
    return (float(B.leaf(crop).mean() * 100.0), float((g > 40.0).mean() * 100.0), float(lum.mean()))


# --------------------------------------------------------------------------- the levers
def lv_green(crop, m, k):
    """Albedo / light green gain: G *= k on the card pixels."""
    out = crop.copy()
    out[..., 1] = np.where(m, np.clip(crop[..., 1] * k, 0, 255), crop[..., 1])
    return out


def lv_warm(crop, m, k):
    """Take the warm cast out: R *= k (k < 1) on the card pixels."""
    out = crop.copy()
    out[..., 0] = np.where(m, np.clip(crop[..., 0] * k, 0, 255), crop[..., 0])
    return out


def lv_sat(crop, m, k):
    """Chroma gain about each pixel's own luma: rgb = L + k (rgb - L)."""
    out = crop.copy()
    lum = (crop @ P.LUMA)[..., None]
    new = np.clip(lum + k * (crop - lum), 0, 255)
    return np.where(m[..., None], new, out)


def lv_level(crop, m, k):
    """A pure level change on the cards (what a brighter / darker card irradiance would do)."""
    out = np.where(m[..., None], np.clip(crop * k, 0, 255), crop)
    return out


def lv_spread(crop, m, k):
    """RESTORE PER-LEAF SHADING SPREAD: expand every card pixel about the card set's own mean,
    k > 1 = a sunlit half and a shaded half instead of one flat average. Level-preserving by
    construction (the mean is the pivot), which is why it does not move the box's level."""
    out = crop.copy()
    if m.sum() == 0:
        return out
    mu = crop[m].mean(0)
    out[m] = np.clip(mu + k * (crop[m] - mu), 0, 255)
    return out


LEVERS = [
    ("green G*k", lv_green, (1.04, 1.08, 1.12, 1.20)),
    ("warm  R*k", lv_warm, (0.96, 0.92, 0.88, 0.80)),
    ("sat   k", lv_sat, (1.2, 1.5, 2.0, 3.0)),
    ("level k", lv_level, (0.85, 0.92, 1.08, 1.20)),
    ("spread k", lv_spread, (1.3, 1.6, 2.0, 3.0)),
]


def _boxes():
    for name, st, box, _why in P17.SHRUB:
        cur = B.crop_of(B.frame(CUR, st), box)
        pv = B.crop_of(B.frame(PREV, st), box)
        rf = B.crop_of(B.ref(st), box)
        yield name, st, cur, pv, rf, card_mask(cur, pv)


# --------------------------------------------------------------------------- 1. spread
def cmd_spread():
    print("== the leaf-test margin over the CARD pixels: mean and spread, viewer vs the reference ==")
    print("   (the reference's own card set is its leaf mask dilated to the same footprint share)")
    print(f"{'box':22s} {'cur mean':>9s} {'ref mean':>9s} {'cur std':>8s} {'ref std':>8s} "
          f"{'std x':>6s} {'cur p90':>8s} {'ref p90':>8s} {'cur skew':>9s} {'ref skew':>9s}")
    for name, st, cur, pv, rf, m in _boxes():
        mc = B.margin(cur)[m]
        share = m.mean()
        mr_all = B.margin(rf)
        thr = np.percentile(mr_all, 100.0 * (1.0 - share))
        mr = mr_all[mr_all >= thr]

        def sk(x):
            s = x.std()
            return float(((x - x.mean()) ** 3).mean() / max(s ** 3, 1e-9))
        print(f"{name:22s} {mc.mean():9.2f} {mr.mean():9.2f} {mc.std():8.2f} {mr.std():8.2f} "
              f"{mr.std()/max(mc.std(),1e-6):5.2f}x {np.percentile(mc,90):8.2f} "
              f"{np.percentile(mr,90):8.2f} {sk(mc):9.2f} {sk(mr):9.2f}")
    print("\n-- a narrower spread at the same mean loses a one-sided threshold test: the reference's")
    print("   card pixels are bimodal (a sunlit half and a shaded half), ours are one flat average,")
    print("   because the viewer replaced the cards' sun diffuse with ONE irradiance per placement.")


# --------------------------------------------------------------------------- 2. levers
def cmd_levers():
    print(f"== each lever applied to the card pixels of {CUR}, box probe re-run (leaf% / hard% / level) ==")
    for name, st, cur, pv, rf, m in _boxes():
        l0, h0, v0 = metrics(cur)
        lr, hr, vr = metrics(rf)
        print(f"\n{name}  (st {st}; now {l0:.1f}% leaf / {h0:.2f}% hard / {v0:.0f} lum; "
              f"ref {lr:.1f}% / {hr:.2f}% / {vr:.0f}; card footprint {m.mean()*100:.0f}%)")
        for lname, fn, ks in LEVERS:
            cells = []
            for k in ks:
                lf, hd, lv = metrics(fn(cur, m, k))
                cells.append(f"k={k:<4g} {lf:5.1f}% ({lf/max(lr,1e-6):4.2f}x) h{hd:5.2f} L{lv/max(vr,1e-6):4.2f}x")
            print(f"   {lname:11s} " + " | ".join(cells))


# --------------------------------------------------------------------------- 3. solve
def _solve(fn, cur, m, target, lo, hi):
    """The smallest strength in [lo, hi] that reaches `target` leaf%, or None."""
    f = lambda k: metrics(fn(cur, m, k))[0]
    a, b = f(lo), f(hi)
    if (a - target) * (b - target) > 0:
        return None
    for _ in range(18):
        mid = 0.5 * (lo + hi)
        if (f(lo) - target) * (f(mid) - target) <= 0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


SOLVE = [("green G*k", lv_green, 1.0, 2.5), ("warm R*k", lv_warm, 1.0, 0.3),
         ("sat k", lv_sat, 1.0, 6.0), ("spread k", lv_spread, 1.0, 6.0)]


def cmd_solve():
    print("== the strength each lever needs to put the box AT the reference's leaf share, and the ==")
    print("== hard-edge share and level it lands on there (hard% must not rise above the reference) ==")
    print(f"{'box':22s} {'ref leaf%':>9s} " + " ".join(f"{n:>26s}" for n, _, _, _ in SOLVE))
    for name, st, cur, pv, rf, m in _boxes():
        lr, hr, vr = metrics(rf)
        cells = []
        for lname, fn, lo, hi in SOLVE:
            k = _solve(fn, cur, m, lr, lo, hi)
            if k is None:
                cells.append(f"{'unreachable':>26s}")
            else:
                _, hd, lv = metrics(fn(cur, m, k))
                cells.append(f"k={k:5.2f} h{hd:5.2f}/{hr:<5.2f} L{lv/max(vr,1e-6):4.2f}x".rjust(26))
        print(f"{name:22s} {lr:8.1f}% " + " ".join(cells))
    print("\n-- h = the hard-edge share the lever lands on / the reference's; L = the box level as a")
    print("   multiple of the reference's. A lever that reaches 1.00x leaf while h stays under the")
    print("   reference and L stays near 1.00x is the one to build.")


# --------------------------------------------------------------------------- 3b. directional relight
def shade_chroma():
    """The chromatic direction of CARD SHADE, from the export's own bake: the ratio between the
    colour a card takes under the darkest decile of the baked irradiance and the colour it takes
    under the mean, normalised to equal luma so only the HUE/SATURATION rotation is left."""
    import p8a_rescope_terms as T  # noqa: E402
    import json
    d = json.loads(T.IRR.read_text())
    a = np.array([x["rgb"] for e in d["meshes"].values() for x in e["placements"]], dtype=np.float64)
    lum = a @ P.LUMA
    lo = a[lum <= np.percentile(lum, 10)].mean(0)
    mu = a.mean(0)
    lo = lo / max(float(lo @ P.LUMA), 1e-9)
    mu = mu / max(float(mu @ P.LUMA), 1e-9)
    return lo / mu                     # per-channel, luma-neutral


def lv_relight(crop, m, f, dark=0.55, chroma=None):
    """PUT THE SUN BACK ON A NORMAL. The flat per-placement irradiance is redistributed: the
    fraction `f` of the card pixels that read darkest today go to SHADE (darkened by `dark` and
    rotated by the bake's own shade chroma), the rest take the light that shade gave up, so the
    card set's mean luma is preserved and the box's level does not move."""
    out = crop.copy()
    if m.sum() == 0:
        return out
    c = crop[m]
    k = shade_chroma() if chroma is None else chroma
    lum = c @ P.LUMA
    thr = np.percentile(lum, 100.0 * f)
    sh = lum <= thr
    new = c.copy()
    new[sh] = c[sh] * dark * k
    lost = float((c[sh] @ P.LUMA).sum() - (new[sh] @ P.LUMA).sum())
    sun = ~sh
    if sun.sum():
        gain = 1.0 + lost / max(float((c[sun] @ P.LUMA).sum()), 1e-9)
        new[sun] = c[sun] * gain
    out[m] = np.clip(new, 0, 255)
    return out


def cmd_relight():
    print("== the directional-relight lever: the same light, redistributed into sun and shade ==")
    print(f"   shade chroma from the bake (luma-neutral): {np.round(shade_chroma(), 3)}")
    print(f"{'box':22s} {'now':>6s} {'ref':>6s} " +
          " ".join(f"{'f='+str(f):>22s}" for f in (0.3, 0.45, 0.6)))
    for name, st, cur, pv, rf, m in _boxes():
        l0, h0, v0 = metrics(cur)
        lr, hr, vr = metrics(rf)
        cells = []
        for f in (0.3, 0.45, 0.6):
            lf, hd, lv = metrics(lv_relight(cur, m, f))
            cells.append(f"{lf:5.1f}% {lf/max(lr,1e-6):4.2f}x h{hd:5.2f} L{lv/max(vr,1e-6):4.2f}x")
        print(f"{name:22s} {l0:5.1f}% {lr:5.1f}% " + " ".join(f"{c:>22s}" for c in cells))
    print("\n-- dark = 0.55 of the flat value in shade; the light removed is given back to the sunlit")
    print("   half, so the box LEVEL (QA 17's one closed shrub item) is held by construction.")


# --------------------------------------------------------------------------- 4. the fitted gain
def cmd_fit():
    """One number for the whole band: the per-channel gain that maps OUR card pixels' mean onto the
    reference's. If the same gain comes out of all eight boxes it is a single constant, not a
    per-station tweak."""
    print("== the per-channel gain that would put our card pixels on the reference's card colour ==")
    print(f"{'box':22s} {'cur card RGB':>24s} {'ref card RGB':>24s} "
          f"{'kR':>6s} {'kG':>6s} {'kB':>6s} {'kG/kR':>7s} {'cur G/R':>8s} {'ref G/R':>8s}")
    ks = []
    for name, st, cur, pv, rf, m in _boxes():
        share = m.mean()
        mr_all = B.margin(rf)
        thr = np.percentile(mr_all, 100.0 * (1.0 - share))
        rc = rf[mr_all >= thr]
        c = cur[m].mean(0)
        r = rc.mean(0)
        k = r / np.maximum(c, 1e-6)
        ks.append(k)
        print(f"{name:22s} {str(np.round(c,1)):>24s} {str(np.round(r,1)):>24s} "
              f"{k[0]:6.3f} {k[1]:6.3f} {k[2]:6.3f} {k[1]/max(k[0],1e-6):7.3f} "
              f"{c[1]/max(c[0],1e-6):8.3f} {r[1]/max(r[0],1e-6):8.3f}")
    k = np.array(ks)
    print(f"{'MEDIAN':22s} {'':>24s} {'':>24s} {np.median(k[:,0]):6.3f} {np.median(k[:,1]):6.3f} "
          f"{np.median(k[:,2]):6.3f} {np.median(k[:,1]/k[:,0]):7.3f}")
    print("\n-- kG/kR > 1 is the warm cast to take out; the level part (the common factor) is the")
    print("   band's brightness, which QA 17 already closed and which must NOT be moved far.")


# --------------------------------------------------------------------------- 5. one global lever
GLOBAL = [("warm R*k", lv_warm, (0.98, 0.95, 0.92, 0.90, 0.88, 0.85)),
          ("green G*k", lv_green, (1.02, 1.05, 1.08, 1.10, 1.12, 1.15)),
          ("G/R split", None, (1.02, 1.04, 1.06, 1.08, 1.10, 1.12))]


def lv_split(crop, m, k):
    """The level-preserving version of both: G *= sqrt(k), R /= sqrt(k) on the card pixels, so the
    chromaticity rotates and the box's luma barely moves."""
    s = np.sqrt(k)
    out = crop.copy()
    out[..., 1] = np.where(m, np.clip(crop[..., 1] * s, 0, 255), crop[..., 1])
    out[..., 0] = np.where(m, np.clip(crop[..., 0] / s, 0, 255), crop[..., 0])
    return out


def cmd_global():
    """ONE constant applied at every box - what a single material / irradiance change really does,
    including to the three boxes that already sit at or above the reference."""
    GLOBAL[2] = ("G/R split", lv_split, GLOBAL[2][2])
    data = list(_boxes())
    refs = [metrics(rf) for _, _, _, _, rf, _ in data]
    for lname, fn, ks in GLOBAL:
        print(f"\n== ONE global {lname} on every shrub card: leaf%/ref per box ==")
        print(f"{'k':>6s} " + " ".join(f"{n[:11]:>11s}" for n, _, _, _, _, _ in data)
              + f" {'mean':>6s} {'in 0.85-1.15':>13s} {'hard>ref':>9s} {'lvl drift':>10s}")
        for k in ks:
            xs, hs, ls = [], 0, []
            for (name, st, cur, pv, rf, m), (lr, hr, vr) in zip(data, refs):
                lf, hd, lv = metrics(fn(cur, m, k))
                xs.append(lf / max(lr, 1e-6))
                hs += 1 if hd > hr else 0
                ls.append(lv / max(vr, 1e-6))
            n_ok = sum(1 for x in xs if 0.85 <= x <= 1.15)
            print(f"{k:6.3f} " + " ".join(f"{x:10.2f}x" for x in xs)
                  + f" {np.mean(xs):5.2f}x {n_ok:8d}/8 {hs:8d}/8 {np.mean(ls):9.2f}x")
    print("\n-- 'hard>ref' counts the boxes whose hard-edge share sits above the reference's (it is")
    print("   already 7/8 today, so the test is that the lever does not make it 8/8 or push it far);")
    print("   'lvl drift' is the mean box level as a multiple of the reference's (today 1.20x).")


def main():
    cmds = {"spread": cmd_spread, "levers": cmd_levers, "solve": cmd_solve, "relight": cmd_relight,
            "fit": cmd_fit, "global": cmd_global}
    for a in (sys.argv[1:] or ["all"]):
        if a == "all":
            for f in (cmd_spread, cmd_fit, cmd_relight, cmd_solve, cmd_global, cmd_levers):
                f()
                print()
        elif a in cmds:
            cmds[a]()
        else:
            print(f"unknown command {a!r}; one of {', '.join(cmds)} or all")


if __name__ == "__main__":
    main()
