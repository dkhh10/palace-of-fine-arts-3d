// Vite config.  The baked assets are NOT copied into the bundle: /assets/* is served straight from
// export/out (PFA_ASSETS, default the main checkout), in dev, in preview and by tools/serve.mjs, so
// a 300 MB bake never enters web/dist and `npm run build` stays a source-only build.
import { defineConfig } from 'vite';
import fs from 'node:fs';
import path from 'node:path';

export const ASSETS_DIR = process.env.PFA_ASSETS
	|| '/Users/dk/Projects/3d render blender 3rd attempt building/export/out';

const MIME = { '.json': 'application/json', '.glb': 'model/gltf-binary', '.ktx2': 'image/ktx2',
	'.hdr': 'image/vnd.radiance', '.exr': 'image/x-exr', '.png': 'image/png', '.jpg': 'image/jpeg',
	'.cube': 'text/plain', '.bin': 'application/octet-stream', '.gltf': 'model/gltf+json' };

export const TESTDATA_DIR = path.resolve( import.meta.dirname, 'testdata' );

export function assetsMiddleware() {
	return ( req, res, next ) => {
		const isAssets = req.url.startsWith( '/assets/' ), isTest = req.url.startsWith( '/test/' );
		if ( ! isAssets && ! isTest ) return next();
		const root = isAssets ? ASSETS_DIR : TESTDATA_DIR;
		const rel = decodeURIComponent( req.url.split( '?' )[ 0 ].slice( isAssets ? '/assets/'.length : '/test/'.length ) );
		const file = path.join( root, rel );
		if ( ! file.startsWith( root ) || ! fs.existsSync( file ) || fs.statSync( file ).isDirectory() ) {
			res.statusCode = 404; res.end( 'not found' ); return;
		}
		res.setHeader( 'Content-Type', MIME[ path.extname( file ) ] || 'application/octet-stream' );
		res.setHeader( 'Content-Length', fs.statSync( file ).size );
		fs.createReadStream( file ).pipe( res );
	};
}

const pfaAssets = () => ( {
	name: 'pfa-assets',
	configureServer: ( s ) => s.middlewares.use( assetsMiddleware() ),
	configurePreviewServer: ( s ) => s.middlewares.use( assetsMiddleware() ),
} );

export default defineConfig( {
	base: './',
	plugins: [ pfaAssets() ],
	build: { target: 'es2022', sourcemap: false, chunkSizeWarningLimit: 2000 },
} );
