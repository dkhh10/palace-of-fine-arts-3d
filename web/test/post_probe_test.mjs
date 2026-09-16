// postChain.js and probeEnv.js: the two places a wrong default would silently reach a scored capture.
import * as THREE from 'three';
import { parsePost, readCompositor, applyMist, removeMist, mistShapeGlsl, MIST_NEAR_M, MIST_FAR_M } from '../src/postChain.js';
import { applyProbeEnv } from '../src/probeEnv.js';

let fails = 0;
const check = ( ok, what ) => { console.log( `${ok ? 'PASS' : 'FAIL'}  ${what}` ); if ( ! ok ) fails ++; };

// --- ?post= : only an ABSENT parameter may mean the default -------------------------------------
{
	const off = ( p ) => ! p.mist && ! p.bloom && ! p.vignette;
	const on = ( p ) => p.mist && p.bloom && p.vignette;
	check( off( parsePost( undefined ) ), 'post absent -> none (the default is off, so a capture is untouched)' );
	check( off( parsePost( null ) ), 'post null -> none' );
	check( off( parsePost( '' ) ), 'post EMPTY -> none (screenshot.mjs --query can emit "post=")' );
	check( off( parsePost( '   ' ) ), 'post blank -> none' );
	check( off( parsePost( 'nonsense' ) ), 'post unrecognised -> none, never all' );
	check( on( parsePost( 'all' ) ) && on( parsePost( '1' ) ), 'post=all / post=1 -> everything on' );
	check( off( parsePost( 'none' ) ) && off( parsePost( '0' ) ), 'post=none / post=0 -> everything off' );
	const p = parsePost( 'bloom,vignette' );
	check( ! p.mist && p.bloom && p.vignette, 'post=bloom,vignette -> those two only' );
}

// --- the mist is refused unless the manifest states Blender's own normalisation -------------------
{
	const raw = { COMP_golden_hour: { 'Haze Color': [ 5.32, 3.74, 1.96, 1 ], 'Haze Strength': 0.25,
		'Haze Falloff': 5.0, 'Bloom Threshold': 6.41, 'Bloom Strength': 0.05, 'Bloom Size': 0.6, Vignette: 0.08 } };
	const comp = readCompositor( raw );
	check( comp.hazeStrength === 0.25 && comp.hazeFalloff === 5.0 && comp.vignette === 0.08, 'compositor parameters read' );
	check( comp.mist === null, 'no compositor.mist in this manifest' );

	const scene = new THREE.Scene();
	const r = applyMist( scene, comp );
	check( !! r && !! r.refused && ! scene.fog, `mist REFUSED without compositor.mist: ${r && r.refused ? r.refused.slice( 0, 48 ) + '…' : 'NOT refused'}` );

	const r2 = applyMist( scene, comp, { near: 10, far: 500 } );
	check( !! scene.fog && r2.invented === true, 'an explicit ?mist=near,far is allowed and flags itself invented' );
	check( r2.near === 10 && r2.far === 500, `?mist= is honoured (${r2.near}..${r2.far})` );
	removeMist( scene );
	check( ! scene.fog, 'removeMist clears it' );

	// with the real block, the numbers come from Blender and nothing is invented
	const comp2 = readCompositor( { ...raw, mist: { use_mist: true, start: 20, depth: 2000, falloff: 'LINEAR', intensity: 0, height: 0 } } );
	const r3 = applyMist( new THREE.Scene(), comp2 );
	check( r3 && ! r3.refused && r3.invented === false && r3.near === 20 && r3.far === 2020,
		`compositor.mist gives 20..2020 m, invented=false (got ${r3 && r3.near}..${r3 && r3.far})` );
	check( r3.cap === 0.25 && r3.k === 5.0 && Math.abs( r3.extinctionLength_m - 400 ) < 1e-9,
		`cap 0.25, k 5 (the EXTINCTION COEFFICIENT), extinction length ${r3.extinctionLength_m} m` );
	check( r3.near !== MIST_NEAR_M && r3.far !== MIST_FAR_M, 'and the placeholder constants are not used' );

	// a height fade is refused rather than approximated
	const comp3 = readCompositor( { ...raw, mist: { use_mist: true, start: 20, depth: 2000, falloff: 'LINEAR', intensity: 0, height: 40 } } );
	const r4 = applyMist( new THREE.Scene(), comp3 );
	check( !! r4.refused && /height/.test( r4.refused ), 'a non-zero mist height is refused, not approximated' );
}

// --- the mist shaping follows compositor.mist.falloff, not the haze exponent ---------------------
check( mistShapeGlsl( 'LINEAR' ) === 't', 'LINEAR falloff -> t' );
check( mistShapeGlsl( 'QUADRATIC' ) === 't * t', 'QUADRATIC -> t*t' );
check( mistShapeGlsl( 'INVERSE_QUADRATIC' ) === 'sqrt( t )', 'INVERSE_QUADRATIC -> sqrt(t)' );
check( mistShapeGlsl( undefined ) === 't', 'a missing falloff defaults to LINEAR, which is what this scene uses' );

// --- the probe reaches EXACTLY the materials with no baked light of their own --------------------
{
	const scene = new THREE.Scene();
	const env = new THREE.Texture();
	const mk = ( name, extra = {} ) => {
		const m = new THREE.MeshStandardMaterial( { name } );
		Object.assign( m, extra );
		const o = new THREE.Mesh( new THREE.BoxGeometry(), m );
		scene.add( o );
		return m;
	};
	const bare = mk( 'MAT_EXP_ENVBD__MAT_backdrop_building' );
	const lit = mk( 'MAT_lightmapped', { lightMap: new THREE.Texture() } );
	const patched = mk( 'MAT_patched' );
	patched.userData.pfaPatched = { specularOnlySun: true };
	const hasEnv = mk( 'MAT_already_has_env', { envMap: new THREE.Texture() } );
	const shader = new THREE.ShaderMaterial( { name: 'MAT_WEB_impostor' } );
	scene.add( new THREE.Mesh( new THREE.BoxGeometry(), shader ) );

	const r = applyProbeEnv( scene, env );
	check( bare.envMap === env, 'a material with no baked light gets the probe' );
	check( lit.envMap === null, 'a LIGHTMAPPED material is left alone' );
	check( patched.envMap === null, 'a patched (vertex-irradiance) material is left alone' );
	check( hasEnv.envMap !== env, 'a material that already owns an envMap keeps it (the baked glossy specular)' );
	check( shader.envMap === undefined || shader.envMap === null, 'a ShaderMaterial (the impostors) is not touched' );
	check( r.materials === 1 && r.skippedPatched === 2 && r.skippedHasEnv === 1 && r.skippedNonStandard === 1,
		`report: ${r.materials} applied, ${r.skippedPatched} baked, ${r.skippedHasEnv} had env, ${r.skippedNonStandard} non-standard` );
	check( applyProbeEnv( scene, null ).materials === 0, 'no probe texture -> nothing applied, no throw' );
}

console.log( fails ? `${fails} check(s) FAILED` : 'all post/probe checks passed' );
process.exit( fails ? 1 : 0 );
