"""Gate 4: merge the `inst_irr_*` bake records into out/gate3/instance_irradiance.json.

    python3 export/gate3_instance_compose.py

CPU only, no Blender, no GPU. One scene-linear RGB per PLACEMENT of the 28 shrub/reed card meshes, in the
same units as a DECODED lightmap texel and as vertex_irradiance.npz (irradiance / pi; x lightmaps.scale).

THE REDUCTION, and why it is the non-zero mean. A leaf card's own material is alpha cut-out: where a vertex
falls in a transparent texel the DIFFUSE bake returns exactly 0. Measured on inst_probe (12 placements, both
variants, out/gate3/bake/inst_probe.json): with the card's own material only 10.7 % of vertices came back
non-zero and one placement of twelve was entirely black, so the plain vertex mean is 10-50x too dark and
carries no light information at all. The production bake therefore replaces the card material with an opaque
grey Principled (`color: false` divides the albedo out, so the measured quantity is unchanged) and turns the
card's shadow ray visibility off, which lifts coverage to 0.86 mean with no black placement. The remaining
zeros are the card vertices buried in the terrain (their hemisphere is fully blocked); averaging them in
would darken a placement by its own buried fraction, which is geometry, not light. `rgb` is therefore the
mean over the vertices that received light; `cov` ships beside it so the consumer can see how many that was.

Also runs sanity checks 2 and 3 of the brief (the near-tree neighbour and the 1 379 count); check 1 (shaded
colonnade vs sunlit lawn against the ground lightmap) needs a ray cast and lives in gate3_instance_check.py.
"""
import json
import os
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MAIN = Path(os.environ.get("PFA_MAIN_ROOT", "/Users/dk/Projects/3d render blender 3rd attempt building"))
OUT = ROOT / "export" / "out" / "gate3"
OUT_JSON = OUT / "instance_irradiance.json"
LUM = np.array([0.2126, 0.7152, 0.0722], dtype=np.float64)


def pick(rel):
    for base in (ROOT, MAIN):
        p = base / rel
        if p.exists():
            return p
    raise FileNotFoundError(rel)


def r6(v):
    return [round(float(x), 6) for x in v]


def main():
    plan = json.loads((OUT / "instance_jobs.json").read_text())
    cards = json.loads((OUT / "env_cards.json").read_text())
    order = [(d["object"], d["mesh"]) for d in plan["objects"]]
    mesh_of = dict(order)

    recs, got = {}, {}
    variant = plan["variants"][0]
    for jid in plan["jobs"]:
        rec = json.loads((OUT / "bake" / f"{jid}.json").read_text())
        recs[jid] = {k: v for k, v in rec.items() if k != "results"}
        assert not rec["missing"], f"{jid}: missing objects {rec['missing']}"
        res = rec["results"][variant]
        recs[jid]["bake_s"], recs[jid]["coverage_mean"] = res["bake_s"], res["coverage_mean"]
        for it in res["items"]:
            assert it["object"] not in got, f"duplicate placement {it['object']}"
            got[it["object"]] = it

    missing = [o for o, _ in order if o not in got]
    assert not missing, f"{len(missing)} placements never baked, first: {missing[:5]}"
    assert len(got) == cards["summary"]["placements"] == len(order), \
        f"{len(got)} baked != {cards['summary']['placements']} in env_cards.json"

    meshes, all_rgb = {}, []
    for obj, mesh in order:                               # export-set order, per mesh
        it = got[obj]
        assert it["mesh"] == mesh, f"{obj}: baked mesh {it['mesh']} != export set {mesh}"
        rgb = np.array(it["mean_nonzero"], dtype=np.float64)
        all_rgb.append(rgb)
        meshes.setdefault(mesh, []).append(dict(object=obj, rgb=r6(rgb), cov=round(it["coverage"], 3)))
    A = np.array(all_rgb)

    out_meshes, rows = {}, []
    for mesh, plc in meshes.items():
        M = np.array([p["rgb"] for p in plc], dtype=np.float64)
        lum = M @ LUM
        out_meshes[mesh] = dict(n=len(plc),
                                min=r6(M.min(axis=0)), max=r6(M.max(axis=0)), mean=r6(M.mean(axis=0)),
                                lum_min=round(float(lum.min()), 6), lum_max=round(float(lum.max()), 6),
                                lum_mean=round(float(lum.mean()), 6),
                                lum_ratio=round(float(lum.max() / max(lum.min(), 1e-9)), 1),
                                cov_mean=round(float(np.mean([p["cov"] for p in plc])), 3),
                                placements=plc)
        rows.append((mesh, out_meshes[mesh]))

    lum_all = A @ LUM
    # ---- sanity check 2: a placement beside a near tree vs that tree's own COLOR_0
    eset = json.loads(pick("export/out/gate1/export_set.json").read_text())
    npz = np.load(str(pick("export/out/gate3/vertex_irradiance.npz")))
    trees = {n: np.array(a["location_blender"], dtype=float) for n, a in eset["assets"].items()
             if (a.get("kind") == "tree_near" or n.startswith("ENV_tree_")) and a.get("mesh") in set(npz.files)}
    P = {o: np.array(got[o]["loc"], dtype=float) for o, _ in order}
    best = None
    for tn, tp in trees.items():
        for o, p in P.items():
            d = float(np.linalg.norm(p[:2] - tp[:2]))
            if best is None or d < best[0]:
                best = (d, tn, o)
    check2 = None
    if best:
        d, tn, o = best
        v = npz[eset["assets"][tn]["mesh"]]
        nz = v.sum(axis=1) > 0
        tree_mnz = v[nz].mean(axis=0) if nz.any() else np.zeros(3)
        shrub = np.array(got[o]["mean_nonzero"], dtype=float)
        check2 = dict(tree=tn, tree_mesh=eset["assets"][tn]["mesh"],
                      tree_color0_mean_nonzero=r6(tree_mnz),
                      tree_color0_coverage=round(float(nz.mean()), 4),
                      shrub=o, shrub_rgb=r6(shrub), distance_m=round(d, 2),
                      lum_ratio_shrub_over_tree=round(float((shrub @ LUM) / max(tree_mnz @ LUM, 1e-9)), 3))

    doc = dict(
        schema="pfa-phase6/gate4-instance-irradiance/1",
        generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
        encoding="linear-float32",
        units=("scene-linear irradiance / pi - the same units as a DECODED lightmap texel and as "
               "vertex_irradiance.npz; multiply by lightmaps.scale (pi) for irradiance"),
        placements=len(order), meshes_n=len(out_meshes),
        range_global=round(float(A.max()), 6),
        lum_min=round(float(lum_all.min()), 6), lum_max=round(float(lum_all.max()), 6),
        lum_mean=round(float(lum_all.mean()), 6),
        placement_order=plan["placement_order"],
        placement_key=("OBJECT NAME. The array order is export_set.json assets order filtered to the mesh, "
                       "which is the order the Gate 1 set lists the placements; it is a convenience, never "
                       "the contract - gltfpack -mi re-orders and merges instances across meshes, so the "
                       "consumer must match EXT_mesh_gpu_instancing rows to these entries by object name "
                       "(README 'Gate 3 export hand-off' item 20)."),
        reduce=("mean over the vertices that received light (cov), not over all vertices: see the module "
                "docstring and out/gate3/bake/inst_probe.json"),
        bake=dict(engine="CYCLES", type="DIFFUSE", direct=True, indirect=True, color=False,
                  samples=recs[plan["jobs"][0]]["samples"], denoiser="OPENIMAGEDENOISE",
                  target="VERTEX_COLORS", blend="gate3_bake.blend",
                  rig="light_presets.apply_final_cycles (same rig as every Gate 3 bake)",
                  single_user="mesh data copied per placement in the bake process only; nothing saved",
                  material_override=("opaque grey Principled (base 0.5, roughness 1) with the card's shadow "
                                     "ray visibility off, because the cut-out material returns 0 at a "
                                     "transparent vertex; `color: false` divides the albedo out"),
                  variant=variant, jobs=recs,
                  bake_s=round(sum(r["bake_s"] for r in recs.values()), 1)),
        checks=dict(
            count=dict(baked=len(got), env_cards=cards["summary"]["placements"],
                       meshes=len(out_meshes), env_cards_meshes=cards["summary"]["meshes"],
                       ok=len(got) == cards["summary"]["placements"] == len(order)),
            near_tree=check2),
        meshes=out_meshes)
    OUT_JSON.write_text(json.dumps(doc, indent=1))
    kb = OUT_JSON.stat().st_size / 1024.0

    rows.sort(key=lambda r: r[1]["lum_mean"])
    print(f"{'mesh':32s} {'n':>4s} {'lum_min':>8s} {'lum_mean':>8s} {'lum_max':>8s} {'ratio':>7s} {'cov':>5s}")
    for mesh, m in rows:
        print(f"{mesh:32s} {m['n']:4d} {m['lum_min']:8.4f} {m['lum_mean']:8.4f} {m['lum_max']:8.4f} "
              f"{m['lum_ratio']:7.1f} {m['cov_mean']:5.2f}")
    print(f"\nglobal: {len(order)} placements, range {doc['range_global']:.4f}, "
          f"lum {doc['lum_min']:.4f} .. {doc['lum_max']:.4f} (mean {doc['lum_mean']:.4f})")
    print(f"check 2 near tree: {json.dumps(check2)}")
    print(f"check 3 count: {json.dumps(doc['checks']['count'])}")
    print(f"wrote {OUT_JSON} ({kb:.1f} kB)")


main()
