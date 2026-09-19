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
          "leaves_eucalyptus": 0.5, "needles_pine": 0.42}
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


def blob(tex, u_win, w_px, h_px):
    """The blade the alpha cut leaves when the card is w_px x h_px on screen: box-downsample the
    ALPHA of the sampled strip to exactly that many samples (the mip the GPU picks), cut it at the
    material's alphaCutoff, and measure the surviving blob."""
    from PIL import Image
    a = np.asarray(Image.open(find(f"assets/textures/foliage/{tex}.png")), np.float32)[..., 3] / 255.0
    w = a.shape[1]
    a = a[:, int((0.5 - u_win / 2) * w):int((0.5 + u_win / 2) * w)]
    ys = np.array_split(np.arange(a.shape[0]), max(2, int(round(h_px))))
    xs = np.array_split(np.arange(a.shape[1]), max(2, int(round(w_px))))
    ds = np.array([[a[np.ix_(y, x)].mean() for x in xs] for y in ys], np.float32)
    mask = ds > CUTOFF[tex]
    th = thickness(mask, max_iter=80)
    return dict(p90=None if th is None else th["px_p90"], max=None if th is None else th["px_max"],
                coverage=round(float(mask.mean()), 3))


def cards(dist_m=40.0, factors=(1, 1.5, 2, 2.5, 3)):
    """The doc's table: what one card of each species measures on screen at `dist_m`, and what the
    blade would measure with a UV scale k (the card then shows k x k tiles of the cluster)."""
    place = json.loads(find("export/out/gate3/trees_far/placements.json").read_text())["placements"]
    sc = {}
    for p in place:
        sp = p["prototype"].split("ENV_tree_")[1].rsplit("_s", 1)[0]
        sc.setdefault(sp, []).append(p["scale"])
    ppm = px_per_m(dist_m)
    rows = []
    for sp, (w, h, uw, tex) in CARD.items():
        s = float(np.median(sc[sp]))
        wm, hm = w * s, h * s
        r = dict(species=sp, tex=tex, scale_median=round(s, 3), card_m=[round(wm, 3), round(hm, 3)],
                 card_px=[round(wm * ppm, 1), round(hm * ppm, 1)], dist_m=dist_m, k={})
        for k in factors:
            b = blob(tex, uw, wm * ppm * DPR / k, hm * ppm * DPR / k)
            r["k"][str(k)] = dict(p90_px=round(b["p90"] / DPR, 1), max_px=round(b["max"] / DPR, 1),
                                  coverage=b["coverage"])
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
    print(f"\n{'species':16s}{'card m WxH':>13}{'card px@40m':>12} | "
          + " | ".join(f"k={k}: p90/max/cov" for k in card_rows[0]["k"]))
    for r in card_rows:
        wm, hm = r["card_m"]
        wp, hp = r["card_px"]
        print("%-16s%13s%12s | " % (r["species"], "%.2fx%.2f" % (wm, hm), "%.0fx%.0f" % (wp, hp))
              + " | ".join("%5.0f/%4.0f/%.2f" % (v["p90_px"], v["max_px"], v["coverage"])
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
