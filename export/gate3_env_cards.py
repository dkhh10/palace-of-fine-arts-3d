"""Which env.glb card meshes have neither a lightmap nor COLOR_0, and can they take a per-MESH vertex bake?

CPU only, no Blender. Reads the Gate 1 export set and the Gate 3 manifest / npz (from this worktree, or
from MAIN via PFA_MAIN_ROOT when the worktree has no copy - Gate 1 was produced on the export branch).

    python3 export/gate3_env_cards.py

The second question is the important one. `bake_lm.py`'s `vertex` job bakes each MESH once, at the first
object that uses it, and records the rest as `shared_with`. That is nearly harmless for the 14 near trees
(1-3 placements each). It is NOT harmless for a mesh whose placements are scattered over the site: every
instance would take the irradiance of one arbitrary representative. So this script reports, per candidate
mesh, how far apart its placements actually are.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MAIN = Path(os.environ.get("PFA_MAIN_ROOT", "/Users/dk/Projects/3d render blender 3rd attempt building"))
EXCLUDE_TOKENS = ("backdrop", "lawn", "bird", "lamp_post")   # backdrop group: not planting
OUT_JSON = ROOT / "export" / "out" / "gate3" / "env_cards.json"


def pick(rel):
    """Prefer this worktree's copy, fall back to MAIN (Gate 1 lives on the export branch)."""
    for base in (ROOT, MAIN):
        p = base / rel
        if p.exists():
            return p
    raise FileNotFoundError(rel)


def main():
    eset = json.loads(pick("export/out/gate1/export_set.json").read_text())
    man3 = json.loads(pick("export/out/gate3/manifest.json").read_text())
    npz = np.load(str(pick("export/out/gate3/vertex_irradiance.npz")))
    have_color0 = set(npz.files)
    meshes, assets = eset["meshes"], eset["assets"]

    cand = []
    for mn, m in meshes.items():
        if m.get("cls") != "ENV" or mn in have_color0 or mn.startswith("EXPM_treeboard"):
            continue
        if any(t in mn for t in EXCLUDE_TOKENS):
            continue
        objs = [v for v in assets.values() if v.get("mesh") == mn]
        if not objs or any((o.get("lightmap") or {}).get("mode") == "asset" for o in objs):
            continue
        cand.append((mn, m, objs))

    rows = []
    print(f"{'mesh':34s} {'plc':>4s} {'tris':>5s} {'spread_m':>9s} {'z_min':>6s} {'z_max':>6s}  material")
    for mn, m, objs in sorted(cand, key=lambda r: -len(r[2])):
        P = np.array([o["location_blender"] for o in objs], dtype=float)
        spread = float(np.linalg.norm(P.max(axis=0) - P.min(axis=0)))
        rows.append(dict(mesh=mn, placements=len(objs), tris=m.get("tris", 0),
                         material=m.get("material"), kind=m.get("kind"),
                         spread_m=round(spread, 1),
                         z_min=round(float(P[:, 2].min()), 2), z_max=round(float(P[:, 2].max()), 2)))
        print(f"{mn:34s} {len(objs):4d} {m.get('tris', 0):5d} {spread:9.1f} "
              f"{P[:, 2].min():6.2f} {P[:, 2].max():6.2f}  {m.get('material')}")

    n_plc = sum(r["placements"] for r in rows)
    tris = sum(r["tris"] for r in rows)
    weighted = sum(r["spread_m"] * r["placements"] for r in rows) / max(n_plc, 1)
    allP = np.array([o["location_blender"] for _, _, objs in cand for o in objs], dtype=float)
    site = (allP.max(axis=0) - allP.min(axis=0))
    mats = sorted({r["material"] for r in rows})
    summary = dict(
        meshes=len(rows), placements=n_plc, unique_mesh_tris=tris,
        verts_upper_bound=tris * 2,                       # cards are quads: <= 2 verts per tri
        materials={mm: sum(1 for r in rows if r["material"] == mm) for mm in mats},
        placement_weighted_spread_m=round(weighted, 1),
        site_extent_m=[round(float(v), 1) for v in site],
        meshes_over_20_placements=sum(1 for r in rows if r["placements"] > 20),
        max_placements_on_one_mesh=max(r["placements"] for r in rows),
        existing_color0_meshes=len(have_color0),
        existing_color0_verts=int(man3["lightmaps"]["vertex_irradiance"]["verts"]),
        existing_color0_in_glb=bool(man3["lightmaps"]["vertex_irradiance"]["in_glb"]),
    )
    print()
    print(json.dumps(summary, indent=1))
    print()
    print("VERDICT: a per-MESH vertex bake gives all "
          f"{n_plc} placements only {len(rows)} distinct irradiances, chosen by one arbitrary "
          f"representative each, while those placements are spread {weighted:.0f} m apart on average "
          f"across a {site[0]:.0f} x {site[1]:.0f} m site. Per-PLACEMENT is the only correct granularity.")
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(dict(summary=summary, meshes=rows), indent=1))
    print(f"wrote {OUT_JSON}")


main()
