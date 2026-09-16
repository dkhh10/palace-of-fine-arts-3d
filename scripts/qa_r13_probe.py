#!/usr/bin/env python3
"""QA round 13 (Phase 6 Gate 3 lightmaps, before Gate 4 post) measurement probe — no Blender, no Chrome.

    python3 scripts/qa_r13_probe.py boxes    # the round-10b / round-12b acceptance boxes, baked vs direct vs Phase 5
    python3 scripts/qa_r13_probe.py green    # QA-12b-1: G>R fraction on the building crops, baked vs direct vs Phase 5
    python3 scripts/qa_r13_probe.py shafts   # QA-12-4: shaft-to-shaft coefficient of variation at cam01
    python3 scripts/qa_r13_probe.py frame    # whole-frame luma / p10 / p90 per station, baked vs direct vs reference
    python3 scripts/qa_r13_probe.py black    # the bake's "reads black" question: cam04 coffer field, drum band
    python3 scripts/qa_r13_probe.py perf     # resident / draws / GPU from the round13b perf json
    python3 scripts/qa_r13_probe.py all
    python3 scripts/qa_r13_probe.py --round 14 all   # the Gate 4 capture: post=all / post=off / round13b
                                                     # plus band (QA-13-1), foliage, mist, walk

Round 12b's `scripts/qa_r12b_probe.py` compared ONE capture (`lighting=direct`) with the Phase 5 render.
This round has three frames per station — baked, direct and the Phase 5 reference — so every box is
reported as a triple plus the two ratios, which is what "did the lightmap close, halve or leave the
deficit" needs. Definitions are unchanged: Rec.709 luma 0-255, `mid(5-21)` and `hp9` exactly as
`web/tools/qa12_boxes.py` states them, HSV-style saturation (max-min)/max on the box mean.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
VIEW = Path(os.environ.get("PFA_VIEWER_WEB", ROOT / ".claude/worktrees/phase6-viewer/renders/web"))

REF_R13 = {
    1: (ROOT / "renders/previews/qa/round10b_01_lagoon_hero_cycles.png", "Cycles r10b"),
    2: (ROOT / "renders/previews/qa/round09_02_lagoon_ne_threequarter_cycles.png", "Cycles r09"),
    3: (ROOT / "renders/previews/qa/round09_03_colonnade_walk.png", "EEVEE r09"),
    4: (ROOT / "renders/previews/qa/round09_04_rotunda_ceiling_cycles.png", "Cycles r09"),
    5: (ROOT / "renders/previews/qa/round09_05_south_lawn.png", "EEVEE r09"),
    6: (ROOT / "renders/previews/qa/round09_06_aerial_nocomp.png", "Cycles r09 nocomp"),
}
# Round 14: the lead's compositor-on 128 spp Cycles frames for 2-6; the hero keeps the Phase 5 render.
REF_R14 = dict(REF_R13)
for _st, _name in ((2, "02_lagoon_ne_threequarter"), (3, "03_colonnade_walk"), (4, "04_rotunda_ceiling"),
                   (5, "05_south_lawn"), (6, "06_aerial")):
    _p = ROOT / f"renders/previews/qa/round13_{_name}_cycles.png"
    if _p.exists():
        REF_R14[_st] = (_p, "Cycles r13")

# Round 13 compared baked / direct / Gate 2; round 14 compares post=all / post=off / the round-13 baked
# frame, so the same three columns attribute the Gate 4 additions (post, probe, impostors, water).
ROUNDS = {
    "13": ("round13b_cam%02d.png", "round13direct_cam%02d.png", "gate2_cam%02d.png",
           ("baked", "direct", "gate2"), REF_R13),
    "14": ("round14_cam%02d.png", "round14nopost_cam%02d.png", "round13b_cam%02d.png",
           ("post=all", "post=off", "round13b"), REF_R14),
}
BAKED = DIRECT = GATE2 = PERF_JSON = ""
LABELS = ()
REF = {}


def select_round(tag):
    """Point the probe at one capture set. Everything below reads the module globals."""
    global BAKED, DIRECT, GATE2, LABELS, REF, PERF_JSON
    baked, direct, prev, LABELS, REF = ROUNDS[tag]
    BAKED, DIRECT, GATE2 = (str(VIEW / baked), str(VIEW / direct), str(VIEW / prev))
    PERF_JSON = baked.split("_cam")[0] + "_perf.json"


select_round("13")

LUMA = np.array([0.2126, 0.7152, 0.0722])
AT = (1920, 1080)

# name, station, (x0, y0, x1, y1) in the 1920x1080 frame, what the box is for
BOXES = [
    ("hero shade band",   1, (1110, 225, 1150, 260), "r10b shaded attic — the deficit QA-12b attributed to lighting"),
    ("sunlit attic hold", 1, (900, 222, 1020, 256), "must not drift: sat >= 0.94x of Phase 5"),
    ("S-colonnade wall",  1, (1600, 590, 1670, 635), "QA-12b-2 blow-out, mean was 201-221"),
    ("N-colonnade wall",  1, (62, 548, 104, 606), "the same wall on the north run"),
    ("capital row",       1, (1400, 520, 1900, 556), "the south colonnade capitals, per-instance contact shade"),
    ("entablature",       1, (900, 262, 1020, 296), "r10b"),
    ("vault field",       1, (900, 380, 1010, 430), "r10b"),
    ("columns",           1, (680, 280, 1240, 470), "r10b"),
    ("water reflection",  1, (900, 760, 1020, 840), "r10b — Gate 4 water is in this capture"),
    ("cam05 pier face",   5, (1180, 560, 1280, 680), "QA-12-1 acceptance box, r12b control frame"),
    ("cam04 coffer field", 4, (560, 200, 1200, 560), "the bake's 'does it read black' question"),
]


def rgb(path, size=AT):
    im = Image.open(path).convert("RGB")
    if im.size != size:
        im = im.resize(size, Image.LANCZOS)
    return np.asarray(im, dtype=np.float64)


def gaussian(img, sigma):
    r = max(1, int(round(3.0 * sigma)))
    x = np.arange(-r, r + 1, dtype=np.float64)
    k = np.exp(-0.5 * (x / sigma) ** 2)
    k /= k.sum()
    o = np.pad(img, ((0, 0), (r, r)), mode="reflect")
    o = np.apply_along_axis(lambda m: np.convolve(m, k, mode="valid"), 1, o)
    o = np.pad(o, ((r, r), (0, 0)), mode="reflect")
    return np.apply_along_axis(lambda m: np.convolve(m, k, mode="valid"), 0, o)


def hue_sat(mean):
    mx, mn = float(mean.max()), float(mean.min())
    s = 0.0 if mx <= 0 else (mx - mn) / mx
    if mx == mn:
        return 0.0, s
    if mx == mean[0]:
        return (60 * (mean[1] - mean[2]) / (mx - mn)) % 360, s
    if mx == mean[1]:
        return 60 * (mean[2] - mean[0]) / (mx - mn) + 120, s
    return 60 * (mean[0] - mean[1]) / (mx - mn) + 240, s


def stats(a, box):
    x0, y0, x1, y1 = box
    full = a @ LUMA
    mid = gaussian(full, 2.5) - gaussian(full, 10.5)
    hp = full - gaussian(full, 4.5)
    crop = a[y0:y1, x0:x1]
    L = crop @ LUMA
    h, s = hue_sat(crop.reshape(-1, 3).mean(0))
    return {"lum": float(L.mean()), "std": float(L.std()), "hue": h, "sat": s,
            "mid": float(mid[y0:y1, x0:x1].std()), "hp9": float(hp[y0:y1, x0:x1].std()),
            "rb": float((crop[..., 0] - crop[..., 2]).mean())}


def cmd_boxes():
    print("== the acceptance boxes: baked / direct / Phase 5 reference, and the two ratios ==")
    print(f"{'box':19s} {'frame':8s} {'lum':>7s} {'std':>7s} {'hue':>7s} {'sat':>6s} {'mid':>6s} {'hp9':>6s} {'R-B':>7s}")
    cache = {}
    out = {}
    for name, st, box, why in BOXES:
        rows = {}
        for tag, tmpl in (("baked", BAKED), ("direct", DIRECT), ("gate2", GATE2)):
            p = tmpl % st
            if p not in cache:
                cache[p] = rgb(p)
            rows[tag] = stats(cache[p], box)
        rp = REF[st][0]
        if str(rp) not in cache:
            cache[str(rp)] = rgb(rp)
        rows["ref"] = stats(cache[str(rp)], box)
        print(f"-- {name}  (station {st}, {box})  {why}")
        names = dict(zip(("baked", "direct", "gate2"), LABELS))
        for tag in ("baked", "direct", "gate2", "ref"):
            r = rows[tag]
            lbl = names[tag] if tag != "ref" else f"ref/{REF[st][1]}"
            print(f"{'':19s} {lbl:8s} {r['lum']:7.1f} {r['std']:7.2f} {r['hue']:7.1f} {r['sat']:6.3f} "
                  f"{r['mid']:6.2f} {r['hp9']:6.2f} {r['rb']:7.1f}")
        b, d, rf = rows["baked"], rows["direct"], rows["ref"]
        print(f"{'':19s} {'ratios':8s} {LABELS[0]}/ref lum {b['lum'] / max(rf['lum'], 1e-6):.2f}x "
              f"std {b['std'] / max(rf['std'], 1e-6):.2f}x | {LABELS[1]}/ref lum {d['lum'] / max(rf['lum'], 1e-6):.2f}x "
              f"std {d['std'] / max(rf['std'], 1e-6):.2f}x sat {d['sat'] / max(rf['sat'], 1e-6):.2f}x")
        out[name] = rows
    return out


GREEN = [
    ("cam02 building", 2, (560, 90, 1200, 450)),
    ("cam06 rotunda from above", 6, (620, 260, 1260, 620)),
    ("cam05 colonnade base", 5, (500, 380, 1140, 740)),
    ("cam01 building", 1, (700, 160, 1240, 480)),
]


def cmd_green():
    print("== QA-12b-1: fraction of non-sky pixels with G > R (every baked stone albedo has none) ==")
    print(f"{'crop':28s} {LABELS[0]:>9s} {LABELS[1]:>9s} {LABELS[2]:>9s} {'Phase 5':>9s}   mean RGB col1")
    for name, st, box in GREEN:
        vals, mrgb = [], None
        for tmpl in (BAKED, DIRECT, GATE2, None):
            p = (tmpl % st) if tmpl else REF[st][0]
            a = rgb(p)
            x0, y0, x1, y1 = box
            m = a[y0:y1, x0:x1].reshape(-1, 3)
            m = m[~(m[:, 2] > m[:, 0] + 25)]          # drop the blue sky
            vals.append((m[:, 1] > m[:, 0]).mean() * 100)
            if mrgb is None:
                mrgb = m.mean(0).round(1)
        print(f"{name:28s} {vals[0]:8.1f}% {vals[1]:8.1f}% {vals[2]:8.1f}% {vals[3]:8.1f}%   {mrgb}")


def cmd_shafts():
    print("== QA-12-4: colonnade shaft-to-shaft variation at cam01 (strip y 600-650) ==")
    frames = [(LABELS[0], rgb(BAKED % 1) @ LUMA), (LABELS[1], rgb(DIRECT % 1) @ LUMA),
              (LABELS[2], rgb(GATE2 % 1) @ LUMA), ("Phase 5", rgb(REF[1][0]) @ LUMA)]
    for label, img in frames:
        for side, (x0, x1) in (("south", (1380, 1900)), ("north", (20, 540))):
            prof = img[600:650, x0:x1].mean(0)
            peaks = []
            for i in range(3, len(prof) - 3):
                if prof[i] == max(prof[max(0, i - 5):i + 6]) and (not peaks or i - peaks[-1] >= 8):
                    peaks.append(i)
            val = np.array([img[600:650, x0 + p - 2:x0 + p + 3].mean() for p in peaks])
            print(f"{label:9s} {side:6s} {len(peaks):3d} shafts  mean {val.mean():6.1f}  "
                  f"sd {val.std():5.2f}  CV {val.std() / max(val.mean(), 1e-6):.3f}")


def cmd_frame():
    print("== whole-frame luma, p10, p90 per station ==")
    print(f"{'station':9s} {'frame':9s} {'mean':>7s} {'p10':>7s} {'p90':>7s} {'MAE vs ref':>11s}  reference")
    for st in range(1, 7):
        r = rgb(REF[st][0])
        rl = r @ LUMA
        for tag, tmpl in zip(LABELS, (BAKED, DIRECT, GATE2)):
            a = rgb(tmpl % st) @ LUMA
            print(f"cam{st:02d}     {tag:9s} {a.mean():7.2f} {np.percentile(a, 10):7.2f} "
                  f"{np.percentile(a, 90):7.2f} {np.abs(a - rl).mean():11.2f}  {REF[st][1]}")
        print(f"cam{st:02d}     {'ref':9s} {rl.mean():7.2f} {np.percentile(rl, 10):7.2f} "
              f"{np.percentile(rl, 90):7.2f} {0.0:11.2f}  {REF[st][0].name}")


BLACK = [
    ("cam04 coffer field", 4, (560, 200, 1200, 560)),
    ("cam04 coffer soffit", 4, (700, 300, 900, 420)),
    ("cam01 drum band", 1, (860, 150, 1060, 185)),
    ("cam06 drum band", 6, (820, 300, 1060, 340)),
    ("cam01 colonnade roof under", 1, (1400, 556, 1900, 580)),
]


def cmd_black():
    print("== 'reads black where Phase 5 has light': the bake's item-4 surfaces ==")
    print(f"{'crop':28s} {LABELS[0]:>8s} {LABELS[1]:>8s} {LABELS[2]:>8s} {'ref':>8s}  col1/ref")
    for name, st, box in BLACK:
        v = []
        for tmpl in (BAKED, DIRECT, GATE2, None):
            p = (tmpl % st) if tmpl else REF[st][0]
            a = rgb(p)
            x0, y0, x1, y1 = box
            v.append(float((a[y0:y1, x0:x1] @ LUMA).mean()))
        print(f"{name:28s} {v[0]:8.1f} {v[1]:8.1f} {v[2]:8.1f} {v[3]:8.1f}  {v[0] / max(v[3], 1e-6):.2f}x")


# ---------------------------------------------------------------- round 14 additions

# The Gate 4 water at the hero. `refl` is the whole reflected mass, not the round-10b strip;
# `ripple` is a water-only band, and the streaks a real lagoon shows are HORIZONTAL high-frequency
# energy (a mirror has none), so the row/column ratio of the high-pass separates ripple from blur.
WATER = [
    ("refl strip (r10b box)", (900, 760, 1020, 840)),
    ("refl mass", (700, 700, 1300, 950)),
    ("open water", (300, 900, 1600, 1060)),
]


def cmd_water():
    print("== cam01 water: the reflection, the ripple structure and the near-edge Fresnel ==")
    print(f"{'crop':24s} {'frame':10s} {'lum':>7s} {'std':>7s} {'hue':>7s} {'sat':>6s} {'R-B':>7s} "
          f"{'rowHF':>7s} {'colHF':>7s} {'row/col':>8s}")
    for name, box in WATER:
        for lbl, tmpl in list(zip(LABELS, (BAKED, DIRECT, GATE2))) + [("ref", None)]:
            p = (tmpl % 1) if tmpl else REF[1][0]
            a = rgb(p)
            r = stats(a, box)
            x0, y0, x1, y1 = box
            L = a[y0:y1, x0:x1] @ LUMA
            row = float(np.abs(np.diff(L, axis=0)).mean())   # variation across rows -> horizontal streaks
            col = float(np.abs(np.diff(L, axis=1)).mean())
            print(f"{name if lbl == LABELS[0] else '':24s} {lbl:10s} {r['lum']:7.1f} {r['std']:7.2f} "
                  f"{r['hue']:7.1f} {r['sat']:6.3f} {r['rb']:7.1f} {row:7.3f} {col:7.3f} "
                  f"{row / max(col, 1e-6):8.2f}")
    print("\n-- Fresnel: mean luma of 40 px water rows from the far shore to the near edge")
    for lbl, tmpl in list(zip(LABELS, (BAKED, DIRECT, GATE2))) + [("ref", None)]:
        p = (tmpl % 1) if tmpl else REF[1][0]
        L = rgb(p) @ LUMA
        prof = [f"{L[y:y + 40, 700:1300].mean():6.1f}" for y in range(760, 1060, 40)]
        print(f"{lbl:10s} " + " ".join(prof))


# QA-13-1's acceptance band and the surfaces the hero probe was given, per station.
BANDS = [
    ("cam01 N-colonnade band", 1, (20, 520, 540, 645), "QA-13-1: B > R+20 must stay under 3.9 %"),
    ("cam05 behind colonnade", 5, (20, 430, 520, 600), "the same backdrop surface"),
    ("cam06 backdrop", 6, (60, 120, 1860, 300), "the same backdrop surface, aerial"),
]


def cmd_band():
    """The blue-backdrop test: share of pixels with B > R + 20 (Cycles has none)."""
    print("== QA-13-1: % of band pixels with B > R + 20 (sky excluded by luma < 200 & B-R < 80) ==")
    print(f"{'band':26s} {LABELS[0]:>9s} {LABELS[1]:>9s} {LABELS[2]:>9s} {'ref':>9s}   mean RGB col1")
    for name, st, box, why in BANDS:
        x0, y0, x1, y1 = box
        vals, mrgb = [], None
        for tmpl in (BAKED, DIRECT, GATE2, None):
            p = (tmpl % st) if tmpl else REF[st][0]
            c = rgb(p)[y0:y1, x0:x1].reshape(-1, 3)
            vals.append(float((c[:, 2] > c[:, 0] + 20).mean() * 100))
            if mrgb is None:
                mrgb = c.mean(0).round(1)
        print(f"{name:26s} {vals[0]:8.1f}% {vals[1]:8.1f}% {vals[2]:8.1f}% {vals[3]:8.1f}%   {mrgb}  {why}")


# Near foliage: leaf cards, shrubs and reeds. Amber-brown vs Cycles olive-green is the open question.
FOLIAGE = [
    ("cam01 shore planting", 1, (1240, 640, 1700, 760)),
    ("cam02 near trees", 2, (60, 520, 700, 980)),
    ("cam03 foreground foliage", 3, (1300, 600, 1900, 1040)),
    ("cam05 lawn trees", 5, (1300, 200, 1880, 620)),
    ("cam06 shoreline", 6, (200, 700, 1700, 1040)),
]


def cmd_foliage():
    """Foliage hue per station: green foliage is 70-140 deg, amber-brown is 20-50 deg."""
    print("== foliage hue: the green-vegetation share and the median hue of the crop ==")
    print(f"{'crop':26s} {'frame':10s} {'lum':>7s} {'hue':>7s} {'sat':>6s} {'G>R %':>7s} {'hue err':>8s}")
    for name, st, box in FOLIAGE:
        ref = stats(rgb(REF[st][0]), box)
        for lbl, tmpl in list(zip(LABELS, (BAKED, DIRECT, GATE2))) + [("ref", None)]:
            p = (tmpl % st) if tmpl else REF[st][0]
            a = rgb(p)
            r = stats(a, box)
            x0, y0, x1, y1 = box
            c = a[y0:y1, x0:x1].reshape(-1, 3)
            gr = float((c[:, 1] > c[:, 0]).mean() * 100)
            err = "" if lbl == "ref" else f"{r['hue'] - ref['hue']:+8.1f}"
            print(f"{name if lbl == LABELS[0] else '':26s} {lbl:10s} {r['lum']:7.1f} {r['hue']:7.1f} "
                  f"{r['sat']:6.3f} {gr:6.1f}% {err}")


# Airlight: near vs far at the hazy stations. A real airlight lifts the far band's black point
# and pulls its saturation toward the haze colour; a linear fog lifts everything by the same amount.
MIST = [
    ("cam03 near (10-25 m)", 3, (700, 700, 1300, 1000)),
    ("cam03 far (120 m+)", 3, (820, 300, 1180, 430)),
    ("cam06 near (60 m)", 6, (700, 760, 1300, 1000)),
    ("cam06 far (400 m+)", 6, (60, 180, 700, 330)),
]


def cmd_mist():
    print("== airlight: near vs far crops, p10 (the black point the haze lifts) and saturation ==")
    print(f"{'crop':24s} {'frame':10s} {'lum':>7s} {'p10':>7s} {'sat':>6s} {'R-B':>7s}")
    for name, st, box in MIST:
        for lbl, tmpl in list(zip(LABELS, (BAKED, DIRECT, GATE2))) + [("ref", None)]:
            p = (tmpl % st) if tmpl else REF[st][0]
            a = rgb(p)
            r = stats(a, box)
            x0, y0, x1, y1 = box
            L = a[y0:y1, x0:x1] @ LUMA
            print(f"{name if lbl == LABELS[0] else '':24s} {lbl:10s} {r['lum']:7.1f} "
                  f"{np.percentile(L, 10):7.1f} {r['sat']:6.3f} {r['rb']:7.1f}")


def cmd_walk():
    """The walk probe: the ground clamp (minGround vs WATER_Z + 0.1) and the lagoon test."""
    path = VIEW / (PERF_JSON.split("_perf")[0] + "_walk.json")
    if not path.exists():
        print(f"no walk json at {path}")
        return
    probes = json.loads(path.read_text()).get("walkProbes") or []
    water = probes[0]["waterY"] if probes else -1.3
    floor = water + 0.1
    worst = min(probes, key=lambda p: p["minGround"]) if probes else None
    below = [p for p in probes if p["minGround"] < floor]
    print(f"{len(probes)} probes, water {water:.2f} m, clamp floor {floor:.2f} m; "
          f"lowest ground {worst['minGround']:.3f} m at station {worst['station']} heading {worst['headingDeg']}")
    print(f"probes standing below the floor: {len(below)}   "
          f"(a probe below it would have walked into the lagoon)")
    print(f"{'st':>3s} {'hdg':>4s} {'minGround':>10s} {'eyeY':>7s} {'blocked':>8s} {'of':>6s} {'ashore_m':>9s} {'travel_m':>9s}")
    for pr in probes:
        dx = pr["end"]["x"] - pr["start"]["x"]
        dz = pr["end"]["z"] - pr["start"]["z"]
        flag = "" if pr["minGround"] >= floor else "  <-- BELOW THE FLOOR"
        print(f"{pr['station']:3d} {pr['headingDeg']:4d} {pr['minGround']:10.3f} {pr['eyeY']:7.3f} "
              f"{pr['blocked']:8d} {pr['samples']:6d} {pr.get('ashore_m', 0):9.1f} "
              f"{(dx * dx + dz * dz) ** 0.5:9.1f}{flag}")


def cmd_perf():
    d = json.loads((VIEW / PERF_JSON).read_text())
    s = d["stations"][0]["resident"]
    tot = s["texture_bytes"] + s["render_target_bytes"] + s["geometry_bytes"] + s["instance_matrix_bytes"]
    print(f"resident at {d['stations'][0]['size']}: {tot / 1e6:.1f} MB "
          f"(textures {s['texture_bytes'] / 1e6:.1f} + render targets {s['render_target_bytes'] / 1e6:.1f} "
          f"+ geometry {(s['geometry_bytes'] + s['instance_matrix_bytes']) / 1e6:.1f})")
    m = d["materials"]
    print(f"materials {m['matched']}/{m['materials_in_scene']} matched, {m['sets_used']}/{m['sets_in_manifest']} sets, "
          f"{len(m['failed'])} failures, {len(m['colourspace_conflicts'])} colour-space conflicts")
    lm = d.get("lightmaps")
    if lm:
        print("lightmaps: " + json.dumps({k: v for k, v in lm.items() if not isinstance(v, (list, dict))}))
        for k, v in lm.items():
            if isinstance(v, dict):
                print(f"  {k}: " + json.dumps({a: b for a, b in v.items() if not isinstance(b, (list, dict))}))
            elif isinstance(v, list) and v and not isinstance(v[0], (list, dict)):
                print(f"  {k}: {v}")
    print(f"load {d['bytes']['loaded'] / 1e6:.1f} MB in {d['load_s']['total_s']:.2f} s")
    for st in d["stations"]:
        g = st["gpu_cost_ms"]
        fr = st.get("frame_ms", {})
        print(f"  {st['name'][:28]:30s} draws {st['draw_calls']:4d}  tris {st['triangles'] / 1e6:.2f} M  "
              f"gpu {g['median']:.1f}/{g['p95']:.1f} ms  frame {fr.get('median', float('nan')):.1f} ms "
              f"({1000 / max(fr.get('median', 1), 1e-6):.0f} fps)")


if __name__ == "__main__":
    argv = list(sys.argv[1:])
    if "--round" in argv:
        i = argv.index("--round")
        select_round(argv[i + 1])
        del argv[i:i + 2]
    cmd = argv[0] if argv else "all"
    fns = {"boxes": cmd_boxes, "green": cmd_green, "shafts": cmd_shafts, "frame": cmd_frame,
           "black": cmd_black, "band": cmd_band, "foliage": cmd_foliage, "mist": cmd_mist,
           "walk": cmd_walk, "water": cmd_water, "perf": cmd_perf}
    for k, f in (fns.items() if cmd == "all" else [(cmd, fns[cmd])]):
        print(f"\n### {k}")
        f()
