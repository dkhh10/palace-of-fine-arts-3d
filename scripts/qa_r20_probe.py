#!/usr/bin/env python3
"""QA round 20 (Phase 8 items 8a shrubs / 8b part 1 crowns / 8c column) measurement probe.

No Blender, no Chrome. An EXTENSION of `scripts/qa_r19_probe.py` (-> r18b -> r18 -> r17 -> r16 ->
r13), so every measure is the one the earlier rounds used; the crossings table comes from
`export/p8_atlas_probe.py viewer` (the bake/export tool, run as-is, `viewer` mode — its crown-top /
trunk label swap is in the ATLAS mode's `bands()`, not here).

    python3 scripts/qa_r20_probe.py shrubs    # the QA-17 shrub boxes at 1/2/3/5, gate7 -> gate8 -> ref
    python3 scripts/qa_r20_probe.py crowns    # the QA-17 crown boxes at 1/2/5, gate7 -> gate8 -> ref
    python3 scripts/qa_r20_probe.py column    # cam03 near columns: grain, banding anisotropy, level
    python3 scripts/qa_r20_probe.py regress   # gate8 vs gate7 and vs the reference, six stations
    python3 scripts/qa_r20_probe.py boxes     # every round-13/15/16 box, gate8 vs gate7, >3 % flagged
    python3 scripts/qa_r20_probe.py payload | perf | mobile | mobdiff | names
    python3 scripts/qa_r20_probe.py all

`gate8` = the desktop capture on the URL after deploy 8 | `gate8m` = its ?tier=mobile pass |
before = `gate7` / `gate7m` (round 19). No orbit was captured this round.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_r19_probe as P19  # noqa: E402
import qa_r18b_probe as P18B  # noqa: E402
import qa_r18_probe as P18  # noqa: E402
import qa_r17_probe as P17  # noqa: E402
import qa_r16_probe as P16  # noqa: E402

P = P18.P
ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "renders" / "web"

CUR, PREV = "gate8", "gate7"

# The near-column boxes at station 3, on the two columns the tile review reads at 100 %.
# Shaft only (no capital, no base, no background between shafts).
COLUMN_BOXES = [
    ("03 near col R shaft", 3, (1400, 180, 1800, 840), "the near right shaft, ~1 m from the lens"),
    ("03 near col L shaft", 3, (520, 220, 790, 720), "the near left shaft, ~3 m"),
    ("03 mid col shaft", 3, (300, 260, 430, 700), "a mid-distance shaft, the same material"),
]


def _f(tag, st):
    return P.rgb(str(WEB / f"{tag}_cam{st:02d}.png"))


def _ref(st):
    return P.rgb(P.REF[st][0])


def _frame_ratio(tag, st):
    return float((_f(tag, st) @ P.LUMA).mean()) / max(float((_ref(st) @ P.LUMA).mean()), 1e-6)


# --------------------------------------------------------------------------------- 8a: shrubs
def cmd_shrubs():
    """QA 17 §3's shrub / reed boxes: level (raw and frame-normalised), hard-edge %, leaf-green %.

    The brief's targets: leaf% moves from ~0.5x of the reference toward 1.0x; hard% must not rise
    above the reference; level and hue hold.
    """
    print(f"== 8a: the QA-17 shrub / reed boxes, {PREV} -> {CUR}, against the reference ==")
    print(f"{'box':22s} {'st':>2s} {'g7 lum':>7s} {'g8 lum':>7s} {'ref':>6s} {'g7 x':>6s} {'g8 x':>6s} "
          f"{'g7 fn':>6s} {'g8 fn':>6s} {'g7 leaf%':>9s} {'g8 leaf%':>9s} {'ref':>6s} "
          f"{'g8/ref':>7s} {'g7 hard%':>9s} {'g8 hard%':>9s} {'ref':>6s} {'g7 hue':>7s} {'g8 hue':>7s} {'ref':>6s}")
    rows = []
    for name, st, box, _why in P17.SHRUB:
        ref = P16.box_stats(_ref(st), box)
        a = P16.box_stats(_f(PREV, st), box)
        b = P16.box_stats(_f(CUR, st), box)
        fa, fb = _frame_ratio(PREV, st), _frame_ratio(CUR, st)
        ra = a["lum"] / max(ref["lum"], 1e-6)
        rb = b["lum"] / max(ref["lum"], 1e-6)
        lr = b["cover"] / max(ref["cover"], 1e-6)
        rows.append((name, ra, rb, a["cover"], b["cover"], ref["cover"], lr,
                     a["hard"], b["hard"], ref["hard"]))
        print(f"{name:22s} {st:2d} {a['lum']:7.1f} {b['lum']:7.1f} {ref['lum']:6.1f} "
              f"{ra:5.2f}x {rb:5.2f}x {ra / fa:5.2f}x {rb / fb:5.2f}x "
              f"{a['cover']:8.1f}% {b['cover']:8.1f}% {ref['cover']:5.1f}% {lr:6.2f}x "
              f"{a['hard']:8.2f}% {b['hard']:8.2f}% {ref['hard']:5.2f}% "
              f"{a['hue']:7.1f} {b['hue']:7.1f} {ref['hue']:6.1f}")
    n_up = sum(1 for r in rows if r[4] > r[3])
    n_hard = sum(1 for r in rows if r[8] > r[9])
    print(f"-- leaf% rises at {n_up}/{len(rows)} boxes; hard% above the reference at {n_hard}/{len(rows)}")
    print(f"-- mean leaf%/ref {np.mean([r[6] for r in rows]):.2f}x "
          f"(before {np.mean([r[3] / max(r[5], 1e-6) for r in rows]):.2f}x)")


# --------------------------------------------------------------------------------- 8b: crowns
def cmd_crowns():
    """QA 17's crown boxes: centre/edge, p10, level, leaf%, hard%. Crossings come from the atlas
    probe (`export/p8_atlas_probe.py viewer gate7 gate8 --stations 1,2,5`), quoted in the report."""
    print(f"== 8b: the QA-17 crown boxes, {PREV} -> {CUR}, against the reference ==")
    print(f"{'crown':22s} {'frame':8s} {'leaf%':>6s} {'c/e':>6s} {'p10':>6s} {'p90':>6s} "
          f"{'lum':>7s} {'x ref':>6s} {'hard%':>6s} {'range/mean':>11s}")
    for name, st, box in P16.CROWN:
        ref = P16.box_stats(_ref(st), box)
        for lbl, tag in ((PREV, PREV), (CUR, CUR), ("ref", None)):
            a = _f(tag, st) if tag else _ref(st)
            x0, y0, x1, y1 = box
            crop = a[y0:y1, x0:x1]
            lum = crop @ P.LUMA
            h, w = lum.shape
            cy, cx = h // 4, w // 4
            centre = lum[cy:h - cy, cx:w - cx]
            ring = (lum.sum() - centre.sum()) / max(lum.size - centre.size, 1)
            ce = centre.mean() / max(ring, 1e-6)
            r = P16.box_stats(a, box)
            if lbl == "ref":
                ref = r
            p10, p90 = float(np.percentile(lum, 10)), float(np.percentile(lum, 90))
            print(f"{name if lbl == PREV else '':22s} {lbl:8s} {r['cover']:5.1f}% {ce:6.3f} "
                  f"{p10:6.1f} {p90:6.1f} {r['lum']:7.1f} "
                  f"{r['lum'] / max(ref['lum'], 1e-6) if ref else float('nan'):5.2f}x "
                  f"{r['hard']:5.2f}% {(p90 - p10) / max(lum.mean(), 1e-6):11.3f}")


# -------------------------------------------------------------------------------- 8c: columns
def _dir_energy(lum):
    """Mean |d/dx| and |d/dy| of the box. Vertical streaking (a detail texel running the shaft's
    whole height) shows as dx >> dy; real grain and pores are close to isotropic."""
    dx = np.abs(lum[:, 1:] - lum[:, :-1]).mean()
    dy = np.abs(lum[1:, :] - lum[:-1, :]).mean()
    return float(dx), float(dy)


def cmd_column():
    """8c: the cam03 near columns. `hp9` is the round-13 high-pass std (grain); dx/dy is the
    banding signature (the objxy detail plane streaks vertically, so dx/dy runs high)."""
    print(f"== 8c: cam03 column boxes, {PREV} -> {CUR}, against the reference ==")
    print(f"{'box':22s} {'frame':8s} {'lum':>7s} {'x ref':>6s} {'hp9':>6s} {'x ref':>6s} "
          f"{'mid':>6s} {'dx':>6s} {'dy':>6s} {'dx/dy':>6s} {'sat':>6s} {'hue':>6s}")
    for name, st, box, _why in COLUMN_BOXES:
        x0, y0, x1, y1 = box
        ref = P16.box_stats(_ref(st), box)
        refl = (_ref(st)[y0:y1, x0:x1] @ P.LUMA)
        for lbl, tag in ((PREV, PREV), (CUR, CUR), ("ref", None)):
            a = _f(tag, st) if tag else _ref(st)
            r = P16.box_stats(a, box)
            dx, dy = _dir_energy(a[y0:y1, x0:x1] @ P.LUMA)
            print(f"{name if lbl == PREV else '':22s} {lbl:8s} {r['lum']:7.1f} "
                  f"{r['lum'] / max(ref['lum'], 1e-6):5.2f}x {r['hp9']:6.2f} "
                  f"{r['hp9'] / max(ref['hp9'], 1e-6):5.2f}x {r['mid']:6.2f} "
                  f"{dx:6.2f} {dy:6.2f} {dx / max(dy, 1e-6):6.2f} {r['sat']:6.3f} {r['hue']:6.1f}")
        print(f"{'':22s} (ref hp9 {ref['hp9']:.2f}, ref dx/dy "
              f"{_dir_energy(refl)[0] / max(_dir_energy(refl)[1], 1e-6):.2f})")


# ---------------------------------------------------------------------------------- regression
def cmd_regress():
    print(f"== desktop: {CUR} vs {PREV}, 1920x1080, and both against the reference ==")
    print(f"{'st':>2s} {'g8 lum':>8s} {'g7 lum':>8s} {'ratio':>7s} {'MAE':>7s} {'max|d|':>7s} "
          f"{'px>1/255 %':>11s} {'MAE ref g8':>11s} {'MAE ref g7':>11s} {'g8/ref':>8s} {'g7/ref':>8s}")
    for st in range(1, 7):
        b = _f(CUR, st) @ P.LUMA
        a = _f(PREV, st) @ P.LUMA
        f = _ref(st) @ P.LUMA
        d = np.abs(b - a)
        print(f"{st:2d} {b.mean():8.3f} {a.mean():8.3f} {b.mean() / max(a.mean(), 1e-6):6.4f}x "
              f"{d.mean():7.4f} {d.max():7.2f} {(d > 1).mean() * 100:10.3f}% "
              f"{np.abs(b - f).mean():11.2f} {np.abs(a - f).mean():11.2f} "
              f"{b.mean() / max(f.mean(), 1e-6):7.3f}x {a.mean() / max(f.mean(), 1e-6):7.3f}x")


def cmd_boxes():
    print(f"== boxes: {CUR} vs {PREV} (lum, std, hard-edge %) — >3 % on lum flagged ==")
    print(f"{'box':24s} {'st':>2s} {'g8 lum':>8s} {'g7':>8s} {'ratio':>7s} {'g8 std':>7s} "
          f"{'g7':>7s} {'g8 hard%':>9s} {'g7':>7s} {'ref lum':>8s}  flag")
    flagged = []
    for name, st, box, _why in P18.ALL_BOXES:
        g = P16.box_stats(_f(CUR, st), box)
        r = P16.box_stats(_f(PREV, st), box)
        f = P16.box_stats(_ref(st), box)
        ratio = g["lum"] / max(r["lum"], 1e-6)
        flag = "MOVED" if abs(ratio - 1.0) > 0.03 else ""
        if flag:
            flagged.append((name, round(ratio, 3)))
        print(f"{name:24s} {st:2d} {g['lum']:8.2f} {r['lum']:8.2f} {ratio:6.3f}x {g['std']:7.2f} "
              f"{r['std']:7.2f} {g['hard']:8.2f}% {r['hard']:6.2f}% {f['lum']:8.2f}  {flag}")
    print(f"-- {len(flagged)} box(es) of {len(P18.ALL_BOXES)} move more than 3 %: {flagged}")


# ------------------------------------------------------------------------- payload / perf / mob
def cmd_payload():
    for tag, name in ((f"desktop URL ({CUR})", f"{CUR}_net.json"),
                      (f"mobile URL ({CUR}m)", f"{CUR}m_net.json"),
                      (f"desktop URL ({PREV}, before)", f"{PREV}_net.json"),
                      (f"mobile URL ({PREV}m, before)", f"{PREV}m_net.json")):
        d = json.loads((WEB / name).read_text())
        t = d["viewer_tiers"]
        print(f"== {tag}: {name}")
        print(f"   bytes before first frame {d['bytes_before_first_frame']:,} "
              f"({d['bytes_before_first_frame'] / 1e6:.2f} MB) in "
              f"{d['requests_before_first_frame']} req, {d['time_to_first_frame_s']:.2f} s")
        print(f"   total {d['bytes_total']:,} ({d['bytes_total'] / 1e6:.1f} MB) over "
              f"{d['requests_n']} req, all tiers {d['time_to_all_tiers_s']:.2f} s")
        for pt in t["per_tier"]:
            print(f"   tier {pt['tier']}: {pt['bytes'] / 1e6:8.1f} MB in {pt['wall_s']:6.2f} s "
                  f"(planned {pt['planned'] / 1e6:.1f} MB, {pt['glbs']} glb)")
        bad = [r for r in d["requests"] if (r.get("status") or 200) >= 400]
        print(f"   failures {t['failures']}  responses >= 400: {len(bad)} "
              f"{[(r.get('status'), r['url'].split('/')[-1]) for r in bad[:6]]}")
        print()


def cmd_netdiff():
    """Which asset files changed between the two deploys, by URL and size."""
    def rows(name):
        d = json.loads((WEB / name).read_text())
        out = {}
        for r in d["requests"]:
            out[r["url"].split("/assets/")[-1]] = r.get("encodedBytes") or r.get("bytes") or 0
        return out
    a, b = rows(f"{PREV}_net.json"), rows(f"{CUR}_net.json")
    add = sorted(set(b) - set(a))
    rem = sorted(set(a) - set(b))
    chg = sorted(k for k in set(a) & set(b) if a[k] != b[k])
    print(f"== asset diff {PREV} -> {CUR}: {len(add)} new, {len(rem)} gone, {len(chg)} resized ==")
    for k in add:
        print(f"  NEW  {k:70s} {b[k]:>12,}")
    for k in rem:
        print(f"  GONE {k:70s} {a[k]:>12,}")
    for k in chg:
        print(f"  CHG  {k:70s} {a[k]:>12,} -> {b[k]:>12,} ({b[k] - a[k]:+,})")


def cmd_perf():
    cur = json.loads((WEB / f"{CUR}_perf.json").read_text())
    prev = {s["station"]: s for s in json.loads((WEB / f"{PREV}_perf.json").read_text())["stations"]}
    cold = {s["station"]: s for s in json.loads((WEB / "gate5cold_perf.json").read_text())["stations"]}
    print(f"== 2560x1440 medians (ms): {CUR} vs {PREV} (both post-capture) vs gate5cold (idle) ==")
    print(f"{'st':>2s} {'g8':>6s} {'g7':>6s} {'cold':>6s} {'d g7':>6s} {'d cold':>7s} "
          f"{'fps':>6s} {'gpu ms':>7s} {'draws':>6s} {'tris':>9s} {'progs':>6s}")
    for s in cur["stations"]:
        st = s["station"]
        m = s["frame_ms"]["median"]
        print(f"{st:2d} {m:6.1f} {prev[st]['frame_ms']['median']:6.1f} "
              f"{cold[st]['frame_ms']['median']:6.1f} "
              f"{m - prev[st]['frame_ms']['median']:+6.1f} "
              f"{m - cold[st]['frame_ms']['median']:+7.1f} {s['fps_presented']:6.1f} "
              f"{s['gpu_cost_ms']['median']:7.1f} {s['draw_calls']:6d} {s['triangles']:9d} "
              f"{s['programs']:6d}")
    for tag in (CUR, PREV):
        for s in json.loads((WEB / f"{tag}_perf.json").read_text())["stations"][:1]:
            r = s["resident"]
            print(f"resident {tag:7s} {r['total_bytes'] / 1e6:8.1f} MB (tex {r['texture_bytes'] / 1e6:.1f}, "
                  f"geo {r['geometry_bytes'] / 1e6:.1f}, rt {r['render_target_bytes'] / 1e6:.1f}, "
                  f"{r['textures']} textures)")
    # draws / tris per station, both captures
    for tag in (CUR, PREV):
        d = json.loads((WEB / f"{tag}_perf.json").read_text())["stations"]
        print(f"{tag}: draws {[s['draw_calls'] for s in d]}  "
              f"tris {[round(s['triangles'] / 1e6, 2) for s in d]} M  "
              f"progs {[s['programs'] for s in d]}")


def cmd_mobile():
    P18B.cmd_mobile(f"{CUR}m")
    print()
    P18B.cmd_canvas(f"{CUR}m")


def cmd_mobdiff():
    print(f"== mobile: {CUR}m vs {PREV}m (round 19), 1170x2532 ==")
    print(f"{'st':>2s} {'g8m lum':>9s} {'g7m lum':>9s} {'ratio':>7s} {'MAE':>7s} "
          f"{'px>1/255 %':>11s} {'changed %':>10s}")
    for st in range(1, 7):
        a = P.rgb(str(WEB / f"{CUR}m_cam{st:02d}.png"))
        b = P.rgb(str(WEB / f"{PREV}m_cam{st:02d}.png"))
        al, bl = a @ P.LUMA, b @ P.LUMA
        d = np.abs(al - bl)
        print(f"{st:2d} {al.mean():9.3f} {bl.mean():9.3f} {al.mean() / max(bl.mean(), 1e-6):6.4f}x "
              f"{d.mean():7.4f} {(d > 1).mean() * 100:10.3f}% "
              f"{100 * (np.abs(a - b).max(2) > 0).mean():9.3f}%")
    for tag in (f"{CUR}m", f"{PREV}m"):
        cam = json.loads((WEB / f"{tag}_cam.json").read_text())
        print(f"{tag}: draws {[s.get('draw_calls') for s in cam['perStation']]}  "
              f"tris {[round((s.get('triangles') or 0) / 1e6, 2) for s in cam['perStation']]} M  "
              f"errors {len(cam.get('pageErrors') or [])}")


def cmd_names():
    P18B.cmd_names()


def cmd_all():
    for fn in (cmd_regress, cmd_shrubs, cmd_crowns, cmd_column, cmd_boxes, cmd_payload,
               cmd_netdiff, cmd_perf, cmd_mobile, cmd_mobdiff, cmd_names):
        fn()
        print()


if __name__ == "__main__":
    P.select_round("18")
    for a in (sys.argv[1:] or ["all"]):
        {"regress": cmd_regress, "shrubs": cmd_shrubs, "crowns": cmd_crowns, "column": cmd_column,
         "boxes": cmd_boxes, "payload": cmd_payload, "netdiff": cmd_netdiff, "perf": cmd_perf,
         "mobile": cmd_mobile, "mobdiff": cmd_mobdiff, "names": cmd_names, "all": cmd_all}[a]()
