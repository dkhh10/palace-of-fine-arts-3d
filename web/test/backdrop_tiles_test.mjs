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

// ---- 5. the shipped export on disk (skipped when it is not there) ----------------------------
// TWO files, because they answer two different questions and neither can answer the other's:
//   * env.gltf + env.bin are what the Blender export WROTE - plain float32, readable here, so the UV
//     LAYOUT can be measured directly (which set is the tile UV, which is the packed bake atlas);
//   * env.glb is what the viewer FETCHES - meshopt-compressed, so its buffers cannot be read without
//     a decoder, but its accessors' componentType still says whether gltfpack requantised the two
//     sets on one shared box. That is the `-vtf` contract, and it is the whole reason for the flag.
const MAIN = process.env.PFA_MAIN_ROOT || '/Users/dk/Projects/3d render blender 3rd attempt building';
const gltfPath = path.join( MAIN, 'export/out/gate1/env.gltf' );
const glbPath = path.join( MAIN, 'export/out/gate1/env.glb' );
const BD_RE = /MAT_EXP_ENVBD__MAT_backdrop_/;

if ( ! fs.existsSync( gltfPath ) ) {
	console.log( `SKIP  env.gltf UV-layout measurement: ${gltfPath} is not on disk` );
} else {
	const gltf = JSON.parse( fs.readFileSync( gltfPath, 'utf8' ) );
	const bins = new Map();
	const bdMat = new Set( gltf.materials.map( ( m, i ) => [ m.name, i ] ).filter( ( [ n ] ) => BD_RE.test( n ) ).map( ( [ , i ] ) => i ) );
	const span = ( accIdx ) => {
		const acc = gltf.accessors[ accIdx ];
		if ( acc.componentType !== 5126 ) return null;         // this file is written unquantised
		const bv = gltf.bufferViews[ acc.bufferView ];
		const uri = gltf.buffers[ bv.buffer ].uri;
		if ( ! uri ) return null;
		if ( ! bins.has( uri ) ) bins.set( uri, fs.readFileSync( path.join( path.dirname( gltfPath ), decodeURIComponent( uri ) ) ) );
		const buf = bins.get( uri );
		const off = ( bv.byteOffset || 0 ) + ( acc.byteOffset || 0 );
		let lo = [ Infinity, Infinity ], hi = [ - Infinity, - Infinity ];
		for ( let i = 0; i < acc.count; i ++ ) for ( const c of [ 0, 1 ] ) {
			const v = buf.readFloatLE( off + ( i * 2 + c ) * 4 );
			if ( v < lo[ c ] ) lo[ c ] = v;
			if ( v > hi[ c ] ) hi[ c ] = v;
		}
		return { u: hi[ 0 ] - lo[ 0 ], v: hi[ 1 ] - lo[ 1 ], min: lo, max: hi };
	};
	let checked = 0, twoSets = 0, tileWide = 0, atlasFills = 0;
	const worst = [];
	for ( const mesh of gltf.meshes ) for ( const pr of mesh.primitives ) {
		if ( ! bdMat.has( pr.material ) ) continue;
		checked ++;
		const a = pr.attributes;
		if ( a.TEXCOORD_0 === undefined || a.TEXCOORD_1 === undefined ) { worst.push( `${mesh.name}: sets ${Object.keys( a ).filter( k => /TEXCOORD/.test( k ) )}` ); continue; }
		twoSets ++;
		const s0 = span( a.TEXCOORD_0 ), s1 = span( a.TEXCOORD_1 );
		if ( s0 && Math.max( s0.u, s0.v ) > 1.5 ) tileWide ++;
		else worst.push( `${mesh.name}: TEXCOORD_0 spans ${s0 ? Math.max( s0.u, s0.v ).toFixed( 3 ) : '?'}` );
		if ( s1 && Math.max( s1.u, s1.v ) <= 1.05 && Math.max( s1.u, s1.v ) >= 0.5 ) atlasFills ++;
		else worst.push( `${mesh.name}: TEXCOORD_1 spans ${s1 ? Math.max( s1.u, s1.v ).toFixed( 3 ) : '?'} - not a packed [0,1] atlas` );
	}
	check( checked > 0, `env.gltf carries backdrop primitives (${checked})` );
	check( twoSets === checked, `every backdrop primitive carries TWO UV sets (${twoSets}/${checked})` );
	// Not "all of them": `backdrop_door_green` is ONE cube and its own tile UV spans 0.94 of a 16 m tile.
	// A swap would put the packed atlas on TEXCOORD_0 for EVERY merge, i.e. spans of ~1.0 across the board,
	// so "all but at most one, and at least four" separates the two cases without excusing a swap.
	check( twoSets > 0 && tileWide >= Math.max( 4, twoSets - 1 ),
		`TEXCOORD_0 runs in tile units on ${tileWide}/${twoSets} merges (all but the single-cube door group) - it IS the tile UV` );
	check( twoSets > 0 && atlasFills === twoSets, `TEXCOORD_1 fills [0,1] without leaving it on all of them (${atlasFills}/${twoSets}) - it IS the packed bake atlas` );
	if ( worst.length ) console.log( `      ${worst.slice( 0, 6 ).join( ' | ' )}` );
}

if ( ! fs.existsSync( glbPath ) ) {
	console.log( `SKIP  env.glb quantisation check: ${glbPath} is not on disk` );
} else {
	const buf = fs.readFileSync( glbPath );
	const gltf = JSON.parse( buf.subarray( 20, 20 + buf.readUInt32LE( 12 ) ).toString( 'utf8' ) );
	const bdMat = new Set( gltf.materials.map( ( m, i ) => [ m.name, i ] ).filter( ( [ n ] ) => BD_RE.test( n ) ).map( ( [ , i ] ) => i ) );
	let prims = 0, float = 0, xf = 0;
	for ( const mesh of gltf.meshes ) for ( const pr of mesh.primitives ) {
		if ( ! bdMat.has( pr.material ) ) continue;
		prims ++;
		const a = pr.attributes;
		const sets = [ a.TEXCOORD_0, a.TEXCOORD_1 ].filter( ( x ) => x !== undefined );
		if ( sets.length === 2 && sets.every( ( i ) => gltf.accessors[ i ].componentType === 5126 ) ) float ++;
		const t = ( ( gltf.materials[ pr.material ] || {} ).pbrMetallicRoughness || {} ).baseColorTexture;
		if ( t && t.extensions && t.extensions.KHR_texture_transform ) xf ++;
	}
	check( prims > 0, `env.glb carries backdrop primitives (${prims})` );
	check( float === prims,
		`both UV sets are FLOAT in the packed glb (${float}/${prims}) - gltfpack -vtf, so the many-tile `
		+ `TEXCOORD_0 cannot drag the bake atlas onto its own quantisation box` );
	check( xf === 0, `and no KHR_texture_transform is left to apply to the wrong set (${xf} material(s) carry one)` );
}

// ---- 6. the SHIPPED manifests, both variants (skipped when they are not there) ----------------
// The fixtures above prove the code; this proves the file the viewer will actually fetch - including the
// mobile plan's redirect of every tile key to its half-resolution copy under tex_lo/.
for ( const [ variant, file ] of [ [ 'desktop', 'manifest.json' ], [ 'mobile', 'manifest_mobile.json' ] ] ) {
	const p5 = path.join( MAIN, 'export/out/gate5', file );
	if ( ! fs.existsSync( p5 ) ) { console.log( `SKIP  shipped ${variant} manifest: ${p5} is not on disk` ); continue; }
	const real = normaliseManifest( JSON.parse( fs.readFileSync( p5, 'utf8' ) ), `https://x/assets/gate5/${file}` );
	const bd = real.backdropTiles;
	check( !! bd && bd.count === 4, `${variant}: four backdrop groups in the shipped manifest (got ${bd ? bd.count : 'none'})` );
	if ( ! bd ) continue;
	check( bd.missing === 0, `${variant}: every tile key resolves to a file (${bd.missing} unresolved)` );
	check( bd.tileChannel === 0 && bd.bakedChannel === 1, `${variant}: tile UV 0, baked atlas 1` );
	check( checkUvContract( bd, real.materials.sets ).length === 0,
		`${variant}: the UV contract holds against the real material sets` );
	const tc1 = Object.values( real.materials.sets ).filter( ( s ) => s.texCoord === 1 ).length;
	check( tc1 === 8, `${variant}: texcoord 1 on the 8 backdrop merges, 0 on the rest (got ${tc1})` );
	const urls = Object.values( bd.groups ).map( ( g ) => g.url );
	const lo = urls.filter( ( u ) => /tex_lo\//.test( u ) ).length;
	check( variant === 'mobile' ? lo === 4 : lo === 0,
		`${variant}: ${lo}/4 tiles served from tex_lo (mobile halves them, desktop does not)` );
	check( Object.values( bd.groups ).every( ( g ) => g.tier === 1 ),
		`${variant}: all four are tier 1, so the first frame does not pay for them` );
}

console.log( fails ? `${fails} FAILURES` : 'all backdrop-tile checks passed' );
process.exit( fails ? 1 : 0 );
