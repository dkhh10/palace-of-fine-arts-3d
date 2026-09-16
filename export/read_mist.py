"""Gate 3 hand-off 3: read the scene's MIST settings out of master_delivery.blend.

    scripts/blender_run.sh 600 -- --background <master_delivery.blend> --python export/read_mist.py

Read-only: no render, no save. The manifest's `compositor` block records the COMP_golden_hour group's `Mist`
input as 0.0 because a group input's stored default is what a disconnected socket reports - the real value is
the Mist PASS the Render Layers node feeds it, and that pass is shaped entirely by
`scene.world.mist_settings` (start, depth, falloff, height, intensity). Without those three numbers the
viewer cannot reproduce the haze ramp: a fog that starts at the wrong distance is a different picture.
Writes export/out/gate3/mist_settings.json; export/manifest_v4.py copies it into `compositor.mist`.
"""
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate3_common as g3  # noqa: E402

scene = bpy.context.scene
world = scene.world
ms = world.mist_settings if world else None
vl = scene.view_layers[0] if len(scene.view_layers) else None

out = dict(
    schema="pfa-phase6/gate3-mist/1", written_by="export/read_mist.py",
    source=bpy.data.filepath, scene=scene.name, world=(world.name if world else None),
    view_layer=(vl.name if vl else None),
    # `use_pass_mist` is what decides whether the compositor's Mist socket carries anything at all.
    use_pass_mist=(bool(vl.use_pass_mist) if vl else None),
    unit_scale=scene.unit_settings.scale_length,
    mist=(dict(use_mist=bool(ms.use_mist), start=float(ms.start), depth=float(ms.depth),
               falloff=str(ms.falloff), height=float(ms.height), intensity=float(ms.intensity))
          if ms else None),
    note=("Blender's mist pass: t = clamp((dist - start) / depth, 0, 1) shaped by `falloff` "
          "(QUADRATIC t^2, LINEAR t, INVERSE_QUADRATIC sqrt(t)), then mist = intensity + (1 - intensity) * t, "
          "measured along the view ray from the camera in metres (1 BU = 1 m here). `height` > 0 fades the "
          "mist out above z = height in WORLD space (Blender +Z; the viewer's +Y after the glTF swap). "
          "The compositor group's own `Mist` input reads 0.0 because that is a disconnected socket's stored "
          "default - the live value is this pass."),
)
p = g3.OUT / "mist_settings.json"
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(out, indent=1) + "\n")
print("[read_mist] " + json.dumps(out["mist"]) + f" use_pass_mist={out['use_pass_mist']}")
print(f"[read_mist] wrote {p}")
