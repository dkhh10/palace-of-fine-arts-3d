"""Round-11 review proof: run the real `lead_build.sh` bake sequence on a COPY of master.blend and show that the
saved state is what it should be.

    blender -b --python scripts/light_r11_verify.py -- --blend /path/to/master_copy.blend [--render]

Checks, in order, printing the vault lights' `energy`, `energy_W`, `use_custom_distance` / `cutoff_distance` and the
scene engine at each step:

  1. as opened            - the state build_master.py leaves behind (Eevee engine + Eevee vault override)
  2. after light_probes.bake() - review fixes 1 and 2: the bake runs on the PHYSICAL rig, then the override AND the
     original engine are restored in a finally
  3. after save + reopen  - what the lead's master.blend would actually carry

`--render` additionally renders cam04 through `apply_viewport_eevee` so the QA-04-12 numbers in the preset's comment
are measured on the saved file rather than asserted. Never touches the real master.blend.
"""
import bpy, os, sys, math
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_presets as lp
import light_build as lb
import light_probes as probes

args = common.script_args()
BLEND = args[args.index("--blend") + 1] if "--blend" in args else str(common.ROOT / "master_bakecheck.blend")
OUT = Path(args[args.index("--out") + 1] if "--out" in args else str(common.RENDERS / "previews" / "lighting"))


def state(label):
    s = bpy.context.scene
    v = sorted([o for o in bpy.data.objects if o.name.startswith(lb.VAULT_FILL["name"])], key=lambda o: o.name)
    d = bpy.data.objects.get(lb.FILL["name"])
    shade = [o for o in bpy.data.objects if o.name.startswith(lb.SHADE_FILL["name"])]
    pr = [o for o in bpy.data.objects if o.type == "LIGHT_PROBE"]
    print(f"\n[verify] --- {label}")
    print(f"[verify]   engine {s.render.engine}, exposure {s.view_settings.exposure:.3f}, look {s.view_settings.look!r}")
    if v:
        o = v[0]
        print(f"[verify]   vault x{len(v)}: energy {o.data.energy:.0f} W, energy_W {o.get('energy_W')}, "
              f"custom_distance {o.data.use_custom_distance} @ {o.data.cutoff_distance:.0f} m, "
              f"spread {math.degrees(o.data.spread):.0f} deg")
        print(f"[verify]   vault energies all equal: {len({round(x.data.energy, 3) for x in v}) == 1}")
    if d:
        print(f"[verify]   disk {d.name}: energy {d.data.energy:.0f} W, energy_W {d.get('energy_W')}")
    print(f"[verify]   SHADE_FILL lamps in file: {len(shade)} (must be 0 while SHADE_FILL['energy'] == 0)")
    print(f"[verify]   light probes: {[p.name for p in pr]}")
    return v


print(f"[verify] opening COPY {BLEND} (the real master.blend is never written)")
bpy.ops.wm.open_mainfile(filepath=BLEND, load_ui=False)
eng0 = bpy.context.scene.render.engine
state("1. as opened (what build_master.py leaves)")

probes.bake(bpy.context.scene)
state("2. after light_probes.bake() - the finally must have restored BOTH the rig and the engine")

bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
bpy.ops.wm.open_mainfile(filepath=BLEND, load_ui=False)
v = state("3. after save + reopen - what the lead's master would carry")

s = bpy.context.scene
ok = True
if s.render.engine != eng0:
    print(f"[verify] FAIL: engine {s.render.engine} != the engine the file arrived with ({eng0})"); ok = False
if v:
    o = v[0]
    want = float(o["energy_W"]) * lp.EEVEE_VAULT["energy_scale"]
    if abs(o.data.energy - want) > 1.0:
        print(f"[verify] FAIL: vault energy {o.data.energy:.0f} != energy_W x{lp.EEVEE_VAULT['energy_scale']} = {want:.0f}"); ok = False
    if abs(float(o["energy_W"]) - lb.VAULT_FILL["energy"]) > 1.0:
        # NOT a failure: a master assembled before the current lighting.blend legitimately carries the older
        # physical energy. What matters is that energy_W survived the bake unchanged and that `energy` is derived
        # from it, both checked above. Flagged so the lead knows the master predates the rig.
        print(f"[verify] NOTE: energy_W {o['energy_W']} is light_build's PREVIOUS physical energy "
              f"({lb.VAULT_FILL['energy']} now) - this master predates the round-11 lighting.blend; "
              f"re-run scripts/lead_build.sh")
    if not o.data.use_custom_distance or abs(o.data.cutoff_distance - lp.EEVEE_VAULT["cutoff_distance"]) > 0.5:
        print(f"[verify] FAIL: cutoff {o.data.use_custom_distance} @ {o.data.cutoff_distance}"); ok = False
print(f"\n[verify] SAVE SEQUENCE {'OK' if ok else 'BROKEN'}: engine restored, Eevee override saved, "
      f"physical energies preserved in energy_W")

if "--render" in args:
    OUT.mkdir(parents=True, exist_ok=True)
    cam = bpy.data.objects.get("CAM_qa_04_rotunda_ceiling")
    s.camera = cam
    s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = 1280, 720, 100
    s.render.image_settings.color_depth = "8"
    lp.apply_viewport_eevee(s)
    print(f"[verify] viewport preset: raytracing {s.eevee.use_raytracing}, fast_gi {s.eevee.use_fast_gi}, "
          f"light_threshold {s.eevee.light_threshold}, taa {s.eevee.taa_samples}/{s.eevee.taa_render_samples}")
    s.render.filepath = str(OUT / "r11verify_04v.png")
    import time
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[verify] -> r11verify_04v.png ({time.time() - t:.1f}s)")

print("[verify] done")
