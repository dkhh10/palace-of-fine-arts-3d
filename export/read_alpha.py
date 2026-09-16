"""Gate 3 hand-off 4: read the card materials' ALPHA settings out of master_delivery.blend.

    scripts/blender_run.sh 900 -- --background <master_delivery.blend> --python export/read_alpha.py

Read-only: no render, no save. glTF defaults a material with no `alphaMode` to OPAQUE, so every leaf card in
env.glb drew as a solid rectangle (viewer, cam02). The fix belongs on the export side, and the cutoff has to
come from the source material - never from a guess - so this dumps, per material whose base-colour image
carries an alpha channel: the Principled `Alpha` input, the whole node chain feeding it (any Math threshold,
colour ramp or Alpha output), and every alpha-related material property Blender 5.2 still exposes.
Writes export/out/gate3/alpha_cutoffs.json; export/gltf_gate1.py reads it and asserts its own copy of each
material agrees before it writes alphaMode/alphaCutoff into the glTF.
"""
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate3_common as g3  # noqa: E402

MATH_1IN = {"ROUND", "FLOOR", "CEIL", "TRUNC", "FRACT", "ABSOLUTE", "SQRT", "SIGN"}


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
    # THE CUTOFF. Blender's own words for `alpha_threshold`: "a pixel is rendered only if its alpha value is
    # above this threshold". A Math GREATER_THAN/LESS_THAN in the Alpha chain would override it, so it is
    # reported first; nothing here has one (these materials clip through blend_method HASHED / DITHERED).
    thr = next((c.get("threshold") for c in (chain(a_in) if alpha_linked else [])
                if c.get("operation") in ("GREATER_THAN", "LESS_THAN") and c.get("threshold") is not None),
               None)
    out[mat.name] = dict(
        users=mat.users, alpha_images=[i["image"] for i in alpha_imgs],
        alpha_image_files=[i["file"] for i in alpha_imgs], images=imgs,
        alpha_input_linked=alpha_linked,
        alpha_default=(round(float(a_in.default_value), 6) if a_in and not alpha_linked else None),
        alpha_chain=(chain(a_in) if alpha_linked else []),
        material_props=props,
        cutoff=(thr if thr is not None else props.get("alpha_threshold")),
        cutoff_source=("Math " + str(thr) + " in the Alpha chain" if thr is not None
                       else "material.alpha_threshold"))

report = dict(schema="pfa-phase6/gate3-alpha/1", written_by="export/read_alpha.py",
              source=bpy.data.filepath, materials=out, count=len(out),
              note=("A glTF material with no `alphaMode` is OPAQUE, so a leaf card drew as a solid rectangle. "
                    "`alpha_chain` is the node path feeding Principled Alpha in the SOURCE file: a Math "
                    "GREATER_THAN/LESS_THAN `threshold` is the clip value to use; a bare Alpha output means "
                    "the source blended rather than clipped, and then `material_props.alpha_threshold` is "
                    "Blender's own clip value for the same material."))
p = g3.OUT / "alpha_cutoffs.json"
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(report, indent=1) + "\n")
for k, v in sorted(out.items()):
    print(f"[read_alpha] {k}: cutoff={v['cutoff']} ({v['cutoff_source']}) "
          f"alpha_images={v['alpha_image_files']} blend={v['material_props'].get('blend_method')}/"
          f"{v['material_props'].get('surface_render_method')} users={v['users']}")
print(f"[read_alpha] wrote {p} ({len(out)} materials)")
