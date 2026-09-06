# Still-frame realism gate

## Pass 2 — golden hour + statuary (renders/gh_gate_hero.png, 1920x1318, 96 samples)

Brief changed mid-project: target lighting is now a golden-hour sun and the statuary is required.

Lighting: sun at 6.5 deg elevation, compass 118 deg (morning light raking across the east faces from the camera's left),
lamp colour (1.0, 0.72, 0.44) and strength taken from the physical sky's own sun disc measured at that elevation
(~27% of midday irradiance, RGB ratio 1.24:1:0.72), physical multiple-scattering sky with aerosol 1.05, AgX Punchy,
exposure -2.45, compositor mist haze (warm, quadratic from 70 m) and fog-glow glare. A world scattering volume was
tried and rejected (needs volume bounces, black at 0, expensive at 1); the mist-pass haze gives the aerial perspective
at no render cost.

Statuary (public-domain scans from Statens Museum for Kunst casts on Wikimedia Commons, decimated to ~90k/126k tris,
listed in assets/stl/sources.json):
- weeping women: Polyhymnia cast, 3.0 m, four per planter/pylon box, facing the box (ref 138, 187, 032)
- attic corner figures: Doryphoros / Isis-priestess casts alternating, 3.8 m on the corner chamfers (ref 017, 085)
- inner rotunda figures: Pudicitia cast, 2.5 m on the inner entablature blocks (ref 082, 010)
- relief panels: Parthenon Lapith-and-centaur metope and two Trajan's-column slabs composed per attic panel (ref 017, 085
  show centaurs and figure groups in Zimm's panels).

| # | Item | Result |
|---|------|--------|
| 1-8 | structural checklist (piers, vaults, coursing, ornament, coffering, capitals, dome, colonnade) | unchanged from pass 1 — PASS |
| 9 | Lighting / atmosphere | PASS for the new brief: low warm sun with long crisp shadows (columns across the piers, trees across the lawn), sky-lit blue shade, warm horizon glow toward the sun and deeper blue opposite, hazy distance, warm broken reflections on the lagoon |
| 10 | Statuary present and plausible | PASS: figures read as classical statues at animation distances; poses are casts, not the Ellerhusen/Zimm originals |

Known remaining gaps: broadleaf card foliage still reads as scales at full res; relief slabs read faintly under
near-frontal light (they show better from the oblique animation angles).

## Pass 1 — midday (renders/g01_hero.png)

| # | Item | Result | Evidence / refs |
|---|------|--------|-----------------|
| 1 | Pier shape in plan | PASS | Wedge piers at the octagon vertices, one pink column on each adjacent face (~3.5 m c-c), entablature breaks forward over each pair; inner tan column at each inner corner with its own entablature block. Ref 085, 017, 021, 082, 161. |
| 2 | Vault / soffit | PASS | 5 m deep barrel vaults from the outer archivolt to the inner ring, coursed soffit with courses running along the vault. Ref 001, 047, 088, 010. |
| 3 | Wall surface | PASS | Coursed ashlar (1.25 x 0.66 m) with dark recessed joints and per-block tone/hue variation on every stone surface; per-face planar UV so courses follow every face. Ref 047, 083, 007, 016. |
| 4 | Ornament inventory | PASS (stylised) | Archivolt leaf-and-dart + keystone/impost bosses; bead-and-reel architrave; rinceau frieze with rosettes; egg-and-dart + dentils; attic Greek-key framed corner panels, pilaster strips, Greek-key band, anthemion band, modillion cornice; drum rosette band and corner bowls; rostra with Greek key + rosettes. Ref 047, 054, 049, 032, 017, 085, 007, 016, 210. |
| 5 | Ceiling coffering | PASS | Star pattern: central disc; ring of 8 small octagons alternating with 8 squares; ring of 8 larger octagons; 8 rounded-trapezoid panels over the arches; radial ribs with long rectangular recesses; base ring. Ref 003, 083, 082, 001. |
| 6 | Capitals | PASS (stylised) | Two rows of lobed acanthus with drooping tips, corner volutes on cauliculi, inner helices, concave abacus with fleuron; fluted shafts with entasis on Attic bases. Ref 002, 054, 213. |
| 7 | Exterior dome | PASS | Shallow spherical cap, 36 m across, 11.5 m rise, on a low drum with rosette band. Ref 00, 032, 085, satellite. |
| 8 | Colonnade | PASS | Curved double-row Corinthian pergola along the OSM wing outlines, cross beams, planter boxes on 2x2 clusters, tall boxes on 4-column pylons at the wing ends, exhibition hall behind. Ref 138, 165, 167, 187, 214. |
| 9 | Lighting / atmosphere (midday brief) | PASS | Single sun (ESE, 52 deg) with crisp shadows, physical sky, sky-lit shade, rippled grey-green water, gulls, shore shrubs and rip-rap. Ref 00. |
