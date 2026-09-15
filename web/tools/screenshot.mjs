// Deterministic headless-Chrome screenshot of the viewer.  ALWAYS run through
//   scripts/chrome_run.sh <max_seconds> -- node web/tools/screenshot.mjs [options]
// and only while the bake queue is idle (export/out/bake_queue/status.json).
//
//   --station N       station preset (default 1)
//   --out PATH        PNG path (default renders/web/gate0_viewer_cam01.png)
//   --size WxH        window / canvas size (default 1280x720)
//   --url URL         page to open; default: serve web/dist on a free port (built by `npm run build`)
//   --dev             serve with `vite dev` instead of the built dist
//   --query k=v       extra query parameters, repeatable (e.g. --query test=1 --query testlut=gamma22)
//   --frames N        measure N frames with window.__pfaFrameStats (0 = skip, default 120)
//   --timeout MS      ready timeout (default 120000)
//   --json PATH       write the info + frame stats sidecar (default <out>.json)
//   --pixels x,y;...  read back display pixels (after the screenshot) and print them
//
// The browser is closed in a finally block and the process calls process.exit, so no Chrome is left
// behind (a raw `--headless=new --screenshot` lingers 60-90 s on Chrome 152; puppeteer with an
// explicit close does not).
import puppeteer from 'puppeteer-core';
import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const WEB = path.resolve( fileURLToPath( new URL( '..', import.meta.url ) ) );
const REPO = path.resolve( WEB, '..' );
const CHROME = process.env.PFA_CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const ASSETS = process.env.PFA_ASSETS || '/Users/dk/Projects/3d render blender 3rd attempt building/export/out';

function args() {
	const a = process.argv.slice( 2 ), o = { query: [] };
	for ( let i = 0; i < a.length; i ++ ) {
		const k = a[ i ].replace( /^--/, '' );
		if ( k === 'dev' ) { o.dev = true; continue; }
		const v = a[ ++ i ];
		if ( k === 'query' ) o.query.push( v ); else o[ k ] = v;
	}
	return o;
}
const o = args();
const station = parseInt( o.station || '1', 10 );
const [ W, H ] = ( o.size || '1280x720' ).split( 'x' ).map( Number );
const out = path.resolve( REPO, o.out || 'renders/web/gate0_viewer_cam01.png' );
const jsonOut = o.json ? path.resolve( REPO, o.json ) : out.replace( /\.png$/, '.json' );
const frames = parseInt( o.frames ?? '120', 10 );
const timeout = parseInt( o.timeout || '120000', 10 );

const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css',
	'.json': 'application/json', '.wasm': 'application/wasm', '.glb': 'model/gltf-binary', '.ktx2': 'image/ktx2',
	'.hdr': 'image/vnd.radiance', '.exr': 'image/x-exr', '.png': 'image/png', '.jpg': 'image/jpeg',
	'.cube': 'text/plain', '.bin': 'application/octet-stream', '.gltf': 'model/gltf+json' };

/** Static server for web/dist with /assets/* mapped to the (large, un-copied) bake output. */
function serveDist() {
	const root = path.join( WEB, 'dist' );
	if ( ! fs.existsSync( path.join( root, 'index.html' ) ) )
		throw new Error( `web/dist missing - run "npm run build" first (${root})` );
	const srv = createServer( ( req, res ) => {
		const url = decodeURIComponent( req.url.split( '?' )[ 0 ] );
		let file = url.startsWith( '/assets/' ) && ! fs.existsSync( path.join( root, url.slice( 1 ) ) )
			? path.join( ASSETS, url.slice( '/assets/'.length ) )
			: path.join( root, url === '/' ? 'index.html' : url.slice( 1 ) );
		if ( ! fs.existsSync( file ) || fs.statSync( file ).isDirectory() ) { res.statusCode = 404; res.end( 'not found' ); return; }
		res.setHeader( 'Content-Type', MIME[ path.extname( file ) ] || 'application/octet-stream' );
		res.setHeader( 'Content-Length', fs.statSync( file ).size );
		fs.createReadStream( file ).pipe( res );
	} );
	return new Promise( ( resolve ) => srv.listen( 0, '127.0.0.1', () => resolve( { srv, port: srv.address().port } ) ) );
}

function serveDev() {
	const port = 5180 + Math.floor( Math.random() * 200 );
	const p = spawn( 'npx', [ 'vite', '--port', String( port ), '--strictPort' ], { cwd: WEB, stdio: [ 'ignore', 'pipe', 'pipe' ] } );
	return new Promise( ( resolve, reject ) => {
		const t = setTimeout( () => reject( new Error( 'vite dev did not start in 30 s' ) ), 30000 );
		p.stdout.on( 'data', ( d ) => { if ( String( d ).includes( 'ready in' ) || String( d ).includes( 'Local:' ) ) { clearTimeout( t ); resolve( { proc: p, port } ); } } );
		p.stderr.on( 'data', ( d ) => process.stderr.write( `[vite] ${d}` ) );
	} );
}

let browser = null, server = null, viteProc = null;
const t0 = Date.now();
try {
	let base = o.url;
	if ( ! base ) {
		if ( o.dev ) { const s = await serveDev(); viteProc = s.proc; base = `http://127.0.0.1:${s.port}/`; }
		else { const s = await serveDist(); server = s.srv; base = `http://127.0.0.1:${s.port}/`; }
	}
	const q = new URLSearchParams( [ [ 'station', String( station ) ], [ 'size', `${W}x${H}` ], ...o.query.map( s => s.split( /=(.*)/ ).slice( 0, 2 ) ) ] );
	const url = `${base}${base.includes( '?' ) ? '&' : '?'}${q}`;

	browser = await puppeteer.launch( {
		executablePath: CHROME,
		headless: true,                         // Chrome's "new" headless (puppeteer >= 22 default)
		args: [
			`--window-size=${W},${H}`, '--hide-scrollbars', '--mute-audio', '--no-first-run',
			'--use-angle=metal', '--ignore-gpu-blocklist', '--enable-gpu-rasterization',
			'--enable-unsafe-webgpu', '--disable-dev-shm-usage', '--force-color-profile=srgb',
		],
		defaultViewport: { width: W, height: H, deviceScaleFactor: 1 },
		protocolTimeout: Math.max( timeout + 60000, 180000 ),
	} );
	const page = await browser.newPage();
	const pageLog = [];
	page.on( 'console', ( m ) => { pageLog.push( `${m.type()}: ${m.text()}` ); console.log( `[page] ${m.text()}` ); } );
	page.on( 'pageerror', ( e ) => { pageLog.push( `pageerror: ${e.message}` ); console.error( `[page error] ${e.message}` ); } );
	page.on( 'requestfailed', ( r ) => { pageLog.push( `requestfailed: ${r.url()} ${r.failure()?.errorText}` ); } );

	console.log( `[shot] ${url}` );
	await page.goto( url, { waitUntil: 'domcontentloaded', timeout } );
	await page.waitForFunction( 'window.__pfaReady === true || window.__pfaError', { timeout, polling: 250 } );
	const err = await page.evaluate( () => window.__pfaError || null );
	if ( err ) throw new Error( `viewer boot failed:\n${err}` );

	const info = await page.evaluate( () => window.__pfaInfo() );
	let stats = null;
	if ( frames > 0 ) stats = await page.evaluate( ( n ) => window.__pfaFrameStats( n ), frames );

	fs.mkdirSync( path.dirname( out ), { recursive: true } );
	await page.screenshot( { path: out, captureBeyondViewport: false } );

	let pixels = null;
	if ( o.pixels ) {
		pixels = await page.evaluate( ( spec ) => spec.split( ';' ).filter( Boolean ).map( ( s ) => {
			const [ x, y ] = s.split( ',' ).map( Number );
			return { x, y, rgba: window.__pfaPixel( x, y ) };
		} ), o.pixels );
	}

	const sidecar = { out, url, station, size: [ W, H ], wall_s: ( Date.now() - t0 ) / 1000, info, stats, pixels, pageLog };
	fs.writeFileSync( jsonOut, JSON.stringify( sidecar, null, 1 ) );
	console.log( `[shot] wrote ${out} (${( fs.statSync( out ).size / 1024 ).toFixed( 0 )} kB) and ${path.basename( jsonOut )}` );
	console.log( `[shot] station ${info.station?.index} ${info.station?.name}  draws ${info.render.calls}  tris ${info.render.triangles}  lightmaps ${info.lightmapsApplied}/${info.patchedMaterials}` );
	if ( stats ) console.log( `[shot] frame time at ${W}x${H}: median ${stats.median.toFixed( 2 )} ms (${( 1000 / stats.median ).toFixed( 1 )} fps), mean ${stats.mean.toFixed( 2 )}, p95 ${stats.p95.toFixed( 2 )}, n=${stats.frames}` );
	if ( pixels ) pixels.forEach( p => console.log( `[shot] pixel (${p.x}, ${p.y}) = ${p.rgba}` ) );
} catch ( e ) {
	console.error( `[shot] FAILED: ${e.message}` );
	process.exitCode = 1;
} finally {
	try { if ( browser ) await browser.close(); } catch { /* ignore */ }
	try { if ( server ) server.close(); } catch { /* ignore */ }
	try { if ( viteProc ) viteProc.kill( 'SIGTERM' ); } catch { /* ignore */ }
	console.log( `[shot] done in ${( ( Date.now() - t0 ) / 1000 ).toFixed( 1 )} s` );
	process.exit( process.exitCode || 0 );
}
