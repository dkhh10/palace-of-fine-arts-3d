/**
 * Phase 6b — the R2 FALLBACK for assets over Cloudflare Pages' 25 MiB per-file cap.
 *
 * It is a fallback, not the default.  The load-tier split is meant to keep every published file
 * under 25 MiB; when one cannot be split (a 4K UASTC atlas, say), `web/deploy.sh --r2` uploads THAT
 * FILE to an R2 bucket and leaves it out of the Pages upload, and this Function serves it at exactly
 * the same url.  The viewer therefore never learns the difference: one origin, one path space, no
 * CORS, and `?tier=` / the manifest stay as they are.
 *
 * Wiring (one-off, in the Pages project's settings or `npx wrangler pages project`):
 *   - an R2 bucket (free tier: 10 GB stored, egress always free)
 *   - bound to this Pages project as `ASSETS_BUCKET`
 * With no binding, or with no object for the path, the Function falls through to Pages' own static
 * asset for that url (`env.ASSETS.fetch`), which is what serves everything in the normal case.
 *
 * Range requests: the viewer's glTF and KTX2 loaders fetch whole files today, but a 25 MB+ asset is
 * exactly where a browser or a CDN may ask for a range, so `Range` is passed through to R2 and a
 * 206 with `Content-Range` is returned when R2 honours it.  `Accept-Ranges: bytes` is always set,
 * and a `If-None-Match` matching the object's etag gets a 304.
 */

const TYPES = {
	glb: 'model/gltf-binary', gltf: 'model/gltf+json', ktx2: 'image/ktx2',
	hdr: 'image/vnd.radiance', exr: 'image/x-exr', cube: 'text/plain; charset=utf-8',
	json: 'application/json', png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg',
	webp: 'image/webp', bin: 'application/octet-stream',
};

export async function onRequestGet( context ) {
	const { request, env, params, next } = context;
	const parts = Array.isArray( params.path ) ? params.path : [ params.path ];
	// `assets/<...>` is the key layout deploy.sh uploads with: the published path, unchanged.
	const key = `assets/${parts.join( '/' )}`;
	const bucket = env.ASSETS_BUCKET;
	if ( ! bucket ) return next();                       // no R2 bound: Pages serves its own file

	const range = request.headers.get( 'range' );
	const opts = {};
	if ( range ) opts.range = request.headers;            // R2 parses the header itself
	const etag = request.headers.get( 'if-none-match' );
	if ( etag ) opts.onlyIf = { etagDoesNotMatch: etag };

	let object;
	try { object = await bucket.get( key, opts ); } catch { return next(); }
	if ( object === null ) return next();                 // not in R2 either: let Pages answer (404s there)

	const headers = new Headers();
	object.writeHttpMetadata( headers );
	headers.set( 'etag', object.httpEtag );
	headers.set( 'accept-ranges', 'bytes' );
	headers.set( 'cache-control', 'public, max-age=31536000, immutable' );
	headers.set( 'access-control-allow-origin', '*' );
	const ext = key.split( '.' ).pop().toLowerCase();
	if ( TYPES[ ext ] ) headers.set( 'content-type', TYPES[ ext ] );

	// onlyIf matched: R2 returns the object without a body.
	if ( ! object.body ) return new Response( null, { status: 304, headers } );

	if ( object.range && typeof object.range.offset === 'number' ) {
		const start = object.range.offset;
		const end = start + ( object.range.length ?? ( object.size - start ) ) - 1;
		headers.set( 'content-range', `bytes ${start}-${end}/${object.size}` );
		return new Response( object.body, { status: 206, headers } );
	}
	return new Response( object.body, { status: 200, headers } );
}
