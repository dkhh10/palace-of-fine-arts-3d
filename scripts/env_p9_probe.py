#!/usr/bin/env python3
"""Phase 9 ENV / 8d R3 measurement probe.  No Blender, no Chrome.

Re-uses QA round 22's own definitions for the backdrop bands (`qa_r22_probe._bd` and `qa_r22_probe.BACKDROP`),
so luma / sat / hf / luma-sd are the numbers 8d was judged on and nothing is redefined here.

Columns:
  before   renders/previews/environment/p9r3_before_cam<NN>.png   (master with main's environment/materials)
  after    renders/previews/environment/p9r3_after_cam<NN>.png    (same master, this branch's assets)
  cyc_p9   renders/qa_comparisons/cycles_p9/cam<NN>_1080_32spp.png (the Phase 9 Cycles reference)
  photo    ref 169 registered to cam01 by env_r8_fit.REF_XF (stations 1) / ref 105 (station 6)

    python3 scripts/env_p9_probe.py               # table
    python3 scripts/env_p9_probe.py --sheet       # table + renders/qa_comparisons/env_p9_r3_sheet.jpg
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_r22_probe as P22  # noqa: E402

P = P22.P
ROOT = Path(__file__).resolve().parents[1]
MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
PREV = ROOT / "renders/previews/environment"
OUT = ROOT / "renders/qa_comparisons"
CYC = "renders/qa_comparisons/cycles_p9/cam{:02d}_1080_32spp.png"


def frame(tag, st):
    if tag == "cyc_p9":
        for base in (ROOT, MAIN):
            p = base / CYC.format(st)
            if p.exists():
                return P.rgb(str(p))
        return None
    p = PREV / f"p9r3_{tag}_cam{st:02d}.png"
    return P.rgb(str(p)) if p.exists() else None


def photo_box(st, box):
    """ref 169 for station 1 (registered), ref 105 for station 6 (its own frame)."""
    if st == 1:
        p169 = P22.REF169 if P22.REF169.exists() else MAIN / "reference/photos/raw" / P22.REF169.name
        im = np.asarray(Image.open(str(p169)).convert("RGB"))
        sx, dx, sy, dy = P22.REF_XF
        x0, y0, x1, y1 = box
        return P22._bd(im, (int(x0 * sx + dx), int(y0 * sy + dy), int(x1 * sx + dx), int(y1 * sy + dy)))
    if st == 6:
        p = P22.REF105 if P22.REF105.exists() else MAIN / "reference/photos/raw" / P22.REF105.name
        im = np.asarray(Image.open(str(p)).convert("RGB"))
        h, w = im.shape[:2]
        x0, y0, x1, y1 = box
        r = (int(x0 / 1920 * w), int(y0 / 1080 * h), int(x1 / 1920 * w), int(y1 / 1080 * h))
        return P22._bd(im, r)
    return None


def table():
    cache = {}
    print(f"{'box':24s} {'st':>2s} {'frame':8s} {'luma':>7s} {'sat':>7s} {'hf':>7s} {'lum sd':>7s}")
    rows = []
    for name, st, box, why in P22.BACKDROP:
        first = True
        vals = {}
        for tag in ("before", "after", "cyc_p9"):
            key = (tag, st)
            if key not in cache:
                cache[key] = frame(tag, st)
            im = cache[key]
            if im is None:
                continue
            b = P22._bd(im, box)
            vals[tag] = b
            print(f"{name if first else '':24s} {st if first else '':>2} {tag:8s} "
                  f"{b['lum']:7.3f} {b['sat']:7.3f} {b['hf']:7.4f} {b['sd']:7.3f}")
            first = False
        ph = photo_box(st, box)
        if ph:
            vals["photo"] = ph
            print(f"{'':24s} {'':>2} {'photo':8s} {ph['lum']:7.3f} {ph['sat']:7.3f} "
                  f"{ph['hf']:7.4f} {ph['sd']:7.3f}")
        if "before" in vals and "after" in vals:
            d = {k: vals["after"][k] - vals["before"][k] for k in ("lum", "sat", "hf", "sd")}
            print(f"{'':24s} {'':>2} {'DELTA':8s} {d['lum']:+7.3f} {d['sat']:+7.3f} "
                  f"{d['hf']:+7.4f} {d['sd']:+7.3f}   ({why})")
        rows.append((name, st, box, vals))
    return rows


def sheet(rows):
    """One 960 px composite: the three stations before / after, plus the hero band at 100 %."""
    panels = []
    for st in (1, 5, 6):
        for tag in ("before", "after"):
            p = PREV / f"p9r3_{tag}_cam{st:02d}.png"
            if p.exists():
                im = Image.open(p).convert("RGB").resize((470, 264), Image.LANCZOS)
                panels.append((f"cam{st:02d} {tag}", im))
    # the hero band at 100 % (the 8d target box), before / after, side by side
    crops = []
    for tag in ("before", "after"):
        p = PREV / f"p9r3_{tag}_cam01.png"
        if p.exists():
            crops.append(Image.open(p).convert("RGB").crop((0, 524, 640, 670)))
    sh_h = 264 * ((len(panels) + 1) // 2) + (150 if crops else 0)
    out = Image.new("RGB", (960, sh_h + 10), (18, 18, 18))
    for i, (_lbl, im) in enumerate(panels):
        out.paste(im, ((i % 2) * 480 + 5, (i // 2) * 264 + 5))
    for i, c in enumerate(crops):
        out.paste(c.resize((470, 107), Image.LANCZOS), (i * 480 + 5, 264 * ((len(panels) + 1) // 2) + 10))
    OUT.mkdir(parents=True, exist_ok=True)
    fp = OUT / "env_p9_r3_sheet.jpg"
    out.save(fp, quality=88)
    print(f"[env_p9_probe] {fp}")
    return fp


if __name__ == "__main__":
    rows = table()
    if "--sheet" in sys.argv:
        sheet(rows)


# ------------------------------------------------------------------------------- item 2: the belt
# The QA-24 residuals are stated viewer-vs-Cycles (`docs/qa_round_24.md` items 2 and 4).  The brief's question is
# a different one: is the belt's cover in BLENDER under the PHOTOGRAPH's?  Station 1 is the only station with a
# photo registration (`env_r8_fit.REF_XF`), so it is the only place the question can be answered with a number.
BELT_BOXES = [
    ("01 belt N (r2c1)", 1, (0, 500, 640, 680)),
    ("01 belt S", 1, (1280, 500, 1900, 680)),
    ("02 belt band R", 2, (960, 600, 1920, 850)),
    ("05 belt band", 5, (0, 620, 1920, 800)),
]
P8DIR = "renders/qa_comparisons/cycles_p8/cam{:02d}_1080_32spp.png"


def belt():
    print(f"== item 2: the belt bands in Cycles, p8 -> p9, against the photograph where one is registered ==")
    print(f"{'box':20s} {'st':>2s} {'frame':8s} {'luma':>7s} {'sat':>7s} {'hf':>7s} {'lum sd':>7s} {'dark%':>7s}")
    for name, st, box in BELT_BOXES:
        first = True
        for lbl in ("cyc_p8", "cyc_p9", "photo"):
            if lbl == "photo":
                b = photo_box(st, box)
            else:
                path = (P8DIR if lbl == "cyc_p8" else CYC).format(st)
                im = None
                for base in (ROOT, MAIN):
                    if (base / path).exists():
                        im = P.rgb(str(base / path))
                        break
                b = P22._bd(im, box) if im is not None else None
            if b is None:
                continue
            x0, y0, x1, y1 = box
            src = (photo_src(st, box) if lbl == "photo" else P.rgb(str((ROOT if (ROOT / (P8DIR if lbl == "cyc_p8" else CYC).format(st)).exists() else MAIN) / (P8DIR if lbl == "cyc_p8" else CYC).format(st)))[y0:y1, x0:x1])
            lum = (src.astype(np.float32) / 255.0) @ P.LUMA
            dark = float((lum < 0.20).mean()) * 100.0
            print(f"{name if first else '':20s} {st if first else '':>2} {lbl:8s} {b['lum']:7.3f} "
                  f"{b['sat']:7.3f} {b['hf']:7.4f} {b['sd']:7.3f} {dark:6.2f}%")
            first = False


def photo_src(st, box):
    if st == 1:
        p169 = P22.REF169 if P22.REF169.exists() else MAIN / "reference/photos/raw" / P22.REF169.name
        im = np.asarray(Image.open(str(p169)).convert("RGB"))
        sx, dx, sy, dy = P22.REF_XF
        x0, y0, x1, y1 = box
        return im[int(y0 * sy + dy):int(y1 * sy + dy), int(x0 * sx + dx):int(x1 * sx + dx)]
    return None
