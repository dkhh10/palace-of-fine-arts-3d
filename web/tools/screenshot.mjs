// Deterministic headless-Chrome screenshot of the viewer.  ALWAYS run through
//   scripts/chrome_run.sh <max_seconds> -- node web/tools/screenshot.mjs [options]
// and only while the bake queue is idle (export/out/bake_queue/status.json).
//
//   --station N       station preset (default 1)
//   --stations 1-6    capture several stations in ONE browser session (out gets _camNN); ranges,
//                     commas and mixes ("1-3,6") are all accepted
//   --out PATH        PNG path (default renders/web/gate0_viewer_cam01.png)
//   --size WxH        window / canvas size (default 1280x720)
//   --url URL         page to open; default: serve web/dist on a free port (built by `npm run build`)
//   --dev             serve with `vite dev` instead of the built dist
//   --query k=v       extra query parameters, repeatable (e.g. --query test=1 --query testlut=gamma22)
//   --frames N        measure N frames with window.__pfaFrameStats (0 = skip, default 120)
//   --timeout MS      ready timeout (default 120000)
//   --json PATH       write the info + frame stats sidecar (default <out>.json)
//   --pixels x,y;...  read back display pixels (after the screenshot) and print them
//   --probe A,B       project objects whose name contains A / B and read their centre pixel
//   --shots 0         measure only, write no PNGs (the performance pass)
//   --perf PATH       write the per-station performance JSON (frame time, GPU cost, draws, tris, bytes)
//   --warmup N        frames rendered and discarded after each station switch (default 20)
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
const ASSETS = process.env.PFA_ASSETS
	|| ( process.env.PFA_MAIN_ROOT ? path.join( process.env.PFA_MAIN_ROOT, 'export/out' ) : path.join( REPO, 'export/out' ) );

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

/** "1-6" / "1,3,5" / "1-3,6" -> [1,2,3,6]; out of range and duplicates are dropped. */
function parseStations( spec ) {
	const out = [];
	for ( const part of String( spec || '' ).split( ',' ) ) {
		const m = part.trim().match( /^(\d+)\s*-\s*(\d+)$/ );
		if ( m ) { for ( let i = + m[ 1 ]; i <= + m[ 2 ]; i ++ ) out.push( i ); }
		else if ( part.trim() ) out.push( parseInt( part, 10 ) );
	}
	return [ ...new Set( out ) ].filter( n => n >= 1 && n <= 6 );
}
const station = parseInt( o.station || '1', 10 );
const [ W, H ] = ( o.size || '1280x720' ).split( 'x' ).map( Number );
const out = path.resolve( REPO, o.out || 'renders/web/gate0_viewer_cam01.png' );
const jsonOut = o.json ? path.resolve( REPO, o.json ) : out.replace( /\.png$/, '.json' );
const frames = parseInt( o.frames ?? '120', 10 );
const warmup = parseInt( o.warmup ?? '20', 10 );
const takeShots = ( o.shots ?? '1' ) !== '0';
const perfOut = o.perf ? path.resolve( REPO, o.perf ) : null;
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
		let file;
		if ( url.startsWith( '/assets/' ) && ! fs.existsSync( path.join( root, url.slice( 1 ) ) ) ) file = path.join( ASSETS, url.slice( '/assets/'.length ) );
		else if ( url.startsWith( '/test/' ) ) file = path.join( WEB, 'testdata', url.slice( '/test/'.length ) );
		else file = path.join( root, url === '/' ? 'index.html' : url.slice( 1 ) );
		// Containment on a PATH BOUNDARY: `startsWith` alone lets /export/out2 pass as /export/out.
		const allowed = [ root, ASSETS, path.join( WEB, 'testdata' ) ].map( a => path.resolve( a ) );
		const real = path.resolve( file );
		if ( ! allowed.some( a => real === a || real.startsWith( a + path.sep ) )
			|| ! fs.existsSync( file ) || fs.statSync( file ).isDirectory() ) { res.statusCode = 404; res.end( 'not found' ); return; }
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
	// Last --query wins: URLSearchParams.get() returns the FIRST value of a repeated key, so the
	// pairs are deduplicated here (gate2.sh passes its defaults first and PFA_QUERY after).
	const qmap = new Map( [ [ 'station', String( station ) ], [ 'size', `${W}x${H}` ], [ 'hud', '0' ] ] );
	for ( const s of o.query ) { const [ k, v = '' ] = s.split( /=(.*)/ ); if ( k ) qmap.set( k, v ); }
	const q = new URLSearchParams( [ ...qmap ] );
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

	const extra = parseStations( o.stations );
	const shotList = extra.length ? extra : [ station ];
	const info = await page.evaluate( () => window.__pfaInfo() );

	fs.mkdirSync( path.dirname( out ), { recursive: true } );
	const written = [], perStation = [];
	for ( const st of shotList ) {
		let file = out;
		if ( shotList.length > 1 ) file = out.replace( /(\.png)$/, `_cam${String( st ).padStart( 2, '0' )}$1` );
		const name = await page.evaluate( ( n ) => window.__pfaStation( n ), st );
		// warm up: the first frames after a station switch pay for shader compiles and texture uploads
		if ( warmup > 0 ) await page.evaluate( ( n ) => window.__pfaRenderCost( n ), warmup );
		if ( takeShots ) {
			await page.screenshot( { path: file, captureBeyondViewport: false } );
			written.push( { station: st, name, file } );
		}
		let stats = null, cost = null;
		if ( frames > 0 ) {
			stats = await page.evaluate( ( n ) => window.__pfaFrameStats( n ), frames );
			cost = await page.evaluate( ( n ) => window.__pfaRenderCost( n ), Math.min( frames, 60 ) );
		}
		const i = await page.evaluate( () => window.__pfaInfo() );
		const row = {
			station: st, name, size: [ W, H ], file: takeShots ? file : null,
			frame_ms: stats && { median: stats.median, mean: stats.mean, p95: stats.p95, min: stats.min, max: stats.max, frames: stats.frames },
			fps_presented: stats ? 1000 / stats.median : null,
			gpu_cost_ms: cost && { median: cost.median, mean: cost.mean, p95: cost.p95, frames: cost.frames },
			fps_uncapped: cost ? 1000 / cost.median : null,
			draw_calls: i.render.calls, triangles: i.render.triangles, programs: i.render.programs ?? null,
			info_memory: i.memory, resident: i.resident,
		};
		perStation.push( row );
		if ( takeShots ) written[ written.length - 1 ] = { ...written[ written.length - 1 ], draws: row.draw_calls, tris: row.triangles };
		console.log( `[shot] station ${st} ${name}: frame ${stats ? stats.median.toFixed( 2 ) : '-'} ms, gpu ${cost ? cost.median.toFixed( 2 ) : '-'} ms, `
			+ `draws ${row.draw_calls}, tris ${row.triangles}` );
	}
	const stats = perStation.length ? perStation[ 0 ].frame_ms : null;      // back-compat: the sidecar's
	const cost = perStation.length ? perStation[ 0 ].gpu_cost_ms : null;    // top-level pair is station 1's

	if ( o.names ) { const n = await page.evaluate( () => window.__pfaNames() ); console.log( '[shot] meshes: ' + JSON.stringify( n ) ); }

	let probes = null;
	if ( o.probe ) {
		probes = await page.evaluate( ( names ) => names.split( ',' ).filter( Boolean ).map( ( n ) => {
			const hit = window.__pfaProject( n )[ 0 ];
			if ( ! hit ) return { name: n, error: 'not found' };
			const cx = Math.round( ( hit.bbox[ 0 ] + hit.bbox[ 2 ] ) / 2 ), cy = Math.round( ( hit.bbox[ 1 ] + hit.bbox[ 3 ] ) / 2 );
			return { name: hit.name, centre: [ cx, cy ], bbox: hit.bbox.map( v => Math.round( v * 10 ) / 10 ), rgba: window.__pfaPixel( cx, cy ) };
		} ), o.probe );
		probes.forEach( p => console.log( `[shot] probe ${p.name} centre ${p.centre} rgba ${p.rgba} bbox ${p.bbox}` ) );
	}

	let pixels = null;
	if ( o.pixels ) {
		pixels = await page.evaluate( ( spec ) => spec.split( ';' ).filter( Boolean ).map( ( s ) => {
			const [ x, y ] = s.split( ',' ).map( Number );
			return { x, y, rgba: window.__pfaPixel( x, y ) };
		} ), o.pixels );
	}

	const sidecar = { out, url, station, size: [ W, H ], wall_s: ( Date.now() - t0 ) / 1000, info, stats, cost, perStation, probes, pixels, written, pageLog };
	fs.writeFileSync( jsonOut, JSON.stringify( sidecar, null, 1 ) );
	if ( perfOut ) {
		fs.mkdirSync( path.dirname( perfOut ), { recursive: true } );
		fs.writeFileSync( perfOut, JSON.stringify( {
			generated: new Date().toISOString(),
			url, size: [ W, H ], frames, warmup,
			gl: info.gl, schema: info.schema, lighting_mode: info.lightingMode,
			bytes: info.bytes, load_s: info.load_s, glbs: info.glbs, billboards: info.billboards,
			stations: perStation,
		}, null, 1 ) );
		console.log( `[shot] wrote ${perfOut}` );
	}
	written.forEach( w => console.log( `[shot] wrote ${w.file} (${( fs.statSync( w.file ).size / 1024 ).toFixed( 0 )} kB) station ${w.station} draws ${w.draws} tris ${w.tris}` ) );
	console.log( `[shot] ${info.schema || '(no schema)'} lighting ${info.lightingMode} lightmaps ${info.lightmapsApplied}/${info.patchedMaterials}` );
	if ( info.bytes && info.load_s )
		console.log( `[shot] loaded ${( info.bytes.loaded / 1e6 ).toFixed( 1 )} MB of ${( info.bytes.planned / 1e6 ).toFixed( 1 )} MB planned in ${info.load_s.total_s.toFixed( 2 )} s `
			+ `(sky ${info.load_s.sky_s.toFixed( 2 )}, lut ${info.load_s.lut_s.toFixed( 2 )}, glb ${info.load_s.glb_s.toFixed( 2 )})` );
	if ( stats ) console.log( `[shot] frame time at ${W}x${H}: median ${stats.median.toFixed( 2 )} ms (${( 1000 / stats.median ).toFixed( 1 )} fps presented, vsync-capped at 16.7), mean ${stats.mean.toFixed( 2 )}, p95 ${stats.p95.toFixed( 2 )}, n=${stats.frames}` );
	if ( cost ) console.log( `[shot] render cost (gl.finish, no vsync): median ${cost.median.toFixed( 2 )} ms (${( 1000 / cost.median ).toFixed( 1 )} fps), p95 ${cost.p95.toFixed( 2 )}, n=${cost.frames}` );
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
