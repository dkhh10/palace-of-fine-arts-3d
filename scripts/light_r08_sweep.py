"""Round-08 knob sweeps for QA-02-8 (aerial haze) and QA-02-12 (vault soffits), in ONE Blender session.

Opening master.blend costs more than these renders do, so both sweeps share a session. Nothing is saved back:
the file is opened read-only and the process exits when the script ends.

    blender -b --python scripts/light_r08_sweep.py -- [--haze 1.33 2.22 5.0] [--vault 520 1600 4000]
                                                      [--res 960 540] [--samples 16] [--out DIR]

Haze sweep: cam06, varying the COMP_golden_hour "Haze Falloff" k (extinction length L = MIST depth / k).
Vault sweep: cam04, varying LIGHT_rotunda_vault_bounce_* energy. The baked irradiance volumes still hold the
indirect from the shipped energies, so the sweep measures the DIRECT response only - which is the part that
lights a soffit. Re-bake (scripts/lead_build.sh) before believing an absolute number.
"""
import bpy, sys, os, time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_presets as lp

args = common.script_args()


def arg(name, default, n=0):
    if name not in args:
        return default
    out = []
    for v in args[args.index(name) + 1:]:
        if v.startswith("--"):
            break
        out.append(v)
        if n and len(out) >= n:
            break
    return out or default


HAZE = [float(v) for v in arg("--haze", ["1.33", "2.22", "5.0"])]
VAULT = [float(v) for v in arg("--vault", ["520", "1600", "4000"])]
RES = [int(v) for v in arg("--res", ["960", "540"], n=2)]
SAMPLES = int(arg("--samples", ["16"], n=1)[0])
OUT = Path(arg("--out", [str(common.RENDERS / "previews" / "lighting")], n=1)[0])
OUT.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=str(common.ROOT / "master.blend"), load_ui=False)
scene = bpy.context.scene
lp.apply_preview_eevee(scene, samples=SAMPLES)
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.resolution_percentage = 100


def haze_node():
    """The COMP_golden_hour group node inside the scene's compositor tree (5.2: scene.compositing_node_group)."""
    tree = getattr(scene, "compositing_node_group", None) or getattr(scene, "node_tree", None)
    if tree is None:
        return None
    for n in tree.nodes:
        if n.type == "GROUP" and n.node_tree and n.node_tree.name == "COMP_golden_hour":
            return n
    return None


def shoot(cam_name, tag):
    cam = bpy.data.objects.get(cam_name)
    scene.camera = cam
    fp = OUT / f"r08sweep_{tag}.png"
    scene.render.filepath = str(fp)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[r08sweep] {tag} -> {fp.name} ({time.time() - t:.1f}s)")
    return fp


gn = haze_node()
if gn is None:
    print("[r08sweep] COMP_golden_hour group node not found in the scene tree; haze sweep skipped")
    HAZE = []
else:
    base_k = gn.inputs["Haze Falloff"].default_value
    base_cap = gn.inputs["Haze Strength"].default_value
    depth = scene.world.mist_settings.depth
    print(f"[r08sweep] haze base: cap {base_cap:.2f}, k {base_k:.2f} (L = {depth / base_k:.0f} m), mist depth {depth:.0f}")

for k in HAZE:
    gn.inputs["Haze Falloff"].default_value = k
    print(f"[r08sweep] cam06 haze k {k:.2f} -> L {scene.world.mist_settings.depth / k:.0f} m")
    shoot("CAM_qa_06_aerial", f"06_k{k:.2f}")
if HAZE:
    gn.inputs["Haze Falloff"].default_value = base_k

vault = sorted([o for o in bpy.data.objects if o.name.startswith("LIGHT_rotunda_vault_bounce")], key=lambda o: o.name)
print(f"[r08sweep] {len(vault)} vault lights found")
for e in VAULT:
    for o in vault:
        o.data.energy = e
    print(f"[r08sweep] cam04 vault energy {e:.0f} W each")
    shoot("CAM_qa_04_rotunda_ceiling", f"04_v{e:.0f}")

print("[r08sweep] done")
