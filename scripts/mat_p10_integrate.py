"""Phase 10 r1, step 8 -- wire the projected atlas into the concrete node group of assets/materials.blend (post-step).

    scripts/blender_run.sh 600 -- --background assets/materials.blend --python scripts/mat_p10_integrate.py -- \
        [--weight 0.6] [--save]

Inside `PFA_concrete` (every MAT_concrete_* and the column materials run through it), just before the group's Color
output, after round 9's `Albedo Tint` (M_chroma) and ref-169 ratio:
    c = mix(w, c, c * ratio_p10)      w = conf_p10 x WEIGHT x (1 - round9_weight x Photo)
`ratio_p10` / `conf_p10` come from PFA_p10_ratio.png / PFA_p10_mask.png (scripts/mat_p10_texture.py) through the
`UVBake` layer (scripts/arch_uvbake.py).  A mesh without `UVBake` reads UV (0, 0), where the mask is 0 by
construction, so every other object keeps the procedural exactly.  Where round 9's projector already acts (the hero
band from the hero station) the new map yields, so round 9's measured hero numbers are not applied twice.
Idempotent: nodes named P10_* are removed and the original link restored before rebuilding.  Nothing else changes.
`mat_build.py` rebuilds PFA_concrete from scratch: it must run this script after it (hand-off, same as arch_uvbake).
"""
import bpy, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

args = common.script_args()
WEIGHT = float(args[args.index("--weight") + 1]) if "--weight" in args else 0.6
TEX = common.ASSETS / "textures" / "projection2"

ng = bpy.data.node_groups["PFA_concrete"]
N, L = ng.nodes, ng.links
go = next(n for n in N if n.type == "GROUP_OUTPUT")
gi = next(n for n in N if n.type == "GROUP_INPUT")
old_mix = N.get("P10_mix")
if old_mix is not None:
    a_in = next(s for s in old_mix.inputs if s.name == "A" and s.type == "RGBA")
    src = a_in.links[0].from_socket
    for n in [n for n in N if n.name.startswith("P10_")]:
        N.remove(n)
    L.new(src, go.inputs["Color"])
src = go.inputs["Color"].links[0].from_socket
ph = next(n for n in N if n.type == "GROUP" and n.node_tree and n.node_tree.name == "PFA_photo")


def node(t, name, **kw):
    n = N.new(t); n.name = n.label = name
    for k, v in kw.items():
        setattr(n, k, v)
    n.location = (go.location.x - 300, go.location.y - 300 - 60 * len([x for x in N if x.name.startswith("P10_")]))
    return n


def image(fname):
    key = f"TEX_{fname[:-4]}"
    img = bpy.data.images.get(key)
    if img is None:
        img = bpy.data.images.load(str(TEX / fname), check_existing=True)
        img.name = key
    else:
        img.filepath = str(TEX / fname); img.reload()
    img.colorspace_settings.name = "Non-Color"
    return img


uvn = node("ShaderNodeUVMap", "P10_uv"); uvn.uv_map = "UVBake"
rim = node("ShaderNodeTexImage", "P10_ratio", interpolation="Linear", extension="EXTEND"); rim.image = image("PFA_p10_ratio.png")
mim = node("ShaderNodeTexImage", "P10_mask", interpolation="Linear", extension="EXTEND"); mim.image = image("PFA_p10_mask.png")
L.new(uvn.outputs["UV"], rim.inputs["Vector"]); L.new(uvn.outputs["UV"], mim.inputs["Vector"])
sep = node("ShaderNodeSeparateColor", "P10_sep"); L.new(mim.outputs["Color"], sep.inputs["Color"])
x2 = node("ShaderNodeVectorMath", "P10_x2", operation="SCALE")
L.new(rim.outputs["Color"], x2.inputs[0]); x2.inputs["Scale"].default_value = 2.0
r9 = node("ShaderNodeMath", "P10_r9w", operation="MULTIPLY")
L.new(ph.outputs["Weight"], r9.inputs[0]); L.new(gi.outputs["Photo"], r9.inputs[1])
comp = node("ShaderNodeMath", "P10_r9c", operation="SUBTRACT", use_clamp=True)
comp.inputs[0].default_value = 1.0; L.new(r9.outputs[0], comp.inputs[1])
wv = node("ShaderNodeMath", "P10_w", operation="MULTIPLY")
L.new(sep.outputs[0], wv.inputs[0]); wv.inputs[1].default_value = WEIGHT
w2 = node("ShaderNodeMath", "P10_w2", operation="MULTIPLY", use_clamp=True)
L.new(wv.outputs[0], w2.inputs[0]); L.new(comp.outputs[0], w2.inputs[1])
mul = node("ShaderNodeVectorMath", "P10_mul", operation="MULTIPLY")
L.new(src, mul.inputs[0]); L.new(x2.outputs[0], mul.inputs[1])
mix = node("ShaderNodeMix", "P10_mix"); mix.data_type = "RGBA"
a_in = next(s for s in mix.inputs if s.name == "A" and s.type == "RGBA")
b_in = next(s for s in mix.inputs if s.name == "B" and s.type == "RGBA")
L.new(w2.outputs[0], mix.inputs["Factor"]); L.new(src, a_in); L.new(mul.outputs[0], b_in)
col_out = next(s for s in mix.outputs if s.name == "Result" and s.type == "RGBA")
L.new(col_out, go.inputs["Color"])
# the rose column shafts: ref 169's column mask (mat_r7_measure.columns on the REF169_XF-warped photo) is hue 24.8 /
# sat 0.585; the atlas is mean-1 and neutral, so the shaft's mean colour is set here, on MAT_column_rose only, by a
# Hue/Saturation node after the PFA_column group (idempotent: P10_colsat is removed and the link restored first).
COL_SAT = float(args[args.index("--col-sat") + 1]) if "--col-sat" in args else 1.0
COL_HUE = float(args[args.index("--col-hue") + 1]) if "--col-hue" in args else 0.0      # degrees
mt = bpy.data.materials["MAT_column_rose"].node_tree
old = mt.nodes.get("P10_colsat")
if old is not None:
    src_c = old.inputs["Color"].links[0].from_socket
    dsts = [l.to_socket for l in old.outputs["Color"].links]
    mt.nodes.remove(old)
    for d in dsts:
        mt.links.new(src_c, d)
if COL_SAT != 1.0 or COL_HUE != 0.0:
    cgn = next(n for n in mt.nodes if n.type == "GROUP" and n.node_tree and n.node_tree.name == "PFA_column")
    src_c = cgn.outputs["Color"]
    dsts = [l.to_socket for l in src_c.links]
    hs = mt.nodes.new("ShaderNodeHueSaturation"); hs.name = hs.label = "P10_colsat"
    hs.location = (cgn.location.x + 200, cgn.location.y - 200)
    hs.inputs["Hue"].default_value = 0.5 + COL_HUE / 360.0
    hs.inputs["Saturation"].default_value = COL_SAT
    mt.links.new(src_c, hs.inputs["Color"])
    for d in dsts:
        mt.links.new(hs.outputs["Color"], d)
    print(f"[p10int] MAT_column_rose: saturation x{COL_SAT}, hue {COL_HUE:+.1f} deg -> {len(dsts)} consumer(s)")
users = [m.name for m in bpy.data.materials if m.node_tree and any(
    n.type == "GROUP" and n.node_tree == ng for n in m.node_tree.nodes)]
print(f"[p10int] PFA_concrete: atlas wired (weight {WEIGHT}); materials using the group: {users}")
if "--save" in args:
    common.save_blend(common.ASSETS / "materials.blend")
    print("[p10int] saved assets/materials.blend")
