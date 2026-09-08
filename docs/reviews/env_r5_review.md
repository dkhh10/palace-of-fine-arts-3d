# Code review: branch environment (round 5, 9c4b940) — MERGE WITH FIXES

1. HIGH — `x1_exit` moved three HAND-PLACED trees out of frame, contrary to environment_notes ("changes no position",
   "nothing hand-placed moved"): planting table #11 broadleaf (26,32)->(67,22), #12 willow (18,40)->(65,28), #26 broadleaf
   (33,26)->(66,18), 36-48 m relocations of trees pinned to user-image positions (cam01 x 0.21-0.26; user image x~410);
   env_r5_build5.log:113 shows relief moves 3 (r4) -> 5. This is nearly the outcome the notes say was rejected.
   Fix: `scripts/env_trees.py:722-726` apply `x1_exit` only to procedural screen trees (or set x1_exit = x1 for the P/C
   hand-placed group); re-measure the QA-03-10 band on the master hero afterwards; correct the notes.
2. MEDIUM — `scripts/env_sightlines.py:299` `--before` move-back table still lists r4 destinations ((31.6,25.8),(33.0,25.9),...)
   that no longer exist, so `--coverage --before` silently puts 0 objects back. Fix: update the pairs or drop the flag.
3. LOW — `scripts/env_sightlines.py:190` rebinds `loc` (camera-origin Vector) to a string in the --who block. Rename.

Verified correct: shift_y math (0.06 * 16/9 = 0.1067, right sign in all three places), city_az pure rename (6 call sites),
clear() corners cost 2 road segments and no blocks, build_all's only caller updated, env_r5_hero.py never saves, idempotent
and deterministic (builds 4 and 5 bit-identical counts), zero library warnings, no out-of-ownership files.
