#!/usr/bin/env python3
"""Phase 8c, item (a)+(b): texel density of the near-cam03 concrete, measured, READ-ONLY.

No Blender, no GPU. Reads the UNCOMPRESSED Gate 1 glTF (`export/out/gate1/*.gltf` + `.bin`, the
pre-gltfpack source of the shipped meshopt glb - same vertex data, plain float accessors), the
Gate 2 bake sidecars and the Gate 5 manifest, all from the MAIN checkout.

texels_per_m(mesh, map_px) = map_px * sqrt( sum(uv1 tri area) / sum(world tri area) )
    -- the UV1 atlas is the bake's packing, so this is exactly what a shading point gets.
pixels_per_m(camera, d)    = res_x * f / (sensor_w * d)      (36 mm horizontal sensor)

Usage:  python3 export/p8_texel_probe.py [--root <main checkout>] [--json out.json]
"""
import argparse, base64, json, math, os, struct, sys
import numpy as np

CTYPE = {5120: 'i1', 5121: 'u1', 5122: 'i2', 5123: 'u2', 5125: 'u4', 5126: 'f4'}
NCOMP = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}

# cam03 - Blender world, Z-up. READ FROM THE MANIFEST'S OWN `stations` BLOCK (`station()` below), which is
# what `scripts/qa_cameras.py` exported: this file used to carry a hand copy of that camera's numbers, and a
# hand copy of a camera the lead owns will drift (review r1 finding 3). The literal survives only as the
# fallback for a manifest too old to carry `stations`, and it says so when it is used.
CAM03_NAME = 'CAM_qa_03_colonnade_walk'
CAM03_FALLBACK = dict(name=CAM03_NAME, loc=(81.0, 12.04, 1.7), lens=18.0, sensor=36.0)
RES = (1920, 1080)


def station(man, name=CAM03_NAME, fallback=None):
    """The station as the export shipped it, else the literal above with a warning."""
    fallback = fallback or CAM03_FALLBACK
    st = ((man or {}).get('stations') or {}).get(name)
    if not st or 'location' not in st:
        print(f"[texel] WARNING: the manifest carries no stations[{name!r}]; falling back to this "
              f"script's hard-coded copy {fallback['loc']} / {fallback['lens']} mm, which may have drifted "
              f"from scripts/qa_cameras.py", file=sys.stderr)
        return dict(fallback, source='hard-coded fallback')
    return dict(name=name, loc=tuple(float(v) for v in st['location']),
                lens=float(st.get('lens_mm', fallback['lens'])),
                sensor=float(st.get('sensor_width_mm', fallback['sensor'])),
                source='manifest stations')


def blender_to_gltf(p):
    return (p[0], p[2], -p[1])


class Gltf:
    def __init__(self, path):
        self.dir = os.path.dirname(path)
        self.j = json.load(open(path))
        self.buffers = []
        for b in self.j['buffers']:
            uri = b.get('uri')
            if uri is None:
                raise RuntimeError('glb-embedded buffer: use the .gltf/.bin pair')
            if uri.startswith('data:'):
                self.buffers.append(base64.b64decode(uri.split(',', 1)[1]))
            else:
                self.buffers.append(open(os.path.join(self.dir, uri), 'rb').read())

    def accessor(self, i):
        a = self.j['accessors'][i]
        bv = self.j['bufferViews'][a['bufferView']]
        buf = self.buffers[bv.get('buffer', 0)]
        off = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
        n, comp = a['count'], NCOMP[a['type']]
        dt = np.dtype('<' + CTYPE[a['componentType']])
        stride = bv.get('byteStride') or comp * dt.itemsize
        if stride == comp * dt.itemsize:
            arr = np.frombuffer(buf, dtype=dt, count=n * comp, offset=off).reshape(n, comp)
        else:  # interleaved
            raw = np.frombuffer(buf, dtype=np.uint8, count=stride * n, offset=off).reshape(n, stride)
            arr = raw[:, :comp * dt.itemsize].copy().view(dt).reshape(n, comp)
        return arr.astype(np.float64) if a['componentType'] == 5126 else arr

    def node_matrices(self):
        """world 4x4 per node index (glTF Y-up)."""
        out = {}
        children = {i: n.get('children', []) for i, n in enumerate(self.j['nodes'])}
        roots = set(range(len(self.j['nodes']))) - {c for v in children.values() for c in v}
        for scene in self.j.get('scenes', []):
            roots |= set(scene.get('nodes', []))

        def local(n):
            if 'matrix' in n:
                return np.array(n['matrix'], dtype=np.float64).reshape(4, 4).T
            m = np.eye(4)
            t = n.get('translation', [0, 0, 0]); r = n.get('rotation', [0, 0, 0, 1]); s = n.get('scale', [1, 1, 1])
            x, y, z, w = r
            rot = np.array([
                [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
            m[:3, :3] = rot @ np.diag(s)
            m[:3, 3] = t
            return m

        stack = [(i, np.eye(4)) for i in sorted(roots)]
        while stack:
            i, par = stack.pop()
            w = par @ local(self.j['nodes'][i])
            out[i] = w
            for c in children.get(i, []):
                stack.append((c, w))
        return out


def mesh_density(g, mesh_idx, scale_vec):
    """(world_area_m2, uv1_area_uv2, tris) for a mesh at a world scale (x,y,z)."""
    wa = uva = 0.0
    tris = 0
    for prim in g.j['meshes'][mesh_idx]['primitives']:
        pos = g.accessor(prim['attributes']['POSITION']) * np.asarray(scale_vec)
        uv = g.accessor(prim['attributes']['TEXCOORD_0'])
        idx = g.accessor(prim['indices']).reshape(-1).astype(np.int64)
        a, b, c = pos[idx[0::3]], pos[idx[1::3]], pos[idx[2::3]]
        wa += 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1).sum()
        ua, ub, uc = uv[idx[0::3]], uv[idx[1::3]], uv[idx[2::3]]
        uva += 0.5 * np.abs((ub[:, 0] - ua[:, 0]) * (uc[:, 1] - ua[:, 1])
                            - (uc[:, 0] - ua[:, 0]) * (ub[:, 1] - ua[:, 1])).sum()
        tris += len(idx) // 3
    return wa, uva, tris


def uv_islands(g, mesh_idx, px):
    """UV1 islands after welding by UV position (so a normal-only vertex split is not counted
    as a seam).  Returns the per-island (width, height) in texels."""
    prim = g.j['meshes'][mesh_idx]['primitives'][0]
    uv = g.accessor(prim['attributes']['TEXCOORD_0'])
    idx = g.accessor(prim['indices']).reshape(-1).astype(np.int64)
    q = np.round(uv * px, 3)
    uniq, inv = np.unique(q, axis=0, return_inverse=True)
    parent = list(range(len(uniq)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for a, b, c in inv[idx].reshape(-1, 3):
        for x, y in ((a, b), (b, c)):
            ra, rb = find(x), find(y)
            if ra != rb:
                parent[ra] = rb
    groups = {}
    for i in range(len(uniq)):
        groups.setdefault(find(i), []).append(i)
    wh = []
    for v in groups.values():
        p = uniq[v]
        wh.append((p[:, 0].max() - p[:, 0].min(), p[:, 1].max() - p[:, 1].min()))
    return np.array(wh)


def detail_projection_density(g, mesh_idx, tile_m, px, mode='objxy'):
    """texels per metre the world-space tiling detail layer gives, along the world-vertical and the
    in-surface horizontal direction (web/src/detail.js pfaDetailUv).  `objxy` is the shipped default
    uv = (x, -z) / tile_m, `dominant` picks the axis plane most facing the surface."""
    prim = g.j['meshes'][mesh_idx]['primitives'][0]
    pos = g.accessor(prim['attributes']['POSITION'])
    idx = g.accessor(prim['indices']).reshape(-1).astype(np.int64)
    a, b, c = pos[idx[0::3]], pos[idx[1::3]], pos[idx[2::3]]
    n = np.cross(b - a, c - a)
    A2 = np.linalg.norm(n, axis=1)
    ok = A2 > 1e-12
    a, b, c, n, A2 = a[ok], b[ok], c[ok], n[ok], A2[ok]
    nn = n / A2[:, None]
    up = np.array([0., 1., 0.])                       # glTF Y-up = Blender +Z
    t_up = up - nn * (nn @ up)[:, None]
    L = np.linalg.norm(t_up, axis=1)
    good = L > 1e-3
    t_up = t_up / np.maximum(L, 1e-9)[:, None]
    t_h = np.cross(nn, t_up)
    k = px / float(tile_m)

    def grad(d):                                      # texels per metre along world dir d
        if mode == 'dominant':
            ax = np.abs(nn)
            pick = ax.argmax(1)                       # 0 -> (z,y), 1 -> (x,z), 2 -> (x,y)
            out = np.zeros(len(d))
            for p, cols in ((0, (2, 1)), (1, (0, 2)), (2, (0, 1))):
                m = pick == p
                out[m] = np.linalg.norm(d[m][:, cols], axis=1) * k
            return out
        return np.linalg.norm(d[:, (0, 2)], axis=1) * k   # uv = (x, -z)

    w = (A2 / 2)[good]
    tu, th = grad(t_up)[good], grad(t_h)[good]
    wa = lambda x: float((x * w).sum() / w.sum())
    return dict(mode=mode, tile_m=tile_m, px=px,
                texels_per_m_vertical=round(wa(tu), 2), texels_per_m_horizontal=round(wa(th), 2),
                mm_per_texel_vertical=round(1000.0 / wa(tu), 2) if wa(tu) > 1e-6 else None,
                mm_per_texel_horizontal=round(1000.0 / wa(th), 2) if wa(th) > 1e-6 else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=os.environ.get(
        'PFA_MAIN_ROOT', '/Users/dk/Projects/3d render blender 3rd attempt building'),
        help='the checkout to read export/out from (default $PFA_MAIN_ROOT, else the main checkout)')
    ap.add_argument('--radius', type=float, default=5.0)
    ap.add_argument('--json', default=None)
    args = ap.parse_args()
    R = args.root

    man = json.load(open(os.path.join(R, 'export/out/gate5/manifest.json')))
    sets = man['materials']['sets']
    CAM03 = station(man)
    cam = np.array(blender_to_gltf(CAM03['loc']))
    px_per_m_1m = RES[0] * CAM03['lens'] / CAM03['sensor']   # at d = 1 m

    rows = []
    for name in ('arch', 'orn'):
        p = os.path.join(R, 'export/out/gate1', name + '.gltf')
        if not os.path.exists(p):
            continue
        g = Gltf(p)
        mats = [m['name'] for m in g.j['materials']]
        wm = g.node_matrices()
        cache = {}
        for i, n in enumerate(g.j['nodes']):
            if 'mesh' not in n:
                continue
            M = wm.get(i, np.eye(4))
            scale = np.linalg.norm(M[:3, :3], axis=0)
            # node centre + nearest-vertex distance
            prim0 = g.j['meshes'][n['mesh']]['primitives'][0]
            acc = g.j['accessors'][prim0['attributes']['POSITION']]
            corners = np.array([[x, y, z] for x in (acc['min'][0], acc['max'][0])
                                for y in (acc['min'][1], acc['max'][1])
                                for z in (acc['min'][2], acc['max'][2])])
            wc = (M[:3, :3] @ corners.T).T + M[:3, 3]
            lo, hi = wc.min(0), wc.max(0)
            d = float(np.linalg.norm(np.maximum(np.maximum(lo - cam, cam - hi), 0.0)))
            if d > args.radius:
                continue
            key = (n['mesh'], tuple(np.round(scale, 6)))
            if key not in cache:
                cache[key] = mesh_density(g, n['mesh'], scale)
            wa, uva, tris = cache[key]
            mat = mats[prim0.get('material', 0)]
            s = sets.get(mat, {})
            for slot in ('albedo', 'normal', 'roughness'):
                pass
            size = s.get('size')
            rows.append(dict(glb=name, node=n.get('name'), mesh=g.j['meshes'][n['mesh']].get('name'),
                             material=mat, set_px=size, dist_m=round(d, 2),
                             area_m2=round(wa, 3), uv1_area=round(uva, 6), tris=tris))
        del g

    # per-material-set roll-up
    bysets = {}
    for r in rows:
        k = r['material']
        e = bysets.setdefault(k, dict(material=k, set_px=r['set_px'], nodes=0, min_d=1e9,
                                      area_m2=0.0, uv1_area=0.0, meshes=set()))
        e['nodes'] += 1
        e['min_d'] = min(e['min_d'], r['dist_m'])
        if r['mesh'] not in e['meshes']:
            e['meshes'].add(r['mesh'])
            e['area_m2'] += r['area_m2']
            e['uv1_area'] += r['uv1_area']

    out = dict(camera=CAM03, resolution=RES, px_per_m_at_1m=px_per_m_1m,
               radius_m=args.radius, sets=[], nodes=rows)
    print(f"cam03 {CAM03['lens']} mm / {RES[0]}x{RES[1]}: {px_per_m_1m:.0f} px per metre at 1 m "
          f"({1000/px_per_m_1m:.2f} mm per pixel)")
    print(f"{'material set':58s} {'px':>5s} {'n':>4s} {'d_min':>6s} {'m2':>8s} {'tex/m':>7s} {'mm/texel':>8s} {'ratio@1m':>8s}")
    for k, e in sorted(bysets.items(), key=lambda kv: kv[1]['min_d']):
        if e['area_m2'] <= 0 or not e['set_px']:
            continue
        tpm = e['set_px'] * math.sqrt(e['uv1_area'] / e['area_m2'])
        row = dict(material=k, set_px=e['set_px'], nodes=e['nodes'], unique_meshes=len(e['meshes']),
                   min_dist_m=round(e['min_d'], 2), area_m2=round(e['area_m2'], 2),
                   uv1_coverage=round(e['uv1_area'], 4), texels_per_m=round(tpm, 2),
                   mm_per_texel=round(1000.0 / tpm, 2),
                   ratio_px_over_texel_at_1m=round(px_per_m_1m / tpm, 2),
                   ratio_at_min_d=round(px_per_m_1m / e['min_d'] / tpm, 2))
        out['sets'].append(row)
        print(f"{k:58s} {e['set_px']:5d} {e['nodes']:4d} {e['min_d']:6.2f} {e['area_m2']:8.1f} "
              f"{tpm:7.2f} {1000/tpm:8.1f} {px_per_m_1m/tpm:8.1f}")
    # ---- (b) the two things that make a near shaft blurred and vertically banded ----------------
    g = Gltf(os.path.join(R, 'export/out/gate1/arch.gltf'))
    names = {m.get('name'): i for i, m in enumerate(g.j['meshes'])}
    detail = man['materials']['detail']
    focus = [('EXPM_ARCH_colonnade_south_column_000_LOD0', 2048, 'concrete_wall_007', 2.16),
             ('EXPM_ARCH_colonnade_south_concrete_colonnade_merged', 2048, 'concrete_wall_007', 2.16)]
    out['islands'], out['detail'] = {}, {}
    print()
    for mesh, px, dset, tile in focus:
        if mesh not in names:
            continue
        wh = uv_islands(g, names[mesh], px)
        mn = np.minimum(wh[:, 0], wh[:, 1])
        isl = dict(islands=int(len(wh)), min_dim_texels_median=round(float(np.median(mn)), 2),
                   min_dim_texels_p25=round(float(np.percentile(mn, 25)), 2),
                   share_narrower_than_16_texels=round(float((mn < 16).mean()), 3),
                   width_median=round(float(np.median(wh[:, 0])), 1),
                   height_median=round(float(np.median(wh[:, 1])), 1))
        out['islands'][mesh] = isl
        print(f"{mesh}\n  UV1 islands {isl['islands']}, median {isl['width_median']} x {isl['height_median']} texels, "
              f"{100 * isl['share_narrower_than_16_texels']:.0f} % narrower than 16 texels")
        dp = {m: detail_projection_density(g, names[mesh], tile, detail['ship_px'].get(dset, 2048), m)
              for m in ('objxy', 'dominant')}
        out['detail'][mesh] = dp
        for m, v in dp.items():
            print(f"  detail {m:8s} tile {v['tile_m']} m @ {v['px']} px: "
                  f"vertical {v['texels_per_m_vertical']:8.1f} tex/m, horizontal {v['texels_per_m_horizontal']:8.1f} tex/m")

    if args.json:
        json.dump(out, open(args.json, 'w'), indent=1)
        print('wrote', args.json)
    return out


if __name__ == '__main__':
    main()
