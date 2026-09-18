#!/usr/bin/env python3
"""QA round 18b — re-check `verify_publish`'s claim (1 051 paths, 0 missing) against the live URL.

curl only (HEAD), no Chrome, no Blender. A deterministic sample: every `groups/m_*.glb` (the round-18
blocker), plus 20 paths spread across each manifest by stride, plus the entry points.

    python3 scripts/qa_r18b_live.py            # sample
    python3 scripts/qa_r18b_live.py --all-glb  # every glb named by either plan
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / "export" / "out" / "gate5"
URL = "https://pfa-walkthrough.3d-render-blender-3rd-attempt-building.workers.dev"
BASE = URL + "/assets/gate5/"


def head(url):
    p = subprocess.run(["curl", "-sSI", "--max-time", "30", url],
                       capture_output=True, text=True)
    st, ct, cc, cl = "?", "", "", ""
    for line in p.stdout.splitlines():
        low = line.lower()
        if low.startswith("http/"):
            st = line.split()[1]
        elif low.startswith("content-type:"):
            ct = line.split(":", 1)[1].strip()
        elif low.startswith("cache-control:"):
            cc = line.split(":", 1)[1].strip()
        elif low.startswith("content-length:"):
            cl = line.split(":", 1)[1].strip()
    return st, ct, cc, cl


def sample(paths, n):
    paths = sorted(set(paths))
    if len(paths) <= n:
        return paths
    stride = len(paths) / n
    return [paths[int(i * stride)] for i in range(n)]


def main():
    desk = json.loads((EXPORT / "manifest.json").read_text())["files"]
    mob = json.loads((EXPORT / "manifest_mobile.json").read_text())["files"]
    dpaths = [f["path"] for f in desk]
    mpaths = [f["path"] for f in mob]
    groups_m = [p for p in set(dpaths) | set(mpaths) if p.startswith("groups/m_")]
    if "--all-glb" in sys.argv:
        pick = sorted({p for p in set(dpaths) | set(mpaths) if p.endswith(".glb")})
        label = "every glb in either plan"
    else:
        pick = sorted(set(groups_m) | set(sample(dpaths, 20)) | set(sample(mpaths, 20)))
        label = f"{len(groups_m)} m_* group(s) + 20 desktop + 20 mobile by stride"
    print(f"== live HEAD on {URL}  ({label}) ==")
    bad = 0
    sizes = {f["path"]: f.get("bytes") for f in desk + mob}
    for p in pick:
        st, ct, cc, cl = head(BASE + p)
        tag = "m_*" if p.startswith("groups/m_") else ""
        want = sizes.get(p)
        size_ok = "" if (want in (None, "") or cl in ("", str(want))) else f"SIZE {cl} != plan {want}"
        if st != "200" or size_ok:
            bad += 1
        print(f"  {st:>3s} {p:44s} {ct:28s} {cc:40s} {cl:>10s} {tag} {size_ok}")
    for p in ("", "index.html", "assets/gate5/manifest.json", "assets/gate5/manifest_mobile.json",
              "assets/gate5/uv2_relay_status.json"):
        st, ct, cc, cl = head(URL + "/" + p)
        print(f"  {st:>3s} /{p:43s} {ct:28s} {cc:40s} {cl:>10s}")
    print(f"-- {len(pick)} sampled path(s), {bad} not 200 / wrong size; "
          f"plans name {len(set(dpaths))} desktop + {len(set(mpaths))} mobile "
          f"= {len(set(dpaths) | set(mpaths))} distinct")


if __name__ == "__main__":
    main()
