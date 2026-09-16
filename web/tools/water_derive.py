#!/usr/bin/env python3
"""QA-14-1 item 1a: the murk derivation and its evidence, reproducible without the viewer.

    python3 web/tools/water_derive.py [VIEWER_FRAME.png ...]

Prints, in order:
  1. the derivation itself (the same arithmetic as web/src/water.js derivedMurk(), independently);
  2. the sky irradiances it reads, integrated from the exported equirects, so the constants baked
     into water.js can be re-checked against a re-export;
  3. the SCENE-LINEAR value of the `open water` crop in the Phase 5 hero and in each frame given,
     obtained by inverting the delivery LUT (AgX High Contrast at -2.833 EV) numerically - the LUT
     round-trips its own manifest proof patches to < 0.1/255;
  4. what reflection radiance each of those implies, given the derived murk and a Schlick F, which
     is how the level deficit is attributed between the body term and the reflection.

Reads only from the MAIN checkout's export/out and renders/.
"""
import os, sys
from pathlib import Path
import numpy as np

os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "1")
import cv2
from PIL import Image

MAIN = Path(os.environ.get("PFA_MAIN_ROOT") or "/Users/dk/Projects/3d render blender 3rd attempt building")
REF = MAIN / "renders/previews/qa/round10b_01_lagoon_hero_cycles.png"
CUBE = MAIN / "export/out/gate0/lut_agx_high_contrast_65.cube"
SKY_CAMERA = MAIN / "export/out/gate0/sky_camera_4096x2048.exr"
SKY_DIFFUSE = MAIN / "export/out/gate3/sky_diffuse_1024x512.exr"
BOX = (300, 900, 1600, 1060)
LUMA = np.array([0.2126, 0.7152, 0.0722])
MIN_EV, MAX_EV, PIVOT, EV = -12.47393, 4.026069, 0.18, -2.8331398963928223

# --- the material and the reference sheet -------------------------------------------------------
DENSITY, SCAT, ABSC, G = 0.7, np.array([0.205, 0.250, 0.195]), np.array([0.70, 0.80, 0.68]), 0.3
DEPTH, BED = 1.5, np.array([0.12, 0.10, 0.06])
SUN_W, SUN_EL_DEG, SUN_COL = 67.31939697265625, 7.357, np.array([1.0, 0.607324, 0.0])
T_SKY, T_SUN, R_INT, IOR = 0.934, 0.544, 0.48, 1.333


def sky_irradiance(p):
    a = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)[..., ::-1].astype(np.float64)
    h, w, _ = a.shape
    th = np.pi * (np.arange(h) + 0.5) / h
    wg = np.where(th < np.pi / 2, np.cos(th) * np.sin(th) * (np.pi / h) * (2 * np.pi / w), 0.0)
    return (a * wg[:, None, None]).sum(axis=(0, 1))


def load_cube(p):
    size, vals = None, []
    for ln in open(p):
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        if ln.upper().startswith("LUT_3D_SIZE"):
            size = int(ln.split()[1]); continue
        if ln.upper().startswith(("TITLE", "DOMAIN_")):
            continue
        q = ln.split()
        if len(q) == 3:
            try:
                vals.append([float(x) for x in q])
            except ValueError:
                pass
    return np.array(vals).reshape(size, size, size, 3), size


def apply_lut(lin, lut, size):
    c = np.asarray(lin, dtype=np.float64) * 2.0 ** EV
    t = np.clip((np.log2(np.maximum(c, 1e-10) / PIVOT) - MIN_EV) / (MAX_EV - MIN_EV), 0, 1) * (size - 1)
    i0 = np.clip(np.floor(t).astype(int), 0, size - 2)
    f = t - i0
    out = np.zeros(c.shape)
    for dz in (0, 1):
        for dy in (0, 1):
            for dx in (0, 1):
                w = ((1 - f[..., 2]) if dz == 0 else f[..., 2]) * ((1 - f[..., 1]) if dy == 0 else f[..., 1]) \
                    * ((1 - f[..., 0]) if dx == 0 else f[..., 0])
                out += w[..., None] * lut[i0[..., 2] + dz, i0[..., 1] + dy, i0[..., 0] + dx]
    return out


def invert(disp, lut, size):
    lin = np.array([0.5, 0.5, 0.5])
    for _ in range(400):
        cur = apply_lut(lin, lut, size)
        err = disp - cur
        if np.abs(err).max() < 1e-6:
            break
        for ch in range(3):
            h = max(lin[ch] * 0.01, 1e-7)
            p = lin.copy(); p[ch] += h
            d = (apply_lut(p, lut, size)[ch] - cur[ch]) / h
            if d > 1e-9:
                lin[ch] = max(lin[ch] + err[ch] / d * 0.7, 1e-7)
    return lin


def hue_sat(m):
    r, g, b = m
    mx, mn = float(max(m)), float(min(m))
    d = mx - mn
    if d < 1e-12:
        return 0.0, 0.0
    h = 60 * ((b - r) / d + 2) if mx == g else (60 * ((r - g) / d + 4) if mx == b else 60 * (((g - b) / d) % 6))
    return h, d / mx


def crop_mean(p):
    im = Image.open(p).convert("RGB")
    if im.size != (1920, 1080):
        im = im.resize((1920, 1080), Image.LANCZOS)
    a = np.asarray(im, dtype=np.float64)
    x0, y0, x1, y1 = BOX
    return a[y0:y1, x0:x1].reshape(-1, 3).mean(axis=0)


def main():
    e_sky_cam, e_sky_dif = sky_irradiance(SKY_CAMERA), sky_irradiance(SKY_DIFFUSE)
    e_sun = SUN_W * np.sin(np.radians(SUN_EL_DEG)) * SUN_COL
    print(f"E_sky  camera branch  {np.round(e_sky_cam, 3)}   B/R {e_sky_cam[2]/e_sky_cam[0]:.2f}")
    print(f"E_sky  diffuse branch {np.round(e_sky_dif, 3)}   B/R {e_sky_dif[2]/e_sky_dif[0]:.2f}  (lighting's shade fill; NOT used)")
    print(f"E_sun  horizontal     {np.round(e_sun, 3)}")

    sa, ss = DENSITY * (1 - ABSC), DENSITY * SCAT
    B = (1 - G) / (2 * G) * ((1 + G) / np.sqrt(1 + G * G) - 1)
    bb = ss * B
    k = sa + bb
    r_col = bb / k * (1 - np.exp(-2 * k * DEPTH))
    r_bot = BED * np.exp(-2 * sa * DEPTH)
    a_up = r_col + r_bot
    e_in = T_SKY * e_sky_cam + T_SUN * e_sun
    murk = a_up * e_in / (1 - R_INT * a_up) / (np.pi * IOR ** 2)
    print(f"\nsigma_a {np.round(sa,4)}  sigma_s {np.round(ss,4)}  B(g={G}) {B:.5f}")
    print(f"R_column {np.round(r_col,4)}  R_bottom {np.round(r_bot,4)}  A_up {np.round(a_up,4)}")
    print(f"   cross-check: Phase 5 WATER_MURK albedo (0.165, 0.170, 0.1025), independent")
    print(f"E_in {np.round(e_in,3)}")
    print(f"MURK = {np.round(murk,4)}   hue {hue_sat(murk)[0]:.1f} sat {hue_sat(murk)[1]:.3f}")

    lut, size = load_cube(CUBE)
    print(f"\nopen water {BOX}, scene-linear by inverting the delivery LUT")
    for p in [REF] + [Path(x) for x in sys.argv[1:]]:
        m = crop_mean(p)
        lin = invert(m / 255.0, lut, size)
        h, s = hue_sat(m)
        # F at the crop's mean geometry: camera 2.6 m over the water, rows 900-1060 -> 12.9-20.8 deg
        F = np.mean([0.02 + 0.98 * (1 - np.sin(np.radians(t))) ** 5 for t in (12.93, 20.78)])
        implied = (lin - (1 - F) * murk) / F
        print(f"  {p.name[:44]:44s} rgb {np.round(m,1)} lum {float(m@LUMA):6.1f} hue {h:5.1f} sat {s:.3f}")
        print(f"      linear {np.round(lin,4)}   implied reflection at F={F:.3f}: {np.round(implied,3)}")


if __name__ == "__main__":
    main()
