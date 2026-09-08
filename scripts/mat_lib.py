"""Node-building helpers for the Palace of Fine Arts materials library (Blender 5.2, Cycles + Eevee Next).

Design rules (docs/briefs/materials.md):
- everything in object/world space (no UV seams): image textures are BOX projected on object coordinates,
  procedural layers use object coordinates (+ a per-instance random offset) or the world position/normal;
- geometry-driven weathering that works in BOTH engines: AO node (recess dirt, under-ledge streak zones),
  AO with inside=True (convex edge mask, weak in Eevee), Bevel node (Cycles only, adds crisper edge wear);
- per-instance variation from Object Info -> Random (hue, value, pattern offset).

The `Tree` class is a thin fluent wrapper: every helper returns an output socket (or a node) and accepts either
sockets or plain python values for its inputs.
"""
import bpy, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEX_DIR = ROOT / "assets" / "textures"

# Poly Haven sets (CC0): physical tile size in metres (from the asset metadata) used for the box projection.
TEXTURE_SETS = {
    "concrete_wall_008": dict(tile=2.71, folder="polyhaven/concrete_wall_008", mean_lum=0.46),
    "concrete_wall_007": dict(tile=2.16, folder="polyhaven/concrete_wall_007", mean_lum=0.42),
    "concrete_moss": dict(tile=3.00, folder="polyhaven/concrete_moss", mean_lum=0.30),
    "bark_bluegum": dict(tile=1.82, folder="polyhaven/bark_bluegum", mean_lum=0.35),
    "chinese_cedar_bark": dict(tile=2.27, folder="polyhaven/chinese_cedar_bark", mean_lum=0.25),
    "gravelly_sand": dict(tile=2.48, folder="polyhaven/gravelly_sand", mean_lum=0.40),
    "rock_boulder_dry": dict(tile=1.80, folder="polyhaven/rock_boulder_dry", mean_lum=0.45),
    "forest_ground_04": dict(tile=3.15, folder="polyhaven/forest_ground_04", mean_lum=0.25),
}
MAP_SUFFIX = {"diff": "_diff_2k.jpg", "rough": "_rough_2k.jpg", "nor": "_nor_gl_2k.jpg", "ao": "_ao_2k.jpg", "disp": "_disp_2k.jpg"}


def texture_path(set_name, map_name):
    info = TEXTURE_SETS[set_name]
    p = TEX_DIR / info["folder"] / (set_name + MAP_SUFFIX[map_name])
    if not p.exists():   # displacement may be png on some sets
        alt = p.with_suffix(".png")
        p = alt if alt.exists() else p
    return p


def load_image(set_name, map_name, non_color=True):
    """Load (once) an image datablock with an absolute path; common.save_blend remaps it to //textures/..."""
    p = texture_path(set_name, map_name)
    key = f"TEX_{set_name}_{map_name}"
    img = bpy.data.images.get(key)
    if img is None:
        if not p.exists():
            print(f"[mat_lib] WARNING missing texture {p}")
            return None
        img = bpy.data.images.load(str(p), check_existing=True)
        img.name = key
    img.colorspace_settings.name = "Non-Color" if non_color else "sRGB"
    return img


# Macro weathering maps (0.3-3 m features) derived from CC0 ambientCG scans by scripts/mat_make_grunge.py.
# 128 = ratio 1.0; the shader uses them as mean-1.0 value multipliers.  `tile` is the physical size in metres the
# box projection gives them, chosen so the source's own features land in the band that reads at hero distance.
MACRO_MAPS = {
    "pfa_macro_stain": dict(tile=5.5),      # broad soft pour / damp blotches
    "pfa_macro_blotch": dict(tile=3.2),     # mid-scale weathered mottle (second, decorrelating layer)
    "pfa_macro_streak": dict(tile=4.5),     # vertical run-off, a stain field stretched 3.2x down the wall
}


def macro_image(name):
    """Load (once) one of the macro maps as Non-Color; returns None if mat_make_grunge.py has not been run."""
    p = TEX_DIR / "pfa" / f"{name}.png"
    key = f"TEX_{name}"
    img = bpy.data.images.get(key)
    if img is None:
        if not p.exists():
            print(f"[mat_lib] WARNING missing macro map {p} -- run scripts/mat_make_grunge.py")
            return None
        img = bpy.data.images.load(str(p), check_existing=True)
        img.name = key
    img.colorspace_settings.name = "Non-Color"
    return img


def neutral_image(name, color, size=4):
    """A tiny generated Non-Color image used as the *neutral* default of a swappable map socket.

    An Image Texture node with no image is not neutral: it returns Alpha 1.0 in both engines (so the alpha cannot be
    used as a "map plugged in?" flag) and Color (1,0,1) in Cycles / (0,0,0) in Eevee, which decodes to a broken
    normal and, in Eevee, to full AO occlusion. Shipping a flat 4x4 constant instead makes the un-plugged material
    behave exactly like the map-less one, and build_master only swaps the image datablock.
    """
    img = bpy.data.images.get(name)
    if img is None:
        img = bpy.data.images.new(name, size, size, alpha=True, float_buffer=False, is_data=True)
    img.generated_width = img.generated_height = size
    img.generated_color = color
    img.colorspace_settings.name = "Non-Color"
    img.use_fake_user = True
    return img


def sock(sockets, key):
    """Socket by name, falling back to identifier (Mix/ColorRamp/HueSat have duplicate or odd names)."""
    for s in sockets:
        if s.name == key:
            return s
    for s in sockets:
        if s.identifier == key:
            return s
    raise KeyError(f"no socket {key!r} in {[ (x.name, x.identifier) for x in sockets ]}")


# ----------------------------------------------------------------------------- fluent tree builder
class Tree:
    def __init__(self, node_tree):
        self.nt = node_tree
        self._n = 0

    # -- basics
    def new(self, idname, **props):
        n = self.nt.nodes.new(idname)
        self._n += 1
        n.location = (self._n % 12 * 220, -(self._n // 12) * 260)
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def plug(self, socket, value):
        """Connect a socket or set a constant on an input socket."""
        if value is None:
            return
        if isinstance(value, bpy.types.NodeSocket):
            self.nt.links.new(value, socket)
        else:
            try:
                socket.default_value = value
            except Exception:
                if isinstance(value, (int, float)):
                    socket.default_value = (value, value, value, 1.0) if len(socket.default_value) == 4 else (value, value, value)
                else:
                    v = tuple(value)
                    socket.default_value = v if len(socket.default_value) == len(v) else (v + (1.0,))[:len(socket.default_value)]

    def link(self, out_socket, in_socket):
        self.nt.links.new(out_socket, in_socket)

    # -- inputs
    def value(self, v, name=None):
        n = self.new("ShaderNodeValue")
        n.outputs[0].default_value = v
        if name:
            n.name = n.label = name
        return n.outputs[0]

    def rgb(self, c, name=None):
        n = self.new("ShaderNodeRGB")
        n.outputs[0].default_value = (c[0], c[1], c[2], 1.0)
        if name:
            n.name = n.label = name
        return n.outputs[0]

    def texcoord(self):
        return self.new("ShaderNodeTexCoord")

    def geometry(self):
        return self.new("ShaderNodeNewGeometry")

    def objinfo(self):
        return self.new("ShaderNodeObjectInfo")

    # -- math
    def math(self, op, a, b=None, c=None, clamp=False):
        n = self.new("ShaderNodeMath", operation=op, use_clamp=clamp)
        self.plug(n.inputs[0], a)
        if b is not None:
            self.plug(n.inputs[1], b)
        if c is not None:
            self.plug(n.inputs[2], c)
        return n.outputs[0]

    def add(self, a, b): return self.math("ADD", a, b)
    def sub(self, a, b): return self.math("SUBTRACT", a, b)
    def mul(self, a, b): return self.math("MULTIPLY", a, b)
    def div(self, a, b): return self.math("DIVIDE", a, b)
    def madd(self, a, b, c): return self.math("MULTIPLY_ADD", a, b, c)
    def clamp01(self, a): return self.math("ADD", a, 0.0, clamp=True)
    def maximum(self, a, b): return self.math("MAXIMUM", a, b)
    def minimum(self, a, b): return self.math("MINIMUM", a, b)
    def absval(self, a): return self.math("ABSOLUTE", a)
    def fract(self, a): return self.math("FRACT", a)
    def smoothstep(self, v, lo, hi):
        return self.maprange(v, lo, hi, 0.0, 1.0, interp="SMOOTHSTEP")

    def maprange(self, v, fmin, fmax, tmin, tmax, clamp=True, interp="LINEAR"):
        n = self.new("ShaderNodeMapRange", clamp=clamp, interpolation_type=interp)
        self.plug(n.inputs["Value"], v)
        self.plug(n.inputs["From Min"], fmin)
        self.plug(n.inputs["From Max"], fmax)
        self.plug(n.inputs["To Min"], tmin)
        self.plug(n.inputs["To Max"], tmax)
        return n.outputs["Result"]

    def vmath(self, op, a, b=None, scale=None):
        n = self.new("ShaderNodeVectorMath", operation=op)
        self.plug(n.inputs[0], a)
        if b is not None:
            self.plug(n.inputs[1], b)
        if scale is not None:
            self.plug(n.inputs["Scale"], scale)
        return n.outputs["Value"] if op in ("DOT_PRODUCT", "LENGTH", "DISTANCE") else n.outputs["Vector"]

    def vadd(self, a, b): return self.vmath("ADD", a, b)
    def vscale(self, a, s): return self.vmath("SCALE", a, scale=s)
    def vmul(self, a, b): return self.vmath("MULTIPLY", a, b)
    def dot(self, a, b): return self.vmath("DOT_PRODUCT", a, b)

    def sepxyz(self, v):
        n = self.new("ShaderNodeSeparateXYZ")
        self.plug(n.inputs[0], v)
        return n.outputs["X"], n.outputs["Y"], n.outputs["Z"]

    def combxyz(self, x, y, z):
        n = self.new("ShaderNodeCombineXYZ")
        self.plug(n.inputs["X"], x); self.plug(n.inputs["Y"], y); self.plug(n.inputs["Z"], z)
        return n.outputs[0]

    def mapping(self, v, loc=None, rot=None, scale=None):
        n = self.new("ShaderNodeMapping")
        self.plug(n.inputs["Vector"], v)
        self.plug(n.inputs["Location"], loc); self.plug(n.inputs["Rotation"], rot); self.plug(n.inputs["Scale"], scale)
        return n.outputs[0]

    # -- mixing
    def mix(self, fac, a, b, blend="MIX", clamp_fac=True):
        """Colour mix. a, b: colour sockets or tuples. Returns the Result colour socket."""
        n = self.new("ShaderNodeMix", data_type="RGBA", blend_type=blend, clamp_factor=clamp_fac)
        self.plug(sock(n.inputs, "Factor_Float"), fac)
        self.plug(sock(n.inputs, "A_Color"), a); self.plug(sock(n.inputs, "B_Color"), b)
        return n.outputs[2]

    def mixf(self, fac, a, b):
        n = self.new("ShaderNodeMix", data_type="FLOAT")
        self.plug(sock(n.inputs, "Factor_Float"), fac)
        self.plug(sock(n.inputs, "A_Float"), a); self.plug(sock(n.inputs, "B_Float"), b)
        return n.outputs[0]

    def mixv(self, fac, a, b):
        n = self.new("ShaderNodeMix", data_type="VECTOR")
        self.plug(sock(n.inputs, "Factor_Float"), fac)
        self.plug(sock(n.inputs, "A_Vector"), a); self.plug(sock(n.inputs, "B_Vector"), b)
        return n.outputs[1]

    def tint(self, color, fac, mult):
        """color * lerp(1, mult, fac) -- multiply a colour by a grey/colour factor with a mask."""
        return self.mix(fac, color, mult, blend="MULTIPLY")

    def scale_color(self, color, s):
        """color * s (s float socket/value)."""
        return self.vscale(color, s)

    def hsv(self, color, hue=0.5, sat=1.0, val=1.0, fac=1.0):
        n = self.new("ShaderNodeHueSaturation")
        self.plug(n.inputs["Hue"], hue); self.plug(n.inputs["Saturation"], sat)
        self.plug(n.inputs["Value"], val); self.plug(sock(n.inputs, "Fac"), fac); self.plug(n.inputs["Color"], color)
        return n.outputs[0]

    def luminance(self, color):
        return self.dot(color, (0.2126, 0.7152, 0.0722))

    def ramp(self, fac, stops, interp="LINEAR"):
        """stops: [(pos, (r,g,b[,a])), ...]"""
        n = self.new("ShaderNodeValToRGB")
        n.color_ramp.interpolation = interp
        els = n.color_ramp.elements
        while len(els) > 1:
            els.remove(els[-1])
        for i, (pos, col) in enumerate(stops):
            e = els[0] if i == 0 else els.new(pos)
            e.position = pos
            e.color = tuple(col) if len(col) == 4 else tuple(col) + (1.0,)
        self.plug(sock(n.inputs, "Fac"), fac)
        return n.outputs["Color"]

    # -- textures
    def noise(self, vec, scale, detail=2.0, rough=0.5, distortion=0.0, ntype="FBM", w=None, lacunarity=2.0, normalize=True):
        n = self.new("ShaderNodeTexNoise", noise_type=ntype, normalize=normalize)
        if w is not None:
            n.noise_dimensions = "4D"
            self.plug(n.inputs["W"], w)
        self.plug(n.inputs["Vector"], vec)
        self.plug(n.inputs["Scale"], scale); self.plug(n.inputs["Detail"], detail)
        self.plug(n.inputs["Roughness"], rough); self.plug(n.inputs["Distortion"], distortion)
        self.plug(n.inputs["Lacunarity"], lacunarity)
        return n.outputs["Factor"]

    def noise_color(self, vec, scale, detail=2.0, rough=0.5):
        n = self.new("ShaderNodeTexNoise")
        self.plug(n.inputs["Vector"], vec); self.plug(n.inputs["Scale"], scale)
        self.plug(n.inputs["Detail"], detail); self.plug(n.inputs["Roughness"], rough)
        return n.outputs["Color"]

    def voronoi(self, vec, scale, feature="F1", distance="EUCLIDEAN", randomness=1.0, detail=0.0):
        n = self.new("ShaderNodeTexVoronoi", feature=feature, distance=distance)
        self.plug(n.inputs["Vector"], vec); self.plug(n.inputs["Scale"], scale)
        self.plug(n.inputs["Randomness"], randomness); self.plug(n.inputs["Detail"], detail)
        return n

    def wave(self, vec, scale, distortion=0.0, detail=2.0, wave_type="BANDS", direction="Z", profile="SIN"):
        n = self.new("ShaderNodeTexWave", wave_type=wave_type, wave_profile=profile)
        if wave_type == "BANDS":
            n.bands_direction = direction
        else:
            n.rings_direction = direction
        self.plug(n.inputs["Vector"], vec); self.plug(n.inputs["Scale"], scale)
        self.plug(n.inputs["Distortion"], distortion); self.plug(n.inputs["Detail"], detail)
        return n.outputs["Factor"]

    def image(self, img, vec, projection="BOX", blend=0.25, interpolation="Linear"):
        n = self.new("ShaderNodeTexImage", projection=projection, projection_blend=blend, interpolation=interpolation)
        n.image = img
        n.extension = "REPEAT"
        self.plug(n.inputs["Vector"], vec)
        return n

    def image_set(self, set_name, vec, maps=("diff", "rough", "disp"), tile=None):
        """Box-projected Poly Haven set on `vec` (object coords in metres). Returns dict of output sockets."""
        info = TEXTURE_SETS[set_name]
        t = tile or info["tile"]
        v = self.vscale(vec, 1.0 / t)
        out = {}
        for m in maps:
            img = load_image(set_name, m, non_color=(m != "diff"))
            if img is None:
                continue
            node = self.image(img, v)
            node.label = f"{set_name} {m}"
            out[m] = node.outputs["Color"]
        return out

    # -- geometry-driven
    def ao(self, distance=0.5, inside=False, normal=None, samples=8, only_local=False):
        n = self.new("ShaderNodeAmbientOcclusion", inside=inside, samples=samples, only_local=only_local)
        self.plug(n.inputs["Distance"], distance)
        self.plug(n.inputs["Normal"], normal)
        return n.outputs["AO"]

    def bevel(self, radius=0.03, samples=4, normal=None):
        n = self.new("ShaderNodeBevel", samples=samples)
        self.plug(n.inputs["Radius"], radius)
        self.plug(n.inputs["Normal"], normal)
        return n.outputs[0]

    def bump(self, height, strength=0.4, distance=0.01, normal=None, invert=False):
        n = self.new("ShaderNodeBump", invert=invert)
        self.plug(n.inputs["Height"], height); self.plug(n.inputs["Strength"], strength)
        self.plug(n.inputs["Distance"], distance); self.plug(n.inputs["Normal"], normal)
        return n.outputs[0]

    def normal_map(self, color, strength=1.0, uv_map=""):
        n = self.new("ShaderNodeNormalMap", space="TANGENT")
        if uv_map:
            n.uv_map = uv_map
        self.plug(n.inputs["Color"], color); self.plug(n.inputs["Strength"], strength)
        return n.outputs[0]

    # -- shaders
    def principled(self, **inputs):
        n = self.new("ShaderNodeBsdfPrincipled")
        for k, v in inputs.items():
            self.plug(n.inputs[k], v)
        return n

    def output(self, surface=None, volume=None, displacement=None, target="ALL"):
        n = self.new("ShaderNodeOutputMaterial", target=target)
        self.plug(n.inputs["Surface"], surface); self.plug(n.inputs["Volume"], volume)
        self.plug(n.inputs["Displacement"], displacement)
        return n

    def group(self, ng, **inputs):
        n = self.new("ShaderNodeGroup")
        n.node_tree = ng
        n.label = ng.name
        for k, v in inputs.items():
            self.plug(n.inputs[k], v)
        return n


# ----------------------------------------------------------------------------- node groups
def new_group(name, inputs, outputs):
    """(Re)create a shader node group.
    inputs/outputs: list of (name, type, default[, min, max]) with type in FLOAT/FACTOR/COLOR/VECTOR/SHADER."""
    old = bpy.data.node_groups.get(name)
    if old is not None:
        bpy.data.node_groups.remove(old)
    ng = bpy.data.node_groups.new(name, "ShaderNodeTree")
    types = {"FLOAT": "NodeSocketFloat", "FACTOR": "NodeSocketFloat", "COLOR": "NodeSocketColor",
             "VECTOR": "NodeSocketVector", "SHADER": "NodeSocketShader"}
    for spec in inputs:
        nm, ty, default = spec[0], spec[1], spec[2]
        s = ng.interface.new_socket(nm, in_out="INPUT", socket_type=types[ty])
        if ty == "FACTOR":
            s.subtype = "FACTOR"
        if default is not None:
            s.default_value = default
        if len(spec) > 3 and ty in ("FLOAT", "FACTOR"):
            s.min_value, s.max_value = spec[3], spec[4]
    for spec in outputs:
        ng.interface.new_socket(spec[0], in_out="OUTPUT", socket_type=types[spec[1]])
    t = Tree(ng)
    gi = t.new("NodeGroupInput")
    go = t.new("NodeGroupOutput")
    gi.location = (-1200, 0)
    go.location = (2600, 0)
    return ng, t, gi, go


def auto_layout(node_tree, x_gap=230, y_gap=180):
    """Cheap readable layout: columns by longest path from a source node."""
    nodes = list(node_tree.nodes)
    depth = {n.name: 0 for n in nodes}
    changed = True
    it = 0
    while changed and it < 100:
        changed = False
        it += 1
        for l in node_tree.links:
            a, b = l.from_node.name, l.to_node.name
            if depth[b] < depth[a] + 1:
                depth[b] = depth[a] + 1
                changed = True
    cols = {}
    for n in nodes:
        cols.setdefault(depth[n.name], []).append(n)
    for d, col in cols.items():
        for i, n in enumerate(col):
            n.location = (d * x_gap, -i * y_gap)


# ----------------------------------------------------------------------------- material helpers
def new_material(name):
    """Fresh material datablock with an empty node tree (removes an existing one of the same name)."""
    old = bpy.data.materials.get(name)
    if old is not None:
        bpy.data.materials.remove(old)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    m.use_fake_user = True
    m.displacement_method = "BUMP"
    return m


def finish(mat):
    auto_layout(mat.node_tree)
    if "placeholder" in mat:
        del mat["placeholder"]
    mat.use_fake_user = True
    return mat


def srgb_to_linear(c):
    def f(u):
        u = u / 255.0
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4
    return tuple(f(x) for x in c)


def linear_to_srgb(c):
    def f(u):
        return 12.92 * u if u <= 0.0031308 else 1.055 * u ** (1 / 2.4) - 0.055
    return tuple(int(round(255 * min(1.0, max(0.0, f(x))))) for x in c)


def luminance(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


# ----------------------------------------------------------------------------- library use from other files
def append_materials(names, link=False):
    """Append (or link) several library materials in ONE load so shared node groups/images are not duplicated."""
    lib = ROOT / "assets" / "materials.blend"
    if not lib.exists():
        print(f"[mat_lib] missing {lib}")
        return []
    with bpy.data.libraries.load(str(lib), link=link) as (src, dst):
        dst.materials = [n for n in names if n in src.materials]
    out = []
    for n in names:
        m = bpy.data.materials.get(n)
        if m is not None:
            if "placeholder" in m:
                del m["placeholder"]
            out.append(m)
    dedupe_node_groups()
    return out


def dedupe_node_groups():
    """Remap 'PFA_x.001'-style copies of node groups and 'TEX_x.001' images to the original datablocks (after appends)."""
    import re
    n_fixed = 0
    for coll in (bpy.data.node_groups, bpy.data.images):
        for blk in list(coll):
            m = re.match(r"^(.*)\.(\d{3})$", blk.name)
            if not m:
                continue
            base = coll.get(m.group(1))
            if base is None or base is blk:
                continue
            if getattr(blk, "filepath", None) is not None and getattr(base, "filepath", None) != blk.filepath:
                continue     # different image files, leave alone
            blk.user_remap(base)
            coll.remove(blk)
            n_fixed += 1
    if n_fixed:
        print(f"[mat_lib] deduplicated {n_fixed} node groups / images")
    return n_fixed
