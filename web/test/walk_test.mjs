// src/walk.js: the ground heightfield, the shoreline and the column push-out, on a synthetic site.
//
// The site: a 200 x 200 m terrain plate at y = 0 named like the real ground meshes, cut off at x > 20
// where the lagoon begins (no ground at all, which is how the real export leaves the water), plus one
// 1 m square column at the origin.  That is the same shape the real grids see, small enough to assert on.
import * as THREE from 'three';
import { buildWalkGrids, groundAt, resolveObstacles, EYE_HEIGHT, WALK_RADIUS } from '../src/walk.js';

let fails = 0;
const check = ( ok, what ) => { console.log( `${ok ? 'PASS' : 'FAIL'}  ${what}` ); if ( ! ok ) fails ++; };

const WATER_Y = - 1.3;

function site() {
	const scene = new THREE.Scene();
	// terrain: one quad per 4 m cell over x in [-100, 20], z in [-100, 100], at y = 0, sloping to
	// y = -3 (below the water) in the last 8 m so the shoreline is where the ground crosses WATER_Y
	const pos = [], idx = [];
	let v = 0;
	for ( let x = - 100; x < 20; x += 4 ) for ( let z = - 100; z < 100; z += 4 ) {
		const h = ( X ) => ( X > 12 ? - 3 * ( X - 12 ) / 8 : 0 );
		pos.push( x, h( x ), z, x + 4, h( x + 4 ), z, x + 4, h( x + 4 ), z + 4, x, h( x ), z + 4 );
		idx.push( v, v + 1, v + 2, v, v + 2, v + 3 );
		v += 4;
	}
	const g = new THREE.BufferGeometry();
	g.setAttribute( 'position', new THREE.BufferAttribute( new Float32Array( pos ), 3 ) );
	g.setIndex( idx );
	const ground = new THREE.Mesh( g, new THREE.MeshStandardMaterial( { name: 'MAT_EXP_ENV__ENV_terrain_ground' } ) );
	ground.name = 'ENV_terrain_ground';
	scene.add( ground );

	const col = new THREE.Mesh( new THREE.BoxGeometry( 1, 8, 1 ), new THREE.MeshStandardMaterial() );
	col.name = 'ARCH_colonnade_column_01';
	col.position.set( 0, 4, 0 );
	scene.add( col );
	scene.updateMatrixWorld( true );
	return scene;
}

const grids = buildWalkGrids( site() );
check( grids.groundMeshes === 1 && grids.obstacleMeshes === 1,
	`${grids.groundMeshes} ground mesh(es), ${grids.obstacleMeshes} obstacle mesh(es) found by name` );
check( grids.tris > 1000, `${grids.tris} triangles rasterised in ${grids.ms.toFixed( 0 )} ms` );

// --- the ground is where it was put -------------------------------------------------------------
check( Math.abs( groundAt( grids, - 50, 0 ) ) < 0.2, `ground at (-50, 0) = ${groundAt( grids, - 50, 0 ).toFixed( 3 )} (0 expected)` );
check( groundAt( grids, - 50, 0 ) > WATER_Y, 'dry land reads above WATER_Z' );

// --- the shoreline: the lagoon and everything off the terrain read below the water ---------------
check( groundAt( grids, 60, 0 ) < WATER_Y, 'open lagoon (x = 60) has no ground, so it reads below WATER_Z' );
check( groundAt( grids, 19, 0 ) < WATER_Y, `the submerged bank (x = 19) reads ${groundAt( grids, 19, 0 ).toFixed( 2 )}, below WATER_Z` );
check( groundAt( grids, - 400, 0 ) < WATER_Y, 'off the gridded area reads below WATER_Z too (cannot walk off the site)' );
// the crossing is where the slope passes WATER_Y, ~x = 15.5
let shore = null;
for ( let x = 0; x < 20; x += 0.25 ) if ( shore === null && groundAt( grids, x, 0 ) <= WATER_Y ) shore = x;
check( shore !== null && shore > 13 && shore < 19, `the shoreline falls at x = ${shore} (13..19 expected from the slope)` );

// --- the column pushes the walker out, and sideways ----------------------------------------------
{
	const r = resolveObstacles( grids, 0.1, 0.0, 0 );
	const d = Math.max( Math.abs( r.x ), Math.abs( r.z ) );
	check( d >= 0.5 + WALK_RADIUS - 1e-6, `a walker inside the column is pushed to ${d.toFixed( 3 )} m (>= ${( 0.5 + WALK_RADIUS ).toFixed( 2 )})` );
	const side = resolveObstacles( grids, 0.0, 3.0, 0 );
	check( Math.abs( side.x ) < 1e-9 && Math.abs( side.z - 3 ) < 1e-9, 'a walker clear of the column is not moved' );
	const graze = resolveObstacles( grids, 0.6, 2.0, 0 );
	check( Math.abs( graze.x - 0.6 ) < 1e-9, 'and one beside it slides past rather than sticking' );
}

// --- an obstacle below the knee is stepped over, one above the head is walked under --------------
{
	const scene = new THREE.Scene();
	const plate = new THREE.Mesh( new THREE.PlaneGeometry( 60, 60 ), new THREE.MeshStandardMaterial() );
	plate.name = 'ENV_terrain_ground';
	plate.rotation.x = - Math.PI / 2;
	scene.add( plate );
	const kerb = new THREE.Mesh( new THREE.BoxGeometry( 4, 0.2, 4 ), new THREE.MeshStandardMaterial() );
	kerb.name = 'ARCH_site_kerb';
	kerb.position.set( 10, 0.1, 0 );
	const lintel = new THREE.Mesh( new THREE.BoxGeometry( 4, 1, 4 ), new THREE.MeshStandardMaterial() );
	lintel.name = 'ARCH_rotunda_lintel';
	lintel.position.set( - 10, 5, 0 );
	scene.add( kerb, lintel );
	scene.updateMatrixWorld( true );
	const g2 = buildWalkGrids( scene );
	check( Math.abs( resolveObstacles( g2, 10, 0, 0 ).x - 10 ) < 1e-9, 'a 0.2 m kerb is stepped over, not collided with' );
	check( Math.abs( resolveObstacles( g2, - 10, 0, 0 ).x + 10 ) < 1e-9, 'a lintel 4.5 m overhead is walked under' );
	check( Math.abs( resolveObstacles( g2, - 10, 0, 4.0 ).x + 10 ) > 0.1, 'and the SAME lintel blocks a walker standing on a balcony at its own height' );
}

check( EYE_HEIGHT === 1.7, `eye height ${EYE_HEIGHT} m` );

console.log( fails ? `${fails} check(s) FAILED` : 'all walk checks passed' );
process.exit( fails ? 1 : 0 );
