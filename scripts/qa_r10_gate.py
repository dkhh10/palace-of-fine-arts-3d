#!/usr/bin/env python3
"""QA round 10 gate composite (QA-owned; PIL only, no Blender).

    python3 scripts/qa_r10_gate.py

Panels, top to bottom:
  1. Cycles hero 1920x1080 beside ref 169 mapped through the round-05..10 alignment (scale 1.3108, dx -291.8, dy -126.6)
  2. the main arch at 1:1 (2x nearest-free LANCZOS zoom of the same 260x290 box in both), the round's headline question
  3. the tile defect list from the 100 % six-tile review of the hero + four tiles each of the Eevee cam02 / cam03
  4. the score table with the round-09 -> round-10 deltas and the verdict line

Writes renders/final/v2/round10_gate.png.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
V2 = ROOT / "renders" / "final" / "v2"
HERO = V2 / "qa_round10_cam01_cycles.png"
ALIGNED = V2 / "round10_cam01_aligned_vs_ref169.png"      # render | aligned ref | 50 % blend, 3 x 1920
OUT = V2 / "round10_gate.png"

FONTS = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf",
         "/System/Library/Fonts/Helvetica.ttc"]
FONTS_R = ["/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc"]


def font(size, bold=True):
    for f in (FONTS if bold else FONTS_R):
        if Path(f).exists():
            try:
                return ImageFont.truetype(f, size)
            except Exception:
                pass
    return ImageFont.load_default()


ARCH_BOX = (840, 290, 1100, 580)          # the main arch, render pixels

DEFECTS = [
    ("HERO TILES (Cycles 1920x1080, 3 x 2 at 100 %) — every defect, regardless of the metrics", None, None),
    ("r0c1  840 290 1100 580   the main arch has NO archivolt: a plain bevelled lip where the photo has a moulded", "arch ring", "ornament"),
    ("        band + keystone + rosette course. Arch-ring std 40.8 vs ref 64.2 (0.64x), col-sd 23.5 vs 47.9 (0.49x).", None, None),
    ("r0c1  890 355 1030 470   the coffered barrel reads as a PERFORATED PLATE: round holes in a pale flat field,", "vault coffers", "architecture"),
    ("        no coffer depth, no cast shadow, no rosette. Vault field 103.1 lum vs ref 44.9 = 2.30x too bright.", None, None),
    ("r0c1  866 395 895 490    arch jamb / reveal is MAGENTA-VIOLET: hue 338.5, sat 0.265, lum 61.5 vs ref 95.7 /", "LIGHT_shade_fill_00", "lighting"),
    ("        hue 22.2 / 0.466. QA-08-2's violet is now in the HERO, not only cam02.", None, None),
    ("r0c1  920 95 1000 120    dome cap (ARCH_rotunda_dome, MAT_dome_membrane) untextured near-white, col-sd 5.1:", "dome cap", "materials"),
    ("        a smooth plastic lid; ref 224.3 vs render 189.5 (0.845).", None, None),
    ("r0c1  760 360 900 470 / 1100 360 1240 470   the two side-bay soffits (ARCH_rotunda_vault_01 / _07, 112 faces,", "side-bay vaults", "architecture"),
    ("        MAT_concrete_inner) read as flat dark-olive plates; no coffer relief at all.", None, None),
    ("r0c1  845 330 890 540 / 1050 330 1095 540   ARCH_rotunda_column_03_LOD1 (MAT_column_rose): the shafts are hard", "column shafts", "materials"),
    ("        vertical stripes, bright ochre against violet-black, with no cylindrical falloff. Columns box sat 0.694 vs ref 0.595.", None, None),
    ("r1c1  1055 1005 1090 1065  ENV_gulls_sitting [ENV_extras, MAT_bird_white] at 7.5 m: TWO FLAT-SHADED ICOSPHERES", "ENV_gulls_sitting", "environment"),
    ("        (body + head), no neck, beak, wing, tail or leg. The closest object to the hero camera. BLOCKER.", None, None),
    ("r1c0/r1c1/r1c2  715 705 1785 840   five more gulls in open water; each mirrors as an unbroken white column", "ENV_gulls_sitting", "environment"),
    ("        ~4x its own height, reading as a white post standing in the lagoon.", None, None),
    ("r1c0  0 540 250 650      the left-of-frame colonnade back wall (ARCH_colonnade_south) is flat indigo panels.", "colonnade back wall", "lighting"),
    ("r1c0/r1c2  0 540 640 680 / 1280 540 1920 670   shoreline planting: hard-edged leaf cards, black clumps,", "ENV trees / shrubs", "environment"),
    ("        an orange mulch blob at 1755 655 1820 690, and evenly spaced identical bank rocks.", None, None),
    ("r0c0/r0c2  sky           cloudless, structureless gradient; render sky 0.83x the photograph's level (carried).", "world", "lighting"),
    ("", None, None),
    ("EEVEE cam02, four tiles at 100 %", None, None),
    ("r0c0/r0c1  340 210 640 360   the whole shaded NE face is violet-indigo (shafts, dentils, piers) — QA-08-2 open.", "shade rig", "lighting"),
    ("r0c0/r0c1  735 275 830 360   the arch soffit is CHROME YELLOW rim on an INDIGO coffer field: reads as painted", "interior fill", "lighting"),
    ("        gold-on-blue decoration, not shaded concrete.", None, None),
    ("r1c1  920 465 1160 590   ENV_backdrop_hall_detail / _hall_pavilion (66 faces, MAT_backdrop_building) at 116-122 m:", "ENV_backdrop", "environment"),
    ("        untextured stepped ochre boxes squarely in cam02's mid-ground.", None, None),
    ("r1c0/r1c1  0 360 1280 720   the whole lower half is near-black; leaf cards visible as separate hard cut-outs.", "foliage / shade", "environment"),
    ("", None, None),
    ("EEVEE cam03, four tiles at 100 %", None, None),
    ("r1c0/r1c1  0 480 460 720   colonnade paving is a BLACK-AND-WHITE CHEQUER of large triangles: a test pattern,", "MAT paving", "materials"),
    ("        cold blue-grey, no grout depth, no wear, no dirt.", None, None),
    ("r0c1/r1c1  845 0 1280 720   the near column fills 34 % of the frame as a FLAT olive-green slab: no cylindrical", "near column", "lighting"),
    ("        shading, flutes gone, only a vertical streak texture. LIGHT_gallery_fill lights it evenly from the front.", None, None),
    ("r0c0  0 0 200 360        foreground foliage is a black spiky silhouette with no leaf mass.", "ENV trees", "environment"),
]

SCORES = [
    ("Silhouette match", "4", "4", "align transform bit-identical (1.3108 / -291.8 / -126.6), apex delta 0.44 %H"),
    ("Proportion", "4", "4.5", "the arch opening now has its real depth: ray test + pixel probe give SKY at its centre; far sky 214.4 vs ref 233.3 (0.92x)"),
    ("Ornament fidelity", "4", "3.5", "the revealed arch has no archivolt and its coffers are punched holes: arch-ring structure 0.64x the photograph's"),
    ("Material realism", "3.5", "3.5", "every chroma / texture box within 0.1 of round 09"),
    ("Edge wear", "3.5", "3.5", "attic std 28.9, aniso 5.03, run-off 20.0 % — unchanged"),
    ("Lighting mood", "4.5", "4.0", "the hero's deepest shade is 2.30x the photograph (vault field 103.1 vs 44.9) with a magenta edge (jamb hue 338.5)"),
    ("Water reflection", "3", "3", "lum 115.8 -> 131.5 clears the 124 floor (0.795 of ref) but sat 0.383 -> 0.227 and R-B +50.2 -> +31.9 now fail"),
    ("Repetition visibility", "3", "3", "unchanged"),
    ("Scale cues", "3.5", "3", "the waterfowl that carry the hero's scale are two-icosphere blobs; the nearest is 7.5 m from the camera"),
]

W = 1980
PAD = 20


def main():
    hero = Image.open(HERO).convert("RGB")
    sheet = Image.open(ALIGNED).convert("RGB")
    ref = sheet.crop((1920, 0, 3840, 1080))

    fb, fr, fs = font(21), font(16, False), font(15, False)
    pw = (W - 3 * PAD) // 2
    ph = int(1080 * pw / 1920)

    ax0, ay0, ax1, ay1 = ARCH_BOX
    aw, ah = (ax1 - ax0) * 2, (ay1 - ay0) * 2
    arch_r = hero.crop(ARCH_BOX).resize((aw, ah), Image.LANCZOS)
    arch_f = ref.crop(ARCH_BOX).resize((aw, ah), Image.LANCZOS)

    y_p1 = 78
    y_p2 = y_p1 + ph + 52
    y_p3 = y_p2 + ah + 82
    h_def = 20 * len(DEFECTS) + 16
    y_p4 = y_p3 + h_def + 24
    H = y_p4 + 26 * (len(SCORES) + 4) + 96

    im = Image.new("RGB", (W, H), (18, 18, 20))
    d = ImageDraw.Draw(im)

    d.text((PAD, 16), "QA ROUND 10 — hero gate on the fixed vaults (master.blend, 9695 objects, LOD1 11.52 M)",
           font=font(28), fill=(255, 255, 255))
    d.text((PAD, 50), "Name sweep PASS (1 hit, exempted) · ray-cast opening test PASS on cam01/bay00 and cam02/bay07 · "
                      "tile review FAIL — see the blockers below", font=fr, fill=(230, 200, 120))

    im.paste(hero.resize((pw, ph), Image.LANCZOS), (PAD, y_p1))
    im.paste(ref.resize((pw, ph), Image.LANCZOS), (2 * PAD + pw, y_p1))
    d.text((PAD, y_p1 + ph + 6), "round 10 Cycles hero, 1920x1080, 128 spp, 384.5 s", font=fr, fill=(200, 200, 200))
    d.text((2 * PAD + pw, y_p1 + ph + 6), "ref 169, aligned (scale 1.3108, dx -291.8, dy -126.6)",
           font=fr, fill=(200, 200, 200))
    for x0 in (PAD, 2 * PAD + pw):
        sx = pw / 1920.0
        d.rectangle([x0 + ax0 * sx, y_p1 + ay0 * sx, x0 + ax1 * sx, y_p1 + ay1 * sx], outline=(255, 90, 70), width=2)

    im.paste(arch_r, (PAD, y_p2))
    im.paste(arch_f, (2 * PAD + aw, y_p2))
    d.text((PAD, y_p2 - 24), "THE ROUND'S QUESTION — the main arch at 1:1 (2x), same 260 x 290 px box in both",
           font=fb, fill=(255, 255, 255))
    d.text((PAD, y_p2 + ah + 4), "RENDER — OPEN (v1's chord fill gone,",
           font=fs, fill=(255, 150, 130))
    d.text((PAD, y_p2 + ah + 22), "sky through it) but no archivolt, coffers",
           font=fs, fill=(255, 150, 130))
    d.text((PAD, y_p2 + ah + 40), "= punched holes, jamb magenta",
           font=fs, fill=(255, 150, 130))
    d.text((2 * PAD + aw, y_p2 + ah + 4), "REF 169 — moulded archivolt +",
           font=fs, fill=(160, 220, 160))
    d.text((2 * PAD + aw, y_p2 + ah + 22), "keystone, deep sunk coffers, warm",
           font=fs, fill=(160, 220, 160))
    d.text((2 * PAD + aw, y_p2 + ah + 40), "bounce in the reveal",
           font=fs, fill=(160, 220, 160))
    tx = 3 * PAD + 2 * aw
    for i, ln in enumerate([
            "measured on the pair (aligned panel):",
            "  vault field 900 380 1010 430   render 103.1 lum   ref  44.9   2.30x",
            "  arch jamb   872 400  892 480   render  61.5 / hue 338.5   ref 95.7 / hue 22.2",
            "  arch ring   890 340 1050 370   render std 40.8 / colsd 23.5   ref 64.2 / 47.9",
            "  far sky     940 500  990 530   render 214.4   ref 233.3   0.92x  <-- the opening is real",
            "",
            "ray test (scripts/qa_r10_rays.py), z 16..22 on the bay axis:",
            "  cam01 / bay 00  7/7 PASS  (6 through to the far side, 1 soffit at r 4.9 vs 4.98)",
            "  cam02 / bay 07  7/7 PASS  (6 through, 1 soffit at r 5.0)",
            "  pixel probe: the hero's arch centre (960, 500) returns SKY",
            "",
            "name sweep: 520 exempt, 1 hit — LIGHT_shade_fill_00 (a LIGHT, the",
            "  az-25 blue shade lamp; added to quality_checklist.md as an exception,",
            "  and it is the source of the magenta jamb above)."]):
        d.text((tx, y_p2 + 6 + i * 21), ln, font=fs, fill=(215, 215, 220))

    d.text((PAD, y_p3 - 22), "TILE DEFECT LIST — 100 % review, before any score (CLAUDE.md gate checks 2026-09-10)",
           font=fb, fill=(255, 255, 255))
    for i, (txt, obj, owner) in enumerate(DEFECTS):
        y = y_p3 + i * 20
        col = (255, 255, 255) if owner is None and txt and not txt.startswith("  ") else (205, 205, 210)
        if txt.startswith("HERO TILES") or txt.startswith("EEVEE"):
            col = (250, 205, 110)
        d.text((PAD, y), txt, font=fs, fill=col)
        if owner:
            d.text((W - 430, y), f"{obj}", font=fs, fill=(150, 200, 250))
            d.text((W - 170, y), owner.upper(), font=fs, fill=(255, 140, 120))

    d.text((PAD, y_p4 - 22), "SCORE — hero (cam01) on the round-07..09 boxes, re-based in round 08",
           font=fb, fill=(255, 255, 255))
    d.text((PAD, y_p4 + 4), f"{'row':24s}{'r09':>6s}{'r10':>7s}   why", font=fb, fill=(200, 200, 200))
    for i, (row, a, b, why) in enumerate(SCORES):
        y = y_p4 + 30 + i * 26
        col = (255, 160, 140) if float(b) < float(a) else ((150, 230, 150) if float(b) > float(a) else (215, 215, 220))
        d.text((PAD, y), f"{row:24s}{a:>6s}{b:>7s}", font=fr, fill=col)
        d.text((PAD + 330, y), why, font=fs, fill=(200, 200, 205))
    y = y_p4 + 30 + len(SCORES) * 26 + 10
    d.text((PAD, y), "HERO AVERAGE  3.67  ->  3.56   (-0.11)", font=font(24), fill=(255, 180, 150))
    d.text((PAD + 470, y + 4),
           "like-for-like (scoring only what the round changed: Proportion +0.5, Lighting -0.5) the hero is 3.67, +0.00;",
           font=fs, fill=(200, 200, 205))
    d.text((PAD + 470, y + 22),
           "the -0.11 is the mandated 100 % re-scoring of Ornament fidelity and Scale cues, not a regression in the scene.",
           font=fs, fill=(200, 200, 205))
    d.text((PAD, y + 44),
           "VERDICT — TILE REVIEW: FAIL.  Blockers before the 4K v2: (1) ENV_gulls_sitting [ENVIRONMENT] — two-icosphere "
           "placeholder waterfowl, nearest 7.5 m from the hero camera;",
           font=fb, fill=(255, 120, 100))
    d.text((PAD, y + 68),
           "(2) the rotunda interior fill [LIGHTING] — the arch's barrel field is 2.30x the photograph and its jamb is "
           "magenta (hue 338.5), i.e. the arch the user complained about still does not read.",
           font=fb, fill=(255, 120, 100))
    d.text((PAD, y + 92),
           "Majors for the known-issues list (not blocking, no budget): archivolt absent, coffers without depth, "
           "chequer paving on cam03, flat near column on cam03, cam02 violet face, backdrop boxes.",
           font=fr, fill=(230, 200, 120))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT)
    print(f"wrote {OUT} {im.size}")


main()
