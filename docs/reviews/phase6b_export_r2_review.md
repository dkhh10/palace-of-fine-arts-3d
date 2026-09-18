# MERGE WITH FIXES

Delta review of `phase6b-export` 67c990e..01905e5 (2 commits, +803/-92, only export/ and its own report). Every number below
re-measured by me from MAIN `export/out/gate5` with my own gzip -9 / stat, never read out of the manifest.

**Holds, verified independently.** (1) `first_frame_transfer_bytes` is computed as claimed: all 588 desktop / 341 mobile
`files[*].transfer` reproduce exactly (gzip -9 for json/js/css/html/txt/svg/map, st_size for ktx2/glb/wasm/hdr/cube), tier 0
48,401,404 + boot 1,090,421 (page 622, bundle 321,602, transcoder 15,063 + 527,333, manifest 225,801) = **49.49 MB, WITHIN
50,000,000, 508 kB headroom**; mobile 47,516,395, 2.48 MB headroom; every boot path exists in `web/dist`. (2) tiers.py:757-764
deletes only the entries whose `m_` prefix matches the variant, so desktop and mobile no longer wipe each other (`groups/` has
no subdirectories, `f.unlink()` is safe). (3) The instance_irradiance join cannot silently mismatch: nearest placement by
instance translation, residual <= 0.02 m AND runner-up >= 3.0x further, double claim raises, scoped per variant
(gate5_instance_rows.py:70-106); **1376 / 1379** is what MAIN's `instance_order_groups.json` and both manifests say, the 3
unmatched `.001` cards named, `groups_complete: false`. (4) **0 of the 11 group glbs carry an image with a bufferView** (I
parsed each JSON chunk). (5) All 245 desktop `lowres.files[k].full` paths exist on disk and are in the plan at tier 1; 0
missing files either variant; `verify_gate5_*` 2540/2540, `fail: []`, written after the manifests. Also good: `--tier0-div`
default 2, `tex_mobile` refused explicitly, `wall_s` no longer cumulative, `uv2_relay_status.json` tier 0 in both, no
placeholder groups, 0 duplicate assets across groups.

1. **tiers.py:704-710 — the fixed-point resync is indented under `if unpublished:`. FIX NOW.** The loop at 676-684 mutates only
   `boot` (shared object, so that propagates); `first_frame_transfer_bytes` / `tier0_within_budget` are rewritten only when the
   plan is INCOMPLETE. The shipped desktop manifest shows it: recorded manifest transfer 225,801 vs its own gzip 225,802,
   `first_frame` 49,491,826 against the 49,491,825 its own fields give. 1 byte, harmless at 508 kB headroom, but "iterated to a
   fixed point" is not what the code does. Fix: dedent those three lines.
2. **The "-20.8 %" qlevel-32 normal claim has no measurement of the shipped set. FIX NOW (report + README line).** The branch's
   own `lowres.json` gives it: `tier0` 3,057,292 B at qlevel 128 -> `tier0_normals_qlevel` 2,520,098 B over all 46, **-17.6 %**
   (537 kB). -20.8 % is a hand sample of five files, and "RMS unchanged to five decimals" has no artifact at all
   (`rms_vs_source` is wired only to `gate5_tex.py --probe`). Restate as -17.6 % measured, or persist the A/B.
3. **The trim leaves 28 hero materials with no map at all in tier 0, unstated. FIX NOW (report line).** For all 28 trimmed keys
   both `lowres.files[k].path` and `.full` are tier 1: the v5 bullet "`path` is the half-resolution file the group or the
   material already has" is false for them, "0 hero-visible assets not in tier 0" reads as full tier-0 coverage, and tier 1
   fetches half AND full of the same key (1.52 MB wasted). Fix: drop the lo copy when its key is trimmed, plus one line telling
   the viewer those keys are untextured until tier 1.
4. **Carry.** (a) tiers.py:686-706 duplicates the completeness block at 517-543 verbatim — delete the second copy; (b) mobile
   `lowres.files` has no `full` on any of its 52 keys (deliberate, permanent redirect) — say so in the contract; (c)
   gate5_instance_rows.py:23 says an unmatched row fails the run, the code warns and sets `complete: false` (right behaviour,
   wrong docstring); (d) desktop tier 0 still ships `../gate1/arch.glb` and `ground.glb` with 15 / 4 bufferView images — not
   groups, so verify_glb.py:584 skips them and those maps can never be tier-upgraded; (e) r1 carries (c), (d) and (e) stay open.
