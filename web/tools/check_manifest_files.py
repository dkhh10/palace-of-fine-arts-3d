#!/usr/bin/env python3
"""Does every file this manifest references exist on disk?  Run before a capture.

    python3 web/tools/check_manifest_files.py [manifest.json]      # default:
                                                   #   $PFA_MAIN_ROOT/export/out/gate2/manifest.json

Resolves the glbs, the sky, the LUT and every `materials.sets[*].<map>.texture` key (through
textures.gate2.files + ktx2_dir, then the Gate 1 textures.files list) against the manifest's own
directory and reports what is missing, with the total bytes of what is there.  Exit 1 if anything is
missing, so a gate script can refuse to capture a half-baked set.
"""
import json, os, sys
from pathlib import Path

MAPS = ("albedo", "roughness", "normal", "metallic", "occlusion")


def default_manifest():
    """$PFA_MAIN_ROOT/export/out/gate2/manifest.json, else the repo this file lives in."""
    root = os.environ.get("PFA_MAIN_ROOT") or Path(__file__).resolve().parents[2]
    return Path(root) / "export/out/gate2/manifest.json"


def main(argv):
    mp = Path(argv[1]) if len(argv) > 1 else default_manifest()
    m = json.loads(mp.read_text())
    base = mp.parent
    want, missing, total = [], [], 0

    def add(rel, what):
        if not rel:
            return
        want.append((os.path.normpath(base / rel), what))

    for cls, g in (m.get("glb", {}).get("per_class") or {}).items():
        add(g.get("path"), f"glb:{cls}")
    for k in ("camera", "glossy"):
        v = (m.get("sky") or {}).get(k) or {}
        add(v.get("hdr") if isinstance(v, dict) else v, f"sky.{k}")
    add((m.get("lut") or {}).get("path"), "lut")

    tex = m.get("textures") or {}
    g2 = tex.get("gate2") or {}
    files2, dir2 = g2.get("files") or {}, g2.get("ktx2_dir") or ""
    files1, dir1 = tex.get("files") or [], tex.get("ktx2_dir") or ""
    n_const = 0
    for name, s in ((m.get("materials") or {}).get("sets") or {}).items():
        if s.get("uv1_in_glb") is False:
            continue
        for slot in MAPS:
            e = s.get(slot)
            if not isinstance(e, dict):
                continue
            key = e.get("texture")
            if not key:
                n_const += 1
                continue
            if key in files2:
                add(os.path.join(dir2, files2[key].get("path") or f"{key}.ktx2"), f"{name}.{slot}")
            else:
                hit = next((f for f in files1 if f in (key, key + ".ktx2") or f.startswith(key + ".")), None)
                if hit:
                    add(os.path.join(dir1, hit), f"{name}.{slot}")
                else:
                    missing.append((key, f"{name}.{slot} (key in no index)"))

    seen = set()
    for p, what in want:
        if p in seen:
            continue
        seen.add(p)
        if os.path.exists(p):
            total += os.path.getsize(p)
        else:
            missing.append((p, what))
    print(f"{mp}: {len(seen)} referenced files, {len(seen) - len(missing)} present, "
          f"{total / 1e6:.1f} MB, {n_const} constant maps with no file")
    for p, what in missing[:20]:
        print(f"  MISSING {what}: {p}")
    if len(missing) > 20:
        print(f"  … and {len(missing) - 20} more")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
