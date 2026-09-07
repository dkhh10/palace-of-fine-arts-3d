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
    r = t.fract(t.add(r, t.fract(t.mul(iattr.outputs["Fac"], 0.6180339887))))
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
    m1 = t.smoothstep(n1, 0.56, 0.66)
    m2 = t.smoothstep(n2, 0.6, 0.7)
    # drips fade in and out along their length
    fade = t.maprange(t.noise(t.combxyz(t.mul(x, I["Scale"]), t.mul(y, I["Scale"]), t.mul(z, 0.7)), 1.0, detail=2), 0.35, 0.65, 0.2, 1.0)
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
                              [("Band", "FLOAT", 0.0), ("Effl", "FLOAT", 0.0)])
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
    t.link(band, go.inputs["Band"])
    t.link(effl, go.inputs["Effl"])
    ML.auto_layout(ng)
    return ng


CONCRETE_INPUTS = [
    ("Base Color", "COLOR", (0.42, 0.29, 0.17, 1.0)),
    ("Grey Color", "COLOR", (0.30, 0.25, 0.19, 1.0)),
    ("Grey Drift", "FACTOR", 0.35, 0, 1),
    ("Grey Below Z", "FLOAT", 3.0), ("Grey Above Z", "FLOAT", 10.0),
    ("Tone Variation", "FACTOR", 0.22, 0, 1),
    ("Block Size", "FLOAT", 2.6, 0.1, 50), ("Blotch Size", "FLOAT", 3.0, 0.1, 50),
    ("Detail Color", "COLOR", (0.46, 0.46, 0.46, 1.0)), ("Detail Mean", "FLOAT", 0.46, 0.01, 1),
    ("Detail Rough", "FLOAT", 0.7, 0, 1), ("Detail Height", "FLOAT", 0.5, 0, 1), ("Detail Strength", "FACTOR", 0.6, 0, 1),
    ("Streaks", "FACTOR", 0.55, 0, 1), ("Streak Scale", "FLOAT", 1.5, 0.1, 20), ("Streak Length", "FLOAT", 3.0, 0.2, 30),
    ("Ledge Distance", "FLOAT", 2.5, 0.1, 20), ("Ledge Weight", "FACTOR", 0.75, 0, 1), ("Streak Shade Bias", "FACTOR", 0.0, 0, 1),
    ("Algae", "FACTOR", 0.0, 0, 1), ("Algae Z", "FLOAT", WATER_Z), ("Algae Height", "FLOAT", 0.6, 0.05, 5),
    ("Efflorescence", "FACTOR", 1.0, 0, 3),
    ("Patches", "FACTOR", 0.25, 0, 1),
    ("Edge Wear", "FACTOR", 0.45, 0, 1), ("Edge Radius", "FLOAT", 0.03, 0.001, 0.5),
    ("Recess Dirt", "FACTOR", 0.55, 0, 1), ("Recess Distance", "FLOAT", 0.4, 0.02, 5), ("Extra Dirt", "FACTOR", 0.0, 0, 1),
    ("Underside Dirt", "FACTOR", 0.0, 0, 1),
    ("Roughness", "FLOAT", 0.78, 0, 1), ("Roughness Variation", "FLOAT", 0.12, 0, 1),
    ("Bump", "FLOAT", 0.35, 0, 3),
    ("Pour Lines", "FACTOR", 0.35, 0, 1), ("Pour Spacing", "FLOAT", 0.6, 0.05, 10),
    ("Grid Joints", "FACTOR", 0.0, 0, 1), ("Grid Size", "FLOAT", 1.5, 0.1, 20),
    ("Bird Droppings", "FACTOR", 0.0, 0, 1),
    ("Instance Variation", "FACTOR", 1.0, 0, 2),
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
    hue = t.madd(t.sub(r2, 0.5), t.mul(0.06, IV), 0.5)
    val = t.madd(t.sub(r3, 0.5), t.mul(0.16, IV), 1.0)
    c = t.hsv(I["Base Color"], hue=hue, val=val)
    # 2. cast-block tone steps (axis-aligned Chebychev cells) + 3. soft pour blotches + 4. fine speckle
    vb = t.voronoi(P, t.div(1.0, I["Block Size"]), feature="F1", distance="CHEBYCHEV", randomness=0.3)
    cell = t.sepxyz(vb.outputs["Color"])[0]
    tone_b = t.maprange(cell, 0.0, 1.0, t.sub(1.0, TV), t.add(1.0, TV))
    nb = t.noise(P, t.div(1.0, I["Blotch Size"]), detail=3, rough=0.55)
    tone_n = t.maprange(nb, 0.3, 0.7, t.sub(1.0, t.mul(TV, 0.8)), t.add(1.0, t.mul(TV, 0.8)))
    ns = t.noise(P, 30.0, detail=4, rough=0.7)
    tone_s = t.maprange(ns, 0.35, 0.65, 0.93, 1.07)
    # 5. photo detail (luminance only, normalised around its mean)
    dn = t.div(t.luminance(I["Detail Color"]), I["Detail Mean"])
    tone_d = t.mixf(I["Detail Strength"], 1.0, dn)
    tone = t.mul(t.mul(tone_b, tone_n), t.mul(tone_s, tone_d))
    c = t.vscale(c, tone)
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
    vp = t.voronoi(t.vadd(P, (0.5, 0.5, 0.5)), 1.0 / 1.6, feature="F1", distance="CHEBYCHEV", randomness=0.6)
    pr = t.sepxyz(vp.outputs["Color"])[1]
    thr = t.sub(1.0, t.mul(I["Patches"], 0.3))
    pm = t.maprange(pr, thr, t.add(thr, 0.004), 0.0, 1.0)
    pm = t.mul(pm, t.math("GREATER_THAN", I["Patches"], 0.001))
    c = t.mix(pm, c, t.hsv(c, sat=0.8, val=1.14))
    # 9. rain streaks
    st = t.group(G["streaks"], Offset=off, Scale=I["Streak Scale"], Length=I["Streak Length"], Normal=N,
                 **{"Ledge Distance": I["Ledge Distance"], "Ledge Weight": I["Ledge Weight"], "Shade Bias": I["Streak Shade Bias"]})
    smask = t.mul(st.outputs["Mask"], I["Streaks"])
    c = t.mix(smask, c, t.vmul(c, (0.36, 0.37, 0.31)))
    # 10. recess dirt (AO) + baked/extra dirt + underside soot
    ao = t.ao(distance=I["Recess Distance"], samples=8, normal=N)
    dirt = t.clamp01(t.add(t.mul(t.sub(1.0, ao), I["Recess Dirt"]), I["Extra Dirt"]))
    under = t.mul(t.maprange(nz, -0.15, -0.8, 0.0, 1.0), I["Underside Dirt"])
    dirt_all = t.clamp01(t.add(dirt, t.mul(under, 0.6)))
    c = t.mix(dirt_all, c, t.vmul(c, (0.5, 0.47, 0.42)))
    # 11. edge wear (lighter, cleaner, smoother on convex arrises)
    em = t.mul(t.group(G["edge"], Radius=I["Edge Radius"], Normal=N).outputs["Mask"], I["Edge Wear"])
    c = t.mix(em, c, t.hsv(c, sat=0.85, val=1.22))
    # 12. algae band + efflorescence
    al = t.group(G["algae"], Offset=off, Height=I["Algae Height"], **{"Band Z": I["Algae Z"]})
    band = t.mul(al.outputs["Band"], I["Algae"])
    effl = t.mul(t.mul(al.outputs["Effl"], I["Algae"]), I["Efflorescence"])
    effl = t.math("ADD", effl, 0.0, clamp=True)
    # salt bloom: a chalky, slightly crusty white-grey wash just above the tide line (podium, rostra, rip-rap)
    c = t.mix(t.mul(effl, 0.80), c, t.mix(0.85, c, (0.66, 0.635, 0.575)))
    c = t.mix(band, c, t.mix(0.35, (0.045, 0.07, 0.04), c))
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

    t.link(c, go.inputs["Color"])
    t.link(rough, go.inputs["Roughness"])
    t.link(normal, go.inputs["Normal"])
    t.link(smask, go.inputs["Streak Mask"])
    t.link(dirt_all, go.inputs["Dirt Mask"])
    t.link(em, go.inputs["Edge Mask"])
    t.link(st.outputs["Ledge"], go.inputs["Ledge Mask"])
    t.link(tone, go.inputs["Tone"])
    t.link(band, go.inputs["Algae Mask"])
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
    """Urethane roof membrane: meridional lap seams, radial rain streaks, moss on the north flank, grime ring at the base.
    Object space: origin on the dome axis (any z); world normal for orientation."""
    ng, t, gi, go = new_group("PFA_dome",
                              [("Base Color", "COLOR", (0.70, 0.66, 0.58, 1.0)), ("Streak Color", "COLOR", (0.50, 0.52, 0.52, 1.0)),
                               ("Moss Color", "COLOR", (0.42, 0.47, 0.40, 1.0)), ("Grime Color", "COLOR", (0.20, 0.13, 0.06, 1.0)),
                               ("Seams", "FLOAT", 48.0, 4, 400), ("Seam Width", "FLOAT", 0.05, 0.005, 0.5),
                               ("Streaks", "FACTOR", 0.7, 0, 1), ("Moss", "FACTOR", 0.6, 0, 1), ("Grime", "FACTOR", 0.8, 0, 1),
                               ("Base Normal Z", "FLOAT", 0.66), ("Roughness", "FLOAT", 0.35, 0, 1), ("Bump", "FLOAT", 0.3, 0, 3),
                               ("Seed", "FLOAT", 0.0), ("Normal", "VECTOR", (0, 0, 1))],
                              [("Color", "COLOR", None), ("Roughness", "FLOAT", 0.0), ("Normal", "VECTOR", (0, 0, 1)), ("Coat", "FLOAT", 0.0)])
    I = gi.outputs
    inst = t.group(G["instance"], Seed=I["Seed"])
    off = inst.outputs["Offset"]
    P = t.texcoord().outputs["Object"]
    px, py, pz = t.sepxyz(P)
    N = I["Normal"]
    nx, ny, nz = t.sepxyz(N)
    ang = t.math("ARCTAN2", py, px)                                   # -pi..pi
    r = t.math("SQRT", t.add(t.mul(px, px), t.mul(py, py)))
    # seams: nearest meridian, distance in metres along the parallel
    s = t.fract(t.madd(t.div(ang, 2 * math.pi), I["Seams"], 0.5))
    seam_d = t.mul(t.mul(t.minimum(s, t.sub(1.0, s)), t.div(2 * math.pi, I["Seams"])), r)
    seam = t.maprange(seam_d, t.mul(I["Seam Width"], 0.5), I["Seam Width"], 1.0, 0.0)
    seam_lap = t.maprange(seam_d, 0.0, I["Seam Width"], 1.0, 0.0)
    # radial streaks: polar coords, stretched along the meridian; stronger where the surface is steeper
    u = t.mul(ang, 16.0)                                               # ~ metres around at the base
    sv = t.vadd(t.combxyz(t.mul(u, 2.6), t.mul(pz, 0.05), 0.0), t.vscale(off, 0.01))
    n1 = t.noise(sv, 1.0, detail=3, rough=0.65)
    n2 = t.noise(t.vscale(sv, 2.6), 1.0, detail=2, rough=0.6)
    fade = t.maprange(t.noise(t.combxyz(t.mul(u, 1.6), t.mul(pz, 0.5), 0.0), 1.0, detail=2), 0.35, 0.65, 0.3, 1.0)
    smask = t.mul(t.clamp01(t.madd(t.smoothstep(n2, 0.58, 0.7), 0.6, t.smoothstep(n1, 0.54, 0.66))), fade)
    steep = t.maprange(nz, 0.97, t.add(I["Base Normal Z"], 0.04), 0.15, 1.0)
    smask = t.mul(t.mul(smask, steep), I["Streaks"])
    # seams collect dirt too
    smask = t.clamp01(t.add(smask, t.mul(seam, t.mul(0.35, I["Streaks"]))))
    # moss: north flank (-X), patchy
    north = t.maprange(nx, -0.15, -0.6, 0.0, 1.0)
    mp = t.smoothstep(t.noise(t.vadd(P, off), 1.8, detail=3, rough=0.6), 0.56, 0.68)
    moss = t.mul(t.mul(t.mul(north, mp), steep), I["Moss"])
    # grime ring at the base + gentle darkening of the lower flank
    ring_n = t.maprange(t.noise(t.vadd(P, off), 4.0, detail=2), 0.35, 0.65, -0.006, 0.006)
    grime = t.mul(t.maprange(nz, t.add(t.add(I["Base Normal Z"], 0.02), ring_n), t.add(I["Base Normal Z"], 0.004), 0.0, 1.0), I["Grime"])
    lower = t.mul(t.maprange(nz, 0.9, t.add(I["Base Normal Z"], 0.03), 0.0, 0.3), I["Grime"])
    # tone variation
    tv = t.maprange(t.noise(t.vadd(P, off), 0.25, detail=2), 0.35, 0.65, 0.94, 1.06)
    c = t.vscale(I["Base Color"], tv)
    c = t.mix(smask, c, t.vscale(I["Streak Color"], tv))
    c = t.mix(moss, c, I["Moss Color"])
    c = t.mix(lower, c, t.vmul(c, (0.75, 0.72, 0.68)))
    c = t.mix(grime, c, I["Grime Color"])
    rough = I["Roughness"]
    rough = t.add(rough, t.mul(smask, 0.22))
    rough = t.mixf(moss, rough, 0.75)
    rough = t.mixf(grime, rough, 0.6)
    rough = t.add(rough, t.mul(t.sub(t.noise(P, 3.0, detail=2), 0.5), 0.08))
    coat = t.mul(t.sub(1.0, t.clamp01(t.add(t.add(smask, moss), grime))), 0.4)
    # bump: seam lap ridge + fine membrane texture + streak grime
    h = t.add(t.mul(seam_lap, 0.6), t.mul(t.noise(P, 25.0, detail=3), 0.15))
    normal = t.bump(h, strength=I["Bump"], distance=0.01, normal=N)
    t.link(c, go.inputs["Color"]); t.link(t.math("ADD", rough, 0.0, clamp=True), go.inputs["Roughness"])
    t.link(normal, go.inputs["Normal"]); t.link(coat, go.inputs["Coat"])
    ML.auto_layout(ng)
    return ng


G["instance"] = build_group_instance()
G["edge"] = build_group_edge()
G["streaks"] = build_group_streaks()
G["algae"] = build_group_algae()
G["concrete"] = build_group_concrete()
G["column"] = build_group_column()
G["dome"] = build_group_dome()


# =============================================================================== materials
def concrete_material(name, tex_set, seed, params, specular=0.4, column=None, baked=False, extra=None):
    m = ML.new_material(name)
    t = Tree(m.node_tree)
    inst = t.group(G["instance"], Seed=seed)
    P = t.vadd(t.texcoord().outputs["Object"], inst.outputs["Offset"])
    tex = t.image_set(tex_set, P, maps=("diff", "rough", "disp"))
    geo = t.geometry()
    N = geo.outputs["Normal"]
    if baked:
        # hooks for ORN's baked maps (see docs/materials_notes.md): mat_lib.wire_baked_maps() fills these.
        nm_img = t.new("ShaderNodeTexImage"); nm_img.name = nm_img.label = "BAKED_NORMAL"
        ao_img = t.new("ShaderNodeTexImage"); ao_img.name = ao_img.label = "BAKED_AO"
        w = t.value(0.0, "BAKED_WEIGHT")
        nmap = t.normal_map(nm_img.outputs["Color"], strength=1.0)
        N = t.mixv(w, geo.outputs["Normal"], nmap)
        extra = dict(extra or {})
        extra["Extra Dirt"] = t.mul(w, t.mul(t.sub(1.0, ao_img.outputs["Color"]), 0.6))
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
    # walls, entablature, attic, drum (upper rotunda): the reference ochre
    concrete_material("MAT_concrete_ochre", "concrete_wall_008", 1.0, {
        "Base Color": C(0.575, 0.363, 0.082), "Grey Color": C(0.37, 0.272, 0.105), "Grey Drift": 0.28,
        "Grey Below Z": 3.0, "Grey Above Z": 10.0, "Tone Variation": 0.08, "Block Size": 3.6, "Blotch Size": 1.8,
        "Detail Strength": 0.85, "Streaks": 1.0, "Streak Scale": 2.5, "Streak Length": 10.0, "Ledge Distance": 3.0, "Ledge Weight": 0.55,
        "Patches": 0.25, "Edge Wear": 0.45, "Edge Radius": 0.03, "Recess Dirt": 0.55, "Recess Distance": 0.4,
        "Roughness": 0.78, "Roughness Variation": 0.12, "Bump": 0.35, "Pour Lines": 0.35, "Pour Spacing": 0.6})
    # podium, pedestals, rostra, platform: greyer, damper, algae band at the water line
    concrete_material("MAT_concrete_podium", "concrete_wall_007", 2.0, {
        "Base Color": C(0.445, 0.333, 0.140), "Grey Color": C(0.35, 0.288, 0.165), "Grey Drift": 0.42,
        "Grey Below Z": 0.5, "Grey Above Z": 5.0, "Tone Variation": 0.08, "Block Size": 2.4, "Blotch Size": 2.5,
        "Detail Strength": 0.6, "Streaks": 0.55, "Streak Scale": 2.5, "Streak Length": 6.0, "Ledge Distance": 2.0, "Ledge Weight": 0.5,
        "Algae": 1.0, "Algae Z": WATER_Z, "Algae Height": 0.6, "Efflorescence": 1.7,
        "Patches": 0.35, "Edge Wear": 0.5, "Edge Radius": 0.03, "Recess Dirt": 0.6, "Recess Distance": 0.4,
        "Roughness": 0.8, "Roughness Variation": 0.12, "Bump": 0.4, "Pour Lines": 0.15, "Pour Spacing": 0.9})
    # colonnade concrete: same ochre, the strongest black-green streaking, worse on the shade (north) side
    concrete_material("MAT_concrete_colonnade", "concrete_wall_007", 3.0, {
        "Base Color": C(0.585, 0.368, 0.082), "Grey Color": C(0.34, 0.262, 0.112), "Grey Drift": 0.25,
        "Grey Below Z": 1.0, "Grey Above Z": 6.0, "Tone Variation": 0.08, "Block Size": 3.0, "Blotch Size": 3.0,
        "Detail Strength": 0.55, "Streaks": 0.8, "Streak Scale": 3.0, "Streak Length": 12.0, "Ledge Distance": 2.5, "Ledge Weight": 0.4,
        "Streak Shade Bias": 0.6,
        "Patches": 0.2, "Edge Wear": 0.45, "Edge Radius": 0.03, "Recess Dirt": 0.55, "Recess Distance": 0.4,
        "Roughness": 0.78, "Roughness Variation": 0.12, "Bump": 0.35, "Pour Lines": 0.25, "Pour Spacing": 0.6})
    # vault soffits, inner arch rings: greyer, dustier, soot on the undersides
    concrete_material("MAT_concrete_inner", "concrete_wall_008", 4.0, {
        "Base Color": C(0.425, 0.297, 0.098), "Grey Color": C(0.33, 0.262, 0.145), "Grey Drift": 0.40,
        "Grey Below Z": 40.0, "Grey Above Z": 60.0, "Tone Variation": 0.08, "Block Size": 3.0, "Blotch Size": 2.5,
        "Detail Strength": 0.5, "Streaks": 0.3, "Streak Scale": 2.5, "Streak Length": 6.0, "Ledge Distance": 2.0, "Ledge Weight": 0.6,
        "Patches": 0.1, "Edge Wear": 0.4, "Edge Radius": 0.03, "Recess Dirt": 0.7, "Recess Distance": 0.5, "Underside Dirt": 0.6,
        "Roughness": 0.85, "Roughness Variation": 0.1, "Bump": 0.35, "Pour Lines": 0.4, "Pour Spacing": 0.6})
    # ornament: capitals, maidens, urns, panels -- dust in the hollows, worn arrises, per-instance variation, baked-map hooks
    concrete_material("MAT_ornament_concrete", "concrete_wall_008", 5.0, {
        "Base Color": C(0.575, 0.363, 0.082), "Grey Color": C(0.37, 0.272, 0.105), "Grey Drift": 0.20,
        "Grey Below Z": 2.0, "Grey Above Z": 9.0, "Tone Variation": 0.12, "Block Size": 1.2, "Blotch Size": 0.8,
        "Detail Strength": 0.4, "Streaks": 0.35, "Streak Scale": 5.0, "Streak Length": 4.0, "Ledge Distance": 1.0, "Ledge Weight": 0.5,
        "Patches": 0.0, "Edge Wear": 0.5, "Edge Radius": 0.02, "Recess Dirt": 0.75, "Recess Distance": 0.3,
        "Roughness": 0.8, "Roughness Variation": 0.1, "Bump": 0.3, "Pour Lines": 0.0, "Bird Droppings": 0.12,
        "Instance Variation": 1.0}, baked=True)
    # the 16 fluted pink shafts: dusty terracotta rose, integral pigment washing out to mauve-grey
    concrete_material("MAT_column_rose", "concrete_wall_008", 6.0, {
        "Base Color": C(0.455, 0.190, 0.098), "Grey Color": C(0.37, 0.215, 0.155), "Grey Drift": 0.22,
        "Grey Below Z": -100.0, "Grey Above Z": -99.0, "Tone Variation": 0.12, "Block Size": 3.2, "Blotch Size": 1.5,
        "Detail Strength": 0.45, "Streaks": 0.0, "Patches": 0.0, "Edge Wear": 0.5, "Edge Radius": 0.02,
        "Recess Dirt": 0.6, "Recess Distance": 0.25, "Roughness": 0.72, "Roughness Variation": 0.1, "Bump": 0.3, "Pour Lines": 0.0},
        column={"Wash Color": C(0.42, 0.24, 0.21), "Wash": 0.55, "Drum Height": 3.25, "Drum Variation": 0.07, "Top Z": 16.3, "Top Darkening": 0.35})
    # the 8 inner tan columns (and their blocks)
    concrete_material("MAT_column_tan_inner", "concrete_wall_008", 7.0, {
        "Base Color": C(0.530, 0.352, 0.100), "Grey Color": C(0.40, 0.307, 0.148), "Grey Drift": 0.18,
        "Grey Below Z": -100.0, "Grey Above Z": -99.0, "Tone Variation": 0.15, "Block Size": 3.0, "Blotch Size": 1.5,
        "Detail Strength": 0.5, "Streaks": 0.0, "Patches": 0.0, "Edge Wear": 0.45, "Edge Radius": 0.02,
        "Recess Dirt": 0.6, "Recess Distance": 0.25, "Roughness": 0.78, "Roughness Variation": 0.1, "Bump": 0.3, "Pour Lines": 0.0},
        column={"Wash Color": C(0.40, 0.33, 0.26), "Wash": 0.35, "Drum Height": 3.0, "Drum Variation": 0.06, "Top Z": 11.0, "Top Darkening": 0.3})
    # platform floor / steps: light neutral concrete slabs with joints
    concrete_material("MAT_paving", "concrete_wall_008", 8.0, {
        "Base Color": C(0.50, 0.475, 0.405), "Grey Color": C(0.37, 0.355, 0.305), "Grey Drift": 0.28,
        "Grey Below Z": -100.0, "Grey Above Z": -99.0, "Tone Variation": 0.12, "Block Size": 1.5, "Blotch Size": 4.0,
        "Detail Strength": 0.5, "Streaks": 0.0, "Patches": 0.2, "Edge Wear": 0.3, "Edge Radius": 0.02,
        "Recess Dirt": 0.5, "Recess Distance": 0.3, "Roughness": 0.7, "Roughness Variation": 0.12, "Bump": 0.3, "Pour Lines": 0.0,
        "Grid Joints": 0.8, "Grid Size": 1.5}, specular=0.45)
    # coffered plaster saucer (only bounce-lit)
    concrete_material("MAT_plaster_ceiling", "concrete_wall_008", 9.0, {
        "Base Color": C(0.565, 0.435, 0.215), "Grey Color": C(0.39, 0.30, 0.155), "Grey Drift": 0.18,
        "Grey Below Z": -100.0, "Grey Above Z": -99.0, "Tone Variation": 0.12, "Block Size": 1.5, "Blotch Size": 1.0,
        "Detail Strength": 0.3, "Streaks": 0.0, "Patches": 0.0, "Edge Wear": 0.3, "Edge Radius": 0.02,
        "Recess Dirt": 0.7, "Recess Distance": 0.4, "Roughness": 0.9, "Roughness Variation": 0.05, "Bump": 0.25, "Pour Lines": 0.0}, specular=0.3)
    # bronze-brown guilloche band on the drum
    concrete_material("MAT_drum_band", "concrete_wall_007", 10.0, {
        "Base Color": C(0.28, 0.18, 0.09), "Grey Color": C(0.22, 0.17, 0.11), "Grey Drift": 0.3,
        "Grey Below Z": -100.0, "Grey Above Z": -99.0, "Tone Variation": 0.15, "Block Size": 1.0, "Blotch Size": 1.0,
        "Detail Strength": 0.4, "Streaks": 0.3, "Streak Scale": 3.0, "Streak Length": 1.5, "Ledge Weight": 0.4,
        "Patches": 0.0, "Edge Wear": 0.5, "Edge Radius": 0.02, "Recess Dirt": 0.7, "Recess Distance": 0.25,
        "Roughness": 0.8, "Roughness Variation": 0.1, "Bump": 0.3, "Pour Lines": 0.0})
    # exhibition hall / distant massing: buff stucco, coarse
    concrete_material("MAT_backdrop_building", "concrete_wall_008", 11.0, {
        "Base Color": C(0.555, 0.445, 0.245), "Grey Color": C(0.41, 0.35, 0.235), "Grey Drift": 0.28,
        "Grey Below Z": 1.0, "Grey Above Z": 6.0, "Tone Variation": 0.15, "Block Size": 4.0, "Blotch Size": 6.0,
        "Detail Strength": 0.3, "Streaks": 0.4, "Streak Scale": 1.0, "Streak Length": 5.0, "Ledge Weight": 0.6,
        "Patches": 0.1, "Edge Wear": 0.2, "Edge Radius": 0.03, "Recess Dirt": 0.4, "Recess Distance": 0.5,
        "Roughness": 0.85, "Roughness Variation": 0.1, "Bump": 0.25, "Pour Lines": 0.0})


def build_dome():
    m = ML.new_material("MAT_dome_membrane")
    t = Tree(m.node_tree)
    N = t.geometry().outputs["Normal"]
    g = t.group(G["dome"], Normal=N, **{"Base Color": C(0.70, 0.645, 0.535), "Streak Color": C(0.50, 0.50, 0.47), "Moss Color": C(0.34, 0.42, 0.28),
                                        "Grime Color": C(0.20, 0.13, 0.06), "Seams": 48.0, "Seam Width": 0.05, "Streaks": 0.8, "Moss": 0.3,
                                        "Grime": 0.8, "Base Normal Z": 0.66, "Roughness": 0.50, "Bump": 0.3, "Seed": 12.0})
    bsdf = t.principled(**{"Base Color": g.outputs["Color"], "Roughness": g.outputs["Roughness"], "Normal": g.outputs["Normal"],
                           "Specular IOR Level": 0.40, "Coat Weight": t.mul(g.outputs["Coat"], 0.35), "Coat Roughness": 0.35, "Coat Normal": g.outputs["Normal"]})
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
    ripple_lod = t.maprange(depth, 30.0, 180.0, 1.0, 0.13)
    far_rough = t.maprange(depth, 45.0, 200.0, 0.0, 0.030)
    # anisotropy: crests run ~3x longer along X (across the hero view), so the reflection breaks into vertical streaks
    Pa = t.combxyz(t.mul(wx, 0.33), wy, 0.0)
    Ps = t.combxyz(t.mul(wx, 0.55), wy, 0.0)
    h1 = t.noise(Pa, 3.3, detail=3, rough=0.55, w=t.mul(time, 1.0))          # 0.3 m ripples
    h2 = t.noise(Ps, 0.33, detail=2, rough=0.5, w=t.mul(time, 0.3))          # 3 m swell
    h3 = t.noise(Pa, 9.0, detail=2, rough=0.5, w=t.mul(time, 1.7))           # 0.1 m capillary
    h = t.add(t.add(t.mul(h1, 0.6), h2), t.mul(h3, 0.18))
    # calmer patches (wind shadow) so the reflection is glassy in places
    calm = t.maprange(t.noise(t.combxyz(wx, wy, 0.0), 0.04, detail=2), 0.35, 0.65, 0.45, 1.0)
    normal = t.bump(h, strength=t.mul(t.mul(0.45, calm), ripple_lod), distance=0.03, normal=N)
    rough = t.add(t.maprange(t.noise(t.combxyz(wx, wy, 0.0), 0.12, detail=2), 0.3, 0.7, 0.02, 0.055), far_rough)
    # green murk body. Transmission 0.55 (not 1.0) so the material reads the same on ENV's single water plane as it
    # does inside a closed lagoon volume: the opaque 45 % is a green murk lambertian that picks up sky and sun, the
    # transmissive 55 % carries the volume when there is one. Fresnel reflection is on top of both.
    murk_far = t.maprange(t.noise(t.combxyz(wx, wy, 0.0), 0.05, detail=2), 0.35, 0.65, 0.0, 1.0)
    murk = t.mix(murk_far, C(0.042, 0.084, 0.055), C(0.078, 0.140, 0.086))
    bsdf = t.principled(**{"Base Color": murk, "Roughness": rough, "IOR": 1.333, "Transmission Weight": 0.45,
                           "Specular IOR Level": 0.5, "Normal": normal})
    # one Principled Volume (absorption + weak scatter): Absorption + Scatter + Add Shader pushed Cycles past its
    # 64-closure budget (76) and closures were silently dropped. extinction = density * (color + 1 - absorption_color):
    # scatter (0.117, 0.234, 0.144)/m, absorption (0.36, 0.135, 0.36)/m -> single-scatter albedo 0.25/0.63/0.29, i.e. a
    # LIT green murk (the v1 numbers gave albedo 0.07-0.15, which made a closed lagoon volume read black).
    vol = t.new("ShaderNodeVolumePrincipled")
    t.plug(vol.inputs["Color"], C(0.13, 0.26, 0.16)); t.plug(vol.inputs["Density"], 0.9)
    t.plug(vol.inputs["Absorption Color"], C(0.60, 0.85, 0.60)); t.plug(vol.inputs["Anisotropy"], 0.3)
    t.output(surface=bsdf.outputs[0], volume=vol.outputs[0], target="CYCLES")
    # Eevee cannot reflect through its transmission path (tested: no Fresnel reflection with or without raytraced
    # refraction), so Eevee gets an opaque dark-murk surface with the same ripples: reflections come from raytracing/probes.
    # (Diffuse + Glossy by a Fresnel node rather than a second Principled: Cycles counts every closure node in the
    #  tree against its 64-closure budget, two Principled BSDFs blew it to 76.)
    murk_e = t.mix(murk_far, C(0.050, 0.098, 0.064), C(0.088, 0.155, 0.096))
    dif = t.new("ShaderNodeBsdfDiffuse"); t.plug(dif.inputs["Color"], murk_e); t.plug(dif.inputs["Normal"], normal)
    glo = t.new("ShaderNodeBsdfGlossy"); t.plug(glo.inputs["Color"], C(1.0, 1.0, 1.0)); t.plug(glo.inputs["Roughness"], rough); t.plug(glo.inputs["Normal"], normal)
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
    m = ML.new_material("MAT_backdrop_forest")
    t = Tree(m.node_tree)
    W = t.geometry().outputs["Position"]
    N = t.geometry().outputs["Normal"]
    crowns = t.voronoi(W, 1.0 / 9.0, feature="SMOOTH_F1", randomness=1.0)
    cr = t.sepxyz(crowns.outputs["Color"])[0]
    c = t.mix(cr, C(0.035, 0.07, 0.03), C(0.07, 0.11, 0.045))
    haze = t.maprange(t.noise(W, 0.02, detail=2), 0.35, 0.65, 0.85, 1.15)
    c = t.vscale(c, haze)
    normal = t.bump(t.add(crowns.outputs["Distance"], t.mul(t.noise(W, 0.8, detail=3), 0.4)), strength=0.7, distance=0.6, normal=N)
    t.output(surface=t.principled(**{"Base Color": c, "Roughness": 0.9, "Specular IOR Level": 0.15, "Normal": normal}).outputs[0])
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
    bsdf = t.principled(**{"Base Color": c, "Roughness": 0.85, "Specular IOR Level": 0.2, "Normal": normal, "Sheen Weight": 0.1})
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
    bsdf = t.principled(**{"Base Color": c, "Roughness": t.add(t.mul(t.sub(tex["rough"], 0.5), 0.3), 0.9), "Normal": normal, "Specular IOR Level": 0.25})
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
    bsdf = t.principled(**{"Base Color": c, "Roughness": t.add(t.mul(t.sub(tex["rough"], 0.5), 0.3), 0.85), "Normal": normal, "Specular IOR Level": 0.3})
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
    al = t.group(G["algae"], Offset=inst.outputs["Offset"], Height=0.35, **{"Band Z": WATER_Z + 0.05})
    band = al.outputs["Band"]
    c = t.mix(band, c, C(0.06, 0.07, 0.05))
    ao = t.ao(distance=0.3, samples=6)
    c = t.mix(t.mul(t.sub(1.0, ao), 0.5), c, t.vmul(c, (0.55, 0.53, 0.5)))
    normal = t.bump(tex["disp"], strength=0.6, distance=0.02, normal=N)
    r = t.mixf(band, t.add(t.mul(t.sub(tex["rough"], 0.5), 0.3), 0.8), 0.4)
    bsdf = t.principled(**{"Base Color": c, "Roughness": r, "Normal": normal, "Specular IOR Level": 0.35})
    t.output(surface=bsdf.outputs[0])
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
    leaf_material("MAT_shrub", "leaves_shrub", (0.8, 1.1, 0.5), rough=0.5, hue_var=0.08, val_var=0.4, seed=23.0, translucency=0.2, spec=0.4)
    leaf_material("MAT_reeds", "reeds", (0.9, 1.0, 0.5), rough=0.6, hue_var=0.06, val_var=0.4, seed=26.0, translucency=0.35, cluster_var=0.35)
    build_extra_env()
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
    cap = capital_proxy(f"MAT_test_capital_v{i + 1}", (-6.9 + i * 1.15, -7.0, GZ + 1.55), "MAT_ornament_concrete")
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
