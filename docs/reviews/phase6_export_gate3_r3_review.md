# MERGE WITH FIXES — `phase6-export` `ed00a62..05967b5` (Gate 3 r3), 9 findings (2 fix now, 7 carry, 0 blockers)

Read-only: 2 commits over `export/` (README.md, gate3_relay_check.py, gltf_gate1.py, manifest_v4.py, new read_mist.py)
plus 3 logs. Nothing outside `export/` and `renders/logs/` is touched; no blend, no `scripts/`, no `docs/`. Gate 1/Gate 3-r1
carries 6-11 are untouched and unworsened; r1 fix-nows 1-3 stay closed (`gate3_relay_check.py:324` now resolves
`PFA_MAIN_ROOT`, both halves read the same dir, the split guard is bidirectional at `verify_glb.py:224-235`).

**Verified from the diff and the sources, not from the report.** (a) Symmetry: `gltf_gate1.py:250` and
`gate3_relay_check.py:196` compute the global range with the *same* expression over the same npz, the checker never
takes the writer's, and `:265` fails on any disagreement — an old per-mesh encoder fails at that check, an old relay
fails at the new manifest assert. No "per mesh" survives in a *decode* string (`manifest_v4.py:170,179-183`,
`gate3_relay_check.py:253-256`). (b) That assert keys on `vertex_irradiance_range_global` and falls back to a single
distinct row `range`: an old-schema relay gives 14 distinct values → `None` → assert; rows without `range` give
`{None}` → `None` → assert. Correct on both paths. (c) The rel_p99 exclusion is right — the r3 log's means are 9e-6
(broadleaf_s19) and 1.14e-3 (pine_s29), the only two under the 0.01 mean docs/decisions.md sets as the gate's scope;
the other twelve run 0.046-3.89. (d) read_mist is read-only: no `save_*`, no render, no operator, no prompt, exits
(log rc=0 after 3 s). (e) The mist numbers and formula are independently confirmed by `scripts/light_build.py:281`
(`start=20.0, depth=2000.0, falloff="LINEAR"`, "mist pass = (d - 20) / 2000, clamped"); LINEAR = unshaped `t`.
(f) The "group input 0.0 is a stored default" claim holds: `render_reference.py:78-82` records group inputs
*regardless of links*, and `scripts/light_presets.py:456-457` links Render Layers → `Mist`, so the socket is live.

## Fix now

1. **fix now** — the carried-over glbs are not pinned to the regenerated `.gltf` they are validated against.
   `export/gate3_relay_check.py:93-96` reads UV2/COLOR_0 values out of `<cls>.gltf` and presence out of `<cls>.glb`;
   `export/verify_glb.py:196-211` compares the two. This round only env was re-packed, and in the worktree
   `export/out/gate1/arch.gltf` is 14:48:10 while `arch.glb` (and `arch_ktx2.gltf`, the pack input) is **14:15:49** —
   the PASS describes a `.gltf` the shipped glb was not built from. Counts happen to match this round, so nothing is
   wrong today; but a changed UV2 layout, a renamed/recopied material or a different primitive→material assignment
   would be invisible: `verify_glb` compares triangle *counts* and material *name sets*, never UV values or node and
   material order, and the relay never opens the glb's geometry. One comparison closes it:
   fail (or re-pack) when `<cls>.glb` is older than `<cls>.gltf`/`<cls>_ktx2.gltf`, in `verify_glb.py` and
   `gate3_relay_check.py`. Until then the README should say which class glbs are carried and from which run.
2. **fix now** — `export/manifest_v4.py:391-392`: `mp = g3.OUT / "mist_settings.json"` is local-only and the whole
   block is `if mp.exists():`. `export/out/` is gitignored (`.gitignore:31`), so after the merge the lead's
   `manifest_v4.py` run in MAIN finds no file and drops `compositor.mist` **silently** — the viewer keeps the 0.0
   haze and nothing says so. Use the same local-then-MAIN `next(...)` resolution as the relay at `:41-43`, and print
   a warning (or record `compositor.mist = null` with a reason) when neither exists.

## Carry

3. **carry** — `export/gate3_relay_check.py:268-270`: with a global range the per-mesh max tolerance is
   `1e-3 * 43.32 = 0.043` *absolute linear* — vacuous for the dim meshes (broadleaf mean 9e-6), 1-3 orders looser than
   the per-mesh version for the rest; the comment claims "to within the 16-bit step at that code", which is not what it
   tests. Use `1e-3 * lin_npz.max() + 2*sqrt(max*rng)/65535`. The unique-value mean test at `:281` guards it today.
4. **carry** — docs/decisions.md's 2 % fallback rule ("keep the 14 out of `-mi` if any mesh above 0.01 exceeds 2 %") is
   nowhere in code: `roundtrip_rel_p99` is reported at `gate3_relay_check.py:250`, never asserted. Two lines fix that.
5. **carry** — `export/manifest_v4.py:156-163` publishes the global range without checking it against the per-row
   `range` values it also copies at `:185-190`. A half-updated relay (new global key, old rows) would ship a wrong
   single number with no complaint; assert they all match.
6. **carry** — stale "per mesh" wording left in three places that a reader will take as the contract:
   `gate3_relay_check.py:290` ("copies `range` PER MESH … (ONE global `range` …)", self-contradictory in one sentence),
   `gltf_gate1.py:504` ("the gamma-2 per-mesh encode needs") and `gltf_pack.sh:136` (the `-vc 16` rationale).
7. **carry** — `export/read_mist.py:43-48`: the note's `mist = intensity + (1 - intensity) * t` and the `height` fade
   are Blender-Internal/EEVEE-era semantics; Blender syncs only start/depth/falloff to Cycles' film, so a future
   non-zero `intensity`/`height` would change nothing in the render while a viewer following this note would apply it.
   Both read 0.0 today, so the shipped formula is right. Say "Cycles uses start/depth/falloff only".
8. **carry** — `export/manifest_v4.py:398-409` stops at the mist *pass*; the shipped haze is
   `airlight = 0.25 * (1 - exp(-5 * mist))`, geometry only (`scripts/light_build.py:299-300`). A viewer fogging
   linearly in `mist` is 5x off near the camera. Record cap/k beside `compositor.mist`.
9. **carry** — `export/read_mist.py` never asserts the opened blend is `master_delivery.blend` (it records the path,
   which is the saving grace). One `assert bpy.data.filepath == str(g2.SRC_BLEND)` makes a mis-aimed run loud.

## Could not verify (no Blender, gltfpack, npm or Chrome)

- README item 26's per-mesh round-trip table (0.92 % worst, 26 %/14 % on the two shadowed meshes): it lives in the
  gitignored `uv2_relay_status.json`; the committed logs carry only the means. The 12-vs-2 split and the means are
  confirmed, the error figures are the branch's own report.
- `-6 004 B` and `43.31983947753906` are read from `export_gate3_verify_r3.log`; the arithmetic checks out.
- That `-vc 16` survives into the packed glb (r1 carry 6 still open: the glb test is presence-only), and that `-mi`
  instances primitives across trees — the premise of the whole change is the viewer's round-13b measurement.
