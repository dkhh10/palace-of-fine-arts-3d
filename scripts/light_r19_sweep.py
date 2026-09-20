"""Round-19 sweep: one candidate DIFFUSE-sky rig, rendered from a scratch copy of master_delivery.blend.

WHY IT PATCHES THE WORLD INSTEAD OF REBUILDING THE MASTER.  A candidate here only ever changes arguments of
`light_calibrate.make_sky_world` -- the sockets `light_build.build_world` passes it and nothing else.  The world in
master_delivery is a LOCAL copy of that same generated node tree, so rebuilding it from the sockets the file itself
carries (`sky_*` custom properties, written by `build_world`) and re-assigning it reproduces exactly what a full
`light_build -> lead_build -> phase5_deliver` chain would put there, in ~2 minutes instead of ~50.  That claim is
not assumed: candidate `base` rebuilds the world from the file's OWN socket values and changes nothing, and its
frame must match the BEFORE reference to within the 32 spp + OIDN noise floor (`light_r19_measure --mae`).  If it
does not, the shortcut is invalid and the sweep is void.  The WINNER is then shipped in `light_build.py` and
re-measured through the real chain.

Everything else is `scripts/p8_cycles_refs.py`: the same scratch-copy assertion, the same asserted delivery look
(AgX / AgX - High Contrast / -2.8331 EV), the same `light_presets.apply_final_cycles`, adaptive OFF, GPU, OIDN.

    blender --background --python scripts/light_r19_sweep.py -- --blend <scratch.blend> --cam 02 \
        --out <png> --set tint_b=138 --set antisun_p=10 [--samples 32] [--seed 1] [--engine eevee]

`--set` keys (each maps to one make_sky_world argument):
    tint_r tint_g tint_b            SKY_DIFFUSE_TINT channels
    antisun antisun_p               SKY_DIFFUSE_TINT_ANTISUN / _P
    horizon horizon_p               SKY_DIFFUSE_TINT_HORIZON / _P
    sunside_r sunside_g sunside_b   SKY_DIFFUSE_TINT_SUNSIDE channels
    sunside_p                       SKY_DIFFUSE_TINT_SUNSIDE_P
    diffuse_boost diffuse_sat diffuse_hue
"""
import bpy, sys, os, time

LOOK = "AgX - High Contrast"
EXPOSURE = -2.8331

# socket key -> (world custom property that carries its current value, make_sky_world keyword, index or None)
KEYS = {
    "tint_r": ("sky_diffuse_tint", "diffuse_tint", 0),
    "tint_g": ("sky_diffuse_tint", "diffuse_tint", 1),
    "tint_b": ("sky_diffuse_tint", "diffuse_tint", 2),
    "sunside_r": ("sky_diffuse_tint_sunside", "diffuse_tint_sunside", 0),
    "sunside_g": ("sky_diffuse_tint_sunside", "diffuse_tint_sunside", 1),
    "sunside_b": ("sky_diffuse_tint_sunside", "diffuse_tint_sunside", 2),
    "antisun": ("sky_diffuse_tint_antisun", "diffuse_tint_antisun", None),
    "antisun_p": ("sky_diffuse_tint_antisun_p", "diffuse_tint_antisun_p", None),
    "horizon": ("sky_diffuse_tint_horizon", "diffuse_tint_horizon", None),
    "horizon_p": ("sky_diffuse_tint_horizon_p", "diffuse_tint_horizon_p", None),
    "sunside_p": ("sky_diffuse_tint_sunside_p", "diffuse_tint_sunside_p", None),
    "diffuse_boost": ("sky_diffuse_boost", "diffuse_boost", None),
    "diffuse_sat": ("sky_diffuse_saturation", "diffuse_saturation", None),
    "diffuse_hue": ("sky_diffuse_hue", "diffuse_hue", None),
}


def arg(a, name, default=None, cast=str):
    return cast(a[a.index(name) + 1]) if name in a else default


def rebuild_world(scene, overrides):
    """Rebuild scene.world from the sockets the file itself carries, with `overrides` applied."""
    import light_calibrate as cal
    old = scene.world
    p = {k: old[k] for k in old.keys()}
    need = ["sun_azimuth_deg", "sun_elevation_deg", "sky_strength_lighting", "sky_camera_boost",
            "sky_glossy_boost", "sky_diffuse_boost", "sky_camera_saturation", "sky_glossy_saturation",
            "sky_glossy_hue", "sky_diffuse_saturation", "sky_diffuse_hue", "sky_diffuse_tint",
            "sky_diffuse_tint_antisun", "sky_diffuse_tint_horizon", "sky_diffuse_tint_antisun_p",
            "sky_diffuse_tint_horizon_p", "sky_diffuse_tint_sunside", "sky_diffuse_tint_sunside_p"]
    missing = [k for k in need if k not in p]
    assert not missing, f"the delivery world does not carry {missing}; the sweep cannot reproduce it"
    sky = {k[4:]: p[k] for k in p if k.startswith("sky_") and k[4:] in
           ("sun_size_deg", "sun_intensity", "altitude", "air_density", "aerosol_density", "ozone_density")}
    kw = dict(
        strength=p["sky_strength_lighting"], camera_boost=p["sky_camera_boost"],
        glossy_boost=p["sky_glossy_boost"], diffuse_boost=p["sky_diffuse_boost"],
        camera_saturation=p["sky_camera_saturation"], glossy_saturation=p["sky_glossy_saturation"],
        glossy_hue=p["sky_glossy_hue"], diffuse_saturation=p["sky_diffuse_saturation"],
        diffuse_hue=p["sky_diffuse_hue"],
        diffuse_tint=list(p["sky_diffuse_tint"]),
        diffuse_tint_antisun=p["sky_diffuse_tint_antisun"],
        diffuse_tint_horizon=p["sky_diffuse_tint_horizon"],
        diffuse_tint_antisun_p=p["sky_diffuse_tint_antisun_p"],
        diffuse_tint_horizon_p=p["sky_diffuse_tint_horizon_p"],
        diffuse_tint_sunside=list(p["sky_diffuse_tint_sunside"]),
        diffuse_tint_sunside_p=p["sky_diffuse_tint_sunside_p"],
    )
    for k, v in overrides.items():
        prop, kwname, idx = KEYS[k]
        if idx is None:
            kw[kwname] = v
        else:
            kw[kwname][idx] = v
    print(f"[r19] sockets: tint={kw['diffuse_tint']} antisun_p={kw['diffuse_tint_antisun_p']} "
          f"horizon_p={kw['diffuse_tint_horizon_p']} sunside={kw['diffuse_tint_sunside']} "
          f"sunside_p={kw['diffuse_tint_sunside_p']} diffuse_boost={kw['diffuse_boost']}")
    new = cal.make_sky_world(old.name + "_r19", p["sun_azimuth_deg"], p["sun_elevation_deg"], sky,
                             sun_disc=False, **kw)
    ms_old, ms = old.mist_settings, new.mist_settings           # the compositor's haze reads the mist pass
    ms.use_mist, ms.start, ms.depth, ms.falloff = ms_old.use_mist, ms_old.start, ms_old.depth, ms_old.falloff
    for k in p:                                                  # keep the meta block, then correct what moved
        new[k] = p[k]
    new["sky_diffuse_tint"] = list(kw["diffuse_tint"])
    new["sky_diffuse_tint_sunside"] = list(kw["diffuse_tint_sunside"])
    for k in ("antisun", "horizon", "antisun_p", "horizon_p", "sunside_p"):
        new["sky_diffuse_tint_" + k] = kw["diffuse_tint_" + k]
    new["sky_diffuse_boost"] = kw["diffuse_boost"]
    new["r19_candidate"] = str(sorted(overrides.items()))
    scene.world = new
    return new


def main():
    a = sys.argv[sys.argv.index("--") + 1:]
    blend, cam, out = arg(a, "--blend"), arg(a, "--cam"), arg(a, "--out")
    samples = arg(a, "--samples", 32, int)
    seed = arg(a, "--seed", None, int)
    engine = arg(a, "--engine", "cycles")
    overrides = {}
    for i, t in enumerate(a):
        if t == "--set":
            k, v = a[i + 1].split("=", 1)
            assert k in KEYS, f"unknown socket {k!r}; known: {sorted(KEYS)}"
            overrides[k] = float(v)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert os.path.abspath(blend) != os.path.join(root, "master_delivery.blend"), \
        "render a scratch copy, never master_delivery.blend itself"
    bpy.ops.wm.open_mainfile(filepath=blend)
    scene = bpy.context.scene
    vs = scene.view_settings
    print(f"[r19] look as found: {vs.view_transform!r} / {vs.look!r} / {vs.exposure:.4f}  world={scene.world.name!r}")
    assert vs.view_transform == "AgX" and vs.look == LOOK and abs(vs.exposure - EXPOSURE) < 1e-3
    sys.path.insert(0, os.path.join(root, "scripts"))
    import light_presets
    rebuild_world(scene, overrides)
    if engine == "eevee":
        light_presets.apply_preview_eevee(scene)
        scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    else:
        light_presets.apply_final_cycles(scene, samples=samples, time_limit=0)
        scene.cycles.use_adaptive_sampling = False
        scene.cycles.samples = samples
        assert scene.cycles.device == "GPU" and scene.cycles.denoiser == "OPENIMAGEDENOISE"
        if seed is not None:
            scene.cycles.seed = seed
        scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    cams = [o for o in bpy.data.objects if o.type == "CAMERA" and f"_qa_{cam}_" in o.name]
    assert len(cams) == 1, [o.name for o in bpy.data.objects if o.type == "CAMERA"]
    scene.camera = cams[0]
    scene.render.resolution_percentage = 100
    scene.render.filepath = out
    scene.render.image_settings.file_format = "PNG"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[r19] {engine} {cams[0].name} {samples} spp -> {out} in {time.time() - t0:.1f}s")


main()
