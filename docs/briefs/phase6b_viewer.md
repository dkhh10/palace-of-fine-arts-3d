# 6b viewer brief — progressive loading, tier switch, deploy (Opus high, fresh agent). Branch `phase6b-viewer` (worktree .claude/worktrees/phase6b-viewer, branched from main today).
Read first: CLAUDE.md "Phase 6" (machine rules: every Chrome run through scripts/chrome_run.sh, screenshot.mjs refuses while a Blender process is alive — do not kill it, do
non-Chrome work and retry), docs/briefs/phase6b_plan.md (items 2, 3, 4, 5), docs/briefs/phase6b_hosting.md §1 and §3, docs/decisions.md from "2026-09-18 · 6b" to the end
(the user's decisions: iPhone 16 Pro; Cloudflare Pages FREE tier, 25 MiB per-file cap, no custom domain, `<project>.pages.dev` staging; the tier-0 look may be low-res with a
progress readout), docs/briefs/phase6b_export.md (the manifest v5 `tiers` / `glb.groups` / `files` contract you consume — coordinate the schema with the export engineer
through the lead if you need a field), web/README.md "Run" and the loading-screen section, web/src/main.js (the progress accounting at lines ~199-270, the lazy env_trees path),
web/src/foliageLazy.js (the pattern for streaming a glb after boot), web/src/manifest.js, web/tools/screenshot.mjs, web/tools/gate4.sh.

## Deliverables (commit after every working step; `npm run build` must pass at every commit)
A. **Progressive loading.** Manifest v5: tier 0 boots the scene (loading screen as 6a; denominator = tier 0 bytes from `tiers`), `window.__pfaReady` fires on the first
   presented frame after tier 0; tiers 1-2 stream after that frame in manifest order with material / texture hot-swap (low-res -> full-res KTX2 on the same material, ORN
   groups added as they arrive, lightmaps bound when they land) and a small unobtrusive readout ("tier 1: 212 / 380 MB"). No visible pop at the hero station: a 960 px capture
   at boot (tier 0 only, `?tiers=0`) and after tier 2 (`?tiers=all`), judged by the lead; the frame after tier 2 must match round16c's station-1 capture (luma 1.00 +- 0.01,
   MAE within the resampling noise as QA 17 measured the bare URL). Until the export's gate5 manifest lands in MAIN, develop against a stub you generate from the v4 manifest
   with a documented rule (`web/tools/stub_tiers.mjs`, not committed as data); switch to the real one when the lead says it is in MAIN.
B. **Tier switch.** `?tier=desktop|mobile` overrides; default from a WebGL probe (max texture size, ASTC/ETC support, `navigator.userAgent` iPhone/iPad, devicePixelRatio
   and screen size) recorded in the boot log. The mobile manifest (`manifest_mobile.json`): impostors for all trees, shrubs LOD2, water without the planar Reflector, post =
   LUT only, renderer pixel ratio capped so the drawing buffer is <= 1.5 M px. Report the desktop 1440p median frame time and resident memory unchanged from round16c
   (`--perf`, gate4 settings) after A + B — the streaming must cost nothing once everything is resident.
C. **Deploy.** `web/deploy.sh [--dry-run] [--project <name>]`: builds web/dist, assembles the publish directory (dist + `assets/` = the manifest's `files` for the tiers of
   both manifests, symlinked or hard-linked from MAIN export/out, never copied twice), verifies every file <= 25 MiB and the file count <= 20 000, writes `_headers`
   (immutable cache for `assets/*`, `Cross-Origin-*` only if the KTX2 worker pool needs it — measure; prefer not), then `npx wrangler pages deploy <dir> --project-name <name>
   --branch staging`. If the export reports files over 25 MiB in `tiers.oversize`, add the R2 path: `functions/assets/[[path]].js` streams those from an R2 binding at the
   same URL (range passthrough), and `deploy.sh` uploads them with `wrangler r2 object put`; document it as the fallback, not the default. Dry-run must work without a
   Cloudflare login; the real deploy waits for the user's `npx wrangler login` (ask the lead, who asks the user; never store a token in the repo). `web/tools/screenshot.mjs`
   gets `--url <base>` used against the staging URL; `web/tools/gate5.sh` = stations 1-6 at 1920x1080 against a base URL plus a network log (initial payload before the first
   frame, time to first frame, per-tier arrival) into `renders/web/gate5_*.json`.
D. **Docs.** web/README.md: a "Phase 6b" section (tiers, the boot order, the switch, deploy, the staging URL once it exists); docs/delivery.md is the lead's.

Rules: Chrome only through scripts/chrome_run.sh and only when no Blender is alive (the export engineer runs short CPU Blender jobs on the same machine); low frame counts;
no Blender at all on this branch; commit every 15 minutes; do not touch export/, assets/, master*.blend, or any manifest under export/out (the export owns them). Report < 25
lines to the lead: what boots at tier 0 and its bytes, the pop judgement captures (paths), frame time and resident after A + B, deploy dry-run output, files, commit id.
Code review before merge (the lead dispatches it).
