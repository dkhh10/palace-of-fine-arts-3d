#!/usr/bin/env python3
"""Gate 2 step 6: the numbers the bake engineer's report quotes, straight out of the records.

    python3 export/gate2_report.py

Reads export/out/gate2/{bake_jobs.json, bake/*.json, manifest.json, verify.json} and the KTX2 directories.
Prints per-class job counts and wall seconds, texture bytes (UASTC on disk, ETC1S where it exists, ASTC
resident), the resident sum against the 1 200 MB budget, and the verification boxes. Writes nothing.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "export"))
import gate2_common as g2  # noqa: E402

OUT = g2.OUT
jobs = {j["id"]: j for j in g2.read_jobs()["jobs"]}
recs = {p.stem: json.loads(p.read_text()) for p in sorted((OUT / "bake").glob("*.json"))}
man = json.loads((OUT / "manifest.json").read_text()) if (OUT / "manifest.json").exists() else {}
files = man.get("textures", {}).get("gate2", {}).get("files", {})

cls_rows = {}
for jid, rec in recs.items():
    c = jobs[jid]["cls"]
    r = cls_rows.setdefault(c, dict(jobs=0, maps=0, bake_s=0.0, png_bytes=0, ktx2_bytes=0, etc1s_bytes=0,
                                    resident_mb=0.0, shipped=0, constant=0))
    r["jobs"] += 1
    for kind, m in rec["maps"].items():
        r["maps"] += 1
        r["bake_s"] += m["bake_s"]
        r["png_bytes"] += m["bytes"]
        f = files.get(f"gate2_{jid}_{kind}")
        if f:
            r["shipped"] += 1
            r["ktx2_bytes"] += f.get("bytes") or 0
            r["etc1s_bytes"] += f.get("etc1s_bytes") or 0
            r["resident_mb"] += f.get("resident_mb") or 0.0
        else:
            r["constant"] += 1

n_sets = len(man.get("materials", {}).get("sets", {}))
if n_sets != len(recs):
    print(f"WARNING manifest.json has {n_sets} material sets but {len(recs)} bake records exist - "
          f"run `python3 export/manifest_v3.py` first, or every missing map counts as constant below")
print(f"jobs done {len(recs)}/{len(jobs)}")
print("%-9s %5s %5s %6s %5s %10s %13s %12s %11s" %
      ("class", "jobs", "maps", "ship", "const", "bake_s", "ktx2_B", "etc1s_B", "resident_MB"))
tot = dict(jobs=0, maps=0, shipped=0, constant=0, bake_s=0.0, ktx2_bytes=0, etc1s_bytes=0, resident_mb=0.0)
for c in ("arch", "ground", "backdrop", "orn"):
    r = cls_rows.get(c)
    if not r:
        continue
    print("%-9s %5d %5d %6d %5d %10.1f %13d %12d %11.2f" %
          (c, r["jobs"], r["maps"], r["shipped"], r["constant"], r["bake_s"], r["ktx2_bytes"],
           r["etc1s_bytes"], r["resident_mb"]))
    for k in tot:
        tot[k] += r[k]
print("%-9s %5d %5d %6d %5d %10.1f %13d %12d %11.2f" %
      ("TOTAL", tot["jobs"], tot["maps"], tot["shipped"], tot["constant"], tot["bake_s"],
       tot["ktx2_bytes"], tot["etc1s_bytes"], tot["resident_mb"]))

b = man.get("budget")
if b:
    print("\nresident estimate (ASTC 4x4 = 1 B/texel x 4/3 mips):")
    for k, v in b["resident_mb"].items():
        print(f"  {k:26s} {v:9.2f} MB")
    print(f"  budget                     {b['budget_mb']:9.2f} MB   "
          f"{'UNDER by' if b['resident_mb']['total'] <= b['budget_mb'] else 'OVER by'} "
          f"{abs(b['budget_mb'] - b['resident_mb']['total']):.2f} MB")

# the 2K -> 1K roughness reduction, measured per group
rms = [(jid, m["downsample_rms"], m["stats"]["std"][0])
       for jid, rec in recs.items() for kind, m in rec["maps"].items()
       if kind == "roughness" and m["ship_px"] != m["bake_px"]]
if rms:
    print(f"\nroughness 2K->1K reduction over {len(rms)} groups: "
          f"RMS mean {sum(r[1] for r in rms) / len(rms):.4f}, worst {max(r[1] for r in rms):.4f} "
          f"(the maps' own std averages {sum(r[2] for r in rms) / len(rms):.4f})")

v = OUT / "verify.json"
if v.exists():
    d = json.loads(v.read_text())
    print(f"\nverification (Gate 0 slice, cam01, 1280x720, 64 spp, compositor detached):")
    for k, box in d["boxes"].items():
        print(f"  {k:18s} procedural {box['procedural']:.6f}  baked {box['baked']:.6f}  "
              f"{box['delta_pct']:+.2f} %   ({box['px']} px)")
    print(f"  frame mean         procedural {d['frame_mean']['procedural']:.6f}  "
          f"baked {d['frame_mean']['baked']:.6f}  {d['frame_mean']['delta_pct']:+.2f} %")
    print(f"  worst box |delta| {d['worst_abs_delta_pct']} %   pass(<=3 %) = {d['pass_3pct']}")
