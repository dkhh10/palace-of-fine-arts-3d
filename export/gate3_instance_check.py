"""Gate 4 sanity check 1: a shaded colonnade placement vs a sunlit lawn placement, against the GROUND.

    scripts/blender_run.sh 600 -- --background export/out/gate3/gate3_bake.blend \
        --python-exit-code 1 --python export/gate3_instance_check.py

No render, no GPU: it only ray-casts. For every shrub placement in instance_irradiance.json it drops a ray
onto the ground, finds which lightmapped ground asset was hit, reads that asset's UV2 at the hit point and
samples the asset's baked EXR there. The ground texel and the placement value are in the SAME units
(scene-linear irradiance / pi), so the shade/sun ratio measured on the shrubs must track the ratio measured
on the ground under them. Writes out/gate3/instance_check.json.
"""
import bpy
import json
import os
import sys
import time

import numpy as np
from mathutils import Vector
from mathutils.geometry import barycentric_transform, intersect_point_tri

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate3_common as g3      # noqa: E402

LUM = np.array([0.2126, 0.7152, 0.0722])
doc = json.loads((g3.OUT / "instance_irradiance.json").read_text())
jobs = {j["id"]: j for j in g3.read_jobs()["jobs"]}
uv2_of = {j["object"]: j["uv2"] for j in jobs.values() if j["kind"] in ("own", "own_gate1uv2")}
exr_cache, dg = {}, bpy.context.evaluated_depsgraph_get()


def ground_texel(hit_ob, hit_p, face):
    """The baked lightmap value under `hit_p`, or None if that object has no own map / no EXR."""
    uvname = uv2_of.get(hit_ob.name)
    if uvname is None:
        return None, "no own lightmap"
    p = g3.TEX / f"gate3_lm_{hit_ob.name}.exr"
    if not p.exists():
        return None, f"missing {p.name}"
    if p.name not in exr_cache:
        exr_cache[p.name] = g3.read_exr32(p)
    a = exr_cache[p.name]                       # bottom-up, (h, w, 3)
    me = hit_ob.data
    lay = me.uv_layers.get(uvname)
    if lay is None:
        return None, f"no UV layer {uvname}"
    me.calc_loop_triangles()
    local = hit_ob.matrix_world.inverted() @ hit_p
    for lt in me.loop_triangles:
        if lt.polygon_index != face:
            continue
        v = [me.vertices[i].co for i in lt.vertices]
        if intersect_point_tri(local, *v) is None:
            continue
        uvs = [Vector((*lay.uv[li].vector[:], 0.0)) for li in lt.loops] \
            if hasattr(lay, "uv") and hasattr(lay.uv[lt.loops[0]], "vector") \
            else [Vector((*lay.data[li].uv[:], 0.0)) for li in lt.loops]
        uv = barycentric_transform(local, v[0], v[1], v[2], uvs[0], uvs[1], uvs[2])
        h, w = a.shape[:2]
        col = min(max(int(uv.x * w), 0), w - 1)
        row = min(max(int(uv.y * h), 0), h - 1)
        return [float(x) for x in a[row, col]], f"{hit_ob.name}[{row},{col}] of {w}x{h}"
    return None, "hit point outside every loop triangle of the face"


rows = []
t0 = time.time()
for mesh, m in doc["meshes"].items():
    for p in m["placements"]:
        ob = bpy.data.objects.get(p["object"])
        if ob is None:
            continue
        o = ob.matrix_world.translation
        ok, loc, _n, face, hit_ob, _mw = bpy.context.scene.ray_cast(
            dg, Vector((o.x, o.y, o.z + 0.60)), Vector((0.0, 0.0, -1.0)), distance=6.0)
        if not ok or hit_ob is None:
            continue
        g, why = ground_texel(hit_ob, loc, face)
        rows.append(dict(object=p["object"], mesh=mesh, rgb=p["rgb"],
                         lum=float(np.array(p["rgb"]) @ LUM), ground_ob=hit_ob.name,
                         ground=g, ground_lum=(float(np.array(g) @ LUM) if g else None), where=why,
                         z=round(float(o.z), 2)))
print(f"[gate4] ray-cast {len(rows)} placements in {time.time() - t0:.0f}s")

with_g = [r for r in rows if r["ground_lum"] is not None]
# Check 1 of the brief. No shrub's ray lands on the colonnade walk (the 1 379 cards sit on the terrain,
# the riprap, the lagoon bed and the podium), so "shaded" is taken as it is measured on the ground itself:
# the placement standing on the DARKEST lightmapped ground texel - which is what colonnade / tree shade is
# in a baked map - against the one on the brightest. Both single pair and decile means, the latter because
# one texel of one card is noise and the decile is not.
lit = sorted([r for r in with_g if "terrain_ground" in r["ground_ob"] or "paving" in r["ground_ob"]
              or "colonnade_walk" in r["ground_ob"]], key=lambda r: r["ground_lum"])
pick = {}
if len(lit) >= 20:
    s_, t_ = lit[0], lit[-1]
    k = max(len(lit) // 10, 5)
    dec_lo, dec_hi = lit[:k], lit[-k:]

    def mean(rs, key):
        return float(np.mean([r[key] for r in rs]))

    pick = dict(
        shaded=dict({kk: s_[kk] for kk in ("object", "mesh", "ground_ob", "where", "z")},
                    rgb=s_["rgb"], lum=round(s_["lum"], 4), ground_lum=round(s_["ground_lum"], 4)),
        sunlit=dict({kk: t_[kk] for kk in ("object", "mesh", "ground_ob", "where", "z")},
                    rgb=t_["rgb"], lum=round(t_["lum"], 4), ground_lum=round(t_["ground_lum"], 4)),
        ratio_shrub_sun_over_shade=round(t_["lum"] / max(s_["lum"], 1e-9), 2),
        ratio_ground_sun_over_shade=(round(t_["ground_lum"] / s_["ground_lum"], 2)
                                     if s_["ground_lum"] > 0 else None),   # review note 8: no 1/0 headline
        decile=dict(n=k,
                    shade_ground=round(mean(dec_lo, "ground_lum"), 4),
                    sun_ground=round(mean(dec_hi, "ground_lum"), 4),
                    shade_shrub=round(mean(dec_lo, "lum"), 4),
                    sun_shrub=round(mean(dec_hi, "lum"), 4),
                    ratio_ground=round(mean(dec_hi, "ground_lum") / max(mean(dec_lo, "ground_lum"), 1e-9), 2),
                    ratio_shrub=round(mean(dec_hi, "lum") / max(mean(dec_lo, "lum"), 1e-9), 2)))
    pick["agreement_decile"] = round(pick["decile"]["ratio_shrub"] / max(pick["decile"]["ratio_ground"], 1e-9), 3)
    q = np.quantile([r["ground_lum"] for r in lit], [0.25, 0.5, 0.75])
    bins = [[], [], [], []]
    for r in lit:
        bins[int(np.searchsorted(q, r["ground_lum"]))].append(r)
    pick["quartiles"] = [dict(n=len(b), ground_lum=round(float(np.mean([r["ground_lum"] for r in b])), 4),
                              shrub_lum=round(float(np.mean([r["lum"] for r in b])), 4)) for b in bins if b]

by_ob = {}
for r in with_g:
    by_ob.setdefault(r["ground_ob"], []).append(r)
corr = {}
for gob, rs in by_ob.items():
    if len(rs) >= 20:
        x = np.array([r["ground_lum"] for r in rs])
        y = np.array([r["lum"] for r in rs])
        if x.std() > 0 and y.std() > 0:
            corr[gob] = dict(n=len(rs), pearson=round(float(np.corrcoef(x, y)[0, 1]), 3),
                             ground_lum_mean=round(float(x.mean()), 4), shrub_lum_mean=round(float(y.mean()), 4))

out = dict(generated=time.strftime("%Y-%m-%dT%H:%M:%S"), placements_raycast=len(rows),
           with_ground_lightmap=len(with_g), check1=pick, correlation_by_ground=corr,
           ground_objects={k: len(v) for k, v in sorted(by_ob.items())},
           all_ray_hits={k: sum(1 for r in rows if r["ground_ob"] == k)
                         for k in sorted({r["ground_ob"] for r in rows})},
           no_ground_reason=sorted({r["where"] for r in rows if r["ground_lum"] is None}))
(g3.OUT / "instance_check.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: v for k, v in out.items() if k != "correlation_by_ground"}, indent=1)[:2000])
print(json.dumps(corr, indent=1))
print(f"[gate4] wrote {g3.OUT / 'instance_check.json'}")
