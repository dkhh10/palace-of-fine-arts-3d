// src/uvDequant.js: gltfpack's texcoord quantisation undone on the attribute.
//
// The shape of the real thing (measured on export/out/gate1/*.glb): the uv attribute arrives
// normalised into [0, 0.0625] and the dequantisation (offset = the island's min, scale ~16) sits in
// KHR_texture_transform on the material's baseColorTexture, which GLTFLoader has already turned into
// texture.offset / texture.repeat.  TEXCOORD_1 has no texture of its own, so nothing applies it there.
import * as THREE from 'three';
import { dequantizeUvs } from '../src/uvDequant.js';

let fails = 0;
const check = ( ok, what ) => { console.log( `${ok ? 'PASS' : 'FAIL'}  ${what}` ); if ( ! ok ) fails ++; };
const close = ( a, b, eps = 1e-5 ) => Math.abs( a - b ) < eps;

/** A mesh whose uv/uv1 are quantised by (scale, offset), with the transform on its baseColorTexture. */
function quantised( scale, offset, { withUv1 = true, sharedMat = null } = {} ) {
	const g = new THREE.BufferGeometry();
	const n = 4;
	g.setAttribute( 'position', new THREE.BufferAttribute( new Float32Array( n * 3 ), 3 ) );
	// true UVs 0, 1/3, 2/3, 1 -> stored as (true - offset) / scale
	const t = [ 0, 1 / 3, 2 / 3, 1 ];
	const enc = new Float32Array( n * 2 );
	for ( let i = 0; i < n; i ++ ) {
		enc[ i * 2 ] = ( t[ i ] - offset[ 0 ] ) / scale[ 0 ];
		enc[ i * 2 + 1 ] = ( t[ i ] - offset[ 1 ] ) / scale[ 1 ];
	}
	g.setAttribute( 'uv', new THREE.BufferAttribute( enc.slice(), 2 ) );
	if ( withUv1 ) g.setAttribute( 'uv1', new THREE.BufferAttribute( enc.slice(), 2 ) );
	const mat = sharedMat || new THREE.MeshStandardMaterial();
	if ( ! sharedMat ) {
		const tex = new THREE.Texture();
		tex.offset.set( offset[ 0 ], offset[ 1 ] );
		tex.repeat.set( scale[ 0 ], scale[ 1 ] );
		mat.map = tex;
		const nrm = new THREE.Texture();            // a second texture with the SAME transform
		nrm.offset.set( offset[ 0 ], offset[ 1 ] );
		nrm.repeat.set( scale[ 0 ], scale[ 1 ] );
		mat.normalMap = nrm;
	}
	return new THREE.Mesh( g, mat );
}

// --- the transform is undone on both uv sets ---------------------------------------------------
{
	const root = new THREE.Object3D();
	const m = quantised( [ 15.9538, 15.9534 ], [ 0.00156, 0.00158 ] );
	root.add( m );
	const before = m.geometry.getAttribute( 'uv1' ).getX( 3 );
	const r = dequantizeUvs( root );
	check( before < 0.07, `TEXCOORD_1 arrives quantised (${before.toFixed( 5 )} for a true 1.0)` );
	const uv = m.geometry.getAttribute( 'uv' ), uv1 = m.geometry.getAttribute( 'uv1' );
	check( close( uv.getX( 0 ), 0 ) && close( uv.getX( 1 ), 1 / 3 ) && close( uv.getX( 3 ), 1 ),
		`uv dequantised to 0, 1/3, 2/3, 1 (got ${[ 0, 1, 2, 3 ].map( i => uv.getX( i ).toFixed( 4 ) ).join( ', ' )})` );
	check( close( uv1.getY( 3 ), 1 ) && close( uv1.getY( 1 ), 1 / 3 ), 'uv1 gets the SAME transform - that is the whole fix' );
	check( uv1.array instanceof Float32Array, 'written back as float32, not left normalised' );
	check( r.geometries === 1 && r.sets === 2 && r.materials === 1, `report: ${r.geometries} geometr(ies), ${r.sets} set(s), ${r.materials} material(s)` );
}

// --- every texture on the material is neutralised, or the transform would apply twice -----------
{
	const root = new THREE.Object3D();
	const m = quantised( [ 16, 16 ], [ 0.001, 0.002 ] );
	root.add( m );
	dequantizeUvs( root );
	check( m.material.map.repeat.x === 1 && m.material.map.offset.x === 0, 'baseColorTexture reset to the identity' );
	check( m.material.normalMap.repeat.x === 1 && m.material.normalMap.offset.y === 0, 'every other texture reset too' );
}

// --- a material shared by two primitives: the second must not read a neutralised transform ------
{
	const root = new THREE.Object3D();
	const scale = [ 16, 16 ], offset = [ 0.001, 0.001 ];
	const a = quantised( scale, offset );
	const b = quantised( scale, offset, { sharedMat: a.material } );
	root.add( a, b );
	const r = dequantizeUvs( root );
	check( r.geometries === 2 && r.materials === 1, `${r.geometries} geometries share ${r.materials} material` );
	check( close( a.geometry.getAttribute( 'uv' ).getX( 3 ), 1 ) && close( b.geometry.getAttribute( 'uv' ).getX( 3 ), 1 ),
		'both geometries dequantised with the recorded transform, not with the reset one' );
}

// --- idempotent, and a mesh with no transform is left alone -------------------------------------
{
	const root = new THREE.Object3D();
	const m = quantised( [ 16, 16 ], [ 0, 0 ] );
	root.add( m );
	dequantizeUvs( root );
	const after = m.geometry.getAttribute( 'uv' ).getX( 3 );
	const r2 = dequantizeUvs( root );          // the transforms are identities now: nothing to do
	check( close( m.geometry.getAttribute( 'uv' ).getX( 3 ), after ), 'running it twice does not scale the UVs twice' );
	check( r2.skipped === 1 && r2.geometries === 0, `an already-dequantised geometry is skipped (${r2.skipped})` );
}

// --- the escape hatch -------------------------------------------------------------------------
{
	const root = new THREE.Object3D();
	const m = quantised( [ 16, 16 ], [ 0.001, 0.001 ] );
	root.add( m );
	const r = dequantizeUvs( root, { enabled: false } );
	check( r.geometries === 0 && m.geometry.getAttribute( 'uv' ).getX( 3 ) < 0.07, '?uvdq=0 leaves the glb exactly as it arrived' );
}

console.log( fails ? `${fails} check(s) FAILED` : 'all uvDequant checks passed' );
process.exit( fails ? 1 : 0 );
