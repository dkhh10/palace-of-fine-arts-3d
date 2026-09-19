// Phase 8b item 3 — the BAND atlas lookup, checked without a browser:
//   node test/impostor_band_test.mjs
//
// The contract is docs/briefs/phase8b_band_atlas.md. What is pinned here is everything a screenshot
// could not tell apart from a working atlas: the azimuth-0 convention and its direction of travel
// (a wrong sign rotates 127 trees by up to 180 deg and still renders a plausible tree), the wrap at
// the last column, the two-azimuth blend, the NEAREST elevation row, the layout arithmetic, and the
// manifest block being read whole or refused. The fragment shader mirrors `bandSelect` line for
// line, so the GLSL is pinned textually beside it: the two cannot drift in silence.
import * as THREE from 'three';
import { buildImpostors, bandSelect, bandFrameUv, parseImpBand, IMP_COV } from '../src/impostors.js';

let fails = 0;
const check = ( ok, msg ) => { if ( ! ok ) fails ++; console.log( `${ok ? 'PASS' : 'FAIL'}  ${msg}` ); };
const close = ( a, b, eps = 1e-6 ) => Math.abs( a - b ) <= eps;

// The contract's own geometry: 12 x 3 frames of 341 px on 4096 x 1024, gutter 8 (the octahedral
// rule doubled), inner 325.
const GEOM = { framePx: 341, gutterPx: 8, innerPx: 325, atlasW: 4096, atlasH: 1024,
	columns: 12, rows: 3, azimuth0Deg: 0, elevationsDeg: [ 0, 20, 40 ], rowOrigin: 'bottom' };
// A tree -> camera direction in BLENDER Z-up at a given azimuth (deg, clockwise from +Y seen from
// above) and elevation (deg above the horizon). This is the inverse of what bandSelect does, so a
// round trip through both is a real test of the convention and not of one formula twice.
function dirAt( azDeg, elDeg ) {
	const az = azDeg * Math.PI / 180, el = elDeg * Math.PI / 180;
	return [ Math.sin( az ) * Math.cos( el ), Math.cos( az ) * Math.cos( el ), Math.sin( el ) ];
}

// ---- 1. the azimuth-0 convention ---------------------------------------------------------------
{
	const s = bandSelect( dirAt( 0, 0 ), GEOM );
	check( s.col0 === 0 && close( s.f, 0 ) && s.row === 0,
		`azimuth0 looks at column 0 exactly (got ${s.col0} + ${s.f.toFixed( 3 )}, row ${s.row})` );
	// +Y is azimuth 0 by construction, so the direction itself must come back as 0 deg
	check( close( bandSelect( [ 0, 1, 0 ], GEOM ).azDeg, 0 ), '+Y (Blender) is azimuth 0' );
	// CLOCKWISE SEEN FROM ABOVE: from +Y the next column is toward +X, not toward -X.
	check( close( bandSelect( [ 1, 0, 0 ], GEOM ).azDeg, 90 ), '+X is azimuth +90 (clockwise from above)' );
	check( close( bandSelect( [ - 1, 0, 0 ], GEOM ).azDeg, - 90 ), '-X is azimuth -90' );
	// one column step clockwise must land ON column 1 - written as "the weight that ends up on
	// column 1 is 1", because atan2's round trip puts the boundary at f = 0.9999999 as often as at 0
	const one = bandSelect( dirAt( 30, 0 ), GEOM );
	const onCol1 = ( one.col0 === 1 ) ? 1 - one.f : ( one.col1 === 1 ? one.f : 0 );
	check( onCol1 > 0.9999, `30 deg clockwise is column 1, not column 11 (weight on column 1 ${onCol1.toFixed( 6 )})` );
	// a non-zero azimuth0 shifts the columns and nothing else
	const g45 = { ...GEOM, azimuth0Deg: 45 };
	check( bandSelect( dirAt( 45, 0 ), g45 ).col0 === 0 && close( bandSelect( dirAt( 45, 0 ), g45 ).f, 0 ),
		'azimuth0_deg = 45: the 45 deg heading is column 0' );
	const shifted = bandSelect( dirAt( 0, 0 ), g45 );
	check( shifted.col0 === 10 && shifted.col1 === 11 && close( shifted.f, 0.5 ),
		'azimuth0_deg = 45: +Y is -45 deg, which wraps to 315 and blends columns 10 and 11' );
}

// ---- 2. the two-azimuth blend and the wrap ------------------------------------------------------
{
	const mid = bandSelect( dirAt( 15, 0 ), GEOM );
	check( mid.col0 === 0 && mid.col1 === 1 && close( mid.f, 0.5 ),
		`halfway between two columns blends them 50/50 (got ${mid.col0}/${mid.col1} f ${mid.f.toFixed( 3 )})` );
	const last = bandSelect( dirAt( 345, 0 ), GEOM );
	check( last.col0 === 11 && last.col1 === 0, 'the last column blends back into the first' );
	const just = bandSelect( dirAt( - 1, 0 ), GEOM );
	check( just.col0 === 11 && close( just.f, 1 - 1 / 30, 1e-9 ),
		`a negative azimuth wraps instead of clamping (got col ${just.col0}, f ${just.f.toFixed( 4 )})` );
	// the weights are a partition of unity at every angle, which is what keeps the card from
	// flickering as the camera turns
	for ( let a = - 400; a <= 400; a += 7.5 ) {
		const s = bandSelect( dirAt( a, 0 ), GEOM );
		if ( ! ( s.col0 >= 0 && s.col0 < 12 && s.col1 >= 0 && s.col1 < 12 && s.f >= 0 && s.f < 1 ) ) {
			check( false, `azimuth ${a}: columns and weight stay in range` );
			break;
		}
	}
	check( true, 'every azimuth from -400 to 400 deg yields in-range columns and a weight in [0,1)' );
	// continuity: one degree either side of a column edge must not jump by more than one column
	const a = bandSelect( dirAt( 29.9, 0 ), GEOM ), b = bandSelect( dirAt( 30.1, 0 ), GEOM );
	check( a.col0 === 0 && b.col0 === 1 && close( a.f, 0.99666, 1e-4 ) && close( b.f, 0.00333, 1e-4 ),
		'the blend crosses a column edge continuously (0.997 -> 0.003 on the next column)' );
}

// ---- 3. the elevation row is the NEAREST, never blended ------------------------------------------
{
	check( bandSelect( dirAt( 0, 0 ), GEOM ).row === 0, 'horizon -> row 0' );
	check( bandSelect( dirAt( 0, 9 ), GEOM ).row === 0, '9 deg -> row 0 (nearest of 0/20/40)' );
	check( bandSelect( dirAt( 0, 11 ), GEOM ).row === 1, '11 deg -> row 1' );
	check( bandSelect( dirAt( 0, 35 ), GEOM ).row === 2, '35 deg -> row 2' );
	check( bandSelect( dirAt( 0, 80 ), GEOM ).row === 2, 'above the top row it stays on the top row' );
	check( bandSelect( dirAt( 0, - 10 ), GEOM ).row === 0, 'below the horizon it stays on row 0' );
	// the stations look at the crowns from 0-15 deg: they must all land on rows 0 or 1
	for ( const e of [ 0, 3, 7, 12, 15 ] )
		check( bandSelect( dirAt( 123, e ), GEOM ).row <= 1, `a station elevation of ${e} deg uses row 0 or 1` );
}

// ---- 4. the layout arithmetic -------------------------------------------------------------------
{
	const [ u, v ] = bandFrameUv( 0, 0, [ 0, 0 ], GEOM );
	check( close( u, ( 8 + 0.5 ) / 4096 ), 'frame (0,0) starts one gutter in on u' );
	check( close( v, 1 - ( 8 + 0.5 ) / 1024 ), 'row 0 counted from the BOTTOM is the bottom of the image' );
	const [ u2 ] = bandFrameUv( 11, 0, [ 1, 0 ], GEOM );
	check( close( u2, ( 11 * 341 + 8 + 325 + 0.5 ) / 4096 ) && u2 < 1,
		'the last column\'s right edge stays inside the atlas' );
	const [ , v2 ] = bandFrameUv( 2, 2, [ 0, 1 ], GEOM );
	check( v2 > 0 && v2 < 1 && close( v2, 1 - ( 2 * 341 + 8 + 325 + 0.5 ) / 1024 ),
		'the top row\'s top edge stays inside the atlas' );
	// every frame's inner region must be disjoint from its neighbour's: gutter on both sides
	check( 12 * GEOM.framePx <= GEOM.atlasW && 3 * GEOM.framePx <= GEOM.atlasH,
		'12 x 3 frames of 341 px fit inside 4096 x 1024' );
	check( GEOM.innerPx + 2 * GEOM.gutterPx === GEOM.framePx, 'inner + 2 x gutter = frame' );
	// row_origin: top is the same arithmetic without the flip
	const top = bandFrameUv( 0, 0, [ 0, 0 ], { ...GEOM, rowOrigin: 'top' } );
	check( close( top[ 1 ], ( 8 + 0.5 ) / 1024 ), 'row_origin "top" drops the v flip and nothing else' );
}

// ---- 5. the GLSL mirrors this, textually --------------------------------------------------------
{
	const notes = [];
	const { group, report } = buildImpostors( {
		impostors: { count: 1, grid: 12, atlasPx: 1024, framePx: 85, innerPx: 81, gutterPx: 2,
			prototypeMap: {}, variant2k: null,
			prototypes: { P: { albedo: 'a.ktx2', range: 2, radius: 5, heightAboveBase: 10, centreZ: 5, bytes: 1 } } },
		far: [ { prototype: 'P', id: 't', height: 10, base: [ 0, 0, 0 ] } ],
		loadTexture: async () => null, note: ( m ) => notes.push( m ), msaa: true, samples: 4,
		band: { switch: null, block: { ...GEOM, prototypes: { P: { albedo: 'band/P.ktx2', bytes: 9 } }, count: 1 } },
	} );
	await report.promise;                 // the boot notes are written when the atlases resolve
	const mat = group.children[ 0 ].material;
	check( 'PFA_IMP_BAND' in mat.defines, 'the band define is set when the manifest carries the block' );
	check( mat.uniforms.atlasWH.value.x === 4096 && mat.uniforms.atlasWH.value.y === 1024,
		'the atlas is (4096, 1024), not a square' );
	check( mat.uniforms.framePx.value === 341 && mat.uniforms.innerPx.value === 325
		&& mat.uniforms.gutterPx.value === 8, 'the frame geometry comes from the block, not from the octahedral one' );
	check( mat.uniforms.pfaBand.value.x === 12 && mat.uniforms.pfaBand.value.y === 3
		&& close( mat.uniforms.pfaBand.value.z, 0 ), 'columns, rows and azimuth0 reach the shader' );
	check( close( mat.uniforms.pfaBandEl.value.y, 20 * Math.PI / 180 ),
		'the elevations reach the shader in RADIANS' );
	check( mat.uniforms.rowFromTop.value === 0, 'row_origin "bottom" keeps the octahedral v flip' );
	check( close( mat.uniforms.pfaImpCov.value.z, IMP_COV.shareBand ),
		'the band draws with its own swept coverage share' );
	const src = mat.fragmentShader;
	check( /atan\( d.x, d.y \) - pfaBand.z/.test( src ),
		'the shader measures azimuth as atan2(x, y) from azimuth0 — the same convention as bandSelect' );
	check( /cf = cf - floor\( cf \/ cols \) \* cols;/.test( src ), 'the shader wraps the column the same way' );
	check( /w = vec3\( 1.0 - f, f, 0.0 \);/.test( src ), 'two columns, linear in angle, the third weight 0' );
	check( /asin\( clamp\( d.z, -1.0, 1.0 \) \)/.test( src ), 'elevation is asin(z), clamped' );
	check( notes.some( ( m ) => /BAND atlas \(Phase 8b\)/.test( m ) && /azimuth 0 at 0 deg/.test( m )
		&& /clockwise seen from above/.test( m ) && /elevation rows 0\/20\/40 deg/.test( m ) ),
	'the boot log states the convention it is drawing with' );
	check( report.band.prototypes === 1 && report.band.available === true,
		'the report counts the prototypes the band covers' );
}

// ---- 6. the switch, and a prototype the band does not carry --------------------------------------
{
	for ( const v of [ '0', 'off', 'none' ] ) check( parseImpBand( v ).on === false, `?impband=${v} keeps the octahedral path` );
	for ( const v of [ '', '1', 'on', null ] ) check( parseImpBand( v ).on === true, `?impband=${v} is the default` );
	check( parseImpBand( 'yes' ).on === true && parseImpBand( 'yes' ).unknown === 'yes',
		'a typo falls back to the default AND says so' );

	const notes = [];
	const mk = ( sw, protos ) => buildImpostors( {
		impostors: { count: 2, grid: 12, atlasPx: 1024, framePx: 85, innerPx: 81, gutterPx: 2,
			prototypeMap: {}, variant2k: { atlasPx: 2048, framePx: 170, gutterPx: 4, innerPx: 162 },
			prototypes: {
				P: { albedo: 'a.ktx2', albedo2k: 'a2k.ktx2', range: 2, radius: 5, heightAboveBase: 10, centreZ: 5, bytes: 1 },
				Q: { albedo: 'q.ktx2', albedo2k: 'q2k.ktx2', range: 2, radius: 5, heightAboveBase: 10, centreZ: 5, bytes: 1 } } },
		far: [ { prototype: 'P', id: 't1', height: 10, base: [ 0, 0, 0 ] },
			{ prototype: 'Q', id: 't2', height: 10, base: [ 9, 0, 0 ] } ],
		loadTexture: async () => null, note: ( m ) => notes.push( m ), msaa: true, samples: 4, atlas2k: true,
		band: { switch: sw, block: { ...GEOM, prototypes: protos, count: Object.keys( protos ).length } },
	} );
	const half = mk( null, { P: { albedo: 'band/P.ktx2', bytes: 9 } } );
	const mats = Object.fromEntries( half.group.children.map( ( c ) => [ c.userData.pfaImpostor.prototype, c.material ] ) );
	check( 'PFA_IMP_BAND' in mats.P.defines, 'the prototype the band carries draws the band' );
	check( ! ( 'PFA_IMP_BAND' in mats.Q.defines ), 'the one it does not keeps the octahedral path' );
	check( mats.Q.uniforms.atlasWH.value.x === 2048 && mats.Q.uniforms.framePx.value === 170,
		'and keeps its 2K geometry — the two are never mixed inside one material' );
	check( half.report.band.missing.includes( 'Q' ), 'the report names the prototype that kept the octahedral atlas' );

	const off = mk( '0', { P: { albedo: 'band/P.ktx2', bytes: 9 } } );
	for ( const c of off.group.children )
		check( ! ( 'PFA_IMP_BAND' in c.material.defines ), `?impband=0: ${c.userData.pfaImpostor.prototype} is octahedral` );
	check( off.group.children[ 0 ].material.uniforms.atlasWH.value.x === 2048,
		'?impband=0 is the 2K path, geometry included' );
	// the octahedral path is BYTE-FOR-BYTE what it was: same defines, same uniform values
	const plain = buildImpostors( {
		impostors: { count: 1, grid: 12, atlasPx: 1024, framePx: 85, innerPx: 81, gutterPx: 2,
			prototypeMap: {}, variant2k: null,
			prototypes: { P: { albedo: 'a.ktx2', range: 2, radius: 5, heightAboveBase: 10, centreZ: 5, bytes: 1 } } },
		far: [ { prototype: 'P', id: 't', height: 10, base: [ 0, 0, 0 ] } ],
		loadTexture: async () => null, note: () => {}, msaa: true, samples: 4,
	} );
	const pm = plain.group.children[ 0 ].material;
	check( pm.uniforms.atlasWH.value.x === 1024 && pm.uniforms.atlasWH.value.y === 1024
		&& pm.uniforms.rowFromTop.value === 0, 'with no band block at all the atlas is square and unflipped' );
	check( ! ( 'PFA_IMP_BAND' in pm.defines ) && close( pm.uniforms.pfaImpCov.value.z, IMP_COV.share ),
		'and it draws with the octahedral coverage share' );
}

console.log( `\nthree r${THREE.REVISION}` );
console.log( fails ? `${fails} FAILED` : 'all passed' );
process.exit( fails ? 1 : 0 );
