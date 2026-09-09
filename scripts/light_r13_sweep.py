"""Round-13 sweep: the Eevee shade (item 1), cam06's mist (item 2) and the wing / shore sky term (item 3).

Round 12's sweep only ever changed the WORLD and the fills. Round 13 has to change three more things, so this
script adds them as case keys rather than as separate scripts:

  * `bake` -- which world the Eevee irradiance volumes are baked with. 1 = the round-13 lighting world
    (light_probes.bake_world: the diffuse branch on every ray), 2 = the round-12 behaviour (bake with the scene
    world, which Eevee captures as a camera ray), 0 = do not re-bake, use the master's saved cache.
  * `ms` / `md` -- MIST start (the near limit) and depth. QA-05-8 / ENV's hand-off: COMP_golden_hour's mist adds
    +58 lum to cam06's horizon crop and cuts its std 44.0 -> 23.5, flattening the far-shore line that
    environment's geometry now produces un-composited.
  * `hz` / `hk` -- the compositor's haze cap and extinction. `comp=0` renders with the compositor off, which is
    the un-composited reference the hand-off is stated against.

    scripts/blender_run.sh 1200 -- --background --python scripts/light_r13_sweep.py -- --cams 01e 01c
    scripts/blender_run.sh 900  -- --background --python scripts/light_r13_sweep.py -- \
        --case "tag=nocomp;comp=0" --case "tag=ship" --cams 06e
"""
import bpy, os, sys, time
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
CAMS = arg("--cams", ["01e", "01c"])
RES = [int(v) for v in arg("--res", ["1280", "720"], n=2)]
HERO_RES = [int(v) for v in arg("--herores", ["1920", "1080"], n=2)]
SAMPLES = int(arg("--samples", ["64"], n=1)[0])
EEVEE_SAMPLES = int(arg("--eevsamples", ["32"], n=1)[0])
MASTER = arg("--master", [str(common.ROOT / "master.blend")], n=1)[0]   # THIS worktree's master, per the round-12 lesson
OUT = Path(arg("--out", [str(common.RENDERS / "previews" / "lighting")], n=1)[0])
PREFIX = arg("--prefix", ["r13"], n=1)[0]
# --border x0 y0 x1 y1 in HERO pixels (1920x1080): render only that rectangle and leave the rest black, WITHOUT
# cropping, so every measurement box still lands on the same pixel coordinates. A carry that only needs the attic
# and the water costs a quarter of a frame instead of a whole one.
BORDER = [int(v) for v in arg("--border", [], n=4)]
OUT.mkdir(parents=True, exist_ok=True)

CAM_OBJ = {"01": "CAM_qa_01_lagoon_hero", "02": "CAM_qa_02_lagoon_ne_threequarter",
           "03": "CAM_qa_03_colonnade_walk", "04": "CAM_qa_04_rotunda_ceiling",
           "05": "CAM_qa_05_south_lawn", "06": "CAM_qa_06_aerial"}

DEFAULTS = dict(sky=lb.SKY_STRENGTH, cb=lb.SKY_CAMERA_BOOST, gb=lb.SKY_GLOSSY_BOOST, db=lb.SKY_DIFFUSE_BOOST,
                csat=lb.SKY_CAMERA_SATURATION, gsat=lb.SKY_GLOSSY_SATURATION, dsat=lb.SKY_DIFFUSE_SATURATION,
                dhue=lb.SKY_DIFFUSE_HUE,
                tr=lb.SKY_DIFFUSE_TINT[0], tg=lb.SKY_DIFFUSE_TINT[1], tb=lb.SKY_DIFFUSE_TINT[2],
                ta=lb.SKY_DIFFUSE_TINT_ANTISUN, th=lb.SKY_DIFFUSE_TINT_HORIZON,
                bm=lb.SUN_BLUE_MULT, de=0.0,
                f=1.0, v=1.0,                     # FILL / VAULT_FILL energy scales
                bake=1.0,                         # 1 lighting world, 2 camera (round 12), 0 no re-bake
                comp=1.0,                         # compositor on/off
                ms=lb.MIST["start"], md=lb.MIST["depth"],
                hz=lb.COMP["haze_strength"], hk=lb.COMP["haze_extinction"],
                # SHADE_FILL, as in the round-12 sweep: total irradiance in W/m2 across the three anti-sun lamps,
                # their elevation, their specular factor and their colour. Round 13 uses it as an EEVEE-ONLY rig
                # (Cycles already has the shade; see docs/lighting_notes.md 22), so the round-10 costs it was
                # rejected for -- near-water saturation and the column highlights in CYCLES -- do not apply.
                fill=0.0, fel=-1.0, spec=-1.0, fcr=-1.0, fcg=-1.0, fcb=-1.0,
                # EEVEE-ONLY preset overrides, applied AFTER light_presets.apply_preview_eevee. `fgi` is
                # fast_gi_distance in metres (-1 = fast GI off), `rt` raytracing on/off, `fgir` the fast-GI ray
                # count, `thr` light_threshold. Eevee's horizon scan is what decides how much of the world SH an
                # occluded surface is allowed to see, so it -- not the world -- is the shaded stone's real knob.
                fgi=-2.0, rt=-1.0, fgir=-1.0, thr=-1.0)
SKY_KEYS = ("sky", "cb", "gb", "db", "csat", "gsat", "dsat", "dhue", "tr", "tg", "tb", "ta", "th", "bm", "de")


def parse(case):
    c = dict(DEFAULTS, tag=None)
    for part in case.split(";"):
        part = part.strip()
        if not part:
            continue
        k, v = part.split("=", 1)
        k = k.strip()
        c[k] = v if k == "tag" else float(v)
    return c


def case_tag(c):
    if c["tag"]:
        return c["tag"]
    bits = [f"{k}{c[k]:g}" for k in DEFAULTS if abs(c[k] - DEFAULTS[k]) > 1e-9]
    return "_".join(bits) or "base"


CASES = [parse(x) for x in CASES_IN] or [parse("tag=base")]

# calibration BEFORE the master is opened (light_calibrate wipes the session)
AZ, EL, SRC = lb.solar_position("morning")
_calib = {}
for c in CASES:
    if any(abs(c[k] - DEFAULTS[k]) > 1e-9 for k in SKY_KEYS) and c["sky"] not in _calib:
        m = cal.measure_sky(AZ, EL, lb.SKY, samples=512)
        e = cal.measure_exposure(AZ, EL, m["lamp_energy"], m["sun_color_normalised"], lb.SKY,
                                 samples=256, sky_strength=c["sky"])
        _calib[c["sky"]] = (m["lamp_energy"], list(m["sun_color_normalised"]), e["exposure_ev"])
        print(f"[r13] calibrate sky {c['sky']:g}: lamp {m['lamp_energy']:.2f} W/m2 "
              f"exposure {e['exposure_ev']:.3f} EV", flush=True)

bpy.ops.wm.open_mainfile(filepath=MASTER, load_ui=False)
scene = bpy.context.scene
common.setup_scene(scene)
sun = bpy.data.objects.get("LIGHT_sun")
WORLD0 = scene.world
EXPOSURE0 = scene.view_settings.exposure
_DISK = bpy.data.objects.get(lb.FILL["name"])
_VAULT = sorted([o for o in bpy.data.objects if o.name.startswith(lb.VAULT_FILL["name"])], key=lambda o: o.name)
_E_DISK0 = float(_DISK.get("energy_W", _DISK.data.energy)) if _DISK else 0.0
_E_VAULT0 = float(_VAULT[0].get("energy_W", _VAULT[0].data.energy)) if _VAULT else 0.0
_SHADE_FILL0 = dict(lb.SHADE_FILL, lamps=[dict(l) for l in lb.SHADE_FILL["lamps"]])   # pristine copy (r11 fix 7)
_N_OBJ = len(scene.objects)
print(f"[r13] master {MASTER}: {_N_OBJ} objects, exposure {EXPOSURE0:.4f}, look {scene.view_settings.look!r}, "
      f"engine {scene.render.engine}, world {WORLD0.name!r}, sun {sun.data.energy:.2f} W/m2", flush=True)


def comp_group():
    """The COMP_golden_hour group node inside this scene's compositor tree (None if the tree is missing)."""
    st = getattr(scene, "compositing_node_group", None)
    if st is None:
        return None
    for n in st.nodes:
        if n.bl_idname == "CompositorNodeGroup" and n.node_tree and n.node_tree.name.startswith(lb.GROUP_NAME):
            return n
    return None


def apply_case(c):
    # --- world (only rebuilt if a sky key moved; otherwise the master's own world is used exactly as saved)
    if any(abs(c[k] - DEFAULTS[k]) > 1e-9 for k in SKY_KEYS):
        energy, colour, exp_ev = _calib[c["sky"]]
        w = cal.make_sky_world(f"R13_{case_tag(c)}", AZ, EL, lb.SKY, sun_disc=False, strength=c["sky"],
                               camera_boost=c["cb"], camera_saturation=c["csat"],
                               glossy_boost=c["gb"], glossy_saturation=c["gsat"],
                               diffuse_saturation=c["dsat"], diffuse_hue=c["dhue"],
                               diffuse_tint=(c["tr"], c["tg"], c["tb"]), diffuse_boost=c["db"],
                               diffuse_tint_antisun=c["ta"], diffuse_tint_horizon=c["th"])
        for k, v in (("sun_azimuth_deg", AZ), ("sun_elevation_deg", EL), ("sky_strength_lighting", c["sky"]),
                     ("sky_diffuse_boost", c["db"]), ("sky_diffuse_saturation", c["dsat"]),
                     ("sky_diffuse_hue", c["dhue"]), ("sky_diffuse_tint", [c["tr"], c["tg"], c["tb"]]),
                     ("sky_diffuse_tint_antisun", c["ta"]), ("sky_diffuse_tint_horizon", c["th"])):
            w[k] = v          # so light_probes.bake_world can rebuild the swept rig, not the shipped one
        for k, v in lb.SKY.items():
            w["sky_" + k] = v
        scene.world = w
        sun.data.energy = energy
        sun.data.color = (colour[0], colour[1], colour[2] * c["bm"])
        scene.view_settings.exposure = exp_ev + lb.EXPOSURE_BIAS + c["de"]
    else:
        scene.world = WORLD0
        scene.view_settings.exposure = EXPOSURE0 + c["de"]
    # --- mist (world) and the compositor's haze
    ms = scene.world.mist_settings
    ms.use_mist = True
    ms.start, ms.depth, ms.falloff = c["ms"], c["md"], lb.MIST["falloff"]
    g = comp_group()
    if g is not None:
        g.inputs["Haze Strength"].default_value = c["hz"]
        g.inputs["Haze Falloff"].default_value = c["hk"]
    scene.render.use_compositing = c["comp"] > 0.5
    # --- the anti-sun shade fill (rebuilt in memory every case from a pristine copy)
    lb.SUN_REFERENCE_W = sun.data.energy
    lb.SHADE_FILL = dict(_SHADE_FILL0) if c["fel"] < 0.0 else dict(
        _SHADE_FILL0, lamps=[dict(l, el=c["fel"]) for l in _SHADE_FILL0["lamps"]])
    if c["spec"] >= 0.0:
        lb.SHADE_FILL = dict(lb.SHADE_FILL, specular=c["spec"])
    if min(c["fcr"], c["fcg"], c["fcb"]) >= 0.0:
        lb.SHADE_FILL = dict(lb.SHADE_FILL, color=(c["fcr"], c["fcg"], c["fcb"]))
    lb.build_shade_fill(bpy.data.collections.get(lb.COLLECTION) or scene.collection, energy=c["fill"])
    # --- interior fills
    if _DISK:
        _DISK["energy_W"] = _E_DISK0 * c["f"]
        _DISK.data.energy = _E_DISK0 * c["f"]
    for o in _VAULT:
        o["energy_W"] = _E_VAULT0 * c["v"]
    # --- the Eevee irradiance bake (item 1). This is what carries the shade in Eevee, so it is a case key.
    if c["bake"] > 2.5:
        probes.free(scene)          # bake=3: no irradiance volumes at all, i.e. Eevee's world SH alone
        print("[r13] light-probe caches FREED: the frame is lit by the world SH and the lamps only", flush=True)
    elif c["bake"] > 0.5:
        lighting = c["bake"] < 1.5
        t = time.time()
        probes.bake(scene, lighting_world=lighting)
        print(f"[r13] re-baked with the {'LIGHTING (r13)' if lighting else 'SCENE/CAMERA (r12)'} world "
              f"in {time.time()-t:.0f}s", flush=True)
    print(f"[r13] case {case_tag(c)}: bake {c['bake']:g} comp {c['comp']:g} mist start {c['ms']:g} depth {c['md']:g} "
          f"haze cap {c['hz']:g} k {c['hk']:g} db {c['db']:g} tint {c['tr']:g},{c['tg']:g},{c['tb']:g} "
          f"ta {c['ta']:g} th {c['th']:g} f {c['f']:g} v {c['v']:g} "
          f"exposure {scene.view_settings.exposure:.3f} EV, world {scene.world.name!r}", flush=True)


def shoot(cam_id, tag):
    num, eng = cam_id[:2], cam_id[2:]
    scene.camera = bpy.data.objects.get(CAM_OBJ[num])
    res = HERO_RES if num == "01" else RES     # the hero is measured on QA's 1920x1080 grid in BOTH engines
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.color_depth = "8"
    scene.render.use_border = bool(BORDER)
    scene.render.use_crop_to_border = False
    if BORDER:
        x0, y0, x1, y1 = BORDER
        W, H = res
        scene.render.border_min_x, scene.render.border_max_x = x0 / 1920.0, x1 / 1920.0
        scene.render.border_min_y, scene.render.border_max_y = 1.0 - y1 / 1080.0, 1.0 - y0 / 1080.0
    if eng == "c":
        lp.apply_final_cycles(scene, samples=SAMPLES, time_limit=0.0)
    elif eng == "v":
        lp.apply_viewport_eevee(scene)
    else:
        lp.apply_preview_eevee(scene, samples=EEVEE_SAMPLES)
        e = scene.eevee
        if CASE["fgi"] > -1.5:
            e.use_fast_gi = CASE["fgi"] >= 0.0
            if CASE["fgi"] >= 0.0:
                e.fast_gi_distance = CASE["fgi"]
        if CASE["rt"] >= 0.0:
            e.use_raytracing = CASE["rt"] > 0.5
        if CASE["fgir"] >= 0.0:
            e.fast_gi_ray_count = int(CASE["fgir"])
        if CASE["thr"] >= 0.0:
            e.light_threshold = CASE["thr"]
        print(f"[r13] eevee: fast_gi {e.use_fast_gi} dist {getattr(e, 'fast_gi_distance', 0):.1f} rays "
              f"{e.fast_gi_ray_count} raytracing {e.use_raytracing} threshold {e.light_threshold}", flush=True)
    fp = OUT / f"{PREFIX}_{tag}_{num}{eng}.png"
    scene.render.filepath = str(fp)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[r13] -> {fp.name} ({time.time()-t:.1f}s, {res[0]}x{res[1]})", flush=True)


CASE = CASES[0]
for c in CASES:
    CASE = c
    apply_case(c)
    for cam in CAMS:
        shoot(cam, case_tag(c))
print("[r13] done", flush=True)
