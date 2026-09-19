"""CPU-only coverage probe for Phase 8d (no bpy, no GPU).

Rasterises the Gate 1 export (`export/out/gate1/*.gltf` + `.bin`, the UNPACKED pair, which still
carries object names) through the six `scripts/qa_cameras.py` stations with a numpy z-buffer and
reports how many pixels each ENV backdrop group actually owns at the delivery framing.

Why this and not a render: the backdrop work has to go where the pixels are, and Blender/Chrome are
both forbidden while another agent holds the GPU.  The geometry, the transforms and the camera model
are identical to what the viewer draws (Blender lens/shift model, `web/src/blenderCamera.js`), so the
numbers are the viewer's own coverage up to the viewer-only effects listed under CAVEATS.

CAVEATS (each measured or bounded, never guessed):
  * impostor billboards are drawn at their authored orientation, not camera-facing; they are far trees
    and only ever *add* occlusion of the backdrop, so backdrop shares here are upper bounds by that
    amount (reported separately as the `far_impostor` class).
  * the lagoon water plane is not in any glb (the viewer builds it); it is added here as a quad at
    common.WATER_Z over the lagoon extent so the backdrop is not credited with water pixels.
  * alpha is ignored: leaf cards and impostor quads occlude as solid.  That makes tree-occluded
    backdrop shares conservative (the real viewer shows *more* backdrop through the leaf gaps).

usage:  python3 scripts/env_probe_backdrop.py [--w 960] [--out docs/briefs/phase8d_probe.json] [--png DIR]
"""
import json, struct, math, sys, os, argparse
import numpy as np

MAIN = os.environ.get("PFA_MAIN_ROOT", "/Users/dk/Projects/3d render blender 3rd attempt building")
GATE1 = os.path.join(MAIN, "export", "out", "gate1")
WATER_Z = -1.3

# name, loc, target, lens, shift_y  (copied from scripts/qa_cameras.py; asserted against it at run time)
STATIONS = [
    ("cam01", (-14.1, 100.0, 1.3), (0.0, 0.0, 1.3), 20.0, 0.06),
    ("cam02", (-79.8, 24.4, 1.55), (0.0, 0.0, 23.5), 27.0, 0.0),
    ("cam03", (81.0, 12.04, 1.7), (0.0, 0.0, 9.2), 18.0, 0.0),
    ("cam04", (0.0, 3.0, 1.6), (0.0, 3.0, 40.0), 15.0, 0.0),
    ("cam05", (28.1, 111.8, 1.5), (0.0, 0.0, 21.5), 35.0, 0.0),
    ("cam06", (-205.0, 143.0, 120.0), (0.0, 0.0, 15.0), 50.0, 0.0),
]

CT = {5120: "<i1", 5121: "<u1", 5122: "<i2", 5123: "<u2", 5125: "<u4", 5126: "<f4"}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


# --------------------------------------------------------------------------- gltf
def load(path):
    doc = json.load(open(path))
    buf = doc["buffers"][0]
    bin_path = os.path.join(os.path.dirname(path), buf["uri"])
    return doc, np.fromfile(bin_path, dtype=np.uint8)


def acc(doc, blob, i):
    a = doc["accessors"][i]
    bv = doc["bufferViews"][a["bufferView"]]
    dt = np.dtype(CT[a["componentType"]])
    n = NC[a["type"]]
    off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = bv.get("byteStride") or dt.itemsize * n
    cnt = a["count"]
    if stride == dt.itemsize * n:
        out = blob[off:off + cnt * stride].view(dt).reshape(cnt, n)
    else:
        raw = blob[off:off + (cnt - 1) * stride + dt.itemsize * n]
        out = np.lib.stride_tricks.as_strided(raw.view(dt), (cnt, n), (stride, dt.itemsize))
    return np.asarray(out, dtype=np.float32 if dt.kind == "f" else np.int64)


def node_matrix(n):
    if "matrix" in n:
        return np.array(n["matrix"], dtype=np.float64).reshape(4, 4).T
    m = np.eye(4)
    if "rotation" in n:
        x, y, z, w = n["rotation"]
        m[:3, :3] = np.array([
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    if "scale" in n:
        m[:3, :3] = m[:3, :3] @ np.diag(n["scale"])
    if "translation" in n:
        m[:3, 3] = n["translation"]
    return m


def prims(path, label_of):
    """-> list of (label, verts_blender(n,3) float32, tris(m,3) int64)"""
    doc, blob = load(path)
    out = []
    cache = {}
    for ni, n in enumerate(doc["nodes"]):
        if "mesh" not in n:
            continue
        lbl = label_of(n.get("name", ""), doc["meshes"][n["mesh"]].get("name", ""))
        if lbl is None:
            continue
        M = node_matrix(n)
        for pi, p in enumerate(doc["meshes"][n["mesh"]]["primitives"]):
            key = (n["mesh"], pi)
            if key not in cache:
                v = acc(doc, blob, p["attributes"]["POSITION"]).astype(np.float64)
                idx = acc(doc, blob, p["indices"]).reshape(-1, 3).astype(np.int64)
                cache[key] = (v, idx)
            v, idx = cache[key]
            w = v @ M[:3, :3].T + M[:3, 3]
            # glTF Y-up -> Blender Z-up
            b = np.stack([w[:, 0], -w[:, 2], w[:, 1]], axis=1).astype(np.float32)
            out.append((lbl, b, idx))
    return out


# --------------------------------------------------------------------------- camera
def cam_basis(loc, target):
    f = np.array(target, float) - np.array(loc, float)
    f /= np.linalg.norm(f)
    zc = -f
    up = np.array([0.0, 0.0, 1.0])
    xc = np.cross(f, up)
    if np.linalg.norm(xc) < 1e-9:
        xc = np.array([1.0, 0.0, 0.0])
    xc /= np.linalg.norm(xc)
    yc = np.cross(zc, xc)
    return np.stack([xc, yc, zc])          # rows = camera axes in world


def project(V, loc, R, lens, shift_y, W, H):
    c = (V - np.array(loc, np.float32)) @ R.T.astype(np.float32)
    z = c[:, 2]
    half_w = 18.0 / lens                   # tan(hfov/2) with a 36 mm horizontal sensor
    aspect = W / H
    ndc_x = (c[:, 0] / -z) / half_w
    ndc_y = (c[:, 1] / -z) / (half_w / aspect) - 2.0 * shift_y * aspect
    sx = (ndc_x * 0.5 + 0.5) * W
    sy = (0.5 - ndc_y * 0.5) * H
    return sx, sy, z


def raster(parts, loc, target, lens, shift_y, W, H, near=0.25):
    R = cam_basis(loc, target)
    labels = sorted({p[0] for p in parts})
    lut = {l: i for i, l in enumerate(labels)}
    zbuf = np.zeros(W * H, dtype=np.uint64)
    idbuf = np.full(W * H, -1, dtype=np.int32)

    for lbl, V, T in parts:
        sx, sy, z = project(V, loc, R, lens, shift_y, W, H)
        keep = z[T].max(axis=1) < -near               # all three in front (clipper below handles the rest)
        straddle = (z[T].min(axis=1) < -near) & ~keep
        tris = [T[keep]]
        if straddle.any():                            # near-plane clip, few triangles, python loop
            extra = []
            for t in T[straddle]:
                poly = [V[i] for i in t]
                cz = [(V[i] - loc) @ R[2] for i in t]
                cl = []
                for i in range(3):
                    a, b = i, (i + 1) % 3
                    ina, inb = cz[a] < -near, cz[b] < -near
                    if ina:
                        cl.append(poly[a])
                    if ina != inb:
                        t01 = (-near - cz[a]) / (cz[b] - cz[a])
                        cl.append(poly[a] + t01 * (poly[b] - poly[a]))
                if len(cl) >= 3:
                    base = len(V)
                    V = np.vstack([V, np.array(cl, np.float32)])
                    for k in range(1, len(cl) - 1):
                        extra.append([base, base + k, base + k + 1])
            if extra:
                sx, sy, z = project(V, loc, R, lens, shift_y, W, H)
                tris.append(np.array(extra, np.int64))
        T2 = np.vstack([t for t in tris if len(t)]) if any(len(t) for t in tris) else None
        if T2 is None or not len(T2):
            continue
        _draw(T2, sx, sy, z, lut[lbl], zbuf, idbuf, W, H)
    return idbuf.reshape(H, W), labels


def _draw(T, sx, sy, z, lid, zbuf, idbuf, W, H):
    x0, x1, x2 = sx[T[:, 0]], sx[T[:, 1]], sx[T[:, 2]]
    y0, y1, y2 = sy[T[:, 0]], sy[T[:, 1]], sy[T[:, 2]]
    w0, w1, w2 = -1.0 / z[T[:, 0]], -1.0 / z[T[:, 1]], -1.0 / z[T[:, 2]]
    area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
    live = np.abs(area) > 1e-9
    bx0 = np.maximum(np.floor(np.minimum(np.minimum(x0, x1), x2)), 0).astype(np.int64)
    bx1 = np.minimum(np.ceil(np.maximum(np.maximum(x0, x1), x2)), W - 1).astype(np.int64)
    by0 = np.maximum(np.floor(np.minimum(np.minimum(y0, y1), y2)), 0).astype(np.int64)
    by1 = np.minimum(np.ceil(np.maximum(np.maximum(y0, y1), y2)), H - 1).astype(np.int64)
    live &= (bx1 >= bx0) & (by1 >= by0)
    if not live.any():
        return
    sel = np.nonzero(live)[0]
    bw = (bx1 - bx0 + 1)[sel]
    bh = (by1 - by0 + 1)[sel]
    k = np.maximum(bw, bh)
    bucket = np.maximum(1, 1 << np.ceil(np.log2(np.maximum(k, 1))).astype(np.int64))
    for bk in np.unique(bucket):
        ids = sel[bucket == bk]
        step = max(1, int(4_000_000 // (bk * bk)))
        for s in range(0, len(ids), step):
            ch = ids[s:s + step]
            oy, ox = np.meshgrid(np.arange(bk), np.arange(bk), indexing="ij")
            px = bx0[ch][:, None] + ox.ravel()[None, :]
            py = by0[ch][:, None] + oy.ravel()[None, :]
            ok = (px <= bx1[ch][:, None]) & (py <= by1[ch][:, None])
            cx = px + 0.5
            cy = py + 0.5
            ax, ay = x0[ch][:, None], y0[ch][:, None]
            e0 = (x1[ch][:, None] - ax) * (cy - ay) - (y1[ch][:, None] - ay) * (cx - ax)
            e1 = (x2[ch][:, None] - x1[ch][:, None]) * (cy - y1[ch][:, None]) - \
                 (y2[ch][:, None] - y1[ch][:, None]) * (cx - x1[ch][:, None])
            e2 = (ax - x2[ch][:, None]) * (cy - y2[ch][:, None]) - \
                 (ay - y2[ch][:, None]) * (cx - x2[ch][:, None])
            ar = area[ch][:, None]
            inside = ok & (((e0 >= 0) & (e1 >= 0) & (e2 >= 0)) | ((e0 <= 0) & (e1 <= 0) & (e2 <= 0)))
            if not inside.any():
                continue
            l0 = e1 / ar
            l1 = e2 / ar
            l2 = 1.0 - l0 - l1
            wv = l0 * w0[ch][:, None] + l1 * w1[ch][:, None] + l2 * w2[ch][:, None]
            pix = (py * W + px)[inside]
            q = np.clip(wv[inside] * 4.0e8, 0, 4.2e9).astype(np.uint64)
            np.maximum.at(zbuf, pix, q)
            hit = zbuf[pix] == q
            idbuf[pix[hit]] = lid


def water_quad():
    r = 900.0
    V = np.array([[-r, -r, WATER_Z], [r, -r, WATER_Z], [r, r, WATER_Z], [-r, r, WATER_Z]], np.float32)
    return ("water_plane", V, np.array([[0, 1, 2], [0, 2, 3]], np.int64))


def env_label(node, mesh):
    if node.startswith("ENV_backdropgroup_"):
        return "bd:" + node[len("ENV_backdropgroup_"):]
    if "treeboard" in mesh:
        return "far_impostor"
    if node.startswith("ENV_tree"):
        return "near_tree"
    if node.startswith("ENV_shrub"):
        return "shrub"
    return "env_other"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--w", type=int, default=960)
    ap.add_argument("--out", default=os.path.join(MAIN, "export", "out", "phase8d_probe.json"))
    ap.add_argument("--png", default="")
    ap.add_argument("--skip", default="", help="comma list of labels to drop (e.g. far_impostor,near_tree,shrub)")
    a = ap.parse_args()
    W, H = a.w, int(a.w * 9 / 16)

    parts = []
    parts += prims(os.path.join(GATE1, "env.gltf"), env_label)
    parts += prims(os.path.join(GATE1, "arch.gltf"), lambda n, m: "arch")
    parts += prims(os.path.join(GATE1, "ground.gltf"), lambda n, m: "ground")
    parts += prims(os.path.join(GATE1, "orn.gltf"), lambda n, m: "orn")
    parts.append(water_quad())
    if a.skip:
        drop = set(a.skip.split(","))
        parts = [p for p in parts if p[0] not in drop]
    print(f"[probe] {len(parts)} primitives, {sum(len(t) for _, _, t in parts):,} triangles", flush=True)

    res = {}
    for name, loc, target, lens, shift_y in STATIONS:
        idm, labels = raster(parts, loc, target, lens, shift_y, W, H)
        tot = W * H
        counts = {}
        for i, l in enumerate(labels):
            c = int((idm == i).sum())
            if c:
                counts[l] = c
        counts["sky"] = int((idm < 0).sum())
        tiles = {}
        for r in range(2):
            for c in range(3):
                sub = idm[r * (H // 2):(r + 1) * (H // 2), c * (W // 3):(c + 1) * (W // 3)]
                n = 0
                for i, l in enumerate(labels):
                    if l.startswith("bd:"):
                        n += int((sub == i).sum())
                tiles[f"r{r+1}c{c+1}"] = n
        boxes = {}
        for i, l in enumerate(labels):
            if not l.startswith("bd:"):
                continue
            ys, xs = np.nonzero(idm == i)
            if len(xs):
                k = 1920.0 / W
                boxes[l] = [int(xs.min() * k), int(ys.min() * k), int(xs.max() * k), int(ys.max() * k),
                            int(len(xs) * k * k)]
        res[name] = {"w": W, "h": H, "total": tot, "counts": counts, "bd_tiles": tiles,
                     "bd_boxes_1920": boxes,
                     "backdrop_px": sum(v for k, v in counts.items() if k.startswith("bd:")),
                     "backdrop_pct": round(100.0 * sum(v for k, v in counts.items() if k.startswith("bd:")) / tot, 3)}
        print(name, res[name]["backdrop_pct"], "%", {k: v for k, v in sorted(counts.items(), key=lambda x: -x[1])[:8]}, flush=True)
        if a.png:
            os.makedirs(a.png, exist_ok=True)
            from PIL import Image
            rng = np.random.default_rng(3)
            pal = (rng.random((len(labels) + 1, 3)) * 200 + 40).astype(np.uint8)
            for i, l in enumerate(labels):
                if l.startswith("bd:"):
                    pal[i] = [255, 40, 40]
                elif l in ("arch", "orn"):
                    pal[i] = [235, 235, 235]
                elif l == "water_plane":
                    pal[i] = [30, 70, 120]
            img = np.where((idm < 0)[..., None], np.array([120, 180, 240], np.uint8), pal[np.clip(idm, 0, None)])
            Image.fromarray(img.astype(np.uint8)).save(os.path.join(a.png, f"probe_{name}.png"))
    json.dump(res, open(a.out, "w"), indent=1)
    print("[probe] wrote", a.out)


if __name__ == "__main__":
    main()
