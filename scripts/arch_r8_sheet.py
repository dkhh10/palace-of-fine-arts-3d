"""ARCH r8 composite: v1 hero arch tile (the defect) vs the r8 cam01 arch, plus cam02 and cam03.

    python3 scripts/arch_r8_sheet.py

PIL only. The panels are the same world region at each camera's own resolution, scaled to a 960 px wide sheet;
the 100 % tiles next to it (renders/previews/arch/r8_cam0*_tile*.png) are what the defect judgement is made on.
"""
import os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.environ.get("PFA_MAIN_ROOT", "/Users/dk/Projects/3d render blender 3rd attempt building")  # r8 review fix
W = 960
panels = []


def add(path, box, label):
    if not os.path.exists(path):
        print("missing", path)
        return
    im = Image.open(path).convert("RGB")
    panels.append((im.crop(box) if box else im, label))


add(os.path.join(MAIN, "renders/final/v1/hero_cam01_3840x2160.png"), (1560, 560, 2460, 1260),
    "BEFORE  v1 4K hero, arch tile: the opening closed by chord triangles")
add(os.path.join(ROOT, "renders/previews/arch/r8_cam01.png"), (780, 280, 1230, 630),
    "AFTER   r8 cam01 1920x1080 64 spp: coffered barrel, inner arch, sky behind")
add(os.path.join(ROOT, "renders/previews/arch/r8_cam02.png"), None, "r8 cam02 1280x720 64 spp (bay 07)")
add(os.path.join(ROOT, "renders/previews/arch/r8_cam03.png"), None, "r8 cam03 1280x720 64 spp (near column 028)")

cells = []
for im, label in panels:
    im = im.resize((W, round(im.height * W / im.width)), Image.LANCZOS)
    strip = Image.new("RGB", (W, im.height + 22), (16, 16, 16))
    strip.paste(im, (0, 22))
    ImageDraw.Draw(strip).text((8, 6), label, fill=(235, 235, 235))
    cells.append(strip)

sheet = Image.new("RGB", (W, sum(c.height for c in cells)), (16, 16, 16))
y = 0
for c in cells:
    sheet.paste(c, (0, y))
    y += c.height
out = os.path.join(ROOT, "renders/qa_comparisons/arch_r8_vault_fix.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
sheet.save(out)
print("wrote", out, sheet.size)
