"""Does an ornament resolve into readable tiers at hero distance?  (QA-03-15 acceptance, measured.)

    python3 scripts/orn_tier_stats.py IMAGE [--box x0 y0 x1 y1] [--rows N] [--min-contrast 0.10]

Takes a 1:1 hero crop, builds the vertical profile of mean luminance over the object's columns, and reports
  * relative luminance std (std/mean) over the box - exposure-invariant, comparable across renders;
  * the light/dark band structure: every run of the profile between a local max and the next local min whose
    Michelson contrast (hi-lo)/(hi+lo) clears --min-contrast counts as one readable tier boundary.
"Two readable leaf tiers with dark recesses" = at least 3 alternations (leaf tier, recess, leaf tier, recess).
Works on any image; with no --box the whole image is used.
"""
import sys
from PIL import Image

args = sys.argv[1:]
if not args:
    print(__doc__)
    sys.exit(1)
path = args[0]


def opt(name, n=1, cast=float, default=None):
    if name not in args:
        return default
    i = args.index(name) + 1
    v = [cast(x) for x in args[i:i + n]]
    return v[0] if n == 1 else v


im = Image.open(path).convert("RGB")
box = opt("--box", 4, int)
if box:
    im = im.crop(tuple(box))
w, h = im.size
px = im.load()
MIN_C = opt("--min-contrast", 1, float, 0.10)


def lum(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


rows = []
allv = []
for y in range(h):
    vs = [lum(px[x, y]) for x in range(w)]
    rows.append(sum(vs) / w)
    allv += vs
mean = sum(allv) / len(allv)
var = sum((v - mean) ** 2 for v in allv) / len(allv)
std = var ** 0.5
print(f"{path}  box={box or (0, 0, w, h)}  {w}x{h}px")
print(f"  mean {mean:.1f}  std {std:.1f}  relative std {std / max(mean, 1e-6):.4f}")

# smooth the profile by 1 px so single-pixel noise does not create bands
sm = [rows[0]] + [(rows[i - 1] + 2 * rows[i] + rows[i + 1]) / 4 for i in range(1, h - 1)] + [rows[-1]]
ext = []          # (y, value, "max"/"min")
for i in range(1, h - 1):
    if sm[i] >= sm[i - 1] and sm[i] > sm[i + 1]:
        ext.append((i, sm[i], "max"))
    elif sm[i] <= sm[i - 1] and sm[i] < sm[i + 1]:
        ext.append((i, sm[i], "min"))
# keep only alternating extrema, greedily merging same-kind runs
clean = []
for e in ext:
    if clean and clean[-1][2] == e[2]:
        if (e[2] == "max" and e[1] > clean[-1][1]) or (e[2] == "min" and e[1] < clean[-1][1]):
            clean[-1] = e
    else:
        clean.append(e)
edges = []
for a, b in zip(clean, clean[1:]):
    hi, lo = (a, b) if a[2] == "max" else (b, a)
    c = (hi[1] - lo[1]) / max(hi[1] + lo[1], 1e-6)
    if c >= MIN_C:
        edges.append((a[0], b[0], round(c, 3)))
print(f"  profile top->bottom: " + " ".join(f"{v:.0f}" for v in sm))
print(f"  readable alternations at contrast >= {MIN_C}: {len(edges)}")
for y0, y1, c in edges:
    print(f"    y {y0:3d} -> {y1:3d}   Michelson {c}")
