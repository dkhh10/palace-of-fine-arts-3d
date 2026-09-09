"""ORN round 5 repair tool: rebuild every LOD2 in assets/ornament.blend that is over its tier budget.

    scripts/blender_run.sh 1800 -- --background --python scripts/orn_r5_lod2fix.py -- [--voxel 0.10] [--dry]

SUPERSEDED for new builds (ORN r5 review finding 5): the voxel-weld path now lives in
`orn_lib.enforce_lod2_budget` and runs inside `finalize_asset`, so ANY rebuild of an asset already lands its LOD2
inside budget. This script stays only as an in-place repair for a .blend built before that change; on a current
file it prints "nothing to do" and writes nothing.

Collapse decimation cannot go below ~4 faces per shell, so a LOD2 made of thousands of disjoint shells (the attic
panels after the field clamp) stalls far above budget. A voxel remesh welds the shells into one surface first, and
the collapse then reaches the budget. Silhouette only: LOD2 is used beyond ~200 m. The LOD2 OBJECT is kept (name,
material, custom properties, viewport state); only its mesh data is replaced, so build_master.py sees no change.
"""
import bpy, sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import orn_lib as L

ARGS = common.script_args()
VOXEL = float(ARGS[ARGS.index("--voxel") + 1]) if "--voxel" in ARGS else 0.10
DRY = "--dry" in ARGS
pat = re.compile(r"^ORN_(.+?)_v(\d+)_LOD2$")

bpy.ops.wm.open_mainfile(filepath=str(common.ASSET_FILES["ORN"]), load_ui=False)
fixed = []
for lod2 in sorted([o for o in bpy.data.objects if pat.match(o.name) and o.type == "MESH"], key=lambda o: o.name):
    m = pat.match(lod2.name)
    typ, var = m.group(1), m.group(2)
    budget = L.BUDGETS.get(typ, L.BUDGETS["default"])[2]
    before = L.tri_count(lod2)
    if before <= budget:
        continue
    src = bpy.data.objects.get(f"ORN_{typ}_v{var}_LOD1") or bpy.data.objects.get(f"ORN_{typ}_v{var}_LOD0")
    if src is None:
        print(f"[fix] {lod2.name}: {before} tris over {budget} but no LOD1/LOD0 source")
        continue
    print(f"[fix] {lod2.name}: {before} tris > budget {budget}; rebuilding from {src.name} at voxel {VOXEL}")
    if DRY:
        continue
    # single implementation, shared with the build path (orn_lib.finalize_asset)
    L.enforce_lod2_budget(lod2, src, budget, voxel=VOXEL)
    after = L.tri_count(lod2)
    (x0, y0, z0), (x1, y1, z1) = L.bbox(lod2)
    lod2["tris"] = after
    lod2["size"] = f"{x1 - x0:.2f} x {y1 - y0:.2f} x {z1 - z0:.2f} m (x y z)"
    lod2.hide_viewport = True
    fixed.append((lod2.name, before, after, budget))

print("\n[fix] LOD2 rebuilds")
for n, b, a, bud in fixed:
    print(f"  {n:34s} {b:7d} -> {a:6d} tris (budget {bud})")
if fixed and not DRY:
    common.set_lod_visibility(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(common.ASSET_FILES["ORN"]), relative_remap=True, compress=True)
    print(f"[fix] saved {common.ASSET_FILES['ORN']}")
else:
    print("[fix] nothing to do" if not fixed else "[fix] dry run, nothing written")
