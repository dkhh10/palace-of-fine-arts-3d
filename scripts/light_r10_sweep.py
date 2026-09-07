"""Round-10 sweeps. Unlike round 09 this one can move the SKY MODEL itself (aerosol / ozone / air density), so every
case re-runs the real calibration (light_calibrate.measure_sky + measure_exposure) instead of the closed-form
sky-strength compensation: the lamp energy and colour ARE the sky's own sun disc, so changing the atmosphere changes
the sun, and a sweep that held the lamp fixed would be measuring a physically impossible rig.

    blender -b --python scripts/light_r10_sweep.py -- --baseline
    blender -b --python scripts/light_r10_sweep.py -- --hero "aer=4;oz=1;cb=1.2" "aer=6;oz=0.6" [--res 960 540] [--samples 48]
    blender -b --python scripts/light_r10_sweep.py -- --cam04 --vault "f=1;v=1"        # item 6, Eevee vs Cycles
    blender -b --python scripts/light_r10_sweep.py -- --cam06 --comp "haze=0.5;k=2.5"  # item 5

CASE is a ';'-separated k=v list; anything not given keeps light_build's shipped value.
    sky   SKY_STRENGTH          cb   SKY_CAMERA_BOOST      gb   SKY_GLOSSY_BOOST
    csat  SKY_CAMERA_SATURATION gsat SKY_GLOSSY_SATURATION dsat SKY_DIFFUSE_SATURATION
    bm    SUN_BLUE_MULT         aer  aerosol_density       oz   ozone_density   air air_density  alt altitude
    de    extra EV on top of the recalibration             look AgX look, spaces as '_'
    tag   filename tag
Nothing is written back to master.blend; it is opened read-only and mutated in memory.
"""
import bpy, os, sys, math, time, json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_presets as lp
import light_build as lb
import light_calibrate as cal

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


HERO = arg("--hero", [])
VAULT = arg("--vault", [])
RES = [int(v) for v in arg("--res", ["1920", "1080"], n=2)]
SAMPLES = int(arg("--samples", ["64"], n=1)[0])
MASTER = arg("--master", [str(common.ROOT / "master.blend")], n=1)[0]
OUT = Path(arg("--out", [str(common.RENDERS / "previews" / "lighting")], n=1)[0])
PREFIX = arg("--prefix", ["r10"], n=1)[0]
OUT.mkdir(parents=True, exist_ok=True)

DEFAULTS = dict(f=1.0, v=1.0, sky=lb.SKY_STRENGTH, cb=lb.SKY_CAMERA_BOOST, gb=lb.SKY_GLOSSY_BOOST,
                csat=lb.SKY_CAMERA_SATURATION, gsat=getattr(lb, "SKY_GLOSSY_SATURATION", lb.SKY_CAMERA_SATURATION),
                dsat=getattr(lb, "SKY_DIFFUSE_SATURATION", 1.0), bm=lb.SUN_BLUE_MULT,
                aer=lb.SKY["aerosol_density"], oz=lb.SKY["ozone_density"], air=lb.SKY["air_density"],
                alt=lb.SKY["altitude"], de=0.0)


def parse(case):
    c = dict(DEFAULTS)
    c["look"] = None
    c["tag"] = None
    for part in case.split(";"):
        part = part.strip()
        if not part:
            continue
        k, v = part.split("=", 1)
        k = k.strip()
        if k in ("look", "tag"):
            c[k] = v
        else:
            c[k] = float(v)
    return c


def case_tag(c):
    if c["tag"]:
        return c["tag"]
    bits = []
    for k in ("aer", "oz", "air", "sky", "cb", "gb", "csat", "gsat", "dsat", "bm", "de", "f", "v"):
        if abs(c[k] - DEFAULTS[k]) > 1e-9:
            bits.append(f"{k}{c[k]:g}")
    if c["look"]:
        bits.append(c["look"].replace(" ", "").replace("_", ""))
    return "_".join(bits) or "base"


# --- every calibration runs BEFORE master.blend is opened ---------------------------------------------------------
# light_calibrate._fresh_scene() calls wm.read_homefile(use_empty=True), i.e. it wipes the whole session. Calibrating
# after opening master.blend therefore destroys it (round-10 bug: "StructRNA of type Scene has been removed").
AZ, EL, SRC = lb.solar_position("morning")
CASES = [parse(c) for c in HERO]
_calib_cache = {}


def _sky_dict(c):
    return dict(lb.SKY, aerosol_density=c["aer"], ozone_density=c["oz"], air_density=c["air"], altitude=c["alt"])


def _key(c):
    return (c["aer"], c["oz"], c["air"], c["alt"], c["sky"])


for c in CASES:
    if _key(c) in _calib_cache:
        continue
    skyd = _sky_dict(c)
    t = time.time()
    m = cal.measure_sky(AZ, EL, skyd, samples=512)
    e = cal.measure_exposure(AZ, EL, m["lamp_energy"], m["sun_color_normalised"], skyd,
                             samples=256, sky_strength=c["sky"])
    _calib_cache[_key(c)] = (m["lamp_energy"], list(m["sun_color_normalised"]), e["exposure_ev"])
    print(f"[r10] calibrate aer {c['aer']:g} oz {c['oz']:g} air {c['air']:g} sky {c['sky']:g}: "
          f"lamp {m['lamp_energy']:.2f} W/m2 colour {[round(v,4) for v in m['sun_color_normalised']]}, "
          f"exposure {e['exposure_ev']:.3f} EV, L_zenith {[round(v,3) for v in m['L_zenith']]}, "
          f"L_horizon_west {[round(v,3) for v in m['L_horizon_west']]}, "
          f"L_sunward {[round(v,3) for v in m['L_horizon_sunward']]} ({time.time()-t:.0f}s)", flush=True)

bpy.ops.wm.open_mainfile(filepath=MASTER, load_ui=False)
scene = bpy.context.scene
common.setup_scene(scene)
sun = bpy.data.objects.get("LIGHT_sun")
master_world = scene.world
base_exp = scene.view_settings.exposure
base_look = scene.view_settings.look
print(f"[r10] master {MASTER}: exposure {base_exp:.4f}, look {base_look!r}, sun az {AZ:.2f} el {EL:.2f} ({SRC}), "
      f"energy {sun.data.energy:.2f}, colour {tuple(round(v,4) for v in sun.data.color)}, "
      f"world {master_world.name!r}", flush=True)
print(f"[r10] light_build says: sky {lb.SKY}, strength {lb.SKY_STRENGTH}, camboost {lb.SKY_CAMERA_BOOST}, "
      f"glossyboost {lb.SKY_GLOSSY_BOOST}, csat {lb.SKY_CAMERA_SATURATION}, sunblue {lb.SUN_BLUE_MULT}, "
      f"bias {lb.EXPOSURE_BIAS}, look {lp.LOOK!r}", flush=True)


def apply_case(c):
    energy, colour, exp_ev = _calib_cache[_key(c)]
    skyd = _sky_dict(c)
    w = cal.make_sky_world(f"R10_{case_tag(c)}", AZ, EL, skyd, sun_disc=False, strength=c["sky"],
                           camera_boost=c["cb"], camera_saturation=c["csat"], glossy_boost=c["gb"],
                           glossy_saturation=c["gsat"], diffuse_saturation=c["dsat"])
    ms = w.mist_settings
    ms.use_mist = True
    ms.start, ms.depth, ms.falloff = lb.MIST["start"], lb.MIST["depth"], lb.MIST["falloff"]
    scene.world = w
    sun.data.energy = energy
    sun.data.color = (colour[0], colour[1], colour[2] * c["bm"])
    scene.view_settings.exposure = exp_ev + lb.EXPOSURE_BIAS + c["de"]
    if c["look"]:
        scene.view_settings.look = "AgX - " + c["look"].replace("_", " ")
    else:
        scene.view_settings.look = base_look
    print(f"[r10] case {case_tag(c)}: exposure {scene.view_settings.exposure:.3f} EV "
          f"(cal {exp_ev:.3f} + bias {lb.EXPOSURE_BIAS} + {c['de']:+.2f}), look {scene.view_settings.look!r}, "
          f"sun {energy:.2f} W/m2 {tuple(round(v,4) for v in sun.data.color)}", flush=True)


def shoot(cam_name, fp):
    scene.camera = bpy.data.objects.get(cam_name)
    scene.render.filepath = str(fp)
    scene.render.image_settings.color_depth = "8"
    scene.render.resolution_x, scene.render.resolution_y = RES
    scene.render.resolution_percentage = 100
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[r10] -> {fp.name} ({time.time() - t:.1f}s)", flush=True)


CAM01, CAM04, CAM06 = "CAM_qa_01_lagoon_hero", "CAM_qa_04_rotunda_ceiling", "CAM_qa_06_aerial"

# ---- baseline: render the merged master EXACTLY as it stands, no overrides -------------------------------------
if "--baseline" in args:
    lp.apply_final_cycles(scene, samples=SAMPLES)
    shoot(CAM01, OUT / f"{PREFIX}_base_01_hero_cycles.png")
    if "--cam04" in args:
        shoot(CAM04, OUT / f"{PREFIX}_base_04_ceiling_cycles.png")
        lp.apply_preview_eevee(scene, samples=64)
        shoot(CAM04, OUT / f"{PREFIX}_base_04_ceiling_eevee.png")
    if "--cam06" in args:
        lp.apply_preview_eevee(scene, samples=64)
        shoot(CAM06, OUT / f"{PREFIX}_base_06_aerial_eevee.png")

# ---- hero cases -------------------------------------------------------------------------------------------------
_disk0 = bpy.data.objects.get(lb.FILL["name"])
_vault0 = sorted([o for o in bpy.data.objects if o.name.startswith(lb.VAULT_FILL["name"])], key=lambda o: o.name)
_e_disk0 = _disk0.data.energy if _disk0 else 0.0
_e_vault0 = _vault0[0].data.energy if _vault0 else 0.0
for c in CASES:
    apply_case(c)
    if _disk0:
        _disk0.data.energy = _e_disk0 * c["f"]
    for o in _vault0:
        o.data.energy = _e_vault0 * c["v"]
    lp.apply_final_cycles(scene, samples=SAMPLES)
    shoot(CAM01, OUT / f"{PREFIX}hero_{case_tag(c)}.png")
    if _disk0:
        _disk0.data.energy = _e_disk0
    for o in _vault0:
        o.data.energy = _e_vault0
    if "--also04" in args:
        shoot(CAM04, OUT / f"{PREFIX}c04_{case_tag(c)}.png")
    if "--also06" in args:
        lp.apply_preview_eevee(scene, samples=64)
        shoot(CAM06, OUT / f"{PREFIX}c06_{case_tag(c)}.png")

# ---- vault / interior-fill cases (item 6): every case is rendered in BOTH engines --------------------------------
disk = bpy.data.objects.get(lb.FILL["name"])
vault = sorted([o for o in bpy.data.objects if o.name.startswith(lb.VAULT_FILL["name"])], key=lambda o: o.name)
base_disk = disk.data.energy if disk else 0.0
base_vault = vault[0].data.energy if vault else 0.0
base_spread = math.degrees(vault[0].data.spread) if vault else 0.0
if VAULT:
    print(f"[r10] fills: disk {base_disk:.0f} W, {len(vault)} vault emitters {base_vault:.0f} W, "
          f"spread {base_spread:.0f} deg", flush=True)
def set_fills(fscale, vscale, spread, cut=0.0, dcut=0.0):
    """cut/dcut = Eevee `Custom Distance` (light.cutoff_distance) in metres, 0 = off.
    Cycles IGNORES cutoff_distance, Eevee honours it, so it is a genuinely engine-conditional lever that needs no
    second set of lights: it is the one knob that can stop the vault emitters from reaching the central coffered
    dome (~20.7 m away) while still lighting their own soffit (4.5-11 m)."""
    if disk:
        disk.data.energy = base_disk * fscale
        disk.data.use_custom_distance = dcut > 0.0
        if dcut > 0.0:
            disk.data.cutoff_distance = dcut
    for o in vault:
        o.data.energy = base_vault * vscale
        o.data.spread = math.radians(spread)
        o.data.use_custom_distance = cut > 0.0
        if cut > 0.0:
            o.data.cutoff_distance = cut


for case in VAULT:
    d = dict(f=1.0, v=1.0, sp=base_spread, cut=0.0, dcut=0.0, ef=None, ev=None, esp=None, ecut=None, edcut=None)
    for part in case.split(";"):
        if part.strip():
            k, val = part.split("=", 1)
            d[k.strip()] = float(val)
    tag = f"f{d['f']:g}_v{d['v']:g}_sp{d['sp']:g}" + (f"_cut{d['cut']:g}" if d["cut"] else "") \
        + (f"_dcut{d['dcut']:g}" if d["dcut"] else "")
    set_fills(d["f"], d["v"], d["sp"], d["cut"], d["dcut"])
    if "--noC" not in args:
        lp.apply_final_cycles(scene, samples=SAMPLES)
        shoot(CAM04, OUT / f"{PREFIX}v_{tag}_cycles.png")
    # Eevee gets its OWN energies / cutoffs if the case supplies them (ef/ev/esp/ecut/edcut): the engine-conditional fix
    if any(d[k] is not None for k in ("ef", "ev", "esp", "ecut", "edcut")):
        ef = d["f"] if d["ef"] is None else d["ef"]
        ev = d["v"] if d["ev"] is None else d["ev"]
        esp = d["sp"] if d["esp"] is None else d["esp"]
        ecut = d["cut"] if d["ecut"] is None else d["ecut"]
        edcut = d["dcut"] if d["edcut"] is None else d["edcut"]
        set_fills(ef, ev, esp, ecut, edcut)
        tag += f"_E{ef:g}_{ev:g}_{esp:g}_{ecut:g}_{edcut:g}"
    lp.apply_preview_eevee(scene, samples=64)
    shoot(CAM04, OUT / f"{PREFIX}v_{tag}_eevee.png")
    set_fills(1.0, 1.0, base_spread)

# ---- compositor haze cases (item 5) -------------------------------------------------------------------------------
COMPC = arg("--comp", [])
if COMPC:
    grp = None
    for n in scene.node_tree.nodes if scene.use_nodes and scene.node_tree else []:
        if n.type == "GROUP" and n.node_tree and n.node_tree.name == lb.GROUP_NAME:
            grp = n
    print(f"[r10] compositor group node: {grp!r}", flush=True)
for case in COMPC:
    d = dict(haze=lb.COMP["haze_strength"], k=lb.COMP["haze_extinction"])
    for part in case.split(";"):
        if part.strip():
            kk, val = part.split("=", 1)
            d[kk.strip()] = float(val)
    if grp:
        grp.inputs["Haze Strength"].default_value = d["haze"]
        grp.inputs["Haze Falloff"].default_value = d["k"]
    lp.apply_preview_eevee(scene, samples=64)
    shoot(CAM06, OUT / f"{PREFIX}c06_haze{d['haze']:g}_k{d['k']:g}.png")

print("[r10] done", flush=True)
