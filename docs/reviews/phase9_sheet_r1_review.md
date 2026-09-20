# MERGE WITH FIXES — phase9-sheet @ c05f775 (scripts/phase9_sheet.py, 1 file, +300)

Verified clean: `scripts/phase8_sheet.py` untouched, nothing else on the branch; MAIN_CHECKOUT/REPO_ROOT split kept
(:32-42, inputs from main, outputs under the worktree); every phase5/phase8/gate7 label re-pointed correctly (BEFORE =
gate12 + `renders/final/phase8/…`, AFTER = AFTER_GATE + `renders/final/hero_…`, labels "Phase 8 (final)" / "Phase 9");
`--check` exits 0, opens no image, writes nothing (ran it, `git status` clean); `--after-gate` is parsed at module scope
under `__main__`, so it rebinds the global before any builder reads it — no missing `global`, override confirmed working;
stand-in logic correct (`renders/final/hero_cam01_3840x2160_128spp.png` is byte-identical to the phase8 copy today, so the
warning fires as intended).

1. `.gitignore:112` / `scripts/phase9_sheet.py:19` — **fix now.** The gitignore has `renders/qa_comparisons/phase8_tiles/`
   but no phase9 entry, so the docstring's "tiles (gitignored, full resolution)" is false and 12 full-res PNGs would be
   staged. Fix: add `renders/qa_comparisons/phase9_tiles/` to .gitignore before the first non-`--check` run.
2. `scripts/phase9_sheet.py:290-293` — **fix now.** `--after-gate` as the last argv element raises
   `IndexError: list index out of range`. Fix: `if i + 1 >= len(sys.argv): sys.exit("--after-gate needs a value")`.
3. `scripts/phase9_sheet.py:167-192` — **fix now (small).** The Cycles row has a missing-file stand-in but the viewer row
   does not: with gate13 not yet captured (the state today, per `--check`), `_mtime(viewer_after)` dies on a raw
   `FileNotFoundError` traceback. Fix: guard both viewer paths and `sys.exit("run --check: <path> missing")`.
4. `scripts/phase9_sheet.py:58-68` — **carry.** `BOXES_960` are the Phase 8 crop subjects (colonnade backdrop, shore shrub
   band, far crown) with a comment citing the Phase 8 report. Re-pick them against the Phase 9 defect list before the gate,
   or the tile review shows last phase's subjects.
5. `scripts/phase9_sheet.py:51` — **carry.** `renders/final/phase8/hero_…png` (33 MB) is untracked and not ignored; it is
   the only BEFORE copy once the Phase 9 render overwrites `renders/final/hero_…png`. Too big to track — note it in
   docs/status.md as a must-not-delete local baseline.
