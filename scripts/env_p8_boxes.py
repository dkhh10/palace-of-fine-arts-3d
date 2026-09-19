#!/usr/bin/env python3
"""Phase 8a shrub-structure probe: the QA-17 shrub/reed boxes measured on ENV Eevee previews.

No Blender. Measures the two numbers the 8a brief is judged on, with QA 16's own definitions
(`qa_r16_probe.box_stats`, imported, never redefined here):

  * `leaf%`  share of pixels matching the leaf mask  G - 0.85R > 5 and B < G   (`cover`)
  * `hard%`  share of pixels whose luma gradient magnitude exceeds 40/255      (`hard`)

Frames: the `--local --lod=1` ENV previews written by scripts/env_preview.py (1280x720, Eevee), tagged
`p8a_before` / `p8a_after`, against the QA-17 reference frames (the Phase 5 Cycles hero at station 1, the
round-13 Cycles frames at 2, 3, 5).

RESOLUTION.  qa_r13_probe.rgb() resizes every frame to 1920x1080, so a 1280x720 preview is UPSCALED and its
edges are softened -- which would flatter `hard%` against a native-1920 reference.  Every frame here therefore
goes through the same pipeline: resized to the preview's native 1280x720 first, then to 1920x1080, so the box
coordinates stay QA-17's and the three columns are measured on identical resolution treatment.  The reference
at its native 1920 is printed as a fourth column for context only.

The preview look (env_preview's placeholder sun + sky, AgX Base Contrast, exposure -0.8) is not the Phase 5
master look, so the reference columns are a target to move TOWARD, not an equality test; the decision metric
is before -> after, measured identically.

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
NATIVE = (1280, 720)          # the preview resolution every frame is normalised to
AT = P.AT                     # (1920, 1080), the coordinate space of the QA-17 boxes
# renders/previews/qa/ (the QA reference frames) lives in the MAIN checkout only, like reference/.
MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")


def ref_path(st):
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


def norm(path, native=True):
    """Load -> (optionally) the preview's native 1280x720 -> the box space 1920x1080. LANCZOS throughout."""
    im = Image.open(path).convert("RGB")
    if native and im.size != NATIVE:
        im = im.resize(NATIVE, Image.LANCZOS)
    if im.size != AT:
        im = im.resize(AT, Image.LANCZOS)
    return np.asarray(im, dtype=np.float64)


def table(before_tag, after_tag):
    rows = []
    print("== Phase 8a: QA-17 shrub/reed boxes on the ENV LOD1 Eevee previews ==")
    print(f"   before = {before_tag}   after = {after_tag}   (all frames normalised to {NATIVE} then {AT})")
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
