// Gate 3 baked lighting: the manifest v4 `lightmaps` block applied to the loaded glbs.
//
// IDENTITY.  `gltfpack -mi` drops every node and mesh name, so a drawn mesh carries no clue about
// which manifest asset it is.  The manifest's `assets[<name>].location_blender` is each asset's world
// bounding-box CENTRE, so this module matches the other way round: it computes the world bbox centre
// of every drawn mesh (and of every instance of an InstancedMesh) and looks it up in a 2 m grid of
// the manifest's centres.  The match distance is measured and reported, so a wrong join shows up as a
// number instead of as a dark building.
//
// TWO KINDS OF MAP.
//   * `mode: "asset"`  (16 single-use masses)  - one 2K/4K map per object on its own UV2.
//   * `mode: "slot"`   (988 instances)         - a 256 px slot on a shared 4K atlas, addressed by a
//     per-instance `pfaSlot = (offset.u, offset.v, scale)` attribute.  Three meshes straddle two
//     atlases (colonnade astragals, rotunda columns, ORN drum band); those instances also carry
//     `pfaSlotB = 1` and the material samples the second atlas.
//
// MATERIAL SPLITTING.  One glb material serves several assets with different plans (the colonnade
// material is on the merged mass AND on the astragals), so a material is CLONED the moment a second
// mesh wants a different plan from it.  Clones keep the material's name, which is what the Gate 2 PBR
// and detail passes match on, so they must run AFTER this one and they then texture every clone.
//
// WHAT BLOCKS IT.  A lightmap needs UV2.  `gltfpack` prunes a vertex attribute no material references,
// so the Gate 1 glbs carry no TEXCOORD_1 at all even where the source .gltf had one; and an asset with
// `uv2_in_glb: false` carries a UV2 that is not the layout its map was baked on.  Both cases are
// counted and reported here, and the affected material is left on the environment-lit path rather than
// rendered with a map that does not belong to it.
import * as THREE from 'three';
import { b2t } from './blenderCamera.js';
import { patchBakedMaterial, attachLightMap } from './materials.js';

const CELL = 2.0;                       // m, the match grid's cell size
const MAX_MATCH_M = 1.5;                // m, beyond this a candidate is not the same object

function key( x, y, z ) { return `${Math.round( x / CELL )},${Math.round( y / CELL )},${Math.round( z / CELL )}`; }

/** Grid of manifest asset centres (three space) -> asset names. */
function centreGrid( assets, wanted ) {
	const grid = new Map();
	const centres = new Map();
	for ( const name of wanted ) {
		const a = assets && assets[ name ];
		const loc = a && a.location_blender;
		if ( ! Array.isArray( loc ) || loc.length !== 3 ) continue;
		const p = b2t( loc[ 0 ], loc[ 1 ], loc[ 2 ] );
		centres.set( name, p );
		const k = key( p.x, p.y, p.z );
		if ( ! grid.has( k ) ) grid.set( k, [] );
		grid.get( k ).push( name );
	}
	return { grid, centres };
}

/** Nearest manifest asset to a world point, searching the 27 cells around it. */
function nearest( idx, p, taken ) {
	let best = null, bestD = Infinity;
	const cx = Math.round( p.x / CELL ), cy = Math.round( p.y / CELL ), cz = Math.round( p.z / CELL );
	for ( let i = - 1; i <= 1; i ++ ) for ( let j = - 1; j <= 1; j ++ ) for ( let k = - 1; k <= 1; k ++ ) {
		const list = idx.grid.get( `${cx + i},${cy + j},${cz + k}` );
		if ( ! list ) continue;
		for ( const name of list ) {
			if ( taken && taken.has( name ) ) continue;
			const d = idx.centres.get( name ).distanceTo( p );
			if ( d < bestD ) { bestD = d; best = name; }
		}
	}
	return { name: best, d: bestD };
}

const _box = new THREE.Box3(), _v = new THREE.Vector3(), _m = new THREE.Matrix4();

/** World bounding-box centre of a mesh, or of instance `i` of an InstancedMesh. */
function worldCentre( mesh, i ) {
	if ( ! mesh.geometry.boundingBox ) mesh.geometry.computeBoundingBox();
	_box.copy( mesh.geometry.boundingBox );
	if ( i === undefined ) return _box.applyMatrix4( mesh.matrixWorld ).getCenter( new THREE.Vector3() );
	_m.fromArray( mesh.instanceMatrix.array, i * 16 ).premultiply( mesh.matrixWorld );
	return _box.applyMatrix4( _m ).getCenter( new THREE.Vector3() );
}

/**
 * @param {{ scene:THREE.Object3D, gate3:object, assets:object, loadTexture:(url:string)=>Promise<THREE.Texture>,
 *           note:(s:string)=>void, onTexture?:Function }} o
 * @returns {object} the report that goes into __pfaInfo().gate3
 */
export function applyGate3Lightmaps( o ) {
	const { scene, gate3, assets, loadTexture, note } = o;
	const report = {
		own: { matched: 0, applied: 0, blockedNoUv2InGlb: 0, noUv2Attribute: 0, unmatched: 0, maxMatchError_m: 0, assets: {} },
		slots: { instances: 0, matched: 0, applied: 0, single: 0, noUv2Attribute: 0, unmatched: 0, maxMatchError_m: 0, meshes: [] },
		materialsCloned: 0, texturesRequested: 0, texturesLoaded: 0, texturesFailed: [],
		meshesSeen: 0, instancedMeshesSeen: 0,
	};
	if ( ! gate3 ) return report;

	const ownReady = Object.values( gate3.ownMaps ).filter( m => m.url );
	const ownIdx = centreGrid( assets, ownReady.map( m => m.name ) );
	const slotIdx = centreGrid( assets, Object.keys( gate3.slots ) );
	const ownTaken = new Set(), slotTaken = new Set();

	// ---- pass 1: decide a plan per drawn mesh -------------------------------------------------
	const plans = [];                      // { mesh, kind, ... }
	scene.updateMatrixWorld( true );
	scene.traverse( ( mesh ) => {
		if ( ! mesh.isMesh || ! mesh.visible ) return;
		const hasUv2 = !! mesh.geometry.attributes.uv1;
		if ( mesh.isInstancedMesh ) {
			report.instancedMeshesSeen ++;
			const n = mesh.count;
			const off = new Float32Array( n * 3 ), sel = new Float32Array( n );
			const atlasKeys = new Set();
			let matched = 0, maxD = 0;
			for ( let i = 0; i < n; i ++ ) {
				const hit = nearest( slotIdx, worldCentre( mesh, i ) );
				if ( ! hit.name || hit.d > MAX_MATCH_M ) continue;
				const s = gate3.slots[ hit.name ];
				slotTaken.add( hit.name );
				off[ i * 3 ] = s.offset[ 0 ]; off[ i * 3 + 1 ] = s.offset[ 1 ]; off[ i * 3 + 2 ] = s.scale;
				atlasKeys.add( s.atlasKey );
				matched ++; if ( hit.d > maxD ) maxD = hit.d;
			}
			if ( ! matched ) return;
			report.slots.instances += n; report.slots.matched += matched;
			report.slots.unmatched += n - matched;
			report.slots.maxMatchError_m = Math.max( report.slots.maxMatchError_m, maxD );
			const keys = [ ...atlasKeys ];
			// The second atlas, for the three meshes whose instances straddle one.
			if ( keys.length > 1 ) {
				for ( let i = 0; i < n; i ++ ) {
					const hit = nearest( slotIdx, worldCentre( mesh, i ) );
					if ( hit.name && hit.d <= MAX_MATCH_M && gate3.slots[ hit.name ].atlasKey === keys[ 1 ] ) sel[ i ] = 1;
				}
			}
			report.slots.meshes.push( { atlases: keys, instances: n, matched,
				match_max_m: Math.round( maxD * 1000 ) / 1000, uv2: hasUv2 } );
			if ( ! hasUv2 ) { report.slots.noUv2Attribute += matched; return; }
			plans.push( { mesh, kind: 'slot', atlasKeys: keys, off, sel, matched, maxD } );
		} else {
			report.meshesSeen ++;
			const centre = worldCentre( mesh );
			const hit = nearest( ownIdx, centre, ownTaken );
			if ( hit.name && hit.d <= MAX_MATCH_M ) {
				ownTaken.add( hit.name );
				report.own.matched ++;
				report.own.maxMatchError_m = Math.max( report.own.maxMatchError_m, hit.d );
				if ( ! hasUv2 ) { report.own.noUv2Attribute ++; report.own.assets[ hit.name ] = 'no TEXCOORD_1 in the glb'; return; }
				plans.push( { mesh, kind: 'own', name: hit.name, d: hit.d } );
				return;
			}
			// gltfpack collapses a mesh with ONE placement into a plain node, so a slot object can
			// arrive as an ordinary Mesh.  Same shader path, with the window as a constant vertex
			// attribute instead of a per-instance one - no texture clone, so no second 4K upload.
			const s = nearest( slotIdx, centre, slotTaken );
			if ( ! s.name || s.d > MAX_MATCH_M ) return;
			slotTaken.add( s.name );
			report.slots.instances ++; report.slots.matched ++; report.slots.single ++;
			report.slots.maxMatchError_m = Math.max( report.slots.maxMatchError_m, s.d );
			if ( ! hasUv2 ) { report.slots.noUv2Attribute ++; return; }
			const sl = gate3.slots[ s.name ];
			const nv = mesh.geometry.attributes.position.count;
			const off = new Float32Array( nv * 3 ), sel = new Float32Array( nv );
			for ( let i = 0; i < nv; i ++ ) { off[ i * 3 ] = sl.offset[ 0 ]; off[ i * 3 + 1 ] = sl.offset[ 1 ]; off[ i * 3 + 2 ] = sl.scale; }
			plans.push( { mesh, kind: 'slot', single: true, atlasKeys: [ sl.atlasKey ], off, sel, matched: 1, maxD: s.d } );
		}
	} );
	report.own.unmatched = ownReady.length - report.own.matched;
	report.own.blockedNoUv2InGlb = gate3.blockedNoUv2;

	// ---- pass 2: give every planned mesh a material that is exclusive to its plan --------------
	const planKey = ( p ) => ( p.kind === 'own' ? `own:${p.name}` : `slot:${p.atlasKeys.join( '+' )}` );
	const claimed = new Map();             // material -> planKey
	for ( const p of plans ) {
		const mats = Array.isArray( p.mesh.material ) ? p.mesh.material : [ p.mesh.material ];
		if ( mats.length !== 1 || ! mats[ 0 ] || ! mats[ 0 ].isMeshStandardMaterial ) { p.skip = 'not a single MeshStandardMaterial'; continue; }
		let m = mats[ 0 ];
		const k = planKey( p );
		if ( claimed.has( m ) && claimed.get( m ) !== k ) {
			const c = m.clone();             // keeps `name`: the PBR and detail passes still match it
			c.userData = { ...m.userData };
			p.mesh.material = c; m = c;
			report.materialsCloned ++;
		}
		claimed.set( m, k );
		p.material = m;
	}

	// ---- pass 3: attributes, shader patch, textures --------------------------------------------
	const texCache = new Map();
	const fetch = ( url ) => {
		if ( ! texCache.has( url ) ) {
			report.texturesRequested ++;
			texCache.set( url, loadTexture( url ).then( ( t ) => { report.texturesLoaded ++; return t; } )
				.catch( ( e ) => { report.texturesFailed.push( `${url.split( '/' ).pop()}: ${e.message}` ); return null; } ) );
		}
		return texCache.get( url );
	};
	const pending = [];
	for ( const p of plans ) {
		if ( ! p.material ) continue;
		if ( p.kind === 'own' ) {
			const lm = gate3.ownMaps[ p.name ];
			patchBakedMaterial( p.material, { lightMapEncoding: lm.encode, range: lm.range } );
			pending.push( fetch( lm.url ).then( ( t ) => {
				if ( ! t ) return;
				attachLightMap( p.material, t, gate3.scale );
				report.own.applied ++;
				report.own.assets[ p.name ] = `${lm.encode} range ${lm.range.toFixed( 2 )} layout ${lm.layout} (match ${p.d.toFixed( 3 )} m)`;
			} ) );
		} else {
			// The per-instance window lives on the GEOMETRY, and chunking hands each chunk its own
			// slice (chunking.js), so a geometry shared by two InstancedMeshes is cloned first.
			let geo = p.mesh.geometry;
			if ( geo.attributes.pfaSlot ) { geo = geo.clone(); p.mesh.geometry = geo; }
			const Attr = p.single ? THREE.BufferAttribute : THREE.InstancedBufferAttribute;
			geo.setAttribute( 'pfaSlot', new Attr( p.off, 3 ) );
			geo.setAttribute( 'pfaSlotB', new Attr( p.sel, 1 ) );
			const a = gate3.atlases[ p.atlasKeys[ 0 ] ];
			const b = p.atlasKeys[ 1 ] ? gate3.atlases[ p.atlasKeys[ 1 ] ] : null;
			const mat = p.material;
			pending.push( Promise.all( [ fetch( a.url ), b ? fetch( b.url ) : Promise.resolve( null ) ] ).then( ( [ ta, tb ] ) => {
				if ( ! ta ) return;
				// The patch must know the second sampler before the program is built.
				patchBakedMaterial( mat, { lightMapEncoding: a.encode, range: a.range, slot: true, atlasB: tb || ta } );
				attachLightMap( mat, ta, gate3.scale );
				if ( tb ) { tb.flipY = false; tb.colorSpace = THREE.NoColorSpace; tb.needsUpdate = true; }
				mat.needsUpdate = true;
				report.slots.applied += p.matched;
			} ) );
		}
	}

	report.promise = Promise.all( pending ).then( () => {
		note( `gate3 lightmaps: ${report.own.applied}/${ownReady.length} own map(s), `
			+ `${report.slots.applied}/${gate3.slotCount} instance slot(s), ${report.materialsCloned} material(s) cloned; `
			+ `match error <= ${Math.max( report.own.maxMatchError_m, report.slots.maxMatchError_m ).toFixed( 3 )} m` );
		if ( report.own.noUv2Attribute || report.slots.noUv2Attribute )
			note( `gate3 BLOCKED: ${report.own.noUv2Attribute} own map(s) and ${report.slots.noUv2Attribute} instance(s) matched an asset `
				+ `but their glb mesh carries NO TEXCOORD_1 (gltfpack prunes an unreferenced attribute: the re-export needs -kv). `
				+ `They stay on the environment-lit path.` );
		if ( report.own.blockedNoUv2InGlb )
			note( `gate3: ${report.own.blockedNoUv2InGlb} asset(s) have uv2_in_glb false with no frozen-layout twin — no map applied (there is no factor fallback for a lightmap)` );
		if ( report.texturesFailed.length ) note( `gate3: ${report.texturesFailed.length} lightmap texture(s) failed: ${report.texturesFailed.slice( 0, 4 ).join( '; ' )}` );
		return report;
	} );
	return report;
}
