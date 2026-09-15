#!/usr/bin/env python3
"""Gate 1 step 5c: finish export/out/gate1/manifest.json as schema `pfa-phase6/2`.

    python3 export/manifest_v2.py

The geometry half (assets, meshes, stations, sun, water, totals, orn_slots, tree lists) is written by
export/export_set.py -- --gate1; the packing half (glb, textures) by export/gltf_pack.sh --gate1. This script
adds the colour half, which has not changed since Gate 0 and is NOT re-derived here: `view`, `lut`, `sky`,
`compositor` and the two `reference` frames are copied from the Gate 0 manifest, with their file paths
rewritten to `../gate0/<file>` (both gates sit under export/out/ in the same checkout, and
export/sync_main.sh copies both to the MAIN checkout the viewer reads).

It also derives `instancing`: the mesh -> placement groups that EXT_mesh_gpu_instancing draws, which is the
list the viewer needs because gltfpack -mi drops node names.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = Path(os.environ.get("PFA_MAIN_ROOT", "/Users/dk/Projects/3d render blender 3rd attempt building"))
OUT = ROOT / "export" / "out" / "gate1"
CARRY = ("view", "lut", "sky", "compositor", "reference", "reference_frame", "lightmap_scale")


def gate0_manifest():
    for p in (ROOT / "export" / "out" / "gate0" / "manifest.json",
              MAIN / "export" / "out" / "gate0" / "manifest.json"):
        if p.exists():
            return json.loads(p.read_text()), p
    return None, None


def reroot(obj):
    """Rewrite Gate 0's manifest-relative file paths so they resolve from export/out/gate1/."""
    if isinstance(obj, dict):
        return {k: reroot(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [reroot(v) for v in obj]
    if isinstance(obj, str) and (obj.endswith((".cube", ".exr", ".hdr", ".png")) and not obj.startswith(("/", "../"))):
        return "../gate0/" + obj
    return obj


def main():
    mp = OUT / "manifest.json"
    man = json.loads(mp.read_text())
    g0m, g0p = gate0_manifest()
    carried = []
    if g0m:
        for k in CARRY:
            if k not in g0m:
                continue
            if k == "view":
                # the colour pipeline is frozen: the two files must agree or every parity score is wrong
                assert abs(g0m["view"]["exposure_ev"] - man["view"]["exposure_ev"]) < 1e-6, \
                    f"exposure differs: gate0 {g0m['view']['exposure_ev']} vs gate1 {man['view']['exposure_ev']}"
                assert g0m["view"]["look"] == man["view"]["look"], "look differs between the gates"
                continue
            man[k] = reroot(g0m[k])
            carried.append(k)
        man["colour_source"] = dict(gate0_manifest=str(g0p), carried=carried,
                                    note="LUT, sky equirects, compositor values and the two reference frames "
                                         "are Gate 0's, unchanged: same master_delivery.blend, same view "
                                         "transform, look and exposure (asserted).")
    else:
        man["colour_source"] = dict(gate0_manifest=None, carried=[],
                                    note="Gate 0 manifest not found; LUT/sky/compositor/reference are MISSING")

    # instancing groups: what gltfpack -mi collapses into one draw call
    inst = {}
    for name, a in man["assets"].items():
        m = man["meshes"][a["mesh"]]
        g = inst.setdefault(a["mesh"], dict(cls=m["cls"], tris=m["tris"], material=m["material"],
                                            instanced=m["instanced"], kind=m.get("kind"), placements=[]))
        g["placements"].append(name)
    man["instancing"] = {k: dict(count=len(v["placements"]), cls=v["cls"], tris=v["tris"],
                                 material=v["material"], instanced=v["instanced"], kind=v["kind"],
                                 placed_tris=v["tris"] * len(v["placements"]),
                                 objects=v["placements"] if len(v["placements"]) <= 16 else
                                 v["placements"][:16] + [f"... {len(v['placements']) - 16} more"])
                         for k, v in sorted(inst.items())}
    # ---------------------------------------------------------------- texture schema + lightmap encoding
    # Hand-off from the viewer engineer (2026-09-15): manifest v2 carried no `rgbm_range`, and the viewer's
    # own default is 7.0 - a 9x brightness error the moment a Gate 3 lightmap ships without it. The range is
    # part of the contract, not a viewer default, so it is written here (and asserted) from Gate 1 onward.
    lm_range = 64
    g0tex = (g0m or {}).get("textures", {})
    for v in g0tex.values():
        if isinstance(v, dict) and "rgbm_range" in v:
            lm_range = v["rgbm_range"]
            break
    man["lightmap_encoding"] = dict(
        encoding="RGBM8", rgbm_range=lm_range, decode="rgb = texel.rgb * texel.a * rgbm_range",
        colorspace="NoColorSpace", uv="UV2 / TEXCOORD_1", lightmap_scale=man.get("lightmap_scale"),
        slot_atlas=dict(atlas_px=4096, slot_px=256),
        note="Gate 0 measured 0 source texels above %d on every slice map; worst RGBM8 round-trip 4.8 %%%% "
             "relative at p99. A viewer that falls back to any other range is wrong by that ratio." % lm_range)
    tex = man.setdefault("textures", {})
    if not isinstance(tex, dict):
        tex = {}
    tex["schema"] = dict(
        per_map="each baked map is an entry {path, uv, colorspace, encoding}; a lightmap entry ALSO carries "
                "rgbm_range and decode, and names its `exr` source",
        required_on_lightmaps=["rgbm_range", "decode"],
        rgbm_range_default_is_not_allowed="the viewer must read rgbm_range from the manifest, never default it")
    for k, v in list(tex.items()):
        if isinstance(v, dict) and "lightmap" in k.lower():
            v.setdefault("rgbm_range", lm_range)
            v.setdefault("decode", "rgb = texel.rgb * texel.a * rgbm_range")
    missing_range = [k for k, v in tex.items()
                     if isinstance(v, dict) and "lightmap" in k.lower() and "rgbm_range" not in v]
    assert not missing_range, f"lightmap textures without rgbm_range: {missing_range}"
    man["textures"] = tex

    # slot layout: re-derived from export/gate1_common.slot_uv so the manifest can never disagree with the
    # export set about the gutter (review finding 3).
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import gate1_common as g1c
    n_slot = 0
    for pool, rows in man.get("orn_slots", {}).items():
        for r in rows:
            atlas, slot, off, scale = g1c.slot_uv(r["atlas"] * g1c.ORN_ATLAS_SLOTS + r["slot"])
            r["uv2_offset"], r["uv2_scale"] = off, scale
            a = man["assets"].get(r["object"])
            if a and a.get("lightmap", {}).get("mode") == "slot":
                a["lightmap"].update(uv2_offset=off, uv2_scale=scale,
                                     gutter_px=g1c.ORN_ATLAS_GUTTER_PX, slot_px=g1c.ORN_ATLAS_SLOT_PX)
                n_slot += 1
    man["lightmap_encoding"]["slot_atlas"] = dict(
        atlas_px=g1c.ORN_ATLAS_PX, slot_px=g1c.ORN_ATLAS_SLOT_PX, gutter_px=g1c.ORN_ATLAS_GUTTER_PX,
        usable_px=g1c.ORN_ATLAS_SLOT_PX - g1c.ORN_ATLAS_GUTTER_PX,
        uv2_scale=(g1c.ORN_ATLAS_SLOT_PX - g1c.ORN_ATLAS_GUTTER_PX) / float(g1c.ORN_ATLAS_PX),
        note="each instance samples the inner 248 px of its 256 px slot; the 4 px border on every side keeps "
             "the Gate 3 bake margin, bilinear taps and the mip chain off the neighbouring instance")
    man["slot_layout_source"] = "export/gate1_common.slot_uv"
    print(f"[manifest_v2] slot layout re-derived for {n_slot} instances, gutter "
          f"{g1c.ORN_ATLAS_GUTTER_PX} px, uv2_scale "
          f"{man['lightmap_encoding']['slot_atlas']['uv2_scale']:.6f}")

    # uv1_in_glb: the ten merged backdrop meshes had no UV layer at Gate 1; the Gate 2 bake generated one and
    # export/gltf_gate1.py now writes it back as TEXCOORD_0 from export/out/gate2/backdrop_uv1.npz, so the flag
    # is true for every exported mesh. (The same flag in the bake engineer's export/out/gate2/manifest.json is
    # theirs to write - the ten names are in gltf_gate1.json's `backdrop_uv1`.)
    gl = json.loads((OUT / "gltf_gate1.json").read_text()) if (OUT / "gltf_gate1.json").exists() else {}
    from_gate2 = set((gl.get("backdrop_uv1") or {}).get("meshes", {}))
    missing_uv1 = set(((json.loads((OUT / "export_set.json").read_text()).get("uv_missing") or {})
                       .get("uv1") or []))
    n_true = 0
    for mn, m in man.get("meshes", {}).items():
        has = (mn not in missing_uv1) or (mn in from_gate2)
        m["uv1_in_glb"] = bool(has)
        m["uv1_source"] = "gate2 backdrop_uv1.npz" if mn in from_gate2 else "gate1 smart project"
        n_true += int(has)
    man["uv1_in_glb"] = dict(meshes_true=n_true, meshes_total=len(man.get("meshes", {})),
                             from_gate2=sorted(from_gate2),
                             note="the ten backdrop meshes carry the Gate 2 bake's own UV1 loop layer, read "
                                  "back from export/out/gate2/backdrop_uv1.npz with the loop count asserted")
    print(f"[manifest_v2] uv1_in_glb true on {n_true}/{len(man.get('meshes', {}))} meshes "
          f"({len(from_gate2)} from the Gate 2 npz)")

    man["schema"] = "pfa-phase6/2"
    mp.write_text(json.dumps(man, indent=1) + "\n")
    print(f"[manifest_v2] {mp} {mp.stat().st_size} B; carried {carried}; "
          f"{len(man['assets'])} assets, {len(man['instancing'])} instancing groups")
    print(f"[manifest_v2] lightmap_encoding.rgbm_range = {man['lightmap_encoding']['rgbm_range']}, "
          f"lightmap_scale = {man.get('lightmap_scale')}")
    missing = [k for k in ("lut", "sky", "compositor", "reference", "glb") if not man.get(k)]
    if missing:
        print(f"[manifest_v2] WARNING empty blocks: {missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
