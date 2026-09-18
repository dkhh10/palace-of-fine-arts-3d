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
import { normaliseManifest, applyUv2RelayStatus, tierForUrl, WATER_Z } from './manifest.js';
import { probeGl, probeEnv, chooseTier, pixelRatioFor, TIER_SETTINGS } from './device.js';
import { patchBakedMaterial, attachLightMap } from './materials.js';
import { LUTDisplayPass, makeLUT } from './lutPass.js';
import { makeWater, reduceReflectionSet } from './water.js';
import { makeWalk } from './walk.js';
import { readCompositor, applyMist, removeMist, makeBloom, parsePost, MIST_NEAR_M, MIST_FAR_M, BLOOM_THRESHOLD_SCALE } from './postChain.js';
import { buildTestScene } from './testScene.js';
import { makeTreeBillboards, aimBillboards } from './billboards.js';
import { buildImpostors } from './impostors.js';
import { applyFoliage, applyShrubLod, nearTreeImpostorEntries, equirectIntegral, farTreeIrradiance,
	keepMeshAlways, shaderErrors } from './foliage.js';
import { loadFarTrees, loadShrubLod1, loadFarTreeLighting, prototypeEbake, applyFoliageTextures,
	markShrubLodRows } from './foliageLazy.js';
import { buildProbeEnv, applyProbeEnv } from './probeEnv.js';
import { chunkInstancedMeshes } from './chunking.js';
import { applyPbrSets, upgradePbrSets, upgradeGlbTextures, pbrPlan, formatName, texBytes, collectTextures, disposeOrphans } from './pbr.js';
import { applyDetail } from './detail.js';
import { applyGate3Lightmaps } from './lightmaps.js';

const qs = new URLSearchParams( location.search );
// ?quality is compared ONCE, lowercased, and an unknown value is rejected rather than echoed as a
// preset name: ?quality=FAST used to report 'fast' and silently run the full-res chain.
const QUALITY_RAW = ( qs.get( 'quality' ) || 'look' ).toLowerCase();
const QUALITY = ( QUALITY_RAW === 'fast' || QUALITY_RAW === 'look' ) ? QUALITY_RAW : 'look';
const CFG = {
	station: parseInt( qs.get( 'station' ) || '1', 10 ),
	manifestUrl: qs.get( 'manifest' ) || '/assets/gate3/manifest.json',   // delivery default (6a); ?manifest=/assets/gate0/manifest.json for the Gate 0 slice
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
	billboards: qs.get( 'billboards' ) === '1',         // far-tree placeholder quads (dev only; off by default since 6a, impostors replace them)
	impostors: qs.get( 'impostors' ) !== '0',           // Gate 3 octahedral far-tree impostors
	impNormalDepth: qs.get( 'impnd' ) === '1',          // also load the normal+depth atlases
	impDebug: parseInt( qs.get( 'impdebug' ) || '0', 10 ),   // 1 raw, 2 alpha, 3 frame cell, 4 quad uv
	probeEnv: qs.get( 'probe' ) !== '0',                // baked hero probe as the irradiance of unlit surfaces
	probeSpec: qs.get( 'probespec' ) === '1',           // A/B: probe as the SPECULAR env of baked materials
	treeboards: qs.get( 'treeboards' ) === '1',         // the export's own ENV_treeboard_* stand-ins inside env.glb (QA 11b; off by default since 6a)
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
	vertexIrr: qs.get( 'vertexirr' ) || 'auto',
	instIrr: qs.get( 'instirr' ) || 'auto',             // per-placement shrub/reed irradiance: auto | 0
	// 6c round 3: the exponent on the per-placement cov correction (0 = the shipped rgb, 1 = mean_all)
	shrubCov: qs.has( 'shrubcov' ) ? parseFloat( qs.get( 'shrubcov' ) ) : undefined,
	// Phase 6c item C — the foliage pass.  `treemesh` is metres from the walker: inside it a tree
	// draws its mesh, beyond it its impostor, with `treefade` metres of dissolve between.  `inf`
	// (or `never`) keeps every mesh for ever and creates no near-tree impostor at all, which is the
	// round-15 behaviour and therefore the A/B for anything this pass changes at range.
	// Every numeric switch below is guarded in applyFoliage (Number.isFinite + a clamp): a typo must
	// fall back to the default, never reach smoothstep as NaN and erase the canopy (round-1 review 3).
	leafNormal: qs.has( 'leafnormal' ) ? parseFloat( qs.get( 'leafnormal' ) ) : 0.5,
	cardNormal: qs.has( 'cardnormal' ) ? parseFloat( qs.get( 'cardnormal' ) ) : 0,   // the shrub/reed cards' bend
	// 6c round 3 — the crown interior (QA 16 open 2).  `crownint` / `cardint` are
	// "str[,low[,gamma[,gain[,trn]]]]" over foliage.js' CROWN_INTERIOR / CARD_INTERIOR ("0" = off,
	// "1" = the default), `leafgate` the radius above which the crown-bent normal fades in (0 =
	// round-16b, bend everywhere), `impint` the same interior on the ATLAS crowns: "str[,radiusUV]".
	crownInt: qs.get( 'crownint' ),
	cardInt: qs.get( 'cardint' ),
	leafGate: qs.has( 'leafgate' ) ? parseFloat( qs.get( 'leafgate' ) ) : undefined,
	impInt: qs.get( 'impint' ),
	foliageBias: qs.get( 'foliagebias' ),   // LOD bias on the cut-out fetch: "card[,leaf]"
	leafTrn: qs.get( 'leaftrn' ),                       // scale, or "shrubs" to include the cards
	leafSoft: qs.get( 'leafsoft' ) !== '0',             // alphaToCoverage on the MASK cutoffs
	treeMesh: qs.get( 'treemesh' ),                     // metres | inf | never  (default 40)
	treeFade: qs.has( 'treefade' ) ? parseFloat( qs.get( 'treefade' ) ) : 5,
	imp2k: qs.get( 'imp2k' ) !== '0',                   // the 2K impostor atlas variant on desktop
	// undefined = "not asked", so the manifest's own dist_m still wins; an explicit value always does
	shrubLod: qs.has( 'shrublod' ) ? parseFloat( qs.get( 'shrublod' ) ) : undefined,   // LOD1 within this many metres
	// 6c round 2, the two lazily loaded glbs and the foliage material textures
	farTreeLight: ( qs.get( 'fartreelight' ) || 'near' ).toLowerCase(),   // near | probe | 0
	shrubEnv: qs.has( 'shrubenv' ) ? parseFloat( qs.get( 'shrubenv' ) ) : undefined,  // env term on the LOD1 shrubs
	cardEnv: qs.has( 'cardenv' ) ? parseFloat( qs.get( 'cardenv' ) ) : undefined,     // the same on the LOD2 cards
	farTrn: qs.has( 'fartrn' ) ? parseFloat( qs.get( 'fartrn' ) ) : undefined,  // translucency on the far-tree meshes
	farAo: qs.has( 'farao' ) ? parseFloat( qs.get( 'farao' ) ) : 1,   // how much of the env term the AO occludes
	farTreeMesh: qs.has( 'fartreemesh' ) ? parseFloat( qs.get( 'fartreemesh' ) ) : undefined,  // the far trees' own switch distance
	// 6c round 3 item 3: the walk-up LOD1 tree set (trees.walkup_mesh).  A distance in metres is the
	// switch distance, "0" / "off" forces the LOD2 set back for the A/B, absent = 15 m when the
	// manifest carries the block and the LOD2 set when it does not.
	walkupMesh: qs.get( 'walkupmesh' ),
	foliageTex: qs.get( 'foliagetex' ) || '1024',                         // 1024 | 2048 | 0
	// The impostor atlases were baked with each prototype ALONE under the open sky, so their light is
	// the sky's.  `impmod` re-lights each placement by E_placement / E_bake: `chroma` (the default)
	// corrects the COLOUR only, `full` the level too (only honest once E_bake is measured, which the
	// bake ships per prototype), `0` draws the atlas as baked.  `impbake=r,g,b` overrides E_bake.
	// null = not asked: `full` becomes the default the day the bake's per-prototype E_bake is in the
	// manifest, `chroma` until then (the lead's rule, docs/decisions.md 2026-09-17).
	impMod: qs.has( 'impmod' ) ? String( qs.get( 'impmod' ) ).toLowerCase() : null,
	impBake: qs.get( 'impbake' ),
	post: qs.get( 'post' ) || 'all',                  // all | none | mist,bloom,vignette (default all since 6a: the Phase 5 compositor look)
	bloomThreshold: qs.has( 'bloomthr' ) ? parseFloat( qs.get( 'bloomthr' ) ) : null,  // scene-linear
	bloomRadius: qs.has( 'bloomrad' ) ? parseFloat( qs.get( 'bloomrad' ) ) : null,     // UnrealBloomPass radius
	mist: qs.get( 'mist' ),                             // near,far in metres (the manifest carries neither)
	// Phase 6b.  `?tier=` picks the ASSET SET (desktop | mobile | auto, default auto = the device
	// probe in src/device.js).  `?tiers=` is the other axis: how many LOAD TIERS of that set to fetch
	// — `all` (the default) streams every one after the first frame, `0` boots tier 0 and stops there,
	// `1` stops after tier 1.  A manifest with no `tiers` block has one tier and both are no-ops.
	deviceTier: ( qs.get( 'tier' ) || 'auto' ).toLowerCase(),
	tiers: ( qs.get( 'tiers' ) || 'all' ).toLowerCase(),
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
renderer.setPixelRatio( 1 );                            // deterministic screenshots (the mobile tier raises it below)
renderer.toneMapping = THREE.NoToneMapping;             // the LUT pass IS the display transform
renderer.outputColorSpace = THREE.SRGBColorSpace;
container.appendChild( renderer.domElement );

// ---------------------------------------------------------------------------- device tier (6b)
// Decided BEFORE the composer exists, because EffectComposer captures the renderer's pixel ratio at
// construction: a ratio set afterwards would size the canvas and leave every render target at the old
// one.  Everything the choice was made from is kept for the boot log and __pfaInfo().device.
const DEVICE = ( () => {
	const gl = probeGl( renderer ), env = probeEnv();
	const choice = chooseTier( { gl, env, query: CFG.deviceTier } );
	return { ...choice, gl, env, settings: TIER_SETTINGS[ choice.tier ] || TIER_SETTINGS.desktop };
} )();
const MOBILE = DEVICE.tier === 'mobile';
note( `device tier: ${DEVICE.tier} (${DEVICE.from}) — ${DEVICE.reasons.join( '; ' )}; `
	+ `gl ${DEVICE.gl.renderer || '?'}, max texture ${DEVICE.gl.maxTextureSize}, `
	+ `astc ${DEVICE.gl.astc} etc2 ${DEVICE.gl.etc2} s3tc ${DEVICE.gl.s3tc} bptc ${DEVICE.gl.bptc}, `
	+ `dpr ${DEVICE.env.devicePixelRatio}, screen ${DEVICE.env.screen.join( 'x' )}, touch ${DEVICE.env.maxTouchPoints}` );
// The mobile tier's render settings, applied ONLY where the url asked for nothing: an explicit
// ?post= / ?treemesh= / ?shrublod= still wins, so every A/B keeps working on a phone.
if ( MOBILE ) {
	const s = DEVICE.settings, took = [];
	const set = ( key, cfgKey, value ) => { if ( ! qs.has( key ) && value !== null && value !== undefined ) { CFG[ cfgKey ] = value; took.push( `${cfgKey}=${value}` ); } };
	set( 'post', 'post', s.post );
	set( 'treemesh', 'treeMesh', s.treeMesh );
	set( 'fartreelight', 'farTreeLight', s.farTreeLight );
	set( 'shrublod', 'shrubLod', s.shrubLod );
	set( 'walkupmesh', 'walkupMesh', s.walkupMesh );
	set( 'imp2k', 'imp2k', s.imp2k );
	set( 'reflset', 'reflSet', s.reflSet );
	set( 'reflres', 'reflRes', 'half' );
	note( `mobile render settings: ${took.join( ', ' )}; the planar reflection draws the SKY only `
		+ `(no second scene pass), the drawing buffer is capped at ${( s.maxDrawingBufferPx / 1e6 ).toFixed( 1 )} M pixels` );
}

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
	planned: new Set(),              // the urls measurePlan() HEADed; anything else is off-plan
	extra: new Map(),                // off-plan url -> bytes counted, folded into the denominator
	tier: null,                      // 6b: { index, base, total } while a later tier streams
};
const MB = ( b ) => ( b / 1e6 ).toFixed( 1 );
// 6b: the streaming readout.  The loading PANEL belongs to tier 0 and goes away with the first frame;
// tiers 1-2 arrive behind a finished picture, so they get one small line instead ("tier 1: 212 / 380
// MB"), hidden with ?hud=0 like the HUD and removed the moment the last tier lands.
const tierUi = document.getElementById( 'tiers' );
function drawTierProgress() {
	if ( ! tierUi ) return;
	const s = progress.tier;
	if ( ! s || ! CFG.hud ) { tierUi.classList.add( 'hidden' ); return; }
	const got = Math.max( 0, progress.loaded - s.base );
	tierUi.classList.remove( 'hidden' );
	tierUi.textContent = `tier ${s.index}: ${MB( Math.min( got, s.total || got ) )} / ${MB( s.total )} MB`;
}
function drawProgress() {
	const pct = progress.total ? Math.min( 100, 100 * progress.loaded / progress.total ) : 0;
	bar.style.width = `${pct.toFixed( 1 )}%`;
	uiText.textContent = `${MB( progress.loaded )} / ${MB( progress.total )} MB` + ( progress.label ? ` — ${progress.label}` : '' );
	if ( progress.tier ) drawTierProgress();
}
/**
 * QA-14 minor: the bar read 639.0 MB loaded of 522.3 MB planned, 122 %.  measurePlan() HEADs every
 * file the MANIFEST plan lists, but the detail-texture sets and anything else a module fetches on its
 * own are never in that list, so their bytes landed in the numerator only.  Off-plan bytes are now
 * folded into the DENOMINATOR as they arrive, which is what "count what is actually fetched" means:
 * the bar can lag reality but it can never exceed 100 %, and `bytes.offPlan` in the sidecar names
 * every url that was not planned so the plan can be fixed rather than patched over.
 */
function addBytes( url, delta ) {
	progress.loaded += delta;
	if ( url && ! progress.planned.has( url ) ) {
		const n = ( progress.extra.get( url ) || 0 ) + delta;
		progress.extra.set( url, n );
		progress.total += delta;
	}
	drawProgress();
}
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
	files.forEach( ( f ) => progress.planned.add( f.url ) );
	// anything already counted before the plan existed is, by definition, off-plan
	progress.total = files.reduce( ( a, f ) => a + ( f.bytes || 0 ), 0 )
		+ [ ...progress.extra.values() ].reduce( ( a, b ) => a + b, 0 );
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
let foliageReport = null, shrubLodReport = null, skySphereIntegral = null, impModReport = null;
let farTreeReport = null, shrubLod1Report = null, foliageTexReport = null, farTreeUpdate = null;
let farTreeLighting = null;
let diffusePmremTarget = null, glossyEnv = null, envRotation = new THREE.Euler();
let gate3Report = null;
// ---------------------------------------------------------------------------- load tiers (6b)
// `now` is the highest tier that has fully arrived, `max` is how far this url goes (?tiers=).  A
// manifest with no `tiers` block has one tier: `count` 1, nothing streams, and every code path below
// behaves exactly as it did at v4.
const tierState = { present: false, count: 1, max: Infinity, now: 0, tier0PlannedBytes: 0,
	plan: null, per: [], deferredLightmaps: 0, streaming: false, done: false, stub: null };
let tierOf = () => 0;
// The tier at which the scene is complete enough for the foliage / impostor passes: the later of the
// env geometry and the impostor atlases, because applyFoliage produces the near-tree units the
// impostor build consumes and neither pass may run twice.
let sceneCompletionTier = 0;
// where the hero probe's six HDR faces are: the viewer used to fetch them at boot whatever the
// manifest said, which made an export that moved them to a later tier save nothing
let probeTier = 0;

function setupTiers() {
	const t = manifest.tiers;
	const askedAll = CFG.tiers === 'all' || CFG.tiers === '';
	if ( ! askedAll && ! /^\d+$/.test( CFG.tiers ) ) note( `?tiers=${CFG.tiers} is neither "all" nor a number: streaming every tier` );
	tierState.max = askedAll || ! /^\d+$/.test( CFG.tiers ) ? Infinity : parseInt( CFG.tiers, 10 );
	tierState.present = !! ( t && t.present );
	tierState.count = tierState.present ? Math.max( 1, t.count ) : 1;
	// The colour pipeline is tier 0 whatever the manifest says: there is no first frame without a
	// display transform, and the background sphere IS the first frame at five of the six stations.
	const colour = new Set( [ manifest.sky.camera, manifest.sky.glossy, manifest.sky.diffuse,
		manifest.lut && manifest.lut.url ].filter( Boolean ) );
	tierOf = ( url ) => ( colour.has( url ) ? 0 : tierForUrl( manifest.tiers, url, 0 ) );
	if ( t && t.present ) {
		for ( const u of colour ) if ( tierForUrl( t, u, 0 ) > 0 ) note( `colour file ${u.split( '/' ).pop()} is declared tier ${tierForUrl( t, u, 0 )} in the manifest; the viewer loads it at tier 0 anyway` );
		tierState.stub = ( manifest.raw.tiers && manifest.raw.tiers.stub ) || null;
		if ( tierState.stub ) note( `TIERS ARE A STUB (${tierState.stub.generator}): ${tierState.stub.warning}` );
		if ( t.oversize.length ) note( `${t.oversize.length} published file(s) over the host's per-file cap: `
			+ t.oversize.map( o => `${o.path} ${( ( o.bytes || 0 ) / 1e6 ).toFixed( 1 )} MB` ).join( ', ' ) );
	}
	// Where the foliage / impostor passes belong: after the LAST env group (v5 splits env across
	// tiers, and applyFoliage clusters crowns across the whole set — running it on half the trees and
	// again on the other half would re-cluster what it had already patched) and after the impostor
	// atlases, whose low-resolution stand-ins are what an early tier ships.
	let envTier = 0, impTier = 0;
	for ( const g of manifest.glbs ) if ( g.cls === 'env' ) envTier = Math.max( envTier, g.tier );
	const protos = ( manifest.gate3 && manifest.gate3.impostors && manifest.gate3.impostors.prototypes ) || {};
	for ( const p of Object.values( protos ) ) impTier = Math.max( impTier, tierOf( p.albedo ), tierOf( p.normalDepth ) );
	sceneCompletionTier = Math.max( envTier, impTier );
	const pf = manifest.gate3 && manifest.gate3.probe ? manifest.gate3.probe.faces : null;
	probeTier = pf ? Math.max( ...pf.map( ( u ) => tierOf( u ) ) ) : 0;
	if ( sceneCompletionTier > 0 ) note( `foliage + impostors run at tier ${sceneCompletionTier} `
		+ `(last env group tier ${envTier}, impostor atlases tier ${impTier})` );

	const byTier = {};
	for ( const g of manifest.glbs ) ( byTier[ g.tier ] ||= [] ).push( g.cls );
	if ( ! byTier[ 0 ] && manifest.glbs.length ) note( `NO glb is tier 0: the first frame has no geometry `
		+ `(tiers present: ${Object.keys( byTier ).join( ', ' )})` );
	note( `load tiers: ${tierState.count} declared, streaming up to ${tierState.max === Infinity ? 'all' : tierState.max}`
		+ ` (?tiers=${CFG.tiers}); glbs ` + Object.entries( byTier ).map( ( [ k, v ] ) => `tier ${k}: ${v.join( '+' )}` ).join( ', ' )
		+ ( tierState.present ? `; declared bytes ${Object.entries( manifest.tiers.totals ).map( ( [ k, b ] ) => `${k}=${MB( b || 0 )} MB` ).join( ', ' )}` : '' ) );
}

/** The bytes tier `t` is expected to cost: the manifest's own total when it states one (that is what
 *  the export measured), otherwise the sum of what this viewer planned for it. */
function tierBytes( t ) {
	const declared = manifest.tiers && manifest.tiers.totals ? manifest.tiers.totals[ t ] : null;
	if ( declared ) return declared + ( t === 0 ? ( manifest.tiers.bootOverhead || 0 ) : 0 );
	return ( tierState.plan ? tierState.plan( t ) : [] ).reduce( ( a, f ) => a + ( f.bytes || 0 ), 0 );
}

let patchedMaterials = 0, lightmapsApplied = 0;
// what the last whole-scene gate3 pass had already counted (its report is a total, not a delta)
let gate3Counted = { own: 0, patched: 0 };
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
	let manifestUrl = new URL( CFG.manifestUrl, location.href ).href;
	let raw = null;
	try {
		const r = await fetch( manifestUrl, { cache: 'no-cache' } );
		if ( r.ok ) raw = await r.json(); else note( `manifest ${r.status} at ${manifestUrl}` );
	} catch ( e ) { note( `manifest fetch failed: ${e.message}` ); }
	// 6b: the mobile ASSET SET is a sibling manifest (LOD1 geometry, halved ETC1S textures).  If the
	// export has not written one yet the desktop set is kept and the mobile RENDER settings still
	// apply — a phone then loads more than it should, and the log says so, which is a better failure
	// than a blank page.
	if ( MOBILE && DEVICE.settings.manifest ) {
		const mUrl = new URL( DEVICE.settings.manifest, manifestUrl ).href;
		try {
			const r = await fetch( mUrl, { cache: 'no-cache' } );
			if ( r.ok ) { raw = await r.json(); manifestUrl = mUrl; note( `mobile asset set: ${mUrl}` ); }
			else note( `mobile manifest ${r.status} at ${mUrl}: staying on the DESKTOP asset set with the mobile render settings` );
		} catch ( e ) { note( `mobile manifest fetch failed (${e.message}): staying on the DESKTOP asset set` ); }
	}
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

	// load tiers (6b) ----------------------------------------------------------------------------
	// tierState.max is how far this url goes; tierState.now is how far it has got.  Everything that
	// asks "is this file mine yet?" goes through `tierOf`, and the COLOUR pipeline (the two sky
	// equirects, the diffuse one and the LUT) is forced to tier 0 whatever the manifest says: there is
	// no first frame without a display transform, and a background is 3.6 MB.
	setupTiers();
	// What tier `t` adds to the byte plan, and nothing an earlier tier already counted.  Lightmaps
	// stay OFF the plan exactly as they were at v4 (an own map that matches no mesh is never fetched,
	// and planning it would leave the bar short of 100 %); addBytes folds them into the denominator as
	// they arrive.
	const tierPlan = ( t ) => {
		const p = [];
		if ( t === 0 ) {
			if ( manifest.sky.camera ) p.push( { url: manifest.sky.camera, kind: 'sky.camera', bytes: manifest.raw.sky?.camera?.bytes_hdr || 0 } );
			if ( manifest.sky.glossy ) p.push( { url: manifest.sky.glossy, kind: 'sky.glossy', bytes: manifest.raw.sky?.glossy?.bytes_hdr || 0 } );
			if ( manifest.sky.diffuse ) p.push( { url: manifest.sky.diffuse, kind: 'sky.diffuse', bytes: manifest.raw.sky?.diffuse?.bytes_hdr || 0 } );
			if ( CFG.lut && manifest.lut && manifest.lut.url && ! CFG.testLut ) p.push( { url: manifest.lut.url, kind: 'lut', bytes: 0 } );
		}
		if ( ! CFG.testScene ) for ( const g of manifest.glbs ) if ( g.tier === t ) p.push( { url: g.url, kind: `glb:${g.cls}`, bytes: g.bytes || 0 } );
		// The PBR set is part of the payload, so it is in the byte plan from the first frame of the bar.
		if ( materialsMode === 'pbr' && ! CFG.testScene ) {
			const before = t > 0 ? new Set( pbrPlan( manifest.materials.sets, t - 1 ).map( f => f.url ) ) : new Set();
			p.push( ...pbrPlan( manifest.materials.sets, t ).filter( f => ! before.has( f.url ) ) );
		}
		return p;
	};
	tierState.plan = tierPlan;

	// byte budget before anything downloads ------------------------------------------------------
	const tp = performance.now();
	await measurePlan( tierPlan( 0 ) );
	// The page's own cost (manifest + /basis/ + the bundle) when the manifest states it: already paid
	// by the time this line runs, so it goes into BOTH sides of the bar rather than capping it.
	if ( manifest.tiers && manifest.tiers.bootOverhead > 0 ) {
		progress.total += manifest.tiers.bootOverhead;
		progress.loaded += manifest.tiers.bootOverhead;
		note( `boot overhead ${MB( manifest.tiers.bootOverhead )} MB counted into tier 0 (already downloaded: `
			+ 'the manifest, the KTX2 transcoder and the bundle)' );
		drawProgress();
	}
	tierState.tier0PlannedBytes = progress.total;
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
			// The manifest's own value stays readable on `comp` (the sidecar and the note below both
			// report it); the viewer's scaled threshold is passed to makeBloom instead of overwriting it.
			const bloomComp = { ...comp,
				bloomThreshold: CFG.bloomThreshold ?? comp.bloomThreshold * BLOOM_THRESHOLD_SCALE,
				bloomSize: CFG.bloomRadius ?? comp.bloomSize };
			const bp = makeBloom( bloomComp, size, { half: CFG.bloomRes !== 'full' } );
			if ( bp ) { composer.addPass( bp ); postState.bloom = true; postState.bloomRes = CFG.bloomRes;
				note( `post bloom: threshold ${bloomComp.bloomThreshold.toFixed( 3 )} (scene-linear; manifest `
					+ `${comp.bloomThreshold.toFixed( 4 )} x ${CFG.bloomThreshold !== null ? '?bloomthr' : BLOOM_THRESHOLD_SCALE}), `
					+ `strength ${comp.bloomStrength}, radius ${bloomComp.bloomSize}, `
					+ `mip chain from ${bp.userData.sourceResolution.map( Math.round ).join( 'x' )} (?bloomres=${CFG.bloomRes})` ); }
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

	// geometry: TIER 0's glbs, in the manifest's order, each one drawn as soon as it lands ---------
	const tg = performance.now();
	const tier0Glbs = manifest.glbs.filter( ( g ) => g.tier === 0 );
	if ( tier0Glbs.length && ! CFG.testScene ) {
		const roots = await loadGlbs( tier0Glbs );
		await afterGeometry( roots, 0 );
	} else if ( manifest.glbs.length && ! CFG.testScene ) {
		// Every glb is in a later tier: the first frame is the sky and the water, which is a manifest
		// defect, not a viewer state.  It is said once, loudly, and the stream still runs.
		note( `PFA_TIER0_NO_GEOMETRY: ${manifest.glbs.length} glb(s) and none in tier 0` );
	} else {
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

	// materials: the Gate 2 PBR texture sets ran inside afterGeometry(), over the roots tier 0
	// brought and in nearest-material-first order.  A later tier runs the same pass over ITS roots and
	// upgrades the maps this tier could only show as factors (streamTiers -> upgradePbrSets).

	// QA-13-1, tier-aware (6b): the baked hero probe is the irradiance of everything with no baked
	// light.  The export may put its six HDR faces in a later tier (6.3 MB); until they arrive those
	// surfaces take the sky-diffuse PMREM, which is the documented ?probe=0 path — dimmer and flatter
	// in the shade, never unlit.  `probeTier` is where the faces actually are.
	if ( probeTier === 0 || ! ( manifest.gate3 && manifest.gate3.probe ) ) await setupProbeEnv();
	else note( `probe env deferred to tier ${probeTier} (${manifest.gate3.probe.faces.length} face(s)); until then `
		+ 'surfaces with no baked light take the sky-diffuse PMREM' );

	// 6c foliage, the far-tree impostors and the far-tree lighting run ONCE, at the load tier that
	// brings the env glb and the impostor atlases (tier 0 when the manifest has no tiers, which is
	// every manifest up to v4 — the order there is unchanged).  They cannot be split across tiers:
	// applyFoliage patches each leaf material exactly once and the impostor build needs the near-tree
	// units that patch produces.
	if ( sceneCompletionTier === 0 ) await setupFoliageAndImpostors();

	applyReflectionAndFog();

	// first frame -------------------------------------------------------------------------------
	renderFrame();
	requestAnimationFrame( () => {
		renderFrame();
		ui.style.display = 'none';
		loadTimes.total_s = ( performance.now() - t0 ) / 1000;   // set BEFORE __pfaReady: the harness
		window.__pfaReady = true;                                // reads __pfaInfo() the moment it flips
		// 6b: the page's OWN first-frame time, in ms since the document started.  A harness that polls
		// for __pfaReady notices it up to a poll late, and the tier-1 stream has begun by then, so
		// "bytes before the first frame" measured from the poll is too high.  This is the honest mark.
		window.__pfaReadyAt = performance.now();
		tierState.per.push( { tier: 0, wall_s: loadTimes.total_s,
			bytes: progress.loaded, planned: tierState.tier0PlannedBytes, glbs: glbRoots.length } );
		note( `ready in ${loadTimes.total_s.toFixed( 2 )} s: ${MB( progress.loaded )} MB loaded of ${MB( progress.total )} MB planned `
			+ `(plan ${loadTimes.plan_s.toFixed( 2 )} s, sky ${loadTimes.sky_s.toFixed( 2 )} s, lut ${loadTimes.lut_s.toFixed( 2 )} s, glb ${loadTimes.glb_s.toFixed( 2 )} s)`
			+ ( tierState.count > 1 ? ` — TIER 0 of ${tierState.count}` : '' ) );
		animate();
		// 6b: tiers 1..n stream BEHIND the presented first frame, in manifest order.  The lazy foliage
		// glbs are part of that stream now (they used to be started here directly); with no tiers in
		// the manifest streamTiers() does exactly what this line did.
		streamTiers();
	} );
}

/**
 * 6b: load tiers 1..max after the first frame is on screen.  Each tier brings its glb groups, the
 * full-resolution files of the textures earlier tiers could only show as a factor or a low-resolution
 * stand-in, and the lightmaps that were deferred with them; the scene-completion passes (foliage,
 * impostors) run at the tier that brings their geometry.  Nothing here blocks a frame: every step is
 * awaited between rendered frames, and `__pfaTiersReady` flips when the last one lands.
 */
async function streamTiers() {
	window.__pfaTiersReady = false;
	tierState.streaming = true;
	try {
		for ( let t = 1; t < tierState.count && t <= tierState.max; t ++ ) {
			const t0 = performance.now();
			const before = progress.loaded;
			progress.tier = { index: t, base: before, total: tierBytes( t ) };
			drawTierProgress();
			const plan = tierState.plan ? tierState.plan( t ) : [];
			for ( const f of plan ) progress.planned.add( f.url );          // its bytes are not off-plan
			progress.total += plan.reduce( ( a, f ) => a + ( f.bytes || 0 ), 0 );
			const roots = await loadGlbs( manifest.glbs.filter( ( g ) => g.tier === t ) );
			await afterGeometry( roots, t );
			// the maps an earlier tier showed as a factor or a low-resolution stand-in, and the maps the
			// GLBS reference themselves, which no manifest material set names
			{
				const beforeTex = collectTextures( scene );
				const up = materialsMode === 'pbr'
					? await upgradePbrSets( { scene, maxTier: t, loadTexture: loadAnyTexture, note } )
					: { upgraded: 0, candidates: 0, bytes: 0, failed: [] };
				const glbUp = await upgradeGlbTextures( { scene, maxTier: t, note, loadTexture: loadAnyTexture,
					upgradeOf: manifest.tiers ? manifest.tiers.upgradeOf : null } );
				if ( up.upgraded || glbUp.upgraded ) disposeOrphans( scene, beforeTex );
				tierState.lowresRemaining = glbUp.remaining;
				tierState.upgrades = [ ...( tierState.upgrades || [] ), { tier: t, ...up, failed: up.failed.length,
					glb_textures: glbUp.upgraded, glb_textures_remaining: glbUp.remaining.length } ];
			}
			if ( t === probeTier ) await setupProbeEnv();
			if ( t === sceneCompletionTier ) await setupFoliageAndImpostors();
			if ( roots.length ) applyReflectionAndFog();
			tierState.now = t;
			const wall = ( performance.now() - t0 ) / 1000;
			tierState.per.push( { tier: t, wall_s: wall, bytes: progress.loaded - before,
				planned: progress.tier.total, glbs: roots.length } );
			note( `tier ${t} in ${wall.toFixed( 2 )} s: ${MB( progress.loaded - before )} MB, ${roots.length} glb(s)`
				+ ( tierState.deferredLightmaps ? `, ${tierState.deferredLightmaps} lightmap(s) still deferred` : '' ) );
			renderFrame();
			await new Promise( ( r ) => requestAnimationFrame( r ) );
		}
		// The lazily loaded foliage glbs belong to the tier that owns the env geometry; with no tiers
		// they run here exactly as they did before 6b.  With ?tiers= stopping short of that tier there
		// is no foliage report for them to join to, so they are not fetched at all — a tier-0 capture
		// must cost tier 0 and nothing else.
		if ( sceneCompletionTier <= tierState.max ) await loadLazyFoliage();
		else note( `lazy foliage not loaded: it belongs to tier ${sceneCompletionTier} and ?tiers=${CFG.tiers} stops at ${tierState.max}` );
	} catch ( e ) {
		note( `tier stream FAILED: ${e.message}` );
		tierState.error = e.message;
	} finally {
		progress.tier = null;
		drawTierProgress();
		tierState.streaming = false;
		tierState.done = true;
		window.__pfaTiersReady = true;
		if ( tierState.count > 1 ) note( `tiers complete: ${tierState.per.map( p => `${p.tier}:${MB( p.bytes )} MB/${p.wall_s.toFixed( 1 )} s` ).join( ', ' )}`
			+ `; ${MB( progress.loaded )} MB total` );
		// THE ASSERTION: after the last tier nothing in the scene may still be wearing a file an
		// earlier tier shipped as a low-resolution stand-in.  It is stated either way, so a capture
		// can be checked without re-deriving it.
		if ( tierState.max === Infinity && manifest.tiers && manifest.tiers.upgradeOf && manifest.tiers.upgradeOf.size ) {
			const left = lowresStillInScene();
			tierState.lowresRemaining = left;
			// The url check only sees textures that HAVE a url.  A texture the glb embedded in a buffer
			// view reaches three as a blob and keeps whatever encode the pack chose, so the format
			// census is the other half of the same question: on the desktop tier every map is UASTC
			// (ASTC on this GPU), and anything still in an ETC1S/ETC2 format is a low-resolution
			// leftover that no viewer-side swap can reach.
			const res = residentBytes();
			const etc = Object.entries( res.texture_formats || {} )
				.filter( ( [ f ] ) => /ETC/i.test( f ) ).reduce( ( a, [ , n ] ) => a + n, 0 );
			tierState.lowresEtcTextures = etc;
			note( left.length
				? `LOW-RESOLUTION FILES STILL IN THE SCENE after the last tier: ${left.length} — `
					+ left.slice( 0, 6 ).map( ( u ) => u.split( '/' ).pop() ).join( ', ' ) + ( left.length > 6 ? ' …' : '' )
				: 'low-resolution check: 0 tier-0 stand-in textures remain in the scene after the last tier' );
			if ( etc && DEVICE.tier !== 'mobile' ) note( `low-resolution check: ${etc} texture(s) are STILL in an ETC `
				+ 'format on the desktop tier — an embedded (buffer-view) texture has no url, so no tier can replace '
				+ 'it; the export has to pack the groups with EXTERNAL textures for those to sharpen' );
		}
		renderFrame();
	}
}

/**
 * The baked hero probe as the irradiance of everything with no baked light.  Extracted so a
 * manifest that puts its faces in a later tier can run it there instead of at boot.
 */
async function setupProbeEnv() {
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

}

/**
 * The passes that need the WHOLE scene: the bake's far-tree lighting, the leaf shader and crown
 * normals, the shrub LOD, and the far-tree impostors.  Run once, from boot() when the env geometry is
 * in tier 0 and from streamTiers() when it is not.
 */
async function setupFoliageAndImpostors() {
	// 6c round 2: the bake's far-tree lighting (a few kB, inline or a sidecar json).  Fetched HERE,
	// not with the lazy glb, because the impostors are built below and their modulation mode depends
	// on whether E_bake has been measured.
	if ( manifest.raw && manifest.raw.trees && manifest.raw.trees.far_mesh ) {
		try {
			farTreeLighting = await loadFarTreeLighting( manifest, async ( url ) => {
				const r = await fetch( url );
				if ( ! r.ok ) throw new Error( `HTTP ${r.status}` );
				return r.json();
			}, note );
		} catch ( e ) { note( `far-tree lighting: ${e.message}` ); }
	}

	// Phase 6c item C: the leaf shader, the crown-bent normals and the runtime tree LOD -----------
	// AFTER the probe pass, because `applyProbeEnv` reads `pfaPatched` and the foliage patch adds its
	// own chain on top of whatever the shrub/reed cards already carry; BEFORE the impostors, which
	// need the near-tree units and the switch uniforms this pass computes.
	{
		const t = ( CFG.treeMesh || '' ).toLowerCase();
		const meshDist = ( t === 'inf' || t === 'never' ) ? Infinity
			: ( CFG.treeMesh !== null && CFG.treeMesh !== '' && isFinite( parseFloat( CFG.treeMesh ) ) ? parseFloat( CFG.treeMesh ) : 40 );
		const trnArg = ( CFG.leafTrn || '' ).toLowerCase();
		const trnShrubs = trnArg === 'shrubs' || trnArg === '1s';
		const trnScale = trnShrubs ? 1 : ( CFG.leafTrn !== null && isFinite( parseFloat( CFG.leafTrn ) ) ? parseFloat( CFG.leafTrn ) : 1 );
		// alphaToCoverage is only worth asking for when the target this draws into is multisampled:
		// the composer's is `samples: 4` and so is the Reflector's, and with ?post=none the canvas
		// itself is `antialias: true`.
		const msaa = CFG.leafSoft && ( ( composer && composer.renderTarget1 && composer.renderTarget1.samples > 0 )
			|| renderer.getContext().getParameter( renderer.getContext().SAMPLES ) > 0 );
		const vi = manifest.gate3 && manifest.gate3.vertexIrradiance;
		const vertexIrrScale = ( vi && vi.range > 0 && ! vi.rangeConflict ) ? vi.range * manifest.gate3.scale : 0;
		// 6c round 2, BEFORE the patch: export item D's tinted albedo and per-texel translucency
		// factor (the glb ships the untinted source card), and the per-row LOD mask for the three
		// shrub meshes with no LOD1 - a shader attribute has to exist when the program is built.
		foliageTexReport = await applyFoliageTextures( { scene, manifest, note, mode: CFG.foliageTex,
			loadTexture: ( url ) => { progress.label = url.split( '/' ).pop();
				return getKTX2().loadAsync( url, onProgressFor( url ) ); } } );
		markShrubLodRows( scene, manifest, note );
		foliageReport = applyFoliage( { scene, sun: sunLight, note, msaa, vertexIrrScale,
			normalBlend: CFG.leafNormal, cardNormalBlend: CFG.cardNormal,
			interior: CFG.crownInt, cardInterior: CFG.cardInt, normalGate: CFG.leafGate,
			mipBias: CFG.foliageBias, cardEnv: CFG.cardEnv,
			trnScale, trnShrubs, meshDist, fadeBand: CFG.treeFade,
			trnMaps: foliageTexReport ? foliageTexReport.trnMaps : null } );
		shrubLodReport = applyShrubLod( { scene, manifest, note, dist: CFG.shrubLod } );
	}

	// far-tree impostors (Gate 4 item 2) ----------------------------------------------------------
	// They REPLACE the Gate 1 placeholder quads: when they build, the placeholders are not made at all,
	// so a capture can never show a grey card where a tree should be and the name sweep stays clean.
	const impAvailable = CFG.impostors && manifest.gate3 && manifest.gate3.impostors
		&& manifest.gate3.impostors.count && manifest.treesFar.length;
	if ( impAvailable ) {
		// 6c C2: the near trees join the impostor set so that a tree beyond the switch distance is
		// drawn ONCE, as a card, instead of as a full mesh for ever.  With ?treemesh=inf the list is
		// empty and the build is exactly the round-15 one.
		// E_bake: the irradiance the atlases were baked under.  Sphere-averaged, both terms carry the
		// same 1/4, so the ratio only needs sun + sky:  E = sunColour * irradiance + integral L_sky dw.
		// It is an ESTIMATE of the bake rig (which also had a lawn bounce), which is exactly why the
		// default mode is `chroma`: a wrong magnitude cancels, a wrong colour does not.
		// The bake's own per-prototype E_bake, when it has shipped: raw manifest units (irradiance/pi),
		// so it is scaled by lightmaps.scale here to match the near trees' own crown irradiance, which
		// is a decoded FULL irradiance.  The far trees' side divides raw by raw and never sees this.
		const protoE = prototypeEbake( farTreeLighting );
		let eBake = null, eBakeFrom = 'none';
		if ( CFG.impBake && CFG.impBake.split( ',' ).length === 3 ) {
			eBake = CFG.impBake.split( ',' ).map( Number ); eBakeFrom = '?impbake';
		} else if ( protoE ) {
			const k = manifest.gate3 ? manifest.gate3.scale : Math.PI;
			eBake = {};
			for ( const [ name, e ] of Object.entries( protoE ) ) eBake[ name ] = e.map( ( x ) => x * k );
			eBakeFrom = `the bake, per prototype (${Object.keys( protoE ).length} value(s))`;
		} else if ( skySphereIntegral && sunLight ) {
			const sc = sunLight.color.clone().multiplyScalar( sunLight.intensity );
			eBake = [ sc.r + skySphereIntegral.x, sc.g + skySphereIntegral.y, sc.b + skySphereIntegral.z ];
			eBakeFrom = 'sun + the sky diffuse integral (estimate)';
		}
		// ?impmod= wins; with nothing asked the mode is `full` once E_bake is MEASURED and `chroma`
		// while it is the viewer's own sky estimate (an estimate off by a factor would re-light every
		// tree by that factor; a chroma-normalised ratio cannot).
		const impMode = CFG.impMod === '0' ? '0'
			: ( CFG.impMod === 'full' ? 'full'
				: ( CFG.impMod === 'chroma' ? 'chroma' : ( protoE ? 'full' : 'chroma' ) ) );
		const far = farTreeIrradiance( manifest.treesFar, manifest.raw, impMode, note );
		const treesFar = ( impMode !== '0' && far.byIndex.size )
			? manifest.treesFar.map( ( t, i ) => ( far.byIndex.has( i ) ? { ...t, irr: far.byIndex.get( i ) } : t ) )
			: manifest.treesFar;
		const nearEntries = ( foliageReport && Number.isFinite( foliageReport.meshDist ) )
			? nearTreeImpostorEntries( foliageReport.units, manifest.gate3.impostors, note, eBake, impMode ) : [];
		// Round-1 review 4: a unit with no impostor behind it must NOT dissolve at the switch distance.
		if ( nearEntries.unmatched && nearEntries.unmatched.length )
			keepMeshAlways( foliageReport, nearEntries.unmatched.map( ( u ) => u.mesh ), note );
		impModReport = { mode: impMode, eBake: Array.isArray( eBake ) ? eBake : ( eBake ? Object.keys( eBake ).length : null ),
			eBakeFrom, far: far.applied, farUnmatched: far.unmatched,
			near: nearEntries.filter( ( e ) => e.irr ).length };
		// eBake is EITHER one rgb (the viewer's sky estimate) OR a map keyed by prototype (the bake's)
		const eBakeStr = Array.isArray( eBake ) ? eBake.map( ( v ) => v.toFixed( 2 ) ).join( '/' )
			: ( eBake ? `${Object.keys( eBake ).length} per-prototype value(s)` : 'unknown' );
		note( `impostor irradiance modulation: mode ${impMode}, E_bake ${eBakeStr} `
			+ `from ${eBakeFrom}; ${impModReport.far} far + ${impModReport.near} near placement(s) modulated` );
		const built = buildImpostors( {
			impostors: manifest.gate3.impostors, far: treesFar, near: nearEntries, note,
			normalDepth: CFG.impNormalDepth, debug: CFG.impDebug,
			atlas2k: CFG.imp2k, interior: CFG.impInt,
			switchUniforms: foliageReport ? foliageReport.shared.uniforms : null,
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

}

/**
 * The Reflector's draw set and the water's airlight.  Re-run after every tier that adds geometry:
 * both are traversals of the finished scene, and a mesh that arrives later must be excluded from the
 * reflection on the same terms as one that was there at boot.
 */
function applyReflectionAndFog() {
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
		{ note, orn: true, backdrop: CFG.reflSet === 'both', all: CFG.reflSet === 'all' } );
	else if ( water ) note( 'reflection draw set NOT reduced (?reflset=full): the Reflector traverses the whole scene' );

}

/**
 * 6c round 2 — the two lazily loaded foliage glbs.  Called AFTER `__pfaReady` and after the first
 * frame is on screen: nothing in that frame depends on either file, and a capture harness that waits
 * for `__pfaReady` would otherwise be paying for them.  `__pfaLazyReady` flips when both are done, and
 * `__pfaInfo()` carries both reports, so a capture can wait for the full scene when it wants it.
 */
async function loadLazyFoliage() {
	const t0 = performance.now();
	window.__pfaLazyReady = false;
	const loader = new GLTFLoader( manager ).setKTX2Loader( getKTX2() ).setMeshoptDecoder( MeshoptDecoder );
	const loadGlb = async ( url ) => {
		const buf = await fetchBuffer( url );
		const base = url.slice( 0, url.lastIndexOf( '/' ) + 1 );
		const gltf = await loader.parseAsync( buf, base );
		gltf.userData.pfaBytes = buf.byteLength;
		return gltf;
	};
	const common = {
		scene, manifest, loadGlb, note, sun: sunLight,
		probeTexture: probeTarget ? probeTarget.texture : null,
		foliageReport, msaa: foliageReport ? foliageReport.msaa : false,
		normalBlend: CFG.leafNormal, cardNormalBlend: CFG.cardNormal,
		interior: foliageReport ? foliageReport.interior : CFG.crownInt,
		cardInterior: foliageReport ? foliageReport.cardInterior : CFG.cardInt,
		normalGate: foliageReport ? foliageReport.normalGate : CFG.leafGate,
		mipBias: CFG.foliageBias, shrubCov: CFG.shrubCov,
		trnScale: foliageReport ? foliageReport.trnScale : 1,
		trnShrubs: foliageReport ? foliageReport.trnShrubs : false,
		trnMaps: foliageTexReport ? foliageTexReport.trnMaps : null,
		albedoMaps: foliageTexReport ? foliageTexReport.albedoMaps : null,
		meshDist: foliageReport ? foliageReport.meshDist : 40,
		fadeBand: foliageReport ? foliageReport.fadeBand : 5,
		uvDequant: CFG.uvDequant,
		scale: manifest.gate3 ? manifest.gate3.scale : Math.PI,
	};
	try {
		farTreeReport = await loadFarTrees( { ...common, impostorGroup, farTrn: CFG.farTrn, aoEnv: CFG.farAo, farMeshDist: CFG.farTreeMesh,
			walkup: CFG.walkupMesh, walkupDist: parseFloat( CFG.walkupMesh ),
			mode: CFG.farTreeLight, impMode: impModReport ? impModReport.mode : 'chroma' } );
		if ( farTreeReport && farTreeReport.update ) farTreeUpdate = farTreeReport.update;
	} catch ( e ) { note( `far-tree meshes FAILED: ${e.message}` ); farTreeReport = { error: e.message }; }
	renderFrame();
	await new Promise( ( r ) => requestAnimationFrame( r ) );
	try {
		shrubLod1Report = await loadShrubLod1( { ...common, envScale: CFG.shrubEnv,
			dist: shrubLodReport ? shrubLodReport.dist : 30, mode: CFG.shrubLod === 0 ? '0' : 'on' } );
	} catch ( e ) { note( `shrub/reed LOD1 FAILED: ${e.message}` ); shrubLod1Report = { errors: [ e.message ] }; }
	if ( farTreeUpdate ) farTreeUpdate( camera );
	renderFrame();
	window.__pfaLazyReady = true;
	note( `lazy foliage done in ${( ( performance.now() - t0 ) / 1000 ).toFixed( 2 )} s` );
}

async function loadSky() {
	const load = ( url ) => {
		const L = url.endsWith( '.exr' ) ? new EXRLoader( manager ) : new RGBELoader( manager );
		progress.label = url.split( '/' ).pop();
		return L.loadAsync( url, onProgressFor( url ) );
	};
	const rotY = THREE.MathUtils.degToRad( manifest.sky.rotationDeg );
	envRotation = new THREE.Euler( 0, rotY, 0 );
	const pmremOf = async ( url, measure = false ) => {
		const tex = await load( url );
		if ( measure ) {
			skySphereIntegral = equirectIntegral( tex );
			if ( skySphereIntegral ) note( `sky diffuse integral / L dw = ${skySphereIntegral.toArray().map( ( v ) => v.toFixed( 3 ) ).join( ', ' )} `
				+ '(the sky half of the irradiance the impostor atlases were baked under)' );
		}
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
			diffusePmremTarget = await pmremOf( manifest.sky.diffuse, true );
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
let ktx2RawLoad = null;
function getKTX2() {
	// One instance, kept alive: it owns a worker pool and also transcodes any .ktx2 lightmap.
	if ( ! ktx2Loader ) {
		ktx2Loader = new KTX2Loader( manager ).setTranscoderPath( '/basis/' ).detectSupport( renderer );
		ktx2RawLoad = ktx2Loader.load.bind( ktx2Loader );
		// GLTFLoader asks THIS loader for every texture `gltfpack -tr` left external, and it caches
		// per parse, so the same file reached the GPU once per glb group that referenced it.  Routing
		// its `load` through the shared cache makes the groups share one upload (and stamps `pfaUrl`,
		// which is what the tier upgrade of a glb-referenced texture is keyed on).
		ktx2Loader.load = ( url, onLoad, onProgress, onError ) => {
			// A glTF image stored in a BUFFER VIEW reaches the loader as a blob: url that GLTFLoader
			// made and revokes itself.  It has no identity to cache on and no extension to switch on,
			// so it goes straight to the real loader.  (An embedded texture also cannot be upgraded to
			// a later tier: there is no url for the manifest to name.)
			if ( /^blob:/.test( url ) ) return ktx2RawLoad( url, onLoad, onProgress, onError );
			loadAnyTexture( url ).then( ( t ) => onLoad && onLoad( t ) ).catch( ( e ) => {
				if ( onError ) onError( e ); else note( `ktx2 ${url.split( '/' ).pop()} failed: ${e.message}` );
			} );
			return ktx2Loader;
		};
	}
	return ktx2Loader;
}

/** Cycles' colour-off diffuse pass is irradiance/pi and three's lightMap path divides by pi again in
 *  BRDF_Lambert, so the manifest's lightmap_scale (pi) is applied as lightMapIntensity. */
let lightmapScale = 1.0;

/**
 * Load ONE GROUP of glbs — at v4 that is every glb in the manifest, at v5 it is the groups of one
 * load tier — and return the roots it added.  What happens AFTER the geometry (lightmaps, chunking,
 * the PBR and detail passes, the probe) is `afterGeometry`, because a later tier has to run the same
 * passes over the meshes it brings and nothing else.
 */
async function loadGlbs( list = manifest.glbs ) {
	lightmapScale = CFG.lmScale !== null ? CFG.lmScale : manifest.lightmapScale;
	if ( ! glbRoots.length ) note( `lightMapIntensity = lightmap_scale ${lightmapScale.toFixed( 5 )}${CFG.lmScale !== null ? ' (?lmscale override)' : ''}` );
	const loader = new GLTFLoader( manager ).setKTX2Loader( getKTX2() ).setMeshoptDecoder( MeshoptDecoder );
	const newRoots = [];
	let first = ! glbRoots.length;
	for ( const g of list ) {
		const t = performance.now();
		progress.label = g.name;
		try {
			const buf = await fetchBuffer( g.url );
			const base = g.url.slice( 0, g.url.lastIndexOf( '/' ) + 1 );
			const gltf = await loader.parseAsync( buf, base );
			// The root name is the lighting CLASS, because reduceReflectionSet and the instance
			// irradiance both look a class up by name.  v5 may ship several GROUPS of one class, and
			// two roots may not share a name, so the second group onward carries its group key too.
			gltf.scene.name = scene.getObjectByName( `WEB_glb_${g.cls}` )
				? `WEB_glb_${g.cls}_${g.group || g.order}` : `WEB_glb_${g.cls}`;
			// Gate 4 item 1c: the glTF NODE INDEX is the only stable key gltfpack -mi leaves (it drops
			// node names), and it is what lightmaps.instance_irradiance.nodes[].gltf_node refers to.
			// GLTFLoader's parser.associations is the only place it survives, so it is stamped on the
			// object here, before any pass can reshape the graph.
			if ( gltf.parser && gltf.parser.associations ) {
				for ( const [ obj, a ] of gltf.parser.associations )
					if ( obj && obj.isObject3D && a && typeof a.nodes === 'number' ) obj.userData.pfaGltfNode = a.nodes;
			}
			// FIRST, before any pass: gltfpack stores texcoords as normalised 12-bit ints with the
			// dequantisation in KHR_texture_transform on the baseColorTexture only, so every UV that
			// reaches a shader is 1/16 of its real value until this undoes it on the attribute.
			// See src/uvDequant.js.  ?uvdq=0 restores the broken behaviour for an A/B.
			uvDequantReport.push( { name: g.name, ...dequantizeUvs( gltf.scene, { note, enabled: CFG.uvDequant } ) } );
			scene.add( gltf.scene );
			glbRoots.push( gltf.scene );
			newRoots.push( gltf.scene );
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
	return newRoots;
}

/** The loader every texture pass uses: KTX2 through the shared transcoder, HDR/EXR through their own,
 *  everything else through TextureLoader, with the bytes counted into the progress bar either way. */
function rawLoadTexture( url ) {
	progress.label = url.split( '/' ).pop();
	if ( /\.ktx2$/i.test( url ) ) {
		// the ORIGINAL load: `loadAsync` calls `this.load`, which is the method the dedupe below
		// replaces, so going through it here would recurse forever
		const ktx = getKTX2();
		return new Promise( ( resolve, reject ) => ktx2RawLoad( url, resolve, onProgressFor( url ), reject ) );
	}
	if ( /\.hdr$/i.test( url ) ) return new RGBELoader( manager ).loadAsync( url, onProgressFor( url ) );
	if ( /\.exr$/i.test( url ) ) return new EXRLoader( manager ).loadAsync( url, onProgressFor( url ) );
	return new THREE.TextureLoader( manager ).loadAsync( url, onProgressFor( url ) );
}

/**
 * ONE GPU UPLOAD PER URL, across every glb group and every manifest pass.
 *
 * GLTFLoader caches textures per PARSE, so a texture `gltfpack -tr` left external and two tier groups
 * both reference was uploaded twice — and so was a lightmap or a PBR map whose two users were passes
 * with their own little caches.  Measured at the hero on the v5 groups: 2 217 MB resident against
 * 1 819 MB for the same scene as one glb per class.
 *
 * The cache holds the FIRST texture per url; every later user gets `clone()`, which copies the
 * sampler state but shares `texture.source`.  three keys its WebGLTexture by source + sampler cache
 * key and refcounts it (`usedTimes` in WebGLTextures.deallocateTexture), so identical users share one
 * upload, a user that needs different sampler state gets its own — which is correct, not a leak — and
 * disposing one clone cannot pull the texture out from under another.
 */
const textureCache = new Map();          // url -> Promise<THREE.Texture> (the first one loaded)
const textureShare = { urls: 0, shared: 0, bytesSaved: 0 };
function loadAnyTexture( url ) {
	if ( ! textureCache.has( url ) ) {
		textureShare.urls ++;
		textureCache.set( url, rawLoadTexture( url ).then( ( t ) => {
			t.userData.pfaUrl = url;     // the identity the glb-texture upgrade below is keyed on
			return t;
		} ) );
		return textureCache.get( url );
	}
	return textureCache.get( url ).then( ( t ) => {
		textureShare.shared ++;
		textureShare.bytesSaved += texBytes( t );
		const c = t.clone();             // shares `source`: one upload, independent sampler state
		c.userData.pfaUrl = url;
		return c;
	} );
}

/**
 * Everything that has to happen once a group of glbs is in the scene.  Called for tier 0 during boot
 * and again for each later tier; `newRoots` is what that tier added (empty when a tier brings only
 * textures), and `tier` is how far the load has got, which is what the lightmap and PBR passes test
 * a file's own tier against.
 */
async function afterGeometry( newRoots, tier ) {
	// Gate 3 (manifest v4): the baked lightmaps.  BEFORE chunking (a chunk inherits its slice of the
	// per-instance slot attribute) and BEFORE the PBR / detail passes, which match on material NAME
	// and so texture every clone this pass makes.
	// It runs over the WHOLE scene, not over newRoots: a later tier's job is as much to bind the maps
	// an earlier tier deferred as to light the meshes it brought.  The pass re-plans from scratch and
	// is idempotent (see applyGate3Lightmaps), and the two irradiance passes are skipped on a re-run
	// that added no geometry, since they would traverse the same meshes for the same result.
	if ( manifest.gate3 && lightingMode === 'baked' ) {
		// The per-placement irradiance binds to the glb `instance_irradiance.glb` names: with that glb
		// in a later tier it is not an error that it is missing, it is simply not here yet.
		const iiGlb = manifest.gate3.instanceIrradiance ? manifest.gate3.instanceIrradiance.glb : null;
		// The per-placement irradiance is keyed to the glTF NODE INDEX and the per-node row counts of
		// ONE env glb (gltfpack drops names, so the index is the only key there is).  When v5 splits
		// env into per-tier GROUPS those indices no longer exist: node 1 of env_t0 is a different mesh
		// with a different row count, and lightmaps.js refuses to bind a misaligned array — rightly,
		// because binding it would tint 1 379 shrubs from the wrong rows.  The pass is skipped, loudly:
		// the export has to re-emit `lightmaps.instance_irradiance` per GROUP for it to come back.
		const envGroups = manifest.glbs.filter( ( g ) => g.cls === ( iiGlb || 'env' ) ).length;
		const iiSplit = !! ( iiGlb && envGroups > 1 );
		const iiHere = ! iiGlb || ( ! iiSplit && !! scene.getObjectByName( `WEB_glb_${iiGlb}` ) );
		if ( iiSplit && ! tier ) note( `gate4 instance irradiance SKIPPED: ${iiGlb} ships as ${envGroups} tier groups and the `
			+ `manifest's node indices / row counts are those of the single ${iiGlb}.glb — the 1 379 shrub and reed `
			+ `placements stay on the probe until the export re-emits lightmaps.instance_irradiance per group` );
		const report = applyGate3Lightmaps( {
			scene, gate3: manifest.gate3, assets: manifest.assets, note, flipV: CFG.lmFlip, encodeOverride: CFG.lmEnc,
			vertexIrr: CFG.vertexIrr, instIrr: iiHere ? CFG.instIrr : '0', shrubCov: CFG.shrubCov,
			tierOf, maxTier: tier, skipIrradiance: ! newRoots.length,
			loadTexture: loadAnyTexture,
		} );
		await report.promise;
		if ( ! iiHere ) note( `gate3 instance irradiance postponed: ${iiGlb}.glb is in a later load tier` );
		// The pass re-plans the WHOLE scene every time, so its counts are totals, not deltas: what a
		// re-run adds is the difference against the last one, or a three-tier load would report three
		// times the lightmaps it applied.
		lightmapsApplied += report.own.applied - gate3Counted.own;
		patchedMaterials += ( report.own.applied + report.slots.meshes.length ) - gate3Counted.patched;
		gate3Counted = { own: report.own.applied, patched: report.own.applied + report.slots.meshes.length };
		tierState.deferredLightmaps = report.deferred.length;
		gate3Report = report;
	}

	// QA-11d-1: a site-spanning InstancedMesh passes the frustum test everywhere.  Split those
	// batches into regional ones so a station that sees little of the site draws little of it.
	chunkStats = chunkStats || { candidates: 0, split: 0, chunks: 0, added: 0, batches: [], spent: 0 };
	const chunkArgs = ( CFG.chunk || '' ).split( ',' ).map( Number );
	if ( CFG.chunk !== '0' && newRoots.length ) {
		const opts = {};
		if ( chunkArgs.length && isFinite( chunkArgs[ 0 ] ) && chunkArgs[ 0 ] > 0 ) opts.minRadius = chunkArgs[ 0 ];
		if ( isFinite( chunkArgs[ 1 ] ) ) opts.maxDepth = chunkArgs[ 1 ];
		if ( isFinite( chunkArgs[ 2 ] ) ) opts.gain = chunkArgs[ 2 ];
		if ( isFinite( chunkArgs[ 3 ] ) ) opts.budget = chunkArgs[ 3 ];
		chunkStats.opts = opts;
		// The budget is the ADDED draw calls over the WHOLE scene, so it has to be spent across the
		// glbs, not per glb (each root would otherwise get the full allowance) — and across TIERS too,
		// so what earlier tiers spent is carried in chunkStats.added.
		let left = ( opts.budget !== undefined ? opts.budget : 32 ) - chunkStats.added;
		for ( const root of newRoots ) {
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
	} else if ( CFG.chunk === '0' && ! tier ) { note( 'instance chunking disabled (?chunk=0)' ); }
	finishMaterials();

	// The Gate 2 PBR sets and the QA-12-1 detail layer, over the meshes THIS tier brought.  Passing
	// the new root as the traversal root is what keeps a second tier from re-walking (and re-loading)
	// materials an earlier one already textured; the tier UPGRADE of an existing material is a
	// different pass (upgradePbrSets), run from streamTiers.
	if ( materialsMode === 'pbr' && newRoots.length ) await applyMaterialPasses( newRoots, tier );

	// QA-13-1: the baked hero probe as the irradiance of everything with no baked light, for the new
	// meshes too (applyProbeEnv skips a material that already has it).
	if ( probeTarget ) {
		if ( CFG.probeSpec ) assignSpecularEnv();
		for ( const root of newRoots ) applyProbeEnv( root, probeTarget.texture, { note: () => {}, gate3Report } );
	}
}

/** The PBR + detail passes over one or more roots (Gate 2 / QA-12-1), tier-aware. */
async function applyMaterialPasses( roots, tier ) {
	const tt = performance.now();
	const texturesBeforePbr = collectTextures( scene );
	for ( const root of roots ) {
		let drawn = 0;
		const rep = await applyPbrSets( {
			scene: root, camera, sets: manifest.materials.sets, note, maxTier: tier,
			loadTexture: loadAnyTexture,
			// progressive: the near materials are visible while the far ones are still downloading
			onLoaded: ( m, applied, done, total ) => {
				progress.label = `materials ${done}/${total}`;
				if ( done - drawn >= 16 || done === total ) { drawn = done; renderFrame(); }
			},
		} );
		pbrReport = pbrReport ? mergePbrReports( pbrReport, rep ) : rep;
		if ( CFG.detail > 0 && manifest.materials.detail ) {
			detailReport = await applyDetail( {
				scene: root, detail: manifest.materials.detail, note,
				projection: CFG.detailProj, strength: CFG.detail, normalScale: CFG.detailNormal,
				lodBias: CFG.detailBias, gain: CFG.detailGain, debug: parseInt( qs.get( 'detaildebug' ) || '0', 10 ),
				synthetic: CFG.detailTest === 'noise',
				loadTexture: loadAnyTexture,
			} );
			renderFrame();
		} else if ( manifest.materials.detail && ! tier ) {
			note( `detail layer OFF (?detail=${CFG.detail}); the manifest carries ${Object.keys( manifest.materials.detail.sets ).length} tiling set(s)` );
		}
	}
	// A replaced Gate 1 map (the ORN normals) is unreachable but still on the GPU: free it.
	const freed = disposeOrphans( scene, texturesBeforePbr );
	if ( pbrReport ) pbrReport.disposed = freed;
	loadTimes.tex_s += ( performance.now() - tt ) / 1000;
	note( `pbr textures in ${( ( performance.now() - tt ) / 1000 ).toFixed( 2 )} s; `
		+ `${freed.disposed} superseded texture(s) disposed, ${MB( freed.freed_bytes )} MB freed` );
}

/** Two PBR reports over disjoint roots, added up: the numbers are per scene, not per glb. */
function mergePbrReports( a, b ) {
	const out = { ...a };
	for ( const k of [ 'materials_in_scene', 'matched', 'textures', 'unique_files', 'bytes', 'kept_glb_normal',
		'replaced_glb_normal', 'kept_glb_ao', 'factored', 'constant_only' ] ) out[ k ] = ( a[ k ] || 0 ) + ( b[ k ] || 0 );
	for ( const k of [ 'unmatched', 'order', 'colourspace_conflicts', 'failed', 'flat_normal_constant', 'without_uv1' ] )
		out[ k ] = [ ...( a[ k ] || [] ), ...( b[ k ] || [] ) ];
	out.formats = { ...a.formats };
	for ( const [ f, n ] of Object.entries( b.formats || {} ) ) out.formats[ f ] = ( out.formats[ f ] || 0 ) + n;
	out.sets_used = Math.max( a.sets_used || 0, b.sets_used || 0 );
	return out;
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
	// 6b: the mobile tier solves the pixel ratio for a drawing-buffer budget instead of taking the
	// device's own (3 on the named iPhone).  Desktop stays at 1, which is what every capture uses.
	const r = pixelRatioFor( w, h, DEVICE.settings.maxDrawingBufferPx, DEVICE.env.devicePixelRatio );
	if ( Math.abs( renderer.getPixelRatio() - r ) > 1e-3 ) {
		renderer.setPixelRatio( r );
		if ( composer ) composer.setPixelRatio( r );          // EffectComposer caches it; setSize alone would not
	}
	renderer.setSize( w, h, false );
	camera.aspect = w / h;
	camera.updateProjectionMatrix();
	if ( composer ) composer.setSize( w, h );
}

const _lastCamPos = new THREE.Vector3( Infinity, Infinity, Infinity );
function renderFrame() {
	// 6c round 2: the far-tree meshes are only ever DRAWN inside the switch distance, so a chunk whose
	// whole bounding sphere is beyond it is hidden before three sees it.  254 instance rows x ~8 k
	// tris would otherwise be vertex-shaded every frame for fragments the dissolve throws away.
	if ( farTreeUpdate ) farTreeUpdate( camera );
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
		offPlan: [ ...progress.extra.entries() ].map( ( [ url, b ] ) => ( { url, bytes: b } ) ),
		files: progress.files.map( f => ( { kind: f.kind, bytes: f.bytes, sizeFrom: f.sizeFrom, name: f.url.split( '/' ).pop() } ) ) },
	load_s: { ...loadTimes },
	// 6b: which asset tier this device got and why, and how the load tiers streamed.
	device: { tier: DEVICE.tier, from: DEVICE.from, reasons: DEVICE.reasons, gl: DEVICE.gl, env: DEVICE.env,
		pixelRatio: renderer.getPixelRatio(),
		drawingBufferPx: renderer.domElement.width * renderer.domElement.height },
	tiers: { present: tierState.present, count: tierState.count, max: tierState.max === Infinity ? null : tierState.max,
		now: tierState.now, streaming: tierState.streaming, done: tierState.done,
		tier0_planned_bytes: tierState.tier0PlannedBytes, per_tier: tierState.per.slice(),
		declared_bytes: manifest && manifest.tiers ? manifest.tiers.totals : null,
		oversize: manifest && manifest.tiers ? manifest.tiers.oversize : [],
		deferred_lightmaps: tierState.deferredLightmaps, upgrades: tierState.upgrades || [],
		lowres_remaining: tierState.lowresRemaining || [],
		lowres_etc_textures: tierState.lowresEtcTextures ?? null,
		texture_sharing: { urls: textureShare.urls, shared_users: textureShare.shared,
			bytes_saved_estimate: textureShare.bytesSaved },
		stub: tierState.stub, error: tierState.error || null },
	glbs: glbReport.slice(),
	uv_dequant: uvDequantReport.slice(),
	resident: residentBytes(),
	billboards: billboards ? { ...billboards.userData } : null,
	chunking: chunkStats,
	post: postState,
	probeEnv: probeReport,
	// 6c item C.  `units` is dropped (14 Vector3 triples the harness never reads); its count stays.
	foliage: foliageReport && { geometries: foliageReport.geometries, clusters: foliageReport.clusters,
		leafMaterials: foliageReport.leafMaterials, cardMaterials: foliageReport.cardMaterials,
		barkMaterials: foliageReport.barkMaterials, bent: foliageReport.bent, softened: foliageReport.softened,
		normalBlend: foliageReport.normalBlend, trnScale: foliageReport.trnScale, trnShrubs: foliageReport.trnShrubs,
		msaa: foliageReport.msaa, meshDist: Number.isFinite( foliageReport.meshDist ) ? foliageReport.meshDist : null,
		fadeBand: foliageReport.fadeBand, units: foliageReport.units.length, skipped: foliageReport.skipped.length,
		depthMean: foliageReport.depthMean, clustersOver40m: foliageReport.clustersOver40m,
		interior: foliageReport.interior, cardInterior: foliageReport.cardInterior,
		normalGate: foliageReport.normalGate, interiorMaterials: foliageReport.interiorMaterials,
		cardMipBias: foliageReport.cardMipBias, leafMipBias: foliageReport.leafMipBias,
		cardEnv: foliageReport.cardEnv, cardEnvMaterials: foliageReport.cardEnvMaterials,
		cardEnvAlready: foliageReport.cardEnvAlready },
	shrubLod: shrubLodReport,
	impostorModulation: impModReport,
	reflectionSet,
	quality: { preset: CFG.quality, bloomRes: CFG.bloomRes, reflRes: CFG.reflRes, reflSet: CFG.reflSet },
	impostors: impostorReport && { prototypes: impostorReport.prototypes, instances: impostorReport.instances,
		drawCalls: impostorReport.drawCalls, textures: impostorReport.textures, bytes: impostorReport.bytes,
		skipped: impostorReport.skipped.length, missingPrototypes: impostorReport.missingPrototypes,
		// round-1 review 5: the three 6c defaults the info block was missing
		atlas2k: impostorReport.atlas2k, atlasGeometry: impostorReport.drawnGeom,
		nearInstances: impostorReport.nearInstances, modulated: impostorReport.modulated,
		interior: impostorReport.interior },
	farTrees: farTreeReport && { glb: farTreeReport.glb, rows: farTreeReport.rows, joined: farTreeReport.joined,
		placements: farTreeReport.placements, lit: farTreeReport.lit, litFrom: farTreeReport.litFrom,
		ao: farTreeReport.ao, aoEncode: farTreeReport.aoEncode, aoAlphaForced: farTreeReport.aoAlphaForced || 0,
		placementCheck: farTreeReport.placementCheck, drawCalls: farTreeReport.drawCalls,
		tris: farTreeReport.tris, chunks: farTreeReport.chunks, wall_s: farTreeReport.wall_s,
		impostors: farTreeReport.impostors, error: farTreeReport.error,
		set: farTreeReport.set, meshDist: farTreeReport.meshDist,
		walkupFellBack: farTreeReport.walkupFellBack || false, walkupError: farTreeReport.walkupError || null },
	shrubLod1: shrubLod1Report,
	foliageTextures: foliageTexReport && { size: foliageTexReport.size, albedo: foliageTexReport.albedo,
		translucency: foliageTexReport.translucency, materials: foliageTexReport.materials,
		missing: foliageTexReport.missing },
	shaderErrors: shaderErrors.slice(),
	walk: walk ? { ...walk.state } : null,
	materialsMode,
	pbr: pbrReport,
	detail: detailReport,
	notes: log.slice(),
} );

/** Every texture in the scene whose url an earlier tier shipped as a low-resolution stand-in. */
function lowresStillInScene() {
	const up = manifest.tiers && manifest.tiers.upgradeOf;
	if ( ! up || ! up.size ) return [];
	const left = new Set();
	scene.traverse( ( o ) => {
		if ( ! o.isMesh ) return;
		for ( const m of ( Array.isArray( o.material ) ? o.material : [ o.material ] ) ) {
			if ( ! m ) continue;
			for ( const k of [ 'map', 'lightMap', 'aoMap', 'normalMap', 'roughnessMap', 'metalnessMap', 'emissiveMap', 'alphaMap' ] ) {
				const u = m[ k ] && m[ k ].userData && m[ k ].userData.pfaUrl;
				if ( u && up.has( u ) ) left.add( u );
			}
		}
	} );
	return [ ...left ];
}

/** Resident GPU-side bytes we can account for: unique geometries and unique textures in the scene.
 *  renderer.info.memory only counts objects, so this is the viewer's own sum, stated as an estimate:
 *  compressed textures are summed from their mip data, uncompressed ones as w*h*4*(4/3 with mips). */
function residentBytes() {
	const geos = new Set(), texs = new Set(), sources = new Set();
	let geometry = 0, texture = 0, instanceMatrices = 0;
	let sharedTextures = 0;
	const formats = {};
	// Per SOURCE, not per texture object: two Texture clones that share `texture.source` are ONE
	// upload on the GPU (three refcounts the WebGLTexture per source + sampler cache key), so counting
	// them twice would report memory the card never spent.  `textures` still counts the objects.
	const addTex = ( t ) => {
		if ( ! t || texs.has( t ) ) return;
		texs.add( t );
		const src = t.source || t;
		if ( sources.has( src ) ) { sharedTextures ++; return; }
		sources.add( src );
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
		texture_bytes: Math.round( texture ), geometries: geos.size, textures: texs.size,
		texture_sources: sources.size, textures_sharing_a_source: sharedTextures, texture_formats: formats,
		render_target_bytes: rtBytes, render_targets: rts,
		total_bytes: Math.round( geometry + instanceMatrices + texture ) + rtBytes,
		note: 'viewer-side sum, ONE ENTRY PER texture.source (clones that share a source are one GPU '
			+ 'upload); compressed textures from their mip data, uncompressed as w*h*4 (x4/3 with '
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
