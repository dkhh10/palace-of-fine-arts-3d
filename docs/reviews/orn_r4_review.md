# Code review: branch ornament (round 4, e90abec) — MERGE WITH FIXES

1. Bell scallop phase inverted — `scripts/orn_build.py:255-257`: `1 - sc*band*(0.55 + 0.45*cos(16θ))` puts the MINIMUM radius at
   θ = k·22.5°, exactly where the leaves sit (lower row 0°+k·45°, upper 22.5°+k·45°): trough under each leaf, ridge in the gap,
   the opposite of the stated "slot between two leaves bottoms out in a groove". Fix: `(0.55 - 0.45*math.cos(16.0*th))`.
2. Consequence of 1: upper leaf bases may detach. `build_leaf_ring` seats leaves at un-scalloped bell_radius x 0.965
   (orn_build.py:180); at the upper row the bell is 0.078 R narrower, the leaf inner edge clears by ~13 mm against a
   0.011 m voxel: marginal union. The sign fix removes this.
3. docs/sockets.md contradicts itself: contract line 9-10 still says "for the ceiling, +Y = radially outward"; the new ORN
   section (line 67+) says that is wrong for all 24. LEAD DECISION (from the reference sheet, "base ring with rosette band above
   the inner arches"): the 16 band sockets move to the VERTICAL inner face of the base ring with +Y = -radial; the 8 ring-1
   coffer-floor sockets face DOWN (+Y = -Z). Architecture is rebuilding the sockets that way (branch architecture). Ornament:
   rewrite your sockets.md section to state that final contract (short), and drop the ROT_Z_FIX workaround suggestion (it is one
   Z angle per type and cannot express both).
4. The `cavity` attribute and the AO maps are inert today: mat_build.py creates no ORN_NORMAL/ORN_AO nodes, so
   build_master.orn_material_for returns None, and nothing reads a `cavity` Attribute node. Materials round 5 gets the request
   (lead). Ornament: state in ornament_notes exactly what materials must read (attribute name, domain, 1 = open / 0 = enclosed).
5. Keystone back plate 2 cm off the mounting plane — `orn_build.py:756`: ks_cap at y = 0.15 with depth 0.34 spans y = -0.02;
   `y_mode="back"` then re-origins and shifts ks_back to y = 0.02. Fix: cap y = 0.16 (or depth 0.30).
6. Doc figure: ornament_notes claims rosette LOD0 total depth 0.29 m; the delivered `size` property reads 0.21-0.23 m. Correct.
7. Low: `cavity_attr` is an object property that build_master does not copy to instances (harmless, name is constant).

Passed: asset names/variant regex, all LODs present for all variants, vertex_cavity deterministic and applied after decimate
before bake, relief signs (+Y outward) correct, idempotent, no out-of-ownership files (28 texture bakes are ORN's own).
