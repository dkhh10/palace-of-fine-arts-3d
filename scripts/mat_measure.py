"""Measure mean colour of rectangles in a render (sRGB 0-255 and linear), for albedo checks.
    blender -b --python scripts/mat_measure.py -- image.png x,y,w,h [x,y,w,h ...]   (pixel coords, origin top-left)
"""
import bpy, sys
argv = sys.argv[sys.argv.index("--") + 1:]
img = bpy.data.images.load(argv[0])
img.colorspace_settings.name = "Non-Color"
W, H = img.size
px = img.pixels[:]
def lin(u):
    return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4
for rect in argv[1:]:
    x, y, w, h = [int(v) for v in rect.split(",")]
    acc = [0.0, 0.0, 0.0]; n = 0
    for yy in range(y, y + h):
        row = H - 1 - yy
        for xx in range(x, x + w):
            i = (row * W + xx) * 4
            acc[0] += px[i]; acc[1] += px[i + 1]; acc[2] += px[i + 2]; n += 1
    s = [a / n for a in acc]
    l = [lin(v) for v in s]
    Y = 0.2126 * l[0] + 0.7152 * l[1] + 0.0722 * l[2]
    print(f"rect {rect}: sRGB {[round(v * 255) for v in s]}  linear {[round(v, 3) for v in l]}  Y {Y:.3f}  ratios 1:{l[1]/max(l[0],1e-6):.2f}:{l[2]/max(l[0],1e-6):.2f}")
