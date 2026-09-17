// Phase 6c round 2 — the two LAZY foliage glbs and the foliage material textures.
//
// Nothing in the first frame depends on either file, so both are fetched AFTER the page is ready:
//   * `env_trees.glb`   (manifest `trees.far_mesh`)  — a real LOD2 mesh for each of the 127 far
//     trees, 16 prototypes x (bark + leaf) as 32 EXT_mesh_gpu_instancing nodes, 254 rows.  Until it
//     lands every one of those trees is an impostor at EVERY distance, which is the user's finding at
//     station 2: an 85 px atlas frame magnified into a blue-green blob a few metres from the camera.
//   * `env_shrubs.glb`  (manifest `shrubs.lod1`)     — the shrub/reed LOD1 meshes (25 of the 28 card
//     meshes, 1 376 of the 1 379 placements) that replace the LOD2 cards within `shrubLodDist`.
//
// THE JOIN IS POSITIONAL, because gltfpack -mi drops node names and re-orders the rows.  For the far
// trees the key is the instance TRANSLATION against `trees.far_mesh.placements[].loc` (Blender), the
// same key and the same 5.8 mm residual the export measured (export/README.md item 36); for the
// shrubs it is the manifest's own per-node `segments` cursor, unchanged, through the existing
// `applyInstanceIrradiance` — `lightmaps.instance_irradiance.lod1` is the SAME per-placement rgb in
// the LOD1 glb's row order, so crossing the LOD distance cannot change a shrub's light.
//
// WHAT LIGHTS THE FAR-TREE MESHES.  Exactly what lights the shrub cards: one baked scene-linear
// irradiance per PLACEMENT (`pfaInstIrr`, specular-only sun) times a per-vertex ambient occlusion in
// COLOR_0.  Both come from the bake (item B).  Where the bake has not landed:
//   * no COLOR_0 -> AO = 1 (the glb simply has no `color` attribute and three multiplies by nothing);
//   * no `trees.far_mesh.lighting` -> `?fartreelight=` decides.  The default `near` gives each
//     placement the irradiance of the NEAREST near-tree crown, which is a MEASURED value of the same
//     kind of object (`lightmaps.vertex_irradiance`, 18 crowns) rather than a guess, and the note
//     reports the join distances so nobody mistakes it for the bake.  `probe` leaves the meshes on
//     the hero probe + full sun direct (the viewer's ordinary "no baked light" path), `0` refuses to
//     draw the meshes at all and every far tree stays the impostor it was.
import * as THREE from 'three';
import { applyFoliage, farTreeIrradiance, irradianceRatio } from './foliage.js';
import { applyInstanceIrradiance } from './lightmaps.js';
import { patchBakedMaterial } from './materials.js';
import { applyProbeEnv } from './probeEnv.js';
import { dequantizeUvs } from './uvDequant.js';
import { activateImpostorMeshes } from './impostors.js';
import { chunkInstancedMeshes } from './chunking.js';
import { resolveUrl } from './manifest.js';

const JOIN_TOL_M = 0.05;          // the export measured 5.8 mm; 50 mm is a generous ceiling
const CULL_MARGIN_M = 10;         // see `out.update`: the water's mirrored camera stands further back
const NEAR_LIGHT_MAX_M = 220;     // the site is 250 x 166 m: beyond this "the nearest crown" is meaningless

/**
 * Where a lazily loaded file may be.  The 6c manifest blocks name `env_trees.glb` / `env_shrubs.glb`
 * with no directory and `out/gate3/foliage/tex_ktx2` with the OUT root still in it, while every other
 * path in the manifest is relative to the manifest itself (`../gate1/env.glb`, `../gate0/lut...`).
 * Rather than hard-code one reading, each candidate is tried in order and the one that answers is
 * reported, so the export engineer can see exactly which spelling the viewer had to fall back to.
 */
export function lazyUrlCandidates( baseUrl, spec ) {
	const out = [];
	const add = ( u ) => { if ( u && ! out.includes( u ) ) out.push( u ); };
	const clean = String( spec || '' ).replace( /^\.\//, '' );
	if ( ! clean ) return out;
	const base = clean.split( '/' ).pop();
	// LIKELIEST FIRST, so the usual case costs no 404 at all: a bare `x.glb` is in ../gate1 (where
	// gltf_pack.sh writes and where `glb.per_class` points), and an `out/...` path is the OUT root the
	// manifest still has in it.  The as-written spelling is tried too, so a corrected manifest works
	// without a viewer change either way.
	if ( ! clean.includes( '/' ) ) add( resolveUrl( baseUrl, `../gate1/${base}` ) );
	if ( /^out\// .test( clean ) ) add( resolveUrl( baseUrl, `../${clean.replace( /^out\//, '' )}` ) );
	add( resolveUrl( baseUrl, clean ) );
	add( resolveUrl( baseUrl, `../gate1/${base}` ) );
	if ( /^out\/gate3\//.test( clean ) ) add( resolveUrl( baseUrl, clean.replace( /^out\/gate3\//, '' ) ) );
	return out;
}

async function firstThatLoads( cands, load, note, what ) {
	const tried = [];
	for ( const url of cands ) {
		try { const v = await load( url ); if ( v ) return { url, value: v, tried }; }
		catch ( e ) { tried.push( `${url} (${e.message})` ); }
	}
	note( `${what}: none of ${cands.length} candidate url(s) answered — ${tried.join( '; ' )}` );
	return null;
}

const b2tKey = ( x, y, z ) => `${x.toFixed( 2 )},${y.toFixed( 2 )},${z.toFixed( 2 )}`;

/** three-space world position -> Blender (x, y, z), the manifest's own convention. */
function toBlender( v ) { return [ v.x, - v.z, v.y ]; }

/**
 * The bake's far-tree lighting, which the manifest may either inline or name as a sidecar json
 * (`trees.far_mesh.lighting.json`).  Fetched EARLY (it is a few kB) rather than with the glb, because
 * `?impmod=full` and the near trees' own E_bake depend on it and the impostors are built long before
 * the lazy glb arrives.  Returns the block, and folds a fetched sidecar back into `manifest.raw` so
 * every existing consumer (`farTreeIrradiance`) reads it the same way whichever shape it arrived in.
 */
export async function loadFarTreeLighting( manifest, fetchJson, note = () => {} ) {
	const fm = manifest && manifest.raw && manifest.raw.trees && manifest.raw.trees.far_mesh;
	const lit = fm && fm.lighting;
	if ( ! lit ) { note( 'far-tree lighting: trees.far_mesh.lighting is not in the manifest (bake item B)' ); return null; }
	const has = ( b ) => b && b.prototypes && Array.isArray( b.placements || b.instances || b.rows );
	if ( has( lit ) ) { note( 'far-tree lighting: inline in the manifest' ); return lit; }
	const spec = lit.json || ( lit.instance_irradiance && lit.instance_irradiance.json );
	if ( ! spec ) { note( 'far-tree lighting: the block names neither rows nor a json to fetch' ); return null; }
	const got = await firstThatLoads( lazyUrlCandidates( manifest.baseUrl, spec ), fetchJson, note, 'far-tree lighting json' );
	if ( ! got ) return null;
	const j = got.value;
	lit.placements = j.placements || j.instances || j.rows || null;
	lit.prototypes = j.prototypes || lit.prototypes || null;
	lit.schema = j.schema || lit.schema || null;
	lit.reduce = j.reduce || lit.reduce || null;
	note( `far-tree lighting: ${got.url.split( '/' ).pop()} (${lit.schema || 'no schema'}), `
		+ `${( lit.placements || [] ).length} placement row(s), ${Object.keys( lit.prototypes || {} ).length} prototype E_bake value(s)` );
	return has( lit ) ? lit : null;
}

/** E_bake per prototype, in the manifest's raw (irradiance / pi) units, or null. */
export function prototypeEbake( lit ) {
	if ( ! lit || ! lit.prototypes ) return null;
	const out = {};
	let n = 0;
	for ( const [ k, v ] of Object.entries( lit.prototypes ) ) {
		const e = v && ( v.E_bake || v.e_bake );
		if ( Array.isArray( e ) && e.length === 3 ) { out[ k ] = e; n ++; }
	}
	return n ? out : null;
}

// ---------------------------------------------------------------- item 1: the far-tree meshes

/**
 * @param {object} o
 * @param {THREE.Scene}  o.scene
 * @param {object}       o.manifest          the normalised manifest (needs `.raw` and `.baseUrl`)
 * @param {Function}     o.loadGlb           (url) -> Promise<GLTF>
 * @param {THREE.Object3D|null} o.impostorGroup
 * @param {object|null}  o.foliageReport     the FIRST applyFoliage report (its shared uniforms)
 * @param {THREE.Texture|null} o.probeTexture
 * @param {number}       o.scale             lightmaps.scale (pi)
 * @param {string}       o.mode              ?fartreelight= : 'near' | 'probe' | '0'
 * @param {string}       o.impMode           the impostor modulation mode in force
 */
export async function loadFarTrees( o ) {
	const { scene, manifest, loadGlb, note = () => {} } = o;
	const out = { glb: null, bytes: 0, wall_s: 0, nodes: 0, rows: 0, joined: 0, unjoined: 0,
		placements: 0, lit: 0, litFrom: null, ao: false, aoEncode: null, impostors: null,
		chunks: 0, drawCalls: 0, tris: 0, error: null };
	const fm = manifest.raw && manifest.raw.trees && manifest.raw.trees.far_mesh;
	if ( ! fm || ! fm.glb ) { note( 'far-tree meshes: no trees.far_mesh in the manifest (export item A)' ); return out; }
	if ( o.mode === '0' ) { note( 'far-tree meshes SUPPRESSED (?fartreelight=0): the 127 far trees stay impostors' ); return out; }
	const placements = Array.isArray( fm.placements ) ? fm.placements : [];
	if ( ! placements.length ) { out.error = 'trees.far_mesh.placements is empty'; note( `far-tree meshes: ${out.error}` ); return out; }
	out.placements = placements.length;

	const t0 = performance.now();
	const got = await firstThatLoads( lazyUrlCandidates( manifest.baseUrl, fm.glb ), loadGlb, note, 'env_trees.glb' );
	if ( ! got ) { out.error = 'not found'; return out; }
	const gltf = got.value;
	out.glb = got.url;
	const root = gltf.scene;
	root.name = 'WEB_glb_env_trees';
	root.visible = false;                     // nothing unpatched is ever presented
	if ( gltf.parser && gltf.parser.associations ) {
		for ( const [ obj, a ] of gltf.parser.associations )
			if ( obj && obj.isObject3D && a && typeof a.nodes === 'number' ) obj.userData.pfaGltfNode = a.nodes;
	}
	dequantizeUvs( root, { note, enabled: o.uvDequant !== false } );
	scene.add( root );
	root.updateMatrixWorld( true );

	// ---- the positional join: every instance row -> its manifest placement --------------------
	const byLoc = new Map();
	for ( const p of placements ) if ( Array.isArray( p.loc ) ) byLoc.set( b2tKey( p.loc[ 0 ], p.loc[ 1 ], p.loc[ 2 ] ), p );
	const locList = placements.filter( ( p ) => Array.isArray( p.loc ) );
	const rowsOf = [];                        // { mesh, row, placement }
	const v = new THREE.Vector3(), m = new THREE.Matrix4();
	root.traverse( ( mesh ) => {
		if ( ! mesh.isMesh ) return;
		out.nodes ++;
		const n = mesh.isInstancedMesh ? mesh.count : 1;
		for ( let i = 0; i < n; i ++ ) {
			if ( mesh.isInstancedMesh ) m.fromArray( mesh.instanceMatrix.array, i * 16 ).premultiply( mesh.matrixWorld );
			else m.copy( mesh.matrixWorld );
			v.setFromMatrixPosition( m );
			const b = toBlender( v );
			let p = byLoc.get( b2tKey( b[ 0 ], b[ 1 ], b[ 2 ] ) ), d = 0;
			if ( ! p ) {                      // the rounded key missed: nearest within the tolerance
				let best = null, bestD = JOIN_TOL_M;
				for ( const q of locList ) {
					const e = Math.hypot( q.loc[ 0 ] - b[ 0 ], q.loc[ 1 ] - b[ 1 ], q.loc[ 2 ] - b[ 2 ] );
					if ( e < bestD ) { bestD = e; best = q; }
				}
				p = best; d = bestD;
			}
			rowsOf.push( { mesh, row: i, placement: p || null, residual_m: p ? d : null } );
			out.rows ++;
			if ( p ) out.joined ++; else out.unjoined ++;
		}
	} );
	// Every tree is bark + leaf, so a placement is expected TWICE (the manifest's `rows` note).
	const seenPlacements = new Set( rowsOf.filter( ( r ) => r.placement ).map( ( r ) => r.placement.index ) );
	if ( out.unjoined || seenPlacements.size !== placements.length ) {
		out.error = `${out.unjoined} of ${out.rows} instance row(s) matched no placement within ${JOIN_TOL_M} m `
			+ `and ${placements.length - seenPlacements.size} placement(s) were never presented`;
		note( `far-tree meshes: JOIN FAILED — ${out.error}; the meshes are not drawn and every far tree stays its impostor` );
		scene.remove( root );
		return out;
	}

	// ---- E_placement per row ------------------------------------------------------------------
	const lit = fm.lighting;
	const rows = lit && ( lit.placements || lit.instances || lit.rows );
	const byBakeLoc = new Map();
	if ( Array.isArray( rows ) ) for ( const r of rows ) {
		const loc = r.location_blender || r.loc || r.location;
		const rgb = r.rgb || r.irradiance;
		if ( Array.isArray( loc ) && Array.isArray( rgb ) ) byBakeLoc.set( b2tKey( loc[ 0 ], loc[ 1 ], loc[ 2 ] ), { rgb, cov: r.cov } );
	}
	// the fallback: the nearest near-tree crown's own baked irradiance, in the SAME raw (/pi) units
	const crowns = ( o.foliageReport && o.foliageReport.units || [] )
		.filter( ( u ) => Array.isArray( u.irradiance ) && u.irradiance.some( ( x ) => x > 0 ) );
	const scale = o.scale > 0 ? o.scale : Math.PI;
	const nearestCrown = ( p ) => {
		let best = null, bestD = NEAR_LIGHT_MAX_M;
		// placement loc is Blender; a crown centre is three-space
		for ( const u of crowns ) {
			const b = toBlender( u.centre );
			const d = Math.hypot( b[ 0 ] - p.loc[ 0 ], b[ 1 ] - p.loc[ 1 ] );
			if ( d < bestD ) { bestD = d; best = u; }
		}
		return best ? { rgb: best.irradiance.map( ( x ) => x / scale ), d: bestD } : null;
	};
	const useNear = ! byBakeLoc.size && o.mode !== 'probe';
	out.litFrom = byBakeLoc.size ? 'trees.far_mesh.lighting (the bake, per placement)'
		: ( useNear ? 'the nearest near-tree crown COLOR_0 (measured, NOT the bake)' : 'the hero probe + sun direct' );
	const joinD = [];

	if ( byBakeLoc.size || useNear ) {
		const seen = new Set();
		root.traverse( ( mesh ) => {
			if ( ! mesh.isMesh || seen.has( mesh ) ) return;
			seen.add( mesh );
			const n = mesh.isInstancedMesh ? mesh.count : 1;
			const irr = new Float32Array( n * 3 ), on = new Float32Array( n );
			for ( const r of rowsOf ) {
				if ( r.mesh !== mesh || ! r.placement ) continue;
				const p = r.placement;
				let e = byBakeLoc.get( b2tKey( p.loc[ 0 ], p.loc[ 1 ], p.loc[ 2 ] ) );
				if ( ! e && useNear ) { const c = nearestCrown( p ); if ( c ) { e = { rgb: c.rgb }; joinD.push( c.d ); } }
				if ( ! e || ! e.rgb || ( e.cov !== undefined && ! ( e.cov > 0 ) ) ) continue;
				irr[ r.row * 3 ] = e.rgb[ 0 ]; irr[ r.row * 3 + 1 ] = e.rgb[ 1 ]; irr[ r.row * 3 + 2 ] = e.rgb[ 2 ];
				on[ r.row ] = 1;
				out.lit ++;
			}
			const Attr = mesh.isInstancedMesh ? THREE.InstancedBufferAttribute : THREE.BufferAttribute;
			mesh.geometry.setAttribute( 'pfaInstIrr', new Attr( irr, 3 ) );
			mesh.geometry.setAttribute( 'pfaInstOn', new Attr( on, 1 ) );
			for ( const mat of Array.isArray( mesh.material ) ? mesh.material : [ mesh.material ] ) {
				if ( ! mat ) continue;
				mat.userData.pfaWantsProbeEnv = true;     // a row with no measurement keeps the probe
				patchBakedMaterial( mat, { instanceIrradiance: scale, noEnvDiffuse: false, specularOnlySun: true } );
			}
		} );
	}
	// AO: COLOR_0 on the export's LOD2 topology (bake item B).  glTF's own use of COLOR_0 is a base
	// colour multiplier, which is exactly what an occlusion factor is, so three needs no help - except
	// when the export encodes it gamma2, where the value has to be squared back to linear.
	const c0 = fm.color0 || {};
	root.traverse( ( mesh ) => {
		if ( ! mesh.isMesh || ! mesh.geometry.getAttribute( 'color' ) ) return;
		out.ao = true;
		if ( String( c0.encode || 'none' ).toLowerCase() !== 'gamma2' ) return;
		out.aoEncode = 'gamma2';
		for ( const mat of Array.isArray( mesh.material ) ? mesh.material : [ mesh.material ] ) {
			if ( ! mat || mat.userData.pfaAoSquared ) continue;
			mat.userData.pfaAoSquared = true;
			const prev = mat.onBeforeCompile;
			mat.onBeforeCompile = function ( sh, r ) {
				if ( prev ) prev.call( this, sh, r );
				sh.fragmentShader = sh.fragmentShader.replace( '#include <color_fragment>',
					'#include <color_fragment>\n\tdiffuseColor.rgb *= vColor.rgb;   // PFA: gamma2 AO, squared back to linear' );
			};
			mat.needsUpdate = true;
		}
	} );

	if ( o.probeTexture ) applyProbeEnv( root, o.probeTexture, { note: () => {} } );

	// ---- the leaf shader and the LOD dissolve, sharing the first pass's uniforms ---------------
	const fol = applyFoliage( {
		scene: root, sun: o.sun, note, msaa: o.msaa, vertexIrrScale: 0,
		sharedUniforms: o.foliageReport ? o.foliageReport.shared.uniforms : null,
		normalBlend: o.normalBlend, cardNormalBlend: o.cardNormalBlend,
		trnScale: o.trnScale, trnShrubs: o.trnShrubs, trnMaps: o.trnMaps,
		meshDist: o.meshDist, fadeBand: o.fadeBand,
	} );
	out.foliage = { geometries: fol.geometries, clusters: fol.clusters, leafMaterials: fol.leafMaterials,
		barkMaterials: fol.barkMaterials, bent: fol.bent, softened: fol.softened, units: fol.units.length };

	// ---- the impostor side: these 127 now have a mesh to fade into ----------------------------
	// The crown centre the MESH switches on (pfaCrown through the instance matrix) has to be the one
	// the impostor switches on, or the two dissolves cross at different metres and the complement
	// breaks exactly where it is visible.
	const byId = new Map();
	const crownOf = new Map();                // placement index -> world crown centre
	for ( const u of fol.units ) {
		// a unit is one crown of one instance; find its placement by the instance's own translation
		const r = rowsOf.find( ( x ) => x.mesh.name === u.mesh && x.row === u.instance && x.placement );
		if ( ! r ) continue;
		const prev = crownOf.get( r.placement.index );
		if ( ! prev || u.centre.y > prev.y ) crownOf.set( r.placement.index, u.centre );
	}
	const impMode = o.impMode || 'chroma';
	const far = ( impMode !== '0' ) ? farTreeIrradiance( manifest.treesFar, manifest.raw, impMode, note ) : { byIndex: new Map() };
	manifest.treesFar.forEach( ( t, i ) => {
		if ( ! t.id ) return;
		const p = placements.find( ( q ) => q.billboard === t.id );
		if ( ! p ) return;
		const c = crownOf.get( p.index );
		if ( ! c ) return;
		byId.set( t.id, { switchCentre: [ c.x, c.y, c.z ], irr: far.byIndex.get( i ) || null } );
	} );
	out.impostors = activateImpostorMeshes( o.impostorGroup, byId, note );

	// ---- draw cost: split the site-spanning batches, then cull by the switch distance ----------
	// 254 rows x ~8 k tris is 1.03 M triangles that would be vertex-shaded every frame even though
	// the fragment side discards all but the trees inside `treeMeshDist`.  Chunking gives each group
	// its own bounding sphere (so three's frustum test bites) and the per-frame test below hides any
	// chunk whose whole sphere is beyond the switch distance.  Both are pure culling: nothing about
	// what is drawn changes, only whether it is submitted.
	const ch = chunkInstancedMeshes( root, { minRadius: 12, minCount: 2, maxDepth: 3, gain: 0.95, budget: 256 } );
	out.chunks = ch.chunks; out.split = ch.split; out.added = ch.added;
	const batches = [];
	root.traverse( ( mesh ) => {
		if ( ! mesh.isMesh ) return;
		mesh.frustumCulled = true;
		if ( ! mesh.geometry.boundingSphere ) mesh.geometry.computeBoundingSphere();
		if ( mesh.isInstancedMesh ) mesh.computeBoundingSphere();
		const s = ( mesh.isInstancedMesh ? mesh.boundingSphere : mesh.geometry.boundingSphere );
		if ( s ) batches.push( { mesh, centre: s.center.clone(), radius: s.radius } );
		out.drawCalls ++;
		const idx = mesh.geometry.index;
		out.tris += ( idx ? idx.count : mesh.geometry.getAttribute( 'position' ).count ) / 3
			* ( mesh.isInstancedMesh ? mesh.count : 1 );
	} );
	const shared = o.foliageReport ? o.foliageReport.shared.uniforms : null;
	out.update = ( camera ) => {
		const d = shared && shared.pfaMeshDist ? shared.pfaMeshDist.value : 40;
		const band = shared && shared.pfaFadeBand ? shared.pfaFadeBand.value : 5;
		// + CULL_MARGIN_M because the WATER draws the scene a second time from the mirrored camera,
		// which stands a few metres further from a tree than this one does.  Without the margin a tree
		// right at the switch could be culled for the main camera while the reflection's own dissolve
		// wanted to draw it - and its impostor, being the exact complement, would not draw either.
		const lim = d + band + CULL_MARGIN_M;
		let on = 0;
		for ( const b of batches ) {
			b.mesh.visible = camera.position.distanceTo( b.centre ) - b.radius <= lim;
			if ( b.mesh.visible ) on ++;
		}
		return on;
	};
	out.batches = batches.length;
	root.visible = true;
	out.wall_s = ( performance.now() - t0 ) / 1000;
	note( `far-tree meshes: ${out.glb.split( '/' ).pop()} in ${out.wall_s.toFixed( 2 )} s — `
		+ `${out.joined}/${out.rows} instance row(s) joined to ${seenPlacements.size}/${placements.length} placement(s) `
		+ `by translation (<= ${JOIN_TOL_M} m), ${Math.round( out.tris / 1000 )} k placed tris in ${out.drawCalls} batch(es) `
		+ `(${ch.split} split into ${ch.chunks}); lighting from ${out.litFrom} on ${out.lit} row(s)`
		+ ( joinD.length ? `, nearest-crown distance ${Math.min( ...joinD ).toFixed( 0 )}-${Math.max( ...joinD ).toFixed( 0 )} m` : '' )
		+ `; vertex AO ${out.ao ? `present${out.aoEncode ? ` (${out.aoEncode})` : ''}` : 'NOT in the glb (AO = 1)'}` );
	return out;
}

// ---------------------------------------------------------------- item 2: the shrub/reed LOD1 set

/**
 * `env_shrubs.glb` — the LOD1 meshes drawn within `dist` metres, the env.glb LOD2 cards beyond it.
 * The two sets share one dissolve (the same shader, the sign flipped), and the three meshes with no
 * LOD1 keep their card at every distance through the per-row `pfaSwitchOn` mask, because gltfpack
 * merged their single placements INTO nodes whose other rows do have one.
 */
export async function loadShrubLod1( o ) {
	const { scene, manifest, loadGlb, note = () => {} } = o;
	const out = { glb: null, dist: o.dist, lod1Nodes: 0, lod1Rows: 0, lod2Materials: 0, masked: 0,
		errors: [], wall_s: 0 };
	const block = manifest.raw && manifest.raw.shrubs && manifest.raw.shrubs.lod1;
	const ii = manifest.gate3 && manifest.gate3.instanceIrradiance;
	const lod1Irr = manifest.raw && manifest.raw.lightmaps && manifest.raw.lightmaps.instance_irradiance
		&& manifest.raw.lightmaps.instance_irradiance.lod1;
	if ( ! block || ! block.glb ) { note( 'shrub/reed LOD1: no shrubs.lod1 in the manifest (export item E)' ); return out; }
	if ( o.mode === '0' ) { note( 'shrub/reed LOD1 SUPPRESSED (?shrublod=0): every card stays the LOD2 one' ); return out; }
	const t0 = performance.now();
	const got = await firstThatLoads( lazyUrlCandidates( manifest.baseUrl, block.glb ), loadGlb, note, 'env_shrubs.glb' );
	if ( ! got ) return out;
	const gltf = got.value;
	out.glb = got.url;
	const root = gltf.scene;
	root.name = 'WEB_glb_env_shrubs';
	root.visible = false;
	if ( gltf.parser && gltf.parser.associations ) {
		for ( const [ obj, a ] of gltf.parser.associations )
			if ( obj && obj.isObject3D && a && typeof a.nodes === 'number' ) obj.userData.pfaGltfNode = a.nodes;
	}
	dequantizeUvs( root, { note, enabled: o.uvDequant !== false } );
	scene.add( root );
	root.updateMatrixWorld( true );

	// the SAME per-placement irradiance, in this glb's own row order (manifest `shrubs.lod1.join`)
	const bound = applyInstanceIrradiance( scene, manifest.gate3, note, 'auto',
		{ root, block: lod1Irr ? { ...lod1Irr, placements: lod1Irr.placements ?? block.placements } : null,
			scale: manifest.gate3 ? manifest.gate3.scale : Math.PI, label: 'shrub/reed LOD1 irradiance' } );
	out.lod1Nodes = bound.nodes; out.lod1Rows = bound.rows;
	if ( bound.errors.length ) {
		out.errors = bound.errors;
		note( 'shrub/reed LOD1: the irradiance binding failed, the LOD1 set is NOT drawn (the LOD2 cards stay)' );
		scene.remove( root );
		return out;
	}
	if ( o.probeTexture ) applyProbeEnv( root, o.probeTexture, { note: () => {} } );

	// the leaf shader on the LOD1 cards, then the switch: LOD1 within `dist` (sign +1)
	const fol = applyFoliage( {
		scene: root, sun: o.sun, note, msaa: o.msaa, vertexIrrScale: 0,
		sharedUniforms: o.foliageReport ? o.foliageReport.shared.uniforms : null,
		normalBlend: o.normalBlend, cardNormalBlend: o.cardNormalBlend,
		trnScale: o.trnScale, trnShrubs: o.trnShrubs, trnMaps: o.trnMaps,
		meshDist: o.meshDist, fadeBand: o.fadeBand,
	} );
	const dist = out.dist;
	const setSwitch = ( r, sign ) => {
		let n = 0;
		for ( const mats of r.byMesh.values() ) for ( const mat of mats ) {
			const f = mat && mat.userData.pfaFoliage;
			if ( ! f ) continue;
			f.uniforms.pfaSwitchDist.value = dist; f.uniforms.pfaSwitchSign.value = sign;
			f.dist = dist; f.sign = sign; n ++;
		}
		return n;
	};
	out.lod1Materials = setSwitch( fol, 1 );

	// the env.glb LOD2 cards: beyond `dist` (sign -1).  The per-ROW mask for the three meshes with no
	// LOD1 was written before the first foliage pass (`markShrubLodRows`), because the attribute has to
	// be declared when the program is built; here only the uniforms move.
	const ii2 = manifest.gate3 && manifest.gate3.instanceIrradiance;
	const env = scene.getObjectByName( `WEB_glb_${( ii2 && ii2.glb ) || 'env'}` );
	const lod2Nodes = new Set( ( ( ii2 && ii2.nodes ) || [] ).map( ( n ) => n.gltf_node ) );
	const seenMat = new Set();
	if ( env ) env.traverse( ( mesh ) => {
		if ( ! mesh.isMesh || ! lod2Nodes.has( mesh.userData && mesh.userData.pfaGltfNode ) ) return;
		for ( const mat of Array.isArray( mesh.material ) ? mesh.material : [ mesh.material ] ) {
			const f = mat && mat.userData.pfaFoliage;
			if ( ! f || seenMat.has( mat.uuid ) ) continue;
			seenMat.add( mat.uuid );
			f.uniforms.pfaSwitchDist.value = dist; f.uniforms.pfaSwitchSign.value = - 1;
			f.dist = dist; f.sign = - 1; out.lod2Materials ++;
			if ( f.switchMask ) out.masked ++;
		}
	} );
	root.visible = true;
	out.wall_s = ( performance.now() - t0 ) / 1000;
	note( `shrub/reed LOD1: ${out.glb.split( '/' ).pop()} in ${out.wall_s.toFixed( 2 )} s — `
		+ `${out.lod1Rows}/${block.placements} placement(s) over ${out.lod1Nodes} node(s) on their own baked irradiance, `
		+ `LOD1 within ${dist} m on ${out.lod1Materials} material(s), the env.glb cards beyond it on ${out.lod2Materials}`
		+ ( out.masked ? `, ${out.masked} of them carrying the per-row mask for the placements with no LOD1` : '' ) );
	return out;
}

// ---------------------------------------------------------------- item 2b: materials.foliage

/**
 * Export item D — the foliage cards' MATERIAL albedo (the glb ships the untinted source PNG, ~1.9x
 * too dark on the three shrub cards, and the same card for all three) and the per-texel translucency
 * FACTOR map that replaces the Phase 5 constant.  Paths are read from the manifest, never built.
 */
export async function applyFoliageTextures( o ) {
	const { manifest, loadTexture, note = () => {} } = o;
	const out = { size: null, albedo: 0, translucency: 0, normals: 0, materials: [], missing: [], bytes: 0 };
	const fol = manifest.raw && manifest.raw.materials && manifest.raw.materials.foliage;
	if ( ! fol || ! fol.materials ) { note( 'foliage textures: no materials.foliage in the manifest (export item D)' ); return out; }
	if ( o.mode === '0' ) { note( 'foliage textures OFF (?foliagetex=0): the cards keep the glb\'s untinted source texture' ); return out; }
	const sizes = ( fol.sizes || [ 1024 ] ).map( String );
	const want = sizes.includes( String( o.mode ) ) ? String( o.mode ) : String( Math.min( ...sizes.map( Number ) ) );
	out.size = Number( want );
	const dir = fol.dir || '';
	const pick = ( rec, kind ) => {
		const e = rec && rec[ kind ];
		if ( ! e ) return null;
		const name = typeof e === 'string' ? e : ( e[ want ] || e[ sizes[ 0 ] ] || null );
		return name ? `${name}${/\.[a-z0-9]+$/i.test( name ) ? '' : '.ktx2'}` : null;
	};
	const byName = new Map();
	o.scene.traverse( ( m ) => {
		if ( ! m.isMesh ) return;
		for ( const mat of Array.isArray( m.material ) ? m.material : [ m.material ] ) {
			if ( ! mat || ! mat.name ) continue;
			if ( ! byName.has( mat.name ) ) byName.set( mat.name, [] );
			if ( ! byName.get( mat.name ).includes( mat ) ) byName.get( mat.name ).push( mat );
		}
	} );
	const trnMaps = {};
	// The first file that answers fixes the directory for the rest: a wrong candidate is a 404 per
	// file otherwise, and there are 16 of them.
	let prefix = null;
	const fetchOne = async ( file, what ) => {
		if ( prefix ) {
			try { return await loadTexture( prefix + file ); } catch ( e ) { /* fall through to the search */ }
		}
		const g = await firstThatLoads( lazyUrlCandidates( manifest.baseUrl, `${dir}/${file}` ), loadTexture, note, what );
		if ( g ) prefix = g.url.slice( 0, g.url.lastIndexOf( '/' ) + 1 );
		return g && g.value;
	};
	for ( const [ name, rec ] of Object.entries( fol.materials ) ) {
		const mats = byName.get( name ) || [];
		const alb = pick( rec, 'albedo' ), trn = pick( rec, 'translucency_map' );
		const tint = rec.translucency && rec.translucency.colour_multiplier;
		let aTex = null, tTex = null;
		if ( alb ) aTex = await fetchOne( alb, `foliage albedo ${name}` );
		if ( trn ) tTex = await fetchOne( trn, `foliage translucency ${name}` );
		if ( tTex ) {
			tTex.colorSpace = THREE.NoColorSpace;          // a factor, not a colour
			tTex.wrapS = tTex.wrapT = THREE.ClampToEdgeWrapping;
			tTex.anisotropy = Math.max( tTex.anisotropy || 1, 8 );
			tTex.needsUpdate = true;
			if ( Array.isArray( tint ) && tint.length === 3 ) tTex.userData.pfaTint = tint;
			trnMaps[ name ] = tTex;
			out.translucency ++;
		}
		if ( ! mats.length ) { out.missing.push( name ); continue; }
		for ( const mat of mats ) {
			if ( aTex ) {
				const old = mat.map;
				aTex.colorSpace = THREE.SRGBColorSpace;
				aTex.wrapS = old ? old.wrapS : THREE.ClampToEdgeWrapping;
				aTex.wrapT = old ? old.wrapT : THREE.ClampToEdgeWrapping;
				aTex.anisotropy = Math.max( aTex.anisotropy || 1, 8 );
				aTex.channel = old ? old.channel : 0;
				aTex.needsUpdate = true;
				mat.map = aTex;
				mat.needsUpdate = true;
			}
		}
		if ( aTex ) { out.albedo ++; out.materials.push( name ); }
	}
	out.trnMaps = trnMaps;
	note( `foliage textures (materials.foliage, ${out.size} px): ${out.albedo} tinted albedo(s) and `
		+ `${out.translucency} translucency factor map(s) on ${out.materials.join( ', ' )}`
		+ ( out.missing.length ? `; ${out.missing.length} declared material(s) not in the scene: ${out.missing.join( ', ' )}` : '' ) );
	return out;
}


/**
 * Written BEFORE the first `applyFoliage` (the attribute has to exist when the shader program is
 * built): `pfaSwitchOn` on every env.glb shrub/reed node that carries a placement with NO LOD1.
 * `shrubs.lod1.not_in_lod1.meshes` names them and the node's own `segments` say which rows they are;
 * gltfpack merged those single placements into nodes whose other rows DO have a LOD1, so without the
 * mask three cards would dissolve inside the switch distance with nothing behind them.
 */
export function markShrubLodRows( scene, manifest, note = () => {} ) {
	const out = { nodes: 0, rows: 0, meshes: [] };
	const block = manifest.raw && manifest.raw.shrubs && manifest.raw.shrubs.lod1;
	const ii = manifest.gate3 && manifest.gate3.instanceIrradiance;
	const orphan = new Set( Object.keys( ( block && block.not_in_lod1 && block.not_in_lod1.meshes ) || {} ) );
	if ( ! block || ! ii || ! orphan.size ) return out;
	const nodes = new Map( ( ii.nodes || [] ).map( ( n ) => [ n.gltf_node, n ] ) );
	const root = scene.getObjectByName( `WEB_glb_${ii.glb || 'env'}` );
	if ( ! root ) return out;
	root.traverse( ( mesh ) => {
		if ( ! mesh.isMesh ) return;
		const spec = nodes.get( mesh.userData && mesh.userData.pfaGltfNode );
		if ( ! spec ) return;
		const count = mesh.isInstancedMesh ? mesh.count : 1;
		const on = new Float32Array( count ).fill( 1 );
		let cursor = 0, orphans = 0;
		for ( const [ meshName, cnt ] of spec.segments ) {
			const isOrphan = orphan.has( meshName );
			for ( let i = 0; i < cnt && cursor < count; i ++, cursor ++ ) if ( isOrphan ) { on[ cursor ] = 0; orphans ++; }
		}
		if ( ! orphans ) return;
		const Attr = mesh.isInstancedMesh ? THREE.InstancedBufferAttribute : THREE.BufferAttribute;
		mesh.geometry.setAttribute( 'pfaSwitchOn', new Attr( on, 1 ) );
		out.nodes ++; out.rows += orphans; out.meshes.push( spec.gltf_node );
	} );
	if ( out.nodes ) note( `shrub/reed LOD: ${out.rows} placement(s) over ${out.nodes} node(s) have no LOD1 `
		+ `(${[ ...orphan ].join( ', ' )}) and are masked OUT of the switch — their card draws at every distance` );
	else note( `shrub/reed LOD: ${orphan.size} mesh(es) have no LOD1 but none of their rows were found in the scene` );
	return out;
}
