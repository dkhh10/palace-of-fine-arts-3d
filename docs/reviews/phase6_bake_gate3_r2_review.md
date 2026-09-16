# phase6-bake @ 73d5bb0 — Gate 3 r2: ceiling flip-bake + sky-branch probe — MERGE WITH FIXES (3 fix now, 9 carry)

Read-only review. Diff is `export/*.py` + `renders/logs/*` only (`git diff --stat main...phase6-bake -- scripts web
docs` is empty), no `save_as_mainfile` in any of the four new/changed scripts, every write under `export/out/gate3/`.
The four claims check out against the artefacts on disk. No correctness defect in the shipped ceiling map.

## Fix now

1. **export/gate3_common.py:84 — `BAKE_DIFFUSE_WORLD = bool(os.environ.get("PFA_BAKE_DIFFUSE_WORLD"))`.**
   Any non-empty value arms it, including `0`, `false`, `off` — i.e. the spellings someone uses to *disarm* it.
   The environment is inherited: `bake_queue.sh` → `scripts/blender_run.sh` exec Blender with no env scrub, so one
   exported variable in the operator's shell silently re-baked 47 jobs against a different world. Unlike
   `PFA_LM_DRYRUN` (which trips the queue's `rc 90` no-record guard, bake_queue.sh:158) this fails silently: the only
   trace is `rec["rig"]["diffuse_world"]` per job, which is post-hoc. Parse `in ("1","true","yes","on")`, and echo the
   armed state once in `bake_queue.sh`'s status/log header so a queue run states which world it used.
2. **export/README.md — not touched by this branch.** Neither `FLIP_NORMALS_FOR_BAKE` nor `PFA_BAKE_DIFFUSE_WORLD`
   appears in it (`grep -n "flip\|DIFFUSE_WORLD"` → only unrelated v-flip text). The flip is now permanent behaviour
   for that asset on every future re-bake, and the export/viewer engineers read the README, not `gate3_common.py`.
   Add both to "Gate 3 — what the bake found", with the QA-13-2 numbers and the "bake-process only, blend never
   saved" contract. (Prior review's carry 11 on `docs/tech_notes.md` is still open as well.)
3. **`.claude/worktrees/phase6-bake/export/out/gate3/manifest.json` — stale.** It still carries
   `lightmaps.assets.ARCH_rotunda_plaster_ceiling_merged.range = 0.721332`; MAIN's regenerated copy has
   `16.755167`. Anything run from the worktree (relay_check, a local viewer sync) would decode the new map ~23x too
   dark. The split is deliberate (the lead owns `manifest_v4.py` in MAIN), so delete or regenerate the worktree copy
   rather than leave a wrong-range file where a script can find it.

## Carry

4. **bake_lm.py:129 — the facing assert is on the mean.** `nz_after < 0 < nz_before or …` catches a sign flip of the
   *area-unweighted mean* only; a mesh with mixed windings averaging near zero would pass silently. Fine for this
   asset (mean |n.z| 0.9227, `area_normal_up = 1.000`), weak as a general guard: assert per-face sign inversion.
5. **bake_lm.py:104 — the flip edits `ob.data`.** If a second object in `gate3_bake.blend` shares that mesh
   datablock its winding flips too (two jobs in `bake_jobs.json` already show shared meshes). One cheap line:
   `assert me_.users == 1`. Cross-job leakage is impossible (one Blender per job, blend never saved) — confirmed.
6. **bake_lm.py:104 / gate3_ceiling_probe.py:177 — geometric vs shading normals.** The probe measures
   `polygon.normal`; Cycles shades with split normals. `flip_normals` and custom split normals do not always agree.
   The 0.721 → 16.755 result proves it worked *here*; a generic flip path should assert `has_custom_normals` is False.
7. **gate3_skybranch_probe.py:101-105 — dead branch.** The `PFA_SKIP_C` assignment to `rep["real_world"]` is
   overwritten unconditionally two lines later, so the JSON never records that part (c) was skipped. Report-only.
8. **gate3_skybranch_probe.py:46 (CAM02) and gate3_scene_audit.py:28-35 (STATIONS) — hard-coded stations.** The
   canonical set is `scripts/qa_cameras.py` / the Gate 2 manifest (which `bake_lm.py` already reads for the probe).
   Drift risk; import them.
9. **gate3_scene_audit.py:23 — `MAIN = Path("/Users/…")` with no `PFA_MAIN_ROOT` override**, unlike
   `gate1_common.py:20`, `manifest_v2.py:22`, `bake_queue.sh:21`. Same pattern as `gate0_common.py:17`, so it is a
   consistency carry, not a break.
10. **gate3_skybranch_probe.py:262-276 — the (b) mask is one centre ray per pixel against a 32-spp AA render.**
    Silhouette pixels mix sky (pure red) into `mean_arch`, which is the likely source of the residual R = 0.108 in an
    otherwise green result. It does not change the verdict (green dominates 8x) but it should be named in the report
    rather than left as an unexplained red fraction. The mask itself is sound: sky = no hit, foliage excluded by the
    `ARCH_`/`EXPM_ARCH`/`INST_` prefix test, `hob.original` resolves instances, and `hide_viewport` is synced to
    `hide_render` before the cast (probe:254-256).
11. **gate3_skybranch_probe.py:107-155 — no `try/finally`** around the Light-Path link isolation, the all-mesh
    hide, the temporary pano camera and `sc.camera`. That region is exactly where the first two runs went wrong
    (empty scene). In-memory only, so nothing can be corrupted, but a mid-part exception leaves parts (a)/(b)
    measuring a scene nobody described.
12. **Slot / vertex kinds have no flip path.** `FLIP_NORMALS_FOR_BAKE` is only consulted in the `own` /
    `own_gate1uv2` branch. Acceptable because the six-station sweep found no second candidate over 200 px, but if a
    future sweep finds one inside a slot batch the fix will not apply.

## Verified against the artefacts

- **Flip, claim 1.** `out/gate3/bake/lm_ARCH_rotunda_plaster_ceiling_merged.json`: `flip_normals_for_bake
  {polys: 529, mean_normal_z 0.9227 → -0.9227, uv_layout_identical: true}`, `bake_s 1313.8`, `samples 128`,
  `rig.world = rig.world_before = WORLD_golden_hour`, `diffuse_world: false` — the shipped re-bake was unarmed, and
  the UV assert compares the per-face *sorted corner UV sets* read from the loop layer actually baked
  (`uv.foreach_get("vector")`), which is the right, order-insensitive test for a winding reversal.
  `gate3_set.py:288` derives the job flag from the same constant, so it is not hand-set.
- **In-place replacement, claim 1.** `encode.json` → `range 16.755167`, `range_first_pass 32.0`, `max 16.755167`,
  `mean_nonzero 2.056919`, `clipped_px_vs_range 0`, `signal_frac 0.2877`. `manifest_v4.py:31-33,107` prefers
  `encode.json`'s range over the bake record's (which still reads 32.0 by design), and MAIN's manifest carries
  16.755167 with `bytes` 5 338 208 / 1 619 649 — byte-for-byte the two ktx2 files on disk, so no stale entry.
  `gate3_pack.sh:23` does `rm -rf "$KTX"` before repacking, so no stale KTX2 or mip chain can survive; `compose.json`
  contains no ceiling key. The only stale artefact anywhere is finding 3.
- **Probe faithfulness, claim 2.** `scripts/light_calibrate.py:216-231`: the real world gates on exactly
  `Is Camera Ray` and `Is Glossy Ray` (ADD → MIN 1.0), everything else keeps `diffuse_boost` and the tint. The debug
  world's `G = 1 − (camera + glossy)` is therefore *the same set*, so the fact that shadow, transmission and volume
  rays also land in G does **not** weaken the conclusion: they take the diffuse branch in the real world too. And the
  load-bearing number is R = B = 0 exactly over 3 629 texels — no camera flag, no glossy flag, whatever G contains.
- **47/18 split, claim 3.** Computed from `bake_jobs.json` by kind: 47 in (`own`, `own_gate1uv2`, `slot`, `vertex`),
  18 in (`impostor`, `sky`, `probe`). Derived, not hard-coded — only the wall-second figures in the comment are text.
- **Audit, claim 4.** `gate3_scene_audit.py:246-258` applies `g0.apply_final_cycles_checked` plus exactly the
  overrides `bake_lm.prepare()` applies, then diffs lights / cycles / world / bounce materials against
  `master_delivery.blend` opened read-only. Method matches the claim.

## Could not verify (no Blender, read-only)

Whether the ceiling mesh datablock has a second user; whether it carries custom split normals; that the flip precedes
any modifier evaluation the bake uses (no modifier stack is visible in the scripts, and the result implies none);
and the completeness of `sync_main.sh` beyond the two ceiling ktx2 files I compared (it runs without `--delete`, so
orphans in MAIN are possible in general — not for this change, whose keys are unchanged).
