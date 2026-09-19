"""Phase 8 Cycles station references — the parity baseline QA 23 measures against.

    blender --background --python scripts/p8_cycles_refs.py -- --blend <scratch.blend> --cam 01 --out <png>
                                                              [--samples 32]

One station per run (the lead's brief: one Blender at a time through scripts/blender_run.sh 1200).  Renders a
SCRATCH COPY of master_delivery.blend — never the file itself — in the delivery look exactly as the file carries
it, with the same Cycles settings `scripts/p8d_haze_check.py` used so the two sets are comparable:
`AgX` / `AgX - High Contrast` / -2.8331 EV, GPU, 1920x1080, fixed (adaptive OFF) samples, OpenImageDenoise.
The look is ASSERTED, not applied: if master_delivery ever stops carrying the frozen look, this aborts instead
of quietly rendering a reference in the wrong transform, which would make every QA-23 parity number wrong.
The compositor is left exactly as the file has it (the round-13 references are post-on frames too).
"""
import bpy, sys, os, time

LOOK = "AgX - High Contrast"
EXPOSURE = -2.8331


def main():
    a = sys.argv[sys.argv.index("--") + 1:]
    blend = a[a.index("--blend") + 1]
    cam = a[a.index("--cam") + 1]
    out = a[a.index("--out") + 1]
    samples = int(a[a.index("--samples") + 1]) if "--samples" in a else 32
    seed = int(a[a.index("--seed") + 1]) if "--seed" in a else None
    assert os.path.abspath(blend) != os.path.abspath(
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "master_delivery.blend")), \
        "render a scratch copy, never master_delivery.blend itself"
    bpy.ops.wm.open_mainfile(filepath=blend)
    scene = bpy.context.scene
    vs = scene.view_settings
    print(f"[p8refs] delivery look as found: view_transform={vs.view_transform!r} look={vs.look!r} "
          f"exposure={vs.exposure:.4f}  compositor={scene.use_nodes}")
    assert vs.view_transform == "AgX", vs.view_transform
    assert vs.look == LOOK, vs.look
    assert abs(vs.exposure - EXPOSURE) < 1e-3, vs.exposure
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import light_presets
    light_presets.apply_final_cycles(scene, samples=samples, time_limit=0)
    scene.cycles.use_adaptive_sampling = False       # fixed samples: every reference spends the same everywhere
    scene.cycles.samples = samples
    assert scene.cycles.device == "GPU" and scene.cycles.denoiser == "OPENIMAGEDENOISE"
    if seed is not None:
        # a second seed is the NOISE FLOOR control: the same scene, the same settings, a different sampling
        # sequence, so MAE(seed 0, seed 1) is what 32 spp + OIDN costs before any scene change is counted.
        scene.cycles.seed = seed
    cams = [o for o in bpy.data.objects if o.type == "CAMERA" and f"_qa_{cam}_" in o.name]
    assert len(cams) == 1, [o.name for o in bpy.data.objects if o.type == "CAMERA"]
    scene.camera = cams[0]
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = 100
    scene.render.filepath = out
    scene.render.image_settings.file_format = "PNG"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[p8refs] {cams[0].name} {samples} spp fixed -> {out} in {time.time() - t0:.1f}s")


main()
