# Phase 8d PART 1 — backdrop build report (env builder, 2026-09-19, branch `phase8d-env`)

Scope built: R1 (the MAT_backdrop_* rework) and R2 (the hall's tree belt). R3 deferred as decided.
Files touched: `scripts/mat_build.py` (MAT_backdrop_* block only), `scripts/env_backdrop.py`, `scripts/env_city.py`,
and the two assets they rebuild (`assets/materials.blend`, `assets/environment.blend`). `export/` untouched, master not rebuilt.

## 1. Materials — verified by a node-graph diff, not by eye
`/tmp/matdiff.py` hashes every material's node graph (node kinds + unlinked input values + link topology) in the
pre-change `materials.blend` (from git) and the rebuilt one:

```
added:     ['MAT_backdrop_lawn']
removed:   []
changed:   ['MAT_backdrop_asphalt', 'MAT_backdrop_building', 'MAT_backdrop_forest',
            'MAT_backdrop_hill', 'MAT_backdrop_roof', 'MAT_backdrop_roof_tile', 'MAT_backdrop_skylight']
unchanged: 34
```
No MAT_ outside the backdrop block moved. What changed in each:

| material | change |
|---|---|
| `MAT_backdrop_building` | albedo C(0.568, 0.545, 0.120) (saturation **0.79**) → C(0.452, 0.424, 0.318) (**0.30**); grey drift colour to match. Then lot spread ±19 % at 13 m + block drift at 90 m, the palace shadow, and distance haze. |
| `MAT_backdrop_skylight` | the hero's "dark rectangles": albedo ×2.4 (C(0.072,0.080,0.092)→C(0.196,0.202,0.208)), roughness 0.14→0.46, specular 0.75→0.28, coat off. |
| `MAT_backdrop_roof` / `_roof_tile` | lot spread (22 % / 20 %) + haze; roof also takes the palace shadow. |
| `MAT_backdrop_forest` | albedo ×1.55 and the gap-shadow depth 0.66→0.55 (round 5 took it down 45 % against a bright yellow canopy; with the haze doing that job the only thing left was turning the un-hazed masses — the new belt at 150 m — into black holes), + haze from 210 m. |
| `MAT_backdrop_hill` / `_asphalt` | haze only (hills 900–2600 m, asphalt from 200 m). |
| `MAT_backdrop_lawn` | **new.** The far-field ground (23.2 km² at 0.18 texels/m). It exists so the palace's own `MAT_lawn` — the turf the hero stands on — does not move, and because Gate 1 groups a multi-material backdrop mesh by **slot 0 alone**, so in the viewer this one material is also what the far roads, gravel and soil read as (Cycles still shades each face with its own). |

All three new terms are fixed functions of world position, so the Gate 2 DIFFUSE-colour bake reproduces them exactly
and the end-of-Phase-8 Cycles hero sees them too. The three mechanisms they answer (measured in `phase8d_analysis.md`):
0.79 texels/m makes anything finer than 1.3 m unbakeable; the Gate 1 merge of 640 objects makes Object Info → Random
constant so every per-object term collapses; and `sunLight.castShadow = false` + no backdrop lightmap means the hall is
drawn fully sunlit unless the shade is in the albedo.

## 2. Geometry — the tree belt, and the export pin
`ENV_backdrop_hall_belt_0..3`: **89 crowns, 6 900 triangles** against the **6 986** cap, one closest-packed row
(2.8 m spacing, offset alternating 5.4 / 9.2 m ± 1.1 m from the hall's concave east face, crowns 12.5–19.5 m tall),
each tested against the hall footprint and the colonnade roof polygons; 3 sample points rejected. They carry
`MAT_backdrop_forest`, so they join the existing `backdrop_forest` export group — **no new group**.

Per-group triangles in `assets/environment.blend`, before → after (same inventory rule Gate 1 groups by, slot-0 material):

| group | before | after |
|---|---|---|
| `backdrop_forest` | 99 640 (6 obj) | **106 540 (10 obj)** |
| `lawn` → `backdrop_lawn` | 5 882 (MAT_lawn) | 5 882 (MAT_backdrop_lawn) |
| building / roof / roof_tile / skylight / hill / door / bird / lamp | 33 696 / 5 927 / 1 380 / 1 236 / 880 / 12 / 2 268 / 816 | unchanged |
| backdrop total | 151 739 | **158 639 (+6 900)** |

ENV objects 5 925 → 5 929. **+6 900 ≤ 6 986**, so `tree_allow` still leaves the same 20 near trees fitting and no
21st (cheapest candidate 12 892), i.e. **near 20 / far 127 stay byte-identical with `CLASS_BUDGET["ENV"]` at 902 000**
and no impostor re-bake. The `lawn` group is renamed `backdrop_lawn` (same 3 objects, same 5 882 tris, so
`env_so_far` does not move) — the export will see a renamed group mesh and Gate 2 bake job, not a new one.

## 3. Previews (Eevee, 1280x720, `env_preview` harness, cams 01/05/06)
`renders/qa_comparisons/phase8d_env_before_after_960.jpg` — before | after, three stations plus two 100 % crops.
Caveat on the numbers: this harness is AgX **Base** Contrast at −0.8 EV with a placeholder sun, not the delivery look,
so only the before→after direction transfers, not the absolute values.

| box | luma | saturation | luma sd |
|---|---|---|---|
| hero, N-colonnade band | 0.303 → 0.269 | 0.457 → 0.452 | 0.159 → **0.177** |
| hero, S-colonnade band | 0.324 → 0.297 | 0.545 → 0.532 | 0.172 → 0.171 |
| cam05 backdrop band | 0.440 → 0.419 | 0.551 → 0.543 | 0.188 → **0.202** |
| cam06 backdrop city | 0.298 → 0.303 | 0.282 → **0.137** | 0.083 → 0.079 |
| cam06 far field | 0.203 → 0.206 | 0.308 → **0.264** | 0.123 → 0.105 |

The 100 % crops are the real result: at the hero every intercolumniation that held a pale olive wall with dark glazed
panels now holds a dark, varied tree mass with light through the gaps, which is what ref 169 shows there; at cam06 the
saturated green-olive city slabs are pale hazed grey.

**Two honest limits.** (a) Saturation is the defect that moved (cam06 −51 %); luminance did not, because the albedo
came down as the haze went up. ref 105's 0.82 luma / 0.073 saturation is 1–3 km of air, while our cam06 band is
200–700 m, so matching it exactly would be wrong physics — and real aerial perspective is light *added* to the view,
which an albedo (max 1.0) cannot reach and the albedo bake would not carry anyway. (b) The hero band is now slightly
darker than ref 169's belt; its variance moved the right way, and the rest is lighting's, not the backdrop's.
