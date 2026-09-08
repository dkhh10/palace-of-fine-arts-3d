"""Round-7 diagnostics for QA-05-5 / -8 / -10 / -11.

For any QA box: ray-cast every Nth pixel from the QA camera, classify the first hit, and then cast a SECOND ray
from that hit point towards the sun.  That gives, per box and per category, both "what fills it" and "how much of
it the sun actually reaches" - with the names of the objects doing the blocking.  Everything QA measures as a
luminance is one of those two things.

    blender -b --python scripts/env_r7_probe.py -- --boxes cam01_left_wing,cam01_shore --step 3
    blender -b --python scripts/env_r7_probe.py -- --boxes cam01_left_wing --nofoliage    (ENV ceiling probe)

Runs on assets/environment.blend + assets/architecture.blend (the same scene env_sightlines.coverage uses), so it
needs no master and no render.
"""
import bpy, sys, os, math, json
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common, qa_cameras, env_lib as L
from env_sightlines import COVERAGE_BOXES

ARGS = common.script_args()


def _arg(flag, default=None):
    return ARGS[ARGS.index(flag) + 1] if flag in ARGS and ARGS.index(flag) + 1 < len(ARGS) else default


EXTRA_BOXES = {
    # QA-05-8: cam 06's horizon strip.  QA states it as 0 0 1280 220 of the 1280x720 frame.
    "cam06_horizon": ("_qa_06_", (0, 0, 1280, 220), (1280, 720)),
    # QA-05-11: cam 03's ground.  The walk fills the bottom third of an 18 mm frame.
    "cam03_ground": ("_qa_03_", (0, 470, 1280, 720), (1280, 720)),
}
BOXES = dict(COVERAGE_BOXES)
BOXES.update(EXTRA_BOXES)


def classify(obj, mat_name, nm):
    if "leaf" in mat_name or "shrub" in mat_name or "reed" in mat_name or "forest" in mat_name or "canopy" in nm:
        return "foliage"
    if ("terrain" in nm or "ground" in nm or "water" in nm or "bed" in nm
            or "lawn" in mat_name or "gravel" in mat_name or "asphalt" in mat_name or "bed" in mat_name):
        return "ground"
    return "building"


def open_scene(nofoliage=False):
    bpy.ops.wm.open_mainfile(filepath=str(common.ASSET_FILES["ENV"]))
    arch = common.ASSET_FILES["ARCH"]
    if arch.exists():
        common.link_collection(arch, "ARCH", link=True)
    if nofoliage:
        n = 0
        for o in bpy.data.objects:
            if o.name.startswith(("ENV_tree_", "ENV_shrub_", "ENV_canopy", "ENV_forest")):
                o.hide_set(True)
                o.hide_viewport = True
                o.hide_render = True
                n += 1
        print(f"[probe] foliage hidden: {n} objects (ENV ceiling probe)")
    qa_cameras.ensure(bpy.context.scene)
    return bpy.context.scene


def probe(scene, name, step=3, sun=True, top=14):
    cam_key, box, res = BOXES[name]
    spec = next(c for c in qa_cameras.CAMERAS if cam_key in c["name"])
    loc = Vector(spec["loc"])
    f = (Vector(spec["target"]) - loc).normalized()
    r = f.cross(Vector((0, 0, 1))).normalized()
    u = r.cross(f).normalized()
    hw = 0.5 * 36.0 / spec["lens"]
    hh = hw * 9.0 / 16.0
    W, H = res
    x0, y0, x1, y1 = box
    sv = Vector(L.sun_vector())
    dg = bpy.context.evaluated_depsgraph_get()
    tot = 0
    cat = {"foliage": 0, "building": 0, "ground": 0, "sky": 0}
    lit = {"foliage": 0, "building": 0, "ground": 0}
    away = {}
    who = {}
    blockers = {}
    dists = []
    for py in range(y0, y1, step):
        for px in range(x0, x1, step):
            sx = ((px + 0.5) / W - 0.5) * 2
            sy = (0.5 - (py + 0.5) / H) * 2 + 2.0 * spec.get("shift_y", 0.0) * (hw / hh)
            d = (f + r * hw * sx + u * hh * sy).normalized()
            ok, hit, nrm, idx, obj, _ = scene.ray_cast(dg, loc, d, distance=4000)
            tot += 1
            if not ok:
                cat["sky"] += 1
                continue
            nm = obj.name
            mat = ""
            if obj.type == "MESH" and obj.data.materials:
                mi = obj.data.polygons[idx].material_index if idx < len(obj.data.polygons) else 0
                mm = obj.data.materials[min(mi, len(obj.data.materials) - 1)]
                mat = mm.name if mm else ""
            k = classify(obj, mat, nm)
            cat[k] += 1
            dists.append((hit - loc).length)
            key = f"{k}|{nm}|{mat}"
            who[key] = who.get(key, 0) + 1
            if sun:
                # pure occlusion: "can this point see the sun".  The normal offset takes the SUN's side of the
                # surface (leaf cards are single-sided and Cycles flips their normal, so the geometric normal's
                # own sign says nothing about whether the shader is lit); `away` records how much of the box is
                # turned away from the sun for the record.
                nn = nrm.normalized() if nrm.length > 0 else sv
                if nn.dot(sv) < 0:
                    away[k] = away.get(k, 0) + 1
                    nn = -nn
                o2 = hit + nn * 0.02 + sv * 0.05
                ok2, h2, n2, i2, o2b, _ = scene.ray_cast(dg, o2, sv, distance=1200)
                if ok2:
                    bn = o2b.name
                    blockers[bn] = blockers.get(bn, 0) + 1
                else:
                    lit[k] += 1
    print(f"\n=== {name}  box {box} of {res}  step {step}  samples {tot}")
    for k in ("foliage", "building", "ground", "sky"):
        s = f"{k:9s} {100.0 * cat[k] / max(1, tot):5.1f} %"
        if k != "sky" and cat[k]:
            s += (f"   sunlit {100.0 * lit[k] / cat[k]:5.1f} % of it"
                  f"   (normal turned from the sun {100.0 * away.get(k, 0) / cat[k]:5.1f} %)")
        print("   " + s)
    if dists:
        dists.sort()
        print(f"   hit distance  p10 {dists[len(dists)//10]:6.1f}  median {dists[len(dists)//2]:6.1f} "
              f" p90 {dists[9*len(dists)//10]:6.1f} m")
    surf = sum(cat[k] for k in ("foliage", "building", "ground"))
    if surf:
        print(f"   SUN REACH over all surfaces: {100.0 * sum(lit.values()) / surf:5.1f} %")
    print("   fills the box:")
    for key, c in sorted(who.items(), key=lambda kv: -kv[1])[:top]:
        k, nm, mat = key.split("|")
        o = bpy.data.objects.get(nm)
        where = f"({o.location.x:7.1f},{o.location.y:7.1f})" if o else ""
        print(f"      {100.0 * c / tot:5.2f}%  {k:8s} {nm:44s} {mat:26s} {where}")
    if blockers:
        print("   blocks the sun (samples shadowed):")
        for nm, c in sorted(blockers.items(), key=lambda kv: -kv[1])[:top]:
            o = bpy.data.objects.get(nm)
            where = f"({o.location.x:7.1f},{o.location.y:7.1f})" if o else ""
            note = f" h{o.get('height_m', 0):.0f} {str(o.get('note',''))[:26]}" if o else ""
            print(f"      {100.0 * c / max(1, surf):5.2f}%  {nm:44s}{where}{note}")
    return dict(cat=cat, lit=lit, tot=tot)


def main():
    names = (_arg("--boxes") or "cam01_left_wing,cam01_shore,cam03_ground,cam06_horizon").split(",")
    step = int(_arg("--step", 3))
    scene = open_scene(nofoliage="--nofoliage" in ARGS)
    out = {}
    for n in names:
        if n not in BOXES:
            print(f"[probe] unknown box {n}")
            continue
        out[n] = probe(scene, n, step=step, sun="--nosun" not in ARGS)
    p = _arg("--json")
    if p:
        json.dump(out, open(p, "w"), indent=1)
        print(f"[probe] wrote {p}")


if __name__ == "__main__":
    main()
