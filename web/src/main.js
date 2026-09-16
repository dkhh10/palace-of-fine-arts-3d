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
import { dequantizeUvs } from './uvDequant.js';
import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';
import { EXRLoader } from 'three/addons/loaders/EXRLoader.js';
import { LUTCubeLoader } from 'three/addons/loaders/LUTCubeLoader.js';
import { LUTImageLoader } from 'three/addons/loaders/LUTImageLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';

import { makeStationCamera, stationMatrix, b2t, matrixMaxDiff } from './blenderCamera.js';
import { normaliseManifest, applyUv2RelayStatus, WATER_Z } from './manifest.js';
import { patchBakedMaterial, attachLightMap } from './materials.js';
import { LUTDisplayPass, makeLUT } from './lutPass.js';
import { makeWater, reduceReflectionSet } from './water.js';
import { makeWalk } from './walk.js';
import { readCompositor, applyMist, removeMist, makeBloom, parsePost, MIST_NEAR_M, MIST_FAR_M } from './postChain.js';
import { buildTestScene } from './testScene.js';
import { makeTreeBillboards, aimBillboards } from './billboards.js';
import { buildImpostors } from './impostors.js';
import { buildProbeEnv, applyProbeEnv } from './probeEnv.js';
import { chunkInstancedMeshes } from './chunking.js';
import { applyPbrSets, pbrPlan, formatName, collectTextures, disposeOrphans } from './pbr.js';
import { applyDetail } from './detail.js';
import { applyGate3Lightmaps } from './lightmaps.js';

const qs = new URLSearchParams( location.search );
// ?quality is compared ONCE, lowercased, and an unknown value is rejected rather than echoed as a
// preset name: ?quality=FAST used to report 'fast' and silently run the full-res chain.
const QUALITY_RAW = ( qs.get( 'quality' ) || 'look' ).toLowerCase();
const QUALITY = ( QUALITY_RAW === 'fast' || QUALITY_RAW === 'look' ) ? QUALITY_RAW : 'look';
const CFG = {
	station: parseInt( qs.get( 'station' ) || '1', 10 ),
	manifestUrl: qs.get( 'manifest' ) || '/assets/gate0/manifest.json',
	testScene: qs.get( 'test' ) === '1',
	water: qs.get( 'water' ) !== '0',
	// ?quality: `look` (the default) is the frozen Phase 5 look - planar Reflector at full resolution,
	// full-res bloom.  `fast` is the ONE non-default preset: half-res bloom + a half-res Reflector
	// target + the reduced reflection draw set.  It is a QUERY PARAMETER ONLY, no UI.  An explicit
	// ?bloomres / ?reflres still wins over the preset, so the A/B switches keep working.
	quality: QUALITY,
	bloomRes: ( qs.get( 'bloomres' ) || ( QUALITY === 'fast' ? 'half' : 'full' ) ).toLowerCase(),
	reflRes: ( qs.get( 'reflres' ) || ( QUALITY === 'fast' ? 'half' : 'full' ) ).toLowerCase(),
	reflSet: ( qs.get( 'reflset' ) || 'orn' ).toLowerCase(),      // full | orn | both (item 6: cut the draw set)
	waterDebug: parseInt( qs.get( 'waterdebug' ) || '0', 10 ),   // 1 F, 2 proj uv, 3 normal, 4 raw refl
	waterDist: qs.has( 'waterdist' ) ? parseFloat( qs.get( 'waterdist' ) ) : null,
	waterNorm: qs.has( 'waternorm' ) ? parseFloat( qs.get( 'waternorm' ) ) : null,
	waterTile: qs.has( 'watertile' ) ? parseFloat( qs.get( 'watertile' ) ) : null,
	waterAniso: qs.has( 'wateraniso' ) ? parseFloat( qs.get( 'wateraniso' ) ) : null,
	waterHoriz: qs.has( 'waterhoriz' ) ? parseFloat( qs.get( 'waterhoriz' ) ) : null,
	waterGraze: qs.has( 'watergraze' ) ? parseFloat( qs.get( 'watergraze' ) ) : null,
	waterCrest: qs.has( 'watercrest' ) ? parseFloat( qs.get( 'watercrest' ) ) : null,   // directional spread power
	waterSlope: qs.has( 'waterslope' ) ? parseFloat( qs.get( 'waterslope' ) ) : null,   // rms surface slope, rad
	waterMurk: qs.get( 'watermurk' ) || null,                    // "r,g,b" linear, overrides the derivation
	waterMurkGain: qs.has( 'watermurkgain' ) ? parseFloat( qs.get( 'watermurkgain' ) ) : null,  // scales it
	waterGrazeMax: qs.has( 'watergrazemax' ) ? parseFloat( qs.get( 'watergrazemax' ) ) : null,  // grazing cap
	waterBlur: qs.has( 'waterblur' ) ? parseFloat( qs.get( 'waterblur' ) ) : null,   // reflection gather radius
	waterSat: qs.has( 'watersat' ) ? parseFloat( qs.get( 'watersat' ) ) : null,      // reflection saturation
	lut: qs.get( 'lut' ) !== '0',
	testLut: qs.get( 'testlut' ),                       // 'identity' | 'gamma22'
	exposureOverride: qs.has( 'exposure' ) ? parseFloat( qs.get( 'exposure' ) ) : null,
	skyRotationDeg: qs.has( 'skyrot' ) ? parseFloat( qs.get( 'skyrot' ) ) : null,
	size: qs.get( 'size' ),                             // "1280x720" forces the canvas size
	sun: qs.has( 'sun' ) ? parseFloat( qs.get( 'sun' ) ) : null,   // override the sun irradiance (probes)
	unlit: qs.get( 'unlit' ) || 'share',                // share | stock | black: materials with no lightmap
	haze: qs.has( 'haze' ) ? parseFloat( qs.get( 'haze' ) ) : 0,   // diagnostic constant airlight
	hud: qs.get( 'hud' ) !== '0',                       // ?hud=0 for clean screenshots
	lmScale: qs.has( 'lmscale' ) ? parseFloat( qs.get( 'lmscale' ) ) : null,  // override lightmap_scale
	time: qs.has( 't' ) ? parseFloat( qs.get( 't' ) ) : null,      // freeze the water phase (captures)
	glbOverride: qs.get( 'glb' ),                       // comma-separated URLs, overrides the manifest's list
	lighting: qs.get( 'lighting' ) || 'auto',           // auto | baked | direct  (see pickLightingMode)
	billboards: qs.get( 'billboards' ) !== '0',         // far-tree placeholder quads
	impostors: qs.get( 'impostors' ) !== '0',           // Gate 3 octahedral far-tree impostors
	impNormalDepth: qs.get( 'impnd' ) === '1',          // also load the normal+depth atlases
	impDebug: parseInt( qs.get( 'impdebug' ) || '0', 10 ),   // 1 raw, 2 alpha, 3 frame cell, 4 quad uv
	probeEnv: qs.get( 'probe' ) !== '0',                // baked hero probe as the irradiance of unlit surfaces
	probeSpec: qs.get( 'probespec' ) === '1',           // A/B: probe as the SPECULAR env of baked materials
	treeboards: qs.get( 'treeboards' ) !== '0',         // the export's own ENV_treeboard_* stand-ins inside env.glb (QA 11b)
	colourFrom: qs.get( 'colour' ),                     // manifest to borrow lut / sky / exposure from
	materials: qs.get( 'materials' ) || 'auto',         // auto | pbr | grey  (see pickMaterialsMode)
	// QA-11d-1 instance chunking: "0" disables it, "minRadius[,maxDepth[,gain]]" tunes it
	chunk: qs.get( 'chunk' ),                           // "minRadius[,maxDepth[,gain[,budget]]]" 
	lutFloat: qs.get( 'lutfloat' ) !== '0',             // 0 forces the 8-bit LUT (no-OES_texture_float_linear path)
	detail: qs.has( 'detail' ) ? parseFloat( qs.get( 'detail' ) ) : 1.0,   // QA-12-1 detail layer strength, 0 = off
	detailProj: qs.get( 'detailproj' ) || 'objxy',      // objxy (the manifest's plane) | dominant
	detailNormal: qs.has( 'detailnormal' ) ? parseFloat( qs.get( 'detailnormal' ) ) : 1.0,  // detail normal scale (1 = the map's own slope)
	detailTest: qs.get( 'detailtest' ),                 // "noise": a synthetic stand-in set (diagnostic)
	detailBias: qs.has( 'detailbias' ) ? parseFloat( qs.get( 'detailbias' ) ) : - 2.0,  // detail mip footprint shrink (log2)
	detailGain: qs.has( 'detailgain' ) ? parseFloat( qs.get( 'detailgain' ) ) : 1.0,    // contrast gain on the detail ratio
	lmFlip: qs.get( 'lmflip' ) === '1',                 // diagnostic: flip the lightmap V (UV origin test)
	lmEnc: qs.get( 'lmenc' ) || null,                   // diagnostic: force the lightmap decode (gamma2|linear|rgbm8)
	uvDequant: qs.get( 'uvdq' ) !== '0',                // undo gltfpack's texcoord quantisation (default on)
	vertexIrr: qs.get( 'vertexirr' ) || 'auto',         // near-tree COLOR_0 irradiance: auto | 1 | 0
	post: qs.get( 'post' ),                             // all | none | mist,bloom,vignette (default none)
	mist: qs.get( 'mist' ),                             // near,far in metres (the manifest carries neither)
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
// Progress is measured in BYTES, not in files: every asset's size is taken from a HEAD request (the
// manifest's declared `bytes` is the fallback) before anything is fetched, so the bar is linear in
// download and the viewer can report exactly how many bytes the walkthrough costs.
const ui = document.getElementById( 'loading' );
const bar = document.getElementById( 'bar' );
const uiText = document.getElementById( 'loading-text' );
const manager = new THREE.LoadingManager();

const progress = {
	total: 0, loaded: 0, label: '',
	files: [],                       // { url, kind, bytes, loaded, sizeFrom, ms }
	perFile: new Map(),              // url -> bytes counted so far (three loaders report cumulative)
	unknown: [],
};
const MB = ( b ) => ( b / 1e6 ).toFixed( 1 );
function drawProgress() {
	const pct = progress.total ? Math.min( 100, 100 * progress.loaded / progress.total ) : 0;
	bar.style.width = `${pct.toFixed( 1 )}%`;
	uiText.textContent = `${MB( progress.loaded )} / ${MB( progress.total )} MB` + ( progress.label ? ` — ${progress.label}` : '' );
}
function addBytes( url, delta ) { progress.loaded += delta; drawProgress(); }
/** three's Loader.loadAsync onProgress reports the file's CUMULATIVE bytes: turn it into a delta. */
function onProgressFor( url ) {
	return ( e ) => {
		const prev = progress.perFile.get( url ) || 0;
		const now = e && e.loaded ? e.loaded : prev;
		progress.perFile.set( url, now );
		addBytes( url, now - prev );
	};
}
/** HEAD every planned file so `total` is real before the first byte is fetched. */
async function measurePlan( files ) {
	progress.files = files;
	// A Gate 2 plan is a few hundred files: HEAD them 16 at a time rather than all at once, or the
	// browser's own connection limit turns the byte plan into the slowest part of the load.
	const one = async ( f ) => {
		try {
			const r = await fetch( f.url, { method: 'HEAD', cache: 'no-cache' } );
			const n = Number( r.headers.get( 'content-length' ) ) || 0;
			if ( r.ok && n ) { f.bytes = n; f.sizeFrom = 'HEAD'; return; }
		} catch ( e ) { /* fall through to the manifest's number */ }
		if ( f.bytes ) { f.sizeFrom = 'manifest'; return; }
		f.bytes = 0; f.sizeFrom = 'unknown'; progress.unknown.push( f.url );
	};
	let next = 0;
	await Promise.all( Array.from( { length: Math.min( 16, files.length ) },
		async () => { while ( next < files.length ) await one( files[ next ++ ] ); } ) );
	progress.total = files.reduce( ( a, f ) => a + ( f.bytes || 0 ), 0 );
	note( `load plan: ${files.length} files, ${MB( progress.total )} MB (${files.map( f => `${f.kind} ${MB( f.bytes )}` ).join( ', ' )})`
		+ ( progress.unknown.length ? ` — ${progress.unknown.length} of unknown size` : '' ) );
	drawProgress();
}
/** Streamed fetch: exact byte progress and the buffer, for the glbs the viewer parses itself. */
async function fetchBuffer( url ) {
	const r = await fetch( url, { cache: 'no-cache' } );
	if ( ! r.ok ) throw new Error( `${r.status} ${r.statusText} for ${url}` );
	if ( ! r.body ) { const b = await r.arrayBuffer(); addBytes( url, b.byteLength ); return b; }
	const reader = r.body.getReader();
	const chunks = []; let got = 0;
	for ( ; ; ) {
		const { done, value } = await reader.read();
		if ( done ) break;
		chunks.push( value ); got += value.byteLength; addBytes( url, value.byteLength );
	}
	const out = new Uint8Array( got );
	let off = 0;
	for ( const c of chunks ) { out.set( c, off ); off += c.byteLength; }
	return out.buffer;
}

// ---------------------------------------------------------------------------- main
let composer, lutPass, water, manifest, stations, sunLight, billboards = null, pmremTarget = null, postState = null;
let impostorGroup = null, impostorReport = null, probeTarget = null, probeReport = null, reflectionSet = null;
let diffusePmremTarget = null, glossyEnv = null, envRotation = new THREE.Euler();
let gate3Report = null;
let patchedMaterials = 0, lightmapsApplied = 0;
const unpatchedMaterials = new Set();
const seenMats = new Set(), lightmapMaterials = [], noLightmapMaterials = [];
let userControlled = false, currentStation = null;
let lightingMode = 'baked';
const loadTimes = { plan_s: 0, sky_s: 0, lut_s: 0, glb_s: 0, tex_s: 0, total_s: 0 };
const glbReport = [];
const uvDequantReport = [];
const glbRoots = [];
let chunkStats = null;
let materialsMode = 'grey', pbrReport = null, detailReport = null;

/** baked  = the Gate 0/3 path: lightmaps carry the diffuse, so the sun and the environment are
 *           stripped to their specular terms (materials.js).
 *  direct = the Gate 1 path: the export has NO lightmaps yet (neutral grey + ORN normal/AO only),
 *           so three's own lighting does the work — full DirectionalLight + PMREM irradiance, same
 *           sun irradiance and the same LUT/exposure, no shadow maps.  Chosen from the manifest, so
 *           it is known before a single material is touched. */
function pickLightingMode() {
	if ( CFG.lighting === 'baked' || CFG.lighting === 'direct' ) return CFG.lighting;
	const tex = manifest.raw.textures || {};
	// v4 states it: lightmaps.mode === 'baked' with at least one usable map.
	if ( manifest.gate3 && manifest.gate3.mode === 'baked'
		&& ( manifest.gate3.ownCount || manifest.gate3.slotCount ) ) return 'baked';
	const baked = manifest.lightmaps.length > 0
		|| Object.keys( tex ).some( k => k.toLowerCase().includes( 'lightmap' ) )
		|| !! ( manifest.raw.gltf && manifest.raw.gltf.lightmap_slot );
	return baked ? 'baked' : 'direct';
}

/** grey = the Gate 1 neutral-grey export (ORN normal + AO only), the frames QA scored at Gate 1;
 *  pbr  = manifest v3's per-material albedo / roughness / normal KTX2 sets on top of the same
 *         geometry and the same `direct` lighting.  `auto` takes pbr whenever the manifest carries
 *         a texture set, so a grey capture can never be reported as a PBR one by accident. */
function pickMaterialsMode() {
	const has = manifest.materials && manifest.materials.count > 0;
	if ( CFG.materials === 'grey' ) return 'grey';
	if ( CFG.materials === 'pbr' ) {
		if ( has ) return 'pbr';
		note( '?materials=pbr but the manifest carries no texture set: falling back to grey' );
		return 'grey';
	}
	const declared = ( manifest.materials && manifest.materials.mode ) || null;
	if ( declared === 'grey' || declared === 'neutral' ) return 'grey';
	return has ? 'pbr' : 'grey';
}

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
	note( `manifest ${manifest.schema || '(no schema)'} at ${manifestUrl}` );
	if ( CFG.skyRotationDeg !== null ) manifest.sky.rotationDeg = CFG.skyRotationDeg;
	if ( CFG.exposureOverride !== null ) manifest.exposure = CFG.exposureOverride;
	if ( CFG.sun !== null ) { manifest.sun.irradiance = CFG.sun; manifest.sun.color = [ 1, 1, 1 ]; note( `sun irradiance overridden to ${CFG.sun}` ); }
	if ( CFG.glbOverride ) {
		manifest.glbs = CFG.glbOverride.split( ',' ).filter( Boolean ).map( ( u, i ) => ( {
			url: new URL( u, manifestUrl ).href, name: u.split( '/' ).pop(), cls: `override_${i}`, bytes: null, order: i } ) );
		note( `?glb override: ${manifest.glbs.map( g => g.name ).join( ', ' )}` );
	}
	// The colour pipeline (LUT + the two sky equirects) is the FROZEN Phase 5 look and is identical
	// for every gate.  If this manifest does not carry it yet, borrow it from another manifest rather
	// than falling back to gamma 2.2 and reporting parity against the wrong transform.
	const needColour = ! ( manifest.lut && manifest.lut.url ) || ! manifest.sky.camera;
	if ( CFG.colourFrom || needColour ) {
		const src = new URL( CFG.colourFrom || '/assets/gate0/manifest.json', manifestUrl ).href;
		if ( src !== manifestUrl ) {
			try {
				const r = await fetch( src, { cache: 'no-cache' } );
				if ( ! r.ok ) throw new Error( `${r.status}` );
				const other = normaliseManifest( await r.json(), src );
				const took = [];
				if ( ! ( manifest.lut && manifest.lut.url ) && other.lut && other.lut.url ) { manifest.lut = other.lut; manifest.exposure = other.exposure; took.push( 'lut + exposure' ); }
				if ( ! manifest.sky.camera && other.sky.camera ) { manifest.sky = other.sky; took.push( 'sky' ); }
				note( took.length ? `colour borrowed from ${src}: ${took.join( ', ' )} (this manifest carries none)`
					: `colour fallback ${src} had nothing to add` );
			} catch ( e ) { note( `colour fallback ${src} failed: ${e.message}` ); }
		}
	}
	// `uv2_in_glb` moves faster in the glbs than in the manifest: export/gate3_relay_check.py writes
	// what each re-packed glb ACTUALLY carries, and that file wins until the bake rewrites the flags.
	if ( manifest.gate3 ) {
		const url = new URL( 'uv2_relay_status.json', manifestUrl ).href;
		try {
			const r = await fetch( url, { cache: 'no-cache' } );
			if ( r.ok ) {
				const st = applyUv2RelayStatus( manifest, await r.json() );
				note( `uv2_relay_status.json: ${st.applied} asset(s) checked against the packed glbs, `
					+ `${st.flipped.length} flag(s) flipped${st.flipped.length ? ` (${st.flipped.join( '; ' )})` : ''}; `
					+ `${manifest.gate3.ownCount} own map(s) usable, ${manifest.gate3.blockedNoUv2} blocked, `
					+ `${manifest.gate3.frozenUsed} on the frozen layout`
					+ ( st.note ? `; vertex irradiance: ${st.note}` : '' ) );
			} else note( `no uv2_relay_status.json (${r.status}): the manifest's own uv2_in_glb flags stand` );
		} catch ( e ) { note( `uv2_relay_status.json fetch failed (${e.message}): the manifest's own flags stand` ); }
	}

	lightingMode = pickLightingMode();
	note( `lighting mode: ${lightingMode}${CFG.lighting !== 'auto' ? ' (?lighting override)' : ''} — `
		+ ( lightingMode === 'baked' ? 'lightmaps carry the diffuse, sun and env are specular-only'
			: 'no lightmaps in the manifest: full DirectionalLight + PMREM irradiance, no shadow maps' ) );

	materialsMode = pickMaterialsMode();
	note( `materials mode: ${materialsMode}${CFG.materials !== 'auto' ? ' (?materials override)' : ''} — `
		+ ( materialsMode === 'pbr'
			? `${manifest.materials.count} manifest texture set(s), ${manifest.materials.maps} maps`
			: 'neutral grey as exported (Gate 1 frames)' )
		+ ( manifest.materials && manifest.materials.mode ? `; manifest declares "${manifest.materials.mode}"` : '' ) );

	// byte budget before anything downloads ------------------------------------------------------
	const tp = performance.now();
	const plan = [];
	if ( manifest.sky.camera ) plan.push( { url: manifest.sky.camera, kind: 'sky.camera', bytes: manifest.raw.sky?.camera?.bytes_hdr || 0 } );
	if ( manifest.sky.glossy ) plan.push( { url: manifest.sky.glossy, kind: 'sky.glossy', bytes: manifest.raw.sky?.glossy?.bytes_hdr || 0 } );
	if ( manifest.sky.diffuse ) plan.push( { url: manifest.sky.diffuse, kind: 'sky.diffuse', bytes: manifest.raw.sky?.diffuse?.bytes_hdr || 0 } );
	if ( CFG.lut && manifest.lut && manifest.lut.url && ! CFG.testLut ) plan.push( { url: manifest.lut.url, kind: 'lut', bytes: 0 } );
	if ( ! CFG.testScene ) for ( const g of manifest.glbs ) plan.push( { url: g.url, kind: `glb:${g.cls}`, bytes: g.bytes || 0 } );
	// The PBR set is part of the payload, so it is in the byte plan from the first frame of the bar.
	if ( materialsMode === 'pbr' && ! CFG.testScene ) plan.push( ...pbrPlan( manifest.materials.sets ) );
	await measurePlan( plan );
	loadTimes.plan_s = ( performance.now() - tp ) / 1000;

	// sky --------------------------------------------------------------------------------------
	const ts = performance.now();
	await loadSky();
	loadTimes.sky_s = ( performance.now() - ts ) / 1000;

	// sun --------------------------------------------------------------------------------------
	const d = manifest.sun.toSunBlender;                           // direction TOWARD the sun, Blender axes
	sunLight = new THREE.DirectionalLight( new THREE.Color().setRGB( ...manifest.sun.color, THREE.LinearSRGBColorSpace ), manifest.sun.irradiance );
	sunLight.position.copy( b2t( d[ 0 ], d[ 1 ], d[ 2 ] ).multiplyScalar( 1000 ) );   // the light sits toward the sun, aiming at the origin
	sunLight.target.position.set( 0, 0, 0 );
	sunLight.castShadow = false;                                   // baked: shadows are in the lightmap; direct: carry 8 / Gate 2
	scene.add( sunLight, sunLight.target );
	note( `sun: three direction ${sunLight.position.clone().normalize().toArray().map( v => v.toFixed( 3 ) )}, irradiance ${manifest.sun.irradiance}, ${lightingMode === 'baked' ? 'specular only' : 'diffuse + specular (no shadow map)'}` );

	// water -------------------------------------------------------------------------------------
	if ( CFG.water ) {
		const reflPx = CFG.reflRes === 'full' ? 1024 : 512;
		water = makeWater( manifest.waterZ, { resolution: reflPx, debug: CFG.waterDebug,
			...( CFG.waterBlur !== null ? { reflBlur: CFG.waterBlur } : {} ),
			...( CFG.waterSat !== null ? { reflSat: CFG.waterSat } : {} ),
			...( CFG.waterDist !== null ? { distortion: CFG.waterDist } : {} ),
			...( CFG.waterNorm !== null ? { normalScale: CFG.waterNorm } : {} ),
			...( CFG.waterTile !== null ? { rippleTiling: CFG.waterTile } : {} ),
			...( CFG.waterAniso !== null ? { distortAniso: CFG.waterAniso } : {} ),
			...( CFG.waterHoriz !== null ? { horizonBias: CFG.waterHoriz } : {} ),
			...( CFG.waterGraze !== null ? { grazingGain: CFG.waterGraze } : {} ),
			...( CFG.waterCrest !== null ? { spread: CFG.waterCrest } : {} ),
			...( CFG.waterSlope !== null ? { slopeRms: CFG.waterSlope } : {} ),
			...( CFG.waterGrazeMax !== null ? { grazingMax: CFG.waterGrazeMax } : {} ),
			...( CFG.waterMurkGain !== null ? { murkGain: CFG.waterMurkGain } : {} ),
			...( CFG.waterMurk ? { murk: CFG.waterMurk.split( ',' ).map( Number ) } : {} ) } );
		scene.add( water );
		const wu = water.material.uniforms;
		note( `water plane at y = ${manifest.waterZ} (WATER_Z ${WATER_Z}), planar Reflector ${reflPx}x${reflPx}`
			+ ` (?reflres=${CFG.reflRes}), `
			+ `reflection gather ${wu.reflBlur.value} / saturation ${wu.reflSat.value}, `
			+ `ripple ${water.userData.waveSet.a.length} waves `
			+ `${water.userData.waveSet.b[ 0 ][ 1 ].toFixed( 2 )}-${water.userData.waveSet.b.at( -1 )[ 1 ].toFixed( 3 )} m, `
			+ `murk ${wu.murk.value.toArray().map( v => v.toFixed( 4 ) ).join( ', ' )}`
			+ ( CFG.waterMurk ? ' (?watermurk override)' : ` (derived; ?watermurkgain=${wu.murk.value.r / water.userData.murkDerived[ 0 ]})` )
			+ `, grazing cap ${wu.grazingMax.value}` );
	}

	// display transform ---------------------------------------------------------------------------
	const size = canvasSize();
	composer = new EffectComposer( renderer, new THREE.WebGLRenderTarget( size.w, size.h, {
		type: THREE.HalfFloatType, colorSpace: THREE.NoColorSpace, samples: 4,
	} ) );
	composer.addPass( new RenderPass( scene, camera ) );
	// Gate 4 item 4: the Phase 5 compositor, in scene-linear BEFORE the LUT, each part switchable.
	// Default OFF so every capture so far stays comparable; ?post=all turns the chain on.
	// `want` is what ?post asked for; the sibling fields are what actually ended up in the chain.
	postState = { requested: CFG.post ?? 'none', want: parsePost( CFG.post ?? 'none' ), mistSpec: null, bloom: false, vignette: 0 };
	const comp = readCompositor( manifest.compositor || ( manifest.raw && manifest.raw.compositor ) );
	postState.compositor = comp;
	if ( comp ) {
		if ( postState.want.mist ) {
			const mm = String( CFG.mist || '' ).split( ',' ).map( x => ( x.trim() === '' ? NaN : Number( x ) ) );
			const spec = applyMist( scene, comp, {
				near: isFinite( mm[ 0 ] ) ? mm[ 0 ] : null,
				far: isFinite( mm[ 1 ] ) ? mm[ 1 ] : null,
			} );
			if ( spec && spec.refused ) { postState.mistRefused = spec.refused; note( `post mist REFUSED: ${spec.refused}` ); }
			else if ( spec ) {
				postState.mistSpec = spec;
				note( `post mist: COMP_golden_hour airlight cap ${spec.cap} * (1 - exp(-k ${spec.k} * mist)), `
					+ `mist = ${spec.shape} over ${spec.near}..${spec.far} m along the view ray (extinction length `
					+ `${spec.extinctionLength_m.toFixed( 0 )} m), haze [${comp.hazeColor.map( v => v.toFixed( 2 ) ).join( ', ' )}], `
					+ `from ${spec.source}`
					+ ( spec.invented ? '. THESE ARE NOT BLENDER\'S NUMBERS - no scored capture may use them.' : '' ) );
			}
		} else removeMist( scene );
		if ( postState.want.bloom ) {
			const bp = makeBloom( comp, size, { half: CFG.bloomRes !== 'full' } );
			if ( bp ) { composer.addPass( bp ); postState.bloom = true; postState.bloomRes = CFG.bloomRes;
				note( `post bloom: threshold ${comp.bloomThreshold.toFixed( 3 )} (scene-linear), strength ${comp.bloomStrength}, `
					+ `radius ${comp.bloomSize}, mip chain from ${bp.userData.sourceResolution.map( Math.round ).join( 'x' )} (?bloomres=${CFG.bloomRes})` ); }
		}
	}
	lutPass = new LUTDisplayPass( { exposure: manifest.exposure } );
	lutPass.renderToScreen = true;
	composer.addPass( lutPass );
	const tl = performance.now();
	await loadLUT();
	loadTimes.lut_s = ( performance.now() - tl ) / 1000;
	if ( CFG.haze > 0 ) { lutPass.uniforms.hazeStrength.value = CFG.haze; note( `diagnostic constant haze ${CFG.haze} with COMP_golden_hour's colour (not the real depth mist)` ); }
	if ( comp && postState.want.vignette ) { lutPass.uniforms.vignette.value = comp.vignette; postState.vignette = comp.vignette;
		note( `post vignette: ${comp.vignette} in linear, before the transform` ); }
	note( `quality preset '${CFG.quality}'${QUALITY_RAW !== CFG.quality ? ` (?quality=${QUALITY_RAW} is not a preset; using look)` : ''}: `
		+ `bloom ${CFG.bloomRes}-res, Reflector ${CFG.reflRes}-res target, reflection set ${CFG.reflSet}` );
	note( `post chain: ${[ postState.mistSpec && 'mist', postState.bloom && 'bloom', postState.vignette && 'vignette' ].filter( Boolean ).join( ' + ' ) || 'none'} (?post=${postState.requested})` );
	note( `display: tone mapping OFF, exposure x${manifest.exposure.toFixed( 5 )}, LUT ${lutPass.uniforms.lutEnabled.value ? 'on' : 'OFF (gamma 2.2 fallback)'}` );

	if ( ! CFG.hud ) document.getElementById( 'hud' ).classList.add( 'hidden' );
	applyStation( CFG.station );
	resize();
	window.addEventListener( 'resize', resize );
	installControls();

	// geometry: the glbs in the manifest's order, each one drawn as soon as it lands --------------
	const tg = performance.now();
	if ( manifest.glbs.length && ! CFG.testScene ) await loadGlbs();
	else {
		buildTestScene( scene );
		if ( CFG.testScene ) note( 'test scene (?test=1)' );
		else {
			// A capture of the test scene must never be mistaken for a capture of the building.
			const msg = `PFA_NO_GEOMETRY: the manifest at ${manifestUrl} yielded 0 glbs `
				+ `(looked at glbs, glb.per_class, glb.parts, glb.files, glb.classes, files.glbs, glb); `
				+ `rendering the TEST SCENE, not the model`;
			note( msg );
			console.error( `[pfa] ${msg}` );
			window.__pfaNoGeometry = msg;
			uiText.textContent = 'no geometry in the manifest';
		}
	}
	loadTimes.glb_s = ( performance.now() - tg ) / 1000;

	// materials: the Gate 2 PBR texture sets, nearest material to THIS station first ---------------
	if ( materialsMode === 'pbr' && glbRoots.length ) {
		const tt = performance.now();
		let drawn = 0;
		const texturesBeforePbr = collectTextures( scene );
		pbrReport = await applyPbrSets( {
			scene, camera, sets: manifest.materials.sets, note,
			loadTexture: ( url ) => {
				progress.label = url.split( '/' ).pop();
				return /\.ktx2$/i.test( url )
					? getKTX2().loadAsync( url, onProgressFor( url ) )
					: new THREE.TextureLoader( manager ).loadAsync( url, onProgressFor( url ) );
			},
			// progressive: the near materials are visible while the far ones are still downloading
			onLoaded: ( m, applied, done, total ) => {
				progress.label = `materials ${done}/${total}`;
				if ( done - drawn >= 16 || done === total ) { drawn = done; renderFrame(); }
			},
		} );
		// QA-12-1: the tiling grain layer on top of the baked maps, before the orphan sweep so a
		// detail texture is never mistaken for an orphan.
		if ( CFG.detail > 0 && manifest.materials.detail ) {
			detailReport = await applyDetail( {
				scene, detail: manifest.materials.detail, note,
				projection: CFG.detailProj, strength: CFG.detail, normalScale: CFG.detailNormal,
				lodBias: CFG.detailBias, gain: CFG.detailGain, debug: parseInt( qs.get( 'detaildebug' ) || '0', 10 ),
				synthetic: CFG.detailTest === 'noise',
				loadTexture: ( url ) => {
					progress.label = url.split( '/' ).pop();
					return /\.ktx2$/i.test( url )
						? getKTX2().loadAsync( url, onProgressFor( url ) )
						: new THREE.TextureLoader( manager ).loadAsync( url, onProgressFor( url ) );
				},
			} );
			renderFrame();
		} else if ( manifest.materials.detail ) {
			note( `detail layer OFF (?detail=${CFG.detail}); the manifest carries ${Object.keys( manifest.materials.detail.sets ).length} tiling set(s)` );
		}

		// A replaced Gate 1 map (the ORN normals) is unreachable but still on the GPU: free it.
		const freed = disposeOrphans( scene, texturesBeforePbr );
		pbrReport.disposed = freed;
		loadTimes.tex_s = ( performance.now() - tt ) / 1000;
		note( `pbr textures in ${loadTimes.tex_s.toFixed( 2 )} s; `
			+ `${freed.disposed} superseded Gate 1 texture(s) disposed, ${MB( freed.freed_bytes )} MB freed` );
	}

	// QA-13-1: the baked hero probe as the irradiance of everything with no baked light ------------
	// AFTER the PBR and detail passes (they may add an envMap or replace a material) and BEFORE the
	// impostors, which are ShaderMaterials and take no environment at all.  Only in `baked` mode:
	// ?lighting=direct is the untouched A/B.
	if ( CFG.probeEnv && lightingMode === 'baked' && manifest.gate3 && manifest.gate3.probe ) {
		try {
			const rt = await buildProbeEnv( manifest.gate3.probe, {
				renderer, note,
				loadHdr: ( url ) => { progress.label = url.split( '/' ).pop(); return new RGBELoader( manager ).loadAsync( url, onProgressFor( url ) ); },
			} );
			if ( rt ) {
				probeTarget = rt;
				// ?probespec=1 wants the probe as the SPECULAR env of the baked materials, and
				// finishMaterials() already assigned the sky glossy one before the probe existed.
				// Re-run it now that probeTarget is set; it is idempotent (it skips a material that
				// already has the env it would assign).
				if ( CFG.probeSpec ) assignSpecularEnv();
				probeReport = applyProbeEnv( scene, rt.texture, { note, gate3Report } );
				probeReport.station = manifest.gate3.probe.station || null;
				probeReport.positionBlender = manifest.gate3.probe.positionBlender || null;
				note( 'probe env is a SINGLE-POINT approximation taken at the hero station, and the manifest\'s own '
					+ 'probe.use says it is not the diffuse environment; this use of it is the lead\'s QA-13-1 call '
					+ 'and applies only to surfaces with no baked light. ?probe=0 restores the sky-diffuse path.' );
			}
		} catch ( e ) { note( `probe env failed: ${e.message}; the sky-diffuse path stays` ); }
	} else if ( manifest.gate3 && manifest.gate3.probe && ! CFG.probeEnv ) {
		note( 'probe env OFF (?probe=0): surfaces with no baked light stay on the sky-diffuse PMREM' );
	}

	// far-tree impostors (Gate 4 item 2) ----------------------------------------------------------
	// They REPLACE the Gate 1 placeholder quads: when they build, the placeholders are not made at all,
	// so a capture can never show a grey card where a tree should be and the name sweep stays clean.
	const impAvailable = CFG.impostors && manifest.gate3 && manifest.gate3.impostors
		&& manifest.gate3.impostors.count && manifest.treesFar.length;
	if ( impAvailable ) {
		const built = buildImpostors( {
			impostors: manifest.gate3.impostors, far: manifest.treesFar, note,
			normalDepth: CFG.impNormalDepth, debug: CFG.impDebug,
			// the same mist the rest of the scene got, as plain uniforms (a ShaderMaterial gets no
			// automatic fog) - so the far trees recede with everything else when ?post has mist on
			fog: ( scene.fog && postState && postState.mistSpec ) ? {
				color: scene.fog.color, near: scene.fog.near, far: scene.fog.far,
				cap: postState.mistSpec.cap, k: postState.mistSpec.k, intensity: postState.mistSpec.intensity,
			} : null,
			loadTexture: ( url ) => {
				progress.label = url.split( '/' ).pop();
				return /\.ktx2$/i.test( url ) ? getKTX2().loadAsync( url, onProgressFor( url ) )
					: new THREE.TextureLoader( manager ).loadAsync( url, onProgressFor( url ) );
			},
		} );
		impostorReport = built.report;
		if ( built.group ) { scene.add( built.group ); impostorGroup = built.group; }
		await built.report.promise;
	} else if ( manifest.treesFar.length && ! CFG.impostors ) {
		note( 'far-tree impostors suppressed (?impostors=0)' );
	}

	// far-tree billboards (Gate 1 stand-in for the Gate 3 impostors) ------------------------------
	if ( ! impAvailable && CFG.billboards && manifest.treesFar.length ) {
		billboards = makeTreeBillboards( manifest.treesFar );
		// G1-5: under `baked` lighting every other material is specular-only, so an unpatched
		// placeholder quad would take the full 67.3 W/m2 sun diffuse and read as a white card.
		if ( lightingMode === 'baked' ) {
			let n = 0;
			for ( const m of billboards.children ) if ( m.material ) { patchBakedMaterial( m.material, {} ); n ++; }
			note( `${n} billboard placeholder material(s) put on the specular-only path (G1-5)` );
		}
		scene.add( billboards );
		aimBillboards( billboards, camera );
		note( `${manifest.treesFar.length} far-tree placeholder quads in ${billboards.children.length} prototype group(s), tagged pfaPlaceholder=gate3_tree_impostor` );
	} else if ( manifest.treesFar.length && ! impAvailable ) {
		note( `${manifest.treesFar.length} far-tree quads suppressed (?billboards=0)` );
	}

	// Item 6: cut the Reflector's DRAW SET.  After every glb, the impostors and the probe pass, so
	// the traversal sees the final scene.  The main camera is re-made per station, so applyStation
	// enables every layer on it too.
	// `orn` (the default) cuts the 436 ORN instances only.  `both` also cuts the backdrop city
	// blocks - MEASURED and rejected at the hero: the backdrop IS inside the reflected frustum there,
	// and removing it left the reflection reading sky (lum 1.227x, sat 0.527x, R-B +23.2 -> -17.6).
	// The water is a ShaderMaterial, so three's fog chunk never reaches it and applyMist skips it by
	// name: it must be given the same airlight explicitly, or the one surface spanning 5-600 m at the
	// hero is the only thing in the frame with no haze.
	if ( water && water.userData.applyFog && scene.fog && postState && postState.mistSpec ) {
		const ok = water.userData.applyFog( { color: scene.fog.color, near: scene.fog.near, far: scene.fog.far,
			cap: postState.mistSpec.cap, k: postState.mistSpec.k, intensity: postState.mistSpec.intensity } );
		if ( ok ) note( 'water surface takes the COMP_golden_hour airlight too (it is a ShaderMaterial, so three\'s fog chunk cannot)' );
	}

	if ( water && CFG.reflSet !== 'full' ) reflectionSet = reduceReflectionSet( scene, water, camera,
		{ note, orn: true, backdrop: CFG.reflSet === 'both' } );
	else if ( water ) note( 'reflection draw set NOT reduced (?reflset=full): the Reflector traverses the whole scene' );

	// first frame -------------------------------------------------------------------------------
	renderFrame();
	requestAnimationFrame( () => {
		renderFrame();
		ui.style.display = 'none';
		loadTimes.total_s = ( performance.now() - t0 ) / 1000;   // set BEFORE __pfaReady: the harness
		window.__pfaReady = true;                                // reads __pfaInfo() the moment it flips
		note( `ready in ${loadTimes.total_s.toFixed( 2 )} s: ${MB( progress.loaded )} MB loaded of ${MB( progress.total )} MB planned `
			+ `(plan ${loadTimes.plan_s.toFixed( 2 )} s, sky ${loadTimes.sky_s.toFixed( 2 )} s, lut ${loadTimes.lut_s.toFixed( 2 )} s, glb ${loadTimes.glb_s.toFixed( 2 )} s)` );
		animate();
	} );
}

async function loadSky() {
	const load = ( url ) => {
		const L = url.endsWith( '.exr' ) ? new EXRLoader( manager ) : new RGBELoader( manager );
		progress.label = url.split( '/' ).pop();
		return L.loadAsync( url, onProgressFor( url ) );
	};
	const rotY = THREE.MathUtils.degToRad( manifest.sky.rotationDeg );
	envRotation = new THREE.Euler( 0, rotY, 0 );
	const pmremOf = async ( url ) => {
		const tex = await load( url );
		const pmrem = new THREE.PMREMGenerator( renderer );
		pmrem.compileEquirectangularShader();
		const rt = pmrem.fromEquirectangular( tex );
		tex.dispose(); pmrem.dispose();
		return rt;
	};
	try {
		if ( manifest.sky.camera ) {
			const tex = await load( manifest.sky.camera );
			tex.mapping = THREE.EquirectangularReflectionMapping;
			scene.background = tex;
			scene.backgroundRotation = new THREE.Euler( 0, rotY, 0 );
			note( `sky background ${manifest.sky.camera.split( '/' ).pop()} ${tex.image.width}x${tex.image.height}, rotation ${manifest.sky.rotationDeg} deg` );
		} else { scene.background = new THREE.Color( 0.09, 0.13, 0.22 ); note( 'no camera sky: flat background' ); }
		if ( manifest.sky.glossy ) {
			pmremTarget = await pmremOf( manifest.sky.glossy );
			glossyEnv = pmremTarget.texture;
			note( `PMREM specular environment from ${manifest.sky.glossy.split( '/' ).pop()}` );
		}
		// QA-12b-1: the world's DIFFUSE branch is a different colour from its glossy branch, and using
		// the glossy PMREM as the diffuse environment made 16-22 % of the cam02/cam06 building pixels
		// read olive-green.  v4 ships the diffuse branch as its own equirect, so:
		//   scene.environment      = the DIFFUSE PMREM  -> the irradiance of everything with no lightmap
		//                            (near trees, impostors, foliage, shrubs)
		//   material.envMap        = the GLOSSY PMREM on every lightmapped material, whose env DIFFUSE
		//                            term is deleted in the shader anyway, so it is specular-only
		if ( manifest.sky.diffuse ) {
			diffusePmremTarget = await pmremOf( manifest.sky.diffuse );
			scene.environment = diffusePmremTarget.texture;
			scene.environmentRotation = envRotation;
			note( `PMREM diffuse environment from ${manifest.sky.diffuse.split( '/' ).pop()} (irradiance for everything without a lightmap; QA-12b-1)` );
		} else if ( glossyEnv ) {
			scene.environment = glossyEnv;
			scene.environmentRotation = envRotation;
			note( 'no sky.diffuse in the manifest: the GLOSSY PMREM is the diffuse environment too (QA-12b-1 unfixed)' );
		}
	} catch ( e ) { note( `sky load failed: ${e.message}` ); }
}

/** Every baked material takes its SPECULAR from the glossy branch through its own envMap, so the
 *  scene-wide diffuse environment can stay on the diffuse branch.  Called once, after the materials
 *  are final. */
function assignSpecularEnv() {
	// QA-12b-1 A/B (?probespec=1): the lead's hypothesis is that Cycles' shaded stone receives a
	// glossy reflection of the WARM sunlit surroundings - the building and the ground - which a
	// SKY-ONLY glossy PMREM cannot give, and that the missing warmth is what reads as olive.  The
	// hero probe's glossy branch does contain those surroundings, so this swaps it in as the
	// specular env of every BAKED material.  Same single-point caveat as the irradiance use.
	const specEnv = ( CFG.probeSpec && probeTarget ) ? probeTarget.texture : glossyEnv;
	if ( ! specEnv || ! diffusePmremTarget ) return 0;     // nothing to separate
	let n = 0;
	scene.traverse( ( o ) => {
		if ( ! o.isMesh ) return;
		for ( const m of ( Array.isArray( o.material ) ? o.material : [ o.material ] ) ) {
			if ( ! m || ! m.isMeshStandardMaterial || ! m.userData.pfaPatched || m.envMap === specEnv ) continue;
			m.envMap = specEnv;
			m.envMapRotation.copy( envRotation );
			m.needsUpdate = true;
			n ++;
		}
	} );
	if ( n ) note( `${n} baked material(s) take specular from ${CFG.probeSpec && probeTarget ? 'the HERO PROBE (?probespec=1)' : 'the GLOSSY sky PMREM'} `
		+ '(material.envMap); the scene environment stays the DIFFUSE branch' );
	return n;
}

let ktx2Loader = null;
function getKTX2() {
	// One instance, kept alive: it owns a worker pool and also transcodes any .ktx2 lightmap.
	if ( ! ktx2Loader ) ktx2Loader = new KTX2Loader( manager ).setTranscoderPath( '/basis/' ).detectSupport( renderer );
	return ktx2Loader;
}

/** Cycles' colour-off diffuse pass is irradiance/pi and three's lightMap path divides by pi again in
 *  BRDF_Lambert, so the manifest's lightmap_scale (pi) is applied as lightMapIntensity. */
let lightmapScale = 1.0;

async function loadGlbs() {
	lightmapScale = CFG.lmScale !== null ? CFG.lmScale : manifest.lightmapScale;
	note( `lightMapIntensity = lightmap_scale ${lightmapScale.toFixed( 5 )}${CFG.lmScale !== null ? ' (?lmscale override)' : ''}` );
	const loader = new GLTFLoader( manager ).setKTX2Loader( getKTX2() ).setMeshoptDecoder( MeshoptDecoder );
	let first = true;
	for ( const g of manifest.glbs ) {
		const t = performance.now();
		progress.label = g.name;
		try {
			const buf = await fetchBuffer( g.url );
			const base = g.url.slice( 0, g.url.lastIndexOf( '/' ) + 1 );
			const gltf = await loader.parseAsync( buf, base );
			gltf.scene.name = `WEB_glb_${g.cls}`;
			// FIRST, before any pass: gltfpack stores texcoords as normalised 12-bit ints with the
			// dequantisation in KHR_texture_transform on the baseColorTexture only, so every UV that
			// reaches a shader is 1/16 of its real value until this undoes it on the attribute.
			// See src/uvDequant.js.  ?uvdq=0 restores the broken behaviour for an A/B.
			uvDequantReport.push( { name: g.name, ...dequantizeUvs( gltf.scene, { note, enabled: CFG.uvDequant } ) } );
			scene.add( gltf.scene );
			glbRoots.push( gltf.scene );
			const r = processGltf( gltf, g );
			r.bytes = buf.byteLength; r.wall_s = ( performance.now() - t ) / 1000;
			glbReport.push( r );
			note( `glb ${g.name} (${g.cls}) ${MB( r.bytes )} MB in ${r.wall_s.toFixed( 2 )} s: ${r.meshes} meshes, `
				+ `${r.instancedMeshes} instanced (${r.instances} instances), ${Math.round( r.tris )} placed tris, ${r.materials} materials` );
			if ( r.hiddenBoards ) note( `${r.hiddenBoards} ENV_treeboard_* stand-ins hidden (?treeboards=0)` );
		} catch ( e ) {
			glbReport.push( { name: g.name, cls: g.cls, error: e.message } );
			note( `glb ${g.name} FAILED: ${e.message}` );
			continue;
		}
		// progressive: draw what has arrived, and let the loading panel go translucent over it
		if ( first ) { ui.style.background = 'rgba(11, 13, 16, 0.55)'; first = false; }
		renderFrame();
		await new Promise( ( r ) => requestAnimationFrame( r ) );
	}
	// Gate 3 (manifest v4): the baked lightmaps.  BEFORE chunking (a chunk inherits its slice of the
	// per-instance slot attribute) and BEFORE the PBR / detail passes, which match on material NAME
	// and so texture every clone this pass makes.
	if ( manifest.gate3 && lightingMode === 'baked' ) {
		gate3Report = applyGate3Lightmaps( {
			scene, gate3: manifest.gate3, assets: manifest.assets, note, flipV: CFG.lmFlip, encodeOverride: CFG.lmEnc,
			vertexIrr: CFG.vertexIrr,
			loadTexture: ( url ) => {
				progress.label = url.split( '/' ).pop();
				return /\.ktx2$/i.test( url ) ? getKTX2().loadAsync( url, onProgressFor( url ) )
					: ( /\.(hdr)$/i.test( url ) ? new RGBELoader( manager ).loadAsync( url, onProgressFor( url ) )
						: ( /\.exr$/i.test( url ) ? new EXRLoader( manager ).loadAsync( url, onProgressFor( url ) )
							: new THREE.TextureLoader( manager ).loadAsync( url, onProgressFor( url ) ) ) );
			},
		} );
		await gate3Report.promise;
		lightmapsApplied += gate3Report.own.applied;
		patchedMaterials += gate3Report.own.applied + gate3Report.slots.meshes.length;
	}

	// QA-11d-1: a site-spanning InstancedMesh passes the frustum test everywhere.  Split those
	// batches into regional ones so a station that sees little of the site draws little of it.
	chunkStats = { candidates: 0, split: 0, chunks: 0, added: 0, batches: [] };
	const chunkArgs = ( CFG.chunk || '' ).split( ',' ).map( Number );
	if ( CFG.chunk !== '0' ) {
		const opts = {};
		if ( chunkArgs.length && isFinite( chunkArgs[ 0 ] ) && chunkArgs[ 0 ] > 0 ) opts.minRadius = chunkArgs[ 0 ];
		if ( isFinite( chunkArgs[ 1 ] ) ) opts.maxDepth = chunkArgs[ 1 ];
		if ( isFinite( chunkArgs[ 2 ] ) ) opts.gain = chunkArgs[ 2 ];
		if ( isFinite( chunkArgs[ 3 ] ) ) opts.budget = chunkArgs[ 3 ];
		chunkStats.opts = opts;
		// The budget is the ADDED draw calls over the WHOLE scene, so it has to be spent across the
		// glbs, not per glb (each root would otherwise get the full allowance).
		let left = opts.budget !== undefined ? opts.budget : 32;
		for ( const root of glbRoots ) {
			const s = chunkInstancedMeshes( root, { ...opts, budget: left } );
			left -= s.added;
			chunkStats.candidates += s.candidates; chunkStats.split += s.split;
			chunkStats.chunks += s.chunks; chunkStats.added += s.added;
			chunkStats.batches.push( ...s.batches );
		}
		note( `instance chunking (QA-11d-1): ${chunkStats.split} of ${chunkStats.candidates} site-spanning batches `
			+ `(bounding radius >= ${opts.minRadius || 30} m, depth ${opts.maxDepth || 2}, gain ${opts.gain ?? 0.8}) `
			+ `split into ${chunkStats.chunks} regional batches, `
			+ `+${chunkStats.added} draw calls when every chunk is in frame` );
	} else { note( 'instance chunking disabled (?chunk=0)' ); }
	finishMaterials();
}

/** Walk one loaded glb: count it, and put every MeshStandardMaterial on the right lighting path. */
function processGltf( gltf, g ) {
	let tris = 0, meshes = 0, instancedMeshes = 0, instances = 0, materials = 0;
	let hiddenBoards = 0;
	gltf.scene.traverse( ( o ) => {
		if ( ! o.isMesh ) return;
		// QA round 11b: the export ships opaque ENV_treeboard_* stand-ins for the Gate 3 impostors; ?treeboards=0 hides them
		// gltfpack -mi drops node names, so the boards are recognised by their material (MAT_EXP_treeboard), one InstancedMesh
		if ( ! CFG.treeboards ) {
			const mm = Array.isArray( o.material ) ? o.material : [ o.material ];
			if ( mm.some( ( m ) => m && /treeboard|impostor|billboard/i.test( m.name ) ) ) { o.visible = false; hiddenBoards += o.isInstancedMesh ? o.count : 1; }
		}
		meshes ++;
		const geo = o.geometry;
		const n = ( geo.index ? geo.index.count : geo.attributes.position.count ) / 3;
		if ( o.isInstancedMesh ) { instancedMeshes ++; instances += o.count; }
		tris += n * ( o.isInstancedMesh ? o.count : 1 );
		const mats = Array.isArray( o.material ) ? o.material : [ o.material ];
		for ( const m of mats ) {
			if ( ! m || ! m.isMeshStandardMaterial ) continue;
			if ( seenMats.has( m ) ) continue;
			seenMats.add( m ); materials ++;
			// QA round 11 belt-and-braces: a glTF texCoord of -1 (UV-less mesh) reaches three.js as channel -1
			// and kills the program.  Clamp every map's channel to 0 and say so once per material.
			for ( const k of [ 'map', 'roughnessMap', 'metalnessMap', 'normalMap', 'aoMap', 'emissiveMap' ] ) {
				if ( m[ k ] && m[ k ].channel < 0 ) { m[ k ].channel = 0; note( `${m.name}: ${k} texCoord < 0 clamped to 0 (export defect)` ); }
			}
			// schema pfa-phase6-gate0/1 and /2 ship any lightmap INSIDE the glb as the emissiveTexture
			// on TEXCOORD_1 (RGBM8).  Move it to lightMap channel 1, kill the emissive, decode RGBM.
			// An in-glb emissive lightmap always wins: it must never be left live as emissive.
			let lm = m.emissiveMap ? null : matchLightmap( o, m );
			if ( m.emissiveMap ) {
				if ( lightingMode === 'direct' ) note( `material ${m.name}: emissiveTexture found although the manifest declares no lightmap — treated as a lightmap` );
				lm = { encoding: 'rgbm', rgbmMaxRange: manifest.rgbmRange, intensity: lightmapScale, fromEmissive: true };
				m.lightMap = m.emissiveMap;
				// GLTFLoader tags an emissiveTexture as sRGB (glTF requires it), but the RGBM8 lightmap
				// is LINEAR data: leaving it as sRGB would put a decode curve on the baked irradiance.
				m.lightMap.colorSpace = THREE.NoColorSpace;
				m.lightMap.needsUpdate = true;
				m.lightMap.channel = 1;
				m.lightMapIntensity = lightmapScale;
				m.emissiveMap = null;
				m.emissive = new THREE.Color( 0, 0, 0 );
				m.emissiveIntensity = 0;
				lightmapsApplied ++;
			}
			if ( lm ) {
				patchBakedMaterial( m, { lightMapEncoding: lm.encoding, rgbmMaxRange: lm.rgbmMaxRange } );
				patchedMaterials ++;
				lightmapMaterials.push( m );
				if ( ! lm.fromEmissive ) applyLightmap( m, lm );
			} else {
				unpatchedMaterials.add( m.name || '(unnamed)' );
				noLightmapMaterials.push( m );
			}
		}
	} );
	return { name: g.name, cls: g.cls, url: g.url, meshes, instancedMeshes, instances, tris, materials, hiddenBoards };
}

/** What to do with materials that have no lightmap, once every glb is in. */
function finishMaterials() {
	if ( lightingMode === 'direct' ) {
		note( `${noLightmapMaterials.length} material(s) on three's own lighting (Gate 1 has no lightmap bake); `
			+ `${patchedMaterials} on the baked path` );
		return;
	}
	// Gate 3 (manifest v4) bakes a map for everything that should have one, so a material without one
	// is meant to have none (foliage, shrubs, impostors, the backdrop).  It stays on three's own
	// lighting, whose diffuse irradiance now comes from `sky.diffuse` — never from a neighbour's map.
	if ( manifest.gate3 ) {
		const withMap = noLightmapMaterials.filter( m => m.lightMap ).length;
		note( `${noLightmapMaterials.length - withMap} material(s) with no Gate 3 lightmap stay on the environment path `
			+ `(diffuse irradiance from sky.diffuse); the Gate 0 "borrow a neighbour's lightmap" stand-in is off at Gate 3` );
		assignSpecularEnv();
		return;
	}
	// Gate 0 bakes a lightmap for ONE of the 16 columns; the other 15 share the mesh with a
	// lightmap-free material.  Under a specular-only sun they would be black, under stock lighting
	// they blow out (sun 67.3 W/m2, no tone mapping), so by default they borrow the lit column's
	// lightmap (same mesh, same UV2, baked at column 00's position): an explicit Gate 0 stand-in.
	if ( noLightmapMaterials.length && lightmapMaterials.length ) {
		// Pick the donor by name similarity: GATE0_column must borrow GATE0_column_lit's lightmap,
		// never the capital's (a different UV2 layout would sample near-black texels).
		const similarity = ( a, b ) => { let i = 0; while ( i < a.length && i < b.length && a[ i ] === b[ i ] ) i ++; return i; };
		const donorFor = ( m ) => lightmapMaterials.filter( d => d.lightMap )
			.sort( ( x, y ) => similarity( y.name || '', m.name || '' ) - similarity( x.name || '', m.name || '' ) )[ 0 ];
		const donor = donorFor( noLightmapMaterials[ 0 ] );
		if ( CFG.unlit === 'share' && donor ) {
			for ( const m of noLightmapMaterials ) {
				const d = donorFor( m ) || donor;
				m.lightMap = d.lightMap; m.lightMapIntensity = d.lightMapIntensity;
				patchedMaterials ++;
				patchBakedMaterial( m, { lightMapEncoding: 'rgbm', rgbmMaxRange: manifest.rgbmRange } );
				m.needsUpdate = true;
			}
			note( `${noLightmapMaterials.length} lightmap-free material(s) borrow the nearest-named lightmap (${noLightmapMaterials.map( m => `${m.name} <- ${( donorFor( m ) || donor ).name}` ).join( ', ' )}; Gate 0 stand-in, Gate 3 bakes their own)` );
		} else if ( CFG.unlit === 'black' ) {
			for ( const m of noLightmapMaterials ) patchBakedMaterial( m, {} );
			note( `${noLightmapMaterials.length} lightmap-free material(s) left specular-only (they render black)` );
		} else {
			note( `${noLightmapMaterials.length} lightmap-free material(s) left on stock three lighting` );
		}
	}
	const stillStock = noLightmapMaterials.filter( m => ! m.lightMap ).map( m => m.name || '(unnamed)' );
	note( `${patchedMaterials} materials patched (specular-only sun), ${stillStock.length} left on stock lighting: ${stillStock.join( ', ' ) || 'none'}` );
}

function matchLightmap( obj, mat ) {
	// gltfpack puts each mesh on an unnamed child node, so the manifest's object name is usually on
	// the PARENT; material name and both node names are all accepted.
	const names = [ mat.name, obj.name, obj.parent?.name, obj.parent?.parent?.name ].filter( Boolean );
	for ( const lm of manifest.lightmaps ) {
		if ( ! lm.match ) continue;
		const want = lm.matchKind === 'material' ? [ mat.name ].filter( Boolean ) : names;
		if ( want.some( n => n === lm.match || n.startsWith( lm.match ) ) ) return lm;
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
		progress.label = url.split( '/' ).pop();
		// Carry 11a: LUTCubeLoader defaults to UnsignedByteType, which quantizes a 65^3 LUT behind a
		// log2 shaper at the shadow end (1/255 of the shaper range is ~0.065 EV down there).  Float
		// texels need OES_texture_float_linear for the trilinear fetch; WebGL2 has no linear float
		// filtering without it, so fall back to 8-bit rather than render a nearest-sampled LUT.
		const hasExt = !! renderer.getContext().getExtension( 'OES_texture_float_linear' );
		const floatLinear = hasExt && CFG.lutFloat;
		const cubeLoader = new LUTCubeLoader( manager );
		if ( floatLinear ) cubeLoader.setType( THREE.FloatType );
		note( `LUT texel type ${floatLinear ? 'FloatType (OES_texture_float_linear)' : 'UnsignedByte'}`
			+ ` — extension ${hasExt ? 'present' : 'ABSENT'}${! CFG.lutFloat ? ', forced 8-bit by ?lutfloat=0' : ''}` );
		const lut = url.endsWith( '.cube' )
			? await cubeLoader.loadAsync( url, onProgressFor( url ) )
			: await new LUTImageLoader( manager ).loadAsync( url, onProgressFor( url ) );
		const res = lut.texture3D ? lut : { texture3D: lut.texture3D || lut, size: lut.size };
		res.shaper = manifest.lut.shaper; res.shaperMin = manifest.lut.shaperMin; res.shaperMax = manifest.lut.shaperMax;
		res.shaperPivot = manifest.lut.shaperPivot;
		lutPass.setLUT( res );
		note( `LUT ${url.split( '/' ).pop()} size ${lutPass.uniforms.lutSize.value}${res.shaper ? ` shaper ${res.shaper} [${res.shaperMin}, ${res.shaperMax}] pivot ${lutPass.uniforms.shaperPivot.value}` : ` domain [${lutPass.uniforms.domainMin.value.toArray()}, ${lutPass.uniforms.domainMax.value.toArray()}]`}` );
	} catch ( e ) { note( `LUT load failed (${e.message}); gamma 2.2 fallback` ); lutPass.setLUT( null ); }
}

// ---------------------------------------------------------------------------- stations
function applyStation( n ) {
	const st = stations.find( s => s.index === n ) || stations[ 0 ];
	camera = makeStationCamera( st, camera.aspect || 16 / 9, camera );
	camera.layers.enableAll();             // item 6: the reflection-excluded layer still draws here
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

let controls = null, walk = null;
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
	// Walk mode (Gate 4 item 5): WASD takes over from OrbitControls, eye height 1.7 m on the ground,
	// out of the lagoon, out of the columns.  It builds its grids on the FIRST walk key, never at
	// load, and refuses to start before __pfaReady - a capture sends no input and so never walks.
	walk = makeWalk( () => camera, renderer.domElement, scene, {
		waterY: manifest.waterZ, note,
		onStart: () => { userControlled = true; if ( controls ) controls.enabled = false; },
	} );
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

const _lastCamPos = new THREE.Vector3( Infinity, Infinity, Infinity );
function renderFrame() {
	if ( billboards && camera.position.distanceToSquared( _lastCamPos ) > 1e-6 ) {
		aimBillboards( billboards, camera );
		_lastCamPos.copy( camera.position );
	}
	if ( water ) water.userData.tick( CFG.time !== null ? CFG.time : elapsed() );
	renderer.info.autoReset = false;          // otherwise info shows only the last composer pass
	renderer.info.reset();
	if ( composer ) composer.render(); else renderer.render( scene, camera );
}

/** True while __pfaFrameStats owns the frame loop: animate() must not render a SECOND time per
 *  tick, or the reported median presented frame time is up to 2x the real one. */
let measuring = false;
function animate() {
	requestAnimationFrame( animate );
	if ( measuring ) return;
	if ( walk && walk.state.active ) walk.tick();
	else if ( userControlled && controls ) controls.update();
	renderFrame();
}

// ---------------------------------------------------------------------------- test hooks
window.__pfaReady = false;
window.__pfaStation = ( n ) => { applyStation( n ); resize(); renderFrame(); return currentStation.name; };
// Gate 4 item 5: drive the walker from the harness without input, pointer lock or a rendered frame.
window.__pfaWalkProbe = ( o ) => ( walk ? walk.probe( o || {} ) : null );

/**
 * Gate 4 item 2: orbit the camera around a world point, for the impostor rotational-pop sweep.
 * An impostor picks its frame from the world-space view DIRECTION, so a pop can only be seen by
 * rotating around one; the six fixed stations cannot show it.  Angles are degrees clockwise from
 * world -Z, matching the walk probe's heading convention.
 */
window.__pfaOrbit = ( { target, dist = 30, headingDeg = 0, height = 12, fov = 40 } ) => {
	const t = new THREE.Vector3( ...target );
	const h = headingDeg * Math.PI / 180;
	camera = new THREE.PerspectiveCamera( fov, camera.aspect || 16 / 9, 0.1, 5000 );
	camera.layers.enableAll();             // or ?reflset=orn leaves every ORN mesh (layer 2) invisible
	camera.position.set( t.x + Math.sin( h ) * dist, t.y + height, t.z + Math.cos( h ) * dist );
	camera.lookAt( t );
	camera.updateMatrixWorld( true );
	currentStation = { index: 0, name: `orbit_${headingDeg}`, lens: null, shift_y: 0 };
	userControlled = false;
	if ( composer ) composer.passes[ 0 ].camera = camera;
	renderFrame();
	return { headingDeg, position: camera.position.toArray().map( v => + v.toFixed( 2 ) ), target: t.toArray() };
};
window.__pfaInfo = () => ( {
	station: currentStation && { index: currentStation.index, name: currentStation.name, lens: currentStation.lens, shift_y: currentStation.shift_y },
	cameraWorldMatrix: camera.matrixWorld.elements.slice(),
	projectionMatrix: camera.projectionMatrix.elements.slice(),
	fovVertical: camera.fov, aspect: camera.aspect,
	size: [ renderer.domElement.width, renderer.domElement.height ],
	render: { ...renderer.info.render, programs: renderer.info.programs ? renderer.info.programs.length : null },
	memory: { ...renderer.info.memory },
	gl: glInfo(),
	patchedMaterials, lightmapsApplied, unpatchedMaterials: [ ...unpatchedMaterials ],
	lightmapScale, rgbmRange: manifest ? manifest.rgbmRange : null,
	gate3: gate3Report && { own: gate3Report.own, slots: gate3Report.slots,
		materialsCloned: gate3Report.materialsCloned, texturesRequested: gate3Report.texturesRequested,
		texturesLoaded: gate3Report.texturesLoaded, texturesFailed: gate3Report.texturesFailed },
	skyDiffuse: manifest ? !! manifest.sky.diffuse : null,
	shaperPivot: lutPass ? lutPass.uniforms.shaperPivot.value : null,
	skyRotationDeg: manifest ? manifest.sky.rotationDeg : null,
	exposure: lutPass ? lutPass.uniforms.exposure.value : null,
	lutEnabled: lutPass ? !! lutPass.uniforms.lutEnabled.value : false,
	lutSize: lutPass ? lutPass.uniforms.lutSize.value : 0,
	waterZ: manifest ? manifest.waterZ : null,
	lightingMode,
	schema: manifest ? manifest.schema : null,
	bytes: { loaded: progress.loaded, planned: progress.total, unknownSize: progress.unknown.slice(),
		files: progress.files.map( f => ( { kind: f.kind, bytes: f.bytes, sizeFrom: f.sizeFrom, name: f.url.split( '/' ).pop() } ) ) },
	load_s: { ...loadTimes },
	glbs: glbReport.slice(),
	uv_dequant: uvDequantReport.slice(),
	resident: residentBytes(),
	billboards: billboards ? { ...billboards.userData } : null,
	chunking: chunkStats,
	post: postState,
	probeEnv: probeReport,
	reflectionSet,
	quality: { preset: CFG.quality, bloomRes: CFG.bloomRes, reflRes: CFG.reflRes, reflSet: CFG.reflSet },
	impostors: impostorReport && { prototypes: impostorReport.prototypes, instances: impostorReport.instances,
		drawCalls: impostorReport.drawCalls, textures: impostorReport.textures, bytes: impostorReport.bytes,
		skipped: impostorReport.skipped.length, missingPrototypes: impostorReport.missingPrototypes },
	walk: walk ? { ...walk.state } : null,
	materialsMode,
	pbr: pbrReport,
	detail: detailReport,
	notes: log.slice(),
} );

/** Resident GPU-side bytes we can account for: unique geometries and unique textures in the scene.
 *  renderer.info.memory only counts objects, so this is the viewer's own sum, stated as an estimate:
 *  compressed textures are summed from their mip data, uncompressed ones as w*h*4*(4/3 with mips). */
function residentBytes() {
	const geos = new Set(), texs = new Set();
	let geometry = 0, texture = 0, instanceMatrices = 0;
	const formats = {};
	const addTex = ( t ) => {
		if ( ! t || texs.has( t ) ) return;
		texs.add( t );
		const f = formatName( t );
		formats[ f ] = ( formats[ f ] || 0 ) + 1;
		if ( t.mipmaps && t.mipmaps.length && t.mipmaps[ 0 ].data ) {
			for ( const m of t.mipmaps ) texture += m.data.byteLength;       // compressed (KTX2)
		} else if ( t.image && t.image.width ) {
			const bpp = ( t.type === THREE.FloatType ) ? 16 : ( t.type === THREE.HalfFloatType ? 8 : 4 );
			texture += t.image.width * t.image.height * bpp * ( t.generateMipmaps ? 4 / 3 : 1 );
		}
	};
	scene.traverse( ( o ) => {
		if ( ! o.isMesh ) return;
		if ( ! geos.has( o.geometry ) ) {
			geos.add( o.geometry );
			for ( const a of Object.values( o.geometry.attributes ) ) geometry += a.array.byteLength;
			if ( o.geometry.index ) geometry += o.geometry.index.array.byteLength;
		}
		if ( o.isInstancedMesh ) instanceMatrices += o.instanceMatrix.array.byteLength;
		for ( const m of ( Array.isArray( o.material ) ? o.material : [ o.material ] ) ) {
			if ( ! m ) continue;
			for ( const k of [ 'map', 'lightMap', 'aoMap', 'normalMap', 'roughnessMap', 'metalnessMap', 'emissiveMap', 'alphaMap' ] ) addTex( m[ k ] );
			// the detail layer's maps are custom uniforms, not material slots, but they are resident
			if ( m.userData.pfaDetailTextures ) for ( const t of m.userData.pfaDetailTextures ) addTex( t );
		}
	} );
	if ( scene.background && scene.background.isTexture ) addTex( scene.background );
	// scene.environment IS pmremTarget.texture and has an image, so addTex would bill the cubeUV
	// here AND addRT would bill the identical bytes below (review finding 1): count it once, as a
	// render target.
	const pmremTextures = [ pmremTarget, diffusePmremTarget ].filter( Boolean ).map( t => t.texture );
	if ( scene.environment && ! pmremTextures.includes( scene.environment ) ) addTex( scene.environment );
	// Render targets dominate the GPU-memory figure at 1440p and carry no `image`, so addTex() sees
	// nothing: count them explicitly.  A HalfFloat RGBA target is 8 B/px, and three allocates an extra
	// multisampled renderbuffer of samples x that size when `samples` > 0.
	const rts = [];
	const addRT = ( rt, what ) => {
		if ( ! rt ) return;
		const w = rt.width, h = rt.height, n = rt.samples || 0;
		const bpp = rt.texture && rt.texture.type === THREE.FloatType ? 16
			: ( rt.texture && rt.texture.type === THREE.HalfFloatType ? 8 : 4 );
		rts.push( { what, size: [ w, h ], samples: n, bytes: Math.round( w * h * bpp * ( 1 + n ) ) } );
	};
	if ( composer ) { addRT( composer.renderTarget1, 'composer.renderTarget1' ); addRT( composer.renderTarget2, 'composer.renderTarget2' ); }
	if ( water && water.getRenderTarget ) addRT( water.getRenderTarget(), 'water.Reflector' );
	if ( pmremTarget ) addRT( pmremTarget, 'PMREM cubeUV (glossy, specular)' );
	if ( diffusePmremTarget ) addRT( diffusePmremTarget, 'PMREM cubeUV (diffuse, irradiance)' );
	const rtBytes = rts.reduce( ( a, r ) => a + r.bytes, 0 );
	return {
		geometry_bytes: Math.round( geometry ), instance_matrix_bytes: Math.round( instanceMatrices ),
		texture_bytes: Math.round( texture ), geometries: geos.size, textures: texs.size, texture_formats: formats,
		render_target_bytes: rtBytes, render_targets: rts,
		total_bytes: Math.round( geometry + instanceMatrices + texture ) + rtBytes,
		note: 'viewer-side sum; compressed textures from their mip data, uncompressed as w*h*4 (x4/3 with '
			+ 'mipmaps), render targets as w*h*bpp*(1+samples) for the resolve plus the multisample buffer',
	};
}
window.__pfaFrameStats = ( n = 120 ) => new Promise( ( resolve ) => {
	const t = [];
	let last = performance.now();
	measuring = true;                     // animate() stands down for the duration
	const step = () => {
		renderFrame();
		const now = performance.now();
		t.push( now - last ); last = now;
		if ( t.length < n ) requestAnimationFrame( step );
		else {
			measuring = false;
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
/**
 * Item 6: WHERE the presented frame time goes.  At 1440p the GPU does 0.6-2.4 ms of work
 * (gl.finish) while the presented frame sits at 16.6-25.8 ms, so the cost is not in the draw.  This
 * splits each presented frame into
 *   js_ms    the CPU inside renderFrame(): three's matrix/frustum/uniform work and the DRAW SUBMIT,
 *            with no gl.finish, so it is the cost of BUILDING the frame, not of drawing it;
 *   gap_ms   from the end of renderFrame() to the next rAF callback: vsync wait plus whatever the
 *            browser's compositor does with the presented buffer.
 * and reports the passes and render targets that could be driving it - the water Reflector renders
 * the whole scene a second time, and the composer adds a full-screen pass per effect.
 */
window.__pfaFrameBreakdown = ( n = 120 ) => new Promise( ( resolve ) => {
	const js = [], gap = [];
	let last = performance.now();
	measuring = true;
	const step = () => {
		const a = performance.now();
		renderFrame();
		const b = performance.now();
		js.push( b - a );
		gap.push( a - last );              // time since the previous frame's renderFrame START
		last = a;
		if ( js.length < n ) requestAnimationFrame( step );
		else {
			measuring = false;
			const q = ( arr ) => { const s = arr.slice( 1 ).sort( ( x, y ) => x - y );
				return { median: s[ Math.floor( s.length / 2 ) ], mean: s.reduce( ( x, y ) => x + y, 0 ) / s.length,
					p95: s[ Math.floor( s.length * 0.95 ) ], min: s[ 0 ], max: s[ s.length - 1 ] }; };
			const passes = composer ? composer.passes.map( ( p ) => p.name || p.constructor.name ) : [];
			resolve( {
				frames: js.length - 1,
				js_ms: q( js ), presented_ms: q( gap ),
				composerPasses: passes,
				waterReflector: !! ( water && water.getRenderTarget ),
				drawCalls: renderer.info.render.calls, triangles: renderer.info.render.triangles,
				programs: renderer.info.programs ? renderer.info.programs.length : null,
				geometries: renderer.info.memory.geometries, textures: renderer.info.memory.textures,
				devicePixelRatio: renderer.getPixelRatio(),
				drawingBuffer: [ renderer.domElement.width, renderer.domElement.height ],
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
		const matName = Array.isArray( o.material ) ? o.material.map( m => m?.name ).join( ',' ) : ( o.material?.name || '' );
		if ( ! o.isMesh || ! ( o.name.includes( needle ) || matName.includes( needle ) ) ) return;
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

/** Every render-visible mesh with its material and triangle count (probe/ROI naming). */
window.__pfaNames = () => {
	const out = [];
	scene.traverse( ( o ) => {
		if ( ! o.isMesh ) return;
		const g = o.geometry, n = g.index ? g.index.count : g.attributes.position.count;
		out.push( { name: o.name, material: Array.isArray( o.material ) ? o.material.map( m => m.name ) : o.material?.name,
			tris: n / 3, instances: o.isInstancedMesh ? o.count : 1, lightMap: !! ( o.material && o.material.lightMap ) } );
	} );
	return out;
};

/** Read back the linear pixel at the centre of a named object (LUT / luminance probes). */
/**
 * QA pick: what is UNDER a pixel.  `gltfpack -mi` drops every name, so the identity comes from the
 * same world-bbox-centre join the lightmap pass uses, and everything that decides how the surface is
 * lit is reported beside it: the material, whether it carries UV2, whether a lightmap actually
 * attached, whether the environment still reaches it, and what the baked-material patch did.
 * That is the whole question "which side owns this pixel", answered without changing anything.
 */
window.__pfaPick = ( x, y ) => {
	const { w, h } = canvasSize();
	const ndc = new THREE.Vector2( ( x / w ) * 2 - 1, - ( y / h ) * 2 + 1 );
	const rc = new THREE.Raycaster();
	rc.layers.enableAll();                 // ORN is on layer 2 under ?reflset=orn; a default mask misses it
	rc.setFromCamera( ndc, camera );
	rc.firstHitOnly = true;
	// three's Raycaster does NOT skip invisible objects, so a hidden placeholder (?treeboards=0) would
	// be reported as the thing under the pixel when it is not drawn at all.  Filter them out.
	const visibleUp = ( o ) => { let p = o; while ( p ) { if ( p.visible === false ) return false; p = p.parent; } return true; };
	const hits = rc.intersectObjects( scene.children, true ).filter( ( h ) => visibleUp( h.object ) );
	const out = [];
	for ( const hit of hits.slice( 0, 4 ) ) {
		const o = hit.object;
		const m = Array.isArray( o.material ) ? o.material[ 0 ] : o.material;
		const g = o.geometry;
		const box = new THREE.Box3().setFromObject( o );
		const c = box.getCenter( new THREE.Vector3() );
		// nearest manifest asset to the mesh centre, the same identity the lightmap join uses
		let near = null, nearD = Infinity;
		const assets = manifest && manifest.assets;
		for ( const name in ( assets || {} ) ) {
			const loc = assets[ name ] && assets[ name ].location_blender;
			if ( ! Array.isArray( loc ) ) continue;
			const p = b2t( loc[ 0 ], loc[ 1 ], loc[ 2 ] );
			const d = p.distanceTo( c );
			if ( d < nearD ) { nearD = d; near = name; }
		}
		// The sun term, decomposed: three's Lambert is irradiance * NdotL * albedo/pi, so a surface
		// whose normal faces away from the sun gets NOTHING from it however bright the sun is, and the
		// blue sky is then all the light it has.  Reported so "the sun is not reaching it" is a number.
		let nWorld = null, ndotl = null;
		if ( hit.normal ) {
			nWorld = hit.normal.clone().transformDirection( o.matrixWorld ).normalize();
			if ( sunLight ) {
				const L = sunLight.position.clone().normalize();
				ndotl = nWorld.dot( L );
			}
		}
		out.push( {
			distance_m: + hit.distance.toFixed( 2 ),
			worldNormal: nWorld ? nWorld.toArray().map( v => + v.toFixed( 3 ) ) : null,
			NdotL_sun: ndotl === null ? null : + ndotl.toFixed( 4 ),
			sunReaches: ndotl === null ? null : ndotl > 0,
			materialSide: m ? ( m.side === THREE.DoubleSide ? 'double' : m.side === THREE.BackSide ? 'back' : 'front' ) : null,
			flatShading: m ? !! m.flatShading : null,
			hasNormalAttr: !! ( g && g.attributes.normal ),
			alphaMode: m ? { transparent: !! m.transparent, alphaTest: m.alphaTest ?? 0 } : null,
			point: hit.point.toArray().map( v => + v.toFixed( 2 ) ),
			mesh: o.name || '(unnamed - gltfpack -mi)',
			root: ( () => { let p = o; while ( p && ! /^WEB_glb_|^WEB_/.test( p.name || '' ) ) p = p.parent; return p ? p.name : null; } )(),
			instanced: !! o.isInstancedMesh, instanceCount: o.isInstancedMesh ? o.count : 1,
			instanceId: hit.instanceId ?? null,
			bboxCentre: c.toArray().map( v => + v.toFixed( 2 ) ),
			nearestAsset: near, nearestAsset_m: + nearD.toFixed( 3 ),
			material: m ? m.name : null,
			materialType: m ? m.type : null,
			hasUv1: !! ( g && g.attributes.uv1 ),
			hasColor0: !! ( g && g.attributes.color ),
			hasSlotAttr: !! ( g && g.attributes.pfaSlot ),
			lightMap: m && m.lightMap ? ( m.lightMap.name || m.lightMap.source?.data?.src || 'yes' ) : null,
			lightMapIntensity: m ? m.lightMapIntensity : null,
			map: m && m.map ? ( m.map.name || 'yes' ) : null,
			colorFactor: m && m.color ? m.color.toArray().map( v => + v.toFixed( 4 ) ) : null,
			envMap: !! ( m && m.envMap ),
			sceneEnvironment: !! scene.environment,
			pfaPatched: m ? ( m.userData.pfaPatched || null ) : null,
			vertexColors: m ? !! m.vertexColors : null,
			visible: o.visible, renderOrder: o.renderOrder,
			userData: o.userData && Object.keys( o.userData ).length ? o.userData : null,
		} );
	}
	return { x, y, size: [ w, h ], pixel: window.__pfaPixel( x, y ), hits: out.length, under: out };
};

window.__pfaPixel = ( x, y ) => {
	const gl = renderer.getContext();
	const px = new Uint8Array( 4 );
	gl.readPixels( x, renderer.domElement.height - 1 - y, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px );
	return Array.from( px );
};

boot().catch( ( e ) => { note( `boot failed: ${e.stack}` ); uiText.textContent = `failed: ${e.message}`; window.__pfaError = String( e.stack ); } );
