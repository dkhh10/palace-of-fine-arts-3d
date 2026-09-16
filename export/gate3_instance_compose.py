"""Gate 4: merge the `inst_irr_*` bake records into out/gate3/instance_irradiance.json.

    python3 export/gate3_instance_compose.py

CPU only, no Blender, no GPU. One scene-linear RGB per PLACEMENT of the 28 shrub/reed card meshes, in the
same units as a DECODED lightmap texel and as vertex_irradiance.npz (irradiance / pi; x lightmaps.scale).

THE OVERRIDE, and why it is not a neutral re-encoding. A leaf card's material is alpha cut-out: where a
vertex falls in a transparent texel the DIFFUSE bake returns exactly 0. Measured on inst_probe/inst_probe2
(12 placements): only 10.7 % of vertices come back non-zero with the card's own material and 1 placement of
12 is entirely black, so the plain vertex mean of a 36-tri card is noise. The bake therefore wraps each card
MATERIAL so that non-shadow rays see an opaque grey Principled while shadow rays keep the original cut-out
chain (`visible_shadow` stays ON, so every shadow the leaf casts is real), which lifts coverage to 0.79-0.95.
Because materials are shared datablocks the wrap covers all 1 379 placements in every job, so no value
depends on the job split (measured: one placement baked in two different splits is bit-identical).
This CHANGES the measured number, it does not preserve it: `color: false` divides the albedo out, but the
surface that receives the light is a full grey lambert instead of a partly transparent leaf. Matched
per-vertex against the cut-out bake the shadow-ray wrap is a median 1.61x brighter (0.12-3.39 over 11
placements with any matched vertex), and the superseded `visible_shadow = False` variant was a further
median 1.14x brighter than this one (up to 2.01x on sunlit cards).

THE REDUCTION is the mean over the vertices that received light. The remaining zeros are the card vertices
buried in the terrain (their hemisphere really is blocked); averaging them in would darken a placement by
its own buried fraction, which is geometry, not light. `cov` ships beside `rgb` with `mean_all` (the
all-vertex mean) for a consumer that wants the occluded form.

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
    for jid in list(plan["jobs"]):
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
        meshes.setdefault(mesh, []).append(dict(
            object=obj, loc=[round(float(x), 4) for x in it["loc"]], rgb=r6(rgb),
            mean_all=r6(it["mean"]), cov=round(it["coverage"], 3)))
    A = np.array(all_rgb)

    out_meshes, rows = {}, []
    for mesh, plc in meshes.items():
        M = np.array([p["rgb"] for p in plc], dtype=np.float64)
        lum = M @ LUM
        out_meshes[mesh] = dict(n=len(plc),
                                min=r6(M.min(axis=0)), max=r6(M.max(axis=0)), mean=r6(M.mean(axis=0)),
                                lum_min=round(float(lum.min()), 6), lum_max=round(float(lum.max()), 6),
                                lum_mean=round(float(lum.mean()), 6),
                                lum_ratio=(round(float(lum.max() / lum.min()), 1)
                                           if lum.min() > 0 else None),
                                cov_mean=round(float(np.mean([p["cov"] for p in plc])), 3),
                                placements=plc)
        rows.append((mesh, out_meshes[mesh]))

    lum_all = A @ LUM
    L = np.array([got[o]["loc"] for o, _ in order], dtype=float)
    d2 = ((L[:, None, :] - L[None, :, :]) ** 2).sum(axis=2)
    np.fill_diagonal(d2, np.inf)
    nn = np.sqrt(d2.min(axis=1))
    tol = 0.02
    # The join is per MESH (a glTF mesh's instancing rows can only be that mesh's placements), so what
    # matters is the closest pair WITHIN a mesh, not across the site.
    same_min, pairs = np.inf, []
    for mi, plc in meshes.items():
        ix = [k for k, (_, mm) in enumerate(order) if mm == mi]
        if len(ix) < 2:
            continue
        sub = d2[np.ix_(ix, ix)]
        same_min = min(same_min, float(np.sqrt(sub.min())))
        for a, b in np.argwhere(sub < (2 * tol) ** 2):
            if a < b:
                ra, rb = np.array(all_rgb[ix[a]]), np.array(all_rgb[ix[b]])
                pairs.append(dict(mesh=mi, a=order[ix[a]][0], b=order[ix[b]][0],
                                  gap_m=round(float(np.sqrt(sub[a, b])), 4),
                                  max_abs_rgb_delta=round(float(np.abs(ra - rb).max()), 4)))
    join = dict(
        space="Blender world metres (x, y, z). glTF is Y-up: gltf_translation = (x, z, -y).",
        how=("nearest-translation match, PER MESH: for each EXT_mesh_gpu_instancing row of a mesh (after that "
             "swap) take that mesh's entry whose `loc` is nearest, assert the residual is below "
             "`tolerance_m` and that the assignment is a bijection (every entry used exactly once). "
             "`object` is a label, not a key: gltfpack -mi drops node names and manifest "
             "instancing.<mesh>.objects[] is truncated at 16 entries."),
        tolerance_m=tol,
        min_separation_within_mesh_m=round(float(same_min), 4),
        min_separation_any_mesh_m=round(float(nn.min()), 4),
        median_separation_m=round(float(np.median(nn)), 4),
        same_mesh_pairs_closer_than_2x_tolerance=pairs,
        note=("the closest two placements of the SAME mesh are %.3f m apart and %d same-mesh pair(s) sit "
              "within 2 x tolerance, so a nearest match inside a mesh is unambiguous at 0.02 m. (Three pairs "
              "of DIFFERENT meshes sit 9-29 mm apart; they cannot be confused because the join is per mesh.) "
              "gltfpack quantises instance translations, so an exact match must never be required; if a "
              "residual exceeds the tolerance the export must fail, not guess."
              % (float(same_min), len(pairs))))
    dark = [dict(object=obj, mesh=mesh, loc=got[obj]["loc"], verts=got[obj]["verts"])
            for obj, mesh in order if max(got[obj]["mean_nonzero"]) <= 0.0]
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
        # review finding 6: the bare ratio has no control. Add one - the median of every placement within
        # 20 m of that tree - and state the tree's own coverage, since a low coverage makes the tree's mean
        # a mean over a biased 23 % of its vertices rather than over its canopy.
        tp = trees[tn]
        near = [np.array(got[x]["mean_nonzero"], dtype=float) @ LUM
                for x, _ in order if np.linalg.norm(np.array(got[x]["loc"])[:2] - tp[:2]) <= 20.0]
        check2 = dict(tree=tn, tree_mesh=eset["assets"][tn]["mesh"],
                      tree_color0_mean_nonzero=r6(tree_mnz),
                      tree_color0_coverage=round(float(nz.mean()), 4),
                      shrub=o, shrub_rgb=r6(shrub), distance_m=round(d, 2),
                      lum_ratio_shrub_over_tree=round(float((shrub @ LUM) / max(tree_mnz @ LUM, 1e-9)), 3),
                      control=dict(n_within_20m=len(near),
                                   median_lum_within_20m=round(float(np.median(near)), 4) if near else None,
                                   site_median_lum=round(float(np.median(A @ LUM)), 4)))

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
        placement_key=("WORLD TRANSLATION (`loc`). The object name is a label: gltfpack -mi drops node "
                       "names and the manifest's instancing.<mesh>.objects[] is truncated at 16 entries, so "
                       "no name survives where the consumer can read it. The array order is export_set.json "
                       "assets order filtered to the mesh; it is a convenience, never the contract, because "
                       "gltfpack -mi re-orders and merges instances (README hand-off item 20)."),
        join=join,
        reduce=("`rgb` = mean over the vertices that received light (`cov`); `mean_all` = the same mean over "
                "ALL vertices, which is `rgb` scaled down by the fraction of the card buried in the terrain. "
                "Use `rgb`. The 7 placements with cov == 0 are fully enclosed and ship [0,0,0]: the viewer "
                "falls back to the probe irradiance for cov == 0 (lead, 2026-09-17)."),
        bake=dict(engine="CYCLES", type="DIFFUSE", direct=True, indirect=True, color=False,
                  samples=recs[list(plan["jobs"])[0]]["samples"], denoiser="OPENIMAGEDENOISE",
                  target="VERTEX_COLORS", blend="gate3_bake.blend",
                  rig="light_presets.apply_final_cycles (same rig as every Gate 3 bake)",
                  single_user="mesh data copied per placement in the bake process only; nothing saved",
                  material_override=("Light Path > Is Shadow Ray mixes the card's ORIGINAL cut-out chain for "
                                     "shadow rays with an opaque grey Principled (base 0.5, roughness 1) for "
                                     "every other ray; visible_shadow stays ON. Applied to the material, so "
                                     "all 1 379 placements are wrapped in every job. This is NOT a neutral "
                                     "re-encoding: matched per-vertex it is a median 1.61x brighter than the "
                                     "cut-out bake - see the module docstring"),
                  variant=variant, jobs=recs,
                  bake_s=round(sum(r["bake_s"] for r in recs.values()), 1)),
        checks=dict(
            count=dict(baked=len(got), env_cards=cards["summary"]["placements"],
                       meshes=len(out_meshes), env_cards_meshes=cards["summary"]["meshes"],
                       ok=len(got) == cards["summary"]["placements"] == len(order)),
            near_tree=check2,
            dark=dict(note=("placements whose every vertex came back exactly 0: the card is fully enclosed "
                            "(no ray escapes). Left as measured - nothing is invented here - but listed so "
                            "the consumer can floor them if one turns out to be on camera."),
                      n=len(dark), placements=dark)),
        meshes=out_meshes)
    OUT_JSON.write_text(json.dumps(doc, indent=1))
    kb = OUT_JSON.stat().st_size / 1024.0

    rows.sort(key=lambda r: r[1]["lum_mean"])
    print(f"{'mesh':32s} {'n':>4s} {'lum_min':>8s} {'lum_mean':>8s} {'lum_max':>8s} {'ratio':>7s} {'cov':>5s}")
    for mesh, m in rows:
        print(f"{mesh:32s} {m['n']:4d} {m['lum_min']:8.4f} {m['lum_mean']:8.4f} {m['lum_max']:8.4f} "
              f"{(m['lum_ratio'] if m['lum_ratio'] is not None else float('inf')):7.1f} "
              f"{m['cov_mean']:5.2f}")
    print(f"\nglobal: {len(order)} placements, range {doc['range_global']:.4f}, "
          f"lum {doc['lum_min']:.4f} .. {doc['lum_max']:.4f} (mean {doc['lum_mean']:.4f})")
    print(f"dark (coverage 0): {len(dark)} -> {[d['object'] for d in dark]}")
    print(f"check 2 near tree: {json.dumps(check2)}")
    print(f"check 3 count: {json.dumps(doc['checks']['count'])}")
    print(f"wrote {OUT_JSON} ({kb:.1f} kB)")


main()
