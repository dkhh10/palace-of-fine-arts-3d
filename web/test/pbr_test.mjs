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

// --- (a2) the REAL v3 contract (export/README.md "manifest.json v3") ---------------------------
{
	const real = {
		schema: 'pfa-phase6/3', gate: 'gate2',
		textures: {
			ktx2_dir: 'tex_ktx2', files: [ 'orn_capital_rotunda_v1_ao.ktx2', 'bark_bluegum_diff_2k.ktx2' ],
			gate2: {
				ktx2_dir: '../gate2/tex_ktx2', bytes: 3000, resident_mb: 16.0,
				files: {
					gate2_arch_rotunda__MAT_column_rose_albedo: { path: 'gate2_arch_rotunda__MAT_column_rose_albedo.ktx2', w: 2048, h: 2048, map: 'albedo', colorspace: 'srgb', cls: 'arch', bytes: 2000, resident_mb: 5.33 },
					gate2_arch_rotunda__MAT_column_rose_roughness: { path: 'gate2_arch_rotunda__MAT_column_rose_roughness.ktx2', w: 2048, h: 2048, map: 'roughness', colorspace: 'linear', cls: 'arch', bytes: 1000, resident_mb: 5.33 },
				},
			},
		},
		materials: {
			mode: 'pbr', uv: 'TEXCOORD_0', constant_threshold: 0.02,
			colorspace: { albedo: 'srgb', roughness: 'linear', normal: 'linear', occlusion: 'linear' },
			sets: {
				'MAT_EXP_ARCH_rotunda__MAT_column_rose': {
					job: 'arch_rotunda__MAT_column_rose', cls: 'arch', src_material: 'MAT_column_rose', size: 2048,
					albedo: { texture: 'gate2_arch_rotunda__MAT_column_rose_albedo', factor: [ 0.35, 0.22, 0.18 ] },
					roughness: { texture: 'gate2_arch_rotunda__MAT_column_rose_roughness', factor: 0.83 },
					normal: { texture: null, scale: 1.0 },
					metallic: { texture: null, constant: true, factor: 0.0 },
					occlusion: { texture: 'gate2_not_a_file' },      // a key in neither index
					uv1_in_glb: true,
				},
				'MAT_EXP_ORN__ORN_capital_rotunda_v1_LOD0_a': {
					job: 'orn_capital_rotunda_v1', cls: 'orn', src_material: null, size: 1024,
					albedo: { texture: null, constant: true, factor: [ 0.5, 0.47, 0.42 ] },
					occlusion: { texture: 'orn_capital_rotunda_v1_ao' },
					uv1_in_glb: true,
				},
				'MAT_EXP_ENVBD__MAT_backdrop_building': {
					job: 'backdrop_building', cls: 'backdrop', size: 1024,
					albedo: { texture: 'gate2_backdrop_building_albedo', factor: [ 0.28, 0.27, 0.26 ] },
					roughness: { texture: null, constant: true, factor: 0.9 },
					uv1_in_glb: false,
				},
			},
		},
		budget: { resident_mb: { total: 980.0 }, budget_mb: 1200 },
	};
	const m = normaliseManifest( real, base );
	const rose = m.materials.sets[ 'MAT_EXP_ARCH_rotunda__MAT_column_rose' ];
	check( rose.maps.map.url === 'http://x/assets/gate2/tex_ktx2/gate2_arch_rotunda__MAT_column_rose_albedo.ktx2',
		`v3 real: a texture KEY resolves through textures.gate2.files + ktx2_dir -> ${rose.maps.map.url.split( '/' ).pop()}` );
	check( rose.maps.map.srgb === true && rose.maps.roughnessMap.srgb === false, 'v3 real: colour space from the file entry' );
	check( JSON.stringify( rose.factors.map ) === '[0.35,0.22,0.18]' && rose.factors.roughnessMap === 0.83,
		'v3 real: albedo and roughness factors kept alongside their textures' );
	check( rose.factors.metalnessMap === 0 && ! rose.maps.metalnessMap, 'v3 real: metallic texture null + constant -> factor only' );
	check( ! rose.maps.normalMap && rose.normalScale === 1.0, 'v3 real: a null normal texture leaves no map but keeps scale' );
	const cap = m.materials.sets[ 'MAT_EXP_ORN__ORN_capital_rotunda_v1_LOD0_a' ];
	check( cap.maps.aoMap && cap.maps.aoMap.url.endsWith( 'tex_ktx2/orn_capital_rotunda_v1_ao.ktx2' ),
		'v3 real: an ORN occlusion key carried from Gate 1 resolves through the v2 file list' );
	check( ! cap.maps.map && JSON.stringify( cap.factors.map ) === '[0.5,0.47,0.42]', 'v3 real: a constant albedo is the factor, no file' );
	const bd = m.materials.sets[ 'MAT_EXP_ENVBD__MAT_backdrop_building' ];
	check( Object.keys( bd.maps ).length === 0 && bd.factors.map && bd.factors.roughnessMap === 0.9,
		'v3 real: uv1_in_glb false -> factors only, no texture requested' );
	check( m.materials.constantMaps === 4 && m.materials.withoutUv1 === 1,
		`v3 real: ${m.materials.constantMaps} constant maps, ${m.materials.withoutUv1} set without UV1` );
	check( m.materials.budget.budget_mb === 1200 && m.materials.gate2Textures.files === 2, 'v3 real: budget and the gate2 texture index are carried' );
	check( ! rose.maps.aoMap && m.notes.some( n => /not in textures\.gate2\.files/.test( n ) && /gate2_not_a_file/.test( n ) ),
		'v3 real: an unresolvable key is skipped AND reported, not silently dropped' );
	check( ! m.notes.some( n => /gate2_backdrop_building_albedo/.test( n ) ),
		'v3 real: a uv1_in_glb false set requests nothing, so its key is not reported as unresolvable' );
	check( pbrPlan( m.materials.sets ).length === 3, 'v3 real: the byte plan has the 3 real files (the constants cost nothing)' );
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
