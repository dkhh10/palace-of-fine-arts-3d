// Verifies src/manifest.js against the REAL export manifests, without a browser.
//   PFA_MAIN_ROOT=/path/to/main-checkout node test/manifest_test.mjs
//
// The blocker found at Gate 1 was that `glb.per_class` — the only shape export/gltf_pack.sh --gate1
// writes — was not in the pick list, so the viewer silently rendered the test scene.  This test pins
// that shape (built here exactly as gltf_pack.sh writes it, so it can be checked before the glbs
// exist), plus the v2 fields the viewer depends on.
//
// manifest.js imports a .json module, which node will not do without an import attribute, so the
// source is transformed to CJS in memory rather than duplicating the normaliser.
import { readFileSync, existsSync, writeFileSync, mkdtempSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';

const WEB = path.resolve( fileURLToPath( new URL( '..', import.meta.url ) ) );
const MAIN = process.env.PFA_MAIN_ROOT || path.resolve( WEB, '..' );
let fails = 0;
const check = ( ok, msg ) => { if ( ! ok ) fails ++; console.log( `${ok ? 'PASS' : 'FAIL'}  ${msg}` ); };

const src = readFileSync( path.join( WEB, 'src/manifest.js' ), 'utf8' )
	.replace( /^import stationsFallback.*$/m,
		'const stationsFallback = ' + readFileSync( path.join( WEB, 'src/stations_blender.json' ), 'utf8' ) + ';' )
	.replace( /^export /gm, '' ) + '\nmodule.exports = { normaliseManifest };';
const tmp = path.join( mkdtempSync( path.join( os.tmpdir(), 'pfa-manifest-' ) ), 'manifest.cjs' );
writeFileSync( tmp, src );
const { normaliseManifest } = createRequire( import.meta.url )( tmp );

// --- the glb shape export/gltf_pack.sh --gate1 writes ------------------------------------------
const perClass = { glb: { per_class: {
	arch: { path: 'arch.glb', bytes: 1, placed_tris: 844554, objects: 564, meshes: 40 },
	orn: { path: 'orn.glb', bytes: 2, placed_tris: 1099194, objects: 436, meshes: 33 },
	env: { path: 'env.glb', bytes: 3, placed_tris: 792822, objects: 1540, meshes: 74 },
	ground: { path: 'ground.glb', bytes: 4, placed_tris: 1, objects: 1, meshes: 1 },
}, total_bytes: 10, gltfpack: '-cc -mi' } };

const base = 'http://x/assets/gate1/manifest.json';
{
	const m = normaliseManifest( perClass, base );
	check( m.glbs.length === 4, `glb.per_class -> ${m.glbs.length} glbs (expected 4, never 0: 0 means the test scene)` );
	check( m.glbs.map( g => g.cls ).join( ',' ) === 'arch,orn,env,ground',
		`load order ${m.glbs.map( g => g.cls ).join( ',' )} (expected arch,orn,env,ground)` );
	check( m.glbs.every( g => /\/assets\/gate1\/[a-z]+\.glb$/.test( g.url ) ), 'every url resolves next to the manifest' );
	check( m.glbs[ 1 ].bytes === 2, 'declared bytes carried for the progress bar' );
}
// the Gate 0 single-glb object must still be ONE file, not a map of its metadata keys
{
	const m = normaliseManifest( { glb: { path: 'gate0.glb', bytes: 5, texture_source: 'ktx2',
		instanced_variant: { path: 'gate0_instanced.glb', bytes: 6 }, gltfpack: '-cc -mi -kn' } }, base );
	check( m.glbs.length === 1 && m.glbs[ 0 ].name === 'gate0.glb',
		`gate0 shape -> ${m.glbs.length} glb (${m.glbs.map( g => g.name ).join( ',' )}), the variant is not loaded too` );
}

// --- the real synced manifests -----------------------------------------------------------------
for ( const gate of [ 'gate1', 'gate0' ] ) {
	const f = path.join( MAIN, 'export/out', gate, 'manifest.json' );
	if ( ! existsSync( f ) ) { console.log( `      ${gate}: no manifest at ${f}, skipped` ); continue; }
	const raw = JSON.parse( readFileSync( f ) );
	const m = normaliseManifest( { ...raw, ...( raw.glb ? {} : perClass ) }, base );
	const tag = `${gate} (${m.schema})`;
	check( m.glbs.length > 0, `${tag}: ${m.glbs.length} glb(s)` );
	check( m.stations.length >= 6 && m.stations[ 0 ].name === 'CAM_qa_01_lagoon_hero' && m.stations[ 5 ].index === 6,
		`${tag}: stations 1-6 are the QA cameras (${m.stations.length} total, extras after 6)` );
	check( m.waterZ === - 1.3, `${tag}: water ${m.waterZ}` );
	check( !! ( m.lut && m.lut.url ) && !! m.sky.camera, `${tag}: lut + sky present (else the viewer borrows gate0's)` );
	check( m.notes.filter( n => /has no path, ignored/.test( n ) ).length === 0, `${tag}: no per-asset lightmap warnings` );
	if ( gate === 'gate1' ) {
		check( m.treesFar.length > 0 && m.treesFar.every( t => t.base && t.height > 0 ),
			`${tag}: ${m.treesFar.length} far-tree billboards, all with a trunk base and a height` );
		check( m.ornSlots && m.ornSlots.orn && m.ornSlots.orn.entries > 0,
			`${tag}: orn_slots ${JSON.stringify( m.ornSlots )}` );
	}
}
console.log( fails ? `${fails} FAILURES` : 'all manifest checks passed' );
process.exit( fails ? 1 : 0 );
