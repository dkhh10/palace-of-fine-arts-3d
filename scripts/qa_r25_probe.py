#!/usr/bin/env python3
"""QA round 25 (the Phase 9 gate on deploy 13) probe.  No Blender, no Chrome.

An EXTENSION of `scripts/qa_r24_probe.py` (-> r23 -> ... -> r13): every carried measure is the one
the earlier rounds used, retargeted to `gate13` (before = `gate12`).  What is new is the Phase 9
comparison set: the AFTER Cycles refs `renders/qa_comparisons/cycles_p9/cam0N_1080_32spp.png` are
FULL RESOLUTION, so parity is measured at 1920x1080 and not only on the 960 px grid.

    python3 scripts/qa_r25_probe.py parity     # viewer gate13 vs cycles p9 (and vs p8) per station
    python3 scripts/qa_r25_probe.py shade02    # station 2's shaded shafts: b* / h_ab / R-B, 4 ways
    python3 scripts/qa_r25_probe.py col03      # station 3's near_column + frame/box p10, 3 ways
    python3 scripts/qa_r25_probe.py rim        # the far-crown rim index, gate12 -> gate13
    python3 scripts/qa_r25_probe.py counters   # the capture's own modulation / re-lit counters
    python3 scripts/qa_r25_probe.py regress | fartree3 | belt3 | crossings | shrubs | boxes |
                                    payload | netdiff | perf | mobile | mobdiff | names | all
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_r24_probe as P24  # noqa: E402
import qa_r23_probe as P23  # noqa: E402
import qa_r22_probe as P22  # noqa: E402
import qa_r21_probe as P21  # noqa: E402
import qa_r20_probe as P20  # noqa: E402
import qa_r18b_probe as P18B  # noqa: E402
import light_r19_measure as L19  # noqa: E402

P = P23.P
ROOT = P23.ROOT
WEB = P23.WEB
P9 = ROOT / "renders/qa_comparisons/cycles_p9"
REF062 = ROOT / "reference/photos/raw/ref_062_rotunda_Palace_of_Fine_Arts_View_of_Rotunda_from_north_eas.jpg"

CUR, PREV = "gate13", "gate12"
SHAFTS = ("shade_pier", "shade_pier_r", "shade_arch", "soffit_l", "soffit_r", "shade_frieze")
# the lighting round's own acceptance table (docs/briefs/phase9_light_report.md §1), for reference
LIGHT_R19 = {"shade_pier": 11.26, "shade_pier_r": 5.29, "shade_arch": 8.80,
             "soffit_l": 18.74, "soffit_r": 20.06, "shade_frieze": 23.31}
PHOTO_R19 = {"shade_pier": 14.10, "shade_pier_r": 13.22, "shade_arch": 7.49,
             "soffit_l": 12.83, "soffit_r": 7.93, "shade_frieze": 10.50}
NEAR03 = (900, 150, 1270, 700)   # light_r17 BOXES["03"]["near_column"], the 1280x720 fixture


def _retarget(prev=PREV):
    P24.CUR, P24.PREV = CUR, prev
    P23.CUR, P23.PREV = CUR, prev
    for M in (P20, P21, P22):
        M.CUR, M.PREV = CUR, prev
    P22.ORB, P22.ORB_PREV = f"{CUR}_orbit", f"{prev}_orbit"


def _f(tag, st):
    return P.rgb(str(WEB / f"{tag}_cam{st:02d}.png"))


def _cyc(st, phase=9):
    d = P9 if phase == 9 else ROOT / "renders/qa_comparisons/cycles_p8"
    return P.rgb(str(d / f"cam{st:02d}_1080_32spp.png"))


def _lum(a):
    return (a / 255.0) @ P.LUMA * 255.0


# --------------------------------------------------------------------------- 1. parity, full res
def cmd_parity():
    """Viewer vs the Phase 9 Cycles AFTER refs at 1920x1080, whole frame and outside the Cycles
    shade (luma < 64, the capture reports' definition), with p10 / mean.  gate12 alongside, so the
    size of the whole Phase 9 change and its direction are both on the page."""
    print("== parity: gate13 vs cycles_p9 (1920x1080, whole frame), gate12 for the before ==")
    print(f"{'st':>2s} {'MAE g13 %':>9s} {'MAE g12 %':>9s} {'d':>6s} {'out-shade g13 %':>15s} "
          f"{'sunlit g13 %':>12s} {'p10 g12/g13/cyc':>20s} {'mean g12/g13/cyc':>22s}")
    for st in range(1, 7):
        c, b, a = _cyc(st), _f(PREV, st), _f(CUR, st)
        lc, lb, la = _lum(c), _lum(b), _lum(a)
        shade, sun = lc < 64, lc > 150
        mae = lambda x: 100.0 * float(np.abs(x - c).mean()) / 255.0
        msk = lambda x, m: 100.0 * float(np.abs(x - c)[m].mean()) / 255.0
        print(f"{st:2d} {mae(a):9.3f} {mae(b):9.3f} {mae(a) - mae(b):+6.3f} "
              f"{msk(a, ~shade):15.3f} {msk(a, sun):12.3f} "
              f"{np.percentile(lb, 10):6.1f}/{np.percentile(la, 10):5.1f}/"
              f"{np.percentile(lc, 10):5.1f}  {lb.mean():6.1f}/{la.mean():6.1f}/{lc.mean():6.1f}")
    print("-- the same against the PHASE 8 Cycles refs (did the round move the viewer toward p9?)")
    for st in range(1, 7):
        c8, c9, a, b = _cyc(st, 8), _cyc(st), _f(CUR, st), _f(PREV, st)
        f = lambda x, r: 100.0 * float(np.abs(x - r).mean()) / 255.0
        print(f"{st:2d} g12 v p8 {f(b, c8):6.3f}  g13 v p8 {f(a, c8):6.3f} | "
              f"g12 v p9 {f(b, c9):6.3f}  g13 v p9 {f(a, c9):6.3f}  "
              f"{'toward p9' if f(a, c9) < f(b, c9) else 'away from p9'}")


# ------------------------------------------------------- 2. station 2, the shaded shafts, 4 ways
def _lab02(img_path):
    return L19.measure(str(img_path), cam="02")[1]


def cmd_shade02():
    """b* / h_ab / R-B on light_r16 BOXES['02'], viewer gate12 | viewer gate13 | Cycles p9 | photo.
    The photo column is ref 062 resampled into the cam02 fixture (light_r19_sheet's own panel): a
    COLOUR reference, not the same stone.  Acceptance = light_r19's: b* >= +5, h_ab 40-80, R-B >= +10."""
    import tempfile
    d = Path(tempfile.mkdtemp(prefix="r25_"))
    ph = Image.open(str(REF062)).convert("RGB").resize((1280, 720), Image.LANCZOS)
    ph.save(str(d / "cam02_ref062.png"))
    srcs = [("gate12", WEB / f"{PREV}_cam02.png"), ("gate13", WEB / f"{CUR}_cam02.png"),
            ("cycles p9", P9 / "cam02_1080_32spp.png"), ("ref 062", d / "cam02_ref062.png")]
    m = {k: _lab02(p) for k, p in srcs}
    print("== station 2, the shaded shafts (light_r16 BOXES['02'], stated on the 1280x720 fixture) ==")
    print(f"{'box':14s} " + "".join(f"{k + ' b*':>12s}" for k, _ in srcs)
          + f"{'h_ab g13':>9s}{'R-B g13':>8s}  {'r19 Cycles b*':>13s} verdict(gate13)")
    for k in SHAFTS:
        row = [m[s][k] for s, _ in srcs]
        v = m["gate13"][k]
        acc = "" if k == "shade_frieze" else (
            f"b {'PASS' if v['b'] >= 5 else 'FAIL'} h {'PASS' if 40 <= v['h_ab'] <= 80 else 'FAIL'} "
            f"RB {'PASS' if v['r_minus_b'] >= 10 else 'FAIL'}")
        if k == "shade_frieze":
            acc = f"control, window 9.9-12.9: {'PASS' if 9.9 <= v['b'] <= 12.9 else 'FAIL'}"
        print(f"{k:14s} " + "".join(f"{r['b']:12.2f}" for r in row)
              + f"{v['h_ab']:9.1f}{v['r_minus_b']:8.1f}  {LIGHT_R19[k]:13.2f} {acc}")
    for tag in ("gate12", "gate13", "cycles p9"):
        e = np.mean([abs(m[tag][k]["b"] - m["ref 062"][k]["b"]) for k in SHAFTS])
        e2 = np.mean([abs(m[tag][k]["b"] - PHOTO_R19[k]) for k in SHAFTS])
        print(f"-- mean |b* - photo| over the six boxes, {tag}: {e:.2f} "
              f"(against the r19 report's own photo column: {e2:.2f})")
    print("-- luma / hue of the same boxes (viewer vs Cycles): the shade must not merely re-hue")
    for k in SHAFTS:
        print(f"   {k:14s} " + "  ".join(
            f"{s} L {m[s][k]['L']:5.1f} a {m[s][k]['a']:5.1f}" for s, _ in srcs))


# --------------------------------------------------------- 3. station 3, the near column, 3 ways
def cmd_col03():
    """The r17 `near_column` box and the frame / box p10, gate12 | gate13 | Cycles p9.  8-bit sRGB
    means and the per-channel ratio (the capture report's linear numbers are the input this
    re-measures)."""
    x0, y0, x1, y1 = [int(v * 1.5) for v in NEAR03]
    print("== station 3: near_column (r17 box, x1.5 to frame px) and the frame's dark end ==")
    print(f"{'src':10s} {'R':>7s}{'G':>7s}{'B':>7s} {'box lum':>8s} {'box p10':>8s} {'frame p10':>10s}")
    vals = {}
    for tag, img in (("gate12", _f(PREV, 3)), ("gate13", _f(CUR, 3)), ("cycles p9", _cyc(3))):
        box = img[y0:y1, x0:x1]
        v = box.reshape(-1, 3).mean(0)
        vals[tag] = v
        print(f"{tag:10s} {v[0]:7.2f}{v[1]:7.2f}{v[2]:7.2f} {_lum(box).mean():8.2f} "
              f"{np.percentile(_lum(box), 10):8.2f} {np.percentile(_lum(img), 10):10.2f}")
    c = vals["cycles p9"]
    for tag in ("gate12", "gate13"):
        r = vals[tag] / np.maximum(c, 1e-6)
        print(f"-- {tag}/cycles per channel: R {r[0]:.3f}x G {r[1]:.3f}x B {r[2]:.3f}x")
    print("-- the same box on the PHASE 8 Cycles ref (has the reference itself moved?): "
          + " ".join(f"{v:6.2f}" for v in _cyc(3, 8)[y0:y1, x0:x1].reshape(-1, 3).mean(0)))


# ------------------------------- 3b. the far-tree carry: re-scored against the PHASE 9 references
def cmd_fartree9():
    """QA 23's brightness question, re-asked against the AFTER reference.  The re-bake moved the
    far-tree population's mean irradiance +33.6 % (docs/briefs/phase9_rebake_report.md), so the
    QA-21 far-crown boxes must be scored against `cycles_p9`, not against gate10's level."""
    print("== the far-tree carry: QA-21 far-crown boxes, gate12 | gate13 | cycles p9 (960 px) ==")
    print(f"{'crown':26s} {'st':>2s} {'g12':>7s} {'g13':>7s} {'cyc p9':>7s} {'g12/cyc':>8s} "
          f"{'g13/cyc':>8s} {'closer?':>8s}")
    dv = {PREV: [], CUR: []}
    better = 0
    for name, st, box, _why in P21.SKY_CROWNS:
        hb = P23._half(box)
        c9 = P23._960(_cyc(st).astype(np.uint8))
        lc = P23._bd(c9, hb)["lum"]
        l = {t: P23._bd(P23._f960(t, st), hb)["lum"] for t in (PREV, CUR)}
        for t in l:
            dv[t].append(abs(l[t] / max(lc, 1e-6) - 1.0))
        ok = dv[CUR][-1] < dv[PREV][-1]
        better += 1 if ok else 0
        print(f"{name:26s} {st:>2} {l[PREV]:7.3f} {l[CUR]:7.3f} {lc:7.3f} "
              f"{l[PREV] / max(lc, 1e-6):7.3f}x {l[CUR] / max(lc, 1e-6):7.3f}x "
              f"{'closer' if ok else 'FURTHER':>8s}")
    for t in (PREV, CUR):
        print(f"-- mean |viewer/cycles_p9 - 1| at {t}: {100 * float(np.mean(dv[t])):.1f} %")
    print(f"-- boxes closer to the Phase 9 reference at gate13: {better}/{len(dv[CUR])}")


# ------------------------------------------------------------------------ 4. the far-crown rim
def cmd_rim():
    out = subprocess.run([sys.executable, str(ROOT / "web/tools/p9v_rim.py"), "ab", PREV, CUR],
                         capture_output=True, text=True, cwd=str(ROOT))
    print(out.stdout.strip() or out.stderr.strip())


# ------------------------------------------------------- 5. the capture's own counters / errors
def cmd_counters():
    for tag in (f"{CUR}_cam", f"{CUR}m_cam", f"{CUR}_orbit"):
        p = WEB / f"{tag}.json"
        if not p.exists():
            print(f"[counters] MISSING {p.name}")
            continue
        d = json.loads(p.read_text())
        log = d.get("pageLog") or []
        keys = ("modulation", "re-lit", "billboard", "impostor", "lightmap", "coverage mask")
        seen = []
        for ln in log:
            t = ln if isinstance(ln, str) else json.dumps(ln)
            if any(k in t for k in keys) and t not in seen:
                seen.append(t)
        print(f"== {p.name}: pageErrors {len(d.get('pageErrors') or [])} "
              f"{(d.get('pageErrors') or [])[:2]}; {len(log)} log line(s) ==")
        for t in seen:
            print("   " + t[:190])


def cmd_all():
    for fn in (cmd_parity, cmd_shade02, cmd_col03, cmd_rim, cmd_counters):
        fn()
        print()
    for name in ("fartree3", "belt3", "crossings", "regress", "shrubs", "boxes", "payload",
                 "netdiff", "perf", "mobile", "mobdiff", "names"):
        _retarget()
        getattr(P24, "cmd_" + name)()
        print()


if __name__ == "__main__":
    P.select_round("18")
    CMDS = {"parity": cmd_parity, "shade02": cmd_shade02, "col03": cmd_col03, "rim": cmd_rim,
            "counters": cmd_counters, "all": cmd_all}
    for a in (sys.argv[1:] or ["all"]):
        if a in CMDS:
            CMDS[a]()
        else:
            _retarget()
            getattr(P24, "cmd_" + a)()
