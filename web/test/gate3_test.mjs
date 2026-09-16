// Gate 3 (manifest v4) without a browser:
//   PFA_MAIN_ROOT=/path/to/main-checkout node test/gate3_test.mjs
//
// Three things are checked here, because none of them can be checked by looking at a screenshot:
//   1. src/manifest.js parses the REAL export/out/gate3/manifest.json — the own maps with their
//      per-texture encode/range, the `uv2_in_glb: false` fallback to the frozen `_gate1_layout`
//      twin, the 988 slots joined to their atlas, sky.diffuse, the impostor atlases and the probe;
//   2. src/lightmaps.js joins drawn meshes back to manifest assets BY POSITION (gltfpack drops every
//      name), against a synthetic scene built from the manifest's own `location_blender` values —
//      including the material clone when one material serves two different plans and the per-instance
//      slot attribute;
//   3. the shader patches in src/materials.js actually substitute, run against three's own chunks.
//      A `once()` failure is a black building in Chrome and nothing at all in node otherwise.
import { readFileSync, existsSync, writeFileSync, mkdtempSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import * as THREE from 'three';
import { applyGate3Lightmaps } from '../src/lightmaps.js';
import { patchBakedMaterial, decodeGlsl } from '../src/materials.js';
import { b2t } from '../src/blenderCamera.js';

const WEB = path.resolve( fileURLToPath( new URL( '..', import.meta.url ) ) );
const MAIN = process.env.PFA_MAIN_ROOT || path.resolve( WEB, '..' );
let fails = 0;
const check = ( ok, msg ) => { if ( ! ok ) fails ++; console.log( `${ok ? 'PASS' : 'FAIL'}  ${msg}` ); };

// manifest.js imports a .json module; transform it to CJS in memory rather than duplicate it.
const src = readFileSync( path.join( WEB, 'src/manifest.js' ), 'utf8' )
	.replace( /^import stationsFallback.*$/m,
		'const stationsFallback = ' + readFileSync( path.join( WEB, 'src/stations_blender.json' ), 'utf8' ) + ';' )
	.replace( /^export /gm, '' ) + '\nmodule.exports = { normaliseManifest, applyUv2RelayStatus, selectOwnMap };';
const tmp = path.join( mkdtempSync( path.join( os.tmpdir(), 'pfa-gate3-' ) ), 'manifest.cjs' );
writeFileSync( tmp, src );
const { normaliseManifest, applyUv2RelayStatus } = createRequire( import.meta.url )( tmp );

// ---------------------------------------------------------------- 3. the shader patches, always run
{
	const shader = {
		vertexShader: THREE.ShaderLib.physical.vertexShader,
		fragmentShader: THREE.ShaderLib.physical.fragmentShader,
		uniforms: {},
	};
	const mat = new THREE.MeshStandardMaterial();
	mat.lightMap = new THREE.Texture();
	patchBakedMaterial( mat, { lightMapEncoding: 'gamma2', range: 52.07, slot: true, atlasB: new THREE.Texture() } );
	let err = null;
	try { mat.onBeforeCompile( shader, null ); } catch ( e ) { err = e; }
	check( ! err, `slot + gamma2 shader patch substitutes into three ${THREE.REVISION}${err ? `: ${err.message}` : ''}` );
	check( /lightMapTexel.rgb \* lightMapTexel.rgb \* 52.070000/.test( shader.fragmentShader ), 'gamma2 decode is rgb*rgb*range' );
	check( /pfaSlotUv/.test( shader.fragmentShader ) && /attribute vec3 pfaSlot;/.test( shader.vertexShader ),
		'the per-instance slot window reaches both stages' );
	check( ! /iblIrradiance \+= getIBLIrradiance/.test( shader.fragmentShader ), 'env diffuse irradiance removed (the lightmap carries it)' );
	check( !! shader.uniforms.pfaLmAtlasB, 'the second slot atlas is bound as a uniform' );

	const s2 = { vertexShader: THREE.ShaderLib.physical.vertexShader, fragmentShader: THREE.ShaderLib.physical.fragmentShader, uniforms: {} };
	const m2 = new THREE.MeshStandardMaterial(); m2.lightMap = new THREE.Texture();
	patchBakedMaterial( m2, { lightMapEncoding: 'rgbm8', range: 64 } );
	let err2 = null;
	try { m2.onBeforeCompile( s2, null ); } catch ( e ) { err2 = e; }
	check( ! err2 && /lightMapTexel.rgb \* lightMapTexel.a \* 64.000000/.test( s2.fragmentShader ),
		`rgbm8 decode is rgb*a*range${err2 ? `: ${err2.message}` : ''}` );
	check( decodeGlsl( 'linear', 1 ).includes( 'lightMapTexel.rgb * lightMapIntensity' ), 'linear needs no decode' );
}

// ---------------------------------------------------------------- 1 + 2. the real Gate 3 manifest
const g3path = path.join( MAIN, 'export/out/gate3/manifest.json' );
if ( ! existsSync( g3path ) ) {
	console.log( `SKIP  ${g3path} not on disk (the bake has not run in this checkout)` );
	process.exit( fails ? 1 : 0 );
}
const raw = JSON.parse( readFileSync( g3path, 'utf8' ) );
const m = normaliseManifest( raw, `http://localhost/assets/gate3/manifest.json` );
const g3 = m.gate3;

check( m.schema === 'pfa-phase6/4', `schema ${m.schema}` );
check( !! g3, 'the v4 `lightmaps` object is parsed (an array-only parser throws on it)' );
check( m.glbs.length === 4, `${m.glbs.length} glb(s) (4 expected: a v4 regression here means the test scene)` );
check( Math.abs( g3.scale - Math.PI ) < 1e-9, `lightmap scale ${g3.scale} == pi` );
const own = Object.values( g3.ownMaps );
// 16 own-map assets; 7 were re-unwrapped at Gate 3, 2 of those have a frozen-layout twin to fall
// back on, so 11 are usable today and 5 are blocked until the export re-exports their UV2.
check( own.length === 16 && g3.ownCount === 11, `${g3.ownCount}/${own.length} own map(s) resolved to a texture (11 usable, 5 blocked on the UV2 re-export)` );
check( own.filter( a => a.url ).every( a => a.encode === 'gamma2' || a.encode === 'rgbm8' ), 'every resolved own map declares a known encode' );
check( own.filter( a => a.url ).every( a => typeof a.range === 'number' && a.range > 0 ), 'every resolved own map carries its own range' );
check( own.filter( a => a.blocked ).length === 5, `${own.filter( a => a.blocked ).length} asset(s) blocked with a stated reason (5 expected)` );
check( own.filter( a => a.layout === 'gate1_frozen' && a.url ).length === g3.frozenUsed && g3.frozenUsed === 2,
	`${g3.frozenUsed} asset(s) fall back to the frozen Gate 1 layout (2 expected)` );
const relaid = ( raw.lightmaps.uv2_relaid || [] ).length;
check( Object.values( g3.ownMaps ).filter( a => ! a.uv2InGlb ).length === relaid && relaid === 7,
	`${relaid} asset(s) ship uv2_in_glb false (the export re-export)` );
check( g3.slotCount === 988, `${g3.slotCount} per-instance slot(s) (988 expected)` );
check( g3.slotsNoAtlas === 0, `${g3.slotsNoAtlas} slot(s) whose atlas is missing (0 expected)` );
check( Object.keys( g3.atlases ).length === 5 && Object.values( g3.atlases ).every( a => a.url ),
	`${Object.keys( g3.atlases ).length} slot atlas(es), all with a texture` );
check( Object.values( g3.atlases ).every( a => a.uv2Scale > 0 && a.uv2Scale < 0.07 ), 'the slot uv2 scale comes from the manifest, not a constant' );
check( !! m.sky.diffuse && m.sky.diffuse !== m.sky.glossy, 'sky.diffuse is its own equirect (QA-12b-1)' );
check( g3.impostors && g3.impostors.count === 16, `${g3.impostors && g3.impostors.count} impostor prototype(s) (16 expected)` );
check( g3.probe && g3.probe.faces.length === 6, 'the hero probe has six faces' );
check( g3.vertexIrradiance && g3.vertexIrradiance.inGlb === false, 'vertex irradiance is declared NOT in the glb yet' );

// --- uv2_relay_status.json wins over the manifest's own flags -----------------------------------
// The export re-packs the glbs with the re-laid UV2 before the bake rewrites `uv2_in_glb`, so the
// relay file is the live truth.  Checked against the real file when it is on disk.
{
	const relayPath = path.join( MAIN, 'export/out/gate3/uv2_relay_status.json' );
	const m2 = normaliseManifest( raw, 'http://localhost/assets/gate3/manifest.json' );
	const before = m2.gate3.ownCount;
	if ( existsSync( relayPath ) ) {
		const st = applyUv2RelayStatus( m2, JSON.parse( readFileSync( relayPath, 'utf8' ) ) );
		check( st.applied === 7, `${st.applied} re-laid asset(s) checked against the packed glbs (7 expected)` );
		check( m2.gate3.ownCount >= before, `own maps usable ${before} -> ${m2.gate3.ownCount} after the relay status` );
		const relaidNow = Object.values( m2.gate3.ownMaps ).filter( a => a.layout === 'gate3_relaid' && a.url );
		check( relaidNow.length === st.flipped.length,
			`${relaidNow.length} asset(s) now take the Gate 3 re-laid map, matching the ${st.flipped.length} flag(s) flipped` );
		check( relaidNow.every( a => ! /lmg1/.test( a.textureKey || '' ) ),
			'a re-laid asset takes its own Gate 3 map, never the frozen lmg1 twin' );
	} else console.log( 'SKIP  uv2_relay_status.json not on disk yet' );
	// the flag must be able to go BACK: a manifest that says true with a glb that says false
	const m3 = normaliseManifest( raw, 'http://localhost/assets/gate3/manifest.json' );
	const victim = Object.values( m3.gate3.ownMaps ).find( a => a.uv2InGlb && a.url && ! a.relaid );
	applyUv2RelayStatus( m3, { uv2: { X: { asset: victim.name, uv2_in_glb: false } } } );
	check( ! m3.gate3.ownMaps[ victim.name ].url && !! m3.gate3.ownMaps[ victim.name ].blocked,
		'a glb that does NOT carry UV2 removes the map rather than applying the wrong layout' );
}

// --- the position join, on a synthetic scene ---------------------------------------------------
// One mesh per own-map asset and one InstancedMesh per instanced mesh, each placed so its world
// bounding-box centre IS the manifest's `location_blender`.  A shared material across two different
// plans is deliberate: it must be cloned.
function meshAt( centre, material, uv2 = true ) {
	const g = new THREE.BoxGeometry( 1, 1, 1 );
	if ( ! uv2 ) g.deleteAttribute( 'uv' ); else g.setAttribute( 'uv1', g.attributes.uv.clone() );
	const o = new THREE.Mesh( g, material );
	o.position.copy( centre );
	return o;
}
const scene = new THREE.Scene();
const sharedMat = () => { const x = new THREE.MeshStandardMaterial(); x.name = 'MAT_EXP_shared'; return x; };
const matA = sharedMat();
for ( const a of own ) {
	const loc = raw.assets[ a.name ].location_blender;
	scene.add( meshAt( b2t( ...loc ), matA ) );
}
// the instanced side: group the slot objects by their manifest mesh
const byMesh = new Map();
for ( const name of Object.keys( g3.slots ) ) {
	const mesh = raw.assets[ name ].mesh;
	if ( ! byMesh.has( mesh ) ) byMesh.set( mesh, [] );
	byMesh.get( mesh ).push( name );
}
for ( const [ meshName, names ] of byMesh ) {
	const g = new THREE.BoxGeometry( 1, 1, 1 );
	g.setAttribute( 'uv1', g.attributes.uv.clone() );
	const im = new THREE.InstancedMesh( g, matA, names.length );
	names.forEach( ( n, i ) => {
		const p = b2t( ...raw.assets[ n ].location_blender );
		im.setMatrixAt( i, new THREE.Matrix4().makeTranslation( p.x, p.y, p.z ) );
	} );
	im.name = meshName;
	scene.add( im );
}
const notes = [];
const rep = applyGate3Lightmaps( {
	scene, gate3: g3, assets: raw.assets, note: ( s ) => notes.push( s ),
	loadTexture: async ( url ) => { const t = new THREE.Texture(); t.name = url.split( '/' ).pop(); return t; },
} );
await rep.promise;
check( rep.own.matched === 11 && rep.own.applied === 11, `own maps: ${rep.own.matched} matched, ${rep.own.applied} applied (11/11 usable)` );
check( rep.own.maxMatchError_m < 1e-6, `own-map position join exact (max ${rep.own.maxMatchError_m.toExponential( 2 )} m)` );
check( rep.slots.matched === 988 && rep.slots.unmatched === 0, `slots: ${rep.slots.matched} matched, ${rep.slots.unmatched} unmatched (988/0)` );
check( rep.slots.applied === 988, `slots applied to ${rep.slots.applied} instance(s)` );
check( rep.materialsCloned === 11 + byMesh.size - 1,
	`${rep.materialsCloned} material clone(s): one material cannot carry two different lightmap plans` );
const straddling = rep.slots.meshes.filter( x => x.atlases.length > 1 );
check( straddling.length === 3, `${straddling.length} mesh(es) straddle two slot atlases (3 expected: astragals, rotunda columns, ORN drum band)` );
// every lightmapped material must decode with ITS OWN range, never a default
const ranges = new Set();
scene.traverse( ( o ) => { if ( o.isMesh && o.material.userData.pfaPatched ) ranges.add( o.material.userData.pfaPatched.maxRange ); } );
check( ! ranges.has( 7 ) && ! ranges.has( undefined ) && ranges.size > 3,
	`${ranges.size} distinct per-texture range(s) in use, none of them three's 7.0 default` );
// the slot attribute really is per instance
const im0 = scene.children.find( o => o.isInstancedMesh && o.geometry.attributes.pfaSlot );
check( !! im0 && im0.geometry.attributes.pfaSlot.isInstancedBufferAttribute
	&& im0.geometry.attributes.pfaSlot.count === im0.count, 'pfaSlot is an InstancedBufferAttribute, one window per instance' );

// --- the blocker: a glb with no TEXCOORD_1 must apply NOTHING, loudly --------------------------
{
	const s2 = new THREE.Scene();
	const mat = sharedMat();
	for ( const a of own ) s2.add( meshAt( b2t( ...raw.assets[ a.name ].location_blender ), mat, false ) );
	const n2 = [];
	const r2 = applyGate3Lightmaps( { scene: s2, gate3: g3, assets: raw.assets, note: ( s ) => n2.push( s ),
		loadTexture: async () => new THREE.Texture() } );
	await r2.promise;
	check( r2.own.matched === 11 && r2.own.applied === 0 && r2.own.noUv2Attribute === 11,
		`a glb without TEXCOORD_1 applies 0 map(s) and reports all 11 (got ${r2.own.applied} applied, ${r2.own.noUv2Attribute} reported)` );
	check( n2.some( s => /NO TEXCOORD_1/.test( s ) ), 'and says so in the notes' );
}

console.log( fails ? `${fails} check(s) FAILED` : 'all gate3 checks passed' );
process.exit( fails ? 1 : 0 );
