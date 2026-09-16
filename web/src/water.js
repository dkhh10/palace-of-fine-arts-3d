// Lagoon water: a planar Reflector at y = WATER_Z with a ripple normal map, murk tint and Fresnel.
// Not a mirror (attempts 1-2 failed on that): the reflection is broken up by the ripple normal and
// mixed toward a murky green by a Schlick Fresnel term, so only grazing angles read as reflective.
import * as THREE from 'three';
import { Reflector } from 'three/addons/objects/Reflector.js';

/** Small tileable ripple normal map, generated so the viewer needs no texture asset for it. */
export function makeRippleNormalMap( size = 256, waves = 14 ) {
	const h = new Float32Array( size * size );
	const rnd = ( s => () => ( s = ( s * 1664525 + 1013904223 ) >>> 0 ) / 4294967296 )( 12345 );
	for ( let w = 0; w < waves; w ++ ) {
		const kx = Math.round( ( rnd() * 6 ) - 3 ) || 1, ky = Math.round( ( rnd() * 6 ) - 3 ) || 1;
		const amp = 1 / ( 1 + Math.hypot( kx, ky ) ), ph = rnd() * Math.PI * 2;
		for ( let y = 0; y < size; y ++ ) for ( let x = 0; x < size; x ++ ) {
			h[ y * size + x ] += amp * Math.sin( 2 * Math.PI * ( kx * x / size + ky * y / size ) + ph );
		}
	}
	const data = new Uint8Array( size * size * 4 );
	const at = ( x, y ) => h[ ( ( y + size ) % size ) * size + ( ( x + size ) % size ) ];
	for ( let y = 0; y < size; y ++ ) for ( let x = 0; x < size; x ++ ) {
		const dx = ( at( x + 1, y ) - at( x - 1, y ) ) * 0.5, dy = ( at( x, y + 1 ) - at( x, y - 1 ) ) * 0.5;
		const n = new THREE.Vector3( - dx, - dy, 1 ).normalize();
		const i = ( y * size + x ) * 4;
		data[ i ] = ( n.x * 0.5 + 0.5 ) * 255; data[ i + 1 ] = ( n.y * 0.5 + 0.5 ) * 255;
		data[ i + 2 ] = ( n.z * 0.5 + 0.5 ) * 255; data[ i + 3 ] = 255;
	}
	const tex = new THREE.DataTexture( data, size, size );
	tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
	tex.minFilter = THREE.LinearMipmapLinearFilter;
	tex.magFilter = THREE.LinearFilter;
	tex.generateMipmaps = true;
	tex.needsUpdate = true;
	return tex;
}

const WaterShader = {
	uniforms: {
		color: { value: null }, tDiffuse: { value: null }, textureMatrix: { value: null },
		tNormal: { value: null }, time: { value: 0 }, distortion: { value: 0.035 },
		murk: { value: new THREE.Color( 0.020, 0.035, 0.030 ) },
		reflectTint: { value: new THREE.Color( 0.88, 0.94, 0.90 ) },
		normalScale: { value: 0.06 }, rippleTiling: { value: 0.09 },
		distortAniso: { value: 1.0 },
		// A ROUGH surface at a grazing angle does not reflect a point - its lobe is stretched toward
		// the HORIZON, so the near water carries the bright near-horizon band rather than the dark
		// zenith a mirror gives it.  That, not the murk, is why the reference's open water is bright
		// (lum 118) and nearly neutral (sat 0.041) while a mirror reads dark blue (66.8, sat 0.326).
		horizonBias: { value: 0.0 },
		// grazingGain 0 reproduces the round14 surface EXACTLY (the displacement is then n.xy *
		// distortion, as it was).  Every term added for QA-14-1 is opt-in until one is agreed, so the
		// shipped look cannot drift while the fix is still being searched for.
		grazingGain: { value: 0.0 },
		// A real lagoon is a ROUGH, murky surface, not a mirror.  Two terms carry that, both
		// calibrated against the Phase 5 Cycles hero's water box (docs/qa_round_10b.md
		// 900 760 1020 840: lum 128.6, std 34.2, sat 0.33, R-B +34.4) - see makeWater().
		//   reflBlur   the slope distribution of the ripples: the reflection is gathered over a
		//              small disc instead of a point, which is what takes the edge off `std`.
		//   reflSat    the murk scatters light back out through the reflected ray, washing its
		//              colour toward neutral.  1.0 = a clean mirror.
		reflBlur: { value: 0.0 }, reflSat: { value: 1.0 },
		// QA-14-1 diagnostics: 1 = Fresnel F, 2 = the projected reflection uv, 3 = the perturbed
		// normal's xy, 4 = the raw reflection sample, 5 = |ripple offset| in screen units.
		debugMode: { value: 0 },
	},
	vertexShader: /* glsl */`
		uniform mat4 textureMatrix;
		varying vec4 vProjUv;
		varying vec3 vWorld;
		void main() {
			vec4 wp = modelMatrix * vec4( position, 1.0 );
			vWorld = wp.xyz;
			vProjUv = textureMatrix * vec4( position, 1.0 );
			gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
		}
	`,
	fragmentShader: /* glsl */`
		uniform sampler2D tDiffuse, tNormal;
		uniform float time, distortion, normalScale, rippleTiling, reflBlur, reflSat, distortAniso, horizonBias, grazingGain;
		uniform int debugMode;
		uniform vec3 murk, reflectTint;
		varying vec4 vProjUv;
		varying vec3 vWorld;
		void main() {
			vec2 p = vWorld.xz * rippleTiling;
			vec3 n1 = texture2D( tNormal, p + vec2( time * 0.013, time * 0.007 ) ).rgb * 2.0 - 1.0;
			vec3 n2 = texture2D( tNormal, p * 2.7 - vec2( time * 0.009, time * 0.017 ) ).rgb * 2.0 - 1.0;
			vec3 n = normalize( vec3( ( n1.xy + n2.xy ) * normalScale, 1.0 ) );
			vec3 N = normalize( vec3( n.x, n.z, n.y ) );                       // tangent -> world (plane is +Y up)
			// QA-14-1.  A grazing view turns a small surface slope into a LARGE vertical displacement of
			// the reflected ray and a small horizontal one, which is why a real lagoon reads as
			// horizontal streaks (the reference's row/col high-pass ratio is 3.24, a mirror's is ~1).
			// The vertical term is therefore scaled by distortAniso, and both are scaled by 1/c so
			// the displacement grows toward the horizon exactly as the geometry says it should.
			vec4 uv = vProjUv;
			float grazingRaw = clamp( 1.0 / max( dot( normalize( cameraPosition - vWorld ), N ), 0.02 ), 1.0, 40.0 );
			float grazing = mix( 1.0, grazingRaw, grazingGain );
			uv.x += n.x * distortion * grazing * uv.w;
			uv.y += ( n.y * distortion * distortAniso + horizonBias ) * grazing * uv.w;
			// gather over a small disc: the ripple slopes spread the reflected ray
			vec3 refl = texture2DProj( tDiffuse, uv ).rgb;
			if ( reflBlur > 0.0 ) {
				float b = reflBlur * uv.w;
				refl += texture2DProj( tDiffuse, uv + vec4(  b,  0.0, 0.0, 0.0 ) ).rgb;
				refl += texture2DProj( tDiffuse, uv + vec4( -b,  0.0, 0.0, 0.0 ) ).rgb;
				refl += texture2DProj( tDiffuse, uv + vec4( 0.0,  b * 0.5, 0.0, 0.0 ) ).rgb;
				refl += texture2DProj( tDiffuse, uv + vec4( 0.0, -b * 0.5, 0.0, 0.0 ) ).rgb;
				refl *= 0.2;
			}
			refl *= reflectTint;
			// the murk scatters the reflection's colour toward neutral
			refl = mix( vec3( dot( refl, vec3( 0.2126, 0.7152, 0.0722 ) ) ), refl, reflSat );
			vec3 V = normalize( cameraPosition - vWorld );
			float c = clamp( dot( V, N ), 0.0, 1.0 );
			float F = 0.02 + 0.98 * pow( 1.0 - c, 5.0 );                        // water, IOR 1.33
			if ( debugMode == 1 ) { gl_FragColor = vec4( vec3( F ), 1.0 ); return; }
			if ( debugMode == 2 ) { vec2 q = uv.xy / max( uv.w, 1e-6 ); gl_FragColor = vec4( fract( q ), float( q.x < 0.0 || q.x > 1.0 || q.y < 0.0 || q.y > 1.0 ), 1.0 ); return; }
			if ( debugMode == 3 ) { gl_FragColor = vec4( n.xy * 0.5 + 0.5, 0.0, 1.0 ); return; }
			if ( debugMode == 4 ) { gl_FragColor = vec4( texture2DProj( tDiffuse, vProjUv ).rgb, 1.0 ); return; }
			gl_FragColor = vec4( mix( murk, refl, F ), 1.0 );
		}
	`,
};

/**
 * @param {number} waterY  WATER_Z in three space (y)
 * @param {{size?:number, resolution?:number, murk?:number[], tint?:number[], distortion?:number}} o
 */
export function makeWater( waterY, o = {} ) {
	const size = o.size ?? 1200;
	// Item 6: the Reflector renders the WHOLE SCENE a second time into this target - 6.3 ms at the
	// hero, 8.6 ms at the aerial, and it doubles the draw calls.  Halving it is nearly free visually
	// because `reflBlur` already gathers the reflection over a disc.
	// The plane is rotated on the OBJECT, not baked into the geometry: Reflector derives the mirror
	// normal from the object's world rotation (normal = +Z rotated by matrixWorld), so a geometry-baked
	// rotation leaves it reflecting about a vertical plane.
	const geo = new THREE.PlaneGeometry( size, size );
	const reflector = new Reflector( geo, {
		textureWidth: o.resolution ?? 1024,
		textureHeight: o.resolution ?? 1024,
		color: 0xffffff,
		shader: WaterShader,
		clipBias: 0.003,
	} );
	reflector.rotation.x = - Math.PI / 2;
	reflector.position.y = waterY;
	reflector.name = 'WATER_lagoon';
	const u = reflector.material.uniforms;
	u.tNormal.value = makeRippleNormalMap();
	if ( o.murk ) u.murk.value.setRGB( ...o.murk );
	if ( o.tint ) u.reflectTint.value.setRGB( ...o.tint );
	if ( o.distortion !== undefined ) u.distortion.value = o.distortion;
	if ( o.normalScale !== undefined ) u.normalScale.value = o.normalScale;
	if ( o.rippleTiling !== undefined ) u.rippleTiling.value = o.rippleTiling;
	if ( o.distortAniso !== undefined ) u.distortAniso.value = o.distortAniso;
	if ( o.horizonBias !== undefined ) u.horizonBias.value = o.horizonBias;
	if ( o.grazingGain !== undefined ) u.grazingGain.value = o.grazingGain;
	if ( o.murk ) u.murk.value.setRGB( ...o.murk );
	// Calibrated on the Gate 4 capture against the Phase 5 Cycles hero's water box: the mirror-sharp
	// Gate 0 water read std 44.0 against 34.2 and sat 0.69 against 0.33.  ?waterblur / ?watersat
	// move them for the A/B; the defaults are the calibration.
	u.reflBlur.value = o.reflBlur ?? 0.0045;
	u.reflSat.value = o.reflSat ?? 0.66;
	if ( o.debug ) u.debugMode.value = o.debug;
	reflector.userData.tick = ( t ) => { u.time.value = t; };
	return reflector;
}


/** Layer the reflection camera does NOT test; everything on it is excluded from the reflection. */
export const REFLECT_EXCLUDE_LAYER = 2;

/**
 * Item 6: cut the Reflector's DRAW SET, not its resolution.
 *
 * The planar Reflector renders the whole scene a second time - measured at 6.3 ms (hero) and 8.6 ms
 * (aerial), and it doubles the draw calls, 151 -> 301.  Halving its target recovered almost none of
 * that, because the cost is the second scene TRAVERSAL and the submit, not the fill: at half
 * resolution it still submitted all 314 draws.  Cutting what it traverses is the only lever that
 * touches the real cost.
 *
 * three's Reflector clones the MAIN camera to make its reflection camera, so the clone inherits the
 * main camera's layer mask.  This puts the excluded objects on their own layer, enables every layer
 * on the main camera so they still draw normally, and restricts each reflection camera to layer 0.
 *
 * What is cut and why: the 436 ORN instances (sub-pixel in a reflection that `reflBlur` gathers over
 * a disc, at hero distance) and the far backdrop city blocks (140-190 m away and behind the camera's
 * own reflected frustum at the lagoon stations).  ARCH, the ground, the water-adjacent ENV, the
 * impostors and the sky all stay.
 *
 * @returns {{excluded:number, orn:number, backdrop:number, kept:number}}
 */
export function reduceReflectionSet( scene, water, camera, { orn = true, backdrop = true, note = () => {} } = {} ) {
	const out = { excluded: 0, orn: 0, backdrop: 0, kept: 0 };
	if ( ! water || ! water.getReflectionCamera ) return out;
	const rootOf = ( o ) => { let p = o; while ( p && ! /^WEB_glb_/.test( p.name || '' ) ) p = p.parent; return p ? p.name : ''; };
	scene.traverse( ( o ) => {
		if ( ! o.isMesh ) return;
		const mats = Array.isArray( o.material ) ? o.material : [ o.material ];
		const name = mats.map( ( m ) => ( m && m.name ) || '' ).join( ' ' );
		const isOrn = orn && /^WEB_glb_orn$/.test( rootOf( o ) );
		const isBackdrop = backdrop && /MAT_EXP_ENVBD__MAT_backdrop_/.test( name );
		if ( ! isOrn && ! isBackdrop ) { out.kept ++; return; }
		o.layers.set( REFLECT_EXCLUDE_LAYER );        // off layer 0, so the reflection camera misses it
		out.excluded ++;
		if ( isOrn ) out.orn ++; else out.backdrop ++;
	} );
	if ( camera ) camera.layers.enableAll();          // the MAIN camera still draws everything

	// Every reflection camera is a clone of a main camera, made lazily and cached per camera, so the
	// restriction has to be applied to each one as it appears - a station change makes a new camera.
	if ( ! water.userData.pfaReflectionLayersPatched ) {
		water.userData.pfaReflectionLayersPatched = true;
		const base = water.getReflectionCamera.bind( water );
		water.getReflectionCamera = ( cam ) => { const c = base( cam ); c.layers.set( 0 ); return c; };
	}
	note( `reflection draw set reduced: ${out.excluded} mesh(es) excluded (${out.orn} ORN, ${out.backdrop} backdrop), `
		+ `${out.kept} kept (ARCH, ground, water-adjacent ENV, impostors, sky). ?reflset=full restores them.` );
	return out;
}
