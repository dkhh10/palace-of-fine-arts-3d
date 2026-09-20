#!/usr/bin/env python3
"""Phase 9 bake analysis, Part B: decompose station 3's shade excess (viewer vs Cycles) per term.

CPU ONLY - no Blender, no GPU, no Chrome.  Three measurements, all from files already on disk:

  A. `--lightmaps`  the SHIPPED lightmap texture against the archival EXR the bake wrote, per own map,
     over the whole map and over its deep-shade tail (p1/p5/p10/p20).  This is the only term that had
     never been measured on the KTX2 itself: export/gate3_encode.py's roundtrip numbers are the PNG's,
     and the UASTC/ASTC step after it was unmeasured.  Needs tools/bin/ktx (transcode -> rgba8 -> extract).
  B. `--boxes`      the cam03 boxes, inverted through the DELIVERY LUT (full 3D Gauss-Newton inverse of
     export/out/gate0/lut_agx_high_contrast_65.cube at exposure -2.8331399 EV, not a per-channel
     approximation), so viewer and Cycles are compared in scene-linear, where the terms are additive.
  C. `--post`       the station-1 ?post= captures (none / mist / bloom / vignette / all), the only flag
     captures on disk, as the measured size of the post term on shaded stone.

The comparison is additive on purpose: a multiplicative error (albedo, lightmap scale, exposure) would
move the SUNLIT boxes too, and they are within 4-7 %.
"""
import argparse, json, subprocess, sys, tempfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
BAKE_WT = MAIN/".claude/worktrees/phase6-bake"          # the archival EXRs live here only
CUBE = MAIN/"export/out/gate0/lut_agx_high_contrast_65.cube"
MANIFEST = MAIN/"export/out/gate3/manifest.json"
MIN_EV, MAX_EV, PIVOT, EXP_EV = -12.47393, 4.026069, 0.18, -2.8331398963928223
HAZE = np.array([5.320880889892578, 3.739000082015991, 1.9603391885757446])   # compositor Haze Color
SAT = 245                                               # 8-bit display ceiling to exclude

# ------------------------------------------------------------------ the delivery LUT, forward + inverse
def load_cube(p=CUBE):
    n, data = None, []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line[0] == '#':
            continue
        if line.startswith('LUT_3D_SIZE'):
            n = int(line.split()[1]); continue
        if line[0].isalpha():
            continue
        v = line.split()
        if len(v) == 3:
            data.append([float(x) for x in v])
    return np.array(data, np.float32).reshape(n, n, n, 3).transpose(2, 1, 0, 3), n

def shaper(lin):
    return np.clip((np.log2(np.maximum(lin, 1e-10)/PIVOT) - MIN_EV)/(MAX_EV - MIN_EV), 0.0, 1.0)

def lut_apply(lin, lut, n):
    s = shaper(lin)*(n - 1)
    i0 = np.clip(np.floor(s).astype(int), 0, n - 2); f = s - i0
    out = np.zeros(lin.shape[:-1] + (3,))
    for dr in (0, 1):
        for dg in (0, 1):
            for db in (0, 1):
                w = ((1 - f[..., 0]) if dr == 0 else f[..., 0]) \
                    * ((1 - f[..., 1]) if dg == 0 else f[..., 1]) \
                    * ((1 - f[..., 2]) if db == 0 else f[..., 2])
                out += w[..., None]*lut[i0[..., 0] + dr, i0[..., 1] + dg, i0[..., 2] + db]
    return out

class Lut:
    def __init__(self):
        self.lut, self.n = load_cube()
        lin = np.concatenate([[0.0], np.logspace(-6, 3, 4096)])
        d = self.fwd(np.stack([lin]*3, -1)).mean(1)
        o = np.argsort(d)
        self._seed_x, self._seed_y = d[o], lin[o]
    def fwd(self, lin):
        return lut_apply(np.asarray(lin, float)*(2.0**EXP_EV), self.lut, self.n)*255.0
    def inv(self, d255, iters=24):
        """display 0..255 -> pre-exposure scene-linear, exact to <1e-4 display units."""
        d = np.asarray(d255, float)
        lin = np.maximum(np.interp(d, self._seed_x, self._seed_y), 1e-7)
        h = 0.02
        for _ in range(iters):
            f0 = self.fwd(lin); r = d - f0
            if np.abs(r).max() < 1e-4:
                break
            J = (self.fwd(lin*np.exp(h)) - f0)/h
            lin = np.clip(lin*np.exp(np.clip(r/np.where(np.abs(J) < 1e-6, 1e-6, J), -1.5, 1.5)), 1e-7, 1e4)
        return lin

# ------------------------------------------------------------------ A. the shipped lightmap vs the EXR
def cmd_lightmaps(args):
    import cv2                                    # EXR through OpenCV (OPENCV_IO_ENABLE_OPENEXR=1)
    man = json.loads(MANIFEST.read_text())
    ktx = MAIN/"tools/bin/ktx"
    out = {}
    print(f"{'asset':52s} {'range':>8s} {'whole':>7s} {'<p20':>7s} {'<p10':>7s} {'<p5':>7s} "
          f"{'p50 st':>7s} {'p99 st':>7s}")
    for asset, e in man["lightmaps"]["assets"].items():
        if not isinstance(e, dict) or "textures" not in e:
            continue
        key = e["textures"].get(e.get("default", "gamma2"))
        exr = BAKE_WT/"export/out/gate3"/e["exr"]
        k2 = MAIN/"export/out/gate3/tex_ktx2"/f"{key}.ktx2"
        if not exr.exists() or not k2.exists():
            print(f"{asset:52s}  SKIP (exr {exr.exists()} ktx2 {k2.exists()})"); continue
        R = float(e["range"])
        with tempfile.TemporaryDirectory() as td:
            t8 = Path(td)/"t.ktx2"; png = Path(td)/"t.png"
            subprocess.run([str(ktx), "transcode", "--target", "rgba8", str(k2), str(t8)], check=True)
            subprocess.run([str(ktx), "extract", "--level", "0", str(t8), str(png)], check=True)
            dec = np.asarray(Image.open(png))[..., :3].astype(np.float64)
        D = (dec/255.0)**2*R                              # the viewer's own gamma2 decode
        A = cv2.imread(str(exr), cv2.IMREAD_UNCHANGED)[..., ::-1].astype(np.float64)
        m = A.sum(2) > 0
        row = {"range": R, "whole": float(D[m].mean()/A[m].mean())}
        for q in (20, 10, 5):
            t = np.percentile(A[m], q); sel = m & (A.mean(2) < t)
            row[f"p{q}"] = float(D[sel].mean()/max(A[sel].mean(), 1e-9))
        sig = A[m] > 0.01*np.percentile(A[m], 99)
        st = np.abs(np.log2(np.maximum(D[m], 1e-6)/np.maximum(A[m], 1e-6)))[sig]
        row["stops_p50"], row["stops_p99"] = float(np.percentile(st, 50)), float(np.percentile(st, 99))
        out[asset] = row
        print(f"{asset:52s} {R:8.2f} {row['whole']:6.3f}x {row['p20']:6.3f}x {row['p10']:6.3f}x "
              f"{row['p5']:6.3f}x {row['stops_p50']:7.3f} {row['stops_p99']:7.3f}")
    Path(args.out).write_text(json.dumps(out, indent=1))
    print(f"-> {args.out}")

# ------------------------------------------------------------------ B. the cam03 boxes, in scene-linear
S = 1.5                                          # the r14/r16/r17 boxes are stated at 1280x720
def s15(b): return tuple(int(round(v*S)) for v in b)
BOXES = {
    "near_column (r17)":  s15((900, 150, 1270, 700)),
    "flute_band (r17)":   s15((900, 330, 1270, 470)),
    "outer_row (r14)":    s15((880, 120, 1200, 600)),
    "shaft_flank (r14)":  s15((480, 150, 560, 600)),
    "walk (r14)":         s15((420, 560, 900, 720)),
    "sunlit_rotunda":     s15((560, 0, 880, 320)),
    "bush (8a-4)":        (860, 650, 1180, 760),
    "fg_foliage (r13)":   (1300, 600, 1900, 1040),
    "near 10-25 m (r13)": (700, 700, 1300, 1000),
    "far 120 m+ (r13)":   (820, 300, 1180, 430),
}
VIEWER = "renders/web/gate12_cam03.png"
CYCLES = "renders/qa_comparisons/cycles_p8/cam03_1080_32spp.png"

def cmd_boxes(args):
    L = Lut()
    V = np.asarray(Image.open(MAIN/VIEWER).convert("RGB"), float)
    C = np.asarray(Image.open(MAIN/(args.cycles or CYCLES)).convert("RGB"), float)
    rng = np.random.default_rng(0)
    out = {}
    print(f"{'box':20s} {'n':>7s} | {'Cycles linear RGB':^26s} | {'viewer linear RGB':^26s} | "
          f"{'excess RGB':^26s} | {'exc/Cyc':>8s}")
    for k, (x0, y0, x1, y1) in BOXES.items():
        x1, y1 = min(x1, V.shape[1]), min(y1, V.shape[0])
        v = V[y0:y1, x0:x1].reshape(-1, 3); c = C[y0:y1, x0:x1].reshape(-1, 3)
        ok = (v.max(1) < SAT) & (c.max(1) < SAT)
        v, c = v[ok], c[ok]
        if len(v) > 20000:
            i = rng.choice(len(v), 20000, replace=False); v, c = v[i], c[i]
        if len(v) < 200:
            print(f"{k:20s} {ok.sum():7d} | all saturated"); continue
        vl, cl = L.inv(v).mean(0), L.inv(c).mean(0)
        d = vl - cl
        out[k] = dict(n=int(ok.sum()), cycles=cl.tolist(), viewer=vl.tolist(), excess=d.tolist(),
                      ratio_linear=(vl/np.maximum(cl, 1e-9)).tolist())
        print(f"{k:20s} {ok.sum():7d} | {cl[0]:8.4f}{cl[1]:9.4f}{cl[2]:9.4f} | "
              f"{vl[0]:8.4f}{vl[1]:9.4f}{vl[2]:9.4f} | {d[0]:+8.4f}{d[1]:+9.4f}{d[2]:+9.4f} | "
              f"{d[0]/max(cl[0], 1e-9):7.2f}x")
    Path(args.out).write_text(json.dumps(out, indent=1))
    print(f"-> {args.out}")

# ------------------------------------------------------------------ C. the station-1 post captures
P1 = {"shaded_attic": (1110, 225, 1150, 260), "water_refl": (900, 760, 1020, 840),
      "south_wing": (60, 480, 560, 600), "shore_band": (700, 600, 1200, 740)}

def cmd_post(args):
    L = Lut()
    F = {k: np.asarray(Image.open(MAIN/f"renders/web/post_{k}.png").convert("RGB"), float)
         for k in ("none", "mist", "bloom", "vignette", "all")}
    out = {}
    for k, (x0, y0, x1, y1) in P1.items():
        sub = {n: f[y0:y1, x0:x1].reshape(-1, 3) for n, f in F.items()}
        ok = np.ones(len(sub["none"]), bool)
        for s in sub.values():
            ok &= s.max(1) < SAT
        if ok.sum() < 50:
            print(f"{k:14s} only {ok.sum()} unsaturated px, skipped"); continue
        lin = {n: L.inv(s[ok]).mean(0) for n, s in sub.items()}
        b = lin["none"]
        out[k] = {n: (lin[n] - b).tolist() for n in F if n != "none"}
        out[k]["none"] = b.tolist()
        print(f"{k:14s} n={int(ok.sum()):6d}  post=none linear {np.round(b, 4)}")
        for n in ("mist", "bloom", "vignette", "all"):
            d = lin[n] - b
            print(f"{'':14s}   {n:9s} {d[0]:+9.4f}{d[1]:+9.4f}{d[2]:+9.4f}")
    Path(args.out).write_text(json.dumps(out, indent=1))
    print(f"-> {args.out}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--lightmaps", action="store_true")
    ap.add_argument("--boxes", action="store_true")
    ap.add_argument("--post", action="store_true")
    ap.add_argument("--cycles", default=None)
    ap.add_argument("--out", default="/tmp/p9_shade_terms.json")
    a = ap.parse_args()
    if a.lightmaps: cmd_lightmaps(a)
    elif a.boxes:   cmd_boxes(a)
    elif a.post:    cmd_post(a)
    else:           ap.error("one of --lightmaps / --boxes / --post")
