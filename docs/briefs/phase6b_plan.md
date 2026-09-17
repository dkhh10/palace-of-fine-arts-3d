# Phase 6b — web deployment plan (lead draft, 2026-09-17; finalised after the 6c gate; the user names the iPhone and the host)
Definition of done (CLAUDE.md 6b): initial payload <= 50 MB, progressive loading, meshopt + KTX2; Safari and Chrome on macOS; a mobile fallback (LOD1 geometry,
halved textures) that loads and walks, tested in iOS Safari on the iPhone the user names; a staging URL with ONE QA round against it. Stops at deployment + one clean QA round.

## Where we start (measured on MAIN export/out at the 6c manifest, 2026-09-17)
| set | bytes | note |
|---|---|---|
| glb (arch, orn, env, ground, backdrop, env_shrubs, env_trees, water) | 194.7 MB | meshopt -cc -mi; env_trees 2.0 MB and env_shrubs 0.4 MB already lazy |
| KTX2 referenced by the manifest | 747.3 MB | UASTC desktop set; the loading screen reports 639 MB resident at 1440p |
| 6a target on this Mac | 1 055 MB resident GPU | budget 1 200 MB |
The desktop download is therefore ~840 MB against a 50 MB initial payload: 6b is a LOADING-ORDER and ENCODING problem, not a viewer rewrite.

## Gate 5 items (owners; one branch each: phase6b-export, phase6b-viewer; reviews before every merge as Phase 6)
1. Load tiers (export, manifest v5 block `tiers`): tier 0 = what the hero station sees at 1440p within 50 MB (ARCH + ground glb ~40 MB of the 195, the LUT, the sky
   equirect, ETC1S or quarter-res UASTC of the hero-visible albedos, no ORN ornament lightmaps yet); tier 1 = the rest of the full-look textures and ORN in hero
   visibility order (the manifest's per-asset station visibility from the Gate 1 silhouette pass); tier 2 = everything else, streamed while the walker stands still.
   Measured, not guessed: `export/tiers.py` writes the byte total per tier and the viewer's loading screen reports it. Textures get a per-tier KTX2 variant only where
   the tier needs it (no second full set).
2. Progressive viewer (viewer): tier 0 boots the scene (loading screen as 6a, denominator = tier 0), tiers 1-2 stream after the first frame with material hot-swap
   (the existing lazy env_trees.glb path is the pattern), no visible pop at the hero station (a 960 px capture at boot vs after tier 2, judged by the lead).
3. Mobile fallback (export + viewer): `?tier=mobile` manifest with LOD1 geometry (the export set already carries `_LOD1` for ENV; ARCH/ORN use the LOD1 export where it
   exists, else the decimated LOD0 at half budget), textures halved (ETC1S KTX2, the toktx `--encode etc1s` path in gltf_pack.sh), impostors only for the far trees, shrubs
   at LOD2, water without the planar reflection, post = LUT only. Target: loads and walks at 30 fps on the named iPhone; resident < 700 MB. User-agent + a WebGL
   probe (max texture size, ASTC/ETC support) pick the tier automatically; `?tier=` overrides.
4. Hosting and staging: static site + assets on object storage with HTTP range and Brotli (Vercel is connected to this session and hosts the static build; large
   assets go to Vercel Blob or an R2 bucket behind the same origin, because per-file limits and egress pricing decide, not convenience — the lead lists the two with
   their measured cost for ~840 MB x N visitors before the user picks). Deployment through one script (`web/deploy.sh`), never a hand upload; the staging URL is
   password-free but unlisted; `docs/delivery.md` gets the URL and the tier table.
5. QA on the URL (Opus xhigh, one round): stations 1-6 in headless Chrome against the staging URL (screenshot.mjs takes a base URL), Safari on this Mac by the user
   (one screenshot at the hero), iOS Safari on the named iPhone by the user (a screen recording of a 30 s walk), initial payload measured from the network log
   (<= 50 MB before the first frame), time to first frame, per-tier arrival times. Verdict: 6b DONE or one fix round.

## Decisions the user takes before Gate 5 starts
- The iPhone model (sets the mobile GPU memory ceiling and the ASTC assumption).
- The host: Vercel (already connected) or Cloudflare Pages + R2; the lead brings the cost table first.
- Whether the 50 MB initial payload may show the building with placeholder-resolution textures for the first seconds (the tier-0 look), or must wait for tier 1
  (then "initial" means ~150 MB and the definition of done changes — the lead recommends the tier-0 look with a progress readout).
