"""ORN round 5 stats / socket / coverage check (no render).

    scripts/blender_run.sh 900 -- --background --python scripts/orn_r5_stats.py -- [--orn PATH] [--types a,b]

Reports, all measured on meshes and socket empties, never on an image:
  1. socket census from assets/architecture.blend: every orn_type, its count, and whether ORN ships an asset for it
     (the build_master.py ORN_COLL coverage check);
  2. frieze_run fit: for each distinct rotunda run length, the ORN asset that serves it and the length mismatch;
  3. band metrics for the rinceau panels: areal coverage of the 0.90 m band, proud depth above the frieze face
     (y = RIN_EMBED behind the asset's min-y), max proud vs the 0.16 m architrave-crown clearance, and the lateral
     shadow each proud element throws at the hero sun (az 118.5 / el 7.4 on a face whose normal is az 82);
  4. the LOD tri table for every ORN type, with the budget and pass/fail;
  5. per-instance variation available to the lead: distinct (design, variant_seed) pairs per socket type.
"""
import bpy, sys, os, math, statistics
from collections import defaultdict
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import orn_lib as L

ARGS = common.script_args()
ORN_BLEND = ARGS[ARGS.index("--orn") + 1] if "--orn" in ARGS else str(common.ASSET_FILES["ORN"])
ONLY = ARGS[ARGS.index("--types") + 1].split(",") if "--types" in ARGS else None
EMBED = 0.015            # orn_build.RIN_EMBED: how far the rinceau is sunk into the frieze face
CROWN_CLEAR = 0.16       # architrave crown at d 0.50 vs frieze face at d 0.34 (docs/arch_notes.md r4b profile)
SUN_AZ, SUN_EL, FACE_AZ = 118.5, 7.4, 82.0

# ------------------------------------------------------------------ 1/2/5: sockets (architecture.blend)
bpy.ops.wm.open_mainfile(filepath=str(common.ASSET_FILES["ARCH"]), load_ui=False)
bpy.context.view_layer.update()
socket_types = defaultdict(list)
for o in bpy.data.objects:
    if o.name.startswith("SOCKET_") and o.get("orn_type"):
        socket_types[o["orn_type"]].append({
            "name": o.name, "z": o.matrix_world.translation.z,
            "run": float(o.get("run_length", o.get("size_hint", 0.0)) or 0.0),
            "host": o.get("host"), "subtype": o.get("subtype"),
            "design": o.get("design"), "seed": int(o.get("variant_seed", 0) or 0),
            "hint": float(o.get("size_hint", 0.0) or 0.0)})

# ------------------------------------------------------------------ ornament library
bpy.ops.wm.open_mainfile(filepath=ORN_BLEND, load_ui=False)
assets = defaultdict(lambda: defaultdict(dict))     # type -> variant -> lod -> obj
import re
pat = re.compile(r"^ORN_(.+?)_v(\d+)_LOD(\d)$")
for o in bpy.data.objects:
    m = pat.match(o.name)
    if m and o.type == "MESH":
        assets[m.group(1)][int(m.group(2))][int(m.group(3))] = o

print("\n=== 1. socket census vs ORN assets (build_master.py ORN_COLL coverage) ===")
SERVES = {"capital_rotunda": "capital_rotunda", "capital_inner": "capital_inner",
          "capital_colonnade": "capital_colonnade", "maiden": "maiden", "attic_figure": "attic_figure",
          "attic_panel": "attic_panel", "keystone": "keystone", "inner_figure": "winged_figure",
          "finial": "finial", "rosette_ceiling": "rosette_ceiling", "urn": "urn", "drum_band": "drum_band",
          "frieze_run": "frieze_rinceau"}
for t in sorted(socket_types):
    lst = socket_types[t]
    a = SERVES.get(t)
    have = a in assets if a else False
    print(f"  {t:16s} n={len(lst):4d}  ORN asset: {a or '-':22s} {'PRESENT' if have else 'MISSING'}")

print("\n=== 2. frieze_run fit ===")
groups = defaultdict(list)
for s in socket_types.get("frieze_run", []):
    groups[(s["host"] or "rotunda", s["subtype"] or "rinceau", round(s["run"], 3))].append(s)
for key in sorted(groups, key=lambda k: (str(k[0]), k[2])):
    host, sub, run = key
    lst = groups[key]
    z = statistics.fmean(s["z"] for s in lst)
    served, err = "-", ""
    if host == "rotunda":
        best = None
        for t in ("frieze_rinceau", "frieze_rinceau_return"):
            for v, lods in assets.get(t, {}).items():
                o = lods.get(1) or lods.get(0)
                if o is None:
                    continue
                (x0, _, _), (x1, _, _) = L.bbox(o)
                d = abs((x1 - x0) - run)
                if best is None or d < best[1]:
                    best = (t, d, x1 - x0)
        if best:
            served, err = best[0], f"asset {best[2]:.3f} m, mismatch {best[1]*1000:5.1f} mm"
    print(f"  host={host:12s} sub={sub:10s} run={run:6.3f} n={len(lst):3d} z={z:6.2f}  -> {served:24s} {err}")

print("\n=== 3. rinceau band metrics ===")


def band_metrics(obj, nx=520, nz=100):
    from mathutils.bvhtree import BVHTree
    mw = obj.matrix_world
    verts = [mw @ v.co for v in obj.data.vertices]
    polys = [tuple(p.vertices) for p in obj.data.polygons]
    bvh = BVHTree.FromPolygons(verts, polys, all_triangles=False, epsilon=0.0)
    bb = [mw @ Vector(c) for c in obj.bound_box]
    x0, x1 = min(v.x for v in bb), max(v.x for v in bb)
    y1 = max(v.y for v in bb)
    z0, z1 = min(v.z for v in bb), max(v.z for v in bb)
    hits, depths = 0, []
    n = 0
    for i in range(nx):
        x = x0 + (i + 0.5) * (x1 - x0) / nx
        for k in range(nz):
            z = z0 + (k + 0.5) * (z1 - z0) / nz
            n += 1
            loc, nor, idx, dist = bvh.ray_cast(Vector((x, y1 + 0.5, z)), Vector((0, -1, 0)))
            if loc is None:
                continue
            hits += 1
            depths.append(loc.y)          # already measured from the wall plane y = 0
    depths.sort()
    return x1 - x0, z1 - z0, hits / n, depths


lat = math.tan(math.radians(SUN_AZ - FACE_AZ)) if abs(SUN_AZ - FACE_AZ) < 89 else float("inf")
for t in ("frieze_rinceau", "frieze_rinceau_return"):
    for v in sorted(assets.get(t, {})):
        for lod in (0, 1, 2):
            o = assets[t][v].get(lod)
            if o is None or (lod and lod != 1):
                continue
            w, h, cov, d = band_metrics(o)
            if not d:
                continue
            band = float(o.get("band_height", h) or h)
            cov *= h / band          # coverage of the WHOLE band, not just the carved field
            p = lambda q: d[min(len(d) - 1, int(q * len(d)))]
            print(f"  {o.name:36s} {w:.3f} x {h:.3f} m field in a {band:.2f} m band, coverage {cov*100:5.1f} % "
                  f"of the band ({cov*band/h*100:4.1f} % of the field)  proud above the frieze face: "
                  f"p50 {p(.5)*1000:5.1f}  p90 {p(.9)*1000:5.1f}  max {d[-1]*1000:5.1f} mm  "
                  f"clearance to the architrave crown {(CROWN_CLEAR - d[-1])*1000:5.1f} mm  "
                  f"lateral shadow at max proud {d[-1]*lat*1000:5.1f} mm")

print("\n=== 4. LOD tri table ===")
for t in sorted(assets):
    if ONLY and t not in ONLY:
        continue
    bud = L.BUDGETS.get(t, L.BUDGETS["moulding"] if t in ("dentil", "egg_and_dart", "greek_key", "rosette_band",
                                                          "modillion", "anthemion", "drum_band") else L.BUDGETS["default"])
    for v in sorted(assets[t]):
        tris = {lod: L.tri_count(o) for lod, o in sorted(assets[t][v].items())}
        ok = all(tris.get(i, 0) <= bud[i] for i in range(3) if i in tris)
        print(f"  {('ORN_' + t + '_v' + str(v)):40s} " +
              " / ".join(f"LOD{i} {tris.get(i, 0):7d}" for i in range(3)) +
              f"   budget {bud[0]}/{bud[1]}/{bud[2]}  {'ok' if ok else '*** OVER ***'}")

print("\n=== 5. per-instance variation available to the lead ===")
for t in sorted(socket_types):
    lst = socket_types[t]
    seeds = {s["seed"] for s in lst}
    designs = {s["design"] for s in lst if s["design"]}
    nvar = len(assets.get(SERVES.get(t, ""), {}))
    print(f"  {t:16s} sockets {len(lst):4d}  distinct variant_seed {len(seeds):4d}  designs {sorted(designs) or '-'}"
          f"  ORN variants {nvar}")
