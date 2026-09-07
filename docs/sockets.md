# Socket contract between ARCH (architecture) and ORN (ornament)  — lead-owned

Every ornament attachment point in `assets/architecture.blend` is an Empty named `SOCKET_<type>_<index>` (index zero-padded
to 3 digits) inside collection `ARCH/ARCH_sockets`. Every ornament asset in `assets/ornament.blend` is a mesh object
`ORN_<type>[_v<variant>]_LOD<n>` inside `ORN/ORN_<type>`. `build_master.py` instances `ORN_<type>` onto every `SOCKET_<type>_*`.

Frame convention for BOTH the socket empty and the asset's object origin:
- Origin at the bottom-centre of the element's footprint (where it sits on the architecture).
- Local +Z = up. Local +Y = outward from the building (toward the viewer / away from the rotunda centre; for colonnade
  elements away from the colonnade's axis toward the lagoon side; for the ceiling, +Y = radially outward).
- Scale 1.0. Metres. The asset is built at real size and must not be rescaled by the socket (ARCH sets socket scale to 1).
- The socket empty carries custom properties: `orn_type` (string, = `<type>`), `size_hint` (float, metres, main dimension),
  and optionally `variant_seed` (int) which the lead uses to pick a variant.

Socket types (counts are for the whole building; ARCH reports the actual numbers in docs/arch_notes.md):

| type | where | expected count | size_hint |
|---|---|---|---|
| `capital_rotunda` | top of each of the 16 outer pink columns (top of shaft; asset = capital only) | 16 | shaft top diameter |
| `capital_inner` | top of each of the 8 inner tan columns | 8 | shaft top diameter |
| `capital_colonnade` | top of every colonnade column (both rows, both wings, pylons) | ~150-200 | shaft top diameter |
| `base_rotunda` / `base_inner` / `base_colonnade` | column bases (Attic base on plinth), if ARCH does not model them itself | as above | shaft bottom diameter |
| `maiden` | on each planter box corner, standing on the box top rim, +Y = the direction the figure's BACK faces (outward) | 4 per box, boxes per reference sheet | figure height |
| `urn` | urn positions on the rostra / pedestals / attic corners as catalogued | per sheet | urn height |
| `attic_panel` | centre-bottom of each attic relief panel, +Y = face normal | per sheet (typically 8 faces x panels) | panel width |
| `attic_figure` | attic corner figure blocks | per sheet | figure height |
| `keystone` | arch keystone masks, +Y = face normal | 8 outer (+8 inner if present) | mask height |
| `frieze_run` | start of a straight entablature frieze run; `size_hint` = run length, custom prop `run_length` | per face/ressaut | length |
| `drum_band` | the scale/rosette band around the drum: one socket at band start with `run_length` = circumference | 1 | height |
| `finial` | dome top / drum corner finials | per sheet | height |
| `rosette_ceiling` | coffer rosettes inside the dome | per sheet | diameter |
| `inner_figure` | the 8 winged "Priestess of Culture" figures on the inner entablature blocks, +Y toward the rotunda centre's opposite (outward), figure faces the centre | 8 | figure height (4.6) |

Contract additions after the Phase 2 build (2026-09-07): sockets may carry a `subtype` string property: keystone
(`crown` / `impost`), finial (`volute_scroll` / `dome_apex`), frieze_run (`greek_fret` plus arc data `arc_center`,
`arc_radius`, `arc_start`, `arc_end` for curved colonnade runs). Podium urns are 24 (3 per pier), attic urns 16.
Actual socket counts delivered by ARCH: capital_rotunda 16, capital_inner 8, capital_colonnade 114, maiden 48, urn 40,
attic_panel 8, attic_figure 8, keystone 24, frieze_run 28, drum_band 1, finial 9, rosette_ceiling 24, inner_figure 8.

Repeated linear ornament (dentils, egg-and-dart, Greek key, rosette bands) is modelled by ORN as ONE unit with a known
length; ARCH either arrays it itself along its profile sweeps using `frieze_run`-style sockets, or (preferred) ARCH
models these small mouldings as geometry directly and only uses ORN for capitals, figures, urns, keystones, relief panels
and finials. State which in docs/arch_notes.md.

LOD rule: the lead instances LOD1 by default in the viewport and switches to LOD0 for Cycles finals via
`common.set_lod_visibility`. LOD0 target < 150k tris per capital, < 300k per maiden; LOD1 < 20k; LOD2 < 2k.
