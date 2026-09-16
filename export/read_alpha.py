"""Gate 3 hand-off 4: read the card materials' ALPHA settings out of master_delivery.blend.

    scripts/blender_run.sh 900 -- --background <master_delivery.blend> --python export/read_alpha.py

Read-only: no render, no save. glTF defaults a material with no `alphaMode` to OPAQUE, so every leaf card in
env.glb drew as a solid rectangle (viewer, cam02). The fix belongs on the export side, and the cutoff has to
come from the source material - never from a guess.

WHERE THE CUT ACTUALLY IS (r4 review). `material.alpha_threshold` is Blender's factory 0.5 on every material
in this file and is INERT under `blend_method HASHED` / `surface_render_method DITHERED` - reading it gave the
right answer for six materials by coincidence and the wrong one for two. The real cut is built by
`scripts/mat_build.py leaf_material` (~1385-1417): the material output's Surface is a **Mix Shader** between a
**Transparent BSDF** and the shaded branch, and its factor is a **Map Range** over the base-colour image's
`Alpha` output, `From Min = alpha_cut - 0.15`, `From Max = alpha_cut + 0.15`. So the 50 % crossing - the one
number a glTF `alphaCutoff` can express - is the MIDPOINT of From Min and From Max, i.e. `alpha_cut` itself:
0.45 for MAT_leaf_cypress and 0.42 for MAT_leaf_pine (mat_build.py ~1738-1741), 0.5 for the other six.
`cut_chain()` walks exactly that graph and returns None with a REASON on anything else - it never defaults.

Writes export/out/gate3/alpha_cutoffs.json; export/gltf_gate1.py imports `cut_chain` from here and re-derives
the value from its own copy of each material, so the shipped cutoff is checked against the graph twice.
"""
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate3_common as g3  # noqa: E402

MATH_1IN = {"ROUND", "FLOOR", "CEIL", "TRUNC", "FRACT", "ABSOLUTE", "SQRT", "SIGN"}


def cut_chain(mat):
    """(cutoff, description) for a material whose alpha is cut by mat_build.py's Transparent/Mix/Map Range
    trio, else (None, why). Never guesses and never falls back to `material.alpha_threshold`."""
    nt = getattr(mat, "node_tree", None)
    if nt is None:
        return None, "material has no node tree"
    outs = [n for n in nt.nodes if n.bl_idname == "ShaderNodeOutputMaterial"]
    out = next((n for n in outs if n.is_active_output), outs[0] if outs else None)
    if out is None or not out.inputs["Surface"].is_linked:
        return None, "no active material output, or its Surface is unlinked"
    mix = out.inputs["Surface"].links[0].from_node
    if mix.bl_idname != "ShaderNodeMixShader":
        return None, f"Surface is fed by {mix.bl_idname}, not the Mix Shader that does the cut"
    branches = {i: (mix.inputs[i].links[0].from_node.bl_idname if mix.inputs[i].is_linked else None)
                for i in (1, 2)}
    if "ShaderNodeBsdfTransparent" not in branches.values():
        return None, f"the Surface Mix Shader has no Transparent BSDF branch (got {branches})"
    fac = mix.inputs[0]
    if not fac.is_linked:
        return None, f"the cut Mix Shader's factor is the constant {float(fac.default_value)}"
    mr = fac.links[0].from_node
    if mr.bl_idname != "ShaderNodeMapRange":
        return None, f"the cut factor comes from {mr.bl_idname}, not a Map Range"
    try:
        fmin = float(mr.inputs["From Min"].default_value)
        fmax = float(mr.inputs["From Max"].default_value)
        tmin = float(mr.inputs["To Min"].default_value)
        tmax = float(mr.inputs["To Max"].default_value)
    except (KeyError, TypeError) as e:
        return None, f"Map Range sockets are not the scalar ones: {e}"
    val = mr.inputs["Value"]
    if not val.is_linked:
        return None, "the Map Range's Value is not linked to an image alpha"
    src, sock = val.links[0].from_node, val.links[0].from_socket.name
    if src.bl_idname != "ShaderNodeTexImage" or sock != "Alpha":
        return None, f"the Map Range reads {src.bl_idname}.{sock}, not an Image Texture Alpha"
    if fmax <= fmin:
        return None, f"Map Range From Min {fmin} >= From Max {fmax}"
    # To Min/To Max reversed would flip the sense of the cut, and the midpoint would be the wrong side.
    if not (tmin < tmax):
        return None, f"Map Range To Min {tmin} / To Max {tmax} is inverted"
    mid = round((fmin + fmax) / 2.0, 6)
    return mid, (f"midpoint of Map Range From Min {round(fmin, 6)} / From Max {round(fmax, 6)} "
                 f"(To {tmin}..{tmax}) over {src.image.name if src.image else '?'}.Alpha, feeding the "
                 f"Transparent/Mix Shader cut - mat_build.py leaf_material")


def chain(sock, depth=0):
    """Walk backwards from a linked input socket, reporting each node and the number that shapes alpha."""
    if not sock.is_linked or depth > 6:
        return []
    ln = sock.links[0]
    nd = ln.from_node
    row = dict(node=nd.name, type=nd.bl_idname, out=ln.from_socket.name)
    if nd.bl_idname == "ShaderNodeMath":
        row["operation"] = nd.operation
        row["threshold"] = (None if nd.operation in MATH_1IN
                            else round(float(nd.inputs[1].default_value), 6))
        row["use_clamp"] = bool(nd.use_clamp)
    if nd.bl_idname == "ShaderNodeValToRGB":
        row["ramp"] = [[round(e.position, 6), [round(v, 6) for v in e.color]] for e in nd.color_ramp.elements]
    if nd.bl_idname == "ShaderNodeTexImage":
        im = nd.image
        row["image"] = (im.name if im else None)
        row["image_file"] = (im.filepath if im else None)
        row["channels"] = (im.channels if im else None)
        row["depth"] = (im.depth if im else None)
        row["has_alpha"] = bool(im and im.depth in (32, 64)) if im else None
        row["alpha_mode"] = (im.alpha_mode if im else None)
    rows = [row]
    for inp in nd.inputs:
        rows += chain(inp, depth + 1)
    return rows


def rgba_images(nt, seen=None):
    """Every RGBA image reachable from a material's tree, INCLUDING inside node groups. The leaf cards feed
    their Principled through a group, and their Image Texture nodes have no links in the material's own tree,
    so a "follow the Base Color link" test finds nothing - `depth` 32/64 is the only honest alpha test."""
    seen = seen if seen is not None else set()
    if nt is None or nt.as_pointer() in seen:
        return []
    seen.add(nt.as_pointer())
    out = []
    for n in nt.nodes:
        if n.bl_idname == "ShaderNodeTexImage" and n.image is not None:
            out.append(dict(node=n.name, image=n.image.name, depth=n.image.depth,
                            channels=n.image.channels, file=Path(n.image.filepath).name or None,
                            size=list(n.image.size), alpha_mode=n.image.alpha_mode,
                            has_alpha=n.image.depth in (32, 64)))
        if n.bl_idname == "ShaderNodeGroup":
            out += rgba_images(n.node_tree, seen)
    return out


# Only the discovery run does this; export/gltf_gate1.py imports `cut_chain` from this module and
# must not trip the master_delivery.blend assertion while it is open on gate1_set.blend.
if __name__ == "__main__":
    assert Path(bpy.data.filepath).name == "master_delivery.blend", (
        f"read_alpha.py must run on master_delivery.blend, not {bpy.data.filepath!r}: the cut lives in the "
        f"material graph and only the delivery blend is the source of truth")

    out = {}
    for mat in bpy.data.materials:
        nt = getattr(mat, "node_tree", None)
        if nt is None:
            continue
        bsdf = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
        imgs = rgba_images(nt)
        alpha_imgs = [i for i in imgs if i["has_alpha"]]
        a_in = bsdf.inputs.get("Alpha") if bsdf else None
        alpha_linked = bool(a_in and a_in.is_linked)
        if not (alpha_imgs or alpha_linked):
            continue
        props = {}
        for k in ("blend_method", "shadow_method", "alpha_threshold", "surface_render_method",
                  "use_backface_culling", "use_transparent_shadow"):
            if hasattr(mat, k):
                v = getattr(mat, k)
                props[k] = (round(float(v), 6) if isinstance(v, float) else v)
        # THE CUTOFF comes from the Transparent/Mix/Map Range graph, never from material.alpha_threshold
        # (factory 0.5 here, and inert under HASHED/DITHERED).
        cut, cut_why = cut_chain(mat)
        out[mat.name] = dict(
            users=mat.users, alpha_images=[i["image"] for i in alpha_imgs],
            alpha_image_files=[i["file"] for i in alpha_imgs], images=imgs,
            alpha_input_linked=alpha_linked,
            alpha_default=(round(float(a_in.default_value), 6) if a_in and not alpha_linked else None),
            alpha_chain=(chain(a_in) if alpha_linked else []),
            material_props=props,
            cutoff=cut, cutoff_source=cut_why,
            alpha_threshold_inert=props.get("alpha_threshold"))

    # A material whose RGBA base colour is a real FILE is a card the export can ship; those must resolve, or the
    # export would have nothing to write. (The MAT_ornament_* materials reach generated, file-less RGBA images and
    # have no cut chain at all - they are reported with cutoff null and never shipped a mode.)
    unresolved = sorted(k for k, v in out.items()
                        if v["cutoff"] is None and any(f for f in v["alpha_image_files"]))
    assert not unresolved, ("these file-backed alpha card materials have no recognised cut chain, so no cutoff "
                            "could be READ: " + json.dumps({k: out[k]["cutoff_source"] for k in unresolved}))

    report = dict(schema="pfa-phase6/gate3-alpha/1", written_by="export/read_alpha.py",
                  source=bpy.data.filepath, materials=out, count=len(out),
                  note=("A glTF material with no `alphaMode` is OPAQUE, so a leaf card drew as a solid rectangle. "
                        "`cutoff` is the 50 % crossing of the Transparent/Mix Shader cut this material actually "
                        "uses - the midpoint of the Map Range that shapes the image alpha (mat_build.py "
                        "leaf_material). `alpha_threshold_inert` is Blender's factory 0.5, reported only to show "
                        "it is NOT the cut: it is inert under blend_method HASHED / surface_render_method "
                        "DITHERED and it disagrees with the real value on MAT_leaf_cypress and MAT_leaf_pine."))
    p = g3.OUT / "alpha_cutoffs.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, indent=1) + "\n")
    for k, v in sorted(out.items()):
        print(f"[read_alpha] {k}: cutoff={v['cutoff']} (inert alpha_threshold={v['alpha_threshold_inert']}) "
              f"alpha_images={v['alpha_image_files']} blend={v['material_props'].get('blend_method')}/"
              f"{v['material_props'].get('surface_render_method')} users={v['users']}")
    print(f"[read_alpha] wrote {p} ({len(out)} materials)")
