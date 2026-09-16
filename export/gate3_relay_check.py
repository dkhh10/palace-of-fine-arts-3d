#!/usr/bin/env python3
"""Gate 3 hand-off check: read the two Gate 3 attributes BACK out of the exported files and write the status
the bake engineer's manifest writer flips `uv2_in_glb` / `vertex_irradiance.in_glb` from.

    python3 export/gate3_relay_check.py [export/out/gate1] [export/out/gate3]

What it proves, per mesh, from the files themselves - never from the script that wrote them:

* the seven re-laid masses - TEXCOORD_1 in `<cls>.gltf` is the layout of `gate3/lightmap_uv2.npz` (the
  island-area fraction is recomputed from the glTF's own indices and TEXCOORD_1, which is the same metric the
  bake reports as `uv2_coverage`), and the attribute survives into the packed `<cls>.glb`;
* the 14 near trees - COLOR_0 exists, is NOT sRGB-encoded (every distinct value is a multiple of 1/255 and the
  distinct set is a subset of the gamma-2 codes in `gate3/vertex_irradiance.npz`), and its decoded linear mean
  is compared with the npz's. The exporter splits and welds vertices, so the vertex COUNTS and therefore the
  means differ slightly while the distinct value set does not - both numbers are reported.

No Blender, no GPU. Exit 1 on any mismatch.
"""
import json
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ("arch", "orn", "env", "ground")
VI_RANGE = 64.0                      # manifest lightmaps.vertex_irradiance.range
COMP = {5120: ("i1", 127.0), 5121: ("u1", 255.0), 5122: ("i2", 32767.0),
        5123: ("u2", 65535.0), 5125: ("u4", 4294967295.0), 5126: ("f4", 1.0)}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def glb_json(path):
    b = path.read_bytes()
    assert b[:4] == b"glTF", f"{path} is not a glb"
    ln = struct.unpack("<I", b[12:16])[0]
    return json.loads(b[20:20 + ln])


class Gltf:
    """A .gltf plus its .bin, with accessor reads. Only the plain (uncompressed) layout is supported: the
    packed glb is meshopt-compressed and is inspected through its JSON alone."""

    def __init__(self, path):
        self.path = path
        self.doc = json.loads(path.read_text())
        self.buf = [(path.parent / b["uri"]).read_bytes() if "uri" in b else b"" for b in self.doc["buffers"]]

    def read(self, idx):
        acc = self.doc["accessors"][idx]
        dt, norm = COMP[acc["componentType"]]
        n = NCOMP[acc["type"]]
        bv = self.doc["bufferViews"][acc["bufferView"]]
        off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
        stride = bv.get("byteStride") or np.dtype(dt).itemsize * n
        raw = self.buf[bv["buffer"]]
        item = np.dtype(dt).itemsize * n
        if stride == item:
            a = np.frombuffer(raw, dtype=dt, count=acc["count"] * n, offset=off).reshape(-1, n)
        else:
            rows = np.frombuffer(raw, dtype=np.uint8, count=acc["count"] * stride, offset=off).reshape(-1, stride)
            a = np.frombuffer(rows[:, :item].tobytes(), dtype=dt).reshape(-1, n)
        return a.astype(np.float64) / norm if acc.get("normalized") else a, acc

    def meshes(self):
        return {m.get("name"): m for m in self.doc.get("meshes", []) if m.get("name")}


def uv_area_fraction(uv, idx):
    """Sum |UV triangle area| over the primitive's triangles - the bake's `uv2_coverage`."""
    t = uv[idx].reshape(-1, 3, 2)
    a, b, c = t[:, 0], t[:, 1], t[:, 2]
    cross = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (b[:, 1] - a[:, 1])
    return float(np.abs(cross).sum() * 0.5)


def main(out_dir, g3_dir, g3_out=None):
    out, g3 = Path(out_dir), Path(g3_dir)
    g3o = Path(g3_out) if g3_out else ROOT / "export" / "out" / "gate3"
    g3o.mkdir(parents=True, exist_ok=True)
    fail, status = [], {}
    setjson = json.loads((out / "export_set.json").read_text())
    asset_of = {a["mesh"]: n for n, a in setjson["assets"].items() if a.get("mesh")}
    gl = json.loads((out / "gltf_gate1.json").read_text())
    cls_of = {}
    for cls in CLASSES:
        p = out / f"{cls}.gltf"
        if p.exists():
            for mn in Gltf(p).meshes():
                cls_of[mn] = cls
    files = {cls: Gltf(out / f"{cls}.gltf") for cls in CLASSES if (out / f"{cls}.gltf").exists()}
    packed = {cls: glb_json(out / f"{cls}.glb") for cls in CLASSES if (out / f"{cls}.glb").exists()}
    packed_attr = {cls: {k for m in d.get("meshes", []) for pr in m["primitives"] for k in pr["attributes"]}
                   for cls, d in packed.items()}

    # ---------------------------------------------------------------- 1. the seven re-laid UV2 layers
    uv2 = {}
    z2 = np.load(str(g3 / "lightmap_uv2.npz"))
    for mn in z2.files:
        cls = cls_of.get(mn)
        if cls is None:
            fail.append(f"{mn}: the Gate 3 UV2 npz names a mesh no class glTF contains")
            continue
        g = files[cls]
        me = g.meshes()[mn]
        want = np.asarray(z2[mn], dtype=np.float64)
        cov, seen, n_v, got = 0.0, 0, 0, []
        for pr in me["primitives"]:
            ai = pr["attributes"].get("TEXCOORD_1")
            if ai is None:
                continue
            seen += 1
            uv, acc = g.read(ai)
            # glTF flips V against Blender: v_gltf = 1 - v_blender. |area| is unaffected; the value
            # comparison below is not, so flip back here.
            uv = np.column_stack([uv[:, 0], 1.0 - uv[:, 1]])
            idx, _ = g.read(pr["indices"])
            cov += uv_area_fraction(uv, idx.reshape(-1).astype(np.int64))
            n_v += acc["count"]
            got.append(uv)
        if not seen:
            fail.append(f"{mn}: {cls}.gltf carries no TEXCOORD_1 - the re-laid UV2 did not reach the export")
            continue
        rec = (gl.get("gate3_uv2") or {}).get("meshes", {}).get(mn, {})
        in_glb = "TEXCOORD_1" in packed_attr.get(cls, set())
        # the exported UVs must be the npz's values, not Gate 1's: compare the distinct SETS (the exporter
        # splits and welds vertices, so a 1:1 comparison is meaningless while the value set survives).
        wset = set(map(tuple, np.unique(np.round(want, 4), axis=0)))
        hset = np.unique(np.round(np.concatenate(got, axis=0), 4), axis=0)
        share = round(float(np.mean([tuple(x) in wset for x in hset])), 4)
        if share < 0.98:
            fail.append(f"{mn}: only {share:.1%} of the exported TEXCOORD_1 values are in "
                        f"lightmap_uv2.npz - the glTF is not carrying the Gate 3 layout")
        uv2[mn] = dict(asset=asset_of.get(mn), glb=f"{cls}.glb", uv2_in_glb=bool(in_glb),
                       coverage=round(cov, 5), coverage_gate1=rec.get("coverage_gate1"),
                       coverage_in_blend=rec.get("coverage_gate3"), gain=rec.get("gain"),
                       loops_npz=int(want.shape[0]), verts_in_gltf=int(n_v),
                       distinct_uv_share_from_npz=share, uv_set="TEXCOORD_1",
                       source="gate3/lightmap_uv2.npz")
        if not in_glb:
            fail.append(f"{mn}: {cls}.glb has no TEXCOORD_1 (gltfpack strips attributes no material uses "
                        f"unless -kv is given) - the lightmap has no UV set to land on")
        if rec and abs(cov - (rec.get("coverage_gate3") or 0)) > 0.02:
            fail.append(f"{mn}: the glTF's TEXCOORD_1 packs {cov:.5f}, the blend's UV2 {rec.get('coverage_gate3')}")

    # ---------------------------------------------------------------- 2. the 14 near-tree COLOR_0 attributes
    vi = {}
    z3 = np.load(str(g3 / "vertex_irradiance.npz"))
    for mn in z3.files:
        cls = cls_of.get(mn)
        if cls is None:
            fail.append(f"{mn}: the vertex irradiance npz names a mesh no class glTF contains")
            continue
        g = files[cls]
        me = g.meshes()[mn]
        codes = np.asarray(z3[mn]).astype(np.float64)
        vals, ctype, norm_flag, n_v = [], set(), set(), 0
        for pr in me["primitives"]:
            ai = pr["attributes"].get("COLOR_0")
            if ai is None:
                continue
            a, acc = g.read(ai)
            ctype.add(acc["componentType"])
            norm_flag.add(bool(acc.get("normalized")))
            vals.append(a[:, :3])
            n_v += acc["count"]
        if not vals:
            fail.append(f"{mn}: {cls}.gltf carries no COLOR_0 - the vertex irradiance did not reach the export")
            continue
        c = np.concatenate(vals, axis=0)
        # not sRGB-encoded: every exported value is a multiple of 1/255 and belongs to this mesh's own codes.
        q = np.abs(c * 255.0 - np.round(c * 255.0)).max()
        codeset = set(np.unique(np.round(codes)).astype(int).tolist())
        stray = sorted(set(np.unique(np.round(c * 255.0)).astype(int).tolist()) - codeset)
        lin_glb = (c ** 2) * VI_RANGE
        lin_npz = (codes / 255.0) ** 2 * VI_RANGE
        in_glb = "COLOR_0" in packed_attr.get(cls, set())
        vi[mn] = dict(asset=asset_of.get(mn), glb=f"{cls}.glb", in_glb=bool(in_glb),
                      encoding="gamma2", range=VI_RANGE, attribute="COLOR_0",
                      component_type=sorted(ctype), normalized=sorted(norm_flag),
                      mean=round(float(lin_glb.mean()), 6), mean_npz=round(float(lin_npz.mean()), 6),
                      mean_delta=round(float(lin_glb.mean() - lin_npz.mean()), 6),
                      color0_mean=round(float(c.mean()), 6), color0_max=round(float(c.max()), 6),
                      max_npz=round(float(lin_npz.max()), 4), max_glb=round(float(lin_glb.max()), 4),
                      verts_npz=int(codes.shape[0]), verts_in_gltf=int(n_v),
                      code_quantisation_error=round(float(q), 6), codes_not_in_npz=stray[:6],
                      decode="irradiance = COLOR_0^2 * range * lightmap_scale",
                      source="gate3/vertex_irradiance.npz")
        if q > 2e-3:
            fail.append(f"{mn}: COLOR_0 values are not multiples of 1/255 (max {q:.4f}) - the exporter "
                        f"transformed the gamma-2 codes (sRGB encode?)")
        if stray:
            fail.append(f"{mn}: COLOR_0 carries codes the npz does not: {stray[:6]}")
        if abs(lin_glb.max() - lin_npz.max()) > 1e-3:
            fail.append(f"{mn}: COLOR_0 decodes to max {lin_glb.max():.4f}, the npz max is {lin_npz.max():.4f}")
        if not in_glb:
            fail.append(f"{mn}: {cls}.glb has no COLOR_0 - gltfpack dropped the vertex irradiance")

    status = dict(
        schema="pfa-phase6/gate3-relay/1", written_by="export/gate3_relay_check.py",
        source_blend="export/out/gate1/gate1_set.blend (frozen Gate 1 geometry)",
        note="The bake engineer's manifest writer flips lightmaps.assets[<asset>].uv2_in_glb and "
             "lightmaps.vertex_irradiance.in_glb from this file. COLOR_0 is the gamma-2 CODE / 255: "
             "irradiance = COLOR_0^2 * 64 * lightmap_scale. Standard glTF multiplies COLOR_0 into base "
             "colour, so the viewer must consume these 14 meshes' COLOR_0 as irradiance, not as a tint.",
        uv2=uv2, vertex_irradiance=vi,
        glb_bytes={cls: (out / f"{cls}.glb").stat().st_size for cls in CLASSES if (out / f"{cls}.glb").exists()},
        packed_attributes={cls: sorted(v) for cls, v in packed_attr.items()},
        gltfpack_flags=(out / "gltfpack_flags.txt").read_text().strip().split("\n")
        if (out / "gltfpack_flags.txt").exists() else [], failures=fail)
    (g3o / "uv2_relay_status.json").write_text(json.dumps(status, indent=1) + "\n")
    print(f"[gate3_relay] wrote {g3o / 'uv2_relay_status.json'}")
    print("[gate3_relay] uv2:", json.dumps({m: [v["uv2_in_glb"], v["coverage"], v["glb"]] for m, v in uv2.items()}))
    print("[gate3_relay] color0:", json.dumps({m: [v["in_glb"], v["mean"], v["mean_npz"]] for m, v in vi.items()}))
    if fail:
        for f in fail:
            print("[gate3_relay] FAIL " + f, file=sys.stderr)
        return 1
    print(f"[gate3_relay] PASS: {len(uv2)} re-laid UV2 layers and {len(vi)} COLOR_0 attributes are in the glbs")
    return 0


if __name__ == "__main__":
    # the Gate 3 npz files are the bake engineer's, and they live in the MAIN checkout (export/out/ is
    # gitignored and this worktree never ran the bake); the status file is written HERE and reaches MAIN
    # through export/sync_main.sh, like every other export output.
    main_g3 = Path("/Users/dk/Projects/3d render blender 3rd attempt building/export/out/gate3")
    local_g3 = ROOT / "export" / "out" / "gate3"
    src = local_g3 if (local_g3 / "lightmap_uv2.npz").exists() else main_g3
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else ROOT / "export" / "out" / "gate1",
                  sys.argv[2] if len(sys.argv) > 2 else src,
                  sys.argv[3] if len(sys.argv) > 3 else local_g3))
