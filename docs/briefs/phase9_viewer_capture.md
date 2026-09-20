# Phase 9 viewer captures — one Chrome window, three capture sets (brief from the lead, 2026-09-20). Opus 5 high. Fresh agent.
Branch `phase9-viewer-capture` from main (b60699c or later), worktree .claude/worktrees/phase9-viewer-capture; `npm install` in web/ if needed. Read
docs/briefs/process.md, then web/README.md sections "Phase 9" (item 1 the dotted-rim quantiser and its owed capture; the specular gate `?specgate`),
docs/briefs/phase9_bake_analysis_report.md B.5 (the four cam03 flag frames), docs/briefs/phase9_viewer_shade.md "Captures", docs/reviews/phase9_viewer_r2_review.md
and phase9_viewer_shade_r1_review.md (carries that name a measure). The GPU is FREE and granted to you for this window: no Blender may start while you run;
every Chrome run through `scripts/chrome_run.sh <honest seconds> -- node web/tools/screenshot.mjs ...` from MAIN or the worktree as stated; check
`pgrep -fl "MacOS/Blender|headless"` is empty before each run and STOP if a Blender appears (the lead's re-bake chain would own the GPU; report what you have).
Assets: MAIN's export/out is the Phase 8 bake (deploy 12). For frames that need the sky/sun constants in the manifest, mirror MAIN's export/out into the worktree
by symlink and run `python3 export/manifest_v4.py` + `export/tiers.py --no-pack` (+ `--mobile --no-pack`) there with PFA_MAIN_ROOT=<worktree>, as the shade
engineer did (its report: nothing written into MAIN's export/out — keep it that way; `find MAIN/export/out -newer` must stay empty).
The gate5 look for every frame (deploy-12 settings): `--query manifest=/assets/gate5/manifest.json --query tiers=all --query t=0 --query billboards=0
--query treeboards=0 --query lighting=baked --query post=all --query probe=1 --query impostors=1 --query water=1`, 1920x1080, `--frames 0`.

## Set A — cam03 flag frames, the gate OFF (B.5; `--query specgate=0` on every frame so this is the Phase 8 path): station 3, one key changed per frame:
post=all (control) / post=none / probe=0 / lighting=direct -> renders/web/p9_cam03_{all,postnone,probe0,direct}.png. Then per frame
`python3 export/p9_shade_terms.py --boxes --viewer renders/web/p9_cam03_<flag>.png --cycles renders/qa_comparisons/cycles_p8/cam03_1080_32spp.png --out <scratch>/p9_cam03_<flag>.json`
(the `--viewer` flag exists on main since 07a7af3). Report whether B.3/B.4's split (env specular carries the blue, sun specular the warm remainder, post ~0 on
the near column) holds to the channel.
## Set B — the gate ON, six stations: stations 1-6 -> renders/web/p9s_cam0N.png, plus station 3 with `--query specgate=0` -> renders/web/p9s_cam03_specgate0.png.
Per station MAE vs renders/web/gate12_cam0N.png (whole frame and outside the shade boxes); station 3 near_column and p10 luma before / after / Cycles
(p9_shade_terms --boxes on p9s_cam03; Cycles ref cam03 p10 7.3, near_column (0.488, 0.290, 0.000)); confirm stations 1, 2, 4, 5, 6 move <= 0.5 % MAE outside shade.
Also read from the boot log / __pfaInfo: the modulation line (expect 166/166 on deploy-12 assets — the belt rule is not packed yet, so say what it shows today).
## Set C — the dotted rim (viewer item 1): stations 1-6 at the gate12 settings -> renders/web/p9v_cam0N.png; `python3 web/tools/p9v_rim.py ab gate12 p9v`
(rim index before / after at 2 and 5; MAE at 1, 3, 4, 6); `?tier=mobile` stations 1-6 -> renders/web/p9vm_cam0N.png, whole-frame MAE vs gate12m_cam0N.png;
`export/p8_atlas_probe.py viewer` on cam01 (viewer r2 carry 10) if it runs without Blender.
## Output: 960 px copies (renders/web/960/) committed; full-size PNGs gitignored (check .gitignore; if they are not ignored, do not add them). Write
docs/briefs/phase9_viewer_capture_report.md (< 30 lines, the three tables) and commit it with the 960 px copies on your branch. No deploy, no Blender, no edits
to web/src (if a capture reveals a defect, report it; the lead assigns the fix). Final message: the report, and the last commit id.
