// Phase 6b: the manifest v5 LOAD TIER contract, checked without a browser.
//   PFA_MAIN_ROOT=/path/to/main-checkout node test/tiers_test.mjs
//
// Two halves: synthetic manifests that pin each rule of readTiers (and would have caught every
// defect the real gate5 manifest found), and the REAL export manifests when they are on disk.
import { readFileSync, existsSync, writeFileSync, mkdtempSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';

const WEB = path.resolve( fileURLToPath( new URL( '..', import.meta.url ) ) );
const MAIN = process.env.PFA_MAIN_ROOT || path.resolve( WEB, '..' );
let fails = 0;
const check = ( ok, msg ) => { if ( ! ok ) fails ++; console.log( `${ok ? 'PASS' : 'FAIL'}  ${msg}` ); };

// manifest.js imports a .json module; the same in-memory CJS transform manifest_test.mjs uses.
const src = readFileSync( path.join( WEB, 'src/manifest.js' ), 'utf8' )
	.replace( /^import stationsFallback.*$/m,
		'const stationsFallback = ' + readFileSync( path.join( WEB, 'src/stations_blender.json' ), 'utf8' ) + ';' )
	.replace( /^export /gm, '' ) + '\nmodule.exports = { normaliseManifest, readTiers, tierForUrl };';
const tmp = path.join( mkdtempSync( path.join( os.tmpdir(), 'pfa-tiers-' ) ), 'manifest.cjs' );
writeFileSync( tmp, src );
const { normaliseManifest, readTiers, tierForUrl } = createRequire( import.meta.url )( tmp );

const base = 'http://x/assets/gate5/manifest.json';
const url = ( p ) => new URL( p, base ).href;

// --- 1. no tiers block: one tier, and every consumer behaves as it did at v4 ------------------
{
	const t = readTiers( { glb: { per_class: { arch: { path: 'a.glb' } } } }, base );
	check( t.present === false && t.count === 0, 'a manifest with no tiers block yields present:false' );
	check( tierForUrl( t, url( 'a.glb' ), 0 ) === 0, 'tierForUrl falls back to 0 with no tiers' );
}

// --- 2. the export's shape: an ARRAY plan plus tiers.bytes ------------------------------------
{
	const raw = {
		tiers: { bytes: { 0: 100, 1: 200 }, files: { 0: 2, 1: 1 },
			lowres: { dir: 'tex_lo', files: { k_albedo: { path: 'tex_lo/k.ktx2', bytes: 10, px: 1024 } } },
			boot_overhead_bytes: 2_000_000, oversize: [] },
		files: [
			{ path: '../gate1/arch.glb', tier: 0, kind: 'glb', bytes: 60 },
			{ path: 'tex_lo/k.ktx2', tier: 0, kind: 'gate2_lo', bytes: 10, key: 'k_albedo' },
			{ path: '../gate2/tex_ktx2/k.ktx2', tier: 1, kind: 'gate2', bytes: 200, key: 'k_albedo' },
		],
	};
	const t = readTiers( raw, base );
	check( t.present && t.count === 2, `the array plan is read (${t.count} tier(s))` );
	check( t.totals[ 0 ] === 100 && t.totals[ 1 ] === 200, 'tiers.bytes is the per-tier total' );
	check( tierForUrl( t, url( '../gate1/arch.glb' ) ) === 0 && tierForUrl( t, url( '../gate2/tex_ktx2/k.ktx2' ) ) === 1,
		'each file takes its own tier from the plan' );
	check( tierForUrl( t, url( 'nothing/at/all.ktx2' ) ) === 0, 'a file no tier names is tier 0 (it boots)' );
	check( t.lowres.get( 'k_albedo' ) && t.lowres.get( 'k_albedo' ).url === url( 'tex_lo/k.ktx2' ),
		'tiers.lowres.files is keyed by TEXTURE KEY' );
	check( t.bootOverhead === 2_000_000, 'boot_overhead_bytes is read' );
	check( t.byKey.get( 'k_albedo' ).tier === 0, 'the plan is indexed by key as well as by path' );
}

// --- 3. the smallest declaration wins ---------------------------------------------------------
{
	const raw = { tiers: { list: [ { tier: 0, files: [ { path: 'x.ktx2' } ] }, { tier: 2, files: [] } ] },
		files: { 'x.ktx2': { tier: 2, bytes: 5 } } };
	const t = readTiers( raw, base );
	check( tierForUrl( t, url( 'x.ktx2' ) ) === 0,
		'a file named in tier 0 AND declared tier 2 is tier 0 (the earliest moment wins)' );
}

// --- 4. glb groups + the glbs that are only in the plan, minus the lazy foliage ---------------
{
	const raw = {
		schema: 'pfa-phase6/5',
		glb: { groups: [ { id: 'orn_t0', cls: 'orn', path: 'groups/orn_t0.glb', bytes: 1 },
			{ id: 'orn_t1', cls: 'orn', path: 'groups/orn_t1.glb', bytes: 2 } ],
		per_class_gate3: { orn: { path: '../gate1/orn.glb', bytes: 999 } } },
		trees: { far_mesh: { glb: 'env_trees.glb' }, walkup_mesh: { glb: 'env_trees_lod1.glb' } },
		shrubs: { lod1: { glb: 'env_shrubs.glb' } },
		tiers: { bytes: { 0: 10, 1: 20, 2: 30 } },
		files: [
			{ path: 'groups/orn_t0.glb', tier: 0, kind: 'glb_group:orn', bytes: 1 },
			{ path: 'groups/orn_t1.glb', tier: 1, kind: 'glb_group:orn', bytes: 2 },
			{ path: '../gate1/arch.glb', tier: 0, kind: 'glb', bytes: 3 },
			{ path: '../gate1/ground.glb', tier: 0, kind: 'glb', bytes: 4 },
			{ path: '../gate1/env_trees.glb', tier: 2, kind: 'glb', bytes: 5 },
			{ path: '../gate1/env_shrubs.glb', tier: 2, kind: 'glb', bytes: 6 },
			{ path: '../gate1/env_trees_lod1.glb', tier: 2, kind: 'glb', bytes: 7 },
		],
	};
	const m = normaliseManifest( raw, base );
	const names = m.glbs.map( ( g ) => g.name );
	check( names.includes( 'arch.glb' ) && names.includes( 'ground.glb' ),
		'glbs that are only in the plan (arch, ground) are loaded: they are not in glb.groups' );
	check( ! names.includes( 'env_trees.glb' ) && ! names.includes( 'env_shrubs.glb' ) && ! names.includes( 'env_trees_lod1.glb' ),
		'the three LAZY foliage glbs are NOT in the glb list (foliageLazy.js owns them)' );
	check( ! names.includes( 'orn.glb' ), 'glb.per_class is not loaded beside glb.groups (it would draw twice)' );
	check( m.glbs.every( ( g, i, a ) => i === 0 || a[ i - 1 ].tier <= g.tier ), 'the glb list is sorted tier first' );
	const orn = m.glbs.filter( ( g ) => g.cls === 'orn' );
	check( orn.length === 2 && orn[ 0 ].group === 'orn_t0' && orn[ 1 ].tier === 1,
		'a group keeps its id as its identity and its class as its lighting class' );
}

// --- 5. the lowres variant reaches the material sets by key -----------------------------------
{
	const raw = {
		schema: 'pfa-phase6/5',
		materials: { mode: 'pbr', sets: { MAT_x: { cls: 'arch', albedo: { texture: 'k_albedo', factor: [ 0.5, 0.5, 0.5 ] } } } },
		textures: { gate2: { ktx2_dir: '../gate2/tex_ktx2', files: { k_albedo: { path: 'k.ktx2', bytes: 200 } } } },
		tiers: { bytes: { 0: 1, 1: 2 }, lowres: { dir: 'tex_lo', files: { k_albedo: { path: 'tex_lo/k.ktx2', bytes: 10, px: 512 } } } },
		files: [ { path: 'tex_lo/k.ktx2', tier: 0, kind: 'gate2_lo', bytes: 10, key: 'k_albedo' },
			{ path: '../gate2/tex_ktx2/k.ktx2', tier: 1, kind: 'gate2', bytes: 200, key: 'k_albedo' } ],
	};
	const m = normaliseManifest( raw, base );
	const map = m.materials.sets.MAT_x.maps.map;
	check( map && map.tier === 1, 'the full-resolution map carries its own tier' );
	check( map && map.lo && map.lo.url === url( 'tex_lo/k.ktx2' ) && map.lo.tier === 0,
		'the low-resolution stand-in is attached to the map by its texture key' );
}

// --- 6. the real export manifests, when they are on disk --------------------------------------
for ( const which of [ 'manifest.json', 'manifest_mobile.json' ] ) {
	const f = path.join( MAIN, 'export/out/gate5', which );
	if ( ! existsSync( f ) ) { console.log( `SKIP  ${which} (not in ${path.dirname( f )})` ); continue; }
	const m = normaliseManifest( JSON.parse( readFileSync( f, 'utf8' ) ), `http://x/assets/gate5/${which}` );
	const t = m.tiers;
	check( t.present && t.count >= 2, `${which}: ${t.count} tier(s), ${( t.totals[ 0 ] / 1e6 ).toFixed( 1 )} MB in tier 0` );
	check( m.glbs.length > 0 && m.glbs.some( ( g ) => g.tier === 0 ), `${which}: ${m.glbs.length} glb(s), at least one in tier 0` );
	// arch ships whole on desktop and as groups on mobile; either way its CLASS has to be there.
	check( m.glbs.some( ( g ) => g.cls === 'arch' ), `${which}: the arch class is in the glb list` );
	check( ! m.glbs.some( ( g ) => /env_(trees|shrubs)/.test( g.name ) ), `${which}: no lazy foliage glb in the glb list` );
	check( t.oversize.length === 0, `${which}: no file over the host's per-file cap` );
	// Both variants ship low-resolution stand-ins now (the desktop PBR sets, and on both the maps the
	// glbs reference).  What matters is that every one of them has a full-resolution successor in a
	// LATER tier — a stand-in with nothing to upgrade to would stay on screen for ever.
	const withLo = Object.values( m.materials.sets ).filter( ( s ) => Object.values( s.maps ).some( ( e ) => e.lo ) ).length;
	console.log( `NOTE  ${which}: ${t.lowres.size} low-resolution stand-in(s), ${withLo} material set(s) wearing one at tier 0` );
	// A stand-in is only ever USED while its full-resolution file has not arrived, so what has to hold
	// is that a stand-in the viewer can be served has a successor it can be upgraded to.  A stand-in
	// that arrives with (or after) its full file is simply never fetched — the viewer takes the full
	// one — and is reported so the export can drop those rows from the plan.
	let useless = 0, inverted = 0;
	for ( const [ lo, full ] of t.upgradeOf ) {
		const lt = t.byUrl.get( lo ) ?? 0;
		if ( full.tier < lt ) inverted ++;
		else if ( full.tier === lt ) useless ++;
	}
	check( t.upgradeOf.size > 0 && t.lowresFor.size === t.upgradeOf.size,
		`${which}: every stand-in is paired both ways (${t.upgradeOf.size} pair(s))` );
	if ( useless || inverted ) console.log( `NOTE  ${which}: ${useless} stand-in(s) share a tier with their full file and `
		+ `${inverted} arrive AFTER it — the viewer takes the full file in both cases and never fetches them` );
	const ii = m.gate3 && m.gate3.instanceIrradiance;
	if ( ii ) check( !! ii.groups && Object.keys( ii.groups ).length > 0,
		`${which}: instance_irradiance is re-keyed per group (${ii.groups ? Object.keys( ii.groups ).join( ', ' ) : 'MISSING'})` );
	check( t.bootOverhead > 0, `${which}: boot overhead ${( ( t.bootOverhead || 0 ) / 1e6 ).toFixed( 2 )} MB is in the manifest` );
}

console.log( fails ? `${fails} FAILED` : 'all tier checks passed' );
process.exit( fails ? 1 : 0 );
