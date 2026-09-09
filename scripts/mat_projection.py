"""Round 9 -- the photo-projection pass: build the ratio map and the mask pack from ref 169.

    python3 scripts/mat_projection.py build [--render <projector.png>] [--out assets/textures/projection]
    python3 scripts/mat_projection.py stats                        # re-print the numbers from the shipped maps

What the two maps are (docs/briefs/materials_r8_projection.md, constraints 1-6):

  PFA_photo_ratio.png   RGB, 1920x1080, Non-Color.  Stored value = ratio / 2 (decode: x2 in the shader).
                        ratio = ref169_aligned / render, i.e. the per-pixel correction that turns THIS build's
                        stone into the photograph's, with two parts pulled out of it first:
                          * the global chroma of the correction, `M_chroma` (a luminance-normalised RGB mean over
                            the calibration region), which is printed here and applied to the base albedo of the
                            band materials instead -- so the chroma fix (QA-07-2) works from EVERY camera and
                            cannot make a seam, and the map only ever carries spatial structure;
                          * the calibration region's mean luminance, so the map is mean-1 exactly where QA's
                            sunlit attic box is and the sunlit luminance window (178-201) is held by construction.
                        Because it is a ratio against a render that already carries the rig's sun, the photo's own
                        sun divides out; what is left is reflectance (constraint 1).  Values are clipped to
                        [RATIO_LO, RATIO_HI] and the clip is what the confidence mask below is built from.

  PFA_photo_mask.png    RGB, 1920x1080, Non-Color.  R = confidence (how far the raw ratio had to be clipped /
                        how far the render and the photo disagree at that pixel -- sky, trees, sculpture the model
                        does not have, and any sun/shadow disagreement all fall out here), G = the band mask
                        (drum + attic + entablature rows, with soft ramps), B = render coverage (the border render
                        actually has data there).  The shader multiplies all three by the facing mask, the
                        world-space band gate and the global `Photo` weight.

Frame convention: BOTH maps live in the frame of the camera `scripts/arch_uvproj.py` baked `UVProj` from
(cam01 before the round-08 station move: loc (-14.1, 100.0, 1.6), 20 mm, shift_y 0.06), because that is the frame
`arch_params.REF169_XF` was fitted in.  `scripts/mat_r9_render.py --jobs before` renders the denominator from a
reconstruction of exactly that camera.

Per-course registration (constraint 3): the photo is warped with REF169_XF AND a piecewise-linear vertical shift
`STACK` taken from QA round 07 section (g) (render row minus ref row, course by course), so each photographic
course lands on the modelled course that means the same thing.  Geometry is never moved.
"""
import sys, os, json
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import arch_params as P                                   # REF169_XF + the photo path, no bpy

HERO = (1920, 1080)
OUT_DIR = ROOT / "assets" / "textures" / "projection"
RENDER = ROOT / "renders" / "previews" / "materials" / "r9_cycles_projector.png"
RATIO_PNG, MASK_PNG = "PFA_photo_ratio.png", "PFA_photo_mask.png"
META = "projection_meta.json"

# --- QA round 07 section (g): render row - ref row, on the same (z 1.6) station and the same REF169_XF ---------
STACK = [(165, -4), (181, -1), (199, +1), (265, -5), (281, -1), (294, +2), (301, +4), (321, 0), (333, +5)]

# --- the band the projection is allowed to touch, in render rows: drum + attic + entablature ------------------
BAND = (86, 100, 312, 328)            # ramp up 86->100, full, ramp down 312->328 (architrave top is row 321)
BORDER = (40, 400)                    # rows mat_r9_render.py rendered
CALIB = (900, 222, 1020, 256)         # QA's attic_sunlit box: the project's calibration point for lit stone
# The ratio is built in TWO bands, which is what makes it survive its own clip.  LF (sigma 10 px = 0.75 m on the
# wall) is the ratio of LOCAL MEANS: the honest photometric correction, and the only part whose box average the
# render actually follows -- a single-band per-pixel ratio in a high-contrast box (the shaded attic ressaut,
# render std 51) puts 23 % of its pixels outside any sane clip and loses two thirds of the correction.  HF is what
# is left after LF is divided out: the streaks and the panel relief, mean 1 by construction, clipped on its own.
LF_SIGMA, MF_SIGMA, HF_SIGMA = 10.0, 3.0, 1.1
LF_LO, LF_HI = 0.65, 1.55             # a LOCAL MEAN correction is never more than this if both frames show stone
MF_LO, MF_HI = 0.62, 1.62
# How much of each finer band is kept.  MEASURED (the sweep in docs/materials_notes.md round 9): the photograph's
# streaks and the procedural streaks are UNCORRELATED, so mixing them destroys variance -- at HF_K 1.0 / weight 0.6
# the attic box's texture std ratio falls 0.68 -> 0.55, i.e. the projection would break the very test it was
# commissioned to fix, while the model's own anisotropy already equals the photograph's (4.00 against 4.08).
# What the photograph is worth here is its PHOTOMETRY (level and colour, course by course), not its texture, so
# the 1.1 px band is dropped entirely and the 0.22-0.75 m band is kept at half strength.
MF_K, HF_K = 0.5, 0.0
RATIO_LO, RATIO_HI = 0.45, 2.00       # the encoding clip (stored as ratio / 2)
CONF_IN, CONF_OUT = 0.40, 0.85        # |log(LF luminance)| for full / zero confidence (1.49x and 2.34x): sky,
                                      # foliage and sculpture the model does not have fall out here, weathering
                                      # does not
BLUR_SIGMA = HF_SIGMA                 # kept for the metadata


def gauss(a, sigma):
    """Separable Gaussian on a HxW or HxWxC float array (no scipy in this environment)."""
    if sigma <= 0:
        return a
    r = max(1, int(3 * sigma))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    out = a.astype(np.float64)
    for axis in (0, 1):
        pad = [(0, 0)] * out.ndim
        pad[axis] = (r, r)
        p = np.pad(out, pad, mode="edge")
        acc = np.zeros_like(out)
        for i, w in enumerate(k):
            sl = [slice(None)] * out.ndim
            sl[axis] = slice(i, i + out.shape[axis])
            acc += w * p[tuple(sl)]
        out = acc
    return out


def stack_delta(rows):
    """render_row - ref_row, piecewise linear between the QA round-07 courses, held flat outside them."""
    xs = np.array([c[0] for c in STACK], float)
    ys = np.array([c[1] for c in STACK], float)
    return np.interp(rows, xs, ys)


def warp_ref169():
    """ref 169 -> the projector frame: photo px * S + D = render px (arch_params.REF169_XF), plus the per-course
    vertical shift.  Bilinear, done by hand (no scipy)."""
    S, DX, DY = P.REF169_XF
    src = np.asarray(Image.open(str(P.ref169_path())).convert("RGB")).astype(np.float64)
    H, W = HERO[1], HERO[0]
    cols = np.arange(W, dtype=np.float64)
    rows = np.arange(H, dtype=np.float64)
    # the render row r should show the photo content of the ALIGNED row r - delta(r)
    aligned_rows = rows - stack_delta(rows)
    sx = (cols - DX) / S                                   # source columns, shape (W,)
    sy = (aligned_rows - DY) / S                           # source rows, shape (H,)
    sh, sw = src.shape[:2]
    x0 = np.clip(np.floor(sx), 0, sw - 2).astype(int); fx = np.clip(sx - x0, 0, 1)
    y0 = np.clip(np.floor(sy), 0, sh - 2).astype(int); fy = np.clip(sy - y0, 0, 1)
    inb = ((sx >= 0) & (sx <= sw - 1))[None, :] & ((sy >= 0) & (sy <= sh - 1))[:, None]
    a = src[np.ix_(y0, x0)]; b = src[np.ix_(y0, x0 + 1)]
    c = src[np.ix_(y0 + 1, x0)]; d = src[np.ix_(y0 + 1, x0 + 1)]
    FX = fx[None, :, None]; FY = fy[:, None, None]
    out = (a * (1 - FX) * (1 - FY) + b * FX * (1 - FY) + c * (1 - FX) * FY + d * FX * FY)
    return out, inb


def ramp(x, lo, hi):
    return np.clip((x - lo) / (hi - lo), 0.0, 1.0)


def band_mask(H, W):
    r = np.arange(H, dtype=np.float64)
    m = np.minimum(ramp(r, BAND[0], BAND[1]), 1.0 - ramp(r, BAND[2], BAND[3]))
    m = np.clip(m, 0.0, 1.0)
    return np.repeat(m[:, None], W, axis=1)


def build(render_path, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    ren = np.asarray(Image.open(render_path).convert("RGB")).astype(np.float64)
    if ren.shape[:2] != (HERO[1], HERO[0]):
        raise SystemExit(f"render must be {HERO[0]}x{HERO[1]}, got {ren.shape[1]}x{ren.shape[0]}")
    pho, inb = warp_ref169()
    H, W = ren.shape[:2]

    lum = lambda a: 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    covered = np.zeros((H, W), bool)
    covered[BORDER[0]:BORDER[1], :] = True
    cov = covered & inb & (lum(ren) > 6.0)                 # the border render's own data

    # --- raw ratio, two bands ---------------------------------------------------------------------------------
    r10 = np.maximum(gauss(pho, LF_SIGMA), 1.0) / np.maximum(gauss(ren, LF_SIGMA), 4.0)
    r3 = np.maximum(gauss(pho, MF_SIGMA), 1.0) / np.maximum(gauss(ren, MF_SIGMA), 4.0)
    r1 = np.maximum(gauss(pho, HF_SIGMA), 1.0) / np.maximum(gauss(ren, HF_SIGMA), 4.0)
    lf, mf, hf = r10, r3 / r10, r1 / r3
    raw = np.clip(lf, LF_LO, LF_HI) * np.clip(mf, MF_LO, MF_HI) ** MF_K * np.clip(hf, MF_LO, MF_HI) ** HF_K

    x0, y0, x1, y1 = CALIB
    calib = np.zeros((H, W), bool); calib[y0:y1, x0:x1] = True
    calib &= cov
    M = pho[calib].mean(axis=0) / ren[calib].mean(axis=0)   # RGB mean correction over the calibration region
    Mlum = float(0.2126 * M[0] + 0.7152 * M[1] + 0.0722 * M[2])
    M_chroma = M / Mlum                                     # luminance-neutral: the chroma half, goes to the albedo

    S = raw / M_chroma[None, None, :]                       # what is left after the global chroma correction
    # Normalise on the GEOMETRIC mean, not the arithmetic one.  What a box mean does when every pixel's albedo is
    # multiplied by S_p is (to first order) old_mean * exp(mean(log S)) ^ c -- a log-space average -- while
    # mean(S) is biased upward by Jensen (here 1.044 against a true correction of 0.996).  Normalising the
    # arithmetic mean to 1 therefore darkens the box by 4-5 %.  Target = the honest ratio of the two box means.
    target = float(lum(pho[calib].mean(axis=0)) / lum(ren[calib].mean(axis=0)))
    S *= target / float(np.exp(np.log(np.clip(lum(S[calib]), 1e-3, None)).mean()))

    # --- confidence: how far the render and the photo disagree, at the SCALE THAT MATTERS (LF) ------------------
    dev = np.abs(np.log(np.clip(lum(lf), 1e-3, None)))
    conf = 1.0 - ramp(dev, CONF_IN, CONF_OUT)
    conf *= cov
    Sc = np.clip(S, RATIO_LO, RATIO_HI)

    band = band_mask(H, W)
    w_eff = conf * band * cov                               # everything the maps themselves contribute

    # --- write -------------------------------------------------------------------------------------------------
    ratio_u8 = np.clip(np.rint(Sc / 2.0 * 255.0), 0, 255).astype(np.uint8)
    mask_u8 = np.stack([np.clip(np.rint(conf * 255), 0, 255),
                        np.clip(np.rint(band * 255), 0, 255),
                        np.clip(np.rint(cov * 255.0), 0, 255)], axis=-1).astype(np.uint8)
    Image.fromarray(ratio_u8).save(out_dir / RATIO_PNG, optimize=True)
    Image.fromarray(mask_u8).save(out_dir / MASK_PNG, optimize=True)

    inside = w_eff > 0.05
    meta = dict(
        ratio=RATIO_PNG, mask=MASK_PNG, res=[W, H],
        projector=dict(loc=[-14.1, 100.0, 1.6], target=[0.0, 0.0, 1.6], lens=20.0, shift_y=0.06,
                       note="the station scripts/arch_uvproj.py baked UVProj from"),
        ref169_xf=list(P.REF169_XF), stack=STACK, band=list(BAND), calib=list(CALIB),
        clip=[RATIO_LO, RATIO_HI], conf=[CONF_IN, CONF_OUT], blur_sigma=BLUR_SIGMA,
        bands=dict(lf=LF_SIGMA, mf=MF_SIGMA, hf=HF_SIGMA, mf_k=MF_K, hf_k=HF_K),
        M_rgb=[round(float(v), 4) for v in M], M_lum=round(Mlum, 4), calib_lum_target=round(target, 4),
        M_chroma=[round(float(v), 4) for v in M_chroma],
        px_in_band=int(inside.sum()),
        mean_conf_in_band=round(float(conf[band > 0.5].mean()), 4),
        clipped_frac=round(float((np.abs(Sc - S).max(axis=-1) > 1e-9)[inside].mean()), 4),
        ratio_lum_p05_p50_p95=[round(float(v), 4) for v in np.percentile(lum(Sc)[inside], [5, 50, 95])],
        render=str(Path(render_path).name),
    )
    (out_dir / META).write_text(json.dumps(meta, indent=2) + "\n")
    for k, v in meta.items():
        if k not in ("stack",):
            print(f"[projection] {k}: {v}")
    return meta


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "build"
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else OUT_DIR
    ren = Path(argv[argv.index("--render") + 1]) if "--render" in argv else RENDER
    if cmd == "build":
        build(ren, out)
    elif cmd == "stats":
        print((out / META).read_text())
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
