#!/usr/bin/env python3
"""Phase 8b step 3: the band sidecar the export reads, plus the numbers the report quotes.

    python3 export/band_compose.py            # after export/band_queue.sh has finished (and band_pack.sh)

No Blender, no GPU. Reads the 16 records in export/out/gate3/band/rec/, the band PNGs and (read-only) the
shipped 2K octahedral PNGs, and writes export/out/gate3/band/band.json + band/band_report.json.

The histogram definitions are IMPORTED from export/p8_atlas_probe.py (`bands`, `hist`,
`transitions_per_100px`), so the band numbers are comparable, term for term, with the 8b analysis'
1K/2K octahedral numbers.
"""
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import band_common as bc          # noqa: E402
import p8_atlas_probe as probe    # noqa: E402

MAIN = bc.MAIN_ROOT
STATIONS = ("CAM_qa_01_lagoon_hero", "CAM_qa_02_lagoon_ne_threequarter", "CAM_qa_03_colonnade_walk",
            "CAM_qa_04_rotunda_ceiling", "CAM_qa_05_south_lawn", "CAM_qa_06_aerial")


def read_png(path):
    """-> BOTTOM-UP uint8 RGBA, the order the bake writes and `p8_atlas_probe.bands` assumes.

    Orientation matters and the 8b analysis got it wrong: p8_atlas_probe.main() reads the atlas
    top-down (`np.asarray(Image.open(...))`) and then calls `bands()`, whose docstring says row 0 of
    the array is the trunk. On a top-down array row 0 is the tree TOP, so its "crown top" band is the
    frame's bottom third (the trunk) and its "trunk band" is the crown top - measured here on the
    shipped 2K broadleaf_s53 cam02 frame: p8 "crown top" mean alpha 0.055 is geometrically the trunk
    band, p8 "trunk band" 0.1545 is the crown top. Its frame INDEXING is flipped the same way
    (`row` then counts frames from the top). Everything in this file reads bottom-up, so `bands()`,
    `hist()` and `frame_alpha()` mean what they say.
    """
    from PIL import Image
    return np.asarray(Image.open(str(path)).convert("RGBA"), dtype=np.uint8)[::-1]


def band_inner_alpha(atlas, i, j):
    y0, y1, x0, x1 = bc.inner_slice(i, j)
    return atlas[y0:y1, x0:x1, 3].astype(np.float32) / 255.0


def crown_top_hist(a):
    top, _, _ = probe.bands(a)
    return probe.hist(top) if top is not None else {}


def main():
    man = json.loads((MAIN / "export/out/gate3/manifest.json").read_text())
    imp = man["impostors"]
    setrep = json.loads((bc.BAND_OUT / "band_set.json").read_text())
    protos = sorted(setrep["prototypes"])
    recs = {p: json.loads((bc.REC_DIR / f"{p}.json").read_text()) for p in protos}

    # ---- the station-2 view per prototype (export/imp_diag_atlas.py): the true camera direction and the
    # octahedral frame it picks. `view_dir` is the real direction, `baked_dir` the frame's own.
    diag = json.loads((MAIN / "export/out/gate3/impostor_diag_atlas.json").read_text())["prototypes"]
    cam02 = {p: dict(frame=(e["1024"]["cam02_frame"]["col"], e["1024"]["cam02_frame"]["row"]),
                     view_dir=e["1024"]["cam02_frame"]["view_dir"],
                     baked_dir=e["1024"]["cam02_frame"]["baked_dir"],
                     nearest_m=e["nearest_cam02_m"])
             for p, e in diag.items()}

    out, rep = {}, {}
    for p in protos:
        r = recs[p]
        m = imp["prototypes"][p]
        png = bc.BAND_OUT / bc.png_name(p)
        ktx = bc.BAND_OUT / bc.ktx_name(p)
        atlas = read_png(png)
        assert atlas.shape[:2] == (bc.ATLAS_H, bc.ATLAS_W), f"{png}: {atlas.shape}"
        # crown-top alpha: every elevation-0 column (what the six stations look at), and their mean
        per_col = [crown_top_hist(band_inner_alpha(atlas, i, 0)) for i in range(bc.GRID_AZ)]
        mean_top = {k: round(float(np.mean([c[k] for c in per_col])), 4)
                    for k in per_col[0] if k != "texels"}
        # the frame the station-2 view picks, and the 2K octahedral frame the analysis measured
        c2 = cam02.get(p)
        cell = None
        if c2:
            d = np.array(c2["view_dir"], dtype=np.float64)
            d /= np.linalg.norm(d)
            i, j, az, el = bc.cell_of(tuple(float(v) for v in d))
            a_band = band_inner_alpha(atlas, i, j)
            cell = dict(octa_frame=list(c2["frame"]), view_dir=[round(float(v), 5) for v in d],
                        nearest_cam02_m=c2["nearest_m"], az_deg=round(az, 2), el_deg=round(el, 2),
                        band_cell=[i, j], band_dir=[round(v, 5) for v in bc.direction(i, j)],
                        angle_to_cell_deg=round(math.degrees(math.acos(max(-1.0, min(1.0, float(
                            np.dot(d, np.array(bc.direction(i, j)))))))), 2),
                        crown_top=crown_top_hist(a_band),
                        crown_crossings_per_100_texels=probe.transitions_per_100px(
                            probe.bands(a_band)[1] > probe.ALPHA_TEST, 1.0))
            octa = bc.OCTA_DIR / f"gate3_imp_{p}_albedo_2048.png"
            if octa.exists():
                oa = probe.frame_alpha(read_png(octa), 2048, *c2["frame"])
                cell["octa_2k_crown_top"] = crown_top_hist(oa)
                cell["octa_2k_crown_crossings_per_100_texels"] = probe.transitions_per_100px(
                    probe.bands(oa)[1] > probe.ALPHA_TEST, 1.0)
        sphere = dict(centre_m=r["centre"], radius_m=r["radius_m"],
                      note="the prototype's own bounding sphere in its own frame: the same sphere the "
                           "octahedral bake framed, so impostors.placement is unchanged")
        out[p] = dict(
            albedo=bc.key(p), file=bc.ktx_name(p), png=png.name,
            png_bytes=png.stat().st_size, ktx2_bytes=(ktx.stat().st_size if ktx.exists() else None),
            range=r["range"], range_same_as_octahedral=r["range_same_as_octahedral"],
            range_band_p999=r["range_band_p999"],
            clipped_body_texels=r["clipped_body_texels"], body_texels=r["body_texels"],
            clipped_body_pct=round(100.0 * r["clipped_body_texels"] / max(r["body_texels"], 1), 3),
            crown_sphere_m=sphere, radius_m=r["radius_m"], centre_z_m=r["centre_z_m"],
            base_z_m=r["base_z_m"], height_above_base_m=r["height_above_base_m"],
            depth_range_m=r["depth_range_m"], bbox_m=r["bbox_m"],
            views=r["views"], alpha_coverage=r["alpha_coverage"],
            roundtrip_albedo=r["roundtrip_albedo"],
            render_s=r["render_s"], s_per_view=r["s_per_view"])
        rep[p] = dict(crown_top_el0_mean=mean_top, crown_top_el0_per_column=per_col,
                      cam02=cell, render_s=r["render_s"], wall_s=r.get("wall_s"),
                      png_bytes=png.stat().st_size,
                      ktx2_bytes=(ktx.stat().st_size if ktx.exists() else None))
        for k in ("radius_m", "centre_z_m", "base_z_m", "height_above_base_m", "depth_range_m"):
            assert abs(out[p][k] - m[k]) < 5e-4, f"{p}: {k} drifted from the manifest"

    # ---- what elevation the six stations actually see the far-tree crowns at (the band clamps at 0 deg)
    st = {}
    for cam in STATIONS:
        loc = np.array(man["stations"][cam]["location"], dtype=np.float64)
        els, ds = [], []
        for t in man["tree_far"]:
            p = imp["prototype_map"].get(t["prototype"], t["prototype"])
            m = imp["prototypes"][p]
            s = t["height_m"] / m["height_above_base_m"]
            c = np.array(t["trunk_base"], dtype=np.float64) + np.array([0.0, 0.0, m["centre_z_m"] * s])
            d = loc - c
            n = float(np.linalg.norm(d))
            els.append(math.degrees(math.asin(d[2] / n)))
            ds.append(n)
        els, ds = np.array(els), np.array(ds)
        near = els[ds < 120.0]
        st[cam] = dict(
            trees=len(els), dist_m=[round(float(ds.min()), 1), round(float(np.median(ds)), 1),
                                    round(float(ds.max()), 1)],
            elevation_deg=dict(min=round(float(els.min()), 2), median=round(float(np.median(els)), 2),
                               max=round(float(els.max()), 2),
                               p10=round(float(np.percentile(els, 10)), 2),
                               p90=round(float(np.percentile(els, 90)), 2)),
            elevation_deg_within_120m=(dict(n=int(near.size), min=round(float(near.min()), 2),
                                            median=round(float(np.median(near)), 2),
                                            max=round(float(near.max()), 2)) if near.size else None),
            row_choice_pct={str(bc.ELEV_DEG[j]): round(100.0 * float(np.mean(
                [bc.cell_of((math.cos(math.radians(e)), 0.0, math.sin(math.radians(e))))[1] == j
                 for e in els])), 1) for j in range(bc.GRID_EL)},
            mean_row_error_deg=round(float(np.mean([abs(e - bc.ELEV_DEG[bc.cell_of(
                (math.cos(math.radians(e)), 0.0, math.sin(math.radians(e))))[1]]) for e in els])), 2))

    band = dict(
        schema=bc.SCHEMA,
        generator="export/band_set.py + export/bake_band.py + export/band_compose.py",
        source_blend=dict(path=str(MAIN / "master_delivery.blend"), mtime=setrep["src_mtime"],
                          bytes=setrep["src_bytes"], nursery="export/out/gate3/band_imp.blend"),
        mapping="band", grid_az=bc.GRID_AZ, grid_el=bc.GRID_EL,
        atlas_px=[bc.ATLAS_W, bc.ATLAS_H], frame_px=bc.FRAME_PX, gutter_px=bc.GUTTER_PX,
        inner_px=bc.INNER_PX, pad_px=dict(x=bc.PAD_X, y=bc.PAD_Y, value="0,0,0,0",
                                          note="12*341 = 4092 of 4096 and 3*341 = 1023 of 1024; the "
                                               "right 4 columns and the top row are unwritten and never "
                                               "sampled (frame_uv never reaches them)"),
        azimuth0_deg=bc.AZIMUTH0_COMPASS_DEG,
        azimuth0_convention=(
            "azimuth 0 is the view direction d = camera - billboard = (1, 0, 0) in BLENDER Z-up world "
            "space (+X, which CLAUDE.md's compass makes due SOUTH, hence azimuth0_deg = 180 clockwise "
            "from north). It is the octahedral map's +X pole: impostors.frame_lookup on (1,0,0) gives "
            "frame (col, row) = (11, 6), and that frame and band cell (0, 0) face the same world "
            "heading. Azimuth increases CLOCKWISE seen from above (+X -> -Y -> -X -> +Y), so cell i "
            "faces d_xy = (cos(30 i deg), -sin(30 i deg))."),
        azimuth0_blender_dir=list(bc.AZIMUTH0_BLENDER_DIR),
        azimuth0_octahedral_frame=list(bc.octa_cell(bc.AZIMUTH0_BLENDER_DIR)),
        azimuth_step_deg=bc.AZ_STEP_DEG,
        azimuth_dir="clockwise seen from above",
        elevations_deg=list(bc.ELEV_DEG),
        elevation_datum="the BILLBOARD CENTRE (trunk_base + (0,0,centre_z_m*s)), positive above the horizon",
        row_order=("row 0 = elevations_deg[0], counted from the BOTTOM of the image - the same convention "
                   "impostors.frame_lookup uses for its octahedral rows"),
        cell_dirs_blender={f"{i},{j}": [round(v, 5) for v in bc.direction(i, j)]
                           for j in range(bc.GRID_EL) for i in range(bc.GRID_AZ)},
        octahedral_nearest_frame={f"{i},{j}": list(bc.octa_cell(bc.direction(i, j)))
                                  for j in range(bc.GRID_EL) for i in range(bc.GRID_AZ)},
        frame_lookup=bc.FRAME_LOOKUP, frame_uv=bc.FRAME_UV,
        encode=dict(
            albedo=("gamma2 on RGB at the prototype's own `range` (rgb = t.rgb*t.rgb*range, LINEAR oetf, "
                    "NOT sRGB), straight (un-premultiplied) alpha in A - byte for byte the octahedral "
                    "albedo encode. `range` here EQUALS impostors.prototypes[p].range, so one constant "
                    "decodes both atlases."),
            alpha=("COVERAGE, exactly as the octahedral bake: a = clip(Cycles Combined.A, 0, 1). No "
                   "threshold, no dilate, no erode, and no premultiplied 2x reduction (the band is "
                   "written at its native 341 px)."),
            normal_depth="omitted on purpose (the contract): the band replaces the albedo lookup only."),
        ktx2=("toktx --t2 --encode uastc --uastc_quality 2 --zcmp 18 --assign_oetf linear, NO mips - the "
              "same flags the octahedral atlases ship with (export/gate3_pack.sh)"),
        lighting=imp["lighting"], unlit=imp["unlit"], instance_rotation=imp["instance_rotation"],
        placement=imp["placement"],
        placement_note=("unchanged: the band frames the same bounding sphere at the same ortho scale, so "
                        "radius_m / centre_z_m / height_above_base_m are identical to "
                        "impostors.prototypes (asserted in band_compose.py)"),
        samples=bc.SAMPLES, prototypes=out, prototype_map=imp["prototype_map"])
    bc.BAND_OUT.mkdir(parents=True, exist_ok=True)
    (bc.BAND_OUT / "band.json").write_text(json.dumps(band, indent=1) + "\n")

    totals = dict(
        prototypes=len(protos),
        png_bytes=sum(v["png_bytes"] for v in out.values()),
        ktx2_bytes=(sum(v["ktx2_bytes"] for v in out.values())
                    if all(v["ktx2_bytes"] for v in out.values()) else None),
        gpu_render_s=round(sum(v["render_s"] for v in out.values()), 1),
        wall_s=round(sum(r.get("wall_s") or 0 for r in recs.values()), 1),
        render_s_min=min(v["render_s"] for v in out.values()),
        render_s_max=max(v["render_s"] for v in out.values()),
        clipped_body_pct_max=max(v["clipped_body_pct"] for v in out.values()))
    (bc.BAND_OUT / "band_report.json").write_text(json.dumps(
        dict(totals=totals, per_prototype=rep, stations=st), indent=1) + "\n")
    print(json.dumps(totals, indent=1))
    for p in protos:
        c = rep[p]["cam02"] or {}
        t = c.get("crown_top", {})
        o = c.get("octa_2k_crown_top", {})
        print(f"{p:36s} cam02 band{c.get('band_cell')} semi {t.get('semi_pct')}% mean {t.get('mean')} "
              f"| 2K octa semi {o.get('semi_pct')}% mean {o.get('mean')} "
              f"| crossings/100 texels {c.get('crown_crossings_per_100_texels')} vs "
              f"{c.get('octa_2k_crown_crossings_per_100_texels')}")
    print("stations (elevation at the billboard centre):")
    for k, v in st.items():
        print(f"  {k:34s} el {v['elevation_deg']['min']:+.1f} / {v['elevation_deg']['median']:+.1f} / "
              f"{v['elevation_deg']['max']:+.1f} deg, row0 {v['row_choice_pct']['0.0']} %, "
              f"mean row error {v['mean_row_error_deg']} deg")


if __name__ == "__main__":
    main()
