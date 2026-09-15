// Generates .cube LUTs used to verify the display pass end to end (not shipped):
//   node tools/make_test_lut.mjs            -> public/test/gamma22.cube  (domain 0..1)
//   node tools/make_test_lut.mjs 4          -> public/test/gamma22_d4.cube (domain 0..4)
// Both encode display = linear^(1/2.2) over their domain, so a 0.18 linear patch must read
// round(255 * 0.18^(1/2.2)) = 117 in the screenshot whatever the domain is.
import fs from 'node:fs';
const N = 17;
const dmax = Number( process.argv[ 2 ] || 1 );
const out = [ `TITLE "gamma22 test domain 0-${dmax}"`, `LUT_3D_SIZE ${N}`, 'DOMAIN_MIN 0.0 0.0 0.0', `DOMAIN_MAX ${dmax} ${dmax} ${dmax}` ];
for ( let b = 0; b < N; b ++ ) for ( let g = 0; g < N; g ++ ) for ( let r = 0; r < N; r ++ ) {
	const f = ( i ) => Math.min( 1, Math.pow( ( i / ( N - 1 ) ) * dmax, 1 / 2.2 ) ).toFixed( 6 );
	out.push( `${f( r )} ${f( g )} ${f( b )}` );
}
const name = dmax === 1 ? 'gamma22.cube' : `gamma22_d${dmax}.cube`;
fs.writeFileSync( `public/test/${name}`, out.join( '\n' ) + '\n' );
console.log( `wrote public/test/${name} (${N}^3)` );
