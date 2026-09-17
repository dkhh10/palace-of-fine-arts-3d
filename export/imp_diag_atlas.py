"""6c item 1, part A (no GPU): read the SHIPPED impostor atlases back and measure the crown colour.

Answers half of "is the blue in the atlas or in the viewer": if the decoded atlas crown is green in linear
radiance, the bake is not the blue. Reads the PNG the encoder wrote (gate3_common.read_png, bottom-up) and
decodes it exactly as the manifest tells the viewer to (`rgb = t.rgb*t.rgb*range`, straight alpha in A), and,
when tools/bin/ktx can extract it, the KTX2 that actually ships, so the pack chain is measured too.

    python3 export/imp_diag_atlas.py [--protos a,b] [--out out/gate3/impostor_diag_atlas.json]
"""
import argparse
import colorsys
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate3_common as g3      # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = g3.OUT / "manifest.json"
if not MANIFEST.exists():                      # the synced copy lives in MAIN
    MANIFEST = Path("/Users/dk/Projects/3d render blender 3rd attempt building/export/out/gate3/manifest.json")


def hue_sat(rgb):
    """HSV hue in degrees and saturation of a linear-RGB triple (the same convention QA uses on its crops)."""
    r, g, b = [float(max(v, 0.0)) for v in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return round(h * 360.0, 1), round(s, 3), round(v, 4)


def octa_frame(d, grid):
    """manifest impostors.frame_lookup, in Blender Z-up. d = camera - billboard. -> (col, row from bottom)."""
    d = np.asarray(d, dtype=np.float64)
    d = d / np.linalg.norm(d)
    n = d / (abs(d[0]) + abs(d[1]) + abs(d[2]))
    if n[2] >= 0.0:
        u, v = n[0], n[1]
    else:
        u = (1.0 - abs(n[1])) * (1.0 if n[0] >= 0 else -1.0)
        v = (1.0 - abs(n[0])) * (1.0 if n[1] >= 0 else -1.0)
    return (int(round((u * 0.5 + 0.5) * (grid - 1))), int(round((v * 0.5 + 0.5) * (grid - 1))))


def octa_dir(col, row, grid):
    """The inverse: the direction bake_lm.py put in that frame."""
    u = col / float(grid - 1) * 2.0 - 1.0
    v = row / float(grid - 1) * 2.0 - 1.0
    au, av = abs(u), abs(v)
    z = 1.0 - au - av
    if z >= 0.0:
        d = np.array([u, v, z])
    else:
        d = np.array([(1.0 - av) * (1.0 if u >= 0 else -1.0),
                      (1.0 - au) * (1.0 if v >= 0 else -1.0), z])
    return d / np.linalg.norm(d)


def crown_stats(lin, alpha, tag):
    body = alpha > 0.5
    if not body.any():
        return dict(tag=tag, body_px=0)
    mean = lin[body].mean(axis=0)
    h, s, v = hue_sat(mean)
    # per-texel hue, weighted by nothing: the median is robust to the few sun glints
    mx = lin[body].max(axis=-1)
    sel = mx > 1e-4
    hues = []
    for px in lin[body][sel][::max(1, int(sel.sum()) // 20000)]:
        hh, _, _ = colorsys.rgb_to_hsv(*[float(max(c, 0.0)) for c in px])
        hues.append(hh * 360.0)
    return dict(tag=tag, body_px=int(body.sum()),
                mean_rgb=[round(float(c), 5) for c in mean],
                hue_deg=h, sat=s, val=v,
                hue_median_deg=round(float(np.median(hues)), 1) if hues else None,
                b_over_g=round(float(mean[2] / max(mean[1], 1e-6)), 3),
                r_over_g=round(float(mean[0] / max(mean[1], 1e-6)), 3),
                blue_max_px_pct=round(100.0 * float((lin[body].argmax(axis=-1) == 2).mean()), 2))


def load_atlas(path, rng):
    a = g3.read_png(path)                      # bottom-up uint8 RGBA
    lin = g3.gamma2_decode_u8(a[..., :3], rng)
    alpha = a[..., 3].astype(np.float32) / 255.0
    return lin, alpha


def frame_slice(arr, col, row, frame_px, gutter):
    y0, x0 = row * frame_px + gutter, col * frame_px + gutter
    inner = frame_px - 2 * gutter
    return arr[y0:y0 + inner, x0:x0 + inner]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--protos", default="")
    ap.add_argument("--ktx", action="store_true", help="also decode the shipped KTX2 through tools/bin/ktx")
    ap.add_argument("--out", default=str(g3.OUT / "impostor_diag_atlas.json"))
    a = ap.parse_args()
    man = json.load(open(MANIFEST))
    imp = man["impostors"]
    protos = man["impostors"]["prototypes"]
    want = [p for p in (a.protos.split(",") if a.protos else list(protos))]
    # where each prototype's nearest cam02 placement looks at it from
    st = man["stations"]["CAM_qa_02_lagoon_ne_threequarter"]
    cam = np.array(st["location"], dtype=np.float64)
    pmap = imp["prototype_map"]
    nearest = {}
    for t in man["tree_far"]:
        p = pmap[t["prototype"]]
        if p not in protos:
            continue
        pr = protos[p]
        s = t["height_m"] / pr["height_above_base_m"]
        ctr = np.array(t["trunk_base"], dtype=np.float64) + np.array([0.0, 0.0, pr["centre_z_m"] * s])
        d = float(np.linalg.norm(ctr - cam))
        if p not in nearest or d < nearest[p]["dist_m"]:
            nearest[p] = dict(dist_m=round(d, 2), billboard=t["billboard"], centre=[round(float(c), 3) for c in ctr],
                              view_dir=(cam - ctr) / max(d, 1e-9))
    out = dict(manifest=str(MANIFEST), grid=imp["grid"], prototypes={})
    for p in want:
        pr = protos[p]
        rng = float(pr["range"])
        rec = dict(range=rng, nearest_cam02_m=nearest.get(p, {}).get("dist_m"))
        for tag, px, fpx, gut in (("1024", imp["atlas_px"], imp["frame_px"], imp["gutter_px"]),
                                  ("2048", imp["variant_2k"]["atlas_px"], imp["variant_2k"]["frame_px"],
                                   imp["variant_2k"]["gutter_px"])):
            f = g3.OUT / "impostor" / f"gate3_imp_{p}_albedo_{tag}.png"
            if not f.exists():
                rec[tag] = dict(missing=str(f))
                continue
            lin, alpha = load_atlas(f, rng)
            sub = dict(atlas=crown_stats(lin.reshape(-1, 3), alpha.reshape(-1), f"atlas_{tag}"))
            if p in nearest:
                col, row = octa_frame(nearest[p]["view_dir"], imp["grid"])
                fl = frame_slice(lin, col, row, fpx, gut)
                fa = frame_slice(alpha, col, row, fpx, gut)
                sub["cam02_frame"] = dict(col=col, row=row,
                                          baked_dir=[round(float(c), 4) for c in octa_dir(col, row, imp["grid"])],
                                          view_dir=[round(float(c), 4) for c in nearest[p]["view_dir"]],
                                          **crown_stats(fl.reshape(-1, 3), fa.reshape(-1), f"frame_{tag}"))
            rec[tag] = sub
        out["prototypes"][p] = rec
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(a.out, "w"), indent=1)
    print(f"[diag] wrote {a.out}")
    for p, rec in out["prototypes"].items():
        for tag in ("1024", "2048"):
            s = rec.get(tag, {}).get("atlas")
            if s and s.get("body_px"):
                print(f"  {p:42s} {tag}  atlas hue {s['hue_deg']:6.1f} sat {s['sat']:.3f} "
                      f"B/G {s['b_over_g']:.3f} R/G {s['r_over_g']:.3f} bluemax {s['blue_max_px_pct']:5.2f}%")
        fr = rec.get("2048", {}).get("cam02_frame")
        if fr and fr.get("body_px"):
            print(f"  {'':42s} cam02 frame ({fr['col']},{fr['row']}) hue {fr['hue_deg']:6.1f} "
                  f"sat {fr['sat']:.3f} B/G {fr['b_over_g']:.3f} px {fr['body_px']}")


if __name__ == "__main__":
    main()
