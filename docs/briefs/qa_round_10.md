# QA round 10 — hero only, on the fixed vaults (brief from the lead, 2026-09-10). Model: Opus 5 xhigh. Read docs/briefs/qa.md (item 2b is new) and CLAUDE.md "Gate checks added 2026-09-10".

Why: the user found the v1 hero's main arch filled by chord triangles of the vault rib plate (docs/status.md "USER DEFECT"); architecture r8 fixed all
8 bays; lighting r17 re-lit the arch soffits and the cam03 colonnade. Round 10 scores the HERO ONLY (cam01), plus a defect pass on cam02 and cam03.
Renders: Cycles hero 1920x1080 128 spp (max 1500) into renders/final/v2/qa_round10_cam01_cycles.png; Eevee cam01/02/03 (max 600). No 4K, no cam04-06.
Required, in this order:
1. `scripts/qa_name_sweep.py` on master.blend (exit code + hits; exceptions on record in quality_checklist.md).
2. The ray-cast opening test from cam01 (bay 00) and cam02 (bay 07) along the bay axis at z 16-22 (scripts/arch_vault_facecheck.py has the
   pattern; stations from qa_cameras by name): first hit = far side or soffit at its radius, else blocker.
3. Six 100 % tiles of the Cycles hero (`scripts/qa_hero_tiles.py`), viewed one by one with the Read tool BEFORE any score: list every visible
   geometry or material defect per tile (filled openings, flat surfaces, missing ornament, plain cylinders, z-fighting, seams, leaf cards, birds),
   each with the tile id and a pixel box, regardless of the metrics. Then four tiles each of the Eevee cam02 and cam03.
4. Score the hero on the rubric (r09 basis: 3.67) with the r07-r09 boxes (re-based boxes from round 08); state the delta and whether the arch
   now reads as the photo's (coffered barrel, far arch, sky through it: crop pair vs ref 169 at 1:1 in the composite).
5. Composite renders/final/v2/round10_gate.png: hero vs ref 169 top, the arch 1:1 pair, the tile defect list, the score deltas.
   Verdict line: PASS / FAIL for the tile review (a FAIL names the blocking tile defect and its owner); the lead renders the 4K v2 only on PASS.
Commit only docs/qa_round_10.md, docs/quality_checklist.md, scripts/qa_*.py, renders/final/v2/round10_*, renders/final/v2/qa_round10_*.
Touch renders/final/v2/round10_RENDERS_DONE when every render has exited. Report under 40 lines.
