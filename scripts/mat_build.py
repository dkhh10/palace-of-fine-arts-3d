"""Materials library builder (Materials & Texturing specialist).

    blender --background --python scripts/mat_build.py

Rebuilds every material of the contract (docs/briefs/materials.md) from scratch, plus the `MAT_test` collection of
sample objects, and saves assets/materials.blend. All materials carry use_fake_user so they survive linking.
Base albedos: docs/reference_sheet.md section 5 (linear). Weathering logic: see docs/materials_notes.md.

Everything is object-space / world-space (no UVs needed). The only scene-level constant baked into node values is
common.WATER_Z (algae band centre) -- if the water level changes, rebuild the library.
"""
import bpy, bmesh, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import mat_lib as ML
from mat_lib import Tree, new_group
from mathutils import Vector

bpy.ops.wm.read_homefile(use_empty=True)
common.wipe_scene()
for m in list(bpy.data.materials):
    bpy.data.materials.remove(m)
for g in list(bpy.data.node_groups):
    bpy.data.node_groups.remove(g)
scene = common.setup_scene()
WATER_Z = common.WATER_Z

# The round-9 projection's global chroma correction, read from the map metadata so the number in the library and
# the number the ratio map was normalised against can never drift apart.  M_chroma is luminance-neutral by
# construction (scripts/mat_projection.py), so it multiplies the finished albedo of the hero band's materials and
# moves ONLY hue and saturation.  Falls back to white if the maps have not been built.
import json as _json
_pm = ML.TEX_DIR / "projection" / "projection_meta.json"
PHOTO_TINT = (1.0, 1.0, 1.0, 1.0)
PHOTO_WEIGHT = 0.6                    # constraint 2 of docs/briefs/materials_r8_projection.md
if _pm.exists():
    _m = _json.loads(_pm.read_text())
    PHOTO_TINT = tuple(_m["M_chroma"]) + (1.0,)
    print(f"[mat_build] projection: albedo tint {PHOTO_TINT}, weight {PHOTO_WEIGHT}, maps {_m['res']}")
else:
    print("[mat_build] WARNING no projection metadata -- run scripts/mat_projection.py build")

# =============================================================================== node groups
G = {}


def build_group_instance():
    ng, t, gi, go = new_group("PFA_instance", [("Seed", "FLOAT", 0.0)],
                              [("R1", "FLOAT", 0.0), ("R2", "FLOAT", 0.0), ("R3", "FLOAT", 0.0), ("R4", "FLOAT", 0.0), ("Offset", "VECTOR", (0, 0, 0))])
    r = t.objinfo().outputs["Random"]
    # `instance_seed` object custom property (set by ORN / build_master on every ornament instance): decorrelates
    # instances that share an Object Info Random (linked duplicates, geometry-nodes instances). Absent -> 0 -> no-op.
    iattr = t.new("ShaderNodeAttribute", attribute_type="OBJECT")
    iattr.attribute_name = "instance_seed"
    ihash = t.fract(t.mul(t.math("SINE", t.mul(iattr.outputs["Fac"], 12.9898)), 43758.5453))
    ihash = t.mul(ihash, t.math("SIGN", t.absval(iattr.outputs["Fac"])))     # property absent -> 0 -> no shift
    # Object Info Random is 0 for every object in some evaluated contexts (and identical for linked duplicates), so the
    # object's own origin is hashed in as well: two instances at different places are then never the same shade.
    loc = t.objinfo().outputs["Location"]
    lhash = t.fract(t.mul(t.math("SINE", t.dot(loc, (12.9898, 78.233, 37.719))), 43758.5453))
    r = t.fract(t.add(t.add(r, ihash), lhash))
    seed = gi.outputs["Seed"]
    r1 = t.fract(t.madd(seed, 0.6180339, r))
    r2 = t.fract(t.madd(r1, 7.31, 0.137))
    r3 = t.fract(t.madd(r1, 13.7, 0.411))
    r4 = t.fract(t.madd(r1, 23.9, 0.713))
    off = t.combxyz(t.madd(r1, 37.1, t.mul(seed, 11.3)), t.madd(r2, 53.3, t.mul(seed, 7.9)), t.mul(r3, 71.7))
    for k, s in (("R1", r1), ("R2", r2), ("R3", r3), ("R4", r4), ("Offset", off)):
        t.link(s, go.inputs[k])
    ML.auto_layout(ng)
    return ng


def build_group_edge():
    """Convex-edge mask: Bevel-normal difference (Cycles) OR inside-AO thinness (both engines)."""
    ng, t, gi, go = new_group("PFA_edge", [("Radius", "FLOAT", 0.03, 0.001, 0.5), ("Normal", "VECTOR", (0, 0, 1))],
                              [("Mask", "FLOAT", 0.0)])
    N = gi.outputs["Normal"]
    bev = t.bevel(radius=gi.outputs["Radius"], samples=4, normal=N)
    d = t.clamp01(t.mul(t.sub(1.0, t.dot(bev, N)), 3.0))
    aoin = t.ao(distance=t.mul(gi.outputs["Radius"], 3.0), inside=True, samples=8, normal=N)
    e_in = t.maprange(aoin, 0.9, 0.7, 0.0, 1.0)
    t.link(t.maximum(d, e_in), go.inputs["Mask"])
    ML.auto_layout(ng)
    return ng


def build_group_streaks():
    """Vertical rain-streak field in world space; strongest under overhangs (up-facing AO)."""
    ng, t, gi, go = new_group("PFA_streaks",
                              [("Offset", "VECTOR", (0, 0, 0)), ("Scale", "FLOAT", 1.5, 0.1, 20), ("Length", "FLOAT", 3.0, 0.2, 30),
                               ("Ledge Distance", "FLOAT", 2.5, 0.1, 20), ("Ledge Weight", "FACTOR", 0.7, 0, 1),
                               ("Shade Bias", "FACTOR", 0.0, 0, 1), ("Normal", "VECTOR", (0, 0, 1))],
                              [("Mask", "FLOAT", 0.0), ("Ledge", "FLOAT", 0.0)])
    I = gi.outputs
    g = t.geometry()
    W = t.vadd(g.outputs["Position"], I["Offset"])
    N = I["Normal"]
    x, y, z = t.sepxyz(W)
    sv = t.combxyz(t.mul(x, I["Scale"]), t.mul(y, I["Scale"]), t.mul(z, t.div(I["Scale"], I["Length"])))
    n1 = t.noise(sv, 1.0, detail=3, rough=0.65)
    n2 = t.noise(t.vscale(sv, 2.3), 1.0, detail=2, rough=0.6)
    # QA-02-3: v2's wide ramps made a low-contrast wash rather than streaks. Tight ramps -> discrete drips.
    m1 = t.smoothstep(n1, 0.47, 0.58)
    m2 = t.smoothstep(n2, 0.51, 0.62)
    # drips fade in and out along their length
    fade = t.maprange(t.noise(t.combxyz(t.mul(x, I["Scale"]), t.mul(y, I["Scale"]), t.mul(z, 0.7)), 1.0, detail=2), 0.35, 0.65, 0.35, 1.0)
    mask = t.mul(t.clamp01(t.madd(m2, 0.6, m1)), fade)
    nx, ny, nz = t.sepxyz(N)
    vert = t.maprange(t.absval(nz), 0.15, 0.75, 1.0, 0.0)
    # sheltered zones: a large-distance AO along the normal drops under cornices, ledges and in corners
    ao_big = t.ao(distance=I["Ledge Distance"], normal=N, samples=8)
    ledge = t.maprange(t.sub(1.0, ao_big), 0.06, 0.5, 0.0, 1.0)
    strength = t.madd(ledge, I["Ledge Weight"], t.sub(1.0, I["Ledge Weight"]))
    shade = t.madd(t.maprange(nx, 0.5, -0.5, 0.35, 1.0), I["Shade Bias"], t.sub(1.0, I["Shade Bias"]))   # north (-X) faces streak more
    out = t.mul(t.mul(t.mul(mask, vert), strength), shade)
    t.link(out, go.inputs["Mask"])
    t.link(ledge, go.inputs["Ledge"])
    ML.auto_layout(ng)
    return ng


def build_group_algae():
    """Dark algae/tide band around a world height with an irregular top edge, plus a pale efflorescence zone above."""
    ng, t, gi, go = new_group("PFA_algae",
                              [("Band Z", "FLOAT", WATER_Z), ("Height", "FLOAT", 0.6, 0.05, 5), ("Offset", "VECTOR", (0, 0, 0))],
                              [("Band", "FLOAT", 0.0), ("Effl", "FLOAT", 0.0), ("Damp", "FLOAT", 0.0),
                               ("Brown", "FLOAT", 0.0)])
    I = gi.outputs
    g = t.geometry()
    ox, oy, oz = t.sepxyz(I["Offset"])
    W = t.vadd(g.outputs["Position"], t.combxyz(ox, oy, 0.0))
    x, y, z = t.sepxyz(W)
    flat = t.combxyz(x, y, 0.0)
    n = t.noise(flat, 0.8, detail=3, rough=0.55)
    n2 = t.noise(flat, 4.0, detail=2, rough=0.5)
    top = t.add(I["Band Z"], t.mul(I["Height"], t.add(t.maprange(n, 0.3, 0.7, 0.55, 1.35), t.maprange(n2, 0.3, 0.7, -0.12, 0.12))))
    band = t.maprange(z, t.sub(top, 0.12), top, 1.0, 0.0)
    # mottled inside the band (not a flat stripe)
    mott = t.maprange(t.noise(W, 6.0, detail=3), 0.3, 0.7, 0.6, 1.0)
    band = t.mul(band, mott)
    # efflorescence: pale zone above the band with vertical streaky edge
    sv = t.combxyz(t.mul(x, 3.0), t.mul(y, 3.0), t.mul(z, 0.4))
    st = t.smoothstep(t.noise(sv, 1.0, detail=2), 0.45, 0.7)
    effl = t.mul(t.maprange(z, top, t.add(top, t.mul(I["Height"], 1.2)), 1.0, 0.0), t.madd(st, 0.6, 0.4))
    effl = t.mul(effl, t.sub(1.0, band))
    # Round 6 (QA-04-3c): a wider DAMP zone above the hard algae band. Splash, capillary rise and shade keep the
    # stone visibly wetter for roughly another band-height above the growth line; it is a value + roughness change,
    # not a colour, and it is what makes the waterline read as a transition rather than as a painted stripe.
    damp = t.maprange(z, t.add(top, t.mul(I["Height"], 1.35)), top, 0.0, 1.0)
    damp = t.mul(damp, t.maprange(t.noise(W, 1.6, detail=3, rough=0.55), 0.3, 0.7, 0.55, 1.0))
    damp = t.maximum(damp, band)
    # green vs brown: filamentous green algae low down where it stays wet, a rust-brown tide scum at the top edge
    brown = t.maprange(t.noise(t.vadd(W, (7.0, 3.0, 0.0)), 1.1, detail=3), 0.35, 0.65, 0.0, 1.0)
    t.link(band, go.inputs["Band"])
    t.link(effl, go.inputs["Effl"])
    t.link(damp, go.inputs["Damp"])
    t.link(brown, go.inputs["Brown"])
    ML.auto_layout(ng)
    return ng


CONCRETE_INPUTS = [
    ("Base Color", "COLOR", (0.42, 0.29, 0.17, 1.0)),
    ("Grey Color", "COLOR", (0.30, 0.25, 0.19, 1.0)),
    ("Grey Drift", "FACTOR", 0.35, 0, 1),
    ("Grey Below Z", "FLOAT", 3.0), ("Grey Above Z", "FLOAT", 10.0),
    ("Tone Variation", "FACTOR", 0.22, 0, 1),
    ("Block Size", "FLOAT", 2.6, 0.1, 50), ("Blotch Size", "FLOAT", 3.0, 0.1, 50),
    ("Drift Size", "FLOAT", 12.0, 0.5, 100),
    ("Detail Color", "COLOR", (0.46, 0.46, 0.46, 1.0)), ("Detail Mean", "FLOAT", 0.46, 0.01, 1),
    ("Detail Rough", "FLOAT", 0.7, 0, 1), ("Detail Height", "FLOAT", 0.5, 0, 1), ("Detail Strength", "FACTOR", 0.6, 0, 1),
    ("Streaks", "FACTOR", 0.55, 0, 1), ("Streak Scale", "FLOAT", 6.0, 0.1, 40), ("Streak Length", "FLOAT", 8.0, 0.2, 30),
    ("Ledge Distance", "FLOAT", 2.5, 0.1, 20), ("Ledge Weight", "FACTOR", 0.85, 0, 1), ("Streak Shade Bias", "FACTOR", 0.0, 0, 1),
    ("Algae", "FACTOR", 1.0, 0, 1), ("Algae Z", "FLOAT", WATER_Z), ("Algae Height", "FLOAT", 0.55, 0.05, 5),
    ("Efflorescence", "FACTOR", 1.0, 0, 3),
    ("Patches", "FACTOR", 0.25, 0, 1),
    ("Edge Wear", "FACTOR", 0.6, 0, 1), ("Edge Radius", "FLOAT", 0.10, 0.001, 0.5),
    ("Recess Dirt", "FACTOR", 0.55, 0, 1), ("Recess Distance", "FLOAT", 0.4, 0.02, 5), ("Extra Dirt", "FACTOR", 0.0, 0, 1),
    ("Cavity", "FACTOR", 0.0, 0, 1),
    ("Vertex Cavity", "FACTOR", 0.0, 0, 1), ("Vertex Dust", "FACTOR", 0.0, 0, 1),
    ("Underside Dirt", "FACTOR", 0.0, 0, 1), ("Rib Grime", "FACTOR", 0.0, 0, 1),
    # round 6 (QA-04-3): photographic macro weathering, 0.3-3 m features, see scripts/mat_make_grunge.py
    ("Macro", "FACTOR", 0.0, 0, 3), ("Macro Scale", "FLOAT", 1.0, 0.02, 20),
    ("Macro Streak", "FACTOR", 0.0, 0, 3), ("Macro Rough", "FACTOR", 0.5, 0, 3),
    # round 7 (QA-05-2): the run-off layer is projected with its vertical axis stretched by `Streak Aspect`, so its
    # features are 0.15-0.9 m wide and 1-4 m long (rain runs), and it is gated to `Run Coverage` of the columns so
    # the under-ledge darkening varies ACROSS the wall instead of being a uniform horizontal stripe.
    ("Streak Aspect", "FLOAT", 4.5, 1.0, 24), ("Run Coverage", "FACTOR", 0.40, 0.02, 1),
    # `Run Scale` multiplies the run-off tile ON TOP of `Macro Scale`. Measured r7a: the ornament material carries
    # the attic panels and runs its macro at `Macro Scale` 0.22, i.e. a 1.0 m streak tile whose own features are
    # 5-20 cm = 1-4 px on the hero, so they averaged out and the attic box's column-mean spread did not move
    # (8.98 -> 8.34 against the photo's 20.0). Ornament needs fine dust AND architectural-scale run-off.
    ("Run Scale", "FLOAT", 1.0, 0.05, 30),
    ("Ledge Band", "FACTOR", 0.62, 0, 3), ("Damp Band", "FACTOR", 0.0, 0, 2),
    ("Roughness", "FLOAT", 0.78, 0, 1), ("Roughness Variation", "FLOAT", 0.12, 0, 1),
    ("Bump", "FLOAT", 0.35, 0, 3),
    ("Pour Lines", "FACTOR", 0.35, 0, 1), ("Pour Spacing", "FLOAT", 0.6, 0.05, 10),
    ("Grid Joints", "FACTOR", 0.0, 0, 1), ("Grid Size", "FLOAT", 1.5, 0.1, 20),
    ("Bird Droppings", "FACTOR", 0.0, 0, 1),
    ("Instance Variation", "FACTOR", 1.0, 0, 2),
    # round 9 (QA-07-2 / the photo-projection pass, docs/briefs/materials_r8_projection.md).
    # `Albedo Tint` is a straight multiply on the finished albedo: the LUMINANCE-NEUTRAL half of the ref-169
    #   correction (`mat_projection.py` prints it as M_chroma) lives here rather than in the projected texture, so
    #   the chroma fix works from every camera, on every surface of the material, and can never make a seam.
    # `Photo` is the weight of the projected ratio map (constraint 2: <= 0.6, and 0 on every material that is not
    #   in the hero band).  The map itself is mean-1 on QA's sunlit attic box, so at any weight the sunlit
    #   luminance window is held by construction and only spatial structure is imported.
    ("Albedo Tint", "COLOR", (1.0, 1.0, 1.0, 1.0)),
    ("Photo", "FACTOR", 0.0, 0, 1),
    ("Seed", "FLOAT", 0.0),
    ("Normal", "VECTOR", (0, 0, 1)),
]


def build_group_concrete():
    ng, t, gi, go = new_group("PFA_concrete", CONCRETE_INPUTS,
                              [("Color", "COLOR", None), ("Roughness", "FLOAT", 0.0), ("Normal", "VECTOR", (0, 0, 1)),
                               ("Streak Mask", "FLOAT", 0.0), ("Dirt Mask", "FLOAT", 0.0), ("Edge Mask", "FLOAT", 0.0),
                               ("Ledge Mask", "FLOAT", 0.0), ("Tone", "FLOAT", 0.0), ("Algae Mask", "FLOAT", 0.0)])
    I = gi.outputs
    inst = t.group(G["instance"], Seed=I["Seed"])
    off, r2, r3, r4 = inst.outputs["Offset"], inst.outputs["R2"], inst.outputs["R3"], inst.outputs["R4"]
    P = t.vadd(t.texcoord().outputs["Object"], off)
    g = t.geometry()
    W = g.outputs["Position"]
    N = I["Normal"]
    wx, wy, wz = t.sepxyz(W)
    nx, ny, nz = t.sepxyz(N)
    px, py, pz = t.sepxyz(P)
    IV = I["Instance Variation"]
    TV = I["Tone Variation"]

    # 1. base + per-instance hue/value
    # QA-02-2: v2 spread instances by +-18 deg of HUE at IV 1.7 (a yellow capital beside a salmon one), which reads
    # as a colour error, not as weathering. Hue now moves +-1.7 deg (pigment-lot scale); the visible per-instance
    # difference is value plus `wvar`, which scales that instance's streaking and recess dirt.
    hue = t.madd(t.sub(r2, 0.5), t.mul(0.0055, IV), 0.5)
    val = t.madd(t.sub(r3, 0.5), t.mul(0.22, IV), 1.0)
    wvar = t.math("MAXIMUM", t.madd(t.sub(r4, 0.5), t.mul(0.9, IV), 1.0), 0.05)
    c = t.hsv(I["Base Color"], hue=hue, val=val)
    # 2. cast-block tone steps (axis-aligned Chebychev cells) + 3. soft pour blotches + 4. fine speckle
    # QA-02-2: the hard Chebychev cell borders read as pasted-on blotches 30-120 px across at hero distance, so the
    # cell coordinate is noise-warped (broken, plaster-like borders) and the step amplitude is cut to 0.35 x TV.
    warp = t.vscale(t.vadd(t.noise_color(P, t.div(0.7, I["Block Size"]), detail=2), (-0.5, -0.5, -0.5)),
                    t.mul(I["Block Size"], 0.55))
    vb = t.voronoi(t.vadd(P, warp), t.div(1.0, I["Block Size"]), feature="F1", distance="CHEBYCHEV", randomness=0.55)
    cell = t.sepxyz(vb.outputs["Color"])[0]
    tb = t.mul(TV, 0.35)
    tone_b = t.maprange(cell, 0.0, 1.0, t.sub(1.0, tb), t.add(1.0, tb))
    # the large soft tonal drift that is what actually reads at 100 m on real cast concrete (8-20 m across)
    nd = t.noise(P, t.div(1.0, I["Drift Size"]), detail=4, rough=0.6)
    tone_dr = t.maprange(nd, 0.25, 0.75, t.sub(1.0, TV), t.add(1.0, TV))
    nb = t.noise(P, t.div(1.0, I["Blotch Size"]), detail=3, rough=0.55)
    tone_n = t.maprange(nb, 0.28, 0.72, t.sub(1.0, TV), t.add(1.0, TV))
    ns = t.noise(P, 30.0, detail=4, rough=0.7)
    tone_s = t.maprange(ns, 0.35, 0.65, 0.93, 1.07)
    # 5. photo detail (luminance only, normalised around its mean)
    dn = t.div(t.luminance(I["Detail Color"]), I["Detail Mean"])
    tone_d = t.mixf(I["Detail Strength"], 1.0, dn)
    tone = t.mul(t.mul(t.mul(tone_b, tone_dr), tone_n), t.mul(tone_s, tone_d))
    # 5b. MACRO weathering (round 6, QA-04-3). The Poly Haven detail above is a 2.2-2.7 m tile: on the 1920x1080
    # hero one pixel is ~5 cm, so it is sampled ~40x below its own texel size and averages to a flat tint -- which
    # is why two rounds of procedural tuning moved the attic's luminance std-dev by 0.02. These three maps are real
    # photographed concrete (CC0 ambientCG scans, lighting divided out, mean exactly 1.0, see mat_make_grunge.py)
    # box-projected in WORLD space at 5.5-9 m, so their own features land at 0.3-3 m: 6-60 px on the hero, which is
    # the band the eye reads as weathering. World space (not object) so the field runs continuously across ARCH's
    # separate meshes and the run-off runs down the wall whatever the object's own axes are.
    Wm = t.vadd(W, off)
    MSC = I["Macro Scale"]
    macro = {}
    for _nm, _info in ML.MACRO_MAPS.items():
        _img = ML.macro_image(_nm)
        if _img is None:
            continue
        _s = t.div(1.0, t.mul(_info["tile"], MSC))
        if _nm == "pfa_macro_streak":
            # ROUND 7, QA-05-2. Round 6 put the same isotropic field on every layer and QA measured the result
            # exactly: streak anisotropy (std of column means / std of row means) 0.64 against the photograph's
            # 4.07 -- "rain runs down, it does not blotch". The run-off map is therefore projected with its
            # VERTICAL axis stretched by `Streak Aspect`: at tile 4.5 m and aspect 4.5 its own 0.05-0.20-of-tile
            # features become 0.2-0.9 m wide and 1-4 m long, which is what a run-off streak is. The stretch is in
            # the projection and not in the map (round 6 pre-stretched the pixels 3.2x, which cost horizontal
            # detail and could not be re-tuned without rebuilding the PNG).
            _sr = t.div(_s, I["Run Scale"])
            _v = t.vmul(Wm, t.combxyz(_sr, _sr, t.div(_sr, I["Streak Aspect"])))
        else:
            _v = t.vscale(Wm, _s)
        # 128 = ratio 1.0 in an 8-bit Non-Color map, so the linear value is half the ratio
        macro[_nm] = t.mul(t.sepxyz(t.image(_img, _v).outputs["Color"])[0], 2.0)
    d_stain = t.sub(macro.get("pfa_macro_stain", 1.0), 1.0) if macro else 0.0
    d_blotch = t.sub(macro.get("pfa_macro_blotch", 1.0), 1.0) if macro else 0.0
    d_streak = t.sub(macro.get("pfa_macro_streak", 1.0), 1.0) if macro else 0.0
    # two decorrelating layers at different tiles, so nothing beats against the 9 m repeat
    d_all = t.add(d_stain, t.mul(d_blotch, 0.75))
    # round 6 biased the macro 35 % toward its dark half to beat AgX's compression; QA measured the cost
    # (attic 180.4 -> 166.5, below its own luminance window) and round 7 gives most of it back: 0.35 -> 0.22.
    d_all = t.sub(d_all, t.mul(t.math("MAXIMUM", d_all, 0.0), 0.22))
    m_tone = t.math("MAXIMUM", t.madd(d_all, I["Macro"], 1.0), 0.30)
    # vertical run-off: keep the map's dark half at full strength and halve its light half (run-off darkens), gate
    # it to near-vertical faces, and let it fade in under shelter. `ledge_all` is built below, so this is finished
    # after the streak group; here only the direction-independent part.
    vertness = t.maprange(t.absval(nz), 0.20, 0.80, 1.0, 0.15)
    dark_biased = t.sub(d_streak, t.mul(t.math("MAXIMUM", d_streak, 0.0), 0.45))
    c = t.vscale(c, tone)
    c = t.vscale(c, m_tone)
    # 6. grey/damp drift (lower zones, noise)
    lowz = t.maprange(wz, I["Grey Below Z"], I["Grey Above Z"], 1.0, 0.0)
    ngd = t.noise(P, 0.15, detail=2, rough=0.5)
    drift = t.clamp01(t.mul(I["Grey Drift"], t.add(t.mul(lowz, 0.7), t.maprange(ngd, 0.4, 0.7, 0.0, 0.6))))
    c = t.mix(drift, c, t.vscale(I["Grey Color"], tone))
    # 7. pour / formwork lines (object z)
    tz = t.fract(t.div(pz, I["Pour Spacing"]))
    dline = t.mul(t.minimum(tz, t.sub(1.0, tz)), I["Pour Spacing"])
    line_n = t.maprange(t.noise(P, 2.0, detail=2), 0.35, 0.65, 0.3, 1.0)     # broken, not ruler-straight
    line = t.mul(t.mul(t.maprange(dline, 0.004, 0.016, 1.0, 0.0), I["Pour Lines"]), line_n)
    c = t.vscale(c, t.sub(1.0, t.mul(line, 0.28)))
    # 7b. slab grid joints (object xy) for paving
    gx = t.fract(t.div(px, I["Grid Size"])); gy = t.fract(t.div(py, I["Grid Size"]))
    dgx = t.mul(t.minimum(gx, t.sub(1.0, gx)), I["Grid Size"]); dgy = t.mul(t.minimum(gy, t.sub(1.0, gy)), I["Grid Size"])
    grid = t.mul(t.maprange(t.minimum(dgx, dgy), 0.004, 0.014, 1.0, 0.0), I["Grid Joints"])
    c = t.vscale(c, t.sub(1.0, t.mul(grid, 0.45)))
    # 8. repair patches (sparse sharp cells, lighter and less saturated)
    # QA-02-2: real skim-coat repairs are feathered, not stencilled. The cell field is noise-warped, the threshold
    # ramp is 0.05 wide (was a 0.004 hard cut) and the tone step is 6 % lighter (was 14 %).
    # Round 6 (QA-04-3d "a few percent of the surface as slightly different-tone rectangular patches with soft
    # edges"): the cell field is Chebychev, i.e. rectangles, mildly noise-warped so the sides are not ruler-straight;
    # the threshold ramp is 0.11 wide (a skim-coat repair feathers into the wall, it is not stencilled); and the
    # patch is no longer always lighter -- a second component of the same cell splits them roughly half lighter /
    # half darker, which is what makes a wall read as repaired rather than as stained.
    pwarp = t.vscale(t.vadd(t.noise_color(P, 0.9, detail=3), (-0.5, -0.5, -0.5)), 1.1)
    vp = t.voronoi(t.vadd(t.vadd(P, (0.5, 0.5, 0.5)), pwarp), 1.0 / 2.4, feature="F1", distance="CHEBYCHEV", randomness=0.8)
    pr = t.sepxyz(vp.outputs["Color"])[1]
    pdir = t.sepxyz(vp.outputs["Color"])[2]
    thr = t.sub(1.0, t.mul(I["Patches"], 0.30))
    pm = t.maprange(pr, thr, t.add(thr, 0.11), 0.0, 1.0)
    pm = t.mul(pm, t.math("GREATER_THAN", I["Patches"], 0.001))
    p_val = t.maprange(pdir, 0.35, 0.65, 0.84, 1.16)          # this patch's own tone step
    c = t.mix(t.mul(pm, 0.85), c, t.hsv(c, sat=0.90, val=p_val))
    # 9. rain streaks
    st = t.group(G["streaks"], Offset=off, Scale=I["Streak Scale"], Length=I["Streak Length"], Normal=N,
                 **{"Ledge Distance": I["Ledge Distance"], "Ledge Weight": I["Ledge Weight"], "Shade Bias": I["Streak Shade Bias"]})
    smask = t.clamp01(t.mul(t.mul(st.outputs["Mask"], I["Streaks"]), wvar))
    # 9a. LEDGE RUN-OFF (round 6, QA-04-3b: "no dark streak under the main cornice or the string course").
    # The streak group's `Ledge` is an isotropic shelter mask -- it drops in every corner, not specifically below a
    # horizontal projection. A second probe answers the actual question "is there an overhang above this point?":
    # an AO probe whose normal is tilted strongly toward +Z, so most of its rays leave the wall going up and only a
    # cornice, string course or box rim above can occlude them. A pure +Z normal cannot be used -- half its rays
    # would start into the wall itself and return a constant ~0.5.
    n_up = t.vmath("NORMALIZE", t.vadd(N, (0.0, 0.0, 1.6)))
    ao_up = t.ao(distance=I["Ledge Distance"], normal=n_up, samples=8)
    overhang = t.maprange(t.sub(1.0, ao_up), 0.08, 0.52, 0.0, 1.0)
    ledge_all = t.maximum(st.outputs["Ledge"], overhang)
    # the band must not be a clean painted stripe: the macro streak map breaks it up along the cornice and gives it
    # the irregular lower edge run-off actually has.
    # ROUND 7: `run_gate` is 1 in the columns the (now vertical) streak field marks dark and 0 in the rest, so the
    # band is a set of runs coming off the cornice, not a painted stripe. Its column-to-column contrast is what QA's
    # anisotropy numerator measures; its lower MEAN is what takes the row-mean spread (the denominator) down.
    if macro:
        _k = t.mul(t.sub(I["Run Coverage"], 0.35), 0.55)
        run_gate = t.maprange(d_streak, _k, t.sub(_k, 0.20), 0.0, 1.0)
        lb_break = t.madd(run_gate, 1.30, 0.18)
    else:
        run_gate, lb_break = 0.5, 1.0
    lband = t.clamp01(t.mul(t.mul(t.mul(ledge_all, t.mul(I["Streaks"], I["Ledge Band"])), wvar),
                            t.mul(lb_break, vertness)))
    c = t.mix(lband, c, t.vmul(c, (0.50, 0.455, 0.375)))
    # 9a-2. the macro run-off layer itself, strongest under the same shelter
    # the run-off layer itself is now present over the whole vertical face (0.55 floor, was 0.35) and doubles under
    # shelter: rain runs the length of a wall, it does not stop 2 m below the cornice.
    m_run = t.madd(t.mul(t.mul(dark_biased, vertness), t.madd(ledge_all, 0.45, 0.55)), I["Macro Streak"], 1.0)
    m_run = t.math("MAXIMUM", m_run, 0.30)
    c = t.vscale(c, m_run)
    # QA-02-2: the v2 streak tint (0.36, 0.37, 0.31) had G > R -- a green multiplier over a broad low-contrast mask,
    # which is where the olive cast on the shaded piers and arch soffits came from. Rain grime on this concrete is a
    # warm dark grey: R > G > B, and it now rides a narrow high-contrast mask so it reads as drips, not as a wash.
    c = t.mix(smask, c, t.vmul(c, (0.46, 0.405, 0.325)))
    # 9b. ORN's per-vertex `cavity` attribute (contract in docs/ornament_notes.md, "Cavity attribute for materials"):
    # POINT / FLOAT_COLOR, 1.0 = open surface, 0.0 = fully enclosed, carried by LOD0 AND LOD1 of the capitals,
    # ceiling rosettes and keystones -- the only recess channel LOD0 has, since LOD0 carries no UVs and LOD0 is the
    # render LOD. Measured distribution (10 rays, quantised to 0.1): capitals p25 0.30 / p50 0.60, keystones and
    # rosettes p25 0.60 / p50 0.90.
    # A shader CANNOT tell "attribute missing" from "attribute = 0": measured in both Cycles and Eevee, a missing
    # geometry attribute reads Fac 0, Color 0 and Alpha *1.0*, so Alpha is not a presence flag. 92 of the 106 ORN
    # meshes (maidens, urns, attic panels, figures, mouldings) carry no `cavity` and share this same material, so a
    # naive (1 - cavity) would paint every one of them uniformly black. `vpres` is therefore a ramp that is exactly
    # 0 at cavity = 0.0: the term vanishes on meshes without the attribute, and on meshes with it the cost is only
    # the deepest ~5 % of vertices (p05 = 0.10), whose immediate neighbours still get the full effect.
    # The ramp is set from the SCREEN-space distribution, not the vertex one. Rendered as raw emission on the hero
    # capital (`mat_scene_check.py --debug-attr`), the visible surface measures p02 0.61 / p10 0.75 / p25 0.93 /
    # p50 1.00: ORN's probe is 10 rays over 6 % of the object diagonal (~66 mm on a capital), so it only finds
    # enclosure deep inside crevices the camera never sees, and the per-vertex p25 of 0.30 is nearly all hidden
    # geometry. A ramp keyed on the vertex statistics (0.62 -> 0.08) moved the rendered capital by 0.7 % and was
    # invisible; 1.00 -> 0.60 puts the whole visible range to work. See the round-5 hand-off in materials_notes.
    vattr = t.new("ShaderNodeAttribute", attribute_type="GEOMETRY", attribute_name="cavity")
    vraw = vattr.outputs["Fac"]
    vpres = t.maprange(vraw, 0.0, 0.05, 0.0, 1.0)
    vdeep = t.maprange(vraw, 1.0, 0.60, 0.0, 1.0)
    vcav = t.mul(vpres, vdeep)
    # 10. recess dirt (AO) + baked/extra dirt + underside soot + vertex-cavity dust
    ao = t.ao(distance=I["Recess Distance"], samples=8, normal=N)
    dirt = t.clamp01(t.add(t.mul(t.mul(t.sub(1.0, ao), I["Recess Dirt"]), wvar), I["Extra Dirt"]))
    dirt = t.clamp01(t.add(dirt, t.mul(t.mul(vcav, I["Vertex Dust"]), wvar)))
    under = t.mul(t.maprange(nz, -0.15, -0.8, 0.0, 1.0), I["Underside Dirt"])
    # Coffer ribs: near-vertical faces, i.e. the coffer returns. This does NOT reach the rib web, and a shader cannot
    # get there: ARCH hangs the rib plate 0.55 m BELOW the panel field, so ribs and panels are parallel down-facing
    # planes -- same normal, and the AO probe reads both as open (a 1.1 m probe keyed on `ao` was tried this round
    # and simply dirtied the whole saucer: dark/light 0.568 -> 0.642 against ref 083's 0.439). Separating them needs
    # the rib plate to carry its own material; see the round-5 hand-off to architecture in materials_notes.
    under = t.clamp01(t.add(under, t.mul(t.maprange(t.absval(nz), 0.60, 0.16, 0.0, 1.0), I["Rib Grime"])))
    dirt_all = t.clamp01(t.add(dirt, t.mul(under, 0.6)))
    c = t.mix(dirt_all, c, t.vmul(c, (0.56, 0.495, 0.405)))
    # 10b. cavity darkening (short AO, value only) -- makes leaf tiers / undercuts read at 100 m (QA-03-4, -15)
    ao_c = t.ao(distance=t.mul(I["Recess Distance"], 0.34), samples=8, normal=N)
    cav = t.mul(t.mul(t.sub(1.0, ao_c), t.sub(1.0, ao_c)), I["Cavity"])
    # the vertex cavity resolves slots the 0.14 m AO probe cannot (leaf-tier undercuts are 20-60 mm deep), so the two
    # add rather than replace each other; clamped so the deepest points stop at 78 % darkening, not black.
    cdark = t.math("MINIMUM", t.add(t.mul(cav, 0.55), t.mul(vcav, t.mul(I["Vertex Cavity"], 0.55))), 0.78)
    c = t.vscale(c, t.sub(1.0, cdark))
    # 11. edge wear (lighter, cleaner, smoother on convex arrises)
    em = t.mul(t.group(G["edge"], Radius=I["Edge Radius"], Normal=N).outputs["Mask"], I["Edge Wear"])
    c = t.mix(em, c, t.hsv(c, sat=0.85, val=1.22))
    # 12. algae band + efflorescence
    al = t.group(G["algae"], Offset=off, Height=I["Algae Height"], **{"Band Z": I["Algae Z"]})
    band = t.mul(al.outputs["Band"], I["Algae"])
    effl = t.mul(t.mul(al.outputs["Effl"], I["Algae"]), I["Efflorescence"])
    effl = t.math("ADD", effl, 0.0, clamp=True)
    # salt bloom: a chalky, slightly crusty white-grey wash just above the tide line (podium, rostra, rip-rap)
    c = t.mix(t.mul(effl, 0.68), c, t.mix(0.85, c, (0.66, 0.635, 0.575)))
    # Round 6 (QA-04-3c). The damp zone first: stone that is wet reads ~35 % darker and slightly cooler, over a
    # ~0.9 m transition above the growth line, so the waterline is a gradient and not an edge.
    dampm = t.mul(t.mul(al.outputs["Damp"], I["Algae"]), I["Damp Band"])
    c = t.mix(t.mul(dampm, 0.60), c, t.vmul(c, (0.60, 0.605, 0.575)))
    # then the algae band itself, green low down and rust-brown at the tide edge (ref sheet: algae (0.10,0.14,0.08),
    # "green algae/black tide band at the waterline (093, 091), efflorescence streaks below the band")
    algae_col = t.mix(al.outputs["Brown"], (0.052, 0.082, 0.040, 1.0), (0.098, 0.076, 0.040, 1.0))
    c = t.mix(band, c, t.mix(0.30, algae_col, c))
    # 13. bird droppings on up-facing surfaces (sparse)
    vd = t.voronoi(t.vadd(P, (0.2, 0.7, 0.1)), 6.0, feature="F1", randomness=1.0)
    dropcell = t.sepxyz(vd.outputs["Color"])[2]
    drop = t.mul(t.maprange(vd.outputs["Distance"], 0.25, 0.32, 1.0, 0.0), t.maprange(dropcell, 0.8, 0.82, 0.0, 1.0))
    drop = t.mul(t.mul(drop, t.maprange(nz, 0.35, 0.8, 0.0, 1.0)), I["Bird Droppings"])
    c = t.mix(drop, c, (0.75, 0.75, 0.70))

    # roughness
    rn = t.noise(P, 4.0, detail=2)
    rough = I["Roughness"]
    rough = t.add(rough, t.mul(t.sub(rn, 0.5), t.mul(2.0, I["Roughness Variation"])))
    rough = t.add(rough, t.mul(t.sub(I["Detail Rough"], 0.5), t.mul(0.3, I["Detail Strength"])))
    rough = t.add(rough, t.mul(dirt_all, 0.08))
    rough = t.sub(rough, t.mul(em, 0.15))
    rough = t.add(rough, t.mul(smask, 0.05))
    # QA-04-3a asks for albedo AND roughness to be driven by the macro maps: a dark stain on concrete is also a
    # rougher, more porous patch, and the two together are what keeps it from reading as a printed decal in
    # raking sun. Sign: darker (m_tone * m_run < 1) -> rougher.
    rough = t.add(rough, t.mul(t.sub(1.0, t.mul(m_tone, m_run)), t.mul(I["Macro Rough"], 0.55)))
    rough = t.mixf(t.mul(dampm, 0.55), rough, 0.34)      # wet stone is smooth and glossy
    rough = t.mixf(band, rough, 0.45)
    rough = t.mixf(effl, rough, 0.92)
    rough = t.math("ADD", rough, 0.0, clamp=True)
    # normal (bump from photo height + fine grain + lines + joints)
    hfine = t.add(t.mul(t.noise(P, 60.0, detail=3, rough=0.6), 0.25), t.mul(t.mul(effl, 0.30), t.noise(P, 22.0, detail=3, rough=0.6)))
    h = t.madd(I["Detail Height"], I["Detail Strength"], hfine)
    h = t.sub(h, t.mul(line, 0.35))
    h = t.sub(h, t.mul(grid, 0.6))
    h = t.add(h, t.mul(pm, 0.08))
    normal = t.bump(h, strength=I["Bump"], distance=0.015, normal=N)

    # 14. round 9: the global chroma correction, then the projected ref-169 ratio (both multiply the finished
    # albedo, so nothing upstream -- streaks, algae, patches, macro -- has to be re-tuned).  `Photo` is 0 on every
    # material that is not in the hero band, and the projector group's own weight is 0 off the band, off-frame,
    # behind the camera and at grazing incidence, so this is a no-op everywhere else in both engines.
    c = t.vmul(c, I["Albedo Tint"])
    ph = t.group(G["photo"])
    c = t.mixv(t.mul(ph.outputs["Weight"], I["Photo"]), c, t.vmul(c, ph.outputs["Ratio"]))

    t.link(c, go.inputs["Color"])
    t.link(rough, go.inputs["Roughness"])
    t.link(normal, go.inputs["Normal"])
    t.link(smask, go.inputs["Streak Mask"])
    t.link(dirt_all, go.inputs["Dirt Mask"])
    t.link(em, go.inputs["Edge Mask"])
    t.link(ledge_all, go.inputs["Ledge Mask"])
    t.link(tone, go.inputs["Tone"])
    t.link(band, go.inputs["Algae Mask"])
    ML.auto_layout(ng)
    return ng


# ------------------------------------------------------------------ the ref-169 projector (round 9)
# The camera scripts/arch_uvproj.py baked `UVProj` from -- cam01 as it stood before the round-08 station move.
# architecture.blend has not been rebuilt since, so this IS the frame the baked layer is in, and it is also the
# frame arch_params.REF169_XF aligns ref 169 into.  The projection is computed from the world position here
# instead of read from `UVProj` for one measured reason: `UVProj` exists on the 33 ARCH meshes only, and QA's
# attic box is covered by ORN's attic-panel assets (MAT_ornament_concrete), which have no such layer -- a
# UVProj-only projection would land on the ARCH field and stop at every ornament edge, which is a seam generator.
# scripts/mat_r9_uvcheck.py measures this projection against the baked layer vertex by vertex; they agree to
# < 0.05 px, so this is the same projection, computed rather than baked (and immune to an ARCH rebuild).
PROJ_LOC = (-14.1, 100.0, 1.6)
PROJ_TARGET = (0.0, 0.0, 1.6)
PROJ_LENS, PROJ_SENSOR, PROJ_SHIFT_Y = 20.0, 36.0, 0.06
PROJ_RES = (1920, 1080)
# Facing ramp: full weight face-on to 58 deg, zero past 80 deg.  The spec said 25-70.  MEASURED why it moved: at
# 45/72 the shaded attic ressaut returns (50-65 deg off the projector) got an effective weight of ~0.26 instead of
# 0.6 and the box moved 136.4 -> 132.9 where the ratio map is worth 136.4 -> 124.5; QA-07-7's materials half is
# exactly those oblique returns, so the plateau has to cover them.  80 deg is a 5.8x texel stretch, but it is only
# ever reached where the weight is already ramping to zero, and every one of those faces is a 2-6 px return on the
# hero.
PROJ_FACE_LO, PROJ_FACE_HI = math.cos(math.radians(80.0)), math.cos(math.radians(58.0))
PROJ_Z = (24.0, 26.0, 45.5, 47.5)      # world z ramp: the drum / attic / entablature band and nothing else
PROJ_R = 34.0                          # world radius from the rotunda axis


def projector_basis():
    """(right, up, forward, u_scale, u_off, v_scale, v_off) for PROJ_*, matching Blender's own camera maths.

    Blender: with sensor_fit HORIZONTAL the view plane at unit distance spans +-sensor/(2*lens) in x and that
    times res_y/res_x in y, and shift_y displaces it by shift_y * sensor / lens (BKE_camera_params_compute_viewplane
    with viewfac = res_x).  So for a camera-space point, X = xc/depth, Y = yc/depth:
        u = (X + hx) / (2 hx)                       hx = sensor / (2 lens)
        v = (Y - shift_y * sensor / lens + hy) / (2 hy)      hy = hx * res_y / res_x
    v = 0 at the BOTTOM, which is both Blender's image convention and arch_uvproj's `UVProj` convention.
    """
    from mathutils import Euler, Matrix
    rot = common.lookat_rotation(PROJ_LOC, PROJ_TARGET)
    M = Euler(rot).to_matrix()
    right, up, back = M.col[0], M.col[1], M.col[2]
    forward = -back
    hx = PROJ_SENSOR / (2.0 * PROJ_LENS)
    hy = hx * PROJ_RES[1] / PROJ_RES[0]
    dy = PROJ_SHIFT_Y * PROJ_SENSOR / PROJ_LENS
    return (tuple(right), tuple(up), tuple(forward),
            1.0 / (2.0 * hx), 0.5,
            1.0 / (2.0 * hy), (hy - dy) / (2.0 * hy))


def build_group_photo():
    """ref 169 as a mean-1 albedo ratio, projected from the hero station. Outputs Ratio (COLOR) and Weight (FLOAT)."""
    ng, t, gi, go = new_group("PFA_photo", [("Normal", "VECTOR", (0, 0, 1))],
                              [("Ratio", "COLOR", None), ("Weight", "FLOAT", 0.0)])
    right, up, fwd, us, uo, vs, vo = projector_basis()
    geo = t.geometry()
    pos = geo.outputs["Position"]
    d = t.vmath("SUBTRACT", pos, PROJ_LOC)
    xc = t.dot(d, right)
    yc = t.dot(d, up)
    depth = t.dot(d, fwd)
    inv = t.div(1.0, t.maximum(depth, 1.0))
    u = t.madd(t.mul(xc, inv), us, uo)
    v = t.madd(t.mul(yc, inv), vs, vo)
    uv = t.combxyz(u, v, 0.0)

    ratio_img = ML.projection_image("PFA_photo_ratio")
    mask_img = ML.projection_image("PFA_photo_mask")
    if ratio_img is None or mask_img is None:
        t.link(t.rgb((1.0, 1.0, 1.0, 1.0)), go.inputs["Ratio"])
        t.link(t.value(0.0), go.inputs["Weight"])
        ML.auto_layout(ng)
        return ng
    rn = t.new("ShaderNodeTexImage", interpolation="Linear")
    rn.image = ratio_img; rn.extension = "CLIP"; rn.label = "PFA_photo_ratio"
    t.plug(rn.inputs["Vector"], uv)
    mn = t.new("ShaderNodeTexImage", interpolation="Linear")
    mn.image = mask_img; mn.extension = "CLIP"; mn.label = "PFA_photo_mask"
    t.plug(mn.inputs["Vector"], uv)
    conf, band, cov = t.sepxyz(mn.outputs["Color"])

    # facing: the angle between the shading point's TRUE normal and the direction back to the projector.
    to_cam = t.vmath("NORMALIZE", t.vmath("SUBTRACT", PROJ_LOC, pos))
    ndot = t.dot(to_cam, geo.outputs["True Normal"])
    facing = t.maprange(ndot, PROJ_FACE_LO, PROJ_FACE_HI, 0.0, 1.0, interp="SMOOTHSTEP")

    # world gates: only the rotunda's drum / attic / entablature band, and only in front of the projector.
    z = t.sepxyz(pos)[2]
    zgate = t.mul(t.maprange(z, PROJ_Z[0], PROJ_Z[1], 0.0, 1.0),
                  t.maprange(z, PROJ_Z[2], PROJ_Z[3], 1.0, 0.0))
    rad = t.vmath("LENGTH", t.vmul(pos, (1.0, 1.0, 0.0)))
    rgate = t.maprange(rad, PROJ_R, PROJ_R + 3.0, 1.0, 0.0)
    front = t.maprange(depth, 5.0, 15.0, 0.0, 1.0)

    w = t.mul(t.mul(t.mul(conf, band), cov), t.mul(facing, t.mul(zgate, t.mul(rgate, front))))
    t.link(t.vscale(rn.outputs["Color"], 2.0), go.inputs["Ratio"])     # stored as ratio / 2
    t.link(w, go.inputs["Weight"])
    ML.auto_layout(ng)
    return ng


def build_group_column():
    """Column-shaft specifics on top of the concrete group: drum joints, per-drum tone, dark zone under the capital,
    pale wash streaks (lighter, greyer -- the pigment washes out), all in object space (origin at the shaft base)."""
    ng, t, gi, go = new_group("PFA_column",
                              [("Color", "COLOR", None), ("Wash Color", "COLOR", (0.42, 0.24, 0.21, 1.0)), ("Wash", "FACTOR", 0.5, 0, 1),
                               ("Drum Height", "FLOAT", 3.25, 0.2, 30), ("Drum Variation", "FACTOR", 0.07, 0, 0.5),
                               ("Top Z", "FLOAT", 16.3), ("Top Darkening", "FACTOR", 0.3, 0, 1), ("Seed", "FLOAT", 0.0),
                               ("Normal", "VECTOR", (0, 0, 1))],
                              [("Color", "COLOR", None), ("Joint", "FLOAT", 0.0), ("Wash Mask", "FLOAT", 0.0)])
    I = gi.outputs
    inst = t.group(G["instance"], Seed=I["Seed"])
    off = inst.outputs["Offset"]
    P = t.texcoord().outputs["Object"]
    px, py, pz = t.sepxyz(P)
    # drums
    d = t.div(pz, I["Drum Height"])
    di = t.math("FLOOR", d)
    fr = t.fract(d)
    joint_d = t.mul(t.minimum(fr, t.sub(1.0, fr)), I["Drum Height"])
    joint = t.maprange(joint_d, 0.004, 0.02, 1.0, 0.0)
    drum_rand = t.fract(t.mul(t.add(di, t.mul(inst.outputs["R1"], 31.7)), 0.7548776))
    tone = t.maprange(drum_rand, 0.0, 1.0, t.sub(1.0, I["Drum Variation"]), t.add(1.0, I["Drum Variation"]))
    c = t.vscale(I["Color"], tone)
    c = t.vscale(c, t.sub(1.0, t.mul(joint, 0.35)))
    # under-capital darkening (dirt shadow zone)
    topd = t.mul(t.maprange(pz, t.sub(I["Top Z"], 1.8), I["Top Z"], 0.0, 1.0), I["Top Darkening"])
    c = t.mix(topd, c, t.vmul(c, (0.62, 0.55, 0.5)))
    # pale wash streaks running down the shaft
    st = t.group(G["streaks"], Offset=off, Scale=2.5, Length=12.0, Normal=I["Normal"], **{"Ledge Distance": 1.5, "Ledge Weight": 0.3})
    wash = t.mul(st.outputs["Mask"], I["Wash"])
    lum = t.luminance(c)
    washed = t.mix(0.65, c, t.vscale(I["Wash Color"], t.div(lum, 0.22)))
    c = t.mix(wash, c, washed)
    t.link(c, go.inputs["Color"])
    t.link(joint, go.inputs["Joint"])
    t.link(wash, go.inputs["Wash Mask"])
    ML.auto_layout(ng)
    return ng


def build_group_dome():
    """Rotunda dome cap.  Round 10 (QA-10-8): the old group read as a near-white plastic lid in the hero box
    920 95 1000 120 (lum 187.6 / hue 40.0 / sat 0.463 / column-sd 5.34 against ref 169's 224.3 / 44.1 / 0.272 /
    6.61).  Three measured faults, all fixed here.

    1. `Base Normal Z` was 0.66.  The dome is a spherical cap of radius 19.23 m (local mesh r 0..16.50, z
       0.05..9.40, so the rim's world normal z is 0.514, not 0.66) -- the grime ring and the lower-flank
       darkening were therefore sitting in the MIDDLE of the visible cap, not at its foot.  Measured row by row
       on the round-10b hero: the ungrimed rows 95-99 read 228 lum / sat 0.21, the grimed rows 103-115 read
       190 / 0.40, and ref 169 reads 226-249 / 0.17-0.32 over the whole span with no ring at all.  The default
       is now 0.52 and the lower-flank mix drops 0.30 -> 0.10, which is what recovers the level and the chroma.
    2. There was no structure the hero can resolve.  The dome is 33 m across in ~190 px, i.e. 0.17 m/px, and the
       old seams were 0.05 m wide (0.3 px) on a 48-fold division -- they averaged out to nothing, which is the
       column-sd 5.34.  The cap is now built as 28 meridional PANELS (ref: the panel lines countable in
       reference/photos/material_crops/dome_2.jpg and dome_3.jpg, ~10-14 across the visible half), each with its
       own tone drawn from a per-panel hash and a slower per-family drift, separated by a RIDGE 0.30 m wide that
       carries the lap shadow, a lit sliver beside it and real bump.  At r = 14 m that is 3.14 m = 18 px per
       panel, so the hero resolves the rhythm.
    3. The rain streaks were noise at 0.34 m (2 px) and disappeared for the same reason.  They are now keyed to
       `Streak Width` (1.4 m = 8 px at the box) along the parallel and stretched 10:1 down the meridian, which
       is the proportion in dome_2.jpg.

    Moss stays but is nearly off by default: dome_2.jpg (pre-recoat) is green on the north flank, ref 169 (2020,
    the target) has none.  Object space: origin on the dome axis; world normal for orientation."""
    ng, t, gi, go = new_group("PFA_dome",
                              [("Base Color", "COLOR", (0.70, 0.66, 0.58, 1.0)), ("Streak Color", "COLOR", (0.50, 0.52, 0.52, 1.0)),
                               ("Moss Color", "COLOR", (0.42, 0.47, 0.40, 1.0)), ("Grime Color", "COLOR", (0.20, 0.13, 0.06, 1.0)),
                               ("Panels", "FLOAT", 28.0, 4, 400), ("Ridge Width", "FLOAT", 0.30, 0.02, 2.0),
                               ("Ridge Dark", "FACTOR", 0.30, 0, 1), ("Panel Tone", "FACTOR", 0.22, 0, 1),
                               ("Ring Spacing", "FLOAT", 2.6, 0.2, 20.0), ("Ring", "FACTOR", 0.10, 0, 1),
                               ("Streaks", "FACTOR", 0.7, 0, 1), ("Streak Width", "FLOAT", 1.4, 0.05, 10.0),
                               ("Moss", "FACTOR", 0.6, 0, 1), ("Grime", "FACTOR", 0.8, 0, 1),
                               ("Base Normal Z", "FLOAT", 0.52), ("Roughness", "FLOAT", 0.35, 0, 1), ("Bump", "FLOAT", 0.3, 0, 3),
                               ("Seed", "FLOAT", 0.0), ("Normal", "VECTOR", (0, 0, 1))],
                              [("Color", "COLOR", None), ("Roughness", "FLOAT", 0.0), ("Normal", "VECTOR", (0, 0, 1)), ("Coat", "FLOAT", 0.0)])
    I = gi.outputs
    inst = t.group(G["instance"], Seed=I["Seed"])
    off = inst.outputs["Offset"]
    P = t.texcoord().outputs["Object"]
    px, py, pz = t.sepxyz(P)
    N = I["Normal"]
    nx, ny, nz = t.sepxyz(N)
    ang = t.math("ARCTAN2", py, px)                                   # -pi..pi, constant along a meridian
    r = t.math("SQRT", t.add(t.mul(px, px), t.mul(py, py)))
    steep = t.maprange(nz, 0.97, t.add(I["Base Normal Z"], 0.04), 0.15, 1.0)

    # ---- meridional panels and their ridges -------------------------------------------------------------
    u = t.madd(t.div(ang, 2 * math.pi), 1.0, 0.5)                     # 0..1 around the axis
    up = t.mul(u, I["Panels"])
    pidx = t.math("FLOOR", up)
    pf = t.fract(up)
    arc = t.div(t.mul(2 * math.pi, r), I["Panels"])                   # metres of parallel per panel at this r
    ed = t.mul(t.minimum(pf, t.sub(1.0, pf)), arc)                    # metres to the nearest ridge
    # per-panel tone: a hash (decorrelated neighbours) times a slower family drift, so the panels come in
    # groups of three or four as they do in dome_2.jpg rather than as a per-panel dither.
    ph = t.noise(t.combxyz(t.madd(pidx, 2.37, t.mul(I["Seed"], 0.113)), 11.3, 0.0), 1.0, detail=0.0)
    pfam = t.noise(t.combxyz(t.madd(pidx, 0.42, t.mul(I["Seed"], 0.071)), 4.7, 0.0), 1.0, detail=2.0)
    tone_p = t.mul(t.maprange(ph, 0.12, 0.88, t.sub(1.0, I["Panel Tone"]), t.add(1.0, I["Panel Tone"])),
                   t.maprange(pfam, 0.20, 0.80, 0.94, 1.06))
    ridge_line = t.maprange(ed, t.mul(I["Ridge Width"], 0.22), t.mul(I["Ridge Width"], 0.75), 1.0, 0.0)
    ridge_lit = t.mul(t.maprange(ed, t.mul(I["Ridge Width"], 0.75), t.mul(I["Ridge Width"], 2.20), 1.0, 0.0),
                      t.sub(1.0, ridge_line))
    # horizontal lap courses: faint, in object height, so they are circles on the cap
    rz = t.fract(t.div(pz, I["Ring Spacing"]))
    ring = t.mul(t.maprange(t.mul(t.minimum(rz, t.sub(1.0, rz)), I["Ring Spacing"]), 0.0, 0.10, 1.0, 0.0), I["Ring"])

    # ---- radial rain streaks ----------------------------------------------------------------------------
    # `ang` (not arc length) keeps a streak on its meridian; the scale is set so one noise unit is
    # `Streak Width` metres at r = 14 m, the radius the hero's dome-cap box actually sees (measured by
    # scripts/mat_r10_probe.py: r 13.08-15.49 m, world nz 0.586-0.740).
    sv = t.vadd(t.combxyz(t.mul(ang, t.div(14.0, I["Streak Width"])), t.mul(pz, 0.10), 0.0), t.vscale(off, 0.01))
    n1 = t.noise(sv, 1.0, detail=3, rough=0.62)
    n2 = t.noise(t.vscale(sv, 2.7), 1.0, detail=2, rough=0.55)
    fade = t.maprange(t.noise(t.combxyz(t.mul(ang, 3.2), t.mul(pz, 0.45), 0.0), 1.0, detail=2), 0.35, 0.68, 0.25, 1.0)
    smask = t.mul(t.clamp01(t.add(t.smoothstep(n1, 0.44, 0.66), t.mul(0.45, t.smoothstep(n2, 0.52, 0.72)))), fade)
    smask = t.mul(t.mul(smask, steep), I["Streaks"])
    smask = t.clamp01(t.add(smask, t.mul(ridge_line, t.mul(0.30, I["Streaks"]))))   # the joints hold dirt too

    # ---- moss, grime ring, tone -------------------------------------------------------------------------
    north = t.maprange(nx, -0.15, -0.6, 0.0, 1.0)
    mp = t.smoothstep(t.noise(t.vadd(P, off), 1.8, detail=3, rough=0.6), 0.56, 0.68)
    moss = t.mul(t.mul(t.mul(north, mp), steep), I["Moss"])
    ring_n = t.maprange(t.noise(t.vadd(P, off), 4.0, detail=2), 0.35, 0.65, -0.006, 0.006)
    grime = t.mul(t.maprange(nz, t.add(t.add(I["Base Normal Z"], 0.02), ring_n), t.add(I["Base Normal Z"], 0.004), 0.0, 1.0), I["Grime"])
    lower = t.mul(t.maprange(nz, 0.9, t.add(I["Base Normal Z"], 0.03), 0.0, 0.10), I["Grime"])
    tv = t.maprange(t.noise(t.vadd(P, off), 0.25, detail=2), 0.35, 0.65, 0.94, 1.06)
    # panel tone, ridge shadow / lit sliver and the lap ring all act on the albedo as one multiplier
    fac = t.mul(t.mul(tone_p, tv),
                t.add(t.sub(1.0, t.add(t.mul(ridge_line, I["Ridge Dark"]), ring)), t.mul(ridge_lit, 0.07)))
    c = t.vscale(I["Base Color"], fac)
    c = t.mix(smask, c, t.vscale(I["Streak Color"], t.mul(tone_p, tv)))
    c = t.mix(moss, c, I["Moss Color"])
    c = t.mix(lower, c, t.vmul(c, (0.75, 0.72, 0.68)))
    c = t.mix(grime, c, I["Grime Color"])
    rough = I["Roughness"]
    rough = t.add(rough, t.mul(smask, 0.22))
    rough = t.mixf(moss, rough, 0.75)
    rough = t.mixf(grime, rough, 0.6)
    rough = t.add(rough, t.mul(ridge_line, 0.10))
    rough = t.add(rough, t.mul(t.sub(t.noise(P, 3.0, detail=2), 0.5), 0.08))
    coat = t.mul(t.sub(1.0, t.clamp01(t.add(t.add(smask, moss), grime))), 0.4)
    # bump: the ridge is a real lap, plus a fine membrane grain
    h = t.add(t.mul(t.maprange(ed, 0.0, I["Ridge Width"], 1.0, 0.0), 0.55), t.mul(t.noise(P, 18.0, detail=3), 0.12))
    normal = t.bump(h, strength=I["Bump"], distance=0.02, normal=N)
    t.link(c, go.inputs["Color"]); t.link(t.math("ADD", rough, 0.0, clamp=True), go.inputs["Roughness"])
    t.link(normal, go.inputs["Normal"]); t.link(coat, go.inputs["Coat"])
    ML.auto_layout(ng)
    return ng


G["instance"] = build_group_instance()
G["edge"] = build_group_edge()
G["streaks"] = build_group_streaks()
G["algae"] = build_group_algae()
G["photo"] = build_group_photo()
G["concrete"] = build_group_concrete()
G["column"] = build_group_column()
G["dome"] = build_group_dome()


# =============================================================================== materials
def concrete_material(name, tex_set, seed, params, specular=0.30, column=None, baked=False, extra=None):
    m = ML.new_material(name)
    t = Tree(m.node_tree)
    inst = t.group(G["instance"], Seed=seed)
    P = t.vadd(t.texcoord().outputs["Object"], inst.outputs["Offset"])
    tex = t.image_set(tex_set, P, maps=("diff", "rough", "disp"))
    geo = t.geometry()
    N = geo.outputs["Normal"]
    if baked:
        # Hooks for ORN's baked LOD1 maps. build_master.orn_material_for() copies this material per asset and loads
        # assets/textures/orn/ORN_<asset>_nrm.png / _ao.png (Non-Color) into the nodes named ORN_NORMAL / ORN_AO.
        # The nodes are NOT left empty: an Image Texture node with no image returns Alpha 1.0 in both engines and
        # Color (1,0,1) in Cycles / (0,0,0) in Eevee (measured), i.e. neither the alpha nor the colour can be used to
        # detect "no bake plugged", and both fallbacks are wrong (a pink normal, or full AO dirt in Eevee). Each node
        # therefore ships with a 4x4 generated NEUTRAL image -- flat tangent normal and pure white AO -- so the
        # library material and every LOD0 instance behave exactly as if the hooks were not there, and build_master
        # only has to swap the image datablock.
        nm_img = t.new("ShaderNodeTexImage"); nm_img.name = nm_img.label = "ORN_NORMAL"
        nm_img.image = ML.neutral_image("ORN_NEUTRAL_normal", (0.5, 0.5, 1.0, 1.0))
        ao_img = t.new("ShaderNodeTexImage"); ao_img.name = ao_img.label = "ORN_AO"
        ao_img.image = ML.neutral_image("ORN_NEUTRAL_ao", (1.0, 1.0, 1.0, 1.0))
        w = t.value(1.0, "ORN_MAP_WEIGHT")
        nmap = t.normal_map(nm_img.outputs["Color"], strength=1.0)
        N = t.mixv(w, geo.outputs["Normal"], nmap)
        extra = dict(extra or {})
        ao_r = t.sepxyz(ao_img.outputs["Color"])[0]
        extra["Extra Dirt"] = t.mul(w, t.mul(t.sub(1.0, ao_r), 0.6))
    kw = {"Detail Color": tex["diff"], "Detail Rough": tex["rough"], "Detail Height": tex["disp"],
          "Detail Mean": ML.TEXTURE_SETS[tex_set]["mean_lum"], "Seed": seed, "Normal": N}
    kw.update(params)
    if extra:
        kw.update(extra)
    g = t.group(G["concrete"], **kw)
    color = g.outputs["Color"]
    if column:
        cg = t.group(G["column"], Color=color, Seed=seed, Normal=N, **column)
        color = cg.outputs["Color"]
    bsdf = t.principled(**{"Base Color": color, "Roughness": g.outputs["Roughness"], "Normal": g.outputs["Normal"],
                           "Specular IOR Level": specular})
    t.output(surface=bsdf.outputs[0])
    m["pfa_texture_set"] = tex_set
    return ML.finish(m)


def C(r, g, b):
    return (r, g, b, 1.0)


def build_concrete_family():
    # Round-3 (QA-02-2/-3/-14) changes across the family:
    #  - Base Color hue pushed +4 to +8 deg toward the reference ochre (ref 169 sunlit stone sits at 34-39 deg).
    #  - Tone Variation raised but carried by `Drift Size` (soft, 8-20 m) instead of hard cast-block cells.
    #  - Streak Scale/Length retuned to narrow (0.13-0.17 m) long (1-1.5 m) drips concentrated under ledges.
    #  - Edge Radius 0.02-0.03 -> 0.05-0.14 m so worn arrises read at 100 m (7 cm/px on the hero).
    #  - Algae on every material that can reach z = WATER_Z; the mask is height-gated so high geometry is untouched.
    # walls, entablature, attic, drum (upper rotunda): the reference ochre
    concrete_material("MAT_concrete_ochre", "concrete_wall_008", 1.0, {
        # ROUND 9 (QA-07-2, the blocker).  The chroma deficit is not a guess: ref 169 aligned into the projector
        # frame and divided by this build's own render over QA's attic box gives an RGB correction of
        # (1.026, 1.001, 0.749), whose luminance-neutral part is PHOTO_TINT.  It multiplies the FINISHED albedo,
        # so it reaches every camera and every surface of this material and cannot make a seam at the projection's
        # edge.  ROUND 9b (review finding 5): the round-9 text here claimed this "lands the box at sat 0.59 /
        # R-B 138", which was an ALBEDO-space prediction stated as a rendered fact.  MEASURED on the hero it lands
        # the box at sat 0.461 / R-B +104.7 with lum 189.8 -- that number was the ASK, not the result, because the
        # tint multiplies a scene-linear albedo while the ask was read in AgX display space.  The measured in-situ
        # chroma transfers (albedo blue x0.758 moves the sunlit box's display blue -2.2 % and the shaded box's
        # -12.2 %, i.e. t_B 0.080 and 0.470) are also why the tint is NOT linearised the way the ratio map now is:
        # the shaded attic's sat <= 0.50 ceiling binds at albedo blue x0.666, and at that ceiling the sunlit box
        # only reaches sat 0.478 / R-B +109, still outside 0.53-0.62 / >= 120.  docs/materials_notes.md round 9b.
        "Albedo Tint": PHOTO_TINT, "Photo": PHOTO_WEIGHT,
        # round 7 (QA-05-2): +8 % on red / +7 % on green with G/R 0.832 -> 0.789. On the r12 rig the sunlit attic
        # measured lum 173.8 sat 0.530 against ref 169's 188.5 / 0.582, i.e. the last of the gap is albedo value
        # AND chroma (lighting r12 hand-off 2 says the same); raising red hardest lifts both at once.
        "Base Color": C(0.748, 0.590, 0.105), "Grey Color": C(0.450, 0.385, 0.062), "Grey Drift": 0.16,
        "Grey Below Z": 3.0, "Grey Above Z": 10.0, "Tone Variation": 0.30, "Block Size": 3.6, "Blotch Size": 0.9,
        "Drift Size": 12.0,
        "Detail Strength": 1.0, "Streaks": 1.0, "Streak Scale": 3.2, "Streak Length": 7.0, "Ledge Distance": 3.0, "Ledge Weight": 0.55,
        "Algae": 1.0, "Algae Z": WATER_Z, "Algae Height": 0.75, "Damp Band": 1.0,
        # QA-05-2: the isotropic half of the macro comes down 2.6x and the vertical half goes up; the horizontal
        # pour lines (0.6 m spacing = 12 px on the hero, i.e. three of them inside QA's 34 px attic box) come down
        # 3.5x and their spacing more than doubles, because they were the largest materials-owned contribution to
        # the ROW-mean spread that is the denominator of the anisotropy statistic.
        "Macro": 0.45, "Macro Scale": 1.0, "Macro Streak": 2.40, "Macro Rough": 0.60, "Ledge Band": 1.35,
        "Streak Aspect": 6.0, "Run Coverage": 0.32,
        "Patches": 0.30, "Edge Wear": 0.34, "Edge Radius": 0.12, "Recess Dirt": 0.72, "Recess Distance": 0.7, "Cavity": 0.70,
        "Roughness": 0.78, "Roughness Variation": 0.12, "Bump": 0.35, "Pour Lines": 0.10, "Pour Spacing": 1.4},
        specular=0.09)
    # podium, pedestals, rostra, platform: greyer, damper, algae band at the water line
    concrete_material("MAT_concrete_podium", "concrete_wall_007", 2.0, {
        "Base Color": C(0.545, 0.474, 0.110), "Grey Color": C(0.402, 0.372, 0.080), "Grey Drift": 0.38,
        "Grey Below Z": 0.5, "Grey Above Z": 5.0, "Tone Variation": 0.20, "Block Size": 2.4, "Blotch Size": 2.2,
        "Drift Size": 9.0,
        "Detail Strength": 0.6, "Streaks": 0.75, "Streak Scale": 3.0, "Streak Length": 6.5, "Ledge Distance": 2.0, "Ledge Weight": 0.52,
        "Algae": 1.0, "Algae Z": WATER_Z, "Algae Height": 0.85, "Efflorescence": 1.15, "Damp Band": 1.25,
        "Macro": 0.55, "Macro Scale": 0.85, "Macro Streak": 2.10, "Macro Rough": 0.65, "Ledge Band": 1.22,
        "Streak Aspect": 5.5, "Run Coverage": 0.36,
        "Patches": 0.32, "Edge Wear": 0.65, "Edge Radius": 0.18, "Recess Dirt": 0.68, "Recess Distance": 0.6, "Cavity": 0.35,
        "Roughness": 0.8, "Roughness Variation": 0.12, "Bump": 0.4, "Pour Lines": 0.06, "Pour Spacing": 1.6},
        specular=0.18)
    # colonnade concrete: same ochre, the strongest black-green streaking, worse on the shade (north) side
    concrete_material("MAT_concrete_colonnade", "concrete_wall_007", 3.0, {
        "Base Color": C(0.752, 0.594, 0.105), "Grey Color": C(0.420, 0.372, 0.064), "Grey Drift": 0.10,
        "Grey Below Z": 1.0, "Grey Above Z": 4.0, "Tone Variation": 0.24, "Block Size": 3.0, "Blotch Size": 2.2,
        "Drift Size": 10.0,
        "Detail Strength": 0.80, "Streaks": 0.9, "Streak Scale": 3.4, "Streak Length": 7.5, "Ledge Distance": 2.5, "Ledge Weight": 0.50,
        "Streak Shade Bias": 0.6,
        "Algae": 1.0, "Algae Z": WATER_Z, "Algae Height": 0.80, "Damp Band": 1.0,
        "Macro": 0.45, "Macro Scale": 0.9, "Macro Streak": 2.45, "Macro Rough": 0.60, "Ledge Band": 1.30,
        "Streak Aspect": 6.0, "Run Coverage": 0.32,
        "Patches": 0.22, "Edge Wear": 0.34, "Edge Radius": 0.12, "Recess Dirt": 0.6, "Recess Distance": 0.7, "Cavity": 0.65,
        "Roughness": 0.78, "Roughness Variation": 0.12, "Bump": 0.35, "Pour Lines": 0.08, "Pour Spacing": 1.3},
        specular=0.09)
    # vault soffits, inner arch rings: greyer, dustier, soot on the undersides
    concrete_material("MAT_concrete_inner", "concrete_wall_008", 4.0, {
        "Base Color": C(0.475, 0.358, 0.034), "Grey Color": C(0.382, 0.318, 0.058), "Grey Drift": 0.34,
        "Grey Below Z": 40.0, "Grey Above Z": 60.0, "Tone Variation": 0.16, "Block Size": 3.0, "Blotch Size": 2.2,
        "Drift Size": 10.0,
        "Detail Strength": 0.6, "Streaks": 0.45, "Streak Scale": 3.0, "Streak Length": 6.0, "Ledge Distance": 2.0, "Ledge Weight": 0.55,
        "Algae": 1.0, "Algae Z": WATER_Z, "Algae Height": 0.55, "Damp Band": 0.8,
        "Macro": 0.65, "Macro Scale": 0.8, "Macro Streak": 0.95, "Macro Rough": 0.45, "Ledge Band": 0.95,
        "Streak Aspect": 4.0, "Run Coverage": 0.45,
        "Patches": 0.12, "Edge Wear": 0.60, "Edge Radius": 0.15, "Recess Dirt": 0.7, "Recess Distance": 0.7, "Cavity": 0.50, "Underside Dirt": 0.6,
        "Roughness": 0.85, "Roughness Variation": 0.1, "Bump": 0.35, "Pour Lines": 0.16, "Pour Spacing": 1.2})
    # ornament: capitals, maidens, urns, panels -- dust in the hollows, worn arrises, per-instance variation, baked-map hooks
    # Edge Radius stays small: a 0.12 m bevel would eat a 0.4 m capital volute. Instance Variation is now value +
    # weathering (see PFA_concrete `wvar`), not hue -- QA-02-2's yellow-vs-salmon capitals.
    concrete_material("MAT_ornament_concrete", "concrete_wall_008", 5.0, {
        # ROUND 9: this material, not MAT_concrete_ochre, is what covers QA's attic-panel box on the hero (ORN's
        # attic_panel assets sit on the ARCH field), so it carries the same photo-derived tint and the same
        # projection weight; without it the box QA scores would be the only part of the attic left uncorrected.
        "Albedo Tint": PHOTO_TINT, "Photo": PHOTO_WEIGHT,
        "Base Color": C(0.744, 0.586, 0.100), "Grey Color": C(0.450, 0.385, 0.062), "Grey Drift": 0.12,
        "Grey Below Z": 2.0, "Grey Above Z": 9.0, "Tone Variation": 0.20, "Block Size": 1.2, "Blotch Size": 0.8,
        "Drift Size": 3.5,
        "Detail Strength": 0.4, "Streaks": 0.55, "Streak Scale": 6.0, "Streak Length": 4.0, "Ledge Distance": 1.0, "Ledge Weight": 0.6,
        "Algae": 0.0,
        # QA-05-2 "the attic relief gone soft under it": the attic panels are ORN meshes on this material, so the
        # blotch was competing with the relief. Half the isotropic macro, and a longer recess probe (0.42 -> 0.52 m,
        # the depth of an attic panel's figure ground) so the relief's own verticals darken instead.
        # `Ledge Band` 0.90 -> 0.45: on the attic panels this material's under-ledge band is a HORIZONTAL line
        # inside QA's attic box (measured: the box's row-mean profile has a 60-lum step at its own panel frame),
        # i.e. it feeds the denominator of the anisotropy statistic. The run-off amplitude takes its place.
        "Macro": 0.45, "Macro Scale": 0.22, "Macro Streak": 2.20, "Macro Rough": 0.40, "Ledge Band": 0.45,
        "Streak Aspect": 6.0, "Run Coverage": 0.32, "Run Scale": 3.6,
        "Patches": 0.0, "Edge Wear": 0.45, "Edge Radius": 0.055, "Recess Dirt": 0.88, "Recess Distance": 0.52, "Cavity": 1.0,
        "Vertex Cavity": 0.85, "Vertex Dust": 0.55,
        "Roughness": 0.8, "Roughness Variation": 0.1, "Bump": 0.3, "Pour Lines": 0.0, "Bird Droppings": 0.12,
        "Instance Variation": 1.7}, specular=0.09, baked=True)
    # the 16 fluted pink shafts: dusty terracotta rose, integral pigment washing out to mauve-grey
    # QA-04-5: the hero column mask measured hue 31.2 (test 20-29), saturation 0.753 (ref 0.588) and lum 122
    # (test <= 120). Round 4 cut 37 % of the albedo and bought 3 % of display value, so this round moves CHROMA,
    # not level: blue goes 0.021 -> 0.056 (the shafts are integral-pigment concrete weathered toward mauve-grey, not
    # a saturated terracotta) and G/R drops 0.500 -> 0.472, which is the -6 deg of hue the mask is asking for. The
    # value falls only 6 %, so the remaining 1.27x brightness stays where round 4 put it: the entablature's shadow
    # (lighting). `Tone Variation` and the macro layer supply the "strong tonal variation" the sheet describes.
    concrete_material("MAT_column_rose", "concrete_wall_008", 6.0, {
        "Base Color": C(0.298, 0.1385, 0.079), "Grey Color": C(0.284, 0.175, 0.098), "Grey Drift": 0.26,
        "Grey Below Z": -100.0, "Grey Above Z": -99.0, "Tone Variation": 0.34, "Block Size": 3.2, "Blotch Size": 1.1,
        "Drift Size": 4.5,
        "Detail Strength": 0.70, "Streaks": 0.50, "Streak Scale": 4.0, "Streak Length": 8.0, "Ledge Distance": 1.5, "Ledge Weight": 0.4,
        "Algae": 0.0,
        "Macro": 0.70, "Macro Scale": 0.45, "Macro Streak": 0.90, "Macro Rough": 0.45, "Ledge Band": 0.80,
        "Streak Aspect": 6.0, "Run Coverage": 0.40,
        "Patches": 0.0, "Edge Wear": 0.85, "Edge Radius": 0.045,
        "Recess Dirt": 0.65, "Recess Distance": 0.30, "Cavity": 0.95, "Roughness": 0.72, "Roughness Variation": 0.1, "Bump": 0.3, "Pour Lines": 0.0},
        specular=0.20,
        column={"Wash Color": C(0.372, 0.246, 0.172), "Wash": 0.60, "Drum Height": 3.25, "Drum Variation": 0.13, "Top Z": 16.3, "Top Darkening": 0.40})
    # the 8 inner tan columns (and their blocks)
    concrete_material("MAT_column_tan_inner", "concrete_wall_008", 7.0, {
        "Base Color": C(0.565, 0.428, 0.032), "Grey Color": C(0.442, 0.360, 0.058), "Grey Drift": 0.16,
        "Grey Below Z": -100.0, "Grey Above Z": -99.0, "Tone Variation": 0.20, "Block Size": 3.0, "Blotch Size": 1.3,
        "Drift Size": 6.0,
        "Detail Strength": 0.6, "Streaks": 0.3, "Streak Scale": 5.0, "Streak Length": 8.0, "Ledge Distance": 1.5, "Ledge Weight": 0.4,
        "Algae": 0.0,
        "Macro": 0.55, "Macro Scale": 0.45, "Macro Streak": 0.60, "Macro Rough": 0.40, "Ledge Band": 0.75,
        "Streak Aspect": 6.0, "Run Coverage": 0.40,
        "Patches": 0.0, "Edge Wear": 0.80, "Edge Radius": 0.045,
        "Recess Dirt": 0.6, "Recess Distance": 0.30, "Cavity": 0.90, "Roughness": 0.78, "Roughness Variation": 0.1, "Bump": 0.3, "Pour Lines": 0.0},
        column={"Wash Color": C(0.420, 0.320, 0.150), "Wash": 0.38, "Drum Height": 3.0, "Drum Variation": 0.09, "Top Z": 11.0, "Top Darkening": 0.3})
    # platform floor / steps: light neutral concrete slabs with joints (the stair runs down to the water -> algae)
    concrete_material("MAT_paving", "concrete_wall_008", 8.0, {
        "Base Color": C(0.510, 0.500, 0.270), "Grey Color": C(0.378, 0.356, 0.228), "Grey Drift": 0.26,
        "Grey Below Z": -100.0, "Grey Above Z": -99.0, "Tone Variation": 0.14, "Block Size": 1.5, "Blotch Size": 4.0,
        "Drift Size": 8.0,
        "Detail Strength": 0.5, "Streaks": 0.0, "Patches": 0.24, "Edge Wear": 0.4, "Edge Radius": 0.06,
        "Macro": 0.80, "Macro Scale": 0.8, "Macro Rough": 0.50,
        "Algae": 1.0, "Algae Z": WATER_Z, "Algae Height": 0.60, "Damp Band": 1.15,
        "Recess Dirt": 0.5, "Recess Distance": 0.45, "Cavity": 0.30, "Roughness": 0.7, "Roughness Variation": 0.12, "Bump": 0.3, "Pour Lines": 0.0,
        "Grid Joints": 0.8, "Grid Size": 1.5}, specular=0.34)
    # ENVIRONMENT hand-off (round 7, docs/status.md "ENV r7 reported"): the colonnade walk is 16.7 % of cam03's
    # lower frame and was falling back to gravel/soil because these two names did not exist in the library.
    # ref 128 / ref 169: the walk is laid in large pale grey-buff slabs, ~1.2 m, with open dark joints, a cooler and
    # much less yellow stone than the building, and it darkens where it runs down to the water (QA-05-11 also wants
    # ground std >= 12, which is what the joints plus the slab-to-slab tone step give).
    concrete_material("MAT_paving_stone", "concrete_wall_007", 20.0, {
        "Base Color": C(0.560, 0.535, 0.375), "Grey Color": C(0.415, 0.400, 0.310), "Grey Drift": 0.30,
        "Grey Below Z": -100.0, "Grey Above Z": -99.0, "Tone Variation": 0.20, "Block Size": 1.2, "Blotch Size": 3.0,
        "Drift Size": 7.0,
        "Detail Strength": 0.55, "Streaks": 0.0, "Patches": 0.20, "Edge Wear": 0.45, "Edge Radius": 0.05,
        "Macro": 0.70, "Macro Scale": 0.7, "Macro Rough": 0.50,
        "Algae": 1.0, "Algae Z": WATER_Z, "Algae Height": 0.55, "Damp Band": 1.30,
        "Recess Dirt": 0.55, "Recess Distance": 0.40, "Cavity": 0.30,
        "Roughness": 0.74, "Roughness Variation": 0.13, "Bump": 0.35, "Pour Lines": 0.0,
        "Grid Joints": 0.90, "Grid Size": 1.20}, specular=0.32)
    # the worn / patched half of the same walk: darker, greyer, more repair patches and a heavier damp zone, so ENV
    # can break the walk up instead of tiling one slab tone over 16 % of the frame.
    concrete_material("MAT_paving_stone_worn", "concrete_wall_008", 21.0, {
        "Base Color": C(0.468, 0.448, 0.322), "Grey Color": C(0.360, 0.348, 0.280), "Grey Drift": 0.42,
        "Grey Below Z": -100.0, "Grey Above Z": -99.0, "Tone Variation": 0.26, "Block Size": 0.9, "Blotch Size": 2.0,
        "Drift Size": 5.0,
        "Detail Strength": 0.65, "Streaks": 0.0, "Patches": 0.38, "Edge Wear": 0.55, "Edge Radius": 0.06,
        "Macro": 0.95, "Macro Scale": 0.55, "Macro Rough": 0.60,
        "Algae": 1.0, "Algae Z": WATER_Z, "Algae Height": 0.70, "Damp Band": 1.45, "Efflorescence": 0.9,
        "Recess Dirt": 0.68, "Recess Distance": 0.40, "Cavity": 0.40,
        "Roughness": 0.80, "Roughness Variation": 0.14, "Bump": 0.42, "Pour Lines": 0.0,
        "Grid Joints": 1.00, "Grid Size": 0.95}, specular=0.28)
    # coffered plaster saucer -- the PANEL FIELDS only. ARCH assigns MAT_plaster_ceiling_rib to the rib plate from
    # round 6, so the two are separable at last (round 5 measured that nothing inside a single shared material can
    # tell them apart: the rib plate hangs 0.55 m below the field on the same sphere, so ribs and panels are
    # parallel down-facing planes with the same normal and the same AO openness).
    concrete_material("MAT_plaster_ceiling", "concrete_wall_008", 9.0, {
        # QA-06-8 (round 8): coffer field sat 0.914 Cycles / 0.966 Eevee against ref 083's 0.427 -- a saturated
        # orange saucer, "lit right and coloured wrong".  Round 6's albedo was an ochre at HSV saturation 0.773
        # (B only 0.23 of R); ref 083's plaster is a warm CREAM.  Both colours drop to HSV saturation 0.40 at the
        # same hue (46.2 deg field / 41.9 deg grey) and are then scaled to hold their luminance, so the coffer /
        # sky luminance ratio QA asks to hold at 0.35-0.55 is untouched and only the chroma moves.  MEASURED at
        # albedo saturation 0.40: rendered coffer sat 0.966 -> 0.614 (Eevee cam04), i.e. 0.94 rendered points per
        # albedo point, not the 1.28 the two round-6 materials suggested -- so the albedo goes to 0.25 to land the
        # rendered field near ref 083's 0.427.  Ratio held at 0.355 against round 6's 0.346.
        # QA-09-8 (round 10).  QA scored 0.341 on the round-09 frame; re-measured on THIS master (LIGHT r17, the
        # shade fill off) by `mat_r9_measure.py coffer` the field is 0.310 at lum 106.9 -- the saucer lost 30 lum
        # with the fill, so the whole operating point moved and the round-9 gain no longer applies as quoted.
        # The gain at albedo 0.25 was ~1.09 rendered points per albedo point in Cycles at display 137 (from
        # albedo 0.40 -> Eevee 0.614, 0.25 -> Eevee 0.415, Cycles/Eevee 0.822); AgX's chroma transfer at display
        # 107 is ~1.35x the one at 137, so the local gain here is 1.1-1.6.  Albedo saturation 0.250 -> 0.345 is
        # +0.095, i.e. +0.105 to +0.152 rendered, landing 0.415-0.462 inside the 0.38-0.50 window next to ref
        # 083's 0.427.  HUE (46.45 / 41.65 deg) and Rec.709 luminance (0.46606 / 0.316268) are held to 5
        # decimals, which is what holds the coffer/sky luminance ratio lighting measured at 0.347.
        "Base Color": C(0.506932, 0.467441, 0.332040), "Grey Color": C(0.351557, 0.314453, 0.230270), "Grey Drift": 0.16,
        "Grey Below Z": -100.0, "Grey Above Z": -99.0, "Tone Variation": 0.20, "Block Size": 1.5, "Blotch Size": 1.0,
        "Drift Size": 5.0, "Algae": 0.0,
        # QA-04-7 "no dirt gradient inside any coffer": now that the ribs carry their own material, a LONG AO probe
        # on the panel material IS the in-coffer gradient -- it sees the rib plate below and the coffer returns
        # around, so it darkens each panel toward its own frame and leaves the middle of the field clean. Round 5's
        # experiment that "dirtied the whole saucer" failed only because the ribs shared this material. `Rib Grime`
        # drops to a token 0.30: it reaches the 1-2 px coffer returns, which do belong to the panel object.
        "Detail Strength": 0.3, "Streaks": 0.0, "Patches": 0.0, "Edge Wear": 0.3, "Edge Radius": 0.05,
        "Macro": 0.85, "Macro Scale": 0.32, "Macro Rough": 0.35,
        "Recess Dirt": 0.74, "Recess Distance": 1.05, "Cavity": 0.70, "Rib Grime": 0.30, "Roughness": 0.9,
        "Roughness Variation": 0.05, "Bump": 0.25, "Pour Lines": 0.0}, specular=0.24)
    # the coffer RIB plate (ARCH round 6: saucer-dome and barrel-vault rib faces). Ref 083 / coffered_ceiling_1: the
    # panel fields are the palest surface in the rotunda at L 93-130 and the rib bands read L 22-50, i.e. the ribs
    # sit near 0.35 of the panels and are distinctly cooler -- they are in their own shadow all day and carry the
    # guilloche / bead-and-reel mouldings that hold a century of dust. Base Color is 0.37-0.40 of the panel's with
    # red pulled down harder than green (cooler), plus heavy recess dirt and cavity so the mouldings separate.
    concrete_material("MAT_plaster_ceiling_rib", "concrete_wall_007", 19.0, {
        # QA-06-8: the rib band measured sat 0.782 Cycles / 0.922 Eevee against the same 0.427.  Same treatment as
        # the panel field above -- HSV saturation 0.670 -> 0.25 at hue 49.0, luminance held.
        # QA-07-9 (round 9): the round-8 correction overshot on the RIB only -- Cycles rim sat 0.323 against the
        # 0.38-0.50 window while the field landed at 0.467 on the same albedo saturation (0.25).  Round 8's own
        # measured gain for the field was 0.94 rendered points per albedo point; the rib renders at 1.29 albedo
        # points per rendered point, so 0.25 -> 0.34 puts it at ~0.44, mid-window, next to ref 083's 0.438.  Hue
        # (48.8 / 49.2 deg) and Rec.709 luminance (0.1831 / 0.1472) are held to 4 decimals by construction.
        # QA-09-8 (round 10): the round-9 move overshot -- QA scored the rim 0.634, and on THIS master it is
        # 0.600 at lum 27.9, still far outside the 0.38-0.50 window.  Round 9 measured the rim's own gain
        # directly (albedo 0.25 -> 0.34 moved Cycles rim 0.323 -> 0.625, i.e. 3.36 rendered points per albedo
        # point -- steep because the dark quarter sits where AgX's chroma transfer is steepest), so albedo
        # saturation 0.340 -> 0.292 is -0.048 and lands 0.398-0.475 for any gain between 2.6 and 4.2, i.e. the
        # window is held even if the gain moved with the light as the field's did.  Hue (48.79 / 49.18 deg) and
        # Rec.709 luminance (0.183130 / 0.147178) held to 6 decimals, so the dark/light ratio (0.261 here
        # against ref 083's 0.265) and the coffer/sky ratio do not move.
        "Base Color": C(0.194840, 0.184207, 0.137947), "Grey Color": C(0.156364, 0.148135, 0.110706), "Grey Drift": 0.30,
        "Grey Below Z": -100.0, "Grey Above Z": -99.0, "Tone Variation": 0.24, "Block Size": 1.2, "Blotch Size": 0.7,
        "Drift Size": 3.0, "Algae": 0.0,
        "Detail Strength": 0.45, "Streaks": 0.0, "Patches": 0.0, "Edge Wear": 0.55, "Edge Radius": 0.035,
        "Macro": 0.90, "Macro Scale": 0.22, "Macro Rough": 0.40,
        "Recess Dirt": 0.85, "Recess Distance": 0.35, "Cavity": 0.95, "Underside Dirt": 0.35,
        "Roughness": 0.92, "Roughness Variation": 0.06, "Bump": 0.30, "Pour Lines": 0.0}, specular=0.18)
    # bronze-brown guilloche band on the drum
    concrete_material("MAT_drum_band", "concrete_wall_007", 10.0, {
        "Albedo Tint": PHOTO_TINT, "Photo": PHOTO_WEIGHT,        # round 9: inside the projected band
        "Base Color": C(0.285, 0.228, 0.038), "Grey Color": C(0.222, 0.188, 0.060), "Grey Drift": 0.3,
        "Grey Below Z": -100.0, "Grey Above Z": -99.0, "Tone Variation": 0.15, "Block Size": 1.0, "Blotch Size": 1.0,
        "Drift Size": 2.5, "Algae": 0.0,
        "Detail Strength": 0.4, "Streaks": 0.35, "Streak Scale": 10.0, "Streak Length": 3.0, "Ledge Weight": 0.5,
        "Macro": 0.45, "Macro Scale": 0.30, "Macro Streak": 0.55, "Macro Rough": 0.35, "Streak Aspect": 4.0,
        "Patches": 0.0, "Edge Wear": 0.5, "Edge Radius": 0.03, "Recess Dirt": 0.7, "Recess Distance": 0.25, "Cavity": 0.60,
        "Roughness": 0.8, "Roughness Variation": 0.1, "Bump": 0.3, "Pour Lines": 0.0})
    # exhibition hall / distant massing: buff stucco, coarse
    concrete_material("MAT_backdrop_building", "concrete_wall_008", 11.0, {
        "Base Color": C(0.568, 0.545, 0.120), "Grey Color": C(0.425, 0.382, 0.148), "Grey Drift": 0.30,
        "Grey Below Z": 1.0, "Grey Above Z": 6.0, "Tone Variation": 0.24, "Block Size": 3.0, "Blotch Size": 3.2,
        "Drift Size": 11.0, "Algae": 0.0,
        "Detail Strength": 0.7, "Streaks": 0.8, "Streak Scale": 5.0, "Streak Length": 8.0,
        "Ledge Distance": 3.5, "Ledge Weight": 0.55,
        "Macro": 0.85, "Macro Scale": 1.3, "Macro Streak": 1.15, "Macro Rough": 0.50, "Ledge Band": 0.95,
        "Streak Aspect": 4.0, "Run Coverage": 0.45,
        "Patches": 0.22, "Edge Wear": 0.3, "Edge Radius": 0.08, "Recess Dirt": 0.65, "Recess Distance": 0.9,
        "Roughness": 0.85, "Roughness Variation": 0.12, "Bump": 0.5, "Pour Lines": 0.0})


def build_dome():
    m = ML.new_material("MAT_dome_membrane")
    t = Tree(m.node_tree)
    N = t.geometry().outputs["Normal"]
    # Round 10 / QA-10-8.  Base Color is unchanged: measured on the round-10b hero, the rows of the cap the old
    # grime ring did NOT reach already rendered at 228 lum / hue 43.8 / sat 0.208 against ref 169's 226-241 /
    # 42-50 / 0.22-0.30 on the same rows -- the albedo was never the fault, its placement was.  What changes is
    # `Base Normal Z` 0.66 -> 0.52 (the cap's true rim normal), `Grime` 0.8 -> 0.55, `Moss` 0.3 -> 0.12 (ref 169
    # is the post-recoat dome and has none), the 28-panel ridge structure, and a streak width the hero resolves.
    # The streak colour is lightened and desaturated to 0.712 of the base's Rec.709 luminance at HSV saturation
    # 0.40 (was 0.606 at 0.531): the streaks in reference/photos/material_crops/dome_2.jpg are a grey-green wash,
    # not a brown one, and they have to pull the box's saturation DOWN toward ref 169's 0.272.
    g = t.group(G["dome"], Normal=N, **{"Base Color": C(0.952, 0.995, 0.352), "Streak Color": C(0.700, 0.685, 0.420), "Moss Color": C(0.34, 0.42, 0.28),
                                        "Grime Color": C(0.20, 0.13, 0.06), "Panels": 28.0, "Ridge Width": 0.30, "Ridge Dark": 0.30,
                                        "Panel Tone": 0.22, "Ring Spacing": 2.6, "Ring": 0.08, "Streaks": 0.75, "Streak Width": 1.4,
                                        "Moss": 0.12, "Grime": 0.55, "Base Normal Z": 0.52, "Roughness": 0.42, "Bump": 0.35, "Seed": 12.0})
    bsdf = t.principled(**{"Base Color": g.outputs["Color"], "Roughness": g.outputs["Roughness"], "Normal": g.outputs["Normal"],
                           "Specular IOR Level": 0.26, "Coat Weight": t.mul(g.outputs["Coat"], 0.18), "Coat Roughness": 0.30, "Coat Normal": g.outputs["Normal"]})
    t.output(surface=bsdf.outputs[0])
    return ML.finish(m)


def build_water():
    m = ML.new_material("MAT_water_lagoon")
    t = Tree(m.node_tree)
    W = t.geometry().outputs["Position"]
    N = t.geometry().outputs["Normal"]
    time = t.value(0.0, "WATER_TIME")          # driver: frame-based drift (see below)
    wx, wy, wz = t.sepxyz(W)
    # Distance filtering (Toksvig): a 0.3 m ripple is far smaller than a pixel at 150 m, so past ~45 m its slope must
    # move out of the normal and into the roughness. Without this the far water tips every grazing reflection ray away
    # from the sunlit building and the lagoon reads brown-black (QA-01-3).
    cam = t.new("ShaderNodeCameraData")
    depth = cam.outputs["View Z Depth"]
    # ROUND 7 (QA-05-4 "a flat blue-grey plane with uniform fine ripple noise"): the round-6 LOD ramp took the
    # ripple slope out of the normal from 30 m, so the whole 40-90 m band that carries the building's reflection
    # was glassy and the reflection came back as long vertical smears. ref 169's crop at the same distance is
    # corrugated by 0.25-0.4 m ripples right up to the far shore, and it is that corrugation that chops the ochre
    # into the warm horizontal flecks QA measures with R-B. The ramp starts at 55 m instead.
    ripple_lod = t.maprange(depth, 55.0, 240.0, 1.0, 0.18)
    far_rough = t.maprange(depth, 45.0, 200.0, 0.0, 0.030)
    # QA-03-7: within ~40 m of the camera the reflection held together in streaks tens of px long where the photo
    # breaks up at ~10-15. `near` drives the capillary detail, the bump strength and a little extra roughness in
    # exactly that band; past 70 m nothing changes, so the flank luminance QA-02-6 closed is untouched.
    # Round 6 (QA-04-8): the reflection of the sunlit stone measured sat 0.146 against ref 169's 0.339 -- grey,
    # because at 20-45 m the chop was smearing the ochre column together with the sky above it until the two
    # averaged out. The near band is pulled in from 70 m to 45 m (and its chop layer weakened), so the mid-distance
    # reflection holds its colour while the last 20 m in front of the camera keep the break-up QA-03-7 bought.
    near = t.maprange(depth, 95.0, 9.0, 0.0, 1.0)
    # anisotropy: crests run longer along X (across the hero view), so the reflection breaks into vertical streaks.
    # v3 used 0.33 (3x elongation), which is what made the near-field runs so long; 0.5 keeps the character.
    Pa = t.combxyz(t.mul(wx, 0.36), wy, 0.0)
    Ps = t.combxyz(t.mul(wx, 0.55), wy, 0.0)
    h1 = t.noise(Pa, 3.3, detail=3, rough=0.55, w=t.mul(time, 1.0))          # 0.3 m ripples
    h2 = t.noise(Ps, 0.33, detail=2, rough=0.5, w=t.mul(time, 0.3))          # 3 m swell
    h3 = t.noise(Pa, 9.0, detail=2, rough=0.5, w=t.mul(time, 1.7))           # 0.1 m capillary
    h4 = t.noise(Pa, 24.0, detail=2, rough=0.5, w=t.mul(time, 2.4))          # 0.04 m near-field chop
    h = t.add(t.add(t.mul(h1, 0.6), h2), t.add(t.mul(h3, t.madd(near, 0.28, 0.18)), t.mul(h4, t.mul(near, 0.13))))
    # calmer patches (wind shadow) so the reflection is glassy in places
    # ROUND 8 tried dropping the calm floor 0.45 -> 0.20, on the argument that the slope sweep flattened the
    # water's spatial contrast as it warmed it (box std 52.0 -> 25.5 -> 18.4 from dist 0.03 to 0.22) while ref
    # 169's reflection is bright streaks on dark water.  MEASURED on the acceptance frame, a deeper wind-shadow
    # floor leaves ~half the box near-glassy and each glassy patch returns the FLAT mirror, which points at the
    # willow and the arch: R-B +38.7 -> +22.9 for +7 of luminance.  Same bad trade as the murk, same reason, so
    # the floor stays at round 7's 0.45.  The streak contrast has to come from the slope's own distribution.
    calm = t.maprange(t.noise(t.combxyz(wx, wy, 0.0), 0.04, detail=2), 0.35, 0.65, 0.45, 1.0)
    chop = t.value(1.6, "WATER_CHOP")      # swept by scripts/mat_r7_sweep.py; 1.0 -> 1.6 measured in the sweep
    # ROUND 8 (QA-06-3, the blocker).  The Bump node's Strength only BLENDS between N and the bumped normal, so it
    # saturates at 1.0 and the shipped chop already puts it at ~0.94; the ripple SLOPE is set by Distance, which is
    # why four rounds of chop sweeps never moved the reflection.  `scripts/mat_r8_probe.py` casts the hero's mirror
    # rays from the reflection box (23.4 m out, 82.7 deg incidence) and shows what the slope has to buy: on flat
    # water the mirror ray leaves at +7.3 deg elevation and lands on a shore willow, on the backdrop hall seen
    # THROUGH the rotunda arch, and on sky (SKY 25 % / ENV 62 % / ARCH 12 %, only 7.5 % of it sunlit).  The sunlit
    # stone sits at +17 to +23 deg of ray elevation, i.e. behind a facet pitch of +5 to +8 deg (ARCH 97-100 %,
    # sunlit 30 % then 75 %, mean hit height 21-23 m).  A ripple slope that reaches that far up returns bright warm
    # streaks from the upper rotunda between dark troughs pointing at the trees -- which is ref 169's water exactly.
    # `WATER_BUMP_DIST` is that slope, swept by scripts/mat_r8_sweep.py.
    # The sweep (mat_r8_sweep.py, 4 cases, Cycles 64 spp, box 900 760 1020 840) is monotone in the slope and
    # confirms the probe exactly -- dist 0.030 / 0.070 / 0.130 / 0.220 gives R-B +8.0 / +19.2 / +38.7 / +49.7 and
    # hue 54.5 / 39.8 / 36.1 / 35.2 against ref 169's +69.0 / 33.7, i.e. the reflection acquires the stone's colour
    # for the first time in five rounds.  It costs luminance (131.0 -> 114.4 -> 105.0 -> 99.4 against the 124-208
    # window), because a facet pitched +8 deg drops the local incidence from 82.7 to 74.7 deg and with it the
    # Fresnel from 0.46 to 0.33, and because the troughs then point down at dark water.  The same sweep makes the
    # NEAR field worse on every count (sat 0.304 -> 0.519 against the 0.22-0.32 window, ripples R-B -48 -> -74),
    # because at 9.4 m the flat mirror already looks 18 deg up and extra slope only sends it deeper into the blue
    # zenith.  The two ends of the lagoon therefore want opposite slopes, so the slope is RAMPED BY DEPTH: the
    # near field keeps round 7's calibration untouched and the 24 m+ band that carries the reflection gets the
    # slope that aims it at the stone.
    bumpdist = t.maprange(depth, 14.0, 24.0, 0.030, 0.170, name="WATER_BUMP_DIST")
    normal = t.bump(h, strength=t.mul(t.mul(t.mul(t.madd(near, 0.14, 0.45), calm), ripple_lod), chop),
                    distance=bumpdist, normal=N)
    rough = t.add(t.maprange(t.noise(t.combxyz(wx, wy, 0.0), 0.12, detail=2), 0.3, 0.7, 0.02, 0.055), far_rough)
    # green murk body. Transmission 0.55 (not 1.0) so the material reads the same on ENV's single water plane as it
    # does inside a closed lagoon volume: the opaque 45 % is a green murk lambertian that picks up sky and sun, the
    # transmissive 55 % carries the volume when there is one. Fresnel reflection is on top of both.
    # QA-02-6: the flanking water measured lum 34.9 against ref 169's 134.5 (3.9x dark) and the near field was an
    # over-saturated cyan (sat 0.678 vs 0.426). Both come from the same place: 45 % of the surface was transmitting
    # into a dense absorbing volume (a light sink), so the only bright thing left in the lagoon was the specular
    # sky/building mirror -- a dark body with a blue mirror on it. The murk is now brighter and closer to neutral
    # green-grey and carries more of the surface, which lifts the flanks and desaturates the near field at once.
    murk_far = t.maprange(t.noise(t.combxyz(wx, wy, 0.0), 0.05, detail=2), 0.35, 0.65, 0.0, 1.0)
    # QA-03-7: near-water sat 0.382 hue 206 vs ref 0.269 hue 192 -- the near field was almost pure sky mirror.
    # The near murk goes greener (G above both R and B) so it pulls the mix off the sky hue and desaturates it.
    # Round 6 (QA-04-8): the sky-reflecting near water measured hue 208.7 against ref 169's 189.9-192.1 -- blue,
    # where the lagoon is teal. Lighting has already shown the sky's own hue is exact, so the missing green is the
    # water's, and there are only two places it can come from at a grazing angle.
    #  (1) the upwelling murk. The near murk goes properly green (G well above R and B) instead of the near-neutral
    #      green-grey of round 3; it carries the ~15-25 % of the pixel that is not Fresnel.
    #  (2) SHEEN. Round 4 measured that `Specular Tint` cannot do this -- Blender tints F0 only, and this crop is
    #      all F90 -- but the Principled's sheen lobe is grazing-weighted by construction, which is exactly the
    #      angular dependence a scum / biofilm film has. A teal sheen therefore lands on the near, grazing water and
    #      leaves the facing water (and the building's reflection, which is not a sheen direction) alone.
    # Measured (r6a): pushing the near murk hard green moved the near-water hue only 204.8 -> 202.6 but took the
    # sunlit-stone reflection from hue 43.8 / sat 0.143 to 66.5 / 0.122 -- the murk sits under the whole lagoon, so
    # it greys the reflection at the same time. The green therefore rides the SHEEN alone, which is grazing-weighted
    # and on a much tighter depth ramp (22 -> 5 m) than the chop's `near`, so it lands on the bottom-of-frame water
    # QA measures for hue and nowhere near the reflection column at 40-90 m.
    # Round 6 review: the sheen SHIPS AT ZERO. Measured on the hero it bought 1.0 deg of near-water hue
    # (204.8 -> 203.8, still far outside the 185-200 window) and moved the sunlit-stone reflection further from
    # ref 169 on both axes (hue 43.8 -> 48.9 against 33.6, sat 0.143 -> 0.130 against 0.363); pushed to weight 1.0
    # over a 70 m ramp it took the reflection to hue 134, green. It is left wired, at 0, as the record of the
    # third measured lever: see the QA-04-8 table in docs/materials_notes.md. What is kept from round 6 is the
    # near-neutral murk (the r6a green murk greyed the reflection) and the 62 m chop band.
    # ROUND 7. Lighting r12 hand-off 1: its diffuse-sky boost is invisible to camera and glossy rays by
    # construction, so the water's MIRROR is untouched and the whole of near-water sat 0.281 -> 0.418 (window
    # 0.22-0.32) and hue 208.9 -> 218.1 is this diffuse murk taking sky light like any up-facing surface. The murk
    # therefore loses a third of its chroma, warms (blue down hardest, so its product with a blue sky lands nearer
    # teal than periwinkle) and drops 12 % of its value -- which the lagoon flank can afford, measured at 174.1
    # against ref 169's 155.2. Transmission ships at 0.18 (sweep case w1: 0.40 -> 0.18 bought +0.045 of reflection
    # saturation), which moves that share of the surface off the diffuse lobe and is what lets the building's
    # reflection (QA-05-4, R-B -39 where the photo is +71) carry the stone's colour again instead of a blue-grey
    # wash over it.
    # ROUND 8: the murk goes from a near-neutral green-grey (HSV saturation 0.19) to the shallow lagoon's actual
    # silty green (0.40), and up ~20 % in value.  It is the substrate under the Fresnel mirror, so its colour is
    # what the 54 % of the reflection box that is NOT mirror returns; a neutral murk under lighting's blue sky
    # returns blue and fights the warm streaks, a green-ochre one returns near-neutral (albedo R/B 1.63 against
    # the sky's E_B/E_R ~1.4) and adds luminance without taking R-B back.
    murk = t.mix(murk_far, C(0.155, 0.160, 0.095), C(0.175, 0.180, 0.110))
    murk.node.name = murk.node.label = "WATER_MURK"        # addressed by scripts/mat_r7_sweep.py
    # ROUND 7, and this is the measured answer to lighting r12's hand-off 1 (which asked for a third of the murk's
    # CHROMA). The round-7 sweep (mat_r7_sweep.py, 9 cases on one master, docs/materials_notes.md) scaled the murk
    # albedo instead: at gain 1.00 near-water sat 0.390 / hue 218.6 and the ripples' R-B -64; at gain 0.00 (a pure
    # Fresnel mirror) 0.276 / 209.6 and -29.7, against QA's 0.22-0.32 / 185-200 and ref 169's -16 to -26. So the
    # whole of the defect is the murk's PRESENCE under a boosted diffuse sky, not its hue -- and it is linear in the
    # gain, which is what lets it be set rather than guessed.
    # It cannot simply be turned down, because the same lambertian is what keeps the lagoon from reading black from
    # above (QA-02-6, round 2). The physical form of the fix is a Fresnel weight: real turbid water returns its
    # sub-surface light through the surface twice, so the diffuse term falls off at grazing incidence far faster
    # than Blender's single-sided Fresnel makes it. The Fresnel weight `0.15 + 0.85 (1 - F)^2` alone keeps ~0.36 of
    # the murk at the hero's 75-85 deg grazing water and ~0.76 at cam06's ~30 deg; the SHIPPED gain multiplying it
    # is 0.15, so the murk actually reaching those two places is ~0.054 and ~0.114 of round 6's -- the wash comes
    # off the crop QA measures and the aerial lagoon is dimmed, not left alone.  Measured 2026-09-09 on cam06 at
    # 1280x720 (scripts/mat_r7fix_cam06.py): Cycles open-water box (60 380 340 500) lum 115.6 at gain 1.00 ->
    # **94.3** at the shipped 0.15 (0.82x); Eevee is bit-identical between the two gains because the Eevee branch
    # below is fed by WATER_MURK_EEVEE, which this gain does not touch.
    _fr = t.new("ShaderNodeFresnel")
    t.plug(_fr.inputs["IOR"], 1.333); t.plug(_fr.inputs["Normal"], normal)
    _fw = t.sub(1.0, _fr.outputs[0])
    murk_w = t.madd(t.mul(_fw, _fw), 0.85, 0.15)
    # ROUND 8.  Round 7's flat 0.15 was calibrated on ONE crop -- QA-05-4's near-water box at 9 m -- and then
    # applied to the whole lagoon, which is what left the reflection column's substrate at an effective albedo of
    # 0.0125 (black) and cost cam06's open water 115.6 -> 94.3 lum.  The angular part of that suppression is
    # already carried physically by the Fresnel weight above, so the gain only has to protect the near crop: it is
    # now ramped by depth instead.  MEASURED, and this is why the ramp is where it is: a first shipped attempt put
    # it at 14 -> 24 m, which set the gain to 0.95 inside the hero's reflection box (mean 23.4 m) and cost the box
    # 23.9 of R-B (+38.7 in the sweep -> +14.8 on the acceptance frame) to buy 12.5 of luminance -- 1.9 points of
    # warmth per point of light, because the murk is a lambertian under lighting's blue sky and returns blue.  The
    # box therefore keeps round 7's 0.15 exactly, and the ramp is pushed out to the 30-90 m band that only cam05's
    # lagoon and cam06's aerial see, where the water is far from grazing, no reflection test is scored on it, and
    # the murk is the whole reason QA-02-6's lagoon does not read black.
    murk = t.vscale(murk, t.mul(murk_w, t.maprange(depth, 30.0, 90.0, 0.15, 1.00, name="WATER_MURK_GAIN")))
    bsdf = t.principled(**{"Base Color": murk, "Roughness": rough, "IOR": 1.333, "Transmission Weight": 0.18,
                           "Specular IOR Level": 0.5, "Normal": normal,
                           "Sheen Weight": 0.0, "Sheen Roughness": 0.35,
                           "Sheen Tint": C(0.22, 0.62, 0.46)})
    # ROUND 9 (QA-07-1 hue + QA-07-3 level), and it is one lobe for both because both are properties of the same
    # thing: the grazing MIRROR.  Arithmetic first, because three previous rounds spent their budget on the body
    # colour and the body colour is not what is being measured.  At 9.4 m the near-water pixel is ~95 % Fresnel
    # mirror (murk_w ~0.36 x gain 0.15 = 0.054 of the surface), so its hue IS the sky's hue and the murk can move
    # it by ~1 deg -- measured twice, round 6 (sheen, 1.0 deg) and round 7 (murk gain, 209.6 -> 218.6 the WRONG
    # way, because the murk is a lambertian under a blue sky).  ref 169's lagoon is 18 deg greener than the sky it
    # mirrors, which physically is upwelling green returned THROUGH the surface, i.e. a tint on the reflected
    # radiance.  Blender's `Specular Tint` cannot do it (F0 only; this crop is all F90), so the mirror is tinted
    # by mixing in a Glossy lobe with the SAME roughness and normal, weighted by the SAME Fresnel the Principled
    # uses: at grazing the surface becomes the tinted mirror, at facing angles it is the Principled untouched.
    # Solved from the measured pixel: near water (r 91.4, g 110.6, b 129.1) needs blue down ~12 % to move hue
    # 209.4 -> ~195 at lum 105 (ref 105.4); the same tint takes the reflection box's R-B from +39.8 to +48.9 at
    # hue 39.9, both inside their windows.  The Fresnel mix ALSO raises the mirror's share in the reflection box
    # (0.46 -> 0.71 at 82.7 deg incidence), which is the luminance QA-07-3 asks for.  `WATER_GLOSS_MIX` = 0 is
    # bit-identical to round 8; it is swept by scripts/mat_r9_sweep.py.
    gloss_tint = t.rgb(C(1.00, 0.985, 0.875), "WATER_GLOSS_TINT")
    # SWEPT (scripts/mat_r9_sweep.py, 4 cases, Cycles 64 spp, hero border rows 740-1080 = 31 % of a frame):
    #   mix       0.00     0.45     0.75     1.00        ref 169        window
    #   refl lum  102.1    116.3    124.3    130.3       164.6          124-208
    #   refl R-B  +40.7    +45.8    +47.8    +49.0       +71.7          >= +35
    #   near lum  107.9    125.2    134.1    140.3       105.4          79-131
    #   near sat  0.288    0.200    0.160    0.134       0.246          0.22-0.32
    #   near hue  209.2    208.0    207.0    206.0       189.8          185-200
    #   ripp R-B  -31.2    -22.5    -17.8    -14.5       -16.4          -26 +- 10
    #   flank lum 145.2    162.7    171.5    177.7       152.4          114-190
    # Two things are settled by that table.  (1) The mirror is a LEVEL lever, not a hue one: 12.5 % of blue taken
    # out of the whole reflected radiance moves the near water 3.2 deg, so the 19 deg QA-07-1 asks for would need
    # the mirror ~50 % green and the reflection column would leave its hue window long before the lagoon reached
    # 200.  With round 6's sheen (1.0 deg) and round 7's murk gain (which moves it the WRONG way, 209.6 -> 218.6)
    # that is the third measured lever, and the near-water hue is hereby reported as NOT reachable from this
    # material -- it is the hue of the sky this water mirrors.  (2) Everything the extra mirror buys the
    # reflection column it also spends on the open lagoon, which is already at or above reference.  0.25 is the
    # largest setting at which nothing that passes today stops passing: near sat ~0.24, near lum ~118, flank ~155
    # against ref 152.4, cam05's band inside its 117 ceiling, and the reflection column 102.1 -> ~110 with the
    # ripples' R-B error halved.  Raising it to 0.75 CLOSES QA-07-3 (refl 124.3) and is one number away.
    # ROUND 9b: the lead took the middle of that sweep -- 0.25 -> 0.45.  It is the lead's call on the mirror, made
    # against the swept table above: reflection lum 116.3 (still under the 124 window, but 0.61 of the sunlit attic
    # against the photograph's 0.88, where 0.25 gave 0.58), near water 125.2 / sat 0.200 (the sat window 0.22-0.32
    # is the one thing this costs, and the near-water hue is already reported unreachable from this material), and
    # cam05's band still under its 117 ceiling.  Measured on the round-9b acceptance frame, not re-swept.
    gloss_mix = t.value(0.45, "WATER_GLOSS_MIX")
    gl2 = t.new("ShaderNodeBsdfGlossy")
    t.plug(gl2.inputs["Color"], gloss_tint); t.plug(gl2.inputs["Roughness"], rough)
    t.plug(gl2.inputs["Normal"], normal)
    mixsh = t.new("ShaderNodeMixShader")
    t.link(t.mul(_fr.outputs[0], gloss_mix), mixsh.inputs[0])
    t.link(bsdf.outputs[0], mixsh.inputs[1])
    t.link(gl2.outputs[0], mixsh.inputs[2])
    # one Principled Volume (absorption + weak scatter): Absorption + Scatter + Add Shader pushed Cycles past its
    # 64-closure budget (76) and closures were silently dropped. extinction = density * (color + 1 - absorption_color):
    # scatter (0.117, 0.234, 0.144)/m, absorption (0.36, 0.135, 0.36)/m -> single-scatter albedo 0.25/0.63/0.29, i.e. a
    # LIT green murk (the v1 numbers gave albedo 0.07-0.15, which made a closed lagoon volume read black).
    vol = t.new("ShaderNodeVolumePrincipled")
    vol.name = vol.label = "WATER_VOLUME"
    t.plug(vol.inputs["Color"], C(0.205, 0.250, 0.195)); t.plug(vol.inputs["Density"], 0.7)
    t.plug(vol.inputs["Absorption Color"], C(0.70, 0.80, 0.68)); t.plug(vol.inputs["Anisotropy"], 0.3)
    t.output(surface=mixsh.outputs[0], volume=vol.outputs[0], target="CYCLES")
    # Eevee cannot reflect through its transmission path (tested: no Fresnel reflection with or without raytraced
    # refraction), so Eevee gets an opaque dark-murk surface with the same ripples: reflections come from raytracing/probes.
    # (Diffuse + Glossy by a Fresnel node rather than a second Principled: Cycles counts every closure node in the
    #  tree against its 64-closure budget, two Principled BSDFs blew it to 76.)
    murk_e = t.mix(murk_far, C(0.140, 0.152, 0.124), C(0.156, 0.163, 0.136))
    murk_e.node.name = murk_e.node.label = "WATER_MURK_EEVEE"
    dif = t.new("ShaderNodeBsdfDiffuse"); t.plug(dif.inputs["Color"], murk_e); t.plug(dif.inputs["Normal"], normal)
    # the same tint in Eevee, at the same strength, so the navigable viewport and the flythrough test agree with
    # Cycles on the water's colour (round-8 review carry 6).
    glo = t.new("ShaderNodeBsdfGlossy"); t.plug(glo.inputs["Color"], t.mixv(gloss_mix, C(1.0, 1.0, 1.0), gloss_tint)); t.plug(glo.inputs["Roughness"], rough); t.plug(glo.inputs["Normal"], normal)
    fr = t.new("ShaderNodeFresnel"); t.plug(fr.inputs["IOR"], 1.333); t.plug(fr.inputs["Normal"], normal)
    mx = t.new("ShaderNodeMixShader"); t.link(fr.outputs[0], mx.inputs[0]); t.link(dif.outputs[0], mx.inputs[1]); t.link(glo.outputs[0], mx.inputs[2])
    t.output(surface=mx.outputs[0], target="EEVEE")
    m.use_raytrace_refraction = False
    m.surface_render_method = "DITHERED"
    m.use_backface_culling = False
    # drift driver (frame-based). Safe if drivers are disabled: the value simply stays 0.
    try:
        fc = time.node.outputs[0].driver_add("default_value")
        fc.driver.type = "SCRIPTED"
        fc.driver.expression = "frame * 0.03"
    except Exception as e:
        print("[mat_build] water driver skipped:", e)
    return ML.finish(m)


def foliage_image(name, data=False):
    p = ML.TEX_DIR / "foliage" / f"{name}.png"
    key = f"TEX_foliage_{name}"
    img = bpy.data.images.get(key)
    if img is None:
        if not p.exists():
            print(f"[mat_build] WARNING missing foliage texture {p} (run scripts/mat_leaf_textures.py)")
            return None
        img = bpy.data.images.load(str(p), check_existing=True)
        img.name = key
    img.colorspace_settings.name = "Non-Color" if data else "sRGB"
    img.alpha_mode = "STRAIGHT"
    return img


def leaf_material(name, texture, translucent, rough=0.55, hue_var=0.05, val_var=0.3, seed=20.0, spec=0.3, translucency=0.3,
                  sheen=0.15, tint=(1.0, 1.0, 1.0), alpha_cut=0.5, cluster_var=0.2, nrm_strength=0.6):
    """Alpha-cut, two-sided, translucent card material on a generated RGBA foliage texture (UV map 'UVMap').
    Per-tree hue/value variation from Object Info Random, cluster-scale variation from object-space noise."""
    m = ML.new_material(name)
    t = Tree(m.node_tree)
    uv = t.new("ShaderNodeUVMap"); uv.uv_map = "UVMap"
    img = foliage_image(texture)
    tex = t.new("ShaderNodeTexImage", projection="FLAT", interpolation="Linear", extension="EXTEND")
    tex.image = img
    t.link(uv.outputs[0], tex.inputs["Vector"])
    inst = t.group(G["instance"], Seed=seed)
    P = t.vadd(t.texcoord().outputs["Object"], t.vscale(inst.outputs["Offset"], 0.1))
    hue = t.madd(t.sub(inst.outputs["R2"], 0.5), hue_var, 0.5)
    val = t.madd(t.sub(inst.outputs["R3"], 0.5), val_var, 1.0)
    c = t.vmul(tex.outputs["Color"], tint)
    c = t.hsv(c, hue=hue, val=val)
    cl = t.maprange(t.noise(P, 1.2, detail=2), 0.3, 0.7, 1.0 - cluster_var, 1.0 + cluster_var)
    c = t.vscale(c, cl)
    # alpha: hard-ish cut so cards read solid at 120 m, soft rim at 3 m
    alpha = t.maprange(tex.outputs["Alpha"], alpha_cut - 0.15, alpha_cut + 0.15, 0.0, 1.0)
    # blade relief: a real tangent-space normal map (generated with the colour/alpha, see mat_leaf_textures.save_maps)
    nimg = foliage_image(texture + "_nrm", data=True)
    normal = None
    if nimg is not None:
        ntex = t.new("ShaderNodeTexImage", projection="FLAT", interpolation="Linear", extension="EXTEND")
        ntex.image = nimg
        t.link(uv.outputs[0], ntex.inputs["Vector"])
        normal = t.normal_map(ntex.outputs["Color"], strength=nrm_strength, uv_map="UVMap")
    # translucency mask: thin margins and tips transmit, midribs/stems/needle spines do not
    timg = foliage_image(texture + "_trn", data=True)
    tfac = translucency
    if timg is not None:
        ttex = t.new("ShaderNodeTexImage", projection="FLAT", interpolation="Linear", extension="EXTEND")
        ttex.image = timg
        t.link(uv.outputs[0], ttex.inputs["Vector"])
        tfac = t.mul(t.maprange(ttex.outputs["Color"], 0.05, 0.85, 0.35, 1.55), translucency)
    pin = {"Base Color": c, "Roughness": rough, "Specular IOR Level": spec, "Sheen Weight": sheen}
    if normal is not None:
        pin["Normal"] = normal
    bsdf = t.principled(**pin)
    tr = t.new("ShaderNodeBsdfTranslucent")
    t.plug(tr.inputs["Color"], t.vmul(c, translucent))
    if normal is not None:
        t.plug(tr.inputs["Normal"], normal)
    mix = t.new("ShaderNodeMixShader")
    t.plug(mix.inputs[0], tfac)
    t.link(bsdf.outputs[0], mix.inputs[1]); t.link(tr.outputs[0], mix.inputs[2])
    transp = t.new("ShaderNodeBsdfTransparent")
    cut = t.new("ShaderNodeMixShader")
    t.plug(cut.inputs[0], alpha)
    t.link(transp.outputs[0], cut.inputs[1]); t.link(mix.outputs[0], cut.inputs[2])
    t.output(surface=cut.outputs[0])
    m.use_backface_culling = False
    m.surface_render_method = "DITHERED"
    try:
        m.use_transparent_shadow = True
    except Exception:
        pass
    m["pfa_texture"] = texture
    return ML.finish(m)


def build_extra_env():
    # Presidio ridge / tree masses at 300+ m: dark crown-clumped green
    # Round 5: on ENV's new 250-450 m canopy this read bright and yellow in direct sun (cam06, env_r4_sheet). A real
    # canopy is not a Lambertian shell of leaf albedo: most of what the eye sees is self-shadowed gaps between and
    # inside the crowns. Ref 105's tree masses measure lum 120-152 against a sunlit lawn at 142 and sunlit stucco at
    # 182, at saturation 0.04-0.13 and a hue that is never below 50 deg -- i.e. NOT brighter than grass, and barely
    # coloured. Three changes: albedo down ~45 % and shifted cool (B/G 0.43 -> 0.63, so warm sun cannot drive it
    # yellow), an explicit gap-shadow mask that puts ~40 % of the surface at 0.42x, and specular 0.15 -> 0.06.
    m = ML.new_material("MAT_backdrop_forest")
    t = Tree(m.node_tree)
    W = t.geometry().outputs["Position"]
    N = t.geometry().outputs["Normal"]
    crowns = t.voronoi(W, 1.0 / 9.0, feature="SMOOTH_F1", randomness=1.0)
    cr = t.sepxyz(crowns.outputs["Color"])[0]
    c = t.mix(cr, C(0.0140, 0.0235, 0.0150), C(0.0305, 0.0440, 0.0280))
    # gaps: the shaded flanks and the holes between crowns. Two scales (whole crowns, 3 m branch clumps) so the mass
    # never reads as one lit plane, plus a downward bias -- the underside of a canopy is always the dark part.
    gap = t.maximum(t.maprange(crowns.outputs["Distance"], 0.55, 0.10, 0.0, 1.0),
                    t.maprange(t.noise(W, 0.33, detail=3, rough=0.65), 0.52, 0.30, 0.0, 1.0))
    gap = t.clamp01(t.add(t.mul(gap, 0.8), t.mul(t.maprange(t.sepxyz(N)[2], 0.35, -0.2, 0.0, 1.0), 0.35)))
    c = t.vscale(c, t.sub(1.0, t.mul(gap, 0.66)))
    haze = t.maprange(t.noise(W, 0.02, detail=2), 0.35, 0.65, 0.88, 1.12)
    c = t.vscale(c, haze)
    normal = t.bump(t.add(crowns.outputs["Distance"], t.mul(t.noise(W, 0.8, detail=3), 0.4)), strength=0.7, distance=0.6, normal=N)
    t.output(surface=t.principled(**{"Base Color": c, "Roughness": 0.92, "Specular IOR Level": 0.06, "Normal": normal}).outputs[0])
    ML.finish(m)
    # far-field street asphalt (ENV's Marina / Presidio city field, env_lib placeholder was 0.052 grey / rough 0.72).
    # Cheap by design: no textures, everything from world-space noise, per-object value spread from PFA_instance
    # (Object Info Random hashed with ENV's `instance_seed` custom property).
    m = ML.new_material("MAT_backdrop_asphalt")
    t = Tree(m.node_tree)
    inst = t.group(G["instance"], Seed=31.0)
    W = t.geometry().outputs["Position"]
    N = t.geometry().outputs["Normal"]
    P = t.vadd(W, inst.outputs["Offset"])
    lanes = t.maprange(t.noise(P, 0.06, detail=3, rough=0.6), 0.35, 0.70, 0.0, 1.0)    # sun-bleached wheel tracks
    patch = t.maprange(t.noise(P, 0.45, detail=2), 0.56, 0.63, 0.0, 1.0)               # darker resurfacing patches
    grit = t.maprange(t.noise(P, 9.0, detail=3), 0.35, 0.65, 0.92, 1.08)
    c = t.mix(lanes, C(0.030, 0.029, 0.029), C(0.078, 0.076, 0.074))
    c = t.mix(t.mul(patch, 0.75), c, C(0.021, 0.020, 0.021))
    c = t.vscale(c, t.mul(grit, t.madd(t.sub(inst.outputs["R3"], 0.5), 0.30, 1.0)))    # +-15 % per object
    rough = t.add(0.72, t.mul(t.sub(t.noise(P, 3.0, detail=2), 0.5), 0.18))
    normal = t.bump(t.noise(P, 14.0, detail=3), strength=0.25, distance=0.006, normal=N)
    t.output(surface=t.principled(**{"Base Color": c, "Roughness": rough, "Specular IOR Level": 0.35, "Normal": normal}).outputs[0])
    ML.finish(m)
    # far-field mission-tile roofs (env_lib placeholder was 0.185/0.072/0.042 / rough 0.80). Courses come off world Z
    # so they stay parallel to the eaves whatever way a building faces; pans off world X+Y. Both are sub-pixel past
    # 250 m -- they exist so the near ones in cam 06 are not flat -- and the per-building hue/value spread is what
    # actually reads: a tile roof field is dozens of clay lots, never one colour.
    m = ML.new_material("MAT_backdrop_roof_tile")
    t = Tree(m.node_tree)
    inst = t.group(G["instance"], Seed=32.0)
    W = t.geometry().outputs["Position"]
    N = t.geometry().outputs["Normal"]
    P = t.vadd(W, inst.outputs["Offset"])
    wx, wy, wz = t.sepxyz(W)
    course = t.smoothstep(t.absval(t.sub(t.fract(t.mul(wz, 3.2)), 0.5)), 0.30, 0.5)    # ~0.31 m courses
    pan = t.smoothstep(t.absval(t.sub(t.fract(t.mul(t.add(wx, wy), 3.6)), 0.5)), 0.26, 0.5)
    mottle = t.maprange(t.noise(P, 1.4, detail=3, rough=0.6), 0.30, 0.70, 0.0, 1.0)
    c = t.mix(mottle, C(0.128, 0.048, 0.028), C(0.232, 0.100, 0.058))
    c = t.mix(t.mul(course, 0.55), c, t.scale_color(c, 0.55))                          # shadow under each course
    c = t.mix(t.mul(pan, 0.30), c, t.scale_color(c, 1.22))                             # sunlit pan crowns
    c = t.hsv(c, hue=t.madd(t.sub(inst.outputs["R2"], 0.5), 0.033, 0.5),               # +-6 deg per building
              val=t.madd(t.sub(inst.outputs["R3"], 0.5), 0.34, 1.0))                   # +-17 %
    grey = t.maprange(inst.outputs["R4"], 0.82, 0.86, 0.0, 1.0)                        # ~15 % are grey composition
    c = t.mix(grey, c, C(0.058, 0.055, 0.052))
    moss = t.mul(t.maprange(t.noise(P, 2.2, detail=3, rough=0.6), 0.62, 0.78, 0.0, 1.0), 0.6)
    c = t.mix(moss, c, C(0.045, 0.050, 0.030))
    rough = t.add(0.80, t.mul(t.sub(t.noise(P, 4.0, detail=2), 0.5), 0.14))
    normal = t.bump(t.add(t.mul(pan, 0.6), t.mul(course, 0.3)), strength=0.4, distance=0.02, normal=N)
    t.output(surface=t.principled(**{"Base Color": c, "Roughness": rough, "Specular IOR Level": 0.30, "Normal": normal}).outputs[0])
    ML.finish(m)
    # distant hill: dry grass and scrub
    m = ML.new_material("MAT_backdrop_hill")
    t = Tree(m.node_tree)
    W = t.geometry().outputs["Position"]
    scrub = t.smoothstep(t.noise(W, 0.05, detail=3), 0.5, 0.65)
    c = t.mix(scrub, C(0.26, 0.26, 0.17), C(0.09, 0.12, 0.06))
    c = t.vscale(c, t.maprange(t.noise(W, 0.3, detail=2), 0.3, 0.7, 0.85, 1.15))
    t.output(surface=t.principled(**{"Base Color": c, "Roughness": 0.95, "Specular IOR Level": 0.1}).outputs[0])
    ML.finish(m)
    # lamp posts: dark painted iron, milky globe above z 3.55 (object space)
    m = ML.new_material("MAT_lamp_post")
    t = Tree(m.node_tree)
    P = t.texcoord().outputs["Object"]
    px, py, pz = t.sepxyz(P)
    globe = t.maprange(pz, 3.5, 3.6, 0.0, 1.0)
    c = t.mix(globe, C(0.035, 0.035, 0.035), C(0.75, 0.74, 0.68))
    rough = t.mixf(globe, 0.45, 0.35)
    t.output(surface=t.principled(**{"Base Color": c, "Roughness": rough, "Specular IOR Level": 0.5, "Metallic": t.mixf(globe, 0.15, 0.0)}).outputs[0])
    ML.finish(m)


def bark_material(name, tex_set, base, seed, tile=None, rough=0.85, bump=0.6, stringy=0.0):
    m = ML.new_material(name)
    t = Tree(m.node_tree)
    inst = t.group(G["instance"], Seed=seed)
    P = t.vadd(t.texcoord().outputs["Object"], inst.outputs["Offset"])
    tex = t.image_set(tex_set, P, maps=("diff", "rough", "disp"), tile=tile)
    val = t.madd(t.sub(inst.outputs["R3"], 0.5), 0.25, 1.0)
    c = t.mix(0.35, tex["diff"], t.vscale(base, t.div(t.luminance(tex["diff"]), ML.TEXTURE_SETS[tex_set]["mean_lum"])))
    c = t.vscale(c, val)
    h = tex["disp"]
    if stringy > 0:   # extra vertical fibre streaks (cypress)
        px, py, pz = t.sepxyz(P)
        fib = t.noise(t.combxyz(t.mul(px, 12.0), t.mul(py, 12.0), t.mul(pz, 0.6)), 1.0, detail=3, rough=0.6)
        h = t.madd(fib, stringy, h)
        c = t.vscale(c, t.maprange(fib, 0.3, 0.7, 0.85, 1.1))
    N = t.geometry().outputs["Normal"]
    normal = t.bump(h, strength=bump, distance=0.02, normal=N)
    r = t.add(t.mul(t.sub(tex["rough"], 0.5), 0.3), rough)
    bsdf = t.principled(**{"Base Color": c, "Roughness": r, "Normal": normal, "Specular IOR Level": 0.3})
    t.output(surface=bsdf.outputs[0])
    return ML.finish(m)


def build_ground():
    # lawn: patchy November grass, fine blade grain, no gloss
    m = ML.new_material("MAT_lawn")
    t = Tree(m.node_tree)
    W = t.geometry().outputs["Position"]
    N = t.geometry().outputs["Normal"]
    wx, wy, wz = t.sepxyz(W)
    flat = t.combxyz(wx, wy, 0.0)
    dry = t.smoothstep(t.noise(flat, 0.12, detail=3, rough=0.55), 0.45, 0.7)
    wet = t.smoothstep(t.noise(t.vadd(flat, (50, 50, 0)), 0.08, detail=2), 0.55, 0.75)
    c = t.mix(dry, C(0.11, 0.19, 0.05), C(0.22, 0.21, 0.07))
    c = t.mix(wet, c, C(0.07, 0.13, 0.035))
    blade = t.noise(flat, 90.0, detail=3, rough=0.65)
    c = t.vscale(c, t.maprange(blade, 0.3, 0.7, 0.75, 1.25))
    clump = t.noise(flat, 8.0, detail=2)
    h = t.add(t.mul(blade, 0.6), clump)
    normal = t.bump(h, strength=0.5, distance=0.02, normal=N)
    al = t.group(G["algae"], Height=0.45, **{"Band Z": WATER_Z + 0.15})
    band, damp = al.outputs["Band"], al.outputs["Damp"]
    c = t.mix(t.mul(damp, 0.45), c, t.vmul(c, (0.62, 0.66, 0.58)))       # QA-04-3c: wet margin above the band
    c = t.mix(t.mul(band, 0.85), c, C(0.035, 0.055, 0.028))
    bsdf = t.principled(**{"Base Color": c, "Roughness": t.mixf(band, 0.85, 0.42), "Specular IOR Level": 0.2,
                           "Normal": normal, "Sheen Weight": 0.1})
    t.output(surface=bsdf.outputs[0])
    ML.finish(m)

    # soil
    m = ML.new_material("MAT_soil")
    t = Tree(m.node_tree)
    W = t.geometry().outputs["Position"]
    N = t.geometry().outputs["Normal"]
    tex = t.image_set("forest_ground_04", W, maps=("diff", "rough", "disp"))
    c = t.mix(0.4, tex["diff"], t.vscale(C(0.18, 0.12, 0.08), t.div(t.luminance(tex["diff"]), 0.25)))
    c = t.vscale(c, t.maprange(t.noise(W, 0.3, detail=2), 0.3, 0.7, 0.8, 1.15))
    normal = t.bump(tex["disp"], strength=0.5, distance=0.02, normal=N)
    # wet margin: the shore darkens and slicks over the last ~0.5 m down to the water (QA-02-3)
    al = t.group(G["algae"], Height=0.5, **{"Band Z": WATER_Z + 0.18})
    band, damp = al.outputs["Band"], al.outputs["Damp"]
    # QA-04-3c: the shore strip measured as one uniform pale tone. The last ~0.9 m down to the water is wet mud,
    # then the growth band; both are on the soil now, not only on the stone.
    c = t.mix(t.mul(damp, 0.62), c, t.vmul(c, (0.50, 0.52, 0.48)))
    c = t.mix(t.mul(band, 0.88), c, C(0.030, 0.040, 0.026))
    bsdf = t.principled(**{"Base Color": c, "Roughness": t.mixf(band, t.add(t.mul(t.sub(tex["rough"], 0.5), 0.3), 0.9), 0.38),
                           "Normal": normal, "Specular IOR Level": 0.25})
    t.output(surface=bsdf.outputs[0])
    ML.finish(m)

    # decomposed granite / gravel path
    m = ML.new_material("MAT_gravel_path")
    t = Tree(m.node_tree)
    W = t.geometry().outputs["Position"]
    N = t.geometry().outputs["Normal"]
    tex = t.image_set("gravelly_sand", W, maps=("diff", "rough", "disp"))
    c = t.mix(0.45, tex["diff"], t.vscale(C(0.32, 0.28, 0.21), t.div(t.luminance(tex["diff"]), 0.40)))
    damp = t.smoothstep(t.noise(W, 0.2, detail=2), 0.55, 0.75)
    c = t.mix(t.mul(damp, 0.5), c, t.vmul(c, (0.6, 0.58, 0.55)))
    normal = t.bump(tex["disp"], strength=0.5, distance=0.02, normal=N)
    al = t.group(G["algae"], Height=0.45, **{"Band Z": WATER_Z + 0.15})
    band, damp = al.outputs["Band"], al.outputs["Damp"]
    c = t.mix(t.mul(damp, 0.55), c, t.vmul(c, (0.55, 0.56, 0.53)))
    c = t.mix(t.mul(band, 0.85), c, C(0.040, 0.052, 0.034))
    bsdf = t.principled(**{"Base Color": c, "Roughness": t.mixf(band, t.add(t.mul(t.sub(tex["rough"], 0.5), 0.3), 0.85), 0.40),
                           "Normal": normal, "Specular IOR Level": 0.3})
    t.output(surface=bsdf.outputs[0])
    ML.finish(m)

    # rip-rap boulders: grey-brown stone, per-instance tone, wet/dark below the waterline, lichen on top
    m = ML.new_material("MAT_rock_riprap")
    t = Tree(m.node_tree)
    inst = t.group(G["instance"], Seed=30.0)
    P = t.vadd(t.texcoord().outputs["Object"], inst.outputs["Offset"])
    W = t.geometry().outputs["Position"]
    N = t.geometry().outputs["Normal"]
    nx, ny, nz = t.sepxyz(N)
    wx, wy, wz = t.sepxyz(W)
    tex = t.image_set("rock_boulder_dry", P, maps=("diff", "rough", "disp"))
    hue = t.madd(t.sub(inst.outputs["R2"], 0.5), 0.06, 0.5)
    val = t.madd(t.sub(inst.outputs["R3"], 0.5), 0.3, 1.0)
    base = t.hsv(C(0.30, 0.28, 0.22), hue=hue, val=val)
    c = t.mix(0.35, t.vscale(base, t.div(t.luminance(tex["diff"]), 0.45)), tex["diff"])
    c = t.vscale(c, 0.85)
    lich = t.mul(t.smoothstep(t.noise(P, 5.0, detail=3), 0.58, 0.7), t.maprange(nz, 0.2, 0.7, 0.0, 1.0))
    c = t.mix(t.mul(lich, 0.7), c, C(0.36, 0.38, 0.26))
    # QA-02-3: the v2 band was 0.35 m and stopped ~0.4 m above the water, so it never read at hero distance.
    al = t.group(G["algae"], Offset=inst.outputs["Offset"], Height=0.55, **{"Band Z": WATER_Z + 0.10})
    band = al.outputs["Band"]
    c = t.mix(t.mul(al.outputs["Damp"], 0.6), c, t.vmul(c, (0.52, 0.54, 0.50)))
    c = t.mix(band, c, t.mix(al.outputs["Brown"], C(0.042, 0.058, 0.038), C(0.075, 0.058, 0.032)))
    ao = t.ao(distance=0.3, samples=6)
    c = t.mix(t.mul(t.sub(1.0, ao), 0.5), c, t.vmul(c, (0.55, 0.53, 0.5)))
    normal = t.bump(tex["disp"], strength=0.6, distance=0.02, normal=N)
    r = t.mixf(band, t.add(t.mul(t.sub(tex["rough"], 0.5), 0.3), 0.8), 0.4)
    bsdf = t.principled(**{"Base Color": c, "Roughness": r, "Normal": normal, "Specular IOR Level": 0.35})
    t.output(surface=bsdf.outputs[0])
    ML.finish(m)


def build_lagoon_bed():
    """MAT_lagoon_bed (ENV round 6): the lagoon floor under the water plane. Environment split ENV_lagoon_bed onto
    its own name after a magenta-bed probe showed that at QA's 18-20 deg grazing crop 0.00 % of the near-water
    pixels see the bed at all -- so this material is deliberately cheap: it is what you see through the water in
    the shallow first metre or two at the shore, and nothing else. Muddy green-brown, very rough, no specular
    highlight to speak of (it is always under water)."""
    m = ML.new_material("MAT_lagoon_bed")
    t = Tree(m.node_tree)
    W = t.geometry().outputs["Position"]
    N = t.geometry().outputs["Normal"]
    wx, wy, wz = t.sepxyz(W)
    flat = t.combxyz(wx, wy, 0.0)
    # silt drifts (5-15 m) over a coarser mud/weed mottle (1-3 m), plus a fine grain so the shallows are not flat
    drift = t.maprange(t.noise(flat, 0.09, detail=3, rough=0.55), 0.3, 0.7, 0.0, 1.0)
    c = t.mix(drift, C(0.052, 0.046, 0.030), C(0.038, 0.049, 0.030))
    weed = t.smoothstep(t.noise(flat, 0.45, detail=3, rough=0.6), 0.56, 0.72)
    c = t.mix(t.mul(weed, 0.7), c, C(0.026, 0.040, 0.022))
    c = t.vscale(c, t.maprange(t.noise(W, 6.0, detail=3), 0.3, 0.7, 0.82, 1.18))
    # the last half metre before the shore dries out lighter (exposed silt / sand)
    shore = t.maprange(wz, WATER_Z - 0.55, WATER_Z - 0.05, 0.0, 1.0)
    c = t.mix(t.mul(shore, 0.55), c, C(0.086, 0.076, 0.050))
    h = t.add(t.mul(t.noise(W, 3.0, detail=3), 0.6), t.mul(t.noise(W, 18.0, detail=2), 0.25))
    bsdf = t.principled(**{"Base Color": c, "Roughness": 0.94, "Specular IOR Level": 0.15,
                           "Normal": t.bump(h, strength=0.35, distance=0.02, normal=N)})
    t.output(surface=bsdf.outputs[0])
    return ML.finish(m)


def build_backdrop_details():
    """Exhibition-hall details ENV needs by name: roof membrane, skylight glazing, the green door on the rotunda axis."""
    # roof: pale grey built-up membrane with tar seams and pooled grime, seen from above in the aerial only
    m = ML.new_material("MAT_backdrop_roof")
    t = Tree(m.node_tree)
    W = t.geometry().outputs["Position"]
    N = t.geometry().outputs["Normal"]
    seams = t.smoothstep(t.absval(t.sub(t.fract(t.mul(t.sepxyz(W)[1], 0.4)), 0.5)), 0.44, 0.5)
    grime = t.maprange(t.noise(W, 0.35, detail=3, rough=0.6), 0.35, 0.7, 0.0, 1.0)
    c = t.mix(grime, C(0.155, 0.150, 0.135), C(0.085, 0.082, 0.075))
    c = t.mix(t.mul(seams, 0.8), c, C(0.045, 0.043, 0.040))
    rough = t.add(0.82, t.mul(t.sub(t.noise(W, 2.0, detail=2), 0.5), 0.16))
    normal = t.bump(t.add(t.mul(t.noise(W, 12.0, detail=3), 0.5), t.mul(seams, 0.5)), strength=0.35, distance=0.01, normal=N)
    t.output(surface=t.principled(**{"Base Color": c, "Roughness": rough, "Specular IOR Level": 0.35, "Normal": normal}).outputs[0])
    ML.finish(m)
    # skylight glazing: dirty wired glass, mostly a dark reflective panel at hero distance
    m = ML.new_material("MAT_backdrop_skylight")
    t = Tree(m.node_tree)
    W = t.geometry().outputs["Position"]
    N = t.geometry().outputs["Normal"]
    dirt = t.maprange(t.noise(W, 1.6, detail=3, rough=0.6), 0.3, 0.75, 0.0, 1.0)
    c = t.mix(dirt, C(0.072, 0.080, 0.092), C(0.15, 0.144, 0.122))
    rough = t.add(0.14, t.mul(dirt, 0.30))
    normal = t.bump(t.mul(t.noise(W, 6.0, detail=2), 0.4), strength=0.2, distance=0.008, normal=N)
    t.output(surface=t.principled(**{"Base Color": c, "Roughness": rough, "Specular IOR Level": 0.75,
                                     "Coat Weight": 0.25, "Coat Roughness": 0.12, "Normal": normal}).outputs[0])
    ML.finish(m)
    # the hall's green door on the rotunda axis (visible through the central arch in the hero): old semi-gloss
    # park-service green paint on wood, chalked and streaked, with a dull bronze push-plate zone at object z 1.0-1.2
    m = ML.new_material("MAT_backdrop_door_green")
    t = Tree(m.node_tree)
    P = t.texcoord().outputs["Object"]
    W = t.geometry().outputs["Position"]
    N = t.geometry().outputs["Normal"]
    px, py, pz = t.sepxyz(P)
    boards = t.smoothstep(t.absval(t.sub(t.fract(t.mul(px, 1.6)), 0.5)), 0.42, 0.5)
    chalk = t.maprange(t.noise(W, 3.0, detail=3, rough=0.6), 0.3, 0.72, 0.0, 1.0)
    c = t.mix(chalk, C(0.028, 0.055, 0.036), C(0.060, 0.088, 0.062))
    c = t.mix(t.mul(boards, 0.8), c, C(0.014, 0.028, 0.019))
    # weathered lower edge (kicked, damp)
    c = t.mix(t.maprange(pz, 0.05, 0.35, 0.7, 0.0), c, C(0.030, 0.038, 0.030))
    plate = t.mul(t.maprange(pz, 0.95, 1.02, 0.0, 1.0), t.maprange(pz, 1.18, 1.25, 1.0, 0.0))
    c = t.mix(plate, c, C(0.115, 0.085, 0.045))
    rough = t.mixf(plate, t.add(0.42, t.mul(chalk, 0.30)), 0.45)
    normal = t.bump(t.add(t.mul(t.noise(W, 40.0, detail=3), 0.3), t.mul(boards, 0.6)), strength=0.3, distance=0.006, normal=N)
    t.output(surface=t.principled(**{"Base Color": c, "Roughness": rough, "Specular IOR Level": 0.5,
                                     "Metallic": t.mul(plate, 0.7), "Normal": normal}).outputs[0])
    ML.finish(m)


def build_misc():
    # gulls: white body, grey mantle from object z, matte
    m = ML.new_material("MAT_bird_white")
    t = Tree(m.node_tree)
    inst = t.group(G["instance"], Seed=40.0)
    P = t.texcoord().outputs["Object"]
    px, py, pz = t.sepxyz(P)
    mantle = t.maprange(pz, 0.05, 0.12, 0.0, 1.0)
    c = t.mix(mantle, C(0.80, 0.80, 0.78), C(0.35, 0.36, 0.37))
    c = t.vscale(c, t.madd(t.sub(inst.outputs["R3"], 0.5), 0.2, 1.0))
    bsdf = t.principled(**{"Base Color": c, "Roughness": 0.6, "Specular IOR Level": 0.3, "Subsurface Weight": 0.1, "Subsurface Radius": (0.02, 0.01, 0.005)})
    t.output(surface=bsdf.outputs[0])
    ML.finish(m)


def build_all_materials():
    build_concrete_family()
    build_dome()
    build_water()
    leaf_material("MAT_leaf_cypress", "needles_cypress", (0.9, 1.1, 0.5), rough=0.6, hue_var=0.05, val_var=0.35, seed=20.0, translucency=0.25, alpha_cut=0.45)
    # conifers other than cypress (Monterey pine, redwood): darker, bluer, longer needles -- ENV maps pines here
    leaf_material("MAT_leaf_pine", "needles_pine", (0.7, 0.95, 0.5), rough=0.55, hue_var=0.04, val_var=0.28, seed=27.0,
                  translucency=0.18, spec=0.35, tint=(0.80, 0.92, 0.78), alpha_cut=0.42, nrm_strength=0.5)
    leaf_material("MAT_leaf_eucalyptus", "leaves_eucalyptus", (0.8, 1.0, 0.5), rough=0.42, hue_var=0.06, val_var=0.3, seed=21.0, spec=0.4, translucency=0.3)
    leaf_material("MAT_leaf_broadleaf", "leaves_broadleaf", (0.8, 1.2, 0.4), rough=0.5, hue_var=0.07, val_var=0.35, seed=22.0, translucency=0.35)
    # QA-05-10 / ENV r7 hand-off: the hero shore band measured lum 91.1 against ref 169's 115.6 at sat 0.487
    # against the photo's 0.663 -- so this round can spend BOTH, and the cheapest lum with the least saturation
    # cost is translucency: a backlit leaf is lighter and less chromatic than the same leaf lit from the front.
    leaf_material("MAT_shrub", "leaves_shrub", (0.85, 1.15, 0.60), rough=0.5, hue_var=0.08, val_var=0.4, seed=23.0,
                  translucency=0.34, spec=0.4, tint=(1.86, 1.88, 1.80))
    # shore planting mix (ENV): a paler grey-green (pittosporum / agapanthus) and a straw-dry one, so a 1400-bush belt
    # is not one flat green. Same card texture, different tint / value spread.
    leaf_material("MAT_shrub_light", "leaves_shrub", (0.90, 1.10, 0.70), rough=0.45, hue_var=0.06, val_var=0.45, seed=24.0,
                  translucency=0.40, spec=0.45, tint=(2.30, 2.36, 2.10), sheen=0.2)
    leaf_material("MAT_shrub_dry", "leaves_shrub", (1.05, 0.95, 0.5), rough=0.62, hue_var=0.05, val_var=0.5, seed=25.0,
                  translucency=0.22, spec=0.25, tint=(6.30, 1.62, 0.98), sheen=0.1, cluster_var=0.3)
    leaf_material("MAT_reeds", "reeds", (0.95, 1.05, 0.60), rough=0.6, hue_var=0.06, val_var=0.4, seed=26.0,
                  translucency=0.45, cluster_var=0.35, tint=(1.82, 1.85, 1.74))
    build_extra_env()
    build_lagoon_bed()
    build_backdrop_details()
    bark_material("MAT_bark_cypress", "chinese_cedar_bark", C(0.20, 0.15, 0.11), 24.0, tile=1.6, rough=0.9, bump=0.7, stringy=0.4)
    bark_material("MAT_bark_eucalyptus", "bark_bluegum", C(0.40, 0.35, 0.29), 25.0, tile=1.82, rough=0.75, bump=0.5)
    build_ground()
    build_misc()


build_all_materials()

# =============================================================================== test objects (collection MAT_test)
coll = common.rebuild_collection("MAT_test")


def mat(name):
    return bpy.data.materials[name]


def box(name, size, loc, material, bevel=0.02, segments=2):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    common.link_object(o, coll)
    common.assign_material(o, mat(material))
    if bevel:
        b = o.modifiers.new("bevel", "BEVEL"); b.width = bevel; b.segments = segments; b.limit_method = "ANGLE"
    for p in o.data.polygons:
        p.use_smooth = False
    return o


def wall_with_ledge(name, x, z0, material, height=3.0, width=3.0):
    """3 m wall panel with a projecting cornice on top and a recessed square panel (to test streaks + recess dirt)."""
    w = box(name, (width, 0.4, height), (x, -0.2, z0 + height / 2), material)
    # recessed panel: boolean cut
    cut = box(name + "_cut", (0.8, 0.2, 0.8), (x - 0.7, 0.0, z0 + height * 0.45), material, bevel=0)
    cut.hide_render = True; cut.hide_viewport = True; cut.display_type = "WIRE"
    b = w.modifiers.new("cut", "BOOLEAN"); b.operation = "DIFFERENCE"; b.object = cut
    w.modifiers.move(len(w.modifiers) - 1, 0)
    box(name + "_ledge", (width + 0.3, 0.75, 0.28), (x, -0.2 + 0.18, z0 + height + 0.14), material)
    box(name + "_string", (width, 0.5, 0.12), (x, -0.2 + 0.05, z0 + height * 0.7), material)
    return w


def fluted_column(name, radius, height, loc, material, flutes=24, depth=0.06, fillet=0.22, segs=10, rings=12):
    bm = bmesh.new()
    n = flutes * segs
    prof = []
    for i in range(n):
        a = 2 * math.pi * i / n
        f = (i % segs) / segs        # position within one flute
        if f < fillet:
            r = radius
        else:
            u = (f - fillet) / (1 - fillet)   # 0..1 across the flute
            r = radius - depth * math.sin(math.pi * u)
        prof.append((r, a))
    layers = []
    for k in range(rings + 1):
        z = height * k / rings
        layers.append([bm.verts.new((r * math.cos(a), r * math.sin(a), z)) for (r, a) in prof])
    for k in range(rings):
        for i in range(n):
            bm.faces.new((layers[k][i], layers[k][(i + 1) % n], layers[k + 1][(i + 1) % n], layers[k + 1][i]))
    bm.faces.new(list(reversed(layers[0])))
    bm.faces.new(layers[-1])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new(name, me)
    o.location = loc
    coll.objects.link(o)
    common.assign_material(o, mat(material))
    b = o.modifiers.new("bevel", "BEVEL"); b.width = 0.012; b.segments = 2; b.limit_method = "ANGLE"; b.angle_limit = math.radians(20)
    return o


def lumpy(name, radius, loc, material, seed=1, strength=0.12, scale=0.35):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5, radius=radius, location=loc)
    o = bpy.context.object
    o.name = name
    common.link_object(o, coll)
    common.assign_material(o, mat(material))
    tex = bpy.data.textures.new(name + "_tex", "CLOUDS")
    tex.noise_scale = scale; tex.noise_depth = 3
    d = o.modifiers.new("disp", "DISPLACE"); d.texture = tex; d.strength = strength; d.texture_coords = "LOCAL"
    o.location = loc
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def plane(name, size, loc, material, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.scale = (size[0], size[1], 1.0)
    bpy.ops.object.transform_apply(scale=True)
    common.link_object(o, coll)
    common.assign_material(o, mat(material))
    return o


def dome(name, loc, material, base_r=16.5, sphere_r=21.7, rise=7.6, segs=96, rings=24):
    bm = bmesh.new()
    zc = rise - sphere_r     # sphere centre relative to the base ring
    layers = []
    for k in range(rings):
        z = rise * (k / rings) ** 1.4 if k else 0.0
        r = math.sqrt(max(sphere_r ** 2 - (z - zc) ** 2, 0.0))
        layers.append([bm.verts.new((r * math.cos(2 * math.pi * i / segs), r * math.sin(2 * math.pi * i / segs), z)) for i in range(segs)])
    apex = bm.verts.new((0, 0, rise))
    for k in range(rings - 1):
        for i in range(segs):
            bm.faces.new((layers[k][i], layers[k][(i + 1) % segs], layers[k + 1][(i + 1) % segs], layers[k + 1][i]))
    for i in range(segs):
        bm.faces.new((layers[-1][i], layers[-1][(i + 1) % segs], apex))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new(name, me)
    o.location = loc
    coll.objects.link(o)
    common.assign_material(o, mat(material))
    return o


GZ = -2.0    # lineup ground level (so the WATER_Z = -1.3 band lands on the podium samples)
# --- zone A: concrete close-ups (fronts face +Y, cameras stand at +Y)
wall_with_ledge("MAT_test_wall_ochre", -3.5, 8.0, "MAT_concrete_ochre")            # elevated: reads as an upper wall (no grey drift)
wall_with_ledge("MAT_test_wall_podium", 1.5, GZ, "MAT_concrete_podium", height=3.0)
box("MAT_test_wall_colonnade", (3.0, 0.4, 3.0), (6.5, -0.2, GZ + 1.5), "MAT_concrete_colonnade")
box("MAT_test_wall_colonnade_ledge", (3.3, 0.7, 0.25), (6.5, -0.05, GZ + 3.12), "MAT_concrete_colonnade")
fluted_column("MAT_test_column_rose", 1.2, 4.0, (-3.5, 0.0, GZ), "MAT_column_rose")
fluted_column("MAT_test_column_tan", 0.85, 4.0, (-7.0, 0.0, GZ), "MAT_column_tan_inner")
fluted_column("MAT_test_column_colonnade", 0.85, 4.0, (9.5, 0.0, GZ), "MAT_concrete_colonnade")
box("MAT_test_block_ornament", (1.0, 1.0, 1.0), (5.0, 0.0, GZ + 0.5), "MAT_ornament_concrete", bevel=0.03, segments=3)
def capital_proxy(name, loc, material, r=0.42, h=0.8, notches=12):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=loc, vertices=96)
    o = bpy.context.object
    o.name = name
    common.link_object(o, coll)
    common.assign_material(o, mat(material))
    for p in o.data.polygons:
        p.use_smooth = True
    cutters = []
    for i in range(notches):
        a = 2 * math.pi * i / notches
        c = box(f"{name}_n{i}", (0.07, r * 0.6, h * 0.8), (loc[0] + math.cos(a) * r, loc[1] + math.sin(a) * r, loc[2] - h * 0.05), material, bevel=0)
        c.rotation_euler = (0, 0, a + math.pi / 2)
        cutters.append(c)
    for k in (-0.22, 0.18):
        bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=0.05, location=(loc[0], loc[1], loc[2] + k), major_segments=64, minor_segments=12)
        c = bpy.context.object; c.name = f"{name}_ring{k}"; common.link_object(c, coll); cutters.append(c)
    for c in cutters:
        c.hide_render = True; c.hide_viewport = True; c.display_type = "WIRE"
        b = o.modifiers.new("cut_" + c.name, "BOOLEAN"); b.operation = "DIFFERENCE"; b.object = c
    b = o.modifiers.new("bevel", "BEVEL"); b.width = 0.012; b.segments = 2; b.limit_method = "ANGLE"
    return o


# six capital proxies with distinct `instance_seed` values: the per-instance weathering test at 60 m (QA non-negotiable
# "no ornament asset identical twice at hero distance"). They are separate meshes here, so Object Info Random already
# differs; the explicit property is what ORN's linked/instanced copies will carry.
for i in range(6):
    cap = capital_proxy(f"MAT_test_capital_v{i + 1}", (22.0 + i * 1.15, 20.0, GZ + 1.55), "MAT_ornament_concrete")
    cap["instance_seed"] = float(i) * 1.618 + 0.37
lumpy("MAT_test_blob", 0.4, (6.2, 0.0, GZ + 0.4), "MAT_ornament_concrete", seed=4)
basin = box("MAT_test_basin", (3.6, 2.8, 0.95), (1.5, 1.4, GZ + 0.475), "MAT_concrete_podium", bevel=0.015)
bcut = box("MAT_test_basin_cut", (3.1, 2.3, 2.0), (1.5, 1.4, GZ + 0.15 + 1.0), "MAT_concrete_podium", bevel=0)
bcut.hide_render = True; bcut.hide_viewport = True; bcut.display_type = "WIRE"
bb = basin.modifiers.new("cut", "BOOLEAN"); bb.operation = "DIFFERENCE"; bb.object = bcut
basin.modifiers.move(len(basin.modifiers) - 1, 0)
plane("MAT_test_basin_bed", (3.1, 2.3), (1.5, 1.4, GZ + 0.16), "MAT_soil")
plane("MAT_test_water", (3.1, 2.3), (1.5, 1.4, WATER_Z), "MAT_water_lagoon")
for i, (dx, dy) in enumerate(((-1.9, 0.9), (-1.6, 2.0), (3.4, 1.2), (3.6, 2.3))):
    lumpy(f"MAT_test_riprap_{i + 1}", 0.45, (1.5 + dx, dy, GZ + 0.15), "MAT_rock_riprap", seed=i + 7, strength=0.18, scale=0.5)
box("MAT_test_paving", (3.0, 3.0, 0.2), (-8.0, 5.0, GZ + 0.1), "MAT_paving", bevel=0.01)
box("MAT_test_greycard", (0.6, 0.02, 0.6), (-5.4, 0.01, 9.3), "MAT_concrete_ochre", bevel=0)
# --- zone B: the dome at true scale
dome("MAT_test_dome", (0.0, 60.0, GZ), "MAT_dome_membrane")
box("MAT_test_drum", (1.0, 1.0, 1.0), (0.0, 60.0, GZ - 0.5), "MAT_drum_band", bevel=0)   # placeholder core under the dome
# --- zone C: ground materials
plane("MAT_test_ground", (60.0, 130.0), (0.0, 40.0, GZ), "MAT_lawn")
plane("MAT_test_soil", (2.5, 2.5), (-12.0, 5.0, GZ + 0.01), "MAT_soil")
plane("MAT_test_gravel", (2.5, 2.5), (-12.0, 8.0, GZ + 0.01), "MAT_gravel_path")
# --- zone D: foliage
def card(name, size, loc, material, rot=(math.radians(90), 0, 0)):
    o = plane(name, size, loc, material, rot=rot)
    uv = o.data.uv_layers.new(name="UVMap")
    for poly in o.data.polygons:
        for k, li in enumerate(poly.loop_indices):
            uv.data[li].uv = ((0, 0), (1, 0), (1, 1), (0, 1))[k % 4]
    return o


for i, (nm, matn) in enumerate((("cypress", "MAT_leaf_cypress"), ("pine", "MAT_leaf_pine"), ("eucalyptus", "MAT_leaf_eucalyptus"), ("broadleaf", "MAT_leaf_broadleaf"), ("shrub", "MAT_shrub"), ("reeds", "MAT_reeds"))):
    card(f"MAT_test_card_{nm}", (1.0, 1.0), (7.4 + i * 1.15, 8.0, GZ + 0.55), matn)
    # a crossed-card cluster of the same material for the distance read
    for j in range(3):
        card(f"MAT_test_cluster_{nm}_{j}", (1.4, 1.4), (7.4 + i * 1.15, 30.0, GZ + 0.8), matn, rot=(math.radians(90), 0, j * math.pi / 3))
for i, (nm, matn) in enumerate((("shrub_light", "MAT_shrub_light"), ("shrub_dry", "MAT_shrub_dry"))):
    card(f"MAT_test_card_{nm}", (1.0, 1.0), (7.4 + i * 1.15, 10.5, GZ + 0.55), matn)
    for j in range(3):
        card(f"MAT_test_cluster_{nm}_{j}", (1.4, 1.4), (7.4 + i * 1.15, 32.5, GZ + 0.8), matn, rot=(math.radians(90), 0, j * math.pi / 3))
box("MAT_test_backdrop_forest", (6.0, 3.0, 4.0), (-4.0, 34.0, GZ + 2.0), "MAT_backdrop_forest", bevel=0)
box("MAT_test_backdrop_hill", (6.0, 3.0, 2.0), (-11.0, 34.0, GZ + 1.0), "MAT_backdrop_hill", bevel=0)
bpy.ops.mesh.primitive_cylinder_add(radius=0.08, depth=3.6, location=(13.5, 7.0, GZ + 1.8), vertices=12)
lp = bpy.context.object; lp.name = "MAT_test_lamp_post"; common.link_object(lp, coll); common.assign_material(lp, mat("MAT_lamp_post"))
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.22, location=(13.5, 7.0, GZ + 3.8))
lg = bpy.context.object; lg.name = "MAT_test_lamp_globe"; common.link_object(lg, coll); common.assign_material(lg, mat("MAT_lamp_post"))
lg.location = (13.5, 7.0, GZ + 3.8)
for o in (lp, lg):
    o.location.z -= GZ   # object space z = height above the post base, as in ENV
    o.location.z += GZ
for i, (nm, matn) in enumerate((("cypress", "MAT_bark_cypress"), ("eucalyptus", "MAT_bark_eucalyptus"))):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.3, depth=2.5, location=(12.5 + i * 1.0, 8.0, GZ + 1.25), vertices=48)
    o = bpy.context.object; o.name = f"MAT_test_bark_{nm}"; common.link_object(o, coll); common.assign_material(o, mat(matn))
    for p in o.data.polygons: p.use_smooth = True
lumpy("MAT_test_bird", 0.15, (7.0, 8.0, GZ + 0.15), "MAT_bird_white", seed=5, strength=0.02, scale=0.2)
# --- zone E: inner concrete, ceiling, drum band, backdrop
box("MAT_test_inner_vault", (2.5, 0.5, 2.5), (-10.5, -0.25, GZ + 1.25), "MAT_concrete_inner")
box("MAT_test_inner_soffit", (2.5, 1.2, 0.3), (-10.5, 0.35, GZ + 2.65), "MAT_concrete_inner")
ceil = box("MAT_test_ceiling", (2.0, 0.3, 2.0), (-13.5, -0.15, GZ + 1.2), "MAT_plaster_ceiling", bevel=0.01)
for i in range(2):
    for j in range(2):
        c = box(f"MAT_test_ceiling_cut{i}{j}", (0.7, 0.3, 0.7), (-13.5 - 0.45 + i * 0.9, 0.0, GZ + 0.75 + j * 0.9), "MAT_plaster_ceiling", bevel=0)
        c.hide_render = True; c.hide_viewport = True; c.display_type = "WIRE"
        b = ceil.modifiers.new(f"cut{i}{j}", "BOOLEAN"); b.operation = "DIFFERENCE"; b.object = c
box("MAT_test_drumband", (2.5, 0.4, 0.6), (-10.5, -0.2, GZ + 3.4), "MAT_drum_band", bevel=0.02)
box("MAT_test_backdrop", (3.0, 0.4, 2.5), (-16.5, -0.2, GZ + 1.25), "MAT_backdrop_building")
# far-field city fill (round 5): three tile roofs so the per-object hue spread is visible, and a strip of asphalt
for i in range(3):
    r = box(f"MAT_test_roof_tile_{i}", (1.5, 1.5, 0.9), (-13.6 + i * 1.7, 3.6, GZ + 0.45), "MAT_backdrop_roof_tile", bevel=0.02)
    r.rotation_euler = (0, 0, math.radians(17 * i))
    r["instance_seed"] = 0.13 + 0.31 * i
plane("MAT_test_asphalt", (5.0, 3.0), (-12.0, 6.5, GZ + 0.01), "MAT_backdrop_asphalt")
# exhibition-hall details for ENV: roof membrane (tilted up so the misc camera sees it), skylight glazing, green door
roofp = box("MAT_test_backdrop_roof", (2.4, 1.6, 0.15), (-19.6, 0.6, GZ + 2.2), "MAT_backdrop_roof", bevel=0)
roofp.rotation_euler = (math.radians(-55), 0, 0)
box("MAT_test_backdrop_skylight", (1.1, 0.15, 0.9), (-19.6, -0.2, GZ + 0.9), "MAT_backdrop_skylight", bevel=0.01)
door = box("MAT_test_backdrop_door", (1.6, 0.12, 2.4), (-22.4, -0.2, GZ + 1.2), "MAT_backdrop_door_green", bevel=0.01)
door.location.z = GZ + 1.2

# grey card: an 18 % reflectance reference next to the ochre wall (test-only material)
gc = ML.new_material("MAT_test_greycard18")
tg = Tree(gc.node_tree)
tg.output(surface=tg.principled(**{"Base Color": C(0.18, 0.18, 0.18), "Roughness": 0.9, "Specular IOR Level": 0.2}).outputs[0])
ML.finish(gc)
common.assign_material(bpy.data.objects["MAT_test_greycard"], gc)

for m in bpy.data.materials:
    m.use_fake_user = True
n_mat = len([m for m in bpy.data.materials if m.name.startswith("MAT_")])
print(f"[mat_build] {n_mat} materials, {len(bpy.data.node_groups)} node groups, {len(bpy.data.images)} images, {len(coll.objects)} test objects")
common.save_blend(common.ASSETS / "materials.blend")
