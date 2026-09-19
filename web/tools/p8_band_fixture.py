#!/usr/bin/env python3
"""Phase 8b item 3 — a SYNTHETIC band atlas, so the viewer's band path runs before the bake lands.

    python3 web/tools/p8_band_fixture.py [--protos 3] [--out export/out/p8/band_fixture]

It re-lays the already-baked 2K OCTAHEDRAL frames as the contract's 12 azimuth x 3 elevation grid
(docs/briefs/phase8b_band_atlas.md): for each band cell it takes the octahedral frame nearest that
direction, scales its inner region to the band's inner size and pastes it into the band frame. The
content is therefore the 2K content — this fixture proves the PATH, never the look — but the layout,
the gutters, the sidecar and the manifest block are the real contract, so the shader's selection,
blend and uv arithmetic are exercised exactly as they will be on the real atlas.

Nothing in the MAIN checkout is written. The output is a full ASSET MIRROR (symlinks to MAIN's
export/out, with gate5/manifest.json replaced by a patched copy and the band files added), so the
viewer runs against it with PFA_ASSETS=<out>/assets:

    PFA_ASSETS=$PWD/export/out/p8/band_fixture/assets web/tools/p7.sh desk p8bandfix
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
MAIN = Path(os.environ.get("PFA_MAIN_ROOT", "/Users/dk/Projects/3d render blender 3rd attempt building"))
SRC_DIRS = [MAIN / ".claude/worktrees/phase8-bake/export/out/gate3/impostor",
            MAIN / ".claude/worktrees/phase6-bake/export/out/gate3/impostor",
            MAIN / "export/out/gate3/impostor"]
TOKTX = MAIN / "tools/bin/toktx"

# The contract's geometry. 12 columns x 3 rows of 341 px frames on 4096 x 1024, with the octahedral
# gutter rule doubled (2K: 170/4/162 -> 341/8/325).
COLUMNS, ROWS = 12, 3
FRAME, GUTTER = 341, 8
INNER = FRAME - 2 * GUTTER
ATLAS_W, ATLAS_H = 4096, 1024
AZIMUTH0_DEG = 0.0
ELEVATIONS_DEG = [0.0, 20.0, 40.0]
SRC_GRID, SRC_FRAME, SRC_GUTTER = 12, 170, 4
SRC_INNER = SRC_FRAME - 2 * SRC_GUTTER
SRC_PX = 2048


def octa_cell(d):
    """manifest.impostors.frame_lookup, verbatim: a Blender-space direction -> (col, row), rows
    counted from the BOTTOM, the same convention the viewer's frameUv reads."""
    x, y, z = d
    s = abs(x) + abs(y) + abs(z)
    nx, ny, nz = x / s, y / s, z / s
    if nz >= 0:
        u, v = nx, ny
    else:
        u = (1 - abs(ny)) * (1 if nx >= 0 else -1)
        v = (1 - abs(nx)) * (1 if ny >= 0 else -1)
    cu = min(max(u * 0.5 + 0.5, 0.0), 1.0) * (SRC_GRID - 1)
    cv = min(max(v * 0.5 + 0.5, 0.0), 1.0) * (SRC_GRID - 1)
    return int(round(cu)), int(round(cv))


def dir_of(az_deg, el_deg):
    """The band's own convention: azimuth clockwise from +Y seen from above, elevation above the
    horizon, in BLENDER Z-up — the inverse of the shader's atan2(x, y) / asin(z)."""
    az, el = math.radians(az_deg), math.radians(el_deg)
    return (math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el))


def src_block(img, col, row):
    """The INNER region of one octahedral frame, taken with rows counted from the bottom (the same
    arithmetic the viewer uses), so whatever the frame's internal orientation is, it is inherited."""
    y0 = SRC_PX - (row + 1) * SRC_FRAME + SRC_GUTTER
    x0 = col * SRC_FRAME + SRC_GUTTER
    return img.crop((x0, y0, x0 + SRC_INNER, y0 + SRC_INNER))


def build_atlas(src_png):
    img = Image.open(src_png).convert("RGBA")
    if img.size != (SRC_PX, SRC_PX):
        raise SystemExit(f"{src_png} is {img.size}, expected {SRC_PX}x{SRC_PX}")
    out = Image.new("RGBA", (ATLAS_W, ATLAS_H), (0, 0, 0, 0))
    for j, el in enumerate(ELEVATIONS_DEG):
        for i in range(COLUMNS):
            az = AZIMUTH0_DEG + i * (360.0 / COLUMNS)
            col, row = octa_cell(dir_of(az, el))
            cell = src_block(img, col, row).resize((INNER, INNER), Image.LANCZOS)
            # rows from the BOTTOM, as the sidecar declares (row_origin "bottom")
            y0 = ATLAS_H - (j + 1) * FRAME + GUTTER
            out.paste(cell, (i * FRAME + GUTTER, y0))
    return out


def alpha_stats(im):
    a = np.asarray(im)[..., 3].astype(np.float32) / 255.0
    cov = a > 0
    return {"mean": round(float(a.mean()), 4),
            "covered_pct": round(float(cov.mean()) * 100, 2),
            "covered_semi_pct": round(float(((a > 0) & (a < 1)).sum() / max(cov.sum(), 1)) * 100, 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--protos", type=int, default=0, help="limit the number of prototypes (0 = all)")
    ap.add_argument("--out", default=str(ROOT / "export/out/p8/band_fixture"))
    ap.add_argument("--manifest", default=str(MAIN / "export/out/gate5/manifest.json"))
    ap.add_argument("--no-ktx2", action="store_true", help="stop after the PNGs")
    a = ap.parse_args()

    out = Path(a.out)
    band_png = out / "png"
    band_png.mkdir(parents=True, exist_ok=True)
    man = json.load(open(a.manifest))
    protos = list(man["impostors"]["prototypes"])
    if a.protos:
        protos = protos[:a.protos]

    srcdir = next((d for d in SRC_DIRS if d.exists()), None)
    if not srcdir:
        raise SystemExit(f"no octahedral source dir found: {[str(d) for d in SRC_DIRS]}")
    print(f"[band] source frames: {srcdir}")

    sidecar = {"schema": "pfa-phase8b/band/1", "synthetic": True,
               "note": "FIXTURE re-laid from the 2K octahedral frames; content is 2K, layout is the contract",
               "atlas_px": [ATLAS_W, ATLAS_H], "frame_px": FRAME, "gutter_px": GUTTER, "inner_px": INNER,
               "columns": COLUMNS, "rows": ROWS, "azimuth0_deg": AZIMUTH0_DEG,
               "azimuth_direction": "clockwise seen from above (atan2(x, y) in Blender Z-up)",
               "elevations_deg": ELEVATIONS_DEG, "row_origin": "bottom", "prototypes": {}}
    made = []
    for name in protos:
        src = srcdir / f"gate3_imp_{name}_albedo_2048.png"
        if not src.exists():
            print(f"[band] {name}: no 2K source png, skipped")
            continue
        im = build_atlas(src)
        p = band_png / f"{name}_albedo_4096.png"
        im.save(p)
        st = alpha_stats(im)
        sidecar["prototypes"][name] = {"albedo": f"{name}_albedo_4096", "alpha": st,
                                       "crown_sphere_m": man["impostors"]["prototypes"][name].get("radius_m")}
        made.append((name, p, st))
        print(f"[band] {name}: {p.name} alpha mean {st['mean']} covered {st['covered_pct']} %")
    if not made:
        raise SystemExit("[band] nothing built")

    # ---- ktx2, the same encode the export gives the octahedral atlases (UASTC, no mips) ----------
    ktx_dir = out / "assets/gate3/tex_ktx2/band"
    if not a.no_ktx2:
        if not TOKTX.exists():
            raise SystemExit(f"[band] {TOKTX} missing — run tools/install.sh, or pass --no-ktx2")
        ktx_dir.mkdir(parents=True, exist_ok=True)
        for name, p, _ in made:
            k = ktx_dir / f"{name}_albedo_4096.ktx2"
            subprocess.run([str(TOKTX), "--t2", "--encode", "uastc", "--uastc_quality", "2",
                            "--zcmp", "18", "--assign_oetf", "linear", str(k), str(p)],
                           check=True, stdout=subprocess.DEVNULL)
            sidecar["prototypes"][name]["bytes"] = k.stat().st_size
            print(f"[band] {name}: {k.name} {k.stat().st_size / 1048576:.1f} MB")

    (out / "band.json").write_text(json.dumps(sidecar, indent=1))

    # ---- the asset mirror -------------------------------------------------------------------------
    # Every directory of MAIN's export/out is symlinked; gate3 and gate5 are real directories whose
    # children are symlinks, so only the two files this fixture adds or patches are ours.
    assets = out / "assets"
    src_assets = MAIN / "export/out"
    for child in src_assets.iterdir():
        dst = assets / child.name
        if child.name in ("gate3", "gate5"):
            continue
        if dst.is_symlink() or dst.exists():
            continue
        assets.mkdir(parents=True, exist_ok=True)
        dst.symlink_to(child)
    for grp in ("gate3", "gate5"):
        d = assets / grp
        d.mkdir(parents=True, exist_ok=True)
        for child in (src_assets / grp).iterdir():
            dst = d / child.name
            if child.name == "manifest.json" and grp == "gate5":
                continue
            if child.name == "tex_ktx2" and grp == "gate3":
                t = d / "tex_ktx2"
                t.mkdir(exist_ok=True)
                for f in child.iterdir():
                    q = t / f.name
                    if not (q.is_symlink() or q.exists()):
                        q.symlink_to(f)
                continue
            if not (dst.is_symlink() or dst.exists()):
                dst.symlink_to(child)

    # ---- the manifest patch: the band block, its texture rows and its tier rows -------------------
    files = man["textures"]["gate3"]["files"]
    band_block = {k: v for k, v in sidecar.items()
                  if k in ("atlas_px", "frame_px", "gutter_px", "inner_px", "columns", "rows",
                           "azimuth0_deg", "elevations_deg", "row_origin", "note")}
    band_block["synthetic"] = True
    band_block["prototypes"] = {}
    for name, _, st in made:
        key = f"gate3_imp_{name}_albedo_4096"
        by = sidecar["prototypes"][name].get("bytes", 0)
        files[key] = {"path": f"band/{name}_albedo_4096.ktx2", "w": ATLAS_W, "h": ATLAS_H,
                      "map": "impostor_albedo_band", "colorspace": "linear", "encode": "gamma2",
                      "bytes": by, "mips": False, "resident_mb": round(ATLAS_W * ATLAS_H * 1.0 / 1048576, 1)}
        band_block["prototypes"][name] = {"albedo": key, "bytes": by,
                                          "crown_sphere_m": sidecar["prototypes"][name]["crown_sphere_m"]}
        # tier 1, with the prototype's own 1K octahedral atlas as the tier-0 stand-in (the contract)
        man["files"].append({"path": f"../gate3/tex_ktx2/band/{name}_albedo_4096.ktx2", "tier": 1,
                             "kind": "tex:impostor_band", "key": key, "bytes": by,
                             "lo": {"path": f"../gate3/tex_ktx2/gate3_imp_{name}_albedo_1024.ktx2",
                                    "tier": 0, "stand_in": True}})
    man["impostors"]["band"] = band_block
    (assets / "gate5").mkdir(parents=True, exist_ok=True)
    json.dump(man, open(assets / "gate5/manifest.json", "w"))
    print(f"[band] mirror ready: PFA_ASSETS={assets}")
    kept = len(man["impostors"]["prototypes"]) - len(made)
    print(f"[band] {len(made)} prototype(s) in the band block; {kept} keep the octahedral atlas")


if __name__ == "__main__":
    main()
