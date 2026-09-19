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
import { applyFoliage, farTreeIrradiance, irradianceRatio, recordShaderError, CARD_ENV } from './foliage.js';
import { applyInstanceIrradiance } from './lightmaps.js';
import { patchBakedMaterial } from './materials.js';
import { applyProbeEnv } from './probeEnv.js';
import { dequantizeUvs } from './uvDequant.js';
import { activateImpostorMeshes } from './impostors.js';
import { chunkInstancedMeshes } from './chunking.js';
import { resolveUrl } from './manifest.js';

const JOIN_TOL_M = 0.05;          // the export measured 5.8 mm; 50 mm is a generous ceiling
// A mesh tree must stand where its impostor stands (the lead's gate, 2026-09-17, after the export
// was found placing every far tree ~300 m off).  The REFUSAL runs on the two components that are
// exact by construction - the trunk's XZ and the base plane - because a real crown's bounding box is
// legitimately a metre or two off its trunk axis, while the defect is hundreds of metres.  The
// lead's own number, the distance from the mesh bbox centre to the impostor quad centre, is measured
// and reported beside them.
const PLACEMENT_XZ_TOL_M = 5.0;
// The base check is RELATIVE to the tree, because a prototype's own lowest vertex is not always its
// base plane: the LOD2 reduction keeps leaf cards and thins branches, so several prototypes' lowest
// geometry sits metres up the trunk (measured on the shipped glb: leaf primitives start at y = 3.1
// and 3.7 m).  A tree pushed vertically off its placement is out by hundreds of metres, not by a
// third of its height, so the tolerance is max(3 m, 0.4 x height).
const PLACEMENT_BASE_TOL_M = 3.0;
const PLACEMENT_BASE_TOL_REL = 0.4;
const CULL_MARGIN_M = 10;
const _m4 = /* one shared scratch matrix */ new THREE.Matrix4();         // see `out.update`: the water's mirrored camera stands further back
// The walk-up LOD1 set's own switch distance (?walkupmesh=).  15 m, not the LOD2's 12: the walk-in
// that failed QA 16 stops AT a tree, and a 3 m crown wants the LOD1 all the way in.
const WALKUP_DIST_M = 15;
/** `?walkupmesh=<m>` beats the block's own `draw_within_m`, which beats the 15 m default. */
function walkupDist( o, block ) {
	// Clamped like every other numeric switch (round-1 review 3): a negative value would kill the
	// mesh set outright and a huge one would submit all 254 rows, 3.77 M triangles, every frame.
	const cl = ( x ) => Math.min( Math.max( x, 0 ), 60 );
	if ( Number.isFinite( o.walkupDist ) ) return cl( o.walkupDist );
	if ( block && Number.isFinite( block.draw_within_m ) ) return cl( block.draw_within_m );
	return WALKUP_DIST_M;
}
const NEAR_LIGHT_MAX_M = 220;     // the site is 250 x 166 m: beyond this "the nearest crown" is meaningless

/**
 * PHASE 8b ITEM A — the CPU side of a distance switch, shared by the far-tree meshes and the
 * shrub/reed LOD1 set.
 *
 * Both sets are drawn by a fragment dissolve (`pfaSwitchDist` / `pfaSwitchSign`): beyond the switch
 * distance every fragment is discarded.  A discard costs the whole vertex shader and the whole
 * rasterisation first, and `renderer.info` counts the SUBMITTED triangle either way, so a set that
 * is invisible at a station is still paid for in full there.  QA 20 measured exactly that on
 * `env_shrubs.glb`: +463 922 triangles per pass at every station, +1.12 M per frame at the five
 * water stations (the planar Reflector draws the scene a second time), on mobile too.
 *
 * The cure is pure culling — nothing about WHAT is drawn changes, only whether it is submitted:
 *   1. `chunkInstancedMeshes` splits a site-spanning EXT_mesh_gpu_instancing batch into regional
 *      InstancedMeshes, each with a bounding sphere three's frustum test can bite on;
 *   2. per frame, a batch whose every ROW is beyond the switch limit is hidden outright.
 * The test is per ROW and not against the batch's bounding sphere, because a chunk scattered over
 * 60 m has a 30 m radius and `distance - radius` is small almost everywhere, so the batch would be
 * submitted at every station anyway.  A few hundred rows is nothing to test per frame.
 *
 * @param {THREE.Object3D} root    the loaded glb scene
 * @param {object|null} o.chunk    chunkInstancedMeshes options, or null to skip the split
 * @param {function} o.limit       () => metres; a row nearer than this keeps its batch visible
 * @returns {{stats:object, update:function, batches:Array}}
 */
export function buildDistanceCull( root, { chunk = null, limit } ) {
	const stats = { chunks: 0, split: 0, added: 0, batches: 0, drawCalls: 0, tris: 0 };
	if ( chunk ) {
		const ch = chunkInstancedMeshes( root, chunk );
		stats.chunks = ch.chunks; stats.split = ch.split; stats.added = ch.added;
	}
	const batches = [];
	const _row = new THREE.Vector3();
	root.traverse( ( mesh ) => {
		if ( ! mesh.isMesh ) return;
		mesh.frustumCulled = true;
		if ( ! mesh.geometry.boundingSphere ) mesh.geometry.computeBoundingSphere();
		if ( mesh.isInstancedMesh ) mesh.computeBoundingSphere();
		const s = ( mesh.isInstancedMesh ? mesh.boundingSphere : mesh.geometry.boundingSphere );
		const n = mesh.isInstancedMesh ? mesh.count : 1;
		const rows = new Float32Array( n * 3 );
		const rad = ( s ? s.radius : 0 );
		for ( let i = 0; i < n; i ++ ) {
			if ( mesh.isInstancedMesh ) _row.setFromMatrixPosition(
				_m4.fromArray( mesh.instanceMatrix.array, i * 16 ).premultiply( mesh.matrixWorld ) );
			else _row.setFromMatrixPosition( mesh.matrixWorld );
			rows[ i * 3 ] = _row.x; rows[ i * 3 + 1 ] = _row.y; rows[ i * 3 + 2 ] = _row.z;
		}
		// r3 review 4: for an InstancedMesh the rows ARE the placements and `CULL_MARGIN_M` covers the
		// crown around each one, so the row test is exact enough.  A NON-instanced mesh has ONE row -
		// its object origin - and a site-spanning one (a merged group, a chunk that was not split)
		// would be hidden while its geometry is still on screen.  Its own bounding radius is the pad
		// that makes the test a SPHERE test instead of an origin test.
		if ( s ) batches.push( { mesh, centre: s.center.clone(), radius: rad, rows,
			pad: mesh.isInstancedMesh ? 0 : rad } );
		stats.drawCalls ++;
		const idx = mesh.geometry.index;
		stats.tris += ( idx ? idx.count : mesh.geometry.getAttribute( 'position' ).count ) / 3
			* ( mesh.isInstancedMesh ? mesh.count : 1 );
	} );
	stats.batches = batches.length;
	const update = ( camera ) => {
		const lim = limit();
		// A non-finite or absurd limit must never hide the set: fall back to "everything visible".
		if ( ! Number.isFinite( lim ) ) { for ( const b of batches ) b.mesh.visible = true; return batches.length; }
		const cx = camera.position.x, cy = camera.position.y, cz = camera.position.z;
		let on = 0;
		for ( const b of batches ) {
			let near = false;
			const r = b.rows;
			// the batch's own limit: `lim` for the instanced sets, `lim + radius` where one row has
			// to stand for a whole mesh (r3 review 4)
			const l = lim + ( b.pad || 0 ), lim2 = l * l;
			for ( let i = 0; i < r.length; i += 3 ) {
				const dx = r[ i ] - cx, dy = r[ i + 1 ] - cy, dz = r[ i + 2 ] - cz;
				if ( dx * dx + dy * dy + dz * dz <= lim2 ) { near = true; break; }
			}
			b.mesh.visible = near;
			if ( near ) on ++;
		}
		return on;
	};
	return { stats, update, batches };
}

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

/** Exactly one occurrence, or the patch is refused (the same rule as foliage.js). */
function once( src, needle, replacement, what ) {
	const n = src.split( needle ).length - 1;
	if ( n !== 1 ) throw new Error( `foliageLazy patch "${what}": expected 1 occurrence, found ${n}` );
	return src.replace( needle, replacement );
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
	// manifest_v4 ships the block INLINE and split by consumer: `mesh.placements[]` is the per-tree
	// E_placement the MESH path wants, `impostor.prototypes[p].E_bake` the denominator the IMPOSTOR
	// path wants.  Both are normalised onto the block itself (`rows`, `prototypes`) so every consumer
	// reads one shape whether the block arrived inline or as the bake's sidecar json.
	if ( lit.mesh && Array.isArray( lit.mesh.placements ) ) lit.rows = lit.mesh.placements;
	if ( lit.impostor && lit.impostor.prototypes ) lit.prototypes = lit.impostor.prototypes;
	const has = ( b ) => b && b.prototypes && Array.isArray( b.rows || b.placements || b.instances );
	if ( has( lit ) ) {
		note( `far-tree lighting: inline in the manifest (${lit.schema || 'no schema'}), ${lit.rows.length} `
			+ `placement row(s), ${Object.keys( lit.prototypes ).length} prototype E_bake value(s)` );
		return lit;
	}
	const spec = lit.json || ( lit.instance_irradiance && lit.instance_irradiance.json );
	if ( ! spec ) { note( 'far-tree lighting: the block names neither rows nor a json to fetch' ); return null; }
	const got = await firstThatLoads( lazyUrlCandidates( manifest.baseUrl, spec ), fetchJson, note, 'far-tree lighting json' );
	if ( ! got ) return null;
	const j = got.value;
	// schema pfa-phase6/gate4-instance-irradiance/2: the rows are NESTED, one list per LOD2 mesh
	// (`meshes[<mesh>].placements[] = { object, loc, rgb, mean_all, cov }`), and the top-level
	// `placements` is a COUNT, not a list.  Flattened here into one row list, which is the only shape
	// every consumer reads.
	const flat = [];
	for ( const rec of Object.values( j.meshes || {} ) )
		for ( const r of ( rec && rec.placements ) || [] ) flat.push( r );
	lit.rows = flat.length ? flat
		: ( Array.isArray( j.placements ) ? j.placements : ( Array.isArray( j.rows ) ? j.rows : null ) );
	lit.prototypes = j.prototypes || lit.prototypes || null;
	lit.schema = j.schema || lit.schema || null;
	lit.reduce = j.reduce || lit.reduce || null;
	note( `far-tree lighting: ${got.url.split( '/' ).pop()} (${lit.schema || 'no schema'}), `
		+ `${( lit.rows || [] ).length} placement row(s), ${Object.keys( lit.prototypes || {} ).length} prototype E_bake value(s)` );
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

/**
 * The same tinted albedo on a lazily loaded root.  `applyFoliageTextures` runs before the first frame,
 * over the glbs that are in by then; env_trees.glb and env_shrubs.glb arrive later and carry the same
 * material NAMES with the same untinted source card, so they take the same replacement here - one
 * material must not look different because of which file it was loaded from.
 */
export function applyFoliageAlbedo( root, maps, note = () => {}, trnMaps = null ) {
	let n = 0;
	if ( ! maps ) return n;
	const seen = new Set();
	root.traverse( ( m ) => {
		if ( ! m.isMesh ) return;
		for ( const mat of Array.isArray( m.material ) ? m.material : [ m.material ] ) {
			const t = mat && maps[ mat.name ];
			if ( ! t || seen.has( mat.uuid ) ) continue;
			seen.add( mat.uuid );
			const old = mat.map;
			if ( old ) {
				t.wrapS = old.wrapS; t.wrapT = old.wrapT; t.channel = old.channel;
				// 8e DEPENDENCY (lead, Phase 8a).  three r186 applies sampler state only inside
				// `uploadTexture`, so a wrap written after the first upload never reaches the GPU:
				// the eager near-tree pass uploads this ONE shared albedo at the glb's clamp, and
				// when env_trees.glb arrives with 8e's REPEAT leaf samplers the copy above would be
				// silently ignored.  The translucency map beside it has always had this line.
				// Pixel-neutral on today's assets (every foliage sampler is clamp today).
				t.needsUpdate = true;
				// PHASE 8b ITEM D — the translucency FACTOR map is sampled with these same leaf-card
				// UVs, so it takes this root's sampler exactly as the albedo does.  Without this the
				// trn map kept whatever the FIRST pass (env.glb) set, and 8e's REPEAT samplers on
				// env_trees.glb would tile the albedo while the trn map clamped.
				const tr = trnMaps && trnMaps[ mat.name ];
				if ( tr ) {
					// Both maps are ONE texture object shared by every root that uses this material
					// name, so two roots with different samplers cannot both be served: say so rather
					// than let the later root silently re-wrap the earlier one.
					if ( ( tr.wrapS !== old.wrapS || tr.wrapT !== old.wrapT ) && tr.userData.pfaWrapFrom )
						note( `foliage textures: ${mat.name}'s sampler in ${root.name} `
							+ `(${old.wrapS}/${old.wrapT}) disagrees with ${tr.userData.pfaWrapFrom}'s `
							+ `(${tr.wrapS}/${tr.wrapT}); the albedo and translucency maps are SHARED, so `
							+ 'both roots now use this one — the export must patch the samplers together' );
					tr.wrapS = old.wrapS; tr.wrapT = old.wrapT;
					tr.needsUpdate = true;
					tr.userData.pfaWrapFrom = root.name || 'a lazily loaded glb';
				}
			}
			mat.map = t;
			mat.needsUpdate = true;
			n ++;
		}
	} );
	if ( n ) note( `foliage textures: the tinted albedo on ${n} material(s) of ${root.name}` );
	return n;
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
	// 6c ROUND 3, ITEM 3 — THE WALK-UP SET.  `trees.walkup_mesh` is the same contract as
	// `trees.far_mesh` (a glb of instance rows joined to the same placements by translation), so it is
	// consumed by THIS loader with the block swapped, not by a second one: the positional join, the
	// crown-deviation gate, the per-placement irradiance, the leaf shader and the impostor complement
	// are all the same code and can only agree if they are literally the same lines.
	//   * where a walk-up LOD1 exists it REPLACES the LOD2 set rather than stacking with it - the LOD2
	//     only ever drew inside 12 m, which is inside the walk-up's own 15 m, so drawing both would
	//     put two crowns in the same place for the whole band;
	//   * the tier order the brief sets is therefore: LOD1 within `?walkupmesh=` (15 m), else the LOD2
	//     within `?fartreemesh=` (12 m), else the impostor;
	//   * `o.walkup` is 'off' / '0' to force the LOD2 set back (the A/B), and a walk-up glb that fails
	//     the join falls back to the LOD2 block instead of leaving every far tree an impostor.
	const trees = ( manifest.raw && manifest.raw.trees ) || {};
	const askWalk = String( o.walkup === undefined || o.walkup === null ? '' : o.walkup ).toLowerCase();
	const wantWalkup = !! ( trees.walkup_mesh && trees.walkup_mesh.glb ) && askWalk !== '0' && askWalk !== 'off';
	// The walk-up block states what it SHARES instead of repeating it, "so the two can never
	// disagree" (manifest `placements.same_as`, `lighting`): the placements and the per-placement
	// irradiance are trees.far_mesh's, row for row, and this set ships no COLOR_0 by design because
	// the round-3 interior term carries the occlusion.  Resolving those references here is the whole
	// difference between the two sets as far as this loader is concerned.
	let fm = trees.far_mesh;
	out.set = 'far_mesh';
	if ( wantWalkup ) {
		const w = trees.walkup_mesh;
		const far = trees.far_mesh || {};
		const place = Array.isArray( w.placements ) ? w.placements
			: ( w.placements && w.placements.same_as ? far.placements : null );
		const lighting = ( w.lighting && typeof w.lighting === 'object' ) ? w.lighting : far.lighting;
		if ( Array.isArray( place ) && place.length ) {
			fm = { ...w, placements: place, lighting, impostor_join: w.impostor_join || far.impostor_join };
			out.set = 'walkup_mesh';
		} else {
			note( 'far-tree meshes: trees.walkup_mesh carries no placements and none can be resolved from '
				+ 'trees.far_mesh — the LOD2 set is used' );
		}
	}
	if ( ! fm || ! fm.glb ) { note( 'far-tree meshes: no trees.far_mesh in the manifest (export item A)' ); return out; }
	if ( o.mode === '0' ) { note( 'far-tree meshes SUPPRESSED (?fartreelight=0): the 127 far trees stay impostors' ); return out; }
	if ( out.set === 'walkup_mesh' ) note( `far-tree meshes: the WALK-UP set trees.walkup_mesh (${fm.glb}) replaces `
		+ `trees.far_mesh (item 3); ${fm.placements.length} placement(s) and the per-placement irradiance are read from `
		+ `far_mesh as the manifest says; it draws within ${walkupDist( o, fm )} m, the impostor beyond` );
	const placements = Array.isArray( fm.placements ) ? fm.placements : [];
	if ( ! placements.length ) { out.error = 'trees.far_mesh.placements is empty'; note( `far-tree meshes: ${out.error}` ); return out; }
	out.placements = placements.length;

	const t0 = performance.now();
	const got = await firstThatLoads( lazyUrlCandidates( manifest.baseUrl, fm.glb ), loadGlb, note, fm.glb );
	if ( ! got ) {
		out.error = 'not found';
		// The walk-up glb is an extra file on the wire: if it is not deployed yet (or 404s), the LOD2
		// set must still draw.  The manifest's own `load` note says as much - "until it is in, every
		// tree is the 8 k far mesh" - and it is the same fallback a failed join takes.
		if ( out.set === 'walkup_mesh' ) {
			note( `far-tree meshes: ${fm.glb} did not load — falling back to trees.far_mesh (the LOD2 set)` );
			const back = await loadFarTrees( { ...o, walkup: '0' } );
			back.walkupError = `${fm.glb} not found`;
			back.walkupFellBack = true;
			return back;
		}
		return out;
	}
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
	applyFoliageAlbedo( root, o.albedoMaps, note, o.trnMaps );
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
			rowsOf.push( { mesh, row: i, placement: p || null, residual_m: p ? d : null, mtx: m.clone() } );
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
		// A walk-up set that will not join must not cost the round-16b behaviour: fall back to the
		// LOD2 block, once, and report both.  (`walkup: '0'` is what that call means.)
		if ( out.set === 'walkup_mesh' ) {
			note( 'far-tree meshes: falling back to trees.far_mesh (the LOD2 set) for this session' );
			const back = await loadFarTrees( { ...o, walkup: '0' } );
			back.walkupError = out.error;
			back.walkupFellBack = true;
			return back;
		}
		return out;
	}

	// ---- DOES THE MESH STAND WHERE ITS IMPOSTOR STANDS? ---------------------------------------
	// The join above matches an instance ROW's translation to a placement, which says nothing about
	// where the GEOMETRY of that row ends up: a prototype mesh that kept its source object's world
	// matrix draws its tree hundreds of metres from its own instance origin, and every metric in the
	// frame would still look plausible.  So the world bounding box of each placement's meshes is
	// compared with the centre of the impostor quad that placement has always had.  Over the tolerance
	// the meshes are NOT drawn: a far tree in the wrong place is worse than the impostor it replaces.
	const impProtos = ( manifest.gate3 && manifest.gate3.impostors && manifest.gate3.impostors.prototypes ) || {};
	const placeBox = new Map();
	const _b = new THREE.Box3();
	for ( const r of rowsOf ) {
		if ( ! r.placement ) continue;
		if ( ! r.mesh.geometry.boundingBox ) r.mesh.geometry.computeBoundingBox();
		_b.copy( r.mesh.geometry.boundingBox ).applyMatrix4( r.mtx );
		const cur = placeBox.get( r.placement.index );
		if ( cur ) cur.union( _b ); else placeBox.set( r.placement.index, _b.clone() );
	}
	const dev = [];
	const _c = new THREE.Vector3(), _mid = new THREE.Vector3();
	for ( const p of placements ) {
		const box = placeBox.get( p.index ), proto = impProtos[ p.prototype ];
		if ( ! box ) continue;
		box.getCenter( _mid );
		// the trunk base, in three space: the impostor quad's XZ is exactly this
		const bx = p.loc[ 0 ], bz3 = - p.loc[ 1 ], by = p.loc[ 2 ];
		const xz = Math.hypot( _mid.x - bx, _mid.z - bz3 );
		const base = Math.abs( box.min.y - by );
		let centre = null;
		if ( proto && proto.heightAboveBase > 0 ) {
			// the impostor's own placement rule, verbatim (manifest impostors.placement)
			const sc = ( p.height_m || proto.heightAboveBase ) / proto.heightAboveBase;
			_c.set( bx, by + ( proto.centreZ || 0 ) * sc, bz3 );
			centre = _mid.distanceTo( _c );
		}
		dev.push( { index: p.index, xz, base, centre,
			baseTol: Math.max( PLACEMENT_BASE_TOL_M, PLACEMENT_BASE_TOL_REL * ( p.height_m || 0 ) ) } );
	}
	const worst = ( key ) => dev.reduce( ( a, b ) => ( ( b[ key ] ?? - 1 ) > ( a[ key ] ?? - 1 ) ? b : a ), dev[ 0 ] || {} );
	const med = ( key ) => {
		const v = dev.map( ( x ) => x[ key ] ).filter( ( x ) => x !== null ).sort( ( a, b ) => a - b );
		return v.length ? + v[ Math.floor( v.length / 2 ) ].toFixed( 3 ) : null;
	};
	const wXz = worst( 'xz' ), wBase = worst( 'base' ), wC = worst( 'centre' );
	const over = dev.filter( ( x ) => x.xz > PLACEMENT_XZ_TOL_M || x.base > x.baseTol );
	out.placementCheck = {
		compared: dev.length,
		tolerance: { xz_m: PLACEMENT_XZ_TOL_M, base_m: `max(${PLACEMENT_BASE_TOL_M}, ${PLACEMENT_BASE_TOL_REL} x height)` },
		max_xz_m: dev.length ? + wXz.xz.toFixed( 3 ) : null, max_xz_at: dev.length ? wXz.index : null,
		max_base_m: dev.length ? + wBase.base.toFixed( 3 ) : null,
		// the lead's number: mesh bbox centre vs impostor quad centre
		max_centre_m: wC && wC.centre !== null && wC.centre !== undefined ? + wC.centre.toFixed( 3 ) : null,
		median_xz_m: med( 'xz' ), median_centre_m: med( 'centre' ),
		over_tolerance: over.length,
	};
	if ( over.length ) {
		out.error = `${over.length}/${dev.length} far-tree mesh(es) do not stand where their impostor stands `
			+ `(worst trunk offset ${out.placementCheck.max_xz_m} m at placement ${out.placementCheck.max_xz_at}, `
			+ `worst base offset ${out.placementCheck.max_base_m} m; tolerances ${PLACEMENT_XZ_TOL_M} m horizontally, `
			+ `max(${PLACEMENT_BASE_TOL_M}, ${PLACEMENT_BASE_TOL_REL} x height) vertically)`;
		note( `far-tree meshes: PLACEMENT CHECK FAILED — ${out.error}; the meshes are NOT drawn and every far tree `
			+ 'stays its impostor.  This is an EXPORT defect (the prototype mesh keeps its source world matrix), not a flag.' );
		scene.remove( root );
		return out;
	}
	note( `far-tree meshes: placement check OK over ${dev.length} placement(s) — trunk offset max `
		+ `${out.placementCheck.max_xz_m} m (median ${out.placementCheck.median_xz_m}), base offset max `
		+ `${out.placementCheck.max_base_m} m, mesh bbox centre vs impostor quad centre max `
		+ `${out.placementCheck.max_centre_m} m (median ${out.placementCheck.median_centre_m})` );

	// ---- E_placement per row ------------------------------------------------------------------
	const lit = fm.lighting;
	const rows = lit && ( lit.rows || lit.instances || ( Array.isArray( lit.placements ) ? lit.placements : null ) );
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
		const col = mesh.isMesh && mesh.geometry.getAttribute( 'color' );
		if ( ! col ) return;
		out.ao = true;
		// The bake ships AO as COLOR_0, and gltfpack writes it as a normalized VEC4: three's
		// `color_fragment` multiplies the WHOLE vec4 into diffuseColor, so a stored alpha below 1
		// would multiply the leaf's alpha as well and the MASK cutoff would eat the canopy.  AO is an
		// rgb factor; the alpha is forced to opaque here, once, and the count is reported.
		if ( col.itemSize === 4 && ! mesh.geometry.userData.pfaAoAlphaFixed ) {
			mesh.geometry.userData.pfaAoAlphaFixed = true;
			const one = col.normalized ? ( col.array.BYTES_PER_ELEMENT === 1 ? 255 : 65535 ) : 1;
			let touched = 0;
			for ( let i = 0; i < col.count; i ++ ) if ( col.array[ i * 4 + 3 ] !== one ) { col.array[ i * 4 + 3 ] = one; touched ++; }
			if ( touched ) { col.needsUpdate = true; out.aoAlphaForced = ( out.aoAlphaForced || 0 ) + touched; }
		}
		// The manifest states the encode as prose ("COLOR_0 = sqrt(linear / range); viewer decodes
		// linear = COLOR_0^2 * range"), so it is MATCHED, not compared: reading it as the token
		// "gamma2" would silently leave the AO as sqrt(AO) - every crown a stop too bright.
		const enc = String( c0.encode || 'none' );
		const gamma2 = /sqrt|\^ ?2|\*\s*color_0|gamma-? ?2/i.test( enc );
		const aoRange = ( typeof c0.range === 'number' && c0.range > 0 ) ? c0.range : 1;
		out.aoEncode = gamma2 ? `gamma2 x range ${aoRange.toFixed( 6 )}` : 'linear';
		const aoEnv = Number.isFinite( o.aoEnv ) ? Math.min( Math.max( o.aoEnv, 0 ), 1 ) : 1;
		out.aoEnv = aoEnv;
		for ( const mat of Array.isArray( mesh.material ) ? mesh.material : [ mesh.material ] ) {
			if ( ! mat || mat.userData.pfaAoPatched ) continue;
			mat.userData.pfaAoPatched = true;
			const prev = mat.onBeforeCompile;
			mat.onBeforeCompile = function ( sh, r ) {
				if ( prev ) prev.call( this, sh, r );
				try {
					// AO IS THE ENVIRONMENT'S VISIBILITY, not just an albedo multiplier.  glTF's COLOR_0
					// only tints base colour, so three applies it to the DIFFUSE ALBEDO and leaves the
					// image-based specular (and KHR_materials_sheen, which is an environment lobe too)
					// sampling the whole sky from every interior leaf the bake measured as occluded -
					// which is what made an 8 k-triangle LOD2 crown read cream-white against the Cycles
					// reference's dark green.  The bake's own 0-1 AO is exactly the visibility factor
					// those terms want, so it multiplies them here as well.  ?farao= is the A/B.
					if ( gamma2 ) sh.fragmentShader = once( sh.fragmentShader, '#include <color_fragment>',
						`#include <color_fragment>\n\tdiffuseColor.rgb *= vColor.rgb * ${aoRange.toFixed( 7 )};   // PFA: AO = COLOR_0^2 * range`,
						'AO gamma2 decode' );
					if ( aoEnv > 0 ) {
						const ao = gamma2 ? `( vColor.rgb * vColor.rgb * ${aoRange.toFixed( 7 )} )` : 'vColor.rgb';
						// The anchor is `lights_fragment_end`, NOT `lights_fragment_maps`: patchBakedMaterial
						// has already replaced the maps INCLUDE with its expanded chunk, so the include
						// string is gone by the time this runs.  `lights_fragment_end` survives every
						// patch in the chain (the translucency one re-emits it), and it is where
						// RE_IndirectDiffuse / RE_IndirectSpecular consume these three terms - scaling
						// `radiance` there covers the sheen lobe too, which is computed from it.
						sh.fragmentShader = once( sh.fragmentShader, '#include <lights_fragment_end>',
							'{\n'
							+ `\t\tvec3 pfaAoV = mix( vec3( 1.0 ), ${ao}, ${aoEnv.toFixed( 4 )} );\n`
							+ '\t\tiblIrradiance *= pfaAoV;\n\t\tradiance *= pfaAoV;\n\t}\n'
							+ '\t#include <lights_fragment_end>',
							'AO on the environment terms' );
					}
				} catch ( e ) { recordShaderError( `far-tree AO on ${mat.name || '(unnamed)'}`, e ); }
			};
			mat.needsUpdate = true;
		}
	} );

	if ( o.probeTexture ) applyProbeEnv( root, o.probeTexture, { note: () => {} } );

	// ---- the leaf shader and the LOD dissolve, sharing the first pass's uniforms ---------------
	// `?fartreemesh=` — the FAR trees' own switch distance.  MEASURED (web/README.md): at station 2 the
	// modulated impostor matches the Cycles reference on every column of the far-tree box while the
	// LOD2 mesh reads 1.96x and twice the reference's high-frequency detail, because the atlas carries
	// the self-shadowing of the DENSE source tree and an 8 k-triangle LOD2 crown has almost none of it.
	// So the mesh is kept for what only a mesh can do - silhouette and parallax when the walker is a
	// few metres away - and the atlas carries every station.
	const farDist = out.set === 'walkup_mesh' ? walkupDist( o, fm )
		: ( Number.isFinite( o.farMeshDist ) ? o.farMeshDist : 12 );

	// `?fartrn=` — the translucency scale on the FAR-tree meshes alone.  The Phase 5 mix adds a back
	// lobe of the full unoccluded sun, and Cycles' own version of that lobe is occluded by the rest of
	// the crown; the near trees carry a dense LOD1 canopy that hides most of it, while a far tree is an
	// 8 k-triangle LOD2 with big cards and nothing to shadow them, so the same term over-lights it.
	// Measured at cam02, see web/README.md.
	const fol = applyFoliage( {
		scene: root, sun: o.sun, note, msaa: o.msaa, vertexIrrScale: 0,
		sharedUniforms: o.foliageReport ? o.foliageReport.shared.uniforms : null,
		normalBlend: o.normalBlend, cardNormalBlend: o.cardNormalBlend,
		interior: o.interior, cardInterior: o.cardInterior, normalGate: o.normalGate, mipBias: o.mipBias,
		trnScale: Number.isFinite( o.farTrn ) ? o.farTrn : o.trnScale,
		trnShrubs: o.trnShrubs, trnMaps: o.trnMaps,
		// the FAR trees' own switch distance (see `farMeshDist`), not the near trees' 40 m
		meshDist: farDist, fadeBand: o.fadeBand,
	} );
	out.meshDist = farDist;
	out.trnScale = Number.isFinite( o.farTrn ) ? o.farTrn : o.trnScale;
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
		byId.set( t.id, { switchCentre: [ c.x, c.y, c.z ], dist: farDist, irr: far.byIndex.get( i ) || null } );
	} );
	out.impostors = activateImpostorMeshes( o.impostorGroup, byId, note );

	// ---- draw cost: split the site-spanning batches, then cull by the switch distance ----------
	// 254 rows x ~8 k tris is 1.03 M triangles that would be vertex-shaded every frame even though
	// the fragment side discards all but the trees inside `treeMeshDist`.  Chunking gives each group
	// its own bounding sphere (so three's frustum test bites) and the per-frame test below hides any
	// chunk whose whole sphere is beyond the switch distance.  Both are pure culling: nothing about
	// what is drawn changes, only whether it is submitted.
	const shared = o.foliageReport ? o.foliageReport.shared.uniforms : null;
	const cull = buildDistanceCull( root, {
		chunk: { minRadius: 12, minCount: 2, maxDepth: 3, gain: 0.95, budget: 256 },
		// the FAR trees' own distance, not the shared (near-tree) one - otherwise 1.0 M triangles are
		// submitted out to 40 m for fragments the dissolve throws away at 12.
		// + CULL_MARGIN_M because the WATER draws the scene a second time from the mirrored camera,
		// which stands a few metres further from a tree than this one does.  Without the margin a tree
		// right at the switch could be culled for the main camera while the reflection's own dissolve
		// wanted to draw it - and its impostor, being the exact complement, would not draw either.
		limit: () => farDist + ( shared && shared.pfaFadeBand ? shared.pfaFadeBand.value : 5 ) + CULL_MARGIN_M,
	} );
	const ch = cull.stats;
	out.chunks = ch.chunks; out.split = ch.split; out.added = ch.added;
	out.drawCalls = ch.drawCalls; out.tris = ch.tris;
	out.update = cull.update;
	out.batches = ch.batches;
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
	applyFoliageAlbedo( root, o.albedoMaps, note, o.trnMaps );
	scene.add( root );
	root.updateMatrixWorld( true );

	// the SAME per-placement irradiance, in this glb's own row order (manifest `shrubs.lod1.join`)
	const bound = applyInstanceIrradiance( scene, manifest.gate3, note, 'auto',
		{ root, block: lod1Irr ? { ...lod1Irr, placements: lod1Irr.placements ?? block.placements } : null,
			// the SAME cov exponent as the LOD2 cards, or crossing the LOD distance would change a
			// shrub's level - which is the one thing the shared irradiance exists to prevent
			covScale: o.shrubCov,
			scale: manifest.gate3 ? manifest.gate3.scale : Math.PI, label: 'shrub/reed LOD1 irradiance' } );
	out.lod1Nodes = bound.nodes; out.lod1Rows = bound.rows;
	if ( bound.errors.length ) {
		out.errors = bound.errors;
		note( 'shrub/reed LOD1: the irradiance binding failed, the LOD1 set is NOT drawn (the LOD2 cards stay)' );
		scene.remove( root );
		return out;
	}
	if ( o.probeTexture ) applyProbeEnv( root, o.probeTexture, { note: () => {} } );

	// `?shrubenv=` — the ENVIRONMENT term on the LOD1 meshes only.  A LOD2 card is one flat quad whose
	// normal reflects the horizon; a LOD1 shrub is a hundred leaves facing every direction, including
	// up, and their diffuse is a single direction-independent baked irradiance while their SPECULAR
	// (plus the material's KHR_materials_sheen, which is an environment lobe too) is free to sample the
	// blue sky from every interior leaf that the bake would have occluded.  Measured, see web/README.md.
	// The LOD2 cards' `?cardenv=` default, shared so the LOD switch cannot change a shrub's level.
	const envScale = Number.isFinite( o.envScale ) ? o.envScale : CARD_ENV;
	if ( envScale !== 1 ) {
		let n = 0;
		root.traverse( ( m ) => {
			if ( ! m.isMesh ) return;
			for ( const mat of Array.isArray( m.material ) ? m.material : [ m.material ] ) {
				if ( ! mat || mat.userData.pfaEnvScaled ) continue;
				mat.userData.pfaEnvScaled = envScale;
				mat.envMapIntensity = ( mat.envMapIntensity ?? 1 ) * envScale;
				if ( mat.sheenColor ) mat.sheenColor.multiplyScalar( envScale );
				mat.needsUpdate = true; n ++;
			}
		} );
		out.envScale = envScale;
		note( `shrub/reed LOD1: environment term x${envScale} on ${n} material(s) (?shrubenv=)` );
	}

	// the leaf shader on the LOD1 cards, then the switch: LOD1 within `dist` (sign +1)
	const fol = applyFoliage( {
		scene: root, sun: o.sun, note, msaa: o.msaa, vertexIrrScale: 0,
		sharedUniforms: o.foliageReport ? o.foliageReport.shared.uniforms : null,
		normalBlend: o.normalBlend, cardNormalBlend: o.cardNormalBlend,
		interior: o.interior, cardInterior: o.cardInterior, normalGate: o.normalGate, mipBias: o.mipBias,
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

	// PHASE 8b ITEM A — the CPU side of that switch.  Until this round the LOD1 set had only the
	// fragment dissolve above: every one of its 463 922 triangles was submitted at every station and
	// in the water's mirrored pass as well, for fragments that are discarded the moment the walker is
	// more than `dist` metres away (QA 20 §2, +1.12 M triangles per frame at the five water stations).
	// `?shrubcull=0` restores that behaviour for the A/B; `?shrubcull=<n>` tunes the chunk budget.
	if ( o.cull !== '0' ) {
		const budget = Number.isFinite( parseFloat( o.cull ) ) ? Math.max( 0, parseFloat( o.cull ) ) : 48;
		const cull = buildDistanceCull( root, {
			// minRadius 12 m: a shrub batch tighter than that is already local enough to frustum-cull.
			// The budget is the ADDED draw calls over the whole set.  SWEPT same-session against 128
			// (web/README.md "Phase 8b fix round"): 128 cuts 0.4 M more triangles at the hero but adds
			// 41 draw calls at cam02, and interleaved B/C pairs put its frame time at or above 48's at
			// four of the six stations - the extra draw calls cost what the triangles save.  48 keeps
			// every station's draw count within 13 of the pre-8b figure and still cuts 0.33-2.02 M
			// triangles per frame.
			chunk: budget > 0 ? { minRadius: 12, minCount: 2, maxDepth: 3, gain: 0.95, budget } : null,
			// the shrub set's OWN switch distance (25 m mobile / 30 m desktop), the shared fade band,
			// and the same CULL_MARGIN_M the far trees take for the water's mirrored camera.
			limit: () => dist + ( o.foliageReport && o.foliageReport.shared.uniforms.pfaFadeBand
				? o.foliageReport.shared.uniforms.pfaFadeBand.value : ( Number.isFinite( o.fadeBand ) ? o.fadeBand : 5 ) )
				+ CULL_MARGIN_M,
		} );
		out.chunks = cull.stats.chunks; out.split = cull.stats.split; out.added = cull.stats.added;
		out.batches = cull.stats.batches; out.drawCalls = cull.stats.drawCalls; out.tris = cull.stats.tris;
		out.update = cull.update;
		out.cullBudget = budget;
	} else {
		note( 'shrub/reed LOD1: the distance CULL is off (?shrubcull=0) — the whole LOD1 set is submitted '
			+ 'at every station and the dissolve throws its fragments away beyond the switch' );
		out.update = null;
	}

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
		+ ( out.masked ? `, ${out.masked} of them carrying the per-row mask for the placements with no LOD1` : '' )
		+ ( out.update ? `; ${Math.round( out.tris / 1000 )} k placed tris in ${out.batches} batch(es) `
			+ `(${out.split} split into ${out.chunks}, +${out.added} draw calls), culled per frame beyond `
			+ `${dist} m + band + ${CULL_MARGIN_M} m (?shrubcull=)` : '' ) );
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
	const out = { size: null, albedo: 0, translucency: 0, normals: 0, materials: [], missing: [], bytes: 0,
		// item d: the wrap each translucency map took, and where it came from
		trnWrap: {} };
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
	const trnMaps = {}, albedoMaps = {};
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
		// PHASE 8b ITEM D (lead) — the translucency map is sampled with the SAME leaf-card UVs as the
		// albedo it is derived from, so it must take the albedo's own glTF SAMPLER wrap mode and not a
		// hard-coded one (neither clamp, which it was, nor repeat).  Phase 8e scales the leaf-card UVs
		// by k = 2.0 (willow 1.5) on env_trees.glb and patches that glb's leaf samplers to REPEAT: a
		// clamped translucency map would then smear its edge texel across every tile while the albedo
		// tiled correctly, and the defect would read as a translucency artefact, not as a wrap bug.
		// Today's shipped samplers are all clamp, so this changes no pixel on the current assets.
		// r3 review 3: ONE sampler rule for BOTH maps.  The albedo replacement and the translucency
		// factor are one texture object each per material NAME, shared by every material that carries
		// it, and they are sampled with the same UVs - so the wrap has to be decided once, here, and
		// written to both.  Before this the translucency took `srcMaps[0]` (the FIRST material of the
		// name) while the albedo took `mat.map` inside the per-material loop (the LAST one won), so
		// two eager materials of one name that disagreed about wrap ended with albedo REPEAT and
		// translucency CLAMP - the exact mis-serve item d exists to prevent - and the note that fired
		// described only the translucency's choice.
		const srcMaps = mats.map( ( m ) => m.map ).filter( Boolean );
		const wrapS = srcMaps.length ? srcMaps[ 0 ].wrapS : THREE.ClampToEdgeWrapping;
		const wrapT = srcMaps.length ? srcMaps[ 0 ].wrapT : THREE.ClampToEdgeWrapping;
		if ( srcMaps.some( ( t ) => t.wrapS !== wrapS || t.wrapT !== wrapT ) )
			note( `foliage textures ${name}: this material's own albedo samplers disagree about wrap; `
				+ `the first (${wrapS}/${wrapT}) is used for BOTH the tinted albedo and the `
				+ 'translucency factor — the export must patch the samplers of one material name together' );
		if ( tTex ) {
			tTex.colorSpace = THREE.NoColorSpace;          // a factor, not a colour
			tTex.wrapS = wrapS; tTex.wrapT = wrapT;
			tTex.userData.pfaWrapFrom = srcMaps.length ? 'the first pass (the env.glb samplers)' : null;
			out.trnWrap[ name ] = [ wrapS, wrapT, srcMaps.length ? 'from the glb albedo sampler' : 'no albedo in the glb: clamp' ];
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
				// the SAME decision the translucency map above took, not this material's own
				aTex.wrapS = wrapS;
				aTex.wrapT = wrapT;
				aTex.anisotropy = Math.max( aTex.anisotropy || 1, 8 );
				aTex.channel = old ? old.channel : 0;
				aTex.needsUpdate = true;
				mat.map = aTex;
				mat.needsUpdate = true;
			}
		}
		if ( aTex ) {
			aTex.userData.pfaWrapFrom = srcMaps.length ? 'the first pass (the env.glb samplers)' : null;
			out.albedoWrap = out.albedoWrap || {};
			out.albedoWrap[ name ] = [ wrapS, wrapT, srcMaps.length ? 'from the glb albedo sampler' : 'no albedo in the glb: clamp' ];
			out.albedo ++; out.materials.push( name ); albedoMaps[ name ] = aTex;
		}
	}
	out.trnMaps = trnMaps;
	out.albedoMaps = albedoMaps;
	// item d: one line naming the wrap modes taken, so an 8e sampler change is visible in the boot log
	const wraps = [ ...new Set( Object.values( out.trnWrap ).map( ( w ) => `${w[ 0 ]}/${w[ 1 ]}` ) ) ];
	note( `foliage textures (materials.foliage, ${out.size} px): ${out.albedo} tinted albedo(s) and `
		+ `${out.translucency} translucency factor map(s) on ${out.materials.join( ', ' )}`
		+ ( wraps.length ? `; translucency wrap taken from the glb albedo sampler(s): ${wraps.join( ', ' )} `
			+ `(${THREE.ClampToEdgeWrapping} = clamp, ${THREE.RepeatWrapping} = repeat)` : '' )
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
	// The node's OWN row order, from its segments: 1 = this placement has a LOD1, 0 = it never does.
	const nodeMask = new Map();
	for ( const spec of nodes.values() ) {
		const total = spec.segments.reduce( ( a, x ) => a + x[ 1 ], 0 );
		const on = new Float32Array( total ).fill( 1 );
		let cursor = 0, orphans = 0;
		for ( const [ meshName, cnt ] of spec.segments ) {
			const isOrphan = orphan.has( meshName );
			for ( let i = 0; i < cnt && cursor < total; i ++, cursor ++ ) if ( isOrphan ) { on[ cursor ] = 0; orphans ++; }
		}
		if ( orphans ) nodeMask.set( spec.gltf_node, on );
	}
	const doneNodes = new Set();
	root.traverse( ( mesh ) => {
		if ( ! mesh.isMesh ) return;
		const gn = mesh.userData && mesh.userData.pfaGltfNode;
		const full = nodeMask.get( gn );
		if ( ! full ) return;
		const count = mesh.isInstancedMesh ? mesh.count : 1;
		// QA-11d-1 chunking has already split some of these batches, and a chunk carries its source's
		// userData (so the same gltf_node) but only SOME of its rows.  `pfaChunk.indices` is the map
		// back; without it the mask would be written at the wrong row of every chunk.
		const idx = mesh.userData.pfaChunk && mesh.userData.pfaChunk.indices;
		if ( idx && idx.length !== count ) { out.errors = ( out.errors || [] ).concat( `chunk ${mesh.name}: ${idx.length} indices for ${count} rows` ); return; }
		if ( ! idx && count !== full.length ) {
			out.errors = ( out.errors || [] ).concat( `node ${gn}: ${count} rows in the scene, ${full.length} in the manifest` );
			return;
		}
		const on = new Float32Array( count );
		let orphans = 0;
		for ( let i = 0; i < count; i ++ ) {
			on[ i ] = full[ idx ? idx[ i ] : i ];
			if ( ! on[ i ] ) orphans ++;
		}
		const Attr = mesh.isInstancedMesh ? THREE.InstancedBufferAttribute : THREE.BufferAttribute;
		mesh.geometry.setAttribute( 'pfaSwitchOn', new Attr( on, 1 ) );
		if ( orphans ) { out.rows += orphans; out.meshes.push( gn ); }
		if ( ! doneNodes.has( gn ) ) { doneNodes.add( gn ); out.nodes ++; }
	} );
	if ( out.nodes ) note( `shrub/reed LOD: ${out.rows} placement(s) over ${out.nodes} node(s) have no LOD1 `
		+ `(${[ ...orphan ].join( ', ' )}) and are masked OUT of the switch — their card draws at every distance` );
	else note( `shrub/reed LOD: ${orphan.size} mesh(es) have no LOD1 but none of their rows were found in the scene` );
	return out;
}
