# ARCH round 6 (branch `architecture`, head 2361006) — code review, Opus 5, no Blender

**MERGE WITH FIXES** — the course move is real work and reproduces from the committed scripts and logs: the row map,
every re-anchored course, the socket z deltas and the tri/silhouette numbers all recompute from `arch_params` exactly
as reported, the r5 carries 3/4/5/6/7 are closed, and the colonnade is genuinely untouched. Two hand-off gaps mean
the master *as instanced today* is worse than the report reads (capital and frieze band), and one report claim is
contradicted by its own script. All five "fix now" items are one-to-three-line changes.

1. **Capital socket does not carry the new height — fix now (visible in this round's own proof render).**
   `scripts/arch_build.py:251` still adds `SOCKET_capital_rotunda` with `size_hint = P.COL_D_TOP` and no `extra`,
   so nothing machine-readable says `CAPITAL_H` went 2.6 → 3.0. ORN's asset is fixed at `scripts/orn_build.py:58`
   (`"capital_rotunda": dict(H=2.6, ...)`), the contract forbids the socket rescaling it (docs/sockets.md), and
   `renders/logs/arch_r6_master.log` shows 16 `capital_rotunda` instanced — i.e. the r6 master has a 0.40 m void
   between the abacus and the architrave at the hero's most-read junction. Fix: `extra={"capital_height": P.CAPITAL_H}`
   and a rebuild request to ORN (also `capital_inner` if its own height ever moves).

2. **`band_height` missing on the 24 rotunda `frieze_run` sockets — fix now.** `arch_build.py:340-345` writes
   `run_length / run_dir / host / subtype` only; the 98 Greek-key runs do get it (`arch_build.py:791`), and
   `orn_r5_sockets.py:35` / `orn_r5_stats.py:172` read it. `FRIEZE_H` is now 0.81 while ORN's rinceau is
   `orn_build.py:1491 RIN_BAND_H = 0.90`. Fix: add `"band_height": P.FRIEZE_H` to that `extra` dict.
   (`attic_panel` is fine — `panel_height` is stamped at `arch_build.py:377` — but note nothing in `build_master.py`
   or `orn_*` reads it either, so ORN must be told the field grew 4.50 → 5.27.)

3. **The "ref 062 is unchanged" claim is false — fix now.** `docs/arch_notes.md` Round 6 item 1 says
   "`arch_ref062_fit.py` uses only ATTIC_Z1, DOME_APEX_Z and the podium, none of which moved". It does not:
   `scripts/arch_ref062_fit.py:44` fits `("attic base (modillions)", P.ATTIC_Z0, P.WALL_APOTHEM, 330.0, 12.0)`, and
   `ATTIC_Z0` moved 31.20 → 29.18 — a ~2 m target shift against a ±12 px tolerance. Re-run the fit and commit the log,
   or strike the sentence. Same file `:43,131,152` still hard-codes `WALL_APOTHEM + 0.74` instead of the new
   `P.ATTIC_CORNICE_D` (r5 finding 2's carry, cheap to close while there).

4. **The headline registration claim has no committed log — fix now.** "every strong edge pairs within 5 rows … attic
   storey 101 render rows vs the photo's 100 (`qa_stack_offset.py --sheet arch_r6_aligned_vs_ref169.png --x0 880
   --x1 1040`)" is the whole acceptance test for QA-06-1, and `renders/logs/arch_r6_*` contains build / courses /
   master / render / sockets only. Re-run the one command and commit its output (no Blender needed).

5. **The burnt-in table is hand-typed, and its first row keeps the label the notes reject — fix now (cheap).**
   `scripts/arch_r6_sheet.py:27-35` `TABLE` is a literal: the "before" and "ref 169" columns are transcribed, not
   measured, so the sheet cannot disagree with the report. Its first row reads "attic crown, top lit edge 168/168/169"
   while the same round's argument is that row 168 is *not* the attic crown (the crown is 161.2, `arch_r6_courses.log`).
   Relabel that row (drum edge) or drop it; ideally read the three columns from `qa_stack_offset`'s output.

6. **Inside the build, uvproj's tri-count guard is self-referential — carry.** `arch_build.py:1333` writes
   `docs/arch_stats.json`, then `:1343` execs `arch_uvproj.py`, whose tail compares the live counts to *that same
   file* → always "SAME" (`arch_r6_build.log:88-91`). As a post-step of the build it can no longer catch a tri
   regression; snapshot the previous json before writing, or move the comparison out of the build path.

7. **A uvproj failure now aborts the build after the stats are written — carry.** The new
   `arch_uvproj.py:82` `raise SystemExit(...)` (and any other) propagates out of the `exec` before
   `common.save_blend` (`arch_build.py:1347`), so `docs/arch_stats.json` would describe a build that was never saved.
   Wrap the exec, or write the stats after the save.

8. **Cornice: only the soffit is anchored; the crown is scaled — carry.** The profile does fit inside 1.37 m and stays
   monotone (dentils 1.94-2.25, modillions 2.37-2.82, eggs ~2.83-2.96, corona soffit 2.97, crown 3.22), and every
   projection is held. But the photo anchor is the corona *soffit* (row 281, hit to 0.4 row); `ENTABLATURE_Z1 = ATTIC_Z0`
   comes from the 1.37/1.75 = 0.783 scaling, leaving only 0.25 m of corona fascia + drip + cyma over a 1.66 m oversail
   (was 0.32). Two sub-items to watch at hero distance: `arch_build.py:151,464` keeps 0.13 m eggs at an unchanged
   0.47 m pitch inside a now-0.09 m nominal band, and modillions are 0.45 tall × 0.86 deep (1.9:1). The r4 "apparent
   height" arithmetic *does* reproduce when read as architrave-bottom → corona-soffit including projection
   (13.486·2.97 + 5.157·1.52 = 47.9 rows vs the photo's 47), so the prose "3.80 → 3.22 by 47/54.7" is loose but the
   two edges it rests on are independent and both land within half a row — no action beyond the note.

9. **Notes say 23 meshes; the log says 31 — carry.** `arch_r6_build.log:49` "33 objects / 31 meshes; missing: none"
   (26,376 verts, matching the report). Nothing was dropped from the object list — just fix the number in arch_notes.

10. **Socket check is mostly independent; its exit code is not — carry.** `arch_socket_check.py:33-79` reconstructs the
    ressaut centre from the sockets' own midpoints (genuinely independent) and asserts +Y outward, +Z up, host/subtype;
    `+X · run_dir > 0.99` however tests the empty's rotation against the *builder-stamped* `run_dir`, i.e. it validates
    `add_socket`'s `(out.y, -out.x)` transform — which is where the bug was, so it is the right test, but it cannot
    catch a wrong `run_dir`. The branch ends `raise SystemExit(0)` and prints "N WRONG" without a non-zero exit
    (the pre-existing path does the same), so the check can never fail a scripted run. All 126 pass today
    (`arch_r6_sockets.log`).

11. **6.4 MB tracked intermediate — carry.** `renders/qa_comparisons/arch_r6_aligned_vs_ref169.png` re-stores panel 1
    of QA's own 9.3 MB `round06_cam01_aligned_vs_ref169.png`. Keep it until QA re-measures, then drop it (the owner
    already dropped the 3.7 MB full frame in 2361006).

**Checked and clean:** idempotency (`rebuild_collection` unchanged, uvproj removes/re-adds its layer and attribute);
no absolute paths outside `common`/worktree-relative `ROOT`; no shared-constant copies leaked (`CAPITAL_H`,
`COL_SHAFT_H`, `ENTABLATURE_*`, `ATTIC_*` are read only by `arch_*` scripts — grep across `scripts/`); colonnade
courses are separate parameters (`arch_params.py:177-181 COLONNADE_*`), so cam03/cam05 fits cannot have moved;
socket z deltas all recompute (capital 22.96, frieze 27.00, panel 30.48/35.75 h 5.27, figure 29.20, urn/finial 38.30);
silhouette 87.5 / 212.0 / 544 / 0.2288 is measured from the LOD1 alpha crop, not asserted; tris +0.012 %; no files
outside ARCH ownership (`qa_comparisons` writes are the brief's deliverable), `master.blend` correctly not committed.
