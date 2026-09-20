#!/usr/bin/env python3
"""Phase 9 item 1 — the dotted rim on the far-crown silhouettes (QA 21 item 1), proved WITHOUT a GPU.

    python3 web/tools/p9v_rim.py                     # the whole argument, all three parts
    python3 web/tools/p9v_rim.py capture             # part 1 only, on renders/web/gate12_cam0N.png
    python3 web/tools/p9v_rim.py capture p9v         # part 1 on another capture tag (the AFTER frames)
    python3 web/tools/p9v_rim.py ab gate12 p9v       # the A/B: ONE rim mask, from the BEFORE frame
    python3 web/tools/p9v_rim.py selftest            # the frame guard and the A/B, no GPU, no capture

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

3. THE ONLY STAGE LEFT is the hardware's alpha-to-coverage mask.  GL ES 3.0 s15.1.3 says of the
   algorithm that turns alpha into coverage: "The algorithm can and probably should be different at
   different pixel locations" - i.e. dither.  Push the same smooth pfaCov through three models of it
   - no dither, a 2x2 dither, and a 1/8-step dither - and compare the checkerboard index with part
   1's measurement.  Then push it through the FIX (quantise pfaCov to the target's own sample ladder
   before the mask sees it) under the same dither models.  All three models are per-pixel scalar
   OFFSETS, so their "after the fix" column is arithmetic, not evidence (r1 review 3): the capture
   is what decides, and `ab` below is how it is scored.
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

# THE FRAME THE BOXES WERE READ IN (h, w).  r1 review 6: the boxes below are absolute rectangles, so
# a 960 px copy or a mobile capture would print plausible numbers for the WRONG pixels - and the rim
# is a per-pixel, period-2 phenomenon that no resample carries anyway.  Every frame this tool opens
# is therefore asserted against FRAME (`_frame`), and BOXES are DERIVED from it rather than written
# out.
#
# `boxes_for` is a RESAMPLE lever, not a re-aim (r2 review carry 2).  It follows the crowns only while
# the CAMERA is unchanged - i.e. for a 1920x1080 frame rescaled to another pixel count at the same 16:9
# aspect.  At a different aspect the viewer's own camera aspect changes with the canvas, so a crown
# does not move affinely with its rectangle and the scaled box lands somewhere else; the 1170x2532
# mobile frames are exactly that case, which is why `_frame` refuses every frame where `boxes_for` is
# not the identity.  To measure another aspect, re-read the boxes there - do not scale these.
FRAME = (1080, 1920)

# QA 21 §2b's two boxes, plus a control crown with a building behind it instead of sky, stated in the
# 1920x1080 delivery frame they were measured in.
FRAME_REF = (1080, 1920)
BOXES_REF = [("05 left crown  (sky behind, QA 21)", 5, (0, 480, 200, 640)),
             ("02 right cypress (sky behind, QA 21)", 2, (1700, 370, 1900, 660)),
             ("01 hero crown  (building behind, control)", 1, (760, 545, 1000, 690))]


def boxes_for(frame):
    """BOXES_REF scaled from FRAME_REF into `frame` (h, w).  Identity at the delivery resolution."""
    sx, sy = frame[1] / FRAME_REF[1], frame[0] / FRAME_REF[0]
    return [(label, st, (int(round(x0 * sx)), int(round(y0 * sy)),
                         int(round(x1 * sx)), int(round(y1 * sy))))
            for label, st, (x0, y0, x1, y1) in BOXES_REF]


BOXES = boxes_for(FRAME)


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
    """The partly covered pixels that touch sky.  For an A/B this is derived ONCE, from the BEFORE
    frame, and then REUSED on the after frame (r1 review 6): re-deriving it per frame scores a
    different pixel set on each side, so the rim-pixel count would move for two reasons at once and
    neither column would mean what it says."""
    sky_l, leaf_l = np.percentile(L, 98), np.percentile(L, 2)
    sky = L > leaf_l + 0.90 * (sky_l - leaf_l)
    leaf = L < leaf_l + 0.35 * (sky_l - leaf_l)
    d = sky.copy()
    for dy in range(-band, band + 1):
        for dx in range(-band, band + 1):
            d |= np.roll(np.roll(sky, dy, 0), dx, 1)
    return d & ~sky & ~leaf, sky_l - leaf_l


def _box(tag, st, box, caps=None):
    """The luminance inside one box of one capture, with the frame size ASSERTED (r1 review 6)."""
    p = (caps or CAPS) / f"{tag}_cam0{st}.png"
    a = np.asarray(Image.open(p).convert("RGB")).astype(np.float64)
    if a.shape[:2] != FRAME:
        raise SystemExit(f"{p.name} is {a.shape[1]}x{a.shape[0]}, not {FRAME[1]}x{FRAME[0]}: the "
                         f"boxes are delivery-frame rectangles and the rim is a per-pixel, period-2 "
                         f"pattern that no resample carries. Capture at {FRAME[1]}x{FRAME[0]}.")
    x0, y0, x1, y1 = box
    return lum(a[y0:y1, x0:x1])


def part1(tag="gate12", caps=None):
    print(f"1. THE CAPTURE — the rim on the delivered frames ({tag}, {FRAME[1]}x{FRAME[0]})\n")
    print(f"   {'box':44s} {'rim px':>7s} {'chk index':>10s} {'chk amp':>8s} {'contrast':>9s} {'amp/contrast':>13s}")
    out = {}
    for label, st, box in BOXES:
        L = _box(tag, st, box, caps)
        m, contrast = rim_mask(L)
        idx, amp, n = checker_index(L, m, box[0], box[1])
        print(f"   {label:44s} {n:7d} {idx:10.3f} {amp:8.2f} {contrast:9.1f} {amp / contrast:13.4f}")
        out[label] = idx
    return out


def part_ab(before, after, caps=None):
    """The A/B the capture round owes.  ONE rim mask, derived from the BEFORE frame and applied
    unchanged to both, so the two columns differ only by what the fix did (r1 review 6)."""
    print(f"THE A/B — one rim mask, derived from {before} and applied to both\n")
    print(f"   {'box':44s} {'rim px':>7s} {'chk ' + before:>13s} {'chk ' + after:>13s} {'MAE/255':>8s}")
    out = {}
    for label, st, box in BOXES:
        b = _box(before, st, box, caps)
        a = _box(after, st, box, caps)
        m, _contrast = rim_mask(b)                 # ONE mask, from the baseline
        ib, _amp, n = checker_index(b, m, box[0], box[1])
        ia, _amp, _n = checker_index(a, m, box[0], box[1])
        mae = float(np.abs(a - b).mean())
        print(f"   {label:44s} {n:7d} {ib:13.3f} {ia:13.3f} {mae:8.3f}")
        out[label] = (n, ib, ia, mae)
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


def _synth(dirp, tag, dither):
    """Three synthetic frames at the delivery size: sky, a dark crown filling the left half of each
    box, and a two-pixel rim between them that is either period-2 dithered or flat."""
    for _label, st, (x0, y0, x1, y1) in BOXES:
        a = np.full((FRAME[0], FRAME[1], 3), 200.0)
        xm = (x0 + x1) // 2
        a[y0:y1, x0:xm] = 20.0
        ys, xs = np.mgrid[y0:y1, xm:xm + 2]
        rim = np.full(xs.shape, 110.0)
        if dither:
            rim += 30.0 * (1 - 2 * ((xs + ys) % 2))
        a[y0:y1, xm:xm + 2] = rim[..., None]
        Image.fromarray(a.astype(np.uint8)).save(dirp / f"{tag}_cam0{st}.png")


def selftest():
    """r1 review 6, proved without a capture: the frame guard fires, the boxes are derived from
    FRAME, and the A/B scores ONE mask on both sides."""
    import tempfile
    ok = True

    def check(name, cond):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"   {'PASS' if cond else 'FAIL'}  {name}")

    print("SELFTEST — the frame guard and the A/B\n")
    check("BOXES are derived from FRAME and are identity at the delivery size",
          [b[2] for b in BOXES] == [b[2] for b in BOXES_REF])
    check("halving FRAME halves the rectangles",
          boxes_for((FRAME_REF[0] // 2, FRAME_REF[1] // 2))[0][2] == (0, 240, 100, 320))
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _synth(d, "before", dither=True)
        _synth(d, "after", dither=False)
        # the guard: a 960 px copy of a real box must be refused, not scored
        small = Image.open(d / "before_cam05.png").resize((960, 540))
        small.save(d / "small_cam05.png")
        try:
            _box("small", 5, BOXES[0][2], caps=d)
            check("a 960x540 frame is refused", False)
        except SystemExit as e:
            check("a 960x540 frame is refused", "960x540" in str(e))
        ab = part_ab("before", "after", caps=d)
        same = part_ab("before", "before", caps=d)
        for label, st, _box_ in BOXES:
            n, ib, ia, mae = ab[label]
            sn, sib, sia, smae = same[label]
            check(f"cam0{st}: the rim mask is the same pixel set on both sides", n == sn and n >= 50)
            check(f"cam0{st}: a frame against itself scores equal and MAE 0", sib == sia and smae == 0.0)
            check(f"cam0{st}: the dithered rim scores above the flat one ({ib:.3f} > {ia:.3f})",
                  ib > ia + 0.1)
            check(f"cam0{st}: and the two frames do differ (MAE {mae:.2f})", mae > 0)
    print("\n   all passed" if ok else "\n   FAILURES above")
    return 0 if ok else 1


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what == "selftest":
        sys.exit(selftest())
    elif what == "ab":
        if len(sys.argv) < 4:
            raise SystemExit("usage: p9v_rim.py ab <before tag> <after tag>")
        part_ab(sys.argv[2], sys.argv[3])
    else:
        m = part1(sys.argv[2] if len(sys.argv) > 2 else "gate12")
        if what != "capture":
            part2and3(m)
