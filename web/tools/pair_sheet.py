#!/usr/bin/env python3
"""Gate 0 acceptance sheet and measurements: Cycles reference vs the three.js viewer.

  python3 web/tools/pair_sheet.py --cycles renders/web/gate0_cycles_cam01.png \
      --viewer renders/web/gate0_viewer_cam01.png --out renders/web/gate0_pair.png \
      --column-roi x0,y0,x1,y1 [--capital-roi x0,y0,x1,y1]

Builds  Cycles | viewer | 50 % blend  over  100 % crops of the column and the capital from both
frames, and prints (also writes <out>.json):
  - the column's pixel bounding box in each frame, from a silhouette mask inside the ROI, and the
    disagreement as a percentage of frame height (gate: <= 1 %);
  - mean luminance of the sunlit column face, the shaded column face and the sky box
    (x 0-300, rows 0-100) in each frame, as 0-255 Rec.709 luma of the display pixels and as the
    linear value after sRGB decoding (the frames are display-referred: Cycles through AgX High
    Contrast, the viewer through the LUT baked from it).
Uses only PIL + numpy (system python3).
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float64)


def srgb_to_linear(x):
    x = x / 255.0
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def load(p, size=None):
    im = Image.open(p).convert("RGB")
    if size and im.size != size:
        raise SystemExit(f"{p}: {im.size} != {size}; both frames must share the render size")
    return im


def stats(arr, box):
    """box = (x0, y0, x1, y1) inclusive-exclusive; returns display luma 0-255 and linear luminance."""
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    x0, y0 = max(0, x0), max(0, y0)
    patch = arr[y0:y1, x0:x1, :].astype(np.float64)
    if patch.size == 0:
        return dict(box=[x0, y0, x1, y1], n=0, luma=None, linear=None)
    return dict(box=[x0, y0, x1, y1], n=int(patch.shape[0] * patch.shape[1]),
                luma=float((patch @ LUMA).mean()),
                linear=float((srgb_to_linear(patch) @ LUMA).mean()),
                rgb=[float(patch[..., i].mean()) for i in range(3)])


def column_mask(arr, roi):
    """Stone/column silhouette inside the ROI: warm (R > B) and not sky (sky is blue-dominant),
    not grass (grass is green-dominant).  Returns the mask and its bbox in image coordinates."""
    x0, y0, x1, y1 = [int(v) for v in roi]
    sub = arr[y0:y1, x0:x1, :].astype(np.int16)
    r, g, b = sub[..., 0], sub[..., 1], sub[..., 2]
    warm = (r - b) > 12
    not_grass = (g - r) < 8
    bright = (sub.mean(axis=2) > 12)
    m = warm & not_grass & bright
    if m.sum() < 50:
        return m, None
    cols = np.where(m.sum(axis=0) > 0.15 * m.shape[0])[0]
    rows = np.where(m.sum(axis=1) > 0.10 * m.shape[1])[0]
    if len(cols) == 0 or len(rows) == 0:
        ys, xs = np.nonzero(m)
        return m, [x0 + xs.min(), y0 + ys.min(), x0 + xs.max(), y0 + ys.max()]
    return m, [x0 + int(cols.min()), y0 + int(rows.min()), x0 + int(cols.max()), y0 + int(rows.max())]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycles", required=True)
    ap.add_argument("--viewer", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--column-roi", required=True, help="x0,y0,x1,y1 around ONE column")
    ap.add_argument("--capital-roi", default=None)
    ap.add_argument("--sun-side", default="left", choices=["left", "right"],
                    help="which half of the column the sun lights")
    args = ap.parse_args()

    a = load(args.cycles)
    b = load(args.viewer, a.size)
    W, H = a.size
    A, B = np.asarray(a), np.asarray(b)
    roi = [float(v) for v in args.column_roi.split(",")]
    res = {"frames": {"cycles": args.cycles, "viewer": args.viewer}, "size": [W, H], "column_roi": roi}

    # --- column bounding box ------------------------------------------------------------------
    _, bbA = column_mask(A, roi)
    _, bbB = column_mask(B, roi)
    res["column_bbox"] = {"cycles": bbA, "viewer": bbB}
    if bbA and bbB:
        d = [abs(u - v) for u, v in zip(bbA, bbB)]
        res["column_bbox_delta_px"] = d
        res["column_bbox_delta_pct_height"] = [round(100.0 * v / H, 3) for v in d]
        res["column_bbox_gate_1pct"] = max(d) <= 0.01 * H

    # --- luminance boxes ----------------------------------------------------------------------
    boxes = {"sky": (0, 0, 300, 100)}
    if bbA and bbB:
        bb = [(p + q) / 2 for p, q in zip(bbA, bbB)]
        x0, y0, x1, y1 = bb
        w, h = x1 - x0, y1 - y0
        mid = x0 + w / 2
        lit = (x0 + 0.12 * w, y0 + 0.30 * h, mid - 0.06 * w, y0 + 0.75 * h)
        sha = (mid + 0.06 * w, y0 + 0.30 * h, x1 - 0.12 * w, y0 + 0.75 * h)
        if args.sun_side == "right":
            lit, sha = sha, lit
        boxes["column_sunlit"] = lit
        boxes["column_shaded"] = sha
    res["boxes"] = {k: [round(v, 1) for v in bx] for k, bx in boxes.items()}
    res["luminance"] = {k: {"cycles": stats(A, bx), "viewer": stats(B, bx)} for k, bx in boxes.items()}
    for k, v in res["luminance"].items():
        c, w_ = v["cycles"], v["viewer"]
        if c["luma"] is not None and w_["luma"] is not None:
            v["delta_luma"] = round(w_["luma"] - c["luma"], 2)
            v["ratio_linear"] = round(w_["linear"] / c["linear"], 4) if c["linear"] else None

    # --- sheet --------------------------------------------------------------------------------
    blend = Image.blend(a, b, 0.5)
    pad, label = 8, 26
    top = Image.new("RGB", (W * 3 + pad * 4, H + label + pad * 2), (18, 18, 20))
    for i, (im, name) in enumerate([(a, "Cycles 64 spp"), (b, "three.js viewer"), (blend, "50 % blend")]):
        top.paste(im, (pad + i * (W + pad), label + pad))
        ImageDraw.Draw(top).text((pad + i * (W + pad) + 4, pad), name, fill=(230, 226, 216))

    crops, crop_labels = [], []
    for name, r in [("column", roi), ("capital", [float(v) for v in args.capital_roi.split(",")] if args.capital_roi else None)]:
        if r is None:
            continue
        box = tuple(int(v) for v in r)
        crops += [a.crop(box), b.crop(box)]
        crop_labels += [f"{name[:3]} cyc", f"{name[:3]} view"]
    sheet = top
    if crops:
        ch = max(c.height for c in crops) + label + pad
        cw = sum(c.width + pad for c in crops) + pad
        row = Image.new("RGB", (max(cw, top.width), ch), (18, 18, 20))
        x = pad
        for c, t in zip(crops, crop_labels):
            row.paste(c, (x, label))
            ImageDraw.Draw(row).text((x + 2, 4), t, fill=(230, 226, 216))
            x += max(c.width, 60) + pad
        sheet = Image.new("RGB", (max(top.width, row.width), top.height + row.height), (18, 18, 20))
        sheet.paste(top, (0, 0)); sheet.paste(row, (0, top.height))

    # draw the measurement boxes on the blend panel for the record
    d = ImageDraw.Draw(sheet)
    ox = pad + 2 * (W + pad)
    for k, bx in boxes.items():
        x0, y0, x1, y1 = [int(v) for v in bx]
        d.rectangle([ox + x0, label + pad + y0, ox + x1, label + pad + y1], outline=(255, 90, 90))
        d.text((ox + x0 + 2, label + pad + y0 - 12), k, fill=(255, 90, 90))
    if bbA:
        d.rectangle([pad + bbA[0], label + pad + bbA[1], pad + bbA[2], label + pad + bbA[3]], outline=(90, 200, 255))
    if bbB:
        d.rectangle([pad + W + pad + bbB[0], label + pad + bbB[1], pad + W + pad + bbB[2], label + pad + bbB[3]], outline=(90, 200, 255))

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)
    Path(args.out + ".json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    print(f"[pair_sheet] wrote {args.out} ({sheet.width}x{sheet.height})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
