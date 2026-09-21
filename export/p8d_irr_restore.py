"""RETIRED 2026-09-21 (Phase 9 re-bake, A.4). DO NOT RUN. Kept only as the record of what it did.

The Phase 9 chain re-bakes **all 166** far-tree placements in one `tfirr_00..03` set, at one scene state, in
the r19 world - which is A.4's "all or none" rule taken on the "all" side, because the world moved and a
partial set cannot be mixed with it. After that bake `export/out/gate3/trees_far/instance_irradiance.json`
holds ONE population and needs no join, so this script has nothing legitimate left to do: its 6c source
(2026-09-17, md5 11212fbc..., a world whose diffuse-sky blue is 2.64x the current one - measured this round,
per-channel mean B 11.4928 -> 4.3453) would paste values from one lighting state into a file describing
another, which is the exact defect it was written to prevent, inverted.

The QA-23 evidence it rested on does not carry either: "7 of 10 crown boxes moved AWAY from the Phase 8
Cycles references" was measured against references rendered in the OLD world. This round re-renders all six
(renders/qa_comparisons/cycles_p9/), so the comparison basis moves with the bake instead of standing still.

Original docstring follows.

QA 23 fix: put the 127 EXISTING far trees back on their 6c irradiance, keep the belt's 39 on the r2 bake.

    python3 export/p8d_irr_restore.py [--check]      # CPU only: no Blender, no GPU

WHY. The 8d r2 chain re-baked `E_placement` for all 166 far trees (the 39 hall-belt trees had no rows and
the join had to be re-keyed anyway). The re-bake is not the 6c bake: its scene is the 21:58
master_delivery, so every existing crown came back 4-16 % brighter against its background and QA 23
measured 7 of 10 crown boxes moving AWAY from the Phase 8 Cycles references - the 8e blade margin lost
photometrically, not geometrically. The decision (docs/decisions.md, QA 23): the 127 go back to the values
that were measured and accepted, the 39 keep the only values they have, and the two populations are
reported side by side so the next QA round can see them separately.

THE SOURCE OF THE 127 IS THE 6C FILE ITSELF, not a manifest copy: `<phase6-bake worktree>/export/out/
gate3/trees_far/instance_irradiance.json`, generated 2026-09-17T10:16:23, 127 rows, untouched since the
6c bake (mtime Sep 17 10:16, md5 recorded in the output). The deploy-10 manifest is NOT usable - it
already carries the r2 values (its lighting block is generated 2026-09-19T22:47:28 and all 127 rows
differ). Every row is joined BY WORLD LOCATION on the same 0.02 m grid manifest_v4 uses; the object
labels are ignored, because the belt's name-sorted interleave re-pointed 87 of the 127 TREEFAR_### ids.

The per-mesh and per-file statistics are recomputed from the merged rows, so nothing in the file
describes a population it no longer holds. Provenance is written into the file: `rows_source` counts,
the source paths and md5s, and a `source` field on every row.
"""
import argparse
import hashlib
import json
import os
import statistics
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = Path(os.environ.get("PFA_MAIN_ROOT", "/Users/dk/Projects/3d render blender 3rd attempt building"))
SIXC = MAIN / ".claude/worktrees/phase6-bake/export/out/gate3/trees_far/instance_irradiance.json"
CUR = ROOT / "export/out/gate3/trees_far/instance_irradiance.json"
JOIN_TOL_M = 0.02                      # the grid manifest_v4 joins on
LUM = (0.2126, 0.7152, 0.0722)


def _retired():
    raise SystemExit(
        "export/p8d_irr_restore.py is RETIRED (Phase 9 A.4): the far-tree irradiance is now one population "
        "baked in the r19 world. Running it would mix two lighting states in one file. "
        "Set PFA_IRR_RESTORE_I_KNOW=1 only if you are deliberately reproducing the Phase 8 file.")


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def key(loc):
    return tuple(round(float(v) / JOIN_TOL_M) for v in loc)


def lum(rgb):
    return sum(c * w for c, w in zip(rgb, LUM))


def stats(rows):
    """The per-mesh / per-file block the file carries, recomputed from whatever rows it now holds."""
    if not rows:
        return {}
    ch = list(zip(*[r["rgb"] for r in rows]))
    lums = [lum(r["rgb"]) for r in rows]
    mn = [round(min(c), 6) for c in ch]
    mx = [round(max(c), 6) for c in ch]
    me = [round(sum(c) / len(c), 6) for c in ch]
    return dict(n=len(rows), min=mn, max=mx, mean=me,
                lum_min=round(min(lums), 6), lum_max=round(max(lums), 6),
                lum_mean=round(sum(lums) / len(lums), 6),
                lum_ratio=round(max(lums) / max(min(lums), 1e-9), 2),
                cov_mean=round(sum(r["cov"] for r in rows) / len(rows), 3))


def modulation(row, proto_e_bake):
    """What the viewer actually applies to an impostor: clamp(E_placement / E_bake, 0, 4) per channel,
    strength 1.0 (manifest `impostors.ratio`). Reported as its luminance, which is what a crown box sees."""
    e = proto_e_bake
    m = [min(4.0, (row["rgb"][i] / e[i]) if e[i] > 0 else 1.0) for i in range(3)]
    return lum(m)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report the two populations and write nothing")
    a = ap.parse_args()
    if os.environ.get("PFA_IRR_RESTORE_I_KNOW") != "1":
        _retired()
    cur = json.loads(CUR.read_text())
    six = json.loads(SIXC.read_text())
    assert cur["schema"] == six["schema"], (cur["schema"], six["schema"])
    old_rows = {}
    for m in six["meshes"].values():
        for r in m["placements"]:
            k = key(r["loc"])
            assert k not in old_rows, f"two 6c rows in one {JOIN_TOL_M} m cell: {k}"
            old_rows[k] = r

    restored, kept, out_rows = 0, 0, []
    proto_of_mesh = {v["mesh"]: k for k, v in json.loads(
        (ROOT / "export/out/gate3/trees_far/topology.json").read_text())["prototypes"].items()}
    for mesh, blk in cur["meshes"].items():
        rows = []
        for r in blk["placements"]:
            o = old_rows.get(key(r["loc"]))
            if o is not None:
                assert max(abs(x - y) for x, y in zip(o["loc"], r["loc"])) < JOIN_TOL_M, (o["loc"], r["loc"])
                rows.append(dict(r, rgb=o["rgb"], mean_all=o["mean_all"], cov=o["cov"], source="6c"))
                restored += 1
            else:
                rows.append(dict(r, source="8d-r2"))
                kept += 1
        blk.update(stats(rows))
        blk["placements"] = rows
        out_rows.extend((mesh, r) for r in rows)

    # the two populations, as the lead asked: the median modulation the impostor path applies
    med = {}
    for tag in ("6c", "8d-r2"):
        vals = [modulation(r, cur["prototypes"][proto_of_mesh[mesh]]["E_bake"])
                for mesh, r in out_rows if r["source"] == tag]
        med[tag] = dict(n=len(vals),
                        median=round(statistics.median(vals), 4) if vals else None,
                        p10=round(statistics.quantiles(vals, n=10)[0], 4) if len(vals) > 9 else None,
                        p90=round(statistics.quantiles(vals, n=10)[8], 4) if len(vals) > 9 else None)
    lums = [lum(r["rgb"]) for _, r in out_rows]
    print(f"[irr_restore] 6c rows restored {restored}, r2 belt rows kept {kept}, total {len(out_rows)}")
    for tag, d in med.items():
        print(f"[irr_restore] {tag:6s} n={d['n']:3d} median modulation {d['median']} "
              f"(p10 {d['p10']}, p90 {d['p90']})")
    print(f"[irr_restore] file lum_mean {cur['lum_mean']} -> {round(sum(lums) / len(lums), 6)}")
    if a.check:
        return 0

    cur.update(
        generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
        generator="export/trees_far_compose.py + export/p8d_irr_restore.py (QA 23)",
        lum_min=round(min(lums), 6), lum_max=round(max(lums), 6),
        lum_mean=round(sum(lums) / len(lums), 6),
        range_global=round(max(max(r["rgb"]) for _, r in out_rows), 6),
        zero_placements=sum(1 for _, r in out_rows if max(r["rgb"]) <= 0),
        rows_source=dict(
            restored_6c=restored, kept_8d_r2=kept,
            rule="joined BY WORLD LOCATION on a %.2f m grid, the same join manifest_v4 uses; the "
                 "TREEFAR_### labels are ignored because the belt's name-sorted interleave re-pointed 87 "
                 "of the 127" % JOIN_TOL_M,
            why=("QA 23: the r2 re-bake brightened every existing crown 4-16 %% against its background "
                 "(7 of 10 boxes away from the Phase 8 Cycles references), so the 127 trees that HAVE a "
                 "6c value go back to it; the 39 hall-belt trees keep the r2 bake because they have no "
                 "other value. The two populations are reported separately in `modulation_median`."),
            source_6c=dict(path=str(SIXC), md5=md5(SIXC), generated=six["generated"],
                           rows=six["placements"]),
            source_r2=dict(md5_before=md5(CUR), generated=json.loads(CUR.read_text())["generated"],
                           rows=cur["placements"]),
            not_used=("the deploy-10 manifest's lighting block: it already carries the r2 values "
                      "(generated 2026-09-19T22:47:28, all 127 rows differ from the 6c file)")),
        modulation_median=med)
    CUR.write_text(json.dumps(cur, indent=1) + "\n")
    print(f"[irr_restore] wrote {CUR} ({CUR.stat().st_size} B, md5 {md5(CUR)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
