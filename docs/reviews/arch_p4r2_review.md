# Code review: branch architecture (polish round 2, 37b611e) — MERGE WITH FIXES

1. HIGH — `scripts/arch_params.py:109` `VAULT_COFFER_REGISTERS` widens the barrel-vault coffer holes past their neighbours.
   Replaying `build_vault_coffers`' hole set (arch_build.py:578-601) + `offset_polygon`: tightest gap 29 mm (row octagon vs
   mid-row diamond) and 75 mm (in-row octagon vs diamond), so max safe widen ~0.012 m. The branch offsets by 0.07 (splay) and
   0.03 (room face) -> 38 and 14 overlapping hole pairs: back cap tessellated from self-overlapping loops (garbage/dropped tris
   via the bare `except ValueError`), reveal side walls interpenetrate, on the vault soffit seen from cam03/cam04.
   Fix: `VAULT_COFFER_REGISTERS = ((-0.010, 0.04), (0.012, 0.10))`, or first open the gaps (in-row diamond factor 0.8 -> 0.55 at
   arch_build.py:593; mid-row gate at arch_build.py:599 to `dr > 0.2`) and keep 0.03. Ceiling coffers are clean (no overlap
   at widen 0.10; breaks at 0.15); `COFFER_REGISTERS` is fine.
2. MEDIUM — `scripts/arch_build.py:843`: `rosette_ceiling` sockets sit at `sz - COFFER_DEPTH` = the coffer MOUTH plane, not the
   floor. COFFER_DEPTH 0.30 -> 0.55 pushed 16 of 24 sockets 0.25 m further out; ORN rosettes would hang at the rib underside.
   Fix: `- (0.10 if rr > 6 else 0.0)` or agree the offset with ornament (ornament was told "sockets moved down 0.25 m").
3. LOW — `scripts/arch_lib.py:551-552` LOD1 `shaft_rings`: top ladder `[h-0.06, h]` with the last mid ring ~1.6 m below smears
   the flute run-out (fade 0.35 m) over 1.63 m. Viewport-only. Fix: insert `height - fade - 0.05` into `top`.
4. LOW — `scripts/arch_build.py:1279/1283`: `--cams`/`--res` raise IndexError when the flag is last. Guard the index.
5. INFO — `scripts/arch_lib.py:650`: apophyge course flares outward 4 mm (R_ut - f_ut*H/2 = 1.2256 < 1.23), effectively a no-op.

Verified clean: attic_base_profile (no folds, monotonic z, radii > 0, inside plinth), flute_section (monotonic angles, watertight,
depth 0.1047 r), seams unchanged, plate(registers=()) identical for all 12 callers, sockets.md untouched, idempotent, no
out-of-ownership files.
