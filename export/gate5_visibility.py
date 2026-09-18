#!/usr/bin/env python3
"""6b Gate 5 item A: per-station, per-asset visibility of the frozen export set.

    scripts/blender_run.sh 1800 -- --background \
        <gate1_set.blend> --python export/gate5_visibility.py -- [--rays 480x270] [--out <dir>]

CPU only - no Cycles, no Eevee, no GPU.  `scene.ray_cast` is fired on a regular grid over each QA
station's own frame (the station's camera intrinsics come from the MANIFEST, which is what the viewer
uses, never from a camera re-derived here), and the FIRST hit object is counted.  The result is the
ordering key for the load tiers: an asset the hero never sees does not belong in tier 0, and an asset
that covers 3 % of the hero frame does.

Why a ray grid and not a render: a render would need the GPU (the viewer engineer owns it this round)
and would answer in pixels of colour, not in object identity.  A first-hit ray IS the occlusion test -
it reports the asset the walker actually sees, with the near vault in front of the far one, which is
exactly the ordering the tiers need.

Output (`--out`, default $PFA_MAIN_ROOT/export/out/gate5):
  visibility.json   schema pfa-phase6/gate5-visibility/1
    stations{}          the intrinsics used, the ray grid, the miss (sky) fraction
    assets{asset}       {station: fraction}, plus hero, first_station, max_fraction, n_stations
    unknown{}           first-hit object names that are NOT manifest assets (must be empty)
"""
import json
import math
import os
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
MAIN = Path(os.environ.get("PFA_MAIN_ROOT", "/Users/dk/Projects/3d render blender 3rd attempt building"))
HERO = "CAM_qa_01_lagoon_hero"


def argv():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = {"rays": "480x270", "out": str(MAIN / "export/out/gate5"),
           "manifest": str(MAIN / "export/out/gate3/manifest.json")}
    i = 0
    while i < len(a):
        k = a[i].lstrip("-")
        if k in out and i + 1 < len(a):
            out[k] = a[i + 1]
            i += 2
        else:
            i += 1
    return out


def station_rays(st, w, h):
    """Unit ray directions in WORLD space for the centre of every cell of a w x h grid, plus the origin.

    Blender's camera: -Z forward, +Y up in camera space; `shift_x`/`shift_y` are fractions of the sensor's
    FIT dimension (HORIZONTAL here, so of `sensor_width_mm` for both axes); with a horizontal fit the
    vertical extent is sensor_width / aspect.
    """
    from mathutils import Euler
    loc = Vector(st["location"])
    rot = Euler(st["rotation_euler_xyz"], st.get("rotation_mode", "XYZ")).to_matrix()
    sw = float(st["sensor_width_mm"])
    lens = float(st["lens_mm"])
    sx, sy = float(st.get("shift_x", 0.0)), float(st.get("shift_y", 0.0))
    aspect = w / h
    dirs = []
    for j in range(h):
        # v measured from the TOP row, as a render is
        cy = ((1.0 - (j + 0.5) / h) - 0.5) * (sw / aspect) + sy * sw
        for i in range(w):
            cx = ((i + 0.5) / w - 0.5) * sw + sx * sw
            d = rot @ Vector((cx, cy, -lens))
            d.normalize()
            dirs.append(d)
    return loc, dirs


def main():
    args = argv()
    w, h = (int(x) for x in args["rays"].lower().split("x"))
    outdir = Path(args["out"])
    outdir.mkdir(parents=True, exist_ok=True)
    man = json.loads(Path(args["manifest"]).read_text())
    assets = man["assets"]
    stations = {k: v for k, v in man["stations"].items() if k != "CAM_flythrough"}

    scene = bpy.context.scene
    # The bake's hi-poly sources (EXPHI_*, one per ORN prototype) sit inside their own LOD0 export mesh and
    # are NOT in the export set, so a first hit on one is a hit on nothing the viewer will ever load.  Every
    # object that is not a manifest asset is unlinked from the scene before a single ray is cast, and named
    # in `excluded` - never silently, because an exclusion that is wrong moves an asset out of tier 0.
    # The blend is only ever READ; nothing is saved.
    excluded = []
    for o in list(scene.objects):
        if o.type == "MESH" and o.name not in assets:
            excluded.append(o.name)
            for c in list(o.users_collection):
                c.objects.unlink(o)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    n_obj = sum(1 for o in scene.objects if o.type == "MESH")
    print(f"[gate5vis] excluded {len(excluded)} non-asset mesh objects: {sorted(excluded)[:6]}"
          f"{' ...' if len(excluded) > 6 else ''}", flush=True)
    print(f"[gate5vis] blend={bpy.data.filepath} mesh_objects={n_obj} manifest_assets={len(assets)} "
          f"stations={len(stations)} grid={w}x{h}", flush=True)

    per_station = {}
    counts = {}          # asset -> {station: hits}
    unknown = {}
    for name, st in sorted(stations.items()):
        t0 = time.time()
        origin, dirs = station_rays(st, w, h)
        far = float(st.get("clip_end", 5000.0))
        hits = 0
        local = {}
        for d in dirs:
            ok, _loc, _nrm, _idx, obj, _mw = scene.ray_cast(dg, origin, d, distance=far)
            if not ok or obj is None:
                continue
            hits += 1
            nm = obj.name
            local[nm] = local.get(nm, 0) + 1
        total = w * h
        for nm, c in local.items():
            if nm not in assets:
                unknown[nm] = unknown.get(nm, 0) + c
            counts.setdefault(nm, {})[name] = c / total
        per_station[name] = dict(rays=total, hit_fraction=hits / total, sky_fraction=1.0 - hits / total,
                                 objects_hit=len(local), wall_s=round(time.time() - t0, 1),
                                 lens_mm=st["lens_mm"], sensor_width_mm=st["sensor_width_mm"],
                                 shift_x=st.get("shift_x", 0.0), shift_y=st.get("shift_y", 0.0),
                                 location=st["location"], aspect=w / h)
        print(f"[gate5vis] {name}: {len(local)} objects, sky {100 * (1 - hits / total):.1f} %, "
              f"{time.time() - t0:.1f} s", flush=True)

    order = list(stations)
    out_assets = {}
    for nm, by in counts.items():
        first = next((s for s in order if by.get(s, 0) > 0), None)
        out_assets[nm] = dict(by_station={k: round(v, 6) for k, v in sorted(by.items())},
                              hero=round(by.get(HERO, 0.0), 6),
                              first_station=first,
                              max_fraction=round(max(by.values()), 6),
                              n_stations=len(by),
                              cls=(assets.get(nm) or {}).get("cls"))

    doc = dict(schema="pfa-phase6/gate5-visibility/1",
               generator="export/gate5_visibility.py",
               source_blend=bpy.data.filepath,
               manifest=str(args["manifest"]),
               hero_camera=HERO,
               grid=[w, h],
               method=("scene.ray_cast on a regular grid over each station's own frame; first hit only. "
                       "Intrinsics from the manifest's `stations` block (lens, sensor, shift), Blender "
                       "camera convention (-Z forward, shift in units of the sensor fit dimension)."),
               excluded_objects=sorted(excluded),
               stations=per_station,
               station_order=order,
               assets=dict(sorted(out_assets.items())),
               unknown=dict(sorted(unknown.items())),
               totals=dict(assets_seen=len(out_assets), assets_in_manifest=len(assets),
                           hero_visible=sum(1 for a in out_assets.values() if a["hero"] > 0),
                           never_visible=len(assets) - len(out_assets)))
    p = outdir / "visibility.json"
    p.write_text(json.dumps(doc, indent=1))
    print(f"[gate5vis] wrote {p} ({p.stat().st_size} B): {doc['totals']}", flush=True)
    if unknown:
        print(f"[gate5vis] WARNING {len(unknown)} first-hit objects are not manifest assets: "
              f"{sorted(unknown)[:10]}", flush=True)


if __name__ == "__main__":
    main()
