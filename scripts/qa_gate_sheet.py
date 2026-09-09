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
R05 = {
    "Silhouette match":      [4, 3.5, 2.5, 3.5, 3.5, 4],
    "Proportion":            [4, 3.5, 3, 3.5, 3, 3.5],
    "Ornament fidelity":     [3.5, 3, 2, 3, 3, 2.5],
    "Material realism":      [3, 2.5, 1, 2, 2.5, 2],
    "Edge wear":             [2, 1.5, 0.5, 1, 1.5, 0.5],
    "Lighting mood":         [3.5, 3, 1, 2, 3.5, 3],
    "Water reflection":      [3, 2.5, None, None, 2.5, 2],
    "Repetition visibility": [3, 2.5, 2, 2.5, 2.5, 2.5],
    "Scale cues":            [3.5, 3, 2, 3, 3, 2.5],
}
R06 = {
    # round 06 (2026-09-09, polish round 4: ARCH r4 cornice/dentils, LIGHT r12+r13 diffuse sky + Eevee shade fill,
    # MAT r7, ENV r7+r8 + paving). Hero Proportion is RE-SCORED 4 -> 3.5 on the first per-course stack measurement
    # (docs/qa_round_06.md section (g)); the geometry did not change this round. Hero average holding Proportion at
    # 4 would be 3.28 (flat), with the re-score 3.22.
    "Silhouette match":      [4, 3.5, 2.5, 3.5, 3.5, 4],
    "Proportion":            [3.5, 3.5, 3, 3.5, 3, 3.5],
    "Ornament fidelity":     [3.5, 3, 2.5, 3, 3, 2.5],
    "Material realism":      [3, 2.5, 1.5, 2.5, 3, 1.5],
    "Edge wear":             [2.5, 2, 1, 1, 2, 0.5],
    "Lighting mood":         [4, 3, 2, 3, 3.5, 2],
    "Water reflection":      [2, 1.5, None, None, 1.5, 1.5],
    "Repetition visibility": [3, 2.5, 2, 2.5, 2.5, 2.5],
    "Scale cues":            [3.5, 3, 2.5, 3, 3, 2.5],
}
R07 = {
    # round 07 (2026-09-09, polish round 5: ARCH r6 stack registration + r7 archivolt sockets, ORN r6+r7 capitals 3.0 m /
    # rinceau / attic panels, LIGHT r14 sky-tint discriminators, MAT r8 water + coffer albedo, ENV r9 gallery width).
    # The photo-projection pass did NOT ship this round (MAT r8 was re-scoped to water; decisions.md budget plan).
    "Silhouette match":      [4, 3.5, 2.5, 3.5, 3.5, 4],
    "Proportion":            [4, 3.5, 3, 3.5, 3.5, 3.5],
    "Ornament fidelity":     [4, 3.5, 2.5, 3, 3.5, 2.5],
    "Material realism":      [3, 3, 2, 3.5, 3, 2.5],
    "Edge wear":             [3, 2.5, 1, 1, 2, 0.5],
    "Lighting mood":         [4, 3.5, 2.5, 3, 3.5, 2.5],
    "Water reflection":      [2.5, 2.5, None, None, 2.5, 2],
    "Repetition visibility": [3, 2.5, 2, 2.5, 2.5, 2.5],
    "Scale cues":            [3.5, 3, 2.5, 3, 3, 2.5],
}
R08 = {
    # round 08 (2026-09-09, polish round 6: the PHOTO-PROJECTION pass MAT r9 + r9b, LIGHT r15 lagoon horizon /
    # shade fill, ORN r8 capital presets + bake, and the lead's new stations: cam01 down 0.30 m to z 1.3 (2.6 m
    # over the water) and cam02 re-stationed to the ref-062 NNE fit at 40 mm.  cam02's drop is the new station
    # (the dome is clipped out of frame and the near face is in violet shade), not a loss in the model.
    "Silhouette match":      [4, 2.5, 2.5, 3.5, 3.5, 4],
    "Proportion":            [4, 3.5, 3, 3.5, 3.5, 3.5],
    "Ornament fidelity":     [4, 4, 3, 3, 3.5, 2.5],
    "Material realism":      [3.5, 2, 2.5, 3, 3.5, 2.5],
    "Edge wear":             [3.5, 2.5, 1.5, 1, 2, 0.5],
    "Lighting mood":         [4.5, 2, 3.5, 3, 3.5, 3],
    "Water reflection":      [3, None, None, None, 2.5, 2.5],
    "Repetition visibility": [3, 2.5, 2, 2.5, 2.5, 2.5],
    "Scale cues":            [3.5, 2.5, 2.5, 3, 3, 3],
}
R09 = {
    # round 09 (2026-09-10, the LAST polish round): cam02 lens 40 -> 27 mm (QA-08-1) and LIGHT r16 (sun-side diffuse
    # tint b 40 -> 70, cam03 knob, flythrough back to 1224 frames).  Nothing from materials / ornament / environment.
    # cam01 geometry is bit-identical to round 08 (same edge rows); its only change is chroma, mean |d| 1.24 lum
    # concentrated in blue (2.73).  cam03 / 04 / 05 moved by 0.09-0.20 lum mean = below the scoring resolution.
    "Silhouette match":      [4, 3.5, 2.5, 3.5, 3.5, 4],
    "Proportion":            [4, 3.5, 3, 3.5, 3.5, 3.5],
    "Ornament fidelity":     [4, 4, 3, 3, 3.5, 2.5],
    "Material realism":      [3.5, 2, 2.5, 3, 3.5, 2.5],
    "Edge wear":             [3.5, 2.5, 1.5, 1, 2, 0.5],
    "Lighting mood":         [4.5, 2.5, 3.5, 3, 3.5, 3],
    "Water reflection":      [3, None, None, None, 2.5, 2.5],
    "Repetition visibility": [3, 2.5, 2, 2.5, 2.5, 2.5],
    "Scale cues":            [3.5, 3, 2.5, 3, 3, 3],
}
SCORES = {"01": R01, "02": R02, "03": R03, "04": R04, "05": R05, "06": R06, "07": R07, "08": R08, "09": R09}
VERDICT = {
    "09": "Gate: NOT passed. Hero 3.67 -> 3.67 (+0.00): the sun-side tint moved the sunlit attic box sat 0.462 -> 0.487 (window 0.53-0.62) but took the whole building from 1.01x to 1.10x the photograph's saturation. cam02 +0.25: the 27 mm lens closes QA-08-1 (top-band sky 0.2 % -> 91.8 %, ref 91 %); its face is still violet in CYCLES on all four boxes (hue 234-268). cam03/04/05/06 flat within 0.2 lum. First flat round of the definition-of-done clock: 1 of 2.",
    "02": "Gate: NOT passed. Target is >= 4 on every row, hero average >= 4.5. "
          "Blockers: dome reads absent from cam05, edge wear absent, camera 03 framing, haze.",
    "03": "Gate: NOT passed. Target is >= 4 on every row, hero average >= 4.5. "
          "Blockers: hero stone still clean CAD at 1:1, chroma 6 deg cool (R-B 92 vs 138), "
          "interior fills 2x, watchdog kills GPU renders.",
    "04": "Gate: NOT passed. Target is >= 4 on every row, hero average >= 4.5. "
          "Attic chroma and flutes landed; blockers: Eevee ceiling black (coffer/sky 0.04), cam03 foreground crushed "
          "(shaft 0.10 of ref), stone still streak-free and uniform (std 55 % of photo), bare shoreline.",
    "05": "Gate: NOT passed. Target is >= 4 on every row, hero average >= 4.5. Hero 3.28 for the third round. "
          "Shoreline, columns, cam05 apex, Eevee vault (0.04 -> 0.16) landed; blockers: cam03 shade crushed (shaft 0.06 of "
          "the sunlit stone, ref 0.61), hero stone now a dark isotropic blotch (attic lum 0.88 of ref, streak anisotropy "
          "0.64 vs photo 4.07), Cycles coffers 0.21 with black floors (claimed 0.39), water reflection grey (sat 0.11).",
    "06": "Gate: NOT passed. Target is >= 4 on every row, hero average >= 4.5. Hero 3.22 (3.28 holding Proportion at 4): no gain for a fourth round. Landed: hero shade colour (shaded attic 30.7 deg / sat 0.373 vs ref 29.5 / 0.425), Cycles coffers 0.21 -> 0.451 (ref 0.437), cornice/dentil shadow (row std 20.9 -> 36.5), cam03 shade 0.06 -> 0.15 old box / 0.38 on the sky-visible box, cam05 stone std 0.92 of ref. Blockers: the diffuse sky tint floods cam06 and the water blue-violet (roofs hue 37 -> 253, cam05 lagoon sat 0.31 -> 0.12), hero reflection sat 0.043 (ref 0.358), stone streak anisotropy 0.41 vs 4.07, and the hero stack does not register course by course (+0.07 m to +2.31 m).",
    "07": "Gate: NOT passed (target >= 4 every row, hero average >= 4.5). Hero 3.44, +0.22 - the first hero gain in five rounds, and every camera gained. Landed: the hero stack registers course by course (all 8 courses within 5 rows / 0.37 m, attic storey 100 vs 101 rows, capital 35 vs 30), capitals read (alternation 20 maxima vs the photo's 17 at 0.95 of its contrast), attic run-off 19.2 % = the photo's 19.2 %, streak anisotropy 0.41 -> 3.12 (ref 4.08), entablature row std 44.0 (test 40), reflection R-B +2.5 -> +36.4 at hue 36.5, coffer sat 0.91 -> 0.47 (ref 0.43), the violet flood gone (cam06 plaza 269 -> 33, trees 240 -> 33), cam03 black 46.1 -> 28.0 %, Eevee pass 218.6 -> 146.1 s. Open blockers: sunlit stone chroma (attic sat 0.437 vs 0.581, R-B 99 vs 133), the open lagoon (flank 1.24x too bright at hue 224 vs 200, near water 228 vs 190), the hero mirror at 0.64 of the photo's luminance, and cam03 still 28 % black with the lagoon-side row at 0.097 of sunlit. The photo-projection pass did not ship this round; its precondition (a registered stack) is now met.",
    "08": "Gate: NOT passed (target >= 4 every row, hero average >= 4.5). Hero 3.44 -> 3.67, +0.22 - a second consecutive hero gain, and the first round after the photo-projection pass, so the two-round <+0.1 clock is armed with 0 flat rounds on it. Landed: the projection registers with NO resolvable seam on cam02/cam05 (largest coherent step 4.5-13.6 lum/row against the projector frame's own 22.4, i.e. every step is a real moulding), sunlit attic sat 0.437 -> 0.462 and R-B 99 -> 105, shaded attic 134.0 -> 127.8 (window top 126.5) with its chroma now on the photo (sat 0.432 vs 0.454), the open lagoon closed (flank 189.5 -> 162.8 at hue 224 -> 210 vs the photo's 154.0 / 200.5; ripples R-B -47.6 -> -22.5 vs -17.0), reflection 105.6 -> 116.3, cam03 black 28.0 -> 12.6 % with the lagoon-side row 0.097 -> 0.166 (test 0.15), cam06 far-shore lines 0 -> 3 (test 3) at ratio 0.633, capital alternation 25 maxima vs the photo's 22 at 0.97 of its contrast. Open blockers: cam02's new station clips the dome out of frame (0 % sky at top-centre against ref 062's 91 %) and shows a violet shaded face (pier hue 255-263 at sat 0.43-0.46); sunlit stone chroma still 0.07 sat and 29 R-B short of the photograph; the hero mirror at 0.61 of its own sunlit stone against the photo's 0.87.",
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


def _wrap(text, n):
    out, line = [], ""
    for w in text.split():
        if len(line) + len(w) + 1 > n:
            out.append(line); line = w
        else:
            line = (line + " " + w).strip()
    if line:
        out.append(line)
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
    table_h = 60 + (len(ROWS) + 2) * 40 + 20 + 44 + 34 * (len(CAMS) + 1)   # + the r02 -> rnd trend block, one camera per row
    n_verdict = len(_wrap(VERDICT.get(rnd, "Gate: NOT passed."), 165))
    H = 44 + top_h + 30 + strip_h + 26 + table_h + 30 * n_verdict + 30

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
    # ---- trend block: the average per camera for every round scored so far (brief item 2) ----
    seq = [r for r in sorted(SCORES) if int(r) <= int(rnd) and r != "01"]
    d.text((col0, y), "trend  " + "  ".join(f"r{r}" for r in seq), font=f_cell, fill=(200, 200, 200))
    y += 34
    for i, c in enumerate(CAMS):
        vals = [averages(SCORES[r])[i] for r in seq]
        txt = "  ".join(f"{v:.2f}" for v in vals)
        dv = vals[-1] - vals[0]
        col = (140, 235, 140) if dv > 0.3 else ((255, 140, 140) if dv < 0 else (215, 215, 215))
        # one camera per row: with 8 scored rounds the 3-per-row layout overprinted itself (round 09).
        d.text((col0, y + i * 34), f"cam {c:13s} {txt}   ({dv:+.2f} since r02)", font=f_cell, fill=col)
    y += 34 * len(CAMS) + 12
    for line in _wrap(VERDICT.get(rnd, "Gate: NOT passed."), 165):
        d.text((col0, y), line, font=f_cell, fill=(255, 180, 120))
        y += 30

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
