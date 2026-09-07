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
CAPS = [float(v) for v in arg("--cap", [])]        # cam06 at these haze caps (k left at the file's value); 0 = haze off
VZ = arg("--vaultz", [], n=1)
VSPREAD = arg("--vaultspread", [], n=1)
FILL = arg("--fill", [], n=1)          # override LIGHT_rotunda_bounce energy for the cam04 sweep
VR = arg("--vaultr", [], n=1)          # move the vault emitters to this radius (the arch plane is ~20.5)
VTILT = arg("--vaulttilt", [], n=1)    # degrees from vertical, tilted INWARD: 0 = up-facing, 90 = facing the axis
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

for cap in CAPS:
    gn.inputs["Haze Strength"].default_value = cap
    print(f"[r08sweep] cam06 haze cap {cap:.2f} at k {gn.inputs['Haze Falloff'].default_value:.2f}")
    shoot("CAM_qa_06_aerial", f"06_cap{cap:.2f}")
if CAPS:
    gn.inputs["Haze Strength"].default_value = base_cap

vault = sorted([o for o in bpy.data.objects if o.name.startswith("LIGHT_rotunda_vault_bounce")], key=lambda o: o.name)
if VZ or VSPREAD or VR or VTILT:
    import math as _m
    from mathutils import Vector as _V
    for o in vault:
        n = _V((o.location.x, o.location.y, 0.0))
        n = n.normalized() if n.length > 1e-6 else _V((0, 1, 0))
        if VR:
            o.location.x, o.location.y = n.x * float(VR[0]), n.y * float(VR[0])
        if VZ:
            o.location.z = float(VZ[0])
        if VSPREAD:
            o.data.spread = _m.radians(float(VSPREAD[0]))
        if VTILT:
            th = _m.radians(float(VTILT[0]))
            d = (-n * _m.sin(th) + _V((0, 0, 1)) * _m.cos(th)).normalized()   # emit inward and up
            o.rotation_euler = (-d).to_track_quat("Z", "Y").to_euler()        # lights emit along local -Z
    print(f"[r08sweep] vault emitters: r {VR or '-'} z {VZ or '-'} spread {VSPREAD or '-'} tilt {VTILT or '-'}")
print(f"[r08sweep] {len(vault)} vault lights found")
if FILL:
    d = bpy.data.objects.get("LIGHT_rotunda_bounce")
    if d:
        d.data.energy = float(FILL[0])
        print(f"[r08sweep] central disk LIGHT_rotunda_bounce -> {FILL[0]} W")

for e in VAULT:
    for o in vault:
        o.data.energy = e
    print(f"[r08sweep] cam04 vault energy {e:.0f} W each")
    shoot("CAM_qa_04_rotunda_ceiling", f"04_v{e:.0f}{'_r' + VR[0] if VR else ''}{'_z' + VZ[0] if VZ else ''}{'_t' + VTILT[0] if VTILT else ''}{'_f' + FILL[0] if FILL else ''}")

print("[r08sweep] done")
