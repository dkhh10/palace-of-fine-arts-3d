"""QA-05-6 probe: where does the rotunda entablature land in cam01 pixels, and what does a crop of it look like?

    blender --background <blend> --python scripts/arch_entab_probe.py -- [--map] [--render OUT.png]
                                        [--cam CAM_qa_01_lagoon_hero] [--res 1920 1080] [--spp 48]
                                        [--border x0 y0 x1 y1]

--map   prints, for a grid of (d, z) points on the near (lagoon) face of the rotunda -- d = projection outward from
        the wall plane at apothem P.WALL_APOTHEM, z = world height -- the pixel row/column the camera puts them at.
        This is the only honest way to know which model surface owns which row of QA's box 900 262 1020 296:
        a projecting moulding is lifted up the frame by (d * tan(up-look angle)), so profile depth and height mix.
--render renders only the border box (Cycles, --spp samples, denoised) into a full-frame-sized PNG, so the QA box
        coordinates stay valid while the render costs a fraction of a hero frame.
"""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import arch_params as P
from bpy_extras.object_utils import world_to_camera_view

args = common.script_args()


def opt(flag, n=1, cast=float, default=None):
    if flag not in args:
        return default
    vals = args[args.index(flag) + 1:args.index(flag) + 1 + n]
    return [cast(v) for v in vals] if n > 1 else cast(vals[0])


CAM = opt("--cam", 1, str, "CAM_qa_01_lagoon_hero")
RES = opt("--res", 2, int, [1920, 1080])
SPP = opt("--spp", 1, int, 48)
OUT = opt("--render", 1, str, None)
BORDER = opt("--border", 4, int, None)

scene = bpy.context.scene
cam = bpy.data.objects.get(CAM)
if cam is None:
    raise SystemExit(f"camera {CAM} not found: {[o.name for o in bpy.data.objects if o.type == 'CAMERA']}")
scene.camera = cam
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.resolution_percentage = 100

# near (lagoon) face: outward normal at compass azimuth FACE_AZ0, wall plane at apothem WALL_APOTHEM
nx, ny = P.az_dir(P.FACE_AZ0)


def pix(d, z):
    """(projection d outward from the wall plane, world height z) on the near face centre -> (col, row)"""
    r = P.WALL_APOTHEM + d
    co = world_to_camera_view(scene, cam, (nx * r, ny * r, z))
    return co.x * RES[0], (1.0 - co.y) * RES[1]


if "--map" in args or OUT is None:
    print(f"[probe] {CAM} loc {tuple(round(v, 2) for v in cam.location)} lens {cam.data.lens} "
          f"shift {cam.data.shift_x:.3f},{cam.data.shift_y:.3f} res {RES}")
    c0, r0 = pix(0.0, P.ENTABLATURE_Z0)
    c1, r1 = pix(0.0, P.ENTABLATURE_Z1)
    print(f"[probe] wall plane: entablature z {P.ENTABLATURE_Z0} -> row {r0:.1f}, z {P.ENTABLATURE_Z1} -> row {r1:.1f}; "
          f"scale {(r0 - r1) / (P.ENTABLATURE_Z1 - P.ENTABLATURE_Z0):.2f} px/m   col at d=0: {c0:.1f}")
    cd, rd = pix(1.0, P.ENTABLATURE_Z0)
    print(f"[probe] 1.00 m of outward projection lifts a point by {r0 - rd:.2f} px "
          f"(= {(r0 - rd) / ((r0 - r1) / (P.ENTABLATURE_Z1 - P.ENTABLATURE_Z0)):.3f} m of apparent height)")
    print(f"{'z':>7} {'d':>6} {'row':>8} {'col':>8}")
    for z in (P.ENTABLATURE_Z0, P.ENTABLATURE_Z0 + 1.4, P.ENTABLATURE_Z0 + 2.6, P.ENTABLATURE_Z0 + 3.2,
              P.ENTABLATURE_Z1, P.ATTIC_Z0 + P.ATTIC_BASE_MOULDING_H, P.ATTIC_Z1):
        for d in (0.0, 0.5, 1.0, 1.7):
            c, r = pix(d, z)
            print(f"{z:7.2f} {d:6.2f} {r:8.1f} {c:8.1f}")

if OUT:
    # exactly the preset QA renders the hero with, so the crop's absolute luminances are comparable with
    # renders/previews/qa/round05_01_lagoon_hero_cycles.png (the "before" of the QA-05-6 measurement)
    import light_presets
    light_presets.apply_final_cycles(scene, samples=SPP, time_limit=0.0)
    if BORDER:
        x0, y0, x1, y1 = BORDER
        scene.render.use_border = True
        scene.render.use_crop_to_border = False
        scene.render.border_min_x = x0 / RES[0]
        scene.render.border_max_x = x1 / RES[0]
        scene.render.border_min_y = 1.0 - y1 / RES[1]
        scene.render.border_max_y = 1.0 - y0 / RES[1]
        print(f"[probe] border {BORDER}")
    scene.render.filepath = OUT if os.path.isabs(OUT) else str(common.ROOT / OUT)
    scene.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    print("[probe] wrote", scene.render.filepath)
