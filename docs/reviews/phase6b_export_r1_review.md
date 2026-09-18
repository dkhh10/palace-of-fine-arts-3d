# MERGE WITH FIXES

Branch `phase6b-export` @ 67c990e vs main 441594b (7 commits, +2041 lines, no other owner's files touched, no
binaries committed). Brief `docs/briefs/phase6b_export.md`, report `docs/briefs/phase6b_export_report.md`,
export/README.md items 27-34. Read-only review; every number below was re-measured from MAIN `export/out/gate5`.

**Verified independently (holds).** Asset coverage: 2540/2540 across the 4 real groups + arch.glb + ground.glb,
**0 duplicates**, placeholders excluded from the count (verify_glb.py:470-500). Instancing survives the split:
gate1 orn.glb has 32 EXT_mesh_gpu_instancing nodes, the two ORN groups have 32; env 34 -> 35, triangles drawn
exactly 679779 = Gate 3. Normal drop is safe: all 33 ORN glTF materials carrying `normalTexture` declare
`normal.replaces_gate1`, the 33 replacements are all published (27 tier 1 / 6 tier 2, 27 also at half-res in
tier 0), `occlusionTexture` kept on all 33 (27+6 in the packed groups), ENV untouched (0 dropped). README 29's
"86.3 MB saved" = 86,292,317 B measured. Every manifest block path resolves from MAIN out/gate5 (lut, 3 sky,
probe, gate1/2/3 ktx2_dir, foliage, 3 lazy glbs, all group textures). 0 files over 25 MiB; largest 16.7 MB.
Visibility ran at 640x360 (brief floor 480x270), 0 unknown first hits, 33 EXPHI_* excluded and named.
Treeboard exception is real: impostors are procedural planes (web/src/impostors.js:277), boards hidden by
default (main.js:94).

1. **export/gate5_common.py:38 / tiers.py:410-430 — the tier-0 total is not the first-frame payload. FIX NOW.**
   43.29 MB counts published assets only; the viewer must also fetch `manifest.json` (**2,475,405 B**, uncompressed)
   and `/basis/` (580 KB) plus the JS bundle before frame 1. Real tier 0 ~46.5 MB, so the headroom README 31
   calls "6.7 MB" is ~3.5 MB. Fix: add a `tiers.boot_overhead_bytes` block (manifest + transcoder) and test
   tier0+overhead against TIER0_BUDGET. (50 MB is read as decimal 50,000,000 — the stricter reading, consistent
   with the 6b definition of done; keep it.)
2. **tiers.py:355 — the probe (6.29 MB) is in tier 1, against the brief's tier-0 list. FIX NOW (report line).**
   Justified in export/README.md item 31 but absent from the report the lead actually reads; and with finding 1
   it cannot simply be moved back (46.5 + 6.3 > 50). Add the deviation + its cost to the report's tier section
   so the lead accepts it explicitly. Note tier 0 ships no lightmaps *and* no probe, so the first frame is
   sky-diffuse-lit only — the viewer engineer should know before Gate 5 capture.
3. **export/gate5_tex.py:169 — `--tier0-div` defaults to 4, the shipped set is /2. FIX NOW.** A rerun without
   the README's flag silently produces a quarter-res tier 0 (different bytes, different look) while tiers.py's
   own encode is hardcoded to /2 (tiers.py:519). Change the default to 2.
4. **tiers.py:544 — `shutil.rmtree(out/"groups")` on the desktop run deletes the mobile `m_*` groups that
   manifest_mobile.json references. FIX NOW.** Idempotency currently depends on the run order documented only
   in README. Fix: remove only `groups/{prefix}*` for the variant being built.
5. **Carry.** (a) `lowres.json` `wall_s` is accumulated across runs (tiers.py:527), so the report's ETC1S wall
   seconds inflate on every rerun; (b) `gate5_tex.py --mobile` writes `tex_mobile/`, which nothing reads (the
   mobile swap uses `tex_lo`) — dead path that sync_main would ship; (c) tiers.py:452 hardcodes orn/env byte
   figures (154 253 424 / 38 119 568) that disagree with `per_class_gate3` (154 065 360 / 35 797 240) — read
   them; (d) verify_gate5 compares triangles but never compares instanced-row counts to a Gate 3 figure (I
   checked by hand; the assertion is missing); (e) `scene.ray_cast` treats alpha-cut leaf cards as opaque, so
   the tier ordering is conservative behind foliage; (f) the deploy set spans `out/gate0..gate3` as well as
   gate5 — the report should say so, or the 6b deploy will 404 on `../gate0/lut...`.
