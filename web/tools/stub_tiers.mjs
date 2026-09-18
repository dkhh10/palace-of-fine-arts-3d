// Build a STUB manifest v5 (`pfa-phase6/5`) from the real v4 one, so the progressive-loading path can
// be developed and captured before the export engineer's gate5 manifest lands in MAIN.
//
//   PFA_MAIN_ROOT=/path/to/main node web/tools/stub_tiers.mjs [--out web/public/stub/gate5] [--lo-stand-in]
//
// IT IS A STUB, AND IT SAYS SO: the output carries `tiers.stub` with the rule below and the viewer
// prints it.  Nothing here is a substitute for export/tiers.py — it cannot split orn.glb into
// per-tier groups (that needs gltfpack) and it cannot make a low-resolution texture variant (that
// needs toktx).  What it CAN do is give the viewer a real `tiers` / `files` / `glb.groups` block over
// the real files, which is all the streaming path needs to be written and measured against.
//
// THE RULE (documented, deterministic, and the only thing that changes when the real manifest lands):
//   tier 0  what the hero station needs for a first frame: the LUT, both sky equirects + the diffuse
//           one, the hero probe, arch.glb + ground.glb, and the lightmaps / PBR / detail textures of
//           the ARCH and GROUND classes (the ground lightmaps included: the ground is half the hero
//           frame and an unlit ground is not a first look).
//   tier 1  orn.glb, the ORN lightmap atlases and ORN textures, the far-tree impostor atlases.
//   tier 2  env.glb, the ENV textures and lightmaps, the foliage texture set and the three lazily
//           loaded foliage glbs (env_trees, env_shrubs, walk-up) — everything the walker reaches
//           after standing still.
// Every path is rewritten to an ABSOLUTE /assets/<gate>/... url, and only when the file it names is
// on disk; a path that resolves to nothing is left exactly as written and listed under
// `tiers.stub.unresolved`, so a wrong rewrite can never be mistaken for a missing file.
//
// --lo-stand-in additionally gives every tier-1 ARCH albedo a `lo` variant pointing at ANOTHER real
// texture (there is no low-resolution set on disk).  It exercises the hot-swap end to end — the frame
// visibly changes when tier 1 lands and must return to the full-resolution look — and it is marked
// `stand_in: true` in the manifest and refused by any scored capture.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const WEB = path.resolve( fileURLToPath( new URL( '..', import.meta.url ) ) );
const REPO = path.resolve( WEB, '..' );
const MAIN = process.env.PFA_MAIN_ROOT || REPO;
const OUT_ROOT = path.join( MAIN, 'export/out' );

const argv = process.argv.slice( 2 );
const arg = ( k, d ) => { const i = argv.indexOf( `--${k}` ); return i >= 0 ? argv[ i + 1 ] : d; };
const LO_STAND_IN = argv.includes( '--lo-stand-in' );
const SRC = path.resolve( arg( 'src', path.join( OUT_ROOT, 'gate3/manifest.json' ) ) );
const OUT_DIR = path.resolve( REPO, arg( 'out', 'web/public/stub/gate5' ) );
const SRC_GATE = path.basename( path.dirname( SRC ) );                 // "gate3"

const raw = JSON.parse( fs.readFileSync( SRC, 'utf8' ) );

// ---------------------------------------------------------------------------- path rewriting
const unresolved = [];
const rewritten = new Map();                 // absolute url -> on-disk file
const EXT = /\.(glb|gltf|ktx2|hdr|exr|png|jpe?g|webp|cube|json|npz|bin)$/i;

/** Candidate on-disk spellings of a manifest path, in the order lazyUrlCandidates tries them.
 *  `dir` is the nearest enclosing `ktx2_dir` / `dir` field: `textures.gate2.files[k].path` is a bare
 *  file name that only means anything joined to `textures.gate2.ktx2_dir`. */
function candidates( p, dir ) {
	const clean = String( p ).replace( /^\.\//, '' );
	const base = clean.split( '/' ).pop();
	const out = [];
	if ( dir ) out.push( path.posix.normalize( `${SRC_GATE}/${dir}/${clean}` ) );
	out.push( path.posix.normalize( `${SRC_GATE}/${clean}` ) );
	if ( /^out\//.test( clean ) ) out.push( path.posix.normalize( clean.replace( /^out\//, '' ) ) );
	if ( ! clean.includes( '/' ) ) out.push( `gate1/${base}` );
	return [ ...new Set( out ) ].filter( ( c ) => ! c.startsWith( '..' ) );
}

/**
 * "../gate1/arch.glb" -> "/assets/gate1/arch.glb", but only when that file (or dir) exists.
 * Returns { url, usedDir }: `usedDir` means the path only resolved once the enclosing `ktx2_dir` /
 * `dir` was prepended, and THAT STRING MUST BE LEFT AS IT IS.  The two consumers join a dir to a path
 * differently — manifest.js's joinDir drops the dir when the path is absolute, while the probe block
 * concatenates the two — so rewriting a dir-relative path to an absolute url produced
 * `/assets/gate3/probe//assets/gate3/probe/...`.  Rewriting the DIR alone is right for both.
 */
function toAbs( p, wantDir = false, dir = null ) {
	if ( typeof p !== 'string' || ! p || /^(https?:)?\//.test( p ) ) return null;
	const withDir = candidates( p, wantDir ? null : dir );
	const withoutDir = candidates( p, null );
	for ( const rel of withDir ) {
		const disk = path.join( OUT_ROOT, rel );
		if ( ! fs.existsSync( disk ) ) continue;
		if ( fs.statSync( disk ).isDirectory() !== wantDir ) continue;
		const url = `/assets/${rel}`;
		if ( ! wantDir ) rewritten.set( url, disk );
		return { url, usedDir: ! withoutDir.includes( rel ) };
	}
	unresolved.push( p );
	return null;
}

const DIR_KEY = /^(dir|.*_dir)$/;
/** Deep copy with every path string rewritten, remembering where each url was found. */
const found = [];                            // { url, jsonPath }
function walk( node, keyPath, dir ) {
	if ( Array.isArray( node ) ) return node.map( ( v, i ) => walk( v, `${keyPath}[${i}]`, dir ) );
	if ( node && typeof node === 'object' ) {
		// An object that declares a directory sets it for its whole subtree (textures.gate2.ktx2_dir
		// governs textures.gate2.files[*].path, which is a bare file name).
		const own = Object.entries( node ).find( ( [ k, v ] ) => DIR_KEY.test( k ) && typeof v === 'string' );
		const sub = own ? own[ 1 ] : dir;
		const out = {};
		for ( const [ k, v ] of Object.entries( node ) ) out[ k ] = walk( v, keyPath ? `${keyPath}.${k}` : k, sub );
		return out;
	}
	if ( typeof node !== 'string' ) return node;
	const key = keyPath.split( '.' ).pop().replace( /\[\d+\]$/, '' );
	if ( DIR_KEY.test( key ) ) { const a = toAbs( node, true ); return a ? a.url : node; }
	if ( ! EXT.test( node ) ) return node;
	const a = toAbs( node, false, dir );
	if ( ! a ) return node;
	found.push( { url: a.url, jsonPath: keyPath } );
	return a.usedDir ? node : a.url;                 // a dir-relative path stays relative to its dir
}
const m = walk( raw, '', null );

// ---------------------------------------------------------------------------- tiers
const TIER_OF_CLASS = { arch: 0, ground: 0, orn: 1, backdrop: 2, env: 2 };

/** Which tier a url belongs to, from WHERE in the manifest it was found and what it is called. */
function classify( url, jsonPath ) {
	const p = jsonPath;
	const f = url.split( '/' ).pop();
	if ( /^(lut|sky|probe)\b/.test( p ) || /^view\./.test( p ) ) return 0;
	if ( /^glb\./.test( p ) ) {
		const cls = p.split( '.' )[ 2 ] || '';                 // glb.per_class.<cls>.path
		return TIER_OF_CLASS[ cls ] ?? 2;
	}
	if ( /^impostors\./.test( p ) ) return 1;
	if ( /^(trees|shrubs)\./.test( p ) ) return 2;
	if ( /^materials\.detail\./.test( p ) ) return 0;          // the shared tiling grain: arch needs it
	if ( /^materials\.foliage\./.test( p ) ) return 2;
	// The Gate 2 PBR sets are tier 1 on purpose: manifest v3 rule 3 already ships each map's MEAN as a
	// factor, so tier 0 draws the lightmapped building in its mean albedo and tier 1 sharpens it.  That
	// is the "low-resolution first look" the user allowed, without inventing a texture set.
	if ( /^textures\.gate2\./.test( p ) || /^gate2_/.test( f ) ) return 1;
	if ( /gate3_imp_|gate3_lmatlas_/.test( f ) ) return 1;     // impostor atlases, ORN + ARCH_inst slots
	// own-asset lightmaps: the hero's masses and its ground are the first frame, the rest is not.
	if ( /gate3_lmg?1?_?ARCH_|terrain_ground|lagoon_bed|ground_colonnade_walk|riprap/.test( f ) ) return 0;
	if ( /_ORN_|_orn_/.test( f ) ) return 1;
	return 2;                                                  // unknown: it is not the first frame
}

const files = {};
const bytesOf = ( url ) => { const d = rewritten.get( url ); try { return d ? fs.statSync( d ).size : null; } catch { return null; } };
// Every lightmap ships in two encodings and the viewer loads ONE of them (`default`, gamma2 since
// Gate 3).  Counting both would make every tier total nearly twice what the viewer downloads, and the
// loading screen's denominator is that total, so the variant nothing loads is dropped here — with the
// manifest's own `default` checked rather than assumed.
const defaults = new Set();
const collectDefaults = ( o ) => {
	if ( ! o || typeof o !== 'object' ) return;
	if ( o.textures && typeof o.textures === 'object' && o.default ) defaults.add( String( o.default ) );
	for ( const v of Object.values( o ) ) collectDefaults( v );
};
collectDefaults( m.lightmaps );
const DROPPED_VARIANT = defaults.size === 1 && defaults.has( 'gamma2' ) ? 'rgbm8' : null;
const urlSet = new Set( found.map( ( f ) => f.url ) );
const pathSet = new Set( found.map( ( f ) => f.jsonPath ) );
/** The other files the manifest names but the viewer never fetches: the 32-bit .exr twin of every
 *  sky equirect (manifest.js's skyFile takes the .hdr), the LUT's strip PNG (the .cube is loaded),
 *  and the .npz intermediates.  Counting them would nearly double every tier total. */
const skipUnfetched = ( { url, jsonPath } ) => {
	const key = jsonPath.split( '.' ).pop();
	if ( key === 'exr' && pathSet.has( jsonPath.replace( /\.exr$/, '.hdr' ) ) ) return true;
	if ( key === 'strip_png' ) return true;
	if ( /\.npz$/i.test( url ) ) return true;
	return false;
};
const skipVariant = ( url ) => DROPPED_VARIANT
	&& url.endsWith( `_${DROPPED_VARIANT}.ktx2` )
	&& urlSet.has( url.replace( `_${DROPPED_VARIANT}.ktx2`, '_gamma2.ktx2' ) );
let droppedVariants = 0;
for ( const f of found ) {
	const { url, jsonPath } = f;
	if ( skipVariant( url ) || skipUnfetched( f ) ) { droppedVariants ++; continue; }
	const tier = classify( url, jsonPath );
	const prev = files[ url ];
	// A file used twice takes the EARLIER tier (the viewer's own rule, applied here too).
	if ( prev && prev.tier <= tier ) continue;
	files[ url ] = { bytes: bytesOf( url ), tier, kind: ( url.match( EXT ) || [ '' ] )[ 0 ].replace( '.', '' ) || null,
		from: jsonPath, ...( prev ? { from: `${prev.from} + ${jsonPath}` } : {} ) };
}
// The one file the viewer fetches that no manifest field names: the uv2 relay status beside the
// manifest.  It is copied next to the stub, so it is tier 0 and local.
files[ 'uv2_relay_status.json' ] = { bytes: null, tier: 0, kind: 'json', from: '(beside the manifest)' };

// --lo-stand-in: a low-resolution stand-in for a handful of tier-1 textures, so the hot-swap path is
// exercised.  It is NOT a low-resolution version of the file — it is a different real texture.
let standIns = 0;
if ( LO_STAND_IN ) {
	const t1 = Object.keys( files ).filter( ( u ) => files[ u ].tier === 1 && /\.ktx2$/.test( u ) ).sort();
	for ( let i = 1; i < t1.length; i += 2 ) {
		files[ t1[ i ] ].lo = { path: t1[ i - 1 ], bytes: files[ t1[ i - 1 ] ].bytes, tier: 0, stand_in: true };
		standIns ++;
	}
}

const byTier = {};
for ( const [ url, f ] of Object.entries( files ) ) {
	( byTier[ f.tier ] ||= [] ).push( url );
	if ( f.lo ) ( byTier[ f.lo.tier ] ||= [] ).push( f.lo.path );
}
const tierList = Object.keys( byTier ).map( Number ).sort( ( a, b ) => a - b ).map( ( t ) => {
	const urls = [ ...new Set( byTier[ t ] ) ];
	const bytes = urls.reduce( ( a, u ) => a + ( ( files[ u ] && files[ u ].bytes ) || 0 ), 0 );
	return { tier: t, bytes, files_n: urls.length, files: urls,
		label: [ 'hero first frame (arch + ground + colour)', 'ornament and the impostor atlases', 'environment, foliage and the walk-up set' ][ t ] || null };
} );

m.schema = 'pfa-phase6/5';
m.tiers = {
	stub: {
		generator: 'web/tools/stub_tiers.mjs',
		source: path.relative( MAIN, SRC ),
		rule: 'tier 0 = lut + sky + probe + arch.glb + ground.glb + ARCH/GROUND textures and lightmaps; '
			+ 'tier 1 = orn.glb + ORN lightmap atlases + ORN textures + impostor atlases; '
			+ 'tier 2 = env.glb + ENV/foliage textures + the three lazy foliage glbs',
		warning: 'STUB. It cannot split a glb (gltfpack) and it makes no low-resolution texture variant '
			+ '(toktx). Replace with export/out/gate5/manifest.json when it lands in MAIN.',
		lo_stand_in: LO_STAND_IN ? `${standIns} tier-1 texture(s) point at ANOTHER real texture as their lo variant — a look test only` : null,
		dropped_variant: DROPPED_VARIANT ? `${droppedVariants} ${DROPPED_VARIANT} lightmap file(s) left out of the tiers: the manifest's own default is gamma2 and the viewer loads only that one` : null,
		unresolved: [ ...new Set( unresolved ) ],
	},
	list: tierList.map( ( t ) => ( { tier: t.tier, bytes: t.bytes, files_n: t.files_n, label: t.label, files: t.files } ) ),
	oversize: Object.entries( files ).filter( ( [ , f ] ) => ( f.bytes || 0 ) > 25 * 1024 * 1024 )
		.map( ( [ url, f ] ) => ( { path: url, bytes: f.bytes, reason: 'over the Cloudflare Pages 25 MiB per-file cap; the real export splits or moves it to R2' } ) ),
};
m.files = files;
// glb.groups: the v5 shape, built from per_class (the stub cannot split a glb, so one group per class).
if ( m.glb && m.glb.per_class ) {
	m.glb.groups = {};
	for ( const [ cls, g ] of Object.entries( m.glb.per_class ) ) {
		m.glb.groups[ cls ] = { ...g, class: cls, tier: ( files[ g.path ] && files[ g.path ].tier ) ?? TIER_OF_CLASS[ cls ] ?? 2 };
	}
}

fs.mkdirSync( OUT_DIR, { recursive: true } );
fs.writeFileSync( path.join( OUT_DIR, 'manifest.json' ), JSON.stringify( m, null, 1 ) );
// the relay status the viewer fetches beside the manifest
const relay = path.join( path.dirname( SRC ), 'uv2_relay_status.json' );
if ( fs.existsSync( relay ) ) fs.copyFileSync( relay, path.join( OUT_DIR, 'uv2_relay_status.json' ) );

const MB = ( b ) => ( b / 1e6 ).toFixed( 1 );
console.log( `stub_tiers: ${path.relative( REPO, path.join( OUT_DIR, 'manifest.json' ) )} from ${path.relative( MAIN, SRC )}` );
for ( const t of tierList ) console.log( `  tier ${t.tier}: ${MB( t.bytes )} MB in ${t.files_n} file(s) — ${t.label}` );
console.log( `  total ${MB( tierList.reduce( ( a, t ) => a + t.bytes, 0 ) )} MB, ${Object.keys( files ).length} file(s), `
	+ `${m.tiers.oversize.length} over 25 MiB, ${[ ...new Set( unresolved ) ].length} path(s) left as written` );
if ( unresolved.length ) console.log( `  unresolved: ${[ ...new Set( unresolved ) ].slice( 0, 12 ).join( ', ' )}` );
if ( tierList[ 0 ] && tierList[ 0 ].bytes > 50e6 ) console.log( `  NOTE: tier 0 is ${MB( tierList[ 0 ].bytes )} MB, over the 50 MB budget — the real export's low-resolution variants are what close that gap.` );
