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

# What Cloudflare Pages compresses by default, by content type: html, css, javascript, json, plain text
# and svg.  Everything else - KTX2, glb, wasm, .hdr, and `.cube`, which Pages serves as
# application/octet-stream - is counted at its size on disk, which is what the network log will show.
# The LUT is the one file where that costs real headroom; the report says what a `_headers` rule buys.
COMPRESSIBLE_EXT = {".json", ".js", ".mjs", ".css", ".html", ".txt", ".svg", ".map"}
# The tier-0 normal maps are re-encoded at this ETC1S quality.  Measured on five of the 46 (qlevel 128 ->
# 32): 33 786 B -> 26 747 B, -20.8 %, with the RMS against the source moving by +0.00001 or less.  It is
# the cheapest room in tier 0 there is, which is why it is spent before any texture is moved out.
TIER0_NORMAL_QLEVEL = 32
# Headroom kept under the budget when the trim runs, so a manifest that grows by a few kB on the next
# run does not put the first frame back over it.
TIER0_SLACK = 500_000

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


def _glb_chunks(b):
    assert b[:4] == b"glTF", "not a glb"
    out, off = [], 12
    while off < len(b):
        ln = int.from_bytes(b[off:off + 4], "little")
        ty = b[off + 4:off + 8]
        out.append((ty, b[off + 8:off + 8 + ln]))
        off += 8 + ln
    return out


def glb_image_uris(path):
    """The external texture URIs a packed group refers to (`-tr`), read back OUT of the glb."""
    doc = json.loads(_glb_chunks(Path(path).read_bytes())[0][1])
    return [im["uri"] for im in doc.get("images", []) if im.get("uri")]


def rewrite_glb_image_uris(path, sources, pub_dir):
    """Point a packed group's external texture URIs at the PUBLISHED layout.

    gltfpack rewrites a `-tr` URI relative to the output file, so a group built in a worktree comes out
    pointing at `../../../../../../../export/out/gate1/tex_ktx2/x.ktx2` - correct on this disk, wrong on
    the web. The map is `{basename: absolute source}` from the splitter, and the URI written back is that
    source's path relative to the PUBLISHED group directory (MAIN out/gate5/groups). Matching on the
    basename, not on position: gltfpack may drop or reorder images.
    """
    b = Path(path).read_bytes()
    chunks = _glb_chunks(b)
    doc = json.loads(chunks[0][1])
    changed = []
    for im in doc.get("images", []):
        u = im.get("uri")
        if not u:
            continue
        src = sources.get(os.path.basename(u))
        if not src:
            raise RuntimeError(f"{path}: no source recorded for image uri {u}")
        # a file this worktree produced (tex_lo) is published under gate5; anything else under MAIN
        srcp = Path(src)
        if srcp.is_relative_to(G.OUT):
            pub = G.PUB_BASE / srcp.relative_to(G.OUT)
        else:
            pub = srcp
        new = os.path.relpath(pub, pub_dir)
        if new != u:
            changed.append((u, new))
        im["uri"] = new
    if not changed:
        return 0
    js = json.dumps(doc, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    out = bytearray(b"glTF") + (2).to_bytes(4, "little") + b"\0\0\0\0"
    out += len(js).to_bytes(4, "little") + chunks[0][0] + js
    for ty, data in chunks[1:]:
        pad = b"\0" * (-len(data) % 4)
        out += (len(data) + len(pad)).to_bytes(4, "little") + ty + data + pad
    out[8:12] = len(out).to_bytes(4, "little")
    Path(path).write_bytes(bytes(out))
    return len(changed)


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
    rewrite_glb_image_uris(glb, rep["image_sources"], G.PUB_BASE / "groups")
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


def build_groups(cls, vis, order, out, man, cap, log, prefix=None, lowres_dir=None, simplify=None,
                 hero_tier=1):
    """One group per TIER per class, re-cut only if a group does not fit under `cap`.

    With `-tr` a group is geometry alone, so the cap is not what shapes the cut any more: tier 1 is
    every mesh the hero sees, tier 2 is the rest (ordered by the first station that sees it), and the
    viewer gets one request per tier per class instead of a dozen."""
    nodes, doc = class_nodes(cls)
    by_mesh, ordered, score = group_by_mesh(nodes, vis, order)
    prefix = prefix or cls
    buckets = {hero_tier: [], 2: []}
    for mesh in ordered:
        buckets[hero_tier if -score[mesh][0] > 0 else 2].append(mesh)
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


def transfer_bytes(path):
    """What the network log will show for this file: gzip -9 for the types the host compresses, the
    size on disk for everything else.  gzip, not brotli: it is available here, and it OVERSTATES the
    transfer slightly, which is the right direction for a budget."""
    path = Path(path)
    if not path.exists():
        return None
    if path.suffix.lower() not in COMPRESSIBLE_EXT:
        return path.stat().st_size
    import gzip as _gz
    return len(_gz.compress(path.read_bytes(), 9))


def boot_overhead(out, man_path):
    """Everything the browser fetches before the first frame that is NOT in `files`: the page, the JS
    bundle, the KTX2 transcoder (web/src/main.js configures `setTranscoderPath('/basis/')`) and the
    manifest itself.  Measured from `web/dist` as built on main - if it is not built, the sizes are
    reported as null and the budget test says so rather than quietly passing."""
    dist = G.MAIN / "web/dist"
    items = {}
    for name, rel in (("page", "index.html"),
                      ("bundle", None),
                      ("transcoder_js", "basis/basis_transcoder.js"),
                      ("transcoder_wasm", "basis/basis_transcoder.wasm")):
        if name == "bundle":
            js = sorted((dist / "assets").glob("index-*.js")) if (dist / "assets").is_dir() else []
            pth = js[0] if js else None
        else:
            pth = dist / rel
        items[name] = dict(path=str(pth.relative_to(G.MAIN)) if pth and pth.exists() else None,
                           bytes=pth.stat().st_size if pth and pth.exists() else None,
                           transfer=transfer_bytes(pth) if pth and pth.exists() else None)
    items["manifest"] = dict(path=os.path.basename(str(man_path)),
                             bytes=Path(man_path).stat().st_size if Path(man_path).exists() else None,
                             transfer=transfer_bytes(man_path) if Path(man_path).exists() else None)
    total = sum(v["transfer"] or 0 for v in items.values())
    return dict(items=items, total=total,
                complete=all(v["transfer"] is not None for v in items.values()),
                note="web/dist is Vite's build of the viewer as it stands on main; the bundle hash "
                     "changes with every viewer change, so this is an estimate of the same order, not "
                     "a pin. `/basis/` is the path web/src/main.js gives KTX2Loader.")


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
            return G.pub_rel(f, base), lr_px.get(pub.key), True
        return G.pub_rel(pub.path, base), None, False

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
            # Lead's decision (review finding 2, 2026-09-18): the probe is tier 0. Without it the first
            # frame carries no lightmap AND no environment, so it is sky-diffuse-lit only - darker and
            # flatter than the low-resolution look the user approved, not just softer.
            put(rel, 0, kind, "the first frame's environment: tier 0 ships no lightmap, so this is the "
                              "only indirect light there is until tier 1", key=pub.key)
        elif pub.kind == "gate2":
            hero = pub.key in hero_tex
            put(rel, 0 if (mobile and hero) else 1 if hero else 2, kind,
                "hero material" if hero else "not seen from the hero",
                order_key=tex_order.get(pub.key, 99), key=pub.key, px=px)
        elif pub.kind == "detail":
            # The viewer tiles these in object space over every concrete and ground surface and binds
            # them at boot (web/src/detail.js), so at full resolution they were an unlabelled 23.3 MB
            # of tier 0. Tier 0 takes the half-resolution ETC1S copy; tier 1 restores the full set.
            put(rel, 1, kind, "full-resolution object-space detail set (QA-12-1); tier 0 carries the "
                              "half-resolution ETC1S copy", key=pub.key, px=px)
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

    # web/src/main.js resolves `uv2_relay_status.json` against the MANIFEST url, and it is the file
    # that decides which lightmap variant every own-map asset uses, so a 404 there silently changes the
    # light. It is copied beside the v5 manifest rather than left in gate3.
    relay_src = G.GATE3 / "uv2_relay_status.json"
    if relay_src.exists():
        (out / "uv2_relay_status.json").write_bytes(relay_src.read_bytes())
        put("uv2_relay_status.json", 0, "relay",
            "which lightmap layout each own-map asset actually carries; main.js fetches it beside the "
            "manifest and the manifest's own uv2_in_glb flags are only the fallback", key="uv2_relay")
        man5.setdefault("lightmaps", {}).setdefault("uv2_relay_status", {})["path"] = \
            "uv2_relay_status.json"

    lowres_files = {}
    if not mobile:
        for cls in ("arch", "ground"):
            g = man["glb"]["per_class"][cls]
            pth = os.path.normpath(os.path.join(str(G.GATE3), g["path"]))
            put(G.pub_rel(pth, base), 0, "glb",
                f"{cls}: the building itself, already under the cap", key=cls)
        detail_keys = {pub.key for pub in files.values() if pub.kind == "detail" and pub.key}
        kinds_lo = [(hero_tex, "gate2_lo"), (imp_keys, "impostor_lo"), (detail_keys, "detail_lo")]
        for keys, kind_lo in kinds_lo:
            for k in sorted(keys):
                f = lowres / f"{k}.ktx2"
                if not f.exists() or k in lowres_files:
                    continue
                rel = G.pub_rel(f, base)
                put(rel, 0, kind_lo, "half-resolution ETC1S copy, upgraded in tier 1",
                    key=k, px=lr_px.get(k))
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
    # A group's URIs name the FULL-resolution files.  Desktop publishes the half-resolution twin in the
    # group's tier (that is what the first frame fetches, through the viewer's redirect) and the full
    # file in tier 1; MOBILE publishes only the half-resolution twin, and its redirect is permanent.
    for rel, t in sorted(tex_tier.items()):
        key = os.path.basename(rel)[:-len(".ktx2")] if rel.endswith(".ktx2") else None
        lo_p = lowres / f"{key}.ktx2" if key else None
        has_lo = bool(lo_p and lo_p.exists())
        if has_lo:
            lo_rel = G.pub_rel(lo_p, base)
            put(lo_rel, t, "glb_texture_lo",
                "half-resolution ETC1S copy of a map a glb group names; the viewer redirects the "
                "group's URI here until the full file is in", key=key, px=lr_px.get(key))
            lowres_files.setdefault(key, dict(path=lo_rel, bytes=lo_p.stat().st_size,
                                              px=lr_px.get(key)))
        if not mobile or not has_lo:
            put(rel, 1 if has_lo else t,
                "glb_texture_full" if has_lo else "glb_texture",
                "the map a glb group's URI names" + (
                    "; tier 1, because tier 0 fetches the half-resolution copy instead" if has_lo
                    else "; no half-resolution copy exists, so it is fetched as it is"), key=key)
        if has_lo and not mobile:
            lowres_files[key]["full"] = rel

    if not mobile:
        for k, v in lowres_files.items():
            if "full" in v:
                continue
            pub = next((p_ for p_, q in files.items() if q.key == k), None)
            if pub:
                v["full"] = G.pub_rel(pub, base)
    seen, uniq = set(), []
    for e in sorted(entries, key=lambda e: (e["tier"], e["order"], e["path"])):
        if e["path"] in seen:
            continue
        seen.add(e["path"])
        ap_ = (base / e["path"]).resolve()
        if not ap_.exists():
            ap_ = (G.PUB_BASE / e["path"]).resolve()
        e["bytes"] = ap_.stat().st_size if ap_.exists() else None
        e["transfer"] = transfer_bytes(ap_) if ap_.exists() else None
        uniq.append(e)

    # ---- tier 0 is measured against the WHOLE first-frame payload, in TRANSFER bytes -------------
    # `boot` is what the browser fetches before frame 1 that is not in `files` (page, bundle, KTX2
    # transcoder, this manifest).  If tier 0 + boot is over the budget, the least hero-visible tier-0
    # Gate 2 placeholders are moved to tier 1, cheapest look first, and what moved is recorded.
    boot = boot_overhead(out, out / out_name)
    trim = dict(moved=[], moved_bytes=0, reason=None)
    budget_left = G.TIER0_BUDGET - boot["total"]

    def t0_transfer():
        return sum(e["transfer"] or 0 for e in uniq
                   if e["tier"] == 0 and not e.get("_drop"))

    if t0_transfer() > budget_left:
        trim["reason"] = (f"tier 0 + boot overhead ({t0_transfer() + boot['total']:,} B) is over the "
                          f"{G.TIER0_BUDGET:,} B budget")
        # least hero-visible first: a placeholder map whose material covers almost none of the hero
        # frame costs the least to leave until tier 1.
        cand = [e for e in uniq if e["tier"] == 0 and e["kind"] in ("gate2_lo", "gate2_half")]
        cand.sort(key=lambda e: (-tex_order.get(e.get("key"), 99), -(e["transfer"] or 0)))
        full_at = {e.get("key") for e in uniq if e["tier"] == 1 and e["kind"] in ("gate2", "detail")}
        dropped = []
        for e in cand:
            if t0_transfer() <= budget_left - TIER0_SLACK:
                break
            # Review r2 finding 3: MOVING the half-resolution copy to tier 1 makes tier 1 fetch half
            # AND full of the same key. When the full-resolution file is already in tier 1 the half is
            # simply DROPPED - the material is untextured until tier 1, which is the cost being paid -
            # and its `lowres.files` entry goes with it, so the contract stays true. On the mobile set
            # there is no full-resolution twin to fall back to, so there it is moved, never dropped.
            if e.get("key") in full_at and not mobile:
                e["_drop"] = True
                dropped.append(e)
                lowres_files.pop(e.get("key"), None)
            else:
                e["tier"] = 1
                e["why"] = ("moved out of tier 0 to fit the first-frame budget: its material covers "
                            "nothing of the hero frame")
            trim["moved"].append(dict(path=e["path"], key=e.get("key"), bytes=e["bytes"],
                                      transfer=e["transfer"],
                                      hero_order=tex_order.get(e.get("key")),
                                      action="dropped (the full-resolution file is in tier 1)"
                                             if e.get("_drop") else "moved to tier 1"))
            trim["moved_bytes"] += e["transfer"] or 0
        if dropped:
            uniq = [e for e in uniq if not e.get("_drop")]
        trim["dropped"] = len(dropped)
        trim["effect"] = ("the materials of these keys carry NO map until tier 1: the glb's own base "
                          "colour stands in. They were chosen because each covers less than 0.003 % "
                          "of the hero frame.")
        uniq.sort(key=lambda e: (e["tier"], e["order"], e["path"]))

    tier_bytes, tier_files, tier_transfer, oversize = (defaultdict(int), defaultdict(int),
                                                       defaultdict(int), [])
    for e in uniq:
        if e["bytes"] is None:
            continue
        tier_bytes[e["tier"]] += e["bytes"]
        tier_transfer[e["tier"]] += e["transfer"] or 0
        tier_files[e["tier"]] += 1
        if e["bytes"] > cap:
            oversize.append(dict(path=e["path"], bytes=e["bytes"], tier=e["tier"],
                                 reason="single texture or container above the 25 MiB Pages cap; "
                                        "not splittable without re-baking it"))
    first_frame = tier_transfer[0] + boot["total"]

    # Completeness: every file `resolve_files` knows about is either published, or published in its
    # half-resolution form, or deliberately dropped by this variant. The viewer treats anything it
    # fetches that is not in `files` as an error, so the plan has to be exhaustive - and this is what
    # missed the detail set the first time round.
    pub_paths = {e["path"] for e in uniq}
    unpublished = []
    for p_, pub in sorted(files.items()):
        if pub.kind == "glb":
            continue
        rel = G.pub_rel(p_, base)
        lo = lowres / f"{pub.key}.ktx2" if pub.key else None
        if rel in pub_paths:
            continue
        if lo is not None and lo.exists() and G.pub_rel(lo, base) in pub_paths:
            continue
        if mobile and pub.kind == "glb_lazy":
            continue
        unpublished.append(dict(path=rel, kind=pub.kind, key=pub.key))
    if unpublished:
        print(f"[tiers] {variant}: WARNING {len(unpublished)} viewer-reachable files are in no tier: "
              f"{[u['path'] for u in unpublished][:5]}", flush=True)

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
        transfer_bytes={str(t): tier_transfer[t] for t in sorted(tier_transfer)},
        files={str(t): tier_files[t] for t in sorted(tier_files)},
        total_bytes=sum(tier_bytes.values()),
        total_transfer_bytes=sum(tier_transfer.values()),
        boot_overhead_bytes=boot,
        first_frame_transfer_bytes=first_frame,
        tier0_trim=trim,
        unpublished=unpublished,
        tier0_within_budget=first_frame <= G.TIER0_BUDGET,
        budget_note="the budget is TRANSFER bytes as the network log sees them: gzip -9 for the types "
                    "Cloudflare Pages compresses (html, css, js, json, txt, svg), size on disk for "
                    "KTX2, glb, wasm, .hdr and .cube. `first_frame_transfer_bytes` = tier 0 + "
                    "`boot_overhead_bytes.total`, and THAT is what is tested against 50 000 000.",
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
    # (5) `lightmaps.instance_irradiance` was keyed to env.glb's node indices, which the split
    # renumbers: without this the 1 379 shrub/reed placements bind nothing and fall back to the probe.
    ig = out / "instance_order_groups.json"
    if ig.exists():
        doc = json.loads(ig.read_text())
        ii = man5["lightmaps"]["instance_irradiance"]
        ii["groups"] = {k: v for k, v in doc["groups"].items()
                        if (k.startswith("m_") == bool(mobile))}
        ii["groups_placements"] = sum(v["placements"] for v in ii["groups"].values())
        ii["groups_complete"] = ii["groups_placements"] == (ii.get("placements") or 0)
        ii["groups_join"] = (
            "env.glb is not published any more, so `nodes` (keyed to its node indices) cannot be used "
            "as it stands. `groups[<group id>]` carries the SAME entries re-numbered for that group's "
            "glb: bind under `WEB_glb_<group id>` by `mesh.userData.pfaGltfNode` exactly as "
            "web/src/lightmaps.js applyInstanceIrradiance does today, with `opts.root` set to that "
            "group's scene. `segments` is unchanged - it addresses rows inside a node by mesh name and "
            "offset, which the split cannot move. `gltf_node_env` is the old index, for tracing only. "
            "The match is row-by-row on instance translation within 0.02 m "
            "(export/gate5_instance_rows.py); `groups_complete` says every placement is covered.")
    man5["files"] = uniq
    p = out / out_name
    # The manifest is part of the payload it measures.  Write, re-measure, patch, rewrite until the
    # number stops moving: `boot`, `first_frame` and the verdict are ALL rewritten on every pass, not
    # just `boot` (review r2 finding 1 - the resync used to sit under an `if`, so the published
    # `first_frame_transfer_bytes` was one byte behind the fields it is the sum of).
    for _ in range(4):
        p.write_text(json.dumps(man5, indent=1))
        t = transfer_bytes(p)
        m_it = man5["tiers"]["boot_overhead_bytes"]["items"]["manifest"]
        if t == m_it["transfer"]:
            break
        boot["total"] += t - (m_it["transfer"] or 0)
        m_it.update(bytes=p.stat().st_size, transfer=t)
        first_frame = tier_transfer[0] + boot["total"]
        man5["tiers"]["boot_overhead_bytes"]["total"] = boot["total"]
        man5["tiers"]["first_frame_transfer_bytes"] = first_frame
        man5["tiers"]["tier0_within_budget"] = first_frame <= G.TIER0_BUDGET
    p.write_text(json.dumps(man5, indent=1))
    print(f"[tiers] {variant}: " + ", ".join(
        f"t{t} {tier_bytes[t]/1e6:.1f} MB / {tier_files[t]} files" for t in sorted(tier_bytes))
        + f"; total {sum(tier_bytes.values())/1e6:.1f} MB; resident est {res_total:.0f} MB")
    print(f"[tiers] {variant}: first frame = tier 0 {tier_transfer[0]/1e6:.2f} MB transfer + boot "
          f"{boot['total']/1e6:.2f} MB = {first_frame/1e6:.2f} MB, "
          f"{'within' if first_frame <= G.TIER0_BUDGET else 'OVER'} the 50.0 MB budget"
          + (f" (moved {len(trim['moved'])} placeholder maps out, {trim['moved_bytes']/1e6:.2f} MB)"
             if trim["moved"] else "") )
    print(f"[tiers] {variant}: {len(oversize)} files over the 25 MiB cap -> {p}")
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
    # The detail set is bound at boot on every concrete and ground surface (web/src/detail.js), so it
    # is part of the first frame whether the plan says so or not: tier 0 gets a half-resolution copy on
    # BOTH variants.  The mobile manifest swaps every texture there is.
    need |= {pub.key for pub in G.resolve_files(man).values()
             if pub.key and pub.kind == "detail"}
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
        lr.setdefault("groups_and_mobile", dict(files={}, wall_s=0.0,
                                                encoder=rep["encoder"], resize_div=rep["resize_div"],
                                                dir=rep["dir"]))
        lr["groups_and_mobile"]["files"].update(rep["files"])
        # carry (a) from the review: `wall_s` used to accumulate across runs, so the report's ETC1S
        # seconds grew every time the chain was re-run. It is now THIS run's seconds for the files this
        # run actually encoded, with the running total kept beside it and labelled.
        lr["groups_and_mobile"]["wall_s"] = rep["wall_s"]
        lr["groups_and_mobile"]["wall_s_cumulative"] = round(
            lr["groups_and_mobile"].get("wall_s_cumulative", 0.0) + rep["wall_s"], 1)
        lr["groups_and_mobile"]["files_this_run"] = len(rep["files"])
        lr["groups_and_mobile"]["missing"] = rep["missing"]
        lr_p.write_text(json.dumps(lr, indent=1))

    # The cheapest room in tier 0: the normal maps at a lower ETC1S quality.  Measured on five of the
    # 46 tier-0 normals, qlevel 128 -> 32 is -20.8 % of their bytes for an RMS change of +0.00001 or
    # less against the source, which is far below what moving a whole map to tier 1 costs.  Done before
    # the trim, so the trim only has to find what this does not.
    if not a.no_pack:
        _, t0keys = gate5_tex.tier0_texture_keys(man, vis)
        norms = sorted({k for k, tag in t0keys if tag.endswith(":normal")})
        nrep = gate5_tex.encode_set(norms, man, lowres, "etc1s", 2,
                                    f"tier0 normals etc1s /2 qlevel {TIER0_NORMAL_QLEVEL}",
                                    qlevel=TIER0_NORMAL_QLEVEL)
        lr_p = out / "lowres.json"
        lr = json.loads(lr_p.read_text()) if lr_p.exists() else {}
        lr["tier0_normals_qlevel"] = nrep
        lr_p.write_text(json.dumps(lr, indent=1))

    # ------------------------------------------------------------------------------- the glb groups
    gfile = out / ("groups_mobile.json" if a.mobile else "groups.json")
    if not a.no_pack:
        # Review finding 4: remove only THIS variant's groups. `rm -rf groups/` on the desktop run
        # deleted the `m_*` files manifest_mobile.json points at, so idempotency depended on a run
        # order that only the README knew about.
        gdir = out / "groups"
        if gdir.is_dir():
            for f in sorted(gdir.iterdir()):
                if f.name.startswith("m_") == bool(a.mobile):
                    f.unlink()
        groups = build_all_groups(man, vis, order, out, a.cap, lowres, log, a.mobile)
        gfile.write_text(json.dumps(dict(groups=groups), indent=1))
    else:
        groups = json.loads(gfile.read_text())["groups"]
    log.close()

    assign_and_write(man, vis, order, out, groups, a.cap, lowres, imp_keys,
                     "mobile" if a.mobile else "desktop",
                     "manifest_mobile.json" if a.mobile else "manifest.json")


def build_all_groups(man, vis, order, out, cap, lowres, log, mobile):
    """One group per (class, tier).  NO duplicated geometry, desktop or mobile.

    The first cut shipped a tier-0 PLACEHOLDER group (the hero-visible subset) beside the tier-1 group
    that carried the same prototypes' other instances.  Measured by the viewer engineer at the hero:
    428 draw calls and 5.83 M drawn triangles against Gate 3's 329 and 5.24 M, because both were in the
    scene at once and a prototype's instances were cut across two files.  Now every instance of a
    prototype is in exactly ONE group, whose tier is the earliest any of its instances needs, and the
    group's own maps are the half-resolution ETC1S set from the start.  What tier 1 upgrades is the
    TEXTURE, not the geometry: `tiers.lowres.files[key].full` names the full-resolution file for every
    key a group refers to, so the viewer re-loads the map and keeps the mesh.
    """
    # Every group refers to the FULL-RESOLUTION map by its published name, and embeds nothing.  Pointing
    # the URIs at `tex_lo` instead was the first cut and it dead-ends: a texture that arrives inside the
    # glb reaches three.js as a blob with no name, so no tier can ever pair it with its full-resolution
    # twin and the half-resolution copy stays in place for ever.  With the full name in the glb, the
    # viewer redirects the URI to `tiers.lowres.files[key].path` while it is in tier 0 and lets it
    # resolve normally afterwards - the same by-name pairing it already does for the Gate 2 sets.
    groups = []
    for cls in ("orn", "env") if not mobile else ("arch", "ground", "orn", "env"):
        groups += build_groups(cls, vis, order, out, man, cap, log,
                               prefix=f"m_{cls}" if mobile else cls,
                               lowres_dir=None,
                               simplify=MOBILE_SIMPLIFY.get(cls) if mobile else None,
                               hero_tier=0)
    return groups


if __name__ == "__main__":
    main()
