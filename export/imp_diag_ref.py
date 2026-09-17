"""6c item 1, part B (no GPU): the ground truth. Project a `tree_far` placement into the Phase 5 Cycles
reference at station 2 (where the tree is a real MESH, not an impostor) and measure the crown colour, so the
atlas frame for the same view direction has something to be right or wrong against.

    python3 export/imp_diag_ref.py --index 0 [--ref <png>] [--out <json>] [--crop <png>]

The reference is display-referred (AgX High Contrast, -2.833 EV, sRGB), so the number it yields is a
display-referred hue; export/imp_diag_view.py puts the atlas through the same transform before comparing.
"""
import argparse
import colorsys
import json
import math
import os
import struct
import sys
import zlib
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate3_common as g3      # noqa: E402

MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
MANIFEST = g3.OUT / "manifest.json"
if not MANIFEST.exists():
    MANIFEST = MAIN / "export/out/gate3/manifest.json"
REF = MAIN / "renders/previews/qa/round13_02_lagoon_ne_threequarter_cycles.png"


def read_png_any(path):
    """Minimal 8-bit RGB/RGBA PNG reader, TOP-DOWN (the order the file stores). -> (h, w, c) uint8."""
    d = open(str(path), "rb").read()
    assert d[:8] == b"\x89PNG\r\n\x1a\n", f"{path}: not a PNG"
    i, idat, w, h, bd, ct = 8, b"", 0, 0, 0, 0
    while i < len(d):
        ln = struct.unpack(">I", d[i:i + 4])[0]
        typ = d[i + 4:i + 8]
        if typ == b"IHDR":
            w, h, bd, ct = struct.unpack(">IIBB", d[i + 8:i + 18])
        elif typ == b"IDAT":
            idat += d[i + 8:i + 8 + ln]
        elif typ == b"IEND":
            break
        i += 12 + ln
    assert bd == 8 and ct in (2, 6), f"{path}: bit depth {bd} colour type {ct} unsupported"
    c = 3 if ct == 2 else 4
    raw = zlib.decompress(idat)
    stride = w * c
    out = np.zeros((h, stride), dtype=np.uint8)
    prev = np.zeros(stride, dtype=np.uint8)
    p = 0
    for y in range(h):
        f = raw[p]
        line = np.frombuffer(raw[p + 1:p + 1 + stride], dtype=np.uint8).astype(np.int32)
        p += 1 + stride
        if f == 0:
            cur = line
        elif f == 1:
            cur = line.copy()
            for x in range(c, stride):
                cur[x] = (cur[x] + cur[x - c]) & 255
        elif f == 2:
            cur = (line + prev.astype(np.int32)) & 255
        elif f == 3:
            cur = line.copy()
            for x in range(stride):
                a = cur[x - c] if x >= c else 0
                cur[x] = (cur[x] + ((a + int(prev[x])) >> 1)) & 255
        elif f == 4:
            cur = line.copy()
            for x in range(stride):
                a = int(cur[x - c]) if x >= c else 0
                b = int(prev[x])
                cc = int(prev[x - c]) if x >= c else 0
                pp = a + b - cc
                pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - cc)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else cc)
                cur[x] = (cur[x] + pr) & 255
        else:
            raise ValueError(f"filter {f}")
        cur = cur.astype(np.uint8)
        out[y] = cur
        prev = cur
    return out.reshape(h, w, c)


def euler_matrix(rx, ry, rz):
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def srgb_to_linear(u8):
    f = u8.astype(np.float32) / 255.0
    return np.where(f <= 0.04045, f / 12.92, ((f + 0.055) / 1.055) ** 2.4)


def hue_of(rgb):
    h, s, v = colorsys.rgb_to_hsv(*[float(max(c, 0.0)) for c in rgb])
    return round(h * 360.0, 1), round(s, 3), round(v, 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", type=int, default=0, help="index into manifest tree_far")
    ap.add_argument("--ref", default=str(REF))
    ap.add_argument("--station", default="CAM_qa_02_lagoon_ne_threequarter")
    ap.add_argument("--out", default=str(g3.OUT / "impostor_diag_ref.json"))
    ap.add_argument("--crop", default="")
    a = ap.parse_args()
    man = json.load(open(MANIFEST))
    imp = man["impostors"]
    t = man["tree_far"][a.index]
    pr = imp["prototypes"][imp["prototype_map"][t["prototype"]]]
    s = t["height_m"] / pr["height_above_base_m"]
    ctr = np.array(t["trunk_base"], dtype=np.float64) + np.array([0.0, 0.0, pr["centre_z_m"] * s])
    rad = pr["radius_m"] * s
    st = man["stations"][a.station]
    cam = np.array(st["location"], dtype=np.float64)
    R = euler_matrix(*st["rotation_euler_xyz"])
    right, up, fwd = R @ np.array([1., 0, 0]), R @ np.array([0, 1., 0]), R @ np.array([0, 0, -1.])
    img = read_png_any(a.ref)
    H, W = img.shape[:2]
    sw = st["sensor_width_mm"]
    sh = sw * H / float(W)
    tx = (sw * 0.5) / st["lens_mm"]
    ty = (sh * 0.5) / st["lens_mm"]

    def project(p):
        d = p - cam
        z = float(fwd @ d)
        x = float(right @ d) / z / tx
        y = float(up @ d) / z / ty
        return ((x * 0.5 + 0.5 + st["shift_x"]) * W, (1.0 - (y * 0.5 + 0.5 + st["shift_y"] * W / H)) * H), z

    (cxp, cyp), z = project(ctr)
    (rxp, _), _ = project(ctr + right * rad)
    rpx = abs(rxp - cxp)
    # the crown box: the upper 60 % of the billboard square, inset to 0.55 r, so trunk and ground stay out
    x0, x1 = int(cxp - 0.55 * rpx), int(cxp + 0.55 * rpx)
    y0, y1 = int(cyp - 0.55 * rpx), int(cyp + 0.15 * rpx)
    x0, y0 = max(x0, 0), max(y0, 0)
    x1, y1 = min(x1, W), min(y1, H)
    crop = img[y0:y1, x0:x1, :3]
    lin = srgb_to_linear(crop)
    # drop sky: the sky at this station is the brightest thing in the box and reads far above the crown
    lum = lin @ np.array([0.2126, 0.7152, 0.0722])
    sky = lum > np.percentile(lum, 80)
    fol = ~sky
    out = dict(ref=str(a.ref), index=a.index, prototype=t["prototype"], billboard=t["billboard"],
               dist_m=round(float(np.linalg.norm(ctr - cam)), 2), centre_px=[round(cxp, 1), round(cyp, 1)],
               radius_px=round(rpx, 1), box=[x0, y0, x1, y1], px=int(crop.shape[0] * crop.shape[1]))
    for name, mask in (("all", np.ones_like(fol)), ("foliage_p80", fol)):
        sel = crop.reshape(-1, 3)[mask.reshape(-1)]
        if not sel.size:
            continue
        m8 = sel.mean(axis=0)
        ml = srgb_to_linear(sel).mean(axis=0)
        h8, s8, v8 = hue_of(m8 / 255.0)
        hl, sl, vl = hue_of(ml)
        out[name] = dict(px=int(sel.shape[0]),
                         mean_srgb8=[round(float(c), 1) for c in m8], hue_srgb_deg=h8, sat_srgb=s8,
                         mean_linear=[round(float(c), 5) for c in ml], hue_linear_deg=hl, sat_linear=sl,
                         b_over_g_srgb=round(float(m8[2] / max(m8[1], 1e-6)), 3),
                         b_over_g_linear=round(float(ml[2] / max(ml[1], 1e-6)), 3),
                         g_gt_r_pct=round(100.0 * float((sel[:, 1] > sel[:, 0]).mean()), 1))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(a.out, "w"), indent=1)
    if a.crop:
        g3.write_png_rgb8(Path(a.crop), np.ascontiguousarray(crop[::-1]))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
