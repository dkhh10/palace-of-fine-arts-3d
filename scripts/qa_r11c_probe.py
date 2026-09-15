#!/usr/bin/env python3
"""QA round 11c: pixel proof that no exported ENV_treeboard_* placeholder covers any Gate 1 frame.

The geometric probe (scripts/qa_r11b_probe.py boards) projects the quads and cannot know whether
they draw: it is an upper bound.  This compares the pixels under that mask in the round-11c capture
against the round-11b capture (git b828fa4^, the last one in which the boards drew) and measures
what is left of a flat grey slab.

    python3 scripts/qa_r11c_probe.py pixels  <old_dir>     # old_cam0K.png = the pre-fix frames
    python3 scripts/qa_r11c_probe.py slabs   [station]     # per-board flatness in the current frame
No Blender, no Chrome.
"""
import sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, "/Users/dk/Projects/3d render blender 3rd attempt building/scripts")
from qa_r11b_probe import nodes_of, cameras, project, ROOT, BOARD_PREFIX

GLTF_ENV = f"{ROOT}/export/out/gate1/env.gltf"


def board_quads(st, W, P, size):
    V = np.linalg.inv(W)
    out = []
    for name, M, lo, hi in nodes_of(GLTF_ENV, BOARD_PREFIX):
        corners = [(lo[0], lo[1], lo[2]), (hi[0], lo[1], lo[2]),
                   (hi[0], hi[1], hi[2]), (lo[0], hi[1], hi[2])]
        pts = project([(M @ np.array([*c, 1.0]))[:3] for c in corners], V, P, size)
        if pts:
            out.append((name, pts))
    return out


def mask_for(st, W, P, size, quads=None):
    img = Image.new("L", size, 0)
    d = ImageDraw.Draw(img)
    for _, pts in (quads if quads is not None else board_quads(st, W, P, size)):
        d.polygon(pts, fill=255)
    return np.asarray(img) > 0


def gray(path):
    return np.asarray(Image.open(path).convert("L"), dtype=np.int16)


def cmd_pixels(argv):
    old_dir = argv[0]
    print(f"{'st':>3} {'mask%':>6} {'chg>2%':>8} {'meanNOW':>8} {'meanOLD':>8} "
          f"{'sdNOW':>7} {'sdOLD':>7} {'identical%':>10}")
    for st, (W, P, size) in sorted(cameras().items()):
        m = mask_for(st, W, P, size)
        now = gray(f"{ROOT}/renders/web/gate1_cam{st:02d}.png")
        old = gray(f"{old_dir}/old_cam{st:02d}.png")
        if m.sum() == 0:
            print(f"{st:>3} {0.0:>6.1f}      --       --       --      --      --        --")
            continue
        dif = np.abs(now - old)
        chg = (dif[m] > 2).mean() * 100
        idt = (dif[m] == 0).mean() * 100
        print(f"{st:>3} {100*m.mean():>6.1f} {chg:>8.1f} {now[m].mean():>8.1f} "
              f"{old[m].mean():>8.1f} {now[m].std():>7.1f} {old[m].std():>7.1f} {idt:>10.1f}")


def cmd_slabs(argv):
    """A drawn opaque board is a near-constant patch: report the flattest board interiors."""
    sts = [int(argv[0])] if argv else sorted(cameras().keys())
    for st in sts:
        W, P, size = cameras()[st]
        now = gray(f"{ROOT}/renders/web/gate1_cam{st:02d}.png")
        rows = []
        for name, pts in board_quads(st, W, P, size):
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            x0, x1 = int(max(0, min(xs))), int(min(size[0], max(xs)))
            y0, y1 = int(max(0, min(ys))), int(min(size[1], max(ys)))
            if x1 - x0 < 24 or y1 - y0 < 24:
                continue
            patch = now[y0 + (y1-y0)//4: y1 - (y1-y0)//4, x0 + (x1-x0)//4: x1 - (x1-x0)//4]
            if patch.size:
                rows.append((float(patch.std()), name, (x1-x0)*(y1-y0), float(patch.mean())))
        rows.sort()
        print(f"station {st}: {len(rows)} boards >24 px; flattest interiors (std, mean):")
        for sd, name, area, mn in rows[:4]:
            print(f"   {name:22s} area {area:7d} px   std {sd:6.2f}   mean {mn:6.1f}")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("pixels", "slabs"):
        print(__doc__); sys.exit(2)
    (cmd_pixels if sys.argv[1] == "pixels" else cmd_slabs)(sys.argv[2:])
