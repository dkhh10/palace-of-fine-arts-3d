// PHASE 8a — the shrub / reed card directional relight (`?cardsun=`).
//
// Nothing here needs a GPU.  The numeric half tests `cardSunFactor`, which is the SPEC the GLSL is
// written from (see CARD_SUN in src/foliage.js); the shader half runs the real patch chain -
// patchBakedMaterial (the per-placement irradiance line) then applyFoliage (the relight that
// rewrites it) - against three's own physical shader, and asserts the one property the switch
// promises: `?cardsun=0` leaves the program BYTE-IDENTICAL to today.
import * as THREE from 'three';
import { patchBakedMaterial } from '../src/materials.js';
import { applyFoliage, parseCardSun, cardSunFactor, cardSunOff, instIrrOf, CARD_SUN,
	shaderErrors } from '../src/foliage.js';

let fails = 0;
const ok = ( c, m ) => { console.log( `${c ? 'PASS' : 'FAIL'}  ${m}` ); if ( ! c ) fails ++; };
const near = ( a, b, e = 1e-9 ) => Math.abs( a - b ) <= e;
const SUN = [ 1.0, 0.607324, 0.0 ];            // the manifest's LIGHT_sun colour (gate3)

// ---------------------------------------------------------------- 1. the switch parses
{
	const d = parseCardSun( undefined );
	ok( d.amt === CARD_SUN.amt && d.share === CARD_SUN.share, `no flag -> the default (amt ${d.amt})` );
	ok( CARD_SUN.amt === 0.6 && CARD_SUN.share === 0.8 && CARD_SUN.wrap === 0.35 && CARD_SUN.shade === 0.9
		&& CARD_SUN.mean === 0.38 && CARD_SUN.chroma === 1 && CARD_SUN.cap === 3 && CARD_SUN.two === 1,
		'the shipped default is the value stage 2 adopted (0.6, 0.8, 0.35, 0.9, 0.38, 1, 3, 1)' );
	ok( parseCardSun( '0.7' ).amt === 0.7, 'a bare number is the amount' );
	ok( parseCardSun( 0.4 ).amt === 0.4, 'a JS number is the amount' );
	ok( parseCardSun( 'off' ).amt === 0 && parseCardSun( '0' ).amt === 0, '"off" / "0" -> amount 0' );
	ok( parseCardSun( 'on' ).amt === CARD_SUN.amt, '"on" -> the adopted amount' );
	const p = parseCardSun( '0.8,0.5,0.25,0.4,0.5,1,3,0' );
	ok( p.amt === 0.8 && p.share === 0.5 && p.wrap === 0.25 && p.shade === 0.4
		&& p.mean === 0.5 && p.chroma === 1 && p.cap === 3 && p.two === 0, 'the whole positional list' );
	ok( parseCardSun( '0.6,' ).share === CARD_SUN.share, 'a missing field keeps its default' );
	// round-1 review 3: a bad switch falls back to the DEFAULT, never to NaN
	const bad = parseCardSun( 'nonsense' );
	ok( Number.isFinite( bad.amt ) && bad.amt === CARD_SUN.amt, 'garbage -> the default, not NaN' );
	const cl = parseCardSun( '9,9,9,9,99,9,99,9' );
	ok( cl.amt === 1 && cl.share === 0.98 && cl.wrap === 4 && cl.shade === 1
		&& cl.mean === 4 && cl.chroma === 1 && cl.cap === 8 && cl.two === 1, 'every field is clamped' );
	ok( cardSunOff( parseCardSun( 'off' ) ) && ! cardSunOff( parseCardSun( '0.3' ) ), 'cardSunOff' );
	ok( parseCardSun( { amt: 0.5, mean: 0.3 } ).mean === 0.3, 'an object works like the string' );
}

// ---------------------------------------------------------------- 2. the factor: the three promises
// A FIXED parameter set, not the shipped default: these assertions are about the shape of the term,
// and they must not move when a later round re-adopts a number.
const FIX = { amt: 1, share: 0.55, wrap: 0.5, shade: 0.6, mean: 0.45, chroma: 0.65, cap: 2.5, two: 1 };
const f = ( amt, nl, depth, extra = {} ) =>
	cardSunFactor( { ...FIX, amt, ...extra }, SUN, nl, depth );
{
	const off = cardSunFactor( { ...FIX, amt: 0 }, SUN, 1, 0 );
	ok( off.every( ( x ) => x === 1 ), 'amt 0 -> exactly [1,1,1] (today), whatever the geometry' );

	// PROMISE 2: g == 1 returns the flat term exactly, in every channel.  nl*clump/mean == 1 with
	// wrap 0.5 and mean 0.45 needs ( nl + 0.5 ) / 1.5 = 0.45 -> nl = 0.175.
	const unity = f( 1, 0.175, 0, { two: 0 } );
	ok( unity.every( ( x ) => near( x, 1, 1e-12 ) ), 'g == 1 -> the flat irradiance, exactly' );

	// PROMISE 2b (the level): a set of cards whose MEAN g is 1 keeps the mean level, per channel.
	// (`two: 0` here so the sample is the signed cosine and the arithmetic is readable.)
	const nls = [ - 1, - 0.5, 0, 0.175, 0.4, 0.8, 1 ];
	const gs = nls.map( ( n ) => Math.min( Math.max( ( n + 0.5 ) / 1.5, 0 ), 1 ) / 0.45 );
	const mean = gs.reduce( ( a, b ) => a + b, 0 ) / gs.length;
	const facs = nls.map( ( n ) => f( 1, n, 0, { two: 0 } ) );
	// the factor is affine in g below the cap, so the MEAN factor is the factor of the mean g: a box
	// whose cards average g = 1 keeps its level exactly, which is the level constraint in one line.
	const atMeanG = f( 1, 1.5 * mean * 0.45 - 0.5, 0, { two: 0 } );
	for ( let k = 0; k < 3; k ++ ) {
		const mf = facs.reduce( ( a, x ) => a + x[ k ], 0 ) / facs.length;
		ok( near( mf, atMeanG[ k ], 1e-9 ),
			`channel ${k}: mean( factor ) == factor( mean g ) (redistribution, not gain)` );
	}

	// TWO-SIDED (`two`, the default): a card is a stand-in for a bush volume and its baked irradiance
	// is two-sided, so its sun term follows how its PLANE sits to the sun, not which side we see.
	ok( near( f( 1, - 0.8, 0 )[ 0 ], f( 1, 0.8, 0 )[ 0 ] ), 'two = 1: |N.L| - the two faces read alike' );
	ok( f( 1, - 0.8, 0, { two: 0 } )[ 0 ] < f( 1, 0.8, 0, { two: 0 } )[ 0 ],
		'two = 0: the one-sided cosine (a backlit card goes to the sky share)' );
	ok( f( 1, 0, 0 )[ 0 ] < f( 1, 1, 0 )[ 0 ],
		'two = 1: a card EDGE-ON to the sun still falls to the sky share' );

	// PROMISE 3: the sun share is warm, the shade it leaves is cool - and derived from the manifest.
	const lit = f( 1, 1, 0 ), shade = f( 1, - 1, 0, { two: 0 } );
	ok( lit[ 0 ] > 1 && lit[ 2 ] < lit[ 0 ], 'a sunward card gains red and stays cooler in blue (gold rim)' );
	ok( shade[ 0 ] < 1 && shade[ 2 ] > shade[ 0 ], 'a lee card loses red and keeps blue (cool shade)' );
	ok( shade[ 1 ] / shade[ 0 ] > 1.2, `the shade goes GREENER: G/R ${( shade[ 1 ] / shade[ 0 ] ).toFixed( 2 )}x` );
	ok( shade.every( ( x ) => x >= 0 ), 'the shade share never goes negative' );

	// the clump / self-shadow term sends the inner and lee cards to the sky share
	const front = f( 1, 1, 0 ), inner = f( 1, 1, 1 );
	// the level drops with the sun share, so the sky term shows as a CHROMA shift, not a blue gain
	ok( inner[ 0 ] < front[ 0 ] && inner[ 1 ] / inner[ 0 ] > front[ 1 ] / front[ 0 ]
		&& inner[ 2 ] / inner[ 0 ] > front[ 2 ] / front[ 0 ],
		'the clump depth moves a card toward the sky term (darker and cooler per unit red)' );
	ok( near( inner[ 0 ], f( 1, 1, 1, { shade: 0.6 } )[ 0 ] ), 'the clump term is `shade`-scaled' );
	ok( f( 1, 1, 1, { shade: 1 } )[ 0 ] < inner[ 0 ], 'a deeper clump term darkens further' );
	ok( f( 1, 1, 1, { shade: 0 } )[ 0 ] === front[ 0 ], 'shade 0 -> the pure cosine' );

	// monotone in N.L, and the cap bites
	let mono = true, monoTwo = true;
	for ( let i = 1; i <= 20; i ++ ) {
		const a = f( 1, - 1 + ( i - 1 ) / 10, 0, { two: 0 } )[ 0 ], b = f( 1, - 1 + i / 10, 0, { two: 0 } )[ 0 ];
		if ( b < a - 1e-12 ) mono = false;
		const c = f( 1, ( i - 1 ) / 20, 0 )[ 0 ], d = f( 1, i / 20, 0 )[ 0 ];
		if ( d < c - 1e-12 ) monoTwo = false;
	}
	ok( mono, 'two = 0: the red channel is monotone in N.L' );
	ok( monoTwo, 'two = 1: the red channel is monotone in |N.L|' );
	const capped = f( 1, 1, 0, { mean: 0.05, cap: 1.5 } ), uncapped = f( 1, 1, 0, { mean: 0.05, cap: 8 } );
	ok( capped[ 0 ] < uncapped[ 0 ], 'the cap limits a card that is far above the scene mean' );

	// the 0.98 clamp on the share: a pure-red sun would otherwise take the sky share negative
	const red = cardSunFactor( { ...FIX, share: 0.98, chroma: 1, two: 0 }, [ 1, 0, 0 ], - 1, 1 );
	ok( red.every( ( x ) => x >= 0 ), `a degenerate sun colour stays >= 0 ([${red.map( ( x ) => x.toFixed( 3 ) )}])` );
	const black = cardSunFactor( { ...FIX }, [ 0, 0, 0 ], 1, 0 );
	ok( black.every( ( x ) => Number.isFinite( x ) && x >= 0 ), 'a black sun colour is finite (fallback to neutral)' );
	ok( near( cardSunFactor( { ...FIX, chroma: 0, two: 0 }, SUN, 0.175, 0 )[ 0 ], 1 ),
		'chroma 0 is a pure level term (no hue rotation)' );
}

// ---------------------------------------------------------------- 3. the shader patch
function cardScene( n = 2 ) {
	const scene = new THREE.Scene();
	const g = new THREE.BufferGeometry();
	// two cards a metre apart: one cluster, a real pfaCrown / pfaCrownD to hang the clump term on
	g.setAttribute( 'position', new THREE.BufferAttribute( new Float32Array( [
		- 0.5, 0, 0, 0.5, 0, 0, 0, 1, 0, - 0.5, 0, 1, 0.5, 0, 1, 0, 1, 1 ] ), 3 ) );
	g.setAttribute( 'normal', new THREE.BufferAttribute( new Float32Array( [
		0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1 ] ), 3 ) );
	const mat = new THREE.MeshStandardMaterial( { name: 'MAT_shrub' } );
	const mesh = new THREE.InstancedMesh( g, mat, n );
	mesh.name = 'WEB_cards';
	for ( let i = 0; i < n; i ++ ) mesh.setMatrixAt( i, new THREE.Matrix4().makeTranslation( i * 3, 0, 0 ) );
	g.setAttribute( 'pfaInstIrr', new THREE.InstancedBufferAttribute( new Float32Array( n * 3 ).fill( 1.5 ), 3 ) );
	g.setAttribute( 'pfaInstOn', new THREE.InstancedBufferAttribute( new Float32Array( n ).fill( 1 ), 1 ) );
	scene.add( mesh );
	return { scene, mat, mesh };
}
const sunLight = new THREE.DirectionalLight( new THREE.Color( SUN[ 0 ], SUN[ 1 ], SUN[ 2 ] ), 3 );
sunLight.position.set( 0.473, 0.128, 0.872 );

function compile( mat ) {
	const shader = { vertexShader: THREE.ShaderLib.physical.vertexShader,
		fragmentShader: THREE.ShaderLib.physical.fragmentShader, uniforms: {} };
	let err = null;
	try { mat.onBeforeCompile( shader, null ); } catch ( e ) { err = e; }
	return { shader, err };
}
function build( cardSun ) {
	const { scene, mat } = cardScene();
	patchBakedMaterial( mat, { instanceIrradiance: Math.PI, noEnvDiffuse: false, specularOnlySun: true } );
	const report = applyFoliage( { scene, sun: sunLight, cardSun, note: () => {} } );
	const { shader, err } = compile( mat );
	return { report, shader, err, mat };
}
{
	const before = shaderErrors.length;
	const off = build( 0 ), on = build( '0.8' );
	ok( ! off.err && ! on.err, `both patch chains substitute into three ${THREE.REVISION}`
		+ `${off.err ? `: ${off.err.message}` : ''}${on.err ? `: ${on.err.message}` : ''}` );
	ok( shaderErrors.length === before, `no recorded shader error (${shaderErrors.slice( before ).join( '; ' )})` );

	// THE PROMISE: ?cardsun=0 is not "close to" today, it is the same program - no 8a token reaches
	// either stage, so the compiled shader is the pre-8a one byte for byte.
	const dflt = build( undefined );
	ok( ! /pfaCard/.test( off.shader.fragmentShader ) && ! /pfaCard/.test( off.shader.vertexShader ),
		'?cardsun=0 -> not one 8a token in either stage (the pre-8a program)' );
	ok( off.shader.fragmentShader === build( 'off' ).shader.fragmentShader,
		'?cardsun=0 and ?cardsun=off compile the same source' );
	ok( /pfaCardSun/.test( dflt.shader.fragmentShader ),
		'no flag -> the ADOPTED default is patched in (CARD_SUN.amt > 0)' );
	ok( /irradiance \+= vPfaInstIrr \* 3\.141593;/.test( off.shader.fragmentShader ),
		'with the relight off the flat per-placement line is untouched' );
	ok( off.mat.customProgramCacheKey().endsWith( ':0' ) && on.mat.customProgramCacheKey().endsWith( ':1' ),
		'the program cache key carries the relight bit' );

	// and with it on, the flat line is GONE, replaced by the split
	ok( ! /irradiance \+= vPfaInstIrr \* 3\.141593;/.test( on.shader.fragmentShader ),
		'with the relight on the flat line is rewritten, not added to' );
	ok( /vec3 pfaE = vPfaInstIrr \* 3\.141593;/.test( on.shader.fragmentShader ),
		'the same decode constant is carried into the split (no second scale)' );
	for ( const s of [ 'uniform vec4 pfaCardSun;', 'uniform vec4 pfaCardSunB;', 'uniform vec3 pfaSunDir;',
		'uniform vec3 pfaSunIrr;', 'pfaSunC = mix( vec3( 1.0 ), pfaSunC, pfaCardSunB.y );',
		'dot( normal, pfaSunL )', 'clamp( vPfaCrownD.z, 0.0, 1.0 )',
		'mix( pfaCardC, abs( pfaCardC ), pfaCardSunB.w )' ] )
		ok( on.shader.fragmentShader.includes( s ), `the relight block declares/uses \`${s}\`` );
	ok( ( on.shader.fragmentShader.match( /uniform vec3 pfaSunDir;/g ) || [] ).length === 1,
		'pfaSunDir is declared exactly once (no redeclaration against the translucent lobe)' );

	// the uniforms reach the shader with the parsed values, and the sun with the manifest ones
	const u = on.shader.uniforms;
	ok( u.pfaCardSun && near( u.pfaCardSun.value.x, 0.8 ) && near( u.pfaCardSun.value.y, CARD_SUN.share ),
		'pfaCardSun = ( amt, share, wrap, shade )' );
	ok( u.pfaCardSunB && near( u.pfaCardSunB.value.x, CARD_SUN.mean ) && near( u.pfaCardSunB.value.z, CARD_SUN.cap )
		&& near( u.pfaCardSunB.value.w, CARD_SUN.two ), 'pfaCardSunB = ( mean, chroma, cap, two )' );
	ok( u.pfaSunIrr && near( u.pfaSunIrr.value.r, SUN[ 0 ] * 3, 1e-6 ),
		'the sun COLOUR the relight uses is the light three itself uses (colour x intensity)' );
	ok( u.pfaSunDir && near( u.pfaSunDir.value.length(), 1, 1e-6 ), 'the sun DIRECTION is the shared unit vector' );
	ok( on.report.cardSunMaterials === 1 && on.report.cardSunSkipped.length === 0,
		`the report counts the relit card materials (${on.report.cardSunMaterials})` );
	ok( on.report.cardSun.amt === 0.8, 'the report carries the parsed switch' );
}
{
	// ?cardint=0: no interior varying, so the clump term degenerates instead of failing to compile
	const { scene, mat } = cardScene();
	patchBakedMaterial( mat, { instanceIrradiance: Math.PI, noEnvDiffuse: false, specularOnlySun: true } );
	applyFoliage( { scene, sun: sunLight, cardSun: '1', cardInterior: '0', note: () => {} } );
	const { shader, err } = compile( mat );
	ok( ! err && ! /vPfaCrownD/.test( shader.fragmentShader ),
		`?cardint=0 + ?cardsun=1 compiles with no crown varying${err ? `: ${err.message}` : ''}` );
	ok( /pfaCardClump = 1\.0 - pfaCardSun\.w \* 0\.0;/.test( shader.fragmentShader ),
		'without the interior term the clump factor is a literal 1' );
}
{
	// a card material the bake never measured (no per-placement irradiance) is REPORTED, not patched
	const scene = new THREE.Scene();
	const g = new THREE.BufferGeometry();
	g.setAttribute( 'position', new THREE.BufferAttribute( new Float32Array( 9 ), 3 ) );
	g.setAttribute( 'normal', new THREE.BufferAttribute( new Float32Array( [ 0, 0, 1, 0, 0, 1, 0, 0, 1 ] ), 3 ) );
	const mat = new THREE.MeshStandardMaterial( { name: 'MAT_reeds' } );
	scene.add( new THREE.Mesh( g, mat ) );
	const report = applyFoliage( { scene, sun: sunLight, cardSun: '1', note: () => {} } );
	ok( instIrrOf( mat ) === null && report.cardSunMaterials === 0
		&& report.cardSunSkipped.includes( 'MAT_reeds' ), 'an unmeasured card is skipped and named' );
	const { err } = compile( mat );
	ok( ! err, 'and it still compiles' );
}

console.log( fails ? `\n${fails} FAILED` : '\nall passed' );
process.exit( fails ? 1 : 0 );
