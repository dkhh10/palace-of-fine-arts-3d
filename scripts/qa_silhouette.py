#!/usr/bin/env python3
"""Silhouette measurement + scaled overlay for QA (python3 + numpy + PIL, no Blender).

  python3 scripts/qa_silhouette.py measure IMG --crop x0 y0 x1 y1
      -> prints apex_y, corner_top_y, attic x-extent (W_a px), visible dome rise / W_a, and writes IMG_profile.png
  python3 scripts/qa_silhouette.py align RENDER --crop ... --ref PHOTO --ref-crop ... --out OUT.png
      -> scales/translates the photo so its attic width and corner-top row match the render's, then writes
         render | aligned photo | 50% blend (+ both profiles: render red, photo cyan). Use this, not the letterboxed
         qa_compare blend, when checking "edges align within ~2% of frame height".

The "building" mask (round 02+) is "not sky and not foliage": sky = bluish and bright (b >= r - 0.01, b > 0.30),
foliage = clearly green. --mask warm restores the round-01 rule (r > b + 0.06), which loses the pale cream dome cap. The profile is the first building row per column inside the crop. corner_top = median profile height over the
outer 12% of the building's width (the attic corner blocks + their urns), apex = min over the central 30%.
"""
import sys, argparse, json
import numpy as np
from PIL import Image, ImageDraw


def load(path):
    return np.asarray(Image.open(path).convert("RGB")).astype(np.float32) / 255.0


MASK_MODE = "sky"


def building_mask(img, mode=None):
    """Building = not sky, not foliage.

    mode "warm" (round 01): warm pixels only (r > b + 0.06). This UNDER-REPORTS the apex once the dome carries the
    pale cream MAT_dome_membrane, because a sky-lit cream cap has r - b < 0.06 (QA round 02 finding; the architecture
    agent measured ~3 m of apex lost). Kept for reproducing round-01 numbers.
    mode "sky" (default from round 02): sky = bluish AND bright (b >= r - 0.01 and b > 0.30); foliage = clearly green.
    Anything else that is not near-black is building. Verified against the geometric silhouette from
    scripts/arch_silhouette.py flatten / arch_inspect.py --alpha.
    """
    mode = mode or MASK_MODE
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    if mode == "warm":
        return (r > b + 0.06) & (r >= g - 0.01)
    sky = (b >= r - 0.01) & (b > 0.30)
    foliage = (g > r + 0.03) & (g > b + 0.03)
    return (~sky) & (~foliage) & (r + g + b > 0.06)


def profile(mask, x0, y0, x1, y1, run=3):
    """first row (absolute y) with `run` consecutive building pixels, per column in [x0,x1)."""
    prof = np.full(x1 - x0, -1, dtype=int)
    sub = mask[y0:y1, x0:x1]
    for i in range(sub.shape[1]):
        col = sub[:, i]
        c = 0
        for j, v in enumerate(col):
            c = c + 1 if v else 0
            if c >= run:
                prof[i] = y0 + j - run + 1
                break
    return prof


def measure(img, crop):
    x0, y0, x1, y1 = crop
    m = building_mask(img)
    prof = profile(m, x0, y0, x1, y1)
    valid = np.where(prof >= 0)[0]
    if len(valid) < 20:
        raise SystemExit("no building found in crop")
    lx, rx = valid[0], valid[-1]
    w = rx - lx
    cen = prof[lx + int(0.35 * w): lx + int(0.65 * w)]
    apex = int(cen[cen >= 0].min())
    edge = np.concatenate([prof[lx: lx + int(0.12 * w)], prof[rx - int(0.12 * w): rx + 1]])
    corner_top = int(np.median(edge[edge >= 0]))
    # attic width: building extent on the row corner_top + 6% of the crop height (inside the corner blocks)
    row = min(y1 - 1, corner_top + max(4, int(0.06 * (y1 - y0))))
    cols = np.where(m[row, x0:x1])[0]
    wa_l, wa_r = x0 + cols[0], x0 + cols[-1]
    wa = wa_r - wa_l
    res = dict(apex_y=apex, corner_top_y=corner_top, wa_row=row, wa_left=int(wa_l), wa_right=int(wa_r), wa_px=int(wa),
               centre_x=float((wa_l + wa_r) / 2), rise_px=corner_top - apex, rise_over_wa=round((corner_top - apex) / wa, 3),
               profile_left_x=int(x0 + lx), profile_right_x=int(x0 + rx))
    return res, prof, (x0, y0, x1, y1)


def draw_profile(path, img, prof, crop, res, out, color=(255, 0, 0)):
    im = Image.fromarray((img * 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = crop
    d.rectangle([x0, y0, x1, y1], outline=(255, 255, 0))
    for i, y in enumerate(prof):
        if y >= 0:
            d.point((x0 + i, y), fill=color)
    d.line([(x0, res["apex_y"]), (x1, res["apex_y"])], fill=(0, 255, 0))
    d.line([(x0, res["corner_top_y"]), (x1, res["corner_top_y"])], fill=(0, 255, 255))
    d.line([(res["wa_left"], res["wa_row"]), (res["wa_right"], res["wa_row"])], fill=(255, 0, 255), width=2)
    im.save(out)


def align(render_path, rcrop, ref_path, refcrop, out):
    R = load(render_path); P = load(ref_path)
    rres, rprof, _ = measure(R, rcrop)
    pres, pprof, _ = measure(P, refcrop)
    s = rres["wa_px"] / pres["wa_px"]
    H, W = R.shape[:2]
    pim = Image.fromarray((P * 255).astype(np.uint8))
    pim = pim.resize((int(round(pim.width * s)), int(round(pim.height * s))), Image.LANCZOS)
    dx = rres["centre_x"] - pres["centre_x"] * s
    dy = rres["corner_top_y"] - pres["corner_top_y"] * s
    canvas = Image.new("RGB", (W, H), (0, 0, 0))
    canvas.paste(pim, (int(round(dx)), int(round(dy))))
    rim = Image.fromarray((R * 255).astype(np.uint8))
    blend = Image.blend(rim, canvas, 0.5)
    d = ImageDraw.Draw(blend)
    x0 = rcrop[0]
    for i, y in enumerate(rprof):
        if y >= 0:
            d.point((x0 + i, y), fill=(255, 0, 0))
    px0 = refcrop[0]
    for i, y in enumerate(pprof):
        if y >= 0:
            d.point((int(round((px0 + i) * s + dx)), int(round(y * s + dy))), fill=(0, 255, 255))
    for y in (rres["apex_y"], rres["corner_top_y"]):
        d.line([(0, y), (W, y)], fill=(255, 0, 0))
    d.line([(0, pres["apex_y"] * s + dy), (W, pres["apex_y"] * s + dy)], fill=(0, 255, 255))
    sheet = Image.new("RGB", (W * 3, H))
    sheet.paste(rim, (0, 0)); sheet.paste(canvas, (W, 0)); sheet.paste(blend, (2 * W, 0))
    sheet.save(out)
    info = dict(render=rres, ref=pres, scale=round(s, 4), dx=round(dx, 1), dy=round(dy, 1),
                apex_delta_px=round(rres["apex_y"] - (pres["apex_y"] * s + dy), 1),
                apex_delta_frac_height=round((rres["apex_y"] - (pres["apex_y"] * s + dy)) / H, 4))
    print(json.dumps(info, indent=1))
    print("wrote", out)
    return info


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["measure", "align"])
    ap.add_argument("image")
    ap.add_argument("--crop", type=int, nargs=4, required=True)
    ap.add_argument("--ref"); ap.add_argument("--ref-crop", type=int, nargs=4); ap.add_argument("--out")
    ap.add_argument("--mask", choices=["sky", "warm"], default="sky",
                    help="silhouette mask: 'sky' (default, round 02+) or 'warm' (round 01 behaviour)")
    a = ap.parse_args()
    MASK_MODE = a.mask
    globals()["MASK_MODE"] = a.mask
    if a.mode == "measure":
        img = load(a.image)
        res, prof, crop = measure(img, a.crop)
        print(json.dumps(res))
        out = a.out or a.image.rsplit(".", 1)[0] + "_profile.png"
        draw_profile(a.image, img, prof, crop, res, out)
        print("wrote", out)
    else:
        align(a.image, a.crop, a.ref, a.ref_crop, a.out)
