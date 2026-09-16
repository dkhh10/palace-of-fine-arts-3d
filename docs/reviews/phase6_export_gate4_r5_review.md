# MERGE WITH FIXES — `phase6-export` `0ba4cb8..4f19d01` (Gate 4 r5, instance-irradiance order), 11 findings (3 fix now, 4 should fix, 0 blockers)

Read-only: 5 commits, `export/gate4_instance_order.py` (new), `web/tools/instance_rows.mjs` (new),
`export/manifest_v4.py`, `export/verify_glb.py`, README item 31. Checked against the artefacts in MAIN
(`out/gate3/instance_{rows,irradiance,order}.json`), not against the report.

**Verified correct.** The axis swap is right: `to_gltf` = `(x, z, -y)` (`gate4_instance_order.py:71-74`) is exactly
CLAUDE.md's "Blender +Y -> glTF -Z, Blender +Z -> glTF +Y", and it is asserted, not assumed — 7 bake-measured
`checks.dark` locs, worst 0.63 mm (`:123-132`), with a hard exit if none carried a loc. The greedy nearest match is
a real bijection at these numbers, not a heuristic: per-row nearest + runner-up >= 3x + a global `used` duplicate
exit (`:164-179`) + containment and count equality per node (`:146-162`) + the unmatched/per-mesh asserts
(`:193-199`). Two placements 88 mm apart cannot swap: that needs a residual > 22 mm, and `TOL_M` (30 mm) trips at
the same order while the worst residual measured is 5.7 mm and the worst margin 69x; the JSON's 3-dp `loc` rounding
is 0.5 mm, 44x below the margin. `PFA_INSTANCE_IRR` overrides only the input, never the output path (`:88-91`).
`in_glb: false` is the right call — `env.glb` is byte-identical (36 946 188 B in the order file and on disk) and a
re-pack would reshuffle the very rows being mapped. Float32 vs JSON is a non-issue: 6-dp decimals, max 12.607, so
<= 1e-6 absolute, well inside float32; `encode: "none"`, `range_global` informational, nothing quantised.
No viewer consumer exists yet (`grep -rn instance_irradiance web/src` is empty), so the schema fix below is free.

## Fix now

1. **`segments` repeats a mesh inside a node, and both the docstring and the consumer note say it cannot.**
   `gate4_instance_order.py:37-38` ("a mesh's rows stay contiguous inside a node") is contradicted by the file it
   writes: nodes 10 / 16 / 21 are `[maho2, 8] [maho2.001, 1] [maho2, 37]` etc. — the odd row is *inside* the run, so
   the base mesh owns two segments. The builder at `:182-188` handles that correctly, but the schema ships no
   offset and `manifest_v4.py:114-120` tells the consumer to concatenate "each segment's slice of that mesh's
   `rgb`". Add a per-segment `offset` (row index into that mesh's array) and fix both texts to say a mesh may
   appear more than once and must be read with a running cursor.
   *Failure:* the viewer slices `rgb[0 .. 3*37]` for the third segment and 37 of node 10's 46 mahonias get the
   irradiance of placements 0-36 — wrong lighting that looks like a bake artefact, not a bug.

2. **Nothing ties `instance_order.json` to the irradiance JSON or the glb it was built from, and the documented
   refresh chain skips `verify_glb`.** `manifest_v4.py:55-59` asserts only placement/mesh counts, which survive any
   re-bake unchanged; `order["irradiance_generated"]` and `order["glb_bytes"]` are copied into the manifest
   (`:96-99`) but never compared. README item 31 (line 1493) documents `manifest_v4.py && sync_main.sh` — the
   `glb_bytes` guard at `verify_glb.py:107` only runs inside `gltf_pack.sh --gate1`. Assert both inside
   `instance_block()`.
   *Failure:* the re-baked RGBs ship under the harness-era order file, or under a re-packed `env.glb`'s old row
   order, and every assert in the chain passes.

3. **The test harness can ship as production silently.** `gate4_instance_order.py:103-120`: `have_loc = all("loc" in
   p ...)` — if the re-bake writes `loc` for 1378 of 1379 placements the script drops the whole set back to
   `env.gltf` translations *by object name*, i.e. exactly the name join the bake review ruled out
   (`docs/reviews/phase6_bake_gate4_instance_review.md`, decisions.md 2026-09-16 "Join key: object names do not
   survive gltfpack -mi"). `manifest_v4.py:97` only reports `loc_in_json`; verify_glb only reports it too
   (`verify_glb.py:144`). Make the harness opt-in (`PFA_INSTANCE_ORDER_HARNESS=1`), hard-exit otherwise, and make
   `loc_in_json: false` a `bad` in verify_glb.
   *Failure:* the current run (`loc_in_json: false`, cross-check "trivially true") is merged as-is and nobody
   re-runs the join after the re-bake; the name join ships behind a paragraph of prose saying it did not.

## Should fix

4. **The stale guard on `instance_rows.json` is basename + mtime only** (`gate4_instance_order.py:95-97`);
   `instance_rows.mjs:60` records no size or hash. *Failure:* rows dumped from MAIN's `env.glb`, join run against
   the worktree's `env.glb` of the same name — every residual stays under 3 cm and a wrong row order ships with no
   error. Write `glb_bytes` in the mjs and assert it against the glb the join picks (the pattern already exists at
   `verify_glb.py:107`).

5. **`gltf_node` may be `null`** (`instance_rows.mjs:53`, `assoc.nodes ?? null`), and `verify_glb.py:114-115` does
   `0 <= i < len(...)` on it. *Failure:* a gltfpack/three change that puts the InstancedMesh under a Group makes
   verify raise `TypeError` instead of reporting a clean failure. Reject a null node index in the mjs.

6. **No negative test for the new gate.** Nothing exercises `counts_match: false`, the duplicate-row exit or the
   segment-total mismatch. *Failure:* an inverted condition in `instance_irradiance_check` passes forever because
   it is only ever run against good data. A synthetic order file with one duplicated row, run in the gate3 suite,
   is enough.

7. **`verify_glb.py:85` hardcodes the MAIN absolute path** while every other module honours `PFA_MAIN_ROOT`
   (`gate3_common.MAIN_ROOT`, `gltf_pack.sh:12`). *Failure:* on a differently named checkout the fallback silently
   finds nothing and the Gate 4 check disappears from the report instead of failing.

## Note

8. `verify_glb.py:103` builds `out / "env.glb"` for whatever out dir it is given while reading `out/../gate3`; only
   `--gate1` calls it today, but on `gate0` it would report a false failure.
9. README item 31 lines 1503-1505 quote worst residual **5.9 mm / margin 55x**; the shipped `instance_order.json`
   says **5.738 mm / 69.2x** (pre-location-join numbers). Same paragraph's "1.85 -> 1.96 MB" is not yet true — the
   MAIN manifest is still 1 852 075 B and carries no `instance_irradiance` block (the lead's step B).
10. `manifest_v4.py:114-120` hardcodes "nodes 10 / 16 / 21 hold 46 / 102 / 76" in prose that is emitted whatever the
    data says; derive it from `nodes` or drop the numbers.
11. +106 kB onto a ~1.96 MB manifest that blocks the first frame is fine on this Mac; make sure the 6b host serves
    it gzip/br, and prefer a per-node flat array over per-mesh + segments if the viewer ends up stitching anyway.
