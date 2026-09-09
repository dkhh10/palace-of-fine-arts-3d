MERGE WITH FIXES

Reviewed `phase5` @ c9afc7f (`git diff main...HEAD`): scripts/phase5_deliver.sh, scripts/phase5_hero.py,
scripts/phase5_flythrough.py, docs/tech_notes.md. Read-only, no Blender run.

Verified good (no action): `light_presets.apply_final_cycles(scene, samples=, time_limit=)` and
`apply_preview_eevee(scene, samples=)` exist with those signatures (light_presets.py:195, :301);
`light_flythrough.load_schedule()` (:385) really returns `frames`/`fps`; `qa_cameras.ensure(scene)` (:50);
`common.script_args/ROOT/RENDERS/setup_scene`. Engine ids `CYCLES`/`BLENDER_EEVEE`, `denoiser='OPENIMAGEDENOISE'`,
`cycles.use_adaptive_sampling`, `cycles.time_limit` all 5.2-correct. Step 4 does set 128 spp with adaptive OFF
(hero:49 overrides the preset's `True`) and `time_limit 0`; 4K runs use max 7200 s; every Blender goes through
`blender_run.sh` with `--background` (the wrapper refuses otherwise); `cd "$(dirname "$0")/.."` quotes the spaced
path; ffmpeg `-pattern_type glob` copes with the non-contiguous frame_0001/0003 numbering and `24/2 = 12` fps is
the right output rate. `phase5_hero` inherits render LOD0 from master.blend (build_master.py:17 default).

1. **blocker** phase5_deliver.sh:49 (and :105-106) — `t128=$(grep -o ... | tail -1 | cut ...)` under `set -e -o pipefail`:
   a no-match grep aborts the function/subshell, so the "no wall_time_s found" fallback at :51 and the `${fps:-24}`
   fallback at :107 are unreachable. Verified in zsh (assignment exits rc=1). Worse: `pick_step5_settings` then
   prints nothing, `read` leaves `spp` empty, and step 5 launches `phase5_hero.py --spp ""` -> `int('')` ValueError.
   Fix: `t128=$(grep -o 'wall_time_s=[0-9.]*' "$log" | tail -1 | cut -d= -f2 || true)`, same for fps/frame_step.
2. **blocker** phase5_deliver.sh:43-60,88-93 — the slow branch renders 2560x1440 and `sips`-upscales it into the
   deliverable `renders/final/hero_cam01_3840x2160.png`. The quoted justification ("checklist: render at 2560 wide
   and upscale") is not in docs/phase5_checklist.md or any doc (grepped); the checklist says only "choose the final
   sample count from that time (target: the final frame under 90 min)". Delivering an upscale as the 4K hero fails
   step 5. Fix: keep 3840x2160 always and scale spp to the budget, e.g. `spp = 128 * clamp(floor(5400/t128), 1, 6)`
   snapped to 128/256/384/512/768.
3. **fix now** phase5_hero.py:64 — `color_depth = "8"` (and `common.setup_scene` at :51, which also resets it) undoes
   `apply_final_cycles`'s deliberate 16-bit + compression 90 (light_presets.py r13 carry 11), contradicting the
   file's own "SAME final preset" docstring. 8-bit AgX at 4K will band in the sky gradient. Fix: drop the override,
   or set `"16"` after `setup_scene` and say so in the docstring.
4. **fix now** phase5_deliver.sh — checklist step 5's side-by-side (`renders/qa_comparisons/final_hero_vs_ref169.png`)
   and the `light_r12_measure`/`qa_measure` numbers, and step 6's `light_flythrough_check.py` at LOD0, are not run by
   the driver and not mentioned as manual. Fix: add them to step5/step6 (or list them explicitly as lead-run steps).
5. **carry** phase5_deliver.sh:30 — step 3 runs `qa_render_round.py --eevee`, which applies `apply_preview_eevee`
   (raytracing ON, `set_lod(render=1)`), not the saved `apply_viewport_eevee` state the checklist names; nothing
   asserts the saved viewport state opens as claimed. Fix: assert the saved state in step 2's `--python-expr`.
6. **carry** phase5_hero.py — add an explicit `common.set_lod(viewport=1, render=0)`; today LOD0 is only implicit via
   build_master's default, so a `--render-lod 1` master would silently ship a LOD1 hero.
7. **carry** phase5_deliver.sh:22 — step 2 logs no timing line of its own; `$SECONDS` around `blender_run.sh` includes
   wrapper + Blender startup, so the "< 60 s" number is pessimistic. Fine for the gate, worth a note in the log line.
