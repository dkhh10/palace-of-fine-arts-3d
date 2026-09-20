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
import { patchBakedMaterial, specGateFrom, specGateEval, specGateGlsl } from '../src/materials.js';

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
			// Within 1 % of the fixture the analysis measured, or the sky/sun the viewer is gating
			// against is not the one B.6 decomposed and the decile table above no longer describes it.
			check( Math.abs( live.openSkyB - G.openSkyB ) / G.openSkyB < 0.01
				&& Math.abs( live.sunIrrOverPi - G.sunIrrOverPi ) / G.sunIrrOverPi < 0.01,
				`the shipped constants match B.6's fixture: openSky.b ${live.openSkyB}, sun/pi ${live.sunIrrOverPi}` );
			const deep = specGateEval( DECILES[ 0 ][ 1 ], live );
			check( deep.sunVis < 0.005 && deep.skyVis < 0.01,
				`with the SHIPPED constants, B.6's deep-shade band still gates to sunVis ${deep.sunVis.toFixed( 4 )} / `
				+ `skyVis ${deep.skyVis.toFixed( 4 )} — the near_column box's specular veil` );
		}
	}
}

console.log( fails ? `${fails} FAILURES` : 'all spec-gate checks passed' );
process.exit( fails ? 1 : 0 );
