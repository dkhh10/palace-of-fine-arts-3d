"""QA name sweep (lead, 2026-09-10; CLAUDE.md "Gate checks added 2026-09-10"). Lists every render-visible object of master.blend whose
name matches the placeholder pattern, with collection and world position, and the exceptions on record. Exit 1 if any non-exempt hit.

    scripts/blender_run.sh 300 -- --background master.blend --python scripts/qa_name_sweep.py
"""
import bpy, re, sys
PAT = re.compile(r"placeholder|proxy|blocker|fill|occlud|block|dummy|temp|card|board|impostor|billboard", re.I)
EXEMPT = re.compile(r"^(ARCH_rotunda_inner_block(_cap)?_\d+|ENV_backdrop_fill(roof)?_\d+|ENV_treeboard_\d+)$")  # ENV_treeboard_*: Gate 3 impostor carriers, hidden in every QA capture until the impostor bake (QA 11b)
hits, exempt = [], []
for ob in bpy.context.scene.objects:
    if ob.hide_render or not PAT.search(ob.name):
        continue
    coll = ob.users_collection[0].name if ob.users_collection else "-"
    row = f"{ob.name:48s} {coll:28s} {ob.type:6s} {tuple(round(v, 1) for v in ob.matrix_world.translation)}"
    (exempt if EXEMPT.match(ob.name) else hits).append(row)
print(f"[qa_name_sweep] {len(exempt)} exempt (on record in docs/quality_checklist.md), {len(hits)} to explain:")
for r in hits:
    print("   HIT", r)
print("[qa_name_sweep] " + ("PASS" if not hits else "FAIL"))
sys.exit(0 if not hits else 1)
