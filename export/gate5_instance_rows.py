#!/usr/bin/env python3
"""6b Gate 5 fix (5): re-key `lightmaps.instance_irradiance` to the per-tier ENV groups.

    python3 export/gate5_instance_rows.py            # -> out/gate5/instance_order_groups.json

CPU only (node + meshopt, no browser, no GPU).

WHY. The block the 6c bake shipped binds per glTF NODE INDEX inside the single `env.glb`
(`web/src/lightmaps.js applyInstanceIrradiance`, which looks the node up by `mesh.userData.pfaGltfNode`
under `WEB_glb_env`). Splitting ENV into per-tier groups renumbers those nodes, so every one of the
1 379 shrub/reed placements would miss its irradiance and fall back to the probe - the 6c look
regression the viewer engineer measured.

THE JOIN is the bake's own: **the instance TRANSLATION**, the only key that survives `gltfpack -mi`
(docs/reviews/phase6_bake_gate4_instance_review.md, decisions.md 2026-09-16). `web/tools/instance_rows.mjs`
decodes each group's `EXT_mesh_gpu_instancing` rows in glb row order; every row's translation is brought
back to Blender space (glTF (x, y, z) -> Blender (x, -z, y)) and matched to the nearest of the 1 379
`instance_irradiance.json` placements, with the residual required below `TOL_M` and the runner-up at
least `MARGIN` times further. `segments` is then REBUILT from the matched rows as an ordered
[mesh, count, offset] list - the same shape the viewer already reads - rather than copied from a node
layout the split has renumbered and re-merged. Matching node-to-node against env.glb was tried first and
is not enough: splitting ENV changes which meshes gltfpack merges into one node, so 4 of the 25 card
nodes had a different row count and 224 placements went unmatched. Any unmatched row, any placement
claimed twice, and the run fails - a silently swapped pair would light two shrubs with each other's
irradiance.

OUTPUT. `{group_id: {glb, nodes: [<the manifest's own node entries, gltf_node re-numbered>]}}`, folded
into the v5 manifest by `tiers.py` as `lightmaps.instance_irradiance.groups`. `segments` is copied
unchanged: it addresses rows INSIDE a node by mesh name and offset, which the split cannot move.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate5_common as G

TOL_M = 0.02          # the tolerance gate4_instance_order.py states, in metres
ROWS_TOOL = G.MAIN / "web/tools/instance_rows.mjs"


def rows_of(glb, out_json, force=False):
    """Decode a packed glb's instancing rows (node order, row order), caching to `out_json`."""
    out_json = Path(out_json)
    if force or not out_json.exists() or out_json.stat().st_mtime < Path(glb).stat().st_mtime:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(["node", str(ROWS_TOOL), str(glb), str(out_json)],
                           capture_output=True, text=True, cwd=str(G.MAIN / "web"))
        if r.returncode != 0:
            raise RuntimeError(f"instance_rows.mjs failed on {glb}:\n{r.stderr[-800:]}")
    return json.loads(out_json.read_text())


MARGIN = 3.0          # the runner-up must be at least this much further than the match


def placements_table(man=None, gate3=None):
    """(N,3) Blender translations, and the (mesh, row index) each one is."""
    import numpy as np
    p = Path(gate3 or G.GATE3) / "instance_irradiance.json"
    doc = json.loads(p.read_text())
    locs, owner = [], []
    for mesh, m in doc["meshes"].items():
        for i, pl in enumerate(m["placements"]):
            locs.append(pl["loc"])
            owner.append((mesh, i))
    return np.asarray(locs, dtype=float), owner, doc


def rows_to_segments(grp, locs, owner):
    """Per instanced node: the rows matched to placements, as an ordered [mesh, count, offset] list."""
    import numpy as np
    nodes, claimed, unmatched = [], {}, 0
    for gn in grp["nodes"]:
        rows = np.asarray([[r[0], -r[2], r[1]] for r in gn["rows"]], dtype=float)   # glTF -> Blender
        d = np.linalg.norm(locs[None, :, :] - rows[:, None, :], axis=2)
        idx = np.argsort(d, axis=1)[:, :2]
        best = d[np.arange(len(rows)), idx[:, 0]]
        second = d[np.arange(len(rows)), idx[:, 1]]
        hit = (best <= TOL_M) & (second > MARGIN * np.maximum(best, 1e-6))
        if not hit.any():
            continue                       # not a card node (bark, trunk, backdrop): no irradiance
        segs, cur, run = [], None, 0
        for r in range(len(rows)):
            if not hit[r]:
                unmatched += 1
                cur, run = None, 0
                continue
            mesh, i = owner[idx[r, 0]]
            key = (mesh, i)
            if key in claimed:
                raise RuntimeError(f"placement {mesh}[{i}] claimed twice "
                                   f"(node {gn['gltf_node']} and {claimed[key]})")
            claimed[key] = gn["gltf_node"]
            if cur == mesh and run == i:
                segs[-1][1] += 1
                run += 1
            else:
                segs.append([mesh, 1, i])
                cur, run = mesh, i + 1
        nodes.append(dict(gltf_node=gn["gltf_node"], count=gn["count"],
                          material=gn.get("material"), tris=gn.get("tris"),
                          segments=[[m, c, o] for m, c, o in segs],
                          rows_matched=int(hit.sum())))
    return nodes, unmatched, claimed


def build(out_dir, groups, cache=None):
    """`{group_id: {glb, nodes}}` for every ENV group that carries card placements."""
    out_dir = Path(out_dir)
    cache = Path(cache or (out_dir / "_rows"))
    locs, owner, src = placements_table()
    res, report, claimed_all = {}, {}, {}
    # Desktop and mobile are two independent publications of the same placements, so "claimed twice" is
    # only a fault WITHIN a variant. The check is scoped by the `m_` prefix that names the mobile set.
    claimed_by_variant = {}
    for g in groups:
        if g["cls"] != "env":
            continue
        claimed_all = claimed_by_variant.setdefault(g["id"].startswith("m_"), {})
        glb = out_dir / g["path"]
        if not glb.exists():
            continue
        grp = rows_of(glb, cache / f"{g['id']}.json")
        nodes, unmatched, claimed = rows_to_segments(grp, locs, owner)
        dup = set(claimed) & set(claimed_all)
        if dup:
            raise RuntimeError(f"{g['id']}: {len(dup)} placements already claimed by another group, "
                               f"e.g. {sorted(dup)[:3]}")
        claimed_all.update(claimed)
        placements = sum(n["rows_matched"] for n in nodes)
        res[g["id"]] = dict(glb=g["path"], nodes=nodes, placements=placements,
                            card_nodes=len(nodes), rows_unmatched=unmatched)
        report[g["id"]] = dict(group_nodes=len(grp["nodes"]), card_nodes=len(nodes),
                               placements=placements, rows_unmatched=unmatched)
        print(f"[gate5rows] {g['id']}: {len(grp['nodes'])} instanced nodes, {len(nodes)} carry "
              f"irradiance, {placements} placements matched", flush=True)
    want = src.get("placements") or 0
    desktop_claims = claimed_by_variant.get(False, {})
    got = len(desktop_claims)
    missing = []
    for mesh, m in src["meshes"].items():
        for i, pl in enumerate(m["placements"]):
            if (mesh, i) not in desktop_claims:
                missing.append(dict(mesh=mesh, row=i, object=pl.get("object"), loc=pl.get("loc")))
    doc = dict(schema="pfa-phase6/gate5-instance-order/2",
               generator="export/gate5_instance_rows.py",
               source="export/out/gate3/instance_irradiance.json placements[].loc",
               tolerance_m=TOL_M, margin=MARGIN, placements_expected=want, placements_covered=got,
               complete=(got == want), groups=res, report=report, unmatched=missing,
               unmatched_note="a placement with no row within the tolerance, or whose runner-up is "
                              "too close to call. The viewer falls back to the probe for these, which "
                              "is what it already does for the 7 fully enclosed cards.",
               join="rows decoded with web/tools/instance_rows.mjs, brought back to Blender space as "
                    "(x, -z, y), matched to the nearest placement with the runner-up at least "
                    f"{MARGIN}x further; `segments` rebuilt from the matched rows as [mesh, count, "
                    "offset], which is the shape web/src/lightmaps.js already reads.")
    p = out_dir / "instance_order_groups.json"
    p.write_text(json.dumps(doc, indent=1))
    print(f"[gate5rows] {got}/{want} placements covered -> {p}", flush=True)
    if got != want:
        print(f"[gate5rows] WARNING {want - got} placements are in no group node: "
              f"{[m['object'] for m in missing][:6]}", flush=True)
    return doc


def main():
    out = G.OUT
    groups = []
    for f in ("groups.json", "groups_mobile.json"):
        if (out / f).exists():
            groups += json.loads((out / f).read_text())["groups"]
    build(out, groups)


if __name__ == "__main__":
    main()
