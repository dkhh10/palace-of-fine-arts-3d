#!/usr/bin/env python3
"""QA round 17 (Phase 6c foliage gate, round two of two) measurement probe.

No Blender, no Chrome. An EXTENSION of `scripts/qa_r16_probe.py` (which imports `qa_r15_probe` ->
`qa_r13_probe` unchanged): this module registers the round-16c capture triple and re-runs round 16's
own boxes on it, so every number in docs/qa_round_17.md is the same measure as docs/qa_round_16.md's.

    python3 scripts/qa_r17_probe.py all
    python3 scripts/qa_r17_probe.py foliage16   # the 6c boxes (shrub/reed, near/far tree bands)
    python3 scripts/qa_r17_probe.py crown       # crown interior-vs-rim, stations 1, 2, 5
    python3 scripts/qa_r17_probe.py norm        # frame-normalised shrub level, round16b -> round16c
    python3 scripts/qa_r17_probe.py bareurl     # the bare URL against the station-1 preset
    python3 scripts/qa_r17_probe.py perf17      # round 15 / 16b / 16c A / 16c B / cold, + memory
    python3 scripts/qa_r17_probe.py walk        # the 30 s walk clamp probe
    python3 scripts/qa_r17_probe.py names       # the export-set name sweep, restated
    python3 scripts/qa_r17_probe.py boxes | frame | water | bloom | ...  (round-10b / -14 / -15 boxes)

Columns: `round16c` (post=all, the scored look) | `round16cnopost` (the control) | `round16b` (the
previously scored capture) | the reference (Phase 5 hero at station 1, the round-13 compositor-on
Cycles frames at 2-6).  Definitions are qa_r13_probe's / qa_r16_probe's and are not redefined here.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_r16_probe as P16  # noqa: E402  (registers round 16; imports qa_r15_probe -> qa_r13_probe)

P = P16.P

P.ROUNDS["17"] = ("round16c_cam%02d.png", "round16cnopost_cam%02d.png", "round16b_cam%02d.png",
                  ("post=all", "post=off", "round16b"), P.REF_R14)

SHRUB = [b for b in P16.FOLIAGE16 if "shrub" in b[0] or "reed" in b[0] or "planting" in b[0]]


# ------------------------------------------------------- frame-normalised shrub level (QA 16 §3)
def cmd_norm():
    """Level / ref, divided by the whole-frame ratio of the same station (QA 16's definition)."""
    print("== shrub and reed boxes: raw level and frame-normalised level vs the reference ==")
    print(f"{'box':22s} {'16b lum':>8s} {'16c lum':>8s} {'ref':>7s} {'16b x':>7s} {'16c x':>7s} "
          f"{'16b fn':>7s} {'16c fn':>7s} {'16b hard%':>10s} {'16c hard%':>10s} {'ref hard%':>10s} "
          f"{'16c leaf%':>10s} {'ref leaf%':>10s}")
    for name, st, box, why in SHRUB:
        ref = P16.box_stats(P16._img(st, None), box)
        cur = P16.box_stats(P16._img(st, P.BAKED), box)
        prev = P16.box_stats(P16._img(st, P.GATE2), box)
        # whole-frame ratio of the same station
        fr_ref = float((P16._img(st, None) @ P.LUMA).mean())
        fr_cur = float((P16._img(st, P.BAKED) @ P.LUMA).mean()) / max(fr_ref, 1e-6)
        fr_prev = float((P16._img(st, P.GATE2) @ P.LUMA).mean()) / max(fr_ref, 1e-6)
        rc = cur["lum"] / max(ref["lum"], 1e-6)
        rp = prev["lum"] / max(ref["lum"], 1e-6)
        print(f"{name:22s} {prev['lum']:8.1f} {cur['lum']:8.1f} {ref['lum']:7.1f} "
              f"{rp:6.2f}x {rc:6.2f}x {rp / fr_prev:6.2f}x {rc / fr_cur:6.2f}x "
              f"{prev['hard']:9.2f}% {cur['hard']:9.2f}% {ref['hard']:9.2f}% "
              f"{cur['cover']:9.1f}% {ref['cover']:9.1f}%")


# ------------------------------------------------------------------------------ the bare URL
def cmd_bareurl():
    a = P.rgb(str(P.VIEW / "round16c_bareurl.png"))
    b = P.rgb(P.BAKED % 1)
    mae = float(np.abs(a - b).mean())
    la, lb = float((a @ P.LUMA).mean()), float((b @ P.LUMA).mean())
    print(f"bare URL  luma {la:.2f}   station-1 preset luma {lb:.2f}   ratio {la / lb:.4f}   "
          f"MAE {mae:.2f}/255")
    d = json.loads((P.VIEW / "round16c_bareurl.json").read_text())
    print("url:", d.get("url"))
    print("page errors:", len(d.get("pageErrors") or []))
    info = d.get("info") or {}
    for k in ("foliage", "impostors", "trees", "shrubs", "lightmaps", "detail",
              "lighting_mode", "materials_mode"):
        v = info.get(k)
        if isinstance(v, dict):
            print(f"  {k}: " + json.dumps({a_: b_ for a_, b_ in v.items()
                                           if not isinstance(b_, (list, dict))})[:400])
        elif v is not None:
            print(f"  {k}: {str(v)[:240]}")


# --------------------------------------------------------------------------- perf and memory
def cmd_perf17():
    print("== frame time (median, 2560x1440) and resident GPU memory ==")
    rows = {}
    for tag, f in (("round15", "round15_perf.json"), ("round16b", "round16b_perf.json"),
                   ("r16c A", "round16c_perf.json"), ("r16c B", "round16cB_perf.json"),
                   ("r16c cold", "round16c_cold_perf.json")):
        for base in (P.VIEW, Path(__file__).resolve().parent.parent / "renders/web"):
            p = base / f
            if p.exists():
                rows[tag] = json.loads(p.read_text())
                break
    tags = list(rows)
    print(f"{'station':30s} " + " ".join(f"{t:>10s}" for t in tags) + "    best-16c - r15")
    n = len(rows[tags[-1]]["stations"])
    for i in range(n):
        name = rows[tags[-1]]["stations"][i]["name"][:28]
        v = {t: rows[t]["stations"][i]["frame_ms"]["median"] for t in tags}
        c = [v[t] for t in tags if t.startswith("r16c")]
        d = (min(c) - v["round15"]) if c and "round15" in v else float("nan")
        print(f"{name:30s} " + " ".join(f"{v[t]:9.1f}m" for t in tags) + f"   {d:+7.1f} ms")
    print()
    for tag in tags:
        d = rows[tag]
        s = d["stations"][0]["resident"]
        tot = (s["texture_bytes"] + s["render_target_bytes"] + s["geometry_bytes"]
               + s["instance_matrix_bytes"])
        st = d["stations"][0]
        print(f"{tag:10s} resident {tot / 1e6:8.1f} MB  (tex {s['texture_bytes'] / 1e6:7.1f} + rt "
              f"{s['render_target_bytes'] / 1e6:6.1f} + geo "
              f"{(s['geometry_bytes'] + s['instance_matrix_bytes']) / 1e6:6.1f})  self-reported "
              f"{s['total_bytes'] / 1e6:.1f}  {tot / 1e6 / P16.BUDGET_MB:.2f}x budget   "
              f"draws {st['draw_calls']}  tris {st['triangles'] / 1e6:.2f} M  "
              f"load {d['bytes']['loaded'] / 1e6:.1f} MB in {d['load_s']['total_s']:.2f} s")
    print()
    print(f"{'station':30s} {'draws 16b':>10s} {'draws 16c':>10s} {'tris 16b':>10s} {'tris 16c':>10s}")
    if "round16b" in rows and "r16c A" in rows:
        for i in range(n):
            a = rows["round16b"]["stations"][i]
            b = rows["r16c A"]["stations"][i]
            print(f"{b['name'][:28]:30s} {a['draw_calls']:10d} {b['draw_calls']:10d} "
                  f"{a['triangles'] / 1e6:9.2f}M {b['triangles'] / 1e6:9.2f}M")


# --------------------------------------------------------------------------- the walk clamp
def cmd_walk():
    p = P.VIEW / "round16c_walk.json"
    if not p.exists():
        print("no round16c_walk.json")
        return
    d = json.loads(p.read_text())
    probes = d.get("probes") or d.get("runs") or []
    lows, below = [], 0
    floor = None
    for pr in probes:
        g = [s.get("ground") for s in (pr.get("samples") or []) if s.get("ground") is not None]
        if g:
            lows.append(min(g))
    floor = d.get("floor_y", d.get("floor"))
    below = d.get("below_floor", d.get("n_below"))
    print(f"walk probe: {len(probes)} probes, duration {d.get('seconds', d.get('duration_s'))} s, "
          f"lowest ground {min(lows) if lows else 'n/a'}, floor {floor}, below floor {below}")
    print("keys:", sorted(d.keys())[:20])


# --------------------------------------------------------------------------- MAE per station
def cmd_mae():
    """frame.mean_abs_diff_255 out of the committed pair sheets, round 15 / 16b / 16c."""
    root = Path(__file__).resolve().parent.parent / "renders/web"
    out = {}
    for tag in ("round15", "round16b", "round16c"):
        for base in (root, P.VIEW):
            p = base / f"{tag}_pairs.json"
            if p.exists():
                out[tag] = json.loads(p.read_text())
                break
    print(f"{'station':10s} " + " ".join(f"{t:>10s}" for t in out) + "   16c-16b   16c-15")
    for st in range(1, 7):
        v = {}
        for t, d in out.items():
            for r in (d.get("sheets") or []):
                if r.get("station") == st:
                    v[t] = (r.get("frame") or {}).get("mean_abs_diff_255")
                    break
        if all(v.get(t) is not None for t in out):
            print(f"cam{st:02d}     " + " ".join(f"{v[t]:10.2f}" for t in out)
                  + f"   {v['round16c'] - v['round16b']:+7.2f}  {v['round16c'] - v['round15']:+7.2f}")
        else:
            print(f"cam{st:02d}     {v}")


if __name__ == "__main__":
    argv = [a for a in sys.argv[1:] if a not in ("--round", "17")]
    P.select_round("17")
    cmd = argv[0] if argv else "all"
    fns = {"frame": P.cmd_frame, "boxes": P.cmd_boxes, "green": P.cmd_green, "band": P.cmd_band,
           "water": P.cmd_water, "mist": P.cmd_mist, "foliage": P.cmd_foliage,
           "bloom": P16.P15.cmd_bloom, "foliage16": P16.cmd_foliage16, "crown": P16.cmd_crown,
           "norm": cmd_norm, "bareurl": cmd_bareurl, "perf17": cmd_perf17, "walk": cmd_walk,
           "mae": cmd_mae, "names": P16.cmd_names}
    for k, f in (fns.items() if cmd == "all" else [(cmd, fns[cmd])]):
        print(f"\n### {k}")
        f()
