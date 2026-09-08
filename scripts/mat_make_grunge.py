#!/usr/bin/env python3
"""Build the MACRO weathering maps (0.3-3 m features) that the concrete family multiplies into albedo and roughness.

Why this exists (QA-04-3, the third round of the same defect).  The library's only photographic input was the Poly
Haven 2K concrete set, box-projected on a 2.2-2.7 m tile.  On the 1920x1080 hero one pixel is ~5 cm, so that tile is
sampled ~40x below its own texel size and averages to a flat tint -- which is why two rounds of procedural tuning
moved the measured luminance std-dev by 0.02 and the stone still read as CAD.  What was missing is *architectural
scale* surface information: the 0.3-3 m pour blotches, run-off fans, damp patches and repair patches the eye reads
as "weathered concrete" at 100 m.  This script takes that information out of real photographed concrete.

Sources: **ambientCG, CC0 1.0** (https://ambientcg.com/license) -- photogrammetric flat-wall scans, so they carry
surface field and no architectural relief.  (PFA's own reference photos were evaluated first, `--preview`: at the
1920 px the corpus is capped at, every frontal wall region of the building also contains mouldings, dentils or
sculpture, and tiling those over a wall stamps fake architecture on it.  The PFA-specific part of the look is
therefore carried by the amplitudes, the tile sizes and the band placements, all measured from the reference, and
by the procedural layers already in `PFA_concrete`.)

Method per map:
  1. luminance of the CC0 colour map;
  2. **divide by a heavy gaussian blur of itself** -- removes the scan's own lighting/exposure and leaves the
     surface's reflectance ratio with mean 1.0;
  3. clip at +-3 sigma and rescale to the requested relative std (the amplitude that reads at hero distance);
  4. optional anisotropic pre-stretch (vertical run-off is a stain field stretched down the wall);
  5. crop-and-feather wrap so it tiles with no seam and no mirror symmetry;
  6. 8-bit greyscale PNG, **128 == ratio 1.0**, + sources.json (asset, URL, licence, derivation, measured std).

The shader uses these as value-only multipliers with mean 1.0, so round 4's calibrated chroma is untouched and only
the variance moves.

Usage:  python3 scripts/mat_make_grunge.py                 # fetch (once) + build the shipped set
        python3 scripts/mat_make_grunge.py --preview       # contact sheet of PFA reference-photo candidates
"""
import io, json, sys, urllib.request, zipfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")   # reference photos live in the main checkout
OUT = ROOT / "assets" / "textures" / "pfa"
CACHE = OUT / "_src"                    # CC0 colour maps as downloaded (kept: the build must be reproducible offline)
ACG = "https://ambientcg.com/get?file={}_1K-JPG.zip"
UA = {"User-Agent": "Mozilla/5.0 pfa-materials/1.0 (Blender build, CC0 assets)"}

# shipped maps.  size is the tile before the feather crop; tile_m is the *physical* size the shader box-projects it
# at, chosen so the scan's own features land in the 0.3-3 m band.
BUILD = {
    # broad soft pour/damp blotches -- the layer that does most of the work on a plain wall
    "pfa_macro_stain":  dict(asset="Concrete019", std=0.150, blur=0.30, stretch=None,     tile_m=9.0),
    # mid-scale weathered mottle, decorrelating second layer (different tile, so no visible repeat beat)
    "pfa_macro_blotch": dict(asset="Concrete035", std=0.130, blur=0.26, stretch=None,     tile_m=5.5),
    # vertical run-off: a heavy stain field stretched 3.2x down the wall -> 0.2-0.6 m wide, 1-3 m long dark runs
    "pfa_macro_streak": dict(asset="Concrete036", std=0.200, blur=0.22, stretch=(1.0, 3.2), tile_m=7.0),
}
LICENCE = "CC0 1.0 (ambientCG, https://ambientcg.com/license)"

# ---------------------------------------------------------------- PFA reference-photo candidates (evaluated, --preview)
RAW = MAIN / "reference" / "photos" / "raw"
CROPS = MAIN / "reference" / "photos" / "material_crops"
PATCHES = {
    "frieze": (RAW / "ref_047_rotunda_Palace_of_Fine_Arts_14.jpg", (300, 235, 1320, 405)),
    "pier":   (RAW / "ref_047_rotunda_Palace_of_Fine_Arts_14.jpg", (1345, 250, 1705, 610)),
    "soffit": (RAW / "ref_047_rotunda_Palace_of_Fine_Arts_14.jpg", (300, 700, 1150, 1180)),
    "attic":  (RAW / "ref_085_rotunda_San_Francisco_CA_USA_Palace_of_Fine_Arts_2022_0921.jpg", (430, 470, 1470, 800)),
    "wall2a": (CROPS / "rotunda_wall_2.jpg", (230, 20, 960, 200)),
    "wall2b": (CROPS / "rotunda_wall_2.jpg", (240, 300, 460, 700)),
    "rostra": (CROPS / "rostra_wall_1.jpg", (60, 60, 900, 330)),
    "lower":  (RAW / "ref_016_rotunda_Palace_of_Fine_Arts_March_2018_1529.jpg", (230, 200, 1500, 560)),
}


def fetch_colour(asset):
    dest = CACHE / f"{asset}_Color.jpg"
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = ACG.format(asset)
    print(f"[grunge] fetch {asset} <- {url}")
    data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300).read()
    z = zipfile.ZipFile(io.BytesIO(data))
    name = next(n for n in z.namelist() if n.endswith("_Color.jpg"))
    dest.write_bytes(z.read(name))
    return dest


def to_ratio(im, blur_frac=0.25, stretch=None):
    """luminance / heavy-blur(luminance): the source's own lighting divided out, mean ~1.0."""
    if stretch:
        w, h = im.size
        im = im.resize((max(8, int(w * stretch[0])), max(8, int(h * stretch[1]))), Image.LANCZOS)
    g = im.convert("L")
    lo = g.filter(ImageFilter.GaussianBlur(max(4.0, blur_frac * min(g.size))))
    a = np.asarray(g, dtype=np.float64) + 0.5
    b = np.asarray(lo, dtype=np.float64) + 0.5
    return np.where(b > 2.0, a / b, 1.0)


def normalise(a, target_std, clip=3.0):
    m, sd = a.mean(), max(a.std(), 1e-6)
    out = 1.0 + np.clip((a - m) / sd, -clip, clip) * target_std
    return out - out.mean() + 1.0


def to_image(a, size):
    im = Image.fromarray(np.clip(np.rint(a * 128.0), 0, 255).astype(np.uint8))
    return im.resize((size, size), Image.LANCZOS)


def make_tileable(im, feather=0.16):
    """Crop-and-feather wrap: the first f columns/rows cross-fade into the strip that will abut them in the next
    tile, so the (size - f) result tiles seamlessly without the mirror symmetry a flip would leave on a big wall."""
    a = np.asarray(im, dtype=np.float64)
    h, w = a.shape
    f = max(4, int(feather * min(w, h)))
    r = a[: h - f, : w - f].copy()
    tx = (np.arange(f) / float(f))[None, :]
    r[:, :f] = r[:, :f] * tx + a[: h - f, w - f:] * (1.0 - tx)
    ty = (np.arange(f) / float(f))[:, None]
    r[:f, :] = r[:f, :] * ty + a[h - f:, : w - f] * (1.0 - ty)
    return Image.fromarray(np.clip(np.rint(r), 0, 255).astype(np.uint8))


def stats(im):
    a = np.asarray(im, dtype=np.float64) / 128.0
    return float(a.mean()), float(a.std())


def preview():
    """The PFA reference-photo candidates, raw beside their ratio map.  Kept because the finding is the point:
    at 1920 px every frontal PFA wall region also contains relief, so these are not usable as tiles."""
    tiles = []
    for name, (path, box) in PATCHES.items():
        im = Image.open(path).convert("RGB").crop(box)
        g = to_image(normalise(to_ratio(im, 0.25), 0.15), 300)
        tiles.append((name, im.resize((300, 300), Image.LANCZOS), g))
    cols = 4
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 610, rows * 322), (18, 18, 18))
    d = ImageDraw.Draw(sheet)
    for i, (n, a, b) in enumerate(tiles):
        x, y = (i % cols) * 610, (i // cols) * 322
        sheet.paste(a, (x, y + 18)); sheet.paste(b.convert("RGB"), (x + 305, y + 18))
        d.text((x + 4, y + 4), n, fill=(255, 240, 120))
    out = ROOT / "renders" / "qa_comparisons" / "mat_grunge_candidates.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print("[grunge] PFA candidate sheet ->", out)


def main():
    if "--preview" in sys.argv:
        return preview()
    OUT.mkdir(parents=True, exist_ok=True)
    src = {}
    for name, cfg in BUILD.items():
        colour = fetch_colour(cfg["asset"])
        im = Image.open(colour).convert("RGB")
        g = make_tileable(to_image(normalise(to_ratio(im, cfg["blur"], cfg["stretch"]), cfg["std"]), 1024))
        dest = OUT / f"{name}.png"
        g.save(dest, optimize=True)
        m, sd = stats(g)
        print(f"[grunge] {name}: {cfg['asset']} -> {g.size} tile {cfg['tile_m']} m  mean {m:.3f} std {sd:.3f}")
        src[name] = dict(asset=cfg["asset"], url=f"https://ambientcg.com/view?id={cfg['asset']}", licence=LICENCE,
                         map="Color (1K JPG)", tile_metres=cfg["tile_m"], size=list(g.size),
                         mean=round(m, 4), std=round(sd, 4),
                         derivation=("luminance / gaussian(sigma = %.2f x min side) of itself, clipped at 3 sigma, "
                                     "rescaled to relative std %.3f%s, crop-and-feather tiled; 128 = ratio 1.0"
                                     % (cfg["blur"], cfg["std"],
                                        "" if not cfg["stretch"] else ", pre-stretched %gx%g" % cfg["stretch"])))
    (OUT / "sources.json").write_text(json.dumps(src, indent=2))
    print("[grunge] wrote", OUT / "sources.json")


if __name__ == "__main__":
    main()
