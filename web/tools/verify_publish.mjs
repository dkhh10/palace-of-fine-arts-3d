// Every `files[].path` of every manifest given must be present in the publish directory.
//
//   node web/tools/verify_publish.mjs --dir web/deploy_out <manifest.json> [<manifest_mobile.json> …]
//
// publish_set.mjs guarantees that a planned path resolves to a file ON DISK; this guarantees the
// file is IN THE PUBLISH DIRECTORY, which is a different claim and the one QA 18's blocker needed:
// the seven mobile group glbs existed on disk, were named in manifest_mobile.files, and were simply
// never linked, so `?tier=mobile` 404ed on all of them.  Exits non-zero and names what is missing.
import fs from 'node:fs';
import path from 'node:path';

const argv = process.argv.slice( 2 );
const di = argv.indexOf( '--dir' );
const DIR = path.resolve( di >= 0 ? argv[ di + 1 ] : 'web/deploy_out' );
const MANIFESTS = argv.filter( ( a, i ) => ! a.startsWith( '--' ) && i !== di + 1 );
const ASSETS = process.env.PFA_ASSETS
	|| ( process.env.PFA_MAIN_ROOT ? path.join( process.env.PFA_MAIN_ROOT, 'export/out' ) : 'export/out' );

let bad = 0, checked = 0;
for ( const mf of MANIFESTS ) {
	const abs = path.resolve( mf );
	const raw = JSON.parse( fs.readFileSync( abs, 'utf8' ) );
	const rel = path.relative( ASSETS, path.dirname( abs ) ).split( path.sep ).join( '/' );
	const files = Array.isArray( raw.files ) ? raw.files
		: Object.entries( raw.files || {} ).map( ( [ p, v ] ) => ( { path: ( v && v.path ) || p } ) );
	const missing = [];
	for ( const f of files ) {
		if ( ! f || ! f.path ) continue;
		// the published path is `assets/<the path resolved against the manifest's own directory>`
		const pub = 'assets/' + path.posix.normalize( `${rel}/${f.path}` );
		checked ++;
		if ( ! fs.existsSync( path.join( DIR, pub ) ) ) missing.push( pub );
	}
	// the manifest itself has to be there too, and so does any sibling the viewer fetches by name
	for ( const extra of [ path.basename( abs ), 'uv2_relay_status.json' ] ) {
		if ( ! fs.existsSync( path.join( path.dirname( abs ), extra ) ) ) continue;
		const pub = 'assets/' + path.posix.normalize( `${rel}/${extra}` );
		checked ++;
		if ( ! fs.existsSync( path.join( DIR, pub ) ) ) missing.push( pub );
	}
	console.log( `verify_publish: ${path.basename( abs )} — ${files.length} planned path(s), `
		+ ( missing.length ? `${missing.length} MISSING from the publish directory` : 'all present' ) );
	for ( const m of missing.slice( 0, 12 ) ) console.error( `  MISSING  ${m}` );
	if ( missing.length > 12 ) console.error( `  … and ${missing.length - 12} more` );
	bad += missing.length;
}
console.log( `verify_publish: ${checked} path(s) checked across ${MANIFESTS.length} manifest(s), ${bad} missing` );
process.exit( bad ? 9 : 0 );
