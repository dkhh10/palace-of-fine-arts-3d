# phase9-backdrop-export r1 — code review (Opus 5, read-only, no Blender/Chrome), 2026-09-21

**SEND BACK** — one blocker: the `-vtf` fix was applied to the class pack but not to the pack that
builds the glbs the viewer actually fetches, so the shipped env groups carry exactly the defect the
flag exists to prevent. Everything else in the round verifies.

1. **BLOCKER — `export/tiers.py:81** `PACK_FLAGS["env"]` has no `-vtf`. `gltf_pack.sh:274` only fixes
   `gate1/env.glb`, which is **not a shipped file**: `gate5/manifest.json` ships `groups/env_t0.glb`,
   `groups/env_t2.glb` and the `m_*` twins, re-packed by `tiers.pack()` from `env_ktx2.gltf`.
   Measured on the shipped `export/out/gate5/groups/env_t0.glb` (built 19:55 this round):
   both TEXCOORD sets are `componentType 5123` normalized under ONE `KHR_texture_transform`,
   `MAT_EXP_ENVBD__MAT_backdrop_building` scale **483.89 x 162.12**, `..._roof` 301.86, `..._skylight`
   349.02, all with `baseColorTexture.texCoord: 1`. With gltfpack's 12-bit texcoords that leaves the
   [0,1] bake atlas **~8.5 steps in U / 25 in V** (4096/483.89) — ~120 atlas texels per step, i.e. the
   city's baked albedo posterised. `uvDequant.js:107` applies the shared transform to `uv` and `uv1`
   alike, so the values are right and only the precision is gone — silent in every count.
   Fix: add `-vtf` to `PACK_FLAGS["env"]`, re-run the group pack, re-measure tier 0 (env_t0 is tier 0
   and the desktop first frame has only 106 kB of headroom to the 49.5 MB target — if float UVs push it
   over, split the backdrop merges into their own group rather than dropping the flag).
2. **BLOCKER (same defect, why it passed) — `web/test/backdrop_tiles_test.mjs:142** the quantisation
   check points at `export/out/gate1/env.glb`, an intermediate. Point it at the published glbs
   (`gate5/groups/env_t0.glb`, `env_t2.glb`, `m_env_t0.glb`, `m_env_t2.glb`) — it fails there today.
   `verify_glb.verify_gate5` (`verify_glb.py:701`) likewise checks the manifest rows but never the
   groups' accessors.
3. **fix now — `export/README.md:3102` / report §3.3** "no shared box, no transform, and nothing for
   `web/src/uvDequant.js` to apply to the wrong set" is false for every file that ships; correct the
   claim when 1 is fixed.
4. **carry — `export/gate2_common.py:162`** the re-bake guard is a span test (`> 1.5`), the very test
   `gltf_gate1.py:161` documents as unable to do this job: `backdrop_door_green`'s tile UV spans 0.941,
   so `smart_project` would still overwrite it (no gain tile on that group, so cosmetic today). Use the
   same npz comparison, or assert on "a second UV layer exists".
5. **carry — `web/src/backdropTiles.js:34`** `VERT` hard-codes the `uv` attribute while the manifest
   declares `tileChannel`; `checkUvContract:82` only tests that the two channels differ. A consistent
   relabel (tile=1, baked=0) passes the viewer check and samples the wrong set — only
   `verify_glb.py:707` catches it, export-side. Either honour `tileChannel` in the patch or assert it is 0.
6. **carry — `web/src/main.js:1705`** `?bdtiles=0` never calls `applyBackdropTiles`, so the shader is
   byte-identical to the pre-Phase-9 one — correct, but untested, and the off run also never fetches the
   four tiles, so the A/B is pixel-neutral, not payload-neutral. Say so in the QA-26 note.
7. **carry — `web/src/pbr.js:170`** `texcoord_conflicts` is recorded and then the channel is overwritten
   anyway; nothing fails on a non-empty list.

**Verified as claimed** (no finding): sha256 table exact — arch/orn/ground/env_trees/env_trees_lod1/
env_shrubs byte-identical, `env.glb` `d310e19a…` 38 560 908 B; +1 570 072 B is plausible for the second
float UV set (388 046 backdrop vertices x 8 B = 3 104 368 raw, ~51 % after meshopt). Payload read back
from the shipped manifests: desktop tier 0 48 243 816, first frame **49 393 685**; mobile 46 312 049 /
**47 450 506**; four tiles tier 1 (597 927 B desktop, 92 479 B `tex_lo` mobile), `texcoord: 1` on 8 of 62
sets in both variants, `backdrop_tiles.uv` tile=0/baked=1. `npm test` in the worktree **819 PASS, 0 FAIL,
rc 0**, no SKIPs. Relay targets the layer by npz comparison, not by name (`gltf_gate1.py:155-168`);
gate5/tiers/manifest rows are consistent; scope clean (export/ backdrop class, web/src backdrop +
pbr channel, web/test, READMEs, regenerated budget doc); no tracked binaries; every commit carries its
suite count.
