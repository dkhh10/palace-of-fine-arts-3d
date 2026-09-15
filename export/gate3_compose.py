"""Gate 3 step 3: compose the five slot atlases and the vertex-irradiance file. CPU only, no Blender, no GPU.

    python3 export/gate3_compose.py

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
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate3_common as g3  # noqa: E402

t0 = time.time()
g3.ensure_dirs()
man2 = json.loads((g3.GATE2_OUT / "manifest.json").read_text())
slots = man2["orn_slots"]
rep = {"started": time.strftime("%Y-%m-%dT%H:%M:%S"), "atlases": {}, "vertex": {}}

# ---------------------------------------------------------------- 1. the slot atlases
loaded, missing_jobs = {}, []
for j in g3.read_jobs()["jobs"]:
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
rep["missing_slot_jobs"] = missing_jobs

A, S, G, U = g3.ATLAS_PX, g3.SLOT_PX, g3.GUTTER_PX, g3.USABLE_PX
per_row = A // S
half = G // 2
for pool in ("orn", "arch_inst"):
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
for j in g3.read_jobs()["jobs"]:
    if j["kind"] != "vertex":
        continue
    p = g3.OUT / "vertex" / f"{j['id']}.npz"
    if not p.exists():
        continue
    z = np.load(str(p))
    for k in z.files:
        vz[k] = z[k]
if vz:
    rng = float(max(2.0 ** np.ceil(np.log2(max(max(float(v.max()) for v in vz.values()), 1e-3))), 1.0))
    enc = {}
    for k, v in vz.items():
        e = g3.gamma2_encode(v, rng)
        enc[k] = e
        d = g3.gamma2_decode_u8(e, rng)
        rows.append(dict(mesh=k, verts=int(v.shape[0]), max=round(float(v.max()), 4),
                         mean=round(float(v.mean()), 4), roundtrip=g3.roundtrip(v, d)))
    p = g3.OUT / "vertex_irradiance.npz"
    np.savez_compressed(str(p), **enc)
    back = np.load(str(p))
    assert sorted(back.files) == sorted(enc) and all(np.array_equal(back[k], enc[k]) for k in enc)
    rep["vertex"] = dict(npz=p.name, bytes=p.stat().st_size, range=rng, encode="gamma2",
                         meshes=len(enc), verts=int(sum(v.shape[0] for v in vz.values())), rows=rows)
    print(f"[gate3] vertex irradiance: {len(enc)} meshes, {rep['vertex']['verts']} verts, range {rng}")

rep["wall_s"] = round(time.time() - t0, 1)
(g3.OUT / "compose.json").write_text(json.dumps(rep, indent=1) + "\n")
print(f"[gate3] compose done in {rep['wall_s']} s")
