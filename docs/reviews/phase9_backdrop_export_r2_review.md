# phase9-backdrop-export r2 — code review (Opus 5, read-only, no Blender/Chrome), 2026-09-21

**MERGE WITH FIXES** — both r1 blockers are closed in substance, verified on the shipped files rather than on
the report. One sentence of the corrected README is still wrong and r1 carry 4's new guard is inert as written.

1. **fix now — `export/README.md:3144`** "first frame 49 314 019 B = 49.31 MB … *under* the pre-round 49.39 MB":
   49.39 was the **r1 pack**, not the pre-round state (the report's own table: before the round 48 128 039 /
   49.30 MB), so the round still adds ~36 kB to the first frame. `…_report.md:113` says it right ("below the
   first (quantised) pack"). Fix: "under the r1 (quantised) pack's 49.39 MB; +36 579 B on tier 0 vs pre-round".
2. **carry — `export/gate2_common.py:164`** `assert uv_layers.get("UVBake") is None` cannot fire: `UVBake` is
   created by `gltf_gate1.py:129/169` in the **export** session and never saved — a byte grep of
   `gate1_set.blend` and `gate2_bake.blend` (the only blends `smart_uv1` sees) finds `UVBake` 0 times, `UVMap`
   171 / 190. The span backup is again the only live test, and `backdrop_door_green` (0.941) still slips it.
   One-liner that works: a `CLS_BACKDROP` mesh has no UV1 in the Gate 1 set (`gate2_set.py:236`) — assert
   `lay is None`; or compare against `backdrop_uv1.npz` the way `gltf_gate1.py:155-168` does.
3. **carry — `web/test/backdrop_tiles_test.mjs:200-203`** the group list is `.filter(existsSync)` and SKIPs only
   when **none** exists, so a partial `gate5/groups` silently loses coverage — assert 4/4 found. `glbPath`
   (line 142) is now dead; remove it.
4. **carry — `export/verify_glb.py:753`** `group_primitives_float = q_prims - len(set(q_bad))` subtracts a count
   of groups from a count of primitives; right only when nothing is bad. Report `float / total` instead.
   (`bad` is filled correctly, so the gate itself still fails.)
5. **carry — the counterfactual is prose only.** The 483.92 -> 8.5-of-4096 re-pack lives in commit 1c4edba and
   three docs; nothing on disk reproduces it (`grep -r "483\.9"` finds nothing outside the docs). Keep the
   no-`-vtf` re-pack measurement as a log or fixture so the test's negative case is runnable.
6. **carried from r1, unchanged (all carry):** `backdropTiles.js:34` `VERT` hard-codes `uv` while the manifest
   declares `tileChannel`; `main.js:1705` `?bdtiles=0` is pixel-neutral, not payload-neutral (say so in QA-26);
   `pbr.js:170` `texcoord_conflicts` never fails.

**Verified by reading the shipped files.** All four `export/out/gate5/groups/{env_t0,env_t2,m_env_t0,m_env_t2}.glb`
(20:11-20:12): 4 backdrop primitives each, TEXCOORD_0 **and** TEXCOORD_1 `componentType 5126`, `normalized false`,
**0** `KHR_texture_transform`, `baseColorTexture.texCoord 1` — blocker 1 closed (`tiers.py:88` carries `-vtf`).
Shipped manifests, regenerated 20:12, `files[]` bytes == disk (`env_t0` 2 196 928, `env_t2` 7 149 836, `m_*` the
same): desktop tier 0 **48 164 618**, first frame on wire **49 314 019** (target 49 500 000, rule 50 000 000,
`tier0_within_target` true); mobile **46 542 733** / **47 681 185**; `tier0_trim.moved` 32 desktop / 0 mobile as
claimed; **0** of 746 / 345 published files over the 26 214 400 B cap (largest 16 684 808). `npm test` in the
worktree **828 PASS, 0 FAIL, rc 0, no SKIPs**, including the 12 new per-group assertions (`env_t0 … 4/4 float,
0 transforms`) — blocker 2 closed; `verify_glb.py:730-751` reads the same accessors. Scope clean: 7 files, all
this branch's (export/, web/, docs/briefs), no binaries, no other owner's file touched.
