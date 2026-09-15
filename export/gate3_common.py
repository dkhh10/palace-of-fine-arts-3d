"""Shared constants and IO for the Phase 6 Gate 3 lightmap / impostor / probe bake (branch `phase6-bake`).

Extends gate0_common (paths, Step, colour constants), gate1_common (the frozen set + slot_uv) and
gate2_common (the relinked bake blend). Nothing here writes to master*.blend.

Every map this gate ships is written from numpy and read back from disk before any number is claimed
(docs/tech_notes.md "Phase 6": `Image.save()` on a generated float image wrote all-zero files).

Import from a Blender run as:

    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import gate3_common as g3
"""
import json
import os
import struct
import zlib
from pathlib import Path

import numpy as np

import gate0_common as g0
import gate1_common as g1
import gate2_common as g2

ROOT = g0.ROOT
MAIN_ROOT = g2.MAIN_ROOT
OUT = ROOT / "export" / "out" / "gate3"
TEX = OUT / "tex"
KTX = OUT / "tex_ktx2"
REC = OUT / "bake"
QUEUE = ROOT / "export" / "out" / "bake_queue"
GATE1_OUT = g2.GATE1_OUT
GATE2_OUT = g2.OUT
SRC_BLEND = g2.SRC_BLEND                  # master_delivery.blend, read-only
BASE_BLEND = g2.OUT / "gate2_bake.blend"  # geometry + UV1/UV2 + relinked Phase 5 materials + the light rig
BAKE_BLEND = OUT / "gate3_bake.blend"     # what every lightmap / slot / vertex / probe job opens
IMP_BLEND = OUT / "gate3_imp.blend"       # the 25 far-tree prototypes alone
UV1 = g0.UV1
UV2 = g0.UV2
UV2_GATE1 = "UV2_gate1"          # the frozen Gate 1 layout, kept beside the re-laid one

# ---------------------------------------------------------------- sizes and samples
SIZE_OWN = 2048
SIZE_OWN_BIG = 4096
BIG_AREA_M2 = 100_000.0        # an own-map asset larger than this gets 4K (only ENV_terrain_ground: 514 896 m2)
SAMPLES_LM = 128               # Gate 0's setting for every lightmap number on record
SAMPLES_VERTEX = 128
SAMPLES_IMPOSTOR = 64
SAMPLES_PROBE = 64
MARGIN_OWN = 16
MARGIN_SLOT = 6                # 16 px of margin on a 248 px slot would flood a third of it

# UV2 re-lay: Gate 1's UV2 on the merged masses is margin-dominated (south colonnade 0.0095 coverage,
# median triangle 0.21 px across at 2K). Anything under this gets a new UV2 in gate3_bake.blend and a
# hand-off npz; see export/README.md "Re-laid UV2".
UV2_RELAY_THRESHOLD = 0.15
UV2_RELAY_ANGLE = 1.15
UV2_RELAY_MARGIN = 0.0008

# slot atlases (frozen at Gate 1, gate1_common.slot_uv is the single source of truth)
ATLAS_PX = g1.ORN_ATLAS_PX            # 4096
SLOT_PX = g1.ORN_ATLAS_SLOT_PX        # 256
GUTTER_PX = g1.ORN_ATLAS_GUTTER_PX    # 8
USABLE_PX = SLOT_PX - GUTTER_PX       # 248
SLOTS_PER_ATLAS = g1.ORN_ATLAS_SLOTS  # 256
SLOT_BATCH = 40                       # instances per queue job

# impostors
IMP_GRID = 12
IMP_FRAME_PX = 170                    # 12 x 170 = 2040 of the 2048 atlas; the last 8 px are unused
IMP_GUTTER_PX = 4
IMP_INNER_PX = IMP_FRAME_PX - 2 * IMP_GUTTER_PX   # 162
IMP_ATLAS_PX = 2048
IMP_SHIP_PX = 1024                    # the shipped atlas; the 2K variant stays on disk (the budget lever)

# hero reflection probe
PROBE_RENDER_PX = 1024
PROBE_SHIP_PX = 512
PROBE_FACES = ("px", "nx", "py", "ny", "pz", "nz")

# sky diffuse equirect (QA-12b-1)
SKY_DIFFUSE_W, SKY_DIFFUSE_H = 1024, 512

LIGHTMAP_SCALE = 3.14159265358979


def ensure_dirs():
    for d in (OUT, TEX, KTX, REC, QUEUE, OUT / "impostor", OUT / "probe"):
        d.mkdir(parents=True, exist_ok=True)


def jobs_path():
    return OUT / "bake_jobs.json"


def read_jobs():
    return json.loads(jobs_path().read_text())


def size_for_own(area_m2):
    return SIZE_OWN_BIG if area_m2 >= BIG_AREA_M2 else SIZE_OWN


# ---------------------------------------------------------------- encodings
def pick_range(rgb, floor=1.0):
    """A power-of-two ceiling at or above the map's own max. Never assumed to be 64."""
    m = float(np.max(rgb)) if rgb.size else 0.0
    return float(max(2.0 ** np.ceil(np.log2(max(m, 1e-3))), floor))


def rgbm_encode(rgb, rng):
    m = np.clip(rgb.max(axis=-1) / rng, 1.0 / 255.0, 1.0)
    m = np.ceil(m * 255.0) / 255.0
    enc = np.clip(rgb / (rng * m[..., None]), 0.0, 1.0)
    return (np.round(np.concatenate([enc, m[..., None]], axis=-1) * 255.0)).astype(np.uint8)


def rgbm_decode_u8(a, rng):
    f = a.astype(np.float32) / 255.0
    return f[..., :3] * f[..., 3:4] * rng


def gamma2_encode(rgb, rng):
    return np.round(np.sqrt(np.clip(rgb, 0.0, rng) / rng) * 255.0).astype(np.uint8)


def gamma2_decode_u8(a, rng):
    f = a.astype(np.float32) / 255.0
    return f * f * rng


def px_stats(rgb, ceiling=None):
    lum = rgb.max(axis=-1)
    nz = rgb[rgb > 0]
    d = dict(min=round(float(rgb.min()), 6), max=round(float(rgb.max()), 6), mean=round(float(rgb.mean()), 6),
             mean_nonzero=round(float(nz.mean()) if nz.size else 0.0, 6),
             p99=round(float(np.percentile(lum, 99)), 6), total_px=int(lum.size))
    if ceiling is not None:
        d["ceiling"] = ceiling
        d["clipped_px_vs_range"] = int((lum > ceiling).sum())
        d["clipped_pct_vs_range"] = round(100.0 * float((lum > ceiling).sum()) / max(d["total_px"], 1), 5)
    return d


def roundtrip(src, dec, floor=0.01):
    err = np.abs(dec - src)
    sel = src > floor
    rel = err[sel] / np.maximum(src[sel], 1e-4) if sel.any() else np.zeros(1)
    return dict(abs_max=round(float(err.max()), 6),
                rel_p99=round(float(np.percentile(rel, 99)), 6),
                rel_mean=round(float(rel.mean()), 6))


# ---------------------------------------------------------------- PNG IO (numpy in, bytes out; no Blender)
def _png(path, arr, colortype, nchan):
    a = np.ascontiguousarray(arr[::-1], dtype=np.uint8)      # arrays are bottom-up (Blender order)
    h, w = a.shape[0], a.shape[1]
    rows = np.hstack([np.zeros((h, 1), dtype=np.uint8), a.reshape(h, w * nchan)])
    comp = zlib.compress(rows.tobytes(), 6)

    def chunk(typ, data):
        return (struct.pack(">I", len(data)) + typ + data
                + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF))

    blob = (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, colortype, 0, 0, 0))
            + chunk(b"IDAT", comp) + chunk(b"IEND", b""))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(str(path), "wb") as f:
        f.write(blob)
    return len(blob)


def write_png_rgba8(path, arr):
    """arr: (h, w, 4) uint8, BOTTOM-UP. -> 8-bit RGBA PNG. Returns bytes written."""
    return _png(path, arr, 6, 4)


def write_png_rgb8(path, arr):
    """arr: (h, w, 3) uint8, BOTTOM-UP. -> 8-bit RGB PNG. Returns bytes written."""
    return _png(path, arr, 2, 3)


def read_png(path):
    """Read back a PNG written above -> (h, w, c) uint8, BOTTOM-UP. Verification, not a general reader."""
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
        i += 12 + ln
    assert bd == 8 and ct in (2, 6), f"{path}: expected 8-bit RGB/RGBA, got bitdepth {bd} colortype {ct}"
    n = 3 if ct == 2 else 4
    raw = np.frombuffer(zlib.decompress(idat), dtype=np.uint8).reshape(h, w * n + 1)
    assert not raw[:, 0].any(), f"{path}: unexpected PNG row filters"
    return raw[:, 1:].reshape(h, w, n)[::-1]


# ---------------------------------------------------------------- EXR IO (uncompressed 32-bit scanline)
def _attr(name, typ, payload):
    return name.encode() + b"\0" + typ.encode() + b"\0" + struct.pack("<I", len(payload)) + payload


def write_exr32(path, arr):
    """arr: (h, w, 3) float32, BOTTOM-UP -> uncompressed scanline OpenEXR (FLOAT, channels B,G,R).

    Blender's own Image.save() is not in this path on purpose: it wrote all-zero files for images whose
    pixels came from foreach_set (docs/tech_notes.md "Phase 6").
    """
    a = np.ascontiguousarray(arr[::-1], dtype=np.float32)    # EXR scanline 0 is the TOP row
    h, w = a.shape[0], a.shape[1]
    chans = b""
    for c in (b"B", b"G", b"R"):
        chans += c + b"\0" + struct.pack("<iBxxxii", 2, 0, 1, 1)
    chans += b"\0"
    hdr = b"\x76\x2f\x31\x01" + struct.pack("<I", 2)
    hdr += _attr("channels", "chlist", chans)
    hdr += _attr("compression", "compression", bytes([0]))
    hdr += _attr("dataWindow", "box2i", struct.pack("<iiii", 0, 0, w - 1, h - 1))
    hdr += _attr("displayWindow", "box2i", struct.pack("<iiii", 0, 0, w - 1, h - 1))
    hdr += _attr("lineOrder", "lineOrder", bytes([0]))
    hdr += _attr("pixelAspectRatio", "float", struct.pack("<f", 1.0))
    hdr += _attr("screenWindowCenter", "v2f", struct.pack("<ff", 0.0, 0.0))
    hdr += _attr("screenWindowWidth", "float", struct.pack("<f", 1.0))
    hdr += b"\0"
    row_bytes = w * 4 * 3
    off0 = len(hdr) + 8 * h
    offsets = struct.pack("<%dQ" % h, *[off0 + y * (8 + row_bytes) for y in range(h)])
    body = bytearray()
    for y in range(h):
        body += struct.pack("<ii", y, row_bytes)
        body += a[y, :, 2].tobytes() + a[y, :, 1].tobytes() + a[y, :, 0].tobytes()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(str(path), "wb") as f:
        f.write(hdr)
        f.write(offsets)
        f.write(bytes(body))
    return off0 + h * (8 + row_bytes)


def read_exr32(path):
    """Read back an EXR written by write_exr32 -> (h, w, 3) float32, BOTTOM-UP."""
    d = open(str(path), "rb").read()
    assert d[:4] == b"\x76\x2f\x31\x01", f"{path}: not an EXR"
    i = 8
    win = None
    while True:
        j = d.index(b"\0", i)
        name = d[i:j].decode()
        if not name:
            i = j + 1
            break
        i = j + 1
        j = d.index(b"\0", i)
        typ = d[i:j].decode()
        i = j + 1
        (sz,) = struct.unpack("<I", d[i:i + 4])
        i += 4
        if name == "dataWindow":
            win = struct.unpack("<iiii", d[i:i + 16])
        i += sz
    x0, y0, x1, y1 = win
    w, h = x1 - x0 + 1, y1 - y0 + 1
    i += 8 * h
    out = np.empty((h, w, 3), dtype=np.float32)
    for y in range(h):
        yy, nb = struct.unpack("<ii", d[i:i + 8])
        i += 8
        row = np.frombuffer(d[i:i + nb], dtype="<f4").reshape(3, w)
        out[yy, :, 2] = row[0]
        out[yy, :, 1] = row[1]
        out[yy, :, 0] = row[2]
        i += nb
    return out[::-1]


def write_hdr(path, arr):
    """arr: (h, w, 3) float32, BOTTOM-UP -> Radiance .hdr (RGBE, uncompressed scanlines)."""
    a = np.ascontiguousarray(arr[::-1], dtype=np.float32)
    h, w = a.shape[0], a.shape[1]
    m = np.maximum(a.max(axis=-1), 1e-32)
    e = np.ceil(np.log2(m))
    e = np.clip(e, -128, 127)
    scale = np.exp2(-e) * 256.0
    rgb = np.clip(a * scale[..., None], 0, 255).astype(np.uint8)
    ebyte = np.where(m <= 1e-32, 0, (e + 128)).astype(np.uint8)
    px = np.concatenate([rgb, ebyte[..., None]], axis=-1)
    head = b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n" + f"-Y {h} +X {w}\n".encode()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(str(path), "wb") as f:
        f.write(head)
        f.write(np.ascontiguousarray(px).tobytes())
    return len(head) + px.size


def read_hdr(path):
    """Read back an uncompressed .hdr written above -> (h, w, 3) float32, BOTTOM-UP."""
    d = open(str(path), "rb").read()
    k = d.index(b"\n\n")
    j = d.index(b"\n", k + 2)
    dims = d[k + 2:j].decode().split()
    h, w = int(dims[1]), int(dims[3])
    px = np.frombuffer(d[j + 1:j + 1 + w * h * 4], dtype=np.uint8).reshape(h, w, 4).astype(np.float32)
    f = np.exp2(px[..., 3] - 128.0 - 8.0)
    return (px[..., :3] * f[..., None]).astype(np.float32)[::-1]


def resident_mb(w, h, encode, mips=True):
    """Gate 2's rule: ASTC 4x4 on the Apple GPU = 1 byte/texel; uncompressed RGBA8 = 4. x4/3 for mips."""
    per = 4.0 if encode in ("rgbm8", "rgba8") else 1.0
    return round(w * h * per * (4.0 / 3.0 if mips else 1.0) / (1024.0 * 1024.0), 2)


def read_exr_channels(path):
    """Any UNCOMPRESSED scanline EXR (including Blender's multilayer, `exr_codec = 'NONE'`, 32-bit)
    -> {channel name: (h, w) float32, BOTTOM-UP}. Written because Blender exposes no way to read a
    render pass back into Python, and `Image.save*` is not trusted in this pipeline."""
    d = open(str(path), "rb").read()
    assert d[:4] == b"\x76\x2f\x31\x01", f"{path}: not an EXR"
    ver = struct.unpack("<I", d[4:8])[0]
    assert not (ver & 0x1000), f"{path}: multi-part EXR is not supported by this reader"
    i, win, chans, comp = 8, None, None, None
    while True:
        j = d.index(b"\0", i)
        name = d[i:j].decode()
        if not name:
            i = j + 1
            break
        i = j + 1
        j = d.index(b"\0", i)
        i = j + 1
        (sz,) = struct.unpack("<I", d[i:i + 4])
        i += 4
        val = d[i:i + sz]
        if name == "dataWindow":
            win = struct.unpack("<iiii", val)
        elif name == "compression":
            comp = val[0]
        elif name == "channels":
            chans = []
            k = 0
            while k < len(val) - 1:
                e = val.index(b"\0", k)
                cn = val[k:e].decode()
                ptype, _pl, xs, ys = struct.unpack("<iBxxxii", val[e + 1:e + 1 + 16])
                chans.append((cn, ptype, xs, ys))
                k = e + 1 + 16
        i += sz
    assert comp == 0, f"{path}: compression {comp}, this reader needs NONE (scene.render.image_settings.exr_codec)"
    x0, y0, x1, y1 = win
    w, h = x1 - x0 + 1, y1 - y0 + 1
    order = sorted(chans, key=lambda c: c[0])          # EXR stores channels alphabetically within a scanline
    dt = {1: "<f2", 2: "<f4"}
    out = {c[0]: np.empty((h, w), dtype=np.float32) for c in order}
    i += 8 * h
    for _ in range(h):
        yy, nb = struct.unpack("<ii", d[i:i + 8])
        i += 8
        off = i
        for cn, ptype, _xs, _ys in order:
            n = w * (2 if ptype == 1 else 4)
            out[cn][yy - y0] = np.frombuffer(d[off:off + n], dtype=dt[ptype]).astype(np.float32)
            off += n
        i += nb
    return {k: v[::-1] for k, v in out.items()}


def encode_and_write_arr(key, rgb, out_dir=None, exr=True):
    """The same encode/write/read-back as export/bake_lm.encode_and_write, importable without bpy."""
    out_dir = out_dir or TEX
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = pick_range(rgb)
    d = dict(range=rng, size=[int(rgb.shape[1]), int(rgb.shape[0])], stats=px_stats(rgb, ceiling=rng))
    if exr:
        p = out_dir / f"{key}.exr"
        write_exr32(p, rgb)
        back = read_exr32(p)
        assert back.shape == rgb.shape
        d["exr"] = dict(path=p.name, bytes=p.stat().st_size,
                        read_back_abs_max=round(float(np.abs(back - rgb).max()), 8))
    for enc, fn, dec in (("rgbm8", rgbm_encode, rgbm_decode_u8), ("gamma2", gamma2_encode, gamma2_decode_u8)):
        a = fn(rgb, rng)
        p = out_dir / f"{key}_{enc}.png"
        nb = (write_png_rgba8 if a.shape[-1] == 4 else write_png_rgb8)(p, a)
        rb = read_png(p)
        assert rb.shape == a.shape and np.array_equal(rb, a), f"{p}: did not read back identical"
        d[enc] = dict(path=p.name, bytes=nb, roundtrip=roundtrip(rgb, dec(rb, rng)))
    return d
