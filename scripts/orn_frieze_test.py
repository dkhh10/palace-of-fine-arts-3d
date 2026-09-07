"""QA-01-11 acceptance test for orn_lib.array_unit_along_run.

Appends the ORN moulding units and ARCH's read-only `SOCKET_frieze_run_*` empties into an empty scene, arrays a unit
along every socket (straight and curved), checks the geometry (unit spacing, end-flush error, distance of every unit
from the arc centre) and renders a straight run and a curved run for the record.

    blender --background --python scripts/orn_frieze_test.py -- [--kind greek_key|rosette_band] [--no-render]
Output: renders/previews/ornament/frieze_run_straight.png / frieze_run_curved.png and a printed report.
"""
import bpy, math, os, sys
from pathlib import Path
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import orn_lib as L
import orn_preview as P

ARGS = common.script_args()
KIND = ARGS[ARGS.index("--kind") + 1] if "--kind" in ARGS else "rosette_band"
OUT_DIR = common.RENDERS / "previews" / "ornament"


def append_objects(blend, names):
    with bpy.data.libraries.load(str(blend), link=False) as (df, dt):
        dt.objects = [n for n in df.objects
                      if n in names or any(n.startswith(p[:-1]) for p in names if p.endswith("*"))]
    out = []
    for o in dt.objects:
        if o is not None:
            bpy.context.scene.collection.objects.link(o)
            out.append(o)
    return out


def mock_rostra_sockets():
    """Stand-ins for the `frieze_run` sockets with subtype 'greek_key' that ARCH is adding along the rostra walls and
    the planter-box bases (QA-01-11): one straight 12 m run and one 90 deg curved run of radius 9 m. They let this
    test exercise the rosette-band unit and the curved branch before ARCH ships the real sockets."""
    made = []
    coll = bpy.context.scene.collection
    s = common.add_empty("SOCKET_frieze_run_900", (0.0, 40.0, 4.0), coll, size=0.5)
    s["orn_type"] = "frieze_run"; s["subtype"] = "greek_key"; s["run_length"] = 12.0; s["size_hint"] = 12.0
    made.append(s)
    r, cen = 9.0, Vector((30.0, 40.0))
    a0 = math.radians(180.0)
    s = common.add_empty("SOCKET_frieze_run_901", (cen.x + r * math.cos(a0), cen.y + r * math.sin(a0), 4.0), coll,
                         size=0.5, rotation=(0.0, 0.0, a0 - math.pi / 2))   # +X = clockwise tangent, +Y = outward
    s["orn_type"] = "frieze_run"; s["subtype"] = "greek_key"
    s["arc_center"] = [cen.x, cen.y, 0.0]; s["arc_radius"] = r
    s["arc_start"] = a0; s["arc_end"] = a0 - math.pi / 2
    s["run_length"] = r * math.pi / 2; s["size_hint"] = s["run_length"]
    made.append(s)
    return made


def main():
    bpy.ops.wm.read_homefile(use_empty=True)
    common.wipe_scene()
    common.setup_scene()
    units = append_objects(common.ASSET_FILES["ORN"],
                           [L.asset_name(k, 1, 1) for k in ("greek_key", "rosette_band")])
    units = {u.get("orn_type"): u for u in units}
    for u in units.values():
        u.hide_viewport = u.hide_render = True
    sockets = append_objects(common.ASSET_FILES["ARCH"], ["SOCKET_frieze_run_*"])
    sockets.sort(key=lambda o: o.name)
    sockets += mock_rostra_sockets()
    print(f"[frieze_test] units {sorted(units)} ; {len(sockets)} frieze_run sockets")
    for k, u in units.items():
        print(f"[frieze_test] {u.name}: unit_length {L.unit_length_of(u):.3f} m, band {u.get('band_height')}, "
              f"relief {u.get('relief_depth')}")

    coll = common.rebuild_collection("FRIEZE_TEST")
    runs = {}
    total = 0
    worst_gap = worst_radial = worst_margin = 0.0
    for sk in sockets:
        # subtype greek_fret (colonnade architrave, rotunda ressauts) -> plain meander;
        # subtype greek_key / rostra (podium + box bases, QA-01-11) -> meander with rosette bosses
        unit = units["rosette_band" if sk.get("subtype") in ("greek_key", "rostra") else "greek_key"]
        made = L.array_unit_along_run(unit, sk, collection=coll, alternatives=[units["greek_key"]])
        runs[sk.name] = made
        total += len(made)
        ul = L.unit_length_of(made[0])
        # measured spacing between consecutive unit origins vs the nominal unit length
        for a, b in zip(made, made[1:]):
            step = (b.matrix_world.translation - a.matrix_world.translation).length
            worst_gap = max(worst_gap, abs(step - ul * a.matrix_world.to_scale().x))
        c = sk.get("arc_center")
        if c is not None:
            cen = Vector((float(c[0]), float(c[1])))
            r = float(sk["arc_radius"])
            for o in made:
                t = o.matrix_world.translation
                worst_radial = max(worst_radial, abs((Vector((t.x, t.y)) - cen).length - r))
        # plain margin left at the far end (0 for a scaled fit, < one unit for a centred fit)
        run = float(sk.get("run_length", 0.0))
        u = L.unit_length_of(made[-1])
        end_local = made[-1].matrix_world @ Vector((u / 2, 0, 0))
        if c is None:
            worst_margin = max(worst_margin, abs(run - (end_local - sk.matrix_world.translation).length))
    print(f"[frieze_test] {total} units placed on {len(sockets)} sockets; worst unit-to-unit spacing error "
          f"{worst_gap * 1000:.1f} mm; worst plain margin at a run end {worst_margin * 1000:.0f} mm (a centred fit "
          f"leaves < one unit of plain band, by design); worst radial deviation from the arc (chord sagitta) "
          f"{worst_radial * 1000:.1f} mm")

    if "--no-render" in ARGS:
        return
    rig, cam = P.build_rig()
    g = bpy.data.objects.get("preview_ground")      # the rig's ground plane is at the world origin; not useful here
    if g:
        g.hide_render = True
    scene = bpy.context.scene
    common.configure_eevee(scene, samples=24)
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    def pick(pred):
        for sk in sockets:
            if pred(sk):
                return sk.name
        return None
    shots = [("straight", pick(lambda s: s.get("subtype") in (None, "greek_fret") and s.get("arc_center") is None)),
             ("curved", pick(lambda s: s.get("arc_center") is not None and not s.name.endswith("901"))),
             ("rostra_straight", pick(lambda s: s.get("subtype") == "greek_key" and float(s.get("run_length", 0)) > 5.0)),
             ("rostra_curved", "SOCKET_frieze_run_901")]
    for tag, sname in shots:
        sk = bpy.data.objects.get(sname)
        made = runs.get(sname)
        if sk is None or not made:
            continue
        shown = made[:max(2, min(len(made), int(6.0 / L.unit_length_of(made[0]))))]
        keep = {o.name for o in shown}            # frame a 6 m stretch of THIS run only
        for o in coll.objects:
            o.hide_render = o.name not in keep
        pts = [o.matrix_world.translation for o in shown]
        mid = sum(pts, Vector((0, 0, 0))) / len(pts) + Vector((0, 0, 0.26))
        span = max((a - b).length for a in pts for b in pts) + L.unit_length_of(made[0])
        out_dir_v = (shown[len(shown) // 2].matrix_world.to_3x3() @ Vector((0, 1, 0))).normalized()
        eye = mid + out_dir_v * (span * 0.80) + Vector((0, 0, span * 0.30))
        cam.location = eye
        cam.rotation_euler = common.lookat_rotation(eye, mid)
        cam.data.lens = 55.0
        cam.data.clip_end = 500.0
        bpy.context.view_layer.update()
        scene.render.filepath = str(OUT_DIR / f"frieze_run_{tag}.png")
        bpy.ops.render.render(write_still=True)
        for o in coll.objects:
            o.hide_render = False
        print(f"[frieze_test] rendered {scene.render.filepath} ({len(shown)} of {len(made)} units, span {span:.2f} m, "
              f"mesh {shown[0].data.name}, visible-in-scene {sum(1 for o in bpy.data.objects if o.type == 'MESH' and not o.hide_render)})")


if __name__ == "__main__":
    main()
