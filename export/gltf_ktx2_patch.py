#!/usr/bin/env python3
"""Point a glTF's colour/roughness/normal textures at the .ktx2 files toktx just produced.

    python3 export/gltf_ktx2_patch.py <in.gltf> <out.gltf> <ktx2_dir_relative_to_out>

The RGBM8 lightmap is deliberately LEFT as PNG: UASTC is a 4x4 block codec and the M channel is a per-texel
exponent, so block compression of an RGBM map produces visible energy blocks. Everything else becomes
KHR_texture_basisu. Prints one JSON line with what it changed.
"""
import json
import os
import sys

src, dst, ktxdir = sys.argv[1], sys.argv[2], sys.argv[3]
doc = json.load(open(src))
base = os.path.dirname(os.path.abspath(dst))
changed, skipped = [], []

images = doc.setdefault("images", [])
for t in doc.get("textures", []):
    si = t.get("source")
    if si is None:
        continue
    uri = images[si].get("uri", "")
    name = os.path.basename(uri)
    if not name.lower().endswith(".png") or "lightmap" in name.lower():
        skipped.append(name)
        continue
    ktx = os.path.join(ktxdir, os.path.splitext(name)[0] + ".ktx2")
    if not os.path.exists(os.path.join(base, ktx)):
        skipped.append(name + " (no ktx2)")
        continue
    images.append({"uri": ktx, "mimeType": "image/ktx2"})
    t.setdefault("extensions", {})["KHR_texture_basisu"] = {"source": len(images) - 1}
    t.pop("source", None)
    changed.append(f"{name} -> {ktx}")

# Drop the PNG image entries the textures no longer point at: gltfpack embeds every entry in images[], so
# leaving them behind shipped a 153 MB glb that carried both the PNGs and the KTX2 files.
used = set()
for t in doc.get("textures", []):
    if "source" in t:
        used.add(t["source"])
    bu = t.get("extensions", {}).get("KHR_texture_basisu")
    if bu and "source" in bu:
        used.add(bu["source"])
remap, kept = {}, []
for i, im in enumerate(images):
    if i in used:
        remap[i] = len(kept)
        kept.append(im)
dropped = len(images) - len(kept)
doc["images"] = kept
for t in doc.get("textures", []):
    if "source" in t:
        t["source"] = remap[t["source"]]
    bu = t.get("extensions", {}).get("KHR_texture_basisu")
    if bu and "source" in bu:
        bu["source"] = remap[bu["source"]]

if changed:
    used_ext = doc.setdefault("extensionsUsed", [])
    if "KHR_texture_basisu" not in used_ext:
        used_ext.append("KHR_texture_basisu")
    req = doc.setdefault("extensionsRequired", [])
    if "KHR_texture_basisu" not in req:
        req.append("KHR_texture_basisu")
json.dump(doc, open(dst, "w"))
print(json.dumps({"ktx2": changed, "left_as_png": skipped, "images_kept": len(kept),
                  "orphan_png_entries_dropped": dropped}))
