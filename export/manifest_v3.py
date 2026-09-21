#!/usr/bin/env python3
"""Gate 2 step 4: write export/out/gate2/manifest.json as schema `pfa-phase6/3`.

    python3 export/manifest_v3.py

Carries every Gate 1 (v2) block verbatim, with the file paths rewritten so they resolve from export/out/gate2/,
and adds `materials` (mode "pbr", the per-material texture sets), `textures.gate2` and `budget`.
`lightmap_encoding` and `textures.schema` are copied unchanged - the RGBM contract is not renegotiated here.

Documented in export/README.md, "manifest.json v3". Reads only; writes one JSON.
"""
import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "export"))
import gate0_common as g0  # noqa: E402
import gate2_common as g2  # noqa: E402

OUT = g2.OUT
GATE1 = g2.GATE1_OUT
# ASTC 4x4 on the Apple GPU = 8 bpp = 1 byte per texel, x 4/3 for the full mip chain (the budget doc's rule).
BYTES_PER_TEXEL = 1.0
MIP = 4.0 / 3.0
BUDGET_MB = 1200
# a map whose covered texels vary by less than this (linear, per channel) ships as a factor and no texture
CONSTANT_STD = 0.005


def resident_mb(px, maps=1):
    return round(px * px * BYTES_PER_TEXEL * MIP * maps / (1024.0 * 1024.0), 2)


def reroot1(obj):
    """Gate 1's manifest paths are relative to export/out/gate1/ (and some already point at ../gate0/)."""
    if isinstance(obj, dict):
        return {k: reroot1(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [reroot1(v) for v in obj]
    if isinstance(obj, str) and obj.endswith((".cube", ".exr", ".hdr", ".png", ".glb", ".gltf", ".ktx2")) \
            and not obj.startswith(("/", "../")):
        return "../gate1/" + obj
    if isinstance(obj, str) and obj.startswith("../gate0/"):
        return obj
    return obj


def gltf_uv0_meshes():
    """Mesh names whose glTF primitives all carry TEXCOORD_0, read from the Gate 1 .gltf files.

    `uv1_in_glb` is derived from the shipped file, never asserted by hand: the ten backdrop groups left
    Gate 1 with no UV1 at all (QA-11c-2), Gate 2 generated one and wrote it to backdrop_uv1.npz, and the
    export engineer re-exported env.glb with it. This reads back which meshes actually have it now.
    """
    have, seen = set(), {}
    for cls in ("arch", "orn", "env", "ground"):
        p = GATE1 / f"{cls}.gltf"
        if not p.exists():
            continue
        d = json.loads(p.read_text())
        for m in d.get("meshes", []):
            n = m.get("name")
            if not n:
                continue
            seen[n] = cls
            if m["primitives"] and all("TEXCOORD_0" in pr.get("attributes", {}) for pr in m["primitives"]):
                have.add(n)
    return have, seen


def backdrop_uv_matches(gltf_have):
    """Prove that the UV1 now in env.gltf IS the layout Gate 2 baked against, not a fresh unwrap.

    The exporter de-duplicates vertices, so counts and means cannot be compared (a mean test called all ten a
    mismatch); the SET of distinct UV pairs survives de-duplication exactly. glTF puts the UV origin at the top
    left, so Blender's exporter writes `v_gltf = 1 - v_blender` - the same flip every other texture in this
    project already rides. Both hypotheses are measured and the better one is reported.
    """
    import numpy as np
    # compare against the layout env.glb actually SHIPS. gate2_set.py regenerates backdrop_uv1.npz on every
    # run, so comparing the current one would be new-against-new and would pass however much it drifted.
    npz = OUT / "backdrop_uv1_shipped.npz"
    if not npz.exists():
        npz = OUT / "backdrop_uv1.npz"
    gp = GATE1 / "env.gltf"
    if not (npz.exists() and gp.exists()):
        return None
    d = json.loads(gp.read_text())
    z = np.load(str(npz))
    bins, out = {}, {}
    for m in d.get("meshes", []):
        n = m.get("name")
        if n not in z.files or not m["primitives"]:
            continue
        attrs = m["primitives"][0].get("attributes", {})

        def uv_set(which):
            """The float32 UV array of TEXCOORD_<which>, or None when the set is absent/quantised."""
            if which not in attrs:
                return None
            acc = d["accessors"][attrs[which]]
            if acc.get("componentType") != 5126:        # a quantised export is not comparable this way
                return None
            bv = d["bufferViews"][acc["bufferView"]]
            uri = d["buffers"][bv["buffer"]].get("uri")
            if not uri:
                return None
            if uri not in bins:
                bins[uri] = (gp.parent / uri).read_bytes()
            off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
            return np.frombuffer(bins[uri], dtype=np.float32, count=acc["count"] * 2, offset=off).reshape(-1, 2)

        # Phase 9: the ENV build inserted the tile UV ("UVMap", world metres / tile) at layer 0, so the
        # BAKED layout moves to TEXCOORD_1.  Which set carries it is never assumed - every set present is
        # scored against the npz and the best one wins, so a swap of the two is a loud failure here and
        # `texcoord` in the manifest is read back rather than asserted.
        b = z[n]
        sd = {(round(float(x), 5), round(float(y), 5)) for x, y in b}
        sf = {(round(float(x), 5), round(float(1.0 - y), 5)) for x, y in b}
        scored = {}
        for i in (0, 1, 2):
            a = uv_set(f"TEXCOORD_{i}")
            if a is None:
                continue
            sg = {(round(float(x), 5), round(float(y), 5)) for x, y in a}
            direct, flip = len(sg & sd) / len(sg), len(sg & sf) / len(sg)
            span = float(max(a[:, 0].max() - a[:, 0].min(), a[:, 1].max() - a[:, 1].min()))
            scored[i] = dict(distinct_uv_gltf=len(sg), match_direct=round(direct, 5),
                             match_v_flipped=round(flip, 5), v_flipped=flip > direct,
                             match=round(max(direct, flip), 5), uv_span=round(span, 3))
        if not scored:
            continue
        best = max(scored, key=lambda i: scored[i]["match"])
        out[n] = dict(scored[best])
        out[n]["texcoord"] = best
        out[n]["sets_in_glb"] = sorted(scored)
        # the tile UV is the OTHER set, and it is recognisable on its own terms: it runs in tile units, so
        # its span is many tiles wide where a packed bake atlas can never leave [0,1].
        other = [i for i in scored if i != best]
        out[n]["tile_texcoord"] = other[0] if len(other) == 1 else None
        out[n]["tile_uv_span"] = scored[other[0]]["uv_span"] if len(other) == 1 else None
        out[n]["ok"] = out[n]["match"] >= 0.999
    return out


def main():
    man = reroot1(json.loads((GATE1 / "manifest.json").read_text()))
    gltf_have, gltf_seen = gltf_uv0_meshes()
    jobs = {j["id"]: j for j in g2.read_jobs()["jobs"]}
    recs, missing = {}, []
    for jid in jobs:
        p = OUT / "bake" / f"{jid}.json"
        if p.exists():
            recs[jid] = json.loads(p.read_text())
        else:
            missing.append(jid)

    ktx = OUT / "tex_ktx2"
    etc = OUT / "tex_ktx2_etc1s"
    ktx_bytes = {f.stem: f.stat().st_size for f in sorted(ktx.glob("*.ktx2"))} if ktx.is_dir() else {}
    detail_files = {k: v for k, v in ktx_bytes.items() if k.startswith("detail_")}
    detail_px = {}
    if (OUT / "detail.json").exists():
        _d = json.loads((OUT / "detail.json").read_text())
        for _k, _rec in _d["sets"].items():
            for _r, _v in _rec["maps"].items():
                detail_px[f"detail_{_k}_{_r}"] = _v.get("px", 1024)
    etc_bytes = {f.stem: f.stat().st_size for f in sorted(etc.glob("*.ktx2"))} if etc.is_dir() else {}

    files, sets = {}, {}
    per_cls = {}
    for jid, rec in sorted(recs.items()):
        job = jobs[jid]
        cls = job["cls"]
        entry = dict(job=jid, cls=cls, src_material=(job["src_materials"][0] if len(job["src_materials"]) == 1
                                                     else job["src_materials"]),
                     size=job["size"],
                     uv1_in_glb=(all(m in gltf_have for m in job["meshes"]) if gltf_seen
                                 else job["uv1_in_glb"]))
        for kind, m in rec["maps"].items():
            st = m["stats"]
            mean = st.get("mean") or [0.0, 0.0, 0.0]
            std = st.get("std") or [0.0, 0.0, 0.0]
            key = f"gate2_{jid}_{kind}"
            # a normal map whose X and Y never leave the flat value carries nothing: the surface uses its
            # geometry normal and the texture is pure resident memory (measured on 6 of the 10 backdrop groups).
            constant = (max(std[:2]) if kind == "normal" else max(std)) < CONSTANT_STD
            # QA-12-1: an ARCH / ground set always ships a normal map, however small its amplitude, so the
            # viewer never falls back to a flat geometry normal on stone. The amplitude is what the atlas
            # texel can carry (std 0.0017-0.0234); the grain itself rides materials.detail, not this map.
            if kind == "normal" and cls in (g2.CLS_ARCH, g2.CLS_GROUND):
                constant = False
            if not constant:
                files[key] = dict(path=f"{key}.ktx2", w=m["ship_px"], h=m["ship_px"], map=kind,
                                  colorspace=("srgb" if kind == "albedo" else "linear"),
                                  cls=cls, job=jid, bytes=ktx_bytes.get(key),
                                  etc1s_bytes=etc_bytes.get(key),
                                  resident_mb=resident_mb(m["ship_px"]),
                                  png_bytes=m["bytes"], bake_s=m["bake_s"], bake_px=m["bake_px"],
                                  downsample_rms=m["downsample_rms"], coverage=st.get("coverage"),
                                  stats=dict(mean=mean, std=std, min=st.get("min"), max=st.get("max")))
                per_cls.setdefault(cls, dict(maps=0, resident_mb=0.0, ktx2_bytes=0, bake_s=0.0))
                per_cls[cls]["maps"] += 1
                per_cls[cls]["resident_mb"] += resident_mb(m["ship_px"])
                per_cls[cls]["ktx2_bytes"] += ktx_bytes.get(key) or 0
            per_cls.setdefault(cls, dict(maps=0, resident_mb=0.0, ktx2_bytes=0, bake_s=0.0))
            per_cls[cls]["bake_s"] += m["bake_s"]
            slot = dict(texture=(None if constant else key), constant=constant)
            if kind == "albedo":
                slot["factor"] = [round(v, 6) for v in mean]
            elif kind == "normal":
                slot["scale"] = 1.0
                slot["factor"] = [0.5, 0.5, 1.0] if constant else None
            else:
                slot["factor"] = round(mean[0], 6)
            entry["occlusion" if kind == "ao" else kind] = slot
        if "metallic" not in entry:
            entry["metallic"] = dict(texture=None, constant=True, factor=0.0)
        if cls == g2.CLS_ORN:
            # the Gate 1 AO map rides on, in glTF's occlusionTexture; the Gate 1 NORMAL is superseded here
            entry["occlusion"] = dict(texture=None, constant=False, in_glb=True,
                                      gate1_texture=Path(job["gate1_ao"]).stem, factor=None,
                                      note="Gate 1 map, unchanged, already in orn.glb occlusionTexture - "
                                           "the viewer loads nothing for it")
            entry["normal"]["replaces_gate1"] = Path(job["gate1_normal"]).stem
        sets[job["group"]] = entry

    # ------------------------------------------------- Phase 9: the backdrop gain tiles and their UV set
    # `export/p9_bd_tiles.py` encodes four REPEAT-sampled, Non-Color gain images the viewer multiplies over
    # the baked backdrop albedo (docs/briefs/phase9_env_report.md "Export hand-off").  They are NOT bake
    # products, so they carry no `job`/`bake_s`/`stats`; every consumer downstream reads only
    # path/w/h/map/colorspace/cls/bytes/resident_mb, and `bytes` keeps the gate2 totals and the resident
    # budget honest.  The block below is the only place the four rows and their constants enter the chain.
    bd_tiles = None
    bd_path = OUT / "p9_backdrop_tiles.json"
    if bd_path.exists():
        bd_tiles = json.loads(bd_path.read_text())
        for key, row in sorted(bd_tiles["files"].items()):
            files[key] = dict(path=row["path"], w=row["w"], h=row["h"], map=row["map"],
                              colorspace=row["colorspace"], cls=row["cls"], job=None,
                              bytes=row["bytes"], etc1s_bytes=None,
                              resident_mb=resident_mb(row["w"]),
                              png_bytes=row.get("png_bytes"), encode=row.get("encode"),
                              source="export/p9_bd_tiles.py")
            per_cls.setdefault(row["cls"], dict(maps=0, resident_mb=0.0, ktx2_bytes=0, bake_s=0.0))
            per_cls[row["cls"]]["maps"] += 1
            per_cls[row["cls"]]["resident_mb"] += resident_mb(row["w"])
            per_cls[row["cls"]]["ktx2_bytes"] += row["bytes"] or 0

    for c in per_cls:
        per_cls[c]["resident_mb"] = round(per_cls[c]["resident_mb"], 2)
        per_cls[c]["bake_s"] = round(per_cls[c]["bake_s"], 1)

    man["schema"] = "pfa-phase6/3"
    man["gate"] = "gate2"
    man["generator"] = "export/manifest_v3.py"
    man["materials"] = dict(
        mode="pbr", uv="TEXCOORD_0",
        colorspace=dict(albedo="srgb", roughness="linear", normal="linear", occlusion="linear"),
        constant_threshold=CONSTANT_STD,
        normal_convention="tangent space, +X +Y +Z (OpenGL)",
        note="`texture` is a key into textures.gate2.files, never a path. `texture: null` with `constant: true` "
             "IS the map: apply `factor` and set no map. `factor` is the baked map's mean and is the correct "
             "value before the texture has streamed in; never multiply the texture by it. A material name that "
             "is not here keeps what the glb gave it (foliage, MAT_EXP_treeboard, MAT_water_lagoon).",
        sets=sets)

    # ---------------------------------------------------------------- the shared detail set (QA-12-1)
    detail = None
    dp = OUT / "detail.json"
    if dp.exists():
        d = json.loads(dp.read_text())
        by_src = {}
        for jid, job in jobs.items():
            for sm in job["src_materials"]:
                if d["per_material"].get(sm):
                    by_src.setdefault(job["group"], {})[sm] = d["per_material"][sm]
        detail = dict(
            mode="object_space_tiled", ship_px=d["ship_px"], bump_distance_m=d["bump_distance_m"],
            normal_derivation="n = normalize(-dh/dx, -dh/dy, 1) with h = Distance * H metres, differentiated "
                              "at the SOURCE resolution and the normal reduced afterwards; k = Distance / "
                              "m_per_texel is recorded per set",
            albedo_ratio="albedo_sampled / mean_linear, no smoothing; the KTX2 is tagged sRGB (DFD transfer 2, "
                         "verified on disk) so the GPU returns linear and mean_linear is in that same space",
            sets={k: dict(maps={r: dict(texture=f"detail_{k}_{r}", px=v["px"],
                                        colorspace=v["colorspace"],
                                        # the viewer divides by mean_linear; a compressed texture has no
                                        # readable pixels, so the denominator has to travel here.
                                        mean_linear=v.get("mean_linear"), std_linear=v.get("std_linear"),
                                        file_mean=v.get("file_mean"), file_std=v.get("file_std"),
                                        png_bytes=v.get("bytes"))
                                for r, v in rec["maps"].items()},
                          tile_m=rec.get("tile_m_used_for_normal"))
                  for k, rec in d["sets"].items()},
            per_material={m: v for m, v in d["per_material"].items() if v},
            per_group=by_src,
            apply="uv_detail = object_position.xy * per_material.object_scale (the Blender graph's own "
                  "Texture Coordinate > Object, scaled); multiply the baked albedo by detail albedo / its "
                  "mean, take roughness from the detail map, and blend the detail normal over the baked one.",
            why="measured three ways, no map baked into a unique atlas can carry this grain: the Cycles NORMAL "
                "bake of the bump gives std 0.00167 at 2K and 0.00272 at 4K on ARCH_site__concrete_podium (it "
                "scales with the texel footprint), the same bump baked as a height and converted at the map's "
                "own resolution is flat too, and the arithmetic says why - the Bump node's Distance is 0.015 m "
                "against an atlas texel of 0.038-0.118 m. The detail images are 1.05-1.32 mm per texel in "
                "Blender, 36-110x finer, and that is where the Phase 5 surface comes from.")
        man.setdefault("materials", {})["detail"] = detail

    tex = man.setdefault("textures", {})
    tex["gate2"] = dict(
        ktx2_dir="tex_ktx2", etc1s_dir="tex_ktx2_etc1s",
        encoder="toktx --t2 --encode uastc --uastc_quality 2 --zcmp 18 --genmipmap --assign_oetf <srgb|linear>",
        etc1s_encoder="toktx --t2 --encode etc1s --clevel 2 --qlevel 128 --genmipmap (mobile timing sample only)",
        files=files, detail_files={k: dict(bytes=v, px=detail_px.get(k, 1024),
                                           resident_mb=resident_mb(detail_px.get(k, 1024)))
                                   for k, v in detail_files.items()},
        bytes=sum(v["bytes"] or 0 for v in files.values()) + sum(detail_files.values()),
        etc1s_bytes=sum(v["etc1s_bytes"] or 0 for v in files.values()),
        resident_mb=round(sum(v["resident_mb"] for v in files.values()), 2),
        per_class=per_cls,
        source_png_dir="tex")
    man["textures"] = tex

    # ---------------------------------------------------------------- the resident-memory budget
    orn_ao = 0.0
    for jid, job in jobs.items():
        if job["cls"] == g2.CLS_ORN:
            orn_ao += resident_mb(int(job["size"]))
    carried = dict(orn_ao_gate1=round(orn_ao, 2), foliage_cards=20.0,
                   detail_set=round(sum(resident_mb(detail_px.get(k, 1024)) for k in detail_files), 2))
    gate3 = dict(lightmaps_own_map=85.0, lightmap_slot_atlases=107.0, tree_impostor_atlases=267.0)
    gate2_total = tex["gate2"]["resident_mb"]
    total = round(gate2_total + sum(carried.values()) + sum(gate3.values()), 2)
    man["budget"] = dict(
        budget_mb=BUDGET_MB,
        resident_mb=dict(gate2_pbr=gate2_total, **{k: round(v, 2) for k, v in carried.items()},
                         **gate3, total=total),
        gate2_by_class={k: v["resident_mb"] for k, v in per_cls.items()},
        rule="ASTC 4x4 on the Apple GPU = 1 byte per texel, x4/3 for the mip chain (docs/briefs/phase6_budget.md)",
        levers_applied=[
            "ORN roughness at 1K for every prototype (roughness is low-frequency; the 2K->1K reduction RMS is "
            "reported per map as textures.gate2.files.*.downsample_rms)",
            "ARCH / ground roughness baked at 2K and shipped at 1K, same measurement",
            "ORN albedo at 1K for the 9 prototypes under 2 m (the budget doc's named lever)",
            "backdrop at 1K, and any map whose covered texels vary by less than %.3f ships as a factor with no "
            "texture at all" % CONSTANT_STD],
        levers_not_applied=[
            "4K for the hero-near set: measured, that set is EMPTY (cam01 stands 100 m out; the nearest group "
            "inside its frame is the backdrop lamp post at 36.2 m). The walk-near alternative - the 8 ARCH "
            "groups within 30 m of a QA station - is 44.0 MB resident per group at 4K against 12.0 MB at 2K, "
            "so +32.0 MB each and +256 MB for the eight: 1422 MB, 222 MB over budget",
            "ETC1S instead of UASTC on the backdrop: ETC1S is a PAYLOAD lever, not a memory one. Both "
            "transcode to ASTC 4x4 on this GPU, so the resident bytes are identical"],
        note="the Gate 1 projection was 1343 MB against 1200")

    uvchk = backdrop_uv_matches(gltf_have)
    man["materials"]["uv1_in_glb_source"] = dict(
        derived_from=[f"../gate1/{c}.gltf" for c in ("arch", "orn", "env", "ground")
                      if (GATE1 / f"{c}.gltf").exists()],
        meshes_with_texcoord_0=len(gltf_have), meshes_seen=len(gltf_seen),
        backdrop_uv_crosscheck=uvchk,
        note="uv1_in_glb is read back from the shipped glTF, not asserted. The backdrop cross-check compares "
             "the UV bounding box and mean in env.gltf against export/out/gate2/backdrop_uv1.npz, the layout "
             "the backdrop textures were baked against. The exporter de-duplicates vertices, so counts and "
             "means differ; the SET of distinct UV pairs does not, and glTF's top-left origin means the match "
             "is against v_gltf = 1 - v_blender.")
    if uvchk:
        bad = sorted(k for k, v in uvchk.items() if not v["ok"])
        flipped = sum(1 for v in uvchk.values() if v["v_flipped"])
        worst = min(v["match"] for v in uvchk.values())
        tc = sorted({v["texcoord"] for v in uvchk.values()})
        print(f"[manifest_v3] backdrop UV cross-check: {len(uvchk) - len(bad)}/{len(uvchk)} meshes carry the "
              f"baked layout at TEXCOORD_{'/'.join(str(i) for i in tc)} (worst distinct-UV match {worst:.5f}, "
              f"V-flipped on {flipped}/{len(uvchk)})" + (f"; MISMATCH {bad}" if bad else ""))
        assert not bad, f"env.gltf carries a different UV1 than the backdrop textures were baked against: {bad}"
        # Phase 9: the set is MIXED by design. The eight MAT_backdrop_* merges carry the ENV tile UV at
        # TEXCOORD_0 and their bake atlas at 1; `bird_white` and `lamp_post` are merged by the same Gate 1
        # rule but take no gain tile and keep the atlas at 0. So the index is stated per MESH here and per
        # material SET below - never once for "the backdrop".
        if bd_tiles:
            spans = {k: v["tile_uv_span"] for k, v in uvchk.items() if v.get("tile_texcoord") == 0}
            assert spans, "no backdrop mesh carries a second UV set: the Gate 1 export lost the tile UV"
            wide = {k: s for k, s in spans.items() if (s or 0) > 1.5}
            assert wide, ("no backdrop merge's TEXCOORD_0 leaves a single tile, so it is a packed atlas, "
                          f"not the tile UV - the two sets are swapped: {spans}")
            print(f"[manifest_v3] backdrop tile UV at TEXCOORD_0 on {len(spans)} merge(s), span "
                  f"{min(wide.values()):.2f}-{max(wide.values()):.2f} tiles on {len(wide)} of them")
            for k, v in uvchk.items():
                assert v["texcoord"] == (1 if k in spans else 0), (
                    f"{k}: the baked layout is at TEXCOORD_{v['texcoord']} but its tile UV is "
                    f"{'present' if k in spans else 'absent'} - the two sets are swapped")
    # ------------------------------------------------- which UV set the Gate 2 maps ride, per material
    # The viewer hard-coded TEXCOORD_0 for every PBR map until Phase 9 (web/src/pbr.js `t.channel = 0`).
    # Now that the backdrop merges carry the tile UV at layer 0, their baked maps ride TEXCOORD_1 and the
    # rest of the scene still rides TEXCOORD_0, so the index travels per set - READ BACK from the shipped
    # glTF by the cross-check above, never asserted.
    mesh_tc = {m: v["texcoord"] for m, v in (uvchk or {}).items()}
    for _n, _s in sets.items():
        _s["texcoord"] = 0
    for _jid, _job in jobs.items():
        _n = _job["group"]
        if _n not in sets:
            continue
        _vals = {mesh_tc[m] for m in _job["meshes"] if m in mesh_tc}
        assert len(_vals) <= 1, f"{_n}: its meshes put the bake atlas on different TEXCOORDs: {sorted(_vals)}"
        if _vals:
            sets[_n]["texcoord"] = _vals.pop()
    bd_tc = 1 if any(v == 1 for v in mesh_tc.values()) else 0
    man["materials"]["texcoord_source"] = (
        "per set: the glTF UV set the Gate 2 maps ride. `materials.uv` names the scene default; a set's "
        "own `texcoord` wins. Derived from backdrop_uv_crosscheck, which scores every TEXCOORD_n in "
        "env.gltf against the layout the bake used.")
    n_tc1 = sum(1 for _s in sets.values() if _s["texcoord"] == 1)
    print(f"[manifest_v3] texcoord 1 on {n_tc1}/{len(sets)} material sets (the backdrop merges), 0 on the rest")

    # ------------------------------------------------- the backdrop gain tiles (Phase 9)
    if bd_tiles:
        by_src = {}
        for _n, _s in sets.items():
            sm = _s.get("src_material")
            for m_ in ([sm] if isinstance(sm, str) else list(sm or [])):
                by_src.setdefault(m_, _n)
        groups, unmatched = {}, []
        for src, g in sorted(bd_tiles["groups"].items()):
            name = by_src.get(src)
            if not name:
                unmatched.append(src)
                continue
            assert int(sets[name].get("texcoord", 0)) == 1, (
                f"{name} wears a gain tile on TEXCOORD_0, so its baked maps must be on TEXCOORD_1; the "
                f"shipped glTF says {sets[name].get('texcoord')}")
            groups[name] = dict(g, src_material=src)
        assert not unmatched, (f"the backdrop tile groups name source materials with no Gate 2 set: "
                               f"{unmatched} (known: {sorted(by_src)[:12]})")
        man["backdrop_tiles"] = dict(
            schema=bd_tiles["schema"], generator=bd_tiles["generator"],
            uv=dict(tile="TEXCOORD_0", baked=f"TEXCOORD_{bd_tc}"),
            wrap="repeat", colorspace="linear", apply=bd_tiles["apply"],
            groups=groups,
            files={k: dict(key=k, w=v["w"], h=v["h"], bytes=v["bytes"], encode=v["encode"],
                           lo_bytes=v["lo"]["bytes"], lo_px=v["lo"]["px"])
                   for k, v in sorted(bd_tiles["files"].items())},
            bytes=bd_tiles["bytes"], lo_bytes=bd_tiles["lo_bytes"],
            note="each key is a row in textures.gate2.files, so it resolves through the same ktx2_dir and "
                 "the same tier plan as every other texture. The image is Non-Color: it must NOT be "
                 "sRGB-decoded. The UVs are already divided by the tile size - wrap REPEAT and no texture "
                 "transform. A material with no entry here takes no gain (gain = 1).")
        print(f"[manifest_v3] backdrop tiles: {len(groups)} group(s), {len(bd_tiles['files'])} texture(s), "
              f"{bd_tiles['bytes']} B + {bd_tiles['lo_bytes']} B half-res")

    n_uv = sum(1 for v in sets.values() if v["uv1_in_glb"])
    print(f"[manifest_v3] uv1_in_glb true for {n_uv}/{len(sets)} material sets")

    mp = OUT / "manifest.json"
    mp.write_text(json.dumps(man, indent=1) + "\n")
    print(f"[manifest_v3] {mp} {mp.stat().st_size} B; {len(sets)} material sets, {len(files)} textures, "
          f"{len(missing)} jobs missing")
    print(f"[manifest_v3] gate2 resident {gate2_total} MB, ktx2 {tex['gate2']['bytes']} B; "
          f"projected total {total} MB against {BUDGET_MB} MB")
    for c, v in sorted(per_cls.items()):
        print(f"[manifest_v3]   {c:9s} maps={v['maps']:3d} resident={v['resident_mb']:8.2f} MB "
              f"ktx2={v['ktx2_bytes']:11d} B bake={v['bake_s']:8.1f} s")
    assert man["lightmap_encoding"]["rgbm_range"], "lightmap_encoding.rgbm_range lost in the carry"
    assert man["textures"]["schema"], "textures.schema lost in the carry"
    if missing:
        print(f"[manifest_v3] WARNING jobs with no bake record: {missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
