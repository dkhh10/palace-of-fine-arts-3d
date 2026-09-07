#!/usr/bin/env python3
"""ORN relief legibility metric (python3 + numpy + PIL). Reads images only.

  python3 scripts/orn_relief_stats.py IMG x0 y0 x1 y1 [IMG2 x0 y0 x1 y1 ...]

Per box: mean luminance, std, relative std (std/mean) and the 5-95 percentile spread / mean.
QA-02-9's acceptance is the render panel's luminance std >= 60 % of ref 063's over the equivalent box; because the
two images are at different exposures the *relative* std (std / mean) is the exposure-invariant form of that test.
Add --save OUT.jpg to write the crops side by side (upscaled to 480 px wide each) for a visual check.
"""
import sys
import numpy as np
from PIL import Image

args = sys.argv[1:]
save = None
if "--save" in args:
    i = args.index("--save")
    save = args[i + 1]
    args = args[:i] + args[i + 2:]

crops = []
for i in range(0, len(args), 5):
    path = args[i]
    x0, y0, x1, y1 = (int(v) for v in args[i + 1:i + 5])
    im = Image.open(path).convert("RGB").crop((x0, y0, x1, y1))
    a = np.asarray(im).astype(np.float64)
    lum = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    m, s = lum.mean(), lum.std()
    p5, p95 = np.percentile(lum, 5), np.percentile(lum, 95)
    print(f"{path.split('/')[-1]:52s} box {x0},{y0},{x1},{y1}  {im.width}x{im.height}px  "
          f"mean {m:6.1f}  std {s:5.1f}  rel-std {s/m:6.3f}  p5-p95/mean {(p95-p5)/m:6.3f}")
    crops.append(im)

if save and crops:
    W = 480
    tiles = [c.resize((W, max(1, int(c.height * W / c.width))), Image.LANCZOS) for c in crops]
    H = max(t.height for t in tiles)
    canvas = Image.new("RGB", (W * len(tiles), H), (18, 18, 18))
    for i, t in enumerate(tiles):
        canvas.paste(t, (i * W, 0))
    canvas.save(save, quality=92)
    print("saved", save, canvas.size)
