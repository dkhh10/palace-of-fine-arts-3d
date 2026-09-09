"""ORN round 5 stats / socket / coverage check (no render).

    scripts/blender_run.sh 900 -- --background --python scripts/orn_r5_stats.py -- [--orn PATH] [--types a,b]

Reports, all measured on meshes and socket empties, never on an image:
  1. socket census from assets/architecture.blend: every orn_type, its count, and whether ORN ships an asset for it
     (the build_master.py ORN_COLL coverage check);
  2. frieze_run fit: for each distinct rotunda run length, the ORN asset build_master.py's guard would place on it
     and the length mismatch. **This section FAILS the script (exit 1) on a mismatch > RUN_TOL (5 mm)**: the run
     lengths in orn_build.RIN_RUNS are hard-coded, so a change to ARCH's RESSAUT_ALONG / CHAMFER_CIRCUMRADIUS would
     otherwise desynchronise the panels from the sockets in silence (ORN r5 review finding 4);
  3. band metrics for the rinceau panels: areal coverage of the frieze band (r6: 0.81 m), proud depth above its face
     (y = RIN_EMBED behind the asset's min-y), max proud vs the 0.10 m architrave-crown clearance (also a hard
     failure if the clearance drops below MIN_CLEAR = 10 mm), and the lateral
     shadow each proud element throws at the hero sun (az 118.5 / el 7.4 on a face whose normal is az 82);
  4. the LOD tri table for every ORN type, with the budget and pass/fail;
  5. per-instance variation available to the lead: distinct (design, variant_seed) pairs per socket type;
  6/7 (round 6): every capital and every attic relief field FILLS the ARCH course it sits in, to COURSE_TOL
     (30 mm). The course is read from the socket (capital_height / panel_height / band_height) when ARCH stamps
     it and is then also checked against orn_build's own constant, so an ARCH/ORN desync fails here instead of
     leaving a void under the architrave (QA-06-6, ARCH r6 capital 2.6 -> 3.0 / panel 4.50 -> 5.27);
  8. the capital's silhouette tier profile: how many times the max radius swells and pinches on the way up, a
     no-render proxy for QA-06-6's "the two acanthus rows and the volutes separately readable".
"""
import bpy, sys, os, math, statistics
from collections import defaultdict
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import orn_lib as L

import orn_build as B          # ORN's build constants (ARCH_R6, RIN_*, PANEL_*) -- the gate compares them to ARCH

ARGS = common.script_args()
ORN_BLEND = ARGS[ARGS.index("--orn") + 1] if "--orn" in ARGS else str(common.ASSET_FILES["ORN"])
ONLY = ARGS[ARGS.index("--types") + 1].split(",") if "--types" in ARGS else None
EMBED = 0.015            # orn_build.RIN_EMBED: how far the rinceau is sunk into the frieze face
CROWN_CLEAR = 0.10       # architrave crown d 0.44 vs frieze face d 0.34 (scripts/arch_build.py:156, r4b profile).
                         # The 0.16 used in round 5 came from the superseded d 0.50 row (docs/arch_notes.md:718).
MIN_CLEAR = 0.010        # a panel must leave at least 10 mm under the crown, else this script fails
RUN_TOL = 0.005          # a panel must match its socket's run_length to 5 mm, else this script fails
COURSE_TOL = 0.030       # round 6: an asset must fill its ARCH course (capital 3.0, band 0.81, panel 5.27) to 30 mm
# ARCH's OWN frieze bands: these frieze_run sockets carry geometry ARCH models itself, not an ORN asset. Everything
# else on the frieze_run type is the 24 rotunda ressaut faces. ARCH round 6 stamps those host="rotunda" /
# subtype="rinceau"; until then they carry neither prop, so select them BY EXCLUSION, exactly as the guard in
# build_master.py does. Both readings give the same 24 sockets.
ARCH_OWN_SUBTYPES = ("greek_key", "greek_fret")
FAILURES = []
SUN_AZ, SUN_EL, FACE_AZ = 118.5, 7.4, 82.0

# ------------------------------------------------------------------ 1/2/5: sockets (architecture.blend)
bpy.ops.wm.open_mainfile(filepath=str(common.ASSET_FILES["ARCH"]), load_ui=False)
bpy.context.view_layer.update()
socket_types = defaultdict(list)
for o in bpy.data.objects:
    if o.name.startswith("SOCKET_") and o.get("orn_type"):
        socket_types[o["orn_type"]].append({
            "name": o.name, "z": o.matrix_world.translation.z,
            "run": float(o.get("run_length", o.get("size_hint", 0.0)) or 0.0),
            "host": o.get("host"), "subtype": o.get("subtype"),
            "design": o.get("design"), "seed": int(o.get("variant_seed", 0) or 0),
            "hint": float(o.get("size_hint", 0.0) or 0.0),
            # round 6: the course heights ARCH stamps on the socket. 0.0 = not stamped by this architecture.blend.
            "band": float(o.get("band_height", 0.0) or 0.0),
            "caph": float(o.get("capital_height", 0.0) or 0.0),
            "panelh": float(o.get("panel_height", 0.0) or 0.0)})

# ------------------------------------------------------------------ ornament library
bpy.ops.wm.open_mainfile(filepath=ORN_BLEND, load_ui=False)
assets = defaultdict(lambda: defaultdict(dict))     # type -> variant -> lod -> obj
import re
pat = re.compile(r"^ORN_(.+?)_v(\d+)_LOD(\d)$")
for o in bpy.data.objects:
    m = pat.match(o.name)
    if m and o.type == "MESH":
        assets[m.group(1)][int(m.group(2))][int(m.group(3))] = o

print("\n=== 1. socket census vs ORN assets (build_master.py ORN_COLL coverage) ===")
SERVES = {"capital_rotunda": "capital_rotunda", "capital_inner": "capital_inner",
          "capital_colonnade": "capital_colonnade", "maiden": "maiden", "attic_figure": "attic_figure",
          "attic_panel": "attic_panel", "keystone": "keystone", "inner_figure": "winged_figure",
          "finial": "finial", "rosette_ceiling": "rosette_ceiling", "urn": "urn", "drum_band": "drum_band",
          "frieze_run": "frieze_rinceau"}
for t in sorted(socket_types):
    lst = socket_types[t]
    a = SERVES.get(t)
    have = a in assets if a else False
    print(f"  {t:16s} n={len(lst):4d}  ORN asset: {a or '-':22s} {'PRESENT' if have else 'MISSING'}")

print("\n=== 2. frieze_run fit (hard check: run_length read from architecture.blend, tol 5 mm) ===")


def asset_type_for(run):
    """The asset build_master.py's frieze_run guard places on a rotunda ressaut socket of this run length."""
    return "frieze_rinceau" if run > 4.0 else "frieze_rinceau_return"


def asset_lengths(typ):
    """X extent of every variant of `typ`, per LOD, as {(variant, lod): length}."""
    out = {}
    for v, lods in sorted(assets.get(typ, {}).items()):
        for lod, o in sorted(lods.items()):
            (x0, _, _), (x1, _, _) = L.bbox(o)
            out[(v, lod)] = x1 - x0
    return out


groups = defaultdict(list)
stamped = 0
for sk in socket_types.get("frieze_run", []):
    rotunda = sk["subtype"] not in ARCH_OWN_SUBTYPES
    if rotunda and sk["subtype"] == "rinceau":
        stamped += 1
    groups[(sk["host"] or ("rotunda" if rotunda else "?"),
            sk["subtype"] or "(unstamped)", round(sk["run"], 3), rotunda)].append(sk)
n_rot = sum(len(v) for k, v in groups.items() if k[3])
print(f"  ARCH socket props: {stamped}/{n_rot} rotunda sockets carry subtype=\"rinceau\" "
      f"({'ARCH r6 contract in place' if stamped == n_rot and n_rot else 'selected by exclusion of ' + str(ARCH_OWN_SUBTYPES)})")
for key in sorted(groups, key=lambda k: (not k[3], str(k[0]), k[2])):
    host, sub, run, rotunda = key
    lst = groups[key]
    z = statistics.fmean(s["z"] for s in lst)
    if not rotunda:
        print(f"  host={host:12s} sub={sub:12s} run={run:6.3f} n={len(lst):3d} z={z:6.2f}  -> ARCH's own band geometry")
        continue
    typ = asset_type_for(run)
    lens = asset_lengths(typ)
    if not lens:
        FAILURES.append(f"section 2: {len(lst)} rotunda sockets of run {run:.3f} m map to '{typ}', which is MISSING "
                        f"from {ORN_BLEND}")
        print(f"  host={host:12s} sub={sub:12s} run={run:6.3f} n={len(lst):3d} z={z:6.2f}  -> {typ:24s} *** MISSING ***")
        continue
    worst = max(abs(v - run) for v in lens.values())
    tag = "ok" if worst <= RUN_TOL else "*** MISMATCH ***"
    print(f"  host={host:12s} sub={sub:12s} run={run:6.3f} n={len(lst):3d} z={z:6.2f}  -> {typ:24s} "
          f"asset {min(lens.values()):.4f}-{max(lens.values()):.4f} m over {len(lens)} LODs, "
          f"worst mismatch {worst*1000:6.2f} mm  {tag}")
    if worst > RUN_TOL:
        for (v, lod), ln in sorted(lens.items()):
            if abs(ln - run) > RUN_TOL:
                FAILURES.append(f"section 2: ORN_{typ}_v{v}_LOD{lod} is {ln:.4f} m but its socket run_length is "
                                f"{run:.4f} m ({abs(ln - run)*1000:.1f} mm > {RUN_TOL*1000:.0f} mm). "
                                f"orn_build.RIN_RUNS is hard-coded -- re-read it from architecture.blend.")

print("\n=== 3. rinceau band metrics ===")


def band_metrics(obj, nx=520, nz=100):
    from mathutils.bvhtree import BVHTree
    mw = obj.matrix_world
    verts = [mw @ v.co for v in obj.data.vertices]
    polys = [tuple(p.vertices) for p in obj.data.polygons]
    bvh = BVHTree.FromPolygons(verts, polys, all_triangles=False, epsilon=0.0)
    bb = [mw @ Vector(c) for c in obj.bound_box]
    x0, x1 = min(v.x for v in bb), max(v.x for v in bb)
    y1 = max(v.y for v in bb)
    z0, z1 = min(v.z for v in bb), max(v.z for v in bb)
    hits, depths = 0, []
    n = 0
    for i in range(nx):
        x = x0 + (i + 0.5) * (x1 - x0) / nx
        for k in range(nz):
            z = z0 + (k + 0.5) * (z1 - z0) / nz
            n += 1
            loc, nor, idx, dist = bvh.ray_cast(Vector((x, y1 + 0.5, z)), Vector((0, -1, 0)))
            if loc is None:
                continue
            hits += 1
            depths.append(loc.y)          # already measured from the wall plane y = 0
    depths.sort()
    return x1 - x0, z1 - z0, hits / n, depths


lat = math.tan(math.radians(SUN_AZ - FACE_AZ)) if abs(SUN_AZ - FACE_AZ) < 89 else float("inf")
# The band the SOCKETS say the rinceau has to fill (ARCH r6 stamps band_height; 0 before that landed).
rot_socket_bands = {round(s_["band"], 4) for s_ in socket_types.get("frieze_run", [])
                    if s_["subtype"] not in ARCH_OWN_SUBTYPES and s_["band"] > 0}
socket_band = min(rot_socket_bands) if len(rot_socket_bands) == 1 else None
if len(rot_socket_bands) != 1:          # r6 review finding 1
    FAILURES.append(f"section 3: rotunda frieze_run sockets carry {len(rot_socket_bands)} distinct band_height values "
                    f"{sorted(rot_socket_bands)}; expected exactly one.")
print(f"  socket band_height on the rotunda ressaut runs: "
      f"{('%.3f m' % socket_band) if socket_band else 'not stamped by this architecture.blend'}; "
      f"ORN builds to orn_build.RIN_BAND_H = {B.RIN_BAND_H:.3f} m")
if socket_band and abs(socket_band - B.RIN_BAND_H) > COURSE_TOL:
    FAILURES.append(f"section 3: ARCH's frieze_run sockets carry band_height {socket_band:.3f} m but "
                    f"orn_build.RIN_BAND_H is {B.RIN_BAND_H:.3f} m "
                    f"({abs(socket_band - B.RIN_BAND_H)*1000:.0f} mm apart) -- refit the rinceau to the socket.")
for t in ("frieze_rinceau", "frieze_rinceau_return"):
    for v in sorted(assets.get(t, {})):
        for lod in (0, 1, 2):
            o = assets[t][v].get(lod)
            if o is None or (lod and lod != 1):
                continue
            w, h, cov, d = band_metrics(o)
            if not d:
                continue
            band = float(o.get("band_height", h) or h)
            cov *= h / band          # coverage of the WHOLE band, not just the carved field
            p = lambda q: d[min(len(d) - 1, int(q * len(d)))]
            clear = CROWN_CLEAR - d[-1]
            print(f"  {o.name:36s} {w:.3f} x {h:.3f} m field in a {band:.2f} m band, coverage {cov*100:5.1f} % "
                  f"of the band ({cov*band/h*100:4.1f} % of the field)  proud above the frieze face: "
                  f"p50 {p(.5)*1000:5.1f}  p90 {p(.9)*1000:5.1f}  max {d[-1]*1000:5.1f} mm  "
                  f"clearance to the architrave crown {clear*1000:5.1f} mm  "
                  f"lateral shadow at max proud {d[-1]*lat*1000:5.1f} mm  "
                  f"{'ok' if clear >= MIN_CLEAR else '*** FOULS THE CROWN ***'}")
            if clear < MIN_CLEAR:
                FAILURES.append(f"section 3: {o.name} stands {d[-1]*1000:.1f} mm proud, leaving {clear*1000:.1f} mm "
                                f"under the architrave crown ({CROWN_CLEAR*1000:.0f} mm budget, "
                                f"{MIN_CLEAR*1000:.0f} mm minimum). Lower orn_build.RIN_MAX_PROUD.")

print("\n=== 4. LOD tri table ===")
for t in sorted(assets):
    if ONLY and t not in ONLY:
        continue
    bud = L.BUDGETS.get(t, L.BUDGETS["moulding"] if t in ("dentil", "egg_and_dart", "greek_key", "rosette_band",
                                                          "modillion", "anthemion", "drum_band") else L.BUDGETS["default"])
    for v in sorted(assets[t]):
        tris = {lod: L.tri_count(o) for lod, o in sorted(assets[t][v].items())}
        ok = all(tris.get(i, 0) <= bud[i] for i in range(3) if i in tris)
        print(f"  {('ORN_' + t + '_v' + str(v)):40s} " +
              " / ".join(f"LOD{i} {tris.get(i, 0):7d}" for i in range(3)) +
              f"   budget {bud[0]}/{bud[1]}/{bud[2]}  {'ok' if ok else '*** OVER ***'}")
        if not ok:
            over = [f"LOD{i} {tris[i]} > {bud[i]}" for i in range(3) if i in tris and tris[i] > bud[i]]
            FAILURES.append(f"section 4: ORN_{t}_v{v} over budget ({', '.join(over)}). "
                            f"orn_lib.enforce_lod2_budget should have welded LOD2 during the build.")

print("\n=== 5. per-instance variation available to the lead ===")
for t in sorted(socket_types):
    lst = socket_types[t]
    seeds = {s["seed"] for s in lst}
    designs = {s["design"] for s in lst if s["design"]}
    nvar = len(assets.get(SERVES.get(t, ""), {}))
    print(f"  {t:16s} sockets {len(lst):4d}  distinct variant_seed {len(seeds):4d}  designs {sorted(designs) or '-'}"
          f"  ORN variants {nvar}")


# ------------------------------------------------------------------ 6/7: round 6, does the asset fill its course?
def z_extent(o):
    (_, _, z0), (_, _, z1) = L.bbox(o)
    return z1 - z0


def x_extent(o):
    (x0, _, _), (x1, _, _) = L.bbox(o)
    return x1 - x0


def course_check(section, typ, sock_type, sock_key, orn_target, what):
    """Hard check that every LOD of every variant of `typ` fills the ARCH course it sits in.
    The course comes from the SOCKET when ARCH stamps it (authoritative); orn_build's own constant is checked
    against the socket too, so an ARCH/ORN desync fails here instead of leaving a void under the architrave."""
    socks = socket_types.get(sock_type, [])
    stamped = {round(s_[sock_key], 4) for s_ in socks if s_[sock_key] > 0}
    course = min(stamped) if len(stamped) == 1 else None
    src = f"socket {sock_key} {course:.3f} m" if course else f"NOT stamped on {len(socks)} {sock_type} sockets"
    if socks and len(stamped) != 1:      # r6 review finding 1: an empty or inconsistent stamp set is a failure, not a fallback
        FAILURES.append(f"section {section}: {sock_type} sockets carry {len(stamped)} distinct {sock_key} values "
                        f"{sorted(stamped)}; expected exactly one (ARCH contract, docs/sockets.md).")
    print(f"  {typ:20s} course: {src}; orn_build builds to {orn_target:.3f} m")
    if course and abs(course - orn_target) > COURSE_TOL:
        FAILURES.append(f"section {section}: ARCH's {sock_type} sockets carry {sock_key} {course:.3f} m but ORN "
                        f"builds {what} {orn_target:.3f} m ({abs(course - orn_target)*1000:.0f} mm apart).")
    target = course or orn_target
    for v in sorted(assets.get(typ, {})):
        hs = {lod: z_extent(o) for lod, o in sorted(assets[typ][v].items())}
        worst = max(abs(h - target) for h in hs.values())
        tag = "ok" if worst <= COURSE_TOL else "*** DOES NOT FILL THE COURSE ***"
        print(f"    ORN_{typ}_v{v:<2d} height " + " / ".join(f"LOD{k} {h:.3f}" for k, h in hs.items()) +
              f"  vs {target:.3f} m, worst {worst*1000:6.1f} mm  {tag}")
        if worst > COURSE_TOL:
            for lod, h in hs.items():
                if abs(h - target) > COURSE_TOL:
                    FAILURES.append(f"section {section}: ORN_{typ}_v{v}_LOD{lod} is {h:.3f} m tall in a "
                                    f"{target:.3f} m course ({(h - target)*1000:+.0f} mm).")


print("\n=== 6. capitals fill their course (QA-06-6; ARCH r6 capital_rotunda 2.6 -> 3.0 m) ===")
course_check(6, "capital_rotunda", "capital_rotunda", "caph", B.CAPITAL_PRESETS["capital_rotunda"]["H"], "a capital")
course_check(6, "capital_inner", "capital_inner", "caph", B.CAPITAL_PRESETS["capital_inner"]["H"], "a capital")
course_check(6, "capital_colonnade", "capital_colonnade", "caph", B.CAPITAL_PRESETS["capital_colonnade"]["H"], "a capital")
for t in ("capital_rotunda", "capital_inner", "capital_colonnade"):
    hints = {round(s_["hint"], 3) for s_ in socket_types.get(t, [])}
    lod0 = [assets[t][v][0] for v in sorted(assets.get(t, {})) if 0 in assets[t][v]]
    if lod0 and hints:
        # Round 8 (r7 review finding 8): this line used to be labelled "abacus", but x_extent() is the WHOLE
        # LOD0's plan width - leaf tips and corner volutes included - so it is 0.3-0.4 m wider than the abacus and
        # was quoted as if the leaves stopped at the abacus edge. The abacus itself is a preset number, printed
        # beside it: `abacus_across` is the across-the-corners width the abacus outline is built to.
        ab = [x_extent(o) for o in lod0]
        across = B.CAPITAL_PRESETS[t]["abacus_across"]
        print(f"  {t:20s} LOD0 plan extent (leaf tips + volutes) {min(ab):.2f}-{max(ab):.2f} m across x; "
              f"abacus {across:.2f} m across corners; socket size_hint (shaft top D) {sorted(hints)} "
              f"-> plan {min(ab)/max(hints):.2f}x / abacus {across/max(hints):.2f}x the shaft")

print("\n=== 7. attic panels fill their field (ARCH r6 panel_height 4.50 -> 5.27 m) ===")
course_check(7, "attic_panel", "attic_panel", "panelh", B.PANEL_H, "a relief field")
wid = {round(s_["hint"], 3) for s_ in socket_types.get("attic_panel", [])}
for v in sorted(assets.get("attic_panel", {})):
    o = assets["attic_panel"][v].get(0)
    if o:
        print(f"    ORN_attic_panel_v{v} width {x_extent(o):.3f} m vs socket size_hint (panel width) {sorted(wid)}")

print("\n=== 8. capital tier profile (geometric proxy for QA-06-6's readable acanthus rows) ===")


def tier_profile(o, nz=90):
    """Max radius in each of nz horizontal slices, then the alternation structure of that profile: how many
    times the silhouette swells and pinches on the way up. QA-06-6 asks for the two acanthus rows and the
    volutes to be separately readable; a capital whose radius rises monotonically has one tier, whatever its
    tri count. No render: this is the mesh's own silhouette."""
    (_, _, z0), (_, _, z1) = L.bbox(o)
    H = z1 - z0
    prof = [0.0] * nz
    for vtx in o.data.vertices:
        c = o.matrix_world @ vtx.co
        k = min(nz - 1, max(0, int((c.z - z0) / H * nz)))
        prof[k] = max(prof[k], math.hypot(c.x, c.y))
    # smooth over 3 slices so vertex noise does not count as a tier
    sm = [statistics.fmean(prof[max(0, i - 1):min(nz, i + 2)]) for i in range(nz)]
    ext, last, run_dir = [], sm[0], 0
    for i in range(1, nz):
        d = 1 if sm[i] > last + 1e-4 else (-1 if sm[i] < last - 1e-4 else run_dir)
        if run_dir and d and d != run_dir:
            ext.append((i, sm[i - 1], run_dir))
        run_dir, last = d or run_dir, sm[i]
    # count only swings between consecutive extrema that clear 2 % of the max radius (a real pinch, not a wobble)
    rmax = max(sm)
    swings = [abs(ext[i][1] - ext[i - 1][1]) for i in range(1, len(ext))]
    strong = [w for w in swings if w > 0.02 * rmax]
    return H, rmax, len(strong), (max(strong) if strong else 0.0)


for t in ("capital_rotunda",):
    for v in sorted(assets.get(t, {})):
        for lod in (0, 1):
            o = assets[t][v].get(lod)
            if o is None:
                continue
            H, rmax, n, big = tier_profile(o)
            print(f"  ORN_{t}_v{v}_LOD{lod}: h {H:.3f} m, max radius {rmax:.3f} m, "
                  f"{n} silhouette alternations >= 2 % of r_max, deepest pinch {big*1000:.0f} mm")

print("\n=== verdict ===")
if FAILURES:
    print(f"  *** {len(FAILURES)} HARD FAILURE(S) ***")
    for f in FAILURES:
        print(f"    - {f}")
    sys.stdout.flush()
    sys.exit(1)
print("  all hard checks passed (run lengths within "
      f"{RUN_TOL*1000:.0f} mm, crown clearance >= {MIN_CLEAR*1000:.0f} mm, every LOD inside its tier budget, "
      f"every capital and relief field filling its ARCH course to {COURSE_TOL*1000:.0f} mm)")
