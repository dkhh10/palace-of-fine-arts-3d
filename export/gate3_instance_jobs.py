"""Gate 4: queue jobs for the PER-PLACEMENT irradiance of the 28 shrub/reed card meshes.

    python3 export/gate3_instance_jobs.py --probe          # one 12-placement validation job
    python3 export/gate3_instance_jobs.py --jobs 4         # the production jobs (1 379 placements)

CPU only, no Blender. Appends `inst_*` jobs to out/gate3/bake_jobs.json (replacing any of the same id) so
export/bake_queue.sh --gate3 runs them and export/out/bake_queue/status.json says `running` while the GPU is
ours. The 65 Gate 3 jobs already have records in out/gate3/bake/, so the queue skips them.

WHY PER PLACEMENT (docs/decisions.md 2026-09-16 "Shrub/reed irradiance is baked PER PLACEMENT"): those 28
meshes carry 1 379 placements, up to 101 on one mesh, 279 m apart on average, so bake_lm.py's `vertex` kind -
one bake per MESH, the rest recorded as shared_with - would give 1 379 shrubs 28 arbitrary values.

PLACEMENT ORDER: the order objects appear in export_set.json["assets"] (the Gate 1 export set's own object
order), filtered to the mesh. The consumer keys by OBJECT NAME; the array order is a convenience, never the
contract - gltfpack -mi re-orders instances (README "Gate 3 export hand-off" item 20).
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MAIN = Path(os.environ.get("PFA_MAIN_ROOT", "/Users/dk/Projects/3d render blender 3rd attempt building"))
OUT = ROOT / "export" / "out" / "gate3"
BLEND = "gate3_bake.blend"
CHUNK = 100          # objects per bpy.ops.object.bake call (one Cycles sync each)


def pick(rel):
    for base in (ROOT, MAIN):
        p = base / rel
        if p.exists():
            return p
    raise FileNotFoundError(rel)


def placements():
    """[(object, mesh)] in export-set order, for the 28 card meshes env_cards.json identified."""
    cards = json.loads((OUT / "env_cards.json").read_text())
    want = {r["mesh"] for r in cards["meshes"]}
    eset = json.loads(pick("export/out/gate1/export_set.json").read_text())
    rows = [(name, a["mesh"]) for name, a in eset["assets"].items() if a.get("mesh") in want]
    assert len(rows) == cards["summary"]["placements"], (
        f"{len(rows)} placements from export_set.json != {cards['summary']['placements']} in env_cards.json")
    return rows, sorted(want)


def write(jobs_new, force=False):
    p = OUT / "bake_jobs.json"
    d = json.loads(p.read_text())
    ids = {j["id"] for j in jobs_new}
    have = [j["id"] for j in jobs_new if (OUT / "bake" / f"{j['id']}.json").exists()]
    if have and not force:
        # review note 7: an accidental second run must not destroy a finished bake's records.
        raise SystemExit(f"refusing to replace {len(have)} existing bake record(s) {have[:4]} - pass --force")
    d["jobs"] = [j for j in d["jobs"] if j["id"] not in ids] + jobs_new
    p.write_text(json.dumps(d, indent=1))
    for j in jobs_new:
        rec = OUT / "bake" / f"{j['id']}.json"
        if rec.exists():
            rec.unlink()      # the queue skips a job whose record exists
    print(f"{p}: {len(d['jobs'])} jobs, {len(jobs_new)} new/replaced "
          f"({sum(len(j['objects']) for j in jobs_new)} placements)")


def main():
    rows, meshes = placements()
    argv = sys.argv[1:]
    force = "--force" in argv
    scope = "instance_jobs.json"            # the override covers all 1 379, whatever this job bakes
    if "--probe2" in argv:
        # Review fix 3 verification: the same 12 placements as inst_probe, as-is against the shadow-ray wrap
        # (and camray, measured only), arrays kept so the ratio can be taken on the vertices lit in both.
        step = max(len(rows) // 12, 1)
        sel = [rows[i * step][0] for i in range(12)]
        write([dict(id="inst_probe2", kind="instance", blend=BLEND, objects=sel, chunk=6,
                    variants=["asis", "shadow", "camray"], override_scope=scope,
                    single_chunk_index=1, keep_arrays=True, est_s=300)], force)
        return
    if "--split" in argv:
        # Split independence: one target placement baked in two jobs with different companions and chunk
        # sizes. With a scope-wide override the two values must agree to within sampling noise.
        tgt = rows[len(rows) // 2][0]
        near = [o for o, _ in rows[len(rows) // 2 + 1:len(rows) // 2 + 6]]
        far = [o for o, _ in rows[:3]] + [o for o, _ in rows[-2:]]
        write([dict(id="inst_splitA", kind="instance", blend=BLEND, objects=[tgt] + near, chunk=6,
                    variants=["shadow"], override_scope=scope, keep_arrays=True, est_s=120),
               dict(id="inst_splitB", kind="instance", blend=BLEND, objects=far + [tgt], chunk=2,
                    variants=["shadow"], override_scope=scope, keep_arrays=True, est_s=120)], force)
        print(f"split target: {tgt}")
        return
    if "--trees" in argv:
        # Review finding 6 / lead decision 6: the 14 near trees carry the same cut-out zeros (77-99 % of
        # their COLOR_0 vertices are exactly 0 -> black patches). Re-bake the two `vertex` jobs with the same
        # shadow-ray wrap, in place: same ids, same out/gate3/vertex/<id>.npz path and schema, so
        # gate3_compose.py --only vertex and the export's r2 encode re-run unchanged.
        jp = OUT / "bake_jobs.json"
        d = json.loads(jp.read_text())
        before = OUT / "vertex_irradiance_before_shadowray.npz"
        cur = OUT / "vertex_irradiance.npz"
        if cur.exists() and not before.exists():
            before.write_bytes(cur.read_bytes())
        touched = []
        for j in d["jobs"]:
            if j["kind"] == "vertex":
                j["override"] = "shadow"
                touched.append(j["id"])
                rec = OUT / "bake" / f"{j['id']}.json"
                npz = OUT / "vertex" / f"{j['id']}.npz"
                if (rec.exists() or npz.exists()) and not force:
                    raise SystemExit(f"refusing to replace {j['id']}'s record/npz - pass --force")
                for f in (rec, npz):
                    if f.exists():
                        f.unlink()
        jp.write_text(json.dumps(d, indent=1))
        print(f"vertex jobs armed with the shadow-ray override: {touched}; kept {before.name}")
        return
    if "--probe" in argv:
        # 12 placements spread across the list (different meshes, sun and shade), both variants, and the
        # first chunk baked as one multi-object call against the second baked one object at a time: that is
        # the test that a multi-object VERTEX_COLORS bake writes every selected object, not just the active.
        step = max(len(rows) // 12, 1)
        sel = [rows[i * step][0] for i in range(12)]
        write([dict(id="inst_probe", kind="instance", blend=BLEND, objects=sel, chunk=6,
                    variants=["asis", "opaque"], single_chunk_index=1, keep_arrays=True, est_s=240)])
        return
    n = int(argv[argv.index("--jobs") + 1]) if "--jobs" in argv else 4
    variants = ["shadow"]
    if "--variants" in argv:
        variants = argv[argv.index("--variants") + 1].split(",")
    per = -(-len(rows) // n)
    jobs = []
    for i in range(n):
        part = [o for o, _ in rows[i * per:(i + 1) * per]]
        if part:
            jobs.append(dict(id=f"inst_irr_{i:02d}", kind="instance", blend=BLEND, objects=part,
                             chunk=CHUNK, variants=variants, override_scope=scope,
                             est_s=60 + 2 * len(part)))
    write(jobs, force)
    (OUT / "instance_jobs.json").write_text(json.dumps(dict(
        placement_order="export_set.json assets order, filtered per mesh; object name is the key",
        meshes=len(meshes), placements=len(rows), chunk=CHUNK, variants=variants,
        jobs={j["id"]: len(j["objects"]) for j in jobs},
        objects=[dict(object=o, mesh=m) for o, m in rows]), indent=1))
    print(f"wrote {OUT / 'instance_jobs.json'} ({len(rows)} placements, {len(meshes)} meshes)")


main()
