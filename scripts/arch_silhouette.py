#!/usr/bin/env python3
"""ARCH helper: turn an alpha (film_transparent) render into a mask image that `qa_silhouette` reads reliably,
then measure / align it against a reference photo.

Why: `qa_silhouette.building_mask` calls a pixel "building" when r > b + 0.06. A pale, sky-lit dome fails that test
(measured r-b = 12/255 on the ARCH preview), so the tool reports an apex several metres below the real one. Rendering
`arch_inspect.py --alpha` (transparent film) and flattening the alpha here gives the true geometric silhouette; the
photographs are unaffected (their sunlit stone is strongly warm) so the comparison stays apples-to-apples.

    blender -b assets/architecture.blend --python scripts/arch_inspect.py -- --alpha ... --out x.png
    python3 scripts/arch_silhouette.py flatten x.png x_mask.png
    python3 scripts/arch_silhouette.py measure x_mask.png --crop x0 y0 x1 y1
    python3 scripts/arch_silhouette.py align x_mask.png --crop ... --ref photo.png --ref-crop ... --out sheet.png
"""
import sys, os, json, argparse
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa_silhouette as QS

BUILD = (230, 150, 90)      # warm: passes r > b + 0.06
SKY = (120, 150, 200)       # cool


def flatten(src, dst, thresh=0.5):
    im = Image.open(src).convert("RGBA")
    a = np.asarray(im).astype(np.float32) / 255.0
    m = a[..., 3] > thresh
    out = np.empty(a.shape[:2] + (3,), dtype=np.uint8)
    out[...] = SKY
    out[m] = BUILD
    Image.fromarray(out).save(dst)
    return dst


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["flatten", "measure", "align"])
    ap.add_argument("image")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--crop", type=int, nargs=4)
    ap.add_argument("--ref"); ap.add_argument("--ref-crop", type=int, nargs=4)
    ap.add_argument("--out-sheet", dest="sheet")
    a = ap.parse_args()
    if a.mode == "flatten":
        print(flatten(a.image, a.out))
    elif a.mode == "measure":
        img = QS.load(a.image)
        res, prof, crop = QS.measure(img, a.crop)
        print(json.dumps(res))
        if a.out:
            QS.draw_profile(a.image, img, prof, crop, res, a.out)
            print("wrote", a.out)
    else:
        QS.align(a.image, a.crop, a.ref, a.ref_crop, a.out or a.sheet)
