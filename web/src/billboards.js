// Far-tree billboards (Gate 1 stand-in).
//
// manifest v2's `trees.far` is the list the Gate 3 impostor bake will consume: per entry a prototype
// id, a height and a trunk base in Blender coordinates.  Until that bake exists the viewer draws ONE
// FLAT QUAD per entry, grey, unshaded by any texture, explicitly tagged so a QA tile review reports
// them as placeholders and never scores them as vegetation:
//     object name   WEB_far_tree_billboard_<prototype>    (one InstancedMesh per prototype)
//     userData      { pfaPlaceholder: 'gate3_tree_impostor', prototype, count }
// They rotate about Y to face the camera, recomputed only when the camera actually moves (a station
// switch or an orbit drag), so a static frame costs nothing.
import * as THREE from 'three';
import { b2t } from './blenderCamera.js';

const WIDTH_RATIO = 0.55;       // quad width as a fraction of height when the manifest gives none

/** @param {{prototype:string,height:number,width:number|null,base:number[]}[]} far */
export function makeTreeBillboards( far, opts = {} ) {
	const group = new THREE.Group();
	group.name = 'WEB_far_tree_billboards';
	if ( ! far || ! far.length ) return group;

	const byProto = new Map();
	for ( const t of far ) {
		if ( ! byProto.has( t.prototype ) ) byProto.set( t.prototype, [] );
		byProto.get( t.prototype ).push( t );
	}

	// Unit quad with its origin at the bottom centre, so an instance matrix is scale + translate.
	const geo = new THREE.PlaneGeometry( 1, 1 );
	geo.translate( 0, 0.5, 0 );

	for ( const [ proto, list ] of byProto ) {
		const mat = new THREE.MeshStandardMaterial( {
			color: new THREE.Color().setRGB( 0.20, 0.22, 0.17, THREE.LinearSRGBColorSpace ),
			roughness: 0.95, metalness: 0.0, side: THREE.DoubleSide,
		} );
		mat.name = `WEB_far_tree_billboard_${proto}`;
		const mesh = new THREE.InstancedMesh( geo, mat, list.length );
		mesh.name = `WEB_far_tree_billboard_${proto}`;
		mesh.userData = { pfaPlaceholder: 'gate3_tree_impostor', prototype: proto, count: list.length };
		mesh.frustumCulled = true;
		mesh.castShadow = false; mesh.receiveShadow = false;
		mesh.userData.quads = list.map( ( t ) => {
			const p = b2t( t.base[ 0 ], t.base[ 1 ], t.base[ 2 ] );
			const h = Math.max( 0.5, t.height || 12 );
			return { p, h, w: t.width || h * WIDTH_RATIO };
		} );
		group.add( mesh );
	}
	group.userData = {
		pfaPlaceholder: 'gate3_tree_impostor',
		quads: far.length,
		prototypes: [ ...byProto.keys() ],
		note: 'flat tagged quads; the Gate 3 impostor bake replaces them',
	};
	if ( opts.faceCamera !== false ) group.userData.faceCamera = true;
	return group;
}

const _m = new THREE.Matrix4(), _q = new THREE.Quaternion(), _s = new THREE.Vector3(), _up = new THREE.Vector3( 0, 1, 0 );

/** Re-aim every quad at the camera about Y.  Call only when the camera has moved. */
export function aimBillboards( group, camera ) {
	if ( ! group || ! group.userData.faceCamera ) return 0;
	let n = 0;
	for ( const mesh of group.children ) {
		const quads = mesh.userData.quads;
		for ( let i = 0; i < quads.length; i ++ ) {
			const { p, h, w } = quads[ i ];
			const yaw = Math.atan2( camera.position.x - p.x, camera.position.z - p.z );
			_q.setFromAxisAngle( _up, yaw );
			_s.set( w, h, 1 );
			_m.compose( p, _q, _s );
			mesh.setMatrixAt( i, _m );
			n ++;
		}
		mesh.instanceMatrix.needsUpdate = true;
		mesh.computeBoundingSphere();
	}
	return n;
}
