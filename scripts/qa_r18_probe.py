#!/usr/bin/env python3
"""QA round 18 (Phase 6b, Gate 5 — the web deployment) measurement probe.

No Blender, no Chrome. An EXTENSION of `scripts/qa_r17_probe.py` (which imports qa_r16 -> qa_r15 ->
qa_r13 unchanged), so every box below is the same measure round 17 used.

    python3 scripts/qa_r18_probe.py parity    # gate5 (the URL) vs round16c (the 6c build), per station
    python3 scripts/qa_r18_probe.py boxes     # every round-13/15/16 box, gate5 vs round16c, >3 % flagged
    python3 scripts/qa_r18_probe.py payload   # gate5_net.json / gate5m_net.json / gate5_tier0_net.json
    python3 scripts/qa_r18_probe.py perf      # gate5_perf.json vs docs/perf_ab_6c.md pass B and r16c cold
    python3 scripts/qa_r18_probe.py mobile    # the ?tier=mobile capture: geometry, errors, level
    python3 scripts/qa_r18_probe.py names     # the name sweep over BOTH gate5 manifests
    python3 scripts/qa_r18_probe.py all

Columns: `gate5` = the staging URL at tiers=all (the scored capture) | `round16c` = the 6c build QA 17
scored | the reference (Phase 5 hero at station 1, the round-13 Cycles frames at 2-6).
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_r17_probe as P17  # noqa: E402
import qa_r16_probe as P16  # noqa: E402
import qa_r13_probe as P13  # noqa: E402

P = P17.P
ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "renders" / "web"
EXPORT = ROOT / "export" / "out" / "gate5"

# Round 18: the URL capture against the 6c capture QA 17 scored. Both are 1920x1080 headless Chrome.
P.ROUNDS["18"] = ("gate5_cam%02d.png", "round16c_cam%02d.png", "round16c_cam%02d.png",
                  ("gate5url", "round16c", "round16c"), P.REF_R14)

ALL_BOXES = ([(n, s, b, w) for n, s, b, w in P13.BOXES]
             + [(n, s, b, w) for n, s, b, w in P16.FOLIAGE16])


def _img(st, tmpl):
    return P.rgb((tmpl % st) if tmpl else P.REF[st][0])


# --------------------------------------------------------------------------------------- parity
def cmd_parity():
    """Whole-frame luma ratio and MAE, URL vs the 6c build, and both against the reference."""
    print("== parity: gate5 (URL, tiers=all) vs round16c (the 6c build QA 17 scored) ==")
    print(f"{'station':>7s} {'gate5 lum':>10s} {'r16c lum':>9s} {'ratio':>7s} {'MAE':>7s} "
          f"{'p99 |d|':>8s} {'>8/255 %':>9s} {'gate5/ref':>10s} {'r16c/ref':>9s} "
          f"{'MAE ref g5':>11s} {'MAE ref r16c':>13s}")
    for st in range(1, 7):
        g = _img(st, str(WEB / "gate5_cam%02d.png"))
        r = _img(st, str(WEB / "round16c_cam%02d.png"))
        f = _img(st, None)
        gl, rl, fl = g @ P.LUMA, r @ P.LUMA, f @ P.LUMA
        d = np.abs(gl - rl)
        print(f"{st:7d} {gl.mean():10.2f} {rl.mean():9.2f} {gl.mean() / max(rl.mean(), 1e-6):6.3f}x "
              f"{d.mean():7.2f} {np.percentile(d, 99):8.2f} {(d > 8).mean() * 100:8.2f}% "
              f"{gl.mean() / max(fl.mean(), 1e-6):9.3f}x {rl.mean() / max(fl.mean(), 1e-6):8.3f}x "
              f"{np.abs(gl - fl).mean():11.2f} {np.abs(rl - fl).mean():13.2f}")


# ----------------------------------------------------------------------------------------- boxes
def cmd_boxes():
    """Every round-13/15/16 box: gate5 vs round16c. A move > 3 % on lum is a finding."""
    print("== boxes: gate5 vs round16c (lum, std, hard-edge %) — >3 % on lum flagged ==")
    print(f"{'box':24s} {'st':>2s} {'g5 lum':>8s} {'r16c':>8s} {'ratio':>7s} {'g5 std':>7s} "
          f"{'r16c':>7s} {'g5 hard%':>9s} {'r16c':>7s} {'ref lum':>8s}  flag")
    flagged = 0
    for name, st, box, _why in ALL_BOXES:
        g = P16.box_stats(_img(st, str(WEB / "gate5_cam%02d.png")), box)
        r = P16.box_stats(_img(st, str(WEB / "round16c_cam%02d.png")), box)
        f = P16.box_stats(_img(st, None), box)
        ratio = g["lum"] / max(r["lum"], 1e-6)
        flag = "MOVED" if abs(ratio - 1.0) > 0.03 else ""
        flagged += bool(flag)
        print(f"{name:24s} {st:2d} {g['lum']:8.2f} {r['lum']:8.2f} {ratio:6.3f}x {g['std']:7.2f} "
              f"{r['std']:7.2f} {g['hard']:8.2f}% {r['hard']:6.2f}% {f['lum']:8.2f}  {flag}")
    print(f"-- {flagged} box(es) of {len(ALL_BOXES)} move more than 3 %")


# --------------------------------------------------------------------------------------- payload
def _net(name):
    return json.loads((WEB / name).read_text())


def cmd_payload():
    for tag, name in (("desktop URL", "gate5_net.json"), ("mobile URL", "gate5m_net.json"),
                      ("tier0 (LOCAL dev server)", "gate5_tier0_net.json")):
        d = _net(name)
        print(f"== {tag}: {name}")
        print(f"   url                      {d['url'][:110]}")
        print(f"   bytes before first frame {d['bytes_before_first_frame']:,} "
              f"({d['bytes_before_first_frame'] / 1e6:.2f} MB, {d['bytes_before_first_frame'] / 2**20:.2f} MiB)")
        print(f"   requests before frame 1  {d['requests_before_first_frame']}")
        print(f"   time to first frame      {d['time_to_first_frame_s']:.3f} s")
        print(f"   time to all tiers        {d['time_to_all_tiers_s']:.3f} s")
        print(f"   bytes total              {d['bytes_total']:,} ({d['bytes_total'] / 1e6:.1f} MB)")
        print(f"   by kind                  {d['bytes_by_kind']}")
        t = d["viewer_tiers"]
        for pt in t["per_tier"]:
            print(f"   tier {pt['tier']}: {pt['bytes'] / 1e6:8.1f} MB in {pt['wall_s']:6.2f} s "
                  f"(planned {pt['planned'] / 1e6:.1f} MB, {pt['glbs']} glb)")
        print(f"   upgrades {[(u['tier'], u['upgraded'], u.get('failed')) for u in t.get('upgrades', [])]} "
              f"failures {t.get('failures')} lowres_remaining {len(t.get('lowres_remaining', []))} "
              f"oversize {t.get('oversize')} deferred_lightmaps {t.get('deferred_lightmaps')}")
        big = [r for r in d["requests"] if (r.get("bytes") or 0) > 25 * 2**20]
        print(f"   responses over 25 MiB    {len(big)}")
        bad = [r for r in d["requests"] if (r.get("status") or 200) >= 400]
        print(f"   responses >= 400         {len(bad)}")
        for r in bad[:8]:
            print(f"      {r.get('status')} {r['url'].split('/assets/')[-1]}")
        print()


# ------------------------------------------------------------------------------------------ perf
PASS_B = {1: 29.7, 2: 30.4, 3: 33.5, 4: 22.0, 5: 29.8, 6: 32.3}


def cmd_perf():
    g = json.loads((WEB / "gate5_perf.json").read_text())
    c = json.loads((WEB / "round16c_cold_perf.json").read_text())
    cold = {s["station"]: s for s in c["stations"]}
    print("== 2560x1440 medians (ms): gate5 URL vs perf_ab pass B vs round16c cold ==")
    print(f"{'st':>2s} {'gate5':>7s} {'passB':>7s} {'d(B)':>7s} {'r16c':>7s} {'d(r16c)':>8s} "
          f"{'fps':>6s} {'gpu ms':>7s} {'draws':>6s} {'tris':>9s} {'progs':>6s}")
    for s in g["stations"]:
        st = s["station"]
        m = s["frame_ms"]["median"]
        print(f"{st:2d} {m:7.1f} {PASS_B[st]:7.1f} {m - PASS_B[st]:+7.1f} "
              f"{cold[st]['frame_ms']['median']:7.1f} {m - cold[st]['frame_ms']['median']:+8.1f} "
              f"{s['fps_presented']:6.1f} {s['gpu_cost_ms']['median']:7.1f} {s['draw_calls']:6d} "
              f"{s['triangles']:9d} {s['programs']:6d}")
    rg, rc = g["stations"][0]["resident"], cold[1]["resident"]
    print(f"resident gate5 {rg['total_bytes'] / 1e6:.1f} MB "
          f"(tex {rg['texture_bytes'] / 1e6:.1f}, geo {rg['geometry_bytes'] / 1e6:.1f}, "
          f"rt {rg['render_target_bytes'] / 1e6:.1f}, {rg['textures']} textures)")
    print(f"resident r16c  {rc['total_bytes'] / 1e6:.1f} MB "
          f"(tex {rc['texture_bytes'] / 1e6:.1f}, geo {rc['geometry_bytes'] / 1e6:.1f}, "
          f"rt {rc['render_target_bytes'] / 1e6:.1f}, {rc['textures']} textures) "
          f"-> {rg['total_bytes'] / rc['total_bytes']:.4f}x")
    print(f"load {json.dumps(g['load_s'])}")
    # outlier evidence for the throttling question
    for s in g["stations"]:
        f = s["frame_ms"]
        print(f"  st{s['station']}: min {f['min']:.1f} p95 {f['p95']:.1f} max {f['max']:.1f} "
              f"mean {f['mean']:.1f} (max/p95 {f['max'] / f['p95']:.1f}x)")


# ---------------------------------------------------------------------------------------- mobile
def cmd_mobile():
    cam = json.loads((WEB / "gate5m_cam.json").read_text())
    print(f"== mobile capture (?tier=mobile, 1170x2532): {len(cam['pageErrors'])} page error(s) ==")
    for e in cam["pageErrors"]:
        print("  ", e)
    for s in cam["perStation"]:
        r = s.get("render", s)
        print(f"  station {s.get('station')} tris {r.get('triangles')} progs {r.get('programs')} "
              f"geometries {s.get('memory', {}).get('geometries')} "
              f"textures {s.get('memory', {}).get('textures')}")
    print("== the 7 mobile group glbs: on disk, in which plan, live status ==")
    desk = set(f["path"] for f in json.loads((EXPORT / "manifest.json").read_text())["files"])
    mob = json.loads((EXPORT / "manifest_mobile.json").read_text())
    for f in mob["files"]:
        if "groups/" not in f["path"]:
            continue
        p = EXPORT / f["path"]
        print(f"  {f['path']:28s} tier {f.get('tier')} {f.get('bytes', 0):>9,} B  "
              f"on disk {p.exists()}  in desktop deploy plan {f['path'] in desk}")
    print("== mobile frame level (whole frame luma), station by station ==")
    for st in range(1, 7):
        a = P.rgb(str(WEB / f"gate5m_cam{st:02d}.png"), size=(1170, 2532)) @ P.LUMA
        print(f"  station {st}: lum {a.mean():6.2f} std {a.std():6.2f} "
              f"p10 {np.percentile(a, 10):6.2f} p90 {np.percentile(a, 90):6.2f}")


# ----------------------------------------------------------------------------------------- names
def cmd_names():
    """CLAUDE.md's object-name sweep (qa_r16_probe's PAT/OBJ), restated over BOTH gate5 manifests."""
    import re
    for tag, name in (("desktop", "manifest.json"), ("mobile", "manifest_mobile.json")):
        d = json.loads((EXPORT / name).read_text())
        out = []
        P16._strings(d, out)
        hits = {}
        for x in out:
            if len(x) < 90 and P16.PAT.search(x) and P16.OBJ.match(x):
                hits.setdefault(re.sub(r"\d+$", "##", x), 0)
                hits[re.sub(r"\d+$", "##", x)] += 1
        print(f"== name sweep, {tag} ({name}): {len(hits)} distinct object-shaped hit(s) ==")
        for k in sorted(hits):
            print(f"   {k:56s} x{hits[k]}")


def cmd_all():
    for fn in (cmd_parity, cmd_boxes, cmd_payload, cmd_perf, cmd_mobile, cmd_names):
        fn()
        print()


if __name__ == "__main__":
    P.select_round("18")
    cmds = {k[4:]: v for k, v in list(globals().items()) if k.startswith("cmd_")}
    for a in (sys.argv[1:] or ["all"]):
        cmds[a]()
