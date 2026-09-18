#!/usr/bin/env python3
"""QA round 18b gate sheet — renders/web/gate5b_gate.png (960 px; the MOBILE row is the point).

Row 1: the six `?tier=mobile` stations on the redeployed URL (`gate5cm_cam0N.png`) — the whole scene
       now draws (142-180 calls, 1.5-1.9 M tris, resident 499.7 MB).
Row 2: the pre-fix capture (`gate5bm_cam01.png`, the 832x1801 canvas in a 1170x2532 page) beside the
       fixed one, and the waterline evidence: mobile (no reflection) beside desktop (reflection).
Row 3: the six desktop stations (`gate5b_cam0N.png`), pixel-identical to round 18's gate5.
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "renders" / "web"
W = 960
MW, MH = 160, 346          # mobile thumbs, 6 per row
TW, TH = 320, 180          # desktop thumbs, 3 per row
EW, EH = 240, 200          # evidence strip
BAR = 16

NAMES = ["01 lagoon hero", "02 lagoon NE", "03 colonnade walk",
         "04 rotunda ceiling", "05 south lawn", "06 aerial"]


def main():
    h = BAR + MH + BAR + EH + BAR + TH * 2 + BAR
    sheet = Image.new("RGB", (W, h), (18, 18, 18))
    d = ImageDraw.Draw(sheet)

    d.text((6, 4), "QA 18b / Gate 5 fix round — ?tier=mobile on the redeployed URL (gate5c): all 7 "
                   "m_*.glb serve 200, 142-180 draws, 1.5-1.9 M tris, resident 499.7 MB",
           fill=(180, 255, 180))
    for i in range(6):
        im = Image.open(WEB / f"gate5cm_cam{i + 1:02d}.png").convert("RGB")
        sheet.paste(im.resize((MW, MH), Image.LANCZOS), (i * MW, BAR))
        d.text((i * MW + 4, BAR + 4), NAMES[i][:2], fill=(255, 255, 160))

    y0 = BAR + MH + BAR
    d.text((6, y0 - 13), "found and fixed inside the round: the mobile canvas (left, gate5bm) filled "
                         "832x1801 of the 1170x2532 page  |  residual: no reflection on mobile water",
           fill=(255, 210, 150))
    pre = Image.open(WEB / "gate5bm_cam01.png").convert("RGB")
    post = Image.open(WEB / "gate5cm_cam01.png").convert("RGB")
    sheet.paste(pre.resize((int(EH * 1170 / 2532), EH), Image.LANCZOS), (0, y0))
    sheet.paste(post.resize((int(EH * 1170 / 2532), EH), Image.LANCZOS), (100, y0))
    mob = Image.open(WEB / "gate5cm_cam01.png").convert("RGB").crop((0, 1320, 1170, 1620))
    des = Image.open(WEB / "gate5b_cam01.png").convert("RGB").crop((375, 560, 1545, 860))
    sheet.paste(mob.resize((EW * 2, EH // 2), Image.LANCZOS), (200 + 40, y0))
    sheet.paste(des.resize((EW * 2, EH // 2), Image.LANCZOS), (200 + 40, y0 + EH // 2))
    d.text((244, y0 + 14), "mobile lagoon: no reflection", fill=(255, 170, 170))
    d.text((244, y0 + EH // 2 + 4), "desktop lagoon: reflection + ripples", fill=(180, 255, 180))

    y1 = y0 + EH + BAR
    d.text((6, y1 - 13), "desktop, same URL after the fix (gate5b): MAE vs round-18 gate5 <= 0.001/255 "
                         "at every station, resident 1 861.3 MB, 46.81 MB before the first frame",
           fill=(235, 235, 235))
    for i in range(6):
        im = Image.open(WEB / f"gate5b_cam{i + 1:02d}.png").convert("RGB").resize((TW, TH), Image.LANCZOS)
        x, y = (i % 3) * TW, y1 + (i // 3) * TH
        sheet.paste(im, (x, y))
        d.text((x + 4, y + 4), NAMES[i], fill=(255, 255, 160))

    d.text((6, h - 13), "payload before the first frame on the URL: desktop 46 808 904 B, mobile "
                        "46 738 628 B; 0 page errors, 0 404s but /favicon.ico, 0 files over 25 MiB",
           fill=(200, 200, 200))
    out = WEB / "gate5b_gate.png"
    sheet.save(out)
    print(out, sheet.size)


if __name__ == "__main__":
    main()
