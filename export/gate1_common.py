"""Shared constants for the Phase 6 Gate 1 export set (export engineer, branch `phase6-export`).

Extends export/gate0_common.py (paths, Step timer, save_copy, manifest helpers, colour constants) with the
Gate 1 selection rule, the per-asset decimation targets of docs/briefs/phase6_plan.md section 2 and the tree
near/far rule of section 4b as the user decided it (docs/decisions.md 2026-09-15 "User's three decisions").

Import from a Blender run as:

    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import gate1_common as g1
"""
import os
import re
from pathlib import Path

import gate0_common as g0

# review finding 8: one env-overridable root, not a fourth hard-coded copy.
MAIN_ROOT = Path(os.environ.get("PFA_MAIN_ROOT", str(g0.MAIN_ROOT)))
SRC_BLEND = MAIN_ROOT / "master_delivery.blend"
ROOT = g0.ROOT
OUT = ROOT / "export" / "out" / "gate1"
TEX = OUT / "tex"
QUEUE = ROOT / "export" / "out" / "bake_queue"
SET_BLEND = OUT / "gate1_set.blend"
BAKE_BLEND = OUT / "gate1_bake.blend"   # the 33 ORN lo/hi pairs only; what every bake job opens
UV1 = g0.UV1
UV2 = g0.UV2

# ---------------------------------------------------------------- selection (CLAUDE.md "Phase 6 / Sources")
# ARCH_/INST_ at LOD0, ENV_ at LOD1 (LOD2 for shrubs and the far trees), unsuffixed ARCH_/ENV_ always.
# ORN_ prototypes (origin-parked bake sources) and PH_ placeholders are never exported.
LOD_RE = re.compile(r"_LOD(\d)$")
NEVER_PREFIX = ("ORN_", "PH_", "SOCKET_", "CAM_", "LIGHT_")
# the water is a viewer plane at WATER_Z, never exported geometry (plan section 2)
NEVER_NAME = {"ENV_lagoon_water", "ENV_backdrop_bay"}

# ---------------------------------------------------------------- decimation targets
# ARCH: mesh-name prefix -> target triangles for the shared mesh (None = export as modelled).
ARCH_TARGETS = [
    # (regex on the MESH name, target tris, note)
    (r"^ARCH_(rotunda|colonnade_north|colonnade_south)(_inner)?_column_\d+_LOD0$", 3500, "fluted shaft, flutes -> normal map"),
    (r"^ARCH_.*_colbase_\d+_torus$", 600, "column base torus"),
    (r"^ARCH_rotunda_eggs_LOD0$", 8000, "egg-and-dart band"),
    # QA-11-9: decimating these two left 174 sliver triangles (thinness > 50, worst 610) in the merged
    # ceiling mesh, and cam04 looks straight at them - a long thin wedge across the coffers with a loose
    # shard beside it. They are 57.6 % of the defect box by ray cast and there is budget for the real
    # geometry, so both export as modelled: +104,828 placed tris, ARCH still 150,618 under its budget.
    (r"^ARCH_rotunda_vault_coffers_\d+$", None, "coffered vault sector - as modelled, cam04 looks at it"),
    (r"^ARCH_rotunda_ceiling_ribs$", None, "rib cage - as modelled, cam04 looks at it"),
    (r"^ARCH_site_rostra_meander_\d+$", 3000, "meander frieze band"),
    (r"^ARCH_.*_astragal_\d+$", 400, "astragal ring"),
    (r"^ARCH_rotunda_dome$", 6000, "dome shell"),
]
# ORN prototypes: regex on the MESH name -> target triangles (plan section 2, trimmed to hold 1.10 M placed).
ORN_TARGETS = [
    (r"^ORN_drum_band_", 1200),
    (r"^ORN_capital_colonnade_", 2000),
    (r"^ORN_capital_rotunda_", 6000),
    (r"^ORN_capital_inner_", 3000),
    (r"^ORN_maiden_", 4400),
    (r"^ORN_attic_figure_", 8000),
    (r"^ORN_attic_panel_", 8000),
    (r"^ORN_winged_figure_", 6000),
    (r"^ORN_urn_niche_", 2500),
    (r"^ORN_urn_", 2500),
    (r"^ORN_keystone_", 1500),
    (r"^ORN_rosette_ceiling_", 1500),
    (r"^ORN_frieze_rinceau_return_", 1500),
    (r"^ORN_frieze_rinceau_", 3000),
    (r"^ORN_corner_scroll_", 2000),
    (r"^ORN_finial_", 2000),
]
ORN_DEFAULT_TARGET = 3000
# QA round 11 blocker 2: the LOD0 attic panels are ~40 000 separate relief islands, COLLAPSE stalls on them and
# the voxel shell that replaced it read TORN at cam02/cam05 (figures in disconnected speckled fragments, black
# voids). Build their low-poly from the Phase 5 _LOD1 mesh instead - a clean, connected reduction - and let
# COLLAPSE take it to the target. The hi-poly bake source stays the LOD0 prototype.
ORN_LO_FROM_LOD1 = (r"^ORN_attic_panel_",)


def lo_from_lod1(proto_mesh_name):
    """The _LOD1 twin to use as the low-poly base, or None to use the LOD0 prototype itself."""
    if not any(re.match(pat, proto_mesh_name) for pat in ORN_LO_FROM_LOD1):
        return None
    return re.sub(r"_LOD0.*$", "_LOD1", proto_mesh_name)
# prototypes whose longest dimension is under 1 m bake at 1K, the rest at 2K (brief item 2)
ORN_BAKE_SIZE_SMALL = 1024
ORN_BAKE_SIZE = 2048
ORN_SMALL_DIM_M = 1.0

# ENV: near trees keep LOD1 thinned 50 %; far trees become tagged billboard quads; shrubs drop to LOD2.
TREE_NEAR_RADIUS_M = 25.0       # of the walkable area (brief item 1)
TREE_NEAR_THIN = 0.50           # decimate ratio applied to the near trees' LOD1 mesh
BILLBOARD_PREFIX = "ENV_treeboard_"

# ORN lightmap atlas (user's option (c)): a 256 px slot per instance on 4096 px atlases
ORN_ATLAS_SLOT_PX = 256
ORN_ATLAS_PX = 4096
ORN_ATLAS_SLOTS = (ORN_ATLAS_PX // ORN_ATLAS_SLOT_PX) ** 2      # 256 slots per atlas
# Review finding 3: slots that tile edge to edge have no gutter, so the Gate 3 bake margin, bilinear filtering
# and every mip pull the neighbouring instance. A 4 px border on every side (8 px off the slot in each axis)
# leaves 248 usable px, which still samples a 3 m capital 3.6x finer than the hero frame does.
ORN_ATLAS_GUTTER_PX = 8


def slot_uv(index):
    """index -> (atlas, slot, uv2_offset, uv2_scale) with the gutter applied. One source of truth: the export
    writes it into every asset and export/manifest_v2.py re-derives it from here."""
    atlas, s = divmod(int(index), ORN_ATLAS_SLOTS)
    per_row = ORN_ATLAS_PX // ORN_ATLAS_SLOT_PX
    row, col = divmod(s, per_row)
    half = ORN_ATLAS_GUTTER_PX / 2.0
    scale = (ORN_ATLAS_SLOT_PX - ORN_ATLAS_GUTTER_PX) / float(ORN_ATLAS_PX)
    off = [(col * ORN_ATLAS_SLOT_PX + half) / float(ORN_ATLAS_PX),
           (row * ORN_ATLAS_SLOT_PX + half) / float(ORN_ATLAS_PX)]
    return atlas, s, off, scale

# QA-12-1 / round 12 follow-up (lead, 2026-09-15). Two levers on the UV1 atlases:
#
# 1. UV1_SPLIT_MERGED - a group whose merged single-use mass dominates its atlas gives that mass its OWN
#    material and therefore its own 2K. Measured cause: the merged 130-object colonnade mass holds 76 % of
#    its group's surface area, so area weighting handed it 76 % of the atlas while its own island packing
#    tops out at 0.146 (smart project 0.146, pack_islands CONVEX 0.108, CONCAVE 0.144) - 0.76 x 0.15 capped
#    the group near 0.13 whatever the other meshes did. Split, the mass gets a whole square (1.3x density)
#    and the instanced meshes reach ~0.40 on theirs.
# 2. UV1_FINE_MARGIN_GROUPS - a merged mass that is ALREADY alone on its atlas only needs the finer island
#    margin (0.001 instead of 0.004): on the merged colonnade mesh that is 0.036 -> 0.114 self-coverage.
#
# Only the groups named here change; every other UV1 layer stays byte-identical, and the bake engineer
# re-bakes exactly these.
UV1_SPLIT_MERGED = {
    "MAT_EXP_ARCH_colonnade_north__MAT_concrete_colonnade",
    "MAT_EXP_ARCH_colonnade_south__MAT_concrete_colonnade",
}
UV1_FINE_MARGIN_GROUPS = {
    "MAT_EXP_ARCH_rotunda__MAT_concrete_ochre",
    "MAT_EXP_ARCH_rotunda__MAT_plaster_ceiling_rib",
    "MAT_EXP_ARCH_site__MAT_concrete_podium",
    "MAT_EXP_ENV__riprap",
}
# The three rotunda multi-mesh groups were pinned to the old layout while their Gate 2 bakes stood; the lead
# lifted the pin (2026-09-15) because they are being re-baked with the split.
UV1_LEGACY_PACK = set()

CLASS_BUDGET = {"ARCH": 1_100_000, "ORN": 1_100_000, "ENV": 800_000}
TOTAL_BUDGET = 3_000_000


def target_for(patterns, mesh_name, default=None):
    for pat, tgt, *_ in patterns:
        if re.match(pat, mesh_name):
            return tgt
    return default


def arch_target(mesh_name):
    return target_for(ARCH_TARGETS, mesh_name, None)


def orn_target(mesh_name):
    return target_for(ORN_TARGETS, mesh_name, ORN_DEFAULT_TARGET)


def lod_of(name):
    m = LOD_RE.search(name)
    return int(m.group(1)) if m else None


def ensure_dirs():
    for d in (OUT, TEX, QUEUE, OUT / "tex_gltf", OUT / "tex_ktx2"):
        d.mkdir(parents=True, exist_ok=True)
