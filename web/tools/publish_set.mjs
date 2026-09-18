// Which files a manifest needs published, and where they are on disk.
//
//   node web/tools/publish_set.mjs --manifest <path/to/manifest.json> [--json] [--max-bytes N]
//
// Reads the manifest's v5 `files` table — the export's own list of everything it publishes, with the
// tier each file belongs to — and prints one `<public path>\t<disk path>\t<bytes>\t<tier>` row per
// file.  web/deploy.sh consumes those rows and hard-links each disk file into the publish directory.
//
// The public path of a file is `assets/<its path under export/out>`, because that is how the viewer
// asks for it: the dev server, the preview server and tools/screenshot.mjs all map `/assets/*` onto
// `$PFA_MAIN_ROOT/export/out`, and the deployment has to answer the same urls.  Two things follow:
//   - the manifest itself is published (at `assets/<gate>/manifest.json`), and so is any sibling the
//     viewer fetches by name (uv2_relay_status.json, manifest_mobile.json);
//   - a file the manifest names but nothing on disk answers is REPORTED, never skipped silently —
//     a deployment missing one texture is a deployment with a hole in the building.
//
// Without a v5 `files` table (a v4 manifest) it walks the manifest for path-like strings instead and
// says so: that is the same rule web/tools/stub_tiers.mjs documents, and it publishes more than the
// tiers strictly need.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const WEB = path.resolve( fileURLToPath( new URL( '..', import.meta.url ) ) );
const REPO = path.resolve( WEB, '..' );
const MAIN = process.env.PFA_MAIN_ROOT || REPO;
const ASSETS = process.env.PFA_ASSETS || path.join( MAIN, 'export/out' );

const argv = process.argv.slice( 2 );
const arg = ( k, d ) => { const i = argv.indexOf( `--${k}` ); return i >= 0 ? argv[ i + 1 ] : d; };
const MANIFEST = path.resolve( arg( 'manifest', path.join( ASSETS, 'gate5/manifest.json' ) ) );
const AS_JSON = argv.includes( '--json' );
const MAX_BYTES = Number( arg( 'max-bytes', 25 * 1024 * 1024 ) );

if ( ! fs.existsSync( MANIFEST ) ) { console.error( `publish_set: no manifest at ${MANIFEST}` ); process.exit( 2 ); }
const raw = JSON.parse( fs.readFileSync( MANIFEST, 'utf8' ) );

/** `<ASSETS>/gate3/manifest.json` -> `gate3/manifest.json` (the path the viewer asks for). */
const relOf = ( disk ) => path.relative( ASSETS, disk ).split( path.sep ).join( '/' );
const manifestRel = relOf( MANIFEST );
const manifestDir = path.posix.dirname( manifestRel );

/**
 * A manifest path (relative to the manifest, or an absolute `/assets/...` url) -> its disk file.
 * `dir` is the enclosing `ktx2_dir` / `dir`, which is what a bare file name in a `files` table is
 * relative to.
 */
function toDisk( p, dir = null ) {
	if ( typeof p !== 'string' || ! p ) return null;
	const clean = p.replace( /^\.\//, '' );
	const cands = [];
	const abs = ( u ) => ( u.startsWith( '/assets/' ) ? u.slice( '/assets/'.length ) : null );
	if ( abs( clean ) ) cands.push( abs( clean ) );
	if ( dir ) {
		const d = abs( dir ) || path.posix.normalize( `${manifestDir}/${dir}` );
		cands.push( path.posix.normalize( `${d}/${clean}` ) );
	}
	cands.push( path.posix.normalize( `${manifestDir}/${clean}` ) );
	for ( const rel of cands ) {
		if ( rel.startsWith( '..' ) ) continue;
		const disk = path.join( ASSETS, rel );
		if ( fs.existsSync( disk ) && fs.statSync( disk ).isFile() ) return { rel, disk };
	}
	return null;
}

const rows = new Map();                 // public path -> { disk, bytes, tier, from }
const missing = [];
const add = ( hit, tier, from ) => {
	if ( ! hit ) return;
	const pub = `assets/${hit.rel}`;
	const prev = rows.get( pub );
	// the earliest tier wins, exactly as the viewer reads it
	if ( prev && prev.tier <= tier ) return;
	rows.set( pub, { disk: hit.disk, bytes: fs.statSync( hit.disk ).size, tier, from } );
};

// A manifest UNDER export/out is published with the rest of the bake; one outside it (the
// development stub in web/public/stub/) is already inside the site bundle that `npm run build`
// produces, so it is neither published here nor counted as missing.
const manifestInAssets = ! manifestRel.startsWith( '..' );
const beside = ( name ) => path.join( path.dirname( MANIFEST ), name );
if ( manifestInAssets ) {
	add( { rel: manifestRel, disk: MANIFEST }, 0, 'the manifest' );
	for ( const sib of [ 'uv2_relay_status.json', 'manifest_mobile.json' ] ) {
		const disk = beside( sib );
		if ( fs.existsSync( disk ) ) add( { rel: relOf( disk ), disk }, 0, 'manifest sibling' );
	}
}

let source = 'v5 files table';
// `files` is the ordered load PLAN: an array of { path, tier, kind, key, bytes } as the export
// writes it, or a map keyed by path.  Its paths reach out of the gate5 directory (../gate0 for the
// LUT and the sky, ../gate1 for the glbs, ../gate2 for the PBR sets, ../gate3 for the lightmaps),
// which is exactly why the publish set is built from the PLAN and not from one folder.
if ( raw.files && typeof raw.files === 'object' ) {
	const fileEntries = Array.isArray( raw.files )
		? raw.files.map( ( v ) => [ ( v && v.path ) || '', v ] ).filter( ( [ q ] ) => q )
		: Object.entries( raw.files );
	for ( const [ p, v ] of fileEntries ) {
		const e = ( v && typeof v === 'object' ) ? v : {};
		const tier = Number.isFinite( e.tier ) ? e.tier : 0;
		const hit = toDisk( e.path || p );
		if ( ! hit ) {
			// A file that sits beside a manifest outside export/out is part of the site bundle, not of
			// the bake: `npm run build` has already copied it.  Anything else is a hole.
			if ( ! manifestInAssets && fs.existsSync( beside( e.path || p ) ) ) continue;
			missing.push( { path: e.path || p, tier } ); continue;
		}
		add( hit, tier, 'files[]' );
		const lo = e.lo || e.low || e.variant_lo;
		if ( lo && lo.path ) {
			const lh = toDisk( lo.path );
			if ( lh ) add( lh, Number.isFinite( lo.tier ) ? lo.tier : 0, 'files[].lo' ); else missing.push( { path: lo.path, tier: lo.tier ?? 0 } );
		}
	}
} else {
	// v4 fallback: every path-like string in the manifest, with the enclosing dir for bare names.
	source = 'walked (no v5 files table)';
	const EXT = /\.(glb|gltf|ktx2|hdr|cube|png|jpe?g|webp)$/i;
	const DIR_KEY = /^(dir|.*_dir)$/;
	const walk = ( node, dir ) => {
		if ( Array.isArray( node ) ) { for ( const v of node ) walk( v, dir ); return; }
		if ( node && typeof node === 'object' ) {
			const own = Object.entries( node ).find( ( [ k, v ] ) => DIR_KEY.test( k ) && typeof v === 'string' );
			for ( const v of Object.values( node ) ) walk( v, own ? own[ 1 ] : dir );
			return;
		}
		if ( typeof node !== 'string' || ! EXT.test( node ) ) return;
		const hit = toDisk( node, dir );
		if ( hit ) add( hit, 0, 'walked' );
	};
	walk( raw, null );
}

// --------------------------------------------------------------- files nothing NAMES by path
// Two sets of files the manifest references without ever writing their path, both of which a
// publish set that trusted `files[]` alone would leave out — and a missing texture is a hole in the
// building, found only when someone looks at the deployment:
//   1. a texture referenced by KEY: `materials.detail.sets[*].maps[*].texture` is
//      "detail_concrete_wall_008_albedo" and the file is `<ktx2_dir>/<key>.ktx2` (or `<dir>/<key>.png`);
//      the same holds for every key in a `textures.*.files` table that carries no `path`.
//   2. a texture the GLB references itself: gltfpack -tr leaves the leaf and bark maps external, so
//      their names are in the glb's own glTF JSON (`images[].uri`) and nowhere else.
// Both are added here and REPORTED as `byReference`, so the export can put them in `files[]` — this
// is a safety net, not the contract.
const byReference = [];
const addRef = ( hit, tier, why ) => { if ( ! hit ) return false; const pub = `assets/${hit.rel}`;
	if ( rows.has( pub ) ) return false; add( hit, tier, why ); byReference.push( { path: pub, why } ); return true; };

// 1. keys -> <dir>/<key>.<ext>.  A key is resolved against its ENCLOSING dir first and then against
// every other directory the manifest declares, because that is what the viewer does: the detail
// tiling sets name `detail_concrete_wall_008_albedo` with no dir of their own and the file is in
// `textures.gate2.ktx2_dir` (src/manifest.js `detailUrl`).
const dirsSeen = [];
const allDirs = ( node ) => {
	if ( Array.isArray( node ) ) { for ( const v of node ) allDirs( v ); return; }
	if ( ! node || typeof node !== 'object' ) return;
	for ( const [ k, v ] of Object.entries( node ) ) {
		if ( typeof v === 'string' && /^(dir|.*_dir)$/.test( k ) ) dirsSeen.push( v ); else allDirs( v );
	}
};
allDirs( raw );
const collectKeys = ( node, dir ) => {
	if ( Array.isArray( node ) ) { for ( const v of node ) collectKeys( v, dir ); return; }
	if ( ! node || typeof node !== 'object' ) return;
	const own = Object.entries( node ).find( ( [ k, v ] ) => /^(dir|.*_dir)$/.test( k ) && typeof v === 'string' );
	const d = own ? own[ 1 ] : dir;
	for ( const [ k, v ] of Object.entries( node ) ) {
		if ( typeof v === 'string' && ( k === 'texture' || k === 'albedo' || k === 'normal_depth' || k === 'albedo_2k' )
			&& ! /[./]/.test( v ) ) {
			let got = false;
			for ( const dd of [ d, ...dirsSeen ] ) {
				for ( const ext of [ 'ktx2', 'png' ] ) if ( ( got = addRef( toDisk( `${v}.${ext}`, dd ), 0, `key "${k}"` ) ) ) break;
				if ( got ) break;
			}
		} else collectKeys( v, d );
	}
};
collectKeys( raw, null );
// The `textures.*.files` tables are NOT swept: everything in them that the viewer actually loads is
// already in `files[]`, and the tables also list the alternate encodings the viewer never fetches
// (every lightmap ships rgbm8 AND gamma2; `lightmaps.*.default` picks one).  Publishing the spares
// would add ~100 MB to a deployment that nothing would ever request.

// 1b. `materials.foliage` names a DIRECTORY and a size and builds its file names in the viewer
// (src/foliageLazy.js: `foliage_<material>_<albedo|translu>_<size>.ktx2`), so no key and no path in
// the manifest ever spells them.  That one directory is therefore published whole — with a guard, so
// a mis-declared dir cannot drag the whole bake in.
const folDir = raw.materials && raw.materials.foliage && raw.materials.foliage.dir;
if ( folDir ) {
	const hit = toDisk( '.', folDir );
	const dirRel = hit ? path.posix.dirname( hit.rel ) : null;
	const diskDir = dirRel ? path.join( ASSETS, dirRel ) : null;
	let base = diskDir;
	if ( ! base ) {
		for ( const cand of [ path.posix.normalize( `${manifestDir}/${folDir}` ),
			folDir.replace( /^out\//, '' ), folDir.replace( /^\/assets\//, '' ) ] ) {
			const d = path.join( ASSETS, cand );
			if ( fs.existsSync( d ) && fs.statSync( d ).isDirectory() ) { base = d; break; }
		}
	}
	if ( base ) {
		const names = fs.readdirSync( base ).filter( ( n ) => fs.statSync( path.join( base, n ) ).isFile() );
		const bytes = names.reduce( ( a, n ) => a + fs.statSync( path.join( base, n ) ).size, 0 );
		if ( names.length > 200 || bytes > 100e6 ) {
			console.error( `publish_set: materials.foliage.dir (${folDir}) holds ${names.length} file(s) / ${( bytes / 1e6 ).toFixed( 0 )} MB — too much to publish blind, skipped` );
		} else for ( const n of names ) addRef( { rel: `${relOf( base )}/${n}`, disk: path.join( base, n ) }, 0, 'materials.foliage.dir' );
	} else console.error( `publish_set: materials.foliage.dir "${folDir}" is not a directory under ${ASSETS}` );
}

// 2. external uris inside each published glb (the glTF JSON chunk of a .glb)
for ( const [ pub, r ] of [ ...rows.entries() ] ) {
	if ( ! /\.glb$/i.test( pub ) ) continue;
	try {
		const fd = fs.openSync( r.disk, 'r' );
		const head = Buffer.alloc( 20 );
		fs.readSync( fd, head, 0, 20, 0 );
		if ( head.readUInt32LE( 0 ) !== 0x46546c67 ) { fs.closeSync( fd ); continue; }   // "glTF"
		const jsonLen = head.readUInt32LE( 12 );
		const json = Buffer.alloc( jsonLen );
		fs.readSync( fd, json, 0, jsonLen, 20 );
		fs.closeSync( fd );
		const g = JSON.parse( json.toString( 'utf8' ) );
		const dir = path.posix.dirname( pub.slice( 'assets/'.length ) );
		for ( const src of [ ...( g.images || [] ), ...( g.buffers || [] ) ] ) {
			if ( ! src.uri || /^data:/.test( src.uri ) ) continue;
			const rel = path.posix.normalize( `${dir}/${src.uri}` );
			if ( rel.startsWith( '..' ) ) continue;
			const disk = path.join( ASSETS, rel );
			if ( fs.existsSync( disk ) ) addRef( { rel, disk }, r.tier, `referenced by ${path.posix.basename( pub )}` );
			else missing.push( { path: src.uri, tier: r.tier, from: pub } );
		}
	} catch { /* a glb we cannot parse is not a reason to fail the publish set */ }
}

const list = [ ...rows.entries() ].map( ( [ pub, r ] ) => ( { path: pub, disk: r.disk, bytes: r.bytes, tier: r.tier, from: r.from } ) )
	.sort( ( a, b ) => a.tier - b.tier || a.path.localeCompare( b.path ) );
const oversize = list.filter( ( r ) => r.bytes > MAX_BYTES );
const byTier = {};
for ( const r of list ) { byTier[ r.tier ] = byTier[ r.tier ] || { files: 0, bytes: 0 }; byTier[ r.tier ].files ++; byTier[ r.tier ].bytes += r.bytes; }

if ( AS_JSON ) {
	console.log( JSON.stringify( { manifest: MANIFEST, assets_root: ASSETS, source, files: list, oversize, by_tier: byTier, missing, by_reference: byReference }, null, 1 ) );
} else {
	for ( const r of list ) console.log( `${r.path}\t${r.disk}\t${r.bytes}\t${r.tier}` );
	console.error( `publish_set: ${list.length} file(s) from ${source}, `
		+ Object.entries( byTier ).map( ( [ t, v ] ) => `tier ${t}: ${v.files} files ${( v.bytes / 1e6 ).toFixed( 1 )} MB` ).join( ', ' )
		+ `; ${oversize.length} over ${( MAX_BYTES / 1024 / 1024 ).toFixed( 0 )} MiB`
		+ ( byReference.length ? `; ${byReference.length} found BY REFERENCE and not in files[] (${[ ...new Set( byReference.map( b => b.why ) ) ].slice( 0, 4 ).join( ', ' )}) — the export should list them` : '' )
		+ ( missing.length ? `; ${missing.length} NAMED BUT NOT ON DISK: ${missing.slice( 0, 6 ).map( m => m.path ).join( ', ' )}` : '' ) );
}
if ( missing.length ) process.exitCode = 3;
