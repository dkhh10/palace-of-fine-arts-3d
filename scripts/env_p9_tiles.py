"""Phase 9 ENV / 8d R3 -- the high-frequency half of the backdrop.

Generates four TILEABLE detail images for the backdrop materials.  They are *gain* maps, not albedos: the shader
reads them as `gain = 1 + (tex - 0.5) * 2 * strength`, so a tile whose channel mean is exactly 0.5 multiplies the
R1 low-frequency albedo by a mean of 1.0.  That is the whole point -- 8d R1 spent a round landing cam06's top-row
luma and saturation and the hero wall band's saturation, and R3 must add structure without moving those means.

Why images and not more procedural nodes: Cycles would see a procedural, the web viewer never would.  The viewer
gets a 1024 baked atlas at 0.79 texels/m on the facades (docs/briefs/phase8d_analysis.md Sec.2) and nothing finer
than 1.3 m survives that bake.  A REPEAT-sampled tile on TEXCOORD_0 is the only band that carries the bay/storey
rhythm to both renderers at the same time.

Licence: generated here from numpy, CC0 / project-owned.  No fetched asset.

Run (no Blender):  python3 scripts/env_p9_tiles.py
Writes assets/textures/backdrop/*.png and prints the mean / min / max / texel density of each.
"""
import os
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "textures", "backdrop")

# name -> (resolution px, tile size in metres (u, v))
# The UV0 laid by scripts/env_p9_uv0.py is already in TILE UNITS, so the exporter needs no texture transform:
# sample with wrap REPEAT on TEXCOORD_0 and nothing else.
TILES = {
    "bd_facade":   (1024, (16.0, 13.2)),   # 4 bays x 4 storeys: bay 4.0 m, storey 3.3 m
    "bd_roof":     (512,  (16.0, 16.0)),   # flat roof: gravel, seams, roof furniture
    "bd_rooftile": (512,  (8.0, 8.0)),     # mission tile: 0.33 m courses, 0.30 m pans
    "bd_canopy":   (1024, (24.0, 24.0)),   # leaf mass: 4-12 m crowns, 0.8 m clumps
}


# ------------------------------------------------------------------ tileable value noise
def _smooth(t):
    return t * t * (3.0 - 2.0 * t)


def vnoise(res, cells, rng):
    """Periodic (tileable) value noise at `cells` cells across the image."""
    g = rng.random((cells, cells))
    s = np.arange(res) / res * cells
    i0 = np.floor(s).astype(int) % cells
    i1 = (i0 + 1) % cells
    t = _smooth(s - np.floor(s))
    g00 = g[np.ix_(i0, i0)]
    g01 = g[np.ix_(i0, i1)]
    g10 = g[np.ix_(i1, i0)]
    g11 = g[np.ix_(i1, i1)]
    tx = t[None, :]
    ty = t[:, None]
    top = g00 * (1 - tx) + g01 * tx
    bot = g10 * (1 - tx) + g11 * tx
    return top * (1 - ty) + bot * ty


def fbm(res, cells, rng, octaves=3, rough=0.5):
    out = np.zeros((res, res))
    amp, tot, c = 1.0, 0.0, cells
    for _ in range(octaves):
        out += amp * vnoise(res, max(2, c), rng)
        tot += amp
        amp *= rough
        c *= 2
    return out / tot


# MEAN_GAIN: the tiles are normalised to 0.505, not 0.500.  A mean-1.0 multiplicative gain is mean-preserving in
# LINEAR albedo, but AgX is concave there, so the render came out 1 % dark (round 2: -0.005 luma at every box) and
# AgX read the darker pixels as more saturated (+0.005 to +0.018).  A +0.005 lift on the tile mean is a +1.0 %
# lift on the gain at amp 2.0, which is what the measurement says the transfer costs.
MEAN_GAIN = 0.505


def normalise(a, mean=MEAN_GAIN, lo=0.12, hi=0.92):
    """Shift/clip so the channel mean is `mean` and nothing leaves [lo, hi] (gain stays positive)."""
    a = a.astype(np.float64)
    for _ in range(6):
        a = a - a.mean() + mean
        a = np.clip(a, lo, hi)
        if abs(a.mean() - mean) < 1e-4:
            break
    return a


def save(name, rgb):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name + ".png")
    Image.fromarray(np.clip(rgb * 255.0 + 0.5, 0, 255).astype(np.uint8), "RGB").save(p)
    res, (tu, tv) = TILES[name]
    print(f"[env_p9_tiles] {name}.png {res}^2  tile {tu} x {tv} m  "
          f"{res / tu:.1f} x {res / tv:.1f} texels/m  mean {rgb.reshape(-1, 3).mean(axis=0).round(4)}  "
          f"min {rgb.min():.3f} max {rgb.max():.3f}")
    return p


# ------------------------------------------------------------------ 1. facade
def make_facade():
    res, (tu, tv) = TILES["bd_facade"]
    rng = np.random.default_rng(9301)
    BAYS, STOREYS = 4, 4
    cw, ch = res // BAYS, res // STOREYS
    v = np.full((res, res), 0.50)

    # stucco: two grains, the coarse one is what survives the mip at 146 m
    v += (fbm(res, 8, rng, 3, 0.55) - 0.5) * 0.070
    v += (fbm(res, 48, rng, 2, 0.5) - 0.5) * 0.045

    cool = np.zeros((res, res))  # noqa: E501          # >0 = push the gain cool (windows), used on R/B below

    # y is row 0 = top of the image = top of the tile.  v of the UV grows with world z, and PNG row 0 is v=1 in
    # Blender's image space, so "row 0 = top" is consistent with storeys stacking upward.
    for s in range(STOREYS):
        y0 = s * ch
        for b in range(BAYS):
            x0 = b * cw
            cell = (slice(y0, y0 + ch), slice(x0, x0 + cw))
            v[cell] += rng.normal(0.0, 0.055)                      # per-bay tonal spread

            wx0 = x0 + int(0.28 * cw); wx1 = x0 + int(0.72 * cw)
            wy0 = y0 + int(0.22 * ch); wy1 = y0 + int(0.74 * ch)
            # glass: dark, with a sky-reflection gradient toward the head of the opening
            grad = np.linspace(1.0, 0.0, wy1 - wy0)[:, None]
            base = rng.uniform(0.11, 0.20)
            top = rng.uniform(0.30, 0.44)
            blind = rng.random() < 0.18                            # ~1 in 6 has a pale blind / curtain
            g = base + (top - base) * grad
            if blind:
                g = np.full_like(g, rng.uniform(0.58, 0.70))
            v[wy0:wy1, wx0:wx1] = g
            if not blind:
                cool[wy0:wy1, wx0:wx1] = 1.0
            # mullion
            xm = (wx0 + wx1) // 2
            v[wy0:wy1, xm:xm + max(1, cw // 128)] = 0.46
            # head shadow above the opening, sill below it, reveals left / right
            r = max(1, ch // 96)
            v[wy0 - 2 * r:wy0, wx0 - r:wx1 + r] = 0.22
            v[wy1:wy1 + 2 * r, wx0 - 2 * r:wx1 + 2 * r] = 0.86
            v[wy1 + 2 * r:wy1 + 3 * r, wx0 - 2 * r:wx1 + 2 * r] = 0.30   # shadow the sill throws
            v[wy0:wy1, wx0 - r:wx0] = 0.26
            v[wy0:wy1, wx1:wx1 + r] = 0.74

        # storey line across the full width: shadow under the floor slab, lit band above it
        r = max(1, ch // 110)
        v[y0:y0 + r, :] = 0.30
        v[y0 + r:y0 + 2 * r, :] = 0.78

    # pier / pilaster strip at each bay joint
    for b in range(BAYS):
        x0 = b * cw
        w = max(2, cw // 64)
        v[:, x0:x0 + w] = np.clip(v[:, x0:x0 + w] * 0.0 + 0.36, 0, 1)
        v[:, x0 + w:x0 + 3 * w] = 0.62

    v = normalise(v)
    # windows cool the gain: the hero wall band measures saturation 0.654 against ref 169's 0.431, and a quarter
    # of its pixels are glass.  Luma is held (the R loss is matched by the B gain at Rec.709 weights).
    # round 3: the tint was R x0.90 / B x1.16, which multiplied an ochre albedo into a BLUE one and raised the
    # hero band's saturation 0.666 -> 0.676 where the photograph wants 0.395.  Cut to a quarter.
    rgbv = np.dstack([v * (1.0 - 0.030 * cool), v * (1.0 - 0.005 * cool), v * (1.0 + 0.045 * cool)])
    for c in range(3):
        rgbv[..., c] = normalise(rgbv[..., c])
    return save("bd_facade", rgbv)


# ------------------------------------------------------------------ 2. flat roof
def make_roof():
    res, (tu, tv) = TILES["bd_roof"]
    rng = np.random.default_rng(9302)
    v = np.full((res, res), 0.50)
    # R3 round 2: the first cut had channel sd 0.064, half the facade's, and cam06 gives the flat roofs
    # 259 656 px -- the largest single backdrop group in the frame.  Contrast raised to land near 0.10.
    v += (fbm(res, 6, rng, 3, 0.6) - 0.5) * 0.26          # resurfacing patches / ponding
    v += (fbm(res, 64, rng, 2, 0.5) - 0.5) * 0.16         # gravel grain (~0.25 m)
    # felt seams every 3 m
    per = max(4, int(round(res * 3.0 / tu)))
    v[::per, :] *= 0.62
    v[:, ::per] *= 0.70
    # roof furniture: penthouses, vents, ducts -- with the shadow each one throws.  This is what stops cam06's
    # 259 656 roof pixels reading as one poster-flat field.
    for _ in range(11):
        w = int(rng.uniform(1.0, 3.5) / tu * res)
        h = int(rng.uniform(1.0, 2.8) / tv * res)
        x = rng.integers(0, res - w - 1); y = rng.integers(0, res - h - 1)
        v[y:y + h, x:x + w] = rng.uniform(0.62, 0.76)                        # lit top
        sh = max(2, res // 160)
        v[y + h:y + h + sh + h // 4, x + sh:x + w + sh] = rng.uniform(0.20, 0.30)   # cast shadow
        v[y:y + max(1, h // 8), x:x + w] = 0.72                              # coping highlight
    v = normalise(v)
    return save("bd_roof", np.dstack([v, v, v]))


# ------------------------------------------------------------------ 3. mission tile roof
def make_rooftile():
    res, (tu, tv) = TILES["bd_rooftile"]
    rng = np.random.default_rng(9303)
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float64)
    mu = xx / res * tu          # metres along u
    mv = yy / res * tv          # metres along v
    course = np.abs(((mv / 0.33) % 1.0) - 0.5) * 2.0          # 0 at the course line
    pan = np.cos(mu / 0.30 * 2 * np.pi) * 0.5 + 0.5           # barrel pans
    v = 0.50 + (pan - 0.5) * 0.15                              # ridge lit / valley shaded (secondary)
    v *= np.clip(0.62 + 0.42 * course ** 0.6, 0, 1.3)          # the course line is what a tile roof reads as
    # per-course value jitter: a tile field is dozens of firings
    ci = (mv / 0.33).astype(int)
    jit = rng.normal(0.0, 0.05, ci.max() + 2)[ci]
    v += jit
    v += (fbm(res, 16, rng, 3, 0.6) - 0.5) * 0.13              # lot spread / moss blooms
    v += (fbm(res, 96, rng, 2, 0.5) - 0.5) * 0.06
    v = normalise(v)
    return save("bd_rooftile", np.dstack([v, v, v]))


# ------------------------------------------------------------------ 4. canopy leaf mass
def make_canopy():
    res, (tu, tv) = TILES["bd_canopy"]
    rng = np.random.default_rng(9304)
    yy, xx = (np.mgrid[0:res, 0:res].astype(np.float64) + 0.5) / res
    v = np.full((res, res), 0.28)                              # the gaps between crowns
    lit = np.zeros((res, res))
    for _ in range(26):
        cx, cy = rng.random(), rng.random()
        r = rng.uniform(4.0, 11.0) / tu / 2.0                  # crown radius in tile units
        # SIGNED wrapped deltas: the unwrapped form creased the shading at the tile edge and the seam showed
        sx = xx - cx; sx = sx - np.round(sx)
        sy = yy - cy; sy = sy - np.round(sy)
        d = np.sqrt(sx ** 2 + sy ** 2) / r
        m = np.clip(1.0 - d ** 2, 0.0, 1.0)
        # a crown is lit on the sun side (-X / +Y is the morning sun's bearing in this scene) and self-shadowed
        # on the far side: that gradient is 4x the energy a flat lobe albedo has (hf 0.025 vs ref 105's 0.118).
        shade = 0.5 + 0.5 * np.clip((-sx * 0.7 + sy * 0.7) / max(r, 1e-6), -1, 1)
        val = 0.30 + 0.52 * shade * rng.uniform(0.85, 1.15)
        take = m > lit
        lit = np.where(take, m, lit)
        v = np.where(take, val, v)
    v += (fbm(res, 32, rng, 3, 0.65) - 0.5) * 0.22             # 0.75 m leaf clumps
    v += (fbm(res, 8, rng, 2, 0.5) - 0.5) * 0.10               # whole-crown spread
    v = normalise(v)
    # the shaded gaps go cool, the lit tops warm: ref 105's tree masses sit at saturation 0.04-0.13, so this is a
    # small move, but it is the difference between a mass and a flat green card.
    warm = np.clip((v - MEAN_GAIN) * 2.0, -1, 1)
    rgbv = np.dstack([v * (1.0 + 0.06 * warm), v, v * (1.0 - 0.05 * warm)])
    for c in range(3):
        rgbv[..., c] = normalise(rgbv[..., c])
    return save("bd_canopy", rgbv)


if __name__ == "__main__":
    make_facade()
    make_roof()
    make_rooftile()
    make_canopy()
    print(f"[env_p9_tiles] wrote 4 tiles into {OUT}")
