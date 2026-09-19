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
import { execFileSync } from 'node:child_process';
import { normaliseManifest } from '../src/manifest.js';
import { irradianceRatio, applyFoliage, farTreeIrradiance, RATIO_RULES, ratioRules } from '../src/foliage.js';
import { lazyUrlCandidates, loadFarTrees, markShrubLodRows, prototypeEbake,
	loadFarTreeLighting, buildDistanceCull, applyFoliageTextures,
	applyFoliageAlbedo } from '../src/foliageLazy.js';
import { buildImpostors } from '../src/impostors.js';

let fails = 0;
const ok = ( c, m ) => { console.log( `${c ? 'PASS' : 'FAIL'}  ${m}` ); if ( ! c ) fails ++; };
const info = ( m ) => console.log( `      ${m}` );

// PFA_MAIN_ROOT wins; then this checkout's own root (web/test -> <repo>); then, when this IS a
// worktree, the MAIN checkout it was made from - `export/out` is gitignored and exists only there, so
// without this a worktree run would skip every manifest-backed check for no good reason.
function mainRoot() {
	if ( process.env.PFA_MAIN_ROOT ) return process.env.PFA_MAIN_ROOT;
	const here = path.resolve( import.meta.dirname, '../..' );
	if ( fs.existsSync( path.join( here, 'export/out/gate3/manifest.json' ) ) ) return here;
	try {
		const common = execFileSync( 'git', [ '-C', here, 'rev-parse', '--path-format=absolute', '--git-common-dir' ],
			{ encoding: 'utf8' } ).trim();
		if ( common ) return path.dirname( common );        // <main>/.git -> <main>
	} catch ( e ) { /* not a git checkout: fall through */ }
	return here;
}
const MAIN = mainRoot();
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
	ok( irradianceRatio( [ 1, 1, 1 ], [ 0, 1, 1 ], 'full' )[ 0 ] === RATIO_RULES.zeroChannelFallback,
		'E_bake zero channel -> the fallback, not a runaway' );
	const r = irradianceRatio( [ 100, 1, 1 ], [ 1, 1, 1 ], 'full' );
	ok( r[ 0 ] === RATIO_RULES.clamp, `full mode clamped at ${RATIO_RULES.clamp} (got ${r[ 0 ]})` );
	const c = irradianceRatio( [ 2, 2, 2 ], [ 1, 1, 1 ], 'chroma' );
	ok( Math.abs( c[ 0 ] - 1 ) < 1e-6 && Math.abs( c[ 1 ] - 1 ) < 1e-6, 'chroma mode is level-free' );
	// the clamp bites in chroma too (round-2 review 4): without it the runaway channel dominates the
	// luminance the normalisation divides by, so the OTHER two channels come out wrong.
	const big = irradianceRatio( [ 100, 1, 1 ], [ 1, 1, 1 ], 'chroma' );
	const bigClamped = irradianceRatio( [ 4, 1, 1 ], [ 1, 1, 1 ], 'chroma' );
	ok( big.every( ( x, i ) => Math.abs( x - bigClamped[ i ] ) < 1e-9 ),
		`chroma clamps before normalising (${big.map( x => x.toFixed( 3 ) ).join( '/' )})` );
	// and the three rules come from the manifest, not from the constants
	const rr = ratioRules( { trees: { far_mesh: { lighting: { impostor: { strength: 2, clamp: 9, zero_channel_fallback: 0 } } } } } );
	ok( rr.strength === 2 && rr.clamp === 9 && rr.zeroChannelFallback === 0,
		`ratio rules read from the manifest (${rr.strength}/${rr.clamp}/${rr.zeroChannelFallback})` );
	ok( irradianceRatio( [ 3, 1, 1 ], [ 1, 1, 1 ], 'full', rr )[ 0 ] === 9,
		'the manifest strength and clamp are applied (3^2 = 9, at the 9 ceiling)' );
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
	// export/out is gitignored and lives in the MAIN checkout only, so a worktree run legitimately has
	// no manifest: the checks above (which need none) still ran and the rest is SKIPPED, the same way
	// manifest_test.mjs skips its gate manifests.  PFA_MAIN_ROOT points the run at the real assets.
	info( `no manifest at ${MANIFEST}: the manifest-backed checks are skipped (set PFA_MAIN_ROOT to run them)` );
	console.log( fails ? `${fails} FAILURES` : 'all foliage-lazy checks passed (manifest-backed ones skipped)' );
	process.exit( fails ? 1 : 0 );
}
const raw = JSON.parse( fs.readFileSync( MANIFEST, 'utf8' ) );
const manifest = normaliseManifest( raw, 'http://x/assets/gate3/manifest.json' );

// The synthetic glb, exactly as gltfpack emits it: one instanced node per prototype per material,
// rows in the manifest order.  Both tree sets (far_mesh and walkup_mesh) are the SAME 254 rows over
// the SAME 127 placements, so one builder serves both.
function makeRoot() {
		const fm = raw.trees && raw.trees.far_mesh;
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
	return root;
}

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
	const root = makeRoot();
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

// ---------------------------------------------------------------- 4b. the walk-up LOD1 tree set
// Same synthetic glb, served under the walk-up name: the block states its placements and its lighting
// BY REFERENCE to trees.far_mesh, so this proves the loader resolves both instead of reading an empty
// list, takes the block's own `draw_within_m`, and falls back to the LOD2 set when the glb is absent.
{
	const w = raw.trees && raw.trees.walkup_mesh;
	if ( ! w || ! w.glb ) {
		info( 'trees.walkup_mesh is not in this manifest yet: the walk-up checks are skipped' );
	} else {
		const scene = new THREE.Scene();
		const sun = new THREE.DirectionalLight( 0xffffff, 1 );
		sun.position.set( 1, 1, 1 );
		const built = buildImpostors( { impostors: manifest.gate3.impostors, far: manifest.treesFar,
			near: [], note: () => {}, loadTexture: () => Promise.resolve( null ), atlas2k: false } );
		if ( built.group ) scene.add( built.group );
		const common = { scene, manifest, sun, note: () => {}, impostorGroup: built.group,
			foliageReport: null, probeTexture: null, scale: manifest.gate3.scale, mode: 'near',
			impMode: 'full', meshDist: 40, fadeBand: 5, uvDequant: false };
		const serve = ( name ) => async ( url ) => ( url.endsWith( `/${name}` )
			? { scene: makeRoot(), parser: null, userData: {} } : Promise.reject( new Error( '404' ) ) );
		const up = await loadFarTrees( { ...common, loadGlb: serve( w.glb ) } );
		ok( up.set === 'walkup_mesh', `the walk-up set is chosen when the block is present (${up.set})` );
		ok( up.error === null && up.rows === 254 && up.joined === 254,
			`the walk-up glb joins on far_mesh's own placements (${up.joined}/${up.rows}, ${up.error || 'no error'})` );
		ok( up.placements === 127, `127 placements resolved through placements.same_as (${up.placements})` );
		ok( up.meshDist === ( w.draw_within_m || 15 ),
			`the block's own draw_within_m is the switch distance (${up.meshDist} m)` );
		ok( up.lit === 254, `every row lit from far_mesh.lighting (${up.lit}/254)` );
		// and with only the LOD2 glb on the wire it must fall back rather than lose every mesh
		const scene2 = new THREE.Scene();
		const built2 = buildImpostors( { impostors: manifest.gate3.impostors, far: manifest.treesFar,
			near: [], note: () => {}, loadTexture: () => Promise.resolve( null ), atlas2k: false } );
		if ( built2.group ) scene2.add( built2.group );
		const back = await loadFarTrees( { ...common, scene: scene2, impostorGroup: built2.group,
			loadGlb: serve( 'env_trees.glb' ) } );
		ok( back.walkupFellBack === true && back.set === 'far_mesh' && back.joined === 254,
			`a missing walk-up glb falls back to the LOD2 set (${back.set}, fellBack=${back.walkupFellBack})` );
		// ?walkupmesh=0 is the A/B and must not even look for the file
		const scene3 = new THREE.Scene();
		const built3 = buildImpostors( { impostors: manifest.gate3.impostors, far: manifest.treesFar,
			near: [], note: () => {}, loadTexture: () => Promise.resolve( null ), atlas2k: false } );
		if ( built3.group ) scene3.add( built3.group );
		const off = await loadFarTrees( { ...common, scene: scene3, impostorGroup: built3.group,
			walkup: '0', loadGlb: serve( 'env_trees.glb' ) } );
		ok( off.set === 'far_mesh' && ! off.walkupFellBack && off.meshDist === 12,
			`?walkupmesh=0 is the LOD2 set at 12 m (${off.set}, ${off.meshDist} m)` );
	}
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
		const impBlock = ( ( ( raw.trees || {} ).far_mesh || {} ).lighting || {} ).impostor || null;
		const raw2 = JSON.parse( JSON.stringify( { trees: { far_mesh: { lighting: {
			rows, prototypes: j.prototypes, impostor: impBlock } } }, impostors: raw.impostors } ) );
		info( `ratio rules: ${JSON.stringify( ratioRules( raw2 ) )}` );
		for ( const mode of [ 'full', 'chroma' ] ) {
			const notes = [];
			const out = farTreeIrradiance( manifest.treesFar, raw2, mode, ( m ) => notes.push( m ) );
			ok( out.applied === 127, `mode ${mode}: ${out.applied}/127 placements modulated (${out.unmatched} unmatched)` );
			const v = [ ...out.byIndex.values() ];
			const mx = Math.max( ...v.flat() ), mn = Math.min( ...v.flat() );
			const rr2 = ratioRules( raw2 );
			const clamped = v.filter( ( r ) => r.some( ( x ) => Math.abs( x - rr2.clamp ) < 1e-9 ) ).length;
			info( `mode ${mode}: ratio range ${mn.toFixed( 3 )}..${mx.toFixed( 3 )}, ${clamped} placement(s) on the ${rr2.clamp} clamp` );
			ok( mx <= rr2.clamp + 1e-9, `mode ${mode}: no channel above the clamp (max ${mx.toFixed( 3 )})` );
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

// ---------------------------------------------------------------- 7. the distance cull (Phase 8b a)
{
	// Two instanced batches: one at the origin, one 200 m away.  A limit of 40 m must keep the first
	// and hide the second, and a limit past both must keep both - the whole contract of the CPU cull
	// the shrub LOD1 set was missing (QA 20 §2).
	const root = new THREE.Object3D();
	const geo = new THREE.BoxGeometry( 1, 1, 1 );      // 12 triangles
	const mk = ( name, x ) => {
		const m = new THREE.InstancedMesh( geo, new THREE.MeshBasicMaterial(), 4 );
		m.name = name;
		for ( let i = 0; i < 4; i ++ ) m.setMatrixAt( i, new THREE.Matrix4().makeTranslation( x + i, 0, 0 ) );
		m.instanceMatrix.needsUpdate = true;
		root.add( m );
		return m;
	};
	const near = mk( 'near', 0 ), far = mk( 'far', 200 );
	root.updateMatrixWorld( true );
	let lim = 40;
	const cull = buildDistanceCull( root, { chunk: null, limit: () => lim } );
	ok( cull.stats.batches === 2, `two batches registered (${cull.stats.batches})` );
	ok( cull.stats.tris === 96, `8 boxes x 12 tris = 96 placed triangles (${cull.stats.tris})` );
	const cam = new THREE.PerspectiveCamera();
	cam.position.set( 0, 0, 0 );
	let on = cull.update( cam );
	ok( near.visible === true && far.visible === false && on === 1,
		`at the origin with a 40 m limit only the near batch is submitted (on=${on})` );
	cam.position.set( 200, 0, 0 );
	on = cull.update( cam );
	ok( near.visible === false && far.visible === true && on === 1,
		`200 m away it is the other way round (on=${on})` );
	lim = 1000;
	on = cull.update( cam );
	ok( near.visible === true && far.visible === true && on === 2, `a limit past both keeps both (on=${on})` );
	// a limit that is not a number must never hide geometry
	lim = NaN;
	cam.position.set( 0, 0, 0 );
	on = cull.update( cam );
	ok( near.visible === true && far.visible === true && on === 2, 'a non-finite limit draws everything' );
	// and chunking a site-spanning batch tightens it: 4 rows over 200 m split into regional chunks
	const root2 = new THREE.Object3D();
	const wide = new THREE.InstancedMesh( geo, new THREE.MeshBasicMaterial(), 8 );
	wide.name = 'wide';
	for ( let i = 0; i < 8; i ++ ) wide.setMatrixAt( i, new THREE.Matrix4().makeTranslation( i * 40, 0, 0 ) );
	wide.instanceMatrix.needsUpdate = true;
	root2.add( wide );
	root2.updateMatrixWorld( true );
	const c2 = buildDistanceCull( root2, { chunk: { minRadius: 12, minCount: 2, maxDepth: 3, gain: 0.95, budget: 128 },
		limit: () => 40 } );
	info( `chunking: ${c2.stats.split} batch(es) split into ${c2.stats.chunks}, +${c2.stats.added} draw call(s), `
		+ `${c2.stats.batches} batch(es), ${c2.stats.tris} placed tris` );
	ok( c2.stats.batches > 1, 'the site-spanning batch was split, so the cull has spatial granularity' );
	ok( c2.stats.tris === 96, `and no triangle was gained or lost by the split (${c2.stats.tris})` );
	const cam2 = new THREE.PerspectiveCamera();
	cam2.position.set( 0, 0, 0 );
	const on2 = c2.update( cam2 );
	ok( on2 < c2.stats.batches, `at one end of it ${on2} of ${c2.stats.batches} chunk(s) are submitted` );
}

// ------------------------------------------- 8. the translucency map's wrap mode (Phase 8b item d)
{
	// Phase 8e will scale the leaf-card UVs and patch env_trees.glb's leaf samplers to REPEAT.  The
	// translucency FACTOR map is sampled with those same UVs, so it must follow the albedo's sampler
	// and never a hard-coded mode.  Two materials, one clamped and one repeating, one fake loader.
	const fake = ( wrapS, wrapT ) => {
		const t = new THREE.Texture();
		t.wrapS = wrapS; t.wrapT = wrapT;
		return t;
	};
	const scene = new THREE.Object3D();
	const mk = ( name, wrapS, wrapT ) => {
		const mat = new THREE.MeshStandardMaterial();
		mat.name = name;
		mat.map = fake( wrapS, wrapT );
		scene.add( new THREE.Mesh( new THREE.PlaneGeometry(), mat ) );
		return mat;
	};
	mk( 'MAT_leaf_clamped', THREE.ClampToEdgeWrapping, THREE.ClampToEdgeWrapping );
	mk( 'MAT_leaf_repeat', THREE.RepeatWrapping, THREE.RepeatWrapping );
	const man = { baseUrl: 'https://example.invalid/x/', raw: { materials: { foliage: { dir: 'tex', sizes: [ 1024 ], materials: {
		MAT_leaf_clamped: { albedo: { 1024: 'a1' }, translucency_map: { 1024: 't1' } },
		MAT_leaf_repeat: { albedo: { 1024: 'a2' }, translucency_map: { 1024: 't2' } },
	} } } } };
	const loadTexture = async () => new THREE.Texture();
	const r = await applyFoliageTextures( { manifest: man, loadTexture, scene, note: () => {}, mode: '1024' } );
	const w = r.trnWrap;
	ok( r.translucency === 2, `both translucency maps loaded (${r.translucency})` );
	ok( w.MAT_leaf_clamped && w.MAT_leaf_clamped[ 0 ] === THREE.ClampToEdgeWrapping
		&& w.MAT_leaf_clamped[ 1 ] === THREE.ClampToEdgeWrapping,
	'a clamped albedo sampler gives a clamped translucency map (today\'s assets, unchanged)' );
	ok( w.MAT_leaf_repeat && w.MAT_leaf_repeat[ 0 ] === THREE.RepeatWrapping
		&& w.MAT_leaf_repeat[ 1 ] === THREE.RepeatWrapping,
	'a REPEAT albedo sampler gives a REPEAT translucency map (what Phase 8e needs)' );
	ok( r.trnMaps.MAT_leaf_repeat.wrapS === THREE.RepeatWrapping
		&& r.trnMaps.MAT_leaf_repeat.wrapT === THREE.RepeatWrapping,
	'... and it is on the texture itself, not only in the report' );

	// A LAZILY loaded root re-wraps the shared albedo from its OWN sampler (that is how the maps have
	// always been applied to env_trees.glb / env_shrubs.glb); the translucency map must follow it
	// there too, or 8e's REPEAT leaf samplers would tile the albedo and clamp the trn map.
	const lazy = new THREE.Object3D();
	lazy.name = 'WEB_glb_env_trees';
	const lm = new THREE.MeshStandardMaterial();
	lm.name = 'MAT_leaf_clamped';                        // clamp in env.glb, REPEAT in this glb
	lm.map = fake( THREE.RepeatWrapping, THREE.RepeatWrapping );
	lazy.add( new THREE.Mesh( new THREE.PlaneGeometry(), lm ) );
	let warned = 0;
	applyFoliageAlbedo( lazy, r.albedoMaps, ( msg ) => { if ( /disagrees/.test( msg ) ) warned ++; }, r.trnMaps );
	ok( r.trnMaps.MAT_leaf_clamped.wrapS === THREE.RepeatWrapping
		&& r.trnMaps.MAT_leaf_clamped.wrapT === THREE.RepeatWrapping,
	'a lazily loaded glb re-wraps the translucency map from its own sampler, as it does the albedo' );
	ok( r.albedoMaps.MAT_leaf_clamped.wrapS === THREE.RepeatWrapping,
		'... and the albedo took the same wrap (unchanged behaviour)' );
	ok( warned === 1, `the shared-texture conflict is REPORTED, not silent (${warned} note)` );
}

console.log( fails ? `${fails} FAILURES` : 'all foliage-lazy checks passed' );
process.exit( fails ? 1 : 0 );
