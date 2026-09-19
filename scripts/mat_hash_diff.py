"""Material blast-radius check: hash every material AND every shared node group in two .blend files and diff.

    blender --background --python scripts/mat_hash_diff.py -- <old.blend> <new.blend> [--json <out.json>]
    # the "old" file usually comes out of git:  git show <ref>:assets/materials.blend > /tmp/old_materials.blend

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
    if img is None:
        return "none"
    parts = [img.name, tuple(img.size), img.source, len(img.packed_files or ())]
    try:
        if img.has_data and img.size[0] * img.size[1] <= 4096 * 4096:
            buf = bytearray(len(img.pixels) * 4)
            img.pixels.foreach_get(memoryview(buf).cast("f"))
            parts.append(hashlib.sha1(bytes(buf)).hexdigest()[:16])
    except Exception as e:
        parts.append(f"nopix:{e.__class__.__name__}")
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
    argv = sys.argv[sys.argv.index("--") + 1:]
    a, b = argv[0], argv[1]
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
