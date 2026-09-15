// Blender -> three.js camera conversion (Phase 6, viewer engineer).
//
// AXES.  Blender world is Z-up with +Y toward the lagoon; glTF / three is Y-up.
// The Blender glTF exporter writes Blender +Z -> glTF +Y and Blender +Y -> glTF -Z, i.e.
//     three (x, y, z) = blender (x, z, -y)
// which is exactly a rotation of -90 deg about X.  The viewer never re-rotates the scene:
// the same matrix B2T is applied to the camera stations so they land in the exported scene.
//
// CAMERA LOCAL FRAME.  A Blender camera looks down its local -Z with local +Y up; a three.js
// PerspectiveCamera does the same.  The local frame therefore needs NO conversion, only the
// world-space placement does:  W_three = B2T * W_blender   (no B2T^-1 on the right).
//
// LENS.  Blender lens/sensor_width with sensor_fit HORIZONTAL gives the HORIZONTAL fov;
// three.js PerspectiveCamera.fov is VERTICAL, so fov = 2*atan(tan(hfov/2)/aspect).
//
// SHIFT.  Blender shift_x/shift_y are fractions of the fit sensor dimension (the width here).
// A shift of s moves the image plane window by s * full_width; in the projection matrix that is
//     m[0][2] = 2*shift_x        m[1][2] = 2*shift_y*aspect
// (column-major elements[8] and elements[9]).  Positive shift_y moves the frame up, so scene
// content moves DOWN the frame by 2*shift_y*aspect in NDC.
import * as THREE from 'three';

export const B2T = new THREE.Matrix4().makeRotationX( - Math.PI / 2 );

export function b2t( bx, by, bz ) { return new THREE.Vector3( bx, bz, - by ); }

/** Blender 4x4 as rows (mathutils Matrix rows) -> three world matrix. */
export function blenderMatrixToThree( rows ) {
	const flat = Array.isArray( rows[ 0 ] ) ? rows.flat() : rows;   // row-major 16
	const m = new THREE.Matrix4().set( ...flat );                   // Matrix4.set() is row-major
	return new THREE.Matrix4().multiplyMatrices( B2T, m );
}

/** Blender euler, rotation_mode 'XYZ' (extrinsic X then Y then Z) -> matrix  M = Rz*Ry*Rx. */
export function blenderEulerXYZToMatrix( e ) {
	const rx = new THREE.Matrix4().makeRotationX( e[ 0 ] );
	const ry = new THREE.Matrix4().makeRotationY( e[ 1 ] );
	const rz = new THREE.Matrix4().makeRotationZ( e[ 2 ] );
	return rz.multiply( ry ).multiply( rx );
}

export function hFovRad( lens, sensorWidth ) { return 2 * Math.atan( sensorWidth / ( 2 * lens ) ); }

export function vFovDeg( lens, sensorWidth, aspect, sensorFit = 'HORIZONTAL', sensorHeight = 24 ) {
	const horizontal = sensorFit === 'HORIZONTAL' || ( sensorFit === 'AUTO' && aspect >= 1 );
	if ( ! horizontal ) return THREE.MathUtils.radToDeg( 2 * Math.atan( sensorHeight / ( 2 * lens ) ) );
	return THREE.MathUtils.radToDeg( 2 * Math.atan( Math.tan( hFovRad( lens, sensorWidth ) / 2 ) / aspect ) );
}

/**
 * Give a PerspectiveCamera Blender's lens + shift behaviour.  updateProjectionMatrix() is wrapped
 * so the shift survives every aspect change; the inverse is re-derived after the patch.
 */
export function applyBlenderLens( cam, st ) {
	cam.userData.blender = {
		lens: st.lens, sensorWidth: st.sensor_width ?? 36, sensorHeight: st.sensor_height ?? 24,
		sensorFit: st.sensor_fit ?? 'HORIZONTAL', shiftX: st.shift_x ?? 0, shiftY: st.shift_y ?? 0,
	};
	if ( ! cam.userData.blenderLensPatched ) {
		const base = THREE.PerspectiveCamera.prototype.updateProjectionMatrix.bind( cam );
		cam.updateProjectionMatrix = function () {
			const b = this.userData.blender;
			if ( b ) this.fov = vFovDeg( b.lens, b.sensorWidth, this.aspect, b.sensorFit, b.sensorHeight );
			base();
			if ( b && ( b.shiftX || b.shiftY ) ) {
				const e = this.projectionMatrix.elements;
				e[ 8 ] += 2 * b.shiftX;                 // row 0, col 2
				e[ 9 ] += 2 * b.shiftY * this.aspect;   // row 1, col 2
				this.projectionMatrixInverse.copy( this.projectionMatrix ).invert();
			}
		};
		cam.userData.blenderLensPatched = true;
	}
	cam.near = st.clip_start ?? 0.1;
	cam.far = st.clip_end ?? 5000;
	cam.updateProjectionMatrix();
	return cam;
}

/**
 * Build the world matrix of a Blender station in three space.
 * Preference order: matrix_world (exact, works for the straight-up station 4) > rotation_euler > look-at.
 * Returns { matrix, source, lookAtMatrix|null }.
 */
export function stationMatrix( st ) {
	const pos = b2t( ...st.location );
	let matrix = null, source = null;
	if ( st.matrix_world ) { matrix = blenderMatrixToThree( st.matrix_world ); source = 'matrix_world'; }
	else if ( st.rotation_euler ) {
		const m = blenderEulerXYZToMatrix( st.rotation_euler );
		m.setPosition( st.location[ 0 ], st.location[ 1 ], st.location[ 2 ] );
		matrix = new THREE.Matrix4().multiplyMatrices( B2T, m ); source = 'rotation_euler';
	}
	let lookAtMatrix = null;
	if ( st.target ) {
		const tgt = b2t( ...st.target );
		const flat = Math.hypot( tgt.x - pos.x, tgt.z - pos.z );
		if ( flat > 1e-6 ) {            // degenerate straight up/down (station 4) has no look-at solution
			lookAtMatrix = new THREE.Matrix4().lookAt( pos, tgt, new THREE.Vector3( 0, 1, 0 ) );
			lookAtMatrix.setPosition( pos );
		}
	}
	if ( ! matrix ) { matrix = lookAtMatrix; source = 'look_at'; }
	return { matrix, source, lookAtMatrix, position: pos };
}

/** Largest absolute element difference between two matrices (cross-check helper; acos-free,
 *  because Quaternion.angleTo amplifies float32 matrix noise to ~0.02 deg near identity). */
export function matrixMaxDiff( a, b ) {
	let d = 0;
	for ( let i = 0; i < 16; i ++ ) d = Math.max( d, Math.abs( a.elements[ i ] - b.elements[ i ] ) );
	return d;
}

/** Station -> configured PerspectiveCamera (or apply onto an existing one). */
export function makeStationCamera( st, aspect, cam = null ) {
	const c = cam || new THREE.PerspectiveCamera();
	c.aspect = aspect;
	applyBlenderLens( c, st );
	const { matrix } = stationMatrix( st );
	c.matrixAutoUpdate = false;
	c.matrix.copy( matrix );
	c.matrix.decompose( c.position, c.quaternion, c.scale );
	c.matrixAutoUpdate = true;
	c.updateMatrixWorld( true );
	c.updateProjectionMatrix();
	c.userData.station = st;
	return c;
}
