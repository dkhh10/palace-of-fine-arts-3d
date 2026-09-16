"""Gate 3 step 3: compose the five slot atlases and the vertex-irradiance file. CPU only, no Blender, no GPU.

    python3 export/gate3_compose.py [--only atlases|vertex|all]

`--only vertex` re-runs part 2 alone and MERGES into the existing compose.json, so the atlas PNGs the
authoritative encoder (export/gate3_encode.py) already rewrote are not reverted to the first-pass range.

The per-instance slots are baked one 248 px image at a time (export/bake_lm.py, kind `slot`) and stored per
queue batch in out/gate3/slots/*.npz. This assembles them into the 4096 px atlases the frozen Gate 1 slot
layout addresses, and writes both encodings plus the archival EXR.

ORIENTATION, the one thing that is easy to get silently wrong:
  * a Blender image is BOTTOM-UP (row 0 is v = 0); a PNG and a glTF texture are TOP-DOWN (v = 0 is the top row)
    and the glTF exporter already flipped every exported UV as `v_gltf = 1 - v_blender`.
  * the viewer samples `uv_atlas = uv2_gltf * uv2_scale + uv2_offset`, so the texel it wants for v_blender is at
    `y_from_top = (1 - v_blender) * 248 + row * 256 + 4`.
  * therefore each slot goes in TOP-DOWN at (row*256+4, col*256+4) after flipping the baked array, and the
    finished atlas is handed to the writers (which flip once more) as `atlas_top[::-1]`.
  A single-slot self-check at the end proves the composed atlas round-trips to the baked array.

VERTEX IRRADIANCE, the second output, is NOT encoded (code review Gate 3, findings 3 + 4). It used to be a
single gamma-2 uint8 array at a shared range of 64.0, set by the brightest of the 14 meshes, which cost the
dim ones most of their code space (roundtrip rel_p99 0.244 on cypress_s41, and broadleaf_s19 used 22 of 255
codes). The file is a hand-off to the export engineer, not a shipped texture, so it now holds the baked
values themselves: float32 (n_verts, 3) scene-linear RGB per mesh, exactly as Cycles baked them
(irradiance / pi; multiply by `lightmaps.scale` = pi like any lightmap texel). Whatever the glb encodes
COLOR_0 as is the exporter's choice, made on the real numbers.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate3_common as g3  # noqa: E402

ONLY = "all"
for i, a in enumerate(sys.argv):
    if a == "--only" and i + 1 < len(sys.argv):
        ONLY = sys.argv[i + 1]
assert ONLY in ("all", "atlases", "vertex"), f"--only {ONLY}"

t0 = time.time()
g3.ensure_dirs()
man2 = json.loads((g3.GATE2_OUT / "manifest.json").read_text())
slots = man2["orn_slots"]
prev = (json.loads((g3.OUT / "compose.json").read_text())
        if (g3.OUT / "compose.json").exists() else {})
rep = {"started": time.strftime("%Y-%m-%dT%H:%M:%S"), "atlases": {}, "vertex": {}}
if ONLY != "all":                       # keep the part we are not re-running
    rep["atlases"] = prev.get("atlases", {}) if ONLY == "vertex" else {}
    rep["vertex"] = prev.get("vertex", {}) if ONLY == "atlases" else {}
    rep["missing_slot_jobs"] = prev.get("missing_slot_jobs", [])
    rep["only"] = ONLY

# ---------------------------------------------------------------- 1. the slot atlases
loaded, missing_jobs = {}, []
if ONLY == "vertex":
    loaded = None
for j in (g3.read_jobs()["jobs"] if loaded is not None else []):
    if j["kind"] != "slot":
        continue
    p = g3.OUT / "slots" / f"{j['id']}.npz"
    if not p.exists():
        missing_jobs.append(j["id"])
        continue
    z = np.load(str(p))
    loaded[(j["pool"], j["atlas"])] = loaded.get((j["pool"], j["atlas"]), {})
    for k in z.files:
        loaded[(j["pool"], j["atlas"])][int(k)] = z[k]
if loaded is not None:
    rep["missing_slot_jobs"] = missing_jobs

A, S, G, U = g3.ATLAS_PX, g3.SLOT_PX, g3.GUTTER_PX, g3.USABLE_PX
per_row = A // S
half = G // 2
for pool in (("orn", "arch_inst") if loaded is not None else ()):
    want = {}
    for r in slots[pool]:
        want.setdefault(r["atlas"], []).append(r)
    for atlas in sorted(want):
        key = f"gate3_lmatlas_{pool}_{atlas}"
        top = np.zeros((A, A, 3), dtype=np.float32)
        have = loaded.get((pool, atlas), {})
        filled, blank = 0, []
        check = None
        for r in sorted(want[atlas], key=lambda d: d["slot"]):
            a = have.get(int(r["slot"]))
            if a is None:
                blank.append(r["object"])
                continue
            row, col = divmod(int(r["slot"]), per_row)
            y0, x0 = row * S + half, col * S + half
            top[y0:y0 + U, x0:x0 + U] = a[::-1]          # baked array is bottom-up
            filled += 1
            if check is None:
                check = (r["object"], int(r["slot"]), row, col, a)
        bottom = top[::-1]
        rec = g3.encode_and_write_arr(key, bottom)
        rec.update(pool=pool, atlas=atlas, slots_expected=len(want[atlas]), slots_filled=filled,
                   slots_blank=blank[:20], slots_blank_n=len(blank),
                   atlas_px=A, slot_px=S, gutter_px=G, usable_px=U,
                   uv2_scale=slots[pool][0]["uv2_scale"])
        # self-check: read the written PNG back and pull the first slot out again through the viewer's own maths
        if check is not None:
            obj, sl, row, col, src = check
            rb = g3.read_png(g3.TEX / f"{key}_gamma2.png")        # bottom-up
            rb_top = rb[::-1]
            got = g3.gamma2_decode_u8(rb_top[row * S + half:row * S + half + U,
                                             col * S + half:col * S + half + U], rec["range"])[::-1]
            rec["slot_check"] = dict(object=obj, slot=sl,
                                     abs_max=round(float(np.abs(got - src).max()), 5),
                                     src_mean=round(float(src.mean()), 5), got_mean=round(float(got.mean()), 5))
        rep["atlases"][key] = rec
        print(f"[gate3] atlas {key}: {filled}/{len(want[atlas])} slots, range {rec['range']}, "
              f"max {rec['stats']['max']:.3f}, check {rec.get('slot_check', {}).get('abs_max')}")

# ---------------------------------------------------------------- 2. vertex irradiance
vz, rows = {}, []
for j in (g3.read_jobs()["jobs"] if ONLY != "atlases" else []):
    if j["kind"] != "vertex":
        continue
    p = g3.OUT / "vertex" / f"{j['id']}.npz"
    if not p.exists():
        continue
    z = np.load(str(p))
    for k in z.files:
        vz[k] = z[k]
if vz:
    # NO encoding: float32 scene-linear RGB, the contract the export engineer consumes (review findings 3+4).
    out = {}
    for k, v in vz.items():
        a = np.ascontiguousarray(v, dtype=np.float32)
        out[k] = a
        rows.append(dict(mesh=k, verts=int(a.shape[0]),
                         min=round(float(a.min()), 6), max=round(float(a.max()), 6),
                         mean=round(float(a.mean()), 6),
                         mean_nonzero=round(float(a[a > 0].mean()) if (a > 0).any() else 0.0, 6),
                         p99=round(float(np.percentile(a.max(axis=-1), 99)), 6),
                         roundtrip=dict(abs_max=0.0, rel_p99=0.0, rel_mean=0.0)))
    p = g3.OUT / "vertex_irradiance.npz"
    np.savez_compressed(str(p), **out)
    back = np.load(str(p))
    assert sorted(back.files) == sorted(out), "vertex npz: key set changed on read-back"
    for k in out:
        assert back[k].dtype == np.float32 and back[k].shape == out[k].shape, f"{k}: dtype/shape"
        assert np.array_equal(back[k], out[k]), f"{k}: did not read back bit-identical"
    rep["vertex"] = dict(npz=p.name, bytes=p.stat().st_size, encode="none", dtype="float32",
                         shape="(n_verts, 3)", units="scene-linear irradiance / pi (x lightmaps.scale = pi)",
                         meshes=len(out), verts=int(sum(v.shape[0] for v in out.values())), rows=rows)
    print(f"[gate3] vertex irradiance: {len(out)} meshes, {rep['vertex']['verts']} verts, "
          f"float32 unencoded, {p.stat().st_size} B")

rep["wall_s"] = round(time.time() - t0, 1)
(g3.OUT / "compose.json").write_text(json.dumps(rep, indent=1) + "\n")
print(f"[gate3] compose done in {rep['wall_s']} s")
