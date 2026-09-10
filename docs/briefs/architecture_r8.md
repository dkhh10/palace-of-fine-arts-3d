# Architecture round 8 — the arch vaults are closed by chord triangles (brief from the lead, 2026-09-10; user-found defect in the v1 hero).
Branch `architecture`. Read docs/briefs/process.md first. `git merge main` first. Opus high. Every render to renders/final/v2/ or renders/previews/arch/.
THE DEFECT (measured by the lead, renders/logs/lead_raycast3.log, scripts/arch_vault_facecheck.py): `ARCH_rotunda_vault_coffers_00` (build_vault_coffers,
scripts/arch_build.py:696, rib plate from `L.plate` bent onto the barrel with the per-vertex mapping) carries **67 faces of 7-11 m2**, all
triangles with normals along the bay axis (+-(0.12, 0.99, 0)), centred inside the opening at x -1..-4 / y 15-19.5 / z 18-21: 304 m2 of
faces inside the opening band. They are the plate's cap / bridge triangles: the flat plate with holes is triangulated, then the VERTICES are
mapped onto the arc, so any triangle whose vertices sit at different arc angles becomes a chord cutting through the space under the vault.
From cam01 the ray along the bay axis at z 18 and 20 hits this object 2 m past the arch face at z 18.2 / 20.2 where the soffit is at 23.6;
in the 4K hero the upper half of the main arch is a smooth flat plate (renders/final/v1/hero_cam01_3840x2160.png, tile x 1560-2460 y 560-1260).
The same object exists on all 8 bays (bay 07 closes cam02's arch: its "blue soffit" is these chords lit by the sky). Not a placeholder, not a
metric fill: a tessellation bug since round 1.
1. Fix build_vault_coffers so every face follows the barrel: subdivide the plate along the arc (bisect at <= 0.25 m spacing, or build the rib
   network as arc-following strips) BEFORE the mapping so no face spans more than one step in s; keep the octagon / diamond coffers, the 0.38
   depth, the registers, the taper r0 -> r1 and the materials. Do the same check for `ARCH_rotunda_vault_NN` (the panel: 0 faces over 1.5 m2 now,
   keep it so), the inner archivolt and any other plate-bent-onto-arc object (grep for the mapping pattern). Acceptance, all 8 bays, in
   `scripts/arch_vault_facecheck.py` (extend the lead's script: per bay, no face with centre more than 0.45 m below the local soffit radius
   r(t), no face over 1.0 m2, exit 1 otherwise) and a ray test from cam01 (bay 00) and cam02 (bay 07) along the bay axis at z 16-22: first hit
   must be the far side or the soffit at its radius.
2. The slab across the opening: in the v1 tile a straight horizontal edge cuts the opening at about the springing height behind the vault, and
   the inner arch behind it reads as a flat lintel. Identify it (ray test at z 16-18 along the axis; candidates: `ARCH_rotunda_inner_block_cap_NN`,
   the inner archivolt, the inner arch's own chords) and fix it if it is not real geometry; docs/reference_sheet.md lines 140-141 and 192-198:
   deep barrel vaults join the outer and inner arches, open to the ground on both sides.
3. cam03's near column: the camera stands 1.6-1.8 m from `ARCH_colonnade_south_column_028` (the left edge of the frame) and it renders as a
   plain cylinder with no fluting and no capital. Check the LOD0 mesh (LOD1 is hidden at render), the fluting, whether the capital socket
   `SOCKET_capital_##` for that column is instanced (INST_capital_colonnade_*), and fix (fluting on the LOD0, capital instance present). State
   the column's px width in the cam03 frame.
4. Renders (after the fixes, on your rebuilt master in the worktree): Cycles cam01 1920x1080 64 spp, Cycles cam02 and cam03 1280x720 64 spp,
   through blender_run.sh (max 1200 / 900 / 900), into renders/previews/arch/r8_*.png. Inspect cam01 in six 100 % tiles (3 x 2) and cam02 / cam03
   in four tiles each with the Read tool (crop with PIL; do NOT judge from a 960 px downscale); report every visible defect you see in the
   tiles, fixed or not. Commit the renders and the tile crops of the arch.
Do not touch lighting / materials files; do not re-tune anything to hold a shade number (lighting re-bases the cam02 soffit box after you).
Deliverables: scripts, assets/architecture.blend, arch_notes.md round 8 section with the face-check table per bay and the ray tests, the three
renders, commits after every successful script, report < 25 lines with the last commit id.
