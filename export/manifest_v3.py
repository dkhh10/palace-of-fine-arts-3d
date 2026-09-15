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


def main():
    man = reroot1(json.loads((GATE1 / "manifest.json").read_text()))
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
    etc_bytes = {f.stem: f.stat().st_size for f in sorted(etc.glob("*.ktx2"))} if etc.is_dir() else {}

    files, sets = {}, {}
    per_cls = {}
    for jid, rec in sorted(recs.items()):
        job = jobs[jid]
        cls = job["cls"]
        entry = dict(job=jid, cls=cls, src_material=(job["src_materials"][0] if len(job["src_materials"]) == 1
                                                     else job["src_materials"]),
                     size=job["size"], uv1_in_glb=job["uv1_in_glb"])
        for kind, m in rec["maps"].items():
            st = m["stats"]
            mean = st.get("mean") or [0.0, 0.0, 0.0]
            std = st.get("std") or [0.0, 0.0, 0.0]
            key = f"gate2_{jid}_{kind}"
            # a normal map whose X and Y never leave the flat value carries nothing: the surface uses its
            # geometry normal and the texture is pure resident memory (measured on 6 of the 10 backdrop groups).
            constant = (max(std[:2]) if kind == "normal" else max(std)) < CONSTANT_STD
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

    tex = man.setdefault("textures", {})
    tex["gate2"] = dict(
        ktx2_dir="tex_ktx2", etc1s_dir="tex_ktx2_etc1s",
        encoder="toktx --t2 --encode uastc --uastc_quality 2 --zcmp 18 --genmipmap --assign_oetf <srgb|linear>",
        etc1s_encoder="toktx --t2 --encode etc1s --clevel 2 --qlevel 128 --genmipmap (mobile timing sample only)",
        files=files,
        bytes=sum(v["bytes"] or 0 for v in files.values()),
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
    carried = dict(orn_ao_gate1=round(orn_ao, 2), foliage_cards=20.0)
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
            "groups within 30 m of a QA station - would cost +48 MB each",
            "ETC1S instead of UASTC on the backdrop: ETC1S is a PAYLOAD lever, not a memory one. Both "
            "transcode to ASTC 4x4 on this GPU, so the resident bytes are identical"],
        note="the Gate 1 projection was 1343 MB against 1200")

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
