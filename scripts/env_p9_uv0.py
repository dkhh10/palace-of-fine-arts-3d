"""Phase 9 ENV / 8d R3 -- UV0 for the backdrop, laid per face in world metres.

The backdrop carries no UV at all today (verified on assets/environment.blend: 1 291 ENV_backdrop_* meshes, every
one with an empty `uv_layers`).  Gate 2 generates UV1 from the MERGED geometry (`export/gate2_common.py:48`), so a
UV0 authored here does not disturb it, does not move a vertex and does not move a triangle.

Layout (`TILE`, metres per tile, keyed by the source material):
  * a face whose world normal has |nz| >= 0.5 is HORIZONTAL  -> planar world XY  (roofs, canopy lobes' tops, lawn)
  * anything else is a WALL -> u runs along the face's own horizontal tangent (i.e. along the street), v = world z
UV values are already divided by the tile size, so the image is sampled with wrap REPEAT and NO texture transform
-- that is what makes the export hand-off a one-liner (see docs/briefs/phase9_env_report.md).

Phase is per object, not global: u starts at the object's own bbox corner and v at its own base, plus a stable
name-hashed jitter, so neighbouring buildings do not line their storeys up into one continuous grid.

The layer is called "UVMap" and it is layer 0, so it lands on TEXCOORD_0.  One shared name across all 1 291
objects is required: `export/gate1_set.py:583` joins the backdrop per source material and Blender's join matches
UV layers by NAME.

Called from `env_backdrop.build_all` (so a full `env_build.py` reproduces it) and runnable on its own to patch an
existing assets/environment.blend:
    scripts/blender_run.sh 300 -- --background --python scripts/env_p9_uv0.py
"""
import math
import hashlib
import numpy as np
import bpy

UV_NAME = "UVMap"

# metres per tile -- must match scripts/env_p9_tiles.py TILES
TILE = {
    "MAT_backdrop_building":  (16.0, 13.2),
    "MAT_backdrop_roof":      (16.0, 16.0),
    "MAT_backdrop_roof_tile": (8.0, 8.0),
    "MAT_backdrop_forest":    (24.0, 24.0),
}
TILE_DEFAULT = (16.0, 16.0)      # lawn / hill / skylight / door: they get the layer so the Gate-1 join stays
                                 # consistent, but their materials do not sample it.


def _jitter(name):
    h = hashlib.md5(name.encode()).digest()
    return (h[0] / 255.0, h[1] / 255.0)


def lay_uv0(objects):
    """Add/refresh `UV_NAME` as layer 0 on every mesh in `objects`.  Returns (n_objects, n_loops)."""
    n_obj = n_loop = 0
    for ob in objects:
        me = ob.data
        if me is None:
            continue
        mat = me.materials[0].name if me.materials else ""
        tu, tv = TILE.get(mat, TILE_DEFAULT)

        lay = me.uv_layers.get(UV_NAME)
        if lay is None:
            lay = me.uv_layers.new(name=UV_NAME, do_init=False)
        # keep it as layer 0 (TEXCOORD_0); anything else would have to be re-indexed at export
        while me.uv_layers[0].name != UV_NAME and len(me.uv_layers) > 1:
            me.uv_layers.remove(me.uv_layers[0])
        lay = me.uv_layers[UV_NAME]
        if not me.polygons:          # empty mesh: it still needs the layer so the Gate-1 join stays consistent
            n_obj += 1
            continue

        mw = np.array(ob.matrix_world.to_4x4()).reshape(4, 4)
        nm = np.linalg.inv(mw[:3, :3]).T

        nv = len(me.vertices)
        co = np.empty(nv * 3, dtype=np.float64)
        me.vertices.foreach_get("co", co)
        co = co.reshape(nv, 3)
        wco = co @ mw[:3, :3].T + mw[:3, 3]

        npo = len(me.polygons)
        pn = np.empty(npo * 3, dtype=np.float64)
        me.polygons.foreach_get("normal", pn)
        pn = pn.reshape(npo, 3) @ nm.T
        ln = np.linalg.norm(pn, axis=1, keepdims=True)
        pn = pn / np.where(ln < 1e-12, 1.0, ln)

        tot = np.empty(npo, dtype=np.int32)
        me.polygons.foreach_get("loop_total", tot)
        nl = len(me.loops)
        lv = np.empty(nl, dtype=np.int32)
        me.loops.foreach_get("vertex_index", lv)
        pidx = np.repeat(np.arange(npo, dtype=np.int32), tot)

        p = wco[lv]                                  # world position per loop
        n = pn[pidx]                                 # world face normal per loop

        ox, oy, oz = wco[:, 0].min(), wco[:, 1].min(), wco[:, 2].min()
        jx, jy = _jitter(ob.name)

        # wall: u along the face's horizontal tangent, v = height above the object's own base
        az = np.arctan2(n[:, 1], n[:, 0])
        tx, ty = -np.sin(az), np.cos(az)
        u_wall = (p[:, 0] * tx + p[:, 1] * ty - (ox * tx + oy * ty)) / tu + jx
        v_wall = (p[:, 2] - oz) / tv + jy * 0.0      # storeys start at the building's own base, no v jitter

        # horizontal: planar world XY
        u_flat = (p[:, 0] - ox) / tu + jx
        v_flat = (p[:, 1] - oy) / tv + jy

        horiz = np.abs(n[:, 2]) >= 0.5
        uv = np.empty((nl, 2), dtype=np.float32)
        uv[:, 0] = np.where(horiz, u_flat, u_wall)
        uv[:, 1] = np.where(horiz, v_flat, v_wall)
        lay.uv.foreach_set("vector", uv.reshape(-1))
        me.update()
        n_obj += 1
        n_loop += nl
    return n_obj, n_loop


def backdrop_objects():
    """Every mesh whose slot-0 material is a MAT_backdrop_* one, plus every mesh in ENV_backdrop.  Selection is by
    MATERIAL, not name, because Gate 1 groups the backdrop by material (`ENV_BACKDROP` + `ENV_OTHER`)."""
    out = []
    seen = set()
    coll = bpy.data.collections.get("ENV_backdrop")
    pool = list(coll.all_objects) if coll else []
    pool += [o for o in bpy.data.objects if o.type == "MESH"]
    for ob in pool:
        if ob.type != "MESH" or ob.name in seen:
            continue
        mats = [m.name for m in ob.data.materials if m]
        in_coll = coll is not None and ob.name in coll.all_objects
        if not (in_coll or any(m.startswith("MAT_backdrop_") for m in mats)):
            continue
        seen.add(ob.name)
        out.append(ob)
    return out


def apply():
    objs = backdrop_objects()
    n_obj, n_loop = lay_uv0(objs)
    print(f"[env_p9_uv0] UV0 '{UV_NAME}' on {n_obj} backdrop meshes, {n_loop} loops")
    return n_obj, n_loop


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import common
    bpy.ops.wm.open_mainfile(filepath=str(common.ASSET_FILES["ENV"]))
    apply()
    # report the per-material tile span so the number in the report is measured, not asserted
    for mat, (tu, tv) in sorted(TILE.items()):
        objs = [o for o in bpy.data.objects
                if o.type == "MESH" and o.data.materials and o.data.materials[0]
                and o.data.materials[0].name == mat and o.data.uv_layers.get(UV_NAME)]
        if not objs:
            continue
        us, vs = [], []
        for o in objs[:80]:
            lay = o.data.uv_layers[UV_NAME]
            a = np.empty(len(o.data.loops) * 2)
            lay.uv.foreach_get("vector", a)
            a = a.reshape(-1, 2)
            us.append(a[:, 0].max() - a[:, 0].min())
            vs.append(a[:, 1].max() - a[:, 1].min())
        print(f"[env_p9_uv0] {mat:26s} tile {tu} x {tv} m  n={len(objs):4d}  "
              f"u span median {np.median(us):.2f} tiles, v span median {np.median(vs):.2f} tiles")
    common.save_blend(common.ASSET_FILES["ENV"])
