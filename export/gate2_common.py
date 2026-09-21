"""Shared constants and helpers for the Phase 6 Gate 2 PBR bake (bake engineer, branch `phase6-bake`).

Extends export/gate0_common.py (paths, Step, manifest helpers, colour constants) and export/gate1_common.py
(the frozen Gate 1 set). Nothing here writes to master*.blend.

Sources (both read-only):
  geometry + UV1/UV2 : the frozen Gate 1 set, `gate1_set.blend` / `gate1_bake.blend` (SET_BLEND / BAKE_BLEND)
  materials          : the REGENERATED master_delivery.blend (MAT r10), appended by name at Gate 2

Import from a Blender run as:

    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import gate2_common as g2
"""
import json
import os
import re
from pathlib import Path

import gate0_common as g0
import gate1_common as g1

MAIN_ROOT = g1.MAIN_ROOT
SRC_BLEND = g1.SRC_BLEND                      # master_delivery.blend, materials only, never saved
ROOT = g0.ROOT
OUT = ROOT / "export" / "out" / "gate2"
TEX = OUT / "tex"
QUEUE = ROOT / "export" / "out" / "bake_queue"
# Gate 1's JSON lives in the export engineer's worktree and is synced to MAIN; this worktree has no copy.
GATE1_OUT = g1.OUT if (g1.OUT / "export_set.json").exists() else (MAIN_ROOT / "export" / "out" / "gate1")
UV1 = g0.UV1
UV2 = g0.UV2

# The frozen Gate 1 blends live in the export engineer's worktree and are never synced (325 MB).
# PFA_GATE1_BLEND_DIR overrides; the default is the phase6-export worktree beside this one.
# r4 finding 2: LOCAL THEN MAIN, never another worktree. This used to default to the phase6-export
# worktree, so a Gate 2 run in any other checkout baked THAT branch's geometry; it failed loudly in the 8d
# chain only because a mesh had been renamed (a geometry-only change would have baked silently). The
# checkout this file lives in wins when it has a Gate 1 blend; MAIN is the fallback; PFA_GATE1_BLEND_DIR
# still overrides both.
_LOCAL_G1 = Path(__file__).resolve().parents[1] / "export" / "out" / "gate1"
_DEFAULT_G1 = _LOCAL_G1 if (_LOCAL_G1 / "gate1_set.blend").exists() else (MAIN_ROOT / "export" / "out" / "gate1")
GATE1_BLEND_DIR = Path(os.environ.get("PFA_GATE1_BLEND_DIR", str(_DEFAULT_G1)))
SET_BLEND = GATE1_BLEND_DIR / "gate1_set.blend"
BAKE_BLEND = GATE1_BLEND_DIR / "gate1_bake.blend"
EXPORT_SET_JSON = GATE1_OUT / "export_set.json"       # synced copy in this worktree / MAIN

# ---------------------------------------------------------------- what gets baked
# One bake job per UV1 atlas group (ARCH / ENV ground / ENV backdrop) or ORN prototype.
# Classes, by the group material name the Gate 1 export wrote into every mesh record:
CLS_ARCH = "arch"          # MAT_EXP_ARCH_<zone>__<src material>
CLS_GROUND = "ground"      # MAT_EXP_ENV__<ground object>
CLS_BACKDROP = "backdrop"  # MAT_EXP_ENVBD__<src material>   - no UV1 in the Gate 1 set, generated here
CLS_ORN = "orn"            # MAT_EXP_ORN__<prototype mesh>

# foliage keeps its shipped 1K bark/leaf textures, the treeboards are Gate 3 impostors,
# MAT_water_lagoon is a viewer plane - none of them is baked here.
NO_BAKE_MATERIALS = re.compile(r"^(MAT_EXP_treeboard|MAT_bark_|MAT_shrub|MAT_reeds|MAT_leaf|MAT_water_lagoon)")

SIZE_DEFAULT = 2048
SIZE_BACKDROP = 1024
SIZE_SMALL = 1024          # ORN prototypes whose longest dimension is under ORN_SMALL_DIM_M
ORN_SMALL_DIM_M = g1.ORN_SMALL_DIM_M

MAPS = ("albedo", "roughness", "normal")

# Cycles bake settings (the Gate 0 numbers: DIFFUSE colour-only and ROUGHNESS are noise-free at low spp
# because no light path is involved; NORMAL needs 4).
SAMPLES_ALBEDO = 16
SAMPLES_ROUGHNESS = 16
SAMPLES_NORMAL = 4
BAKE_MARGIN_PX = 16


def tex_name(job_id, kind):
    return f"gate2_{job_id}_{kind}.png"


def size_for(cls, max_dim_m=None):
    if cls == CLS_BACKDROP:
        return SIZE_BACKDROP
    if cls == CLS_ORN and max_dim_m is not None and max_dim_m < ORN_SMALL_DIM_M:
        return SIZE_SMALL
    return SIZE_DEFAULT


def ensure_dirs():
    for d in (OUT, TEX, QUEUE, OUT / "tex_gltf", OUT / "tex_ktx2", OUT / "bake"):
        d.mkdir(parents=True, exist_ok=True)


def read_export_set():
    return json.loads(EXPORT_SET_JSON.read_text())


def jobs_path():
    return OUT / "bake_jobs.json"


def read_jobs():
    return json.loads(jobs_path().read_text())


# ---------------------------------------------------------------- Blender-side helpers
def append_materials(names, src_blend=None):
    """Append materials by name from master_delivery.blend and return {name: material}.

    The Gate 1 blend was written from the OLD delivery file, so every material it carries may be stale.
    Appended copies land as `<name>.001` when a same-named datablock already exists; this renames the old one
    out of the way first so the appended datablock keeps the exact name the manifest uses.
    """
    import bpy
    src = str(src_blend or SRC_BLEND)
    wanted = sorted({n for n in names if n})
    for n in wanted:
        old = bpy.data.materials.get(n)
        if old is not None:
            old.name = f"STALE_{n}"
    with bpy.data.libraries.load(src, link=False) as (data_from, data_to):
        missing = [n for n in wanted if n not in data_from.materials]
        data_to.materials = [n for n in wanted if n in data_from.materials]
    got = {}
    for m in data_to.materials:
        if m is None:
            continue
        got[m.name] = m
    return got, missing


def uv1_of(me):
    import bpy  # noqa: F401
    return me.uv_layers.get(UV1)


def smart_uv1(objs, angle_limit=1.15, island_margin=0.004):
    """Deterministic UV1 for a mesh that has none (the ten Gate 1 backdrop merges).

    Same call the Gate 1 export used for its groups, so the layout is reproducible from the same mesh:
    one multi-object smart project over the group, packed into [0,1] with a 0.004 margin.
    """
    import bpy
    for ob in objs:
        lay = ob.data.uv_layers.get(UV1)
        # PHASE 9 GUARD (export engineer, branch phase9-backdrop-export). The ENV build authors a TILE UV
        # on every backdrop mesh, in world metres / tile size, and it is ALSO called "UVMap" - the join in
        # gate1_set.py carries it into these merges. `smart_uv1` only creates a layer when none exists, so
        # a re-bake would smart-project ON TOP of the tile UV: the bake atlas would overwrite it and the
        # four gain tiles would be sampled at atlas coordinates. That is silent in every number the bake
        # reports, so it stops here instead. The fix when this fires: bake to a second layer (the Gate 1
        # relay calls it "UVBake" and ships it as TEXCOORD_1 - export/gltf_gate1.py `UV1_BAKE`) and hand
        # THAT layer's loops over in backdrop_uv1.npz.
        if lay is not None and len(ob.data.loops):
            import numpy as _np
            _a = _np.empty(len(ob.data.loops) * 2, dtype=_np.float32)
            try:
                lay.uv.foreach_get("vector", _a)
            except (AttributeError, TypeError):
                lay.data.foreach_get("uv", _a)
            _a = _a.reshape(-1, 2)
            _span = float(max(_a[:, 0].max() - _a[:, 0].min(), _a[:, 1].max() - _a[:, 1].min()))
            # review r1 carry 4: the span alone cannot do this job (backdrop_door_green's tile UV spans
            # 0.941), so the layer the Gate 1 relay appends is the primary tell and the span is the backup.
            assert ob.data.uv_layers.get("UVBake") is None, (
                f"{ob.name} carries a 'UVBake' layer, so its '{UV1}' is the Phase 9 backdrop TILE UV and "
                f"smart_uv1 would bake over it. Bake to 'UVBake' (TEXCOORD_1) and hand THAT layer over "
                f"in backdrop_uv1.npz.")
            assert _span <= 1.5, (
                f"{ob.name}: its '{UV1}' spans {_span:.2f} UV units - that is the Phase 9 backdrop TILE UV, "
                f"not a packed bake layout, and smart_uv1 would bake over it. Bake to a second layer "
                f"('UVBake', TEXCOORD_1) and hand that one over in backdrop_uv1.npz.")
        if lay is None:
            ob.data.uv_layers.new(name=UV1)
        ob.data.uv_layers[UV1].active = True
        ob.data.uv_layers[UV1].active_render = True
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=angle_limit, island_margin=island_margin,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    return [ob.name for ob in objs]
