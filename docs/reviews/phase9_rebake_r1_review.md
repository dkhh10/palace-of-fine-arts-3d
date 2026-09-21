# phase9-rebake r1 review — **MERGE WITH FIXES** (9 findings; reviewer: Opus 5, CPU only, no Blender/Chrome)

Verified on disk, not from the report: both probe JSONs reproduce the report's tables digit-for-digit; the probe's claimed
identity control re-run here gives MAE/p50/p99 **exactly 0.000** on a map against itself; `bake_p8_backup` holds **109**
records (Sep 15/16/17/19 mtimes, clone-preserved) and `bake/` holds 109 = **87 dated 2026-09-21** + 22; all 87 carry one rig
(`WORLD_golden_hour`, `diffuse_world false`, `lights 20`) and `bake_queue/status.json` shows 87 jobs **rc 0**;
`instance_irradiance.json` = 166 placements, generator `trees_far_compose.py` alone, **no `rows_source`**, `tfirr_00..03`
`override_scope.objects = 166`; exposure gap is 3.3379e-6 EV and `scripts/p8_cycles_refs.py:37` does assert 1e-3; `npm test`
rc 0 / **771 PASS** reproduced in MAIN; no binary over 175 KB; no `assets/*.blend`, `master*`, or `scripts/` file touched.

1. **`export/p9_geom_pin.py:82-85` — 2 of the "30/30" checks are tautologies. (fix now)** The shipped manifest has no
   `gate3.uv2_meshes_total` and no `orn_slots.pools` (checked: `gate3` keys are generated/jobs/records; `orn_slots` keys are
   orn/arch_inst), so both `eq()` calls take the `else` branch and compare the NEW export set with itself — "uv2 meshes 66 vs
   66", "slots 2 vs 2" can never fail. Real score is 28/30. Fix: raise on the missing key instead of falling back.
2. **The probe's floor is the wrong class for a bake-to-bake delta. (carry)** `export/p9_probe_cmp.py:10-12` takes B.2's
   **KTX2-transcode** error (p50 0.015-0.097) as the floor, but the comparison is EXR vs EXR — two Cycles runs, so Monte-Carlo
   + OIDN variation is not in that floor and no second seed was baked. For the own map (p50 1.018, blue 0.414x) the margin is
   overwhelming and the verdict is safe; the slot's "1.8x above the floor top" is thin on a floor that does not measure
   re-bake noise. What actually carries the slot case is the channel-correlated blue (0.622x all, 0.596x lit). Re-label, or
   bake one duplicate slot job next round for a true floor. **FULL CHAIN verdict stands.**
3. **`trees_far/ratio_check.json` PASSes against an OLD-world reference. (fix now, CPU-cheap)** Its target comes from
   `impostor_diag_ref.json` -> `renders/previews/qa/round13_02_lagoon_ne_threequarter_cycles.png` (2026-09-17, pre-r19) — the
   exact defect the report retires `p8d_irr_restore.py` for ("measured against references rendered in the OLD world"), cited
   here as this round's far-tree evidence. Re-point it at `renders/qa_comparisons/cycles_p9/cam02_1080_32spp.png` and re-run.
4. **QA-23 (far-tree crowns +4-16 % too bright) is not measured this round. (carry -> QA gate)** `luminance_scale 1.4877` is
   the impostor modulation's effect on **one** placement's crown (TREEFAR_000, ratio 1.70/1.58/0.50) and it is **applied** at
   runtime (`ratio.strength 1.0`, clamp 4.0, shipped) — it says the crowns get 49 % brighter there, not that the 166 are
   consistent; population mean lum moved 2.0127 -> 2.6885 (+33.6 %). QA must re-score the crown boxes against the p9 refs.
5. **The manifest-order fix is not in the README. (fix now)** `export/README.md:822-830` lists `manifest_v4.py` with no
   `gate3_relay_check`; `:1410-1414` lists `gate3_relay_check` with no `manifest_v4`. The constraint the report discovered
   (relay_check writes COLOR_0 range, v4 must read it after) exists only in the report. One line in each block.
6. **Stale `lmg1_*` are in the shipped manifest's texture set. (carry)** Records and source EXRs are 2026-09-16 (pre-r19), yet
   `gate3_encode`/`gate3_pack` re-encoded their 4 KTX2 on 09-21 and they sit in `textures.gate3.files` (4 of 126). They are in
   **no** tier group (`groups.json`/`groups_mobile.json`: 0 hits) and `web/test/gate3_test.mjs:134` forbids any asset taking
   the lmg1 twin, so nothing ships them — drop them from the texture set or stamp them "diagnostic, old world". The 16 `tfao_*`
   (Sep-17) bake in `GATE3_ao_white` with `lights 0` (verified on the record) and are world-independent: legitimately skipped.
   **No `lm_` / `slot_` / `lmatlas` / `probe` / `vc_` / `imp_` / `tfirr_` record older than 2026-09-21 is in the texture set.**
7. **Report wording: "every one of the 87 records reads rc 0". (carry)** The per-job record JSONs carry **no** `rc` field; the
   rc lives in `export/out/bake_queue/status.json` (87 / 87 rc 0, confirmed). Cite that file.
8. **`sync_main.sh` skip is correct and misses nothing. (carry)** With `ROOT == MAIN` every rsync is a directory onto itself
   and `export/sync_main.sh:60` `cp -f` a file onto itself → `set -e` → rc 1; gate3/gate5 manifests, groups and both
   `verify_gate5_*.json` are present in MAIN because the chain wrote there. Add `[ "$ROOT" = "$MAIN" ] && exit 0` at line 7.
9. **Merge hygiene. (fix now, lead)** MAIN's working tree already holds a byte-identical **uncommitted** copy of
   `export/manifest_v2.py`; `git checkout -- export/manifest_v2.py` in MAIN before merging. The 1e-3 EV bound itself is fine:
   0.069 % linear, 250x below the smallest exposure change ever shipped (0.25 EV), and it matches `p8_cycles_refs.py`.
