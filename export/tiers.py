#!/usr/bin/env python3
"""6b Gate 5 items B and C: the load tiers, the per-tier glb groups, and manifest v5.

    python3 export/tiers.py                 # desktop:  out/gate5/manifest.json
    python3 export/tiers.py --mobile        # and       out/gate5/manifest_mobile.json
    python3 export/tiers.py --no-pack       # re-assign tiers from the groups already on disk

No Blender, no GPU.  Reads manifest v4 (MAIN out/gate3), `visibility.json` (export/gate5_visibility.py)
and the bytes on disk; writes `pfa-phase6/5` - everything v4 has, plus `tiers` and `files`.

What a tier is
  tier 0  what the HERO station's first frame needs, within 50 MB: arch.glb and ground.glb (already
          small and already the building), placeholder ORN and ENV groups cut to the hero-visible nodes
          with half-resolution ETC1S textures, the LUT, the three sky equirects, the impostor atlases
          the far trees are drawn from, and the hero materials' Gate 2 maps at half resolution.  No
          lightmaps, no probe, no detail set: the first frame is allowed to be a placeholder (the
          user's decision, docs/decisions.md 2026-09-18), the progress readout says so, and tier 1
          sharpens it.
  tier 1  the full look at the hero: the full-resolution Gate 2 maps for the hero's materials, their
          lightmaps, the probe, the detail set, the foliage cards, and the ORN / ENV groups at LOD0
          with their own textures, in hero-visibility order.
  tier 2  everything the hero never sees, in the order of stations 2-6: the far ENV groups, the
          backdrop, the remaining Gate 2 maps and lightmaps, and the three lazy foliage glbs.

Every published file is <= 25 MiB (Cloudflare Pages).  Only `orn.glb` (154 253 424 B) and `env.glb`
(38 119 568 B) are over it, and both are replaced by per-tier groups; anything that still cannot be
split is listed in `tiers.oversize` with the reason.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate5_common as G
import gate5_split
import gate5_tex

GLTFPACK = str(G.MAIN / "tools/bin/gltfpack")
# gltf_pack.sh's Gate 3 flags per class, so a group is packed exactly as its class was, plus `-tr`.
#
# `-tr` (keep referring to the original texture paths) is the difference between a tier split that
# works and one that inflates the payload.  Measured on the first desktop cut, with the Gate 1 maps
# EMBEDDED as gltf_pack.sh embeds them: the 16 ENV groups came to 180.3 MB against env.glb's 38.1 MB,
# because gltfpack embeds a copy of every map into every group that reaches it and the bark, leaf and
# needle sets are shared by most of them.  With `-tr` a group is geometry only (env_g06: 11 100 000 B
# -> 409 892 B), each map is published once, and a map can be given its own tier.  This is the same
# flag env_trees.glb and env_shrubs.glb already ship with, so it is a path the viewer already loads.
# The group .gltf is written INTO the groups directory so that gltfpack, which rewrites a kept URI
# relative to the OUTPUT file, leaves `../../gate1/tex_ktx2/x.ktx2` exactly as the published layout
# needs it (out/gate5/groups/*.glb beside out/gate1/tex_ktx2/*.ktx2).
# The mobile fallback: ARCH and ORN have NO LOD1 in the export set (the Gate 1 set is LOD0, and
# `orn_lo_from_lod1` covers only the three attic panels), so the brief's "else the decimated LOD0 at
# half the Gate 1 budget" applies: gltfpack's own simplifier at ratio 0.5, which is CPU and needs no
# Blender.  ENV is already exported at _LOD1 / _LOD2 and ground is the terrain and the lagoon bed,
# where a simplifier would move the shoreline, so neither is simplified.  Which of the two routes each
# class took is recorded per group as `lod_route`.
MOBILE_SIMPLIFY = dict(arch=0.5, orn=0.5)
PACK_FLAGS = dict(arch=["-cc", "-mi", "-vpf", "-km", "-kv", "-tr"],
                  env=["-cc", "-mi", "-vpf", "-km", "-kv", "-vc", "16", "-tr"],
                  orn=["-cc", "-mi", "-kv", "-tr"],
                  ground=["-cc", "-mi", "-kv", "-tr"])


def pack(gltf, glb, cls, log, simplify=None):
    t0 = time.time()
    flags = list(PACK_FLAGS[cls]) + (["-si", str(simplify)] if simplify else [])
    r = subprocess.run([GLTFPACK, "-i", str(gltf), "-o", str(glb)] + flags,
                       capture_output=True, text=True)
    log.write(f"$ gltfpack -i {gltf} -o {glb} {' '.join(flags)}\n{r.stdout}{r.stderr}\n")
    if r.returncode != 0:
        raise RuntimeError(f"gltfpack refused {gltf}:\n{r.stderr[-1000:]}")
    return time.time() - t0


def glb_image_uris(path):
    """The external texture URIs a packed group refers to (`-tr`), read back OUT of the glb."""
    b = Path(path).read_bytes()
    assert b[:4] == b"glTF", f"{path} is not a glb"
    ln = int.from_bytes(b[12:16], "little")
    doc = json.loads(b[20:20 + ln])
    return [im["uri"] for im in doc.get("images", []) if im.get("uri")]


# ------------------------------------------------------------------ which node belongs to which group
def class_nodes(cls):
    doc = json.loads((G.GATE1 / f"{cls}_ktx2.gltf").read_text())
    mesh_name = {i: (doc["meshes"][n["mesh"]].get("name") if "mesh" in n else None)
                 for i, n in enumerate(doc["nodes"])}
    return [(n["name"], mesh_name[i]) for i, n in enumerate(doc["nodes"])], doc


def group_by_mesh(nodes, vis, order):
    """Prototypes (unique meshes) ordered by how much of the HERO frame they cover, then by the first
    station that sees them.  A mesh is never split across groups: gltfpack instances within a group,
    so a mesh in two groups would be two copies of the geometry."""
    by_mesh = defaultdict(list)
    for name, mesh in nodes:
        by_mesh[mesh].append(name)
    score = {}
    for mesh, names in by_mesh.items():
        hero = sum((vis["assets"].get(n) or {}).get("hero", 0.0) for n in names)
        first = min((order.index((vis["assets"].get(n) or {}).get("first_station"))
                     if (vis["assets"].get(n) or {}).get("first_station") in order else len(order)
                     for n in names), default=len(order))
        score[mesh] = (-hero, first, mesh)
    return by_mesh, sorted(by_mesh, key=lambda m: score[m]), score


def make_group(cls, gid, names, out, man, cap, log, lowres_dir=None, drop_normals=True,
               tier=None, extra=None, vis=None, simplify=None):
    """Split, pack and measure ONE group; returns its record (`over_cap` if it still does not fit)."""
    gdir = Path(out) / "groups"
    gdir.mkdir(parents=True, exist_ok=True)
    gltf = gdir / f"{gid}.gltf"
    rep = gate5_split.split(cls, gltf, names, manifest=man, drop_gate1_normals=drop_normals,
                            image_dir=lowres_dir)
    glb = gdir / f"{gid}.glb"
    wall = pack(gltf, glb, cls, log, simplify=simplify)
    gltf.unlink(missing_ok=True)          # regenerable, and never published
    size = glb.stat().st_size
    hero = sum((vis["assets"].get(n) or {}).get("hero", 0.0) for n in names) if vis else 0.0
    st = {}
    if vis:
        for n in names:
            for s, f in ((vis["assets"].get(n) or {}).get("by_station") or {}).items():
                st[s] = round(st.get(s, 0.0) + f, 6)
    rec = dict(id=gid, path=f"groups/{gid}.glb", cls=cls, bytes=size, nodes=len(names),
               assets=sorted(names), hero_fraction=round(hero, 6), station_visibility=st,
               over_cap=size > cap, pack_s=round(wall, 1),
               dropped_gate1_normals=rep["dropped_gate1_normals"],
               lod_route=("gltfpack -si %.2f of the Gate 1 LOD0 (no LOD1 in the export set)" % simplify
                          if simplify else "the Gate 1 export set as it is"),
               textures=[os.path.normpath(os.path.join("groups", u)) for u in glb_image_uris(glb)])
    if tier is not None:
        rec["tier"] = tier
    rec.update(extra or {})
    print(f"[tiers] {gid}: {len(names)} nodes, {size/1e6:.2f} MB, {len(rec['textures'])} external "
          f"textures, hero {hero*100:.2f} %" + (f" (tier {tier})" if tier is not None else ""),
          flush=True)
    return rec


def build_groups(cls, vis, order, out, man, cap, log, prefix=None, lowres_dir=None, simplify=None):
    """One group per TIER per class, re-cut only if a group does not fit under `cap`.

    With `-tr` a group is geometry alone, so the cap is not what shapes the cut any more: tier 1 is
    every mesh the hero sees, tier 2 is the rest (ordered by the first station that sees it), and the
    viewer gets one request per tier per class instead of a dozen."""
    nodes, doc = class_nodes(cls)
    by_mesh, ordered, score = group_by_mesh(nodes, vis, order)
    prefix = prefix or cls
    buckets = {1: [], 2: []}
    for mesh in ordered:
        buckets[1 if -score[mesh][0] > 0 else 2].append(mesh)
    recs = []
    for tier, meshes in sorted(buckets.items()):
        if not meshes:
            continue
        queue = [meshes]
        i = 0
        while queue:
            part = queue.pop(0)
            gid = f"{prefix}_t{tier}" + (f"_g{i:02d}" if (i or queue) else "")
            rec = make_group(cls, gid, [n for m in part for n in by_mesh[m]], out, man, cap, log,
                             tier=tier, vis=vis, lowres_dir=lowres_dir, simplify=simplify,
                             extra=dict(meshes=sorted(part)))
            if rec["over_cap"] and len(part) > 1:
                (Path(out) / "groups" / f"{gid}.glb").unlink(missing_ok=True)
                half = max(1, len(part) // 2)
                queue.insert(0, part[half:])
                queue.insert(0, part[:half])
                log.write(f"# {gid} came out at {rec['bytes']} B > cap {cap}; re-cut\n")
                continue
            recs.append(rec)
            i += 1
    return recs


def rebase_gate3_paths(man):
    """v4's paths are relative to out/gate3; v5 lives in out/gate5, so the gate3-relative ones are
    rewritten.  Everything already written as `../gate0/...`, `../gate1/...` or `../gate2/...` is a
    sibling path and is left alone.  Recorded in `tiers.path_rebase` - never a silent rewrite."""
    moved = {}

    def to3(v, where):
        if isinstance(v, str) and v and not v.startswith("../") and not v.startswith("/"):
            moved[where] = v
            return "../gate3/" + v.replace("out/gate3/", "")
        return v

    man["textures"]["gate3"]["ktx2_dir"] = to3(man["textures"]["gate3"]["ktx2_dir"],
                                               "textures.gate3.ktx2_dir")
    man["probe"]["dir"] = to3(man["probe"]["dir"], "probe.dir")
    for k in ("hdr", "exr"):
        if man["sky"]["diffuse"].get(k):
            man["sky"]["diffuse"][k] = to3(man["sky"]["diffuse"][k], f"sky.diffuse.{k}")
    fol = man["materials"].get("foliage") or {}
    if fol.get("dir"):
        moved["materials.foliage.dir"] = fol["dir"]
        fol["dir"] = "../gate3/" + fol["dir"].replace("out/gate3/", "")
    for blk, key in ((man["trees"].get("far_mesh"), "trees.far_mesh.glb"),
                     (man["trees"].get("walkup_mesh"), "trees.walkup_mesh.glb"),
                     (man["shrubs"].get("lod1"), "shrubs.lod1.glb")):
        if blk and blk.get("glb") and "/" not in blk["glb"]:
            moved[key] = blk["glb"]
            blk["glb"] = "../gate1/" + blk["glb"]
    return moved


def resident_mb(px, mips=True, uncompressed=False):
    """The budget doc's rule: ASTC 4x4 on this GPU (and on the A18 Pro) is 1 byte per texel, x4/3 for
    the mip chain; an rgbm8 / rgba8 variant is uncompressed RGBA8 at 4 bytes per texel."""
    b = px * px * (4 if uncompressed else 1) * (4 / 3 if mips else 1)
    return b / 1e6


def assign_and_write(man, vis, order, out, groups, cap, lowres, imp_keys, variant, out_name):
    """Give every published file a tier and write the v5 manifest.

    `variant` is "desktop" or "mobile".  The MOBILE pass publishes the half-resolution ETC1S copy of
    every texture that has one (the same `tex_lo` files tier 0 already uses - the encoding the mobile
    fallback asks for IS the tier-0 encoding, so there is no third texture set), drops the three lazily
    loaded foliage glbs, and reports the ASTC-rule resident estimate per class."""
    mobile = variant == "mobile"
    files = G.resolve_files(man)
    idx = G.material_index(man)
    hero_mats, hero_keys = gate5_tex.tier0_texture_keys(man, vis)
    hero_tex = {k for k, _ in hero_keys}

    # The first station that sees a material set - the tier-2 ordering key for its Gate 2 maps.
    first_st = {}
    for name, x in vis["assets"].items():
        mat = (man["assets"].get(name) or {}).get("material")
        s = G.set_of(man, idx, mat) if mat else None
        st = x.get("first_station")
        if not s or st not in order:
            continue
        if s not in first_st or order.index(st) < order.index(first_st[s]):
            first_st[s] = st
    # How much of the HERO frame a material set covers - the within-tier order for its Gate 2 maps, so
    # tier 1 sharpens the foreground first.  A set the hero never sees falls back to the first station
    # that does see it, which is the tier-2 order.
    mat_hero = defaultdict(float)
    for name, x in vis["assets"].items():
        mat = (man["assets"].get(name) or {}).get("material")
        s = G.set_of(man, idx, mat) if mat else None
        if s:
            mat_hero[s] += x["hero"]
    tex_order = {}
    for s in man["materials"]["sets"]:
        key_order = (-mat_hero[s] if mat_hero[s] > 0
                     else order.index(first_st[s]) if s in first_st else 99)
        for slot in ("albedo", "roughness", "normal"):
            e = man["materials"]["sets"][s].get(slot)
            if isinstance(e, dict) and e.get("texture"):
                tex_order[e["texture"]] = min(tex_order.get(e["texture"], 99), key_order)

    man5 = json.loads(json.dumps(man))
    rebased = rebase_gate3_paths(man5)
    entries = []
    base = out
    lr = json.loads((out / "lowres.json").read_text()) if (out / "lowres.json").exists() else {}
    lr_px = {k: v.get("px") for blk in lr.values() if isinstance(blk, dict)
             for k, v in (blk.get("files") or {}).items() if isinstance(v, dict)}

    def put(path, tier, kind, why, order_key=0, key=None, px=None):
        entries.append(dict(path=os.path.normpath(str(path)), tier=tier, kind=kind, why=why,
                            order=order_key, key=key, px=px))

    def mobile_swap(pub):
        """The half-resolution ETC1S copy of a texture, when one exists."""
        f = lowres / f"{pub.key}.ktx2" if pub.key else None
        if mobile and f and f.exists():
            return os.path.relpath(f, str(base)), lr_px.get(pub.key), True
        return os.path.relpath(pub.path, str(base)), None, False

    swapped = 0
    for p_, pub in sorted(files.items()):
        rel, px, did = mobile_swap(pub)
        swapped += 1 if did else 0
        kind = pub.kind + ("_half" if did else "")
        if pub.kind == "glb":
            continue                      # replaced by the groups (arch/ground handled below)
        if pub.kind == "lut":
            put(rel, 0, kind, "colour from the first frame", key=pub.key)
        elif pub.kind == "sky":
            put(rel, 0, kind, "background + PMREM + diffuse environment", key=pub.key)
        elif pub.kind == "probe":
            put(rel, 1, kind, "water's fallback environment; the planar reflector carries the hero",
                key=pub.key)
        elif pub.kind == "gate2":
            hero = pub.key in hero_tex
            put(rel, 0 if (mobile and hero) else 1 if hero else 2, kind,
                "hero material" if hero else "not seen from the hero",
                order_key=tex_order.get(pub.key, 99), key=pub.key, px=px)
        elif pub.kind == "detail":
            put(rel, 1, kind, "shared object-space detail set (QA-12-1)", key=pub.key, px=px)
        elif pub.kind in ("lightmap", "lightmap_atlas"):
            put(rel, 1, kind, "the baked light; tier 0 ships none", key=pub.key, px=px)
        elif pub.kind == "impostor":
            put(rel, 0 if mobile else 1, kind,
                "the far trees are drawn from these atlases", key=pub.key, px=px)
        elif pub.kind == "foliage":
            put(rel, 1, kind, "tinted leaf cards", key=pub.key, px=px)
        elif pub.kind == "gate1tex":
            put(rel, 1, kind, "Gate 1 map a material set still points at", key=pub.key, px=px)
        elif pub.kind == "glb_lazy":
            if mobile:
                continue                  # impostors for ALL far trees: no near mesh, no walk-up set
            put(rel, 2, kind, "lazily loaded foliage set", key=pub.key)

    lowres_files = {}
    if not mobile:
        for cls in ("arch", "ground"):
            g = man["glb"]["per_class"][cls]
            pth = os.path.normpath(os.path.join(str(G.GATE3), g["path"]))
            put(os.path.relpath(pth, str(base)), 0, "glb",
                f"{cls}: the building itself, already under the cap", key=cls)
        for k in sorted(set(hero_tex) | set(imp_keys)):
            f = lowres / f"{k}.ktx2"
            if not f.exists():
                continue
            rel = os.path.relpath(f, str(base))
            put(rel, 0, "gate2_lo" if k in hero_tex else "impostor_lo",
                "half-resolution ETC1S placeholder, replaced in tier 1", key=k, px=lr_px.get(k))
            lowres_files[k] = dict(path=rel, bytes=f.stat().st_size, px=lr_px.get(k))

    # A group's own external textures (`-tr`) get the group's tier: published once, whichever groups
    # reach them, at the EARLIEST tier that needs them.  Read back out of the packed glb, never guessed.
    tex_tier = {}
    for g in groups:
        t = g.get("tier")
        if t is None:
            t = 1 if g["hero_fraction"] > 0 else 2
            g["tier"] = t
        put(g["path"], t, f"glb_group:{g['cls']}",
            f"{g['nodes']} nodes, hero {g['hero_fraction']*100:.2f} %", order_key=-g["hero_fraction"])
        for rel in g["textures"]:
            tex_tier[rel] = min(tex_tier.get(rel, 9), t)
    for rel, t in sorted(tex_tier.items()):
        put(rel, t, "glb_texture", "external map a glb group refers to (gltfpack -tr)")

    seen, uniq = set(), []
    for e in sorted(entries, key=lambda e: (e["tier"], e["order"], e["path"])):
        if e["path"] in seen:
            continue
        seen.add(e["path"])
        ap_ = (base / e["path"]).resolve()
        e["bytes"] = ap_.stat().st_size if ap_.exists() else None
        uniq.append(e)

    tier_bytes, tier_files, oversize = defaultdict(int), defaultdict(int), []
    for e in uniq:
        if e["bytes"] is None:
            continue
        tier_bytes[e["tier"]] += e["bytes"]
        tier_files[e["tier"]] += 1
        if e["bytes"] > cap:
            oversize.append(dict(path=e["path"], bytes=e["bytes"], tier=e["tier"],
                                 reason="single texture or container above the 25 MiB Pages cap; "
                                        "not splittable without re-baking it"))

    # ASTC-rule resident estimate per class (docs/briefs/phase6_budget.md, manifest v4 `budget.rule`).
    res = defaultdict(float)
    for e in uniq:
        if not e["path"].endswith(".ktx2"):
            continue
        px = e.get("px")
        if not px:
            g2 = man["textures"]["gate2"]["files"].get(e.get("key") or "")
            g3 = man["textures"]["gate3"]["files"].get(e.get("key") or "")
            px = (g2 or g3 or {}).get("w")
        if not px:
            continue
        cls = e["kind"].split(":")[0].replace("_half", "")
        res[cls] += resident_mb(px)
    res_total = round(sum(res.values()), 1)

    man5["schema"] = "pfa-phase6/5"
    man5["gate"] = "gate5"
    man5["variant"] = variant
    man5["generator"] = "export/tiers.py"
    man5["carried_from"] = "../gate3/manifest.json"
    man5["glb"] = dict(groups=groups, per_class_gate3=man["glb"]["per_class"],
                       total_bytes=sum(g["bytes"] for g in groups)
                       + (0 if mobile else sum(man["glb"]["per_class"][c]["bytes"]
                                               for c in ("arch", "ground"))),
                       gltfpack=man["glb"]["gltfpack"],
                       note="orn.glb (154 253 424 B) and env.glb (38 119 568 B) are NOT published: both "
                            "are over Cloudflare Pages' 25 MiB per-file cap. Their nodes ship as "
                            "`groups`, packed with the same gltfpack flags from the same gate1 .bin, so "
                            "the geometry is identical to Gate 3."
                            + ("" if mobile else " arch.glb and ground.glb ship whole."))
    man5["tiers"] = dict(
        schema="pfa-phase6/5-tiers/1", variant=variant,
        budget_bytes=dict(tier0=G.TIER0_BUDGET), per_file_cap_bytes=cap,
        host="Cloudflare Pages (25 MiB per file, unmetered bandwidth)",
        bytes={str(t): tier_bytes[t] for t in sorted(tier_bytes)},
        files={str(t): tier_files[t] for t in sorted(tier_files)},
        total_bytes=sum(tier_bytes.values()),
        tier0_within_budget=tier_bytes[0] <= G.TIER0_BUDGET,
        station_order=order, oversize=oversize, path_rebase=rebased,
        resident_estimate_mb=dict(by_kind={k: round(v, 1) for k, v in sorted(res.items())},
                                  total=res_total,
                                  rule=man["budget"]["rule"]),
        lowres=dict(dir="tex_lo",
                    encoder="toktx --t2 --encode etc1s --clevel 2 --qlevel 128 --genmipmap "
                            "--resize <half>",
                    chosen="half-resolution ETC1S: measured smaller AND lower RMS than quarter-res "
                           "UASTC on 5 of 6 sampled maps (export/out/gate5/lowres.json `probe`)",
                    use="in tier 0 the viewer loads `files[key]` for a texture key instead of the "
                        "manifest's own path and re-loads the full-resolution file when tier 1 "
                        "arrives (material hot-swap). A key with no entry here has no tier-0 variant.",
                    files=lowres_files,
                    textures_swapped=swapped),
        note="tier 0 boots the scene, tier 1 is the full look at the hero, tier 2 is everything the "
             "hero never sees, in station order. A tier-0 group is a PLACEHOLDER: the same assets "
             "arrive again in tier 1 at LOD0 with their own maps, and the viewer swaps them.")
    man5["files"] = uniq
    p = out / out_name
    p.write_text(json.dumps(man5, indent=1))
    print(f"[tiers] {variant}: " + ", ".join(
        f"t{t} {tier_bytes[t]/1e6:.1f} MB / {tier_files[t]} files" for t in sorted(tier_bytes))
        + f"; total {sum(tier_bytes.values())/1e6:.1f} MB; resident est {res_total:.0f} MB")
    print(f"[tiers] {variant}: tier 0 "
          f"{'within' if tier_bytes[0] <= G.TIER0_BUDGET else 'OVER'} the 50 MB budget; "
          f"{len(oversize)} files over the 25 MiB cap -> {p}")
    return man5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(G.OUT))
    ap.add_argument("--mobile", action="store_true")
    ap.add_argument("--no-pack", action="store_true")
    ap.add_argument("--cap", type=int, default=G.CAP_BYTES)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    man = G.manifest()
    vis = G.visibility(out / "visibility.json")
    order = G.station_order(man, vis)
    lowres = out / "tex_lo"
    log = open(out / "gltfpack.log", "a" if a.mobile else "w")

    # ------------------------------------------------- the low-resolution copies the tiers need
    # The ORN/ENV groups reach their Gate 1 maps by URI (`-tr`); tier 0 needs half-resolution ETC1S
    # copies of exactly those, and of the impostor atlases the far trees are drawn from.  The MOBILE
    # manifest needs one for every texture there is - the same encoding, so the same directory.
    need = set()
    for cls in ("orn", "env"):
        doc = json.loads((G.GATE1 / f"{cls}_ktx2.gltf").read_text())
        for im in doc["images"]:
            if im.get("uri"):
                need.add(Path(im["uri"]).stem)
    imp_keys = set()
    for proto, v in man["impostors"]["prototypes"].items():
        for slot in ("albedo", "normal_depth"):
            if v.get(slot):
                imp_keys.add(v[slot])
    if a.mobile:
        need |= {pub.key for pub in G.resolve_files(man).values()
                 if pub.key and pub.kind in ("gate2", "detail", "lightmap", "lightmap_atlas",
                                             "foliage", "gate1tex")}
    todo = sorted({k for k in need | imp_keys
                   if k and not (lowres / f"{k}.ktx2").exists() and G.png_source(k, man)})
    if todo and not a.no_pack:
        rep = gate5_tex.encode_set(todo, man, lowres, "etc1s", 2, "etc1s /2")
        lr_p = out / "lowres.json"
        lr = json.loads(lr_p.read_text()) if lr_p.exists() else {}
        lr.setdefault("groups_and_mobile", dict(files={}, wall_s=0.0))
        lr["groups_and_mobile"]["files"].update(rep["files"])
        lr["groups_and_mobile"]["wall_s"] = round(
            lr["groups_and_mobile"]["wall_s"] + rep["wall_s"], 1)
        lr["groups_and_mobile"]["missing"] = rep["missing"]
        lr_p.write_text(json.dumps(lr, indent=1))

    # ------------------------------------------------------------------------------- the glb groups
    gfile = out / ("groups_mobile.json" if a.mobile else "groups.json")
    if not a.no_pack:
        if not a.mobile:
            shutil.rmtree(out / "groups", ignore_errors=True)
        groups = build_all_groups(man, vis, order, out, a.cap, lowres, log, a.mobile)
        gfile.write_text(json.dumps(dict(groups=groups), indent=1))
    else:
        groups = json.loads(gfile.read_text())["groups"]
    log.close()

    assign_and_write(man, vis, order, out, groups, a.cap, lowres, imp_keys,
                     "mobile" if a.mobile else "desktop",
                     "manifest_mobile.json" if a.mobile else "manifest.json")


def build_all_groups(man, vis, order, out, cap, lowres, log, mobile):
    """The tier-0 placeholders and the tier-1/2 groups, desktop or mobile."""
    groups = []
    hero_orn = sorted(n for n, x in vis["assets"].items()
                      if x["hero"] > 0 and (man["assets"].get(n) or {}).get("cls") == "ORN")
    env_nodes = {n for n, _ in class_nodes("env")[0]}
    hero_env = sorted(n for n, x in vis["assets"].items()
                      if x["hero"] > 0 and n in env_nodes and "treeboard" not in n)
    if mobile:
        # The mobile set has no full-resolution second copy to swap to, so there is no placeholder
        # tier-0 group: the tier-1 groups ARE the mobile geometry and tier 0 takes the hero ones.
        for cls in ("arch", "ground", "orn", "env"):
            groups += build_groups(cls, vis, order, out, man, cap, log, prefix=f"m_{cls}",
                                   lowres_dir=lowres, simplify=MOBILE_SIMPLIFY.get(cls))
        for g in groups:
            if g["hero_fraction"] > 0:
                g["tier"] = 0
        return groups
    for cls, names, prefix in (("orn", hero_orn, "orn_t0"), ("env", hero_env, "env_t0")):
        groups.append(make_group(
            cls, prefix, names, out, man, cap, log, lowres_dir=lowres, tier=0, vis=vis,
            extra=dict(placeholder=True, texture_encoding="etc1s, half resolution",
                       replaced_by=f"the tier-1 {cls} group (the same assets at LOD0 with their "
                                   f"own full-resolution maps)")))
    for cls in ("orn", "env"):
        groups += build_groups(cls, vis, order, out, man, cap, log, prefix=cls)
    return groups


if __name__ == "__main__":
    main()
