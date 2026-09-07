#!/usr/bin/env python3
"""FOV-correct render-vs-photo comparison (architecture QA). python3 + ffmpeg only.

scripts/qa_compare.py letterboxes the reference by HEIGHT, which shrinks a 1.475:1 photo by 0.83 against a 16:9 render
and makes every width read ~20 % off. This tool instead scales the photo to the render's WIDTH (the QA cameras are
sensor_fit=HORIZONTAL, so equal width = equal horizontal field of view when the photo lens matches) and crops its height
so that the two horizons coincide.

  python3 scripts/arch_compare.py --render R.png --ref P.png --out X.png [--ref-horizon 0.68] [--render-horizon 0.802]
     -> render | photo (FOV-matched) | 50/50 blend

Horizon fractions are measured from the TOP. Render horizon for a level camera = 0.5 + shift_y * (W/H)
(cam 01: 0.5 + 0.17 * 16/9 = 0.802). Reference horizon for cam_01_lagoon_hero.png: 0.68 (reference sheet section 8).
"""
import argparse, subprocess, json, sys
from pathlib import Path


def size(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                   "-of", "json", str(path)])
    s = json.loads(out)["streams"][0]
    return int(s["width"]), int(s["height"])


def compare(render, ref, out, ref_h=0.68, ren_h=0.802, zoom=1.0):
    """zoom > 1 enlarges the photo about its centre column and its horizon (equivalent to a longer photo lens)."""
    wr, hr = size(render)
    wp, hp = size(ref)
    scale = wr / wp * zoom
    wp_s, hp_s = int(round(wp * scale)), int(round(hp * scale))
    xoff = max(0, (wp_s - wr) // 2)
    # crop offset (in scaled photo pixels) so that the horizons coincide
    off = int(round(ref_h * hp_s - ren_h * hr))
    off = max(0, min(off, hp_s - hr))
    ch = min(hr, hp_s)
    chain = f"scale={wp_s}:{hp_s},crop={min(wr, wp_s)}:{ch}:{xoff}:{off},pad={wr}:{hr}:0:0:color=black,setsar=1"
    fc = (f"[1:v]{chain}[ref];"
          f"[0:v]setsar=1[ren];[ren][ref]blend=all_mode=average[blend];"
          f"[0:v]setsar=1[r2];[1:v]{chain}[ref2];"
          f"[r2][ref2][blend]hstack=inputs=3[stack]")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", str(render), "-i", str(ref), "-filter_complex", fc,
                           "-map", "[stack]", "-frames:v", "1", str(out)])
    print("wrote", out, f"(photo scaled {scale:.3f}, crop offset {off}px)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", required=True)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ref-horizon", type=float, default=0.68)
    ap.add_argument("--render-horizon", type=float, default=0.802)
    ap.add_argument("--ref-zoom", type=float, default=1.0, help="enlarge the photo (1.2 = as if shot with a 20%% longer lens)")
    a = ap.parse_args()
    compare(a.render, a.ref, a.out, a.ref_horizon, a.render_horizon, a.ref_zoom)
