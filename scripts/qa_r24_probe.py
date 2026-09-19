#!/usr/bin/env python3
"""QA round 24 (verification of the far-tree irradiance RE-KEY shipped as deploy 12) probe.

No Blender, no Chrome.  A thin EXTENSION of `scripts/qa_r23_probe.py` (-> r22 -> r21 -> ... -> r13):
every carried measure is the one the earlier rounds used; only the three-way comparisons are new.

    python3 scripts/qa_r24_probe.py fartree3   # far-crown level: gate10 | gate11 | gate12 | cycles p8
    python3 scripts/qa_r24_probe.py belt3      # the 39 belt rows: level + dark share, same three
    python3 scripts/qa_r24_probe.py orbit3     # 8e blade run p90: gate10 | gate11 | gate12
    python3 scripts/qa_r24_probe.py regress    # gate11 -> gate12 with the water mask (r23 carried)
    python3 scripts/qa_r24_probe.py crossings | shrubs | fixround | boxes | payload | netdiff |
                                    perf | mobile | mobdiff | names | grid | seam | all

`gate12` = the desktop capture on the live URL after deploy 12 (main aee019c: the 127 existing far
trees re-keyed to the 6c bake bodies, median modulation 0.9415; the 39 belt rows keep the r2 bake,
median 0.2424).  before = `gate11` (round 23, the re-bake) and `gate10` (round 22, pre-re-bake).

The reference sets, the 960 px rule and the water mask are exactly round 23's (see its docstring).
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_r23_probe as P23  # noqa: E402
import qa_r22_probe as P22  # noqa: E402
import qa_r21_probe as P21  # noqa: E402
import qa_r20_probe as P20  # noqa: E402
import qa_r18b_probe as P18B  # noqa: E402

P = P23.P
ROOT = P23.ROOT
WEB = P23.WEB

CUR, PREV, BASE = "gate12", "gate11", "gate10"
TAGS = (BASE, PREV, CUR)


def _retarget(prev=None):
    """Point every inherited module at gate12 (vs `prev`, default the round's PREV = gate11)."""
    prev = prev or PREV
    P23.CUR, P23.PREV = CUR, prev
    for M in (P20, P21, P22):
        M.CUR, M.PREV = CUR, prev
    P22.ORB, P22.ORB_PREV = f"{CUR}_orbit", f"{prev}_orbit"


def _dark(img, box, thr=0.20):
    x0, y0, x1, y1 = box
    lum = (img[y0:y1, x0:x1].astype(np.float32) / 255.0) @ P.LUMA
    return 100.0 * float((lum < thr).mean())


# --------------------------------------------------------------- the far-tree re-key: three-way
def cmd_fartree3():
    """The 127 EXISTING far trees must return to their gate10 level (within 3 %) and to their
    gate10 deviation from the Phase 8 Cycles reference (mean was 6.7 % at gate10, 9.7 % at
    gate11)."""
    print("== the far-tree re-key: the QA-21 far-crown boxes, gate10 | gate11 | gate12 | cycles p8 ==")
    print("   reference = the PHASE 8 Cycles render (same master), 960 px on both sides.")
    print(f"{'crown':26s} {'st':>2s} {'g10':>7s} {'g11':>7s} {'g12':>7s} {'g12/g10':>8s} "
          f"{'p8':>7s} {'g10/p8':>7s} {'g11/p8':>7s} {'g12/p8':>7s}")
    dev = {t: [] for t in TAGS}
    back = 0
    rows = []
    for name, st, box, _why in P21.SKY_CROWNS:
        hb = P23._half(box)
        p8 = P23._p8_960(st)
        lp = P23._bd(p8, hb)["lum"]
        l = {t: P23._bd(P23._f960(t, st), hb)["lum"] for t in TAGS}
        for t in TAGS:
            dev[t].append(abs(l[t] / max(lp, 1e-6) - 1.0))
        ratio = l[CUR] / max(l[BASE], 1e-6)
        back += 1 if abs(ratio - 1.0) <= 0.03 else 0
        rows.append((name, st, l, lp, ratio))
        print(f"{name:26s} {st:>2} {l[BASE]:7.3f} {l[PREV]:7.3f} {l[CUR]:7.3f} {ratio:7.3f}x "
              f"{lp:7.3f} {l[BASE] / max(lp, 1e-6):6.3f}x {l[PREV] / max(lp, 1e-6):6.3f}x "
              f"{l[CUR] / max(lp, 1e-6):6.3f}x")
    print(f"-- boxes back within 3 % of gate10: {back}/{len(rows)}")
    for t in TAGS:
        print(f"-- mean |viewer/cycles - 1| at {t}: {100 * float(np.mean(dev[t])):.1f} %  "
              f"(boxes worse than gate10: "
              f"{sum(1 for i in range(len(rows)) if dev[t][i] > dev[BASE][i] + 1e-9)}/{len(rows)})")
    print("-- dark share (luma < 0.20): the dark cores must come back")
    for name, st, box, _why in P21.SKY_CROWNS:
        hb = P23._half(box)
        out = [f"{t} {_dark(P23._f960(t, st), hb):5.2f}%" for t in TAGS]
        out.append(f"p8 {_dark(P23._p8_960(st), hb):5.2f}%")
        print(f"   {name:26s} " + "  ".join(out))


def cmd_belt3():
    """The 39 belt rows keep the r2 bake (median modulation 0.2424): a SEPARATE population.  They
    must not have moved with the re-key, and they must read as shaded trees, not black cut-outs."""
    print("== the 39 belt rows (r2 bake kept): the belt bands, gate10 | gate11 | gate12 | cycles p8 ==")
    print(f"{'box':26s} {'st':>2s} {'g10':>7s} {'g11':>7s} {'g12':>7s} {'g12/g11':>8s} "
          f"{'p8':>7s} {'g12/p8':>7s} {'MAEv p8':>8s} {'%':>6s}")
    for name, st, box, _why in P23.BELT[:4]:
        hb = P23._half(box)
        p8 = P23._p8_960(st)
        lp = P23._bd(p8, hb)["lum"]
        l = {t: P23._bd(P23._f960(t, st), hb)["lum"] for t in TAGS}
        m = P23._mae(P23._f960(CUR, st), p8, hb)
        print(f"{name:26s} {st:>2} {l[BASE]:7.3f} {l[PREV]:7.3f} {l[CUR]:7.3f} "
              f"{l[CUR] / max(l[PREV], 1e-6):7.3f}x {lp:7.3f} {l[CUR] / max(lp, 1e-6):6.3f}x "
              f"{m:8.2f} {m / 2.55:5.2f}%")
    print("-- belt tone distribution at 100 % (are they shaded trees or black cut-outs?): "
          "share below 0.06 luma = near-black, 0.06-0.25 = shaded foliage, sd of the box")
    for name, st, box, _why in P23.BELT[:4]:
        a = P23._f(CUR, st)
        x0, y0, x1, y1 = box
        lum = (a[y0:y1, x0:x1].astype(np.float32) / 255.0) @ P.LUMA
        p8 = P23._p8_960(st)
        hb = P23._half(box)
        lp = (p8[hb[1]:hb[3], hb[0]:hb[2]].astype(np.float32) / 255.0) @ P.LUMA
        print(f"   {name:26s} g12 black {100 * float((lum < 0.06).mean()):5.2f}%  "
              f"shaded {100 * float(((lum >= 0.06) & (lum < 0.25)).mean()):5.2f}%  "
              f"sd {float(lum.std()):.3f} | p8 black {100 * float((lp < 0.06).mean()):5.2f}%  "
              f"shaded {100 * float(((lp >= 0.06) & (lp < 0.25)).mean()):5.2f}%  "
              f"sd {float(lp.std()):.3f}")


def cmd_orbit3():
    """8e: the blade run p90 on the mobile close-orbit crowns, all three gates."""
    print("== 8e: far-tree blade runs in the mobile close orbit, gate10 | gate11 | gate12 ==")
    print(f"{'crown box':16s} {'heading':8s} " + "".join(f"{t + ' p90':>11s}" for t in TAGS)
          + f"{'g12 cover':>11s}{'cov g12/g10':>12s}")
    p90 = {t: [] for t in TAGS}
    under = {t: 0 for t in TAGS}
    for name, head, box in P22.BLADE_BOXES:
        v, cov = {}, {}
        for t in TAGS:
            p = WEB / f"{t}_orbit_{head}.png"
            if not p.exists():
                print(f"{name:16s} MISSING {p.name}")
                v = {}
                break
            a = P22._rgb_native(p)
            x0, y0, x1, y1 = box
            m = P22._leaf_mask(a[y0:y1, x0:x1])
            rn = P22._runs(m)
            v[t] = float(np.percentile(rn, 90)) if rn.size else float("nan")
            cov[t] = 100.0 * float(m.mean())
        if not v:
            continue
        for t in TAGS:
            p90[t].append(v[t])
            under[t] += 1 if v[t] <= 25 else 0
        print(f"{name:16s} {head:8s} " + "".join(f"{v[t]:10.1f} " for t in TAGS)
              + f"{cov[CUR]:10.2f}%{cov[CUR] / max(cov[BASE], 1e-6):11.3f}x")
    for t in TAGS:
        print(f"-- {t}: run p90 mean {np.mean(p90[t]):.1f} px, boxes at or under 25 px: "
              f"{under[t]}/{len(p90[t])}")


# ------------------------------------------------------------------- carried, retargeted to gate12
def cmd_regress():
    _retarget()
    P23.cmd_regress()


def cmd_crossings():
    _retarget()
    P23.cmd_crossings()


def cmd_shrubs():
    _retarget()
    P20.cmd_shrubs()


def cmd_fixround():
    _retarget()
    P22.cmd_fixround()


def cmd_seam():
    _retarget()
    P22.cmd_seam()


def cmd_grid():
    _retarget()
    P21.cmd_grid()


def cmd_boxes():
    _retarget()
    P20.cmd_boxes()


def cmd_payload():
    _retarget()
    P20.cmd_payload()


def cmd_netdiff():
    _retarget()
    P20.cmd_netdiff()


def cmd_perf():
    _retarget()
    P20.cmd_perf()


def cmd_mobile():
    P18B.cmd_mobile(f"{CUR}m")
    print()
    P18B.cmd_canvas(f"{CUR}m")


def cmd_mobdiff():
    _retarget()
    P22.cmd_mobdiff()


def cmd_names():
    P18B.cmd_names()


def cmd_all():
    for fn in (cmd_fartree3, cmd_belt3, cmd_orbit3, cmd_crossings, cmd_regress, cmd_shrubs,
               cmd_fixround, cmd_seam, cmd_grid, cmd_boxes, cmd_payload, cmd_netdiff, cmd_perf,
               cmd_mobile, cmd_mobdiff, cmd_names):
        fn()
        print()


if __name__ == "__main__":
    P.select_round("18")
    CMDS = {"fartree3": cmd_fartree3, "belt3": cmd_belt3, "orbit3": cmd_orbit3,
            "crossings": cmd_crossings, "regress": cmd_regress, "shrubs": cmd_shrubs,
            "fixround": cmd_fixround, "seam": cmd_seam, "grid": cmd_grid, "boxes": cmd_boxes,
            "payload": cmd_payload, "netdiff": cmd_netdiff, "perf": cmd_perf, "mobile": cmd_mobile,
            "mobdiff": cmd_mobdiff, "names": cmd_names, "all": cmd_all}
    for a in (sys.argv[1:] or ["all"]):
        CMDS[a]()
