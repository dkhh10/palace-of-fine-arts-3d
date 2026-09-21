// Phase 9 backdrop gain tiles — the contract a screenshot cannot show:
//
//     node test/backdrop_tiles_test.mjs
//
// The ENV round put the TILE UV at layer 0 on the 1 291 backdrop meshes, which moved the BAKED atlas
// UV to layer 1: in env.glb TEXCOORD_0 = tile, TEXCOORD_1 = baked atlas.  Swap the two and the city
// samples a 1 K packed atlas at 64 tiles per metre and the gain map at atlas coordinates — a frame
// that reads as "the tiles did nothing", not as an error.  So:
//
//   1. the manifest's two indices survive normaliseManifest, and the material sets' own `texcoord`
//      reaches `pbr.js` (a set with no `texcoord` is still 0 — every pre-Phase-9 manifest);
//   2. `checkUvContract` FAILS when the two sets are swapped, and `applyBackdropTiles` then patches
//      NOTHING rather than shipping a scrambled city;
//   3. the shader the patch compiles is the Cycles formula, on the tile UV, after <map_fragment>;
//   4. the amplitude arithmetic itself: gain is mean-1.0, and `keep` limits how much the haze can
//      take out of it (the ENV report's "amp only varies by 26 % across the whole haze range");
//   5. env.glb itself, when it is on disk: the backdrop merges carry two UV sets, TEXCOORD_0 spans
//      many tiles and TEXCOORD_1 stays inside [0,1].  That is the measurement that catches a swap at
//      the source instead of in the manifest.
import * as THREE from 'three';
import fs from 'node:fs';
import path from 'node:path';
import { normaliseManifest } from '../src/manifest.js';
import { applyBackdropTiles, patchBackdropMaterial, checkUvContract, groupFor } from '../src/backdropTiles.js';

let fails = 0;
const check = ( ok, msg ) => { if ( ! ok ) fails ++; console.log( `${ok ? 'PASS' : 'FAIL'}  ${msg}` ); };
const near = ( a, b, eps, msg ) => check( Math.abs( a - b ) <= eps, `${msg} (got ${a.toFixed( 5 )}, want ${b} +-${eps})` );

const SET = 'MAT_EXP_ENVBD__MAT_backdrop_building';
const raw = ( bakedTexcoord = 1, uvBaked = 'TEXCOORD_1', uvTile = 'TEXCOORD_0' ) => ( {
	schema: 'pfa-phase6/4',
	textures: { gate2: { ktx2_dir: 'tex_ktx2', files: {
		p9_bd_facade: { path: 'p9_bd_facade.ktx2', w: 1024, h: 1024, map: 'gain', colorspace: 'linear', bytes: 402862 },
		gate2_x_albedo: { path: 'gate2_x_albedo.ktx2', w: 1024, h: 1024, map: 'albedo', colorspace: 'srgb', bytes: 10 },
	} } },
	materials: { mode: 'pbr', uv: 'TEXCOORD_0', sets: {
		[ SET ]: { job: 'ENVBD__backdrop_building', cls: 'backdrop', src_material: 'MAT_backdrop_building',
			texcoord: bakedTexcoord, albedo: { texture: 'gate2_x_albedo', factor: [ 0.68, 0.67, 0.63 ] } },
		MAT_EXP_ARCH_x__MAT_concrete: { job: 'a', cls: 'arch', src_material: 'MAT_concrete',
			albedo: { texture: 'gate2_x_albedo', factor: [ 0.5, 0.5, 0.5 ] } },
	} },
	backdrop_tiles: { schema: 'pfa-phase9/backdrop-tiles/1', wrap: 'repeat', colorspace: 'linear',
		uv: { tile: uvTile, baked: uvBaked },
		groups: { [ SET ]: { texture: 'p9_bd_facade', src_material: 'MAT_backdrop_building',
			strength: 1.25, keep: 0.7, r0: 150, r1: 720, amount: 0.86 } } },
} );

// ---- 1. the indices survive the manifest ------------------------------------------------------
const man = normaliseManifest( raw(), 'https://x/assets/gate5/manifest.json' );
check( !! man.backdropTiles, 'backdrop_tiles is parsed' );
check( man.backdropTiles.count === 1, `one group parsed (got ${man.backdropTiles && man.backdropTiles.count})` );
check( man.backdropTiles.tileChannel === 0 && man.backdropTiles.bakedChannel === 1,
	`tile UV channel 0, baked atlas channel 1 (got ${man.backdropTiles.tileChannel} / ${man.backdropTiles.bakedChannel})` );
check( man.backdropTiles.groups[ SET ].url.endsWith( 'tex_ktx2/p9_bd_facade.ktx2' ),
	`the tile resolves through textures.gate2 (${man.backdropTiles.groups[ SET ].url})` );
check( man.materials.sets[ SET ].texCoord === 1, 'the backdrop set reports texCoord 1 to pbr.js' );
check( man.materials.sets.MAT_EXP_ARCH_x__MAT_concrete.texCoord === 0,
	'a set with no texcoord is 0 — every pre-Phase-9 manifest still lands on TEXCOORD_0' );
check( groupFor( SET, man.backdropTiles.groups ) === man.backdropTiles.groups[ SET ], 'group matched by glb material name' );
check( groupFor( 'MAT_EXP_ENVBD2__MAT_backdrop_building', man.backdropTiles.groups ) === man.backdropTiles.groups[ SET ],
	'and by the __<source material> suffix, so a renamed export still finds its tile' );

// ---- 2. SWAPPED: the contract fails and nothing is patched ------------------------------------
// This is the whole point of the file.  `texcoord: 0` on a set that wears a gain tile means the baked
// maps were left on the tile UV — i.e. the two sets are the wrong way round.
const swapped = normaliseManifest( raw( 0 ), 'https://x/assets/gate5/manifest.json' );
const problems = checkUvContract( swapped.backdropTiles, swapped.materials.sets );
check( problems.length === 1, `a swapped pair is reported (got ${problems.length}: ${problems.join( '; ' )})` );
check( checkUvContract( man.backdropTiles, man.materials.sets ).length === 0, 'the correct pair reports nothing' );
const bothSame = normaliseManifest( raw( 0, 'TEXCOORD_0', 'TEXCOORD_0' ), 'https://x/assets/gate5/manifest.json' );
check( checkUvContract( bothSame.backdropTiles, bothSame.materials.sets ).length >= 1,
	'a manifest that puts both the tile and the atlas on TEXCOORD_0 is reported too' );

function scene( name = SET ) {
	const s = new THREE.Scene();
	const m = new THREE.MeshStandardMaterial( { name } );
	s.add( new THREE.Mesh( new THREE.PlaneGeometry( 1, 1 ), m ) );
	return { s, m };
}
const loadTexture = async () => new THREE.Texture();
const notes = [];
const bad = scene();
const badRep = await applyBackdropTiles( { scene: bad.s, backdropTiles: swapped.backdropTiles,
	sets: swapped.materials.sets, loadTexture, note: ( t ) => notes.push( t ) } );
check( badRep.patched === 0 && ! bad.m.userData.pfaBackdropTile,
	'with the sets swapped NO material is patched' );
check( notes.some( ( t ) => /UV contract broken/.test( t ) ), 'and the viewer says so in the boot note' );

const good = scene();
const goodRep = await applyBackdropTiles( { scene: good.s, backdropTiles: man.backdropTiles,
	sets: man.materials.sets, loadTexture, note: () => {} } );
check( goodRep.patched === 1, `the correct manifest patches the material (got ${goodRep.patched})` );
check( good.m.userData.pfaBackdropTile.key === 'p9_bd_facade', 'and records which tile it wears' );
const tex = good.m.userData.pfaBackdropTile.uniforms.pfaBdTile.value;
check( tex.colorSpace === THREE.NoColorSpace, 'the gain texture is NOT sRGB-decoded (Non-Color)' );
check( tex.wrapS === THREE.RepeatWrapping && tex.wrapT === THREE.RepeatWrapping, 'and is REPEAT-sampled' );
check( tex.channel === 0, `and samples the TILE UV set (channel ${tex.channel})` );

// a material outside the four groups is left alone
const other = scene( 'MAT_EXP_ARCH_x__MAT_concrete' );
const otherRep = await applyBackdropTiles( { scene: other.s, backdropTiles: man.backdropTiles,
	sets: man.materials.sets, loadTexture, note: () => {} } );
check( otherRep.materials === 0 && ! other.m.userData.pfaBackdropTile, 'a non-backdrop material takes no gain' );

// ---- 3. the compiled shader -------------------------------------------------------------------
const mat = new THREE.MeshStandardMaterial( { name: SET } );
patchBackdropMaterial( mat, new THREE.Texture(), { ...man.backdropTiles.groups[ SET ] }, 1.0 );
const shader = { vertexShader: 'void main() {\n#include <project_vertex>\n}',
	fragmentShader: 'void main() {\n#include <map_fragment>\n}', uniforms: {} };
mat.onBeforeCompile( shader, null );
check( /vPfaBdUv = uv;/.test( shader.vertexShader ),
	'the tile UV comes from the `uv` attribute, not from three\'s vUv (which does not exist at channel 1)' );
check( /vPfaBdXZ = \( modelMatrix \* pfaBdW \).xz/.test( shader.vertexShader ),
	'the haze radius is world xz — glTF Y-up, i.e. the Blender XY plane' );
const frag = shader.fragmentShader.split( '#include <map_fragment>' )[ 1 ] || '';
check( /pfaBdT - 0\.5/.test( frag ) && /2\.0 \* pfaBdStrength/.test( frag ) && /1\.0 - \( 1\.0 - pfaBdKeep \) \* pfaBdH/.test( frag ),
	'the gain is 1 + (tile - 0.5) * 2 * strength * (1 - (1 - keep) * haze), applied AFTER the baked albedo' );
check( shader.uniforms.pfaBdStrength.value === 1.25 && shader.uniforms.pfaBdKeep.value === 0.7
	&& shader.uniforms.pfaBdHaze.value.x === 150 && shader.uniforms.pfaBdHaze.value.y === 720
	&& shader.uniforms.pfaBdHaze.value.z === 0.86,
	'and it carries the ENV report\'s constants for MAT_backdrop_building unchanged' );

// ---- 4. the arithmetic -------------------------------------------------------------------------
const gain = ( t, strength, keep, haze ) => 1 + ( t - 0.5 ) * 2 * strength * ( 1 - ( 1 - keep ) * haze );
near( ( gain( 0.505, 1.25, 0.7, 0 ) + gain( 0.495, 1.25, 0.7, 0 ) ) / 2, 1.0, 1e-9,
	'the gain is mean-1.0: it cannot move a group\'s mean albedo, only its variance' );
near( gain( 1.0, 1.25, 0.7, 0 ), 2.25, 1e-9, 'a white texel near the building doubles-and-a-quarter' );
near( gain( 1.0, 1.25, 0.7, 1 ), 1.875, 1e-9, 'and the far haze keeps 70 % of that amplitude' );
near( ( gain( 1.0, 1.25, 0.7, 1 ) - 1 ) / ( gain( 1.0, 1.25, 0.7, 0 ) - 1 ), 0.7, 1e-9,
	'`keep` IS the ratio: amp varies by 30 % across the whole haze range, never more' );

// ---- 5. env.glb on disk (skipped when it is not there) ----------------------------------------
const MAIN = process.env.PFA_MAIN_ROOT || '/Users/dk/Projects/3d render blender 3rd attempt building';
const glbPath = path.join( MAIN, 'export/out/gate1/env.glb' );
if ( ! fs.existsSync( glbPath ) ) {
	console.log( `SKIP  env.glb UV-set measurement: ${glbPath} is not on disk` );
} else {
	const buf = fs.readFileSync( glbPath );
	const jsonLen = buf.readUInt32LE( 12 );
	const gltf = JSON.parse( buf.subarray( 20, 20 + jsonLen ).toString( 'utf8' ) );
	const binOff = 20 + jsonLen + 8;
	const bdMat = new Set( gltf.materials.map( ( m, i ) => [ m.name, i ] )
		.filter( ( [ n ] ) => /MAT_EXP_ENVBD__MAT_backdrop_/.test( n ) ).map( ( [ , i ] ) => i ) );
	const read = ( accIdx ) => {
		const acc = gltf.accessors[ accIdx ];
		const bv = gltf.bufferViews[ acc.bufferView ];
		const off = binOff + ( bv.byteOffset || 0 ) + ( acc.byteOffset || 0 );
		const n = acc.count * 2;
		const stride = bv.byteStride || 0;
		const out = new Float32Array( n );
		if ( acc.componentType === 5126 && ( ! stride || stride === 8 ) ) {
			for ( let i = 0; i < n; i ++ ) out[ i ] = buf.readFloatLE( off + i * 4 );
			return out;
		}
		// gltfpack quantises UVs to unsigned shorts with a KHR_mesh_quantization scale in the node/mat
		if ( acc.componentType === 5123 ) {
			for ( let i = 0; i < acc.count; i ++ ) {
				const b = off + i * ( stride || 4 );
				out[ i * 2 ] = buf.readUInt16LE( b ); out[ i * 2 + 1 ] = buf.readUInt16LE( b + 2 );
			}
			return out;
		}
		return null;
	};
	// the material's KHR_texture_transform, when the file still carries one: gltfpack's shared-box
	// quantisation. With -vtf (this round) there is none and the UVs are already metres-per-tile.
	const xfOf = ( matIdx ) => {
		const t = ( ( gltf.materials[ matIdx ] || {} ).pbrMetallicRoughness || {} ).baseColorTexture;
		const x = t && t.extensions && t.extensions.KHR_texture_transform;
		return x ? { scale: x.scale || [ 1, 1 ], offset: x.offset || [ 0, 0 ] } : { scale: [ 1, 1 ], offset: [ 0, 0 ] };
	};
	let checked = 0, twoSets = 0, tileWide = 0, atlasInUnit = 0;
	for ( const mesh of gltf.meshes ) {
		for ( const pr of mesh.primitives ) {
			if ( ! bdMat.has( pr.material ) ) continue;
			checked ++;
			const a = pr.attributes;
			if ( a.TEXCOORD_0 !== undefined && a.TEXCOORD_1 !== undefined ) twoSets ++;
			// the accessor min/max are authoritative and survive quantisation: the tile UV runs in tile
			// units over a whole city block, the packed bake atlas cannot leave [0,1].
			const span = ( which ) => {
				if ( a[ which ] === undefined ) return null;
				const acc = gltf.accessors[ a[ which ] ];
				if ( ! acc.min || ! acc.max ) { const v = read( a[ which ] ); if ( ! v ) return null;
					let lo = Infinity, hi = - Infinity;
					for ( let i = 0; i < v.length; i ++ ) { if ( v[ i ] < lo ) lo = v[ i ]; if ( v[ i ] > hi ) hi = v[ i ]; }
					return hi - lo; }
				return Math.max( acc.max[ 0 ] - acc.min[ 0 ], acc.max[ 1 ] - acc.min[ 1 ] );
			};
			const xf = xfOf( pr.material );
			const s0raw = span( 'TEXCOORD_0' ), s1raw = span( 'TEXCOORD_1' );
			const s0 = s0raw === null ? null : s0raw * xf.scale[ 0 ];
			const s1 = s1raw === null ? null : s1raw * xf.scale[ 0 ];
			if ( s0 !== null && s0 > 1.5 ) tileWide ++;
			// the packed bake atlas fills its square: inside [0,1] AND not collapsed into a sliver,
			// which is what a shared-box quantisation of a many-tile UV0 would leave of it.
			if ( s1 !== null && s1 <= 1.05 && s1 >= 0.5 ) atlasInUnit ++;
		}
	}
	check( checked > 0, `env.glb carries backdrop primitives (${checked})` );
	check( twoSets === checked, `every backdrop primitive carries TWO UV sets (${twoSets}/${checked})` );
	check( tileWide === checked, `TEXCOORD_0 spans more than one tile on all of them (${tileWide}/${checked}) — it is the tile UV` );
	check( atlasInUnit === checked, `TEXCOORD_1 fills [0,1] without leaving it on all of them (${atlasInUnit}/${checked}) — it is the packed bake atlas, at full precision` );
}

console.log( fails ? `${fails} FAILURES` : 'all backdrop-tile checks passed' );
process.exit( fails ? 1 : 0 );
