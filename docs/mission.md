# Mission (original brief, verbatim)

Build a stunningly beautiful, photoreal 3D model of the Palace of Fine Arts
(the current 1974 concrete reconstruction, not the 1915 original) in Blender,
lit at golden hour. The first deliverable is a .blend file we can open and
fly around in. It must also be render-ready (Cycles) and camera-ready for a
later flythrough video.

Success means: a render from the classic lagoon-side viewpoint at golden hour
is hard to tell from a photograph.

Environment and conventions
Blender 4.x. Check the installed version with blender --version and adapt.
All scene construction is done with Python (bpy) run headless: blender
--background --python scripts/<name>.py. Never rely on manual clicks.
Everything must be reproducible from scripts.
Preview renders use Eevee Next. Final renders use Cycles with denoising.
Units: metric. Scale: 1 Blender unit = 1 meter. World origin is the center of
the rotunda floor. +Y points toward the lagoon.
Each specialist owns its own .blend file under assets/. The lead assembles
master.blend by linking/appending collections. Nobody edits another agent's
file directly. Requests go through the lead.
Every script must be idempotent: running it twice produces the same result,
not duplicate objects. Clear or rebuild your collection at the start.
After any meaningful change, render a 1280x720 Eevee preview from the fixed
QA cameras (see scripts/qa_cameras.py) into
renders/previews/<agent>/<timestamp>.png.
Commit often. One agent, one branch, one worktree. The lead merges.
Repository layout
CLAUDE.md
docs/
  reference_sheet.md        measurements, ornament catalog, photo index
  decisions.md              lead's log of choices and why
  quality_checklist.md      living QA rubric
reference/
  photos/                   named by viewpoint, e.g. lagoon_south_golden.jpg
  plans/                    elevations, plan drawings, any scan data
scripts/
  common.py                 shared helpers (collections, units, materials
loader)
  qa_cameras.py             creates the fixed QA camera set
  build_master.py           assembles master.blend from assets
  <agent>_*.py              each agent's build scripts
assets/
  architecture.blend
  ornament.blend
  materials.blend
  environment.blend
  lighting.blend
master.blend
renders/
  previews/<agent>/
  qa_comparisons/
  final/
The team

Run this as a coordinated team of subagents. The lead is the only agent that
talks to the user. Use parallel subagents where the dependency graph allows
it (see Phases).

1. Lead / Art Director (orchestrator)
Reads this file, writes docs/decisions.md, owns master.blend and
build_master.py.
Defines the art target: current condition, gently weathered concrete, warm
golden-hour light, still lagoon with reflections, no people or cars unless
requested.
Assigns work, sets deadlines per phase, reviews every specialist's previews
against reference photos before accepting.
Resolves conflicts (naming, scale, overlap) and keeps the whole thing
coherent.
Never accepts "looks fine" without a side-by-side against a reference photo.
2. Reference and Research
Collects reference photos from many viewpoints and times of day into
reference/photos/, plus any published dimensions, plans, and public scan or
photogrammetry data. Download only what's licensed for this use; note
sources.
Writes docs/reference_sheet.md containing:
Key dimensions (rotunda height about 49 m, dome diameter, drum diameter,
column height and spacing, colonnade arc radius and sweep, entablature
height, lagoon outline).
Ornament catalog: every distinct repeated element (Corinthian capital, frieze
panel types, the weeping maiden figures, urns, planter boxes, rosettes) with
reference crops and how many times each repeats.
Material catalog: the specific ochre/terracotta concrete tone with sample
colors pulled from photos, streaking patterns, algae line, patched areas.
A list of 6 canonical camera viewpoints with matching reference photos for
QA.
This agent finishes first. Everyone else waits for the reference sheet.
3. Architectural Modeler
Owns assets/architecture.blend, collection ARCH.
Builds to measured dimensions from the reference sheet: rotunda floor, eight
pier groups, drum, dome and lantern, entablature, the curved colonnade with
its column groups and the boxed "planter" tops, steps, plinths, lagoon edge
wall.
Clean quad topology, correct real-world scale, proper origins, named objects
(ARCH_rotunda_dome, ARCH_colonnade_column_01, etc.).
Uses Geometry Nodes or array/curve modifiers for the repeated columns so
spacing can be adjusted from one parameter.
Leaves clearly named empties at every ornament attachment point
(SOCKET_capital_##, SOCKET_maiden_##) so ornament can be instanced onto them.
4. Ornament and Sculpture Modeler
Owns assets/ornament.blend, collection ORN.
Models each element in the ornament catalog once as a high-quality asset:
Corinthian capitals, the frieze reliefs, the weeping maidens (figures with
bowed heads and draped cloth, backs to the viewer, on the colonnade boxes),
urns, rosettes, dentils.
Sculpt at high resolution, then bake normal and displacement maps to a
mid-poly mesh so the scene stays viewable in the viewport.
Each asset ships with a low, mid, and high LOD and a documented socket origin
that matches the architecture empties.
5. Materials and Texturing
Owns assets/materials.blend. Provides a material library the other agents use
by name (MAT_concrete_ochre, MAT_concrete_weathered, MAT_water_lagoon,
etc.).
Physically based, procedural first, image textures where they add realism.
Concrete needs: base ochre tone matched to reference, subtle color variation
per panel, vertical rain streaks, darker algae band at the waterline, soft
edge wear on corners, patch repairs, a hint of specular sheen in low sun.
Uses object-info random and Geometry Nodes attributes so instanced ornament
does not look identical.
Water: realistic index of refraction, gentle procedural ripples, slight murk
and green tint, correct reflection strength at grazing angles.
6. Environment
Owns assets/environment.blend, collection ENV.
Lagoon surface and bed, lawns, paths, the island beds, trees (eucalyptus,
Monterey cypress, willows near water; use a tree addon or particle scatter,
not hand placement), ducks or swans optional, low-detail Marina district
backdrop, distant hills.
Everything outside the hero area is low poly with baked or simple materials.
Viewport performance matters: the user wants to fly around this.
7. Lighting and Rendering
Owns assets/lighting.blend. Also owns the final render settings in
master.blend.
Golden hour: sun elevation roughly 5 to 10 degrees, azimuth from the
west-northwest so the rotunda face toward the lagoon is warmly lit. Use the
Sun Position addon set to San Francisco (37.80 N, 122.45 W) at a real date
and time; document which.
HDRI sky for fill and reflections, matched in color temperature to the sun.
Slight atmospheric haze and volumetric scattering so distant elements soften.
Color management: AgX (or Filmic if unavailable), gentle contrast, no crushed
blacks.
Sets up: a Cycles final config, an Eevee viewport config, and a flythrough
camera path on a bezier curve around the lagoon and through the colonnade for
the future video.
8. QA / Critic
Independent from the builders. Never writes scene code, only reviews.
For each of the 6 canonical viewpoints, renders the current master.blend and
places it side by side with the reference photo in renders/qa_comparisons/.
Maintains docs/quality_checklist.md and scores each round on: silhouette
match, proportion, ornament fidelity, material realism, edge wear, lighting
mood, water reflection, repetition visibility, scale cues.
Writes specific, actionable defects ("drum is roughly 8 percent too tall
relative to dome; compare cam_02") and files them to the lead. Reject
anything that reads as "game asset" or "clean CAD."
Phases and parallelization

Phase 0. Lead sets up repo, common.py, qa_cameras.py, and branch/worktree
plan. (Solo, quick.)

Phase 1. Reference and Research produces docs/reference_sheet.md. (Solo.
Blocking gate. Lead reviews and approves.)

Phase 2. Run these in parallel, each in its own worktree:

Architectural Modeler: blockout at true scale first, then detail.
Ornament Modeler: assets built against the catalog.
Materials: library built against the material catalog.
Environment: terrain, lagoon, trees.
Lighting: sun/sky rig on a placeholder scene.

Gate: lead assembles a first master.blend from blockout geometry plus
placeholder materials. QA produces the first comparison sheet.

Phase 3. Integration. Ornament instanced onto architecture sockets. Materials
applied. Environment and lighting merged. Parallelize the fixes that QA
files back to each owner.

Phase 4. Polish loop. QA scores, lead assigns, specialists fix. Repeat until
every viewpoint scores at target. Expect at least three rounds. Each round
should produce a visibly better comparison sheet.

Phase 5. Deliver. master.blend opens in under a minute, viewport is navigable
in Eevee, Cycles hero render from the lagoon viewpoint is produced at
3840x2160, flythrough camera path exists and a short low-res Eevee test
animation confirms it works.

Non-negotiables
Real dimensions from reference, never eyeballed proportions.
No ornament asset appears identical twice at hero distance. Vary weathering
per instance.
No flat, clean, or plastic-looking materials.
Every claim of "matches reference" is backed by a side-by-side image in
renders/qa_comparisons/.
Keep the file viewable: heavy assets get LODs and the viewport uses the mid
LOD by default.
Log every significant decision in docs/decisions.md.
Reporting to the user

The lead reports at each phase gate with: what was built, the latest
comparison sheet, open defects, and what comes next. Keep it short. Show
images, not adjectives.
