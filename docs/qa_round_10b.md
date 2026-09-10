# QA round 10b — hero tile re-check after the two blockers (2026-09-10). Tile review **PASS**; hero **3.56 -> 3.61 (+0.05)**.

Scored master: the file on disk after the lead's rebuild, **9691 objects**. Merged since round 10: the gull removal in
`env_build.py` (b058e45), **LIGHT r18** (VAULT_FILL bay weights) and the lead's **shade-fill-off** (f40d0e7,
`LIGHT_shade_fill` energy 49 -> 0). Hero only, per the brief: Cycles cam01 plus a defect pass on the Eevee cam01/02/03.
No other Blender ran during any render; every run was one blocking `scripts/blender_run.sh` call and exited on its own.

| file | what |
|---|---|
| `renders/final/v2/qa_round10b_cam01_cycles.png` | Cycles 1920x1080, 128 spp, OIDN, GPU: **376.1 s** (r10 384.5). Also `renders/previews/qa/round10b_01_lagoon_hero_cycles.png`. |
| `renders/previews/qa/round10b_0{1,2,3}_*.png` | Eevee 1280x720, 32 TAA, LOD1; three-camera pass **75.3 s**. |
| `renders/final/v2/round10b_cam01_aligned_vs_ref169.png` | `qa_silhouette.py align`, crop 690 40 1235 520 / ref-crop 749 127 1165 493 |
| **`renders/final/v2/round10b_gate.png`** | **the gate composite**: hero vs ref 169, the arch 1:1 pair, the re-stated tile list, the boxes, the score, the verdict |
| `renders/final/v2/round10b_RENDERS_DONE` | touched after the last render exited |

Commands: `scripts/blender_run.sh 400 -- --background master.blend --python scripts/qa_name_sweep.py`;
`... 600 -- ... scripts/qa_r10_rays.py`;
`... 1500 -- --background --python scripts/qa_render_round.py -- --round 10b --final --cams 01 --samples 128 --res 1920 1080`;
`... 600 -- ... --round 10b --eevee --cams 01 02 03`. Analysis, no Blender: `qa_hero_tiles.py`, `qa_silhouette.py align`,
`qa_r07_measure.py box`, `qa_r10b_gate.py`. Nothing was written to master.blend.

---

## Item 1 — name sweep

`scripts/qa_name_sweep.py`: **520 exempt, 0 hits, exit 0. PASS.** The round-10 hit is gone: `LIGHT_shade_fill_00` was
removed from the rig with the lead's shade-fill-off, so the exception recorded in `docs/quality_checklist.md` is now
moot (kept on record for the history). The 520 exempt are the `ARCH_rotunda_inner_block_*` piers and the
`ENV_backdrop_fill*` city blocks already on record.

## Item 2 — ray-cast opening test (`scripts/qa_r10_rays.py`)

**14 / 14 PASS**, unchanged from round 10 and re-run on the rebuilt master:

* cam01 / bay 00 — z 16 clear to sky; z 17-21 first hit on the *far* side of the rotunda (`inner_wall_04`,
  `ceiling_ribs`, `ceiling_field`) at apothem -9.6 to -15.4, 113-118 m out; z 22 the near soffit
  `ARCH_rotunda_vault_coffers_00` at r **4.9** against a local soffit radius of 4.98.
* cam02 / bay 07 — z 16-21 through to the ceiling ribs / rosettes / inner wall at apothem -1.8 to -8.1; z 22
  `ARCH_rotunda_vault_coffers_07` at r **5.0**.

Not one ray hits a face of the near vault, rib plate or archivolt inside the opening.

## Item 3 — the round-10 tile list, re-stated at 100 %

Six tiles of the Cycles hero (3 x 2, 640 x 540) viewed one by one, plus 100 % crops of cam02's shaded face / soffit and
cam03's near column. **Two blockers closed, sixteen carried, one new major.**

| # | status | what the tile shows now |
|---|---|---|
| QA-10-1 | **FIXED** | No waterfowl on the open water in front of the camera. The nearest gull is a shore bird ~100 m out, a few px wide. `env_build.py` b058e45 removed the floating set; shore + flying gulls stay. |
| QA-10-2 | **FIXED** | Vault field `900 380 1010 430` = **60.6 lum** (window 45-65, ref 44.9; was 103.1 = 2.30x). Jamb `872 400 892 480` = **hue 25.0, R-B +36.2** (window 25-60 + positive; was hue 338.5, R-B negative). No magenta anywhere in the reveal. |
| QA-10-3 | OPEN | Still no archivolt — a plain band where the photograph has a moulded archivolt, keystone and bead course, and plain blocks where it has engaged springing capitals. Arch-ring std **55.5 vs ref 64.2 (0.86x**, was 0.64x), col-sd **30.3 vs 47.9 (0.63x**, was 0.49x): the vault now shades, the moulding is still absent. Owner ornament. |
| QA-10-4 | OPEN | The barrel reads concave and shaded at last, but the coffers are soft round holes with no hard shadow line and no rosette; several on the right haunch read as melted blobs. Owner architecture. |
| QA-10-5 | OPEN | The two side-bay soffits are still flat plates showing punched circles, no coffer relief. Owner architecture. |
| QA-10-6 | **FIXED** | No white posts in the water on any of the three lower tiles. |
| QA-10-7 | OPEN / worse | Shafts are still hard vertical stripes with no cylindrical falloff, and the columns box sat is **0.712 vs the photograph's 0.566** — up from 0.694 in round 10. Owner materials. |
| QA-10-8 | OPEN | Dome cap untextured near-white lid, col-sd 5.3, 187.6 vs ref 224.3 (0.84x). Unchanged. Owner materials. |
| QA-10-9 | changed | The colonnade back wall is no longer indigo (warm dark brown now) but is still a flat untextured panel. |
| QA-10-10 | OPEN | Shoreline planting: hard leaf cards, smooth shrub blobs, the orange mulch pile still at 1755 655. |
| QA-10-11 | OPEN | Sky cloudless and structureless; sky_top **167.9 vs ref 202.8 = 0.83x**, sat 0.433 vs 0.332. |
| QA-10-12 | **partly** | cam02's piers and entablature are warm at last (pier hue **44.9**, NE face hue **42.9**; both were violet) — but a shaded shaft cluster at `690 230 720 320` is **still magenta: hue 335.5, sat 0.182**. The blue fill was not the only source. Owner lighting. |
| QA-10-13 | OPEN | cam02's arch soffit is still a bright rim over a dark coffer field: reads as gold-on-dark paint, not shaded concrete. |
| QA-10-14 | OPEN | cam02: `ENV_backdrop_hall_*` stepped untextured boxes in the mid-ground (box 93.9 lum, std 71.5). |
| QA-10-15 | OPEN | cam02: the lower half is still near-black (60.1 lum); leaf cards read as separate hard cut-outs. |
| QA-10-16 | OPEN | cam03: the paving is still a chequer, cold and flat (hue 71.5, sat 0.331, no grout depth, no wear). |
| QA-10-17 | **worse** | cam03: the near column is now a near-black olive slab — **17.7 lum = 0.192 of the sunlit rotunda** against the photograph's 0.292 and LIGHT r17's own measured 0.305. The outer row fell **0.289 -> 0.176** (floor 0.15). The shade-fill-off took cam03's ambient with it. Owner lighting. |
| QA-10-18 | OPEN | cam03: foreground foliage is a black spiky silhouette with no leaf mass. |

**New this round**

* **QA-10b-1 — frame chroma, major, owners lighting + materials.** The whole frame is more saturated than the
  photograph and it moved this round: whole building `700 160 1240 480` sat **0.571 (r09) -> 0.636** against ref 169's
  **0.521 = 1.22x** (round 09 was 1.10x, already logged as QA-09-1); shaded attic **hue 41.2 / sat 0.628** vs ref
  **30.6 / 0.454**; entablature sat 0.777 vs 0.588; shore band 0.821; columns 1.26x. At 100 % the shaded stone reads
  **mustard-olive** where the photograph is a warm neutral grey-tan. This is the price of the shade-fill-off. It is
  **not a blocker** — the lead pre-accepted the shaded-attic windows — but it is the single cheap lever left on the hero
  (a low-energy neutral shade fill, or a saturation pull on the shade side of the concrete).
* **QA-10b-2 — entablature level, minor, owner lighting.** `900 262 1020 296` **120.2 vs ref 145.5 = 0.83x**, down from
  0.91x: the VAULT_FILL bay weights darkened it, exactly as LIGHT r18 predicted (132.9 -> 120.9; measured 120.2).

## Item 3b — the acceptance boxes and the moved holds

Render | ref 169 (aligned panel) | window.

| box | render 10b | ref 169 | window | verdict |
|---|---|---|---|---|
| **vault field** 900 380 1010 430 | **60.6** lum | 44.9 | 45-65 | **PASS** (was 103.1 = 2.30x) |
| **jamb** 872 400 892 480 | **hue 25.0, R-B +36.2**, lum 54.9 | 22.2, +58.9, 95.7 | hue 25-60, R-B > 0 | **PASS** (was hue 338.5) |
| shaded attic 1110 225 1150 260 | 122.1 / 41.2 / 0.628 | 120.5 / 30.6 / 0.454 | lum 103.5-126.5, hue 23.5-35.5, sat <= 0.50 | lum PASS, **hue FAIL, sat FAIL** — the lead's accepted trade, and sat is worse than the 0.53 he was told to expect |
| sunlit attic 900 222 1020 256 | 187.7 / sat 0.518 / R-B +117.7 | 189.8 / 0.582 / +134.2 | lum 178-201, sat 0.53-0.62 | lum PASS, sat marginal FAIL — but 0.487 -> 0.518 moved **toward** the photograph |
| sky top 1210 22 1690 76 | 167.9 | 202.8 | carried | 0.83x, unchanged |
| water reflection 900 760 1020 840 | 128.6 / 44.2 / 0.250 / +34.4 | 165.5 / 33.7 / 0.358 / +68.7 | lum >= 124 | lum PASS (0.78x), sat + R-B still FAIL; flat vs r10 (131.5 / 0.227 / +31.9) |
| entablature 900 262 1020 296 | 120.2 | 145.5 | — | 0.83x, **down** from 0.91x (QA-10b-2) |
| columns 680 280 1240 470 | 114.3 / 39.1 / 0.712 | 124.0 / 32.7 / 0.566 | sat <= ref | sat 1.26x, **worse** than r10's 0.694 |
| cam02 pier 600 110 660 200 | 70.3 / **hue 44.9** / sat 0.549 | — | hue 25-60, sat <= 0.35 | hue **PASS** (the violet is off the pier), sat FAIL |
| cam02 soffit_l / _r 735-830 x 275-360 | hue 41.4 / 42.2, sat 0.424 / 0.488 | — | r18 held 36 / 34 at sat 0.34 / 0.33 | both drifted warmer and more saturated with the fill off |
| cam03 near column / outer row | 0.192 / 0.176 of the sunlit rotunda | 0.292 (ref 128) | >= 0.15 | near column **FAIL** (r17 had 0.305), outer row barely clears |

## Item 4 — the score

Alignment came back **bit-identical for the fifth round** (scale 1.3108, dx -291.8, dy -126.6, apex delta 0.44 %H), so
the round-07..09 boxes are used unshifted.

| row | r10 | **r10b** | why |
|---|---|---|---|
| Silhouette match | 4 | **4** | transform bit-identical, apex delta 0.44 %H |
| Proportion | 4.5 | **4.5** | ray test 14/14 again; the opening is real and unchanged |
| Ornament fidelity | 3.5 | **3.5** | arch-ring structure 0.64x -> 0.86x (the vault shades now) but still no archivolt, keystone or rosette |
| Material realism | 3.5 | **3** | frame chroma moved away from the photograph: whole building 1.10x -> **1.22x** ref sat, columns 1.26x, the shade reads mustard |
| Edge wear | 3.5 | **3.5** | attic std 29.5, aniso 5.15 — unchanged within noise |
| Lighting mood | 4 | **4.5** | both acceptance boxes land: the frame's deepest shade is 60.6 against the photograph's 44.9, and the reveal is warm |
| Water reflection | 3 | **3** | 128.6 lum still clears the 124 floor but sat 0.250 vs 0.358 and R-B +34.4 vs +68.7 still fail |
| Repetition visibility | 3 | **3** | unchanged |
| Scale cues | 3 | **3.5** | the two-icosphere gulls are gone; no placeholder-grade object remains in the frame |
| **average** | **3.56** | **3.61** | **+0.05** (round 09 was 3.67, so **-0.06** against it) |

The lighting gain and the material loss are the two halves of the same lamp: the lead traded frame-wide chroma for the
arch reading correctly at 100 %, and on the hero that trade is worth +0.05 net. The definition-of-done clock is
unchanged — the hero is not at 4.0, and the two-round flat rule was already spent before this re-check.

## Does the arch read as the photograph's?

**Yes structurally, and now tonally; no as a piece of architecture.** The 1:1 pair in the composite: near arch ->
concave shaded coffered barrel -> far arch -> sky, in the right order, at the right level (60.6 vs 44.9), with a warm
reveal. What is still missing against the photograph is moulding, not light: no archivolt band, no keystone, no rosette
course, no engaged springing capitals, and coffers that are holes rather than sunk boxes with hard shadow lines.

## Verdict

**TILE REVIEW: PASS.** Both round-10 blockers are closed and both acceptance boxes land; the name sweep is clean at
**0 hits**; every ray still passes; **no placeholder-grade object remains anywhere in the hero frame.** The 4K v2 is
worth its wall time and the lead can render it.

Carried to the Phase 5 known-issues list, ordered by hero visibility: **QA-10b-1** (frame chroma 1.22x — the one cheap
lever left if the lead wants one more lighting touch before the 4K), QA-10-3 (archivolt), QA-10-4 / QA-10-5 (coffer
depth), QA-10-7 (column stripes), QA-10-8 (dome cap), QA-10-17 (cam03's near column, now **worse**: 0.192 vs 0.292),
QA-10-16 (chequer paving), QA-10-12 (cam02's remaining magenta shaft) / QA-10-13 (gold-on-dark soffit), QA-10-14
(backdrop boxes), QA-10b-2 (entablature 0.83x), then the minors.
