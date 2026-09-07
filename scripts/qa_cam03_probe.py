"""QA probe for the CAM_qa_03 re-station (QA / Critic owned). Reads master.blend, never saves it, never edits
scripts/qa_cameras.py. Lists colonnade column positions, or renders candidate camera stations at low cost.

    blender -b --python scripts/qa_cam03_probe.py -- --list
    blender -b --python scripts/qa_cam03_probe.py -- --cams "name:x,y,z:tx,ty,tz:lens" [more...] [--res 640 360] [--samples 8]

Outputs go to the scratch dir given by --out (default /tmp/qa_cam03).
"""
import bpy, sys, os, math, time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

args = common.script_args()


def arg(name, default=None, n=1):
    if name not in args:
        return default
    i = args.index(name) + 1
    vals = []
    for v in args[i:]:
        if v.startswith("--"):
            break
        vals.append(v)
        if n and len(vals) >= n:
            break
    return vals[0] if n == 1 else vals


bpy.ops.wm.open_mainfile(filepath=str(common.ROOT / "master.blend"), load_ui=False)
scene = bpy.context.scene

if "--list" in args:
    pat = arg("--pat", "shaft")
    cols = [o for o in bpy.data.objects if o.name.startswith("ARCH_colonnade_south") and pat in o.name]
    print(f"[probe] {len(cols)} colonnade column objects")
    for o in sorted(cols, key=lambda o: o.name):
        l = o.matrix_world.translation
        print(f"  {o.name:46s} x {l.x:8.2f}  y {l.y:8.2f}  z {l.z:6.2f}")
    for pre in ("ARCH_colonnade", "ARCH_pylon", "ARCH_planter", "ENV_tree"):
        names = sorted({o.name.rsplit("_", 1)[0] for o in bpy.data.objects if o.name.startswith(pre)})
        print(f"[probe] {pre}* families: {len(names)}  e.g. {names[:6]}")
else:
    RES = [int(v) for v in arg("--res", ["640", "360"], n=2)]
    SAMPLES = int(arg("--samples", 8))
    OUT = Path(arg("--out", "/tmp/qa_cam03"))
    OUT.mkdir(parents=True, exist_ok=True)
    specs = arg("--cams", [], n=0) or []
    import light_presets
    light_presets.apply_preview_eevee(scene, samples=SAMPLES)
    scene.render.resolution_x, scene.render.resolution_y = RES
    scene.render.resolution_percentage = 100
    for s in specs:
        name, loc, tgt, lens = s.split(":")
        loc = tuple(float(v) for v in loc.split(","))
        tgt = tuple(float(v) for v in tgt.split(","))
        cam_data = bpy.data.cameras.new("PROBE_" + name)
        cam_data.lens = float(lens)
        cam_data.sensor_width = 36.0
        cam_data.sensor_fit = "HORIZONTAL"
        cam_data.clip_start, cam_data.clip_end = 0.1, 5000.0
        obj = bpy.data.objects.new("PROBE_" + name, cam_data)
        obj.location = loc
        obj.rotation_euler = common.lookat_rotation(loc, tgt)
        scene.collection.objects.link(obj)
        scene.camera = obj
        fp = OUT / f"cam03_{name}.png"
        scene.render.filepath = str(fp)
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"[probe] {name} loc {loc} target {tgt} lens {lens} -> {fp} ({time.time()-t:.1f}s)")

print("[probe] done")
