"""Phase 8d step 1: the PIN REPORT. Does the rebuilt Gate 1 set still stand on MAIN's bakes?

    python3 export/p8d_pin.py            # exit 1 if any pin fails; writes out/gate1/p8d_pin.json

The 8d ENV change (backdrop materials + a tree belt) and the 8a-3 shrub-card UV scale must not move
anything the Gate 2 PBR bakes, the Gate 3 lightmaps, the impostor atlases or the instance-row joins are
addressed by. What is pinned, from the brief and docs/decisions.md "8a export gate":

  * uv1 groups / atlas tiles / coverage and uv2 meshes and lightmap slots - identical (the bakes' UV space)
  * near trees 20 / far billboards 127, and the near and far LISTS identical in content AND order (the
    billboard index is the impostor atlas' key and the instance rows' order)
  * ARCH and ORN placed triangles identical; ENV placed = MAIN + 6 900 (the belt) and nothing else
  * the lawn group renamed lawn -> backdrop_lawn, with no `..._lawn` group left behind

CPU only: it reads two export_set.json files. The glb byte-identity check (arch/orn/ground) runs after the
pack, in p8d_pin.py --glbs.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = Path(os.environ.get("PFA_MAIN_ROOT", "/Users/dk/Projects/3d render blender 3rd attempt building"))
EXPECT_ENV_DELTA = 6900


def sha(p):
    import hashlib
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pin(a, b, out):
    def eq(name, va, vb, expect=None):
        ok = (va == vb) if expect is None else (vb == expect)
        out["checks"].append(dict(name=name, ok=bool(ok), main=va, new=vb, expected=expect))
        return ok

    ok = True
    for k in ("uv1_groups", "uv1_atlas_tiles", "uv1_coverage", "uv1_coverage_min", "uv2_meshes",
              "lightmap_slots", "lightmap_assets", "uv_missing_counts", "meshes_not_single_material"):
        ok &= eq(k, a.get(k), b.get(k))
    ta, tb = a["tree_rule"], b["tree_rule"]
    for k in ("trees_total", "within_radius", "near_exported", "far_billboards", "lod2_blob_objects",
              "near_tris_used"):
        ok &= eq(f"tree_rule.{k}", ta.get(k), tb.get(k))
    ok &= eq("tree_far_list (order and content)", a["tree_far_list"], b["tree_far_list"])
    ok &= eq("tree_near_list (order and content)", a["tree_near_list"], b["tree_near_list"])
    for cls in ("ARCH", "ORN"):
        ok &= eq(f"placed_tris.{cls}", a["totals"]["placed_tris"][cls], b["totals"]["placed_tris"][cls])
    da = b["totals"]["placed_tris"]["ENV"] - a["totals"]["placed_tris"]["ENV"]
    ok &= eq("placed_tris.ENV delta", da, da, expect=EXPECT_ENV_DELTA)
    # the lawn rename, seen through the derived export names
    def groups(doc, needle):
        return sorted({n for n in doc["assets"] if needle in n})
    ok &= eq("lawn groups gone (MAIN had them)", None, groups(b, "_lawn") and
             [n for n in groups(b, "_lawn") if "backdrop_lawn" not in n], expect=[])
    ok &= eq("backdrop_lawn group present", True, bool(groups(b, "backdrop_lawn")), expect=True)
    out["lawn"] = dict(main=groups(a, "_lawn"), new=groups(b, "_lawn"))
    out["env_placed"] = dict(main=a["totals"]["placed_tris"]["ENV"],
                             new=b["totals"]["placed_tris"]["ENV"], delta=da)
    return ok


def glbs():
    """After the pack: arch / orn / ground glbs byte-identical to MAIN, env / env_shrubs expected to move."""
    out = {}
    for name in ("arch.glb", "orn.glb", "ground.glb", "env.glb", "env_shrubs.glb", "env_trees.glb",
                 "env_trees_lod1.glb"):
        p, q = ROOT / "export/out/gate1" / name, MAIN / "export/out/gate1" / name
        if not p.exists() or not q.exists():
            out[name] = "missing"
            continue
        out[name] = dict(bytes_main=q.stat().st_size, bytes_new=p.stat().st_size,
                         identical=sha(p) == sha(q))
    pinned = ("arch.glb", "orn.glb", "ground.glb")
    ok = all(isinstance(out[n], dict) and out[n]["identical"] for n in pinned)
    print(json.dumps(out, indent=1))
    print(f"[p8d_pin] glbs {'PASS' if ok else 'FAIL'}: {', '.join(pinned)} must be byte-identical")
    return ok, out


def main():
    outp = ROOT / "export/out/gate1/p8d_pin.json"
    if "--glbs" in sys.argv:
        ok, out = glbs()
        rec = json.loads(outp.read_text()) if outp.exists() else {}
        rec["glbs"] = out
        rec["glbs_ok"] = ok
        outp.write_text(json.dumps(rec, indent=1))
        return 0 if ok else 1
    a = json.loads((MAIN / "export/out/gate1/export_set.json").read_text())
    b = json.loads((ROOT / "export/out/gate1/export_set.json").read_text())
    out = dict(main=str(MAIN / "export/out/gate1/export_set.json"), checks=[])
    ok = pin(a, b, out)
    out["ok"] = bool(ok)
    outp.write_text(json.dumps(out, indent=1))
    for c in out["checks"]:
        mark = "ok  " if c["ok"] else "FAIL"
        v = c["expected"] if c["expected"] is not None else c["new"]
        print(f"[pin] {mark} {c['name']}: {str(v)[:110]}")
    print(f"[p8d_pin] ENV placed {out['env_placed']['main']} -> {out['env_placed']['new']} "
          f"(+{out['env_placed']['delta']}), lawn groups {out['lawn']['main']} -> {out['lawn']['new']}")
    print(f"[p8d_pin] {'PASS' if ok else 'FAIL'} -> {outp}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
