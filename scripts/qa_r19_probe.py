#!/usr/bin/env python3
"""QA round 19 (Phase 7, the foliage look on the live site) measurement probe.

No Blender, no Chrome. An EXTENSION of `scripts/qa_r18b_probe.py` (-> r18 -> r17 -> r16 -> r13),
so every measure is the one the earlier rounds used; the Phase 7 crown / edge / frame tables come
from `scripts/qa_p7_probe.py` (the viewer's own tool, run as-is with PFA_VIEWER_WEB=renders/web).

    python3 scripts/qa_r19_probe.py regress   # gate7 vs gate5b and vs round16c, per station
    python3 scripts/qa_r19_probe.py boxes     # every round-13/15/16 box, gate7 vs gate5b, >3 % flagged
    python3 scripts/qa_r19_probe.py payload   # gate7_net.json / gate7m_net.json vs the gate5b pair
    python3 scripts/qa_r19_probe.py perf      # gate7_perf.json vs gate5b / gate5cold / pass B
    python3 scripts/qa_r19_probe.py mobile    # gate7m_cam.json: draws, tris, resident, errors, canvas
    python3 scripts/qa_r19_probe.py mobdiff   # gate7m vs gate5cm per station (the mobile before)
    python3 scripts/qa_r19_probe.py orbit     # the close-orbit crowns: structure statistics per box
    python3 scripts/qa_r19_probe.py names     # the name sweep over both gate5 manifests (restated)
    python3 scripts/qa_r19_probe.py all

`gate7` = the desktop capture on the URL after the Phase 7 deploy | `gate7m` = its ?tier=mobile pass |
`gate7_orbit_h0{2530,2150}` = the lead's mobile close orbit (80 m, height 5 m) | before = `gate5b`
(desktop, round 18b) and `gate5cm` (mobile, round 18b).
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_r18b_probe as P18B  # noqa: E402
import qa_r18_probe as P18  # noqa: E402
import qa_r16_probe as P16  # noqa: E402

P = P18.P
ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "renders" / "web"


def _net(name):
    return json.loads((WEB / name).read_text())


def _lum(path):
    return P.rgb(str(path)) @ P.LUMA


# --------------------------------------------------------------------------------- regression
def cmd_regress():
    """gate7 vs gate5b (the deployed before) and both against the Cycles reference."""
    print("== desktop: gate7 (Phase 7 on the URL) vs gate5b (round 18b), 1920x1080 ==")
    print(f"{'st':>2s} {'g7 lum':>8s} {'g5b lum':>8s} {'ratio':>7s} {'MAE':>7s} {'max|d|':>7s} "
          f"{'px>1/255 %':>11s} {'MAE ref g7':>11s} {'MAE ref g5b':>12s} {'g7/ref':>8s}")
    for st in range(1, 7):
        b = _lum(WEB / f"gate7_cam{st:02d}.png")
        a = _lum(WEB / f"gate5b_cam{st:02d}.png")
        f = _lum(P.REF[st][0])
        d = np.abs(b - a)
        print(f"{st:2d} {b.mean():8.3f} {a.mean():8.3f} {b.mean() / max(a.mean(), 1e-6):6.4f}x "
              f"{d.mean():7.4f} {d.max():7.2f} {(d > 1).mean() * 100:10.3f}% "
              f"{np.abs(b - f).mean():11.2f} {np.abs(a - f).mean():12.2f} "
              f"{b.mean() / max(f.mean(), 1e-6):7.3f}x")


# -------------------------------------------------------------------------------------- boxes
def cmd_boxes():
    """Every round-13/15/16 box: gate7 vs gate5b. A move > 3 % on lum is a finding."""
    print("== boxes: gate7 vs gate5b (lum, std, hard-edge %) — >3 % on lum flagged ==")
    print(f"{'box':24s} {'st':>2s} {'g7 lum':>8s} {'g5b':>8s} {'ratio':>7s} {'g7 std':>7s} "
          f"{'g5b':>7s} {'g7 hard%':>9s} {'g5b':>7s} {'ref lum':>8s}  flag")
    flagged = []
    for name, st, box, _why in P18.ALL_BOXES:
        g = P16.box_stats(P.rgb(str(WEB / f"gate7_cam{st:02d}.png")), box)
        r = P16.box_stats(P.rgb(str(WEB / f"gate5b_cam{st:02d}.png")), box)
        f = P16.box_stats(P.rgb(P.REF[st][0]), box)
        ratio = g["lum"] / max(r["lum"], 1e-6)
        flag = "MOVED" if abs(ratio - 1.0) > 0.03 else ""
        if flag:
            flagged.append((name, ratio))
        print(f"{name:24s} {st:2d} {g['lum']:8.2f} {r['lum']:8.2f} {ratio:6.3f}x {g['std']:7.2f} "
              f"{r['std']:7.2f} {g['hard']:8.2f}% {r['hard']:6.2f}% {f['lum']:8.2f}  {flag}")
    print(f"-- {len(flagged)} box(es) of {len(P18.ALL_BOXES)} move more than 3 %: "
          f"{[(n, round(x, 3)) for n, x in flagged]}")


# ------------------------------------------------------------------------------------ payload
def cmd_payload():
    for tag, name in (("desktop URL (gate7)", "gate7_net.json"),
                      ("mobile URL (gate7m)", "gate7m_net.json"),
                      ("desktop URL (gate5b, before)", "gate5b_net.json"),
                      ("mobile URL (gate5bm, before)", "gate5bm_net.json")):
        d = _net(name)
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


# --------------------------------------------------------------------------------------- perf
def cmd_perf():
    cur = json.loads((WEB / "gate7_perf.json").read_text())
    prev = {s["station"]: s for s in json.loads((WEB / "gate5b_perf.json").read_text())["stations"]}
    cold = {s["station"]: s for s in json.loads((WEB / "gate5cold_perf.json").read_text())["stations"]}
    print("== 2560x1440 medians (ms): gate7 vs gate5b (post-capture) vs gate5cold vs pass B ==")
    print(f"{'st':>2s} {'g7':>6s} {'g5b':>6s} {'cold':>6s} {'passB':>6s} {'d g5b':>7s} {'d cold':>7s} "
          f"{'fps':>6s} {'gpu ms':>7s} {'draws':>6s} {'tris':>9s} {'progs':>6s}")
    for s in cur["stations"]:
        st = s["station"]
        m = s["frame_ms"]["median"]
        print(f"{st:2d} {m:6.1f} {prev[st]['frame_ms']['median']:6.1f} "
              f"{cold[st]['frame_ms']['median']:6.1f} {P18.PASS_B[st]:6.1f} "
              f"{m - prev[st]['frame_ms']['median']:+7.1f} "
              f"{m - cold[st]['frame_ms']['median']:+7.1f} {s['fps_presented']:6.1f} "
              f"{s['gpu_cost_ms']['median']:7.1f} {s['draw_calls']:6d} {s['triangles']:9d} "
              f"{s['programs']:6d}")
    for tag in ("gate7", "gate5b"):
        r = json.loads((WEB / f"{tag}_perf.json").read_text())["stations"][0]["resident"]
        print(f"resident {tag:7s} {r['total_bytes'] / 1e6:8.1f} MB (tex {r['texture_bytes'] / 1e6:.1f}, "
              f"geo {r['geometry_bytes'] / 1e6:.1f}, rt {r['render_target_bytes'] / 1e6:.1f}, "
              f"{r['textures']} textures)")


# ------------------------------------------------------------------------------------- mobile
def cmd_mobile():
    P18B.cmd_mobile("gate7m")
    print()
    P18B.cmd_canvas("gate7m")


def cmd_mobdiff():
    """gate7m vs gate5cm, the mobile before (same canvas geometry, same stations)."""
    print("== mobile: gate7m vs gate5cm (round 18b), 1170x2532 ==")
    print(f"{'st':>2s} {'g7m lum':>9s} {'g5cm lum':>9s} {'ratio':>7s} {'MAE':>7s} "
          f"{'px>1/255 %':>11s} {'changed %':>10s}")
    for st in range(1, 7):
        a = P.rgb(str(WEB / f"gate7m_cam{st:02d}.png"))
        b = P.rgb(str(WEB / f"gate5cm_cam{st:02d}.png"))
        al, bl = a @ P.LUMA, b @ P.LUMA
        d = np.abs(al - bl)
        print(f"{st:2d} {al.mean():9.3f} {bl.mean():9.3f} {al.mean() / max(bl.mean(), 1e-6):6.4f}x "
              f"{d.mean():7.4f} {(d > 1).mean() * 100:10.3f}% "
              f"{100 * (np.abs(a - b).max(2) > 0).mean():9.3f}%")
    for tag in ("gate7m", "gate5cm"):
        cam = json.loads((WEB / f"{tag}_cam.json").read_text())
        tris = [s.get("triangles") for s in cam["perStation"]]
        draws = [s.get("draw_calls") for s in cam["perStation"]]
        print(f"{tag}: draws {draws}  tris {[round(t / 1e6, 2) for t in tris]} M")


# -------------------------------------------------------------------------------------- orbit
ORBIT_BOXES = [
    # (name, file tag, box) — the crowns the user's screenshot framed, at 37-40 m.
    ("h253 crown L", "gate7_orbit_h02530", (20, 780, 330, 1450)),
    ("h253 crown R", "gate7_orbit_h02530", (620, 500, 1150, 1400)),
    ("h215 crown", "gate7_orbit_h02150", (120, 1020, 700, 1560)),
    ("h215 crown R", "gate7_orbit_h02150", (760, 830, 1170, 1560)),
]


def cmd_orbit():
    """Crown STRUCTURE in the close-orbit frames: a card blob has low interior variation and no
    sky holes; a mesh canopy has both. Reported as hard-edge %, interior std, dark-core p05 and the
    share of near-black pixels (the 'black core' the user photographed)."""
    print("== mobile close orbit (80 m, h 5 m): crown structure ==")
    print(f"{'box':16s} {'file':22s} {'lum':>7s} {'std':>7s} {'hard%':>7s} {'p05':>6s} "
          f"{'<12/255 %':>10s} {'sky holes %':>12s}")
    for name, tag, box in ORBIT_BOXES:
        p = WEB / f"{tag}.png"
        if not p.exists():
            print(f"{name:16s} MISSING {p.name}")
            continue
        a = P.rgb(str(p))
        x0, y0, x1, y1 = box
        crop = a[y0:y1, x0:x1]
        lum = crop @ P.LUMA
        r = P16.box_stats(a, box)
        # "sky holes": bluish pixels brighter than the crown mean inside the box
        blue = (crop[:, :, 2] > crop[:, :, 1] + 6) & (lum > lum.mean())
        print(f"{name:16s} {tag:22s} {lum.mean():7.2f} {lum.std():7.2f} {r['hard']:6.2f}% "
              f"{np.percentile(lum, 5):6.1f} {100 * (lum < 12).mean():9.2f}% "
              f"{100 * blue.mean():11.2f}%")
    cam = WEB / "gate7_orbit_cam.json"
    if cam.exists():
        d = json.loads(cam.read_text())
        i = d.get("info", {})
        print(f"orbit capture: {len(d.get('pageErrors', []))} page error(s), canvas {i.get('size')}, "
              f"drawingBuffer {i.get('device', {}).get('drawingBufferPx')}")
        for s in d.get("perStation", []):
            print(f"   {s.get('station', s.get('name'))}: draws {s.get('draw_calls')} "
                  f"tris {s.get('triangles')}")


def cmd_names():
    P18B.cmd_names()


def cmd_all():
    for fn in (cmd_regress, cmd_boxes, cmd_payload, cmd_perf, cmd_mobile, cmd_mobdiff,
               cmd_orbit, cmd_names):
        fn()
        print()


if __name__ == "__main__":
    P.select_round("18")
    for a in (sys.argv[1:] or ["all"]):
        {"regress": cmd_regress, "boxes": cmd_boxes, "payload": cmd_payload, "perf": cmd_perf,
         "mobile": cmd_mobile, "mobdiff": cmd_mobdiff, "orbit": cmd_orbit, "names": cmd_names,
         "all": cmd_all}[a]()
