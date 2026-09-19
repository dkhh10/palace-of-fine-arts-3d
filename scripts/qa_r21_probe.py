#!/usr/bin/env python3
"""QA round 21 (Phase 8 item 8b, the BAND atlas) measurement probe.

No Blender, no Chrome. An EXTENSION of `scripts/qa_r20_probe.py` (-> r19 -> r18b -> r18 -> r17 ->
r16 -> r13), so every measure is the one the earlier rounds used; the crossings table comes from
`export/p8_atlas_probe.py viewer` (run as-is, `viewer` mode — the bake report's crown-top / trunk
label swap lives in the ATLAS mode's `bands()` and touches no number here).

    python3 scripts/qa_r21_probe.py crowns   # QA-17 crown boxes at 1/2/5, gate8 -> gate9 -> ref
    python3 scripts/qa_r21_probe.py grid     # the QA-20 ordered dot grid: lattice autocorrelation
    python3 scripts/qa_r21_probe.py willow   # willow-body p99 / clipped-pixel share vs gate8, Cycles
    python3 scripts/qa_r21_probe.py clip     # whole-frame NEW near-white pixels, gate8 -> gate9
    python3 scripts/qa_r21_probe.py shrubs   # the round-20 shrub boxes restated (must not move)
    python3 scripts/qa_r21_probe.py regress | boxes | payload | netdiff | perf | mobile | mobdiff | names
    python3 scripts/qa_r21_probe.py all

`gate9` = the desktop capture on the URL after deploy 9 (the band atlas live, share 0.10);
`gate9m` = its ?tier=mobile pass; before = `gate8` / `gate8m` (round 20). No orbit this round.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_r20_probe as P20  # noqa: E402
import qa_r18b_probe as P18B  # noqa: E402
import qa_r18_probe as P18  # noqa: E402
import qa_r17_probe as P17  # noqa: E402
import qa_r16_probe as P16  # noqa: E402

P = P18.P
ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "renders" / "web"

CUR, PREV = "gate9", "gate8"

# --------------------------------------------------------------------------- the boxes this round
# Far-tree crowns seen against the SKY (or, at 6, against the flat backdrop: the aerial has no sky
# behind its crowns).  These are the QA-20 tile hits — "every far crown against the sky at 100 %".
SKY_CROWNS = [
    ("01 far roofline N", 1, (400, 436, 620, 540), "far trees over the north colonnade roof (QA-17 box)"),
    ("01 far crown S", 1, (1280, 424, 1560, 545), "the south roof-line crowns, sky behind"),
    ("01 hero shore crown", 1, (760, 545, 1000, 690), "the QA-17 hero crown (building behind, control)"),
    ("02 right cypress", 2, (1700, 370, 1900, 660), "the tall cypress at cam02's right edge, sky behind"),
    ("02 fill tree", 2, (700, 660, 1240, 950), "the QA-17 fill crown (building behind, control)"),
    ("05 left crown", 5, (0, 480, 200, 640), "the west crown over the colonnade, sky behind"),
    ("05 right crown", 5, (1390, 590, 1720, 730), "the east crown band, sky behind"),
    ("05 lawn tree crown", 5, (300, 580, 500, 870), "the QA-17 lawn crown (colonnade behind, control)"),
    ("06 NW crown", 6, (40, 90, 250, 330), "the aerial's north-west crowns against the backdrop"),
    ("06 N crown", 6, (790, 50, 960, 200), "the aerial's north crowns against the backdrop"),
]

# The willow bodies.  x fractions are the ones `scripts/env_trees.py` records per placement
# ("ships x 0.340-0.417" etc. — ref-169 screen fractions at cam01), converted at 1920; the y band is
# the QA-17 "01 near tree band" crown band.  cam02's is the (-40, 16) willow ("ships x 0.736-0.787").
WILLOW = [
    ("01 willow L (x.24-.30)", 1, (461, 545, 576, 700)),
    ("01 willow shore W", 1, (653, 545, 801, 700)),
    ("01 willow shore C", 1, (812, 545, 960, 700)),
    ("01 willow shore E", 1, (993, 545, 1148, 700)),
    ("01 willow E (x.62-.68)", 1, (1194, 545, 1304, 700)),
    ("02 willow right", 2, (1413, 700, 1511, 900)),
    ("05 shore crown band", 5, (640, 560, 1280, 860)),
]


def _f(tag, st):
    return P.rgb(str(WEB / f"{tag}_cam{st:02d}.png"))


def _ref(st):
    return P.rgb(P.REF[st][0])


def _lum(a):
    return a @ P.LUMA


# ------------------------------------------------------------------------------------ 8b: crowns
def cmd_crowns():
    """The QA-17 crown boxes, gate8 -> gate9, against the Cycles reference (r20's measure)."""
    P20.CUR, P20.PREV = CUR, PREV
    P20.cmd_crowns()


def cmd_shrubs():
    """The round-20 shrub boxes restated: the band touches no shrub, so nothing here may move."""
    P20.CUR, P20.PREV = CUR, PREV
    P20.cmd_shrubs()


# --------------------------------------------------------------------- the QA-20 ordered dot grid
def _boxblur(a, k):
    """Mean over a k x k window, k odd, edges replicated (no scipy on this machine)."""
    p = k // 2
    b = np.pad(a, p, mode="edge")
    c = np.cumsum(np.cumsum(b, 0), 1)
    c = np.pad(c, ((1, 0), (1, 0)))
    h, w = a.shape
    return (c[k:k + h, k:k + w] - c[0:h, k:k + w] - c[k:k + h, 0:w] + c[0:h, 0:w]) / (k * k)


def _acf(h, lag, axis):
    """Normalised autocorrelation of the high-pass residual at `lag` along `axis`."""
    if axis == 1:
        a, b = h[:, :-lag], h[:, lag:]
    else:
        a, b = h[:-lag, :], h[lag:, :]
    v = float((h * h).mean())
    return float((a * b).mean()) / max(v, 1e-9)


PERIODS = (2, 3, 4)
LAGS = tuple(range(1, 9))


def grid_index(rgb, box):
    """How strongly an ORDERED LATTICE sits in the box's high-pass residual.

    The QA-20 defect is the coverage share spending one alpha constant over a block of screen pixels
    (a texel): a lattice whose period is the texel's screen size — 2 px on the 2K atlas at these
    stations, ~1 px on the band's 341 px frames.  Natural foliage detail gives a monotonically
    decaying autocorrelation, so for every candidate period p the excess

        mean(acf at multiples of p) - mean(acf at the other lags in 1..8)

    is ~0; a lattice makes it clearly positive at its own p.  The index is that excess (x100), taken
    at the worst p, per axis and as the axes' mean; the Cycles reference is the negative control and
    the gate8 capture (share 0.15, the defect QA 20 saw at 100 %) the positive one.
    """
    x0, y0, x1, y1 = box
    lum = _lum(rgb[y0:y1, x0:x1].astype(np.float32))
    h = lum - _boxblur(lum, 7)
    out = {}
    for ax, tag in ((1, "x"), (0, "y")):
        c = {L: _acf(h, L, ax) for L in LAGS}
        best, bp = -9e9, 0
        for p in PERIODS:
            on = [c[L] for L in LAGS if L % p == 0]
            off = [c[L] for L in LAGS if L % p]
            e = 100.0 * (float(np.mean(on)) - float(np.mean(off)))
            if e > best:
                best, bp = e, p
        out[f"grid_{tag}"], out[f"p_{tag}"], out[f"acf_{tag}"] = best, bp, c
    out["grid"] = 0.5 * (out["grid_x"] + out["grid_y"])
    out["period"] = out["p_x"] if out["grid_x"] >= out["grid_y"] else out["p_y"]
    out["hp_std"] = float(h.std())
    return out


def cmd_grid():
    """gate8 (share 0.15 on the 2K atlas = the known positive) -> gate9 (band, share 0.10),
    with the Cycles reference as the negative control."""
    print(f"== the ordered dot grid: period-3 autocorrelation of the high-pass residual, "
          f"{PREV} -> {CUR}, Cycles as the control ==")
    print(f"{'crown box':22s} {'st':>2s} {'frame':8s} {'grid x':>7s} {'grid y':>7s} {'grid':>7s} "
          f"{'period':>6s} {'hp std':>7s}")
    rows = []
    for name, st, box, _why in SKY_CROWNS:
        per = {}
        for lbl, tag in ((PREV, PREV), (CUR, CUR), ("cycles", None)):
            g = grid_index(_f(tag, st) if tag else _ref(st), box)
            per[lbl] = g
            print(f"{name if lbl == PREV else '':22s} {st if lbl == PREV else '':>2} {lbl:8s} "
                  f"{g['grid_x']:7.2f} {g['grid_y']:7.2f} {g['grid']:7.2f} "
                  f"{g['period']:6d} {g['hp_std']:7.2f}")
        rows.append((name, per))
    print("-- lattice index (x100 of residual variance) at the worst period of 2/3/4; the Cycles "
          "column is the negative control and gate8 (share 0.15) the positive one")
    for lbl in (PREV, CUR, "cycles"):
        v = [r[1][lbl]["grid"] for r in rows]
        cyc = [r[1]["cycles"]["grid"] for r in rows]
        over = sum(1 for x, c in zip(v, cyc) if x > c + 5.0)
        worst = rows[int(np.argmax(v))][0]
        print(f"   {lbl:8s} mean {np.mean(v):6.2f}  max {np.max(v):6.2f} ({worst})  "
              f"boxes more than 5 above their Cycles control: {over}/{len(v)}")


# ----------------------------------------------------------------------------- willow highlights
def cmd_willow():
    """The bake shipped the band at the OCTAHEDRAL range; the willows' own p99.9 is 3.1x higher and
    1.62 % of their opaque body texels clip.  If that shows, the willow body's bright tail rises and
    flattens: p99 / p99.9 up, and a spike of pixels at the top of the range."""
    print(f"== willow bodies: the bright tail, {PREV} -> {CUR}, against Cycles ==")
    print(f"{'willow box':24s} {'st':>2s} {'frame':8s} {'mean':>7s} {'p90':>7s} {'p99':>7s} "
          f"{'p99.9':>7s} {'max':>6s} {'>235 %':>8s} {'>245 %':>8s} {'flat%':>7s} {'chg%':>6s}")
    for name, st, box in WILLOW:
        x0, y0, x1, y1 = box
        ca, cb = _f(PREV, st)[y0:y1, x0:x1], _f(CUR, st)[y0:y1, x0:x1]
        chg = 100.0 * (np.abs(ca.astype(np.int32) - cb.astype(np.int32)).max(2) > 0).mean()
        for lbl, tag in ((PREV, PREV), (CUR, CUR), ("cycles", None)):
            a = (_f(tag, st) if tag else _ref(st))[y0:y1, x0:x1].astype(np.float32)
            lum = _lum(a)
            # "flat" = near-white pixels whose 3x3 neighbourhood is within 2/255 of them: the
            # signature of a clipped patch as opposed to a specular glint.
            hi = lum > 235
            flat = hi & (np.abs(lum - _boxblur(lum, 3)) < 2.0)
            print(f"{name if lbl == PREV else '':24s} {st if lbl == PREV else '':>2} {lbl:8s} "
                  f"{lum.mean():7.2f} {np.percentile(lum, 90):7.1f} {np.percentile(lum, 99):7.1f} "
                  f"{np.percentile(lum, 99.9):7.1f} {lum.max():6.1f} {100 * hi.mean():7.3f}% "
                  f"{100 * (lum > 245).mean():7.3f}% {100 * flat.mean():6.3f}% "
                  f"{chg if lbl == CUR else float('nan'):5.1f}%")


def cmd_clip():
    """Whole-frame: pixels that are near-white in gate9 and were NOT in gate8 (and the reverse),
    with the largest clusters located, so a new blown highlight cannot hide outside a named box."""
    print(f"== new near-white pixels (lum > 240) {PREV} -> {CUR}, whole frame ==")
    print(f"{'st':>2s} {'g8 >240 %':>10s} {'g9 >240 %':>10s} {'new px':>8s} {'gone px':>8s} "
          f"{'largest new cluster (x0,y0,x1,y1, n)':>44s}")
    for st in range(1, 7):
        a, b = _lum(_f(PREV, st)), _lum(_f(CUR, st))
        new = (b > 240) & (a <= 240)
        gone = (a > 240) & (b <= 240)
        loc = "-"
        ys, xs = np.nonzero(new)
        if len(xs):
            # coarse 32 px cluster histogram; report the densest cell's extent
            hgram, _, _ = np.histogram2d(ys, xs, bins=[np.arange(0, 1081, 32), np.arange(0, 1921, 32)])
            iy, ix = np.unravel_index(int(np.argmax(hgram)), hgram.shape)
            loc = f"({ix * 32},{iy * 32},{ix * 32 + 32},{iy * 32 + 32}, {int(hgram[iy, ix])})"
        print(f"{st:2d} {100 * (a > 240).mean():9.4f}% {100 * (b > 240).mean():9.4f}% "
              f"{int(new.sum()):8d} {int(gone.sum()):8d} {loc:>44s}")


# ---------------------------------------------------------------------------------- the r20 suite
def _delegate(fn):
    P20.CUR, P20.PREV = CUR, PREV
    fn()


def cmd_regress():
    _delegate(P20.cmd_regress)


def cmd_boxes():
    _delegate(P20.cmd_boxes)


def cmd_payload():
    _delegate(P20.cmd_payload)


def cmd_netdiff():
    _delegate(P20.cmd_netdiff)


def cmd_perf():
    _delegate(P20.cmd_perf)
    # the resident correction QA 20 asked for: the counter omits the impostor atlases.
    cur = json.loads((WEB / f"{CUR}_perf.json").read_text())["stations"][0]["resident"]
    tot = cur["total_bytes"] / 1e6
    print(f"-- resident sidecar {tot:.1f} MB; ESTIMATE with the impostor atlases the counter omits: "
          f"{tot:.1f} + 67 (band) + 48 (2K octahedral) = {tot + 115:.1f} MB")


def cmd_mobile():
    P18B.cmd_mobile(f"{CUR}m")
    print()
    P18B.cmd_canvas(f"{CUR}m")


def cmd_mobdiff():
    _delegate(P20.cmd_mobdiff)
    print(f"== mobile frames: is {CUR}m byte-identical to {PREV}m? ==")
    for st in range(1, 7):
        a = P.rgb(str(WEB / f"{CUR}m_cam{st:02d}.png")).astype(np.int32)
        b = P.rgb(str(WEB / f"{PREV}m_cam{st:02d}.png")).astype(np.int32)
        d = np.abs(a - b)
        print(f"   station {st}: MAE {d.mean():.5f}, max |d| {d.max():3d}, "
              f"pixels differing {100 * (d.max(2) > 0).mean():.4f}% "
              f"{'IDENTICAL' if d.max() == 0 else ''}")
    for tag in (f"{CUR}m", f"{PREV}m"):
        cam = json.loads((WEB / f"{tag}_cam.json").read_text())
        r = cam["perStation"][0].get("resident") or {}
        print(f"   {tag} resident {(r.get('total_bytes') or 0) / 1e6:.1f} MB")


def cmd_names():
    P18B.cmd_names()


def cmd_all():
    for fn in (cmd_regress, cmd_crowns, cmd_grid, cmd_willow, cmd_clip, cmd_shrubs, cmd_boxes,
               cmd_payload, cmd_netdiff, cmd_perf, cmd_mobile, cmd_mobdiff, cmd_names):
        fn()
        print()


if __name__ == "__main__":
    P.select_round("18")
    for a in (sys.argv[1:] or ["all"]):
        {"regress": cmd_regress, "crowns": cmd_crowns, "grid": cmd_grid, "willow": cmd_willow,
         "clip": cmd_clip, "shrubs": cmd_shrubs, "boxes": cmd_boxes, "payload": cmd_payload,
         "netdiff": cmd_netdiff, "perf": cmd_perf, "mobile": cmd_mobile, "mobdiff": cmd_mobdiff,
         "names": cmd_names, "all": cmd_all}[a]()
