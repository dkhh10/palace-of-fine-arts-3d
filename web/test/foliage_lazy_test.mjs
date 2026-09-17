// 6c round 2 — the lazy foliage consumers, tested against the REAL manifest with a synthetic scene.
//
// Nothing here needs a GPU: three's scene graph, the geometry attributes and the material patches are
// all plain JS, and `loadFarTrees` takes its glb through an injected `loadGlb`.  The synthetic glb is
// built from the manifest's own placement table, exactly as gltfpack emits it (one instanced node per
// prototype per material, rows in the manifest's order), so the POSITIONAL JOIN is tested on the real
// 127 placements and the real 254 rows.
import * as THREE from 'three';
import fs from 'node:fs';
import path from 'node:path';
import { normaliseManifest } from '../src/manifest.js';
import { irradianceRatio, applyFoliage, farTreeIrradiance, RATIO_CLAMP } from '../src/foliage.js';
import { lazyUrlCandidates, loadFarTrees, markShrubLodRows, prototypeEbake,
	loadFarTreeLighting } from '../src/foliageLazy.js';
import { buildImpostors } from '../src/impostors.js';

let fails = 0;
const ok = ( c, m ) => { console.log( `${c ? 'PASS' : 'FAIL'}  ${m}` ); if ( ! c ) fails ++; };
const info = ( m ) => console.log( `      ${m}` );

const MAIN = process.env.PFA_MAIN_ROOT || path.resolve( import.meta.dirname, '../../..' );
const MANIFEST = path.join( MAIN, 'export/out/gate3/manifest.json' );

// ---------------------------------------------------------------- 1. the url candidates
{
	const base = 'http://x/assets/gate3/manifest.json';
	const a = lazyUrlCandidates( base, 'env_trees.glb' );
	ok( a.includes( 'http://x/assets/gate3/env_trees.glb' ), 'candidate: beside the manifest' );
	ok( a.includes( 'http://x/assets/gate1/env_trees.glb' ), 'candidate: ../gate1 (where gltf_pack.sh writes)' );
	const b = lazyUrlCandidates( base, 'out/gate3/foliage/tex_ktx2/x.ktx2' );
	ok( b.includes( 'http://x/assets/gate3/foliage/tex_ktx2/x.ktx2' ), 'candidate: the OUT root stripped' );
}

// ---------------------------------------------------------------- 2. the ratio, clamped
{
	ok( irradianceRatio( [ 1, 1, 1 ], [ 0, 1, 1 ], 'full' )[ 0 ] === 1, 'E_bake zero channel -> 1, not a runaway' );
	const r = irradianceRatio( [ 100, 1, 1 ], [ 1, 1, 1 ], 'full' );
	ok( r[ 0 ] === RATIO_CLAMP, `full mode clamped at ${RATIO_CLAMP} (got ${r[ 0 ]})` );
	const c = irradianceRatio( [ 2, 2, 2 ], [ 1, 1, 1 ], 'chroma' );
	ok( Math.abs( c[ 0 ] - 1 ) < 1e-6 && Math.abs( c[ 1 ] - 1 ) < 1e-6, 'chroma mode is level-free' );
}

// ---------------------------------------------------------------- 3. the dissolve is a complement
// The two tests live in different files and must partition the pixels exactly: the mesh keeps
// { hash <= meshFade }, the impostor must keep its complement and nothing else.
{
	const fol = fs.readFileSync( path.resolve( import.meta.dirname, '../src/foliage.js' ), 'utf8' );
	const imp = fs.readFileSync( path.resolve( import.meta.dirname, '../src/impostors.js' ), 'utf8' );
	const meshDiscard = /vPfaFade < 0\.9995 && pfaHash\( gl_FragCoord\.xy \) >= vPfaFade/.test( fol );
	const impDiscard = /vPfaFade < 0\.9995 && pfaHash\( gl_FragCoord\.xy \) < 1\.0 - vPfaFade/.test( imp );
	ok( meshDiscard, 'mesh discards hash >= vPfaFade (keeps hash < 1-t)' );
	ok( impDiscard, 'impostor discards hash < 1 - vPfaFade (keeps hash >= 1-t) — the exact complement' );
	// and a numeric check of the partition at ten fade values
	let bad = 0;
	for ( let k = 0; k <= 10; k ++ ) {
		const t = k / 10;                       // the impostor's vPfaFade; the mesh's is 1 - t
		for ( let h = 0; h < 1; h += 0.05 ) {
			// exactly the two shipped tests, guards included
			const meshFade = 1 - t;
			const meshKeeps = ! ( meshFade < 0.9995 && h >= meshFade );
			const impKeeps = ! ( t < 0.9995 && h < 1 - t );
			if ( meshKeeps === impKeeps ) bad ++;
		}
	}
	ok( bad === 0, `every (fade, hash) pair is drawn exactly once (${bad} overlaps/holes)` );
}

if ( ! fs.existsSync( MANIFEST ) ) {
	ok( false, `no manifest at ${MANIFEST} (set PFA_MAIN_ROOT)` );
	process.exit( 1 );
}
const raw = JSON.parse( fs.readFileSync( MANIFEST, 'utf8' ) );
const manifest = normaliseManifest( raw, 'http://x/assets/gate3/manifest.json' );

// ---------------------------------------------------------------- 4. the far-tree join
{
	const fm = raw.trees && raw.trees.far_mesh;
	ok( !! fm, 'manifest carries trees.far_mesh' );
	// the normaliser the viewer runs before anything reads the block (inline OR sidecar)
	const notesL = [];
	const lit = await loadFarTreeLighting( manifest, async () => { throw new Error( 'no fetch in this test' ); },
		( m ) => notesL.push( m ) );
	info( notesL.join( '\n      ' ) );
	if ( lit ) {
		ok( Array.isArray( lit.rows ) && lit.rows.length === 127, `lighting normalised to ${lit.rows && lit.rows.length} rows` );
		ok( lit.prototypes && Object.keys( lit.prototypes ).length === 16,
			`${lit.prototypes ? Object.keys( lit.prototypes ).length : 0} prototype E_bake values` );
		const e = prototypeEbake( lit );
		ok( !! e, 'prototypeEbake reads the normalised block -> ?impmod defaults to full' );
	} else {
		info( 'trees.far_mesh.lighting not in the manifest yet' );
	}
	const placements = fm.placements;
	// one instanced node per prototype per material, gltfpack-style, rows in manifest order
	const byProto = new Map();
	for ( const p of placements ) {
		if ( ! byProto.has( p.prototype ) ) byProto.set( p.prototype, [] );
		byProto.get( p.prototype ).push( p );
	}
	const root = new THREE.Group();
	const protoInfo = new Map( ( fm.prototypes || [] ).map( ( q ) => [ q.name, q ] ) );
	const impProtos = manifest.gate3.impostors.prototypes;
	for ( const [ proto, list ] of byProto ) {
		const info = protoInfo.get( proto ) || {};
		const ip = impProtos[ proto ] || {};
		const mats = info.materials || [ 'MAT_bark_cypress', 'MAT_leaf_cypress' ];
		// the prototype's own bounding volume, in PROTOTYPE space: trunk base at the origin, the tree
		// standing up to `heightAboveBase` - which is what the export's LOD2 objects are (and what the
		// 300 m placement bug broke).  The test therefore exercises the placement check for real.
		const h = ip.heightAboveBase || info.height_above_base_m || 12;
		const r = ip.radius || 2;
		for ( const matName of mats ) {
			const g = new THREE.BufferGeometry();
			const isLeaf = /^MAT_leaf_/.test( matName );
			const y0 = isLeaf ? h * 0.25 : 0, y1 = isLeaf ? h : h * 0.3;
			// symmetric about the trunk in XZ, exactly as a prototype in its own space is
			g.setAttribute( 'position', new THREE.BufferAttribute( new Float32Array( [
				- r, y0, - r, r, y0, - r, 0, y1, - r, - r, y0, r, r, y0, r, 0, y1, r ] ), 3 ) );
			g.setAttribute( 'normal', new THREE.BufferAttribute( new Float32Array( 18 ).fill( 0 ).map( ( _, i ) => ( i % 3 === 2 ? 1 : 0 ) ), 3 ) );
			const m = new THREE.MeshStandardMaterial( { name: matName } );
			const im = new THREE.InstancedMesh( g, m, list.length );
			im.name = `mesh_${root.children.length}`;
			list.forEach( ( p, i ) => {
				// the export's own rule: scale = height_m / height_above_base, translation = trunk base,
				// and the manifest's loc is BLENDER (x, y, z) -> three (x, z, -y)
				const sc = ( p.height_m || h ) / h;
				im.setMatrixAt( i, new THREE.Matrix4().compose(
					new THREE.Vector3( p.loc[ 0 ], p.loc[ 2 ], - p.loc[ 1 ] ),
					new THREE.Quaternion(), new THREE.Vector3( sc, sc, sc ) ) );
			} );
			root.add( im );
		}
	}
	const scene = new THREE.Scene();
	const sun = new THREE.DirectionalLight( 0xffffff, 1 );
	sun.position.set( 1, 1, 1 );

	// the impostors the far trees are supposed to fade into
	const built = buildImpostors( { impostors: manifest.gate3.impostors, far: manifest.treesFar,
		near: [], note: () => {}, loadTexture: () => Promise.resolve( null ), atlas2k: false } );
	if ( built.group ) scene.add( built.group );

	const notes = [];
	const rep = await loadFarTrees( {
		scene, manifest, sun, note: ( m ) => notes.push( m ),
		loadGlb: async ( url ) => ( url.includes( 'gate1/env_trees.glb' ) || url.endsWith( '/env_trees.glb' ) )
			? { scene: root, parser: null, userData: {} } : Promise.reject( new Error( '404' ) ),
		impostorGroup: built.group, foliageReport: null, probeTexture: null,
		scale: manifest.gate3.scale, mode: 'near', impMode: lit ? 'full' : 'chroma', meshDist: 40, fadeBand: 5,
		uvDequant: false,
	} );
	info( notes.filter( ( n ) => n.startsWith( 'far-tree' ) ).join( '\n      ' ) );
	ok( rep.error === null, `join clean (${rep.error || 'no error'})` );
	info( `placement check: ${JSON.stringify( rep.placementCheck )}` );
	ok( rep.placementCheck && rep.placementCheck.compared === 127,
		`every placement compared against its impostor quad (${rep.placementCheck && rep.placementCheck.compared})` );
	ok( rep.placementCheck && rep.placementCheck.over_tolerance === 0,
		`no mesh stands away from its impostor (${rep.placementCheck && rep.placementCheck.over_tolerance} over tolerance)` );
	ok( rep.rows === 254 && rep.joined === 254, `254/254 instance rows joined (${rep.joined}/${rep.rows})` );
	ok( rep.placements === 127, `127 placements declared (${rep.placements})` );
	ok( !! rep.update, 'a per-frame distance cull was returned' );
	// the impostor side must now know these trees have a mesh
	ok( rep.impostors && rep.impostors.placements === 127,
		`127 impostor rows flipped to iNear = 1 (${rep.impostors && rep.impostors.placements})` );
	// and the cull must hide a batch the camera is nowhere near
	const cam = new THREE.PerspectiveCamera();
	cam.position.set( 5000, 0, 5000 );
	const onFar = rep.update( cam );
	// stand ON a placement (Blender loc -> three): its own batch must be submitted, almost nothing else
	const p0 = placements[ 0 ].loc;
	cam.position.set( p0[ 0 ], p0[ 2 ] + 2, - p0[ 1 ] );
	const onNear = rep.update( cam );
	ok( onFar === 0, `nothing submitted from 5 km away (${onFar} batch(es))` );
	ok( onNear > 0 && onNear <= 16, `standing at placement 0, only the batches around it are submitted (${onNear}/${rep.batches})` );
	info( `far-tree mesh switch ${rep.meshDist} m: ${onNear} of ${rep.batches} batch(es) submitted at the tree, 0 at 5 km` );
}

// ---------------------------------------------------------------- 5. the shrub rows with no LOD1
{
	const ii = raw.lightmaps.instance_irradiance;
	const orphan = Object.keys( ( raw.shrubs.lod1.not_in_lod1 && raw.shrubs.lod1.not_in_lod1.meshes ) || {} );
	ok( orphan.length === 3, `3 shrub meshes have no LOD1 (${orphan.length})` );
	const scene = new THREE.Scene();
	const env = new THREE.Group();
	env.name = 'WEB_glb_env';
	scene.add( env );
	for ( const n of ii.nodes ) {
		const g = new THREE.BufferGeometry();
		g.setAttribute( 'position', new THREE.BufferAttribute( new Float32Array( 9 ), 3 ) );
		const im = new THREE.InstancedMesh( g, new THREE.MeshStandardMaterial( { name: 'MAT_shrub' } ), n.count );
		im.userData.pfaGltfNode = n.gltf_node;
		env.add( im );
	}
	const out = markShrubLodRows( scene, manifest, () => {} );
	ok( out.rows === 3, `3 placements masked out of the LOD switch (${out.rows})` );
	let masked = 0;
	env.traverse( ( m ) => {
		const a = m.geometry && m.geometry.getAttribute( 'pfaSwitchOn' );
		if ( a ) for ( let i = 0; i < a.count; i ++ ) if ( a.getX( i ) === 0 ) masked ++;
	} );
	ok( masked === 3, `the mask is on the right ROWS (${masked} zeros)` );
}

// ---------------------------------------------------------------- 5b. the bake's json, end to end
// The file the bake shipped, flattened exactly as loadFarTreeLighting flattens it, then pushed
// through the consumer that will run the day the lead's manifest_v4 puts the block in the manifest.
{
	const f = path.join( MAIN, 'export/out/gate3/trees_far/instance_irradiance.json' );
	if ( ! fs.existsSync( f ) ) {
		info( 'no trees_far/instance_irradiance.json yet, skipped' );
	} else {
		const j = JSON.parse( fs.readFileSync( f, 'utf8' ) );
		const rows = [];
		for ( const rec of Object.values( j.meshes || {} ) ) for ( const r of rec.placements || [] ) rows.push( r );
		ok( rows.length === 127, `${rows.length} rows flattened out of meshes[*].placements (expected 127)` );
		const eb = prototypeEbake( { prototypes: j.prototypes } );
		ok( eb && Object.keys( eb ).length === 16, `${eb ? Object.keys( eb ).length : 0} prototype E_bake values (expected 16)` );
		const raw2 = JSON.parse( JSON.stringify( { trees: { far_mesh: { lighting: { rows, prototypes: j.prototypes } } },
			impostors: raw.impostors } ) );
		for ( const mode of [ 'full', 'chroma' ] ) {
			const notes = [];
			const out = farTreeIrradiance( manifest.treesFar, raw2, mode, ( m ) => notes.push( m ) );
			ok( out.applied === 127, `mode ${mode}: ${out.applied}/127 placements modulated (${out.unmatched} unmatched)` );
			const v = [ ...out.byIndex.values() ];
			const mx = Math.max( ...v.flat() ), mn = Math.min( ...v.flat() );
			const clamped = v.filter( ( r ) => r.some( ( x ) => Math.abs( x - RATIO_CLAMP ) < 1e-9 ) ).length;
			info( `mode ${mode}: ratio range ${mn.toFixed( 3 )}..${mx.toFixed( 3 )}, ${clamped} placement(s) on the ${RATIO_CLAMP} clamp` );
			ok( mx <= RATIO_CLAMP + 1e-9, `mode ${mode}: no channel above the clamp (max ${mx.toFixed( 3 )})` );
			ok( mn > 0, `mode ${mode}: every channel positive (min ${mn.toFixed( 3 )})` );
		}
	}
}

// ---------------------------------------------------------------- 6. E_bake plumbing
{
	const l = raw.trees.far_mesh.lighting;
	const e = prototypeEbake( l );
	info( e ? `${Object.keys( e ).length} prototype E_bake value(s) -> ?impmod defaults to full`
		: 'no prototype E_bake in the manifest yet -> ?impmod stays chroma' );
	const c0 = raw.trees.far_mesh.color0 || {};
	info( `COLOR_0: present=${c0.present} topology_rev=${c0.topology_rev} range=${c0.range} encode="${String( c0.encode ).slice( 0, 60 )}"` );
	ok( true, 'E_bake and COLOR_0 presence reported' );
}

console.log( fails ? `${fails} FAILURES` : 'all foliage-lazy checks passed' );
process.exit( fails ? 1 : 0 );
