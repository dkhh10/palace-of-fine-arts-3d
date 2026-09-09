"""Phase 5 delivery: make a .blend shippable. Purge orphans, optionally pack images, restore the LOD defaults and
the saved Eevee viewport preset, write a JSON inventory, and prove the saved file re-opens in under 60 s.

    scripts/blender_run.sh 600 -- --background --python scripts/phase5_cleanup.py -- \
        --blend master_delivery.blend [--pack] [--save-as <path>] [--report <path>] [--render-lod 0]

It is checklist step 1b (scripts/phase5_deliver.sh), run on a COPY of master.blend -- see `--allow-master` below.

What it does, in order:
  1. inventory: data-blocks per type (local vs linked), objects, libraries, images external vs packed, file size.
  2. purge orphans, recursively, until the count stops moving (`bpy.ops.outliner.orphans_purge`, the same call
     `common.purge_orphans` makes). LINKED ids are NOT purged (`do_linked_ids=False`): they belong to the library
     file, this script never edits another file, and an unused linked id is reported instead.
  3. `--pack` only: pack every EXTERNAL, LOCAL image whose file is on disk. Linked images are skipped (library data
     is read-only). If current size + the bytes to pack would exceed PACK_SIZE_LIMIT (1.5 GB), NOTHING is packed and
     the estimate is reported -- packing is the one step that can make the file too big to open.
  4. LODs: `common.set_lod(viewport=1, render=RENDER_LOD)`, exactly as scripts/build_master.py:251 leaves the master
     (viewport LOD1, render LOD0 -- the LOD every 4K / flythrough final has rendered at; docs/tech_notes.md
     "LOD convention"). `--render-lod 1` if a delivery is ever wanted at the mid LOD in renders too.
  5. `light_presets.apply_viewport_eevee(scene)` -- the saved navigable state (Eevee, light_threshold 0.01,
     raytracing off, the Eevee vault/shade overrides), the same call build_master.py:269 makes last.
  6. save (compressed), then time an in-process re-open of the saved file. Exits non-zero if that exceeds 60 s
     (docs/phase5_checklist.md step 2) so blender_run.sh / phase5_deliver.sh report a real failure.

Camera stations are NEVER touched: qa_cameras.ensure is not called and nothing writes to a camera. Every camera's
world matrix + lens is hashed before and after and the pair is asserted (and reported as `cameras_unchanged`).

Idempotent: a second run purges 0, packs 0, and re-applies the same LOD / preset state.
"""
import bpy, sys, os, json, time, resource
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

PACK_SIZE_LIMIT = 1_500_000_000     # 1.5 GB: refuse to pack past this
REOPEN_LIMIT_S = 60.0               # docs/phase5_checklist.md step 2

args = common.script_args()


def arg(name, default=None, n=1):
    if name not in args:
        return default
    i = args.index(name) + 1
    vals = args[i:i + n]
    return vals[0] if n == 1 else vals


BLEND = Path(arg("--blend", str(common.ROOT / "master.blend"))).resolve()
SAVE_AS = Path(arg("--save-as", str(BLEND))).resolve()
REPORT = Path(arg("--report", str(common.RENDERS / "logs" / "phase5_cleanup.json")))
RENDER_LOD = int(arg("--render-lod", 0))
PACK = "--pack" in args
ALLOW_MASTER = "--allow-master" in args

if not BLEND.exists():
    sys.exit(f"[phase5_cleanup] no such file: {BLEND}")
# Safety rail: the delivery driver runs this on master_delivery.blend, never on master.blend itself.
if SAVE_AS.name == "master.blend" and not ALLOW_MASTER:
    sys.exit(f"[phase5_cleanup] refusing to write {SAVE_AS} (the lead's master). Pass --save-as <copy> "
             f"(scripts/phase5_deliver.sh step 1b does), or --allow-master to override.")


# ------------------------------------------------------------------ inventory helpers
# `bpy.data.all_ids` is a meta-collection holding every ID in the file; counting it doubles every total.
SKIP_COLLECTIONS = {"all_ids"}


def id_collections():
    """(name, collection) for every bpy.data collection that holds data-blocks."""
    out = []
    for prop in bpy.data.bl_rna.properties:
        if prop.type != "COLLECTION" or prop.identifier in SKIP_COLLECTIONS:
            continue
        coll = getattr(bpy.data, prop.identifier, None)
        if coll is None:
            continue
        try:
            len(coll)
        except TypeError:
            continue
        out.append((prop.identifier, coll))
    return out


def datablock_counts():
    """{type: {'local': n, 'linked': n}} for every non-empty data-block collection."""
    counts = {}
    for name, coll in id_collections():
        local = linked = 0
        for item in coll:
            if getattr(item, "library", None) is not None:
                linked += 1
            else:
                local += 1
        if local or linked:
            counts[name] = {"local": local, "linked": linked}
    return counts


def total_of(counts):
    return sum(v["local"] + v["linked"] for v in counts.values())


def camera_fingerprint():
    fp = {}
    for ob in bpy.data.objects:
        if ob.type != "CAMERA":
            continue
        m = [round(v, 6) for row in ob.matrix_world for v in row]
        lens = round(getattr(ob.data, "lens", 0.0), 6) if ob.data else 0.0
        fp[ob.name] = m + [lens]
    return fp


def image_stats():
    """External vs packed, and the on-disk bytes an unpacked local image would add to the file."""
    packed, external, generated, missing, linked = [], [], [], [], []
    bytes_to_pack, seen = 0, set()
    for img in bpy.data.images:
        if img.packed_file is not None or img.packed_files:
            packed.append(img.name)
            continue
        if img.source not in {"FILE", "SEQUENCE", "MOVIE", "TILED"} or not img.filepath:
            generated.append(img.name)
            continue
        abspath = bpy.path.abspath(img.filepath, library=img.library)
        if not os.path.exists(abspath):
            missing.append({"name": img.name, "path": img.filepath})
            continue
        if img.library is not None:
            linked.append(img.name)
            continue
        external.append({"name": img.name, "path": img.filepath, "bytes": os.path.getsize(abspath)})
        real = os.path.realpath(abspath)
        if real not in seen:                       # several images can share one file; count its bytes once
            seen.add(real)
            bytes_to_pack += os.path.getsize(abspath)
    return dict(packed=packed, external=external, generated=generated, missing=missing,
                linked_external=linked, bytes_to_pack=bytes_to_pack)


def library_report():
    out = []
    for lib in bpy.data.libraries:
        abspath = bpy.path.abspath(lib.filepath)
        try:
            rel = os.path.relpath(os.path.realpath(abspath), str(common.ROOT))
        except ValueError:
            rel = abspath
        out.append(dict(name=lib.name, filepath=lib.filepath, relative_to_root=rel,
                        exists=os.path.exists(abspath),
                        users_id=len([i for c_name, c in id_collections() for i in c
                                      if getattr(i, "library", None) is lib])))
    return out


# ------------------------------------------------------------------ open
t_open0 = time.time()
bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
t_open = time.time() - t_open0
scene = bpy.context.scene
size_before = BLEND.stat().st_size
print(f"[phase5_cleanup] opened {BLEND.name} in {t_open:.2f}s "
      f"({size_before/1e6:.0f} MB, {len(bpy.data.objects)} objects, scene '{scene.name}')")

cams_before = camera_fingerprint()
counts_before = datablock_counts()
images_before = image_stats()
libs = library_report()
linked_ids = {k: v["linked"] for k, v in counts_before.items() if v["linked"]}
if libs:
    print(f"[phase5_cleanup] {len(libs)} linked librar{'y' if len(libs) == 1 else 'ies'} "
          f"({sum(linked_ids.values())} linked ids): read-only, reported not purged/edited")
    for lib in libs:
        print(f"    {lib['relative_to_root']}  ids={lib['users_id']}  exists={lib['exists']}")
else:
    print("[phase5_cleanup] no linked libraries (master.blend is built by APPEND; build_master.py --link would add them)")

# ------------------------------------------------------------------ 1. purge orphans
purge_passes = []
for _ in range(8):
    before = total_of(datablock_counts())
    try:
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
    except Exception as ex:
        print("[phase5_cleanup] orphans_purge:", ex)
        break
    after = total_of(datablock_counts())
    purge_passes.append(before - after)
    if before == after:
        break
counts_after_purge = datablock_counts()
purged = {}
for k, v in counts_before.items():
    d = v["local"] - counts_after_purge.get(k, {"local": 0})["local"]
    if d:
        purged[k] = d
n_purged = sum(purged.values())
print(f"[phase5_cleanup] purged {n_purged} orphan data-blocks in {len(purge_passes)} passes "
      f"({total_of(counts_before)} -> {total_of(counts_after_purge)} total)")
for k in sorted(purged, key=lambda k: -purged[k]):
    print(f"    {k:24s} {counts_before[k]['local']:6d} -> {counts_after_purge.get(k, {'local': 0})['local']:6d}"
          f"  (-{purged[k]})")

# ------------------------------------------------------------------ 2. pack images (optional)
images_mid = image_stats()
pack_result = dict(requested=PACK, packed_count=0, packed_bytes=0, skipped_reason=None,
                   estimated_bytes=images_mid["bytes_to_pack"],
                   estimated_size_after=size_before + images_mid["bytes_to_pack"])
if PACK:
    projected = size_before + images_mid["bytes_to_pack"]
    if projected > PACK_SIZE_LIMIT:
        pack_result["skipped_reason"] = (
            f"projected {projected/1e9:.2f} GB > {PACK_SIZE_LIMIT/1e9:.2f} GB limit")
        print(f"[phase5_cleanup] PACK REFUSED: {len(images_mid['external'])} external images would add "
              f"{images_mid['bytes_to_pack']/1e6:.0f} MB to {size_before/1e6:.0f} MB = "
              f"{projected/1e9:.2f} GB, past the {PACK_SIZE_LIMIT/1e9:.1f} GB limit. Nothing packed; "
              f"the delivery keeps its external textures (they are in the repo).")
    else:
        done = 0
        for entry in images_mid["external"]:
            img = bpy.data.images.get(entry["name"])
            if img is None or img.library is not None:
                continue
            try:
                img.pack()
                done += 1
            except Exception as ex:
                print(f"[phase5_cleanup] pack failed for {entry['name']}: {ex}")
        pack_result["packed_count"] = done
        pack_result["packed_bytes"] = images_mid["bytes_to_pack"]
        print(f"[phase5_cleanup] packed {done} images, {images_mid['bytes_to_pack']/1e6:.1f} MB of texture data")
else:
    print(f"[phase5_cleanup] --pack not given: {len(images_mid['external'])} external images "
          f"({images_mid['bytes_to_pack']/1e6:.1f} MB) would be packed; "
          f"{len(images_mid['packed'])} already packed, {len(images_mid['linked_external'])} linked (skipped), "
          f"{len(images_mid['missing'])} missing on disk")
    for m in images_mid["missing"]:
        print(f"    MISSING {m['name']}  {m['path']}")

# ------------------------------------------------------------------ 3. LOD defaults
lod_skipped = []
linked_objects = [o for o in bpy.data.objects if o.library is not None]
if not linked_objects:
    common.set_lod(viewport=1, render=RENDER_LOD)                    # build_master.py:251, the shipped default
else:
    # Library objects are read-only, so common.set_lod would raise on the first one and leave the rest untouched.
    # Same semantics, per-id guarded, and every id it cannot write is reported.
    import re
    pat = re.compile(r"_LOD(\d)$")
    for group, want_v, want_r in ((bpy.data.objects, True, True), (bpy.data.collections, True, True)):
        for item in list(group):
            m = pat.search(item.name)
            if not m:
                continue
            k = int(m.group(1))
            try:
                item.hide_viewport = (k != 1)
                item.hide_render = (k != RENDER_LOD)
            except Exception as ex:
                lod_skipped.append({"name": item.name, "error": str(ex)})
    print(f"[phase5_cleanup] set_lod viewport=LOD1 render=LOD{RENDER_LOD} (guarded: "
          f"{len(linked_objects)} linked objects, {len(lod_skipped)} not writable)")
lod_counts = dict(
    objects=len([o for o in bpy.data.objects if o.name[-5:-1] == "_LOD"]),
    viewport_visible=len([o for o in bpy.data.objects if o.name.endswith("_LOD1") and not o.hide_viewport]),
    hidden_lod0=len([o for o in bpy.data.objects if o.name.endswith("_LOD0") and o.hide_viewport]),
    hidden_lod2=len([o for o in bpy.data.objects if o.name.endswith("_LOD2") and o.hide_viewport]),
    render_lod=RENDER_LOD,
)

# ------------------------------------------------------------------ 4. saved Eevee viewport preset
preset_ok, preset_err = True, None
try:
    import light_presets
    light_presets.apply_viewport_eevee(scene)
    print(f"[phase5_cleanup] apply_viewport_eevee: engine={scene.render.engine} "
          f"taa={scene.eevee.taa_samples} light_threshold={scene.eevee.light_threshold} "
          f"raytracing={scene.eevee.use_raytracing}")
except Exception as ex:
    preset_ok, preset_err = False, str(ex)
    print("[phase5_cleanup] apply_viewport_eevee FAILED:", ex)

# ------------------------------------------------------------------ 5. cameras untouched, then save
cams_after = camera_fingerprint()
cams_unchanged = cams_before == cams_after
if not cams_unchanged:
    moved = [k for k in cams_before if cams_before.get(k) != cams_after.get(k)]
    print(f"[phase5_cleanup] ERROR: camera stations changed: {moved}")
else:
    print(f"[phase5_cleanup] {len(cams_after)} camera stations unchanged")

SAVE_AS.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(SAVE_AS), relative_remap=True, compress=True)
size_after = SAVE_AS.stat().st_size
print(f"[phase5_cleanup] saved {SAVE_AS} ({size_after/1e6:.1f} MB; was {size_before/1e6:.1f} MB)")

counts_final = datablock_counts()
images_final = image_stats()

# ------------------------------------------------------------------ 6. timed re-open of the saved file
t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=str(SAVE_AS), load_ui=False)
reopen_s = time.time() - t0
reopen_ok = reopen_s < REOPEN_LIMIT_S
print(f"[phase5_cleanup] re-open of {SAVE_AS.name}: {reopen_s:.2f}s "
      f"({'PASS' if reopen_ok else 'FAIL'}, limit {REOPEN_LIMIT_S:.0f}s) -- "
      f"{len(bpy.data.objects)} objects, engine {bpy.context.scene.render.engine}")

peak_rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6   # macOS reports bytes

report = dict(
    script="phase5_cleanup.py",
    blend_in=str(BLEND), blend_out=str(SAVE_AS), when=common.timestamp(),
    render_lod=RENDER_LOD, pack_requested=PACK,
    open_s=round(t_open, 3), reopen_s=round(reopen_s, 3), reopen_limit_s=REOPEN_LIMIT_S,
    file_size_bytes_before=size_before, file_size_bytes_after=size_after,
    file_size_mb_after=round(size_after / 1e6, 1),
    objects=len(bpy.data.objects),
    objects_by_type={t: len([o for o in bpy.data.objects if o.type == t])
                     for t in sorted({o.type for o in bpy.data.objects})},
    datablocks_before=counts_before, datablocks_after=counts_final,
    datablocks_total_before=total_of(counts_before), datablocks_total_after=total_of(counts_final),
    purged_by_type=purged, purged_total=n_purged, purge_passes=purge_passes,
    linked_libraries=libs, linked_ids_by_type=linked_ids,
    images=dict(
        total=len(bpy.data.images),
        packed_before=len(images_before["packed"]), external_before=len(images_before["external"]),
        packed_after=len(images_final["packed"]), external_after=len(images_final["external"]),
        external_bytes_after=sum(e["bytes"] for e in images_final["external"]),
        linked_external=images_final["linked_external"], missing=images_final["missing"],
        generated=len(images_final["generated"]),
        external_list=[dict(name=e["name"], path=e["path"], mb=round(e["bytes"] / 1e6, 2))
                       for e in sorted(images_final["external"], key=lambda e: -e["bytes"])[:40]],
    ),
    pack=pack_result,
    lod=lod_counts, lod_not_writable=lod_skipped,
    viewport_preset=dict(applied=preset_ok, error=preset_err,
                         engine=bpy.context.scene.render.engine,
                         light_threshold=round(bpy.context.scene.eevee.light_threshold, 4),
                         use_raytracing=bpy.context.scene.eevee.use_raytracing,
                         taa_samples=bpy.context.scene.eevee.taa_samples),
    cameras=sorted(cams_after), cameras_unchanged=cams_unchanged,
    peak_rss_mb=round(peak_rss_mb, 1),
    gates=dict(reopen_under_60s=reopen_ok, size_under_1_5gb=size_after < PACK_SIZE_LIMIT,
               cameras_unchanged=cams_unchanged, viewport_preset=preset_ok),
)
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(report, indent=1, sort_keys=True))
print(f"[phase5_cleanup] wrote {REPORT}")
print(f"[phase5_cleanup] reopen_s={reopen_s:.2f} size_mb={size_after/1e6:.1f} purged={n_purged} "
      f"packed_count={pack_result['packed_count']} packed_bytes={pack_result['packed_bytes']} "
      f"objects={len(bpy.data.objects)} libraries={len(libs)} peak_rss_mb={peak_rss_mb:.0f}")

if not (reopen_ok and cams_unchanged):
    sys.exit(1)
