"""Gate 1 step 1: the frozen export SET, built from master_delivery.blend.

Entry point is `export/export_set.py -- --gate1` (this module is imported and `build()` called), so the Gate 0
chain keeps working unchanged:

    scripts/blender_run.sh 1800 -- --background <master_delivery.blend> --python export/export_set.py -- --gate1

Idempotent: it always rebuilds the EXP_* collections from the source file and overwrites export/out/gate1/gate1_set.blend.
master_delivery.blend is never saved (save_as_mainfile(copy=True) keeps bpy.data.filepath on the source).

Selection (CLAUDE.md "Phase 6 / Sources and conventions")
  ARCH_ at LOD0 + unsuffixed ARCH_ ; INST_ at LOD0 (the placed ORN_ prototypes) ; ENV_ at LOD1 + unsuffixed ENV_ ;
  shrubs at LOD2 ; ORN_ prototypes, PH_ placeholders, SOCKET_, cameras and lights are never exported.
  ENV_lagoon_water and ENV_backdrop_bay are dropped: the water is a viewer plane at WATER_Z.

Geometry policy
  * every mesh is taken through the depsgraph (the 685 ARCH BEVEL modifiers are applied);
  * shared meshes stay shared - one decimated datablock per (source mesh, modifier signature) and N placements,
    which is what EXT_mesh_gpu_instancing needs;
  * ARCH objects with fewer than INSTANCE_MIN placements are JOINED per (zone, material) into one merged mesh:
    one draw call, one PBR atlas and one lightmap each, instead of 1 000 single-use draw calls;
  * ENV backdrop (city blocks, roofs, Presidio) is merged per material and gets no bake;
  * near trees keep LOD1 with half their leaf cards deleted (cards get sparser, not smaller - plan section 4b
    option C), far trees become tagged billboard quads for the Gate 3 impostor bake.

UVs
  UV1 (material bake, Gate 2): one packed atlas per group - ARCH per (zone, material), ORN per prototype,
  ENV ground per object. UV2 (lightmap, Gate 3): a [0,1] unwrap per unique mesh; assets with one placement get
  their own map, instanced assets get a per-instance slot in a 4K/256 px atlas (the user's ORN option (c)).
"""
import bpy
import bmesh
import os
import sys
import json
import math
import time
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0  # noqa: E402
import gate1_common as g1  # noqa: E402
import common  # noqa: E402
import qa_cameras  # noqa: E402
from mathutils import Vector  # noqa: E402

INSTANCE_MIN = 4            # >= this many placements of one mesh -> keep it shared, never merge it
TILE_MARGIN = 0.004         # smart-project island margin for the UV1 atlases
UV2_MARGIN = 0.010          # lightmap islands need a wider gutter at 2K


# ---------------------------------------------------------------------------- small helpers
def tris_of(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def mod_sig(ob):
    return "|".join(f"{m.type}:{getattr(m, 'width', '')}:{getattr(m, 'segments', '')}" for m in ob.modifiers)


def select_only(objs):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    objs = list(objs)
    for o in objs:
        o.select_set(True)
    if objs:
        bpy.context.view_layer.objects.active = objs[0]
    return objs


def smart_project(objs, uv_name, margin):
    """Multi-object smart project into a shared [0,1] atlas on the uv layer `uv_name`."""
    objs = [o for o in objs if o.data.polygons]
    if not objs:
        return
    for o in objs:
        me = o.data
        if uv_name not in me.uv_layers:
            me.uv_layers.new(name=uv_name)
        me.uv_layers.active = me.uv_layers[uv_name]
        me.uv_layers[uv_name].active_render = (uv_name == g1.UV1)
    select_only(objs)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=margin,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def thin_leaf_cards(me, target_fraction):
    """Delete leaf cards until the mesh is `target_fraction` of its triangle count. Branch geometry (the large
    connected components) is never touched, so the tree gets sparser, not smaller (plan section 4b, option C).
    The card keep-fraction is derived from the target, not assumed: a tree is ~23 % branches, so dropping half
    the cards only reaches 62-66 % of the triangles."""
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    # connected components over faces
    seen = set()
    comps = []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack, comp = [f], []
        seen.add(f.index)
        while stack:
            cf = stack.pop()
            comp.append(cf)
            for e in cf.edges:
                for nf in e.link_faces:
                    if nf.index not in seen:
                        seen.add(nf.index)
                        stack.append(nf)
        comps.append(comp)
    cards = [c for c in comps if len(c) <= 2]
    branches = len(comps) - len(cards)
    total = sum(len(f.verts) - 2 for c in comps for f in c)
    card_tris = sum(len(f.verts) - 2 for c in cards for f in c)
    want_drop = total - target_fraction * total
    keep_fraction = 1.0 if card_tris <= 0 else max(0.0, min(1.0, 1.0 - want_drop / card_tris))
    keep_pct = int(round(keep_fraction * 1000))
    drop, dropped = [], 0
    for i, c in enumerate(cards):
        if (i % 1000) >= keep_pct:
            drop.extend(c)
            dropped += 1
    bmesh.ops.delete(bm, geom=drop, context="FACES")
    bm.to_mesh(me)
    bm.free()
    me.update()
    return dict(components=len(comps), cards=len(cards), branch_components=branches,
                branch_tris=total - card_tris, card_tris=card_tris,
                card_keep_fraction=round(keep_fraction, 4), cards_dropped=dropped)


# ---------------------------------------------------------------------------- the build
def build():
    t_all = time.time()
    g1.ensure_dirs()
    (g1.OUT / "manifest.json").unlink(missing_ok=True)
    step = g0.Step("gate1_export_set")
    scene = bpy.context.scene
    rep = {"source": bpy.data.filepath, "started": time.strftime("%Y-%m-%dT%H:%M:%S")}

    # ---- 0. the delivery file hides every _LOD0 object; un-hide before any transform is read
    for ob in bpy.data.objects:
        ob.hide_viewport = False
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()

    # ---- 1. classify the source objects
    src = {"ARCH": [], "ORN": [], "ENV_GROUND": [], "ENV_BACKDROP": [], "ENV_TREE": [], "ENV_SHRUB": [],
           "ENV_OTHER": []}
    ENV_GROUND_RE = re.compile(r"^ENV_(terrain_ground|ground_colonnade_walk|lagoon_bed|riprap_)")
    ENV_BACKDROP_RE = re.compile(r"^ENV_backdrop")
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        n = ob.name
        if n.startswith(g1.NEVER_PREFIX) or n in g1.NEVER_NAME:
            continue
        lod = g1.lod_of(n)
        if n.startswith("ARCH_") and lod in (None, 0):
            src["ARCH"].append(ob)
        elif n.startswith("INST_") and lod == 0:
            src["ORN"].append(ob)
        elif n.startswith("ENV_"):
            if n.startswith("ENV_tree") and lod == 1:
                src["ENV_TREE"].append(ob)
            elif n.startswith("ENV_shrub") and lod == 2:
                src["ENV_SHRUB"].append(ob)
            elif lod is None:
                (src["ENV_GROUND"] if ENV_GROUND_RE.match(n) else
                 src["ENV_BACKDROP"] if ENV_BACKDROP_RE.match(n) else src["ENV_OTHER"]).append(ob)
    rep["source_counts"] = {k: len(v) for k, v in src.items()}
    MW = {ob.name: ob.matrix_world.copy() for objs in src.values() for ob in objs}

    # ---- 2. output collections
    for name in ("EXP_ARCH", "EXP_ORN", "EXP_ENV", "EXP_ORN_HI"):
        c = bpy.data.collections.get(name)
        if c:
            bpy.data.collections.remove(c)
    colls = {}
    for name in ("EXP_ARCH", "EXP_ORN", "EXP_ENV", "EXP_ORN_HI"):
        c = bpy.data.collections.new(name)
        scene.collection.children.link(c)
        colls[name] = c
    tmp = bpy.data.collections.new("EXP_TMP")
    scene.collection.children.link(tmp)

    def exp_mesh(ob, target_tris, name, allow_remesh=True, src_me=None):
        """Evaluated (modifiers applied) copy of ob's mesh, decimated to ~target_tris. Object space.

        `src_me` copies a mesh datablock directly and never touches the depsgraph: an object created after
        `dg` was captured is not in it, and `evaluated_get(dg)` then hands back a STALE evaluation - measured,
        it gave attic panel v2 the v1 low-poly and v3 the v2 one (lo->hi deviation 457 / 412 mm against
        51 mm for the pair that happened to line up)."""
        me = src_me.copy() if src_me is not None else bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        me.name = name
        src_t = tris_of(me)
        if target_tris and src_t > target_tris:
            # COLLAPSE stalls on meshes that are thousands of separate islands (the three ORN attic panels
            # stopped at 83 k of a 8 k target): weld the coincident vertices first, then iterate the ratio.
            bm = bmesh.new()
            bm.from_mesh(me)
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
            bm.to_mesh(me)
            bm.free()
            me.update()
            tob = bpy.data.objects.new("EXP_TMP_dec", me)
            tmp.objects.link(tob)
            bpy.context.view_layer.objects.active = tob
            for _ in range(4):
                cur = tris_of(me)
                if cur <= target_tris * 1.05:
                    break
                m = tob.modifiers.new("decimate", "DECIMATE")
                m.decimate_type = "COLLAPSE"
                m.ratio = max(1e-4, float(target_tris) / float(cur))
                m.use_collapse_triangulate = True
                bpy.ops.object.modifier_apply(modifier=m.name)
                if tris_of(me) >= cur:
                    break
            # Three ORN attic panels are ~40 000 separate islands of relief: COLLAPSE has no edge to collapse
            # across them and stalls at 38-78 k against an 8 k target. Voxel-remesh them into one shell first
            # (the relief is going into the hi->lo normal map anyway), then collapse.
            if allow_remesh and tris_of(me) > target_tris * 1.5:
                bpy.context.view_layer.objects.active = tob
                dx, dy, dz = (max(1e-3, v) for v in tob.dimensions)
                area = 2.0 * (dx * dy + dy * dz + dx * dz)
                me.remesh_voxel_size = max(0.01, math.sqrt(area / (4.0 * target_tris)))
                me.remesh_voxel_adaptivity = 0.0
                bpy.ops.object.voxel_remesh()
                me = tob.data
                me.name = name
                for _ in range(3):
                    cur = tris_of(me)
                    if cur <= target_tris * 1.05:
                        break
                    m = tob.modifiers.new("decimate", "DECIMATE")
                    m.decimate_type = "COLLAPSE"
                    m.ratio = max(1e-4, float(target_tris) / float(cur))
                    m.use_collapse_triangulate = True
                    bpy.ops.object.modifier_apply(modifier=m.name)
                    if tris_of(me) >= cur:
                        break
                remeshed.add(name)
            tmp.objects.unlink(tob)
            bpy.data.objects.remove(tob, do_unlink=True)
        return me, src_t, tris_of(me)

    grey_cache = {}
    remeshed = set()

    def grey(name):
        m = grey_cache.get(name)
        if m:
            return m
        m = bpy.data.materials.get(name)
        if m:
            bpy.data.materials.remove(m)
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        b = m.node_tree.nodes.get("Principled BSDF")
        if b:
            b.inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1.0)
            b.inputs["Roughness"].default_value = 0.7
            b.inputs["Metallic"].default_value = 0.0
        grey_cache[name] = m
        return m

    assets = {}          # exported object name -> record
    meshes = {}          # exported mesh name -> record
    placements = []      # (exported object, source object) for the placement assertion

    # ---------------------------------------------------------------- 3. ARCH
    t0 = time.time()
    by_mesh = {}
    for ob in src["ARCH"]:
        by_mesh.setdefault((ob.data.name, mod_sig(ob)), []).append(ob)
    arch_inst, arch_static = {}, {}
    for key, obs in by_mesh.items():
        (arch_inst if len(obs) >= INSTANCE_MIN else arch_static)[key] = obs

    def zone_of(name):
        p = name.split("_")
        return "_".join(p[:3]) if len(p) > 2 and p[1] == "colonnade" else "_".join(p[:2])

    # 3a. instanced ARCH: one shared decimated mesh, N placements
    for (mname, sig), obs in sorted(arch_inst.items()):
        tgt = g1.arch_target(mname)
        me, s_t, l_t = exp_mesh(obs[0], tgt, f"EXPM_{mname}")
        mat = grey(f"MAT_EXP_{zone_of(obs[0].name)}__{(obs[0].data.materials[0].name if obs[0].data.materials else 'NONE')}")
        me.materials.clear()
        me.materials.append(mat)
        meshes[me.name] = dict(cls="ARCH", src_mesh=mname, src_tris=s_t, tris=l_t, target=tgt,
                               placements=len(obs), material=mat.name, instanced=True,
                               src_material=(obs[0].data.materials[0].name if obs[0].data.materials else None))
        for ob in obs:
            no = bpy.data.objects.new(ob.name, me)
            colls["EXP_ARCH"].objects.link(no)
            placements.append((no, ob))
            assets[no.name] = dict(cls="ARCH", mesh=me.name, tris=l_t, material=mat.name, instanced=True)
    # 3b. static ARCH: decimate, place in world space, then join per (zone, material)
    merge_groups = {}
    for (mname, sig), obs in sorted(arch_static.items()):
        tgt = g1.arch_target(mname)
        for ob in obs:
            me, s_t, l_t = exp_mesh(ob, tgt, f"EXPM_{ob.name}")
            no = bpy.data.objects.new(f"EXPO_{ob.name}", me)
            no.matrix_world = MW[ob.name]
            tmp.objects.link(no)
            gk = (zone_of(ob.name), ob.data.materials[0].name if ob.data.materials else "NONE")
            merge_groups.setdefault(gk, []).append(no)
    arch_merged = []
    for (zone, smat), objs in sorted(merge_groups.items()):
        select_only(objs)
        if len(objs) > 1:
            bpy.ops.object.join()
        merged = bpy.context.view_layer.objects.active
        merged.name = f"{zone}_{smat.replace('MAT_', '')}_merged"
        merged.data.name = f"EXPM_{merged.name}"
        mat = grey(f"MAT_EXP_{zone}__{smat}")
        merged.data.materials.clear()
        merged.data.materials.append(mat)
        tmp.objects.unlink(merged)
        colls["EXP_ARCH"].objects.link(merged)
        t = tris_of(merged.data)
        meshes[merged.data.name] = dict(cls="ARCH", src_mesh=None, src_tris=t, tris=t, target=None,
                                        placements=1, material=mat.name, instanced=False,
                                        merged_from=len(objs), src_material=smat)
        assets[merged.name] = dict(cls="ARCH", mesh=merged.data.name, tris=t, material=mat.name, instanced=False,
                                   merged_from=len(objs))
        arch_merged.append(merged)
    rep["arch_s"] = round(time.time() - t0, 1)

    # ---------------------------------------------------------------- 4. ORN prototypes + placements
    t0 = time.time()
    by_proto = {}
    for ob in src["ORN"]:
        by_proto.setdefault(ob.data.name, []).append(ob)
    orn_lo = {}
    lo_sources = {}

    def _bb(m):
        co = [v.co for v in m.vertices]
        return [[min(c[i] for c in co), max(c[i] for c in co)] for i in range(3)]

    for pname, obs in sorted(by_proto.items()):
        tgt = g1.orn_target(pname)
        lod1_name = g1.lo_from_lod1(pname)
        lod1_me = bpy.data.meshes.get(lod1_name) if lod1_name else None
        if lod1_me is not None:
            # the _LOD1 twin must sit in the same prototype-local space as the LOD0 hi, or the hi->lo bake
            # would be cast between two different objects. Assert it on the bounding box.
            b0, b1 = _bb(obs[0].data), _bb(lod1_me)
            worst_bb = max(abs(b0[i][j] - b1[i][j]) for i in range(3) for j in range(2))
            assert worst_bb < 0.05, (f"{lod1_name} is not coincident with {pname}: bounding boxes differ by "
                                     f"{worst_bb:.4f} m")
            me, s_t, l_t = exp_mesh(None, tgt, f"EXPM_{pname}", allow_remesh=False, src_me=lod1_me)
            # check the EXPORTED mesh, not just the two source datablocks: the stale-depsgraph bug passed the
            # source check and still shipped the wrong panel.
            bb_out, bb_src = _bb(me), _bb(lod1_me)
            out_bb = max(abs(bb_out[i][j] - bb_src[i][j]) for i in range(3) for j in range(2))
            assert out_bb < 0.01, (f"the exported low-poly for {pname} is not {lod1_name}: bounding boxes "
                                   f"differ by {out_bb:.4f} m")
            assert abs(s_t - len(lod1_me.polygons)) < len(lod1_me.polygons), "source tri count mismatch"
            lo_sources[pname] = dict(lo_source=lod1_name, lo_source_tris=s_t, bbox_delta_m=round(worst_bb, 5),
                                     exported_bbox_delta_m=round(out_bb, 5), out_tris=l_t, target=tgt)
        else:
            me, s_t, l_t = exp_mesh(obs[0], tgt, f"EXPM_{pname}")
        mat = grey(f"MAT_EXP_ORN__{pname}")
        me.materials.clear()
        me.materials.append(mat)
        co = [v.co for v in me.vertices]
        dims = ([round(max(c[i] for c in co) - min(c[i] for c in co), 3) for i in range(3)]
                if co else [0.0, 0.0, 0.0])
        meshes[me.name] = dict(cls="ORN", src_mesh=pname, src_tris=s_t, tris=l_t, target=tgt,
                               placements=len(obs), material=mat.name, instanced=True, src_material=None,
                               dims_m=dims, max_dim_m=max(dims),
                               lo_source=lo_sources.get(pname, {}).get("lo_source"))
        orn_lo[pname] = me
        # the hi twin, at the placement of the first instance, for the hi->lo normal + AO bake
        hi_me = bpy.data.meshes.new_from_object(obs[0].evaluated_get(dg))
        hi_me.name = f"EXPHI_{pname}"
        hi = bpy.data.objects.new(f"EXPHI_{pname}", hi_me)
        colls["EXP_ORN_HI"].objects.link(hi)
        hi.hide_render = True
        for ob in obs:
            no = bpy.data.objects.new(ob.name, me)
            colls["EXP_ORN"].objects.link(no)
            placements.append((no, ob))
            assets[no.name] = dict(cls="ORN", mesh=me.name, tris=l_t, material=mat.name, instanced=True,
                                   prototype=pname)
    rep["orn_lo_from_lod1"] = lo_sources
    rep["orn_s"] = round(time.time() - t0, 1)

    # ---------------------------------------------------------------- 5. ENV ground + backdrop
    t0 = time.time()
    env_ground = []
    riprap = []
    for ob in src["ENV_GROUND"]:
        me, s_t, l_t = exp_mesh(ob, None, f"EXPM_{ob.name}")
        no = bpy.data.objects.new(ob.name, me)
        no.matrix_world = MW[ob.name]
        if ob.name.startswith("ENV_riprap"):
            tmp.objects.link(no)
            riprap.append(no)
        else:
            colls["EXP_ENV"].objects.link(no)
            mat = grey(f"MAT_EXP_ENV__{ob.name}")
            me.materials.clear()
            me.materials.append(mat)
            env_ground.append(no)
            placements.append((no, ob))
            meshes[me.name] = dict(cls="ENV", src_mesh=ob.data.name, src_tris=s_t, tris=l_t, target=None,
                                   placements=1, material=mat.name, instanced=False, src_material=None,
                                   kind="ground")
            assets[no.name] = dict(cls="ENV", mesh=me.name, tris=l_t, material=mat.name, instanced=False,
                                   kind="ground")
    if riprap:
        select_only(riprap)
        if len(riprap) > 1:
            bpy.ops.object.join()
        m = bpy.context.view_layer.objects.active
        m.name = "ENV_riprap_merged"
        m.data.name = "EXPM_ENV_riprap_merged"
        mat = grey("MAT_EXP_ENV__riprap")
        m.data.materials.clear()
        m.data.materials.append(mat)
        tmp.objects.unlink(m)
        colls["EXP_ENV"].objects.link(m)
        t = tris_of(m.data)
        env_ground.append(m)
        meshes[m.data.name] = dict(cls="ENV", src_mesh=None, src_tris=t, tris=t, target=None, placements=1,
                                   material=mat.name, instanced=False, merged_from=len(riprap), src_material=None,
                                   kind="ground")
        assets[m.name] = dict(cls="ENV", mesh=m.data.name, tris=t, material=mat.name, instanced=False,
                              kind="ground", merged_from=len(riprap))
    # backdrop: merge per source material, no bake
    bd = {}
    for ob in src["ENV_BACKDROP"] + src["ENV_OTHER"]:
        me, s_t, l_t = exp_mesh(ob, None, f"EXPM_{ob.name}")
        no = bpy.data.objects.new(f"EXPO_{ob.name}", me)
        no.matrix_world = MW[ob.name]
        tmp.objects.link(no)
        bd.setdefault(ob.data.materials[0].name if ob.data.materials else "NONE", []).append(no)
    backdrop = []
    for smat, objs in sorted(bd.items()):
        select_only(objs)
        if len(objs) > 1:
            bpy.ops.object.join()
        m = bpy.context.view_layer.objects.active
        m.name = f"ENV_backdropgroup_{smat.replace('MAT_', '')}"
        m.data.name = f"EXPM_{m.name}"
        mat = grey(f"MAT_EXP_ENVBD__{smat}")
        m.data.materials.clear()
        m.data.materials.append(mat)
        tmp.objects.unlink(m)
        colls["EXP_ENV"].objects.link(m)
        t = tris_of(m.data)
        backdrop.append(m)
        meshes[m.data.name] = dict(cls="ENV", src_mesh=None, src_tris=t, tris=t, target=None, placements=1,
                                   material=mat.name, instanced=False, merged_from=len(objs), src_material=smat,
                                   pbr=False)
        assets[m.name] = dict(cls="ENV", mesh=m.data.name, tris=t, material=mat.name, instanced=False,
                              kind="backdrop", merged_from=len(objs))
    rep["env_ground_s"] = round(time.time() - t0, 1)

    # ---------------------------------------------------------------- 6. trees: near / far
    t0 = time.time()
    # walkable surface = the paved colonnade walk + the gravel-path faces of the terrain. MAT_lawn is excluded:
    # it covers 489 424 m2 out to +-365 m, so every tree in the file would be "near" it.
    walk_pts = []
    gw = bpy.data.objects.get("ENV_ground_colonnade_walk")
    tg = bpy.data.objects.get("ENV_terrain_ground")
    if gw:
        mw = gw.matrix_world
        walk_pts += [(mw @ p.center).xy[:] for p in gw.data.polygons]
    if tg:
        mats = [m.name if m else None for m in tg.data.materials]
        mw = tg.matrix_world
        walk_pts += [(mw @ p.center).xy[:] for p in tg.data.polygons
                     if p.material_index < len(mats) and mats[p.material_index] == "MAT_gravel_path"]
    tree_rows = []
    for ob in src["ENV_TREE"]:
        mw = MW[ob.name]
        corners = [mw @ Vector(c) for c in ob.bound_box]
        zmin = min(c.z for c in corners)
        zmax = max(c.z for c in corners)
        bx = sum(c.x for c in corners) / 8.0
        by = sum(c.y for c in corners) / 8.0
        d = min(math.hypot(bx - px, by - py) for px, py in walk_pts) if walk_pts else 1e9
        tree_rows.append(dict(name=ob.name, mesh=ob.data.name, ob=ob,
                              base=[round(bx, 2), round(by, 2), round(zmin, 2)],
                              height_m=round(zmax - zmin, 2),
                              width_m=round(max(max(c.x for c in corners) - min(c.x for c in corners),
                                                max(c.y for c in corners) - min(c.y for c in corners)), 2),
                              walk_dist_m=round(d, 2),
                              lod1_tris=tris_of(bpy.data.meshes.new_from_object(ob.evaluated_get(dg)))))
    # 46 of the 147 _LOD1 tree OBJECTS in master_delivery already carry a _LOD2 blob mesh (1 188-1 596 tris):
    # that downgrade is inherited from Phase 5. They are impostor-grade already, so they go straight to the
    # billboard list and never spend the near-tree budget, which is reserved for real LOD1 crowns.
    blob = [t for t in tree_rows if t["mesh"].endswith("_LOD2")]
    within = [t for t in tree_rows
              if t["walk_dist_m"] <= g1.TREE_NEAR_RADIUS_M and not t["mesh"].endswith("_LOD2")]
    within.sort(key=lambda t: t["walk_dist_m"])
    # budget: the ENV class allowance left for near trees after ground, backdrop and the shrubs
    env_so_far = sum(meshes[m.data.name]["tris"] for m in env_ground + backdrop)
    shrub_est = 0
    shrub_by_mesh = {}
    for ob in src["ENV_SHRUB"]:
        shrub_by_mesh.setdefault(ob.data.name, []).append(ob)
    for mname, obs in shrub_by_mesh.items():
        shrub_est += tris_of(obs[0].data) * len(obs)
    tree_allow = max(0, g1.CLASS_BUDGET["ENV"] - env_so_far - shrub_est - 2 * len(tree_rows))
    # thin every prototype the within-radius set uses, then spend the allowance on real numbers
    thin_cache, thin_report = {}, {}
    for t in within:
        if t["mesh"] in thin_cache:
            continue
        me = bpy.data.meshes.new_from_object(t["ob"].evaluated_get(dg))
        me.name = f"EXPM_{t['mesh']}_thin"
        before = tris_of(me)
        info = thin_leaf_cards(me, g1.TREE_NEAR_THIN)
        after = tris_of(me)
        thin_cache[t["mesh"]] = me
        thin_report[t["mesh"]] = dict(before=before, after=after, ratio=round(after / max(before, 1), 3), **info)
    near, used = [], 0
    for t in within:
        cost = tris_of(thin_cache[t["mesh"]])
        if used + cost > tree_allow:
            continue
        near.append(t)
        used += cost
    near_names = {t["name"] for t in near}
    far = [t for t in tree_rows if t["name"] not in near_names]
    rep["tree_rule"] = dict(
        rule="base of the tree within %.0f m of a walkable face centre; walkable = ENV_ground_colonnade_walk "
             "(845 paving faces) + the MAT_gravel_path faces of ENV_terrain_ground (8 952 faces, 19 783 m2). "
             "MAT_lawn is excluded: 489 424 m2 out to +-365 m would make every tree near." % g1.TREE_NEAR_RADIUS_M,
        trees_total=len(tree_rows), within_radius=len(within), near_exported=len(near), far_billboards=len(far),
        lod2_blob_objects=len(blob),
        lod2_blob_within_radius=len([t for t in blob if t["walk_dist_m"] <= g1.TREE_NEAR_RADIUS_M]),
        thin_fraction=g1.TREE_NEAR_THIN, near_tris_budget=tree_allow, near_tris_used=used,
        cut="the near list is the `within_radius` set truncated by the ENV budget, closest to the walk first; "
            "the remainder joins the impostor list (docs/briefs/phase6_plan.md section 4b, user's decision)")
    # near trees: thin the shared prototype mesh once, place N times
    near_by_mesh = {}
    for t in near:
        near_by_mesh.setdefault(t["mesh"], []).append(t)
    for mname, rows in sorted(near_by_mesh.items()):
        me = thin_cache[mname]
        before = thin_report[mname]["before"]
        after = thin_report[mname]["after"]
        meshes[me.name] = dict(cls="ENV", src_mesh=mname, src_tris=before, tris=after, target=None,
                               placements=len(rows), material=(me.materials[0].name if me.materials else None),
                               instanced=True, src_material=None, kind="tree_near")
        for t in rows:
            no = bpy.data.objects.new(t["name"], me)
            colls["EXP_ENV"].objects.link(no)
            placements.append((no, t["ob"]))
            assets[no.name] = dict(cls="ENV", mesh=me.name, tris=after,
                                   material=(me.materials[0].name if me.materials else None),
                                   instanced=True, kind="tree_near")
    rep["tree_thin"] = {k: v for k, v in thin_report.items() if k in near_by_mesh}
    # far trees: one 2-triangle billboard mesh per prototype, instanced per placement
    board_mat = grey("MAT_EXP_treeboard")
    board_mesh = {}
    far_rows = []
    for t in far:
        proto = t["mesh"]
        key = proto
        if key not in board_mesh:
            me = bpy.data.meshes.new(f"EXPM_treeboard_{proto}")
            me.from_pydata([(-0.5, 0.0, 0.0), (0.5, 0.0, 0.0), (0.5, 0.0, 1.0), (-0.5, 0.0, 1.0)], [],
                           [(0, 1, 2), (0, 2, 3)])
            me.update()
            me.uv_layers.new(name=g1.UV1)
            uv = me.uv_layers[g1.UV1].uv
            for i, c in enumerate(((0, 0), (1, 0), (1, 1), (0, 0), (1, 1), (0, 1))):
                uv[i].vector = c
            me.materials.append(board_mat)
            board_mesh[key] = me
            meshes[me.name] = dict(cls="ENV", src_mesh=proto, src_tris=2, tris=2, target=None, placements=0,
                                   material=board_mat.name, instanced=True, src_material=None, kind="tree_board")
        me = board_mesh[key]
        meshes[me.name]["placements"] += 1
        idx = len(far_rows)
        no = bpy.data.objects.new(f"{g1.BILLBOARD_PREFIX}{idx:03d}", me)
        no.location = Vector(t["base"])
        no.scale = (max(t["width_m"], 0.5), 1.0, max(t["height_m"], 0.5))
        colls["EXP_ENV"].objects.link(no)
        assets[no.name] = dict(cls="ENV", mesh=me.name, tris=2, material=board_mat.name, instanced=True,
                               kind="tree_board", prototype=proto, source_tree=t["name"],
                               height_m=t["height_m"], width_m=t["width_m"], trunk_base=t["base"],
                               walk_dist_m=t["walk_dist_m"])
        far_rows.append(dict(billboard=no.name, prototype=proto, source_tree=t["name"], height_m=t["height_m"],
                             width_m=t["width_m"], trunk_base=t["base"], walk_dist_m=t["walk_dist_m"]))
    rep["tree_far_list"] = far_rows
    rep["tree_near_list"] = [dict(name=t["name"], mesh=t["mesh"], walk_dist_m=t["walk_dist_m"],
                                  height_m=t["height_m"], lod1_tris=t["lod1_tris"]) for t in near]
    # shrubs at LOD2, shared mesh per prototype
    for mname, obs in sorted(shrub_by_mesh.items()):
        me = bpy.data.meshes.new_from_object(obs[0].evaluated_get(dg))
        me.name = f"EXPM_{mname}"
        t = tris_of(me)
        meshes[me.name] = dict(cls="ENV", src_mesh=mname, src_tris=t, tris=t, target=None, placements=len(obs),
                               material=(me.materials[0].name if me.materials else None), instanced=True,
                               src_material=None, kind="shrub")
        for ob in obs:
            no = bpy.data.objects.new(ob.name, me)
            colls["EXP_ENV"].objects.link(no)
            placements.append((no, ob))
            assets[no.name] = dict(cls="ENV", mesh=me.name, tris=t,
                                   material=(me.materials[0].name if me.materials else None),
                                   instanced=True, kind="shrub")
    rep["env_tree_s"] = round(time.time() - t0, 1)

    # ---------------------------------------------------------------- 7. placements (assert before the UVs)
    for no, so in placements:
        loc, rot, scl = MW[so.name].decompose()
        no.rotation_mode = "QUATERNION"
        no.location = loc
        no.rotation_quaternion = rot
        no.scale = scl
    bpy.context.view_layer.update()
    worst, worst_name = 0.0, ""
    for no, so in placements:
        d = (no.matrix_world.translation - MW[so.name].translation).length
        if d > worst:
            worst, worst_name = d, no.name
    assert worst < 1e-4, f"{worst_name} is {worst:.5f} m from its source"
    rep["placement_max_error_m"] = round(worst, 8)
    rep["placements_checked"] = len(placements)

    # ---------------------------------------------------------------- 8. UVs
    t0 = time.time()
    # UV1: one packed atlas per group
    uv_groups = {}
    for name, a in assets.items():
        ob = bpy.data.objects.get(name)
        if not ob or a.get("kind") in ("tree_board", "tree_near", "shrub", "backdrop"):
            continue
        uv_groups.setdefault(a["material"], set()).add(ob.data.name)
    uv1_done = set()
    atlas_tiles = {}
    for mat_name, mesh_names in sorted(uv_groups.items()):
        objs = []
        for mn in sorted(mesh_names):
            if mn in uv1_done:
                continue
            uv1_done.add(mn)
            me_ = bpy.data.meshes[mn]
            # the source UV layers are dropped here so UV1 is layer 0 (TEXCOORD_0) and UV2 layer 1; without
            # this the glb carried three UV sets and the first one was the unused inherited map.
            while len(me_.uv_layers):
                me_.uv_layers.remove(me_.uv_layers[0])
            o = bpy.data.objects.new(f"EXP_UVTMP_{mn}", me_)
            tmp.objects.link(o)
            objs.append(o)
        if not objs:
            continue
        smart_project(objs, g1.UV1, TILE_MARGIN)
        # smart_project packs EACH object into the full [0,1] even in multi-object edit mode (measured: the
        # five multi-mesh ARCH groups came back 100 % overlapped). Pack them here instead: a square tile per
        # mesh with side proportional to sqrt(its surface area), shelf-packed into the unit square, so texel
        # density follows the asset and the Gate 2 bake of one atlas cannot overwrite itself.
        if len(objs) > 1:
            areas = [(o, max(1e-9, sum(p.area for p in o.data.polygons))) for o in objs]
            areas.sort(key=lambda t: -t[1])
            tot_a = sum(a for _, a in areas)
            sides = [(o, math.sqrt(a / tot_a)) for o, a in areas]
            k = (1.0 - 2 * TILE_MARGIN) / math.sqrt(sum(sd * sd for _, sd in sides) * 1.6)
            sides = [(o, sd * k) for o, sd in sides]
            x = y = TILE_MARGIN
            row_h = 0.0
            tiles = {}
            for o, sd in sides:
                if x + sd > 1.0 - TILE_MARGIN:
                    x = TILE_MARGIN
                    y += row_h + TILE_MARGIN
                    row_h = 0.0
                if y + sd > 1.0 - TILE_MARGIN:          # ran out of room: shrink the rest into the last row
                    sd = max(1e-3, 1.0 - TILE_MARGIN - y)
                tiles[o.data.name] = (x, y, sd)
                uvs = o.data.uv_layers[g1.UV1].uv
                for i in range(len(uvs)):
                    u, v = uvs[i].vector
                    uvs[i].vector = (x + u * sd, y + v * sd)
                x += sd + TILE_MARGIN
                row_h = max(row_h, sd)
            atlas_tiles[mat_name] = {k2: [round(t, 5) for t in v2] for k2, v2 in tiles.items()}
        for o in objs:
            tmp.objects.unlink(o)
            bpy.data.objects.remove(o, do_unlink=True)
    rep["uv1_groups"] = len(uv_groups)
    rep["uv1_atlas_tiles"] = atlas_tiles
    # UV2: a [0,1] lightmap unwrap per unique bakeable mesh
    uv2_meshes = [mn for mn, m in meshes.items()
                  if m["cls"] in ("ARCH", "ORN") or (m["cls"] == "ENV" and m.get("kind") == "ground")]
    for mn in uv2_meshes:
        o = bpy.data.objects.new(f"EXP_UVTMP2_{mn}", bpy.data.meshes[mn])
        tmp.objects.link(o)
        smart_project([o], g1.UV2, UV2_MARGIN)
        o.data.uv_layers.active = o.data.uv_layers[g1.UV1] if g1.UV1 in o.data.uv_layers else o.data.uv_layers[0]
        tmp.objects.unlink(o)
        bpy.data.objects.remove(o, do_unlink=True)
    rep["uv2_meshes"] = len(uv2_meshes)
    rep["uv_s"] = round(time.time() - t0, 1)

    # ---------------------------------------------------------------- 9. lightmap slots
    slots = {"orn": [], "arch_inst": []}
    counters = {"orn": 0, "arch_inst": 0}
    for name, a in sorted(assets.items()):
        m = meshes[a["mesh"]]
        if not m["instanced"] or m["cls"] not in ("ARCH", "ORN"):
            continue
        pool = "orn" if m["cls"] == "ORN" else "arch_inst"
        i = counters[pool]
        counters[pool] += 1
        atlas, s, off, scale = g1.slot_uv(i)
        a["lightmap"] = dict(mode="slot", pool=pool, atlas=atlas, slot=s,
                             uv2_offset=off, uv2_scale=scale,
                             gutter_px=g1.ORN_ATLAS_GUTTER_PX, slot_px=g1.ORN_ATLAS_SLOT_PX)
        slots[pool].append(dict(object=name, atlas=atlas, slot=s))
    for name, a in assets.items():
        if "lightmap" in a:
            continue
        m = meshes[a["mesh"]]
        a["lightmap"] = (dict(mode="asset", size=2048)
                         if (m["cls"] == "ARCH" or (m["cls"] == "ENV" and a.get("kind") == "ground"))
                         else dict(mode="none"))
    rep["lightmap_slots"] = {k: dict(count=len(v), atlases=(max([r["atlas"] for r in v]) + 1) if v else 0)
                             for k, v in slots.items()}
    rep["lightmap_assets"] = sum(1 for a in assets.values() if a["lightmap"]["mode"] == "asset")

    # ---------------------------------------------------------------- 10. strip, cameras, save
    keep = set()
    for c in colls.values():
        keep |= {o.name for o in c.objects}
    keep |= {o.name for o in bpy.data.objects if o.type == "LIGHT"}
    removed = 0
    for ob in list(bpy.data.objects):
        if ob.name in keep or ob.type == "CAMERA":
            continue
        bpy.data.objects.remove(ob, do_unlink=True)
        removed += 1
    for c in list(bpy.data.collections):
        if c.name.startswith("EXP_") or len(c.objects):
            continue
        bpy.data.collections.remove(c)
    # Blender gave every exported object a ".001" suffix while its source of the same name was still loaded.
    # The source objects are gone now, so take the real names back - they are the manifest's keys and what the
    # name sweep reads.
    renames = {}
    for ob in bpy.data.objects:
        m = re.match(r"^(.*)\.\d{3}$", ob.name)
        if m and m.group(1) not in bpy.data.objects:
            renames[ob.name] = m.group(1)
            ob.name = m.group(1)
    if renames:
        assets = {renames.get(k, k): v for k, v in assets.items()}
        for pool in slots.values():
            for row in pool:
                row["object"] = renames.get(row["object"], row["object"])
    rep["renamed_back"] = len(renames)
    assert not [o for o in bpy.data.objects if re.search(r"\.\d{3}$", o.name)], \
        "an exported object still carries a .### name-collision suffix"
    if tmp.name in bpy.data.collections:
        bpy.data.collections.remove(tmp)
    qa_cameras.ensure(scene)
    scene.camera = bpy.data.objects[g0.HERO_CAM]
    common.purge_orphans()
    g0.save_copy(g1.SET_BLEND)
    rep["objects_removed"] = removed
    rep["set_blend"] = str(g1.SET_BLEND)
    rep["set_blend_bytes"] = g1.SET_BLEND.stat().st_size

    # ---------------------------------------------------------------- 11. totals and the manifest
    uv_missing = {"uv1": [], "uv2": []}
    multi_mat = []
    for mn, m in meshes.items():
        me = bpy.data.meshes.get(mn)
        if me is None:
            continue
        names = [u.name for u in me.uv_layers]
        if g1.UV1 not in names:
            uv_missing["uv1"].append(mn)
        if mn in uv2_meshes and g1.UV2 not in names:
            uv_missing["uv2"].append(mn)
        if len(me.materials) != 1:
            multi_mat.append((mn, len(me.materials)))
    rep["uv_missing"] = {k: v[:20] for k, v in uv_missing.items()}
    rep["uv_missing_counts"] = {k: len(v) for k, v in uv_missing.items()}
    rep["meshes_not_single_material"] = multi_mat[:20]
    cls_tris = {"ARCH": 0, "ORN": 0, "ENV": 0}
    cls_objs = {"ARCH": 0, "ORN": 0, "ENV": 0}
    for a in assets.values():
        cls_tris[a["cls"]] += a["tris"]
        cls_objs[a["cls"]] += 1
    uniq = {"ARCH": 0, "ORN": 0, "ENV": 0}
    for m in meshes.values():
        uniq[m["cls"]] += m["tris"]
    draw_calls = 0
    for mn in meshes:
        me = bpy.data.meshes.get(mn)
        draw_calls += max(1, len(me.materials)) if me else 1
    rep["totals"] = dict(placed_tris=cls_tris, placed_total=sum(cls_tris.values()),
                         unique_tris=uniq, unique_total=sum(uniq.values()),
                         objects=cls_objs, unique_meshes=len(meshes),
                         budget=g1.CLASS_BUDGET, budget_total=g1.TOTAL_BUDGET,
                         draw_call_batches=draw_calls)
    rep["voxel_remeshed"] = sorted(remeshed)
    for mn in remeshed:
        if mn in meshes:
            meshes[mn]["remeshed"] = True
    rep["assets"] = assets
    rep["meshes"] = meshes
    rep["wall_s"] = round(time.time() - t_all, 1)
    (g1.OUT / "export_set.json").write_text(json.dumps(rep, indent=1, default=str) + "\n")

    # ---- the ORN normal + AO bake jobs (brief item 2): 2K per prototype, 1K under ORN_SMALL_DIM_M
    jobs = []
    for mname, m in sorted(meshes.items()):
        if m["cls"] != "ORN":
            continue
        proto = m["src_mesh"]
        key = re.sub(r"_LOD0(_a)*$", "", re.sub(r"^ORN_", "", proto))
        size = g1.ORN_BAKE_SIZE_SMALL if m["max_dim_m"] < g1.ORN_SMALL_DIM_M else g1.ORN_BAKE_SIZE
        jobs.append(dict(id=f"orn_{key}", prototype=proto, lo=mname, lo_object=f"BAKE_LO_{proto}",
                         hi=f"EXPHI_{proto}", size=size,
                         tris=m["tris"], src_tris=m["src_tris"], placements=m["placements"],
                         max_dim_m=m["max_dim_m"],
                         normal=f"tex/orn_{key}_normal.png", ao=f"tex/orn_{key}_ao.png"))
    (g1.OUT / "bake_jobs.json").write_text(json.dumps(
        dict(set_blend=str(g1.SET_BLEND), bake_blend=str(g1.BAKE_BLEND), out=str(g1.TEX), jobs=jobs),
        indent=1) + "\n")
    rep["bake_jobs"] = len(jobs)

    stations = {}
    for cam in [o for o in bpy.data.objects if o.type == "CAMERA"]:
        d = cam.data
        stations[cam.name] = dict(location=[round(v, 6) for v in cam.location],
                                  rotation_euler_xyz=[round(v, 8) for v in cam.rotation_euler],
                                  rotation_mode=cam.rotation_mode, lens_mm=d.lens,
                                  sensor_width_mm=d.sensor_width, sensor_fit=d.sensor_fit,
                                  shift_x=d.shift_x, shift_y=d.shift_y, clip_start=d.clip_start,
                                  clip_end=d.clip_end, reference_photo=cam.get("reference_photo", ""))
    sun = next(o for o in bpy.data.objects if o.type == "LIGHT" and o.data.type == "SUN")
    sun_dir = (sun.matrix_world.to_quaternion() @ Vector((0, 0, -1))).normalized()
    man = dict(
        schema="pfa-phase6/2", gate="gate1", generator="export/export_set.py --gate1",
        source_blend=str(g1.SRC_BLEND),
        units=dict(scale_m=1.0, up_blender="+Z", up_gltf="+Y",
                   note="glb written with export_yup=True: Blender +Y -> glTF -Z, Blender +Z -> glTF +Y. "
                        "Every *_blender vector here is Blender Z-up; the viewer converts as (x, z, -y)."),
        water=dict(water_z=common.WATER_Z, plane_axis="blender_z", viewer_y=common.WATER_Z,
                   note="viewer plane at y = water_z; ENV_lagoon_water and ENV_backdrop_bay are not exported"),
        view=dict(view_transform=scene.view_settings.view_transform, look=scene.view_settings.look,
                  exposure_ev=scene.view_settings.exposure, gamma=scene.view_settings.gamma,
                  display_device=scene.display_settings.display_device),
        sun=dict(name=sun.name, energy_w_m2=sun.data.energy, color=[round(c, 6) for c in sun.data.color],
                 angle_rad=sun.data.angle, direction_blender=[round(v, 6) for v in sun_dir],
                 direction_gltf=[round(sun_dir.x, 6), round(sun_dir.z, 6), round(-sun_dir.y, 6)],
                 note="direction the light travels; the viewer's DirectionalLight is specular-only"),
        stations=stations, hero_camera=g0.HERO_CAM,
        assets=assets, meshes=meshes, totals=rep["totals"],
        voxel_remeshed=sorted(remeshed), orn_lo_from_lod1=lo_sources,
        voxel_remeshed_note="COLLAPSE stalls on these meshes (thousands of separate relief islands), so the "
                            "low-poly is a voxel shell and the relief lives entirely in the hi->lo normal map. "
                            "QA reads this list, not a cage-size proxy.",
        orn_slots=slots, tree_rule=rep["tree_rule"], tree_far=far_rows,
        tree_near=[r["name"] for r in rep["tree_near_list"]],
        textures={}, lut={}, sky={}, compositor={}, reference={},
        lightmap_scale=3.14159265358979,
    )
    g1.OUT.mkdir(parents=True, exist_ok=True)
    (g1.OUT / "manifest.json").write_text(json.dumps(man, indent=1, default=str) + "\n")

    # ---------------------------------------------------------------- 12. the slim bake file
    # Each of the 33 ORN bake jobs re-opens its source; the full set is 206 MB (89 packed foliage images,
    # 2 540 objects). Strip everything but the 33 lo/hi pairs at identity and save that instead.
    keep_hi = {o.name for o in bpy.data.objects if o.name.startswith("EXPHI_")}
    for ob in list(bpy.data.objects):
        if ob.name not in keep_hi:
            bpy.data.objects.remove(ob, do_unlink=True)
    bakecoll = bpy.data.collections.new("BAKE")
    scene.collection.children.link(bakecoll)
    for pname, me in orn_lo.items():
        bob = bpy.data.objects.new(f"BAKE_LO_{pname}", me)
        bakecoll.objects.link(bob)
        bob.matrix_world.identity()
    for ob in bpy.data.objects:
        ob.hide_viewport = False
        ob.hide_render = False
        ob.matrix_world.identity()
    common.purge_orphans()
    g0.save_copy(g1.BAKE_BLEND)
    rep["bake_blend_bytes"] = g1.BAKE_BLEND.stat().st_size
    (g1.OUT / "export_set.json").write_text(json.dumps(rep, indent=1, default=str) + "\n")

    step.done(g1.SET_BLEND, g1.BAKE_BLEND, g1.OUT / "export_set.json", g1.OUT / "manifest.json",
              placed=sum(cls_tris.values()), arch=cls_tris["ARCH"], orn=cls_tris["ORN"], env=cls_tris["ENV"],
              unique=sum(uniq.values()), objects=len(assets), meshes=len(meshes), batches=draw_calls,
              near_trees=len(near), far_trees=len(far), removed=removed)
    print("[gate1] totals", json.dumps(rep["totals"]))
    print("[gate1] tree rule", json.dumps({k: v for k, v in rep["tree_rule"].items() if k != "rule"}))
