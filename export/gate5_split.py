#!/usr/bin/env python3
"""6b Gate 5 item B (helper): cut a Gate 1 class glTF into a node subset, ready for gltfpack.

    python3 export/gate5_split.py <class> <out.gltf> --nodes <names.json> [--drop-gate1-normals]
                                  [--images <dir>] [--image-suffix _q4]

No Blender, no GPU, no re-export: the geometry is the SAME `<class>.bin` the Gate 3 glbs were packed
from, so a group is byte-for-byte the same triangles as gate3 - only the node set differs.  `verify_glb.py
--gate5` asserts exactly that.

What the subset carries:
  * `scenes[0].nodes` and `nodes` reduced to the named subset (indices remapped);
  * meshes, materials, textures, images and samplers pruned to what the surviving nodes reach, indices
    remapped.  This is done HERE and not left to gltfpack: measured, gltfpack embeds every entry of
    `images` whether a node reaches it or not (a 124-node ORN subset of the 436 came out at 153 983 832 B
    against the full orn.glb's 154 253 424), and the embedded textures are what the 25 MiB per-file cap
    is really about.  Accessors and buffer views are left alone - gltfpack rebuilds its own buffer from
    the primitives it keeps, so an unreferenced accessor costs nothing in the output.
  * `buffers[0].uri` and every `images[*].uri` rewritten relative to the OUTPUT file, so the subset can
    live in out/gate5 while its data stays in out/gate1.

`--drop-gate1-normals` removes `normalTexture` from exactly those materials whose Gate 2 set declares
`normal.replaces_gate1` (the manifest's own word: the viewer overwrites `normalMap` from the Gate 2 set
in web/src/pbr.js, so the Gate 1 map inside the glb is downloaded, decoded and then thrown away).  The
materials it touches are listed in the report; a material with no such declaration is never touched.
`occlusionTexture` is NEVER dropped - pbr.js keeps the glb's aoMap (`kept_glb_ao`) and no Gate 2 set
replaces it.
"""
import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = Path(os.environ.get("PFA_MAIN_ROOT", "/Users/dk/Projects/3d render blender 3rd attempt building"))
GATE1 = MAIN / "export/out/gate1"


def replaced_gate1_normals(manifest):
    """{material name: the Gate 1 normal texture key the Gate 2 set replaces} from the manifest itself."""
    out = {}
    for name, s in (manifest.get("materials") or {}).get("sets", {}).items():
        n = s.get("normal")
        if isinstance(n, dict) and n.get("texture") and n.get("replaces_gate1"):
            out[name] = n["replaces_gate1"]
    return out


def split(cls, out_path, node_names, manifest=None, drop_gate1_normals=False,
          image_dir=None, image_suffix="", gate1=GATE1):
    src = Path(gate1) / f"{cls}_ktx2.gltf"
    doc = json.loads(src.read_text())
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    want = set(node_names)
    keep = [i for i, n in enumerate(doc["nodes"]) if n.get("name") in want]
    kept_names = {doc["nodes"][i]["name"] for i in keep}
    missing = sorted(want - kept_names)
    assert not any(doc["nodes"][i].get("children") for i in keep), \
        f"{cls}: a kept node has children; the Gate 1 glTFs are flat and this splitter assumes it"
    doc["nodes"] = [doc["nodes"][i] for i in keep]
    doc["scenes"] = [dict(doc["scenes"][doc.get("scene", 0)], nodes=list(range(len(keep))))]
    doc["scene"] = 0

    # ---- prune to what the kept nodes reach, remapping every index we touch.
    used_mesh = {n["mesh"] for n in doc["nodes"] if "mesh" in n}
    meshes = [doc["meshes"][i] for i in sorted(used_mesh)]
    mesh_map = {o: n for n, o in enumerate(sorted(used_mesh))}
    for n in doc["nodes"]:
        if "mesh" in n:
            n["mesh"] = mesh_map[n["mesh"]]
    doc["meshes"] = meshes

    used_mat = {pr["material"] for me in meshes for pr in me.get("primitives", []) if "material" in pr}
    mats = [doc["materials"][i] for i in sorted(used_mat)]
    mat_map = {o: n for n, o in enumerate(sorted(used_mat))}
    for me in meshes:
        for pr in me.get("primitives", []):
            if "material" in pr:
                pr["material"] = mat_map[pr["material"]]
    doc["materials"] = mats

    dropped = []
    if drop_gate1_normals:
        repl = replaced_gate1_normals(manifest or {})
        for mat in mats:
            if mat.get("name") in repl and "normalTexture" in mat:
                mat.pop("normalTexture")
                dropped.append(mat["name"])

    def tex_refs(mat):
        for k in ("normalTexture", "occlusionTexture", "emissiveTexture"):
            if isinstance(mat.get(k), dict) and "index" in mat[k]:
                yield mat[k]
        pbr = mat.get("pbrMetallicRoughness") or {}
        for k in ("baseColorTexture", "metallicRoughnessTexture"):
            if isinstance(pbr.get(k), dict) and "index" in pbr[k]:
                yield pbr[k]

    used_tex = {r["index"] for mat in mats for r in tex_refs(mat)}
    texs = [doc["textures"][i] for i in sorted(used_tex)]
    tex_map = {o: n for n, o in enumerate(sorted(used_tex))}
    for mat in mats:
        for r in tex_refs(mat):
            r["index"] = tex_map[r["index"]]
    doc["textures"] = texs

    def img_of(t):
        e = (t.get("extensions") or {}).get("KHR_texture_basisu") or {}
        return e.get("source", t.get("source"))

    used_img = {img_of(t) for t in texs if img_of(t) is not None}
    imgs = [doc["images"][i] for i in sorted(used_img)]
    img_map = {o: n for n, o in enumerate(sorted(used_img))}
    for t in texs:
        e = (t.get("extensions") or {}).get("KHR_texture_basisu")
        if e and "source" in e:
            e["source"] = img_map[e["source"]]
        if "source" in t:
            t["source"] = img_map[t["source"]]
    doc["images"] = imgs

    if doc.get("samplers"):
        used_s = {t["sampler"] for t in texs if "sampler" in t}
        smp = [doc["samplers"][i] for i in sorted(used_s)]
        s_map = {o: n for n, o in enumerate(sorted(used_s))}
        for t in texs:
            if "sampler" in t:
                t["sampler"] = s_map[t["sampler"]]
        doc["samplers"] = smp

    rel = os.path.relpath(Path(gate1).resolve(), out_path.parent.resolve())
    for b in doc.get("buffers", []):
        if b.get("uri"):
            b["uri"] = os.path.join(rel, os.path.basename(b["uri"]))
    for im in doc.get("images", []):
        u = im.get("uri")
        if not u:
            continue
        stem, ext = os.path.splitext(os.path.basename(u))
        if image_dir:
            cand = Path(image_dir) / f"{stem}{image_suffix}{ext}"
            if cand.exists():
                im["uri"] = os.path.relpath(cand.resolve(), out_path.parent.resolve())
                continue
        im["uri"] = os.path.join(rel, os.path.dirname(u), os.path.basename(u))
    out_path.write_text(json.dumps(doc))
    return dict(gltf=str(out_path), nodes=len(keep), requested=len(want), missing=missing,
                meshes=len(meshes), materials=len(mats), textures=len(texs), images=len(imgs),
                image_uris=[im.get("uri") for im in imgs],
                dropped_gate1_normals=sorted(set(dropped)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cls")
    ap.add_argument("out")
    ap.add_argument("--nodes", required=True, help="json file: a list of node names")
    ap.add_argument("--manifest", default=str(MAIN / "export/out/gate3/manifest.json"))
    ap.add_argument("--drop-gate1-normals", action="store_true")
    ap.add_argument("--images", default=None)
    ap.add_argument("--image-suffix", default="")
    a = ap.parse_args()
    man = json.loads(Path(a.manifest).read_text())
    rep = split(a.cls, a.out, json.loads(Path(a.nodes).read_text()), manifest=man,
                drop_gate1_normals=a.drop_gate1_normals, image_dir=a.images, image_suffix=a.image_suffix)
    print(json.dumps(rep))


if __name__ == "__main__":
    main()
