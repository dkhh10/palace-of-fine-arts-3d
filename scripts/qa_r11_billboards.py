#!/usr/bin/env python3
"""QA round 11 — project the viewer's far-tree PLACEHOLDER billboards into any QA station frame.

No Blender, no Chrome. Inputs: export/out/gate1/export_set.json (`tree_far_list`: trunk_base in Blender
world metres, height_m, width_m) and export/out/gate1/manifest.json (`stations.<name>`: location,
rotation_euler_xyz, lens_mm, sensor_width_mm, sensor_fit, shift_x/y). Each far tree is drawn by the viewer
as one flat quad, camera-facing about world +Z, `userData.pfaPlaceholder = 'gate3_tree_impostor'`
(web/README.md "Far-tree billboards"), so its screen coverage is exactly reconstructible.

Validated against ground truth: for station 1 this camera reproduces the three.js world/projection matrices
the viewer logged in renders/web/gate1_cam.json to 0.03 % of frame area (16.13 % vs 16.16 %).

    python3 scripts/qa_r11_billboards.py [--station N ...] [--box x0 y0 x1 y1 ...] [--overlay out.png]

Coverage is the projected quad area BEFORE the depth test, i.e. the upper bound on what the placeholders hide.
"""
import argparse, json, math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
STATIONS = ["CAM_qa_01_lagoon_hero", "CAM_qa_02_lagoon_ne_threequarter", "CAM_qa_03_colonnade_walk",
            "CAM_qa_04_rotunda_ceiling", "CAM_qa_05_south_lawn", "CAM_qa_06_aerial"]


def euler_xyz(e):
    x, y, z = e
    rx = np.array([[1, 0, 0], [0, math.cos(x), -math.sin(x)], [0, math.sin(x), math.cos(x)]])
    ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]])
    rz = np.array([[math.cos(z), -math.sin(z), 0], [math.sin(z), math.cos(z), 0], [0, 0, 1]])
    return rz @ ry @ rx


def mask_for(station, trees, w, h):
    rot = euler_xyz(station["rotation_euler_xyz"])
    loc = np.array(station["location"], dtype=float)
    aspect = w / h
    th_x = station["sensor_width_mm"] / (2 * station["lens_mm"])
    if station.get("sensor_fit") == "VERTICAL":
        th_x, th_y = th_x * aspect, th_x
    else:
        th_y = th_x / aspect
    sx, sy = 2 * station.get("shift_x", 0.0), 2 * station.get("shift_y", 0.0) * aspect
    right = rot[:, 0].copy()
    right[2] = 0.0
    right /= np.linalg.norm(right)
    up = np.array([0.0, 0.0, 1.0])

    img = Image.new("1", (w, h), 0)
    draw = ImageDraw.Draw(img)
    drawn = 0
    for t in trees:
        base = np.array(t["trunk_base"], dtype=float)
        pts = []
        for a, b in ((-1, 0), (1, 0), (1, 1), (-1, 1)):
            p = base + right * (a * t["width_m"] / 2) + up * (b * t["height_m"])
            pc = rot.T @ (p - loc)
            if -pc[2] <= 0.01:
                pts = []
                break
            pts.append((((pc[0] / -pc[2]) / th_x - sx + 1) * 0.5 * w,
                        (1 - ((pc[1] / -pc[2]) / th_y - sy)) * 0.5 * h))
        if len(pts) == 4:
            draw.polygon(pts, fill=1)
            drawn += 1
    return np.asarray(img, dtype=bool), drawn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default=str(ROOT / "export/out/gate1/export_set.json"))
    ap.add_argument("--manifest", default=str(ROOT / "export/out/gate1/manifest.json"))
    ap.add_argument("--station", type=int, action="append", default=[])
    ap.add_argument("--size", type=int, nargs=2, default=[1920, 1080])
    ap.add_argument("--box", type=int, nargs=4, action="append", default=[])
    ap.add_argument("--overlay", default=None, help="write <overlay> with the mask tinted over the frame")
    ap.add_argument("--frame", default=str(ROOT / "renders/web/gate1_cam%02d.png"))
    a = ap.parse_args()

    trees = json.loads(Path(a.set).read_text())["tree_far_list"]
    stations = json.loads(Path(a.manifest).read_text())["stations"]
    w, h = a.size
    out = {"billboards": len(trees), "stations": []}
    for n in (a.station or [1, 2, 3, 4, 5, 6]):
        m, drawn = mask_for(stations[STATIONS[n - 1]], trees, w, h)
        row = {"station": n, "projected": drawn, "frame_coverage_pct": round(100 * m.mean(), 2),
               "boxes": [{"box": b, "coverage_pct": round(100 * m[b[1]:b[3], b[0]:b[2]].mean(), 2)}
                         for b in a.box]}
        out["stations"].append(row)
        if a.overlay:
            base = np.asarray(Image.open(a.frame % n).convert("RGB")).astype(float)
            base[m] = base[m] * 0.45 + np.array([255, 40, 40]) * 0.55
            p = a.overlay % n if "%" in a.overlay else a.overlay
            Image.fromarray(base.astype("uint8")).save(p)
            row["overlay"] = p
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
