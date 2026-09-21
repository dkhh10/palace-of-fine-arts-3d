// Phase 9: the SPECULAR GATE (docs/briefs/phase9_bake_analysis_report.md B.6), without a browser.
//   PFA_MAIN_ROOT=/path/to/main-checkout node test/spec_gate_test.mjs
//
// The gate is two clamped ratios applied to two specular terms, and every way it can be wrong is
// silent: a wrong unit at either end (the constants are irradiance/pi, the shader's
// `lightMapIrradiance` is that TIMES lightMapIntensity) is a gate that is off by pi and still renders
// a picture; a wrong channel gates the sun by the sky; a gate that reaches a material with no
// lightmap darkens the impostors and the water. So:
//   1. the gate's arithmetic against the B.6 decile table, band by band, to the stated values;
//   2. the unit conversion, proved by driving the reference implementation with a SHADER-side value;
//   3. the emitted GLSL: it carries the same three constants, applies skyVis to the IBL specular and
//      sunVis to reflectedLight.directSpecular, and reads the decoded texel divided by the intensity;
//   4. `?specgate=0` — the Phase 8 fragment shader and program cache key, character for character;
//   5. a material with no lightmap in the patch is untouched (impostors, water, backdrop, foliage);
//   6. the real manifest's constants, when they are on disk, put the near_column box's own lightmap
//      band at the visibility B.6 predicts.
import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import * as THREE from 'three';
import { patchBakedMaterial, specGateFrom, specGateEval, specGateGlsl, specGateCommonGlsl,
	skyE0OverPi } from '../src/materials.js';

const WEB = path.resolve( fileURLToPath( new URL( '..', import.meta.url ) ) );
const MAIN = process.env.PFA_MAIN_ROOT || path.resolve( WEB, '..' );
let fails = 0;
const check = ( ok, msg ) => { if ( ! ok ) fails ++; console.log( `${ok ? 'PASS' : 'FAIL'}  ${msg}` ); };
const near = ( a, b, tol, msg ) => check( Math.abs( a - b ) <= tol, `${msg} (got ${a.toFixed( 4 )}, want ${b} +-${tol})` );

// The B.6 fixture: the numbers the analysis measured on the CURRENT sky_diffuse and the CURRENT sun.
// They are a FIXTURE, not a constant — manifest_v4 re-derives them from the shipped equirect on every
// run, and the lighting re-bake will move them. What must not move is the arithmetic below.
const OPEN_SKY = [ 2.196, 3.432, 11.256 ];
const SUN_IRR_PI = 21.428;
const G = specGateFrom( OPEN_SKY, SUN_IRR_PI );

// ---------------------------------------------------------------- 0. the constructor refuses junk
{
	check( !! G && G.openSkyB === 11.256, `specGateFrom builds from the manifest pair (openSkyB ${G && G.openSkyB})` );
	near( G.skyRedOverBlue, 0.1951, 0.0001, 'skyRedOverBlue = openSky.r / openSky.b, B.6\'s 0.1951' );
	for ( const [ what, sky, sun ] of [
		[ 'no sky constant', null, SUN_IRR_PI ],
		[ 'a 2-channel sky', [ 1, 2 ], SUN_IRR_PI ],
		[ 'a zero blue channel', [ 2.196, 3.432, 0 ], SUN_IRR_PI ],
		[ 'a NaN channel', [ 2.196, NaN, 11.256 ], SUN_IRR_PI ],
		[ 'no sun constant', OPEN_SKY, null ],
		[ 'a zero sun', OPEN_SKY, 0 ],
		[ 'a string sun', OPEN_SKY, 'twenty-one' ] ] )
		check( specGateFrom( sky, sun ) === null, `${what} -> null (the gate is OFF, never a guessed denominator)` );
}

// ---------------------------------------------------------------- 1. the B.6 decile table
// `export/p9_shade_terms.py`'s measurement of the colonnade's own lightmap EXR
// (ARCH_colonnade_south_concrete_colonnade_merged), by luminance decile, in irradiance/pi.
const DECILES = [
	// band,          mean R G B,                    B/11.256, sunVis, note
	[ 'p0-10 deep shade', [ 0.051, 0.051, 0.088 ], 0.008, 0.0016, 'sees almost no sky' ],
	[ 'p10-25', [ 0.244, 0.237, 0.404 ], 0.036, null, '' ],
	[ 'p25-50', [ 0.568, 0.544, 0.951 ], 0.084, null, '' ],
	[ 'p50-75 half-open', [ 1.076, 1.145, 3.622 ], 0.322, null, '' ],
	[ 'p75-95 sky-exposed', [ 3.190, 3.035, 9.128 ], 0.811, null, '' ],
	[ 'p95-100 sunlit', [ 16.334, 11.130, 1.604 ], 0.142, 0.747, 'sun-dominated, B/R 0.098' ],
];
for ( const [ band, rgb, skyVis, sunVis, note ] of DECILES ) {
	const v = specGateEval( rgb, G );
	near( v.skyVis, skyVis, 0.0006, `${band}: skyVis = b/openSky.b = ${skyVis}${note ? ` (${note})` : ''}` );
	if ( sunVis !== null ) near( v.sunVis, sunVis, 0.001, `${band}: sunVis = ${sunVis}` );
}
{
	// The two ends are what the whole fix rests on: deep shade must take ~nothing of either specular,
	// and the sunlit band must take most of the sun (its own dotNL) while taking little of the sky.
	const deep = specGateEval( DECILES[ 0 ][ 1 ], G ), lit = specGateEval( DECILES[ 5 ][ 1 ], G );
	check( deep.sunVis < 0.005 && deep.skyVis < 0.01,
		`deep shade kills both specular terms (sunVis ${deep.sunVis.toFixed( 4 )}, skyVis ${deep.skyVis.toFixed( 4 )})` );
	check( lit.sunVis > 0.7 && lit.skyVis < 0.2,
		`the sunlit band keeps the sun and not the sky (sunVis ${lit.sunVis.toFixed( 3 )}, skyVis ${lit.skyVis.toFixed( 3 )})` );
	// Monotonic in the sky channel: a texel that sees more sky can never be gated harder.
	let mono = true;
	for ( let i = 1; i < 5; i ++ ) mono = mono && specGateEval( DECILES[ i ][ 1 ], G ).skyVis > specGateEval( DECILES[ i - 1 ][ 1 ], G ).skyVis;
	check( mono, 'skyVis rises monotonically p0-10 -> p75-95' );
	// Both are clamped: a sky brighter than the open sky, or a sun texel above dotNL = 1 (the bounce
	// off a sunlit wall onto a sunlit one), must not amplify.
	const hot = specGateEval( [ 200, 150, 60 ], G );
	check( hot.skyVis === 1 && hot.sunVis === 1, 'both ratios clamp to 1 on an over-bright texel' );
	const black = specGateEval( [ 0, 0, 0 ], G );
	check( black.skyVis === 0 && black.sunVis === 0, 'a black texel gates both terms to 0' );
	// The red correction can push sunVis negative (a texel lit by sky only); it must clamp at 0, not
	// go negative and flip the specular's sign.
	check( specGateEval( [ 0.05, 0.08, 0.6 ], G ).sunVis === 0, 'a sky-only texel clamps sunVis at 0, never negative' );
}

// ---------------------------------------------------------------- 2. the unit conversion
{
	// What the shader holds is `lightMapIrradiance` = texel * lightMapIntensity, and lightMapIntensity
	// is the manifest's `lightmaps.scale` = pi. Feeding that number straight to the gate — the one
	// mistake that would look plausible and be wrong by pi — is checked here against the right answer.
	const texel = DECILES[ 0 ][ 1 ];                       // deep shade, in the bake's irradiance/pi
	const shaderSide = texel.map( v => v * Math.PI );      // what the chunk's variable actually holds
	const right = specGateEval( shaderSide.map( v => v / Math.PI ), G );
	const wrong = specGateEval( shaderSide, G );
	near( right.skyVis, 0.008, 0.0006, 'dividing lightMapIrradiance by lightMapIntensity reproduces B.6' );
	check( wrong.skyVis / right.skyVis > 3.1 && wrong.skyVis / right.skyVis < 3.2,
		`skipping that division is a ${( wrong.skyVis / right.skyVis ).toFixed( 3 )}x error (= pi), which is why the shader divides` );
}

// ---------------------------------------------------------------- 3 + 4 + 5. the shader patch
const freshShader = () => ( { vertexShader: THREE.ShaderLib.physical.vertexShader,
	fragmentShader: THREE.ShaderLib.physical.fragmentShader, uniforms: {} } );
{
	const gated = new THREE.MeshStandardMaterial(); gated.lightMap = new THREE.Texture();
	patchBakedMaterial( gated, { lightMapEncoding: 'gamma2', range: 44.409718, specGate: G } );
	const sg = freshShader();
	let err = null;
	try { gated.onBeforeCompile( sg, null ); } catch ( e ) { err = e; }
	check( ! err, `the gated patch substitutes into three ${THREE.REVISION}${err ? `: ${err.message}` : ''}` );
	const f = sg.fragmentShader;
	check( /vec3 pfaLmPi = lightMapIrradiance \/ lightMapIntensity;/.test( f ),
		'the gate reads the decoded texel DIVIDED BY lightMapIntensity (the bake\'s units, both ends)' );
	check( f.includes( 'pfaSkyVis = clamp( pfaLmPi.b / 11.256000, 0.0, 1.0 )' ),
		'skyVis divides the BLUE channel by the manifest\'s openSky.b' );
	check( f.includes( 'pfaSunVis = clamp( ( pfaLmPi.r - 0.195096 * pfaLmPi.b ) / 21.428000, 0.0, 1.0 )' ),
		'sunVis takes RED less the sky\'s red share, over the sun\'s irradiance/pi' );
	check( f.includes( 'radiance += iblRadiance * pfaSkyVis;' ) && ! /radiance \+= iblRadiance;/.test( f ),
		'skyVis scales the IBL specular radiance, and the ungated line is gone' );
	check( /reflectedLight\.directSpecular \*= pfaSunVis;/.test( f ), 'sunVis scales reflectedLight.directSpecular' );
	check( /float pfaSkyVis = 1\.0;/.test( f ) && /float pfaSunVis = 1\.0;/.test( f ),
		'both default to 1.0 outside every #if, so a program without USE_LIGHTMAP or USE_ENVMAP is unchanged' );
	// the gate must not touch the diffuse side, which is the term B.2 measured as correct
	check( /irradiance \+= lightMapIrradiance;/.test( f ), 'the diffuse lightmap term is untouched' );
	check( ! /iblIrradiance \+= getIBLIrradiance/.test( f ), 'the env diffuse is still removed (Phase 6 behaviour kept)' );
	check( specGateGlsl( G ).includes( '11.256000' ) && specGateGlsl( G ).includes( '21.428000' )
		&& specGateGlsl( G ).includes( '0.195096' ),
		'specGateGlsl carries exactly the three constants specGateFrom derived' );
	check( gated.userData.pfaPatched.specGate && gated.userData.pfaPatched.specGate.openSkyB === 11.256,
		'the material records the constants it compiled in (the sidecar reads this, not the url flag)' );
}
{
	// 4. ?specgate=0 — bit-identical to Phase 8.
	const a = new THREE.MeshStandardMaterial(); a.lightMap = new THREE.Texture();
	patchBakedMaterial( a, { lightMapEncoding: 'gamma2', range: 44.409718, specGate: null } );
	const b = new THREE.MeshStandardMaterial(); b.lightMap = new THREE.Texture();
	patchBakedMaterial( b, { lightMapEncoding: 'gamma2', range: 44.409718 } );          // the Phase 8 call
	const sa = freshShader(), sb = freshShader();
	a.onBeforeCompile( sa, null ); b.onBeforeCompile( sb, null );
	check( sa.fragmentShader === sb.fragmentShader && sa.vertexShader === sb.vertexShader,
		'?specgate=0 compiles the Phase 8 shader character for character' );
	check( a.customProgramCacheKey() === b.customProgramCacheKey(),
		`and the same program cache key (${b.customProgramCacheKey().split( '|' ).pop()}), so it shares the program` );
	check( ! /pfaSkyVis|pfaSunVis|pfaLmPi/.test( sa.fragmentShader ), 'and carries no gate identifier at all' );
	const c = new THREE.MeshStandardMaterial(); c.lightMap = new THREE.Texture();
	patchBakedMaterial( c, { lightMapEncoding: 'gamma2', range: 44.409718, specGate: G } );
	check( c.customProgramCacheKey() !== b.customProgramCacheKey(),
		'the gated material takes a DIFFERENT cache key, so the two never share one program' );
}
{
	// 5. the paths that have no lightmap must be untouched, gate or no gate.
	const { s } = ( () => {
		const m = new THREE.MeshStandardMaterial();
		patchBakedMaterial( m, { vertexIrradiance: 1.5 } );                 // a near tree: COLOR_0, no lightmap
		const sh = freshShader(); m.onBeforeCompile( sh, null ); return { s: sh };
	} )();
	check( ! /pfaSkyVis|pfaSunVis/.test( s.fragmentShader ), 'the vertex-irradiance path (near trees) takes no gate' );
	const m2 = new THREE.MeshStandardMaterial();
	patchBakedMaterial( m2, { instanceIrradiance: Math.PI, noEnvDiffuse: false } );      // shrubs / reeds
	const s2 = freshShader(); m2.onBeforeCompile( s2, null );
	check( ! /pfaSkyVis|pfaSunVis/.test( s2.fragmentShader ), 'the instance-irradiance path (shrubs, reeds) takes no gate' );
	check( /getIBLIrradiance/.test( s2.fragmentShader ), 'and it keeps its probe env diffuse' );
}

// ---------------------------------------------------------------- 6. the real manifest's constants
{
	const f = path.join( MAIN, 'export/out/gate3/manifest.json' );
	if ( ! existsSync( f ) ) {
		console.log( `      no gate3 manifest at ${f}, the live-constant check is skipped` );
	} else {
		const raw = JSON.parse( readFileSync( f ) );
		const live = specGateFrom( ( raw.sky || {} ).open_irradiance_over_pi, ( raw.sun || {} ).irradiance_over_pi );
		if ( ! live ) {
			console.log( '      the gate3 manifest carries no spec-gate constants yet (re-run export/manifest_v4.py), skipped' );
		} else {
			// The constants move with every lighting re-bake — r19 alone takes the open sky's blue from
			// 11.256 to 5.825 — so what is PINNED here is the RELATION, not the value. B.6's decile table
			// is stated as fractions of the sky and sun it was measured under, and the shipped constants
			// must gate those same fractions to the same visibilities. (An absolute comparison against
			// the B.6 fixture would fail the moment the sky it describes is re-baked, and would be
			// reporting the bake, not the gate.)
			// A band is re-expressed in the shipped sky by taking it apart with the constants it was
			// measured under and putting it back together with these: its blue is that much of the sky,
			// its red-less-the-sky's-share that much of the sun. Under a correct gate the two
			// visibilities are then IDENTICAL to B.6's — which is the property being asserted, that a
			// re-baked sky cannot move the shade end, and it is false for any wrong denominator.
			const band = ( rgb ) => {
				const sunPart = Math.max( rgb[ 0 ] - G.skyRedOverBlue * rgb[ 2 ], 0 );
				const b = rgb[ 2 ] * ( live.openSkyB / G.openSkyB );
				return [ sunPart * ( live.sunIrrOverPi / G.sunIrrOverPi ) + live.skyRedOverBlue * b, rgb[ 1 ], b ];
			};
			const k = [ 0, 0, live.openSkyB / G.openSkyB ];
			const scaleSun = live.sunIrrOverPi / G.sunIrrOverPi;
			console.log( `      shipped constants: openSky ${live.openSky.map( v => v.toFixed( 3 ) )}, `
				+ `sun/pi ${live.sunIrrOverPi.toFixed( 3 )} (B.6's fixture: ${G.openSky.map( v => v.toFixed( 3 ) )}, `
				+ `${G.sunIrrOverPi.toFixed( 3 )}; blue x${k[ 2 ].toFixed( 3 )}, sun x${scaleSun.toFixed( 3 )})` );
			const deep = specGateEval( band( DECILES[ 0 ][ 1 ] ), live );
			check( deep.sunVis < 0.01 && deep.skyVis < 0.012,
				`with the SHIPPED constants, B.6's deep-shade band scaled into this sky still gates to `
				+ `sunVis ${deep.sunVis.toFixed( 4 )} / skyVis ${deep.skyVis.toFixed( 4 )} — the near_column veil` );
			const open = specGateEval( [ live.sunIrrOverPi + live.openSky[ 0 ], 0, live.openSkyB ], live );
			check( open.skyVis > 0.999 && open.sunVis > 0.999,
				`and a fully open, fully sunlit UPWARD texel still reads 1.0 / 1.0 under them` );
		}
	}
}

// ================================================================ ROUND 2 (decisions.md 2026-09-21)
// The round-1 gate above divides by the open sky of an UPWARD-facing surface and multiplies a
// directSpecular that already carries dotNL. Round 2 fixes both: E0(n) for the surface's own world
// normal, from the manifest's sky lobes, and sunVis / max(dotNL, 0.05).
//
// THE FIXTURE. A UNIFORM sky of radiance OPEN_SKY has E(n)/pi = OPEN_SKY for EVERY normal, so it is
// the one sky where round 2 and round 1 must agree exactly on skyVis — which makes it the fixture
// that pins the arithmetic without pinning a particular sky. It is built as delta lobes over the
// whole sphere, the same representation the manifest ships.
const SUN_DIR = ( () => {                                  // manifest sun.direction_blender, negated, b2t
	const b = [ 0.473126, 0.871639, 0.128055 ];            // TOWARD the sun, Blender axes
	const t = [ b[ 0 ], b[ 2 ], - b[ 1 ] ];                // three axes: (bx, bz, -by)
	const n = Math.hypot( ...t );
	return t.map( v => v / n );
} )();
const UNIFORM_LOBES = ( () => {
	const K = 256, out = [];
	for ( let i = 0; i < K; i ++ ) {
		const y = 1 - 2 * ( i + 0.5 ) / K, r = Math.sqrt( Math.max( 0, 1 - y * y ) );
		const a = Math.PI * ( 1 + Math.sqrt( 5 ) ) * i;
		// E(n) = sum I * max(dot) ; for a uniform sphere sampling, sum max(dot) over K dirs -> K/4 * ...
		// the scale is solved below, so the construction never depends on that algebra being right.
		out.push( [ Math.cos( a ) * r, y, Math.sin( a ) * r, 1, 1, 1 ] );
	}
	// with unit rgb, skyE0OverPi returns sum(max(dot(n,d),0)) in both channels: solve for the scale that
	// puts E0(zenith) exactly on OPEN_SKY, and the same scale then holds at every normal by symmetry.
	const s = skyE0OverPi( out, [ 0, 1, 0 ] )[ 0 ];
	return out.map( l => [ l[ 0 ], l[ 1 ], l[ 2 ], OPEN_SKY[ 0 ] / s, OPEN_SKY[ 1 ] / s, OPEN_SKY[ 2 ] / s ] );
} )();
const NORMALS = [ [ 'zenith', [ 0, 1, 0 ] ], [ 'east wall', [ 0, 0, - 1 ] ], [ 'west wall', [ 0, 0, 1 ] ],
	[ 'north wall', [ - 1, 0, 0 ] ], [ 'south wall', [ 1, 0, 0 ] ] ];
const G2 = specGateFrom( OPEN_SKY, SUN_IRR_PI, { lobes: UNIFORM_LOBES, floorFrac: 0.05, sunDir: SUN_DIR } );

// ---------------------------------------------------------------- 7. the round-2 constructor
{
	check( !! G2 && G2.mode === 'r2' && G2.lobes.length === UNIFORM_LOBES.length,
		`specGateFrom builds round 2 from the lobes + the sun direction (${G2 && G2.lobes.length} lobes)` );
	check( G && G.mode === 'r1', 'the two-argument call still builds round 1 (?specgate=1 and the r1 A/B)' );
	near( G2.floor, 0.05 * OPEN_SKY[ 2 ], 0.02, 'the denominator floor is floor_frac x E0(zenith).b' );
	const bad = ( o, what ) => check( specGateFrom( OPEN_SKY, SUN_IRR_PI, o ) === null,
		`${what} -> null (gate OFF, never a silent fall back to round 1's constant denominator)` );
	bad( { lobes: null, floorFrac: 0.05, sunDir: SUN_DIR }, 'no lobes' );
	bad( { lobes: UNIFORM_LOBES.slice( 0, 4 ), floorFrac: 0.05, sunDir: SUN_DIR }, 'a 4-lobe set' );
	bad( { lobes: UNIFORM_LOBES.map( ( l, i ) => i ? l : [ 0, 2, 0, 1, 1, 1 ] ), floorFrac: 0.05, sunDir: SUN_DIR },
		'a lobe whose direction is not unit length' );
	bad( { lobes: UNIFORM_LOBES.map( ( l, i ) => i ? l : [ 0, 1, 0, - 1, 1, 1 ] ), floorFrac: 0.05, sunDir: SUN_DIR },
		'a lobe with a negative channel' );
	bad( { lobes: UNIFORM_LOBES, floorFrac: 0.05, sunDir: [ 0, 2, 0 ] }, 'a sun direction that is not a unit vector' );
	bad( { lobes: UNIFORM_LOBES, floorFrac: 0.05, sunDir: null }, 'no sun direction' );
	bad( { lobes: UNIFORM_LOBES, floorFrac: 0, sunDir: SUN_DIR }, 'a zero floor fraction' );
}

// ---------------------------------------------------------------- 8. E0(n) and the two ends
{
	for ( const [ name, n ] of NORMALS ) {
		const e = skyE0OverPi( UNIFORM_LOBES, n );
		check( Math.abs( e[ 1 ] / OPEN_SKY[ 2 ] - 1 ) < 0.02,
			`uniform fixture: E0(${name}).b = ${e[ 1 ].toFixed( 3 )} = the open sky for EVERY normal (+-2 %)` );
	}
	// (a) THE SHADE END IS UNCHANGED. Under a uniform sky E0(n).b is the round-1 constant at every
	// normal, so the B.6 decile table's skyVis must reproduce to the third decimal, and sunVis must be
	// round 1's divided by dotNL — the only intended change at that end.
	for ( const [ band, rgb, skyVis ] of DECILES ) {
		const v = specGateEval( rgb, G2, [ 0, 1, 0 ] );
		near( v.skyVis, skyVis, 0.001, `${band}: round 2 at the zenith reproduces round 1's skyVis ${skyVis}` );
	}
	const deep = specGateEval( DECILES[ 0 ][ 1 ], G2, [ 0, 0, - 1 ] );
	check( deep.sunVis < 0.005 && deep.skyVis < 0.01,
		`deep shade still kills both terms on an east wall (sunVis ${deep.sunVis.toFixed( 4 )}, skyVis ${deep.skyVis.toFixed( 4 )})` );
	// (b) THE SUNLIT END IS THE FIX. A surface that is FULLY open and FULLY sunlit has, by definition,
	// lm.b = E0(n).b and lm.r = sunIrrOverPi*dotNL + E0(n).r — so both gates must read exactly 1.0, at
	// EVERY orientation. Round 1 reads 0.22 on an east wall, which is the sunlit-station regression.
	for ( const [ name, n ] of NORMALS ) {
		const e = skyE0OverPi( UNIFORM_LOBES, n );
		const dotNL = Math.max( SUN_DIR[ 0 ] * n[ 0 ] + SUN_DIR[ 1 ] * n[ 1 ] + SUN_DIR[ 2 ] * n[ 2 ], 0 );
		const lm = [ SUN_IRR_PI * dotNL + e[ 0 ], 0, e[ 1 ] ];
		const v = specGateEval( lm, G2, n );
		check( v.skyVis > 0.995, `${name}: an unoccluded texel reads skyVis ${v.skyVis.toFixed( 4 )} (round 1: `
			+ `${specGateEval( lm, G, n ).skyVis.toFixed( 4 )})` );
		if ( dotNL > 0.1 ) check( v.sunVis > 0.99,
			`${name}: an unshadowed sunlit texel reads sunVis ${v.sunVis.toFixed( 4 )} at dotNL ${dotNL.toFixed( 3 )} `
			+ `(round 1 before the dotNL division: ${specGateEval( lm, G, n ).sunVis.toFixed( 4 )})` );
	}
	// (c) half-shadowed stays half: the gate is linear in the lightmap between the two ends.
	const n = [ 0, 0, - 1 ], e = skyE0OverPi( UNIFORM_LOBES, n );
	const dotNL = SUN_DIR[ 0 ] * n[ 0 ] + SUN_DIR[ 1 ] * n[ 1 ] + SUN_DIR[ 2 ] * n[ 2 ];
	const half = specGateEval( [ 0.5 * SUN_IRR_PI * dotNL + 0.5 * e[ 0 ], 0, 0.5 * e[ 1 ] ], G2, n );
	near( half.skyVis, 0.5, 0.005, 'a half-open texel reads skyVis 0.5' );
	near( half.sunVis, 0.5, 0.005, 'a half-shadowed texel reads sunVis 0.5' );
	// (d) the two guards: the dotNL floor must not let a grazing face amplify, and the E0 floor must not
	// let a downward-facing soffit read as sky-exposed.
	const graze = specGateEval( [ 3.0, 0, 0.05 ], G2, [ 0, 0, 1 ] );        // west wall, dotNL < 0
	check( graze.dotNL === 0.05 && graze.sunVis <= 1, `a face turned away from the sun floors dotNL at 0.05 `
		+ `and still clamps (sunVis ${graze.sunVis.toFixed( 3 )})` );
	const gDown = specGateFrom( OPEN_SKY, SUN_IRR_PI,
		{ lobes: UNIFORM_LOBES.filter( l => l[ 1 ] > 0.05 ), floorFrac: 0.05, sunDir: SUN_DIR } );
	const soffit = specGateEval( DECILES[ 0 ][ 1 ], gDown, [ 0, - 1, 0 ] );
	check( skyE0OverPi( gDown.lobes, [ 0, - 1, 0 ] )[ 1 ] === 0 && soffit.skyVis < 0.2,
		`a downward normal with E0.b = 0 is floored, not opened (skyVis ${soffit.skyVis.toFixed( 4 )})` );
}

// ---------------------------------------------------------------- 9. the round-2 shader patch
{
	const m = new THREE.MeshStandardMaterial(); m.lightMap = new THREE.Texture();
	patchBakedMaterial( m, { lightMapEncoding: 'gamma2', range: 44.409718, specGate: G2 } );
	const sh = freshShader();
	let err = null;
	try { m.onBeforeCompile( sh, null ); } catch ( e ) { err = e; }
	check( ! err, `the round-2 patch substitutes into three ${THREE.REVISION}${err ? `: ${err.message}` : ''}` );
	const f = sh.fragmentShader;
	check( /vec3 pfaWN = inverseTransformDirection\( geometryNormal, viewMatrix \);/.test( f ),
		'the gate reads the GEOMETRY normal in WORLD space (the lobes are in three world axes)' );
	check( ( f.match( /vec2 pfaSkyE0\( const in vec3 n \)/g ) || [] ).length === 1
		&& f.indexOf( 'vec2 pfaSkyE0' ) < f.indexOf( 'pfaE0 = pfaSkyE0( pfaWN )' ),
		'pfaSkyE0 is declared exactly once, before its call' );
	check( ( f.match( /e \+= max\( dot\( n, vec3\(/g ) || [] ).length === UNIFORM_LOBES.length,
		`the emitted E0 carries all ${UNIFORM_LOBES.length} lobes` );
	check( f.includes( `float pfaDen = max( pfaE0.y, ${G2.floor.toFixed( 6 )} );` ),
		'the denominator is floored with the manifest\'s own floor' );
	check( /pfaSkyVis = clamp\( pfaLmPi\.b \/ pfaDen, 0\.0, 1\.0 \);/.test( f ),
		'skyVis divides the BLUE channel by E0(n).b, not by a constant' );
	check( /float pfaNL = max\( dot\( pfaWN, pfaSunDirW \), 0\.05 \);/.test( f )
		&& new RegExp( `pfaSunVis = clamp\\( \\( pfaLmPi\\.r - \\( pfaE0\\.x / pfaDen \\) \\* pfaLmPi\\.b \\) / \\( ${SUN_IRR_PI.toFixed( 6 )} \\* pfaNL \\)` ).test( f ),
		'sunVis subtracts E0(n).r/E0(n).b of the blue and divides by sunIrrOverPi * max(dotNL, 0.05)' );
	check( f.includes( `const vec3 pfaSunDirW = vec3( ${SUN_DIR.map( v => v.toFixed( 6 ) ).join( ', ' )} );` ),
		'the sun direction compiled in is the manifest\'s own, in three axes' );
	check( f.includes( 'radiance += iblRadiance * pfaSkyVis;' ) && /reflectedLight\.directSpecular \*= pfaSunVis;/.test( f ),
		'both terms are still scaled where they are accumulated' );
	check( /irradiance \+= lightMapIrradiance;/.test( f ) && ! /iblIrradiance \+= getIBLIrradiance/.test( f ),
		'the diffuse side is untouched and the env diffuse is still removed' );
	check( ! /11\.256000/.test( f ), 'and the round-1 constant denominator is gone from the program' );
	// the JS reference and the GLSL must carry the same numbers: spot-check lobe 0 and the floor
	const l0 = UNIFORM_LOBES[ 0 ];
	check( specGateCommonGlsl( G2 ).includes( `vec3( ${l0[ 0 ].toFixed( 6 )}, ${l0[ 1 ].toFixed( 6 )}, ${l0[ 2 ].toFixed( 6 )} ) ), 0.0 ) * vec2( ${l0[ 3 ].toFixed( 6 )}, ${l0[ 5 ].toFixed( 6 )} )` ),
		'each lobe emits its direction and its (r, b) — green is never read, so it is never emitted' );
	check( specGateCommonGlsl( G ) === '', 'round 1 emits no E0 function at all' );
	// the three programs must never be shared
	const mk = ( g ) => { const q = new THREE.MeshStandardMaterial(); q.lightMap = new THREE.Texture();
		patchBakedMaterial( q, { lightMapEncoding: 'gamma2', range: 44.409718, specGate: g } ); return q.customProgramCacheKey(); };
	const k0 = mk( null ), k1 = mk( G ), k2 = mk( G2 );
	check( k0 !== k1 && k1 !== k2 && k0 !== k2, `off / round 1 / round 2 take three different program keys` );
	check( k2.includes( '|sg2:' ) && k1.includes( '|sg:' ), `the round-2 key is tagged sg2 (${k2.split( '|' ).pop()})` );
	// the SLOT path patches `#include <common>` too (its second atlas sampler), and 988 ornament
	// instances take it: both substitutions have to survive each other.
	{
		const q = new THREE.MeshStandardMaterial(); q.lightMap = new THREE.Texture();
		patchBakedMaterial( q, { lightMapEncoding: 'gamma2', range: 44.409718, slot: true,
			atlasB: new THREE.Texture(), specGate: G2 } );
		const s = freshShader();
		let e2 = null;
		try { q.onBeforeCompile( s, null ); } catch ( e ) { e2 = e; }
		check( ! e2 && /uniform sampler2D pfaLmAtlasB/.test( s.fragmentShader )
			&& /vec2 pfaSkyE0/.test( s.fragmentShader ) && /pfaSlotUv/.test( s.fragmentShader ),
			`the slot atlas path takes the gate too (the 988 ornament instances)${e2 ? `: ${e2.message}` : ''}` );
	}
	const k2b = mk( specGateFrom( OPEN_SKY, SUN_IRR_PI,
		{ lobes: UNIFORM_LOBES.map( ( l, i ) => i === 3 ? [ l[ 0 ], l[ 1 ], l[ 2 ], l[ 3 ], l[ 4 ], l[ 5 ] * 1.5 ] : l ),
			floorFrac: 0.05, sunDir: SUN_DIR } ) );
	check( k2b !== k2, 'a single changed lobe changes the cache key (a re-baked sky recompiles)' );
}

// ---------------------------------------------------------------- 10. the SHIPPED sky, when on disk
{
	const f = path.join( MAIN, 'export/out/gate3/manifest.json' );
	const raw = existsSync( f ) ? JSON.parse( readFileSync( f ) ) : null;
	const lob = raw && raw.sky && raw.sky.diffuse_lobes;
	if ( ! lob ) {
		console.log( '      no gate3 manifest with sky.diffuse_lobes on disk, the shipped-sky checks are skipped' );
	} else {
		const live = specGateFrom( raw.sky.open_irradiance_over_pi, raw.sun.irradiance_over_pi,
			{ lobes: lob.lobes, floorFrac: lob.floor_frac, sunDir: SUN_DIR } );
		check( !! live, `the shipped manifest builds a round-2 gate (${lob.count} lobes)` );
		// (a) THE BRIEF'S CHECK: the model evaluated straight up must equal the quadrature's open-sky
		// blue (11.256 on the deploy-12 sky) — the one number that proves the same sky, the same units
		// and the same axes at both ends. It is 0.57 % out today and 1.30 % on the r19 re-bake (the
		// delta-lobe fit's own residual, measured in the manifest's own `checks`), so the bound is 2 %:
		// a convention error is off by pi, by a channel or by 10x, never by 1 %. The FIT's accuracy is
		// asserted separately, below and in manifest_test, and is a lever in manifest_v4's
		// SKY_LOBE_BANDS/SECTORS (8x8 = 64 lobes takes the zenith to 0.29 % / 0.66 % for 60 % more ALU).
		const zen = skyE0OverPi( live.lobes, [ 0, 1, 0 ] );
		check( Math.abs( zen[ 1 ] / raw.sky.open_irradiance_over_pi[ 2 ] - 1 ) < 0.02,
			`E0(zenith).b ${zen[ 1 ].toFixed( 4 )} = sky.open_irradiance_over_pi.b `
			+ `${raw.sky.open_irradiance_over_pi[ 2 ].toFixed( 4 )} to `
			+ `${( ( zen[ 1 ] / raw.sky.open_irradiance_over_pi[ 2 ] - 1 ) * 100 ).toFixed( 2 )} %` );
		// (b) the shade end of the B.6 table, at the zenith normal, is unchanged to the third decimal.
		for ( const [ band, rgb, skyVis ] of DECILES.slice( 0, 3 ) )
			near( specGateEval( rgb, live, [ 0, 1, 0 ] ).skyVis, skyVis, 0.001,
				`shipped sky, ${band}: skyVis ${skyVis} (round 1's number, because E0(zenith) IS that constant)` );
		// (c) the sunlit band on the east wall the colonnade actually presents to this sun. B.6's
		// p95-100 row is (16.334, 11.130, 1.604); round 1 read skyVis 0.142 there because it divided by
		// the zenith's 11.256. Both numbers are REPORTED, not pinned: the sky moves with every re-bake.
		const eN = [ 0, 0, - 1 ];
		const e0 = skyE0OverPi( live.lobes, eN );
		const v = specGateEval( DECILES[ 5 ][ 1 ], live, eN );
		const dotNL = SUN_DIR[ 0 ] * eN[ 0 ] + SUN_DIR[ 1 ] * eN[ 1 ] + SUN_DIR[ 2 ] * eN[ 2 ];
		console.log( `      shipped sky, east wall (+Y blender): E0 = (${e0[ 0 ].toFixed( 3 )} r, ${e0[ 1 ].toFixed( 3 )} b), `
			+ `dotNL ${dotNL.toFixed( 3 )}; B.6's sunlit band reads skyVis ${v.skyVis.toFixed( 3 )} `
			+ `(round 1: ${specGateEval( DECILES[ 5 ][ 1 ], live && G, eN ).skyVis.toFixed( 3 )}), `
			+ `sunVis ${v.sunVis.toFixed( 3 )} (round 1: ${specGateEval( DECILES[ 5 ][ 1 ], G, eN ).sunVis.toFixed( 3 )})` );
		check( v.skyVis > 0.4 && v.skyVis < 1.001,
			`the sunlit band's blue 1.604 is a plausible visibility on that wall (${v.skyVis.toFixed( 3 )}), not 0.142` );
		// (d) the lobes must not point below the horizon: this sky's ground is black, and a lobe under
		// the horizon would hand a soffit an E0 it cannot see.
		check( live.lobes.every( l => l[ 1 ] > - 0.05 ), 'no shipped lobe points below the horizon' );
		// (e) THE SH CONVENTION, against three's own evaluator. manifest_v4 writes sky.diffuse_sh9 in
		// three's SphericalHarmonics3 order and scale; if that is right, three's getIrradianceAt on
		// those coefficients reproduces the value manifest_v4 recorded for the zenith, and (because SH9
		// is a poor fit for this near-horizon sky — which is why the LOBES are the denominator) it also
		// reproduces manifest_v4's measured error against the quadrature.
		const sh9 = raw.sky.diffuse_sh9;
		if ( ! Array.isArray( sh9 ) ) { console.log( '      no sky.diffuse_sh9 in the manifest, the SH convention check is skipped' ); } else {
			const probe = new THREE.SphericalHarmonics3();
			sh9.forEach( ( c, i ) => probe.coefficients[ i ].fromArray( c ) );
			const E = probe.getIrradianceAt( new THREE.Vector3( 0, 1, 0 ), new THREE.Vector3() );
			const rec = lob.checks.reference_normals[ 0 ];
			near( E.z / Math.PI, rec.sh9[ 2 ], Math.abs( rec.sh9[ 2 ] ) * 0.002,
				'three\'s SphericalHarmonics3.getIrradianceAt reproduces manifest_v4\'s own SH9 evaluation at +Y' );
			check( Math.abs( rec.sh9_over_exact_b - 1 ) > 0.05,
				`and SH9 is ${rec.sh9_over_exact_b.toFixed( 3 )}x the quadrature at the zenith, which is why `
				+ `sky.diffuse_lobes (${rec.lobes_over_exact_b.toFixed( 4 )}x) is the denominator` );
		}
	}
}

console.log( fails ? `${fails} FAILURES` : 'all spec-gate checks passed' );
process.exit( fails ? 1 : 0 );
