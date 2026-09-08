#!/usr/bin/env python3
"""Build the single gate composite for a QA round (QA / Critic owned; images only).

  python3 scripts/qa_gate_sheet.py --round 02 --out renders/qa_comparisons/round02_gate.png

Layout: Cycles hero next to its golden-hour twin (ref 169) on top, the six Eevee QA views as a strip below,
then the score table with the deltas against the previous round burnt in. Scores live in SCORES below so the
sheet and docs/qa_round_NN.md cannot drift apart.
"""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf",
         "/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf"]

ROWS = ["Silhouette match", "Proportion", "Ornament fidelity", "Material realism", "Edge wear",
        "Lighting mood", "Water reflection", "Repetition visibility", "Scale cues"]
CAMS = ["01 hero", "02 NE 3/4", "03 colonnade", "04 ceiling", "05 S lawn", "06 aerial"]

# round 01 -> round 02, per row per camera. None = not scored (n/a).
R01 = {
    "Silhouette match":      [3, 1, 1.5, 4, 1.5, 3],
    "Proportion":            [3, 3, 3.5, 4, 3.5, 3.5],
    "Ornament fidelity":     [3, 3, 3, 2.5, 2.5, 3],
    "Material realism":      [1, 1, 1, 1, 1, 1],
    "Edge wear":             [0, 0, 0, 0, 0, 0],
    "Lighting mood":         [3.5, 3, 3, 1, 3, 2.5],
    "Water reflection":      [1, None, 1, None, 1, 1.5],
    "Repetition visibility": [2, 3, 2, 3, 2, 2],
    "Scale cues":            [3, 2, 3, 3, 2.5, 3],
}
R02 = {
    "Silhouette match":      [4, 2, 1.5, 3.5, 2, 4],
    "Proportion":            [3.5, 3, 3, 3.5, 3, 3.5],
    "Ornament fidelity":     [3, 2.5, 2.5, 1.5, 2, 2.5],
    "Material realism":      [2.5, 2, 2, 2, 2, 1.5],
    "Edge wear":             [1, 1, 1, 0.5, 1, 0.5],
    "Lighting mood":         [3.5, 2.5, 2, 3, 3, 2],
    "Water reflection":      [3, 2, None, None, 2, 1.5],
    "Repetition visibility": [2.5, 2, 2, 2, 2, 2],
    "Scale cues":            [3.5, 2, 1.5, 2.5, 2, 2],
}
# round 03 (2026-09-07, first polish round: all five owners' p4r1 merged, cam03/cam05 re-stationed, Eevee at LOD1)
R03 = {
    "Silhouette match":      [4, 2, 2.5, 3.5, 3, 4],
    "Proportion":            [4, 3, 3, 3.5, 3, 3.5],
    "Ornament fidelity":     [3, 2.5, 2.5, 1.5, 3, 2.5],
    "Material realism":      [3, 2.5, 1.5, 1.5, 2.5, 1.5],
    "Edge wear":             [1.5, 1, 0.5, 0.5, 1.5, 0.5],
    "Lighting mood":         [4, 3, 2.5, 2, 3.5, 2],
    "Water reflection":      [3.5, 2.5, None, None, 2.5, 1.5],
    "Repetition visibility": [3, 2, 2, 2, 2.5, 2],
    "Scale cues":            [3.5, 2.5, 2.5, 2.5, 2.5, 2],
}
# round 04 (2026-09-08, polish round 2: lighting r09/r10, arch p4r2 + sockets, materials r4/r5, env r4/r5, ornament r4;
# cam02 re-stationed on land by QA's probe; Eevee at LOD1)
R04 = {
    "Silhouette match":      [4, 3.5, 2.5, 3.5, 3.5, 4],
    "Proportion":            [4, 3.5, 3, 3.5, 3, 3.5],
    "Ornament fidelity":     [3.5, 3, 2.5, 3, 3, 2.5],
    "Material realism":      [3, 2.5, 1.5, 1.5, 2.5, 2],
    "Edge wear":             [1.5, 1, 0.5, 0.5, 1.5, 0.5],
    "Lighting mood":         [4, 3, 1.5, 2, 3.5, 2.5],
    "Water reflection":      [3.5, 2, None, None, 2.5, 2],
    "Repetition visibility": [3, 2.5, 2, 2.5, 2.5, 2],
    "Scale cues":            [3, 3, 2.5, 3, 2.5, 2.5],
}
SCORES = {"01": R01, "02": R02, "03": R03, "04": R04}
VERDICT = {
    "02": "Gate: NOT passed. Target is >= 4 on every row, hero average >= 4.5. "
          "Blockers: dome reads absent from cam05, edge wear absent, camera 03 framing, haze.",
    "03": "Gate: NOT passed. Target is >= 4 on every row, hero average >= 4.5. "
          "Blockers: hero stone still clean CAD at 1:1, chroma 6 deg cool (R-B 92 vs 138), "
          "interior fills 2x, watchdog kills GPU renders.",
    "04": "Gate: NOT passed. Target is >= 4 on every row, hero average >= 4.5. "
          "Attic chroma and flutes landed; blockers: Eevee ceiling black (coffer/sky 0.04), cam03 foreground crushed "
          "(shaft 0.10 of ref), stone still streak-free and uniform (std 55 % of photo), bare shoreline.",
}


def font(size, bold=True):
    for f in FONTS:
        if Path(f).exists():
            try:
                return ImageFont.truetype(f, size)
            except Exception:
                pass
    return ImageFont.load_default()


def fit(img, w, h=None):
    if h is None:
        h = int(img.height * w / img.width)
    return img.resize((w, h), Image.LANCZOS)


def averages(tbl):
    out = []
    for i in range(6):
        vals = [tbl[r][i] for r in ROWS if tbl[r][i] is not None]
        out.append(sum(vals) / len(vals))
    return out


def build(rnd, out):
    prev_rnd = f"{int(rnd) - 1:02d}"
    W = 1920
    prev = ROOT / "renders" / "previews" / "qa"
    hero = Image.open(prev / f"round{rnd}_01_lagoon_hero_cycles.png").convert("RGB")
    ref = Image.open(ROOT / "reference/photos/raw/ref_169_main_Palace_of_Fine_Arts_16794p.jpg").convert("RGB")
    eevee = [Image.open(prev / f"round{rnd}_{n}.png").convert("RGB") for n in
             ["01_lagoon_hero", "02_lagoon_ne_threequarter", "03_colonnade_walk",
              "04_rotunda_ceiling", "05_south_lawn", "06_aerial"]]

    hero_s, ref_s = fit(hero, 950), fit(ref, 950)
    top_h = max(hero_s.height, ref_s.height)
    strip_h = 180
    table_h = 60 + (len(ROWS) + 2) * 40 + 20
    H = 44 + top_h + 30 + strip_h + 26 + table_h

    sheet = Image.new("RGB", (W, H), (18, 18, 20))
    d = ImageDraw.Draw(sheet)
    f_title, f_lab, f_cell = font(30), font(20), font(22)

    d.text((20, 10), f"Palace of Fine Arts - QA round {rnd} gate (round {prev_rnd} -> {rnd}).  "
                     f"Cycles hero 1920x1080 128 spp vs ref 169 (golden-hour twin).", font=f_title, fill=(240, 240, 235))
    y = 44
    sheet.paste(hero_s, (10, y)); sheet.paste(ref_s, (960, y))
    d.text((16, y + 6), "RENDER  round %s  Cycles" % rnd, font=f_lab, fill=(255, 220, 120))
    d.text((966, y + 6), "PHOTO  ref 169", font=f_lab, fill=(140, 230, 255))
    y += top_h + 30

    tw = W // 6
    for i, im in enumerate(eevee):
        t = fit(im, tw - 4, strip_h - 4)
        sheet.paste(t, (i * tw + 2, y + 2))
        d.text((i * tw + 8, y + 6), f"cam {CAMS[i]}", font=f_lab, fill=(255, 220, 120))
    y += strip_h + 26

    T1, T2 = SCORES[prev_rnd], SCORES[rnd]
    a1, a2 = averages(T1), averages(T2)
    col0, colw = 20, 300
    d.text((col0, y), "row", font=f_cell, fill=(200, 200, 200))
    for i, c in enumerate(CAMS):
        d.text((col0 + colw + i * 265, y), c, font=f_cell, fill=(200, 200, 200))
    y += 40
    for r in ROWS:
        d.text((col0, y), r, font=f_cell, fill=(225, 225, 225))
        for i in range(6):
            v1, v2 = T1[r][i], T2[r][i]
            if v2 is None:
                txt, col = "n/a", (120, 120, 120)
            else:
                dv = None if v1 is None else v2 - v1
                txt = f"{v1 if v1 is not None else '-'} -> {v2}" + (f"  {dv:+.1f}" if dv else "")
                col = (140, 235, 140) if dv and dv > 0 else ((255, 140, 140) if dv and dv < 0 else (215, 215, 215))
            d.text((col0 + colw + i * 265, y), txt, font=f_cell, fill=col)
        y += 40
    d.line([(col0, y + 4), (W - 20, y + 4)], fill=(90, 90, 90))
    y += 14
    d.text((col0, y), "average", font=f_cell, fill=(255, 255, 255))
    for i in range(6):
        dv = a2[i] - a1[i]
        col = (140, 235, 140) if dv > 0 else (255, 140, 140)
        d.text((col0 + colw + i * 265, y), f"{a1[i]:.2f} -> {a2[i]:.2f}  {dv:+.2f}", font=f_cell, fill=col)
    y += 44
    d.text((col0, y), VERDICT.get(rnd, "Gate: NOT passed."), font=f_cell, fill=(255, 180, 120))

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print("wrote", out, sheet.size)
    for i, c in enumerate(CAMS):
        print(f"  cam {c:14s} {a1[i]:.2f} -> {a2[i]:.2f}  ({a2[i]-a1[i]:+.2f})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", default="02")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    build(a.round, a.out or ROOT / "renders" / "qa_comparisons" / f"round{a.round}_gate.png")
