#!/usr/bin/env python3
"""QA round 23 (Phase 8 closing round: 8d belt r2, the far-tree irradiance re-bake, and the
8a/8e/fix-round regression) measurement probe.  No Blender, no Chrome.

An EXTENSION of `scripts/qa_r22_probe.py` (-> r21 -> r20 -> r19 -> r18b -> r18 -> r17 -> r16 ->
r13): every carried measure is the one the earlier rounds used and only the new ones are here.

    python3 scripts/qa_r23_probe.py refcheck   # the Phase 8 Cycles refs vs the Phase 5 refs
    python3 scripts/qa_r23_probe.py belt       # 8d r2: the belt bands vs the PHASE 8 Cycles refs
    python3 scripts/qa_r23_probe.py fartree    # the irradiance re-bake: far-tree level at 1/2/5
    python3 scripts/qa_r23_probe.py crossings  # far-crown crossings, gate10 -> gate11
    python3 scripts/qa_r23_probe.py walkup     # 8e: the 2.5 m walk-up close cards
    python3 scripts/qa_r23_probe.py regress | shrubs | orbit | fixround | boxes | payload |
                                    netdiff | perf | mobile | mobdiff | names | grid | seam | all

`gate11` = the desktop capture on the live URL after deploy 11 (belt r2 + the far-tree irradiance
re-bake) | `gate11m` = its ?tier=mobile pass | before = `gate10` / `gate10m` (round 22).

THE TWO REFERENCE SETS (decisions.md "QA 22", brief round-23 deltas).
  * Phase 5 Cycles (`qa_r13_probe.REF`, 1920x1080 PNG) stays the record of the frozen look and is
    the reference for the ARCHITECTURE boxes.
  * Phase 8 Cycles (`renders/qa_comparisons/cycles_p8/`, 1080p / 32 spp from the Phase 8 master) is
    the parity reference at every BACKDROP / BELT box.  **Only the 960 px JPEG copies survive** —
    the full-resolution PNGs are gitignored and the phase8d-env worktree is gone — so every
    Phase 8 comparison in this file is computed at 960x540 on BOTH sides (`_960`), with the boxes
    halved.  Level (luma, saturation) and box MAE are valid there; `hf` and `sd` are reported but
    are not comparable with the 1920 px numbers of earlier rounds, and are labelled `@960`.
  * The Phase 8 refs are 32 spp fixed, so a 1-4 % MAE noise floor at the belt / backdrop boxes is
    expected (the ENV builder's number, merge 3a3a2e4).  Nothing inside that band is a finding.

THE WATER MASK: unchanged from round 22 (the planar reflector is not session-reproducible).
cam01 keeps y < 680, cam05 y < 910, cam06 y < 540; cam02 / 03 / 04 have no water in frame.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_r22_probe as P22  # noqa: E402
import qa_r21_probe as P21  # noqa: E402
import qa_r20_probe as P20  # noqa: E402
import qa_r18b_probe as P18B  # noqa: E402
import qa_r16_probe as P16  # noqa: E402

P = P22.P
ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "renders" / "web"
P8DIR = ROOT / "renders" / "qa_comparisons" / "cycles_p8" / "960"

CUR, PREV = "gate11", "gate10"
WATERLINE = P22.WATERLINE

# --- the boxes this round -----------------------------------------------------------------------
# The belt is the hall-east tree row seen through / behind the colonnade.  Bands picked on the
# delivered gate10/gate11 pair at 100 % (scripts/qa_r23_tiles.py grid), 1920x1080 frame px.
BELT = [
    ("01 belt N (r2c1)", 1, (0, 500, 640, 680), "the QA-22 blocker's worst band"),
    ("01 belt S", 1, (1280, 500, 1900, 680), "the same band at the south end"),
    ("02 belt band R", 2, (960, 600, 1920, 850), "cam02's belt, the QA-22 'row of spikes' tile"),
    ("05 belt band", 5, (0, 620, 1920, 800), "cam05's belt band across the frame"),
    ("06 top row", 6, (0, 0, 1920, 540), "the aerial's backdrop row (R1 only: no belt here)"),
    ("06 city r1c3", 6, (1280, 0, 1920, 540), "the densest city tile"),
    ("06 far field", 6, (0, 0, 640, 300), "the north-west far ground / forest"),
    ("06 far lawn", 6, (640, 300, 1280, 470), "MAT_backdrop_lawn: must not be washed out"),
]
# The nine TRUE architecture boxes (QA 22 §5: the two 'colonnade wall' boxes sample the backdrop
# through the intercolumniation and are not architecture).
ARCH_BOX = [b for b in P.BOXES if not any(k in b[0].lower() for k in
                                          ("tree", "shrub", "reed", "water", "sky", "planting",
                                           "wall", "lawn", "foliage", "crown"))]


def _f(tag, st):
    return P.rgb(str(WEB / f"{tag}_cam{st:02d}.png"))


def _ref5(st):
    return P.rgb(P.REF[st][0])


def _960(a):
    """1920x1080 uint8 -> 960x540 uint8 (the grid the Phase 8 references survive on)."""
    return np.asarray(Image.fromarray(a.astype(np.uint8)).resize((960, 540), Image.LANCZOS))


def _f960(tag, st):
    return _960(_f(tag, st))


def _ref5_960(st):
    return _960(_ref5(st))


def _p8_960(st):
    p = P8DIR / f"cam{st:02d}_960.jpg"
    return np.asarray(Image.open(str(p)).convert("RGB"))


def _half(box):
    return tuple(v // 2 for v in box)


def _bd(rgbimg, box):
    return P22._bd(rgbimg, box)


def _mae(a, b, box):
    x0, y0, x1, y1 = box
    return float(np.abs(a[y0:y1, x0:x1].astype(np.float32)
                        - b[y0:y1, x0:x1].astype(np.float32)).mean())


# ------------------------------------------------- the Phase 8 references: do they hold the look?
def cmd_refcheck():
    print("== the Phase 8 Cycles references vs the Phase 5 ones, at 960 px (both downscaled) ==")
    print("   the brief's condition: the ARCHITECTURE boxes must agree within 1 % "
          "(= MAE < 2.55 / 255); the backdrop is where they are allowed to differ.")
    print(f"{'box':26s} {'st':>2s} {'MAE p5-p8':>10s} {'%':>6s} {'p5 luma':>8s} {'p8 luma':>8s} "
          f"{'p8/p5':>7s}")
    worst = 0.0
    for name, st, box, _why in ARCH_BOX:
        a, b = _ref5_960(st), _p8_960(st)
        hb = _half(box)
        m = _mae(a, b, hb)
        la, lb = _bd(a, hb)["lum"], _bd(b, hb)["lum"]
        worst = max(worst, m / 2.55)
        print(f"{name:26s} {st:>2} {m:10.2f} {m / 2.55:5.2f}% {la:8.3f} {lb:8.3f} "
              f"{lb / max(la, 1e-6):6.3f}x")
    print(f"-- worst architecture box {worst:.2f} % (rule: < 1 %)")
    print("-- the backdrop / belt boxes, where the two sets are EXPECTED to differ:")
    for name, st, box, _why in BELT:
        a, b = _ref5_960(st), _p8_960(st)
        hb = _half(box)
        print(f"{name:26s} {st:>2} {_mae(a, b, hb):10.2f} {_mae(a, b, hb) / 2.55:5.2f}% "
              f"{_bd(a, hb)['lum']:8.3f} {_bd(b, hb)['lum']:8.3f}")
    print("-- whole-frame MAE, Phase 5 vs Phase 8 reference, per station:")
    for st in range(1, 7):
        a, b = _ref5_960(st), _p8_960(st)
        print(f"   cam{st:02d}: {np.abs(a.astype(np.float32) - b.astype(np.float32)).mean():6.2f} "
              f"({np.abs(a.astype(np.float32) - b.astype(np.float32)).mean() / 2.55:.2f} %)")


# ------------------------------------------------------------------------- 8d r2: the belt, PARITY
def cmd_belt():
    print(f"== 8d r2: the belt / backdrop bands, {PREV} -> {CUR}, PARITY vs the PHASE 8 Cycles "
          f"references (32 spp: a 1-4 % MAE noise floor at these boxes) ==")
    print("   all rows at 960x540 on both sides; hf and sd are @960 and not comparable with the "
          "1920 px numbers of rounds 17-22.")
    print(f"{'box':26s} {'st':>2s} {'frame':10s} {'luma':>7s} {'sat':>7s} {'hf@960':>7s} "
          f"{'sd@960':>7s} {'MAE v p8':>9s} {'%':>6s}")
    for name, st, box, why in BELT:
        hb = _half(box)
        p8 = _p8_960(st)
        for lbl, tag in ((PREV, PREV), (CUR, CUR), ("cycles p8", None), ("cycles p5", "p5")):
            img = p8 if tag is None else (_ref5_960(st) if tag == "p5" else _f960(tag, st))
            b = _bd(img, hb)
            m = _mae(img, p8, hb)
            print(f"{name if lbl == PREV else '':26s} {st if lbl == PREV else '':>2} {lbl:10s} "
                  f"{b['lum']:7.3f} {b['sat']:7.3f} {b['hf']:7.4f} {b['sd']:7.3f} "
                  f"{m:9.2f} {m / 2.55:5.2f}%")
        print(f"{'':26s} ({why})")
    print("-- the same boxes at 1920 px, viewer only (hf / sd comparable with rounds 17-22):")
    print(f"{'box':26s} {'st':>2s} {PREV:>9s} {CUR:>9s} {'d sd':>8s} {PREV + ' hf':>9s} "
          f"{CUR + ' hf':>9s} {'d hf':>9s}")
    for name, st, box, _why in BELT:
        a, b = _bd(_f(PREV, st), box), _bd(_f(CUR, st), box)
        print(f"{name:26s} {st:>2} {a['sd']:9.3f} {b['sd']:9.3f} {b['sd'] - a['sd']:+8.3f} "
              f"{a['hf']:9.4f} {b['hf']:9.4f} {b['hf'] - a['hf']:+9.4f}")


# ----------------------------------------------- the far-tree irradiance re-bake (+48 % modulation)
def cmd_fartree():
    """decisions.md 'Belt export chain r2 merged': the re-bake moved the 127 EXISTING far trees
    (full-mode modulation median 0.942 -> 1.390).  A brightness regression is a blocker (EXPORT).
    Measured on the QA-21 sky-crown boxes (the far crowns) at stations 1, 2, 5, against the
    PHASE 8 Cycles reference, which was rendered from the same Phase 8 master."""
    print(f"== the far-tree irradiance re-bake: the QA-21 far-crown boxes, {PREV} -> {CUR} ==")
    print("   reference = the PHASE 8 Cycles render (same master), at 960 px on both sides.")
    print(f"{'crown':26s} {'st':>2s} {'g10 lum':>8s} {'g11 lum':>8s} {'ratio':>7s} "
          f"{'p8 lum':>8s} {'g11/p8':>7s} {'g10/p8':>7s} {'g11 sat':>8s} {'MAE v p8':>9s}")
    for name, st, box, _why in P21.SKY_CROWNS:
        hb = _half(box)
        p8 = _p8_960(st)
        a, b = _f960(PREV, st), _f960(CUR, st)
        ba, bb, bp = _bd(a, hb), _bd(b, hb), _bd(p8, hb)
        print(f"{name:26s} {st:>2} {ba['lum']:8.3f} {bb['lum']:8.3f} "
              f"{bb['lum'] / max(ba['lum'], 1e-6):6.3f}x {bp['lum']:8.3f} "
              f"{bb['lum'] / max(bp['lum'], 1e-6):6.3f}x {ba['lum'] / max(bp['lum'], 1e-6):6.3f}x "
              f"{bb['sat']:8.3f} {_mae(b, p8, hb):9.2f}")
    print("-- the belt trees themselves (they ship at median 0.24 modulation): the belt boxes, "
          "viewer level vs the Phase 8 Cycles reference")
    for name, st, box, _why in BELT[:4]:
        hb = _half(box)
        p8 = _p8_960(st)
        a, b = _bd(_f960(PREV, st), hb), _bd(_f960(CUR, st), hb)
        bp = _bd(p8, hb)
        print(f"   {name:26s} g10 {a['lum']:.3f} -> g11 {b['lum']:.3f} "
              f"({b['lum'] / max(a['lum'], 1e-6):.3f}x)  cycles p8 {bp['lum']:.3f}  "
              f"g11/p8 {b['lum'] / max(bp['lum'], 1e-6):.3f}x")
    print("-- dark share (luma < 0.20) in each far-crown box: a belt that is too bright "
          "eats the dark crown pixels")
    for name, st, box, _why in P21.SKY_CROWNS:
        hb = _half(box)
        out = []
        for lbl, img in ((PREV, _f960(PREV, st)), (CUR, _f960(CUR, st)), ("p8", _p8_960(st))):
            x0, y0, x1, y1 = hb
            lum = (img[y0:y1, x0:x1].astype(np.float32) / 255.0) @ P.LUMA
            out.append(f"{lbl} {100 * (lum < 0.20).mean():5.2f}%")
        print(f"   {name:26s} " + "  ".join(out))


def cmd_crossings():
    exe = ROOT / "export" / "p8_atlas_probe.py"
    r = subprocess.run([sys.executable, str(exe), "viewer", PREV, CUR, "--stations", "1,2,5"],
                       capture_output=True, text=True, cwd=str(ROOT))
    print(r.stdout[-5000:] or r.stderr[-2000:])


# ----------------------------------------------------------------------- 8e: the 2.5 m walk-up
def cmd_walkup():
    """The frame QA 22 was owed.  The 8e contract line: the close cards must not FATTEN (the leaf
    blades must stay thin).  Same run-width measure as the orbit, read natively."""
    print(f"== 8e: the 2.5 m walk-up on belt tree #19 ({CUR}_walkup_h00000 / _h00900) ==")
    j = json.loads((WEB / f"{CUR}_walkup.json").read_text())
    wp = j.get("walkProbes") or j.get("orbits") or []
    print(f"   capture: size {j.get('size')}, page errors {len(j.get('pageErrors', []))}, "
          f"probes {[(p.get('headingDeg'), p.get('position'), p.get('label')) for p in wp]}")
    for head in ("h00000", "h00900"):
        p = WEB / f"{CUR}_walkup_{head}.png"
        if not p.exists():
            print(f"   {head}: MISSING")
            continue
        a = P22._rgb_native(str(p))
        h, w, _ = a.shape
        # the crown half of the frame (the trunk fills the middle); leaf mask as qa_r22_probe
        for lbl, box in (("upper crown", (0, 0, w, h // 3)),
                         ("mid crown", (0, h // 3, w, 2 * h // 3))):
            x0, y0, x1, y1 = box
            crop = a[y0:y1, x0:x1]
            m = P22._leaf_mask(crop)
            runs = P22._runs(m)
            lum = (crop.astype(np.float32) / 255.0) @ P.LUMA
            if runs.size:
                print(f"   {head} {lbl:12s} {w}x{h}: leaf cover {100 * m.mean():5.2f}%, "
                      f"run width p50 {np.percentile(runs, 50):5.1f} p90 "
                      f"{np.percentile(runs, 90):6.1f} max {runs.max():5.0f} px, "
                      f"luma {lum.mean():.3f}")
            else:
                print(f"   {head} {lbl:12s}: no sunlit-leaf run (cover {100 * m.mean():.2f}%)")
    print("-- the close-orbit crown boxes at 37-45 m for comparison (the 8e gate, "
          f"{P22.ORB_PREV} -> {CUR}_orbit):")


# --------------------------------------------------------------------------- carried, retargeted
def _retarget():
    for M in (P20, P21, P22):
        M.CUR, M.PREV = CUR, PREV
    P22.ORB, P22.ORB_PREV = f"{CUR}_orbit", f"{PREV}_orbit"


def cmd_regress():
    _retarget()
    P22.cmd_regress()
    print("-- MAE against the PHASE 8 Cycles reference (960 px, above the waterline where masked):")
    print(f"{'st':>2s} {'g10 v p8':>9s} {'g11 v p8':>9s} {'d':>7s} {'g10 v p5':>9s} "
          f"{'g11 v p5':>9s} {'d':>7s}")
    for st in range(1, 7):
        y = WATERLINE.get(st)
        ys = (y // 2) if y else 540
        p8, p5 = _p8_960(st)[:ys], _ref5_960(st)[:ys]
        a, b = _f960(PREV, st)[:ys], _f960(CUR, st)[:ys]
        f = lambda x, r: float(np.abs(x.astype(np.float32) - r.astype(np.float32)).mean())
        print(f"{st:2d} {f(a, p8):9.2f} {f(b, p8):9.2f} {f(b, p8) - f(a, p8):+7.2f} "
              f"{f(a, p5):9.2f} {f(b, p5):9.2f} {f(b, p5) - f(a, p5):+7.2f}")


def _d(fn):
    _retarget()
    fn()


def cmd_shrubs():
    _d(P20.cmd_shrubs)


def cmd_orbit():
    _d(P22.cmd_orbit)


def cmd_fixround():
    _d(P22.cmd_fixround)


def cmd_seam():
    _d(P22.cmd_seam)


def cmd_crowns():
    _d(P20.cmd_crowns)


def cmd_grid():
    _d(P21.cmd_grid)


def cmd_boxes():
    _d(P20.cmd_boxes)


def cmd_payload():
    _d(P20.cmd_payload)


def cmd_netdiff():
    _d(P20.cmd_netdiff)


def cmd_perf():
    _d(P20.cmd_perf)


def cmd_mobile():
    P18B.cmd_mobile(f"{CUR}m")
    print()
    P18B.cmd_canvas(f"{CUR}m")


def cmd_mobdiff():
    _d(P22.cmd_mobdiff)


def cmd_names():
    P18B.cmd_names()


def cmd_all():
    for fn in (cmd_refcheck, cmd_belt, cmd_fartree, cmd_crossings, cmd_walkup, cmd_regress,
               cmd_shrubs, cmd_orbit, cmd_fixround, cmd_seam, cmd_crowns, cmd_grid, cmd_boxes,
               cmd_payload, cmd_netdiff, cmd_perf, cmd_mobile, cmd_mobdiff, cmd_names):
        fn()
        print()


if __name__ == "__main__":
    P.select_round("18")
    CMDS = {"refcheck": cmd_refcheck, "belt": cmd_belt, "fartree": cmd_fartree,
            "crossings": cmd_crossings, "walkup": cmd_walkup, "regress": cmd_regress,
            "shrubs": cmd_shrubs, "orbit": cmd_orbit, "fixround": cmd_fixround, "seam": cmd_seam,
            "crowns": cmd_crowns, "grid": cmd_grid, "boxes": cmd_boxes, "payload": cmd_payload,
            "netdiff": cmd_netdiff, "perf": cmd_perf, "mobile": cmd_mobile, "mobdiff": cmd_mobdiff,
            "names": cmd_names, "all": cmd_all}
    for a in (sys.argv[1:] or ["all"]):
        CMDS[a]()
