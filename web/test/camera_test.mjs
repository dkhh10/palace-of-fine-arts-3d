// Verifies the Blender -> three camera conversion without a browser.
//   node test/camera_test.mjs
// Checks: (a) the three orientation sources (Blender matrix_world / euler XYZ / look-at) agree,
// (b) the brief's sanity number: from station 1 the Blender world origin projects to the exact
// horizontal centre and 2*shift_y*aspect + a small target offset below the vertical centre,
// (c) every station's target projects to the shifted centre.
import * as THREE from 'three';
import { readFileSync } from 'node:fs';
import { stationMatrix, makeStationCamera, matrixMaxDiff, b2t, vFovDeg } from '../src/blenderCamera.js';

const data = JSON.parse( readFileSync( new URL( '../src/stations_blender.json', import.meta.url ) ) );
const ASPECT = 1280 / 720;
let fails = 0;
const check = ( ok, msg ) => { if ( ! ok ) fails ++; console.log( `${ok ? 'PASS' : 'FAIL'}  ${msg}` ); };

for ( const st of data.stations ) {
	const { matrix, source, lookAtMatrix } = stationMatrix( st );
	const eulerOnly = stationMatrix( { ...st, matrix_world: null } );
	const dEuler = matrixMaxDiff( matrix, eulerOnly.matrix );
	check( dEuler < 1e-5, `st${st.index} matrix_world vs euler XYZ: max element diff ${dEuler.toExponential( 2 )}` );
	if ( lookAtMatrix ) {
		const dLook = matrixMaxDiff( matrix, lookAtMatrix );
		check( dLook < 1e-5, `st${st.index} matrix_world vs look-at:    max element diff ${dLook.toExponential( 2 )}` );
	} else {
		console.log( `      st${st.index} look-at degenerate (straight up), ${source} used` );
	}

	const cam = makeStationCamera( st, ASPECT );
	if ( st.target ) {
		const p = b2t( ...st.target ).project( cam );
		const expectedY = - 2 * ( st.shift_y ?? 0 ) * ASPECT;
		check( Math.abs( p.x ) < 1e-5 && Math.abs( p.y - expectedY ) < 1e-5,
			`st${st.index} target -> ndc (${p.x.toFixed( 6 )}, ${p.y.toFixed( 6 )}), expected (0, ${expectedY.toFixed( 6 )})` );
	}
}

// Brief sanity number: station 1, lens 20 on a 36 mm sensor, shift_y 0.06, eye (-14.1, 100, 1.3),
// target (0, 0, 1.3).  The rotunda floor origin (0,0,0) is 1.3 m below the target at 101.0 m.
const st1 = data.stations[ 0 ];
const cam1 = makeStationCamera( st1, ASPECT );
const ndc = b2t( 0, 0, 0 ).project( cam1 );
const dist = Math.hypot( 14.1, 100.0 );
const vfov = THREE.MathUtils.degToRad( vFovDeg( st1.lens, st1.sensor_width, ASPECT ) );
const expect = - ( 1.3 / dist ) / Math.tan( vfov / 2 ) - 2 * st1.shift_y * ASPECT;
check( Math.abs( ndc.x ) < 1e-5, `st1 origin ndc.x = ${ndc.x.toExponential( 2 )} (frame centre)` );
check( Math.abs( ndc.y - expect ) < 2e-3,
	`st1 origin ndc.y = ${ndc.y.toFixed( 5 )} (analytic ${expect.toFixed( 5 )}), ${( - ndc.y * 50 ).toFixed( 1 )} % of frame height below centre` );
check( ndc.y < 0 && ndc.y > - 0.35, `st1 origin sits slightly below the vertical centre` );
console.log( `      st1 hfov ${( 2 * Math.atan( 36 / 40 ) * 180 / Math.PI ).toFixed( 2 )} deg, vfov ${( vfov * 180 / Math.PI ).toFixed( 2 )} deg at 16:9` );
console.log( `      st1 camera world matrix (three, column-major): [${cam1.matrixWorld.elements.map( v => v.toFixed( 5 ) ).join( ', ' )}]` );
console.log( `      st1 projection matrix     (column-major): [${cam1.projectionMatrix.elements.map( v => v.toFixed( 5 ) ).join( ', ' )}]` );
console.log( fails ? `${fails} FAILURES` : 'all checks passed' );
process.exit( fails ? 1 : 0 );
