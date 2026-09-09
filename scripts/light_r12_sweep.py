"""Round-12 sweeps: the shade (QA-05-1), the merged-master coffer (QA-05-3) and the Eevee soffit W (QA-05-9).

Round 12 is round 11's sweep with three additions and one changed default:

  * `dhue` -- the DIFFUSE-only sky hue rotation added to light_calibrate this round. Rounds 10 and 11 proved that
    saturating or boosting the diffuse sky makes the shade WARMER (the sky at a 7.4 deg sun is horizon-weighted and
    therefore warm, and most of the extra light comes back off the sunlit plaza), so the hue has to be rotated before
    it is saturated.
  * cam03 is now measured as a RATIO inside its own frame (QA round-05 (d)), so the sweep shoots cam03 in BOTH
    engines: QA scores the Eevee preview, and the Cycles frame says whether a change is real or an Eevee artifact.
  * the round-11 budget on the sunlit stone (0.02 saturation / 5 R-B) is WITHDRAWN by the lead for this round.
    Priorities: (1) cam03 shade/sunlit 0.30-0.70 and hero shade sat <= 0.55, hue 29.5 +- 8; (2) sunlit attic
    sat >= 0.50, R-B >= 110, lum 178-201; (3) columns <= 1.3x; (4) visible sky and lagoon reflection unchanged.

Round-11 header, still accurate:

Round 10's sweep only ever rendered cam01 in Cycles. Round 11's two blockers are on cam03 and cam04 and one of them
is an Eevee-only defect that depends on the BAKED light-probe volumes, so this script can

  * render any of cam01 / cam03 / cam04 in either engine on the lead's master (opened read-only, mutated in memory),
  * re-bake the irradiance volumes in memory with a chosen vault rig (the bake is what actually lights the Eevee
    vault: build_master now ends with apply_viewport_eevee, so lead_build.sh bakes the x8 + 13 m CUT-OFF rig and the
    coffers are starved in the bake itself, not only in the direct term),
  * sweep the Eevee vault override (energy scale x cutoff) and the sky's new diffuse boost / saturation.

    blender -b --python scripts/light_r12_sweep.py -- --cams 03e 03c 01c        # reproduce the merged master
    blender -b --python scripts/light_r12_sweep.py -- --case "db=4;dhue=0.55;tag=x" --cams 03e 01c
    blender -b --python scripts/light_r12_sweep.py -- --case "f=2;v=1;tag=y" --cams 04c 04e

CASE keys (anything not given keeps light_build's shipped value):
    sky SKY_STRENGTH | cb SKY_CAMERA_BOOST | gb SKY_GLOSSY_BOOST | db SKY_DIFFUSE_BOOST
    csat/gsat/dsat the three saturations | dhue SKY_DIFFUSE_HUE (0.5 = none) | bm SUN_BLUE_MULT | de extra EV
    look AgX look (spaces as '_') | tag
CAM ids: 01c 03e 04c 04e 04v (number = QA camera; c = Cycles, e = apply_preview_eevee, v = apply_viewport_eevee).
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
CAMS = arg("--cams", ["03e", "01c"])
REBAKE = arg("--rebake", ["NONE"], n=1)[0].upper()
RES = [int(v) for v in arg("--res", ["1280", "720"], n=2)]   # QA measures cam03 / cam04 at 1280x720
HERO_RES = [int(v) for v in arg("--herores", ["1920", "1080"], n=2)]
SAMPLES = int(arg("--samples", ["64"], n=1)[0])
EEVEE_SAMPLES = int(arg("--eevsamples", ["32"], n=1)[0])
# review fix 6: honour $PFA_MAIN_ROOT the way common.REFERENCE_DIR does, so a relocated checkout still works
MAIN_ROOT = Path(os.environ.get("PFA_MAIN_ROOT", str(common.MAIN_ROOT)))
MASTER = arg("--master", [str(MAIN_ROOT / "master.blend")], n=1)[0]
OUT = Path(arg("--out", [str(common.RENDERS / "previews" / "lighting")], n=1)[0])
PREFIX = arg("--prefix", ["r12"], n=1)[0]
OUT.mkdir(parents=True, exist_ok=True)

CAM_OBJ = {"01": "CAM_qa_01_lagoon_hero", "03": "CAM_qa_03_colonnade_walk", "04": "CAM_qa_04_rotunda_ceiling",
           "06": "CAM_qa_06_aerial"}

DEFAULTS = dict(sky=lb.SKY_STRENGTH, cb=lb.SKY_CAMERA_BOOST, gb=lb.SKY_GLOSSY_BOOST,
                db=getattr(lb, "SKY_DIFFUSE_BOOST", 1.0),
                csat=lb.SKY_CAMERA_SATURATION, gsat=lb.SKY_GLOSSY_SATURATION, dsat=lb.SKY_DIFFUSE_SATURATION,
                dhue=getattr(lb, "SKY_DIFFUSE_HUE", 0.5),
                tr=getattr(lb, "SKY_DIFFUSE_TINT", (1., 1., 1.))[0],   # diffuse tint, one key per channel so the
                tg=getattr(lb, "SKY_DIFFUSE_TINT", (1., 1., 1.))[1],   # existing "k=v;" case syntax still parses
                tb=getattr(lb, "SKY_DIFFUSE_TINT", (1., 1., 1.))[2],
                ta=getattr(lb, "SKY_DIFFUSE_TINT_ANTISUN", 0.0),   # anti-sun weighting of the diffuse tint
                th=getattr(lb, "SKY_DIFFUSE_TINT_HORIZON", 0.0),   # horizon-band weighting of the diffuse tint
                bm=lb.SUN_BLUE_MULT, de=0.0,
                sm=1.0,      # sun-lamp energy multiplier: sm=0 renders the SKY's contribution alone
                wm=1.0,      # world strength multiplier on top of `sky`: wm=0 renders the SUN's contribution alone
                fill=0.0,    # SHADE_FILL total irradiance in W/m2 across the three lamps (0 = off)
                fcr=-1.0, fcg=-1.0, fcb=-1.0,   # SHADE_FILL colour override, one key per channel (-1 = keep
                             # light_build's clear-sky blue 0.42/0.62/1.00). Round 10 measured that the fill makes the
                             # shaded attic WARMER partly because its own green is 0.62 of its blue: hue is
                             # (G-B)/(R-B), so a lamp whose green is high cannot lower it however blue it looks.
                spec=-1.0,   # SHADE_FILL specular_factor override (-1 = keep light_build's 0.10). ROUND 12: at 0.0
                             # the fill is DIFFUSE-ONLY, so it cannot reach the lagoon's grazing reflection or the
                             # column highlights -- the two costs that made round 10 reject the rig.
                fel=-1.0,    # SHADE_FILL elevation override in degrees (-1 = keep light_build's per-lamp value).
                             # The fill's elevation decides WHAT it lights: at 16 deg it lands on the water and the
                             # plaza at sin(16) = 0.28 and drags the near-water saturation and the columns with it;
                             # near the horizon it rakes vertical shaded stone and leaves horizontal surfaces alone.
                dif=-1.0,    # Cycles diffuse_bounces override (-1 = keep light_presets' 3). A colonnade walk is a
                             # warm stone corridor and QA-01-9 only ever tested the bounce cap on the rotunda vault,
                             # so round 12 tests whether cam03's near shaft is starved of BOUNCES rather than of light.
                f=1.0,       # LIGHT_rotunda_bounce (FILL) energy scale        -- QA-04-7
                v=1.0)       # LIGHT_rotunda_vault_bounce (VAULT_FILL) scale, applied to the PHYSICAL energy_W so
                             # light_presets.apply_vault_for_engine reproduces it in either engine


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
    bits = [f"{k}{c[k]:g}" for k in ("sky", "cb", "gb", "db", "csat", "gsat", "dsat", "dhue", "bm", "de",
                                     "tr", "tg", "tb", "ta", "th", "fill", "fel", "spec", "fcr", "fcg", "fcb", "dif", "f", "v")
            if abs(c[k] - DEFAULTS[k]) > 1e-9]
    if c["look"]:
        bits.append(c["look"].replace(" ", "").replace("_", ""))
    return "_".join(bits) or "base"


CASES = [parse(c) for c in CASES_IN] or [parse("tag=base")]
_SHADE_FILL0 = dict(lb.SHADE_FILL, lamps=[dict(l) for l in lb.SHADE_FILL["lamps"]])   # pristine copy

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
    print(f"[r12] calibrate sky {key:g}: lamp {m['lamp_energy']:.2f} W/m2 exposure {e['exposure_ev']:.3f} EV", flush=True)

bpy.ops.wm.open_mainfile(filepath=MASTER, load_ui=False)
scene = bpy.context.scene
common.setup_scene(scene)
sun = bpy.data.objects.get("LIGHT_sun")
base_look = scene.view_settings.look
# the PHYSICAL interior-fill energies, captured once so `f` / `v` are always relative to the shipped rig
_DISK = bpy.data.objects.get(lb.FILL["name"])
_VAULT = sorted([o for o in bpy.data.objects if o.name.startswith(lb.VAULT_FILL["name"])], key=lambda o: o.name)
_E_DISK0 = float(_DISK.get("energy_W", _DISK.data.energy)) if _DISK else 0.0
_E_VAULT0 = float(_VAULT[0].get("energy_W", _VAULT[0].data.energy)) if _VAULT else 0.0
print(f"[r12] master {MASTER}: exposure {scene.view_settings.exposure:.4f}, look {base_look!r}, "
      f"engine {scene.render.engine}, sun {sun.data.energy:.2f} W/m2", flush=True)


def apply_case(c):
    if case_tag(c) == "base" and not any(abs(c[k] - DEFAULTS[k]) > 1e-9 for k in DEFAULTS) and not c["look"]:
        print("[r12] case base: master left exactly as saved (no world rebuild, no shade fill)", flush=True)
        return
    energy, colour, exp_ev = _calib[c["sky"]]
    w = cal.make_sky_world(f"R11_{case_tag(c)}", AZ, EL, lb.SKY, sun_disc=False, strength=c["sky"] * c["wm"],
                           camera_boost=c["cb"], camera_saturation=c["csat"],
                           glossy_boost=c["gb"], glossy_saturation=c["gsat"],
                           diffuse_saturation=c["dsat"], diffuse_hue=c["dhue"],
                           diffuse_tint=(c["tr"], c["tg"], c["tb"]), diffuse_boost=c["db"],
                           diffuse_tint_antisun=c["ta"], diffuse_tint_horizon=c["th"])
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
    # review fix 7: rebuild the elevation override from the PRISTINE definition every case, so a case with fel >= 0
    # cannot leave its elevation behind for a later fel = -1 case to inherit.
    lb.SHADE_FILL = dict(_SHADE_FILL0) if c["fel"] < 0.0 else dict(
        _SHADE_FILL0, lamps=[dict(l, el=c["fel"]) for l in _SHADE_FILL0["lamps"]])
    if c["spec"] >= 0.0:
        lb.SHADE_FILL = dict(lb.SHADE_FILL, specular=c["spec"])
    if min(c["fcr"], c["fcg"], c["fcb"]) >= 0.0:
        lb.SHADE_FILL = dict(lb.SHADE_FILL, color=(c["fcr"], c["fcg"], c["fcb"]))
    lb.build_shade_fill(coll, energy=c["fill"])
    # interior fills (QA-04-7). Scale energy_W, not energy: apply_vault_for_engine rewrites energy from energy_W on
    # every preset call, so a scale written to energy alone would be silently undone before the render.
    if _DISK:
        _DISK["energy_W"] = _E_DISK0 * c["f"]
        _DISK.data.energy = _E_DISK0 * c["f"]
    for o in _VAULT:
        o["energy_W"] = _E_VAULT0 * c["v"]
    print(f"[r12] case {case_tag(c)}: db {c['db']:g} dsat {c['dsat']:g} dhue {c['dhue']:g} "
          f"tint {c['tr']:g},{c['tg']:g},{c['tb']:g} antisun {c['ta']:g} horizon {c['th']:g} cb {c['cb']:g} gb {c['gb']:g} "
          f"sm {c['sm']:g} wm {c['wm']:g} fill {c['fill']:g} spec {c['spec']:g} "
          f"fcol {c['fcr']:g},{c['fcg']:g},{c['fcb']:g} f {c['f']:g} ({_E_DISK0*c['f']:.0f} W) "
          f"v {c['v']:g} ({_E_VAULT0*c['v']:.0f} W) "
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
    probes.bake(scene, physical_vault=(rig == "CYCLES"))
    print(f"[r12] rebake with the {rig} vault rig: {time.time()-t:.0f}s", flush=True)


DIF = -1.0          # set per case in the loop below, read by shoot()


def shoot(cam_id, tag):
    num, eng = cam_id[:2], cam_id[2:]
    scene.camera = bpy.data.objects.get(CAM_OBJ[num])
    res = HERO_RES if num == "01" and eng == "c" else RES
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.color_depth = "8"
    if eng == "c":
        lp.apply_final_cycles(scene, samples=SAMPLES, time_limit=0.0)
        if DIF >= 0:
            scene.cycles.diffuse_bounces = int(DIF)
            scene.cycles.max_bounces = max(scene.cycles.max_bounces, int(DIF))
            print(f"[r12] cycles diffuse_bounces {scene.cycles.diffuse_bounces} "
                  f"max_bounces {scene.cycles.max_bounces}", flush=True)
    elif eng == "v":                      # QA-04-12: the viewport preset (taa 8/16, raytracing off,
                                          # light_threshold 0.01 since round 11)
        lp.apply_viewport_eevee(scene)
    else:
        lp.apply_preview_eevee(scene, samples=EEVEE_SAMPLES)
    fp = OUT / f"{PREFIX}_{tag}_{num}{eng}.png"
    scene.render.filepath = str(fp)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[r12] -> {fp.name} ({time.time()-t:.1f}s, {res[0]}x{res[1]})", flush=True)


for c in CASES:
    apply_case(c)
    DIF = c["dif"]
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

print("[r12] done", flush=True)
