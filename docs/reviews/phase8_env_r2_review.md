# Code review — branch `phase8d-env` (ebd9f8f..0fd2d86), Phase 8d PART 1

Reviewer: code reviewer (Opus 5, read-only, no Blender, no Chrome). Date 2026-09-19.
Scope reviewed: `git diff a51e1f8..0fd2d86` in the worktree — `scripts/mat_build.py`, `scripts/env_backdrop.py`,
`scripts/env_city.py`, `docs/briefs/phase8d_env_report.md`, the committed build logs; against CLAUDE.md,
`docs/briefs/phase8d_backdrop.md`, `docs/decisions.md` "8d decision", `docs/briefs/phase8d_analysis.md`,
and the export chain (`export/gate1_set.py`, `gate2_set.py`, `tiers.py`, `budget_doc.py`, `web/src/*.js`).
The two .blend files are binary and were judged only through the rebuild scripts and the committed run logs.

## Verdict: **MERGE WITH FIXES**

The build is sound, deterministic, inside the pin window, and does what the 8d decision authorised. Nothing here
justifies blocking the merge of the .blend files. Four things must be done — findings 1, 2 and 3 before the merge
(a `mat_build.py` re-run is 4 s and needs no ENV rebuild), finding 4 before the end-of-Phase-8 Cycles hero.

## What was verified and holds

* **Determinism / "nothing outside the backdrop moved".** The branch ran a *full* `env_build.py`, not a backdrop-only
  pass, so this needed proof. Diffing the committed logs line by line (main `renders/logs/p8a_build_lod2.log` vs
  `renders/logs/p8d_env_build3.log`, timing noise stripped) the **only** differences are the new belt line and the
  totals: LOD0 13,909,362 → 13,916,262, LOD1 5,237,628 → 5,244,528, LOD2 772,574 → 779,474, objects 5925 → 5929 —
  i.e. **exactly +6,900 at every LOD and +4 objects**. Terrain CDT, paving, water, rip-rap, 1,379 shrubs, 131 trees,
  every Sapling seed and the 1,747-crown far canopy reproduce identically. The rebuild is idempotent and scoped.
* **The pin.** `env_so_far` in `export/gate1_set.py:642` includes the backdrop groups and feeds `tree_allow` at :654,
  so +6,900 consumes 6,900 of the 6,986 slack (398,894 − 391,908); the cheapest further candidate is 12,892, so the
  20/127 near/far split cannot re-cut. `BELT_TRI_CAP` (`env_backdrop.py:347`) is that number and the planter's guard
  (`tris + max(tris_of.values()) > CAP`) is conservative. The crowns are icospheres at `subdivisions=1` (20 faces per
  lobe, 4 or 3 lobes = 80/60 **triangles**), so `len(me.polygons)` is a true triangle count — no undercount.
  Logged result 89 crowns / 6,900 tris / 3 points rejected, corroborated independently by the tri-count delta above.
* **R1 graphs are bakeable.** Every new term in `backdrop_atmosphere` and `build_backdrop_lawn` is a function of
  `ShaderNodeNewGeometry.Position` (and `.Normal`, which is view-independent) only. No Camera Data, no Layer Weight,
  no Fresnel, no Object Info (correctly — the Gate 1 merge makes it constant), no emission, no volume. The haze is a
  Base Color mix, so the Gate 2 **DIFFUSE colour** bake reproduces it exactly. `vmath("LENGTH")` correctly reads
  `outputs["Value"]` (mat_lib.py:229). The merged backdrop group carries world-space vertices at the bake, so
  Position is the right world position there.
* **Material blast radius.** Only the `MAT_backdrop_*` block of `mat_build.py` changed (:1072, :1446, :1698, and the
  new :1751-1856 block, plus two call lines at :1903/:1905). `apply_backdrop_atmosphere()` names only
  `MAT_backdrop_*`; it adds nodes inside each material's own tree and mutates no shared `PFA_*` node group.
  `ML.finish()` is idempotent (`auto_layout` only), so the double call is harmless. Re-linking an already-linked
  Base Color/Roughness input is correct Blender behaviour. `MAT_lawn` itself is untouched (`mat_build.py:1555`) and
  keeps its users: the palace terrain (`env_build.py:269`), `arch_build.py:1429`, and the impostor nursery ground
  (`export/band_set.py:56`, `gate3_set.py:239` → `GATE3_imp_lawn`), so the far-tree impostor bakes are unaffected.
  `MAT_backdrop_lawn` is used by backdrop objects only: `env_backdrop.py:459/462` and `env_city.py:171` (slot 0).
* **R2 belt hygiene.** `MAT_backdrop_forest` → joins the existing `backdrop_forest` export group, no new group
  (6 → 10 objects). Naming `ENV_backdrop_hall_belt_0..3` trips neither `scripts/qa_name_sweep.py` nor
  `export/name_sweep.py`. Seed `random.Random(8004)` is fixed and the rng stream is consumed in a
  placement-independent order, so the belt is reproducible. `blocked()` tests the hall field (+3 m), the 34 m rotunda
  platform and every colonnade roof polygon with a 3 m dilation. `L.join_instances` builds a fresh mesh and the four
  `ENV_src_hallbelt_*` source meshes are removed at 0 users — no stray objects, no name accumulation.
* **Preview-harness honesty (brief item 6).** `docs/briefs/phase8d_env_report.md` §3 carries the explicit caveat that
  the harness is AgX **Base** Contrast at −0.8 EV with a placeholder sun and that **only the before→after direction
  transfers**, plus two further "honest limits" on saturation vs luminance. Compliant; the delivery-look numbers in
  the decision (cam06 luma → ~0.80, sat → ~0.10) are **not** claimed to have been hit and must be re-measured on the
  real delivery render after the merge.

## Findings

**1. [MEDIUM — fix before merge] The "34 other materials unchanged" claim rests on an uncommitted script.**
`docs/briefs/phase8d_env_report.md:6-8` cites `/tmp/matdiff.py`. Nothing in the diff adds it and no committed log
holds its raw output (`renders/logs/p8d_mat2.log` is just the build). The brief (and CLAUDE.md's "every claim is
backed") requires a committed, re-runnable check. The method itself is sound (per-material SHA1 of sorted node kinds
+ operation/blend_type/data_type + unlinked input defaults + link topology, comparing the git copy of
`materials.blend` against the rebuilt one), but it has a real hole: **it hashes `bpy.data.materials` only**, so a
change inside a shared `PFA_*` node group or a swapped image would report every consumer as "unchanged".
*Fix:* commit it as `scripts/mat_hash_diff.py`, extend the signature to cover `bpy.data.node_groups` (nodes + links)
and each material's image users, re-run it and commit the raw log next to the report.

**2. [MEDIUM — fix before merge] The stated reason for `MAT_backdrop_lawn`'s grey/soil content is wrong, and the
content double-counts.** `scripts/env_city.py:167-170`, `scripts/mat_build.py:1818-1824` and the report's §1 table all
claim "Gate 1 groups a multi-material backdrop mesh by slot 0 alone, so in the viewer this one material is also what
the far roads, gravel and soil read as". That is not what the pipeline does: `export/gate2_set.py:211-233` rebuilds
the per-polygon material assignment on every merged ENV/backdrop mesh from `env_poly_src.npz` with a KD-tree lookup
on world polygon centres *before* the albedo bake (its own docstring at :9-10 says so: "the gravel paths, soil and
asphalt would otherwise bake as lawn"). The viewer samples that baked albedo, so roads, gravel, soil and dry hill
already read as their own materials; slot 0 only decides which group the mesh joins and which atlas it shares.
Consequence: the street-grey mix (`mat_build.py:1831`) and the bare-soil mix (:1833) are painted **on top of** the
polygons that already bake as asphalt and soil, greying the Marina Green / Crissy lawn twice — visible as the washed
grey mid-ground in the aerial "after" panel of the composite.
*Fix:* correct both code comments and the report paragraph; drop or roughly halve the `street`/`soil` mixes in
`build_backdrop_lawn` and keep the material a low-saturation mown-grass field (the "don't move the palace's MAT_lawn"
reason for its existence is entirely valid on its own).

**3. [MEDIUM — fix before merge] The palace-shadow term has no cross-wind gate.** `mat_build.py:1795-1803`:
`u = -0.477·wx − 0.879·wy` is the downwind distance and `inside` compares `22 − 0.130·u` to `wz`; `gate` limits `u` to
12–230 m. Nothing limits the **lateral** offset `v = 0.879·wx − 0.477·wy`, yet `MAT_backdrop_building` /`_roof`
/`_skylight` also cover the whole Marina / Cow Hollow house field out to 460 m. A house at world (−300, +100) is
311 m off the shadow axis and still gets up to 52 % albedo shade below z ≈ 15 m; the shading reads as a band across
the city rather than a shadow behind the palace, which is exactly the "flat authored field" 8d set out to remove.
*Fix:* two lines — `lat = t.absval(t.sub(t.mul(wx, 0.879), t.mul(wy, 0.477)))` and multiply `gate` by
`t.maprange(lat, 150.0, 220.0, 1.0, 0.0)` (width from the colonnade span, stated in the comment).

**4. [MEDIUM — must be measured before the Phase-8 Cycles hero, not before the merge] The haze albedo is a viewer
trick that Cycles will take literally.** `HAZE_TINT` (`mat_build.py:1751`) is a **linear** albedo of (0.780, 0.762,
0.724); at `amount` 0.82–0.92 the fully hazed far field reaches 0.65–0.72 linear reflectance — over 23 km² of ground
(`MAT_backdrop_lawn`, :1852), the hills (:1853) and the city. The viewer has no GI, so there it is free and correct.
The promised end-of-Phase-8 Cycles before/after hero **does** have GI: this is roughly a 6× lift of far-field bounce
against the previous ~0.1-albedo lawn, and it can move the palace's own fill — a change to the frozen Phase 5 look
that nobody approved. The same file-shared-with-Cycles problem applies to finding 3's shade term: in Cycles the sun
really is occluded by the colonnade, so the hall's lower wall is darkened twice (albedo ×0.48 **and** the real cast
shadow). The report states "Cycles sees them too" as a feature; it is a risk that has not been measured.
*Fix:* before the final hero, render cam01 at 1080p/32 spp with and without the 8d materials (a `PFA_NO8D=1` guard in
`apply_backdrop_atmosphere` or a temporary revert) and report the palace stone luma / hall lower-wall luma delta; if
the stone moves more than ~2 %, pull `amount`/`tint` down or gate `shade` to the hall's own distance band.

**5. [INFO — the rename fan-out the lead asked for] Everywhere `lawn` → `backdrop_lawn` must follow.**
The group name is derived, not hard-coded, so most of this happens automatically — but every artifact keyed by the
old name changes and two places need a human:
  a. `export/gate1_set.py:587` (derived): object `ENV_backdropgroup_lawn` → `ENV_backdropgroup_backdrop_lawn`, mesh
     `EXPM_ENV_backdropgroup_lawn` → `EXPM_..._backdrop_lawn`, group material `MAT_EXP_ENVBD__MAT_lawn` →
     `MAT_EXP_ENVBD__MAT_backdrop_lawn`. Same 3 objects / 5,882 tris, so `env_so_far` does not move. No other
     backdrop object still carries `MAT_lawn` at slot 0, so no empty/leftover `lawn` group is produced.
  b. `export/gate2_set.py:70-71` `job_id()` → the bake job is renamed `ENVBD__lawn` → `ENVBD__backdrop_lawn`. It is a
     **new** job to the queue: **purge the stale `ENVBD__lawn` entry from `export/out/bake_queue/status.json` and its
     maps from `export/out/gate2/`** before the re-bake, or a stale texture can survive into the pack.
     `ENV_SRC_OBJ`'s `slot0_material` key comes from the manifest (`group_src`), so it follows by itself.
  c. **`web/src/water.js:397`** — `/MAT_EXP_ENVBD__MAT_backdrop_/` is a *name-pattern* test. The far-ground group did
     not match before and now does, so with `reflSet: 'both'` (the default, `web/src/device.js:110`) the far field is
     newly **dropped from the water reflection set**. Probably harmless or a small win, but it is a behaviour change
     and the reflection counts recorded in the 6d/8b notes will shift. Re-measure at the hero and cam02, or narrow
     the regex.
  d. `manifest.json` (assets, meshes, tier membership lists), `web/public/assets/**` and the deployed
     `web/deploy_out/assets/gate5/manifest.json` — regenerated, but the deployed copy must be rebuilt, not patched.
  e. `docs/briefs/phase6_budget.md:133` (and the forest rows :97/:268) regenerate themselves from
     `export/budget_doc.py`; see finding 6.
  f. Not affected, checked: `export/tiers.py` (no name keys), `export/name_sweep.py` (fill exemptions only),
     `export/gate1_probe.py:78` and the `GATE3_imp_lawn` nursery (both still `MAT_lawn`, so the far-tree impostors and
     the walkable-surface rule are untouched), `export/gate2_common.py` atlas sizes (class-keyed).

**6. [LOW] Stale hard-coded budget prose.** `export/budget_doc.py:288` prints "`ENV_backdropgroup_backdrop_forest` is
99 640 triangles … 12.6 % … **never closer than the far shore**". After the belt it is 106,540 triangles and its
closest member is 150 m away, behind the north colonnade, in the hero frame — the sentence is now false and it is the
sentence used to argue the forest is the cheapest ENV saving. *Fix:* make the number data-driven (it is already in the
manifest) and delete the "far shore" clause.

**7. [LOW — for QA's full-resolution tiles, not a code defect] Belt silhouette and footing.**
`env_backdrop.py:415-419`: crowns are 12.5–19.5 m tall, centred at `z0 + 0.46h + 0.6…2.4`, i.e. the canopy bottom
floats 0.6–2.4 m above terrain and there are no trunks, while the tallest tops reach ≈ 22 m against a hall eave+rise
of 20 m. Two things the hero/cam05 100 % tiles must confirm: (a) no daylight or wall visible *under* the belt through
an intercolumniation, and (b) the belt does not cut the hall roof line that ref 169 shows above it.

**8. [LOW] Terrain-edge tone seam.** `ENV_terrain_ground` keeps green `MAT_lawn`; the far ground from ±360 m is now
`MAT_backdrop_lawn` + haze (grey, lifted). Check the cam06/aerial tiles for a hard tone step at the terrain edge.

**9. [LOW — accepted, noted] The belt shares the `backdrop_forest` 1024 atlas** (`gate2_common.SIZE_BACKDROP`) with
1,747 far crowns, so the closest canopy in the scene bakes at ≈ 0.8 texels/m. Consistent with R1's "low-frequency
only" decision; just do not expect the belt to gain detail from the Gate 2 re-bake.

## Merge conditions

1. Apply findings 1, 2 and 3 (one 4 s `mat_build.py` re-run; no ENV rebuild needed) and re-commit.
2. Carry finding 5 into the export brief — especially 5b (purge the stale `ENVBD__lawn` bake job) and 5c (the
   `water.js` reflection-set regex).
3. Gate 1 must be re-run in the worktree and its pin report (arch/orn/ground glbs byte-identical, near 20 / far 127
   impostor placements byte-identical) read before the export chain proceeds — the tri-count evidence above is strong
   but is not the pin proof itself.
4. Finding 4 is a condition on the Phase-8 Cycles hero, not on this merge; put it on the delivery checklist.
