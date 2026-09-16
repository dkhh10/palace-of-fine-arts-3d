// Walk mode: WASD + mouse look, eye height 1.7 m, clamped to the ground, out of the lagoon and out
// of the columns.
//
// WHY A HEIGHTFIELD AND NOT A RAYCAST.  The walkable ground is four merged meshes (riprap alone is
// 181 k vertices) and three's Raycaster has no BVH, so a per-frame down-ray would cost more than the
// whole render.  The ground is instead rasterised ONCE into a 2 m height grid the first time walk mode
// is entered - never at load, so a capture never pays for it and `__pfaReady` is unaffected.  The grid
// also gives the shoreline for nothing: a cell whose ground is below WATER_Z is lagoon, so "cannot walk
// into the water" is the same test as "cannot walk off the terrain", both derived from the ground
// meshes' own geometry rather than from a hand-drawn polygon.
//
// COLUMNS.  Every ARCH_/ORN_ mesh above knee height contributes its world-space footprint rectangle to
// a second grid; the walker is a circle of WALK_RADIUS and is pushed out along the axis of least
// penetration, which slides along a colonnade instead of sticking to it.
//
// DETERMINISM.  Nothing here touches the camera until the viewer is ready AND the user has pressed a
// walk key: `screenshot.mjs` sends no input, so a captured frame is always the station's own camera.
import * as THREE from 'three';

export const EYE_HEIGHT = 1.7;         // m, standing eye height
export const WALK_RADIUS = 0.35;       // m, the walker's capsule radius
export const WALK_SPEED = 3.2;         // m/s
export const RUN_SPEED = 8.0;          // m/s, shift
const CELL = 2.0;                      // m, heightfield cell
const OBST_CELL = 4.0;                 // m, obstacle grid cell
const EXTENT = 320;                    // m, half-size of the gridded area around the origin
const KNEE = 0.45;                     // m above the ground: below this an obstacle is steppable
const HEAD = 2.2;                      // m above the ground: above this it is walked under
const NO_GROUND = - 1e9;

const GROUND_RE = /terrain|ground|paving|podium|walk|riprap|lawn|path|plaza|step/i;
const OBSTACLE_RE = /^(ARCH|ORN|WEB_glb_(arch|orn))/i;

/** A 2D grid of floats over [-EXTENT, EXTENT]^2, addressed in world x/z. */
class Grid {
	constructor( cell, fill ) {
		this.cell = cell;
		this.n = Math.ceil( 2 * EXTENT / cell );
		this.data = new Float32Array( this.n * this.n ).fill( fill );
	}
	idx( x, z ) {
		const i = Math.floor( ( x + EXTENT ) / this.cell ), j = Math.floor( ( z + EXTENT ) / this.cell );
		if ( i < 0 || j < 0 || i >= this.n || j >= this.n ) return - 1;
		return j * this.n + i;
	}
	get( x, z ) { const k = this.idx( x, z ); return k < 0 ? NO_GROUND : this.data[ k ]; }
	max( x, z, v ) { const k = this.idx( x, z ); if ( k >= 0 && v > this.data[ k ] ) this.data[ k ] = v; }
}

/** Is this mesh part of the walkable ground? */
function isGround( o ) {
	const names = [ o.name, o.material && o.material.name, o.parent && o.parent.name ].filter( Boolean ).join( ' ' );
	return GROUND_RE.test( names );
}

function rootName( o ) {
	let p = o;
	while ( p && ! /^WEB_glb_/.test( p.name || '' ) ) p = p.parent;
	return p ? p.name : '';
}

/**
 * Rasterise every walkable triangle into a height grid, and every obstacle footprint into a second.
 * @returns {{height:Grid, obstacles:Map<number,number[][]>, groundMeshes:number, obstacleMeshes:number, ms:number}}
 */
export function buildWalkGrids( scene ) {
	const t0 = performance.now();
	const height = new Grid( CELL, NO_GROUND );
	const obstacles = new Map();
	let groundMeshes = 0, obstacleMeshes = 0, tris = 0;
	const a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3();
	const m = new THREE.Matrix4(), box = new THREE.Box3();

	const rasterTri = () => {
		// per-cell point-in-triangle over the triangle's own cell bbox, storing the max height
		const x0 = Math.min( a.x, b.x, c.x ), x1 = Math.max( a.x, b.x, c.x );
		const z0 = Math.min( a.z, b.z, c.z ), z1 = Math.max( a.z, b.z, c.z );
		if ( x1 < - EXTENT || x0 > EXTENT || z1 < - EXTENT || z0 > EXTENT ) return;
		const d = ( b.z - c.z ) * ( a.x - c.x ) + ( c.x - b.x ) * ( a.z - c.z );
		const ymax = Math.max( a.y, b.y, c.y );
		for ( let x = Math.floor( x0 / CELL ) * CELL; x <= x1 + CELL; x += CELL ) {
			for ( let z = Math.floor( z0 / CELL ) * CELL; z <= z1 + CELL; z += CELL ) {
				if ( Math.abs( d ) > 1e-12 ) {
					const w0 = ( ( b.z - c.z ) * ( x - c.x ) + ( c.x - b.x ) * ( z - c.z ) ) / d;
					const w1 = ( ( c.z - a.z ) * ( x - c.x ) + ( a.x - c.x ) * ( z - c.z ) ) / d;
					const w2 = 1 - w0 - w1;
					if ( w0 < - 0.25 || w1 < - 0.25 || w2 < - 0.25 ) continue;   // a little slack: no pinholes
					height.max( x, z, w0 * a.y + w1 * b.y + w2 * c.y );
					continue;
				}
				height.max( x, z, ymax );
			}
		}
	};

	scene.traverse( ( o ) => {
		if ( ! o.isMesh || ! o.geometry || o.visible === false ) return;
		if ( /^WATER_/.test( o.name || '' ) ) return;
		const pos = o.geometry.getAttribute( 'position' );
		if ( ! pos ) return;

		if ( isGround( o ) ) {
			groundMeshes ++;
			const index = o.geometry.index;
			const count = index ? index.count : pos.count;
			const mats = o.isInstancedMesh ? o.count : 1;
			for ( let inst = 0; inst < mats; inst ++ ) {
				if ( o.isInstancedMesh ) m.fromArray( o.instanceMatrix.array, inst * 16 ).premultiply( o.matrixWorld );
				else m.copy( o.matrixWorld );
				for ( let i = 0; i < count; i += 3 ) {
					const i0 = index ? index.getX( i ) : i, i1 = index ? index.getX( i + 1 ) : i + 1, i2 = index ? index.getX( i + 2 ) : i + 2;
					a.fromBufferAttribute( pos, i0 ).applyMatrix4( m );
					b.fromBufferAttribute( pos, i1 ).applyMatrix4( m );
					c.fromBufferAttribute( pos, i2 ).applyMatrix4( m );
					rasterTri();
					tris ++;
				}
			}
			return;
		}

		if ( ! OBSTACLE_RE.test( o.name || rootName( o ) ) ) return;
		obstacleMeshes ++;
		if ( ! o.geometry.boundingBox ) o.geometry.computeBoundingBox();
		const n = o.isInstancedMesh ? o.count : 1;
		for ( let inst = 0; inst < n; inst ++ ) {
			if ( o.isInstancedMesh ) m.fromArray( o.instanceMatrix.array, inst * 16 ).premultiply( o.matrixWorld );
			else m.copy( o.matrixWorld );
			box.copy( o.geometry.boundingBox ).applyMatrix4( m );
			if ( box.max.x < - EXTENT || box.min.x > EXTENT || box.max.z < - EXTENT || box.min.z > EXTENT ) continue;
			if ( box.max.x - box.min.x > 60 || box.max.z - box.min.z > 60 ) continue;   // a merged mass, not a column
			const rect = [ box.min.x, box.min.z, box.max.x, box.max.z, box.min.y, box.max.y ];
			for ( let x = Math.floor( box.min.x / OBST_CELL ); x <= Math.floor( box.max.x / OBST_CELL ); x ++ ) {
				for ( let z = Math.floor( box.min.z / OBST_CELL ); z <= Math.floor( box.max.z / OBST_CELL ); z ++ ) {
					const k = x * 100000 + z;
					if ( ! obstacles.has( k ) ) obstacles.set( k, [] );
					obstacles.get( k ).push( rect );
				}
			}
		}
	} );

	return { height, obstacles, groundMeshes, obstacleMeshes, tris, ms: performance.now() - t0 };
}

/** Ground height under (x, z), or NO_GROUND where there is none (the lagoon, off the site). */
export function groundAt( grids, x, z ) {
	// the max of the four neighbouring cells: a step edge should not drop the walker through it
	let h = NO_GROUND;
	for ( const dx of [ - CELL, 0, CELL ] ) for ( const dz of [ - CELL, 0, CELL ] ) {
		const v = grids.height.get( x + dx * 0.5, z + dz * 0.5 );
		if ( v > h ) h = v;
	}
	return h;
}

/**
 * The nearest point with dry ground, searched outward in rings of one cell.  The hero station stands
 * 100 m out OVER the lagoon (that is the photograph's viewpoint), so entering walk mode there would
 * otherwise refuse every direction and look broken; the walker steps ashore instead.
 * @returns {{x:number,z:number,y:number,moved_m:number}|null}
 */
export function nearestDry( grids, x, z, waterY, maxRings = 120 ) {
	if ( groundAt( grids, x, z ) > waterY + 0.05 ) return { x, z, y: groundAt( grids, x, z ), moved_m: 0 };
	for ( let r = 1; r <= maxRings; r ++ ) {
		let best = null, bestD = Infinity;
		for ( let i = - r; i <= r; i ++ ) {
			for ( const [ dx, dz ] of [ [ i, - r ], [ i, r ], [ - r, i ], [ r, i ] ] ) {
				const nx = x + dx * CELL, nz = z + dz * CELL;
				const g = groundAt( grids, nx, nz );
				if ( g <= waterY + 0.05 ) continue;
				const d = ( nx - x ) ** 2 + ( nz - z ) ** 2;
				if ( d < bestD ) { bestD = d; best = { x: nx, z: nz, y: g, moved_m: Math.sqrt( d ) }; }
			}
		}
		if ( best ) return best;
	}
	return null;
}

/**
 * Push the walker out of anything it overlaps. Returns the corrected (x, z).
 * The axis of least penetration is used, which slides along a colonnade rather than sticking to it.
 */
export function resolveObstacles( grids, x, z, footY ) {
	for ( let pass = 0; pass < 2; pass ++ ) {
		let moved = false;
		for ( let cx = Math.floor( ( x - WALK_RADIUS ) / OBST_CELL ); cx <= Math.floor( ( x + WALK_RADIUS ) / OBST_CELL ); cx ++ ) {
			for ( let cz = Math.floor( ( z - WALK_RADIUS ) / OBST_CELL ); cz <= Math.floor( ( z + WALK_RADIUS ) / OBST_CELL ); cz ++ ) {
				const list = grids.obstacles.get( cx * 100000 + cz );
				if ( ! list ) continue;
				for ( const r of list ) {
					if ( r[ 5 ] < footY + KNEE || r[ 4 ] > footY + HEAD ) continue;   // steppable, or walked under
					const px = Math.min( x + WALK_RADIUS - r[ 0 ], r[ 2 ] - ( x - WALK_RADIUS ) );
					const pz = Math.min( z + WALK_RADIUS - r[ 1 ], r[ 3 ] - ( z - WALK_RADIUS ) );
					if ( px <= 0 || pz <= 0 ) continue;                               // no overlap
					if ( px < pz ) x += ( x < ( r[ 0 ] + r[ 2 ] ) * 0.5 ) ? - px : px;
					else z += ( z < ( r[ 1 ] + r[ 3 ] ) * 0.5 ) ? - pz : pz;
					moved = true;
				}
			}
		}
		if ( ! moved ) break;
	}
	return { x, z };
}

/**
 * One move of the walker: substepped so a run cannot tunnel through a column or over the shoreline.
 * Mutates nothing; returns the new foot position and whether the move was refused.
 * @param {{x:number,z:number}} from   current position
 * @param {{x:number,z:number}} step   the full step this frame, in metres
 * @returns {{x:number,z:number,y:number,blocked:boolean}}  y = the GROUND height at the result
 */
export function stepWalker( grids, from, step, waterY, footY = 0 ) {
	let x = from.x, z = from.z, y = groundAt( grids, x, z ), blocked = false;
	const len = Math.hypot( step.x, step.z );
	const n = Math.max( 1, Math.ceil( len / ( WALK_RADIUS * 0.8 ) ) );
	for ( let i = 0; i < n; i ++ ) {
		const nx = x + step.x / n, nz = z + step.z / n;
		if ( groundAt( grids, nx, nz ) <= waterY + 0.05 ) { blocked = true; break; }
		const r = resolveObstacles( grids, nx, nz, footY );
		const g = groundAt( grids, r.x, r.z );
		if ( g <= waterY + 0.05 ) { blocked = true; break; }
		x = r.x; z = r.z; y = g;
	}
	return { x, z, y, blocked };
}

/**
 * Walk mode over the viewer's camera.  `getCamera` is a getter, not the object: a station change
 * REPLACES the camera (a new lens and sensor fit), and walk mode must follow it rather than keep
 * driving the one it was built with.  `opts.waterY` is WATER_Z in three space; a step whose ground is
 * at or below it is refused, which is the shoreline.  `opts.onStart` is called when walk mode takes
 * over, so the caller can put its orbit controls down.
 */
export function makeWalk( getCamera, dom, scene, opts = {} ) {
	const waterY = opts.waterY ?? - 1.3;
	const note = opts.note || ( () => {} );
	const keys = new Set();
	let grids = null, active = false, yaw = 0, pitch = 0, last = 0;
	const state = { active: false, blocked: 0, buildMs: 0, y: 0 };
	const fwd = new THREE.Vector3(), right = new THREE.Vector3(), e = new THREE.Euler( 0, 0, 0, 'YXZ' );

	function start() {
		if ( active ) return;
		const camera = getCamera();
		if ( ! grids ) {
			grids = buildWalkGrids( scene );
			state.buildMs = grids.ms;
			note( `walk grids: ${grids.groundMeshes} ground mesh(es) -> ${grids.tris} triangles rasterised at ${CELL} m, `
				+ `${grids.obstacleMeshes} obstacle mesh(es) -> ${grids.obstacles.size} occupied cell(s), ${grids.ms.toFixed( 0 )} ms` );
		}
		e.setFromQuaternion( camera.quaternion, 'YXZ' );
		yaw = e.y; pitch = e.x;
		// stand the camera on the ground under wherever the station left it - or, at a station over
		// the water like the hero's, on the nearest shore
		const d = nearestDry( grids, camera.position.x, camera.position.z, waterY );
		if ( d ) {
			camera.position.set( d.x, d.y + EYE_HEIGHT, d.z );
			if ( d.moved_m > 0.01 ) note( `walk: this station stands over the water, stepped ${d.moved_m.toFixed( 1 )} m ashore` );
		}
		active = true; state.active = true;
		if ( opts.onStart ) opts.onStart();
		last = performance.now();
		dom.requestPointerLock && dom.requestPointerLock();
		note( 'walk mode: WASD to move, shift to run, mouse to look, Esc to release the pointer, 1-6 for the stations' );
	}
	function stop() { active = false; state.active = false; keys.clear(); }

	dom.addEventListener( 'mousemove', ( ev ) => {
		if ( ! active || document.pointerLockElement !== dom ) return;
		yaw -= ev.movementX * 0.0022;
		pitch = Math.max( - 1.45, Math.min( 1.45, pitch - ev.movementY * 0.0022 ) );
	} );
	document.addEventListener( 'pointerlockchange', () => { if ( document.pointerLockElement !== dom ) stop(); } );
	window.addEventListener( 'keyup', ( ev ) => keys.delete( ev.code ) );
	window.addEventListener( 'keydown', ( ev ) => {
		if ( ! /^(KeyW|KeyA|KeyS|KeyD|ShiftLeft|ShiftRight|Space)$/.test( ev.code ) ) return;
		if ( ! window.__pfaReady ) return;                       // never before the viewer is ready
		keys.add( ev.code );
		if ( ! active && /^Key[WASD]$/.test( ev.code ) ) start();
	} );

	/** One frame of walking. Returns true if it moved the camera (so the caller re-renders). */
	function tick() {
		if ( ! active ) return false;
		const camera = getCamera();
		const now = performance.now();
		const dt = Math.min( 0.1, ( now - last ) / 1000 );
		last = now;
		e.set( pitch, yaw, 0, 'YXZ' );
		camera.quaternion.setFromEuler( e );
		let f = 0, s = 0;
		if ( keys.has( 'KeyW' ) ) f += 1;
		if ( keys.has( 'KeyS' ) ) f -= 1;
		if ( keys.has( 'KeyD' ) ) s += 1;
		if ( keys.has( 'KeyA' ) ) s -= 1;
		if ( ! f && ! s ) return true;                            // looked around, did not move
		const speed = ( keys.has( 'ShiftLeft' ) || keys.has( 'ShiftRight' ) ) ? RUN_SPEED : WALK_SPEED;
		fwd.set( - Math.sin( yaw ), 0, - Math.cos( yaw ) );
		right.set( Math.cos( yaw ), 0, - Math.sin( yaw ) );
		const step = new THREE.Vector3().addScaledVector( fwd, f ).addScaledVector( right, s ).normalize().multiplyScalar( speed * dt );

		const r = stepWalker( grids, camera.position, step, waterY, camera.position.y - EYE_HEIGHT );
		if ( r.blocked ) state.blocked ++;
		camera.position.set( r.x, r.y + EYE_HEIGHT, r.z );
		state.y = camera.position.y;
		return true;
	}

	/**
	 * Deterministic walk probe for the capture harness: no input, no pointer lock, no rendering.
	 * Walks `seconds` at `headingDeg` (0 = -Z, the viewer's forward) from the camera's own position at
	 * a fixed 60 Hz and reports the path, so "cannot walk into the lagoon" is a number and not a claim.
	 */
	function probe( { headingDeg = 0, seconds = 20, speed = WALK_SPEED, from = null } = {} ) {
		if ( ! grids ) { grids = buildWalkGrids( scene ); state.buildMs = grids.ms; }
		const cam = getCamera();
		const h = headingDeg * Math.PI / 180;
		const dir = { x: - Math.sin( h ), z: - Math.cos( h ) };
		const start0 = nearestDry( grids, from ? from[ 0 ] : cam.position.x, from ? from[ 1 ] : cam.position.z, waterY );
		if ( ! start0 ) return { error: 'no dry ground within 240 m of the station' };
		let p = { x: start0.x, z: start0.z };
		const dt = 1 / 60, path = [];
		let blocked = 0, minGround = Infinity;
		for ( let t = 0; t < seconds; t += dt ) {
			const r = stepWalker( grids, p, { x: dir.x * speed * dt, z: dir.z * speed * dt }, waterY, 0 );
			if ( r.blocked ) blocked ++;
			p = { x: r.x, z: r.z };
			if ( r.y < minGround ) minGround = r.y;
			if ( path.length < 4000 ) path.push( [ + r.x.toFixed( 3 ), + r.z.toFixed( 3 ), + r.y.toFixed( 3 ) ] );
		}
		return { headingDeg, seconds, speed, start: { x: start0.x, z: start0.z }, ashore_m: start0.moved_m,
			end: p, eyeY: minGround + EYE_HEIGHT, minGround, blocked,
			waterY, samples: path.length, path: path.filter( ( _, i ) => i % 30 === 0 ),
			grid: { groundMeshes: grids.groundMeshes, obstacleMeshes: grids.obstacleMeshes, cells: grids.obstacles.size, build_ms: grids.ms } };
	}

	return { tick, start, stop, probe, state, get grids() { return grids; } };
}
