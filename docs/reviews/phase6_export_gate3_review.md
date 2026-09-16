# MERGE WITH FIXES — `phase6-export` @ 6798563 (Gate 3 export), 11 findings (3 fix now, 8 carry, 0 blockers)

Reviewed read-only: 13 commits, `main...phase6-export` over `export/` (README.md, gate3_relay_check.py, gltf_gate1.py,
gltf_pack.sh, verify_glb.py) plus 8 logs under `renders/logs/`. **Nothing outside `export/` and `renders/logs/` is
touched** — no `scripts/`, no `docs/`, no `assets/`, no `manifest.json`, no other agent's file; `sync_main.sh` is main's
(kept at the merge, `f31dd2a`/`21c781f`), still no `--delete`. No tracked binaries. Numbers below are reproduced from
the committed logs, not from the report.

Passing, verified from the diff: the COLOR_0 encode/decode is symmetric end to end — writer `gltf_gate1.py:~270`
`rng = float(np.float32(lin.max()))`, `code = sqrt(v/rng)`; checker `gate3_relay_check.py:~188` recomputes `rng` from the
npz and never takes the writer's, then cross-checks the writer's (`abs(w["range"]) - rng > 1e-6·rng` → fail); manifest
`export/manifest_v4.py:172-176` copies exactly `range`, `encoding`, `mean_linear`, `roundtrip_rel_p99`, and the relay
emits all four (`gate3_relay_check.py:~225-238`) — **keys match, no silent drop**. `glb_decode` in manifest_v4.py:163
(`v = C²·range`, then `·lightmaps.scale`) inverts the encode on the raw npz value exactly. Asserting the mean over the
*distinct* value set instead of the per-vertex mean (c15360e) is the right call: the exporter splits 6-36 % more
vertices, and a split/weld cannot move a unique-value mean. Frozen Gate 1 geometry holds: arch −0.185 %, orn −0.157 %,
env/ground 0.000 % against `export_set.json` — identical to Gate 1/2 — UV1 is untouched by any new code, and orn.glb /
ground.glb are byte-identical this round. The brief's "`-vp 16` on env" is the brief's own stale wording; env has been
`-vpf` since Gate 1 for a measured reason (README item 295-298), and the branch correctly kept `-vpf` — *not* a defect.

## Fix now

1. **fix now** — `export/gate3_relay_check.py:297`: `main_g3 = Path("/Users/dk/Projects/3d render blender 3rd attempt
   building/export/out/gate3")` is hard-coded and ignores `PFA_MAIN_ROOT`. Every other export script resolves MAIN
   through the common module (`gltf_gate1.py:112,146` `g1.MAIN_ROOT`; `manifest_v4.py:42` `g3.MAIN_ROOT`;
   `sync_main.sh`). The Gate 1 review recorded "`PFA_MAIN_ROOT` honoured throughout"; this is the first regression of
   that. One line: `Path(os.environ.get("PFA_MAIN_ROOT", …)) / "export" / "out" / "gate3"`.
2. **fix now** — `export/gate3_relay_check.py:295-299` vs `export/gltf_gate1.py:146`: the two halves of the hand-off
   resolve their source differently. The **encoder always reads MAIN's** `out/gate3`; the **checker prefers a LOCAL**
   `out/gate3` whenever `lightmap_uv2.npz` exists there. If a worktree ever holds a local gate3 npz that differs, the
   checker validates the glb against a file the encoder never read and the PASS means nothing; and a local
   `lightmap_uv2.npz` *without* `vertex_irradiance.npz` crashes at `np.load` (line ~165) instead of skipping. Make both
   resolve identically (MAIN-first, or pass the directory in from the caller).
3. **fix now** — `export/verify_glb.py:221-223` with `export/gltf_pack.sh:112-113`: the material-split guard is
   one-directional. `dup_names and not split` fails, but **`split and not dup_names` does not** — i.e. gltfpack merging
   the same-named copies back is silent. The split only works because `-km` (keep named materials, so equal-named
   materials are never merged) is on arch and env; **orn and ground are packed `-cc -mi -kv` with no `-km`**
   (`export_gate3_pack_r2b.log:140`), so a split on either would be undone without a failure. Today orn is caught only
   incidentally by the slot count (436 == 436) and ground not at all. Add: when `split` is non-empty, require
   `dup_names >= len(split)` **and** `-km` in that class's `gltfpack_flags`.

## Carry

4. **carry** — `export/verify_glb.py:226-236`: the slot guard compares a **class total** (`plain + inst >= slot_objects`)
   rather than one drawn mesh/instance per `orn_slots` row. It does catch this round's regression (arch was 442 vs 552,
   now 556 vs 552) but would pass a future merge of up to 4 slot meshes on arch. The real invariant is per-slot.
5. **carry** — `export/verify_glb.py:198-208`: a class whose `.gltf` carries `TEXCOORD_1`/`COLOR_0` but was packed
   **without `-kv`** only gets a printed note, never a `bad` entry — the exact Gate 3 blocker, downgraded to a note.
   It is covered today only by `gate3_relay_check` (for the 7 + 14) and the orn-specific check at `:245`; the other 59
   `uv2_all_meshes` rows are reported, never asserted. Make it a failure.
6. **carry** — `-vc 16` is never verified on the packed glb. `gate3_relay_check.py` reads the codes out of `<cls>.gltf`
   (correctly — the glb is meshopt-compressed) and the glb test is presence-only (`packed_attr`, `:107`). The glb JSON
   still carries `componentType`/`normalized` on the COLOR_0 accessors, so a dropped `-vc 16` (silent requantisation to
   8 bits, 0.8 % linear error at mid grey) would pass. Assert `5123` + `normalized` in the packed doc.
7. **carry** — `export/verify_glb.py:245`: `if n_uv2 != 33` ("the 33 ORN prototypes") is a magic number, as is the
   `0.15` threshold constant at `:281`. Harmless while Gate 1 geometry is frozen; derive the 33 from `export_set.json`.
8. **carry** — `export/gltf_gate1.py:_acc_vals` (~:470): plain-buffer layout only. It asserts on `byteStride`, but does
   not handle sparse accessors and would `TypeError` on a GLB-embedded buffer (`uri` is `None` → `path.parent / None`).
   Safe under `GLTF_SEPARATE`; add one explicit `assert uri`.
9. **carry** — `export/gltf_gate1.py` fake-COLOR_0 detector (~:495): "the fake is the `UNSIGNED_BYTE` set whose `min()`
   is 1.0". It **cannot drop the real attribute here** — the strip above leaves exactly one real colour attribute per
   mesh (the `FLOAT_COLOR` irradiance, exported as u16/float), the branch runs only when ≥2 sets exist, and the survivor
   is asserted to be `5123`/`5126`, so a u8 real set fails loudly rather than being kept. But the test itself would also
   match a genuinely constant-white u8 attribute; harden it with `max() == 1.0`, a component/count check, or by keying
   on accessor order, so the invariant does not depend on the strip staying in place.
10. **carry** — 8 logs (~1,900 lines) committed this round, with the `_r2`/`_r2b` pairs near-duplicates. Within the
    convention, but the pre-fix runs add little once the README records the measured deltas.
11. **carry** — downstream numbers now stale: arch 27 → **29** draw calls / 4 609 468 → **4 613 040 B**, env 35 797 240 →
    **36 951 988 B** (+1.15 MB, +3.2 %). `docs/briefs/phase6_budget.md` and any payload figure derived from it still
    carry pre-Gate-3 bytes; the lead's `manifest_v4.py` re-run fixes the manifest, not the budget doc. Class glbs now
    total 43.5 MB against the 6b ≤ 50 MB initial-payload target (orn.glb 154 MB is streamed, not initial).

## Gate 1 carries — status

**Closed (all 5 fix-now):** 1 `--assign_oetf $oetf` per-map at `gltf_pack.sh:31,42,58,87,177`; 2 `cp -f "$STATUS"
"$MAIN/…/status.json"` at `bake_queue.sh:72,85`; 3 slot gutter at `gate1_common.py:102-109` + `gate1_set.py:891`
(`gutter_px`/`slot_px`); 4 `voxel_remeshed` in the manifest at `gate1_set.py:980,1035`; 5 measured `per_tree` at
`budget_doc.py:189`. **Open (carries, none touched or worsened by this branch):** 6 unmatched `ENV_*` LOD dropped
silently (no `rep["skipped"]`); 7 `hide_render` still never read on the export set; 8 raw-vs-evaluated tris in the
shrub allowance; 9 no bake retry on rc 143/137; 10 half — `gltfpack.log` truncated at `gltf_pack.sh:74`, but the
`new_from_object` leaks are unchanged; 11 the 77-vs-20 near-tree count and 1 343 MB texture memory, still a user item.

## Could not verify (read-only: no Blender, gltfpack, npm or Chrome run)

- **gltfpack's actual merge rule** ("same material **and** identical node transform set") and that `-km` really keeps
  same-named materials apart. The only evidence is the branch's own measurement — 442 → 556 placements, 988/988 slots,
  +3 572 B, 27 → 29 draw calls vs `-kn`'s +52 552 B / 564 draw calls (README item 22, `export_gate3_pack_r2b.log:140`).
  Plausible and self-consistent, but not independently reproduced; finding 3 is the guard that makes it safe to trust.
- **Idempotency.** No script saves a blend (`grep -n "save_as_mainfile\|save_mainfile"` on the branch → none); every
  output is re-derived from the frozen `gate1_set.blend`, the `.gltf` is rewritten whole each run, and the re-run
  asserts (`pre` colour attributes empty, `delta > 1e-5`, `after > before`) all hold on a fresh load. Not executed. The
  **determinism of the split** depends on the exporter's mesh ordering in the `.gltf`, which I could not prove stable
  across runs; `merge_groups` itself is deterministic given that order (insertion order, `mis[1:]`).
- **Blender 5.2's fake-COLOR_0 behaviour** (`primitive_extract.py` ~line 818) — taken from the branch's note and its own
  measurement (COLOR_0 u8 min = max = 1.0, COLOR_1 u16 mean 0.1097, 27 primitives fixed on env), not from the source.
- **Downstream effect of duplicate material names.** `web/src/pbr.js:19-38` builds a name→set map, so two materials with
  one name resolve to the same Gate 2 texture set; `web/src/detail.js` traverses materials rather than indexing by name;
  `web/src/main.js:616-626 matchLightmap` matches on `mat.name` and would give both copies the same lightmap, which is
  correct. No `KHR_materials_variants` anywhere. Looks safe; the viewer's 988-placement re-check is still owed.
- **The glbs themselves.** Every byte, triangle, coverage and mean figure above is read from the committed logs and
  `verify_glb` / `gate3_relay_check` output, not re-measured.
