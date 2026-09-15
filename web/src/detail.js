// QA-12-1: the concrete grain, as a shared tiling detail layer (manifest v3 `materials.detail`).
//
// WHY IT CANNOT COME FROM THE ATLAS.  The Phase 5 surface is a Bump node with Distance 0.015 m
// evaluated per shading point; the Gate 2 atlas texel is 3.8-11.8 cm, so a baked normal averages the
// grain away (measured by the bake engineer: atlas normal std 0.00205 against the detail map's
// 0.02363, 11.5x).  The bake therefore ships the five tiling sets Phase 5 itself uses — albedo,
// roughness and a tangent normal at 1K over a 1.18-3.15 m tile, 1.05-1.54 mm per texel — and the
// viewer re-creates the layer on top of the baked maps.
//
// WHAT THIS DOES, per the manifest's `apply` rule:
//   albedo     *= detail albedo / its own LINEAR mean    (the mean is measured on the CPU, so the
//   roughness  *= detail roughness / its own mean         baked colour and gloss level survive and
//   normal      = baked normal + the detail normal's tangent-space xy     only the grain is added)
//
// A map whose measured mean is ~0 or whose measured std is below 1/255 is DROPPED, not applied: it
// carries no grain, and as a ratio denominator an empty map turns the surface black.
//
// PROJECTION.  The manifest's rule is `object_position.xy * object_scale` (Blender's Texture
// Coordinate > Object).  Per-instance object space is not recoverable in the viewer: gltfpack folds
// the dequantisation of the quantised positions into the instance matrices, so the shader's
// `position` is not metres and `instanceMatrix` is placement AND dequantisation in one.  The layer
// is therefore tiled in WORLD space at the same tile size, with Blender's xy = three's (x, -z):
//   `objxy`     (default) the manifest's plane, so a vertical face takes the same vertical streaking
//               Phase 5 gives it;
//   `dominant`  the axis-aligned plane most facing the surface, so a wall samples an unsmeared tile.
// World space also breaks the "one atlas per shared mesh" repetition for free: each placement of a
// shared mesh samples a different part of the tile.
import * as THREE from 'three';
import { candidateKeys } from './pbr.js';

function once( src, needle, replacement, what ) {
	const n = src.split( needle ).length - 1;
	if ( n !== 1 ) throw new Error( `detail patch "${what}": expected 1 occurrence, found ${n}` );
	return src.replace( needle, replacement );
}

const PARS = /* glsl */`
varying vec3 vPfaWorld;
uniform sampler2D pfaDetailAlbedo;
uniform sampler2D pfaDetailRough;
uniform sampler2D pfaDetailNormal;
uniform float pfaDetailScale;      // 1 / tile_m
uniform float pfaDetailStrength;
uniform float pfaDetailNormalScale;
uniform vec3 pfaDetailAlbedoMean;  // the map's own LINEAR mean, measured on the CPU
uniform float pfaDetailRoughMean;
vec2 pfaDetailUv() {
	vec3 p = vPfaWorld * pfaDetailScale;
	#if PFA_DETAIL_PROJ == 1
		vec3 n = abs( normalize( cross( dFdx( vPfaWorld ), dFdy( vPfaWorld ) ) ) );
		if ( n.y >= n.x && n.y >= n.z ) return vec2( p.x, - p.z );
		if ( n.x >= n.z ) return vec2( - p.z, p.y );
		return vec2( p.x, p.y );
	#else
		return vec2( p.x, - p.z );
	#endif
}
// three's getTangentFrame, copied so the patch does not depend on the material having a normal map.
mat3 pfaTangentFrame( vec3 eye_pos, vec3 surf_norm, vec2 uv ) {
	vec3 q0 = dFdx( eye_pos.xyz ), q1 = dFdy( eye_pos.xyz );
	vec2 st0 = dFdx( uv.st ), st1 = dFdy( uv.st );
	vec3 N = surf_norm;
	vec3 q1perp = cross( q1, N ), q0perp = cross( N, q0 );
	vec3 T = q1perp * st0.x + q0perp * st1.x;
	vec3 B = q1perp * st0.y + q0perp * st1.y;
	float det = max( dot( T, T ), dot( B, B ) );
	float sc = ( det == 0.0 ) ? 0.0 : inversesqrt( det );
	return mat3( T * sc, B * sc, N );
}
`;

// The world position AFTER the instance matrix: `transformed` is the local vertex, instanceMatrix
// carries both the placement and gltfpack's dequantisation, modelMatrix the glb root's Y-up frame.
const VERT = /* glsl */`
	vec4 pfaW = vec4( transformed, 1.0 );
	#ifdef USE_INSTANCING
		pfaW = instanceMatrix * pfaW;
	#endif
	vPfaWorld = ( modelMatrix * pfaW ).xyz;
`;

const FRAG_ALBEDO = /* glsl */`
	{
		vec2 dUv = pfaDetailUv();
		vec3 dAlb = texture2D( pfaDetailAlbedo, dUv ).rgb;
		diffuseColor.rgb *= mix( vec3( 1.0 ), dAlb / max( pfaDetailAlbedoMean, vec3( 1e-4 ) ), pfaDetailStrength );
	}
`;

const FRAG_ROUGH = /* glsl */`
	{
		vec2 dUv = pfaDetailUv();
		float dR = texture2D( pfaDetailRough, dUv ).g;
		roughnessFactor *= mix( 1.0, dR / max( pfaDetailRoughMean, 1e-4 ), pfaDetailStrength );
		roughnessFactor = clamp( roughnessFactor, 0.03, 1.0 );
	}
`;

const FRAG_NORMAL = /* glsl */`
	{
		vec2 dUv = pfaDetailUv();
		vec3 dN = texture2D( pfaDetailNormal, dUv ).xyz * 2.0 - 1.0;
		mat3 dTBN = pfaTangentFrame( - vViewPosition, normal, dUv );
		normal = normalize( normal + dTBN * vec3( dN.xy * pfaDetailNormalScale * pfaDetailStrength, 0.0 ) );
	}
`;

/** The texture's own mean in LINEAR light, measured on the CPU (every 2nd texel).  The shader
 *  divides by it, so the layer multiplies the baked albedo by 1.0 on average and the baked colour
 *  and brightness survive: a mip-chain average cannot be used for this (glGenerateMipmap averages
 *  an sRGB texture in its stored non-linear space, which biases the ratio). */
export function measureLinearMean( tex, srgb, stride = 2 ) {
	const img = tex.image;
	if ( ! img || ! img.width ) return null;
	const w = img.width, h = img.height;
	let cv;
	try {
		cv = typeof OffscreenCanvas !== 'undefined' ? new OffscreenCanvas( w, h ) : document.createElement( 'canvas' );
		cv.width = w; cv.height = h;
		const ctx = cv.getContext( '2d', { willReadFrequently: true } );
		ctx.drawImage( img, 0, 0 );
		const d = ctx.getImageData( 0, 0, w, h ).data;
		const toLin = ( v ) => { const x = v / 255; return srgb ? ( x <= 0.04045 ? x / 12.92 : Math.pow( ( x + 0.055 ) / 1.055, 2.4 ) ) : x; };
		let r = 0, g = 0, b = 0, n = 0, s8 = 0, s8sq = 0;
		for ( let y = 0; y < h; y += stride ) for ( let x = 0; x < w; x += stride ) {
			const i = ( y * w + x ) * 4;
			r += toLin( d[ i ] ); g += toLin( d[ i + 1 ] ); b += toLin( d[ i + 2 ] ); n ++;
			const v = d[ i + 1 ];                      // the green channel carries the detail in all three maps
			s8 += v; s8sq += v * v;
		}
		if ( ! n ) return null;
		const m8 = s8 / n;
		return { mean: [ r / n, g / n, b / n ], std8: Math.sqrt( Math.max( 0, s8sq / n - m8 * m8 ) ), mean8: m8, samples: n };
	} catch ( e ) { return null; }
}

/** A synthetic stand-in set (`?detailtest=noise`): fractal value noise as a height field, turned
 *  into albedo / roughness / tangent-normal at the same 1K over the same tile.  It exists to prove
 *  the layer end to end when the shipped maps cannot (the Gate 2 set shipped all-zero), and it is
 *  labelled in every report so its numbers are never mistaken for the bake's. */
export function makeNoiseSet( px = 1024, mmPerTexel = 1.05, bumpDistanceM = 0.015 ) {
	const h = new Float32Array( px * px );
	let amp = 1, total = 0;
	for ( let octave = 0, freq = 8; octave < 6; octave ++, freq *= 2, amp *= 0.55 ) {
		const g = new Float32Array( freq * freq );
		for ( let i = 0; i < g.length; i ++ ) g[ i ] = Math.random();
		const sc = px / freq;
		for ( let y = 0; y < px; y ++ ) {
			const fy = y / sc, y0 = Math.floor( fy ) % freq, y1 = ( y0 + 1 ) % freq, ty = fy - Math.floor( fy );
			const wy = ty * ty * ( 3 - 2 * ty );
			for ( let x = 0; x < px; x ++ ) {
				const fx = x / sc, x0 = Math.floor( fx ) % freq, x1 = ( x0 + 1 ) % freq, tx = fx - Math.floor( fx );
				const wx = tx * tx * ( 3 - 2 * tx );
				const a = g[ y0 * freq + x0 ] * ( 1 - wx ) + g[ y0 * freq + x1 ] * wx;
				const b = g[ y1 * freq + x0 ] * ( 1 - wx ) + g[ y1 * freq + x1 ] * wx;
				h[ y * px + x ] += ( a * ( 1 - wy ) + b * wy ) * amp;
			}
		}
		total += amp;
	}
	let mean = 0;
	for ( let i = 0; i < h.length; i ++ ) { h[ i ] /= total; mean += h[ i ]; }
	mean /= h.length;

	const canvas = ( draw ) => {
		const cv = typeof OffscreenCanvas !== 'undefined' ? new OffscreenCanvas( px, px ) : document.createElement( 'canvas' );
		cv.width = px; cv.height = px;
		const ctx = cv.getContext( '2d', { willReadFrequently: true } );
		const img = ctx.createImageData( px, px );
		draw( img.data );
		ctx.putImageData( img, 0, 0 );
		const t = new THREE.CanvasTexture( cv );
		t.needsUpdate = true;
		return t;
	};
	const clamp255 = ( v ) => Math.max( 0, Math.min( 255, Math.round( v ) ) );
	const albedo = canvas( ( d ) => {
		for ( let i = 0, p = 0; i < h.length; i ++, p += 4 ) {
			const v = clamp255( 186 + ( h[ i ] - mean ) * 150 );     // mid grey with the grain on top
			d[ p ] = v; d[ p + 1 ] = v; d[ p + 2 ] = v; d[ p + 3 ] = 255;
		}
	} );
	const rough = canvas( ( d ) => {
		for ( let i = 0, p = 0; i < h.length; i ++, p += 4 ) {
			const v = clamp255( 150 + ( h[ i ] - mean ) * 120 );
			d[ p ] = v; d[ p + 1 ] = v; d[ p + 2 ] = v; d[ p + 3 ] = 255;
		}
	} );
	// the bake's own conversion: slope k = bump distance / metres per texel
	const k = bumpDistanceM / ( mmPerTexel / 1000 );
	const normal = canvas( ( d ) => {
		for ( let y = 0; y < px; y ++ ) for ( let x = 0; x < px; x ++ ) {
			const i = y * px + x, p = i * 4;
			const dx = h[ y * px + ( x + 1 ) % px ] - h[ y * px + ( x + px - 1 ) % px ];
			const dy = h[ ( ( y + 1 ) % px ) * px + x ] - h[ ( ( y + px - 1 ) % px ) * px + x ];
			let nx = - dx * k * 0.5, ny = - dy * k * 0.5, nz = 1;
			const len = Math.hypot( nx, ny, nz );
			nx /= len; ny /= len; nz /= len;
			d[ p ] = clamp255( ( nx * 0.5 + 0.5 ) * 255 );
			d[ p + 1 ] = clamp255( ( ny * 0.5 + 0.5 ) * 255 );
			d[ p + 2 ] = clamp255( ( nz * 0.5 + 0.5 ) * 255 );
			d[ p + 3 ] = 255;
		}
	} );
	return { map: albedo, roughnessMap: rough, normalMap: normal };
}

/** Patch one MeshStandardMaterial with a detail set.  Chains any existing onBeforeCompile. */
export function patchDetailMaterial( mat, tex, rule, opts = {} ) {
	if ( mat.userData.pfaDetail ) return false;
	const proj = opts.projection === 'dominant' ? 1 : 0;
	const uniforms = {
		pfaDetailAlbedo: { value: tex.map || null },
		pfaDetailRough: { value: tex.roughnessMap || null },
		pfaDetailNormal: { value: tex.normalMap || null },
		pfaDetailScale: { value: rule.scale },
		pfaDetailStrength: { value: opts.strength ?? 1.0 },
		pfaDetailNormalScale: { value: opts.normalScale ?? 1.0 },
		pfaDetailAlbedoMean: { value: ( tex.map && tex.map.userData.pfaLinearMean )
			? new THREE.Vector3().fromArray( tex.map.userData.pfaLinearMean ) : new THREE.Vector3( 0.5, 0.5, 0.5 ) },
		pfaDetailRoughMean: { value: ( tex.roughnessMap && tex.roughnessMap.userData.pfaLinearMean )
			? tex.roughnessMap.userData.pfaLinearMean[ 1 ] : 0.5 },
	};
	mat.userData.pfaDetail = { set: rule.set, scale: rule.scale, tile_m: rule.tileM,
		projection: proj ? 'dominant' : 'objxy', strength: uniforms.pfaDetailStrength.value,
		normal_scale: uniforms.pfaDetailNormalScale.value,
		albedo_mean: uniforms.pfaDetailAlbedoMean.value.toArray().map( v => Math.round( v * 1e4 ) / 1e4 ),
		rough_mean: Math.round( uniforms.pfaDetailRoughMean.value * 1e4 ) / 1e4,
		maps: Object.keys( tex ) };
	const prevCompile = mat.onBeforeCompile;
	mat.onBeforeCompile = function ( shader, renderer ) {
		if ( prevCompile ) prevCompile.call( this, shader, renderer );
		Object.assign( shader.uniforms, uniforms );
		shader.vertexShader = `varying vec3 vPfaWorld;\n` + once( shader.vertexShader,
			'#include <project_vertex>', `#include <project_vertex>\n${VERT}`, 'world position' );
		shader.fragmentShader = `#define PFA_DETAIL_PROJ ${proj}\n${PARS}\n` + shader.fragmentShader;
		shader.fragmentShader = once( shader.fragmentShader, '#include <map_fragment>',
			`#include <map_fragment>\n${tex.map ? FRAG_ALBEDO : ''}`, 'detail albedo' );
		shader.fragmentShader = once( shader.fragmentShader, '#include <roughnessmap_fragment>',
			`#include <roughnessmap_fragment>\n${tex.roughnessMap ? FRAG_ROUGH : ''}`, 'detail roughness' );
		shader.fragmentShader = once( shader.fragmentShader, '#include <normal_fragment_maps>',
			`#include <normal_fragment_maps>\n${tex.normalMap ? FRAG_NORMAL : ''}`, 'detail normal' );
		mat.userData.pfaDetailCompiled = true;
	};
	const prevKey = mat.customProgramCacheKey;
	mat.customProgramCacheKey = function () {
		return `${prevKey ? prevKey.call( this ) : ''}|pfadetail:${proj}:${tex.map ? 1 : 0}${tex.roughnessMap ? 1 : 0}${tex.normalMap ? 1 : 0}`;
	};
	mat.needsUpdate = true;
	return true;
}

/**
 * Attach the detail layer to every material the manifest names.
 * @returns {Promise<object>} report
 */
export async function applyDetail( { scene, detail, loadTexture, note, projection = 'objxy', strength = 1.0, normalScale = 1.0, synthetic = false } ) {
	const report = { projection, strength, normal_scale: normalScale, sets_loaded: 0, materials: 0, textures: 0, bytes: 0,
		means: {},
		by_set: {}, unmatched_rules: [], applied: [], failed: [], empty: [], fallbacks: [], stats: {} };
	if ( ! detail || ! detail.sets ) return report;

	// which scene materials take which rule -----------------------------------------------------
	const seen = new Set(), work = [];
	scene.traverse( ( o ) => {
		if ( ! o.isMesh ) return;
		for ( const m of ( Array.isArray( o.material ) ? o.material : [ o.material ] ) ) {
			if ( ! m || ! m.isMeshStandardMaterial || seen.has( m ) ) continue;
			seen.add( m );
			let rule = detail.perGroup[ m.name ];
			if ( ! rule ) {
				const k = candidateKeys( m.name ).find( key => detail.perMaterial[ key ] );
				if ( k ) rule = detail.perMaterial[ k ];
			}
			if ( rule ) work.push( { mat: m, rule } );
		}
	} );
	for ( const name of Object.keys( detail.perGroup ) )
		if ( ! work.some( w => w.mat.name === name ) ) report.unmatched_rules.push( name );

	// load each set once ------------------------------------------------------------------------
	const wanted = [ ...new Set( work.map( w => w.rule.set ) ) ];
	const loaded = {};
	if ( synthetic ) {
		for ( const name of wanted ) {
			const rule = work.find( w => w.rule.set === name ).rule;
			const tex = makeNoiseSet( detail.shipPx || 1024, rule.mmPerTexel || 1.05, detail.bumpDistanceM || 0.015 );
			for ( const [ slot, t ] of Object.entries( tex ) ) {
				t.colorSpace = slot === 'map' ? THREE.SRGBColorSpace : THREE.NoColorSpace;
				t.wrapS = t.wrapT = THREE.RepeatWrapping;
				t.anisotropy = 8; t.needsUpdate = true;
				const m = measureLinearMean( { image: t.image }, slot === 'map' );
				if ( m ) t.userData.pfaLinearMean = m.mean;
				report.textures ++;
				report.bytes += ( detail.shipPx || 1024 ) * ( detail.shipPx || 1024 ) * 4 * 4 / 3;
			}
			loaded[ name ] = tex;
			report.sets_loaded ++;
		}
		report.synthetic = 'value noise, NOT the bake set (?detailtest=noise)';
	}
	for ( const name of ( synthetic ? [] : wanted ) ) {
		const set = detail.sets[ name ];
		const tex = {};
		for ( const [ slot, entry ] of Object.entries( set.maps ) ) {
			try {
				let t;
				try { t = await loadTexture( entry.url ); }
				catch ( e ) {
					if ( ! entry.fallback ) throw e;
					report.fallbacks.push( { from: entry.url.split( '/' ).pop(), to: entry.fallback.split( '/' ).pop() } );
					t = await loadTexture( entry.fallback );
				}
				t.colorSpace = entry.srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
				t.wrapS = t.wrapT = THREE.RepeatWrapping;      // the layer is tiled, not clamped
				t.anisotropy = 8;
				t.generateMipmaps = true;                      // the 1x1 mip is the mean the shader divides by
				t.minFilter = THREE.LinearMipmapLinearFilter;
				t.needsUpdate = true;
				let m = measureLinearMean( t, entry.srgb );
				if ( ! m && entry.meanLinear ) m = { mean: entry.meanLinear, mean8: 255, std8: 255, samples: 0 };
				if ( ! m ) {
					// A compressed texture has no readable pixels, so its own mean cannot be measured
					// here: the manifest has to declare `mean_linear` for the KTX2 set to be usable.
					report.failed.push( { url: entry.url, error: 'no readable pixels and no mean_linear in the manifest (compressed texture)' } );
					continue;
				}
				// An empty or flat map is data, not a texture: applying it would multiply the baked
				// albedo by 0/0 and turn the surface black (the Gate 2 detail set shipped 15 of 15
				// maps at 1024x1024 all-zero, which is how this guard was found).
				if ( m.mean8 < 1.0 || m.std8 < 1.0 ) {
					report.empty.push( { url: entry.url.split( '/' ).pop(), mean8: Math.round( m.mean8 * 100 ) / 100, std8: Math.round( m.std8 * 100 ) / 100 } );
					t.dispose();
					continue;
				}
				t.userData.pfaLinearMean = m.mean;
				tex[ slot ] = t;
				report.textures ++;
				report.stats[ entry.url.split( '/' ).pop() ] = { mean8: Math.round( m.mean8 * 10 ) / 10, std8: Math.round( m.std8 * 10 ) / 10 };
				report.bytes += ( t.image && t.image.width ) ? t.image.width * t.image.height * 4 * 4 / 3 : 0;
			} catch ( e ) { report.failed.push( { url: entry.url, error: e.message } ); }
		}
		loaded[ name ] = tex;
		report.means[ name ] = { albedo: tex.map && tex.map.userData.pfaLinearMean, roughness: tex.roughnessMap && tex.roughnessMap.userData.pfaLinearMean };
		if ( ! Object.keys( tex ).length ) report.sets_empty = ( report.sets_empty || 0 ) + 1;
		report.sets_loaded ++;
	}

	for ( const { mat, rule } of work ) {
		const tex = loaded[ rule.set ];
		if ( ! tex || ! Object.keys( tex ).length ) continue;
		if ( patchDetailMaterial( mat, tex, rule, { projection, strength, normalScale } ) ) {
			report.materials ++;
			report.by_set[ rule.set ] = ( report.by_set[ rule.set ] || 0 ) + 1;
			report.applied.push( { material: mat.name, set: rule.set, tile_m: rule.tileM, src: rule.src } );
		}
	}
	if ( note ) {
		note( `detail (QA-12-1): ${report.materials} material(s) on ${report.sets_loaded} tiling set(s) `
			+ `(${Object.entries( report.by_set ).map( ( [ k, v ] ) => `${k} x${v}` ).join( ', ' )}), `
			+ `${report.textures} textures, ${( report.bytes / 1e6 ).toFixed( 1 )} MB, `
			+ `projection ${projection} (world space, Blender xy = three x,-z), strength ${strength}, normal scale ${normalScale}`
			+ ( synthetic ? ' — SYNTHETIC NOISE SET (?detailtest=noise), not the bake\'s maps' : '' ) );
		if ( report.unmatched_rules.length )
			note( `detail: ${report.unmatched_rules.length} manifest rule(s) match no scene material: ${report.unmatched_rules.join( ', ' )}` );
		if ( report.empty.length )
			note( `detail: ${report.empty.length} map(s) are EMPTY or FLAT and were dropped (mean8 / std8): `
				+ report.empty.slice( 0, 6 ).map( e => `${e.url} ${e.mean8}/${e.std8}` ).join( ', ' )
				+ ( report.empty.length > 6 ? ' …' : '' ) + ' — the layer cannot run on these' );
		if ( report.failed.length )
			note( `detail: ${report.failed.length} texture(s) FAILED: ${report.failed.map( f => f.url.split( '/' ).pop() ).join( ', ' )}` );
	}
	return report;
}
