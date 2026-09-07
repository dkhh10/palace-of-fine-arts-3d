"""QA-03-11 acceptance measurements on cam 06.

Two modes:

  python3 scripts/env_cam06_audit.py IMAGE [IMAGE ...]        image metrics only (no Blender)
  blender -b --python scripts/env_cam06_audit.py -- --cast    ray-cast the horizon crop in assets/environment.blend

QA-03-11's tests, on the 1280x720 aerial:
  * horizon crop (0, 0, 1280, 220): >= 30 building volumes with roof pitch and >= 3 colours; paths readable.
  * rotunda / far-shore contrast >= 1.5 : 1 (round 03 measured 1.04 : 1).

The image mode reports the luminance / hue spread of the crop and the contrast ratio; the ray-cast mode counts the
distinct backdrop objects the crop actually resolves, which is the honest answer to "how many building volumes".
"""
import sys, os, math

HORIZON = (0, 0, 1280, 220)
DOME = (534, 96, 782, 208)          # the rotunda dome in the 1280x720 aerial
FAR_SHORE = (0, 150, 1280, 220)     # ground past ~250 m, below the buildings


def image_metrics(paths):
    import numpy as np
    from PIL import Image
    import colorsys
    print(f"{'image':44s} {'crop lum':>9s} {'std':>6s} {'sat':>6s} {'hue':>6s} "
          f"{'dome lum':>9s} {'far lum':>8s} {'contrast':>9s}")
    for p in paths:
        im = Image.open(p).convert("RGB")
        if im.size != (1280, 720):
            im = im.resize((1280, 720))
        a = np.asarray(im).astype(np.float32)

        def box(b):
            x0, y0, x1, y1 = b
            return a[y0:y1, x0:x1].reshape(-1, 3)
        c = box(HORIZON)
        lum = 0.2126 * c[:, 0] + 0.7152 * c[:, 1] + 0.0722 * c[:, 2]
        m = c.mean(0)
        h, s, _ = colorsys.rgb_to_hsv(*(m / 255.0))
        d = box(DOME)
        dl = float((0.2126 * d[:, 0] + 0.7152 * d[:, 1] + 0.0722 * d[:, 2]).mean())
        f = box(FAR_SHORE)
        fl = float((0.2126 * f[:, 0] + 0.7152 * f[:, 1] + 0.0722 * f[:, 2]).mean())
        print(f"{os.path.basename(str(p)):44s} {lum.mean():9.1f} {lum.std():6.1f} {s:6.3f} {h * 360:6.1f} "
              f"{dl:9.1f} {fl:8.1f} {dl / max(1e-6, fl):8.2f}:1")


def ray_cast():
    import bpy
    from mathutils import Vector
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import common
    bpy.ops.wm.open_mainfile(filepath=str(common.ASSET_FILES["ENV"]))
    scene = bpy.context.scene
    import qa_cameras
    spec = next(c for c in qa_cameras.CAMERAS if "_qa_06_" in c["name"])
    loc = Vector(spec["loc"])
    f = (Vector(spec["target"]) - loc).normalized()
    r = f.cross(Vector((0, 0, 1))).normalized()
    u = r.cross(f).normalized()
    hw = 0.5 * 36.0 / spec["lens"]
    hh = hw * 9.0 / 16.0
    dg = bpy.context.evaluated_depsgraph_get()
    x0, y0, x1, y1 = HORIZON
    W, H = 1280, 720
    walls, roofs, mats, ground_mats, canopy = set(), set(), set(), {}, 0
    hits = 0
    step = 3
    for py in range(y0, y1, step):
        for px in range(x0, x1, step):
            sx = ((px + 0.5) / W - 0.5) * 2
            sy = (0.5 - (py + 0.5) / H) * 2
            d = (f + r * hw * sx + u * hh * sy).normalized()
            ok, hit, nrm, idx, obj, _ = scene.ray_cast(dg, loc, d, distance=6000)
            if not ok:
                continue
            hits += 1
            n = obj.name
            mat = ""
            if obj.type == "MESH" and obj.data.materials:
                mi = obj.data.polygons[idx].material_index if idx < len(obj.data.polygons) else 0
                m = obj.data.materials[min(mi, len(obj.data.materials) - 1)]
                mat = m.name if m else ""
            mats.add(mat)
            if "roof" in n or "roof" in mat:
                roofs.add(n)
            elif "house" in n or "fill_" in n or "presidio_" in n or "backdrop_hall" in n:
                walls.add(n)
            elif "canopy" in n or "forest" in n or "ridge" in n:
                canopy += 1
            elif "ground" in n or "terrain" in n:
                ground_mats[mat] = ground_mats.get(mat, 0) + 1
    print(f"\n[cam06 audit] horizon crop {HORIZON}, {step}px grid, {hits} hits")
    print(f"  building volumes resolved : {len(walls | roofs)}  (wall objects {len(walls)}, roof objects {len(roofs)})")
    print(f"  with a pitched roof       : {len(roofs)}")
    print(f"  distinct materials in crop: {len(mats)}")
    print(f"  canopy samples            : {canopy}")
    print(f"  ground materials          : {ground_mats}")


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    if "--cast" in argv:
        ray_cast()
    else:
        image_metrics(argv)
