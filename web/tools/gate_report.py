#!/usr/bin/env python3
"""One table of the numbers a gate report needs, out of the files gate2.sh already writes.

    python3 web/tools/gate_report.py [--tag gate2] [--dir renders/web]

Reads <dir>/<tag>_perf.json (the 1440p pass) and <dir>/<tag>_pairs.json (the pair sheets) and prints
per station: presented frame time, gl.finish GPU cost, draw calls, triangles, and the pair sheet's
whole-frame luma and linear ratio against the Phase 5 render; then the load bytes, the resident bytes
with the render targets and the texture-format histogram, and the PBR report (sets matched, files,
bytes, unmatched materials).  No adjectives, only what is in the JSON.
"""
import argparse, json, sys
from pathlib import Path

MB = lambda b: f"{(b or 0) / 1e6:.1f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="gate2")
    ap.add_argument("--dir", default="renders/web")
    a = ap.parse_args()
    d = Path(a.dir)
    perf_p, pairs_p = d / f"{a.tag}_perf.json", d / f"{a.tag}_pairs.json"
    if not perf_p.exists():
        print(f"no {perf_p}", file=sys.stderr)
        return 1
    perf = json.loads(perf_p.read_text())
    pairs = json.loads(pairs_p.read_text()) if pairs_p.exists() else {"sheets": []}
    by_station = {s.get("station"): s for s in pairs.get("sheets", [])}

    print(f"{a.tag}: {perf.get('schema')}  lighting {perf.get('lighting_mode')}  materials {perf.get('materials_mode')}  "
          f"{perf.get('size')}  {perf.get('frames')} frames after {perf.get('warmup')} warm-up")
    print(f"{'st':>2} {'name':<34} {'ms':>6} {'gpu':>6} {'p95':>6} {'draws':>6} {'Mtris':>7} {'luma v/r':>12} {'x lin':>7}")
    for s in perf.get("stations", []):
        n = s["station"]
        f = (by_station.get(n) or {}).get("frame", {})
        fm, gc = s.get("frame_ms") or {}, s.get("gpu_cost_ms") or {}
        print(f"{n:>2} {s['name']:<34} {fm.get('median', 0):6.2f} {gc.get('median', 0):6.2f} {gc.get('p95', 0):6.2f} "
              f"{s.get('draw_calls', 0):6d} {s.get('triangles', 0) / 1e6:7.2f} "
              f"{str(f.get('viewer_luma', '-')):>5}/{str(f.get('reference_luma', '-')):<6} {str(f.get('ratio_linear', '-')):>7}")

    b, l = perf.get("bytes") or {}, perf.get("load_s") or {}
    print(f"\nload  {MB(b.get('loaded'))} MB of {MB(b.get('planned'))} MB planned in {l.get('total_s', 0):.2f} s "
          f"(sky {l.get('sky_s', 0):.2f}, lut {l.get('lut_s', 0):.2f}, glb {l.get('glb_s', 0):.2f}, tex {l.get('tex_s', 0):.2f})")
    r = (perf.get("stations") or [{}])[0].get("resident") or {}
    if r:
        print(f"resident {MB(r.get('total_bytes'))} MB = tex {MB(r.get('texture_bytes'))} + rt {MB(r.get('render_target_bytes'))} "
              f"+ geo {MB((r.get('geometry_bytes') or 0) + (r.get('instance_matrix_bytes') or 0))}  "
              f"({r.get('textures')} textures {r.get('texture_formats')})")
        for t in r.get("render_targets", []):
            print(f"   rt {t['what']:<24} {t['size'][0]}x{t['size'][1]} samples {t['samples']}  {MB(t['bytes'])} MB")
    m = perf.get("materials")
    if m:
        print(f"pbr   {m['matched']}/{m['materials_in_scene']} materials from {m['sets_used']}/{m['sets_in_manifest']} sets, "
              f"{m['textures']} attachments, {m['unique_files']} files, {MB(m['bytes'])} MB, formats {m['formats']}")
        print(f"      factors first: {m.get('factored')} materials, {m.get('constant_only')} finished by factors alone, "
              f"{len(m.get('without_uv1') or [])} without UV1; kept glb normal {m.get('kept_glb_normal')}, "
              f"replaced {m.get('replaced_glb_normal')}, kept glb AO {m.get('kept_glb_ao')}")
        if m.get("unmatched"):
            print(f"      unmatched ({len(m['unmatched'])}): " + ", ".join(u["material"] for u in m["unmatched"][:10]))
        if m.get("failed"):
            print(f"      FAILED ({len(m['failed'])}): " + "; ".join(f"{f['url'].split('/')[-1]} {f['error']}" for f in m["failed"][:5]))
        if m.get("nearest_first"):
            print("      nearest first: " + ", ".join(f"{r['rank']}:{r['material'].split('__')[-1]} {r['distance_m']}m" for r in m["nearest_first"][:6]))
    c = perf.get("chunking")
    if c:
        print(f"chunk {c['split']}/{c['candidates']} batches -> {c['chunks']} regional, +{c['added']} draws max")
    return 0


if __name__ == "__main__":
    sys.exit(main())
