#!/usr/bin/env python3
"""QA round 16 (Phase 6c, the foliage gate) measurement probe.

No Blender, no Chrome. An EXTENSION of `scripts/qa_r15_probe.py` (which imports `qa_r13_probe`
unchanged): this module only registers the round-16b capture triple and adds what 6c is judged on.

    python3 scripts/qa_r16_probe.py all
    python3 scripts/qa_r16_probe.py foliage16   # the 6c boxes: near tree / far-tree band / shrub-reed
    python3 scripts/qa_r16_probe.py crown       # crown interior-vs-rim contrast (stations 1, 2, 5)
    python3 scripts/qa_r16_probe.py bareurl     # the bare URL against the station-1 preset
    python3 scripts/qa_r16_probe.py perf16      # frame time and resident memory, round 15 -> 16 -> 16b
    python3 scripts/qa_r16_probe.py names       # the export-set name sweep, restated from the manifests
    python3 scripts/qa_r16_probe.py boxes | frame | water | bloom | ...  (round-10b / -14 / -15 boxes)

Columns: `round16b` (post=all, the scored look) | `round16bnopost` (the control) | `round15` (the
previous scored capture) | the reference (Phase 5 hero at station 1, the round-13 compositor-on Cycles
frames at 2-6). Definitions (Rec.709 luma 0-255, mid(5-21), hp9, HSV saturation on the box mean) are
qa_r13_probe's and are not redefined here.

The 6c-specific measures, defined once:
  * `soft`  mean gradient magnitude in the box (a soft canopy is low, a hard alpha cut-out is high);
  * `hard%` share of pixels whose gradient magnitude exceeds 40/255 — the alpha-test signature;
  * `in/rim` crown interior luminance / crown rim luminance, on a foliage mask built per frame
    (G - 0.85R > 5 and B < G, which separates leaf from warm stone and from the sky), eroded by
    `ERODE_IN` px for the interior and by `ERODE_RIM` for the boundary band. A real crown is dark
    inside and lit at the edge (< 1); a flat-shaded blob is ~1.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_r15_probe as P15  # noqa: E402  (registers round 15; imports qa_r13_probe as P)
P = P15.P

P.ROUNDS["16"] = ("round16b_cam%02d.png", "round16bnopost_cam%02d.png", "round15_cam%02d.png",
                  ("post=all", "post=off", "round15"), P.REF_R14)

ERODE_IN, ERODE_RIM = 6, 2


# --------------------------------------------------------------------------- the 6c foliage boxes
# name, station, box, what it is. Stations 1, 2 and 5 are the ones 6c is judged on.
FOLIAGE16 = [
    ("01 near tree band",     1, (660, 545, 1240, 700), "the hero's shore trees, crowns only"),
    ("01 far-tree roofline",  1, (400, 440, 620, 540), "far trees over the north colonnade roof"),
    ("01 shore shrub/reed",   1, (0, 620, 640, 700), "the left shore planting at 100 %"),
    ("01 shore shrub S",      1, (1280, 600, 1900, 690), "the south shore planting"),
    ("02 near trees",         2, (60, 520, 700, 980), "the round-15 box, unchanged"),
    ("02 far tree (fill)",    2, (700, 660, 1240, 950), "the user's finding: the tree that fills cam02"),
    ("02 shrub/reed shore",   2, (40, 860, 640, 1060), "foreground reeds and shrub cards"),
    ("02 reed clump SE",      2, (1380, 880, 1860, 1070), "the orange reed clump at the right bank"),
    ("05 tree crown",         5, (300, 580, 500, 870), "the isolated lawn tree"),
    ("05 tree band",          5, (640, 560, 1280, 860), "the crowns behind the colonnade arch"),
    ("05 shrub/reed shore",   5, (200, 840, 1200, 930), "the shore planting band"),
    ("05 shrub/reed W",       5, (1300, 700, 1900, 900), "the west end of the same band"),
    ("03 shrub cards",        3, (860, 620, 1280, 750), "the same cards at ~8 m in the colonnade walk"),
    ("06 shore planting",     6, (640, 740, 1280, 890), "the aerial's shore band"),
]

# The crown boxes that carry an interior-vs-rim measure (a single crown, not a band).
CROWN = [
    ("01 hero shore crown", 1, (760, 545, 1000, 690)),
    ("02 fill tree crown",  2, (700, 660, 1240, 950)),
    ("05 lawn tree crown",  5, (300, 580, 500, 870)),
]


def _frames():
    return list(zip(P.LABELS, (P.BAKED, P.DIRECT, P.GATE2))) + [("ref", None)]


def _img(st, tmpl):
    return P.rgb((tmpl % st) if tmpl else P.REF[st][0])


def _grad(lum):
    gx = np.zeros_like(lum)
    gy = np.zeros_like(lum)
    gx[:, 1:-1] = (lum[:, 2:] - lum[:, :-2]) * 0.5
    gy[1:-1, :] = (lum[2:, :] - lum[:-2, :]) * 0.5
    return np.hypot(gx, gy)


def _erode(mask, k):
    """Binary erosion by a (2k+1) square, done with shifts so nothing outside numpy is needed."""
    m = mask
    for _ in range(k):
        s = m.copy()
        s[1:, :] &= m[:-1, :]
        s[:-1, :] &= m[1:, :]
        s[:, 1:] &= m[:, :-1]
        s[:, :-1] &= m[:, 1:]
        m = s
    return m


def foliage_mask(crop):
    """Leaf pixels: green-of-warm-stone and not sky."""
    r, g, b = crop[..., 0], crop[..., 1], crop[..., 2]
    return (g - 0.85 * r > 5.0) & (b < g)


def crown_stats(crop):
    """(cover %, interior lum, rim lum, in/rim). Returns None where the mask is too small."""
    m = foliage_mask(crop)
    cover = float(m.mean() * 100.0)
    lum = crop @ P.LUMA
    inner = _erode(m, ERODE_IN)
    rim = m & ~_erode(m, ERODE_RIM)
    if inner.sum() < 200 or rim.sum() < 200:
        return cover, None, None, None
    a, b = float(lum[inner].mean()), float(lum[rim].mean())
    return cover, a, b, a / max(b, 1e-6)


def box_stats(a, box):
    x0, y0, x1, y1 = box
    crop = a[y0:y1, x0:x1]
    r = P.stats(a, box)
    lum = crop @ P.LUMA
    g = _grad(lum)
    r["soft"] = float(g.mean())
    r["hard"] = float((g > 40.0).mean() * 100.0)
    r["ggr"] = float((crop[..., 1] > crop[..., 0]).mean() * 100.0)
    cover, ci, cr, ratio = crown_stats(crop)
    r["cover"] = cover
    r["inrim"] = ratio
    return r


def cmd_foliage16():
    print("== 6c foliage boxes: level / hue / sat / edge softness against the reference ==")
    print(f"{'box':22s} {'frame':10s} {'lum':>7s} {'x ref':>6s} {'hue':>6s} {'sat':>6s} {'G>R%':>6s} "
          f"{'soft':>6s} {'hard%':>6s} {'hp9':>6s} {'leaf%':>6s}")
    for name, st, box, why in FOLIAGE16:
        ref = box_stats(_img(st, None), box)
        for lbl, tmpl in _frames():
            r = ref if lbl == "ref" else box_stats(_img(st, tmpl), box)
            print(f"{name if lbl == P.LABELS[0] else '':22s} {lbl:10s} {r['lum']:7.1f} "
                  f"{r['lum'] / max(ref['lum'], 1e-6):5.2f}x {r['hue']:6.1f} {r['sat']:6.3f} "
                  f"{r['ggr']:5.1f}% {r['soft']:6.2f} {r['hard']:5.2f}% {r['hp9']:6.2f} {r['cover']:5.1f}%")
        print(f"{'':22s} ({why})")


def cmd_crown():
    print("== crown interior vs rim: mean luma of the eroded crown / of its boundary band ==")
    print("   c/e is geometric and needs no mask (central 50 % of the box / the ring around it), so it")
    print("   is the reference-comparable column; in/rim needs the leaf mask, which the reference's much")
    print("   darker crowns partly fail, so read it down the viewer columns only.")
    print(f"{'crown':22s} {'frame':10s} {'leaf%':>6s} {'interior':>9s} {'rim':>7s} {'in/rim':>7s} "
          f"{'c/e':>6s} {'p10':>6s} {'p90':>6s} {'range/mean':>11s}")
    for name, st, box in CROWN:
        for lbl, tmpl in _frames():
            a = _img(st, tmpl)
            x0, y0, x1, y1 = box
            crop = a[y0:y1, x0:x1]
            cover, ci, cr, ratio = crown_stats(crop)
            lum = crop @ P.LUMA
            h, w = lum.shape
            cy, cx = h // 4, w // 4
            centre = lum[cy:h - cy, cx:w - cx]
            ring = lum.sum() - centre.sum()
            ce = centre.mean() / max(ring / max(lum.size - centre.size, 1), 1e-6)
            p10, p90 = float(np.percentile(lum, 10)), float(np.percentile(lum, 90))
            rng = (p90 - p10) / max(lum.mean(), 1e-6)
            f = lambda v, w=7, d=1: (f"{v:{w}.{d}f}" if v is not None else " " * (w - 1) + "-")  # noqa: E731
            print(f"{name if lbl == P.LABELS[0] else '':22s} {lbl:10s} {cover:5.1f}% {f(ci, 9)} "
                  f"{f(cr)} {f(ratio, 7, 3)} {ce:6.3f} {p10:6.1f} {p90:6.1f} {rng:11.3f}")


# --------------------------------------------------------------------------- the bare URL
def cmd_bareurl():
    """The no-query-string boot against the station-1 preset: same look, no dev defaults."""
    a = P.rgb(str(P.VIEW / "round16b_bareurl.png"))
    b = P.rgb(P.BAKED % 1)
    mae = float(np.abs(a - b).mean())
    la, lb = float((a @ P.LUMA).mean()), float((b @ P.LUMA).mean())
    print(f"bare URL  luma {la:.2f}   station-1 preset luma {lb:.2f}   ratio {la / lb:.4f}   MAE {mae:.2f}/255")
    d = json.loads((P.VIEW / "round16b_bareurl.json").read_text())
    print("url:", d.get("url"))
    print("page errors:", len(d.get("pageErrors") or []))
    info = d.get("info") or {}
    for k in ("foliage", "impostors", "lightmaps", "detail", "lighting_mode", "materials_mode"):
        v = info.get(k)
        if isinstance(v, dict):
            print(f"  {k}: " + json.dumps({a_: b_ for a_, b_ in v.items()
                                           if not isinstance(b_, (list, dict))})[:300])
        elif v is not None:
            print(f"  {k}: {str(v)[:200]}")


# --------------------------------------------------------------------------- perf and memory
BUDGET_MB = 1200.0   # the Gate 1 resident budget, docs/briefs/phase6_budget.md


def cmd_perf16():
    print("== frame time (median, 2560x1440) and resident GPU memory ==")
    rows = {}
    for tag in ("round15", "round16", "round16b"):
        p = P.VIEW / f"{tag}_perf.json"
        if p.exists():
            rows[tag] = json.loads(p.read_text())
    tags = list(rows)
    print(f"{'station':34s} " + " ".join(f"{t:>10s}" for t in tags) + "   delta 15->16b")
    n = len(rows[tags[-1]]["stations"])
    for i in range(n):
        name = rows[tags[-1]]["stations"][i]["name"][:32]
        v = [r["stations"][i]["frame_ms"]["median"] for r in rows.values()]
        print(f"{name:34s} " + " ".join(f"{x:9.1f}m" for x in v) + f"   {v[-1] - v[0]:+6.1f} ms")
    print()
    for tag, d in rows.items():
        s = d["stations"][0]["resident"]
        tot = s["texture_bytes"] + s["render_target_bytes"] + s["geometry_bytes"] + s["instance_matrix_bytes"]
        print(f"{tag:10s} resident {tot / 1e6:8.1f} MB  (tex {s['texture_bytes'] / 1e6:7.1f} + rt "
              f"{s['render_target_bytes'] / 1e6:6.1f} + geo "
              f"{(s['geometry_bytes'] + s['instance_matrix_bytes']) / 1e6:6.1f})  "
              f"self-reported total {s['total_bytes'] / 1e6:.1f}  vs budget {tot / 1e6 / BUDGET_MB:.2f}x")
        st = d["stations"][0]
        print(f"{'':10s} draws {st['draw_calls']}  tris {st['triangles'] / 1e6:.2f} M  "
              f"load {d['bytes']['loaded'] / 1e6:.1f} MB in {d['load_s']['total_s']:.2f} s")


# --------------------------------------------------------------------------- the name sweep
PAT = re.compile(r"placeholder|proxy|blocker|fill|occluder|block|dummy|temp|card", re.I)
OBJ = re.compile(r"^(ARCH|ORN|ENV|INST|LIGHT|EXPM|SOCKET)_")


def _strings(o, out):
    if isinstance(o, str):
        out.append(o)
    elif isinstance(o, dict):
        for k, v in o.items():
            out.append(k)
            _strings(v, out)
    elif isinstance(o, list):
        for v in o:
            _strings(v, out)


def cmd_names():
    """CLAUDE.md's object-name sweep, restated over the export set's own manifests (no Blender)."""
    root = Path(__file__).resolve().parent.parent
    hits = {}
    for f in sorted(list((root / "export/out/gate1").glob("*.json"))
                    + list((root / "export/out/gate3").glob("*.json"))):
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        s = []
        _strings(d, s)
        for x in s:
            if len(x) < 90 and PAT.search(x) and OBJ.match(x):
                hits.setdefault(re.sub(r"\d+$", "##", x), set()).add(f.name)
    print("== export-set name sweep (object-shaped names only; field names are not objects) ==")
    if not hits:
        print("no object name matches the pattern")
    for k in sorted(hits):
        print(f"  {k:44s} {sorted(hits[k])}")


if __name__ == "__main__":
    argv = [a for a in sys.argv[1:] if a not in ("--round", "16")]
    P.select_round("16")
    cmd = argv[0] if argv else "all"
    fns = {"frame": P.cmd_frame, "boxes": P.cmd_boxes, "green": P.cmd_green, "band": P.cmd_band,
           "water": P.cmd_water, "mist": P.cmd_mist, "foliage": P.cmd_foliage,
           "bloom": P15.cmd_bloom, "foliage16": cmd_foliage16, "crown": cmd_crown,
           "bareurl": cmd_bareurl, "perf16": cmd_perf16, "names": cmd_names}
    for k, f in (fns.items() if cmd == "all" else [(cmd, fns[cmd])]):
        print(f"\n### {k}")
        f()
