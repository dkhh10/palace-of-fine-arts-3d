"""Temporary helper: average colours of pixel rectangles in reference photos.

Run with Blender:
  /Applications/Blender.app/Contents/MacOS/Blender -b --python scripts/tmp_sample_colors.py -- rects.json
where rects.json is a JSON list of [file, x, y, w, h, label] (x,y = top-left
corner in normal image coordinates, y downwards, like ffmpeg crop=W:H:X:Y).
Without an argument the RECTS list below is used.

Prints per rectangle: sRGB 0-255 mean, linear 0-1 mean, sRGB std-dev, and
HSV-ish saturation (max-min)/max of the sRGB mean so saturation can be compared
between photos. Images are loaded once and cached.
"""
import sys, json, os
import bpy
import numpy as np

RECTS = [
    # (file, x, y, w, h, label)
]

def srgb_to_linear(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

_cache = {}
def load(path):
    path = os.path.abspath(path)
    if path in _cache:
        return _cache[path]
    img = bpy.data.images.load(path, check_existing=True)
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    arr = buf.reshape(h, w, 4)[::-1, :, :3]   # flip to top-down rows, drop alpha
    _cache[path] = arr
    return arr

def sample(path, x, y, w, h):
    arr = load(path)
    H, W = arr.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    patch = arr[y0:y1, x0:x1].reshape(-1, 3).astype(np.float64)
    mean = patch.mean(axis=0)
    std = patch.std(axis=0)
    return mean, std, (x1 - x0) * (y1 - y0)

def main():
    rects = RECTS
    if '--' in sys.argv:
        args = sys.argv[sys.argv.index('--') + 1:]
        if args:
            with open(args[0]) as f:
                rects = json.load(f)
    print("label | file | rect(x,y,w,h) | sRGB mean 0-255 | linear 0-1 | sRGB std | sat")
    for file, x, y, w, h, label in rects:
        mean, std, n = sample(file, x, y, w, h)
        s255 = mean * 255
        lin = srgb_to_linear(mean)
        sat = (s255.max() - s255.min()) / max(s255.max(), 1e-6)
        print(f"{label:28s} | {os.path.basename(file)[:24]:24s} | ({x},{y},{w},{h}) | "
              f"{s255[0]:6.1f} {s255[1]:6.1f} {s255[2]:6.1f} | "
              f"{lin[0]:.3f} {lin[1]:.3f} {lin[2]:.3f} | "
              f"{std[0]*255:4.1f} {std[1]*255:4.1f} {std[2]*255:4.1f} | {sat:.2f}")

if __name__ == '__main__':
    main()
