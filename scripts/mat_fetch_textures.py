#!/usr/bin/env python3
"""Download the CC0 Poly Haven texture sets used by the materials library (2K JPG, diffuse/roughness/normal[/ao]).
Run once (network):  python3 scripts/mat_fetch_textures.py [asset ...]
Writes assets/textures/polyhaven/<asset>/<asset>_<map>_2k.jpg and assets/textures/polyhaven/sources.json (URL + license).
Everything on Poly Haven is CC0 1.0 (https://polyhaven.com/license)."""
import json, sys, urllib.request, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "textures" / "polyhaven"
DEFAULT = ["concrete_wall_008", "concrete_wall_007", "concrete_moss", "bark_bluegum", "chinese_cedar_bark", "sandy_gravel", "rock_boulder_dry"]
MAPS = ["Diffuse", "Rough", "nor_gl", "AO", "Displacement"]
RES = "2k"


def fetch(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return
    req = urllib.request.Request(url, headers={"User-Agent": "pfa-materials/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        f.write(r.read())


def main(assets):
    src_path = OUT / "sources.json"
    sources = json.loads(src_path.read_text()) if src_path.exists() else {}
    for a in assets:
        req = urllib.request.Request(f"https://api.polyhaven.com/files/{a}", headers={"User-Agent": "pfa-materials/1.0"})
        info = json.load(urllib.request.urlopen(req, timeout=60))
        entry = {"license": "CC0 1.0", "page": f"https://polyhaven.com/a/{a}", "files": {}}
        for m in MAPS:
            if m not in info:
                continue
            variants = info[m].get(RES, {})
            fmt = "jpg" if "jpg" in variants else next(iter(variants), None)
            if not fmt:
                continue
            url = variants[fmt]["url"]
            dest = OUT / a / Path(url).name
            print(f"[fetch] {a} {m} <- {url}")
            fetch(url, dest)
            entry["files"][m] = str(dest.relative_to(ROOT))
        sources[a] = entry
    src_path.write_text(json.dumps(sources, indent=2))
    total = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file()) / 1e6
    print(f"[fetch] done, {total:.1f} MB under {OUT}")


if __name__ == "__main__":
    main(sys.argv[1:] or DEFAULT)
