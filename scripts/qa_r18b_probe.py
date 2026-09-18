#!/usr/bin/env python3
"""QA round 18b (Phase 6b, the Gate 5 fix round) measurement probe.

No Blender, no Chrome (curl only, in qa_r18b_live.py). An EXTENSION of `scripts/qa_r18_probe.py`
(-> qa_r17 -> qa_r16 -> qa_r13 unchanged), so every measure below is the one earlier rounds used.

    python3 scripts/qa_r18b_probe.py regress   # gate5b vs gate5 per station: any move > 1/255 is a finding
    python3 scripts/qa_r18b_probe.py payload   # gate5b_net.json / gate5bm_net.json
    python3 scripts/qa_r18b_probe.py bars      # the loading-bar denominators, both variants
    python3 scripts/qa_r18b_probe.py perf      # gate5b_perf.json vs gate5cold / gate5 / pass B
    python3 scripts/qa_r18b_probe.py mobile    # gate5bm_cam.json: draws, tris, resident, errors, canvas
    python3 scripts/qa_r18b_probe.py names     # the name sweep over BOTH gate5 manifests (restated)
    python3 scripts/qa_r18b_probe.py all

`gate5b` = the desktop capture on the redeployed URL | `gate5bm` = the ?tier=mobile capture |
`gate5` / `gate5m` = the round-18 captures on the same URL before the fix.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_r18_probe as P18  # noqa: E402
import qa_r16_probe as P16  # noqa: E402

P = P18.P
ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "renders" / "web"
EXPORT = ROOT / "export" / "out" / "gate5"


def _net(name):
    return json.loads((WEB / name).read_text())


# ------------------------------------------------------------------- desktop regression check
def cmd_regress():
    """gate5b vs gate5, same URL, same assets expected: any move > 1/255 is a finding."""
    print("== desktop regression: gate5b (after the fix) vs gate5 (round 18), 1920x1080 ==")
    print(f"{'st':>2s} {'g5b lum':>8s} {'g5 lum':>8s} {'ratio':>7s} {'MAE':>7s} {'max|d|':>7s} "
          f"{'px>1/255 %':>11s} {'MAE ref g5b':>12s} {'MAE ref g5':>11s}")
    for st in range(1, 7):
        b = P.rgb(str(WEB / f"gate5b_cam{st:02d}.png"))
        a = P.rgb(str(WEB / f"gate5_cam{st:02d}.png"))
        f = P.rgb(P.REF[st][0])
        bl, al, fl = b @ P.LUMA, a @ P.LUMA, f @ P.LUMA
        d = np.abs(bl - al)
        print(f"{st:2d} {bl.mean():8.3f} {al.mean():8.3f} {bl.mean() / max(al.mean(), 1e-6):6.4f}x "
              f"{d.mean():7.4f} {d.max():7.2f} {(d > 1).mean() * 100:10.3f}% "
              f"{np.abs(bl - fl).mean():12.2f} {np.abs(al - fl).mean():11.2f}")


# ------------------------------------------------------------------------------------- payload
def cmd_payload():
    for tag, name in (("desktop URL (gate5b)", "gate5b_net.json"),
                      ("mobile URL (gate5bm)", "gate5bm_net.json"),
                      ("desktop URL (gate5, round 18)", "gate5_net.json"),
                      ("mobile URL (gate5m, round 18, broken)", "gate5m_net.json")):
        d = _net(name)
        t = d["viewer_tiers"]
        print(f"== {tag}: {name}")
        print(f"   bytes before first frame {d['bytes_before_first_frame']:,} "
              f"({d['bytes_before_first_frame'] / 1e6:.2f} MB, "
              f"{d['bytes_before_first_frame'] / 2**20:.2f} MiB) in "
              f"{d['requests_before_first_frame']} req, {d['time_to_first_frame_s']:.2f} s")
        print(f"   total {d['bytes_total']:,} ({d['bytes_total'] / 1e6:.1f} MB) over "
              f"{d['requests_n']} req, all tiers {d['time_to_all_tiers_s']:.2f} s")
        print(f"   by kind {d['bytes_by_kind']}")
        for pt in t["per_tier"]:
            print(f"   tier {pt['tier']}: {pt['bytes'] / 1e6:8.1f} MB in {pt['wall_s']:6.2f} s "
                  f"(planned {pt['planned'] / 1e6:.1f} MB, {pt['glbs']} glb)")
        print(f"   failures {t['failures']} lowres_remaining {len(t['lowres_remaining'])} "
              f"lowres_substituted {t['lowres_substituted']} oversize {t['oversize']} "
              f"deferred_lightmaps {t['deferred_lightmaps']}")
        bad = [r for r in d["requests"] if (r.get("status") or 200) >= 400]
        big = [r for r in d["requests"] if (r.get("bytes") or 0) > 25 * 2**20]
        print(f"   responses >= 400: {len(bad)} {[(r.get('status'), r['url'].split('/')[-1]) for r in bad[:6]]}"
              f"   over 25 MiB: {len(big)}")
        print()


# ---------------------------------------------------------------------------- loading-bar fix
def cmd_bars():
    """QA 18 finding 2: the bar's denominator. loaded vs declared vs planned, per variant."""
    print("== loading bar: tier-0 denominator vs the bytes actually fetched ==")
    print(f"{'capture':10s} {'tier0 fetched':>14s} {'declared':>12s} {'planned':>12s} "
          f"{'bar at t0 end':>14s} {'planned/fetched':>16s}")
    for tag, name in (("gate5b", "gate5b_net.json"), ("gate5bm", "gate5bm_net.json"),
                      ("gate5", "gate5_net.json"), ("gate5m", "gate5m_net.json")):
        d = _net(name)
        t = d["viewer_tiers"]
        got = t["per_tier"][0]["bytes"]
        dec = t["declared_bytes"]["0"]
        pl = t["tier0_planned_bytes"]
        print(f"{tag:10s} {got:14,d} {dec:12,d} {pl:12,d} {got / pl * 100:13.1f}% "
              f"{pl / got:15.3f}x")
    print("(bar at t0 end = what the progress bar reads when tier 0 has finished downloading;"
          " 100 % is right)")


# ---------------------------------------------------------------------------------------- perf
def cmd_perf():
    cur = json.loads((WEB / "gate5b_perf.json").read_text())
    prev = {s["station"]: s for s in json.loads((WEB / "gate5_perf.json").read_text())["stations"]}
    cold = {s["station"]: s for s in json.loads((WEB / "gate5cold_perf.json").read_text())["stations"]}
    print("== 2560x1440 medians (ms): gate5b vs gate5 (post-capture) vs gate5cold vs pass B ==")
    print(f"{'st':>2s} {'g5b':>6s} {'g5':>6s} {'cold':>6s} {'passB':>6s} {'d cold':>7s} "
          f"{'fps':>6s} {'gpu ms':>7s} {'draws':>6s} {'tris':>9s} {'progs':>6s} {'max/p95':>8s}")
    for s in cur["stations"]:
        st = s["station"]
        m = s["frame_ms"]["median"]
        print(f"{st:2d} {m:6.1f} {prev[st]['frame_ms']['median']:6.1f} "
              f"{cold[st]['frame_ms']['median']:6.1f} {P18.PASS_B[st]:6.1f} "
              f"{m - cold[st]['frame_ms']['median']:+7.1f} {s['fps_presented']:6.1f} "
              f"{s['gpu_cost_ms']['median']:7.1f} {s['draw_calls']:6d} {s['triangles']:9d} "
              f"{s['programs']:6d} {s['frame_ms']['max'] / s['frame_ms']['p95']:7.1f}x")
    for tag, d in (("gate5b", cur), ("gate5", json.loads((WEB / "gate5_perf.json").read_text()))):
        r = d["stations"][0]["resident"]
        print(f"resident {tag:7s} {r['total_bytes'] / 1e6:8.1f} MB (tex {r['texture_bytes'] / 1e6:.1f}, "
              f"geo {r['geometry_bytes'] / 1e6:.1f}, rt {r['render_target_bytes'] / 1e6:.1f}, "
              f"{r['textures']} textures)")


# -------------------------------------------------------------------------------------- mobile
def cmd_mobile(tag="gate5bm"):
    cam = json.loads((WEB / f"{tag}_cam.json").read_text())
    i = cam["info"]
    print(f"== {tag}: {len(cam['pageErrors'])} page error(s); canvas {i['size']}, "
          f"drawingBuffer {i['device'].get('drawingBufferPx')}, dpr {i['device'].get('pixelRatio')}")
    for e in cam["pageErrors"][:10]:
        print("   ", e)
    print(f"{'st':>2s} {'draws':>6s} {'tris':>10s} {'progs':>6s} {'geoms':>6s} {'texs':>6s}")
    for s in cam["perStation"]:
        m = s.get("info_memory", {})
        print(f"{s.get('station'):2d} {s.get('draw_calls'):6d} {s.get('triangles'):10d} "
              f"{s.get('programs'):6d} {m.get('geometries'):6d} {m.get('textures'):6d}")
    r = cam["perStation"][0].get("resident", i.get("resident", {}))
    print(f"texture formats {r.get('texture_formats')}")
    print(f"render targets  {[(t['what'], [round(x) for x in t['size']], t['bytes']) for t in r.get('render_targets', [])]}")
    print(f"resident {r.get('total_bytes', 0) / 1e6:.1f} MB (tex {r.get('texture_bytes', 0) / 1e6:.1f}, "
          f"geo {r.get('geometry_bytes', 0) / 1e6:.1f}, rt {r.get('render_target_bytes', 0) / 1e6:.1f}, "
          f"{r.get('textures')} textures) vs the 700 MB target")
    print(f"glbs loaded: {[g.get('name', g) if isinstance(g, dict) else g for g in i.get('glbs', [])]}")
    print(f"lightmapsApplied {i.get('lightmapsApplied')} patchedMaterials {i.get('patchedMaterials')} "
          f"unpatched {len(i.get('unpatchedMaterials', []))} shrubLod {i.get('shrubLod')}")


def cmd_mobile_c():
    cmd_mobile("gate5cm")


# ---------------------------------------------------------------------- mobile frame geometry
def cmd_canvas(tag="gate5bm"):
    """Is the whole canvas painted? (the 1.5 Mpx cap shrank the canvas in gate5bm)."""
    print(f"== {tag}: the WebGL canvas inside each capture (page background = the corner pixel) ==")
    for st in range(1, 7):
        p = WEB / f"{tag}_cam{st:02d}.png"
        if not p.exists():
            print(f"   station {st}: MISSING {p.name}")
            continue
        from PIL import Image
        a = np.asarray(Image.open(str(p)).convert("RGB"), dtype=np.float64)
        bg = a[-1, -1]
        content = np.abs(a - bg).max(axis=2) > 1
        cols, rows = np.where(content.any(axis=0))[0], np.where(content.any(axis=1))[0]
        w, h = cols.max() + 1, rows.max() + 1
        lum = a @ P.LUMA
        print(f"   station {st}: page {a.shape[1]}x{a.shape[0]}, canvas {w}x{h} "
              f"({w / a.shape[1] * 100:.1f}% x {h / a.shape[0] * 100:.1f}%, "
              f"{content.mean() * 100:.1f}% of the page; aspect {w / h:.4f} vs "
              f"{a.shape[1] / a.shape[0]:.4f}), bg {bg.tolist()}, "
              f"canvas lum {lum[:h, :w].mean():.2f}")


def cmd_canvas_c():
    cmd_canvas("gate5cm")


# --------------------------------------------------------------------------------------- names
def cmd_names():
    import re
    for tag, name in (("desktop", "manifest.json"), ("mobile", "manifest_mobile.json")):
        d = json.loads((EXPORT / name).read_text())
        out = []
        P16._strings(d, out)
        hits = {}
        for x in out:
            if len(x) < 90 and P16.PAT.search(x) and P16.OBJ.match(x):
                k = re.sub(r"\d+$", "##", x)
                hits[k] = hits.get(k, 0) + 1
        print(f"== name sweep, {tag} ({name}): {len(d['files'])} rows, "
              f"{len(hits)} object-shaped hit(s) ==")
        for k in sorted(hits):
            print(f"   {k:56s} x{hits[k]}")
    desk = json.loads((EXPORT / "manifest.json").read_text())
    mob = json.loads((EXPORT / "manifest_mobile.json").read_text())
    dp = {f["path"] for f in desk["files"]}
    miss = [f["path"] for f in mob["files"] if f["path"] not in dp]
    tiers = {}
    for f in desk["files"]:
        tiers[str(f.get("tier"))] = tiers.get(str(f.get("tier")), 0) + 1
    print(f"== deploy plan: desktop rows by tier {tiers}; "
          f"mobile paths absent from the desktop plan: {len(miss)} {miss[:8]}")


def cmd_all():
    for fn in (cmd_regress, cmd_payload, cmd_bars, cmd_perf, cmd_mobile, cmd_canvas, cmd_names):
        fn()
        print()


if __name__ == "__main__":
    P.select_round("18")
    cmds = {k[4:]: v for k, v in list(globals().items()) if k.startswith("cmd_")}
    for a in (sys.argv[1:] or ["all"]):
        cmds[a]()
