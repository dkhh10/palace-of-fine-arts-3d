"""Gate 3 step 5: manifest v4 (`pfa-phase6/4`). Pure python3 - no Blender, no GPU.

    python3 export/manifest_v4.py

Everything in v3 is carried verbatim from out/gate2/manifest.json; out/gate2 and out/gate3 are siblings, so the
`../gate1/` and `../gate0/` paths it already carries stay correct and only the two bare `*_dir` keys are rerooted.
The schema of the three new blocks is export/README.md "manifest.json v4"; this writer is the only thing that
fills them and it never invents a number - every value comes from a bake record, compose.json or a file on disk.
"""
import hashlib
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


def find(name):
    """out/gate3 in this worktree first, then the MAIN checkout (the bake branch syncs its files there)."""
    for base in (g3.OUT, g3.MAIN_ROOT / "export" / "out" / "gate3"):
        p = base / name
        if p.exists():
            return p
    return None


def instance_block():
    """`lightmaps.instance_irradiance`: the 1 379 shrub/reed placements, IN env.glb's INSTANCE ROW ORDER.

    Two inputs, neither of them this writer's: `instance_irradiance.json` (bake engineer, one scene-linear
    RGB per placement with its world `loc`) and `instance_order.json` (export/gate4_instance_order.py, the
    glb row -> placement map joined on the instance TRANSLATION - `gltfpack -mi` strips node names and
    re-orders the rows, so a name is a label, never the key). Every number below comes from one of those two
    files. Without the order file the block still ships the bake's own summaries, with
    `order_recovered: false` and no arrays: an array in the wrong order would light 1 379 shrubs with each
    other's values.
    """
    ip = find("instance_irradiance.json")
    if ip is None:
        return dict(present=False,
                    note="out/gate3/instance_irradiance.json not synced yet (bake branch, Gate 4)")
    irr = json.loads(ip.read_text())
    assert irr.get("schema") == "pfa-phase6/gate4-instance-irradiance/1", f"irr schema {irr.get('schema')!r}"
    op = find("instance_order.json")
    order = json.loads(op.read_text()) if op is not None else None
    if order is not None:
        assert order.get("schema") == "pfa-phase6/gate4-instance-order/2", f"order schema {order.get('schema')!r}"
        assert order["placements"] == irr["placements"], \
            f"order {order['placements']} placements != irradiance {irr['placements']}"
        assert order["meshes_n"] == irr["meshes_n"], "order/irradiance mesh count mismatch"
        # The counts survive a re-bake unchanged, so they prove nothing about WHICH irradiance file the row
        # order was built from, nor which env.glb (review r5, 2). Pin both by identity.
        assert order.get("irradiance_generated") == irr.get("generated"), (
            f"instance_order.json was built against instance_irradiance.json generated "
            f"{order.get('irradiance_generated')}, but the file here is {irr.get('generated')}: re-run "
            f"export/gate4_instance_order.py before the manifest")
        # `generated` did not change when the bake added `loc` to the same file, so the real pin is the
        # hash: any re-bake, however stamped, forces the join to be re-run before the manifest.
        sha = hashlib.sha256(ip.read_bytes()).hexdigest()
        assert order.get("irradiance_sha256") in (None, sha), (
            f"instance_order.json was built against a different {ip.name} (sha256 "
            f"{order.get('irradiance_sha256')[:12]}... vs {sha[:12]}...): re-run "
            f"export/gate4_instance_order.py before the manifest")
        glb = next((q for q in (g3.GATE1_OUT / order["glb"],
                                g3.MAIN_ROOT / "export" / "out" / "gate1" / order["glb"]) if q.exists()), None)
        assert glb is not None, f"instance_order.json refers to {order['glb']}, which is in no out/gate1"
        assert glb.stat().st_size == order["glb_bytes"], (
            f"instance_order.json holds the row order of a {order['glb_bytes']} B {order['glb']}, but the "
            f"file on disk is {glb.stat().st_size} B: re-dump the rows and re-run the join")
    # A harness run (positions from env.gltf BY OBJECT NAME - the join the bake review ruled out) is never
    # shipped: the block keeps the bake's summaries and drops every array, exactly as if no order existed.
    harness = order is not None and not order.get("loc_in_json")
    if harness:
        print("[manifest_v4] WARNING: instance_order.json is a PFA_INSTANCE_ORDER_HARNESS run "
              "(loc_in_json: false) - no instance_irradiance rgb array is emitted. Re-run "
              "export/gate4_instance_order.py once the re-baked JSON carries per-placement `loc`.")

    rows_of = {} if harness else {m: e["objects"] for m, e in (order or {}).get("meshes", {}).items()}
    meshes = {}
    for mesh, m in sorted(irr["meshes"].items()):
        by_obj = {p["object"]: p for p in m["placements"]}
        e = dict(n=m["n"], min=m["min"], max=m["max"], mean=m["mean"], lum_min=m["lum_min"],
                 lum_mean=m["lum_mean"], lum_max=m["lum_max"], cov_mean=m["cov_mean"])
        if mesh in rows_of:
            names = rows_of[mesh]
            assert len(names) == m["n"], f"{mesh}: {len(names)} glb rows != {m['n']} placements"
            missing = [n for n in names if n not in by_obj]
            assert not missing, f"{mesh}: glb rows with no baked placement: {missing[:5]}"
            e["rgb"] = [c for n in names for c in by_obj[n]["rgb"]]
            e["cov"] = [by_obj[n]["cov"] for n in names]
            e["glb_nodes"] = sorted({nd["gltf_node"] for nd in order["nodes"]
                                     if any(s[0] == mesh for s in nd["segments"])})
        meshes[mesh] = e

    nodes = [] if harness else [
        dict(gltf_node=nd["gltf_node"], count=nd["count"], tris=nd["tris"], material=nd["material"],
             segments=nd["segments"]) for nd in (order or {}).get("nodes", [])]
    return dict(
        encode="none", dtype="float32", encoding=irr["encoding"], units=irr["units"],
        attribute="_IRRADIANCE", json=ip.name, placements=irr["placements"], meshes_n=irr["meshes_n"],
        range_global=irr["range_global"], lum_min=irr["lum_min"], lum_mean=irr["lum_mean"],
        lum_max=irr["lum_max"], reduce=irr["reduce"],
        in_glb=False,
        delivery=("this manifest, not the glb: env.glb is unchanged (no re-pack, no COLOR_0 on the cards). "
                  "`meshes[*].rgb` is a flat float32 RGB list in that mesh's glb row order; a node's "
                  "InstancedBufferAttribute is built from `nodes[*].segments` (see `nodes_note`), not by "
                  "assuming one mesh per node."),
        decode=("irradiance = rgb * lightmaps.scale (pi) - the same units as a DECODED lightmap texel. "
                "Multiply it into the card's diffuse term in place of the sky-only ambient, never as a tint. "
                "Nothing is quantised: `range_global` is informational."),
        order=("glb" if nodes else "none"),
        order_recovered=bool(nodes),
        order_source=(dict(file=op.name, schema=order["schema"], generator=order["generator"],
                           glb=order["glb"], glb_bytes=order["glb_bytes"], method=order["method"],
                           join="instance translation (the only key gltfpack -mi leaves in the glb)",
                           loc_source=order["loc_source"], loc_in_json=order["loc_in_json"],
                           irradiance_sha256=order.get("irradiance_sha256"),
                           axis_swap=order["axis_swap"], axis_swap_check=order["axis_swap_check"],
                           tol_m=order["tol_m"], margin=order["margin"],
                           rows_matched=order["rows_matched"],
                           worst_residual_m=order["worst_residual_m"],
                           worst_margin_ratio=order["worst_margin_ratio"],
                           name_crosscheck=order.get("name_crosscheck"))
                      if order is not None else
                      "instance_order.json not written yet: run `node web/tools/instance_rows.mjs "
                      "export/out/gate1/env.glb export/out/gate3/instance_rows.json && python3 "
                      "export/gate4_instance_order.py`. No rgb array ships until it is."),
        key=("INSTANCE TRANSLATION. The object name in instance_irradiance.json is a label: gltfpack -mi "
             "drops node names and re-orders the rows, so the arrays below are ordered by the positional "
             "join in `order_source`, verified row by row against env.glb's own matrices."),
        key_bake=irr["placement_key"],
        irradiance_generated=irr.get("generated"),
        nodes=nodes,
        nodes_note=(("the viewer binds per NODE, not per mesh: gltfpack merges meshes, so a node can draw "
                     "the placements of more than one of them. `segments` is that node's rows as an ordered "
                     "[mesh, count, offset] list, `offset` being the row index into THAT mesh's own rgb/cov "
                     "array (3*offset in the flat rgb) - a mesh may own several segments in a node, so read "
                     "them with a running cursor, never one slice per mesh. Merged here: " +
                     "; ".join(f"node {n['gltf_node']} = {n['count']} rows, " +
                               " + ".join(f"{c}x{m}@{o}" for m, c, o in n["segments"])
                               for n in nodes if len(n["segments"]) > 1) +
                     ". `gltf_node` is the index into env.glb's `nodes` array (three's GLTFLoader: "
                     "parser.associations).")
                    if nodes else
                    ("no usable order file: no node binding and no rgb array. " +
                     ("the one on disk is a PFA_INSTANCE_ORDER_HARNESS run (positions by object name), "
                      "which is not shippable - re-run export/gate4_instance_order.py against the "
                      "loc-carrying instance_irradiance.json." if harness else
                      "run export/gate4_instance_order.py."))),
        dark=irr["checks"]["dark"],
        meshes=meshes)


def main():
    man = json.loads((g3.GATE2_OUT / "manifest.json").read_text())
    setj = json.loads((g3.OUT / "gate3_set.json").read_text())
    comp = json.loads((g3.OUT / "compose.json").read_text()) if (g3.OUT / "compose.json").exists() else {}
    # export/gate3_encode.py is the authoritative encode (range = the map's own max, error in stops).
    enc = (json.loads((g3.OUT / "encode.json").read_text())["maps"]
           if (g3.OUT / "encode.json").exists() else {})
    jobs = {j["id"]: j for j in g3.read_jobs()["jobs"]}

    # The export engineer applies out/gate3/lightmap_uv2.npz to the glbs and writes uv2_relay_status.json
    # (`pfa-phase6/gate3-relay/1`, export/gate3_relay_check.py) beside it, in MAIN. This writer NEVER decides
    # a flag itself: `uv2_in_glb` and `vertex_irradiance.in_glb` are read from that file and from nowhere
    # else, and stay false while it is absent. Background (docs/decisions.md 2026-09-16): gltfpack had been
    # stripping TEXCOORD_1 from every glb since Gate 1, so Gate 1's own `uv2_in_glb: true` was never true.
    rp = next((q for q in (g3.OUT / "uv2_relay_status.json",
                           g3.MAIN_ROOT / "export" / "out" / "gate3" / "uv2_relay_status.json") if q.exists()),
              None)
    relay = json.loads(rp.read_text()) if rp is not None else None
    if relay is not None:
        assert relay.get("schema") == "pfa-phase6/gate3-relay/1", f"relay schema {relay.get('schema')!r}"
    relay_uv2 = (relay or {}).get("uv2", {})
    relay_all = (relay or {}).get("uv2_all_meshes", {})
    relay_vi = (relay or {}).get("vertex_irradiance") or {}

    def relay_entry(mesh, obj):
        """The relay row for an own-map asset, by MESH name first (its own key) then by asset name."""
        for d in (relay_uv2, relay_all):
            if mesh in d:
                return d[mesh]
        for d in (relay_uv2, relay_all):
            for e in d.values():
                if e.get("asset") == obj:
                    return e
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
        ent = relay_entry(j.get("mesh", row.get("mesh", "")), j["object"])
        if ent is not None and isinstance(ent.get("uv2_in_glb"), bool):
            # For a gate3-relaid asset the flag IS the relay's. For the two `lmg1_*` diagnostics the sense is
            # inverted: they are baked on the FROZEN Gate 1 layout, so they are usable only while the glb has
            # NOT been re-laid.
            in_glb = (not ent["uv2_in_glb"]) if gate1_layout else bool(ent["uv2_in_glb"])
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
            e["note"] = ("diagnostic: the same asset baked on the FROZEN Gate 1 UV2. Usable only while the "
                         "glb still carries THAT layout - `uv2_in_glb` here is the inverse of the relay's "
                         "flag for the same mesh, and goes false the moment the re-laid UV2 is packed.")
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

    # The 988 slots are addressed by the ORN / ARCH-instance meshes' own TEXCOORD_1: if orn.glb is packed
    # without `-kv` the atlases cannot be applied at all, so the relay's per-glb count is carried here too.
    by_glb = {}
    for e in relay_all.values():
        g = by_glb.setdefault(e.get("glb", "?"), {"meshes": 0, "with_uv2": 0})
        g["meshes"] += 1
        g["with_uv2"] += 1 if e.get("uv2_in_glb") else 0
    slot_meshes = [(k, e) for k, e in relay_all.items() if e.get("glb") == "orn.glb"]
    slots_uv2 = bool(slot_meshes) and all(e.get("uv2_in_glb") for _, e in slot_meshes)

    v = comp.get("vertex") or {}
    # The npz is the hand-off (float32, unencoded). What the glb actually carries is the export engineer's
    # per-mesh gamma-2 encode of it, reported back in the relay's `vertex_irradiance` block; the manifest
    # copies that range per mesh and says how to decode COLOR_0. Empty block -> in_glb stays false.
    vi_in_glb = bool(relay_vi) and all(isinstance(r, dict) for r in relay_vi.values())
    relay_vi_range = (relay or {}).get("vertex_irradiance_range_global")
    if relay_vi_range is None and relay_vi:
        rr = {r.get("range") for r in relay_vi.values() if isinstance(r, dict)}
        relay_vi_range = rr.pop() if len(rr) == 1 else None
    assert not vi_in_glb or relay_vi_range is not None, (
        "uv2_relay_status.json says COLOR_0 is in the glb but carries no single global range; the viewer "
        "cannot pick a per-mesh one (gltfpack -mi instances primitives across trees)")
    vertex = dict(encode=v.get("encode", "none"), dtype=v.get("dtype", "float32"),
                  shape=v.get("shape", "(n_verts, 3)"), units=v.get("units"),
                  attribute="COLOR_0", in_glb=vi_in_glb,
                  npz=v.get("npz"), bytes=v.get("bytes"), meshes_n=v.get("meshes"), verts=v.get("verts"),
                  npz_decode=("none: the npz holds the baked values themselves, scene-linear RGB, same units "
                              "as a DECODED lightmap texel. irradiance = value * lightmaps.scale (pi)."),
                  glb_encode="gamma2 at ONE GLOBAL range (code = sqrt(v / range)), FLOAT_COLOR, "
                             "env.glb -vc 16",
                  # ONE number for the whole block (lead's decision after viewer round 13b): gltfpack's -mi
                  # instances primitives across trees, so the 14 baked buffers arrive as 14 primitives over
                  # 26 placements and a PER-MESH range cannot be joined back to its mesh. The per-mesh rows
                  # below still carry `range` (the same value) plus their own mean and round-trip error.
                  range=relay_vi_range,
                  range_source=("uv2_relay_status.json vertex_irradiance_range_global = the max over all 14 "
                                "near-tree meshes in vertex_irradiance.npz"),
                  glb_decode=("v = COLOR_0 * COLOR_0 * lightmaps.vertex_irradiance.range, then "
                              "irradiance = v * lightmaps.scale (pi) - exactly as a gamma2 lightmap texel. "
                              "ONE global `range` for all 14 meshes; do not look for a per-mesh one. glTF "
                              "multiplies COLOR_0 into base colour by default, so these 14 meshes must "
                              "consume it as irradiance, not as a tint."),
                  meshes={r["mesh"]: dict(verts=r["verts"], min=r.get("min"), max=r["max"], mean=r["mean"],
                                          mean_nonzero=r.get("mean_nonzero"), p99=r.get("p99"),
                                          roundtrip=r["roundtrip"],
                                          **{k: relay_vi[r["mesh"]][k]
                                             for k in ("range", "encoding", "mean_linear",
                                                       "roundtrip_rel_p99")
                                             if isinstance(relay_vi.get(r["mesh"]), dict)
                                             and k in relay_vi[r["mesh"]]})
                          for r in v.get("rows", [])},
                  note=(("COLOR_0 is in env.glb; the single global `range` comes from "
                         "uv2_relay_status.json."
                         if vi_in_glb else
                         "`in_glb: false` until env.glb is re-exported with COLOR_0 and the relay reports a "
                         "global range; this writer re-runs on that hand-off. Until then the near trees "
                         "stay on the PMREM path and must take their irradiance from sky.diffuse, not "
                         "sky.glossy (QA-12b-1).")),
                  relay_note=(relay or {}).get("vertex_irradiance_skipped"))

    instance = instance_block()

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
        uv2_relay_status=(dict(file="uv2_relay_status.json", schema=relay.get("schema"),
                               written_by=relay.get("written_by"),
                               meshes_with_uv2=sum(1 for e in relay_all.values() if e.get("uv2_in_glb")),
                               meshes_total=len(relay_all), by_glb=by_glb,
                               relaid_in_glb=sorted(e.get("asset", k) for k, e in relay_uv2.items()
                                                    if e.get("uv2_in_glb")),
                               gltfpack_flags=relay.get("gltfpack_flags"))
                          if relay is not None else
                          "not written yet: every re-laid asset stays uv2_in_glb=false"),
        assets=assets,
        slots=dict(atlases=atlases,
                   uv2_in_glb=slots_uv2 if relay is not None else False,
                   uv2_in_glb_source=("uv2_relay_status.json uv2_all_meshes, glb == orn.glb: "
                                      f"{sum(1 for _, e in slot_meshes if e.get('uv2_in_glb'))} of "
                                      f"{len(slot_meshes)} meshes carry TEXCOORD_1"
                                      if relay is not None else "relay not written yet"),
                   note=("the per-instance uv2_offset / uv2_scale are `orn_slots`, unchanged since v2 and derived "
                         "from export/gate1_common.slot_uv; this block only names the atlas texture per pool and "
                         "atlas index. Atlas rows are laid out for the glTF UV flip (v_gltf = 1 - v_blender): "
                         "see export/gate3_compose.py, and `slot_check` is that proof read back from the PNG.")),
        vertex_irradiance=vertex,
        instance_irradiance=instance)

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

    # ------------------------------------------------------------ compositor.mist (lead, viewer round 13b)
    # The carried `compositor` block records COMP_golden_hour's `Mist` INPUT as 0.0, which is only what a
    # disconnected socket's stored default reports - the live value is the Mist PASS the Render Layers node
    # feeds it, and that pass is shaped entirely by scene.world.mist_settings. export/read_mist.py reads them
    # out of master_delivery.blend (read-only, no render) into out/gate3/mist_settings.json; this copies them
    # in so the viewer has the haze ramp's real start and depth instead of a zero.
    # Review r3 finding 2: export/out/ is gitignored, so a local-only lookup would silently drop
    # `compositor.mist` after the merge (the viewer would keep the 0.0 haze and nothing would say so).
    # Same local-then-MAIN resolution as the relay json above, and it says so when neither exists.
    mp = next((q for q in (g3.OUT / "mist_settings.json",
                           g3.MAIN_ROOT / "export" / "out" / "gate3" / "mist_settings.json") if q.exists()),
              None)
    if mp is None:
        print("[gate3] WARNING: no mist_settings.json in out/gate3 or MAIN's - compositor.mist is null and "
              "the viewer has no haze ramp. Run: scripts/blender_run.sh 600 -- --background "
              "master_delivery.blend --python export/read_mist.py", file=sys.stderr)
        cb = man.get("compositor")
        man["compositor"] = dict(cb if isinstance(cb, dict) else {}, mist=None,
                                 mist_missing="mist_settings.json not found in out/gate3 or MAIN's; run "
                                              "export/read_mist.py. COMP_golden_hour's own `Mist` group "
                                              "input is a disconnected socket's 0.0 default, not the value "
                                              "the render used.")
    else:
        mj = json.loads(mp.read_text())
        assert mj.get("schema") == "pfa-phase6/gate3-mist/1", f"mist schema {mj.get('schema')!r}"
        comp_block = man.get("compositor")
        if not isinstance(comp_block, dict):
            comp_block = {}
        comp_block["mist"] = dict(**(mj.get("mist") or {}),
                                  use_pass_mist=mj.get("use_pass_mist"),
                                  units="metres (1 BU = 1 m), measured along the view ray from the camera",
                                  source="master_delivery.blend scene.world.mist_settings, "
                                         "read by export/read_mist.py",
                                  file="mist_settings.json", read_at=mj.get("source"),
                                  formula=mj.get("note"),
                                  group_input_note=("COMP_golden_hour's own `Mist` group input reads 0.0 in "
                                                    "this block: that is a disconnected socket's stored "
                                                    "default, NOT the value the render used."))
        man["compositor"] = comp_block

    man["gate3"] = dict(generated=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                        jobs=len(jobs), records=len(list(g3.REC.glob("*.json"))))
    p = g3.OUT / "manifest.json"
    p.write_text(json.dumps(man, indent=1) + "\n")
    print(f"[gate3] manifest v4 -> {p} ({p.stat().st_size} B), textures.gate3 {len(files)} files, "
          f"missing {len(missing_ktx)}, resident {total} MB (measured basis {b['measured_total_mb']} MB)")
    return man


if __name__ == "__main__":
    main()
