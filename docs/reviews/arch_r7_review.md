# arch r7 review (head 9d6f8ee) — MERGE WITH FIXES

Item 1 (the only thing that touches the .blend) is clean and verified; the two analysis items overstate what their
scripts actually establish. Fixes below are edits to docs/arch_notes.md + the report, not to the build.

Verified independently (no Blender): `add_socket(frame=)` has exactly ONE call site (arch_build.py:416) and is a
no-op when `frame is None`, so no existing socket's frame moves; the props log goes 434 -> 442 with all 13 previous
types' counts and example props byte-identical to arch_r6b_sockets_props.log; tris_LOD0/1/2 and tris_placeholders in
arch_stats.json are unchanged (objects 2281 -> 2289 = the 8 empties), so "no geometry change" holds.
`Matrix((X,Y,X.cross(Y))).transposed().to_euler()` builds the right-handed basis the doc describes; with n = the face
normal, `X = up x n` in arch_build:373 equals `Zloc`, so the socket really sits at the a=0 springing and
`P(phi)=C+R(cos phi*+Z + sin phi*+X)` matches the sweep. R_in = ARCH_SPAN/2 + 0.30 = 6.550, pi*R = 20.577,
band 0.22, crown_gap 3.494 deg all recompute. Only architecture-owned files + docs/sockets.md (allowed); no new
binary > 5 MB (the crop is 396 KB); reference paths are the sanctioned main-checkout absolutes with a
worktree-relative try first. 5.2 API use (`closest_point_on_mesh`, `evaluated_get`) is correct.

1. **arch_r7_cornice.py:187 — the modillion count N is not measured, it is assumed, via a magic constant.**
   `RUN_M / (pL / 33.8)` divides by the answer (33.8 ~ the 33.7 px/m it is about to derive), so "the left face's run
   holds 11.0 periods, i.e. N = 11" is circular; `run_px` (line 186) is computed and never used, and the window is
   330 px against the ~371 px an 11-period run would need. **fix now (wording):** say N = 11 is assumed. The
   qualitative verdict survives (at N = 12 the crown-to-modillion span is still 1.62 m against CORNICE_H 1.37), but
   the precision does not.
2. **arch_notes r7 item 2, "every conclusion below survives either" — not quite.** At N = 12 the modillion pitch
   reads 0.951 vs the model's 1.060 = **-10.3 %**, outside the brief's 10 % band, so "modillions 1.06 m pitch:
   CONFIRMED" is contingent on N = 11. *carry:* qualify it.
3. **arch_notes r7 item 3, "the fitted station is in the lagoon / ref 062 cannot be reproduced from a standable
   point" — contradicted by the script's own two tables.** I reproduced `land_check` (the inline
   `(Y, -X)` inverse of `common.osm_to_world` is correct, and az 37 is indeed water to D 100, land from 105). But
   the same script says az is unidentifiable, and its az scan gives az 17 chi2 **7.80** vs az 37's 7.69 at D 83.4 —
   which `land_check` classifies as **LAND** (az 15/17 are land over D 75-90). **fix now:** either restrict the
   claim to "on the face normal the station is in the water" or fit D on the land set over the whole az scan.
4. **arch_r7_cornice.py:61,126-129 — `slope_of()` is defined and never called.** The de-slant slopes (0.063,
   -0.1304) are hand-entered, but line 124 says "slope from slope_of" and the module docstring (line 26) says the
   slope is found by cross-correlation. *fix now:* call it, or say the slopes are hand-read. The band row bounds
   (838-846 etc.) are likewise hand-entered from `edges()`, which is fine but is not what "measured" implies.
5. **arch_notes r7 item 2 sign.** The notes write the projection correction as `s*(dz - tan(elev)*dd)`; the code
   (line 208) uses `(z + d*tanE)` differences, i.e. `dz + tanE*dd`. The code's sign is the right one (a feature that
   projects toward a camera looking up is magnified, closing the gap: 0.25 -> 0.226). *carry:* fix the note.
6. **ORN wording mismatch.** docs/ornament_notes.md:876 asks for "+Y = the radial face normal"; ARCH delivers
   +Y = the wall's outward normal and +Z = radial (correct under the global contract, and clearly documented). *carry:*
   have the lead confirm with ORN that the band width runs along socket-local **+Z**, before ORN builds the panel.
7. **arch_socket_check.py:110 — the arc test is weak radially.** The crown face is a 0.22 m planar strip, so a sample
   up to ~9 mm off in radius (the 28-segment sweep's chord sag at the 15 deg samples) still returns 0.00 mm. The check
   never compares `arc_radius` to the crown face's inner edge on the mesh. *carry:* also assert
   `min over crown-face verts of (radius from arc_center) == arc_radius` to 5 mm.
8. **Duplicated shared constants.** `land_check` re-implements `common.osm_to_world`'s inverse inline;
   `MODEL`/`MODEL_PITCH` (arch_r7_cornice.py:131-134) copy arch_build's `CORNICE` dict (they match today: 1.06 /
   0.47). *carry:* import them so the comparison cannot go stale.
9. **arch_notes option C** says "the archivolt socket ... moves". It does not: the archivolt springs at
   `ARCH_SPRING_Z` 17.5, below `ENTABLATURE_Z0`. *carry:* drop it from the C row.
