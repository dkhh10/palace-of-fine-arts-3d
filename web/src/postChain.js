// Gate 4 item 4: the Phase 5 compositor, reproduced in the viewer's linear pass, each part switchable.
//
// `manifest.compositor.COMP_golden_hour` is the Blender group the Phase 5 frames were finished with.
// The manifest carries the group's PARAMETERS but not its internals, so what is reproduced here is the
// documented effect of each parameter, in the same place in the chain (scene-linear, BEFORE the AgX
// LUT), and every one is measured on the hero's acceptance boxes with it on and off:
//
//   Haze Color / Strength / Falloff   -> distance fog, per fragment, on the scene's own materials
//   Bloom Threshold / Strength / Size -> UnrealBloomPass on the linear buffer
//   Vignette                          -> in the LUT pass, before the transform
//
// THE ONE THING THAT IS NOT IN THE MANIFEST: Blender's Mist pass normalises distance by
// `world.mist_settings.start` and `.depth`, and neither is exported - the compositor block records the
// group's `Mist` INPUT as 0.0, not the settings that produced it.  The two numbers below are therefore
// the viewer's own, stated in the notes and overridable with `?mist=near,far`; they are the only
// invented values in the display chain and the export should supply the real ones.
import * as THREE from 'three';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';

// Kept only as the ?mist= escape hatch's defaults; NEVER used when the manifest states the real ones.
export const MIST_NEAR_M = 60;
export const MIST_FAR_M = 1400;

let fogChunkPatched = false;

/** The mist pass's own shaping, from `compositor.mist.falloff`. */
export function mistShapeGlsl( falloff ) {
	const f = String( falloff || 'LINEAR' ).toUpperCase();
	if ( f === 'QUADRATIC' ) return 't * t';
	if ( f === 'INVERSE_QUADRATIC' ) return 'sqrt( t )';
	return 't';                                  // LINEAR, which is what this scene uses
}

/**
 * COMP_golden_hour's haze, exactly as `scripts/light_build.py` builds it - NOT a power curve.
 *
 *   mist     = clamp( ( dist - start ) / depth, 0, 1 ), shaped by compositor.mist.falloff, then
 *              intensity + (1 - intensity) * t.  `dist` is measured ALONG THE VIEW RAY in metres,
 *              which is why fog_vertex below uses length( mvPosition.xyz ) and not three's -z.
 *   airlight = cap * ( 1 - exp( -k * mist ) )    cap = "Haze Strength" (0.25), k = "Haze Falloff" (5.0)
 *   out      = mix( image, hazeColor, clamp( airlight, 0, 1 ) )
 *
 * `Haze Falloff` is the EXTINCTION COEFFICIENT k, not an exponent: L = depth / k = 400 m here.  The
 * viewer's first attempt read it as an exponent (`mist^5 * 0.25`), which is ~0 near the camera where
 * the truth is cap*k*mist = 1.25*mist - the 5x error the review predicted, and it is why the mist
 * measured as a no-op at the hero.
 *
 * The compositor also masks the haze off the BACKGROUND (`Depth < 4000`) because the sky model
 * already carries it.  Here that is free: fog lives in the scene materials and the sky is the
 * background, which runs no material.
 */
function patchFogChunk( cap, k, shapeGlsl, intensity ) {
	if ( fogChunkPatched ) return;
	fogChunkPatched = true;
	THREE.ShaderChunk.fog_vertex = /* glsl */`
#ifdef USE_FOG
	vFogDepth = length( mvPosition.xyz );   // along the VIEW RAY, as Blender's mist pass measures it
#endif`;
	THREE.ShaderChunk.fog_fragment = /* glsl */`
#ifdef USE_FOG
	float t = clamp( ( vFogDepth - fogNear ) / max( fogFar - fogNear, 1e-6 ), 0.0, 1.0 );
	float pfaMist = ${intensity.toFixed( 5 )} + ( 1.0 - ${intensity.toFixed( 5 )} ) * ( ${shapeGlsl} );
	float pfaAir = ${cap.toFixed( 5 )} * ( 1.0 - exp( - ${k.toFixed( 5 )} * pfaMist ) );
	gl_FragColor.rgb = mix( gl_FragColor.rgb, fogColor, clamp( pfaAir, 0.0, 1.0 ) );
#endif`;
}

/** The compositor block, with every value it does not carry made explicit. */
export function readCompositor( raw ) {
	const g = raw && raw.COMP_golden_hour;
	if ( ! g ) return null;
	const c = g[ 'Haze Color' ] || [ 1, 1, 1, 1 ];
	return {
		hazeColor: [ c[ 0 ], c[ 1 ], c[ 2 ] ],
		hazeStrength: g[ 'Haze Strength' ] ?? 0,
		hazeFalloff: g[ 'Haze Falloff' ] ?? 1,
		bloomThreshold: g[ 'Bloom Threshold' ] ?? 1,
		bloomStrength: g[ 'Bloom Strength' ] ?? 0,
		bloomSize: g[ 'Bloom Size' ] ?? 0.5,
		vignette: g.Vignette ?? 0,
		// Blender's Mist pass normalisation, which the group's parameters alone do not carry.
		mist: ( raw && raw.mist ) || g.mist || null,
		group: g.group || 'COMP_golden_hour',
	};
}

/**
 * Distance fog with the compositor's haze colour.  Returns what it did, or null when off.
 * The fog colour is the haze colour as exported (scene-linear, and well above 1.0 - it is a light,
 * not an sRGB swatch), so it goes in unclamped and the LUT does the rest.
 */
export function applyMist( scene, comp, { near = null, far = null, allowInvented = false } = {} ) {
	if ( ! comp || comp.hazeStrength <= 0 ) return null;
	// The mist is REFUSED until the manifest states Blender's own normalisation.  MIST_NEAR_M /
	// MIST_FAR_M were the viewer's invention and must never reach a scored capture (review fix-now 2):
	// `?mist=near,far` is the only way to use them, and it says so in the report it returns.
	const m = comp.mist;
	let invented = false;
	if ( near === null || far === null ) {
		if ( m && typeof m.start === 'number' && typeof m.depth === 'number' && m.use_mist !== false ) {
			near = m.start; far = m.start + m.depth;
		} else if ( allowInvented ) {
			near = MIST_NEAR_M; far = MIST_FAR_M; invented = true;
		} else {
			return { refused: 'compositor.mist is not in the manifest (world.mist_settings.start/depth/falloff); '
				+ 'the viewer will not invent a normalisation for a scored capture. ?mist=near,far overrides.' };
		}
	} else invented = true;
	const shape = mistShapeGlsl( m && m.falloff );
	const intensity = ( m && typeof m.intensity === 'number' ) ? m.intensity : 0;
	if ( m && m.height ) return { refused: `compositor.mist.height = ${m.height} fades the mist above that world z; `
		+ 'the viewer does not implement the height fade and will not approximate it' };
	// cap = Haze Strength, k = Haze Falloff (the EXTINCTION COEFFICIENT, not an exponent)
	patchFogChunk( comp.hazeStrength, comp.hazeFalloff, shape, intensity );
	const col = new THREE.Color().setRGB( ...comp.hazeColor, THREE.LinearSRGBColorSpace );
	scene.fog = new THREE.Fog( col, near, far );
	// three only compiles the fog chunk into a material that asks for it
	scene.traverse( ( o ) => {
		if ( ! o.isMesh ) return;
		for ( const m of Array.isArray( o.material ) ? o.material : [ o.material ] ) {
			if ( ! m || m.fog === true || /^WATER_/.test( o.name || '' ) ) continue;
			m.fog = true; m.needsUpdate = true;
		}
	} );
	return { near, far, cap: comp.hazeStrength, k: comp.hazeFalloff, shape: ( m && m.falloff ) || 'LINEAR',
		intensity, extinctionLength_m: ( far - near ) / comp.hazeFalloff, color: comp.hazeColor,
		// kept under the old names so the impostor material and the sidecar keep reading one shape
		strength: comp.hazeStrength, falloff: comp.hazeFalloff,
		invented, source: invented ? 'the viewer (?mist= or the placeholder constants)' : 'manifest compositor.mist' };
}

export function removeMist( scene ) {
	scene.fog = null;
	scene.traverse( ( o ) => {
		if ( ! o.isMesh ) return;
		for ( const m of Array.isArray( o.material ) ? o.material : [ o.material ] ) {
			if ( m && m.fog ) { m.fog = false; m.needsUpdate = true; }
		}
	} );
}

/**
 * Bloom on the LINEAR buffer, which is where Blender's is: the threshold is a scene-linear radiance
 * (6.41 here), not a display value, so it only ever catches the sun-facing highlights.
 */
export function makeBloom( comp, size ) {
	if ( ! comp || comp.bloomStrength <= 0 ) return null;
	const pass = new UnrealBloomPass( new THREE.Vector2( size.w, size.h ),
		comp.bloomStrength, comp.bloomSize, comp.bloomThreshold );
	pass.name = 'PFA_bloom';
	return pass;
}

/** Which parts of the chain `?post=` asks for. `all` / `none` / a comma list of mist,bloom,vignette. */
export function parsePost( spec ) {
	const on = { mist: true, bloom: true, vignette: true };
	const off = { mist: false, bloom: false, vignette: false };
	// ONLY AN ABSENT PARAMETER MAY MEAN "the default".  `screenshot.mjs --query post=` emits an EMPTY
	// value, and treating that as `all` would switch the invented mist on inside a scored capture
	// (review fix-now 2).  An empty or unrecognised value is therefore `none`, never `all`.
	if ( spec === undefined || spec === null ) return off;
	const s = String( spec ).trim().toLowerCase();
	if ( s === '' ) return off;
	if ( s === 'all' || s === '1' ) return on;
	if ( s === 'none' || s === '0' ) return off;
	const want = new Set( s.split( ',' ).map( x => x.trim() ).filter( Boolean ) );
	if ( ! want.size ) return off;
	return { mist: want.has( 'mist' ), bloom: want.has( 'bloom' ), vignette: want.has( 'vignette' ) };
}
