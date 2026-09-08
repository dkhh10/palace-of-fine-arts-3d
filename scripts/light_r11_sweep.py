"""Round-11 sweeps: the colonnade shade (QA-04-2) and the Eevee vault (QA-04-1).

Round 10's sweep only ever rendered cam01 in Cycles. Round 11's two blockers are on cam03 and cam04 and one of them
is an Eevee-only defect that depends on the BAKED light-probe volumes, so this script can

  * render any of cam01 / cam03 / cam04 in either engine on the lead's master (opened read-only, mutated in memory),
  * re-bake the irradiance volumes in memory with a chosen vault rig (the bake is what actually lights the Eevee
    vault: build_master now ends with apply_viewport_eevee, so lead_build.sh bakes the x8 + 13 m CUT-OFF rig and the
    coffers are starved in the bake itself, not only in the direct term),
  * sweep the Eevee vault override (energy scale x cutoff) and the sky's new diffuse boost / saturation.

    blender -b --python scripts/light_r11_sweep.py -- --cams 03e 04e            # reproduce QA round 04
    blender -b --python scripts/light_r11_sweep.py -- --rebake CYCLES --cams 04e 04c
    blender -b --python scripts/light_r11_sweep.py -- --evault "cut=25;e=4" "cut=0;e=1" --cams 04e
    blender -b --python scripts/light_r11_sweep.py -- --case "db=2.5;tag=db2.5" --cams 03e 01c

CASE keys (anything not given keeps light_build's shipped value):
    sky SKY_STRENGTH | cb SKY_CAMERA_BOOST | gb SKY_GLOSSY_BOOST | db SKY_DIFFUSE_BOOST
    csat/gsat/dsat the three saturations | bm SUN_BLUE_MULT | de extra EV | look AgX look (spaces as '_') | tag
CAM ids: 01c 01e 03c 03e 04c 04e (number = QA camera, c = Cycles, e = Eevee preview preset).
"""
import bpy, os, sys, math, time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_presets as lp
import light_build as lb
import light_calibrate as cal
import light_probes as probes

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


CASES_IN = arg("--case", [])
EVAULT = arg("--evault", [])
CAMS = arg("--cams", ["03e", "04e"])
REBAKE = arg("--rebake", ["NONE"], n=1)[0].upper()
RES = [int(v) for v in arg("--res", ["1280", "720"], n=2)]
HERO_RES = [int(v) for v in arg("--herores", ["1920", "1080"], n=2)]
SAMPLES = int(arg("--samples", ["64"], n=1)[0])
EEVEE_SAMPLES = int(arg("--eevsamples", ["32"], n=1)[0])
MASTER = arg("--master", [str(common.MAIN_ROOT / "master.blend")], n=1)[0]
OUT = Path(arg("--out", [str(common.RENDERS / "previews" / "lighting")], n=1)[0])
PREFIX = arg("--prefix", ["r11"], n=1)[0]
OUT.mkdir(parents=True, exist_ok=True)

CAM_OBJ = {"01": "CAM_qa_01_lagoon_hero", "03": "CAM_qa_03_colonnade_walk", "04": "CAM_qa_04_rotunda_ceiling",
           "06": "CAM_qa_06_aerial"}

DEFAULTS = dict(sky=lb.SKY_STRENGTH, cb=lb.SKY_CAMERA_BOOST, gb=lb.SKY_GLOSSY_BOOST,
                db=getattr(lb, "SKY_DIFFUSE_BOOST", 1.0),
                csat=lb.SKY_CAMERA_SATURATION, gsat=lb.SKY_GLOSSY_SATURATION, dsat=lb.SKY_DIFFUSE_SATURATION,
                bm=lb.SUN_BLUE_MULT, de=0.0,
                sm=1.0,      # sun-lamp energy multiplier: sm=0 renders the SKY's contribution alone
                wm=1.0,      # world strength multiplier on top of `sky`: wm=0 renders the SUN's contribution alone
                fill=0.0)    # SHADE_FILL total irradiance in W/m2 across the three lamps (0 = off)


def parse(case):
    c = dict(DEFAULTS, look=None, tag=None)
    for part in case.split(";"):
        part = part.strip()
        if not part:
            continue
        k, v = part.split("=", 1)
        k = k.strip()
        c[k] = v if k in ("look", "tag") else float(v)
    return c


def case_tag(c):
    if c["tag"]:
        return c["tag"]
    bits = [f"{k}{c[k]:g}" for k in ("sky", "cb", "gb", "db", "csat", "gsat", "dsat", "bm", "de")
            if abs(c[k] - DEFAULTS[k]) > 1e-9]
    if c["look"]:
        bits.append(c["look"].replace(" ", "").replace("_", ""))
    return "_".join(bits) or "base"


CASES = [parse(c) for c in CASES_IN] or [parse("tag=base")]

# --- calibration first: light_calibrate._fresh_scene() wipes the session, so it can never run after master is open
AZ, EL, SRC = lb.solar_position("morning")
_calib = {}
for c in CASES:
    key = c["sky"]
    if key in _calib:
        continue
    m = cal.measure_sky(AZ, EL, lb.SKY, samples=512)
    e = cal.measure_exposure(AZ, EL, m["lamp_energy"], m["sun_color_normalised"], lb.SKY,
                             samples=256, sky_strength=key)
    _calib[key] = (m["lamp_energy"], list(m["sun_color_normalised"]), e["exposure_ev"])
    print(f"[r11] calibrate sky {key:g}: lamp {m['lamp_energy']:.2f} W/m2 exposure {e['exposure_ev']:.3f} EV", flush=True)

bpy.ops.wm.open_mainfile(filepath=MASTER, load_ui=False)
scene = bpy.context.scene
common.setup_scene(scene)
sun = bpy.data.objects.get("LIGHT_sun")
base_look = scene.view_settings.look
print(f"[r11] master {MASTER}: exposure {scene.view_settings.exposure:.4f}, look {base_look!r}, "
      f"engine {scene.render.engine}, sun {sun.data.energy:.2f} W/m2", flush=True)


def apply_case(c):
    if case_tag(c) == "base" and not any(abs(c[k] - DEFAULTS[k]) > 1e-9 for k in DEFAULTS) and not c["look"]:
        print("[r11] case base: master left exactly as saved (no world rebuild, no shade fill)", flush=True)
        return
    energy, colour, exp_ev = _calib[c["sky"]]
    w = cal.make_sky_world(f"R11_{case_tag(c)}", AZ, EL, lb.SKY, sun_disc=False, strength=c["sky"] * c["wm"],
                           camera_boost=c["cb"], camera_saturation=c["csat"],
                           glossy_boost=c["gb"], glossy_saturation=c["gsat"],
                           diffuse_saturation=c["dsat"], diffuse_boost=c["db"])
    ms = w.mist_settings
    ms.use_mist = True
    ms.start, ms.depth, ms.falloff = lb.MIST["start"], lb.MIST["depth"], lb.MIST["falloff"]
    scene.world = w
    sun.data.energy = energy * c["sm"]
    sun.data.color = (colour[0], colour[1], colour[2] * c["bm"])
    scene.view_settings.exposure = exp_ev + lb.EXPOSURE_BIAS + c["de"]
    scene.view_settings.look = ("AgX - " + c["look"].replace("_", " ")) if c["look"] else base_look
    # SHADE_FILL: rebuilt in memory every case (master.blend does not carry it until the lead re-links LIGHT).
    # `fill` is the TOTAL irradiance in W/m2 across the lamps, i.e. directly comparable with the sun's 67.3.
    coll = bpy.data.collections.get(lb.COLLECTION) or scene.collection
    lb.SUN_REFERENCE_W = energy
    lb.build_shade_fill(coll, energy=c["fill"])
    print(f"[r11] case {case_tag(c)}: db {c['db']:g} dsat {c['dsat']:g} cb {c['cb']:g} gb {c['gb']:g} "
          f"sm {c['sm']:g} wm {c['wm']:g} fill {c['fill']:g} "
          f"exposure {scene.view_settings.exposure:.3f} EV, sun {sun.data.energy:.2f} W/m2", flush=True)


def set_evault(scale, cutoff):
    """Override light_presets.EEVEE_VAULT for this run (apply_*_eevee reads it every time it is called)."""
    lp.EEVEE_VAULT["energy_scale"] = scale
    lp.EEVEE_VAULT["cutoff_distance"] = cutoff


def rebake(rig):
    """Re-bake the two irradiance volumes with the vault emitters in `rig` ("CYCLES" = physical, "EEVEE" = override).
    The bake is a function of the rig that is live when it runs, and it is what lights the Eevee vault."""
    lp.apply_vault_for_engine(rig)
    t = time.time()
    probes.bake(scene)
    print(f"[r11] rebake with the {rig} vault rig: {time.time()-t:.0f}s", flush=True)


def shoot(cam_id, tag):
    num, eng = cam_id[:2], cam_id[2:]
    scene.camera = bpy.data.objects.get(CAM_OBJ[num])
    res = HERO_RES if num == "01" and eng == "c" else RES
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.color_depth = "8"
    if eng == "c":
        lp.apply_final_cycles(scene, samples=SAMPLES, time_limit=0.0)
    else:
        lp.apply_preview_eevee(scene, samples=EEVEE_SAMPLES)
    fp = OUT / f"{PREFIX}_{tag}_{num}{eng}.png"
    scene.render.filepath = str(fp)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[r11] -> {fp.name} ({time.time()-t:.1f}s, {res[0]}x{res[1]})", flush=True)


for c in CASES:
    apply_case(c)
    if REBAKE != "NONE":      # AFTER the world change: the Eevee shade is lit by the BAKE, not by the live world
        rebake(REBAKE)
    tag = case_tag(c)
    if EVAULT:
        for ev in EVAULT:
            d = dict(e=lp.EEVEE_VAULT["energy_scale"], cut=lp.EEVEE_VAULT["cutoff_distance"])
            for part in ev.split(";"):
                if part.strip():
                    k, v = part.split("=", 1)
                    d[k.strip()] = float(v)
            set_evault(d["e"], d["cut"])
            for cam in CAMS:
                shoot(cam, f"{tag}_e{d['e']:g}cut{d['cut']:g}")
    else:
        for cam in CAMS:
            shoot(cam, tag)

print("[r11] done", flush=True)
