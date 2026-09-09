# ORN round 8 review (branch `ornament`, head 2410e95) — code review, Opus 5, no Blender

**MERGE WITH FIXES** — the round does what the brief asked and the numbers hold up. I re-ran
`orn_r7_capital_layout.py --verify` offline (pure Python, no Blender): it reproduces the notes' r8 table to the
printed digit for all three variants (v1 0.300/0.300 H, r_tip 1.358/1.397 R; v2 spiral 0.633-0.891 H; v3 r_tip
1.329/1.389 R), prints ARCH_R6 read from the builder, and exits 0. The hand copies are genuinely gone,
`apply_capital_style` is a faithful lift of the old inline block (mesh unchanged by the refactor), the back-row
count is arithmetically 5 at ±12/-25 % margin with byte-identical positions, and `bake_pending` now exits 1.
Ownership clean (only `orn_*`/`ornament` paths, no `build_master.py`, no camera stations, no absolute paths);
one tracked binary > 5 MB (`ornament.blend`, one commit, 85.63 → 85.62 MB); the two crop JPEGs are 0.25 MB each.

1. **BLOCKER for the merge (not for the code) — merging this blend throws away the lead's bake of a panel this
   round never touched.** The branch never ran `git merge main` (merge-base 76a1fae; the brief's first line), so
   its `assets/ornament.blend` descends from the pre-bake blob. Main has since gained 037dc59, which baked
   `ORN_attic_panel_v1-3_LOD1` normals **and** `ORN_capital_rotunda_v1-3_LOD1` normals + AO. Taking the branch's
   blob loses both sets — and attic_panel was deliberately *not* rebuilt this round, so its bake is still valid.
   Fix at merge: keep **main's** `ornament.blend`, then re-run `orn_build.py --only capital_rotunda` **with** bake
   (deterministic seeds, ~16 s + bake) so only the re-laid asset is redone; gate on `--bake-pending` (exit 1 now).
   Do not resolve the binary conflict in the branch's favour.
2. **FIX NOW — the notes' open-issue bullet is stale against main.** `docs/ornament_notes.md` "PENDING BAKE
   (rounds 7 and 8)" still lists `attic_panel` as pending; on main it is baked. Same for the r7-review carry
   language. Reword to "capital_rotunda only" when merging, or the next round re-bakes 8 panels for nothing.
3. **CARRY — two incompatible pixel scales now live in the same file.** `orn_r7_capital_layout.py:36-45` still
   carries the r7 reference block (H = 400 px, 133 px/m) and `REF` still derives `volute_zone_bottom=0.650` and
   the raw tier fractions from it, while section 3 of this round establishes H = 358 px / 119.3 px/m on the
   committed crop — a 12 % difference. Only the volute band was reconciled (0.774 vs preset 0.762 H); the
   docstring's "lower acanthus 0.213 H raw" is 0.237 H on the new scale, as `orn_r8_ref002_crop.py` itself
   prints. The gate passes either way (0.650 is the conservative side), but the window the report calls "the
   ref_002 window" rests on the reading this round superseded. Fix: restate `REF`'s pixel-derived entries on the
   358-px scale, or say in the docstring which numbers are canon and which are pixels.
4. **CARRY — `source_ns()` is a brace counter, not a parser.** `_bracket_slice` (`:60-72`) counts `[{(`/`]})`
   without skipping strings or comments, and `_def_slice` (`:75-84`) stops at the first line starting in column 0.
   Correct on today's `orn_build.py` (I checked every comment inside the four blocks — all balanced), but an
   unbalanced bracket in a comment, or a docstring line at column 0, silently truncates and `exec` raises or, worse,
   exec's a partial dict. Fix if it ever bites: `ast.parse` the module and slice by node line numbers (~6 lines).
5. **CARRY — `--verify` still checks only the rotunda.** `verify()` `continue`s past the tier-extent, r_tip,
   abacus and volute-margin gates for `capital_inner` / `capital_colonnade` (only the volute top prints as
   "carried"). Their v3 meshes on disk are also still the r7 `CAPITAL_STYLE[3]`. Both are named in the notes'
   open issues; they close together at the one GPU-window rebuild of those two.
6. **CARRY — the attic_panel change is unexecuted, and two r7 carries are untouched.** `BACK_HALF_SPAN` and the
   new print line have never run (panel deliberately not rebuilt); I verified `2*int(4.00/1.780)+1 = 5` and the
   unchanged `bx` expression by hand, so "byte-identical" is sound, but it lands at the next rebuild. r7 findings
   6 (`panel_x` scales the group CENTRE, so end scan groups are clipped at ±4.74 m, not dropped) and 7
   (`rin_normalise` still never executed) are out of this round's scope and carry forward unchanged.
7. **OK.** Gate log exit 0, zero FAIL lines, worst course error 1.3-1.5 mm on the rebuilt capitals; line 145 now
   reads "LOD0 plan extent (leaf tips + volutes) 2.98-2.98 m ... abacus 3.00 m across corners", so the r7
   overstatement (finding 8) is both fixed in the label and true in the numbers. `main()` raises
   `SystemExit(bake_pending())`; nothing in `scripts/` or `lead_build.sh` calls `--bake-pending`, so the new
   non-zero exit breaks no caller. `BEFORE`/`BEFORE_26` restate `proud` in H at the same millimetres
   (0.140 R × 1.05 = 0.147 m = 0.049 × 3.0), so the historical column is unmoved by dropping `proud_unit`.
