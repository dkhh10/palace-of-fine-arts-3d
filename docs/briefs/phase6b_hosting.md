# Phase 6b — hosting comparison (research only, 2026-09-17)

Payload: web/dist ~2 MB (site) + export/out ~840 MB desktop (195 MB glb, 747 MB ktx2, few MB hdr/exr/cube; largest
single files ~30 MB) + ~200 MB more for the mobile tier. A few dozen-hundred visitors, each may pull the full 840 MB.
Range requests + Brotli/gzip on JSON wanted. Staging URL unlisted, no auth, must work on iPhone Safari.

## 1. Host comparison

| | Per-file / deploy limit | Bandwidth / egress pricing | Range requests | Custom cache headers |
|---|---|---|---|---|
| **Vercel static (Hobby/Pro)** | CLI deploy source-size cap 100 MB (Hobby) / 1 GB (Pro) total, not truly per-file [vercel.com/docs/limits, read 2026-09-17] | Fast Data Transfer: Hobby first 100 GB free, no paid overage (Blob/site blocked past the cap); Pro: included via Flat Rate CDN (1 TB/1M req at no extra cost on the lowest tier) or on-demand $0.15–$0.35/GB [vercel.com/docs/manage-cdn-usage, vercel.com/docs/pricing/flat-rate-cdn, vercel.com/docs/pricing/regional-pricing, all read 2026-09-17] | Not documented either way for static files | Yes, via `vercel.json` headers |
| **Vercel Blob (for the large assets)** | Max object 5 TB; cache tier only up to 512 MB/object (bigger objects always MISS = pay Fast Origin Transfer every hit) [vercel.com/docs/vercel-blob/usage-and-pricing, read 2026-09-17] | Hobby: first 10 GB/month free, then Blob simply stops working until the next cycle (no paid overage); Pro: storage $0.023–$0.041/GB-mo, data transfer $0.05–$0.117/GB, **covered by Flat Rate CDN's tier if enabled** [same source] | Backed by S3 but Vercel's docs never explicitly confirm byte-range passthrough — unverified | Yes, `cacheControlMaxAge` per blob (≥60 s) |
| **Cloudflare Pages** | 25 MiB per asset, 20,000 files (Free) / 100,000 (paid) [developers.cloudflare.com/pages/platform/limits, read 2026-09-17] | Pages bandwidth itself is unmetered/free on all plans (not billed) | Yes (platform-wide) | Yes, `_headers` file |
| **Cloudflare R2 (for the large assets)** | Object size effectively unlimited for our files | Storage $0.015/GB-mo standard; **egress is always free, no cap**; free tier also gives 10 GB storage + 1M Class A + 10M Class B ops/month [developers.cloudflare.com/r2/pricing, read 2026-09-17] | Yes, documented | Yes, per-object or via custom domain worker/rules |
| **GitHub Pages** (baseline) | Published site ≤ 1 GB, repo soft-limit 1 GB | Soft bandwidth limit 100 GB/month, no paid tier — throttled/warned above it [docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits, read 2026-09-17] | Not a storage service; not documented | Limited (no custom headers on the default domain) |
| **Netlify** (baseline) | Not documented for static assets | Free plan now credit-based (~15 GB/mo equivalent for accounts created after 2025-09-04; legacy accounts 100 GB hard cap); paid-plan bandwidth-per-credit numbers were not confirmable from the public pricing page during this pass [netlify.com/pricing, read 2026-09-17 — inconclusive, flagged for follow-up] | Unclear | Yes, `_headers` file |

Cloudflare Pages' 25 MB per-file cap and GitHub Pages' 1 GB site cap both rule out hosting the glb/ktx2 set directly on
the page host — everyone in this comparison needs (or already plans, per the draft) a separate object-storage origin
for the ~1 GB of binary assets.

## 2. Estimated monthly cost, N full 840 MB downloads (0.84 GB decimal)

| N downloads | Total egress | Vercel (Pro $20/mo + Blob, on-demand) | Vercel (Pro + Flat Rate CDN, included tier) | Cloudflare Pages + R2 |
|---|---|---|---|---|
| 50 | 42 GB | $20 + $2–$5 ≈ **$22–$25** | **$20** flat (well under the 1 TB/mo tier) | **~$0** (storage ≈ $0.02; egress free) |
| 200 | 168 GB | $20 + $8–$20 ≈ **$28–$40** | **$20** flat | **~$0** |
| 1,000 | 840 GB | $20 + $42–$98 ≈ **$62–$118** | **$20** flat (still under 1 TB) | **~$0–$0.50** (R2 ops start to matter only in the millions) |

Vercel Hobby is excluded from the cost table: Blob hard-stops at 10 GB of data transfer/month (~12 full downloads)
with no paid path past it — it cannot serve this payload at any of the three scales. Flat Rate CDN's own eligibility
rules exclude "bulk file distribution," "large-scale media delivery," and "using the CDN as a file-hosting system"
[vercel.com/docs/pricing/flat-rate-cdn, read 2026-09-17] — a photoreal-building asset bundle sits close to that line,
so the $20-flat number is optimistic; Vercel could require moving to on-demand billing, which is the middle column.
GitHub Pages and Netlify's free tiers are blown through at all three scales (GH Pages: 200 downloads = 168 GB > 100 GB
soft cap; Netlify's new free tier caps around 15 GB, i.e. under 20 downloads).

## 3. CORS / same-origin implications (assets on a separate origin from the page)

- **Same-origin avoids the problem entirely.** R2 supports attaching a custom domain/subdomain of the site's own zone
  (e.g. `assets.example.com` next to `example.com` on Pages) — same-origin, no CORS headers needed, and it is the
  simplest way to keep byte-range + caching behavior fully in Cloudflare's hands. Vercel Blob URLs are always on
  `*.public.blob.vercel-storage.com`, a different origin from the Vercel-hosted site — CORS is mandatory there.
- **If cross-origin:** the asset origin must send `Access-Control-Allow-Origin` (the site's origin, not `*`, if
  credentials/cookies ever matter — they don't here), `Access-Control-Allow-Methods: GET, HEAD, OPTIONS`, and expose
  `Content-Range, Content-Length, Accept-Ranges, ETag` via `Access-Control-Expose-Headers` so three.js's range-based
  glTF/KTX2 loaders can read partial-content responses. `Accept-Ranges: bytes` and correct `Content-Range` on 206
  responses are required for any range-fetching loader to work at all, cross-origin or not.
- **Threaded KTX2 transcoding** (Basis Universal's multi-threaded build) needs `SharedArrayBuffer`, which requires the
  *page* to send `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp` — and then
  every cross-origin asset response must carry `Cross-Origin-Resource-Policy: cross-origin` or the fetch is blocked.
  This is avoidable by staying single-threaded or by keeping assets same-origin (R2 custom domain sidesteps it).
- `<img>`/texture fetches also need `crossorigin="anonymous"` set on the client side whenever the asset origin differs
  from the page origin.

## 4. Recommendation

Cloudflare Pages (site) + R2 (the ~1 GB of glb/ktx2/hdr) on a custom subdomain of the same zone is the clear choice:
egress is free at any of the three visitor scales, R2 has no per-file ceiling that forces workarounds the way Pages'
own 25 MB limit or GitHub's 1 GB site cap would, and a same-origin custom domain removes the CORS/COEP complexity
entirely while still supporting range requests natively. Vercel is viable only on Pro with Blob, costs $20–$118/month
at this project's scale depending on whether Flat Rate CDN is allowed to cover it (uncertain given its own
bulk-media exclusion), and gives no documented range-request guarantee for large blobs — a real cost and risk
difference for zero functional gain over Cloudflare. GitHub Pages and Netlify's free tiers are ruled out outright by
their bandwidth and per-site size caps at even the 50-download scale.
