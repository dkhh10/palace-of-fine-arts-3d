"""What actually fills the backdrop bands? A first-hit ray cast, not an opinion (Phase 8d belt r2).

    blender --background --python scripts/env_belt_probe.py [-- --bands N,S,05]

Builds the env_preview scene (linked ENV + ARCH, the QA cameras) and casts one ray per sampled pixel of the
QA-22 backdrop boxes (docs/qa_round_22.md section 2 / scripts/qa_r22_probe.BACKDROP), reporting the first-hit
object for every ray that gets past the colonnade - i.e. exactly what a QA tile sees THROUGH the
intercolumniations. Prints a histogram by object class (hall wall, hall roof, belt tree, screen tree, city,
sky) per band and the fraction of through-rays that land on the hall.
"""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import env_preview
import qa_cameras
from mathutils import Vector

# band boxes in 1920x1080 frame px, from qa_r22_probe.BACKDROP
BANDS = {
    "N": (1, (0, 524, 640, 670)),
    "S": (1, (1280, 524, 1900, 670)),
    "05": (5, (0, 654, 1920, 786)),
}
STEP = 4        # sample every 4th pixel in x and y


def classify(name):
    if not name:
        return "sky"
    n = name
    if n.startswith("ENV_tree_"):
        return "tree"
    if n.startswith("ENV_shrub_") or n.startswith("ENV_reed"):
        return "shrub"
    if n.startswith("ENV_backdrop_hall_belt"):
        return "ICOSPHERE belt"          # the 8d R2 belt QA 22 rejected: only present in the before-state file
    if n.startswith("ENV_backdrop_hall_roof") or n.startswith("ENV_backdrop_hall_skylight"):
        return "hall roof"
    if n.startswith("ENV_backdrop_hall"):
        return "hall wall"
    if n.startswith("ENV_backdrop_") or n.startswith("ENV_city") or n.startswith("ENVBD"):
        return "city/backdrop"
    if n.startswith("ARCH_") or n.startswith("ORN_") or n.startswith("INST_"):
        return "palace"
    if n.startswith("ENV_terrain") or n.startswith("ENV_ground"):
        return "ground"
    return "other:" + n.split("_")[1] if "_" in n else "other"


def run(bands, env=None):
    if env:
        common.ASSET_FILES["ENV"] = common.Path(env)
        print(f"[belt_probe] ENV from {env}")
    # lod=1, not 0: `hide_viewport` is what the depsgraph honours, and the LOD0 tree objects are saved hidden in
    # the viewport (LOD1 is the viewport default) - a ray cast at lod=0 would pass straight through every tree.
    # At LOD1 the far trees (and the belt) carry their LOD2 crown envelope, so the coverage below is an UPPER
    # bound on the belt's real crown coverage and a lower bound on what still shows past it.
    scene = env_preview.build_scene(lod=1)
    qa_cameras.ensure(scene)
    dg = bpy.context.evaluated_depsgraph_get()
    belt_names = set()
    for ob in bpy.data.objects:
        if ob.name.startswith("ENV_tree_") and ob.get("note", "").startswith("HB"):
            belt_names.add(ob.name)
    print(f"[belt_probe] belt objects in scene: {len(belt_names)}")
    W, H = 1920, 1080
    for key in bands:
        st, (x0, y0, x1, y1) = BANDS[key]
        cam = next(o for o in bpy.data.objects if o.name.startswith(f"CAM_qa_{st:02d}"))
        mw = cam.matrix_world
        origin = mw.translation
        cd = cam.data
        f_px = cd.lens / cd.sensor_width * W
        # POSITIVE shift_y puts the horizon BELOW the frame centre (the architectural rise: the frame extends
        # upward, the content moves down), which is the viewer's own `ndc_y -= 2*shift_y*aspect`
        # (web/src/blenderCamera.js) and the reference sheet's "horizon at 68 % height with shift_y +0.17".
        # Getting this sign wrong aims the whole band at the lagoon - the first run of this probe did.
        cx = W / 2.0 + cd.shift_x * W
        cy = H / 2.0 + cd.shift_y * W
        hist = {}
        belt_hits = 0
        total = 0
        wall = []          # world hit points on the hall wall/roof: where the belt is still missing
        cmap = {"BELT tree": (40, 200, 60), "tree": (20, 110, 40), "shrub": (120, 180, 60),
                "hall wall": (255, 40, 40), "hall roof": (255, 150, 0), "ICOSPHERE belt": (255, 0, 255),
                "palace": (210, 200, 170), "other:capital": (180, 170, 150), "other:colonnade": (150, 140, 120),
                "sky": (120, 180, 255), "city/backdrop": (255, 255, 0), "ground": (90, 70, 50)}
        iw, ih = (x1 - x0) // STEP, (y1 - y0) // STEP
        buf = [0.0] * (iw * ih * 4)          # Blender's own image writer: bpy has no PIL
        for py in range(y0, y1, STEP):
            for px in range(x0, x1, STEP):
                d = Vector(((px + 0.5 - cx) / f_px, -(py + 0.5 - cy) / f_px, -1.0)).normalized()
                d = (mw.to_3x3() @ d).normalized()
                hit, loc, nor, idx, ob, mat = scene.ray_cast(dg, origin, d, distance=4000.0)
                name = ob.name if hit and ob else ""
                base = name.split(".")[0]
                c = classify(base)
                if base in belt_names:
                    c = "BELT tree"
                    belt_hits += 1
                hist[c] = hist.get(c, 0) + 1
                total += 1
                if c.startswith("hall"):
                    wall.append((px, loc.x, loc.y, loc.z))
                ix, iy = (px - x0) // STEP, (py - y0) // STEP
                if ix < iw and iy < ih:
                    r, g, bl = cmap.get(c, (255, 255, 255))
                    o = ((ih - 1 - iy) * iw + ix) * 4      # Blender images are bottom-up
                    buf[o:o + 4] = [(r / 255.0) ** 2.2, (g / 255.0) ** 2.2, (bl / 255.0) ** 2.2, 1.0]
        out = f"/tmp/belt_probe_class_{key}.png"
        bi = bpy.data.images.new(f"class_{key}", iw, ih, alpha=True)
        bi.pixels = buf
        bi.filepath_raw = out
        bi.file_format = "PNG"
        bi.save()
        print(f"\n[belt_probe] cam{st:02d} band {key} box {(x0, y0, x1, y1)}  {total} rays  class map -> {out}")
        blocked = sum(v for c, v in hist.items() if c in ("palace", "other:capital", "other:colonnade"))
        through = max(1, total - blocked)
        for c, v in sorted(hist.items(), key=lambda kv: -kv[1]):
            print(f"    {c:16s} {v:6d}  {100.0 * v / total:5.1f} % of band   {100.0 * v / through:5.1f} % of the "
                  f"{through} rays that get past the colonnade")
        if wall:
            cols = {}
            for (px, wx, wy, wz) in wall:
                cols[px // 80 * 80] = cols.get(px // 80 * 80, 0) + 1
            print("    hall hits by frame-x bin (80 px): "
                  + "  ".join(f"{k}-{k + 79}: {v}" for k, v in sorted(cols.items())))
            xs = sorted(w[1] for w in wall)
            ys = sorted(w[2] for w in wall)
            zs = sorted(w[3] for w in wall)
            q = lambda a: (a[0], a[len(a) // 2], a[-1])
            print("    hall hit world x (min/med/max) %.1f / %.1f / %.1f   y %.1f / %.1f / %.1f   "
                  "z %.1f / %.1f / %.1f" % (q(xs) + q(ys) + q(zs)))


if __name__ == "__main__":
    args = common.script_args()
    bands = ["N", "S", "05"]
    env = None
    for i, a in enumerate(args):
        if a == "--bands":
            bands = args[i + 1].split(",")
        elif a == "--env":
            env = args[i + 1]
    run(bands, env=env)
