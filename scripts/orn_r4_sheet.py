"""Assemble renders/previews/ornament/orn4_sheet.png: before / after / reference for the three round-4 defects.

    python3 scripts/orn_r4_sheet.py

Rows: capital (QA-03-15), rosette (QA-03-8 ornament half), keystone (carried depth defect).
Each row: hero 1:1 crop before | hero 1:1 crop after | look-dev before | look-dev after | reference photo.
Hero crops are nearest-neighbour upscaled x6 so the pixels QA judges are visible; a caption strip carries the
tri counts, the measured relief and the hero-scale tier statistics from scripts/orn_tier_stats.py.
Pure python3 + PIL - no Blender.
"""
import subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "renders" / "previews" / "ornament"
REF = Path("/Users/dk/Projects/3d render blender 3rd attempt building/reference/photos/ornament_crops")

ROWS = [
    ("capital", "corinthian_capital_1.jpg", "QA-03-15  ORN_capital_rotunda",
     "LOD0 100k -> 64k, LOD1 20k -> 16k tris. Kalathos necked 1.30 R -> 1.155 R at the top, 0.865 R at the waist; "
     "leaves lofted on a bell-hugging spine, tips curl out+down through 90-100 deg; leaf tips 0.29 -> 0.40 m proud "
     "of the bell; bell scalloped 0.078 R with the 0.064 m groove BETWEEN the leaves (phase fixed in review). "
     "Cavity FLOAT_COLOR vertex attribute 'cavity' on LOD0/LOD1, 1 = open."),
    ("rosette", "coffered_ceiling_1.jpg", "QA-03-8 (ornament half)  ORN_rosette_ceiling",
     "LOD0 20k -> 26k tris. Was a lathe with a cos(12t) radius wobble (no undercut anywhere). Now a sunk back disc, "
     "8+8 modelled petals whose tips lift 0.082 m off the disc, a 0.045 m annular groove and a beaded boss. "
     "Relief 0.14 -> 0.21 m on a 0.60 m rosette (0.35 of the diameter); delivered mesh depth 0.197-0.225 m, "
     "inside ARCH's 0.55 m saucer coffers."),
    ("keystone", "keystone_mask_1.jpg", "carried defect  ORN_keystone",
     "LOD0 50k tris (unchanged). New tapered voussoir standing 0.30 m proud of the archivolt face plus a 0.075 m "
     "moulded cap (back plane now exactly y = 0); mask nose 0.63-0.68 m proud (was 0.50). Brow overhangs the eyes; "
     "eye 0.03 -> 0.072 m, "
     "mouth 0.09 -> 0.115 m, nostrils added; mane 14 thin -> 10 bold leaves. 3 variants (was 2)."),
]
HERO_ZOOM = 6
CELL_H = 340
PAD = 10
BG = (18, 18, 20)
FG = (235, 235, 230)


def font(sz):
    for p in ("/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Supplemental/Arial.ttf"):
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


def tier(path, box=None):
    cmd = [sys.executable, str(ROOT / "scripts" / "orn_tier_stats.py"), str(path), "--min-contrast", "0.05"]
    if box:
        cmd += ["--box"] + [str(v) for v in box]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    rel = alt = "-"
    for ln in out.splitlines():
        if "relative std" in ln:
            rel = ln.split("relative std")[1].strip()
        if "readable alternations" in ln:
            alt = ln.split(":")[-1].strip()
    return rel, alt


def fit(im, h):
    return im.resize((max(1, int(im.width * h / im.height)), h), Image.LANCZOS)


def main():
    f_t, f_s, f_c = font(21), font(15), font(13)
    tiles = []
    for key, ref, title, caption in ROWS:
        row = []
        for tag in ("before", "after"):
            p = D / f"r4_{tag}_hero_{key}.png"
            im = Image.open(p).convert("RGB")
            im = im.resize((im.width * HERO_ZOOM, im.height * HERO_ZOOM), Image.NEAREST)
            rel, alt = tier(p)
            row.append((fit(im, CELL_H), f"{tag} - hero 1:1 x{HERO_ZOOM}   rel-std {rel}  alternations {alt}"))
        for tag in ("before", "after"):
            im = Image.open(D / f"r4_{tag}_close_{key}.png").convert("RGB")
            row.append((fit(im, CELL_H), f"{tag} - look-dev, real sun az 118.5 el 7.4"))
        rp = REF / ref
        row.append((fit(Image.open(rp).convert("RGB"), CELL_H), f"reference {ref}"))
        tiles.append((title, caption, row))

    width = max(sum(im.width for im, _ in row) + PAD * (len(row) + 1) for _, _, row in tiles)
    row_h = CELL_H + 30 + 46 + PAD
    H = 54 + row_h * len(tiles)
    sheet = Image.new("RGB", (width, H), BG)
    d = ImageDraw.Draw(sheet)
    d.text((PAD, 14), "Palace of Fine Arts - ORNAMENT round 4: capitals (QA-03-15), coffer rosettes (QA-03-8), "
                      "keystone depth.  Cycles 48 spp, lighting rig r09, one stone for ornament and stand-in wall.",
           fill=FG, font=f_t)
    y = 54
    for title, caption, row in tiles:
        d.text((PAD, y), title, fill=(255, 205, 120), font=f_s)
        x = PAD
        for im, cap in row:
            sheet.paste(im, (x, y + 22))
            d.text((x + 2, y + 22 + CELL_H + 2), cap, fill=(190, 190, 185), font=f_c)
            x += im.width + PAD
        # wrap the caption to the sheet width
        words, line, lines = caption.split(), "", []
        for wd in words:
            t = (line + " " + wd).strip()
            if d.textlength(t, font=f_c) > width - 2 * PAD:
                lines.append(line)
                line = wd
            else:
                line = t
        lines.append(line)
        for i, ln in enumerate(lines[:2]):
            d.text((PAD, y + 22 + CELL_H + 20 + i * 15), ln, fill=(160, 190, 210), font=f_c)
        y += row_h
    out = D / "orn4_sheet.png"
    sheet.save(out)
    print(f"wrote {out}  {sheet.size}")


main()
