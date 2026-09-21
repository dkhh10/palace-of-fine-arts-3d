"""Phase 9 A.2 probe: compare a freshly baked lightmap EXR against the SHIPPED one, texel-wise.

    python3 export/p9_probe_cmp.py --new <dir-with-new-EXRs> --old <dir-with-shipped-EXRs> \
        --keys gate3_lm_ARCH_rotunda_dome_membrane_merged,gate3_slot_arch_inst_1_06 [--out report.json]

No Blender, no GPU. Reads both EXRs with `gate3_common.read_exr32` (the same reader the bake writes with) and
reports, per key and over the texels BOTH maps cover:

  * the linear ratio new/old per channel and on luminance (max over channels, the encode's own luminance),
  * |log2(new/old)| in STOPS: mean (MAE), p50, p99, max — the floor to beat is the shipped texture's own
    encode error, measured in Part B.2 of docs/briefs/phase9_bake_analysis_report.md:
    **p50 0.015-0.097 stops, p99 0.097-1.077 stops**,
  * the same split LIT (old luminance >= the map's own p80) vs SHADED (<= its own p20), because a diffuse-sky
    change is expected to act on the shade and not on the sunlit texels,
  * the per-decile mean ratio (deciles of the OLD luminance over covered texels).

`--keys` names the EXR stems without the `.exr`. A key missing on either side is reported, never silently skipped.
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate3_common as g3      # noqa: E402  (imports cleanly outside Blender)

EPS = 1e-6


def stats(new, old, mask):
    """Ratio / stop statistics for the masked texels of two (h, w, 3) float arrays."""
    n, o = new[mask], old[mask]                      # (k, 3)
    if n.size == 0:
        return dict(texels=0)
    ln, lo = n.max(axis=-1), o.max(axis=-1)
    # symmetric clamp: two texels that are both below the float floor must read as a ratio of 1, not as the
    # 16-stop artefact an asymmetric clamp gives (checked with an identity self-test: MAE must be exactly 0).
    r = np.maximum(ln, EPS) / np.maximum(lo, EPS)
    st = np.abs(np.log2(np.maximum(r, EPS)))
    ch = [float(n[:, c].sum() / max(float(o[:, c].sum()), EPS)) for c in range(3)]
    return dict(texels=int(ln.size),
                ratio_lum_mean=round(float(ln.sum() / max(float(lo.sum()), EPS)), 6),
                ratio_rgb_mean=[round(v, 6) for v in ch],
                stops_mae=round(float(st.mean()), 6),
                stops_p50=round(float(np.percentile(st, 50)), 6),
                stops_p99=round(float(np.percentile(st, 99)), 6),
                stops_max=round(float(st.max()), 6),
                lum_mean_old=round(float(lo.mean()), 6),
                lum_mean_new=round(float(ln.mean()), 6))


def load(path):
    """An own-map / atlas EXR, or a slot batch .npz (16 x 248 x 248 x 3 stacked into one array)."""
    if str(path).endswith(".npz"):
        z = np.load(str(path))
        keys = sorted(z.files, key=lambda k: (len(k), k))
        return np.concatenate([z[k] for k in keys], axis=0), keys
    return g3.read_exr32(path), None


def compare(key, new_path, old_path):
    new, kn = load(new_path)
    old, ko = load(old_path)
    if kn is not None and kn != ko:
        return dict(key=key, error=f"slot key sets differ: new={kn} old={ko}")
    rec = dict(key=key, new=str(new_path), old=str(old_path),
               shape_new=list(new.shape), shape_old=list(old.shape))
    if new.shape != old.shape:
        rec["error"] = "shape mismatch - not comparable"
        return rec
    ln_all, lo_all = new.max(axis=-1), old.max(axis=-1)
    cov = (lo_all > 0) & (ln_all > 0)                # texels both bakes actually covered
    rec["coverage"] = dict(total_px=int(lo_all.size), covered_px=int(cov.sum()),
                           covered_pct=round(100.0 * float(cov.sum()) / float(lo_all.size), 4),
                           old_only_px=int(((lo_all > 0) & (ln_all <= 0)).sum()),
                           new_only_px=int(((ln_all > 0) & (lo_all <= 0)).sum()))
    rec["px_new"] = g3.px_stats(new)
    rec["px_old"] = g3.px_stats(old)
    if not cov.any():
        rec["error"] = "no covered texels in common"
        return rec
    lo_cov = lo_all[cov]
    p20, p80 = float(np.percentile(lo_cov, 20)), float(np.percentile(lo_cov, 80))
    rec["thresholds"] = dict(old_p20=round(p20, 6), old_p80=round(p80, 6))
    rec["all"] = stats(new, old, cov)
    rec["shaded"] = stats(new, old, cov & (lo_all <= p20))
    rec["lit"] = stats(new, old, cov & (lo_all >= p80))
    # per-decile mean ratio over the covered texels, deciles of the OLD luminance
    edges = np.percentile(lo_cov, np.arange(0, 101, 10))
    dec = []
    for i in range(10):
        lo_e, hi_e = edges[i], edges[i + 1]
        m = cov & (lo_all >= lo_e) & ((lo_all <= hi_e) if i == 9 else (lo_all < hi_e))
        s = stats(new, old, m)
        dec.append(dict(decile=i + 1, lo=round(float(lo_e), 6), hi=round(float(hi_e), 6),
                        texels=s.get("texels", 0), ratio=s.get("ratio_lum_mean"),
                        stops_mae=s.get("stops_mae")))
    rec["deciles"] = dec
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", required=True, help="directory holding the NEW EXRs")
    ap.add_argument("--old", required=True, help="directory holding the SHIPPED EXRs")
    ap.add_argument("--keys", required=True, help="comma-separated stems (no extension)")
    ap.add_argument("--ext", default=".exr", help=".exr (own maps / atlases) or .npz (slot batches)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = dict(new_dir=a.new, old_dir=a.old, ext=a.ext, keys=[], missing=[])
    for key in [k.strip() for k in a.keys.split(",") if k.strip()]:
        np_, op_ = os.path.join(a.new, key + a.ext), os.path.join(a.old, key + a.ext)
        if not (os.path.exists(np_) and os.path.exists(op_)):
            out["missing"].append(dict(key=key, new_exists=os.path.exists(np_), old_exists=os.path.exists(op_)))
            print(f"[p9probe] MISSING {key}: new={os.path.exists(np_)} old={os.path.exists(op_)}")
            continue
        rec = compare(key, np_, op_)
        out["keys"].append(rec)
        if "error" in rec:
            print(f"[p9probe] {key}: {rec['error']}")
            continue
        for band in ("all", "shaded", "lit"):
            s = rec[band]
            print(f"[p9probe] {key:52s} {band:6s} n={s['texels']:>9d} ratio={s['ratio_lum_mean']:.4f} "
                  f"MAE={s['stops_mae']:.4f} p50={s['stops_p50']:.4f} p99={s['stops_p99']:.4f} "
                  f"max={s['stops_max']:.3f} stops")
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1)
        print(f"[p9probe] -> {a.out}")


main()
