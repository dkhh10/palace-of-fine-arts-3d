# Brief: Architectural Modeler

You own `assets/architecture.blend` (collection `ARCH`) and `scripts/arch_*.py`. Read, in order: `CLAUDE.md`,
`docs/reference_sheet.md`, `docs/sockets.md`, `docs/tech_notes.md`, `scripts/common.py`, `scripts/qa_cameras.py`.
Look at the reference photos named in the sheet (Read tool shows images) before modelling each part. Never eyeball a
dimension the sheet gives; when the sheet is silent, derive from photo ratios and write the derivation in `docs/arch_notes.md`.

## Deliverables
1. `scripts/arch_build.py` (plus `scripts/arch_lib.py` helpers): one idempotent entry point that rebuilds `ARCH` from scratch
   and saves `assets/architecture.blend`. Parameters at the top of the file (or `scripts/arch_params.py`), all in metres.
2. `assets/architecture.blend` with collection `ARCH` and sub-collections `ARCH_rotunda`, `ARCH_colonnade_north`,
   `ARCH_colonnade_south`, `ARCH_site` (platform, steps, rostra, lagoon edge wall of the rotunda island), `ARCH_sockets`.
3. `docs/arch_notes.md`: what was built, parameter table, socket counts per type, tri counts per LOD, known gaps.
4. Previews from the QA cameras after every milestone (`common.render_previews('architecture')`) and commits.

## What to build (all at true scale, in this order: blockout first, then detail)
Rotunda: circular platform with steps down to the lawn; the eight pier groups (chamfered wedge piers at the octagon
vertices, pedestals, paired outer fluted columns with entasis, bases; capital via socket), the eight arch faces with
archivolt mouldings and deep barrel vaults to the inner ring; inner columns (8) with their entablature blocks and inner
arches; entablature with ressauts over each column pair (architrave fascias, frieze band, cornice with corona, dentil and
egg-and-dart courses modelled as geometry); attic with panel frames, corner blocks, top mouldings; drum; dome with the exact
rise from the sheet and its top element; the coffered star ceiling under the dome (a saucer with the octagon/square/rib
pattern as recessed geometry); rostra/planter walls with their Greek-key band recess; urn plinths.
Colonnade (both wings): columns along the two arcs (curve + array/geometry nodes so bay count is a parameter; both rows;
pylon clusters), plinths, entablature swept along the arc, pergola cross beams, planter boxes on the 2x2 clusters with
their framed panels, pylons at the ends with taller boxes. The exhibition hall is ENV's; you only do the colonnade.

## Quality rules
- Quad-dominant clean topology, no live booleans in the saved file (apply them or build the openings directly), smooth
  shading with sharp edges marked where the concrete has crisp arrises, `bevel` modifiers (0.02-0.04 m, 2-3 segments) on
  arrises so nothing is knife-sharp, since the materials agent's edge wear reads from bevels/AO.
- Column shafts: 24 flutes with fillets, entasis per sheet. `_LOD0` fluted, `_LOD1` fluted low-res, `_LOD2` plain cylinder.
- Named objects with the `ARCH_` prefix. Origins at a sensible base point. Apply scale (1,1,1).
- UVs: every mesh gets a box/cube projection UV in metres (use a Python cube-projection helper; the materials use
  object-space triplanar mostly, but UVs are needed for bakes). Store a `part_type` custom property on each object
  (values: wall, pier, column, entablature, attic, drum, dome, ceiling, rostra, platform, colonnade_column,
  colonnade_entablature, box, pylon) and the materials agent will map it to materials.
- Assign materials by name with `common.load_material` (placeholders are fine now): MAT_concrete_ochre (upper rotunda:
  walls, entablature, attic, drum), MAT_concrete_weathered (piers, pedestals, rostra, platform, everything below ~6 m),
  MAT_column_terracotta (pink column shafts), MAT_concrete_inner (inner columns, vault soffits, ceiling),
  MAT_dome_plaster (dome), MAT_concrete_colonnade (all colonnade concrete), MAT_paving (platform floor and steps).
- Sockets exactly per `docs/sockets.md`. Give every socket the custom properties described there.
- Keep it viewable: full ARCH at LOD1 under 2.5 M triangles. Use instancing (linked mesh data) for repeated columns.

## Process
Blockout (massing at true scale, every element as simple geometry) -> render previews -> compare with the sheet's
elevation ratios by overlaying on the canonical photos with `scripts/qa_compare.py` -> commit -> then detail pass by pass
(piers and columns, arches and vaults, entablature, attic, dome, ceiling, colonnade), rendering and committing after each.
Budget: aim to have the blockout committed within the first hour and the detailed model within several hours.
