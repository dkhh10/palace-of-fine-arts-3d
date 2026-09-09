# Ornament round 6 — refit to the registered stack (brief from the lead, 2026-09-09). Branch `ornament`. Read docs/briefs/process.md first.
`git merge main` first (main will carry architecture r6 when you are dispatched: rotunda courses moved to register on ref 169).
Read: docs/status.md "ARCH r6 reported" (socket deltas), docs/arch_notes.md "Round 6", docs/sockets.md, your Round 5 / 5b notes, docs/qa_round_06.md
defect QA-06-6 (capitals read 24 px vs the photo's 37; bed-mould, frieze and archivolt blank at 1:1).
Socket changes from ARCH r6 (rotunda only; colonnade untouched): capital_rotunda x16 z 24.80 -> 22.96 and the capital course is now 3.0 m tall
(was 2.6); frieze_run rotunda x24 z 28.55 -> 27.00, band 0.90 -> 0.81 m (host="rotunda", subtype="rinceau", origin at run start, +X = run_dir,
+Y away from the block); attic_panel x8 z 32.55 -> 30.48, panel_height 4.50 -> 5.27; attic_figure x8 z 31.22 -> 29.20 (size_hint 6.7 unchanged).
1. Capitals (QA-06-6): ORN_capital_rotunda must fill the 3.0 m course (read the height from the socket if ARCH writes it; else from arch_params)
   with the reference's proportions (sheet: Corinthian, two acanthus tiers, volutes; ref 169 / 085 crops); at cam01 the capital reads 37 px tall.
   Report the asset height before / after and the tris per LOD within the tier budget.
2. Rinceau: refit ORN_frieze_rinceau / _return to the 0.81 m band (coverage, proud <= 90 mm, clearance >= 10 mm) and run orn_r5_stats as the gate.
3. Attic panels / figures: refit to panel_height 5.27 (scale or rebuild; keep the socket contract and the per-instance seeds); the reference's attic
   band is a deep figural relief: report the relief depth achievable inside the tier budget after the refit.
4. Bed-mould / archivolt (QA-06-6 second half): state what would fill them (asset, socket type, owner) as a proposal; no build unless a socket exists.
5. `orn_build.py -- --bake-pending`: run the pending normal/AO bakes LAST if and only if no other agent is rendering (`pgrep -fl "MacOS/Blender"`
   shows none); otherwise leave them pending and say so.
Deliverables: assets/ornament.blend, orn scripts, notes "Round 6", one composite renders/previews/ornament/orn_r6_sheet.png (asset turntable
crops, no scene render) only if the GPU is free, commits after every successful script, report < 25 lines with the tri tables and last commit id.
