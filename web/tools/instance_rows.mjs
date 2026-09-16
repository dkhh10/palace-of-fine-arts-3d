// Dump EXT_mesh_gpu_instancing rows from a meshopt-packed glb, IN GLB ROW ORDER, in node.
//
//     node web/tools/instance_rows.mjs export/out/gate1/env.glb export/out/gate3/instance_rows.json
//
// Why node and not python: every accessor in the packed glbs rides in an EXT_meshopt_compression
// bufferView, so the instancing TRANSLATION/ROTATION/SCALE cannot be read without the meshopt decoder.
// three's GLTFLoader builds an InstancedMesh whose instanceMatrix rows are the accessor rows in order,
// which is exactly the order a viewer's InstancedBufferAttribute has to line up with.
//
// Output: { glb, generated, nodes: [ { index, name, mesh, material, count, tris,
//           rows: [ [x,y,z, qx,qy,qz,qw, sx,sy,sz], ... ] } ] }  -- world space (matrixWorld applied).
import fs from 'node:fs';
import path from 'node:path';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

globalThis.self = globalThis.self || globalThis;
if ( ! globalThis.URL.createObjectURL ) globalThis.URL.createObjectURL = () => 'blob:stub';
if ( ! globalThis.URL.revokeObjectURL ) globalThis.URL.revokeObjectURL = () => {};

const [ , , glbPath, outPath ] = process.argv;
if ( ! glbPath || ! outPath ) { console.error( 'usage: instance_rows.mjs <glb> <out.json>' ); process.exit( 2 ); }
const buf = fs.readFileSync( glbPath );
const ab = buf.buffer.slice( buf.byteOffset, buf.byteOffset + buf.byteLength );

const stubKTX2 = { load( _u, onLoad ) { const t = new THREE.Texture(); onLoad( t ); return t; },
	setPath() { return this; }, setCrossOrigin() { return this; }, setTranscoderPath() { return this; },
	detectSupport() { return this; }, isKTX2Loader: true };
const loader = new GLTFLoader().setMeshoptDecoder( MeshoptDecoder ).setKTX2Loader( stubKTX2 );
await MeshoptDecoder.ready;

const gltf = await new Promise( ( res, rej ) => loader.parse( ab, path.dirname( glbPath ) + '/', res, rej ) );
gltf.scene.updateMatrixWorld( true );

const nodes = [];
const m = new THREE.Matrix4(), p = new THREE.Vector3(), q = new THREE.Quaternion(), s = new THREE.Vector3();
let order = 0;
gltf.scene.traverse( o => {
	if ( ! o.isInstancedMesh ) return;
	const g = o.geometry;
	const idx = g.getIndex();
	const tris = ( idx ? idx.count : g.getAttribute( 'position' ).count ) / 3;
	const rows = [];
	for ( let i = 0; i < o.count; i ++ ) {
		m.fromArray( o.instanceMatrix.array, i * 16 ).premultiply( o.matrixWorld );
		m.decompose( p, q, s );
		rows.push( [ p.x, p.y, p.z, q.x, q.y, q.z, q.w, s.x, s.y, s.z ] );
	}
	// The glTF node index is the stable key (three's traverse order is not part of the file): verify_glb.py
	// and the manifest both address a node by it. GLTFLoader records it in parser.associations.
	const assoc = gltf.parser.associations.get( o ) || {};
	if ( ! Number.isInteger( assoc.nodes ) ) throw new Error(
		`instanced mesh ${o.name || '(unnamed)'} has no glTF node index (three put it under a Group?): ` +
		`the row order cannot be addressed without one` );
	nodes.push( { order: order ++, gltf_node: assoc.nodes, gltf_mesh: assoc.meshes ?? null,
		name: o.name || null, mesh: g.name || null,
		material: ( Array.isArray( o.material ) ? o.material[ 0 ] : o.material )?.name || null,
		count: o.count, tris, rows } );
} );

fs.mkdirSync( path.dirname( outPath ), { recursive: true } );
// glb_bytes is the stale guard the consumer asserts: two checkouts hold an `env.glb` of the same name, and a
// row order dumped from the wrong one matches within tolerance and ships silently (review r5 finding 4).
fs.writeFileSync( outPath, JSON.stringify( { schema: 'pfa-phase6/instance-rows/1', glb: glbPath,
	glb_bytes: buf.byteLength, generated: new Date().toISOString(), nodes } ) );
console.log( `[instance_rows] ${nodes.length} instanced meshes, ` +
	`${nodes.reduce( ( a, n ) => a + n.count, 0 )} rows -> ${outPath}` );
