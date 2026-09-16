"""Gate 4: recover env.glb's EXT_mesh_gpu_instancing row order for the 1 379 shrub/reed placements.

    node web/tools/instance_rows.mjs export/out/gate1/env.glb export/out/gate3/instance_rows.json
    python3 export/gate4_instance_order.py            # -> export/out/gate3/instance_order.json

CPU only, no Blender, no GPU. `export/out/gate3/instance_irradiance.json` (bake engineer) carries one
scene-linear RGB per PLACEMENT keyed by OBJECT NAME, because `gltfpack -mi` re-orders instances and merges
them across meshes: the array order in that file is the Gate 1 export-set order and is explicitly NOT the
contract. The viewer binds an `InstancedBufferAttribute` in the glb's own row order, so something has to map
row -> object name. Node names do not survive the pack (gltfpack 1.2 refuses -kn together with -mi), so the
only key left in the glb is the instance TRANSFORM.

THE MATCH. `export/out/gate1/env.gltf` is the pre-pack glTF the pack reads: 1 536 flat, named mesh nodes with
their own TRS, of which 1 379 are the card placements. `web/tools/instance_rows.mjs` decodes the packed glb
with three's meshopt decoder and dumps every instanced node's rows in accessor order. Each row is matched to
its nearest env.gltf node translation; the match is accepted only if it is a bijection, the residual is under
`TOL_M` and the runner-up is at least `MARGIN` times further away (measured: worst residual 5.7 mm on a card
node, worst margin 6.5x - gltfpack recentres a merged mesh, so the residual is the recentring offset, not
noise). Every object name is then required to exist in instance_irradiance.json and every one of its 1 379
placements is required to be hit exactly once. A single unknown or missing name fails the script.

WHAT IT FINDS (and why the manifest needs `nodes` as well as `meshes`): 25 of the 28 card meshes are one glb
node each, but gltfpack merged `EXPM_ENV_src_{maho2,pitto5,reed1}_LOD2.001` - a one-placement near-duplicate
of its base mesh - into the base mesh's node. Those three nodes therefore hold 46 / 102 / 76 rows against
their base mesh's 45 / 101 / 75 placements, and a viewer that bound the base mesh's array alone would be one
row short and misaligned from the merge point on. The rows of a mesh stay contiguous inside a node, so the
node is described exactly by an ordered `segments` list of (mesh, count).
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate3_common as g3  # noqa: E402

SCHEMA = "pfa-phase6/gate4-instance-order/1"
TOL_M = 0.05        # max accepted row -> source residual (measured worst on a card node: 0.0057 m)
MARGIN = 3.0        # nearest must be this many times closer than the runner-up


def pick(rel):
    """out/gate3 and out/gate1 live in this worktree; the bake branch's files arrive in MAIN via sync."""
    for base in (g3.ROOT, g3.MAIN_ROOT):
        p = base / rel
        if p.exists():
            return p
    raise FileNotFoundError(rel)


def main():
    src_gltf = pick("export/out/gate1/env.gltf")
    rows_p = pick("export/out/gate3/instance_rows.json")
    irr_p = pick("export/out/gate3/instance_irradiance.json")
    glb_p = pick("export/out/gate1/env.glb")
    rows = json.loads(rows_p.read_text())
    assert rows.get("schema") == "pfa-phase6/instance-rows/1", f"rows schema {rows.get('schema')!r}"
    if Path(rows["glb"]).name != glb_p.name or rows_p.stat().st_mtime < glb_p.stat().st_mtime - 1.0:
        raise SystemExit(f"{rows_p.name} is older than {glb_p.name}: re-run "
                         f"`node web/tools/instance_rows.mjs {glb_p} {rows_p}`")
    irr = json.loads(irr_p.read_text())
    assert irr.get("schema") == "pfa-phase6/gate4-instance-irradiance/1", f"irr schema {irr.get('schema')!r}"

    mesh_of_obj, n_of_mesh = {}, {}
    for mesh, m in irr["meshes"].items():
        n_of_mesh[mesh] = len(m["placements"])
        assert m["n"] == n_of_mesh[mesh], f"{mesh}: n={m['n']} but {n_of_mesh[mesh]} placements"
        for pl in m["placements"]:
            assert pl["object"] not in mesh_of_obj, f"duplicate placement object {pl['object']}"
            mesh_of_obj[pl["object"]] = mesh
    assert len(mesh_of_obj) == irr["placements"], f"{len(mesh_of_obj)} != {irr['placements']}"

    doc = json.loads(src_gltf.read_text())
    assert not any(n.get("children") for n in doc["nodes"]), \
        "env.gltf is no longer flat: the source world transform needs a parent walk"
    mn = [m.get("name") for m in doc["meshes"]]
    src = [(n.get("name"), mn[n["mesh"]], n.get("translation") or [0.0, 0.0, 0.0])
           for n in doc["nodes"] if "mesh" in n]
    P = np.array([s[2] for s in src], dtype=np.float64)

    used, nodes, per_mesh = {}, [], {}
    worst_resid, worst_margin = 0.0, 1e9
    for nd in rows["nodes"]:
        R = np.array([r[:3] for r in nd["rows"]], dtype=np.float64)
        d = np.linalg.norm(P[None, :, :] - R[:, None, :], axis=2)
        order = np.argsort(d, axis=1)
        best, second = order[:, 0], order[:, 1]
        names = [src[int(j)][0] for j in best]
        if not any(n in mesh_of_obj for n in names):
            continue                                   # not a card node (trees, backdrop): not our business
        seq = []
        for k, j in enumerate(best):
            name, mesh, _ = src[int(j)]
            r1, r2 = float(d[k, j]), float(d[k, second[k]])
            worst_resid = max(worst_resid, r1)
            worst_margin = min(worst_margin, r2 / max(r1, 1e-9))
            if r1 > TOL_M or r2 < MARGIN * max(r1, 1e-9):
                raise SystemExit(f"node {nd['order']} row {k}: ambiguous match to {name!r} "
                                 f"(residual {r1:.4f} m, runner-up {r2:.4f} m)")
            if name in used:
                raise SystemExit(f"node {nd['order']} row {k}: {name!r} already taken by {used[name]}")
            used[name] = (nd["order"], k)
            if name not in mesh_of_obj:
                raise SystemExit(f"node {nd['order']} row {k}: {name!r} is a card node row with no "
                                 f"irradiance entry in instance_irradiance.json")
            assert mesh_of_obj[name] == mesh, f"{name}: glTF mesh {mesh} != irradiance mesh {mesh_of_obj[name]}"
            seq.append((name, mesh))
            per_mesh.setdefault(mesh, []).append(name)
        segs = []
        for _, mesh in seq:
            if segs and segs[-1][0] == mesh:
                segs[-1][1] += 1
            else:
                segs.append([mesh, 1])
        assert sum(s[1] for s in segs) == nd["count"] == len(seq)
        nodes.append(dict(gltf_node=nd["gltf_node"], traverse_order=nd["order"], count=nd["count"],
                          tris=nd["tris"], material=nd["material"], segments=[[m, c] for m, c in segs]))

    missing = sorted(set(mesh_of_obj) - set(used))
    if missing:
        raise SystemExit(f"{len(missing)} placements have no glb instance row, first: {missing[:5]}")
    assert len(per_mesh) == irr["meshes_n"] == 28, f"{len(per_mesh)} meshes matched, want {irr['meshes_n']}"
    for mesh, names in per_mesh.items():
        assert len(names) == n_of_mesh[mesh], f"{mesh}: {len(names)} rows != {n_of_mesh[mesh]} placements"

    out = dict(schema=SCHEMA, generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
               generator="export/gate4_instance_order.py", glb="env.glb",
               glb_bytes=glb_p.stat().st_size, glb_mtime=int(glb_p.stat().st_mtime),
               source_gltf="../gate1/env.gltf", rows_file="instance_rows.json",
               irradiance="instance_irradiance.json",
               method=("each EXT_mesh_gpu_instancing row (decoded by web/tools/instance_rows.mjs) matched to "
                       "its nearest env.gltf node translation; bijective, residual < %.3f m, runner-up > %gx "
                       "further. Node names do not survive gltfpack -mi, the transform is the only key."
                       % (TOL_M, MARGIN)),
               placements=len(used), meshes_n=len(per_mesh),
               rows_matched=len(used), worst_residual_m=round(worst_resid, 6),
               worst_margin_ratio=round(worst_margin, 3),
               merged_nodes=[n for n in nodes if len(n["segments"]) > 1],
               nodes=nodes,
               meshes={m: dict(n=len(v), objects=v) for m, v in sorted(per_mesh.items())})
    op = g3.OUT / "instance_order.json"
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, indent=1))
    print(f"[instance_order] {len(used)} rows / {len(per_mesh)} meshes matched by name over {len(nodes)} "
          f"instanced nodes; worst residual {worst_resid*1000:.1f} mm, worst margin {worst_margin:.1f}x")
    for n in out["merged_nodes"]:
        print(f"  merged node {n['gltf_node']}: {n['count']} rows = " +
              " + ".join(f"{c}x{m.split('src_')[-1]}" for m, c in n["segments"]))
    print(f"  -> {op}")


if __name__ == "__main__":
    main()
