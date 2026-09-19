// Phase 8b item A — alpha as COVERAGE under magnification, checked without a browser:
//   node test/impostor_cov_test.mjs
//
// Three things none of which a screenshot can show:
//   1. `?impcov=` parses the way the header says (off / default / band / a typo that says so), and
//      the coverage QUANTUM follows the target: 1/samples only when a coverage mask is actually
//      written, 1 (the ordered-dither fallback) otherwise - including the case that bit Phase 7,
//      `?impedge=premul` on a multisampled target, where three sets no alphaToCoverage at all;
//   2. buildImpostors turns that into the define, the uniform and the report the boot note reads;
//   3. the shader still COMPILES as GLSL ES 1.0 in the four define combinations (a missing
//      `#endif` or a `pfaBayer4` behind the wrong guard is a black canvas in Chrome and nothing at
//      all in node), and `?impcov=0` leaves the Phase 7 source byte-identical.
import * as THREE from 'three';
import { buildImpostors, parseImpCov, ALPHA_TEST } from '../src/impostors.js';

let fails = 0;
const check = ( ok, msg ) => { if ( ! ok ) fails ++; console.log( `${ok ? 'PASS' : 'FAIL'}  ${msg}` ); };

// ---- 1. the parser ----------------------------------------------------------------------------
const on4 = parseImpCov( null, { a2c: true, samples: 4 } );
check( on4.on && on4.magLo === 1 && on4.magHi === 2, `default: on, handover 1->2 (got ${on4.magLo}->${on4.magHi})` );
check( on4.quant === 0.25 && on4.samples === 4 && ! on4.dither, 'default on a 4x target: quantum 1/4, no binary fallback' );
for ( const v of [ '0', 'off', 'none', 'OFF' ] )
	check( parseImpCov( v, { a2c: true, samples: 4 } ).on === false, `?impcov=${v} restores Phase 7` );
for ( const v of [ '1', 'on', '' ] )
	check( parseImpCov( v, { a2c: true, samples: 4 } ).on === true, `?impcov=${v} is the default` );
const band = parseImpCov( '2,6', { a2c: true, samples: 4 } );
check( band.on && band.magLo === 2 && band.magHi === 6, 'a band parses: 2 -> 6 screen px per texel' );
const one = parseImpCov( '3', { a2c: true, samples: 4 } );
check( one.magLo === 3 && one.magHi === 6, 'one number sets magLo and doubles it for magHi' );
const rev = parseImpCov( '4,2', { a2c: true, samples: 4 } );
check( rev.magHi > rev.magLo, 'an inverted band cannot divide by zero' );
const bad = parseImpCov( 'yes please', { a2c: true, samples: 4 } );
check( bad.on && bad.magLo === 1 && bad.unknown === 'yes please', 'a typo falls back to the default AND says so' );
// the quantum: no mask written -> 1, which is the ordered-dither fallback
check( parseImpCov( null, { a2c: false, samples: 4 } ).quant === 1, 'no alpha-to-coverage: quantum 1 (ordered dither)' );
check( parseImpCov( null, { a2c: false, samples: 4 } ).dither === true, 'no alpha-to-coverage: the fallback says so' );
check( parseImpCov( null, { a2c: true, samples: 1 } ).quant === 1, 'a 1-sample target is not multisampled: quantum 1' );
check( parseImpCov( null, { a2c: true, samples: 8 } ).quant === 0.125, 'an 8x target: quantum 1/8, not a hard-coded 1/4' );

// ---- 2. the build -----------------------------------------------------------------------------
const IMPOSTORS = {
	count: 1, grid: 12, atlasPx: 1024, framePx: 85, innerPx: 81, gutterPx: 2,
	prototypeMap: {}, variant2k: null,
	prototypes: { P: { albedo: 'a.ktx2', range: 2, radius: 5, heightAboveBase: 10, centreZ: 5, bytes: 1 } },
};
const FAR = [ { prototype: 'P', id: 't1', height: 10, base: [ 0, 0, 0 ] } ];

async function build( opts ) {
	const notes = [];
	const { group, report } = buildImpostors( {
		impostors: IMPOSTORS, far: FAR, loadTexture: async () => null,
		note: ( m ) => notes.push( m ), ...opts,
	} );
	await report.promise;
	const mat = group.children[ 0 ].material;
	return { report, mat, notes: notes.join( '\n' ) };
}

const b = await build( { edge: null, msaa: true, samples: 4, coverage: null } );
check( 'PFA_IMP_COV' in b.mat.defines, 'default: PFA_IMP_COV is defined' );
check( b.mat.uniforms.pfaImpCov.value.x === 1 && b.mat.uniforms.pfaImpCov.value.y === 2
	&& b.mat.uniforms.pfaImpCov.value.z === 0.25, 'the uniform carries (magLo, magHi, quantum)' );
check( b.report.coverage.on && b.report.coverage.samples === 4 && b.report.coverage.orderedDither === false,
	'the report states the coverage path, for __pfaInfo and the gate' );
check( /alpha as COVERAGE \(Phase 8b\): ON/.test( b.notes ) && /quantum 1\/4/.test( b.notes ),
	'the boot note names it' );

const off = await build( { edge: null, msaa: true, samples: 4, coverage: '0' } );
check( ! ( 'PFA_IMP_COV' in off.mat.defines ), '?impcov=0: the define is gone (the Phase 7 program)' );
check( off.mat.fragmentShader === b.mat.fragmentShader, 'the source is one string: only the defines differ' );
check( /alpha as COVERAGE \(Phase 8b\): off/.test( off.notes ), '?impcov=0 says so in the boot note' );

const noMsaa = await build( { edge: null, msaa: false, samples: 0, coverage: null } );
check( noMsaa.mat.alphaToCoverage === false, 'no multisampled target: three writes no coverage mask' );
check( noMsaa.mat.uniforms.pfaImpCov.value.z === 1, 'and the quantum is 1 — the ordered-dither fallback' );
check( /ordered dither, no coverage mask/.test( noMsaa.notes ), 'the fallback is named in the boot note' );

const premulOnly = await build( { edge: 'premul', msaa: true, samples: 4, coverage: null } );
check( premulOnly.mat.alphaToCoverage === false && premulOnly.mat.uniforms.pfaImpCov.value.z === 1,
	'?impedge=premul on an MSAA target: no mask is written, so the quantum falls back to 1' );

// ---- 3. the shader compiles, in every define combination ---------------------------------------
// A headless WebGL context is not available, so the program is built by three's own shader chain
// and parsed: the guards are checked structurally (every #ifdef closed, every symbol defined in the
// branch that uses it), which is what the define combinations can actually break.
const SRC = b.mat.fragmentShader;
for ( const sym of [ 'pfaBayer4', 'pfaImpCov', 'PFA_IMP_COV' ] )
	check( SRC.includes( sym ), `the shader carries ${sym}` );
const ifs = ( SRC.match( /#ifdef|#ifndef|#if\b/g ) || [] ).length;
const ends = ( SRC.match( /#endif/g ) || [] ).length;
check( ifs === ends, `every preprocessor guard is closed (${ifs} open, ${ends} #endif)` );
// pfaBayer4 is used only where it is defined
const defAt = SRC.indexOf( 'float pfaBayer4' );
const useAt = SRC.indexOf( 'pfaBayer4( gl_FragCoord' );
check( defAt > 0 && useAt > defAt, 'pfaBayer4 is declared before it is called' );
check( SRC.indexOf( '#ifdef PFA_IMP_COV' ) < defAt, 'and its declaration sits inside the PFA_IMP_COV guard' );
// the Phase 7 contract: the cutoff itself is untouched
check( ALPHA_TEST === 0.33, 'the alpha test is unchanged at 0.33' );
check( /pfaCov = mix\( pfaCov, covMag, magT \)/.test( SRC ), 'the two paths are mixed by the magnification' );

// The same preprocessor pass the GPU would do, so a branch that never compiles here is caught.
function preprocess( src, defines ) {
	const out = [];
	const stack = [ true ];
	for ( const line of src.split( '\n' ) ) {
		const t = line.trim();
		let m;
		if ( ( m = t.match( /^#ifdef\s+(\w+)/ ) ) ) { stack.push( stack[ stack.length - 1 ] && m[ 1 ] in defines ); continue; }
		if ( ( m = t.match( /^#ifndef\s+(\w+)/ ) ) ) { stack.push( stack[ stack.length - 1 ] && ! ( m[ 1 ] in defines ) ); continue; }
		if ( t === '#else' ) { const top = stack.pop(); stack.push( stack[ stack.length - 1 ] && ! top ); continue; }
		if ( t === '#endif' ) { stack.pop(); continue; }
		if ( stack[ stack.length - 1 ] ) out.push( line );
	}
	return out.join( '\n' );
}
for ( const combo of [ {}, { PFA_IMP_COV: '' }, { PFA_IMP_COV: '', PFA_IMP_A2C: '' },
	{ PFA_IMP_COV: '', PFA_IMP_A2C: '', PFA_IMP_PREMUL: '' }, { PFA_IMP_A2C: '', PFA_IMP_PREMUL: '' },
	{ PFA_IMP_COV: '', PFA_IMP_PREMUL: '', PFA_FOG: '' } ] ) {
	const name = Object.keys( combo ).join( '+' ) || '(none)';
	const p = preprocess( SRC, combo );
	const usesBayer = p.includes( 'pfaBayer4( gl_FragCoord' );
	check( ! usesBayer || p.includes( 'float pfaBayer4' ), `${name}: pfaBayer4 defined wherever it is called` );
	check( ( p.match( /\{/g ) || [] ).length === ( p.match( /\}/g ) || [] ).length, `${name}: braces balance` );
	check( p.includes( 'if ( pfaCov <= 0.0 ) discard;' ), `${name}: the fragment is still dropped at zero coverage` );
	check( ( p.match( /float pfaCov/g ) || [] ).length === 1, `${name}: pfaCov is declared exactly once` );
	check( p.includes( 'gl_FragColor = vec4( lin, pfaCov );' ), `${name}: the coverage reaches the output` );
	// no define combination may leave `a` unassigned or assigned twice
	check( ( p.match( /^\s*float a;$/gm ) || [] ).length === 1, `${name}: the alpha is declared once` );
}

// three has to keep honouring the flag on a raw ShaderMaterial, or the coverage never reaches the GPU
check( b.mat.alphaToCoverage === true, 'the material asks for alpha-to-coverage on a multisampled target' );
check( THREE.REVISION >= '186'.slice( 0, 3 ), `three r${THREE.REVISION}` );

console.log( fails ? `\n${fails} FAILED` : '\nall passed' );
process.exit( fails ? 1 : 0 );
