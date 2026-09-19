"""Phase 8e PART 0 probe (CPU only, no bpy, no GPU): how big is a far-tree leaf card on screen?

    python3 export/p8e_leaf_probe.py            # table + export/out/p8e/leaf_probe.json

Two independent measurements of the same thing, so neither is taken on trust:

  (A) GEOMETRY.  export/out/gate3/trees_far/{placements,topology}.json give, per placement, the
      prototype's mean leaf-card area AFTER the thin-and-grow (leaf_area_m2_after / cards_kept, in
      prototype space) and the placement's uniform scale.  Projected through the orbit camera that
      took renders/web/gate7_orbit_h0{2150,2530}.png (window.__pfaOrbit: fov 40 deg VERTICAL,
      canvas 1170x2532, so px/m at distance d = H / (2 d tan(fov/2))), that is the apparent card
      side in px, and - divided by the number of texture leaves that fit across one card - the
      apparent size of a single painted leaf.

  (B) THE PIXELS.  The same crowns in the capture, at 100 %: a bright-foliage mask inside a crown
      box, thinned by repeated erosion (a crude distance transform - scipy is not installed), whose
      2 x p90 radius is the characteristic blade width in px.  No frustum arithmetic in it at all.

Camera convention: the placements are BLENDER world (x, y, z); the viewer is glTF Y-up, so
(x, y, z) -> (x, z, -y), which is export/trees_far.py's own `to_gltf`.  The orbit stations are read
from renders/web/gate7_orbit_cam.json (MAIN checkout) rather than retyped.
"""
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
FOV_V_DEG = 40.0          # web/src/main.js __pfaOrbit default
CANVAS = (1170, 2532)     # renders/web/gate7_orbit_cam.json "size"


def find(rel):
    for base in (ROOT, MAIN):
        p = base / rel
        if p.exists():
            return p
    raise SystemExit(f"not found in worktree or MAIN: {rel}")


def to_gltf(loc):
    return np.array([float(loc[0]), float(loc[2]), -float(loc[1])])


def px_per_m(d, h=CANVAS[1], fov=FOV_V_DEG):
    return h / (2.0 * d * math.tan(math.radians(fov) * 0.5))


def view_basis(eye, target, up=(0.0, 1.0, 0.0)):
    """three.js lookAt: -Z forward, X right, Y up."""
    f = np.array(target, float) - np.array(eye, float)
    f /= np.linalg.norm(f)
    r = np.cross(f, np.array(up, float))
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return r, u, f


def project(p, eye, basis, canvas=CANVAS, fov=FOV_V_DEG):
    r, u, f = basis
    d = np.array(p, float) - np.array(eye, float)
    z = float(np.dot(d, f))
    if z <= 0.01:
        return None
    ty = math.tan(math.radians(fov) * 0.5)
    tx = ty * (canvas[0] / canvas[1])
    x = float(np.dot(d, r)) / (z * tx)
    y = float(np.dot(d, u)) / (z * ty)
    return (0.5 * (x + 1.0) * canvas[0], 0.5 * (1.0 - y) * canvas[1], z)


def geometry():
    place = json.loads(find("export/out/gate3/trees_far/placements.json").read_text())
    topo = json.loads(find("export/out/gate3/trees_far/topology.json").read_text())
    cams = json.loads(find("renders/web/gate7_orbit_cam.json").read_text())["orbits"]
    protos = {}
    for name, rec in topo["prototypes"].items():
        r = rec["reduction"]
        # mean card area AFTER the grow, in prototype space; a card is one quad (2 tris)
        area = r["leaf_area_m2_after"] / max(1, r["cards_kept"])
        protos[name] = dict(card_side_m=math.sqrt(area), card_scale=r["card_scale"],
                            keep=r["keep_fraction"], cards_kept=r["cards_kept"],
                            height=rec["height_above_base_m"])
    rows = []
    for cam in cams:
        eye = np.array(cam["position"], dtype=float)
        for p in place["placements"]:
            pr = protos[p["prototype"]]
            base = to_gltf(p["loc"])
            centre = base + np.array([0.0, 0.5 * p["height_m"], 0.0])
            d = float(np.linalg.norm(centre - eye))
            ppm = px_per_m(d)
            card_m = pr["card_side_m"] * p["scale"]
            rows.append(dict(heading=cam["headingDeg"], obj=p["object"], proto=p["prototype"],
                             species=p["prototype"].split("_")[2], dist_m=round(d, 2),
                             height_m=p["height_m"], scale=round(p["scale"], 4),
                             px_per_m=round(ppm, 2), card_m=round(card_m, 3),
                             card_px=round(card_m * ppm, 1),
                             crown_px=round(p["height_m"] * ppm, 1)))
    return rows


# ------------------------------------------------------------------ (B) the pixels
def thickness(mask, max_iter=40):
    """2 x p90 of a crude distance transform: repeated 4-neighbour erosion, counting survivals."""
    # PAD: without a background border the blobs that touch the crop edge are never eroded and their
    # "thickness" runs away to max_iter (measured: a 9-px-wide willow card reported 26).
    mask = np.pad(mask, 1, constant_values=False)
    m = mask.copy()
    dist = np.zeros(mask.shape, np.int16)
    for _ in range(max_iter):
        if not m.any():
            break
        dist[m] += 1
        e = m.copy()
        e[1:, :] &= m[:-1, :]
        e[:-1, :] &= m[1:, :]
        e[:, 1:] &= m[:, :-1]
        e[:, :-1] &= m[:, 1:]
        m = e
    d = dist[mask]
    if d.size == 0:
        return None
    return dict(px_p50=float(2 * np.percentile(d, 50)), px_p90=float(2 * np.percentile(d, 90)),
                px_max=float(2 * d.max()), pixels=int(mask.sum()))


# The crowns the geometry pass says are the nearest ones in the two orbit frames (TREEFAR_117 willow
# 37.4 m and TREEFAR_001 broadleaf 38.5 m at heading 215; TREEFAR_000 broadleaf 36.7 m and
# TREEFAR_116 willow 37.7 m at heading 253), plus a 130 m cypress as the far control.  The LIT mask
# over-reads wherever warm stone or the shore band is behind the crown; the DARK half is clean.
BOXES = [
    dict(name="willow_117_37m_h215", file="gate7_orbit_h02150.png", box=[60, 1000, 600, 1740]),
    dict(name="broadleaf_001_38m_h215", file="gate7_orbit_h02150.png", box=[1000, 900, 1170, 1500]),
    dict(name="broadleaf_000_37m_h253", file="gate7_orbit_h02530.png", box=[330, 760, 790, 1540]),
    dict(name="willow_116_38m_h253", file="gate7_orbit_h02530.png", box=[40, 800, 470, 1600]),
    dict(name="far_cypress_130m_h253", file="gate7_orbit_h02530.png", box=[700, 760, 980, 1180]),
]


def pixels(boxes):
    from PIL import Image
    out = []
    for b in boxes:
        im = Image.open(MAIN / "renders/web" / b["file"]).convert("RGB")
        a = np.asarray(im.crop(tuple(b["box"])), dtype=np.float32) / 255.0
        r, g, bl = a[..., 0], a[..., 1], a[..., 2]
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * bl
        # sunlit foliage in this frame is warm (r > b) and bright; the shaded cards are the same
        # blades in the dark duotone and are measured separately
        warm = (r - bl) > 0.10
        lit = warm & (lum > float(np.percentile(lum, 70)))
        dark = warm & (lum < float(np.percentile(lum, 30)))
        out.append(dict(name=b["name"], file=b["file"], box=b["box"],
                        lit=thickness(lit), dark=thickness(dark)))
    return out


# ------------------------------------------------------------- (C) what the card shows at that size
# The card's UVs (read out of export/out/gate1/env_trees.gltf) span u 0.075-0.925, v 0-1: ONE card
# samples the WHOLE painted cluster.  So the apparent "leaf" is set by what survives the mip at the
# card's screen size, not by the leaf the texture painter drew.  Box-downsample the albedo's ALPHA to
# the card's screen size, apply the material's alphaCutoff, and measure the surviving blob width -
# that is the blade QA measured, predicted from the texture alone.
CUTOFF = {"leaves_broadleaf": 0.5, "needles_cypress": 0.45,
          "leaves_eucalyptus": 0.5, "needles_pine": 0.42,
          # the shrub/reed cards (env.glb LOD2 + env_shrubs.glb LOD1), read from those glbs' materials
          "leaves_shrub": 0.5, "reeds": 0.5}
# ---------------------------------------------------------------- 8a item 3: the shrub / reed cards
# Card W x H in PROTOTYPE metres and the median instance scale, measured the same way as CARD above but
# on export/out/gate1/{env,env_shrubs}.gltf and export/out/gate3/instance_rows{,_shrub_lod1}.json. The
# UV window is the WHOLE texture (u 0-1, v 0-1) for every one of them, unlike the trees' centred strip.
SHRUB_CARD = {
    "LOD2": {"MAT_shrub": (0.33, 0.43, "leaves_shrub", 1.13),
             "MAT_shrub_light": (0.34, 0.46, "leaves_shrub", 1.10),
             "MAT_shrub_dry": (0.08, 0.39, "leaves_shrub", 1.19),
             "MAT_reeds": (0.06, 0.23, "reeds", 1.08)},
    "LOD1": {"MAT_shrub": (0.16, 0.21, "leaves_shrub", 1.13),
             "MAT_shrub_light": (0.17, 0.23, "leaves_shrub", 1.10),
             "MAT_shrub_dry": (0.09, 0.22, "leaves_shrub", 1.19),
             "MAT_reeds": (0.03, 0.23, "reeds", 1.08)}}
# px per metre at 1 m for the two stations the relight tiles named, from scripts/qa_cameras.py's lens on
# a 36 mm sensor at 1920x1080 (gate7_cam.json `perStation.size`): px/m = H / (2 d tan(vfov/2)), and
# tan(vfov/2) = (18/lens) * (1080/1920).
STATION_PPM_1M = {"cam03_colonnade_walk(18mm)": 960.0, "cam05_south_lawn(35mm)": 1866.6}
UV_U = (0.075, 0.925)
# Measured off export/out/gate1/env_trees.gltf (positions + UVs decoded from env_trees.bin, one card =
# 2 tris / 4 verts): the card's world W x H in PROTOTYPE space and the u window it samples.  v is 0-1
# for every species, so one texture tile is 0.88-1.02 m of prototype world.
CARD = {"broadleaf": (0.745, 0.876, 0.850, "leaves_broadleaf"),
        "cypress": (0.383, 1.008, 0.380, "needles_cypress"),
        "cypress_column": (0.383, 1.009, 0.380, "needles_cypress"),
        "eucalyptus": (0.427, 1.017, 0.420, "leaves_eucalyptus"),
        "pine": (0.338, 0.965, 0.350, "needles_pine"),
        "redwood": (0.369, 0.922, 0.400, "needles_pine"),
        "willow": (0.164, 0.909, 0.180, "leaves_broadleaf")}
DPR = 0.712               # gate7 orbit capture: canvas 1170x2532, drawing buffer 832x1801


def box_alpha(path, size, u=UV_U):
    from PIL import Image
    im = Image.open(path)
    a = np.asarray(im, dtype=np.float32)[..., 3] / 255.0
    w = a.shape[1]
    a = a[:, int(u[0] * w):int(u[1] * w)]
    s = max(1, int(round(size)))
    ys = np.array_split(np.arange(a.shape[0]), s)
    xs = np.array_split(np.arange(a.shape[1]), s)
    return np.array([[a[np.ix_(yy, xx)].mean() for xx in xs] for yy in ys], np.float32)


_ALPHA = {}


def leaf_alpha(tex):
    if tex not in _ALPHA:
        from PIL import Image
        _ALPHA[tex] = np.asarray(Image.open(find(f"assets/textures/foliage/{tex}.png")),
                                 np.float32)[..., 3] / 255.0
    return _ALPHA[tex]


def card_alpha(tex, u_win, ku, kv, w_px, h_px, v_off=0.0):
    """The alpha a card of `w_px` x `h_px` screen samples actually reads, for a UV scale (ku, kv).

    The card's UV window is the species' centred u strip, widened by ku, and kv periods of v, WRAPPED
    (the shipped samplers are REPEAT, and the textures fade to alpha 0 at their rim, so a tile boundary
    is seamless). Box-averaging the source alpha over each screen sample IS the mip the GPU picks -
    that is the whole point: at 20-30 texels per pixel the painted leaves are gone and what is left is
    what the alpha cut hardens into a blade.
    """
    a = leaf_alpha(tex)
    h, w = a.shape
    ncol, nrow = max(2, int(round(w_px))), max(2, int(round(h_px)))
    u0, u1 = 0.5 - u_win * ku / 2, 0.5 + u_win * ku / 2
    us = ((np.linspace(u0, u1, ncol + 1)[:-1]) % 1.0 * w).astype(int)
    vs = ((np.linspace(v_off, v_off + kv, nrow + 1)[:-1]) % 1.0 * h).astype(int)
    du = max(1, int((u1 - u0) * w / ncol))
    dv = max(1, int(kv * h / nrow))
    out = np.empty((nrow, ncol), np.float32)
    for i, v in enumerate(vs):
        rows = np.arange(v, v + dv) % h
        for j, u in enumerate(us):
            out[i, j] = a[np.ix_(rows, np.arange(u, u + du) % w)].mean()
    return out


def run_width(mask):
    """p90 of the HORIZONTAL run length of the cut mask, in the same px as the grid.

    The complement of `thickness`: QA 19 said the blades read "~40 px WIDE", and a v-only tiling
    shortens a blade without narrowing it (review r2 finding 2). Thickness alone cannot see that.
    """
    runs = []
    for row in mask:
        n = 0
        for v in row:
            if v:
                n += 1
            elif n:
                runs.append(n)
                n = 0
        if n:
            runs.append(n)
    if not runs:
        return None
    return dict(px_p50=float(np.percentile(runs, 50)), px_p90=float(np.percentile(runs, 90)),
                px_max=float(max(runs)), runs=len(runs))


def blade(tex, u_win, ku, kv, w_px, h_px, cutoff=None, v_offs=(0.0, 0.37, 0.71)):
    """Coverage, thickness and run width of the cut mask, averaged over `v_offs` (the per-card offset
    the export applies). `cutoff` overrides the material's own alphaCutoff (the k+cutoff variant)."""
    cut = CUTOFF[tex] if cutoff is None else cutoff
    cov, th90, thmax, rw90, rwmax = [], [], [], [], []
    for vo in v_offs:
        m = card_alpha(tex, u_win, ku, kv, w_px, h_px, v_off=vo) > cut
        t, r = thickness(m, max_iter=80), run_width(m)
        cov.append(float(m.mean()))
        th90.append(t["px_p90"] if t else 0.0)
        thmax.append(t["px_max"] if t else 0.0)
        rw90.append(r["px_p90"] if r else 0.0)
        rwmax.append(r["px_max"] if r else 0.0)
    f = lambda xs: round(float(np.mean(xs)) / DPR, 1)      # noqa: E731  grid px -> capture px
    return dict(cutoff=round(cut, 3), coverage=round(float(np.mean(cov)), 3),
                thickness_p90_px=f(th90), thickness_max_px=f(thmax),
                run_width_p90_px=f(rw90), run_width_max_px=f(rwmax))


def solve_cutoff(tex, u_win, ku, kv, w_px, h_px, target_cov, lo=0.02, hi=0.99, iters=18):
    """The alphaCutoff at which (ku, kv) reproduces `target_cov` - the shipped crown's leaf area.
    Coverage falls monotonically with the cut, so a bisection is exact enough at 3 decimals."""
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        c = blade(tex, u_win, ku, kv, w_px, h_px, cutoff=mid, v_offs=(0.0, 0.37))["coverage"]
        if c > target_cov:
            lo = mid
        else:
            hi = mid
    return round(0.5 * (lo + hi), 3)


def card_px(dist_m=40.0):
    """(species -> (w_px, h_px) of ONE card in the DRAWING BUFFER at `dist_m`, u window, texture)."""
    place = json.loads(find("export/out/gate3/trees_far/placements.json").read_text())["placements"]
    sc = {}
    for p in place:
        sp = p["prototype"].split("ENV_tree_")[1].rsplit("_s", 1)[0]
        sc.setdefault(sp, []).append(p["scale"])
    ppm = px_per_m(dist_m)
    out = {}
    for sp, (w, h, uw, tex) in CARD.items():
        s = float(np.median(sc[sp]))
        out[sp] = dict(scale_median=round(s, 3), card_m=[round(w * s, 3), round(h * s, 3)],
                       card_px=[round(w * s * ppm, 1), round(h * s * ppm, 1)],
                       buf_px=[w * s * ppm * DPR, h * s * ppm * DPR], u_win=uw, tex=tex)
    return out


def cards(dist_m=40.0, factors=((1, 1), (1, 1.5), (1, 2.5), (1, 3), (2, 2)), solve_for=((2, 2),)):
    """The README's table, from code: per species, what one card measures on screen at `dist_m` and
    what the blade measures under each (ku, kv). `solve_for` adds, for those factors, the variant whose
    alphaCutoff is lowered until the coverage matches the shipped k = 1 one (review r2 finding 2)."""
    rows = []
    for sp, g in card_px(dist_m).items():
        wpx, hpx = g["buf_px"]
        base = blade(g["tex"], g["u_win"], 1, 1, wpx, hpx)
        r = dict(species=sp, tex=g["tex"], scale_median=g["scale_median"], card_m=g["card_m"],
                 card_px=g["card_px"], dist_m=dist_m, u_win=g["u_win"], k={})
        for ku, kv in factors:
            b = blade(g["tex"], g["u_win"], ku, kv, wpx, hpx)
            b["coverage_ratio"] = round(b["coverage"] / base["coverage"], 3)
            r["k"][f"{ku},{kv}"] = b
        for ku, kv in solve_for:
            cut = solve_cutoff(g["tex"], g["u_win"], ku, kv, wpx, hpx, base["coverage"])
            b = blade(g["tex"], g["u_win"], ku, kv, wpx, hpx, cutoff=cut)
            b["coverage_ratio"] = round(b["coverage"] / base["coverage"], 3)
            r["k"][f"{ku},{kv}+cut"] = b
        rows.append(r)
    return rows


def shrubs(cases=(("LOD2", "cam05_south_lawn(35mm)", 25.0), ("LOD2", "cam05_south_lawn(35mm)", 54.0),
                  ("LOD2", "cam03_colonnade_walk(18mm)", 25.0), ("LOD2", "cam03_colonnade_walk(18mm)", 54.0),
                  ("LOD1", "cam05_south_lawn(35mm)", 3.0)),
           factors=(1, 2, 3, 4)):
    """8a item 3: the same measurement on the SHRUB cards. Their UV window is the whole texture, so an
    isotropic k is coverage-neutral by construction (it repeats what the card already samples) - no
    cutoff solve is needed, unlike the trees."""
    rows = []
    for lod, station, dist in cases:
        ppm = STATION_PPM_1M[station] / dist
        for mat, (w, h, tex, sc) in SHRUB_CARD[lod].items():
            wp, hp = w * sc * ppm, h * sc * ppm
            base = blade(tex, 1.0, 1, 1, wp, hp)
            r = dict(lod=lod, station=station, dist_m=dist, material=mat, tex=tex,
                     card_m=[round(w * sc, 3), round(h * sc, 3)], card_px=[round(wp, 1), round(hp, 1)],
                     k={})
            for k in factors:
                b = blade(tex, 1.0, k, k, wp, hp)
                b["coverage_ratio"] = round(b["coverage"] / base["coverage"], 3) if base["coverage"] else None
                r["k"][str(k)] = b
            rows.append(r)
    return rows


def texture(sizes=(53, 40, 26, 20, 13, 9, 6)):
    out = []
    for name, cut in CUTOFF.items():
        p = find(f"assets/textures/foliage/{name}.png")
        for s in sizes:
            ds = box_alpha(p, s)
            mask = ds > cut
            th = thickness(mask, max_iter=max(4, s))
            out.append(dict(tex=name, cutoff=cut, screen_px=s,
                            coverage=round(float(mask.mean()), 3),
                            alpha_mean=round(float(ds.mean()), 3),
                            blob_px=None if th is None else round(th["px_p90"], 1),
                            blob_max_px=None if th is None else round(th["px_max"], 1)))
    return out


def main():
    if "--shrubs" in sys.argv:
        rows = shrubs()
        print("Shrub / reed cards: run width p90 / thickness p90 / coverage ratio, capture px, "
              "isotropic UV scale k (the window is already the whole texture, so k is coverage-neutral)")
        for r in rows:
            print("%-6s %-26s %5.1f m %-16s card %5.1fx%5.1f px | " % (
                r["lod"], r["station"], r["dist_m"], r["material"], *r["card_px"])
                + " | ".join("k=%s %5.1f/%4.1f/%s" % (k, v["run_width_p90_px"], v["thickness_p90_px"],
                                                      ("%.2f" % v["coverage"]) if k == "1"
                                                      else ("%.2fx" % v["coverage_ratio"]))
                             for k, v in r["k"].items()))
        out = ROOT / "export/out/p8e"
        out.mkdir(parents=True, exist_ok=True)
        (out / "shrub_probe.json").write_text(json.dumps(dict(cards=SHRUB_CARD, rows=rows), indent=1))
        print(f"[p8e] wrote {out / 'shrub_probe.json'}")
        return
    rows = geometry()
    outdir = ROOT / "export/out/p8e"
    outdir.mkdir(parents=True, exist_ok=True)
    band = [r for r in rows if 30.0 <= r["dist_m"] <= 50.0]
    band.sort(key=lambda r: r["dist_m"])
    print(f"{'head':>5} {'obj':>12} {'species':>10} {'dist':>6} {'px/m':>7} {'card_m':>7} "
          f"{'card_px':>8} {'crown_px':>9}")
    for r in band:
        print(f"{r['heading']:>5} {r['obj']:>12} {r['species']:>10} {r['dist_m']:>6.1f} "
              f"{r['px_per_m']:>7.1f} {r['card_m']:>7.3f} {r['card_px']:>8.1f} {r['crown_px']:>9.1f}")
    card_rows = cards()
    print("\nPer species at 40 m: run width p90 / thickness p90 / coverage ratio (cutoff), "
          "in capture px. ku,kv = the UV scale; +cut = the cutoff solved to hold the coverage.")
    print("%-16s%13s%12s | " % ("species", "card m WxH", "card px")
          + " | ".join("%-22s" % f"ku,kv={k}" for k in card_rows[0]["k"]))
    for r in card_rows:
        wm, hm = r["card_m"]
        wp, hp = r["card_px"]
        print("%-16s%13s%12s | " % (r["species"], "%.2fx%.2f" % (wm, hm), "%.0fx%.0f" % (wp, hp))
              + " | ".join("%5.1f /%5.1f /%.2f (%.2f)" % (v["run_width_p90_px"], v["thickness_p90_px"],
                                                          v["coverage_ratio"], v["cutoff"])
                           for v in r["k"].values()))
    boxes = json.loads(Path(sys.argv[1]).read_text()) if len(sys.argv) > 1 else BOXES
    pix = pixels(boxes) if boxes else []
    for p in pix:
        print(p["name"], "lit", p["lit"], "dark", p["dark"])
    (outdir / "leaf_probe.json").write_text(json.dumps(
        dict(fov_v_deg=FOV_V_DEG, canvas=CANVAS, dpr=DPR, rows=rows, band=band, cards=card_rows,
             texture=texture(), pixels=pix), indent=1))
    print(f"[p8e] wrote {outdir / 'leaf_probe.json'}  ({len(rows)} placement x camera rows)")


if __name__ == "__main__":
    main()
