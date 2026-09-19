# Code review — `phase8d-export2` r6 delta (711a5a6, 8a89021, 66aace8 on 763f61c)

Reviewer: Claude Opus 5, read-only, no Blender, no Chrome. Judged from `git diff 763f61c..66aace8` in the
worktree, the regenerated artefacts under MAIN's `export/out/` (byte-identical to the worktree's — checked on
the three manifests, `env_trees.glb` and `instance_irradiance.json`), the 6c bake records kept in the
`phase6-bake` worktree, `npm test` re-run here, and CPU probes that need no Blender. Prior review:
`docs/reviews/phase8_export_r5_review.md` (blockers 1-2, fixes 3-10).

## Verdict: **MERGE** — the code is correct and both r5 blockers are closed in code and in the artefacts.
## Deploy: **DEPLOY BLOCKED** on finding 1 (an unannounced, unmeasured +48 % change to the lighting of every
## far tree, not only the 39 new ones). It needs a `docs/decisions.md` line and one QA station pass, not a re-bake.

Everything the brief asked me to check came back clean (findings 3-8). The blocker below is something the
chain did not look for: the re-bake did not only *add* 39 rows, it *moved* the 127 that were already there.

---

## 1. BLOCKER (deploy) — the re-bake brightens the existing 127 far trees by a median 1.49x, and nobody measured it

The r2 README says the cloned blends are "what keeps the new rows in the same scene and rig as the 127 that
were already there". The scene and the rig are indeed identical (finding 7). **The measured values are not.**
Joining the 6c file (`phase6-bake/.../instance_irradiance.json`, 2026-09-17, 127 rows) to the new one by world
location, all 127 old locations survive and:

| | old (shipped at 6c/8c) | new (this branch) |
|---|---|---|
| `rgb` luminance over the 127 | med 2.458 | med 3.684 |
| new/old luminance ratio | — | **min 0.83, med 1.49, p95 1.84, max 2.22** |
| rows within ±5 % of their old value | — | **4 of 127** |

The change is upstream of `trees_far_compose.py`: the raw `tfirr_*.json` bake items show the same shift
(mean-luminance ratio med 1.60), so it is the GPU bake, not the join or the encoding.

**It reaches the viewer at full strength.** `main.js:1094-1096` picks mode `full` whenever the manifest carries
measured per-prototype `E_bake` — it does, and `foliage_lazy_test.mjs` prints `mode full` on this manifest. The
denominator is bit-identical to 6c (all 16 `E_bake` rows unchanged), so the per-placement modulation
`E_placement / E_bake` moves with the numerator:

* existing 127, full-mode ratio luminance: **median 0.942 → 1.390** (i.e. the far-tree band goes from slightly
  darkened to ~1.4x brightened);
* nothing absorbs it: **0 of 381 channels** reach the 4.0 clamp, before or after;
* it is not a chroma-only shift either (max channel change 0.83 in chroma mode).

**Most likely cause, and why it is probably a *correction*.** The bake bodies changed: **116 of the 127
placements report a different `verts` than in 6c** for the same mesh name (e.g.
`EXPM_treefar_ENV_tree_cypress_s3_LOD1` 14 147 → 13 883). The new counts equal the exported LOD2 topology
exactly — `vertex_ao.npz` (byte-identical to 6c, 17 arrays, all `allclose`) has 13 883 for that mesh, and
`trees_far.json`'s `color0` agrees (0 mismatches over 16 meshes). So the 8d bake measured the bodies the export
actually ships and the 6c bake measured something denser, which self-shadowed more and read ~1.5x darker. The
manifest itself names this term: *"what does not cancel between the two bodies is crown density"*.

That makes the new numbers the better ones — but it is still a look change to every far tree in the scene,
delivered in a round whose stated scope was "39 belt trees", measured by nobody, and absent from the README,
`docs/decisions.md` and the commit message. Per CLAUDE.md a look change is logged and decided, and per the
Phase 6 definition of done every station's parity is re-scored.

**Cheapest close (no re-bake):** (a) a line in `docs/decisions.md` stating that the 8d irradiance re-bake
corrects a 6c body mismatch and raises the far-tree modulation by ~48 % at the median; (b) one QA station pass
(hero + the two orbit stations) against the current deployment, confirming the far band did not blow out. Then
deploy.

## 2. Watch item — the 39 belt trees ship very dark (median modulation 0.24, 12 of 39 below 0.15)

Belt rows vs the other 127, in the new file: `rgb` luminance med **0.676** vs 3.684; full-mode modulation med
**0.242** vs 1.390; 12 of the 39 below 0.15, min 0.046. Physically plausible — `env_backdrop.build_hall_belt`
plants them 5-11 m off the hall's east face with the crowns sunk 0.25-0.90 m, so they sit in the hall's and the
colonnade's occlusion — and the bake scene is clean (I checked `gate3_bake.blend`'s object table by string
scan: **no** `ENV_backdrop_hall_belt` icospheres, `ENV_backdropgroup_backdrop_building` present, 127
`ENV_treeboard_*`, i.e. the pre-belt scene with the belt's own 39 LOD2 meshes added by `trees_far_set.py` and
mutually shading). Not a defect, but the belt is the thing 8d exists to show: QA should look at those 39 crowns
in the viewer at cam02/cam05 before the round is called done — at 0.24 they may read as silhouettes.

## 3. The instance-irradiance join by world location — correct for all 166 rows ✔

* `instance_irradiance.json`: schema `…/gate4-instance-irradiance/2`, 16 meshes, **166 rows**, 16 `prototypes`.
* The 0.02 m grid key is **unique**: 166 distinct cells for 166 rows; the closest pair of far trees is 0.476 m
  apart (`TREEFAR_100` / `TREEFAR_107`), 24 cells apart, so a mis-join is not reachable.
* Every one of `trees_far.json`'s 166 placements joins, **worst residual exactly 0.0 m**, `missing` empty — the
  39 belt rows included (39 locations are new-only against the 6c file, 0 old-only).
* Four `tfirr_*` bake records: 42 + 42 + 42 + 40 = **166**, all `rc=0` in `bake_queue/status.json`,
  `missing: []`, `zero_placements: 0` in all four, 128 spp, coverage_mean 0.91-0.95, 199.1 + 189.5 + 198.5 +
  192.2 = 779.3 s = **13.0 min**, as the README states.
* Luminance range 0.137-6.097, 0 zero rows, `cov` present on every row.

**3a (low).** The grid key is brittle by construction: locations are stored to 2 decimals, so **234 of the 498
coordinates land exactly on a half-cell boundary**, where `round()` is banker's rounding. It works today only
because the two files carry byte-identical values. A writer that changes its decimals by one would flip keys —
loudly (`missing` → assert), not silently, so it is a robustness note, not a defect. Consider keying on the
rounded centimetre value directly, or a nearest-neighbour join with the existing 0.02 m residual assert.

**3b (low).** Uniqueness is asserted on the *irradiance* side only; nothing asserts the map is injective from
the `trees_far.json` side (two placements in one cell would both take the same row). Unreachable at a 0.476 m
minimum separation; one `len(set(keys_used)) == len(tf["placements"])` would close it.

## 4. The guards — present, correct, and they fire on the right pair ✔

* `manifest_v4.py:947-965`: `len(tf["placements"]) == len(man["tree_far"])`, the **billboard identity row by
  row**, and `env_trees.glb` may not be older than `trees_far.json` (today 22:13:51 vs 22:13:40 ✔).
* `verify_glb.py` `--gate5` check 5 compares all four (five, with `tree_far` rows) counts in one place. Both
  shipped reports carry it: `far_tree_counts {tree_far_rows: 166, far_billboards: 166, far_mesh_placements:
  166, walkup_count: 166, lighting_rows: 166}`, `fail: []` desktop and mobile.
* `trees_far.py:657-663` pins `far` against `export_set.json`'s `tree_rule.far_billboards` (r5 fix 6);
  `g0` is imported (line 69), so the eagerly-built path tuple cannot raise `NameError`.
* **No `== 127` literal remains anywhere in `export/*.py`** (grep): `trees_far_compose.py:183` and
  `trees_far_set.py:214` now derive the count.

**4a (medium).** `env_trees_lod1.glb` gets **no** mtime guard — only its `st_size` is read. It is the other
half of the pair that was stale in r5. One more assert next to the `tf_glb` one (against
`trees_far_lod1.json`) closes the class properly.

**4b (low).** `tf_p` and `tf_glb` are resolved independently (worktree first, then MAIN), so a half-synced
checkout can compare MAIN's glb mtime against the worktree's report. Resolve both from the same root.

**4c (cosmetic).** The new block is commented "5." but is inserted *above* "# 4. the per-file cap"; and
`seen_counts = {k: v for k, v in counts.items() if v}` drops a legitimate 0 as well as None.

## 5. The manifests in MAIN — 166 everywhere, bytes match, the first frame reconciles ✔

| | gate3 | gate5 desktop | gate5 mobile |
|---|---|---|---|
| `tree_far` / `far_billboards` / `far_mesh.placements` / `walkup.count` / `lighting.mesh.placements` | 166 ×5 | 166 ×5 | 166 ×5 |
| `far_mesh.bytes` / `walkup_mesh.bytes` | 3 769 736 / 7 643 580 | same | same |

Both equal the files on disk (`env_trees.glb` 3 769 736, `env_trees_lod1.glb` 7 643 580) — the r5 stale-bytes
finding is gone. First frame: `transfer_bytes["0"]` 48 111 210 + boot 1 126 277 = **49 237 487** =
`first_frame_transfer_bytes`; + 36 288 headers = **49 273 775** = `first_frame_on_wire_bytes`, **726 225 B
under the 50 000 000 rule**, 218 files in tier 0. `npm test` in the worktree: **three r186, all passed**.

## 6. The viewer test change — does not weaken the test ✔ (with one gap that predates it)

`FAR_N = raw.trees.far_mesh.placements.length` replaces the literals 127 / 254. The synthetic glb was always
built *from the manifest's own placement table*, so the literal never pinned the count independently — it only
guaranteed the fixture manifest was the 6c one. What the test still proves, now at 166: the positional join
(332/332 rows → 166/166 placements), `placements.same_as` resolution, the LOD2 fallback, the impostor `iNear`
flip, the `mode full` / `mode chroma` modulation over all 166, and — the one genuinely cross-file check — that
`instance_irradiance.json` flattens to exactly `FAR_N` rows and that the normalised lighting has `FAR_N` rows.

**6a (low).** No test in `npm test` pins the far count to `export_set.json`; that pin lives only in
`verify_glb --gate5`, which the suite does not run. If the manifest were internally consistent but wrong, the
suite would stay green. Cheap fix: have `tiers_test.mjs` (which already reads the gate5 manifest) assert
`tree_rule.far_billboards === trees.far_mesh.placements.length`.

## 7. The cloned bake inputs — same scene, same rig, byte for byte ✔

`gate3_bake.blend` md5 `7c437c3e92182ccea77d41c563f276c9` and `gate3_imp.blend` md5
`4f3fcb89778162a2f423fcd652714bb3` are **identical in the `phase6-bake` and `phase8d-export` worktrees** (same
sizes, same mtimes), and `trees_far/ao` + `trees_far/ebake` (16 + 16 files) hash identically as a set. The bake
rig dict in `tfirr_00.json` is `==` to 6c's (20 lights, 128 spp, adaptive off, OIDN, same world); the override
scope's material list is identical, objects 127 → 166, sharers 290 → 329. `trees_far_set.json` differs from 6c
only in `generated`, `placements` 127 → 166, `wall_s`, and `irr.source_trees_missing` 0 → **39** — expected and
correct: the belt's source trees do not exist in the pre-belt bake blend, so there is nothing to hide for them.
The one thing that is *not* the same as 6c is the placed bodies — finding 1.

## 8. r5 fixes 3-10

| r5 fix | status |
|---|---|
| 3 `manifest_v4` count + billboard asserts, mirrored in `verify_glb` | **done** (finding 4), with gap 4a |
| 4 `trees_far_compose.py` / `trees_far_set.py` hard-coded 127 | **done**, both derive the count |
| 5 `billboard_reindexed` measured by tree, not by index | **code done, artefact stale** — the shipped `export/out/gate1/p8d_pin.json` is still the 22:10:28 file and still says `billboard_reindexed: 0`. The corrected code has never been run, and after `sync_main.sh` it cannot be. Note the true value (87) in the JSON or in the README so the record does not contradict the review. |
| 6 pin `far` against `export_set.json` | **done**, import safe |
| 7 pin glb rows carry mtimes + a sync note | **code done, artefact stale** — same file; its `glbs` block still reports `env_trees.glb` 3 768 500 / `env_trees_lod1.glb` 7 642 344 as `identical: true`, both now wrong on disk, with no `mtime_*` or `_note` field. |
| 8 `p8d_pin.py` docstring | **done**, and accurate (166 / 85 / 20 / −6 822) |
| 9 stale 127 / 254 / 46 references | **partial**. `p8e_leaf_probe.py` ✔, README r1 runbook block ✔ (v2 before v3, `rm -rf` comment corrected). **Still shipping inside the delivered manifests** (gate3 *and* both gate5 files): `"46 of the 127"`, `"the 127 real far trees"`, `"the 127 billboard quads"`, `"until it is in, the 127 far trees are the impostors"`, `"254 rows for 127 trees"` ×2 — `manifest_v4.py:529-530, 644/660, 970, 992, 1047`. Also `web/src/impostors.js:705` and `export/gate3_set.py:16,18,23,215` (comments). These are strings a consumer reads as the contract; the counts they state are now wrong by 39. |
| 10 state the `CLASS_BUDGET["ENV"]` decision | **done** (README r2 follow-ups, first bullet) |

---

## Fix list

| # | Fix | Severity | Blocks merge | Blocks deploy |
|---|-----|----------|--------------|---------------|
| 1 | The re-bake moves the existing 127 far trees' modulation from med 0.942 to 1.390 (+48 %); cause is a 6c body mismatch the re-bake corrects. Log it in `docs/decisions.md` and re-score the stations before deploying. | **blocker** | no | **YES** |
| 2 | The 39 belt trees ship at med 0.24 modulation (12 below 0.15). QA should eyeball them at cam02/cam05. | medium | no | no (watch) |
| 3 | `env_trees_lod1.glb` has no mtime-vs-report guard (4a). | medium | no | no |
| 4 | `p8d_pin.json` in MAIN is the pre-fix artefact: `billboard_reindexed: 0` and stale tree-glb rows (fixes 5 and 7 are code-only). | medium | no | no |
| 5 | Six stale "127 / 254 / 46" statements ship inside the three delivered manifests (fix 9, unfinished). | medium | no | no |
| 6 | `tf_p` / `tf_glb` resolved from different roots (4b); check numbering and the falsy filter in `verify_glb` (4c). | low | no | no |
| 7 | The world-location grid key sits on a half-cell boundary for 234 of 498 coordinates (3a); the join is not asserted injective from the placement side (3b). | low | no | no |
| 8 | No test in `npm test` pins the far count to `export_set.json` (6a). | low | no | no |

Merge the branch. Do not deploy until finding 1 has a decision entry and one QA station pass.
