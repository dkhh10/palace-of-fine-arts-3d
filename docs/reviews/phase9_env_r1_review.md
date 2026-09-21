# phase9-env r1 (f854f93) — MERGE WITH FIXES

Verified by re-running/reading, not by trusting the report: tiles regenerate **byte-identical** (md5 match on all four PNGs,
scratchpad copy of `env_p9_tiles.py`, numpy/PIL only, nothing fetched → CC0 holds); channel means 0.5050 ±0.0001, sizes
1024²/512²/512²/1024², densities 64.0x77.6 / 32 / 64 / 42.7 texels/m as claimed; min texel gives min gain 0.40/0.21/0.34/0.16
(all positive). `BACKDROP_HAZE` triples match `mat_build.py:1970-1978` exactly and the report's export table matches
`BACKDROP_TILES`; `apply_backdrop_tiles()` runs after `apply_backdrop_atmosphere()` (`mat_build.py:2025-2028`), Non-Color,
REPEAT, `uv_map="UVMap"`, same `LENGTH(xy)` radius as the atmosphere node. mat_build diff is the new block + one call line,
no other material. UV0 re-run is clean (deterministic name hash, `.get` before `.new`, no layer duplication). ENV tri delta 0
(15,444,910 / 5,298,928 / 833,874, 6042 obj) equals main's last ENV build (`renders/logs/p8d_belt_r2_build5.log:162-165`).
Before/after really are two `lead_build.sh` runs (master 164 vs 166 MB, 18:41 vs 18:54). Blends +3.8 MB / +0.2 MB, tile PNGs
1.0 MB total, image paths relative (`//textures/backdrop/...`), worktree clean, commits carry "no suite" + attribution.

1. **fix now** — `scripts/env_p9_tiles.py:31,206-208`: `bd_rooftile` is **not tileable**. 8.0 m / 0.33 m = 24.24 courses and
   8.0 / 0.30 = 26.67 pans per tile, so the phase breaks at every wrap. Measured on the committed PNG: wrap |Δ| 0.149 (V) /
   0.116 (H) against interior neighbours 0.004-0.013 → a hard line every 8 m on every mission-tile roof. (facade 0.175 vs its
   own storey boundaries 0.170-0.222 and roof 0.183 vs its seam rows 0.10-0.20 are fine; canopy is seamless, 0.3-0.8x.)
   Fix: tile 7.92 x 8.10 m (24 courses x 27 pans) in both `env_p9_tiles.TILES` and `env_p9_uv0.TILE`, regenerate.
2. **fix now (cross-owner)** — `env_p9_uv0.py` puts "UVMap" at index 0 on the 1 291 backdrop meshes. `gate1_set.py:804`
   does exclude `kind=="backdrop"` from the UV1 groups and `gate2_common.py:136-145` adds UV1 only when absent, so the layer
   survives — but that **shifts the baked backdrop atlas from TEXCOORD_0 to TEXCOORD_1** in env.glb, where today it is the
   only UV set. `web/src/lightmaps.js:130,239` and the backdrop materials assume the current indexing. Merging ENV alone is
   safe for Cycles and breaks the next bake/export: land it with the export/viewer change, or pin it in docs/status.md.
3. **fix now** — `scripts/env_p9_uv0.py:60-61`: the `while` loop *deletes* layer 0 until "UVMap" is first. Correct for today's
   empty-UV backdrop, destructive for any future backdrop-material mesh that carries a real map (impostor, leaf card) — the
   safety check at :136 only covers non-backdrop materials. Fix: if `me.uv_layers` is non-empty and lacks UV_NAME, skip + print.
4. **fix now** — `scripts/env_p9_probe.py:120-123` vs `:139`: `belt()` is defined *after* the `__main__` guard, so the report's
   "`python3 scripts/env_p9_probe.py` -> `belt()`" does not print the item-2 table. Fix: move the guard to the bottom, add `--belt`.
5. **carry** — the item-2 shrub hash (4 137 objects, md5 `748f3343…`) was measured by `/tmp/shrubhash.py`, which is not in the
   diff; the claim cannot be reproduced. Commit it as `scripts/env_p9_shrubhash.py` or a probe subcommand.
6. **carry** — neither pair is reproducible from the repo: no script writes the flat-0.505 stand-ins the Cycles control swaps in
   (`env_p9_cycles.py` only renders), and nothing records how the "before" master's `assets/*.blend` were reverted to main.
   Fix: a `--standin` flag and two lines of recipe in the report.
7. **carry** — Cycles does no mip filtering, so a 64 texel/m tile minified to ~1 px/m at 506 m aliases; part of the control's
   +27.6 % hf (mean |laplacian|, noise-sensitive) may be sampling noise, not structure. Re-check one box at higher spp or after
   a 2 px blur before the 4K hero is judged on it. The "33.5 % of pixels move > 4 levels" number is not affected.
8. **carry** — report §"Item 1" facade `channel sd 0.128` is stale (round-3 value; committed tile measures 0.122); `env_p9_probe.py:27`
   hard-codes the MAIN path instead of `common.REFERENCE_DIR` / `$PFA_MAIN_ROOT`.
9. **carry (lead)** — the APPENDS finding is correct: `build_master.py:15` `LINK = "--link" in args` and `lead_build.sh` passes
   none, so master.blend holds no libraries. **CLAUDE.md:36 "The lead assembles master.blend by linking" is stale** — fix it.
