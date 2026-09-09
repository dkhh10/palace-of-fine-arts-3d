"""What does AgX do to chroma at the sunlit attic's luminance?  (a 320x64 emission chart, 1 spp, ~5 s)

    blender -b --python scripts/mat_r9_agx.py

Round 9 measured that a -24 % change in the concrete's albedo BLUE moved the hero's sunlit attic box by only
-2.2 % of display blue, while the same albedo moved the SHADED attic box by -12.2 %.  Either the tint was not
reaching the surface or the view transform was eating it.  This settles it without another hero frame: a row of
emission patches whose scene-linear colour is scaled in blue by a known factor is rendered through the project's
own colour management (common.setup_scene -> AgX), and the display RGB of each patch is printed.  The ratio of
display-blue change to scene-blue change IS the transfer the albedo has to fight, as a function of level.
"""
import bpy, sys, os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

bpy.ops.wm.read_homefile(use_empty=True)
scene = common.setup_scene()
scene.render.engine = "CYCLES"
scene.cycles.samples = 1
scene.render.film_transparent = False

# scene-linear colours whose AgX image lands near the attic's operating point, x blue scale factors
BASE = [(1.30, 0.80, 0.30), (0.75, 0.46, 0.17), (0.42, 0.26, 0.10)]     # bright sunlit / mid / shade
BLUE = [1.00, 0.90, 0.80, 0.70, 0.60, 0.50]
NX, NY = len(BLUE), len(BASE)
scene.render.resolution_x, scene.render.resolution_y = NX * 32, NY * 32
scene.render.resolution_percentage = 100

cam_d = bpy.data.cameras.new("C"); cam_d.type = "ORTHO"; cam_d.ortho_scale = NX
cam = bpy.data.objects.new("C", cam_d); cam.location = (0, 0, 10)
scene.collection.objects.link(cam); scene.camera = cam

for j, base in enumerate(BASE):
    for i, k in enumerate(BLUE):
        bpy.ops.mesh.primitive_plane_add(size=1.0,
                                         location=(i - (NX - 1) / 2.0, (NY - 1) / 2.0 - j, 0))
        o = bpy.context.object
        m = bpy.data.materials.new(f"E{j}_{i}")
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs[0].default_value = (base[0], base[1], base[2] * k, 1.0)
        em.inputs[1].default_value = 1.0
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        o.data.materials.append(m)

scene.render.filepath = str(common.RENDERS / "previews" / "materials" / "r9_agx_chart.png")
scene.render.image_settings.color_depth = "8"
bpy.ops.render.render(write_still=True)

a = np.asarray(bpy.data.images.load(scene.render.filepath).pixels[:], dtype=np.float64)
W, H = scene.render.resolution_x, scene.render.resolution_y
a = a.reshape(H, W, 4)[::-1, :, :3] * 255.0     # Blender's buffer is bottom-up and already display-referred
print(f"[agx] view transform {scene.view_settings.view_transform} look {scene.view_settings.look} "
      f"exposure {scene.view_settings.exposure}")
lum = lambda c: 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
for j, base in enumerate(BASE):
    ref = None
    for i, k in enumerate(BLUE):
        c = a[j * 32 + 10:j * 32 + 22, i * 32 + 10:i * 32 + 22].reshape(-1, 3).mean(axis=0)
        mx, mn = c.max(), c.min()
        sat = (mx - mn) / mx if mx > 0 else 0.0
        if ref is None:
            ref = c.copy()
        db = (c[2] / ref[2] - 1.0) * 100.0 if ref[2] > 0 else 0.0
        ds = (k - 1.0) * 100.0
        print(f"[agx] scene {base[0]:.2f},{base[1]:.2f},{base[2] * k:.3f}  ->  display "
              f"{c[0]:6.1f},{c[1]:6.1f},{c[2]:6.1f}  lum {lum(c):6.1f}  sat {sat:.3f}  R-B {c[0] - c[2]:+6.1f}"
              f"   scene B {ds:+6.1f} % -> display B {db:+6.1f} %"
              f"   transfer {db / ds if ds else float('nan'):.3f}")
