// Phase 6b: which asset tier this device gets, and the render settings that go with it.
//
// Two tiers, both of them real files the export writes:
//   desktop   manifest.json        — the frozen Phase 5 look, full-resolution UASTC, planar water
//   mobile    manifest_mobile.json — LOD1 geometry, halved ETC1S textures, impostors for every tree,
//                                    shrubs at LOD2, the water's planar reflection cut to the sky,
//                                    post = the LUT alone, drawing buffer capped at 1.5 M pixels
//
// `?tier=desktop|mobile` overrides everything and is what the QA harness uses.  With nothing asked,
// the choice is a PROBE, and every input to it is recorded in the boot log and in `__pfaInfo().device`
// so a wrong guess can be read off a capture instead of being argued about.
//
// The probe deliberately does NOT trust the user agent alone: iPadOS 13+ reports a Macintosh UA and
// is distinguished only by `maxTouchPoints`, and a desktop browser in a phone-sized window is still a
// desktop GPU.  The GPU's own evidence (max texture size, which compressed formats exist) comes first.

/** What the WebGL context says about itself.  Never throws: a missing extension is a `false`. */
export function probeGl( renderer ) {
	const caps = { maxTextureSize: null, astc: false, etc2: false, bptc: false, s3tc: false,
		renderer: null, vendor: null, webgl2: false };
	try {
		const gl = renderer.getContext();
		caps.webgl2 = typeof WebGL2RenderingContext !== 'undefined' && gl instanceof WebGL2RenderingContext;
		caps.maxTextureSize = gl.getParameter( gl.MAX_TEXTURE_SIZE );
		const has = ( n ) => !! gl.getExtension( n );
		caps.astc = has( 'WEBGL_compressed_texture_astc' );
		caps.etc2 = has( 'WEBGL_compressed_texture_etc' );
		caps.bptc = has( 'EXT_texture_compression_bptc' );
		caps.s3tc = has( 'WEBGL_compressed_texture_s3tc' );
		const dbg = gl.getExtension( 'WEBGL_debug_renderer_info' );
		caps.renderer = dbg ? gl.getParameter( dbg.UNMASKED_RENDERER_WEBGL ) : gl.getParameter( gl.RENDERER );
		caps.vendor = dbg ? gl.getParameter( dbg.UNMASKED_VENDOR_WEBGL ) : gl.getParameter( gl.VENDOR );
	} catch ( e ) { caps.error = e.message; }
	return caps;
}

/** What the page says about itself (no GL).  Kept separate so the rule below can be unit-tested. */
export function probeEnv( nav = ( typeof navigator !== 'undefined' ? navigator : {} ),
	win = ( typeof window !== 'undefined' ? window : {} ) ) {
	const scr = win.screen || {};
	return {
		ua: nav.userAgent || '',
		maxTouchPoints: nav.maxTouchPoints || 0,
		deviceMemoryGb: nav.deviceMemory || null,
		hardwareConcurrency: nav.hardwareConcurrency || null,
		devicePixelRatio: win.devicePixelRatio || 1,
		screen: [ scr.width || 0, scr.height || 0 ],
	};
}

/**
 * The rule, in one place and with its reasons.  `mobile` wins on ANY of:
 *   - a phone/tablet user agent, or a Macintosh UA with touch points (iPadOS 13+);
 *   - a GPU with ASTC but no S3TC/BPTC — that combination is a mobile tile GPU, not a desktop one;
 *   - MAX_TEXTURE_SIZE <= 4096, which cannot hold the desktop atlases;
 *   - a touch screen whose short side is <= 900 CSS px at devicePixelRatio >= 2.
 * Everything else is `desktop`.  Each reason that fired is reported.
 */
export function chooseTier( { gl, env, query } ) {
	if ( query === 'mobile' || query === 'desktop' ) return { tier: query, from: 'query', reasons: [ `?tier=${query}` ] };
	if ( query && query !== 'auto' ) return { tier: 'desktop', from: 'query-invalid',
		reasons: [ `?tier=${query} is not a tier (desktop | mobile | auto): using desktop` ] };
	const reasons = [];
	const ua = env.ua || '';
	if ( /iPhone|iPod|Android.*Mobile|Windows Phone/i.test( ua ) ) reasons.push( `phone user agent` );
	else if ( /iPad|Android/i.test( ua ) ) reasons.push( `tablet user agent` );
	else if ( /Macintosh/i.test( ua ) && env.maxTouchPoints > 1 ) reasons.push( 'Macintosh user agent with touch points (iPadOS 13+ reports this)' );
	if ( gl && gl.astc && ! gl.s3tc && ! gl.bptc ) reasons.push( 'ASTC without S3TC/BPTC: a mobile tile GPU' );
	if ( gl && gl.maxTextureSize && gl.maxTextureSize <= 4096 ) reasons.push( `MAX_TEXTURE_SIZE ${gl.maxTextureSize} <= 4096` );
	const short = Math.min( env.screen[ 0 ] || 1e9, env.screen[ 1 ] || 1e9 );
	if ( env.maxTouchPoints > 0 && short <= 900 && env.devicePixelRatio >= 2 ) reasons.push( `touch screen ${env.screen.join( 'x' )} at dpr ${env.devicePixelRatio}` );
	return { tier: reasons.length ? 'mobile' : 'desktop', from: 'probe',
		reasons: reasons.length ? reasons : [ 'no mobile evidence: desktop' ] };
}

/** The render settings each tier carries.  The viewer reads THESE, never the string, so a new tier
 *  is a row here and nothing else.  `maxDrawingBufferPx` is the cap the pixel ratio is solved for. */
export const TIER_SETTINGS = {
	desktop: { manifest: null, maxDrawingBufferPx: null, post: null, water: null,
		treeMesh: null, farTreeLight: null, shrubLod: null, walkupMesh: null, farTreeMesh: null,
		impInt: null,
		imp2k: null, reflSet: null, foliageTex: null },
	mobile: {
		manifest: 'manifest_mobile.json',   // resolved against the desktop manifest's own url
		maxDrawingBufferPx: 1.5e6,          // 1500x1000; the iPhone 16 Pro's own panel is 1179x2556
		post: 'none',                       // the LUT display pass is not part of ?post and still runs
		water: 'sky',                       // the planar Reflector draws the SKY only (no second scene pass)
		// PHASE 7 ITEM D.  6b made every tree on a phone an impostor at EVERY distance, and the
		// user's close orbit is what that looks like from three crown-widths away: flat cut-outs with
		// black cores, because an 85 px atlas frame magnified onto a 30 m card has no silhouette and
		// no interior left.  The three near tiers are turned back on, each with a radius small enough
		// that only what the walker is standing among is a mesh:
		treeMesh: '25',                     // near-tree meshes within 25 m (desktop 80)
		// The far-tree mesh set, which is what a walker at the shore actually looks at: MEASURED on
		// the orbit fixture, every crown in the user's screenshot is a far-tree placement and the
		// nearest is 36.7 m (heading 253) / 37.4 m (heading 215); the nearest NEAR tree
		// (ENV_tree_*_LOD1) is 127.6 m away and contributes nothing, so `treeMesh` above cannot be
		// the lever for that frame.  `walkupMesh: '0'` takes the LOD2 set (127 k unique tris)
		// instead of the walk-up LOD1 one (472 k): the same feature at the same radius for a quarter
		// of the resident memory - 561.9 MB against 689.7, measured - which is what pays for the
		// radius below.
		walkupMesh: '0',                    // the LOD2 far set, not the walk-up LOD1 one (lead, Phase 7)
		farTreeMesh: 45,                    // ... drawn within 45 m, which covers the shore stance (desktop 12)
		farTreeLight: 'near',               // ... which needs the far-tree loader to run at all
		shrubLod: 25,                       // LOD1 shrubs inside the same radius (desktop 30)
		// and the atlas darkening is eased where a card is now only ever seen from further away
		// (?impint=str,radius,floor; the desktop default is 0.90,0.015,0.35).
		impInt: '0.45,0.015,0.55',
		imp2k: false,                       // the 1K impostor atlas
		reflSet: 'both',   // 6d: was 'all' (sky only); 'both' keeps ARCH, ground, near ENV and impostors, drops ORN and backdrop, at the half-res target
		foliageTex: '1024',
	},
};

/**
 * Pixel ratio that keeps `w x h` CSS pixels inside `maxPx` drawing-buffer pixels.
 * With no cap (desktop) it is 1, which is what every capture since Gate 0 has used and the only
 * value that makes two screenshots comparable.  With a cap it may go ABOVE 1 on a retina phone —
 * up to 2, and only as far as the cap allows — because 1.0 on a dpr-3 panel is visibly soft and the
 * budget is in drawing-buffer pixels, not in CSS ones.
 */
export function pixelRatioFor( w, h, maxPx, devicePixelRatio = 1 ) {
	if ( ! maxPx || ! ( w > 0 ) || ! ( h > 0 ) ) return 1;
	const fit = Math.sqrt( maxPx / ( w * h ) );
	return Math.max( 0.25, Math.min( Math.min( devicePixelRatio || 1, 2 ), fit ) );
}
