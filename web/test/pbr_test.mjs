// Gate 2 unit tests without a browser:
//   node test/pbr_test.mjs
// (a) manifest v3 `materials` normalisation: texture sets, colour spaces, the ktx2 directory;
// (b) material-name matching between the glb's `MAT_EXP_<zone>__<source>` and the bake's keys;
// (c) the QA-11d-1 instance chunking: a site-spanning batch is split, a local one is not, and no
//     instance is lost or duplicated.
import * as THREE from 'three';
import { readFileSync, writeFileSync, mkdtempSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { candidateKeys, pbrPlan } from '../src/pbr.js';
import { chunkInstancedMeshes } from '../src/chunking.js';

const WEB = path.resolve( fileURLToPath( new URL( '..', import.meta.url ) ) );
let fails = 0;
const check = ( ok, msg ) => { if ( ! ok ) fails ++; console.log( `${ok ? 'PASS' : 'FAIL'}  ${msg}` ); };

// manifest.js imports a .json module; transform to CJS in memory rather than duplicating it.
const src = readFileSync( path.join( WEB, 'src/manifest.js' ), 'utf8' )
	.replace( /^import stationsFallback.*$/m,
		'const stationsFallback = ' + readFileSync( path.join( WEB, 'src/stations_blender.json' ), 'utf8' ) + ';' )
	.replace( /^export /gm, '' ) + '\nmodule.exports = { normaliseManifest };';
const tmp = path.join( mkdtempSync( path.join( os.tmpdir(), 'pfa-pbr-' ) ), 'manifest.cjs' );
writeFileSync( tmp, src );
const { normaliseManifest } = createRequire( import.meta.url )( tmp );

const base = 'http://x/assets/gate2/manifest.json';

// --- (a) manifest v3 ---------------------------------------------------------------------------
const v3 = {
	schema: 'pfa-phase6/3',
	textures: { ktx2_dir: 'tex_ktx2' },
	materials: {
		mode: 'pbr',
		sets: {
			MAT_concrete_colonnade: {
				albedo: { path: 'MAT_concrete_colonnade_albedo_2k.ktx2', colorspace: 'sRGB', bytes: 1000 },
				roughness: { path: 'MAT_concrete_colonnade_rough_2k.ktx2', colorspace: 'linear', bytes: 500 },
				normal: { path: 'MAT_concrete_colonnade_nrm_2k.ktx2', colorspace: 'non-color', bytes: 700 },
			},
			MAT_dome_membrane: { albedo: 'MAT_dome_membrane_albedo_4k.ktx2' },   // bare string, no colour space
		},
	},
};
{
	const m = normaliseManifest( v3, base );
	check( m.materials.count === 2, `v3: ${m.materials.count} texture sets (expected 2)` );
	check( m.materials.mode === 'pbr', `v3: materials.mode = ${m.materials.mode}` );
	check( m.materials.maps === 4, `v3: ${m.materials.maps} maps (expected 4)` );
	const s = m.materials.sets.MAT_concrete_colonnade;
	check( s.maps.map.url === 'http://x/assets/gate2/tex_ktx2/MAT_concrete_colonnade_albedo_2k.ktx2',
		`v3: albedo resolved under textures.ktx2_dir -> ${s.maps.map.url}` );
	check( s.maps.map.srgb === true, 'v3: albedo declared sRGB -> sRGB' );
	check( s.maps.roughnessMap.srgb === false && s.maps.normalMap.srgb === false,
		'v3: roughness "linear" and normal "non-color" -> linear' );
	check( m.materials.sets.MAT_dome_membrane.maps.map.srgb === true,
		'v3: an undeclared albedo defaults to sRGB (and the fallback is noted)' );
	check( m.notes.some( n => /colour space defaulted/.test( n ) ), 'v3: the colour-space fallback is reported' );
	check( m.materials.declaredBytes === 2200, `v3: ${m.materials.declaredBytes} declared bytes` );
	check( pbrPlan( m.materials.sets ).length === 4, 'v3: the byte plan lists every unique texture file' );
	// the Gate 1 manifest must still normalise to grey (no sets, no notes about materials)
	const g1 = normaliseManifest( { schema: 'pfa-phase6/2' }, base );
	check( g1.materials.count === 0 && g1.materials.mode === null, 'v2: no texture sets -> grey mode' );
}

// alternative shapes: `per_material` under textures, per-set alias lists, absolute paths
{
	const alt = { textures: { per_material: {
		g_arch_zone_a: { base_color: { path: 'tex/a_alb.ktx2' }, rough: 'tex/a_rgh.ktx2',
			materials: [ 'MAT_EXP_ARCH_colonnade_north__MAT_concrete_colonnade' ] },
	} } };
	const m = normaliseManifest( alt, base );
	check( m.materials.count === 1 && m.materials.maps === 2, 'alt: textures.per_material with base_color/rough aliases' );
	check( m.materials.sets.g_arch_zone_a.aliases.length === 1, 'alt: the set keeps its declared material list' );
	check( m.materials.sets.g_arch_zone_a.maps.map.url === 'http://x/assets/gate2/tex/a_alb.ktx2', 'alt: a path with a slash is manifest-relative' );
}

// --- (b) matching ------------------------------------------------------------------------------
{
	const keys = candidateKeys( 'MAT_EXP_ARCH_colonnade_north__MAT_concrete_colonnade' );
	check( keys.includes( 'MAT_concrete_colonnade' ), `match: source material name is a candidate (${keys.length} keys)` );
	check( keys.includes( 'MAT_EXP_ARCH_colonnade_north' ), 'match: the atlas-group half is a candidate' );
	check( keys[ 0 ] === 'MAT_EXP_ARCH_colonnade_north__MAT_concrete_colonnade', 'match: the full name is tried first' );
}

// --- (c) QA-11d-1 chunking ---------------------------------------------------------------------
function batch( name, positions ) {
	const geo = new THREE.BoxGeometry( 1, 1, 1 );
	const mesh = new THREE.InstancedMesh( geo, new THREE.MeshStandardMaterial(), positions.length );
	mesh.name = name;
	const m = new THREE.Matrix4();
	positions.forEach( ( p, i ) => { m.makeTranslation( p[ 0 ], p[ 1 ], p[ 2 ] ); mesh.setMatrixAt( i, m ); } );
	return mesh;
}
{
	const root = new THREE.Group();
	// 120 shrubs over 250 x 166 m, deterministic
	const wide = [];
	for ( let i = 0; i < 120; i ++ ) wide.push( [ - 125 + ( i * 251 ) % 250, 0, - 83 + ( i * 97 ) % 166 ] );
	root.add( batch( 'ENV_shrub_site', wide ) );
	// 60 instances inside one 6 m bed: must NOT be split
	const local = [];
	for ( let i = 0; i < 60; i ++ ) local.push( [ 20 + ( i % 6 ), 0, 5 + ( i % 5 ) ] );
	root.add( batch( 'ENV_shrub_bed', local ) );
	root.updateMatrixWorld( true );

	const before = [];
	root.traverse( o => { if ( o.isInstancedMesh ) before.push( o.count ); } );
	const stats = chunkInstancedMeshes( root );
	const after = [];
	root.traverse( o => { if ( o.isInstancedMesh ) after.push( o ); } );
	check( stats.candidates === 1 && stats.split === 1, `chunk: 1 site-spanning candidate split, the 6 m bed untouched (candidates ${stats.candidates})` );
	check( stats.chunks === 4, `chunk: ${stats.chunks} regional batches from one (maxDepth 2)` );
	check( after.reduce( ( a, o ) => a + o.count, 0 ) === 180, 'chunk: every instance is kept exactly once' );
	const chunks = after.filter( o => o.userData.pfaChunk );
	const maxR = Math.max( ...chunks.map( o => o.boundingSphere.radius ) );
	check( maxR < 0.8 * 150, `chunk: the widest chunk radius is ${maxR.toFixed( 1 )} m, below the 150 m site batch` );
	check( chunks.every( o => /_chunk\d$/.test( o.name ) ), 'chunk: chunks are named <batch>_chunkN (no placeholder-sweep word)' );
	const off = chunkInstancedMeshes( new THREE.Group(), { budget: 0 } );
	check( off.chunks === 0, 'chunk: budget 0 disables it' );
}

console.log( fails ? `${fails} FAILURES` : 'all checks passed' );
process.exit( fails ? 1 : 0 );
