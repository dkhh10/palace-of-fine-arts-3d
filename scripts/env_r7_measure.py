"""Round-7 image measurements for the four QA-05 environment defects.  Pure Pillow/numpy, no Blender.

    python3 scripts/env_r7_measure.py --before <hero> <cam03> <cam06> --after <hero> <cam03> <cam06> --tag b|a

Writes/merges renders/previews/environment/r7_numbers.json, which scripts/env_sheet_r7.py burns onto the sheet.
Definitions are fixed here so BEFORE and AFTER are measured identically:

  band / shore lum   mean Rec.709 luminance over QA's own box.
  cam03 ground       the walk strip actually visible between the near columns, box 560 480 900 720 of the
                     1280x720 frame (the full-width row band is 70 % black column silhouette and reads std 12.9
                     where QA reads 15.7); `sunlit` is the mean of the frame's brightest decile, so
                     "ground / sunlit" is a contrast ratio that does not move with the exposure.
  cam06 street lines Column and row mean profiles of the crop 0 0 1280 220.  A "line" is a local minimum of a
                     profile that sits >= 15 luminance under the local background (the median of the profile
                     within +-70 samples, i.e. the roofs around it) and is at least 4 samples wide; minima closer
                     than 25 samples are one line.  Counted on both axes, reported as (vertical + horizontal).
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "renders/previews/environment/r7_numbers.json"


def lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def load(p, w=None):
    im = Image.open(p).convert("RGB")
    if w and im.width != w:                       # QA sheets are 3-panel strips; take the first panel
        im = im.crop((0, 0, w, im.height))
    return lum(np.asarray(im, dtype=float))


def box_stats(L, box):
    x0, y0, x1, y1 = box
    b = L[y0:y1, x0:x1]
    return dict(mean=float(b.mean()), med=float(np.median(b)), std=float(b.std()),
                dark60=float(100 * (b < 60).mean()))


def count_lines(crop, drop=15.0, win=70, minw=4, sep=25):
    total, detail = 0, []
    for axis, name in ((0, "vert"), (1, "horiz")):
        prof = crop.mean(axis=axis)
        n = len(prof)
        bg = np.array([np.median(prof[max(0, i - win):min(n, i + win + 1)]) for i in range(n)])
        below = (bg - prof) >= drop
        runs, i = [], 0
        while i < n:
            if below[i]:
                j = i
                while j < n and below[j]:
                    j += 1
                if j - i >= minw:
                    runs.append((i, j, float((bg[i:j] - prof[i:j]).max())))
                i = j
            else:
                i += 1
        merged = []
        for r in runs:
            if merged and r[0] - merged[-1][1] < sep:
                merged[-1] = (merged[-1][0], r[1], max(merged[-1][2], r[2]))
            else:
                merged.append(r)
        total += len(merged)
        detail.append(f"{name} {len(merged)}" + (" (" + ", ".join(f"{a}-{b} -{d:.0f}" for a, b, d in merged) + ")"
                                                 if merged else ""))
    return total, "; ".join(detail)


def measure(tag, hero, cam03, cam06):
    out = {}
    if hero and Path(hero).exists():
        L = load(hero, 1920)
        band = box_stats(L, (60, 480, 560, 600))
        shore = box_stats(L, (700, 600, 1200, 740))
        out[f"{tag}_band_lum"] = (f"{band['mean']:.1f}  med {band['med']:.1f}  std {band['std']:.1f}  "
                                  f"dark<60 {band['dark60']:.1f} %")
        out[f"{tag}_band_mean"] = round(band["mean"], 1)
        out[f"{tag}_shore_lum"] = (f"{shore['mean']:.1f}  med {shore['med']:.1f}  std {shore['std']:.1f}  "
                                   f"dark<60 {shore['dark60']:.1f} %")
        out[f"{tag}_shore_mean"] = round(shore["mean"], 1)
    if cam03 and Path(cam03).exists():
        L = load(cam03, 1280)
        g = L[480:720, 560:900]
        wide = L[470:720, :]
        sunlit = float(L[L >= np.percentile(L, 90)].mean())
        out[f"{tag}_c03_std"] = f"{g.std():.1f}  (full-width row band {wide.std():.1f})"
        out[f"{tag}_c03_stdn"] = round(float(g.std()), 1)
        out[f"{tag}_c03_ratio"] = f"{g.mean() / max(1e-6, sunlit):.3f}  (ground {g.mean():.1f} / sunlit {sunlit:.1f})"
    if cam06 and Path(cam06).exists():
        L = load(cam06, 1280)
        c = L[0:220, 0:1280]
        k, det = count_lines(c)
        out[f"{tag}_c06_lum"] = f"{c.mean():.1f}  std {c.std():.1f}"
        out[f"{tag}_c06_lines"] = f"{k}  [{det}]"
        out[f"{tag}_c06_n"] = k
    return out


def main():
    args = sys.argv[1:]
    tag = "b"
    files = {}
    i = 0
    while i < len(args):
        if args[i] == "--tag":
            tag = args[i + 1]
            i += 2
        elif args[i] in ("--hero", "--cam03", "--cam06"):
            files[args[i][2:]] = args[i + 1]
            i += 2
        else:
            i += 1
    data = json.loads(OUT.read_text()) if OUT.exists() else {}
    data.update(measure(tag, files.get("hero"), files.get("cam03"), files.get("cam06")))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1))
    for k, v in sorted(data.items()):
        print(f"  {k:16s} {v}")
    print(f"[env_r7_measure] wrote {OUT}")


if __name__ == "__main__":
    main()
