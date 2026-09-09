MERGE WITH FIXES

Delta review of `phase5` c4a73cb..82bb218 (phase5_cleanup.py, deliver.sh step 1b, `--blend` on hero/flythrough,
flythrough_plan.md, tech_notes/checklist/.gitignore). Read-only, no Blender run. Both r1 blockers are fixed: `|| true`
on all three greps (verified in zsh under `set -e -o pipefail` — the fallbacks are reachable, `packflag=()` does not
abort, `read <<<` splits) and the 2560-upscale path is now the user's stated checklist rule, not an invented one.

Verified good: purge is `orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)` — identical to
`common.purge_orphans`, looped to a fixed point, try/wrapped, linked ids reported not touched. LOD uses
`common.set_lod(viewport=1, render=RENDER_LOD)`, the same call as build_master.py:251; the guarded fallback fires only
if linked objects exist and matches common.py:175. No `bpy.ops.file.pack_all` (it could not write library images
anyway): per-image `img.pack()` skipping `img.library`, and the 1.5 GB guard is computed **before** any pack. Step 1b
uses `cp`, not save-as; the copy sits beside master.blend so `//assets/…` resolves unchanged and `relative_remap=True`
is a no-op there. Master-write refusal rail, camera hashes, `BLEND=${PFA_DELIVERY_BLEND:-$SOURCE_BLEND}` (a lone
`phase5_deliver.sh 4` uses master.blend; step1b's non-local `BLEND=` repoints steps 2-6 in an `all` run), spaced path
quoted, `blender_run.sh` everywhere, no absolute paths, nothing writes master.blend. Plan findings spot-checked
against source + `light_r14_check_final.log`: 1 (frame 85 = 0.50 m/s, `ds=0.20`, `ACCEL=2.5`), 3 (397 = 6.35 water /
409 = 5.60 shore), 2 (`link_site()` links ARCH+ENV only) — all hold, with frames.

1. **fix now** phase5_hero.py:51-54,66 — r1 fix 3 is half applied. `common.setup_scene(scene)` at :54 runs *after*
   `apply_final_cycles` and re-sets `color_depth = "8"` (common.py:78), so :66's "depth stays 16-bit" comment is false
   and the 4K hero still ships 8-bit AgX (sky banding). Move `setup_scene` above :51, or set `"16"` at :66.
2. **carry (r1 #4)** deliver.sh — step 5's `final_hero_vs_ref169.png` + measure numbers and step 6's
   `light_flythrough_check.py` at LOD0 (plan finding 2 wants ORN linked too) are still neither run nor listed.
3. **carry (r1 #5)** step 3 renders with `apply_preview_eevee`, not the `apply_viewport_eevee` state step 1b saved;
   step 2 asserts nothing. One `--python-expr` check of engine / light_threshold / LOD1 would close it.
4. **nit** phase5_cleanup.py:357 exits non-zero only on reopen/cameras — `viewport_preset` and `size_under_1_5gb`
   fail silently; `bytes_to_pack` dedupes by realpath while Blender packs per datablock (harmless at 116 MB).
