// Palace of Fine Arts web viewer (Phase 6).  Loads the baked slice described by manifest.json,
// reproduces the Phase 5 look (AgX High Contrast at -2.833 EV) through a baked 3D LUT with three.js
// tone mapping OFF, and exposes the six QA stations as presets on keys 1-6 (?station=N).
//
// Test hooks used by tools/screenshot.mjs:
//   window.__pfaReady        true once the first frame after all loads has been presented
//   window.__pfaFrameStats(n) median / mean / p95 frame time in ms over n rendered frames
//   window.__pfaInfo()       camera matrices, draw calls, triangles, patched material count, notes
//   window.__pfaStation(n)   apply a station preset
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';
import { EXRLoader } from 'three/addons/loaders/EXRLoader.js';
import { LUTCubeLoader } from 'three/addons/loaders/LUTCubeLoader.js';
import { LUTImageLoader } from 'three/addons/loaders/LUTImageLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';

import { makeStationCamera, stationMatrix, b2t, matrixMaxDiff } from './blenderCamera.js';
import { normaliseManifest, WATER_Z } from './manifest.js';
import { patchBakedMaterial, attachLightMap } from './materials.js';
import { LUTDisplayPass, makeLUT } from './lutPass.js';
import { makeWater } from './water.js';
import { buildTestScene } from './testScene.js';

const qs = new URLSearchParams( location.search );
const CFG = {
	station: parseInt( qs.get( 'station' ) || '1', 10 ),
	manifestUrl: qs.get( 'manifest' ) || '/assets/gate0/manifest.json',
	testScene: qs.get( 'test' ) === '1',
	water: qs.get( 'water' ) !== '0',
	lut: qs.get( 'lut' ) !== '0',
	testLut: qs.get( 'testlut' ),                       // 'identity' | 'gamma22'
	exposureOverride: qs.has( 'exposure' ) ? parseFloat( qs.get( 'exposure' ) ) : null,
	skyRotationDeg: qs.has( 'skyrot' ) ? parseFloat( qs.get( 'skyrot' ) ) : null,
	size: qs.get( 'size' ),                             // "1280x720" forces the canvas size
	sun: qs.has( 'sun' ) ? parseFloat( qs.get( 'sun' ) ) : null,   // override the sun irradiance (probes)
};

function glInfo() {
	try {
		const gl = renderer.getContext();
		const dbg = gl.getExtension( 'WEBGL_debug_renderer_info' );
		return {
			renderer: dbg ? gl.getParameter( dbg.UNMASKED_RENDERER_WEBGL ) : gl.getParameter( gl.RENDERER ),
			vendor: dbg ? gl.getParameter( dbg.UNMASKED_VENDOR_WEBGL ) : gl.getParameter( gl.VENDOR ),
			version: gl.getParameter( gl.VERSION ),
		};
	} catch ( e ) { return { error: e.message }; }
}

const log = [];
const note = ( s ) => { log.push( s ); console.log( `[pfa] ${s}` ); };

// ---------------------------------------------------------------------------- renderer + scene
const container = document.getElementById( 'app' );
const renderer = new THREE.WebGLRenderer( { antialias: true, powerPreference: 'high-performance', preserveDrawingBuffer: true } );
renderer.setPixelRatio( 1 );                            // deterministic screenshots
renderer.toneMapping = THREE.NoToneMapping;             // the LUT pass IS the display transform
renderer.outputColorSpace = THREE.SRGBColorSpace;
container.appendChild( renderer.domElement );

const scene = new THREE.Scene();
let camera = new THREE.PerspectiveCamera( 50, 16 / 9, 0.1, 5000 );
const startTime = performance.now();
const elapsed = () => ( performance.now() - startTime ) / 1000;

function canvasSize() {
	if ( CFG.size && /^\d+x\d+$/.test( CFG.size ) ) {
		const [ w, h ] = CFG.size.split( 'x' ).map( Number ); return { w, h };
	}
	return { w: container.clientWidth || window.innerWidth, h: container.clientHeight || window.innerHeight };
}

// ---------------------------------------------------------------------------- loading screen
const ui = document.getElementById( 'loading' );
const bar = document.getElementById( 'bar' );
const uiText = document.getElementById( 'loading-text' );
const manager = new THREE.LoadingManager();
manager.onProgress = ( url, done, total ) => {
	const pct = total ? Math.round( 100 * done / total ) : 0;
	bar.style.width = `${pct}%`;
	uiText.textContent = `loading ${done}/${total} — ${url.split( '/' ).pop()}`;
};

// ---------------------------------------------------------------------------- main
let composer, lutPass, water, manifest, stations, sunLight;
let patchedMaterials = 0, lightmapsApplied = 0;
const unpatchedMaterials = new Set();
let userControlled = false, currentStation = null;

async function boot() {
	const t0 = performance.now();
	const manifestUrl = new URL( CFG.manifestUrl, location.href ).href;
	let raw = null;
	try {
		const r = await fetch( manifestUrl, { cache: 'no-cache' } );
		if ( r.ok ) raw = await r.json(); else note( `manifest ${r.status} at ${manifestUrl}` );
	} catch ( e ) { note( `manifest fetch failed: ${e.message}` ); }
	manifest = normaliseManifest( raw, manifestUrl );
	manifest.notes.forEach( note );
	stations = manifest.stations;
	if ( CFG.skyRotationDeg !== null ) manifest.sky.rotationDeg = CFG.skyRotationDeg;
	if ( CFG.exposureOverride !== null ) manifest.exposure = CFG.exposureOverride;
	if ( CFG.sun !== null ) { manifest.sun.irradiance = CFG.sun; manifest.sun.color = [ 1, 1, 1 ]; note( `sun irradiance overridden to ${CFG.sun}` ); }

	// sky --------------------------------------------------------------------------------------
	await loadSky();

	// sun: SPECULAR ONLY (materials.js strips its diffuse term; the lightmap has the diffuse) -----
	const d = manifest.sun.toSunBlender;                           // direction TOWARD the sun, Blender axes
	sunLight = new THREE.DirectionalLight( new THREE.Color().setRGB( ...manifest.sun.color, THREE.LinearSRGBColorSpace ), manifest.sun.irradiance );
	sunLight.position.copy( b2t( d[ 0 ], d[ 1 ], d[ 2 ] ).multiplyScalar( 1000 ) );   // the light sits toward the sun, aiming at the origin
	sunLight.target.position.set( 0, 0, 0 );
	sunLight.castShadow = false;                                   // shadows are in the lightmap
	scene.add( sunLight, sunLight.target );
	note( `sun: three direction ${sunLight.position.clone().normalize().toArray().map( v => v.toFixed( 3 ) )}, irradiance ${manifest.sun.irradiance}, specular only` );

	// geometry ----------------------------------------------------------------------------------
	if ( manifest.glb && ! CFG.testScene ) await loadGlb( manifest.glb );
	else { buildTestScene( scene ); note( 'test scene (no glb)' ); }

	// water -------------------------------------------------------------------------------------
	if ( CFG.water ) {
		water = makeWater( manifest.waterZ, { resolution: 1024 } );
		scene.add( water );
		note( `water plane at y = ${manifest.waterZ} (WATER_Z ${WATER_Z}), planar Reflector 1024x1024` );
	}

	// display transform ---------------------------------------------------------------------------
	const size = canvasSize();
	composer = new EffectComposer( renderer, new THREE.WebGLRenderTarget( size.w, size.h, {
		type: THREE.HalfFloatType, colorSpace: THREE.NoColorSpace, samples: 4,
	} ) );
	composer.addPass( new RenderPass( scene, camera ) );
	lutPass = new LUTDisplayPass( { exposure: manifest.exposure } );
	lutPass.renderToScreen = true;
	composer.addPass( lutPass );
	await loadLUT();
	note( `display: tone mapping OFF, exposure x${manifest.exposure.toFixed( 5 )}, LUT ${lutPass.uniforms.lutEnabled.value ? 'on' : 'OFF (gamma 2.2 fallback)'}` );

	applyStation( CFG.station );
	resize();
	window.addEventListener( 'resize', resize );
	installControls();

	// first frame -------------------------------------------------------------------------------
	renderFrame();
	requestAnimationFrame( () => {
		renderFrame();
		ui.style.display = 'none';
		window.__pfaReady = true;
		note( `ready in ${( ( performance.now() - t0 ) / 1000 ).toFixed( 2 )} s` );
		animate();
	} );
}

async function loadSky() {
	const load = ( url ) => new Promise( ( res, rej ) => {
		const L = url.endsWith( '.exr' ) ? new EXRLoader( manager ) : new RGBELoader( manager );
		L.load( url, res, undefined, rej );
	} );
	const rotY = THREE.MathUtils.degToRad( manifest.sky.rotationDeg );
	try {
		if ( manifest.sky.camera ) {
			const tex = await load( manifest.sky.camera );
			tex.mapping = THREE.EquirectangularReflectionMapping;
			scene.background = tex;
			scene.backgroundRotation = new THREE.Euler( 0, rotY, 0 );
			note( `sky background ${manifest.sky.camera.split( '/' ).pop()} ${tex.image.width}x${tex.image.height}, rotation ${manifest.sky.rotationDeg} deg` );
		} else { scene.background = new THREE.Color( 0.09, 0.13, 0.22 ); note( 'no camera sky: flat background' ); }
		if ( manifest.sky.glossy ) {
			const tex = await load( manifest.sky.glossy );
			const pmrem = new THREE.PMREMGenerator( renderer );
			pmrem.compileEquirectangularShader();
			scene.environment = pmrem.fromEquirectangular( tex ).texture;
			scene.environmentRotation = new THREE.Euler( 0, rotY, 0 );
			tex.dispose(); pmrem.dispose();
			note( `PMREM environment from ${manifest.sky.glossy.split( '/' ).pop()} (specular only)` );
		}
	} catch ( e ) { note( `sky load failed: ${e.message}` ); }
}

let ktx2Loader = null;
function getKTX2() {
	// One instance, kept alive: it owns a worker pool and also transcodes any .ktx2 lightmap.
	if ( ! ktx2Loader ) ktx2Loader = new KTX2Loader( manager ).setTranscoderPath( '/basis/' ).detectSupport( renderer );
	return ktx2Loader;
}

async function loadGlb( url ) {
	const loader = new GLTFLoader( manager ).setKTX2Loader( getKTX2() ).setMeshoptDecoder( MeshoptDecoder );
	const t = performance.now();
	const gltf = await loader.loadAsync( url );
	scene.add( gltf.scene );
	let tris = 0, meshes = 0;
	gltf.scene.traverse( ( o ) => {
		if ( ! o.isMesh ) return;
		meshes ++;
		const g = o.geometry;
		tris += ( g.index ? g.index.count : g.attributes.position.count ) / 3 * ( o.isInstancedMesh ? o.count : 1 );
		const mats = Array.isArray( o.material ) ? o.material : [ o.material ];
		for ( const m of mats ) {
			if ( ! m || ! m.isMeshStandardMaterial ) continue;
			const lm = matchLightmap( o, m );
			// Only a LIGHTMAPPED material may lose its diffuse light: one without a lightmap (the 15
			// instanced columns at Gate 0) would otherwise render black, so it keeps stock three
			// lighting (sun diffuse + env diffuse) and is counted separately.
			if ( lm ) {
				patchBakedMaterial( m, { lightMapEncoding: lm.encoding, rgbmMaxRange: lm.rgbmMaxRange } );
				patchedMaterials ++;
				applyLightmap( m, lm );
			} else {
				unpatchedMaterials.add( m.name || '(unnamed)' );
			}
		}
	} );
	note( `glb ${url.split( '/' ).pop()} in ${( ( performance.now() - t ) / 1000 ).toFixed( 2 )} s: ${meshes} meshes, ${Math.round( tris )} placed tris, ${patchedMaterials} lightmapped materials patched (specular-only sun), ${unpatchedMaterials.size} without a lightmap left on stock lighting: ${[ ...unpatchedMaterials ].join( ', ' ) || 'none'}` );
}

function matchLightmap( obj, mat ) {
	for ( const lm of manifest.lightmaps ) {
		if ( ! lm.match ) continue;
		const name = lm.matchKind === 'material' ? mat.name : obj.name;
		if ( name === lm.match || name.startsWith( lm.match ) ) return lm;
	}
	return null;
}

const lightmapCache = new Map();
function applyLightmap( mat, lm ) {
	const get = () => {
		if ( lightmapCache.has( lm.url ) ) return lightmapCache.get( lm.url );
		let p;
		if ( lm.url.endsWith( '.hdr' ) ) p = new RGBELoader( manager ).loadAsync( lm.url );
		else if ( lm.url.endsWith( '.exr' ) ) p = new EXRLoader( manager ).loadAsync( lm.url );
		else if ( lm.url.endsWith( '.ktx2' ) ) p = getKTX2().loadAsync( lm.url );
		else p = new THREE.TextureLoader( manager ).loadAsync( lm.url );
		lightmapCache.set( lm.url, p );
		return p;
	};
	get().then( ( tex ) => {
		if ( lm.encoding === 'srgb' ) tex.colorSpace = THREE.SRGBColorSpace;
		attachLightMap( mat, tex, lm.intensity );
		lightmapsApplied ++;
	} ).catch( ( e ) => note( `lightmap ${lm.url} failed: ${e.message}` ) );
}

async function loadLUT() {
	if ( ! CFG.lut ) { lutPass.setLUT( null ); return; }
	if ( CFG.testLut === 'identity' ) { lutPass.setLUT( makeLUT( 33, ( r, g, b ) => [ r, g, b ] ) ); note( 'test LUT: identity 33^3' ); return; }
	if ( CFG.testLut === 'gamma22' ) {
		lutPass.setLUT( makeLUT( 33, ( r, g, b ) => [ r, g, b ].map( v => Math.pow( v, 1 / 2.2 ) ) ) );
		note( 'test LUT: gamma 1/2.2 33^3' ); return;
	}
	if ( ! manifest.lut || ! manifest.lut.url ) { lutPass.setLUT( null ); return; }
	try {
		const url = manifest.lut.url;
		const lut = url.endsWith( '.cube' )
			? await new LUTCubeLoader( manager ).loadAsync( url )
			: await new LUTImageLoader( manager ).loadAsync( url );
		const res = lut.texture3D ? lut : { texture3D: lut.texture3D || lut, size: lut.size };
		res.shaper = manifest.lut.shaper; res.shaperMin = manifest.lut.shaperMin; res.shaperMax = manifest.lut.shaperMax;
		lutPass.setLUT( res );
		note( `LUT ${url.split( '/' ).pop()} size ${lutPass.uniforms.lutSize.value}${res.shaper ? ` shaper ${res.shaper} [${res.shaperMin}, ${res.shaperMax}]` : ` domain [${lutPass.uniforms.domainMin.value.toArray()}, ${lutPass.uniforms.domainMax.value.toArray()}]`}` );
	} catch ( e ) { note( `LUT load failed (${e.message}); gamma 2.2 fallback` ); lutPass.setLUT( null ); }
}

// ---------------------------------------------------------------------------- stations
function applyStation( n ) {
	const st = stations.find( s => s.index === n ) || stations[ 0 ];
	camera = makeStationCamera( st, camera.aspect || 16 / 9, camera );
	currentStation = st;
	userControlled = false;
	if ( composer ) composer.passes[ 0 ].camera = camera;
	if ( controls ) {
		const dist = st.target ? b2t( ...st.target ).distanceTo( camera.position ) : 40;
		controls.target.copy( camera.position.clone().add( camera.getWorldDirection( new THREE.Vector3() ).multiplyScalar( dist ) ) );
	}
	document.getElementById( 'hud' ).textContent = `${st.index}. ${st.name}  lens ${st.lens} mm  shift_y ${st.shift_y}`;
	const chk = stationMatrix( st );
	console.log( `[pfa] station ${st.index} ${st.name}
  source           ${chk.source}${chk.lookAtMatrix ? `  (look-at cross-check max element diff ${matrixMaxDiff( chk.matrix, chk.lookAtMatrix ).toExponential( 2 )})` : '  (look-at degenerate)'}
  world matrix     [${camera.matrixWorld.elements.map( v => v.toFixed( 5 ) ).join( ', ' )}]
  projection       [${camera.projectionMatrix.elements.map( v => v.toFixed( 5 ) ).join( ', ' )}]
  fov(v) ${camera.fov.toFixed( 3 )} deg  aspect ${camera.aspect.toFixed( 5 )}  near ${camera.near}  far ${camera.far}` );
	return st;
}

let controls = null;
function installControls() {
	controls = new OrbitControls( camera, renderer.domElement );
	controls.enableDamping = true;
	controls.dampingFactor = 0.12;
	controls.enabled = false;
	const enable = () => {
		if ( userControlled ) return;
		userControlled = true; controls.enabled = true;
		const dist = currentStation?.target ? b2t( ...currentStation.target ).distanceTo( camera.position ) : 40;
		controls.target.copy( camera.position.clone().add( camera.getWorldDirection( new THREE.Vector3() ).multiplyScalar( dist ) ) );
		controls.object = camera;
		controls.update();
	};
	renderer.domElement.addEventListener( 'pointerdown', enable );
	renderer.domElement.addEventListener( 'wheel', enable, { passive: true } );
	window.addEventListener( 'keydown', ( e ) => {
		if ( e.key >= '1' && e.key <= '6' ) { applyStation( parseInt( e.key, 10 ) ); resize(); }
		if ( e.key === 'h' ) document.getElementById( 'hud' ).classList.toggle( 'hidden' );
	} );
}

function resize() {
	const { w, h } = canvasSize();
	renderer.setSize( w, h, false );
	camera.aspect = w / h;
	camera.updateProjectionMatrix();
	if ( composer ) composer.setSize( w, h );
}

function renderFrame() {
	if ( water ) water.userData.tick( elapsed() );
	renderer.info.autoReset = false;          // otherwise info shows only the last composer pass
	renderer.info.reset();
	if ( composer ) composer.render(); else renderer.render( scene, camera );
}

function animate() {
	requestAnimationFrame( animate );
	if ( userControlled && controls ) controls.update();
	renderFrame();
}

// ---------------------------------------------------------------------------- test hooks
window.__pfaReady = false;
window.__pfaStation = ( n ) => { applyStation( n ); resize(); renderFrame(); return currentStation.name; };
window.__pfaInfo = () => ( {
	station: currentStation && { index: currentStation.index, name: currentStation.name, lens: currentStation.lens, shift_y: currentStation.shift_y },
	cameraWorldMatrix: camera.matrixWorld.elements.slice(),
	projectionMatrix: camera.projectionMatrix.elements.slice(),
	fovVertical: camera.fov, aspect: camera.aspect,
	size: [ renderer.domElement.width, renderer.domElement.height ],
	render: { ...renderer.info.render }, memory: { ...renderer.info.memory },
	gl: glInfo(),
	patchedMaterials, lightmapsApplied, unpatchedMaterials: [ ...unpatchedMaterials ],
	exposure: lutPass ? lutPass.uniforms.exposure.value : null,
	lutEnabled: lutPass ? !! lutPass.uniforms.lutEnabled.value : false,
	lutSize: lutPass ? lutPass.uniforms.lutSize.value : 0,
	waterZ: manifest ? manifest.waterZ : null,
	notes: log.slice(),
} );
window.__pfaFrameStats = ( n = 120 ) => new Promise( ( resolve ) => {
	const t = [];
	let last = performance.now();
	const step = () => {
		renderFrame();
		const now = performance.now();
		t.push( now - last ); last = now;
		if ( t.length < n ) requestAnimationFrame( step );
		else {
			const s = t.slice( 1 ).sort( ( a, b ) => a - b );   // drop the first (includes the call gap)
			resolve( {
				frames: s.length,
				median: s[ Math.floor( s.length / 2 ) ],
				mean: s.reduce( ( a, b ) => a + b, 0 ) / s.length,
				p95: s[ Math.floor( s.length * 0.95 ) ],
				min: s[ 0 ], max: s[ s.length - 1 ],
				drawCalls: renderer.info.render.calls, triangles: renderer.info.render.triangles,
			} );
		}
	};
	requestAnimationFrame( step );
} );
/** Frame cost without the vsync cap: n renders back to back, each followed by gl.finish().
 *  __pfaFrameStats is the presented frame time (60 Hz cap); this is the render cost. */
window.__pfaRenderCost = ( n = 60 ) => {
	const gl = renderer.getContext();
	renderFrame(); gl.finish();
	const t = [];
	for ( let i = 0; i < n; i ++ ) {
		const a = performance.now();
		renderFrame(); gl.finish();
		t.push( performance.now() - a );
	}
	t.sort( ( x, y ) => x - y );
	return { frames: n, median: t[ Math.floor( n / 2 ) ], mean: t.reduce( ( x, y ) => x + y, 0 ) / n, p95: t[ Math.floor( n * 0.95 ) ], min: t[ 0 ], max: t[ n - 1 ] };
};

/** Pixel bounding box of every object whose name contains `needle`, projected with the live camera.
 *  Used to put the pair-sheet's measurement boxes on the right geometry in BOTH frames. */
window.__pfaProject = ( needle ) => {
	const W = renderer.domElement.width, H = renderer.domElement.height;
	const v = new THREE.Vector3();
	const out = [];
	scene.traverse( ( o ) => {
		if ( ! o.isMesh || ! o.name.includes( needle ) ) return;
		o.geometry.computeBoundingBox();
		const bb = o.geometry.boundingBox;
		const mats = o.isInstancedMesh
			? Array.from( { length: o.count }, ( _, i ) => o.matrixWorld.clone().multiply( new THREE.Matrix4().fromArray( o.instanceMatrix.array, i * 16 ) ) )
			: [ o.matrixWorld ];
		mats.forEach( ( m, i ) => {
			let x0 = Infinity, y0 = Infinity, x1 = - Infinity, y1 = - Infinity, zmin = Infinity, behind = false;
			for ( let c = 0; c < 8; c ++ ) {
				v.set( c & 1 ? bb.max.x : bb.min.x, c & 2 ? bb.max.y : bb.min.y, c & 4 ? bb.max.z : bb.min.z );
				v.applyMatrix4( m );
				const dist = v.distanceTo( camera.position );
				v.project( camera );
				if ( v.z > 1 ) behind = true;
				x0 = Math.min( x0, ( v.x * 0.5 + 0.5 ) * W ); x1 = Math.max( x1, ( v.x * 0.5 + 0.5 ) * W );
				y0 = Math.min( y0, ( 0.5 - v.y * 0.5 ) * H ); y1 = Math.max( y1, ( 0.5 - v.y * 0.5 ) * H );
				zmin = Math.min( zmin, dist );
			}
			out.push( { name: o.name + ( o.isInstancedMesh ? `#${i}` : '' ), bbox: [ x0, y0, x1, y1 ], distance: zmin, behind } );
		} );
	} );
	out.sort( ( a, b ) => a.distance - b.distance );
	return out;
};

/** Read back the linear pixel at the centre of a named object (LUT / luminance probes). */
window.__pfaPixel = ( x, y ) => {
	const gl = renderer.getContext();
	const px = new Uint8Array( 4 );
	gl.readPixels( x, renderer.domElement.height - 1 - y, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px );
	return Array.from( px );
};

boot().catch( ( e ) => { note( `boot failed: ${e.stack}` ); uiText.textContent = `failed: ${e.message}`; window.__pfaError = String( e.stack ); } );
