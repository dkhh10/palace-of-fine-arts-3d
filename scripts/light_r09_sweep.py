"""Round-09 knob sweeps AT DELIVERY RESOLUTION (1920x1080 / 64 spp Cycles).

Round 08b's sweep ran at 960x540 / 32 spp and its numbers turned out to be ~16 luminance and ~20 R-B optimistic on
the small hero regions (docs/lighting_notes.md section 17, "The caveat"). Everything here re-measures at the
resolution the deliverable is judged at, one render at a time, in a single Blender session (opening master.blend
costs more than the renders do). Nothing is saved back; master.blend is opened read-only.

    blender -b --python scripts/light_r09_sweep.py -- --hero CASE [CASE ...] [--res 1920 1080] [--samples 64]
    blender -b --python scripts/light_r09_sweep.py -- --vault SCALE [SCALE ...] [--cam04] ...

HERO case  = `sky,camboost,sunblue,edelta[,look]`
    sky       world Background strength for LIGHTING (SKY_STRENGTH)
    camboost  what the CAMERA sees (SKY_CAMERA_BOOST); the visible sky is sky x camboost
    sunblue   multiplier on LIGHT_sun's blue channel (SUN_BLUE_MULT)
    edelta    extra EV on top of the automatic re-calibration described below
    look      AgX look name without the "AgX - " prefix (default: the file's own look)

    The exposure is NOT left alone when `sky` changes: light_build re-runs the 18 % grey-card calibration whenever
    SKY_STRENGTH changes, so a sweep that only turned the sky down would be measuring "less light" rather than
    "less blue". The grey card's luminance is affine in the sky strength, Y(s) = A + s*B, and the two calibrations on
    record (s=2.0 -> -4.390 EV, s=1.0 -> -4.139 EV, Y(1)=3.1715) pin A and B exactly, so the compensation
    log2(Y(1)/Y(s)) is computed here in closed form. Verified against the real calibration in light_build.

VAULT case = `fillscale,vaultscale` - multipliers on LIGHT_rotunda_bounce and LIGHT_rotunda_vault_bounce_* energy,
    rendered on cam04. Cycles ignores the baked irradiance volumes, so a runtime energy override is EXACT in Cycles
    (it is only the direct term in Eevee, which is why the Eevee number is re-measured after a real rebuild + bake).
"""
import bpy, os, sys, math, time
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


# --- grey-card calibration model (see the docstring) ------------------------------------------------------------
_Y1 = 3.1715117446400227          # grey_card_linear_luminance at sky strength 1.0 (calibration_report.json)
_R = 2.0 ** (4.390 - 4.139)       # Y(2)/Y(1) from the two calibrations on record
_B = _Y1 * (_R - 1.0)                # sky-proportional part of Y at s = 1: (A+2B)/(A+B) = R with A+B = Y1 gives B = Y1(R-1)
_A = _Y1 - _B                        # sun + fill part, independent of the sky strength


def exposure_compensation(sky_strength):
    """EV that light_build's re-calibration would add when SKY_STRENGTH moves from 1.0 to `sky_strength`."""
    return math.log2(_Y1 / (_A + sky_strength * _B))


assert abs(exposure_compensation(2.0) + 0.251) < 0.002, "the model must reproduce the s=2.0 calibration on record"


HERO = arg("--hero", [])
VAULT = arg("--vault", [])
RES = [int(v) for v in arg("--res", ["1920", "1080"], n=2)]
SAMPLES = int(arg("--samples", ["64"], n=1)[0])
MASTER = arg("--master", [str(common.ROOT / "master.blend")], n=1)[0]
OUT = Path(arg("--out", [str(common.RENDERS / "previews" / "lighting")], n=1)[0])
OUT.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=MASTER, load_ui=False)
scene = bpy.context.scene
lp.apply_final_cycles(scene, samples=SAMPLES)
common.setup_scene(scene)
scene.render.image_settings.color_depth = "8"
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.resolution_percentage = 100

world = scene.world
nt = world.node_tree
n_strength = nt.nodes.get("strength")
n_camboost = nt.nodes.get("camera_boost")
sun = bpy.data.objects.get("LIGHT_sun")
base_exp = scene.view_settings.exposure
base_look = scene.view_settings.look
base_col = tuple(sun.data.color)
print(f"[r09] master {MASTER}")
print(f"[r09] base exposure {base_exp:.4f} EV, look {base_look!r}, sun colour "
      f"{tuple(round(c, 4) for c in base_col)}, A {_A:.4f} B {_B:.4f}")


def shoot(cam_name, fp):
    scene.camera = bpy.data.objects.get(cam_name)
    scene.render.filepath = str(fp)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[r09] -> {fp.name} ({time.time() - t:.1f}s)", flush=True)


for case in HERO:
    parts = case.split(",")
    s, cb, bm, de = (float(x) for x in parts[:4])
    look = ("AgX - " + parts[4].replace("_", " ")) if len(parts) > 4 and parts[4] else base_look
    try:
        scene.view_settings.look = look
    except Exception as e:
        print(f"[r09] look {look!r} rejected ({e}); available: "
              f"{[i.identifier for i in scene.view_settings.bl_rna.properties['look'].enum_items]}")
        continue
    if n_strength:
        n_strength.inputs[1].default_value = s
    if n_camboost:
        n_camboost.inputs[1].default_value = cb - 1.0
    sun.data.color = (base_col[0], base_col[1], base_col[2] * bm)
    comp = exposure_compensation(s)
    scene.view_settings.exposure = base_exp + comp + de
    tag = f"s{s:.2f}_cb{cb:.2f}_bm{bm:.2f}_e{de:+.2f}_{look.replace('AgX - ', '').replace(' ', '')}"
    print(f"[r09] hero {tag}: sky lighting x{s}, visible sky x{s * cb:.2f}, sun blue x{bm}, "
          f"exposure {base_exp:.3f} {comp:+.3f} (recalib) {de:+.3f} = {scene.view_settings.exposure:.3f}", flush=True)
    shoot("CAM_qa_01_lagoon_hero", OUT / f"r09hero_{tag}.png")

# restore before the vault pass
scene.view_settings.look = base_look
scene.view_settings.exposure = base_exp
if n_strength:
    n_strength.inputs[1].default_value = 1.0
if n_camboost:
    n_camboost.inputs[1].default_value = 1.20 - 1.0
sun.data.color = base_col

disk = bpy.data.objects.get("LIGHT_rotunda_bounce")
vault = sorted([o for o in bpy.data.objects if o.name.startswith("LIGHT_rotunda_vault_bounce")], key=lambda o: o.name)
base_disk = disk.data.energy if disk else 0.0
base_vault = vault[0].data.energy if vault else 0.0
if VAULT:
    print(f"[r09] fills: disk {base_disk:.0f} W, {len(vault)} vault emitters at {base_vault:.0f} W")
for case in VAULT:
    fs, vs = (float(x) for x in case.split(","))
    if disk:
        disk.data.energy = base_disk * fs
    for o in vault:
        o.data.energy = base_vault * vs
    tag = f"f{fs:.2f}_v{vs:.2f}"
    print(f"[r09] cam04 {tag}: disk {base_disk * fs:.0f} W, vault {base_vault * vs:.0f} W each", flush=True)
    shoot("CAM_qa_04_rotunda_ceiling", OUT / f"r09vault_{tag}.png")

print("[r09] done")
