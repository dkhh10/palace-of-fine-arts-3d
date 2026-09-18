#!/usr/bin/env python3
"""6b Gate 5 shared helpers: where every published file is, which texture key a material needs, and
which of them the hero station actually sees.

Nothing here writes: `gate5_tex.py`, `tiers.py`, `gate5_report.py` and `verify_glb.py --gate5` all read
the SAME answers from here, so a tier table, an encode job and a verification can never disagree about
what the payload is.

The file universe is resolved exactly the way the viewer resolves it (web/src/manifest.js, pbr.js,
lightmaps.js, impostors.js, foliageLazy.js, and web/tools/check_manifest_files.py for the Gate 2 path):
  glb            `glb.per_class[*].path`, plus the three lazily loaded foliage glbs
  lut / sky      `lut.path`, `sky.camera.hdr`, `sky.glossy.hdr`, `sky.diffuse.hdr`
  probe          `probe.dir` + `probe.files[*].hdr`
  gate2 PBR      `materials.sets[*].{albedo,roughness,normal}.texture` -> `textures.gate2`
  detail         `textures.gate2.detail_files`
  lightmaps      `lightmaps.assets[*]` and `lightmaps.slots.atlases[*]`, the `default` variant only
                 (`_gate1_layout` twins are the fallback for `uv2_in_glb: false` and are not published:
                  after the Gate 3 relay all 66 UV2 meshes are in the glbs)
  impostors      `impostors.prototypes[*].{albedo,normal_depth}` at 1 K (`variant_2k` is a lever, off)
  foliage        every file in `materials.foliage.dir`
"""
import json
import os
from pathlib import Path

MAIN = Path(os.environ.get("PFA_MAIN_ROOT", "/Users/dk/Projects/3d render blender 3rd attempt building"))
ROOT = Path(__file__).resolve().parents[1]
GATE3 = MAIN / "export/out/gate3"
GATE1 = MAIN / "export/out/gate1"
MANIFEST_V4 = GATE3 / "manifest.json"
OUT = Path(os.environ.get("PFA_GATE5_OUT", ROOT / "export/out/gate5"))
# Where the published tree IS, whatever worktree produced it: every path in the manifest is relative to
# MAIN's out/gate5, because that is what export/sync_main.sh copies to and what web/public/assets points
# at.  Computing them against a worktree's own out/gate5 gives `../../../../../../export/out/gate3/...`,
# which resolves on this disk and nowhere on the web.
PUB_BASE = MAIN / "export/out/gate5"
HERO = "CAM_qa_01_lagoon_hero"
CAP_BYTES = 25 * 1024 * 1024          # Cloudflare Pages' per-file ceiling
TIER0_BUDGET = 50_000_000             # "initial payload <= 50 MB" (CLAUDE.md 6b), decimal MB

# The 16-bit PNG bake output is regenerable and was never synced to MAIN (export/sync_main.sh excludes
# `tex/`), so the low-res tier-0 variants are encoded from the bake worktree's copies.  Overridable.
BAKE_ROOT = Path(os.environ.get(
    "PFA_BAKE_ROOT", MAIN / ".claude/worktrees/phase6-bake/export/out"))
# The 6c foliage card PNGs (export/foliage_tex.py) were written on the phase6-export branch and are not
# in MAIN either - the sync ships `foliage/tex_ktx2`, not `foliage/tex`.
EXPORT_ROOT = Path(os.environ.get(
    "PFA_EXPORT_ROOT", MAIN / ".claude/worktrees/phase6-export/export/out"))


def manifest(path=None):
    return json.loads(Path(path or MANIFEST_V4).read_text())


def visibility(path=None):
    return json.loads(Path(path or (OUT / "visibility.json")).read_text())


def candidate_keys(name):
    """Every name a bake may have keyed a material set by (web/src/pbr.js candidateKeys)."""
    if not name:
        return []
    out = [name]
    if "__" in name:
        out.append(name.split("__")[-1])
        out.append(name.split("__")[0])
    no_exp = name.replace("MAT_EXP_", "", 1)
    if no_exp != name:
        out += [no_exp, "MAT_" + no_exp]
    seen, uniq = set(), []
    for k in out:
        if k and k not in seen:
            seen.add(k)
            uniq.append(k)
    return uniq


def material_index(man):
    """{any key a glb material could carry: the manifest set name}."""
    idx = {}
    for name, s in man["materials"]["sets"].items():
        for k in [name] + list(s.get("aliases") or []) + candidate_keys(name):
            idx.setdefault(k, name)
    return idx


def set_of(man, idx, glb_material_name):
    for k in candidate_keys(glb_material_name):
        if k in idx:
            return idx[k]
    return None


def station_order(man, vis):
    """The hero first, then the QA stations in number order - the tier-2 ordering the brief asks for."""
    order = [s for s in vis.get("station_order") or [] if s != "CAM_flythrough"]
    return [HERO] + [s for s in order if s != HERO]


# --------------------------------------------------------------------------- the published file universe
class Pub:
    """One published file: where it is now, what it is, and what needs it."""

    __slots__ = ("path", "kind", "key", "reasons", "bytes")

    def __init__(self, path, kind, key=None):
        self.path = os.path.normpath(str(path))
        self.kind = kind
        self.key = key
        self.reasons = set()
        self.bytes = os.path.getsize(self.path) if os.path.exists(self.path) else None

    @property
    def name(self):
        return os.path.basename(self.path)

    def rel_to(self, base):
        return os.path.relpath(self.path, str(base))


def pub_rel(path, local_out):
    """The path a manifest publishes, in the PUBLISHED layout (MAIN out/gate5), not on this disk.
    A file this worktree produced under `local_out` keeps its name relative to gate5; anything else is
    relative to MAIN's out/gate5, where every gate sits side by side."""
    path = os.path.normpath(str(path))
    local_out = os.path.normpath(str(local_out))
    if path.startswith(local_out + os.sep):
        return os.path.relpath(path, local_out)
    return os.path.relpath(path, str(PUB_BASE))


def resolve_files(man, base=None):
    """{abs path: Pub} for every file the viewer downloads at the DESKTOP look."""
    base = Path(base or GATE3)
    out = {}

    def add(rel, kind, why, key=None, root=None):
        if not rel:
            return None
        p = os.path.normpath(os.path.join(str(root or base), rel))
        pub = out.get(p)
        if pub is None:
            pub = out[p] = Pub(p, kind, key)
        pub.reasons.add(why)
        return pub

    for cls, g in man["glb"]["per_class"].items():
        add(g["path"], "glb", f"glb:{cls}", key=cls)
    for k, blk in (("far_mesh", man["trees"].get("far_mesh")),
                   ("walkup_mesh", man["trees"].get("walkup_mesh")),
                   ("shrubs", man["shrubs"].get("lod1"))):
        if blk and blk.get("glb"):
            add("../gate1/" + os.path.basename(blk["glb"]), "glb_lazy", f"glb:{k}", key=k)
    add(man["lut"]["path"], "lut", "lut", key="lut")
    for k in ("camera", "glossy"):
        add(man["sky"][k]["hdr"], "sky", f"sky:{k}", key=k)
    add(man["sky"]["diffuse"]["hdr"], "sky", "sky:diffuse", key="diffuse")
    for face, v in man["probe"]["files"].items():
        add(os.path.join(man["probe"]["dir"], v["hdr"]), "probe", f"probe:{face}", key=face)

    tex = man["textures"]
    g1files, g1dir = tex["files"], tex["ktx2_dir"]
    g2, g3 = tex["gate2"], tex["gate3"]
    for name, s in man["materials"]["sets"].items():
        for slot in ("albedo", "roughness", "normal", "metallic", "occlusion"):
            e = s.get(slot)
            if not isinstance(e, dict) or not e.get("texture"):
                continue
            key = e["texture"]
            if key in g2["files"]:
                add(os.path.join(g2["ktx2_dir"], g2["files"][key]["path"]), "gate2",
                    f"material:{name}:{slot}", key=key)
            else:
                hit = next((f for f in g1files
                            if f in (key, key + ".ktx2") or f.startswith(key + ".")), None)
                if hit:
                    add(os.path.join(g1dir, hit), "gate1tex", f"material:{name}:{slot}", key=key)
    for key, v in (g2.get("detail_files") or {}).items():
        add(os.path.join(g2["ktx2_dir"], (v.get("path") if isinstance(v, dict) else None) or key + ".ktx2"),
            "detail", f"detail:{key}", key=key)
    for a, v in man["lightmaps"]["assets"].items():
        if a == "_gate1_layout" or "textures" not in v:
            continue
        key = v["textures"].get(v.get("default", "gamma2"))
        if key in g3["files"]:
            add(os.path.join(g3["ktx2_dir"], g3["files"][key]["path"]), "lightmap", f"lm:{a}", key=key)
    for a, v in man["lightmaps"]["slots"]["atlases"].items():
        key = v["textures"].get(v.get("default", "gamma2"))
        if key in g3["files"]:
            add(os.path.join(g3["ktx2_dir"], g3["files"][key]["path"]), "lightmap_atlas",
                f"lmatlas:{a}", key=key)
    for proto, v in man["impostors"]["prototypes"].items():
        for slot in ("albedo", "normal_depth"):
            key = v.get(slot)
            if key in g3["files"]:
                add(os.path.join(g3["ktx2_dir"], g3["files"][key]["path"]), "impostor",
                    f"impostor:{proto}:{slot}", key=key)
    fol = man["materials"].get("foliage") or {}
    fdir = (fol.get("dir") or "").replace("out/gate3/", "")
    if fdir and (base / fdir).is_dir():
        for f in sorted(os.listdir(base / fdir)):
            add(os.path.join(fdir, f), "foliage", "foliage", key=os.path.splitext(f)[0])
    return out


def png_source(key, man):
    """The 8/16-bit PNG a KTX2 key was encoded from, for re-encoding at a lower resolution."""
    g2 = man["textures"]["gate2"]
    if key in g2["files"] or key.startswith("gate2_") or key.startswith("detail_"):
        sub = "detail" if key.startswith("detail_") else "tex"
        for root in (BAKE_ROOT / "gate2" / sub, MAIN / "export/out/gate2" / sub):
            p = root / f"{key}.png"
            if p.exists():
                return p
        return None
    if key in man["textures"]["gate3"]["files"]:
        for root in (BAKE_ROOT / "gate3/tex", BAKE_ROOT / "gate3/impostor", GATE3 / "tex"):
            p = root / f"{key}.png"
            if p.exists():
                return p
        return None
    if key.startswith("foliage_"):
        for root in (GATE3 / "foliage/tex", EXPORT_ROOT / "gate3/foliage/tex",
                     BAKE_ROOT / "gate3/foliage/tex"):
            p = root / f"{key}.png"
            if p.exists():
                return p
        return None
    for root in (GATE1 / "tex", GATE1 / "tex_gltf"):
        for ext in (".png", ".jpg", ".jpeg"):
            p = root / f"{key}{ext}"
            if p.exists():
                return p
    return None


def oetf_for(key, man=None):
    """sRGB or linear for toktx.  The MANIFEST's own `colorspace` for the key wins - a colour map tagged
    linear comes back ~1.47x too bright and poisons every parity number (Gate 1 review finding 1) - and
    only a key the manifest does not carry falls back to gltf_pack.sh's name rule (colour is the default,
    DATA maps are the exception)."""
    if man:
        for blk in (man["textures"].get("gate2"), man["textures"].get("gate3")):
            e = ((blk or {}).get("files") or {}).get(key)
            if isinstance(e, dict) and e.get("colorspace") in ("srgb", "linear"):
                return e["colorspace"]
    k = key.lower()
    if k.endswith("_albedo") or "_diff" in k or "albedo" in k:
        return "srgb"
    if any(t in k for t in ("_normal", "_nrm", "normal", "_ao", "rough", "disp", "translu",
                            "_mask", "normdepth", "_lm_", "lmatlas", "gamma2", "rgbm8")):
        return "linear"
    return "srgb"
