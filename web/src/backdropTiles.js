// Phase 9: the ENV backdrop gain tiles, as the viewer's own material layer.
//
// WHY THEY CANNOT COME FROM THE BAKED ATLAS.  The Gate 2 backdrop atlas is 0.79 texels/m on the city
// facades; the gain tile is 64.  Baking the tile in would need ~1.17 km² of MAT_backdrop_building at 64
// texels/m, which no atlas can hold (docs/briefs/phase9_env_report.md "Export hand-off").  So the four
// images ship as their own REPEAT-sampled, **Non-Color** textures and the viewer multiplies them over
// the baked albedo, per fragment, exactly as the Cycles material does:
//
//     haze   = smoothstep( r0, r1, length( worldPos.xz ) ) * amount   // glTF Y-up: the Blender XY plane
//     amp    = 2 * strength * ( 1 - ( 1 - keep ) * haze )
//     albedo = bakedAlbedo * ( 1 + ( tile - 0.5 ) * amp )             // per channel
//
// The gain is mean-1.0 (the images measure 0.5050), so it cannot move a group's mean albedo - it adds
// variance, which is the whole point: the aerial blocks read as flat pale boxes without it.
//
// THE TWO UV SETS, AND WHY THIS FILE STATES BOTH.  The ENV build inserted the tile UV ("UVMap", already
// divided by the tile size, so REPEAT and NO texture transform) at layer 0 on the 1 291 backdrop meshes,
// which pushed the BAKED atlas UV to layer 1.  In env.glb that is TEXCOORD_0 = tile, TEXCOORD_1 = baked
// atlas -> three.js `uv` and `uv1`.  If the two are ever swapped the city samples the 1 K atlas at 64
// tiles per metre and the gain map at atlas coordinates, which would look like noise, not like a defect
// in a number: `checkUvContract()` below is called on every run and fails loudly instead.
//
// The tile UV is read from the `uv` attribute, NOT from three's vUv: with the baked maps on channel 1
// three declares no `vUv` varying at all, while `attribute vec2 uv` is in every vertex prefix.
import * as THREE from 'three';

function once( src, needle, replacement, what ) {
	const n = src.split( needle ).length - 1;
	if ( n !== 1 ) throw new Error( `backdrop tile patch "${what}": expected 1 occurrence, found ${n}` );
	return src.replace( needle, replacement );
}

const VERT = /* glsl */`
	vPfaBdUv = uv;
	{
		vec4 pfaBdW = vec4( transformed, 1.0 );
		#ifdef USE_INSTANCING
			pfaBdW = instanceMatrix * pfaBdW;
		#endif
		vPfaBdXZ = ( modelMatrix * pfaBdW ).xz;
	}
`;

const PARS = /* glsl */`
varying vec2 vPfaBdUv;
varying vec2 vPfaBdXZ;
uniform sampler2D pfaBdTile;
uniform float pfaBdStrength;
uniform vec3 pfaBdHaze;        // r0, r1, amount
uniform float pfaBdKeep;
uniform float pfaBdMix;        // 0 disables the layer without recompiling (?bdtiles=0)
`;

const FRAG = /* glsl */`
	{
		vec3 pfaBdT = texture2D( pfaBdTile, vPfaBdUv ).rgb;
		float pfaBdH = smoothstep( pfaBdHaze.x, pfaBdHaze.y, length( vPfaBdXZ ) ) * pfaBdHaze.z;
		float pfaBdA = 2.0 * pfaBdStrength * ( 1.0 - ( 1.0 - pfaBdKeep ) * pfaBdH );
		diffuseColor.rgb *= mix( vec3( 1.0 ), 1.0 + ( pfaBdT - 0.5 ) * pfaBdA, pfaBdMix );
	}
`;

/** The group a material belongs to: the manifest names the glb material outright, and an older
 *  manifest (or a renamed export) still matches on the `MAT_backdrop_*` source material suffix. */
export function groupFor( materialName, groups ) {
	if ( ! materialName || ! groups ) return null;
	if ( groups[ materialName ] ) return groups[ materialName ];
	for ( const g of Object.values( groups ) ) {
		if ( g.srcMaterial && materialName.endsWith( `__${g.srcMaterial}` ) ) return g;
	}
	return null;
}

/**
 * The UV contract, checked rather than assumed.  Returns a list of problems (empty = fine).
 * @param {object} bd  manifest.backdropTiles
 * @param {object} sets  manifest.materials.sets
 */
export function checkUvContract( bd, sets ) {
	const bad = [];
	if ( ! bd ) return bad;
	if ( bd.tileChannel === bd.bakedChannel )
		bad.push( `the tile UV and the baked atlas are both ${bd.uvTile}` );
	for ( const name of Object.keys( bd.groups || {} ) ) {
		const s = sets && sets[ name ];
		if ( ! s ) continue;
		// The set that wears a gain tile MUST read its baked maps from the other UV set.  A manifest
		// that says both ride TEXCOORD_0 is the swapped case, and it is a failure, not a warning.
		if ( ( s.texCoord | 0 ) !== ( bd.bakedChannel | 0 ) )
			bad.push( `${name}: baked maps on TEXCOORD_${s.texCoord | 0}, backdrop_tiles says ${bd.uvBaked}` );
	}
	return bad;
}

/** Patch one MeshStandardMaterial with its group's gain tile.  Chains any existing onBeforeCompile. */
export function patchBackdropMaterial( mat, tex, group, mix = 1.0 ) {
	if ( mat.userData.pfaBackdropTile ) {            // already patched: swap the texture only (tier upgrade)
		mat.userData.pfaBackdropTile.uniforms.pfaBdTile.value = tex;
		mat.userData.pfaBackdropTile.url = tex && tex.userData ? tex.userData.pfaUrl || null : null;
		return false;
	}
	const uniforms = {
		pfaBdTile: { value: tex },
		pfaBdStrength: { value: group.strength },
		pfaBdHaze: { value: new THREE.Vector3( group.r0, group.r1, group.amount ) },
		pfaBdKeep: { value: group.keep },
		pfaBdMix: { value: mix },
	};
	mat.userData.pfaBackdropTile = { group: group.name, key: group.key, uniforms,
		strength: group.strength, keep: group.keep, r0: group.r0, r1: group.r1, amount: group.amount };
	const prevCompile = mat.onBeforeCompile;
	mat.onBeforeCompile = function ( shader, renderer ) {
		if ( prevCompile ) prevCompile.call( this, shader, renderer );
		Object.assign( shader.uniforms, uniforms );
		shader.vertexShader = `varying vec2 vPfaBdUv;\nvarying vec2 vPfaBdXZ;\n` + once( shader.vertexShader,
			'#include <project_vertex>', `#include <project_vertex>\n${VERT}`, 'tile uv + world xz' );
		shader.fragmentShader = `${PARS}\n` + shader.fragmentShader;
		// AFTER <map_fragment>, so the gain multiplies the baked albedo the same way Cycles multiplies
		// it after the atmosphere term (which the baked albedo already carries).
		shader.fragmentShader = once( shader.fragmentShader, '#include <map_fragment>',
			`#include <map_fragment>\n${FRAG}`, 'backdrop gain' );
		mat.userData.pfaBackdropTileCompiled = true;
	};
	const prevKey = mat.customProgramCacheKey;
	mat.customProgramCacheKey = function () {
		return `${prevKey ? prevKey.call( this ) : ''}|pfabdtile:1`;
	};
	mat.needsUpdate = true;
	return true;
}

/**
 * Attach the gain tiles to every backdrop material in the scene.
 * @returns {Promise<object>} report
 */
export async function applyBackdropTiles( { scene, backdropTiles, sets, loadTexture, note = () => {},
	maxTier = Infinity, strength = 1.0 } = {} ) {
	const report = { present: !! backdropTiles, groups: 0, materials: 0, patched: 0, deferred: [],
		textures: 0, bytes: 0, failed: [], uvProblems: [], byGroup: {}, strength,
		uv: backdropTiles ? { tile: backdropTiles.uvTile, baked: backdropTiles.uvBaked } : null };
	if ( ! backdropTiles || ! backdropTiles.count ) return report;
	report.uvProblems = checkUvContract( backdropTiles, sets );
	if ( report.uvProblems.length ) {
		// Loud and total: a swapped pair makes the city look like static, and it would otherwise read
		// in a capture as "the tiles did nothing".
		note( `backdrop tiles NOT applied — UV contract broken: ${report.uvProblems.join( '; ' )}` );
		return report;
	}
	const cache = new Map();
	const fetch = ( url ) => {
		if ( ! cache.has( url ) ) cache.set( url, loadTexture( url ).then( ( t ) => {
			if ( ! t ) return null;
			t.colorSpace = THREE.NoColorSpace;          // the gain is DATA: never sRGB-decoded
			t.wrapS = t.wrapT = THREE.RepeatWrapping;   // the UVs are in tile units already
			t.anisotropy = Math.max( t.anisotropy || 1, 8 );
			t.channel = backdropTiles.tileChannel | 0;
			t.needsUpdate = true;
			return t;
		} ).catch( ( e ) => { report.failed.push( `${url.split( '/' ).pop()}: ${e.message}` ); return null; } ) );
		return cache.get( url );
	};
	const work = [];
	const seen = new Set();
	scene.traverse( ( o ) => {
		if ( ! o.isMesh ) return;
		for ( const m of ( Array.isArray( o.material ) ? o.material : [ o.material ] ) ) {
			if ( ! m || seen.has( m.uuid ) ) continue;
			const g = groupFor( m.name, backdropTiles.groups );
			if ( ! g ) continue;
			seen.add( m.uuid );
			report.materials ++;
			if ( g.tier > maxTier ) { report.deferred.push( { material: m.name, key: g.key, tier: g.tier } ); continue; }
			work.push( { material: m, group: g } );
		}
	} );
	await Promise.all( work.map( async ( j ) => {
		const t = await fetch( j.group.url );
		if ( ! t ) return;
		const fresh = patchBackdropMaterial( j.material, t, j.group, strength );
		if ( fresh ) report.patched ++;
		report.byGroup[ j.group.name ] = `${j.group.key} strength ${j.group.strength} keep ${j.group.keep} `
			+ `haze ${j.group.r0}-${j.group.r1} m x ${j.group.amount}`;
	} ) );
	report.groups = Object.keys( report.byGroup ).length;
	for ( const url of cache.keys() ) {
		const g = Object.values( backdropTiles.groups ).find( ( x ) => x.url === url );
		if ( g && g.bytes ) { report.textures ++; report.bytes += g.bytes; }
	}
	note( `backdrop tiles: ${report.patched} material(s) patched over ${report.groups} group(s), `
		+ `${report.textures} texture(s) ${( report.bytes / 1e6 ).toFixed( 2 )} MB, tile UV ${backdropTiles.uvTile}, `
		+ `baked atlas ${backdropTiles.uvBaked}`
		+ ( report.deferred.length ? `; ${report.deferred.length} deferred to a later tier` : '' )
		+ ( report.failed.length ? `; ${report.failed.length} FAILED: ${report.failed[ 0 ]}` : '' ) );
	return report;
}
