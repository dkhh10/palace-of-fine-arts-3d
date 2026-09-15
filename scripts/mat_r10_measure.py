"""Round-10 acceptance tables (plain python, no Blender).

    python3 scripts/mat_r10_measure.py dome  <frame.png> [<frame.png> ...]
    python3 scripts/mat_r10_measure.py hold  <after.png>
    python3 scripts/mat_r10_measure.py crop  <after.png> <out.png>

`dome` is item A (QA-10-8): the hero box 920 95 1000 120 against the acceptance window lum 205-235, hue 38-50,
sat 0.22-0.32, column-sd >= 8, plus the row split (the box is NOT all dome -- `scripts/mat_r10_probe.py`
ray-casts it as 267 of 400 rays on `ARCH_rotunda_dome` and 133 on `ARCH_rotunda_drum_cornice`, i.e. rows 95-111
dome and rows 112-119 cornice).  The cornice is MAT_concrete_ochre, the hold-listed stone, so a third of every
number in this box is not the dome membrane -- and in ref 169 four of those eight rows are still dome, because
the modelled cap's rim sits about four rows higher than the photograph's.

`hold` is the round-10b hero hold list from docs/briefs/materials_r10.md, measured on the same frame, with the
BEFORE column read off `renders/final/v2/qa_round10b_cam01_cycles.png` rather than quoted.

`crop` writes the 100 % comparison: the render's dome next to ref 169's, from the round-10b aligned sheet whose
panel 1 is ref 169 warped into this exact frame (so the crops are pixel-registered, not eyeballed).
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mat_r7_measure import load, stats, box, columns, BOXES, lum, ROOT

BEFORE = ROOT / "renders" / "final" / "v2" / "qa_round10b_cam01_cycles.png"
ALIGNED10B = ROOT / "renders" / "final" / "v2" / "round10b_cam01_aligned_vs_ref169.png"
DOME_ROWS, CORNICE_ROWS = (95, 112), (112, 120)      # scripts/mat_r10_probe.py: 267 of 400 rays dome,
#                                                     133 drum cornice; the split lands on row 112
WIN = dict(lum=(205.0, 235.0), hue=(38.0, 50.0), sat=(0.22, 0.32), colsd=8.0)
REF_DOME = dict(lum=224.3, hue=44.1, sat=0.272, colsd=6.61)     # aligned sheet panel 1, ref 169


def _dome_row(arr, label):
    x0, y0, x1, y1 = BOXES["dome_cap"]
    c = arr[y0:y1, x0:x1]
    s, g = stats(c), lum(arr[y0:y1, x0:x1])
    cs = g.mean(axis=0).std()
    d = lum(arr[DOME_ROWS[0]:DOME_ROWS[1], x0:x1])
    k = lum(arr[CORNICE_ROWS[0]:CORNICE_ROWS[1], x0:x1])
    ok = lambda v, w: "ok " if w[0] <= v <= w[1] else "FAIL"
    print(f"  {label:26s} lum {s['lum']:6.1f} {ok(s['lum'], WIN['lum'])}  hue {s['hue']:5.1f} {ok(s['hue'], WIN['hue'])}  "
          f"sat {s['sat']:.3f} {ok(s['sat'], WIN['sat'])}  col-sd {cs:5.2f} "
          f"{'ok ' if cs >= WIN['colsd'] else 'FAIL'}   | dome rows {d.mean():6.1f}/{d.mean(axis=0).std():5.2f}  "
          f"cornice rows {k.mean():6.1f}/{k.mean(axis=0).std():5.2f}")
    return s, cs


def dome(paths):
    print(f"[dome cap] box {BOXES['dome_cap']}  window lum {WIN['lum']}, hue {WIN['hue']}, sat {WIN['sat']}, "
          f"col-sd >= {WIN['colsd']}")
    _dome_row(load(str(BEFORE)), "BEFORE round-10b")
    for p in paths:
        _dome_row(load(p), Path(p).stem)
    print(f"  {'REF ref 169 (aligned)':26s} lum {REF_DOME['lum']:6.1f}      hue {REF_DOME['hue']:5.1f}       "
          f"sat {REF_DOME['sat']:.3f}       col-sd {REF_DOME['colsd']:5.2f}")
    r = load(str(ALIGNED10B), panel=1)
    x0, y0, x1, y1 = BOXES["dome_cap"]
    d = lum(r[DOME_ROWS[0]:DOME_ROWS[1], x0:x1])
    k = lum(r[CORNICE_ROWS[0]:CORNICE_ROWS[1], x0:x1])
    print(f"  {'   ref split':26s} dome rows {d.mean():6.1f}/{d.mean(axis=0).std():5.2f}  "
          f"cornice rows {k.mean():6.1f}/{k.mean(axis=0).std():5.2f}")


# the round-10b hold list of docs/briefs/materials_r10.md: name -> (getter, tolerance text)
def hold(after):
    a0, a1 = load(str(BEFORE)), load(after)
    rows = [
        ("sunlit attic", lambda x: box(x, "attic_sunlit"), "186.1 / sat 0.520 / R-B +117"),
        ("shaded attic", lambda x: box(x, "attic_shaded"), "121.3 / 41.3 / 0.633"),
        ("water reflection", lambda x: box(x, "water_refl"), "126.8"),
        ("near water", lambda x: box(x, "near_water_sky"), "123.9 / 205.7"),
        ("vault field", lambda x: stats(x[380:430, 900:1010]), "60.5"),
        ("jamb", lambda x: stats(x[400:480, 872:892]), "hue 24.0"),
        ("columns", columns, "(r10b 114.3 / 39.1 / 0.712)"),
        ("entablature", lambda x: box(x, "entablature"), "(r10b)"),
    ]
    print(f"{'hold box':18s} {'round-10b (before)':>28s} {'round-10 (after)':>28s}   "
          f"delta lum / hue / sat        brief")
    for name, get, txt in rows:
        s0, s1 = get(a0), get(a1)
        f = lambda s: f"{s['lum']:6.1f}/{s['hue']:5.1f}/{s['sat']:.3f}/{s['rb']:+6.1f}"
        flag = "" if (abs(s1['lum'] - s0['lum']) <= 2.0 and abs(s1['hue'] - s0['hue']) <= 2.0
                      and abs(s1['sat'] - s0['sat']) <= 0.02) else "  <-- MOVED"
        print(f"  {name:16s} {f(s0):>28s} {f(s1):>28s}   {s1['lum'] - s0['lum']:+5.1f} / {s1['hue'] - s0['hue']:+5.1f} / "
              f"{s1['sat'] - s0['sat']:+.3f}  {txt}{flag}")


def crop(after, out):
    """100 % (3x nearest) dome crop: before | after | ref 169, pixel-registered on the hero frame."""
    win = (880, 60, 1060, 180)
    panels = [("round-10b", load(str(BEFORE))), ("round-10", load(after)),
              ("ref 169", load(str(ALIGNED10B), panel=1))]
    w, h = (win[2] - win[0]) * 3, (win[3] - win[1]) * 3
    sheet = Image.new("RGB", (w * 3 + 24, h + 18), (18, 18, 18))
    for i, (nm, arr) in enumerate(panels):
        im = Image.fromarray(arr[win[1]:win[3], win[0]:win[2]].astype(np.uint8)).resize((w, h), Image.NEAREST)
        sheet.paste(im, (i * (w + 12), 18))
    from PIL import ImageDraw
    d = ImageDraw.Draw(sheet)
    for i, (nm, _) in enumerate(panels):
        d.text((i * (w + 12) + 4, 4), f"{nm}  crop {win} at 300 %", fill=(235, 235, 235))
    sheet.save(out)
    print(f"[crop] {out}  {sheet.size[0]}x{sheet.size[1]}")


REF083 = Path("/Users/dk/Projects/3d render blender 3rd attempt building/reference/photos/"
              "ornament_crops/coffered_ceiling_1.jpg")


def coffer_crop(before, after, out):
    """100 % coffer crop: cam04 before | after, next to ref 083 scaled to the same height."""
    from PIL import ImageDraw
    ims = []
    for nm, p in (("round-10b cam04", before), ("round-10 cam04", after)):
        im = Image.open(p).convert("RGB")
        w, h = im.size
        ims.append((nm, im.crop((int(w * 0.28), int(h * 0.20), int(w * 0.72), int(h * 0.80)))))
    H = ims[0][1].size[1]
    ref = Image.open(REF083).convert("RGB")
    ref = ref.resize((int(ref.size[0] * H / ref.size[1]), H), Image.LANCZOS)
    ims.append(("ref 083 (coffered_ceiling_1)", ref))
    W = sum(i.size[0] for _, i in ims) + 12 * (len(ims) - 1)
    sheet = Image.new("RGB", (W, H + 18), (18, 18, 18))
    x = 0
    d = ImageDraw.Draw(sheet)
    for nm, im in ims:
        sheet.paste(im, (x, 18))
        d.text((x + 4, 4), nm, fill=(235, 235, 235))
        x += im.size[0] + 12
    sheet.save(out)
    print(f"[coffer crop] {out}  {sheet.size[0]}x{sheet.size[1]}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "dome":
        dome(sys.argv[2:])
    elif cmd == "hold":
        hold(sys.argv[2])
    elif cmd == "crop":
        crop(sys.argv[2], sys.argv[3])
    elif cmd == "coffercrop":
        coffer_crop(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        raise SystemExit(__doc__)
