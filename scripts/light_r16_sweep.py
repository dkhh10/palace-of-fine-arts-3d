"""Round-16 sweep (a copy of the round-15 sweep with the round-16 keys; the r15 script is left as the record of
round 15). Round-15 header follows.

New keys:
  * `tsr` / `tsg` / `tsb` / `tsp` -- SKY_DIFFUSE_TINT_SUNSIDE and its exponent (QA-08-3). The MIRROR of the
    round-12 diffuse tint: a multiply on the sky that lands on SUN-FACING surfaces only, weighted by
    (0.5 - 0.5 * Incoming.sun)^tsp. The sunlit stone's blue is entirely sky (SUN_BLUE_MULT has been 0.00 since
    round 12), so this is the only socket that can take blue off the sunlit attic without touching the shaded one.
  * `faz` -- the AZIMUTH of the SHADE_FILL lamps (QA-08-2). cam02's piers face straight down the NNE lamp's axis
    at az 25 and read hue 263; the hero's shaded attic sees the same lamp obliquely. Rotating the lamp is the only
    geometric discriminator between the two faces that does not need light linking.

Round-15 header:

Round-15 sweep (a copy of the round-14 sweep with the round-15 keys; the r14 script is left as the record of
round 14). Round-14 header follows.

New keys:
  * `ghue` -- SKY_GLOSSY_HUE (QA-07-1). Blender Hue/Saturation Hue on the GLOSSY stage of the world only, 0.5 = no
    shift, one unit = a full turn. It rotates the sky the LAGOON MIRRORS without touching the visible sky (camera
    rays) or the light on shaded stone (diffuse rays). QA-07-1 is a hue defect (near water 227.9 vs ref 190.0) and
    this socket had no hue lever before.
  * `wwnw` / `wssw` / `wnne` -- the per-lamp weights of SHADE_FILL["lamps"] (WNW / SSW / NNE). Round 14's `cfill`
    scales all three together, but QA-07-7 wants the hero's shade DOWN (WNW) and QA-07-5 wants the south colonnade
    UP (SSW) in the same round, which one knob cannot do.

Round-14 header:

Round-14 sweep (a copy of the round-13 sweep with the round-14 keys; the r13 script is left as the record
of round 13).

  * `tap` / `thp` -- the EXPONENTS on the anti-sun and horizon weights of the diffuse tint (QA-06-2).
  * `sres` / `sray` / `srstep` / `nfill` -- Eevee shadow pool / shadow ray count / shadow step count / how many of
    the three EEVEE-only shade lamps are kept (QA-06-13, the six-camera pass time).
  * `bake` -- which world the Eevee irradiance volumes are baked with. 1 = the lighting world, 2 = the scene world
    (round-12 behaviour), 0 = do not re-bake, 3 = free the caches.
  * `ms` / `md` -- MIST start / depth.   `hz` / `hk` -- the compositor's haze cap and extinction.

    scripts/blender_run.sh 1200 -- --background --python scripts/light_r16_sweep.py -- --cams 01e 01c
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
PREFIX = arg("--prefix", ["r16"], n=1)[0]
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
                fill=lb.SHADE_FILL.get('energy_eevee', 0.0), fel=-1.0, spec=-1.0, fcr=-1.0, fcg=-1.0, fcb=-1.0,
                # EEVEE-ONLY preset overrides, applied AFTER light_presets.apply_preview_eevee. `fgi` is
                # fast_gi_distance in metres (-1 = fast GI off), `rt` raytracing on/off, `fgir` the fast-GI ray
                # count, `thr` light_threshold. Eevee's horizon scan is what decides how much of the world SH an
                # occluded surface is allowed to see, so it -- not the world -- is the shaded stone's real knob.
                fgi=-2.0, rt=-1.0, fgir=-1.0, thr=-1.0,
                # ROUND 14
                tap=lb.SKY_DIFFUSE_TINT_ANTISUN_P, thp=lb.SKY_DIFFUSE_TINT_HORIZON_P,
                ghue=lb.SKY_GLOSSY_HUE,           # ROUND 15 (QA-07-1): hue of the sky the lagoon mirrors
                # ROUND 16 (QA-08-3): the sun-side diffuse tint and its exponent
                tsr=lb.SKY_DIFFUSE_TINT_SUNSIDE[0], tsg=lb.SKY_DIFFUSE_TINT_SUNSIDE[1],
                tsb=lb.SKY_DIFFUSE_TINT_SUNSIDE[2], tsp=lb.SKY_DIFFUSE_TINT_SUNSIDE_P,
                faz=-1.0,                         # ROUND 16 (QA-08-2): SHADE_FILL lamp azimuth (-1 = keep)
                wwnw=-1.0, wssw=-1.0, wnne=-1.0,  # ROUND 15: per-lamp SHADE_FILL weights (-1 = keep)
                sres=-1.0, sray=-1.0, srstep=-1.0, nfill=-1.0,
                sfres=-1.0, sfjit=-1.0,
                cfill=-1.0)   # ROUND 14: the CYCLES energy of LIGHT_shade_fill (`fill` is the Eevee one)      # the shade lamps' own shadow resolution / jitter
SKY_KEYS = ("sky", "cb", "gb", "db", "csat", "gsat", "dsat", "dhue", "ghue", "tr", "tg", "tb", "ta", "th",
            "tap", "thp", "bm", "de", "tsr", "tsg", "tsb", "tsp")


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
        print(f"[r16] calibrate sky {c['sky']:g}: lamp {m['lamp_energy']:.2f} W/m2 "
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
print(f"[r16] master {MASTER}: {_N_OBJ} objects, exposure {EXPOSURE0:.4f}, look {scene.view_settings.look!r}, "
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
        old_w = bpy.data.worlds.get(f"R15_{case_tag(c)}")
        if old_w:
            bpy.data.worlds.remove(old_w)          # r12 review carry 9: do not leak one world per case
        w = cal.make_sky_world(f"R15_{case_tag(c)}", AZ, EL, lb.SKY, sun_disc=False, strength=c["sky"],
                               camera_boost=c["cb"], camera_saturation=c["csat"],
                               glossy_boost=c["gb"], glossy_saturation=c["gsat"], glossy_hue=c["ghue"],  # r15 review fix 1
                               diffuse_saturation=c["dsat"], diffuse_hue=c["dhue"],
                               diffuse_tint=(c["tr"], c["tg"], c["tb"]), diffuse_boost=c["db"],
                               diffuse_tint_antisun=c["ta"], diffuse_tint_horizon=c["th"],
                               diffuse_tint_antisun_p=c["tap"], diffuse_tint_horizon_p=c["thp"],
                               diffuse_tint_sunside=(c["tsr"], c["tsg"], c["tsb"]),
                               diffuse_tint_sunside_p=c["tsp"])
        for k, v in (("sun_azimuth_deg", AZ), ("sun_elevation_deg", EL), ("sky_strength_lighting", c["sky"]),
                     ("sky_diffuse_boost", c["db"]), ("sky_diffuse_saturation", c["dsat"]),
                     ("sky_diffuse_hue", c["dhue"]), ("sky_diffuse_tint", [c["tr"], c["tg"], c["tb"]]),
                     ("sky_diffuse_tint_antisun", c["ta"]), ("sky_diffuse_tint_horizon", c["th"]),
                     ("sky_diffuse_tint_antisun_p", c["tap"]), ("sky_diffuse_tint_horizon_p", c["thp"]),
                     ("sky_glossy_boost", c["gb"]), ("sky_glossy_saturation", c["gsat"]),
                     ("sky_glossy_hue", c["ghue"]),
                     ("sky_diffuse_tint_sunside", [c["tsr"], c["tsg"], c["tsb"]]),
                     ("sky_diffuse_tint_sunside_p", c["tsp"])):
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
    # r13 review carry 2: `energy=` sets the CYCLES energy only, and apply_preview_eevee then overwrites data.energy
    # from `energy_W_eevee` -- so the `fill=` key was dead in Eevee and fill=0 still rendered the full 55 W/m2.
    # `fill` is therefore the EEVEE energy and `cfill` the CYCLES one. (r15 review carry 4: the sentence that used
    # to stand here, "the Cycles energy stays at the shipped 0.0", has been false since round 14 -- SHADE_FILL's
    # Cycles energy is 49.0 W/m2 as shipped, and `cfill` < 0 means "keep it", not "zero it".)
    if c["sfres"] >= 0.0:
        lb.SHADE_FILL = dict(lb.SHADE_FILL, shadow_res=c["sfres"])
    if c["sfjit"] >= 0.0:
        lb.SHADE_FILL = dict(lb.SHADE_FILL, shadow_jitter=c["sfjit"] > 0.5)
    if max(c["wwnw"], c["wssw"], c["wnne"]) >= 0.0:      # ROUND 15 (QA-07-5 / QA-07-7)
        # r15 review fix 3: keyed by the lamp's azimuth, not by list position (the shipped list has one lamp)
        _w = {"wnw": c["wwnw"], "ssw": c["wssw"], "nne": c["wnne"]}
        def _key(l):
            az = l.get("az", l.get("azimuth", -1))
            return "nne" if 0 <= az < 90 else "ssw" if 180 <= az < 270 else "wnw" if 270 <= az < 360 else None
        lb.SHADE_FILL = dict(lb.SHADE_FILL, lamps=[
            dict(l, w=(l["w"] if _key(l) is None or _w[_key(l)] < 0.0 else _w[_key(l)]))
            for l in lb.SHADE_FILL["lamps"]])
    if c["faz"] >= 0.0:                              # ROUND 16 (QA-08-2): rotate the whole fill rig
        lb.SHADE_FILL = dict(lb.SHADE_FILL, lamps=[dict(l, az=c["faz"]) for l in lb.SHADE_FILL["lamps"]])
    if c["nfill"] >= 0.0:                            # ROUND 14 (QA-06-13): keep only the first n shade lamps
        lb.SHADE_FILL = dict(lb.SHADE_FILL, lamps=lb.SHADE_FILL["lamps"][:int(c["nfill"])])
    lb.build_shade_fill(bpy.data.collections.get(lb.COLLECTION) or scene.collection,
                        energy=(lb.SHADE_FILL.get("energy", 0.0) if c["cfill"] < 0.0 else c["cfill"]),
                        energy_eevee=c["fill"])
    # --- interior fills
    if _DISK:
        _DISK["energy_W"] = _E_DISK0 * c["f"]
        _DISK.data.energy = _E_DISK0 * c["f"]
    for o in _VAULT:
        o["energy_W"] = _E_VAULT0 * c["v"]
    # --- the Eevee irradiance bake (item 1). This is what carries the shade in Eevee, so it is a case key.
    if c["bake"] > 2.5:
        probes.free(scene)          # bake=3: no irradiance volumes at all, i.e. Eevee's world SH alone
        print("[r16] light-probe caches FREED: the frame is lit by the world SH and the lamps only", flush=True)
    elif c["bake"] > 0.5:
        lighting = c["bake"] < 1.5
        t = time.time()
        probes.bake(scene, lighting_world=lighting)
        print(f"[r16] re-baked with the {'LIGHTING (r13)' if lighting else 'SCENE/CAMERA (r12)'} world "
              f"in {time.time()-t:.0f}s", flush=True)
    # r14 review carry 1: print what the WORLD actually carries, not the case keys. A case that moves no sky key
    # reuses the master's own saved world, whose exponents / boosts are NOT the sweep defaults, and the old header
    # read as if they were.
    W = scene.world
    def wp(k, d):
        try:
            return float(W[k])
        except Exception:
            return float(d)
    wt = W.get("sky_diffuse_tint", [c["tr"], c["tg"], c["tb"]])
    lamps = ",".join(f"az{l['az']:g}@{l['w']:g}" for l in lb.SHADE_FILL["lamps"])
    wts = W.get("sky_diffuse_tint_sunside", [c["tsr"], c["tsg"], c["tsb"]])
    print(f"[r16] case {case_tag(c)}: bake {c['bake']:g} comp {c['comp']:g} mist start {c['ms']:g} depth {c['md']:g} "
          f"haze cap {c['hz']:g} k {c['hk']:g} | WORLD {W.name!r} db {wp('sky_diffuse_boost', c['db']):g} "
          f"gb {wp('sky_glossy_boost', c['gb']):g} gsat {wp('sky_glossy_saturation', c['gsat']):g} "
          f"ghue {wp('sky_glossy_hue', c['ghue']):.4f} "
          f"tint {','.join(f'{float(v):g}' for v in wt)} "
          f"ta {wp('sky_diffuse_tint_antisun', c['ta']):g}^{wp('sky_diffuse_tint_antisun_p', c['tap']):g} "
          f"th {wp('sky_diffuse_tint_horizon', c['th']):g}^{wp('sky_diffuse_tint_horizon_p', c['thp']):g} "
          f"sunside {','.join(f'{float(v):g}' for v in wts)}^{wp('sky_diffuse_tint_sunside_p', c['tsp']):g} | "
          f"shade cycles {(lb.SHADE_FILL.get('energy', 0.0) if c['cfill'] < 0.0 else c['cfill']):g} "
          f"eevee {c['fill']:g} W/m2 w [{lamps}] | f {c['f']:g} v {c['v']:g} "
          f"exposure {scene.view_settings.exposure:.3f} EV", flush=True)


def shoot(cam_id, tag):
    num, eng = cam_id[:2], cam_id[2:]
    scene.camera = bpy.data.objects.get(CAM_OBJ[num])
    res = HERO_RES if num == "01" else RES     # the hero is measured on QA's 1920x1080 grid in BOTH engines
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.color_depth = "8"
    # ROUND 15: the border is stated in HERO pixels, so it may only be applied to the hero. Applying the same
    # fractions to a 1280x720 camera would crop cam02 / 03 / 05 / 06 to an unrelated rectangle (r14 applied it to
    # every camera, which is only safe because r14 never mixed a bordered hero with the other cameras in one run).
    use_border = bool(BORDER) and num == "01"
    scene.render.use_border = use_border
    scene.render.use_crop_to_border = False
    if use_border:
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
        if CASE["sres"] >= 0.0:                      # ROUND 14 (QA-06-13)
            e.shadow_pool_size = str(int(CASE["sres"]))
        if CASE["sray"] >= 0.0:
            e.shadow_ray_count = int(CASE["sray"])
        if CASE["srstep"] >= 0.0:
            e.shadow_step_count = int(CASE["srstep"])
        print(f"[r16] eevee: fast_gi {e.use_fast_gi} dist {getattr(e, 'fast_gi_distance', 0):.1f} rays "
              f"{e.fast_gi_ray_count} raytracing {e.use_raytracing} threshold {e.light_threshold}", flush=True)
    fp = OUT / f"{PREFIX}_{tag}_{num}{eng}.png"
    scene.render.filepath = str(fp)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    dt = time.time() - t
    TIMES.append((cam_id, dt))
    print(f"[r16] -> {fp.name} ({dt:.1f}s, {res[0]}x{res[1]})", flush=True)


TIMES = []
CASE = CASES[0]
for c in CASES:
    CASE = c
    apply_case(c)
    for cam in CAMS:
        shoot(cam, case_tag(c))
print(f"[r16] camera times: " + "  ".join(f"{k} {v:.1f}s" for k, v in TIMES) +
      f"   TOTAL {sum(v for _, v in TIMES):.1f}s over {len(TIMES)} frames", flush=True)
print("[r16] done", flush=True)
