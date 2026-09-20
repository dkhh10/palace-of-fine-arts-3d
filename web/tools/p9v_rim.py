#!/usr/bin/env python3
"""Phase 9 item 1 — the dotted rim on the far-crown silhouettes (QA 21 item 1), proved WITHOUT a GPU.

    python3 web/tools/p9v_rim.py            # the whole argument, all three parts
    python3 web/tools/p9v_rim.py capture    # part 1 only (the delivered frames)

Three parts, in the order the argument runs:

1. THE CAPTURE.  Measure the rim on the delivered gate12 frames: a `checkerboard index` = the
   projection of the high-pass residual on the ( x + y ) parity sign, over the rim pixels only,
   normalised by that residual's rms.  0 = no screen-space checkerboard, 1 = a pure one.  The two
   stations QA 21 names against a control crown that has a BUILDING behind it, not sky.

2. THE SHADER, RE-IMPLEMENTED OVER THE REAL ATLAS TEXELS (export/out/gate3/band/*.png, the same
   4096x1024 band atlas the viewer draws): the premultiplied 8-tap reconstruction, fwidth on the
   2x2 quad, the Phase 7 ramp, the Phase 8b magnification ramp and share - line for line as
   web/src/impostors.js.  Its output `pfaCov` is a smooth field: its checkerboard index is ~0 at
   BOTH the minified (station 5) and the magnified (station 2) regime.  So nothing the shader
   computes carries a period-2 term, and the ordered 4x4 Bayer fallback is not even compiled when a
   coverage mask is written (the gate12 boot note says `resolved by the 4-sample coverage mask`).

3. THE ONLY STAGE LEFT is the hardware's alpha-to-coverage mask.  GL ES 3.0 s15.1.3 lets the mask
   `be a function of the pixel location`, i.e. dither.  Push the same smooth pfaCov through three
   models of it - no dither, a 2x2 dither, and a 1/8-step dither - and compare the checkerboard
   index with part 1's measurement.  Then push it through the FIX (quantise pfaCov to the target's
   own sample ladder before the mask sees it) under the same dither models.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
CAPS = MAIN / "renders/web"
BAND = MAIN / "export/out/gate3/band"
ALPHA_TEST = 0.33
INNER_PX = 325.0
SHARE = 0.10
MAG_LO, MAG_HI, RAMP = 1.0, 2.0, 1.0

# QA 21 §2b's two boxes, plus a control crown with a building behind it instead of sky.
BOXES = [("05 left crown  (sky behind, QA 21)", 5, (0, 480, 200, 640)),
         ("02 right cypress (sky behind, QA 21)", 2, (1700, 370, 1900, 660)),
         ("01 hero crown  (building behind, control)", 1, (760, 545, 1000, 690))]


def lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def highpass(L):
    return L - 0.25 * (np.roll(L, 1, 1) + np.roll(L, -1, 1) + np.roll(L, 1, 0) + np.roll(L, -1, 0))


def checker_index(L, mask, x0=0, y0=0):
    """|mean( hp * (-1)^(x+y) )| / rms( hp ) over `mask`. A pure period-2 checkerboard scores 1."""
    hp = highpass(L)
    H, W = L.shape
    ys, xs = np.mgrid[0:H, 0:W]
    sgn = 1.0 - 2.0 * ((xs + x0 + ys + y0) % 2)
    v = hp[mask]
    if v.size < 50:
        return float("nan"), 0.0, 0
    amp = abs((hp * sgn)[mask].mean())
    return amp / max(np.sqrt((v ** 2).mean()), 1e-9), amp, int(mask.sum())


def rim_mask(L, band=2):
    sky_l, leaf_l = np.percentile(L, 98), np.percentile(L, 2)
    sky = L > leaf_l + 0.90 * (sky_l - leaf_l)
    leaf = L < leaf_l + 0.35 * (sky_l - leaf_l)
    d = sky.copy()
    for dy in range(-band, band + 1):
        for dx in range(-band, band + 1):
            d |= np.roll(np.roll(sky, dy, 0), dx, 1)
    return d & ~sky & ~leaf, sky_l - leaf_l


def part1(tag="gate12"):
    print(f"1. THE CAPTURE — the rim on the delivered frames ({tag}, 1920x1080)\n")
    print(f"   {'box':44s} {'rim px':>7s} {'chk index':>10s} {'chk amp':>8s} {'contrast':>9s} {'amp/contrast':>13s}")
    out = {}
    for label, st, box in BOXES:
        a = np.asarray(Image.open(CAPS / f"{tag}_cam0{st}.png").convert("RGB")).astype(np.float64)
        x0, y0, x1, y1 = box
        L = lum(a[y0:y1, x0:x1])
        m, contrast = rim_mask(L)
        idx, amp, n = checker_index(L, m, x0, y0)
        print(f"   {label:44s} {n:7d} {idx:10.3f} {amp:8.2f} {contrast:9.1f} {amp / contrast:13.4f}")
        out[label] = idx
    return out


def load_frame_alpha(name="cypress_column_s2"):
    p = next(BAND.glob(f"band_ENV_tree_{name}_LOD1_albedo_4096.png"))
    im = Image.open(p).convert("RGBA")
    return np.asarray(im).astype(np.float64) / 255.0, p.name


def frame_texel(atlas_h, cell, f, frame_px=341.0, gutter_px=8.0, row_from_top=0.0):
    """web/src/impostors.js `frameTexel`, verbatim (rowFromTop = 0: the manifest counts from the bottom)."""
    g = np.clip(f, 0.0, 1.0)
    px = cell[0] * frame_px + gutter_px + g[..., 0] * INNER_PX
    py = cell[1] * frame_px + gutter_px + g[..., 1] * INNER_PX
    ty = py if row_from_top else (atlas_h - 1.0 - py)
    return px, ty


def reconstruct(atlas, cells, weights, uv):
    """The PREMULTIPLIED 8-tap reconstruction of impostors.js (PFA_FRAMES = 2 on the band path)."""
    H = atlas.shape[0]
    acc_a = np.zeros(uv.shape[:2])
    for cell, wk in zip(cells, weights):
        tx, ty = frame_texel(H, cell, uv)
        i0x, i0y = np.floor(tx), np.floor(ty)
        frx, fry = tx - i0x, ty - i0y

        def tap(dx, dy):
            xi = np.clip((i0x + dx).astype(int), 0, atlas.shape[1] - 1)
            yi = np.clip((i0y + dy).astype(int), 0, H - 1)
            return atlas[yi, xi, 3]

        bw = [(1 - frx) * (1 - fry), frx * (1 - fry), (1 - frx) * fry, frx * fry]
        for w, (dx, dy) in zip(bw, [(0, 0), (1, 0), (0, 1), (1, 1)]):
            acc_a += w * wk * tap(dx, dy)
    return acc_a


def quad_fwidth(a):
    """dFdx / dFdy as a GPU computes them: one difference per 2x2 QUAD, broadcast to its four
    fragments. That is why no derivative-driven term can ever carry a period-2 checkerboard."""
    H, W = a.shape
    ax = a[:, :W // 2 * 2].reshape(H, W // 2, 2)
    dx = (ax[:, :, 1] - ax[:, :, 0]).repeat(2, axis=1)
    ay = a[:H // 2 * 2, :].reshape(H // 2, 2, W)
    dy = (ay[:, 1, :] - ay[:, 0, :]).repeat(2, axis=0)
    if dx.shape[1] < W:
        dx = np.pad(dx, ((0, 0), (0, W - dx.shape[1])), mode="edge")
    if dy.shape[0] < H:
        dy = np.pad(dy, ((0, H - dy.shape[0]), (0, 0)), mode="edge")
    return np.abs(dx) + np.abs(dy)


def shader_cov(atlas, mag, f=0.35, cells=((3, 0), (4, 0))):
    """web/src/impostors.js, main(), down to `pfaCov`: the value handed to the coverage mask.
    `mag` is SCREEN PX PER ATLAS TEXEL, the shader's own pfaMag, so the card spans INNER_PX * mag
    screen pixels and the whole card is rasterised - silhouette, interior and all."""
    span = INNER_PX * mag
    side = int(round(span))
    ys, xs = np.mgrid[0:side, 0:side]
    u = (xs + 0.5) / span
    v = (ys + 0.5) / span
    uv = np.stack([np.clip(u, 0, 1), np.clip(v, 0, 1)], axis=-1)
    a = reconstruct(atlas, cells, (1.0 - f, f), uv)
    fw = quad_fwidth(a)
    cov_a2c = np.clip((a - ALPHA_TEST) / np.maximum(fw, 1e-4) + 0.5, 0, 1)
    mag_t = np.clip((mag - MAG_LO) / max(MAG_HI - MAG_LO, 1e-4), 0, 1)
    cov_w = np.maximum(fw * max(mag, 1.0) * RAMP, 1e-5)
    cov_ramp = np.clip((a - ALPHA_TEST) / cov_w + 0.5, 0, 1)
    cov_mag = cov_ramp + (np.clip(a, 0, 1) - cov_ramp) * SHARE
    return cov_a2c + (cov_mag - cov_a2c) * mag_t, a


def bayer2(shape):
    ys, xs = np.mgrid[0:shape[0], 0:shape[1]]
    m = np.array([[0.0, 2.0], [3.0, 1.0]])          # the classic 2x2 ordered matrix
    return (m[ys % 2, xs % 2] + 0.5) / 4.0


def resolve(cov, samples, dither):
    """The alpha-to-coverage mask, then the MSAA resolve, as three models of the hardware.
    `dither` is 'none' (a mask that is a function of alpha alone), '2x2' (a 2x2 ordered offset,
    which is what GL ES 3.0 s15.1.3 permits) or 'eighth' (a 2x2 offset at half a sample step,
    which is the 1/8 ladder Apple's mask is measured to produce)."""
    if dither == "none":
        pop = np.floor(cov * samples + 0.5)
    elif dither == "2x2":
        pop = np.floor(cov * samples + bayer2(cov.shape))
    elif dither == "eighth":
        pop = np.floor(cov * samples + 0.25 + 0.5 * (bayer2(cov.shape) - 0.375))
    else:
        raise ValueError(dither)
    return np.clip(pop, 0, samples) / samples


def quantise(cov, samples):
    """THE FIX: snap the coverage to the target's own sample ladder before the mask sees it.
    popcount = floor( cov*N + d ) with any d in [0,1) is exactly cov*N when cov*N is an integer, so
    the mask stops depending on the pixel position whatever the dither is. N is a power of two and
    1/N is exact in binary floating point, so the integer is exact, not nearly."""
    return np.floor(cov * samples + 0.5) / samples


def part2and3(measured):
    atlas, name = load_frame_alpha()
    print(f"\n2. THE SHADER over the real atlas texels ({name}, 4096x1024, inner {INNER_PX:.0f} px)\n")
    print(f"   {'regime':34s} {'magT':>5s} {'frac px':>8s} {'chk index of pfaCov':>20s}")
    covs = {}
    for label, mag in (("station 5: minified, 0.5 px/texel", 0.5),
                       ("station 2: magnified, 2.2 px/texel", 2.2)):
        cov, a = shader_cov(atlas, mag)
        frac = (cov > 0.001) & (cov < 0.999)
        idx, _amp, n = checker_index(cov * 255.0, frac)
        mag_t = np.clip((mag - MAG_LO) / (MAG_HI - MAG_LO), 0, 1)
        print(f"   {label:34s} {mag_t:5.2f} {n:8d} {idx:20.4f}")
        covs[label] = (cov, frac)
    print("\n   -> the field the shader hands to the mask carries NO period-2 term at either regime.")

    print("\n3. THE COVERAGE MASK — three models of it, before and after the fix (samples = 4)\n")
    print(f"   {'regime':34s} {'dither':8s} {'chk index now':>14s} {'chk index + fix':>16s}")
    for label, (cov, frac) in covs.items():
        for d in ("none", "2x2", "eighth"):
            now = resolve(cov, 4, d)
            fixed = resolve(quantise(cov, 4), 4, d)
            i_now, _a, _n = checker_index(now * 255.0, frac)
            i_fix, _a, _n = checker_index(fixed * 255.0, frac)
            print(f"   {label:34s} {d:8s} {i_now:14.3f} {i_fix:16.3f}")
    print("\n   measured on the delivered frames, for comparison:")
    for k, v in measured.items():
        print(f"      {k:44s} {v:.3f}")


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    m = part1()
    if what != "capture":
        part2and3(m)
