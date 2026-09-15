#!/usr/bin/env python3
"""QA round 11b: what the viewer actually draws at a pixel, and what the far-tree boards cover.

Everything here is read from the Gate 1 glTF files (node hierarchy + POSITION accessor min/max)
and the viewer's own logged camera matrices (renders/web/gate1_cam.json, `info` + the per-station
`pageLog` lines).  No Blender, no Chrome.

    python3 scripts/qa_r11b_probe.py probe  <station> x,y [x,y ...]
        every mesh whose projected world AABB contains the pixel, nearest first -> what a slab is.
    python3 scripts/qa_r11b_probe.py boards [--mask-dir DIR] [--box st x0 y0 x1 y1]
        per-station screen coverage of the 127 exported ENV_treeboard_* quads (the far-tree
        placeholders that live in env.glb, NOT the viewer's WEB_far_tree_billboard_* quads that
        ?billboards=0 suppresses), projected exactly as quads.  Coverage is an upper bound: it is
        computed before the depth test.  --box also reports the coverage of one screen box, e.g.
        the cam01 main-arch opening.
"""
import json, re, sys
import numpy as np

ROOT = "/Users/dk/Projects/3d render blender 3rd attempt building"
GLTFS = ["arch", "orn", "env", "ground"]
BOARD_PREFIX = "ENV_treeboard"


def mat_of(node):
    if "matrix" in node:
        return np.array(node["matrix"], dtype=float).reshape(4, 4).T
    m = np.eye(4)
    if "rotation" in node:
        x, y, z, w = node["rotation"]
        m[:3, :3] = np.array([
            [1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
            [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
            [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
    if "scale" in node:
        m[:3, :3] = m[:3, :3] @ np.diag(node["scale"])
    if "translation" in node:
        m[:3, 3] = node["translation"]
    return m


def nodes_of(path, name_filter=None):
    g = json.load(open(path))
    out = []

    def rec(i, parent):
        n = g["nodes"][i]
        w = parent @ mat_of(n)
        if "mesh" in n and (name_filter is None or n.get("name", "").startswith(name_filter)):
            lo = np.array([1e30]*3); hi = np.array([-1e30]*3)
            for p in g["meshes"][n["mesh"]]["primitives"]:
                a = g["accessors"][p["attributes"]["POSITION"]]
                lo = np.minimum(lo, a["min"]); hi = np.maximum(hi, a["max"])
            out.append((n.get("name", "?"), w, lo, hi))
        for c in n.get("children", []):
            rec(c, w)
    for s in g["scenes"][g.get("scene", 0)]["nodes"]:
        rec(s, np.eye(4))
    return out


def cameras():
    """station -> (world, projection, (w, h)), from the viewer's own log."""
    cam = json.load(open(f"{ROOT}/renders/web/gate1_cam.json"))
    out = {}
    info = cam.get("info") or {}
    if info.get("cameraWorldMatrix"):
        st = info["station"]["index"] if isinstance(info["station"], dict) else int(info["station"])
        out[st] = (np.array(info["cameraWorldMatrix"], float).reshape(4, 4).T,
                   np.array(info["projectionMatrix"], float).reshape(4, 4).T, tuple(info["size"]))
    for line in cam.get("pageLog", []):
        m = re.match(r"log: \[pfa\] station (\d)", line)
        wm = re.search(r"world matrix\s+\[([^\]]+)\]", line)
        pj = re.search(r"projection\s+\[([^\]]+)\]", line)
        if m and wm and pj and int(m.group(1)) not in out:
            out[int(m.group(1))] = (
                np.array([float(x) for x in wm.group(1).split(",")]).reshape(4, 4).T,
                np.array([float(x) for x in pj.group(1).split(",")]).reshape(4, 4).T,
                tuple(cam.get("size", [1920, 1080])))
    return out


def project(pts, V, P, size):
    w, h = size
    out = []
    for c in pts:
        e = V @ np.array([c[0], c[1], c[2], 1.0])
        if -e[2] <= 0.05:
            return None
        cl = P @ e
        n = cl[:3] / cl[3]
        out.append(((n[0]*0.5+0.5)*w, (1-(n[1]*0.5+0.5))*h))
    return out


def cmd_probe(argv):
    st = int(argv[0])
    probes = [tuple(int(v) for v in a.split(",")) for a in argv[1:]]
    W, P, size = cameras()[st]
    V = np.linalg.inv(W)
    hits = {p: [] for p in probes}
    for cls in GLTFS:
        for name, M, lo, hi in nodes_of(f"{ROOT}/export/out/gate1/{cls}.gltf"):
            corners = np.array([[x, y, z, 1.0] for x in (lo[0], hi[0])
                                for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]).T
            eye = np.linalg.inv(W) @ (M @ corners)
            ok = -eye[2] > 0.05
            if not ok.any():
                continue
            clip = P @ eye[:, ok]
            ndc = clip[:3] / clip[3]
            xs = (ndc[0]*0.5+0.5)*size[0]
            ys = (1-(ndc[1]*0.5+0.5))*size[1]
            depth = float(np.min(-eye[2][ok]))
            for p in probes:
                if xs.min() <= p[0] <= xs.max() and ys.min() <= p[1] <= ys.max():
                    hits[p].append((depth, cls, name,
                                    (round(xs.min()), round(ys.min()), round(xs.max()), round(ys.max()))))
    for p in probes:
        print(f"\n== station {st} pixel {p} ==")
        for d, cls, name, box in sorted(hits[p])[:8]:
            print(f"  {d:8.1f} m  {cls:6s} {name[:58]:58s} aabb->{box}")


def cmd_boards(argv):
    from PIL import Image, ImageDraw
    mask_dir = None
    box = None
    if "--mask-dir" in argv:
        mask_dir = argv[argv.index("--mask-dir") + 1]
    if "--box" in argv:
        i = argv.index("--box")
        box = tuple(int(v) for v in argv[i+1:i+6])
    boards = nodes_of(f"{ROOT}/export/out/gate1/env.gltf", BOARD_PREFIX)
    print(f"[boards] {len(boards)} exported {BOARD_PREFIX}_* quads in env.gltf")
    for st, (W, P, size) in sorted(cameras().items()):
        V = np.linalg.inv(W)
        img = Image.new("L", size, 0)
        d = ImageDraw.Draw(img)
        for _, M, lo, hi in boards:
            corners = [(lo[0], lo[1], lo[2]), (hi[0], lo[1], lo[2]),
                       (hi[0], hi[1], hi[2]), (lo[0], hi[1], hi[2])]
            pts = project([(M @ np.array([*c, 1.0]))[:3] for c in corners], V, P, size)
            if pts:
                d.polygon(pts, fill=255)
        a = np.asarray(img) > 0
        line = f"station {st}: ENV_treeboard coverage {100*a.mean():5.1f}% of frame"
        if box and box[0] == st:
            sub = a[box[2]:box[4], box[1]:box[3]]
            line += f"   box {box[1:]}: {100*sub.mean():.1f}%"
        print(line)
        if mask_dir:
            Image.fromarray((a*255).astype("uint8")).save(f"{mask_dir}/boardmask{st}.png")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("probe", "boards"):
        print(__doc__)
        return 2
    (cmd_probe if sys.argv[1] == "probe" else cmd_boards)(sys.argv[2:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
