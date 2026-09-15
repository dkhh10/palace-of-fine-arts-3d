#!/usr/bin/env python3
"""QA round 12b (Phase 6 Gate 2 re-check) measurement probe — no Blender, no Chrome.

    python3 scripts/qa_r12b_probe.py accept    # the round-12 QA-12-1 acceptance boxes
    python3 scripts/qa_r12b_probe.py control   # sunlit vs sun-less: the material/lighting split
    python3 scripts/qa_r12b_probe.py green     # QA-12b-1: G>R fraction on building crops vs the baked albedo
    python3 scripts/qa_r12b_probe.py shafts    # QA-12-4: shaft-to-shaft coefficient of variation at cam01
    python3 scripts/qa_r12b_probe.py budget    # resident / draws / GPU from renders/web/gate2_perf.json
    python3 scripts/qa_r12b_probe.py all

The band-pass metrics (`mid(5-21)`, `hp9`, `std`) come from `web/tools/qa12_boxes.py`, which is the
definition docs/qa_round_12.md states its numbers in; this script only drives it and adds the three
tests round 12 did not have:

  control  Gate 2 runs `lighting=direct` — full sun + PMREM irradiance, NO shadow, NO bounce, NO AO.
           A box where the sun reaches the surface in BOTH frames therefore compares material to
           material; a box on a face the sun never reaches compares material+shade to material alone.
           Reporting the two side by side is what separates the material share from the lighting share.
  green    Every baked ARCH/ORN albedo is warm ochre (R > G > B on 100 % of its pixels).  So any
           rendered pixel with G > R on a stone surface was produced downstream of the albedo — it is
           the shading path, not the asset.  The fraction is the size of the effect.
  shafts   Per-instance variation: the mean luminance of each colonnade shaft across a horizontal
           strip, and its coefficient of variation.  The Phase 5 spread is mostly tree shadow, so the
           reference number is an upper bound, not a material target.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
BOXTOOL = ROOT / "web/tools/qa12_boxes.py"
VIEWER = str(ROOT / "renders/web/gate2_cam%02d.png")
REF = {
    1: ROOT / "renders/previews/qa/round10b_01_lagoon_hero_cycles.png",
    3: ROOT / "renders/previews/qa/round09_03_colonnade_walk.png",
    5: ROOT / "renders/previews/qa/round09_05_south_lawn.png",
}
LUMA = np.array([0.2126, 0.7152, 0.0722])

# The two acceptance boxes docs/qa_round_12.md set for QA-12-1, in the coordinate system it states
# them in (cam05 at the Phase 5 frame's native 1280x720, cam01 at 1920x1080).
ACCEPT = [
    (5, "1280x720", "787 373 853 453:cam05 pier face", "mid>=7.0, std>=25"),
    (1, "1920x1080", "1600 590 1670 635:cam01 S-colonnade wall", "hp9>=4.0"),
    (1, "1920x1080", "900 222 1020 256:cam01 sunlit attic (hold)", "hue +-1.9 deg, sat >=0.97x"),
]
# Sunlit in both frames (material vs material) | sun-less in the reference (material vs material+shade)
CONTROL = [
    ("sunlit attic", 1, (900, 222, 1020, 256), "sunlit both"),
    ("attic pedestals", 1, (700, 200, 780, 240), "sunlit both"),
    ("dome cap", 1, (900, 90, 1020, 130), "sunlit both"),
    ("whole building", 1, (700, 160, 1240, 480), "mixed"),
    ("columns", 1, (680, 280, 1240, 470), "mixed"),
    ("entablature", 1, (900, 262, 1020, 296), "ref in cornice shadow"),
    ("shaded attic", 1, (1110, 225, 1150, 260), "ref in shade"),
    ("podium band", 1, (820, 520, 1100, 560), "ref in shade"),
    ("colonnade pedestal", 1, (1440, 560, 1560, 620), "ref in deep shade"),
    ("cam05 pier face", 5, (1180, 560, 1280, 680), "ref in shade"),
]
GREEN = [
    ("cam02 building", ROOT / "renders/web/gate2_cam02.png", (560, 90, 1200, 450)),
    ("cam06 rotunda from above", ROOT / "renders/web/gate2_cam06.png", (620, 260, 1260, 620)),
    ("cam05 colonnade base", ROOT / "renders/web/gate2_cam05.png", (500, 380, 1140, 740)),
    ("cam01 building", ROOT / "renders/web/gate2_cam01.png", (700, 160, 1240, 480)),
    ("cam01 building Phase 5 ref", REF[1], (700, 160, 1240, 480)),
]
# The baked albedos, from the bake worktree (the shipped KTX2 have no readable pixels)
ALBEDO = ROOT / ".claude/worktrees/phase6-bake/export/out/gate2/tex"


def rgb(path, size=None):
    im = Image.open(path).convert("RGB")
    if size and im.size != size:
        im = im.resize(size, Image.LANCZOS)
    return np.asarray(im, dtype=np.float64)


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


def boxes(station, at, specs):
    cmd = [sys.executable, str(BOXTOOL), VIEWER % station, "--ref", str(REF[station]), "--at", at]
    for s in specs:
        cmd += ["--box", s]
    subprocess.run(cmd, check=True)


def cmd_accept():
    print("== QA-12-1 acceptance boxes (docs/qa_round_12.md section 6) ==")
    for st, at, spec, target in ACCEPT:
        print(f"-- target {target}")
        boxes(st, at, [spec])


def cmd_control():
    print("== material share vs lighting share: the same metric where the sun does and does not reach ==")
    print(f"{'box':22s} {'lit':22s} {'lum':>12s} {'mid(5-21)':>12s} {'hp9':>10s} {'std':>10s}")
    for name, st, box, lit in CONTROL:
        at = (1920, 1080)
        v, r = rgb(VIEWER % st, at), rgb(REF[st], at)
        x0, y0, x1, y1 = box
        out = []
        for a in (v, r):
            L = a[y0:y1, x0:x1] @ LUMA
            full = a @ LUMA
            out.append((L.mean(), L.std(), band(full, box)))
        (lv, sv, (mv, hv)), (lr, sr, (mr, hr)) = out
        print(f"{name:22s} {lit:22s} {lv / max(lr, 1e-6):11.2f}x {mv / max(mr, 1e-6):11.2f}x "
              f"{hv / max(hr, 1e-6):9.2f}x {sv / max(sr, 1e-6):9.2f}x")
    print("ratios are viewer / Phase 5.  A 'sunlit both' row is a pure material comparison.")


def gaussian(img, sigma):
    r = max(1, int(round(3.0 * sigma)))
    x = np.arange(-r, r + 1, dtype=np.float64)
    k = np.exp(-0.5 * (x / sigma) ** 2)
    k /= k.sum()
    o = np.pad(img, ((0, 0), (r, r)), mode="reflect")
    o = np.apply_along_axis(lambda m: np.convolve(m, k, mode="valid"), 1, o)
    o = np.pad(o, ((r, r), (0, 0)), mode="reflect")
    return np.apply_along_axis(lambda m: np.convolve(m, k, mode="valid"), 0, o)


def band(full, box):
    x0, y0, x1, y1 = box
    mid = gaussian(full, 2.5) - gaussian(full, 10.5)
    hp = full - gaussian(full, 4.5)
    return mid[y0:y1, x0:x1].std(), hp[y0:y1, x0:x1].std()


def cmd_green():
    print("== QA-12b-1: fraction of non-sky pixels with G > R (the baked albedo has none) ==")
    for name, path in (("ORN maiden v1 albedo", ALBEDO / "gate2_ORN__ORN_maiden_v1_LOD0_a_albedo.png"),
                       ("ARCH concrete_ochre albedo", ALBEDO / "gate2_ARCH_rotunda__concrete_ochre_albedo.png")):
        if not path.exists():
            print(f"{name:34s} (not in this checkout: {path})")
            continue
        m = rgb(path).reshape(-1, 3)
        m = m[m.sum(1) > 12]
        print(f"{name:34s} frac(G>R) {(m[:, 1] > m[:, 0]).mean():.3f}   mean RGB {m.mean(0).round(1)}")
    print()
    for name, path, box in GREEN:
        a = rgb(path)
        x0, y0, x1, y1 = box
        m = a[y0:y1, x0:x1].reshape(-1, 3)
        m = m[~(m[:, 2] > m[:, 0] + 25)]          # drop the blue sky
        print(f"{name:34s} frac(G>R) {(m[:, 1] > m[:, 0]).mean():.3f}   mean RGB {m.mean(0).round(1)}")


def cmd_shafts():
    print("== QA-12-4: colonnade shaft-to-shaft variation at cam01 (strip y 600-650) ==")
    v = rgb(VIEWER % 1) @ LUMA
    r = rgb(REF[1], (1920, 1080)) @ LUMA
    for label, img in (("viewer", v), ("Phase 5", r)):
        for side, (x0, x1) in (("south", (1380, 1900)), ("north", (20, 540))):
            prof = img[600:650, x0:x1].mean(0)
            peaks = []
            for i in range(3, len(prof) - 3):
                if prof[i] == max(prof[max(0, i - 5):i + 6]) and (not peaks or i - peaks[-1] >= 8):
                    peaks.append(i)
            val = np.array([img[600:650, x0 + p - 2:x0 + p + 3].mean() for p in peaks])
            print(f"{label:8s} {side:6s} {len(peaks):3d} shafts  mean {val.mean():6.1f}  "
                  f"sd {val.std():5.2f}  CV {val.std() / val.mean():.3f}")
    print("the Phase 5 CV is dominated by tree shadow across the row: an upper bound, not a material target.")


def cmd_budget():
    d = json.loads((ROOT / "renders/web/gate2_perf.json").read_text())
    s = d["stations"][0]["resident"]
    tot = s["texture_bytes"] + s["render_target_bytes"] + s["geometry_bytes"] + s["instance_matrix_bytes"]
    print(f"resident at {d['stations'][0]['size']}: {tot / 1e6:.1f} MB "
          f"(textures {s['texture_bytes'] / 1e6:.1f} + render targets {s['render_target_bytes'] / 1e6:.1f} "
          f"+ geometry {(s['geometry_bytes'] + s['instance_matrix_bytes']) / 1e6:.1f})")
    m = d["materials"]
    print(f"materials {m['matched']}/{m['materials_in_scene']} matched, {m['sets_used']}/{m['sets_in_manifest']} sets used, "
          f"{len(m['failed'])} failures, {len(m['colourspace_conflicts'])} colour-space conflicts, "
          f"without_uv1 {m['without_uv1']}, flat_normal_constant {m['flat_normal_constant']}")
    dt = d["detail"]
    print(f"detail layer: {dt['sets_loaded']} sets on {dt['applied']} materials, {dt['bytes'] / 1e6:.1f} MB, "
          f"strength {dt['strength']} normal {dt['normal_scale']}, empty {dt['empty']}, failed {dt['failed']}")
    print(f"load {d['bytes']['loaded'] / 1e6:.1f} MB in {d['load_s']['total_s']:.2f} s")
    for st in d["stations"]:
        print(f"  {st['name'][:28]:30s} draws {st['draw_calls']:4d}  tris {st['triangles'] / 1e6:.2f} M  "
              f"gpu {st['gpu_cost_ms']['median']:.1f} / {st['gpu_cost_ms']['p95']:.1f} ms")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    fns = {"accept": cmd_accept, "control": cmd_control, "green": cmd_green,
           "shafts": cmd_shafts, "budget": cmd_budget}
    for k, f in (fns.items() if cmd == "all" else [(cmd, fns[cmd])]):
        print(f"\n### {k}")
        f()
