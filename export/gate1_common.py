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
    (r"^ARCH_rotunda_vault_coffers_\d+$", 6000, "coffered vault sector"),
    (r"^ARCH_rotunda_ceiling_ribs$", 8000, "rib cage"),
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
