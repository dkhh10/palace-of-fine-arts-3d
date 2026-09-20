#!/usr/bin/env python3
"""Phase 9 before/after comparison sheet (no Blender, no Chrome, no GPU).

    python3 scripts/phase9_sheet.py             # hero composite + tiles (cam01)
    python3 scripts/phase9_sheet.py --stations   # gate12 vs AFTER_GATE, cam02-06, one 960 px composite each
    python3 scripts/phase9_sheet.py --check      # list which input files exist and exit 0 (no images written)
    python3 scripts/phase9_sheet.py --after-gate gate14   # override AFTER_GATE for any of the above

Row A: viewer hero BEFORE (gate12_cam01) vs AFTER (<AFTER_GATE>_cam01, the Phase 9 gate capture).
Row B: Cycles 4K hero BEFORE (renders/final/phase8/hero_cam01_3840x2160_128spp.png) vs AFTER
  (renders/final/hero_cam01_3840x2160_128spp.png, the new Phase 9 hero, rendered later in Phase 9).
  If AFTER is missing, or still byte-identical to BEFORE (i.e. the Phase 9 4K hero has not landed
  yet), the script uses BEFORE as a stand-in for AFTER and prints a warning. Re-run this script
  once the real render lands.
Row C: reference photo (ref 169, letterboxed to the 16:9 hero framing) vs Cycles AFTER.

Outputs:
  renders/qa_comparisons/phase9_before_after_960.jpg   (committed)
  renders/qa_comparisons/phase9_tiles/*.png + boxes.json  (gitignored, full resolution)
  renders/qa_comparisons/phase9_stations/phase9_camNN_960.jpg  (--stations; committed)
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# This script may run from a worktree (e.g. .claude/worktrees/phase9-sheet), which does not
# contain the gitignored renders/final, renders/web full-res captures, or reference/photos
# (~175 MB, main checkout only per CLAUDE.md). Inputs are always read from the MAIN checkout by
# absolute path; outputs are written under THIS repo root (so the branch/worktree gets the
# committed 960 px composites and the gitignored tiles alongside its own scripts/).
REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_CHECKOUT = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
ROOT = MAIN_CHECKOUT  # used for relative-path labels only

WEB = MAIN_CHECKOUT / "renders/web"
FINAL = MAIN_CHECKOUT / "renders/final"
REF169 = MAIN_CHECKOUT / "reference/photos/raw/ref_169_main_Palace_of_Fine_Arts_16794p.jpg"

QA = REPO_ROOT / "renders/qa_comparisons"
TILES_DIR = QA / "phase9_tiles"
STATIONS_DIR = QA / "phase9_stations"

# The Phase 9 gate capture prefix (renders/web/<AFTER_GATE>_camNN.png). Override with
# --after-gate <name> on the command line (e.g. once the real Phase 9 gate number is known).
AFTER_GATE = "gate13"

BEFORE_GATE = "gate12"

CYCLES_BEFORE = FINAL / "phase8/hero_cam01_3840x2160_128spp.png"
CYCLES_AFTER = FINAL / "hero_cam01_3840x2160_128spp.png"

FONT_PATH = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

# ---------------------------------------------------------------------------
# Tile boxes, picked by eye against the 960 px cam01 frame (16:9), then scaled
# to each source resolution. Same boxes apply to viewer (1920x1080) and Cycles
# (3840x2160) captures of cam01 because both use the same fixed QA station
# (scripts/qa_cameras.py CAM_qa_01_lagoon_hero) - verified by cropping both at
# these coordinates before committing to them (see report).
BOXES_960 = {
    "colonnade_backdrop_N": (10, 195, 330, 300),   # left third, colonnade + tree belt at the horizon
    "shore_shrub_band": (520, 260, 820, 360),       # bottom third, centre-right, shore shrubs
    "far_crown": (630, 185, 760, 260),              # top-right, a tree crown against the sky
}

STATIONS = ["cam02", "cam03", "cam04", "cam05", "cam06"]


def _font(size, bold=False):
    try:
        return ImageFont.truetype(FONT_BOLD if bold else FONT_PATH, size)
    except OSError:
        return ImageFont.load_default()


def _im(path):
    return Image.open(str(path)).convert("RGB")


def _scale_to_width(im, width):
    if im.width == width:
        return im
    h = round(im.height * width / im.width)
    return im.resize((width, h), Image.LANCZOS)


def _letterbox(im, target_w, target_h, bg=(8, 8, 8)):
    """Fit im into target_w x target_h preserving aspect, padding with bg (letterbox/pillarbox)."""
    src_ratio = im.width / im.height
    dst_ratio = target_w / target_h
    if src_ratio > dst_ratio:
        new_w = target_w
        new_h = round(target_w / src_ratio)
    else:
        new_h = target_h
        new_w = round(target_h * src_ratio)
    resized = im.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("RGB", (target_w, target_h), bg)
    canvas.paste(resized, ((target_w - new_w) // 2, (target_h - new_h) // 2))
    return canvas


def _truncate(d, text, font, max_w):
    if d.textlength(text, font=font) <= max_w:
        return text
    while text and d.textlength(text + "...", font=font) > max_w:
        text = text[:-1]
    return text + "..."


def _label_bar(width, lines, height=54, bg=(15, 15, 15), fg=(235, 235, 235)):
    bar = Image.new("RGB", (width, height), bg)
    d = ImageDraw.Draw(bar)
    y = 6
    for i, (text, bold) in enumerate(lines):
        font = _font(15, bold=bold)
        text = _truncate(d, text, font, width - 12)
        d.text((8, y), text, font=font, fill=fg)
        y += 19
    return bar


def _panel(im, width, title_lines):
    """Scale im to `width` wide, stack a label bar above it."""
    scaled = _scale_to_width(im, width)
    bar = _label_bar(width, title_lines)
    out = Image.new("RGB", (width, bar.height + scaled.height), (15, 15, 15))
    out.paste(bar, (0, 0))
    out.paste(scaled, (0, bar.height))
    return out


def _row(panels, pad=6, bg=(30, 30, 30)):
    h = max(p.height for p in panels)
    w = sum(p.width for p in panels) + pad * (len(panels) - 1)
    out = Image.new("RGB", (w, h), bg)
    x = 0
    for p in panels:
        out.paste(p, (x, 0))
        x += p.width + pad
    return out


def _stack_rows(rows, pad=10, bg=(30, 30, 30)):
    w = max(r.width for r in rows)
    h = sum(r.height for r in rows) + pad * (len(rows) - 1)
    out = Image.new("RGB", (w, h), bg)
    y = 0
    for r in rows:
        out.paste(r, ((w - r.width) // 2, y))
        y += r.height + pad
    return out


def _mtime(path):
    import datetime
    return datetime.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")


def build_hero_sheet():
    QA.mkdir(parents=True, exist_ok=True)
    TILES_DIR.mkdir(parents=True, exist_ok=True)

    viewer_before = WEB / f"{BEFORE_GATE}_cam01.png"
    viewer_after = WEB / f"{AFTER_GATE}_cam01.png"
    for _p in (viewer_before, viewer_after):
        if not _p.exists():
            sys.exit(f"run --check: {_p} missing")

    cycles_before_path = CYCLES_BEFORE
    cycles_after_path = CYCLES_AFTER
    cycles_after_is_standin = False
    if not cycles_after_path.exists():
        cycles_after_is_standin = True
    else:
        import filecmp
        if cycles_before_path.exists() and filecmp.cmp(cycles_before_path, cycles_after_path, shallow=False):
            cycles_after_is_standin = True

    if cycles_after_is_standin:
        print(f"WARNING: {cycles_after_path.relative_to(ROOT)} is not a post-Phase-9 render yet "
              f"(identical to BEFORE, or missing). Using BEFORE as a stand-in for AFTER. "
              f"Re-run this script once the Phase 9 4K hero lands.")

    col_w = 480  # 960 total / 2 columns

    vb = _panel(_im(viewer_before), col_w,
                [(f"VIEWER BEFORE  {BEFORE_GATE}_cam01.png  ({_mtime(viewer_before)})", True),
                 ("Phase 8 (final)", False)])
    va = _panel(_im(viewer_after), col_w,
                [(f"VIEWER AFTER  {AFTER_GATE}_cam01.png  ({_mtime(viewer_after)})", True),
                 ("Phase 9", False)])
    row1 = _row([vb, va])

    cb_label = f"CYCLES BEFORE  phase8/hero_cam01_3840x2160_128spp.png  ({_mtime(cycles_before_path)})"
    ca_label_line2 = "Phase 9" if not cycles_after_is_standin else \
        "STAND-IN = BEFORE FILE (Phase 9 4K hero not rendered yet)"
    cb = _panel(_im(cycles_before_path), col_w,
                [(cb_label, True), ("Phase 8 (final)", False)])
    ca = _panel(_im(cycles_after_path if cycles_after_path.exists() else cycles_before_path), col_w,
                [(f"CYCLES AFTER  hero_cam01_3840x2160_128spp.png  ({_mtime(cycles_after_path if cycles_after_path.exists() else cycles_before_path)})", True),
                 (ca_label_line2, False)])
    row2 = _row([cb, ca])

    ref_im = _im(REF169)
    ref_letterboxed = _letterbox(ref_im, 1920, 1080)
    rf = _panel(ref_letterboxed, col_w,
                [("REFERENCE  ref_169_main_...16794p.jpg  (2020-02-01, morning golden hour)", True),
                 ("letterboxed to 16:9 hero framing", False)])
    ca2 = _panel(_im(cycles_after_path if cycles_after_path.exists() else cycles_before_path), col_w,
                 [("CYCLES AFTER  (same file as row 2 right)", True),
                  (ca_label_line2, False)])
    row3 = _row([rf, ca2])

    header = _label_bar(row1.width, [("Phase 9 before / after - Palace of Fine Arts lagoon hero (cam01)", True)],
                         height=30, bg=(0, 0, 0))
    sheet = _stack_rows([header, row1, row2, row3])
    out_path = QA / "phase9_before_after_960.jpg"
    sheet.convert("RGB").save(out_path, quality=92)
    print(f"wrote {out_path.relative_to(ROOT)}  {sheet.size}")

    # --- full-resolution tiles ---------------------------------------------------
    sources = {
        f"viewer_before_{BEFORE_GATE}_cam01": viewer_before,
        f"viewer_after_{AFTER_GATE}_cam01": viewer_after,
        "cycles_before_phase8": cycles_before_path,
        "cycles_after_hero": (cycles_after_path if cycles_after_path.exists() else cycles_before_path),
    }
    manifest = {"box_space": "960px-wide reference frame, scaled per source width",
                "boxes_960": BOXES_960, "sources": {}, "crops": []}
    for src_name, src_path in sources.items():
        im = _im(src_path)
        scale = im.width / 960.0
        manifest["sources"][src_name] = {"path": str(src_path.relative_to(ROOT)),
                                          "width": im.width, "height": im.height, "scale_from_960": scale}
        for box_name, box in BOXES_960.items():
            full_box = tuple(round(v * scale) for v in box)
            crop = im.crop(full_box)
            if crop.width > 1920:
                crop = _scale_to_width(crop, 1920)
            out_name = f"{box_name}__{src_name}.png"
            crop.save(TILES_DIR / out_name)
            manifest["crops"].append({"file": out_name, "box_name": box_name, "source": src_name,
                                       "box_960": list(box), "box_full_res": list(full_box)})
    with open(TILES_DIR / "boxes.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"wrote {len(manifest['crops'])} tiles + boxes.json under {TILES_DIR.relative_to(ROOT)}/")

    return cycles_after_is_standin


def build_stations():
    STATIONS_DIR.mkdir(parents=True, exist_ok=True)
    col_w = 480
    for st in STATIONS:
        before = WEB / f"{BEFORE_GATE}_{st}.png"
        after = WEB / f"{AFTER_GATE}_{st}.png"
        if not before.exists() or not after.exists():
            print(f"skip {st}: missing {before if not before.exists() else after}")
            continue
        vb = _panel(_im(before), col_w,
                    [(f"BEFORE  {BEFORE_GATE}_{st}.png  ({_mtime(before)})", True), ("Phase 8 (final)", False)])
        va = _panel(_im(after), col_w,
                    [(f"AFTER  {AFTER_GATE}_{st}.png  ({_mtime(after)})", True), ("Phase 9", False)])
        row = _row([vb, va])
        header = _label_bar(row.width, [(f"Phase 9 before / after - station {st}", True)], height=26, bg=(0, 0, 0))
        sheet = _stack_rows([header, row])
        out_path = STATIONS_DIR / f"phase9_{st}_960.jpg"
        sheet.convert("RGB").save(out_path, quality=92)
        print(f"wrote {out_path.relative_to(ROOT)}  {sheet.size}")


def check_inputs():
    """List which input files exist and exit 0. No images read or written."""
    viewer_before = WEB / f"{BEFORE_GATE}_cam01.png"
    viewer_after = WEB / f"{AFTER_GATE}_cam01.png"
    candidates = [("viewer BEFORE", viewer_before), ("viewer AFTER", viewer_after),
                  ("cycles BEFORE", CYCLES_BEFORE), ("cycles AFTER", CYCLES_AFTER),
                  ("reference photo", REF169)]
    for st in STATIONS:
        candidates.append((f"viewer BEFORE {st}", WEB / f"{BEFORE_GATE}_{st}.png"))
        candidates.append((f"viewer AFTER {st}", WEB / f"{AFTER_GATE}_{st}.png"))
    for label, path in candidates:
        status = "OK" if path.exists() else "MISSING"
        print(f"{status:7s} {label:20s} {path}")
    return 0


if __name__ == "__main__":
    if "--after-gate" in sys.argv:
        i = sys.argv.index("--after-gate")
        if i + 1 >= len(sys.argv):
            sys.exit("--after-gate needs a value")
        AFTER_GATE = sys.argv[i + 1]
        del sys.argv[i:i + 2]

    if "--check" in sys.argv:
        sys.exit(check_inputs())
    elif "--stations" in sys.argv:
        build_stations()
    else:
        build_hero_sheet()
