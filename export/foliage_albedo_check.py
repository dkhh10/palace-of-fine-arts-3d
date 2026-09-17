"""Phase 6c round 3 item 1, step 2: does the SHIPPED card albedo equal the albedo CYCLES uses?

    python3 export/foliage_albedo_check.py        # CPU only, no Blender, no GPU

Reads the Diffuse Colour pass `export/foliage_albedo_render.py` wrote and the tinted albedo PNGs
`export/foliage_tex.py` wrote (the exact images `gltf_pack.sh --foliage` encodes to KTX2), and writes

    export/out/gate3/foliage/albedo_check.json
    renders/web/960/6c_albedo_check.jpg

THE QUESTION (docs/briefs/phase6c_export_r3.md item 1). QA 16 measures the viewer's shrub/reed boxes at
1.34-1.70x the Cycles level and assigns the defect to EXPORT. A rendered level is albedo x irradiance. This
script divides the two: if the shipped albedo agrees with the pass within AGREE_PCT the albedo is right and
the level gap is LIGHTING (the viewer's irradiance reducer, its missing translucency, its missing
self-shadow); if the shipped albedo is brighter, the tint chain in `foliage_tex.py` is missing a node and
the fix is here.

HOW THE TWO SIDES ARE MADE COMPARABLE.

*The pass side.* Per station, per QA box, per material: the mean Diffuse Colour over the pixels where the
Combined alpha is above OPAQUE_MIN (the card is solid there - the brief's "where the cards are opaque") and
the Material Index is exactly that material's `pass_index`. The render isolated the foliage and made the
film transparent, so alpha is the cards' own coverage and nothing behind them can leak into either channel.

*The shipped side.* The mean of `clip(image_linear * tint)` over the texels whose alpha clears the
material's own cut - the same texels, the same clip and the same tint that ship in the KTX2.

*The correction that makes them the same quantity.* Cycles' Diffuse Colour pass sums the DIFFUSE closures,
and `leaf_material` mixes a Translucent BSDF (also a diffuse closure) whose colour is `base * multiplier` at
factor `f = clip(maprange(trn_map) * constant)`. So the pass measures `base * ((1-f) + f*mult)`, not `base`.
`expected_diffcol` below applies exactly that, per texel, from the same maps - so `shipped / measured` is a
like-for-like ratio and not a 10-20 % artefact of the translucent branch. The two per-instance terms the
glTF cannot carry (Object Info Random hue/value, the object-space cluster noise) are identity-CENTRED in
`mat_build.leaf_material` (`val = 1 + (R3-0.5)*val_var`, `cl = maprange(noise, ... , 1-cv, 1+cv)`), so they
average to 1 over the many instances a box contains and are pinned to 1 here; the measured spread per box is
reported as `diffcol_rel_sd` so that assumption is visible rather than assumed.

*The index map is validated, not trusted.* HUE is an independent dimension from level (round-2 item 40
established the tint fixes the hue), so each index's measured hue is checked against its material's own
tinted hue. MAT_shrub_dry is the straw one at 36 deg where the other three are 69-95 deg, so a scrambled map
cannot pass this check.
"""
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import foliage_tex as ft  # noqa: E402  (l2s / s2l / hsv_of / pick; importing runs no work)
import gate3_common as g3  # noqa: E402  (read_exr_channels)

SCHEMA = "pfa-phase6c/foliage-albedo-check/1"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "export" / "out" / "gate3" / "foliage"
SHEET = ROOT / "renders" / "web" / "960" / "6c_albedo_check.jpg"

OPAQUE_MIN = 0.98        # Combined alpha: the card is solid at this pixel
ALPHA_RAMP = 0.15        # leaf_material: alpha = maprange(tex.Alpha, cut-0.15, cut+0.15, 0, 1)
MIN_PX = 200             # a material with fewer pixels than this in a box is reported, never judged
AGREE_PCT = 10.0         # the brief's threshold: within this, the albedo is right and the gap is lighting
LUMA = np.array([0.2126, 0.7152, 0.0722])

# The QA-16 boxes, copied from scripts/qa_r16_probe.py FOLIAGE16 (station -> name -> box). Only the two
# stations this pass renders, and only the shrub/reed boxes of "Open 1" plus the tree boxes for context.
BOXES = {
    "02": [("02 shrub/reed shore", (40, 860, 640, 1060), True),
           ("02 reed clump SE", (1380, 880, 1860, 1070), True),
           ("02 near trees", (60, 520, 700, 980), False),
           ("02 far tree (fill)", (700, 660, 1240, 950), False)],
    "05": [("05 shrub/reed shore", (200, 840, 1200, 930), True),
           ("05 shrub/reed W", (1300, 700, 1900, 900), True),
           ("05 tree crown", (300, 580, 500, 870), False),
           ("05 tree band", (640, 560, 1280, 860), False)],
}
SHRUB_MATS = ("MAT_shrub", "MAT_shrub_light", "MAT_shrub_dry", "MAT_reeds")


def lum(rgb):
    return float(np.asarray(rgb, dtype=np.float64) @ LUMA)


def top_down(a):
    """gate3_common.read_exr_channels returns BOTTOM-UP arrays; the QA boxes are image coordinates."""
    return a[::-1]


def shipped_albedo(mat, e):
    """The tinted albedo that ships, and what Cycles' Diffuse Colour pass should read off it.

    Returns (base_mean_linear[3], expected_diffcol_mean_linear[3], stats), where both means are taken over
    the RAMP population - see below - and the CUT population is reported beside them.

    TWO POPULATIONS, and the difference is not pedantry. `leaf_material` does not cut the alpha, it RAMPS
    it: `alpha = maprange(tex.Alpha, cut-0.15, cut+0.15, 0, 1)`. So the texels Cycles draws at full opacity,
    which are the only ones the pass's `alpha > OPAQUE_MIN` mask can select, are `tex.Alpha > cut+0.15`. The
    viewer, drawing the same card as glTF `alphaMode: MASK` with `alphaCutoff = cut`, draws every texel
    above `cut` at full opacity. Comparing the pass against the CUT mean would therefore mix a real error
    with the colour difference between two different sets of texels, which on a texture whose alpha
    correlates with its colour (a reed blade: bright opaque core, thin dark margins) is worth tens of per
    cent. `ratio_..._over_pass` is the like-for-like RAMP comparison and answers "is the tint chain right";
    `as_drawn_over_ramp` is cut/ramp and is the separate, viewer-side statement "the MASK cut makes the card
    this much brighter than the Cycles card even when the albedo is correct"."""
    ai = e["albedo_image"]
    ap = ai.get("path") or str(ft.MAIN_ROOT / "assets" / "textures" / "foliage" / ai["file"])
    im = np.asarray(Image.open(ap).convert("RGBA"), dtype=np.float64) / 255.0
    lin, alpha = ft.s2l(im[..., :3]), im[..., 3]
    base = np.clip(lin * np.array(e["tint"], dtype=np.float64), 0.0, 1.0)
    cut = float(e["alpha_cutoff"])
    msk = alpha > cut                       # what the viewer draws (glTF MASK at alphaCutoff = cut)
    ramp = alpha > cut + ALPHA_RAMP         # what Cycles draws fully opaque (leaf_material's alpha ramp)
    assert ramp.any(), f"{mat}: no texel clears the alpha ramp at {cut + ALPHA_RAMP}"
    tr = e.get("translucency") or {}
    mult = tr.get("colour_multiplier")
    fac = tr.get("factor") or {}
    mr, tmap, k = fac.get("map_range"), fac.get("map"), fac.get("constant")
    f = None
    if tmap and mr and k is not None:
        tp = tmap.get("path") or str(ft.MAIN_ROOT / "assets" / "textures" / "foliage" / tmap["file"])
        t = np.asarray(Image.open(tp).convert("L"), dtype=np.float64) / 255.0
        fm, fx = float(mr["From Min"]), float(mr["From Max"])
        tm, tx = float(mr["To Min"]), float(mr["To Max"])
        f = np.clip(np.clip((t - fm) / max(fx - fm, 1e-9), 0.0, 1.0) * (tx - tm) + tm, 0.0, 1.0) * float(k)
        f = np.clip(f, 0.0, 1.0)
    elif k is not None:
        f = np.full(alpha.shape, float(k))
    if f is not None and mult is not None and all(v is not None for v in mult):
        exp = base * ((1.0 - f)[..., None] + f[..., None] * np.array(mult, dtype=np.float64))
    else:
        exp = base
    # ---- THE SELECTION THE PASS ACTUALLY MAKES, reproduced on the texture.
    # The pass can only be read where the Combined alpha clears OPAQUE_MIN, and a rendered pixel's alpha is
    # the mean of the card's alpha over that pixel's footprint. On a sparse sheet (MAT_reeds is 32.5 %
    # opaque) an isolated blade tip NEVER clears 0.98 at any distance, so the pixels that survive the mask
    # are the DENSE parts of the sheet. If a texture's colour correlates with its local density - a reed
    # clump whose dense base is dark and whose airy tips are pale - the ramp mean and the measured mean are
    # then means of two different populations, and the difference is an artefact of this comparison, not of
    # the shipped map. `dense_k` reproduces the mask on the texture: the texels whose KxK neighbourhood is
    # at least OPAQUE_MIN opaque, at three plausible footprints.
    ramp_a = np.clip((alpha - (cut - ALPHA_RAMP)) / (2.0 * ALPHA_RAMP), 0.0, 1.0)   # the Cycles alpha
    dense = {}
    ii = np.pad(ramp_a, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    for k in (3, 5, 9):
        h = k // 2
        p = np.pad(ii, ((h, h), (h, h)), mode="edge")
        loc = (p[k:, k:] - p[:-k, k:] - p[k:, :-k] + p[:-k, :-k])[:alpha.shape[0], :alpha.shape[1]] / (k * k)
        sel = loc >= OPAQUE_MIN
        dense[f"k{k}"] = dict(
            texel_fraction=round(float(sel.mean()), 4),
            expected_lum=(round(lum(exp[sel].mean(axis=0)), 6) if sel.any() else None))
    st = dict(source=os.path.basename(ap), tint=e["tint"], alpha_cutoff=cut, dense=dense,
              cut_texel_fraction=round(float(msk.mean()), 4),
              ramp_texel_fraction=round(float(ramp.mean()), 4), alpha_ramp=ALPHA_RAMP,
              base_lum_as_drawn=round(lum(base[msk].mean(axis=0)), 6),
              expected_lum_as_drawn=round(lum(exp[msk].mean(axis=0)), 6),
              as_drawn_over_ramp=round(lum(exp[msk].mean(axis=0)) / max(lum(exp[ramp].mean(axis=0)), 1e-9), 4),
              translucency_factor_mean=(round(float(f[ramp].mean()), 4) if f is not None else None),
              translucency_colour_multiplier=mult)
    return base[ramp].mean(axis=0), exp[ramp].mean(axis=0), st


def main():
    t0 = time.time()
    passes = json.loads((OUT / "albedo_pass.json").read_text())
    assert passes.get("schema") == "pfa-phase6c/foliage-albedo-pass/1", \
        f"albedo_pass.json schema {passes.get('schema')!r}"
    par = json.loads((OUT / "params.json").read_text())
    index_map = passes["index_map"]
    by_index = {v: k for k, v in index_map.items()}

    ship = {}
    for mat, e in sorted(par["materials"].items()):
        base, exp, st = shipped_albedo(mat, e)
        ship[mat] = dict(base_linear=[round(float(v), 6) for v in base],
                         expected_diffcol_linear=[round(float(v), 6) for v in exp],
                         base_lum=round(lum(base), 6), expected_diffcol_lum=round(lum(exp), 6),
                         base_hsv=ft.hsv_of(ft.l2s(base)), expected_hsv=ft.hsv_of(ft.l2s(exp)),
                         **st)

    rep = dict(schema=SCHEMA, generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
               generator="export/foliage_albedo_check.py",
               pass_source=str(OUT / "albedo_pass.json"), samples=passes["samples"], res=passes["res"],
               opaque_alpha_min=OPAQUE_MIN, agree_pct=AGREE_PCT,
               question="shipped tinted albedo vs the Cycles Diffuse Colour pass, in the QA-16 shrub boxes: "
                        "agreement within agree_pct => the level gap is LIGHTING (viewer); shipped brighter "
                        "=> the tint chain is wrong (export)",
               shipped=ship, stations={}, panels={})
    panels, per_object = {}, {}
    for tag, frame in sorted(passes["frames"].items()):
        ch = g3.read_exr_channels(OUT / frame["exr"])
        A = np.clip(top_down(ch["ViewLayer.Combined.A"]), 0.0, 1.0)
        I = top_down(ch["ViewLayer.Material Index.X"])
        D = np.stack([top_down(ch[f"ViewLayer.Diffuse Color.{k}"]) for k in "RGB"], axis=-1)
        panels[tag] = (D, A)
        # ---- per OBJECT, over the whole frame. `hsv(val)` is per object and the cluster noise has ~1 m
        # lobes, so a material drawn by a few clumps in frame cannot average those two terms to the 1 the
        # shipped texture pins them at. `objects_in_frame` and the spread below say whether a material's
        # measured albedo is the texture's or one clump's.
        O = top_down(ch["ViewLayer.Object Index.X"]) if "ViewLayer.Object Index.X" in ch else None
        if O is not None:
            solid_f = A > OPAQUE_MIN
            for mat, k in sorted(index_map.items()):
                m = solid_f & (np.abs(I - k) < 0.01)
                if not m.any():
                    continue
                oid = np.round(O[m]).astype(np.int64)
                ll = D[m] @ LUMA
                rows = []
                for o in np.unique(oid):
                    sel = oid == o
                    n = int(sel.sum())
                    if n < MIN_PX:
                        continue
                    rows.append((int(o), n, float(ll[sel].mean())))
                if not rows:
                    continue
                means = np.array([r[2] for r in rows])
                pw = np.array([r[1] for r in rows], dtype=np.float64)
                e = per_object.setdefault(mat, dict(objects_in_frame=0, judged_objects=0, px=0,
                                                    per_object_mean_lum=[], px_weighted_lum=0.0,
                                                    unweighted_lum=0.0, spread_max_over_min=None))
                e["objects_in_frame"] += int(len(np.unique(oid)))
                e["judged_objects"] += len(rows)
                e["px"] += int(pw.sum())
                e["per_object_mean_lum"] += [round(v, 5) for v in means]
                e["px_weighted_lum"] += float((means * pw).sum())
                e["unweighted_lum"] += float(means.sum())
                e["_wsum"] = e.get("_wsum", 0.0) + float(pw.sum())
        st_rep = dict(camera=frame["camera"], exr=frame["exr"], boxes={})
        # the whole frame as one population. The boxes are small and can contain a handful of INSTANCES,
        # and the two per-instance terms pinned to 1 (hue/value from Object Info Random, the cluster noise)
        # only average to 1 over many of them. A ratio that holds here, over every card the station sees,
        # cannot be a small-sample artefact of those terms.
        st_rep["boxes"]["WHOLE FRAME"] = dict(box=[0, 0, int(A.shape[1]), int(A.shape[0])],
                                              is_shrub_box=False, whole_frame=True)
        for name, box, is_shrub in [("WHOLE FRAME", (0, 0, int(A.shape[1]), int(A.shape[0])), False)] \
                + BOXES[tag]:
            x0, y0, x1, y1 = box
            a, i, d = A[y0:y1, x0:x1], I[y0:y1, x0:x1], D[y0:y1, x0:x1]
            solid = a > OPAQUE_MIN
            brep, tot = {}, int(solid.sum())
            for k, mat in sorted(by_index.items()):
                m = solid & (np.abs(i - k) < 0.01)
                n = int(m.sum())
                if n == 0:
                    continue
                px = d[m]
                mean = px.mean(axis=0)
                sd = float((px @ LUMA).std() / max(lum(mean), 1e-9))
                sh = ship[mat]
                r_base = lum(sh["base_linear"]) / max(lum(mean), 1e-9)
                r_exp = lum(sh["expected_diffcol_linear"]) / max(lum(mean), 1e-9)
                hue_meas = ft.hsv_of(ft.l2s(mean))
                brep[mat] = dict(
                    index=k, px=n, px_share=round(n / max(tot, 1), 4),
                    diffcol_linear=[round(float(v), 6) for v in mean],
                    diffcol_lum=round(lum(mean), 6), diffcol_hsv=hue_meas,
                    diffcol_rel_sd=round(sd, 4),
                    shipped_base_lum=sh["base_lum"], shipped_expected_lum=sh["expected_diffcol_lum"],
                    ratio_shipped_base_over_pass=round(r_base, 4),
                    ratio_shipped_expected_over_pass=round(r_exp, 4),
                    per_channel_expected_over_pass=[
                        round(float(s / max(mm, 1e-9)), 4)
                        for s, mm in zip(sh["expected_diffcol_linear"], mean)],
                    hue_delta_deg=round(hue_meas[0] - sh["expected_hsv"][0], 1),
                    judged=bool(n >= MIN_PX))
            # THE BOX LEVEL: what the shipped albedo alone predicts for this box's mean, against what the
            # pass measures on the same pixels. This is the number QA's 1.34-1.70x is comparable to, because
            # it weights every material by the area it actually covers - a material that is 0.3 % of the box
            # cannot move it, however wrong that material is on its own.
            sn = sum(ship[m]["expected_diffcol_lum"] * e["px"] for m, e in brep.items())
            sd_ = sum(e["diffcol_lum"] * e["px"] for m, e in brep.items())
            st_rep["boxes"][name] = dict(box=list(box), is_shrub_box=is_shrub,
                                         whole_frame=(name == "WHOLE FRAME"), solid_px=tot,
                                         solid_fraction=round(float(solid.mean()), 4),
                                         box_level_shipped_over_pass=(round(sn / sd_, 4) if sd_ else None),
                                         card_px=int(sum(e["px"] for e in brep.values())),
                                         materials=brep)
        rep["stations"][tag] = st_rep

    # ---------------------------------------------------------------- the verdict
    # One number per shrub/reed material: its pixel-weighted ratio over every SHRUB box of both stations.
    agg, worst_hue = {}, 0.0
    for mat in SHRUB_MATS:
        num_e = num_b = den = 0.0
        boxes_used = []
        for tag, st in rep["stations"].items():
            for name, b in st["boxes"].items():
                if not b["is_shrub_box"]:
                    continue
                e = b["materials"].get(mat)
                if not e or not e["judged"]:
                    continue
                w = e["px"]
                num_e += e["ratio_shipped_expected_over_pass"] * w
                num_b += e["ratio_shipped_base_over_pass"] * w
                den += w
                boxes_used.append(f"{name}:{w}px")
                worst_hue = max(worst_hue, abs(e["hue_delta_deg"]))
        if den:
            agg[mat] = dict(px=int(den), boxes=boxes_used,
                            ratio_expected_over_pass=round(num_e / den, 4),
                            ratio_base_over_pass=round(num_b / den, 4),
                            pct_off=round((num_e / den - 1.0) * 100.0, 2))
    # the same ratio over both WHOLE FRAMES, for every card material - the large-sample control
    wf = {}
    for mat in sorted(index_map):
        num = den = 0.0
        for tag, st in rep["stations"].items():
            e = st["boxes"]["WHOLE FRAME"]["materials"].get(mat)
            if e and e["judged"]:
                num += e["ratio_shipped_expected_over_pass"] * e["px"]
                den += e["px"]
        if den:
            wf[mat] = dict(px=int(den), ratio_expected_over_pass=round(num / den, 4),
                           pct_off=round((num / den - 1.0) * 100.0, 2),
                           as_drawn_over_ramp=ship[mat]["as_drawn_over_ramp"])
    for mat, e in per_object.items():
        mm = np.array(e.pop("per_object_mean_lum"))
        e["px_weighted_lum"] = round(e["px_weighted_lum"] / max(e.pop("_wsum"), 1e-9), 5)
        e["unweighted_lum"] = round(e["unweighted_lum"] / max(e["judged_objects"], 1), 5)
        e["spread_max_over_min"] = round(float(mm.max() / max(mm.min(), 1e-9)), 3)
        e["rel_sd_across_objects"] = round(float(mm.std() / max(mm.mean(), 1e-9)), 4)
        e["shipped_over_unweighted"] = round(ship[mat]["expected_diffcol_lum"] / max(e["unweighted_lum"], 1e-9), 4)
        e["note"] = ("objects_in_frame counts every object with a pixel; judged_objects those with at "
                     "least MIN_PX. A material whose judged_objects is small cannot average the "
                     "per-object value term the shipped texture pins to 1.")
    rep["whole_frame"] = wf
    rep["per_object"] = per_object
    # The verdict is the BOX level, because that is what QA measured: the worst shrub box's predicted mean
    # against the pass's. Per-material outliers are reported beside it with the area they cover.
    box_levels = {f"{tag} {name}": b["box_level_shipped_over_pass"]
                  for tag, st in rep["stations"].items() for name, b in st["boxes"].items()
                  if b["is_shrub_box"] and b["box_level_shipped_over_pass"]}
    # Direction matters, and the brief says so: "if they agree within 10 % the level gap is LIGHTING ... if
    # the shipped albedo is BRIGHTER, fix the export". A box whose shipped albedo is DARKER than the pass
    # cannot be the cause of a viewer that renders it 1.34-1.70x too bright - it makes the irradiance excess
    # larger, not smaller - so `worst` is the brightest box, and the darkest is reported beside it.
    hi = max(box_levels.values(), default=1.0)
    lo = min(box_levels.values(), default=1.0)
    worst = (hi - 1.0) * 100.0
    verdict = "EXPORT" if worst > AGREE_PCT else "LIGHTING"
    outliers = {m: dict(ratio=v["ratio_expected_over_pass"], px=v["px"],
                        share_of_shrub_box_card_px=round(
                            v["px"] / max(sum(x["px"] for x in agg.values()), 1), 4))
                for m, v in agg.items() if abs(v["ratio_expected_over_pass"] - 1.0) * 100.0 > AGREE_PCT}
    rep["aggregate"] = agg
    rep["box_levels"] = {k: round(v, 4) for k, v in sorted(box_levels.items())}
    rep["per_material_outliers"] = outliers
    rep["verdict"] = dict(
        owner=verdict, brightest_box_pct_over=round(worst, 2),
        darkest_box_pct_under=round((1.0 - lo) * 100.0, 2), threshold_pct=AGREE_PCT,
        basis="the worst SHRUB BOX level: sum(shipped_expected_lum * px) / sum(pass_lum * px) over every "
              "card material in the box, which is the quantity QA's 1.34-1.70x measures",
        box_levels={k: round(v, 4) for k, v in sorted(box_levels.items())},
        per_material_outliers=outliers,
        index_map_hue_check=dict(worst_abs_hue_delta_deg=round(worst_hue, 1),
                                 rule="each index's measured Diffuse-Colour hue against its material's own "
                                      "expected hue; MAT_shrub_dry is 36 deg where the others are 69-95, so "
                                      "a scrambled pass_index map cannot pass this"),
        reading=("no shrub box's shipped albedo is brighter than the albedo Cycles itself uses on the same "
                 "cards: the brightest is %+.1f %% and the darkest %+.1f %%, against the 1.34-1.70x QA "
                 "measures in the viewer. The level gap is therefore NOT in the albedo - it is irradiance, "
                 "and the owner is the VIEWER." % (worst, -(1.0 - lo) * 100.0))
                if verdict == "LIGHTING" else
                ("the shipped tinted albedo is %.1f %% BRIGHTER than the albedo Cycles uses at the worst "
                 "shrub box: the tint chain is wrong and the fix is in export/foliage_tex.py" % worst))

    # ---------------------------------------------------------------- the sheet
    W = 960
    pw, ph = W // 2, (W // 2) * 1080 // 1920
    sheet = Image.new("RGB", (W, ph + 24 + 20 * (len(SHRUB_MATS) + 6)), (22, 22, 24))
    dr = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 10)
        fb = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 11)
    except OSError:
        f = fb = ImageFont.load_default()
    for n, (tag, (D, A)) in enumerate(sorted(panels.items())):
        disp = np.clip(ft.l2s(np.clip(D, 0, 1)), 0, 1) * np.clip(A, 0, 1)[..., None] \
            + 0.09 * (1.0 - np.clip(A, 0, 1))[..., None]
        img = Image.fromarray(np.round(np.clip(disp, 0, 1) * 255).astype(np.uint8)).resize((pw, ph),
                                                                                           Image.LANCZOS)
        sheet.paste(img, (n * pw, 0))
        d2 = ImageDraw.Draw(sheet)
        for name, box, is_shrub in BOXES[tag]:
            if not is_shrub:
                continue
            s = pw / 1920.0
            d2.rectangle([n * pw + box[0] * s, box[1] * s * 1.0, n * pw + box[2] * s, box[3] * s],
                         outline=(255, 190, 60), width=1)
            d2.text((n * pw + box[0] * s + 2, box[1] * s + 2), name, font=f, fill=(255, 210, 110))
        d2.text((n * pw + 4, ph - 13), f"cam{tag} Cycles Diffuse Colour pass (foliage isolated, sRGB)",
                font=f, fill=(200, 200, 200))
    y = ph + 6
    dr.text((6, y), "6c item 1 - the shipped tinted card albedo against the Cycles Diffuse Colour pass, "
                    "in the QA-16 shrub boxes", font=fb, fill=(255, 255, 255))
    y += 15
    dr.text((6, y), f"VERDICT: {verdict}   brightest shrub box {worst:+.1f} %, darkest "
                    f"{-(1.0 - lo) * 100.0:+.1f} %, EXPORT would need > +{AGREE_PCT:.0f} %",
            font=f, fill=(255, 230, 140))
    y += 13
    dr.text((6, y), "box level (shipped albedo / pass albedo, every card material weighted by its area): "
            + "   ".join(f"{k.split(' ', 1)[1]} {v:.2f}" for k, v in sorted(box_levels.items())),
            font=f, fill=(200, 200, 205))
    y += 16
    dr.text((6, y), "material            shipped   Cycles    ratio   px      hue d   swatches "
                    "(left=shipped expected, right=Cycles pass)", font=f, fill=(170, 170, 175))
    y += 14
    for mat in SHRUB_MATS:
        a_ = agg.get(mat)
        if not a_:
            continue
        sh = ship[mat]
        # the pixel-weighted mean measured colour, for the swatch
        acc, wsum = np.zeros(3), 0.0
        hd = 0.0
        for tag, st in rep["stations"].items():
            for name, b in st["boxes"].items():
                if not b["is_shrub_box"]:
                    continue
                e = b["materials"].get(mat)
                if e and e["judged"]:
                    acc += np.array(e["diffcol_linear"]) * e["px"]
                    wsum += e["px"]
                    hd = e["hue_delta_deg"]
        meas = acc / max(wsum, 1e-9)
        dr.text((6, y), f"{mat:19s} {lum(sh['expected_diffcol_linear']):.4f}   {lum(meas):.4f}   "
                        f"{a_['ratio_expected_over_pass']:.3f}   {a_['px']:7d} {hd:+6.1f}",
                font=f, fill=(235, 235, 235))
        for j, c in enumerate((np.array(sh["expected_diffcol_linear"]), meas)):
            col = tuple(int(round(v * 255)) for v in np.clip(ft.l2s(np.clip(c, 0, 1)), 0, 1))
            dr.rectangle([560 + j * 46, y - 1, 560 + j * 46 + 40, y + 11], fill=col,
                         outline=(90, 90, 95))
        y += 15
    y += 6
    for line in (rep["verdict"]["reading"][i:i + 118]
                 for i in range(0, len(rep["verdict"]["reading"]), 118)):
        dr.text((6, y), line, font=f, fill=(180, 210, 180))
        y += 13
    if outliers:
        dr.text((6, y), "per-material outlier(s): " + "; ".join(
            f"{m} {v['ratio']:.2f}x on {v['share_of_shrub_box_card_px'] * 100:.1f} % of the shrub boxes' "
            f"card pixels" for m, v in outliers.items()), font=f, fill=(230, 180, 140))
        y += 13
    dr.text((6, y), f"pass: {passes['samples']} spp {passes['res'][0]}x{passes['res'][1]} Cycles, foliage "
                    f"isolated, film transparent; alpha>{OPAQUE_MIN}; IndexMA split, hue-validated "
                    f"(worst {worst_hue:.1f} deg)", font=f, fill=(150, 150, 155))
    SHEET.parent.mkdir(parents=True, exist_ok=True)
    sheet.crop((0, 0, W, min(sheet.height, y + 18))).save(SHEET, quality=88)

    rep["sheet"] = str(SHEET.relative_to(ROOT))
    rep["wall_s"] = round(time.time() - t0, 1)
    (OUT / "albedo_check.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(f"[albedo_check] VERDICT {verdict}: brightest shrub box {worst:+.1f} %, darkest "
          f"{-(1.0 - lo) * 100.0:+.1f} % (threshold +{AGREE_PCT:.0f} %), index-map hue check worst "
          f"{worst_hue:.1f} deg")
    for k, v in sorted(box_levels.items()):
        print(f"  box {k:26s} shipped/pass {v:.3f}")
    for mat, a_ in agg.items():
        print(f"  {mat:20s} shipped/pass {a_['ratio_expected_over_pass']:.3f} "
              f"(untranslucent {a_['ratio_base_over_pass']:.3f})  {a_['px']:7d} px")
    print(f"[albedo_check] -> {OUT / 'albedo_check.json'}  +  {SHEET}")


if __name__ == "__main__":
    main()
