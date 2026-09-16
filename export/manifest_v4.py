"""Gate 3 step 5: manifest v4 (`pfa-phase6/4`). Pure python3 - no Blender, no GPU.

    python3 export/manifest_v4.py

Everything in v3 is carried verbatim from out/gate2/manifest.json; out/gate2 and out/gate3 are siblings, so the
`../gate1/` and `../gate0/` paths it already carries stay correct and only the two bare `*_dir` keys are rerooted.
The schema of the three new blocks is export/README.md "manifest.json v4"; this writer is the only thing that
fills them and it never invents a number - every value comes from a bake record, compose.json or a file on disk.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate3_common as g3  # noqa: E402

SCHEMA = "pfa-phase6/4"
QA12B_VIEWER_TEXTURE_MB = 953.5     # docs/qa_round_12b.md section 5, measured in the viewer at 1440p


def rec(jid):
    p = g3.REC / f"{jid}.json"
    return json.loads(p.read_text()) if p.exists() else None


def main():
    man = json.loads((g3.GATE2_OUT / "manifest.json").read_text())
    setj = json.loads((g3.OUT / "gate3_set.json").read_text())
    comp = json.loads((g3.OUT / "compose.json").read_text()) if (g3.OUT / "compose.json").exists() else {}
    # export/gate3_encode.py is the authoritative encode (range = the map's own max, error in stops).
    enc = (json.loads((g3.OUT / "encode.json").read_text())["maps"]
           if (g3.OUT / "encode.json").exists() else {})
    jobs = {j["id"]: j for j in g3.read_jobs()["jobs"]}

    # The export engineer applies out/gate3/lightmap_uv2.npz to the glbs and writes uv2_relay_status.json
    # beside it. Until that file exists the seven re-laid assets ship `uv2_in_glb: false` and the viewer must
    # not apply their maps. This writer never flips a flag on its own - the flag follows that file only.
    rp = g3.OUT / "uv2_relay_status.json"
    relay = json.loads(rp.read_text()) if rp.exists() else None

    def relay_flag(obj):
        """True/False from uv2_relay_status.json, or None when it says nothing about this object.
        Tolerated shapes: {"assets": {obj: bool | {"uv2_in_glb"|"applied"|"relaid": bool}}},
        the same map at the top level, or {"applied": [obj, ...]}."""
        if relay is None:
            return None
        d = relay.get("assets", relay) if isinstance(relay, dict) else {}
        e = d.get(obj) if isinstance(d, dict) else None
        if isinstance(e, bool):
            return e
        if isinstance(e, dict):
            for k in ("uv2_in_glb", "applied", "relaid", "in_glb"):
                if isinstance(e.get(k), bool):
                    return e[k]
        for k in ("applied", "relaid", "uv2_in_glb"):
            v = relay.get(k) if isinstance(relay, dict) else None
            if isinstance(v, list):
                return obj in v
        return None
    man["schema"] = SCHEMA
    man["gate"] = "gate3"
    man["generator"] = "export/manifest_v4.py"
    man["carried_from"] = "../gate2/manifest.json"
    man["textures"]["ktx2_dir"] = "../gate1/tex_ktx2"
    man["textures"]["gate2"]["ktx2_dir"] = "../gate2/tex_ktx2"
    if "etc1s_dir" in man["textures"]["gate2"]:
        man["textures"]["gate2"]["etc1s_dir"] = "../gate2/tex_ktx2_etc1s"

    ktx_dir = g3.KTX
    files, missing_ktx = {}, []

    def add_tex(key, w, h, kind, encode, mips, colorspace="linear", **extra):
        p = ktx_dir / f"{key}.ktx2"
        if not p.exists():
            missing_ktx.append(key)
            return None
        files[key] = dict(path=p.name, w=int(w), h=int(h), map=kind, colorspace=colorspace, encode=encode,
                          bytes=p.stat().st_size, mips=bool(mips),
                          resident_mb=g3.resident_mb(w, h, encode, mips), **extra)
        return key

    # ------------------------------------------------------------ lightmaps.assets
    own_rows = {r["object"]: r for r in setj["own_maps"]}
    assets = {}
    for jid, j in jobs.items():
        if j["kind"] not in ("own", "own_gate1uv2"):
            continue
        r = rec(jid)
        if r is None:
            continue
        row = own_rows[j["object"]]
        size = r["size"]
        base = r["key"]
        ka = add_tex(f"{base}_rgbm8", size, size, "lightmap", "rgbm8", True)
        kb = add_tex(f"{base}_gamma2", size, size, "lightmap", "gamma2", True)
        gate1_layout = j["kind"] == "own_gate1uv2"
        en = enc.get(base, {})
        in_glb = gate1_layout or not row["uv2_relaid"]
        flag = relay_flag(j["object"])
        if not gate1_layout and flag is not None:
            in_glb = bool(flag)
        e = dict(size=size, textures={"rgbm8": ka, "gamma2": kb}, default="gamma2",
                 range=en.get("range", r["map"]["range"]), uv2_in_glb=in_glb,
                 uv2_source="gate1" if (gate1_layout or not row["uv2_relaid"]) else "gate3_relaid",
                 uv2_coverage=row["coverage_gate1"] if gate1_layout else row["coverage"],
                 cm_per_texel=row["cm_per_texel_gate1"] if gate1_layout else row["cm_per_texel"],
                 area_m2=row["area_m2"], tris=row["tris"], bake_s=r["bake_s"],
                 exr=f"tex/{r['map']['exr']['path']}" if "exr" in r["map"] else None,
                 stats=en.get("stats", r["map"]["stats"]), signal_p99=en.get("signal_p99"),
                 roundtrip={"rgbm8": en.get("rgbm8", r["map"]["rgbm8"]["roundtrip"]),
                            "gamma2": en.get("gamma2", r["map"]["gamma2"]["roundtrip"])})
        if gate1_layout:
            e["note"] = ("diagnostic: the same asset baked on the FROZEN Gate 1 UV2 the glb still carries. "
                         "Usable today with no re-export, at the texel density that layout allows.")
            assets.setdefault("_gate1_layout", {})[j["object"]] = e
        else:
            assets[j["object"]] = e

    # ------------------------------------------------------------ lightmaps.slots
    atlases = {}
    for key, a in (comp.get("atlases") or {}).items():
        en = enc.get(key, {})
        ka = add_tex(f"{key}_rgbm8", g3.ATLAS_PX, g3.ATLAS_PX, "lightmap_atlas", "rgbm8", True)
        kb = add_tex(f"{key}_gamma2", g3.ATLAS_PX, g3.ATLAS_PX, "lightmap_atlas", "gamma2", True)
        atlases[key] = dict(pool=a["pool"], atlas=a["atlas"], atlas_px=a["atlas_px"], slot_px=a["slot_px"],
                            gutter_px=a["gutter_px"], usable_px=a["usable_px"], uv2_scale=a["uv2_scale"],
                            slots_expected=a["slots_expected"], slots_filled=a["slots_filled"],
                            slots_blank_n=a["slots_blank_n"],
                            textures={"rgbm8": ka, "gamma2": kb}, default="gamma2",
                            range=en.get("range", a["range"]),
                            stats=en.get("stats", a["stats"]), signal_p99=en.get("signal_p99"),
                            exr=f"tex/{a['exr']['path']}" if "exr" in a else None,
                            roundtrip={"rgbm8": en.get("rgbm8", a["rgbm8"]["roundtrip"]),
                                       "gamma2": en.get("gamma2", a["gamma2"]["roundtrip"])},
                            slot_check=a.get("slot_check"))

    v = comp.get("vertex") or {}
    vertex = dict(encode=v.get("encode", "none"), dtype=v.get("dtype", "float32"),
                  shape=v.get("shape", "(n_verts, 3)"), units=v.get("units"),
                  attribute="COLOR_0", in_glb=False,
                  npz=v.get("npz"), bytes=v.get("bytes"), meshes_n=v.get("meshes"), verts=v.get("verts"),
                  decode=("none: the npz holds the baked values themselves, scene-linear RGB, same units as "
                          "a decoded lightmap texel. irradiance = value * lightmaps.scale (pi). How COLOR_0 "
                          "is quantised in the glb is the exporter's call, made on these numbers."),
                  meshes={r["mesh"]: dict(verts=r["verts"], min=r.get("min"), max=r["max"], mean=r["mean"],
                                          mean_nonzero=r.get("mean_nonzero"), p99=r.get("p99"),
                                          roundtrip=r["roundtrip"]) for r in v.get("rows", [])},
                  note=("`in_glb: false` until env.glb is re-exported with COLOR_0. Until then the near trees "
                        "stay on the PMREM path and must take their irradiance from sky.diffuse, not "
                        "sky.glossy (QA-12b-1)."))

    man["lightmaps"] = dict(
        mode="baked", uv="TEXCOORD_1", scale=g3.LIGHTMAP_SCALE,
        bake=dict(engine="CYCLES", type="DIFFUSE", direct=True, indirect=True, color=False,
                  samples=g3.SAMPLES_LM, denoiser="OPENIMAGEDENOISE",
                  rig="light_presets.apply_final_cycles (Eevee-only rigs asserted off, per job)",
                  occluders=("the Gate 1 export set PLUS the 127 real far trees and the lagoon water restored "
                             "from master_delivery.blend; the 127 billboard quads are hidden from the rays")),
        decode=dict(rgbm8="rgb = t.rgb * t.a * range", gamma2="rgb = t.rgb * t.rgb * range",
                    then="irradiance = rgb * lightmaps.scale; colorSpace = NoColorSpace in both variants"),
        uv2_relay_threshold=g3.UV2_RELAY_THRESHOLD,
        uv2_relaid=setj.get("uv2_relaid", []),
        uv2_npz="lightmap_uv2.npz",
        uv2_relay_status=("uv2_relay_status.json" if relay is not None else
                          "not written yet: every re-laid asset stays uv2_in_glb=false"),
        assets=assets,
        slots=dict(atlases=atlases,
                   note=("the per-instance uv2_offset / uv2_scale are `orn_slots`, unchanged since v2 and derived "
                         "from export/gate1_common.slot_uv; this block only names the atlas texture per pool and "
                         "atlas index. Atlas rows are laid out for the glTF UV flip (v_gltf = 1 - v_blender): "
                         "see export/gate3_compose.py, and `slot_check` is that proof read back from the PNG.")),
        vertex_irradiance=vertex)

    # ------------------------------------------------------------ impostors
    protos, imp_bytes = {}, 0
    for jid, j in jobs.items():
        if j["kind"] != "impostor":
            continue
        r = rec(jid)
        if r is None:
            continue
        p = j["prototype"]
        ka = add_tex(f"gate3_imp_{p}_albedo_{g3.IMP_SHIP_PX}", g3.IMP_SHIP_PX, g3.IMP_SHIP_PX,
                     "impostor_albedo", "gamma2", False)
        ka2 = add_tex(f"gate3_imp_{p}_albedo_{g3.IMP_ATLAS_PX}", g3.IMP_ATLAS_PX, g3.IMP_ATLAS_PX,
                      "impostor_albedo", "gamma2", False)
        # review finding 5: the normal+depth atlas is packed with `--encode uastc` (gate3_pack.sh:44), i.e.
        # ASTC 4x4, and was labelled `rgba8_unorm`. The residency was always counted right (1 B/texel); only
        # the label was wrong, and a wrong label is what a viewer writes its loader against.
        kn = add_tex(f"gate3_imp_{p}_normdepth_{g3.IMP_SHIP_PX}", g3.IMP_SHIP_PX, g3.IMP_SHIP_PX,
                     "impostor_normal_depth", "uastc_astc4x4", False)
        kn2 = add_tex(f"gate3_imp_{p}_normdepth_{g3.IMP_ATLAS_PX}", g3.IMP_ATLAS_PX, g3.IMP_ATLAS_PX,
                      "impostor_normal_depth", "uastc_astc4x4", False)
        # review finding 1: the prototype's own z = 0 is the placement datum, not the bbox bottom.
        # base_z_m comes from the job the bake was handed (gate3_set.json impostor_prototypes), or from the
        # record itself once it carries it; centre_z_m is the billboard centre above that datum.
        base_z = r["base_z_m"] if "base_z_m" in r else round(float(j["bbox_min"][2]), 4)
        top_z = r["base_z_m"] + r["bbox_m"][2] if "base_z_m" in r else round(float(j["bbox_max"][2]), 4)
        centre_z = r["centre_z_m"] if "centre_z_m" in r else round(float(r["centre"][2]), 4)
        h_above = r.get("height_above_base_m", round(top_z - max(base_z, 0.0), 4))
        assert abs((centre_z - base_z) - r["centre_above_base_m"]) < 2e-3, f"{p}: base/centre disagree"
        protos[p] = dict(albedo=ka, normal_depth=kn, albedo_2k=ka2, normal_depth_2k=kn2,
                         range=r["range"], radius_m=r["radius_m"], bbox_m=r["bbox_m"],
                         base_z_m=base_z, centre_z_m=centre_z, height_above_base_m=h_above,
                         depth_range_m=r["depth_range_m"],
                         views=r["views"], alpha_coverage=r["alpha_coverage"],
                         render_s=r["render_s"], s_per_view=r["s_per_view"],
                         bytes=sum(f["bytes"] for f in r["files"].values()),
                         roundtrip_albedo=r["files"]["albedo_1024"]["roundtrip"])
        imp_bytes += protos[p]["bytes"]
    ship = g3.IMP_SHIP_PX
    scale = ship / float(g3.IMP_ATLAS_PX)
    man["impostors"] = dict(
        mapping="octahedral", grid=g3.IMP_GRID,
        atlas_px=ship, frame_px=int(g3.IMP_FRAME_PX * scale), gutter_px=int(g3.IMP_GUTTER_PX * scale),
        inner_px=int(g3.IMP_INNER_PX * scale),
        variant_2k=dict(atlas_px=g3.IMP_ATLAS_PX, frame_px=g3.IMP_FRAME_PX, gutter_px=g3.IMP_GUTTER_PX,
                        inner_px=g3.IMP_INNER_PX, note="on disk; the budget lever is which of the two is loaded"),
        encode=dict(albedo=("gamma2 on RGB at the prototype's own `range` (rgb = t.rgb * t.rgb * range, "
                            "LINEAR oetf, NOT sRGB), straight (un-premultiplied) alpha in A"),
                    normal_depth=("rgb = world normal * 0.5 + 0.5 (Blender Z-up); A is depth about the "
                                  "BILLBOARD CENTRE, a = 0.5 there: depth_from_centre_m = "
                                  "(a - 0.5) * depth_range_m, positive away from the camera. The camera "
                                  "stand-off used at bake time is not exported and is not needed."),
                    normal_depth_note=("block compressed (UASTC -> ASTC 4x4) on purpose while `unlit` holds "
                                       "and nothing samples the normal or the depth. If the viewer ever "
                                       "shades or soft-depth-tests the impostor, repack this map lossless "
                                       "(toktx --zcmp, no --encode): +3.0 MB resident per prototype at 1K, "
                                       "+48.0 MB over the 16.")),
        lighting=("baked: Cycles Combined at the final rig, sun + sky + leaf translucency, film_transparent, "
                  f"{g3.SAMPLES_IMPOSTOR} spp + OIDN, with a camera-invisible lawn plane for the ground bounce"),
        unlit=("the atlas already holds lit radiance: draw it straight into the linear buffer before the LUT, "
               "with no lightmap, no sun and no environment term"),
        frame_lookup=("d = normalize(camera_pos - billboard_pos) in BLENDER Z-up (from a three.js dir with "
                      "(x, -z, y)); n = d / (|d.x|+|d.y|+|d.z|); if n.z >= 0 { u = n.x; v = n.y } else "
                      "{ u = (1-|n.y|)*sign(n.x); v = (1-|n.x|)*sign(n.y) }; uv01 = (u,v)*0.5+0.5; "
                      "col = round(uv01.x*(grid-1)); row = round(uv01.y*(grid-1)) counted from the BOTTOM"),
        frame_uv=("u = (col*frame_px + gutter_px + f.x*inner_px) / atlas_px; "
                  "v_from_bottom likewise with row; clamp f to [0,1] and inset by half a texel"),
        instance_rotation=("IGNORED on purpose: the lighting is baked in world space, so the frame is picked "
                           "from the world-space view direction. Two instances of one prototype differ by "
                           "scale, not silhouette."),
        placement=("s = tree_far[i].height_m / prototypes[p].height_above_base_m; the quad is a screen-facing "
                   "square of side 2*radius_m*s centred at trunk_base + (0,0, centre_z_m*s). Both heights are "
                   "measured from the prototype's OWN z = 0, the plane trunk_base maps to - NOT from the "
                   "bbox bottom: `base_z_m` is 0 for 14 of the 16 prototypes but -2.6748 m on "
                   "ENV_tree_willow_s37_LOD1 and -0.7183 m on ENV_tree_willow_s11_LOD1 (fronds that hang "
                   "below the trunk base and are buried in the Phase 5 scene). Dividing by bbox_m[2] there "
                   "made those two impostors 19 % / 6 % too small and lifted them off their trunks."),
        prototype_map=setj["impostor_prototype_map"],
        prototypes=protos,
        billboards="join on tree_far[i].prototype through prototype_map",
        note=("46 of the 127 far trees were exported against an LOD2 blob; every impostor is baked from the "
              "LOD1 mesh, which is why prototype_map exists and why there are 16 atlases, not 25."))

    # ------------------------------------------------------------ probe + sky.diffuse
    pr = rec("probe_hero")
    if pr:
        man["probe"] = dict(kind="cube", faces=list(g3.PROBE_FACES), size_px=pr["ship_px"],
                            rendered_px=pr["rendered_px"], format="rgbe .hdr (32-bit EXR kept on disk)",
                            dir="probe", station=pr["station"],
                            position_blender=pr["position_blender"], position_gltf=pr["position_gltf"],
                            axes=("faces are rendered in Blender world axes and named for the three.js axes "
                                  "after the (x, z, -y) swap; face `px` looks along three.js +X, up -Y"),
                            samples=pr["samples"], world_branch=pr["world_branch"],
                            files={k: dict(hdr=v["hdr"], bytes=v["hdr_bytes"], mean=v["mean"], max=v["max"],
                                           hdr_rel_p99=v["hdr_rel_p99"]) for k, v in pr["faces"].items()},
                            use=("fallback environment for the water plane and anything the planar Reflector "
                                 "cannot reach; NOT the diffuse environment - see sky.diffuse"))
    sk = rec("sky_diffuse")
    if sk:
        man["sky"]["diffuse"] = dict(hdr=sk["hdr"], exr=sk["exr"], w=sk["w"], h=sk["h"], branch="diffuse",
                                     bytes_hdr=sk["hdr_bytes"], rotation_deg=90.0, u_offset=0.25,
                                     stats=sk["stats"], hdr_rel_p99=sk["hdr_rel_p99"],
                                     orientation_check=dict(upper_half_mean=sk["upper_mean"],
                                                            lower_half_mean=sk["lower_mean"]),
                                     use=("PMREM source for IRRADIANCE only (scene.environment / diffuse). "
                                          "sky.glossy stays the specular PMREM and sky.camera the background. "
                                          "Anything with a lightmap or a baked impostor takes no term from it."))

    # ------------------------------------------------------------ textures.gate3 + budget
    man["textures"]["gate3"] = dict(
        ktx2_dir="tex_ktx2", files=files, missing=missing_ktx,
        encoders=dict(rgbm8="toktx --t2 --zcmp 18 --genmipmap --assign_oetf linear (lossless, RGBA8 resident)",
                      gamma2="toktx --t2 --encode uastc --uastc_quality 2 --zcmp 18 --genmipmap --assign_oetf linear",
                      impostor=("toktx --t2 --encode uastc --uastc_quality 2 --zcmp 18 --assign_oetf linear "
                                "(no mips: an octahedral atlas mips across frame boundaries). Both impostor "
                                "maps, albedo and normal+depth, go through this one encoder.")),
        bytes=sum(f["bytes"] for f in files.values()),
        resident_rule=("ASTC 4x4 on the Apple GPU (`gamma2`, `uastc_astc4x4`) = 1 byte/texel, x4/3 for the "
                       "mip chain; an `rgbm8` / `rgba8` variant is uncompressed RGBA8 = 4 bytes/texel; a "
                       "texture without mips counts x1.0"))

    def res(pred):
        return round(sum(f["resident_mb"] for k, f in files.items() if pred(k, f)), 2)

    own_mb = res(lambda k, f: f["map"] == "lightmap" and f["encode"] == "gamma2" and "_lmg1_" not in k)
    atlas_mb = res(lambda k, f: f["map"] == "lightmap_atlas" and f["encode"] == "gamma2")
    imp_mb = round(sum(files[p["albedo"]]["resident_mb"] + files[p["normal_depth"]]["resident_mb"]
                       for p in protos.values() if p["albedo"] in files and p["normal_depth"] in files), 2)
    probe_mb = round(6 * g3.PROBE_SHIP_PX * g3.PROBE_SHIP_PX * 4 * 4 / 3 / (1024 * 1024), 2) if pr else 0.0
    sky_mb = round(g3.SKY_DIFFUSE_W * g3.SKY_DIFFUSE_H * 4 * 4 / 3 / (1024 * 1024), 2) if sk else 0.0
    b = man["budget"]
    carried = {k: v for k, v in b["resident_mb"].items()
               if k not in ("total", "lightmaps_own_map", "lightmap_slot_atlases", "tree_impostor_atlases")}
    gate3 = dict(gate3_lightmaps_own=own_mb, gate3_lightmap_slot_atlases=atlas_mb,
                 gate3_tree_impostors=imp_mb, gate3_probe_cube=probe_mb, gate3_sky_diffuse=sky_mb)
    total = round(sum(carried.values()) + sum(gate3.values()), 2)
    b["resident_mb"] = dict(**carried, **gate3, total=total)
    b["gate3_reservation_mb"] = 459.0
    b["gate3_measured_mb"] = round(sum(gate3.values()), 2)
    b["gate3_vs_reservation_mb"] = round(sum(gate3.values()) - 459.0, 2)
    b["measured_viewer_baseline_mb"] = QA12B_VIEWER_TEXTURE_MB
    b["measured_total_mb"] = round(QA12B_VIEWER_TEXTURE_MB + sum(gate3.values()), 2)
    b["levers_not_applied"] = list(b.get("levers_not_applied", [])) + [
        f"impostor atlases at {g3.IMP_ATLAS_PX} px instead of {g3.IMP_SHIP_PX} "
        f"(+{round(imp_mb * 3, 2)} MB; the 2K files are on disk)",
        "lightmaps shipped as the lossless rgbm8 variant instead of gamma2 "
        f"(+{round((own_mb + atlas_mb) * 3, 2)} MB, exact instead of the measured gamma-2 error)"]
    b["note"] = ("two accountings, both reported: against this file's own carried rows the total is "
                 f"{total} MB; against the viewer's MEASURED texture residency at round 12b "
                 f"({QA12B_VIEWER_TEXTURE_MB} MB) it is {b['measured_total_mb']} MB. The budget line is "
                 f"{b['budget_mb']} MB.")

    man["gate3"] = dict(generated=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                        jobs=len(jobs), records=len(list(g3.REC.glob("*.json"))))
    p = g3.OUT / "manifest.json"
    p.write_text(json.dumps(man, indent=1) + "\n")
    print(f"[gate3] manifest v4 -> {p} ({p.stat().st_size} B), textures.gate3 {len(files)} files, "
          f"missing {len(missing_ktx)}, resident {total} MB (measured basis {b['measured_total_mb']} MB)")
    return man


if __name__ == "__main__":
    main()
