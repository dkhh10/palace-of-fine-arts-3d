// Phase 9 item 1 — the DOTTED RIM on the far-crown silhouettes (QA 21 item 1), checked without a
// browser and without a GPU:
//
//     node test/impostor_rim_test.mjs
//
// The measurement that identifies the mechanism is `web/tools/p9v_rim.py` (it needs the delivered
// captures and the 4096x1024 band atlas PNGs, neither of which lives in a worktree). What belongs
// HERE is everything about the fix that a screenshot cannot show and that must not rot:
//
//   1. THE ARITHMETIC THAT MAKES IT A FIX. The mask a driver is allowed to build is
//      popcount = floor( cov * N + d( x, y ) ) with d in [0,1) - GL ES 3.0 s15.1.3 says in as many
//      words that the bits may depend on the pixel location. That popcount depends on d for a
//      general cov and CANNOT depend on it when cov * N is an integer. Exhaustively: every ladder
//      point of N = 2 / 4 / 8 against 64 dither phases, and the float product is checked to be the
//      integer EXACTLY (1/N is a binary fraction, so it is, and the whole fix rests on that).
//   2. THE SAME THING AS AN IMAGE. A smooth coverage ramp pushed through a 2x2-dithered mask scores
//      a checkerboard index (the projection of the high-pass residual on the (x+y) parity sign,
//      normalised by its rms - the measure the capture is scored with) far above the undithered
//      mask's; quantised first, it lands back ON the undithered mask's score.
//   3. THE WIRING. `?impq=` parses, the define / uniform / report / boot note follow the TARGET's
//      own sample count, the quantiser is never asked for where no coverage mask is written (the
//      ordered Bayer fallback already emits 0 or 1), and the shader still preprocesses in every
//      define combination with the statement between the coverage block and the discard.
import * as THREE from 'three';
import { buildImpostors, parseImpQuant, ALPHA_TEST } from '../src/impostors.js';

let fails = 0;
const check = ( ok, msg ) => { if ( ! ok ) fails ++; console.log( `${ok ? 'PASS' : 'FAIL'}  ${msg}` ); };

// ---- 1. the arithmetic ------------------------------------------------------------------------
// The shader's one line, in JS.
const quantise = ( cov, n ) => Math.floor( cov * n + 0.5 ) / n;
// A mask of the form the spec permits: any dither phase d in [0,1).
const popcount = ( cov, n, d ) => Math.min( Math.max( Math.floor( cov * n + d ), 0 ), n );

for ( const n of [ 2, 4, 8 ] ) {
	let ladderStable = true, ladderExact = true;
	for ( let k = 0; k <= n; k ++ ) {
		const cov = k / n;
		if ( cov * n !== k ) ladderExact = false;      // 1/N is a binary fraction: this must hold
		for ( let i = 0; i < 64; i ++ ) {
			const d = i / 64;                           // every phase in [0,1)
			if ( popcount( cov, n, d ) !== k ) ladderStable = false;
		}
	}
	check( ladderExact, `N=${n}: every ladder point k/N multiplies back to the exact integer k` );
	check( ladderStable, `N=${n}: on the ladder the popcount is k for every one of 64 dither phases` );
}
// and off the ladder it is NOT stable - which is the defect, stated as a test so the fix cannot be
// mistaken for a no-op.
let offLadderMoves = 0;
for ( const cov of [ 0.10, 0.30, 0.45, 0.62, 0.87 ] ) {
	const seen = new Set();
	for ( let i = 0; i < 64; i ++ ) seen.add( popcount( cov, 4, i / 64 ) );
	if ( seen.size > 1 ) offLadderMoves ++;
}
check( offLadderMoves === 5, 'off the ladder the popcount DOES move with the dither phase (5/5 probes)' );
// the quantiser lands every input on a ladder point, and moves it by at most half a step
let maxErr = 0, allOnLadder = true;
for ( let i = 0; i <= 1000; i ++ ) {
	const cov = i / 1000, q = quantise( cov, 4 );
	if ( q * 4 !== Math.round( q * 4 ) ) allOnLadder = false;
	maxErr = Math.max( maxErr, Math.abs( q - cov ) );
}
check( allOnLadder, 'the quantiser lands every coverage in [0,1] on a ladder point' );
check( maxErr <= 0.5 / 4 + 1e-12, `and moves it by at most half a step (max ${maxErr.toFixed( 4 )} <= 0.125)` );
check( quantise( 0, 4 ) === 0 && quantise( 1, 4 ) === 1, 'full and zero coverage are fixed points' );
// a fragment whose coverage rounds to zero is DISCARDED, not drawn at zero samples: the shader runs
// the quantiser before `if ( pfaCov <= 0.0 ) discard;`, and this is the boundary it moves.
check( quantise( 0.124, 4 ) === 0 && quantise( 0.126, 4 ) === 0.25,
	'the discard boundary sits at half a step (0.125), as the ladder requires' );

// ---- 2. the same thing as an image -------------------------------------------------------------
// A silhouette: a smooth coverage ramp across a diagonal edge, the field the shader hands over.
const W = 96, H = 96;
const field = [];
for ( let y = 0; y < H; y ++ ) for ( let x = 0; x < W; x ++ ) {
	const t = ( x + 0.37 * y ) / 9 - 4;              // ~9 px of ramp, like a magnified atlas texel
	field.push( Math.min( Math.max( t, 0 ), 1 ) );
}
const BAYER2 = [ 0, 2, 3, 1 ];                        // the classic 2x2 ordered matrix
const dither = ( x, y ) => ( BAYER2[ ( y % 2 ) * 2 + ( x % 2 ) ] + 0.5 ) / 4;
function render( fn ) {
	const out = new Float64Array( W * H );
	for ( let y = 0; y < H; y ++ ) for ( let x = 0; x < W; x ++ ) out[ y * W + x ] = fn( field[ y * W + x ], x, y );
	return out;
}
function checkerIndex( img ) {
	// high-pass, then project on the (x+y) parity sign over the PARTIAL pixels only
	let amp = 0, sq = 0, n = 0;
	for ( let y = 1; y < H - 1; y ++ ) for ( let x = 1; x < W - 1; x ++ ) {
		const c = field[ y * W + x ];
		if ( c <= 0.001 || c >= 0.999 ) continue;
		const hp = img[ y * W + x ] - 0.25 * ( img[ y * W + x - 1 ] + img[ y * W + x + 1 ]
			+ img[ ( y - 1 ) * W + x ] + img[ ( y + 1 ) * W + x ] );
		amp += hp * ( 1 - 2 * ( ( x + y ) % 2 ) );
		sq += hp * hp; n ++;
	}
	return Math.abs( amp / n ) / Math.max( Math.sqrt( sq / n ), 1e-12 );
}
const plain = checkerIndex( render( ( c ) => c ) );
const noDither = checkerIndex( render( ( c ) => popcount( c, 4, 0.5 ) / 4 ) );
const dithered = checkerIndex( render( ( c, x, y ) => popcount( c, 4, dither( x, y ) ) / 4 ) );
const fixed = checkerIndex( render( ( c, x, y ) => popcount( quantise( c, 4 ), 4, dither( x, y ) ) / 4 ) );
console.log( `      checkerboard index — the ramp itself ${plain.toFixed( 3 )}, undithered mask `
	+ `${noDither.toFixed( 3 )}, DITHERED mask ${dithered.toFixed( 3 )}, quantised + dithered ${fixed.toFixed( 3 )}` );
check( plain < 0.02, `the coverage field the shader computes carries no period-2 term (${plain.toFixed( 3 )})` );
check( dithered > 0.2, `a pixel-position-dependent mask manufactures one (${dithered.toFixed( 3 )})` );
check( fixed <= noDither + 1e-9, `quantising first returns it to the undithered mask's own level `
	+ `(${fixed.toFixed( 3 )} vs ${noDither.toFixed( 3 )})` );
check( dithered > fixed * 4, 'the fix is worth a factor of four or more on that index' );
// and it does not cost the EDGE: the mean coverage over the ramp is preserved to within half a step
let mA = 0, mB = 0;
for ( let i = 0; i < field.length; i ++ ) { mA += field[ i ]; mB += quantise( field[ i ], 4 ); }
check( Math.abs( mA - mB ) / field.length < 0.02,
	`the quantiser preserves the mean coverage of the edge (${Math.abs( mA - mB ) / field.length < 0.02 ? 'ok' : 'no'}, `
	+ `${( Math.abs( mA - mB ) / field.length ).toFixed( 4 )})` );

// ---- 3. the wiring ------------------------------------------------------------------------------
const mask4 = { a2c: true, samples: 4 };
check( parseImpQuant( null, mask4 ).on === true, 'default on a 4x target with a mask: ON' );
check( parseImpQuant( null, mask4 ).samples === 4, 'and it snaps to the TARGET\'s four samples' );
check( parseImpQuant( null, { a2c: true, samples: 8 } ).samples === 8, 'an 8x target snaps to eight, not to an assumed four' );
for ( const v of [ '0', 'off', 'none', 'OFF' ] )
	check( parseImpQuant( v, mask4 ).on === false, `?impq=${v} restores the Phase 8b coverage path` );
for ( const v of [ '1', 'on', '' ] ) check( parseImpQuant( v, mask4 ).on === true, `?impq=${v} is the default` );
const typo = parseImpQuant( 'yes', mask4 );
check( typo.on === true && typo.unknown === 'yes', 'a typo falls back to the default AND says so' );
check( parseImpQuant( null, { a2c: false, samples: 4 } ).on === false,
	'no alpha-to-coverage: nothing to quantise, the ordered dither already emits 0 or 1' );
check( parseImpQuant( null, { a2c: true, samples: 1 } ).on === false,
	'a 1-sample target is not multisampled: off' );
// r1 review 5: ?impcov=0 is documented in three places as restoring the PHASE 7 frame, so the
// quantiser rides on the Phase 8b coverage path and goes off with it.
check( parseImpQuant( null, { a2c: true, samples: 4, coverage: false } ).on === false,
	'?impcov=0: the quantiser goes off with the Phase 8b coverage path, so Phase 7 is restored exactly' );
check( /impcov=0/.test( parseImpQuant( null, { a2c: true, samples: 4, coverage: false } ).why ),
	'and `why` names that guard, not a generic "off"' );
// r1 review 13: four refusals, four reasons.
check( /asked off/.test( parseImpQuant( '0', mask4 ).why ), '?impq=0 says it was asked off' );
check( /no coverage mask/.test( parseImpQuant( null, { a2c: false, samples: 4 } ).why ),
	'no mask says so, rather than reading as "off"' );
check( parseImpQuant( null, mask4 ).why === null, 'and an ON quantiser has no refusal reason' );
check( parseImpQuant( '0', mask4 ).samples === 4,
	'report.quantise.samples is the TARGET\'s ladder even when the switch is off: a sidecar must read .on' );

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
	return { report, mat: group.children[ 0 ].material, notes: notes.join( '\n' ) };
}

const on = await build( { edge: null, msaa: true, samples: 4, coverage: null, quantise: null } );
check( 'PFA_IMP_QUANT' in on.mat.defines, 'default build: PFA_IMP_QUANT is defined' );
check( on.mat.uniforms.pfaCovQ.value === 4, 'and pfaCovQ carries the target\'s sample count' );
check( on.report.quantise.on === true && on.report.quantise.samples === 4,
	'the report states it, for __pfaInfo and the gate' );
check( /coverage QUANTISER \(Phase 9 item 1, the dotted rim\): ON/.test( on.notes )
	&& /4-sample ladder/.test( on.notes ), 'the boot note names it and the ladder' );

const off = await build( { edge: null, msaa: true, samples: 4, coverage: null, quantise: '0' } );
check( ! ( 'PFA_IMP_QUANT' in off.mat.defines ), '?impq=0: the define is gone (the Phase 8b coverage path)' );
check( off.mat.uniforms.pfaCovQ.value === 0, 'and the uniform is zero, so a stale value cannot leak in' );
check( off.mat.fragmentShader === on.mat.fragmentShader, 'the source is one string: only the defines differ' );
check( off.mat.alphaToCoverage === on.mat.alphaToCoverage && on.mat.alphaToCoverage === true,
	'the coverage mask itself is untouched either way' );
check( /coverage QUANTISER[^\n]*off/.test( off.notes ), '?impq=0 says so in the boot note' );

const covOff = await build( { edge: null, msaa: true, samples: 4, coverage: '0', quantise: null } );
check( ! ( 'PFA_IMP_QUANT' in covOff.mat.defines ) && ! ( 'PFA_IMP_COV' in covOff.mat.defines ),
	'?impcov=0 builds the Phase 7 program: neither the coverage path NOR the quantiser (r1 review 5)' );
check( covOff.mat.uniforms.pfaCovQ.value === 0, '?impcov=0: and pfaCovQ is zero' );
check( /QUANTISER[^\n]*off — the Phase 8b coverage path is off/.test( covOff.notes ),
	'?impcov=0: the boot note says WHICH guard refused' );

const noMask = await build( { edge: null, msaa: false, samples: 0, coverage: null, quantise: null } );
check( ! ( 'PFA_IMP_QUANT' in noMask.mat.defines ),
	'no coverage mask: the quantiser is not compiled (the Bayer fallback already emits 0 or 1)' );
check( /coverage QUANTISER[^\n]*no coverage mask is written/.test( noMask.notes ),
	'and the boot note says WHY, not just that' );
const premulOnly = await build( { edge: 'premul', msaa: true, samples: 4, coverage: null, quantise: null } );
check( ! ( 'PFA_IMP_QUANT' in premulOnly.mat.defines ),
	'?impedge=premul on an MSAA target writes no mask, so the quantiser stays off' );

// ---- 4. the shader source ------------------------------------------------------------------------
const SRC = on.mat.fragmentShader;
check( SRC.includes( 'uniform float pfaCovQ;' ), 'the shader declares pfaCovQ' );
check( /pfaCov = floor\( pfaCov \* pfaCovQ \+ 0\.5 \) \/ pfaCovQ;/.test( SRC ), 'and carries the one statement' );
check( SRC.indexOf( 'pfaCov = mix( pfaCov, covMag, magT )' ) < SRC.indexOf( 'pfaCov = floor( pfaCov * pfaCovQ' ),
	'the quantiser runs AFTER the Phase 8b coverage block' );
check( SRC.indexOf( 'pfaCov = floor( pfaCov * pfaCovQ' ) < SRC.indexOf( 'if ( pfaCov <= 0.0 ) discard;' ),
	'and BEFORE the discard, so a coverage that rounds to zero drops the fragment' );
check( ALPHA_TEST === 0.33, 'the alpha test is unchanged at 0.33' );
check( ! /lin \*= pow/.test( SRC ) && ! /rgb = rgb \*/.test( SRC ), 'and nothing in the colour path changed' );
check( ( SRC.match( /#ifdef|#ifndef|#if\b/g ) || [] ).length === ( SRC.match( /#endif/g ) || [] ).length,
	'every preprocessor guard is closed' );

function preprocess( src, defines ) {
	const out = [], stack = [ true ];
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
for ( const combo of [ {}, { PFA_IMP_QUANT: '' }, { PFA_IMP_COV: '', PFA_IMP_A2C: '', PFA_IMP_QUANT: '' },
	{ PFA_IMP_COV: '', PFA_IMP_A2C: '', PFA_IMP_PREMUL: '', PFA_IMP_QUANT: '' },
	{ PFA_IMP_COV: '', PFA_IMP_A2C: '', PFA_IMP_PREMUL: '', PFA_IMP_BAND: '', PFA_IMP_QUANT: '', PFA_FOG: '' } ] ) {
	const name = Object.keys( combo ).join( '+' ) || '(none)';
	const p = preprocess( SRC, combo );
	check( ( p.match( /\{/g ) || [] ).length === ( p.match( /\}/g ) || [] ).length, `${name}: braces balance` );
	check( ( p.match( /float pfaCov;|float pfaCov =/g ) || [] ).length === 1, `${name}: pfaCov is declared exactly once` );
	check( p.includes( 'if ( pfaCov <= 0.0 ) discard;' ), `${name}: the fragment is still dropped at zero coverage` );
	check( p.includes( 'gl_FragColor = vec4( lin, pfaCov );' ), `${name}: the coverage reaches the output` );
	// the quantiser only ever runs with its define, and never on the no-mask (Bayer) path
	const hasQ = p.includes( 'pfaCov = floor( pfaCov * pfaCovQ' );
	check( hasQ === ( 'PFA_IMP_QUANT' in combo ), `${name}: the quantiser follows its define exactly` );
	check( ! hasQ || ! p.includes( 'pfaBayer4( gl_FragCoord' ),
		`${name}: the quantiser and the ordered-dither fallback are never both compiled` );
}

// ---- 5. the carried review findings -------------------------------------------------------------
// phase8_viewer_r2_review finding 4, carried through r3 ("open, correctly left"): a camera exactly on
// a billboard centre makes vDirBlender zero and normalize() NaN, which reaches BOTH frame lookups.
check( /vec3 pfaViewDir\( vec3 v \) \{ return \( dot\( v, v \) > 0\.0 \) \? normalize\( v \) : vec3\( 1\.0, 0\.0, 0\.0 \); \}/.test( SRC ),
	'r2 carry 4: the degenerate view direction has a guard' );
check( ! /normalize\( vDirBlender \)/.test( SRC ) && ( SRC.match( /pfaViewDir\( vDirBlender \)/g ) || [] ).length === 2,
	'r2 carry 4: and BOTH lookups (band and octahedral) go through it' );
check( SRC.indexOf( 'vec3 pfaViewDir' ) < SRC.indexOf( 'pfaViewDir( vDirBlender )' ),
	'r2 carry 4: declared before it is called' );
// the guard must not touch a non-degenerate direction: normalize() is still what runs there.
const viewDir = ( v ) => ( v[ 0 ] * v[ 0 ] + v[ 1 ] * v[ 1 ] + v[ 2 ] * v[ 2 ] ) > 0
	? v.map( ( c ) => c / Math.hypot( ...v ) ) : [ 1, 0, 0 ];
check( viewDir( [ 0, 0, 0 ] ).every( Number.isFinite ), 'r2 carry 4: the zero vector returns a finite direction' );
check( Math.abs( Math.hypot( ...viewDir( [ 3, -4, 0 ] ) ) - 1 ) < 1e-12, 'r2 carry 4: and a real one is still unit length' );

// phase8_viewer_r2_review finding 6a: the band branch must not fetch its zero-weight third frame.
check( /const int PFA_FRAMES = 2;/.test( SRC ) && /const int PFA_FRAMES = 3;/.test( SRC ),
	'r2 carry 6a: the frame count is a COMPILE-time constant, 2 on the band path and 3 on the octahedral' );
{
	const band = preprocess( SRC, { PFA_IMP_BAND: '', PFA_IMP_PREMUL: '', PFA_IMP_COV: '', PFA_IMP_A2C: '', PFA_IMP_QUANT: '' } );
	check( ! /tc\[ 2 \] = frameTexel/.test( band ), 'r2 carry 6a: the band path builds no third texel coordinate' );
	check( ! /vec4 s2 = sampleFrame/.test( band ), 'r2 carry 6a: and takes no third frame sample' );
	const octa = preprocess( SRC, { PFA_IMP_PREMUL: '', PFA_IMP_COV: '', PFA_IMP_A2C: '', PFA_IMP_QUANT: '' } );
	check( /tc\[ 2 \] = frameTexel/.test( octa ), 'r2 carry 6a: the octahedral path still builds all three' );
}

check( THREE.REVISION >= '186'.slice( 0, 3 ), `three r${THREE.REVISION}` );
console.log( fails ? `\n${fails} FAILED` : '\nall passed' );
process.exit( fails ? 1 : 0 );
