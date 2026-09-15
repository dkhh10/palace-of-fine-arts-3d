"""Gate 3 report: every number in the bake engineer's report, printed from the records. Nothing typed by hand.

    python3 export/gate3_report.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate3_common as g3  # noqa: E402

jobs = {j["id"]: j for j in g3.read_jobs()["jobs"]}
recs = {p.stem: json.loads(p.read_text()) for p in sorted(g3.REC.glob("*.json"))}
status = json.loads((g3.QUEUE / "status.json").read_text())
qjobs = {j["id"]: j for j in status.get("jobs", []) if j["id"] in jobs}

print("== queue ==")
by_kind = {}
for jid, j in jobs.items():
    k = j["kind"]
    d = by_kind.setdefault(k, dict(n=0, done=0, wall=0.0, bake=0.0, rc=[]))
    d["n"] += 1
    if jid in recs:
        d["done"] += 1
        d["wall"] += recs[jid].get("wall_s", 0.0)
        d["bake"] += recs[jid].get("bake_s", recs[jid].get("render_s", 0.0))
    q = qjobs.get(jid)
    if q and q["rc"] != 0:
        d["rc"].append((jid, q["rc"]))
tot = dict(n=0, done=0, wall=0.0, bake=0.0)
print(f"{'kind':14s} {'jobs':>5s} {'done':>5s} {'wall_s':>9s} {'bake_s':>9s}  failures")
for k in sorted(by_kind):
    d = by_kind[k]
    for f in ("n", "done"):
        tot[f] += d[f]
    tot["wall"] += d["wall"]
    tot["bake"] += d["bake"]
    print(f"{k:14s} {d['n']:5d} {d['done']:5d} {d['wall']:9.1f} {d['bake']:9.1f}  {d['rc'] or ''}")
print(f"{'TOTAL':14s} {tot['n']:5d} {tot['done']:5d} {tot['wall']:9.1f} {tot['bake']:9.1f}"
      f"   state={status.get('state')} queue_done={status.get('done')}/{status.get('total')}")

print("\n== per-map EXR range (source, before any encoding) ==")
print(f"{'map':52s} {'px':>5s} {'cov':>6s} {'cm/tx':>6s} {'min':>5s} {'max':>8s} {'mean':>8s} {'p99':>8s} "
      f"{'rng':>5s} {'clip':>5s} {'g2 relp99':>9s} {'rgbm relp99':>11s} {'bake_s':>7s}")
setj = json.loads((g3.OUT / "gate3_set.json").read_text())
own_rows = {r["object"]: r for r in setj["own_maps"]}
rows = []
for jid, r in recs.items():
    if r["kind"] not in ("own", "own_gate1uv2"):
        continue
    row = own_rows[r["object"]]
    g1 = r["kind"] == "own_gate1uv2"
    m = r["map"]
    rows.append((r["object"] + (" [gate1 UV2]" if g1 else ""), r["size"],
                 row["coverage_gate1"] if g1 else row["coverage"],
                 row["cm_per_texel_gate1"] if g1 else row["cm_per_texel"], m, r["bake_s"]))
comp = json.loads((g3.OUT / "compose.json").read_text()) if (g3.OUT / "compose.json").exists() else {}
for k, a in sorted((comp.get("atlases") or {}).items()):
    rows.append((k, a["size"][0], None, None, a, None))
for name, px, cov, cm, m, bs in sorted(rows, key=lambda t: t[0]):
    st = m["stats"]
    print(f"{name[:52]:52s} {px:5d} {cov if cov is not None else '-':>6} {cm if cm is not None else '-':>6} "
          f"{st['min']:5.2f} {st['max']:8.3f} {st['mean']:8.4f} {st['p99']:8.3f} {m['range']:5.0f} "
          f"{st['clipped_px_vs_range']:5d} {m['gamma2']['roundtrip']['rel_p99']:9.4f} "
          f"{m['rgbm8']['roundtrip']['rel_p99']:11.4f} {bs if bs is not None else '-':>7}")

print("\n== slot atlases ==")
per_job = [(jid, r) for jid, r in recs.items() if r["kind"] == "slot"]
n_inst = sum(r["n"] for _, r in per_job)
s_inst = sum(r["bake_s"] for _, r in per_job)
print(f"{len(per_job)} batches, {n_inst} instances, {s_inst:.1f} s bake, "
      f"{s_inst / max(n_inst, 1):.2f} s/instance (Gate 0 reference 5.1 s)")
for k, a in sorted((comp.get("atlases") or {}).items()):
    print(f"  {k:34s} {a['slots_filled']:4d}/{a['slots_expected']:<4d} slots  range {a['range']:5.0f}  "
          f"max {a['stats']['max']:8.3f}  mean {a['stats']['mean']:7.4f}  "
          f"slot_check abs {a.get('slot_check', {}).get('abs_max')}")
v = comp.get("vertex") or {}
if v:
    print(f"  vertex irradiance: {v['meshes']} meshes {v['verts']} verts range {v['range']} "
          f"{v['bytes']} B npz")

print("\n== impostors ==")
imp = [(jid, r) for jid, r in recs.items() if r["kind"] == "impostor"]
print(f"{'prototype':36s} {'views':>5s} {'s':>7s} {'s/view':>7s} {'rng':>5s} {'alpha':>6s} "
      f"{'alb1k B':>9s} {'alb2k B':>9s} {'nd1k B':>9s}")
for jid, r in sorted(imp):
    f = r["files"]
    print(f"{r['prototype'][:36]:36s} {r['views']:5d} {r['render_s']:7.1f} {r['s_per_view']:7.3f} "
          f"{r['range']:5.0f} {r['alpha_coverage']:6.3f} {f['albedo_1024']['bytes']:9d} "
          f"{f['albedo_2048']['bytes']:9d} {f['normdepth_1024']['bytes']:9d}")
if imp:
    print(f"  total {sum(r['render_s'] for _, r in imp):.1f} s, "
          f"{sum(sum(x['bytes'] for x in r['files'].values()) for _, r in imp)} B of PNG")

pr = recs.get("probe_hero")
if pr:
    print("\n== probe ==")
    print(f"  {pr['station']} mirrored to {pr['position_blender']} (gltf {pr['position_gltf']}), "
          f"{pr['rendered_px']} -> {pr['ship_px']} px, {pr['samples']} spp, {pr['bake_s']} s")
    for k, f in pr["faces"].items():
        print(f"   {k:3s} mean {f['mean']:9.5f} max {f['max']:9.3f} hdr B {f['hdr_bytes']:8d} "
              f"rel_p99 {f['hdr_rel_p99']}")
sk = recs.get("sky_diffuse")
if sk:
    print(f"\n== sky.diffuse == {sk['w']}x{sk['h']} {sk['render_s']} s max {sk['stats']['max']} "
          f"mean {sk['stats']['mean']} upper/lower {sk['upper_mean']}/{sk['lower_mean']} "
          f"hdr {sk['hdr_bytes']} B rel_p99 {sk['hdr_rel_p99']}")

mp = g3.OUT / "manifest.json"
if mp.exists():
    b = json.loads(mp.read_text())["budget"]
    print("\n== resident ==")
    for k, vv in b["resident_mb"].items():
        print(f"  {k:34s} {vv:9.2f}")
    print(f"  budget {b['budget_mb']} MB | gate3 measured {b['gate3_measured_mb']} vs reservation "
          f"{b['gate3_reservation_mb']} ({b['gate3_vs_reservation_mb']:+.2f}) | "
          f"measured-basis total {b['measured_total_mb']}")
