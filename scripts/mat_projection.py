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
RATIO_LO, RATIO_HI = 0.45, 2.00       # the encoding clip (stored as ratio / 2), now in SCENE-LINEAR albedo units

# --- ROUND 9b (docs/reviews/mat_r9_review.md finding 3): the map is a SCENE-LINEAR albedo multiplier ------------
# Round 9 divided two AgX display-space PNGs and handed the quotient to the shader as a multiplier on the
# scene-linear albedo.  Those are different spaces, and the round's own phtest measured the cost: where the map
# asked the shaded attic for -9.6 % it delivered -3.9 %, i.e. 0.40 of its own correction, by construction.
#
# The fix: a display ratio D at a pixel whose render sits at display luminance L needs a SCENE multiplier
#     S = D ** (1 / t_eff(L)),      t_eff(L) = d log(display) / d log(albedo)
# and t_eff is measured, not assumed, in two parts:
#
#   t_agx(L)  the view pipeline's own transfer, from `scripts/mat_r9b_agx.py` at the SHIPPED look
#             ("AgX - High Contrast", exposure -2.8331) -- 0.552 at the shaded attic's 132.9, 0.273 at the sunlit
#             attic's 189.8.  Round 9's table was measured at Base Contrast and is not this table.
#   f(L)      the fraction of the pixel's scene radiance that actually scales with this albedo.  The rest is the
#             compositor's haze/bloom (light_build.build_compositor_group) and any term the band materials do not
#             own; it is additive in scene radiance, so it dilutes the dark end far more than the bright end.
#             ONE number is measured in situ -- the round-9 Photo 0 -> 1 pair on the shaded attic gives
#             t_eff = ln(130.3/135.6) / ln(0.904) = 0.394 against t_agx 0.552, so f = 0.714 there -- and the
#             pedestal E_other = (1 - f) * E(132.9) that this implies is then carried to every other level with
#             f(L) = 1 - E_other / E(L).  E(L) is the chart's own scene-value-to-display-luminance curve.
#             At the sunlit attic that gives f 0.884, i.e. exponent 4.15; at the shaded attic exponent 2.55.
#
# Only the LF band is linearised.  LF is the photometric (level) correction and its target IS a display level, so
# it has to be inverted through the pipeline.  MF is a TEXTURE term whose half weight was chosen by the round-9
# sweep of the DELIVERED attic std ratio (a hold item, >= 0.60): linearising it would multiply its delivered
# contrast by ~2.7 and break the test the projection was commissioned to fix.  MF therefore stays a display-space
# exponent and its delivered strength is bit-for-bit what round 9 measured.
TRANSFER_JSON = "agx_transfer.json"
INSITU = dict(box="attic_shaded", display_lum=132.9, t_eff=0.394,
              source="renders/logs/mat_r9_phtest.log: 135.6 -> 130.3 for a map asking -9.6 %")
EXP_LO, EXP_HI = 1.0, 5.5             # exponent clamp: below 1.0 the map would be weaker than display space, and
                                      # above 5.5 an 8-bit ratio's own quantisation would dominate the correction
F_MIN = 0.45                          # floor on the albedo-coupled fraction (deep shade is mostly pedestal)
# What an ALBEDO is allowed to be asked for.  Linearising makes a limit visible that display space hid: the band's
# median display ask is +19.6 %, which at these exponents is x1.8 on the albedo, and the band materials already
# sit at base albedo 0.42-0.75 -- x1.8 is not a reflectance any concrete has.  A correction that large is a LIGHT
# LEVEL deficit (QA-07-7 assigns it there), so the map saturates instead of clipping: |log S| passes through
# untouched up to the knee and then rolls off smoothly to the limit, which keeps the shaded attic's -18 % and the
# entablature's -6 % exact while the drum's impossible +80 % lands at +55 % with its spatial structure intact and
# no plateau edge for the seam test to find.
# The roll-off is ASYMMETRIC because the physics is: MAT_concrete_ochre's base albedo has luminance 0.589, so
# x1.55 puts it at 0.91 and x1.8 puts it over 1.0 -- there is a hard ceiling upward and none downward (stone can
# be as dark as it likes).  A symmetric knee at 1.15 was tried first and cost the shaded attic a third of its own
# correction (an -8.2 % ask compressed to -6.4 %), because that box's per-pixel corrections straddle -18 %.
LIN_KNEE_UP, LIN_LIMIT_UP = 1.15, 1.55
LIN_KNEE_DN, LIN_LIMIT_DN = 1.60, 2.20        # as ratios BELOW 1: 0.625 passes untouched, asymptote 0.455
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


def transfer_table(out_dir):
    """(L[], t_agx[], E[]) from scripts/mat_r9b_agx.py: display luminance, its transfer, its scene radiance."""
    p = out_dir / TRANSFER_JSON
    if not p.exists():
        raise SystemExit(f"missing {p} -- run: blender -b --python scripts/mat_r9b_agx.py -- --looks")
    j = json.loads(p.read_text())
    rows = sorted(j["rows"], key=lambda r: r["lum"])
    L = np.array([r["lum"] for r in rows])
    t = np.array([r["t_lum"] for r in rows])
    E = np.array([r["level"] for r in rows])           # scene radiance in units of the chart's AXIS
    return L, t, E, j


def exponent_field(Ldisp, table):
    """1 / t_eff(L): the power a DISPLAY ratio must be raised to, to become a SCENE-LINEAR albedo multiplier."""
    L, t, E, _ = table
    t_at = lambda x: np.interp(x, L, t)
    E_at = lambda x: np.interp(x, L, E)
    f_ref = INSITU["t_eff"] / float(t_at(INSITU["display_lum"]))
    E_other = (1.0 - f_ref) * float(E_at(INSITU["display_lum"]))
    f = np.clip(1.0 - E_other / np.maximum(E_at(Ldisp), 1e-6), F_MIN, 1.0)
    return np.clip(1.0 / np.maximum(f * t_at(Ldisp), 1e-3), EXP_LO, EXP_HI), f_ref, E_other


def _roll(a, knee, limit):
    k, m = np.log(knee), np.log(limit) - np.log(knee)
    return np.minimum(a, k) + m * np.tanh(np.maximum(a - k, 0.0) / max(m, 1e-6))


def soft_limit(s):
    """Saturate log-ratios: identity up to log(knee), then a tanh roll-off asymptotic to log(limit).  Asymmetric --
    brightening an albedo has a physical ceiling, darkening one does not."""
    up = _roll(np.abs(s), LIN_KNEE_UP, LIN_LIMIT_UP)
    dn = _roll(np.abs(s), LIN_KNEE_DN, LIN_LIMIT_DN)
    return np.sign(s) * np.where(s >= 0, up, dn)


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

    # --- raw ratio, two bands, still in DISPLAY space -----------------------------------------------------------
    r10 = np.maximum(gauss(pho, LF_SIGMA), 1.0) / np.maximum(gauss(ren, LF_SIGMA), 4.0)
    r3 = np.maximum(gauss(pho, MF_SIGMA), 1.0) / np.maximum(gauss(ren, MF_SIGMA), 4.0)
    r1 = np.maximum(gauss(pho, HF_SIGMA), 1.0) / np.maximum(gauss(ren, HF_SIGMA), 4.0)
    lf, mf, hf = r10, r3 / r10, r1 / r3
    lf_c = np.clip(lf, LF_LO, LF_HI)
    tex = np.clip(mf, MF_LO, MF_HI) ** MF_K * np.clip(hf, MF_LO, MF_HI) ** HF_K

    x0, y0, x1, y1 = CALIB
    calib = np.zeros((H, W), bool); calib[y0:y1, x0:x1] = True
    calib &= cov
    M = pho[calib].mean(axis=0) / ren[calib].mean(axis=0)   # RGB mean correction over the calibration region
    Mlum = float(0.2126 * M[0] + 0.7152 * M[1] + 0.0722 * M[2])
    M_chroma = M / Mlum                                     # luminance-neutral: the chroma half, goes to the albedo

    # --- ROUND 9b: display -> scene-linear, per pixel, at the pixel's own level --------------------------------
    # The exponent is looked up on the render's LOCAL display luminance (blurred at LF_SIGMA so it is the level of
    # the same neighbourhood the LF ratio was formed over, and so shot noise cannot modulate it).  Only the LF
    # LUMINANCE is raised to it: LFd is neutral over the calibration box by construction but carries residual
    # chroma elsewhere, and an exponent of 3-4 would turn that residual into coloured patches (it is also why the
    # first cut of this clipped the blue channel over 89 % of the band).  The map carries photometry; chroma is
    # the albedo tint's job, and the map's own residual chroma stays at display strength.
    table = transfer_table(out_dir)
    Ld = lum(gauss(ren, LF_SIGMA))
    expo, f_ref, E_other = exponent_field(Ld, table)

    LFd = lf_c / M_chroma[None, None, :]                    # display-space LF after the global chroma is removed
    Llf = np.clip(lum(LFd), 1e-3, None)
    S = np.exp(soft_limit(expo * np.log(Llf)))[..., None] * (LFd / Llf[..., None])   # SCENE-LINEAR now

    # Normalise on the GEOMETRIC mean, not the arithmetic one.  What a box mean does when every pixel's albedo is
    # multiplied by S_p is (to first order) old_mean * exp(mean(log S)) ^ c -- a log-space average -- while
    # mean(S) is biased upward by Jensen (here 1.044 against a true correction of 0.996).  Normalising the
    # arithmetic mean to 1 therefore darkens the box by 4-5 %.  Target = the honest ratio of the two box means,
    # raised to the calibration box's own exponent because the target is a DISPLAY level and S is now linear.
    target = float(lum(pho[calib].mean(axis=0)) / lum(ren[calib].mean(axis=0)))
    exp_calib = float(np.median(expo[calib]))
    target_lin = target ** exp_calib
    S *= target_lin / float(np.exp(np.log(np.clip(lum(S[calib]), 1e-3, None)).mean()))
    S *= tex                                                # the texture band, at its measured display strength

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
    # --- what the map ASKS of QA's boxes, in display per cent, so the phtest can be scored against it -----------
    # NB the map lives in the projector frame (cam01 at z 1.6) and QA's boxes are read in the hero frame (z 1.3);
    # the two differ by 3-4 rows on the wall, which is why these are quoted to 0.1 % and not finer.
    asks = {}
    for nm, bx in (("attic_sunlit", (900, 222, 1020, 256)), ("attic_shaded", (1110, 225, 1150, 260)),
                   ("entablature", (900, 262, 1020, 296))):
        m = np.zeros((H, W), bool); m[bx[1]:bx[3], bx[0]:bx[2]] = True
        m &= inside
        if not m.any():
            continue
        d_pct = 100.0 * (float(np.exp(np.log(np.clip(lum(Sc[m]), 1e-3, None)) / expo[m]).mean()) - 1.0)
        asks[nm] = dict(display_pct_w1=round(d_pct, 2),
                        display_pct_w06=round(100.0 * (float(np.exp(np.log(np.clip(
                            1.0 + 0.6 * (lum(Sc[m]) - 1.0), 1e-3, None)) / expo[m]).mean()) - 1.0), 2),
                        photo_asks_pct=round(100.0 * (float(lum((lf_c / M_chroma[None, None, :])[m]).mean()) - 1.0), 2),
                        linear_ratio=round(float(lum(Sc[m]).mean()), 4),
                        exponent=round(float(np.median(expo[m])), 3),
                        render_lum=round(float(lum(ren[m]).mean()), 1))
    meta = dict(
        ratio=RATIO_PNG, mask=MASK_PNG, res=[W, H],
        projector=dict(loc=[-14.1, 100.0, 1.6], target=[0.0, 0.0, 1.6], lens=20.0, shift_y=0.06,
                       note="the station scripts/arch_uvproj.py baked UVProj from"),
        ref169_xf=list(P.REF169_XF), stack=STACK, band=list(BAND), calib=list(CALIB),
        clip=[RATIO_LO, RATIO_HI], soft_limit=dict(up=[LIN_KNEE_UP, LIN_LIMIT_UP], down=[LIN_KNEE_DN, LIN_LIMIT_DN]), conf=[CONF_IN, CONF_OUT], blur_sigma=BLUR_SIGMA,
        bands=dict(lf=LF_SIGMA, mf=MF_SIGMA, hf=HF_SIGMA, mf_k=MF_K, hf_k=HF_K),
        M_rgb=[round(float(v), 4) for v in M], M_lum=round(Mlum, 4), calib_lum_target=round(target, 4),
        M_chroma=[round(float(v), 4) for v in M_chroma],
        px_in_band=int(inside.sum()),
        mean_conf_in_band=round(float(conf[band > 0.5].mean()), 4),
        clipped_frac=round(float((np.abs(Sc - S).max(axis=-1) > 1e-9)[inside].mean()), 4),
        ratio_lum_p05_p50_p95=[round(float(v), 4) for v in np.percentile(lum(Sc)[inside], [5, 50, 95])],
        render=str(Path(render_path).name),
        # round 9b
        space="scene-linear albedo multiplier (LF band raised to 1/t_eff; MF band left in display space)",
        transfer=dict(file=TRANSFER_JSON, look=table[3]["look"], exposure=table[3]["exposure"],
                      insitu=INSITU, f_ref=round(f_ref, 4), pedestal=round(float(E_other), 5),
                      exp_calib=round(exp_calib, 3),
                      exp_p05_p50_p95=[round(float(v), 3) for v in np.percentile(expo[inside], [5, 50, 95])],
                      target_display=round(target, 4), target_linear=round(target_lin, 4)),
        display_ask_pct=asks,
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
