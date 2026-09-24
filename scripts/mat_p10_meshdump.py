"""Phase 10 r1 -- dump ARCH geometry from assets/architecture.blend for the numpy side (no save, read-only).

    scripts/blender_run.sh 600 -- --background assets/architecture.blend --python scripts/mat_p10_meshdump.py -- list
    scripts/blender_run.sh 600 -- --background assets/architecture.blend --python scripts/mat_p10_meshdump.py -- samples
    scripts/blender_run.sh 600 -- --background assets/architecture.blend --python scripts/mat_p10_meshdump.py -- uvbake

list     print every ARCH mesh object near the rotunda (name, verts, polys, uv layers, radius / z range)
samples  work/arch_samples.npz: area-weighted surface samples (world xyz + normal + object id) of the rotunda's
         LOD0/unsuffixed ARCH meshes -- the ICP target of step 2 -- plus world triangles for the edge renders
uvbake   work/uvbake_tris.npz: for every mesh carrying `UVBake`, LOCAL triangles, per-corner UVBake coords, the
         per-corner normal, the atlas group, and every instance's world matrix (mats / mat_owner) (steps 4 and 6 rasterise these in numpy)
"""
import bpy, sys, os, math, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

args = common.script_args()
CMD = args[0] if args else "list"
WORK = common.ASSETS / "textures" / "projection2" / "work"
WORK.mkdir(parents=True, exist_ok=True)


def world_matrix(o):
    """matrix_world is stale for hidden objects (LOD0 is hide_viewport in the saved file): same rule as
    arch_uvproj.world_matrix -- matrix_basis, refused for parented / delta-transformed objects."""
    if o.parent is not None or tuple(o.delta_location) != (0.0, 0.0, 0.0) or tuple(o.delta_scale) != (1.0, 1.0, 1.0):
        raise SystemExit(f"[p10dump] {o.name} is parented or has a delta transform")
    return o.matrix_basis


def arch_objs(lod=0, rmax=40.0):
    ARCH = bpy.data.collections["ARCH"]
    out = []
    for o in ARCH.all_objects:
        if o.type != "MESH" or o.name.startswith("PH_"):
            continue
        if "_LOD" in o.name and f"_LOD{lod}" not in o.name:
            continue
        mw = world_matrix(o)
        bb = [mw @ __import__("mathutils").Vector(c) for c in o.bound_box]
        r = min(math.hypot(v.x, v.y) for v in bb)
        if r > rmax:
            continue
        out.append(o)
    return out


def tri_arrays(o, uv_name=None):
    me = o.data
    me.calc_loop_triangles()
    mw = np.array(world_matrix(o))
    n = len(me.loop_triangles)
    vi = np.zeros(n * 3, np.int32); me.loop_triangles.foreach_get("vertices", vi)
    li = np.zeros(n * 3, np.int32); me.loop_triangles.foreach_get("loops", li)
    co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    wco = co @ mw[:3, :3].T + mw[:3, 3]
    ln = np.zeros(len(me.loops) * 3, np.float32); me.corner_normals.foreach_get("vector", ln)
    ln = ln.reshape(-1, 3) @ np.linalg.inv(mw[:3, :3])      # normal matrix = inverse-transpose; row-vector form
    ln /= np.maximum(np.linalg.norm(ln, axis=1, keepdims=True), 1e-9)
    P = wco[vi].reshape(n, 3, 3)
    N = ln[li].reshape(n, 3, 3)
    UV = None
    if uv_name is not None:
        uvl = me.uv_layers[uv_name]
        uv = np.zeros(len(me.loops) * 2, np.float32); uvl.data.foreach_get("uv", uv)
        UV = uv.reshape(-1, 2)[li].reshape(n, 3, 2)
    return P, N, UV


if CMD == "list":
    for o in sorted(arch_objs(lod=0, rmax=40.0), key=lambda o: o.name):
        mw = world_matrix(o)
        from mathutils import Vector
        bb = [mw @ Vector(c) for c in o.bound_box]
        print(f"[p10dump] {o.name:48s} v {len(o.data.vertices):7d} p {len(o.data.polygons):7d} "
              f"mesh {o.data.name:40s} uv {[u.name for u in o.data.uv_layers]} "
              f"z {min(v.z for v in bb):6.2f}..{max(v.z for v in bb):6.2f} "
              f"r {min(math.hypot(v.x, v.y) for v in bb):5.1f}")

elif CMD == "samples":
    rng = np.random.default_rng(1)
    objs = arch_objs(lod=0, rmax=200.0)          # the rotunda AND the site / colonnade: breaks the octagon symmetry
    allP, allN, allI, names = [], [], [], []
    TP, TI = [], []
    for k, o in enumerate(objs):
        P, N, _ = tri_arrays(o)
        a = 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1)
        m = max(1, int(a.sum() * (4.0 if "rotunda" in o.name else 1.0)))   # 4 / m2 on the rotunda, 1 elsewhere
        idx = rng.choice(len(a), m, p=a / a.sum())
        r1, r2 = rng.random(m), rng.random(m)
        s = np.sqrt(r1)
        w0, w1, w2 = 1 - s, s * (1 - r2), s * r2
        pts = P[idx, 0] * w0[:, None] + P[idx, 1] * w1[:, None] + P[idx, 2] * w2[:, None]
        fn = np.cross(P[idx, 1] - P[idx, 0], P[idx, 2] - P[idx, 0])
        fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
        allP.append(pts); allN.append(fn); allI.append(np.full(m, k)); names.append(o.name)
        TP.append(P); TI.append(np.full(len(P), k))
    np.savez_compressed(WORK / "arch_samples.npz", xyz=np.concatenate(allP), nrm=np.concatenate(allN),
                        oid=np.concatenate(allI), names=np.array(names),
                        tris=np.concatenate(TP).astype(np.float32), tri_oid=np.concatenate(TI))
    print(f"[p10dump] samples: {sum(len(p) for p in allP)} points on {len(objs)} objects; "
          f"{sum(len(p) for p in TP)} triangles")

elif CMD == "uvbake":
    # LOCAL triangles once per mesh + every instance's world matrix (the 16 columns share one mesh and one atlas
    # region; the projection takes all instances).  Objects sharing a mesh with an identical matrix (LOD0 / LOD1 of
    # one course) count once.
    groups = json.loads((WORK.parent / "uvbake_groups.json").read_text())
    TP, TN, TU, TG, TO, names, mats, mat_owner = [], [], [], [], [], [], [], []
    mesh_index = {}
    for g, onames in groups.items():
        if not g.isdigit():                    # "sha1"
            continue
        for n in onames:
            o = bpy.data.objects.get(n)
            if o is None:
                continue
            mw = np.array(world_matrix(o), dtype=np.float64)
            if o.data.name not in mesh_index:
                if "UVBake" not in o.data.uv_layers:
                    raise SystemExit(f"[p10dump] {n} has no UVBake")
                me = o.data
                me.calc_loop_triangles()
                nt = len(me.loop_triangles)
                vi = np.zeros(nt * 3, np.int32); me.loop_triangles.foreach_get("vertices", vi)
                li = np.zeros(nt * 3, np.int32); me.loop_triangles.foreach_get("loops", li)
                co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co)
                ln = np.zeros(len(me.loops) * 3, np.float32); me.corner_normals.foreach_get("vector", ln)
                uv = np.zeros(len(me.loops) * 2, np.float32); me.uv_layers["UVBake"].data.foreach_get("uv", uv)
                mesh_index[me.name] = len(names)
                TP.append(co.reshape(-1, 3)[vi].reshape(nt, 3, 3)); TN.append(ln.reshape(-1, 3)[li].reshape(nt, 3, 3))
                TU.append(uv.reshape(-1, 2)[li].reshape(nt, 3, 2))
                TG.append(np.full(nt, int(g))); TO.append(np.full(nt, len(names))); names.append(me.name)
            k = mesh_index[o.data.name]
            if not any(mo == k and np.allclose(m, mw) for m, mo in zip(mats, mat_owner)):
                mats.append(mw); mat_owner.append(k)
    np.savez_compressed(WORK / "uvbake_tris.npz", P=np.concatenate(TP), N=np.concatenate(TN),
                        UV=np.concatenate(TU), G=np.concatenate(TG), O=np.concatenate(TO), names=np.array(names),
                        mats=np.array(mats), mat_owner=np.array(mat_owner))
    print(f"[p10dump] uvbake: {sum(len(p) for p in TP)} local triangles on {len(names)} meshes, {len(mats)} instances")
