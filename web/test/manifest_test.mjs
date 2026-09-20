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

// --- the two specular-gate constants, as export/manifest_v4.py writes them ----------------------
// docs/briefs/phase9_bake_analysis_report.md B.6.  These are SCHEMA checks on the raw manifests, not
// on the viewer's reading of them: a wrong shape here makes the gate silently wrong at both ends, and
// the viewer can only fall back to the ungated Phase 8 path (which is the station-3 defect itself).
// Both are re-derived by manifest_v4 on every run, so a re-baked sky or a re-energised sun feeds them
// with no viewer change - which is exactly why the SHAPE, not the value, is what is pinned.
for ( const [ gate, rel ] of [ [ 'gate3', 'export/out/gate3/manifest.json' ],
	[ 'gate5 desktop', 'export/out/gate5/manifest.json' ],
	[ 'gate5 mobile', 'export/out/gate5/manifest_mobile.json' ] ] ) {
	const f = path.join( MAIN, rel );
	if ( ! existsSync( f ) ) { console.log( `      ${gate}: no manifest at ${f}, skipped` ); continue; }
	const raw = JSON.parse( readFileSync( f ) );
	const sky = raw.sky && raw.sky.open_irradiance_over_pi;
	const sun = raw.sun && raw.sun.irradiance_over_pi;
	if ( sky === undefined && sun === undefined ) {
		console.log( `      ${gate}: no spec-gate constants yet (export/manifest_v4.py has not been re-run `
			+ `into this manifest; tiers.py carries them from gate3), skipped` );
		continue;
	}
	check( Array.isArray( sky ) && sky.length === 3 && sky.every( v => typeof v === 'number' && isFinite( v ) && v > 0 ),
		`${gate}: sky.open_irradiance_over_pi is 3 finite positive numbers (${JSON.stringify( sky )})` );
	// LIGHT_sun ships at (1, 0.607, 0) — zero blue — so the open sky's blue is the largest channel by a
	// wide margin and its red/blue ratio is what sunVis subtracts.  A manifest where that is not true is
	// not this scene's sky, and the gate would read the sun's own light as sky.
	if ( Array.isArray( sky ) && sky.length === 3 )
		check( sky[ 2 ] > sky[ 1 ] && sky[ 1 ] > sky[ 0 ] && sky[ 0 ] / sky[ 2 ] < 0.5,
			`${gate}: the open sky is blue-dominant, r/b = ${( sky[ 0 ] / sky[ 2 ] ).toFixed( 4 )}` );
	check( typeof sun === 'number' && isFinite( sun ) && sun > 0, `${gate}: sun.irradiance_over_pi = ${sun}` );
	if ( typeof sun === 'number' && typeof ( raw.sun || {} ).energy_w_m2 === 'number' )
		check( Math.abs( sun - raw.sun.energy_w_m2 / Math.PI ) < 1e-5,
			`${gate}: sun.irradiance_over_pi is energy_w_m2 / pi (${raw.sun.energy_w_m2} / pi)` );
	// sunVis reads the RED channel, after subtracting the sky's own red share.  For that to separate
	// "sunlit" from "open to the sky" at all, the sun's red at dotNL = 1 has to dominate the open sky's
	// red: 21.43 against 2.196 here, 9.8x.  Below ~4x the two bands overlap and the gate is guesswork.
	if ( Array.isArray( sky ) && typeof sun === 'number' )
		check( sun > 4 * sky[ 0 ], `${gate}: sun/pi ${sun.toFixed( 3 )} dominates the open sky's red `
			+ `${sky[ 0 ].toFixed( 3 )} (${( sun / sky[ 0 ] ).toFixed( 1 )}x), so sunVis separates the two bands` );
}
console.log( fails ? `${fails} FAILURES` : 'all manifest checks passed' );
process.exit( fails ? 1 : 0 );
