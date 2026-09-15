#!/usr/bin/env python3
"""Generate web/src/stations_blender.json from scripts/qa_cameras.py + scripts/common.py.

Gate 0 review carry 10: the six stations and WATER_Z used to be HAND-COPIED into the viewer, with the
look-at targets existing only in the copy.  At run time the manifest is authoritative for everything it
carries (location, rotation_euler_xyz, lens, shift, clips, water.viewer_y); this file is the fallback
and the ONLY source of the look-at `target`, which the manifest does not carry — so it is generated,
never typed.  No bpy: the values are read out of the source with `ast`, so it runs under system python3.

    python3 web/tools/dump_stations.py [--check]

--check exits 1 if the committed JSON differs from what the sources say (CI / pre-merge use).

Rotation: qa_cameras.py derives every camera's rotation from (loc, target) with common.lookat_rotation,
which is mathutils' to_track_quat('-Z','Y') — not reimplemented here.  The viewer rebuilds exactly that
look-at itself (blenderCamera.stationMatrix).  The one case with no look-at solution is the straight-up
station, where qa_cameras.py sets a literal rotation_euler; that literal is copied over only after the
source is asserted to still contain it.
"""
import argparse, ast, json, math, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
QA = REPO / "scripts" / "qa_cameras.py"
COMMON = REPO / "scripts" / "common.py"
OUT = REPO / "web" / "src" / "stations_blender.json"

# qa_cameras.py's straight-up branch, asserted verbatim before its literal is used.
STRAIGHT_UP_SRC = 'obj.rotation_euler = (math.pi, 0.0, 0.0)'
STRAIGHT_UP_EULER = [math.pi, 0.0, 0.0]


def literal(node):
    """ast.literal_eval plus the `dict(name=..., loc=(...))` calls qa_cameras.py's CAMERAS uses."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict":
        if node.args:
            raise SystemExit("dict() with positional args in CAMERAS: fix this generator")
        return {kw.arg: literal(kw.value) for kw in node.keywords}
    if isinstance(node, (ast.List, ast.Tuple)):
        return [literal(e) for e in node.elts]
    return ast.literal_eval(node)


def module_assign(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return literal(node.value)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                and node.target.id == name:
            return literal(node.value)
    raise SystemExit(f"{name} not found as a module-level literal assignment")


def camera_defaults(tree):
    """cam_data.<attr> = <literal> inside ensure(): the sensor / clip constants."""
    out = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        t = node.targets[0]
        if not (isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "cam_data"):
            continue
        try:
            out[t.attr] = ast.literal_eval(node.value)
        except ValueError:
            pass            # cam_data.lens = spec["lens"] etc.
    return out


def build():
    qa_src = QA.read_text()
    qa = ast.parse(qa_src)
    cameras = module_assign(qa, "CAMERAS")
    water_z = module_assign(ast.parse(COMMON.read_text()), "WATER_Z")
    d = camera_defaults(qa)
    if STRAIGHT_UP_SRC not in qa_src:
        raise SystemExit(f"qa_cameras.py no longer contains `{STRAIGHT_UP_SRC}`: "
                         "the straight-up rotation rule changed, fix this generator")

    stations = []
    for i, c in enumerate(cameras):
        loc, tgt = list(c["loc"]), list(c["target"])
        straight_up = abs(tgt[0] - loc[0]) < 1e-6 and abs(tgt[1] - loc[1]) < 1e-6
        stations.append({
            "index": i + 1,
            "name": c["name"],
            "location": loc,
            "target": tgt,
            # Only the degenerate straight-up station has no look-at solution; every other rotation is
            # rebuilt from (location, target) by the viewer, and the manifest overrides it anyway.
            "rotation_euler": STRAIGHT_UP_EULER if straight_up else None,
            "rotation_mode": "XYZ",
            "lens": c["lens"],
            "sensor_width": d.get("sensor_width", 36.0),
            "sensor_fit": d.get("sensor_fit", "HORIZONTAL"),
            "shift_x": c.get("shift_x", 0.0),
            "shift_y": c.get("shift_y", 0.0),
            "clip_start": d.get("clip_start", 0.1),
            "clip_end": d.get("clip_end", 5000.0),
            "ref": c["ref"],
        })
    return {
        "_generated_by": "web/tools/dump_stations.py from scripts/qa_cameras.py + scripts/common.py",
        "_authority": "the manifest wins at run time; this file supplies `target` (not in the manifest) "
                      "and the whole set when no manifest is reachable",
        "water_z": water_z,
        "stations": stations,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 1 if the committed JSON is stale")
    a = ap.parse_args()
    data = build()
    text = json.dumps(data, indent=1) + "\n"
    if a.check:
        old = OUT.read_text() if OUT.exists() else ""
        if old != text:
            print(f"[dump_stations] STALE: {OUT} differs from the sources", file=sys.stderr)
            return 1
        print(f"[dump_stations] up to date: {OUT}")
        return 0
    OUT.write_text(text)
    print(f"[dump_stations] wrote {OUT} ({len(data['stations'])} stations, water_z {data['water_z']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
