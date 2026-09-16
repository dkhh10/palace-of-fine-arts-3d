# MERGE WITH FIXES — `phase6-export` `77063c6..35865b8` (Gate 3 r4, leaf alpha), 7 findings (1 fix now, 6 carry, 0 blockers)

Read-only: 2 commits over `export/` (README 29, gltf_gate1.py, verify_glb.py, new read_alpha.py) + 4 logs; nothing
outside `export/` and `renders/logs/`. r3 fix-nows stay closed; r3 carries 3-9 and Gate 1 carries 6-11 untouched.
Verified by parsing the artefacts, not from the report: packed `env.glb` has `MASK` on the 8 cards + `MAT_EXP_treeboard`
and **no `alphaCutoff` on the 8** (gltfpack drops the 0.5 default) — the effective-cutoff test at `verify_glb.py:264` is
necessary and correct. The PNG colour-type test is sound *for this set*: in `out/gate1/tex_gltf` exactly the 6 card
textures are colour type 6, every other PNG type 2, the rest JPEG; no WebP, no palette+tRNS, no KTX2-only base colour
(`export_image_format="AUTO"`, `gltf_gate1.py:431`, writes PNG whenever alpha is needed; JPEG never carries alpha). The
KTX2s keep it: UASTC DFD channelID **3 (RGBA)** on `leaves_*`/`needles_*`/`reeds`, 0 on the `_nrm` maps and the probe.
`MAT_EXP_treeboard` is consistent — patched earlier (`gltf_gate1.py:489-500`) to MASK 1.0 with `baseColorFactor` alpha 0
so every fragment is discarded, and skipped by the new block because it already declares a mode: hence 8, not 9. MASK
over BLEND is right (no depth sort) and nothing downstream undoes it — the gate3 manifest's 9 PBR sets match no foliage
material, so `web/src/pbr.js:157 m[slot] = t` cannot swap the alpha-carrying map out, and the viewer patches materials
in place so GLTFLoader's `alphaTest` survives. `read_alpha.py` is read-only (no `save_*`, render or operator, rc=0 in
4 s), `PFA_MAIN_ROOT` is honoured via `g1.MAIN_ROOT` (`gltf_gate1.py:147`), `alpha_cutoffs.json` is inside the gate3
rsync (`sync_main.sh:29-33`) so local-then-MAIN is real after a merge, and only `alphaMode`/`alphaCutoff` are written.

## Fix now

1. **fix now** — `export/read_alpha.py:91-105` reads the wrong quantity, and two of the eight cards ship at the wrong
   cutoff. `material.alpha_threshold` is Blender's **factory default 0.5, never set by this project** (no
   `alpha_threshold` or `blend_method` assignment exists anywhere in `scripts/`), and under `HASHED`/`DITHERED` it is
   inert — it only applies to `CLIP`. So "read, not guessed" (README 29, docs/decisions.md 2026-09-16) does not hold for
   the number that shipped. The real cut is in the builder, `scripts/mat_build.py:1385-1417`:
   `alpha = map_range(tex.Alpha, alpha_cut - 0.15, alpha_cut + 0.15, 0, 1)` driving a Transparent/Mix-Shader pair into
   the material output — a chain `read_alpha.chain()` never sees, because it walks back only from the Principled
   `Alpha` socket (unlinked at 1.0 here) and looks only for a Math `GREATER_THAN`. The 50 % crossing is exactly
   `alpha_cut`: **0.45 for `MAT_leaf_cypress` and 0.42 for `MAT_leaf_pine`** (`mat_build.py:1738,1740-1741`); the other
   six use the 0.5 default, so they are right by luck. At 0.5 the viewer discards needle texels that Phase 5 renders at
   up to ~77 % opacity — thinner cypress and pine against the Cycles reference, on the stations QA scores for parity.
   Fix: walk the Transparent-mix branch (cutoff = mean of the Map Range From Min/From Max) and re-run, or at minimum
   ship 0.45/0.42 from the builder. The cross-check at `gltf_gate1.py:527-531` is vacuous for the same reason — it
   compares a constant default against itself and would pass any wrong value.

## Carry

2. **carry** — `export/gltf_gate1.py:391-400,519`: `png_has_alpha` returns `None` for an unreadable file or an unknown
   suffix and the material is then **skipped silently** (`is not True`), which is the exact failure mode being fixed.
   `AUTO` passes a WebP source straight through, and a percent-encoded `uri` would miss on disk. Make `None` a hard
   failure. Also: colour type 3 + `tRNS` is alpha-carrying and reads as False (no such file today).
3. **carry** — `export/verify_glb.py:255`: the assertion set is `alpha_mask_materials`, i.e. only what *this run
   changed*. A material that already declares a mode (treeboard, or any future exporter-written one) is never checked in
   the packed glb, and the `alpha_mode_materials` block written at `gltf_gate1.py:544-546` is dead data. Test against it.
4. **carry** — `export/verify_glb.py:266-268`: `BLEND` passes with no cutoff check and no note. The branch never writes
   BLEND, so a glb that comes back BLEND is a silent change of sorting behaviour; make it a reported deviation.
5. **carry** — mip erosion: `toktx --genmipmap` averages the alpha, so a fixed 0.5 test thins foliage with distance and
   shimmers — a parity difference MASK cannot express. Consider `alphaToCoverage` (MSAA) or a mip-aware cutoff on the
   near-tree cards; the far trees are impostors and unaffected.
6. **carry** — `export/gltf_gate1.py:395`: `Path(path).read_bytes()[:26]` reads whole textures (ORN normals 13-16 MB) to
   look at 26 bytes, and `b[25]` raises `IndexError` on a truncated PNG. `open(...).read(26)` plus a length guard.
   `:380` also re-derives the checkout root by hand instead of `g0.ROOT` (identical value; the r1 rule says otherwise).
7. **carry (repeat of r3 #9)** — `export/read_alpha.py` never asserts the opened blend is `master_delivery.blend`; it
   records the path, which is the saving grace. One `assert bpy.data.filepath == str(g2.SRC_BLEND)`.

## Could not verify (no Blender, gltfpack, npm or Chrome)

- That `master_delivery.blend`'s node graph matches `scripts/mat_build.py` — finding 1 reads the builder and the
  `HASHED/DITHERED` + untouched-0.5 evidence in `export_gate3_alpha2.log`, not the blend itself. One `read_alpha` run
  extended to the Transparent-mix branch settles it.
- The on-screen result (leaf cards cut out at cam02) and the ETC1S/mobile alpha path; env `+152 B` and toktx 258 s are
  read from the committed logs.
