#!/usr/bin/env python3
"""QA round 18 gate sheet — renders/web/gate5_gate.png (960 px, desktop and mobile rows).

Row 1-2: the six desktop stations from the staging URL (`gate5_cam0N.png`, tiers=all).
Row 3:   the same six stations on `?tier=mobile` (`gate5m_cam0N.png`) — the mobile fallback as it
         renders on the deployed URL.
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "renders" / "web"
W = 960
TW, TH = 320, 180          # desktop thumbs, 3 per row
MW, MH = 160, 346          # mobile thumbs, 6 per row
BAR = 16

NAMES = ["01 lagoon hero", "02 lagoon NE", "03 colonnade walk",
         "04 rotunda ceiling", "05 south lawn", "06 aerial"]


def main():
    h = BAR + TH * 2 + BAR + MH + BAR
    sheet = Image.new("RGB", (W, h), (18, 18, 18))
    d = ImageDraw.Draw(sheet)
    d.text((6, 4), "QA 18 / Gate 5 — staging URL, desktop tiers=all (rows 1-2) — 1920x1080, "
                   "parity with round16c: luma 0.998-1.002x, 0 boxes > 3 %",
           fill=(235, 235, 235))
    for i in range(6):
        im = Image.open(WEB / f"gate5_cam{i + 1:02d}.png").convert("RGB").resize((TW, TH), Image.LANCZOS)
        x, y = (i % 3) * TW, BAR + (i // 3) * TH
        sheet.paste(im, (x, y))
        d.text((x + 4, y + 4), NAMES[i], fill=(255, 255, 160))
    y0 = BAR + TH * 2
    d.text((6, y0 + 3), "?tier=mobile on the SAME URL — 4 tier-0 group glbs 404: no building, "
                        "no ornament, no ground at any station (49 draws, 548 tris)",
           fill=(255, 170, 170))
    for i in range(6):
        im = Image.open(WEB / f"gate5m_cam{i + 1:02d}.png").convert("RGB").resize((MW, MH), Image.LANCZOS)
        sheet.paste(im, (i * MW, y0 + BAR))
        d.text((i * MW + 4, y0 + BAR + 4), NAMES[i][:2], fill=(255, 255, 160))
    d.text((6, h - 13), "payload before the first frame: desktop 46.81 MB (target 50) in 8.11 s; "
                        "mobile 23.88 MB but incomplete; 0 files over 25 MiB",
           fill=(200, 200, 200))
    out = WEB / "gate5_gate.png"
    sheet.save(out)
    print(out, sheet.size)


if __name__ == "__main__":
    main()
