#!/usr/bin/env python3
"""Phase 8a shrub-structure probe: the QA-17 shrub/reed boxes measured on ENV Eevee previews.

No Blender. Measures the two numbers the 8a brief is judged on, with QA 16's own definitions
(`qa_r16_probe.box_stats`, imported, never redefined here):

  * `leaf%`  share of pixels matching the leaf mask  G - 0.85R > 5 and B < G   (`cover`)
  * `hard%`  share of pixels whose luma gradient magnitude exceeds 40/255      (`hard`)

Frames: the `--local --lod=1` ENV previews written by scripts/env_preview.py (1280x720, Eevee), tagged
`p8a_before` / `p8a_after`, against the QA-17 reference frames (the Phase 5 Cycles hero at station 1, the
round-13 Cycles frames at 2, 3, 5).

RESOLUTION and LOOK -- read before trusting a column.  Frames go through qa_r13_probe.rgb()'s own rule (LANCZOS
to 1920x1080 and nothing else), which reproduces every QA-17 reference number exactly; see `norm`.  Two
consequences: the 1280x720 previews are UPSCALED, so their `hard%` reads several times low against a native-1920
Cycles reference; and env_preview's look (placeholder sun + sky, AgX Base Contrast, exposure -0.8) is not the
Phase 5 master look and is olive enough that the leaf mask also catches lit stone, so the previews' `leaf%` runs
about 1.7x the reference across the seven boxes.  The reference column is therefore a DIRECTION, not an equality
test, and the decision metric is before -> after, measured identically.  The viewer numbers QA scores are taken
on the exported build, not here.

    python3 scripts/env_p8_boxes.py                        # table
    python3 scripts/env_p8_boxes.py --sheet                # table + renders/qa_comparisons/p8a_shrubs_*.jpg
    python3 scripts/env_p8_boxes.py --before X --after Y   # explicit preview tags
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_r17_probe as P17  # noqa: E402  (registers rounds 13-17; gives SHRUB + box_stats)

P16 = P17.P16
P = P17.P
ROOT = Path(__file__).resolve().parent.parent
PREV = ROOT / "renders/previews/environment"
OUT = ROOT / "renders/qa_comparisons"
AT = P.AT                     # (1920, 1080), the coordinate space of the QA-17 boxes
# renders/previews/qa/ (the QA reference frames) lives in the MAIN checkout only, like reference/.
MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")


P.select_round("17")
# qa_r13_probe builds REF_R14 with `if _p.exists()` against ITS OWN root -- in a worktree the round-13 Cycles
# frames are not there, so the table silently fell back to the round-09 frames and the reference column stopped
# being QA 17's (cam02's leaf share read 71.5 % where QA measured 88.6 %). Resolve every reference in MAIN.
R13 = {2: "02_lagoon_ne_threequarter", 3: "03_colonnade_walk", 4: "04_rotunda_ceiling",
       5: "05_south_lawn", 6: "06_aerial"}


def ref_path(st):
    if st in R13:
        p = MAIN / f"renders/previews/qa/round13_{R13[st]}_cycles.png"
        if p.exists():
            return p
    p = Path(P.REF[st][0])
    if p.exists():
        return p
    alt = MAIN / p.relative_to(P.ROOT)
    if alt.exists():
        return alt
    raise SystemExit(f"reference frame for station {st} not found: {p}")

# the 8a stations: the QA-17 shrub/reed boxes at 1, 2, 3 and 5 (cam06 is out of the brief's scope)
BOXES = [(n, st, box, why) for (n, st, box, why) in P17.SHRUB if st in (1, 2, 3, 5)]
CAM = {1: "01_lagoon_hero", 2: "02_lagoon_ne_threequarter", 3: "03_colonnade_walk", 5: "05_south_lawn"}


def preview(tag, st):
    """Newest renders/previews/environment/<ts>_<cam>_<tag>.png for that station."""
    hits = sorted(PREV.glob(f"*_{CAM[st]}_{tag}.png"))
    if not hits:
        raise SystemExit(f"no ENV preview for station {st} with tag '{tag}' in {PREV}")
    return hits[-1]


def norm(path):
    """qa_r13_probe.rgb()'s own rule: LANCZOS to the 1920x1080 box space, nothing else.

    A first version normalised every frame DOWN to the preview's 1280x720 first, to equalise the resolution
    treatment. It has to be recorded as wrong: averaging 1920 -> 1280 destroys the leaf mask wherever the leaf
    is fine against a warm background -- the cam02 reed clump's reference leaf share fell from QA 17's 24.9 %
    to 2.0 % -- so the reference column stopped being the number QA measured. Keeping QA's own pipeline means
    the 1280x720 previews are UPSCALED and their `hard%` reads low against a native-1920 reference; before and
    after are upscaled identically, so the before -> after column is sound and the reference column is a
    direction, not an equality test."""
    im = Image.open(path).convert("RGB")
    if im.size != AT:
        im = im.resize(AT, Image.LANCZOS)
    return np.asarray(im, dtype=np.float64)


def table(before_tag, after_tag):
    rows = []
    print("== Phase 8a: QA-17 shrub/reed boxes on the ENV LOD1 Eevee previews ==")
    print(f"   before = {before_tag}   after = {after_tag}   (frames LANCZOS to {AT}, qa_r13_probe.rgb rule)")
    print()
    print(f"{'box':22s} {'leaf% bef':>9s} {'leaf% aft':>9s} {'ref':>7s} {'aft/ref':>8s}   "
          f"{'hard% bef':>9s} {'hard% aft':>9s} {'ref':>7s}   {'lum bef':>8s} {'lum aft':>8s}")
    for name, st, box, why in BOXES:
        b = P16.box_stats(norm(preview(before_tag, st)), box)
        a = P16.box_stats(norm(preview(after_tag, st)), box)
        r = P16.box_stats(norm(ref_path(st)), box)
        rows.append((name, st, box, b, a, r))
        print(f"{name:22s} {b['cover']:8.1f}% {a['cover']:8.1f}% {r['cover']:6.1f}% "
              f"{a['cover'] / max(r['cover'], 1e-6):7.2f}x   "
              f"{b['hard']:8.2f}% {a['hard']:8.2f}% {r['hard']:6.2f}%   "
              f"{b['lum']:8.1f} {a['lum']:8.1f}")
    print()
    lb = np.mean([b["cover"] for *_, b, a, r in rows])
    la = np.mean([a["cover"] for *_, b, a, r in rows])
    lr = np.mean([r["cover"] for *_, b, a, r in rows])
    hb = np.mean([b["hard"] for *_, b, a, r in rows])
    ha = np.mean([a["hard"] for *_, b, a, r in rows])
    hr = np.mean([r["hard"] for *_, b, a, r in rows])
    print(f"mean over {len(rows)} boxes:  leaf% {lb:.1f} -> {la:.1f} (ref {lr:.1f}; "
          f"{lb / lr:.2f}x -> {la / lr:.2f}x)   hard% {hb:.2f} -> {ha:.2f} (ref {hr:.2f})")
    return rows


def sheet(rows, before_tag, after_tag):
    """One jpg per station: the box crop from before / after / reference, stacked, labelled, 960 px wide."""
    OUT.mkdir(parents=True, exist_ok=True)
    from PIL import ImageDraw
    by_st = {}
    for name, st, box, b, a, r in rows:
        by_st.setdefault(st, []).append((name, box, b, a, r))
    written = []
    for st, items in sorted(by_st.items()):
        srcs = [("before", Image.fromarray(norm(preview(before_tag, st)).astype(np.uint8))),
                ("after", Image.fromarray(norm(preview(after_tag, st)).astype(np.uint8))),
                ("reference", Image.fromarray(norm(ref_path(st)).astype(np.uint8)))]
        cells = []
        for name, box, b, a, r in items:
            x0, y0, x1, y1 = box
            for (lbl, im), st_ in zip(srcs, (b, a, r)):
                c = im.crop(box)
                cells.append((f"{lbl}  leaf {st_['cover']:.1f}%  hard {st_['hard']:.2f}%  {name}", c))
        cw = 960
        scaled = []
        for lbl, c in cells:
            h = max(1, int(round(c.height * cw / c.width)))
            scaled.append((lbl, c.resize((cw, h), Image.LANCZOS)))
        pad = 16
        H = sum(h.height + pad for _, h in scaled) + pad
        sh = Image.new("RGB", (cw, H), (18, 18, 18))
        d = ImageDraw.Draw(sh)
        y = pad
        for lbl, c in scaled:
            sh.paste(c, (0, y))
            d.text((6, y + 3), lbl, fill=(255, 245, 120))
            y += c.height + pad
        p = OUT / f"p8a_shrubs_cam{st:02d}.jpg"
        sh.save(p, quality=88)
        written.append(p)
        print("[env_p8_boxes] wrote", p)
    return written


def frames_sheet(before_tag, after_tag):
    """One 960 px sheet: the whole before / after frame at each of the four stations, box drawn on."""
    from PIL import ImageDraw
    OUT.mkdir(parents=True, exist_ok=True)
    w = 480
    rows = []
    for st in (1, 2, 3, 5):
        pair = []
        for lbl, p in (("before", preview(before_tag, st)), ("after", preview(after_tag, st))):
            im = Image.fromarray(norm(p).astype(np.uint8))
            d = ImageDraw.Draw(im)
            for name, s, box, why in BOXES:
                if s == st:
                    d.rectangle(box, outline=(255, 240, 90), width=3)
            im = im.resize((w, int(round(im.height * w / im.width))), Image.LANCZOS)
            ImageDraw.Draw(im).text((6, 4), f"cam{st:02d} {lbl}", fill=(255, 245, 120))
            pair.append(im)
        rows.append(pair)
    H = sum(r[0].height for r in rows)
    sh = Image.new("RGB", (2 * w, H), (18, 18, 18))
    y = 0
    for a, b in rows:
        sh.paste(a, (0, y))
        sh.paste(b, (w, y))
        y += a.height
    p = OUT / "p8a_shrubs_frames.jpg"
    sh.save(p, quality=86)
    print("[env_p8_boxes] wrote", p)
    return p


if __name__ == "__main__":
    argv = sys.argv[1:]
    bt, at = "p8a_before", "p8a_after"
    for i, a in enumerate(argv):
        if a == "--before":
            bt = argv[i + 1]
        elif a == "--after":
            at = argv[i + 1]
    rows = table(bt, at)
    if "--sheet" in argv:
        sheet(rows, bt, at)
        frames_sheet(bt, at)
