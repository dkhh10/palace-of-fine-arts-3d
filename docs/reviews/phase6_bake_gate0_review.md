MERGE WITH FIXES

Branch `phase6-bake` @ 536fc15 vs main. 18 files, no tracked binary over 5 MB (only `renders/web/gate0_cycles_cam01.png`,
488 KB, inside the owner's allowed set), no file outside export/* + renders/web/gate0_* + phase6_plan.md §4. No
`save_mainfile`; the only save is `gate0_common.save_copy` -> `save_as_mainfile(copy=True)` with a `master*` name guard
(`export/gate0_common.py:138-146`) — check (2) passes. `apply_final_cycles_checked` runs first in every script that bakes or
renders (`bake_normal.py:22`, `bake_pbr.py:26`, `bake_lightmap.py:35`, `bake_lut.py:49`, `render_reference.py:31`), and its
assertion matches `light_presets` (shade fill is a per-engine rig, not Eevee-only; `FINAL_TIME_LIMIT_S` is 0, so the preset
cannot truncate a bake) — check (1) passes. Sun vector, `direction_gltf = (x, z, -y)`, azimuth = `atan2(d.y, -d.x)` and
`u = 0.5 + atan2(x,y)/360` are self-consistent with the file's one SUN and with CLAUDE.md — check (6) passes on the maths.
RGBM8 encode/decode is correct (ceil on M keeps `enc <= 1`; `rng = 64` for max 51.8; worst 0.097 abs = `rng/512`) — check
(5) passes except the clipped claim, see 4.

1. `export/gltf_export.py:146-149` + `export/README.md:67-70` (fix now) — the viewer contract is off by pi. The map is
   Cycles' diffuse-colour-off pass = irradiance/pi, and three.js' lightMap path then multiplies by `BRDF_Lambert` =
   albedo/pi, so `lightMapIntensity = 1` renders pi times too dark. Fix: state `lightMapIntensity = Math.PI` (or bake x pi).
2. `export/bake_lightmap.py:96` (fix now) — the ground lightmap job passes `hi_name=None`, so its own coincident hi twin
   (`ARCH_rotunda_pedestal_00`, still in `REF_ALL`) stays ray-visible and self-shadows the bake; the 12-tri ground taking
   461 s, the slowest job, is the symptom. Fix: pass `g0.GROUND_NAME_FILE.read_text().strip()` as `hi_name` and re-bake.
3. `export/gltf_export.py:147` (fix now) — glTF forces `emissiveTexture` to sRGB, so three.js' GLTFLoader will sRGB-decode
   the RGBM texels before the viewer's decode. Fix: add "set the texture's colorSpace to NoColorSpace" to `viewer_action`.
4. `export/bake_lightmap.py:62,152` + `phase6_plan.md` §4 table (fix now) — `clipped_px` is measured on the *decoded* buffer
   against `rng`, which `rgbm_encode` makes unreachable by construction; "0 clipped" is tautological, not evidence. Fix:
   count `(rgb.max(-1) > rng)` on the source EXR instead, and reword the table's claim.
5. `export/gate0_common.py:118-125` + `export_set.py:331` (fix now) — `manifest_merge` `.update()`s dicts, so
   `assets={}, textures={}, lut={}` never clears; a rerun after a rename leaves ghost entries in the viewer contract.
   Fix: `(g0.OUT / "manifest.json").unlink(missing_ok=True)` at the top of export_set.py. Otherwise idempotency (3) is good
   (collections rebuilt, `bake_image` removes by name, `rm -rf tex_ktx2`, gate0.sh re-runnable by step range).
6. `export/bake_lut.py:335-344` (carry) — `u_error_deg` and `horizon_row_v` are reported but never asserted, and the
   "brightest pixel on the horizon" reading silently assumes `sun_disc` is off. Fix: assert `|u_error_deg| < 0.5` and log
   `sky.sun_disc`.
7. `export/bake_lut.py:118` (carry) — check (4) holds: the lattice is pushed through `FOLLOW_SCENE` with the compositor
   detached, and `lut_apply`/`shaper_inverse` are exact inverses, so the 5-patch proof is like-for-like. But all five patches
   are neutral, so only the LUT's grey diagonal is proven; AgX's hue path is untested. Fix: add two saturated patches at Gate 1.
8. `export/gate0_common.py:17,39`; `gate0.sh:10`; `sync_main.sh:7`; `gltf_pack.sh:11` (carry) — check (7)/(9): `MAIN_ROOT` is
   re-hard-coded instead of `os.environ.get("PFA_MAIN_ROOT", str(common.MAIN_ROOT))`, and `HERO_CAM` duplicates
   `qa_cameras.CAMERAS[0]["name"]`. Everything else correctly comes from `common`/`qa_cameras` (WATER_Z, stations, `ensure`).
9. `export/sync_main.sh:9` (carry) — `rsync -a --delete` into the shared `$MAIN/export/out/gate0/` will erase anything the
   export or viewer agent puts there. Fix: drop `--delete`, or restrict it to `tex/ tex_ktx2/`.
10. `export/gltf_export.py:124` (carry) — `tex_gltf/` is never cleared, so a stale PNG from an earlier run is still fed to
    toktx (harmless but wasteful). And `gate0_common.guard_no_master_write` (:129) is dead code — call it or delete it.
