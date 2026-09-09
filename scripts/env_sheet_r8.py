"""Round-8 comparison sheet: the A/A2 cluster's position in the hero frame, before / after / ref 169.

One row of three panels over the same frame span (cam 01 x 0.55-1.00, y 0.28-0.72), with the frame-x ruler drawn
on all three so the dark mass can be read off directly, plus a numbers panel.  BEFORE is ENV r7c, AFTER is this
worktree's rebuilt master, REFERENCE is ref 169 carried through the round-02 align transform.

    python3 scripts/env_sheet_r8.py            # after renders/previews/environment/r8_hero.png exists
"""
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = Path(__file__).resolve().parent.parent
MAIN = Path(os.environ.get("PFA_MAIN_ROOT", "/Users/dk/Projects/3d render blender 3rd attempt building"))
PREV = ROOT / "renders/previews/environment"
REF169 = MAIN / "reference/photos/raw/ref_169_main_Palace_of_Fine_Arts_16794p.jpg"
OUT = ROOT / "renders/qa_comparisons/env_r8_sheet.png"

# cam-01 render px -> raw ref-169 px (round-02 align transform, as in env_sheet_r6.ref_box)
S, DX, SY, DY = 0.7640, 223.2, 0.7667, 97.0
FX0, FX1, FY0, FY1 = 0.55, 1.00, 0.28, 0.72
W, H = 1920, 1080
PW = 1180                                   # panel width
TICKS = (0.60, 0.65, 0.708, 0.740, 0.80, 0.85, 0.90, 0.95)
RED = (0.708, 0.740)                        # QA-04-6's box edge and ref 169's mass right edge


def font(size, bold=True):
    for p in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else
              "/System/Library/Fonts/Supplemental/Arial.ttf",
              "/System/Library/Fonts/Helvetica.ttc"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                pass
    return ImageFont.load_default()


F_T, F_N = font(24), font(17, bold=False)


def panel(path, ref=False):
    if not Path(path).exists():
        im = Image.new("RGB", (PW, 420), (34, 30, 30))
        ImageDraw.Draw(im).text((10, 10), f"missing: {path}", font=F_N, fill=(230, 120, 120))
        return im
    im = Image.open(path).convert("RGB")
    if ref:
        box = (int(FX0 * W * S + DX), int(FY0 * H * SY + DY), int(FX1 * W * S + DX), int(FY1 * H * SY + DY))
    else:
        box = (int(FX0 * W), int(FY0 * H), int(FX1 * W), int(FY1 * H))
    im = im.crop(box)
    return im.resize((PW, max(1, int(round(PW * im.height / im.width)))), Image.LANCZOS)


def main():
    panels = [
        ("BEFORE  ENV r7c hero (Cycles 128 spp)", PREV / "r7c_hero.jpg", False),
        ("AFTER  ENV r8 hero, this worktree's master", PREV / "r8_hero.png", False),
        ("REFERENCE  ref 169, round-02 align transform", REF169, True),
    ]
    imgs = [(t, panel(p, r)) for t, p, r in panels]
    ph = imgs[0][1].height
    numbers = json.loads((PREV / "r8_numbers.json").read_text()) if (PREV / "r8_numbers.json").exists() else {}
    lines = numbers.get("_lines", ["(no numbers file)"])
    nh = 34 + 24 * len(lines)
    out = Image.new("RGB", (PW, (ph + 40) * len(imgs) + nh + 12), (18, 18, 22))
    d = ImageDraw.Draw(out)
    for i, (title, im) in enumerate(imgs):
        y = i * (ph + 40)
        out.paste(im, (0, y + 38))
        for fx in TICKS:
            px = int((fx - FX0) / (FX1 - FX0) * PW)
            col = (255, 80, 80) if fx in RED else (110, 190, 255)
            d.line([(px, y + 38), (px, y + 38 + im.height)], fill=col, width=2)
            d.text((px + 4, y + 42 + im.height - 24), f"{fx:.3f}", font=F_N, fill=col)
        d.text((8, 8 + y), title, font=F_T, fill=(255, 214, 120))
    y = len(imgs) * (ph + 40)
    d.text((8, y + 4), "QA-04-6 north-wing band, cam 01 1360 480 1860 600 (frame x 0.708-0.969)",
           font=F_T, fill=(255, 214, 120))
    for i, ln in enumerate(lines):
        d.text((8, y + 34 + i * 24), ln, font=F_N, fill=(228, 228, 228))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.save(OUT)
    print(f"[env_sheet_r8] {out.width}x{out.height} -> {OUT}")


if __name__ == "__main__":
    main()
