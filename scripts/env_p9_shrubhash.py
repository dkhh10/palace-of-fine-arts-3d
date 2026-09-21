"""Phase 9 ENV / item 2: the shrub-placement hash.

QA 24 item 4 attributed the shrub hard-edge rise (`01 shore shrub S` 2.78 -> 5.95 %, `05 shrub/reed W` 5.73 ->
7.12 %) to belt r2.  The claim in docs/briefs/phase9_env_report.md is that no shrub moved, and this is the script
that measures it -- committed because a number nobody can reproduce is not a measurement (review r1 carry 5).

Hashes `name|x,y,z` (4 decimals, world space) over every ENV_shrub* / ENV_reed* mesh, sorted by name.

    git show 10f9f5f:assets/environment.blend > /tmp/env_prebelt.blend
    scripts/blender_run.sh 600 -- --background --python scripts/env_p9_shrubhash.py -- \\
        /tmp/env_prebelt.blend assets/environment.blend

Prints one line per file; equal counts + equal md5 means no shrub was re-seeded or moved between them.
"""
import hashlib
import sys

import bpy

PREFIXES = ("ENV_shrub", "ENV_reed")


def hash_file(path):
    bpy.ops.wm.open_mainfile(filepath=path)
    rows = []
    for ob in sorted(bpy.data.objects, key=lambda o: o.name):
        if ob.type == "MESH" and ob.name.startswith(PREFIXES):
            t = ob.matrix_world.translation
            rows.append(f"{ob.name}|{t.x:.4f},{t.y:.4f},{t.z:.4f}")
    h = hashlib.md5("\n".join(rows).encode()).hexdigest()
    print(f"[env_p9_shrubhash] {path}: {len(rows)} shrub/reed objects, md5 {h}")
    return len(rows), h


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not args:
        raise SystemExit("usage: ... --python scripts/env_p9_shrubhash.py -- <blend> [<blend> ...]")
    out = [hash_file(p) for p in args]
    if len(out) > 1:
        same = all(o == out[0] for o in out)
        print(f"[env_p9_shrubhash] {'IDENTICAL' if same else 'DIFFERENT'} across {len(out)} files")
