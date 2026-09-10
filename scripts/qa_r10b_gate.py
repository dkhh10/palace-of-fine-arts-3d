#!/usr/bin/env python3
"""QA round 10b gate composite (QA-owned; PIL only, no Blender).

    python3 scripts/qa_r10b_gate.py

Same four panels as scripts/qa_r10_gate.py, re-stated for the round-10b re-check (gulls removed, LIGHT r18 vault-fill
bay weights, the lead's shade-fill-off):
  1. Cycles hero 1920x1080 beside ref 169 mapped through the round-05..10b alignment (scale 1.3108, dx -291.8, dy -126.6)
  2. the main arch at 1:1 (2x), same 260x290 box in both -- the round's headline question
  3. the round-10 tile list re-stated FIXED / OPEN, plus the new defects
  4. the score table with the round-10 -> round-10b deltas and the verdict line

Writes renders/final/v2/round10b_gate.png.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
V2 = ROOT / "renders" / "final" / "v2"
HERO = V2 / "qa_round10b_cam01_cycles.png"
ALIGNED = V2 / "round10b_cam01_aligned_vs_ref169.png"
OUT = V2 / "round10b_gate.png"

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


ARCH_BOX = (840, 290, 1100, 580)

DEFECTS = [
    ("ROUND-10 TILE LIST, RE-STATED ON THE ROUND-10B HERO (Cycles 1920x1080, 3 x 2 at 100 %)", None, None),
    ("QA-10-1   FIXED   no waterfowl on the open water; the nearest gull is a shore bird ~100 m out, a few px wide.", "ENV_gulls_sitting", "environment"),
    ("QA-10-2   FIXED   vault field 900 380 1010 430 = 60.6 lum (window 45-65, ref 44.9; was 103.1 = 2.30x) and the", "vault fill / shade fill", "lighting"),
    ("                  jamb 872 400 892 480 = hue 25.0, R-B +36.2 (window 25-60 + positive; was hue 338.5). No magenta.", None, None),
    ("QA-10-3   OPEN    still no archivolt: a plain band where the photo has a moulded archivolt, keystone and bead", "arch ring", "ornament"),
    ("                  course. Arch-ring std 55.5 vs ref 64.2 (0.86x, was 0.64x), col-sd 30.3 vs 47.9 (0.63x, was 0.49x).", None, None),
    ("QA-10-4   OPEN    the coffered barrel now shades and reads concave, but the coffers are still soft round holes", "vault coffers", "architecture"),
    ("                  with no hard shadow line and no rosette; several read as melted blobs on the right haunch.", None, None),
    ("QA-10-5   OPEN    the two side-bay soffits are still flat plates; they show punched circles, no coffer relief.", "ARCH_rotunda_vault_01/_07", "architecture"),
    ("QA-10-6   FIXED   floating gulls removed in env_build.py (b058e45); no white posts in the water on any tile.", "ENV_gulls_sitting", "environment"),
    ("QA-10-7   OPEN    shafts are still hard vertical stripes with no cylindrical falloff; columns box sat 0.712 vs", "MAT_column_rose", "materials"),
    ("                  the photograph's 0.566 -- WORSE than round 10 (0.694): the shade fill went, the chroma rose.", None, None),
    ("QA-10-8   OPEN    dome cap untextured near-white lid, col-sd 5.3, 187.6 vs ref 224.3 (0.84x). Unchanged.", "MAT_dome_membrane", "materials"),
    ("QA-10-9   CHANGED the colonnade back wall is no longer indigo (warm dark brown now) but still flat, untextured.", "ARCH_colonnade_south", "lighting"),
    ("QA-10-10  OPEN    shoreline planting: hard leaf cards, smooth shrub blobs, the orange mulch pile still at 1755 655.", "ENV trees / shrubs", "environment"),
    ("QA-10-11  OPEN    sky cloudless and structureless; sky_top 167.9 vs ref 202.8 = 0.83x, sat 0.433 vs 0.332.", "world", "lighting"),
    ("QA-10-12  PARTLY  cam02: the piers and entablature are warm at last (pier hue 44.9, face hue 42.9; was violet),", "shade rig", "lighting"),
    ("                  but a shaded shaft cluster at 690 230 720 320 is STILL magenta: hue 335.5, sat 0.182.", None, None),
    ("QA-10-13  OPEN    cam02: the arch soffit is still a bright rim over dark coffers reading as gold-on-dark paint.", "interior fill", "lighting"),
    ("QA-10-14  OPEN    cam02: ENV_backdrop_hall_* stepped untextured boxes in the mid-ground (box lum 93.9, std 71.5).", "ENV_backdrop", "environment"),
    ("QA-10-15  OPEN    cam02: the lower half is still near-black (60.1 lum); leaf cards read as hard cut-outs.", "foliage / shade", "environment"),
    ("QA-10-16  OPEN    cam03: the paving is still a chequer, cold and flat (hue 71.5, sat 0.331, no grout depth).", "MAT paving", "materials"),
    ("QA-10-17  WORSE   cam03: the near column is now a near-black olive slab: 17.7 lum = 0.192 of the sunlit rotunda", "near column", "lighting"),
    ("                  against the photograph's 0.292 and LIGHT r17's own 0.305. The outer row fell 0.289 -> 0.176.", None, None),
    ("QA-10-18  OPEN    cam03: foreground foliage is a black spiky silhouette with no leaf mass.", "ENV trees", "environment"),
    ("", None, None),
    ("NEW THIS ROUND", None, None),
    ("QA-10b-1  MAJOR   the whole frame is more saturated than the photograph, and it moved this round: whole building", "shade chroma", "lighting + materials"),
    ("                  700 160 1240 480 sat 0.571 (r09) -> 0.636 vs ref 0.521 = 1.22x; shaded attic hue 41.2 / sat 0.628", None, None),
    ("                  vs ref 30.6 / 0.454; entablature sat 0.777 vs 0.588; shore band 0.821. The stone reads mustard-", None, None),
    ("                  olive in shade where the photograph is a warm neutral grey-tan. Cost of the shade-fill-off; not", None, None),
    ("                  a blocker (the lead pre-accepted the shade windows), but it is the one cheap lever left on the hero.", None, None),
    ("QA-10b-2  MINOR   entablature 120.2 vs ref 145.5 = 0.83x (was 0.91x): the vault-fill bay weights darkened it.", "VAULT_FILL weights", "lighting"),
]

SCORES = [
    ("Silhouette match", "4", "4", "align transform bit-identical for the fifth round (1.3108 / -291.8 / -126.6), apex delta 0.44 %H"),
    ("Proportion", "4.5", "4.5", "ray test 14/14 PASS again on cam01/bay00 and cam02/bay07; the opening is real and unchanged"),
    ("Ornament fidelity", "3.5", "3.5", "arch-ring structure 0.64x -> 0.86x std (the vault shades now) but still no archivolt, keystone or rosette"),
    ("Material realism", "3.5", "3", "frame chroma moved AWAY from the photograph: whole building sat 1.10x -> 1.22x ref, columns 1.26x, shade reads mustard"),
    ("Edge wear", "3.5", "3.5", "attic std 29.5, aniso 5.15, unchanged within noise"),
    ("Lighting mood", "4", "4.5", "both QA-10-2 acceptance boxes land: vault field 103.1 -> 60.6 (window 45-65) and the jamb is warm (hue 25.0, R-B +36)"),
    ("Water reflection", "3", "3", "128.6 lum still clears the 124 floor (0.78x ref) but sat 0.250 vs 0.358 and R-B +34.4 vs +68.7 still fail"),
    ("Repetition visibility", "3", "3", "unchanged"),
    ("Scale cues", "3", "3.5", "the two-icosphere gulls are gone from the foreground; the hero now has no placeholder-grade object at all"),
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
    y_p3 = y_p2 + ah + 108
    h_def = 20 * len(DEFECTS) + 16
    y_p4 = y_p3 + h_def + 24
    H = y_p4 + 26 * (len(SCORES) + 4) + 110

    im = Image.new("RGB", (W, H), (18, 18, 20))
    d = ImageDraw.Draw(im)

    d.text((PAD, 16), "QA ROUND 10b — hero tile re-check after the two blockers (master.blend, 9691 objects)",
           font=font(28), fill=(255, 255, 255))
    d.text((PAD, 50), "Name sweep PASS (520 exempt, 0 hits) · ray-cast opening test PASS 14/14 · "
                      "both QA-10 blockers CLOSED · tile review PASS", font=fr, fill=(150, 230, 150))

    im.paste(hero.resize((pw, ph), Image.LANCZOS), (PAD, y_p1))
    im.paste(ref.resize((pw, ph), Image.LANCZOS), (2 * PAD + pw, y_p1))
    d.text((PAD, y_p1 + ph + 6), "round 10b Cycles hero, 1920x1080, 128 spp, 376.1 s", font=fr, fill=(200, 200, 200))
    d.text((2 * PAD + pw, y_p1 + ph + 6), "ref 169, aligned (scale 1.3108, dx -291.8, dy -126.6)",
           font=fr, fill=(200, 200, 200))
    for x0 in (PAD, 2 * PAD + pw):
        sx = pw / 1920.0
        d.rectangle([x0 + ax0 * sx, y_p1 + ay0 * sx, x0 + ax1 * sx, y_p1 + ay1 * sx], outline=(255, 90, 70), width=2)

    im.paste(arch_r, (PAD, y_p2))
    im.paste(arch_f, (2 * PAD + aw, y_p2))
    d.text((PAD, y_p2 - 24), "THE ROUND'S QUESTION — the main arch at 1:1 (2x), same 260 x 290 px box in both",
           font=fb, fill=(255, 255, 255))
    for i, ln in enumerate(["RENDER — the arch READS now: near arch ->", "concave shaded barrel -> far arch -> sky, and",
                            "the reveal is warm. Still no archivolt, the", "coffers are soft holes, the stone is mustard."]):
        d.text((PAD, y_p2 + ah + 4 + i * 18), ln, font=fs, fill=(255, 200, 130))
    for i, ln in enumerate(["REF 169 — moulded archivolt + keystone,", "deep sunk coffers with hard shadow lines,",
                            "engaged capitals at the springing, warm", "neutral grey-tan stone."]):
        d.text((2 * PAD + aw, y_p2 + ah + 4 + i * 18), ln, font=fs, fill=(160, 220, 160))
    tx = 3 * PAD + 2 * aw
    for i, ln in enumerate([
            "the QA-10-2 acceptance boxes (render | ref 169, aligned panel):",
            "  vault field 900 380 1010 430   60.6 lum | 44.9    window 45-65   PASS",
            "  arch jamb   872 400  892 480   hue 25.0, R-B +36.2 | 22.2, +58.9  window 25-60 + positive  PASS",
            "",
            "the moved holds (render | ref 169 | window):",
            "  shaded attic 1110 225 1150 260  122.1 / 41.2 / 0.628 | 120.5 / 30.6 / 0.454 | lum 103.5-126.5 PASS,",
            "                                   hue 23.5-35.5 FAIL, sat <= 0.50 FAIL   (the lead's accepted trade)",
            "  sunlit attic  900 222 1020 256  187.7 / sat 0.518 / R-B +117.7 | 189.8 / 0.582 / +134.2 | lum PASS,",
            "                                   sat 0.53-0.62 marginal FAIL (0.487 -> 0.518, moved toward the photo)",
            "  sky top      1210  22 1690  76  167.9 | 202.8 = 0.83x   (carried, unchanged)",
            "  reflection    900 760 1020 840  128.6 / 44.2 / 0.250 / +34.4 | 165.5 / 33.7 / 0.358 / +68.7  (flat vs r10)",
            "  entablature   900 262 1020 296  120.2 | 145.5 = 0.83x   (was 0.91x -- QA-10b-2)",
            "  columns       680 280 1240 470  114.3 / 39.1 / 0.712 | 124.0 / 32.7 / 0.566   sat 1.26x, worse",
            "",
            "cam02: pier 600 110 660 200 hue 44.9 (window 25-60) PASS, sat 0.549 (<= 0.35) FAIL; soffit_l/_r hue 41.4 /",
            "  42.2, sat 0.424 / 0.488 (r18 held 36 / 34 at 0.34); one shaded shaft cluster still magenta, hue 335.5.",
            "cam03: near column 17.7 lum = 0.192 of the sunlit rotunda (ref 0.292, LIGHT r17 0.305); outer row 0.176.",
            "",
            "name sweep: 520 exempt, 0 hits (LIGHT_shade_fill_00 is off and gone from the sweep).",
            "rays: cam01/bay00 7/7, cam02/bay07 7/7 -- every first hit the far side or the soffit at its radius."]):
        d.text((tx, y_p2 + 6 + i * 20), ln, font=fs, fill=(215, 215, 220))

    d.text((PAD, y_p3 - 22), "TILE REVIEW — the round-10 list re-stated at 100 %, before any score",
           font=fb, fill=(255, 255, 255))
    for i, (txt, obj, owner) in enumerate(DEFECTS):
        y = y_p3 + i * 20
        col = (205, 205, 210)
        if txt.startswith("ROUND-10 TILE") or txt.startswith("NEW THIS"):
            col = (250, 205, 110)
        elif "FIXED" in txt[:22]:
            col = (150, 230, 150)
        elif "WORSE" in txt[:22] or "MAJOR" in txt[:22]:
            col = (255, 160, 140)
        d.text((PAD, y), txt, font=fs, fill=col)
        if owner:
            d.text((W - 460, y), f"{obj}", font=fs, fill=(150, 200, 250))
            d.text((W - 200, y), owner.upper(), font=fs, fill=(255, 140, 120))

    d.text((PAD, y_p4 - 22), "SCORE — hero (cam01) on the round-07..09 boxes, re-based in round 08",
           font=fb, fill=(255, 255, 255))
    d.text((PAD, y_p4 + 4), f"{'row':24s}{'r10':>6s}{'r10b':>8s}   why", font=fb, fill=(200, 200, 200))
    for i, (row, a, b, why) in enumerate(SCORES):
        y = y_p4 + 30 + i * 26
        col = (255, 160, 140) if float(b) < float(a) else ((150, 230, 150) if float(b) > float(a) else (215, 215, 220))
        d.text((PAD, y), f"{row:24s}{a:>6s}{b:>8s}", font=fr, fill=col)
        d.text((PAD + 330, y), why, font=fs, fill=(200, 200, 205))
    y = y_p4 + 30 + len(SCORES) * 26 + 10
    d.text((PAD, y), "HERO AVERAGE  3.56  ->  3.61   (+0.05;  round 09 was 3.67, so -0.06 against it)",
           font=font(24), fill=(180, 230, 170))
    d.text((PAD, y + 34),
           "VERDICT — TILE REVIEW: PASS. Both round-10 blockers are closed and their acceptance boxes land; the name "
           "sweep is clean at 0 hits and every ray still passes.",
           font=fb, fill=(150, 230, 150))
    d.text((PAD, y + 58),
           "No placeholder-grade object remains anywhere in the hero frame. The 4K v2 is worth its wall time.",
           font=fb, fill=(150, 230, 150))
    d.text((PAD, y + 82),
           "Carried, not blocking: QA-10b-1 (frame chroma 1.22x the photograph, the cost of the shade-fill-off) and the "
           "known-issues majors — archivolt, coffer depth, dome cap,",
           font=fr, fill=(230, 200, 120))
    d.text((PAD, y + 104),
           "column stripes, cam02 magenta shaft + gold-on-dark soffit, cam03 chequer paving and its now near-black "
           "column (QA-10-17 worse), backdrop boxes, cloudless sky.",
           font=fr, fill=(230, 200, 120))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT)
    print(f"wrote {OUT} {im.size}")


main()
