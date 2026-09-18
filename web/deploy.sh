#!/bin/zsh
# Phase 6b — build the site, assemble the publish directory, check it against Cloudflare Pages'
# limits, and deploy it.  There is no hand step: the staging URL is whatever this script produced.
#
#   web/deploy.sh --dry-run                     # everything except the upload; needs no login
#   web/deploy.sh --project pfa-walkthrough     # the real deploy (needs `npx wrangler login` first)
#   web/deploy.sh --dry-run --manifest /path/to/manifest.json [--mobile /path/to/manifest_mobile.json]
#
# Options
#   --dry-run            assemble and verify, print the wrangler command, upload nothing
#   --r2                 move files over 25 MiB to R2 behind functions/assets/[[path]].js
#   --allow-oversize     assemble anyway with files over 25 MiB (to serve the directory locally and
#                        test the artefact; a Pages upload would reject them)
#   --project NAME       Cloudflare Pages project (default $PFA_PAGES_PROJECT or pfa-walkthrough)
#   --branch NAME        Pages branch (default staging; Pages gives it its own preview url)
#   --manifest PATH      the desktop manifest to publish (default $PFA_MAIN_ROOT/export/out/gate5/manifest.json,
#                        falling back to the gate3 v4 manifest so the script is testable today)
#   --mobile PATH        the mobile manifest (default: manifest_mobile.json beside the desktop one)
#   --out DIR            publish directory (default web/deploy_out, gitignored, rebuilt every run)
#   --keep               do not clear the publish directory first
#
# What it does, and why each step is there
#   1. `npm run build` -> web/dist (the site: 2 MB of js + the basis transcoder).
#   2. The publish directory is dist, plus one HARD LINK per bake file under `assets/<gate>/...`.
#      Hard links, not copies: the bake is ~840 MB and the publish directory is regenerated on every
#      deploy, so copying it would cost a gigabyte of writes and a gigabyte of disk each time.  It
#      falls back to a copy across filesystems, and says which it used.
#   3. Cloudflare Pages' FREE-tier limits are checked BEFORE the upload, because the upload is where
#      they would otherwise be discovered: 25 MiB per file and 20 000 files
#      [developers.cloudflare.com/pages/platform/limits, read 2026-09-17].  A file over 25 MiB is not
#      a reason to stop: `--r2` puts those files in an R2 bucket behind functions/assets/[[path]].js,
#      which serves them at the SAME url (see that file).  That is the documented fallback, not the
#      default, because the tier split is meant to keep every published file under the cap.
#   4. `_headers` (see the heredoc): `assets/*` is immutable for a year — every bake file's name is
#      unique to its content in practice and a new bake goes to a new gate directory — and the site
#      itself is revalidated.  NO Cross-Origin-Opener/Embedder-Policy: three's KTX2Loader transfers
#      ArrayBuffers to its workers and never allocates a SharedArrayBuffer (checked against
#      node_modules/three/examples/jsm/loaders/KTX2Loader.js and the basis transcoder: zero matches
#      for SharedArrayBuffer), so cross-origin isolation would buy nothing and would force a
#      Cross-Origin-Resource-Policy header onto every asset response.
#   5. `npx wrangler pages deploy <dir> --project-name <name> --branch <branch>`.  NO TOKEN IS EVER
#      READ OR WRITTEN BY THIS SCRIPT: it uses whatever `npx wrangler login` left in the user's own
#      wrangler config.  --dry-run stops before this line and works with no login at all.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
MAIN=${PFA_MAIN_ROOT:-$ROOT}
ASSETS=${PFA_ASSETS:-$MAIN/export/out}
PROJECT=${PFA_PAGES_PROJECT:-pfa-walkthrough}
BRANCH=staging
DRY=0
KEEP=0
R2=0
ALLOW_OVER=0
R2_BUCKET=${PFA_R2_BUCKET:-pfa-assets}
OUT="$ROOT/web/deploy_out"
MANIFEST=""
MOBILE=""
MAX_FILE=$(( 25 * 1024 * 1024 ))
MAX_FILES=20000

while [ $# -gt 0 ]; do
	case "$1" in
		--dry-run) DRY=1 ;;
		--keep) KEEP=1 ;;
		--r2) R2=1 ;;
		--allow-oversize) ALLOW_OVER=1 ;;
		--project) PROJECT=$2; shift ;;
		--branch) BRANCH=$2; shift ;;
		--manifest) MANIFEST=$2; shift ;;
		--mobile) MOBILE=$2; shift ;;
		--bucket) R2_BUCKET=$2; shift ;;
		--out) OUT=$2; shift ;;
		-h|--help) sed -n '2,40p' "$0"; exit 0 ;;
		*) echo "deploy.sh: unknown option $1" >&2; exit 2 ;;
	esac
	shift
done

if [ -z "$MANIFEST" ]; then
	if [ -f "$ASSETS/gate5/manifest.json" ]; then MANIFEST="$ASSETS/gate5/manifest.json"
	elif [ -f "$ASSETS/gate3/manifest.json" ]; then MANIFEST="$ASSETS/gate3/manifest.json"
	else echo "deploy.sh: no manifest found under $ASSETS (pass --manifest)" >&2; exit 2; fi
fi
[ -f "$MANIFEST" ] || { echo "deploy.sh: no manifest at $MANIFEST" >&2; exit 2; }
if [ -z "$MOBILE" ] && [ -f "$(dirname "$MANIFEST")/manifest_mobile.json" ]; then
	MOBILE="$(dirname "$MANIFEST")/manifest_mobile.json"
fi

echo "deploy.sh: project $PROJECT branch $BRANCH  (dry-run $DRY)"
echo "deploy.sh: desktop manifest $MANIFEST"
[ -n "$MOBILE" ] && echo "deploy.sh: mobile manifest  $MOBILE" || echo "deploy.sh: mobile manifest  (none yet)"

# ---------------------------------------------------------------------------- 1. the site
( cd "$ROOT/web" && npm run build >/dev/null )
echo "deploy.sh: web/dist $(du -sh "$ROOT/web/dist" | cut -f1)"

# ---------------------------------------------------------------------------- 2. publish directory
[ "$KEEP" = "1" ] || rm -rf "$OUT"
mkdir -p "$OUT"
# the site first: cp -R keeps the small files as real copies (2 MB), which keeps wrangler simple
cp -R "$ROOT/web/dist/." "$OUT/"
# web/public/stub is the DEVELOPMENT tier stub (web/tools/stub_tiers.mjs) and vite copies it into
# dist with everything else.  It has no business in a deployment unless it IS what is being
# deployed, which is how the dry run is exercised before the export's gate5 manifest exists.
case "$MANIFEST" in
	*web/public/stub/*) ;;   # a relative --manifest has no leading slash
	*) rm -rf "$OUT/stub" ;;
esac

LINKED=0; COPIED=0; TOTAL_BYTES=0; OVERSIZE_LIST="$OUT/.oversize"
: > "$OVERSIZE_LIST"
link_set() {           # $1 = manifest path
	local pub disk bytes tier target dir
	node "$ROOT/web/tools/publish_set.mjs" --manifest "$1" | while IFS=$'\t' read -r pub disk bytes tier; do
		target="$OUT/$pub"
		dir=$(dirname "$target")
		[ -d "$dir" ] || mkdir -p "$dir"
		if [ ! -e "$target" ]; then
			if ln "$disk" "$target" 2>/dev/null; then echo "L $bytes $pub"; else cp "$disk" "$target"; echo "C $bytes $pub"; fi
		fi
	done
}
# `set -e` is on and publish_set.mjs exits 3 when the manifest names a file nothing answers, so a
# publish set with a hole in it stops here rather than becoming a deployment with a hole in it.
link_set "$MANIFEST" > "$OUT/.linked" || {
	echo "deploy.sh: the desktop manifest names files that are not on disk — refusing to deploy a set with holes" >&2
	exit 4
}
if [ -n "$MOBILE" ]; then
	link_set "$MOBILE" >> "$OUT/.linked" || {
		echo "deploy.sh: the mobile manifest names files that are not on disk — refusing to deploy a set with holes" >&2
		exit 4
	}
fi
LINKED=$(grep -c '^L ' "$OUT/.linked" || true)
COPIED=$(grep -c '^C ' "$OUT/.linked" || true)
echo "deploy.sh: $LINKED hard-linked, $COPIED copied from $ASSETS"

# ---------------------------------------------------------------------------- 3. the host's limits
rm -f "$OUT/.linked"
FILES=$(find "$OUT" -type f ! -name '.oversize' | wc -l | tr -d ' ')
BYTES=$(find "$OUT" -type f ! -name '.oversize' -exec stat -f %z {} + | awk '{s+=$1} END {print s+0}')
find "$OUT" -type f ! -name '.oversize' -size +${MAX_FILE}c > "$OVERSIZE_LIST" || true
OVER=$(wc -l < "$OVERSIZE_LIST" | tr -d ' ')
echo "deploy.sh: publish set $FILES file(s), $(( BYTES / 1000000 )) MB, $OVER over 25 MiB"
[ "$FILES" -le "$MAX_FILES" ] || { echo "deploy.sh: $FILES files is over Cloudflare Pages' 20 000 limit" >&2; exit 5; }
if [ "$OVER" -gt 0 ]; then
	echo "deploy.sh: files over Cloudflare Pages' 25 MiB per-file cap:" >&2
	while read -r f; do echo "  $(( $(stat -f %z "$f") / 1048576 )) MiB  ${f#$OUT/}" >&2; done < "$OVERSIZE_LIST"
	if [ "$R2" != "1" ] && [ "$ALLOW_OVER" != "1" ]; then
		echo "deploy.sh: refusing to deploy. Either the export splits them (the tier plan says it should)," >&2
		echo "           or re-run with --r2 to put exactly these files in R2 behind functions/assets/[[path]].js." >&2
		echo "           --allow-oversize assembles the directory anyway: for serving it locally to test the" >&2
		echo "           artefact, never for a Pages upload, which would reject those files." >&2
		exit 6
	fi
fi

# ---------------------------------------------------------------------------- 4. headers
cat > "$OUT/_headers" <<'HEADERS'
# Every bake file lives under a gate directory that is rewritten as a whole, never in place, so its
# url identifies its content: cache it for a year and never revalidate.
/assets/*
  Cache-Control: public, max-age=31536000, immutable
  Access-Control-Allow-Origin: *
# The site is small and changes with every deploy.
/*
  Cache-Control: public, max-age=300, must-revalidate
# Deliberately NOT set: Cross-Origin-Opener-Policy / Cross-Origin-Embedder-Policy.  three's
# KTX2Loader transfers ArrayBuffers to its worker pool and never allocates a SharedArrayBuffer
# (checked: zero matches in KTX2Loader.js and in the basis transcoder), so cross-origin isolation
# would buy no transcoding speed and would require Cross-Origin-Resource-Policy on every asset.
HEADERS

# ---------------------------------------------------------------------------- 4b. the R2 fallback
if [ "$R2" = "1" ] && [ "$OVER" -gt 0 ]; then
	mkdir -p "$OUT/functions/assets"
	cp "$ROOT/web/functions/assets/[[path]].js" "$OUT/functions/assets/[[path]].js"
	echo "deploy.sh: R2 fallback ON — bucket $R2_BUCKET, binding ASSETS_BUCKET, $OVER file(s)"
	while read -r f; do
		key="${f#$OUT/}"
		if [ "$DRY" = "1" ]; then
			echo "deploy.sh: [dry-run] npx wrangler r2 object put \"$R2_BUCKET/$key\" --file \"$f\" --remote"
		else
			npx wrangler r2 object put "$R2_BUCKET/$key" --file "$f" --remote
		fi
		rm -f "$f"                      # it is served by the Function now, not by Pages
	done < "$OVERSIZE_LIST"
fi
rm -f "$OVERSIZE_LIST"
# the authoritative count, after every file that is going to move has moved
FILES=$(find "$OUT" -type f | wc -l | tr -d ' ')
BYTES=$(find "$OUT" -type f -exec stat -f %z {} + | awk '{s+=$1} END {print s+0}')
OVER=$(find "$OUT" -type f -size +${MAX_FILE}c | wc -l | tr -d ' ')
echo "deploy.sh: publish set FINAL $FILES file(s), $(( BYTES / 1000000 )) MB, $OVER over 25 MiB"
if [ "$OVER" -ne 0 ] && [ "$ALLOW_OVER" != "1" ]; then
	echo "deploy.sh: still $OVER file(s) over the cap after the R2 step" >&2; exit 6
elif [ "$OVER" -ne 0 ]; then
	echo "deploy.sh: $OVER file(s) over the cap, kept by --allow-oversize (a Pages upload WILL reject them)" >&2
fi

# ---------------------------------------------------------------------------- 5. deploy
CMD=(npx wrangler pages deploy "$OUT" --project-name "$PROJECT" --branch "$BRANCH")
if [ "$DRY" = "1" ]; then
	echo "deploy.sh: DRY RUN — nothing uploaded. The deploy command is:"
	echo "  ${CMD[*]}"
	echo "deploy.sh: it needs a Cloudflare login once, in the user's own session: npx wrangler login"
	exit 0
fi
"${CMD[@]}"
