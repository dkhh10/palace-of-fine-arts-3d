"""Material blast-radius check: hash every material AND every shared node group in two .blend files and diff.

    blender --background --python scripts/mat_hash_diff.py -- <old.blend> <new.blend> [--json <out.json>]
    # the "old" file comes out of git, and must be written BESIDE the new one (its `//textures/...` paths are
    # relative to whatever blend is open):  git show <ref>:assets/materials.blend > assets/_old_materials.blend

Written for Phase 8d, where the brief allows exactly one block of `scripts/mat_build.py` (the MAT_backdrop_*
materials) to change and every other MAT_ must be provably untouched.  Review r2 finding 1: an earlier throwaway
version of this hashed `bpy.data.materials` only, which would have reported every consumer of a shared `PFA_*`
node group as "unchanged" if the group itself had moved.  This one hashes, per material:

  * every node: bl_idname, operation / blend_type / data_type, and the value of every UNLINKED input socket
    (rounded to 6 dp, so float noise cannot produce a false positive);
  * the link topology (from node kind + socket name -> to node kind + socket name);
  * the node groups it references, transitively, by their own hash;
  * the image datablocks it references, by name + size + a hash of the pixel buffer where one is loaded
    (filepath alone would miss a repacked texture).

and, separately, every node group in the file, so a change inside a shared group is reported once on its own
line as well as on each consumer.  Exit code is 0 always: this is a report, the caller decides.
"""
import bpy, sys, json, hashlib

NO_IMAGES = False          # --no-images: ignore image pixel content (isolates a texture change from a node change)


def _socket_values(node):
    out = []
    for i in node.inputs:
        if i.is_linked:
            continue
        try:
            v = i.default_value
            out.append(tuple(round(float(x), 6) for x in v) if hasattr(v, "__len__") else round(float(v), 6))
        except Exception:
            out.append("?")
    return tuple(out)


def _image_sig(img):
    """Content signature that does NOT depend on whether Blender has lazily loaded the image yet.

    The first version hashed `img.pixels`, which is only populated once the image is loaded: a freshly BUILT file
    has every image loaded, a file just opened from disk does not, so 26 materials came back "changed" when the
    only difference was load state.  Packed data and the file on disk are both load-independent, so those come
    first and the pixel buffer is the fallback for generated images only.
    """
    if img is None:
        return "none"
    if NO_IMAGES:
        return img.name
    # NB: img.size is (0, 0) until Blender loads the image, so it is load state, not content, and must not be
    # hashed -- that alone reported 26 false "changed" materials when the only difference was that a freshly BUILT
    # file has its images loaded and a file just opened from disk does not.
    parts = [img.name, img.source, img.colorspace_settings.name, img.alpha_mode]
    try:
        pf = img.packed_file
        if pf is not None and pf.data:
            parts.append("packed:" + hashlib.sha1(pf.data).hexdigest()[:16])
        elif img.filepath:
            # `//` is relative to the blend that is open, so the two files being compared must sit in the same
            # directory or every relative texture resolves somewhere different.  If the file is not there we fall
            # back to the path string (equal on both sides) rather than to an error tag, which would otherwise
            # report every textured material as changed for a reason that has nothing to do with the material.
            fp = bpy.path.abspath(img.filepath)
            try:
                with open(fp, "rb") as fh:
                    parts.append("file:" + hashlib.sha1(fh.read()).hexdigest()[:16])
            except OSError:
                parts.append("nofile:" + img.filepath.replace("//", ""))
        elif img.has_data:
            buf = bytearray(len(img.pixels) * 4)
            img.pixels.foreach_get(memoryview(buf).cast("f"))
            parts.append("pix:" + hashlib.sha1(bytes(buf)).hexdigest()[:16])
        else:
            parts.append("nodata")
    except Exception as e:
        parts.append(f"err:{e.__class__.__name__}")
    return repr(tuple(parts))


def _tree_sig(nt, group_hash, images):
    nodes, links = [], []
    for n in sorted(nt.nodes, key=lambda x: (x.bl_idname, x.name)):
        extra = ""
        if n.bl_idname == "ShaderNodeGroup":
            g = n.node_tree
            extra = group_hash(g) if g else "none"
        elif n.bl_idname in ("ShaderNodeTexImage", "ShaderNodeTexEnvironment"):
            extra = _image_sig(n.image)
            if n.image:
                images.add(n.image.name)
        nodes.append(repr((n.bl_idname, getattr(n, "operation", ""), getattr(n, "blend_type", ""),
                           getattr(n, "data_type", ""), getattr(n, "projection", ""),
                           getattr(n, "interpolation", ""), _socket_values(n), extra)))
    for l in nt.links:
        links.append((l.from_node.bl_idname, l.from_socket.name, l.to_node.bl_idname, l.to_socket.name))
    return hashlib.sha1(repr((sorted(nodes), sorted(links))).encode()).hexdigest()[:16]


def signature():
    seen = {}

    def group_hash(g):
        if g.name in seen:
            return seen[g.name]
        seen[g.name] = "recursing"
        seen[g.name] = _tree_sig(g, group_hash, set())
        return seen[g.name]

    groups = {g.name: group_hash(g) for g in bpy.data.node_groups}
    mats = {}
    for m in bpy.data.materials:
        if not m.node_tree:
            mats[m.name] = "no-nodes"
            continue
        imgs = set()
        h = _tree_sig(m.node_tree, group_hash, imgs)
        mats[m.name] = h
    return mats, groups


def load(path):
    bpy.ops.wm.open_mainfile(filepath=path)
    return signature()


def diff(old, new, what):
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = sorted(k for k in set(old) & set(new) if old[k] != new[k])
    print(f"[mat_hash_diff] {what} added:     {added}")
    print(f"[mat_hash_diff] {what} removed:   {removed}")
    print(f"[mat_hash_diff] {what} changed:   {changed}")
    print(f"[mat_hash_diff] {what} unchanged: {len(set(old) & set(new)) - len(changed)}")
    return dict(added=added, removed=removed, changed=changed,
                unchanged=len(set(old) & set(new)) - len(changed))


def main():
    global NO_IMAGES
    argv = sys.argv[sys.argv.index("--") + 1:]
    NO_IMAGES = "--no-images" in argv
    a, b = argv[0], argv[1]
    if NO_IMAGES:
        print("[mat_hash_diff] --no-images: image pixel content ignored")
    print(f"[mat_hash_diff] old = {a}")
    print(f"[mat_hash_diff] new = {b}")
    om, og = load(a)
    nm, ng = load(b)
    rep = {"old": a, "new": b,
           "materials": diff(om, nm, "materials"),
           "node_groups": diff(og, ng, "node_groups")}
    if "--json" in argv:
        out = argv[argv.index("--json") + 1]
        json.dump(rep, open(out, "w"), indent=1)
        print("[mat_hash_diff] wrote", out)


main()
