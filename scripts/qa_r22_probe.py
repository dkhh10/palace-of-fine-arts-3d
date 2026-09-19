#!/usr/bin/env python3
"""QA round 22 (Phase 8 items 8a relight + 8a-3 shrub-card UV scale, 8d backdrop, 8e mobile leaf
cards, and the viewer fix round) measurement probe.

No Blender, no Chrome.  An EXTENSION of `scripts/qa_r21_probe.py` (-> r20 -> r19 -> r18b -> r18 ->
r17 -> r16 -> r13), so every carried measure is the one the earlier rounds used and only the new
measures are defined here.

    python3 scripts/qa_r22_probe.py shrubs     # 8a/8a-3: the eight QA-17 shrub boxes, gate9 -> gate10
    python3 scripts/qa_r22_probe.py backdrop   # 8d: the backdrop bands, vs Cycles and vs ref 169 / 105
    python3 scripts/qa_r22_probe.py seam       # 8d: tiling / seam autocorrelation on the cam06 city
    python3 scripts/qa_r22_probe.py orbit      # 8e: blade run width and crown coverage, gate7 -> gate10
    python3 scripts/qa_r22_probe.py fixround   # the shrub cull + resident counter
    python3 scripts/qa_r22_probe.py regress    # luma / MAE vs gate9 WITH the above-waterline mask
    python3 scripts/qa_r22_probe.py boxes | payload | netdiff | perf | mobile | mobdiff | names
    python3 scripts/qa_r22_probe.py crowns | grid | all

`gate10` = the desktop capture on the live URL after deploy 10 | `gate10m` = its ?tier=mobile pass |
`gate10_orbit*` = the mobile close orbit (80 m, h 5 m, headings 253 / 215) | before = `gate9` /
`gate9m` (round 21) and `gate7_orbit*` (round 19).

THE WATER MASK (the brief's rule; the planar reflector is not session-reproducible, so no
viewer-vs-viewer pixel claim may include water pixels).  Read off the delivered frames and stated
here once: cam01 keeps y < 680 (the gull/shore line is at y 690), cam05 keeps y < 910 (waterline
y 920), cam06 keeps y < 540 (its top row, which is where 8d lives; the lagoon fills the lower half
and no whole-frame pixel claim is made for it), cam02 / cam03 / cam04 have no water in frame and are
unmasked.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_r21_probe as P21  # noqa: E402
import qa_r20_probe as P20  # noqa: E402
import qa_r19_probe as P19  # noqa: E402
import qa_r18b_probe as P18B  # noqa: E402
import qa_r18_probe as P18  # noqa: E402
import qa_r17_probe as P17  # noqa: E402
import qa_r16_probe as P16  # noqa: E402

P = P18.P
ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "renders" / "web"
REFDIR = ROOT / "reference" / "photos" / "raw"

CUR, PREV = "gate10", "gate9"
ORB, ORB_PREV = "gate10_orbit", "gate7_orbit"

# above-waterline mask: keep rows y < WATERLINE[st] (None = whole frame)
WATERLINE = {1: 680, 2: None, 3: None, 4: None, 5: 910, 6: 540}

# cam-01 render px -> raw ref-169 px, the round-02 align transform (scripts/env_r8_fit.py REF_XF)
REF_XF = (0.7640, 223.2, 0.7667, 97.0)
REF169 = REFDIR / "ref_169_main_Palace_of_Fine_Arts_16794p.jpg"
REF105 = REFDIR / "ref_105_main_Aerial_view_of_The_Palace_of_Fine_Arts.jpg"


def _f(tag, st):
    return P.rgb(str(WEB / f"{tag}_cam{st:02d}.png"))


def _ref(st):
    return P.rgb(P.REF[st][0])


def _lum(a):
    return a @ P.LUMA


def _mask(st, a):
    """Apply the above-waterline mask to a 2-D array (returns the kept rows)."""
    y = WATERLINE.get(st)
    return a if y is None else a[:y]


# ------------------------------------------------------------------------------- 8d: the backdrop
# Boxes from docs/briefs/phase8d_analysis.md §1 ("one band y 524-670, 75 % of it in tile r2c1";
# cam05 "band y 654-786"; cam06 "whole top row").  1920x1080 frame px.
BACKDROP = [
    ("01 N-colonnade band", 1, (0, 524, 640, 670), "the hero's r2c1 backdrop band (8d's target)"),
    ("01 S-colonnade band", 1, (1280, 524, 1900, 670), "the same band at the south end"),
    ("05 backdrop band", 5, (0, 654, 1920, 786), "cam05's backdrop band across r2c1-r2c3"),
    ("06 top row", 6, (0, 0, 1920, 540), "the aerial's whole top row: 34.9-40.3 % backdrop"),
    ("06 city r1c3", 6, (1280, 0, 1920, 540), "the densest city tile (92 % backdrop)"),
    ("06 far field", 6, (0, 0, 640, 300), "the north-west far ground / forest"),
    ("06 far lawn", 6, (640, 300, 1280, 470), "MAT_backdrop_lawn: must not be washed out"),
]


def _bd(rgbimg, box):
    """8d's own three numbers on a box: luma (0-1), per-pixel saturation, |laplacian| (hf), luma sd."""
    x0, y0, x1, y1 = box
    c = rgbimg[y0:y1, x0:x1].astype(np.float32) / 255.0
    lum = c @ P.LUMA
    mx, mn = c.max(2), c.min(2)
    sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    lap = np.abs(4 * lum[1:-1, 1:-1] - lum[:-2, 1:-1] - lum[2:, 1:-1] - lum[1:-1, :-2] - lum[1:-1, 2:])
    return dict(lum=float(lum.mean()), sat=float(sat.mean()), hf=float(lap.mean()),
                sd=float(lum.std()))


def _ref169_crop(box):
    from PIL import Image
    sx, dx, sy, dy = REF_XF
    x0, y0, x1, y1 = box
    r = (int(x0 * sx + dx), int(y0 * sy + dy), int(x1 * sx + dx), int(y1 * sy + dy))
    im = np.asarray(Image.open(str(REF169)).convert("RGB"))
    return im, r


def cmd_backdrop():
    print(f"== 8d: the backdrop bands, {PREV} -> {CUR}, with the Phase 5 Cycles column ==")
    print("   NOTE the Cycles reference PREDATES 8d (it was rendered with the old backdrop "
          "materials), so at these boxes it is the BEFORE state, not the target.")
    print(f"{'box':24s} {'st':>2s} {'frame':8s} {'luma':>7s} {'sat':>7s} {'hf':>7s} {'lum sd':>7s}")
    for name, st, box, why in BACKDROP:
        for lbl, tag in ((PREV, PREV), (CUR, CUR), ("cycles", None)):
            b = _bd(_f(tag, st) if tag else _ref(st), box)
            print(f"{name if lbl == PREV else '':24s} {st if lbl == PREV else '':>2} {lbl:8s} "
                  f"{b['lum']:7.3f} {b['sat']:7.3f} {b['hf']:7.4f} {b['sd']:7.3f}")
        print(f"{'':24s} ({why})")
    # the photographs
    print("-- ref 169 (registered to cam01 by env_r8_fit.REF_XF) on the two hero bands:")
    im, _ = _ref169_crop((0, 0, 1, 1))
    for name, st, box, _why in BACKDROP[:2]:
        sx, dx, sy, dy = REF_XF
        x0, y0, x1, y1 = box
        r = (int(x0 * sx + dx), int(y0 * sy + dy), int(x1 * sx + dx), int(y1 * sy + dy))
        b = _bd(im, r)
        print(f"   {name:24s} ref169 px {r}  luma {b['lum']:.3f} sat {b['sat']:.3f} "
              f"hf {b['hf']:.4f} sd {b['sd']:.3f}")
    print("-- ref 105 (the aerial photograph), city band y 0-300 and y 0-540 of its own 1920x1280:")
    from PIL import Image
    im5 = np.asarray(Image.open(str(REF105)).convert("RGB"))
    for r in ((0, 0, 1920, 300), (0, 0, 1920, 540)):
        b = _bd(im5, r)
        print(f"   ref105 {r}  luma {b['lum']:.3f} sat {b['sat']:.3f} hf {b['hf']:.4f} "
              f"sd {b['sd']:.3f}")


def cmd_seam():
    """A repeated tile or a UV seam on the flat city blocks shows as an ordered lattice in the
    high-pass residual: the QA-21 grid index (qa_r21_probe.grid_index) at its own worst period."""
    print(f"== 8d: tiling / seam lattice on the backdrop, {PREV} -> {CUR} (Cycles = control) ==")
    print(f"{'box':24s} {'st':>2s} {'frame':8s} {'grid x':>7s} {'grid y':>7s} {'grid':>7s} "
          f"{'period':>6s} {'hp std':>7s}")
    for name, st, box, _why in BACKDROP:
        for lbl, tag in ((PREV, PREV), (CUR, CUR), ("cycles", None)):
            g = P21.grid_index(_f(tag, st) if tag else _ref(st), box)
            print(f"{name if lbl == PREV else '':24s} {st if lbl == PREV else '':>2} {lbl:8s} "
                  f"{g['grid_x']:7.2f} {g['grid_y']:7.2f} {g['grid']:7.2f} {g['period']:6d} "
                  f"{g['hp_std']:7.2f}")


# ---------------------------------------------------------------------------- 8e: the mobile orbit
def _runs(mask_row_stack):
    """Lengths of every horizontal run of True in a 2-D boolean array."""
    out = []
    for row in mask_row_stack:
        if not row.any():
            continue
        d = np.diff(np.concatenate(([0], row.view(np.int8), [0])))
        s = np.flatnonzero(d == 1)
        e = np.flatnonzero(d == -1)
        out.append(e - s)
    return np.concatenate(out) if out else np.zeros(0)


def _leaf_mask(crop):
    """Opaque foliage inside a crown box: not sky.  Sky in these frames is blue-dominant and bright
    (B > R by a clear margin); a leaf blade is gold / dark green / black."""
    r, g, b = crop[..., 0].astype(np.int16), crop[..., 1].astype(np.int16), crop[..., 2].astype(np.int16)
    return ~((b > r + 10) & ((crop @ P.LUMA) > 60))


def cmd_orbit():
    """8e: the size of what survives alphaMode MASK on the far-tree cards, measured on the
    DELIVERED close-orbit frames (the export probe measured it on texture + geometry).

    `run p90` is the 90th percentile of the horizontal run length of contiguous non-sky pixels
    inside the crown box -- i.e. the width of a blade / clump as drawn.  `cover` is the non-sky
    share of the box: it must NOT fall (thinning the crowns was the failure mode of kv 2.5).
    """
    print(f"== 8e: far-tree blade runs in the mobile close orbit (80 m, h 5 m), "
          f"{ORB_PREV} -> {ORB} ==")
    print(f"{'crown box':16s} {'heading':8s} {'frame':8s} {'cover %':>8s} {'runs':>8s} "
          f"{'p50':>6s} {'p90':>6s} {'p99':>6s} {'max':>6s} {'mean lum':>9s}")
    for name, tag7, box in P19.ORBIT_BOXES:
        head = tag7.split("_h0")[-1]
        base = {}
        for lbl, tg in (("gate7", tag7), ("gate10", f"{ORB}_h0{head}")):
            p = WEB / f"{tg}.png"
            if not p.exists():
                print(f"{name:16s} MISSING {p.name}")
                continue
            a = P.rgb(str(p))
            x0, y0, x1, y1 = box
            crop = a[y0:y1, x0:x1]
            m = _leaf_mask(crop)
            rn = _runs(m)
            base[lbl] = (100.0 * m.mean(), rn)
            print(f"{name if lbl == 'gate7' else '':16s} {head if lbl == 'gate7' else '':8s} "
                  f"{lbl:8s} {100 * m.mean():7.2f}% {len(rn):8d} "
                  f"{np.percentile(rn, 50):6.1f} {np.percentile(rn, 90):6.1f} "
                  f"{np.percentile(rn, 99):6.1f} {rn.max():6.0f} "
                  f"{float((crop @ P.LUMA).mean()):9.2f}")
        if len(base) == 2:
            c7, c10 = base["gate7"][0], base["gate10"][0]
            p7 = float(np.percentile(base["gate7"][1], 90))
            p10 = float(np.percentile(base["gate10"][1], 90))
            print(f"{'':16s} {'':8s} {'delta':8s} coverage {c10 / max(c7, 1e-6):.3f}x, "
                  f"run p90 {p7:.1f} -> {p10:.1f} px ({p10 - p7:+.1f})")
    print("-- the structure statistics QA 19 recorded on the same boxes, for continuity:")
    P19.cmd_orbit()
    for tag in (ORB,):
        d = json.loads((WEB / f"{tag}.json").read_text())
        print(f"-- {tag}: {len(d.get('pageErrors', []))} page error(s), size {d.get('size')}, "
              f"orbits {[(o['headingDeg'], o['position']) for o in d.get('orbits') or []]}")
        print(f"   walkProbes in the capture: {len(d.get('walkProbes') or [])} "
              f"(the 2.5 m walk-up is NOT in this capture)")


# ------------------------------------------------------------------------------ the viewer fix round
def cmd_fixround():
    """Draws / triangles per station vs gate9 (the shrub cull) and the rewritten resident counter."""
    print(f"== the viewer fix round: draws / triangles per station, {PREV} -> {CUR} ==")
    def st_rows(tag):
        d = json.loads((WEB / f"{tag}_perf.json").read_text())["stations"]
        return {s["station"]: s for s in d}
    a, b = st_rows(PREV), st_rows(CUR)
    print(f"{'st':>2s} {'g9 draws':>9s} {'g10 draws':>10s} {'g9 tris':>12s} {'g10 tris':>12s} "
          f"{'d tris':>12s} {'g9 progs':>9s} {'g10 progs':>10s}")
    for st in range(1, 7):
        print(f"{st:2d} {a[st]['draw_calls']:9d} {b[st]['draw_calls']:10d} "
              f"{a[st]['triangles']:12d} {b[st]['triangles']:12d} "
              f"{b[st]['triangles'] - a[st]['triangles']:+12d} "
              f"{a[st]['programs']:9d} {b[st]['programs']:10d}")
    print("-- expected from the fix round: hero -1 410 000, cam06 -2 020 000 triangles")
    for tag in (PREV, CUR):
        r = json.loads((WEB / f"{tag}_perf.json").read_text())["stations"][0]["resident"]
        print(f"resident {tag:7s} total {r['total_bytes'] / 1e6:8.1f} MB  "
              f"tex {r['texture_bytes'] / 1e6:8.1f}  geo {r['geometry_bytes'] / 1e6:7.1f}  "
              f"rt {r['render_target_bytes'] / 1e6:6.1f}  textures {r['textures']}")
    for tag in (f"{CUR}m", f"{PREV}m"):
        cam = json.loads((WEB / f"{tag}_cam.json").read_text())
        r = (cam["perStation"][0].get("resident") or {})
        print(f"resident {tag:7s} total {(r.get('total_bytes') or 0) / 1e6:8.1f} MB "
              f"(tex {(r.get('texture_bytes') or 0) / 1e6:.1f}, "
              f"geo {(r.get('geometry_bytes') or 0) / 1e6:.1f})")
    # mobile draws / tris
    for tag in (f"{CUR}m", f"{PREV}m"):
        cam = json.loads((WEB / f"{tag}_cam.json").read_text())
        print(f"{tag}: draws {[s.get('draw_calls') for s in cam['perStation']]}  "
              f"tris {[round((s.get('triangles') or 0) / 1e6, 2) for s in cam['perStation']]} M")


# ------------------------------------------------------------------- regression with the water mask
def cmd_regress():
    print(f"== desktop: {CUR} vs {PREV}, ABOVE THE WATERLINE (mask stated in the docstring) ==")
    print(f"{'st':>2s} {'mask':>10s} {'g10 lum':>8s} {'g9 lum':>8s} {'ratio':>7s} {'MAE':>7s} "
          f"{'max|d|':>7s} {'px>1/255 %':>11s} {'MAE ref g10':>12s} {'MAE ref g9':>11s} "
          f"{'g10/ref':>8s}")
    for st in range(1, 7):
        b = _mask(st, _lum(_f(CUR, st)))
        a = _mask(st, _lum(_f(PREV, st)))
        f = _mask(st, _lum(_ref(st)))
        d = np.abs(b - a)
        y = WATERLINE.get(st)
        print(f"{st:2d} {('y<' + str(y)) if y else 'full':>10s} {b.mean():8.3f} {a.mean():8.3f} "
              f"{b.mean() / max(a.mean(), 1e-6):6.4f}x {d.mean():7.4f} {d.max():7.2f} "
              f"{(d > 1).mean() * 100:10.3f}% {np.abs(b - f).mean():12.2f} "
              f"{np.abs(a - f).mean():11.2f} {b.mean() / max(f.mean(), 1e-6):7.3f}x")
    print("-- whole-frame, for the record (stations 1 / 5 / 6 include the planar reflector, which is "
          "not session-reproducible: no pixel claim is made on those rows)")
    P20.CUR, P20.PREV = CUR, PREV
    P20.cmd_regress()


def cmd_crossings():
    """Far-crown crossings per 100 screen px: the QA-21 measure, must hold within 0.3."""
    exe = ROOT / "export" / "p8_atlas_probe.py"
    if not exe.exists():
        print("p8_atlas_probe.py missing")
        return
    r = subprocess.run([sys.executable, str(exe), "viewer", PREV, CUR, "--stations", "1,2,5"],
                       capture_output=True, text=True, cwd=str(ROOT))
    print(r.stdout[-4000:] or r.stderr[-2000:])


# -------------------------------------------------------------------------------- carried measures
def _d(fn):
    P20.CUR, P20.PREV = CUR, PREV
    P21.CUR, P21.PREV = CUR, PREV
    fn()


def cmd_shrubs():
    _d(P20.cmd_shrubs)


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
    print(f"== mobile frames: {CUR}m vs {PREV}m (tier 0; no planar reflector, so unmasked) ==")
    for st in range(1, 7):
        a = P.rgb(str(WEB / f"{CUR}m_cam{st:02d}.png")).astype(np.int32)
        b = P.rgb(str(WEB / f"{PREV}m_cam{st:02d}.png")).astype(np.int32)
        d = np.abs(a - b)
        print(f"   station {st}: MAE {d.mean():.5f}, max |d| {d.max():3d}, "
              f"pixels differing {100 * (d.max(2) > 0).mean():.4f}% "
              f"{'IDENTICAL' if d.max() == 0 else ''}")


def cmd_names():
    P18B.cmd_names()


def cmd_all():
    for fn in (cmd_regress, cmd_shrubs, cmd_backdrop, cmd_seam, cmd_orbit, cmd_fixround,
               cmd_crowns, cmd_grid, cmd_boxes, cmd_payload, cmd_netdiff, cmd_perf, cmd_mobile,
               cmd_mobdiff, cmd_names):
        fn()
        print()


if __name__ == "__main__":
    P.select_round("18")
    CMDS = {"shrubs": cmd_shrubs, "backdrop": cmd_backdrop, "seam": cmd_seam, "orbit": cmd_orbit,
            "fixround": cmd_fixround, "regress": cmd_regress, "crowns": cmd_crowns,
            "grid": cmd_grid, "boxes": cmd_boxes, "payload": cmd_payload, "netdiff": cmd_netdiff,
            "perf": cmd_perf, "mobile": cmd_mobile, "mobdiff": cmd_mobdiff, "names": cmd_names,
            "crossings": cmd_crossings, "all": cmd_all}
    for a in (sys.argv[1:] or ["all"]):
        CMDS[a]()
