"""Phase 10 r1 (final review #3) -- the land gate on the registered camera stations (numpy, no bpy).

    .venv-p10/bin/python scripts/mat_p10_gates.py      # -> cameras.json `usable_land` + evidence/camera_gates.json

A photographer stands on land: reject a camera whose centre lies inside the OSM lagoon polygons
(reference/plans/site_local.json lagoon*, converted with common.osm_to_world's rule (x_east, y_north) -> (-y_north,
x_east)) or more than 10 m behind the east shore, i.e. farther from the rotunda axis than the lagoon's farthest boundary
crossing on the camera's own bearing + 10 m.  Bearings that never cross the lagoon are not judged by the shore rule.
"""
import json, math
import numpy as np
from pathlib import Path
import mat_p10_common as C

SITE = Path("/Users/dk/Projects/3d render blender 3rd attempt building/reference/plans/site_local.json")
BEHIND = 10.0


def rings():
    d = json.loads(SITE.read_text())
    out = []
    for k in [k for k in d if k.startswith("lagoon")]:
        v = d[k]
        rs = v if isinstance(v[0][0], (list, tuple)) else [v]
        for r in rs:
            a = np.array(r, float)
            out.append(np.stack([-a[:, 1], a[:, 0]], 1))          # osm_to_world
    return out


def inside(p, poly):
    x, y = p; n = len(poly); c = False
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def far_crossing(p, polys):
    d = p / np.linalg.norm(p); best = None
    for poly in polys:
        a, b = poly, np.roll(poly, -1, 0)
        e = b - a
        den = d[0] * (-e[:, 1]) - d[1] * (-e[:, 0])
        ok = np.abs(den) > 1e-12
        t = np.where(ok, (a[:, 0] * (-e[:, 1]) - a[:, 1] * (-e[:, 0])) / np.where(ok, den, 1), -1)
        s = np.where(ok, (d[0] * a[:, 1] - d[1] * a[:, 0]) / np.where(ok, den, 1), -1)
        hit = ok & (t > 0) & (s >= 0) & (s <= 1)
        if hit.any():
            best = max(best or 0.0, float(t[hit].max()))
    return best


if __name__ == "__main__":
    polys = rings()
    P = C.P2 / "cameras.json"
    J = json.loads(P.read_text())
    rows = []
    for c in J["cameras"]:
        xy = np.array(c["centre"][:2]); r = float(np.linalg.norm(xy))
        inl = any(inside(xy, p) for p in polys)
        shore = far_crossing(xy, polys)
        behind = shore is not None and r > shore + BEHIND
        c["usable_land"] = not (inl or behind)
        rp = c.get("residual_px"); used = (c["usable_physical"] and rp is not None and rp <= 6 and c.get("refine_rot_deg", 0) <= 1.5)
        rows.append(dict(file=c["file"], r=round(r, 1), z=round(c["centre"][2], 2), in_lagoon=inl,
                         shore_r=None if shore is None else round(shore, 1), behind_shore=behind,
                         used_before=bool(used), usable_land=c["usable_land"]))
    P.write_text(json.dumps(J, indent=1))
    used = [x for x in rows if x["used_before"]]
    drop = [x for x in used if not x["usable_land"]]
    summ = dict(cameras=len(rows), in_lagoon=sum(x["in_lagoon"] for x in rows), behind_shore=sum(x["behind_shore"] for x in rows),
                used_before=len(used), dropped_from_used=len(drop), used_after=len(used) - len(drop),
                dropped=[(x["file"][:7], x["r"], x["shore_r"], "lagoon" if x["in_lagoon"] else "behind") for x in drop])
    (C.P2 / "evidence").mkdir(exist_ok=True)
    (C.P2 / "evidence" / "camera_gates.json").write_text(json.dumps(dict(summary=summ, cameras=rows), indent=1))
    print(json.dumps(summ))
