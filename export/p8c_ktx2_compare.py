"""Phase 8c (b)4, committed instead of claimed: does the KTX2 encode cost any sharpness?

    python3 export/p8c_ktx2_compare.py                         # the default pair, the analysis' own
    python3 export/p8c_ktx2_compare.py --png <a.png> --ktx2 <b.ktx2> --json out.json

`docs/briefs/phase8c_export_analysis.md` (b)4 states "mean |delta| 0.35/255, RMSE 0.78, Laplacian std
19.64 -> 19.80" for the colonnade albedo, and review r1 finding 4 pointed out that the only artefact behind
it was a crop jpg. This is the measurement, end to end: the BAKED source PNG against the SHIPPED KTX2,
transcoded back to RGBA8 by the pinned `tools/bin/ktx` (v4.4.2) - the same binary `gltf_pack.sh` encodes
with - at level 0, no resize, no colour conversion. Laplacian std is the 4-neighbour Laplacian of the
luma over the whole image: the single number a "blur" claim has to move.

CPU only: no Blender, no GPU. The decode goes to a temp dir and is deleted.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MAIN = Path(os.environ.get("PFA_MAIN_ROOT", "/Users/dk/Projects/3d render blender 3rd attempt building"))
KTX = MAIN / "tools" / "bin" / "ktx"
# the pair (b)4 names: the south colonnade's 2048 px concrete albedo. The source PNG is a BAKE artefact
# and lives where the bake wrote it (out/gate2/tex is not synced to MAIN - it is 9.9 MB per map).
DEFAULT_PNG = ("export/out/gate2/tex/gate2_ARCH_colonnade_south__concrete_colonnade_albedo.png",
               [MAIN / ".claude/worktrees/phase6-bake", ROOT, MAIN])
DEFAULT_KTX2 = ("export/out/gate2/tex_ktx2/gate2_ARCH_colonnade_south__concrete_colonnade_albedo.ktx2",
                [ROOT, MAIN])


def find(rel, bases):
    for b in bases:
        p = Path(b) / rel
        if p.exists():
            return p
    return None


def luma(a):
    return a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722


def lap_std(y):
    """std of the 4-neighbour Laplacian, on the interior (no padding artefacts)."""
    l = (y[:-2, 1:-1] + y[2:, 1:-1] + y[1:-1, :-2] + y[1:-1, 2:] - 4.0 * y[1:-1, 1:-1])
    return float(l.std())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--png", default=None, help="the baked source PNG")
    ap.add_argument("--ktx2", default=None, help="the shipped KTX2")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    png = Path(a.png) if a.png else find(*DEFAULT_PNG)
    ktx2 = Path(a.ktx2) if a.ktx2 else find(*DEFAULT_KTX2)
    for what, p in (("source PNG", png), ("shipped KTX2", ktx2)):
        if p is None or not p.exists():
            print(f"[ktx2cmp] {what} not found ({p}) - nothing to compare", file=sys.stderr)
            return 2
    if not KTX.exists():
        print(f"[ktx2cmp] {KTX} is missing; run tools/install.sh", file=sys.stderr)
        return 2
    ver = subprocess.run([str(KTX), "--version"], capture_output=True, text=True).stdout.strip()
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "level0.png"
        r = subprocess.run([str(KTX), "extract", "--transcode", "rgba8", "--level", "0",
                            str(ktx2), str(out)], capture_output=True, text=True)
        if r.returncode != 0 or not out.exists():
            print(f"[ktx2cmp] ktx extract failed: {r.stderr.strip()[-400:]}", file=sys.stderr)
            return 2
        dec = np.asarray(Image.open(out).convert("RGB"), dtype=np.float64)
    src = np.asarray(Image.open(png).convert("RGB"), dtype=np.float64)
    if src.shape != dec.shape:
        print(f"[ktx2cmp] {png.name} is {src.shape} and the decoded KTX2 {dec.shape} - the shipped map is "
              f"not the same resolution as the bake, so this comparison would measure the RESIZE, not the "
              f"encode", file=sys.stderr)
        return 1
    d = np.abs(src - dec)
    ys, yd = luma(src), luma(dec)
    rep = dict(
        generator="export/p8c_ktx2_compare.py", ktx=ver,
        png=str(png), ktx2=str(ktx2), shape=list(src.shape),
        mean_abs_delta_255=round(float(d.mean()), 4),
        p99_abs_delta_255=round(float(np.percentile(d, 99)), 3),
        max_abs_delta_255=round(float(d.max()), 3),
        rmse_255=round(float(np.sqrt(((src - dec) ** 2).mean())), 4),
        laplacian_std=dict(source=round(lap_std(ys), 3), ktx2=round(lap_std(yd), 3),
                           ratio=round(lap_std(yd) / lap_std(ys), 4) if lap_std(ys) else None),
        luma_mean=dict(source=round(float(ys.mean()), 3), ktx2=round(float(yd.mean()), 3)),
        method=("ktx extract --transcode rgba8 --level 0 on the SHIPPED file, against the baked PNG; "
                "no resize, no colour conversion; Laplacian std is the 4-neighbour Laplacian of the "
                "luma over the interior"))
    print(f"[ktx2cmp] {png.name}  {src.shape[1]}x{src.shape[0]}  ({ver})")
    print(f"[ktx2cmp] mean |delta| {rep['mean_abs_delta_255']}/255, p99 {rep['p99_abs_delta_255']}, "
          f"max {rep['max_abs_delta_255']}, RMSE {rep['rmse_255']}")
    print(f"[ktx2cmp] Laplacian std {rep['laplacian_std']['source']} -> {rep['laplacian_std']['ktx2']} "
          f"({rep['laplacian_std']['ratio']}x): the encode "
          f"{'does not blur' if 0.9 <= (rep['laplacian_std']['ratio'] or 0) <= 1.1 else 'MOVES the detail'}")
    if a.json:
        Path(a.json).write_text(json.dumps(rep, indent=1) + "\n")
        print(f"[ktx2cmp] -> {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
