# MERGE WITH FIXES — phase6b-viewer @ de4dd87 vs main (441594b), 12 commits

Viewer side is sound: I could not break the tier contract, the upgrade direction or the cache accounting.
Both blockers are in `web/deploy.sh`, which has never run for real — fix before the first staging deploy, not before merge.

1. **blocker** `web/deploy.sh:114-134` — `publish_set.mjs` exits 3 on a named-but-missing file, but it is the *left* side of a
   pipeline and zsh has no pipefail, so the pipeline's status is the `while` loop's 0 and the `|| exit 4` guard is dead. Verified
   with a minimal zsh repro. README:1379 ("a file the manifest names and disk does not answer stops the deploy") is therefore
   unbacked, and a deployment with a hole in the building ships silently. Fix: `setopt pipefail` after `set -e` (line 44).
2. **blocker** `web/deploy.sh:160-173` + `web/tools/publish_set.mjs:83-88` — the manifest is published at
   `assets/<gate>/manifest.json`, and Pages' `*` spans `/`, so `manifest.json`, `manifest_mobile.json` and
   `uv2_relay_status.json` are pinned `max-age=31536000, immutable`. The second deploy serves a year-stale load plan to every
   returning visitor. Fix: append after the `/assets/*` block (later rules override): `/assets/*manifest*.json` and
   `/assets/*_status.json` → `public, max-age=60, must-revalidate`.
3. **fix now** `web/src/main.js:787-853` — the whole tier loop sits in ONE try/catch. `loadGlbs` isolates a 404 per glb
   (1358-1361, correct), but a throw in `afterGeometry` / `applyDetail` / `setupFoliageAndImpostors` aborts every *later* tier
   with one `tier stream FAILED` line. Fix: move the try/catch inside the `for`, record per tier, continue.
4. **fix now** `web/src/main.js:843-849` — dangling else: `else note('lazy foliage not loaded…')` hangs off the late-upgrade
   `if`, not off `if ( sceneCompletionTier <= tierState.max )`. Any `?tiers=all` load of a manifest without `upgradeOf` logs that
   the foliage was skipped when it was loaded. Fix: attach the else to the foliage `if`.
5. **fix now** `web/README.md:1281-1288` — stale: "41 of those stay at the low-resolution ETC1S variant for the whole session"
   was fixed by 908666a's by-name pairing; `renders/web/gate5_cam.json` reports `lowres_remaining: []`, `lowres_etc_textures: 0`,
   94 glb textures swapped. Rewrite item 2 as fixed, keep the export-side note.
6. **fix now** claim with no unit — `renders/web/gate5_net.json` `bytes_before_first_frame = 50 405 660` = **50.4 MB** against a
   "<= 50 MB" budget, reported in fb650fb as "payload … pass". It passes in MiB (48.07), not in MB. State the number and the
   unit in README's 6b section; do not carry "pass" unqualified.
7. **fix now** 22.5 MB of full-resolution PNG (+4 MB JSON) committed under `renders/web/` (`6b_real_*.png`, `6bbase.png`,
   `6btierall.png`, `6b_deployserve.png`, …). CLAUDE.md commits `renders/web` at 960 px only, and .gitignore already lists this
   class of file by name. `git rm --cached` the 7 full-res PNGs (the 960 px jpgs are committed) and add the patterns.
8. **carry** `web/src/main.js:1403-1421` — the FIRST consumer gets the cached Texture itself, not a clone, and
   `upgradePbrSets` / `upgradeGlbTextures` mutate `colorSpace` / `wrap` / `flipY` on it; a later consumer's clone inherits that
   sampler state (`upgradePbrSets` only sets wrap when `set.wrap === 'repeat'`). Fix: clone for every consumer, keep the cached
   object pristine. Refcounting itself is correct — three keys the WebGLTexture by source+sampler cacheKey and refcounts
   `usedTimes`, so disposing one clone cannot free another's upload and a differing sampler rightly gets its own.
9. **carry** `web/src/main.js:1404` — a rejected load is cached as a rejected promise forever: a transient failure is permanent
   for that url, with no retry.
10. **carry** `web/deploy.sh:176-189` — `--r2 --dry-run` still `rm -f`s the oversize files from the publish dir although nothing
    was uploaded, so the FINAL census and a locally served `deploy_out` are both wrong for a dry run. Skip the rm when `DRY=1`.
11. **carry** `web/functions/assets/[[path]].js` — only `onRequestGet`: a HEAD for an R2-only asset falls through to Pages and
    404s, and an unsatisfiable Range throws into `catch { return next(); }` → 404 instead of 416. The Range / If-None-Match /
    206 / 304 path itself is correct.
12. **carry** `web/src/device.js:68` — "ASTC without S3TC/BPTC" is the only rule that could misread an Apple-Silicon Mac;
    measured here the M2 reports s3tc+bptc true → desktop, and iPadOS's Macintosh UA + `maxTouchPoints` is covered.
    `pixelRatioFor`'s 0.25 floor can exceed `maxDrawingBufferPx` above ~24 M CSS px (unreachable); iPhone 16 Pro solves to
    1.40 Mpx, inside the 1.5 Mpx cap.

Verified clean: `canonUrl` (`new URL(u, location.href).href`) normalises only `.`/`..`/host case and cannot collapse two distinct
files; no downgrade path exists in `mapForTier`, and the upgrade target is the highest-tier row outside `tiers.lowres.dir`
(manifest.js) — the fix is general, not per-case; `instance_irradiance.groups` binds once per group (`iiBoundGroups`) before
chunking; `web/test/tiers_test.mjs` passes against both real manifests (30 PASS, 0 FAIL); no secret, token or hard-coded home
path in anything this branch adds (`deploy.sh` uses `PFA_MAIN_ROOT:-$ROOT`); `--dry-run` makes no network call.
