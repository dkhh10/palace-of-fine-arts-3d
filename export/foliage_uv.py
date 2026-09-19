"""The foliage-card UV tiling, shared by the far-tree export and the ENV / shrub export.

Why a card's UVs are scaled at all (Phase 8e, docs/briefs/phase8e_analysis.md, and 8a-3,
docs/briefs/phase8a3_shrub_cards_analysis.md): a foliage card carries a whole painted cluster, and at
20-30 texels per screen pixel the mip merges its painted leaves and the alpha cut re-hardens the mush
into one blade the size of the card. Making the card sample the texture k times over divides that blade
by k. It needs REPEAT samplers, and it moves no vertex - so a vertex-AO npz, an instance row and a
lightmap UV1 are all untouched by it.

Two consumers, one contract:
  * export/trees_far.py  - the 16 far-tree LOD2 meshes, `UV_TILE_MODES` (ku/kv and the solved per-material
    alphaCutoff that pays for a widened u window);
  * export/gltf_gate1.py - env.gltf's LOD2 SHRUB cards, `SHRUB_TILE` (no cutoff solve: a shrub card's UV
    window is the whole texture, so tiling repeats what it already samples - measured 0.94-1.09x coverage
    at k = 2 for the three shrub materials, NOT neutral by construction; review r3 finding 8).

This module is bpy-free at import time (export/p8e_leaf_probe.py imports it on plain CPython to print the
mode that actually ships, review r3 finding 1); `tile_cards` imports bmesh when it is called.
"""

# ---------------------------------------------------------------- the far trees (export/trees_far.py)
# `iso_cut` is ku 2.0 / kv 3.0 - it is NOT isotropic, and the name is kept only because it is already in
# trees_far.json and docs/decisions.md (review r3 finding 2; the ku/kv are stated wherever it is quoted).
# ku > 1 widens the card's u window off the cluster texture's dense core and costs coverage, which the
# per-MATERIAL cutoff below buys back (solved so the mean coverage ratio over the species sharing a
# material is 1.00). kv is free: a card's v window is the full texture height, so k periods of it average
# what one period averages.
UV_TILE_MODES = {
    # the first 8e export: vertical only, coverage-neutral, thickness only (kept for the A/B)
    "kv25": dict(u={"broadleaf": 1.0, "cypress": 1.0, "cypress_column": 1.0, "eucalyptus": 1.0,
                    "pine": 1.0, "redwood": 1.0, "willow": 1.0},
                 v={"broadleaf": 2.5, "cypress": 2.5, "cypress_column": 2.5, "eucalyptus": 2.5,
                    "pine": 2.5, "redwood": 2.5, "willow": 1.5},
                 cutoff={}, v_offset=True, wrap=True),
    # what ships: run width p90 at 40 m 35.7 -> 18.4 px on the broadleaf at 0.93x coverage
    "iso_cut": dict(u=dict.fromkeys(("broadleaf", "cypress", "cypress_column", "eucalyptus",
                                     "pine", "redwood", "willow"), 2.0),
                    v=dict.fromkeys(("broadleaf", "cypress", "cypress_column", "eucalyptus",
                                     "pine", "redwood", "willow"), 3.0),
                    cutoff={"MAT_leaf_broadleaf": 0.27, "MAT_leaf_cypress": 0.21,
                            "MAT_leaf_eucalyptus": 0.10, "MAT_leaf_pine": 0.12},
                    v_offset=True, wrap=True),
    # r3 finding 4: a TRUE baseline - no scale, no per-card v offset, no REPEAT patch, no cutoff patch,
    # i.e. the pre-8e asset, so `PFA_UV_TILE_MODE=off` is the A/B control the README says it is.
    "off": dict(u={}, v={}, cutoff={}, v_offset=False, wrap=False),
}

# ---------------------------------------------------------------- the shrub cards (export/gltf_gate1.py)
# Per-material, from the MEASURED LOD2/LOD1 card ratio (review r3 finding 7), because the point of the
# scale is that the LOD2 card stops being a magnified LOD1 card at the 25 m `shrubLod` switch:
#   MAT_shrub        LOD2 0.33x0.43 m vs LOD1 0.16x0.21  -> 2.06x / 2.05x  -> ku 2, kv 2
#   MAT_shrub_light  0.34x0.46 vs 0.17x0.23              -> 2.00x / 2.00x  -> ku 2, kv 2
#   MAT_shrub_dry    0.08x0.39 vs 0.09x0.22              -> 0.89x / 1.77x  -> ku 1, kv 2  (it is already
#                    NARROWER than its LOD1 card; an isotropic 2 would halve its leaf width the wrong way)
#   MAT_reeds        0.06x0.23 vs 0.03x0.23              -> 2.00x / 1.00x  -> 1.0: the reeds are 1-5 px
#                    blades at coverage 0.17-0.23 and k > 1 erodes them (0.82x at 25 m, 0.00x at cam03 54 m)
SHRUB_TILE = {"MAT_shrub": (2.0, 2.0), "MAT_shrub_light": (2.0, 2.0),
              "MAT_shrub_dry": (1.0, 2.0), "MAT_reeds": (1.0, 1.0)}
# golden ratio on the card index, so neighbouring cards do not stack the same tile boundary at the same
# height; deterministic in `components()` order, so nothing has to be stored.
V_OFFSET = 0.6180339887498949
REPEAT, CLAMP = 10497, 33071


def components(bm):
    """Face-connected components, the same definition the thinning uses (<= 2 faces = one card)."""
    bm.faces.ensure_lookup_table()
    seen, comps = set(), []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack, comp = [f], []
        seen.add(f.index)
        while stack:
            cf = stack.pop()
            comp.append(cf)
            for e in cf.edges:
                for nf in e.link_faces:
                    if nf.index not in seen:
                        seen.add(nf.index)
                        stack.append(nf)
        comps.append(comp)
    return comps


def tile_cards(me, factors_by_material, v_offset=True, uv_layer=None):
    """Scale every CARD's UVs about its own UV centre by that card's material factor (ku, kv).

    A card is a connected component of <= 2 faces whose material is in `factors_by_material`; anything
    else (branch geometry, a trunk, a ground mesh sharing the object) is left alone, asserted rather than
    assumed. Geometry is never touched. Returns per-material stats including the UV range before/after.
    """
    import bmesh  # noqa: E402  (Blender-only; this module is imported on plain CPython too)
    slots = {i: factors_by_material[m.name]
             for i, m in enumerate(me.materials) if m and m.name in factors_by_material}
    active = {i: f for i, f in slots.items() if f != (1.0, 1.0)}
    if not active:
        return None
    bm = bmesh.new()
    bm.from_mesh(me)
    uvl = bm.loops.layers.uv.get(uv_layer) if uv_layer else (bm.loops.layers.uv.active
                                                             or bm.loops.layers.uv.verify())
    assert uvl is not None, f"{me.name}: no UV layer to tile"
    stats = {}
    for i, c in enumerate(components(bm)):
        if len(c) > 2:
            continue
        mats = {f.material_index for f in c}
        if len(mats) != 1:
            continue
        mi = mats.pop()
        if mi not in active:
            continue
        ku, kv = active[mi]
        name = me.materials[mi].name
        st = stats.setdefault(name, dict(ku=ku, kv=kv, cards=0,
                                         uv_before=[1e9, -1e9, 1e9, -1e9],
                                         uv_after=[1e9, -1e9, 1e9, -1e9]))
        loops = [lp for f in c for lp in f.loops]
        cu = sum(lp[uvl].uv.x for lp in loops) / len(loops)
        cv = sum(lp[uvl].uv.y for lp in loops) / len(loops)
        ov = (i * V_OFFSET) % 1.0 if v_offset else 0.0
        for lp in loops:
            uv = lp[uvl].uv
            b = st["uv_before"]
            b[0], b[1] = min(b[0], uv.x), max(b[1], uv.x)
            b[2], b[3] = min(b[2], uv.y), max(b[3], uv.y)
            uv.x = cu + (uv.x - cu) * ku
            uv.y = cv + (uv.y - cv) * kv + ov
            a = st["uv_after"]
            a[0], a[1] = min(a[0], uv.x), max(a[1], uv.x)
            a[2], a[3] = min(a[2], uv.y), max(a[3], uv.y)
        st["cards"] += 1
    bm.to_mesh(me)
    bm.free()
    me.update()
    for st in stats.values():
        st["uv_before"] = [round(v, 4) for v in st["uv_before"]]
        st["uv_after"] = [round(v, 4) for v in st["uv_after"]]
    return stats or None


def patch_samplers(doc, materials, gltf_name="the glTF"):
    """wrapS/wrapT = REPEAT on every texture of `materials`, in THIS glTF only.

    A sampler shared with any texture OUTSIDE `materials` is cloned, never patched (review r3 finding 9:
    in env.gltf the leaf cards share the shrub cards' sampler, and a shrub fix must not silently re-wrap
    them). Asserts that no other texture's sampler moved. Returns the record for the report.
    """
    want = set(materials)
    tex_ids = set()
    for m in doc.get("materials", []):
        if (m.get("name") or "") not in want:
            continue
        pbr = m.get("pbrMetallicRoughness") or {}
        for t in (pbr.get("baseColorTexture"), pbr.get("metallicRoughnessTexture"),
                  m.get("normalTexture"), m.get("occlusionTexture"), m.get("emissiveTexture")):
            if t is not None and t.get("index") is not None:
                tex_ids.add(int(t["index"]))
    if not tex_ids:
        return None
    samplers = doc.setdefault("samplers", [])
    texs = doc.get("textures", [])
    shared = {tx.get("sampler") for i, tx in enumerate(texs) if i not in tex_ids}
    before = {i: (tx.get("sampler"),
                  dict(samplers[tx["sampler"]]) if tx.get("sampler") is not None else None)
              for i, tx in enumerate(texs) if i not in tex_ids}
    clones, patched, cloned = {}, [], []
    for ti in sorted(tex_ids):
        tx = texs[ti]
        si = tx.get("sampler")
        if si is not None and si not in shared:
            samplers[si].update(wrapS=REPEAT, wrapT=REPEAT)
            patched.append(si)
        else:
            if si not in clones:
                base = dict(samplers[si]) if si is not None else {}
                base.update(wrapS=REPEAT, wrapT=REPEAT)
                samplers.append(base)
                clones[si] = len(samplers) - 1
            tx["sampler"] = clones[si]
            cloned.append([si, clones[si]])
    for ti in sorted(tex_ids):
        s = samplers[texs[ti]["sampler"]]
        assert s.get("wrapS") == REPEAT and s.get("wrapT") == REPEAT, \
            f"{gltf_name}: texture {ti} did not take the REPEAT sampler ({s})"
    for i, (si, was) in before.items():
        now = dict(samplers[texs[i]["sampler"]]) if texs[i].get("sampler") is not None else None
        assert texs[i].get("sampler") == si and now == was, \
            f"{gltf_name}: texture {i} outside {sorted(want)} changed sampler ({si} {was} -> " \
            f"{texs[i].get('sampler')} {now})"
    return dict(materials=sorted(want), textures=sorted(tex_ids), samplers_patched=sorted(set(patched)),
                samplers_cloned=cloned, samplers_total=len(samplers), wrap=REPEAT, was=CLAMP)


def leaf_uv_range(doc, gltf_p, prefix="MAT_leaf"):
    """min/max of TEXCOORD_0 over every primitive whose material starts with `prefix`, decoded from the
    WRITTEN glTF and its .bin (UV accessors carry no min/max). Loud on anything it cannot decode."""
    import numpy as np
    mats = {i for i, m in enumerate(doc.get("materials", []))
            if (m.get("name") or "").startswith(prefix)}
    bufs = []
    for b in doc.get("buffers", []):
        assert b.get("uri"), f"{gltf_p}: a GLB-embedded buffer cannot be decoded here"
        bufs.append((gltf_p.parent / b["uri"]).read_bytes())
    lo, hi, n = None, None, 0
    for me in doc.get("meshes", []):
        for pr in me.get("primitives", []):
            if pr.get("material") not in mats or "TEXCOORD_0" not in pr.get("attributes", {}):
                continue
            a = doc["accessors"][pr["attributes"]["TEXCOORD_0"]]
            assert a["componentType"] == 5126 and a["type"] == "VEC2" and "sparse" not in a, a
            bv = doc["bufferViews"][a["bufferView"]]
            stride = bv.get("byteStride") or 8
            off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
            raw = bufs[bv["buffer"]]
            # r3 finding 5: per element, so a byteStride > 8 cannot over-read the tail
            uv = np.stack([np.frombuffer(raw, "<f4", count=2, offset=off + k * stride)
                           for k in range(a["count"])])
            lo = float(uv.min()) if lo is None else min(lo, float(uv.min()))
            hi = float(uv.max()) if hi is None else max(hi, float(uv.max()))
            n += a["count"]
    if not n:
        return None
    return dict(min=round(lo, 4), max=round(hi, 4), verts=n)
