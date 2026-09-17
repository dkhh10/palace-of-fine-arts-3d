"""Phase 6c item D/E step 1: read the foliage materials' real parameters out of master_delivery.blend.

    scripts/blender_run.sh 600 -- --background master_delivery.blend --python export/read_foliage.py

Read-only: no render, no bake, no save. Writes export/out/gate3/foliage/params.json.

WHY. The glTF exporter can only write a `baseColorTexture`, so what env.glb ships for every leaf card is the
RAW 1 K PNG. The Phase 5 material is not that image: `scripts/mat_build.py leaf_material` builds

    base_colour = vscale( hsv( image.Color * TINT, hue, val ), cluster )

and the two per-instance terms (`hsv` from Object Info Random, `cluster` from an object-space noise) are
identity-centred variation, but **TINT is not**. Measured here, it is (1.86, 1.88, 1.80) on MAT_shrub,
(2.30, 2.36, 2.10) on MAT_shrub_light and **(6.30, 1.62, 0.98)** on MAT_shrub_dry - so the three shrub
materials, which share one texture, are a green, a paler green and a STRAW one in Blender and three
identical mid-green cards in the viewer, each about 1.9x too dark.

The same material also mixes in a Translucent BSDF whose colour is `base_colour * TRANSLUCENT` (a green-biased
multiplier, e.g. (0.85, 1.15, 0.60)) at a factor `maprange(trn_map, 0.05, 0.85, 0.35, 1.55) * translucency`.
Nothing of that reaches the glb either, and it is what makes a backlit leaf green in Cycles. Item C needs
both numbers; this file is where they come from.

Everything below is READ from the node graph with the structure asserted, never from mat_build.py's source:
a material whose graph does not match raises with a reason, the same rule as read_alpha.cut_chain.
"""
import json
import os
import sys
import time
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate0_common as g0  # noqa: E402
import read_alpha  # noqa: E402

SCHEMA = "pfa-phase6c/foliage-params/1"
OUT = g0.ROOT / "export" / "out" / "gate3" / "foliage"


def from_node(sock):
    return sock.links[0].from_node if sock.is_linked else None


def const_vec(sock):
    if sock.is_linked:
        return None
    v = sock.default_value
    return [round(float(x), 6) for x in v] if hasattr(v, "__len__") else round(float(v), 6)


def chain_to_image(sock, tint=None, depth=0):
    """Follow a colour link back to the first Image Texture, collecting every constant this multiplies by.
    Returns (image, tint[3], path[str]) or (None, None, why)."""
    tint = [1.0, 1.0, 1.0] if tint is None else tint
    path = []
    n = from_node(sock)
    while n is not None and depth < 12:
        depth += 1
        path.append(n.bl_idname)
        if n.bl_idname == "ShaderNodeTexImage":
            return n.image, tint, path
        if n.bl_idname == "ShaderNodeVectorMath" and n.operation in ("MULTIPLY", "SCALE"):
            # the constant operand multiplies the colour; the linked one is the colour
            colour_in = None
            for i, s in enumerate(n.inputs):
                if s.is_linked and colour_in is None:
                    colour_in = s
                elif not s.is_linked and s.type in ("VECTOR", "RGBA"):
                    c = const_vec(s)
                    if c and n.operation == "MULTIPLY" and any(abs(x) > 1e-9 for x in c[:3]):
                        tint = [tint[k] * c[k] for k in range(3)]
                elif not s.is_linked and s.type == "VALUE" and n.operation == "SCALE":
                    pass       # the per-instance cluster scale: identity-centred variation, pinned to 1
            if colour_in is None:
                return None, None, path + ["no linked colour input"]
            n = from_node(colour_in)
            continue
        if n.bl_idname == "ShaderNodeHueSaturation":
            n = from_node(n.inputs["Color"])       # hue/sat are the per-instance variation: pinned to identity
            continue
        # anything else: follow the first linked colour-ish input
        nxt = next((s for s in n.inputs if s.is_linked and s.type in ("RGBA", "VECTOR")), None)
        if nxt is None:
            return None, None, path + ["chain ends at " + n.bl_idname]
        n = from_node(nxt)
    return None, None, path + ["no image found"]


def image_info(img):
    if img is None:
        return None
    fp = bpy.path.abspath(img.filepath) if img.filepath else None
    return dict(name=img.name, size=list(img.size), colorspace=img.colorspace_settings.name,
                file=(os.path.basename(fp) if fp else None),
                path=(fp if fp and os.path.exists(fp) else None),
                packed=bool(img.packed_file))


def main():
    assert Path(bpy.data.filepath).name == "master_delivery.blend", \
        f"read_foliage.py must run on master_delivery.blend, not {bpy.data.filepath!r}"
    OUT.mkdir(parents=True, exist_ok=True)
    rep = dict(schema=SCHEMA, generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
               generator="export/read_foliage.py", source_blend=bpy.data.filepath, materials={})
    step = g0.Step("read_foliage")
    for mat in sorted(bpy.data.materials, key=lambda m: m.name):
        nt = mat.node_tree
        if nt is None:
            continue
        cut, why = read_alpha.cut_chain(mat)
        if cut is None:
            continue                    # not an alpha-cut card material
        bsdf = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
        if bsdf is None:
            continue
        img, tint, cpath = chain_to_image(bsdf.inputs["Base Color"])
        if img is None:
            continue                    # a cut-out that is not a leaf_material card (none at the moment)
        e = dict(alpha_cutoff=cut, alpha_cut_reason=why, base_colour_chain=cpath,
                 tint=[round(v, 6) for v in tint], albedo_image=image_info(img),
                 roughness=round(float(bsdf.inputs["Roughness"].default_value), 4),
                 specular=round(float(bsdf.inputs["Specular IOR Level"].default_value), 4),
                 sheen=round(float(bsdf.inputs["Sheen Weight"].default_value), 4),
                 backface_culling=bool(mat.use_backface_culling),
                 render_method=getattr(mat, "surface_render_method", None))
        # the normal map
        nm = from_node(bsdf.inputs["Normal"])
        if nm is not None and nm.bl_idname == "ShaderNodeNormalMap":
            nimg = from_node(nm.inputs["Color"])
            e["normal"] = dict(strength=round(float(nm.inputs["Strength"].default_value), 4),
                               image=image_info(nimg.image if nimg is not None
                                                and nimg.bl_idname == "ShaderNodeTexImage" else None))
        # the Translucent branch: colour = base_colour * TRANSLUCENT, mixed in at maprange(trn) * translucency
        tr = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfTranslucent"), None)
        if tr is not None:
            _, tcol, tpath = chain_to_image(tr.inputs["Color"])
            # tcol is base_colour's tint TIMES the translucent multiplier; divide the base tint back out
            tmul = [round(tcol[k] / tint[k], 6) if tcol and tint[k] else None for k in range(3)] \
                if tcol else None
            mix = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeMixShader"
                        and any(s.is_linked and s.links[0].from_node.name == tr.name
                                for s in list(n.inputs)[1:])), None)   # bpy hands back a new
                       # wrapper on every access, so `is` never matches: compare by name
            fac = dict(constant=None, map=None, map_range=None)
            assert mix is not None, (f"{mat.name}: the Translucent BSDF feeds no Mix Shader - "
                                     f"leaf_material's translucency branch is not there")
            if mix is not None:
                f = from_node(mix.inputs[0])
                if f is not None and f.bl_idname == "ShaderNodeMath" and f.operation == "MULTIPLY":
                    k = next((const_vec(s) for s in f.inputs if not s.is_linked), None)
                    fac["constant"] = k
                    mr = next((from_node(s) for s in f.inputs if s.is_linked), None)
                    if mr is not None and mr.bl_idname == "ShaderNodeMapRange":
                        # a Map Range node carries BOTH the float and the vector sockets under the
                        # same four names; only the float ones are the live inputs here.
                        fac["map_range"] = {s.name: const_vec(s) for s in mr.inputs
                                            if not s.is_linked and s.type == "VALUE"}
                        fac["map_range_node"] = dict(data_type=getattr(mr, "data_type", None),
                                                     interpolation=mr.interpolation_type,
                                                     clamp=bool(mr.clamp))
                        ti = from_node(mr.inputs["Value"])
                        if ti is not None and ti.bl_idname == "ShaderNodeTexImage":
                            fac["map"] = image_info(ti.image)
                elif f is not None:
                    fac["constant"] = None
                    fac["note"] = f"mix factor is a {f.bl_idname}, not the maprange*constant leaf_material builds"
                elif f is None:
                    fac["constant"] = const_vec(mix.inputs[0])
            e["translucency"] = dict(colour_multiplier=tmul, chain=tpath, factor=fac)
        rep["materials"][mat.name] = e
    step.done(materials=len(rep["materials"]))
    (OUT / "params.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(f"[read_foliage] {len(rep['materials'])} card materials -> {OUT / 'params.json'}")
    for k, v in rep["materials"].items():
        t = v["tint"]
        print(f"  {k:20s} tint {t[0]:.2f},{t[1]:.2f},{t[2]:.2f}  cut {v['alpha_cutoff']}  "
              f"tex {(v['albedo_image'] or {}).get('file')}  "
              f"translu {v.get('translucency', {}).get('colour_multiplier')} "
              f"x{(v.get('translucency', {}).get('factor') or {}).get('constant')}")


if __name__ == "__main__":
    main()
