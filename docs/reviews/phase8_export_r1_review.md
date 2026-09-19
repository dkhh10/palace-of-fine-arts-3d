# MERGE WITH FIXES — branch `phase8-export` @ ee28efe (merge base 0ac089a), Opus 5, read-only, 2026-09-19

Numbers re-run, not read: first frame recomputed from `files[]`, `tiers_test` re-run, `placed_tris` traced. No edits.

## Findings
1. **fix now** — `export/tiers.py:533-540`. The stand-in row now carries the 2 K key with `px=None`, so the
   resident-estimate fallback (`tiers.py:746-750`) resolves that key in `textures.gate3.files` and reads **2048**
   for a file that is the half-resolution copy of the 1 K atlas: `impostor_lo` 44.8 → **111.8 MB**, reported
   `resident_estimate_mb.total` 1 249 MB instead of ~1 182. It errs high (no budget breaks) but the 6a "GPU memory
   reported" figure is wrong. One line, in the `put`: `px=lr_px.get(k) or (man["textures"]["gate3"]["files"].get(k) or {}).get("w")`.
2. **carry** — same block: the 1 K albedo key lost its `tiers.lowres.files` entry and the 1 K file is tier 1, so the
   `?imp2k=0` path has no tier-0 stand-in. Re-adding the row breaks the 1:1 pairing — say it in the `variant_2k` note.
3. **carry** — `export/p8_texel_probe.py:181`: `--root` defaults to a hard-coded MAIN path (use
   `os.environ.get("PFA_MAIN_ROOT", ...)`); `CAM03` at :22 is a hand copy of `scripts/qa_cameras.py:35` — identical
   today, but it will drift. `export/p8a_shrub_check.py` prints `FAIL` and exits 0, so it cannot stop a chain:
   add `sys.exit(0 if ok else 1)`.
4. **carry** — `docs/briefs/phase8c_export_analysis.md` (b)4: the KTX2 claim (mean |Δ| 0.35/255, RMSE 0.78,
   Laplacian 19.64 → 19.80) has **no committed script**, only the crop jpg; every other number there comes from
   `p8_texel_probe.py`. Commit the compare or mark it as read off the crop. Also `export/manifest_v4.py:310-321`:
   a class in Gate 2's `per_class` but missing from the Gate 1 one keeps its stale block silently — one `print`.

## Verified (no finding)
- **No double count.** `imp_keys` (`tiers.py:928-932`) holds only the 1 K slots, so no key reaches the stand-in loop
  twice; the path is emitted once and `files[]` is deduped by path. Desktop: 48 `impostor` rows at tier 1, 32
  `impostor_lo` at tier 0; mobile untouched; tier 0 **byte-identical to MAIN** on both variants. A prototype with no
  2 K variant keeps its 1 K row via `key_2k.get(k, k)`; all 16 albedo keys are unique, so `key_2k` cannot collapse two.
- **First frame recomputed from `files[]`**: desktop 48,242,067 + boot 1,106,348 + headers 36,450 = **49,384,865**;
  mobile 46,488,901 + 1,096,864 + 39,042 = **47,624,807** — both match MAIN's `export/out/gate5` manifests exactly.
- **The `per_class` refresh cannot mask a triangle change**: the new source is the Gate 1 manifest, whose
  `placed_tris` is Blender's own `export_set.json` count (`gltf_gate1.py:458`), while `verify_glb --gate5` counts
  accessors in the packed glbs — two independent measurements, every move logged in `per_class_refreshed_from_gate1`.
  `gate2_common.py:31` resolves `GATE1_OUT` to the worktree, so manifest_v4-before-sync reads the fresh file;
  `verify_gate5_{desktop,mobile}.json` `fail: []`, env ratio 1.0.
- **Shrub check matches the ENV builder**: keys on `ob.data.name` as `gate1_set.py:644-653`, and `EXPECT` 31,268 /
  6,948 equals `renders/logs/p8a_stats_lod2.log:30` ("25 sources" vs 28 datablocks — explained in the script).
  **No re-bake**: `out/gate2` untouched, Gate 3 changes are the `instance_rows*/instance_order*/manifest` json
  hand-offs only; `sync_main.sh` unchanged, **no `--delete`** on any gate.
- ENV 894,974 / 902,000 (7,026 spare), near 20 / far 127, tree lists unchanged (`p8a_gate1_set.log`); `budget_doc`
  imports `CLASS_BUDGET`, `phase6_budget.md` regenerated consistently; `node web/test/tiers_test.mjs` re-run here:
  **all pass, 214 pairs both directions**.
