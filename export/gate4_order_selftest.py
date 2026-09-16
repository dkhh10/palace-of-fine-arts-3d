"""Negative tests for the Gate 4 instance-row check in export/verify_glb.py.

    python3 export/gate4_order_selftest.py          # exit 0 = every case behaved

CPU only, no Blender, no GPU, nothing written outside a temp dir. The Gate 4 check is only ever run against
good data, so an inverted condition in `instance_irradiance_check` would pass forever (review r5, finding 6).
Each case takes the REAL out/gate3 artefacts, breaks exactly one thing in a copy of instance_order.json, and
asserts the check reports it. The glb and the irradiance JSON are symlinked, never copied (37 MB).
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate3_common as g3  # noqa: E402
import verify_glb  # noqa: E402


def find(name, sub):
    for base in (g3.ROOT, g3.MAIN_ROOT):
        p = base / "export" / "out" / sub / name
        if p.exists():
            return p
    raise SystemExit(f"{sub}/{name} is in neither checkout: nothing to test against")


def case(name, mutate, want_fail, root):
    """Run the check on a copy of the artefacts with `mutate` applied to the order file."""
    d = Path(tempfile.mkdtemp(dir=root))
    (d / "gate1").mkdir()
    (d / "gate3").mkdir()
    (d / "gate1" / "env.glb").symlink_to(find("env.glb", "gate1"))
    irr = json.loads(find("instance_irradiance.json", "gate3").read_text())
    order = json.loads(find("instance_order.json", "gate3").read_text())
    mutate(order, irr)
    (d / "gate3" / "instance_order.json").write_text(json.dumps(order))
    (d / "gate3" / "instance_irradiance.json").write_text(json.dumps(irr))
    bad = []
    try:
        row = verify_glb.instance_irradiance_check(d / "gate1", bad)
    except Exception as e:                                  # a crash is a failure, not a report
        print(f"  FAIL {name}: raised {type(e).__name__}: {e}")
        return False
    finally:
        shutil.rmtree(d, ignore_errors=True)
    failed = bool(bad) or (row is not None and row.get("counts_match") is False)
    ok = failed == want_fail
    print(f"  {'ok  ' if ok else 'FAIL'} {name}: "
          f"{'reported ' + bad[0][:90] if bad else 'clean'}")
    return ok


def main():
    root = tempfile.mkdtemp(prefix="gate4_selftest_")
    # Baseline: the artefacts as they are on disk must come back clean. A harness order file beside an
    # irradiance JSON with no `loc` is a NOTE, not a failure - the join cannot be run correctly yet - so the
    # baseline expects no failure either way, and the last case below covers the harness-once-loc-exists rule.
    cases = [
        ("unmutated data passes", lambda o, i: None, False),
        ("one row dropped from a segment", lambda o, i: o["nodes"][0]["segments"][0].__setitem__(1, 0), True),
        ("one row added to a segment", lambda o, i: o["nodes"][0]["segments"][0].__setitem__(1, 999), True),
        ("segment offset out of step",
         lambda o, i: next(n for n in o["nodes"] if len(n["segments"]) > 1)["segments"][2].__setitem__(2, 0),
         True),
        ("node index points at a plain node", lambda o, i: o["nodes"][0].__setitem__("gltf_node", 0), True),
        ("node index is null", lambda o, i: o["nodes"][0].__setitem__("gltf_node", None), True),
        ("node index out of range", lambda o, i: o["nodes"][0].__setitem__("gltf_node", 10 ** 6), True),
        ("a mesh loses all its rows", lambda o, i: o["nodes"].pop(0), True),
        ("glb_bytes from another env.glb", lambda o, i: o.__setitem__("glb_bytes", 1), True),
        ("harness order file but the bake wrote loc",
         lambda o, i: (o.__setitem__("loc_in_json", False),
                       [p.__setitem__("loc", [0.0, 0.0, 0.0])
                        for m in i["meshes"].values() for p in m["placements"]]), True),
    ]
    results = [case(n, m, w, root) for n, m, w in cases]
    shutil.rmtree(root, ignore_errors=True)
    print(f"[gate4_selftest] {sum(results)}/{len(results)} cases behaved")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
