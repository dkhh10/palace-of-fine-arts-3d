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
// Vertex irradiance is identified by COLOR_0, not by position, so the position join only has to pick
// WHICH tree; a thinned LOD1 canopy's bbox centre sits further from the asset's than a mass's does.
const VERTEX_MATCH_M = 12.0;

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
	const flipV = !! o.flipV;
	// ?lmenc= forces the decode for a measurement pass; the manifest's own `encode` is the default and
	// the only thing a capture ever ships with.
	const encOf = ( e ) => o.encodeOverride || e;
	// Phase 6b: a lightmap whose file belongs to a LATER load tier is not attached and its material is
	// not patched — it stays on the environment path (three's own lighting), which is what every
	// material without a baked map already does, instead of being patched specular-only and rendering
	// black while it waits.  The pass is re-run when that tier lands (it re-plans from scratch and is
	// idempotent: a material it cloned last time is already the mesh's own, so nothing clones twice).
	// Phase 9 (B.6): the specular gate's constants, or null.  It reaches ONLY the two lightmap patches
	// below — a material without a lightmap has no visibility to read and is left untouched.
	const specGate = o.specGate || null;
	const tierOf = o.tierOf || ( () => 0 );
	const maxTier = o.maxTier ?? Infinity;
	const report = {
		deferred: [], maxTier,
		own: { matched: 0, applied: 0, blockedNoUv2InGlb: 0, noUv2Attribute: 0, unmatched: 0, maxMatchError_m: 0, assets: {}, nearMiss: {} },
		slots: { instances: 0, matched: 0, applied: 0, single: 0, noUv2Attribute: 0, unmatched: 0, maxMatchError_m: 0, meshes: [] },
		specGate: specGate ? { openSkyB: specGate.openSkyB, skyRedOverBlue: specGate.skyRedOverBlue,
			sunIrrOverPi: specGate.sunIrrOverPi } : null,
		materialsCloned: 0, texturesRequested: 0, texturesLoaded: 0, texturesFailed: [],
		meshesSeen: 0, instancedMeshesSeen: 0,
		// the UV2 census: a lightmap can only attach to a mesh that carries TEXCOORD_1, and gltfpack
		// prunes it unless the pack ran with -kv, so the count is reported every load.
		uv2: { meshesWithUv2: 0, meshesWithoutUv2: 0, drawnWithUv2: 0, drawnWithoutUv2: 0 },
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
		const placements = mesh.isInstancedMesh ? mesh.count : 1;
		if ( hasUv2 ) { report.uv2.meshesWithUv2 ++; report.uv2.drawnWithUv2 += placements; }
		else { report.uv2.meshesWithoutUv2 ++; report.uv2.drawnWithoutUv2 += placements; }
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
				// A mesh with NO TEXCOORD_1 must not CLAIM the asset: env.glb carries no UV2 at all and
				// several of its meshes sit within the tolerance of a ground asset's centre (measured:
				// ENV_ground_colonnade_walk was being taken by an env mesh, so the colonnade walk lost
				// its baked shade and cam03 read 2.5x the Cycles frame).  Leave the asset unclaimed so
				// the mesh that CAN carry it still gets it, and report the near miss.
				if ( ! hasUv2 ) {
					if ( ! report.own.nearMiss[ hit.name ] ) {
						report.own.noUv2Attribute ++;
						report.own.nearMiss[ hit.name ] = `a mesh ${hit.d.toFixed( 2 )} m away carries no TEXCOORD_1`;
					}
				} else {
					ownTaken.add( hit.name );
					report.own.matched ++;
					report.own.maxMatchError_m = Math.max( report.own.maxMatchError_m, hit.d );
					plans.push( { mesh, kind: 'own', name: hit.name, d: hit.d } );
					return;
				}
			}
			// gltfpack collapses a mesh with ONE placement into a plain node, so a slot object can
			// arrive as an ordinary Mesh.  Same shader path, with the window as a constant vertex
			// attribute instead of a per-instance one - no texture clone, so no second 4K upload.
			const s = nearest( slotIdx, centre, slotTaken );
			if ( ! s.name || s.d > MAX_MATCH_M ) return;
			if ( ! hasUv2 ) { report.slots.noUv2Attribute ++; return; }   // same rule: do not claim it
			slotTaken.add( s.name );
			report.slots.instances ++; report.slots.matched ++; report.slots.single ++;
			report.slots.maxMatchError_m = Math.max( report.slots.maxMatchError_m, s.d );
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
	const appliedNames = new Set();
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
		if ( ! p.mesh.geometry.attributes.uv1 ) {            // belt and braces: never attach without UV2
			note( `gate3: refusing to attach a lightmap to a mesh with no uv1 attribute (${p.kind})` );
			continue;
		}
		if ( p.kind === 'own' ) {
			const lm = gate3.ownMaps[ p.name ];
			const t = tierOf( lm.url );
			if ( t > maxTier ) { report.deferred.push( { kind: 'own', name: p.name, url: lm.url, tier: t } ); continue; }
			patchBakedMaterial( p.material, { lightMapEncoding: encOf( lm.encode ), range: lm.range, flipV, specGate } );
			pending.push( fetch( lm.url ).then( ( t ) => {
				if ( ! t ) return;
				attachLightMap( p.material, t, gate3.scale );
				report.own.applied ++;
				appliedNames.add( p.name );
				report.own.assets[ p.name ] = `${lm.encode} range ${lm.range.toFixed( 2 )} layout ${lm.layout} (match ${p.d.toFixed( 3 )} m)`;
			} ) );
		} else {
			const a = gate3.atlases[ p.atlasKeys[ 0 ] ];
			const b = p.atlasKeys[ 1 ] ? gate3.atlases[ p.atlasKeys[ 1 ] ] : null;
			// The tier test comes BEFORE the geometry work: a deferred plan must leave the mesh exactly
			// as it found it, or the re-run at the next tier would clone the geometry a second time.
			const at = Math.max( tierOf( a.url ), b ? tierOf( b.url ) : 0 );
			if ( at > maxTier ) { report.deferred.push( { kind: 'slot', name: p.atlasKeys.join( '+' ), url: a.url, tier: at } ); continue; }
			// The per-instance window lives on the GEOMETRY, and chunking hands each chunk its own
			// slice (chunking.js), so a geometry shared by two InstancedMeshes is cloned first.
			let geo = p.mesh.geometry;
			if ( geo.attributes.pfaSlot ) { geo = geo.clone(); p.mesh.geometry = geo; }
			const Attr = p.single ? THREE.BufferAttribute : THREE.InstancedBufferAttribute;
			geo.setAttribute( 'pfaSlot', new Attr( p.off, 3 ) );
			geo.setAttribute( 'pfaSlotB', new Attr( p.sel, 1 ) );
			const mat = p.material;
			pending.push( Promise.all( [ fetch( a.url ), b ? fetch( b.url ) : Promise.resolve( null ) ] ).then( ( [ ta, tb ] ) => {
				if ( ! ta ) return;
				// The patch must know the second sampler before the program is built.
				patchBakedMaterial( mat, { lightMapEncoding: encOf( a.encode ), range: a.range, slot: true, atlasB: tb || ta, flipV, specGate } );
				attachLightMap( mat, ta, gate3.scale );
				if ( tb ) { tb.flipY = false; tb.colorSpace = THREE.NoColorSpace; tb.needsUpdate = true; }
				mat.needsUpdate = true;
				report.slots.applied += p.matched;
			} ) );
		}
	}

	// ---- pass 3: vertex irradiance on the 14 near trees -------------------------------------
	// COLOR_0 in env.glb carries each vertex's BAKED irradiance, gamma-2 at a per-mesh range, so these
	// meshes leave the environment-lit path exactly as a lightmapped mass does.  The join is the same
	// world-bbox-centre lookup; the range is per mesh and never shared (manifest v4 says so twice).
	// `skipIrradiance` is the tier re-run: both passes already ran at tier 0 over the same meshes and
	// they write vertex attributes and uniforms, so running them again would cost the same traversal
	// for no change.  (A tier that ADDS meshes re-runs them on the new root instead.)
	if ( o.skipIrradiance ) report.vertexIrradiance = null;
	else report.vertexIrradiance = applyVertexIrradiance( scene, gate3, assets, note, o.vertexIrr );

	// ---- pass 4: per-placement irradiance on the 1 379 shrub/reed cards (Gate 4 item 1c) -----
	// v5 ships the block re-keyed PER GROUP (a glTF node index only means anything inside the glb it
	// indexes, and env is several glbs now).  `instanceGroups` is what the caller resolved: the id,
	// that group's nodes, and the root they are in.  One call per group, one merged report.
	if ( o.skipIrradiance ) report.instanceIrradiance = null;
	else if ( Array.isArray( o.instanceGroups ) && o.instanceGroups.length ) {
		const merged = { wanted: 0, nodes: 0, rows: 0, dark: 0, materials: 0, missing: [], errors: [],
			enabled: false, groups: [], covScale: null, covMean: null };
		for ( const grp of o.instanceGroups ) {
			const block = { ...gate3.instanceIrradiance, nodes: grp.nodes, placements: grp.placements };
			const r = applyInstanceIrradiance( scene, gate3, note, o.instIrr,
				{ covScale: o.shrubCov, root: grp.root, block, label: `gate4 instance irradiance [${grp.id}]` } );
			for ( const k of [ 'wanted', 'nodes', 'rows', 'dark', 'materials' ] ) merged[ k ] += r[ k ] || 0;
			merged.missing.push( ...( r.missing || [] ).map( ( n ) => `${grp.id}:${n}` ) );
			merged.errors.push( ...( r.errors || [] ) );
			merged.covScale = r.covScale; merged.covMean = r.covMean;
			merged.groups.push( { id: grp.id, nodes: r.nodes, rows: r.rows, missing: ( r.missing || [] ).length } );
		}
		merged.enabled = merged.nodes > 0 && ! merged.errors.length;
		note( `gate4 instance irradiance: ${merged.rows}/${merged.wanted} placement(s) over ${merged.nodes} node(s) `
			+ `in ${o.instanceGroups.length} group(s) [${merged.groups.map( ( g ) => `${g.id} ${g.rows}` ).join( ', ' )}], `
			+ `${merged.materials} material(s) patched, ${merged.dark} with cov == 0 left on the probe` );
		report.instanceIrradiance = merged;
	} else report.instanceIrradiance = applyInstanceIrradiance( scene, gate3, note, o.instIrr, { covScale: o.shrubCov } );

	report.promise = Promise.all( pending ).then( () => {
		note( `gate3 UV2 census: ${report.uv2.meshesWithUv2} mesh(es) carry TEXCOORD_1 (${report.uv2.drawnWithUv2} placements), `
			+ `${report.uv2.meshesWithoutUv2} do not (${report.uv2.drawnWithoutUv2} placements)` );
		note( `gate3 lightmaps: ${report.own.applied}/${ownReady.length} own map(s), `
			+ `${report.slots.applied}/${gate3.slotCount} instance slot(s), ${report.materialsCloned} material(s) cloned; `
			+ `match error <= ${Math.max( report.own.maxMatchError_m, report.slots.maxMatchError_m ).toFixed( 3 )} m` );
		if ( report.own.applied < ownReady.length )
			note( `gate3 own maps NOT applied: ${ownReady.filter( m => ! appliedNames.has( m.name ) ).map( m => m.name ).join( ', ' )}` );
		if ( report.own.noUv2Attribute || report.slots.noUv2Attribute )
			note( `gate3 near misses: ${report.own.noUv2Attribute} own asset(s) and ${report.slots.noUv2Attribute} instance(s) had a mesh with NO `
				+ `TEXCOORD_1 inside the match tolerance (env.glb carries none at all). The asset is left unclaimed for a mesh that can carry it: `
				+ Object.entries( report.own.nearMiss ).map( ( [ k, v ] ) => `${k} (${v})` ).join( '; ' ) );
		if ( report.own.blockedNoUv2InGlb )
			note( `gate3: ${report.own.blockedNoUv2InGlb} asset(s) have uv2_in_glb false with no frozen-layout twin — no map applied (there is no factor fallback for a lightmap)` );
		if ( report.texturesFailed.length ) note( `gate3: ${report.texturesFailed.length} lightmap texture(s) failed: ${report.texturesFailed.slice( 0, 4 ).join( '; ' )}` );
		if ( report.deferred.length ) note( `gate3: ${report.deferred.length} lightmap(s) deferred to a later load tier `
			+ `(max tier now ${maxTier}): ${[ ...new Set( report.deferred.map( d => `${d.name} @${d.tier}` ) ) ].slice( 0, 6 ).join( ', ' )}`
			+ `${report.deferred.length > 6 ? ' …' : ''}. Those materials stay on the environment path until their tier lands.` );
		const ai = report.instanceIrradiance;
		if ( ai && ai.errors.length ) throw new Error( `gate4 instance irradiance: ${ai.errors.join( '; ' )}` );
		const v = report.vertexIrradiance;
		if ( v && v.applied && v.mode === 'global' )
			note( `gate3 vertex irradiance: ${v.applied} COLOR_0 primitive(s), ${v.placements} placement(s), decoded at the ONE `
				+ `global range ${v.globalRange.toFixed( 5 )} x scale ${gate3.scale.toFixed( 5 )} `
				+ `read from ${gate3.vertexIrradiance.rangeFrom}`
				+ ( gate3.vertexIrradiance.rangeSource ? `; the export derived it as ${gate3.vertexIrradiance.rangeSource}` : '' )
				+ `; gltfpack's shared buffers are harmless at one range` );
		else if ( v && v.wanted && ! v.error )
			note( `gate3 vertex irradiance: ${v.applied}/${v.wanted} near-tree mesh(es) take COLOR_0 as baked irradiance `
				+ `(range ${v.rangeMin.toFixed( 3 )}..${v.rangeMax.toFixed( 3 )}, x scale ${gate3.scale.toFixed( 5 )}); `
				+ `${v.candidates} mesh(es) carry COLOR_0, ${v.instanced} of them batched, ${v.unmatchedMesh} unmatched by position` );
		return report;
	} );
	return report;
}


/**
 * The 14 near trees: `COLOR_0` is baked irradiance (gamma-2, per-mesh range), not a vertex tint.
 * Joined to the manifest asset by world bounding-box centre, exactly like an own map.
 */
export function applyVertexIrradiance( scene, gate3, assets, note = () => {}, mode = 'auto' ) {
	const out = { wanted: 0, matched: 0, applied: 0, unmatched: 0, noColorAttribute: 0, candidates: 0,
		instanced: 0, unmatchedMesh: 0, placements: 0, mode: 'per-mesh', globalRange: 0, error: null,
		maxMatchError_m: 0, rangeMin: Infinity, rangeMax: - Infinity, meshes: [] };
	const vi = gate3 && gate3.vertexIrradiance;
	const byAsset = vi && vi.byAsset;
	if ( mode === '0' || ! vi || ! vi.inGlb ) return out;
	// NEVER a fallback to a guess: a wrong range is a ~90x error in irradiance, so if neither the
	// manifest nor the relay states one, nothing is decoded and the reason is reported.
	const globalRange = ( typeof vi.range === 'number' && vi.range > 0 && ! vi.rangeConflict ) ? vi.range : 0;
	if ( ! globalRange && ( ! byAsset || ! Object.keys( byAsset ).length ) ) {
		out.error = vi.rangeConflict ? `conflicting global ranges ${vi.rangeConflict.join( ', ' )}`
			: 'COLOR_0 is in the glb but no range is stated (lightmaps.vertex_irradiance.range)';
		note( `gate3 vertex irradiance REFUSED: ${out.error}. Nothing decoded - a wrong range is a ~90x error.` );
		return out;
	}
	out.wanted = vi.meshes || Object.keys( byAsset || {} ).length;
	const idx = centreGrid( assets, Object.keys( byAsset || {} ) );
	const taken = new Set();
	const todo = [];
	// The CANDIDATE SET is `COLOR_0 itself`, not a position guess: only these 14 meshes carry a colour
	// attribute in the whole export (ORN's `cavity` was deliberately stripped so it could not be
	// mistaken for one), so the attribute identifies them and the position join only has to say WHICH
	// tree each is.  The tolerance is therefore generous and the worst distance is reported.
	const cands = [];
	scene.traverse( ( mesh ) => {
		if ( ! mesh.isMesh || ! mesh.visible ) return;
		if ( ! mesh.geometry.attributes.color ) return;
		if ( mesh.material && mesh.material.userData.pfaPatched ) return;   // already a lightmapped mass
		cands.push( mesh );
	} );
	out.candidates = cands.length;
	for ( const mesh of cands ) {
		const n = mesh.isInstancedMesh ? mesh.count : 1;
		if ( n !== 1 ) { out.instanced ++; continue; }   // a batched tree cannot take a per-mesh range
		const hit = nearest( idx, worldCentre( mesh, mesh.isInstancedMesh ? 0 : undefined ), taken );
		if ( ! hit.name || hit.d > VERTEX_MATCH_M ) { out.unmatchedMesh ++; continue; }
		todo.push( { mesh, name: hit.name, d: hit.d } );
		taken.add( hit.name );
	}
	out.matched = todo.length;
	out.unmatched = out.wanted - out.matched;

	// ONE GLOBAL RANGE (manifest lightmaps.vertex_irradiance.range, or the relay's range_global while
	// that key lands).  It is what makes gltfpack's sharing harmless: every COLOR_0 buffer decodes with
	// the same scale, so a primitive that carries several trees' vertices - or several placements of
	// one - is correct without any position join at all.  COLOR_0 is the identity; the join is only
	// needed for the per-mesh ranges that this replaced.
	if ( globalRange > 0 ) {
		out.mode = 'global';
		out.globalRange = globalRange;
		out.rangeMin = out.rangeMax = globalRange;
		for ( const mesh of cands ) {
			const mat = mesh.material.clone();
			mat.name = mesh.material.name;
			mesh.material = mat;
			patchBakedMaterial( mat, { vertexIrradiance: globalRange * gate3.scale } );
			out.applied ++;
			out.placements += mesh.isInstancedMesh ? mesh.count : 1;
		}
		return out;
	}
	if ( ! byAsset || ! Object.keys( byAsset ).length ) return out;
	// AUTO means all-or-nothing.  gltfpack's -mi merges and instances geometry across trees that were
	// baked with DIFFERENT per-mesh ranges (measured: 14 COLOR_0 primitives carrying 26 placements,
	// ranges spanning 0.469..43.320), so a partial application would light two trees correctly and
	// leave their neighbours on the sky - which reads as a viewer bug rather than as the export gap it
	// is.  ?vertexirr=1 forces it anyway for an A/B.
	out.mode = mode || 'auto';
	if ( out.mode !== '1' && todo.length < out.wanted ) {
		out.skipped = true;
		note( `gate3 vertex irradiance SKIPPED (?vertexirr=1 to force): only ${todo.length} of ${out.wanted} baked near-tree `
			+ `mesh(es) can be joined to a glb primitive of their own. ${out.candidates} primitive(s) carry COLOR_0, `
			+ `${out.instanced} of them are instanced batches sharing one geometry across trees whose baked ranges differ `
			+ `(0.469..43.320), so no single range is right for them. EXPORT-side: fold the range into the encoded value `
			+ `(one global range, or linear FLOAT_COLOR) so a merge cannot break it, or keep these 14 meshes out of -mi. `
			+ `The near trees stay on the environment-lit path.` );
		return out;
	}
	for ( const t of todo ) {
		out.maxMatchError_m = Math.max( out.maxMatchError_m, t.d );
		if ( ! t.mesh.geometry.attributes.color ) { out.noColorAttribute ++; continue; }
		const rec = byAsset[ t.name ];
		out.rangeMin = Math.min( out.rangeMin, rec.range );
		out.rangeMax = Math.max( out.rangeMax, rec.range );
		// one material per mesh: two trees never share a range
		const mat = t.mesh.material.clone();
		mat.name = t.mesh.material.name;
		t.mesh.material = mat;
		patchBakedMaterial( mat, { vertexIrradiance: rec.range * gate3.scale } );
		out.applied ++;
		out.meshes.push( { asset: t.name, range: rec.range, match_m: + t.d.toFixed( 4 ) } );
	}
	if ( ! isFinite( out.rangeMin ) ) { out.rangeMin = 0; out.rangeMax = 0; }
	return out;
}


/**
 * Gate 4 item 1c — the 1 379 shrub/reed placements' baked irradiance.
 *
 * These 28 card meshes are the only env.glb geometry with neither a lightmap nor `COLOR_0`, so until
 * now they were lit by the hero probe alone and read cyan (hue 180 against the reference's 102).  The
 * bake hands over one scene-linear rgb per PLACEMENT; it ships in the manifest, not the glb
 * (`in_glb: false`), and the viewer uploads it as an `InstancedBufferAttribute` exactly like the ORN
 * slot offsets.
 *
 * THE BINDING IS PER glTF NODE, NEVER PER MESH.  `gltfpack -mi` merged three `.001` single-placement
 * meshes into their base mesh's node with the odd row INSIDE the run (node 10 = 8 x maho2 @0 +
 * 1 x maho2.001 @0 + 37 x maho2 @8), so a node's rows are read from its ordered `segments` list
 * `[mesh, count, offset]` with a RUNNING CURSOR, `offset` being the row index into that mesh's own
 * array.  Slicing one range per mesh would give 37 mahonias the irradiance of placements 0-36.
 * Any node whose row count differs from its segments' sum is a hard failure: a silently misaligned
 * array lights each shrub with its neighbour's irradiance, which no metric would catch.
 *
 * `cov == 0` is a contract, not a diagnostic: the 7 fully enclosed placements ship [0,0,0] and keep
 * the probe irradiance, which `pfaInstOn` switches per instance inside the shader.
 *
 * @returns {{wanted:number, nodes:number, rows:number, dark:number, materials:number, missing:string[], errors:string[]}}
 */
export function applyInstanceIrradiance( scene, gate3, note = () => {}, mode = 'auto', opts = {} ) {
	const out = { wanted: 0, nodes: 0, rows: 0, dark: 0, materials: 0, missing: [], errors: [], enabled: false };
	// 6c round 2: the same binder serves the shrub/reed LOD1 set in its own glb - `block` is
	// lightmaps.instance_irradiance.lod1, `root` the env_shrubs scene, and the manifest promises the
	// SAME per-placement rgb in that glb's own row order, so crossing the LOD distance cannot change
	// a shrub's light.  Nothing else about the binding changes: still per glTF NODE, still segments.
	const ii = opts.block || ( gate3 && gate3.instanceIrradiance );
	const scale = opts.scale !== undefined ? opts.scale : ( gate3 && gate3.scale );
	const label = opts.label || 'gate4 instance irradiance';
	// 6c ROUND 3 — `?shrubcov=` (0 = the round-16b behaviour, 1 = the full correction).
	// The manifest ships ONE irradiance per placement and the viewer applies it to every fragment of
	// that card, but `rgb` is the mean over the vertices that RECEIVED light (`cov` is their fraction):
	// the occluded rest of the card is then drawn at the lit mean.  Multiplying by `cov` is the
	// manifest's own `mean_all` - the mean over ALL the card's vertices - which charges the occluded
	// fraction with the zero the bake measured for it.  The manifest's `reduce` note says to use `rgb`
	// because the uncovered fraction is "the card buried in the terrain", and for a buried card that
	// note is right; export's Cycles DiffCol pass (export/out/gate3/foliage/albedo_check.json, verdict
	// owner LIGHTING: every shrub box's shipped albedo is 2-13 % DARKER than the albedo Cycles uses on
	// the same cards) says the 1.34-1.70x level gap is nevertheless in the irradiance, and this is the
	// only term in it the viewer holds.  `k` is the exponent so the two readings can be weighed on the
	// boxes rather than argued: the measurement is in web/README.md.
	const covK = Number.isFinite( opts.covScale ) ? Math.min( Math.max( opts.covScale, 0 ), 2 ) : 0;
	out.covScale = covK;
	let covSum = 0, covN = 0;
	if ( mode === '0' || ! ii || ! ii.nodes || ! ii.nodes.length ) return out;
	out.wanted = ii.placements || 0;
	const byNode = new Map();
	for ( const n of ii.nodes ) byNode.set( n.gltf_node, n );
	const seen = new Set();
	// The node index is an index into ONE glb's `nodes` array, so the search has to be confined to the
	// glb the manifest joined against (env.glb) - orn.glb has instanced nodes 1..n too, and matching
	// across files is how the first run "found" 28 nodes for a 25-node block.
	const root = opts.root || scene.getObjectByName( `WEB_glb_${ii.glb || 'env'}` );
	if ( ! root ) { out.errors.push( `no WEB_glb_${ii.glb || 'env'} in the scene` ); note( `${label}: ${out.errors[ 0 ]}` ); return out; }
	const census = [];
	root.traverse( ( mesh ) => {
		if ( ! mesh.isMesh ) return;
		const gn = mesh.userData && mesh.userData.pfaGltfNode;
		if ( gn !== undefined ) census.push( `${gn}:${mesh.isInstancedMesh ? mesh.count : 1}` );
		if ( gn === undefined || ! byNode.has( gn ) || seen.has( mesh ) ) return;
		seen.add( mesh );
		const spec = byNode.get( gn );
		const count = mesh.isInstancedMesh ? mesh.count : 1;
		const total = spec.segments.reduce( ( a, s ) => a + s[ 1 ], 0 );
		if ( total !== count || total !== spec.count ) {
			out.errors.push( `glTF node ${gn} (${mesh.name || 'unnamed'}): ${count} row(s) in the glb, `
				+ `${spec.count} in the manifest, ${total} in its segments - refusing to bind a misaligned array` );
			return;
		}
		const irr = new Float32Array( count * 3 ), on = new Float32Array( count );
		let cursor = 0, bad = null;
		for ( const [ meshName, cnt, off ] of spec.segments ) {
			const rec = ii.meshes[ meshName ];
			if ( ! rec || ! rec.rgb || rec.rgb.length < 3 * ( off + cnt ) ) { bad = meshName; break; }
			for ( let i = 0; i < cnt; i ++, cursor ++ ) {
				const src = 3 * ( off + i );
				const cov = rec.cov ? rec.cov[ off + i ] : 1;
				// cov == 0 keeps its [0,0,0] and falls back to the probe: 0^k would be the same value
				// but the intent is clearer written out, and k = 0 must leave the shipped rgb alone.
				const f = ( covK > 0 && cov > 0 ) ? Math.pow( cov, covK ) : 1;
				irr[ 3 * cursor ] = rec.rgb[ src ] * f;
				irr[ 3 * cursor + 1 ] = rec.rgb[ src + 1 ] * f;
				irr[ 3 * cursor + 2 ] = rec.rgb[ src + 2 ] * f;
				on[ cursor ] = cov > 0 ? 1 : 0;
				if ( cov > 0 ) { covSum += cov; covN ++; } else out.dark ++;
			}
		}
		if ( bad !== null || cursor !== count ) {
			out.errors.push( `glTF node ${gn}: segment mesh "${bad}" missing or short (${cursor}/${count} rows written)` );
			return;
		}
		// The attribute lives on the GEOMETRY and chunking hands each chunk its own slice, so a
		// geometry shared by two InstancedMeshes is cloned first - the same rule as the ORN slots.
		let geo = mesh.geometry;
		if ( geo.attributes.pfaInstIrr ) { geo = geo.clone(); mesh.geometry = geo; }
		const Attr = mesh.isInstancedMesh ? THREE.InstancedBufferAttribute : THREE.BufferAttribute;
		geo.setAttribute( 'pfaInstIrr', new Attr( irr, 3 ) );
		geo.setAttribute( 'pfaInstOn', new Attr( on, 1 ) );
		// One material per node: it is patched with a per-instance attribute that other meshes sharing
		// the datablock do not carry, and a missing attribute would silently read 0 on them.
		const mats = Array.isArray( mesh.material ) ? mesh.material : [ mesh.material ];
		mesh.material = Array.isArray( mesh.material ) ? mats.map( cloneForInstIrr ) : cloneForInstIrr( mats[ 0 ] );
		const list = Array.isArray( mesh.material ) ? mesh.material : [ mesh.material ];
		for ( const m of list ) {
			if ( ! m ) continue;
			// The probe must still reach it: the 7 cov == 0 placements fall back to it, and
			// `pfaWantsProbeEnv` is what lets applyProbeEnv past its pfaPatched skip.
			m.userData.pfaWantsProbeEnv = true;
			patchBakedMaterial( m, { instanceIrradiance: scale, noEnvDiffuse: false, specularOnlySun: true } );
			out.materials ++;
		}
		out.nodes ++; out.rows += count;
	} );

	for ( const n of ii.nodes ) if ( ! [ ...seen ].some( m => m.userData.pfaGltfNode === n.gltf_node ) )
		out.missing.push( String( n.gltf_node ) );
	out.census = census.join( ' ' );
	if ( out.errors.length || out.missing.length )
		note( `${label} census (glb node:rows in ${root.name}): ${out.census}` );
	// A node the scene never presented is the SAME failure as a misaligned one, and it is the likelier
	// of the two: a mesh that gains a second primitive stops being the node object, loses
	// `pfaGltfNode`, and its placements would revert to the probe with nothing but a console line to
	// say so.  It goes in `errors`, which the caller throws on.
	if ( out.missing.length ) out.errors.push( `glb node(s) ${out.missing.join( ', ' )} carry ${ii.placements - out.rows} `
		+ 'placement(s) the scene never presented - they would silently fall back to the probe' );
	out.enabled = out.nodes > 0 && ! out.errors.length;
	if ( out.errors.length ) note( `${label} FAILED: ${out.errors.join( '; ' )}` );
	out.covMean = covN ? covSum / covN : 1;
	note( `${label}: ${out.rows}/${ii.placements} placement(s) over ${out.nodes}/${ii.nodes.length} `
		+ `glb node(s), ${out.materials} material(s) cloned and patched, ${out.dark} with cov == 0 left on the probe`
		+ ( covK > 0 ? `; irradiance x cov^${covK} (mean cov ${out.covMean.toFixed( 3 )}, ?shrubcov=)` : '' )
		+ ( out.missing.length ? `; NODE(S) NOT FOUND IN THE SCENE: ${out.missing.join( ', ' )}` : '' ) );
	return out;
}

function cloneForInstIrr( m ) {
	if ( ! m ) return m;
	if ( m.userData.pfaInstIrrClone ) return m;
	const c = m.clone();
	c.userData = { ...m.userData, pfaInstIrrClone: true };
	c.name = m.name;
	return c;
}
