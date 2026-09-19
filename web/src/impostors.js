// Gate 4 item 2: the 127 far trees as octahedral impostors, replacing the grey placeholder quads.
//
// THE CONTRACT IS THE MANIFEST'S, read and never assumed (`manifest.impostors`):
//
//   mapping        octahedral, `grid` x `grid` frames on one `atlas_px` atlas, each frame `frame_px`
//                  with a `gutter_px` border, so `inner_px` is what may be sampled.
//   frame_lookup   d = normalize( camera_pos - billboard_pos ) in BLENDER Z-up (from a three.js dir
//                  with (x, -z, y)); n = d / (|d.x|+|d.y|+|d.z|); if n.z >= 0 { u = n.x; v = n.y }
//                  else { u = (1-|n.y|)*sign(n.x); v = (1-|n.x|)*sign(n.y) }; uv01 = (u,v)*0.5+0.5;
//                  col = uv01.x*(grid-1); row = uv01.y*(grid-1), counted from the BOTTOM.
//   frame_uv       u = (col*frame_px + gutter_px + f.x*inner_px) / atlas_px, v from the bottom
//                  likewise; f clamped to [0,1] and inset by half a texel.
//   encode.albedo  gamma2 on RGB at the prototype's OWN `range` (rgb = t.rgb * t.rgb * range, LINEAR
//                  oetf, NOT sRGB), STRAIGHT (un-premultiplied) alpha in A.
//   placement      s = tree_far[i].height_m / prototypes[p].height_above_base_m; a screen-facing
//                  square of side 2 * radius_m * s centred at trunk_base + (0, 0, centre_z_m * s),
//                  all in BLENDER coordinates, heights measured from the prototype's own z = 0.
//   instance_rotation  IGNORED on purpose: the lighting is baked in world space, so the frame comes
//                  from the world-space view direction. Two instances differ by scale, not silhouette.
//   unlit          the atlas already holds LIT RADIANCE: it goes straight into the linear buffer
//                  before the LUT, with no lightmap, no sun and no environment term.
//
// SO THE NORMAL+DEPTH ATLAS IS NOT LOADED.  The manifest says it is block compressed "on purpose
// while `unlit` holds and nothing samples the normal or the depth", and that shading from it would
// need it repacked lossless (+48 MB over the 16 prototypes).  Loading it to leave it unsampled would
// cost that memory for nothing, so `?impnd=1` is the switch that asks for it and the default is off.
// This is a deliberate reading of the manifest over the brief's "normal+depth for lighting": the
// radiance is already baked, and re-lighting it would double the sun.
//
// BLENDING.  The three frames around the view direction are blended with the barycentric weights of
// the octahedral cell's triangle.  The samples are STRAIGHT alpha, so they are combined the only way
// straight alpha may be: rgb = sum( w * rgb * a ) / sum( w * a ), a = sum( w * a ).  Blending the
// colour without the alpha weight would drag the silhouette's colour in from the transparent gutter.
//
// PHASE 7 ITEM A — THE CARD EDGE (QA 17 residual 3: "a pale halo reads around the crowns", and the
// jagged dithered silhouette in the user's desktop capture).  Two independent defects, two fixes,
// both on the SAMPLING side and neither touching the atlas (it is tier-0 payload):
//
//   1. THE HALO is the hardware's own bilinear filter.  `encode.albedo` is STRAIGHT alpha, so a
//      texel that is fully transparent still carries an rgb, and the bake wrote a pale one there.
//      GL_LINEAR interpolates rgb and a independently, so at the silhouette the fetched rgb is
//      (1-t)*leaf + t*pale while the fetched a is only partly reduced: dividing by that alpha does
//      NOT recover the leaf colour, because the contamination happened INSIDE one fetch, before any
//      alpha weight could be applied.  The only correct filter for straight alpha is to weight each
//      TEXEL by its own alpha, which means doing the bilinear by hand: four texel-centre taps per
//      frame, premultiplied, summed with the barycentric weight, divided by the summed alpha at the
//      end.  That is the same formula the frame blend already uses, pushed down one level - twelve
//      taps instead of three, and the transparent gutter can no longer tint a silhouette texel.
//      `?impedge=` turns it off (`0`) and back on (`1`, the default).
//   2. THE JAGGED SILHOUETTE is the hard `a < alphaTest` cut.  The atlas carries no mips on purpose
//      (a mip would blend across frames), so at the hero a far card is MINIFIED and its alpha steps
//      0 -> 1 between neighbouring pixels.  The composer's target is `samples: 4`, so the fix is the
//      one the leaf cards already use: alpha-to-coverage with three's own analytic ramp,
//      `cov = saturate( ( a - alphaTest ) / fwidth( a ) + 0.5 )`, written into gl_FragColor.a.  The
//      cutoff is unchanged - what changes is that the boundary pixel now resolves across the four
//      MSAA samples instead of snapping.  `fwidth` widens the ramp exactly where the card is
//      minified, which is where the aliasing is, and closes it again at station 2's magnification.
import * as THREE from 'three';
import { b2t } from './blenderCamera.js';

export const ALPHA_TEST = 0.33;

const vertexShader = /* glsl */`
	attribute vec3 iCentre;          // billboard centre, three-space
	attribute float iSide;           // side of the square, metres
	attribute vec3 iSwitch;          // 6c C2: the tree's crown centre, for the mesh/impostor switch
	attribute float iNear;           // 1 where a MESH exists for this tree and may replace the card
	attribute float iDist;           // per-placement switch distance; <= 0 = use the shared pfaMeshDist
	attribute vec3 iIrr;             // 6c: E_placement / E_bake for THIS placement (1,1,1 = untouched)
	varying vec3 vPfaIrr;
	uniform float pfaMeshDist, pfaFadeBand;
	varying vec2 vQuadUv;
	varying vec3 vDirBlender;        // camera -> billboard, BLENDER Z-up, unnormalised
	varying float vPfaFade;          // 1 = the impostor is the LOD, 0 = the mesh is
	#ifdef PFA_FOG
	varying float vFogDepth;
	#endif
	void main() {
		vQuadUv = uv;
		vPfaIrr = iIrr;
		// The SAME formula and the SAME uniforms as the mesh side (foliage.js), from the SAME crown
		// centre, so the two dissolves are exact complements and no tree is ever drawn twice or not
		// at all.  A tree with no mesh (the 127 far ones today) has iNear = 0 and never fades.
		// The FAR trees carry their own distance: their LOD2 mesh is measurably worse than the
		// modulated atlas at station distance (web/README.md), so it is only allowed close in, while
		// the near trees keep the shared 40 m.  One uniform could not express both.
		float pfaD = ( iDist > 0.0 ) ? iDist : pfaMeshDist;
		vPfaFade = ( iNear > 0.5 )
			? smoothstep( pfaD, pfaD + pfaFadeBand, distance( cameraPosition, iSwitch ) )
			: 1.0;
		// Screen-facing quad: the camera's right and up in world space, from the view matrix's rows.
		vec3 right = vec3( viewMatrix[ 0 ][ 0 ], viewMatrix[ 1 ][ 0 ], viewMatrix[ 2 ][ 0 ] );
		vec3 up    = vec3( viewMatrix[ 0 ][ 1 ], viewMatrix[ 1 ][ 1 ], viewMatrix[ 2 ][ 1 ] );
		vec3 world = iCentre + ( right * position.x + up * position.y ) * iSide;
		vec3 d = cameraPosition - iCentre;
		vDirBlender = vec3( d.x, - d.z, d.y );         // three -> Blender Z-up
		vec4 mv = viewMatrix * vec4( world, 1.0 );
		#ifdef PFA_FOG
		vFogDepth = length( mv.xyz );          // along the VIEW RAY, as Blender's mist pass measures it
		#endif
		gl_Position = projectionMatrix * mv;
	}
`;

const fragmentShader = /* glsl */`
	uniform sampler2D atlas;
	uniform float range;             // the prototype's own gamma-2 range
	uniform float grid, framePx, innerPx, gutterPx, atlasPx;
	uniform float alphaTest;
	uniform int debugMode;           // 0 off, 1 raw sample, 2 alpha, 3 frame cell, 4 quad uv
	// 6c round 3 — the atlas crown's own interior. (strength, radius in frame UV, Phase 7 floor)
	uniform vec3 pfaImpInterior;
	#ifdef PFA_FOG
	uniform vec3 fogColor;
	uniform float fogNear, fogFar, fogCap, fogK, fogIntensity;
	varying float vFogDepth;
	#endif
	varying vec2 vQuadUv;
	varying vec3 vDirBlender;
	varying float vPfaFade;
	varying vec3 vPfaIrr;

	// The mesh side's dither, verbatim (foliage.js): a purely spatial hash, so the crossfade is a
	// fixed pattern and a screenshot is byte-identical twice running.
	float pfaHash( vec2 p ) { return fract( 52.9829189 * fract( dot( p, vec2( 0.06711056, 0.00583715 ) ) ) ); }

	// manifest.impostors.frame_uv, with f clamped and sampled at texel centres.
	//
	// THE V FLIP.  The manifest counts the row "from the BOTTOM" and f.y likewise, but the atlases
	// are written KTXorientation: rd (right, DOWN) - measured with ktx info on every one of the 16 -
	// so data row 0 is the TOP.  Without this flip the lookup lands on the mirrored elevation, which
	// is the tree's shaded side: the hero read the far trees as dark blue (raw code 0.25/0.29/0.49)
	// because 49-101 of each atlas's 144 frames are sky-lit back sides, and it was picking those.
	vec2 frameUv( vec2 cell, vec2 f ) {
		vec2 g = clamp( f, 0.0, 1.0 );
		float px = cell.x * framePx + gutterPx + g.x * innerPx;
		float pyFromBottom = cell.y * framePx + gutterPx + g.y * innerPx;
		return vec2( ( px + 0.5 ) / atlasPx, 1.0 - ( pyFromBottom + 0.5 ) / atlasPx );
	}

	vec4 sampleFrame( vec2 cell, vec2 f ) { return texture2D( atlas, frameUv( cell, f ) ); }

	#ifdef PFA_IMP_PREMUL
	// Phase 7 item A1.  The CONTINUOUS TEXEL COORDINATE of frameUv, so the bilinear can be done by
	// hand.  A texel of index i has uv = ( i + 0.5 ) / atlasPx, and frameUv's v is flipped
	// ( uv.y = 1 - ( pyFromBottom + 0.5 ) / atlasPx ), so the data-space row index is
	// atlasPx - 1 - pyFromBottom.  Both axes then read as plain indices, and floor / fract give the
	// four neighbours and their weights the same way GL_LINEAR would.
	vec2 frameTexel( vec2 cell, vec2 f ) {
		vec2 g = clamp( f, 0.0, 1.0 );
		float px = cell.x * framePx + gutterPx + g.x * innerPx;
		float pyFromBottom = cell.y * framePx + gutterPx + g.y * innerPx;
		return vec2( px, atlasPx - 1.0 - pyFromBottom );
	}
	// One texel, exactly: the sampler is GL_LINEAR, and a fetch at a texel CENTRE returns that texel
	// with weights ( 1, 0 ), so no NEAREST sampler and no second texture object is needed.
	vec4 texelAt( vec2 i ) { return texture2D( atlas, ( i + 0.5 ) / atlasPx ); }
	#endif

	void main() {
		// THE EXACT COMPLEMENT OF THE MESH TEST (round-1 review, blocker 1).  The mesh keeps
		// { hash <= 1 - t } and this side's vPfaFade IS t, so keeping { hash <= 1 - vPfaFade } here
		// would keep the SAME set: at mid-fade half the crown drew twice and half showed background.
		// The impostor must keep exactly what the mesh discards: { hash > 1 - t }.
		// The guard is the FULLY VISIBLE case (vPfaFade = 1 keeps every pixel, including hash == 0),
		// never the invisible one: with ?treemesh=inf the mesh side draws everything and this side's
		// vPfaFade is 0, where { hash > 1 } must keep NOTHING.
		if ( vPfaFade < 0.9995 && pfaHash( gl_FragCoord.xy ) < 1.0 - vPfaFade ) discard;
		// manifest.impostors.frame_lookup, verbatim
		vec3 d = normalize( vDirBlender );
		vec3 n = d / ( abs( d.x ) + abs( d.y ) + abs( d.z ) );
		vec2 o = ( n.z >= 0.0 )
			? vec2( n.x, n.y )
			: vec2( ( 1.0 - abs( n.y ) ) * ( n.x >= 0.0 ? 1.0 : - 1.0 ),
			        ( 1.0 - abs( n.x ) ) * ( n.y >= 0.0 ? 1.0 : - 1.0 ) );
		vec2 uv01 = clamp( o * 0.5 + 0.5, 0.0, 1.0 );
		vec2 g = uv01 * ( grid - 1.0 );
		vec2 gi = floor( g );
		vec2 fr = g - gi;
		gi = min( gi, vec2( grid - 2.0 ) );

		// the three frames around the direction: the cell's triangle, barycentric
		vec2 c0, c1, c2;
		vec3 w;
		if ( fr.x + fr.y < 1.0 ) {
			c0 = gi; c1 = gi + vec2( 1.0, 0.0 ); c2 = gi + vec2( 0.0, 1.0 );
			w = vec3( 1.0 - fr.x - fr.y, fr.x, fr.y );
		} else {
			// Vertices (1,1), (0,1), (1,0).  At (fx,fy) = (0,1) the weight of (0,1) must be 1, so it
			// is 1 - fx, and (1,0) gets 1 - fy.  Having these two swapped leaned the blend on the
			// wrong neighbour by up to a cell off the diagonal and was discontinuous at the cell edge.
			c0 = gi + vec2( 1.0, 1.0 ); c1 = gi + vec2( 0.0, 1.0 ); c2 = gi + vec2( 1.0, 0.0 );
			w = vec3( fr.x + fr.y - 1.0, 1.0 - fr.x, 1.0 - fr.y );
		}

		float a;
		vec3 rgb;
		#ifdef PFA_IMP_PREMUL
		// Phase 7 item A1: ONE premultiplied reconstruction over the three frames' twelve texels.
		// Every tap's weight is ( barycentric x bilinear x its own alpha ), which is the only filter
		// straight-alpha data may be resampled with; the hardware's per-channel LINEAR is what put
		// the pale gutter into the silhouette.
		{
			vec3 acc = vec3( 0.0 );
			float accA = 0.0;
			vec2 tc[ 3 ];
			tc[ 0 ] = frameTexel( c0, vQuadUv );
			tc[ 1 ] = frameTexel( c1, vQuadUv );
			tc[ 2 ] = frameTexel( c2, vQuadUv );
			for ( int k = 0; k < 3; k ++ ) {
				vec2 t = tc[ k ];
				vec2 i0 = floor( t );
				vec2 fr2 = t - i0;
				float wk = ( k == 0 ) ? w.x : ( ( k == 1 ) ? w.y : w.z );
				vec4 t00 = texelAt( i0 );
				vec4 t10 = texelAt( i0 + vec2( 1.0, 0.0 ) );
				vec4 t01 = texelAt( i0 + vec2( 0.0, 1.0 ) );
				vec4 t11 = texelAt( i0 + vec2( 1.0, 1.0 ) );
				vec4 bw = vec4( ( 1.0 - fr2.x ) * ( 1.0 - fr2.y ), fr2.x * ( 1.0 - fr2.y ),
				                ( 1.0 - fr2.x ) * fr2.y, fr2.x * fr2.y ) * wk;
				vec4 av = vec4( t00.a, t10.a, t01.a, t11.a ) * bw;
				accA += av.x + av.y + av.z + av.w;
				acc += av.x * t00.rgb + av.y * t10.rgb + av.z * t01.rgb + av.w * t11.rgb;
			}
			a = accA;
			rgb = acc / max( accA, 1e-4 );
		}
		#else
		vec4 s0 = sampleFrame( c0, vQuadUv );
		vec4 s1 = sampleFrame( c1, vQuadUv );
		vec4 s2 = sampleFrame( c2, vQuadUv );

		// STRAIGHT alpha: weight the colour by its own alpha or the gutter bleeds into the silhouette
		a = w.x * s0.a + w.y * s1.a + w.z * s2.a;
		rgb = ( w.x * s0.a * s0.rgb + w.y * s1.a * s1.rgb + w.z * s2.a * s2.rgb ) / max( a, 1e-4 );
		#endif

		// Phase 7 item A2: the cutoff is unchanged; only its RESOLUTION changes.  fwidth( a ) has
		// to be taken before any discard that depends on it, so the coverage is computed first and
		// the fragment is dropped only when it covers no sample at all.
		#ifdef PFA_IMP_A2C
		float pfaCov = clamp( ( a - alphaTest ) / max( fwidth( a ), 1e-4 ) + 0.5, 0.0, 1.0 );
		if ( pfaCov <= 0.0 ) discard;
		#else
		float pfaCov = 1.0;
		if ( a < alphaTest ) discard;
		#endif

		// manifest.impostors.encode.albedo: gamma2 at the prototype's own range, LINEAR oetf
		vec3 lin = rgb * rgb * range;

		// 6c: the atlas is RADIANCE baked with each prototype ALONE on a lawn under the whole open
		// sky (manifest.impostors.lighting), so its light is the sky's - hue 225 deg, measured by the
		// bake engineer's diagnosis - while the same tree in the scene stands in warm bounce (hue
		// 52 deg in the Cycles reference).  The fix is not a re-bake but a per-placement ratio of the
		// two irradiances: radiance is linear in the irradiance that made it, so
		//     radiance_scene = atlas * ( E_placement / E_bake ).
		// iIrr is that ratio, 1 where nothing is known.  ?impmod=0 sets it back to 1 everywhere.
		lin *= vPfaIrr;

		// 6c ROUND 3 — THE INTERIOR OF AN IMPOSTOR CROWN (QA 16 open 2).  At station 2 the tree that
		// fills the frame is an atlas card magnified from an 85 px frame, and it reads as a smooth
		// opaque mass: centre/edge 0.504 against the Cycles reference's 0.364, p10 18.6 against 4.1.
		// The frame the bake wrote is not that flat - three of them are blended per fragment for the
		// view direction, and that average, plus the bilinear magnification, is what takes the
		// canopy's self-shadow out.  What is restored here is only what the blend removed, and it is
		// restored the way the shadow is actually distributed: by how ENCLOSED the fragment is inside
		// the silhouette.  Four alpha taps around it on the dominant frame - opaque on all four means
		// the fragment is inside the canopy, any one of them open means it is at the rim or against
		// the sky, which keeps its full level (the reference's crowns are lit at the edge too).
		// ?impint=0 is the A/B; ?impint=str,radius sets both.
		if ( pfaImpInterior.x > 0.0 ) {
			float rr = pfaImpInterior.y;
			float e = min( min( sampleFrame( c0, clamp( vQuadUv + vec2( rr, 0.0 ), 0.0, 1.0 ) ).a,
			                    sampleFrame( c0, clamp( vQuadUv - vec2( rr, 0.0 ), 0.0, 1.0 ) ).a ),
			               min( sampleFrame( c0, clamp( vQuadUv + vec2( 0.0, rr ), 0.0, 1.0 ) ).a,
			                    sampleFrame( c0, clamp( vQuadUv - vec2( 0.0, rr ), 0.0, 1.0 ) ).a ) );
			// PHASE 7 ITEM B — THE FLOOR.  pfaImpInterior.z is the smallest fraction of its own
			// radiance a crown pixel may keep, so the enclosure term can deepen the interior without
			// any population going near-black (QA 17 residual 2: the hero crown's p10 at 0.57x of the
			// Cycles reference's, and the blotches the lead's tiles found at station 5).  It is a
			// floor on the FACTOR, not a clamp on the result, so a dark tree stays dark relative to a
			// bright one and only the depth of the darkening is bounded.
			lin *= max( 1.0 - pfaImpInterior.x * smoothstep( 0.25, 0.95, e ), pfaImpInterior.z );
		}

		if ( debugMode == 1 ) { gl_FragColor = vec4( rgb, 1.0 ); return; }
		if ( debugMode == 2 ) { gl_FragColor = vec4( vec3( a ), 1.0 ); return; }
		if ( debugMode == 3 ) { gl_FragColor = vec4( c0 / ( grid - 1.0 ), 0.0, 1.0 ); return; }
		if ( debugMode == 4 ) { gl_FragColor = vec4( vQuadUv, 0.0, 1.0 ); return; }

		#ifdef PFA_FOG
		// COMP_golden_hour's airlight, the same form postChain.js patches into three's fog chunk:
		// cap * ( 1 - exp( -k * mist ) ), NOT a power curve.  fogK is the extinction coefficient.
		float t = clamp( ( vFogDepth - fogNear ) / max( fogFar - fogNear, 1e-6 ), 0.0, 1.0 );
		float mist = fogIntensity + ( 1.0 - fogIntensity ) * t;
		lin = mix( lin, fogColor, clamp( fogCap * ( 1.0 - exp( - fogK * mist ) ), 0.0, 1.0 ) );
		#endif

		// With alpha-to-coverage the alpha channel IS the coverage mask; with it off it is 1 and the
		// material is an ordinary opaque alpha-tested one, exactly as before.
		gl_FragColor = vec4( lin, pfaCov );
	}
`;

/** The atlas crown's interior term: `"str[,radius[,floor]]"`, "0" / "off", or null for the default. */
// MEASURED, not chosen (6c round 3, the sweep in web/README.md): at 0.90 / 0.015 the cam02 crown
// box lands on the reference's centre/edge (0.364 against 0.364) and the cam05 crown on its
// range/mean within 0.073, with every crown box's LEVEL inside 0.9-1.1x of the reference.
// PHASE 7 ITEM B adds the third field, the FLOOR on that term's factor.  Swept at the hero,
// station 2 and station 5 (web/README.md "Phase 7"): 0.40 is the smallest value that takes the hero
// crown's p10 back over 0.8x of the Cycles reference's while cam02's centre/edge stays within QA
// 17's credited 0.03 of the reference and station 5's frame luma returns to 1.00x.
export const IMP_INTERIOR = [ 0.90, 0.015, 0.40 ];
export function parseImpInterior( v ) {
	const d = [ ...IMP_INTERIOR ];
	if ( v === null || v === undefined || v === '' ) return d;
	const s = String( v ).trim().toLowerCase();
	if ( s === '0' || s === 'off' ) return [ 0, d[ 1 ], d[ 2 ] ];
	if ( s === '1' || s === 'on' ) return d;
	const p = s.split( ',' ).map( ( x ) => parseFloat( x ) );
	if ( Number.isFinite( p[ 0 ] ) ) d[ 0 ] = Math.min( Math.max( p[ 0 ], 0 ), 1 );
	if ( Number.isFinite( p[ 1 ] ) ) d[ 1 ] = Math.min( Math.max( p[ 1 ], 0.002 ), 0.4 );
	if ( Number.isFinite( p[ 2 ] ) ) d[ 2 ] = Math.min( Math.max( p[ 2 ], 0 ), 1 );
	return d;
}

/**
 * Phase 7 item A — the card-edge treatment, `?impedge=`.  `"premul"` / `"a2c"` pick one half,
 * `"both"` / `"1"` / null both (the default), `"0"` / `"off"` neither (the 6c path, byte-identical).
 * Alpha-to-coverage is only ever asked for when the target is multisampled: without MSAA the
 * coverage mask has one sample and the ramp would quantise back to the hard cut it replaces.
 */
export const IMP_EDGE = { premul: true, a2c: true };
export function parseImpEdge( v, msaa = true ) {
	let d = { ...IMP_EDGE };
	const s = ( v === null || v === undefined ) ? '' : String( v ).trim().toLowerCase();
	if ( s === '0' || s === 'off' || s === 'none' ) d = { premul: false, a2c: false };
	else if ( s === 'premul' ) d = { premul: true, a2c: false };
	else if ( s === 'a2c' ) d = { premul: false, a2c: true };
	else if ( s === 'both' || s === '1' || s === 'on' || s === '' ) d = { ...IMP_EDGE };
	return { premul: d.premul, a2c: d.a2c && !! msaa, a2cAsked: d.a2c, msaa: !! msaa };
}

/**
 * One InstancedMesh per prototype, built from `manifest.gate3.impostors` and `manifest.trees.far`.
 * @returns {{ group:THREE.Group|null, report:object }}
 */
export function buildImpostors( { impostors, far, near = [], loadTexture, note = () => {}, fog = null,
	normalDepth = false, debug = 0, atlas2k = false, switchUniforms = null, interior = null,
	edge = null, msaa = false } ) {
	// 6c round 3: (strength, radius in frame UV, Phase 7 floor).  `?impint=` — see the fragment shader.
	const impInterior = parseImpInterior( interior );
	// Phase 7 item A: `?impedge=` — see the header.
	const impEdge = parseImpEdge( edge, msaa );
	const report = { prototypes: 0, instances: 0, nearInstances: 0, drawCalls: 0, skipped: [], bytes: 0,
		unmappedPrototypes: [], missingPrototypes: [], textures: 0, normalDepthLoaded: 0,
		atlas2k: false, atlas2kMissing: [], modulated: 0,
		// the atlas geometry that ACTUALLY draws, so the summary can never name the 1K one while the
		// 2K variant is on screen (round-1 review 5)
		interior: { strength: impInterior[ 0 ], radius_uv: impInterior[ 1 ], floor: impInterior[ 2 ] },
		edge: { premultiplied: impEdge.premul, alphaToCoverage: impEdge.a2c,
			alphaToCoverageAsked: impEdge.a2cAsked, msaa: impEdge.msaa },
		drawnGeom: { framePx: impostors.framePx, atlasPx: impostors.atlasPx, innerPx: impostors.innerPx } };
	if ( ! impostors || ! impostors.count ) return { group: null, report };
	far = [ ...( Array.isArray( far ) ? far : [] ), ...( Array.isArray( near ) ? near : [] ) ];
	if ( ! far.length ) return { group: null, report };
	// 6c C2: the 2K variant on desktop.  `variant_2k` re-states the geometry of the atlas (frame,
	// gutter, inner), so it is READ from the manifest exactly as the 1K block is and never scaled by
	// hand; a prototype missing a 2K texture keeps its 1K one AND its 1K geometry.
	const v2k = atlas2k ? impostors.variant2k : null;

	// tree_far[i].prototype joins through prototype_map: 46 of the 127 were exported against an LOD2
	// blob and every impostor is baked from the LOD1 mesh, which is why the map exists.
	const byProto = new Map();
	for ( const t of far ) {
		// `far` is manifest.treesFar: { prototype, id, height, width, base } - the normalised shape,
		// so tree_far's own key names live in manifest.js and nowhere else.
		const key = impostors.prototypeMap[ t.prototype ] || t.prototype;
		const p = impostors.prototypes[ key ];
		if ( ! p ) {
			if ( ! report.missingPrototypes.includes( key ) ) report.missingPrototypes.push( key );
			report.skipped.push( t.id || t.prototype );
			continue;
		}
		if ( ! ( p.heightAboveBase > 0 ) || ! ( p.radius > 0 ) || ! ( p.range > 0 )
			|| ! Array.isArray( t.base ) || ! ( t.height > 0 ) ) {
			report.skipped.push( t.id || t.prototype );
			continue;
		}
		if ( ! byProto.has( key ) ) byProto.set( key, [] );
		byProto.get( key ).push( t );
	}

	const group = new THREE.Group();
	group.name = 'WEB_impostors';
	const geo = new THREE.PlaneGeometry( 1, 1 );      // unit square, expanded in the vertex shader
	const IDENTITY = new THREE.Matrix4();
	const pending = [];

	for ( const [ key, list ] of byProto ) {
		const p = impostors.prototypes[ key ];
		const defines = fog ? { PFA_FOG: '' } : {};
		if ( impEdge.premul ) defines.PFA_IMP_PREMUL = '';
		if ( impEdge.a2c ) defines.PFA_IMP_A2C = '';
		// 2K only where BOTH the variant geometry and this prototype's 2K texture exist.
		const use2k = !! ( v2k && p.albedo2k );
		if ( atlas2k && ! use2k && ! report.atlas2kMissing.includes( key ) ) report.atlas2kMissing.push( key );
		const geom = use2k ? v2k : impostors;
		if ( use2k ) report.drawnGeom = { framePx: geom.framePx, atlasPx: geom.atlasPx, innerPx: geom.innerPx };
		const uniforms = {
			atlas: { value: null },
			range: { value: p.range },
			grid: { value: impostors.grid },
			framePx: { value: geom.framePx },
			innerPx: { value: geom.innerPx },
			gutterPx: { value: geom.gutterPx },
			atlasPx: { value: geom.atlasPx },
			alphaTest: { value: ALPHA_TEST },
			debugMode: { value: debug },
			pfaImpInterior: { value: new THREE.Vector3( impInterior[ 0 ], impInterior[ 1 ], impInterior[ 2 ] ) },
			pfaMeshDist: switchUniforms ? switchUniforms.pfaMeshDist : { value: 1e9 },
			pfaFadeBand: switchUniforms ? switchUniforms.pfaFadeBand : { value: 1 },
		};
		if ( fog ) Object.assign( uniforms, {
			fogColor: { value: fog.color }, fogNear: { value: fog.near }, fogFar: { value: fog.far },
			fogCap: { value: fog.cap }, fogK: { value: fog.k }, fogIntensity: { value: fog.intensity || 0 },
		} );
		const mat = new THREE.ShaderMaterial( {
			name: `MAT_WEB_impostor_${key}`,
			vertexShader, fragmentShader, uniforms, defines,
			transparent: false,            // alpha TEST, so they write depth and need no sorting
			depthWrite: true, depthTest: true, side: THREE.DoubleSide,
			// Phase 7 item A2: opaque queue, opaque depth, and the coverage mask resolved by the
			// target's own four samples.  three reads this flag straight into
			// gl.SAMPLE_ALPHA_TO_COVERAGE, so nothing else about the draw changes.
			alphaToCoverage: impEdge.a2c,
		} );
		const g = geo.clone();
		const im = new THREE.InstancedMesh( g, mat, list.length );
		im.name = `WEB_impostor_${key}`;
		im.frustumCulled = false;          // the quad is built in the shader; the bbox is not the geometry's
		im.instanceMatrix.setUsage( THREE.StaticDrawUsage );
		const centre = new Float32Array( list.length * 3 );
		const side = new Float32Array( list.length );
		const swtch = new Float32Array( list.length * 3 );
		const nearFlag = new Float32Array( list.length );
		const switchDist = new Float32Array( list.length );
		const irr = new Float32Array( list.length * 3 ).fill( 1 );
		let nearHere = 0, modHere = 0;
		list.forEach( ( t, i ) => {
			// placement, in BLENDER coordinates, then converted once
			const s = t.height / p.heightAboveBase;
			const [ bx, by, bz ] = t.base;
			const c = b2t( bx, by, bz + p.centreZ * s );
			centre[ i * 3 ] = c.x; centre[ i * 3 + 1 ] = c.y; centre[ i * 3 + 2 ] = c.z;
			side[ i ] = 2 * p.radius * s;
			// 6c C2: a tree that also has a MESH fades between the two; one that does not is always
			// the impostor.  The switch distance is measured to the CROWN centre the mesh side uses,
			// never to the billboard centre, or the two dissolves would cross at different metres.
			const sw = ( t.near && Array.isArray( t.switchCentre ) ) ? t.switchCentre : null;
			if ( sw ) { swtch[ i * 3 ] = sw[ 0 ]; swtch[ i * 3 + 1 ] = sw[ 1 ]; swtch[ i * 3 + 2 ] = sw[ 2 ]; nearFlag[ i ] = 1; nearHere ++; }
			else { swtch[ i * 3 ] = c.x; swtch[ i * 3 + 1 ] = c.y; swtch[ i * 3 + 2 ] = c.z; }
			if ( Array.isArray( t.irr ) && t.irr.length === 3 && t.irr.every( ( x ) => x > 0 && isFinite( x ) ) ) {
				irr[ i * 3 ] = t.irr[ 0 ]; irr[ i * 3 + 1 ] = t.irr[ 1 ]; irr[ i * 3 + 2 ] = t.irr[ 2 ]; modHere ++;
			}
			im.setMatrixAt( i, IDENTITY );              // identity: the shader does the placing
		} );
		report.nearInstances += nearHere;
		report.modulated += modHere;
		g.setAttribute( 'iCentre', new THREE.InstancedBufferAttribute( centre, 3 ) );
		g.setAttribute( 'iSide', new THREE.InstancedBufferAttribute( side, 1 ) );
		g.setAttribute( 'iSwitch', new THREE.InstancedBufferAttribute( swtch, 3 ) );
		g.setAttribute( 'iNear', new THREE.InstancedBufferAttribute( nearFlag, 1 ) );
		g.setAttribute( 'iDist', new THREE.InstancedBufferAttribute( switchDist, 1 ) );
		g.setAttribute( 'iIrr', new THREE.InstancedBufferAttribute( irr, 3 ) );
		im.userData.pfaImpostor = { prototype: key, instances: list.length, near: nearHere, range: p.range,
			radius_m: p.radius, height_above_base_m: p.heightAboveBase, centre_z_m: p.centreZ, atlas2k: use2k,
			// 6c round 2: gltfpack drops node names, so the id (the billboard name) is the only key that
			// joins a row of this batch to a placement of the lazily loaded env_trees.glb.
			ids: list.map( ( t ) => t.id || null ) };
		group.add( im );
		report.prototypes ++;
		report.instances += list.length;
		report.drawCalls ++;
		report.bytes += p.bytes || 0;

		// A manifest with no declared 2K byte count must KEEP the 1K figure, not subtract it (carry 6).
		if ( use2k ) { report.atlas2k = true; if ( p.bytes2k ) report.bytes += p.bytes2k - ( p.bytes || 0 ); }
		pending.push( loadTexture( use2k ? p.albedo2k : p.albedo ).then( ( tex ) => {
			if ( ! tex ) { note( `impostor ${key}: albedo atlas failed to load` ); return; }
			// The atlas holds LINEAR radiance behind a gamma-2 code, not sRGB: the decode is in the
			// shader, so the sampler must not decode anything.
			tex.colorSpace = THREE.NoColorSpace;
			tex.flipY = false;
			tex.wrapS = tex.wrapT = THREE.ClampToEdgeWrapping;
			tex.minFilter = THREE.LinearFilter;         // NO mips: a mip would blend across frames
			tex.magFilter = THREE.LinearFilter;
			tex.generateMipmaps = false;
			tex.anisotropy = 1;
			tex.needsUpdate = true;
			mat.uniforms.atlas.value = tex;
			mat.needsUpdate = true;
			report.textures ++;
		} ).catch( ( e ) => note( `impostor ${key}: ${e.message}` ) ) );

		if ( normalDepth && p.normalDepth ) {
			pending.push( loadTexture( p.normalDepth ).then( () => { report.normalDepthLoaded ++; } ).catch( () => {} ) );
		}
	}

	report.promise = Promise.all( pending ).then( () => {
		if ( report.modulated ) note( `impostors: ${report.modulated}/${report.instances} placement(s) carry an `
			+ `E_placement / E_bake modulation (?impmod=0 reverts); the rest draw the atlas radiance unchanged` );
		if ( report.nearInstances ) note( `impostors: ${report.nearInstances} of them are NEAR trees that also have a mesh `
			+ `(6c C2): they dissolve into their mesh inside the switch distance and the mesh dissolves into them beyond it` );
		if ( atlas2k ) note( `impostor atlas: 2K variant on ${report.atlas2k ? report.prototypes - report.atlas2kMissing.length : 0}/${report.prototypes} prototype(s)`
			+ ( report.atlas2kMissing.length ? `; 1K kept on ${report.atlas2kMissing.join( ', ' )} (no albedo_2k in the manifest)` : '' ) );
		note( `impostors: ${report.instances} tree(s) (${report.instances - report.nearInstances} far + ${report.nearInstances} near) `
			+ `over ${report.prototypes} prototype(s), `
			+ `${report.drawCalls} draw call(s), ${impostors.grid}x${impostors.grid} octahedral frames `
			+ `at ${report.drawnGeom.framePx} px on a ${report.drawnGeom.atlasPx} px atlas`
			+ ( report.atlas2k ? ' (the 2K variant, ?imp2k=0 reverts)' : '' ) + ', 3-frame barycentric blend, '
			+ `alpha test ${ALPHA_TEST}, unlit (the atlas is baked radiance); ${report.textures}/${report.prototypes} atlas(es) loaded, `
			+ `${( report.bytes / 1048576 ).toFixed( 1 )} MB declared`
			+ ( report.normalDepthLoaded ? `, ${report.normalDepthLoaded} normal+depth atlas(es) loaded (?impnd=1)`
				: ', normal+depth NOT loaded (the manifest says nothing samples it while unlit holds)' ) );
		note( `impostor edge (Phase 7 A): premultiplied 12-tap reconstruction ${impEdge.premul ? 'ON' : 'off'}, `
			+ `alpha-to-coverage ${impEdge.a2c ? 'ON' : ( impEdge.a2cAsked ? 'asked but OFF (no multisampled target)' : 'off' )}`
			+ ` (?impedge=0|premul|a2c|both); interior floor ${impInterior[ 2 ].toFixed( 2 )} of the card's own `
			+ `radiance (?impint=str,radius,floor)` );
		if ( report.missingPrototypes.length )
			note( `impostors: ${report.missingPrototypes.length} prototype(s) in trees.far have no atlas: ${report.missingPrototypes.join( ', ' )}` );
		if ( report.skipped.length ) note( `impostors: ${report.skipped.length} far tree(s) skipped` );
		return report;
	} );
	return { group, report };
}


/**
 * 6c round 2 — the far trees gain a MESH after the impostors were built (env_trees.glb is loaded
 * lazily, after the first frame).  This flips those placements from "impostor for ever" (iNear = 0)
 * to "impostor only beyond pfaMeshDist" (iNear = 1) and gives each one the crown centre the MESH
 * side switches on, so the two dissolves stay exact complements - the same rule the near trees
 * already follow.  `byId`: billboard name -> { switchCentre: [x,y,z] (three space), irr?: [r,g,b] }.
 */
export function activateImpostorMeshes( group, byId, note = () => {} ) {
	const out = { placements: 0, modulated: 0, batches: 0, unmatched: 0 };
	if ( ! group || ! byId || ! byId.size ) return out;
	group.traverse( ( im ) => {
		const d = im.userData && im.userData.pfaImpostor;
		if ( ! im.isInstancedMesh || ! d || ! d.ids ) return;
		const g = im.geometry;
		const near = g.getAttribute( 'iNear' ), sw = g.getAttribute( 'iSwitch' ), irr = g.getAttribute( 'iIrr' );
		const dist = g.getAttribute( 'iDist' );
		if ( ! near || ! sw ) return;
		let touched = 0;
		d.ids.forEach( ( id, i ) => {
			const rec = id ? byId.get( id ) : null;
			if ( ! rec ) return;
			near.array[ i ] = 1;
			if ( dist && rec.dist > 0 ) dist.array[ i ] = rec.dist;
			sw.array[ i * 3 ] = rec.switchCentre[ 0 ];
			sw.array[ i * 3 + 1 ] = rec.switchCentre[ 1 ];
			sw.array[ i * 3 + 2 ] = rec.switchCentre[ 2 ];
			if ( irr && Array.isArray( rec.irr ) && rec.irr.length === 3
				&& rec.irr.every( ( x ) => isFinite( x ) && x > 0 ) ) {
				irr.array[ i * 3 ] = rec.irr[ 0 ]; irr.array[ i * 3 + 1 ] = rec.irr[ 1 ]; irr.array[ i * 3 + 2 ] = rec.irr[ 2 ];
				out.modulated ++;
			}
			touched ++; out.placements ++;
		} );
		if ( touched ) {
			near.needsUpdate = true; sw.needsUpdate = true; if ( irr ) irr.needsUpdate = true;
			if ( dist ) dist.needsUpdate = true;
			d.near += touched; out.batches ++;
		}
	} );
	out.unmatched = byId.size - out.placements;
	note( `far-tree impostors: ${out.placements} placement(s) over ${out.batches} batch(es) now fade to a MESH `
		+ `(iNear = 1)${out.modulated ? `, ${out.modulated} re-lit by E_placement / E_bake` : ''}`
		+ ( out.unmatched ? `; ${out.unmatched} mesh placement(s) matched no impostor row` : '' ) );
	return out;
}
