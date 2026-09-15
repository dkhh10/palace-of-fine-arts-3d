#!/usr/bin/env python3
"""Gate 1 step 5d: prove the packed glbs still carry every placement, after gltfpack has folded the nodes.

    python3 export/verify_glb.py [export/out/gate1]

Per class the invariant is TRIANGLES DRAWN, not node count: gltfpack legitimately merges single-use nodes that
share a material (564 ARCH objects become 442 nodes, the 4 ground objects one node), so a node count proves
nothing, while sum(primitive triangles x instance count) must equal export_set.json's placed triangles for that
class. Node and instance counts are reported alongside. The complementary check - nothing stacked at the world
origin, which is what QA-11c-1 shipped when 1379 shrub nodes were written with no transform - is made in
export/gltf_gate1.py on the UNCOMPRESSED .gltf, where the transforms are still readable; here only plain nodes
can be tested, because a meshopt-compressed instancing accessor cannot be decoded without the codec.
Exit 1 on any mismatch. No Blender, no GPU.
"""
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def glb_json(path):
    b = path.read_bytes()
    assert b[:4] == b"glTF", f"{path} is not a glb"
    ln = struct.unpack("<I", b[12:16])[0]
    return json.loads(b[20:20 + ln]), b


def accessor_count(doc, idx):
    return doc["accessors"][idx]["count"] if idx is not None else 0


def main(out_dir):
    out = Path(out_dir)
    setjson = json.loads((out / "export_set.json").read_text())
    per_cls = {}
    for name, a in setjson["assets"].items():
        cls = "ground" if a.get("kind") == "ground" else \
              "arch" if a["cls"] == "ARCH" else "orn" if a["cls"] == "ORN" else "env"
        per_cls.setdefault(cls, []).append(name)
    near_expected = {}
    for name, a in setjson["assets"].items():
        loc = a.get("location_blender")
        if loc and sum(v * v for v in loc) ** 0.5 < 1.0:
            cls = "ground" if a.get("kind") == "ground" else \
                  "arch" if a["cls"] == "ARCH" else "orn" if a["cls"] == "ORN" else "env"
            near_expected[cls] = near_expected.get(cls, 0) + 1

    want_tris = {}
    for name, a in setjson["assets"].items():
        cls = "ground" if a.get("kind") == "ground" else \
              "arch" if a["cls"] == "ARCH" else "orn" if a["cls"] == "ORN" else "env"
        want_tris[cls] = want_tris.get(cls, 0) + a["tris"]

    rows, bad = {}, []
    for cls in ("arch", "orn", "env", "ground"):
        p = out / f"{cls}.glb"
        if not p.exists():
            continue
        doc, _ = glb_json(p)
        mesh_tris = []
        for me in doc.get("meshes", []):
            t = 0
            for pr in me.get("primitives", []):
                if "indices" in pr:
                    t += accessor_count(doc, pr["indices"]) // 3
                else:
                    t += accessor_count(doc, (pr.get("attributes") or {}).get("POSITION")) // 3
            mesh_tris.append(t)
        plain = inst = inst_nodes = origin_inst = 0
        tris = 0
        for nd in doc.get("nodes", []):
            if "mesh" not in nd:
                continue
            mt = mesh_tris[nd["mesh"]]
            gi = (nd.get("extensions") or {}).get("EXT_mesh_gpu_instancing")
            if gi:
                n = accessor_count(doc, (gi.get("attributes") or {}).get("TRANSLATION"))
                if n == 0:
                    n = max((accessor_count(doc, i) for i in (gi.get("attributes") or {}).values()), default=0)
                inst += n
                inst_nodes += 1
                tris += mt * n
            else:
                plain += 1
                tris += mt
                t = nd.get("translation")
                if nd.get("matrix") is None and (t is None or sum(v * v for v in t) ** 0.5 < 1.0):
                    origin_inst += 1
        rows[cls] = dict(tris_drawn=tris, tris_expected=want_tris.get(cls, 0),
                         placements_in_glb=plain + inst, objects_in_set=len(per_cls.get(cls, [])),
                         plain_nodes=plain, instanced_nodes=inst_nodes, instanced_placements=inst,
                         plain_nodes_at_origin=origin_inst, expected_at_origin=near_expected.get(cls, 0))
        # gltfpack drops degenerate triangles while it optimises, so the match is within a tolerance, not
        # exact: measured 0.19 % on arch and 0.16 % on orn, 0.00 % on env and ground. A DROPPED PLACEMENT is
        # orders of magnitude bigger than that (one stacked shrub group is 8.8 % of ENV).
        want = want_tris.get(cls, 0)
        rows[cls]["tris_delta"] = tris - want
        rows[cls]["tris_delta_pct"] = round(100.0 * (tris - want) / max(want, 1), 3)
        if want and abs(tris - want) / want > 0.01:
            bad.append(f"{cls}: {tris} triangles drawn by the glb, {want} placed in export_set.json "
                       f"({100.0 * (tris - want) / want:+.2f} %, tolerance 1 %)")
        if origin_inst > max(1, near_expected.get(cls, 0)):
            bad.append(f"{cls}: {origin_inst} un-instanced mesh nodes sit within 1 m of the world origin "
                       f"({near_expected.get(cls, 0)} expected)")
    print("[verify_glb] " + json.dumps(rows))
    (out / "verify_glb.json").write_text(json.dumps(dict(classes=rows, failures=bad), indent=1) + "\n")
    if bad:
        for b in bad:
            print("[verify_glb] FAIL " + b, file=sys.stderr)
        return 1
    print("[verify_glb] PASS: every placed triangle in export_set.json is drawn by the glb")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else ROOT / "export" / "out" / "gate1"))
