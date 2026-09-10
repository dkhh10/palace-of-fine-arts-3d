"""Cut an ARCH r8 render into 100 % tiles for inspection (PIL only -- run with python3, not Blender).

    python3 scripts/arch_r8_tiles.py renders/previews/arch/r8_cam01.png 3 2

No downscaling: the r8 defect (a flat plate filling an arch) is invisible in a 960 px view, which is how it shipped
in v1. The 960 px downscale is only for the final composite sheet.
"""
import sys, os
from PIL import Image

src = sys.argv[1]
cols = int(sys.argv[2]) if len(sys.argv) > 2 else 3
rows = int(sys.argv[3]) if len(sys.argv) > 3 else 2
im = Image.open(src).convert("RGB")
W, H = im.size
tw, th = W // cols, H // rows
base = os.path.splitext(src)[0]
for r in range(rows):
    for c in range(cols):
        box = (c * tw, r * th, (c + 1) * tw if c < cols - 1 else W, (r + 1) * th if r < rows - 1 else H)
        out = f"{base}_tile{r}{c}.png"
        im.crop(box).save(out)
        print(f"{out}  {box}")
