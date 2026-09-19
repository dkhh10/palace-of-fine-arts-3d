#!/usr/bin/env python3
"""Phase 8 far-tree A/B: one table from the perf jsons `web/tools/p7.sh perf` writes.

    python3 web/tools/p8_perf_table.py p8lodA_perf p8lodB_perf ... [--stations 1,2,5]

Per setting and station: median frame time (the number the A/B is judged on), GPU cost median,
draw calls, triangles and resident MB — and the whole-run medians, so a setting can be compared with
the SAME-SESSION default (which the batch repeats last as the drift control).
"""
import argparse, json, statistics as st
from pathlib import Path

W = Path(__file__).resolve().parents[2] / "renders" / "web"


def resident_mb(s):
    r = s.get("resident") or {}
    b = sum(v for k, v in r.items() if k.endswith("_bytes") and isinstance(v, (int, float)))
    return b / 1048576.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tags", nargs="+")
    ap.add_argument("--stations", default="1,2,3,4,5,6")
    a = ap.parse_args()
    want = [int(x) for x in a.stations.split(",")]
    print(f"{'setting':16s} {'station':8s} {'frame ms':>9s} {'fps':>6s} {'gpu ms':>7s} "
          f"{'draws':>6s} {'tris':>9s} {'resident MB':>12s}")
    summary = {}
    for tag in a.tags:
        p = W / f"{tag}.json"
        if not p.exists():
            p = W / f"{tag}_perf.json"
        if not p.exists():
            print(f"{tag:16s} (missing {p.name})")
            continue
        d = json.load(open(p))
        med, res, dr, tr = [], [], [], []
        for s in d.get("stations", []):
            if s["station"] not in want:
                continue
            fm = s["frame_ms"]["median"]
            med.append(fm)
            res.append(resident_mb(s))
            dr.append(s["draw_calls"])
            tr.append(s["triangles"])
            print(f"{tag if len(med) == 1 else '':16s} cam{s['station']:02d}    {fm:9.2f} "
                  f"{1000.0 / max(fm, 1e-6):6.1f} {s.get('gpu_cost_ms', {}).get('median', float('nan')):7.2f} "
                  f"{s['draw_calls']:6d} {s['triangles']:9d} {resident_mb(s):12.1f}")
        if med:
            summary[tag] = (st.median(med), max(med), st.median(res), max(dr), max(tr))
            print(f"{'':16s} MEDIAN   {st.median(med):9.2f} {1000.0 / st.median(med):6.1f} "
                  f"{'':7s} {max(dr):6d} {max(tr):9d} {st.median(res):12.1f}")
        print()
    if len(summary) > 1:
        base = list(summary)[0]
        print(f"== against {base} (same session) ==")
        for tag, (m, worst, r, dr, tr) in summary.items():
            b = summary[base]
            print(f"{tag:16s} median {m:7.2f} ms ({m - b[0]:+.2f}), worst station {worst:7.2f} ms "
                  f"({worst - b[1]:+.2f}), resident {r:7.1f} MB ({r - b[2]:+.1f}), "
                  f"draws {dr:5d} ({dr - b[3]:+d}), tris {tr} ({tr - b[4]:+d})")


if __name__ == "__main__":
    main()
