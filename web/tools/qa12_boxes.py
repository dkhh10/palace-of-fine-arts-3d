#!/usr/bin/env python3
"""The QA-12-1 acceptance boxes, measured the way docs/qa_round_12.md states them.

    python3 web/tools/qa12_boxes.py viewer.png [--ref reference.png] [--at 1280x720]
                                    [--box "x0 y0 x1 y1[:label]" ...]

Every frame is resampled to `--at` (the reference's native size, 1280x720, as the QA report says:
"both at the reference's native 1280x720") and the metrics are computed on Rec.709 luma 0-255:

  std          standard deviation inside the box
  mid(5-21)    band-pass amplitude: std of gaussian(sigma=5/2) - gaussian(sigma=21/2), the energy
               between a 5 px and a 21 px feature
  hp9          high-pass amplitude: std of image - gaussian(sigma=9/2)

The definitions are calibrated against the report's own numbers for the Phase 5 cam05 frame
(pier face 1180 560 1280 680: mid 10.11, std 38.25); run with --ref to print both sides and the
ratio, which is what an acceptance claim needs.
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
from PIL import Image

LUMA = np.array([0.2126, 0.7152, 0.0722])


def gaussian(img, sigma):
    """Separable gaussian blur with reflect padding, no scipy dependency."""
    if sigma <= 0:
        return img.copy()
    r = max(1, int(round(3.0 * sigma)))
    x = np.arange(-r, r + 1, dtype=np.float64)
    k = np.exp(-0.5 * (x / sigma) ** 2)
    k /= k.sum()
    out = np.pad(img, ((0, 0), (r, r)), mode="reflect")
    out = np.apply_along_axis(lambda m: np.convolve(m, k, mode="valid"), 1, out)
    out = np.pad(out, ((r, r), (0, 0)), mode="reflect")
    out = np.apply_along_axis(lambda m: np.convolve(m, k, mode="valid"), 0, out)
    return out


def load_luma(path, size):
    im = Image.open(path).convert("RGB")
    if im.size != size:
        im = im.resize(size, Image.LANCZOS)
    return np.asarray(im).astype(np.float64) @ LUMA


def metrics(luma, box):
    x0, y0, x1, y1 = box
    mid_full = gaussian(luma, 5 / 2.0) - gaussian(luma, 21 / 2.0)
    hp_full = luma - gaussian(luma, 9 / 2.0)
    crop = luma[y0:y1, x0:x1]
    return {
        "mean": round(float(crop.mean()), 2),
        "std": round(float(crop.std()), 2),
        "mid_5_21": round(float(mid_full[y0:y1, x0:x1].std()), 2),
        "hp9": round(float(hp_full[y0:y1, x0:x1].std()), 2),
        "px": [int(x1 - x0), int(y1 - y0)],
    }


def parse_box(spec):
    label = None
    if ":" in spec:
        spec, label = spec.split(":", 1)
    v = [int(round(float(t))) for t in spec.replace(",", " ").split()]
    if len(v) != 4:
        raise SystemExit(f"box needs 4 numbers: {spec!r}")
    return tuple(v), (label or "box")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("viewer")
    ap.add_argument("--ref", default=None)
    ap.add_argument("--at", default="1280x720", help="size both frames are resampled to")
    ap.add_argument("--box", action="append", required=True,
                    help='"x0 y0 x1 y1[:label]" in the --at coordinate system, repeatable')
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    w, h = (int(t) for t in a.at.split("x"))
    v = load_luma(a.viewer, (w, h))
    r = load_luma(a.ref, (w, h)) if a.ref else None
    rows = []
    for spec in a.box:
        box, label = parse_box(spec)
        row = {"label": label, "box": list(box), "viewer": metrics(v, box)}
        if r is not None:
            row["reference"] = metrics(r, box)
            row["ratio"] = {k: (round(row["viewer"][k] / row["reference"][k], 3)
                                if isinstance(row["reference"][k], float) and row["reference"][k] else None)
                            for k in ("mean", "std", "mid_5_21", "hp9")}
        rows.append(row)
        vm = row["viewer"]
        line = f'{label:<22} {str(box):<26} viewer mid {vm["mid_5_21"]:6.2f}  std {vm["std"]:6.2f}  hp9 {vm["hp9"]:6.2f}  mean {vm["mean"]:6.2f}'
        if r is not None:
            rm = row["reference"]
            line += f' | ref mid {rm["mid_5_21"]:6.2f}  std {rm["std"]:6.2f}  hp9 {rm["hp9"]:6.2f}  mean {rm["mean"]:6.2f}'
        print(line)
    if a.json:
        Path(a.json).write_text(json.dumps({"at": [w, h], "viewer": a.viewer, "reference": a.ref, "rows": rows}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
