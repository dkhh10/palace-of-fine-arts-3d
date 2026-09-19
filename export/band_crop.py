#!/usr/bin/env python3
"""Phase 8b step 4: the 100 % crop of one prototype's band frame beside its 2K octahedral frame.

    python3 export/band_crop.py [--proto ENV_tree_broadleaf_s53_LOD1]

No Blender, no GPU. The sheet is built 960 px wide ON PURPOSE, so the crops stay at 100 % (1 atlas texel
= 1 image pixel) in the copy the lead views: a 325 px band frame, the 162 px 2K octahedral frame at its
own size, and the same 2K frame nearest-upscaled x2 to the band's crown size for a like-for-like read.
Top row: colour through the delivery LUT (AgX High Contrast at -2.8331399 EV) over mid grey, straight
alpha. Bottom row: the alpha channel alone - the silhouette the viewer actually resolves.

Writes renders/qa_comparisons/p8b_band_<short>.jpg (960 px, committed) in the MAIN checkout.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import band_common as bc          # noqa: E402
import p8_atlas_probe as probe    # noqa: E402

MAIN = bc.MAIN_ROOT
LUT_EV = -2.8331398963928223
LUT_MIN_EV, LUT_SPAN_EV, LUT_PIVOT = -12.47393, 16.5, 0.18
BG = 96


def load_cube(path):
    size, rows = None, []
    for line in Path(path).read_text().splitlines():
        t = line.strip()
        if not t or t.startswith(("#", "TITLE", "DOMAIN")):
            continue
        if t.startswith("LUT_3D_SIZE"):
            size = int(t.split()[1])
            continue
        rows.append([float(x) for x in t.split()])
    a = np.array(rows, dtype=np.float64)
    assert size and a.shape == (size ** 3, 3), f"{path}: {a.shape} rows for size {size}"
    return a.reshape(size, size, size, 3).transpose(2, 1, 0, 3), size


def to_display(linear, cube, size):
    """(h, w, 3) scene-linear -> (h, w, 3) display 0-1, trilinear through the delivery .cube."""
    v = np.asarray(linear, dtype=np.float64) * (2.0 ** LUT_EV)
    x = np.clip((np.log2(np.maximum(v, 1e-10) / LUT_PIVOT) - LUT_MIN_EV) / LUT_SPAN_EV, 0.0, 1.0)
    g = x * (size - 1)
    i0 = np.floor(g).astype(int)
    i1 = np.minimum(i0 + 1, size - 1)
    f = g - i0
    out = np.zeros(x.shape[:-1] + (3,))
    for c0 in (0, 1):
        for c1 in (0, 1):
            for c2 in (0, 1):
                ix = (i1[..., 0] if c0 else i0[..., 0], i1[..., 1] if c1 else i0[..., 1],
                      i1[..., 2] if c2 else i0[..., 2])
                w = ((f[..., 0] if c0 else 1 - f[..., 0]) * (f[..., 1] if c1 else 1 - f[..., 1])
                     * (f[..., 2] if c2 else 1 - f[..., 2]))
                out += w[..., None] * cube[ix]
    return out


def panel(rgba_u8, rng, cube, size):
    """atlas texels (straight alpha, gamma-2 RGB) -> (colour over grey, alpha matte), both top-down."""
    t = rgba_u8[::-1].astype(np.float64) / 255.0          # bottom-up -> top-down for display
    lin = t[..., :3] ** 2 * rng
    disp = to_display(lin, cube, size)
    a = t[..., 3:4]
    col = np.clip(disp * 255.0 * a + BG * (1.0 - a), 0, 255).astype(np.uint8)
    mat = np.repeat(np.clip(a * 255.0, 0, 255).astype(np.uint8), 3, axis=-1)
    return col, mat


def up2(a):
    return np.repeat(np.repeat(a, 2, axis=0), 2, axis=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proto", default="ENV_tree_broadleaf_s53_LOD1")
    args = ap.parse_args()
    p = args.proto
    man = json.loads((MAIN / "export/out/gate3/manifest.json").read_text())
    rng = man["impostors"]["prototypes"][p]["range"]
    diag = json.loads((MAIN / "export/out/gate3/impostor_diag_atlas.json").read_text())["prototypes"][p]
    col, row = diag["1024"]["cam02_frame"]["col"], diag["1024"]["cam02_frame"]["row"]
    vd = np.array(diag["1024"]["cam02_frame"]["view_dir"], dtype=np.float64)
    vd /= np.linalg.norm(vd)
    i, j, az, el = bc.cell_of(tuple(vd))
    cube, size = load_cube(MAIN / "export/out/gate0/lut_agx_high_contrast_65.cube")

    import gate3_common as g3
    band = g3.read_png(bc.BAND_OUT / bc.png_name(p))                      # bottom-up
    y0, y1, x0, x1 = bc.inner_slice(i, j)
    bcol, bmat = panel(band[y0:y1, x0:x1], rng, cube, size)
    octa = g3.read_png(bc.OCTA_DIR / f"gate3_imp_{p}_albedo_2048.png")
    f, g, inner = 170, 4, 162
    oy, ox = row * f + g, col * f + g
    ocol, omat = panel(octa[oy:oy + inner, ox:ox + inner], rng, cube, size)

    W, H = 960, 800
    sheet = Image.new("RGB", (W, H), (28, 28, 30))
    d = ImageDraw.Draw(sheet)
    short = p.replace("ENV_tree_", "").replace("_LOD1", "")
    d.text((12, 8), f"Phase 8b band atlas vs the shipped 2K octahedral atlas - {short}, "
                    f"station-2 view dir {np.round(vd, 3).tolist()}", fill=(235, 235, 235))
    d.text((12, 24), f"ALL CROPS 100 % (1 atlas texel = 1 pixel). band cell (az {i}, el {j}) = "
                     f"{bc.ELEV_DEG[j]:.0f} deg at {i*30} deg, 325 px inner | octahedral 2K frame "
                     f"(col {col}, row {row}), 162 px inner", fill=(185, 185, 185))
    xs = [16, 380, 570]
    labels = [f"BAND 4096 - {bc.INNER_PX} px inner", "2K octahedral - 162 px inner",
              "2K octahedral, nearest x2 (same crown size)"]
    for yrow, (a, b) in enumerate(((bcol, ocol), (bmat, omat))):
        ytop = 56 + yrow * 370
        imgs = [a, b, up2(b)]
        for k, (x, im) in enumerate(zip(xs, imgs)):
            sheet.paste(Image.fromarray(im), (x, ytop))
            if yrow == 0:
                d.text((x, ytop + im.shape[0] + 4), labels[k], fill=(200, 200, 200))
        d.text((12, ytop - 14), "colour (delivery LUT, straight alpha over grey)" if yrow == 0
               else "alpha (coverage, as baked: no threshold, no dilate)", fill=(150, 200, 150))
    out = MAIN / "renders" / "qa_comparisons" / f"p8b_band_{short}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=92)
    print(f"[band] {out} {out.stat().st_size} B  band cell ({i},{j}) az {az:.1f} el {el:.1f} "
          f"vs octahedral frame ({col},{row})")


if __name__ == "__main__":
    main()
