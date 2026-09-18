#!/usr/bin/env python3
"""6b Gate 5 item B: the tier-0 low-resolution texture variants, and the measurement that chooses them.

    python3 export/gate5_tex.py --probe            # 6 samples, both candidates, bytes + wall + RMS
    python3 export/gate5_tex.py --encode           # write out/gate5/tex_lo for the tier-0 set
    python3 export/gate5_tex.py --encode --mobile  # and out/gate5/tex_mobile for the mobile manifest

No Blender, no GPU: `toktx` and `ktx extract` only.

The brief asks for "ETC1S KTX2 or quarter-res UASTC, whichever is smaller at equal or better look".
Both are built for the same sources and both are MEASURED, because the two trade different things:
ETC1S keeps every texel and adds block error; quarter-res UASTC keeps low block error and throws three
quarters of the texels away.  The comparison is made against the SOURCE png, in linear light for an
sRGB map, after bringing the decoded image back to the source resolution (bilinear) - so the quarter-res
candidate is charged for the detail it dropped rather than being flattered by comparing it to itself.

Resident memory is NOT a reason to pick either: both transcode to ASTC 4x4 on this GPU and on the
iPhone, so they cost the same bytes on the GPU (the manifest's own `budget.levers_not_applied` says so).
This is a PAYLOAD lever, which is exactly what tier 0 is short of.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate5_common as G

TOKTX = str(G.MAIN / "tools/bin/toktx")
KTX = str(G.MAIN / "tools/bin/ktx")


def _run(cmd):
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed ({r.returncode}): {' '.join(cmd[1:])}\n{r.stderr[-800:]}")
    return time.time() - t0


def encode_etc1s(src, dst, oetf, resize=None):
    cmd = [TOKTX, "--t2", "--encode", "etc1s", "--clevel", "2", "--qlevel", "128",
           "--genmipmap", "--assign_oetf", oetf]
    if resize:
        cmd += ["--resize", f"{resize}x{resize}"]
    return _run(cmd + [str(dst), str(src)])


def encode_uastc(src, dst, oetf, resize=None):
    cmd = [TOKTX, "--t2", "--encode", "uastc", "--uastc_quality", "2", "--zcmp", "18",
           "--genmipmap", "--assign_oetf", oetf]
    if resize:
        cmd += ["--resize", f"{resize}x{resize}"]
    return _run(cmd + [str(dst), str(src)])


def _to_linear(a, oetf):
    if oetf != "srgb":
        return a
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def rms_vs_source(ktx2, src_png, oetf, tmp):
    """Root-mean-square error of the decoded level 0 against the source, in linear light, at the
    SOURCE resolution (the decoded image is resampled up when it was encoded smaller)."""
    out = Path(tmp) / (Path(ktx2).stem + "_dec.png")
    _run([KTX, "extract", "--level", "0", str(ktx2), str(out)])
    dec = Image.open(out).convert("RGB")
    ref = Image.open(src_png).convert("RGB")
    if dec.size != ref.size:
        dec = dec.resize(ref.size, Image.BILINEAR)
    a = _to_linear(np.asarray(dec, np.float32) / 255.0, oetf)
    b = _to_linear(np.asarray(ref, np.float32) / 255.0, oetf)
    err = float(np.sqrt(np.mean((a - b) ** 2)))
    out.unlink(missing_ok=True)
    return err


# --------------------------------------------------------------------------------- the tier-0 texture set
def tier0_texture_keys(man, vis):
    """Every Gate 2 map and Gate 1 ORN AO map the HERO station's materials need, with its source png."""
    idx = G.material_index(man)
    sets = man["materials"]["sets"]
    mats = set()
    for name, a in vis["assets"].items():
        if a["hero"] <= 0:
            continue
        mat = (man["assets"].get(name) or {}).get("material")
        s = G.set_of(man, idx, mat) if mat else None
        if s:
            mats.add(s)
    keys = []
    for s in sorted(mats):
        for slot in ("albedo", "roughness", "normal"):
            e = sets[s].get(slot)
            if isinstance(e, dict) and e.get("texture"):
                keys.append((e["texture"], f"{sets[s].get('cls') or '?'}:{slot}"))
    return mats, keys


def probe(man, vis, tmp, n=6):
    """Both candidates on a spread of classes: bytes, wall seconds and RMS, printed and returned."""
    _, keys = tier0_texture_keys(man, vis)
    by_cls = {}
    for key, tag in keys:
        by_cls.setdefault(tag, key)
    picked = list(by_cls.items())[:n]
    rows = []
    for tag, key in picked:
        src = G.png_source(key, man)
        if not src:
            rows.append(dict(key=key, tag=tag, error="no source png"))
            continue
        oetf = G.oetf_for(key, man)
        w = Image.open(src).size[0]
        # The brief names two candidates; neither dominated on the first six, so the two intermediate
        # ETC1S resolutions are measured with them and the choice is made on the numbers.
        cands = dict(etc1s=("etc1s", 1), etc1s_h2=("etc1s", 2), etc1s_q4=("etc1s", 4),
                     uastc_q4=("uastc", 4))
        row = dict(key=key, tag=tag, src_px=w, oetf=oetf)
        for nm, (enc, div) in cands.items():
            p = Path(tmp) / f"{key}_{nm}.ktx2"
            fn = encode_etc1s if enc == "etc1s" else encode_uastc
            t = fn(src, p, oetf, resize=(max(4, w // div) if div > 1 else None))
            row[nm] = dict(bytes=p.stat().st_size, px=max(4, w // div), wall_s=round(t, 2),
                           rms=round(rms_vs_source(p, src, oetf, tmp), 5))
            p.unlink(missing_ok=True)
        rows.append(row)
        print(f"[gate5tex] {tag:18s} {key[-44:]:44s} {w}px  " + "  ".join(
            f"{nm} {row[nm]['bytes']/1e3:7.1f}kB/{row[nm]['rms']:.4f}" for nm in cands), flush=True)
    return rows


def encode_set(keys, man, outdir, encoder, resize_div, tag):
    """Encode `keys` into `outdir`; returns per-key bytes and the total wall time."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    made, missing, wall = {}, [], 0.0
    for key in keys:
        src = G.png_source(key, man)
        if not src:
            missing.append(key)
            continue
        oetf = G.oetf_for(key, man)
        w = Image.open(src).size[0]
        rz = max(4, w // resize_div) if resize_div > 1 else None
        dst = outdir / f"{key}.ktx2"
        fn = encode_etc1s if encoder == "etc1s" else encode_uastc
        wall += fn(src, dst, oetf, resize=rz)
        made[key] = dict(bytes=dst.stat().st_size, px=rz or w, src_px=w, oetf=oetf, encoder=encoder)
    print(f"[gate5tex] {tag}: {len(made)} files, {sum(v['bytes'] for v in made.values())/1e6:.2f} MB, "
          f"{wall:.0f} s wall" + (f", {len(missing)} with no source png" if missing else ""), flush=True)
    return dict(files=made, missing=missing, wall_s=round(wall, 1), encoder=encoder,
                resize_div=resize_div, dir=str(outdir))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--encode", action="store_true")
    ap.add_argument("--mobile", action="store_true")
    ap.add_argument("--tier0-div", type=int, default=4, help="tier-0 downscale divisor (1 = full res)")
    ap.add_argument("--out", default=str(G.OUT))
    a = ap.parse_args()
    man, vis = G.manifest(), G.visibility(Path(a.out) / "visibility.json")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / "_tmp"
    tmp.mkdir(exist_ok=True)
    rep = {}
    p = out / "lowres.json"
    if p.exists():
        rep = json.loads(p.read_text())
    rep.update(schema="pfa-phase6/gate5-lowres/1", generator="export/gate5_tex.py")

    if a.probe:
        rep["probe"] = probe(man, vis, tmp)
    if a.encode:
        mats, keys = tier0_texture_keys(man, vis)
        rep["tier0_materials"] = sorted(mats)
        rep["tier0"] = encode_set([k for k, _ in keys], man, out / "tex_lo", "etc1s", a.tier0_div,
                                  f"tier0 etc1s /{a.tier0_div}")
        # The Gate 1 AO maps ride INSIDE the class glbs (pbr.js keeps the glb's aoMap; no Gate 2 set
        # replaces it), so the tier-0 groups need low-res copies of them too.  The key is the manifest's
        # own `occlusion.gate1_texture`, never a name reconstructed from the material.
        ao = sorted({sets_occ for s in mats
                     for sets_occ in [((man["materials"]["sets"][s].get("occlusion") or {})
                                       .get("gate1_texture"))] if sets_occ})
        ao = [k for k in ao if G.png_source(k, man)]
        rep["tier0_orn_ao"] = encode_set(ao, man, out / "tex_lo", "etc1s", a.tier0_div,
                                         f"tier0 orn ao etc1s /{a.tier0_div}")
    if a.mobile:
        keys = sorted({pub.key for pub in G.resolve_files(man).values()
                       if pub.kind in ("gate2", "detail") and pub.key})
        rep["mobile"] = encode_set(keys, man, out / "tex_mobile", "etc1s", 2, "mobile etc1s /2")
    shutil.rmtree(tmp, ignore_errors=True)
    p.write_text(json.dumps(rep, indent=1))
    print(f"[gate5tex] wrote {p}", flush=True)


if __name__ == "__main__":
    main()
