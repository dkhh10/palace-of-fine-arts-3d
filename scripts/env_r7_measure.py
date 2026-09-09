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

CAM 06 FAR-SHORE GATE - ONE DEFINITION (round 9, agreed with lighting; env r7 read 44.0/23.5 on the same
statistic where LIGHT r13 read 59.8/33.8, and the disagreement was never the statistic):

  frame      cam 06 (`CAM_qa_06_*`), EEVEE, **1280 x 720**, LOD1, as QA renders it.  If the PNG is wider it is a
             QA 3-panel strip and only the FIRST 1280 columns are used (`load(..., 1280)`).
  crop       rows 0-220, columns 0-1280 - `L[0:220, 0:1280]`, the whole top of the frame.  The far-shore LINE
             count uses the narrower `L[0:110, 0:1280]`; the std is always the 220-row crop.
  luminance  Rec. 709 on the 8-bit sRGB values as stored, 0-255, NOT linearised: 0.2126 R + 0.7152 G + 0.0722 B.
  statistic  `numpy.std` (population) of that crop; the mean is reported beside it.
  the pair   the SAME render twice: once with the compositor as shipped, once with `COMP_golden_hour` bypassed.
             Exposure, samples, resolution and geometry must be identical - only the compositor differs.
  THE GATE   **ratio = std(composited) / std(un-composited)**, and it is the ratio, not either absolute number,
             that is compared between rounds.  The absolutes move with the light rig and the geometry (ENV r7 +
             LIGHT r11 gave 44.0 / 23.5 = 0.534; ARCH r5 + ENV r8 + LIGHT r13 measures 38.1 / 59.8 =
             **0.636**, computed by `--c06ratio` on the two committed r13 frames, not transcribed); the ratio is
             what says how much of the geometry's contrast the mist is eating.
             `--c06ratio <composited.png> <uncomposited.png>` computes it and is the ONLY place a ratio for
             this project may come from - a number transcribed from another agent's notes is a stale constant
             the next round cannot check (env r9 review, finding 5).  Runs already made are in
             renders/logs/env_r9_c06ratio.log.
  file       measure the PNG the renderer wrote, not a JPEG re-encode.  Measured: the r7 pair reads std
             44.0 un-composited as PNG and 42.6 as the committed JPEG, i.e. ratio 0.534 vs 0.536.  The ratio is
             stable to 0.002 under JPEG, the absolutes are not - one more reason the gate is the ratio.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "renders/previews/environment/r7_numbers.json"


def lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def load(p, w=None, rgb=False):
    im = Image.open(p).convert("RGB")
    if w and im.width != w:                       # QA sheets are 3-panel strips; take the first panel
        im = im.crop((0, 0, w, im.height))
    a = np.asarray(im, dtype=float)
    return a if rgb else lum(a)


def hue_sat(a):
    """Mean HSV hue (deg) and saturation of an RGB block, hue averaged as a unit vector."""
    mx = a.max(axis=2)
    mn = a.min(axis=2)
    d = np.maximum(mx - mn, 1e-6)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60.0
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    ang = np.radians(h)
    return float(np.degrees(math.atan2(np.sin(ang).mean(), np.cos(ang).mean())) % 360), float(sat.mean())


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
        # QA-04-6's frame-RIGHT (north) wing band, ref 169 raw box 145.9 / dark<60 16.2 % (round-6 table).
        # Added in the round-7 review follow-up: the pin fix changes what stands in this box, so it is measured.
        nband = box_stats(L, (1360, 480, 1860, 600))
        shore = box_stats(L, (700, 600, 1200, 740))
        out[f"{tag}_nband_lum"] = (f"{nband['mean']:.1f}  med {nband['med']:.1f}  std {nband['std']:.1f}  "
                                   f"dark<60 {nband['dark60']:.1f} %  (ref 169 raw box 145.9 / 16.2 %)")
        out[f"{tag}_nband_mean"] = round(nband["mean"], 1)
        out[f"{tag}_band_lum"] = (f"{band['mean']:.1f}  med {band['med']:.1f}  std {band['std']:.1f}  "
                                  f"dark<60 {band['dark60']:.1f} %")
        out[f"{tag}_band_mean"] = round(band["mean"], 1)
        out[f"{tag}_shore_lum"] = (f"{shore['mean']:.1f}  med {shore['med']:.1f}  std {shore['std']:.1f}  "
                                   f"dark<60 {shore['dark60']:.1f} %")
        out[f"{tag}_shore_mean"] = round(shore["mean"], 1)
        A = load(hero, 1920, rgb=True)[600:740, 700:1200]
        hh, ss = hue_sat(A)
        out[f"{tag}_shore_hue"] = f"hue {hh:.1f} (QA window 40-60)   sat {ss:.3f} (ref 0.663)"
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
        # The far field only occupies the TOP of QA's crop - below about row 110 the frame is the exhibition
        # hall's roof and the near canopy - so a radial street that crosses only the top 60 rows is diluted 3.7x
        # in a column profile taken over all 220.  Both numbers are reported; `_c06_n` is the far-field band.
        kf, detf = count_lines(L[0:110, 0:1280])
        out[f"{tag}_c06_lum"] = f"{c.mean():.1f}  std {c.std():.1f}"
        out[f"{tag}_c06_lines"] = f"{kf} in rows 0-110 [{detf}];  {k} over the whole crop [{det}]"
        out[f"{tag}_c06_n"] = kf
    return out


def c06_ratio(comp, nocomp):
    """The agreed cam-06 far-shore gate: std(composited) / std(un-composited) over rows 0-220 of the 1280 frame."""
    out = {}
    Lc, Ln = load(comp, 1280), load(nocomp, 1280)
    for tag, a in (("comp", Lc), ("nocomp", Ln)):
        c = a[0:220, 0:1280]
        k, _det = count_lines(a[0:110, 0:1280])
        out[f"c06_{tag}"] = f"mean {c.mean():.1f}  std {c.std():.1f}  far-shore lines {k}"
    sc, sn = float(Lc[0:220].std()), float(Ln[0:220].std())
    r = sc / max(1e-6, sn)
    out["c06_ratio"] = round(r, 3)
    # Round 9 review, finding 5: this note used to end "LIGHT r13 ships 0.637" whatever it measured - a constant
    # transcribed from docs/lighting_notes.md that would have survived any change to either frame.  It now quotes
    # only what this run measured, and names the two files it measured, so the number can be reproduced.
    out["c06_ratio_note"] = (f"std composited {sc:.1f} / un-composited {sn:.1f} = {r:.3f} over rows 0-220 of the "
                             f"1280-wide cam 06 frame (Rec.709 on 8-bit sRGB, population std); measured from "
                             f"{Path(comp).name} and {Path(nocomp).name}")
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
    if "--c06ratio" in args:
        i = args.index("--c06ratio")
        data.update(c06_ratio(args[i + 1], args[i + 2]))
    else:
        data.update(measure(tag, files.get("hero"), files.get("cam03"), files.get("cam06")))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1))
    for k, v in sorted(data.items()):
        print(f"  {k:16s} {v}")
    print(f"[env_r7_measure] wrote {OUT}")


if __name__ == "__main__":
    main()
