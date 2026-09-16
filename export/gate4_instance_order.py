"""Gate 4: recover env.glb's EXT_mesh_gpu_instancing row order for the 1 379 shrub/reed placements.

    node web/tools/instance_rows.mjs export/out/gate1/env.glb export/out/gate3/instance_rows.json
    python3 export/gate4_instance_order.py            # -> export/out/gate3/instance_order.json

CPU only, no Blender, no GPU.

WHY A JOIN IS NEEDED. `out/gate3/instance_irradiance.json` (bake engineer) carries one scene-linear RGB per
PLACEMENT of the 28 shrub/reed card meshes. `gltfpack -mi` collapses those placements into
`EXT_mesh_gpu_instancing` rows in its own order, drops every node name (gltfpack 1.2 refuses -kn together
with -mi) and merges near-duplicate meshes, so neither the array order nor a name survives into env.glb. The
viewer uploads an `InstancedBufferAttribute` in the glb's row order, so each row has to be tied back to its
placement - and, per the bake review (docs/reviews/phase6_bake_gate4_instance_review.md), **the only key that
survives the pack is the instance TRANSFORM**. The name is carried through as a label, never as the join.

THE JOIN. Each placement's world translation `loc` is Blender Z-up; the glTF exporter's axis swap is
Blender (x, y, z) -> glTF (x, z, -y), i.e. Blender +Y (toward the lagoon, CLAUDE.md) -> glTF -Z and Blender
+Z (up) -> glTF +Y. The swap is asserted here on the seven `checks.dark` placements, whose `loc` the bake
measured itself, against the pre-pack `out/gate1/env.gltf` node translations: measured residual 0.6 mm, which
is the JSON's own 3-decimal rounding. Then, per node:

1. a mesh is `contained` in an instanced node when EVERY one of its placements has a row of that node within
   `TOL_M`; a mesh must be contained in exactly one node, and a card node's row count must equal the sum of
   its contained meshes' placement counts (nothing unexplained, nothing missing);
2. rows are matched one-to-one to that node's placements by nearest translation, requiring residual < `TOL_M`
   and a runner-up at least `MARGIN` times further. Headroom: the worst residual measured is 5.7 mm
   (gltfpack recentres a merged mesh, so the residual is the recentring offset, not noise) against a smallest
   within-node placement separation of 88 mm.

Any unmatched row, any duplicate match, any mesh in two nodes and any row whose placement is unknown is a
hard failure - a silently swapped pair would light two shrubs with each other's irradiance.

WHAT IT FINDS (and why the manifest needs `nodes` as well as `meshes`): 25 of the 28 card meshes are one glb
node each, but gltfpack merged `EXPM_ENV_src_{maho2,pitto5,reed1}_LOD2.001` - a one-placement near-duplicate
of its base mesh - into the base mesh's node. Those three nodes hold 46 / 102 / 76 rows against their base
mesh's 45 / 101 / 75 placements, so a viewer binding the base mesh's array alone would be one row short and
misaligned from the merge point on. A mesh's rows stay contiguous inside a node, so the node is described
exactly by an ordered `segments` list of (mesh, count).

BEFORE THE RE-BAKE LANDS: `instance_irradiance.json` gains `loc` per placement with the re-baked values
(lead, session 4). While it is absent this script takes the positions from `out/gate1/env.gltf` by object
name as a TEST HARNESS, runs the identical join on them and says so in `loc_source`; the manifest writer
reports that string. The positions are the same either way - only the RGB values change in the re-bake.
"""
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate3_common as g3  # noqa: E402

SCHEMA = "pfa-phase6/gate4-instance-order/1"
TOL_M = 0.03        # max accepted row -> placement residual (worst measured 0.0057 m; nearest rival 0.088 m)
MARGIN = 3.0        # the nearest placement must be this many times closer than the runner-up
SWAP_TOL_M = 0.005  # axis-swap self-check against env.gltf (the JSON rounds loc to 3 decimals)


def pick(rel):
    """out/gate1 and out/gate3 live in this worktree; the bake branch's files arrive in MAIN via sync."""
    for base in (g3.ROOT, g3.MAIN_ROOT):
        p = base / rel
        if p.exists():
            return p
    raise FileNotFoundError(rel)


def to_gltf(loc):
    """Blender Z-up world translation -> glTF Y-up, the exporter's own swap: (x, y, z) -> (x, z, -y)."""
    x, y, z = loc
    return [float(x), float(z), -float(y)]


def source_translations():
    """{object name: glTF-space translation} from the pre-pack out/gate1/env.gltf (the axis-swap reference)."""
    doc = json.loads(pick("export/out/gate1/env.gltf").read_text())
    assert not any(n.get("children") for n in doc["nodes"]), \
        "env.gltf is no longer flat: a world translation now needs a parent walk"
    return {n["name"]: np.array(n.get("translation") or [0.0, 0.0, 0.0], dtype=np.float64)
            for n in doc["nodes"] if "mesh" in n and n.get("name")}


def main():
    rows_p = pick("export/out/gate3/instance_rows.json")
    # PFA_INSTANCE_IRR overrides the input for a dry run against a candidate JSON (e.g. the loc-carrying one
    # before it is synced); it never changes where the output goes.
    irr_p = Path(os.environ["PFA_INSTANCE_IRR"]) if os.environ.get("PFA_INSTANCE_IRR") \
        else pick("export/out/gate3/instance_irradiance.json")
    glb_p = pick("export/out/gate1/env.glb")
    rows = json.loads(rows_p.read_text())
    assert rows.get("schema") == "pfa-phase6/instance-rows/1", f"rows schema {rows.get('schema')!r}"
    if Path(rows["glb"]).name != glb_p.name or rows_p.stat().st_mtime < glb_p.stat().st_mtime - 1.0:
        raise SystemExit(f"{rows_p.name} is older than {glb_p.name}: re-run "
                         f"`node web/tools/instance_rows.mjs {glb_p} {rows_p}`")
    irr = json.loads(irr_p.read_text())
    assert irr.get("schema") == "pfa-phase6/gate4-instance-irradiance/1", f"irr schema {irr.get('schema')!r}"

    # ---- placements: object -> (mesh, glTF-space position). `loc` is the contract; env.gltf is the harness.
    src_tr = source_translations()
    have_loc = all("loc" in p for m in irr["meshes"].values() for p in m["placements"])
    loc_source = ("instance_irradiance.json placements[].loc (Blender Z-up -> glTF by (x, z, -y))"
                  if have_loc else
                  "TEST HARNESS: out/gate1/env.gltf node translations by object name - "
                  "instance_irradiance.json carries no per-placement `loc` yet (it lands with the re-bake); "
                  "the join itself is the same code either way")
    pos, mesh_of_obj = {}, {}
    for mesh, m in irr["meshes"].items():
        assert m["n"] == len(m["placements"]), f"{mesh}: n={m['n']} but {len(m['placements'])} placements"
        for pl in m["placements"]:
            o = pl["object"]
            assert o not in mesh_of_obj, f"duplicate placement object {o}"
            mesh_of_obj[o] = mesh
            if have_loc:
                pos[o] = np.array(to_gltf(pl["loc"]), dtype=np.float64)
            else:
                assert o in src_tr, f"{o}: not in env.gltf and instance_irradiance.json carries no loc"
                pos[o] = src_tr[o]
    assert len(mesh_of_obj) == irr["placements"], f"{len(mesh_of_obj)} != {irr['placements']} placements"

    # ---- the axis swap, asserted on the seven placements whose loc the bake measured itself
    swap_check = []
    for d in irr["checks"]["dark"]["placements"]:
        if d.get("loc") is None or d["object"] not in src_tr:
            continue
        r = float(np.linalg.norm(np.array(to_gltf(d["loc"])) - src_tr[d["object"]]))
        swap_check.append(r)
        assert r < SWAP_TOL_M, (f"axis swap wrong: {d['object']} loc {d['loc']} -> {to_gltf(d['loc'])} is "
                                f"{r:.4f} m from its env.gltf translation {list(src_tr[d['object']])}")
    assert swap_check, "no checks.dark placement carried a loc: the axis swap was never verified"

    objs = sorted(mesh_of_obj)
    P = np.array([pos[o] for o in objs])
    obj_i = {o: i for i, o in enumerate(objs)}

    # ---- step 1: which instanced node holds which mesh (containment, no names involved)
    node_rows, node_near = {}, {}
    for nd in rows["nodes"]:
        R = np.array([r[:3] for r in nd["rows"]], dtype=np.float64)
        d = np.linalg.norm(P[None, :, :] - R[:, None, :], axis=2)
        node_rows[nd["order"]] = (nd, R, d)
        node_near[nd["order"]] = d.min(axis=0)          # per placement: distance to this node's nearest row
    contained = {}
    for mesh, m in irr["meshes"].items():
        idx = [obj_i[p["object"]] for p in m["placements"]]
        hits = [o for o, near in node_near.items() if float(near[idx].max()) < TOL_M]
        if len(hits) != 1:
            raise SystemExit(f"{mesh}: contained in {len(hits)} instanced nodes {hits} at tol {TOL_M} m - "
                             f"the join cannot name the node that draws it")
        contained.setdefault(hits[0], []).append(mesh)

    used, nodes, per_mesh = {}, [], {}
    worst_resid, worst_margin = 0.0, 1e9
    for order_i, meshes in sorted(contained.items()):
        nd, R, d = node_rows[order_i]
        cand = [obj_i[p["object"]] for mesh in meshes for p in irr["meshes"][mesh]["placements"]]
        if len(cand) != nd["count"]:
            raise SystemExit(f"node {nd['gltf_node']}: {nd['count']} instance rows but {len(cand)} placements "
                             f"of its {len(meshes)} contained meshes {sorted(meshes)} - a row is unaccounted "
                             f"for (a merged mesh whose placements are not in instance_irradiance.json?)")
        sub = d[:, cand]
        o2 = np.argsort(sub, axis=1)
        seq = []
        for k in range(len(R)):
            j, j2 = int(o2[k, 0]), int(o2[k, 1]) if sub.shape[1] > 1 else None
            r1 = float(sub[k, j])
            r2 = float(sub[k, j2]) if j2 is not None else float("inf")
            name = objs[cand[j]]
            worst_resid = max(worst_resid, r1)
            worst_margin = min(worst_margin, r2 / max(r1, 1e-9))
            if r1 > TOL_M or r2 < MARGIN * max(r1, 1e-9):
                raise SystemExit(f"node {nd['gltf_node']} row {k}: ambiguous match to {name!r} "
                                 f"(residual {r1:.4f} m, runner-up {r2:.4f} m, tol {TOL_M} m)")
            if name in used:
                raise SystemExit(f"node {nd['gltf_node']} row {k}: {name!r} already matched by row "
                                 f"{used[name]} - the assignment is not one-to-one")
            used[name] = (nd["gltf_node"], k)
            seq.append((name, mesh_of_obj[name]))
            per_mesh.setdefault(mesh_of_obj[name], []).append(name)
        segs = []
        for _, mesh in seq:
            if segs and segs[-1][0] == mesh:
                segs[-1][1] += 1
            else:
                segs.append([mesh, 1])
        assert sum(s[1] for s in segs) == nd["count"] == len(seq)
        nodes.append(dict(gltf_node=nd["gltf_node"], traverse_order=nd["order"], count=nd["count"],
                          tris=nd["tris"], material=nd["material"], segments=[[m, c] for m, c in segs],
                          objects=[n for n, _ in seq]))

    missing = sorted(set(mesh_of_obj) - set(used))
    if missing:
        raise SystemExit(f"{len(missing)} placements have no glb instance row, first: {missing[:5]}")
    assert len(per_mesh) == irr["meshes_n"], f"{len(per_mesh)} meshes matched, want {irr['meshes_n']}"
    for mesh, names in per_mesh.items():
        assert len(names) == irr["meshes"][mesh]["n"], \
            f"{mesh}: {len(names)} glb rows != {irr['meshes'][mesh]['n']} placements"

    # ---- cross-check: the label. Every matched name must also be the nearest env.gltf node to that row.
    cross = {"checked": 0, "disagreements": 0, "worst_m": 0.0}
    if src_tr:
        names = list(src_tr)
        T = np.array([src_tr[n] for n in names])
        for n in nodes:
            R = node_rows[n["traverse_order"]][1]
            dd = np.linalg.norm(T[None, :, :] - R[:, None, :], axis=2)
            nearest = dd.argmin(axis=1)
            for k, name in enumerate(n["objects"]):
                cross["checked"] += 1
                cross["worst_m"] = max(cross["worst_m"], float(dd[k, nearest[k]]))
                if names[int(nearest[k])] != name:
                    cross["disagreements"] += 1
        cross["worst_m"] = round(cross["worst_m"], 6)
        cross["note"] = ("the object NAME is only a label: it is cross-checked against the nearest node of "
                         "the pre-pack env.gltf, never used to join" +
                         ("" if have_loc else " (and, while `loc` is absent, it IS that source - the "
                                              "cross-check is trivially true until the re-bake lands)"))
        assert cross["disagreements"] == 0, f"{cross['disagreements']} rows disagree with the env.gltf label"

    out = dict(schema=SCHEMA, generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
               generator="export/gate4_instance_order.py", glb="env.glb",
               glb_bytes=glb_p.stat().st_size, glb_mtime=int(glb_p.stat().st_mtime),
               source_gltf="../gate1/env.gltf", rows_file="instance_rows.json",
               irradiance="instance_irradiance.json",
               irradiance_generated=irr.get("generated"), loc_source=loc_source, loc_in_json=have_loc,
               axis_swap="Blender (x, y, z) -> glTF (x, z, -y): +Y toward the lagoon -> -Z, +Z up -> +Y",
               axis_swap_check=dict(n=len(swap_check), worst_m=round(max(swap_check), 6),
                                    against="out/gate1/env.gltf node translations",
                                    placements="instance_irradiance.json checks.dark (bake-measured loc)"),
               method=("per node: (1) a mesh is contained in the node when every one of its placements has a "
                       "row within %.3f m and the node's row count equals its contained meshes' placement "
                       "count; (2) rows matched one-to-one to those placements by nearest translation, "
                       "residual < %.3f m and runner-up > %gx. No name is used to join." % (TOL_M, TOL_M, MARGIN)),
               tol_m=TOL_M, margin=MARGIN,
               placements=len(used), meshes_n=len(per_mesh), rows_matched=len(used),
               worst_residual_m=round(worst_resid, 6), worst_margin_ratio=round(worst_margin, 3),
               name_crosscheck=cross,
               merged_nodes=[{k: v for k, v in n.items() if k != "objects"}
                             for n in nodes if len(n["segments"]) > 1],
               nodes=[{k: v for k, v in n.items() if k != "objects"} for n in nodes],
               meshes={m: dict(n=len(v), objects=v) for m, v in sorted(per_mesh.items())})
    op = g3.OUT / "instance_order.json"
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, indent=1))
    print(f"[instance_order] {len(used)} rows / {len(per_mesh)} meshes joined by TRANSLATION over "
          f"{len(nodes)} instanced nodes; worst residual {worst_resid*1000:.1f} mm, "
          f"worst margin {worst_margin:.1f}x, axis swap off by {max(swap_check)*1000:.1f} mm on "
          f"{len(swap_check)} bake-measured locs")
    print(f"  loc source: {loc_source}")
    for n in out["merged_nodes"]:
        print(f"  merged node {n['gltf_node']}: {n['count']} rows = " +
              " + ".join(f"{c}x{m.split('src_')[-1]}" for m, c in n["segments"]))
    print(f"  -> {op}")


if __name__ == "__main__":
    main()
