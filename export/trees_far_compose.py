"""Phase 6c item 2: merge the far-tree bake records into the two hand-off files.

    python3 export/trees_far_compose.py

CPU only, no Blender, no GPU. Writes, under export/out/gate3/trees_far/:

  vertex_ao.npz              one float32 [verts, 3] per LOD2 MESH NAME - the same contract as
                             out/gate3/vertex_irradiance.npz, so `trees_far.py` attaches it as COLOR_0 by
                             re-running. 0-1, 1 = unoccluded: the bake is a Cycles DIFFUSE bake (colour off)
                             with every light hidden under a uniform white world of radiance 1, where an
                             unoccluded lambert returns exactly irradiance/pi = 1. That is not assumed - each
                             AO job bakes a 2 m calibration plane 1 km from the tree with nothing above it and
                             records its value; `vertex_ao.calibration` carries them and this script asserts
                             every one is 1.000 +/- 0.002.

  instance_irradiance.json   schema pfa-phase6/gate4-instance-irradiance/**2** (review r1 finding 10c: /1 is
                             the shrub file, /2 adds the `prototypes` block, so manifest_v4.py can tell them
                             apart). One scene-linear RGB per far-tree PLACEMENT in the same units as the
                             shrub file and as a decoded lightmap texel (irradiance / pi), keyed by WORLD
                             TRANSLATION, plus `prototypes[<p>].E_bake`, the same measurement of the body
                             that produced the impostor atlas in the nursery it was baked in.

BOTH SIDES OF THE RATIO USE THE SAME REDUCER (review r1 finding 4). `rgb` and `E_bake` are both
`mean_nonzero`: the mean over the vertices that received light under the shadow-ray cut-out override, exactly
as gate3_instance_compose.py:84 ships E_placement for the shrubs. A plain vertex mean in the divisor would
bias every ratio by 1/cov, so `cov` ships beside both.

THE RATIO TAKES BOTH VALUES RAW (review r1 finding 7). `E_placement / E_bake` is stored-value over
stored-value. `lightmaps.scale` (pi) is applied to NEITHER: feeding the scaled `_IRRADIANCE` attribute into
the numerator against the unscaled `E_bake` would make every impostor pi x too bright.
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
TF = OUT / "trees_far"
REC = OUT / "bake"
LUM = np.array([0.2126, 0.7152, 0.0722], dtype=np.float64)
CAL_TOL = 0.002


def pick(rel):
    for base in (ROOT, MAIN):
        p = base / rel
        if p.exists():
            return p
    raise FileNotFoundError(rel)


def r6(v):
    return [round(float(x), 6) for x in v]


def main():
    topo = json.loads((TF / "topology.json").read_text())
    plan = json.loads((TF / "trees_far_jobs.json").read_text())
    places = json.loads((TF / "placements.json").read_text())
    man = json.loads(pick("export/out/gate3/manifest.json").read_text())
    protos = sorted(topo["prototypes"])
    mesh_of = {p: topo["prototypes"][p]["mesh"] for p in protos}
    loc_of = {d["object"]: d["loc"] for d in places["placements"]}
    proto_of = {d["object"]: d["prototype"] for d in places["placements"]}
    doc = dict(schema="pfa-phase6/gate4-instance-irradiance/2",
               generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
               generator="export/trees_far_compose.py",
               encoding="linear-float32", dtype="float32", encode="none")

    # ------------------------------------------------------------------ 1. vertex AO
    arrays, ao_meshes, cals = {}, {}, {}
    for p in protos:
        rec = json.loads((REC / f"tfao_{p}.json").read_text())
        assert len(rec["items"]) == 1, f"tfao_{p}: {len(rec['items'])} items"
        it = rec["items"][0]
        z = np.load(str(OUT / rec["npz"]))
        a = np.asarray(z[mesh_of[p]], dtype=np.float32)
        want = topo["prototypes"][p]["verts"]
        assert a.shape == (want, 3), \
            f"{p}: vertex_ao is {a.shape}, the export's LOD2 topology has {want} verts - hard failure"
        assert float(a.min()) >= 0.0 and float(a.max()) <= 1.0 + 1e-4, \
            f"{p}: AO out of [0, 1]: {a.min()} .. {a.max()}"
        cal = rec["cal"]
        cm = float(np.mean(cal["mean"]))
        assert abs(cm - 1.0) <= CAL_TOL, \
            f"{p}: the unoccluded calibration plane baked {cm:.5f}, not 1.0 - the AO is not normalised"
        cals[p] = round(cm, 5)
        arrays[mesh_of[p]] = a
        g = a.mean(axis=1)
        ao_meshes[mesh_of[p]] = dict(
            prototype=p, verts=int(a.shape[0]),
            min=round(float(g.min()), 6), mean=round(float(g.mean()), 6), max=round(float(g.max()), 6),
            p05=round(float(np.percentile(g, 5)), 6), p50=round(float(np.percentile(g, 50)), 6),
            p95=round(float(np.percentile(g, 95)), 6),
            zeros=it["zeros"], zeros_pct=round(100.0 * it["zeros"] / a.shape[0], 2),
            loose_verts=it["loose_verts"], zeros_loose=it["zeros_loose"],
            calibration=cals[p], bake_s=it["bake_s"], job=f"tfao_{p}")
    npz = TF / "vertex_ao.npz"
    np.savez_compressed(str(npz), **arrays)
    back = np.load(str(npz))
    assert sorted(back.files) == sorted(arrays), f"{npz}: mesh set changed on write"
    for k, v in arrays.items():
        assert np.array_equal(np.asarray(back[k]), v), f"{npz}: {k} changed on write"

    # ------------------------------------------------------------------ 2. E_bake, per prototype
    proto_out, missing_eb = {}, []
    for p in protos:
        f = REC / f"tfeb_{p}.json"
        if not f.exists():
            missing_eb.append(p)
            continue
        rec = json.loads(f.read_text())
        it = rec["items"][0]
        assert it["object"] == p, f"tfeb_{p} baked {it['object']}"
        proto_out[p] = dict(E_bake=r6(it["mean_nonzero"]), cov=round(it["coverage"], 4),
                            E_bake_mean_all=r6(it["mean"]), max=r6(it["max"]),
                            object=it["object"], mesh=it["mesh"], verts=it["verts"],
                            lod2_mesh=mesh_of[p], lod2_verts=topo["prototypes"][p]["verts"],
                            samples=rec["samples"], bake_s=it["bake_s"], job=f"tfeb_{p}",
                            zero_channel=bool(min(it["mean_nonzero"]) <= 0.0))

    # ------------------------------------------------------------------ 3. E_placement, per placement
    got = {}
    for jid in [j["id"] for j in plan["jobs"] if j["kind"] == "instance"]:
        rec = json.loads((REC / f"{jid}.json").read_text())
        assert not rec["missing"], f"{jid}: missing objects {rec['missing']}"
        res = rec["results"]["shadow"]
        for it in res["items"]:
            assert it["object"] not in got, f"duplicate placement {it['object']}"
            got[it["object"]] = it
    order = [d["object"] for d in places["placements"]]
    absent = [o for o in order if o not in got]
    assert not absent, f"{len(absent)} placements never baked, first: {absent[:5]}"
    assert len(got) == len(order) == 127, f"{len(got)} baked, {len(order)} planned"

    meshes, all_rgb = {}, []
    for obj in order:
        it = got[obj]
        p = proto_of[obj]
        mesh = mesh_of[p]
        assert it["mesh"] == mesh, f"{obj}: baked mesh {it['mesh']} != {mesh}"
        rgb = np.array(it["mean_nonzero"], dtype=np.float64)
        all_rgb.append(rgb)
        meshes.setdefault(mesh, []).append(dict(
            object=obj, loc=[round(float(x), 4) for x in loc_of[obj]], rgb=r6(rgb),
            mean_all=r6(it["mean"]), cov=round(it["coverage"], 3)))
    A = np.array(all_rgb)
    lum_all = A @ LUM

    out_meshes = {}
    for mesh, plc in meshes.items():
        M = np.array([q["rgb"] for q in plc], dtype=np.float64)
        lum = M @ LUM
        out_meshes[mesh] = dict(n=len(plc), min=r6(M.min(axis=0)), max=r6(M.max(axis=0)),
                                mean=r6(M.mean(axis=0)),
                                lum_min=round(float(lum.min()), 6), lum_max=round(float(lum.max()), 6),
                                lum_mean=round(float(lum.mean()), 6),
                                lum_ratio=(round(float(lum.max() / lum.min()), 1) if lum.min() > 0 else None),
                                cov_mean=round(float(np.mean([q["cov"] for q in plc])), 3),
                                placements=plc)

    # the join the viewer / the export has to make, measured rather than assumed
    L = np.array([loc_of[o] for o in order], dtype=float)
    d2 = ((L[:, None, :] - L[None, :, :]) ** 2).sum(axis=2)
    np.fill_diagonal(d2, np.inf)
    nn = np.sqrt(d2.min(axis=1))
    tol = 0.02
    same_min, pairs = np.inf, []
    for mesh, plc in meshes.items():
        ix = [k for k, o in enumerate(order) if mesh_of[proto_of[o]] == mesh]
        if len(ix) < 2:
            continue
        sub = d2[np.ix_(ix, ix)]
        same_min = min(same_min, float(np.sqrt(sub.min())))
        for a_, b_ in np.argwhere(sub < (2 * tol) ** 2):
            if a_ < b_:
                pairs.append(dict(mesh=mesh, a=order[ix[a_]], b=order[ix[b_]],
                                  gap_m=round(float(np.sqrt(sub[a_, b_])), 4)))
    dark = [dict(object=o, mesh=mesh_of[proto_of[o]], loc=loc_of[o], verts=got[o]["verts"])
            for o in order if max(got[o]["mean_nonzero"]) <= 0.0]

    doc.update(
        placements=len(order), meshes_n=len(out_meshes), prototypes_n=len(protos),
        units=("scene-linear irradiance / pi - the same units as a DECODED lightmap texel, as "
               "vertex_irradiance.npz and as the shrub instance_irradiance.json; multiply by "
               "lightmaps.scale (pi) for irradiance"),
        attribute="_IRRADIANCE", key="WORLD TRANSLATION",
        range_global=round(float(A.max()), 6),
        lum_min=round(float(lum_all.min()), 6), lum_max=round(float(lum_all.max()), 6),
        lum_mean=round(float(lum_all.mean()), 6),
        zero_placements=len(dark), zero_placement_rows=dark,
        placement_order="topology.json placements order (tree_far index), filtered per mesh",
        placement_key=("WORLD TRANSLATION (`loc`) = the manifest's `tree_far[i].trunk_base`, which is the "
                       "glTF instance translation after the (x, z, -y) swap. The object name is a label: "
                       "gltfpack -mi drops node names."),
        join=dict(space="Blender world metres (x, y, z). glTF is Y-up: gltf_translation = (x, z, -y).",
                  how=("nearest-translation match PER MESH, bijective, residual below `tolerance_m`"),
                  tolerance_m=tol,
                  min_separation_within_mesh_m=round(float(same_min), 4),
                  min_separation_any_mesh_m=round(float(nn.min()), 4),
                  median_separation_m=round(float(np.median(nn)), 4),
                  same_mesh_pairs_closer_than_2x_tolerance=pairs),
        reduce=("`rgb` = mean over the vertices that received light (`cov`); `mean_all` = the same mean over "
                "ALL vertices. Use `rgb`: it is the reducer the shrub file ships and the reducer `E_bake` "
                "uses, so E_placement / E_bake is unit-free."),
        ratio=dict(use=("IMPOSTOR ONLY. Beyond `treeMeshDist` the viewer draws "
                        "atlas_frame * (E_placement / E_bake) per placement, per channel."),
                   raw=("BOTH VALUES RAW: the numerator is this file's `rgb` (or the unscaled `_IRRADIANCE` "
                        "attribute), the denominator this file's `prototypes[p].E_bake`. `lightmaps.scale` "
                        "(pi) is applied to NEITHER - scaling only the numerator makes every impostor pi x "
                        "too bright (review r1 finding 7)."),
                   fallback="clamp the ratio to the lead's ceiling; use 1.0 where E_bake has a zero channel",
                   e_bake_body=("the `_LOD1` prototype object in gate3_imp.blend that job imp_<proto> "
                                "rendered into the atlas - NOT the export's LOD2 reduction (review r1 "
                                "finding 5). What does not cancel between the two bodies is crown density, "
                                "reported as `cov` on both sides.")),
        prototypes=proto_out, prototypes_missing=missing_eb,
        vertex_ao=dict(npz="trees_far/vertex_ao.npz", dtype="float32", encode="none",
                       units="0-1 ambient occlusion (1 = unoccluded)",
                       bake=("Cycles DIFFUSE direct+indirect, colour off, every light hidden, uniform white "
                             "world of radiance 1, the shadow-ray cut-out override, 64 spp, VERTEX_COLORS, "
                             "each prototype ISOLATED (all 16 sit at the world origin in "
                             "trees_far_lod2.blend, so every other mesh is hidden from render)"),
                       normalisation=("asserted, not assumed: a 2 m calibration plane 1 km from the tree "
                                      "bakes 1.000 in every job (`calibration` per mesh), which is what "
                                      "makes the raw bake value the AO factor"),
                       topology="asserted equal to topology.json's LOD2 vertex count per prototype",
                       zeros=("vertices whose hemisphere is fully blocked by the crown. They are real "
                              "(`loose_verts` = 0 everywhere, so none of them is an unbaked vertex) and "
                              "they sit inside the crown; `zeros_pct` per mesh says how many."),
                       meshes=ao_meshes),
        bake=dict(engine="CYCLES", type="DIFFUSE", direct=True, indirect=True, color=False,
                  target="VERTEX_COLORS", denoiser="OPENIMAGEDENOISE",
                  samples=dict(vertex_ao=plan["samples"]["ao"], irradiance=plan["samples"]["irradiance"]),
                  blends=dict(vertex_ao="trees_far/trees_far_lod2.blend",
                              E_placement="trees_far/trees_far_irr.blend",
                              E_bake="gate3_imp.blend"),
                  E_placement_scene=("gate3_bake.blend with the 127 LOD2 placements linked in, the 127 "
                                     "`source_tree` objects and the 127 `ENV_treeboard_*` billboards hidden "
                                     "from render - the scene as it ships once the far trees are meshes"),
                  placement_transform=("Translation(trunk_base) @ Scale(s) @ Translation(-anchor_p): the "
                                       "export bakes the prototype's own world matrix into the mesh and "
                                       "never subtracts it again, so the anchor has to come off here "
                                       "(export/trees_far_set.py, and a defect reported for env_trees.glb)"),
                  rig="light_presets.apply_final_cycles (the rig every Gate 3 bake and the atlas used)",
                  material_override=("Light Path > Is Shadow Ray: the baked surface is an opaque grey "
                                     "Principled (base 0.5, roughness 1) while shadow rays keep the "
                                     "original cut-out chain, so a leaf still casts its leaf-shaped shadow. "
                                     "Applied to the MATERIAL over the whole scope, so no value depends on "
                                     "the job split. Not a neutral re-encoding - the same wrap the shrub "
                                     "file documents."),
                  jobs=[j["id"] for j in plan["jobs"]]),
        meshes=out_meshes)
    (TF / "instance_irradiance.json").write_text(json.dumps(doc, indent=1) + "\n")

    print(f"[trees_far_compose] vertex_ao.npz {npz.stat().st_size} B, {len(arrays)} meshes; "
          f"AO mean {min(v['mean'] for v in ao_meshes.values()):.4f}-"
          f"{max(v['mean'] for v in ao_meshes.values()):.4f}")
    print(f"[trees_far_compose] instance_irradiance.json {len(order)} placements, "
          f"lum {doc['lum_min']:.4f}-{doc['lum_max']:.4f}, {len(dark)} zero placements, "
          f"{len(proto_out)}/{len(protos)} E_bake values")
    if missing_eb:
        print(f"[trees_far_compose] E_bake still missing for {len(missing_eb)}: {missing_eb[:4]}")


main()
