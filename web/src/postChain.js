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

export const MIST_NEAR_M = 60;         // viewer's own: see above
export const MIST_FAR_M = 1400;        // ~ the backdrop distance

let fogChunkPatched = false;

/**
 * Blender's haze is `mix( image, hazeColor, mist^falloff * strength )`; three's own fog chunk goes to
 * a FULL mix at `fogFar`, which at this site would bury the backdrop.  The chunk is replaced once,
 * with the falloff exponent and the strength ceiling as compile-time constants.
 */
function patchFogChunk( strength, falloff ) {
	if ( fogChunkPatched ) return;
	fogChunkPatched = true;
	THREE.ShaderChunk.fog_fragment = /* glsl */`
#ifdef USE_FOG
	float pfaMist = clamp( ( vFogDepth - fogNear ) / ( fogFar - fogNear ), 0.0, 1.0 );
	gl_FragColor.rgb = mix( gl_FragColor.rgb, fogColor, pow( pfaMist, ${falloff.toFixed( 3 )} ) * ${strength.toFixed( 5 )} );
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
		group: g.group || 'COMP_golden_hour',
	};
}

/**
 * Distance fog with the compositor's haze colour.  Returns what it did, or null when off.
 * The fog colour is the haze colour as exported (scene-linear, and well above 1.0 - it is a light,
 * not an sRGB swatch), so it goes in unclamped and the LUT does the rest.
 */
export function applyMist( scene, comp, { near = MIST_NEAR_M, far = MIST_FAR_M } = {} ) {
	if ( ! comp || comp.hazeStrength <= 0 ) return null;
	patchFogChunk( comp.hazeStrength, comp.hazeFalloff );
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
	return { near, far, strength: comp.hazeStrength, falloff: comp.hazeFalloff, color: comp.hazeColor };
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
	const s = String( spec ?? 'all' ).trim().toLowerCase();
	if ( s === 'all' || s === '1' || s === '' ) return on;
	if ( s === 'none' || s === '0' ) return { mist: false, bloom: false, vignette: false };
	const want = new Set( s.split( ',' ).map( x => x.trim() ).filter( Boolean ) );
	return { mist: want.has( 'mist' ), bloom: want.has( 'bloom' ), vignette: want.has( 'vignette' ) };
}
