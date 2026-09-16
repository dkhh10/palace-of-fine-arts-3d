# Review: phase6-bake Gate 4 per-placement instance irradiance (fcaf606..aaab677)

**Verdict: MERGE AFTER FIXES.** The pipeline is sound, idempotent, GPU-honest and never saves a .blend; the 1 379
values are real measurements. Two things must change before the export engineer consumes them: the shipped
placement **key cannot be resolved from env.glb**, and the README's claim that the opaque override leaves the
**quantity unchanged is false by the engineer's own probe data** (median +64 %, max +425 %, same vertices).

## The deviation (opaque grey override + `visible_shadow = False`), assessed

Diagnosis is right and well evidenced: a cut-out `DIFFUSE` bake returns exactly 0 at a transparent vertex
(`inst_probe` coverage 0.107 against 0.859), so the plain vertex mean of a 36-tri card is noise. Swapping the
material is the correct instinct and `use_pass_color = False` does divide the albedo out.

But the *invariance* claim is wrong, and it is checkable for free from `out/gate3/instance/inst_probe.npz`
(both variants were kept). Restricted to the vertices lit in **both** variants — same vertices, same transform —
`opaque / asis` luminance is **1.29, 0.84, 1.50, 3.15, 1.09, 3.32, 3.90, 5.25, 1.42, 1.97, 1.64 (median 1.64)**.
The cause is `visible_shadow = False` (bake_lm.py:315): it does not "keep the card from casting the shadow the
cut-out leaf does not" — a cut-out leaf *does* cast a shadow (README:1024 says the ground lightmap under a shrub
carries "that shrub's own baked cut-out shadow"). It removes the card's own self-shadow and all shadowing
between the overridden cards, while `visible_diffuse` stays on, so the opaque grey still occludes and bounces
indirect light: two uncontrolled biases pulling opposite ways, net ~+64 % brighter.

Worse, the override is applied to `obs` = **this job's objects only** (bake_lm.py:308-315), so which neighbours
shadow a card depends on the job split. Measured over the 1 379 placements: median nearest-neighbour distance
0.81 m, 98 % within 3 m, and only **28.9 %** of nearest neighbours land in the same job. 71 % of neighbours
shadowed normally (cut-out), 29 % cast no shadow at all. Re-running `--jobs 3` gives different numbers — the
"everything reproducible from scripts" contract does not hold.

The **mean over lit vertices with `cov`** is otherwise a sound per-placement reduction: excluding buried
vertices is right (that is geometry, not light), and `cov` is the honest companion. Two caveats below.

## fix-now

1. **README:976, 988-990 — the placement key is unrecoverable by the consumer.** The spec says "match each
   `EXT_mesh_gpu_instancing` row by object name, never by index", but `gltfpack -mi` drops node names
   (README:194) and the manifest's `instancing.<mesh>.objects[]` is **truncated at 16 + "… N more"**
   (manifest_v2.py:78-82) — verified: 19 of the 28 card meshes carry 17 entries against 22-101 placements.
   No name survives anywhere the consumer can read. *Failure:* the export engineer writes `_IRRADIANCE` in
   gltfpack's row order, 1 379 shrubs get another shrub's irradiance, and every value is plausible so nothing
   fails. *Fix (CPU only):* ship each placement's world translation — `loc` is already in the bake records
   (bake_lm.py:332) and is dropped at compose (gate3_instance_compose.py:78) — and state the join as
   translation-match against the instancing rows (tolerance per hand-off item 13), or state that the exporter
   must write the attribute before `gltfpack` in export-set order and verify it.
2. **README:1011 — strike "the quantity measured is unchanged"** and record the measurement above (per-vertex
   matched ratio, its spread, and the partition dependence). *Failure:* the lead accepts a +64 % foliage
   brightening as a neutral re-encoding, and the next parity miss is debugged everywhere but here.
3. **bake_lm.py:308-315 — remove the job-partition dependence.** Cheapest correct form without redesigning the
   rig: apply the override (and the shadow flag) to **all 1 379 cards** in every job while baking only that
   job's objects, so every job sees the same scene; ~43 GPU-minutes to re-bake. If the lead declines the
   re-bake, the dependence must be written into `instance_irradiance.json` and the README as a known bias.
   *Failure:* a dense reed bed's per-instance light is an artefact of where the 4-way split fell.

## should-fix

4. **gate3_instance_compose.py:78 — ship `mean` (all-vertex) beside `rgb`, and give the 7 zero placements a
   consumer contract.** The reduction deliberately discards occlusion: a half-buried card gets the same value as
   a fully exposed one, and `cov` is labelled "Diagnostic" (README:994) so no one will use it. The 7 all-zero
   entries ship `[0,0,0]` with the floor advice buried in `checks.dark`. *Failure:* seven black shrubs, and a
   buried card lit as if it were in the open.
5. **gate3_common.py:88 — `"instance"` is missing from `BAKE_DIFFUSE_WORLD_KINDS`.** Both records confirm
   `diffuse_world: false` today, matching the trees, so the production numbers are consistent. *Failure:* the
   day the lead arms `PFA_BAKE_DIFFUSE_WORLD`, the trees, slots and lightmaps move to the diffuse branch and the
   1 379 shrubs silently do not.
6. **Sanity check 2 proves nothing, and it exposes a live defect in the trees.** It compares a mean over 23 % of
   the tree's vertices with a mean over 86 % of the shrub's (`lum_ratio 0.212`, no control). More importantly the
   same cut-out zeros mean the 14 near trees ship `COLOR_0` with 77-99 % exact zeros, so README:1473-74's
   "broadleaf_s19 and pine_s29 sit in full shadow (mean 9e-6, 1.1e-3)" is very likely this artefact, not shadow.
   *Failure:* near trees render with black vertex patches next to correctly lit shrubs. Escalate to the lead.

## note

7. `gate3_instance_jobs.py:59` unlinks the bake record of every id it writes: an accidental second
   `--jobs 4` destroys the 2 597 s of records with no prompt.
8. `gate3_instance_check.py`: 678 of 1 379 rays hit something with no own lightmap and the output never says
   *what* (`by_ob` is built from `with_g` only); the ray starts 0.6 m above the card origin and can hit the card
   itself; `me = hit_ob.data` is the original mesh while `face` indexes the evaluated one (fine only while the
   ground carries no modifiers) and the returned instance matrix is ignored. Check 1's headline
   `ratio_ground_sun_over_shade = 1.1e10` is a divide-by-zero and should not be in the file; the quartile and
   Pearson forms are the usable ones and the README quotes those, correctly.
9. Cosmetic: compose docstring says coverage 0.86 (the probe) where production is 0.892; the decision estimated
   16.5 kB and the file is 210 kB (fine against the 50 MB budget, but the decision should say so); running
   variants as `["opaque", "asis"]` would bake `asis` against a leftover override for any slot-less object
   (bake_lm.py:349 restores by `zip` over an empty saved list).

## verified clean

Single-user handling copies `ob.data` in-process and nothing is saved (no `wm.save*` anywhere in bake_lm.py);
bake settings match the trees' `vertex` kind exactly (128 spp, adaptive off, OIDN, direct+indirect, `color:
false`, `VERTEX_COLORS`, same `WORLD_golden_hour`, 20 lights); queue integration is correct (jobs appended to
the gate3 list, the 65 done jobs skipped by record, `status.json` running/waiting/idle copied to MAIN, one
Blender per job through `blender_run.sh`, `MAXS 1800` against 626-664 s actual, 4 chunked jobs not one long
one); counts reconcile (1 379 / 28 against env_cards.json, no duplicate, no missing, asserted at compose);
units ("irradiance / pi, × lightmaps.scale") match the lightmap and npz convention; every array is read back
from disk before it is recorded. Nothing contradicts a decisions.md entry.
