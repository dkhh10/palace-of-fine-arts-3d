"""Phase 9 backdrop export — the four ENV gain tiles as shipped KTX2 (export engineer, 2026-09-21).

The ENV round (docs/briefs/phase9_env_report.md, "Export hand-off") added four tileable, mean-0.505 gain
images and a per-face UV0 in TILE UNITS on the 1 291 `ENV_backdrop_*` meshes.  They cannot ride the baked
1 K backdrop atlas (0.79 texels/m against the tile's 64), so they ship as their own REPEAT-sampled,
**Non-Color / linear** textures on TEXCOORD_0 and the viewer multiplies them over the baked albedo exactly
as Cycles does (`export/README.md` "Phase 9 — the backdrop gain tiles").

CPU only: no Blender, no GPU.  Two encodes per tile, both with the pinned `tools/bin/toktx` (v4.4.2):

  * the shipped file            -> `export/out/gate2/tex_ktx2/<key>.ktx2`
    `bd_facade` UASTC (it is the largest surface in every frame and the cheapest place to keep the
    contrast exact); the other three ETC1S, which the ENV hand-off calls enough and this file MEASURES
    (`--measure` prints both encodes' RMSE against the source PNG so the choice can be re-taken).
  * the half-resolution ETC1S stand-in -> `export/out/gate5/tex_lo/<key>.ktx2`
    the same `--resize <half>` rule `export/gate5_tex.py` uses, so `export/tiers.py --mobile`'s
    `mobile_swap()` picks it up by existence, with no change to the tier code.

`export/out/gate2/p9_backdrop_tiles.json` is the hand-off `manifest_v3.py` reads: one row per key with
the size, the bytes and the per-group shader constants.  Re-runnable and idempotent.

    python3 export/p9_bd_tiles.py                 # encode + write the hand-off json
    python3 export/p9_bd_tiles.py --measure       # + the UASTC/ETC1S comparison table (slower)
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = Path(os.environ.get("PFA_MAIN_ROOT", "/Users/dk/Projects/3d render blender 3rd attempt building"))
TOKTX = MAIN / "tools" / "bin" / "toktx"
SRC_DIRS = [ROOT / "assets" / "textures" / "backdrop", MAIN / "assets" / "textures" / "backdrop"]
OUT_KTX = ROOT / "export" / "out" / "gate2" / "tex_ktx2"
OUT_LO = ROOT / "export" / "out" / "gate5" / "tex_lo"
HANDOFF = ROOT / "export" / "out" / "gate2" / "p9_backdrop_tiles.json"

# key -> (source png stem, encoder for the shipped file).  The keys are the manifest's texture keys and
# the basenames of both the full file and its tex_lo stand-in - that identity is what `mobile_swap()`
# and `tiers.lowres` are keyed on.
TILES = {
    "p9_bd_facade":   ("bd_facade", "uastc"),
    "p9_bd_roof":     ("bd_roof", "etc1s"),
    "p9_bd_rooftile": ("bd_rooftile", "etc1s"),
    "p9_bd_canopy":   ("bd_canopy", "etc1s"),
}

# The per-group constants, copied from docs/briefs/phase9_env_report.md "Export hand-off" (which is in
# turn `scripts/mat_build.py` BACKDROP_TILES / BACKDROP_HAZE).  `r0/r1/amount` are the SAME haze ramp the
# baked albedo already carries; the tile's amplitude is reduced inside it so the far city keeps the flat
# atmospheric tint Cycles gives it.
GROUPS = {
    "MAT_backdrop_building":  dict(texture="p9_bd_facade",   strength=1.25, keep=0.70, r0=150.0, r1=720.0,  amount=0.86),
    "MAT_backdrop_roof":      dict(texture="p9_bd_roof",     strength=1.15, keep=0.70, r0=150.0, r1=720.0,  amount=0.86),
    "MAT_backdrop_roof_tile": dict(texture="p9_bd_rooftile", strength=1.10, keep=0.70, r0=180.0, r1=720.0,  amount=0.84),
    "MAT_backdrop_forest":    dict(texture="p9_bd_canopy",   strength=1.20, keep=0.70, r0=210.0, r1=1500.0, amount=0.82),
}

UASTC = ["--encode", "uastc", "--uastc_quality", "2", "--zcmp", "18"]
ETC1S = ["--encode", "etc1s", "--clevel", "2", "--qlevel", "128"]


def src_png(stem):
    for d in SRC_DIRS:
        p = d / f"{stem}.png"
        if p.exists():
            return p
    raise SystemExit(f"p9_bd_tiles: {stem}.png is in neither {SRC_DIRS[0]} nor {SRC_DIRS[1]}")


def png_size(p):
    """Width/height straight out of the IHDR - no PIL dependency for the shipping path."""
    with open(p, "rb") as f:
        head = f.read(26)
    assert head[:8] == b"\x89PNG\r\n\x1a\n", f"{p} is not a PNG"
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def encode(png, dst, enc, resize=None):
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(TOKTX), "--t2"] + (UASTC if enc == "uastc" else ETC1S) \
        + ["--genmipmap", "--assign_oetf", "linear"]
    if resize:
        cmd += ["--resize", f"{resize[0]}x{resize[1]}"]
    cmd += [str(dst), str(png)]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"toktx failed on {png.name}: {r.stderr.strip()[:400]}")
    return round(time.time() - t0, 2)


def rmse(png, ktx2):
    """The shipped file decoded back to RGBA8 by the pinned `ktx` and compared with the source - through
    `export/p8c_ktx2_compare.py` itself, so the number is the same number that file reports."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        j = Path(td) / "cmp.json"
        r = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "p8c_ktx2_compare.py"),
                            "--png", str(png), "--ktx2", str(ktx2), "--json", str(j)],
                           capture_output=True, text=True)
        if r.returncode != 0 or not j.exists():
            raise SystemExit(f"p8c_ktx2_compare failed on {ktx2.name}: {r.stderr.strip()[:300]}")
        return json.loads(j.read_text())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--measure", action="store_true", help="also encode the other codec and print both RMSEs")
    args = ap.parse_args()
    assert TOKTX.exists(), f"toktx is not at {TOKTX} - run tools/install.sh"

    rows, total_full, total_lo = {}, 0, 0
    for key, (stem, enc) in sorted(TILES.items()):
        png = src_png(stem)
        w, h = png_size(png)
        full = OUT_KTX / f"{key}.ktx2"
        lo = OUT_LO / f"{key}.ktx2"
        s_full = encode(png, full, enc)
        s_lo = encode(png, lo, "etc1s", resize=(max(1, w // 2), max(1, h // 2)))
        nb, nlo = full.stat().st_size, lo.stat().st_size
        total_full += nb
        total_lo += nlo
        rows[key] = dict(path=f"{key}.ktx2", w=w, h=h, map="gain", colorspace="linear", cls="backdrop",
                         encode=enc, bytes=nb, source_png=str(png.relative_to(png.parents[3])),
                         png_bytes=png.stat().st_size, encode_s=s_full,
                         lo=dict(path=f"tex_lo/{key}.ktx2", bytes=nlo, px=max(1, w // 2), encode_s=s_lo),
                         resident_mb=round(w * h * 4 * 1.3333 / 1e6, 2))
        print(f"[p9_bd_tiles] {key:16s} {w}x{h} {enc:5s} {nb:8d} B   lo {max(1, w // 2)}px {nlo:7d} B")
        if args.measure:
            other = "etc1s" if enc == "uastc" else "uastc"
            tmp = OUT_KTX / f"_{key}_{other}.ktx2"
            encode(png, tmp, other)
            m1, m2 = rmse(png, full), rmse(png, tmp)
            print(f"                 shipped {enc}: rmse {m1['rmse_255']:.3f}/255 mean|d| {m1['mean_abs_delta_255']:.3f}"
                  f"   | {other}: rmse {m2['rmse_255']:.3f}/255 {tmp.stat().st_size} B")
            rows[key]["rmse_255"] = round(m1["rmse_255"], 3)
            rows[key]["alt"] = dict(encode=other, bytes=tmp.stat().st_size, rmse_255=round(m2["rmse_255"], 3))
            tmp.unlink()

    doc = dict(schema="pfa-phase9/backdrop-tiles/1", generator="export/p9_bd_tiles.py",
               uv=dict(tile="TEXCOORD_0", baked="TEXCOORD_1",
                       note="env_p9_uv0 inserted the tile layer 'UVMap' at index 0 on the 1 291 backdrop "
                            "meshes, so the Gate 2 bake atlas the merges carry moves to TEXCOORD_1. The "
                            "UVs are ALREADY divided by the tile size: sample with wrap REPEAT and no "
                            "texture transform."),
               apply=("albedo *= 1 + (tile - 0.5) * 2 * strength * (1 - (1 - keep) * haze), "
                      "haze = smoothstep(r0, r1, length(worldPos.xz)) * amount, after the atmosphere term "
                      "(which the baked albedo already carries)"),
               files=rows, groups=GROUPS,
               bytes=total_full, lo_bytes=total_lo)
    HANDOFF.parent.mkdir(parents=True, exist_ok=True)
    HANDOFF.write_text(json.dumps(doc, indent=1, sort_keys=True))
    print(f"[p9_bd_tiles] {len(rows)} tiles, {total_full} B shipped + {total_lo} B half-res -> {HANDOFF}")


if __name__ == "__main__":
    main()
