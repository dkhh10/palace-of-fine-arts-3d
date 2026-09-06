#!/usr/bin/env python3
"""Side-by-side comparison sheets for QA. Pure python3 + ffmpeg (no PIL needed).

  python3 scripts/qa_compare.py --render R.png --ref P.jpg --out renders/qa_comparisons/round01_cam01.png 
      -> 3 panels: render | reference | 50/50 blend, reference letterboxed to the render's aspect.
  python3 scripts/qa_compare.py --sheet renders/qa_comparisons/round01_sheet.png a.png b.png c.png ...
      -> grid contact sheet (2 columns) of the given panels.
"""
import argparse, subprocess, shlex, sys, os, json, math
from pathlib import Path

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"


def size(path):
    out = subprocess.check_output([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", str(path)])
    s = json.loads(out)["streams"][0]
    return int(s["width"]), int(s["height"])


def compare(render, ref, out, label=None):
    w, h = size(render)
    fc = (f"[1:v]scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1[ref];"
          f"[0:v]setsar=1[ren];[ren][ref]blend=all_mode=average[blend];"
          f"[0:v]setsar=1[r2];[1:v]scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1[ref2];"
          f"[r2][ref2][blend]hstack=inputs=3[stack]")
    outmap = "[stack]"   # (this ffmpeg build has no drawtext; put labels in the filename)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-i", str(render), "-i", str(ref), "-filter_complex", fc, "-map", outmap, "-frames:v", "1", str(out)]
    subprocess.check_call(cmd)
    print("wrote", out)


def sheet(out, panels, cols=2):
    n = len(panels)
    if n == 0:
        sys.exit("no panels")
    rows = math.ceil(n / cols)
    w, h = size(panels[0])
    tw = min(w, 1920)
    th = int(h * tw / w)
    inputs = []
    fc = ""
    for i, p in enumerate(panels):
        inputs += ["-i", str(p)]
        fc += f"[{i}:v]scale={tw}:{th}:force_original_aspect_ratio=decrease,pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1[p{i}];"
    # pad to full grid with black
    while len(panels) < rows * cols:
        i = len(panels)
        fc += f"color=black:s={tw}x{th}:d=1[p{i}];"
        panels = panels + [None]
    for r in range(rows):
        fc += "".join(f"[p{r * cols + c}]" for c in range(cols)) + f"hstack=inputs={cols}[row{r}];"
    fc += "".join(f"[row{r}]" for r in range(rows)) + (f"vstack=inputs={rows}[out]" if rows > 1 else "null[out]")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    cmd = [FFMPEG, "-y", "-loglevel", "error"] + inputs + ["-filter_complex", fc, "-map", "[out]", "-frames:v", "1", str(out)]
    subprocess.check_call(cmd)
    print("wrote", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--render"); ap.add_argument("--ref"); ap.add_argument("--out"); ap.add_argument("--label")
    ap.add_argument("--sheet"); ap.add_argument("panels", nargs="*")
    a = ap.parse_args()
    if a.sheet:
        sheet(a.sheet, a.panels)
    else:
        if not (a.render and a.ref and a.out):
            sys.exit(__doc__)
        compare(a.render, a.ref, a.out, a.label)
