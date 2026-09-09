# Palace of Fine Arts — Reference sheet (Phase 1)

Reference & Research specialist, 2026-09-06. Everything below is either **documented** (cited source) or **measured**
(photo ref number + method) or an **estimate** (marked). Photo refs are `reference/photos/raw/ref_NNN_*.jpg`
(index: `reference/photos/index_wikimedia.csv`); the user's target is `reference/photos/user/user_wide_midday.png`.
World coordinates: origin = rotunda floor centre, z = 0 = rotunda floor, +Y = east (lagoon), −X = north, +X = south.

**Read this first — three findings that change the build**

1. **The user target image is not proportionally reliable.** Measured against real photos (refs 085, 022, 070) its
   dome is ~25 % too wide relative to the attic (dome/attic width 0.90 vs 0.72 in photos) and its drum is a third of
   the real height. Use it for composition, framing, mood and colour only; take proportions from section 2.
2. **Attempt 2 got the dome wrong in the opposite direction from what the critique said.** The real dome is a shallow
   cap: rise ≈ 0.235 × base diameter (refs 085, 022, user image all agree). Attempt 2 used 11.5 / 36 = 0.32 (too
   tall) but its attic (6.1 m) was too *short* and its drum (2.0 m) too short. Fixing the dome fixes the "top-heavy" look.
3. **Golden hour must be morning.** The lagoon is east of the rotunda (section 1); the best golden-hour photo in the
   corpus (ref 169, "morning golden hour", 2020-02-01 ~08:00) is exactly our chosen light: sun az ≈ 115°, el ≈ 7°.

Sources used repeatedly (short names):
- **DPR** = California DPR 523 / NRHP continuation sheets for the Palace of Fine Arts (NRHP #04000659, SFDL #88), 37 pp,
  https://ohp.parks.ca.gov/pages/1067/files/CHL_San%20Francisco_Palace%20of%20Fine%20Arts.pdf (text extracted with pdftotext).
- **Wiki** = https://en.wikipedia.org/wiki/Palace_of_Fine_Arts
- **SFGate-2003** = "Tattered treasure ..." SF Chronicle restoration article (22 ft attic figures, 15 ft angels, "135-foot dome",
  10 ft urns, double dome) https://www.sfgate.com/news/article/Tattered-treasure-Saved-from-ruin-once-the-2858997.php
- **SFGate-1980s** = "Guarding the Palace" (26 bas-reliefs on the colonnade boxes) https://www.sfgate.com
- **Anargyros** = https://en.wikipedia.org/wiki/Spero_Anargyros (52 weeping ladies at 15 ft; 22 ft figures)
- **KQED** = https://www.kqed.org/news/11732261/whats-up-with-the-weeping-women-at-the-palace-of-fine-arts
- **Roofing** = https://www.roofingcontractor.com/articles/84956-project-profile-palace-of-fine-arts (dome coating)
- **OSM** = `reference/plans/site_local.json` (OpenStreetMap footprints, metres, origin rotunda centre, +x east, +y north)
- **SAT** = `reference/plans/satellite_z20.png` (ESRI World Imagery, zoom 20, 0.118 m/px, scale bar in the image)

---

## 1. Site and orientation

**Documented.** "A domed rotunda occupies a small central peninsula on the west side of the lagoon ... The features of the
Palace of Fine Arts are arranged so that they face the residential neighborhood to the east" (DPR p.4-5). "The curving
exhibition building is at the rear, visually terminating the view from the east through the rotunda and the colonnades"
(DPR). Coordinates 37°48′10″N 122°26′54″W (Wiki); `common.LAT, LON = 37.8029, -122.4484`.

**Confirmed from data/photos.** OSM lagoon polygon lies entirely at x_east > −20 m (world Y > −20): the water is east of the
rotunda and wraps around its north-east and south-east. Every classic photo (user image, 022, 141, 169, 174-177) is taken
from the east shore looking west; the exhibition hall roofline appears behind the colonnades (user image left, 022 left).

**Lagoon (OSM `lagoon0`, converted with `common.osm_to_world`).**

| item | world coords (X south, Y east) | source |
|---|---|---|
| lagoon bounding box | X −134.8 … +106.6, Y −20.1 … +117.6 (area 16 940 m²) | OSM, shoelace |
| shore in front of the lagoon face (az 82°) | ~100 m from the rotunda centre; ray hits: az 90° → 96.5 m, az 75° → 109 m, az 105° → 121 m | OSM ray cast |
| rotunda peninsula edge | 44-47 m from the centre toward the east/NE/SE (az 15°-135°); the water reaches to r ≈ 34-36 m at az 0° (north) and 165°-180° (south), i.e. two embayments flanking the rotunda ("Two embayments of the lagoon penetrate to the curved footprints of the colonnades", DPR) | OSM |
| north islet `lagoon1` (wooded, herons) | X −123 … −72, Y 53.5 … 82 (919 m²), 80-120 m north-east of the rotunda | OSM; DPR "small wooded island at its north end" |
| tiny islet `lagoon2` | X −90 … −87, Y 47 … 50 (8 m², a rock) | OSM |
| east shore | irregular; "regular where it meets the colonnades and rotunda on the west" (DPR); hard rip-rap edge (refs 022, 063, 187), "soft edge restored in many locations in the 2013 renovation" (DPR) | |

**Ground levels (estimate, reasoning).** Water z: attempt 2 measured floor 1.3 m above water. Cross-checks: ref 022
(face-on, level camera) gives ground-to-water 15 px vs 145 px attic (≈ 0.10 × attic height 7.1 m ≈ 0.75 m); ref 070 gives
~1.2 m (perspective-inflated); ref 063 shows ~6-8 steps from the lawn to the rotunda floor (≈ 1.0-1.3 m) and the
peninsula lawn ~0.6-0.8 m above water. Recommendation: **WATER_Z = −1.3 m** (keep), **lawn/path on the peninsula
= −0.6 m**, **east-shore lawn = −0.4 … −0.8 m**, rotunda floor = 0. The rotunda floor is "ground level floor" (DPR: inner
columns "rising from the ground level floor"), i.e. a few steps above the surrounding paths, not on top of the podium.

---

## 2. Key dimensions (metres)

### 2a. Published figures

| item | value | metres | source (quote) | confidence |
|---|---|---|---|---|
| dome apex above rotunda floor | 162 ft | **49.4** | DPR p.5: "The apex of the dome is 162 feet above the rotunda floor" (also Wiki "162-foot-high (49-meter) open rotunda") | high |
| "diameter of the rotunda" | 160 ft | **48.8** | DPR p.5: "the diameter of the rotunda 160 feet" (not defined; consistent with the column-axis vertex-to-vertex diameter, see 2b) | medium |
| "the mighty 135-foot dome" | 135 ft | 41.1 | SFGate-2003 (journalistic; consistent with the drum cornice ring outer diameter ≈ 37-41 m, not with the smooth cap ≈ 33 m) | low |
| attic corner figures | 22 ft, hollow | 6.7 | SFGate-2003 "tall decorative figures of men and women ... are 22 feet high and hollow inside"; Anargyros "22 feet" | high |
| winged "Priestess of Culture" figures inside | 15 ft, solid | 4.6 | SFGate-2003 "The winged angels inside the dome are 15 feet tall and made of solid poured concrete" | high |
| weeping maidens | 52 figures, 15 ft | 4.6 | Anargyros: "recreation of the 52 weeping lady outdoor sculptures standing at 15 feet (4.6 m)"; KQED: boxes "surrounded on each corner by 'weeping women'" → 4 per box → **13 boxes** | high (count), medium (height — photo 187 suggests ≈ 4.0-4.3 m, see 2b) |
| garland relief panels on the boxes | 26 | — | SFGate-1980s "cast as extras for the 26 on the colonnade" → 2 per box | medium |
| podium urns | 10 ft | 3.0 | SFGate-2003 "The 10-foot-high ornamental urns that decorate the exterior" | medium |
| exhibition hall | outer arc 1,100 ft, inner arc 950 ft, 135 ft wide, truss 45 ft high | 335 / 290 / 41 / 13.7 | DPR p.5 | high |
| "1,100 ft pergola" | 1,100 ft | 335 | Wiki "a wide, 1,100 ft (340 m) pergola" — almost certainly a conflation with the hall's outer arc; OSM colonnade arcs total ≈ 190 m | low |
| site | 17 acres | 6.9 ha | Wiki, DPR (16.99 acre) | high |
| construction | poured-in-place concrete, precast details/sculpture, exposed (no stucco); coffered ceiling = casting plaster; steel I-beams in the dome; "double domes, one inside another" | — | DPR p.5, Wiki, SFGate-2003 | high |
| dome roof | 1964 neoprene-hypalon (Gacoflex 20NH); 1980s acrylic recoat; 2004 full replacement with urethane system, "UA-60 topcoat (aliphatic gloss urethane) in a special color" | — | Roofing | high |
| colour history | "By 1964, colors had faded or peeled, tending to a buff tone while the paired columns on the rotunda's exterior were russet. These warmer tones were reproduced throughout" ; "columns are tinted red to mimic Numidian marble" | — | DPR p.7-8, p.5 | high |
| restoration 2003-2011 | seismic upgrade of rotunda/colonnades, lagoon edge rebuilt and dredged, walkways, lighting; landscape restored 2013 | — | DPR, SF Public Works, Wiki | high |
| HABS | HABS CA-1909 "Palace of Fine Arts, Baker Street" exists at LoC (https://www.loc.gov/item/ca0686/) — photographs; **no measured drawings found online**; Maybeck drawings are at UC Berkeley EDA (not online at usable resolution) | — | LoC search | — |

### 2b. Photo-measured proportions and the recommended numbers

Method. Pixel ratios read from gridded copies (ffmpeg drawgrid, 25/50 px) of: **ref 085** (vertex-on, long telephoto from
the east shore, overcast — least perspective, upper stack), **ref 022** (face-on from the east shore, level camera),
**ref 070** (portrait from the peninsula shore, lower stack), **ref 187** (colonnade frontal), **SAT** (dome diameter),
user image (composition only). All widths are expressed in units of **W_a = face-on width across the attic corner blocks
(= 2 × attic circumradius × cos 22.5°)**; heights were chained capital → shaft → pedestal from photos where the elements
share the same depth, then scaled so that floor→apex = 49.4 m. Depth correction: front-plane elements in a ~100 m photo
are ~20 % larger than centre-plane elements; this was applied where noted.

Anchors: SAT smooth dome cap ≈ 33.3 m (845 px at 3×, ±1 m), drum cornice ring ≈ 37.4 m; ref 085 dome base 1010 px vs attic
corner width 1520 px (vertex-on) → W_a ≈ 46 m; DPR 160 ft ≈ column-axis vertex-to-vertex (49 m). **W_a = 45 ± 1.5 m** adopted.

Ratios measured (W_a units): dome base 0.72 (085, 022); dome rise 0.17 (085: 240/1404; 022: 155/900; user 0.17);
drum 0.083 (085, 022); attic 0.16-0.18 (085 0.18, 070 0.18, 022 0.16); entablature 0.094 (085, 022);
capital 0.058-0.064; shaft/capital 5.8-6.5 (070 corrected, 022); pedestal/capital 1.4 (022); podium wall/capital 1.9 (022);
column pair spacing (straight line between axes) 0.10 (085 vertex-on 150/1404; user 0.10); shaft top diameter 0.050 (085).

**Vertical stack — recommended (z above rotunda floor).** Sum forced to 49.4 m.

| element | height (m) | z bottom → top | attempt 2 (converted to floor datum) | verdict |
|---|---|---|---|---|
| podium / planter wall (rusticated, Greek-key band at top) | 4.3 ±0.5 | 0.0 → 4.3 | platform 0 + pedestal starts at 0 | attempt 2 had no podium below the pedestal; add it |
| column pedestal (plain block, 3.4 × 3.4 m plan) | 3.2 ±0.4 | 4.3 → 7.5 | 4.6 (ending at 4.6) | pedestal top 7.5 vs 4.6: **too low in attempt 2** |
| column base (plinth + torus) | 1.0 | 7.5 → 8.5 | 1.0 | ok |
| shaft (fluted, entasis; D 2.5 bottom, 2.1 top) | 16.3 ±0.8 | 8.5 → 24.8 | 16.6 | ok |
| capital (Corinthian) | 2.6 ±0.2 | 24.8 → 27.4 | 2.8 | ok |
| entablature (architrave 1.4, frieze 1.2, cornice 1.2) | 3.8 ±0.3 | 27.4 → 31.2 | 3.3 | slightly taller |
| attic (panel storey incl. base moulding and top cornice) | 7.1 ±0.6 | 31.2 → 38.3 | 6.1 | **taller** (panel field itself ≈ 4.5 m) |
| drum ("broad cushion ring with guilloche molding", scale band + cornice) | 3.5 ±0.4 | 38.3 → 41.8 | 2.0 | **taller** |
| dome rise (smooth cap) | 7.6 ±0.5 | 41.8 → 49.4 | 11.5 | **much lower** — attempt 2 dome far too tall |
| **apex** | | **49.4** | 47.9 | |

Arch (front plane): clear span **12.5 ±0.5 m** (085: left arch intrados 360 px/0.924 → 0.277 W_a), semicircular; intrados
crown at z ≈ 23.7 (085: 75 px below the abacus); springing at **z ≈ 17.5**. Attempt 2: span 11.6-12.4, springing 18.2 — ok.
Keystone lion mask centred on the extrados crown; small lion masks at the imposts.

Widths / plan (see section 3 for the full geometry):

| item | recommended | measured from | attempt 2 | verdict |
|---|---|---|---|---|
| attic panel-face apothem | 21.5 ±1.0 | W_a 45 → corner circumradius 24.4; panels set flush over the arch wall | 18.8 | **too small** |
| arch-wall (outer face) apothem | 21.5 ±1.0 | OSM outline retreats to r ≈ 22 between piers; same as attic | 19.8 (spec 22.0) | params too small |
| octagon face length at the wall | 17.8 | = 2·21.5·tan 22.5° | 16.4 | |
| column-axis circumradius (vertex-to-vertex Ø 48.8 ≈ 160 ft) | 23.9 ±0.6 | DPR 160 ft; 085 entablature ends | 22.6 | slightly small |
| column pair spacing (axis to axis, straight line across the vertex) | 4.5 ±0.4 | 085 150 px; user 46/40 px; face-on projection = 4.15 | 3.5 | **too tight** |
| column diameter bottom / top | 2.5 / 2.1 | 085 top 70 px; entasis ratio 0.85 assumed | 2.4 | ok |
| column axis outside the wall plane (o) / along-face from vertex (d) | 1.3 / 1.9 | solved from R_col and spacing (see §3) | 1.3 / — | |
| dome base diameter (smooth cap) | 33.0 ±1.0 | SAT 33.3; 085 0.72 W_a | 36 | **too wide** |
| dome sphere radius / centre z | 21.7 / 27.7 | from cap radius 16.5 and rise 7.6 | — | |
| drum: scale band outer radius / cornice ring outer radius | 17.5 / 18.7 | SAT ring 37.4 m; 085 cornice ends 1120 px | 18.5 | ok |
| inner (tan) columns: axis circumradius / D / height to abacus | 16.0 / 1.7 / 13.0 | **not re-measured** (attempt 2 values; 083/082 show them ≈ 2/3 of the outer order) | same | unverified |
| vault depth (outer arch face → inner arch face) | 6.0 | attempt 2 (047, 088 show deep coursed barrel vaults); not re-measured | 6.0 | unverified |
| inner arch springing / coffered ceiling base ring / ceiling rise | 17.5 / 24.5 / 5.0 | attempt 2, plausible from 083 | same | unverified |
| pedestal plan | 3.4 × 3.4 | 063 (pedestal slightly wider than the base plinth) | 3.1 | |
| podium urns (ovoid, on plinths flanking each pedestal) | 3.0 tall incl. lid, ≈ 1.6 Ø | SFGate-2003 10 ft | — | |
| attic corner figures | 6.7 tall | SFGate-2003 22 ft | 3.8 | **far too small** |
| inner winged figures | 4.6 tall | SFGate-2003 15 ft | 2.5 | too small |

**Colonnade (refs 187, 138, 128, 022, user image; OSM).** Scale from the user image and 022: colonnade entablature top
≈ 0.53 × rotunda entablature-top height → ≈ 16.5 m above ground; ref 187 ratios (column 580 px, entablature 100, box 125,
maidens 170, plinth 50, column width 65).

| item | recommended | attempt 2 | note |
|---|---|---|---|
| column diameter | 1.7 ±0.2 | 2.0 | 187: 65 px / 43 px·m⁻¹ |
| plinth+base / shaft / capital | 1.0 / 11.2 / 1.8 → abacus at 14.0 | 1.0+0.7 / 15.5 / 2.2 → 19.4 | **attempt 2 colonnade ~5 m too tall** |
| entablature (Greek-fret architrave, plain frieze, mutule cornice with egg-and-dart and the "AM" monogram, DPR) | 2.4 → top at 16.4 | 2.6 | |
| pergola cross beams | ≈ 0.6 deep, span the two rows (4.5 m apart), one per bay | — | 138, 187 |
| bay (centre to centre along the arc) | 4.6 ±0.4 | 4.6 | 187: ~185 px |
| planter box on 2×2 column cluster | 5.3 × 5.3 plan, 3.0 tall, top at ≈ 19.5 | 5.0 tall | 187: box 125 px; pylon columns rise to the entablature top ("column capitals reach to the tops of the entablature", DPR) i.e. their shafts are ~2.4 m taller than the row columns |
| weeping maidens | 4.3 (photo) … 4.6 (published) tall, 4 per box, backs to the outside, heads at ≈ 23-24 m | 3.0 | see §4 |
| boxes total | 13 (52 figures / 4; 26 garland panels / 2): per wing 5 along the arc + the quadrangular end pylon group; **exact positions must be counted on the OSM wing polygons / ref 187 by the modeler** (uncertain) | every 5th cluster | |
| end pylons (`roof313` north, `roof314` south) | 10 × 12 m quadrangles at ≈ 104 m from the rotunda centre: world (−104, −3) and (100, 30) | — | OSM |
| nearest colonnade end to the rotunda | ≈ 30 m from the rotunda centre, 15-25 m west (behind) of the rotunda's centre plane: world ≈ (−25, −15) north wing, (30, −18) south wing | — | OSM `roof310`/`roof306` bbox (estimate ±5 m) |

---

## 3. Plan geometry

### 3a. Octagon orientation

OSM rotunda outline (188 nodes) shows eight pier lobes centred at OSM angles 30.5° + 45k (CCW from east), i.e. faces centred
at **8° + 45k** (attempt 2's finding, confirmed). In compass azimuth: **face normals at 82° + 45k** (82, 127, 172, 217, 262,
307, 352, 37); **vertices (pier axes) at 59.5° + 45k** (59.5, 104.5, 149.5, 194.5, 239.5, 284.5, 329.5, 14.5).
The lagoon face points 8° north of due east; the hero camera stands on that normal. In world axes a compass azimuth `az`
at radius `r` is `X = −r·cos(az)`, `Y = r·sin(az)`. Uncertainty of the OSM angle: ±3°.

### 3b. Rotunda (recommended numbers; all in metres, z above floor)

- Arch-wall octagon: apothem 21.5, circumradius 23.27, face 17.8. Piers "triangular in plan" (DPR): at each vertex the
  two wall faces meet; the arch opening (12.5) is centred on each face leaving 2.65 m of pier on each side at the wall.
- Outer column pair per pier: axes at `V + d·u + o·n` with d = 1.9 (along the face from the vertex) and o = 1.3 (outside
  the wall plane) → axis circumradius 23.85, pair spacing 4.51 (checked numerically). Columns on 3.4 m square pedestals,
  pedestal top z 7.5, on the podium (top z 4.3).
- Entablature breaks forward over each pair ("angled impost blocks with a rinceau pattern protruding from a plain frieze.
  The blocks serve to 'turn' the rotunda", DPR) — a plain frieze between the ressauts, ornament only on the ressaut faces.
- Attic: panel faces flush over the arch walls (apothem 21.5, eight relief panels); corner "niches" over the ressauts
  project to circumradius ≈ 25.0, each with a 6.7 m standing figure, topped by volute scrolls and a pair of urns.
- Drum: circular; cornice ring radius 18.7, guilloche/scale cushion band radius 17.5 (band height ≈ 1.6), z 38.3-41.8.
- Dome: spherical cap radius 16.5 at z 41.8, apex 49.4, sphere radius 21.7 centred at z 27.7. No lantern; a small metal
  cap/finial at the apex (085 shows a tiny nub only). Seam lines of the roofing membrane run meridionally (085, 032).
- Inner ring: eight tan single columns at the inner vertices (circumradius 16.0, D 1.7, abacus z ≈ 13.0 + entablature
  block ≈ 2.0 with the 4.6 m winged "Priestess of Culture" figure standing on it facing the centre); inner arches
  (span ≈ 12.4) spring from the blocks; deep barrel vaults (6.0) join outer and inner arches; coffered plaster saucer dome
  inside (base ring z ≈ 24.5, rise ≈ 5). Between it and the outer shell is the "attic" void with steel framing.
- Podium/"rostra": around each pier a raised planter/podium block, roughly 9 m wide tangentially and extending from the
  wall face to r ≈ 27.5 (OSM lobes), with curved planter walls ("stepped planters") that on some piers sweep out to
  r 30-37.6 (OSM nodes 19-23, 40-42, 70-71, 88-90, 163-164, 181-183). Two stair flights on the lagoon side (063 right).
  Greek-key/rosette band along the top of these walls (§4).
- Floor: paved, level; the eight vault bays open to the ground on both sides (no doors, no glazing).

### 3c. Colonnades

The DPR: "The radius of the exhibition building and colonnades is struck from a point on the eastern side of the lagoon".
Constrained circle fits (centre on the E-W axis) to the OSM roof polygons: south wing `roof306` centre osm (54, 0) r 84.8;
north wing `roof310` centre osm (71.7, 0) r 109 (asymmetric — the OSM trace is rough); both together centre osm (51.8, 0)
→ world (0, +52), r ≈ 89. Hall `b302` centre osm (7, 0) r 106 (its east wall). **Use the OSM polygons themselves
(`common.load_site_local()`) as the footprint authority**; treat the arcs as: two rows 4.5 m apart, bay 4.6 m, wings
sweeping from ≈ 30 m behind the rotunda out to the end pylons at ≈ 104 m, angular extent about the common centre:
south −159° … −90°, north 107° … 167° (OSM angles CCW from east). The south wing runs roughly from world (30, −18) to
(100, 30); the north wing from (−25, −15) to (−104, −3). The exhibition hall (`b302`, 20 m tall per OSM tag; DPR truss
45 ft = 13.7 m at the centre plus parapet) stands 20-25 m behind the colonnades, screened by redwoods planted 1968 (DPR).

### 3d. Plan sketch (world axes, not to scale; N is up = −X)

```
                       N (−X)
                        ^
       north wing       |        lagoon islet (−100,+65)
      /‾‾‾‾‾‾‾‾\        |
     |  pylon   ‾‾‾‾\   |
     | (−104,−3)     \  |     water
      \               \ |                    east shore, hero camera
       hall (b302)     \|   rotunda  ---------------->  (−16, +114)  +Y (east)
       r≈106 about      *   octagon
       (0,+7)          /|   faces at az 82+45k
      /               / |
     | (100,+30)  ___/  |     water
     |  pylon   /       |
      \________/  south wing (arc r≈85 about (0,+52))
                        v
                       S (+X)
```

---

## 4. Ornament catalog

Crops: `reference/photos/ornament_crops/` (52 files, made by the ornament sub-researcher from the refs listed; the
sub-researcher's process was interrupted before its text was written, so descriptions below are mine, from the same
photos). Sizes are from §2 unless a ratio is given.

| # | element | occurs / count | size (m) | crops | description (model from this) |
|---|---|---|---|---|---|
| 1 | Corinthian capital, outer pink columns | 16 (8 piers × 2) | h 2.6, abacus ≈ 3.0 across, over a 2.1 m shaft top | corinthian_capital_1-3 (002, 060, 054) | Classic Roman Corinthian: two rows of 8 acanthus leaves (lower row short, upper row taller with drooping tips), cauliculi, 4 corner volutes + 4 inner helices, concave abacus with a central fleuron on each face; astragal (bead) at the shaft top. Cast concrete, softened detail, dust in the leaf recesses (049, 054). The DPR calls the columns "tinted red to mimic Numidian marble" — the capital is *tan* like the walls, not pink (047, 049). |
| 2 | Capital, inner tan columns | 8 | h ≈ 1.8 (order ≈ 2/3 of the outer) | inner_capital_1-2 (082, 083) | Same Corinthian design, smaller; carries a square entablature block bearing the winged figure. |
| 3 | Capital, colonnade columns | ≈ 70 row columns + 4-column pylon clusters | h ≈ 1.8 on a 1.7 m shaft | colonnade_capital_1-2 (138, 128), pylon_capital_1-2 (142, 167), pilaster_capital_1 | Corinthian again, slightly simpler leaves; pylon-cluster capitals identical but 2.4 m higher. Colonnade shafts ARE fluted (24 flutes, 128, 138). |
| 4 | Column base + plinth | all columns | base h 1.0 (torus-scotia-torus Attic base on a square plinth) | column_base_1-3 (113, 161, 016) | Attic base; plinth square = 1.15 × shaft D. Colonnade bases sit on a low square plinth on the gravel (113 shows the plinth with a chamfer; ivy at 129). Lower torus often stained green/black. |
| 5 | Fluting | outer, inner and colonnade shafts | 24 flutes, fillets ≈ 0.25 × flute width | (see capital and base crops; 054, 088, 128) | Flutes run full height between the astragal and the base apophyge, rounded ends top and bottom. Faint horizontal drum/pour lines every ≈ 2.5 m (054, 049). |
| 6 | Zimm attic relief panels ("The Struggle for the Beautiful") | 8 panels, **3 repeating designs** (Wiki: "three repeating panels around the entablature of the rotunda") | panel field ≈ 4.5 h × 10.5 w; frame Greek-key band ≈ 0.45; relief depth ≈ 0.25 | zimm_panel_1-4 (017, 085, 069, 032) | Alto-relievo friezes of nude/draped figures in dramatic classical attitudes with horses/centaurs and kneeling figures; ~8-12 figures per panel; figures ≈ 3.5 m tall; sunk field with a plain fascia and a Greek-key meander band above; corner blocks flank. Designs (from 017/085/069): A "combat with centaur/horse" (central rearing horse), B "procession/garland bearers", C "kneeling group with a standing central figure". Assign A,B,C,A,B,C,A,B around the faces. |
| 7 | Attic corner figures ("Contemplation, Wonderment and Meditation", Ellerhusen; recast Anargyros) | 8 niches × 1 figure = 8 (male and female alternate, DPR "giant male and female figures") | 6.7 tall (22 ft), hollow | attic_corner_figure_1-3 (054/055/056, 032, 017), pier_corner_figure_1 | Standing draped figure in a shallow rectangular niche between fluted pilaster strips, one arm raised to the chest, head bowed slightly, heavy vertical drapery; stands on the ressaut. Niche capped by a pair of Ionic-like volute scrolls (≈ 1.5 m) and a pair of "Roman funerary urns" (DPR) ≈ 1.6 m tall, one each side. |
| 8 | Weeping maidens (Ellerhusen) | 52 = 13 boxes × 4 | 4.3-4.6 tall | weeping_maidens_1-3 (163, 187, 185) | Standing draped female figures at the four corners of each box, **backs to the outside**, arms resting on the box rim, heads bowed into the box ("looking in", DPR); long peplos-like drapery falling in vertical folds, hair bound. Slight differences per figure are fine (all were recast from 4 models — uncertain). |
| 9 | Garland relief panels on the boxes | 26 (2 per box) | ≈ 1.2 h × 2.5 w | garland_maidens_1-3 (136, 138, 187) | Between the corner maidens each box face has a sunk rectangular panel with a Greek-key frame; two faces carry a low relief of a standing maiden holding a swag garland ("Garland Lady", 136). Box top rim plain, a Greek-key band at the box base (187). |
| 10 | Inner winged figures ("Priestess of Culture", Herbert Adams) | 8 | 4.6 tall | angel_1-2 (107, 125) | Winged, draped female, "holding paired cornucopias ... gazes downward" (DPR); stands on the inner entablature block facing the rotunda centre; wings folded up behind the shoulders (185). |
| 11 | Podium urns | 16 (2 per pier, flanking the pedestal) + drum-level urns 16 (2 per corner niche) | podium urns 3.0 h (10 ft), 1.6 Ø; niche urns ≈ 1.6 h | urn_pedestal_1-2 (028, 077), urn_tub_1 (186), drum_urn_finial_1-2 (032, 017) | Podium urns: ovoid body with a fluted/gadrooned lower half, a band of inscription "in a vaguely Latin language" (SFGate-2003) around the shoulder, two small loop handles, domed lid with a knob; on a square plinth at podium level. Niche urns: smaller, same profile. Also large bowl "tubs" on the colonnade pylons (186). |
| 12 | Rostra / podium band | along all podium and planter wall tops | band h ≈ 0.5, rosettes ≈ 0.45 Ø | rostra_band_1-2 (007, 016) | Running Greek-key meander interrupted by square rosette bosses (alternating), incised into the top course of the rusticated podium; below it plain rusticated courses (joints ≈ 0.6 m). |
| 13 | Entablature mouldings (rotunda) | over every pier and along the faces | architrave 1.4 (3 fasciae + bead-and-reel), frieze 1.2 (rinceau on ressauts, plain between), cornice 1.2 (egg-and-dart, dentils ≈ 0.15 pitch, plain corona) | entablature_1-3 (047, 054, 017) | Rinceau = scrolling acanthus with rosette bosses. Modillion (block-bracket) cornice with a Greek-key band forms the attic base over the ressauts (085, 017). |
| 14 | Keystone masks / imposts | 8 keystones + 16 impost masks | lion mask ≈ 0.8 | keystone_mask_1-3 (047, 017, 021) | Lion head on the extrados crown of each outer arch; smaller lion masks at the springing; archivolt: leaf-and-dart (Lesbian cymatium) + bead-and-reel bands, ≈ 0.8 wide. |
| 15 | Drum band | 1 ring | band h ≈ 1.6, r 17.5 | drum_urn_finial_1-2 | "Broad cushion ring with guilloche molding" (DPR): an imbricated scale/guilloche pattern (≈ 0.35 pitch) over a plain torus, then a moulded cornice ring (r 18.7) with a rope/bead moulding; a dark metal flashing strip where the roof meets the band (017). |
| 16 | Coffered ceiling | 1 | Ø ≈ 31 (inner octagon), rise ≈ 5 | coffered_ceiling_1-3 (003, 083, 019) | Eight-fold star in casting plaster (DPR). From the centre: (0) plain flat disc ≈ 6 m Ø; (1) ring of 8 small octagons alternating with 8 small squares on the diagonals; (2) 8 larger octagons on the same 8 radial arms; (3) 8 large rounded-trapezoid panels (curved outer edge) over the arches — the former Reid mural insets, now plain; between the arms 8 radial ribs each with a long narrow rectangular recess and a small triangular coffer at the rim. All ribs carry an acanthus-leaf frame with rosettes (083). Base ring with rosette band above the inner arches. |
| 17 | Colonnade entablature | both wings | h 2.4 | colonnade_entablature_1-2 (138, 187) | Greek-fret (meander) architrave, plain frieze, projecting cornice on mutules with egg-and-dart and Maybeck's "AM" monogram (DPR); pergola cross beams between the rows, open to the sky. |
| 18 | Railings, lamps, signs, bollards | site | — | lamps_railings_1-2, signs_1-2 (021, 178, 179, 184, 149) | Present today: low post-and-chain rope fences along planted beds (187), simple black lamp posts on the path (149), two granite "PALACE OF FINE ARTS" signs (178/179), a bronze floor medallion (184). None on the rotunda itself. **Omit from the hero render** except the rope fence if visible. |

Not present today (do not model): Reid murals, 1915 polychromy, the 1915 hedge, the hall's exterior ornament.

---

## 5. Material catalog

Colour samples are rectangle means measured with Blender (`bpy` pixel averaging; sRGB 0-255 and linear 0-1 as in the
file), rectangles given as (x, y, w, h) in the 1920-px reference files. Full table in the commit message notes; key values:

| surface / light | ref & rect | sRGB | linear | note |
|---|---|---|---|---|
| wall, attic plain, overcast | 085 (521,658,68,150) | 142 111 82 | 0.270 0.160 0.084 | frontal, soft light — closest to albedo × sky |
| wall, attic plain, overcast | 017 (452,438,82,205) | 151 123 95 | 0.310 0.197 0.115 | |
| wall, above arch, overcast | 017 (644,891,137,109) | 149 119 90 | 0.299 0.183 0.102 | |
| wall in low sun (golden) | 047 (685,301,274,82) | 249 211 157 | 0.949 0.649 0.337 | near clipping |
| wall in shade, golden hour | 047 (1371,562,109,68) | 168 125 83 | 0.389 0.206 0.086 | |
| wall panel in sun, midday | 032 (578,604,77,77) | 203 171 134 | 0.596 0.405 0.239 | |
| frieze background (dirt) | 085 (342,946,54,41) | 100 81 64 | 0.126 0.082 0.051 | recesses ≈ 0.55 × plain wall |
| pier lower wall, hazy sun | 062 (617,274,68,68) | 92 79 64 | 0.107 0.078 0.051 | lower zones greyer |
| pink column, overcast | 085 (980,1083,34,150) | 136 85 70 | 0.245 0.091 0.061 | sat 0.49 |
| pink column, overcast | 085 (384,1097,34,137) | 112 76 66 | 0.162 0.072 0.055 | |
| pink column, overcast | 016 (644,205,68,411) | 175 126 124 | 0.430 0.209 0.200 | paler, mauve-grey variant |
| pink column, overcast | 017 (1453,1152,68,109) | 120 76 67 | 0.187 0.073 0.056 | |
| pink column, direct sun | 069 (905,877,54,356) | 197 120 84 | 0.558 0.188 0.089 | |
| pink column, hazy sun | 062 (795,576,41,411) | 196 153 137 | 0.554 0.317 0.250 | |
| pink column, golden hour lit | 054 (521,891,82,342) | 229 148 92 | 0.783 0.297 0.107 | |
| pink column, golden hour shade side | 054 (384,891,54,342) | 139 83 53 | 0.258 0.086 0.036 | |
| inner tan column, shade | 082 (1481,1069,68,205) | 114 95 72 | 0.169 0.114 0.065 | |
| inner tan column, sun | 001 (1618,1508,109,685) | 148 116 80 | 0.297 0.175 0.080 | |
| dome top, overcast | 085 (891,329,164,41) | 209 207 194 | 0.640 0.622 0.541 | |
| dome flank, overcast (streaks) | 017 (990,181,200,40) | 178 172 165 | 0.445 0.415 0.378 | |
| dome moss patch | 017 (640,171,75,40) | 198 201 204 | 0.565 0.585 0.601 | grey-green |
| dome top, sun | 032 (771,128,257,64) | 251 240 229 | 0.967 0.867 0.779 | |
| dome base dark band | 085 (602,476,300,20) | 125 97 65 | 0.207 0.120 0.053 | |
| drum ornament band | 085 (700,560,500,30) | 86 69 51 | 0.094 0.059 0.033 | bronze-brown |
| coffer centre disc, daylight | 083 (960,644,82,82) | 129 113 85 | 0.221 0.164 0.091 | plaster, bounce-lit |
| coffer trapezoid panel | 083 (548,644,109,82) | 98 82 59 | 0.121 0.085 0.043 | |
| podium wall, sun | 063 (1097,960,109,68) | 190 165 131 | 0.513 0.376 0.228 | |
| podium wall, overcast | 016 (274,987,137,109) | 160 145 135 | 0.349 0.282 0.242 | greyer, damp |
| meander band | 016 (480,905,205,34) | 129 113 101 | 0.220 0.166 0.129 | |
| urn, overcast | 016 (411,713,54,82) | 177 153 132 | 0.442 0.319 0.230 | |
| paving (light concrete), sun | 062 (960,1323,274,34) | 208 212 206 | 0.630 0.660 0.619 | neutral |
| asphalt path, overcast | 016 (960,1206,274,27) | 79 77 64 | 0.077 0.074 0.051 | |
| rip-rap / gravel shore | 016 (1371,1241,411,27) | 86 84 71 | 0.094 0.089 0.063 | |
| water, midday, foreground | user (188,801,282,37) | 122 149 165 | 0.195 0.298 0.378 | sky reflection |
| water, hazy day, foreground | 063 (411,1234,411,41) | 121 126 101 | 0.190 0.209 0.130 | green murk |
| water, dark reflection | 063 (1234,1206,274,41) | 76 79 62 | 0.073 0.077 0.048 | |
| shrubs (dark green) | 063 (685,1097,205,68) | 76 84 50 | 0.071 0.089 0.032 | |
| overcast sky | 085 (411,109,411,137) | 214 228 240 | 0.672 0.773 0.872 | reference for the wall samples |

**Recommended base albedos (linear, before weathering; derive from the overcast samples divided by ~0.45 sky fraction and
checked against typical concrete luminance 0.30-0.40).** Attempt 2's values are given for comparison.

| material | base albedo linear (sRGB) | range / variation | attempt 2 | notes for the texture artist |
|---|---|---|---|---|
| MAT_concrete_ochre (walls, piers, entablature, attic, capitals) | **(0.42, 0.29, 0.17)** ≈ sRGB 172 145 113 | luminance ±25 % per cast block; hue drifts from warm ochre (0.50, 0.33, 0.18) on clean upper cornices to grey-tan (0.30, 0.25, 0.19) on the lower 8 m; recess dirt multiplies by 0.55 | (0.72, 0.57, 0.38) — luminance 0.59, **twice too bright**, this is the "clean CAD" look | Exposed poured concrete, no stucco (DPR). Matte (roughness 0.85-0.95), fine sand-grain micro-texture, board/pour lines every ≈ 0.6 m on plain walls (047, 085), tie-hole dots in a grid on the plain wall zones (085 mid, 017), patched repairs as slightly lighter smoother rectangles (0.5-2 m). |
| MAT_column_rose (16 outer columns) | **(0.40, 0.17, 0.12)** ≈ sRGB 170 115 96 | per column ±20 %; vertical streaks of paler mauve-grey (0.42, 0.24, 0.21) where washed, darker russet (0.25, 0.09, 0.06) under the capital; saturation in sRGB ≈ 0.40-0.50 overcast, never above 0.6 | (0.50, 0.24, 0.18) — a little too bright and too orange | "Russet"/"tinted red to mimic Numidian marble" (DPR). Integral pigment, so the colour is in the concrete; weathering desaturates toward grey, flute ridges are paler, flute hollows hold dust. |
| MAT_column_tan_inner (8 inner columns, inner blocks) | (0.45, 0.32, 0.17) | ±15 % | — | Warmer/yellower than the outer walls (001, 082). |
| MAT_dome_membrane | **(0.70, 0.66, 0.58)** ≈ sRGB 220 212 200 | streak zones (0.55, 0.57, 0.57), moss/algae patches (0.50, 0.55, 0.50) on the north/shade flank, dark grime band (0.20, 0.12, 0.05) at the base ring | (0.86, 0.80, 0.66) — too bright and too yellow | Urethane-coated roof membrane: **semi-gloss** (roughness ≈ 0.35, clear coat), so it picks up a soft sky highlight (032, 022). Vertical rain streaks from the apex down, densest on the lower third; meridional seam lines every ≈ 2 m; a metal flashing strip at the base. In warm low sun it reads cream-peach (user image, 169). |
| MAT_drum_band | (0.28, 0.18, 0.10) | dirt in the scale pattern → 0.15 | — | Bronze-brown, much darker than the walls (085, 017). |
| MAT_plaster_ceiling | (0.50, 0.40, 0.25) | coffers darker (0.35, 0.28, 0.17), ribs lighter | — | Casting plaster, matte; only bounce-lit, so keep it lighter than it looks. |
| MAT_concrete_podium (podium, planter walls, pedestals) | (0.36, 0.30, 0.22) | greyer and damper toward the water; algae band (0.10, 0.14, 0.08) in the bottom 0.5 m at the water | — | Rusticated joints; green algae/black tide band at the waterline (093, 091, 022); efflorescence streaks below the band. |
| MAT_concrete_colonnade | (0.44, 0.31, 0.17) | strong black-green streaking on the shade side of shafts (128, 138) | — | Same concrete as the rotunda; the colonnade shafts show the strongest vertical grime streaks in the corpus. |
| MAT_paving | concrete (0.45, 0.45, 0.42); asphalt (0.08, 0.08, 0.06); gravel (0.30, 0.28, 0.22) | | | Paths around the lagoon are asphalt with concrete kerbs; inside the colonnade decomposed granite/gravel (165). |
| MAT_water_lagoon | volume absorption colour ≈ (0.04, 0.07, 0.04), depth 1.5 m to a muddy bottom (0.12, 0.10, 0.06) | | mirror | Green-tea murk; reflections dominate at grazing angles (correct Fresnel), broken into 0.3-1 m streaks by 2-5 cm ripples (user image, 169); ducks' wakes; scum lines near the shore. At golden hour the water is glassy with long warm reflections (169). |
| MAT_lawn / shrubs / rip-rap | lawn (0.12, 0.20, 0.05); shrubs (0.06, 0.09, 0.03); rip-rap boulders (0.30, 0.28, 0.22) | | | Rip-rap is angular grey-brown stone 0.3-0.8 m (187, 063). |

Weathering map (where and what — every one visible in the cited photos):
- Rain streaks: start at every projecting cornice edge (attic base cornice, entablature corona, box rims) and run 1-3 m
  down as darker grey-green vertical stripes 0.1-0.3 m wide; strongest under the attic cornice and on the colonnade
  shafts (128, 138, 085).
- Recess dirt: frieze rinceau, capital leaves, coffers and the Greek-key bands read 40-50 % darker than adjacent plain
  surfaces (085, 054, 047).
- Dome: rain streaks over the whole lower third; moss patches on the north flank (017); the base ring almost black-brown.
- Podium at the water: dark algae/tide band, then a pale efflorescence zone (093, 091).
- Patches: lighter rectangles from the 2009-2011 concrete repair, mostly on lower walls and pedestals (016, 062).
- Edge wear: softened arrises on all precast ornament; small spalls with exposed aggregate on urn rims and plinth corners.
- Bird droppings: white streaks on cornices and urn lids near the water (022 shows hundreds of gulls on the shore).
- Rust: occasional orange bleed below embedded fixings on the attic panels (085 right panel).

Crops for materials: `reference/photos/material_crops/` (rotunda_wall_1-2, pink_column_1-2, dome_1-3, rostra_wall_1).

---

## 6. Vegetation and surroundings

Documented: "willows and acacias choked its portals" was Maybeck's theme (DPR); "The mature Monterey cypress trees at the
northeastern corner of the site date to the time of the Harbor View Inn" (DPR); "The east wall of the [exhibition] building
is screened by redwood trees planted in 1968"; "lagoon ... Australian eucalyptus trees ... encircled by cypress trees"
(web summaries); "small wooded island at its north end provides refuge for egrets, herons, and other waterfowl" (DPR).

From the photos, for the hero view (camera east, looking west):

| where (world coords, estimate) | what | height | refs |
|---|---|---|---|
| right of the rotunda (north-east of it), on the peninsula/north shore, X −20…−40, Y 10…30 | dense dark cluster: 2-3 Monterey pine / Monterey cypress, wind-shaped, plus a young coast redwood directly in front of the north arch | 20-28 m; redwood 15-18 | user image (right), 022 (centre), 070 (in front of the arch), 062 |
| left of the rotunda (south-east), X +25…+45, Y 15…35 | 2 Monterey cypress columns + a broad eucalyptus behind the south wing | cypress 22-25, eucalyptus 30 | user image (left of the rotunda), 169 (left) |
| north shore near the islet, X −60…−110, Y 40…80 | weeping willows at the water's edge, big eucalyptus behind | willow 8-12, eucalyptus 25-35 | 144, 145, 171, 176, 086 |
| east and south shore (behind the hero camera) | blue-gum eucalyptus rows, Monterey cypress at the NE corner | 25-35 | 141, 169 right, 105 |
| behind the colonnades | coast redwood screen (1968) and cypresses between colonnade and hall | 25-35 | 187 background, 128, 138, 062 |
| peninsula ground | low mounded shrubs (Mahonia 147, agapanthus, pittosporum), ferns (178), lawn, rip-rap edge | 0.5-2 | user image, 063, 062, 022 |
| inside the colonnade | gravel, a few small trees/palms (Cordyline/phoenix in 128), shrubs | 3-6 | 128, 165, 132 |

Behind the colonnade from the hero camera: the exhibition hall's buff stucco crescent wall and roof (≈ 20 m) is visible
above/through the columns at the far left and right (user image left, 022 left); the Presidio's forested ridge is
higher than the hall and shows as a dark green band above the north wing on clear days (150 from the Marina Green shows
it); Marina district houses are east/behind the camera and appear only in views looking east (150, 126). Golden Gate
Bridge towers are visible only from the bay side (137, 166).

Birds/animals in the photos: western gulls in hundreds on the peninsula shore and water (user image, 022, 065); two mute
swans (109, 155); black-crowned night herons nesting on the islet (114-122, 143); ducks and coots; turtles sun on the
rip-rap (mentioned by photographers, not visible at hero distance). For the hero render: gulls on the water and shoreline
(the user image has ≈ 40), optionally two swans.

---

## 7. Golden-hour lighting reference

Photos in the corpus at low sun:

| ref | when | sun (est.) | what to learn |
|---|---|---|---|
| **169** `main_Palace_of_Fine_Arts_16794p.jpg` | 2020-02-01 morning, "Morning golden hour" | az ≈ 115°, el ≈ 7° (from the ESE, over the camera's left shoulder) | **Our target light.** East faces lit warm orange-peach; shadows soft-edged but clearly directional; the arch interior and the south faces in cool blue-grey shade lifted by sky; sky a clean gradient from pale warm haze at the horizon to saturated blue at 30°; water glassy, reflections long and only slightly broken, warm building reflection over a blue-sky reflection; trees front-lit, slightly hazy. Wide stitched panorama, ≈ 24 mm equiv. from the east shore. |
| 167, 168 | same morning | same | Pylons and boxes lit from the east; maidens silhouette against the sky. |
| 043-060 series (`Palace_of_Fine_Arts_10…33`) | clear evening/morning, low sun | el ≈ 10-15°; sunlit faces are the east/south-east ones → morning | Best close-ups of ornament in raking warm light: deep shadows in the capitals, saturated deep-blue sky, columns reading russet-orange, walls pale gold. Note the shade side of a column drops to ≈ 0.09 linear while the lit side reaches 0.78 (054). |
| 100 `25_Wallpaper` | late afternoon | low from the west | Sun through the colonnade, flare. |
| 035 | sunset with light beams | from the WNW behind the rotunda | The evening alternate: rotunda backlit, silhouette, beams through the arch. |
| 036, 195, 197, 198 | dusk/blue hour | below horizon | Sky gradient and floodlit building; water very still. |
| 097, 092 | evening haze from Crissy Field / Presidio | low west | Aerial perspective: the dome goes pink-grey in haze. |
| 141, 085, 017, 016 | overcast | none | Albedo references (section 5). |

Chosen light (decisions.md): morning sun from the east-south-east. NOAA solar position (Meeus-based, refraction included)
computed in Python for the rotunda (37.8029, −122.4484), standard time PDT until 2026-11-01, PST after:

| date (2026) | local time | elevation | azimuth | in range 5-8° / 110-125° |
|---|---|---|---|---|
| Oct 31 (PDT) | 08:15 | 6.8° | 113.9° | yes |
| Nov 2 (PST) | 07:15 | 6.4° | 114.3° | yes |
| **Nov 10 (PST)** | **07:30** | **7.4°** | **118.5°** | **yes — recommended** |
| Nov 20 (PST) | 07:30 / 07:45 | 5.4° / 7.8° | 120.1° / 122.5° | yes |
| Dec 1 (PST) | 07:45 | 5.8° | 123.4° | yes |
| Oct 20 (PDT) | 08:00 | 6.3° | 108.4° | azimuth slightly low |

Recommendation: **2026-11-10 07:30 PST → sun elevation 7.4°, azimuth 118.5°** (matches ref 169 within a few degrees).
Sun angular diameter 0.53°; use `sun_rotation` = azimuth in `ShaderNodeTexSky` (MULTIPLE_SCATTERING) and
`common.aim_sun(118.5, 7.4)`. Evening alternate (for the delivery variant): 2026-10-20 17:45 PDT → el 6.9°, az 250.9°.

---

## 8. Six canonical QA viewpoints

Files copied to `reference/photos/canonical/`. Camera estimates use a 36 mm-wide sensor; positions in world metres.

| cam | file | source | camera (X, Y, z) | look-at | lens | sun in the photo | how estimated |
|---|---|---|---|---|---|---|---|
| 01 lagoon hero | `cam_01_lagoon_hero.png` (+ `cam_01b_lagoon_hero_goldenhour_ref169.jpg`) | user image; ref 169 is the real-photo twin | (−16.0, 113.9, 1.0) | (0, 0, 17) | 31 mm (attic spans 450/1320 px at ≈ 115 m) | user: high SSE midday; 169: az 115°, el 7° | on the lagoon-face normal (az 82°), on the east shore (OSM shore at 96-121 m). The user image keeps verticals parallel with the horizon at 68 % height → use shift_y ≈ +0.17 with a level camera instead of tilting. |
| 02 NE shore three-quarter | `cam_02_ne_shore_threequarter.jpg` | ref 062 (2018-05-21, "View of Rotunda from north-east") | (−32, 38, 1.3) | (0, 0, 20) | 26 mm | SSE, el ≈ 55° (late morning) | attic width 1350/1920 px → D ≈ 50 m at az 50° |
| 03 colonnade walk | `cam_03_colonnade_walk.jpg` | ref 128 (2007-07-30, inside the south colonnade toward the rotunda) | (58, −4, 1.7) | (0, 0, 16) | 20 mm (photo is a portrait crop) | afternoon, from the WSW behind the colonnade | on the south-wing arc (r ≈ 85 about (0, 52)), rotunda ≈ 58 m away fills the gap between two columns |
| 04 rotunda ceiling | `cam_04_rotunda_ceiling.jpg` | ref 083 (2017-10-07) | (0, 3, 1.6) | (0, 3, 40) | 15 mm | midday, ceiling in shade | straight up, all eight inner arches and the eight winged figures in frame |
| 05 south lawn / SE ground level | `cam_05_south_lawn.jpg` | ref 063 (2018-05-21, "from south-east") | (35, 42, 1.4) | (0, 0, 18) | 24 mm | S-SW, el ≈ 60° (early afternoon, hazy) | podium, urns and stair visible; rotunda fills the frame at ≈ 55 m, az 130° |
| 06 aerial | `cam_06_aerial.jpg` | ref 105 (2016-05-28 helicopter over the Marina) | photo: ≈ (−570, 400, 250); **QA camera: (−205, 143, 120)** | (0, 0, 15) | photo ≈ 60 mm; QA 50 mm | afternoon, hazy, from the WSW | the only aerial in the corpus is distant; the QA camera keeps its bearing (az 35°, from the NNE over the water) at a third of the distance so both colonnade arcs, the lagoon outline and the islet are in frame. Not a photo match — compare silhouette and layout only. |

Proposed replacement for `scripts/qa_cameras.py` (lead to apply; `shift_y` is optional — apply as `cam_data.shift_y`):

```python
CAMERAS = [
    dict(name="CAM_qa_01_lagoon_hero", loc=(-16.0, 113.9, 1.0), target=(0.0, 0.0, 17.0), lens=31.0, shift_y=0.17,
         ref="canonical/cam_01_lagoon_hero.png",
         note="THE hero. On the lagoon-face normal (az 82 deg), east shore ~115 m, eye level; real-photo twin ref 169 (golden hour)."),
    dict(name="CAM_qa_02_lagoon_ne_threequarter", loc=(-32.0, 38.0, 1.3), target=(0.0, 0.0, 20.0), lens=26.0,
         ref="canonical/cam_02_ne_shore_threequarter.jpg",
         note="Ref 062: north-east shore, 50 m, 3/4 view; south colonnade visible behind the rotunda on the left."),
    dict(name="CAM_qa_03_colonnade_walk", loc=(58.0, -4.0, 1.7), target=(0.0, 0.0, 16.0), lens=20.0,
         ref="canonical/cam_03_colonnade_walk.jpg",
         note="Ref 128: inside the south colonnade looking north-west at the rotunda between two fluted columns."),
    dict(name="CAM_qa_04_rotunda_ceiling", loc=(0.0, 3.0, 1.6), target=(0.0, 3.0, 40.0), lens=15.0,
         ref="canonical/cam_04_rotunda_ceiling.jpg",
         note="Ref 083: straight up; eight inner arches, eight winged figures, star coffering."),
    dict(name="CAM_qa_05_south_lawn", loc=(35.0, 42.0, 1.4), target=(0.0, 0.0, 18.0), lens=24.0,
         ref="canonical/cam_05_south_lawn.jpg",
         note="Ref 063: south-east, ground level across the water's edge; podium, urns, stair, pier groups."),
    dict(name="CAM_qa_06_aerial", loc=(-205.0, 143.0, 120.0), target=(0.0, 0.0, 15.0), lens=50.0,
         ref="canonical/cam_06_aerial.jpg",
         note="Ref 105 bearing (NNE over the lagoon) at a third of its distance: silhouette, dome, both wings, lagoon outline, islet."),
]
```

---

## 9. Photo index by subject

| subject | best refs (in order) |
|---|---|
| whole rotunda, frontal, proportions | 085 (telephoto, overcast), 022, 070, 009, 071, 141 |
| dome and drum | 032, 085, 017, 022, 092, 097; SAT |
| attic panels (Zimm) | 017, 085, 069, 032, 044, 053, 060, 058 |
| attic corner figures | 054, 055, 056, 032, 017, 085 |
| capitals, entablature mouldings | 002, 054, 049, 047, 044, 045, 050, flickr_1-5 (refs 210-214) |
| column bases, pedestals, podium urns | 113, 129, 088, 016, 031, 028, 030, 077, 063, 062 |
| rostra / podium walls, stairs | 007, 016, 031, 021, 063, 062, 161 |
| inner columns, winged figures, vaults | 082, 083, 010, 077, 001, 107, 125, 185, 047, 088 |
| coffered ceiling | 083, 003, 019, 075, 073, 094, 040 |
| colonnade (exterior) | 187, 022, 174-177, user image, 169 |
| colonnade (inside, capitals, beams) | 128, 138, 165, 132, 181, 183, 142 |
| weeping maidens and boxes | 163 (close, night), 187, 185, 136 (garland panel), 167, 168, 172 |
| water, reflections, shoreline | 169, user image, 144, 145, 022, 093, 091, 065, 063 |
| trees and lawn | 144, 145, 171, 176, 086, 126, 062, 063, 141, 105 |
| golden hour / low sun | 169, 167, 168, 043-060, 100, 035 (evening), 097 |
| overcast (albedo) | 085, 017, 016, 141, 187 |
| night / floodlit | 189-199, 005, 037, 038 |
| site / aerial | 105, 102-104 (1980 aerials), 092, 097, 137; `reference/plans/*` |
| 1915 original (history only) | 042, 111, 112, 123, 124, 134, 200-209 |

---

## Derived texture assets and their source licences (added by MAT round 9)

`assets/textures/projection/PFA_photo_ratio.png` and `PFA_photo_mask.png` are DERIVED from **ref 169**
(`reference/photos/raw/ref_169_main_Palace_of_Fine_Arts_16794p.jpg`, Wikimedia Commons,
<https://commons.wikimedia.org/wiki/File:Palace%20of%20Fine%20Arts%20%2816794p%29.jpg>, "Palace of Fine Arts
(16794p)", 18-frame morning-golden-hour panorama, 10074x6252, dated 2020-02-01; index row 169 of
`reference/photos/index_wikimedia.csv`). They are not the photograph: the ratio map is the photograph divided,
pixel by pixel, by a render of this build from the same station, then reduced to a mean-1 reflectance correction
by `scripts/mat_projection.py`, so the photograph's own light, exposure and detail below 0.22 m are removed and
what remains is a derived weathering/photometry field. Attribution and share-alike terms of the Commons file
apply to anything published from these two maps and to any render that uses them; keep this line with the
delivery notes. The other texture sets in `assets/textures/` are CC0 (Poly Haven, ambientCG) and carry no
attribution requirement.

## Disagreements with attempt 2 (summary for the lead)

1. Dome: 36 m Ø × 11.5 m rise → **33 m Ø × 7.6 m rise** (cap of a 21.7 m sphere). This was the single biggest error.
2. Drum: 2.0 → **3.5 m**; attic: 6.1 → **7.1 m** (attempt 2's attic was too short, not too tall).
3. Rotunda plan: arch-wall/attic apothem 19.8/18.8 → **21.5**; column axes at circumradius 22.6 → **23.9**; pair spacing
   3.5 → **4.5 m**.
4. Podium: the columns' pedestals stand on a 4.3 m podium; column base at z 7.5 (attempt 2: 4.6). Total height above
   water 50.7 (attempt 2: 49.2).
5. Colonnade columns ≈ 14 m to the abacus, entablature top ≈ 16.4 m (attempt 2: 19.4 / 22); column Ø 1.7 (2.0);
   boxes 3.0 tall (5.0); 13 boxes with 52 maidens of 4.3-4.6 m (attempt 2: 3.0 m).
6. Attic corner figures 6.7 m (attempt 2: 3.8); inner winged figures 4.6 m (2.5).
7. Materials: STONE_TAN/STONE_LIGHT/DOME_CREAM luminance roughly halved; columns slightly darker and greyer.
8. Colonnade arcs are not r ≈ 38 m circles; use the OSM polygons (arcs of r ≈ 85-110 about a centre ≈ 52 m east).
9. Hero camera moves from (6, 118) to (−16, 114) (onto the face normal) with a 31 mm lens.

## Could not determine

- Exact inner-order dimensions (inner column height, vault depth, ceiling rise) — attempt 2 values kept, unverified.
- Exact positions of the 13 planter boxes along the arcs (count them on the OSM wing polygons / ref 187 when modelling).
- Lagoon depth (restoration reports say "shallow", dredged 2009-2011; no number found; use 1.0-1.5 m).
- Whether the user target image is a photo: its dome/drum/attic proportions do not match any real photo — treat as art.
- The Zimm panel design order around the eight faces (three designs; the sequence is inferred).
- HABS measured drawings: LoC has HABS CA-1909 photographs only, as far as could be found online.
