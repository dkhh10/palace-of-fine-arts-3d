// Dump per-drawn-mesh TEXCOORD_1 occupancy + world bbox centre from a meshopt glb, in node.
import fs from 'node:fs';
import path from 'node:path';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

// node has no DOM: GLTFLoader's image path touches self.URL.
globalThis.self = globalThis.self || globalThis;
if ( ! globalThis.URL.createObjectURL ) globalThis.URL.createObjectURL = () => 'blob:stub';
if ( ! globalThis.URL.revokeObjectURL ) globalThis.URL.revokeObjectURL = () => {};

const [ , , glbPath, outPath ] = process.argv;
const buf = fs.readFileSync( glbPath );
const ab = buf.buffer.slice( buf.byteOffset, buf.byteOffset + buf.byteLength );

// Textures are irrelevant here and KTX2 cannot transcode in node: stub the loader out.
const stubKTX2 = { load( _u, onLoad ) { const t = new THREE.Texture(); onLoad( t ); return t; },
	setPath() { return this; }, setCrossOrigin() { return this; }, setTranscoderPath() { return this; },
	detectSupport() { return this; }, isKTX2Loader: true };
const loader = new GLTFLoader().setMeshoptDecoder( MeshoptDecoder ).setKTX2Loader( stubKTX2 );
await MeshoptDecoder.ready;

const gltf = await new Promise( ( res, rej ) => loader.parse( ab, path.dirname( glbPath ) + '/', res, rej ) );
gltf.scene.updateMatrixWorld( true );

const N = 64;            // occupancy grid resolution
const out = [];
const box = new THREE.Box3(), m = new THREE.Matrix4(), v = new THREE.Vector3();

gltf.scene.traverse( o => {
	if ( ! o.isMesh ) return;
	const g = o.geometry;
	const uv1 = g.getAttribute( 'uv1' ) || g.getAttribute( 'uv2' );
	if ( ! g.boundingBox ) g.computeBoundingBox();
	const centres = [];
	if ( o.isInstancedMesh ) {
		for ( let i = 0; i < o.count; i ++ ) {
			m.fromArray( o.instanceMatrix.array, i * 16 ).premultiply( o.matrixWorld );
			centres.push( box.copy( g.boundingBox ).applyMatrix4( m ).getCenter( new THREE.Vector3() ).toArray() );
		}
	} else {
		centres.push( box.copy( g.boundingBox ).applyMatrix4( o.matrixWorld ).getCenter( new THREE.Vector3() ).toArray() );
	}
	// gltfpack quantises TEXCOORD as normalised ushort and puts the dequantisation in
	// KHR_texture_transform on the material's baseColorTexture.  GLTFLoader turns that into
	// texture.offset / texture.repeat, applied to channel 0 only.
	const bc = o.material && o.material.map;
	const xf = bc ? { offset: bc.offset.toArray(), repeat: bc.repeat.toArray(), rotation: bc.rotation, channel: bc.channel } : null;
	const rec = {
		material: o.material && o.material.name || '',
		uv0_transform: xf,
		count: o.isInstancedMesh ? o.count : 1,
		verts: g.getAttribute( 'position' ).count,
		tris: ( g.index ? g.index.count : g.getAttribute( 'position' ).count ) / 3,
		has_uv2: !! uv1,
		has_color: !! g.getAttribute( 'color' ),
		color_items: g.getAttribute( 'color' ) ? g.getAttribute( 'color' ).itemSize : 0,
		centre: centres[ 0 ],
		centres: centres.length <= 24 ? centres : undefined,
		ncentres: centres.length,
	};
	if ( uv1 ) {
		let mn = [ Infinity, Infinity ], mx = [ - Infinity, - Infinity ];
		const occ = new Uint8Array( N * N );
		let nOut = 0;
		for ( let i = 0; i < uv1.count; i ++ ) {
			const u = uv1.getX( i ), w = uv1.getY( i );
			if ( u < mn[ 0 ] ) mn[ 0 ] = u; if ( u > mx[ 0 ] ) mx[ 0 ] = u;
			if ( w < mn[ 1 ] ) mn[ 1 ] = w; if ( w > mx[ 1 ] ) mx[ 1 ] = w;
			if ( u < -1e-4 || u > 1 + 1e-4 || w < -1e-4 || w > 1 + 1e-4 ) nOut ++;
			const cu = Math.min( N - 1, Math.max( 0, Math.floor( u * N ) ) );
			const cv = Math.min( N - 1, Math.max( 0, Math.floor( w * N ) ) );
			occ[ cv * N + cu ] = 1;
		}
		rec.uv2 = { min: mn, max: mx, out_of_01: nOut, occ: Buffer.from( occ ).toString( 'base64' ), n: N };
		if ( xf ) {                                   // the same transform applied to UV2
			const occX = new Uint8Array( N * N );
			let xn = [ Infinity, Infinity ], xx = [ - Infinity, - Infinity ];
			for ( let i = 0; i < uv1.count; i ++ ) {
				const u = uv1.getX( i ) * xf.repeat[ 0 ] + xf.offset[ 0 ];
				const w = uv1.getY( i ) * xf.repeat[ 1 ] + xf.offset[ 1 ];
				if ( u < xn[ 0 ] ) xn[ 0 ] = u; if ( u > xx[ 0 ] ) xx[ 0 ] = u;
				if ( w < xn[ 1 ] ) xn[ 1 ] = w; if ( w > xx[ 1 ] ) xx[ 1 ] = w;
				const cu = Math.min( N - 1, Math.max( 0, Math.floor( u * N ) ) );
				const cv = Math.min( N - 1, Math.max( 0, Math.floor( w * N ) ) );
				occX[ cv * N + cu ] = 1;
			}
			rec.uv2_xf = { min: xn, max: xx, occ: Buffer.from( occX ).toString( 'base64' ), n: N };
		}
	}
	out.push( rec );
} );

fs.writeFileSync( outPath, JSON.stringify( { glb: glbPath, meshes: out }, null, 0 ) );
console.log( glbPath, 'meshes', out.length, 'with uv2', out.filter( r => r.has_uv2 ).length );
