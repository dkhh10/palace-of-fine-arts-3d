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
walk = [r for r in with_g if "colonnade_walk" in r["ground_ob"] or "paving" in r["ground_ob"]]
lawn = [r for r in with_g if "terrain_ground" in r["ground_ob"]]
pick = {}
if walk:
    pick["shaded_colonnade"] = min(walk, key=lambda r: r["ground_lum"])
if lawn:
    pick["sunlit_lawn"] = max(lawn, key=lambda r: r["ground_lum"])
if len(pick) == 2:
    s, t = pick["shaded_colonnade"], pick["sunlit_lawn"]
    pick["ratio_shrub_sun_over_shade"] = round(t["lum"] / max(s["lum"], 1e-9), 2)
    pick["ratio_ground_sun_over_shade"] = round(t["ground_lum"] / max(s["ground_lum"], 1e-9), 2)
    pick["agreement"] = round(pick["ratio_shrub_sun_over_shade"] / max(pick["ratio_ground_sun_over_shade"], 1e-9), 3)

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
           no_ground_reason=sorted({r["where"] for r in rows if r["ground_lum"] is None}))
(g3.OUT / "instance_check.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: v for k, v in out.items() if k != "correlation_by_ground"}, indent=1)[:2000])
print(json.dumps(corr, indent=1))
print(f"[gate4] wrote {g3.OUT / 'instance_check.json'}")
