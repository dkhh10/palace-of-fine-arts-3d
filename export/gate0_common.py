"""Shared constants and helpers for the Phase 6 Gate 0 slice (bake engineer, branch phase6-bake).

Nothing here writes to master_delivery.blend or master.blend. Every path under export/out/ is gitignored and
regenerable. Import from a Blender run as:

    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import gate0_common as g0
"""
import os
import sys
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # this checkout (the phase6-bake worktree)
MAIN_ROOT = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
SRC_BLEND = MAIN_ROOT / "master_delivery.blend"     # read-only bake/export source
OUT = ROOT / "export" / "out" / "gate0"
QUEUE = ROOT / "export" / "out" / "bake_queue"
WEB_RENDERS = ROOT / "renders" / "web"
SET_BLEND = OUT / "gate0_set.blend"                 # written by export_set.py, opened by every bake script

sys.path.insert(0, str(ROOT / "scripts"))

# --- the slice (docs/briefs/phase6_gate0.md "The slice") -------------------------------------------------
COLUMN_HI = "ARCH_rotunda_column_00_LOD0"           # mesh shared by ARCH_rotunda_column_00..15_LOD0
COLUMN_PLACEMENTS = [f"ARCH_rotunda_column_{i:02d}_LOD0" for i in range(16)]
CAPITAL_HI = "INST_capital_rotunda_000_LOD0"        # mesh ORN_capital_rotunda_v2_LOD0_a, 64 000 tris
COLUMN_TARGET_TRIS = 3500
CAPITAL_TARGET_TRIS = 6000
LO_COLUMN = "GATE0_column_lo"
LO_CAPITAL = "GATE0_capital_lo"
HI_COLUMN = "GATE0_column_hi"
HI_CAPITAL = "GATE0_capital_hi"
GROUND_NAME_FILE = OUT / "ground_name.txt"          # written by export_set.py from the ray cast
GATE0_COLL = "GATE0"
GATE0_HI_COLL = "GATE0_HI"                          # bake sources; excluded from render
HERO_CAM = "CAM_qa_01_lagoon_hero"
UV1 = "UVMap"                                       # material / PBR bake UVs on the low-poly
UV2 = "UV2"                                         # lightmap UVs (non-overlapping)
TEX_SIZE = 2048

# --- colour management (read from master_delivery.blend; asserted by the scripts) ------------------------
VIEW_TRANSFORM = "AgX"
LOOK = "AgX - High Contrast"
EXPOSURE_EV = -2.8331398963928223
# AgX log2 shaper domain, in stops around 0.18 mid grey (Blender's AgX config).
SHAPER_MIN_EV = -12.47393
SHAPER_MAX_EV = 4.026069
SHAPER_PIVOT = 0.18
LUT_SIZE = 65        # 33 left a 1.79/255 trilinear-interpolation error on mid grey; 65 brings it under 1/255


def log_shaper(v):
    """scene-linear (post-exposure) -> [0,1] AgX log2 shaper coordinate."""
    import math
    x = max(float(v), 1e-10) / SHAPER_PIVOT
    ev = math.log2(x)
    return min(max((ev - SHAPER_MIN_EV) / (SHAPER_MAX_EV - SHAPER_MIN_EV), 0.0), 1.0)


def shaper_inverse(x):
    """[0,1] shaper coordinate -> scene-linear (post-exposure) value."""
    ev = SHAPER_MIN_EV + float(x) * (SHAPER_MAX_EV - SHAPER_MIN_EV)
    return SHAPER_PIVOT * (2.0 ** ev)


# --- small utilities -------------------------------------------------------------------------------------
class Step:
    """Wall-clock timer that prints the line the brief asks for."""

    def __init__(self, name):
        self.name = name
        self.t0 = time.time()

    def done(self, *paths, **extra):
        dt = time.time() - self.t0
        sizes = []
        for p in paths:
            p = Path(p)
            sizes.append(f"{p.name}={p.stat().st_size if p.exists() else -1}B")
        tail = " ".join(sizes)
        kv = " ".join(f"{k}={v}" for k, v in extra.items())
        print(f"[gate0] STEP {self.name} wall_s={dt:.1f} {tail} {kv}".rstrip())
        return dt


def script_argv():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def ensure_dirs():
    for d in (OUT, QUEUE, WEB_RENDERS, OUT / "tex"):
        d.mkdir(parents=True, exist_ok=True)


def queue_state(state):
    """export/out/bake_queue/status.json - the viewer engineer reads this before touching the GPU."""
    QUEUE.mkdir(parents=True, exist_ok=True)
    (QUEUE / "status.json").write_text(json.dumps(
        {"state": state, "owner": "phase6-bake", "updated": time.strftime("%Y-%m-%dT%H:%M:%S%z")}, indent=1) + "\n")


def manifest_read():
    p = OUT / "manifest.json"
    if p.exists():
        return json.loads(p.read_text())
    return {}


def manifest_write(man):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    return OUT / "manifest.json"


def manifest_merge(**kw):
    man = manifest_read()
    for k, v in kw.items():
        if isinstance(v, dict) and isinstance(man.get(k), dict):
            man[k].update(v)
        else:
            man[k] = v
    return manifest_write(man)


# --- Blender-only helpers (import bpy lazily so the module is usable from system python) ------------------
def guard_no_master_write():
    """Abort if anything is about to be saved over a master*.blend."""
    import bpy
    fp = bpy.data.filepath
    if Path(fp).name.startswith("master"):
        return fp
    return None


def save_copy(path):
    """Save a .blend COPY; bpy.data.filepath keeps pointing at the read-only source."""
    import bpy
    path = Path(path)
    if path.name.startswith("master"):
        raise SystemExit(f"refusing to write {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(path), copy=True, compress=False)
    return path


def tri_count(obj):
    import bpy
    dg = bpy.context.evaluated_depsgraph_get()
    me = obj.evaluated_get(dg).to_mesh()
    n = sum(len(p.vertices) - 2 for p in me.polygons)
    obj.evaluated_get(dg).to_mesh_clear()
    return n


def apply_final_cycles_checked(scene=None, samples=None):
    """light_presets.apply_final_cycles + the assertion the brief demands: the two Eevee-only rigs are OFF.

    What "off" means (scripts/light_presets.py, docs/tech_notes.md "The two Eevee-only rigs"):
      * every LIGHT_rotunda_vault_bounce_* is back at its own `energy_W` custom property with use_custom_distance
        False (the Eevee override is x6.0 energy + a 21 m cutoff),
      * every LIGHT_shade_fill* is at its `energy_W` (the Cycles value), never at `energy_W_eevee`.
    Raises if any light is still carrying its Eevee value. Returns the per-light state it checked.
    """
    import bpy
    import light_presets as lp
    s = scene or bpy.context.scene
    lp.apply_final_cycles(s, samples=samples)
    state, bad = [], []
    for o in bpy.data.objects:
        if o.type != "LIGHT":
            continue
        base = o.get("energy_W")
        eev = o.get("energy_W_eevee")
        row = dict(name=o.name, energy=round(o.data.energy, 3), hide_render=o.hide_render,
                   energy_W=base, energy_W_eevee=eev,
                   custom_distance=bool(getattr(o.data, "use_custom_distance", False)))
        state.append(row)
        if base is not None and abs(o.data.energy - float(base)) > 1e-3:
            bad.append(row)
        if o.name.startswith("LIGHT_rotunda_vault_bounce") and row["custom_distance"]:
            bad.append(row)
    if bad:
        raise SystemExit(f"[gate0] Eevee-only rig still active in Cycles: {bad}")
    n_shade = sum(1 for r in state if r["name"].startswith("LIGHT_shade_fill"))
    n_vault = sum(1 for r in state if r["name"].startswith("LIGHT_rotunda_vault_bounce"))
    print(f"[gate0] apply_final_cycles ok: engine={s.render.engine} lights={len(state)} "
          f"shade_fill={n_shade} vault_bounce={n_vault} (all at energy_W, no custom distance)")
    return state
