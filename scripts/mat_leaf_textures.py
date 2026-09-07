"""Procedural foliage card textures (RGBA PNG, 1024 px) for the alpha-cut leaf materials.

    blender --background --python scripts/mat_leaf_textures.py

Writes assets/textures/foliage/<name>.png. The cards they go on (ENV): Sapling `rect` needle strips and `hex` leaf
clusters with unknown in-plane orientation, and 0-1 quad cards (shrubs: v up; reeds: v up). Needle/leaf clusters are
therefore drawn radiating from the centre with an elliptical falloff (orientation-agnostic); shrub and reed textures
assume v = up. Colours are painted in linear-ish species tones; the materials add per-tree hue/value variation.
Generated, CC0, no external sources.
"""
import bpy, math, random, os, sys
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "textures" / "foliage"
N = 1024


def blank():
    return np.zeros((N, N, 4), np.float32)


def splat_line(img, x0, y0, x1, y1, width, color, alpha=1.0, taper=False):
    L = math.hypot(x1 - x0, y1 - y0)
    steps = max(2, int(L / max(width * 0.35, 0.7)))
    for i in range(steps + 1):
        t = i / steps
        w = width * (1.0 - 0.85 * t) if taper else width
        r = max(1, int(math.ceil(w / 2 + 1)))
        x = int(round(x0 + (x1 - x0) * t)); y = int(round(y0 + (y1 - y0) * t))
        if y - r < 0 or x - r < 0 or y + r + 1 > N or x + r + 1 > N:
            continue
        yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
        d = np.sqrt(xx * xx + yy * yy)
        a = np.clip(w / 2 + 0.6 - d, 0, 1) * alpha
        win = img[y - r:y + r + 1, x - r:x + r + 1]
        c = np.asarray(color, np.float32)
        win[..., :3] = win[..., :3] * (1 - a[..., None]) + c[None, None, :] * a[..., None]
        win[..., 3] = np.maximum(win[..., 3], a)


def splat_leaf(img, cx, cy, length, width, angle, color, tip_color=None, midrib=True, shape="ovate", alpha=1.0):
    r = int(length / 2 + 3)
    x0, x1 = max(0, int(cx) - r), min(N, int(cx) + r + 1)
    y0, y1 = max(0, int(cy) - r), min(N, int(cy) + r + 1)
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    dx, dy = xx - cx, yy - cy
    ca, sa = math.cos(angle), math.sin(angle)
    u = (dx * ca + dy * sa) / (length / 2)          # -1 (base) .. 1 (tip)
    v = (-dx * sa + dy * ca) / (width / 2)
    if shape == "ovate":
        half = np.clip(1.0 - 0.45 * (u + 1) * 0.5, 0.25, 1.0) * np.sqrt(np.clip(1 - u * u, 0, 1))
    elif shape == "lanceolate":
        half = np.sqrt(np.clip(1 - u * u, 0, 1)) * np.clip(1.0 - 0.35 * np.abs(u + 0.3), 0.15, 1.0)
    else:  # round
        half = np.sqrt(np.clip(1 - u * u, 0, 1))
    inside = np.clip((half - np.abs(v)) * (width / 2) + 0.5, 0, 1)
    if inside.max() <= 0:
        return
    c = np.asarray(color, np.float32)[None, None, :]
    if tip_color is not None:
        tc = np.asarray(tip_color, np.float32)[None, None, :]
        w = np.clip((u + 1) * 0.5, 0, 1)[..., None]
        c = c * (1 - w) + tc * w
    shade = 1.0 + 0.18 * np.clip(v, -1, 1)[..., None]      # a little tone across the blade
    c = c * shade
    if midrib:
        rib = np.clip(1.0 - np.abs(v) * (width / 2) / 1.2, 0, 1)[..., None]
        c = c * (1 - 0.35 * rib)
    a = inside * alpha
    win = img[y0:y1, x0:x1]
    win[..., :3] = win[..., :3] * (1 - a[..., None]) + c * a[..., None]
    win[..., 3] = np.maximum(win[..., 3], a)


def radial_fade(img, inner=0.55, outer=0.98):
    yy, xx = np.mgrid[0:N, 0:N]
    d = np.sqrt(((xx - N / 2) / (N / 2)) ** 2 + ((yy - N / 2) / (N / 2)) ** 2)
    f = np.clip((outer - d) / (outer - inner), 0, 1)
    img[..., 3] *= f
    return img


def save(img, name):
    OUT.mkdir(parents=True, exist_ok=True)
    key = f"FOLIAGE_{name}"
    if key in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[key])
    im = bpy.data.images.new(key, N, N, alpha=True, float_buffer=False)
    im.alpha_mode = "STRAIGHT"
    im.colorspace_settings.name = "sRGB"
    flat = np.clip(img, 0, 1)
    # colours are authored as linear; store sRGB-encoded so the image loads as a normal sRGB colour texture
    rgb = flat[..., :3]
    enc = np.where(rgb <= 0.0031308, 12.92 * rgb, 1.055 * np.power(np.maximum(rgb, 1e-6), 1 / 2.4) - 0.055)
    out = np.concatenate([enc, flat[..., 3:4]], axis=-1)
    im.pixels.foreach_set(out.astype(np.float32).ravel())
    p = OUT / f"{name}.png"
    im.filepath_raw = str(p)
    im.file_format = "PNG"
    im.save()
    print(f"[leaf_textures] {p.name}  coverage {float((flat[..., 3] > 0.5).mean()):.2f}")


def tex_needles_cypress(seed=1):
    """Flat scale-leaf sprays (Monterey cypress) radiating from the centre; dense core, feathery rim."""
    rnd = random.Random(seed)
    img = blank()
    dark = (0.030, 0.062, 0.020)
    mid = (0.045, 0.085, 0.026)
    light = (0.075, 0.120, 0.035)
    centres = [(N / 2, N / 2)] + [(N / 2 + rnd.uniform(-0.3, 0.3) * N, N / 2 + rnd.uniform(-0.3, 0.3) * N) for _ in range(5)]
    # branchlets
    for k in range(520):
        c0 = rnd.choice(centres)
        ang = rnd.uniform(0, 2 * math.pi)
        r0 = rnd.uniform(0, 0.3) * N / 2
        L = rnd.uniform(70, 200)
        cx, cy = c0[0] + math.cos(ang) * r0, c0[1] + math.sin(ang) * r0
        ex, ey = cx + math.cos(ang) * L, cy + math.sin(ang) * L
        col = rnd.choice((dark, mid, mid, light))
        splat_line(img, cx, cy, ex, ey, 3.2, tuple(c * 0.8 for c in col))
        # side sprays
        n = int(L / 9)
        for i in range(n):
            t = (i + 0.5) / n
            px, py = cx + (ex - cx) * t, cy + (ey - cy) * t
            for s in (-1, 1):
                a2 = ang + s * rnd.uniform(0.5, 0.95)
                l2 = rnd.uniform(10, 26) * (1.0 - 0.5 * t)
                qx, qy = px + math.cos(a2) * l2, py + math.sin(a2) * l2
                splat_line(img, px, py, qx, qy, 2.6, col, taper=True)
                for j in range(2):
                    t2 = rnd.uniform(0.3, 0.9)
                    rx, ry = px + (qx - px) * t2, py + (qy - py) * t2
                    a3 = a2 + rnd.choice((-1, 1)) * rnd.uniform(0.5, 1.0)
                    l3 = rnd.uniform(4, 9)
                    splat_line(img, rx, ry, rx + math.cos(a3) * l3, ry + math.sin(a3) * l3, 2.0, light if rnd.random() < 0.3 else col, taper=True)
    radial_fade(img, 0.55, 0.99)
    save(img, "needles_cypress")


def tex_leaves_eucalyptus(seed=2):
    """Long pendulous lanceolate leaves, grey-green with warm stems, radiating cluster."""
    rnd = random.Random(seed)
    img = blank()
    centres = [(N / 2, N / 2)] + [(N / 2 + rnd.uniform(-0.3, 0.3) * N, N / 2 + rnd.uniform(-0.3, 0.3) * N) for _ in range(6)]
    for k in range(520):
        c0 = rnd.choice(centres)
        ang = rnd.uniform(0, 2 * math.pi)
        r0 = rnd.uniform(0, 0.35) * N / 2
        cx, cy = c0[0] + math.cos(ang) * r0, c0[1] + math.sin(ang) * r0
        L = rnd.uniform(130, 230)
        W = rnd.uniform(22, 36)
        a = ang + rnd.uniform(-0.8, 0.8)
        g = rnd.uniform(0.8, 1.2)
        col = (0.085 * g, 0.125 * g, 0.07 * g)
        tip = (0.11 * g, 0.12 * g, 0.06 * g)
        # stem
        sx, sy = cx - math.cos(a) * L * 0.6, cy - math.sin(a) * L * 0.6
        splat_line(img, sx, sy, cx - math.cos(a) * L * 0.45, cy - math.sin(a) * L * 0.45, 3.0, (0.25, 0.15, 0.08))
        splat_leaf(img, cx, cy, L, W, a, col, tip_color=tip, shape="lanceolate")
    radial_fade(img, 0.6, 0.99)
    save(img, "leaves_eucalyptus")


def tex_leaves_broadleaf(seed=3):
    rnd = random.Random(seed)
    img = blank()
    centres = [(N / 2, N / 2)] + [(N / 2 + rnd.uniform(-0.3, 0.3) * N, N / 2 + rnd.uniform(-0.3, 0.3) * N) for _ in range(6)]
    for k in range(700):
        c0 = rnd.choice(centres)
        ang = rnd.uniform(0, 2 * math.pi)
        r0 = rnd.uniform(0, 0.35) * N / 2
        cx, cy = c0[0] + math.cos(ang) * r0, c0[1] + math.sin(ang) * r0
        L = rnd.uniform(85, 150)
        W = rnd.uniform(50, 90)
        a = ang + rnd.uniform(-1.2, 1.2)
        g = rnd.uniform(0.7, 1.25)
        col = (0.055 * g, 0.125 * g, 0.03 * g)
        tip = (0.07 * g, 0.13 * g, 0.03 * g)
        splat_line(img, cx - math.cos(a) * L * 0.7, cy - math.sin(a) * L * 0.7, cx - math.cos(a) * L * 0.45, cy - math.sin(a) * L * 0.45, 2.6, (0.2, 0.13, 0.06))
        splat_leaf(img, cx, cy, L, W, a, col, tip_color=tip, shape="ovate")
    radial_fade(img, 0.6, 0.99)
    save(img, "leaves_broadleaf")


def tex_leaves_shrub(seed=4):
    """Dense small glossy leaves (pittosporum / mahonia mound); v = up: solid below, feathered crown."""
    rnd = random.Random(seed)
    img = blank()
    for k in range(1400):
        cx = rnd.uniform(0, N)
        cy = N * (1.0 - min(1.0, abs(rnd.gauss(0.45, 0.32))))     # denser low, thinning to the top (row 0 = v 1)
        L = rnd.uniform(38, 70)
        W = rnd.uniform(24, 44)
        a = rnd.uniform(0, 2 * math.pi)
        g = rnd.uniform(0.7, 1.3)
        col = (0.045 * g, 0.095 * g, 0.028 * g)
        tip = (0.06 * g, 0.105 * g, 0.03 * g)
        splat_leaf(img, cx, cy, L, W, a, col, tip_color=tip, shape="ovate", midrib=True)
    # fade the crown (top rows) and the sides softly
    yy, xx = np.mgrid[0:N, 0:N]
    top = np.clip((yy / N - 0.05) / 0.35, 0, 1)                    # row 0 is v=1 (top)
    side = np.clip((0.5 - np.abs(xx / N - 0.5)) / 0.12, 0, 1)
    img[..., 3] *= top * side
    save(img, "leaves_shrub")


def tex_reeds(seed=5):
    """Vertical blades from the bottom (v = 0) tapering to the top, green to straw."""
    rnd = random.Random(seed)
    img = blank()
    for k in range(70):
        x0 = rnd.uniform(0.05, 0.95) * N
        h = rnd.uniform(0.55, 1.0) * N
        lean = rnd.uniform(-0.18, 0.18) * N
        w = rnd.uniform(9, 17)
        g = rnd.uniform(0.6, 1.3)
        dry = rnd.random() < 0.35
        col = (0.30 * g, 0.24 * g, 0.09 * g) if dry else (0.12 * g, 0.20 * g, 0.05 * g)
        steps = 24
        px, py = x0, N - 1
        for i in range(1, steps + 1):
            t = i / steps
            x = x0 + lean * t * t
            y = N - 1 - h * t
            splat_line(img, px, py, x, y, w * (1.0 - 0.8 * t), col)
            px, py = x, y
    save(img, "reeds")


def tex_needles_pine(seed=6):
    """Long needle bundles (Monterey pine / redwood fallback) radiating from the centre."""
    rnd = random.Random(seed)
    img = blank()
    centres = [(N / 2, N / 2)] + [(N / 2 + rnd.uniform(-0.3, 0.3) * N, N / 2 + rnd.uniform(-0.3, 0.3) * N) for _ in range(5)]
    for k in range(1600):
        c0 = rnd.choice(centres)
        ang = rnd.uniform(0, 2 * math.pi)
        r0 = rnd.uniform(0, 0.3) * N / 2
        cx, cy = c0[0] + math.cos(ang) * r0, c0[1] + math.sin(ang) * r0
        L = rnd.uniform(90, 200)
        a = ang + rnd.uniform(-0.35, 0.35)
        g = rnd.uniform(0.7, 1.25)
        col = (0.035 * g, 0.075 * g, 0.022 * g)
        splat_line(img, cx, cy, cx + math.cos(a) * L, cy + math.sin(a) * L, 3.4, col, taper=True)
    radial_fade(img, 0.55, 0.99)
    save(img, "needles_pine")


if __name__ == "__main__":
    tex_needles_cypress()
    tex_needles_pine()
    tex_leaves_eucalyptus()
    tex_leaves_broadleaf()
    tex_leaves_shrub()
    tex_reeds()
