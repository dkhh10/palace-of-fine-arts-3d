#!/usr/bin/env python3
"""QA round 15 (Phase 6 Gate 4, round two — the bounded polish round) measurement probe.

No Blender, no Chrome. An EXTENSION of `scripts/qa_r13_probe.py`, which is imported unchanged:
this module only registers the round-15 capture triple and adds the measurements round 15 needs.

    python3 scripts/qa_r15_probe.py all        # every command below
    python3 scripts/qa_r15_probe.py water      # QA-14-1: ripple, level, hue, Fresnel
    python3 scripts/qa_r15_probe.py boxes | green | shafts | frame | black | band | foliage | mist | walk | perf
    python3 scripts/qa_r15_probe.py bloom      # QA-14-4: the acceptance numbers of the round-6 brief
    python3 scripts/qa_r15_probe.py loading    # the loading-screen denominator, from the capture sidecars
    python3 scripts/qa_r15_probe.py delta      # QA-14-1..5 side by side, round 14 -> round 15

Columns everywhere: `round15` (post=all, the scored look) | `round15nopost` (the control) | `round14`
(the previous scored capture) | the reference (Phase 5 hero at station 1, the round-13 compositor-on
Cycles frames at 2-6). Definitions (Rec.709 luma 0-255, mid(5-21), hp9, HSV saturation on the box mean)
are qa_r13_probe's and are not redefined here.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_r13_probe as P  # noqa: E402  (the round-13/14 probe, imported unchanged)

P.ROUNDS["15"] = ("round15_cam%02d.png", "round15nopost_cam%02d.png", "round14_cam%02d.png",
                  ("post=all", "post=off", "round14"), P.REF_R14)


def _frames():
    """(label, path-template or None for the reference) in the fixed column order."""
    return list(zip(P.LABELS, (P.BAKED, P.DIRECT, P.GATE2))) + [("ref", None)]


def _img(st, tmpl):
    return P.rgb((tmpl % st) if tmpl else P.REF[st][0])


# --------------------------------------------------------------------------- QA-14-4, bloom
# The round-6 brief's acceptance: capital-row std >= 0.85x of Cycles, S-colonnade mid >= 0.7x,
# sunlit-attic sat hold >= 0.89x, and the dome-cap halo gone (sky just outside the cap silhouette).
BLOOM = [
    ("capital row std", 1, (1400, 520, 1900, 556), "std", 0.85),
    ("S-colonnade mid", 1, (1600, 590, 1670, 635), "mid", 0.70),
    ("sunlit attic sat", 1, (900, 222, 1020, 256), "sat", 0.89),
    ("vault field lum", 1, (900, 380, 1010, 430), "lum", None),
    ("hero shade band lum", 1, (1110, 225, 1150, 260), "lum", None),
]
# A ring of sky immediately outside the dome cap: bloom spills into it and nothing else does.
HALO = ("dome-cap sky halo", 1, (820, 60, 1100, 120))


def cmd_bloom():
    print("== QA-14-4: the round-6 bloom acceptance boxes (ratio = post=all / reference) ==")
    print(f"{'box':22s} {'metric':6s} {'post=all':>9s} {'post=off':>9s} {'round14':>9s} {'ref':>9s} "
          f"{'ratio':>7s} {'gate':>6s}  verdict")
    for name, st, box, metric, gate in BLOOM:
        v = {}
        for lbl, tmpl in _frames():
            v[lbl] = P.stats(_img(st, tmpl), box)[metric]
        ratio = v["ref"] and v[P.LABELS[0]] / v["ref"]
        ok = "" if gate is None else ("PASS" if ratio >= gate else "FAIL")
        print(f"{name:22s} {metric:6s} {v[P.LABELS[0]]:9.3f} {v[P.LABELS[1]]:9.3f} {v[P.LABELS[2]]:9.3f} "
              f"{v['ref']:9.3f} {ratio:6.2f}x {('%.2f' % gate) if gate else '   - ':>6s}  {ok}")
    name, st, box = HALO
    print(f"\n-- {name} {box}: bloom spill into the sky beside the dome (post-on minus post-off)")
    for lbl, tmpl in _frames():
        a = _img(st, tmpl)
        r = P.stats(a, box)
        print(f"   {lbl:10s} lum {r['lum']:7.2f}  std {r['std']:6.2f}  p99 "
              f"{np.percentile(a[box[1]:box[3], box[0]:box[2]] @ P.LUMA, 99):7.2f}")


# --------------------------------------------------------------------------- the loading screen
def cmd_loading():
    """The bar's denominator against what the page actually fetched."""
    for tag in ("round15", "round14"):
        for suffix in ("_loading.json", "_perf.json", "_cam.json"):
            p = P.VIEW / (tag + suffix)
            if not p.exists():
                continue
            d = json.loads(p.read_text())
            b = d.get("bytes") or (d.get("stations") or [{}])[0].get("bytes") or {}
            if not b:
                continue
            planned = b.get("planned") or b.get("plan") or b.get("total")
            loaded = b.get("loaded")
            off = b.get("offPlan")
            offn = len(off) if isinstance(off, (list, dict)) else off
            print(f"{tag + suffix:26s} planned {planned} loaded {loaded} offPlan {offn} "
                  f"denominator {b.get('denominator', '-')}")
            if planned and loaded:
                print(f"{'':26s} bar reaches {100.0 * loaded / planned:6.1f} % of its denominator")
            break


# --------------------------------------------------------------------------- QA-14-1..5 delta
QA14 = {
    "QA-14-1 water": ("water", "ripple / level / hue / Fresnel at the hero"),
    "QA-14-2 cam03": ("mist", "cam03 near p10 39.8 vs 7.3, frame 1.67x"),
    "QA-14-3 cam06": ("mist", "cam06 near 0.53x, p10 9.7 vs 65.6, far sat 3.7x"),
    "QA-14-4 bloom": ("bloom", "capital std 0.69x, S-col mid 0.40x, attic sat 0.80x"),
    "QA-14-5 foliage": ("foliage", "cam02 near trees hue -45.9 deg, black alpha gaps"),
}


def cmd_delta():
    print("== QA-14-1..5: the boxes each item is judged on, round 14 -> round 15 ==")
    for item, (cmd, why) in QA14.items():
        print(f"\n--- {item}: {why}  (see `{cmd}`)")
    print("\n(run the named command for the numbers; this is the index the report table follows)")


if __name__ == "__main__":
    argv = [a for a in sys.argv[1:] if a not in ("--round", "15")]
    P.select_round("15")
    cmd = argv[0] if argv else "all"
    fns = {"boxes": P.cmd_boxes, "green": P.cmd_green, "shafts": P.cmd_shafts, "frame": P.cmd_frame,
           "black": P.cmd_black, "band": P.cmd_band, "foliage": P.cmd_foliage, "mist": P.cmd_mist,
           "walk": P.cmd_walk, "water": P.cmd_water, "perf": P.cmd_perf,
           "bloom": cmd_bloom, "loading": cmd_loading, "delta": cmd_delta}
    for k, f in (fns.items() if cmd == "all" else [(cmd, fns[cmd])]):
        print(f"\n### {k}")
        f()
