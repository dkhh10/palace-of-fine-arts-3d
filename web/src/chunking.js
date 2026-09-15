// Spatial chunking of site-spanning InstancedMeshes (QA-11d-1).
//
// The exporter collapses every placement of a shared mesh into ONE EXT_mesh_gpu_instancing node, so
// a 100-shrub prototype scattered over the whole 250 x 166 m site is a single InstancedMesh whose
// bounding sphere spans the site.  three's frustum test is per OBJECT, so that batch is drawn at
// every station — cam04 (the rotunda ceiling, which sees almost none of the site) drew 34 env
// batches, +22 draws and +0.12 M triangles for geometry that is nowhere near the frame.
//
// Fix: split such a batch into at most `maxChunks` regional InstancedMeshes by repeated median cuts
// on the widest axis of the instance translations (a 2-level KD split), each with its own bounding
// sphere.  A cut is kept only when it actually tightens the bounds (`gain`), so a genuinely local
// batch is never split, and the global `budget` (added draw calls) keeps the hero station inside
// its 400-draw budget.  Geometry and material are SHARED by the chunks: no extra memory beyond the instance
// matrices, which are moved, not copied.
import * as THREE from 'three';

const DEFAULTS = {
	minRadius: 30,      // m: only batches whose bounding sphere spans more than this are candidates
	minCount: 24,       // instances: below this the draw call is not worth splitting
	maxDepth: 2,        // 2 median cuts -> at most 4 chunks per batch
	gain: 0.8,          // keep a cut only if the widest child extent is < gain x the parent's
	budget: 160,        // hard cap on ADDED draw calls over the whole scene
};

/** Per-instance world-space translation of an InstancedMesh, in the mesh's own parent space. */
function translations( mesh ) {
	const a = mesh.instanceMatrix.array, n = mesh.count;
	const out = new Float64Array( n * 3 );
	for ( let i = 0; i < n; i ++ ) {
		out[ i * 3 ] = a[ i * 16 + 12 ]; out[ i * 3 + 1 ] = a[ i * 16 + 13 ]; out[ i * 3 + 2 ] = a[ i * 16 + 14 ];
	}
	return out;
}

function extent( pos, idx ) {
	const lo = [ Infinity, Infinity, Infinity ], hi = [ - Infinity, - Infinity, - Infinity ];
	for ( const i of idx ) for ( let k = 0; k < 3; k ++ ) {
		const v = pos[ i * 3 + k ];
		if ( v < lo[ k ] ) lo[ k ] = v;
		if ( v > hi[ k ] ) hi[ k ] = v;
	}
	return { lo, hi, size: [ hi[ 0 ] - lo[ 0 ], hi[ 1 ] - lo[ 1 ], hi[ 2 ] - lo[ 2 ] ] };
}

/** Recursive median split on the widest axis; returns a list of index arrays. */
function split( pos, idx, depth, opts ) {
	if ( depth >= opts.maxDepth || idx.length < opts.minCount ) return [ idx ];
	const e = extent( pos, idx );
	const axis = e.size.indexOf( Math.max( ...e.size ) );
	const widest = e.size[ axis ];
	if ( widest <= 0 ) return [ idx ];
	const sorted = idx.slice().sort( ( a, b ) => pos[ a * 3 + axis ] - pos[ b * 3 + axis ] );
	const mid = Math.floor( sorted.length / 2 );
	const left = sorted.slice( 0, mid ), right = sorted.slice( mid );
	if ( ! left.length || ! right.length ) return [ idx ];
	const wl = Math.max( ...extent( pos, left ).size ), wr = Math.max( ...extent( pos, right ).size );
	// A cut that does not tighten the bounds costs a draw call and buys nothing.
	if ( Math.max( wl, wr ) > opts.gain * Math.max( ...e.size ) ) return [ idx ];
	return [ ...split( pos, left, depth + 1, opts ), ...split( pos, right, depth + 1, opts ) ];
}

function makeChunk( src, idx, tag ) {
	const m = new THREE.InstancedMesh( src.geometry, src.material, idx.length );
	m.name = `${src.name || 'instanced'}_chunk${tag}`;
	m.frustumCulled = true;
	m.visible = src.visible;
	m.castShadow = src.castShadow; m.receiveShadow = src.receiveShadow;
	m.renderOrder = src.renderOrder;
	m.position.copy( src.position ); m.quaternion.copy( src.quaternion ); m.scale.copy( src.scale );
	m.matrixAutoUpdate = src.matrixAutoUpdate;
	m.matrix.copy( src.matrix );                 // a source with matrixAutoUpdate false keeps its place
	m.matrixWorld.copy( src.matrixWorld );
	m.userData = { ...src.userData, pfaChunk: { of: src.name, instances: idx.length, tag } };
	const dst = m.instanceMatrix.array, srcArr = src.instanceMatrix.array;
	idx.forEach( ( from, to ) => { for ( let k = 0; k < 16; k ++ ) dst[ to * 16 + k ] = srcArr[ from * 16 + k ]; } );
	m.instanceMatrix.needsUpdate = true;
	if ( src.instanceColor ) {
		m.instanceColor = new THREE.InstancedBufferAttribute( new Float32Array( idx.length * 3 ), 3 );
		idx.forEach( ( from, to ) => { for ( let k = 0; k < 3; k ++ ) m.instanceColor.array[ to * 3 + k ] = src.instanceColor.array[ from * 3 + k ]; } );
		m.instanceColor.needsUpdate = true;
	}
	m.computeBoundingSphere();
	return m;
}

/**
 * @param {THREE.Object3D} root   scene or a loaded glb scene
 * @returns {{candidates:number, split:number, chunks:number, added:number, batches:object[]}}
 */
export function chunkInstancedMeshes( root, options = {} ) {
	const opts = { ...DEFAULTS, ...options };
	const stats = { candidates: 0, split: 0, chunks: 0, added: 0, batches: [] };
	if ( opts.budget <= 0 ) return stats;
	const candidates = [];
	root.traverse( ( o ) => {
		if ( ! o.isInstancedMesh || o.count < opts.minCount ) return;
		if ( o.computeBoundingSphere ) o.computeBoundingSphere();
		const r = o.boundingSphere ? o.boundingSphere.radius : 0;
		if ( r >= opts.minRadius ) candidates.push( { mesh: o, radius: r } );
	} );
	// Biggest bounds first, so the budget is spent where the culling gain is largest.
	candidates.sort( ( a, b ) => b.radius - a.radius );
	stats.candidates = candidates.length;
	for ( const { mesh, radius } of candidates ) {
		if ( stats.added >= opts.budget ) break;
		const pos = translations( mesh );
		const parts = split( pos, [ ...Array( mesh.count ).keys() ], 0, opts );
		if ( parts.length < 2 || stats.added + parts.length - 1 > opts.budget ) continue;
		const parent = mesh.parent;
		const chunks = parts.map( ( idx, i ) => makeChunk( mesh, idx, `${i}` ) );
		for ( const c of chunks ) parent.add( c );
		parent.remove( mesh );
		stats.split ++; stats.chunks += chunks.length; stats.added += chunks.length - 1;
		stats.batches.push( {
			name: mesh.name, material: mesh.material && mesh.material.name, instances: mesh.count,
			radius_m: Math.round( radius * 10 ) / 10, chunks: chunks.length,
			chunk_radius_m: chunks.map( c => Math.round( c.boundingSphere.radius * 10 ) / 10 ),
		} );
	}
	return stats;
}
