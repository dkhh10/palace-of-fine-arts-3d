"""Trim ORN LOD0 tri counts in place (no rebuild, no re-bake: LOD1 and its normal map are untouched).

    blender --background --python scripts/orn_trim_lod0.py -- --set capital_colonnade=48000 [--set typ=N ...] [--dry]

Used to keep the master's ORN instance total down: the 114 colonnade capitals are the single biggest LOD0 block.
"""
import bpy, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import orn_lib as L

args = common.script_args()
targets = {}
for i, a in enumerate(args):
    if a == "--set" and i + 1 < len(args):
        k, v = args[i + 1].split("=")
        targets[k] = int(v)
if not targets:
    print("[trim] nothing to do")
else:
    bpy.ops.wm.open_mainfile(filepath=str(common.ASSET_FILES["ORN"]), load_ui=False)
    total_before = total_after = 0
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        t = o.get("orn_type")
        if not o.name.endswith("_LOD0") or t not in targets:
            continue
        n = L.tri_count(o)
        total_before += n
        if "--dry" not in args and n > targets[t]:
            L.decimate(o, target=targets[t])
            o["tris"] = L.tri_count(o)
        total_after += L.tri_count(o)
        print(f"[trim] {o.name}: {n} -> {L.tri_count(o)}")
    print(f"[trim] LOD0 total for {sorted(targets)}: {total_before} -> {total_after}")
    if "--dry" not in args:
        common.set_lod_visibility(1)
        bpy.ops.wm.save_as_mainfile(filepath=str(common.ASSET_FILES["ORN"]), relative_remap=True, compress=True)
        print("[trim] saved")
