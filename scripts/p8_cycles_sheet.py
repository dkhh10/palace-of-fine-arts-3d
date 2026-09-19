"""Phase 5 vs Phase 8 Cycles station references: 960 px copies, the 6-row composite, and the numbers.

    python3 scripts/p8_cycles_sheet.py

No Blender, no GPU.  Reads renders/qa_comparisons/cycles_p8/cam0N_1080_32spp.png (this round's references,
rendered by scripts/p8_cycles_refs.py from a scratch copy of master_delivery.blend) against the Phase 5
references the QA rounds have used since round 14 (`qa_r13_probe.REF_R14`: the round-10b Cycles hero and the
round-13 Cycles frames for 2-6), and prints, per station:

  * MAE over the QA-17 / round-10b ARCHITECTURE boxes (`qa_r13_probe.BOXES`, the 9 that sample palace stone -
    the two colonnade-wall boxes are excluded because QA 22 established they sample the BACKDROP through the
    intercolumniation, which is exactly what 8d moved),
  * MAE over the 8d backdrop bands (`qa_r22_probe.BACKDROP`) with each band's luma and saturation,
  * whole-frame MAE.

MAE is mean |ΔRGB| in 0-255 levels; the percentage is of 255.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import qa_r13_probe as P13          # noqa: E402  BOXES + REF_R14
import qa_r22_probe as P22          # noqa: E402  BACKDROP bands

OUT = ROOT / "renders" / "qa_comparisons" / "cycles_p8"
LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
# the two boxes QA 22 showed are backdrop, not architecture (docs/qa_round_22.md section 4)
NOT_ARCH = {"S-colonnade wall", "N-colonnade wall"}


def rgb(p):
    im = Image.open(str(p)).convert("RGB")
    if im.size != (1920, 1080):
        im = im.resize((1920, 1080), Image.LANCZOS)
    return np.asarray(im, dtype=np.float32)


def mae(a, b, box=None):
    if box:
        x0, y0, x1, y1 = box
        a, b = a[y0:y1, x0:x1], b[y0:y1, x0:x1]
    return float(np.abs(a - b).mean())


def stats(a, box):
    x0, y0, x1, y1 = box
    c = a[y0:y1, x0:x1] / 255.0
    lum = c @ LUMA
    mx, mn = c.max(2), c.min(2)
    sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    return float(lum.mean()), float(sat.mean()), float(lum.std())


def main():
    p5 = {st: P13.REF_R14[st][0] for st in range(1, 7)}
    p8 = {st: OUT / f"cam{st:02d}_1080_32spp.png" for st in range(1, 7)}
    missing = [st for st in p8 if not p8[st].exists()]
    if missing:
        raise SystemExit(f"not rendered yet: {missing}")
    (OUT / "960").mkdir(parents=True, exist_ok=True)
    A, B = {}, {}
    print("== Phase 5 reference vs Phase 8 reference (1920x1080, MAE in 0-255 levels) ==")
    for st in range(1, 7):
        A[st], B[st] = rgb(p5[st]), rgb(p8[st])
        Image.open(str(p8[st])).convert("RGB").resize((960, 540), Image.LANCZOS).save(
            OUT / "960" / f"cam{st:02d}_960.jpg", quality=92)
        arch = [(n, b) for (n, s, b, _) in P13.BOXES if s == st and n not in NOT_ARCH]
        line = f"cam{st:02d}  whole frame MAE {mae(A[st], B[st]):6.2f} ({mae(A[st], B[st]) / 2.55:5.2f} %)"
        if arch:
            vals = [mae(A[st], B[st], b) for _, b in arch]
            line += (f"   architecture boxes ({len(arch)}) MAE mean {np.mean(vals):5.2f} "
                     f"({np.mean(vals) / 2.55:4.2f} %) worst {max(vals):5.2f} "
                     f"({[n for (n, _), v in zip(arch, vals) if v == max(vals)][0]})")
        else:
            line += "   no QA-17 architecture box at this station"
        print(line)
        for (n, _), b in zip(arch, [b for _, b in arch]):
            print(f"        {n:20s} MAE {mae(A[st], B[st], b):6.2f} ({mae(A[st], B[st], b) / 2.55:5.2f} %)")
    print("\n== the 8d backdrop bands (qa_r22_probe.BACKDROP): where the two references are meant to differ ==")
    for (name, st, box, note) in P22.BACKDROP:
        l5, s5, d5 = stats(A[st], box)
        l8, s8, d8 = stats(B[st], box)
        print(f"  {name:22s} MAE {mae(A[st], B[st], box):6.2f} ({mae(A[st], B[st], box) / 2.55:5.2f} %)   "
              f"luma {l5:.3f} -> {l8:.3f}   sat {s5:.3f} -> {s8:.3f}   sd {d5:.3f} -> {d8:.3f}")
    # 6-row composite, 960 px wide: Phase 5 | Phase 8
    from PIL import ImageDraw
    CW, CH, LH, PAD = 470, 264, 14, 5
    sheet = Image.new("RGB", (960, PAD + 16 + 6 * (LH + CH + 4)), (20, 20, 22))
    d = ImageDraw.Draw(sheet)
    d.text((PAD, PAD), "Phase 8 Cycles station references (right) against the Phase 5 references QA has used "
                       "since round 14 (left). 1080p, 32 spp fixed, delivery look.", fill=(235, 235, 235))
    y = PAD + 16
    for st in range(1, 7):
        d.text((PAD, y), f"cam{st:02d}   left: {P13.REF_R14[st][1]} ({p5[st].name})   right: Phase 8 "
                         f"(belt r2, 32 spp)", fill=(205, 205, 205))
        y += LH
        for i, arr in enumerate((A[st], B[st])):
            im = Image.fromarray(arr.astype(np.uint8)).resize((CW, CH), Image.LANCZOS)
            sheet.paste(im, (PAD + i * (CW + 10), y))
        y += CH + 4
    sp = OUT / "phase5_vs_phase8_stations_960.jpg"
    sheet.save(sp, quality=92)
    print("\n[p8_sheet] wrote", sp, sheet.size)


if __name__ == "__main__":
    main()
