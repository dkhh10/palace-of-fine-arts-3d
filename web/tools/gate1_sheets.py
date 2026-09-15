#!/usr/bin/env python3
"""Gate 1 pair sheets: the three.js viewer against the Phase 5 QA render, station by station.

    python3 web/tools/gate1_sheets.py --viewer-glob 'renders/web/gate1_cam%02d.png' \
        --out-dir renders/web [--stations 1-6] [--tiles 1] [--panel-width 1280]

Per station it writes  renders/web/gate1_pair_cam0N.png  =  viewer | Phase 5 render | 50 % blend,
and a sidecar <name>.json with, for the whole frame and for a 4 x 3 grid of cells:
  - mean display luma (0-255 Rec.709) and mean linear luminance after sRGB decode, per frame,
  - the viewer-minus-reference delta and the linear ratio,
so the QA critic has a number per region instead of an impression.  For cam01 it also cuts the SIX
100 % TILES (3 across x 2 down) of the viewer frame and of the reference, side by side, into
<out-dir>/tiles/ (gitignored) at full resolution for the tile review.

References (defaults, overridable with --ref-N):
  cam01  renders/previews/qa/round10b_01_lagoon_hero_cycles.png   (round-10b Cycles hero, 1920x1080)
  cam02  renders/previews/qa/round09_02_lagoon_ne_threequarter_cycles.png
  cam03  renders/previews/qa/round09_03_colonnade_walk.png        (Eevee; no Cycles frame in round 09)
  cam04  renders/previews/qa/round09_04_rotunda_ceiling_cycles.png
  cam05  renders/previews/qa/round09_05_south_lawn.png            (Eevee)
  cam06  renders/previews/qa/round09_06_aerial_nocomp.png
A reference is resized to the panel width; the viewer frame is the authority on framing, so both
panels are shown at the same size and the blend is computed there.  Sizes and sources are recorded
in the sidecar: an Eevee reference is labelled as such on the sheet, because it is not a parity target.
"""
import argparse, json, os, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float64)

DEFAULT_REFS = {
    1: ("renders/previews/qa/round10b_01_lagoon_hero_cycles.png", "Cycles round-10b hero"),
    2: ("renders/previews/qa/round09_02_lagoon_ne_threequarter_cycles.png", "Cycles round-09"),
    3: ("renders/previews/qa/round09_03_colonnade_walk.png", "Eevee round-09 (no Cycles frame)"),
    4: ("renders/previews/qa/round09_04_rotunda_ceiling_cycles.png", "Cycles round-09"),
    5: ("renders/previews/qa/round09_05_south_lawn.png", "Eevee round-09 (no Cycles frame)"),
    6: ("renders/previews/qa/round09_06_aerial_nocomp.png", "Cycles round-09, no compositor"),
}
MAIN_ROOT = os.environ.get("PFA_MAIN_ROOT", "")


def resolve(path):
    """Reference renders live in the MAIN checkout only (round-10b is untracked there); a worktree
    has the round-09 set but not the round-10 ones.  Try the path as given, then $PFA_MAIN_ROOT."""
    p = Path(path)
    if p.exists() or not MAIN_ROOT:
        return p
    alt = Path(MAIN_ROOT) / path
    return alt if alt.exists() else p


STATION_NAMES = {1: "cam01 lagoon hero", 2: "cam02 lagoon NE three-quarter", 3: "cam03 colonnade walk",
                 4: "cam04 rotunda ceiling", 5: "cam05 south lawn", 6: "cam06 aerial"}


def srgb_to_linear(x):
    x = x / 255.0
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def parse_stations(spec):
    out = []
    for part in str(spec).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-")
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return [n for n in dict.fromkeys(out) if 1 <= n <= 6]


def grid_stats(A, B, rows=3, cols=4):
    """Per-cell luma / linear means and the viewer-vs-reference delta."""
    H, W = A.shape[:2]
    cells = []
    for r in range(rows):
        for c in range(cols):
            y0, y1 = r * H // rows, (r + 1) * H // rows
            x0, x1 = c * W // cols, (c + 1) * W // cols
            a, b = A[y0:y1, x0:x1].astype(np.float64), B[y0:y1, x0:x1].astype(np.float64)
            la, lb = float((a @ LUMA).mean()), float((b @ LUMA).mean())
            na, nb = float((srgb_to_linear(a) @ LUMA).mean()), float((srgb_to_linear(b) @ LUMA).mean())
            cells.append({"cell": [r, c], "box": [x0, y0, x1, y1],
                          "reference_luma": round(la, 2), "viewer_luma": round(lb, 2),
                          "delta_luma": round(lb - la, 2),
                          "ratio_linear": round(nb / na, 4) if na > 1e-9 else None})
    return cells


def frame_stats(A, B):
    a, b = A.astype(np.float64), B.astype(np.float64)
    la, lb = (a @ LUMA), (b @ LUMA)
    na, nb = (srgb_to_linear(a) @ LUMA), (srgb_to_linear(b) @ LUMA)
    return {"reference_luma": round(float(la.mean()), 2), "viewer_luma": round(float(lb.mean()), 2),
            "delta_luma": round(float(lb.mean() - la.mean()), 2),
            "ratio_linear": round(float(nb.mean() / na.mean()), 4) if na.mean() > 1e-9 else None,
            "mean_abs_diff_255": round(float(np.abs(a - b).mean()), 2),
            "rms_diff_255": round(float(np.sqrt(((a - b) ** 2).mean())), 2)}


def label_bar(img, text, height=26):
    out = Image.new("RGB", (img.width, img.height + height), (18, 18, 20))
    out.paste(img, (0, height))
    ImageDraw.Draw(out).text((6, 7), text, fill=(230, 226, 216))
    return out


def make_sheet(viewer_png, ref_png, ref_label, out_png, panel_w, station):
    v = Image.open(viewer_png).convert("RGB")
    r = Image.open(ref_png).convert("RGB")
    vs = v.size
    ph = max(1, round(panel_w * v.height / v.width))
    vp = v.resize((panel_w, ph), Image.LANCZOS) if v.size != (panel_w, ph) else v
    rp = r.resize((panel_w, ph), Image.LANCZOS) if r.size != (panel_w, ph) else r
    blend = Image.blend(rp, vp, 0.5)

    A, B = np.asarray(rp), np.asarray(vp)
    res = {"station": station, "station_name": STATION_NAMES.get(station),
           "viewer": {"path": str(viewer_png), "size": list(vs)},
           "reference": {"path": str(ref_png), "size": list(r.size), "label": ref_label},
           "panel_size": [panel_w, ph],
           "frame": frame_stats(A, B), "cells_3x4": grid_stats(A, B)}

    pad = 8
    panels = [(vp, f"three.js viewer  {vs[0]}x{vs[1]}"),
              (rp, f"reference: {ref_label}  {r.size[0]}x{r.size[1]}"),
              (blend, "50 % blend")]
    labelled = [label_bar(p, t) for p, t in panels]
    W = sum(p.width for p in labelled) + pad * (len(labelled) + 1)
    H = max(p.height for p in labelled) + pad * 2
    sheet = Image.new("RGB", (W, H), (18, 18, 20))
    x = pad
    for p in labelled:
        sheet.paste(p, (x, pad)); x += p.width + pad
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png)
    Path(str(out_png) + ".json").write_text(json.dumps(res, indent=1))
    return res, sheet.size


def make_tiles(viewer_png, ref_png, out_dir, cols=3, rows=2):
    """Six 100 % tiles of the viewer frame, each paired with the same crop of the reference."""
    v = Image.open(viewer_png).convert("RGB")
    r = Image.open(ref_png).convert("RGB")
    if r.size != v.size:
        r = r.resize(v.size, Image.LANCZOS)
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for j in range(rows):
        for i in range(cols):
            box = (i * v.width // cols, j * v.height // rows,
                   (i + 1) * v.width // cols, (j + 1) * v.height // rows)
            vt, rt = v.crop(box), r.crop(box)
            pair = Image.new("RGB", (vt.width * 2 + 24, vt.height + 34), (18, 18, 20))
            pair.paste(vt, (8, 26)); pair.paste(rt, (vt.width + 16, 26))
            d = ImageDraw.Draw(pair)
            d.text((10, 7), f"viewer  tile r{j+1}c{i+1}  {box}", fill=(230, 226, 216))
            d.text((vt.width + 18, 7), "reference", fill=(230, 226, 216))
            f = out_dir / f"gate1_cam01_tile_r{j+1}c{i+1}.png"
            pair.save(f)
            written.append(str(f))
    return written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--viewer-glob", default="renders/web/gate1_cam%02d.png",
                    help="printf pattern for the viewer PNG of station N")
    ap.add_argument("--out-dir", default="renders/web")
    ap.add_argument("--stations", default="1-6")
    ap.add_argument("--panel-width", type=int, default=1280)
    ap.add_argument("--tiles", default="1", help="0 to skip the cam01 100 % tiles")
    ap.add_argument("--tile-dir", default=None, help="default <out-dir>/tiles (gitignored)")
    for n in range(1, 7):
        ap.add_argument(f"--ref-{n}", default=None)
    a = ap.parse_args()

    out_dir = Path(a.out_dir)
    summary, missing = [], []
    for n in parse_stations(a.stations):
        viewer = Path(a.viewer_glob % n)
        ref_arg = getattr(a, f"ref_{n}")
        ref_path, ref_label = (resolve(ref_arg), "override " + Path(ref_arg).name) if ref_arg \
            else (resolve(DEFAULT_REFS[n][0]), DEFAULT_REFS[n][1])
        if not viewer.exists():
            missing.append(f"station {n}: no viewer frame at {viewer}")
            continue
        if not ref_path.exists():
            missing.append(f"station {n}: no reference at {ref_path}")
            continue
        out_png = out_dir / f"gate1_pair_cam{n:02d}.png"
        res, size = make_sheet(viewer, ref_path, ref_label, out_png, a.panel_width, n)
        f = res["frame"]
        print(f"[gate1_sheets] cam{n:02d} -> {out_png} {size[0]}x{size[1]}  "
              f"luma viewer {f['viewer_luma']} vs ref {f['reference_luma']} "
              f"(delta {f['delta_luma']}, linear x{f['ratio_linear']}), mean|diff| {f['mean_abs_diff_255']}/255")
        summary.append(res)
        if n == 1 and a.tiles != "0":
            tiles = make_tiles(viewer, ref_path, a.tile_dir or (out_dir / "tiles"))
            print(f"[gate1_sheets] {len(tiles)} cam01 100 % tiles -> {Path(tiles[0]).parent}")
    idx = out_dir / "gate1_pairs.json"
    idx.write_text(json.dumps({"sheets": summary, "missing": missing}, indent=1))
    for m in missing:
        print(f"[gate1_sheets] MISSING {m}", file=sys.stderr)
    print(f"[gate1_sheets] wrote {idx} ({len(summary)} sheets, {len(missing)} missing)")
    return 0 if summary else 1


if __name__ == "__main__":
    sys.exit(main())
