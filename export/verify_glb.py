#!/usr/bin/env python3
"""Gate 1 step 5d: prove the packed glbs still carry every placement, after gltfpack has folded the nodes.

    python3 export/verify_glb.py [export/out/gate1]

Per class it also asserts that every material name the export set uses survives into the glb, for any
class packed with -km (gltfpack merges materials with identical factors otherwise, and the ten identical
backdrop greys collapsed to one, orphaning nine Gate 2 texture sets). The other invariant is TRIANGLES DRAWN,
not node count: gltfpack legitimately merges single-use nodes that
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


def mesh_centre(doc, mesh_idx):
    """Centre of a mesh's own bounding box, from the POSITION accessors' min/max (no codec needed)."""
    lo = [1e30] * 3
    hi = [-1e30] * 3
    seen = False
    for pr in doc["meshes"][mesh_idx].get("primitives", []):
        ai = (pr.get("attributes") or {}).get("POSITION")
        if ai is None:
            continue
        acc = doc["accessors"][ai]
        if "min" not in acc or "max" not in acc:
            continue
        seen = True
        for i in range(3):
            lo[i] = min(lo[i], acc["min"][i])
            hi[i] = max(hi[i], acc["max"][i])
    return [(lo[i] + hi[i]) / 2.0 for i in range(3)] if seen else None


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

    gl = json.loads((out / "gltf_gate1.json").read_text()) if (out / "gltf_gate1.json").exists() else {}
    flags = {}
    fp = out / "gltfpack_flags.txt"
    if fp.exists():
        for line in fp.read_text().split("\n"):
            if line.strip():
                parts = line.split()
                flags[parts[0]] = " ".join(parts[1:])

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
                # A missing node translation does NOT mean the geometry is at the origin: with -vpf gltfpack
                # writes float positions and drops the translation entirely, and the merged backdrop / ground
                # groups carry their world position inside the vertices. Use the POSITION accessor's own
                # min/max (gltfpack always writes them) plus whatever transform the node has.
                t = nd.get("translation") or [0.0, 0.0, 0.0]
                if nd.get("matrix"):
                    t = nd["matrix"][12:15]
                ctr = mesh_centre(doc, nd["mesh"])
                if ctr is not None:
                    w = [t[i] + ctr[i] for i in range(3)]
                    if sum(v * v for v in w) ** 0.5 < 1.0:
                        origin_inst += 1
        # gltfpack merges materials whose factors match unless -km is given, and a merged-away name is a
        # Gate 2 texture set that matches nothing. Assert the names for any class packed with -km; for the
        # others report the loss without failing (they are frozen byte-identical this round).
        want_mats = set((gl.get("classes", {}).get(cls) or {}).get("materials_expected") or [])
        have_mats = {m.get("name") for m in doc.get("materials", []) if m.get("name")}
        missing = sorted(want_mats - have_mats)
        strict = "-km" in (flags.get(cls) or "")
        rows[cls] = dict(gltfpack_flags=flags.get(cls), materials_expected=len(want_mats),
                         materials_in_glb=len(doc.get("materials", [])),
                         materials_named_in_glb=len(have_mats), materials_missing=len(missing),
                         materials_missing_names=missing[:12], material_names_enforced=strict,
                         tris_drawn=tris, tris_expected=want_tris.get(cls, 0),
                         placements_in_glb=plain + inst, objects_in_set=len(per_cls.get(cls, [])),
                         plain_nodes=plain, instanced_nodes=inst_nodes, instanced_placements=inst,
                         plain_nodes_with_geometry_at_origin=origin_inst, expected_at_origin=near_expected.get(cls, 0))
        # gltfpack drops degenerate triangles while it optimises, so the match is within a tolerance, not
        # exact: measured 0.19 % on arch and 0.16 % on orn, 0.00 % on env and ground. A DROPPED PLACEMENT is
        # orders of magnitude bigger than that (one stacked shrub group is 8.8 % of ENV).
        if missing and strict:
            bad.append(f"{cls}: {len(missing)} material names in the export set are absent from the packed "
                       f"glb although it was packed with -km: {missing[:8]}")
        elif missing:
            print(f"[verify_glb] note {cls}: {len(missing)} material names merged away by gltfpack "
                  f"(no -km on this class): {missing[:6]}")
        want = want_tris.get(cls, 0)
        rows[cls]["tris_delta"] = tris - want
        rows[cls]["tris_delta_pct"] = round(100.0 * (tris - want) / max(want, 1), 3)
        if want and abs(tris - want) / want > 0.01:
            bad.append(f"{cls}: {tris} triangles drawn by the glb, {want} placed in export_set.json "
                       f"({100.0 * (tris - want) / want:+.2f} %, tolerance 1 %)")
        if origin_inst > max(1, near_expected.get(cls, 0)):
            bad.append(f"{cls}: {origin_inst} un-instanced mesh nodes have their GEOMETRY within 1 m of "
                       f"the world origin ({near_expected.get(cls, 0)} expected)")
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
