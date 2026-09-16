#!/usr/bin/env python3
"""The cam01 acceptance boxes of docs/qa_round_10b.md, measured on any set of viewer frames.

    python3 web/tools/hero_boxes.py A.png [B.png ...] [--ref R.png] [--labels a,b] [--json out.json]

Every frame is resampled to 1920x1080 (the boxes' own coordinate frame: the round-10b hero) and each
box reports the four numbers the QA report states -- Rec.709 luma 0-255, its standard deviation, HSV
saturation and the R-B difference -- so a viewer frame can be put next to the Phase 5 Cycles hero
without re-deriving anyone's definitions.  --ref defaults to the round-10b Cycles hero, which is the
PARITY target for Phase 6 (the photograph is the rubric target and lives in the QA report).

The point of several positional frames is the on/off table the Gate 4 brief asks for: capture the
same station with one feature switched and pass both files, and every box comes out as a ratio
against the reference, so QA can attribute a change to the feature that caused it.
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
from PIL import Image

MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
DEFAULT_REF = MAIN / "renders/previews/qa/round10b_01_lagoon_hero_cycles.png"
AT = (1920, 1080)

# docs/qa_round_10b.md "Item 3b - the acceptance boxes", in the 1920x1080 hero frame.
BOXES = [
    ("vault field",      900, 380, 1010, 430),
    ("jamb",             872, 400,  892, 480),
    ("shaded attic",    1110, 225, 1150, 260),
    ("sunlit attic",     900, 222, 1020, 256),
    ("sky top",         1210,  22, 1690,  76),
    ("water reflection", 900, 760, 1020, 840),
    ("entablature",      900, 262, 1020, 296),
    ("columns",          680, 280, 1240, 470),
]

LUMA = np.array([0.2126, 0.7152, 0.0722])


def load(path):
    im = Image.open(path).convert("RGB")
    if im.size != AT:
        im = im.resize(AT, Image.LANCZOS)
    return np.asarray(im, dtype=np.float64)


def metrics(rgb, box):
    _, x0, y0, x1, y1 = box
    a = rgb[y0:y1, x0:x1]
    lum = a @ LUMA
    mx, mn = a.max(axis=2), a.min(axis=2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    return {
        "lum": float(lum.mean()),
        "std": float(lum.std()),
        "sat": float(sat.mean()),
        "rb": float((a[..., 0] - a[..., 2]).mean()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frames", nargs="+")
    ap.add_argument("--ref", default=str(DEFAULT_REF))
    ap.add_argument("--labels", default=None, help="comma-separated names for the frames")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    labels = a.labels.split(",") if a.labels else [Path(f).stem for f in a.frames]
    if len(labels) != len(a.frames):
        sys.exit("hero_boxes.py: --labels must have one name per frame")
    ref = load(a.ref) if Path(a.ref).exists() else None
    frames = [load(f) for f in a.frames]

    out = {"ref": a.ref, "at": list(AT), "frames": {}, "boxes": {}}
    print(f"reference: {a.ref}" if ref is not None else "reference: MISSING")
    head = f"{'box':18s} {'metric':6s}" + "".join(f"{l[:14]:>15s}" for l in labels) + f"{'ref':>10s}"
    print(head)
    print("-" * len(head))
    for box in BOXES:
        name = box[0]
        rm = metrics(ref, box) if ref is not None else None
        out["boxes"][name] = {"ref": rm, "frames": {}}
        for k in ("lum", "std", "sat", "rb"):
            row = f"{name if k == 'lum' else '':18s} {k:6s}"
            for l, f in zip(labels, frames):
                m = metrics(f, box)
                out["boxes"][name]["frames"].setdefault(l, {}).update({k: m[k]})
                ratio = f" ({m[k] / rm[k]:.2f}x)" if rm and abs(rm[k]) > 1e-6 else ""
                row += f"{m[k]:8.2f}{ratio:>7s}"
            row += f"{rm[k]:10.2f}" if rm else " " * 10
            print(row)
        print()

    # the whole-frame luma, which is the number the Gate 4 step-0 finding is quoted in
    print(f"{'WHOLE FRAME':18s} {'lum':6s}" + "".join(f"{(f @ LUMA).mean():8.2f}{'':7s}" for f in frames)
          + (f"{(ref @ LUMA).mean():10.2f}" if ref is not None else ""))
    for l, f in zip(labels, frames):
        out["frames"][l] = {"mean_luma": float((f @ LUMA).mean())}
    if ref is not None:
        out["frames"]["__ref__"] = {"mean_luma": float((ref @ LUMA).mean())}
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1))
        print(f"\nwrote {a.json}")


if __name__ == "__main__":
    main()
